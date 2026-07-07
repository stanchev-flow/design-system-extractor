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
        ├── motion-audit.yaml← tokens.motion + the mined per-selector motion table (when evidenced)
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
    """Kit tokens.css — now a WRAPPER over the canonical layer-1 generator
    (``tokens_css.emit_layer1``), so the export kit ships the IDENTICAL namespace the
    composed pages embed in their `<style id="tokens">` block (one generator, one
    truth — SPEC §B.1). The kit adds its own @font-face blocks + self-hosting note
    (offline field use). Missing REQUIRED tokens are annotated, not raised: the kit
    is documentation; the PAGE path is where generation hard-fails."""
    import tokens_css as tc
    lines, bp_lines, index, missing, disabled = tc.emit_layer1(doc)
    tokens = doc.get("tokens", {}) or {}
    not_hosted: list[str] = []
    for role, t in (tokens.get("type") or {}).items():
        fam = t.get("family") if isinstance(t, dict) else None
        if fam:
            local = fonts_dir.is_dir() and any(
                fam.lower() in f.stem.lower() for f in fonts_dir.glob("*.woff2"))
            if not local and fam not in not_hosted:
                not_hosted.append(fam)
    faces = _font_faces(fonts_dir)
    hosted_note = ("/* NOT self-hosted (no local font files): " + ", ".join(not_hosted)
                   + " — loads from its CDN when online, else falls down the declared "
                     "stack. */\n" if not_hosted else "")
    missing_note = ("/* WARNING — missing REQUIRED tokens (page generation hard-fails "
                    "on these; re-extract or author): " + "; ".join(missing) + " */\n"
                    if missing else "")
    disabled_note = ("/* devices disabled (optional tier absent): " + ", ".join(disabled)
                     + " */\n" if disabled else "")
    return (f"/* {doc.get('brand', {}).get('name', 'Brand')} — design tokens as CSS custom "
            f"properties. Generated by tokens_css.py v{tc.GENERATOR_VERSION} via "
            f"export_kit.py from brand.yaml (canonical); regenerate rather than "
            f"hand-editing. Same namespace as the composed pages' tokens block. */\n"
            + hosted_note + missing_note + disabled_note
            + (faces + "\n\n" if faces else "")
            + ":root {\n" + "\n".join(lines) + "\n}\n" + tc._media_blocks(bp_lines))


# ── motion.json ──────────────────────────────────────────────────────────────────

def build_motion_json(doc: dict) -> str:
    """The RESOLVED motion system (not the raw YAML): easing, durations, scroll-reveal,
    link-interaction mode + measured hover color, and the image-parallax treatment —
    everything a foreign agent needs to reproduce the brand's motion without our
    composers. Values mirror what compose_page/component_render actually emit.

    When the brand carries an EVIDENCED `tokens.motion` (authored from
    evidence/motion-audit.json — validator C13), the duration ladder / easings /
    signature moves come from it verbatim instead of the legacy 3-tier
    voice.motionSpec projection; the composer-behavior blocks (scrollReveal, link,
    imageParallax) stay, since they describe what OUR composed pages do."""
    m = motion_spec(doc)
    p = image_parallax_spec(doc)
    out: dict = {}
    tokens_motion = (doc.get("tokens") or {}).get("motion")
    if isinstance(tokens_motion, dict) and tokens_motion \
            and not tokens_motion.get("notObserved"):
        out["source"] = ("tokens.motion — evidence-derived (per-selector CSS motion "
                         "audit); the full table ships as motion-audit.yaml")
        for key in ("durations", "easings", "signatureMoves", "reducedMotion"):
            if tokens_motion.get(key) is not None:
                out[key] = tokens_motion[key]
    else:
        out["easing"] = {"primary": m["ease"]}
        out["durationsMs"] = {"fast": int(m["fast"].rstrip("ms")),
                              "base": int(m["base"].rstrip("ms")),
                              "slow": int(m["slow"].rstrip("ms"))}
    out.update({
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
    })
    out.setdefault("reducedMotion", "respect")
    return json.dumps(out, indent=2) + "\n"


def build_motion_audit_yaml(doc: dict, brand_dir: Path) -> str | None:
    """agent/motion-audit.yaml — the brand's motion FIDELITY layer: the authored
    `tokens.motion` contract (duration ladder, easings, named signature moves) plus
    the mined per-selector evidence table (evidence/motion-audit.json) it was derived
    from. None (not emitted) when the brand has neither — degrade-to-absent, no
    invented tiers."""
    tokens_motion = (doc.get("tokens") or {}).get("motion")
    audit_path = brand_dir / "evidence" / "motion-audit.json"
    audit = None
    if audit_path.is_file():
        try:
            audit = json.loads(audit_path.read_text())
        except (json.JSONDecodeError, OSError):
            audit = None
    if not isinstance(tokens_motion, dict) and audit is None:
        return None
    payload: dict = {
        "schemaVersion": "kit-motion-audit.v1",
        "note": ("Authored contract first (tokens.motion, evidence-derived — "
                 "validator C13), then the mined per-selector table it cites. "
                 "Selectors are the SOURCE site's (provenance, not classnames to "
                 "reuse); durations/easings are the values to reproduce."),
    }
    if isinstance(tokens_motion, dict):
        payload["tokensMotion"] = tokens_motion
    if audit:
        payload["evidence"] = {
            "source": "evidence/motion-audit.json (mine_motion.py)",
            "durationCensus": audit.get("durationCensus") or {},
            "easingCensus": audit.get("easingCensus") or {},
            "motionVars": audit.get("motionVars") or {},
            "keyframes": [{"name": k.get("name"), "file": k.get("file"),
                           "frames": k.get("frames")}
                          for k in (audit.get("keyframes") or [])],
            "transitions": audit.get("transitions") or [],
            "animations": audit.get("animations") or [],
            "jsTimingNotes": audit.get("jsTimingNotes") or [],
        }
    return yaml.safe_dump(payload, sort_keys=False, width=100, allow_unicode=True)


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
4. **`agent/motion.json`** — the resolved motion system (duration ladder, easings,
   signature moves when evidenced; scroll-reveal, link hover, image parallax). Respect
   `prefers-reduced-motion`. Where present, **`agent/motion-audit.yaml`** carries the
   full per-selector evidence table the values were derived from.
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
    # PRESERVE FIELD LEARNINGS across re-export: learning/ is the field write-back
    # channel — wiping it on every export would erase un-imported proposals/signals
    # (the ratchet only allows HOME to resolve them, never the exporter to drop them).
    preserved: dict[str, str] = {}
    for lf in ("signals.log", "proposals.yaml"):
        old_f = kit / "learning" / lf
        if old_f.exists():
            preserved[lf] = old_f.read_text()
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
    motion_audit = build_motion_audit_yaml(doc, brand_dir)
    if motion_audit is not None:
        (agent / "motion-audit.yaml").write_text(motion_audit)
    (agent / "quality" / "rules.yaml").write_text(build_quality_rules(doc))
    slop = SPEC_DIR / "anti-ai-slop.md"
    if slop.exists():
        (agent / "quality" / "anti-ai-slop.md").write_text(distill_anti_slop(slop))

    # portable gates: the kit carries its own immune system so FOREIGN agents can run
    # the checks, not just read the rules (playwright is their only dependency).
    for audit in ("contrast_audit.mjs", "slop_audit.mjs"):
        src = REPO_ROOT / "brand_pipeline" / audit
        if src.exists():
            shutil.copy2(src, agent / "quality" / audit)
    # standalone runtime (kit gap: gates needed the home repo's playwright): one command,
    # installs its own dependency next to the scripts on first run.
    (agent / "quality" / "package.json").write_text(
        '{\n  "name": "kit-quality-gates",\n  "private": true,\n'
        '  "dependencies": { "playwright": "^1.45" }\n}\n')
    runner = agent / "quality" / "run_gates.sh"
    runner.write_text(RUN_GATES_SH)
    runner.chmod(0o755)

    # field self-education: the learning/ write-back convention (see LEARNING_README).
    learning = kit / "learning"
    learning.mkdir()
    (learning / "README.md").write_text(LEARNING_README)
    (learning / "proposals.yaml").write_text(preserved.get("proposals.yaml") or (
        "schemaVersion: layout-patterns.v1\n# field-proposed patterns — origin: designed, "
        "source: field, scope: one-off. Imported + reviewed at home; never self-ratified.\n"
        "patterns: []\n"))
    (learning / "signals.log").write_text(preserved.get("signals.log") or
        "# <ISO date> | field | <gate-or-context> | <what happened>\n")

    # entry points
    (kit / "readme.md").write_text(build_readme(doc))
    (kit / "SKILL.md").write_text(build_skill_md(doc))
    mt_src = brand_dir / "magic-trick.md"
    if not mt_src.exists():
        mt_src.write_text(MAGIC_TRICK_SCAFFOLD)   # stable home in the brand dir
    shutil.copy2(mt_src, kit / "magic-trick.md")
    _append_blessed_geometry(kit / "magic-trick.md", doc)
    _lint_voice_slots(brand_dir, doc)

    return kit


RUN_GATES_SH = """#!/usr/bin/env bash
# Standalone gate runner: ./run_gates.sh <page.html> [more.html ...]
# First run installs playwright locally (requires node >= 18). Exit 1 on any failure.
set -euo pipefail
ARGS=()
for p in "$@"; do ARGS+=("$(cd "$(dirname "$p")" && pwd)/$(basename "$p")"); done
cd "$(dirname "$0")"
if [ ! -d node_modules/playwright ]; then
  npm install --no-fund --no-audit
  npx playwright install chromium
fi
status=0
for page in "${ARGS[@]}"; do
  node contrast_audit.mjs "$page" || status=1
  node slop_audit.mjs "$page" || status=1
done
exit $status
"""


def distill_anti_slop(src: Path) -> str:
    """Brand-neutral DISTILLATION of spec/anti-ai-slop.md for the kit (F7/AS-38): keep
    the preamble ("what counts as slop" / "how to use") and, per `## AS-NN` entry, the
    heading + its generic **Rule** shape statement. Drop every repo case study — the
    **Caught here** paragraphs (where the home repo's brand hexes/copy/filenames live)
    and the repo-specific **Why/Fix/Verify** prose — plus the trailing authoring
    template. The FULL registry (with case studies) stays home in `spec/`; the kit
    ships the reusable failure shapes, not the home brand's history."""
    lines = src.read_text().splitlines()
    out: list[str] = []
    i = 0
    # preamble: everything before the first AS entry
    while i < len(lines) and not lines[i].startswith("## AS-"):
        out.append(lines[i])
        i += 1
    out.append("> **Kit copy — distilled at export.** Each entry below is the rule "
               "statement only; the home repo's registry additionally carries the "
               "concrete caught-instance history behind every rule.")
    out.append("")
    while i < len(lines):
        line = lines[i]
        if line.startswith("## AS-"):
            out += [line, ""]
            i += 1
            keeping = False
            while i < len(lines) and not lines[i].startswith("## AS-"):
                l = lines[i]
                if l.startswith("**"):
                    keeping = l.startswith("**Rule**")
                if keeping and l.strip() not in ("---",):
                    out.append(l)
                i += 1
            if out and out[-1].strip():
                out.append("")
            out += ["---", ""]
        else:
            i += 1
    return "\n".join(out).rstrip() + "\n"


def _append_blessed_geometry(mt: Path, doc: dict) -> None:
    """Kit gap: blessed magic-trick entries were one-liners referencing a render the kit
    does not ship — field agents had to GUESS offsets. Inline the authoritative ladder
    CSS for every blessed trick named by the reproduce command line. `--wildcard` keys
    are THIS brand's layout ids; each dispatches to its scaffold family's ladder entry
    (the ladder is keyed by scaffold, not layout id)."""
    text = mt.read_text()
    marker = "## Appendix — blessed geometry (exact CSS)"
    m = re.search(r'--wildcard "([^"]+)"', text)
    if not m or marker in text:
        return
    try:
        import compose_section as cs
        import wildcard_generator as wg
    except Exception:
        return
    blocks = []
    for pair in m.group(1).split(","):
        if "=" not in pair:
            continue
        lid, _, lvl = pair.strip().partition("=")
        layout = cs.find_layout(doc, lid.strip())
        if layout is None:
            continue
        entry = (wg.SECTION_LADDER.get(cs.scaffold_key(layout)) or {}).get(int(lvl))
        if entry:
            desc, css = entry
            blocks.append(f"### {lid.strip()} — L{lvl}: {desc}\n\n```css\n{css}\n```\n")
    if blocks:
        mt.write_text(text + f"\n{marker}\n\nGenerated at export from the wildcard "
                      "ladder — the SAME rules the home composer applies via `--wildcard`. "
                      "Copy these; do not re-derive offsets.\n\n" + "\n".join(blocks))


_COPY_KEY_TO_SLOT_WORDS = {
    "heading": ("title", "heading", "display", "statement"),
    "body": ("body", "lede", "paragraph", "description"),
    "caption": ("caption",),
    "eyebrow": ("eyebrow", "kicker", "label"),
    "action": ("action", "cta", "link", "form"),
    "ghost": ("ghost", "watermark"),
}


def _lint_voice_slots(brand_dir: Path, doc: dict) -> None:
    """Kit gap: voice.md §5 shipped copy roles (hero captions) that the section's pattern
    has no slot for — field agents had to guess placement. WARN (never fail) for every
    copy role in a §5 block whose matched layout pattern covers no such slot."""
    voice = brand_dir / "voice.md"
    lib_f = brand_dir / "layout-library.yaml"
    if not (voice.exists() and lib_f.exists()):
        return
    try:
        lib = yaml.safe_load(lib_f.read_text()) or {}
        pats = {p["id"]: p for p in (lib.get("patterns") or []) if isinstance(p, dict)}
        layouts = {l.get("id"): l for l in (doc.get("layouts") or [])}
        sec5 = voice.read_text().split("## 5.", 1)
        if len(sec5) < 2:
            return
        for block in sec5[1].split("### ")[1:]:
            title, _, rest = block.partition("\n")
            lid = next((i for i in layouts
                        if i and i.replace("-", " ") in title.lower()), None)
            ref = ((layouts.get(lid) or {}).get("patternRef") or {}).get("id")
            pat = pats.get(ref)
            if not pat:
                continue
            slot_text = " ".join(
                f"{sl.get('kind', '')} {sl.get('role', '')} {sl.get('note', '')}"
                for sl in ((pat.get("contentShape") or {}).get("slots") or [])).lower()
            keys = re.findall(r"^- (\w+)", rest, re.M)
            for key in keys:
                k = key.rstrip("s").lower()
                words = _COPY_KEY_TO_SLOT_WORDS.get(k)
                if words and not any(w in slot_text for w in words):
                    print(f"  [voice-lint] WARN: voice.md §5 '{title.strip()}' has copy "
                          f"role '{key}' but pattern '{ref}' has no matching slot — "
                          f"field agents will guess its placement")
    except Exception as e:                        # lint must never break an export
        print(f"  [voice-lint] skipped ({e})")


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
