# brand.md - woodwavegallery.webflow.io   <!-- rendered from brand.yaml v1.1 by render_brand_md.py; DO NOT EDIT -->

> Generated projection. Edit `brand.yaml` (canonical) and re-render; never hand-edit this file.

## 1. Brand snapshot
WoodWave Gallery is a warm, editorial art-gallery system on a DARK-FIRST rhythm: a deep espresso canvas (#32271a — the site's own --dark token) alternates band-by-band with warm cream (#fbf4ed — --white) and closes on a near-black footer (#181313 — --footer). One GOLD accent (#edd580 — --yellow) carries the hero wordmark, the logo mark, and every hover state (nav/footer links brighten to gold). Display voice is Melodrama — a high-contrast didone-style serif set OVERSIZED and UPPERCASE: the hero wordmark paints at ~176px filling the band; section headings run 80px uppercase with 2px tracking. Working voice is Satoshi, a geometric grotesque, at a generous 24px/1.4 body and an 18px uppercase 1px-tracked eyebrow/control register. Corners are SHARP everywhere (radius 0 — the one filled button, a dark espresso plate with a 1px cream hairline border, is a hard rectangle). CTAs are typographic: uppercase text-arrow links (BUY TICKETS, SUBSCRIBE) trailing a small arrow glyph; nav and footer link rows are slash-separated. Sections open with an uppercase Satoshi eyebrow over a Melodrama display heading, frequently backed by an OVERSIZED pale ghost-watermark word (ABOUT / 1974-2023). Media is warm-toned gallery photography — spiral wooden interiors, sculpture halls, terracotta vessels — placed as full-bleed bands, overlapping clusters, and a counted slider (1/6).

## Signature moves — the rules that carry the look

The recognizable moves that make this brand identifiable, projected from `brand.yaml` `signatures:` (each is a machine-checkable claim the `signature_check` gate verifies). Rebuild the look from these first.

- [always] Display ranks speak Melodrama (proxy Playfair Display) UPPERCASE; running text and controls speak Satoshi (proxy Manrope). A sans display or a serif body breaks the gallery's editorial register. _(type-treatment)_
- [always] Controls corner SHARP (0px) — buttons, fields and plates are hard rectangles, NEVER pills or soft rectangles. The 0 radius is the working surface corner. _(shape-motif)_
- [never] Dark surfaces come ONLY from the licensed warm-dark family — espresso #32271a and the near-black footer #181313 (photo bands underlay #2a2018). Never a generic black, navy, or cool grey as a section surface. _(surface-habit)_
- [always] Eyebrows, nav, and control labels are UPPERCASE Satoshi with positive letter tracking (~1px); the display headings are uppercase Melodrama with 2px tracking. Sentence-case labels or untracked caps break the register. _(type-treatment)_

## 2. Surface grammar
6 surface roles:
- `surface/primary` - bg `#fbf4ed`, intent `warm cream content canvas (--white; about + newsletter bands)`, text `text/on-primary`
- `surface/panel` - bg `#fbf4ed`, intent `cream card/panel (radius 0 plate, hair of rounding on media frames; FLAT — no shadow); floats on the dark bands (visit info card) and on cream`, text `text/on-primary`
- `surface/raised` - bg `#f7efe8`, intent `raised cream step off the canvas`, text `text/on-primary`
- `surface/inverse` - bg `#32271a`, intent `deep espresso dark band (--dark; hero + visit): cream ink, GOLD display accent, cream-bordered filled button; cream cards float on it`, text `text/on-inverse`, accent `accent/highlight-on-inverse`
- `surface/inverse-strong` - bg `#181313`, intent `near-black footer band (--footer): cream/gold headings, muted-warm-grey links that brighten to gold`, text `text/on-inverse`, accent `accent/highlight-on-inverse`
- `surface/photo-hero` - bg `#2a2018`, intent `full-bleed photographic band (hero staircase cluster; gallery slider) — warm-dark underlay while the photo paints, CREAM ink + GOLD display on it`, text `text/on-inverse`, accent `accent/highlight-on-inverse`

Page rhythm: surface/photo-hero -> surface/primary -> surface/photo-hero -> surface/primary -> surface/inverse -> surface/primary -> surface/inverse-strong.
Section transitions are **hard**.
Nesting: `surface/panel` allowed only inside `surface/inverse`, `surface/primary`.
Nesting: `surface/inverse` allowed only inside `surface/primary`.
Nesting: `surface/inverse-strong` allowed only inside `surface/primary`.

## 3. Color tokens (semantic role + value)

| token | value | role |
|---|---|---|
| `ink/primary` | `#32271a` | espresso — heading + body ink on cream surfaces (measured h3/p/body color rgb(50,39,26)) |
| `ink/muted` | `#6b5d50` | muted warm ink — placeholder / control-label on cream (grounding newsletter control-label #6b5d50) |
| `ink/on-dark` | `#fbf4ed` | cream ink on the espresso/near-black bands (--white; hero/visit/footer ink) |
| `ink/on-dark-muted` | `#a09a94` | muted warm-grey link ink on the footer band (grounding footer nav/social #a09a94) |
| `neutral/cream` | `#fbf4ed` | warm cream — the light content canvas + cream cards (--white; about/newsletter canvas, info card) |
| `neutral/cream-raised` | `#f7efe8` | raised cream step (grounding about/newsletter canvas #f7ede6/#f7efe8) |
| `surface/espresso` | `#32271a` | deep espresso dark band (--dark; hero + visit canvas; measured body background rgb(50,39,26)) |
| `surface/near-black` | `#181313` | near-black footer band (--footer; measured footer bg rgb(24,19,19)) |
| `accent/gold` | `#edd580` | gold accent (--yellow): the hero wordmark ink, the logo mark, and EVERY link hover (nav/footer links brighten to gold — css hoverRules color: var(--yellow)) |
| `action/primary-hover` | `#1d170f` | the filled buy-button's measured hover fill (.buy-button:hover background-color #1d170f) |
| `border/hairline` | `rgba(50, 39, 26, 0.2)` | hairline divider on cream (footer legal rules, ruled price rows) — the espresso ink at low alpha (#32271a33 in the css color census) |
| `border/on-dark` | `#fbf4ed` | cream hairline border — the filled button's 1px border on the espresso plate (measured buy-button border 1px solid rgb(251,244,237)) |
| `border/hairline-on-inverse` | `rgba(251, 244, 237, 0.2)` | cream hairline at low alpha — footer social/legal divider rules on the near-black band |
| `media/map-grey` | `#8a8a8a` | greyscale street-map fill (third-party map media well) |
| `surface/primary` | `#fbf4ed` | ALIAS of neutral/cream — canonical page-canvas role (the warm cream content surface) |
| `surface/panel` | `#fbf4ed` | ALIAS of neutral/cream — canonical panel/card role (cream cards float on the dark bands: the visit info card, gallery frames) |
| `surface/raised` | `#f7efe8` | ALIAS of neutral/cream-raised — canonical raised-light role |
| `surface/inverse` | `#32271a` | ALIAS of surface/espresso — canonical dark band role (hero, visit) |
| `surface/inverse-strong` | `#181313` | ALIAS of surface/near-black — the near-black chrome dark (footer) |
| `accent/highlight` | `#edd580` | ALIAS of accent/gold — canonical accent role (the one gold; display ink on dark, logo mark, link-hover) |
| `accent/highlight-on-inverse` | `#edd580` | accent ON dark surfaces — the gold is scheme-stable (hero wordmark + footer logo both gold on dark) |
| `text/on-primary` | `#32271a` | ALIAS of ink/primary — canonical ink-on-light role |
| `text/on-primary-muted` | `#6b5d50` | ALIAS of ink/muted — canonical muted-ink-on-light role |
| `text/on-inverse` | `#fbf4ed` | canonical ink-on-dark role (cream; hero/visit/footer headings measured cream) |
| `text/on-inverse-muted` | `#a09a94` | canonical muted-ink-on-dark role (footer links #a09a94) |
| `text/on-accent` | `#32271a` | ink on the gold accent — espresso reads on gold (contrast) |
| `text/ghost-on-primary` | `rgba(50, 39, 26, 0.05)` | canonical ghost-on-light role — bound to a faint espresso wash so any ghost/placeholder fallback stays on-palette (WoodWave has no ghost-button device) |
| `color/photo-tint` | `#2a2018` | sampled warm-dark tint of the photographic bands (hero/gallery) — the band's fallback underlay while the photo paints; generic photographic-surface tint role |
| `border/hairline-on-primary` | `rgba(50, 39, 26, 0.2)` | ALIAS of border/hairline — canonical hairline-on-light role |

## 4. Typography roles

| role | family | size (base) | line-height | weight | case |
|---|---|---|---|---|---|
| display-hero | Melodrama | 11rem | 0.9em | 500 | uppercase |
| h1 | Melodrama | 5rem | 1.2em | 400 | uppercase |
| h2 | Melodrama | 3.5rem | 1.2em | 400 | uppercase |
| h3 | Melodrama | 2rem | 1.25em | 400 | uppercase |
| h4 | Satoshi | 1.5rem | 1.3em | 500 | none |
| h5 | Satoshi | 1.125rem | 1.2em | 500 | uppercase |
| h6 | Satoshi | 1rem | 1.2em | 500 | uppercase |
| eyebrow | Satoshi | 1.125rem | 1.2em | 500 | uppercase |
| body | Satoshi | 1.5rem | 1.4em | 400 | sentence |
| body-lg | Satoshi | 1.75rem | 1.4em | 400 | sentence |
| control-text | Satoshi | 1.125rem | 1.2em | 400 | uppercase |
| micro | Satoshi | 0.75rem | 1.2em | 500 | uppercase |
| stat-display | Melodrama | 4rem | 1.05em | 400 | uppercase |
| headingEmphasis |  | Nonerem |  | - |  |

## 5. Spacing system
- `section-padding-light`: 7.5rem - the workhorse vertical section rhythm (~120px; grounding about/visit/newsletter top pads 90–200, bottom 40–130 — the mid rung)
- `section-y-sm`: 4rem - short section tier (~64px; tighter bands e.g. gallery/footer)
- `section-y-lg`: 9.375rem - spacious tier (~150px; the newsletter band top pad 150 / visit top 200)
- `module-gap-editorial`: 7.5rem - ALIAS of section-padding-light — preview/composer module rhythm
- `eyebrow-to-heading`: 2.5rem - eyebrow→heading gap (grounding visit + newsletter relationalSpacingPx eyebrowToHeading 40px)
- `heading-to-body`: 5rem - heading→body gap (grounding visit headingToBody 100 / newsletter 80 → canonical 80px)
- `body-to-cta`: 2.5rem - body→actions gap (grounding gapPx ~40 between copy and the text-arrow CTA rows)
- `block-to-block`: 4rem - header-stack→content rhythm inside sections (grounding gapPx 40–64 between the opener and the media/blocks)
- `column-to-column`: 4rem - split-row column gutter (grounding visit gapPx 64 photo↔price card; about gapPx 60)
- `grid-gap`: 2rem - card/media grid gap (about alternating blocks; synthesized grids)
- `panel-padding`: 2.5rem - card/panel inset (grounding visit info card pad 40x40)
- `list-item-gap`: 1.125rem - ruled row rhythm (grounding visit price rows pad 18x0 above dividers)
- `button-inset`: 0.5625rem 0.9375rem - the filled button inset 9x15 (measured buy-button padding 9px 15px)
- `container-max`: 81.25rem - content max-width 1300px measured at every tier (container cssMaxWidth 1300; --container)
- `container-span`: min(100vw - 2.5rem, 81.25rem) - the container LAW as one CSS expression: 1300px cap, ~20px side gutters below the cap (tier facts: used 1300 @1440/1920, full-width minus gutters @960/375)
- `radius-global`: 0rem - ALIAS of radius/sharp — the brand's working corner is SHARP (0) — the signature

## 6. Layout grammar
- **Nav** (navbar, Inverse): gold wavy-lines mark + WOODWAVE wordmark.
- **Stack** (hero, surface/photo-hero): giant gold Melodrama wordmark (uppercase).
- **Stack** (about, surface/primary): uppercase Satoshi eyebrow ('ABOUT').
- **Stack** (gallery-slider, surface/photo-hero): chrome eyebrow ('GALLERY') over the photo.
- **Split** (founder-story, surface/primary): Melodrama uppercase heading (left).
- **Split** (visit, surface/inverse): uppercase eyebrow ('VISIT').
- **Stack** (newsletter, surface/primary): uppercase eyebrow ('STAY UPDATED').
- **Stack** (footer, Inverse): giant Melodrama slash-nav headline (2 lines).

## 7. Slot mapping (slot -> primitive/block contract)
### navbar

| slot | role | contract |
|---|---|---|
| brand | gold wavy-lines mark + WOODWAVE wordmark | `media` |
| navlinks | slash-separated uppercase nav (18px Satoshi, hover → gold) | `content` |
| actions | BUY TICKETS text-arrow | `content` |

### hero

| slot | role | contract |
|---|---|---|
| heading | giant gold Melodrama wordmark (uppercase) | `content` |
| background | full-bleed warm staircase photo + overlapping cluster | `media` |

### about

| slot | role | contract |
|---|---|---|
| eyebrow | uppercase Satoshi eyebrow ('ABOUT') | `content` |
| heading | 80px Melodrama uppercase heading | `content` |
| body | lede paragraph (Satoshi 24-28px) | `content` |
| media | alternating gallery/architecture photos | `media` |

### gallery-slider

| slot | role | contract |
|---|---|---|
| eyebrow | chrome eyebrow ('GALLERY') over the photo | `content` |
| media | 6 full-bleed gallery photos | `media` |
| controls | slide counter (1/6) + numeric dot rail + circular arrow | `content` |

### founder-story

| slot | role | contract |
|---|---|---|
| heading | Melodrama uppercase heading (left) | `content` |
| body | founder narrative paragraph (right) | `content` |
| media | seated founder portrait | `media` |

### visit

| slot | role | contract |
|---|---|---|
| eyebrow | uppercase eyebrow ('VISIT') | `content` |
| heading | Melodrama display ('WELCOME TO THE GALLERY') | `content` |
| media | greyscale map band + wood-interior photo | `media` |
| card | cream info card (address + open hours ruled rows) | `content` |
| pricing | ruled ticket-price rows w/ BUY TICKETS text-arrows | `content` |

### newsletter

| slot | role | contract |
|---|---|---|
| eyebrow | uppercase eyebrow ('STAY UPDATED') | `content` |
| heading | Melodrama display heading | `content` |
| form | underline email field + SUBSCRIBE text-arrow | `content` |

### footer

| slot | role | contract |
|---|---|---|
| navheadline | giant Melodrama slash-nav headline (2 lines) | `content` |
| social | slash-separated social row (INSTAGRAM / FACEBOOK / YOUTUBE / TWITTER) | `content` |
| legal | copyright + policy links on a pale strip | `content` |

## 8. Composition mechanics
- **dark-first-alternation**: The page runs DARK-FIRST: it opens on espresso (#32271a), alternates band-by-band with warm cream (#fbf4ed), and closes on the near-black footer (#181313). Dark bands take cream ink + a gold display accent; cream bands take espresso ink.
- **melodrama-display-satoshi-body**: Display voice is Melodrama — a high-contrast didone serif set OVERSIZED and UPPERCASE with letter tracking (the hero wordmark fills the band). Working voice is Satoshi, a grotesque, at a generous 24px body + 18px uppercase labels. Hierarchy is SIZE, never weight jumps or a sans display.
- **sharp-corner-controls**: Every control corners SHARP (radius 0) — the one filled button is a hard espresso rectangle with a 1px cream border; the newsletter field is a bare underline. NEVER pills or soft rectangles (the 50%/3px radii in the census are Webflow lightbox/slider chrome).
- **gold-is-the-one-accent**: ONE gold (#edd580 — the site's --yellow token) is the accent: the hero wordmark ink, the logo mark, and EVERY link hover (nav/footer links warm to gold). It never fills a section surface and never paints body copy.
- **text-arrow-cta-system**: CTAs are typographic: uppercase Satoshi labels trailing a small arrow glyph (BUY TICKETS / SUBSCRIBE), ink warming to gold on hover. The filled button is used sparingly; nav and footer link rows are slash-separated.
- **ghost-watermark-headings**: Editorial bands back their heading with an OVERSIZED pale ghost watermark word set in the display face (ABOUT behind the about heading; 1974-2023 behind the founder story) — a tone-on-tone type device, one per band, never a raster.
- **warm-gallery-photography**: Imagery is warm-toned gallery photography — spiral wooden interiors, sculpture halls, terracotta vessels, seated portraits — placed full-bleed, in overlapping clusters, and in a counted slider; SHARP frames (a hair of rounding only on the map/info well).
- **near-black-footer-close**: The page closes on a near-black footer (#181313): a gold logo, a GIANT Melodrama slash-nav headline, a muted-warm-grey social slash row that brightens to gold, and a pale legal strip.

## 9. Do
- Open bands with OVERSIZED uppercase Melodrama display headings, tracked; let the hero wordmark fill the band.
- Keep body copy generous (Satoshi 24px/1.4) — the unhurried body is the gallery's texture.
- Corner every control SHARP (radius 0); the one filled button is an espresso plate with a 1px cream border.
- Alternate espresso and cream bands; close near-black.
- Make CTAs uppercase text-arrow links (label + arrow glyph); warm ink to gold on hover.
- Back editorial headings with an oversized pale ghost display word.

## 10. Avoid
- Avoid rounded/pill buttons — WoodWave controls are SHARP rectangles.
- Avoid gold body/heading-on-cream text — gold is display-on-dark, the mark, and link-hover only.
- Avoid drop shadows/elevation — depth is surface contrast + overlapping media.
- Avoid cool greys/blues as surfaces — the neutral family is warm (espresso/cream); the only grey is the third-party map.

## 11. Never-do
- Never set display headings in the sans — the Melodrama serif IS the brand's editorial voice.
- Never lowercase the display headings/eyebrows — the register is uppercase + tracked.
- Never round the controls — sharp corners are a signature.

## 12. Primitive & block rules

**Primitives** (8 extracted / 0 designed)
- `heading` (extracted: hero, about, visit, newsletter, footer; use: always) - display headings are Melodrama (high-contrast didone serif), UPPERCASE, with letter tracking — the hero wordmark at ~176px, section headings at 80px w400 with 2px tracking; hierarchy is SIZE, never weight jumps; the hero display paints GOLD (#edd580) on the dark band; section headings paint espresso on cream / cream on dark
- `eyebrow` (extracted: about, visit, newsletter, gallery-slider; use: always) - uppercase Satoshi microlabel, 18px w500, 1px tracking (ABOUT / VISIT / GALLERY / STAY UPDATED) — sits above the Melodrama display heading with a ~40px gap
- `paragraph` (extracted: about, founder-story, visit; use: always) - Satoshi w400 at a GENEROUS 24px/33.6 — espresso ink #32271a on cream, cream #fbf4ed on the dark bands; the gallery reads unhurried
- `button` (extracted: nav, hero; use: sparingly; variant: filled-primary) - the ONE filled control is a dark espresso plate with a 1px CREAM hairline border + cream uppercase label, SHARP corners (radius 0); most CTAs are typographic text-arrow links — orange/pill buttons are off-brand
- `link` (extracted: nav, visit, newsletter, footer; use: text-links-only) - text links are the dominant CTA: uppercase Satoshi with a trailing arrow glyph (BUY TICKETS / SUBSCRIBE), or slash-separated nav rows; ink warms to GOLD on hover; standing links reveal an underline
- `image` (extracted: hero, about, gallery-slider, founder-story, visit; use: always) - photography = warm-toned gallery interiors, sculpture halls, spiral wooden architecture, terracotta vessels, seated portraits; placed full-bleed, in overlapping clusters, and in a counted slider; SHARP frames (hair of rounding on the map/info well)
- `logo` (extracted: nav, footer; use: always) - the WoodWave mark is a wavy-lines glyph + wordmark, set in GOLD on dark (hero + footer) and espresso on cream; ~26px tall vector (000-logo.svg)
- `input` (extracted: newsletter; use: forms) - the newsletter field is a borderless UNDERLINE input: uppercase placeholder label, a 1px rule beneath spanning full width, transparent fill, SHARP (radius 0); the submit is an uppercase text-arrow

**Blocks** (12 extracted / 0 designed)
- `header` (extracted: about, visit, newsletter; slots — eyebrow: optional, heading: require, cta: optional)
- `content-block` (extracted: about, founder-story, visit, newsletter; slots — eyebrow: optional, heading: require, body: optional, actions: optional)
- `card` (extracted: visit, about, gallery-slider; slots — media: optional, heading: optional, body: optional, action: optional)
- `form` (extracted: newsletter)
- `testimonial`
- `stat-block`
- `navbar` (extracted: nav)
- `footer` (extracted: footer)
- `accordion`
- `accordion-item`
- `tabs`
- `logo-bar`
- `feature-item` (extracted: about, visit)
- `pricing-card` (extracted: visit)
- `banner`
- `modal`
- `dropdown-menu`
- `breadcrumb`
- `pagination` (extracted: gallery-slider)
- `table`
- `carousel` (extracted: gallery-slider)
- `steps`
- `step-item`
- `cta-block` (extracted: newsletter)
- `media-text` (extracted: about, founder-story, visit)

## 13. Locked dials
- **VARIANCE: medium**
- **MOTION: low** _(state: defined)_
- **DENSITY: low**

## Motion (authored spec)
Motion is an authored spec (state: defined); intensity stays `low` (calm/editorial) — no bounce, spring, overshoot, or snap.

- Easing (primary): `ease-in-out`
- Durations: fast `200ms`, base `300ms`, slow `800ms`
- Link interaction: **link ink warms to gold (#edd580) on hover (color .2s → .8s); standing links reveal an underline**
- Scroll reveal: **fade**
- prefers-reduced-motion: **not-declared** (transitions/reveals disabled when the user requests reduced motion).

## 14. Recipe policy
- `scaffoldFirst`: True
- `reuseBeforeCreate`: True
- `composeFromPrimitives`: True
- `themeViaModes`: True
- `slotsTakeInstancesOnly`: True

## 15. Provenance & confidence ledger

Every asset and value below is **rendered**. These four buckets annotate how each fact was obtained and where a production swap may later be needed — a flag is never a replacement, substitution, or omission.

**Sampled (measured / extracted from source).** 29 color tokens, 14 type roles, 16 spacing steps carry evidence-backed provenance (see §3-§5).

**Assumed (designed or inferred — flagged, still rendered).**
- None.

**Substitute (real family loaded; proxy is the fallback only).**
- `display-hero`, `h1`, `h2`, `h3`, `stat-display`: render `Melodrama`; proxy `Playfair Display` is the loaded fallback only.
- `h4`, `h5`, `h6`, `eyebrow`, `body`, `body-lg`, `control-text`, `micro`: render `Satoshi`; proxy `Manrope` is the loaded fallback only.

**Needs-licensing (rendered as captured, flagged for production swap).**
- 1 third-party mark(s) in `media-assets.yaml` (`usageRights: third-party-mark`) — rendered as captured, flagged for a licensed swap; never auto-substituted.
- 1 own logo mark(s) — rendered, flagged for production review.

## 16. Section catalog (slot contracts)

Each layout as an abstract contract: archetype, surface intent, use case, and the slots it exposes (slot -> type -> use case -> contract).

### navbar - nav (Inverse)

Chrome on the espresso band: gold wavy-mark + WOODWAVE wordmark left; center slash-separated nav (ABOUT / GALLERY / EXHIBITION / VISIT); a BUY TICKETS text-arrow at the far right. Mobile collapses to a hamburger → full-screen menu with a social grid.

| slot | type | use case | contract |
|---|---|---|---|
| brand | media | gold wavy-lines mark + WOODWAVE wordmark | `` |
| navlinks | content | slash-separated uppercase nav (18px Satoshi, hover → gold) | `` |
| actions | content | BUY TICKETS text-arrow | `` |

### hero - stack (surface/photo-hero)

Gallery hero: a giant GOLD Melodrama wordmark 'WOODWAVE GALLERY' centered over a full-bleed warm staircase photo, with an overlapping terracotta-vessel photo and a corner figure photo.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | giant gold Melodrama wordmark (uppercase) | `` |
| background | media | full-bleed warm staircase photo + overlapping cluster | `` |

### about - stack (surface/primary)

Editorial about band on cream: uppercase eyebrow → 80px Melodrama heading backed by an OVERSIZED pale ghost 'ABOUT' watermark; a lede paragraph and alternating photo/copy blocks.

| slot | type | use case | contract |
|---|---|---|---|
| eyebrow | content | uppercase Satoshi eyebrow ('ABOUT') | `` |
| heading | content | 80px Melodrama uppercase heading | `` |
| body | content | lede paragraph (Satoshi 24-28px) | `` |
| media | media | alternating gallery/architecture photos | `` |

### gallery-slider - stack (surface/photo-hero)

Gallery carousel: a full-bleed warm interior photo with a chrome eyebrow (GALLERY) and a slide counter (1/6) over it, a circular slider-arrow control, 6 frames.

| slot | type | use case | contract |
|---|---|---|---|
| eyebrow | content | chrome eyebrow ('GALLERY') over the photo | `` |
| media | media | 6 full-bleed gallery photos | `` |
| controls | content | slide counter (1/6) + numeric dot rail + circular arrow | `` |

### founder-story - split (surface/primary)

Founder story on cream: a large Melodrama heading top-left, a seated portrait + body copy lower-right, an OVERSIZED pale '1974-2023' year watermark behind.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | Melodrama uppercase heading (left) | `` |
| body | content | founder narrative paragraph (right) | `` |
| media | media | seated founder portrait | `` |

### visit - split (surface/inverse)

Visit band on espresso: uppercase eyebrow (VISIT) → Melodrama display (WELCOME TO THE GALLERY) → a greyscale map band with an overlapping cream info card (ADDRESS + OPEN HOURS); then TICKET PRICES — a wood-interior photo left / ruled price rows right (each with a BUY TICKETS text-arrow).

| slot | type | use case | contract |
|---|---|---|---|
| eyebrow | content | uppercase eyebrow ('VISIT') | `` |
| heading | content | Melodrama display ('WELCOME TO THE GALLERY') | `` |
| media | media | greyscale map band + wood-interior photo | `` |
| card | content | cream info card (address + open hours ruled rows) | `` |
| pricing | content | ruled ticket-price rows w/ BUY TICKETS text-arrows | `` |

### newsletter - stack (surface/primary)

Subscribe band on cream: centered uppercase eyebrow (STAY UPDATED) → Melodrama display heading → a borderless underline email field + SUBSCRIBE text-arrow.

| slot | type | use case | contract |
|---|---|---|---|
| eyebrow | content | uppercase eyebrow ('STAY UPDATED') | `` |
| heading | content | Melodrama display heading | `` |
| form | content | underline email field + SUBSCRIBE text-arrow | `` |

### footer - stack (Inverse)

Centered footer stack: gold logo → giant Melodrama nav headline (ABOUT / GALLERY / EXHIBITION / VISIT / BUY TICKETS) → social slash row → legal bar on a pale strip.

| slot | type | use case | contract |
|---|---|---|---|
| navheadline | content | giant Melodrama slash-nav headline (2 lines) | `` |
| social | content | slash-separated social row (INSTAGRAM / FACEBOOK / YOUTUBE / TWITTER) | `` |
| legal | content | copyright + policy links on a pale strip | `` |

## 17. Layout patterns (project library)

Reusable, use-case-keyed layout patterns extracted from this project (project tier — wins over the standard library on ties). Sizes are relationships/classes, never px.

| pattern | use case | archetype | surface | special treatments | origin |
|---|---|---|---|---|---|
| `hero-gallery-overlay` | hero | stack | any | text-on-media | extracted |
| `about-editorial-ghost` | about | stack | primary | ghost-watermark | extracted |
| `gallery-slider-band` | gallery | stack | any | background-with-foreground, carousel | extracted |
| `founder-story-watermark` | content | split | primary | ghost-watermark | extracted |
| `visit-map-card` | content | split | inverse | overlap-card, ruled-rows | extracted |
| `newsletter-subscribe` | cta | stack | primary | underline-field | extracted |

## 18. Component recipes

Recurring multi-slot anatomies this brand reuses across sections — recorded as first-class recipes in `layout-library.yaml` `recipes:` so generators compose them as units instead of re-deriving the parts.

### `section-opener` — section opener

The house band-opener: an uppercase Satoshi eyebrow (18px, 1px tracking) over an oversized uppercase Melodrama display heading, a ~40px eyebrow→heading gap. Four of the working bands open with it (about, gallery, visit, newsletter) — the recurring identity move.

Anatomy: **eyebrow** → **heading**.

- **left** — editorial / split bands — the opener anchors left (about, visit)
- **centered** — standalone bands — the opener centers (newsletter; gallery over the photo)

Used by: `about-editorial-ghost`, `visit-map-card`, `newsletter-subscribe`, `gallery-slider-band`.

### `ghost-watermark-heading` — ghost watermark heading

An OVERSIZED pale ghost word set in the display face behind the band heading, tone-on-tone (ABOUT behind the about band, 1974-2023 behind the founder story). A CSS text device — never a raster; sits at z:back behind the content stack.

Anatomy: **watermark** → **heading**.

- **word** — a single pale word (ABOUT)
- **numerals** — pale year numerals (1974-2023)

Used by: `founder-story-watermark`.

### `ruled-arrow-row` — ruled arrow row

A full-width row above a 1px hairline divider: a label (and value) at the left, an uppercase text-arrow action at the right. The ticket-price rows use it (price + tier | BUY TICKETS →); the info card's open-hours rows use its label|value ruled form. One anatomy, two stylings.

Anatomy: **label** → **trail** (optional) → **rule**.

- **price-row** — ticket pricing — price + tier left, BUY TICKETS text-arrow right
- **hours-row** — info card open-hours — day range left, time right, no action
