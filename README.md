# Design System Extractor — Stanchev Fork

> **Personal fork** of [webflow/design-system-extractor](https://github.com/webflow/design-system-extractor), maintained by [@stanchev-flow](https://github.com/stanchev-flow) for hackathon experimentation. The upstream pipeline mechanics documented below are unchanged. See [Local changes](#local-changes) at the bottom for fork-specific additions and tested run recipes.

---

Design System Extractor turns website screenshots plus available source-site styles into text-based design-system artifacts, generated single-file sites, image assets, and reviewable run outputs. The project is built around a versioned pipeline: each run writes immutable artifacts under `runs/vNNN/`, then regenerates `viewer.html` so versions can be compared side by side.

The current goal is broader than screenshot replication. The pipeline is an experiment in importing richer representations of external brand and design systems into Webflow-like generation workflows, and in building a "good design taste" engine that can help generated sites avoid generic output from the first draft.

Walkthrough video: [Loom project walkthrough](https://www.loom.com/share/7f4b8068af1145d3bfb6bcf4b7ce27d4)

## Why This Exists

Plain LLM site generation tends to produce generic design systems unless the input preserves real taste and visual specificity. Simple CSS ingestion, screenshot replication, or small `design.md` files only capture part of what makes a site feel designed. A website expresses brand through typography, color, imagery, graphics, decorations, surface relationships, layout rhythm, and interaction details.

Screenshots and source code each help, but neither is enough by itself:

- Screenshots show the authored visual expression, but not exact implementation values.
- Source HTML/CSS provides concrete colors, variables, fonts, and assets, but not always the visible design intent.
- Design-system markdown is useful only if it preserves rich visual relationships rather than flattening everything into global tokens.

## Opportunities

This work points at two high-level opportunities:

- Import richer brand/design-system representations into Webflow from external sources such as screenshots, live sites, archived HTML/CSS, and generated design-system artifacts.
- Build a design-taste engine that helps net-new sites generate polished, non-generic designs and helps existing brands explore improved systems for launches, sub-brands, campaigns, and new product directions.

The long-term shape is a library of extracted resources: color systems, type systems, imagery direction, graphics, section structures, interaction patterns, and component recipes that can be recombined into bespoke, good-looking sites for arbitrary prompts.

## Quick Start

Use the repo virtual environment for local commands:

```bash
./venv/bin/python run_pipeline.py
```

That runs the full default pipeline against:

```text
screenshots/best/use for testing
```

Common variants:

```bash
./venv/bin/python run_pipeline.py --version v123
./venv/bin/python run_pipeline.py --screenshots-dir "screenshots/best/use for testing"
./venv/bin/python run_pipeline.py --design-only --version v123
./venv/bin/python run_pipeline.py --sites-only --version v123
./venv/bin/python run_pipeline.py --assets-only --version v123 --site-assets
```

After a run, open `viewer.html` in a browser to compare generated artifacts.

## Configuration And Keys

Defaults live in `config.default.yaml`. Pass an override file with:

```bash
./venv/bin/python run_pipeline.py --config path/to/config.yaml
```

The pipeline reads API keys from the shell environment first, then from repo-local `.env.local` if present. `.env.local` is git-ignored.

```bash
cp .env.example .env.local
```

Supported keys:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_API_KEY
GEMINI_API_KEY
```

## Pipeline Mechanics

The full `run_pipeline.py` flow is roughly:

```text
screenshot + optional source HTML/CSS
  -> source style extraction and source-style ledger
  -> section inventory and section crop detection
  -> per-section grounding
  -> full-page/global grounding
  -> normalized layouts and surface/component contract
  -> design-system synthesis and style reconciliation
  -> site-generation input assembly
  -> generated HTML sites
  -> optional gpt-image-2 site assets
  -> audits, manifest, viewer-data, and viewer regeneration
```

Some flags skip or reuse parts of this flow. For example, `--design-only` stops before site HTML generation, `--sites-only` regenerates HTML from existing design-system inputs, `--surface-map-only` stops after surface/component mapping, and `--assets-only` backfills image assets for existing generated sites.

## Core Learnings

Grounding first: the first important step is pure data gathering. The pipeline tries to describe what is visible before deciding what it means. Mechanics beat vibes: spacing, type scale, surface nesting, image treatment, decoration placement, edge behavior, and interaction affordances are more useful than saying a page feels "premium" or "technical."

Local and global context both matter. Section crops provide smaller context and higher fidelity for local surfaces, components, typography, and imagery. The full-page screenshot preserves global rules: section color rhythm, grouped background runs, container sizing, transitions, and page-level hierarchy.

Schema helps conversion. A flexible but rigid YAML structure makes later conversion more reliable by attributing visual facts into stable kinds such as `section`, `surface`, `layout`, `text`, `control`, `media`, `divider`, and `effect`.

Surface-to-child relationships are load-bearing. A proper design system needs to know which components live on which surfaces. Flat tokens lose this context; YAML contracts preserve host-surface and child-component pairings such as buttons-on-dark, labels-on-image, cards-inside-modules, and dividers-on-shared-canvases.

Evals help find signal, but fixes come from bugs and instructions. Critique/repair loops and reviews identify where abstraction or fidelity breaks, but the biggest gains have come from investigating each failure and improving the pipeline, schema, prompts, and deterministic checks.

Image references beat words for creative direction. For generated assets, source section crops plus `gpt-image-2` references preserve style, composition, and media edge behavior better than text-only prompts.

## Source-Style Extraction

When source HTML/CSS is available, the pipeline extracts source-backed style facts and uses them as evidence. This includes colors, gradients, font families, font files, typography values, CSS variables, and document color literals.

Key artifacts:

- `source-colors.json` - raw extracted colors, typography, font assets, and related facts.
- `source-colors.md` - human-readable source style report.
- `source-style-ledger.yaml` - role-oriented source style ledger for generation and auditing.
- `source-fonts/` - copied or downloaded font assets when available.
- `design-system-style-audit.json` - audit of source-style reconciliation.

Source CSS is evidence, not automatic authority. Exact source values are most useful when mapped to the correct visual role, such as surface, text, border, action fill, icon, shadow, scrim, or gradient.

## Design-System Artifacts

Depending on the run and strategy, a per-site `single/` folder can include:

- `sections.json` - detected page sections and crop boundaries.
- `section-inventory.md` - top-level section inventory before cropping.
- `section-groundings/` - per-section raw grounding files.
- `structural-analysis.md` - merged site-level grounding.
- `layouts.yaml` - source layout structure separate from reusable design-system rules.
- `surface-component-contract.yaml` - deterministic host-surface and child-component contract.
- `surface-component-contract-audit.md` / `.json` - contract coverage and leakage audit.
- `surface-component-map.md` - model-backed surface/component map when used as fallback or comparison.
- `design-system.md` - canonical text-based design-system artifact, often with YAML front matter plus readable Markdown sections.
- `design-system-review.md` / `.json` - screenshot-based design-system review.
- `design-system-conversion-review.md` / `.json` - review of conversion loss from surface facts into the design system.
- `site-generation-input.md` - final prompt input sent to site generators.

## Generated Sites And Assets

Final site outputs are single-file HTML pages such as:

```text
site-claude.html
site-gpt55.html
```

Some runs also include grounding-derived sidecars such as:

```text
site-generation-input.grounding.md
site-claude-grounding.html
site-gpt55-grounding.html
```

When site asset generation is enabled, the pipeline scans generated HTML for explicit asset slots, builds placement-aware prompts, generates `gpt-image-2` assets, and rewrites the HTML to use local PNGs. Asset manifests are saved next to the generated sites, usually as `site-*.assets.json`, with images under `generated-assets/`.

## Main Entry Points

`run_pipeline.py` is the canonical full-pipeline runner. It handles version allocation, screenshot processing, source-style extraction, grounding, contracts, design-system synthesis, generated HTML, generated assets, reviews, manifests, and `viewer.html` regeneration.

`src/screenshot_to_template/cli.py` is the package CLI for a narrower one-shot operation: one screenshot in, one design-system markdown file out. It is exposed by `pyproject.toml` as:

```bash
screenshot-to-template path/to/screenshot.png -o design-system.md
```

Specialized experimental runners:

```bash
./venv/bin/python run_image_pipeline.py
./venv/bin/python run_live_source_pipeline.py --version v001 --screenshots-dir path/to/screenshots
./venv/bin/python run_section_grounding.py --help
./venv/bin/python run_additive_design_system.py --help
```

The main package code lives under `src/screenshot_to_template/`, especially:

- `pipeline/grounding_by_section.py` - section-by-section grounding.
- `pipeline/splitter.py` - screenshot section detection and crop utilities.
- `source_colors.py` and `source_style_ledger.py` - source-style extraction and reconciliation.
- `surface_contract.py` - deterministic surface/component contract compilation.
- `site_assets.py` - generated site asset scanning, prompting, and replacement.
- `models/` - provider adapters for Anthropic, Google, and OpenAI.
- `prompts.py` - source default prompts.

## Outputs And Viewers

Full runs are written under:

```text
runs/vNNN/
```

Important viewer files:

- `viewer.html` - main comparison viewer for normal pipeline runs.
- `viewer-data/vNNN.js` - lazily loaded payloads used by `viewer.html`.
- `viewer-image.html` - viewer for `run_image_pipeline.py`.
- `viewer-live-site.html` - viewer for `run_live_source_pipeline.py`.
- `version-scoreboard.html` - generated score summary across run versions.

Pipeline walkthrough pages can be generated with:

```bash
./venv/bin/python tools/generate_pipeline_walkthrough.py \
  --version v177 \
  --item 2025-12-12_88730-roma-hotel-and-restaurant-framer-website-template \
  --output v177-roma-pipeline-walkthrough.html
```

## Prompt And Versioning Rules

Before changing or testing pipeline prompts, create a new `runs/vNNN/` folder and put the updated prompt files there. Completed run folders are the record of what happened, so do not edit old prompt snapshots to retroactively fix a run.

Only update source prompt defaults in `src/screenshot_to_template/prompts.py` when intentionally promoting a versioned prompt into the defaults.

If a change is tied to a pipeline version, update that version's `runs/vNNN/changes.md`. For repo-level changes, update the nearest relevant changelog, usually root `changes.md`.

## Regenerating `viewer.html`

Regenerate `viewer.html` after any change that affects viewer layout, viewer data shape, embedded run output rendering, `viewer.html`, or `run_pipeline.py`:

```bash
./venv/bin/python - <<'PY'
from run_pipeline import generate_viewer, RUNS_DIR, PROJECT_DIR
generate_viewer(RUNS_DIR, PROJECT_DIR / "viewer.html")
print("viewer regenerated")
PY
```

## Development Checks

Useful syntax and test commands:

```bash
./venv/bin/python -m py_compile run_pipeline.py
./venv/bin/python -m py_compile run_image_pipeline.py
./venv/bin/python -m pytest tests
```

For targeted checks:

```bash
./venv/bin/python -m pytest tests/test_splitter.py
./venv/bin/python -m pytest tests/test_design_system_review.py
./venv/bin/python -m pytest tests/test_surface_contract.py
./venv/bin/python -m pytest tests/test_site_assets.py
./venv/bin/python -m pytest tests/test_framework_generator.py
```

## Repository Notes

Read `AGENTS.md` before doing substantial work. It contains repo-specific rules for viewer regeneration, prompt versioning, changelog maintenance, design-system token guidance, and section-separator experiment directories.

Section-separator experiments should use only:

```text
runs/section-separator/vNNN-*
```

Put primary outputs under `artifacts/` and temporary scratch files under `temp/` inside the same versioned folder.

## Local Changes

This fork adds the following on top of the upstream repository:

### Fork-specific files

- **`config-anthropic.yaml`** — drop-in `--config` override that routes both `provider` and `section-detection-provider` to `anthropic/claude-opus-4-1-20250805`, sets `surface-map-mode: contract`, and disables site-asset generation. Useful when the OpenAI key is missing or when `gpt-5.5` with `reasoning-effort: high` exhausts its output budget on hidden reasoning tokens and returns an empty design-system synthesis ("Design system synthesis returned empty output"). The Anthropic route is the known-working path on this fork.
- **`screenshots/hackathon-test/hatch.png`** — test fixture (Hatch product page screenshot, no source HTML sidecar so source-style extraction is skipped).

### Fork-specific runs

- **`runs/v201-hatch/`** — first end-to-end run on the Hatch fixture. Design system was synthesized by Claude Opus 4.1 (~$0.85). Sites were later filled in via `--sites-only` using `claude-opus-4-6` and `gpt-5.5` (~$1.20).
- Upstream reference runs `v170`–`v178` are retained for viewer comparison.

### Tested run recipes

```bash
# 1. Anthropic-only design-system extraction (no site HTML, no image assets).
#    Avoids the gpt-5.5 reasoning-effort=high empty-output bug. ~$0.85.
./venv/bin/python run_pipeline.py --design-only --no-site-assets \
  --config config-anthropic.yaml \
  --screenshots-dir "screenshots/hackathon-test" \
  --version vNNN-mine

# 2. Sites-only run that reuses an existing extracted design system.
#    Cheap (~$1-2) and useful for iterating on site-gen prompts/skills
#    without re-paying for grounding.
./venv/bin/python run_pipeline.py --sites-only --no-site-assets \
  --screenshots-dir "screenshots/hackathon-test" \
  --version v201-hatch

# 3. Full default pipeline (uses OpenAI gpt-5.5 by default).
#    KNOWN ISSUE: design-system synthesis may return empty output when
#    reasoning-effort=high. If that happens, switch to recipe 1 above
#    or set reasoning-effort to medium in your own override config.
./venv/bin/python run_pipeline.py --no-site-assets \
  --screenshots-dir "screenshots/hackathon-test" \
  --version vNNN-mine
```

### Local viewer and Design System Studio

Use `studio_server.py` (via `./start-studio.sh`) for both the comparison viewer and the Design System Studio UI on **one port** (default `1500`). It serves static files (`viewer.html`, `runs/**`, etc.) and handles `/studio` plus the project API. Do **not** use `python3 -m http.server 1500` for Studio — that static server has no `/studio` route and returns 404.

```bash
./start-studio.sh
# Studio:  http://127.0.0.1:1500/studio
# Viewer:  http://127.0.0.1:1500/viewer.html
```

If port 1500 is already taken (e.g. by a plain `http.server`), stop that process first (`lsof -i :1500`) or set `STUDIO_PORT=8800 ./start-studio.sh`.

### Framework site generation (React + Tailwind v4) — default

**Framework-first** is on by default: new runs build React + Tailwind v4 + shadcn-style sites and **skip** vanilla one-shot HTML (`site-claude.html` / `site-gpt55.html`). To also generate vanilla HTML, set `vanilla-site-generation-enabled: true` in config or pass `--vanilla-sites`.

This path scaffolds a real Vite package per run item (`runs/{version}/{item}/single/framework-{claude|gpt55}/`), syncs DTCG tokens from the design-system YAML front matter, asks the LLM for `src/App.tsx` (shadcn-style components), runs `npm ci && npm run build` (vite-plugin-singlefile), and copies the result to viewable HTML:

```text
runs/{version}/{item}/single/site-gpt55-framework.html
runs/{version}/{item}/single/site-claude-framework.html
runs/{version}/{item}/single/framework/          # full source package
```

Defaults in `config.default.yaml`: `framework-generation-enabled: true`, `vanilla-site-generation-enabled: false`. Studio projects inherit the same via `runs/.studio/{version}.config.yaml`.

```bash
# Full pipeline (framework only; vanilla skipped unless --vanilla-sites)
./venv/bin/python run_pipeline.py \
  --screenshots-dir "screenshots/hackathon-test" \
  --version vNNN-mine

# Force framework on a run that disabled it in saved config
./venv/bin/python run_pipeline.py --framework-sites \
  --screenshots-dir "screenshots/hackathon-test" \
  --version vNNN-mine

# Also generate vanilla one-shot HTML
./venv/bin/python run_pipeline.py --vanilla-sites \
  --screenshots-dir "screenshots/hackathon-test" \
  --version vNNN-mine

# Framework-only regen from an existing design system (no vanilla HTML regen)
./venv/bin/python run_pipeline.py --sites-only --framework-sites \
  --screenshots-dir "screenshots/hackathon-test" \
  --version v301-mine
```

**Nav/footer 1:1 from live URL:** When Studio (or `tools/extract_chrome.py`) harvests a project URL, it writes `runs/{version}/assets/source-chrome.json` plus `source.html`. Framework generation emits token-styled `SiteNav` / `SiteFooter` from that contract; the LLM builds only the body in `App.tsx`. Re-run framework after re-harvesting if the source site changes.

```bash
./venv/bin/python tools/extract_chrome.py \
  --html runs/greenhouse/assets/source.html \
  --base-url https://www.greenhouse.com \
  --out runs/greenhouse/assets/source-chrome.json
```

**Prerequisites:** Node.js 20+ and `npm` on PATH. First build per item runs `npm ci` inside `single/framework/` (~1–2 min). Reference handoff package: `handoff/v302-fieldnote/`. Scaffold template: `handoff/scaffold/framework-site/`. Prompt: `website-gen-framework-prompt.md` (copied into each run as `runs/{version}/website-gen-framework-prompt.md`).

Unit tests (no LLM): `./venv/bin/python -m pytest tests/test_framework_generator.py`

