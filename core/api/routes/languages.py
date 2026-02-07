from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

import random

from core.api.models.payloads import (
    CreateChildRequest,
    GenerateChangesetRequest,
    PreviewChildRequest,
    RerollRequest,
    SampleRequest,
    SaveChangesetRequest,
)
from core.api.routes.utils import resolve_project_dir
from core.engine import family_generator, language_diff, project_io, sample_text, sound_change

router = APIRouter()


def _get_project(project_id: str) -> Path:
    project_dir = resolve_project_dir(project_id)
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found.")
    return project_dir


@router.get("/project/{project_id}/languages")
def list_languages(project_id: str) -> Dict[str, Any]:
    project_dir = _get_project(project_id)
    project = project_io.load_project(project_dir)
    languages = project_io.load_project_languages(project_dir, project)
    return {"languages": languages}


@router.get("/project/{project_id}/language/{language_id}")
def get_language(project_id: str, language_id: str) -> Dict[str, Any]:
    project_dir = _get_project(project_id)
    project = project_io.load_project(project_dir)
    languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
    path = languages_dir / f"{language_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Language not found.")
    return {"language": project_io.load_language(path)}


@router.post("/project/{project_id}/preview-child")
def preview_child(project_id: str, payload: PreviewChildRequest) -> Dict[str, Any]:
    project_dir = _get_project(project_id)
    preview = family_generator.preview_child_language(
        project_dir=project_dir,
        parent_language_id=payload.parent_language_id,
        child_name=payload.child_name,
        child_id=payload.child_id,
        changeset=payload.changeset,
        override_settings=payload.override_settings,
    )
    project = project_io.load_project(project_dir)
    languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
    parent_language = project_io.load_language(languages_dir / f"{payload.parent_language_id}.json")
    diff = sound_change.diff_inventory(
        parent_language.get("inventory", {}),
        preview.get("inventory", {}),
    )
    summary = language_diff.summarize_rule_effects(parent_language.get("inventory", {}), payload.changeset)
    lexicon_preview = language_diff.sample_lexicon_diff(parent_language, preview, n=12)
    return {"language": preview, "diff": diff, "summary": summary, "lexicon_preview": lexicon_preview}


@router.post("/project/{project_id}/create-child")
def create_child(project_id: str, payload: CreateChildRequest) -> Dict[str, Any]:
    project_dir = _get_project(project_id)
    created = family_generator.create_child_language(
        project_dir=project_dir,
        parent_language_id=payload.parent_language_id,
        child_name=payload.child_name,
        child_id=payload.child_id,
        changeset=payload.changeset,
        override_settings=payload.override_settings,
    )
    return {"language": created}


@router.post("/project/{project_id}/save-changeset")
def save_changeset(project_id: str, payload: SaveChangesetRequest) -> Dict[str, Any]:
    project_dir = _get_project(project_id)
    project = project_io.load_project(project_dir)
    changesets_dir = Path(project_dir) / project.get("paths", {}).get("changesets_dir", "changesets")
    changeset = payload.changeset
    changeset_id = changeset.get("changeset_id")
    if not changeset_id:
        raise HTTPException(status_code=400, detail="changeset_id is required.")
    project_io.save_changeset(changeset, changesets_dir / f"{changeset_id}.json")
    return {"status": "ok"}


@router.post("/project/{project_id}/changeset/generate")
def generate_changeset(project_id: str, payload: GenerateChangesetRequest) -> Dict[str, Any]:
    project_dir = _get_project(project_id)
    project = project_io.load_project(project_dir)
    languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
    parent_path = languages_dir / f"{payload.parent_language_id}.json"
    if not parent_path.exists():
        raise HTTPException(status_code=404, detail="Parent language not found.")
    parent_language = project_io.load_language(parent_path)
    parent_inventory = parent_language.get("inventory", {})

    seed_base = int(project.get("seed", 0))
    seed_value = abs(hash(f"{seed_base}:{payload.parent_language_id}:{payload.changeset_id}")) % (2**32)
    rng = random.Random(seed_value)
    changeset = family_generator.generate_changeset(
        parent_inventory=parent_inventory,
        enabled_templates=list(payload.template_ids),
        event_count=max(1, int(payload.event_count)),
        rng=rng,
        changeset_id=payload.changeset_id,
        name=payload.name,
    )
    return {"changeset": changeset}


@router.get("/project/{project_id}/compare")
def compare(project_id: str, parent_id: str, child_id: str, sample_count: int = 20) -> Dict[str, Any]:
    project_dir = _get_project(project_id)
    project = project_io.load_project(project_dir)
    languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
    parent_path = languages_dir / f"{parent_id}.json"
    child_path = languages_dir / f"{child_id}.json"
    if not parent_path.exists() or not child_path.exists():
        raise HTTPException(status_code=404, detail="Language not found.")
    parent_language = project_io.load_language(parent_path)
    child_language = project_io.load_language(child_path)
    diff = sound_change.diff_inventory(
        parent_language.get("inventory", {}),
        child_language.get("inventory", {}),
    )
    lexicon_preview = language_diff.sample_lexicon_diff(parent_language, child_language, n=sample_count)
    return {"diff": diff, "lexicon_preview": lexicon_preview}


@router.post("/project/{project_id}/language/{language_id}/samples")
def get_samples(project_id: str, language_id: str, payload: SampleRequest) -> Dict[str, Any]:
    project_dir = _get_project(project_id)
    project = project_io.load_project(project_dir)
    languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
    path = languages_dir / f"{language_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Language not found.")
    language = project_io.load_language(path)
    model = project_io.hydrate_language_model(language)
    inventory = model.get("inventory", {})
    vowels = inventory.get("vowels", []) if isinstance(inventory, dict) else []
    consonants = inventory.get("consonants", []) if isinstance(inventory, dict) else []
    syllable_range = model.get("syllable_range", [1, 1])
    if not isinstance(syllable_range, (list, tuple)) or len(syllable_range) != 2:
        syllable_range = [1, 1]
    words_range = payload.words_range if len(payload.words_range) == 2 else [3, 7]
    samples = sample_text.build_sample_sentences(
        vowels=vowels,
        consonants=consonants,
        sample_count=payload.sample_count,
        syllable_range=(int(syllable_range[0]), int(syllable_range[1])),
        words_range=(int(words_range[0]), int(words_range[1])),
        syllable_separator=str(model.get("syllable_separator", "")),
        style_name=str(model.get("style_name", sample_text.DEFAULT_STYLE_PRESET)),
        concept_list_name=str(model.get("concept_list_name", sample_text.DEFAULT_CONCEPT_LIST)),
        grammar_profile_name=str(model.get("grammar_profile_name", sample_text.DEFAULT_GRAMMAR_PROFILE)),
        language_model=model,
        phonotactic_profile_overrides=model.get("phonotactic_profile_overrides"),
    )
    return {"samples": samples}


@router.post("/project/{project_id}/language/{language_id}/reroll")
def reroll_entry(project_id: str, language_id: str, payload: RerollRequest) -> Dict[str, Any]:
    project_dir = _get_project(project_id)
    project = project_io.load_project(project_dir)
    languages_dir = Path(project_dir) / project.get("paths", {}).get("languages_dir", "languages")
    path = languages_dir / f"{language_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Language not found.")
    language = project_io.load_language(path)
    model = project_io.hydrate_language_model(language)
    entry = sample_text.reroll_lexicon_entry(model, payload.entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Lexicon entry not found.")
    meta = language.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    overrides = meta.get("lexicon_overrides")
    if not isinstance(overrides, dict):
        overrides = {}
    overrides[payload.entry_id] = str(entry.get("ipa", ""))
    meta["lexicon_overrides"] = overrides
    language["meta"] = meta
    language["lexicon"] = model.get("lexicon", language.get("lexicon", []))
    project_io.save_language(project_io.normalize_language_snapshot(language), path)
    return {"language": language, "entry": entry}
