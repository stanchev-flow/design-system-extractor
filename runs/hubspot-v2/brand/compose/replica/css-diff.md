# Computed-CSS property-diff — hubspot-v2

Per-property divergence of OUR composed replica vs the SOURCE computed styles + bound CSS rules, across the viewport ladder. Measurement only — no renderer / composer / author / SSIM-gate change.

- viewports: `1920, 1440, 960, 375` (primary 1440)
- replica: `runs/hubspot-v2/brand/compose/replica/_cssdiff/index.html`
- source: `runs/hubspot-v2/brand/evidence/joined-evidence.json`
- **26 divergences** — critical 2, high 11, medium 9, low 4

## Known acceptance divergences (recurring source-vs-replica gaps)

- [FOUND] button `translateY(-1px)` hover-transform (source has none)
- [FOUND] hero height px vs source `calc(100dvh - navheight)`
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
| 1 | footer | `responsive-columns` | critical | missing-fact | all | no @media layout reflow | 16 @media reflow rules (@media(width < 900px); @media(width … | 4.0 |
| 2 | hero | `height-rule` | critical | missing-fact | all | 750px (fixed px) | calc(100dvh - var(--global-nav-header-height)) | 4.0 |
| 3 | heading-h2 | `font-size` | high | wrong-value | 1920 | 22px | 18px | 9.0 |
| 4 | heading-h2 | `font-size` | high | wrong-value | 1440 | 22px | 18px | 9.0 |
| 5 | heading-h2 | `font-size` | high | wrong-value | 960 | 22px | 18px | 9.0 |
| 6 | heading-h2 | `font-size` | high | wrong-value | 375 | 22px | 18px | 9.0 |
| 7 | button-primary | `display` | high | wrong-value | 1440 | flex | block | 3.0 |
| 8 | button-primary | `font-size` | high | wrong-value | 1440 | 16px | 18px | 3.0 |
| 9 | button-primary | `transform:hover` | high | invented-default | all | translateY(-1px) | none | 3.0 |
| 10 | footer | `max-width` | high | invented-default | 1440 | 1080px | none | 3.0 |
| 11 | heading-h1 | `font-size` | high | wrong-value | 375 | 80px | 48px | 3.0 |
| 12 | hero | `background-color` | high | wrong-value | 1440 | rgb(85, 69, 62) | rgb(4, 39, 41) | 3.0 |
| 13 | section-4 | `background-color` | high | wrong-value | 1440 | rgb(252, 198, 177) | rgb(252, 222, 210) | 3.0 |
| 14 | heading-h2 | `line-height` | medium | wrong-value | 1920 | 31.9px | 28px | 6.0 |
| 15 | heading-h2 | `line-height` | medium | wrong-value | 1440 | 31.9px | 28px | 6.0 |
| 16 | heading-h2 | `line-height` | medium | wrong-value | 960 | 31.9px | 28px | 6.0 |
| 17 | heading-h2 | `line-height` | medium | wrong-value | 375 | 31.9px | 28px | 6.0 |
| 18 | button-primary | `line-height` | medium | missing-fact | 1440 | normal | 32px | 2.0 |
| 19 | button-primary | `padding` | medium | wrong-value | 1440 | 12px 24px | 16px 40px | 2.0 |
| 20 | button-primary | `width` | medium | wrong-value | 1440 | 140.422px | 183.469px | 2.0 |
| 21 | footer | `padding` | medium | wrong-value | 1440 | 0px | 48px 32px | 2.0 |
| 22 | heading-h1 | `line-height` | medium | wrong-value | 375 | 95.2px | 55px | 2.0 |
| 23 | heading-h1 | `font-family` | low | wrong-value | 1920 | "HubSpot Serif", "Source Serif 4", serif | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | 3.0 |
| 24 | heading-h1 | `font-family` | low | wrong-value | 1440 | "HubSpot Serif", "Source Serif 4", serif | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | 3.0 |
| 25 | heading-h1 | `font-family` | low | wrong-value | 960 | "HubSpot Serif", "Source Serif 4", serif | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | 3.0 |
| 26 | heading-h1 | `font-family` | low | wrong-value | 375 | "HubSpot Serif", "Source Serif 4", serif | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | 3.0 |

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
