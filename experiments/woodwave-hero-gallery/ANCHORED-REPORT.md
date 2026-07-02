# WoodWave — Anchored Hero Variants (grid/overlap contract upgrade)

Supersedes the previous anchored lane IN PLACE. Same anchored-variation discipline (seed =
the measured `hero-display-over-staggered-media` pattern, `novelty:"adapt"`, drift-band,
dark inverse + gold Melodrama 500 headings, hoisted nav, `#edd580` hover), but the five
variants now exercise the user's requested PLACEMENT axes through the new composition.v1
grid/overlap contract fields — no gallery shims, no "nearest expressible" fallbacks.

## What changed in the contract (composition.v1 §4.6.5 — ALL fields optional)

Schema (`brand_pipeline/spec/composition.v1.schema.json`), docs
(`composition-schema.md` §4.6.4/§4.6.5) and rules (`styles/composition-rules.md` §4b):

- **section-level** `grid {columns (default 12), gutter}` — per-section grid override.
- **section-level** `alignment {anchor: centered|left|right, counterweight}` — mid-page
  heroes are no longer hardcoded left (`#sec-0`-only centering retired).
- **slot-level placement**: `colStart`, `colSpan`, `rowSpan`, `offsetCols`,
  `offsetBaselines`, `alignTo {slot, edge: left|right|top|bottom | corner: tl|tr|bl|br}`.
- **overlap registration**: `registration {toSlot, edge, depthCols|depthBaselines,
  z: back|mid|front}` — declared overlaps replace magic % offsets.
- **mediaAspect honored for real**: `wide` (2:1) and `pano` (3:1) added to
  portrait/landscape/square/freeform; rendered as `aspect-ratio` CSS.
- **multiple media slots per section** with distinct placement/z, including `z:back` +
  `width:"full-bleed"` background layers (sanctioned text-on-media, auto scrim for the
  text-contrast gate) and `z:front` small media anchored to a corner via `alignTo.corner`.

## Renderer changes (adapter + composers)

- `compose_from_composition.py`: round-trips every placement field into layout dicts
  (`_slot_placement`/`_media_layers` classify media into background / overlay / corner /
  base layers; `layout['alignment'] / ['_placement'] / ['_mediaLayers'] / ['_grid'] /
  ['_floatSide']`). No more collapsing to `columns:1|2` + booleans.
- `compose_section.py`: layered stack-hero path (`_stack_hero_layered`) renders N media
  layers with explicit z-order (`back=0 < base=1 < mid=2 < front/corner=3 < title=4`),
  grid-column spans from `colStart/colSpan`, registered overlap offsets from
  `registration` depth in cols/baselines, background layer + scrim, corner-anchored
  media; `layout_placement_css()` emits per-section alignment/grid/mirror CSS.
- `component_render.py`: `render_image` honors an `aspect` prop via `aspect-ratio` CSS.
- `generate_composition.py`: `build_prompt` exposes the full placement vocabulary +
  PLACEMENT rules block, so seeded patterns and variety directives can reference spans,
  sides, aspects and layering.
- `onbrand_check.py` untouched (concurrency contract); its new **text-contrast** and
  **decoration-salience** hard checks are active and all shipped pages pass them.

### The 4 composer gap fixes (from the previous lane's honest-limits list)

1. **Stack copy was page-global** (first hero's eyebrow/support/CTA won) → per-section via
   `LAYOUT_COPY[layout_id]` + `copy_for(layout)`; every hero on the assembled page now
   shows its own generated copy.
2. **Interlock dropped support/CTA slots** → now rendered in a `cs-interlock-foot` block.
3. **Collage double-accent on dark** (heading AND arrow link hardcoded `accent`) → CTA is
   no longer accent-classed; gate-compliant single accent.
4. **Per-section alignment was `#sec-0`-only** → `alignment.anchor` is a contract knob
   compiled to scoped per-section CSS by `layout_placement_css()`.

## Seed pattern provenance (unchanged)

- Pattern **`hero-display-over-staggered-media`** `[project]` from
  `runs/woodwave/brand/layout-library.yaml`, `origin: extracted`,
  `provenance: [opening-bookend]`. Seeded via `generate_composition.seed_patterns` →
  `layout_library.match` → `render_pattern_constraint`; every variant cites
  `seededFrom: {lib: project, id: hero-display-over-staggered-media}`.
- The "Original (measured)" hero is derived deterministically from the pattern (its label
  is now baked into the composition's eyebrow copy — the shim `::before` is retired).

## Per-variant results (model `claude-opus-4-8`, live; drift floor = adapt 2.5)

| V | axis (user-requested) | contract fields exercised | drift | attempts | gen gate | standalone gate |
|---|---|---|---|---|---|---|
| 1 | overlap image SIDE — small image on the RIGHT | `registration {toSlot: hero-media, edge: right, depthCols: 1, z: front}` | 5.15 | 1 | PASS | **PASS** (1 accent) |
| 2 | middle image MAX-WIDTH — colSpan 9 vs ~6 | `colSpan: 9, colStart: 3` on hero-media; overlap registration preserved | 5.15 | 1 | PASS | **PASS** (1 accent) |
| 3 | ASPECT RATIO — pano main media, portrait inset | `mediaAspect: pano` (placed, z mid) + `mediaAspect: portrait` on the inset | 5.15 | 1* | PASS | **PASS** (1 accent) |
| 4 | image COUNT — three overlapping images | 3 media slots, each with `registration` + z-order (`back`/`mid`/`front`), balanced left/right | 5.15 | 1 | PASS | **PASS** (1 accent) |
| 5 | BACKGROUND + CORNER — full-bleed photo behind heading + small corner image | `z: back` + `width: full-bleed` (scrimmed text-on-media) + `z: front` slot with `alignTo {corner: br}`, `counterweight: corner-accent` | 5.62 | 1 | PASS | **PASS** (1 accent) |

- \* V3 was regenerated once with a tightened directive: the first take drifted onto the
  background axis (`z:back` full-bleed) instead of keeping the original's PLACED media;
  the directive now pins `width:"media"`/`z:"mid"` and the retake landed in 1 attempt.
- Drift-band: all 5 anchored (score ≥ 2.5) AND visibly varied; `variation_delta` now
  counts placement changes (`placement changed (…)`, `slot count`) as observable deltas.
- Every axis that was "inexpressible" in the previous lane is now a first-class contract
  field — zero nearest-expressible substitutions this run.

## Assembled page + gates

- Order: `hero-original` ("Original (measured)", hoisted nav) → quiet label dividers
  (same caption-scale strip style) → v1…v5 → closing bookend. All six heroes
  `surface/inverse`, gold Melodrama 500 display headings, `#edd580` hover.
- **Retired shims** (now expressed through the contract): per-section centering
  (→ `alignment {anchor: centered}` on every variant), the "Original (measured)"
  `::before` label (→ baked into eyebrow copy), per-section hero copy (→ per-section
  `LAYOUT_COPY`), paper-toned ghost color on dark (→ surface-aware scaffold CSS). The
  remaining `gallery-comparison-shim` block is COLOR-ONLY (gold heading on each bookend +
  divider strip styling) — the two things a one-accent-per-page renderer can't express
  for a six-hero comparison artifact.
- Gate on the ASSEMBLED page (`onbrand_check.py --composition`): **FAIL single-accent**
  (accent elements = 6, one gold bookend per hero — expected for a comparison artifact
  and recorded honestly). All other checks green, including the new text-contrast
  (worst 7.19 vs floor 4.5) and decoration-salience.
- **Standalone gates: 6/6 PASS** (each hero as its own single-inverse-bookend page),
  including the new readability checks — the previous lane's v4 double-accent FAIL is
  gone (gap fix 3).

| standalone page | gate | accents | text-contrast |
|---|---|---|---|
| original | **PASS** | 1 | pass |
| v1-overlap-side | **PASS** | 1 | pass |
| v2-media-width | **PASS** | 1 | pass |
| v3-aspect | **PASS** | 1 | pass |
| v4-image-count | **PASS** | 1 | pass |
| v5-background-corner | **PASS** | 1 | pass (scrimmed background) |

## Regression matrix (`tools/phase0_regate.py` vs `/tmp/phase0-baseline`)

| page | base | now | note |
|---|---|---|---|
| full-editorial-luxury | PASS | PASS | |
| full-radical-editorial | PASS | PASS | |
| full-layout-patterns-v1 | PASS | PASS | |
| full-layout-patterns-v2 | PASS | PASS | |
| full-lp-v2-luxury | FAIL | PASS | improved (not a regression) |
| arm-a-structured | PASS | PASS | |
| arm-a-structured(comp) | PASS | PASS | hard invariants |
| hybrid-run-1…5 | PASS | PASS | hard invariants |
| hybrid-smoke | PASS | PASS | |
| showcase | PASS | PASS | |
| ablation arm-on/off/control | PASS | PASS | |
| page-anchored | — | FAIL single-accent | this lane, comparison artifact (expected); rebaselined |

No PASS→FAIL regression anywhere; the optional contract fields left every existing
composition byte-compatible at the layout level (only inert scaffold CSS was added).

## Outputs

- Page: `experiments/woodwave-hero-gallery/page-anchored/index.html`
- Studio lane (Studio :1500, HTTP 200 confirmed):
  **"WoodWave — anchored hero variants (live)"** →
  `http://localhost:1500/experiments/woodwave-hero-gallery/page-anchored/index.html`
- Full-page screenshot: `experiments/woodwave-hero-gallery/page-anchored/screenshot.png`
- Per-hero standalone screenshots:
  `experiments/woodwave-hero-gallery/anchored-shots/{original,v1-overlap-side,v2-media-width,v3-aspect,v4-image-count,v5-background-corner}-dark.png`
- Standalone gate pages + results: `experiments/woodwave-hero-gallery/standalone-gates/`
  (`results.json` + one gated page per hero)
- Per-variant artifacts: `experiments/woodwave-hero-gallery/gens-anchored/v{N}-*/`
  (`composition.json` · `index.html` · `onbrand-report.{md,json}` ·
  `generation-telemetry.json` · `hero-section.json`)
- Telemetry + drift scores: `experiments/woodwave-hero-gallery/anchored-results.json`

## Reproduce

```bash
# live (ANTHROPIC_API_KEY from .env.local; never hardcoded)
./venv/bin/python experiments/woodwave-hero-gallery/build_anchored_variants.py
# regenerate a single variant (e.g. 3)
./venv/bin/python experiments/woodwave-hero-gallery/build_anchored_variants.py --only 3
# re-stitch saved variants (no model call)
./venv/bin/python experiments/woodwave-hero-gallery/build_anchored_variants.py --assemble-only
# assembly wiring only (original-only page, no model call)
./venv/bin/python experiments/woodwave-hero-gallery/build_anchored_variants.py --offline-test
# regression regate (diff vs /tmp/phase0-baseline)
./venv/bin/python tools/phase0_regate.py
```
