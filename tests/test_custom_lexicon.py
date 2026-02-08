import random
import unittest

import sample_text_generator as stg


class TestCustomLexicon(unittest.TestCase):
    def _build_model(self):
        return stg.build_language_model(
            vowels=["a", "i"],
            consonants=["p", "t", "k"],
            syllable_range=(1, 2),
            syllable_separator="",
            style_name=stg.DEFAULT_STYLE_PRESET,
            concept_list_name=stg.DEFAULT_CONCEPT_LIST,
            grammar_profile_name=stg.DEFAULT_GRAMMAR_PROFILE,
            phonotactic_profile_overrides=None,
        )

    def test_build_custom_entry_metadata(self):
        model = self._build_model()
        meta = {"mode": "random", "syllable_range": [1, 1]}
        entry = stg.build_custom_entry(
            language_model=model,
            meaning="firefly",
            pos="N",
            gloss="FIREFLY",
            custom_meta=meta,
            ipa_override="pa",
        )
        self.assertEqual(entry["source"], "custom")
        self.assertEqual(entry["custom"]["mode"], "random")
        self.assertEqual(entry["ipa"], "pa")

    def test_reroll_custom_entry_changes_ipa(self):
        model = self._build_model()
        meta = {"mode": "random", "syllable_range": [1, 1]}
        entry = stg.build_custom_entry(
            language_model=model,
            meaning="stone",
            pos="N",
            gloss="STONE",
            custom_meta=meta,
            ipa_override="pa",
        )
        model["lexicon"].append(entry)
        old_ipa = entry["ipa"]

        random.seed(7)
        updated = stg.reroll_lexicon_entry(model, entry_id=entry["id"])
        self.assertIsNotNone(updated)
        self.assertNotEqual(updated["ipa"], old_ipa)
        self.assertEqual(updated["id"], entry["id"])
        self.assertEqual(updated["meaning"], "stone")

    def test_rooted_custom_generation_uses_root(self):
        model = self._build_model()
        root_entry = next(entry for entry in model["lexicon"] if str(entry.get("id", "")).startswith("ROOT:"))
        meta = {
            "mode": "rooted",
            "root_id": root_entry["id"],
            "affix_mode": "prefix",
            "affix_syllable_range": [1, 1],
        }
        random.seed(3)
        generated = stg.generate_custom_word_form(model, meta)
        self.assertIn(root_entry["ipa"], generated)
        existing = {str(entry.get("ipa", "")) for entry in model["lexicon"] if isinstance(entry, dict)}
        self.assertNotIn(generated, existing)


if __name__ == "__main__":
    unittest.main()
