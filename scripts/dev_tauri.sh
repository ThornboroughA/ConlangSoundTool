#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PROJECT_ROOT_DEFAULT="${ROOT_DIR}/outputs/projects"
export CONLANG_PROJECT_ROOT="${CONLANG_PROJECT_ROOT:-$PROJECT_ROOT_DEFAULT}"

echo "Project root: ${CONLANG_PROJECT_ROOT}"

echo "Building sidecar..."
"${ROOT_DIR}/scripts/build_sidecar.sh"

cd "${ROOT_DIR}/apps/desktop"
if [ ! -d node_modules ]; then
  npm install
fi

echo "Starting Tauri desktop app..."
npm run tauri:dev
