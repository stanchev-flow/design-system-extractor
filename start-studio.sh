#!/usr/bin/env bash
# Start Design System Studio + static viewer on one port (default 1500).
set -euo pipefail
cd "$(dirname "$0")"

PY="${PY:-./venv/bin/python}"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

PORT="${STUDIO_PORT:-1500}"

if command -v lsof >/dev/null 2>&1; then
  if lsof -i ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Port ${PORT} is already in use." >&2
    echo "  lsof -i :${PORT}    # find the process" >&2
    echo "  Stop it first (often: python3 -m http.server ${PORT}), then re-run ./start-studio.sh" >&2
    exit 1
  fi
fi

exec "$PY" studio_server.py
