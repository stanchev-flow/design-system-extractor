# Phase 2 Plan — Wiring the Hero Archetype Library + HubSpot v2 Gallery

Phase 1 delivered data only (`heroes-saas.yaml`, `spec/archetype-library.md`, this
plan). Phase 2 is wiring + a test gallery. Everything below is execution, not design.
Governing law throughout: style-invariant / structure-variable / physics-hard
(see `brand_pipeline/spec/archetype-library.md`).

## 0. New module (keeps genre knowledge out of shared code paths)

**NEW `brand_pipeline/archetype_library.py`** — the only code that knows the archetype
schema. No archetype ids in code, ever.

- `load_genre(genre: str) -> dict` — reads
  `brand_pipeline/contracts/archetypes/{genre}.yaml` (today: `heroes-saas`), validates
  `schemaVersion: hero-archetypes.v1`, returns parsed doc. Cache like
  `layout_library.load_standard_patterns`.
- `shortlist(doc, page_type: str, task_intents: list[str], variance: str,
  brand_resume: dict, k: int = 3) -> list[dict]` — filter by
  `useCases.pageTypes`/`taskIntents`, rank by intent overlap + affinity, then apply the
  variance dial: at `low`, boost archetypes whose `structure.archetype` matches the
  brand's evidenced hero recipe scaffold (from `brand_resume`); at `high`/wildcard,
  boost non-evidenced neighbors. Deterministic given a seed.
- `render_candidate_block(candidates: list[dict]) -> str` — compact prompt text per
  candidate: id, intent, anatomy summary (slot order + required flags), geometry
  character, variantKnobs, slopTraps (AS numbers), physicsBindings. Mirrors the style
  of `layout_library.render_pattern_constraint` so the prompt reads uniformly.
- `physics_checklist(archetype: dict) -> list[str]` — returns the `physicsBindings`
  list for audit wiring (§3 below).
- Unit tests: NEW `brand_pipeline/tests/test_archetype_library.py` — schema validation
  of the YAML (ids unique, core five bindings present, contracts/scaffoldRefs resolve
  against `blocks.yaml`/`scaffolds.yaml`, exemplar evidence paths exist), shortlist
  determinism, page-type coverage.

## 1. Selection in `generate_composition.py`

Three edits, all genre-agnostic:

1. **Candidate injection** — in `build_prompt(...)` (currently line ~403), after the
   pattern-seed block from `seed_patterns(...)`: when the brief's section plan contains
   a hero (`_is_hero_section` grammar already exists) and a genre library exists for
   the run's declared genre, call `archetype_library.shortlist(...)` with the brief's
   page type + task intents, and append `render_candidate_block(...)` under a
   `HERO STRUCTURE CANDIDATES` heading. Contract text states: pick exactly one,
   record it as `archetypeRef`; brand recipes win slot anatomy; physics is not
   relaxable.
2. **Composition output field** — accept optional `archetypeRef` (string) and
   `archetypeKnobs` (object, must match the chosen archetype's `variantKnobs`) on hero
   sections in the `composition.v1` validation path. Unknown ids fail closed to the
   evidenced hero recipe (log, don't crash).
3. **Prefilter hooks** — extend `neverdo_prefilter`/`offgrid_prefilter` awareness: if
   the chosen archetype requires off-grid license (e.g. banded seam-straddle, ghostword
   collage z-depth) and the style says `offGridExpansion=false`, the prefilter demotes
   to the archetype's nearest in-grid neighbor (data-driven via a `requiresOffGrid:
   true` flag we add to those entries) rather than hand-branching on ids.

Page-type/task-intent source: the brief file already carries free text; phase 2 adds an
optional `pageType:`/`taskIntents:` frontmatter block to gallery briefs (plain YAML at
the top of the brief md). No shared-schema change needed for other lanes.

## 2. Instantiation in `compose_from_composition.py`

- In `adapt_brand_section(...)` (line ~1656): when a section carries `archetypeRef`,
  fetch the archetype, and BEFORE brand adaptation apply the skeleton: set/normalize
  `archetype`, `scaffoldRef`-derived layout knobs (`_bento`/`_tiers`-style stamps where
  the archetype routes through the cards family), slot order, alignment context, and
  geometry ranges (band height character → the existing section spacing knobs;
  mediaFraction → split fraction knob). THEN run the existing brand adaptation so
  recipes/tokens/ladder overwrite anatomy where the brand has its own pattern —
  precedence "recipes win" falls out of the ordering, no special cases.
- `composition_to_layout(...)` passes `archetypeRef` through so reports can show it.
- Fallback: if any physics binding fails to resolve during adaptation (missing
  actionGroup facts, no text-on-media contrast device for scrim/overlay archetypes),
  drop `archetypeRef` and re-adapt with the brand's evidenced hero recipe; record the
  demotion in the section's adaptation notes.

## 3. Creative-mode fact binding + gates

- `onbrand_check.py`: add a genre-agnostic "archetype physics" section — for a section
  with `archetypeRef`, read `physics_checklist(...)` and assert the mapped existing
  checks ran and passed for that section (containment → existing containment check,
  actionGroup → AS-59/registers, textOnMedia → scrim/contrast, gridEqualize → AS-44,
  stackMeasure → measure caps, headerContext → alignment grammar). No new physics is
  invented; the bindings list only selects which existing checks are MANDATORY for
  that section.
- `spacing_audit.py` + `interaction_audit.py` + `slop_audit.mjs` + `readability.py`
  run unchanged — the gallery lane invokes them per hero page (they're already
  lane-relative via `--brand`/`--out`).

## 4. HubSpot v2 hero gallery lane

Layout under `runs/hubspot-v2/brand/compose/hero-archetypes/` (mirrors the `replica`
lane structure, one subdir per hero + a gallery index):

```
runs/hubspot-v2/brand/compose/hero-archetypes/
  briefs/                       # 8 brief md files with pageType/taskIntents frontmatter
  homepage/                     # each: composition.json, index.html, assets/,
  pricing/                      #   onbrand-report.{json,md}, spacing-audit/,
  product/                      #   interaction-audit/, hero-fullpage.png
  about/
  blog/
  demo/
  developer/
  event/
  index.html                    # gallery contact sheet: 8 screenshots + archetypeRef labels
  changes.md                    # lane changelog (repo rule)
```

Per-category archetype expectation (selection is the model's, but briefs are written so
the shortlist contains these; the gallery asserts VARIETY, not exact ids — gate:
at least 6 distinct `archetypeRef`s across the 8 heroes, no archetype used 3+ times):

| brief | pageType | taskIntents seed | expected shortlist flavor |
|---|---|---|---|
| homepage | homepage | product-overview, conversion | split-product / bento-lead / banded-seam-straddle |
| pricing | pricing | price-transparency | pricing-value-forward / pricing-plan-peek |
| product | product | feature-deep-dive, demo | product-canvas-panel / demo-media-proof / terminal-split |
| about | about | mission, trust | editorial-statement / mission-monument / layered-fullbleed-scrim |
| blog | blog | content-hub | content-featured-lead / index-masthead |
| demo | demo | lead-gen-with-form | form-split / form-centered |
| developer | developer | developer-product | terminal-split / search-first / onboarding-steps |
| event | event | launch-announcement | event-meta-forward / announcement-crest / centered-statement-canvas |

Run mechanics per hero:

1. `generate_composition.generate(...)` with the brief, `style_id` =
   hubspot-v2's style, **`force_off_grid=True` for this lane** (the
   corporate-saas-clean style pins `offGridExpansion=false`; the gallery is explicitly
   a structure-variance exercise, and `force_off_grid` already exists at line ~1012 —
   no style edit).
2. Hero-only render: `compose_from_composition.render_composition(...)` on a
   composition trimmed to header + hero (+ footer for header-context realism), out to
   the category dir.
3. Gates per hero: `onbrand_check` (with archetype-physics section), `spacing_audit`,
   `interaction_audit --static-only`, `slop_audit.mjs`, `readability`.
4. Screenshot: the compose lane's existing fullpage screenshot path (same as
   `replica-fullpage.png`) renamed `hero-fullpage.png`; plus a 1440×viewport crop of
   the hero band for the contact sheet.
5. Gallery `index.html`: static contact sheet (thumb, archetypeRef, page type, gate
   pass/fail chips). Regenerate `viewer.html` after the lane lands (repo rule).

## 5. Documentation + hygiene (phase 2, after code lands)

- `spec/brand-schema.md`: one paragraph in the composition section pointing to
  `archetype-library.md` (edit deferred to phase 2 per the fence).
- `changes.md` at repo root + `runs/hubspot-v2/brand/compose/hero-archetypes/changes.md`.
- `spec_book` test (`tests/test_spec_book.py`) may enumerate spec files — add
  `archetype-library.md` if the manifest is explicit.

## 6. Vocabulary extensions phase 2 needs (wanted but not yet facts)

1. **`bandHeight` knob on composition hero sections** (`compact|standard|tall|viewport`)
   — archetypes declare it; today section height is emergent. Map to existing spacing
   knobs in `adapt_brand_section`.
2. **`code-panel` block contract** in `contracts/blocks.yaml` — terminal-split and
   search-first approximate it with `image`/`label` today; a real contract (mono
   register, line-length cap, no fake chrome) makes AS-checks targetable.
3. **`typeAsGraphic` license fact** — ghostword-atmospheric and marquee-canvas use
   display type as a graphic object (outline/oversize/drift). Needs a declared license
   + legibility bound (extends `textOnMedia` family) instead of inferring from
   headingTier.
4. **`motion.reducedMotion` contract entry** in `interaction-contracts.md` — marquee
   drift and showreel autoplay need a declared reduced-motion posture; today only
   hover/focus/scroll devices are contracted.
5. **`seamOffset` fact for banded scaffolds** — plan-peek and seam-straddle want a
   measured "how far media crests the seam" range; today the banded grammar has the
   seam but not the crest depth.
6. **`requiresOffGrid` flag on archetype entries** (data-side addition, no schema bump)
   — so prefilter demotion (§1.3) stays data-driven.
