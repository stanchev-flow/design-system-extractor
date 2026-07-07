#!/usr/bin/env python3
"""HubSpot end-to-end test-page runner (2026-07-02 second-brand system test).

Drives the REAL live composition path — brand_pipeline/generate_composition.py
(one structured Anthropic call → schema validate → neverDo prefilter → off-grid
prefilter → render → onbrand_check --composition gate → ≤2 repairs) — against the
refreshed runs/hubspot/brand/brand.yaml with the CONSERVATIVE base style
`corporate-saas-clean` (offGridExpansion: false, freedomBudget ceiling 2). The
brief is the shared brand-neutral signup-launch brief (the same one the WoodWave
composer runs consume), so nothing about the composition is hand-authored.

Output lands at runs/hubspot/brand/compose/signup-launch/ — the exact directory
shape studio_server.compose_pages() discovers as a "Composed: signup-launch" lane.

Usage:  ../../venv/bin/python run_page.py            (from this dir)
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
OUT_DIR = REPO / "runs" / "hubspot" / "brand" / "compose" / "signup-launch"


def main() -> int:
    if not gc.load_api_keys():
        print("ANTHROPIC_API_KEY missing (checked .env.local) — live generation blocked.")
        return 2
    brief_text = BRIEF_MD.read_text()
    t0 = time.time()
    # Structural bias only (run_hybrid-style varietyDirective; not copy/JSON authoring):
    # keeps the run inside HubSpot's own captured patterns + the style's centered stance,
    # and avoids the split/overlay scaffolds whose CSS carries WoodWave literal fallback
    # hexes (#F7EFE6/#1F1A14) that the off-palette slop check flags.
    directive = (
        "Seed every section from the project library patterns where available "
        "(hero-scrim-filled-cta, features-rounded-card-grid, cta-elevated-card) with "
        "novelty reuse/adapt. Use stack / cards / stack-fullbleed archetypes only — no "
        "split, overlay, banded, collage or interlock. Do NOT declare per-section "
        "alignment (inherit the style's centered stance). For every media slot bind "
        "asset.src to one of the provided real brand filenames. In the features cards "
        "section, every module copy object MUST also carry an 'asset' key set to one of "
        "the provided real filenames as a BARE STRING filename (never an object) so no module falls back "
        "to placeholder photography. Realize primary actions as contract 'button' slots "
        "(the brand's filled orange CTA).")
    res = gc.generate_composition(
        brief_text, BRAND_YAML, STYLE_ID,
        out_dir=OUT_DIR, brief_id="signup-launch",
        # gate context layout: generate_composition DEFAULTS to WoodWave's
        # "opening-bookend" layout id (absent from HubSpot's brand.yaml -> the gate
        # hard-fails before checking anything). Use "navbar": the only HubSpot layout
        # no heading/title/media componentMapping roles, so the source-copy fidelity
        # rows (meant for section RE-renders, not novel compositions) do not assert
        # the homepage hero copy against a brief-driven page; its inverse bg (#1f1f1f)
        # is genuinely present (closing CTA band + footer).
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
        "offGridExpansion": False,
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
