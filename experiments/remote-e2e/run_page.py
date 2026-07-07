#!/usr/bin/env python3
"""Remote-brand LIVE e2e runner (2026-07-03) — the first three-brand test.

Drives the SAME live path as experiments/hubspot-validation/run_validation.py
(generate_composition.py: one structured Anthropic call -> schema validate ->
neverDo prefilter -> off-grid prefilter -> render via compose_from_composition ->
onbrand_check --composition gate (provenance HARD) -> <=2 repairs) against the
NEW runs/remote/brand/brand.yaml with corporate-saas-clean.

FENCE: output goes to runs/remote/brand/compose/signup-launch/ (additive under
runs/remote/**). No pipeline edits. Shared brand-neutral brief (signup-launch.md).

Usage:  ./venv/bin/python experiments/remote-e2e/run_page.py   (from repo root)
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

BRAND_YAML = REPO / "runs" / "remote" / "brand" / "brand.yaml"
BRIEF_MD = REPO / "experiments" / "woodwave-ab" / "inputs" / "signup-launch.md"
STYLE_ID = "corporate-saas-clean"
OUT_DIR = REPO / "runs" / "remote" / "brand" / "compose" / "signup-launch"


def main() -> int:
    if not gc.load_api_keys():
        print("ANTHROPIC_API_KEY missing (checked .env.local) — live generation blocked.")
        return 2
    brief_text = BRIEF_MD.read_text()
    t0 = time.time()
    # Structural bias mirrors the ratified HubSpot validation harness (stack/cards only —
    # the split/overlay/banded/collage/interlock composers carry editorial geometry that
    # is not Remote's grammar under this brief). Seeds name Remote's OWN extracted
    # project patterns. Asset binding rule matches the HubSpot precedent so no module
    # falls back to placeholder photography; the logo wall must bind the tagged
    # monochrome customer logo SVGs (logo-*.svg).
    directive = (
        "Seed every section from the project library patterns where available "
        "(hero-inset-noise-panel, logo-marquee-strip, features-card-grid-navy-media, "
        "cta-inline-banner, cta-closing-noise, testimonial-card-row) with novelty "
        "reuse/adapt. Use stack / cards archetypes only — no split, overlay, banded, "
        "collage or interlock. Do NOT declare per-section alignment (the seeded "
        "patterns carry it). Remote is an ALL-LIGHT brand: the hero section's "
        "surfaceIntent MUST be 'primary' (never inverse — the real hero sits on the "
        "light noise-art panel), and no section uses a dark band. In the hero, bind "
        "exactly ONE media slot (the illustration hero-globe-illustration.webp) and "
        "give that slot colSpan: 6 and z: 'front' so it renders as placed media. "
        "The logo wall's logos slot copy MUST be a list of objects, each "
        "{\"alt\": \"<Company>\", \"asset\": \"<file>\"} using the real customer logo "
        "files: logo-anthropic.svg, logo-box.svg, logo-byd.svg, logo-datadog.svg, "
        "logo-gitlab.svg, logo-heineken.svg, logo-kfc.svg, logo-lovable.svg, "
        "logo-mercury.svg, logo-miro.svg, logo-mizuho.svg, logo-vercel.svg (never "
        "bare strings, never invented names). In the features cards section, every "
        "module copy object MUST also carry an 'asset' key set to one of "
        "card-api-first.webp, card-integrations.webp, card-mcp-agents.webp as a BARE "
        "STRING filename (never an object, never icons) so no module falls back to "
        "placeholder photography. The testimonial section MUST be archetype 'stack' "
        "with a single 'testimonial' contract slot carrying {quote, name, role} copy "
        "(an avatar asset like avatar-erik-sveen.webp is optional on that slot). "
        "The footer MUST be archetype 'stack' with a 'link' contract slot whose copy "
        "is a list of {text} objects plus a 'label' legal line — no logo slot in the "
        "footer. Realize primary actions as contract 'button' slots (the brand's "
        "filled blue pill).")
    res = gc.generate_composition(
        brief_text, BRAND_YAML, STYLE_ID,
        out_dir=OUT_DIR, brief_id="signup-launch",
        # gate context layout: "hero" is a real Remote layout id (the default
        # "opening-bookend" is WoodWave's and absent from Remote's brand.yaml).
        layout="hero",
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
