#!/usr/bin/env python3
"""build_harvest.py — WoodWave editorial-harvest proof harness (editorial-harvest-2026-07).

One section per HARVESTED pattern/treatment (G1–G9), plus the seeded LIVE-generation
proof runs. NOTHING here edits pipeline code — the harness only USES the composers /
generators, following the experiments/woodwave-showcase/build_showcase.py conventions
(deterministic pattern→section derivation with brand-authored copy, quiet divider
labels, gate-then-ship, shoot_reveal_safe screenshots, symlink Studio lanes).

Sub-commands:
  showcase — ONE page: measured opening bookend + one section per harvested pattern
             (card-over-portrait-statement, boundary-straddle-headline,
             framed-inset-monument, stepped-overlay-statement,
             type-behind-media-masthead, tucked-headline-panorama,
             staggered-caption-columns-3, seam-straddle-portrait), rendered through
             compose_from_composition and gated with --composition (incl. the new
             occlusion + band checks).
  live     — SEEDED LIVE generate_composition runs (novelty:adapt, seeds = the new
             standard patterns; real LLM, never hand-authored compositions).
  lane     — publish the gate-green pages as the Studio lane
             "WoodWave — harvested reference patterns" + verify HTTP 200.
  shots    — screenshot the published lane pages.
  report   — write REPORT.md from the accumulated results.json.

Usage: ./venv/bin/python experiments/woodwave-harvest/build_harvest.py <cmd> [...]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
BP = REPO / "brand_pipeline"
sys.path.insert(0, str(BP))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "experiments" / "woodwave-showcase"))
sys.path.insert(0, str(REPO / "experiments" / "woodwave-hero-gallery"))

import layout_library as ll                    # noqa: E402
import generate_composition as gc              # noqa: E402
import compose_from_composition as cfc         # noqa: E402
import compose_section as cs                   # noqa: E402
import build_showcase as bs                    # noqa: E402 (shared helpers, conventions)

BRAND_YAML = REPO / "runs" / "woodwave" / "brand" / "brand.yaml"
BRAND_DIR = BRAND_YAML.parent
STYLE = "editorial-luxury"
PAGES = HERE / "pages"
LIVE = HERE / "live"
RESULTS = HERE / "results.json"
PY = sys.executable

# The 8 harvested patterns, in page order, with the device(s) each one proves.
HARVEST_PATTERNS = [
    ("card-over-portrait-statement", "hero",    "G1 panel-on-media"),
    ("boundary-straddle-headline",   "hero",    "G2 straddle (z:front) + G3 scrim-band"),
    ("framed-inset-monument",        "hero",    "G4 framed + straddle bottom edge + G6 break-frame"),
    ("stepped-overlay-statement",    "hero",    "G7 stepped-lines"),
    ("type-behind-media-masthead",   "hero",    "G8 type-behind-media (occlusion contract)"),
    ("tucked-headline-panorama",     "hero",    "G2 straddle z:back tuck + G5 mixed-face"),
    ("staggered-caption-columns-3",  "gallery", "P1 per-column registered stagger"),
    ("seam-straddle-portrait",       "about",   "G9 banded seam + media-over-seam"),
]


def _load_results() -> dict:
    if RESULTS.exists():
        return json.loads(RESULTS.read_text())
    return {}


def _save_results(key: str, value) -> None:
    data = _load_results()
    data[key] = value
    RESULTS.write_text(json.dumps(data, indent=2) + "\n")


# ── deterministic derivation: pattern → composition.v1 section ─────────────────────
# Faithful to the pattern's contentShape (slots INCLUDING placement + registration) and
# specialTreatments; every copy string is BRAND-AUTHORED (voice.md §5 via
# compose_section.SECTION_COPY / LAYOUT_COPY) — never invented here.

_SLOT_KEYS = ("textLen", "sizeClass", "width", "mediaAspect", "z",
              "colStart", "colSpan", "rowSpan", "offsetCols", "offsetBaselines",
              "alignTo", "registration")


def _pattern(pid: str) -> ll.Pattern:
    p = ll.get({"lib": "standard", "id": pid}, BRAND_YAML)
    if p is None:
        raise SystemExit(f"standard pattern {pid} not found")
    return p


def _derive(pid: str, sid: str, copy_by_slot: dict, assets_by_slot: dict,
            *, extra_treatments: list | None = None,
            bands: dict | None = None, surface: str | None = None) -> dict:
    """ONE harvested pattern → ONE composition.v1 section. Slots keep the pattern's OWN
    placement vocabulary (colStart/colSpan/alignTo/registration); copy + assets are bound
    per slot name from the brand-authored sources passed in."""
    p = _pattern(pid)
    slots = []
    for s in p.slots:
        name = str(s.get("name"))
        slot = {"name": name, "role": str(s.get("role") or name),
                "contract": bs._slot_contract(s)}
        for k in _SLOT_KEYS:
            if s.get(k) is not None:
                slot[k] = s[k]
        if name in copy_by_slot:
            slot["copy"] = copy_by_slot[name]
        if slot["contract"] == "image":
            slot["asset"] = ({"src": f"assets/{assets_by_slot[name]}",
                              "alt": slot["role"]}
                             if name in assets_by_slot else None)
        slots.append(slot)
    treatments = [dict(t) for t in (p.special_treatments or [])]
    treatments += list(extra_treatments or [])
    sec = {
        "id": sid,
        "useCase": p.use_case,
        "archetype": p.archetype_ref,
        "surfaceIntent": surface or p.surface_intent or "any",
        "novelty": "reuse",
        "seededFrom": {"lib": "standard", "id": p.id},
        "slots": slots,
        "treatments": treatments,
        "knobs": {k: (v or {}).get("default") for k, v in (p.variant_knobs or {}).items()
                  if isinstance(v, dict) and v.get("default") is not None},
    }
    if bands:
        sec["bands"] = bands
    return sec


def _harvest_sections() -> list[tuple[str, str, dict]]:
    """(section id, divider label, section) per harvested pattern, brand copy only."""
    CSC, LC = cs.SECTION_COPY, cs.LAYOUT_COPY
    mission, collage = LC["mission-statement"], LC["editorial-collage"]
    info, gal = LC["info-band"], LC["gallery-showcase"]
    quote, cards = LC["curator-quote"], LC["demo-staggered-cards"]
    wordmark = CSC["wordmark"].upper()

    out: list[tuple[str, str, dict]] = []

    # 1 · G1 panel-on-media (ref #1): solid statement card over a full-bleed portrait.
    out.append(("hv-panel-on-media", "01 / card-over-portrait-statement / G1 panel-on-media", _derive(
        "card-over-portrait-statement", "hv-panel-on-media",
        {"wordmark": {"text": wordmark},
         "statement": {"heading": mission["heading"]},
         "caption": {"text": collage["caption"]}},
        {"canvas": "About-img-3.jpg"}, surface="primary")))

    # 2 · G2 z:front straddle + G3 scrim-band (ref #3): rail + seam heading + keyword scrim.
    out.append(("hv-straddle-scrim", "02 / boundary-straddle-headline / G2 straddle + G3 scrim-band", _derive(
        "boundary-straddle-headline", "hv-straddle-scrim",
        {"rail-eyebrow": {"text": info["eyebrow"]},
         "rail-body": {"text": quote["body"]},
         "rail-meta": {"text": collage["caption"]},
         "heading": {"heading": collage["heading"]},
         "keywords": [{"label": l, "text": v} for l, v in info["rows"][:3]]},
        {"photo": "Web-gallery-1.jpg"}, surface="primary")))

    # 3 · G4 framed + bottom-edge straddle (+ G6 break-frame demo, knob decoCount>0)
    # (ref #4): monument word registered to the framed photo's bottom edge.
    deco = {"name": "deco", "role": "corner decoration media", "contract": "image",
            "mediaAspect": "square", "width": "media", "colSpan": 2,
            "alignTo": {"corner": "tr"}, "z": "front", "asset": None}
    sec3 = _derive(
        "framed-inset-monument", "hv-framed-monument",
        {"monument": {"heading": wordmark},
         "annotation": {"text": collage["caption"]},
         "cue": {"text": gal["counter"]}},
        {"frame": "hero-staircase.jpg"},
        extra_treatments=[{"kind": "break-frame", "target": "deco",
                           "salience": "decorative",
                           "registration": {"toSlot": "frame", "edge": "top",
                                            "depthBaselines": 3, "z": "front"}}])
    sec3["slots"].append(deco)
    sec3["knobs"]["decoCount"] = 2
    out.append(("hv-framed-monument",
                "03 / framed-inset-monument / G4 framed + straddle + G6 break-frame", sec3))

    # 4 · G7 stepped-lines (ref #5): 3-line staircase statement on a full-bleed canvas.
    out.append(("hv-stepped-statement", "04 / stepped-overlay-statement / G7 stepped-lines", _derive(
        "stepped-overlay-statement", "hv-stepped-statement",
        {"statement": {"heading": mission["heading"]},
         "support": {"text": collage["caption"]},
         "action": {"label": mission["cta"]}},
        {"canvas": "About-img-5.jpg"}, surface="primary")))

    # 5 · G8 type-behind-media (ref #6): occluded masthead under a portrait stack.
    out.append(("hv-type-behind-media", "05 / type-behind-media-masthead / G8 occlusion contract", _derive(
        "type-behind-media-masthead", "hv-type-behind-media",
        {"eyebrow": {"text": collage["eyebrow"]},
         "monument": {"heading": wordmark + " GALLERY"},
         "caption-left": {"text": collage["caption"]},
         "caption-right": {"text": gal["counter"]}},
        {"media-main": "About-img-2.jpg", "media-detail": "About-img-4.jpg"},
        surface="primary")))

    # 6 · G2 z:back tuck + G5 mixed-face (ref #7): heading line sinks behind the panorama.
    sec6 = _derive(
        "tucked-headline-panorama", "hv-tucked-panorama",
        {"heading": {"heading": mission["heading"],
                     "lead": mission["heading"].split()[0],
                     "emphasis": " ".join(mission["heading"].split()[1:])},
         "support": {"text": mission["body"]}},
        {"panorama": "Web-gallery-1.jpg"},
        extra_treatments=[{"kind": "mixed-face", "target": "heading",
                           "spans": [{"part": "lead", "face": "roman"},
                                     {"part": "emphasis", "face": "italic"}]}],
        surface="primary")
    out.append(("hv-tucked-panorama",
                "06 / tucked-headline-panorama / G2 z-back tuck + G5 mixed-face", sec6))

    # 7 · P1 per-column registered stagger (ref #2): editorial 3-column index.
    sec7 = _derive(
        "staggered-caption-columns-3", "hv-staggered-columns",
        {"masthead": {"eyebrow": cards["eyebrow"], "heading": cards["heading"]},
         "masthead-caption": {"text": collage["caption"]}},
        {}, surface="primary")
    # the cards composer consumes ONE repeatable modules slot (heading/text/link per
    # module) — the established copy-array convention (build_showcase cards_section).
    sec7["slots"] = [
        {"name": "intro", "role": "section-title", "contract": "heading",
         "textLen": "short", "sizeClass": "title", "width": "hug", "z": "front",
         "copy": {"eyebrow": cards["eyebrow"], "heading": cards["heading"]}},
        {"name": "modules", "role": "module run", "contract": "feature-item",
         "textLen": "long", "sizeClass": "body", "width": "stretch", "z": "front",
         "copy": [{"heading": c["caption"], "text": c["body"],
                   **({"link": c["link"]} if c.get("link") else {})}
                  for c in cards["cards"]]
         + [{"heading": gal["caption"], "text": mission["body"]}]},
    ]
    out.append(("hv-staggered-columns",
                "07 / staggered-caption-columns-3 / P1 per-column registered stagger", sec7))

    # 8 · G9 banded seam (ref #8): photo band over panel band, portrait straddles the seam.
    out.append(("hv-seam-straddle", "08 / seam-straddle-portrait / G9 banded seam (media-over-seam)", _derive(
        "seam-straddle-portrait", "hv-seam-straddle",
        {"band-caption": {"text": collage["caption"]},
         "body": {"text": mission["body"]}},
        {"photo-band": "Web-gallery-1.jpg", "inset": "About-img-4.jpg"},
        bands={"split": 0.5, "surfaces": ["inverse", "panel"]},
        surface="primary")))
    return out


def cmd_showcase(args) -> int:
    print(f"=== HARVEST SHOWCASE :: {STYLE} (8 harvested patterns) ===")
    hero = bs._measured_hero_section()
    hero["id"] = "hv-hero"
    entries = _harvest_sections()
    sections = [hero] + [sec for _, _, sec in entries]
    comp = {
        "schemaVersion": "composition.v1",
        "brief": {"id": "woodwave-harvest-showcase",
                  "useCasesRequested": ["hero", "gallery", "about"]},
        "brand": {"ref": str(BRAND_YAML)},
        "style": {"id": STYLE},
        "sections": sections,
        "rationale": ("Editorial-harvest showcase: the measured opening bookend, then one "
                      "section per harvested reference pattern (G1-G9 devices), derived "
                      "deterministically from the standard-tier pattern contentShapes with "
                      "brand-authored copy."),
    }
    labels = [("hv-hero", "00 / measured opening bookend (accent hero)")]
    labels += [(sid, lab) for sid, lab, _ in entries]
    labels.append(("closing-bookend", "09 / closing bookend / brand footer (auto)"))

    out = PAGES / "harvest-showcase"
    out.mkdir(parents=True, exist_ok=True)
    (out / "composition.json").write_text(json.dumps(comp, indent=2) + "\n")
    cfc.render_composition(comp, BRAND_YAML, out, style_id=STYLE, brand_dir=BRAND_DIR)
    bs.inject_divider_shim(out / "index.html", labels)
    overall, failures = bs.gate_page(out, STYLE, composition=True)
    print(f"  gate: {'PASS' if overall else 'FAIL ' + str(failures)}")
    shot = bs.screenshot(out / "index.html", out / "screenshot.png")
    result = {"page": "harvest-showcase", "style": STYLE,
              "sections": [sid for sid, _, _ in entries],
              "devices": {pid: dev for pid, _, dev in HARVEST_PATTERNS},
              "gate_pass": bool(overall), "failures": failures, "screenshot": shot,
              "index_html": str(out / "index.html"),
              "fonts": bs.font_markers(out / "index.html")}
    _save_results("showcase", result)
    return 0 if overall else 1


# ── seeded LIVE generation (the PROOF: real LLM, seeded from the new patterns) ─────

LIVE_DIRECTIVES = {
    "harvest-1": (
        "USE THE HARVESTED OVERLAY DEVICES. Seed the hero from `card-over-portrait-"
        "statement` or `boundary-straddle-headline` (novelty:adapt) and keep its "
        "panel-on-media / straddle + scrim-band treatments. Include ONE `banded` "
        "section seeded from `seam-straddle-portrait` (bands + a media straddle "
        "registered to the seam). Everything else reuse/adapt from the seed list."),
    "harvest-2": (
        "USE THE OCCLUSION-CONTRACT DEVICES. Open with a hero seeded from "
        "`type-behind-media-masthead` (novelty:adapt): keep the type-behind-media "
        "treatment with maxOcclusion + endsVisible:true and the media span strictly "
        "inside the heading span; the hero's surfaceIntent MUST be exactly \"inverse\" "
        "(NOT inverse-strong). Include one section seeded from "
        "`tucked-headline-panorama` (z:back straddle tuck) or `framed-inset-monument` "
        "(framed width + bottom-edge straddle). EVERY text-target straddle / "
        "type-behind-media / text-on-media treatment MUST carry \"sanctioned\": true "
        "and live in the hero-family sections only. Keep the page LEAN — at most 6 "
        "sections, terse rationale, short copy — and everything else reuse/adapt."),
    "harvest-3": (
        "USE THE TYPOGRAPHIC DEVICES. Include a hero seeded from "
        "`stepped-overlay-statement` keeping its stepped-lines treatment, and a "
        "gallery seeded from `staggered-caption-columns-3` (keep the per-column "
        "stagger; you may carry its mixed-face masthead with copy {lead, emphasis}). "
        "Everything else reuse/adapt from the seed list."),
    "harvest-4": (
        "USE THE PANEL + TUCK DEVICES. Open with a hero seeded from "
        "`card-over-portrait-statement` (novelty:adapt): keep the panel-on-media "
        "treatment (solid panel over the full-bleed canvas, distribute space-between); "
        "the hero's surfaceIntent MUST be exactly \"inverse\". Include one section "
        "seeded from `tucked-headline-panorama`: keep its z:back straddle tuck with "
        "maxOcclusion {class: medium} + endsVisible:true, marked \"sanctioned\": true. "
        "You MAY add a break-frame treatment (salience \"decorative\", a small media "
        "slot with alignTo corner) on a framed section. Keep the page LEAN — at most "
        "6 sections, terse rationale, short copy — everything else reuse/adapt."),
}


def _harvest_seeds(doc) -> gc.SeedResult:
    """The normal per-use-case seeds PLUS every harvested pattern, so `seededFrom` can
    legally reference the new patterns and the constraint block describes them."""
    seeds = gc.seed_patterns(doc, BRAND_YAML)
    have = {p.id for p in seeds.patterns}
    for pid, _uc, _dev in HARVEST_PATTERNS:
        if pid not in have:
            seeds.patterns.append(_pattern(pid))
    seeds.block = ll.render_pattern_constraint(seeds.patterns)
    return seeds


def cmd_live(args) -> int:
    if not gc.load_api_keys():
        print(f"ERROR: ANTHROPIC_API_KEY not available (looked in {REPO / '.env.local'}).")
        return 3
    from screenshot_to_template.models.anthropic import AnthropicProvider
    provider = AnthropicProvider(args.model or gc.DEFAULT_MODEL,
                                 reasoning_effort=gc.DEFAULT_REASONING)
    print(f"Model: {provider.model}")
    doc = gc.load_brand(BRAND_YAML)
    seeds = _harvest_seeds(doc)
    print(f"Seed patterns: {', '.join(seeds.pattern_ids())}")
    brief_text = (BRAND_DIR / "brief.md").read_text()

    runs = list(LIVE_DIRECTIVES.items())
    if args.only:
        keep = set(args.only.split(","))
        runs = [r for r in runs if r[0] in keep]

    prior = {r["id"]: r for r in _load_results().get("live", [])}
    results = [v for k, v in prior.items() if k not in {rid for rid, _ in runs}]
    for rid, directive in runs:
        out_dir = LIVE / rid
        print(f"\n=== LIVE {rid} ===")
        t0 = time.time()
        try:
            res = gc.generate_composition(
                brief_text, BRAND_YAML, STYLE,
                out_dir=out_dir, brief_id=f"woodwave-harvest-{rid}",
                variety_directive=directive, max_repairs=args.max_repairs,
                provider=provider, seeds=seeds)
        except Exception as exc:
            print(f"  ERRORED: {type(exc).__name__}: {exc}")
            results.append({"id": rid, "ok": False,
                            "error": f"{type(exc).__name__}: {exc}"})
            continue
        wall = round(time.time() - t0, 1)
        comp = res.composition or {}
        secs = comp.get("sections", [])
        new_kinds = sorted({(t.get("kind") or "") for s in secs
                            for t in (s.get("treatments") or [])
                            if (t.get("kind") or "") in (
                                "straddle", "panel-on-media", "scrim-band", "framed",
                                "type-behind-media", "mixed-face", "stepped-lines",
                                "break-frame")})
        harvest_seeded = sorted({(s.get("seededFrom") or {}).get("id") for s in secs
                                 if isinstance(s.get("seededFrom"), dict)
                                 and (s.get("seededFrom") or {}).get("id")
                                 in {pid for pid, _, _ in HARVEST_PATTERNS}})
        shot = False
        if res.render_dir and (Path(res.render_dir) / "index.html").exists():
            shot = bs.screenshot(Path(res.render_dir) / "index.html",
                                 Path(res.render_dir) / "screenshot.png")
        results.append({
            "id": rid, "directive": directive, "ok": res.ok,
            "attempts": res.attempts, "wall_s": wall,
            "archetypes": [s.get("archetype") for s in secs],
            "harvest_seeded": harvest_seeded, "new_treatments_used": new_kinds,
            "n_sections": len(secs), "failures": res.failures, "screenshot": shot,
            "index_html": str(Path(res.render_dir) / "index.html")
            if res.render_dir else None,
            "fonts": bs.font_markers(Path(res.render_dir) / "index.html")
            if res.render_dir and (Path(res.render_dir) / "index.html").exists() else {},
        })
        print(f"  ok={res.ok} attempts={res.attempts} wall={wall}s "
              f"harvest_seeded={harvest_seeded} new_treatments={new_kinds}")
    _save_results("live", results)
    passes = sum(1 for r in results if r.get("ok"))
    print(f"\nlive: {passes}/{len(results)} gate-green")
    return 0


# ── lane + shots + report ──────────────────────────────────────────────────────────

LANE = "harvested-reference-patterns"
LANE_LABEL = "WoodWave — harvested reference patterns"


def cmd_lane(args) -> int:
    data = _load_results()
    published, skipped = [], []
    sc = data.get("showcase")
    if sc and sc.get("gate_pass"):
        bs._publish_lane(LANE, Path(sc["index_html"]).parent, LANE_LABEL)
        published.append({"lane": LANE, "label": LANE_LABEL,
                          "url": f"/runs/woodwave/brand/variants/{LANE}/index.html"})
    elif sc:
        skipped.append({"lane": LANE, "failures": sc.get("failures")})
    for r in data.get("live", []):
        if not r.get("ok") or not r.get("index_html"):
            skipped.append({"lane": f"{LANE}-{r['id']}", "failures": r.get("failures")})
            continue
        lane = f"{LANE}-{r['id']}"
        label = f"{LANE_LABEL} · live seed {r['id']}"
        bs._publish_lane(lane, Path(r["index_html"]).parent, label)
        published.append({"lane": lane, "label": label,
                          "url": f"/runs/woodwave/brand/variants/{lane}/index.html"})
    port = os.environ.get("STUDIO_PORT", "1500")
    for p in published:
        url = f"http://localhost:{port}{p['url']}"
        try:
            proc = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                   url], capture_output=True, text=True, timeout=15)
            p["http"] = proc.stdout.strip()
        except Exception as exc:
            p["http"] = f"error: {exc}"
        print(f"  {p['http']}  {p['lane']}")
    _save_results("lane", {"published": published, "skipped": skipped})
    return 1 if [p for p in published if p.get("http") != "200"] else 0


def cmd_shots(args) -> int:
    data = _load_results()
    shots = HERE / "shots"
    shots.mkdir(exist_ok=True)
    out = []
    for p in (data.get("lane") or {}).get("published", []):
        index = REPO / p["url"].lstrip("/")
        png = shots / f"{p['lane']}.png"
        ok = bs.screenshot(index, png)
        out.append({"lane": p["lane"], "screenshot": str(png) if ok else None,
                    "fonts": bs.font_markers(index) if index.exists() else {}})
    _save_results("shots", out)
    return 0


def cmd_report(args) -> int:
    # REPORT.md is written by the driving agent from results.json; keep a data dump here.
    print(json.dumps(_load_results(), indent=2)[:2000])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="WoodWave editorial-harvest proof harness.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("showcase")
    lv = sub.add_parser("live")
    lv.add_argument("--only", default="", help="comma list of run ids, e.g. harvest-1")
    lv.add_argument("--max-repairs", type=int, default=2)
    lv.add_argument("--model", default=None)
    sub.add_parser("lane")
    sub.add_parser("shots")
    sub.add_parser("report")
    args = ap.parse_args(argv)
    return {"showcase": cmd_showcase, "live": cmd_live, "lane": cmd_lane,
            "shots": cmd_shots, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
