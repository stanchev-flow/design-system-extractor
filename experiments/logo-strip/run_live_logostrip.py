#!/usr/bin/env python3
"""HubSpot logo-strip LIVE seeded rerun (2026-07-03).

Same live path + arguments as experiments/hubspot-fix/run_live_fixed.py (verbatim
directive, so the A/B against signup-launch-fixed-live isolates the logo-strip
device), rerun AFTER the AS-33 device landed. Output goes to a NEW additive dir
runs/hubspot/brand/compose/signup-launch-logostrip-live/ (all prior dirs stay
read-only). The deterministic replay of the fixed-live composition lives beside it
in signup-launch-logostrip/ — that one isolates the device on a known composition;
this one proves the end-to-end seeded path converges green with the device active.

Usage:  ../../venv/bin/python run_live_logostrip.py   (from this dir)
Needs ANTHROPIC_API_KEY via the repo .env.local (loaded by load_api_keys).
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

BRAND_YAML = REPO / "runs" / "hubspot" / "brand" / "brand.yaml"
BRIEF_MD = REPO / "experiments" / "woodwave-ab" / "inputs" / "signup-launch.md"
STYLE_ID = "corporate-saas-clean"
OUT_DIR = REPO / "runs" / "hubspot" / "brand" / "compose" / "signup-launch-logostrip-live"


def main() -> int:
    if not gc.load_api_keys():
        print("ANTHROPIC_API_KEY missing (checked .env.local) — live generation blocked.")
        return 2
    brief_text = BRIEF_MD.read_text()
    t0 = time.time()
    # Same structural directive as run_live_fixed.py (verbatim) so the A/B isolates
    # the logo-strip device.
    directive = (
        "Seed every section from the project library patterns where available "
        "(hero-scrim-filled-cta, features-rounded-card-grid, cta-elevated-card) with "
        "novelty reuse/adapt. Use stack / cards / stack-fullbleed archetypes only — no "
        "split, overlay, banded, collage or interlock. Do NOT declare per-section "
        "alignment (inherit the style's centered stance). For every media slot bind "
        "asset.src to one of the provided real brand filenames. In the features cards "
        "section, every module copy object MUST also carry an 'asset' key set to one of "
        "the provided real filenames as a BARE STRING filename (never an object) so no "
        "module falls back to placeholder photography. Realize primary actions as "
        "contract 'button' slots (the brand's filled orange CTA).")
    res = gc.generate_composition(
        brief_text, BRAND_YAML, STYLE_ID,
        out_dir=OUT_DIR, brief_id="signup-launch",
        layout="footer",           # real HubSpot layout id (B8 workaround, as before)
        variety_directive=directive,
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
    (HERE / "live-results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
