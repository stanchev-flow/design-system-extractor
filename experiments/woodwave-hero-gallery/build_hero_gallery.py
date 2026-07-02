#!/usr/bin/env python3
"""build_hero_gallery.py — ONE WoodWave page that showcases 5 DISTINCT hero treatments,
each MODEL-INVENTED through the LIVE composition pipeline, stacked + labeled "Hero option N".

Pipeline (mandatory, unmodified shared modules — this script only USES them):
  brief + per-hero varietyDirective
    → brand_pipeline/generate_composition.generate_composition   (ONE live Anthropic call
        → jsonschema validate → neverDo + off-grid pre-filters → render via
        compose_from_composition → onbrand_check.py --composition gate → ≤2 repair retries)
  → take EACH generation's hero section (the model chose its archetype/slots/treatments)
  → stitch the 5 heroes into ONE composition (in option order), inserting a small labeled
    generic-flow divider ("Hero option N — <treatment>") before each subsequent hero
  → render the stitched page via compose_from_composition.render_composition (hoisted
    page-level nav once at top + shared footer once at bottom)
  → gate the assembled page with onbrand_check.py --composition (must PASS)
  → screenshot via the existing shoot_reveal_safe.mjs.

NOTHING under brand_pipeline/ is edited; the API key loads from ../../.env.local via
gc.load_api_keys() (never hardcoded, never logged).

Usage:
  ./venv/bin/python experiments/woodwave-hero-gallery/build_hero_gallery.py            # live 5-gen + assemble
  ./venv/bin/python experiments/woodwave-hero-gallery/build_hero_gallery.py --assemble-only   # re-stitch saved heroes
  ./venv/bin/python experiments/woodwave-hero-gallery/build_hero_gallery.py --offline-test    # stitch heroes harvested
                                                                                             # from woodwave-hybrid (no API)
  ./venv/bin/python experiments/woodwave-hero-gallery/build_hero_gallery.py --only 1,3        # regenerate a subset
"""
from __future__ import annotations

import argparse
import copy as _copy
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent                       # design-system-extractor-mine
BP = REPO / "brand_pipeline"
sys.path.insert(0, str(BP))
sys.path.insert(0, str(REPO / "src"))

import generate_composition as gc               # noqa: E402
import compose_from_composition as cfc          # noqa: E402

# Reuse the SAME snapshotted WoodWave brand + editorial style the woodwave-ab / -hybrid
# experiments used (proven to gate green; carries Melodrama hero-500 + gold #edd580 hover).
AB = REPO / "experiments" / "woodwave-ab"
BRAND_YAML = AB / "inputs" / "brand" / "brand.yaml"
STYLE_ID = "editorial-luxury"                   # offGridExpansion=true (Part B)
BRIEF_MD = HERE / "hero-brief.md"
SHOOT = AB / "shoot_reveal_safe.mjs"

PAGE_DIR = HERE / "page"

# The 5 DISTINCT hero directives. Each biases the treatment; the MODEL invents the actual
# archetype / slots / media / off-grid treatments within it.
HEROES = [
    {"n": 1, "id": "opt1-monumental", "name": "Centered monumental statement",
     "directive": (
         "HERO TREATMENT — a CENTERED MONUMENTAL STATEMENT. One colossal didone display "
         "line, centered on the dark inverse bookend surface, holding the whole frame with "
         "calm authority; a short eyebrow above and a single quiet arrow CTA below. Use the "
         "`stack` archetype (opening bookend). Restraint is the point — no split, no collage.")},
    {"n": 2, "id": "opt2-split", "name": "Asymmetric split with image",
     "directive": (
         "HERO TREATMENT — an ASYMMETRIC SPLIT with a large image. Copy anchored hard to one "
         "column, a single tall hero photograph filling the other, uneven column ratio for "
         "editorial tension. Use the `split` archetype. One image, no collage.")},
    {"n": 3, "id": "opt3-collage", "name": "Offset multi-image collage",
     "directive": (
         "HERO TREATMENT — an OFFSET MULTI-IMAGE COLLAGE. Two or more photographs placed at "
         "different sizes and offsets behind/around a display heading, with a ghost watermark "
         "word for depth. Use the `collage` archetype. Layer the images off the baseline.")},
    {"n": 4, "id": "opt4-fullbleed", "name": "Full-bleed image, overlaid heading",
     "directive": (
         "HERO TREATMENT — a FULL-BLEED IMAGE with the heading OVERLAID on it. A single "
         "edge-to-edge photograph fills the hero; the display title sits over it as the "
         "sanctioned hero display-title-over-media (mark that treatment sanctioned:true). Use "
         "the `stack-fullbleed` archetype. Cinematic, one image, text on media.")},
    {"n": 5, "id": "opt5-offgrid", "name": "Off-grid overlap / editorial layering",
     "directive": (
         "HERO TREATMENT — OFF-GRID OVERLAP / EDITORIAL LAYERING. Break the aligned grid: "
         "overlap the heading and imagery, stagger elements off the baseline, let a plate "
         "bleed past its column (offGridExpansion is UNLOCKED for this editorial style, so "
         "you MAY use overlap / stagger / bleed and novelty:novel). Use the `collage` or "
         "`interlock` archetype. This one should feel the most adventurous.")},
]


# ── generation ─────────────────────────────────────────────────────────────────────

def _provider_and_seeds(model=None, reasoning=None):
    if not gc.load_api_keys():
        print(f"ERROR: ANTHROPIC_API_KEY not available (looked in {REPO / '.env.local'}). "
              "Live generation blocked — set the key or use --offline-test.", flush=True)
        raise SystemExit(3)
    from screenshot_to_template.models.anthropic import AnthropicProvider
    provider = AnthropicProvider(model or gc.DEFAULT_MODEL,
                                 reasoning_effort=reasoning or gc.DEFAULT_REASONING)
    doc = gc.load_brand(BRAND_YAML)
    seeds = gc.seed_patterns(doc, BRAND_YAML)
    print(f"Model: {provider.model}  (reasoning={reasoning or gc.DEFAULT_REASONING})")
    print(f"Seed patterns: {', '.join(seeds.pattern_ids()) or '(none)'}")
    return provider, seeds


def _extract_hero(comp: dict) -> dict | None:
    for s in (comp.get("sections") or []):
        if gc._is_hero_section(s):
            return s
    # fall back to the first section if the model didn't tag a hero useCase
    secs = comp.get("sections") or []
    return secs[0] if secs else None


def generate_one(spec: dict, *, provider, seeds, brief_text: str, max_repairs: int) -> dict:
    out_dir = HERE / "gens" / spec["id"]
    print(f"\n=== GEN Hero option {spec['n']} :: {spec['name']} ===", flush=True)
    t0 = time.time()
    res = gc.generate_composition(
        brief_text, BRAND_YAML, STYLE_ID,
        out_dir=out_dir, brief_id=f"woodwave-hero-{spec['n']}",
        variety_directive=spec["directive"], max_repairs=max_repairs,
        provider=provider, seeds=seeds)
    wall = round(time.time() - t0, 1)
    comp = res.composition or {}
    hero = _extract_hero(comp)
    stages = [t.get("stage") for t in res.telemetry]
    repair_fired = res.attempts > 1
    total_in = sum((t.get("input_tokens") or 0) for t in res.telemetry)
    total_out = sum((t.get("output_tokens") or 0) for t in res.telemetry)
    summary = {
        "n": spec["n"], "id": spec["id"], "name": spec["name"],
        "ok": res.ok, "attempts": res.attempts, "repair_fired": repair_fired,
        "wall_s": wall, "stages": stages,
        "hero_archetype": (hero or {}).get("archetype"),
        "hero_novelty": (hero or {}).get("novelty"),
        "hero_surfaceIntent": (hero or {}).get("surfaceIntent"),
        "hero_treatments": sorted({t.get("kind") for t in (hero or {}).get("treatments", [])
                                   if isinstance(t, dict) and t.get("kind")}),
        "offgrid_treatments": sorted(set(gc._section_off_grid_treatments(hero or {}))),
        "tokens": {"input": total_in, "output": total_out},
        "gen_dir": str(out_dir),
    }
    # persist the harvested hero (for --assemble-only)
    if hero is not None:
        (out_dir / "hero-section.json").write_text(json.dumps(hero, indent=2) + "\n")
    print(f"  ok={res.ok} attempts={res.attempts} archetype={summary['hero_archetype']} "
          f"novelty={summary['hero_novelty']} treatments={summary['hero_treatments']} "
          f"offgrid={summary['offgrid_treatments']} wall={wall}s", flush=True)
    return summary


# ── assembly ─────────────────────────────────────────────────────────────────────

def _treatment_label(summary: dict) -> str:
    """A one-line human label for the model's actual hero treatment."""
    arche = summary.get("hero_archetype") or "?"
    nov = summary.get("hero_novelty") or "reuse"
    offgrid = summary.get("offgrid_treatments") or []
    treats = summary.get("hero_treatments") or []
    bits = [arche]
    if nov == "novel":
        bits.append("novel")
    extra = offgrid or [t for t in treats if t not in ("text-on-media",)]
    if extra:
        bits.append("+".join(extra))
    return f"{summary['name']} · {' / '.join(bits)}"


def _eyebrow_slot(text: str) -> dict:
    return {"name": "eyebrow", "role": "eyebrow", "contract": "eyebrow",
            "textLen": "short", "sizeClass": "caption", "width": "hug", "z": "front",
            "copy": {"text": text}}


def _divider_section(sid: str, eyebrow: str, heading: str) -> dict:
    """A small labeled divider rendered via the generic-flow safety-net composer (an
    archetype outside the six bespoke ones routes to `generic-flow`), so it renders a clean
    eyebrow + heading with NO signup form and NO nav — just a label between heroes. Primary
    surface, no accent, no off-grid treatment → gate-safe under any flag."""
    return {
        "id": sid, "useCase": "about", "archetype": "label-divider", "surfaceIntent": "primary",
        "novelty": "adapt", "seededFrom": None,
        "slots": [
            {"name": "eyebrow", "role": "eyebrow", "contract": "caption",
             "textLen": "short", "sizeClass": "caption", "width": "hug", "z": "front",
             "copy": {"text": eyebrow}},
            {"name": "label", "role": "header", "contract": "heading",
             "textLen": "short", "sizeClass": "title", "width": "stretch", "z": "front",
             "copy": {"text": heading}},
        ],
        "treatments": [], "knobs": {"align": "left"},
    }


def _set_hero_eyebrow(hero: dict, text: str) -> None:
    """Set/insert the hero's eyebrow slot copy so its label flows through _hero_section_copy
    → SECTION_COPY (stack heroes) without touching the model's title/media slots."""
    for s in (hero.get("slots") or []):
        if "eyebrow" in str(s.get("role") or "").lower():
            c = s.get("copy")
            if isinstance(c, dict):
                c["text"] = text
                c.pop("eyebrow", None)
            else:
                s["copy"] = {"text": text}
            return
    hero.setdefault("slots", []).insert(0, _eyebrow_slot(text))


def assemble(summaries: list[dict], *, style_id: str = STYLE_ID) -> dict:
    """Stitch the 5 harvested hero sections (in option order) into ONE composition +
    render + gate + screenshot. Section 0 is forced to the `stack` archetype so the
    page-level nav hoists (only a stack/hero opening emits the hoisted bar); heroes 2-5 are
    normalized to the primary surface so the single-accent invariant holds (the accent
    bookend is the opening hero) — mirroring the woodwave-hybrid showcase stitch. Every
    hero's ARCHETYPE / SLOTS / MEDIA / TREATMENTS remain exactly as the model invented them."""
    heroes = []
    for s in summaries:
        hero_path = Path(s["gen_dir"]) / "hero-section.json"
        if not hero_path.exists():
            raise SystemExit(f"missing harvested hero for option {s['n']}: {hero_path}")
        heroes.append((s, json.loads(hero_path.read_text())))

    sections: list[dict] = []
    notes: list[str] = []
    for idx, (s, hero) in enumerate(heroes):
        hero = _copy.deepcopy(hero)
        hero["id"] = f"hero-opt-{s['n']}"
        hero["useCase"] = "hero"
        label = f"Hero option {s['n']} — {_treatment_label(s)}"
        if idx == 0:
            # opening bookend: force stack so the page-level nav hoists; keep it the ONE
            # inverse accent section; carry its label in the hero eyebrow.
            if str(hero.get("archetype")) != "stack":
                notes.append(f"opt{s['n']}: coerced archetype "
                             f"{hero.get('archetype')}→stack for the nav-bearing opening bookend")
                hero["archetype"] = "stack"
            hero["surfaceIntent"] = "inverse"
            _set_hero_eyebrow(hero, label)
            sections.append(hero)
        else:
            # normalize surface so only the opening hero carries the accent (single-accent gate)
            if str(hero.get("surfaceIntent")) in ("inverse", "inverse-strong", "accent"):
                hero["surfaceIntent"] = "primary"
            sections.append(_divider_section(f"divider-opt-{s['n']}",
                                             f"Hero option {s['n']}", _treatment_label(s)))
            sections.append(hero)

    comp = {
        "schemaVersion": "composition.v1",
        "brief": {"id": "woodwave-hero-gallery",
                  "useCasesRequested": ["hero"]},
        "brand": {"ref": str(BRAND_YAML)},
        "style": {"id": style_id},
        "sections": sections,
        "rationale": ("Five MODEL-INVENTED WoodWave hero treatments (each generated live via "
                      "generate_composition), stacked in option order behind labeled dividers. "
                      "Opening bookend is the single inverse accent hero (+ hoisted nav); the "
                      "rest are normalized to primary for the single-accent invariant."),
    }

    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    print("\n=== ASSEMBLE :: render stitched 5-hero page ===", flush=True)
    for note in notes:
        print(f"  note: {note}")
    cfc.render_composition(comp, BRAND_YAML, PAGE_DIR, style_id=style_id,
                           brand_dir=BRAND_YAML.parent)
    overall, failures, scorecard = gc.gate_composition(
        PAGE_DIR, BRAND_YAML, style_id, layout="opening-bookend")
    # post-render asset self-heal (null any unresolved <img src>, brand photography fills in)
    if not overall and _heal_broken_assets(comp, PAGE_DIR):
        (PAGE_DIR / "composition.json").write_text(json.dumps(comp, indent=2) + "\n")
        cfc.render_composition(comp, BRAND_YAML, PAGE_DIR, style_id=style_id,
                               brand_dir=BRAND_YAML.parent)
        overall, failures, scorecard = gc.gate_composition(
            PAGE_DIR, BRAND_YAML, style_id, layout="opening-bookend")
    print(f"  gate (--composition): {'PASS' if overall else 'FAIL ' + str(failures)}", flush=True)

    accent = len(re.findall(r'class="[^"]*--accent\b', (PAGE_DIR / 'index.html').read_text().lower()))
    has_nav = '<div id="page-nav"' in (PAGE_DIR / "index.html").read_text()
    print(f"  hoisted page-nav present: {has_nav}   accent-class count: {accent}")

    shot = screenshot(PAGE_DIR / "index.html", PAGE_DIR / "screenshot.png")
    result = {
        "gate_pass": bool(overall), "failures": failures,
        "hoisted_nav": has_nav, "accent_class_count": accent,
        "notes": notes, "screenshot": shot,
        "index_html": str(PAGE_DIR / "index.html"),
        "screenshot_path": str(PAGE_DIR / "screenshot.png"),
        "order": [sec.get("id") for sec in sections],
    }
    (PAGE_DIR / "assemble-summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def _heal_broken_assets(comp: dict, render_dir: Path) -> bool:
    import os
    index = render_dir / "index.html"
    if not index.exists():
        return False
    html = index.read_text()
    srcs = set(re.findall(r'src="([^"]+\.(?:jpg|jpeg|png|svg|webp))"', html, re.I))
    broken = {os.path.basename(s) for s in srcs if not (render_dir / s).exists()}
    if not broken:
        return False
    healed = 0
    for sec in comp.get("sections") or []:
        for sl in (sec.get("slots") or []):
            a = sl.get("asset")
            if isinstance(a, dict) and os.path.basename(str(a.get("src", ""))) in broken:
                sl["asset"] = None
                healed += 1
    if healed:
        print(f"  self-heal: nulled {healed} unresolved asset(s) {sorted(broken)} → brand photography")
    return healed > 0


def screenshot(index_html: Path, out_png: Path) -> bool:
    if not SHOOT.exists():
        print(f"  screenshot skipped — {SHOOT} not found")
        return False
    try:
        proc = subprocess.run(["node", str(SHOOT), str(index_html), str(out_png), "1440", "900"],
                              cwd=str(AB), capture_output=True, text=True, timeout=180)
    except Exception as exc:
        print(f"  screenshot failed: {type(exc).__name__}: {exc}")
        return False
    if proc.returncode != 0 or not out_png.exists():
        print(f"  screenshot failed (rc={proc.returncode}): "
              f"{(proc.stderr or proc.stdout).strip()[:200]}")
        return False
    print(f"  screenshot → {out_png}")
    return True


# ── offline harness: harvest heroes from woodwave-hybrid (no API) ───────────────────

def offline_harvest() -> list[dict]:
    """Populate gens/ from existing woodwave-hybrid run compositions so --offline-test can
    exercise the assembler + gate without any model call. Uses distinct source runs so the
    5 slots differ where the saved runs differ."""
    hy = REPO / "experiments" / "woodwave-hybrid"
    srcs = ["run-1", "run-2", "run-3", "run-4", "run-5"]
    summaries = []
    for spec, src in zip(HEROES, srcs):
        comp_path = hy / src / "composition.json"
        if not comp_path.exists():
            raise SystemExit(f"offline source missing: {comp_path}")
        comp = json.loads(comp_path.read_text())
        hero = _extract_hero(comp)
        out_dir = HERE / "gens" / spec["id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "hero-section.json").write_text(json.dumps(hero, indent=2) + "\n")
        summaries.append({
            "n": spec["n"], "id": spec["id"], "name": spec["name"],
            "ok": True, "attempts": 1, "repair_fired": False, "wall_s": 0.0, "stages": ["offline"],
            "hero_archetype": hero.get("archetype"), "hero_novelty": hero.get("novelty"),
            "hero_surfaceIntent": hero.get("surfaceIntent"),
            "hero_treatments": sorted({t.get("kind") for t in hero.get("treatments", [])
                                       if isinstance(t, dict) and t.get("kind")}),
            "offgrid_treatments": sorted(set(gc._section_off_grid_treatments(hero))),
            "tokens": {"input": 0, "output": 0}, "gen_dir": str(out_dir),
        })
    return summaries


# ── main ─────────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the WoodWave 5-hero-experiments page (live).")
    ap.add_argument("--assemble-only", action="store_true",
                    help="skip generation; re-stitch the saved gens/*/hero-section.json")
    ap.add_argument("--offline-test", action="store_true",
                    help="stitch heroes harvested from woodwave-hybrid (no model call)")
    ap.add_argument("--only", default="", help="comma list of option numbers to (re)generate")
    ap.add_argument("--max-repairs", type=int, default=2)
    ap.add_argument("--model", default=None)
    ap.add_argument("--reasoning", default=None)
    args = ap.parse_args(argv)

    results_path = HERE / "generation-results.json"

    if args.offline_test:
        summaries = offline_harvest()
        result = assemble(summaries)
        _print_report(summaries, result)
        return 0 if result["gate_pass"] else 1

    if args.assemble_only:
        if not results_path.exists():
            print("no generation-results.json — run a live generation first.")
            return 2
        summaries = json.loads(results_path.read_text())["heroes"]
        result = assemble(summaries)
        _print_report(summaries, result)
        return 0 if result["gate_pass"] else 1

    # live generation
    brief_text = BRIEF_MD.read_text()
    provider, seeds = _provider_and_seeds(args.model, args.reasoning)
    only = {int(x) for x in args.only.split(",") if x.strip()} if args.only else None

    # start from any prior summaries so --only merges cleanly
    prior = {}
    if results_path.exists():
        prior = {h["n"]: h for h in json.loads(results_path.read_text()).get("heroes", [])}

    summaries = []
    for spec in HEROES:
        if only and spec["n"] not in only and spec["n"] in prior:
            summaries.append(prior[spec["n"]]); continue
        try:
            summaries.append(generate_one(spec, provider=provider, seeds=seeds,
                                          brief_text=brief_text, max_repairs=args.max_repairs))
        except SystemExit:
            raise
        except Exception as exc:
            print(f"  option {spec['n']} ERRORED: {type(exc).__name__}: {exc}", flush=True)
            summaries.append({"n": spec["n"], "id": spec["id"], "name": spec["name"],
                              "ok": False, "error": f"{type(exc).__name__}: {exc}",
                              "gen_dir": str(HERE / "gens" / spec["id"])})

    (results_path).write_text(json.dumps(
        {"model": getattr(provider, "model", None), "heroes": summaries}, indent=2) + "\n")

    if not all(s.get("ok") for s in summaries):
        print("\nWARNING: not all heroes generated OK — assembling the ones that did.", flush=True)
    if not any((Path(s["gen_dir"]) / "hero-section.json").exists() for s in summaries):
        print("no heroes harvested — aborting assemble.")
        return 1
    ok_summaries = [s for s in summaries if (Path(s["gen_dir"]) / "hero-section.json").exists()]
    result = assemble(ok_summaries)
    _print_report(ok_summaries, result)
    return 0 if result["gate_pass"] else 1


def _print_report(summaries: list[dict], result: dict) -> None:
    print("\n================ SUMMARY ================")
    for s in summaries:
        print(f"  option {s['n']}: {s['name']}")
        print(f"      archetype={s.get('hero_archetype')} novelty={s.get('hero_novelty')} "
              f"surface={s.get('hero_surfaceIntent')} treatments={s.get('hero_treatments')} "
              f"offgrid={s.get('offgrid_treatments')}")
        print(f"      attempts={s.get('attempts')} repair_fired={s.get('repair_fired')} "
              f"wall={s.get('wall_s')}s out_tok={s.get('tokens',{}).get('output')}")
    print(f"\n  gate PASS: {result['gate_pass']}   hoisted nav: {result['hoisted_nav']}   "
          f"accent-class count: {result['accent_class_count']}")
    print(f"  page: {result['index_html']}")
    print(f"  screenshot: {result['screenshot_path']}")


if __name__ == "__main__":
    raise SystemExit(main())
