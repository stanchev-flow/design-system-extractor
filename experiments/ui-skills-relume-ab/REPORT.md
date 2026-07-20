# UI skills + Relume controlled experiment

## 2026-07-19 structure-only rerun (supersedes the original result below)

**Verdict: REVISE; fallback remains disabled by default.** This rerun is a valid
render-to-render comparison with one isolated variable: lane B receives the production
structure-only fallback for the intentionally unsupported pricing job; lane A does not.
No UI-skill laws were supplied to either lane. Both lanes rendered, but neither passed
the full strict battery, so the fallback is not promoted.

### Fixed controls and execution

- Gate-passing brand: `hubspot-v2`; fixed brief, assets, `corporate-saas-clean` style,
  `saas-product` directive, `claude-opus-4-8` model, high reasoning, 16k output budget,
  and equal eight-attempt cap.
- Lane A rendered on attempt 1. Lane B rendered on attempt 7 after bounded schema/
  wireframe repair oscillation.
- Lane B received exactly three prompt-safe candidates:
  `pricing-content-stack`, `pricing-repeated-grid`, and `pricing-table`; it selected
  `pricing-repeated-grid`.
- All other jobs were excluded before retrieval by measured-pattern or compatible
  brand/style-archetype support.

### Gate results

Both lanes passed 7/9 battery checks: on-brand hard invariants, strict interaction,
signature, voice, section rules, conversion, and media binding. Both failed:

- anti-slop/browser component fit: the three story cards paint at 195px versus the
  declared 288px minimum and their bodies occupy six lines versus the five-line cap;
- strict spacing: pricing `card.body-to-actions` is 14.39px versus the brand's 40px
  `body-to-cta` relation.

The identical hard failures in both lanes are not evidence that Relume caused them.
They do mean neither lane is green, which blocks promotion.

### First-class provenance

- Lane A: measured pattern 2 sections; brand/style archetype 4; Relume 0.
- Lane B: measured pattern 3 sections; brand/style archetype 2; Relume fallback 1.
- Lane B's sole Relume stamp is pricing with
  `structureRecipeId: pricing-repeated-grid`. Hero, story, results, testimonial, and
  closing all retain higher-tier provenance.
- Stamps are emitted in `composition.v1` and propagated to `wireframe.v1`; they are no
  longer post-render inference.

### Visual comparison

- Both lanes remain recognizably HubSpot: measured serif display, warm canvas, orange
  actions, dark-teal closing, and extracted chrome/assets are intact.
- Lane A renders pricing as three large vertically stacked media cards, producing a much
  longer desktop page. Lane B's repeated-grid fallback gives the plan-choice job a
  clearer, more compact three-column comparison and materially improves desktop rhythm.
- Mobile ordering is coherent in both lanes. Lane B remains long but preserves atomic
  plan records.
- Lane B is not visibly less on-brand than A, but both reuse generic/default photography
  across plan cards and both fail the same action-gap relation. The fallback improves
  structural fit without establishing a gate-green quality improvement.

### Artifacts

- `shots/lane-a-desktop.png`, `shots/lane-a-mobile.png`
- `shots/lane-b-desktop.png`, `shots/lane-b-mobile.png`
- `shots/contact-sheet-desktop.png`, `shots/contact-sheet-mobile.png`
- Per-lane composition, wireframe, telemetry, provenance, and battery reports are under
  `lane-a/` and `lane-b/`; paired outcomes are in `results.json`.

### Recommendation

Keep `enable_relume_fallback=False` by default. Revise the generated-card relational
spacing/component-fit path, then repeat the isolated pair. The sanitizer and fallback
precedence machinery are safe to retain behind the flag; the behavior is not promoted.

## Verdict

**REVISE; do not promote.** The experiment proves a tightly scoped Relume fallback can
reach an on-brand render without visual-token leakage, but it does not prove improvement:
the control lane never reached render, the treatment lane failed one strict spacing gate,
the model is unseeded/non-deterministic, and Relume plus UI-law guidance were bundled in
one treatment. No external skill and no current Relume auto-injection should be promoted
from this sample.

## Controls and execution

- Brand: gate-passing `hubspot-v2` (replica 0.956).
- Fixed base style: `corporate-saas-clean`; identical resolved `saas-product` directive.
- Fixed model: `claude-opus-4-8`, reasoning `high`, temperature/provider default.
- Fixed brief, asset inventory, token budget and bounded repair budget across lanes.
- A: explicit empty `section_recipe_guidance`; no external skill laws.
- B: pricing-only Relume structure fallback, top-3, plus seven deduplicated laws.
- Production source/specs were not edited.

The API path exposes no seed, so exact model determinism is unavailable. The final A run
exhausted five attempts on schema/archetype-selection repair oscillation. B passed the
generator's schema, lint, wireframe and on-brand gate on attempt 3. This asymmetric
sampling failure prevents a causal visual A/B.

Two feasibility runs are preserved:

- `attempt-1-summary.json`: both lanes failed schema/knob repair with a three-attempt cap.
- `attempt-2-summary.json`: both lanes exposed that FAQ accordion records have no
  consuming wireframe/renderer path. The final probe therefore used an also-unmeasured,
  renderer-supported pricing-card job in both lanes.

## Gate results

Lane A: **no render / no gate metrics**. The last accepted-stage failure was missing the
required hero `archetypeRef`; rejected drafts are not treated as output.

Lane B: **8 of 9 battery commands passed**:

- PASS: on-brand hard invariants, anti-slop, strict interaction, strict signature, strict
  voice, strict section rules, strict conversion and media binding.
- FAIL: strict spacing. It measured 62 conforming relationships, 0 drift, 1 wrong-step,
  0 off-ladder and 6 advisory unmapped relationships. The hard failure is in the Relume-
  fallback pricing section: card body-to-action gap rendered 14.39px versus the brand's
  40px `body-to-cta` relation.
- On-brand details: all 27 hard invariants passed; accent paint was 0.246% under the 2%
  budget; all four buttons used the measured 8px non-pill radius; display/body/button
  families passed; two dark sections stayed in the licensed family.
- Interaction: 16 pass, 0 fail, 1 advisory, 16 not-applicable skips. Keyboard nav, Escape
  close and reduced-motion checks passed.

## Provenance

Lane B used:

- measured brand patterns: testimonial, closing;
- brand/style archetype: hero;
- shared drawable archetypes: story, results;
- Relume structure-only fallback: pricing, exposed candidates
  `pricing-content-stack`, `pricing-repeated-grid`, `pricing-table`;
- designed component: none directly stampable.

See `PROVENANCE.md` and `lane-b/structure-provenance.json`. Stamps are post-render
inference because current schemas have no first-class provenance field.

## Human visual read

This is a qualitative read, not a gate:

- Brand recognizability is strong: HubSpot serif display, warm canvas, orange action
  scope, dark-teal closing and measured chrome are immediately legible.
- Section-job fit is clear through hero → story → metrics → testimonial → plan choice →
  closing. The pricing section is structurally conventional and easy to scan.
- Desktop rhythm is too open through the staggered story cards. The page has a long
  sparse middle and limited section-to-section structural novelty.
- The pricing fallback looks like a generic three-card SaaS row. It does not leak Relume
  colors/type, but its conventional anatomy is exactly the homogenization risk under
  audit.
- Pricing copy is component-fit but semantically thin for “pricing” because the fixed
  evidence-safe brief intentionally supplied no invented prices. The section-rule audit
  consequently skipped price-parity checks.
- Mobile reading order is coherent and no squeezed columns are visible. The page is long
  but legible.
- No orphan final-row void or missing bound asset passed into the wireframe/media gates.
  However, the renderer supplies default brand photography to cards without explicit
  assets, causing visually duplicated/reused photography and weak plan-specific media.
- Motion/interaction sanity passed, but this mostly exercises measured navigation chrome;
  the page body has little interactive evidence, so the skill-law effect is not isolated.

## Bias conclusion

Relume does not currently leak visual tokens or source copy. The severe issue is
structural competition: production auto-resolution injects Relume for use cases already
represented by brand seeds. The experiment's fallback-only policy avoided that by
offering candidates only for missing pricing. Even then, the result converged on a
generic SaaS card row and violated brand relational spacing inside those cards.

## Recommendation

1. Disable or revise production auto-resolution before promotion: resolve measured,
   designed and style candidates first; query Relume only for a missing job.
2. Add copy-shape and asset-availability scoring, hard top-k=3 and schema-backed
   `structureProvenance`.
3. Require renderer-capability filtering before a Relume candidate reaches the prompt.
4. Add a strict accessibility semantic gate for names/focus/forms and explicit 44px touch
   targets; keep Playwright as tooling.
5. Test surviving UI laws one at a time. Do not bundle them with Relume, and do not adopt
   fixed animation/radius/shadow prescriptions.
6. Repeat with multiple seeded or replayable samples before promotion. Current result is
   a useful failure case, not an improvement claim.

## Visual artifacts

- Desktop treatment shot: `shots/lane-b-desktop.png`
- Mobile treatment shot: `shots/lane-b-mobile.png`
- Desktop contact sheet: `shots/contact-sheet-desktop.png`
- Mobile contact sheet: `shots/contact-sheet-mobile.png`

The contact sheets deliberately show a `NO RENDER` tile for A rather than substituting a
rejected draft.
