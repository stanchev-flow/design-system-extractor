# Computed-CSS property-diff — remote

Per-property divergence of OUR composed replica vs the SOURCE computed styles + bound CSS rules, across the viewport ladder. Measurement only — no renderer / composer / author / SSIM-gate change.

- viewports: `1920, 1440, 960, 375` (primary 1440)
- replica: `runs/remote/brand/compose/replica/_cssdiff/index.html`
- source: `runs/remote/brand/evidence/joined-evidence.json`
- **19 divergences** — critical 1, high 9, medium 9, low 0

## Known acceptance divergences (recurring source-vs-replica gaps)

- [NOT FOUND] button `translateY(-1px)` hover-transform (source has none)
- [NOT FOUND] hero height px vs source `calc(100dvh - navheight)`
- [NOT FOUND] mega-nav panel missing background
- [FOUND] footer non-responsive grid vs source `@media` columns

## Heading-tier audit (authored vs CSS-variable truth)

- truth: `—` (method `—`)
- **0 heading-tier divergence(s)** — 0 means the authored ladder matches the source's declared font-size tokens

## Spacing-token audit (authored vs CSS-variable truth)

- truth: `—` (method `—`)
- **0 spacing-token divergence(s)** — 0 means the authored spacing tokens match the source's declared custom-property truth

## Radius-token audit (authored vs CSS-variable truth)

- truth: `—` (method `—`)
- **0 radius-token divergence(s)** — 0 means the authored radius tokens match the source's declared custom-property truth

## Color-token audit (authored vs CSS-variable truth)

- truth: `—` (method `—`)
- **0 color-token divergence(s)** — 0 means the authored color tokens match the source's declared custom-property truth

## Ranked divergences

| # | element | property | severity | cause | viewport | ours | source | rank |
|---|---|---|---|---|---|---|---|---|
| 1 | footer | `responsive-columns` | critical | missing-fact | all | no @media layout reflow | 7 @media reflow rules (@media only screen and (min-width:102… | 4.0 |
| 2 | heading-h1 | `font-size` | high | wrong-value | 1920 | 46px | 56px | 7.755 |
| 3 | heading-h1 | `font-size` | high | wrong-value | 960 | 46px | 28px | 7.755 |
| 4 | heading-h1 | `font-size` | high | wrong-value | 375 | 46px | 28px | 7.755 |
| 5 | heading-h2 | `font-size` | high | wrong-value | 1920 | 36px | 46px | 7.755 |
| 6 | heading-h2 | `font-size` | high | wrong-value | 960 | 36px | 22px | 7.755 |
| 7 | heading-h2 | `font-size` | high | wrong-value | 375 | 36px | 22px | 7.755 |
| 8 | footer | `max-width` | high | invented-default | 1440 | 1169.28px | none | 3.0 |
| 9 | hero | `background-color` | high | invented-default | 1440 | rgb(239, 240, 240) | rgba(0, 0, 0, 0) | 3.0 |
| 10 | nav | `background-color` | high | invented-default | 1440 | rgb(239, 240, 240) | rgba(0, 0, 0, 0) | 3.0 |
| 11 | heading-h2 | `line-height` | medium | wrong-value | 1920 | 46.8px | 55.2px | 6.0 |
| 12 | heading-h2 | `line-height` | medium | wrong-value | 1440 | 46.8px | 43.2px | 6.0 |
| 13 | heading-h2 | `line-height` | medium | wrong-value | 960 | 46.8px | 33px | 6.0 |
| 14 | heading-h2 | `line-height` | medium | wrong-value | 375 | 46.8px | 33px | 6.0 |
| 15 | heading-h1 | `line-height` | medium | wrong-value | 1920 | 55.2px | 67.2px | 5.17 |
| 16 | heading-h1 | `line-height` | medium | wrong-value | 960 | 55.2px | 42px | 5.17 |
| 17 | heading-h1 | `line-height` | medium | wrong-value | 375 | 55.2px | 42px | 5.17 |
| 18 | footer | `color` | medium | wrong-value | 1440 | rgb(20, 20, 21) | rgb(0, 0, 0) | 2.0 |
| 19 | nav | `color` | medium | wrong-value | 1440 | rgb(20, 20, 21) | rgb(0, 0, 0) | 2.0 |

## Component match table

| role | source | our selector | matched |
|---|---|---|---|
| hero | `section-00` | `#sec-0` | yes |
| nav | `chrome-header` | `#page-nav` | yes |
| footer | `chrome-footer` | `.c-footer` | yes |
| heading-h1 | `heading-h1` | `h1` | yes |
| heading-h2 | `heading-h2` | `h2` | yes |
| section-1 | `section-01` | `#sec-1` | yes |
| section-2 | `section-02` | `#sec-2` | yes |
| section-3 | `section-03` | `#sec-3` | yes |
| section-4 | `section-04` | `#sec-4` | yes |
| section-5 | `section-05` | `#sec-5` | yes |
| section-6 | `section-06` | `#sec-6` | yes |
| section-7 | `section-07` | `#sec-7` | yes |
| section-8 | `section-08` | `#sec-8` | yes |
| section-9 | `section-09` | `#sec-9` | yes |
