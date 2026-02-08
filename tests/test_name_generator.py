import unittest

import name_generator


class TestNameGenerator(unittest.TestCase):
    def setUp(self):
        self.language_model = {
            "meta": {"language_id": "lang_test"},
            "lexicon": [
                {"id": "ROOT:core.deity", "ipa": "sa", "meaning": "sun god", "pos": "N", "tags": ["deity"]},
                {"id": "ROOT:core.virtue", "ipa": "ra", "meaning": "honor", "pos": "N", "tags": ["virtue"]},
                {"id": "ROOT:core.person", "ipa": "mi", "meaning": "person", "pos": "N", "tags": ["person"]},
                {"id": "ROOT:core.landform", "ipa": "to", "meaning": "hill", "pos": "N", "tags": ["landform"]},
                {"id": "ROOT:core.settlement", "ipa": "na", "meaning": "town", "pos": "N", "tags": ["settlement"]},
            ],
        }

    def test_load_templates(self):
        templates = name_generator.load_templates()
        self.assertTrue(templates)

    def test_generate_names(self):
        templates = [
            {
                "template_id": "deity_virtue",
                "name_type": "personal",
                "subtype": "given",
                "parts": [{"tags_any": ["deity"]}, {"tags_any": ["virtue"]}],
                "joiner": "",
                "weight": 1.0,
            },
            {
                "template_id": "land_settlement",
                "name_type": "toponym",
                "subtype": "settlement",
                "parts": [{"tags_any": ["landform"]}, {"tags_any": ["settlement"]}],
                "joiner": " ",
                "weight": 1.0,
            },
        ]
        config = {
            "counts_by_type": {
                "personal": {"given": 1, "family": 0, "title": 0},
                "toponym": {"settlement": 1, "hydronym": 0, "terrain": 0},
            },
            "archaic_bias": {"self": 1.0},
            "register_bias": {"neutral": 1.0},
            "biome_filters": [],
            "random_seed": 7,
        }
        names = name_generator.generate_names(self.language_model, config, templates=templates)
        self.assertEqual(len(names), 2)
        self.assertTrue(all("form_ipa" in entry for entry in names))

    def test_merge_locked(self):
        existing = [
            {"name_id": "NAME:personal:given:0001", "name_type": "personal", "subtype": "given", "locked": True}
        ]
        generated = [
            {"name_id": "NAME:personal:given:0001", "name_type": "personal", "subtype": "given", "locked": False}
        ]
        merged = name_generator.merge_locked(existing, generated)
        self.assertTrue(merged[0].get("locked"))


if __name__ == "__main__":
    unittest.main()
