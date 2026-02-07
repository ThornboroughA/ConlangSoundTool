from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_default_project_root() -> Path:
    env_root = os.getenv("CONLANG_PROJECT_ROOT")
    if env_root:
        raw = Path(env_root).expanduser()
        if raw.is_absolute():
            return raw
        # Prefer CWD-relative so `CONLANG_PROJECT_ROOT=outputs/projects` works
        # when running from the repo root.
        cwd_based = (Path.cwd() / raw).resolve()
        if cwd_based.exists():
            return cwd_based
        # Fallback: resolve relative to the repo root (useful if the API is launched
        # from a different working directory).
        repo_root = Path(__file__).resolve().parents[4]
        return (repo_root / raw).resolve()
    return Path.home() / "Documents" / "ConlangSoundTool" / "Projects"


def resolve_project_dir(project_id: str, root_override: Optional[str] = None) -> Path:
    root = Path(root_override).expanduser() if root_override else get_default_project_root()
    return root / project_id
