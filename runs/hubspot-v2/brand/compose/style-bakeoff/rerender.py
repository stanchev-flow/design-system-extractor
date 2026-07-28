#!/usr/bin/env python3
"""Deterministic bakeoff re-render (fix7 2026-07): draw each lane's SAVED
composition.json through the current renderer — NO model calls, NO composition
edits (contrast iterate_fix.py, which patches compositions first) — then re-run
the onbrand gate. This is how the frozen checkpoint-D artifacts inherit
renderer-level fixes (fix7 devices/lints) for an honest before/after battery.

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python \
      runs/hubspot-v2/brand/compose/style-bakeoff/rerender.py [STYLE]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import compose_from_composition as cfc  # noqa: E402
import generate_composition as gc  # noqa: E402

BRAND_DIR = REPO / "runs" / "hubspot-v2" / "brand"
BRAND_YAML = BRAND_DIR / "brand.yaml"
BASE_STYLE = "corporate-saas-clean"
PAGE = "product-launch"
STYLES = ("swiss", "editorial-magazine", "neumorphism")


def hero_layout_id() -> str | None:
    import yaml
    doc = yaml.safe_load(BRAND_YAML.read_text()) or {}
    for layout in (doc.get("layouts") or []):
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return layout.get("id")
    return None


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    gate_layout = hero_layout_id()
    ok_all = True
    for style in STYLES:
        if only and style != only:
            continue
        lane = HERE.parent / f"style-bakeoff-{style}" / PAGE
        comp = json.loads((lane / "composition.json").read_text())
        cfc.render_composition(comp, BRAND_YAML, lane, style_id=BASE_STYLE,
                               brand_dir=BRAND_DIR)
        overall, failures, _ = gc.gate_composition(lane, BRAND_YAML, BASE_STYLE,
                                                   layout=gate_layout)
        print(f"[{style}] deterministic re-render gate: "
              f"{'PASS' if overall else 'FAIL'}"
              + (f" {[c for c, _ in failures]}" if failures else ""))
        ok_all &= overall
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
