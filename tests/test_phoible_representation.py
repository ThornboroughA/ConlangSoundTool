import csv
import io
import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

import phoible_representation as pr
import sound_inventory_generator as sig


class TestPhoibleRepresentation(unittest.TestCase):
    def test_build_glyph_inventory_counts_dedupes_by_inventory(self):
        rows = [
            {"InventoryID": "1", "GlyphID": "A"},
            {"InventoryID": "1", "GlyphID": "A"},
            {"InventoryID": "2", "GlyphID": "A"},
            {"InventoryID": "2", "GlyphID": "B"},
            {"InventoryID": "3", "GlyphID": "NA"},
            {"InventoryID": "NA", "GlyphID": "C"},
        ]
        counts, total_inventories = pr.build_glyph_inventory_counts(rows)
        self.assertEqual(total_inventories, 3)
        self.assertEqual(counts.get("A"), 2)
        self.assertEqual(counts.get("B"), 1)
        self.assertNotIn("C", counts)

    def test_build_prevalence_weighted_entries_non_uniform(self):
        rows = [
            {"Phoneme": "i", "SegmentClass": "vowel", "Marginal": "FALSE", "GlyphID": "V1"},
            {"Phoneme": "u", "SegmentClass": "vowel", "Marginal": "FALSE", "GlyphID": "V2"},
            {"Phoneme": "n", "SegmentClass": "consonant", "Marginal": "FALSE", "GlyphID": "C1"},
            {"Phoneme": "x", "SegmentClass": "consonant", "Marginal": "FALSE", "GlyphID": "C2"},
        ]
        counts = {"V1": 2800, "V2": 35, "C1": 2500, "C2": 12}
        vowels, consonants = pr.build_prevalence_weighted_entries(
            rows=rows,
            include_marginal=True,
            include_tones=False,
            glyph_inventory_counts=counts,
            core_multiplier=1.0,
            marginal_multiplier=0.35,
        )
        vmap = {entry["segment"]: entry["representation"] for entry in vowels}
        cmap = {entry["segment"]: entry["representation"] for entry in consonants}
        self.assertGreater(vmap.get("i", 0.0), vmap.get("u", 0.0))
        self.assertGreater(cmap.get("n", 0.0), cmap.get("x", 0.0))
        self.assertGreater(len({round(value, 6) for value in vmap.values()}), 1)
        self.assertGreater(len({round(value, 6) for value in cmap.values()}), 1)

    def test_marginal_multiplier_downscales_same_base_segment(self):
        rows = [
            {"Phoneme": "t", "SegmentClass": "consonant", "Marginal": "FALSE", "GlyphID": "G1"},
            {"Phoneme": "t̪", "SegmentClass": "consonant", "Marginal": "TRUE", "GlyphID": "G1"},
        ]
        counts = {"G1": 100}
        _, consonants = pr.build_prevalence_weighted_entries(
            rows=rows,
            include_marginal=True,
            include_tones=False,
            glyph_inventory_counts=counts,
            core_multiplier=1.0,
            marginal_multiplier=0.35,
        )
        cmap = {entry["segment"]: entry["representation"] for entry in consonants}
        self.assertAlmostEqual(cmap.get("t̪", 0.0), cmap.get("t", 0.0) * 0.35, places=6)

    def test_tones_excluded_by_default_and_included_as_consonants(self):
        rows = [
            {"Phoneme": "a", "SegmentClass": "vowel", "Marginal": "FALSE", "GlyphID": "V1"},
            {"Phoneme": "s", "SegmentClass": "consonant", "Marginal": "FALSE", "GlyphID": "C1"},
            {"Phoneme": "˥", "SegmentClass": "tone", "Marginal": "FALSE", "GlyphID": "T1"},
        ]
        counts = {"V1": 100, "C1": 100, "T1": 100}

        _, consonants_without_tones = pr.build_prevalence_weighted_entries(
            rows=rows,
            include_marginal=True,
            include_tones=False,
            glyph_inventory_counts=counts,
            core_multiplier=1.0,
            marginal_multiplier=0.35,
        )
        _, consonants_with_tones = pr.build_prevalence_weighted_entries(
            rows=rows,
            include_marginal=True,
            include_tones=True,
            glyph_inventory_counts=counts,
            core_multiplier=1.0,
            marginal_multiplier=0.35,
        )

        without_set = {entry["segment"] for entry in consonants_without_tones}
        with_set = {entry["segment"] for entry in consonants_with_tones}
        self.assertNotIn("˥", without_set)
        self.assertIn("˥", with_set)

    def test_missing_or_invalid_prevalence_falls_back_to_neutral_base(self):
        rows = [
            {"Phoneme": "p", "SegmentClass": "consonant", "Marginal": "FALSE", "GlyphID": ""},
            {"Phoneme": "t", "SegmentClass": "consonant", "Marginal": "FALSE", "GlyphID": "BAD"},
            {"Phoneme": "k", "SegmentClass": "consonant", "Marginal": "FALSE", "GlyphID": "GOOD"},
        ]
        counts = {"BAD": "oops", "GOOD": 250}
        _, consonants = pr.build_prevalence_weighted_entries(
            rows=rows,
            include_marginal=True,
            include_tones=False,
            glyph_inventory_counts=counts,
            core_multiplier=1.0,
            marginal_multiplier=0.35,
        )
        cmap = {entry["segment"]: entry["representation"] for entry in consonants}
        self.assertGreater(cmap.get("p", 0.0), 0.0)
        self.assertGreater(cmap.get("t", 0.0), 0.0)
        self.assertAlmostEqual(cmap.get("p", 0.0), cmap.get("t", 0.0), places=6)

    def test_inventory_197_smoke_weights_are_varied_and_ordered(self):
        url = "https://raw.githubusercontent.com/phoible/dev/refs/heads/master/data/phoible.csv"
        try:
            with urllib.request.urlopen(url) as response:  # nosec - test fixture URL
                all_rows = list(csv.DictReader(io.TextIOWrapper(response, encoding="utf-8")))
        except Exception as exc:
            self.skipTest(f"PHOIBLE CSV unavailable for smoke test: {exc}")

        counts, _ = pr.build_glyph_inventory_counts(all_rows)
        rows_197 = [row for row in all_rows if pr.clean_phoible_value(row.get("InventoryID", "")) == "197"]
        vowels, consonants = pr.build_prevalence_weighted_entries(
            rows=rows_197,
            include_marginal=False,
            include_tones=False,
            glyph_inventory_counts=counts,
            core_multiplier=1.0,
            marginal_multiplier=0.35,
        )

        self.assertTrue(vowels)
        self.assertTrue(consonants)
        self.assertGreater(len({round(entry["representation"], 6) for entry in vowels}), 1)
        self.assertGreater(len({round(entry["representation"], 6) for entry in consonants}), 1)

        consonant_rows = [
            row
            for row in rows_197
            if pr.clean_phoible_value(row.get("SegmentClass", "")).lower() == "consonant"
            and pr.clean_phoible_value(row.get("Marginal", "")).upper() != "TRUE"
            and pr.clean_phoible_value(row.get("Phoneme", ""))
        ]
        if len(consonant_rows) < 2:
            self.skipTest("Not enough consonant rows in inventory 197 for ordering check.")

        def glyph_count(row):
            glyph_id = pr.clean_phoible_value(row.get("GlyphID", ""))
            return int(counts.get(glyph_id, 0))

        row_max = max(consonant_rows, key=glyph_count)
        row_min = min(consonant_rows, key=glyph_count)
        if glyph_count(row_max) == glyph_count(row_min):
            self.skipTest("No prevalence contrast available for inventory 197 ordering check.")

        rep_map = {entry["segment"]: entry["representation"] for entry in consonants}
        max_segment = pr.clean_phoible_value(row_max.get("Phoneme", ""))
        min_segment = pr.clean_phoible_value(row_min.get("Phoneme", ""))
        if max_segment not in rep_map or min_segment not in rep_map:
            self.skipTest("Expected segments missing from weighted consonant map.")

        self.assertGreater(rep_map[max_segment], rep_map[min_segment])

    def test_load_preset_compatibility_for_legacy_and_weighted_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            legacy_payload = {
                "name": "legacy",
                "vowels": ["a", "i"],
                "consonants": ["p", "t"],
            }
            weighted_payload = {
                "name": "weighted",
                "vowels": [{"segment": "a", "representation": 1.8}],
                "consonants": [{"segment": "t", "representation": 0.6}],
            }
            (tmp_path / "legacy.json").write_text(json.dumps(legacy_payload), encoding="utf-8")
            (tmp_path / "weighted.json").write_text(json.dumps(weighted_payload), encoding="utf-8")

            original_presets_dir = sig.PRESETS_DIR
            try:
                sig.PRESETS_DIR = str(tmp_path)
                legacy = sig.load_preset("legacy")
                weighted = sig.load_preset("weighted")
            finally:
                sig.PRESETS_DIR = original_presets_dir

            legacy_vowels = {entry["segment"]: entry["representation"] for entry in legacy["vowels_entries"]}
            weighted_vowels = {entry["segment"]: entry["representation"] for entry in weighted["vowels_entries"]}
            self.assertEqual(legacy_vowels.get("a"), 1.0)
            self.assertEqual(legacy_vowels.get("i"), 1.0)
            self.assertEqual(weighted_vowels.get("a"), 1.8)


if __name__ == "__main__":
    unittest.main()
