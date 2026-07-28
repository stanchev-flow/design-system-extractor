#!/usr/bin/env python3
"""customer-story lane driver — generate + gate a NEW customers page for hubspot-v2.

Standard composition path (generate_composition.generate_composition), style_id
`saas-product` (auto-resolved 50-style PRESET layer fires), gates ENFORCED
(fail-closed flow — hubspot-v2 is a gate-PASSING brand so generation is ALLOWED).

Also assembles + saves the EXACT prompt the generator builds (same code paths) so
the [[PASS3-STYLE]] preset block and [[MEDIA-FACTS]] media block are provable on
disk.

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python \
      runs/hubspot-v2/brand/compose/customer-story/run_customer_story.py [--force]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import generate_composition as gc  # noqa: E402

BRAND_DIR = REPO / "runs" / "hubspot-v2" / "brand"
BRAND_YAML = BRAND_DIR / "brand.yaml"
BRIEF = HERE / "copy-brief.md"
# PRESET_STYLE is the style-library preset id whose auto-resolved [[PASS3-STYLE]]
# block shapes the prompt (proven fired on the pure auto path). BASE_STYLE is the
# renderable styles/<id>.md base the renderer + gate need — no preset id has a
# base-style file, so we render in the brand's natural base and inject the IDENTICAL
# resolved preset block (the pass-3 bakeoff pattern). See changes.md.
PRESET_STYLE = "saas-product"
BASE_STYLE = "corporate-saas-clean"
OUT_DIR = HERE                  # render index.html at the lane root


def hero_layout_id() -> str | None:
    import yaml
    doc = yaml.safe_load(BRAND_YAML.read_text()) or {}
    for layout in (doc.get("layouts") or []):
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return layout.get("id")
    return None


def assemble_and_save_prompt() -> tuple[dict, str]:
    """(1) PROVE the AUTO path: resolve the preset block exactly as
    generate_composition does when style_id is a preset id (fires only for a
    style-library preset). (2) Assemble the DELIVERY prompt (base style renders +
    gates; the IDENTICAL preset block injected) and save it. Returns the sentinel
    map + the resolved preset block (to pass through to generation)."""
    import archetype_library as al
    import relume_recipe_catalog as recipe_catalog

    brief_text = BRIEF.read_text()
    doc = gc.load_brand(BRAND_YAML)
    seeds = gc.seed_patterns(doc, BRAND_YAML)
    off_grid = gc.resolve_off_grid_expansion(BASE_STYLE, doc, force=True)

    # (1) AUTO path proof — internal resolution keyed on the PRESET id.
    auto_block = gc._auto_style_directives(PRESET_STYLE, BRAND_YAML)
    (HERE / "auto-preset-block.txt").write_text(auto_block or "")

    meta, brief_body = al.parse_brief_frontmatter(brief_text)
    pt = (meta.get("pageType") or "").strip().lower()
    gen = str(meta.get("genre") or "heroes-saas").strip()
    var = str(meta.get("variance") or "mid").strip().lower()
    exclude = tuple(str(x) for x in (meta.get("excludeArchetypes") or []))
    hero_candidates = None
    if off_grid and pt and gen and al.genre_available(gen):
        cands = al.shortlist(al.load_genre(gen), pt, meta.get("taskIntents") or [],
                             variance=var, brand_hero=al.brand_hero_structure(doc),
                             off_grid=off_grid, exclude=exclude)
        if cands:
            hero_candidates = al.render_candidate_block(cands)

    try:
        recipe_use_cases = [u for u in seeds.use_cases if u != "footer"]
        section_recipes = recipe_catalog.guidance_for_use_cases(recipe_use_cases) or None
    except Exception:
        section_recipes = None

    # (2) DELIVERY prompt — base style (renderable) + the identical preset block.
    prompt = gc.build_prompt(
        brief_body, BRAND_YAML, BASE_STYLE, seeds,
        off_grid_expansion=off_grid,
        hero_candidates=hero_candidates,
        used_surfaces=tuple(meta.get("usedSurfaces") or ()),
        style_directives=auto_block,
        section_recipe_guidance=section_recipes,
    )
    (HERE / "assembled-prompt.txt").write_text(prompt)
    fired = {
        "auto_preset_fired": bool(auto_block),
        "auto_preset_chars": len(auto_block or ""),
        "PASS3-STYLE": "[[PASS3-STYLE:BEGIN]]" in prompt,
        "MEDIA-FACTS": "[[MEDIA-FACTS:BEGIN]]" in prompt,
        "PASS3-FACTS": "[[PASS3-FACTS:BEGIN]]" in prompt,
        "hero_candidates": bool(hero_candidates),
        "prompt_chars": len(prompt),
    }
    (HERE / "prompt-sentinels.json").write_text(json.dumps(fired, indent=2) + "\n")
    return fired, (auto_block or "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    fired, preset_block = assemble_and_save_prompt()
    print("prompt sentinels:", json.dumps(fired))

    gate_layout = hero_layout_id()
    print(f"generating customer-story (base style={BASE_STYLE}, preset={PRESET_STYLE}, "
          f"gate layout={gate_layout}, gates ENFORCED)")
    t0 = time.time()
    res = gc.generate_composition(
        BRIEF.read_text(), BRAND_YAML, BASE_STYLE,
        out_dir=OUT_DIR, brief_id="customer-story",
        max_repairs=2,
        layout=gate_layout,
        force_off_grid=True,          # lane-level lever; brand style pin untouched
        style_directives=preset_block,  # inject the auto-resolved saas-product preset block
        enforce_gates=True,           # PROVE the fail-closed flow (hubspot-v2 PASSES)
    )
    refs = sorted({str(s.get("archetypeRef"))
                   for s in ((res.composition or {}).get("sections") or [])
                   if isinstance(s, dict) and s.get("archetypeRef")})
    secs = [{"id": s.get("id"), "useCase": s.get("useCase"),
             "archetype": s.get("archetype"), "archetypeRef": s.get("archetypeRef"),
             "surfaceIntent": s.get("surfaceIntent")}
            for s in ((res.composition or {}).get("sections") or []) if isinstance(s, dict)]
    summary = {"ok": res.ok, "attempts": res.attempts, "archetypes": refs,
               "seconds": round(time.time() - t0, 1),
               "failures": res.failures[:8], "sections": secs,
               "promptSentinels": fired}
    (HERE / "run-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{'PASS' if res.ok else 'FAIL'} after {res.attempts} attempt(s) — "
          f"archetypes: {refs}")
    if not res.ok:
        print("failures:", res.failures[:8])
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
