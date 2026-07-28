# brand.md - woodwavegallery.webflow.io   <!-- rendered from brand.yaml v2.0 by render_brand_md.py; DO NOT EDIT -->

> Generated projection. Edit `brand.yaml` (canonical) and re-render; never hand-edit this file.

## 1. Brand snapshot
WoodWave Gallery is a warm, two-tone editorial system for a photography gallery. Signature motifs: a single high-contrast didone serif set uppercase at every display tier; a cream canvas with deep warm-brown bookend bands; enormous ghost watermark words behind content; a staggered photographic collage with marginal micro-captions; and a muted gold accent reserved for dark surfaces.

## 2. Surface grammar
4 surface roles:
- `surface/primary` - bg `#FAF0E8`, intent `default cream canvas`, text `text/on-primary`
- `surface/inverse` - bg `#3A2F23`, intent `dark bookend/band`, text `text/on-inverse`, accent `accent/highlight`
- `surface/inverse-strong` - bg `#1B150F`, intent `strong near-black footer`, text `text/on-inverse`, accent `accent/highlight`
- `surface/panel` - bg `#F7EFE6`, intent `cream panel, child of inverse only`, text `text/on-primary`

Page rhythm: surface/inverse -> surface/primary -> surface/primary -> surface/inverse -> surface/primary -> surface/inverse-strong.
Section transitions are **hard-cut** - no gradients, fades, or divider rules at seams.
Nesting: `surface/panel` allowed only inside `surface/inverse`.

## 3. Color tokens (semantic role + value)

| token | value | role |
|---|---|---|
| `surface/primary` | `#FAF0E8` | cream canvas background |
| `surface/panel` | `#F7EFE6` | slightly warmer cream panel (child of inverse only) |
| `surface/inverse` | `#3A2F23` | deep warm-brown bookend/band background |
| `surface/inverse-strong` | `#1B150F` | near-black strong footer band |
| `accent/highlight` | `#edd580` | muted gold accent — dark surfaces only (aligned to the measured link-hover gold) |
| `text/on-primary` | `#1F1A14` | body/display text on cream |
| `text/on-inverse` | `#F5EDE2` | text on dark bands |
| `text/on-primary-muted` | `#4A4239` | secondary/muted text on cream |
| `text/on-inverse-muted` | `#C9BFB2` | secondary/muted text on dark |
| `text/ghost-on-primary` | `rgba(31, 26, 20, 0.06)` | ghost watermark wordmark on cream |
| `border/hairline-on-primary` | `rgba(31, 26, 20, 0.30)` | underline-input hairline on cream |

## 4. Typography roles

| role | family | size (base) | line-height | weight | case |
|---|---|---|---|---|---|
| display-hero | Melodrama | 6rem | 1.05em | 500 | uppercase |
| h1 | Melodrama | 3.5rem | 1.15em | 400 | uppercase |
| h2 | Melodrama | 2.25rem | 1.3em | 400 | uppercase |
| h3 | Melodrama | 1.625rem | 1.3em | 400 | uppercase |
| eyebrow | Inter | 0.6875rem | 1.2em | 400 | uppercase |
| body | Inter | 0.875rem | 1.55em | 400 | sentence |
| control-text | Inter | 0.875rem | 1.2em | 400 | uppercase |
| counter-display | Melodrama | 2rem | 1.0 | 400 | none |
| ghost-watermark | Melodrama | 26.25rem | 1.0 | 400 | uppercase |
| footer-sitemap-link | Melodrama | 2.5rem | 1.4em | 400 | uppercase |

## 5. Spacing system
- `section-padding-light`: 6.875rem - vertical section padding on cream
- `section-padding-dark`: 6.25rem - vertical section padding on dark bands (shares light tier; minor deviation accepted)
- `module-gap-editorial`: 7.5rem - gap between collage modules
- `caption-to-media`: 0.75rem - gap between a micro-caption and its media
- `eyebrow-to-heading`: 1.5rem - gap between eyebrow and heading
- `panel-padding`: 1.75rem - inner padding of cream panels
- `radius-global`: 0rem - global corner radius — all radii zeroed

## 6. Layout grammar
- **Stack** (opening-bookend, surface/inverse): display title over layered photo collage.
- **Collage** (editorial-collage, surface/primary): loose single-column field of [media + micro-caption + offset paragraph] modules.
- **Split** (mission-statement, surface/primary): eyebrow -> heading -> body -> arrow action.
- **Stack-Fullbleed** (gallery-showcase, surface/primary): eyebrow (far left) + static counter (far right).
- **Collage** (heritage-timeline, surface/primary): ghost year-range watermark behind heading + media + two dated captions.
- **Split** (curator-quote, surface/primary): eyebrow -> quote-as-heading -> attribution body.
- **Split** (info-band, surface/inverse): flush hard-edged photo.
- **Split** (visit-band, surface/inverse): eyebrow -> band heading.
- **Stack** (conversion-stack, surface/primary): centered narrow column: eyebrow -> heading -> underline input.
- **Stack** (exhibition-hero, surface/inverse): display title over layered photo collage.
- **Collage** (exhibition-about, surface/primary): loose single-column field of [media + micro-caption + offset paragraph] modules.
- **Stack-Fullbleed** (exhibition-works, surface/primary): eyebrow (far left) + static counter (far right).
- **Stack** (exhibition-schedule, surface/inverse): centered eyebrow -> heading -> ruled event/date rows.
- **Stack** (exhibition-tickets, surface/primary): centered eyebrow -> heading -> intro -> ruled tier/price rows -> action.
- **Split** (exhibition-curator-quote, surface/primary): eyebrow -> quote-as-heading -> attribution body.
- **Stack** (exhibition-faq, surface/primary): centered eyebrow -> heading -> stacked disclosure Q&A rows.
- **Cards** (demo-staggered-cards, surface/primary): staggered feature card modules (image + tracked caption + short body).
- **Interlock** (demo-interlock-inset, surface/primary): pinned caption + inset image floated right + wrapping statement heading.

## 7. Slot mapping (slot -> primitive/block contract)
### opening-bookend

| slot | role | contract |
|---|---|---|
| main | wordmark (nav) | `logo` |
| main | display title | `header` |
| main | hero photography | `image` |
| main | overlap photography | `image` |

### editorial-collage

| slot | role | contract |
|---|---|---|
| main | module media | `image` |
| main | micro-caption | `eyebrow` |
| main | offset paragraph | `paragraph` |

### mission-statement

| slot | role | contract |
|---|---|---|
| text | eyebrow | `eyebrow` |
| text | display heading | `header` |
| text | statement body | `paragraph` |
| text | collection action | `link` |
| media | statement photography | `image` |

### gallery-showcase

| slot | role | contract |
|---|---|---|
| utility | band eyebrow | `eyebrow` |
| utility | static index counter | `caption` |
| main | full-bleed interior photography | `image` |
| main | margin caption below band | `caption` |

### heritage-timeline

| slot | role | contract |
|---|---|---|
| main | ghost year-range watermark | `eyebrow` |
| main | eyebrow | `eyebrow` |
| main | display heading | `header` |
| main | heritage photography | `image` |
| main | offset paragraph | `paragraph` |
| main | dated margin caption | `caption` |

### curator-quote

| slot | role | contract |
|---|---|---|
| text | eyebrow | `eyebrow` |
| text | quote set as heading | `header` |
| text | attribution body | `paragraph` |
| media | curator portrait | `image` |
| media | name caption beside portrait | `caption` |

### info-band

| slot | role | contract |
|---|---|---|
| media | photo | `image` |
| panel | panel title | `header` |
| panel | action row | `link` |

### visit-band

| slot | role | contract |
|---|---|---|
| intro | eyebrow | `eyebrow` |
| intro | band heading | `header` |
| media | static map | `image` |
| media | map margin caption | `caption` |
| tickets | ticket panel title | `header` |
| tickets | buy tickets action | `link` |
| visit | hours/address panel title | `header` |
| visit | get directions action | `link` |

### conversion-stack

| slot | role | contract |
|---|---|---|
| main | eyebrow | `eyebrow` |
| main | heading | `header` |
| main | newsletter form (underline only) | `form` |

### exhibition-hero

| slot | role | contract |
|---|---|---|
| main | wordmark (nav) | `logo` |
| main | display title | `header` |
| main | hero photography | `image` |
| main | overlap photography | `image` |

### exhibition-about

| slot | role | contract |
|---|---|---|
| main | module media | `image` |
| main | micro-caption | `eyebrow` |
| main | offset paragraph | `paragraph` |

### exhibition-works

| slot | role | contract |
|---|---|---|
| utility | band eyebrow | `eyebrow` |
| utility | static index counter | `caption` |
| main | full-bleed interior photography | `image` |
| main | margin caption below band | `caption` |

### exhibition-schedule

| slot | role | contract |
|---|---|---|
| main | eyebrow | `eyebrow` |
| main | heading | `header` |

### exhibition-tickets

| slot | role | contract |
|---|---|---|
| main | eyebrow | `eyebrow` |
| main | heading | `header` |
| main | buy tickets action | `link` |

### exhibition-curator-quote

| slot | role | contract |
|---|---|---|
| text | eyebrow | `eyebrow` |
| text | quote set as heading | `header` |
| text | attribution body | `paragraph` |
| media | curator portrait | `image` |
| media | name caption beside portrait | `caption` |

### exhibition-faq

| slot | role | contract |
|---|---|---|
| main | eyebrow | `eyebrow` |
| main | heading | `header` |

### demo-staggered-cards

| slot | role | contract |
|---|---|---|
| cards | module photography | `image` |
| cards | tracked module caption | `caption` |
| cards | module body | `paragraph` |

### demo-interlock-inset

| slot | role | contract |
|---|---|---|
| main | pinned two-line caption | `caption` |
| main | inset statement photography | `image` |
| main | wrapping statement heading | `header` |

## 8. Composition mechanics
- **overlap-primary-ornament**: Overlap is the brand's primary ornament. Sanctioned types only: display-text-over-media, media-over-media, panel-over-media, media-over-seam.
- **z-order**: ghost watermark (back, aria-hidden) -> media rectangles -> panels -> text. Text never trapped beneath media.
- **stagger-anchors**: Consecutive collage modules alternate horizontal anchors (far-left -> center-right -> left); offsets ~1/3 of container, not subtle.
- **composite-via-offsets**: Composite archetypes (collage/overlay/band) are realized with absolute offsets inside the nearest scaffold slot; no dedicated composite components are created.
- **seam-bridging-photo**: A small foreground photo may straddle a dark->light seam. Optional device, not default; never on every seam. _(low confidence)_

## 9. Do
- Photo captions live in the margin as uppercase eyebrows.
- Use overlap as the primary ornament (sanctioned types only).
- Carry hierarchy with type size, surface flips, and overlap — not interface chrome.

## 10. Avoid
- Prefer anchored/asymmetric editorial runs; reserve centering for bookend/conversion stacks.

## 11. Never-do
- No filled, outlined, or pill buttons - all actions are typographic with arrows/slashes.
- No rounded corners anywhere (radius globally 0).
- No drop shadows, borders, or mats on media or panels - separation is fill contrast only.
- No gradients, tints, or fade transitions between sections - hard cuts only.
- No cards on the cream canvas - light-canvas content is open collage, never boxed.
- No accent color on light surfaces; no accent-colored links or icons.
- No boxed/filled form inputs - underline only, inline text submit.
- No text overlaid directly on photographs (captions live in the margin). Display title over media in the bookend is the sanctioned exception.
- No hairline rules between sections.
- No default/system or generic sans for display - all display tiers use the self-hosted didone display face (Melodrama; Playfair Display / serif fallback).
- Centering is reserved for conversion and bookend stacks; editorial runs are anchored/asymmetric.

## 12. Primitive & block rules

**Primitives** (12 extracted / 24 designed)
- `heading` (extracted: opening-bookend, about-run, info-band, conversion; use: always; refs: `neverDo.no-default-fonts`)
- `eyebrow` (extracted: about-run, info-band, conversion; use: always) - micro-captions live in the margin beside media, never over photos
- `image` (extracted: opening-bookend, about-run, info-band; use: always; refs: `neverDo.no-radius`, `neverDo.no-shadows`)
- `link` (extracted: opening-bookend, info-band, conversion, closing-bookend; use: always; variant: arrow; remap of cta; refs: `neverDo.no-buttons`)
- `logo` (extracted: opening-bookend, closing-bookend; use: always; variant: inverse; refs: `neverDo.no-accent-on-light`)
- `paragraph` (extracted: about-run; use: always) - body copy set narrow (~1/3 container), offset from its media; Inter, sentence case
- `caption` (extracted: about-run; use: optional) - figure/footnote captions are muted uppercase margin micro-text, never over media
- `input` (extracted: conversion; use: when-form; variant: underline) - single underline rule only; inline text submit; no box or fill
- `form-field` (extracted: conversion; use: when-form) - label as uppercase eyebrow; underline control; no boxed rows
- `divider` (extracted: info-band; use: optional) - 1px ruled bars separate action/price rows inside panels; never between sections
- `cta` (extracted: opening-bookend, info-band, conversion; use: always; refs: `neverDo.no-buttons`)
- `button` (extracted: opening-bookend, info-band, conversion; use: never; refs: `neverDo.no-buttons`)
- `subheading` (designed, overridable; use: optional) - no lede observed; synthesize as a smaller didone line under the heading (muted), never a generic sans sub-deck
- `label` (designed, overridable; use: optional) - inline labels as Inter uppercase micro-text matching the eyebrow / control-text roles
- `quote` (designed, overridable; use: optional) - pull quote as large didone type open on the canvas; attribution as a margin eyebrow; never a boxed/quoted card
- `stat` (designed, overridable; use: optional) - metric as a big didone numeral (counter-display) with an uppercase eyebrow label; echoes the ghost-numeral motif; open, never boxed
- `list` (designed, overridable; use: optional) - feature list as plain rows separated by 1px ruled bars (like the action rows); marker none/slash, never decorative bullets in colored chips
- `code` (designed, overridable; use: rare) - monospace snippet on the near-black inverse-strong surface, radius 0, no border; off-brand for a gallery, so rare
- `icon-button` (designed, overridable; use: never) - no icon buttons; an icon action remaps to a typographic arrow/slash link, consistent with no-buttons
- `video` (designed, overridable; use: optional) - treated exactly like image — hard-edged rectangle, radius 0, no chrome; landscape ratio
- `icon` (designed, overridable; use: rare) - thin monoline glyphs inheriting text color; no accent fills on light; used only where a slash/arrow can't stand in
- `avatar` (designed, overridable; use: optional) - person image as a hard-edged rectangle crop (radius 0) — the contract's round/circle default is overridden by no-radius
- `illustration` (designed, overridable; use: rare) - brand uses photography + ghost-watermark type, not illustration; if needed, a flat ghost-tone graphic with no gradients
- `pill` (designed, overridable; use: never) - no rounded chips; a tag/keyword remaps to an uppercase eyebrow label, never a pill
- `badge` (designed, overridable; use: rare) - flat square accent-on-dark marker (gold only on dark surfaces); never rounded or shadowed
- `rating` (designed, overridable; use: rare) - score as small monoline glyphs or a fraction numeral (echoing the observed 1/6 counter); no colored stars on cream
- `progress` (designed, overridable; use: rare) - thin square 1px bar with a solid fill, no rounding/gradient; spinner avoided (low motion)
- `tooltip` (designed, overridable; use: rare) - square dark panel, no shadow/radius, Inter micro-text; fade-free appearance (low motion)
- `spacer` (designed, overridable; use: optional) - explicit gaps use the editorial module-gap ladder; whitespace is structural and generous (low density)
- `textarea` (designed, overridable; use: when-form; variant: underline) - multi-line entry as a single underline rule, no box/fill, matching the Lead-form input
- `select` (designed, overridable; use: when-form; variant: underline) - dropdown as an underline trigger with uppercase control-text; menu is a flat square panel, no rounding
- `checkbox` (designed, overridable; use: when-form) - hard square box (radius 0), 1px hairline, solid check on select; no accent fill on cream
- `radio` (designed, overridable; use: when-form) - rendered as a small SQUARE selector (radius 0 overrides the round default); hairline + solid fill
- `toggle` (designed, overridable; use: when-form) - square sliding switch, no pill/rounding; on-state uses a flat dark fill, accent only on dark
- `slider` (designed, overridable; use: rare) - 1px square track with a square handle; no rounded thumb, no gradient track
- `file-upload` (designed, overridable; use: when-form) - underline-style trigger with an uppercase control-text label; no dashed rounded dropzone box

**Blocks** (8 extracted / 17 designed)
- `header` (extracted: opening-bookend, about-run, info-band, conversion; slots — eyebrow: optional, heading: require, subheading: optional, text: optional, cta: optional; refs: `neverDo.no-centered-everything`)
- `navbar` (extracted: opening-bookend; slots — logo: require, links: require, actions: optional; refs: `neverDo.no-buttons`)
- `footer` (extracted: closing-bookend; slots — logo: require, columns: optional, social: optional, legal: optional) - closing bookend on surface/inverse-strong; sitemap as oversized didone slash links; no boxes
- `media-text` (extracted: info-band; slots — media: require, content: require) - two flush halves, gap 0, hard cut; panel is the only cream-on-dark surface
- `content-block` (extracted: about-run; slots — header: optional, body: require, media: require, cta: optional) - loose single-column collage module: media + margin caption + offset body; alternating anchors over ghost watermark
- `cta-block` (extracted: conversion; slots — header: require, actions: require, media: omit) - narrow centered stack; action is a typographic arrow link or inline form submit
- `form` (extracted: conversion; slots — header: optional, fields: require, submit: require, note: optional; refs: `neverDo.no-boxed-inputs`, `neverDo.no-buttons`)
- `card` (extracted: about-run, info-band; slots — media: omit, heading: omit, text: omit; refs: `neverDo.no-cards-on-cream`)
- `testimonial` (designed, overridable) - quote as large didone type open on the canvas; name/role as margin eyebrow; avatar a hard rectangle crop; never a boxed/shadowed testimonial card
- `stat-block` (designed, overridable) - row of big didone numerals with uppercase eyebrow labels; echoes the ghost-numeral motif; open, no boxes or dividers between
- `accordion` (designed, overridable) - stacked didone triggers separated by 1px ruled bars (the action-row rule); no rounded panels; low-motion expand
- `accordion-item` (designed, overridable) - didone uppercase trigger + Inter body; slash/arrow indicator instead of a chevron chip
- `tabs` (designed, overridable) - triggers as uppercase typographic links with an underline active state; never pill/boxed tabs
- `logo-bar` (designed, overridable) - monochrome wordmarks in a flush row with an uppercase eyebrow caption; no card tiles or rounded frames
- `feature-item` (designed, overridable) - open grid cell: optional hard-edged image / thin icon + didone heading + body + arrow link; never a boxed feature card
- `pricing-card` (designed, overridable) - plan as a ruled action row (price numeral + uppercase label + arrow link), mirroring the observed TICKET PRICES rows; never a boxed pricing tile
- `banner` (designed, overridable) - slim full-width strip on a dark band; uppercase text + arrow link; dismiss as a typographic x/slash; no rounded pill, no accent on light
- `modal` (designed, overridable) - hard-edged square panel (radius 0, no shadow); flat scrim with no blur/gradient; close as a typographic x; low motion
- `dropdown-menu` (designed, overridable) - flat square menu panel, no rounding/shadow; items as uppercase typographic links; trigger is a slash/arrow link
- `breadcrumb` (designed, overridable) - uppercase Inter trail with the brand's slash separator (the ABOUT / GALLERY pattern); muted, typographic
- `pagination` (designed, overridable) - fraction-counter style (echoes the observed 1/6) with prev/next arrow links; no numbered button chips
- `table` (designed, overridable) - rows separated by 1px ruled bars (like the OPEN HOURS rows), uppercase eyebrow column headers; no zebra fills, boxed borders, or rounding
- `carousel` (designed, overridable) - hard-edged image track with a fraction counter (1/6) and arrow links for controls; low motion, no rounded dots/cards
- `steps` (designed, overridable) - ordered stages as big didone numerals + uppercase headings, separated by ruled bars; open, never boxed step cards
- `step-item` (designed, overridable) - number as a didone numeral, didone heading, Inter body; no circular numbered badge

## 13. Locked dials
- **VARIANCE: high**
- **MOTION: low** _(state: defined)_
- **DENSITY: low**

## Motion (authored spec)
Motion is an authored spec (state: defined); intensity stays `low` (calm/editorial) — no bounce, spring, overshoot, or snap.

- Easing (primary): `cubic-bezier(.22, 1, .36, 1)`
- Durations: fast `320ms`, base `480ms`, slow `620ms`
- Link interaction: **color-shift-to-gold**
- Scroll reveal: **fade-translateY** (translateY 16px)
- prefers-reduced-motion: **respect** (transitions/reveals disabled when the user requests reduced motion).

## 14. Recipe policy
- `scaffoldFirst`: True
- `reuseBeforeCreate`: True
- `composeFromPrimitives`: True
- `themeViaModes`: True
- `slotsTakeInstancesOnly`: True
- `magicTrick`: {'wildcardScope': {'value': 'hero-only', 'note': 'WILDCARD variant (C) may relax exactly one neverDo (scope:one-off) on HERO sections only (archetype hero / opening-bookend); every non-hero section enforces all neverDo.', 'confidence': 'high', 'source': 'creation', 'scope': 'design-language', 'changelog': []}}

## 15. Provenance & confidence ledger

Every asset and value below is **rendered**. These four buckets annotate how each fact was obtained and where a production swap may later be needed — a flag is never a replacement, substitution, or omission.

**Sampled (measured / extracted from source).** 11 color tokens, 10 type roles, 7 spacing steps carry evidence-backed provenance (see §3-§5).

**Assumed (designed or inferred — flagged, still rendered).**
- seam-bridging-photo: low confidence
- layout exhibition-schedule: medium confidence
- layout exhibition-tickets: medium confidence
- layout exhibition-faq: medium confidence
- 24 primitive(s): designed contract defaults (overridable; see §12)
- 17 block(s): designed contract defaults (overridable; see §12)

**Substitute (real family loaded; proxy is the fallback only).**
- `display-hero`, `h1`, `h2`, `h3`, `counter-display`, `ghost-watermark`, `footer-sitemap-link`: render `Melodrama`; proxy `Playfair Display` is the loaded fallback only.

**Needs-licensing (rendered as captured, flagged for production swap).**
- None flagged.

## 16. Section catalog (slot contracts)

Each layout as an abstract contract: archetype, surface intent, use case, and the slots it exposes (slot -> type -> use case -> contract).

### opening-bookend - stack (surface/inverse)

| slot | type | use case | contract |
|---|---|---|---|
| main | media | display title over layered photo collage | `logo, header, image` |

### editorial-collage - collage (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| main | media | loose single-column field of [media + micro-caption + offset paragraph] modules | `image, eyebrow, paragraph` |

### mission-statement - split (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| text | content | eyebrow -> heading -> body -> arrow action | `eyebrow, header, paragraph, link` |
| media | media | statement photography | `image` |

### gallery-showcase - stack-fullbleed (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| utility | content | eyebrow (far left) + static counter (far right) | `eyebrow, caption` |
| main | media | full-bleed interior photograph + margin caption | `image, caption` |

### heritage-timeline - collage (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| main | media | ghost year-range watermark behind heading + media + two dated captions | `eyebrow, header, image, paragraph, caption` |

### curator-quote - split (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| text | content | eyebrow -> quote-as-heading -> attribution body | `eyebrow, header, paragraph` |
| media | media | curator portrait + name caption | `image, caption` |

### info-band - split (surface/inverse)

| slot | type | use case | contract |
|---|---|---|---|
| media | media | flush hard-edged photo | `image` |
| panel | content | cream panel with title + ruled action rows | `header, link` |

### visit-band - split (surface/inverse)

| slot | type | use case | contract |
|---|---|---|---|
| intro | content | eyebrow -> band heading | `eyebrow, header` |
| media | media | static desaturated map with pin + margin caption | `image, caption` |
| tickets | content | cream panel: ticket prices, ruled rows, buy action | `header, link` |
| visit | content | cream panel: hours/address, rows, directions action | `header, link` |

### conversion-stack - stack (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| main | content | centered narrow column: eyebrow -> heading -> underline input | `eyebrow, header, form` |

### exhibition-hero - stack (surface/inverse)

| slot | type | use case | contract |
|---|---|---|---|
| main | media | display title over layered photo collage | `logo, header, image` |

### exhibition-about - collage (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| main | media | loose single-column field of [media + micro-caption + offset paragraph] modules | `image, eyebrow, paragraph` |

### exhibition-works - stack-fullbleed (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| utility | content | eyebrow (far left) + static counter (far right) | `eyebrow, caption` |
| main | media | full-bleed interior photograph + margin caption | `image, caption` |

### exhibition-schedule - stack (surface/inverse)

| slot | type | use case | contract |
|---|---|---|---|
| main | content | centered eyebrow -> heading -> ruled event/date rows | `eyebrow, header` |

### exhibition-tickets - stack (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| main | content | centered eyebrow -> heading -> intro -> ruled tier/price rows -> action | `eyebrow, header, link` |

### exhibition-curator-quote - split (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| text | content | eyebrow -> quote-as-heading -> attribution body | `eyebrow, header, paragraph` |
| media | media | curator portrait + name caption | `image, caption` |

### exhibition-faq - stack (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| main | content | centered eyebrow -> heading -> stacked disclosure Q&A rows | `eyebrow, header` |

### demo-staggered-cards - cards (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| cards | media | staggered feature card modules (image + tracked caption + short body) | `image, caption, paragraph` |

### demo-interlock-inset - interlock (surface/primary)

| slot | type | use case | contract |
|---|---|---|---|
| main | media | pinned caption + inset image floated right + wrapping statement heading | `caption, image, header` |

## 17. Layout patterns (project library)

Reusable, use-case-keyed layout patterns extracted from this project (project tier — wins over the standard library on ties). Sizes are relationships/classes, never px.

| pattern | use case | archetype | surface | special treatments | origin |
|---|---|---|---|---|---|
| `hero-display-over-staggered-media` | hero | stack | inverse | overlap, stagger | extracted |
| `editorial-ghostword-collage` | about | collage | primary | ghost-word, marginal-caption, stagger | extracted |
| `features-flush-split-panel` | features | split | inverse | bleed | extracted |
| `cta-underline-conversion-stack` | cta | stack | primary | - | extracted |
| `gallery-fullbleed-counter-band` | gallery | stack-fullbleed | primary | bleed, marginal-caption | extracted |
| `about-anchored-statement` | about | split | primary | stagger | extracted |
| `heritage-ghost-numerals-timeline` | about | collage | primary | ghost-word, marginal-caption, overlap | extracted |
| `curator-quote-portrait-collage` | testimonial | split | primary | marginal-caption | extracted |
| `visit-dual-panel-map` | features | split | inverse | marginal-caption, overlap | extracted |
| `features-staggered-caption-cards` | features | cards | primary | stagger | designed |
| `editorial-interlocking-inset` | about | interlock | primary | float-wrap, inset | designed |
| `pricing-ruled-list-panel` | pricing | stack | primary | - | designed |
| `schedule-ruled-list-panel` | features | stack | inverse | - | designed |
| `faq-accordion-list` | faq | stack | primary | - | designed |
| `logos-hairline-strip` | logos | row | primary | - | designed |
