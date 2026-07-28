# brand.md - www.hubspot.com   <!-- rendered from brand.yaml v2.0 by render_brand_md.py; DO NOT EDIT -->

> Generated projection. Edit `brand.yaml` (canonical) and re-render; never hand-edit this file.

## 1. Brand snapshot
HubSpot is hubSpot presents itself as an agentic customer platform that unites marketing, sales, and customer service around one Smart CRM, anchored by the hero promise "Where go-to-market teams go to grow." The identity pairs a warm cream-and-ink palette with a single high-energy orange accent (#ff4800), setting large humanist serif display headlines against a clean HubSpot Sans body voice, and it leans on social proof — 299,000+ customers in over 135 countries and #1 rankings across 526 G2 reports.

## Signature moves — the rules that carry the look

The recognizable moves that make this brand identifiable, projected from `brand.yaml` `signatures:` (each is a machine-checkable claim the `signature_check` gate verifies). Rebuild the look from these first.

- orange period accent (#ff4800) closing display headlines
- warm cream-on-dark-teal bookend bands framing badges and the closing CTA
- humanist serif display over HubSpot Sans light body
- dual filled+outlined orange CTA pairing (Get a demo / Get started free)
- white cards with 8-12px radius and hairline borders on warm canvas

## 2. Surface grammar
0 surface roles:

## 3. Color tokens (semantic role + value)

| token | value | role |
|---|---|---|
| `surface/primary` | `#fcfcfa` | default warm canvas background |
| `surface/white` | `#ffffff` | card and header surface |
| `surface/inverse` | `#1f1f1f` | dark footer band |
| `surface/inverse-teal` | `#002b28` | dark teal bookend / elevated CTA band |
| `accent/primary` | `#ff4800` | primary action + orange period accent |
| `accent/primary-hover` | `#c93700` | darker orange hover/pressed accent |
| `text/primary` | `#1f1f1f` | body and heading ink on light |
| `text/on-inverse` | `#f8f5ee` | cream ink on dark surfaces |
| `text/on-inverse-muted` | `rgba(255, 255, 255, 0.62)` | muted footer link ink |
| `surface/cream` | `#f8f5ee` | warm cream display ink / soft band |
| `text/on-primary` | `#1f1f1f` | body and heading ink on light |
| `text/secondary` | `rgba(0, 0, 0, 0.6196078431)` | measured secondary ink on light |
| `border/subtle` | `rgba(0, 0, 0, 0.1098039216)` | measured subtle control/card border |
| `text/on-primary-muted` | `rgba(0, 0, 0, 0.6196078431)` | measured secondary ink on light |
| `border/hairline-on-primary` | `rgba(0, 0, 0, 0.1098039216)` | measured subtle control/card border |
| `text/ghost-on-primary` | `rgba(0, 0, 0, 0.6196078431)` | measured secondary ink on light |
| `surface/accent-soft` | `#fcded2` | soft accent canvas |

## 4. Typography roles

| role | family | size (base) | line-height | weight | case |
|---|---|---|---|---|---|
| display-hero | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | 5rem | 1.15 | 500 | sentence |
| h1 | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | 3rem | 1.15 | 500 | sentence |
| h2 | "HubSpot Serif Page Header Human", "HubSpot Serif", serif | 2.5rem | 1.1 | 500 | sentence |
| h3 | "HubSpot Sans", sans-serif | 1.5rem | 1.42 | 500 | sentence |
| h4 | "HubSpot Sans", sans-serif | 1.375rem | 1.45 | 500 | sentence |
| h5 | "HubSpot Sans", sans-serif | 1.125rem | 1.56 | 500 | sentence |
| h6 | "HubSpot Sans", sans-serif | 1rem | 1.75 | 500 | sentence |
| body | "HubSpot Sans", sans-serif | 1rem | 1.75 | 300 | none |
| small | "HubSpot Sans", sans-serif | 0.875rem | 1.57 | 300 | none |
| micro | "HubSpot Sans", sans-serif | 0.75rem | 1.5 | 400 | none |
| eyebrow | "HubSpot Sans", sans-serif | 0.8125rem | 1.5 | 700 | uppercase |
| control-text | "HubSpot Sans", sans-serif | 0.875rem | 1.57 | 500 | none |
| footer-sitemap-link | "HubSpot Sans", sans-serif | 0.75rem | 2.4 | 500 | none |

## 5. Spacing system
- `section-padding-light`: 4rem - vertical section padding on light canvas
- `footer-padding`: 3rem - footer band padding (48px 32px)
- `module-gap`: 2.5rem - gap between header stack and content
- `eyebrow-to-heading`: 1.25rem
- `heading-to-body`: 2.5rem
- `body-to-cta`: 2.5rem
- `container-max`: 67.5rem
- `container-span`: min(75cqw, 67.5rem)
- `block-to-block`: 0.75rem - content-block row rhythm
- `column-to-column`: 1.5rem - measured split-column gutter
- `radius-global`: 8px - shared control and component radius
- `panel-padding`: 1.5rem - measured panel/card inner padding

## 6. Layout grammar
- **Overlay** (full-bleed-photo-hero, surface/inverse-teal): eyebrow.
- **Row** (centered-heading-over-logo-row, surface/primary): h2.
- **Split** (copy-left-illustration-right-carousel, surface/primary): h2.
- **Split** (sticky-copy-with-card-grid, surface/primary): eyebrow.
- **Band** (headrail-split-with-card-carousel, surface/accent-soft): section-headrail.
- **Split** (copy-left-logo-collage-inset, surface/primary): h2.
- **Band** (headrail-two-col-header, surface/primary): section-headrail.
- **Split** (tabbed-testimonial-with-stats, surface/primary): tab-row.
- **Row** (heading-left-award-badges-right, surface/primary): h2.
- **Band** (dark-band-cta, surface/inverse-teal): display.

## 7. Slot mapping (slot -> primitive/block contract)
### full-bleed-photo-hero

| slot | role | contract |
|---|---|---|
| eyebrow | eyebrow | `header` |
| heading | display | `header` |
| body | body | `content-block` |
| actions | action-group | `button` |
| background-media | background-media | `image` |
| utility-card | floating-card | `card` |

### centered-heading-over-logo-row

| slot | role | contract |
|---|---|---|
| heading | h2 | `header` |
| logo-row | mark-row | `logo-bar` |

### copy-left-illustration-right-carousel

| slot | role | contract |
|---|---|---|
| heading | h2 | `header` |
| subheading | body | `header` |
| item-heading | h3 | `header` |
| item-body | body | `content-block` |
| illustration | illustration-media | `image` |
| carousel-nav | carousel-control | `content-block` |

### sticky-copy-with-card-grid

| slot | role | contract |
|---|---|---|
| eyebrow | eyebrow | `header` |
| heading | display | `header` |
| body | body | `content-block` |
| actions | action-group | `button` |
| card-grid | card-grid | `card` |

### headrail-split-with-card-carousel

| slot | role | contract |
|---|---|---|
| headrail | section-headrail | `content-block` |
| heading | h2 | `header` |
| body | body | `content-block` |
| card-carousel | card-carousel | `card` |

### copy-left-logo-collage-inset

| slot | role | contract |
|---|---|---|
| heading | h2 | `header` |
| link | text-underline-link | `button` |
| logo-collage | mark-collage | `logo-bar` |

### headrail-two-col-header

| slot | role | contract |
|---|---|---|
| headrail | section-headrail | `content-block` |
| heading | display | `header` |
| body | body | `content-block` |

### tabbed-testimonial-with-stats

| slot | role | contract |
|---|---|---|
| tab-row | tab-row | `tabs` |
| portrait | portrait-media | `image` |
| quote | body | `testimonial` |
| attribution | caption | `content-block` |
| link | text-underline-link | `button` |
| stat-row | stat-row | `stat-block` |

### heading-left-award-badges-right

| slot | role | contract |
|---|---|---|
| heading | h2 | `header` |
| badge-row | mark-row | `logo-bar` |

### dark-band-cta

| slot | role | contract |
|---|---|---|
| heading | display | `header` |
| actions | action-group | `button` |

## 8. Composition mechanics

## 9. Do
- None.

## 10. Avoid
- None.

## 11. Never-do

## 12. Primitive & block rules

**Primitives** (16 extracted / 20 designed)
- `heading` (extracted: brand.yaml#measured-block-slots)
- `subheading` (extracted: brand.yaml#measured-block-slots)
- `eyebrow` (extracted: brand.yaml#measured-block-slots)
- `paragraph` (extracted: brand.yaml#measured-block-slots)
- `label` (designed, overridable) - No label was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `button` (extracted: evidence/grounding/*.yaml#components[])
- `link` (extracted: evidence/grounding/*.yaml#components[])
- `cta` (extracted: brand.yaml#measured-block-slots)
- `image` (designed, overridable) - No image was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `icon` (extracted: evidence/grounding/*.yaml#components[])
- `logo` (extracted: brand.yaml#measured-block-slots)
- `pill` (extracted: evidence/grounding/*.yaml#components[])
- `badge` (extracted: evidence/grounding/*.yaml#components[])
- `input` (designed, overridable) - No input was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `form-field` (designed, overridable) - No form-field was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `toggle` (designed, overridable) - No toggle was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `select` (designed, overridable) - No select was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `checkbox` (designed, overridable) - No checkbox was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `radio` (designed, overridable) - No radio was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `quote` (extracted: brand.yaml#measured-block-slots)
- `avatar` (extracted: evidence/grounding/*.yaml#components[])
- `rating` (designed, overridable) - No rating was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `video` (designed, overridable) - No video was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `divider` (designed, overridable) - No divider was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `stat` (extracted: evidence/grounding/*.yaml#components[])
- `caption` (extracted: brand.yaml#measured-block-slots)
- `list` (designed, overridable) - No list was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `code` (designed, overridable) - No code was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `icon-button` (designed, overridable) - No icon-button was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `illustration` (extracted: brand.yaml#measured-block-slots)
- `progress` (designed, overridable) - No progress was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `tooltip` (designed, overridable) - No tooltip was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `spacer` (designed, overridable) - No spacer was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `textarea` (designed, overridable) - No textarea was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `slider` (designed, overridable) - No slider was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `file-upload` (designed, overridable) - No file-upload was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.

**Blocks** (10 extracted / 22 designed)
- `hero` (extracted: section-00)
- `logoStrip` (extracted: section-01)
- `featureSplit` (extracted: section-02, section-04)
- `featureGrid` (extracted: section-03)
- `integrations` (extracted: section-05)
- `testimonial` (extracted: section-07)
- `badges` (extracted: section-08)
- `elevatedCta` (extracted: section-09)
- `footer` (extracted: section-10)
- `header` (designed, overridable) - No header was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `content-block` (designed, overridable) - No content-block was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `card` (extracted: evidence/grounding/*.yaml#components[])
- `form` (designed, overridable) - No form was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `stat-block` (designed, overridable) - No stat-block was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `navbar` (designed, overridable) - No navbar was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `accordion` (designed, overridable) - No accordion was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `accordion-item` (designed, overridable) - No accordion-item was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `tabs` (designed, overridable) - No tabs was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `logo-bar` (designed, overridable) - No logo-bar was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `feature-item` (designed, overridable) - No feature-item was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `pricing-card` (designed, overridable) - No pricing-card was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `banner` (designed, overridable) - No banner was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `modal` (designed, overridable) - No modal was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `dropdown-menu` (designed, overridable) - No dropdown-menu was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `breadcrumb` (designed, overridable) - No breadcrumb was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `pagination` (designed, overridable) - No pagination was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `table` (designed, overridable) - No table was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `carousel` (designed, overridable) - No carousel was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `steps` (designed, overridable) - No steps was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `step-item` (designed, overridable) - No step-item was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `cta-block` (designed, overridable) - No cta-block was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.
- `media-text` (designed, overridable) - No media-text was observed on the source page; synthesized on-brand from measured signals (color token families, measured type scale, relational spacing ladder, surface-role grammar, motion duration / easing axis, button family + state facts, brand signatures). Not used in the measured replica.

## 13. Locked dials

## Motion (authored spec)
Motion is an authored spec; intensity stays `low` (calm/editorial) — no bounce, spring, overshoot, or snap.

- Easing (primary): `ease`
- Durations: fast `150ms`, base `300ms`, slow `500ms`

## 14. Recipe policy

## 15. Provenance & confidence ledger

Every asset and value below is **rendered**. These four buckets annotate how each fact was obtained and where a production swap may later be needed — a flag is never a replacement, substitution, or omission.

**Sampled (measured / extracted from source).** 17 color tokens, 13 type roles, 12 spacing steps carry evidence-backed provenance (see §3-§5).

**Assumed (designed or inferred — flagged, still rendered).**
- 20 primitive(s): designed contract defaults (overridable; see §12)
- 22 block(s): designed contract defaults (overridable; see §12)

**Substitute (real family loaded; proxy is the fallback only).**
- None — every type role renders its real family.

**Needs-licensing (rendered as captured, flagged for production swap).**
- 27 third-party mark(s) in `media-assets.yaml` (`usageRights: third-party-mark`) — rendered as captured, flagged for a licensed swap; never auto-substituted.

## 16. Section catalog (slot contracts)

Each layout as an abstract contract: archetype, surface intent, use case, and the slots it exposes (slot -> type -> use case -> contract).

### full-bleed-photo-hero - overlay (surface/inverse-teal)

hero

| slot | type | use case | contract |
|---|---|---|---|
| eyebrow | content | eyebrow | `header` |
| heading | content | display | `header` |
| body | content | body | `content-block` |
| actions | content | action-group | `button` |
| background-media | media | background-media | `image` |
| utility-card | content | floating-card | `card` |

### centered-heading-over-logo-row - row (surface/primary)

logos

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | h2 | `header` |
| logo-row | media | mark-row | `logo-bar` |

### copy-left-illustration-right-carousel - split (surface/primary)

features

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | h2 | `header` |
| subheading | content | body | `header` |
| item-heading | content | h3 | `header` |
| item-body | content | body | `content-block` |
| illustration | media | illustration-media | `image` |
| carousel-nav | content | carousel-control | `content-block` |

### sticky-copy-with-card-grid - split (surface/primary)

features

| slot | type | use case | contract |
|---|---|---|---|
| eyebrow | content | eyebrow | `header` |
| heading | content | display | `header` |
| body | content | body | `content-block` |
| actions | content | action-group | `button` |
| card-grid | content | card-grid | `card` |

### headrail-split-with-card-carousel - band (surface/accent-soft)

features

| slot | type | use case | contract |
|---|---|---|---|
| headrail | content | section-headrail | `content-block` |
| heading | content | h2 | `header` |
| body | content | body | `content-block` |
| card-carousel | content | card-carousel | `card` |

### copy-left-logo-collage-inset - split (surface/primary)

integrations

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | h2 | `header` |
| link | content | text-underline-link | `button` |
| logo-collage | media | mark-collage | `logo-bar` |

### headrail-two-col-header - band (surface/primary)

content

| slot | type | use case | contract |
|---|---|---|---|
| headrail | content | section-headrail | `content-block` |
| heading | content | display | `header` |
| body | content | body | `content-block` |

### tabbed-testimonial-with-stats - split (surface/primary)

testimonial

| slot | type | use case | contract |
|---|---|---|---|
| tab-row | content | tab-row | `tabs` |
| portrait | media | portrait-media | `image` |
| quote | content | body | `testimonial` |
| attribution | content | caption | `content-block` |
| link | content | text-underline-link | `button` |
| stat-row | content | stat-row | `stat-block` |

### heading-left-award-badges-right - row (surface/primary)

logos

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | h2 | `header` |
| badge-row | media | mark-row | `logo-bar` |

### dark-band-cta - band (surface/inverse-teal)

cta

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | display | `header` |
| actions | content | action-group | `button` |

## 17. Layout patterns (project library)

Reusable, use-case-keyed layout patterns extracted from this project (project tier — wins over the standard library on ties). Sizes are relationships/classes, never px.

| pattern | use case | archetype | surface | special treatments | origin |
|---|---|---|---|---|---|
| `full-bleed-photo-hero` | hero | overlay | surface/inverse-teal | floating-utility, orange-period-accent, text-on-media | extracted |
| `centered-heading-over-logo-row` | logos | row | surface/primary | brand-colored-marks | extracted |
| `copy-left-illustration-right-carousel` | features | split | surface/primary | carousel | extracted |
| `sticky-copy-with-card-grid` | features | split | surface/primary | dotted-divider, sticky-column | extracted |
| `headrail-split-with-card-carousel` | features | band | surface/accent-soft | bleed, carousel, dotted-rule-rail, edge-cut | extracted |
| `copy-left-logo-collage-inset` | integrations | split | surface/primary | scattered-cluster | extracted |
| `headrail-two-col-header` | content | band | surface/primary | dotted-leader-rule | extracted |
| `tabbed-testimonial-with-stats` | testimonial | split | surface/primary | stat-rule, tabs | extracted |
| `heading-left-award-badges-right` | logos | row | surface/primary | tiled-grid | extracted |
| `dark-band-cta` | cta | band | surface/inverse-teal | orange-period-accent | extracted |

## 18. Component recipes

Recurring multi-slot anatomies this brand reuses across sections — recorded as first-class recipes in `layout-library.yaml` `recipes:` so generators compose them as units instead of re-deriving the parts.

### `section-headrail` — section-headrail


Used by: `headrail-split-with-card-carousel`, `headrail-two-col-header`.
