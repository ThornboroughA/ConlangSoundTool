#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt

rm -rf dist build core_api.spec || true
pyinstaller --name core_api --onefile -m core.api.app

mkdir -p apps/desktop/src-tauri/bin
cp dist/core_api apps/desktop/src-tauri/bin/core_api

echo "Sidecar built: apps/desktop/src-tauri/bin/core_api"
