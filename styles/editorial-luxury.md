---
id: editorial-luxury
layer: style            # middle layer; brand.md overrides any token it sets
owns: [shape, depth, type, density, color-deployment, motion]
never_sets: [brand hue values, brand font families]
composes_with: [serif-display-override, gradient-feature-section]

# ── machine-consumed structure (AUTHORITATIVE; parsed by brand_pipeline/styles.py) ──
# These structured values are the deterministic parsed source (mirrors brand.yaml). The
# prose body below is authoring guidance; where a field is ABSENT here the parser falls
# back to the prose. Keep the two consistent. (Prose lists — brand slots, invariants,
# soft-option rationale, style rules, failure modes — stay in the body and are still
# prose-parsed; only `soft_options` is mirrored here as structured data for the gate.)
type:
  display_min_rem: 8        # poster floor at desktop (prose: "AT LEAST 8rem / ~11vw")
  display_vw: 11            # documented intent (rendered as cqw, never a viewport unit)
  display_max_rem: 14.4     # upper clamp bound for the display tier
  display_leading: 0.944    # tight display leading (prose range ~0.92-1.04, biased tight)
  display_tracking: "-0.01em"
motion:
  min_ms: 320               # restrained motion floor (prose: ~320–620ms)
  base_ms: 470              # applied transition duration (range midpoint)
radius: 10px                # soft-radius luxury default (brand radius-global still wins)
shape:
  flat: true
  centered: false
  single_accent: true
spacing:                    # named rem scale + which step each structural gap uses
  scale:
    "3xs": 0.5rem
    "2xs": 0.875rem
    "xs": 1.25rem
    "sm": 2rem
    "md": 3rem
    "lg": 5rem
    "xl": 7.5rem
    "2xl": 11rem
  section_pad_slot: 2xl
  block_gap_slot: lg
  cluster_gap_slot: 2xs
soft_options:               # tier-2 brand-choosable options (allowed kept as prose string)
  radius: { allowed: "0, 8-14px", default: "10px" }
  display-case: { allowed: "uppercase, sentence", default: "uppercase" }
  primary-action: { allowed: "pill-button, outline-button, ghost-link", default: "pill-button" }
  accent-presence: { allowed: "single-jewel, monochrome", default: "single-jewel" }
# ── alignment stance (AS-18; parsed into StyleStructure.alignment_*) ──
# Machine-readable role/archetype -> anchor map: the LAST layer of the composer's
# resolution chain (section-explicit > pattern contentShape.alignment > THIS). A key is
# tried as the section's useCase first, then its renderer archetype. `left` anchors on
# an editorial page REQUIRE a counterweight device (the asymmetry must be balanced by
# something — a ghost word, the opposite panel, the staggered grid), never bare.
alignment:
  default: left
  roles:
    # identity-centered stacks (the sanctioned centered moments)
    hero: centered
    cta: centered
    conversion: centered
    testimonial: centered            # centered quote stacks; rail patterns override at the pattern layer
    pricing: centered
    faq: centered
    footer: centered                 # the closing bookend cluster
    # left-anchored editorial devices — each declares its counterweight
    about: { anchor: left, counterweight: media }
    features: { anchor: left, counterweight: media }
    collage: { anchor: left, counterweight: ghost }
    interlock: { anchor: left, counterweight: inset-media }
    split: { anchor: left, counterweight: opposite-panel }
    cards: { anchor: left, counterweight: staggered-grid }
    overlay: { anchor: left, counterweight: canvas }
    generic-flow: { anchor: left, counterweight: media }
    # edge-to-edge bands / utility rows
    gallery: edge-to-edge
    stack-fullbleed: edge-to-edge
    banded: edge-to-edge
    band: edge-to-edge
    utility: space-between
# ── capability: off-grid generative EXPANSION (Part B) ──
# TRUE for this editorial style: the composition generator MAY expand beyond the captured
# layout set — unlock the freedom-envelope off-grid treatments (stagger / overlap / bleed /
# float-wrap / counter-rotate) on non-hero sections AND emit novelty:"novel" sections. Off
# for clean/corporate styles. Parsed by brand_pipeline/styles.py; enforced by
# generate_composition.offgrid_prefilter + the render/gate repair loop.
offGridExpansion: true
---

> Parsed machine values live in the YAML front-matter above (the authoritative source);
> the prose below is authoring guidance the generating LLM reads. Where a field is absent
> from the front-matter, the parser falls back to this prose.

# Editorial Luxury

A brand-agnostic grammar for gallery-grade, magazine-style interfaces: oversized
typographic hierarchy, asymmetric editorial grids, tonal restraint, calm motion.
This file defines design RULES, not a palette — the invariant is structure,
typography, and motion; the swappable part is a theme block (two near-neutral
fields, one jewel accent, a serif+sans pairing, one signature motif). Reads as
expensive, quiet, print-like. Built for art/culture/fashion/hospitality, lookbooks,
exhibition microsites, premium landing pages, and editorial decks.

The look comes from type contrast and whitespace, not from decoration or effects.
Like Radical Editorial it is easy to ruin by half-committing — but it is a touch
softer and airier: it tolerates a soft component radius and a jewel accent as
STYLE DEFAULTS, both of which a brand may override (see `## Soft options` and
`## Precedence`).

## Brand slots (filled by brand.md — do NOT assign values here)
- `paper`   — page background / the LIGHT field. Default behavior: near-white, low-chroma.
- `ink`     — primary text on the light field. Default behavior: near-black, low-chroma.
- `accent`  — the single committed jewel accent.
- `font-display` — the large display SERIF (high-contrast).
- `font-body`    — body / functional SANS (quiet geometric or grotesque).
- `font-mono`    — captions / metadata fallback when the brand carries no mono.
If brand.md is silent, fall back to: paper near-white, ink near-black, ONE accent.
Never invent a second accent; when the brand has none, accent collapses to ink.

## Theme block (role tokens — fill per brand; NEVER literal colors here)
The theme is expressed only as ROLES so it stays swappable. Every brand fills:
- SURFACES — exactly TWO background fields, one dark + one light, both near-neutral
  (low saturation, chroma ≤ ~0.03; pick one warm/cool temperature). Optional
  `field-deep` one step darker than the dark field (footers/bookends). NEVER a
  third field, never a gradient, never a texture.
- ACCENT — exactly ONE jewel hue used on < 5% of surface, plus `accent-hi` one step
  brighter for hover. Never a large fill or background.
- INK — `on-dark` / `on-dark-muted` / `on-dark-faint`, `on-light` / `on-light-muted`
  / `on-light-faint`, `border-dark` / `border-light`, and `watermark` (~6–7% ink)
  for the signature device.
- TYPE — one high-contrast display SERIF + one quiet geometric/grotesque SANS. No
  third family, never a small serif, never mixed-case display unless the softer
  sentence-case mode is the chosen commitment.
- MOTIF — one repeatable signature device (see Structural devices).

(The renderer fills the six canonical brand slots above from `brand.yaml` tokens;
these extended role tokens are the conceptual theme each brand realizes through its
own surfaces/colors — brand-agnostic, never a named palette here.)

## Appearance requirements

### Shape
- STYLE DEFAULT (documented, brand-overridable): a soft component radius — cards
  ~8–14px, primary buttons pill (`999px`). This is the luxury softness.
- Photography stays rectangular with only the small `--radius` (≤ ~14px), never
  large rounding.
- This radius is a DEFAULT, not a floor (it is a Soft option — see `## Soft
  options`). A brand that forbids radius wins: in this two-layer renderer the
  structural corner radius resolves to the BRAND's value, so a brand with
  `radius: 0` / `neverDo: no-radius` renders sharp corners everywhere. The style
  never forces rounding onto such a brand.

### Depth
- Flat and tonal. Depth comes from PHOTOGRAPHY, scale, and whitespace — not from
  lighting. At most a single soft, low shadow on a light card sitting on a dark
  field; never drop-shadow-heavy cards, never glassy blur stacks.
- No gradient-for-depth, no texture. The two flat fields carry the page.

### Type ⟵ the engine
- Type contrast is the whole style. The high-contrast display SERIF is the hero on
  every screen and is set HUGE — display reaches poster scale, AT LEAST 8rem / ~11vw
  at desktop; headlines fill their column. (Documented intent ~11vw → rendered as
  cqw; see Unit policy.)
- Display leading is tight: ~0.92-1.04. Display tracking stays gentle (~-0.01em),
  never as aggressive as a brutalist editorial.
- DISPLAY default is UPPERCASE; sentence-case is the softer alternative — pick ONE
  and commit. Everything FUNCTIONAL (eyebrows, nav, buttons, captions, meta) is the
  SANS in UPPERCASE with wide tracking (letter-spacing ~0.14–0.18em, weight ~500,
  ~11px). Mixed case only inside flowing body paragraphs (sans ~14–16px, leading
  ~1.62, muted ink, measure ~44ch).
- Rule of thumb: serif → big; small → tracked uppercase sans. Never two similar
  sans; never a small serif for body.

### Density & rhythm
- Airy, never dense or app-like. Asymmetric editorial grids: uneven columns
  (spans of ONE shared column grid — e.g. 7/5, 8/4 — never private ad-hoc tracks),
  staggered sibling cards, imagery that overlaps section edges, with full-bleed
  imagery reserved for impact moments. Break the shared grid DELIBERATELY: offsets
  are whole column/baseline multiples; staggered and offset elements keep shared
  edges and baselines, so the asymmetry reads as tension against a visible grid,
  not as elements floating off it. Centered container (one shared measure), real
  gutters, deliberate vertical rhythm. The emptiness is the design — do not fill it.

#### Vertical rhythm & spacing scale
Vertical spacing is a single named scale (rem steps), not ad-hoc gaps — so section
padding and inter-block gaps are deliberate, repeatable, and professional.
Brand-agnostic: the scale defines named STEPS and which step each structural gap
uses; it never hardcodes a brand-specific value. Kept slightly airier than Radical
Editorial for the luxury feel.

Spacing scale (rem):
- `3xs` — 0.5rem
- `2xs` — 0.875rem
- `xs` — 1.25rem
- `sm` — 2rem
- `md` — 3rem
- `lg` — 5rem
- `xl` — 7.5rem
- `2xl` — 11rem

Rhythm slots (which scale step each structural gap defaults to):
- section padding (top & bottom): `2xl` — generous, EQUAL top/bottom breathing room
  (symmetric vertical rhythm reads expensive; never cramped at the top).
- inter-block gap (between stacked blocks within a section): `lg` — airier than a
  standard SaaS rhythm.
- tight cluster gap (eyebrow→heading, caption→media): `2xs`–`xs`.

Composer note: PREFER the brand's real spacing tokens when present in `brand.yaml`
(e.g. `section-padding-*`, `module-gap-*`) — those are the source's measured rhythm;
fall back to this scale only where the brand is silent. Section vertical padding is
symmetric (top = bottom) unless the brand explicitly commits otherwise.

### Color deployment
- Two fields, alternating. Sections alternate the dark field and the light field;
  flat color only; warmth and color come from imagery, not fills.
- The accent is a jewel, not a coat: it appears only on the primary wordmark/hero,
  the primary action, and tiny separators — < 5% of surface. One accent only; never
  a large accent fill or accent background. When unsure, use less.

### Motion
- Calm and expressive. Long ease-out `cubic-bezier(.22, 1, .36, 1)`, durations in the
  ~320–620ms range. Hover BRIGHTENS a step and DRAWS IN an underline (width/scaleX
  0→100% from the left) rather than swapping color; press is a slight darken, never a
  scale jump; links animate an underline rather than change color. Scroll reveals are
  subtle opacity + small translateY fades. NO bounce, NO spring, NO overshoot, NO
  fast snaps. Respect prefers-reduced-motion (disable transitions/reveals).
- The per-brand motion spec is the SOURCE OF TRUTH and OVERRIDES this default (same
  pattern as Radical Editorial): a brand authors its easing, fast/base/slow durations,
  its link interaction (e.g. an animated draw-in underline), and a scroll-reveal in
  `brand.yaml` `voice.motionSpec` — the composer reads that spec, so the style's Motion
  section is intentionally consistent with whatever the brand declares.

## Structural devices (use only if content earns them)
- ONE signature motif per brand, applied to ≥ 1 section per page: a giant faint
  watermark word/numeral behind content (~6–7% ink), a hairline index counter
  (1 / 6), or slash separators between nav items. Define yours in the theme and
  apply it consistently.
- Photography treatment: rectangular, small radius, `object-fit: cover`, one
  consistent tonal filter across ALL images (e.g. `saturate(.94) contrast(1.02)`);
  never illustration, never icons-as-art.
- Near-iconless: lean on type, photography, and space. When an icon is unavoidable,
  use a thin ~1.5px line set, small, monochrome in the current text color — no icon
  fonts, no emoji, no decorative SVG.

## Unit policy (rendered output)
Any rhythm/sizing the spec describes conceptually in `vw` / `clamp(…vw…)` / `px`
(e.g. `--section-y clamp(64px,9vw,160px)`, the poster display at ~11vw, `--radius
8px`) is INTENT only. Rendered output MUST use container-query units
(`cqw`/`cqh`/`cqi`) against a `container-type: size` context — NEVER viewport units
(`vw`/`vh`/`dvh`). Translate the concept; do not emit the `vw` literals. (The
renderer already converts the ~11vw display intent to `cqw`.)

## Component patterns (role-based, theme-driven — STYLE DEFAULTS, brand-overridable)
- Primary button (STYLE DEFAULT): inline-flex, padding ~13px 26px, `border-radius:
  var(--pill)`, `background: var(--accent)`, `color: var(--field-dark)`, sans 600
  ~12px, letter-spacing .14em, uppercase. Outline variant: transparent, 1px solid
  currentColor. Ghost variant: text + animated draw-in underline.
- Eyebrow / caption / nav item: sans 500 ~11px, letter-spacing .18em, uppercase,
  muted ink.
- Signature watermark: an absolutely-positioned `aria-hidden` display-serif word at
  ~`min(30cqw, 320px)` in the watermark ink, behind z-indexed content.
- Light card on dark field: rectangle at `--radius-lg`, hairline rows, at most one
  soft low shadow, values in display serif, labels in tracked uppercase sans.

> These pill/accent/soft-radius component defaults are exactly that — DEFAULTS (see
> `## Soft options`). A brand that forbids buttons or radius OVERRIDES them: its
> `neverDo` wins. A brand that sets `radius: 0`, marks the `button` primitive
> `use: never`, and remaps the CTA role to a typographic arrow/slash `link` renders
> NO pill buttons and NO rounded corners — the action becomes a draw-in underline
> link. The style does not force buttons or radius onto a brand that forbids them.

## Precedence (three enforcement tiers)
Two layers (STYLE base, BRAND on top), three enforcement tiers — this is the model
the parser (`brand_pipeline/styles.py`) and the gate (`onbrand_check.py`) implement:

1. **Invariants** (`## Invariants`) — this style's load-bearing identity (structure,
   typography, motion deployment). Advisory-STRONG: the gate WARNs if an invariant is
   broken with no documented brand override; it never hard-FAILs on an invariant.
2. **Soft options** (`## Soft options`) — style choices with declared allowed values
   and a default. A brand picks one by committing a token / primitive binding; the
   gate blesses the choice as an intentional OVERRIDE (it does not warn).
3. **Brand `neverDo`** (in `brand.yaml`) — the ONLY hard, non-overridable layer; the
   gate FAILs on a violation.

The BRAND fills the named slots (paper/ink/accent/fonts) from its tokens and WINS on
any value it explicitly sets, including a value that contradicts an Invariant. Where a
brand explicitly commits to a value that differs from a soft-option default (e.g. a
brand with `radius: 0` + `neverDo: no-radius`, a CTA remapped to a typographic link,
or a hero display heading scoped to `#sec-0` centered/accent) the brand wins and the
gate records an INTENTIONAL OVERRIDE rather than a warning. Invariants are the style
identity but they are advisory-strong, NOT absolute — only the brand's own `neverDo`
is hard.

## Style definition
1. Type contrast is the engine: a high-contrast display serif set at genuine poster
   scale (≥8rem/~11vw desktop) is the hero of every screen; everything functional is
   small, tracked, uppercase sans. Not "large-ish."
2. Two flat near-neutral fields alternate; depth is photography + whitespace, never
   shadows or gradients. ONE jewel accent only, on < 5% of surface — never a large
   fill, never a second accent.
3. Asymmetric editorial grid — uneven columns, staggered siblings, airy never
   dense; never centered-everything, never evenly padded.
These are the style's core rules: structure and defaults it supplies. They make the
result nameable as Editorial Luxury, but they are brand-overridable — where the
brand explicitly commits to a different value (e.g. a hero's centered, accent display
heading scoped to `#sec-0`) the brand wins. The brand's own neverDo rules remain the
only hard, non-overridable layer.

## Invariants
The load-bearing style identity (tier 1 — see `## Precedence`). Advisory-STRONG: the
gate WARNs if one is broken with no documented brand override, and never hard-FAILs.
1. Type contrast is the engine: a high-contrast display serif at genuine poster scale
   (≥8rem/~11vw desktop) is the hero of every screen; everything functional is small,
   tracked, uppercase sans. Not "large-ish."
2. Two flat near-neutral fields alternate; depth is photography + whitespace, never
   shadows, gradients, or texture. No third field.
3. Exactly ONE accent, deployed on < 5% of surface — never a large fill/background,
   never a second accent.
4. Asymmetric editorial grid — uneven columns, staggered siblings, airy never dense;
   never centered-everything, never evenly padded.
5. Near-iconless and photography-led: rectangular imagery with one consistent tonal
   filter; one signature motif per brand applied consistently.

## Soft options
Brand-choosable style choices (tier 2 — see `## Precedence`). Each is
`option-id: [allowed values] | default: <value>`. A brand commits a choice via a token
or primitive binding; the gate blesses the committed choice as an intentional OVERRIDE.
- `radius`: [0, 8-14px] | default: 10px — the luxury softness; a brand's `radius-global`
  token (and `neverDo: no-radius`) overrides it to sharp corners.
- `display-case`: [uppercase, sentence] | default: uppercase — pick ONE and commit.
- `primary-action`: [pill-button, outline-button, ghost-link] | default: pill-button —
  a brand may remap the CTA role to a typographic link (`button use: never`).
- `accent-presence`: [single-jewel, monochrome] | default: single-jewel — a brand with
  no accent token collapses the accent to ink (monochrome), never inventing a second.

## Failure modes (do NOT produce these)
- Display type that isn't actually large enough — the #1 failure.
- A third background field, a gradient, or a texture; glassy blur stacks.
- More than one accent, or the accent used as a large fill/background.
- Drop-shadow-heavy cards, rounded corners above ~14px, bright/saturated color.
- A third type family, a small serif, or mixed-case display when uppercase was the
  chosen commitment (or vice-versa — not committing to one).
- Invented icons or illustrations; icons-as-art.
- Tight, dense, app-like spacing; filling whitespace because it looks empty.
- Letting the style's pill/radius defaults leak onto a brand that forbids them.

## Do NOT default to
The common AI-luxury cliché is warm cream + high-contrast serif + a single gold
accent. Structure here is fixed; the palette is whatever
brand.md injects. Do not reach for cream/gold unless brand.md specifies it, and do
not let the documented pill/soft-radius component defaults override a brand's
no-radius/no-buttons rules.
