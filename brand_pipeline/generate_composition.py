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

import archetype_library as al      # noqa: E402  (genre structure library — data, not enum)
import layout_library as ll          # noqa: E402  (reuse-before-create: retrieval engine)
import style_scale as ssc            # noqa: E402  (pass-1 derived-scale artifact loader)
import styles as styles_mod          # noqa: E402  (the STYLE layer loader/merge)

REPO_ROOT = _HERE.parent
CONTRACTS_DIR = _HERE / "contracts"
COMPOSITION_RULES_PATH = REPO_ROOT / "styles" / "composition-rules.md"
SCHEMA_PATH = _HERE / "spec" / "composition.v1.schema.json"
ONBRAND_CHECK = _HERE / "onbrand_check.py"

# The grammar file is three layers: YAML front-matter (on-disk registry), the NORMATIVE
# CORE (the only prompt payload), and an extended edition below this sentinel (rationale +
# device detail — on-disk reference, never injected). Split landed 2026-07-14: injecting
# the whole 27KB file cost ~7k tokens/prompt and diluted rule salience; the core carries
# every law + the complete vocabulary at ~1/3 the size (golden: tests/test_grammar_core.py).
GRAMMAR_CORE_SENTINEL = "COMPOSITION-CORE:END"


def grammar_core(raw: str) -> str:
    """Return ONLY the normative core of composition-rules.md: front-matter registry
    stripped, everything at/after ``GRAMMAR_CORE_SENTINEL`` dropped. Degrades safely —
    no front-matter and/or no sentinel → the corresponding cut is skipped (never an
    empty grammar)."""
    _, body = styles_mod.parse_front_matter(raw)
    idx = body.find(GRAMMAR_CORE_SENTINEL)
    if idx != -1:
        # cut at the start of the sentinel's own line (drop the marker comment too)
        cut = body.rfind("\n", 0, idx)
        body = body[:cut if cut != -1 else idx]
    return body.strip() + "\n"

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


def brief_use_cases(brief_text: str) -> list[str]:
    """Infer requested canonical jobs from Markdown headings, preserving page order."""
    aliases = {
        "hero": "hero", "header": "hero", "features": "features", "feature": "features",
        "story": "about", "about": "about", "results": "features", "pricing": "pricing",
        "plans": "pricing", "testimonial": "testimonial", "testimonials": "testimonial",
        "gallery": "gallery", "closing": "cta", "cta": "cta", "faq": "faq",
        "logos": "logos", "footer": "footer",
    }
    found: list[str] = []
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*$", brief_text):
        words = re.findall(r"[a-z]+", heading.lower())
        use_case = next((aliases[word] for word in words if word in aliases), None)
        if use_case and use_case not in found:
            found.append(use_case)
    return found


def relume_precedence_lint(
    composition: dict,
    selections: dict[str, list[str]],
    higher_tier: dict[str, str],
) -> list[tuple[str, str]]:
    """Fail any fallback that competes with a compatible higher-tier source."""
    hits: list[tuple[str, str]] = []
    for section in composition.get("sections") or []:
        if not isinstance(section, dict):
            continue
        sid = str(section.get("id") or "section")
        use_case = str(section.get("useCase") or "")
        provenance = str(section.get("structureProvenance") or "")
        recipe_id = section.get("structureRecipeId")
        if provenance == "relume-fallback":
            if use_case in higher_tier:
                hits.append((sid, f"Relume cannot override {higher_tier[use_case]} for {use_case}"))
            allowed = selections.get(use_case) or []
            if not recipe_id or recipe_id not in allowed:
                hits.append((sid, f"fallback recipe must be one of {allowed or '(none)'}"))
            if section.get("seededFrom"):
                hits.append((sid, "Relume fallback cannot also carry a measured seededFrom"))
        elif recipe_id is not None:
            hits.append((sid, "structureRecipeId is only legal for relume-fallback"))
    return hits


# Existing drawable archetypes have complete generic anatomy for these jobs. Specialist
# jobs (currently pricing and FAQ/disclosure) require a measured/designed recipe or the
# final structural fallback; merely having a drawable stack/cards shell is not compatible.
_GENERIC_ARCHETYPE_USE_CASES = {
    "hero", "features", "testimonial", "gallery", "cta", "about", "logos", "footer",
}


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


def _creative_surface_rules(doc: dict, single_accent: bool,
                            used_surfaces: "list[str] | tuple[str, ...]") -> str:
    """SURFACE SELECTION rule block for creative hero mode (archetype candidates
    injected — spec/archetype-library.md §3 copy-first). Replaces the whole-page
    rhythm MANDATE with the brand's own licensed surface ROSTER: on a standalone
    hero page the rhythm rule ("the observed rhythm opens dark ⇒ the hero MUST be
    inverse") over-applies one licensed band to every gallery member (fix6 root
    cause — 8/8 heroes forced onto the same dark role). Palette-agnostic: every
    line below is derived from tokens.surfaces / surfaceGrammar facts; a brand
    with no dark surface still cannot go dark (the roster simply has none and the
    hard line below says so)."""
    prof = _surface_rhythm_profile(doc)
    surfaces = (doc.get("tokens") or {}).get("surfaces") or {}

    def _is_dark_role(role: str, surf: dict) -> bool:
        # the surface's own schemeMode fact wins (role-name hints misfire on light
        # art bands whose names contain "accent"); hint fallback for brands whose
        # surfaces carry no schemeMode.
        mode = str((surf or {}).get("schemeMode") or "").strip().lower()
        if mode:
            return mode.startswith("inverse")
        return (any(h in role for h in _DARK_ROLE_HINTS)
                or bool(isinstance(surf, dict) and surf.get("textAccent")))

    roster = []
    for role, surf in surfaces.items():
        if not isinstance(surf, dict):
            continue
        suffix = role.split("/", 1)[1] if "/" in role else role
        intent = str(surf.get("intent") or "").split("(")[0].strip().rstrip(";,. ")
        dark = _is_dark_role(role, surf)
        roster.append(
            f"    - \"{suffix}\"{' (dark)' if dark else ''} — {intent or 'declared surface role'}")
    nesting_lines = []
    for n in (doc.get("surfaceGrammar") or {}).get("nesting") or []:
        if isinstance(n, dict) and n.get("child"):
            parents = ", ".join(str(p) for p in (n.get("allowedParents") or []))
            nesting_lines.append(f"    - {n['child']} may nest ONLY on: {parents or '(none)'}")
    used = [str(u) for u in (used_surfaces or []) if str(u).strip()]
    variety = ""
    if used:
        counts: dict[str, int] = {}
        for u in used:
            counts[u] = counts.get(u, 0) + 1
        summary = ", ".join(f"\"{k}\" ×{v}" if v > 1 else f"\"{k}\"" for k, v in counts.items())
        variety = (
            "  GALLERY VARIETY: sibling heroes in this run already chose "
            f"{summary}. Prefer a licensed surface NOT yet used unless this copy plan\n"
            "  genuinely demands a repeat — eight skeletons on one band is monotony,\n"
            "  not fidelity.\n")
    no_dark = ("" if prof["has_dark_surface"] else
               "  This brand declares NO dark surface: \"inverse\"/\"inverse-strong\" are\n"
               "  FORBIDDEN (nothing licensed to paint them with).\n")
    accent_line = (
        "  ACCENT DISCIPLINE: accent-colored TEXT is licensed only on surfaces whose\n"
        "  facts carry a textAccent role; elsewhere accent lives in actions/marks via\n"
        "  the brand catalog (not counted against the text budget).\n"
        if single_accent else "")
    return (
        "- SURFACE SELECTION (creative hero mode — copy-first, spec/archetype-library.md §3):\n"
        "  the hero band's `surfaceIntent` is part of the LAYOUT PLAN, chosen to serve the\n"
        "  copy from this brand's OWN licensed roster (value — evidenced intent):\n"
        + "\n".join(roster) + "\n"
        "  Canonical values (any/primary/panel/inverse/inverse-strong) resolve as usual;\n"
        "  any other value above resolves to the brand's `surface/<value>` role. Never\n"
        "  invent a surface the roster lacks; never repaint slot text to fit a band.\n"
        + ("  NESTING STAYS LICENSED — a panel/form device floats on a band only where\n"
           "  the brand's nesting facts allow that parent:\n" + "\n".join(nesting_lines) + "\n"
           if nesting_lines else "")
        + no_dark + accent_line + variety + _PANEL_INTENT_RULE)


def _brand_fidelity_rules(doc: dict, single_accent: bool,
                          creative_hero_used: "list[str] | tuple[str, ...] | None" = None) -> str:
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
    an inverse band with).

    ``creative_hero_used`` is not-None ONLY when hero archetype candidates are in
    the prompt (creative hero mode): the whole-page rhythm mandate then yields to
    the licensed surface ROSTER (see _creative_surface_rules). Replica-shaped
    composition paths pass None and keep this block byte-identical."""
    if creative_hero_used is not None:
        return _creative_surface_rules(doc, single_accent, creative_hero_used)
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
  - NO SIBLING-SLOT REDUNDANCY (HARD lint, AS-65): no two slots in one section may carry
    the same enumerable content in different registers — a form `note` must never re-list
    the links an adjacent link slot already binds. Keep the structured device; a note is
    for NEW information (what happens next), or omit it.
  - Bind the brief's own facts and vocabulary into slot copy; where the brief is thin for a
    section, derive from the brand's extracted voice/do-avoid evidence — never generic
    marketing filler that could caption any brand.
- PROVEN AUTHORING SHAPES (HARD lints back them — AS-63):
  - ACTIONS are `button` contract slots (or one actionGroup slot whose copy lists action
    objects) — never bare `cta`/`link` strings hoping a composer invents the control.
  - STATS/METRICS: a stat run is ONE `stat`/`stat-block` slot whose copy is an ARRAY of
    {"value": "...", "label": "..."} objects (a single stat may use one such object).
  - PARALLEL BENEFIT ITEMS (3+ short claims) declare list intent (`knobs.supportKind:
    "list"` on form-split heroes, or a `list` contract slot) so they render as the brand's
    marked list, never as look-alike paragraphs.
  - Every `knobs` entry must be a knob the chosen archetype declares or a renderer consumes
    (bandHeight/align/columns/mediaSide/formSide/supportKind/faq/bento/tiers), with a value
    from its declared vocabulary — an unconsumable knob is a HARD lint failure.
- LOGO WALLS (HARD): a `logos` use-case section binds its wall as ONE repeatable slot whose
  `copy` is an ARRAY of {"alt": "<Company>", "asset": "<file>"} objects — each `asset` an
  EXACT filename from the brand-assets list above (the logo files). Never bare strings,
  never invented filenames, and never a text-only wall while real logo assets exist.
- FOOTER (HARD): do NOT compose a footer section. The renderer appends the brand's
  extracted footer chrome to every page, so a model-authored footer renders as a DUPLICATE.
  Omit "footer" from `sections` even when the brief mentions footer content."""

_WIREFRAME_RULES = """
- SECTION WIREFRAME (HARD; a deterministic wireframe.v1 planner validates before render):
  - Every substantive section needs a painted visual anchor: media, proof/stat device,
    meaningful component collection, action cluster, or an explicitly licensed text monument.
  - Preserve repeated semantic records as ONE array on a repeatable `feature-item`,
    `content-block`, `card`, or `testimonial` slot. Never emit their label/body fields as
    sibling primitives in one stack; the item is atomic and responsive collapse preserves it.
  - A side-anchored hero names a real painted counterweight whose complete required slots
    (media/proof/action) have a consuming renderer path. Unsupported skeletons are rejected.
  - Conversion jobs render actions; proof/story jobs render proof, media, or a component
    cluster. Avoid consecutive sparse/text-only sections and alternate density/surface cadence.
"""


# ── PASS 3 (stage 2): pass-1 facts injected as prompt-shaping constraints ──────────
# Pass 2's A/B eval proved pass-1 facts POLICED generation (gates) but never SHAPED
# it — build_prompt was byte-identical with/without them. This block closes exactly
# that gap: derived scale rungs become the allowed geometry vocabulary, brand
# signatures become always/never composition constraints, voice facts become copy
# constraints. PROMPT-SHAPING ONLY — deterministic physics stays in renderers and
# gates. Fact-gated per artifact: a brand carrying none of them keeps a prompt
# byte-identical to the pre-pass-3 assembly.

PASS3_FACTS_BEGIN = "[[PASS3-FACTS:BEGIN]]"
PASS3_FACTS_END = "[[PASS3-FACTS:END]]"


def _fmt_px_list(values) -> str:
    return ", ".join(f"{float(v):g}" for v in (values or []))


def _derived_scale_lines(scale: dict | None) -> list[str]:
    """The derived-scale rungs (style-scale.v1) as the ALLOWED geometry
    vocabulary. Only followsScale blocks speak (a poor fit is never consumed —
    style_scale.py law); absent artifact → []."""
    if not scale:
        return []
    lines: list[str] = []
    t = scale.get("type") or {}
    if t.get("followsScale") and t.get("stepsPx"):
        verdict = ((t.get("fitQuality") or {}).get("verdict") or "").strip()
        lines.append(f"- type rungs(px): {_fmt_px_list(t['stepsPx'])} "
                     f"(base {t.get('basePx'):g}px · ratio {t.get('ratio')}"
                     + (f" · fit {verdict}" if verdict else "") + ")")
    s = scale.get("space") or {}
    if s.get("followsScale") and s.get("stepsPx"):
        lines.append(f"- space steps(px): {_fmt_px_list(s['stepsPx'])} "
                     f"(base unit {s.get('baseUnitPx')}px)")
        rhythm = s.get("sectionRhythmPx") or []
        if rhythm:
            lines.append(f"- section rhythm(px): {_fmt_px_list(rhythm)} — bandHeight "
                         "knob magnitudes ride these rungs")
    r = scale.get("radius") or {}
    if r.get("modes"):
        modes = " · ".join(
            f"{float(m.get('px', 0)):g}px({','.join(map(str, m.get('roles') or []))})"
            for m in r["modes"])
        lines.append(f"- radius modes: {modes}"
                     + (f" (policy {r.get('policy')})" if r.get("policy") else ""))
    m = scale.get("motion") or {}
    band = m.get("bandMs") or {}
    if band:
        lines.append(f"- motion band: {band.get('min')}–{band.get('max')}ms"
                     + (f", easing {m.get('easing')}" if m.get("easing") else ""))
    return lines


def _signature_lines(doc: dict) -> list[str]:
    """The brand's pass-1 `signatures:` (brand-schema §4.7) as always/never
    composition constraints — claims verbatim (they ARE the constraint prose)."""
    lines: list[str] = []
    for sig in (doc.get("signatures") or []):
        if not isinstance(sig, dict) or not sig.get("id"):
            continue
        claim = " ".join(str(sig.get("claim") or "").split())
        lines.append(f"- [{sig.get('mode', '?')}] {sig.get('id')} "
                     f"({sig.get('kind', '')}): {claim}")
    return lines


def _voice_lines(facts: dict | None) -> list[str]:
    """voice-facts.v1 gate budgets as copy constraints (voice_audit.py audits
    the same numbers post-hoc; stating them up front is the shaping half)."""
    if not facts:
        return []
    lines: list[str] = []
    sen = facts.get("sentences") or {}
    gate = sen.get("gate") or {}
    if gate:
        measured = []
        if sen.get("meanWords") is not None:
            measured.append(f"measured mean {sen['meanWords']}w")
        if sen.get("p90Words") is not None:
            measured.append(f"p90 {sen['p90Words']}w")
        if sen.get("maxWords") is not None:
            measured.append(f"max {sen['maxWords']}w")
        lines.append(f"- sentences: mean ≤{gate.get('meanWordsMax')}w, "
                     f"p90 ≤{gate.get('p90WordsMax')}w"
                     + (f" ({'; '.join(measured)})" if measured else "")
                     + " — write brand-length sentences, never run-ons")
    excl = ((facts.get("punctuation") or {}).get("exclamations") or {})
    if (excl.get("gate") or {}).get("max") is not None:
        lines.append(f"- exclamation marks: max {excl['gate']['max']} "
                     "(the captured corpus has none)")
    casing = facts.get("casing") or {}
    h_rule = ((casing.get("headings") or {}).get("rule"))
    if h_rule:
        lines.append(f"- headings: {h_rule} case (brand/product terms keep their "
                     "capitals; never title-case a heading)")
    cta_rule = ((casing.get("ctas") or {}).get("rule"))
    if cta_rule:
        lines.append(f"- CTA labels: {cta_rule} case; prefer verb-led labels")
    lex = ((facts.get("bannedHype") or {}).get("lexicon") or [])
    if lex:
        lines.append("- banned words (the captured corpus never uses them): "
                     + ", ".join(str(w) for w in lex))
    tone = ((facts.get("tone") or {}).get("descriptors") or [])
    if tone:
        lines.append("- tone: " + ", ".join(str(t) for t in tone))
    return lines


def load_voice_facts(brand_dir: Path | str | None) -> dict | None:
    """Parsed voice-facts.yaml for a brand run dir, or None (absent/invalid) —
    same fact-gating shape as style_scale.load_style_scale."""
    if not brand_dir:
        return None
    path = Path(brand_dir) / "voice-facts.yaml"
    if not path.exists():
        return None
    try:
        facts = yaml.safe_load(path.read_text())
    except Exception:
        return None
    if not isinstance(facts, dict) or facts.get("schema") != "voice-facts.v1":
        return None
    return facts


def _accent_device_lines(doc: dict) -> list[str]:
    """The brand's LICENSED accent devices (brand.yaml `accentDevices:`, fix7 —
    brand-schema §4.11) as prompt constraints riding the pass-3 signature
    injection: kind + how the renderer applies it + per-context floors."""
    lines: list[str] = []
    for dev in (doc.get("accentDevices") or []):
        if not isinstance(dev, dict) or not dev.get("kind"):
            continue
        bits = [f"- [{dev.get('kind')}] {dev.get('id', '')}"]
        if dev.get("mark"):
            bits.append(f"mark {dev['mark']!r}")
        glyph = (dev.get("glyph") or {}).get("asset") if isinstance(dev.get("glyph"), dict) else None
        if glyph:
            bits.append(f"glyph {glyph}")
        ctxs = []
        for c in (dev.get("contexts") or []):
            if isinstance(c, dict) and c.get("context"):
                tag = str(c["context"])
                if c.get("floor") is not None:
                    tag += f" floor {c['floor']}"
                if c.get("ceiling") is not None:
                    tag += f" ceiling {c['ceiling']}"
                ctxs.append(tag)
        if ctxs:
            bits.append("contexts: " + ", ".join(ctxs))
        lines.append(" — ".join(bits))
    if lines:
        lines.append("A landmark (hero/closing) band must CARRY at least its floor of "
                     "licensed devices: close a landmark heading with the licensed "
                     "mark, or declare list intent so benefit runs render the marked "
                     "list. Never invent an unlicensed accent device.")
    return lines


def pass1_facts_block(doc: dict, brand_dir: Path | str | None) -> str:
    """Assemble the pass-1 facts injection block ("" when the brand carries NO
    pass-1 artifact — the graceful-degradation contract: prompt byte-identical
    to the pre-pass-3 assembly). Deterministic for fixed artifact bytes."""
    scale = ssc.load_style_scale(brand_dir)
    scale_lines = _derived_scale_lines(scale)
    sig_lines = _signature_lines(doc)
    device_lines = _accent_device_lines(doc)
    voice_lines = _voice_lines(load_voice_facts(brand_dir))
    if not (scale_lines or sig_lines or device_lines or voice_lines):
        return ""
    parts = [PASS3_FACTS_BEGIN,
             "## Pass-1 brand facts (measured/derived — SHAPE the composition to these)"]
    if scale_lines:
        parts += [
            "### Derived scale rungs — the ALLOWED geometry vocabulary",
            *scale_lines,
            "Where no measured fact answers a magnitude (knob values, band heights,",
            "type steps for novel geometry), pick FROM these rungs — never invent an",
            "off-ladder number (the scale_adherence gate audits exactly this).",
        ]
    if sig_lines:
        parts += [
            "### Brand signatures — always/never composition constraints "
            "(signature_check gate verifies each)",
            *sig_lines,
        ]
    if device_lines:
        parts += [
            "### Licensed accent devices — floors are REQUIRED, roster is CLOSED "
            "(signature gate verifies floors; fix7)",
            *device_lines,
        ]
    if voice_lines:
        parts += [
            "### Voice constraints — the copy budget (voice gate audits these)",
            *voice_lines,
        ]
    parts.append(PASS3_FACTS_END)
    return "\n".join(parts)


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
                 seeds: SeedResult | str, off_grid_expansion: bool = True,
                 hero_candidates: str | None = None,
                 used_surfaces: "list[str] | tuple[str, ...] | None" = None,
                 conversion_guidance: str | None = None,
                 style_directives: str | None = None,
                 section_recipe_guidance: str | None = None) -> str:
    """Deterministically assemble the system/user prompt for the composition generator.

    Assembly order (mirrors styles/composition-rules.md ``## Assembly``):
      1. universal composition grammar — the NORMATIVE CORE only (grammar_core():
         front-matter registry + extended edition below the sentinel stay on disk)
      1b. the off-grid EXPANSION capability gate (unlock/lock — Part B)
      2. merged base STYLE (styles.load_and_merge -> invariants, soft options, scales, floor)
      3. brand facts (token color roles, neverDo, measured type tiers, spacing steps)
      3b. PASS-1 FACTS block (pass 3 stage 2 — derived scale rungs as the allowed
          geometry vocabulary, brand signatures as always/never composition
          constraints, voice facts as copy constraints; delimited by
          [[PASS3-FACTS:BEGIN/END]]. Fact-gated PER ARTIFACT: a brand carrying no
          pass-1 artifact keeps the prompt byte-identical to the pre-pass-3 assembly.)
      4. primitives/blocks catalog signatures
      5. SEED constraints (render_pattern_constraint block from seed_patterns)
      5b. HERO STRUCTURE CANDIDATES (genre archetype shortlist — only when the caller
          resolved one; see archetype_library.render_candidate_block. Absent -> the
          assembled prompt is byte-identical to the pre-archetype prompt.)
      5c. STYLE DIRECTIVE block (pass 3 stage 2 — a caller-resolved style-library
          directive rendered by style_resolver.render_style_directive_block, riding
          [[PASS3-STYLE:BEGIN/END]] sentinels. Absent -> byte-identical. Guidance
          only: it never outranks brand facts/neverDo or the gate battery.)
      5d. SECTION RECIPE CANDIDATES (Relume-derived structural priors normalized into
          recipe families + responsive transitions; absent -> byte-identical)
      6. the brief copy [+ 6b. CONVERSION-STRUCTURE guidance — only when the caller
         resolved one via conversion_structure.render_guidance_block; same fact-gated
         byte-identity contract as 5b, riding WITH the brief in the user prompt]
         [+ 6c. MEDIA SEMANTICS block — media-assets.v1 inventory digest + the HARD
         binding rule + the no-match ladder, [[MEDIA-FACTS:BEGIN/END]]; fact-gated:
         brands without media-assets.yaml keep the prompt byte-identical]
         + the output contract (emit ONE composition.v1 object)

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

    grammar = grammar_core(COMPOSITION_RULES_PATH.read_text()) if COMPOSITION_RULES_PATH.exists() else \
        "(styles/composition-rules.md not found)"

    nd_lines = [f"- {rid}: {stmt}" for rid, stmt in facts["neverDo"]]

    # 3b. PASS-1 FACTS (pass 3 stage 2) — "" for artifact-less brands, which keeps
    # every byte of the assembly below identical to the pre-pass-3 prompt.
    p1_block = pass1_facts_block(doc, Path(brand_yaml_path).parent)
    pass1_section = f"\n{p1_block}\n" if p1_block else ""

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
{pass1_section}
## Primitive palette (contracts/primitives.yaml — use only these keys)
{chr(10).join(primitive_signatures())}

## Block grammar (contracts/blocks.yaml — respect accepts / ?optional / *repeatable)
{chr(10).join(block_signatures())}

## SEED constraints (reuse-before-create; use-cases: {seed_use_cases})
{seed_block or '(no reuse patterns matched — compose from the palette; novelty:novel expected)'}
"""
    # 5b. genre archetype candidates — a caller-resolved shortlist (structure-variable
    # lane). Fact-gated: absent/empty keeps the prompt byte-identical.
    if hero_candidates:
        system += "\n" + hero_candidates.strip() + "\n"

    # 5c. style-library directive block (pass 3 stage 2) — caller-resolved via
    # style_resolver.render_style_directive_block. Same byte-identity contract.
    if style_directives:
        system += "\n" + style_directives.strip() + "\n"

    # 5d. external section-recipe priors — metadata/source-derived structure only.
    # They guide archetype/slots/knobs and responsive behavior; they never supply
    # styling, copy, tokens, or a seededFrom ref.
    if section_recipe_guidance:
        system += "\n" + section_recipe_guidance.strip() + "\n"

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

    # MEDIA SEMANTICS block (media-assets.v1, 2026-07) — fact-gated exactly like the
    # pass-1 injection: a brand without media-assets.yaml keeps every byte of the
    # assembled prompt identical. With the artifact, the compact inventory digest
    # (ids/kinds/aspects/rights/luminance) + the HARD binding rule + the no-match
    # ladder ride with the asset rules ([[MEDIA-FACTS:BEGIN/END]] sentinels).
    import media_semantics as ms
    media_block = ms.media_rules_block(ms.load_media_assets(brand_dir))
    media_rules = f"\n{media_block}\n" if media_block else ""

    # 6b. conversion-structure guidance (steal 3) — fact-gated: None keeps the user
    # prompt byte-identical (same contract as hero_candidates in the system prompt).
    guidance_block = f"\n{conversion_guidance.strip()}\n" if conversion_guidance else ""
    user = f"""# USER — brief

{brief_text.strip()}
{guidance_block}
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
  "structureProvenance": one of ["measured-brand-pattern","designed-brand-pattern","brand-style-archetype","relume-fallback"],
  "structureRecipeId": "<selected Relume recipe id>" ONLY for relume-fallback, otherwise null,
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
  `asset: null` for slots where nothing in the list fits.{media_rules}
{_brand_fidelity_rules(doc, single_accent,
                       creative_hero_used=((used_surfaces or []) if hero_candidates else None))}{_COPY_QUALITY_RULES}{_WIREFRAME_RULES}
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


_TOP_LEVEL_KEYS = ("schemaVersion", "brief", "brand", "style", "sections", "rationale")


def normalize_top_level(comp: dict, *, brief_id: str, brand_ref: str, style_id: str) -> dict:
    """Fill/repair the DETERMINISTIC scaffolding fields the caller already knows
    (schemaVersion, brief.id, brand.ref, style.id) so the model spends its budget on the
    creative section work, not boilerplate. Also coerces the two common shape slips
    (style/brand emitted as a bare string) into their object form, and DROPS unknown
    TOP-LEVEL keys (a model sometimes appends commentary objects like a fidelity
    self-review; the schema forbids them and nothing reads them — deleting the key is
    the same mechanical scaffolding repair as the shape coercions, and never touches
    section content). Idempotent."""
    if not isinstance(comp, dict):
        return comp
    for key in [k for k in comp if k not in _TOP_LEVEL_KEYS]:
        comp.pop(key)
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


def _auto_style_directives(style_id: str, brand_yaml_path: Path | str,
                           *, log=print) -> str | None:
    """Auto-resolve the ALREADY-CHOSEN style through the style-library resolver and
    render its pass-3 stage-2 prompt block (style_resolver.render_style_directive_block).

    Gated on PRESET presence: a style with no preset (e.g. ``dark-mode``, the 1/51
    uncovered id) and any non-library style id (e.g. a base-only ``styles/<id>.md``
    id like ``corporate-saas-clean``) return None, so the assembled prompt stays
    BYTE-IDENTICAL to the pre-wiring assembly — this is the feature's fact-gated
    contract (only preset-backed ids gain a block). A preset-backed id
    (``swiss``/``bauhaus``/…) returns the resolved block with its authored preset
    defaults folded in UNDER any measured brand fact (the resolver owns precedence
    + dissent logging; nothing here changes it).

    FAIL-OPEN: a missing/unloadable style-library or ANY resolver error degrades
    to None (no block, no crash). This is a live generation path — prompt shaping
    must never take a run down."""
    try:
        import style_resolver as sr
        library = sr.load_library()
        if style_id not in library.presets:
            return None                       # no preset → byte-identical (no block)
        bundle = sr.load_brand_bundle(Path(brand_yaml_path).parent)
        resolutions = sr.resolve_all(style_id, library, bundle)   # all sections
        return sr.render_style_directive_block(style_id, resolutions, library) or None
    except Exception as exc:                   # fail-open: shaping never crashes a run
        log(f"  style directives: auto-resolution skipped ({type(exc).__name__})")
        return None


def _resolve_style_directives(style_directives: str | None, style_id: str,
                              brand_yaml_path: Path | str, *, log=print) -> str | None:
    """Style-directive precedence for the generate path: an EXPLICIT caller value
    WINS (a non-None value is honored verbatim, including ``""`` = suppress);
    ONLY when the caller supplies nothing (``None``) does the default path
    auto-resolve the picked style. Explicit-wins + opt-out preserved; the library
    loads at most once (inside ``_auto_style_directives``) and never when the
    caller opted out."""
    if style_directives is not None:
        return style_directives               # explicit-wins / opt-out ("" suppresses)
    return _auto_style_directives(style_id, brand_yaml_path, log=log)


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
                         page_type: str | None = None,
                         task_intents: list[str] | None = None,
                         genre: str = "heroes-saas",
                         variance: str = "mid",
                         exclude_archetypes: tuple[str, ...] = (),
                         used_surfaces: tuple[str, ...] = (),
                         inject_conversion_guidance: bool = False,
                         style_directives: str | None = None,
                         section_recipe_guidance: str | None = None,
                         enable_relume_fallback: bool = False,
                         enforce_gates: bool = True,
                         replica_bar: float | None = None,
                         log=print) -> GenerationResult:
    """Generate a validated + on-brand ``composition.v1`` for the brief via ONE structured
    call to the repo's Anthropic client, then a bounded validate → neverDo-prefilter →
    render → gate → repair loop (≤ ``max_repairs`` retries).

    FAIL-CLOSED (2026-07-17): when ``enforce_gates`` is True (the default), page
    generation REFUSES to run for a brand whose lane has not cleared the canonical
    ordered gates (G1 extraction → G2 validation → G3 harness → G4 replica ≥ bar).
    The refusal reads the lane's ``flow-report.json`` (written by the orchestrator,
    ``pipeline_flow.run_flow``) or falls back to ``manifest.json`` — a
    ``needs_iteration`` / ``blocked`` lane, a below-bar replica, or a lane with no
    flow record raises ``pipeline_flow.GenerationBlocked``. This closes the exact
    hole that let a run go extract → generation on a 0.543 replica. Pass
    ``enforce_gates=False`` only for isolated experiments that deliberately skip
    the gate.

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

    brand_yaml_path = Path(brand_yaml_path)
    # FAIL-CLOSED GATE: refuse to generate for a lane that has not cleared the
    # canonical ordered gates. Checked BEFORE any output dir / model work so an
    # ungated lane never produces a page. (pipeline_flow imported lazily to avoid
    # an import cycle — it imports this module for its own G5.)
    if enforce_gates:
        import pipeline_flow as _pf
        bar = _pf.DEFAULT_REPLICA_BAR if replica_bar is None else replica_bar
        _pf.assert_generation_allowed(brand_yaml_path.parent, bar)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = load_brand(brand_yaml_path)
    schema = _load_schema()
    if seeds is None:
        seeds = seed_patterns(doc, brand_yaml_path)
    # resolve the off-grid EXPANSION capability for this run: an explicit force (the ablation
    # lever) wins, else the base style's offGridExpansion flag decides.
    off_grid = resolve_off_grid_expansion(style_id, doc, force=force_off_grid)
    log(f"  offGridExpansion={off_grid}"
        + (f" (forced {force_off_grid})" if force_off_grid is not None else " (from style)"))

    # HERO STRUCTURE CANDIDATES (archetype-library selection, spec/archetype-library.md
    # §3). Fact-gated three ways: the brief must declare a pageType (frontmatter or
    # kwarg), the genre library must exist, and the run must have off-grid expansion
    # (a locked style composes from captured patterns only — no candidates). Absent any
    # of these the prompt is byte-identical to the pre-archetype assembly.
    meta, brief_body = al.parse_brief_frontmatter(brief_text)
    pt = (page_type or meta.get("pageType") or "").strip().lower()
    tis = task_intents if task_intents is not None else (meta.get("taskIntents") or [])
    gen = str(meta.get("genre") or genre or "").strip()
    var = str(meta.get("variance") or variance or "mid").strip().lower()
    exclude = tuple(dict.fromkeys(
        [str(x) for x in (meta.get("excludeArchetypes") or [])]
        + [str(x) for x in (exclude_archetypes or ())]))
    require_archetype = bool(meta.get("requireArchetype"))
    hero_candidates = None
    cand_ids: set[str] = set()
    if off_grid and pt and gen and al.genre_available(gen):
        cands = al.shortlist(al.load_genre(gen), pt, tis, variance=var,
                             brand_hero=al.brand_hero_structure(doc),
                             off_grid=off_grid, exclude=exclude)
        if cands:
            hero_candidates = al.render_candidate_block(cands)
            cand_ids = {str(c.get("id")) for c in cands}
            log(f"  hero archetype candidates ({gen}/{pt}): {sorted(cand_ids)}")

    # CONVERSION-STRUCTURE guidance (steal 3) — DOUBLY fact-gated: the caller must
    # opt in (flag, default False — the pass-3 injection-architecture decision stays
    # open) AND the brief must declare a known campaignType. Absent either, the
    # prompt is byte-identical to the un-guided assembly (test-pinned).
    conv_guidance = None
    if inject_conversion_guidance:
        import conversion_structure as conv_mod
        conv_guidance = conv_mod.render_guidance_block(brief_text)
        if conv_guidance:
            log(f"  conversion guidance: campaign={meta.get('campaignType')}")

    # STYLE DIRECTIVE block (pass 3 stage 2). AUTO-RESOLUTION (2026-07-17): the
    # default path now resolves the ALREADY-CHOSEN style_id through the
    # style-library resolver and injects render_style_directive_block output, so
    # presets shape EVERY generation — not just opt-in lanes. An EXPLICIT caller
    # value still wins (a non-None style_directives is honored verbatim, incl.
    # "" = suppress); a style with no preset, a non-library style id, a missing
    # library, or any resolver error DEGRADES SILENTLY to no block (byte-identical
    # to the pre-wiring assembly). Resolved HERE (not inside build_prompt) so the
    # assembler stays pure, the explicit-wins/opt-out guard is honored, and the
    # library loads at most once per generation.
    style_directives = _resolve_style_directives(
        style_directives, style_id, brand_yaml_path, log=log)
    if style_directives:
        log("  style directives: injected "
            f"({len(style_directives)} chars)")

    # SECTION RECIPE guidance. Explicit caller input wins (including "" to suppress).
    # Automatic resolution is strictly fallback-only: jobs with measured seeds or a
    # compatible injected archetype are excluded before Relume retrieval.
    relume_selections: dict[str, list[str]] = {}
    higher_tier = {
        use_case: "measured-brand-pattern"
        for use_case in (seeds.matches if isinstance(seeds, SeedResult) else {})
    }
    for use_case in _GENERIC_ARCHETYPE_USE_CASES:
        higher_tier.setdefault(use_case, "brand-style-archetype")
    if hero_candidates:
        higher_tier.setdefault("hero", "brand-style-archetype")
    if section_recipe_guidance is None and enable_relume_fallback:
        try:
            import relume_recipe_catalog as recipe_catalog
            requested = brief_use_cases(brief_body)
            ingredients = {
                use_case: tuple(
                    ingredient for ingredient, marker in (
                        ("cards", "card"), ("actions", "action"), ("media", "asset"),
                        ("plans", "pricing"), ("form", "form"), ("logos", "logo"),
                    ) if marker in brief_body.lower()
                )
                for use_case in requested
            }
            section_recipe_guidance, relume_selections = recipe_catalog.fallback_guidance(
                requested,
                higher_tier=higher_tier,
                ingredients_by_use_case=ingredients,
                top_k=3,
            )
            section_recipe_guidance = section_recipe_guidance or None
        except Exception as exc:
            raise RuntimeError(
                f"Relume fallback resolution failed closed: {type(exc).__name__}: {exc}"
            ) from exc
    elif section_recipe_guidance is None:
        section_recipe_guidance = None
    if section_recipe_guidance:
        import relume_recipe_catalog as recipe_catalog
        recipe_catalog.assert_prompt_safe(section_recipe_guidance)
        log(f"  section recipes: injected ({len(section_recipe_guidance)} chars)")

    base_prompt = build_prompt(brief_body, brand_yaml_path, style_id, seeds,
                               off_grid_expansion=off_grid,
                               hero_candidates=hero_candidates,
                               used_surfaces=tuple(meta.get("usedSurfaces") or ())
                               or tuple(used_surfaces or ()),
                               conversion_guidance=conv_guidance,
                               style_directives=style_directives,
                               section_recipe_guidance=section_recipe_guidance)

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

        # 3b. archetype-selection contract (gallery/structure lanes): when the brief
        # declares ``requireArchetype: true`` AND candidates were injected, the hero
        # section MUST record one of the offered ids as archetypeRef (a repairable
        # contract violation, not a schema error).
        if require_archetype and cand_ids:
            hero_refs = [str(s.get("archetypeRef") or "").strip()
                         for s in (comp.get("sections") or [])
                         if isinstance(s, dict) and _is_hero_section(s)]
            if not hero_refs or any(r not in cand_ids for r in hero_refs):
                failures = [("archetype-selection",
                             f"the hero section must set archetypeRef to ONE of "
                             f"{sorted(cand_ids)} (got {hero_refs or 'none'})")]
                tele["stage"] = "archetype-fail"
                telemetry.append(tele)
                log(f"    archetype selection: {failures[0][1]}")
                repair_note = _repair_note([], [], failures)
                continue

        precedence_hits = relume_precedence_lint(comp, relume_selections, higher_tier)
        if precedence_hits:
            failures = [
                ("relume-precedence", f"section `{sid}`: {message}")
                for sid, message in precedence_hits
            ]
            tele["stage"] = "relume-precedence-fail"
            telemetry.append(tele)
            log(f"    Relume precedence: {precedence_hits}")
            repair_note = _repair_note([], [], failures)
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

        # 4c. composition lints (fix7 AS-63/AS-65, cheap, before render): a knob with
        # no consumer / an unconsumable value, or two sibling slots enumerating the
        # same content in different registers — HARD, repairable (the model gets the
        # exact hits back, same loop shape as the neverDo prefilter).
        import composition_lint
        lint_hits = composition_lint.lint_composition(comp)
        if lint_hits:
            failures = [(f"composition-lint:{rule}", f"section `{sid}`: {msg}")
                        for sid, rule, msg in lint_hits]
            tele["stage"] = "lint-fail"
            telemetry.append(tele)
            log(f"    composition lint: {[(s, r) for s, r, _ in lint_hits]}")
            repair_note = _repair_note([], [], failures)
            continue

        # 4d. media-binding lints (media semantics 2026-07, AS-67): every media slot
        # resolves an asset or declares its gap; refs resolve; third-party marks stay
        # in factual proof contexts. Fact-gated: brands without media-assets.yaml
        # never reach this branch (registry None → zero hits).
        import media_semantics as ms
        media_hits = ms.lint_media_bindings(
            comp, ms.load_media_assets(brand_yaml_path.parent))
        if media_hits:
            failures = [(f"media-lint:{rule}", f"section `{sid}`: {msg}")
                        for sid, rule, msg in media_hits]
            tele["stage"] = "media-lint-fail"
            telemetry.append(tele)
            log(f"    media lint: {[(s, r) for s, r, _ in media_hits]}")
            repair_note = _repair_note([], [], failures)
            continue

        # 4e. WHOLE-PAGE WIREFRAME (wireframe.v1): deterministic copy-shape/job/media
        # planning runs after the structured composition exists but BEFORE any HTML is
        # designed.  It validates renderer capability, semantic grouping, visual
        # anchors/cadence, and required-slot consumption.  The artifact is persisted
        # only for a buildable attempt; a failure is repairable and never reaches HTML.
        import section_wireframe as sw
        wireframe = sw.plan_wireframe(comp)
        wire_errors = sw.validate_wireframe(wireframe, comp)
        advanced_hits = composition_lint.lint_wireframe_quality(comp, wireframe)
        if wire_errors or advanced_hits:
            failures = [
                ("wireframe", message) for message in wire_errors
            ] + [
                (f"composition-lint:{rule}", f"section `{sid}`: {message}")
                for sid, rule, message in advanced_hits
            ]
            tele["stage"] = "wireframe-fail"
            telemetry.append(tele)
            log(f"    wireframe: {len(failures)} hard failure(s)")
            repair_note = _repair_note([], [], failures)
            continue
        (out_dir / "wireframe.json").write_text(json.dumps(wireframe, indent=2) + "\n")

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
