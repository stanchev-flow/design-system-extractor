# brand.md - hubspot.com   <!-- rendered from brand.yaml v1.0 by render_brand_md.py; DO NOT EDIT -->

> Generated projection. Edit `brand.yaml` (canonical) and re-render; never hand-edit this file.

## 1. Brand snapshot
HubSpot is a bright, rounded SaaS marketing system on a near-white canvas (#fcfcfa) led by a single vivid orange (#ff4800). Headings and large display copy use HubSpot Serif (the hero page-header uses HubSpot Serif Page Header Human at ~65px, weight 300); HubSpot Sans carries body, UI, and buttons. Content sits in pure-white (#ffffff), 16px-rounded, borderless cards with dashed internal dividers, floating on near-white/cream surfaces and separated by generous vertical whitespace with gentle (non-hard-cut) soft transitions. The hero is a centered eyebrow→animated heading→body→single-primary-button stack over a full-bleed photograph darkened by a flat dark scrim (no blur). The primary action is a FILLED orange button with white text; the design system also defines an orange-outline white-fill secondary and a dark tertiary. Text links are DARK (#1f1f1f) and underlined — orange is reserved for the primary fill, brand borders (active-tab underline), check icons, and the rotating hero word. Dark (#1f1f1f) is reserved for the closing CTA band and the footer.

## 2. Surface grammar
5 surface roles:
- `surface/base` - bg `#fcfcfa`, intent `base (Primary)`, text `text/default`
- `surface/raised` - bg `#f8f5ee`, intent `Secondary`, text `text/default`
- `surface/card` - bg `#ffffff`, intent `Container`, text `text/default`
- `surface/image` - bg `image + dark scrim`, intent `On Image`, text `text/on-image`, accent `brand/primary`
- `surface/inverse` - bg `#1f1f1f`, intent `Inverse`, text `text/inverted`, accent `brand/primary`

Page rhythm: surface/image -> surface/base -> surface/base -> surface/raised -> surface/base -> surface/base -> surface/base -> surface/base -> surface/base -> surface/inverse -> surface/inverse.
Section transitions are **soft**.
Nesting: `surface/card` allowed only inside `surface/base`, `surface/raised`.

## 3. Color tokens (semantic role + value)

| token | value | role |
|---|---|---|
| `brand/primary` | `#ff4800` | action-primary-bg / brand border / accent |
| `brand/primary-hover` | `#c93700` | action-primary-bg-hover / secondary text hover |
| `brand/primary-pressed` | `#9f2800` | action-primary-bg-pressed |
| `brand/sprocket` | `#ff7a59` | legacy coral accent (illustrations, decoration) |
| `brand/soft` | `#fcece6` | secondary-button hover fill / soft peach |
| `neutral/surface-base` | `#fcfcfa` | surface-base (page canvas) |
| `neutral/surface-raised` | `#f8f5ee` | surface-raised (alt section band) |
| `neutral/container` | `#ffffff` | card surface (container-01) |
| `neutral/inverse` | `#1f1f1f` | surface-inverted (cta/footer/container-inverse-01) |
| `text/default` | `#1f1f1f` | text-default (text-01) |
| `text/muted` | `rgba(0,0,0,0.62)` | text-muted (text-02) |
| `text/inverted` | `#ffffff` | text-inverted / on-color (text-on-color-01) |
| `text/on-image` | `#ffffff` | text-on-overlay |
| `text/link` | `#1f1f1f` | text-link (link-01) — DARK + underline, NOT orange |
| `border/default` | `rgba(0,0,0,0.11)` | border-default / dashed card dividers (border-03) |
| `border/medium` | `rgba(0,0,0,0.47)` | border-medium (border-02) |
| `border/strong` | `#1f1f1f` | border-strong (border-01) |
| `border/brand` | `#ff4800` | brand border / active-tab underline (border-brand-01) |
| `accent/sage` | `#b9cdbe` | illustration/elevated-cta backdrop (background-accent-01) |
| `accent/lilac` | `#d6c2d9` | illustration/elevated-cta backdrop (background-accent-02) |
| `accent/pink` | `#fcc3dc` | illustration/elevated-cta backdrop (background-accent-03) |
| `overlay/scrim` | `rgba(0,0,0,0.5)` | surface-overlay-scrim (hero darkening, NO blur) |
| `action/primary-fg` | `#ffffff` | action-primary-fg (button-primary-text-color) |
| `text/link-hover-on-inverse` | `#f8f5ee` | link hover on dark surfaces (footer/cta) |
| `text/link-hover` | `#1f1f1f` | link hover on light surfaces — SAME dark ink as idle; the hover signal is the underline/offset shift + arrow nudge, never an orange color swap |
| `overlay/hover-wash` | `rgba(0,0,0,0.05)` | hover wash on light surfaces (nav links, tabs, hoverable cards; --cl-color-hover-01) |
| `overlay/hover-wash-inverse` | `rgba(255,255,255,0.05)` | hover wash on dark surfaces (--dark-theme-hover-01) |
| `surface/primary` | `#fcfcfa` | ALIAS of neutral/surface-base — canonical page-canvas role consumed by the renderers |
| `surface/panel` | `#f8f5ee` | ALIAS of neutral/surface-raised — canonical panel/tint role |
| `surface/inverse` | `#1f1f1f` | ALIAS of neutral/inverse — canonical dark-band role (footer, elevated CTA) |
| `surface/inverse-strong` | `#1f1f1f` | ALIAS — HubSpot has ONE dark surface; strong == inverse (#1f1f1f) |
| `accent/highlight` | `#ff4800` | ALIAS of brand/primary — canonical accent role (HubSpot orange; used on light AND dark surfaces, unlike WoodWave's dark-only gold) |
| `text/on-primary` | `#1f1f1f` | ALIAS of text/default — canonical ink-on-light role |
| `text/on-primary-muted` | `rgba(0,0,0,0.62)` | ALIAS of text/muted — canonical muted-ink-on-light role |
| `text/on-inverse` | `#ffffff` | ALIAS of text/inverted — canonical ink-on-dark role |
| `text/on-inverse-muted` | `rgba(255,255,255,0.62)` | canonical muted-ink-on-dark role — measured footer idle link color (footer.measured.link.color) |
| `text/on-accent` | `#ffffff` | ALIAS of action/primary-fg — label color on the orange accent fill |
| `text/ghost-on-primary` | `rgba(0,0,0,0.05)` | canonical ghost/watermark-on-light role — HubSpot has no ghost-type device; bound to the measured light hover-wash alpha so any renderer fallback stays on-palette |
| `border/hairline-on-primary` | `rgba(0,0,0,0.11)` | ALIAS of border/default — canonical hairline-on-light role (--light-theme-border-03) |
| `border/hairline-on-inverse` | `rgba(255,255,255,0.4)` | canonical hairline-on-dark role — --dark-theme-border-02 (footer nav-column dividers .global-footer__nav-column border-bottom) |

## 4. Typography roles

| role | family | size (base) | line-height | weight | case |
|---|---|---|---|---|---|
| families |  | Nonerem |  | - |  |
| scale |  | Nonerem |  | - |  |

## 5. Spacing system
- `section-y-md`: 4rem
- `section-y-lg`: 6rem
- `section-y-s`: 2.5rem
- `container-max`: 67.5rem
- `card-padding`: 2rem 2rem 1.5rem
- `grid-gap`: 1.5rem
- `stack-md`: 1rem
- `stack-lg`: 1.5rem
- `button-inset`: 0.75rem 1.5rem
- `radius-global`: 1rem
- `panel-padding`: 2rem
- `eyebrow-to-heading`: 1rem
- `module-gap-editorial`: 6rem

## 6. Layout grammar
- **Nav** (navbar, base (Primary)): HubSpot wordmark.
- **Stack** (hero, On Image): product-line tagline.
- **Logos** (logo-carousel, base (Primary)): customer proof heading.
- **Split** (customer-platform, base (Primary)): platform intro heading + description.
- **Grid** (product-platform, Secondary): section header.
- **Stack** (breeze-agents-carousel, base (Primary)): section heading.
- **Split** (integrations-rotating, base (Primary)): integrations heading.
- **Header** (results-header, base (Primary)): results section heading.
- **Split** (case-studies-tabbed, base (Primary)): segment tab switcher.
- **Grid** (badges, base (Primary)): awards heading.
- **Stack** (elevated-cta, Inverse): closing headline.
- **Grid** (footer, Inverse): footer wordmark.

## 7. Slot mapping (slot -> primitive/block contract)
### navbar

| slot | role | contract |
|---|---|---|
| brand | HubSpot wordmark | `Logo` |
| navlinks | Products / Pricing / Resources nav links | `Link / Secondary` |
| actions | dark tertiary 'Sign in' + filled orange primary CTA | `Button / Primary` |

### hero

| slot | role | contract |
|---|---|---|
| eyebrow | microheading tagline ('Customer Platform') | `Eyebrow` |
| heading | large serif display headline with rotating orange word, white | `Heading` |
| body | supporting paragraph (-large), white | `Paragraph` |
| actions | single FILLED orange primary button ('Get a demo') | `Button / Primary` |
| background | full-bleed photo + flat dark scrim (no blur) | `Image` |

### logo-carousel

| slot | role | contract |
|---|---|---|
| heading | centered customer-proof line (h4) | `Heading` |
| logos | row/carousel of monochrome customer logos | `Logos Wrapper` |

### customer-platform

| slot | role | contract |
|---|---|---|
| intro | intro heading (h1) + description (-medium), left | `Heading` |
| feature | animated feature statement (h2) per carousel slide | `Heading` |
| media | colorful product graphic per slide (soft accent backdrop) | `Image` |

### product-platform

| slot | role | contract |
|---|---|---|
| intro | section header (h2), sticky left sidebar | `Heading` |
| cards | 2-column grid of 6 product-hub cards (white, 16px radius) | `Card / Left With Icon` |
| card-icon | orange product-hub glyph (24px) | `Image` |
| card-cta | per-card 'Learn more about X' dark arrow text link | `Link / Secondary` |

### breeze-agents-carousel

| slot | role | contract |
|---|---|---|
| heading | centered heading (h2) | `Heading` |
| cards | animated carousel of AI-agent cards | `Card / Left With Icon` |
| card-media | Breeze agent glyph | `Image` |

### integrations-rotating

| slot | role | contract |
|---|---|---|
| heading | integrations heading (h3) | `Heading` |
| cta | 'See all app integrations' dark arrow text link | `Link / Secondary` |
| logos | rotating colorful integration logos | `Logos Wrapper` |

### results-header

| slot | role | contract |
|---|---|---|
| heading | centered section heading (h2) | `Heading` |

### case-studies-tabbed

| slot | role | contract |
|---|---|---|
| tabs | Enterprise / Mid-market / Small business tabs (orange active underline) | `Link / Secondary` |
| quote | customer photo + quote + author (testimonial card) | `Testimonial / Split` |
| avatar | customer/case portrait | `Image` |
| metrics | two-to-three large stat blocks (value + description) | `Metrics / Card` |
| cta | 'Read case study' dark arrow text link | `Link / Secondary` |

### badges

| slot | role | contract |
|---|---|---|
| heading | centered awards heading (h3) | `Heading` |
| badges | grid of 6 G2 badge images | `Image` |

### elevated-cta

| slot | role | contract |
|---|---|---|
| heading | large closing headline (h1), white | `Heading` |
| actions | single FILLED orange primary button | `Button / Primary` |

### footer

| slot | role | contract |
|---|---|---|
| brand | HubSpot wordmark (light on dark) | `Logo` |
| linkcols | columns of grouped footer nav links | `Link / Secondary` |
| legal | bottom legal + copyright bar | `Rich Text` |

## 8. Composition mechanics
- **rounded-white-cards**: Content cards are pure white (#ffffff container-01), 16px-rounded, borderless, with DASHED internal dividers (1px rgba(0,0,0,0.11)); they float on near-white/cream surfaces. Elevation is subtle (rounding + contrast), not heavy shadow.
- **filled-orange-primary**: The primary action is always a FILLED orange button (#ff4800 bg, #ffffff text, 8px radius). Secondary is a white-fill orange-outline button; tertiary is a DARK (#1f1f1f) underlined arrow text link. Never demote a primary CTA to a typographic link.
- **centered-hero-scrim**: The hero is a centered text stack over a full-bleed photo darkened by a flat dark scrim (rgba(0,0,0,0.5)); NO blur is applied. The final heading word rotates in brand orange.
- **serif-headings-sans-body**: Headings and large display copy use HubSpot Serif (display); body, UI labels, buttons, and paragraphs use HubSpot Sans. The hero page-header uses HubSpot Serif Page Header Human.
- **multicol-card-grids**: Feature/product sets are presented as multi-column card grids (product hubs = 2-column grid of 6 cards), not single long lists; the lead grid pairs a sticky 1/3 intro with a 2/3 card grid.
- **generous-whitespace-soft-seams**: Sections breathe with generous vertical padding (csol -md = 40/64px up to -lg = 64/96px) and transition softly via surface tint shifts — no hard editorial cuts or hairline dividers between light sections.
- **dark-bookend-only**: Dark inverted (#1f1f1f) surfaces are reserved for the closing elevated-CTA band and the footer; the entire body run is near-white/cream/white.

## 9. Do
- Use pure-white (#ffffff), 16px-rounded, borderless cards with dashed internal dividers, floating on near-white/cream surfaces.
- Make the primary CTA a FILLED orange button (#ff4800 / white text, 8px radius); secondary a white-fill orange-outline button.
- Center the hero text stack over a full-bleed photo with a flat dark scrim (no blur); rotate the final heading word in orange.
- Set headings and display copy in HubSpot Serif; set body, buttons, and UI in HubSpot Sans (weight 300 body / 500 headings).
- Present features and product hubs as multi-column card grids (2-col grid of 6 hub cards), with a sticky 1/3 intro beside a 2/3 grid.
- Use generous vertical whitespace (csol md→lg tiers) and soft surface-tint transitions between sections.
- Use the single vivid orange (#ff4800) as a focused accent: primary buttons, brand borders / active-tab underline, feature check icons, and the rotating hero word.
- Render text links DARK (#1f1f1f) with an underline and a hover arrow; reserve orange for fills/borders/icons.
- Use dark (#1f1f1f) inverted surfaces only for the closing CTA band and the footer.

## 10. Avoid
- No hard-edged editorial brutalism; HubSpot is soft, rounded, friendly SaaS.
- No all-caps didone/serif display at every tier; HubSpot Serif headings are sentence-case, and the serif Page-Header face is hero-only.
- No typographic-only primary CTA; the primary action must be a FILLED button, never just an arrow/underline link.
- No zero-radius / sharp corners on cards (16px), buttons (8px), inputs (4px), or media.
- Do NOT color text links orange; links are dark (#1f1f1f) underlined. Orange is for fills, brand borders, icons, and the rotating hero word only.
- Do NOT blur the hero background; darken it with a flat dark scrim only.
- No hard-cut/contrast seams or hairline dividers between light sections; transition softly.
- Do not flood section surfaces with orange or pastels; keep large fields near-white/cream and use color as a focused accent / illustration backdrop.
- Marketing CTAs are 8px-rounded, NOT full pills; the 999999px pill radius is reserved for tags / Breeze core components.

## 11. Never-do
- Never render the primary CTA as a typographic link; it is always a filled orange button.
- Never zero out radius; the system is rounded (cards 16px, buttons 8px).
- Never apply blur to the hero background photo (flat dark scrim only).
- Never color text links orange; text links are dark (#1f1f1f) and underlined.
- Never set headings in all-caps; HubSpot headings are sentence-case serif.

## 12. Primitive & block rules

**Primitives** (7 extracted / 1 designed)
- `heading` (extracted: hero, results-header; use: always) - display tiers use HubSpot Serif, sentence case (neverDo.no-allcaps-display)
- `eyebrow` (extracted: hero; use: always) - microheading tagline register (e.g. 'Customer Platform')
- `paragraph` (extracted: hero, customer-platform; use: always)
- `button` (extracted: hero, elevated-cta; use: always; variant: filled-primary) - PRIMARY actions are FILLED orange buttons with white text — never typographic (neverDo.never-typographic-primary); secondary is orange-outline white-fill
- `link` (extracted: customer-platform; use: text-links-only) - text links are DARK (#1f1f1f) and underlined — orange is reserved for the primary fill (neverDo.no-orange-links)
- `image` (extracted: hero, case-studies-tabbed; use: always) - photography full-bleed with flat dark scrim in the hero (no blur — neverDo.no-hero-blur); rounded 16px inside cards
- `logo` (extracted: navbar, logo-carousel; use: always)
- `input` (designed, overridable; use: <when>) - no form observed on the captured page; synthesized as a rounded, bordered field to match the card system

**Blocks** (3 extracted / 1 designed)
- `header` (extracted: hero, results-header; slots — eyebrow: optional, heading: require, cta: optional)
- `navbar` (extracted: navbar)
- `footer` (extracted: footer)
- `form` (designed, overridable) - no lead form on the captured page; synthesized rounded field + filled submit to match the system

## 13. Locked dials
- **VARIANCE: low**
- **MOTION: medium** _(state: defined)_
- **DENSITY: medium**

## Motion (authored spec)
Motion is an authored spec (state: defined); intensity stays `medium` (calm/editorial) — no bounce, spring, overshoot, or snap.

- Easing (primary): `ease-in-out`
- Durations: fast `150ms`, base `200ms`, slow `300ms`
- Link interaction: **underline-offset-shift + arrow translateX(5px)**
- Scroll reveal: **fade-translateY** (translateY 16px)
- prefers-reduced-motion: **respect** (transitions/reveals disabled when the user requests reduced motion).

## 14. Recipe policy
- `scaffoldFirst`: True
- `reuseBeforeCreate`: True
- `composeFromPrimitives`: True
- `themeViaModes`: True
- `slotsTakeInstancesOnly`: True

## 15. Provenance & confidence ledger

Every asset and value below is **rendered**. These four buckets annotate how each fact was obtained and where a production swap may later be needed — a flag is never a replacement, substitution, or omission.

**Sampled (measured / extracted from source).** 40 color tokens, 2 type roles, 13 spacing steps carry evidence-backed provenance (see §3-§5).

**Assumed (designed or inferred — flagged, still rendered).**
- 1 primitive(s): designed contract defaults (overridable; see §12)
- 1 block(s): designed contract defaults (overridable; see §12)

**Substitute (real family loaded; proxy is the fallback only).**
- None — every type role renders its real family.

**Needs-licensing (rendered as captured, flagged for production swap).**
- None flagged.

## 16. Section catalog (slot contracts)

Each layout as an abstract contract: archetype, surface intent, use case, and the slots it exposes (slot -> type -> use case -> contract).

### navbar - nav (base (Primary))

Top navigation: wordmark left, dropdown nav links center, dark tertiary 'Sign in' + filled orange primary CTA right.

| slot | type | use case | contract |
|---|---|---|---|
| brand | media | HubSpot wordmark | `Logo` |
| navlinks | content | Products / Pricing / Resources nav links | `Link / Secondary` |
| actions | content | dark tertiary 'Sign in' + filled orange primary CTA | `Button / Primary` |

### hero - stack (On Image)

Centered eyebrow→animated heading→body→single FILLED primary button stack over a full-bleed photo darkened by a flat dark scrim (NO blur). Heading uses HubSpot Serif Page Header Human with a rotating brand-orange final word.

| slot | type | use case | contract |
|---|---|---|---|
| eyebrow | content | microheading tagline ('Customer Platform') | `Eyebrow` |
| heading | content | large serif display headline with rotating orange word, white | `Heading` |
| body | content | supporting paragraph (-large), white | `Paragraph` |
| actions | content | single FILLED orange primary button ('Get a demo') | `Button / Primary` |
| background | media | full-bleed photo + flat dark scrim (no blur) | `Image` |

### logo-carousel - logos (base (Primary))

Trust strip: centered proof heading (h4) above an auto-scrolling carousel of monochrome customer logos (DoorDash, eBay, Eventbrite, TripAdvisor, Reddit…).

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | centered customer-proof line (h4) | `Heading` |
| logos | media | row/carousel of monochrome customer logos | `Logos Wrapper` |

### customer-platform - split (base (Primary))

Customer-platform showcase: intro header (h1, h2-on-mobile) + description, paired with an animated carousel of big feature statements (each an h2 over a colorful product graphic): 'A CRM that's really smart.', 'Products that connect to everything.', 'Breeze: AI that gets your work done.'

| slot | type | use case | contract |
|---|---|---|---|
| intro | content | intro heading (h1) + description (-medium), left | `Heading` |
| feature | content | animated feature statement (h2) per carousel slide | `Heading` |
| media | media | colorful product graphic per slide (soft accent backdrop) | `Image` |

### product-platform - grid (Secondary)

Sticky 1fr/2fr split: left section header (h2 'Growing a business is hard. HubSpot makes it easier.') beside a 2-column grid of six product-hub cards (orange icon + trademarked hub name + dashed divider + 2-item feature list with orange check icons + dashed divider + 'Learn more' dark text link).

| slot | type | use case | contract |
|---|---|---|---|
| intro | content | section header (h2), sticky left sidebar | `Heading` |
| cards | content | 2-column grid of 6 product-hub cards (white, 16px radius) | `Card / Left With Icon` |
| card-icon | media | orange product-hub glyph (24px) | `Image` |
| card-cta | content | per-card 'Learn more about X' dark arrow text link | `Link / Secondary` |

### breeze-agents-carousel - stack (base (Primary))

Breeze AI section: centered heading (h2 'Built-in AI agents that work for you 24/7.') above an animated card carousel of AI-agent product cards (icon + name + description), light surface with sprocket-coral accents.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | centered heading (h2) | `Heading` |
| cards | content | animated carousel of AI-agent cards | `Card / Left With Icon` |
| card-media | media | Breeze agent glyph | `Image` |

### integrations-rotating - split (base (Primary))

Integrations strip: left header (h3 'Works with the tools you already use. 2,000+ integrations.') + 'See all integrations' dark text link, beside a right-side rotating-SVG grid of colorful integration logos (Gmail, Slack, Shopify, Mailchimp, Zapier, Google Ads…).

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | integrations heading (h3) | `Heading` |
| cta | content | 'See all app integrations' dark arrow text link | `Link / Secondary` |
| logos | media | rotating colorful integration logos | `Logos Wrapper` |

### results-header - header (base (Primary))

Standalone centered section header (h2 'Remarkable results for every size business.') that introduces the case-study tab switcher below it.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | centered section heading (h2) | `Heading` |

### case-studies-tabbed - split (base (Primary))

Tabbed testimonials with statistics: a tab switcher (Enterprise / Mid-market / Small business; active tab gets an orange underline) over a card pairing a customer photo + quote + author name/title + 'Read case study' text link with a row of two-to-three large statistic blocks ('300%+', '~350', '59%', '17%') divided by hairlines.

| slot | type | use case | contract |
|---|---|---|---|
| tabs | content | Enterprise / Mid-market / Small business tabs (orange active underline) | `Link / Secondary` |
| quote | content | customer photo + quote + author (testimonial card) | `Testimonial / Split` |
| avatar | media | customer/case portrait | `Image` |
| metrics | content | two-to-three large stat blocks (value + description) | `Metrics / Card` |
| cta | content | 'Read case study' dark arrow text link | `Link / Secondary` |

### badges - grid (base (Primary))

Awards proof: centered heading (h3 'Voted #1 in 526 G2 Reports') above a grid of six G2 award badge images.

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | centered awards heading (h3) | `Heading` |
| badges | media | grid of 6 G2 badge images | `Image` |

### elevated-cta - stack (Inverse)

Dark inverted (#1f1f1f) closing band: centered large heading (h1 'Make impossible growth feel impossibly easy, with HubSpot.') above a single FILLED orange primary CTA ('Get a demo of HubSpot's premium software').

| slot | type | use case | contract |
|---|---|---|---|
| heading | content | large closing headline (h1), white | `Heading` |
| actions | content | single FILLED orange primary button | `Button / Primary` |

### footer - grid (Inverse)

Dark (#1f1f1f) multi-column footer: wordmark + utility row, several columns of grouped nav text links, social/app-store row, and a bottom legal/branding bar.

| slot | type | use case | contract |
|---|---|---|---|
| brand | media | HubSpot wordmark (light on dark) | `Logo` |
| linkcols | content | columns of grouped footer nav links | `Link / Secondary` |
| legal | content | bottom legal + copyright bar | `Rich Text` |

## 17. Layout patterns (project library)

Reusable, use-case-keyed layout patterns extracted from this project (project tier — wins over the standard library on ties). Sizes are relationships/classes, never px.

| pattern | use case | archetype | surface | special treatments | origin |
|---|---|---|---|---|---|
| `hero-scrim-filled-cta` | hero | stack-fullbleed | any | scrim-band, text-on-media | extracted |
| `cta-elevated-card` | cta | stack | inverse | panel-on-media | extracted |
| `features-rounded-card-grid` | features | grid | primary | framed | extracted |
