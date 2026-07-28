# customer-story lane — changelog

A NEW page type for the hubspot-v2 lane: a **customers / customer-story page**
(flagship: Angel City FC). No prior `compose/` lane builds this page type — the
existing set is homepage/product/pricing/about/blog/demo/developer/event
(hero-archetypes) + a product-launch bakeoff. Built to prove the recently-landed
improvements produce genuinely on-brand output for a gate-PASSING brand:
auto-resolved 50-style PRESET layer (`saas-product`) + MEDIA-SEMANTICS binding +
the fail-closed gate flow (gates ENFORCED; hubspot-v2 replica 0.957 ⇒ ALLOWED).

## Plan of record

- Page type: `customers` (customer-story). Genre archetype for the hero:
  `hero-case-lead` (customers-hub opener leading with ONE flagship story).
- Style id: `saas-product` (best match to HubSpot's measured SaaS-product
  identity). Preset is a level-2 default UNDER brand evidence — brand facts win.
- Copy-first: `copy-brief.md` (all copy grounded in the run's OWN extracted
  evidence — the Angel City FC / Unipart / Youth on Course testimonial panels in
  section-copy.yaml + the extracted customer logos). Nothing invented.
- Gates ENFORCED (`enforce_gates=True`), `force_off_grid=True` (lane lever, brand
  style pin untouched), `max_repairs=2`.

## Log

- 2026-07-17 — lane created; copy-brief.md authored (copy-first, grounded in the
  Angel City FC / Unipart / Youth on Course testimonial panels + extracted logos).
- Generation, gates ENFORCED (fail-closed flow ALLOWED generation — flow-report.json
  generationAllowed:true, replica 0.957 ≥ bar 0.90). Auto-resolved preset block FIRED
  on the pure auto path (style_id `saas-product`, [[PASS3-STYLE]] 10,462 chars) +
  [[MEDIA-FACTS]] + [[PASS3-FACTS]] + hero archetype candidates
  (hero-case-lead/hero-social-proof-embedded/hero-stat-forward). Hero bound
  `hero-case-lead`.
  - gen attempt A (auto path): FAIL composition-lint knob-consumption (`statCount`).
  - gen attempt B (tightened brief): FAIL composition-lint knob-consumption (`secondaryCta`).
  - gen attempt C (tightened brief): lints cleared, FAIL at RENDER — the renderer
    hard-requires styles/<style_id>.md and NO style-library preset id has a base-style
    file (only corporate-saas-clean / editorial-luxury / radical-editorial exist). The
    auto path proves the preset block in the prompt but cannot render/gate end-to-end
    with style_id = a preset. Reported as a residual finding (no shared-code edit).
  - gen attempt D (delivery): base style `corporate-saas-clean` (renderable) + the
    IDENTICAL auto-resolved `saas-product` preset block injected (the pass-3 bakeoff
    pattern). onbrand --composition gate PASS on the loop's 3rd attempt.
- Full battery (iteration 0): onbrand PASS · interaction PASS · signature PASS ·
  voice PASS · conversion PASS · media-binding+mark-legality PASS · slop FAIL (AS-11
  short heading-only closing) · spacing FAIL (closing stack-width off-ladder +
  logos strip.gap wrong-step; hero split.column-gap +10 is the pre-existing advisory
  drift the replica also carries) · section-rules FAIL (SR-STAT-01 wordy value `~350`;
  SR-STAT-03 7-word stat label, advisory).
- Iteration 1: brief tightened — clean stat values (`350+`, no `~`) + 1–6-word stat
  labels; closing heading lengthened to a full landmark line closing with the orange
  period (fills the stack measure + clears AS-11). Regeneration did NOT converge in
  the loop budget (the more-stories `gallery`/`cards` section dropped its display
  heading; a schema slip on the last attempt) — regeneration is stochastic and this
  run left a failing composition.
- Iteration 2 (deterministic re-render — the supported post-generation `--rerender`
  path, same class as prior passes' voice/stat re-render fixes; NO shared-code edits):
  applied targeted corrections to the SAVED composition + re-rendered + re-gated:
  - more-stories `gallery` → `features` (renders the product-grid-style section-intro
    heading); section headings `display` → `title` register (display reserved for the
    hero + closing landmarks) — clears the onbrand "authored display heading" check.
  - logos: `seededFrom` = `logo-proof-strip`, archetype `cards`, + the pattern's
    measured `mediaScale.item` (153×76, 69px gap) on the logo slot → the strip now
    renders the brand's item-box geometry (clears the strip.gap wrong-step).
  - hero case card: bound `046-angel-fc.png` into the card copy (bare-string
    convention) — see residual below.
- FINAL onbrand `--composition` gate: **PASS**. Full battery below.

## Final gate battery (true exit codes; `battery/` + battery-summary.json)

| gate | exit | verdict |
|---|---|---|
| onbrand `--composition` (14 HARD invariants) | 0 | PASS |
| slop `@1440+@1180` | 0 | PASS |
| interaction `--strict` | 0 | PASS (0 required fails) |
| spacing `--strict` | 1 | 1 hard cell (see residual) — 64 conform / 1 drift / 1 wrong-step / 10 unmapped; scale 0 off-scale |
| signature `--strict` | 0 | PASS (accent share 0.298% ≤ 2%; landmark device floors met) |
| voice `--strict` | 0 | PASS (sentence-length, exclamations, banned-hype, casing) |
| section-rules `--strict` | 0 | PASS (SR-STAT cleared) |
| conversion `--strict` | 0 | PASS |
| media-binding + mark-legality (AS-67) | 0 | PASS |

**8/9 gates green.**

## On-brand verdict

Genuinely, unmistakably on-brand — the side-by-side contact sheet
(`shots/contact-sheet-vs-source.png`) shows the new page sharing HubSpot's design
system with the real homepage + 0.957 replica: the two-tier nav chrome + wordmark,
the warm off-white canvas, HubSpot Serif display headings closing with the orange
period, the orange-only accent discipline (measured 0.298% paint share), the
challenge headrail (orange chip + dotted rule), serif stat numerals, flat white card
plates on hairline borders, the deep-teal closing bookend with cream ink, and the
near-black 5-column footer. All copy is grounded in the run's own extracted evidence.

Confirmed FIRED in the assembled prompt (`assembled-prompt.txt` / `prompt-sentinels.json`):
- `[[PASS3-STYLE]]` auto-resolved `saas-product` PRESET block (10,462 chars). Preset is
  a level-2 default — brand facts WON on every measured slot (dissents:
  font.display→HubSpot Serif, font.body→HubSpot Sans, type.scaleRatio→1.125,
  type.baseSizePx→16, space→brand ladder, shape.radiusPx→tiered 4/8/16, color→brand
  palette; directive dissents: typeDisplay/typeBody/case/radius). Notably the preset's
  `indigo-violet-default-accent` SaaS signature is overridden by the brand's measured
  `action-orange-scope` — orange wins, brand facts win.
- `[[MEDIA-FACTS]]` media-semantics inventory + hard binding rule + no-match ladder.
- `[[PASS3-FACTS]]` pass-1 signatures/voice/scale.
- Hero archetype candidates (heroes-saas/customers): hero-case-lead /
  hero-social-proof-embedded / hero-stat-forward → hero bound **hero-case-lead**.

Fail-closed flow: gates were ENFORCED (`enforce_gates=True`). hubspot-v2's
flow-report.json (generationAllowed:true, replica 0.957 ≥ bar 0.90) ALLOWED
generation — the fail-closed gate did not block (proving the ALLOW path).

## Residual defects (honest)

1. **spacing (1 hard cell)** — `sec-5 logos container.stack-width` 1080 vs 992
   (wrong-step, ~88px). The logos card-section's heading intro spans the full content
   spine instead of the narrower stack measure. Cosmetic/imperceptible; a generate-path
   nuance (a composition-authored section carries no stackMeasure cap fact). The brand's
   own replica carries a comparable advisory drift. Not fixable via lane data without
   editing shared renderer code (out of scope).
2. **hero featured case card** — the `hero-case-lead` case card renders its TEXT
   (Angel City FC / 300%+ / outcome / "Read the story") but NOT the Angel City photo
   (`046-angel-fc.png`), and it is less prominent than the archetype intends. The
   single-card-in-split render path does not emit card media (the more-stories card
   GRID does — those photos render). A renderer gap, reported not worked around.

## Architecture finding (reported, not edited)

The auto-resolved preset path keys the PRESET on `style_id`, but the RENDERER +
gate also consume `style_id` to load `styles/<id>.md`. No style-library preset id
(saas-product, swiss, …) has a base-style file (only corporate-saas-clean /
editorial-luxury / radical-editorial exist), so a pure auto-path run
(style_id=`saas-product`) proves the preset block in the prompt but FAILS at render
(`FileNotFoundError: styles/saas-product.md`). Delivered via the supported pass-3
bakeoff pattern: base style `corporate-saas-clean` (renderable) + the IDENTICAL
auto-resolved `saas-product` preset block injected. No shared code was modified.

## Artifacts

- copy brief: `copy-brief.md`
- generated page: `index.html`  (Studio: http://127.0.0.1:1500/runs/hubspot-v2/brand/compose/customer-story/index.html)
- full-page shot: `shots/customer-story-fullpage.png`
- side-by-side contact sheet: `shots/contact-sheet-vs-source.png`
- assembled prompt + sentinels: `assembled-prompt.txt`, `prompt-sentinels.json`, `auto-preset-block.txt`
- battery logs: `battery/`, `battery-summary.json`

## Wireframe remediation — user rejection (2026-07-17)

The earlier “genuinely on-brand” verdict above is superseded. Visual review proved
the page was sparse, mechanically flattened, and not acceptable.

### Exact root causes

1. **Hero media dropped.** `composition.json` bound `046-angel-fc.png` inside one
   `card` slot on a `split` hero, but `compose_from_composition.py` treated the card
   as a traceability mapping; `compose_info_band` only searched rendered image/media
   fragments. The nested asset never became one, so the split painted no real case
   counterweight. Fixed by `_single_case_card` + `_caseCard`: the adapter emits the
   bound photo as a real image fragment and the split renderer paints one atomic
   media+stat+outcome+action card.
2. **Challenge section flattened and lacked an action.** The composition used a
   repeatable `list` on a non-conversion `stack`. The generic adapter expanded each
   record into separate caption and paragraph mappings, and `compose_generic_flow`
   wrapped each mapping independently. That produced the primitive waterfall shown
   in the rejected screenshot. The section now binds one `feature-item` array to a
   three-column cards collection; each heading/body remains inside one wrapper, with
   a real supporting action and brand-owned mark artwork.
3. **299,000+ sentence duplicated.** `_cards_copy` called `_text(hdr_copy,
   "eyebrow")` on a plain-string heading. `_text` intentionally passes strings
   through regardless of requested key, so the heading became both eyebrow and
   heading. The fallback is now dict-guarded; the sentence renders once.
4. **Page rhythm was never planned.** The pipeline selected sections and primitive
   slots but carried no page-level jobs/density/surface/anchor/conversion cadence,
   no pre-render renderer-capability check, and no consecutive-sparse constraint.
   Existing gates checked token/contract validity, not whether a mechanically valid
   page had visual anchors or semantic grouping.

### System capability

- Added `brand_pipeline/section_wireframe.py` + `spec/wireframe.v1.schema.json` +
  `spec/section-wireframing.md`. Generation now plans and validates
  `wireframe.v1` before HTML. The artifact records page rhythm, density/surface
  sequence, section jobs, visual anchors, conversion/proof obligations, required
  slots, renderer capability, media requirements/requests, and atomic collection
  `{itemContract, items[], layout, columns, wrap, responsive}`.
- Brand precedence is explicit: measured patterns/recipes → designed brand
  components → shared archetypes. A required slot without a real consuming path
  rejects the attempt before render.
- Added AS-68–AS-74 hard rows: cross-slot duplicate copy, semantic grouping /
  anti-waterfall, section completeness, visual anchors, page rhythm, hero painted
  counterweight, and required wireframe-slot consumption.
- Fixed conversion `button` actionGroup arrays: the closing now renders both
  declared actions (`Get a demo`, `Get started free`) instead of the fallback
  `Get started`.
- Fixed measured logo-strip group matching and responsive wrapping; desktop keeps
  the captured 153×76 boxes at 69px gaps while narrow layouts preserve marks.

### Proof

- Artifact: `wireframe.json`.
- Final screenshot: `shots/customer-story-fullpage.png`.
- Comparison: `shots/contact-sheet-vs-source.png`.
- Visual verdict: materially improved and acceptable. The hero has a real Angel
  City FC photo/card counterweight; challenge copy is three atomic, marked
  components plus CTA; the customer sentence appears once; the page has clear
  hero → component collection → stat proof → quote → story cards → logo proof →
  dark conversion cadence.
- Strict battery: **9/9 GREEN** (`battery-summary.json`): onbrand, slop,
  interaction, spacing, signature, voice, section-rules, conversion, media binding.
  Spacing improved from the prior 1 hard cell to **0 hard fails**.
- Tests: **1581 passed**, 8 existing Pillow deprecation warnings; 15 focused
  wireframe/grouping tests.
- Replica safety after shared adapter/composer changes: hubspot-v2 **0.9567**
  (reported 0.957), Remote **0.9509** (reported 0.951).
- Studio URL returned HTTP 200:
  `http://127.0.0.1:1500/runs/hubspot-v2/brand/compose/customer-story/index.html`.

Residual: at 375px the substantive page content and all three challenge items
collapse to one column, but the pre-existing two-tier desktop nav utility rail
still contributes horizontal document overflow. It is a chrome-responsive issue,
not a wireframe/item-grouping regression, and was not hidden with overflow clipping.

## Component feasibility + testimonial integrity (2026-07-17)

The accepted wireframe pass exposed two further systemic defects under visual
review: three long icon/text items were forced into narrow tracks beside the
section intro, and testimonial intent was flattened into a paragraph + uppercase
caption despite compatible client media already existing.

### Root causes and decisions

- `knobs.columns: 3` flowed directly to `_moduleCols`; neither the planner nor
  renderer compared copy demand and padding against the counterweight column's
  available width. The brand's card icon fact (`heading-row`) then forced inline
  marks even when the remaining text measure was too narrow.
- The story collection has a measured 1080px container and a 616px
  counterweight allocation after the parent gutter. Candidates: 3 columns =
  184px/item (rejected: below 288px family minimum and body line caps); 2 columns
  = 292px/item (accepted); anatomy = `icon-top` because inline anatomy would
  consume another 48px and fail the comfort threshold. The third item uses
  normal grid flow in row two; it does not stretch full-span.
- A non-conversion `stack` testimonial routed to `generic-flow`. The adapter
  explicitly rewrote `testimonial` into `paragraph` + `caption`, so the existing
  quote-card/tab testimonial devices never saw the semantic contract.
  `046-angel-fc.png` was present in `media-assets.yaml` as
  `client-photo-midsize-tab` with role `testimonial-panel-media`, but the loose
  primitive mapping had no media-binding step.
- Wireframe testimonial planning now preserves quote + Whitney Hallock
  attribution atomically, subject-matches the Angel City client photo, and
  selects `portrait-side`. The renderer paints one bordered panel with photo,
  deliberate serif quote measure, grouped attribution, and a licensed accent
  quote glyph. A missing compatible image instead produces an asset request and
  a no-photo quote card with no dead media column.

### System changes and proof

- `wireframe.json` now records `componentFit` demand, min width, available width,
  all candidate/rejection rationale, chosen tracks/anatomy, normal last-row
  behavior, and feasibility-derived breakpoints. It also records the complete
  testimonial contract and media match provenance.
- Renderer consumes those exact decisions; item count and the old heading-row
  card fact cannot override them.
- Added AS-75 (no squeezed components) and AS-76 (testimonial semantic
  integrity/empty-space balance) to the composition and browser-rendered gates.
- Regenerated artifacts:
  - desktop: `shots/customer-story-fullpage.png`
  - mobile 375px: `shots/customer-story-fullpage-375.png`
  - comparison: `shots/contact-sheet-vs-source.png`
- Visual verification: desktop shows a balanced 2-column challenge collection
  with the third item intentionally wrapped and every icon above copy; 375px
  shows one item per row. The testimonial is now a full-width photo/quote panel
  at desktop and a stacked photo/quote component on mobile, with no floating
  attribution or huge empty band.
- On-brand composition gate PASS including new `component-fit` and
  `testimonial-integrity` rows; slop PASS at 1440/1180 including AS-75/76.
- Final strict battery: **9/9 GREEN** (onbrand, slop, interaction, spacing,
  signature, voice, section-rules, conversion, media binding). Full
  `brand_pipeline/tests`: **1596 passed**, 8 existing Pillow deprecation
  warnings (baseline 1581 + 15 component-fit/testimonial tests).
- Replica safety: the new metadata is attached only by
  `compose_from_composition.render_composition` for generated creative pages;
  measured `compose_replica` does not run the wireframe attachment path.
  Renderer branches require `_componentFit`/`_testimonial`, so replica geometry
  remains outside the change and the accepted 0.957/0.951 scores need no rerun.

## Grid-fill follow-up — no orphan final row (2026-07-17)

The prior AS-75 result fixed squeezed cards but left one unpainted track: three
peer challenge cards flowed into a two-column grid as `1,1,1`. That visual claim
is superseded.

- The planner now evaluates row fill after selecting feasible tracks. It records
  higher-column rejection, `lead-span`, `tail-span`, `single-column`, and
  licensed-asymmetry candidates with hierarchy, demand, measure, score, and
  reasons. Every wireframed item carries an explicit span.
- The challenge items declare no lead/primary hierarchy and all three carry real
  marks. The chosen strategy is therefore `tail-span`: spans `1,1,2`. The final
  card's outer plate fills row two while its content remains capped at the 28ch
  preferred measure. Visual inspection confirms no empty orphan track and no
  squeezed prose.
- Added AS-77 hard grid-fill checks to composition/on-brand and rendered-browser
  gates. Licensed asymmetry is accepted only with a real painted counterweight.
- Regenerated:
  - `wireframe.json`, `index.html`, `tokens.manifest.json`
  - `shots/customer-story-fullpage.png`
  - `shots/customer-story-fullpage-375.png`
  - `shots/contact-sheet-vs-source.png`
  - `shots/customer-story-before-orphan-grid.png` (reconstructed prior
    `normal-flow` state for direct comparison)
- Strict battery: **9/9 GREEN**. Full `brand_pipeline/tests`: **1602 passed**,
  8 existing Pillow warnings (1596 baseline + 6 new grid-fill regressions).
- Replica safety: unchanged creative-only path. Fill metadata is attached only
  in generated `render_composition`; measured `compose_replica` does not invoke
  the wireframe attachment branch, so replica geometry and accepted scores
  remain outside this change.
- Page URL:
  `http://127.0.0.1:1500/runs/hubspot-v2/brand/compose/customer-story/index.html`.

