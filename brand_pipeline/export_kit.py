#!/usr/bin/env python3
"""export_kit.py - export a brand as a PORTABLE, self-contained "atomic kit" folder.

Everything this pipeline knows about a brand lives in ``runs/<brand>/brand/`` — but it is
only actionable INSIDE this repo: ``brand.yaml`` references the shared contracts via
relative repo paths, tokens only become CSS at compose time, and rendering requires the
Python composers. This exporter flattens all of that into one folder any agentic tool
(Cursor, Claude Code, Claude Design, Codex, …) can act on with ZERO knowledge of this
pipeline:

    <brand>-kit/
    ├── readme.md            ← the agent ENTRY POINT (what's canonical, consumption order)
    ├── magic-trick.md       ← the human-originality slot (copied if authored; scaffolded if not)
    ├── human/               ← the READABLE layer: brand.md, voice.md, assets.md, gallery
    └── agent/               ← the ACTIONABLE layer:
        ├── brand.yaml       ← canonical, with contract refs REWRITTEN to ./contracts/*
        ├── layout-library.yaml
        ├── contracts/       ← primitives/blocks/scaffolds + the standard layout-patterns
        ├── tokens.css       ← every token emitted as CSS custom properties + @font-face
        ├── motion.json      ← the resolved motion spec (easing, durations, reveal, parallax)
        ├── fonts/  assets/  ← self-hosted faces + real brand imagery
        └── quality/         ← neverDo/avoid/do rules (yaml) + anti-ai-slop.md checklist

Read-only with respect to the source brand dir (single exception: scaffolds
``runs/<brand>/brand/magic-trick.md`` if absent, so the human slot has a stable home the
kit re-export never clobbers). Usage:

    python3 brand_pipeline/export_kit.py runs/woodwave/brand/brand.yaml [-o <outdir>]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from component_render import image_parallax_spec, link_hover_color, link_mode, motion_spec  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "brand_pipeline" / "contracts"
SPEC_DIR = REPO_ROOT / "brand_pipeline" / "spec"

# filename fragment -> css font-weight (for @font-face emission from self-hosted files)
_WEIGHTS = {"light": 300, "regular": 400, "medium": 500, "semibold": 600, "bold": 700}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")


# ── tokens.css ───────────────────────────────────────────────────────────────────

def _font_faces(fonts_dir: Path) -> str:
    """One @font-face per family+weight, from the woff2 files present (ttf as fallback)."""
    if not fonts_dir.is_dir():
        return ""
    blocks = []
    for w2 in sorted(fonts_dir.glob("*.woff2")):
        stem = w2.stem                       # e.g. Melodrama-Bold
        family = stem.split("-")[0]
        weight = next((v for k, v in _WEIGHTS.items() if k in stem.lower()), 400)
        srcs = [f"url('./fonts/{w2.name}') format('woff2')"]
        ttf = w2.with_suffix(".ttf")
        if ttf.exists():
            srcs.append(f"url('./fonts/{ttf.name}') format('truetype')")
        blocks.append(f"@font-face {{ font-family: '{family}'; src: {', '.join(srcs)}; "
                      f"font-weight: {weight}; font-style: normal; font-display: swap; }}")
    return "\n".join(blocks)


def build_tokens_css(doc: dict, fonts_dir: Path) -> str:
    """Emit EVERY brand token as a CSS custom property so a foreign agent can build
    on-brand pages from plain CSS with no YAML parsing. Colors/surfaces/spacing/type are
    all flattened; the naming is the token's own semantic role, slugified."""
    tokens = doc.get("tokens", {}) or {}
    lines: list[str] = []
    for role, c in (tokens.get("colors") or {}).items():
        val = c.get("value") if isinstance(c, dict) else c
        if val:
            lines.append(f"  --color-{_slug(role)}: {val};")
    for role, sf in (tokens.get("surfaces") or {}).items():
        if isinstance(sf, dict) and sf.get("bg"):
            lines.append(f"  --surface-{_slug(role)}: {sf['bg']};")
    for role, a in ((tokens.get("imagery") or {}).get("aspectPalette") or {}).items():
        val = a.get("value") if isinstance(a, dict) else a
        if val:
            lines.append(f"  --aspect-{_slug(role)}: {val};")
    for role, sp in (tokens.get("spacing") or {}).items():
        val = sp.get("value") if isinstance(sp, dict) else sp
        if val:
            lines.append(f"  --space-{_slug(role)}: {val};")
    for role, t in (tokens.get("type") or {}).items():
        if not isinstance(t, dict):
            continue
        fam = t.get("family")
        if fam:
            lines.append(f"  --font-{_slug(role)}: '{fam}';")
        size = t.get("sizeRem")
        base = size.get("base") if isinstance(size, dict) else size
        if base:
            lines.append(f"  --size-{_slug(role)}: {base}rem;")
        if t.get("weight"):
            lines.append(f"  --weight-{_slug(role)}: {t['weight']};")
        if t.get("lineHeight"):
            lines.append(f"  --leading-{_slug(role)}: {t['lineHeight']};")
    faces = _font_faces(fonts_dir)
    return (f"/* {doc.get('brand', {}).get('name', 'Brand')} — design tokens as CSS custom "
            f"properties. Generated by export_kit.py from brand.yaml (canonical); regenerate "
            f"rather than hand-editing. */\n"
            + (faces + "\n\n" if faces else "")
            + ":root {\n" + "\n".join(lines) + "\n}\n")


# ── motion.json ──────────────────────────────────────────────────────────────────

def build_motion_json(doc: dict) -> str:
    """The RESOLVED motion system (not the raw YAML): easing, durations, scroll-reveal,
    link-interaction mode + measured hover color, and the image-parallax treatment —
    everything a foreign agent needs to reproduce the brand's motion without our
    composers. Values mirror what compose_page/component_render actually emit."""
    m = motion_spec(doc)
    p = image_parallax_spec(doc)
    out = {
        "easing": {"primary": m["ease"]},
        "durationsMs": {"fast": int(m["fast"].rstrip("ms")), "base": int(m["base"].rstrip("ms")),
                        "slow": int(m["slow"].rstrip("ms"))},
        "scrollReveal": {"kind": "fade-translateY", "translateY": m["shift"],
                         "trigger": "IntersectionObserver, ~8% viewport inset, small per-item stagger"},
        "link": {"mode": link_mode(doc), "hoverColor": link_hover_color(doc),
                 "hoverColorNote": "measured on a DARK surface — apply ONLY on dark/inverse "
                                   "surfaces; on light surfaces hover stays the surface ink "
                                   "(WCAG: the accent is a 1.3:1 contrast failure on the "
                                   "light canvas — see quality/anti-ai-slop.md AS-10)"},
        "imageParallax": {**p,
                          "mechanism": "GSAP ScrollTrigger scrub; masked wrapper (.c-image-mask, "
                                       "overflow:hidden, wraps ONLY the img, never a caption); "
                                       "img scale(1.12) + yPercent pan; hero overlap pair moves "
                                       "at differential rates (0.4x / 1.2x); "
                                       "prefers-reduced-motion disables everything"},
        "reducedMotion": "respect",
    }
    return json.dumps(out, indent=2) + "\n"


# ── quality/ ─────────────────────────────────────────────────────────────────────

def build_quality_rules(doc: dict) -> str:
    """The brand's rule lists as a standalone machine-readable file: neverDo is the ONLY
    hard gate; avoid is soft; do is affirmative house style."""
    def rows(key):
        return [{"id": r.get("id"), "statement": r.get("statement")}
                for r in (doc.get(key) or []) if isinstance(r, dict)]
    payload = {
        "gate": "neverDo is the ONLY hard gate — violating any entry means the output is "
                "off-brand and must not ship. avoid[] is a soft preference; do[] is the "
                "affirmative house style. One sanctioned exception: recipePolicy.magicTrick "
                "may relax exactly ONE neverDo on HERO sections only, when a blessed entry "
                "in magic-trick.md documents it.",
        "neverDo": rows("neverDo"), "avoid": rows("avoid"), "do": rows("do"),
    }
    return yaml.safe_dump(payload, sort_keys=False, width=100, allow_unicode=True)


# ── readme.md + magic-trick.md ──────────────────────────────────────────────────

def build_readme(doc: dict) -> str:
    name = doc.get("brand", {}).get("name", "Brand")
    src = doc.get("brand", {}).get("sourceUrl", "")
    return f"""# {name} — atomic brand kit

This folder is a **self-contained, machine-actionable brand system**. Everything an agent
needs to write, design, and build on-brand for {name} is in here — no external pipeline,
no repo, no other context required.

## Consumption order (for agents)

1. **`agent/brand.yaml`** — the CANONICAL source of truth: tokens, surface grammar,
   layout instances, composition rules, and the three rule lists (`do`/`avoid`/`neverDo`).
   Contract references resolve locally to `agent/contracts/`.
2. **`agent/layout-library.yaml`** — the brand's reusable, use-case-keyed layout patterns
   (hero, about, gallery, pricing, faq, …). REUSE these before inventing new section
   structure; sizes are relationships/classes, never px — resolve them against the tokens.
3. **`agent/tokens.css`** — every token as a CSS custom property, plus `@font-face` for the
   self-hosted display face. Build pages directly on these variables.
4. **`agent/motion.json`** — the resolved motion system (easing, durations, scroll-reveal,
   link hover, image parallax). Respect `prefers-reduced-motion`.
5. **`agent/quality/rules.yaml`** — `neverDo` is the ONLY hard gate. Check your output
   against it before finishing. `quality/anti-ai-slop.md` lists generation-failure shapes
   (contrast, spacing, context bugs) to self-review against.
6. **`magic-trick.md`** — sanctioned one-off rule relaxations and the human's original
   moves. Only entries marked BLESSED may override a rule, and only as documented there.

## The human layer

`human/` holds the same brand as prose for people: `brand.md` (rendered projection of
brand.yaml — never edit it directly), `voice.md` (tone, vocabulary, casing, length
budgets, real section copy), `assets.md`, and `components-preview/index.html` (open in a
browser to SEE every component).

## Ground rules

- **brand.yaml is canonical.** brand.md is a projection. When they disagree, brand.yaml wins.
- **Reuse before create**: match a layout-library pattern first; adapt via its variantKnobs;
  invent only on a true miss — and keep the invention consistent with `compositionRules`.
- **neverDo is hard.** Everything else bends; those rules don't (except via magic-trick.md).
- Source: {src or "(extracted brand)"} — extracted, consolidated, and verified by the
  brand pipeline; provenance and confidence for every fact are recorded in brand.yaml.
"""


MAGIC_TRICK_SCAFFOLD = """# magic-trick.md — the human-originality slot

Everything else in this kit converges on the brand's MEDIAN — that is what a system is
for. This file is the reserved seat for the one move a system cannot make: the
left-of-center, unpredictable-from-the-inputs idea that makes a launch memorable.

## Rules of the game

- An idea recorded here may relax **exactly one** `neverDo` rule, on **hero sections
  only** (`recipePolicy.magicTrick.wildcardScope`), as a **one-off** — never promoted to
  the design language, always logged.
- An entry only takes effect when marked **BLESSED** by a human. Machine-proposed
  candidates (below, when present) are options, not decisions.
- Yesterday's idea is not today's idea: entries carry the date and the room they were
  made for.

## The room brief (fill this in — it biases everything downstream)

- **The moment**: <what is launching / happening, and when>
- **The audience**: <who is actually looking, what scene are they from>
- **The feeling**: <the one thing they should feel that the median page wouldn't deliver>

## Freedom budget (the per-section 0-5 dial)

Divergence is a PER-SECTION, HUMAN-SET dial, not an all-or-nothing switch. Before
generating, list the page's sections (`wildcard_generator.py --list-sections`), have the
human annotate each 0-5, and run with `--budget "hero 1 mission 3 cta 0"`:

- **0** median only — the section is never touched
- **1** NUDGE — subtle intensification of the section's existing treatments
- **2** CRANK — strong push of an existing treatment
- **3** INVERT — alignment/anchor inversion (bends a SOFT avoid rule; one-off, logged)
- **4** TRANSPLANT — foreign use-case grammar (registered recipes only)
- **5** RELAX — one neverDo relaxation, ONLY where wildcardScope sanctions it (hero) and
  ONLY via a registered recipe; otherwise the level caps down honestly.

Every candidate is gate-checked (brand neverDo) AND contrast-audited (WCAG, every text
element vs its effective background, hover states included) before it may be proposed.

_(budget not set yet)_

## Machine-proposed candidates

<!-- The wildcard generator writes ranked, gate-checked candidates here. Each names the
     rule it bends, its novelty score, and a rendered preview path. None are blessed. -->

_(none generated yet — run `python3 brand_pipeline/wildcard_generator.py <brand.yaml>`)_

## Blessed

_(nothing blessed yet)_
"""


def build_skill_md(doc: dict) -> str:
    """The kit AS A LOADABLE SKILL: any agent session that loads this file becomes the
    brand-designer agent for this brand — including its LEARNING behavior. This is the
    'compiled taste' wrapper: one artifact merging style+brand+rules+patterns+gates."""
    name = doc.get("brand", {}).get("name", "Brand")
    slug = _slug(name)
    return f"""---
name: brand-designer-{slug}
description: >-
  Compose on-brand pages, sections, and campaign surfaces for {name}. Load this skill
  whenever building ANYTHING for this brand — it is the brand's compiled taste: tokens,
  voice, layout patterns, motion, hard rules, and the quality gates. The skill also
  defines how you LEARN: field discoveries are proposed (never self-ratified) into
  learning/ for the home pipeline to review.
---

# brand-designer: {name}

You are composing for {name}. This kit is the brand's brain — everything below is
authoritative. Do not improvise around it; extend THROUGH it.

## Operating loop (every composition task)

1. **Load the canon**: `agent/brand.yaml` (canonical facts), `human/voice.md` (tone,
   vocabulary, casing, length budgets), `agent/tokens.css` (build on these variables),
   `agent/motion.json` (motion system; respect prefers-reduced-motion).
2. **Ask the human for the FREEDOM BUDGET** before generating a page: list the sections
   you plan, ask for a 0-5 level per section (see magic-trick.md for the ladder). 0 means
   median only. Never decide divergence levels yourself.
3. **Reuse before create**: match each section against `agent/layout-library.yaml`
   (project patterns win) — adapt via a pattern's variantKnobs before inventing. Sizes in
   patterns are relationships/classes; resolve them against the tokens, never as px.
4. **Compose**, honoring `agent/quality/rules.yaml`: `neverDo` is the ONLY hard gate;
   `avoid` bends only as a logged one-off; `do` is the affirmative style.
5. **Run the gates before calling anything done**:
   - `node agent/quality/contrast_audit.mjs <your-page.html>` — WCAG, every text element
     vs its effective background, hover states included.
   - `node agent/quality/slop_audit.mjs <your-page.html>` — section completeness (no
     metadata-only sections, no empty columns, maps carry addresses, forms state their
     reason, text never flush against media).
   - Self-review against `agent/quality/anti-ai-slop.md` for the non-scripted shapes.
6. **Propose, never bless.** Divergence beyond the budget, rule relaxations, and new
   patterns are PROPOSALS for a human.

## How you learn (field self-education — write it down, don't ratify it)

- Invented a section the gates pass and the human liked? Append it to
  `learning/proposals.yaml` (schema layout-patterns.v1; `origin: designed`,
  `source: field`, `scope: one-off`).
- Hit a failure, ambiguity, or a rule that fought the content? Append one line to
  `learning/signals.log`: `<ISO date> | field | <gate-or-context> | <what happened>`.
- NEVER edit `agent/brand.yaml`, `agent/layout-library.yaml`, or the Blessed section of
  `magic-trick.md` — those are home-ratified. Your learning flows back via
  `learning/` and the home pipeline's import + review (one-way ratchet: field proposes,
  home ratifies, the next kit export supersedes this copy).

## Escalate to the human, always

Blessing a magic trick, ratifying a proposed rule/pattern, the room brief (the moment,
the audience, the feeling), and anything that would relax a `neverDo`.
"""


LEARNING_README = """# learning/ — field self-education (proposals, never ratifications)

This kit LEARNS wherever it is used. Agents composing with it record discoveries here;
the home pipeline imports this folder (`taste_sync.py --import <kit>`), a human reviews,
and ratified learnings ship in the next kit export — which supersedes this copy.

- `proposals.yaml` — new layout patterns invented in the field that passed the gates
  (schema layout-patterns.v1; every entry `origin: designed`, `source: field`,
  `scope: one-off`). Proposals, not decisions.
- `signals.log` — one line per lesson/failure/ambiguity:
  `<ISO date> | field | <gate-or-context> | <what happened>`

Do NOT edit the canonical files (`agent/brand.yaml`, `agent/layout-library.yaml`,
`magic-trick.md` Blessed section) — field copies never self-ratify.
"""


# ── export ───────────────────────────────────────────────────────────────────────

def export(brand_yaml: Path, out: Path | None) -> Path:
    brand_dir = brand_yaml.parent
    doc = yaml.safe_load(brand_yaml.read_text())
    name = _slug(doc.get("brand", {}).get("name", "brand"))
    kit = out or (brand_dir / "kit")
    if kit.exists():
        shutil.rmtree(kit)
    (kit / "human").mkdir(parents=True)
    agent = kit / "agent"
    (agent / "quality").mkdir(parents=True)

    # human/ — readable layer
    for f in ("brand.md", "voice.md", "assets.md"):
        src = brand_dir / f
        if src.exists():
            shutil.copy2(src, kit / "human" / f)
    gallery = brand_dir / "components-preview"
    if gallery.is_dir():
        shutil.copytree(gallery, kit / "human" / "components-preview")

    # agent/contracts — localize the shared catalogs + standard layout-patterns
    shutil.copytree(CONTRACTS_DIR, agent / "contracts")

    # agent/brand.yaml — canonical, with contract refs REWRITTEN to the local copies.
    # Text-level rewrite (not yaml round-trip) so comments/anchors/formatting survive.
    text = brand_yaml.read_text()
    text = re.sub(r'"(?:\.\./)+brand_pipeline/contracts/', '"./contracts/', text)
    (agent / "brand.yaml").write_text(text)

    lib = brand_dir / "layout-library.yaml"
    if lib.exists():
        shutil.copy2(lib, agent / "layout-library.yaml")

    # fonts + image assets
    fonts_src = brand_dir / "assets" / "fonts"
    if fonts_src.is_dir():
        shutil.copytree(fonts_src, agent / "fonts")
    assets_out = agent / "assets"
    assets_out.mkdir()
    for img in sorted((brand_dir / "assets").glob("*")):
        if img.is_file():
            shutil.copy2(img, assets_out / img.name)

    # generated artifacts
    (agent / "tokens.css").write_text(build_tokens_css(doc, fonts_src))
    (agent / "motion.json").write_text(build_motion_json(doc))
    (agent / "quality" / "rules.yaml").write_text(build_quality_rules(doc))
    slop = SPEC_DIR / "anti-ai-slop.md"
    if slop.exists():
        shutil.copy2(slop, agent / "quality" / "anti-ai-slop.md")

    # portable gates: the kit carries its own immune system so FOREIGN agents can run
    # the checks, not just read the rules (playwright is their only dependency).
    for audit in ("contrast_audit.mjs", "slop_audit.mjs"):
        src = REPO_ROOT / "brand_pipeline" / audit
        if src.exists():
            shutil.copy2(src, agent / "quality" / audit)

    # field self-education: the learning/ write-back convention (see LEARNING_README).
    learning = kit / "learning"
    learning.mkdir()
    (learning / "README.md").write_text(LEARNING_README)
    (learning / "proposals.yaml").write_text(
        "schemaVersion: layout-patterns.v1\n# field-proposed patterns — origin: designed, "
        "source: field, scope: one-off. Imported + reviewed at home; never self-ratified.\n"
        "patterns: []\n")
    (learning / "signals.log").write_text(
        "# <ISO date> | field | <gate-or-context> | <what happened>\n")

    # entry points
    (kit / "readme.md").write_text(build_readme(doc))
    (kit / "SKILL.md").write_text(build_skill_md(doc))
    mt_src = brand_dir / "magic-trick.md"
    if not mt_src.exists():
        mt_src.write_text(MAGIC_TRICK_SCAFFOLD)   # stable home in the brand dir
    shutil.copy2(mt_src, kit / "magic-trick.md")

    return kit


def main():
    ap = argparse.ArgumentParser(description="Export a brand as a portable atomic kit.")
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="kit output dir (default: <brand_dir>/kit)")
    args = ap.parse_args()
    kit = export(args.brand_yaml.resolve(), args.out)
    n_files = sum(1 for _ in kit.rglob("*") if _.is_file())
    size_mb = sum(f.stat().st_size for f in kit.rglob("*") if f.is_file()) / 1e6
    print(f"Exported kit -> {kit}  ({n_files} files, {size_mb:.1f} MB)")
    for p in sorted(kit.iterdir()):
        print(f"  {p.name}{'/' if p.is_dir() else ''}")


if __name__ == "__main__":
    main()
