# Conlang Sound Toolkit

Offline tooling for building phoneme inventories, lexicons, and language families with a desktop-first UI. The core engine stays in Python, exposed through a local FastAPI sidecar, while the UI is a Tauri + React app with an interactive language tree.

## What is the “sidecar” and what should I run?

You’ll see a few ways to run the app; here’s the simple mental model:

- **Engine** (Python): the “brains” (sound changes, lexicon, projects).
- **API server** (FastAPI): a local HTTP server that exposes the engine to a UI.
- **UI** (React): the “face” (tree + panels).
- **Tauri shell** (desktop app): a native desktop wrapper that shows the UI and (eventually) ships as a mac app.

**Sidecar = the API server packaged as a standalone executable** (built from Python with PyInstaller). When you run the **Tauri desktop app**, it starts that sidecar in the background on a local port and the UI talks to it.

If you’re developing or testing quickly, the easiest path is:

1) run the **API server** in one terminal  
2) run the **UI** in another terminal

## Architecture

- `core/engine` — pure Python logic (inventory, sound change, lexicon, family tools)
- `core/api` — FastAPI server exposing JSON endpoints for the UI
- `apps/desktop` — Tauri + React desktop app (Cytoscape tree, panels, help)
- `streamlit_legacy` — legacy Streamlit UI (kept for reference)
- `presets/` and `rules/` — data inputs for the inventory generator
- `outputs/` — generated content and projects

## Project location (important)

Projects are stored on disk in a “project root” folder. The API uses:

- `CONLANG_PROJECT_ROOT` (if set), otherwise
- `~/Documents/ConlangSoundTool/Projects`

If you already have projects under `outputs/projects/`, set:

```bash
export CONLANG_PROJECT_ROOT="outputs/projects"
```

## Quickstart (recommended: UI + API, no Tauri)

This runs the UI in your browser (fastest dev loop) and uses the real API + engine underneath.

If you want the simplest “single command” start:

```bash
./scripts/dev_web.sh
```

If that script says “API did not start”, run:

```bash
pip install -r requirements.txt
```

### 1) Terminal A — start the API

```bash
pip install -r requirements.txt
export CONLANG_PROJECT_ROOT="outputs/projects"
CONLANG_API_PORT=8000 python -m core.api.app
```

You should see the API start locally on `http://127.0.0.1:8000`.

### 2) Terminal B — start the UI

```bash
cd apps/desktop
npm install
npm run dev
```

Open the UI at `http://localhost:5173`.

## Quickstart (desktop shell: Tauri)

Use this if you want the “native desktop” window instead of a browser tab.

### 0) One-time prerequisites

- Install Xcode Command Line Tools:

```bash
xcode-select --install
```

- Install Rust (via rustup):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Then restart your terminal (or run `source ~/.zshrc`) and verify:

```bash
rustc --version
cargo --version
```

- Install the Tauri CLI (recommended: project-local)

This repo already includes `@tauri-apps/cli` in `apps/desktop/package.json`. Running `npm install` in `apps/desktop` installs it automatically (no global install needed).

From inside `apps/desktop`:

```bash
npm install
```

Verify the CLI is available:

```bash
cd apps/desktop
npx tauri -V
```

Optional (global install, not required):

```bash
cargo install tauri-cli --locked
```

### 1) Build the sidecar executable (API)

```bash
pip install -r requirements-build.txt
pyinstaller --name core_api --onefile -m core.api.app
mkdir -p apps/desktop/src-tauri/bin
mv dist/core_api apps/desktop/src-tauri/bin/
```

### 2) Run the desktop app

```bash
cd apps/desktop
npm run tauri:dev
```

## Helper scripts (even simpler)

If you prefer single commands, use:

- `scripts/dev_web.sh` — starts API + UI (browser)
- `scripts/build_sidecar.sh` — builds/copies the sidecar for Tauri
- `scripts/dev_tauri.sh` — builds sidecar and launches the desktop app

## Other entrypoints

### Engine CLI (inventory generator)

```bash
pip install -r requirements.txt
python core/engine/sound_inventory.py \
  --presets english korean \
  --weights 0.4 0.6 \
  --random-weight 0.1 \
  --rules demo_shift \
  --name MyLang \
  --output outputs/mylang
```

### Legacy Streamlit (optional)

```bash
pip install -r requirements-streamlit.txt
streamlit run streamlit_legacy/app.py
```

## Docs

- `docs/architecture.md`
- `docs/api.md`
- `docs/ui.md`

## Troubleshooting (Tauri)

- **`tauri: command not found`**
  - Run `cd apps/desktop && npm install` and then use `npx tauri -V` to confirm the local CLI is installed.
- **Build fails on macOS with missing compiler/tools**
  - Run `xcode-select --install`, restart terminal, then retry.
