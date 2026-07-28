#!/usr/bin/env bash
# Start Design System Studio + static viewer on one port (default 1500).
set -euo pipefail
cd "$(dirname "$0")"

# studio_server.py launches every pipeline run with sys.executable, so the
# interpreter picked here is the one each run inherits. This script used to fall
# back to system python3 when venv/ was missing: the Studio then started and
# looked healthy, and the failure only surfaced much later as a SyntaxError from
# a run. Both checks below are therefore fatal, and deliberately loud.
REQUIRED_PY_MINOR=12

PY="${PY:-./venv/bin/python}"

if [[ ! -x "$PY" ]]; then
  cat >&2 <<EOF
Studio cannot start: no usable Python interpreter at '$PY'.

There is no fallback to system python3 on purpose — it is usually too old to
parse this project's source, and would not have the dependencies installed.

Set up the virtual environment first:

  python3 --version                       # need 3.${REQUIRED_PY_MINOR} or newer
  python3 -m venv venv
  ./venv/bin/pip install -e '.[dev]'
  ./venv/bin/playwright install chromium

Then re-run ./start-studio.sh — see docs/getting-started.md for the full setup.
EOF
  exit 1
fi

PY_VERSION="$("$PY" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null || true)"
PY_MINOR="$("$PY" -c 'import sys; print(sys.version_info[1] if sys.version_info[0] == 3 else -1)' 2>/dev/null || true)"

if [[ -z "$PY_VERSION" || -z "$PY_MINOR" ]]; then
  echo "Studio cannot start: '$PY' is not a working Python interpreter." >&2
  exit 1
fi

if (( PY_MINOR < REQUIRED_PY_MINOR )); then
  cat >&2 <<EOF
Studio cannot start: '$PY' is Python ${PY_VERSION}, but this project needs
3.${REQUIRED_PY_MINOR} or newer.

run_pipeline.py uses PEP 701 f-strings, which older interpreters cannot parse.
Starting anyway would give you a Studio that looks fine until the first run dies
with a SyntaxError.

Rebuild the virtual environment on a newer interpreter:

  rm -rf venv
  python3.${REQUIRED_PY_MINOR} -m venv venv    # or any newer 3.x
  ./venv/bin/pip install -e '.[dev]'
  ./venv/bin/playwright install chromium

See docs/getting-started.md.
EOF
  exit 1
fi

if ! "$PY" -c 'import yaml' >/dev/null 2>&1; then
  cat >&2 <<EOF
Studio cannot start: '$PY' is missing this project's dependencies.

Install them into that interpreter:

  ${PY} -m pip install -e '.[dev]'
  ./venv/bin/playwright install chromium

See docs/getting-started.md.
EOF
  exit 1
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
