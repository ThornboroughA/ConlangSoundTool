import unittest

import sample_text_generator as stg


class TestSegmentFrequency(unittest.TestCase):
    def test_segment_frequency_weighting(self):
        overrides = {
            "segment_frequency": {
                "enabled": True,
                "strength": 1.0,
                "consonant_weights": {"p": 4.0, "t": 1.0},
            }
        }
        profile = stg.resolve_phonotactic_profile(stg.DEFAULT_STYLE_PRESET, overrides)
        freq = profile.get("segment_frequency", {}).get("consonant_weights", {})
        self.assertGreater(freq.get("p", 0.0), freq.get("t", 0.0))

        weight_p = stg._segment_weight_for_slot("p", "onset", profile)
        weight_t = stg._segment_weight_for_slot("t", "onset", profile)
        self.assertGreater(weight_p, weight_t)


if __name__ == "__main__":
    unittest.main()
