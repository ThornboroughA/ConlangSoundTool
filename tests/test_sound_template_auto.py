import unittest

import sample_text_generator as stg


class TestSoundTemplateAuto(unittest.TestCase):
    def test_auto_template_weights_bias_open(self):
        vowels = ["a", "e", "i", "o", "u", "ə"]
        consonants = ["p", "t"]
        features = stg.inventory_features(vowels, consonants)
        weights = stg.auto_template_weights(features)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=5)
        self.assertGreater(weights["Open-Vowel"], weights["Clustered"])
        self.assertGreater(weights["Smooth"], weights["Punchy"])

    def test_blend_sound_templates(self):
        overrides = stg.blend_sound_templates({"Smooth": 1.0})
        self.assertIsInstance(overrides, dict)
        self.assertAlmostEqual(overrides.get("style_template_blend", 0.0), 0.25, places=5)
        single = overrides.get("template_weights_by_position", {}).get("single", [])
        total = sum(weight for _, weight in single) if single else 0.0
        self.assertAlmostEqual(total, 1.0, places=5)


if __name__ == "__main__":
    unittest.main()
