#!/usr/bin/env bash
# Do the Math — install deps and launch the backend + frontend, opening the app
# in your browser. Press Ctrl+C to stop both.
#
# Prerequisites: uv (https://docs.astral.sh/uv/) and Node.js 20.19+ / 22.12+.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Installing backend dependencies (uv)…"
(cd "$ROOT/backend" && uv sync)

echo "==> Installing frontend dependencies (npm)…"
(cd "$ROOT/frontend" && npm install)

echo "==> Starting backend on http://localhost:8000 …"
(cd "$ROOT/backend" && uv run uvicorn app.main:app --port 8000) &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT

echo "==> Starting frontend (it will open in your browser)…"
echo "    Enter your Anthropic API key on first run, then start graphing."
(cd "$ROOT/frontend" && npm run dev -- --open)
