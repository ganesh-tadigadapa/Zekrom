#!/usr/bin/env bash
# Start the ZEKROM API (port 8000) and the frontend dev server (port 5173).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) &
API=$!
trap 'kill $API 2>/dev/null' EXIT
cd "$ROOT/frontend" && npx vite --host 127.0.0.1 --port 5173
