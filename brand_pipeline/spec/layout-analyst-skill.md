---
name: brand-layout-analyst
description: >-
  Extract a target site's layout design language into the canonical brand.yaml.
  Use when analyzing a captured site (screenshots + DOM) to derive surface
  grammar, layout archetypes, grid/width/overlap rules, and per-slot mappings onto
  the AISB Webflow library inventory. Invoke for first-pass brand extraction, for
  re-analyzing a single section after an iteration signal, or whenever you need to
  turn observed sections into brand.yaml layout entries with real library
  component names/ids. Pairs with the webflow-library-aisb skill (component/token
  map) and the signal-loop self-education design.
---

# brand-layout-analyst (the Layout Analyst)

> This is a **spec** for a Cursor skill (USER DECISION #1: the **Layout Analyst** is a
> skill any agent can invoke, NOT a hardcoded pipeline step). It is the extraction arm
> of the **Brand Extractor** pipeline; the **Art Director** (`brand-art-director`) owns
> consolidation. It does not run automatically; an agent reads it and follows the
> method. It writes only to `brand.yaml` (canonical) per `brand-schema.md`. It never
> edits `brand.md` (a rendered projection) and never touches a live site.
>
> **Worked examples reference "the reference brand"** — the first extraction this
> method was proven on. Examples are ILLUSTRATIVE of the method only; never copy their
> values, rules, rhythms, or ids into another brand's extraction. A brand with the
> opposite aesthetic (rounded, filled buttons, light chrome) follows the same method
> and produces entirely different entries.
>
> **`brand.yaml` is library-AGNOSTIC.** Canonical nodes carry *intent* — archetype,
> slot role, primitive/block **contract** (`contracts/primitives.yaml`,
> `contracts/blocks.yaml`), token semantics. The build target NOW is **Tailwind/shadcn**
> (intent → classes); the **Webflow Assembler is DEFERRED** (intent → components). Any
> Webflow-specific ids (component/variable/mode ids, the role table below) are
> **assembler-only annotations** and belong in the optional, non-canonical
> `targetMappings:` block — NOT on canonical token/layout nodes.
>
> **Sign-off notes baked in:** (#5) composite archetypes (`collage`/`overlay`/`band`)
> are realized with **absolute offsets inside the nearest scaffold slot — no new
> components are created**. (#6) `brand.yaml` **indexes** the existing sibling artifacts;
> it references them and never supersedes or deletes them.

## Inputs

- Captured section screenshots + per-section DOM/CSS (e.g. `runs/<brand>/assets/*`,
  `screenshots/*`). Read section-by-section; do NOT load whole inventories at once.
- The library inventory via the **webflow-library-aisb** skill
  (`.cursor/skills/webflow-library-aisb/SKILL.md` → `components.json`,
  `variables.json`). Grep for component names/ids and variable names; never invent ids.
- Any existing `brand.yaml` (for re-analysis / incremental updates).

## Output

- Mutations to `brand.yaml` only, conforming to `brand-schema.md`: `tokens` (intent +
  value, library-agnostic), `surfaceGrammar`, brand `primitives[]`/`blocks[]` overrides
  (against the shared contracts), `layouts[]`, `compositionRules[]`, the three rule lists
  **`do[]` / `avoid[]` / `neverDo[]`**, `voice.dials`, `recipePolicy`. Optionally,
  per-section **`targetMappings.webflow`** annotations for the deferred assembler (never
  on canonical nodes).
- Every decision wrapped in the rule envelope (`value, confidence, source:creation,
  scope, changelog`). First-pass extraction always uses `source: creation`.

## Archetype vocabulary (tied to REAL library scaffolds)

The `archetype` enum maps onto real `Section / *` and `Layout / *` components from
`components.json` (ids verified). Choose the closest scaffold; if none fits, mark
the archetype as a **composite** and compose from primitives (see Gap handling).

| archetype | real library scaffold | componentId | slots | when to use |
|---|---|---|---|---|
| `stack` | `Section / Stack` | `185a3d3a-0806-d61b-7c06-c5fdd636b093` | 1 | single-column hero/bookend/conversion; bg + overlay + width props |
| `split` | `Section / Split / Content and media` | `464eadea-7e5a-f915-2967-4a8d53b13c44` | 2 | content beside media (info band, feature) |
| `split-form` | `Section / Split / Content and form` | `1e71bad3-53f0-ec9b-1456-7048c20d373e` | 2 | content beside a lead form |
| `split-fullbleed` | `Section / Split / Full bleed / Content and media` | `4dc34099-ab5b-36ae-4038-9fba6033f846` | 2 | edge-to-edge split, media bleeds to viewport edge |
| `split-card` | `Section / Split card / Content and media` (+ `- v2`) | `464eadea…`/v2 | 1–2 | boxed split on a contained card surface |
| `stack-fullbleed` | `Section / Stack / Full bleed / Content and media` | `b5c9aa7f-160f-7d95-c514-07e16adcd0e8` | 2 | full-bleed media band with stacked content |
| `grid` | `Layout / Grid` | `d5fba640-4fbd-f78e-5787-c9d5ef9bc1c6` | 1 | N-up card/logo grids (Columns, Gap size props) |
| `bento` | `Layout / Bento /4` | `e3e4b1e1-2787-78b8-a6dc-b2d16bd5f9f9` | 4 | asymmetric 4-cell feature mosaic |
| `row` | `Layout / Row` | `77ad6397-b708-c48f-7bc0-fba0c89e23cb` | 1 | inline horizontal cluster (logos, chips) |
| `layout-stack` | `Layout / Stack` | `1dc9a490-022c-93ee-82d9-23756de94edb` | 1 | inner vertical stack within a section |
| `layout-split` | `Layout / Split` | `c74af562-456b-6df4-f8ab-77794ed53b4f` | 2 | inner two-cell split within a section |
| `header` | `Header` / `Header / Split` | `7cc94828…` / `685a9cc8…` | 1–2 | section heading cluster (eyebrow/heading/subheading) |
| `logos` | `Logos Wrapper` | `f375ff98-6eb2-826d-0e70-4b45d0fd6fc2` | 1 | logo bar |
| `band` *(composite)* | `Section / Stack` + overlay props | `185a3d3a…` | 1 | full-bleed colored bookend; overlap done in-slot |
| `collage` *(composite)* | `Section / Stack` + in-slot `Layout / Stack`/absolute offsets | `185a3d3a…` | 1 | staggered editorial field; **no native scaffold** → compose |
| `overlay` *(composite)* | `Section / Split card` or `Section / Stack` + offset panel | — | 1–2 | panel overlapping media edges; **compose**, library has no overlap primitive |

`band`, `collage`, and `overlay` are **composites**: there is no single library
component that expresses staggered overlap. Use the nearest `Section / *` scaffold
for the surface + slot shell, then build the inner composition from leaf primitives
(see Phase 3 + Gap handling).

## Method — 4 phases

### Phase 1 — Section segmentation

Goal: split the captured page into an ordered list of sections, each a candidate
`layouts[]` entry, and record the page-level surface rhythm.

1. Walk the page top → bottom. A **section** = a top-level full-width band that owns
   a background surface and a coherent content group. Use DOM `<section>`/top-level
   children as the first cut; merge/split by visual surface boundaries from screenshots.
2. Assign each section a stable `sectionId` slug (e.g. `opening-bookend`,
   `about-run`, `info-band`) and register it in `provenanceIndex` (url, node,
   screenshot).
3. Record the **page rhythm**: the ordered list of surface roles across sections →
   `surfaceGrammar.pageRhythm`. (The reference brand, illustrative: inverse → primary →
   band → primary → inverse → inverse-strong.)
4. Note **seam behavior** between consecutive sections (hard cut vs gradient/fade vs
   bridging element) → `surfaceGrammar.transition` + any one-off bridging device.

Output: skeleton `layouts[]` (id + provenance only) + `surfaceGrammar.pageRhythm`
+ `surfaceGrammar.transition`. **Write to `brand.yaml` now** before Phase 2.

### Phase 2 — Layout-archetype extraction

For each section, capture the structural skeleton. Record each observable as a rule
envelope (`source: creation`).

1. **Surface semantics** — identify the section background/surface role
   (`surface/primary|inverse|inverse-strong|panel`) and the Color-schemes **mode**
   that themes it (`surfaceMode` + `modeId`). Map raw bg hex → a `tokens.surfaces`
   entry. Detect child-surface nesting (e.g. panel inside inverse) →
   `surfaceGrammar.nesting`.
2. **Section gutters / padding** — vertical section padding tier and horizontal
   container gutter; map to `Section/Section Padding Vertical` and a `Container/*`
   width. Record per-breakpoint ladder if visible → `tokens.spacing` +
   `widthRules.container`.
3. **Grid observability** — `columns` (1, 2, N, bento-4), `stagger`
   (none | alternating-anchors | offset), `overlap` (none | which sanctioned type),
   and inter-item `gap` (map to `Spacing/*` or `Grid gap` mode) → `gridRules`.
4. **Width constraints** — content max-width (`full-bleed` | `Width`/`Width LG`/
   `Width SM` preset) and text **measure** (e.g. "~1/3 container", "~50%", ch cap)
   → `widthRules`.
5. **Overlap rules** — enumerate sanctioned overlap types present
   (display-text-over-media, media-over-media, panel-over-media, media-over-seam)
   and the z-order ladder → `overlapRules` + (if cross-cutting) `compositionRules`.

Pick the `archetype` from the vocabulary table and set `scaffold`
(component + componentId). **Write each section's layout entry to `brand.yaml` as it
is completed** (incremental save discipline).

6. **Content-shape signature capture (NEW).** Beyond archetype + grid, capture the
   *content shape* — the detail that makes a section reusable as a PATTERN. For each slot
   record, expressed as RELATIONSHIPS/CLASSES, never px (they resolve later against the
   STYLE scale + brand tokens):
   - `textLen` (`none|word|short|medium|long`) — short ≈ eyebrow/caption (≤6 words), long
     ≈ body copy (>40 words). This is how the pattern encodes "SHORT eyebrow + LONG body".
   - `sizeClass` (`colossal|hero|display|title|body|caption`) and, where a slot's size is
     visibly tied to a neighbour, `sizeRel: { to: <slot|container>, ratio, axis }` — e.g. a
     body column measured to ~1/3 the container, or a ghost word ~1.4× the media width.
   - media slots: `mediaAspect` + `mediaScale: { of, fraction }`; `opacityClass` for
     ghost/watermark slots; `z` (`back|mid|front`).
   - **Aspect-ratio PALETTE (page-level, once).** Measure the real dimensions of every
     source image and consolidate into `tokens.imagery.aspectPalette` (roles like
     `band`/`landscape`/`near-square`/`portrait`, each `{value, role, provenance}`) — the
     brand's ratio VARIETY is a signature (anti-ai-slop.md AS-17); a single hardcoded
     ratio per section flattens it. Composers read the palette via `--c-aspect-*` vars.
   - **Special treatments** — the signature devices — into `specialTreatments[]`:
     `ghost-word` (colossal watermark word behind/straddling media), `overlap`, `stagger`,
     `bleed`, `marginal-caption`, `text-on-media`. Record each device's target/pair/anchor/
     `amount.class` (`light|medium|heavy`). *This is exactly the reference brand's detail —
     the giant ghost word floating around the photo, the margin micro-caption, the
     alternating stagger.* Capture the PATTERN, not the pixels.
   - **Alignment coherence — `contentShape.alignment` (REQUIRED whenever any slot is
     centered).** Do not stop at recording the block's own alignment as a `variantKnob` —
     that alone silently drops what happens to SIBLING slots (this is precisely how a real
     gap slipped through: the reference brand's conversion stack recorded `align: center`
     but nothing said the body/form should ALSO center or share the body's measure, so the
     render came back with a centered heading over a left-anchored, full-width form). Record:
     `alignment.value` (center/left/mixed), `alignment.inheritance`
     (block-inherits/per-slot-override), and `alignment.rule` stating the OBSERVED behavior
     for THIS pattern family — it is **not universal**: a CTA/conversion block's centered
     heading conventionally centers every sibling too (and a control/form shares the body's
     measure, never a bare full-width default); a section-level HEADER block (an intro
     heading over a longer body run) can center only the heading while the body stays
     left-anchored — state which case applies, do not assume.
   - **Control-measure requirement.** Any slot with `sizeClass: control` (a form/input/
     button row) MUST carry an explicit `width` or `sizeRel` — a control has no natural
     "measure" the way a paragraph does, so an unrecorded control silently defaults to
     stretching the full container in the renderer. Prefer `sizeRel: { to: body, ratio:
     1.0, axis: width }` over a bare `width: stretch` unless the source genuinely shows the
     control running edge-to-edge.
   - **Scroll-parallax motion (`kind: scroll-parallax`, brand-schema.md §4.4.1).** Check the
     source DOM/CSS for a Webflow IX2 (or equivalent) scroll-linked interaction: sample the
     SAME element's computed `transform` at 2+ scroll depths (not just once) — a static
     entrance animation settles to ONE final value and stays there; a scroll-parallax value
     keeps changing proportional to scroll position. A wrapper element whose class name
     hints "wrp"/"mask" around a single `<img>` with a changing `translate3d(0, Ypx, 0)` is
     the `mask-pan` mode. When the pattern ALSO has an `overlap` treatment between two MEDIA
     slots (not text-over-media), check whether BOTH images carry independent scroll-linked
     transforms at DIFFERENT rates — that is the `depth` mode, recorded by adding a
     `scroll-parallax` entry that references the SAME `pair` the `overlap` entry already
     names (do not duplicate the pair data). Record the OBSERVED brand-level toggle in
     `voice.motionSpec.imageParallax` (§4.4.1) — this is a BRAND rule (applies to every
     module image), not a per-section variantKnob — with `amount` matching the brand's own
     `voice.dials.motion` (never invent a heavier motion than the brand's locked dial).

### Phase 2.5 — Use-case classification + reuse-before-create against the library (NEW)

This phase makes layouts REUSABLE and stops re-inventing section HTML/CSS. It runs the
two-tier layout library (`brand_pipeline/layout_library.py`; schema `layout-patterns.v1`,
`brand-schema.md` §4.4/§5.5, Appendix C).

1. **Classify the section by USE-CASE** (`hero|features|pricing|testimonial|gallery|cta|
   about|faq|logos|footer`) from its role + copy. A hero and a pricing section are
   different use-cases with different vocabularies; keep them separate.
2. **Build a retrieval query** from the section's content-shape (Phase 2 step 6): observed
   `textLen` classes, media presence/aspect, `specialTreatments` kinds, `surfaceIntent`.
   Call `layout_library.match(query, <brand.yaml>)` — it scores PROJECT patterns first,
   then STANDARD, and hard-filters any pattern whose treatments would break a brand
   `neverDo` (the only hard gate). It returns `reuse` / `adapt` / `miss`.
3. **reuse / adapt** → do NOT re-invent structure. Set the `brand.yaml layouts[]` entry's
   `patternRef: { lib, id }` to the chosen pattern and (for `adapt`) record the tuned
   `variantKnobs`. The section now generates FROM the pattern.
4. **miss** (nothing close enough) → capture this section's content-shape as a NEW pattern
   and `layout_library.promote(<patternDict>, <brand.yaml>)` it into
   `runs/<brand>/brand/layout-library.yaml` as `origin: extracted` (with `provenance`,
   `confidence`, `changelog`), then set the layout's `patternRef` to it. Next run it is a
   reuse. **Project patterns win over standard on ties** — this is how a project builds its
   own signature layout library on top of the shared base.

> Reuse-before-create for LAYOUTS is the same discipline the skill already applies to
> contracts (Phase 3): reuse an existing pattern, adapt via knobs, and only create on a
> true miss — promoting the creation so it is reusable next time.

### Phase 3 — Per-slot mapping (contracts now; Webflow components deferred)

For each section, map each slot's semantic role onto a **primitive/block contract**
(`contracts/primitives.yaml`, `contracts/blocks.yaml`) and record it in the canonical
`layouts[].blockMapping[]` with library-agnostic intent props (see `brand-schema.md`
§4.2 / §5). This is **reuse-before-create** against the shared contracts.

> The real-library role map below (component names + ids + Title-Case props) is for the
> **DEFERRED Webflow Assembler** — emit it as per-section `targetMappings.webflow.layouts.<id>.components`,
> NOT onto canonical nodes. The Tailwind/shadcn renderer needs only the contract intent.

1. List the scaffold's slots (Phase 2 archetype → `slots[]`; e.g. `Section / Split`
   has `Slot` + `Slot 2`).
2. For each content element in a slot, find the **closest existing library
   component**: query via the webflow-library-aisb skill (grep `components.json`
   for the name → id) or the role map below. Prefer leaf primitives:
   `Heading`, `Subheading`, `Eyebrow`, `Paragraph`, `Rich Text`, `Image`, `Logo`,
   `Link / Primary`, `Link / Secondary`, `Form / Webflow / Lead`, `Card / Wrapper`.
3. Record `{ slot, role, component, componentId, props }` with real prop names
   (Title Case, from `components.json`).
4. **Brand-rule overrides** take priority over visual mimicry. E.g. a brand carrying a
   typographic-primary `neverDo` maps a CTA to `Link / Secondary` (arrow style), never
   `Button / Primary`, even if it looks button-like — while a filled-button brand maps
   the same CTA straight onto `Button / Primary`.

Verified role map from the reference brand's extraction (illustrative — real ids for
THAT library; derive your own from the active inventory):

| brand role | library component | componentId | key props |
|---|---|---|---|
| display & section headings | `Heading` | `b2fd0399-aede-b4e1-bd06-56c8171fc86e` | Text, Style, Tag (h1/h2/h3) |
| eyebrow / overline / caption | `Eyebrow` | `0add895d-ff42-8ef4-91cb-0eff2e60b2f6` | Text, Style |
| lede under heading | `Subheading` | `b9ff6088-addf-fd27-a6e6-924b468f4775` | Text |
| body copy | `Rich Text` | `168eb097-8c4f-7053-ad79-34bc90c5d144` | Content |
| photography | `Image` | `6310b519-341d-abdd-6429-69c8d2c0f91a` | Image, Alt Text, Aspect ratio, Radius, Link |
| typographic action (no pills) | `Link / Secondary` | `75c4556a-b7c2-b1f3-2d05-0ea2dbee7fc8` | Link, Label, Size, Style |
| accent action on dark | `Link / Primary` | `f4011c6d-2d1a-fe52-2b09-f69962b38d4b` | Link, Label, Size, Style |
| brand mark | `Logo` | `e0a8f694-256a-253e-2b47-350921c8e3fc` | Image, Alt Text, Color, Size |
| newsletter / lead form | `Form / Webflow / Lead` | `f5fc0862-ff04-59e0-1011-79aa7d4c39db` | Type/Style variants, Form ID, per-field props |

**Write `componentMapping[]` into each layout entry now.**

#### Gap handling — reuse-before-create / compose-from-primitives

When no single component matches a slot's content:

1. **Reuse first.** Re-check the inventory for a variant/prop that covers the need
   (e.g. dark theme = a Color-schemes **mode**, not a new component; a "muted"
   caption = `Eyebrow` Style variant). Theme with modes, not new colors.
2. **Compose from primitives.** For composites (`collage`, `overlay`, `band`):
   instantiate the nearest `Section / *` scaffold for the surface/slot shell, then
   fill slots with leaf primitives arranged via `Layout / Stack`/`Layout / Grid` +
   offset utilities. Record the composition in `componentMapping[]` as multiple
   primitive rows on the same slot (as in the reference brand's collage and hero
   bookend examples).
3. **Create only on a true miss.** If a genuinely new reusable component is needed,
   note it in `recipePolicy`/changelog as a `create` action and define it by
   composing existing primitives + forwarding their props (prop-binding workflow in
   the webflow-library-aisb skill). Do not invent ids; creation happens at build
   time, the skill only records the intent + provenance.

### Phase 4 — Rule synthesis into `brand.yaml`

Consolidate per-section observations into the canonical document:

1. **De-duplicate into design-language rules.** Observations that recur across ≥2
   sections with consistent values become `compositionRules`/`surfaceGrammar` entries
   at `scope: design-language`, `confidence: high`. Single-occurrence observations
   stay `confidence: low` and (if they would generalize unsafely)
   `scope: one-off` (e.g. the reference brand's seam-bridging photo).
2. **Synthesize the three rule lists** `do[]` / `avoid[]` / `neverDo[]`:
   - `do[]` — positive prescriptions / affirmative house style (e.g. "all actions are
     typographic arrow links"). High-confidence, source: creation.
   - `avoid[]` — soft discouragements ("prefer asymmetric editorial runs").
   - `neverDo[]` — hard prohibitions from absences + anti-patterns (no buttons, no
     radius, no shadows, no gradients, …). Each a high-confidence prohibition.
3. **Set the locked dials** (`voice.dials`: variance/motion/density) from overall
   variance, observed motion, and content density. Mark inferred dials (e.g. motion
   when hover is unobservable) as `confidence: medium|low`.
4. **Set `recipePolicy`** flags (scaffoldFirst, reuseBeforeCreate,
   composeFromPrimitives, themeViaModes, slotsTakeInstancesOnly) — for the AISB
   library these are all `true`.
5. **Confidence + provenance everywhere.** Every entry carries `confidence`,
   `source: creation`, `scope`, `provenance[sectionIds]`, and an initial `changelog`
   `created` record.
6. **Re-render** `brand.md` via `render_brand_md(brand.yaml)` (do not hand-write it)
   and confirm the projection reads cleanly for human review.
7. **Reconcile the project layout library** (`runs/<brand>/brand/layout-library.yaml`)
   across runs — **append/reconcile, never overwrite**. A pattern seen again with the same
   shape raises `confidence` and may promote `one-off`→`design-language`; a conflicting
   observation lands `scope: one-off` and enqueues a signal (`signal-loop.md`). A standard
   pattern truly observed here is promoted INTO the project library as `origin: extracted`
   (the one-way ratchet, `brand-schema.md` §5.3) — never the reverse.
8. **Check `anti-ai-slop.md` before calling the render done.** This is a MANDATORY step,
   not optional polish — `onbrand_check.py` verifies brand-rule *values*, it does not catch
   context-blindness bugs (a color that's right on one surface and invisible on another, a
   spacing literal that looks fine at one viewport and huge at another, dispatch logic that
   silently breaks the moment a pattern is reused under a new id). Two of the checks are
   SCRIPTED — run both on every composed page:
   - `node brand_pipeline/contrast_audit.mjs <index.html>` — WCAG contrast for every text
     element vs its EFFECTIVE background + every section's hover state (AS-01/AS-10).
   - `node brand_pipeline/slop_audit.mjs <index.html>` — section content-completeness:
     metadata-only sections, empty grid columns, maps without address text, forms without
     a stated reason (AS-11..AS-14).
   Skim the rest of the rule list against what was just built; when a NEW instance of one
   of these failure shapes is caught, add an entry — don't just fix it and move on.

## Operating rules (inherited)

- Read economically: section-by-section; grep the inventory JSONs for names/ids,
  never load them whole.
- Never invent component ids, prop names, variable names, or token hex — source them
  from the real files. If unknown, record `confidence: low` and queue a question via
  the signal loop rather than guessing.
- Write to `brand.yaml` incrementally (after each phase/section) so partial progress
  is never lost.
- On contradiction with an existing rule during re-analysis, follow the
  **one-off-and-queue** default from `signal-loop.md`: apply as `scope: one-off`,
  do not promote, enqueue the clarifying question.
