# Remote — tagged asset inventory

Machine-readable twin: `assets-tagged.json` (schemaVersion 2, referenced by
`brand.yaml → indexes.assetsTagged`). 44 curated assets from the local
"Save Page As, Complete" capture. Filenames relative to `assets/`.

Curation notes:

- **Customer logos were NOT files** — remote.com inlines them as `<svg>` in the DOM
  (`.social-proof-item`). Extracted with `experiments/remote-e2e/curate_assets.py`
  into `assets/*.svg` (flat root — the composer inventories the assets/ root only), identified visually (logo sheet), renamed, and tagged
  **`logo-wall-logo`** so the logo-strip device can bind them. All are monochrome
  ink vectors (fill `#141415` family) sized for a ~40px-tall marquee row.
- The brand wordmark (mark + word) was also inline SVG → `remote-wordmark.svg`
  (94×30 viewBox), tagged `logo`, consumed by `navbar.logo.src`.
- webp names were sanitized from CDN hashes to descriptive names.

## logo-wall-logo (12) — for the logo-strip device

| file | dims (viewBox) | brand |
|---|---|---|
| logo-anthropic.svg | 201×24 | Anthropic |
| logo-box.svg | 88×48 | Box |
| logo-byd.svg | 96×24 | BYD |
| logo-datadog.svg | 137×36 | Datadog |
| logo-gitlab.svg | 141×32 | GitLab |
| logo-heineken.svg | 154×28 | Heineken |
| logo-kfc.svg | 47×48 | KFC |
| logo-lovable.svg | 129×28 | Lovable |
| logo-mercury.svg | 145×32 | Mercury |
| logo-miro.svg | 101×36 | Miro |
| logo-mizuho.svg | 138×28 | Mizuho |
| logo-vercel.svg | 120×28 | Vercel |

## logo (1)

- `remote-wordmark.svg` — 94×30, nav + footer wordmark (ink).

## integration-logo (4) — partner row (colored, 64px tier)

- `logo-bamboohr.webp` (238×64) · `logo-gusto.webp` (170×64) ·
  `logo-personio.webp` (236×64) · `logo-workday-certified.webp` (147×88)

## award-badge (6) + rating-badge (3) — proof strip

- G2 badges (~150px): `badge-g2-gep-leader`, `badge-g2-payroll-leader`,
  `badge-g2-top100-fastest-growing`, `badge-g2-top100-global-sellers`,
  `badge-g2-top100-hr`, `badge-g2-top50-hr` (all .webp)
- Rating chips: `rating-g2.webp`, `rating-trustpilot.webp`, `rating-capterra.webp`

## testimonial-avatar (4) — circle-cropped

- `avatar-erik-sveen.webp`, `avatar-luke-mckinlay.webp`,
  `avatar-maria-shkaruppa.webp`, `avatar-marisol-jimenez.webp`

## hero-illustration (1) / background-art (1)

- `hero-globe-illustration.webp` (1188×880) — hero right-column media.
- `bg-noise-grey-green-blue-top.webp` (4560×2320, avg #dae2e8) — the pastel
  noise-gradient art surface (hero inset panel + closing CTA).

## product-graphic (6) — card/panel media (deep-navy backdrops)

- `card-api-first.webp`, `card-integrations.webp`, `card-mcp-agents.webp`,
  `card-customer-story-culture.webp`, `card-customer-story-reverse-tech.webp`,
  `panel-infrastructure-ui-snippet.webp`

## feature-icon (6)

- Product-family icons: `icon-eor`, `icon-global-payroll`,
  `icon-contractor-management`, `icon-contractor-of-record`, `icon-peo`
  (+ `icon-check-star-stamp` decorative stamp).
