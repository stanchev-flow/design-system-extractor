# Candidate A report

## Summary

- Model: **GPT-5.6 Sol**
- Concept: **From workforce records to decision clarity**
- Sections: **10**
- Goal: qualified demo requests from VP People, CFO, and HR Operations leaders at international companies with 500+ employees.
- Elapsed time: **approximately 12 minutes** (started from the 19:21 task timestamp; final verification completed at 19:33:03 +0100).

The page frames Workforce Intelligence as a shared decision layer. The narrative moves from fragmented reporting, through capabilities and a four-step review flow, into role-specific value, a direct workflow comparison, broader Remote customer proof, trust context, FAQ, and a qualification form.

## Section and pattern mapping

1. `workforce-intelligence-hero` — adapted `hero-inset-noise-panel`; Remote noise art, globe/product UI illustration, and two pill actions.
2. `reporting-gap` — adapted cards scaffold; three specific reporting failure modes with existing Remote product assets.
3. `decision-layer-capabilities` — adapted `feature-accordion-deep-accent`; four capabilities, one active deep-maroon item, and per-item Remote UI media.
4. `how-workforce-intelligence-works` — adapted `features-card-grid-navy-media`; four operational steps using existing navy product art.
5. `leadership-views` — adapted `features-card-grid-navy-media`; VP People, CFO, and HR Operations views.
6. `workflow-comparison` — novel stack within the supported renderer vocabulary; semantic table comparing the current workflow with Workforce Intelligence.
7. `remote-customer-perspectives` — reused `testimonial-card-row`; two canonical attributed Remote customer quotes with an explicit broader-platform disclosure.
8. `operational-trust` — adapted `infra-proof-split`; existing Remote operational UI asset and restrained governance copy.
9. `workforce-intelligence-faq` — adapted disclosure stack; five buying and implementation questions with one active deep-accent item.
10. `qualified-demo-request` — adapted conversion stack; eight qualification fields and a single primary action.

## Gates

- Composition JSON syntax: **PASS**
- `composition.v1` schema: **PASS**
- Deterministic renderer: **PASS**
- Unresolved slots: **0**
- On-brand composition gate: **PASS**
  - All three `neverDo` rules pass.
  - All 14 hard composition invariants pass.
- Anti-slop audit at 1440px: **PASS**
- Anti-slop audit at 1180px: **PASS**
- Visual inspection: **PASS with documented renderer limitations**

Gate outputs:

- `schema-validation.txt`
- `onbrand-report.md`
- `onbrand-report.json`
- `slop-report.txt`
- `RENDER-STATE.json`

## Artifacts

- Exact brief: `PROMPT.md`
- Plan: `PLAN.md`
- Copy direction: `copy-brief.md`
- Structured source: `composition.json`
- Deterministic render: `index.html`
- Token provenance: `tokens.manifest.json`
- Render state: `RENDER-STATE.json`
- Changelog: `changes.md`
- Screenshot utility: `capture-shots.mjs`

## Screenshots

- Full page: `shots/full-page-1440.png`
- Closeups:
  - `shots/01-hero-1440.png`
  - `shots/02-reporting-gap-1440.png`
  - `shots/03-capabilities-1440.png`
  - `shots/04-how-it-works-1440.png`
  - `shots/05-leadership-views-1440.png`
  - `shots/06-comparison-1440.png`
  - `shots/07-customer-proof-1440.png`
  - `shots/08-operational-trust-1440.png`
  - `shots/09-faq-1440.png`
  - `shots/10-lead-form-1440.png`

## Visual inspection and corrections

The first render exposed three composition-level mistakes: capability item descriptions were bound under `body` rather than the split renderer’s row `text` field; two problem cards had fallen back to decorative art instead of explicit product assets; and the comparison description was embedded in a generic header path that did not render it. Those were corrected in `composition.json` and the page was regenerated. No HTML was edited.

The final screenshots show a clear hero, an active capability state with visible supporting copy and media, complete product-art cards, a readable comparison, an attributed proof section, a working FAQ state, and a complete qualification form.

## Shared renderer state and defects

`RENDER-STATE.json` records SHA-256 hashes and mtimes immediately before and after the final render; the two snapshots matched. Shared `compose_section.py` and `component_render.py` changed while this candidate was in progress, so the final render was intentionally regenerated against the later state rather than patched locally.

Observed limitations in that final renderer state:

1. The `columns: "3"` knob on the seeded Remote card-grid pattern still renders three modules as a two-column grid with an orphaned third card. This lengthens the problem and leadership sections and weakens their scan rhythm.
2. The generic semantic table supports a row-label column plus one value column, not two independent comparison value columns. The composition therefore expresses each row as `current → Workforce Intelligence`; it is accurate but less immediately scannable than a true three-column comparison.
3. Testimonial company SVGs are treated as full 16:10 media wells rather than compact company marks, making the logos visually oversized.

These were documented rather than compensated for with lane-local HTML or shared renderer edits.

## Self-critique

The strongest part is the conversion narrative: it is specific to the three buying roles, avoids invented metrics, makes the comparison explicit, and qualifies the demo without bloated copy. The hero and active capability section feel recognizably Remote while the narrative is distinct from the homepage.

The main weakness is pacing. Renderer-enforced two-column card grids create unnecessary page height and orphan cards, and the testimonial logo treatment is visually louder than the restrained proof copy. The product story is also necessarily conceptual because the brief and canonical inputs provide no verified Workforce Intelligence feature specification; the copy stays honest, but a real launch page would benefit from confirmed product screenshots, exact data-source behavior, access-control details, and implementation facts.

