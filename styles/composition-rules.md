---
id: composition-rules
layer: composition-grammar        # NOT a visual style; the universal grammar the AI composes within
kind: composition-rules
assembled_at: generation-time     # merged with brand neverDo/scales + render_pattern_constraint seeds per run

# ── machine-consumed structure (parsed like styles/*.md front-matter via styles.parse_front_matter) ──
# The prompt builder (brand_pipeline/generate_composition.build_prompt) reads these values
# and injects them; the prose below is the guidance the generating LLM reads. Keep the two
# consistent. Values reference the REAL vocabulary (composition.v1.schema.json / §4.4 /
# contracts/*.yaml) — no invented fields.

schemaVersion: composition.v1

# Allowed structural archetypes = compose_section.ARCHETYPE_COMPOSERS keys (the drawable set).
# overlay/banded (editorial-harvest-2026-07): overlay = front slots grid-placed over z:back/mid
# media in ONE positioning context; banded = dual-surface section with a hard horizontal seam.
archetypes: [stack, collage, split, stack-fullbleed, cards, interlock, overlay, banded]

# The AI may only reference contract keys that exist in these catalogs (checked at gen time).
palette_sources:
  primitives: brand_pipeline/contracts/primitives.yaml
  blocks:     brand_pipeline/contracts/blocks.yaml

# Value & unit ethos (hard).
values:
  colors: token-refs-only        # emit tokens.colors ROLES, never raw hex
  units:  cq-only                # cqw/cqh/cqi against container-type; NEVER vw/vh/dvh
  spacing: named-scale-step-only # pick a step from the merged style spacing.scale; never ad-hoc px
  type:   sizeClass-enum-only    # sizeClass → measured brand type tier; never a raw rem

# Treatment legality. kind ∈ layout_library.TREATMENT_KINDS. `maps_to_neverDo` = illegal for a
# brand carrying that neverDo id UNLESS `sanctioned_exception` applies.
treatments:
  legal:   [ghost-word, overlap, stagger, bleed, marginal-caption, float-wrap, inset,
            panel-on-media, scrim-band, framed, mixed-face, stepped-lines]
  amount_classes: [light, medium, heavy]
  stackable: true                # multiple treatments may combine on one section (see prose)
  conditional:
    text-on-media:
      maps_to_neverDo: no-text-on-photos
      sanctioned_exception: display-title-over-media-in-hero   # the ONLY legal text-on-media
    straddle:
      # a straddle whose TARGET IS TEXT and crosses onto a photo is text-on-media-family:
      # same neverDo mapping + sanctioning; a MEDIA-target straddle (media-over-seam /
      # media-over-media) is an overlap-family device and needs no text sanction.
      maps_to_neverDo: no-text-on-photos
      sanctioned_exception: text-target-straddle-in-hero
      occlusion_contract: z-back-requires-maxOcclusion-and-endsVisible   # G8 params on z:back
    type-behind-media:
      # G8: REAL heading copy at full opacity rendered BEHIND media — NOT a ghost-word
      # (which is low-opacity decoration). Legal ONLY under the occlusion contract:
      # maxOcclusion budget (light≈0.25 / medium≈0.4 / heavy≈0.55 glyph area) AND
      # endsVisible:true (first/last letterforms clear). Over the cap the gate demands
      # reclassification to ghost-word. Text-on-media-family for neverDo purposes.
      maps_to_neverDo: no-text-on-photos
      sanctioned_exception: occluded-masthead-in-hero
      requires: [maxOcclusion, endsVisible]
    break-frame:
      salience: decorative-only        # area-capped corner decoration; never covers text
  # devices in the vocabulary a brand's neverDo may forbid outright (checked per-brand):
  neverDo_guarded: [text-on-media, straddle, type-behind-media]

# PLACEMENT vocabulary (grid/overlap contract — composition.v1 §4.6.5). ALL OPTIONAL:
# omitted = the archetype's measured default geometry, byte-unchanged.
placement:
  section_grid: { columns: 12, gutter: shared }        # section.grid re-scopes --grid-cols/--grid-gutter
  section_alignment: [centered, left, right, space-between, edge-to-edge, mixed]  # per-section anchor (+ counterweight slot for asymmetric)
  slot_fields: [colStart, colSpan, rowSpan, offsetCols, offsetBaselines, alignTo, registration]
  media_aspects: [portrait, landscape, square, wide, pano, freeform]   # honored as real aspect-ratio
  overlap_registration: { toSlot: required, edge: required, depth: cols-or-baselines, z: back|mid|front }
  media_layers: multiple-per-section                    # base + registered overlays + z:back background + corner-pinned z:front
  # editorial-harvest-2026-07 additions:
  width_classes: [hug, stretch, fixed, media, full-bleed, framed]   # framed = margins visible on ALL sides
  banded_seam: { archetype: banded, split: 0..1-fraction-of-section, register: "registration.toSlot: seam" }

# The FREEDOM ENVELOPE — what the AI may invent without breaking an invariant.
freedom_envelope:
  module_count: { min: 2, max: 4 }
  column_ratios: ["1:1", "1.2:1", "1.6:1", "2:1"]     # asymmetric preferred; even only in hero/cta
  z_order: author-freely-within-ladder                # ghost-watermark→media→panels→text
  emphasis: one-display-tier-and-one-accent-per-section
  section_select_and_order: author-freely             # SELECT + ORDER the sections
  novel_pattern: gated-by-offGridExpansion            # novelty:novel ONLY when the base style unlocks it
  promotion: novel-green-eligible-for-project-library # gates green → promote to layout-library.yaml
  # ── off-grid EXPANSION capability gate (Part B) ──
  # The base style's `offGridExpansion` flag (styles/<id>.md front-matter) decides whether
  # the generator may EXPAND beyond the captured/seeded layout set. When TRUE the treatments
  # below unlock on non-hero sections AND novelty:"novel" is allowed; when FALSE the model
  # may ONLY reuse/adapt captured patterns (no novel, no off-grid) — enforced by
  # generate_composition.offgrid_prefilter + the repair loop. The sanctioned hero bookend
  # keeps its overlap/text-on-media regardless (style identity, not expansion).
  off_grid_treatments_gated: [stagger, overlap, bleed, float-wrap, counter-rotate,
                              straddle, panel-on-media, scrim-band, type-behind-media,
                              stepped-lines, break-frame]
  off_grid_baseline_always_legal: [ghost-word, marginal-caption, inset]  # style identity, flag-independent

# Three-tier precedence (identical model to styles/*.md ## Precedence).
precedence: [base-style-invariants, composition-rules, brand-neverDo-hard]
---

> Parsed machine values live in the YAML front-matter above; the prose below is the
> guidance the generating LLM reads. This file is the **universal composition grammar** —
> it is assembled at generation time together with (a) the merged base STYLE
> (`styles/<id>.md` invariants + soft options + spacing/type scale), (b) the brand's
> `neverDo` / token scales, and (c) the `render_pattern_constraint` seed block for the
> selected use-cases. See `## Assembly` at the end.

# Composition rules

The AI emits a `composition.v1` object (see `brand_pipeline/spec/composition-schema.md` /
`composition.v1.schema.json`): an ordered list of sections, each = an archetype + slots
(primitive/block refs) + treatments + inline copy. The deterministic renderer draws it and
`onbrand_check.py` validates it. **You never write HTML/CSS and never re-author a `c-*`
primitive or `COMPONENT_CSS` — `brand_pipeline/component_render.py` is the single source of
truth for how every primitive renders.** Your job is to *arrange* the vocabulary well.

## 1. Allowed palette & slot grammar

- **Archetypes:** use only a drawable archetype — `stack`, `collage`, `split`,
  `stack-fullbleed`, `cards`, `interlock` (the `compose_section.ARCHETYPE_COMPOSERS` keys).
  Do not invent an archetype the renderer cannot draw; a novel *arrangement* lives WITHIN
  one of these.
- **Contracts:** every `slot.contract` MUST be a key in
  `brand_pipeline/contracts/primitives.yaml` (~36 leaves) or
  `brand_pipeline/contracts/blocks.yaml` (~23 clusters). Never invent a contract key.
- **Block grammar:** respect each block's slot grammar from `blocks.yaml` —
  `accepts` (which contract keys may fill a slot), `optional` (may be empty), and
  `repeatable` (holds a list). Example: `blocks.header` = `[eyebrow?, heading, subheading?,
  text?, cta?*, after-cta-text?]`; `blocks.feature-item` = `[icon?, heading, text?, link?]`;
  a repeatable slot (e.g. `stat-block.stats`, `logo-bar.logos`, `feature-item` repeated) is
  how you render N items — bind an array of `copy` to it.
- **Recursion:** scaffold → block → primitive. A layout slot is filled by blocks/media; a
  block slot is filled by primitives. Do not put a scaffold inside a block.

## 2. Hard constraints (brand `neverDo` — the only non-overridable layer)

These are absolute for WoodWave (from `runs/woodwave/brand/brand.yaml` `neverDo`). A
composition that violates one FAILS the gate. They are injected per-brand at gen time; obey
whatever the active brand carries.

- **`no-radius`** — radius is globally `0` (`tokens.spacing.radius-global: 0rem`). Never
  request rounding on any slot/asset.
- **`no-shadows`** — no drop shadows, borders, or mats. Separation is fill contrast only.
- **`no-gradients`** — no gradients/tints/fade transitions; surface seams are hard cuts.
- **`no-buttons`** — the `cta` role is realized by the `link` primitive (`variant: arrow`
  or `slash`), NEVER a `button`. `button` / `icon-button` are `use: never`.
- **`no-boxed-inputs`** — form fields are underline-only (`input`/`textarea`/`select`
  `variant: underline`), inline typographic submit; never a boxed/filled input.
- **`no-cards-on-cream`** — no bounded cards on `surface/primary` (cream). Light-canvas
  content is OPEN collage (use `content-block` / `feature-item` open, not boxed). A bounded
  unit is legal ONLY as the `surface/panel` child of a dark band (see `blocks.media-text`).
- **`no-accent-on-light`** — the gold accent (`accent/highlight`) appears ONLY on inverse /
  accent surfaces; never an accent-colored link/icon/fill on a light surface.
- **`no-text-on-photos`** — no text overlaid on photographs; captions live in the margin
  (`marginal-caption`). The **single sanctioned exception** is the hero bookend's
  `display-title-over-media` — emit it as a `text-on-media` treatment with
  `sanctioned: true`, and only in a hero section.
- **`no-section-hairlines`** — no hairline rules between sections. A 1px rule is legal only
  as an action-row bar INSIDE a panel (`divider`), never as a section seam.
- **`no-default-fonts`** — display tiers use the brand didone display face; never a system/
  generic sans for display. (Handled by tokens; do not request a font.)
- **`no-centered-everything`** — centering is reserved for hero + cta/bookend stacks;
  editorial runs are anchored/asymmetric (set `knobs.align` accordingly).

## 3. Values are tokens · units are cq · spacing is a named step · type is a tier

- **Values are tokens.** Colors resolve to `tokens.colors` roles (`surface/inverse`,
  `text/on-primary`, `accent/highlight`, …). Emit token REFS or surface roles — **never a
  raw hex**. Accent obeys `no-accent-on-light`.
- **Units are container-query.** Any rhythm/size is expressed as a *class/relationship*
  (`sizeClass`, `width`, `amount.class`, `mediaScale`), which the renderer resolves to
  `cqw/cqh/cqi` against a `container-type: size` context. **Never emit `vw`/`vh`/`dvh`**, and
  never a px literal (`component_render` emits cq/rem only).
- **Spacing is a named step.** Gaps pick a NAMED step from the merged style
  `spacing.scale` (`3xs`…`2xl`) — or the brand's measured `tokens.spacing` step
  (`section-padding-*`, `module-gap-editorial`, …) when present (the composer prefers brand
  spacing). Never an ad-hoc px gap.
- **Type is a tier.** `sizeClass` (`colossal|hero|display|title|body|caption`) resolves to a
  brand `tokens.type` tier; the base-style **display floor** applies (editorial-luxury:
  display ≥ 8rem / ~11cqw). Never a raw rem. One slot per section carries the display tier.

## 4. Treatment vocabulary & legal ranges

Treatments are the signature devices (`layout_library.TREATMENT_KINDS`), each with an
intensity `amount.class` of `light` / `medium` / `heavy`:

- **`stagger`** — offset sibling modules along an axis (alternating anchors). Legal
  everywhere; the workhorse for editorial runs. `amount: heavy` ≈ ~1/3-container offset.
- **`overlap`** — two slots overlap with an explicit `zOrder`; the brand's *primary
  ornament*. Sanctioned pairs only (WoodWave `compositionRules.overlap-primary-ornament`:
  display-text-over-media, media-over-media, panel-over-media, media-over-seam).
- **`ghost-word`** — an oversized low-opacity watermark word behind content
  (`anchor: behind-media|straddle-media|margin|full-bleed`, `bleed: none|partial|full`).
  Uses the `ghost-watermark` type tier + `text/ghost-on-primary`.
- **`bleed`** — media runs off an `edge` (`left|right|top|bottom|all`).
- **`marginal-caption`** — a micro-caption pinned in the margin `side: left|right` beside
  media (the brand's caption pattern; the on-brand answer to `no-text-on-photos`).
- **`float-wrap` + `inset`** — a statement wraps around an inset image (the incoming
  `interlock` archetype). `inset` sizes the floated media (~50% measure).
- **STACKING:** treatments may combine on one section — e.g. `ghost-word` (back) +
  `stagger` (modules) + `marginal-caption` is the WoodWave editorial-collage signature; a
  hero may stack the sanctioned `text-on-media` + `overlap`. Keep `zOrder` consistent with
  the brand z-ladder (ghost-watermark → media → panels → text).
- **ILLEGAL / conditional:** `text-on-media` maps to `no-text-on-photos` and is illegal
  EXCEPT the sanctioned hero `display-title-over-media` (`sanctioned: true`). `counter-rotate`
  is in the vocabulary but has no composer yet (inert). Any device that would realize a
  boxed card, a shadow, a gradient, or a radius is illegal (maps to the matching neverDo).

### 4a. The overlay family (editorial-harvest-2026-07)

These devices live on the `overlay`/`banded` archetypes and REUSE the §4b placement
vocabulary (grid columns + `registration`) — no parallel mechanisms:

- **`panel-on-media`** — a solid-surface panel (`target`, usually `contract: media-text`)
  grid-placed OVER a media slot (`over`). The panel carries its own opaque surface, so the
  text inside it never touches the photo — this is the sanctioned `panel-over-media`
  overlap pair, and the panel's internal stack distributes by `distribute: start|center|
  space-between`. The panel is a flat surface: no shadow, no radius (neverDo still holds).
- **`straddle`** — the `target` crosses another slot's edge, declared with the SAME
  `registration {toSlot, edge, depthCols|depthBaselines, z}` grammar as any overlap.
  `z: front` rides over the crossed slot (a display heading breaking a rail/photo seam);
  `z: back` TUCKS UNDER it (a heading sinking behind a framed panorama) and then carries
  the G8 occlusion contract (`maxOcclusion` + `endsVisible`, below). A TEXT-target
  straddle onto photography is text-on-media-family (needs `sanctioned: true` under
  `no-text-on-photos`); a MEDIA-target straddle (`media-over-seam`, media-over-media) is
  overlap-family and needs no text sanction. Inside a `banded` section,
  `registration.toSlot: seam` registers against the band boundary.
- **`scrim-band`** — a FLAT translucent band (never a gradient) crossing a media slot at
  `band: {rowStart, rowSpan}` (fractions of the media's height), carrying the `target`
  slot's content (keyword columns, meta rows). `fill.opacityClass: light|medium|heavy`
  (≈0.35/0.55/0.75 of the section's inverse surface); the readability gate's
  text-contrast check sets the effective floor — a `light` scrim under caption text on a
  busy photo will fail; use `medium`+.
- **`framed`** — the `target` media renders at `width: framed`: page margins visible on
  ALL sides (`widthRel: {to: container, ratio}` snapped to whole shared-grid columns).
  The frame creates an inset canvas other slots can register against
  (`alignTo/registration.toSlot: <frame slot>`) — the base for straddled monuments and
  tucked headings.
- **`type-behind-media`** — G8. REAL heading copy at FULL opacity rendered `z: back` with
  the `over` media on top. This is NOT a `ghost-word` (decoration at token opacity) and
  NOT an inverted overlap — the z-ladder still forbids text behind media EXCEPT under
  this explicit contract: `maxOcclusion: {class}` caps the fraction of the heading's
  glyph area the media may cover (light≈0.25 / medium≈0.4 / heavy≈0.55) AND
  `endsVisible: true` keeps the word's first and last letterforms clear — that is why an
  occluded masthead still reads. The gate recomputes occlusion from geometry and FAILS
  the section over budget; above the cap, reclassify the word as `ghost-word` and carry
  the real heading elsewhere. Text-on-media-family for neverDo purposes (sanction it).

### 4a-ii. Typographic devices (editorial-harvest-2026-07, P3)

- **`mixed-face`** — one heading, two faces: `spans: [{part: lead, face: roman},
  {part: emphasis, face: italic}]` with the copy carrying `{lead, emphasis}` parts. When
  the brand ships no italic/alternate cut it degrades to case/weight contrast — never
  fake-italicize.
- **`stepped-lines`** — an authored multi-line statement whose line left-edges step
  progressively (`steps: [0, 1, 6]` in HALF-column units, `direction: right`). The steps
  are registered indents on the shared grid, not free offsets.
- **`break-frame`** — corner-anchored decorative media crossing a `framed` slot's edge
  (`registration` onto the frame slot, `salience: decorative`). Decoration ONLY:
  area-capped, never covers a text slot, decoration-salience gate applies.

## 4b. Placement on the shared grid (WHEN and HOW — composition.v1 §4.6.5)

Every page carries ONE shared registration grid (`--grid-cols: 12` + `--grid-gutter` +
`--baseline` on `:root`); every section's geometry places onto it. The placement fields
are how you AUTHOR that geometry instead of inheriting the composer's single hardcoded
arrangement. All of them are optional — omit them and the archetype's measured default
draws; use them when the brief/axis calls for a placement the default can't express.

- **Align to columns by default; break deliberately.** Give a slot `colStart`/`colSpan`
  so its edges land on shared column lines (`colSpan: 9` ≈ a wide centered media panel;
  `colSpan: 4` ≈ a narrow inset). When you WANT an off-grid break, express it as a
  registered nudge (`offsetCols`/`offsetBaselines` — grid units, may be fractional) so
  the break reads as intent, not drift. Never invent a raw `%`/px offset.
- **Per-section alignment.** `alignment: {anchor: centered}` is how a mid-page hero (or
  any sanctioned centered stack) gets the bookend's centered treatment — centering is no
  longer hardwired to the first section. An asymmetric anchor (`left`/`right`) MUST be
  balanced: name the `counterweight` slot (media, ghost word, panel) that fills the
  opposite half, or the section reads as crammed against a dead void. Omission is NOT
  blessed (AS-18): a section that declares nothing inherits its pattern's
  `contentShape.alignment`, then the active style's role default — the composer resolves
  that chain explicitly and stamps the winner (`data-align-source`); there is no silent
  CSS fall-through to whatever a scaffold happened to hardcode.
- **Offset media requires a non-centered anchor (AS-19 legality).** The editorial media
  offset (statement `6 / -1`, quote `8 / -1` — media pushed off the text's axis) is
  legal ONLY when the section's RESOLVED anchor is a side anchor (`left`/`right`) or the
  offset slot is itself the registered `counterweight`. Under a resolved `centered`
  anchor the media span must be symmetric (`4 / -4`-family, derived by the composer from
  the anchor) — asymmetrically placed media under centered text is misregistration, and
  the `media-registration` gate check fails it.
- **Overlaps declare `registration`.** Any slot that overlaps another names `toSlot`,
  the `edge` it crosses, the crossing depth (`depthCols` for left/right edges,
  `depthBaselines` for top/bottom) and its layer (`z`). Mirroring an overlap is just
  flipping `edge`/`alignTo.corner` — the composer draws either side. A multi-image
  cluster is N registered overlays with an explicit back→front `z` order (respect the
  brand z-ladder: ghost-watermark → media → panels → text).
- **Media aspect is honored.** `mediaAspect` now resolves to a real `aspect-ratio`
  (`wide` 21/9 · `pano` 3/1 · `portrait` 3/4 · `square` 1/1) — pick the aspect that
  serves the composition (a pano base reads calmer under a display title; a portrait
  inset reads editorial) instead of accepting the variant default.
- **Background + corner layers.** A media slot with `z: back` + `width: full-bleed` is a
  true background layer behind the section's text — this is a TEXT-ON-MEDIA treatment,
  so it is only legal where the brand sanctions it (mark the treatment
  `sanctioned: true`), and the renderer adds a flat surface-toned scrim so the type
  keeps AA contrast. A small `z: front` image pins to a corner with
  `alignTo: {corner: br}` (section frame when `slot` is omitted).
- **`overlay` archetype = one positioning context.** When a section IS the layered device
  (panel over a full-bleed portrait, monument straddling a framed inset, occluded
  masthead), use `archetype: overlay`: every slot places by `colStart/colSpan` +
  `z: back|mid|front` inside one shared-grid frame; `registration` declares each crossing.
  Prefer `overlay` over bolting many overlaps onto `stack` — it says what the section is.
- **`banded` archetype = dual-surface seam.** `bands: {split: 0.5, surfaces:
  [photo, panel]}` renders TWO stacked full-width surfaces with a hard horizontal seam
  (a hard cut, never a gradient). Slots straddle the seam via
  `registration: {toSlot: seam, edge: top|bottom, depthBaselines}` — WoodWave's
  sanctioned `media-over-seam` pair. Content is surface-attributed to the band it sits
  on (straddlers to both) for the neverDo/readability checks. Cross-SECTION straddling
  is deliberately unsupported: model the whole device as ONE banded section.
- **Readability is a gate, not a vibe.** Decorative/back layers (ghost words,
  backgrounds, deep overlaps) must never compromise text readability: the on-brand
  gate's readability checks (text-contrast on media/scrims, decoration-salience on
  ghost/back layers) FAIL a section whose text loses contrast against a busy layer or
  whose decoration shouts over the content. Compose the layer stack so text always sits
  on a quiet field — scrim the background, keep ghosts low-opacity, never register an
  overlay under running text.

## 5. The freedom envelope (invent WITHIN the invariants)

You have real latitude — this is the whole point of the hybrid. Without breaking any
invariant you MAY freely choose:

- **Module count:** 2–4 modules in a features/collage/cards run (this is exactly the Arm-A
  ceiling the REPORT flagged — render N value_props as N modules, not one paragraph).
- **Column ratios:** asymmetric splits (`1.2:1`, `1.6:1`, `2:1`); reserve even `1:1` /
  centering for hero + cta.
- **Z-order:** author the layering within the ladder.
- **Emphasis:** choose WHICH slot gets the display tier and WHICH single element carries the
  one accent (accent on inverse/accent surfaces only).
- **Section select + order:** SELECT which use-cases the brief needs and ORDER them (this
  replaces the hardcoded story order).
- **Propose a NOVEL pattern:** set `novelty: novel` and `seededFrom: null` when the brief
  needs a structure the library lacks. A novel section MUST still (a) validate against
  `composition.v1.schema.json` and (b) pass the brand `neverDo`. If it then **gates green**,
  it is eligible for promotion into the project `layout-library.yaml` (`layout_library.promote`)
  — novelty compounds into the library over time.

### 5a. Off-grid EXPANSION capability (Part B — style-gated)

The freedom above is **gated by the base style's `offGridExpansion` flag** (a boolean in
`styles/<id>.md` front-matter, parsed by `brand_pipeline/styles.py`). It is the single
capability that decides whether generation may EXPAND beyond the captured/seeded layout set:

- **`offGridExpansion: true`** (editorial styles — `radical-editorial`, `editorial-luxury`):
  you MAY emit `novelty: novel` sections AND apply the off-grid treatments **`stagger`,
  `overlap`, `bleed`, `float-wrap`, `counter-rotate`** on any section to break the aligned
  grid (within the z-ladder + every `neverDo`). This is the editorial signature — the whole
  point of the hybrid EXPANSION.
- **`offGridExpansion: false`** (clean/corporate — `corporate-saas-clean`): you may **only
  reuse or adapt captured patterns**. No `novelty: novel`. No off-grid treatment on a
  non-hero section — keep modules on the grid (plain `cards`/`split`/`stack`, even ratios,
  no offset/overlap/bleed). Clean SaaS earns trust through disciplined alignment.

`ghost-word`, `marginal-caption`, `inset`, and the sanctioned hero `text-on-media` are style
identity, **not** expansion — they stay legal regardless of the flag. The gate is enforced
BEFORE render by `generate_composition.offgrid_prefilter`: a locked-style composition that
emits a novel or off-grid section is returned for repair (and rejected if unrepaired), so a
FALSE style deterministically produces zero novel / zero off-grid output.

**Seeds BIAS, they do not CAGE — WHEN the style unlocks expansion.** With
`offGridExpansion: true` the seed block ("REUSE these patterns; tune only these knobs") is a
bias you MAY depart from with `novelty: novel`. With `offGridExpansion: false` the seeds
CAGE: reuse/adapt only. Prefer reuse/adapt either way; reach for novel deliberately, and
only when unlocked.

## 6. Precedence (three enforcement tiers) & assembly

Identical model to `styles/*.md ## Precedence`:

1. **Base-style Invariants** (`styles/<id>.md ## Invariants`) — load-bearing style identity
   (poster type, two flat fields, single accent, asymmetric grid, photography-led).
   Advisory-STRONG: the gate WARNs, never hard-fails.
2. **composition-rules** (this file) — the universal grammar: palette, slot grammar,
   treatment legality, the freedom envelope, values/units/spacing/type ethos.
3. **Brand `neverDo`** — the ONLY hard, non-overridable layer; a violation FAILS the gate.

## Assembly (how this file is composed at gen time)

`brand_pipeline/generate_composition.build_prompt` assembles the system/user prompt from,
in order:

1. this **universal grammar** (front-matter + prose above),
2. the **merged base STYLE** (`styles.load_and_merge(style_id, brand)` → invariants, soft
   options, spacing/type scale, display floor),
3. the **brand** `neverDo` ids + statements, token color roles, and measured `type` tiers /
   `spacing` steps (from `brand.yaml`),
4. the **primitives/blocks catalog signatures** (contract keys + slot grammar), and
5. the **seed block** from `layout_library.render_pattern_constraint([...])` for the
   selected use-cases (produced by `generate_composition.seed_patterns`).

The seeds constrain toward reuse; the freedom envelope + `novelty:novel` keep the ceiling
open. The output is a single `composition.v1` object.
