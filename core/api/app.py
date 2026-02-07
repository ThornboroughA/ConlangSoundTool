from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.api.routes import languages, meta, projects
from core.api.routes.utils import get_default_project_root

app = FastAPI(title="Conlang Sound Toolkit API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    project_root: Path = get_default_project_root()
    return {"status": "ok", "project_root": str(project_root), "cwd": os.getcwd()}


app.include_router(projects.router)
app.include_router(languages.router)
app.include_router(meta.router)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("CONLANG_API_HOST", "127.0.0.1")
    port = int(os.getenv("CONLANG_API_PORT", "8000"))
    uvicorn.run("core.api.app:app", host=host, port=port, reload=False)
