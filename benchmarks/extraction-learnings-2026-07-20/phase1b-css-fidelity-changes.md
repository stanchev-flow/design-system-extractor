# Phase 1b — Computed-CSS property-diff harness (measurement only)

> **Date:** 2026-07-21 · **Scope:** additive verification tool. NO renderer / composer /
> author / contract-projection / replica-SSIM-gate change. Builds on Phase 1's
> `runs/<brand>/brand/evidence/joined-evidence.json`.

## What shipped

- **`brand_pipeline/css_fidelity.py`** — a computed-CSS property-diff harness that
  auto-surfaces per-property divergence between OUR composed replica and the SOURCE,
  across the 1920/1440/960/375 viewport ladder, and emits a RANKED report.
- **`brand_pipeline/tests/test_css_fidelity.py`** — 25 tests (comparators, detectors,
  synthetic ours-vs-source diff incl. hover-transform / responsive-column-count /
  calc-height-vs-px, matching, ranking order, artifact shape, real-v3 source facts,
  real-v3 emitted-artifact acceptance).

## Design

- **Compose:** OUR source-order replica is composed through the REAL machinery
  (`compose_replica.build_replica_page`, imported unmodified) into an ISOLATED
  `compose/replica/_cssdiff/` dir so the SSIM gate's artifacts are never overwritten.
- **Measure (ours):** headless Chromium (JS off, `env -u PLAYWRIGHT_BROWSERS_PATH`,
  measure_computed's engine) reads a curated load-bearing property set per component at
  each viewport, plus each probe's bound CSS rules via an in-browser stylesheet scan
  (symmetric with the source's `cssRules`). Band background is resolved to the element
  that actually paints it (inner `.cs-section` / ancestor band), not the probed wrapper.
- **Source facts:** static values from `joined-evidence.json` `computedLadder`;
  behavior (hover transform, viewport-relative calc height, @media reflow, panel
  backgrounds) from bound `cssRules` — the channels a static snapshot cannot see.
- **Matching:** by ROLE, not class names (hero↔hero, nav↔chrome-header,
  footer↔chrome-footer, hero primary button family, headings, sections-by-index).
- **Diff:** per-property (colors with ≤6/channel tolerance + alpha-gap kept; lengths
  with ≤1px tolerance) → `{element, property, ours, source, viewport, severity,
  likelyCause: invented-default|missing-fact|wrong-value}`.
- **Rank:** severity tier first (a lone critical outranks a frequent medium), then
  `severityWeight × frequency` within the tier.
- **Emit:** `runs/<brand>/brand/compose/replica/css-diff.json` + `css-diff.md`.

## Verification (hubspot-v3, all four known divergences FOUND)

| known bug | element.property | ours | source | severity |
|---|---|---|---|---|
| (a) invented hover lift | `button-primary.transform:hover` | `translateY(-1px)` | `none` | high (invented-default) |
| (b) hero height mechanic | `hero.height-rule` | `739px (fixed px)` | `calc(100dvh - var(--global-nav-header-height))` | critical (missing-fact) |
| (c) mega-nav panel bg | `nav.panel-background` | no panel surface rendered | 5 panel bg rules | critical (missing-fact) |
| (d) footer responsiveness | `footer.responsive-columns` | no @media layout reflow | 16 @media reflow rules | critical (missing-fact) |

Composer `translateY(-1px)` hover (see `component_render.py:978`) is confirmed as an
invented-default: the source hero button declares no hover transform.

## Cross-check (severity tracks SSIM quality)

| brand | replica SSIM | divergences | critical |
|---|---|---|---|
| hubspot-v3 | 0.8955 | 27 | 3 |
| hubspot-v2 | 0.956 | 27 | 2 |
| remote | 0.951 | 19 | 1 |

Both v2 and remote run without error and emit their `css-diff.*` artifacts. The
footer non-responsive grid and hero fixed-height mechanics recur across brands — a
SYSTEMIC composer default the 1440 screenshot-SSIM gate is blind to (which is exactly
the gap this harness closes and hands to Phase 2/3).

## Commands

```
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python brand_pipeline/css_fidelity.py \
    runs/hubspot-v3/brand/brand.yaml         # + hubspot-v2, remote
./venv/bin/python -m pytest brand_pipeline/tests/test_css_fidelity.py   # 25 passed
```

## Scope / follow-up

- Zero edits to `render_*`, `compose_section/page`, `component_render`,
  `contract_projection`, `author_brand`, or the SSIM replica gate/outputs.
- Fixes are Phase 2 (responsive schema) / Phase 3 (purge un-grounded defaults),
  driven by this report — the harness only MEASURES.
