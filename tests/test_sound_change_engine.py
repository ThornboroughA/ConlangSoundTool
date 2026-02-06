import unittest

import sound_change_engine as sce


class TestSoundChangeEngine(unittest.TestCase):
    def test_tokenize_multi_char(self):
        tokens = sce.tokenize_form("tʃa", ["tʃ", "t", "ʃ", "a"], ".")
        self.assertEqual(tokens, ["tʃ", "a"])

    def test_tokenize_with_separator(self):
        tokens = sce.tokenize_form("tʃ.a", ["tʃ", "a"], ".")
        self.assertEqual(tokens, ["tʃ", ".", "a"])

    def test_rule_order(self):
        inventory = {"vowels": ["a"], "consonants": ["p", "b"]}
        changeset = {"rules": [{"from": "p", "to": "b"}, {"from": "b", "to": "p"}]}
        result = sce.apply_changeset_to_form("p", inventory, changeset, "")
        self.assertEqual(result, "p")

    def test_inventory_dedup_and_deletion(self):
        inventory = {"vowels": [], "consonants": ["h", "h", "s"]}
        changeset = {"rules": [{"from": "h", "to": ""}]}
        new_inventory = sce.apply_changeset_to_inventory(inventory, changeset)
        self.assertEqual(new_inventory["consonants"], ["s"])


if __name__ == "__main__":
    unittest.main()
