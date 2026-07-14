# Changes

## Candidate

- Model: GPT-5.6 Sol
- Lane: `runs/remote/brand/compose/bakeoff-sol/`
- Brief: Remote Workforce Intelligence launch page for qualified demo requests.

## Authored artifacts

- `PROMPT.md` — exact marketer brief.
- `PLAN.md` — audience, narrative, pattern mapping, and copy safeguards.
- `copy-brief.md` — page-level copy direction and section copy.
- `composition.json` — ten-section `composition.v1` document.

## Render and verification

- Validated `composition.json` against `brand_pipeline/spec/composition.v1.schema.json`.
- Rendered `index.html` through `brand_pipeline/compose_from_composition.py`; unresolved slots: 0.
- Recorded final shared renderer SHA-256 hashes and mtimes in `RENDER-STATE.json`.
- Captured `shots/full-page-1440.png` and ten 1440px section closeups.
- Ran the on-brand gate in composition mode: overall PASS; all hard rules and invariants pass.
- Ran the anti-slop audit at 1440px and 1180px: PASS at both widths.
- Added `schema-validation.txt`, `slop-report.txt`, `onbrand-report.md`, `onbrand-report.json`, and `REPORT.md`.

## Visual corrections

- Bound accordion descriptions to the split renderer’s supported row `text` field so the first item opens with visible copy and media.
- Bound explicit existing Remote product assets to all reporting-gap cards.
- Moved the comparison explanation into a standalone paragraph and aligned the table headers to the renderer’s two-column table contract.
- Regenerated HTML and screenshots after every composition correction; no generated HTML was edited.

## Known renderer limitations

- A declared three-column card-grid knob renders as two columns with an orphan third card.
- The semantic table renderer provides one row-label and one value column, so comparison rows use a `current → product` format.
- Testimonial company SVGs fill the card media well instead of rendering as compact company marks.

