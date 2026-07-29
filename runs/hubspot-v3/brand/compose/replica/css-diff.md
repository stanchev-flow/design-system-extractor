# Computed-CSS property-diff — hubspot-v3

Per-property divergence of OUR composed replica vs the SOURCE computed styles + bound CSS rules, across the viewport ladder. Measurement only — no renderer / composer / author / SSIM-gate change.

- viewports: `1920, 1440, 960, 375` (primary 1440)
- replica: `runs/hubspot-v3/brand/compose/replica/_cssdiff/index.html`
- source: `runs/hubspot-v3/brand/evidence/joined-evidence.json`
- **21 divergences** — critical 0, high 6, medium 11, low 4

## Known acceptance divergences (recurring source-vs-replica gaps)

- [NOT FOUND] button `translateY(-1px)` hover-transform (source has none)
- [NOT FOUND] hero height px vs source `calc(100dvh - navheight)`
- [NOT FOUND] mega-nav panel missing background
- [NOT FOUND] footer non-responsive grid vs source `@media` columns

## Heading-tier audit (authored vs CSS-variable truth)

- truth: `runs/hubspot-v3/brand/evidence/type-scale.json` (method `css-var`)
- **0 heading-tier divergence(s)** — 0 means the authored ladder matches the source's declared font-size tokens

## Spacing-token audit (authored vs CSS-variable truth)

- truth: `runs/hubspot-v3/brand/evidence/spacing-scale.json` (method `css-var+computed-cluster`)
- **0 spacing-token divergence(s)** — 0 means the authored spacing tokens match the source's declared custom-property truth

## Radius-token audit (authored vs CSS-variable truth)

- truth: `runs/hubspot-v3/brand/evidence/radius-scale.json` (method `css-var`)
- **0 radius-token divergence(s)** — 0 means the authored radius tokens match the source's declared custom-property truth

## Color-token audit (authored vs CSS-variable truth)

- truth: `runs/hubspot-v3/brand/evidence/color-roles.json` (method `css-var`)
- **0 color-token divergence(s)** — 0 means the authored color tokens match the source's declared custom-property truth

## Ranked divergences

| # | element | property | severity | cause | viewport | ours | source | rank |
|---|---|---|---|---|---|---|---|---|
| 1 | heading-h2 | `font-size` | high | wrong-value | 1920 | 40px | 18px | 9.0 |
| 2 | heading-h2 | `font-size` | high | wrong-value | 1440 | 40px | 18px | 9.0 |
| 3 | heading-h2 | `font-size` | high | wrong-value | 960 | 40px | 18px | 9.0 |
| 4 | heading-h2 | `font-size` | high | wrong-value | 375 | 40px | 18px | 9.0 |
| 5 | button-primary | `display` | high | wrong-value | 1440 | flex | block | 3.0 |
| 6 | button-primary | `font-size` | high | wrong-value | 1440 | 16px | 18px | 3.0 |
| 7 | heading-h2 | `line-height` | medium | wrong-value | 1920 | 44px | 28px | 6.0 |
| 8 | heading-h2 | `line-height` | medium | wrong-value | 1440 | 44px | 28px | 6.0 |
| 9 | heading-h2 | `line-height` | medium | wrong-value | 960 | 44px | 28px | 6.0 |
| 10 | heading-h2 | `line-height` | medium | wrong-value | 375 | 44px | 28px | 6.0 |
| 11 | heading-h1 | `line-height` | medium | wrong-value | 1920 | 92px | 95px | 5.17 |
| 12 | heading-h1 | `line-height` | medium | wrong-value | 1440 | 92px | 95px | 5.17 |
| 13 | heading-h1 | `line-height` | medium | wrong-value | 960 | 92px | 95px | 5.17 |
| 14 | button-primary | `line-height` | medium | wrong-value | 1440 | 28px | 32px | 2.0 |
| 15 | button-primary | `padding` | medium | wrong-value | 1440 | 12px 24px | 16px 40px | 2.0 |
| 16 | button-primary | `width` | medium | wrong-value | 1440 | 140.422px | 183.469px | 2.0 |
| 17 | footer | `padding` | medium | wrong-value | 1440 | 0px | 48px 32px | 2.0 |
| 18 | heading-h2 | `font-family` | low | wrong-value | 1920 | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | "HubSpot Sans", sans-serif | 3.0 |
| 19 | heading-h2 | `font-family` | low | wrong-value | 1440 | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | "HubSpot Sans", sans-serif | 3.0 |
| 20 | heading-h2 | `font-family` | low | wrong-value | 960 | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | "HubSpot Sans", sans-serif | 3.0 |
| 21 | heading-h2 | `font-family` | low | wrong-value | 375 | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | "HubSpot Sans", sans-serif | 3.0 |

## Component match table

| role | source | our selector | matched |
|---|---|---|---|
| hero | `section-00` | `#sec-0` | yes |
| nav | `chrome-header` | `#page-nav` | yes |
| footer | `chrome-footer` | `.c-footer` | yes |
| button-primary | `action-40` | `#sec-0 .c-button:not(.c-button--navcta)` | yes |
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
