---
name: brand-layout-analyst
description: >-
  Author the canonical brand evidence set (brand.yaml + section-copy.yaml +
  layout-library.yaml + tagged assets) from a Phase-A extraction evidence bundle
  (DOM/CSS mining, computed measurement, section crops, vision grounding).
  Use after the extraction tools have produced runs/<brand>/brand/evidence/;
  the authoring pass is DONE only when tools/extract/validate_brand_evidence.py
  passes (C1–C15). Invoke for first-pass brand authoring, for re-authoring after
  new evidence, or to repair a specific validator failure.
---

# brand-layout-analyst (the evidence-first Layout Analyst)

> This is the normative authoring spec consumed by the executable
> `brand_pipeline/author_brand.py` stage. It is the AUTHORING arm of the Brand
> Extractor: it turns the machine-mined evidence bundle into the canonical brand
> files through the configured repository model provider. It never touches a live
> site and never hand-edits rendered projections (`brand.md` and
> `style-scale.yaml` are regenerated from canonical data).
>
> **The contract is explicit: you owe exactly what the validator checks.** A brand
> folder is not "done" when the YAML looks plausible — it is done when
> `./venv/bin/python tools/extract/validate_brand_evidence.py --brand <brand>` exits
> clean. Every check (C1–C15, below) encodes a real failure this repo has already
> shipped once; treat a validator error as a missed observation, not red tape.
>
> **Worked examples are illustrative of the method only.** Never copy another brand's
> values, rules, rhythms, hexes, or ids into a new extraction. A brand with the
> opposite aesthetic follows the same method and produces entirely different entries.

## Inputs — the Phase-A evidence bundle

All under `runs/<brand>/brand/evidence/` (plus the capture itself). Produced by the
extraction tools; read them section-by-section, never all at once:

| file | producer | what it grounds |
|---|---|---|
| `dom-sections.json` | `tools/extract/mine_dom.py` | section census: order, wrappers, per-section tag/class/text/img inventory, repeated-module counts |
| `css-rules.json` / `css-facts.json` | `tools/extract/mine_css.py` | authored CSS: hover rules, transitions, radii, shadows, chrome-presentation devices (casing, separators), motion evidence |
| `motion-audit.json` | `tools/extract/mine_motion.py` | per-selector transition/animation/@keyframes table (property, duration, easing, delay), keyframes definitions, resolved timing custom-properties, duration/easing censuses — the evidence `tokens.motion` is authored from |
| `computed-styles.json` | `tools/extract/measure_computed.py` | browser-computed styles per sampled element — the BUTTON VARIANT-MATRIX evidence and the real type/spacing/surface numbers; `tiers` = the CANONICAL-TIER LADDER (the page re-measured at 1920/1440/960/375, every block stamped with its tier: type registers, container width facts, heading-emphasis facts) |
| `section-rects.json` | `tools/extract/measure_computed.py` | section y-ranges (drives cropping) |
| `crops/` + `crops-manifest.json` | `tools/extract/slice_sections.py` | per-section screenshots |
| `grounding/*.yaml` | `tools/extract/ground_sections_vision.py` | per-section VISION grounding (`section-grounding.v1`): creative direction, component anatomy, verbatim copy, surface relationships |
| `../assets/` + `assets-manifest.json` | `tools/extract/curate_assets.py` | the real downloaded image/logo/font files |
| `runs/<brand>/assets/source-chrome.v2.json` | chrome extractor | the measured nav/footer contract |

Plus: existing canonical files when re-authoring, `contracts/primitives.yaml` /
`contracts/blocks.yaml`, and the standard pattern library
(`brand_pipeline/layout_library.py`).

## Outputs — the mandatory set (what the validator C1–C15 verifies)

1. **`brand.yaml`** (schema: `spec/brand-schema.md`) — tokens (colors/type/spacing/
   surfaces/motion, every type tier with measured `weight` and `case`;
   `tokens.motion` derived from `evidence/motion-audit.json`), **`meta.canonicalTier`**
   declaring which measured breakpoint every canonical value refers to (C14), **per-tier
   type ladders** — every sized role carries ≥ 2 breakpoints in its `sizeRem` ladder
   (base/tablet/mobileL/mobile, grounded in the measure stage's tier samples, h1–h6
   where evidenced) or an explicit `singleTierConfirmed: true` — and the **relational
   spacing ladder** as named `<role>-to-<role>` tokens (eyebrow-to-heading,
   heading-to-body, body-to-cta, … — or `relationalLadder: {notObserved, reason}`,
   C15), `surfaceGrammar`
   (incl. `pageRhythm`), `buttons:` with the **FULL measured variant matrix** — every
   observed action family (primary/secondary/tertiary/textCta…), each with `radius`,
   fill/ink facts and at least one state fact; one family only with
   `buttons.singleVariantConfirmed: true` after re-checking (schema §10.2) —
   `primitives[]`/`blocks[]` overrides where **every contract block type is either
   evidenced or explicitly `notObserved: true`** (schema §10.1; `card` is the
   historical miss — card anatomy is a COMPONENT, never layout prose), `layouts[]`
   one entry per observed section with `patternRef`, `navbar:`/`footer:` chrome incl.
   presentation devices and `footer.legal.text` (the normative key, schema §10.3),
   the three rule lists, `voice`, `provenanceIndex`.
2. **`section-copy.yaml`** (schema: `spec/section-copy-schema.md`) — the source's REAL
   verbatim copy: `sectionCopy` (incl. `wordmark:`) + `layoutCopy.<layoutId>` for
   every content-bearing layout. Without it every composed section renders
   wordmark+arrow degenerates by design.
3. **`layout-library.yaml`** (`layout-patterns.v1`) — **one pattern per observed
   section shape**, each with `useCase`, `archetypeRef`, `contentShape` (slots with
   `textLen`/`sizeClass`/`sizeRel`/`mediaAspect`/`z`), `specialTreatments`,
   `surfaceIntent`, provenance. Every `brand.yaml` layout carries a `patternRef` to
   one of these (or an explicit `noPatternReason`).
4. **Tagged assets** — `assets-tagged.json` naming only files that exist under
   `assets/`, with role tags; **≥ 3 real logo files whenever a logo wall was
   observed** (a logos use-case with zero logo assets renders a text wall).
4b. **`media-assets.yaml`** (schema: `spec/media-assets-schema.md`, REQUIRED —
   C26/C27/C28 enforced) — the MEDIA SEMANTICS layer over the same files:
   stable logical-asset ids (slugs, never filenames), variant dedupe
   (srcset/retina/format/duplicate siblings collapse into one entry's
   `variants[]`, canonical = highest-res), the closed `assetSemantics.kind`
   taxonomy, per-asset facts (intrinsic geometry, alpha, luminance/busyness
   stats, focal/safe-crop — null = UNKNOWN, never guessed), `usageRights`
   (own | stock | third-party-mark — the AS-67 flag), `treatmentDefaults`,
   provenance; the brand-level `photographyFingerprint`; `generatedVisuals:`
   recipes with posters; and `mediaComposition` on the layout-library patterns
   whose crops show an arrangement (state-swap, marquee, background-with-
   foreground, …). `assets-tagged.json` stays intact — it is the renderer-compat
   inventory; `media-assets.yaml` is the richer superset (note the relationship
   in both).
5. **Chrome presentation evidence** — nav/footer merged into `brand.yaml` via
   `tools/bridge_chrome_to_brand.py` (below), then presentation devices verified
   against css-facts: `tokens.type.<tier>.case`, optional `.prefix`,
   `navbar.separator`/`footer.separator`, `navbar.surface.bg`, measured link-hover
   wash, and the nav-action evidence ladder (`navbar.ctas[]` → `links[].style`
   filled marker → `measured.cta`).

Every decision is wrapped in the rule envelope (`value, confidence, source: creation,
scope, changelog`) with `provenance: [<sectionId>…]` resolving via `provenanceIndex`.

## The vision + DOM cross-check protocol

Neither evidence stream is authoritative alone; each catches the other's blind spots.
For EVERY section, read its `grounding/*.yaml` **and** its `dom-sections.json` entry
plus the relevant `computed-styles.json` samples together:

- **Vision claims a color/size/weight** → confirm against computed styles. Vision
  approximates ("≈ #0a0b1e"); computed styles are exact. Record the computed value,
  keep the vision observation as corroboration. A vision claim with NO computed
  counterpart stays `confidence: low`.
- **DOM shows structure vision missed** — repeated module counts, hidden slides,
  aria labels, real anchor hrefs, image intrinsic sizes. A grounding YAML that read a
  card grid as "one panel" is corrected by the DOM's repeated-wrapper census.
- **Vision shows what DOM cannot** — creative direction (duotone, grain, scrim),
  perceived surface boundaries, image CONTENT ("team photo, warm palette"), whether
  a band reads dark even when its bg is an image. DOM/CSS mining alone misses card
  anatomy and copy hierarchy — this is why C9 requires grounding evidence.
- **Copy is transcribed, not summarized** — `section-copy.yaml` binds the grounding
  YAMLs' verbatim `copy` blocks, cross-checked against DOM text (DOM wins on exact
  characters; vision wins on which text is actually visible/prominent).
- **States need CSS evidence** — hover/focus/pressed facts come from
  `css-facts.json` hoverRules + transitions, never from guessing. A button family
  without a state fact fails C3.

## Grounding conventions (repo law — AGENTS.md)

- **Detailed factual inventory, not evidence summaries.** Preserve approximate
  hex/rgb values, full typography (family/size/weight/case/spacing), image and
  graphic creative direction, component layout, and parent/child surface
  relationships. "Evidence", "local only" and "low confidence" must never become the
  dominant output register — capture the thing itself, flag confidence in the
  envelope.
- **Palette-agnostic language** in every rule/prompt-facing string: describe surface
  relationships ("inverse-strong closing band", "warm-on-dark control family"), never
  "the navy section". Exact values live in tokens; role names describe function.
- **No section-specific token names.** `promoInverse`/`heroAccent` are forbidden
  shapes; a one-off visual relationship is captured as a generic reusable pattern
  (inverse-surface variant, high-contrast inset card, conditional border behavior).
  Surface-scoped VARIANT names (`button-primary-on-inverseStrong`) are fine — they
  name reusable surface roles, not content.
- **Section-aware prose is allowed, section-specific variables are not** — a rule
  may say "the closing conversion band uses the inverse surface"; a token may not be
  named `ctaBandBg`.

## Method — 5 phases

### Phase 0 — Chrome bridge (run FIRST)

Run `./venv/bin/python tools/bridge_chrome_to_brand.py --brand <brand>` (kept as a
STANDALONE generator; this skill invokes it, never re-implements it). It merges the
measured `source-chrome.v2.json` nav/footer into `brand.yaml` atomically and
regenerates the chrome preview at `runs/<brand>/brand/chrome/index.html` — never
hand-edit that HTML. Then VERIFY the presentation devices the bridge cannot see
against `css-facts.json` and the crops: separators, casing per type tier, link-hover
wash, which primary item is the ACTION (evidence ladder, schema §3 note). Fix
`footer.legal` to the normative `text:` key if the contract used a synonym.

### Phase 1 — Section census + surface rhythm

Walk `dom-sections.json` top→bottom against the crops. A section = a full-width band
owning a background surface and a coherent content group; merge/split DOM candidates
by the visual surface boundaries the crops show.

1. Assign each section a stable `sectionId` slug; register url/node/crop in
   `provenanceIndex`.
2. Record `surfaceGrammar.pageRhythm` — the ordered surface roles down the page —
   from computed section backgrounds cross-checked against how the crops READ (an
   image-scrim band that reads dark is a dark band even if its bg property is an
   image). Generation derives its inverse-band budget from this rhythm; an all-light
   brand must record an all-light rhythm, not inherit a dark bookend by template.
3. Record seam behavior (`surfaceGrammar.transition`) and any bridging devices.

Write the skeleton (`layouts[]` ids + provenance + rhythm) to `brand.yaml` NOW —
incremental save discipline applies through every phase.

### Phase 2 — Tokens + component matrices (computed-first)

1. **Tokens** from `computed-styles.json`: colors→semantic roles, every `tokens.type`
   tier with measured `weight` (REQUIRED — default 400 only when genuinely
   undeclared) and `case`, spacing tiers with real section padding / module gaps,
   `tokens.surfaces` with `textPrimary`/`textAccent` per role, imagery
   `aspectPalette` from real image dimensions.
   - **Canonical tier + per-tier ladders (C14).** Declare `meta.canonicalTier`
     (`{viewport, label, note}`) — the measured breakpoint every canonical value
     (`sizeRem.base`, spacing `value:`) refers to. Author every sized type role's
     responsive ladder from the measure stage's tier samples (`computed-styles.json
     tiers` at 1920/1440/960/375 by default): ≥ 2 breakpoints in `sizeRem`, per-tier
     evidence stamps under `tiers: {w<viewport>: {px, source}}`, h1–h6 coverage where
     evidenced (a register that exists only as a class ladder in the source CSS is
     authored with `source: saved-css` and a no-on-page-instance note). A size that
     genuinely holds across the ladder carries `singleTierConfirmed: true` — measured
     constancy, never an unchecked default. Record the heading-emphasis law from the
     tier samples' `headingEmphasis` facts (`<strong>/<b>` weight inside headings, or
     its explicit absence) and container width facts (declared %/max/min beside used
     px per tier) where a container token is authored.
   - **Relational spacing ladder (C15).** The gaps BETWEEN content roles are brand
     rhythm: author the observed rungs as named `<role>-to-<role>` spacing tokens
     (`eyebrow-to-heading`, `heading-to-body`, `body-to-cta`, …) with measured values
     (+ `modeLadder` when the source swaps them by breakpoint — spacing
     custom-property ladders and measured margins are the evidence). A source whose
     rhythm truly exposes no such ladder records
     `tokens.spacing.relationalLadder: {notObserved: true, reason: …}` — never
     silence.
2. **Buttons — the full variant matrix.** Enumerate EVERY observed action style from
   computed samples + css-facts hoverRules into `buttons.<family>` (generic tier
   names: primary/secondary/tertiary/textCta). Each family: `style`, fill/ink,
   `radius`, padding, type facts, and ≥ 1 state fact (bgHover/fgHover/decoration/
   focus). One family only + `singleVariantConfirmed: true` ONLY after re-scanning
   grounding + css-facts for the families sites almost always carry.
3. **Blocks — attempt every contract type.** For each key in `contracts/blocks.yaml`:
   extract the brand's usage (origin/use/slots/provenance) or mark
   `notObserved: true` with a note of where you looked. Card anatomy (media-well,
   radius, hover elevation, link affordance) is extracted as a card COMPONENT entry,
   not left as layout prose.
4. **Motion — `tokens.motion` from `motion-audit.json`.** The audit is the evidence;
   the token block is the derived contract:
   - `durations`: the observed duration LADDER (census-ranked, named by role —
     e.g. micro/state/reveal/expressive — never by section), each value carrying
     the census count or source selector as provenance.
   - `easings`: every distinct easing function observed (keyword or cubic-bezier),
     with its dominant use (enter vs exit vs decorative) when the selectors make
     that legible.
   - `signatureMoves[]`: the NAMED moves that make the brand's motion recognizable —
     each with `name` (generic vocabulary: icon-slide, marquee-scroll,
     accordion-reveal, modal-pop…), the observed timing facts, and `sourceSelectors`
     pointing at the audit rows/keyframes that evidence it. JS-driven timings CSS
     cannot see (autoplay intervals, scroll-triggered reveals) are recorded in the
     audit's `jsTimingNotes` and cited from here.
   - A brand whose audit shows NO authored motion records
     `tokens.motion: {notObserved: true, reason: …}` — validator C13 accepts that,
     but never silence.
   Interactive block entries (accordion/carousel/tabs/modal…) name their observed
   timing (or `notObserved`) so the component contract carries its own motion fact.

### Phase 3 — Per-section layout + pattern authoring

For each section, from its grounding YAML + DOM entry + crop:

1. **Archetype + structure** → `layouts[]` entry: archetype (stack/split/grid/bento/
   row/band/collage/overlay…), `surfaceIntent`, `gridRules` (columns/stagger/overlap/
   gap), `widthRules` (container intent + text measure), `overlapRules`, and
   `blockMapping[]` binding slots to primitive/block CONTRACTS (library-agnostic;
   reuse-before-create against the contracts).
2. **Content-shape signature** → the pattern detail that makes the section reusable:
   per-slot `textLen` (none/word/short/medium/long), `sizeClass`
   (colossal/hero/display/title/body/caption), `sizeRel` where a size is tied to a
   neighbour, `mediaAspect`/`mediaScale`/`opacityClass`/`z` for media, and
   `specialTreatments[]` (ghost-word/overlap/stagger/bleed/marginal-caption/
   text-on-media…) with target/pair/anchor/amount-class. Capture the PATTERN, not
   the pixels.
   - **Alignment coherence** (REQUIRED whenever any slot centers): record
     `alignment.value`, `.inheritance`, and the observed sibling rule — a centered
     conversion stack conventionally centers/measure-locks its form too; a header
     block may center only its heading. State which case applies.
   - **Control measure**: any `sizeClass: control` slot MUST carry `width`/`sizeRel`
     (controls have no natural measure; unrecorded controls stretch full-container).
   - **Scroll motion**: sample computed `transform` at 2+ scroll depths before
     recording `scroll-parallax`; record the brand-level toggle in
     `voice.motionSpec`, never above the brand's locked motion dial.
3. **Pattern authoring — one per observed section shape.** Query
   `layout_library.match()` first: `reuse`/`adapt` → set the layout's `patternRef`
   (+ tuned `variantKnobs`); `miss` → author the NEW pattern into
   `layout-library.yaml` (`origin: extracted`, provenance, confidence) and reference
   it. Distinct observed shapes never share one pattern; near-duplicates raise a
   pattern's confidence instead of forking it.
   - **Component recipes (REQUIRED authoring step, fix2).** After the per-section
     pass, scan the authored patterns for RECURRING COMPONENT ANATOMY: the same
     ordered slot run (e.g. kicker + leader rule + trailing quiet CTA) appearing in
     2+ sections, restyled per context. Record each as a `recipes:` entry in
     `layout-library.yaml` (brand-schema §4.4e): generic anatomy slots, shared
     measured `geometry`, one `variants[]` entry per observed styling (chip vs pill
     vs badge; icon sizes; rule style; trailing-action presence), `usedBy` +
     `provenance`, and bind each participating pattern via
     `recipeRef: {recipe, variant}`. The grounding output's "recurring anatomy"
     notes (extraction-grounding-prompt) are the primary lead; patterns sharing a
     rail-like slot signature without a recipe fail the C23 advisory. Recipes are
     observed brand facts (`origin: extracted`) — never invent a variant the crops
     don't show.
   - **Action-group facts.** Measure the brand's multi-action row law once
     (inter-action gap, orientation, wrap, alignment, seam above, register order —
     JS-off computed at the canonical tier) and author
     `layoutGrammar.actionGroup` (brand-schema §4.4f); bands that measure
     differently get a per-pattern `contentShape.actionGroup` override. Scaffold
     defaults are only the no-facts degrade.
   - **Mark-row item boxes.** For logo/badge strips also record the measured
     per-mark box (`mediaScale.item: {width, height}`) alongside `gap` — flex
     weights derived from asset viewBoxes skew artwork scale when viewBoxes carry
     padding; the measured item box is the truth the renderer locks to.
   - **Text-CTA glyphs.** When the source's arrow/text links carry a REAL vector
     glyph (sprite symbol, inline path), harvest it into `assets/` (verify the
     symbol's own viewBox — sprite harvests often mis-copy it) and author
     `buttons.<family>.glyph: {asset, size, source: computed}` so the device
     renders the brand's real glyph instead of the Unicode fallback.
4. **Verbatim copy** → `section-copy.yaml` `layoutCopy.<layoutId>` from the grounding
   `copy` blocks (slots keyed to the layout's slot names; module arrays for repeated
   cards/logos), plus `sectionCopy.wordmark` and shared strings.
5. **Assets** → tag the section's real files in `assets-tagged.json` (role, section);
   for logo walls confirm ≥ 3 real logo files exist under `assets/` (re-run
   `curate_assets.py` for missing ones rather than inventing filenames).
6. **Media semantics (REQUIRED authoring steps, media semantics 2026-07 —
   spec/media-assets-schema.md; C26/C27/C28 enforced).**
   - **Start from the tool draft.** `curate_assets.py` emits
     `media-assets-draft.yaml` beside the manifest: stable ids, content-hash
     dedupe (identical bytes → `variants[]`), Pillow-measured stats (intrinsic
     geometry, alpha, dominant hue, luminance band, busyness; gracefully absent
     when Pillow can't decode — SVGs stay `stats: null`), and a `kind` hint from
     the filename tag guess. The draft is agent-refined into the authored
     `media-assets.yaml` — the same draft→authored convention as
     assets-manifest → assets-tagged.
   - **Refine per asset** from the groundings' `mediaAssets` blocks + the crops:
     correct the `kind` (closed taxonomy, spec §2.1), write `subject` as generic
     role words, set `usageRights` (every customer/partner/press logo, review
     badge and app badge is `third-party-mark`), carry the harvested alt, author
     `treatmentDefaults` consistent with the assets-tagged fit facts, and set
     provenance (source, sections, confidence). Leave `focalPoint`/`safeCrop`
     null unless measured — null means UNKNOWN, a fabricated center is a guess.
   - **Dedupe variants.** Collapse retina/format/srcset/duplicate siblings into
     one logical asset; canonical = highest resolution. C28 flags byte-identical
     files living under two ids.
   - **Photography fingerprint.** Measure the brand's imagery grammar from the
     actual `photograph`/`portrait` assets (temperature cast, key/exposure,
     saturation band, matte/glossy — Pillow stats via the draft, else documented
     manual reads); a photo-less brand records `notObserved` + reason.
   - **Generated-visual recipes.** Author `generatedVisuals:` for devices the
     evidence shows as CODE, not files (the groundings' `generatedVisualDevices`
     + css-rules gradients): kind, re-instantiable recipe with brand TOKEN ROLES
     for hues, a captured poster (crop it from the run's own capture; poster
     filenames must avoid the default-art resolver keywords), and the
     live → poster → omit degrade. Evidence licenses devices — never author a
     gradient the capture doesn't show.
   - **Composition authoring.** Where a crop/DOM shows an ARRANGEMENT (per-item
     disclosure media swap, logo marquee vs static tiled grid, full-bleed art
     behind a copy stack, an overlap cluster, a facepile), record
     `mediaComposition` on that pattern's media slot (mode + layers with
     `assetRef` ids; the §4.6.5 registration grammar verbatim). Observed
     arrangements only — provenance covers them.

### Phase 4 — Rule synthesis + validation

1. De-duplicate recurring observations (≥ 2 sections, consistent) into
   `compositionRules`/`surfaceGrammar` at `scope: design-language`; single
   occurrences stay `confidence: low` / `scope: one-off`.
2. Synthesize `do[]` / `avoid[]` / `neverDo[]` (prohibitions from consistent
   absences: no shadows, no radius, no text-on-photos…), set `voice.dials`,
   `recipePolicy`.
2b. **Brand signatures (REQUIRED authoring step, pass1 2026-07).** Author the
   `signatures:` block (brand-schema §4.7): the **3-5, not 20** moves that make
   THIS brand recognizable, each as a machine-checkable always/never rule —
   generic `kind` vocabulary (`accent-scope`, `shape-motif`, `type-treatment`,
   `surface-habit`, `spacing-habit`), brand-specific values, `check` params the
   signature auditor can verify, and `evidence` citing the sections/computed
   facts that license the rule. Candidates come from what repeats across the
   whole capture (the accent that only ever paints actions; the corner silhouette
   every control shares; the single display family; the licensed dark-surface
   family). Fewer than 3 means the brand's voice hasn't been found yet; more
   than 5 means rules are being dumped, not signatures. C25 (advisory) is the
   enforcement backstop.
2b². **Accent devices + marker glyphs (REQUIRED extraction targets when the
   evidence shows them, fix7 2026-07).** When the capture shows small accent
   TOUCHES — a landmark heading closing with an accent-colored mark, list
   markers in the brand's glyph, a standing-link underline decoration, an
   accent-emphasized word — author the `accentDevices:` block (brand-schema
   §4.11): device kind + the token role that paints it + licensed contexts
   with floors, AND harvest the marker artwork into `assets/` + the tagged
   inventory (the icon-next.svg pattern: the sprite symbol's own viewBox,
   currentColor, sanitizer-clean). A signature that names the move without
   the license is only half the fact — the fix7 review found the orange
   period + checkmark accents EXTRACTED but never applied, because nothing
   machine-applicable carried them. Do NOT invent: a hover-only underline is
   an interaction treatment (motionSpec.link), not a standing accent device.
2c. **Structured voice facts (REQUIRED, pass1 2026-07).** Derive
   `voice-facts.yaml` (brand-schema §4.8) from the captured copy corpus —
   sentence stats + gate budgets, reading level, casing rules with the
   brand-term allowlist, verb-led CTA share, exclamation facts, banned-hype
   lexicon — and reference it from `voice.factsRef`. Deterministic text stats,
   no model in the loop; voice.md stays the prose companion.
2d. **Derived scale (REQUIRED, pass1 2026-07).** Run
   `./venv/bin/python tools/extract/normalize_scales.py runs/<brand>/brand` to
   derive `style-scale.yaml` (brand-schema §4.9) from the authored facts +
   evidence CSS. Never hand-edit the artifact; a poor fit is recorded honestly
   (`followsScale: false`), not forced. C24 (advisory) checks consistency.
3. Re-render `brand.md` via `render_brand_md(brand.yaml)` — never hand-write it.
   The style md MUST carry a "Component recipes" section (brand-schema §9b):
   projection-rendered files get it from the `recipes:` layer automatically; a
   hand-authored extraction summary gets one prose paragraph/bullet per recipe —
   anatomy, variants, which sections deploy which variant — written as the brand's
   own genre voice (descriptive prose, never a shared genre taxonomy).
4. **Run the validator — the exit criterion:**
   `./venv/bin/python tools/extract/validate_brand_evidence.py --brand <brand>`
   - C1 brand.yaml parses; C2 every contract block evidenced or `notObserved`;
   - C3 button families each usable, single-family only when confirmed;
   - C4 section-copy.yaml present, wordmark set, every content-bearing layout
     covered; C5 layout↔pattern coverage both directions;
   - C6 logo walls have real logo assets; C7 navbar/footer complete incl.
     `legal.text` and presentation evidence; C8 tagged assets exist on disk;
   - C9 vision grounding exists (`--allow-no-vision` only for explicitly
     DOM-only salvage runs);
   - C13 `tokens.motion` present with ≥ 1 evidenced duration + easing (or explicit
     `notObserved` + reason), and interactive blocks carry a timing fact;
   - C14 `meta.canonicalTier` declared and every sized type role carries ≥ 2
     breakpoints (or `singleTierConfirmed: true` after verifying against the
     measured tier ladder);
   - C15 relational spacing ladder present as named `<role>-to-<role>` tokens
     (or `relationalLadder: {notObserved, reason}`);
   - C23 (advisory) recurring rail-like slot signatures across 2+ patterns are
     bound to a `recipes:` entry via `recipeRef` — the recipe layer is written
     during extraction, not post-hoc;
   - C24 (advisory) the derived `style-scale.yaml` is internally consistent and
     its fit ledger honest (steps on the base/ratio, no forced followsScale);
   - C25 (advisory) a `signatures:` block exists with 3-5 well-formed,
     evidence-cited, machine-checkable entries (brand-schema §4.7);
   - C26 media-assets.yaml is well-formed media-assets.v1 (slug ids, on-disk
     files, closed kind taxonomy, rights flags, provenance, poster discipline);
   - C27 media references resolve (mediaComposition layer assetRef/maskRef →
     registry ids, componentRef → shared contracts, pattern-bound files all
     registered);
   - C28 (advisory) variant dedupe is sane (no byte-identical files under two
     ids; canonical = highest-res).
   Fix and re-run until clean — a validator error means a missed observation.
5. **Anti-slop checks** before calling any composed render done:
   `node brand_pipeline/contrast_audit.mjs <index.html>` and
   `node brand_pipeline/slop_audit.mjs <index.html>`; skim `spec/anti-ai-slop.md`
   for new instances of registered failure shapes and REGISTER new ones found.

## Operating rules (inherited)

- Read economically: one section's evidence at a time; grep the big JSONs, never
  load them whole.
- Never invent values — computed styles and real files are the source. Unknown →
  `confidence: low` + a signal-loop question, not a guess.
- Write canonical files incrementally after each phase/section.
- On contradiction with an existing rule during re-authoring: apply as
  `scope: one-off`, do not promote, enqueue the clarifying question
  (`signal-loop.md`).
- Append/reconcile the project layout library across runs — never overwrite; the
  extracted-over-designed ratchet (schema §5.3) only moves one way.
