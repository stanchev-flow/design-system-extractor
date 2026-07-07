#!/usr/bin/env python3
"""wildcard_generator.py - machine-PROPOSED magic-trick candidates (human-BLESSED).

A pattern library is a machine for converging on the brand's median — reuse-before-create
is, by design, an anti-originality force. This generator automates the two-thirds of the
"magic trick" that CAN be automated: producing genuinely divergent, gate-checked,
renderable candidates. The third that can't — picking the one that lands for THIS room on
THIS night — stays human: candidates land in ``magic-trick.md`` as PROPOSALS, and only a
human marking one BLESSED gives it any authority (scope: one-off, wildcardScope rules,
brand-schema.md §4.3).

Three divergence strategies (one candidate each):

  1. DIAL-CRANK   — ``ghost-colossal``: the editorial ghost watermark at ~3x scale, from
                    "texture behind content" to "the wall itself". Bends: the variance
                    dial only (no rule).
  2. AVOID-INVERT — ``centered-monument``: the mission statement dead-centered as a
                    monument. Deliberately inverts ``avoid.prefer-asymmetry`` (a SOFT
                    rule — sanctioned to bend, logged, never promoted).
  3. TRANSPLANT   — ``hero-ghost``: the HERO's content in the about-run's ghost-word
                    collage grammar — a use-case transplant the retrieval engine would
                    never pick on its own (hero queries score the collage pattern below
                    the reuse threshold; that gap IS the novelty).

Every candidate renders to ``runs/<brand>/brand/variants/wildcard-<id>/`` with a
``label.txt`` — the Studio lane dropdown (studio_server.variant_pages) discovers them
automatically, side-by-side with the median page, so a human can curate visually. Each is
then gate-checked (onbrand_check) and written into ``magic-trick.md`` with its novelty
evidence, the rule it bends, and its gate verdict. Never blesses anything itself.

Usage:
  python3 brand_pipeline/wildcard_generator.py runs/<brand>/brand/brand.yaml [--style <id>]
"""
from __future__ import annotations

import argparse
import copy
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose_page as cp  # noqa: E402
import compose_section as cs  # noqa: E402
import layout_library as ll  # noqa: E402
from styles import FreedomBudget, inactive_context, load_and_merge  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── candidate definitions ────────────────────────────────────────────────────────

def _first_layout_of_scaffold(doc, scaffold: str) -> str | None:
    """The FIRST page layout (page order) composing through the given scaffold family,
    or None when this brand's page has no section of that grammar."""
    for lid in page_layout_ids(doc):
        if cs.scaffold_key(cs.find_layout(doc, lid)) == scaffold:
            return lid
    return None


def _candidates(doc: dict) -> list[dict]:
    """Each candidate: which SCAFFOLD grammar to start from (resolved to the ACTIVE
    brand's first layout of that family — a brand without the grammar skips the
    candidate, logged), an optional in-memory layout mutation, optional extra copy
    (registered into LAYOUT_COPY at runtime), a scoped CSS override (the divergence
    itself), and the honest record of what it bends.

    Candidate copy comes from the ACTIVE brand's section-copy.yaml ``wildcardCopy:``
    (keyed by candidate id) — a candidate that NEEDS copy the brand doesn't carry is
    omitted with a logged reason, never seeded from another brand's voice."""
    wc = cs.brand_wildcard_copy(doc)
    cands = [
        {
            "id": "ghost-colossal",
            "label": "Wildcard — Ghost at 3× (dial-crank)",
            "base_scaffold": "collage",
            "strategy": "dial-crank",
            "bends": "voice.dials.variance only — no rule. The ghost watermark goes from "
                     "texture (6% ink, behind content) to THE WALL ITSELF; everything else "
                     "is unchanged.",
            "css": """
/* WILDCARD ghost-colossal: the watermark IS the section. Same token, same opacity
   discipline (ghost ink), ~3x scale, allowed to bleed the section box. */
.cs-collage-sec { overflow: visible; }
.cs-ghost { font-size: clamp(24rem, 95cqw, 70rem) !important; top: -12% !important;
  right: -8cqw !important; line-height: 0.78 !important; }
""",
        },
        {
            "id": "centered-monument",
            "label": "Wildcard — Centered monument (avoid-invert)",
            "base_scaffold": "statement",
            "strategy": "avoid-invert",
            "bends": "avoid.prefer-asymmetry (SOFT rule — sanctioned to bend as a one-off, "
                     "logged, never promoted). The statement runs dead-centered, stacked, "
                     "media beneath like an altarpiece — the one centered editorial moment "
                     "on a page that is otherwise deliberately anchored left.",
            # AS-18/AS-19: the inversion is now DECLARED (section-explicit alignment ->
            # data-align-source="section") instead of raw CSS fighting the scaffold. The
            # composer's resolved-centered anchor supplies the SYMMETRIC statement spans
            # (text 3/-3, media 4/-4), fixing the old misregistration where the media
            # kept its 6/-1 editorial offset (an out-of-range grid-column once the old
            # override collapsed the grid to 1fr) and sat right-shifted under the
            # centered text. The CSS below only adds the monument rhythm/measure.
            "mutate": lambda lay: {**copy.deepcopy(lay),
                                   "alignment": {"anchor": "centered"}},
            "css": """
/* WILDCARD centered-monument: deliberate inversion of avoid.prefer-asymmetry.
   Anchor is DECLARED (alignment.anchor=centered -> symmetric spans via AS-19);
   this override adds only the altarpiece rhythm + measure. */
.cs-statement-grid { row-gap: 3.5rem; }
.cs-statement-text { max-width: 40ch !important; }
.cs-statement-media { width: min(100%, 46rem); margin-inline: auto; }
""",
        },
        {
            "id": "hero-ghost",
            "label": "Wildcard — Hero in ghost-word grammar (transplant)",
            "base_scaffold": "collage",
            "strategy": "use-case transplant",
            "bends": "no rule — a USE-CASE transplant: the hero's content set in the "
                     "about-run's ghost-word collage grammar (the colossal ghost word "
                     "behind the opening statement) instead of the brand's own hero "
                     "pattern.",
            "mutate": lambda lay: {**copy.deepcopy(lay), "id": "wildcard-hero-ghost"},
            # copy REQUIRED: the transplant re-voices the hero in the collage grammar —
            # its copy block lives in the brand's section-copy.yaml wildcardCopy:
            # (key = candidate render id). No block -> candidate omitted below.
            "needs_copy": "wildcard-hero-ghost",
            # hero copy tends to carry far longer words than the collage grammar was
            # measured for — at the style's full poster scale the heading overflows its
            # grid column and collides with the body text (anti-ai-slop.md AS-03 shape:
            # a transplant inherits the target grammar's sizing assumptions; re-fit the
            # display scale to the LONGEST WORD of the transplanted copy, don't assume).
            "css": """
/* WILDCARD hero-ghost: display tier re-fit for hero-length words in the collage column. */
.cs-collage-head .c-heading--display { font-size: clamp(2.75rem, 7.6cqw, 7rem);
  max-width: 14ch; overflow-wrap: normal; }
""",
        },
    ]
    out = []
    for cand in cands:
        scaffold = cand.pop("base_scaffold")
        lid = _first_layout_of_scaffold(doc, scaffold)
        if lid is None:
            print(f"  (skip: candidate '{cand['id']}' needs a '{scaffold}'-scaffold "
                  f"section this brand's page doesn't compose — page sections: "
                  f"{', '.join(page_layout_ids(doc))})")
            continue
        cand["base_layout"] = cand["gate_layout"] = lid
        key = cand.pop("needs_copy", None)
        if key is not None:
            if key not in wc:
                print(f"  (skip: candidate '{cand['id']}' needs wildcardCopy['{key}'] "
                      f"in the brand's section-copy.yaml — not declared)")
                continue
            cand["copy"] = {key: wc[key]}
        out.append(cand)
    return out


# ── FREEDOM BUDGET (per-section 0-5 magic-trick allowance) ───────────────────────
#
# The LEVEL DEFINITIONS live in the STYLE LAYER: each base style's front-matter carries a
# ``freedomBudget:`` block (default level + ceiling + qualitative per-level definitions,
# parsed by styles.py into FreedomBudget). The intensity ladder below documents what the
# MACHINERY here implements per level; what a level MEANS for a given style (what it
# unlocks/forbids, expressed in that style's own vocabulary) is the style's declaration.
#
# The interaction protocol: before generating, the agent prints the page's sections
# (``--list-sections``) — each PRE-FILLED with the level resolved from the style layer
# (brand ``voice.dials.freedom`` LEVEL choice clamped to the style ceiling, else the
# style default) — and the user may adjust and paste the list back (``--budget
# "hero 1 about 3 cta 0"`` — names are the brand's layout ids or canonical use-cases).
# Without ``--budget``, the style-resolved level applies to every section (the template
# is FILLED by the style layer, never left blank).
# One candidate is generated per section at the HIGHEST available intensity <= its level;
# every requested level is clamped to the style's ceiling. 0 means 0: median only.
#
# Intensity ladder (what each level UNLOCKS — higher includes the right to go lower):
#   0  median only — never touched
#   1  NUDGE      — subtle intensification of the section's existing treatments
#   2  CRANK      — strong push of an existing treatment (ghost 3x territory)
#   3  INVERT     — alignment/anchor inversion (bends a SOFT avoid rule; one-off, logged)
#   4  TRANSPLANT — foreign use-case grammar (registered recipes only)
#   5  RELAX      — one neverDo relaxation; ONLY where wildcardScope sanctions it (hero)
#                   and ONLY via a registered recipe — no recipe, level caps at 4.

# Budget names are canonical LIBRARY use-cases ("hero", "about", "cta", …; see
# contracts/layout-patterns/<useCase>.yaml) or exact layout ids. Which LAYOUT a
# use-case resolves to is derived from the ACTIVE doc (use_case_map below), never
# from a hardcoded id table.

def _layout_use_case(layout, patterns_by_id: dict[str, str]) -> str:
    """A layout's use-case: its resolved patternRef's declared useCase first (the
    library is the identity authority), else the keyword inference layout_library
    itself uses when learning a pattern from a layout."""
    ref = (layout or {}).get("patternRef")
    pid = ref.get("id") if isinstance(ref, dict) else None
    if pid and patterns_by_id.get(pid):
        return patterns_by_id[pid]
    return ll.infer_use_case(layout or {})


def use_case_map(doc, brand_yaml: Path) -> dict[str, str]:
    """use-case -> the FIRST page layout realizing it (page order), from the ACTIVE
    doc + its project library. This replaces the old hardcoded alias table so budget
    names like "hero" or "cta" can never resolve to another brand's layout id."""
    patterns = {p.id: p.use_case for p in ll.load_project_patterns(brand_yaml)}
    out: dict[str, str] = {}
    for lid in page_layout_ids(doc):
        layout = cs.find_layout(doc, lid)
        out.setdefault(_layout_use_case(layout, patterns), lid)
    return out


# Per-scaffold CSS transforms for levels 1-3 (generic, treatment-driven). Levels 4-5 come
# from the RECIPES registry below — they need real per-section design work, not a formula.
# KEYED BY SCAFFOLD FAMILY (compose_section.scaffold_key), NOT layout id: the CSS targets
# `.cs-<scaffold>-*` classes, so it applies to ANY brand's layout that composes through
# that scaffold — a budget entry for a layout dispatches layout -> scaffold_key -> entry.
SECTION_LADDER: dict[str, dict[int, tuple[str, str]]] = {
    "hero": {
        1: ("deeper title-over-media overlap",
            ".cs-title { margin-bottom: calc(var(--c-title-overlap) * 1.6); }"),
        2: ("overlap photo crank — bigger, lower, nearly colliding",
            ".c-image--overlap.is-abs { width: 46%; bottom: -38%; right: 1%; }"),
        3: ("LEFT-ANCHORED hero — inverts the hero's own sanctioned centering",
            ".cs-slot, .cs-eyebrow-wrap, .cs-title, .cs-foot { align-items: flex-start; "
            "text-align: left; }\n.cs-title .c-heading--display { text-align: left; margin-left: 0; }"),
    },
    "collage": {
        1: ("ghost watermark +20%",
            ":root { --c-ghost-size: clamp(12rem, 48cqw, 40rem); }"),
        2: ("ghost colossal — the watermark IS the section",
            ".cs-collage-sec { overflow: visible; }\n.cs-ghost { font-size: clamp(24rem, 95cqw, 70rem) "
            "!important; top: -12% !important; right: -8cqw !important; line-height: 0.78 !important; }"),
        3: ("mirrored anchor — media/body columns flipped, ghost swings left",
            ".cs-collage-grid { grid-template-areas: \"body head\" \"body media\"; "
            "grid-template-columns: minmax(0,0.92fr) minmax(0,1.08fr); }\n"
            ".cs-ghost { right: auto; left: -3cqw; }"),
    },
    "statement": {
        1: ("taller statement media (3:4), wider gutter",
            ".cs-statement-grid { column-gap: 8rem; }\n"
            ".cs-statement-media .c-image { aspect-ratio: 3 / 4; }"),
        2: ("media side flip — photo leads, statement follows",
            ".cs-statement-grid { grid-template-columns: minmax(0,1.1fr) minmax(0,0.9fr); }\n"
            ".cs-statement-media { order: -1; }"),
        3: ("CENTERED MONUMENT — dead-centered stack, media beneath like an altarpiece "
            "(inverts avoid.prefer-asymmetry)",
            # AS-19: the collapsed 1fr grid must ALSO re-place the spanned children —
            # the old CSS left .cs-statement-media on its 6/-1 editorial offset, an
            # out-of-range grid-column on a 1-track grid (the media sat right-shifted
            # under the centered text).
            ".cs-statement-grid { grid-template-columns: 1fr !important; justify-items: center; "
            "row-gap: 3.5rem; text-align: center; }\n"
            ".cs-statement-text { grid-column: 1; align-items: center !important; "
            "text-align: center !important; max-width: 40ch !important; }\n"
            ".cs-statement-sec .c-heading--display { text-align: center !important; "
            "margin-left: auto; margin-right: auto; }\n"
            ".cs-statement-media { grid-column: 1; width: min(100%, 46rem); }"),
    },
    "gallery": {
        1: ("wider, shorter cinema band (16:8.5)",
            ".cs-gallery-media .c-image { aspect-ratio: 16 / 8.5; }"),
        2: ("counter at didone display scale — the index becomes typography",
            ".cs-gallery-counter .c-caption { font-family: var(--c-font-heading); "
            "font-size: 2.25rem; color: var(--c-ink); }"),
        3: ("caption swings right; utility row tightens to the band edge",
            ".cs-gallery-caption { text-align: right; }\n"
            ".cs-gallery-utility { padding: 0 1rem; }"),
    },
    "timeline": {
        1: ("ghost numerals +20%",
            ":root { --c-ghost-size: clamp(11rem, 40cqw, 32rem); }"),
        2: ("ghost numerals span the full band behind everything",
            ".cs-timeline-sec .cs-ghost--numerals { font-size: clamp(16rem, 60cqw, 48rem) "
            "!important; bottom: -10% !important; }"),
        3: ("mirrored anchor — media right, numerals left",
            ".cs-collage-grid { grid-template-areas: \"body head\" \"body media\"; "
            "grid-template-columns: minmax(0,0.92fr) minmax(0,1.08fr); }\n"
            ".cs-timeline-sec .cs-ghost--numerals { right: auto !important; left: -1cqw !important; }"),
    },
    "quote": {
        1: ("wider gutter between quote and portrait",
            ".cs-quote-grid { column-gap: 8rem; }"),
        2: ("portrait leads — flipped split",
            ".cs-quote-media { order: -1; }"),
        3: ("centered devotional — quote centered over the portrait "
            "(inverts avoid.prefer-asymmetry)",
            # AS-19: re-place the spanned children on the collapsed 1-track grid (the
            # old CSS left text/media on their 1/span7 + 8/-1 offsets — out of range).
            ".cs-quote-grid { grid-template-columns: 1fr; justify-items: center; text-align: center; "
            "row-gap: 3rem; }\n.cs-quote-text { grid-column: 1; align-items: center; }\n"
            ".cs-quote-sec .c-heading--display { text-align: center; }\n"
            ".cs-quote-media { grid-column: 1; width: min(100%, 30rem); }"),
    },
    "visit": {
        1: ("panels bite deeper into the map",
            ".cs-visit-panels { margin-top: -6.5rem; }"),
        2: ("asymmetric panel weights (first panel dominant)",
            ".cs-visit-panels { grid-template-columns: 1.25fr 0.75fr; margin-top: -7.5rem; }"),
        3: ("panels pushed off-axis left, map breathing right",
            ".cs-visit-panels { max-width: 60rem; margin-left: 6cqw; margin-right: auto; }"),
    },
    "conversion": {
        1: ("tighter column measure",
            ".cs-conversion { --c-cta-measure: 34ch; }"),
        2: ("heading past poster scale",
            ".cs-conversion-sec .c-heading--display { font-size: calc(var(--c-display-size) * 1.15); "
            "max-width: 20ch; }"),
        3: ("LEFT-ANCHORED conversion — inverts its own sanctioned centering",
            ".cs-conversion-sec { justify-content: flex-start; }\n"
            ".cs-conversion { align-items: flex-start; text-align: left; }\n"
            ".cs-conversion-sec .c-heading--display { text-align: left; }\n"
            ".cs-conversion .c-form { margin-left: 0; }"),
    },
}

# Level 4/5 need REAL recipes (foreign grammar / sanctioned rule relaxation), not a CSS
# formula. Registered per SCAFFOLD FAMILY (same key space as SECTION_LADDER); a level
# above the best registered entry caps down.
RECIPES: dict[str, dict[int, str]] = {
    # "hero": {4: "hero-ghost"} PARKED 2026-07-02 (anti-ai-slop AS-22): the transplant
    # kept the collage's light surface while the source brand's hero pattern was
    # surface/inverse (review verdict: the hero should stay dark). Re-register only
    # after the ghost grammar is re-fit for a dark surface (on-inverse ghost token +
    # contrast). 5: none registered anywhere yet — wildcardScope sanctions hero-only
    # neverDo relaxation, but no recipe has been designed; level 5 therefore caps to 4.
}


def parse_budget(text: str, fb: FreedomBudget | None = None,
                 aliases: dict[str, str] | None = None) -> dict[str, int]:
    """Parse "hero 1 about 3" / "hero=1, about=3" into {layoutId: level}. Names are the
    ACTIVE brand's layout ids or canonical use-cases (resolved via `aliases`, the
    use_case_map of the active doc — never a hardcoded id table); an unresolvable name
    is reported with the brand's available names and SKIPPED. When the style declares
    a FreedomBudget, every requested level is clamped to its ceiling (a conservative
    style like corporate-saas-clean caps a "hero 5" down to crank)."""
    aliases = aliases or {}
    out: dict[str, int] = {}
    tokens = re.split(r"[,\s]+", text.strip())
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if "=" in tok:
            name, lvl = tok.split("=", 1)
            i += 1
        else:
            name, lvl = tok, (tokens[i + 1] if i + 1 < len(tokens) else "0")
            i += 2
        try:
            level = max(0, min(5, int(lvl)))
        except ValueError:
            raise SystemExit(f"budget: could not parse level for '{name}' (got '{lvl}')")
        lid = aliases.get(name.lower(), name)
        if fb is not None and level > fb.ceiling:
            print(f"  (note: {name} clamped {level}->{fb.ceiling}: style ceiling)")
            level = fb.ceiling
        out[lid] = level
    return out


def page_layout_ids(doc) -> list[str]:
    """The page's sections in PAGE ORDER — compose_page's brand-declared/derived
    resolution (pageOrder: else authored layouts[]), filtered to layouts that exist."""
    return [lid for lid in cp.page_order(doc) if cs.find_layout(doc, lid) is not None]


def style_budget(doc, style_ctx) -> dict[str, int] | None:
    """The style-layer FILLED budget: every page section at the level resolved from the
    style's freedomBudget (brand voice.dials.freedom LEVEL choice clamped to the style
    ceiling, else the style default). None when the style declares no budget."""
    if not getattr(style_ctx, "active", False) or style_ctx.freedom_budget is None:
        return None
    level = style_ctx.resolve_freedom_level(doc)
    return {lid: level for lid in page_layout_ids(doc)}


def list_sections(doc, style_ctx=None) -> str:
    """The 0-5 freedom-budget template (one line per page section, by LAYOUT ID —
    the id vocabulary is the brand's own). PRE-FILLED from the style layer when the
    active style declares a freedomBudget (no more blank all-zero template); a style
    with no budget keeps the legacy all-zero template."""
    fb = style_ctx.freedom_budget if style_ctx is not None else None
    if fb is not None:
        level = style_ctx.resolve_freedom_level(doc)
        name = (fb.describe(level).get("name") or "?")
        lines = [f"Sections on the main page — pre-filled at level {level} ({name}) from the",
                 f"style layer (style default {fb.default}, ceiling {fb.ceiling}); adjust "
                 "per line and pass back via --budget:", ""]
    else:
        level = 0
        lines = ["Sections on the main page — copy this list back with a 0-5 freedom level",
                 "per line (0 = median only … 5 = max divergence incl. sanctioned rule relax):",
                 ""]
    for lid in page_layout_ids(doc):
        lines.append(f"  {lid} {level}")
    return "\n".join(lines)


def budget_candidates(doc, budget: dict[str, int]) -> list[dict]:
    """One candidate per budgeted section at the HIGHEST available intensity <= level.
    The ladder/recipe lookup dispatches layout -> its SCAFFOLD FAMILY (scaffold_key) —
    a budget name that resolves to no layout in THIS brand is reported with the
    available ids and skipped (never silently borrowed from another brand's page)."""
    out = []
    recipes_by_id = {c["id"]: c for c in _candidates(doc)}
    for lid, level in budget.items():
        if level <= 0:
            continue
        layout = cs.find_layout(doc, lid)
        if layout is None:
            print(f"  (skip: no layout '{lid}' in brand.yaml — available: "
                  f"{', '.join(page_layout_ids(doc))})")
            continue
        scaffold = cs.scaffold_key(layout)
        chosen = None
        for lvl in range(min(level, 5), 0, -1):
            recipe_id = (RECIPES.get(scaffold) or {}).get(lvl)
            if recipe_id and recipe_id in recipes_by_id:
                r = recipes_by_id[recipe_id]
                chosen = {**r, "id": f"{lid}-L{lvl}",
                          "label": f"Wildcard L{lvl} — {lid}: {r['label'].split('—')[-1].strip()}",
                          "level": lvl}
                break
            ladder = (SECTION_LADDER.get(scaffold) or {}).get(lvl)
            if ladder:
                desc, css = ladder
                chosen = {"id": f"{lid}-L{lvl}", "level": lvl,
                          "label": f"Wildcard L{lvl} — {lid}: {desc}",
                          "base_layout": lid, "gate_layout": lid,
                          "strategy": {1: "nudge", 2: "crank", 3: "invert"}[lvl],
                          "bends": ("nothing — intensifies an existing treatment" if lvl <= 2 else
                                    "a SOFT avoid rule (one-off, logged, never promoted)"),
                          "css": "\n/* WILDCARD budget L" + str(lvl) + " */\n" + css + "\n"}
                break
        if chosen:
            if chosen["level"] < level:
                print(f"  (note: {lid} capped {level}->{chosen['level']}: "
                      f"no recipe registered above L{chosen['level']})")
            out.append(chosen)
    return out


# ── novelty evidence (the matcher run in reverse) ────────────────────────────────

def novelty_evidence(brand_yaml: Path) -> str:
    """The transplant's novelty, MEASURED: query the library as if composing a HERO with
    ghost-word treatments. The best hero-use-case match score vs the reuse threshold is
    the gap the transplant jumps — retrieval alone would never make this move."""
    q = ll.Query(use_case="hero", textlens=["word", "short", "medium", "long"],
                 has_media=True, treatments={"ghost-word", "stagger", "marginal-caption"},
                 surface_intent="inverse")
    res = ll.match(q, brand_yaml)
    best = f"{res.pattern.id} @ {res.score:.2f}" if res.pattern else f"none @ {res.score:.2f}"
    # The honest reading is about WHAT retrieval returns, not just whether it returns:
    # if the winning pattern doesn't carry ghost-word, retrieval CONVERGES TO THE MEDIAN
    # hero — i.e. the ghost-word hero is out of reach for reuse, which is the transplant's
    # novelty. (A reuse verdict alone would be misleading: reusing the ghost-less hero is
    # precisely NOT reaching this combination.)
    reaches = bool(res.pattern) and res.match_kind == "reuse" and res.pattern.has_ghostword()
    return (f"hero+ghost-word query -> matchKind={res.match_kind}, best={best} "
            f"(reuse threshold {ll.REUSE_THRESHOLD}); winning pattern "
            f"{'carries' if reaches else 'has NO'} ghost-word — retrieval alone "
            f"{'reaches' if reaches else 'converges to the median hero instead of'} "
            f"this combination")


# ── render + gate ────────────────────────────────────────────────────────────────

def render_candidate(doc, cand, brand_yaml: Path, out_dir: Path, style_ctx) -> None:
    layout = cs.find_layout(doc, cand["base_layout"])
    if layout is None:
        raise SystemExit(f"base layout '{cand['base_layout']}' not found")
    if cand.get("mutate"):
        layout = cand["mutate"](layout)
    for lid, copy_entry in (cand.get("copy") or {}).items():
        cs.LAYOUT_COPY[lid] = copy_entry          # runtime-only registration
    out_dir.mkdir(parents=True, exist_ok=True)
    cs.prepare_nav_logo(doc, brand_yaml.parent, out_dir / "assets")
    html = cs.build_document(doc, layout, brand_yaml, style_ctx)
    if cand["css"]:
        html = html.replace("</style>", cand["css"] + "\n</style>", 1)
    (out_dir / "index.html").write_text(html)
    cs.copy_assets(brand_yaml.parent, out_dir / "assets")
    cs.copy_fonts(brand_yaml.parent, out_dir / "assets", doc)
    (out_dir / "label.txt").write_text(cand["label"] + "\n")


def gate_candidate(brand_yaml: Path, out_dir: Path, gate_layout: str, style_id: str | None) -> str:
    cmd = [str(REPO_ROOT / "venv" / "bin" / "python"),
           str(REPO_ROOT / "brand_pipeline" / "onbrand_check.py"),
           str(brand_yaml), str(out_dir), "--layout", gate_layout,
           "--report", "onbrand-report.md"]
    if style_id:
        cmd += ["--style", style_id]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    out = r.stdout + r.stderr
    m = re.search(r"OVERALL:\s*(\w+)", out)
    fails = re.findall(r"\[FAIL\]\s*(\S+)", out)
    verdict = m.group(1) if m else "UNKNOWN"
    # WCAG contrast audit (anti-ai-slop.md AS-01/AS-10): every text element vs its
    # EFFECTIVE background + every section's --c-link-hover. A candidate that diverges
    # into unreadability is not a magic trick, it's a defect — hard-gated here.
    c = subprocess.run(["node", str(REPO_ROOT / "brand_pipeline" / "contrast_audit.mjs"),
                        str(out_dir / "index.html")], capture_output=True, text=True, cwd=REPO_ROOT)
    contrast = "PASS" if c.returncode == 0 else "FAIL"
    return (f"{verdict}" + (f" (FAIL: {', '.join(fails)})" if fails else "")
            + f" · contrast={contrast}")


# ── magic-trick.md update ────────────────────────────────────────────────────────

def write_proposals(brand_dir: Path, rows: list[dict], evidence: str) -> None:
    mt = brand_dir / "magic-trick.md"
    if not mt.exists():                            # exporter normally scaffolds it first
        from export_kit import MAGIC_TRICK_SCAFFOLD
        mt.write_text(MAGIC_TRICK_SCAFFOLD)
    text = mt.read_text()
    lines = ["", f"Novelty evidence (matcher run in reverse): {evidence}", ""]
    for r in rows:
        lines += [
            f"### PROPOSED — {r['label']}",
            "",
            f"- **strategy**: {r['strategy']}",
            f"- **bends**: {r['bends']}",
            f"- **gate**: {r['gate']}",
            f"- **preview**: `variants/wildcard-{r['id']}/index.html` (visible in Studio's lane dropdown)",
            f"- **origin**: designed · source: wildcard-generator · scope: one-off (NOT blessed)",
            "",
        ]
    block = "\n".join(lines)
    placeholder = re.compile(
        r"## Machine-proposed candidates\n.*?(?=\n## Blessed)", re.DOTALL)
    replacement = ("## Machine-proposed candidates\n\n"
                   "<!-- Written by wildcard_generator.py. Options, not decisions: a human "
                   "moves ONE entry to Blessed (with a date + the room it was made for) to "
                   "give it authority. -->\n" + block + "\n")
    if placeholder.search(text):
        text = placeholder.sub(replacement, text)
    else:
        text += "\n" + replacement
    mt.write_text(text)


def main():
    ap = argparse.ArgumentParser(description="Generate gate-checked magic-trick candidates.")
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("--style", default="radical-editorial")
    ap.add_argument("--list-sections", action="store_true",
                    help="print the page's sections as a 0-5 freedom-budget template "
                         "(pre-filled from the style layer's freedomBudget) and exit")
    ap.add_argument("--budget", default=None,
                    help='per-section freedom levels by layout id or use-case, e.g. '
                         '"hero 1 about 3 cta 0" (0=median only … 5=max, clamped to the '
                         "style ceiling); omitted -> every section at the level resolved "
                         "from the style layer")
    ap.add_argument("--showcase", action="store_true",
                    help="generate the three fixed strategy-showcase candidates "
                         "(ghost-colossal / centered-monument / hero-ghost) instead of a "
                         "budget-driven run")
    args = ap.parse_args()
    brand_yaml = args.brand_yaml.resolve()
    brand_dir = brand_yaml.parent
    doc = cs.load_doc(brand_yaml)
    style_ctx = load_and_merge(args.style, doc) if args.style else inactive_context()
    fb = style_ctx.freedom_budget
    if args.list_sections:
        print(list_sections(doc, style_ctx))
        return

    evidence = novelty_evidence(brand_yaml)
    print(f"novelty evidence: {evidence}\n")

    if args.showcase:
        cands = _candidates(doc)
    elif args.budget:
        cands = budget_candidates(doc, parse_budget(args.budget, fb,
                                                    use_case_map(doc, brand_yaml)))
    else:
        # No user budget: FILL the template from the style layer (freedomBudget default,
        # or the brand's voice.dials.freedom level choice clamped to the style ceiling).
        budget = style_budget(doc, style_ctx)
        if budget is None:   # style declares no budget -> legacy showcase behavior
            cands = _candidates(doc)
        else:
            level = style_ctx.resolve_freedom_level(doc)
            print(f"budget: style-layer fill — every section at level {level} "
                  f"({fb.describe(level).get('name') or '?'}; style default {fb.default}, "
                  f"ceiling {fb.ceiling})\n")
            cands = budget_candidates(doc, budget)
    rows = []
    for cand in cands:
        out_dir = brand_dir / "variants" / f"wildcard-{cand['id']}"
        render_candidate(doc, cand, brand_yaml, out_dir, style_ctx)
        gate = gate_candidate(brand_yaml, out_dir, cand["gate_layout"], args.style)
        rows.append({**cand, "gate": gate})
        print(f"  wildcard-{cand['id']:20} [{cand['strategy']:20}] gate={gate}")

    write_proposals(brand_dir, rows, evidence)
    print(f"\nproposals written -> {brand_dir / 'magic-trick.md'}")
    print("review in Studio (lane dropdown: 'Wildcard — …'), then bless ONE by moving it "
          "to the Blessed section with a date + room brief.")


if __name__ == "__main__":
    main()
