#!/usr/bin/env python3
"""Phase D live e2e runner (2026-07-07) — Remote v2 lane from the RE-EXTRACTED brand.

Same live path as experiments/remote-e2e/run_page.py (generate_composition.py:
one structured Anthropic call -> schema validate -> neverDo prefilter -> off-grid
prefilter -> render via compose_from_composition -> onbrand gate, provenance HARD
-> <=2 repairs) against the Phase-D re-extracted runs/remote/brand/brand.yaml.

DELIBERATELY NO variety_directive: the Phase B prompt overhaul folded the proven
run-directive content into the base prompt (surface grammar derived from the
brand's own rhythm, logo walls bind {alt, asset} items from brand assets, footer
suppression, copy-quality rules) — this run PROVES the all-light grammar + real
logo wall arrive with zero per-run steering.

FENCE: output goes to runs/remote/brand/compose/signup-launch-v2/ (new lane;
prior lanes stay frozen). Needs ANTHROPIC_API_KEY via .env.local (never printed).

Usage:  ./venv/bin/python experiments/phaseD-remote-v2/run_v2.py   (from repo root)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "brand_pipeline"))
sys.path.insert(0, str(REPO / "src"))

import generate_composition as gc  # noqa: E402

BRAND_YAML = REPO / "runs" / "remote" / "brand" / "brand.yaml"
BRIEF_MD = REPO / "experiments" / "woodwave-ab" / "inputs" / "signup-launch.md"
STYLE_ID = "corporate-saas-clean"
OUT_DIR = REPO / "runs" / "remote" / "brand" / "compose" / "signup-launch-v2"


def main() -> int:
    if not gc.load_api_keys():
        print("ANTHROPIC_API_KEY missing (checked .env.local) — live generation blocked.")
        return 2
    brief_text = BRIEF_MD.read_text()
    t0 = time.time()
    res = gc.generate_composition(
        brief_text, BRAND_YAML, STYLE_ID,
        out_dir=OUT_DIR, brief_id="signup-launch",
        layout="hero",           # gate context: a real Remote layout id
        variety_directive=None,  # Phase D point: base prompt carries everything
        max_repairs=2)
    wall = round(time.time() - t0, 1)
    comp = res.composition or {}
    sections = comp.get("sections", [])
    summary = {
        "ok": res.ok,
        "attempts": res.attempts,
        "wall_s": wall,
        "style": STYLE_ID,
        "out_dir": str(OUT_DIR),
        "offGridExpansion": res.off_grid_expansion,
        "sections": [{"id": s.get("id"), "useCase": s.get("useCase"),
                      "archetype": s.get("archetype"), "novelty": s.get("novelty"),
                      "surfaceIntent": s.get("surfaceIntent"),
                      "seededFrom": s.get("seededFrom")} for s in sections],
        "failures": res.failures,
        "schema_errors": res.schema_errors,
        "neverdo_hits": res.neverdo_hits,
        "scorecard_overall": (res.scorecard or {}).get("overall"),
    }
    (HERE / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
