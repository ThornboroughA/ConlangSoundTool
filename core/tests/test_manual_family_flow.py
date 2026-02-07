import tempfile
import unittest
from pathlib import Path

from core.engine import family_generator
from core.engine import language_diff
from core.engine import project_io
from core.engine import sound_change as sound_change_engine
from core.engine.sample_text import DEFAULT_CONCEPT_LIST, DEFAULT_GRAMMAR_PROFILE, DEFAULT_STYLE_PRESET


def _write_proto(project_dir: Path) -> None:
    languages_dir = project_dir / "languages"
    proto = {
        "schema_version": 1,
        "meta": {
            "language_id": "proto",
            "name": "Proto",
            "year": 0,
            "parent_id": None,
            "changeset_id": None,
            "created_at": "now",
            "notes": "",
            "lexicon_overrides": {},
        },
        "style_name": DEFAULT_STYLE_PRESET,
        "concept_list_name": DEFAULT_CONCEPT_LIST,
        "grammar_profile_name": DEFAULT_GRAMMAR_PROFILE,
        "syllable_range": [1, 1],
        "syllable_separator": "",
        "phonotactic_profile_overrides": {},
        "inventory": {"vowels": ["a"], "consonants": ["p", "t"]},
        "lexicon": [
            {
                "id": "ROOT:001",
                "ipa": "pa",
                "meaning": "fire",
                "gloss": "FIRE",
                "pos": "N",
                "source": "concept-list",
            }
        ],
    }
    project_io.save_language(proto, languages_dir / "proto.json")


class TestManualFamilyFlow(unittest.TestCase):
    def test_child_language_creation_and_id_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = project_io.create_project(Path(tmp), "Test Family", seed=1, time_span_years=2000)
            project_dir = Path(tmp) / project["project_slug"]
            _write_proto(project_dir)
            project["root_language_id"] = "proto"
            project["language_index"] = [{"language_id": "proto", "filename": "proto.json"}]
            project_io.save_project(project)

            changeset = {
                "schema_version": 1,
                "changeset_id": "chg_proto_child",
                "name": "proto→child",
                "description": "",
                "rules": [{"from": "p", "to": "b", "enabled": True}],
            }

            child = family_generator.create_child_language(
                project_dir=project_dir,
                parent_language_id="proto",
                child_name="Child",
                child_id="child",
                changeset=changeset,
                override_settings={"year": 200},
            )
            self.assertEqual(child["meta"]["parent_id"], "proto")
            self.assertEqual(child["lexicon"][0]["ipa"], "ba")

            child2 = family_generator.create_child_language(
                project_dir=project_dir,
                parent_language_id="proto",
                child_name="Child",
                child_id="child",
                changeset=changeset,
                override_settings={"year": 300},
            )
            self.assertNotEqual(child2["meta"]["language_id"], "child")

    def test_inventory_diff_and_rule_summary(self):
        parent = {"vowels": ["a"], "consonants": ["p"]}
        changeset = {"rules": [{"from": "p", "to": "b", "enabled": True}]}
        child = sound_change_engine.apply_changeset_to_inventory(parent, changeset)
        diff = sound_change_engine.diff_inventory(parent, child)
        self.assertIn("added_consonants", diff)
        summary = language_diff.summarize_rule_effects(parent, changeset)
        self.assertEqual(summary["rule_count"], 1)


if __name__ == "__main__":
    unittest.main()
