# brand.md - www.greenhouse.com   <!-- rendered from brand.yaml v2.0 by render_brand_md.py; DO NOT EDIT -->

> Generated projection. Edit `brand.yaml` (canonical) and re-render; never hand-edit this file.

## 1. Brand snapshot
Greenhouse is greenhouse is a hiring platform whose marketing site pairs a warm sage-green canvas with a deep forest-green ink (#15372c) and a confident emerald accent (#008561), using the Untitled Serif family for large editorial display and headings and Untitled Sans for body, navigation and controls. Its interface language is built from fully rounded pill buttons (24-25px radius) in green, blue and outline variants, generous section padding, floating white product-UI cards over tinted panels, and dark forest-green bookend bands for CTA and footer regions.

## Signature moves — the rules that carry the look

The recognizable moves that make this brand identifiable, projected from `brand.yaml` `signatures:` (each is a machine-checkable claim the `signature_check` gate verifies). Rebuild the look from these first.

- Fully rounded pill action buttons (24-25px radius) in emerald green, blue and outline variants
- Large Untitled Serif sentence-case display headings with tight negative tracking on a sage/mint canvas
- Dark forest-green (#15372c) bookend bands for CTA and footer, with decorative fingerprint-leaf line art
- Floating white product-UI cards and circle-cropped portraits scattered over tinted panels
- Circular emerald brand badge with a lowercase g glyph

## 2. Surface grammar
4 surface roles:
- `surface/primary` - bg `#ffffff`, intent `default canvas`, text `text/primary`, accent `accent/primary`
- `surface/tint` - bg `#c9f0e6`, intent `mint card panel`, text `text/primary`, accent `accent/primary`
- `surface/muted` - bg `#f5f5f5`, intent `neutral grey feature panel`, text `text/primary`
- `surface/inverse` - bg `#15372c`, intent `dark forest-green bookend band and footer`, text `text/on-inverse`, accent `accent/soft`

## 3. Color tokens (semantic role + value)

| token | value | role |
|---|---|---|
| `text/primary` | `#15372c` | primary forest-green ink on light canvas |
| `text/on-inverse` | `#ffffff` | body and link text on dark green bands |
| `accent/primary` | `#008561` | primary emerald action fill and link ink |
| `accent/secondary` | `#3574d6` | blue demo-request action fill |
| `accent/soft` | `#4cb398` | lighter green hover/hover-border tint |
| `surface/canvas` | `#ffffff` | default page canvas |
| `surface/tint` | `#c9f0e6` | mint tinted card/panel fill |
| `surface/inverse` | `#15372c` | dark forest-green bookend band and footer |
| `surface/muted` | `#f5f5f5` | neutral grey section panel |
| `text/on-primary` | `#15372c` | primary forest-green ink on light canvas |
| `text/on-primary-muted` | `rgba(21, 55, 44, 0.66)` | muted forest-green ink on light canvas (secondary/supporting text) |
| `text/on-inverse-muted` | `rgba(255, 255, 255, 0.72)` | muted text/link on dark forest-green bands and footer |
| `border/hairline-on-primary` | `rgba(21, 55, 44, 0.12)` | hairline divider/border on light canvas (logo-grid rule, card edges) |
| `text/ghost-on-primary` | `rgba(21, 55, 44, 0.06)` | ghost wash / faint fill on light canvas fallback |

## 4. Typography roles

| role | family | size (base) | line-height | weight | case |
|---|---|---|---|---|---|
| display-hero | Untitled Serif, Georgia, sans-serif | 4.375rem | 1.05 | 400 | sentence |
| h1 | Untitled Serif, Georgia, sans-serif | 4.375rem | 1.05 | 400 | sentence |
| h2 | Untitled Serif, Georgia, sans-serif | 2.875rem | 1.18 | 400 | sentence |
| h3 | Untitled Sans, Arial, sans-serif | 1.1875rem | 1.7 | 400 | sentence |
| h4 | Untitled Sans, Arial, Helvetica, sans-serif | 1.0rem | 1.5 | 600 | sentence |
| body | Untitled Sans, Arial, sans-serif | 1.1875rem | 1.7 | 400 | sentence |
| control-text | Untitled Sans, Arial, sans-serif | 0.9375rem | 1.0 | 400 | sentence |
| nav-link | Untitled Sans, Arial, sans-serif | 1.0rem | 1.6 | 400 | sentence |
| footer-sitemap-link | Untitled Serif, Georgia, sans-serif | 1.25rem | 1.3 | 400 | sentence |
| eyebrow | Untitled Sans | 0.875rem | 1.4em | 600 | sentence |

## 5. Spacing system
- `section-padding-light`: 8.125rem - contained feature section top/bottom padding
- `section-padding-band`: 12.5rem - dark CTA band vertical padding
- `footer-padding`: 6.25rem - footer top padding above sitemap
- `module-gap`: 3.75rem - column gap between feature cards
- `heading-to-body`: 2.75rem - grounding headingToBody 44px
- `body-to-cta`: 3.75rem - grounding bodyToCta 60px
- `container-max`: 90rem
- `container-span`: min(100cqw, 90rem)
- `radius-global`: 24px - shared control and component radius
- `eyebrow-to-heading`: 1.5rem - eyebrow→heading gap (grounding gapPx ~24-28px)
- `panel-padding`: 2rem - card/panel inset (white product-UI card padding ~32px)

## 6. Layout grammar
- **Centered-Copy-With-Floating-Media** (hero, surface/tint): primary-heading.
- **Three-Column-Media-Top-Cards** (featureGrid, surface/primary): section-heading.
- **Split-Copy-And-Logo-Grid** (logos, surface/primary): section-heading.
- **Pill-Filtered-Comparison-Card** (comparison, surface/tint): eyebrow.
- **Three-Column-Number-Over-Caption** (stats, surface/muted): stat-column-list: figure plus description and source citation.
- **Three-Column-Quote-Blocks** (testimonial, surface/primary): section-heading.
- **Copy-Left-Decorative-Art-Right** (ctaBand, surface/inverse): band-heading.

## 7. Slot mapping (slot -> primitive/block contract)
### hero

| slot | role | contract |
|---|---|---|
| heading | primary-heading | `header` |
| body | supporting-body | `content-block` |
| primaryCta | primary-action | `button` |
| ghostCta | secondary-action | `button` |
| floatingPortraits | decorative-media-collage | `image` |

### featureGrid

| slot | role | contract |
|---|---|---|
| heading | section-heading | `header` |
| itemMedia | card-media-well | `image` |
| items | feature-card-list (media-well -> heading -> body -> action) | `image` |

### logos

| slot | role | contract |
|---|---|---|
| heading | section-heading | `header` |
| cta | primary-action | `button` |
| logoGrid | partner-logo-wall | `logo-bar` |

### comparison

| slot | role | contract |
|---|---|---|
| eyebrow | eyebrow | `header` |
| heading | section-heading | `header` |
| subhead | subheading | `header` |
| body | supporting-body | `content-block` |
| filters | filter-action-group | `button` |
| comparisonRows | comparison-list | `content-block` |
| mediaPanel | decorative-media-well | `image` |
| awardBadge | review-award-badge | `logo-bar` |

### stats

| slot | role | contract |
|---|---|---|
| items | stat-column-list: figure plus description and source citation | `stat-block` |

### testimonial

| slot | role | contract |
|---|---|---|
| heading | section-heading | `header` |
| items | testimonial-card-list (quote -> name -> meta) | `card` |

### ctaBand

| slot | role | contract |
|---|---|---|
| heading | band-heading | `header` |
| cta | primary-action | `button` |

## 8. Composition mechanics

## 9. Do
- None.

## 10. Avoid
- None.

## 11. Never-do

## 12. Primitive & block rules

**Primitives** (17 extracted / 19 designed)
- `heading` (extracted: brand.yaml#measured-block-slots)
- `subheading` (extracted: brand.yaml#measured-block-slots)
- `eyebrow` (extracted: brand.yaml#measured-block-slots)
- `paragraph` (extracted: brand.yaml#measured-block-slots)
- `label` (designed, overridable) - No label was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `button` (extracted: evidence/grounding/*.yaml#components[])
- `link` (extracted: evidence/grounding/*.yaml#components[])
- `cta` (extracted: brand.yaml#measured-block-slots)
- `image` (designed, overridable) - No image was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `icon` (extracted: evidence/grounding/*.yaml#components[])
- `logo` (extracted: brand.yaml#measured-block-slots)
- `pill` (extracted: brand.yaml#measured-block-slots)
- `badge` (extracted: brand.yaml#measured-block-slots)
- `input` (extracted: evidence/grounding/*.yaml#components[])
- `form-field` (designed, overridable) - No form-field was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `toggle` (designed, overridable) - No toggle was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `select` (designed, overridable) - No select was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `checkbox` (designed, overridable) - No checkbox was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `radio` (designed, overridable) - No radio was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `quote` (extracted: brand.yaml#measured-block-slots)
- `avatar` (extracted: evidence/grounding/*.yaml#components[])
- `rating` (designed, overridable) - No rating was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `video` (designed, overridable) - No video was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `divider` (designed, overridable) - No divider was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `stat` (extracted: brand.yaml#measured-block-slots)
- `caption` (extracted: brand.yaml#measured-block-slots)
- `list` (extracted: brand.yaml#measured-block-slots)
- `code` (designed, overridable) - No code was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `icon-button` (designed, overridable) - No icon-button was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `illustration` (designed, overridable) - No illustration was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `progress` (designed, overridable) - No progress was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `tooltip` (designed, overridable) - No tooltip was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `spacer` (designed, overridable) - No spacer was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `textarea` (designed, overridable) - No textarea was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `slider` (designed, overridable) - No slider was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `file-upload` (designed, overridable) - No file-upload was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.

**Blocks** (1 extracted / 30 designed)
- `hero` (designed, overridable) - No hero was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `featureGrid` (designed, overridable) - No featureGrid was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `logos` (designed, overridable) - No logos was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `comparison` (designed, overridable) - No comparison was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `stats` (designed, overridable) - No stats was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `testimonial` (designed, overridable) - No testimonial was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `ctaBand` (designed, overridable) - No ctaBand was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `footer` (designed, overridable) - No footer was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `header` (designed, overridable) - No header was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `content-block` (designed, overridable) - No content-block was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `card` (extracted: evidence/grounding/*.yaml#components[])
- `form` (designed, overridable) - No form was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `stat-block` (designed, overridable) - No stat-block was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `navbar` (designed, overridable) - No navbar was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `accordion` (designed, overridable) - No accordion was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `accordion-item` (designed, overridable) - No accordion-item was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `tabs` (designed, overridable) - No tabs was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `logo-bar` (designed, overridable) - No logo-bar was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `feature-item` (designed, overridable) - No feature-item was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `pricing-card` (designed, overridable) - No pricing-card was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `banner` (designed, overridable) - No banner was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `modal` (designed, overridable) - No modal was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `dropdown-menu` (designed, overridable) - No dropdown-menu was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `breadcrumb` (designed, overridable) - No breadcrumb was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `pagination` (designed, overridable) - No pagination was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `table` (designed, overridable) - No table was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `carousel` (designed, overridable) - No carousel was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `steps` (designed, overridable) - No steps was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `step-item` (designed, overridable) - No step-item was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `cta-block` (designed, overridable) - No cta-block was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `media-text` (designed, overridable) - No media-text was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.

## 13. Locked dials

## Motion (authored spec)
Motion is an authored spec; intensity stays `low` (calm/editorial) — no bounce, spring, overshoot, or snap.

- Easing (primary): `cubic-bezier(0.645, 0.045, 0.355, 1)`
- Durations: fast `150ms`, base `300ms`, slow `500ms`
- prefers-reduced-motion: **declared** (transitions/reveals disabled when the user requests reduced motion).

## 14. Recipe policy

## 15. Provenance & confidence ledger

Every asset and value below is **rendered**. These four buckets annotate how each fact was obtained and where a production swap may later be needed — a flag is never a replacement, substitution, or omission.

**Sampled (measured / extracted from source).** 14 color tokens, 10 type roles, 11 spacing steps carry evidence-backed provenance (see §3-§5).

**Assumed (designed or inferred — flagged, still rendered).**
- 19 primitive(s): designed contract defaults (overridable; see §12)
- 30 block(s): designed contract defaults (overridable; see §12)

**Substitute (real family loaded; proxy is the fallback only).**
- None — every type role renders its real family.

**Needs-licensing (rendered as captured, flagged for production swap).**
- 14 third-party mark(s) in `media-assets.yaml` (`usageRights: third-party-mark`) — rendered as captured, flagged for a licensed swap; never auto-substituted.

## 16. Section catalog (slot contracts)

Each layout as an abstract contract: archetype, surface intent, use case, and the slots it exposes (slot -> type -> use case -> contract).

### hero - centered-copy-with-floating-media (surface/tint)

Full-bleed opening hero: centered copy stack in the middle with floating portrait photos and product-UI chips scattered left/right over a mint canvas, navbar pinned top.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | primary-heading | `header` |
| body | content | supporting-body | `content-block` |
| primaryCta | action | primary-action | `button` |
| ghostCta | action | secondary-action | `button` |
| floatingPortraits | image | decorative-media-collage | `image` |

### featureGrid - three-column-media-top-cards (surface/primary)

Heading full-width top, then a 3-up card row below; each card: media-well top -> serif heading -> body -> trailing text link/CTA.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | section-heading | `header` |
| itemMedia | image | card-media-well | `image` |
| items | content | feature-card-list (media-well -> heading -> body -> action) | `image` |

### logos - split-copy-and-logo-grid (surface/primary)

Split ~50/50 band: copy left (heading + primary CTA) and a 2-column brand logo grid right, divided by a vertical rule.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | section-heading | `header` |
| cta | action | primary-action | `button` |
| logoGrid | logo | partner-logo-wall | `logo-bar` |

### comparison - pill-filtered-comparison-card (surface/tint)

Heading + body top, a pill filter row, then a split comparison card left and a decorative media panel right with a review-award badge.

| slot | type | use case | contract |
|---|---|---|---|
| eyebrow | content | eyebrow | `header` |
| heading | content | section-heading | `header` |
| subhead | content | subheading | `header` |
| body | content | supporting-body | `content-block` |
| filters | action | filter-action-group | `button` |
| comparisonRows | content | comparison-list | `content-block` |
| mediaPanel | media | decorative-media-well | `image` |
| awardBadge | image | review-award-badge | `logo-bar` |

### stats - three-column-number-over-caption (surface/muted)

Three equal centered columns; each column: big serif number -> description -> underlined text link.

| slot | type | use case | contract |
|---|---|---|---|
| items | content | stat-column-list: figure plus description and source citation | `stat-block` |

### testimonial - three-column-quote-blocks (surface/primary)

Heading top-left, then a 3-column testimonial row below; each column: opening quote mark -> quote body -> attribution name -> role meta caption.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | section-heading | `header` |
| items | content | testimonial-card-list (quote -> name -> meta) | `card` |

### ctaBand - copy-left-decorative-art-right (surface/inverse)

Full-bleed dark forest-green closing band: copy left (heading + filled CTA), decorative fingerprint-flower line art right.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | band-heading | `header` |
| cta | action | primary-action | `button` |

## 17. Layout patterns (project library)

Reusable, use-case-keyed layout patterns extracted from this project (project tier — wins over the standard library on ties). Sizes are relationships/classes, never px.

| pattern | use case | archetype | surface | special treatments | origin |
|---|---|---|---|---|---|
| `hero` | Full-bleed opening hero: centered copy stack in the middle with floating portrait photos and product-UI chips scattered left/right over a mint canvas, navbar pinned top. | centered-copy-with-floating-media | surface/tint | floating-media-collage, staged-scroll-reveal, text-on-canvas |  |
| `featureGrid` | Heading full-width top, then a 3-up card row below; each card: media-well top -> serif heading -> body -> trailing text link/CTA. | three-column-media-top-cards | surface/primary | media-top-card, repeated-3-up |  |
| `logos` | Split ~50/50 band: copy left (heading + primary CTA) and a 2-column brand logo grid right, divided by a vertical rule. | split-copy-and-logo-grid | surface/primary | logo-wall, vertical-divider-rule |  |
| `comparison` | Heading + body top, a pill filter row, then a split comparison card left and a decorative media panel right with a review-award badge. | pill-filtered-comparison-card | surface/tint | pill-filter-state-swap, text-on-media |  |
| `stats` | Three equal centered columns; each column: big serif number -> description -> underlined text link. | three-column-number-over-caption | surface/muted | centered-columns, number-over-caption |  |
| `testimonial` | Heading top-left, then a 3-column testimonial row below; each column: opening quote mark -> quote body -> attribution name -> role meta caption. | three-column-quote-blocks | surface/primary | quote-block, repeated-3-up |  |
| `ctaBand` | Full-bleed dark forest-green closing band: copy left (heading + filled CTA), decorative fingerprint-flower line art right. | copy-left-decorative-art-right | surface/inverse | decorative-line-art, inverse-closing-band |  |

## 18. Component recipes

Recurring multi-slot anatomies this brand reuses across sections — recorded as first-class recipes in `layout-library.yaml` `recipes:` so generators compose them as units instead of re-deriving the parts.

### `media-top-card-with-trailing-action` — media-top-card-with-trailing-action


### `number-over-caption-with-link` — number-over-caption-with-link
