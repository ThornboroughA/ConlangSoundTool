from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import concept_packs
import name_generator
from sample_text_generator import (
    DEFAULT_CONCEPT_LIST,
    DEFAULT_GRAMMAR_PROFILE,
    DEFAULT_STYLE_PRESET,
    rebuild_indices,
)


DEFAULT_SCHEMA_VERSION = 1
DEFAULT_FAMILY_CONFIG: Dict[str, Any] = {
    "extant_language_count": 50,
    "min_branch_years": 100,
    "events_per_1000_years": 6.0,
    "sound_change_templates_enabled": [
        "stop_voicing",
        "stop_devoicing",
        "s_voicing",
        "h_loss",
        "approximant_shift",
        "r_shift",
        "vowel_raise_pair",
        "vowel_lower_pair",
    ],
    "tree_type": "binary",
}


def _now_iso() -> str:
    return datetime.now().isoformat()


def sanitize_slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip()).strip("_").lower()
    return cleaned or "project"


def _normalize_segment_list(raw_segments: Any) -> list:
    if not isinstance(raw_segments, list):
        return []
    normalized: list = []
    for item in raw_segments:
        if isinstance(item, str):
            segment = item.strip()
            if segment:
                normalized.append(segment)
            continue
        if isinstance(item, dict):
            segment = str(item.get("segment", "")).strip()
            if segment:
                normalized.append(segment)
    return normalized


def normalize_language_snapshot(language: Dict[str, Any]) -> Dict[str, Any]:
    """Strip runtime-only fields and ensure required snapshot keys exist."""
    meta = language.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    inventory = language.get("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}

    snapshot: Dict[str, Any] = {
        "schema_version": int(language.get("schema_version", DEFAULT_SCHEMA_VERSION)),
        "meta": meta,
        "style_name": str(language.get("style_name", DEFAULT_STYLE_PRESET)),
        "concept_list_name": str(language.get("concept_list_name", DEFAULT_CONCEPT_LIST)),
        "concept_pack_config": language.get("concept_pack_config", {}),
        "grammar_profile_name": str(language.get("grammar_profile_name", DEFAULT_GRAMMAR_PROFILE)),
        "syllable_range": list(language.get("syllable_range", [1, 1])),
        "syllable_separator": str(language.get("syllable_separator", "")),
        "phonotactic_profile_overrides": language.get("phonotactic_profile_overrides", {}),
        "inventory": {
            "vowels": _normalize_segment_list(inventory.get("vowels", [])),
            "consonants": _normalize_segment_list(inventory.get("consonants", [])),
        },
        "lexicon": list(language.get("lexicon", [])) if isinstance(language.get("lexicon", []), list) else [],
    }
    return snapshot


def create_project(root_dir: Path, project_name: str, seed: int, time_span_years: int) -> Dict[str, Any]:
    root_dir = Path(root_dir)
    project_slug = sanitize_slug(project_name)
    project_dir = root_dir / project_slug
    project_file = project_dir / "project.json"
    if project_file.exists():
        raise FileExistsError(f"Project already exists at {project_file}")

    project_dir.mkdir(parents=True, exist_ok=True)
    languages_dir = project_dir / "languages"
    changesets_dir = project_dir / "changesets"
    languages_dir.mkdir(exist_ok=True)
    changesets_dir.mkdir(exist_ok=True)

    now = _now_iso()
    project: Dict[str, Any] = {
        "schema_version": DEFAULT_SCHEMA_VERSION,
        "project_name": project_name,
        "project_slug": project_slug,
        "created_at": now,
        "last_modified_at": now,
        "seed": int(seed),
        "time_span_years": int(time_span_years),
        "extant_year": int(time_span_years),
        "root_language_id": "",
        "next_language_counter": 1,
        "paths": {"languages_dir": "languages", "changesets_dir": "changesets"},
        "family_config": dict(DEFAULT_FAMILY_CONFIG),
        "concept_pack_config": dict(concept_packs.DEFAULT_CONCEPT_PACK_CONFIG),
        "name_config": dict(name_generator.DEFAULT_NAME_CONFIG),
        "culture_profile": {},
        "name_schema_version": 1,
        "language_index": [],
        "_project_dir": str(project_dir),
    }
    save_project(project)
    return project


def load_project(project_dir: Path) -> Dict[str, Any]:
    project_dir = Path(project_dir)
    path = project_dir / "project.json"
    with path.open("r", encoding="utf-8") as file:
        project = json.load(file)
    if not isinstance(project, dict):
        raise ValueError("Project file must contain a JSON object.")
    project.setdefault("concept_pack_config", dict(concept_packs.DEFAULT_CONCEPT_PACK_CONFIG))
    project.setdefault("name_config", dict(name_generator.DEFAULT_NAME_CONFIG))
    project.setdefault("culture_profile", {})
    project.setdefault("name_schema_version", 1)
    project["_project_dir"] = str(project_dir)
    return project


def save_project(project: Dict[str, Any]) -> None:
    project_dir_value = project.get("_project_dir")
    if not project_dir_value:
        raise ValueError("Project dict is missing _project_dir; cannot save.")
    project_dir = Path(project_dir_value)
    project["last_modified_at"] = _now_iso()
    path = project_dir / "project.json"
    payload = {key: value for key, value in project.items() if not str(key).startswith("_")}
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def save_language(language: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(language, file, ensure_ascii=False, indent=2)


def load_language(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        language = json.load(file)
    if not isinstance(language, dict):
        raise ValueError("Language file must contain a JSON object.")
    return language


def save_changeset(changeset: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(changeset, file, ensure_ascii=False, indent=2)


def load_changeset(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        changeset = json.load(file)
    if not isinstance(changeset, dict):
        raise ValueError("Changeset file must contain a JSON object.")
    return changeset


def hydrate_language_model(language: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure required fields are present and rebuild lookup indices."""
    model = dict(language)
    inventory = model.get("inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}
    inventory["vowels"] = _normalize_segment_list(inventory.get("vowels", []))
    inventory["consonants"] = _normalize_segment_list(inventory.get("consonants", []))
    model["inventory"] = inventory

    lexicon = model.get("lexicon", [])
    if not isinstance(lexicon, list):
        lexicon = []
    model["lexicon"] = lexicon

    model.setdefault("style_name", DEFAULT_STYLE_PRESET)
    model.setdefault("concept_list_name", DEFAULT_CONCEPT_LIST)
    model.setdefault("concept_pack_config", {})
    model.setdefault("grammar_profile_name", DEFAULT_GRAMMAR_PROFILE)
    model.setdefault("syllable_separator", "")
    model.setdefault("syllable_range", [1, 1])
    model.setdefault("phonotactic_profile_overrides", {})

    return rebuild_indices(model)
