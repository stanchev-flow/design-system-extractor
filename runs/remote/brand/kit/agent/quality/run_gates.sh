#!/usr/bin/env bash
# Standalone gate runner: ./run_gates.sh <page.html> [more.html ...]
# First run installs playwright locally (requires node >= 18). Exit 1 on any failure.
set -euo pipefail
ARGS=()
for p in "$@"; do ARGS+=("$(cd "$(dirname "$p")" && pwd)/$(basename "$p")"); done
cd "$(dirname "$0")"
if [ ! -d node_modules/playwright ]; then
  npm install --no-fund --no-audit
  npx playwright install chromium
fi
status=0
for page in "${ARGS[@]}"; do
  node contrast_audit.mjs "$page" || status=1
  node slop_audit.mjs "$page" || status=1
done
exit $status
