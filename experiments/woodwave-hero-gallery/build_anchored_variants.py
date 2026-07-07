#!/usr/bin/env python3
"""build_anchored_variants.py — WoodWave hero: the MEASURED ORIGINAL + 5 ANCHORED
single-axis variations, each generated through the LIVE composition pipeline.

Supersedes the free-invention gallery (build_hero_gallery.py), whose heroes drifted
because they had variety directives but no seed. Here every variant is SEEDED with the
measured original hero pattern and pinned to novelty:"adapt".

SEED (provenance): project pattern `hero-display-over-staggered-media` in
runs/woodwave/brand/layout-library.yaml — origin: extracted, provenance: opening-bookend
(the real site's measured hero: centered gold Melodrama-on-dark display over two
staggered hard-edged photos). Resolved via the EXISTING seeding path:
generate_composition.seed_patterns(use_cases=["hero"]) → layout_library.match →
render_pattern_constraint; the model must cite it via seededFrom.

PER VARIANT (live): gc.generate_composition (one structured Anthropic call → jsonschema →
neverDo/off-grid prefilters → render via compose_from_composition → onbrand_check
--composition gate → ≤2 repair retries) with a directive that varies EXACTLY ONE axis.

DRIFT-BAND GATE (this script, on top of the pipeline gate):
  - anchor:  layout_library.score_pattern(seed, query_from_variant_hero) must be
    >= ADAPT_THRESHOLD (2.5) — below = un-anchored slop → REJECT + regenerate (≤2).
  - variation: the hero must differ from the measured baseline on at least one observable
    field (archetype / treatments / knobs / copy / asset) — byte-identical = no visible
    variation → REJECT + regenerate.

ASSEMBLY: ONE page — the measured original hero first (deterministically derived from the
seed pattern + the measured copy, labeled "Original (measured)"), then the 5 variants each
behind a "Variant N — <axis>" divider. Hoisted page-level nav once on top, shared footer
once at bottom, Melodrama hero 500 + gold #edd580 hover from the brand tokens. Gated with
onbrand_check --composition (must PASS).

Shared pipeline files are only USED, never edited. API key loads from ../../.env.local.

Usage:
  ./venv/bin/python experiments/woodwave-hero-gallery/build_anchored_variants.py                  # live
  ./venv/bin/python experiments/woodwave-hero-gallery/build_anchored_variants.py --assemble-only  # re-stitch
  ./venv/bin/python experiments/woodwave-hero-gallery/build_anchored_variants.py --offline-test   # original-only stitch, no API
  ./venv/bin/python experiments/woodwave-hero-gallery/build_anchored_variants.py --only 2,4       # regenerate subset
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
REPO = HERE.parent.parent
BP = REPO / "brand_pipeline"
sys.path.insert(0, str(BP))
sys.path.insert(0, str(REPO / "src"))

import generate_composition as gc               # noqa: E402
import compose_from_composition as cfc          # noqa: E402
import layout_library as ll                     # noqa: E402

# The CANONICAL WoodWave brand (read-only) — the same brand.yaml + project layout-library
# that rendered the hero the user calls good (runs/woodwave/brand/compose/full-editorial-luxury).
BRAND_YAML = REPO / "runs" / "woodwave" / "brand" / "brand.yaml"
STYLE_ID = "editorial-luxury"
SEED_PATTERN_ID = "hero-display-over-staggered-media"
BRIEF_MD = HERE / "anchored-brief.md"
SHOOT = REPO / "experiments" / "woodwave-ab" / "shoot_reveal_safe.mjs"

GENS = HERE / "gens-anchored"
PAGE_DIR = HERE / "page-anchored"

# The measured hero copy (from the real site / SECTION_COPY snapshot + opening-bookend
# blockMapping heading) — the baseline the variants deviate from on ONE axis only.
MEASURED_COPY = {
    "eyebrow": "Est. 2019 — Portland, Oregon",
    "headline": "WOODWAVE GALLERY",
    "subhead": "An evolving exhibition of woodgrain, light, and the quiet geometry of the handmade.",
    "cta": "Buy Tickets",
}

# 5 variants — each varies EXACTLY ONE axis off the seeded original, now expressed through
# the composition contract's PLACEMENT VOCABULARY (composition.v1 §4.6.5: colStart/colSpan,
# mediaAspect wide/pano, registration {toSlot,edge,depth*,z}, alignTo corners, z:back
# backgrounds, section alignment). All five stay on the `stack` archetype — the layered
# hero composer draws the declared geometry; no more nearest-expressible archetype swaps.
# The SHARED_TAIL keeps every variant pinned to the seed + measured copy + centered anchor.
_SHARED_TAIL = (
    " Keep the measured copy VERBATIM (eyebrow, headline, support, CTA), surfaceIntent "
    "\"inverse\", novelty:\"adapt\", seededFrom {\"lib\": \"project\", \"id\": "
    "\"hero-display-over-staggered-media\"}, alignment {\"anchor\": \"centered\"} (the "
    "original's centered treatment), and the pattern's overlap+stagger treatments. "
    "Everything else (palette, type tiers, spacing) identical to the seed.")

VARIANTS = [
    {"n": 1, "id": "v1-overlap-side", "axis": "overlap side — small image registered to the RIGHT edge",
     "expressibility": ("fully expressible: registration {toSlot, edge:\"right\", depthCols, "
                        "z} on the overlap slot (new §4.6.5 contract field; previously the "
                        "overlap side was a hardcoded composer offset)"),
     "directive": (
         "VARY ONLY THE OVERLAP-SIDE AXIS. Reuse the seeded hero pattern EXACTLY — same "
         "`stack` archetype, same slots (title, hero-media landscape, overlap-media "
         "portrait, subhead), asset:null everywhere (measured photography). Change ONE "
         "thing: the small overlap image registers to the main image's RIGHT edge — on the "
         "overlap-media slot declare colSpan 4 and registration {\"toSlot\": \"hero-media\", "
         "\"edge\": \"right\", \"depthCols\": 1, \"z\": \"front\"} so it crosses the right "
         "edge by one column (the mirror of the original's inset side)." + _SHARED_TAIL)},
    {"n": 2, "id": "v2-media-width", "axis": "media max-width — centered media at colSpan 9 (vs ~6), overlap preserved",
     "expressibility": ("fully expressible: colSpan on the hero-media slot (new §4.6.5 "
                        "contract field; previously the collage width was a fixed 80rem cap)"),
     "directive": (
         "VARY ONLY THE MEDIA MAX-WIDTH AXIS. Reuse the seeded hero pattern EXACTLY — same "
         "`stack` archetype, slots, asset:null (measured photography). Change ONE thing: "
         "the centered hero media widens to a 9-column span — on the hero-media slot "
         "declare colSpan 9 (vs the original's ~6-col reading), and PRESERVE the original's "
         "overlap registration by declaring on overlap-media: colSpan 4 and registration "
         "{\"toSlot\": \"hero-media\", \"edge\": \"bottom\", \"depthBaselines\": 10, "
         "\"z\": \"front\"} (the measured lower-edge crossing)." + _SHARED_TAIL)},
    {"n": 3, "id": "v3-aspect", "axis": "aspect ratio — pano main media, portrait inset, same placement",
     "expressibility": ("fully expressible: mediaAspect \"pano\"/\"portrait\" now resolves "
                        "to a REAL aspect-ratio (new §4.6.5 semantics; previously "
                        "mediaAspect was recorded but the variant ratio always won)"),
     "directive": (
         "VARY ONLY THE ASPECT-RATIO AXIS. Reuse the seeded hero pattern EXACTLY — same "
         "`stack` archetype, slots, asset:null (measured photography), SAME PLACEMENT as "
         "the original: hero-media KEEPS width \"media\" and z \"mid\" (a placed collage "
         "image — NOT width \"full-bleed\", NOT z \"back\", NO background layer; that is a "
         "different axis). Change ONE thing: the media proportions — on the hero-media "
         "slot declare mediaAspect \"pano\" (the placed image renders as a 3:1 panorama "
         "strip), and on the overlap-media slot declare mediaAspect \"portrait\" (the "
         "small inset reads as a 3:4 portrait) plus the measured registration "
         "{\"toSlot\": \"hero-media\", \"edge\": \"bottom\", \"depthBaselines\": 10, "
         "\"z\": \"front\"}." + _SHARED_TAIL)},
    {"n": 4, "id": "v4-image-count", "axis": "image count — three overlapping images, declared registration + z-order",
     "expressibility": ("fully expressible: MULTIPLE media slots with distinct registration "
                        "+ z (new §4.6.5 multi-layer semantics; previously the stack "
                        "composer drew exactly the hero/overlap pair)"),
     "directive": (
         "VARY ONLY THE IMAGE-COUNT AXIS. Reuse the seeded hero pattern — same `stack` "
         "archetype, title/subhead slots and copy unchanged. Change ONE thing: the media "
         "cluster grows to THREE overlapping images with declared registration and z-order, "
         "balanced left/right: (a) hero-media, landscape base, colSpan 8, asset:null; (b) "
         "overlap-media, portrait, colSpan 3, asset:null, registration {\"toSlot\": "
         "\"hero-media\", \"edge\": \"bottom\", \"depthBaselines\": 10, \"z\": \"front\"}; "
         "(c) a NEW third slot named \"counter-media\" (role \"overlap photography left\", "
         "contract \"image\", asset {\"src\": \"About-img-2.jpg\"}), colSpan 3, "
         "registration {\"toSlot\": \"hero-media\", \"edge\": \"left\", \"depthCols\": 1, "
         "\"z\": \"back\"} — a back layer crossing the left edge to counterweight the "
         "front-right inset." + _SHARED_TAIL)},
    {"n": 5, "id": "v5-background-corner", "axis": "background + corner — z:back full-bleed photo behind the heading, small z:front corner image",
     "expressibility": ("fully expressible: z:\"back\" + width:\"full-bleed\" renders a true "
                        "background layer (sanctioned text-on-media w/ scrim) and alignTo "
                        "{corner} pins a z:\"front\" image to the section frame (new §4.6.5 "
                        "semantics; previously no background/corner layer existed)"),
     "directive": (
         "VARY ONLY THE LAYERING AXIS (background + corner). Reuse the seeded hero pattern "
         "— same `stack` archetype, title/subhead slots and copy unchanged. Change ONE "
         "thing: the main image becomes a FULL-BLEED BACKGROUND behind the heading and a "
         "small image anchors in the bottom-right corner: (a) hero-media keeps role "
         "\"background photography\", asset:null, width \"full-bleed\", z \"back\" (the "
         "renderer scrims it so the text keeps contrast); declare the text-on-media "
         "treatment {\"kind\": \"text-on-media\", \"over\": \"background photography\", "
         "\"sanctioned\": true}; (b) overlap-media becomes the corner accent: colSpan 3, "
         "z \"front\", alignTo {\"corner\": \"br\"}, asset:null." + _SHARED_TAIL)},
]

DRIFT_LOW = ll.ADAPT_THRESHOLD          # 2.5 — below this vs the seed = un-anchored slop


# ── seed + baseline ─────────────────────────────────────────────────────────────

def load_seed() -> tuple[gc.SeedResult, ll.Pattern]:
    doc = gc.load_brand(BRAND_YAML)
    seeds = gc.seed_patterns(doc, BRAND_YAML, use_cases=["hero"])
    seed = next((p for p in seeds.patterns if p.id == SEED_PATTERN_ID), None)
    if seed is None:
        raise SystemExit(f"seed pattern {SEED_PATTERN_ID} did not resolve from "
                         f"{BRAND_YAML.parent / 'layout-library.yaml'}")
    return seeds, seed


def original_hero_section(seed: ll.Pattern, *, eyebrow_label: str | None = None) -> dict:
    """The measured original hero as a composition.v1 section — DERIVED deterministically
    from the seed pattern's contentShape/specialTreatments + the measured copy (never
    hand-invented structure). Renders through the same stack-hero composer that drew the
    page the user calls good."""
    slot_contract = {"wordmark": "logo", "title": "heading", "hero-media": "image",
                     "overlap-media": "image", "subhead": "paragraph"}
    slots = []
    for s in seed.slots:
        name = str(s.get("name"))
        slot = {"name": name, "role": str(s.get("role") or name),
                "contract": slot_contract.get(name, "paragraph"),
                "textLen": str(s.get("textLen") or "none"),
                "sizeClass": str(s.get("sizeClass") or "body"),
                "width": str(s.get("width") or "hug"),
                "z": str(s.get("z") or "front")}
        if s.get("mediaAspect"):
            slot["mediaAspect"] = str(s["mediaAspect"])
            slot["asset"] = None            # renderer supplies the measured photography
        if name == "title":
            slot["copy"] = {"heading": MEASURED_COPY["headline"]}
        elif name == "subhead":
            slot["copy"] = {"text": MEASURED_COPY["subhead"]}
        slots.append(slot)
    if eyebrow_label:
        slots.insert(0, {"name": "eyebrow", "role": "eyebrow", "contract": "caption",
                         "textLen": "short", "sizeClass": "caption", "width": "hug",
                         "z": "front", "copy": {"text": eyebrow_label}})
    knobs = {k: (v or {}).get("default") for k, v in (seed.variant_knobs or {}).items()
             if isinstance(v, dict) and v.get("default") is not None}
    return {
        "id": "hero-original", "useCase": "hero", "archetype": seed.archetype_ref,
        "surfaceIntent": "inverse", "novelty": "reuse",
        "seededFrom": {"lib": "project", "id": seed.id},
        "slots": slots,
        "treatments": [dict(t) for t in (seed.special_treatments or [])],
        "knobs": knobs,
    }


# ── drift-band gate ─────────────────────────────────────────────────────────────

def _query_from_section(section: dict) -> ll.Query:
    """Retrieval Query from a composition section (mirrors the woodwave-hybrid harness) so
    the SAME layout_library scorer that ranks reuse candidates measures a variant's
    structural distance from the measured seed."""
    slots = section.get("slots") or []
    textlens, has_media = [], False
    for s in slots:
        tl = ll._textlen_for(str(s.get("role", "")), str(s.get("contract", "")))
        if tl != "none":
            textlens.append(tl)
        if s.get("mediaAspect") or "image" in str(s.get("contract", "")).lower() \
                or str(s.get("width")) == "media":
            has_media = True
    treatments = {str(t.get("kind")) for t in (section.get("treatments") or [])
                  if isinstance(t, dict) and t.get("kind")}
    surf = str(section.get("surfaceIntent") or "any")
    return ll.Query(use_case="hero", textlens=textlens, has_media=has_media,
                    treatments=treatments, surface_intent=surf,
                    archetype=str(section.get("archetype") or ""))


def _slot_texts(section: dict) -> list[str]:
    out = []
    for s in (section.get("slots") or []):
        c = s.get("copy")
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, dict):
            out += [str(v) for v in c.values() if isinstance(v, str)]
        elif isinstance(c, list):
            for m in c:
                if isinstance(m, dict):
                    out += [str(v) for v in m.values() if isinstance(v, str)]
    return sorted(t.strip() for t in out if t and t.strip())


def _asset_srcs(section: dict) -> list[str]:
    out = []
    for s in (section.get("slots") or []):
        a = s.get("asset")
        if isinstance(a, dict) and a.get("src"):
            out.append(str(a["src"]))
    return sorted(out)


def _placements(section: dict) -> dict:
    """The section's declared PLACEMENT geometry (composition.v1 §4.6.5) keyed by slot:
    colStart/colSpan/offset*/alignTo/registration + mediaAspect/z/width, plus the
    section-level grid/alignment. This is the observable-variation surface for the new
    contract axes (a side flip or aspect change is pure placement — no copy/asset delta)."""
    keys = ("colStart", "colSpan", "rowSpan", "offsetCols", "offsetBaselines",
            "alignTo", "registration", "mediaAspect", "z", "width")
    out: dict = {"_grid": section.get("grid"), "_alignment": section.get("alignment")}
    for s in (section.get("slots") or []):
        p = {k: s[k] for k in keys if s.get(k) is not None}
        if p:
            out[str(s.get("name") or s.get("role") or "slot")] = p
    return out


def variation_delta(variant: dict, baseline: dict) -> list[str]:
    """Observable differences between a variant hero and the measured baseline. Empty ==
    near-identical (no visible variation)."""
    deltas = []
    if str(variant.get("archetype")) != str(baseline.get("archetype")):
        deltas.append(f"archetype {baseline.get('archetype')}→{variant.get('archetype')}")
    vt = sorted({str(t.get('kind')) for t in (variant.get('treatments') or []) if isinstance(t, dict)})
    bt = sorted({str(t.get('kind')) for t in (baseline.get('treatments') or []) if isinstance(t, dict)})
    if vt != bt:
        deltas.append(f"treatments {bt}→{vt}")
    if (variant.get("knobs") or {}) != (baseline.get("knobs") or {}):
        deltas.append("knobs changed")
    vp, bp = _placements(variant), _placements(baseline)
    if vp != bp:
        changed = sorted(k for k in (set(vp) | set(bp)) if vp.get(k) != bp.get(k)
                         and not (k == "_alignment"          # centered == the original's own anchor
                                  and (vp.get(k) or {}).get("anchor") == "centered"
                                  and bp.get(k) is None))
        if changed:
            deltas.append(f"placement changed ({', '.join(changed)})")
    if len(variant.get("slots") or []) != len(baseline.get("slots") or []):
        deltas.append(f"slot count {len(baseline.get('slots') or [])}→{len(variant.get('slots') or [])}")
    if _slot_texts(variant) != _slot_texts(baseline):
        deltas.append("copy changed")
    if _asset_srcs(variant) != _asset_srcs(baseline):
        deltas.append(f"assets {_asset_srcs(baseline) or '[measured defaults]'}→"
                      f"{_asset_srcs(variant) or '[measured defaults]'}")
    return deltas


def drift_check(variant_hero: dict, seed: ll.Pattern, baseline: dict) -> dict:
    q = _query_from_section(variant_hero)
    score = ll.score_pattern(seed, q)
    deltas = variation_delta(variant_hero, baseline)
    anchored = score >= DRIFT_LOW
    varied = bool(deltas)
    ok = anchored and varied
    reason = "" if ok else ("drifted below the adapt band (slop)" if not anchored
                            else "near-identical to the measured original (no visible variation)")
    return {"score": round(score, 2), "band_low": DRIFT_LOW, "anchored": anchored,
            "varied": varied, "deltas": deltas, "ok": ok, "reason": reason}


# ── generation (live pipeline + drift-band repair wrapper) ──────────────────────

def _extract_hero(comp: dict) -> dict | None:
    for s in (comp.get("sections") or []):
        if gc._is_hero_section(s):
            return s
    secs = comp.get("sections") or []
    return secs[0] if secs else None


def generate_variant(spec: dict, *, provider, seeds, seed_pattern, baseline,
                     brief_text: str, max_repairs: int, drift_retries: int = 2) -> dict:
    out_root = GENS / spec["id"]
    telemetry_all = []
    drift = None
    hero = None
    gate_ok = False
    attempts_total = 0
    for round_i in range(drift_retries + 1):
        out_dir = out_root if round_i == 0 else out_root / f"drift-retry-{round_i}"
        directive = spec["directive"]
        if drift and not drift["ok"]:
            directive += (f"\n# DRIFT REPAIR — your previous variant was rejected: "
                          f"{drift['reason']} (anchor score {drift['score']}, band floor "
                          f"{DRIFT_LOW}; deltas seen: {drift['deltas'] or 'none'}). Re-emit the "
                          f"variant CLOSER to the seeded pattern but with the ONE directed "
                          f"axis clearly varied.")
        print(f"\n=== GEN Variant {spec['n']} :: {spec['axis']}"
              + (f"  [drift retry {round_i}]" if round_i else "") + " ===", flush=True)
        t0 = time.time()
        res = gc.generate_composition(
            brief_text, BRAND_YAML, STYLE_ID,
            out_dir=out_dir, brief_id=f"woodwave-hero-anchored-v{spec['n']}",
            variety_directive=directive, max_repairs=max_repairs,
            provider=provider, seeds=seeds)
        wall = round(time.time() - t0, 1)
        attempts_total += res.attempts
        telemetry_all += res.telemetry
        comp = res.composition or {}
        hero = _extract_hero(comp)
        gate_ok = res.ok
        if hero is None:
            drift = {"ok": False, "reason": "no hero section emitted", "score": None,
                     "deltas": [], "anchored": False, "varied": False, "band_low": DRIFT_LOW}
            continue
        drift = drift_check(hero, seed_pattern, baseline)
        print(f"  gen ok={res.ok} attempts={res.attempts} wall={wall}s | drift score="
              f"{drift['score']} anchored={drift['anchored']} deltas={drift['deltas']}", flush=True)
        if drift["ok"]:
            break
        print(f"  DRIFT REJECT: {drift['reason']}", flush=True)
    if hero is not None:
        (out_root / "hero-section.json").write_text(json.dumps(hero, indent=2) + "\n")
    total_in = sum((t.get("input_tokens") or 0) for t in telemetry_all)
    total_out = sum((t.get("output_tokens") or 0) for t in telemetry_all)
    return {
        "n": spec["n"], "id": spec["id"], "axis": spec["axis"],
        "expressibility": spec["expressibility"],
        "gen_gate_ok": gate_ok, "attempts": attempts_total,
        "repair_fired": attempts_total > 1,
        "drift": drift,
        "hero_archetype": (hero or {}).get("archetype"),
        "hero_novelty": (hero or {}).get("novelty"),
        "hero_seededFrom": (hero or {}).get("seededFrom"),
        "hero_treatments": sorted({t.get("kind") for t in (hero or {}).get("treatments", [])
                                   if isinstance(t, dict) and t.get("kind")}),
        "tokens": {"input": total_in, "output": total_out},
        "gen_dir": str(out_root),
    }


# ── assembly ────────────────────────────────────────────────────────────────────

def _adapt_slot_roles(hero: dict) -> dict:
    """RETIRED role-rename workarounds (grid/overlap contract upgrade): the adapter's
    copy translators now read the synonymous roles themselves — 'support' joined the hero
    lede keyword set, and the interlock translator looks captions up by slot NAME and
    eyebrow role too (compose_from_composition composer-gap fixes #1/#2). Kept as a
    pass-through so assembly's call sites stay stable; renames nothing anymore."""
    return hero


def _divider_section(sid: str, label: str, description: str) -> dict:
    """QUIET labeled divider rendered by the generic-flow safety net (unmapped archetype).
    Deliberately carries NO heading contract — only caption/paragraph primitives — so it
    can never render display-tier type and be mistaken for a hero. The thin rule +
    minimal padding come from the gallery-comparison shim (divider-scoped, color/spacing
    only)."""
    return {
        "id": sid, "useCase": "about", "archetype": "label-divider", "surfaceIntent": "primary",
        "novelty": "adapt", "seededFrom": None,
        "slots": [
            {"name": "label", "role": "eyebrow label", "contract": "caption",
             "textLen": "short", "sizeClass": "caption", "width": "hug", "z": "front",
             "copy": {"text": label}},
            {"name": "description", "role": "supporting note", "contract": "paragraph",
             "textLen": "short", "sizeClass": "caption", "width": "hug", "z": "front",
             "copy": {"text": description}},
        ],
        "treatments": [], "knobs": {"align": "left"},
    }


def _split_axis(axis: str) -> tuple[str, str]:
    """'scale — monumental one-word headline…' -> ('Scale', 'Monumental one-word headline…')."""
    name, _, desc = axis.partition(" — ")
    name = name.strip().capitalize()
    desc = desc.strip()
    desc = (desc[:1].upper() + desc[1:] + ".") if desc else ""
    return name, desc


def assemble(summaries: list[dict], seed: ll.Pattern) -> dict:
    # PER-SECTION COPY IS NOW A CONTRACT REALITY (composer-gap #1 fixed: hero copy binds
    # via LAYOUT_COPY[section id]), so the "Original (measured)" tag is BAKED INTO the
    # original's own eyebrow copy — it can no longer leak onto the variants, and the old
    # shim ::before workaround is retired.
    baseline = original_hero_section(
        seed, eyebrow_label=f"Original (measured) · {MEASURED_COPY['eyebrow']}")
    sections: list[dict] = [baseline]
    for s in summaries:
        hero_path = Path(s["gen_dir"]) / "hero-section.json"
        if not hero_path.exists():
            print(f"  WARNING: variant {s['n']} has no harvested hero — skipped in assembly")
            continue
        hero = _adapt_slot_roles(_copy.deepcopy(json.loads(hero_path.read_text())))
        hero["id"] = f"hero-v{s['n']}"
        hero["useCase"] = "hero"
        # COMPARISON GALLERY (user directive): EVERY hero renders in the original's
        # treatment — dark inverse surface + gold accent display heading. The page-level
        # single-accent invariant cannot hold on a side-by-side gallery, so invariants are
        # gated per-hero as 6 standalone bookends instead (gate_standalones).
        hero["surfaceIntent"] = "inverse"
        # PER-SECTION ALIGNMENT IS NOW A CONTRACT LEVER (composer-gap #4 fixed): mid-page
        # heroes declare the original's centered anchor through `alignment` instead of the
        # retired shim centering rules (the directives already ask for it; default it here
        # so a model omission can't silently left-cram a hero against the style default).
        if str(hero.get("archetype")) == "stack":
            hero.setdefault("alignment", {"anchor": "centered"})
        axis_name, axis_desc = _split_axis(s["axis"])
        sections.append(_divider_section(f"divider-v{s['n']}",
                                         f"Variant {s['n']} — {axis_name}", axis_desc))
        sections.append(hero)

    comp = {
        "schemaVersion": "composition.v1",
        "brief": {"id": "woodwave-hero-anchored", "useCasesRequested": ["hero"]},
        "brand": {"ref": str(BRAND_YAML)},
        "style": {"id": STYLE_ID},
        "sections": sections,
        "rationale": ("The measured WoodWave hero (seed pattern "
                      f"{SEED_PATTERN_ID}) followed by 5 anchored single-axis variations, "
                      "each live-generated with the seed + novelty:adapt and passed through "
                      "the drift-band gate. Only the opening measured hero carries the "
                      "inverse surface + gold accent (single-accent invariant)."),
    }

    PAGE_DIR.mkdir(parents=True, exist_ok=True)
    print("\n=== ASSEMBLE :: original + 5 anchored variants (all dark+gold) ===", flush=True)
    cfc.render_composition(comp, BRAND_YAML, PAGE_DIR, style_id=STYLE_ID,
                           brand_dir=BRAND_YAML.parent)
    if _heal_broken_assets(comp, PAGE_DIR):
        cfc.render_composition(comp, BRAND_YAML, PAGE_DIR, style_id=STYLE_ID,
                               brand_dir=BRAND_YAML.parent)
    inject_comparison_shim(PAGE_DIR / "index.html", dividers=True)
    # The comparison gallery is expected to fail the page-level single-accent invariant
    # (6 accent bookends side by side); it is recorded honestly and covered by the
    # per-hero standalone gates.
    overall, failures, scorecard = gc.gate_composition(
        PAGE_DIR, BRAND_YAML, STYLE_ID, layout="opening-bookend")
    print(f"  gate (--composition, comparison artifact): "
          f"{'PASS' if overall else 'FAIL ' + str(failures)}", flush=True)

    facts = _hero_page_facts(PAGE_DIR / "index.html")
    print(f"  hoisted nav={facts['hoisted_nav']}  heroes-inverse={facts['all_heroes_inverse']} "
          f"({len(facts['hero_sections'])} heroes)  accent-classes={facts['accent_class_count']}  "
          f"gold-hover={facts['gold_hover']}  melodrama-500={facts['melodrama_500']}  "
          f"shim={facts['shim']}")

    shot = screenshot(PAGE_DIR / "index.html", PAGE_DIR / "screenshot.png")
    result = {
        "gate_pass": bool(overall), "failures": failures,
        **facts,
        "screenshot": shot,
        "index_html": str(PAGE_DIR / "index.html"),
        "screenshot_path": str(PAGE_DIR / "screenshot.png"),
        "order": [sec.get("id") for sec in sections],
    }
    (PAGE_DIR / "assemble-summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def _accent_hex() -> str:
    """The brand's committed accent (tokens/colors/accent/highlight) — read from
    brand.yaml, never invented."""
    doc = gc.load_brand(BRAND_YAML)
    return str(doc["tokens"]["colors"]["accent/highlight"]["value"])


def inject_comparison_shim(index_html: Path, *, dividers: bool = False) -> None:
    """Append the gallery-comparison shim to a rendered page — brand token values, no new
    classes/markup: on this side-by-side gallery every hero mirrors the original's
    treatment (gold accent display heading on the dark inverse surface — the renderer's
    page contract commits the accent to ONE bookend, which is correct for real pages but
    not for a comparison artifact). ``dividers=True`` (assembled gallery only — standalone
    gate pages have no dividers) additionally styles the variant-label dividers as QUIET
    caption-scale strips (thin rule, minimal on-scale padding) so only the six heroes
    carry display-scale type. Idempotent."""
    html = index_html.read_text()
    if 'id="gallery-comparison-shim"' in html:
        return
    divider_css = """
/* RETIRED INTO THE CONTRACT (grid/overlap upgrade): the per-variant centering rules that
   used to live here are now the sections' own `alignment: {anchor: centered}` declaration
   (composer-gap #4 fix), and the original's "Original (measured)" label is baked into its
   per-section eyebrow copy (composer-gap #1 fix) — neither needs a shim anymore. */
/* quiet variant-label dividers: caption-scale type + thin rule + minimal padding
   (brand spacing-scale values), so dividers can never read as heroes. */
[data-layout^="divider-"] .cs-section {
  padding: 1.5rem clamp(1.5rem, 6cqw, 4rem) 1.5rem; }
[data-layout^="divider-"] .cs-flow { gap: 0rem; }
[data-layout^="divider-"] .cs-flow::before {
  content: ""; display: block; width: 100%; height: 1px; background: var(--c-ink);
  margin-bottom: 0.75rem; }
[data-layout^="divider-"] .cs-flow-item { margin: 0; }
[data-layout^="divider-"] .c-caption {
  text-transform: uppercase; letter-spacing: 0.14em; color: var(--c-ink); }
[data-layout^="divider-"] .c-paragraph {
  font-size: var(--c-eyebrow-size); color: var(--c-ink-muted);
  margin-top: 0.35rem; max-width: 60ch; }
""" if dividers else ""
    shim = f"""<style id="gallery-comparison-shim">
/* provenance: preview-chrome — gallery-comparison shim appended by
   build_anchored_variants.py, not a pipeline change: every hero shows the original's
   dark+gold treatment side by side (the page contract deliberately commits the accent
   to ONE bookend, which is correct for real pages but not for a comparison artifact),
   and the variant-label dividers are quiet caption-scale gallery furniture. Accent =
   tokens/colors/accent/highlight. Composition invariants are gated per-hero standalone
   (standalone-gates/). The per-section centering + per-section copy workarounds that
   used to live here are RETIRED — expressed through the composition contract now. */
[data-layout^="hero-"] .c-heading--display {{ color: {_accent_hex()}; }}{divider_css}</style>
"""
    index_html.write_text(html.replace("</head>", shim + "</head>", 1))


def _hero_page_facts(index_html: Path) -> dict:
    html = index_html.read_text()
    low = html.lower()
    hero_layouts = re.findall(r'data-layout="(hero-[^"]+)"[^>]*data-surface="([^"]+)"', html)
    return {
        "hero_sections": [{"layout": h, "surface": s} for h, s in hero_layouts],
        "all_heroes_inverse": bool(hero_layouts) and all("inverse" in s for _, s in hero_layouts),
        "accent_class_count": len(re.findall(r'class="[^"]*--accent\b', low)),
        "shim": 'id="gallery-comparison-shim"' in html,
        "hoisted_nav": '<div id="page-nav"' in html,
        "gold_hover": "--c-link-hover: #edd580" in html,
        "melodrama_500": "--c-display-weight: 500" in html,
        "gold_heading_rule": f".c-heading--display {{ color: {_accent_hex()}; }}" in html
                             or "c-heading--accent" in low,
    }


def gate_standalones(summaries: list[dict], seed: ll.Pattern) -> list[dict]:
    """Gate EVERY hero (original + 5 variants, all forced to the original's inverse
    treatment) as its OWN standalone page — each is then a legal single inverse accent
    bookend, so the single-accent invariant is honestly enforced per hero rather than
    faked on the comparison gallery. Also produces the per-hero dark screenshots."""
    out_root = HERE / "standalone-gates"
    shots = HERE / "anchored-shots"
    shots.mkdir(exist_ok=True)
    jobs = [("original", original_hero_section(seed))]
    for s in summaries:
        hero_path = Path(s["gen_dir"]) / "hero-section.json"
        if not hero_path.exists():
            continue
        hero = _adapt_slot_roles(_copy.deepcopy(json.loads(hero_path.read_text())))
        hero["id"] = f"hero-v{s['n']}"
        hero["useCase"] = "hero"
        hero["surfaceIntent"] = "inverse"
        jobs.append((s["id"], hero))

    results = []
    for name, hero in jobs:
        outdir = out_root / name
        comp = {
            "schemaVersion": "composition.v1",
            "brief": {"id": f"woodwave-hero-anchored-standalone-{name}",
                      "useCasesRequested": ["hero"]},
            "brand": {"ref": str(BRAND_YAML)},
            "style": {"id": STYLE_ID},
            "sections": [hero],
            "rationale": ("standalone single-bookend gate for the comparison gallery: "
                          f"hero '{name}' in the original's inverse+accent treatment"),
        }
        outdir.mkdir(parents=True, exist_ok=True)
        cfc.render_composition(comp, BRAND_YAML, outdir, style_id=STYLE_ID,
                               brand_dir=BRAND_YAML.parent)
        inject_comparison_shim(outdir / "index.html")
        overall, failures, _ = gc.gate_composition(outdir, BRAND_YAML, STYLE_ID,
                                                   layout="opening-bookend")
        facts = _hero_page_facts(outdir / "index.html")
        shot = shots / f"{name}-dark.png"
        screenshot(outdir / "index.html", shot)
        results.append({"hero": name, "gate_pass": bool(overall), "failures": failures,
                        "inverse": facts["all_heroes_inverse"],
                        "accent_class_count": facts["accent_class_count"],
                        "page": str(outdir / "index.html"), "screenshot": str(shot)})
        print(f"  standalone {name}: gate={'PASS' if overall else 'FAIL ' + str(failures)} "
              f"inverse={facts['all_heroes_inverse']} accents={facts['accent_class_count']}")
    return results


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
        print(f"  self-heal: nulled {healed} unresolved asset(s) {sorted(broken)}")
    return healed > 0


def screenshot(index_html: Path, out_png: Path) -> bool:
    if not SHOOT.exists():
        print(f"  screenshot skipped — {SHOOT} not found")
        return False
    import os
    env = {k: v for k, v in os.environ.items() if k != "PLAYWRIGHT_BROWSERS_PATH"}
    try:
        proc = subprocess.run(["node", str(SHOOT), str(index_html), str(out_png), "1440", "900"],
                              cwd=str(SHOOT.parent), capture_output=True, text=True,
                              timeout=180, env=env)
    except Exception as exc:
        print(f"  screenshot failed: {type(exc).__name__}: {exc}")
        return False
    if proc.returncode != 0 or not out_png.exists():
        print(f"  screenshot failed (rc={proc.returncode}): "
              f"{(proc.stderr or proc.stdout).strip()[:200]}")
        return False
    print(f"  screenshot → {out_png}")
    return True


# ── main ────────────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the anchored WoodWave hero-variants page.")
    ap.add_argument("--assemble-only", action="store_true")
    ap.add_argument("--offline-test", action="store_true",
                    help="stitch ONLY the measured original (no model call) to validate assembly")
    ap.add_argument("--only", default="", help="comma list of variant numbers to (re)generate")
    ap.add_argument("--max-repairs", type=int, default=2)
    ap.add_argument("--model", default=None)
    ap.add_argument("--reasoning", default=None)
    args = ap.parse_args(argv)

    seeds, seed = load_seed()
    print(f"Seed: [{seed.lib}] {seed.id} (archetype {seed.archetype_ref}, "
          f"surface {seed.surface_intent}) — provenance: {seed.provenance}")
    results_path = HERE / "anchored-results.json"

    if args.offline_test:
        result = assemble([], seed)
        print(f"\n  gate PASS: {result['gate_pass']}  nav: {result['hoisted_nav']}  "
              f"accents: {result['accent_class_count']}")
        return 0 if result["gate_pass"] else 1

    if args.assemble_only:
        summaries = json.loads(results_path.read_text())["variants"]
        result = assemble(summaries, seed)
        print("\n=== STANDALONE GATES (one inverse bookend per page) ===", flush=True)
        standalones = gate_standalones(summaries, seed)
        (HERE / "standalone-gates" / "results.json").write_text(
            json.dumps(standalones, indent=2) + "\n")
        _print_report(summaries, result, standalones)
        return 0 if all(r["gate_pass"] for r in standalones) else 1

    brief_text = BRIEF_MD.read_text()
    if not gc.load_api_keys():
        print(f"ERROR: ANTHROPIC_API_KEY not available (looked in {REPO / '.env.local'}).")
        return 3
    from screenshot_to_template.models.anthropic import AnthropicProvider
    provider = AnthropicProvider(args.model or gc.DEFAULT_MODEL,
                                 reasoning_effort=args.reasoning or gc.DEFAULT_REASONING)
    print(f"Model: {provider.model}")
    baseline = original_hero_section(seed)

    only = {int(x) for x in args.only.split(",") if x.strip()} if args.only else None
    prior = {}
    if results_path.exists():
        prior = {v["n"]: v for v in json.loads(results_path.read_text()).get("variants", [])}

    summaries = []
    for spec in VARIANTS:
        if only and spec["n"] not in only and spec["n"] in prior:
            summaries.append(prior[spec["n"]]); continue
        try:
            summaries.append(generate_variant(
                spec, provider=provider, seeds=seeds, seed_pattern=seed, baseline=baseline,
                brief_text=brief_text, max_repairs=args.max_repairs))
        except Exception as exc:
            print(f"  variant {spec['n']} ERRORED: {type(exc).__name__}: {exc}", flush=True)
            summaries.append({"n": spec["n"], "id": spec["id"], "axis": spec["axis"],
                              "error": f"{type(exc).__name__}: {exc}",
                              "gen_dir": str(GENS / spec["id"])})

    results_path.write_text(json.dumps(
        {"model": provider.model, "seed": {"id": seed.id, "lib": seed.lib,
                                           "provenance": seed.provenance},
         "variants": summaries}, indent=2) + "\n")

    result = assemble(summaries, seed)
    print("\n=== STANDALONE GATES (one inverse bookend per page) ===", flush=True)
    standalones = gate_standalones(summaries, seed)
    (HERE / "standalone-gates" / "results.json").write_text(
        json.dumps(standalones, indent=2) + "\n")
    _print_report(summaries, result, standalones)
    return 0 if all(r["gate_pass"] for r in standalones) else 1


def _print_report(summaries: list[dict], result: dict,
                  standalones: list[dict] | None = None) -> None:
    print("\n================ SUMMARY ================")
    for s in summaries:
        d = s.get("drift") or {}
        print(f"  V{s['n']}: {s['axis']}")
        print(f"      archetype={s.get('hero_archetype')} novelty={s.get('hero_novelty')} "
              f"seededFrom={s.get('hero_seededFrom')}")
        print(f"      drift score={d.get('score')} (floor {d.get('band_low')}) "
              f"anchored={d.get('anchored')} deltas={d.get('deltas')}")
        print(f"      gen gate ok={s.get('gen_gate_ok')} attempts={s.get('attempts')} "
              f"repair_fired={s.get('repair_fired')} out_tok={s.get('tokens', {}).get('output')}")
    print(f"\n  assembled page gate: {'PASS' if result['gate_pass'] else 'FAIL ' + str(result['failures'])}"
          f" (comparison artifact)  nav: {result['hoisted_nav']}  "
          f"heroes-inverse: {result.get('all_heroes_inverse')}  "
          f"accents: {result['accent_class_count']}  gold-hover: {result['gold_hover']}  "
          f"melodrama-500: {result['melodrama_500']}")
    if standalones is not None:
        npass = sum(1 for r in standalones if r["gate_pass"])
        print(f"  standalone gates: {npass}/{len(standalones)} PASS")
        for r in standalones:
            print(f"    {r['hero']}: {'PASS' if r['gate_pass'] else 'FAIL ' + str(r['failures'])} "
                  f"(inverse={r['inverse']}, accents={r['accent_class_count']})")
    print(f"  page: {result['index_html']}")
    print(f"  screenshot: {result['screenshot_path']}")


if __name__ == "__main__":
    raise SystemExit(main())
