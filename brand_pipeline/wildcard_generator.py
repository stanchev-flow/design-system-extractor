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
import compose_section as cs  # noqa: E402
import layout_library as ll  # noqa: E402
from styles import inactive_context, load_and_merge  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── candidate definitions ────────────────────────────────────────────────────────

def _candidates(doc: dict) -> list[dict]:
    """Each candidate: which brand.yaml layout to start from, an optional in-memory layout
    mutation, optional extra copy (registered into LAYOUT_COPY at runtime), a scoped CSS
    override (the divergence itself), and the honest record of what it bends."""
    return [
        {
            "id": "ghost-colossal",
            "label": "Wildcard — Ghost at 3× (dial-crank)",
            "base_layout": "editorial-collage",
            "gate_layout": "editorial-collage",
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
            "base_layout": "mission-statement",
            "gate_layout": "mission-statement",
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
            "base_layout": "editorial-collage",
            "gate_layout": "editorial-collage",
            "strategy": "use-case transplant",
            "bends": "no rule — a USE-CASE transplant: the hero's content set in the "
                     "about-run's ghost-word collage grammar (colossal 'WOOD' behind the "
                     "opening statement) instead of the display-over-media hero pattern.",
            "mutate": lambda lay: {**copy.deepcopy(lay), "id": "wildcard-hero-ghost"},
            "copy": {
                "wildcard-hero-ghost": {
                    "ghost": "Wood",
                    "eyebrow": "Est. 2019 — Portland, Oregon",
                    "heading": "Contemporary art\nin a landmark\ntimber hall",
                    "body": ("An evolving exhibition of woodgrain, light, and the quiet "
                             "geometry of the handmade — held in a hall that has been "
                             "standing since 1941."),
                    "caption": "Main hall, east light",
                    "cta": "Buy tickets",
                },
            },
            # hero copy carries far longer words ("CONTEMPORARY") than the collage grammar
            # was measured for — at the style's full poster scale the heading overflows its
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


# ── FREEDOM BUDGET (per-section 0-5 magic-trick allowance, user-supplied) ────────
#
# The interaction protocol: before generating, the agent prints the page's sections
# (``--list-sections``) and the user annotates each with 0-5 — how much freedom the
# wildcard machinery gets for THAT section. The user pastes the list back
# (``--budget "hero 1 mission 3 cta 0"``); one candidate is generated per section at the
# HIGHEST available intensity <= its level. This keeps divergence a per-section, human-set
# dial rather than an all-or-nothing switch — and 0 means 0: the section ships median.
#
# Intensity ladder (what each level UNLOCKS — higher includes the right to go lower):
#   0  median only — never touched
#   1  NUDGE      — subtle intensification of the section's existing treatments
#   2  CRANK      — strong push of an existing treatment (ghost 3x territory)
#   3  INVERT     — alignment/anchor inversion (bends a SOFT avoid rule; one-off, logged)
#   4  TRANSPLANT — foreign use-case grammar (registered recipes only)
#   5  RELAX      — one neverDo relaxation; ONLY where wildcardScope sanctions it (hero)
#                   and ONLY via a registered recipe — no recipe, level caps at 4.

USE_CASE_ALIASES = {
    "hero": "opening-bookend", "about": "editorial-collage", "mission": "mission-statement",
    "gallery": "gallery-showcase", "heritage": "heritage-timeline",
    "testimonial": "curator-quote", "features": "visit-band", "visit": "visit-band",
    "cta": "conversion-stack", "newsletter": "conversion-stack",
}
_ALIAS_BY_ID = {}
for a, lid in USE_CASE_ALIASES.items():
    _ALIAS_BY_ID.setdefault(lid, a)

# Per-section CSS transforms for levels 1-3 (generic, treatment-driven). Levels 4-5 come
# from the RECIPES registry below — they need real per-section design work, not a formula.
SECTION_LADDER: dict[str, dict[int, tuple[str, str]]] = {
    "opening-bookend": {
        1: ("deeper title-over-media overlap",
            ".cs-title { margin-bottom: calc(var(--c-title-overlap) * 1.6); }"),
        2: ("overlap photo crank — bigger, lower, nearly colliding",
            ".c-image--overlap.is-abs { width: 46%; bottom: -38%; right: 1%; }"),
        3: ("LEFT-ANCHORED hero — inverts the hero's own sanctioned centering",
            ".cs-slot, .cs-eyebrow-wrap, .cs-title, .cs-foot { align-items: flex-start; "
            "text-align: left; }\n.cs-title .c-heading--display { text-align: left; margin-left: 0; }"),
    },
    "editorial-collage": {
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
    "mission-statement": {
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
    "gallery-showcase": {
        1: ("wider, shorter cinema band (16:8.5)",
            ".cs-gallery-media .c-image { aspect-ratio: 16 / 8.5; }"),
        2: ("counter at didone display scale — the index becomes typography",
            ".cs-gallery-counter .c-caption { font-family: var(--c-font-heading); "
            "font-size: 2.25rem; color: var(--c-ink); }"),
        3: ("caption swings right; utility row tightens to the band edge",
            ".cs-gallery-caption { text-align: right; }\n"
            ".cs-gallery-utility { padding: 0 1rem; }"),
    },
    "heritage-timeline": {
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
    "curator-quote": {
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
    "visit-band": {
        1: ("panels bite deeper into the map",
            ".cs-visit-panels { margin-top: -6.5rem; }"),
        2: ("asymmetric panel weights (tickets dominant)",
            ".cs-visit-panels { grid-template-columns: 1.25fr 0.75fr; margin-top: -7.5rem; }"),
        3: ("panels pushed off-axis left, map breathing right",
            ".cs-visit-panels { max-width: 60rem; margin-left: 6cqw; margin-right: auto; }"),
    },
    "conversion-stack": {
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
# formula. Registered per section; a level above the best registered entry caps down.
RECIPES: dict[str, dict[int, str]] = {
    "opening-bookend": {4: "hero-ghost"},   # -> the transplant in _candidates()
    # 5: none registered anywhere yet — wildcardScope sanctions hero-only neverDo
    # relaxation, but no recipe has been designed; level 5 therefore caps to 4.
}


def parse_budget(text: str) -> dict[str, int]:
    """Parse "hero 1 mission 3" / "hero=1, mission=3" into {layoutId: level}."""
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
        lid = USE_CASE_ALIASES.get(name.lower(), name)
        try:
            out[lid] = max(0, min(5, int(lvl)))
        except ValueError:
            raise SystemExit(f"budget: could not parse level for '{name}' (got '{lvl}')")
    return out


def list_sections(doc) -> str:
    lines = ["Sections on the main page — copy this list back with a 0-5 freedom level",
             "per line (0 = median only … 5 = max divergence incl. sanctioned rule relax):", ""]
    order = ["opening-bookend", "editorial-collage", "mission-statement", "gallery-showcase",
             "heritage-timeline", "curator-quote", "visit-band", "conversion-stack"]
    for lid in order:
        if cs.find_layout(doc, lid) is not None:
            lines.append(f"  {_ALIAS_BY_ID.get(lid, lid)} 0")
    return "\n".join(lines)


def budget_candidates(doc, budget: dict[str, int]) -> list[dict]:
    """One candidate per budgeted section at the HIGHEST available intensity <= level."""
    out = []
    recipes_by_id = {c["id"]: c for c in _candidates(doc)}
    for lid, level in budget.items():
        if level <= 0:
            continue
        if cs.find_layout(doc, lid) is None:
            print(f"  (skip: no layout '{lid}' in brand.yaml)")
            continue
        chosen = None
        for lvl in range(min(level, 5), 0, -1):
            recipe_id = (RECIPES.get(lid) or {}).get(lvl)
            if recipe_id and recipe_id in recipes_by_id:
                r = recipes_by_id[recipe_id]
                chosen = {**r, "id": f"{lid}-L{lvl}",
                          "label": f"Wildcard L{lvl} — {_ALIAS_BY_ID.get(lid, lid)}: {r['label'].split('—')[-1].strip()}",
                          "level": lvl}
                break
            ladder = (SECTION_LADDER.get(lid) or {}).get(lvl)
            if ladder:
                desc, css = ladder
                chosen = {"id": f"{lid}-L{lvl}", "level": lvl,
                          "label": f"Wildcard L{lvl} — {_ALIAS_BY_ID.get(lid, lid)}: {desc}",
                          "base_layout": lid, "gate_layout": lid,
                          "strategy": {1: "nudge", 2: "crank", 3: "invert"}[lvl],
                          "bends": ("nothing — intensifies an existing treatment" if lvl <= 2 else
                                    "a SOFT avoid rule (one-off, logged, never promoted)"),
                          "css": "\n/* WILDCARD budget L" + str(lvl) + " */\n" + css + "\n"}
                break
        if chosen:
            if chosen["level"] < level:
                print(f"  (note: {_ALIAS_BY_ID.get(lid, lid)} capped {level}->{chosen['level']}: "
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
                    help="print the page's sections as a 0-5 freedom-budget template and exit")
    ap.add_argument("--budget", default=None,
                    help='per-section freedom levels, e.g. "hero 1 mission 3 cta 0" '
                         "(0=median only … 5=max; see intensity ladder)")
    args = ap.parse_args()
    brand_yaml = args.brand_yaml.resolve()
    brand_dir = brand_yaml.parent
    doc = cs.load_doc(brand_yaml)
    if args.list_sections:
        print(list_sections(doc))
        return
    style_ctx = load_and_merge(args.style, doc) if args.style else inactive_context()

    evidence = novelty_evidence(brand_yaml)
    print(f"novelty evidence: {evidence}\n")

    cands = budget_candidates(doc, parse_budget(args.budget)) if args.budget else _candidates(doc)
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
