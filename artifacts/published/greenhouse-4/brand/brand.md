# brand.md - www.greenhouse.com   <!-- rendered from brand.yaml v2.0 by render_brand_md.py; DO NOT EDIT -->

> Generated projection. Edit `brand.yaml` (canonical) and re-render; never hand-edit this file.

## 1. Brand snapshot
Greenhouse is greenhouse is a hiring platform whose marketing site presents itself as an end-to-end, AI-powered recruiting solution spanning sourcing to onboarding, anchored by the serif display line 'The only hiring platform you'll ever need' set in a deep forest green (#15372c) on a mint canvas (#cdeadf). The visual system pairs the Untitled Serif family for editorial headings with Untitled Sans for body and controls, uses rounded pill buttons in a primary green (#008561) and a blue demo-request accent (#3574d6), and closes pages on a dark green footer band with a 'Modern Recruiter newsletter' signup and a lowercase sprout 'g' wordmark.

## 2. Surface grammar
0 surface roles:

## 3. Color tokens (semantic role + value)

| token | value | role |
|---|---|---|
| `text/primary` | `#15372c` | primary body and heading ink on light surfaces |
| `text/on-inverse` | `#ffffff` | text on dark green bands and colored buttons |
| `surface/canvas` | `#ffffff` | default page canvas |
| `surface/mint` | `#cdeadf` | hero mint canvas |
| `surface/inverse` | `#15372c` | dark green bookend band and footer |
| `surface/muted` | `#f5f5f5` | light warm-grey feature/stat canvas |
| `accent/primary` | `#008561` | primary green action and text-link accent |
| `accent/blue` | `#3574d6` | demo-request call-to-action fill |
| `accent/green-hover` | `#006147` | green button hover / darker green |
| `accent/mint-soft` | `#c9f0e6` | soft mint inset panel on comparison card |
| `text/on-primary` | `#15372c` | primary body and heading ink on light surfaces |
| `text/on-primary-muted` | `rgba(21, 55, 44, 0.66)` | muted forest-green ink on light canvas (secondary/supporting text) |
| `text/on-inverse-muted` | `rgba(255, 255, 255, 0.72)` | muted text/link on dark forest-green bands and footer |
| `border/hairline-on-primary` | `rgba(21, 55, 44, 0.12)` | hairline divider/border on light canvas (logo-grid rule, card edges) |
| `text/ghost-on-primary` | `rgba(21, 55, 44, 0.06)` | ghost wash / faint fill on light canvas fallback |

## 4. Typography roles

| role | family | size (base) | line-height | weight | case |
|---|---|---|---|---|---|
| display-hero | 'Untitled Serif', Georgia, serif | 4.375rem | 1.05 | 400 | sentence |
| h2 | 'Untitled Serif', Georgia, serif | 2.875rem | 1.18 | 400 | sentence |
| h3 | 'Untitled Sans', Arial, sans-serif | 1.1875rem | 1.7 | 400 | none |
| h4 | 'Untitled Sans', Arial, Helvetica, sans-serif | 1.0rem | 1.5 | 600 | none |
| body | 'Untitled Sans', Arial, sans-serif | 1.1875rem | 1.7 | 400 | none |
| control-text | 'Untitled Sans', Arial, sans-serif | 0.9375rem | 1.0 | 400 | none |
| nav-link | 'Untitled Sans', Arial, sans-serif | 1.0rem | 1.6 | 400 | none |
| footer-sitemap-link | 'Untitled Serif', Georgia, sans-serif | 1.25rem | 1.3 | 400 | none |
| eyebrow | Untitled Sans | 0.875rem | 1.4em | 600 | sentence |
| h1 | 'Untitled Serif', Georgia, serif | 4.375rem | 1.05 | 400 | sentence |

## 5. Spacing system
- `section-padding-dark`: 6.25rem - footer band top padding (100px)
- `section-padding-light`: 7.5rem - contained feature/testimonial section top padding (~120-140px)
- `module-gap`: 2.5rem - inter-card column gap in 3-column grids (~40px)
- `heading-to-body`: 2.75rem - hero display to intro copy (~44px, home-section-00)
- `body-to-cta`: 3.75rem - intro copy to primary action row (~60px, home-section-00)
- `container-max`: 90rem - measured nav/footer/content container cap (1440px)
- `radius-global`: 24px - shared control and component radius
- `eyebrow-to-heading`: 1.5rem - eyebrow→heading gap (grounding gapPx ~24-28px)
- `panel-padding`: 2rem - card/panel inset (white product-UI card padding ~32px)

## 6. Layout grammar
- **Centered-Stack-With-Orbiting-Media** (hero, surface/primary): primary-heading.
- **Heading-Plus-Three-Column-Card-Grid** (featureGrid, surface/primary): section-heading.
- **Split-Copy-Plus-Logo-Grid** (logoWall, surface/primary): section-heading.
- **Three-Column-Numeric-Stat-Row** (stats, surface/primary): stat-column-list: figure plus description and source citation.
- **Three-Column-Text-Quote-Row** (testimonial, surface/primary): section-heading.
- **Full-Bleed-Dark-Band-Copy-Left-Art-Right** (cta, surface/inverse): section-heading.

## 7. Slot mapping (slot -> primitive/block contract)
### hero

| slot | role | contract |
|---|---|---|
| heading | primary-heading | `header` |
| body | intro-body | `content-block` |
| primaryAction | primary-action | `button` |
| ghostAction | secondary-action | `button` |
| mediaCluster | decorative-media-cluster | `image` |
| portraitMedia | supporting-portrait | `image` |

### featureGrid

| slot | role | contract |
|---|---|---|
| sectionHeading | section-heading | `header` |
| cardMedia | card-media | `image` |
| cardHeading | card-heading | `card` |
| cardBody | card-body | `card` |
| cardAction | card-action | `card` |

### logoWall

| slot | role | contract |
|---|---|---|
| heading | section-heading | `header` |
| primaryAction | primary-action | `button` |
| logoGrid | logo-grid | `logo-bar` |

### stats

| slot | role | contract |
|---|---|---|
| statNumber | stat-figure | `stat-block` |
| statBody | stat-body | `stat-block` |
| statAction | stat-action | `stat-block` |

### testimonial

| slot | role | contract |
|---|---|---|
| heading | section-heading | `header` |
| quoteBody | quote-body | `testimonial` |
| authorName | author-name | `content-block` |
| authorRole | author-caption | `content-block` |

### cta

| slot | role | contract |
|---|---|---|
| heading | section-heading | `header` |
| primaryAction | primary-action | `button` |
| decorativeArt | decorative-background-art | `image` |

## 8. Composition mechanics

## 9. Do
- None.

## 10. Avoid
- None.

## 11. Never-do

## 12. Primitive & block rules

**Primitives** (13 extracted / 23 designed)
- `heading` (extracted: brand.yaml#measured-block-slots)
- `subheading` (designed, overridable) - No subheading was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `eyebrow` (designed, overridable) - No eyebrow was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `paragraph` (extracted: brand.yaml#measured-block-slots)
- `label` (designed, overridable) - No label was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `button` (extracted: evidence/grounding/*.yaml#components[])
- `link` (extracted: evidence/grounding/*.yaml#components[])
- `cta` (designed, overridable) - No cta was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `image` (designed, overridable) - No image was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `icon` (extracted: evidence/grounding/*.yaml#components[])
- `logo` (extracted: brand.yaml#measured-block-slots)
- `pill` (extracted: evidence/grounding/*.yaml#components[])
- `badge` (extracted: evidence/grounding/*.yaml#components[])
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
- `list` (designed, overridable) - No list was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `code` (designed, overridable) - No code was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `icon-button` (designed, overridable) - No icon-button was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `illustration` (designed, overridable) - No illustration was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `progress` (designed, overridable) - No progress was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `tooltip` (designed, overridable) - No tooltip was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `spacer` (designed, overridable) - No spacer was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `textarea` (designed, overridable) - No textarea was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `slider` (designed, overridable) - No slider was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `file-upload` (designed, overridable) - No file-upload was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, border / shadow grammar, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.

**Blocks** (3 extracted / 22 designed)
- `hero`
- `featureGrid`
- `logoWall`
- `stats`
- `testimonial` (extracted: brand.yaml#measured-block-archetypes)
- `cta`
- `footer` (extracted: brand.yaml#measured-block-archetypes)
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
Motion is an authored spec; intensity stays `{}` (calm/editorial) — no bounce, spring, overshoot, or snap.

- Easing (primary): `cubic-bezier(0.645, 0.045, 0.355, 1)`
- Durations: fast `150ms`, base `300ms`, slow `500ms`
- prefers-reduced-motion: **declared** (transitions/reveals disabled when the user requests reduced motion).

## 14. Recipe policy

## 15. Provenance & confidence ledger

Every asset and value below is **rendered**. These four buckets annotate how each fact was obtained and where a production swap may later be needed — a flag is never a replacement, substitution, or omission.

**Sampled (measured / extracted from source).** 15 color tokens, 10 type roles, 9 spacing steps carry evidence-backed provenance (see §3-§5).

**Assumed (designed or inferred — flagged, still rendered).**
- 23 primitive(s): designed contract defaults (overridable; see §12)
- 22 block(s): designed contract defaults (overridable; see §12)

**Substitute (real family loaded; proxy is the fallback only).**
- None — every type role renders its real family.

**Needs-licensing (rendered as captured, flagged for production swap).**
- None flagged.

## 16. Section catalog (slot contracts)

Each layout as an abstract contract: archetype, surface intent, use case, and the slots it exposes (slot -> type -> use case -> contract).

### hero - centered-stack-with-orbiting-media (surface/primary)

hero

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | primary-heading | `header` |
| body | content | intro-body | `content-block` |
| primaryAction | action | primary-action | `button` |
| ghostAction | action | secondary-action | `button` |
| mediaCluster | media | decorative-media-cluster | `image` |

### featureGrid - heading-plus-three-column-card-grid (surface/primary)

features

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | section-heading | `` |
| itemMedia | image | card-media-well | `` |
| items | content | feature-card-list (media-well -> heading -> body -> action) | `` |

### logoWall - split-copy-plus-logo-grid (surface/primary)

logos

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | section-heading | `header` |
| primaryAction | action | primary-action | `button` |
| logoGrid | logo | logo-grid | `logo-bar` |

### stats - three-column-numeric-stat-row (surface/primary)

stats

| slot | type | use case | contract |
|---|---|---|---|
| items | content | stat-column-list: figure plus description and source citation | `` |

### testimonial - three-column-text-quote-row (surface/primary)

testimonial

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | section-heading | `header` |
| items | content | testimonial-card-list (quote -> name -> meta) | `` |

### cta - full-bleed-dark-band-copy-left-art-right (surface/inverse)

cta

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | section-heading | `header` |
| primaryAction | action | primary-action | `button` |
