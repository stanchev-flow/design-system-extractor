#!/usr/bin/env python3
"""Arm A (structured) generator for the WoodWave A/B experiment.

Runs the EXISTING structured pipeline (compose_page -> compose_section ->
component_render) against the SNAPSHOTTED brand.yaml + editorial-luxury style, with
the signup-launch brief's copy BOUND into the layouts' typed slots.

There is no standing brief-driven entrypoint in brand_pipeline: `compose_page.py`
walks the brand's `layouts[]` in story order and emits the brand's DEFAULT gallery
copy (SECTION_COPY / LAYOUT_COPY in compose_section.py). To honour the brief while
keeping the deterministic renderer 100% intact, this script performs ONLY the
"BIND the copy into the chosen sections' typed slots" stage of the intended flow
(brief -> section selection -> slot binding -> render): it overrides the copy dicts
in-memory and mutates the hero display-title binding, then calls the unmodified
compose_page.build_page(). No pipeline source is edited; no runs/woodwave write.

All reads come from experiments/woodwave-ab/inputs/ (the insulated snapshot).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent  # design-system-extractor-mine
BP = REPO / "brand_pipeline"
sys.path.insert(0, str(BP))

import compose_page as cp   # noqa: E402
import compose_section as cs  # noqa: E402
from styles import load_and_merge  # noqa: E402

INPUTS = HERE / "inputs"
BRAND_DIR = INPUTS / "brand"
BRAND_YAML = BRAND_DIR / "brand.yaml"
OUT = HERE / "arm-a-structured"

# ── Brief -> slot bindings (signup-launch.md), mapped onto WoodWave's editorial
# layouts. This is the structured "bind copy into typed slots" stage.
BRIEF_HEADLINE = "Everything in one place"

# Arm A's PINNED story order (hero -> value collage -> social-proof band -> signup stack).
# Pinned explicitly rather than borrowing compose_page.DEFAULT_ORDER, which the hybrid work
# expanded to an 8-section gallery narrative (dropping `info-band`) — that drift both changed
# this arm's structure and crashed the per-section report loop below.
ARM_A_ORDER = ["opening-bookend", "editorial-collage", "info-band", "conversion-stack"]

# Shared base copy (hero + nav fallback read these directly in compose_stack_hero).
SECTION_COPY = {
    "wordmark": "WoodWave",
    "nav": ["About", "Gallery", "Exhibition", "Visit"],
    "eyebrow": "Introducing",                                             # hero eyebrow
    "subhead": "A simpler way to get started \u2014 built for how you actually work.",
    "cta": "Start free",                                                  # hero primary CTA (typographic link)
}

# Per-layout brief bindings (merged over SECTION_COPY by compose_section.copy_for).
LAYOUT_COPY = {
    # value_props -> editorial collage. The deterministic collage is a SINGLE module
    # (header + one media + caption + offset body + link); the brand forbids feature
    # grids/cards, so the three value props are woven into one editorial body.
    "editorial-collage": {
        "ghost": "EVERYTHING",
        "eyebrow": "Why teams switch",
        "heading": "One place for how you actually work",
        "body": ("Set up in minutes \u2014 no manual wiring, you\u2019re live the same day. "
                 "One source of truth, so everyone sees the same thing, always up to date. "
                 "And it scales with you, from your first project to your thousandth."),
        "caption": "Built for real work",
        "cta": "See how it works",
    },
    # social_proof -> dark info-band. Stat lands in the eyebrow, the testimonial quote
    # becomes the display statement, and the value props land as the panel's ruled rows.
    "info-band": {
        "eyebrow": "Trusted by 10,000+ teams",
        "heading": "We replaced three tools in a week and never looked back",
        "panelTitle": "Why teams switch",
        "rows": [
            ("Set up in minutes", "Live the same day"),
            ("One source of truth", "Always up to date"),
            ("Scales with you", "1 \u2192 1,000+ projects"),
        ],
        "cta": "Start free",
        "caption": "Operations lead, mid-market team",
    },
    # conversion -> narrow underline signup stack (no boxed input, no button).
    "conversion-stack": {
        "eyebrow": "Introducing",
        "heading": "Everything in one place",
        "body": "A simpler way to get started \u2014 built for how you actually work.",
        "placeholder": "you@company.com",
        "cta": "Start free",
    },
}


def bind_hero_heading(doc: dict) -> None:
    """Bind the brief headline into the opening-bookend's display-title slot."""
    for layout in doc.get("layouts", []):
        if layout.get("id") != "opening-bookend":
            continue
        for m in layout.get("blockMapping", []) or []:
            role = (m.get("role") or "").lower()
            if "display title" in role or ("title" in role and m.get("contract") == "header"):
                m.setdefault("usage", {})["heading"] = BRIEF_HEADLINE


def main() -> int:
    doc = cp.load_doc(BRAND_YAML)

    # Override the composer copy dicts in-memory (brief -> slots). The renderers read
    # cs.SECTION_COPY / cs.LAYOUT_COPY by module reference, so patching binds the brief.
    cs.SECTION_COPY = SECTION_COPY
    cs.LAYOUT_COPY = LAYOUT_COPY
    bind_hero_heading(doc)

    style_ctx = load_and_merge("editorial-luxury", doc, styles_dir=INPUTS)

    OUT.mkdir(parents=True, exist_ok=True)
    # Resolve nav logo + copy media from the SNAPSHOT brand dir (offline, insulated).
    cs.prepare_nav_logo(doc, BRAND_DIR, OUT / "assets")
    html = cp.build_page(doc, BRAND_YAML, ARM_A_ORDER, style_ctx)
    (OUT / "index.html").write_text(html)
    copied = cs.copy_assets(BRAND_DIR, OUT / "assets")
    # Copy the self-hosted display face(s) (Melodrama per-weight masters) into the arm's
    # assets/ so the emitted @font-face resolves offline (mirrors compose_page.main()).
    copied += cs.copy_fonts(BRAND_DIR, OUT / "assets", doc)

    print(f"Arm A composed -> {OUT/'index.html'}  [style:{style_ctx.style_id}]")
    print(f"  order: {' -> '.join(ARM_A_ORDER)} -> closing-bookend")
    print(f"  assets copied: {', '.join(copied) or 'none'}")
    # Report unresolved slots per section (parity with compose_page.main()).
    layouts = {l.get("id"): l for l in doc.get("layouts", [])}
    import component_render as cr
    for idx, lid in enumerate(ARM_A_ORDER):
        layout = layouts[lid]
        ctx = cr.make_context(doc, *cs.resolve_surface_intent(doc, layout))
        unresolved = [r for r in cs.render_slots(doc, layout, ctx) if "unresolved slot" in r["html"]]
        print(f"  [sec-{idx}] {lid:<18} unresolved={len(unresolved)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
