---
id: radical-editorial
layer: style            # middle layer; brand.md overrides any token it sets
owns: [shape, depth, type, density, color-deployment, motion]
never_sets: [brand hue values, brand font families]

# ── machine-consumed structure (AUTHORITATIVE; parsed by brand_pipeline/styles.py) ──
# Structured, deterministic parsed source (mirrors brand.yaml). The prose body below is
# authoring guidance; a field ABSENT here falls back to the prose. Keep them consistent.
type:
  display_min_rem: 9        # poster floor at desktop (prose: "AT LEAST 9rem / ~12vw")
  display_vw: 12            # documented intent (rendered as cqw, never a viewport unit)
  display_max_rem: 16.2     # upper clamp bound for the display tier
  display_leading: 0.936    # tight display leading (prose range ~0.92-1.0, biased tight)
  display_tracking: "-0.02em"
motion:
  min_ms: 320               # restrained motion floor (prose: ~320–620ms)
  base_ms: 470              # applied transition duration (range midpoint)
radius: 0                   # 0px radius everywhere (a load-bearing invariant, not soft)
shape:
  flat: true
  centered: false
  single_accent: true
spacing:                    # named rem scale + which step each structural gap uses
  scale:
    "3xs": 0.5rem
    "2xs": 0.75rem
    "xs": 1rem
    "sm": 1.5rem
    "md": 2.5rem
    "lg": 4rem
    "xl": 6rem
    "2xl": 9rem
  section_pad_slot: 2xl
  block_gap_slot: md
  cluster_gap_slot: 2xs
soft_options:               # tier-2 brand-choosable options (allowed kept as prose string)
  display-case: { allowed: "uppercase, sentence, mixed", default: "sentence" }
  accent-deployment: { allowed: "single-section, single-highlight", default: "single-highlight" }
  structural-numbers: { allowed: "on, off", default: "off" }
# ── alignment stance (AS-18; parsed into StyleStructure.alignment_*) ──
# The hardest-left of the three styles: only the two sanctioned centered stacks (hero
# bookend + conversion/CTA) and the closing footer cluster center; every editorial run
# stays left WITH a declared counterweight device. Resolution order: section-explicit >
# pattern contentShape.alignment > this map (useCase key first, then archetype).
alignment:
  default: left
  roles:
    hero: centered                   # the sanctioned centered bookend (brand override territory)
    cta: centered
    conversion: centered
    footer: centered
    faq: centered
    pricing: centered
    testimonial: { anchor: left, counterweight: portrait }
    about: { anchor: left, counterweight: media }
    features: { anchor: left, counterweight: media }
    collage: { anchor: left, counterweight: ghost }
    interlock: { anchor: left, counterweight: inset-media }
    split: { anchor: left, counterweight: opposite-panel }
    cards: { anchor: left, counterweight: staggered-grid }
    overlay: { anchor: left, counterweight: canvas }
    generic-flow: { anchor: left, counterweight: media }
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
> the prose below is authoring guidance. Where a field is absent from the front-matter, the
> parser falls back to this prose.

# Radical Editorial

The screen treated like an expensive print publication. Typography IS the
design — confidence comes from scale, contrast, and whitespace, not from
color, decoration, or effects. The hardest style to fake and the easiest to
ruin by half-committing. Reads as cultural, expensive, self-assured.

## Brand slots (filled by brand.md — do NOT assign values here)
- `paper`   — page background. Default behavior: near-white/off-white.
- `ink`     — primary text. Default behavior: near-black.
- `accent`  — the single committed accent.
- `font-display` — the large display face.
- `font-body`    — body/running text.
- `font-mono`    — captions, labels, metadata.
If brand.md is silent, fall back to: paper near-white, ink near-black,
ONE accent. Never invent a second accent.

## Appearance requirements

### Shape
- Corners sharp. 0px radius everywhere, including images and buttons.
- NO container cards. Content sits directly on bare canvas.
- Divisions are hairline horizontal rules (1px), never bordered/filled panels.

### Depth
- Completely flat. Zero shadow, zero elevation, zero gradient-for-depth.
- Depth comes only from scale, overlap, and oversized ghosted background
  type — never from lighting.

### Type  ⟵ load-bearing, the whole style
- Extreme size contrast is mandatory. Display headline reaches AT LEAST
  9rem / ~12vw at desktop; if it's smaller, it's a failed Editorial.
- Body and captions stay small and quiet against it. The gap between
  largest and smallest type is dramatic, not gentle.
- Display leading tight: ~0.92-1.0. Negative tracking on display (~-0.02em).
- Confident, deliberate pairing — a characterful display against a tight
  grotesk or mono. Never two similar sans faces.
- Real typographic craft: small-caps or letter-spaced caps for labels,
  hanging/lining numerals for data, controlled widows.

### Density & rhythm
- Asymmetric. Irregular whitespace: large empty margins set against dense
  passages of small text. The asymmetry is deliberate, not evenly spaced.
- Do not center everything — that kills the tension that defines the style.

#### Vertical rhythm & spacing scale
Vertical spacing is a single named scale (rem steps), not ad-hoc gaps — so
section padding and inter-block gaps are deliberate, repeatable, and professional.
Brand-agnostic: the scale defines named STEPS and which step each structural gap
uses; it never hardcodes a brand-specific value.

Spacing scale (rem):
- `3xs` — 0.5rem
- `2xs` — 0.75rem
- `xs` — 1rem
- `sm` — 1.5rem
- `md` — 2.5rem
- `lg` — 4rem
- `xl` — 6rem
- `2xl` — 9rem

Rhythm slots (which scale step each structural gap defaults to):
- section padding (top & bottom): `2xl` — generous, EQUAL top/bottom breathing
  room (symmetric vertical rhythm reads professional; never cramped at the top).
- inter-block gap (between stacked blocks within a section): `md`.
- tight cluster gap (eyebrow→heading, caption→media): `2xs`–`xs`.

Composer note: PREFER the brand's real spacing tokens when present in `brand.yaml`
(e.g. `section-padding-*`, `module-gap-*`) — those are the source's measured rhythm;
fall back to this scale only where the brand is silent. Section vertical padding is
symmetric (top = bottom) unless the brand explicitly commits otherwise.

### Color deployment
- Near-monochrome by default: ink on paper.
- The accent is committed, not scattered: a single full-bleed section OR a
  single highlight, never spread across buttons-and-links as garnish.
- Restraint reads as expensive. When unsure, use less color.

### Motion
- Restrained and smooth — expressive ease-out, durations in the ~320–620ms
  range. The per-brand motion spec is the source of truth and OVERRIDES this
  default: a brand authors its easing + fast/base/slow durations in `brand.yaml`
  `voice.motionSpec` and the composer reads it. Type reveals, line-by-line fades,
  gentle parallax on full-bleed imagery.
- Nothing bouncy, nothing mechanical — no spring, overshoot, or snap. Motion
  should feel like a page turning, not a UI reacting. Respect
  prefers-reduced-motion.

## Structural devices (use only if content earns them)
- Oversized section numbers (01/02/03) ONLY when content is a real sequence.
- Giant ghosted background numerals/words behind content for depth.
- Thin horizontal rules; mono captions/slugs; full-bleed photography; drop caps.

## Style definition
1. Display type reaches genuine poster scale (≥9rem/~12vw desktop). Not "large-ish."
2. No cards, no shadows, flat throughout — depth from scale and whitespace only.
3. Asymmetric whitespace grid — never centered-everything, never evenly padded.
These are the style's core rules: structure and defaults it supplies. They make
the result nameable as Editorial, but they are brand-overridable — where the
brand explicitly commits to a different value (e.g. a hero's centered, accent
display heading, scoped to `#sec-0`) the brand wins. The brand's own neverDo rules
remain the only hard, non-overridable layer.

## Invariants
The load-bearing style identity (tier 1 — see `## Precedence`). Advisory-STRONG: the
gate WARNs if one is broken with no documented brand override, and never hard-FAILs.
1. Display type reaches genuine poster scale (≥9rem/~12vw desktop). Not "large-ish."
2. Corners sharp — 0px radius everywhere (images and buttons); no container cards;
   divisions are hairline rules, never bordered/filled panels.
3. Completely flat — zero shadow, elevation, or gradient-for-depth; depth comes only
   from scale, overlap, and oversized ghosted background type.
4. Asymmetric whitespace grid — irregular deliberate whitespace; never
   centered-everything, never evenly padded.
5. Near-monochrome by default; a single committed accent (one full-bleed section OR
   one highlight), never scattered as garnish.
6. Confident characterful display against a tight grotesk/mono; never two similar
   sans faces.

## Precedence (three enforcement tiers)
Two layers (STYLE base, BRAND on top), three enforcement tiers — the model the parser
(`brand_pipeline/styles.py`) and the gate (`onbrand_check.py`) implement:

1. **Invariants** (`## Invariants`) — the style's load-bearing identity. Advisory-STRONG:
   the gate WARNs on a broken invariant with no documented override; never hard-FAILs.
2. **Soft options** (`## Soft options`) — style choices with declared allowed values and
   a default; a brand commits one via a token/primitive binding and the gate blesses it
   as an intentional OVERRIDE.
3. **Brand `neverDo`** (in `brand.yaml`) — the only hard, non-overridable layer; the gate
   FAILs on a violation.

The BRAND fills paper/ink/accent/fonts and wins on any value it explicitly sets,
including one that contradicts an Invariant (e.g. a hero `#sec-0` centered / accent
display heading). Invariants are the style identity but advisory-strong, NOT absolute —
only the brand's own `neverDo` is hard.

## Soft options
Brand-choosable style choices (tier 2 — see `## Precedence`). Each is
`option-id: [allowed values] | default: <value>`. Radical Editorial is a strict style, so
its soft surface is small — most of its identity is Invariant.
- `display-case`: [uppercase, sentence, mixed] | default: sentence — pick ONE and commit.
- `accent-deployment`: [single-section, single-highlight] | default: single-highlight —
  a brand commits its one accent to a full-bleed section or a single highlight.
- `structural-numbers`: [on, off] | default: off — oversized 01/02/03 section numbers,
  used ONLY when content is a real sequence.

## Failure modes (do NOT produce these)
- Display type that isn't actually large enough — the #1 failure.
- Centering everything → kills asymmetric tension → reverts to generic.
- Any card, border-radius, or shadow → instantly becomes SaaS.
- Timid font pairing (two similar sans) → no contrast, no identity.
- Filling whitespace because it looks empty — the emptiness is the design.
- A second accent color, or accent scattered as garnish.

## Do NOT default to
The most common AI-Editorial cliché is warm cream background + high-contrast
serif + terracotta accent. Structure here is fixed; the palette is whatever
brand.md injects. Do not reach for warm-cream/terracotta unless brand.md
specifies it.
