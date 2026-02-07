import tempfile
import unittest
from pathlib import Path

from core.engine import project_io


class TestProjectIO(unittest.TestCase):
    def test_project_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = project_io.create_project(Path(tmp), "Test Project", seed=123, time_span_years=2000)
            project_dir = Path(tmp) / project["project_slug"]
            loaded = project_io.load_project(project_dir)
            self.assertEqual(loaded["project_name"], "Test Project")
            self.assertEqual(int(loaded["seed"]), 123)
            self.assertEqual(int(loaded["time_span_years"]), 2000)

    def test_hydrate_language_model(self):
        language = {
            "inventory": {"vowels": ["a"], "consonants": ["p"]},
            "lexicon": [
                {"id": "ROOT:001", "ipa": "pa", "meaning": "fire", "gloss": "FIRE", "pos": "N", "source": "concept-list"}
            ],
        }
        hydrated = project_io.hydrate_language_model(language)
        self.assertIn("by_pos", hydrated)
        self.assertIn("particles", hydrated)
        self.assertIn("N", hydrated["by_pos"])


if __name__ == "__main__":
    unittest.main()
