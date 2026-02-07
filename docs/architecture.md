# Architecture

## Overview

The toolkit is split into three layers so the UI can evolve independently from the language engine:

1. **Engine (Python)** — deterministic logic for inventories, sound changes, lexicon generation, and family tools.
2. **API (FastAPI)** — a local HTTP boundary that the UI can call while staying offline.
3. **Desktop UI (Tauri + React)** — interactive panels and Cytoscape-based tree navigation.

## Layout

```
core/
  engine/     # pure logic
  api/        # FastAPI surface
  tests/      # unittest coverage
apps/
  desktop/    # Tauri + React UI
streamlit_legacy/
docs/
presets/
rules/
outputs/
```

## Data flow

1. UI requests data over local HTTP.
2. FastAPI validates payloads and calls engine functions.
3. Engine reads/writes project files inside `outputs/projects`.

## Offline model

- The API runs as a sidecar binary packaged with the desktop app.
- The UI always calls `http://127.0.0.1:<port>` on the local machine.
- No external services are required.
