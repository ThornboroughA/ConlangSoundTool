import unittest

import concept_packs


class TestConceptPacks(unittest.TestCase):
    def test_load_and_select(self):
        packs = concept_packs.load_packs()
        self.assertTrue(packs)

        config = dict(concept_packs.DEFAULT_CONCEPT_PACK_CONFIG)
        config["tier_limits"] = {"core": 100, "context": 5, "optional": 0}
        config["random_seed"] = 1
        selected = concept_packs.select_pack_entries(config)
        self.assertLessEqual(len(selected), 5)
        for entry in selected:
            self.assertIn("concept_id", entry)
            self.assertIn("meaning", entry)
            self.assertIn("pos", entry)
            self.assertIn("source_pack", entry)
            self.assertIsInstance(entry.get("tags", []), list)


if __name__ == "__main__":
    unittest.main()
