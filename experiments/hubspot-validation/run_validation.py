#!/usr/bin/env python3
"""HubSpot token-layer VALIDATION runner (2026-07-03).

Decisive end-to-end retest of the 2026-07-02 "WoodWave brand with HubSpot colors"
verdict, after the token-layer batch (experiments/token-layer-impl/REPORT.md) landed:
per-brand layer-1 tokens feeding the --c-* alias contract, renderer hardcodes
eliminated, token-provenance gate HARD under --composition.

Drives the SAME live path the prior worker drove (generate_composition.py: one
structured Anthropic call -> schema validate -> neverDo prefilter -> off-grid
prefilter -> render via compose_from_composition -> onbrand_check --composition
gate -> <=2 repairs), against the UNTOUCHED runs/hubspot/brand/brand.yaml
(mtime/sha snapshotted in input-hashes.txt) with corporate-saas-clean.

FENCE: output goes to a NEW directory runs/hubspot/brand/compose/signup-launch-tokenized/
(additive-only under runs/hubspot/**; the prior worker's signup-launch/ is read-only).

Usage:  ../../venv/bin/python run_validation.py   (from this dir)
Needs ANTHROPIC_API_KEY via the repo .env.local (loaded by load_api_keys).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent                      # design-system-extractor-mine
sys.path.insert(0, str(REPO / "brand_pipeline"))
sys.path.insert(0, str(REPO / "src"))

import generate_composition as gc              # noqa: E402

BRAND_YAML = REPO / "runs" / "hubspot" / "brand" / "brand.yaml"
BRIEF_MD = REPO / "experiments" / "woodwave-ab" / "inputs" / "signup-launch.md"
STYLE_ID = "corporate-saas-clean"
OUT_DIR = REPO / "runs" / "hubspot" / "brand" / "compose" / "signup-launch-tokenized"


def main() -> int:
    if not gc.load_api_keys():
        print("ANTHROPIC_API_KEY missing (checked .env.local) — live generation blocked.")
        return 2
    brief_text = BRIEF_MD.read_text()
    t0 = time.time()
    # Structural bias only (same shape as the prior harness so the A/B against the
    # 2026-07-02 run isolates the token batch; the prior directive's WoodWave-fallback
    # avoidance rationale is obsolete — the scaffolds are fallback-free now — but the
    # archetype set below IS HubSpot's own captured grammar, so it stays).
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
        # gate context layout: generate_composition defaults to WoodWave's
        # "opening-bookend" id, absent from HubSpot's brand.yaml (prior worker's B8).
        # "footer" is a real HubSpot layout id whose inverse bg (#1f1f1f) is genuinely
        # present (closing CTA band + footer) — same choice as the prior harness.
        layout="footer",
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
    (HERE / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if res.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
