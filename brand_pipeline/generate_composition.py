#!/usr/bin/env python3
"""generate_composition.py - Phase 1C SCAFFOLD: the seeding hook + prompt builder for the
hybrid `composition.v1` generator.

THE HYBRID (approved in experiments/woodwave-ab/REPORT.md): the generation AI emits a
STRUCTURED ``composition.v1`` object (ordered sections -> archetype/slots + primitive/block
refs + treatments + inline copy; see brand_pipeline/spec/composition-schema.md +
composition.v1.schema.json), which the deterministic renderer draws and onbrand_check.py
validates -- NOT raw HTML. This module deterministically ASSEMBLES the prompt the model will
answer and REVIVES the (previously dead) reuse-constraint seeder so the model is biased
toward library reuse while still free to propose novel structures.

WHAT THIS FILE DOES (Phase 1C):
  - ``seed_patterns(doc, brand_yaml_path)`` -> for each candidate use-case, calls
    ``layout_library.match(query_from_layout(...))`` and passes the resolved patterns
    through the REVIVED ``layout_library.render_pattern_constraint([...])`` to produce the
    "REUSE these patterns; tune only these knobs; you MAY depart with novelty:novel" seed
    block. Seeds BIAS, they do not CAGE.
  - ``build_prompt(brief_text, brand_yaml_path, style_id, seeds)`` -> deterministically
    assembles the system/user prompt from: the brief copy, brand.yaml (token roles /
    neverDo / measured type tiers / spacing steps), the merged STYLE (styles.load_and_merge),
    the primitives/blocks catalog signatures, styles/composition-rules.md, and the SEED
    constraints.
  - CLI: emits the assembled prompt to stdout / a file for inspection.

WHAT THIS FILE DOES NOT DO YET:
  - The structured-output MODEL CALL + validate/repair loop is **Phase 3** (see the
    ``generate_composition`` stub + the clearly-marked TODO at the bottom). No live LLM call
    happens here.

This module only READS existing pipeline modules/artifacts and writes nothing except the
inspection prompt file the CLI is asked to write. It does not modify compose_section.py,
compose_page.py, layout_library.py, onbrand_check.py, or any brand.yaml/layout-library.yaml.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# The sibling pipeline modules live in this same directory; make them importable whether
# this file is run as a script or imported as brand_pipeline.generate_composition.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import layout_library as ll          # noqa: E402  (reuse-before-create: retrieval engine)
import styles as styles_mod          # noqa: E402  (the STYLE layer loader/merge)

REPO_ROOT = _HERE.parent
CONTRACTS_DIR = _HERE / "contracts"
COMPOSITION_RULES_PATH = REPO_ROOT / "styles" / "composition-rules.md"
SCHEMA_PATH = _HERE / "spec" / "composition.v1.schema.json"
ONBRAND_CHECK = _HERE / "onbrand_check.py"

# ── off-grid EXPANSION capability (Part B) ─────────────────────────────────────────
# The freedom-envelope OFF-GRID treatment set: the placement moves that break the aligned
# grid. A base style with offGridExpansion=TRUE (styles/<id>.md front-matter) unlocks these
# on non-hero sections AND unlocks novelty:"novel"; a FALSE style may only reuse/adapt
# captured patterns and gets NEITHER (enforced by offgrid_prefilter + the repair loop).
# NB: this is deliberately a SUBSET of layout_library.TREATMENT_KINDS — ghost-word,
# marginal-caption, inset and the sanctioned hero text-on-media are style-identity devices,
# NOT expansion, so they stay legal regardless of the flag.
OFF_GRID_TREATMENTS = frozenset({"stagger", "overlap", "bleed", "float-wrap", "counter-rotate",
                                 # editorial-harvest-2026-07: the overlay family + typographic
                                 # devices are off-grid character — style-gated for free.
                                 "straddle", "panel-on-media", "scrim-band",
                                 "type-behind-media", "stepped-lines", "break-frame"})


# ── loaders ──────────────────────────────────────────────────────────────────────

def load_brand(brand_yaml_path: Path | str) -> dict:
    """Load the canonical brand.yaml (read-only)."""
    p = Path(brand_yaml_path)
    return yaml.safe_load(p.read_text()) or {}


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


# ── PHASE 1C: the seeding hook (revives render_pattern_constraint) ─────────────────

@dataclass
class SeedResult:
    """The output of ``seed_patterns``: the per-use-case matches, the resolved patterns
    (ordered), and the rendered reuse-constraint seed block."""
    matches: dict[str, ll.MatchResult] = field(default_factory=dict)   # useCase -> best match
    patterns: list[ll.Pattern] = field(default_factory=list)           # ordered resolved patterns
    use_cases: list[str] = field(default_factory=list)                 # candidate use-cases (in order)
    block: str = ""                                                    # render_pattern_constraint output

    def pattern_ids(self) -> list[str]:
        return [p.id for p in self.patterns]


def candidate_use_cases(doc: dict) -> list[str]:
    """Derive the candidate use-cases from the brand's own ``layouts[]`` (each layout's
    inferred use-case), preserving first-seen order and de-duplicating. This is the set of
    use-cases the page actually needs; the seeder resolves a reuse pattern for each."""
    seen: list[str] = []
    for layout in (doc.get("layouts") or []):
        uc = ll.infer_use_case(layout)
        # "" = no retrieval bucket (W6: unknown sections no longer default to hero)
        if uc and uc not in seen:
            seen.append(uc)
    return seen


def seed_patterns(doc: dict, brand_yaml_path: Path | str,
                  use_cases: list[str] | None = None,
                  lp_dir: Path | None = None) -> SeedResult:
    """For each candidate use-case, run the layout-library retrieval and render the
    reuse-constraint seed block.

    Call chain (all in ``brand_pipeline/layout_library.py``):
        query_from_layout(layout, doc)          # brand layout -> retrieval Query
          -> match(query, brand_yaml)           # score project+standard, hard-filter neverDo
            -> render_pattern_constraint([...])  # REVIVED: reuse-constraint seed block

    The result BIASES the generator toward reuse; the prose in styles/composition-rules.md
    keeps ``novelty:novel`` open when the brief needs a structure the library lacks.
    """
    brand_yaml = Path(brand_yaml_path)
    layouts = doc.get("layouts") or []
    wanted = use_cases if use_cases is not None else candidate_use_cases(doc)

    # For each layout, build a retrieval query and match. Keep the best (highest-scoring)
    # reuse/adapt pattern per use-case so the seed block has one pattern per use-case.
    best: dict[str, tuple[float, ll.MatchResult]] = {}
    for layout in layouts:
        query = ll.query_from_layout(layout, doc)
        if query.use_case not in wanted:
            continue
        res = ll.match(query, brand_yaml, lp_dir)
        if res.pattern is None:          # miss -> nothing to reuse for this instance
            continue
        prev = best.get(query.use_case)
        if prev is None or res.score > prev[0]:
            best[query.use_case] = (res.score, res)

    # Order patterns by the candidate use-case order (deterministic, matches page intent).
    matches: dict[str, ll.MatchResult] = {}
    patterns: list[ll.Pattern] = []
    for uc in wanted:
        if uc in best:
            res = best[uc][1]
            matches[uc] = res
            patterns.append(res.pattern)

    block = ll.render_pattern_constraint(patterns)   # <-- the revived dead code
    return SeedResult(matches=matches, patterns=patterns, use_cases=wanted, block=block)


# ── catalog signatures (compact primitive/block grammar for the prompt) ────────────

def primitive_signatures() -> list[str]:
    """One compact line per primitive: ``key — intent  [variants: …]``."""
    data = _load_yaml(CONTRACTS_DIR / "primitives.yaml").get("primitives") or {}
    out = []
    for key, spec in data.items():
        spec = spec or {}
        line = f"- {key} — {spec.get('intent', '').strip()}"
        variants = spec.get("variants")
        if variants:
            line += f"  [variants: {', '.join(map(str, variants))}]"
        out.append(line)
    return out


def block_signatures() -> list[str]:
    """One compact line per block: ``key(slot[accepts]{?,*}, …)``. ``?`` = optional, ``*`` =
    repeatable — the grammar the composition MUST respect."""
    data = _load_yaml(CONTRACTS_DIR / "blocks.yaml").get("blocks") or {}
    out = []
    for key, spec in data.items():
        spec = spec or {}
        slots = spec.get("slots") or {}
        parts = []
        for sname, s in slots.items():
            s = s or {}
            accepts = "|".join(map(str, (s.get("accepts") or [])))
            flags = ""
            if s.get("optional"):
                flags += "?"
            if s.get("repeatable"):
                flags += "*"
            parts.append(f"{sname}[{accepts}]{flags}")
        out.append(f"- {key}({', '.join(parts)})")
    return out


# ── brand facts (token roles / neverDo / type tiers / spacing steps) ───────────────

def brand_facts(doc: dict) -> dict:
    tokens = doc.get("tokens") or {}
    colors = list((tokens.get("colors") or {}).keys())
    surfaces = list((tokens.get("surfaces") or {}).keys())
    types = tokens.get("type") or {}
    type_tiers = []
    for role, t in types.items():
        t = t or {}
        base = ((t.get("sizeRem") or {}) or {}).get("base")
        type_tiers.append(f"{role}: base={base}rem weight={t.get('weight')} case={t.get('case')}")
    spacing = tokens.get("spacing") or {}
    spacing_steps = [f"{k}: {(v or {}).get('value')}" for k, v in spacing.items()]
    neverdo = [(str(r.get("id")), str(r.get("statement", "")).strip())
               for r in (doc.get("neverDo") or []) if isinstance(r, dict) and r.get("id")]
    return {
        "name": (doc.get("brand") or {}).get("name", ""),
        "colors": colors,
        "surfaces": surfaces,
        "type_tiers": type_tiers,
        "spacing_steps": spacing_steps,
        "neverDo": neverdo,
    }


# ── PHASE 1C: the prompt builder ──────────────────────────────────────────────────

# Surface-role dark markers (mirrors component_render.make_context + the textAccent
# convention: LIGHT surfaces carry no textAccent; a textAccent-bearing surface is a
# dark/inverse-family band even when its role name is brand-specific, e.g. an
# image-scrim hero surface).
_DARK_ROLE_HINTS = ("inverse", "accent", "overlay")


def _surface_rhythm_profile(doc: dict) -> dict:
    """Derive the brand's OBSERVED surface rhythm facts from extracted evidence
    (surfaceGrammar.pageRhythm resolved against tokens.surfaces), for the
    surface-fidelity prompt rules. Palette-agnostic: only light/dark band structure
    is derived, never any brand's colors.

    Returns {"rhythm": [roles], "dark_count": int, "opens_dark": bool,
             "has_rhythm": bool, "has_dark_surface": bool}.
    A brand with NO captured rhythm reports has_rhythm=False (callers fall back to
    the historical default rather than inventing an all-light claim)."""
    surfaces = (doc.get("tokens") or {}).get("surfaces") or {}

    def _is_dark(role: str) -> bool:
        r = str(role or "")
        if any(h in r for h in _DARK_ROLE_HINTS):
            return True
        surf = surfaces.get(r)
        return bool(isinstance(surf, dict) and surf.get("textAccent"))

    rhythm = (doc.get("surfaceGrammar") or {}).get("pageRhythm")
    if isinstance(rhythm, dict):
        rhythm = rhythm.get("value")
    rhythm = [str(r) for r in rhythm] if isinstance(rhythm, list) else []
    dark_flags = [_is_dark(r) for r in rhythm]
    return {
        "rhythm": rhythm,
        "dark_count": sum(dark_flags),
        "opens_dark": bool(dark_flags and dark_flags[0]),
        "has_rhythm": bool(rhythm),
        "has_dark_surface": any(_is_dark(r) for r in surfaces),
    }


# `surfaceIntent` names the SECTION BAND's paint, not a device inside it. A seeded
# pattern that carries its own inset panel / art-surface treatment (panel-on-media,
# art-surface, inset) already paints that panel INSIDE the section — the section
# itself stays on the page canvas. Emitting "panel" there repaints the whole band
# and erases the canvas the source shows around the device. Brand-agnostic: the
# mechanic holds for any brand whose patterns carry inset panel devices.
_PANEL_INTENT_RULE = (
    "- SURFACE INTENT NAMES THE BAND, NOT A DEVICE: `surfaceIntent` paints the whole\n"
    "  section band. A section seeded from a pattern whose intent/treatments carry an\n"
    "  INSET panel or art surface (panel-on-media, inset, art-panel heroes) already\n"
    "  renders that panel inside the section — keep such a section's `surfaceIntent`\n"
    "  on the page canvas (\"primary\"/\"any\"); do NOT set \"panel\" for it. Reserve\n"
    "  `surfaceIntent: \"panel\"` for sections the source really renders as a full\n"
    "  panel-toned band edge-to-edge.\n")


def _brand_fidelity_rules(doc: dict, single_accent: bool) -> str:
    """The BRAND FIDELITY rule block, derived from the brand's extracted surface
    grammar instead of asserting one grammar for every brand (the old hardcoded
    "exactly ONE inverse hero" rule forced dark bands onto all-light brands).

    Three shapes:
      - rhythm OPENS dark  -> the historical rule (one inverse hero bookend);
      - rhythm has dark bands but NOT at the opening -> hero stays light; inverse
        reserved for as many later bands as observed;
      - all-light rhythm -> inverse surfaceIntent is FORBIDDEN everywhere.
    A brand with no captured rhythm keeps the historical default when it declares a
    dark surface at all, else falls through to the all-light rule (nothing to paint
    an inverse band with)."""
    prof = _surface_rhythm_profile(doc)
    accent_hero = (
        "  It is the ONLY section that carries the brand accent (on its display-title); the\n"
        "  gate's single-accent rule allows at most ONE accent-styled element on the page.\n"
        if single_accent else "")
    accent_light = (
        "- ACCENT DISCIPLINE: at most ONE committed accent-styled TEXT moment page-wide\n"
        "  (accent display-title or eyebrow), placed only on a surface where the brand's own\n"
        "  rules make the accent legal. Actions (buttons/links) realize accent through the\n"
        "  brand's catalog and do not count against this budget.\n"
        if single_accent else "")

    if prof["has_rhythm"] and prof["dark_count"] == 0:
        return (
            "- BRAND FIDELITY (HARD — derived from the brand's extracted surface rhythm): the\n"
            "  observed page rhythm carries NO dark/inverse band. Every section — the hero\n"
            "  included — uses `surfaceIntent` \"primary\", \"panel\" or \"any\"; NEVER emit\n"
            "  \"inverse\" or \"inverse-strong\" for this brand. The hero realizes its impact\n"
            "  through the brand's own extracted hero pattern (panel/art surface, display-scale\n"
            "  type, placed media), not through a dark band the source never shows.\n"
            + _PANEL_INTENT_RULE + accent_light)
    if prof["has_rhythm"] and not prof["opens_dark"]:
        return (
            "- BRAND FIDELITY (HARD — derived from the brand's extracted surface rhythm): the\n"
            "  observed rhythm keeps the OPENING light and reserves dark band(s) for later\n"
            f"  positions ({prof['dark_count']} dark band(s) observed, e.g. a closing conversion\n"
            "  band). The hero uses `surfaceIntent` \"primary\", \"panel\" or \"any\"; at most\n"
            f"  {prof['dark_count']} section(s) may use \"inverse\"/\"inverse-strong\", placed\n"
            "  where the extracted rhythm shows them (never the opener).\n"
            + _PANEL_INTENT_RULE + accent_light)
    if not prof["has_rhythm"] and not prof["has_dark_surface"]:
        return (
            "- BRAND FIDELITY (HARD): this brand declares no dark/inverse surface, so no section\n"
            "  may use `surfaceIntent` \"inverse\" or \"inverse-strong\" — every section uses\n"
            "  \"primary\", \"panel\" or \"any\".\n"
            + _PANEL_INTENT_RULE + accent_light)
    # opens-dark rhythm, or no rhythm evidence but a dark surface exists (historical default).
    return (
        "- BRAND FIDELITY (HARD — derived from the brand's extracted surface rhythm): the\n"
        "  observed rhythm opens on a dark band. Exactly ONE section — the hero/opening\n"
        "  bookend — MUST use `surfaceIntent: \"inverse\"` (or \"inverse-strong\").\n"
        + accent_hero +
        "  EVERY other section uses `surfaceIntent: \"primary\"` or \"panel\""
        + (" and carries NO accent" if single_accent else "") + ".\n")


_COPY_QUALITY_RULES = """- COPY QUALITY (HARD): copy is REAL, specific and non-repeating.
  - Within a section, eyebrow ≠ heading ≠ body: never restate one phrase across slots. The
    eyebrow is a short register label (<= 6 words), the heading carries the section's ONE
    claim, the body ADVANCES it with NEW information (specifics, numbers, proof from the
    brief) instead of paraphrasing the heading.
  - No heading repeats verbatim across sections; no slot ships placeholder prose ("Lorem",
    "Section body", the bare brand name as a heading).
  - Bind the brief's own facts and vocabulary into slot copy; where the brief is thin for a
    section, derive from the brand's extracted voice/do-avoid evidence — never generic
    marketing filler that could caption any brand.
- LOGO WALLS (HARD): a `logos` use-case section binds its wall as ONE repeatable slot whose
  `copy` is an ARRAY of {"alt": "<Company>", "asset": "<file>"} objects — each `asset` an
  EXACT filename from the brand-assets list above (the logo files). Never bare strings,
  never invented filenames, and never a text-only wall while real logo assets exist.
- FOOTER (HARD): do NOT compose a footer section. The renderer appends the brand's
  extracted footer chrome to every page, so a model-authored footer renders as a DUPLICATE.
  Omit "footer" from `sections` even when the brief mentions footer content."""


def _expansion_capability_block(off_grid_expansion: bool) -> str:
    """The prose the model reads for the off-grid EXPANSION capability gate (Part B).

    When unlocked (TRUE) it authorizes the freedom-envelope off-grid treatments + novelty;
    when locked (FALSE) it forbids both and pins the model to reuse/adapt. This is injected
    right after the composition grammar so it overrides the grammar's generic "freedom
    envelope" prose for this run."""
    if off_grid_expansion:
        return (
            "## Expansion capability — OFF-GRID EXPANSION: **UNLOCKED** (base style "
            "offGridExpansion=true)\n"
            "You MAY expand BEYOND the captured/seeded layout set:\n"
            "- You MAY emit `novelty:\"novel\"` sections (`seededFrom:null`) when the brief "
            "needs a structure the library lacks — recomposed WITHIN a drawable archetype and "
            "still obeying EVERY brand neverDo.\n"
            "- You MAY apply the off-grid treatments — `stagger`, `overlap`, `bleed`, "
            "`float-wrap`, `counter-rotate`, and the overlay family (`straddle`, "
            "`panel-on-media`, `scrim-band`, `type-behind-media`, `stepped-lines`, "
            "`break-frame`) — on any section to break the aligned grid "
            "(within the z-ladder + neverDo). These are the editorial signature.\n"
            "- Prefer reuse/adapt for the workhorse sections; reach for novel + off-grid "
            "deliberately where it earns the page distinctiveness.\n")
    return (
        "## Expansion capability — OFF-GRID EXPANSION: **LOCKED** (base style "
        "offGridExpansion=false)\n"
        "You may ONLY reuse or adapt CAPTURED patterns. This style earns trust through "
        "disciplined alignment, not off-grid drama. HARD for this run:\n"
        "- Every section MUST be `novelty:\"reuse\"` or `novelty:\"adapt\"` with a real "
        "`seededFrom` object. Do NOT emit `novelty:\"novel\"` / `seededFrom:null`.\n"
        "- Do NOT apply the off-grid treatments `stagger`, `overlap`, `bleed`, `float-wrap`, "
        "`counter-rotate`, `straddle`, `panel-on-media`, `scrim-band`, `type-behind-media`, "
        "`stepped-lines`, or `break-frame` on any non-hero section. Keep modules on the grid "
        "(plain `cards`/`split`/`stack` rows, even ratios, no offset/overlap/bleed).\n"
        "- The hero bookend keeps its sanctioned display-title-over-media only.\n"
        "A composition that violates this is rejected and returned to you for repair.\n")


def build_prompt(brief_text: str, brand_yaml_path: Path | str, style_id: str,
                 seeds: SeedResult | str, off_grid_expansion: bool = True) -> str:
    """Deterministically assemble the system/user prompt for the composition generator.

    Assembly order (mirrors styles/composition-rules.md ``## Assembly``):
      1. universal composition grammar (styles/composition-rules.md)
      1b. the off-grid EXPANSION capability gate (unlock/lock — Part B)
      2. merged base STYLE (styles.load_and_merge -> invariants, soft options, scales, floor)
      3. brand facts (token color roles, neverDo, measured type tiers, spacing steps)
      4. primitives/blocks catalog signatures
      5. SEED constraints (render_pattern_constraint block from seed_patterns)
      6. the brief copy + the output contract (emit ONE composition.v1 object)

    ``off_grid_expansion`` is the resolved capability flag for this run (see
    resolve_off_grid_expansion): TRUE authorizes novel + off-grid treatments; FALSE pins the
    model to reuse/adapt captured patterns.
    """
    doc = load_brand(brand_yaml_path)
    facts = brand_facts(doc)

    # merged STYLE (structure + invariants + soft options + spacing/type scale).
    single_accent = True  # style-structure default (styles.StyleStructure.single_accent)
    try:
        ctx = styles_mod.load_and_merge(style_id, doc)
        st = ctx.style
        struct = ctx.structure
        single_accent = bool(struct.single_accent)
        style_lines = [
            f"style id: {st.id}",
            f"display floor: {struct.display_size_css()} (>= {struct.min_display_rem}rem)",
            f"radius (merged): {struct.radius}   flat: {struct.flat}   "
            f"centered-default: {struct.centered}   single-accent: {struct.single_accent}",
            "spacing scale: " + ", ".join(f"{k}={v}" for k, v in struct.space_scale.items()),
            f"rhythm slots: section={struct.section_pad_slot} block={struct.block_gap_slot} "
            f"cluster={struct.cluster_gap_slot}",
            "invariants:",
            *[f"  {i+1}. {inv}" for i, inv in enumerate(st.invariants)],
            "soft options:",
            *[f"  - {oid}: [{o.get('allowed')}] default {o.get('default')}"
              for oid, o in st.soft_options.items()],
        ]
        # freedom budget (0-5 wildcard allowance) — the style layer's QUALITATIVE ladder
        # of how far a section may deviate from the brand median. The RESOLVED level for
        # this run (brand voice.dials.freedom clamped to the style ceiling, else the
        # style default) is the operative allowance; levels are style-relative prose,
        # never exact values. Absent for a non-migrated style (lines omitted).
        fb = st.freedom_budget
        if fb is not None:
            resolved = ctx.resolve_freedom_level(doc)
            style_lines += [
                f"freedom budget (0-5 wildcard allowance): resolved level {resolved} "
                f"(style default {fb.default}, ceiling {fb.ceiling} — higher requests cap "
                "at the ceiling):",
                *[f"  {lvl}. {d.get('name')}: unlocks {d.get('unlocks')}"
                  + (f" | forbids {d.get('forbids')}" if d.get("forbids") else "")
                  for lvl, d in sorted(fb.levels.items())],
            ]
    except FileNotFoundError:
        style_lines = [f"style id: {style_id} (NOT FOUND — style layer omitted)"]

    seed_block = seeds.block if isinstance(seeds, SeedResult) else str(seeds)
    seed_use_cases = ", ".join(seeds.use_cases) if isinstance(seeds, SeedResult) else "(caller-supplied)"

    grammar = COMPOSITION_RULES_PATH.read_text() if COMPOSITION_RULES_PATH.exists() else \
        "(styles/composition-rules.md not found)"

    nd_lines = [f"- {rid}: {stmt}" for rid, stmt in facts["neverDo"]]

    system = f"""# SYSTEM — Composition generator ({facts['name'] or 'brand'} · style {style_id})

You author a page as a STRUCTURED `composition.v1` object (see the schema contract at the
end). You NEVER write HTML/CSS and NEVER re-author a primitive: a deterministic renderer
draws your object and an on-brand gate validates it. Arrange the vocabulary well; obey the
three-tier precedence (base-style invariants → composition-rules → brand neverDo HARD).

## Composition grammar (universal)
{grammar}

{_expansion_capability_block(off_grid_expansion)}
## Base STYLE (merged under the brand)
{chr(10).join(style_lines)}

## Brand facts ({facts['name']})
- color roles (emit refs, never hex): {', '.join(facts['colors'])}
- surface roles: {', '.join(facts['surfaces'])}
- measured type tiers (sizeClass resolves to these): {' | '.join(facts['type_tiers'])}
- spacing steps (pick a named step, never ad-hoc px): {' | '.join(facts['spacing_steps'])}
- brand neverDo (HARD — a violation FAILS the gate):
{chr(10).join(nd_lines)}

## Primitive palette (contracts/primitives.yaml — use only these keys)
{chr(10).join(primitive_signatures())}

## Block grammar (contracts/blocks.yaml — respect accepts / ?optional / *repeatable)
{chr(10).join(block_signatures())}

## SEED constraints (reuse-before-create; use-cases: {seed_use_cases})
{seed_block or '(no reuse patterns matched — compose from the palette; novelty:novel expected)'}
"""

    # valid seededFrom refs (the model must pick from these or use null) — from the seeds.
    seed_refs = []
    if isinstance(seeds, SeedResult):
        seed_refs = [f'{{"lib": "{p.lib or "project"}", "id": "{p.id}"}}' for p in seeds.patterns]
    seed_refs_line = "  ".join(seed_refs) if seed_refs else "(none matched — use null)"

    brand_ref = str(brand_yaml_path)

    # real, on-disk brand image assets (the ONLY srcs the gate treats as present). The
    # renderer already defaults media slots to brand photography, so asset:null is safe.
    brand_dir = Path(brand_yaml_path).parent
    img_exts = (".jpg", ".jpeg", ".png", ".svg", ".webp")
    assets: list[str] = []
    for d in (brand_dir, brand_dir / "assets"):
        if d.is_dir():
            assets += sorted(p.name for p in d.iterdir()
                             if p.suffix.lower() in img_exts)
    assets = sorted(dict.fromkeys(assets))
    assets_line = ", ".join(assets) if assets else "(none — use asset:null everywhere)"

    user = f"""# USER — brief

{brief_text.strip()}

# OUTPUT CONTRACT — emit EXACTLY ONE JSON object, no prose, no markdown fences.
It MUST validate against composition.v1.schema.json. The EXACT shape (copy it precisely):

{{
  "schemaVersion": "composition.v1",
  "brief":  {{ "id": "<brief-slug>", "name": "<optional>", "useCasesRequested": ["hero", ...] }},
  "brand":  {{ "ref": "{brand_ref}" }},
  "style":  {{ "id": "{style_id}" }},
  "sections": [ <section>, ... ],
  "rationale": "<why these sections/order/novel departures>"
}}

A <section> is EXACTLY (no other keys; do NOT nest sections):
{{
  "id": "<slug unique in page>",
  "useCase": one of ["hero","features","pricing","testimonial","gallery","cta","about","faq","logos","footer"],
  "archetype": one of ["stack","collage","split","stack-fullbleed","cards","interlock","overlay","banded"]  (ONLY these 8 draw),
  "surfaceIntent": one of ["any","primary","inverse","inverse-strong","panel"],
  "novelty": one of ["reuse","adapt","novel"],
  "seededFrom": one of these objects, or null (NOT a string):
      {seed_refs_line}
  "slots": [ <slot>, ... ],          // >=1, FLAT — a slot NEVER contains a "slots" array
  "treatments": [ <treatment>, ... ], // may be []
  "knobs": {{ ... }},                  // optional, e.g. {{"columns":"3","align":"left"}}
  "grid": {{ "columns": 12, "gutter": "<css length>" }},          // OPTIONAL registration grid
  "alignment": {{ "anchor": "centered"|"left"|"right", "counterweight": "<slot name>" }},  // OPTIONAL
  "bands": {{ "split": <0..1>, "surfaces": ["inverse","panel"] }}  // 'banded' archetype ONLY (dual-surface seam)
}}

A <slot> is EXACTLY (required: name, role, contract — NEVER omit "role"; NO nested "slots"):
{{
  "name": "<slot name>", "role": "<semantic role>", "contract": "<primitive|block key>",
  "textLen": one of ["none","word","short","medium","long"],
  "sizeClass": one of ["colossal","hero","display","title","body","caption"],
  "width": one of ["hug","stretch","fixed","media","full-bleed","framed"],  // framed = page margins visible on ALL sides (an inset canvas)
  "mediaAspect": one of ["portrait","landscape","square","wide","pano","freeform"],  // media slots only; honored as a REAL aspect-ratio (wide=21/9, pano=3/1, portrait=3/4, square=1/1)
  "z": one of ["back","mid","front"],
  // OPTIONAL placement on the section's registration grid (§4.6.5 — all omittable;
  // omitted = the archetype's measured default geometry):
  "colStart": <int>, "colSpan": <int>, "rowSpan": <int>,
  "offsetCols": <number>, "offsetBaselines": <number>,
  "alignTo": {{ "slot": "<slot name|omit for section frame>", "edge": "left|right|top|bottom", "corner": "tl|tr|bl|br" }},
  "registration": {{ "toSlot": "<base slot>", "edge": "left|right|top|bottom",
                     "depthCols": <number> | "depthBaselines": <number>, "z": "back|mid|front" }},
  "copy": "<string>" | {{ "eyebrow": "...", "heading": "...", ... }} | [ {{...}}, ... ],  // repeatable → array
  "asset": null | {{ "src": "...", "alt": "...", "ratio": "landscape" }}
}}
For a repeatable module run (e.g. the brief's THREE value_props), use ONE slot whose "copy" is an
ARRAY of objects (one per module) — NOT three sibling slots and NOT nested slots.

PLACEMENT (grid/overlap contract — use it when the brief calls for a specific geometry):
- Slot edges align to shared column lines via colStart/colSpan; break deliberately with
  offsetCols/offsetBaselines (grid units, may be fractional) — never invent raw % offsets.
- Every OVERLAPPING media slot declares `registration` (base slot + crossed edge + depth in
  cols/baselines + z). Mirror an overlap by flipping the edge. A multi-image cluster is N
  registered overlays with an explicit back→front z order.
- A hero section may carry MULTIPLE media slots with distinct placement/z: a `z:"back"` +
  `width:"full-bleed"` media renders as a true BACKGROUND layer behind the copy (a sanctioned
  text-on-media treatment — mark it `"sanctioned": true`; the renderer adds a surface-toned
  scrim so text keeps contrast), and a small `z:"front"` media with `alignTo: {{"corner":"br"}}`
  pins to the section frame's corner.
- `section.alignment` sets the per-section anchor (a mid-page hero CAN be centered);
  an asymmetric anchor should name a `counterweight` slot that balances the empty half.
- Decorative/back layers must never compromise text readability (the gate checks
  text contrast over media and decoration salience).

A <treatment> is EXACTLY (required: kind):
{{ "kind": one of ["ghost-word","overlap","stagger","bleed","marginal-caption","text-on-media",
      "counter-rotate","float-wrap","inset",
      "straddle","panel-on-media","scrim-band","framed","type-behind-media",
      "mixed-face","stepped-lines","break-frame"],
   "target": "<slot name>", "pair": ["<roleA>","<roleB>"], "zOrder": [...],
   "amount": {{ "class": one of ["light","medium","heavy"] }},
   "over": "<media slot name>", "axis": "vertical|horizontal", "sanctioned": true|false,
   // overlay-family parameters (editorial-harvest devices; use on the `overlay`/`banded` archetypes):
   "registration": {{ "toSlot": "<slot | 'seam' inside a banded section>", "edge": "left|right|top|bottom",
                      "depthCols": <n> | "depthBaselines": <n>, "z": "back|mid|front" }},
   "band": {{ "rowStart": <0..1>, "rowSpan": <0..1> }},          // scrim-band: where it crosses the media
   "fill": {{ "opacityClass": "light|medium|heavy" }},           // scrim-band: FLAT translucent wash (never a gradient)
   "distribute": "start|center|space-between",                  // panel-on-media: panel's internal stack
   "widthRel": {{ "to": "container", "ratio": <0..1> }},         // framed: frame width (snapped to whole columns)
   "maxOcclusion": {{ "class": "light|medium|heavy" }},          // G8: occlusion budget (~0.25/0.4/0.55 glyph area)
   "endsVisible": true,                                         // G8: first+last letterforms stay clear (REQUIRED true)
   "steps": [<n>, ...], "direction": "left|right",              // stepped-lines: per-line indents (HALF-column units)
   "spans": [ {{ "part": "lead|emphasis", "face": "roman|italic" }} ],  // mixed-face (copy carries {{lead, emphasis}})
   "salience": "decorative" }}                                  // break-frame: decoration only (never over text)

THE OVERLAY FAMILY (archetype "overlay" = ONE positioning context; archetype "banded" = a
dual-surface section with a hard horizontal seam):
- `panel-on-media` {{target, over, distribute}}: a SOLID panel grid-placed over a media canvas —
  the sanctioned panel-over-media pair; the panel's text never touches the photo.
- `straddle` {{target, registration}}: the target crosses another slot's edge by the registered
  depth. z:"front" rides OVER (a display heading breaking a rail/photo seam or a framed photo's
  bottom edge); z:"back" TUCKS UNDER the crossed media and then REQUIRES maxOcclusion +
  endsVisible (G8). A TEXT-target straddle onto photography is text-on-media-family — hero-only,
  mark `"sanctioned": true`. A MEDIA-target straddle (media-over-seam) needs no text sanction.
- `scrim-band` {{target, over, band, fill}}: a FLAT translucent band across the media carrying the
  target's content (e.g. keyword columns as a copy ARRAY) — never a gradient; medium+ opacity
  under body-size text.
- `framed` {{target, widthRel}}: the media renders with page margins visible on ALL sides; other
  slots may register against the frame (alignTo/registration.toSlot = the frame slot).
- `type-behind-media` {{target, over, maxOcclusion, endsVisible}}: REAL heading copy at full
  opacity rendered BEHIND the media stack (NOT a ghost-word). Legal ONLY under the occlusion
  contract: the media must cover <= maxOcclusion of the heading's glyph area AND the word's
  first/last letterforms stay clear (`endsVisible: true`). Text-on-media-family — hero-only,
  `"sanctioned": true`. Keep the media span strictly INSIDE the heading span.
- A "banded" section declares `bands: {{split, surfaces: [top, bottom]}}` (hard cut, never a
  gradient) and elements straddle the seam via `registration.toSlot: "seam"` — the
  media-over-seam overlap pair (sanctioned where the brand's compositionRules allow it).
  Model a photo-band→panel-band device as ONE banded section, never as two overlapping
  sections.
- Typographic devices: `stepped-lines` (an authored multi-line statement whose lines step by
  half-column indents), `mixed-face` (copy carries {{"lead": "...", "emphasis": "..."}}),
  `break-frame` (corner decoration crossing a frame edge; salience "decorative", never over text).

RULES:
- Every `slot.contract` MUST be a key in the primitive/block palette above; respect block grammar.
- Values are token ROLES (never hex); units resolve to container-query; spacing is a named scale
  step; sizeClass resolves to a measured type tier.
- Prefer the SEED patterns (novelty reuse/adapt, set `seededFrom` to one of the objects above);
  use `novelty:"novel"` + `seededFrom:null` ONLY when the brief needs a structure the library lacks.
- Obey every brand neverDo. The ONLY sanctioned `text-on-media` is the hero
  display-title-over-media (mark that treatment `"sanctioned": true`).
- Bind the brief's real copy into slot `copy` (render THREE value_props as ONE features slot with a
  3-object copy array so each is its own module).
- BRAND ASSETS: the ONLY real image files are: {assets_line}. For a media slot set
  `asset.src` to one of these EXACT filenames, or `asset: null` (the renderer then supplies
  brand photography). NEVER invent a filename (e.g. gallery-01.jpg) — a missing file FAILS the
  gate. PREFER binding a real asset to each media-bearing module when a suitable one exists
  (a repeatable module run whose items each have matching brand art binds each module's
  `asset` explicitly, as a bare-string filename inside that module's copy object); reserve
  `asset: null` for slots where nothing in the list fits.
{_brand_fidelity_rules(doc, single_accent)}{_COPY_QUALITY_RULES}
"""
    return system + "\n" + user


# ── PHASE 3: the structured-output model call + validate/prefilter/gate/repair loop ─

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_REASONING = "adaptive"


def load_api_keys(project_dir: Path | str = REPO_ROOT) -> bool:
    """Populate os.environ from ``<project_dir>/.env.local`` (only keys not already set),
    mirroring run_brand_pipeline.load_api_keys. Returns True if ANTHROPIC_API_KEY is present
    afterward. NEVER logs the value."""
    env_path = Path(project_dir) / ".env.local"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'\"")
            if key and value and not os.environ.get(key):
                os.environ[key] = value
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def normalize_top_level(comp: dict, *, brief_id: str, brand_ref: str, style_id: str) -> dict:
    """Fill/repair the DETERMINISTIC scaffolding fields the caller already knows
    (schemaVersion, brief.id, brand.ref, style.id) so the model spends its budget on the
    creative section work, not boilerplate. Also coerces the two common shape slips
    (style/brand emitted as a bare string) into their object form. Never invents section
    content. Idempotent."""
    if not isinstance(comp, dict):
        return comp
    comp.setdefault("schemaVersion", "composition.v1")
    # brief
    brief = comp.get("brief")
    if isinstance(brief, str):
        brief = {"text": brief}
    if not isinstance(brief, dict):
        brief = {}
    brief.setdefault("id", brief_id)
    comp["brief"] = brief
    # brand
    brand = comp.get("brand")
    if isinstance(brand, str):
        brand = {"ref": brand}
    if not isinstance(brand, dict):
        brand = {}
    brand.setdefault("ref", brand_ref)
    comp["brand"] = brand
    # style
    style = comp.get("style")
    if isinstance(style, str):
        style = {"id": style}
    if not isinstance(style, dict):
        style = {}
    style.setdefault("id", style_id)
    comp["style"] = style
    return comp


def extract_json(text: str) -> dict:
    """Pull the ONE composition.v1 JSON object out of a model response — tolerant of
    ```json fences / leading prose. Raises ValueError if no balanced object parses."""
    s = text.strip()
    # strip a leading ```json … ``` fence if present
    fence = re.search(r"```(?:json)?\s*(.*?)```", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()
    # fast path
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # scan for the first balanced {...}
    start = s.find("{")
    if start < 0:
        raise ValueError("no JSON object found in model response")
    depth, instr, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return json.loads(s[start:i + 1])
    raise ValueError("unbalanced JSON object in model response")


def validate_schema(comp: dict, schema: dict | None = None) -> list[str]:
    """Validate a composition against composition.v1.schema.json. Returns a list of
    human-readable error strings (empty == valid)."""
    import jsonschema
    schema = schema or _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for e in sorted(validator.iter_errors(comp), key=lambda x: list(x.absolute_path)):
        loc = "/".join(str(p) for p in e.absolute_path) or "(root)"
        errors.append(f"{loc}: {e.message}")
    return errors


def _section_to_pattern(section: dict) -> "ll.Pattern":
    """Adapt one composition.v1 section into a layout_library.Pattern so the SAME
    ``_violates_neverdo`` pre-filter the retrieval engine uses can screen AI output.
    SANCTIONED treatments (e.g. the hero display-title-over-media, which the gate blesses)
    are dropped from the screened set so the pre-filter only catches UNsanctioned devices."""
    treatments = [t for t in (section.get("treatments") or [])
                  if isinstance(t, dict) and not t.get("sanctioned")]
    return ll.Pattern(
        id=str(section.get("id") or section.get("useCase") or "section"),
        use_case=str(section.get("useCase") or ""),
        archetype_ref=str(section.get("archetype") or ""),
        surface_intent=str(section.get("surfaceIntent") or "any"),
        intent=str(section.get("rationale") or ""),
        content_shape={"slots": section.get("slots") or []},
        special_treatments=treatments,
        responsive={}, variant_knobs=section.get("knobs") or {},
        origin="ai", confidence="", scope="section", provenance=[],
    )


def resolve_off_grid_expansion(style_id: str, doc: dict,
                               force: bool | None = None) -> bool:
    """Resolve the effective off-grid EXPANSION capability for a run.

    Precedence: an explicit ``force`` (the ablation lever — e.g. the OFF arm forces False on
    an editorial style to ISOLATE the flag) wins; otherwise the value comes from the base
    style's ``offGridExpansion`` front-matter flag (styles.load_and_merge). A style that is
    not found -> False (conservative: no expansion)."""
    if force is not None:
        return bool(force)
    try:
        ctx = styles_mod.load_and_merge(style_id, doc)
    except FileNotFoundError:
        return False
    return bool(ctx.off_grid_expansion)


def _is_hero_section(section: dict) -> bool:
    """The opening bookend hero — the ONE section allowed its sanctioned overlap /
    text-on-media regardless of the flag (it is style identity, not expansion)."""
    return str(section.get("useCase") or "").strip().lower() == "hero"


def _section_off_grid_treatments(section: dict) -> list[str]:
    """The non-sanctioned OFF-GRID treatment kinds carried by a section. SANCTIONED
    treatments (e.g. the hero display-title-over-media) are excluded — only free/expansion
    devices are returned."""
    kinds: list[str] = []
    for t in (section.get("treatments") or []):
        if not isinstance(t, dict) or t.get("sanctioned"):
            continue
        k = str(t.get("kind") or "").strip()
        if k in OFF_GRID_TREATMENTS:
            kinds.append(k)
    return kinds


def offgrid_prefilter(comp: dict, off_grid_expansion: bool) -> list[tuple[str, str]]:
    """Enforce the off-grid EXPANSION capability gate (Part B).

    When ``off_grid_expansion`` is FALSE the composition may ONLY reuse/adapt captured
    patterns: it may carry NO ``novelty:"novel"`` section and NO off-grid treatment
    (stagger / overlap / bleed / float-wrap / counter-rotate) on a NON-HERO section. Returns
    ``[(section_id, reason)]`` for every violation so the caller can repair or reject them
    (mirrors ``neverdo_prefilter``'s shape). When TRUE, expansion is unlocked -> always [].

    The hero bookend is exempt (its sanctioned overlap/text-on-media is style identity), and
    sanctioned treatments are never counted (see ``_section_off_grid_treatments``)."""
    if off_grid_expansion:
        return []
    hits: list[tuple[str, str]] = []
    for sec in (comp.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or sec.get("useCase") or "section")
        if str(sec.get("novelty") or "").strip().lower() == "novel":
            hits.append((sid, "novelty:'novel' is locked (offGridExpansion=false) — "
                              "reuse/adapt a captured pattern instead"))
        if not _is_hero_section(sec):
            off = _section_off_grid_treatments(sec)
            if off:
                hits.append((sid, f"off-grid treatment(s) {sorted(set(off))} locked "
                                  "(offGridExpansion=false) — remove them / keep the section "
                                  "aligned to the captured pattern"))
    return hits


def neverdo_prefilter(comp: dict, doc: dict) -> list[tuple[str, str]]:
    """Run layout_library._violates_neverdo on each section. Returns [(section_id, nd_id)]
    for sections whose treatments/contracts trip an encodable brand prohibition."""
    neverdo_ids = [str(r.get("id")) for r in (doc.get("neverDo") or [])
                   if isinstance(r, dict) and r.get("id")]
    hits: list[tuple[str, str]] = []
    for sec in (comp.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        nd = ll._violates_neverdo(_section_to_pattern(sec), neverdo_ids)
        if nd:
            hits.append((str(sec.get("id") or sec.get("useCase") or "section"), nd))
    return hits


def _parse_gate_failures(report_md: Path) -> list[tuple[str, str]]:
    """Parse a human onbrand-report.md for FAIL rows → [(check_id, detail)]. Robust to the
    ``| \\`id\\` — label | FAIL | detail |`` table shape used by neverDo + invariant rows."""
    out: list[tuple[str, str]] = []
    if not report_md.exists():
        return out
    for line in report_md.read_text().splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if "FAIL" not in cells:
            continue
        idm = re.search(r"`([^`]+)`", cells[0])
        cid = idm.group(1) if idm else cells[0]
        fi = cells.index("FAIL")
        detail = cells[fi + 1] if fi + 1 < len(cells) else ""
        out.append((cid, detail))
    return out


def gate_composition(render_dir: Path | str, brand_yaml_path: Path | str, style_id: str,
                     *, layout: str | None = None,
                     report_name: str = "onbrand-report.md") -> tuple[bool, list[tuple[str, str]], dict]:
    """Run onbrand_check.py --composition (HARD invariants) on a rendered page dir via
    subprocess (the authoritative gate). Returns (overall_pass, failures, scorecard) where
    failures = [(check_id, detail)] parsed from the human report and scorecard = the
    machine-readable onbrand-report.json.

    ``layout`` is the gate's surface-context layout id and must be an id from the ACTIVE
    brand's brand.yaml. When None (the default), no --layout is passed and onbrand_check
    resolves it itself (render-dir name, else the brand's first layout) — the old shared
    default was one brand's hero id, which hard-failed the gate for every brand that
    didn't carry a layout of that name (hubspot-validation bug B8)."""
    render_dir = Path(render_dir)
    cmd = [sys.executable, str(ONBRAND_CHECK), str(brand_yaml_path), str(render_dir),
           "--style", style_id, "--composition",
           "--report", report_name]
    if layout:
        cmd[4:4] = ["--layout", layout]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    json_name = re.sub(r"\.md$", "", report_name) + ".json"
    scorecard_path = render_dir / json_name
    scorecard = json.loads(scorecard_path.read_text()) if scorecard_path.exists() else {}
    overall = bool(scorecard.get("overall", proc.returncode == 0))
    failures = _parse_gate_failures(render_dir / report_name)
    if not overall and not failures and proc.returncode != 0:
        failures = [("gate", (proc.stderr or proc.stdout or "").strip()[:400] or "gate failed")]
    return overall, failures, scorecard


def _call_model(provider, system_prompt: str, user_prompt: str, *, max_tokens: int,
                temperature: float | None) -> tuple[str, dict]:
    """Reuse the repo's Anthropic client (AnthropicProvider). Default path is the provider's
    ``text_query`` (adaptive thinking). When a non-default ``temperature`` is requested we
    call the SAME underlying client with thinking disabled (Anthropic rejects temperature +
    thinking together), so variety-by-sampling stays available for the harness. Returns
    (text, usage)."""
    if temperature is None:
        text = provider.text_query(system_prompt, user_prompt, max_tokens=max_tokens)
        return text, dict(getattr(provider, "last_usage", {}) or {})
    # explicit-temperature path (no thinking) on the reused client
    result = ""
    with provider.client.messages.stream(
        model=provider.model,
        max_tokens=provider._clamp_max_tokens(max_tokens),
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for chunk in stream.text_stream:
            result += chunk
        final = stream.get_final_message()
    usage = getattr(final, "usage", None)
    return result, {
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }


def _repair_note(schema_errs: list[str], nd_hits: list[tuple[str, str]],
                 gate_failures: list[tuple[str, str]],
                 offgrid_hits: list[tuple[str, str]] | None = None) -> str:
    """Assemble the SPECIFIC failing checks (ids + details) into a repair instruction the
    model can act on. No secrets, no HTML — just the contract failures."""
    lines = ["# REPAIR — your previous composition FAILED these checks. Fix ONLY these,",
             "# keep everything that passed, and re-emit ONE corrected composition.v1 object."]
    if schema_errs:
        lines.append("\n## schema errors (composition.v1.schema.json):")
        lines += [f"- {e}" for e in schema_errs[:20]]
    if offgrid_hits:
        lines.append("\n## off-grid EXPANSION capability violations (HARD — this style is "
                     "offGridExpansion=false, reuse/adapt only):")
        lines += [f"- section `{sid}`: {reason}" for sid, reason in offgrid_hits]
    if nd_hits:
        lines.append("\n## brand neverDo violations (HARD):")
        lines += [f"- section `{sid}` trips neverDo `{nd}` — remove/replace that device"
                  for sid, nd in nd_hits]
    if gate_failures:
        lines.append("\n## on-brand gate failures (--composition, HARD):")
        lines += [f"- `{cid}`: {detail}" for cid, detail in gate_failures]
    return "\n".join(lines)


@dataclass
class GenerationResult:
    composition: dict | None
    ok: bool
    attempts: int
    render_dir: Path | None
    scorecard: dict
    failures: list[tuple[str, str]]
    schema_errors: list[str]
    neverdo_hits: list[tuple[str, str]]
    telemetry: list[dict]           # per-attempt {attempt, latency_s, input_tokens, output_tokens, stage, ...}
    prompt_chars: int = 0
    off_grid_expansion: bool = True                       # the resolved capability flag for this run
    offgrid_hits: list[tuple[str, str]] = field(default_factory=list)   # last off-grid violations (if any)


def generate_composition(brief_text: str, brand_yaml_path: Path | str, style_id: str,
                         *, out_dir: Path | str,
                         model: str | None = None,
                         reasoning_effort: str | None = None,
                         temperature: float | None = None,
                         variety_directive: str | None = None,
                         brief_id: str = "brief",
                         max_repairs: int = 2,
                         layout: str | None = None,
                         provider=None,
                         seeds: "SeedResult | None" = None,
                         max_tokens: int = 16000,
                         force_off_grid: bool | None = None,
                         log=print) -> GenerationResult:
    """Generate a validated + on-brand ``composition.v1`` for the brief via ONE structured
    call to the repo's Anthropic client, then a bounded validate → neverDo-prefilter →
    render → gate → repair loop (≤ ``max_repairs`` retries).

    Pipeline per attempt:
      1. build_prompt(brief, brand, style, seeds)  [+ varietyDirective] [+ REPAIR note]
      2. one structured-output model call (reused AnthropicProvider client)
      3. extract_json → validate_schema (composition.v1.schema.json)
      4. neverdo_prefilter (layout_library._violates_neverdo on each section)
      5. compose_from_composition.render_composition → page dir
      6. gate_composition (onbrand_check.py --composition, JSON scorecard)
      7. pass → persist + return; fail → feed the SPECIFIC failing ids/details back (repair)

    Persists the final composition.json + rendered page + onbrand-report.{md,json} under
    ``out_dir``. Logs token/latency per call (never secrets)."""
    import compose_from_composition as cfc

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    brand_yaml_path = Path(brand_yaml_path)
    doc = load_brand(brand_yaml_path)
    schema = _load_schema()
    if seeds is None:
        seeds = seed_patterns(doc, brand_yaml_path)
    # resolve the off-grid EXPANSION capability for this run: an explicit force (the ablation
    # lever) wins, else the base style's offGridExpansion flag decides.
    off_grid = resolve_off_grid_expansion(style_id, doc, force=force_off_grid)
    log(f"  offGridExpansion={off_grid}"
        + (f" (forced {force_off_grid})" if force_off_grid is not None else " (from style)"))
    base_prompt = build_prompt(brief_text, brand_yaml_path, style_id, seeds,
                               off_grid_expansion=off_grid)

    if provider is None:
        if not load_api_keys():
            raise RuntimeError(
                "ANTHROPIC_API_KEY not available. Add it to "
                f"{REPO_ROOT / '.env.local'} (KEY=VALUE) or export it. "
                "Live generation is blocked without it.")
        from screenshot_to_template.models.anthropic import AnthropicProvider
        provider = AnthropicProvider(model or DEFAULT_MODEL,
                                     reasoning_effort=reasoning_effort or DEFAULT_REASONING)

    directive = ""
    if variety_directive:
        directive = ("\n# VARIETY DIRECTIVE (bias structure/section selection, still obey the "
                     f"contract + neverDo)\n{variety_directive.strip()}\n")

    telemetry: list[dict] = []
    schema_errs: list[str] = []
    nd_hits: list[tuple[str, str]] = []
    og_hits: list[tuple[str, str]] = []
    failures: list[tuple[str, str]] = []
    comp: dict | None = None
    repair_note = ""

    for attempt in range(max_repairs + 1):
        system_prompt = base_prompt
        user_extra = directive + (("\n" + repair_note) if repair_note else "")
        # build_prompt returns system+user joined; append directives/repair to the tail.
        prompt = system_prompt + user_extra
        t0 = time.time()
        try:
            raw, usage = _call_model(provider, prompt, "Emit the composition.v1 JSON now.",
                                     max_tokens=max_tokens, temperature=temperature)
        except Exception as exc:                       # network / auth / API error
            latency = round(time.time() - t0, 2)
            telemetry.append({"attempt": attempt, "stage": "model-error",
                              "latency_s": latency, "error": type(exc).__name__})
            log(f"  [attempt {attempt}] model call failed after {latency}s: {type(exc).__name__}")
            raise
        latency = round(time.time() - t0, 2)
        tele = {"attempt": attempt, "latency_s": latency,
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "temperature": temperature}
        log(f"  [attempt {attempt}] {latency}s  in={usage.get('input_tokens')} "
            f"out={usage.get('output_tokens')}")

        # 3. parse + normalize scaffolding + schema-validate
        try:
            comp = extract_json(raw)
            comp = normalize_top_level(comp, brief_id=brief_id,
                                       brand_ref=str(brand_yaml_path), style_id=style_id)
        except ValueError as exc:
            schema_errs = [f"(root): response was not parseable JSON — {exc}"]
            nd_hits, failures = [], []
            tele["stage"] = "parse-fail"
            telemetry.append(tele)
            repair_note = _repair_note(schema_errs, [], [])
            continue
        schema_errs = validate_schema(comp, schema)
        if schema_errs:
            tele["stage"] = "schema-fail"
            telemetry.append(tele)
            log(f"    schema: {len(schema_errs)} error(s)")
            repair_note = _repair_note(schema_errs, [], [])
            continue

        # 4. neverDo pre-filter (cheap, before render)
        nd_hits = neverdo_prefilter(comp, doc)
        if nd_hits:
            tele["stage"] = "neverdo-fail"
            telemetry.append(tele)
            log(f"    neverDo prefilter: {nd_hits}")
            repair_note = _repair_note([], nd_hits, [])
            continue

        # 4b. off-grid EXPANSION capability pre-filter (cheap, before render). When the
        # resolved flag is FALSE a novel or off-grid section is illegal -> repair/reject.
        og_hits = offgrid_prefilter(comp, off_grid)
        if og_hits:
            tele["stage"] = "offgrid-fail"
            telemetry.append(tele)
            log(f"    offGrid prefilter (flag off): {og_hits}")
            repair_note = _repair_note([], [], [], offgrid_hits=og_hits)
            continue

        # 5. render (via the Phase-2 adapter)
        try:
            cfc.render_composition(comp, brand_yaml_path, out_dir, style_id=style_id,
                                   brand_dir=brand_yaml_path.parent)
        except Exception as exc:
            failures = [("render", f"{type(exc).__name__}: {exc}")]
            tele["stage"] = "render-fail"
            telemetry.append(tele)
            log(f"    render failed: {type(exc).__name__}: {exc}")
            repair_note = _repair_note([], [], failures)
            continue

        # 6. gate (HARD invariants)
        overall, failures, scorecard = gate_composition(
            out_dir, brand_yaml_path, style_id, layout=layout)
        tele["stage"] = "gated"
        tele["gate_pass"] = overall
        telemetry.append(tele)
        if overall:
            log(f"    gate: PASS")
            (out_dir / "composition.json").write_text(json.dumps(comp, indent=2) + "\n")
            (out_dir / "generation-telemetry.json").write_text(
                json.dumps({"attempts": attempt + 1, "telemetry": telemetry,
                            "model": provider.model,
                            "offGridExpansion": off_grid}, indent=2) + "\n")
            return GenerationResult(composition=comp, ok=True, attempts=attempt + 1,
                                    render_dir=out_dir, scorecard=scorecard,
                                    failures=[], schema_errors=[], neverdo_hits=[],
                                    telemetry=telemetry, prompt_chars=len(prompt),
                                    off_grid_expansion=off_grid, offgrid_hits=[])
        log(f"    gate: FAIL {[c for c, _ in failures]}")
        repair_note = _repair_note([], [], failures)

    # exhausted retries — persist the last attempt for inspection
    if comp is not None:
        (out_dir / "composition.json").write_text(json.dumps(comp, indent=2) + "\n")
    (out_dir / "generation-telemetry.json").write_text(
        json.dumps({"attempts": max_repairs + 1, "telemetry": telemetry,
                    "model": getattr(provider, "model", None), "ok": False,
                    "offGridExpansion": off_grid}, indent=2) + "\n")
    return GenerationResult(composition=comp, ok=False, attempts=max_repairs + 1,
                            render_dir=out_dir, scorecard={}, failures=failures,
                            schema_errors=schema_errs, neverdo_hits=nd_hits,
                            telemetry=telemetry, prompt_chars=len(base_prompt),
                            off_grid_expansion=off_grid, offgrid_hits=og_hits)


# ── CLI: emit the assembled prompt for inspection ─────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Assemble (and inspect) the composition.v1 generation prompt + seeds.")
    ap.add_argument("brand_yaml", type=Path, help="path to the canonical brand.yaml")
    ap.add_argument("--style", default="editorial-luxury", help="style id (styles/<id>.md)")
    ap.add_argument("--brief", type=Path, default=None,
                    help="path to a brief markdown file (defaults to a tiny placeholder)")
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="write the assembled prompt here (else stdout)")
    ap.add_argument("--seeds-only", action="store_true",
                    help="print only the reuse-constraint seed block + resolved pattern ids")
    ap.add_argument("--off-grid", dest="off_grid", type=lambda s: s.lower() in ("1", "true", "yes", "on"),
                    default=None,
                    help="force the off-grid EXPANSION capability on/off (ablation lever); "
                         "default = the base style's offGridExpansion flag")
    args = ap.parse_args()

    doc = load_brand(args.brand_yaml)
    seeds = seed_patterns(doc, args.brand_yaml)

    if args.seeds_only:
        print(f"candidate use-cases: {', '.join(seeds.use_cases)}")
        print(f"resolved patterns:   {', '.join(seeds.pattern_ids()) or '(none)'}\n")
        print(seeds.block or "(empty seed block)")
        return

    brief_text = args.brief.read_text() if args.brief and args.brief.exists() else \
        "Launch signup page: hero headline, three value propositions, and a newsletter signup."
    off_grid = resolve_off_grid_expansion(args.style, doc,
                                          force=args.off_grid if args.off_grid is not None else None)
    print(f"# offGridExpansion (resolved for {args.style}): {off_grid}", flush=True)
    prompt = build_prompt(brief_text, args.brand_yaml, args.style, seeds,
                          off_grid_expansion=off_grid)

    if args.out:
        args.out.write_text(prompt)
        print(f"wrote assembled prompt -> {args.out} ({len(prompt)} chars)")
    else:
        print(prompt)


if __name__ == "__main__":
    main()
