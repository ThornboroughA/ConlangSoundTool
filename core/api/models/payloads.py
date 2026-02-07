from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., description="Project name")
    seed: int = Field(0, description="Random seed")
    time_span_years: int = Field(2000, description="Timeline span")
    root_dir: Optional[str] = Field(None, description="Optional project root directory")


class ProjectLoadRequest(BaseModel):
    project_dir: str


class ProjectSaveRequest(BaseModel):
    project: Dict[str, Any]


class PreviewChildRequest(BaseModel):
    parent_language_id: str
    child_name: str
    child_id: str
    changeset: Dict[str, Any]
    override_settings: Optional[Dict[str, Any]] = None


class CreateChildRequest(PreviewChildRequest):
    pass


class SaveChangesetRequest(BaseModel):
    changeset: Dict[str, Any]


class CompareRequest(BaseModel):
    parent_id: str
    child_id: str
    sample_count: int = 20


class GenerateChangesetRequest(BaseModel):
    parent_language_id: str
    template_ids: list[str]
    event_count: int = 1
    changeset_id: str
    name: str


class SampleRequest(BaseModel):
    sample_count: int = 5
    words_range: list[int] = Field(default_factory=lambda: [3, 7])


class RerollRequest(BaseModel):
    entry_id: str
