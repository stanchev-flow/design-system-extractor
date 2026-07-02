# composition-schema.md — `composition.v1` (SPEC §4.6)

> Status: **design / for review**. This document specifies the `composition.v1`
> artifact — the STRUCTURED object the generation AI emits for a whole page. It adds a
> new §4.6 to `brand-schema.md` and does **not** change any runtime. It reuses the
> `layout-patterns.v1` vocabulary from `brand-schema.md` §4.4 **verbatim** so the
> round-trip into the existing renderer is lossless. The JSON Schema companion is
> `brand_pipeline/spec/composition.v1.schema.json`.

## 4.6.0 Why a structured composition (the hybrid decision)

The WoodWave A/B (`experiments/woodwave-ab/REPORT.md`) compared two generation
*representations* at constant brand+style+brief:

- **Arm A (structured → deterministic renderer)** passed the gate **11/11** with zero
  effort, because `compose_page`→`compose_section`→`component_render` and
  `onbrand_check.py` are co-designed — but it is **ceilinged by a fixed layout catalog**:
  the single-module `editorial-collage` flattened the brief's **three** value_props into
  one paragraph (REPORT §"Structural variety", lines 171–177).
- **Arm B (HTML-first)** rendered the three props as three modules and shipped a real
  signup field, but **FAILED** the gate on mechanism coupling (`no-boxed-inputs`,
  `no-default-fonts`, `Webfonts loaded`) — artifacts of the gate keying on the pipeline's
  delivery fingerprints, not off-brand output (REPORT §134–159, lines 105–116).

The approved resolution (REPORT §225–233) is the **hybrid**: the AI emits a
**STRUCTURED `composition.v1` object** — ordered sections → archetype/slots + primitive/
block refs + treatments + inline copy — which the deterministic renderer draws and the
gate validates. This keeps Arm A's primitive consistency + gate-safety while giving the
AI Arm B's freedom to *arrange* novel layouts. **The AI never authors raw HTML/CSS or
re-authors the `c-*` primitives / `COMPONENT_CSS` (`component_render.py` is the SSOT).**

## 4.6.1 Top-level shape

```yaml
schemaVersion: composition.v1
brief:  { id, name?, text?, useCasesRequested?[] }   # what the page is for (SELECT/ORDER/BIND source)
brand:  { ref, name? }                                # path to the canonical brand.yaml
style:  { id }                                        # active styles/<id>.md (merged UNDER brand)
sections: [ <section>, … ]                            # ORDERED = the page (replaces DEFAULT_ORDER)
rationale: "<why these sections / this order / these novel departures>"   # advisory
```

> The composition is a plain object; it may be authored as JSON (validated against
> `composition.v1.schema.json`) or the equivalent YAML. All examples below are YAML for
> readability.

### section

```yaml
- id:            <slug>              # unique within the composition → layouts[].id
  useCase:       hero|features|pricing|testimonial|gallery|cta|about|faq|logos|footer
  archetype:     stack|collage|split|stack-fullbleed|cards|interlock|overlay|banded   # ARCHETYPE_COMPOSERS key
  surfaceIntent: any|primary|inverse|inverse-strong|panel              # → layouts[].surfaceIntent
  seededFrom:    { lib: project|standard, id: <patternId> } | null     # → layouts[].patternRef
  novelty:       reuse|adapt|novel   # how far it departs from the seeded pattern
  grid?:         { columns: 12, gutter: <len> }   # OPTIONAL registration grid (default = shared page grid)
  alignment?:    { anchor: centered|left|right, counterweight?: <slot> }  # OPTIONAL per-section anchor
  bands?:        { split: <0..1>, surfaces: [<top>, <bottom>] }  # 'banded' archetype ONLY (§4.6.6)
  slots:         [ <slot>, … ]       # the filled holes → blockMapping[]
  treatments:    [ <treatment>, … ]  # signature devices → gridRules/overlapRules + --c-* vars
  knobs:         { <knob>: <value> } # tuned variantKnobs → renderer options / --c-* vars
```

### slot (reuses `layout-patterns.v1` §4.4 slot signature verbatim, + placement)

```yaml
- name:        <slot>               # e.g. heading, media, body → blockMapping[].slot
  role:        <semantic role>      # e.g. display-title, hero-photo → blockMapping[].role
  contract:    <primitive|block key># MUST exist in contracts/primitives.yaml|blocks.yaml → blockMapping[].contract
  textLen:     none|word|short|medium|long        # class, resolves to a type tier (never px)
  sizeClass:   colossal|hero|display|title|body|caption
  width:       hug|stretch|fixed|media|full-bleed|framed   # framed = margins visible on ALL sides (G4)
  mediaAspect: portrait|landscape|square|wide|pano|freeform # media slots — honored as a real aspect-ratio
  z:           back|mid|front        # z-layer (respect brand z-order ladder)
  # ── OPTIONAL placement on the section's registration grid (§4.6.5) ──
  colStart?:   <int 1..>            # 1-based start column → grid-column start / registered inset
  colSpan?:    <int 1..>            # span → calc(N·--col + (N-1)·--grid-gutter): edges land on shared lines
  rowSpan?:    <int 1..>            # multi-row scaffolds (advisory where an archetype has no rows)
  offsetCols?:      <number>        # horizontal nudge in shared-grid columns (registered, never a free %)
  offsetBaselines?: <number>        # vertical nudge in --baseline multiples
  alignTo?:    { slot?: <slot|section>, edge?: left|right|top|bottom, corner?: tl|tr|bl|br }
  registration?: { toSlot: <slot>, edge: left|right|top|bottom,      # OVERLAPS declare registration:
                   depthCols?: <n>, depthBaselines?: <n>,            #   how far the overlay CROSSES the edge
                   z?: back|mid|front }                              #   and on which layer (media z-ladder)
  copy?:       "<string>" | { … } | [ … ]          # inline copy bound from the brief
  asset?:      { src, alt, ratio } | null          # bound media asset (null → placeholder)
```

### treatment (reuses `layout-patterns.v1` §4.4 `specialTreatments` shape verbatim)

```yaml
- kind:       ghost-word|overlap|stagger|bleed|marginal-caption|text-on-media|counter-rotate|float-wrap|inset
              |straddle|panel-on-media|scrim-band|framed|type-behind-media       # editorial-harvest P2
              |mixed-face|stepped-lines|break-frame                              # editorial-harvest P3
  target?:    <slot>                 # ghost-word/stagger/bleed/marginal-caption/text-on-media/…
  pair?:      [ <slotA>, <slotB> ]   # overlap
  zOrder?:    [ <slot>, … ]          # overlap/ghost-word layer order back→front
  amount?:    { class: light|medium|heavy }
  side?:      left|right             # marginal-caption / float-wrap
  edge?:      left|right|top|bottom|all               # bleed
  anchor?:    behind-media|straddle-media|margin|full-bleed   # ghost-word
  over?:      <slot>                 # text-on-media / panel-on-media / scrim-band / type-behind-media
  bleed?:     none|partial|full      # ghost-word
  axis?:      vertical|horizontal    # stagger
  sanctioned?: true|false            # true only when a brand rule blesses a normally-forbidden device
  # ── editorial-harvest-2026-07 device parameters (all optional, §4.6.6) ──
  registration?: { toSlot, edge, depthCols?|depthBaselines?, z? }  # straddle/panel-on-media/break-frame
                                     # inside a 'banded' section toSlot may be the reserved name 'seam'
  band?:      { rowStart: <0..1>, rowSpan: <0..1> }   # scrim-band: where it crosses the media (media-height fractions)
  fill?:      { opacityClass: light|medium|heavy }    # scrim-band: FLAT translucent wash (never a gradient)
  distribute?: start|center|space-between             # panel-on-media: panel's internal stack distribution
  widthRel?:  { to: container, ratio: <0..1> }        # framed: frame width ratio, snapped to whole columns
  maxOcclusion?: { class: light|medium|heavy }        # G8: glyph-area occlusion budget (~0.25/0.4/0.55)
  endsVisible?: true                                  # G8: first+last letterforms must stay clear
  steps?:     [ <n>, … ]             # stepped-lines: per-line indents in HALF-column units
  direction?: left|right             # stepped-lines
  spans?:     [ { part: lead|emphasis, face: roman|italic|display|body }, … ]  # mixed-face
  salience?:  decorative             # break-frame: decoration only (area-capped, never over text)
```

`kind` values are exactly `layout_library.TREATMENT_KINDS`. `sanctioned: true` is how the
composition records a device that is *only* legal because a brand
`compositionRule`/`neverDo` exception permits it — the canonical case being WoodWave's
`display-title-over-media` (the ONE `text-on-media` allowed by `no-text-on-photos`, see
`runs/woodwave/brand/brand.yaml` neverDo `no-text-on-photos`).

## 4.6.2 Worked WoodWave example

Brand `runs/woodwave/brand/brand.yaml`, style `editorial-luxury`, brief `signup-launch`
(hero + 3 value_props + conversion). Three sections: a hero with the sanctioned display
overlap, a **`cards` features section that renders the brief's 3 value_props as 3 modules
plus a cta stack**, and a centered conversion stack.

```yaml
schemaVersion: composition.v1
brief: { id: signup-launch, name: "WoodWave — signup launch",
         useCasesRequested: [hero, features, cta] }
brand: { ref: runs/woodwave/brand/brand.yaml, name: "WoodWave Gallery" }
style: { id: editorial-luxury }
sections:

  # ── HERO: display title overlapping layered photography (sanctioned overlap) ──
  - id: hero
    useCase: hero
    archetype: stack                       # → ARCHETYPE_COMPOSERS["stack"] (opening-bookend)
    surfaceIntent: inverse
    seededFrom: { lib: project, id: hero-display-over-staggered-media }
    novelty: reuse
    slots:
      - { name: main, role: wordmark, contract: logo, width: hug, z: front,
          copy: { variant: inverse } }
      - { name: main, role: display-title, contract: header, textLen: medium,
          sizeClass: display, width: hug, z: front,
          copy: { eyebrow: "NOW ENROLLING", heading: "WOODWAVE GALLERY" } }
      - { name: main, role: hero-photo, contract: image, mediaAspect: landscape,
          width: full-bleed, z: back, copy: { radius: "0" }, asset: { ratio: landscape } }
      - { name: main, role: overlap-photo, contract: image, mediaAspect: portrait,
          width: media, z: mid, copy: { radius: "0" }, asset: { ratio: portrait } }
    treatments:
      - { kind: text-on-media, target: display-title, over: hero-photo, sanctioned: true }  # the ONLY legal text-on-media
      - { kind: overlap, pair: [hero-photo, overlap-photo], zOrder: [hero-photo, overlap-photo], amount: { class: medium } }
    knobs: { align: center }               # hero/cta may center (no-centered-everything exception)

  # ── FEATURES: 3 value_props → 3 OPEN modules (no-cards-on-cream honored) + cta ──
  - id: features
    useCase: features
    archetype: cards                       # → ARCHETYPE_COMPOSERS["cards"] (staggered caption modules)
    surfaceIntent: primary
    seededFrom: { lib: standard, id: features-split-feature }
    novelty: adapt                         # library seed is 1 module; adapt to 3
    slots:
      - { name: intro, role: section-title, contract: header, textLen: short,
          sizeClass: title, width: hug, z: front,
          copy: { eyebrow: "WHY WOODWAVE", heading: "Three ways in" } }
      - { name: modules, role: value-prop-module, contract: feature-item, textLen: long,
          sizeClass: body, width: stretch, z: front,
          copy:                            # repeatable: 3 value_props → 3 instances
            - { heading: "Archival prints", text: "Museum-grade pigment on cotton rag." }
            - { heading: "Rotating shows", text: "A new curator every eight weeks." }
            - { heading: "Members' hours", text: "Quiet mornings before the doors open." }
        }
      - { name: cta, role: section-action, contract: link, textLen: short,
          width: hug, z: front, copy: { label: "See the programme", variant: arrow } }
    treatments:
      - { kind: stagger, target: modules, axis: vertical, amount: { class: medium } }   # alternating anchors, NOT boxed cards
    knobs: { columns: "3", railSide: none }

  # ── CTA: centered narrow underline conversion stack ──
  - id: cta
    useCase: cta
    archetype: stack                       # → ARCHETYPE_COMPOSERS["stack"] (conversion-stack)
    surfaceIntent: primary
    seededFrom: { lib: project, id: cta-underline-conversion-stack }
    novelty: reuse
    slots:
      - { name: main, role: heading, contract: header, textLen: short, sizeClass: title,
          width: hug, z: front, copy: { eyebrow: "JOIN", heading: "Start your membership" } }
      - { name: main, role: signup, contract: form, width: hug, z: front,
          copy: { placeholder: "you@company.com", submit: "START FREE" } }   # underline field, inline submit
    treatments: []
    knobs: { align: center }
rationale: >-
  Hero reuses the project bookend (sanctioned display overlap). Features ADAPTS the
  single-module library seed into a 3-module open collage so the brief's three value_props
  each render as their own module (the exact Arm-A ceiling REPORT flagged) while honoring
  no-cards-on-cream via feature-item (open, not boxed). CTA reuses the underline stack.
```

## 4.6.3 The 1:1 round-trip mapping (composition → existing renderer input)

Every `composition.v1` field maps onto a field the current pipeline already consumes — a
`brand.yaml layouts[]`-shaped dict fed to `compose_page`/`compose_section`, the
`blockMapping[]` fed to `component_render`, or a resolved `--c-*` var. The composition is
therefore a *generator* for the existing structured contract, not a new render path.

| composition.v1 field | existing renderer input | mechanism |
|---|---|---|
| `sections[]` order | page section order | replaces `compose_page.DEFAULT_ORDER`; sections render in list order |
| `section.id` | `layouts[].id` | section slug → layout id (`#sec-N` scope) |
| `section.useCase` | retrieval key | `layout_library.infer_use_case` / `match` query (not stored on the layout) |
| `section.archetype` | `layouts[].archetype` → `compose_section.ARCHETYPE_COMPOSERS[key]` | drawable-archetype key; picks the composer |
| `section.surfaceIntent` | `layouts[].surfaceIntent` | resolves to a `tokens.surfaces` role + surface `--c-*` vars |
| `section.seededFrom` | `layouts[].patternRef {lib, id}` | back-ref to the reused `layout-patterns.v1` pattern (§4.4) |
| `section.novelty` | (generation metadata) | drives reuse/adapt/**promote** (novel green → project `layout-library.yaml`) |
| `slot.name` / `slot.role` / `slot.contract` | `blockMapping[].slot` / `.role` / `.contract` | resolved by `component_render.resolve_renderer(contract)` |
| `slot.copy` | `blockMapping[].usage` + section copy | e.g. `header` copy → `render_header` props (eyebrow/heading/cta); replaces `SECTION_COPY`/`LAYOUT_COPY` |
| `slot.asset` | `image`/`video` `usage.src` + `ratio`/`radius` | bound media (or placeholder when null) |
| `slot.width` / `slot.mediaAspect` | `widthRules` / `image` variant | container measure + image aspect class |
| `slot.textLen` / `slot.sizeClass` | type tier resolution | class → tier via brand `tokens.type` + style display floor (see §4.6.4 flag) |
| `slot.z` | `overlapRules.zOrder` | z-layer ladder |
| `treatment` (overlap/stagger/ghost-word/…) | `gridRules` (`stagger`/`overlap`) + `overlapRules.types`/`zOrder` | `query_from_layout` reads these back; composer draws via offsets |
| `treatment.amount.class` + `overlap` | `--c-title-overlap` / offset vars (`component_vars`) | intensity class → offset var (relationships, never px in the AI output) |
| `section.knobs` | archetype/pattern `variantKnobs` | e.g. `align`→hero centering, `columns`→cards grid, `mediaSide`→split side |
| `section.grid` | `layouts[].gridRules {columns, gutter}` → section-scoped `--grid-cols`/`--grid-gutter` | no more collapsing to `columns: 1` + booleans; the declared grid re-scopes the section's registration vars |
| `section.alignment` | `layouts[].alignment` → per-section anchor CSS (`compose_section.alignment_css`) | replaces the `#sec-0`-only centering exception: ANY section may declare centered/left/right (+ counterweight) |
| `slot.colStart` / `colSpan` / `rowSpan` / `offsetCols` / `offsetBaselines` | `layouts[]._placement[slot]` → `grid-column: S / span N` or `calc(N·--col + (N-1)·--grid-gutter)` widths + baseline offsets | slot edges land on shared column lines / baselines instead of free % scalars |
| `slot.alignTo` | `layouts[]._placement[slot]` → corner/edge pinning CSS | pin a slot to another slot's (or the section frame's) edge/corner — e.g. a small `z:front` image anchored `br` |
| `slot.registration` | `layouts[]._mediaLayers[]` → registered overlay placement + `z-index` (`compose_stack_hero` layered path) | replaces the magic `%` overlap offsets: the overlay crosses the declared edge by `depthCols`/`depthBaselines` on the declared layer |
| `slot.mediaAspect` (incl. `wide`/`pano`) | `image` `usage.aspect` → `aspect-ratio` CSS | honored for real: portrait 3/4 · square 1/1 · wide 21/9 · pano 3/1 |

## 4.6.4 Fields that do NOT cleanly round-trip today (flags)

These schema fields are captured faithfully in `composition.v1` (they keep the round-trip
lossless *at the contract level* and are ready for the Phase-2/3 renderer work) but the
**current** renderer does not yet consume them at full fidelity:

1. **`slot.sizeClass` = `colossal` / `hero`.** `component_render` exposes only three
   drawable heading tiers via `render_heading` `level` (`display`/`h2`/`h3`) plus the
   distinct `ghost-watermark` token. `colossal`/`hero` collapse to the `display` tier;
   colossal type is reached via the `ghost-word` **treatment** (its own tier), not via
   `sizeClass`. So `sizeClass` beyond {display, title→h2, body/caption→h3/body} is
   advisory until the composer maps the full class ladder onto tiers.
2. **Per-slot `slot.width` classes.** `hug`/`stretch`/`fixed` remain advisory. This flag
   has otherwise SHRUNK with the §4.6.5 placement vocabulary: per-slot `colStart`/`colSpan`
   /`offset*`/`alignTo`/`registration` are now honored for real (grid-registered widths,
   positions and overlap depths), `width: full-bleed` + `z: back` renders a true
   background layer, and `mediaAspect` (incl. the new `wide`/`pano`) resolves to a real
   `aspect-ratio`. Prefer the placement fields over `width` classes for geometry.
3. **`treatment.kind` = `counter-rotate` / `float-wrap` / `inset`.** These are legal in
   the vocabulary (`layout_library.TREATMENT_KINDS`) but are only drawn where an
   `ARCHETYPE_COMPOSER` implements them — `float-wrap`/`inset` land in the incoming
   `interlock` archetype; `counter-rotate` has no composer yet, so it is inert until one
   exists. A `novel` section using an undrawn treatment will validate against the schema +
   neverDo but the renderer will ignore the undrawn device (no crash, just no effect).
4. **`knobs` the archetype doesn't expose.** Only knobs a composer/pattern reads take
   effect; unknown knobs are ignored (they are still recorded for promotion).

None of these break gate-safety: unconsumed fields are dropped, never rendered as raw
CSS, so a composition that validates here + passes `onbrand_check.py` stays brand-safe.
As later phases grow `ARCHETYPE_COMPOSERS` (the in-flight harvest worker is adding `cards`
+ `interlock`), these flags shrink without any schema change.

## 4.6.5 Placement & registration vocabulary (grid/overlap contract)

All placement fields are **optional** — a composition that omits them renders exactly as
before (the archetype's measured default geometry). When present they give the model real
*placement* levers instead of relying on the composer's hardcoded offsets:

- **The registration grid.** Every section places onto the SHARED page grid emitted on
  `:root` (`--grid-cols: 12`, `--grid-gutter`, `--content-measure`, `--baseline`).
  `section.grid {columns, gutter}` re-scopes those vars for one section (rare; declare it
  only when a section genuinely needs its own rhythm — the default is the shared grid).
- **Spans land on shared lines.** `colStart`/`colSpan` resolve to
  `grid-column: S / span N` on grid scaffolds, or to
  `calc(N·var(--col) + (N-1)·var(--grid-gutter))` widths on flow/absolute scaffolds — so
  a slot's left/right edges register to the same column lines as every other section.
  `offsetCols`/`offsetBaselines` are deliberate registered nudges (grid units, never a
  free `%`).
- **Alignment is per-section.** `alignment.anchor: centered` gives ANY section the same
  centered treatment the hero bookend gets (the old `#sec-0`-only exception is retired);
  `left`/`right` anchor the text column and SHOULD name a `counterweight` slot that fills
  the opposite side (media / ghost / panel) so asymmetry reads as intent, not a dead half.
- **Overlaps declare `registration`.** An overlapping slot names the base slot
  (`toSlot`), the edge it crosses, HOW FAR it crosses (`depthCols` for horizontal edges,
  `depthBaselines` for vertical), and its layer (`z`). The renderer converts that into
  grid-registered position + `z-index` — replacing the old magic `%` offsets whenever a
  registration is declared. `alignTo {slot, corner}` positions the overlay along the
  perpendicular axis (e.g. `corner: bl` = the overlay sits at the base's bottom-left).
- **Multiple media layers per section.** A section may carry several media slots with
  distinct placement/z: one base image, N registered overlays (a collage cluster with an
  explicit back→front order), a `z: back` + `width: full-bleed` background layer behind
  the text (the sanctioned text-on-media treatment — the renderer adds a flat scrim so
  the gate's text-contrast check passes), and small `z: front` images pinned to a corner
  via `alignTo {corner}` (against the section frame when `slot` is omitted).

## 4.6.6 Overlay family, banded sections & typographic devices (editorial-harvest-2026-07)

All of these are OPTIONAL and additive — a composition that uses none of them validates
and renders byte-identically to before. They reuse the §4.6.5 placement vocabulary.

**`overlay` archetype.** One positioning context: every slot places by
`colStart/colSpan` + `z: back|mid|front` inside a single shared-grid frame (the composer
draws one `.c-overlay` scaffold with absolutely-registered children over an in-flow
canvas). Use it when the section IS the layered device rather than a stack that happens
to overlap. Treatments that live here:

- **`panel-on-media`** `{target, over, registration?, distribute?}` — a solid-surface
  panel grid-placed over a media slot. The panel carries an opaque surface token
  (`--c-panel-surface`), so its text never composites against the photo — the sanctioned
  `panel-over-media` pair. `distribute` controls the panel's internal vertical
  distribution (`space-between` = wordmark top / statement center / caption bottom).
- **`straddle`** `{target, registration, maxOcclusion?, endsVisible?}` — the target
  crosses `registration.toSlot`'s `edge` by `depthCols|depthBaselines`. `z: front` rides
  over; `z: back` tucks UNDER the crossed slot and then REQUIRES the G8 occlusion params.
  A text-target straddle onto photography is text-on-media-family (`sanctioned: true`
  under `no-text-on-photos`); a media-target straddle is overlap-family (media-over-seam,
  media-over-media).
- **`scrim-band`** `{target, over, band: {rowStart, rowSpan}, fill: {opacityClass}}` — a
  flat translucent band (NEVER a gradient) crossing the media at media-height fractions,
  carrying the target's content. The gate's text-contrast check sets the opacity floor.
- **`framed`** `{target, widthRel: {to: container, ratio}}` — the media renders at
  `width: framed`: page margins visible on ALL sides, the ratio snapped to whole shared
  columns. Other slots register against the frame (`alignTo`/`registration.toSlot`).
- **`type-behind-media`** `{target, over, maxOcclusion, endsVisible, sanctioned}` — G8.
  REAL heading copy at full opacity rendered `z: back`, media on top. NOT a ghost-word
  and NOT an inverted overlap: the z-ladder still forbids text behind media EXCEPT under
  this contract — `maxOcclusion.class` caps the occluded fraction of the heading's glyph
  area (light≈0.25 / medium≈0.4 / heavy≈0.55), `endsVisible: true` keeps the first and
  last letterforms clear. The composer stamps the computed geometry
  (`data-occlusion`/`data-ends-visible` on the section) and `onbrand_check.py`
  recomputes + enforces it (over budget → reclassify as `ghost-word` + carry a readable
  heading elsewhere).

**`banded` archetype (G9).** `bands: {split, surfaces: [top, bottom]}` renders two
stacked full-width surface bands with a hard horizontal seam at `split` (fraction of
section height, snapped to `--baseline`; a hard cut, never a gradient). Slots straddle
the seam by registering against the reserved slot name `seam`
(`registration: {toSlot: seam, edge: top, depthBaselines: N}`) — realizing WoodWave's
sanctioned `media-over-seam`. For neverDo/readability, content is surface-attributed to
the band it sits on; straddlers to both. Cross-SECTION straddling was explicitly
rejected: model the device as ONE dual-surface section.

**Typographic devices (P3).**
`mixed-face {target, spans}` (copy carries `{lead, emphasis}`; degrades to case/weight
contrast when the brand ships no alternate cut) · `stepped-lines {target, steps,
direction}` (per-line indents in half-column units on an authored multi-line statement)
· `break-frame {target, registration, salience: decorative}` (corner-anchored decoration
crossing a frame edge; area-capped, never over text, decoration-salience gate applies).
