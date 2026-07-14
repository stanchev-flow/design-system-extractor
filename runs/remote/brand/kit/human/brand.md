# brand.md - remote.com   <!-- rendered from brand.yaml v1.1 by render_brand_md.py; DO NOT EDIT -->

> Generated projection. Edit `brand.yaml` (canonical) and re-render; never hand-edit this file.

## 1. Brand snapshot
Remote is a light, systematic SaaS marketing system on a cool gray canvas (#eff0f0) led by a single vivid blue (#0564ff — the site's own sea-blue-500 token). Every heading tier is Bossa (a geometric grotesque) at weight 400, sentence case; hierarchy comes from size, not weight. Inter carries body, UI, buttons, and the footer. All CTAs are fully-rounded 48px-tall pills (40px radius token): blue filled primary, outlined secondary in deep blue (#003284) that FILLS blue on hover, near-black neutral pill for chrome (nav CTA), and blue arrow text-links. Eyebrows are uppercase tracked microlabels color-coded by the section's theme scope (sea-blue #0047bc-family, red-brand crimson #a52d44, neutral gray #595b5f). Content sits in pure-white rounded cards that are FLAT at idle and gain a soft shadow + tint only on hover. Dark surfaces never appear as section bands: deep navy (#00235c, the sea-blue-800 accent step) backs media wells INSIDE white cards, and deep maroon (#511621, red-brand-800) inverts the active item of the feature accordion. The hero sits on an inset 10px-rounded panel painted with a pastel grey-green-blue noise-gradient; the closing CTA repeats the gradient as a full-bleed band; text on both stays dark ink. The footer is LIGHT (#f6f7f8): an 8-group link directory in 6 visual columns, ink links that soften + underline on hover, circular social icons, app badges.

## 2. Surface grammar
7 surface roles:
- `surface/primary` - bg `#eff0f0`, intent `cool gray page canvas (bg-surface-01)`, text `text/on-primary`
- `surface/panel` - bg `#ffffff`, intent `white card/panel floating on the canvas (10px radius = --zora-radius-x3, flat idle, hover shadow+tint)`, text `text/on-primary`
- `surface/raised` - bg `#f6f7f8`, intent `raised light band (neutral-50: footer, nav-open bg, hover tints)`, text `text/on-primary`
- `surface/inverse` - bg `#00235c`, intent `deep navy (sea-blue-800 accent step) — on the source page an INSET media/panel backdrop inside white cards, not a page band`, text `text/on-inverse`, accent `accent/highlight-on-inverse`
- `surface/inverse-strong` - bg `#00235c`, intent `ALIAS — single dark family; strong == inverse`, text `text/on-inverse`, accent `accent/highlight-on-inverse`
- `surface/accent` - bg `#511621`, intent `deep maroon inset emphasis panel (red-brand-800) — the ACTIVE feature-list item inverts to this (generic: deep-accent inset card; white ink; hover #742030)`, text `text/on-inverse`, accent `accent/warm-wash`
- `surface/hero-noise` - bg `#dae2e8`, intent `pastel noise-gradient ART surface (asset bg-noise-top-2x.webp; grey→green→blue gradient; #dae2e8 = sampled average); dark ink text on it. Hero: inset 10px panel (x3, computed fid13); closing CTA: full-bleed band`, text `text/on-primary`

Page rhythm: surface/hero-noise -> surface/primary -> surface/primary -> surface/primary -> surface/primary -> surface/primary -> surface/primary -> surface/primary -> surface/primary -> surface/hero-noise -> surface/raised.
Section transitions are **soft**.
Nesting: `surface/panel` allowed only inside `surface/primary`, `surface/raised`.
Nesting: `surface/inverse` allowed only inside `surface/panel`, `surface/primary`.
Nesting: `surface/accent` allowed only inside `surface/primary`, `surface/panel`.

## 3. Color tokens (semantic role + value)

| token | value | role |
|---|---|---|
| `ink/primary` | `#141415` | heading + nav-link + footer-link ink (neutral-900; h1–h6, nav triggers, footer links) |
| `ink/body` | `#383a3d` | body copy default (neutral-700 = --zora-text-secondary; measured p{color} rgb(56,58,61)) |
| `ink/secondary` | `#595b5f` | quieter ink (neutral-600): gray eyebrow family, footer group headings (--zora-footer-header-text), footer-link hover |
| `ink/muted` | `#777a7e` | neutral-500: disabled-button label, muted labels on accent parents |
| `ink/faint` | `#b3b5b7` | neutral-400: disabled text, faint hairlines |
| `neutral/canvas` | `#eff0f0` | page canvas (--zora-bg-surface-01 = neutral-100; body{background} measured rgb(239,240,240)) |
| `neutral/raised` | `#f6f7f8` | raised light band (neutral-50): footer bg (--zora-footer-bg), nav-open bg, card hover tint, accordion idle hover |
| `neutral/card` | `#ffffff` | card surface (--zora-bg-surface-02 = neutral-white): white content cards, nav hover pill, testimonial slides |
| `action/primary` | `#0564ff` | primary CTA fill (sea-blue-500 = themed --zora-btn-bg), text links (--zora-link), blue eyebrow family |
| `action/primary-hover` | `#0047bc` | primary CTA hover fill (sea-blue-600 = themed --zora-btn-bg-hover); link hover color |
| `action/primary-active` | `#003284` | primary CTA pressed fill (sea-blue-700 = themed --zora-btn-bg-active) |
| `action/primary-disabled` | `#ccdfff` | primary CTA disabled fill (sea-blue-100 = themed --zora-btn-bg-disabled; label #67a1ff sea-blue-300) |
| `action/focus-ring` | `#9bc1ff` | focus-visible outline (sea-blue-200 = themed --zora-btn-border-focused; 2px solid, 2px offset) |
| `action/secondary-ink` | `#003284` | outlined-pill label + border (sea-blue-700 = themed --zora-btn-border-secondary / --zora-btn-text-dark; measured 'Sign up' color rgb(0,50,132)) |
| `action/secondary-hover-fill` | `#0564ff` | outlined-pill hover FILLS with sea-blue-500 (themed --zora-btn-bg-hover-secondary) and the label goes light — outline melts (box-shadow inset -> transparent) |
| `action/neutral` | `#232325` | neutral filled pill (neutral-800 = :root --zora-btn-bg; the nav 'Book demo') |
| `action/neutral-hover` | `#595b5f` | neutral pill hover fill (neutral-600 = :root --zora-btn-bg-hover) |
| `action/neutral-active` | `#383a3d` | neutral pill pressed fill (neutral-700 = :root --zora-btn-bg-active) |
| `surface/deep-navy` | `#00235c` | deep navy media-well backdrop inside white cards (sea-blue-800 — the themed --zora-bg-accent step); vision ~#0a1f56 |
| `surface/deep-accent` | `#511621` | deep maroon inset panel (red-brand-800 — the red theme's --zora-bg-accent): ACTIVE feature-accordion item, white ink on it |
| `surface/deep-accent-hover` | `#742030` | deep maroon hover fill (red-brand-700 — --zora-acc-bg-active-hover under the red theme) |
| `accent/warm-wash` | `#fceef1` | soft pink wash (red-brand-50): idle accordion-item hover in the red-themed section |
| `accent/crimson` | `#a52d44` | crimson eyebrow family (red-brand-600 = red-themed --zora-label); vision ~#a01f38 |
| `accent/eyebrow-blue-deep` | `#0047bc` | blue eyebrow family (sea-blue-600 = sea-blue-themed --zora-label); vision reads #1d5ce0-ish |
| `accent/periwinkle` | `#9bc1ff` | muted blue-on-navy family (sea-blue-200): links/accents on the deep-navy media wells |
| `accent/pale-blue-chip` | `#ccdfff` | pale blue chip fill (sea-blue-100): icon chips, badge tints on light panels |
| `text/link` | `#0564ff` | text links are BLUE (--zora-link = sea-blue-500); idle clean, hover underlines + darkens |
| `text/link-hover` | `#0047bc` | link hover color (--zora-link-hover = sea-blue-600) |
| `text/link-on-inverse` | `#9bc1ff` | link color on accent/dark surfaces (--zora-link-on-bg-accent = sea-blue-200) |
| `text/link-hover-on-inverse` | `#ccdfff` | link hover on dark surfaces (--zora-link-hover-on-bg-accent = sea-blue-100) |
| `overlay/hover-wash` | `#e7e8e9` | hover wash on light surfaces (neutral-200 = --zora-tab-nav-bg-hover: nav trigger pills, language switcher) |
| `overlay/hover-wash-white` | `#ffffff` | nav dropdown item hover wash (--zora-nav-item-bg-hover = neutral-white) |
| `border/input` | `#232325` | form input active border (--zora-input-border-active = neutral-800) |
| `state/disabled-fill` | `#d2d3d5` | neutral disabled fill (neutral-300 = :root --zora-btn-bg-disabled) |
| `state/error` | `#d3433c` | form error border (--zora-peach-500 / --zora-border-alert) |
| `surface/art-pastel` | `#dae2e8` | pastel noise-gradient art surface's average color (sampled from the bg-noise art asset) — palette-legal stand-in wherever the art itself cannot ship |
| `surface/primary` | `#eff0f0` | ALIAS of neutral/canvas — canonical page-canvas role |
| `surface/panel` | `#ffffff` | ALIAS of neutral/card — canonical panel/card role (white cards ON the gray canvas) |
| `surface/inverse` | `#00235c` | ALIAS of surface/deep-navy — canonical dark role. NOTE: on the real page this navy is an INSET surface (media wells inside cards), never a full-width band |
| `surface/inverse-strong` | `#00235c` | ALIAS — Remote has ONE dark family; strong == inverse (#00235c) |
| `accent/highlight` | `#0564ff` | ALIAS of action/primary — canonical accent role (vivid blue; legal on light surfaces: buttons, links, eyebrows) |
| `accent/highlight-on-inverse` | `#9bc1ff` | accent variant ON deep-navy surfaces (periwinkle, sea-blue-200); full-strength blue is reserved for light surfaces |
| `text/on-primary` | `#141415` | ALIAS of ink/primary — canonical ink-on-light role (headings; body uses the muted role) |
| `text/on-primary-muted` | `#383a3d` | ALIAS of ink/body — canonical muted-ink-on-light role (the real body ink, --zora-text-secondary) |
| `text/on-inverse` | `#ffffff` | canonical ink-on-dark role (--zora-text-on-bg-accent): white text on deep-navy/deep-maroon panels |
| `text/on-inverse-muted` | `#9bc1ff` | canonical muted-ink-on-dark role — periwinkle family on navy (links/labels on accent surfaces) |
| `text/on-accent` | `#ffffff` | label color on the blue primary fill (--zora-btn-text-light) |
| `text/ghost-on-primary` | `#e7e8e9` | canonical ghost-on-light role — Remote has NO ghost-type device; bound to the measured light hover wash so any fallback stays on-palette |
| `border/hairline-on-primary` | `rgba(179,181,183,0.4)` | canonical hairline-on-light role — neutral-400 at 40% (footer divider family) |
| `border/hairline-on-inverse` | `rgba(255,255,255,0.4)` | hairline-on-dark role — derived: white at the light-hairline alpha; no solid hairline is measured on navy |

## 4. Typography roles

| role | family | size (base) | line-height | weight | case |
|---|---|---|---|---|---|
| display-hero | Bossa | 2.875rem | 1.2em | 400 | sentence |
| h1 | Bossa | 2.875rem | 1.2em | 400 | sentence |
| h2 | Bossa | 2.25rem | 1.2em | 400 | sentence |
| h3 | Bossa | 1.75rem | 1.2em | 400 | sentence |
| h4 | Bossa | 1.375rem | 1.2em | 400 | sentence |
| h5 | Bossa | 1.25rem | 1.5em | 400 | sentence |
| h6 | Bossa | 1.125rem | 1.5em | 400 | sentence |
| eyebrow | Bossa | 0.875rem | 1.5em | 400 | uppercase |
| body | Inter | 1.125rem | 1.5em | 400 | sentence |
| body-sm | Inter | 1rem | 1.5em | 400 | sentence |
| control-text | Inter | 1.125rem | 1.5em | 500 | none |
| headingEmphasis |  | Nonerem |  | - |  |

## 5. Spacing system
- `section-padding-light`: 3rem - vertical section rhythm on the light canvas (--zora-section-*-margin ladders resolve x6–x9 = 32–80px by breakpoint)
- `section-y-lg`: 5rem - spacious section tier (x9 = 80px; grounding reads 80–130px on hero/closing bands)
- `section-y-xl`: 7rem - closing CTA breathing tier (vision: ~130px top pad on the gradient band)
- `module-gap-editorial`: 5rem - ALIAS of section-y-lg — preview/composer module rhythm
- `eyebrow-to-heading`: 0.75rem - label→headline gap — --zora-st-label-headline-spacing (x2→x3 swap at 1024: 8px→12px)
- `heading-to-body`: 1rem - headline→description gap — --zora-st-headline-description-spacing (x3→x4 swap at 1024: 12px→16px)
- `body-to-cta`: 2rem - description→button gap — --zora-st-description-button-spacing (x5→x6 swap at 1024: 24px→32px)
- `block-to-block`: 4rem - content-block row rhythm — --zora-st-row-gap-spacing (x7→x8 swap at 1024: 48px→64px): header→content, content→content, content→ctasAfterContent all ride this ONE rung (.base-module content:not(:first-child) / ctasAfterContent margin-top)
- `column-to-column`: 3rem - split-row column gutter — --zora-st-split-column-gap (0 below 1024 where columns stack/ride the description-button gap; x6=32px @1024, x7=48px @1440, x8=64px @1920; .base-module splitTop/splitRow gap)
- `body-measure`: 35.6875rem - description column measure — --zora-st-description-width ladder (20.4375/25/30.0625 rem below; 35.6875rem=571px @1440; 47.75rem @1920). 992–1023 carries the <1024 register (known projection seam)
- `header-measure`: 45rem - bounded header-stack measure — --zora-st-width @1440 (45rem=720px; 60.1875rem @1920; .base-header boundedHeader max-width, applied ≥1024 only — below, headers run the full column)
- `band-inset`: 7rem - structured-text band inset ladder — --zora-st-paddings (--zora-padding-x1=1rem below 1024, x5=4rem @1024, x8=7rem @1440+); defined at :root every tier but NO consuming rule found in the mined corpus — captured for ladder completeness, composers do not consume it
- `panel-padding`: 2rem - card/panel inset (--zora-panel-padding x6–x9 ladder; testimonial cards ~40px, hero panel up to 80px @xl)
- `grid-gap`: 2rem - card grid gap (grounding: 32–33px card gaps; --zora-s-p-logos-container-column-gap x6–x8)
- `stack-md`: 1rem - ALIAS of heading-to-body — intra-stack gap the composers consume (--zora-st-headline-description-spacing x3–x4)
- `stack-lg`: 3rem - content-to-actions gap: the HERO badge/button register (x6–x7); the module-level rung is body-to-cta (x5–x6)
- `button-inset`: 0rem 1.5rem - pill inset: fixed 48px height (--zora-spacing-x7) + 0 24px padding (x5) measured on every .button
- `container-max`: 76rem - content max-width 1216px measured (nav/footer contentMaxWidth); the outer layout container is fluid ~81vw below 1920 and caps at 1560px @1920 (tier containerFacts: max 100%/1560px, used 1168px @1440, 1560px @1920)
- `container-span`: min(81.2cqw, 97.5rem) - the outer layout container LAW as one CSS expression (tier containerFacts: used 1168px @1440 = 81.1vw, capped 1560px @1920 = 97.5rem, ~9.4vw side margins each tier; the 960 tier runs tighter 5vw margins — the fluid term under-spans there, accepted). Sections/bands center this span page-wide (--content-measure)
- `badge-tier`: 6.25rem - proof badge tier (~100px awards; partner logos ride --zora-s-p-logos-big-height x8=64px)
- `radius-global`: 0.625rem - ALIAS of radius/card — the working surface rounding (the source's own --zora-radius-x3 = 10px; fid13 corrected the 12px vision estimate)
- `field-to-field`: 1rem - form field-grid rhythm — .hsfc-Row column-gap/row-gap (x3=12px base → x4=16px ≥768; the form's field rows and columns share one rung)
- `field-label-gap`: 0.25rem - label→control seam — form-module label margin-bottom (x1=4px flat, every tier; the field description rides the same x1 rung)
- `form-stack`: 2rem - form module internal stack — --zora-form-spacing (x4=16px base → x5=24px ≥768 → x6=32px ≥1440; .formCard/.form flex-column gap between header, field grid, consent, actions)
- `list-item-gap`: 1rem - disclosure-list stride — --accordion-item-gap (x3=12px base → x4=16px ≥768; the seam between accordion/FAQ item boxes)
- `list-item-inset`: 1.5rem - disclosure item inset — --accordion-item-padding (x4=16px base → x5=24px ≥1440; the trigger row's own padding inside the item box)
- `mark-to-quote`: 1.5rem - quote-card mark→quote seam — testimonial card root gap (x5=24px ≥768; the logo mark to quote-body seam inside the card column)
- `quote-to-attribution`: 4rem - quote-card body→attribution seam — testimonial card frame gap (x6=32px base → x7=48px ≥1024 → x8=64px ≥1440; quote body to author row)
- `strip-gap`: 4rem - logo/badge strip inter-mark gap — --zora-s-p-logos-container-column-gap (x6=32px base → x7=48px ≥768 → x8=64px ≥1440)

## 6. Layout grammar
- **Nav** (navbar, base (Primary)): Remote wordmark.
- **Split** (hero, base (Primary)): display heading (Bossa 400 sentence).
- **Stack** (logo-wall, base (Primary)): uppercase microlabel ('GLOBAL COMPANIES GROW WITH REMOTE').
- **Split** (feature-accordion, base (Primary)): crimson uppercase label ('HOW WE DO IT').
- **Split** (infra-panel, base (Primary)): stacked product-UI proof cards.
- **Stack** (banner-cta, base (Primary)): centered h2 (question form).
- **Cards** (workflow-cards, base (Primary)): section header stack (eyebrow + heading).
- **Stack** (partner-logos, base (Primary)): centered header stack ('THE GLOBAL PAYROLL BACKBONE').
- **Cards** (testimonials, base (Primary)): centered header ('A word from our customers').
- **Stack** (badge-strip, base (Primary)): centered heading.
- **Stack** (closing-cta, base (Primary)): centered h2.
- **Grid** (footer, Secondary): 8 grouped link columns (6 visual).

## 7. Slot mapping (slot -> primitive/block contract)
### navbar

| slot | role | contract |
|---|---|---|

### hero

| slot | role | contract |
|---|---|---|

### logo-wall

| slot | role | contract |
|---|---|---|

### feature-accordion

| slot | role | contract |
|---|---|---|

### infra-panel

| slot | role | contract |
|---|---|---|

### banner-cta

| slot | role | contract |
|---|---|---|

### workflow-cards

| slot | role | contract |
|---|---|---|

### partner-logos

| slot | role | contract |
|---|---|---|

### testimonials

| slot | role | contract |
|---|---|---|

### badge-strip

| slot | role | contract |
|---|---|---|

### closing-cta

| slot | role | contract |
|---|---|---|

### footer

| slot | role | contract |
|---|---|---|

## 8. Composition mechanics
- **inset-panel-hero**: The hero sits on an INSET rounded panel (10px = --zora-radius-x3, the brand's ONE surface radius) painted with the brand's pastel noise-gradient art; text on the art stays dark ink (no scrim, no blur, no white text). The closing CTA repeats the gradient as a full-bleed band.
- **pill-cta-system**: Every button is a fully-rounded pill (40px radius token, 48px fixed height, 0 24px inset, Inter 500 18px): blue filled primary, deep-blue outlined secondary that FILLS blue on hover, near-black neutral pill for chrome; hover swaps the FILL, never the shape.
- **white-cards-flat-idle**: Content cards are pure white, 10px-rounded (--zora-radius-x3), borderless and FLAT at idle; elevation (0 12px 24px rgba(0,0,0,0.08)) plus a #f6f7f8 tint appears only on hover. Media wells inside cards are SQUARE — the card's own radius clips the visible top corners.
- **dark-is-inset**: Dark surfaces are INSET, never page bands: deep navy (#00235c family) backs media wells inside white cards; the page canvas itself stays light end-to-end.
- **deep-accent-active-item**: In interactive lists, the ACTIVE item inverts to a deep-accent inset card (deep maroon #511621 family, white ink, circle-arrow affordance); idle items are hairline rows; hovered items take a warm tint wash (#fceef1). Generic pattern: high-contrast inset emphasis, one item at a time.
- **single-weight-display**: The display face runs at weight 400 on EVERY tier; hierarchy is size-only. Bold appears only as inline emphasis inside body copy.
- **theme-scoped-eyebrows**: Eyebrows are uppercase 14–15px 0.05em-tracked microlabels whose COLOR comes from the section's theme scope: blue family (#0047bc/#0564ff) for product/platform sections, crimson (#a52d44) for the deep-accent feature family, gray (#595b5f) for proof strips. Generic mechanic: one label token, re-scoped per section family.
- **logo-strips-real-vectors**: Customer logo walls render REAL vector logos in monochrome ink (~40px tall) in a spaced row (marquee-capable); partner strips render colored logo images at the bigger tier; award badges ride a shield row. Logos are never text names.
- **light-footer-directory**: The footer is LIGHT (#f6f7f8): a multi-column 14px Inter directory; group headings gray (#595b5f), links ink (#141415 w400) that soften to gray + underline on hover; legal row muted; circular social icons; app badges.

## 9. Do
- Make every CTA a fully-rounded 48px pill: blue filled primary, outlined secondary, near-black neutral for chrome.
- Set all headings in the display face at weight 400, sentence case; scale size, never weight.
- Float white rounded flat cards on the gray canvas; reveal shadow + tint on hover only.
- Deploy deep navy as an inset backdrop (card media wells, inner panels) with white ink and periwinkle accents.
- Open sections with uppercase tracked eyebrows color-coded to the section family (blue/crimson/gray).
- Bookend the page with the pastel noise-gradient art (hero inset panel, closing full-bleed band), dark ink on the art.
- Render logo walls from the extracted monochrome vector logos in a spaced row.

## 10. Avoid
- Avoid full-width dark section bands; the canvas run is light end-to-end — darkness belongs INSIDE cards/panels.
- No bold/heavy display type; the display face never exceeds weight 400 at heading tiers.
- No rectangular or lightly-rounded buttons; CTAs are full pills.
- No resting drop-shadows on cards; elevation is a hover behavior.
- No photographic hero backgrounds or scrims; hero media is illustration/product-UI art on the noise panel.
- Do not flood surfaces with the action blue; large fields stay gray/white/pastel — blue is for CTAs, links, eyebrows, and small chips.

## 11. Never-do
- Never render the primary CTA as a typographic link; it is always a filled blue pill.
- Never zero out radius; the system is rounded (cards 12–14px, panels ~20px, media 10px, pills 40px).
- Never set headings in all-caps; headings are sentence-case — uppercase belongs to the eyebrow register only.

## 12. Primitive & block rules

**Primitives** (8 extracted / 0 designed)
- `heading` (extracted: hero, accordion-features, banner-cta; use: always) - every heading tier is Bossa weight 400 sentence-case — hierarchy by SIZE only, never weight or caps
- `eyebrow` (extracted: accordion-features, infra-panel, workflow-cards, logo-wall; use: always) - uppercase microlabel, 0.05em tracked, color set by the section's theme scope (sea-blue / red-brand crimson / neutral gray) — never body-gray-only
- `paragraph` (extracted: hero, infra-panel, testimonials; use: always) - Inter 400, 1.5 line-height, muted ink (#383a3d) on light surfaces
- `button` (extracted: hero, banner-cta, closing-cta, navbar; use: always; variant: filled-primary) - PRIMARY actions are FILLED blue pills with white labels — never typographic; secondary is a deep-blue outlined pill that FILLS blue on hover; neutral near-black pill for chrome CTAs; all pills 48px tall, 40px radius, content-hugging
- `link` (extracted: workflow-cards, testimonials; use: text-links-only) - text links are BLUE (#0564ff), idle-clean, hover darkens (#0047bc); reserved for tertiary 'Learn more' / 'Read customer story' actions with a trailing arrow
- `image` (extracted: hero, workflow-cards, testimonials; use: always) - illustration/product-UI art on deep-navy or noise-gradient backdrops; media wells rounded 10px; photography only as circle-cropped avatars
- `logo` (extracted: logo-wall; use: always) - customer logos are monochrome ink vectors on the light canvas, ~40px tall, single spaced row (marquee-capable)
- `input` (extracted: popup-forms; use: forms) - boxed light fields, active border #232325 (--zora-input-border-active), 4px radius; submit is a filled pill

**Blocks** (16 extracted / 0 designed)
- `header` (extracted: hero, banner-cta; slots — eyebrow: optional, heading: require, cta: optional)
- `content-block` (extracted: infra-panel, closing-cta; slots — eyebrow: optional, heading: require, body: optional, actions: optional)
- `card` (extracted: workflow-cards, testimonials, infra-panel; slots — media: optional, eyebrow: optional, heading: require, body: optional, action: optional)
- `form` (extracted) - form module CSS measured in the fresh capture (field-module inputWrap: active border --zora-input-border-active #232325, error border peach-500, disabled fill; radius-x2 washes); the booking form itself is a modal not rendered on the captured page
- `testimonial` (extracted: testimonials)
- `stat-block`
- `navbar` (extracted: navbar)
- `footer` (extracted: footer)
- `accordion` (extracted: accordion-features)
- `accordion-item` (extracted: accordion-features)
- `tabs`
- `logo-bar` (extracted: logo-wall, partner-logos, badge-strip)
- `feature-item` (extracted: accordion-features, workflow-cards)
- `pricing-card`
- `banner` (extracted: banner-cta)
- `modal`
- `dropdown-menu` (extracted: navbar)
- `breadcrumb`
- `pagination`
- `table`
- `carousel` (extracted: testimonials)
- `steps`
- `step-item`
- `cta-block` (extracted: banner-cta, closing-cta)
- `media-text` (extracted: hero, infra-panel, accordion-features)

## 13. Locked dials
- **VARIANCE: low**
- **MOTION: medium** _(state: defined)_
- **DENSITY: medium**

## Motion (authored spec)
Motion is an authored spec (state: defined); intensity stays `medium` (calm/editorial) — no bounce, spring, overshoot, or snap.

- Easing (primary): `ease`
- Durations: fast `150ms`, base `200ms`, slow `800ms`
- Link interaction: **color-shift + underline-on-hover (footer)**
- Scroll reveal: **fade**
- prefers-reduced-motion: **declared** (transitions/reveals disabled when the user requests reduced motion).

## 14. Recipe policy
- `scaffoldFirst`: True
- `reuseBeforeCreate`: True
- `composeFromPrimitives`: True
- `themeViaModes`: True
- `slotsTakeInstancesOnly`: True

## 15. Confidence flags
- None.

## 16. Section catalog (slot contracts)

Each layout as an abstract contract: archetype, surface intent, use case, and the slots it exposes (slot -> type -> use case -> contract).

### navbar - nav (base (Primary))

Top nav riding the canvas color (transparent sticky bar): wordmark left, pill-hover nav triggers center, Login + language switcher + near-black 'Book demo' pill right. A dismissible promo utility banner may sit above.

| slot | type | use case | contract |
|---|---|---|---|
| brand | media | Remote wordmark | `` |
| navlinks | content | primary nav triggers (pill hover wash #e7e8e9, radius 40) | `` |
| actions | content | Login link + neutral filled Book demo pill | `` |

### hero - split (base (Primary))

Hero: left content stack (h1 → body → blue filled pill + outlined pill) beside a right globe illustration with floating product-UI status cards, all inside the rounded pastel noise panel.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | display heading (Bossa 400 sentence) | `` |
| body | content | supporting paragraph | `` |
| actions | content | primary filled pill + secondary outlined pill | `` |
| media | media | globe/product illustration | `` |

### logo-wall - stack (base (Primary))

Customer-proof strip: uppercase gray eyebrow caption over a single row of monochrome customer logo vectors (~40px, 64–100px gaps).

| slot | type | use case | contract |
|---|---|---|---|
| caption | content | uppercase microlabel ('GLOBAL COMPANIES GROW WITH REMOTE') | `` |
| logos | media | 12 monochrome ink logo SVGs, spaced row | `` |

### feature-accordion - split (base (Primary))

Product accordion (red theme scope): crimson eyebrow + h2, left accordion list (idle: hairline rows; hover: pink wash; ACTIVE: deep-maroon inset panel w/ white ink + circle-arrow) beside right product-UI media on a grid-lined well.

| slot | type | use case | contract |
|---|---|---|---|
| eyebrow | content | crimson uppercase label ('HOW WE DO IT') | `` |
| heading | content | section h2 | `` |
| list | content | accordion items w/ deep-accent active state | `` |
| media | media | product UI collage (profile card + task list) | `` |

### infra-panel - split (base (Primary))

Deep-dive proof split: product-UI card stack LEFT (payroll/compliance white cards on a grid-lined well), blue eyebrow + h2 + long proof body RIGHT.

| slot | type | use case | contract |
|---|---|---|---|
| media | media | stacked product-UI proof cards | `` |
| eyebrow | content | blue uppercase label ('INTELLIGENT INFRASTRUCTURE') | `` |
| heading | content | section h2 | `` |
| body | content | supporting copy w/ compliance proof terms | `` |

### banner-cta - stack (base (Primary))

Inline conversion banner: centered h2 question + ONE filled blue pill on a rounded inset panel.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | centered h2 (question form) | `` |
| action | content | single filled blue pill | `` |

### workflow-cards - cards (base (Primary))

White card grid (3 col, ~33px gap): deep-navy media well on top (product art), then blue eyebrow label, heading, body. Section header: blue eyebrow ('INTEGRATIONS, API, AND MCP') + h2.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | section header stack (eyebrow + heading) | `` |
| cards | content | white cards w/ navy media wells | `` |

### partner-logos - stack (base (Primary))

Partner proof: gray eyebrow + h2 + body centered, row of 4 colored partner logos (~40–64px tier, one in a bordered white card), one outlined pill.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | centered header stack ('THE GLOBAL PAYROLL BACKBONE') | `` |
| logos | media | 4 partner logos (colored) | `` |
| action | content | outlined pill ('Become a Partner') | `` |

### testimonials - cards (base (Primary))

Testimonial carousel: centered h2 + subhead, 3-up white cards (company mark top, quote, circle avatar + divider + name/role, hover-revealed 'Read customer story →' link), edge cards cut at viewport; centered outlined pill below.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | centered header ('A word from our customers') | `` |
| cards | content | quote cards w/ avatars + company marks | `` |
| action | content | outlined pill ('Hear from our customers') | `` |

### badge-strip - stack (base (Primary))

Award proof: centered heading + row of 6 G2 award shields (~100px) + row of 3 review-platform ratings (glyph + stars + score) + outlined pill ('4,000+ reviews').

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | centered heading | `` |
| badges | media | award shield badges (~100px row) | `` |
| ratings | media | review-platform rating chips (glyph + stars + score) | `` |
| action | content | outlined pill | `` |

### closing-cta - stack (base (Primary))

Closing CTA on the pastel gradient band: centered h2 + body + ONE filled blue pill; generous 130/90px padding.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | centered h2 | `` |
| body | content | supporting paragraph | `` |
| action | content | single filled blue pill | `` |

### footer - grid (Secondary)

Link directory: 8 headed groups flowing into 6 visual columns (14px links), legal row + app badges, bottom bar with policy links + circular social icons.

| slot | type | use case | contract |
|---|---|---|---|
| linkcols | content | 8 grouped link columns (6 visual) | `` |
| legal | content | copyright + disclaimer + policy links | `` |
| social | content | circle social icons (YouTube/LinkedIn/X/Instagram) | `` |

## 17. Layout patterns (project library)

Reusable, use-case-keyed layout patterns extracted from this project (project tier — wins over the standard library on ties). Sizes are relationships/classes, never px.

| pattern | use case | archetype | surface | special treatments | origin |
|---|---|---|---|---|---|
| `hero-inset-noise-panel` | hero | split | any | panel-on-media | extracted |
| `logo-marquee-strip` | logos | stack | primary | marquee | extracted |
| `feature-accordion-deep-accent` | features | split | primary | inset-emphasis | extracted |
| `infra-proof-split` | features | split | primary | - | extracted |
| `cta-inline-banner` | cta | stack | primary | panel-on-media | extracted |
| `features-card-grid-navy-media` | features | grid | primary | inset-media-surface | extracted |
| `partner-proof-row` | logos | stack | primary | - | extracted |
| `testimonial-card-row` | testimonial | grid | primary | edge-cut | extracted |
| `badge-award-strip` | logos | stack | primary | - | extracted |
| `cta-closing-noise` | cta | stack | primary | art-surface | extracted |

## 18. Component recipes

Recurring multi-slot anatomies this brand reuses across sections — recorded as first-class recipes in `layout-library.yaml` `recipes:` so generators compose them as units instead of re-deriving the parts.

### `conversion-noise-band` — conversion noise band

The house conversion beat: a CENTERED stack — question-form heading, optional supporting body, exactly ONE filled primary pill — sitting on the brand's pastel noise-gradient art surface. This SaaS brand closes and punctuates its page with these art-surface conversion bands (the hero opens on the same noise art as an inset split panel), always dark ink on the art: no scrim, no white text.

Anatomy: **heading** → **body** (optional) → **action**.

- **inline-panel** — conversion beat BETWEEN content sections — compact rounded inset panel (10px) with a soft tinted glow at the lower edge; heading + pill only, no body
- **closing-fullbleed** — closing bookend — the noise gradient as a FULL-BLEED band (measured: 54.375rem stack measure, 5rem band pads); heading + body + pill, mirrors the hero's art

Used by: `cta-inline-banner`, `cta-closing-noise`.
