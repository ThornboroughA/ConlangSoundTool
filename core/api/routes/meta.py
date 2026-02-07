from __future__ import annotations

from fastapi import APIRouter

from core.engine import project_io, sample_text

router = APIRouter()


@router.get("/meta/presets")
def list_presets() -> dict:
    return {
        "style_presets": list(sample_text.STYLE_PRESETS.keys()),
        "concept_lists": list(sample_text.CONCEPT_LIST_PRESETS.keys()),
        "grammar_profiles": list(sample_text.GRAMMAR_PROFILES.keys()),
        "defaults": {
            "style_name": sample_text.DEFAULT_STYLE_PRESET,
            "concept_list_name": sample_text.DEFAULT_CONCEPT_LIST,
            "grammar_profile_name": sample_text.DEFAULT_GRAMMAR_PROFILE,
        },
    }


@router.get("/meta/templates")
def list_templates() -> dict:
    return {"templates": list(project_io.DEFAULT_FAMILY_CONFIG.get("sound_change_templates_enabled", []))}
