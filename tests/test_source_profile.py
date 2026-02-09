import json
import tempfile
import unittest
from pathlib import Path

import sound_inventory_generator as sig
import source_profile


class TestSourceProfile(unittest.TestCase):
    def test_load_preset_with_and_without_sidecar(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            preset_payload = {
                "name": "Example",
                "vowels": [{"segment": "a", "representation": 1.0}],
                "consonants": [{"segment": "t", "representation": 1.0}],
            }
            sidecar_payload = {
                "version": 1,
                "provenance": ["unit-test"],
                "segment_frequency": {
                    "vowel_weights": {"a": 2.0, "i": 1.0},
                    "consonant_weights": {"t": 1.2},
                },
            }
            (tmp_path / "with_sidecar.json").write_text(json.dumps(preset_payload), encoding="utf-8")
            (tmp_path / "with_sidecar.profile.json").write_text(json.dumps(sidecar_payload), encoding="utf-8")
            (tmp_path / "without_sidecar.json").write_text(json.dumps(preset_payload), encoding="utf-8")

            old_presets_dir = sig.PRESETS_DIR
            old_source_presets_dir = source_profile.PRESETS_DIR
            try:
                sig.PRESETS_DIR = str(tmp_path)
                source_profile.PRESETS_DIR = str(tmp_path)
                with_sidecar = sig.load_preset("with_sidecar")
                without_sidecar = sig.load_preset("without_sidecar")
            finally:
                sig.PRESETS_DIR = old_presets_dir
                source_profile.PRESETS_DIR = old_source_presets_dir

            self.assertIn("source_profile", with_sidecar)
            self.assertNotIn("source_profile", without_sidecar)

    def test_normalize_source_profile_sanitizes_values(self):
        raw_profile = {
            "version": 1,
            "provenance": ["source A", "", "source B"],
            "segment_frequency": {
                "vowel_weights": {"a": 2, "i": 1, "u": "bad"},
                "consonant_weights": {"t": 3, "k": 1, "x": -2},
            },
            "template_weights_by_position": {
                "single": [["CV", 5], ["CVC", 1], ["INVALID", 8], ["CV", 1]],
                "final": [["VC", 2], ["CVCC", 1], ["", 2]],
            },
            "slot_class_weights": {"coda": {"nasal": 1.2, "stop": "bad", "liquid": 0.8}},
            "co_occurrence": {"front_back_harmony_bonus": "1.5", "enabled": 1},
            "soft_constraints": {"hiatus_penalty": "0.2", "cluster_violation_penalty": None},
            "cluster": {"max_attempts": "16", "violation_penalty": 0.3},
            "hard_constraints": {"deny": ["CVC"]},
        }
        normalized = source_profile.normalize_source_profile(raw_profile)
        self.assertIn("segment_frequency", normalized)
        self.assertIn("template_weights_by_position", normalized)
        self.assertNotIn("hard_constraints", normalized)
        single_pairs = normalized["template_weights_by_position"]["single"]
        single_total = sum(weight for _, weight in single_pairs)
        self.assertAlmostEqual(single_total, 1.0, places=6)
        labels = {label for label, _ in single_pairs}
        self.assertIn("CV", labels)
        self.assertIn("CVC", labels)
        self.assertNotIn("INVALID", labels)

    def test_mix_source_profiles_weighted_merge(self):
        profile_a = {
            "version": 1,
            "provenance": ["A"],
            "segment_frequency": {
                "vowel_weights": {"a": 1.8, "i": 0.7},
                "consonant_weights": {"t": 1.6, "k": 0.8},
            },
            "template_weights_by_position": {
                "single": [["CV", 0.8], ["CVC", 0.2]],
            },
        }
        profile_b = {
            "version": 1,
            "provenance": ["B"],
            "segment_frequency": {
                "vowel_weights": {"a": 0.7, "i": 1.7},
                "consonant_weights": {"t": 0.7, "k": 1.5},
            },
            "template_weights_by_position": {
                "single": [["CV", 0.2], ["CVC", 0.8]],
            },
        }
        mixed = source_profile.mix_source_profiles([profile_a, profile_b], [0.75, 0.25])
        vweights = mixed.get("segment_frequency", {}).get("vowel_weights", {})
        self.assertGreater(vweights.get("a", 0.0), vweights.get("i", 0.0))
        single_pairs = dict(mixed.get("template_weights_by_position", {}).get("single", []))
        self.assertGreater(single_pairs.get("CV", 0.0), single_pairs.get("CVC", 0.0))
        self.assertIn("A", mixed.get("provenance", []))
        self.assertIn("B", mixed.get("provenance", []))

    def test_override_assembly_and_influence_neutral(self):
        sound_template_overrides = {
            "segment_frequency": {
                "enabled": True,
                "strength": 1.0,
                "vowel_weights": {"a": 1.1},
                "consonant_weights": {},
            },
            "soft_constraints": {"hiatus_penalty": 0.4},
        }
        source_profile_overrides = {
            "soft_constraints": {"hiatus_penalty": 0.2},
            "co_occurrence": {"harmony_penalty": 0.8},
        }
        fallback_segment_frequency = {
            "segment_frequency": {
                "enabled": True,
                "strength": 1.0,
                "vowel_weights": {"a": 2.0},
                "consonant_weights": {},
            }
        }
        ui_tuning_overrides = {"soft_constraints": {"hiatus_penalty": 0.7}}
        advanced_override = {"soft_constraints": {"hiatus_penalty": 0.9}}
        merged = source_profile.merge_generation_overrides(
            sound_template_overrides=sound_template_overrides,
            source_profile_overrides=source_profile_overrides,
            fallback_segment_frequency_overrides=fallback_segment_frequency,
            ui_tuning_overrides=ui_tuning_overrides,
            advanced_override_dict=advanced_override,
            use_source_segment_frequency=True,
        )
        self.assertAlmostEqual(
            float(merged.get("soft_constraints", {}).get("hiatus_penalty", 0.0)),
            0.9,
            places=6,
        )
        self.assertAlmostEqual(
            float(merged.get("segment_frequency", {}).get("vowel_weights", {}).get("a", 0.0)),
            1.1,
            places=6,
        )

        profile = {
            "version": 1,
            "segment_frequency": {"vowel_weights": {"a": 2.0}, "consonant_weights": {"t": 1.5}},
            "co_occurrence": {"front_back_harmony_bonus": 1.4},
        }
        neutral = source_profile.build_phonotactic_overrides_from_source_profile(profile, influence=0.0)
        self.assertEqual(neutral, {})

    def test_integration_smoke_distinct_sidecar_templates(self):
        english = sig.mix_inventories(
            preset_names=["english_2252"],
            weights=[1.0],
            random_weight=0.0,
            master_preset_name="random_master",
        )
        japanese = sig.mix_inventories(
            preset_names=["japanese_197"],
            weights=[1.0],
            random_weight=0.0,
            master_preset_name="random_master",
        )
        english_profile = english.get("source_profile_mixed", {})
        japanese_profile = japanese.get("source_profile_mixed", {})
        self.assertIsInstance(english_profile, dict)
        self.assertIsInstance(japanese_profile, dict)
        english_final = dict(english_profile.get("template_weights_by_position", {}).get("final", []))
        japanese_final = dict(japanese_profile.get("template_weights_by_position", {}).get("final", []))
        self.assertGreater(english_final.get("CVCC", 0.0), japanese_final.get("CVCC", 0.0))
        english_single = dict(english_profile.get("template_weights_by_position", {}).get("single", []))
        japanese_single = dict(japanese_profile.get("template_weights_by_position", {}).get("single", []))
        self.assertGreater(japanese_single.get("CV", 0.0), english_single.get("CV", 0.0))


if __name__ == "__main__":
    unittest.main()
