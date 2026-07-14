#!/usr/bin/env python3
"""Pass-3 checkpoint-D bakeoff driver — 3 style-library styles × 1 shared brief.

Standard composition path (generate_composition.generate_composition, same
invocation shape as tools/run_hero_archetype_gallery.py: force_off_grid=True,
gate layout = the brand hero layout id, model = repo default claude-opus-4-8).
The ONLY pass-3 delta per lane is `style_directives` — the style_resolver's
rendered block for that style over the hubspot bundle.

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python \
      runs/hubspot-v2/brand/compose/style-bakeoff/run_bakeoff.py [--only STYLE]

Resumable: a lane whose page dir has a PASSING onbrand-report.json +
composition.json is skipped unless --force.
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
import style_resolver as sr        # noqa: E402

BRAND_DIR = REPO / "runs" / "hubspot-v2" / "brand"
BRAND_YAML = BRAND_DIR / "brand.yaml"
BRIEF = REPO / "evals" / "matrix" / "briefs" / "hubspot-v2" / "product-launch.md"
BASE_STYLE = "corporate-saas-clean"
STYLES = ("swiss", "editorial-magazine", "neumorphism")
# the brief's structural needs mapped to style-library section ids
SECTIONS = ["hero", "feature-trio", "metrics-band", "testimonial", "cta-band"]
PAGE = "product-launch"


def hero_layout_id() -> str | None:
    import yaml
    doc = yaml.safe_load(BRAND_YAML.read_text()) or {}
    for layout in (doc.get("layouts") or []):
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return layout.get("id")
    return None


def page_passed(page_dir: Path) -> bool:
    score = page_dir / "onbrand-report.json"
    if not (score.exists() and (page_dir / "composition.json").exists()):
        return False
    try:
        return bool(json.loads(score.read_text()).get("overall"))
    except (OSError, json.JSONDecodeError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None, choices=STYLES)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--max-repairs", type=int, default=2,
                    help="the upfront iteration budget (criteria doc)")
    args = ap.parse_args()

    brief_text = BRIEF.read_text()
    library = sr.load_library()
    bundle = sr.load_brand_bundle(BRAND_DIR)
    gate_layout = hero_layout_id()
    summary_path = HERE / "bakeoff-summary.json"
    summary: dict = {"brief": str(BRIEF.relative_to(REPO)), "baseStyle": BASE_STYLE,
                     "maxRepairs": args.max_repairs, "lanes": {}}
    if summary_path.exists():
        try:
            summary.update(json.loads(summary_path.read_text()))
        except (OSError, json.JSONDecodeError):
            pass

    ok_all = True
    for style in STYLES:
        if args.only and style != args.only:
            continue
        lane = HERE.parent / f"style-bakeoff-{style}"
        out_dir = lane / PAGE
        if not args.force and page_passed(out_dir):
            print(f"[{style}] already gate-green — skip (--force to redo)")
            continue

        resolutions = sr.resolve_all(style, library, bundle, SECTIONS)
        block = sr.render_style_directive_block(style, resolutions, library)
        (lane / "style-directive-block.txt").parent.mkdir(parents=True, exist_ok=True)
        (lane / "style-directive-block.txt").write_text(block)
        (lane / "resolutions.json").write_text(
            json.dumps(resolutions, indent=2, default=str) + "\n")

        print(f"[{style}] generating {PAGE} (directive block {len(block)} chars)")
        t0 = time.time()
        res = gc.generate_composition(
            brief_text, BRAND_YAML, BASE_STYLE,
            out_dir=out_dir, brief_id=PAGE,
            max_repairs=args.max_repairs,
            layout=gate_layout,
            force_off_grid=True,              # gallery-lane convention
            style_directives=block,
        )
        refs = sorted({str(s.get("archetypeRef"))
                       for s in ((res.composition or {}).get("sections") or [])
                       if isinstance(s, dict) and s.get("archetypeRef")})
        summary["lanes"][style] = {
            "ok": res.ok, "attempts": res.attempts, "archetypes": refs,
            "seconds": round(time.time() - t0, 1),
            "failures": res.failures[:6],
            "sections": [
                {"id": s.get("id"), "useCase": s.get("useCase"),
                 "archetype": s.get("archetype"),
                 "archetypeRef": s.get("archetypeRef"),
                 "surfaceIntent": s.get("surfaceIntent")}
                for s in ((res.composition or {}).get("sections") or [])
                if isinstance(s, dict)],
        }
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"[{style}] {'PASS' if res.ok else 'FAIL'} after {res.attempts} attempt(s)"
              f" — archetypes: {refs}")
        ok_all &= res.ok

    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
