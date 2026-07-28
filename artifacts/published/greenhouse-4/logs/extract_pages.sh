#!/usr/bin/env bash
# Fresh multi-page Greenhouse 4 evidence extraction from existing captures.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
PY=./venv/bin/python
BRAND=runs/greenhouse-4/brand
PAGES=(home talent-sourcing compare)
STAGE="${1:-evidence}"  # evidence | ground | all

run_page_evidence() {
  local page="$1"
  local CAP="screenshots/greenhouse-4/$page"
  local OUT="$BRAND/evidence/pages/$page"
  mkdir -p "$OUT/crops" "$OUT/grounding"
  echo "======== EVIDENCE $page ========"
  $PY tools/extract/mine_dom.py --capture "$CAP" --out "$OUT/dom-sections.json"
  $PY tools/extract/mine_css.py --capture "$CAP" --out-dir "$OUT"
  $PY tools/extract/mine_motion.py --evidence "$OUT" --out "$OUT/motion-audit.json"
  $PY tools/extract/measure_computed.py --capture "$CAP" --out-dir "$OUT" --viewport 1440x900
  $PY tools/extract/slice_sections.py \
    --capture "$CAP" \
    --screenshot "$CAP/${page}-fullpage.png" \
    --rects "$OUT/section-rects.json" \
    --out-dir "$OUT/crops"
  $PY tools/extract/curate_assets.py --capture "$CAP" --brand-dir "$BRAND" --auto --force
  echo "======== DONE EVIDENCE $page ========"
}

run_page_ground() {
  local page="$1"
  local OUT="$BRAND/evidence/pages/$page"
  echo "======== GROUND $page ========"
  $PY tools/extract/ground_sections_vision.py \
    --crops-manifest "$OUT/crops/crops-manifest.json" \
    --crops-dir "$OUT/crops" \
    --out-dir "$OUT/grounding" \
    --model claude-opus-4-8 \
    --reasoning-effort medium \
    --force
  echo "======== DONE GROUND $page ========"
}

case "$STAGE" in
  evidence)
    for p in "${PAGES[@]}"; do run_page_evidence "$p"; done
    ;;
  ground)
    for p in "${PAGES[@]}"; do run_page_ground "$p"; done
    ;;
  all)
    for p in "${PAGES[@]}"; do run_page_evidence "$p"; run_page_ground "$p"; done
    ;;
  *)
    echo "usage: $0 [evidence|ground|all]"; exit 2
    ;;
esac
