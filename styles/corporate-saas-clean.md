---
id: corporate-saas-clean
layer: style            # middle layer; brand.md overrides any token it sets
owns: [shape, depth, type, density, color-deployment, motion]
never_sets: [brand hue values, brand font families]
composes_with: [serif-display-override, gradient-feature-section, dimensional-product-render]

# ── machine-consumed structure (AUTHORITATIVE; parsed by brand_pipeline/styles.py) ──
# These structured values are the deterministic parsed source (mirrors brand.yaml). The
# prose body below is authoring guidance; where a field is ABSENT here the parser falls
# back to the prose. Keep the two consistent. (Prose lists — brand slots, invariants,
# soft-option rationale, style rules, failure modes — stay in the body and are still
# prose-parsed; only `soft_options` is mirrored here as structured data for the gate.)
# NB: display_source: brand — corporate headline scale is a BRAND fact (moderate,
# confident), so the display tier rides the brand's measured display-hero tier; the
# poster clamp numbers below remain the structural bounds only for legacy/fallback
# callers that ask this style for a poster clamp (harness previews), never the page.
type:
  display_source: brand     # brand's measured display-hero tier drives the magnitude
  display_min_rem: 9        # moderate contrast, not Editorial poster scale (parser default)
  display_vw: 12            # documented intent (rendered as cqw, never a viewport unit)
  display_max_rem: 16
  display_leading: 0.94
  display_tracking: "-0.02em"
motion:
  min_ms: 200               # gentle, reassuring motion (prose: ~200–250ms)
  base_ms: 225              # applied transition duration (range midpoint)
radius: 12px                # soft rounded corners default (brand radius-global still wins)
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
    "md": 2rem
    "lg": 3rem
    "xl": 5rem
    "2xl": 7rem
  section_pad_slot: 2xl
  block_gap_slot: md
  cluster_gap_slot: 2xs
soft_options:               # tier-2 brand-choosable options (allowed kept as prose string)
  radius: { allowed: "10-16px, pill", default: "12px" }
  depth: { allowed: "soft-shadow, hairline-border, both", default: "soft-shadow" }
  display-family: { allowed: "sans, serif", default: "sans" }
  primary-action: { allowed: "filled-button, pill-button, ghost-link", default: "filled-button" }
  button-gradient: { allowed: "on, off", default: "off" }
# ── logo-strip device treatment (AS-33; parsed into StyleStructure.logo_strip) ──
# QUALITATIVE stance on partner/customer logo strips (monochrome | reduced | plain).
# The trust wall reads as one quiet grayscale row — marks recede behind the content and
# restore full color on hover (the corporate social-proof register). Realization lives
# in the shared composer helper; this file never carries CSS values.
logoStrip: monochrome
# ── inset art-panel surface (AS-37; parsed into StyleStructure.art_panel) ──
# QUALITATIVE stance on the rounded panel painted with a brand art asset (noise /
# gradient / illustration fill) hosting a section's content or media (inset | none).
# Panels and cards are this style's native grammar, so the device is sanctioned when
# the BRAND carries the measured evidence (heroTreatment art + panel radius tokens).
# Measured values stay brand tokens; this file never carries CSS values.
artPanel: inset
# ── alignment stance (AS-18; parsed into StyleStructure.alignment_*) ──
# Machine-readable role/archetype -> anchor map: the LAST layer of the composer's
# resolution chain (section-explicit > pattern contentShape.alignment > THIS). A key is
# tried as the section's useCase first, then its renderer archetype. Clean/corporate =
# mostly centered/symmetric: section intros center over symmetric grids; only the
# intrinsically two-column devices (split/feature rows) stay left, and they carry the
# opposite panel (or their media) as the counterweight.
alignment:
  default: centered
  roles:
    # centered/symmetric stacks (the house stance)
    hero: centered
    cta: centered
    conversion: centered
    testimonial: centered
    pricing: centered
    faq: centered
    footer: centered
    gallery: centered
    cards: centered                  # symmetric card grids under a centered intro
    generic-flow: centered           # generic flow keeps the house centered stance
    # intrinsically two-column devices — each declares its counterweight
    about: { anchor: left, counterweight: media }
    features: { anchor: left, counterweight: media }
    collage: { anchor: left, counterweight: media }
    interlock: { anchor: left, counterweight: inset-media }
    split: { anchor: left, counterweight: opposite-panel }
    overlay: { anchor: left, counterweight: canvas }
    # edge-to-edge bands / utility rows
    stack-fullbleed: edge-to-edge
    banded: edge-to-edge
    band: edge-to-edge
    utility: space-between
# ── capability: off-grid generative EXPANSION (Part B) ──
# FALSE for this clean/corporate style: the composition generator may ONLY reuse/adapt
# captured patterns — no novelty:"novel" sections and no freedom-envelope off-grid
# treatments (stagger / overlap / bleed / float-wrap / counter-rotate) on non-hero sections.
# A composition that emits one is repaired or rejected by generate_composition.offgrid_prefilter.
# Clean SaaS earns trust through disciplined alignment, not off-grid drama.
offGridExpansion: false
# ── freedom budget (the 0-5 per-section wildcard allowance; parsed by styles.py) ──
# QUALITATIVE, style-relative definitions of how far generation may deviate from the
# brand median at each level — NO exact values (no px/hex/ratios): everything is
# expressed against this style's own vocabulary (hierarchy, accent discipline, spacing
# rhythm, card depth soft options). CONSERVATIVE CEILING: this clean/corporate style
# caps at level 2 — inversion, foreign grammar, and neverDo relaxation are off the
# table (consistent with offGridExpansion: false; trust comes from disciplined
# alignment, not drama). A level above the ceiling resolves AT the ceiling. The BRAND
# may choose a LEVEL (`voice.dials.freedom` in brand.yaml) but never redefines what a
# level means — definitions live here only.
freedomBudget:
  default: 1                # a gentle nudge is the house temperament
  ceiling: 2                # crank is the hard top; 3-5 resolve down to 2
  levels:
    0:
      name: median
      unlocks: nothing — the section ships the brand median exactly as retrieved/blessed
      forbids: any deviation, including intensifying a treatment the section already carries
    1:
      name: nudge
      unlocks: subtle intensification of what the section ALREADY carries — one step up
        the style's own spacing scale for extra air, a slightly stronger heading tier
        within the declared hierarchy, a deliberate (not default) elevation choice among
        the declared depth soft options
      forbids: new treatments, alignment changes, accent spread beyond its reserved
        roles, decoration added where the median carried none
    2:
      name: crank
      unlocks: push ONE existing device to its confident maximum WITHIN the style's
        discipline — the section heading at the top of the declared type ramp, a
        feature card promoted to the full-width highlight treatment, the accent
        concentrated into one unmistakable focal moment
      forbids: off-grid placement, anchor inversion, a second accent, dark-by-default
        surfaces, foreign grammar, any neverDo relaxation — levels above this one do
        not exist for this style (requests cap here)
---

> Parsed machine values live in the YAML front-matter above (the authoritative source);
> the prose below is authoring guidance the generating LLM reads. Where a field is absent
> from the front-matter, the parser falls back to this prose.

# Corporate SaaS Clean

The reliable, trustworthy default of modern software marketing. Approachable
competence — the look that converts because nobody has to think about it.
Light canvas, one confident accent, soft rounded cards, clear sectioning,
generous air. The hardest part of this style is NOT looking generic: its
failure mode is blandness, so quality lives in hierarchy, accent discipline,
and spacing — not in flourish.

## Brand slots (filled by brand.md — do NOT assign values here)
- `paper`      — page background. Default behavior: white or very light grey.
- `surface`    — card background. Default behavior: white (or 1 step off paper).
- `ink`        — primary text. Default behavior: near-black / very dark neutral.
- `ink-muted`  — secondary text, captions. Default: mid grey, still ≥4.5:1 on paper.
- `accent`     — the single brand accent.
- `font-display` — headings.
- `font-body`    — body / UI text.
If brand.md is silent, fall back to: white/light-grey base, near-black ink,
ONE accent. Never invent a second accent. (This style carries no mono slot —
captions and metadata stay in the body sans; that absence is deliberate.)

## Appearance requirements

### Shape
- Soft rounded corners. Cards ~10–16px radius; buttons rounded or full pill.
- Content lives in clearly-bounded cards and sections, not on bare canvas.
- Cards defined by surface fill + soft shadow and/or a hairline border.

### Depth
- Soft and optimistic. Diffuse drop shadows on cards (low opacity, gentle
  spread), never hard-edged. Optional subtle gradient on buttons/heroes.
- Light source reads from above. Elevation is gentle, never heavy.

### Type
- Clear, friendly hierarchy. Each section has ONE primary heading set at a
  clearly larger size than body — at least ~2× body size — so the eye lands
  immediately. Sub-heads and body step down in obvious increments.
- Body is comfortable and legible: line length ~60–75ch, relaxed leading.
- Moderate scale contrast — confident, not extreme (this is not Editorial).
- The display MAGNITUDE is the brand's own measured headline scale (`display_source:
  brand`): this style shapes leading, tracking, and weight, but never inflates a
  moderate corporate headline to editorial poster scale — the brand's display tier
  is a brand fact, not a style flourish.
- A grotesk/geometric sans is the natural default; a serif display is an
  allowed override (see `composes_with`) but the hierarchy rules still apply.

### Density & rhythm
- Comfortable and airy. Generous padding inside cards and between sections;
  nothing cramped. Consistent vertical rhythm — even, predictable spacing
  between sections (a repeating spacing scale, not ad-hoc gaps).
- Standard responsive grid (12-col feel), predictable alignment.

#### Vertical rhythm & spacing scale
Vertical spacing is a single named scale (rem steps), not ad-hoc gaps — so section
padding and inter-block gaps are deliberate, repeatable, and professional.
Brand-agnostic: the scale defines named STEPS and which step each structural gap
uses; it never hardcodes a brand-specific value. Kept even and predictable — the
clean SaaS rhythm reads trustworthy.

Spacing scale (rem):
- `3xs` — 0.5rem
- `2xs` — 0.75rem
- `xs` — 1rem
- `sm` — 1.5rem
- `md` — 2rem
- `lg` — 3rem
- `xl` — 5rem
- `2xl` — 7rem

Rhythm slots (which scale step each structural gap defaults to):
- section padding (top & bottom): `2xl` — generous, EQUAL top/bottom air; never cramped.
- inter-block gap (between stacked blocks within a section): `md`.
- tight cluster gap (label→field, icon→title): `2xs`–`xs`.

Composer note: PREFER the brand's real spacing tokens when present in `brand.yaml`
(e.g. `section-padding-*`, `module-gap-*`) — those are the source's measured rhythm;
fall back to this scale only where the brand is silent. Section vertical padding is
symmetric (top = bottom) unless the brand explicitly commits otherwise.

### Color deployment  ⟵ where this style is won or lost
- Neutrals carry the page. The accent is RESERVED, not sprinkled: primary
  CTAs, active links, and at most one icon/illustration set per section.
- Everything non-interactive stays neutral. If accent appears on more than
  ~10% of the page's surface area, it's overused.
- One accent only. No second or third brand color competing for attention.

### Motion
- Gentle and reassuring. ~200–250ms ease-out. Fade-and-rise on scroll,
  cards lift slightly on hover, buttons give subtle feedback.
- Nothing bouncy, nothing aggressive. Respect prefers-reduced-motion.
- The per-brand motion spec is the SOURCE OF TRUTH and OVERRIDES this default
  (same pattern as the editorial styles): a brand authors its easing,
  fast/base/slow durations, its link interaction, and a scroll-reveal in
  `brand.yaml` `voice.motionSpec` — the composer reads that spec, so the style's
  Motion section is intentionally consistent with whatever the brand declares.

## Structural devices (use only if content earns them)
Use the ones the content earns; this is the conventional order:
- Hero: headline + sub + primary CTA, often with product shot or photography.
- Social-proof bar: customer logo wall or a stat line, directly under hero.
- Feature grid: 2–3 column cards, each icon + title + one-line benefit.
- Optional highlight section (e.g. AI/flagship feature) — candidate for the
  `gradient-feature-section` sub-pattern.
- Case studies / testimonials with real metrics.
- Closing CTA band, then a dense multi-column footer.

## Unit policy (rendered output)
Any rhythm/sizing the spec describes conceptually in `vw` / `clamp(…vw…)` / `px`
(e.g. the display tier's documented ~12vw intent, the ~10–16px card radius) is
INTENT only. Rendered output MUST use container-query units (`cqw`/`cqh`/`cqi`)
against a `container-type: size` context — NEVER viewport units (`vw`/`vh`/`dvh`).
Translate the concept; do not emit the `vw` literals. (The renderer already
converts the display intent to `cqw`.)

## Precedence (three enforcement tiers)
Two layers (STYLE base, BRAND on top), three enforcement tiers — the model the parser
(`brand_pipeline/styles.py`) and the gate (`onbrand_check.py`) implement:

1. **Invariants** (`## Invariants`) — the style's load-bearing identity. Advisory-STRONG:
   the gate WARNs on a broken invariant with no documented override; never hard-FAILs.
2. **Soft options** (`## Soft options`) — style choices with declared allowed values and a
   default; a brand commits one via a token/primitive binding and the gate blesses it as
   an intentional OVERRIDE.
3. **Brand `neverDo`** (in `brand.yaml`) — the only hard, non-overridable layer; the gate
   FAILs on a violation.

The BRAND fills paper/surface/ink/accent/fonts and wins on any value it explicitly sets.
Invariants are the style identity but advisory-strong, NOT absolute — only the brand's own
`neverDo` is hard.

## Style definition
1. Clear hierarchy: every section has one obvious focal point; heading is
   distinctly larger/heavier than body (≥2× body). Never a wall of
   same-weight text.
2. One disciplined accent: reserved for CTAs, links, and key icons only;
   neutrals do everything else. Never a second accent, never scattered.
3. Comfortable, consistent spacing: generous air, even vertical rhythm,
   nothing cramped.
These are the style's core rules: structure and defaults it supplies. They make the
result nameable as SaaS Clean, but they are brand-overridable — where the brand
explicitly commits to a different value the brand wins; the brand's own neverDo rules
remain the only hard, non-overridable layer. If a brand or content constraint forces
a tradeoff, sacrifice decoration first — these three are what separate competent
SaaS Clean from generic template SaaS.

## Invariants
The load-bearing style identity (tier 1 — see `## Precedence`). Advisory-STRONG: the
gate WARNs if one is broken with no documented brand override, and never hard-FAILs.
1. Clear hierarchy: every section has one obvious focal point; the heading is distinctly
   larger/heavier than body (≥2× body). Never a wall of same-weight text.
2. One disciplined accent: reserved for CTAs, links, and key icons only; neutrals do
   everything else. Never a second accent, never scattered.
3. Comfortable, consistent spacing: generous air, even vertical rhythm, nothing cramped.
4. Light canvas: light/optimistic base, never dark-by-default (dark canvases belong to
   other styles).

## Soft options
Brand-choosable style choices (tier 2 — see `## Precedence`). Each is
`option-id: [allowed values] | default: <value>`. A brand commits a choice via a token
or primitive binding; the gate blesses the committed choice as an intentional OVERRIDE.
- `radius`: [10-16px, pill] | default: 12px — soft rounded corners; a brand's
  `radius-global` token overrides it (including to sharp corners).
- `depth`: [soft-shadow, hairline-border, both] | default: soft-shadow — how cards are
  separated from the canvas.
- `display-family`: [sans, serif] | default: sans — a serif display is an allowed override
  (see `composes_with`); the hierarchy Invariant still applies.
- `primary-action`: [filled-button, pill-button, ghost-link] | default: filled-button — the
  primary CTA renders as a FILLED brand-accent button (the corporate conversion grammar);
  a brand that remaps the CTA role to a typographic link commits ghost-link.
- `button-gradient`: [on, off] | default: off — an optional subtle gradient on buttons/heroes.

## Freedom budget (0–5 wildcard allowance)
Machine values live in the front-matter `freedomBudget:` block (authoritative; parsed by
`brand_pipeline/styles.py`, consumed by `wildcard_generator.py`). Qualitative and
style-relative — no exact values; a brand picks a LEVEL (`voice.dials.freedom`), never
new definitions. Default level: `1` (nudge). CONSERVATIVE CEILING: `2` (crank) —
inversion, transplant, and neverDo relaxation do not exist for this style (consistent
with `offGridExpansion: false`); a higher requested level resolves at the ceiling.
- `0` median — ship the brand median untouched.
- `1` nudge — subtly intensify what the section already carries (air, hierarchy,
  a deliberate depth choice) within the declared soft options.
- `2` crank — one device to its confident maximum within the discipline (top of the
  declared type ramp, one full-width highlight, one focal accent moment); never
  off-grid, never a second accent, never dark-by-default.

## Failure modes (do NOT produce these)
- Flat hierarchy — everything medium-weight, no clear focal point per
  section. This is the #1 way the style reads as a generic template.
- Accent scattered across the page, or two/three competing accent colors.
- Cramped spacing or inconsistent gaps between sections.
- Default-framework shadow sameness (the identical soft grey box-shadow on
  every card with no intent) — vary elevation purposefully.
- Stock-illustration overload, or a generic "big number + small label +
  gradient blob" hero used by reflex instead of because the content calls
  for it.
- Hard shadows, 0px corners, or dark-by-default — those belong to other
  styles and break this one.

## Do NOT default to
This style IS the industry default, so the danger is invisibility, not a
cliché palette. Do not coast: a SaaS Clean page that nobody remembers has
failed even if nothing is "wrong." Earn distinction through sharp hierarchy,
disciplined accent use, real spacing rhythm, and specific copy — not through
adding decoration. The palette and fonts come entirely from brand.md; the
style contributes structure and restraint, never a hue.
