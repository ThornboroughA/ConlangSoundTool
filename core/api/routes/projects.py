from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from core.api.models.payloads import ProjectCreateRequest, ProjectLoadRequest, ProjectSaveRequest
from core.api.routes.utils import get_default_project_root, resolve_project_dir
from core.engine import project_io

router = APIRouter()


@router.get("/projects")
def list_projects() -> Dict[str, List[Dict[str, str]]]:
    root = get_default_project_root()
    if not root.exists():
        return {"projects": []}
    projects = []
    for path in sorted(root.iterdir()):
        if path.is_dir() and (path / "project.json").exists():
            projects.append({"id": path.name, "path": str(path)})
    return {"projects": projects}


@router.post("/project/create")
def create_project(payload: ProjectCreateRequest) -> Dict[str, Any]:
    root_dir = Path(payload.root_dir).expanduser() if payload.root_dir else get_default_project_root()
    try:
        project = project_io.create_project(
            root_dir=root_dir,
            project_name=payload.name,
            seed=payload.seed,
            time_span_years=payload.time_span_years,
        )
        return {"project": project}
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/project/load")
def load_project(payload: ProjectLoadRequest) -> Dict[str, Any]:
    project_dir = Path(payload.project_dir).expanduser()
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project directory not found.")
    project = project_io.load_project(project_dir)
    return {"project": project}


@router.post("/project/save")
def save_project(payload: ProjectSaveRequest) -> Dict[str, Any]:
    project = payload.project
    project_io.save_project(project)
    return {"status": "ok"}


@router.get("/project/{project_id}/tree")
def get_tree(project_id: str) -> Dict[str, Any]:
    project_dir = resolve_project_dir(project_id)
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found.")
    project = project_io.load_project(project_dir)
    languages = project_io.load_project_languages(project_dir, project)
    return {"languages": languages}
