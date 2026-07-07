# Token-Layer Implementation — Batch Report (2026-07-03)

Implements `experiments/token-layer-design/SPEC.md` with all six binding decisions from
`DECISIONS.md` applied. Reference brand WoodWave; HubSpot validation deferred (fence).
No commits/pushes — everything is working-tree state.

## What shipped

1. **`brand_pipeline/tokens_css.py` (new)** — canonical layer-1 generator. Flat measured
   vars from `runs/<brand>/brand/brand.yaml` (colors/surfaces, type tiers incl. case +
   tracking, spacing, radius, motion, buttons, aspectPalette, ghost/rhythm ladders).
   Layer 1 stays flat (decision 6). Missing REQUIRED token ⇒ `TokenGenerationError`
   naming the token (decision 2). aspectPalette OPTIONAL (decision 5). Emits
   `<style id="tokens">` + `tokens.manifest.json` (brand-yaml sha256, style md sha256,
   generator version, token index) for drift + provenance.
2. **Alias layer kept as `--c-*`** (decision 1) — `component_vars`/`root_vars`/
   `legacy_root_vars` now emit aliases as `var(--layer1-token)` references; literal
   fallbacks stripped from renderer-emitted CSS. Legacy gate-readable literals
   (`--bg`/`--text`/`--accent`) unchanged for the older checks.
3. **Interaction re-scoping (alignment-batch handoff item)** — hover/interaction colors
   resolve per surface INCLUDING cards/panels: `component_vars(surface_role=…)` re-derives
   `--c-link-hover`/action colors per surface; panels re-scope via `.cs-panel { --c-link-hover:
   var(--c-panel-ink) }`-style alias rebinding, driven by layer-1 tokens. Gold `#edd580`
   hover remains dark-surface-only (WoodWave truth), enforced by surface-aware resolution +
   `interaction-contrast` gate (PASS on all 18 regate jobs).
4. **Structural variants (SPEC §C.3)** — `input_shape()` (underline|boxed) and
   `cta_shape()` (typographic|filled) derived from neverDo/primitives/measured tokens.
   Variant CSS (`.c-button`, `.c-field--boxed`) is emitted CONDITIONALLY by
   `structural_variant_css(doc)` — a brand that never uses a variant ships no dormant
   rule text (dormant grammar was tripping `no-radius`/`no-shadows`/`no-boxed-inputs`
   and is itself the AS-24 leak). Gallery harness uses `include_all=True` (labeled
   specimens carry every variant).
5. **`token-provenance` gate (new, in `onbrand_check.py` via `token_provenance.py`)** —
   advisory by default, HARD under `--composition` (matches invariants mode). Scans all
   emitted style blocks minus the generated tokens block. Colors/spacing/radius/type =
   ERROR; durations/easing = WARNING (decision 3). `/* provenance: structural … */`
   immediately before a declaration allowlists it; `/* provenance: preview-chrome */`
   suppresses a whole comparison-artifact/harness block. Violation detail carries the
   raw value + nearest/suggested token + foreign-brand callout, in the
   `| id | FAIL | detail |` row the repair loop parses. Legacy pages without
   `tokens.manifest.json` are skipped (advisory note), so pre-token artifacts never
   retro-fail.
6. **`render_section.py` retired (decision 4)** — callers migrated to `tokens_css`
   resolvers / composer path; module quarantined to `brand_pipeline/legacy/` with a
   README documenting migration paths. No dead imports (`rg 'render_section'` in live
   sources: none).
7. **`export_kit.build_tokens_css`** — now a wrapper over `tokens_css.emit_layer1`, so
   the export kit and composed pages share one layer-1 namespace (plus font-face +
   hosted/missing notes).
8. **Registry** — **AS-24 “Brand DNA leak: raw visual values in shared renderers”**
   added to `brand_pipeline/spec/anti-ai-slop.md` (three-part form: composer discipline +
   `token-provenance` gate + registry note). AS-25 remains the alignment batch's.
9. **`tokens_drift.py` (new, standalone)** — non-blocking staleness report (SPEC §F):
   compares brand.yaml/style hashes against stamps in `tokens.css`, manifests, and page
   tokens blocks; FRESH/STALE/UNSTAMPED verdicts; appends INFO to `signals.log`;
   always exit 0. (Standalone rather than a `taste_sync.py` edit — that file is
   foreign-worker territory; see conflict notes.)
10. **Gallery harness (`render_components_preview.py`)** — RP-1 fixed (no more
    `--c-accent: var(--ink)` pinning; accent/highlight fall back to `var(--ink-inverse)`
    only when the brand lacks them), per-surface alias blocks via `component_vars`,
    `preview-chrome` provenance banner, brand-agnostic specimen copy.

## Cluster elimination scorecard (vs `hardcode-audit.md`)

| Cluster | Verdict | How |
|---|---|---|
| CR-1 uppercase/case vocabulary | ELIMINATED | `--case-*`/`--tracking-*` tiers via `_tier_ref`; `text-transform: var(--c-case-…)` everywhere |
| CR-2 button cluster | ELIMINATED | fully token-driven (`--c-button-bg/fg/font/size/weight/ls/pad/radius`, measured hover bg swap replaces the universal brightness filter); emitted only for `cta_shape()=="filled"` brands |
| CR-3 motion defaults | ELIMINATED | `_MOTION_DEFAULTS` deleted; motion tokens REQUIRED in layer 1; `motion_vars_css` emits var refs |
| CR-4 logo wordmark styling | ELIMINATED | `--c-logo-weight/-ls` token refs (kind = structural from `navbar.logo` presence) |
| CR-5 underline-only input | ELIMINATED | `input_shape()` structural flag + `--c-input-radius/border/bg` tokens; boxed CSS conditional |
| CR-6 aspect-ratio literals | ELIMINATED / allowlisted | aspect aliases from aspectPalette (`--c-aspect-*`, no literal fallbacks); mobile recrops allowlisted structural |
| CR-7 hairline/accent fallbacks | ELIMINATED | alias refs, fallback literals stripped |
| CR-8 micro-spacing | ELIMINATED / allowlisted | scale-relative `calc(var(--baseline)…)` or em-relative structural (shape-not-magnitude) |
| CS-1 panel surface hexes | ELIMINATED | `--panel-*` layer-1 tokens (REQUIRED), aliases var-only |
| CS-2 ghost scale ladder | ELIMINATED | `--size-ghost-watermark-base` + calc-of-var clamps (decision 6: clamps live in layers 2/3) |
| CS-3 section rhythm | ELIMINATED | `--space-section-*`/rhythm tokens + calc-of-var |
| CS-4 editorial offset media spans | OUT OF SCOPE (deferred) | collage/split media-span item explicitly not this batch's (alignment REPORT) |
| CS-5 z-index ladder | ALLOWLISTED structural | comment per spec |
| CS-6 grid templates/breakpoints | ALLOWLISTED structural | comment per spec |
| CS-7 `_rgba_from_hex` | KEPT (universal resolver) | consumes brand values only |
| CP-1 page-level surface literals | ELIMINATED | `legacy_root_vars` aliases are var-refs; only gate-readable legacy literals remain (documented) |
| CP-2 hero brand-over-style override | ELIMINATED (values) | mechanic kept, values via tokens |
| CP-3 footer/nav chrome | ELIMINATED | via component_render token refs |
| RP-1 accent alias pinning | ELIMINATED | real accent resolution, `--ink-inverse` fallback only for optional tokens |
| RP-2 preview `ex-*` styles | ALLOWLISTED preview-chrome | whole-block suppression marker (harness never ships) |
| ST-1 style structure numerics | KEPT BY DESIGN | style numerics reach CSS only through custom-property exemptions; placeholders never emitted (docstring documents the discipline) |
| §6 render_section (232 hits) | LEFT PROVENANCE SCOPE | module quarantined to `legacy/` (decision 4) |

Late catches during matrix regeneration (this session): interlock mobile-recrop
`aspect-ratio: 3 / 2` allowlisted structural; interlock base `var(--c-aspect-landscape, 3 / 2)`
fallback stripped (WoodWave resolves identically via layer 1 `--aspect-landscape: 3 / 2`;
brands without aspectPalette get natural media ratio — device disabled, never a foreign
crop); hero-gallery + showcase divider shims marked `preview-chrome` (comparison-artifact
furniture; the 4rem padding there was literally flagged as “matches HubSpot
--space-section-y-md” — the foreign-brand callout working as designed).

## render_section.py retirement

Moved to `brand_pipeline/legacy/render_section.py` + `legacy/README.md` (migration map).
Callers now import resolvers from `tokens_css` (`color_value`, `type_role`,
`spacing_value`, `base_size`, `css_len`, `font_stack`) or render through
`compose_section.build_document`. Zero dead imports; suite + regate green after the move.

## Provenance gate behavior

- Advisory on plain runs, HARD under `--composition`; legacy pages (no manifest) skipped.
- Example violation line (captured live from the anchored-gallery build before its shim
  was marked as chrome):

```
| token-provenance | FAIL | [data-layout^="divider-"] .cs-section{padding}: raw `4rem` — no WoodWave Gallery token resolves to this value; nearest token: --size-display-hero@mobileL [foreign-brand value: matches HubSpot --space-section-y-md]; [data-layout^="divider-"] .c-caption{letter-spacing}: raw `0.14em` — no WoodWave Gallery token resolves to this value; nearest token: --tracking-eyebrow; allowlisted: 9 |
```

- Durations/easing report as WARNING rows (decision 3) — never flip overall verdict.
- Final worklist scan across the WoodWave matrix: **0 errors, 0 warnings**
  (`experiments/token-layer-impl/scan_worklist.py`).

## Tests + regate

- **Unit suite: 108/108 OK** (baseline 60 + 48 new) — `./venv/bin/python -m unittest
  discover brand_pipeline/tests`. New fixtures include a synthetic brand with values
  distinct from WoodWave exercising foreign-brand detection + multi-brand namespace
  identity (HubSpot itself deferred, see below).
- **`tools/phase0_regate.py`: 17/18 PASS, zero PASS→FAIL.** `page-anchored` FAIL→FAIL
  pre-existing (`single-accent`, documented; NOT rebaselined). All composition-mode jobs
  run the provenance check HARD and ACTIVE (manifests present after replay).

## WoodWave matrix regeneration + visual parity

Regenerated through the live pipeline only:
- 5 compose CLI pages (`full-editorial-luxury`, `full-radical-editorial`,
  `full-layout-patterns-v1`, `full-layout-patterns-v2`, `full-layout-patterns-v2-luxury`)
- `full-wildcard-centered-monument` via `tools/build_blessed_monument.py`
- hybrid run-1..5 / smoke / showcase / ablation on-off-control via
  `compose_from_composition.py` from persisted compositions
- `arm-a-structured` via `gen_arm_a.py`
- `page-anchored` via `build_anchored_variants.py --assemble-only` (standalone gates 6/6 PASS)
- showcase pattern pages via `build_showcase.py patterns` (4/4 gate-green)

**Parity (before/after Playwright shots + pixel diff, `parity/`):** detail crops
(statement, panel-hover) byte-IDENTICAL; full-page shots ≤ 0.0399% of subpixels changed
with max channel delta 5/255 — subpixel antialiasing jitter, no visible diff, no layout
shift (bboxes match text regions). WoodWave values flow through tokens with identical
computed CSS.

## Deferred

- **HubSpot validation** — fence respected (`runs/hubspot/**`, `experiments/hubspot-e2e/**`
  read-only; live external worker owns them). Multi-brand correctness proven with the
  synthetic fixture brand in unit tests. Real HubSpot regeneration happens after that
  worker exits.
- `hoverColor()` @media recursion — SPEC does not scope it into this batch; deferred.
- Collage/split media-span var-ification (CS-4) + knob-vs-stance lint — explicitly other
  batches' items.
- taste_sync.py extension — drift report shipped standalone (`tokens_drift.py`) to avoid
  touching a foreign-worker file; folding it in can happen once that session exits.

## Conflict protocol

Baseline mtime+sha256 recorded 03:02 (`baseline-hashes.txt`); re-checked before each edit
session and at close (05:20). **No foreign modifications appeared on any owned file during
the batch** — all hash changes on owned files are my own edits; `taste_sync.py`,
`generate_composition.py` (unedited by me) are byte-identical to baseline. One
self-inflicted scare documented in changes.md: a bad zsh loop briefly created junk
`compose/<name with spaces>` dirs and re-gated a stale artifact (looked like a foreign
.c-button write; it was my own loop's output). Junk dirs deleted; real dirs regenerated.

## Studio

:1500 was down at batch close (was healthy 02:57); restarted via `start-studio.sh`,
verified HTTP 200.

## Fence + commits

- No writes under `runs/hubspot/**` or `experiments/hubspot-e2e/**` (read-only).
- No git commits or pushes — working-tree changes only.
- `viewer.html`/`run_pipeline.py` untouched (changes don't affect them).
