#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

API_PORT="${CONLANG_API_PORT:-8000}"
PROJECT_ROOT_DEFAULT="${ROOT_DIR}/outputs/projects"

export CONLANG_PROJECT_ROOT="${CONLANG_PROJECT_ROOT:-$PROJECT_ROOT_DEFAULT}"
export CONLANG_API_PORT="$API_PORT"

echo "Starting API on http://127.0.0.1:${API_PORT}"
echo "Project root: ${CONLANG_PROJECT_ROOT}"

python -m core.api.app &
API_PID=$!

cleanup() {
  echo "Stopping API (pid ${API_PID})"
  kill "${API_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Waiting for API to become ready..."
for i in {1..30}; do
  if curl -fsS "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
    echo "API is ready."
    break
  fi
  sleep 0.2
done

if ! curl -fsS "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
  echo "API did not start. Common fixes:"
  echo "- Ensure dependencies are installed: pip install -r requirements.txt"
  echo "- Ensure the port is free: export CONLANG_API_PORT=8000"
  exit 1
fi

cd "${ROOT_DIR}/apps/desktop"
if [ ! -d node_modules ]; then
  npm install
fi

echo "Starting UI (Vite) at http://localhost:5173"
npm run dev
