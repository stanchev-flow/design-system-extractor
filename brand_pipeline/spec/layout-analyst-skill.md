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

> This is a **spec** for a skill any agent can invoke, NOT a hardcoded pipeline step.
> It is the AUTHORING arm of the Brand Extractor: it turns the machine-mined evidence
> bundle into the canonical brand files. It never touches a live site and never
> hand-edits rendered projections (`brand.md`, chrome preview HTML — both are
> regenerated from canonical data).
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
4. **Verbatim copy** → `section-copy.yaml` `layoutCopy.<layoutId>` from the grounding
   `copy` blocks (slots keyed to the layout's slot names; module arrays for repeated
   cards/logos), plus `sectionCopy.wordmark` and shared strings.
5. **Assets** → tag the section's real files in `assets-tagged.json` (role, section);
   for logo walls confirm ≥ 3 real logo files exist under `assets/` (re-run
   `curate_assets.py` for missing ones rather than inventing filenames).

### Phase 4 — Rule synthesis + validation

1. De-duplicate recurring observations (≥ 2 sections, consistent) into
   `compositionRules`/`surfaceGrammar` at `scope: design-language`; single
   occurrences stay `confidence: low` / `scope: one-off`.
2. Synthesize `do[]` / `avoid[]` / `neverDo[]` (prohibitions from consistent
   absences: no shadows, no radius, no text-on-photos…), set `voice.dials`,
   `recipePolicy`.
3. Re-render `brand.md` via `render_brand_md(brand.yaml)` — never hand-write it.
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
     (or `relationalLadder: {notObserved, reason}`).
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
