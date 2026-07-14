---
id: composition-rules
layer: composition-grammar        # NOT a visual style; the universal grammar the AI composes within
kind: composition-rules
assembled_at: generation-time     # merged with brand neverDo/scales + render_pattern_constraint seeds per run

# ── on-disk registry (documentation; NOT injected, NOT machine-parsed) ──
# The prompt builder (brand_pipeline/generate_composition.build_prompt) injects ONLY the
# "normative core" prose between this front-matter and the COMPOSITION-CORE:END sentinel.
# Everything below the sentinel is the extended edition (rationale, device notes, case
# detail) — on-disk reference for humans/agents, never prompt payload. Keep the three
# layers consistent: this registry, the core, and the extended notes. Values reference the
# REAL vocabulary (composition.v1.schema.json / §4.4 / contracts/*.yaml) — no invented fields.

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

# Composition rules (normative core)

You emit ONE `composition.v1` object: ordered sections, each = archetype + slots
(primitive/block refs) + treatments + inline copy. A deterministic renderer draws it;
`onbrand_check.py` validates it. You NEVER write HTML/CSS and NEVER re-author a `c-*`
primitive (`component_render.py` is the single source of truth). Arrange the vocabulary well.

## 1. Palette & slot grammar

- Archetypes — only these are drawable: `stack`, `collage`, `split`, `stack-fullbleed`,
  `cards`, `interlock`, `overlay`, `banded`. A novel *arrangement* lives WITHIN one.
- Every `slot.contract` must be a key from the primitives/blocks catalogs injected below.
  Never invent a contract key.
- Respect each block's slot grammar: `accepts` (legal fillers), `?optional` (may be empty),
  `*repeatable` (holds a list — bind an ARRAY of `copy` to render N items).
- Recursion: scaffold → block → primitive. Never a scaffold inside a block.

## 2. Hard constraints (brand neverDo)

The ACTIVE brand's `neverDo` rules arrive under "## Brand facts" as `id: statement` pairs.
They are the ONLY non-overridable layer: one violation fails the gate. Realize each
statement STRUCTURALLY — choose primitives, treatments, and surfaces so it holds by
construction. Common shapes: a flatness rule → separation via fill contrast and hard
edges; a typographic-primary rule → `cta` role renders as a `link` (arrow/slash), not a
`button`; an accent-scope rule → accent only on its declared surfaces; a text-on-photo
rule → captions to the margin, EXCEPT the brand's named sanctioned exception (emit that
treatment with `sanctioned: true`); a container-discipline rule → open composition, no
boxed cards on the named surfaces; an alignment rule → centering only for the named roles.
Presume nothing about palette, radius, component family, or section order.

## 3. Values are tokens · units are cq · spacing is a named step · type is a tier

- Colors: emit `tokens.colors` roles / surface roles — never a raw hex.
- Units: sizes/rhythm are classes (`sizeClass`, `width`, `amount.class`, `mediaScale`)
  the renderer resolves to `cqw/cqh/cqi`. Never `vw`/`vh`/`dvh`, never a px literal.
- Spacing: pick a NAMED step from the merged style `spacing.scale` (`3xs`…`2xl`) or the
  brand's measured `tokens.spacing` step (brand preferred). Never an ad-hoc gap.
- Type: `sizeClass` ∈ `colossal|hero|display|title|body|caption` → brand type tier; the
  base-style display floor applies. ONE slot per section carries the display tier.

## 4. Treatments (intensity `amount.class`: light | medium | heavy; stackable)

- `stagger` — offset sibling modules along an axis; heavy ≈ 1/3-container offset.
- `overlap` — two slots overlap with explicit `zOrder`; ONLY pairs the brand's
  `compositionRules` sanctions (display-text-over-media, media-over-media,
  panel-over-media, media-over-seam).
- `ghost-word` — oversized low-opacity watermark (`anchor: behind-media|straddle-media|
  margin|full-bleed`, `bleed: none|partial|full`); ghost-watermark tier + ghost token.
- `bleed` — media runs off an `edge: left|right|top|bottom|all`.
- `marginal-caption` — micro-caption pinned in the margin (`side: left|right`).
- `float-wrap` + `inset` — statement wraps an inset image (~50% measure) — `interlock`.
- `panel-on-media` — solid-surface panel grid-placed OVER media; text sits on the panel,
  never the photo; `distribute: start|center|space-between`; every neverDo holds inside.
- `straddle` — `target` crosses another slot's edge, declared with the same
  `registration {toSlot, edge, depthCols|depthBaselines, z}` grammar as any overlap.
  `z: front` rides over; `z: back` tucks under and carries the G8 occlusion contract.
  TEXT-target onto photography = text-on-media family (needs `sanctioned: true`);
  MEDIA-target (media-over-seam / media-over-media) = overlap family, no text sanction.
- `scrim-band` — FLAT translucent band (never a gradient) crossing media at
  `band: {rowStart, rowSpan}` (fractions of media height), carrying the `target` slot;
  `fill.opacityClass: light|medium|heavy` ≈ 0.35/0.55/0.75 of the inverse surface; the
  text-contrast gate sets the floor — use `medium`+ under caption text on busy photos.
- `framed` — media at `width: framed`: page margins visible on ALL sides, snapped to
  whole shared-grid columns; the frame is an inset canvas other slots register against.
- `type-behind-media` — G8: REAL heading at FULL opacity rendered `z: back` under media
  (NOT a ghost-word). Legal only with `maxOcclusion` class (light≈0.25 / medium≈0.4 /
  heavy≈0.55 of glyph area) AND `endsVisible: true` (first/last letterforms clear); the
  gate recomputes occlusion and fails over budget — above the cap, reclassify as
  `ghost-word` and carry the real heading elsewhere. Text-on-media family (sanction it).
- `mixed-face` — one heading, two faces via `spans: [{part: lead, face: roman},
  {part: emphasis, face: italic}]`; no italic cut shipped → degrade to case/weight
  contrast, never fake-italicize.
- `stepped-lines` — authored multi-line statement; line indents step progressively
  (`steps` in HALF-column units, `direction`) as registered grid indents.
- `break-frame` — corner-anchored decorative media crossing a `framed` slot's edge;
  decoration ONLY: area-capped, never covers text (decoration-salience gate).
- `counter-rotate` is in the vocabulary but has no composer yet (inert).
- Legality: `text-on-media` maps to a carried text-on-photo `neverDo` — illegal except
  that brand's named sanctioned exception, emitted with `sanctioned: true`. Any device
  realizing a shape a carried `neverDo` forbids (bounded card, shadow, gradient, radius)
  is illegal for that brand. Keep stacked treatments on the z-ladder:
  ghost-watermark → media → panels → text.

## 4b. Placement on the ONE shared grid (all fields optional; omitted = measured default)

- The page carries one registration grid (`--grid-cols: 12` + shared gutter + baseline).
  Give slots `colStart`/`colSpan` so edges land on column lines; a deliberate break is a
  registered nudge (`offsetCols`/`offsetBaselines`, fractional allowed) — never raw %/px.
- Per-section `alignment: {anchor}` ∈ `centered|left|right|space-between|edge-to-edge|
  mixed`. An asymmetric anchor MUST name its `counterweight` slot (media, ghost word,
  panel) or the section reads crammed against a void. Omission is NOT blessed (AS-18):
  the composer resolves pattern `contentShape.alignment` → style role default and stamps
  the winner.
- Offset media (AS-19): media pushed off the text axis is legal ONLY under a resolved
  side anchor, or when the offset slot IS the registered counterweight; under a resolved
  `centered` anchor media spans stay symmetric — else the media-registration check fails.
- Every overlap declares `registration {toSlot, edge, depthCols|depthBaselines, z}`.
  A multi-image cluster = N registered overlays with explicit back→front `z`.
- `mediaAspect` resolves to a real aspect-ratio: `wide` 21/9 · `pano` 3/1 · `portrait`
  3/4 · `square` 1/1 (also `landscape`, `freeform`). Pick the aspect that serves the
  composition. Width classes: `hug|stretch|fixed|media|full-bleed|framed`.
- A media slot with `z: back` + `width: full-bleed` is a true background layer = a
  TEXT-ON-MEDIA treatment: legal only where sanctioned (`sanctioned: true`); the renderer
  adds a flat scrim for AA. A small `z: front` image corner-pins via `alignTo: {corner}`.
- `overlay` archetype = the section IS one layered device: every slot places by
  `colStart/colSpan` + `z: back|mid|front` in one positioning context. Prefer it over
  bolting many overlaps onto `stack`.
- `banded` archetype = two stacked full-width surfaces with a HARD horizontal seam
  (`bands: {split, surfaces}`; never a gradient). Slots straddle via
  `registration: {toSlot: seam, edge, depthBaselines}` — the media-over-seam pair
  (sanction it). Content is surface-attributed per band; cross-SECTION straddling is
  unsupported — model the device as ONE banded section.
- Readability is a gate, not a vibe: text-contrast (media/scrims) and decoration-salience
  (ghost/back layers) FAIL sections whose text loses contrast or whose decoration shouts.
  Compose so text always sits on a quiet field.

## 5. The freedom envelope (invent WITHIN the invariants)

You MAY freely choose: module count (2–4 — render N value_props as N modules, never one
paragraph); column ratios (`1.2:1`, `1.6:1`, `2:1` preferred; even `1:1`/centering for
hero + cta); z-order within the ladder; WHICH slot gets the display tier and WHICH single
element carries the one accent (respect accent-scope rules); SELECT + ORDER the sections
for the brief. You MAY propose a NOVEL pattern (`novelty: novel`, `seededFrom: null`)
when the brief needs a structure the library lacks — it must still validate against the
schema and pass every `neverDo`; if it gates green it becomes eligible for promotion into
the project library. Novelty and the off-grid treatments are GATED by the run's expansion
capability: obey the "Expansion capability" block injected right after this grammar
(UNLOCKED → novel + off-grid legal; LOCKED → reuse/adapt captured patterns only).
`ghost-word`, `marginal-caption`, `inset`, and the sanctioned hero `text-on-media` are
style identity, always legal regardless. Seeds BIAS when unlocked, CAGE when locked —
prefer reuse/adapt either way; reach for novel deliberately.

## 6. Precedence (three tiers)

1. Base-style invariants (advisory-STRONG — the gate warns).
2. This grammar (palette, slot grammar, treatment legality, values ethos, envelope).
3. Brand `neverDo` — the ONLY hard layer; a violation FAILS the gate.

<!-- COMPOSITION-CORE:END — nothing below this line is injected into generation prompts -->

# Extended edition — rationale, device notes, case detail (on-disk reference; NOT injected)

> The core above is the normative text the generating LLM reads. This extended edition
> preserves the full guidance with rationale and worked detail. When editing, keep the
> registry (front-matter), the core, and this edition consistent — the golden test
> (`tests/test_grammar_core.py`) enforces the core's vocabulary completeness and budget.

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

Hard constraints are the ACTIVE brand's `neverDo` rules, injected under "## Brand facts"
at generation time. They are the only non-overridable layer: a composition that violates
any injected rule FAILS the gate. Rules arrive as `id: statement` pairs — realize each
statement STRUCTURALLY in what you emit (choose primitives, treatments, and surfaces so
the statement holds by construction, don't merely avoid naming the forbidden thing).

Illustrative rule *shapes* only — NONE of these is active unless the injected brand
facts carry it:

- a **flatness** rule (no shadows / gradients / radius) forbids soft separation, so
  separation must come from fill contrast and hard edges;
- a **typographic-primary** rule remaps the `cta` role onto a `link` primitive
  (`variant: arrow`/`slash`) instead of a `button`;
- an **accent-scope** rule restricts the accent color to its declared surfaces;
- a **text-on-photo** rule forbids overlaying text on photography, with captions moved
  to the margin — except where the brand names a sanctioned exception (emit that
  treatment with `sanctioned: true`);
- a **container-discipline** rule forbids bounded cards/boxes on some surfaces, making
  open composition the default there;
- an **alignment** rule reserves centering for specific section roles and keeps
  editorial runs anchored/asymmetric.

Nothing in this section presumes a palette, a radius, a component family, or a section
order — obey exactly what the active brand's injected rules state, no more and no less.

## 3. Values are tokens · units are cq · spacing is a named step · type is a tier

- **Values are tokens.** Colors resolve to `tokens.colors` roles (`surface/inverse`,
  `text/on-primary`, `accent/highlight`, …). Emit token REFS or surface roles — **never a
  raw hex**. Accent placement obeys the brand's accent-scope `neverDo` rules when carried.
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
- **`overlap`** — two slots overlap with an explicit `zOrder`. Sanctioned pairs only —
  read the ACTIVE brand's `compositionRules` overlap entry for which pairs it sanctions;
  typical pair vocabularies: display-text-over-media, media-over-media, panel-over-media,
  media-over-seam.
- **`ghost-word`** — an oversized low-opacity watermark word behind content
  (`anchor: behind-media|straddle-media|margin|full-bleed`, `bleed: none|partial|full`).
  Uses the `ghost-watermark` type tier + `text/ghost-on-primary`.
- **`bleed`** — media runs off an `edge` (`left|right|top|bottom|all`).
- **`marginal-caption`** — a micro-caption pinned in the margin `side: left|right` beside
  media (the classic caption answer for a brand whose `neverDo` forbids text on photos).
- **`float-wrap` + `inset`** — a statement wraps around an inset image (the incoming
  `interlock` archetype). `inset` sizes the floated media (~50% measure).
- **STACKING:** treatments may combine on one section — e.g. `ghost-word` (back) +
  `stagger` (modules) + `marginal-caption` is a common editorial-collage signature; a
  hero may stack a sanctioned `text-on-media` + `overlap`. Keep `zOrder` consistent with
  the brand z-ladder (ghost-watermark → media → panels → text).
- **ILLEGAL / conditional:** `text-on-media` maps to a brand's text-on-photo `neverDo`
  when carried, and is then illegal EXCEPT that brand's named sanctioned exception
  (emitted with `sanctioned: true`, e.g. a hero `display-title-over-media`).
  `counter-rotate` is in the vocabulary but has no composer yet (inert). Any device that
  would realize a shape a carried `neverDo` forbids (a bounded card, a shadow, a
  gradient, a radius) is illegal for that brand — it maps to the matching rule.

### 4a. The overlay family (editorial-harvest-2026-07)

These devices live on the `overlay`/`banded` archetypes and REUSE the §4b placement
vocabulary (grid columns + `registration`) — no parallel mechanisms:

- **`panel-on-media`** — a solid-surface panel (`target`, usually `contract: media-text`)
  grid-placed OVER a media slot (`over`). The panel carries its own opaque surface, so the
  text inside it never touches the photo — this realizes the `panel-over-media` overlap
  pair (sanction it per the brand's `compositionRules`), and the panel's internal stack
  distributes by `distribute: start|center|space-between`. Every carried `neverDo`
  (flatness, radius, …) still holds inside the panel.
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
  `registration: {toSlot: seam, edge: top|bottom, depthBaselines}` — the
  `media-over-seam` overlap pair (sanction it per the brand's `compositionRules`).
  Content is surface-attributed to the band it sits on (straddlers to both) for the
  neverDo/readability checks. Cross-SECTION straddling is deliberately unsupported:
  model the whole device as ONE banded section.
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

- **Module count:** 2–4 modules in a features/collage/cards run (the classic structured-
  representation ceiling — render N value_props as N modules, not one paragraph).
- **Column ratios:** asymmetric splits (`1.2:1`, `1.6:1`, `2:1`); reserve even `1:1` /
  centering for hero + cta.
- **Z-order:** author the layering within the ladder.
- **Emphasis:** choose WHICH slot gets the display tier and WHICH single element carries the
  one accent (respecting the brand's accent-scope rules where carried).
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

1. the **normative core** of this file (the prose between the front-matter and the
   `COMPOSITION-CORE:END` sentinel — the front-matter registry and this extended
   edition are NOT injected),
2. the **merged base STYLE** (`styles.load_and_merge(style_id, brand)` → invariants, soft
   options, spacing/type scale, display floor),
3. the **brand** `neverDo` ids + statements, token color roles, and measured `type` tiers /
   `spacing` steps (from `brand.yaml`),
4. the **primitives/blocks catalog signatures** (contract keys + slot grammar), and
5. the **seed block** from `layout_library.render_pattern_constraint([...])` for the
   selected use-cases (produced by `generate_composition.seed_patterns`).

The seeds constrain toward reuse; the freedom envelope + `novelty:novel` keep the ceiling
open. The output is a single `composition.v1` object.
