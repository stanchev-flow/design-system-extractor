# GPT-5.6 Sol experiment changes

## Status

Complete.

## Artifacts

- Added `PROMPT.md` with the GPT-5.6 Sol comparison-run brief and write fence.
- Added `PLAN.md` for the Global Payroll Consolidation Plan concept and ten-section pattern mapping.
- Added `copy-brief.md` with original final copy, form microcopy, FAQ answers, and media descriptions.
- Added schema-valid `composition.json`.
- Rendered `index.html` deterministically through `brand_pipeline/compose_from_composition.py` against the latest shared renderer state.
- Corrected composition routing for the semantic comparison table and closing form lede; no emitted HTML was edited.
- Replaced transparent card collages with the captured navy-card media family and revised card copy to match.
- Added final lane-scoped `onbrand-report.md`, `onbrand-report.json`, `slop-report.txt`, and `tokens.manifest.json`.
- Added `shots/full-page-1440.png` and one 1440px closeup for each of the ten authored sections.
- Added lane-local screenshot and Chrome runtime adapters; shared renderer and audit files remain untouched.
- Added `REPORT.md` with gate outcomes, visual review, pattern mapping, renderer notes, and stress-playbook comparison.

## Verification commands

- `./venv/bin/python -m json.tool runs/remote/brand/compose/sol-experiment/composition.json`
- `./venv/bin/python brand_pipeline/compose_from_composition.py runs/remote/brand/compose/sol-experiment/composition.json runs/remote/brand/brand.yaml -o runs/remote/brand/compose/sol-experiment --brand-dir runs/remote/brand`
- `./venv/bin/python brand_pipeline/onbrand_check.py runs/remote/brand/brand.yaml runs/remote/brand/compose/sol-experiment --layout navbar --composition --report onbrand-report.md`
- `node --import ./runs/remote/brand/compose/sol-experiment/slop_chrome_preload.mjs brand_pipeline/slop_audit.mjs runs/remote/brand/compose/sol-experiment/index.html`
- `node runs/remote/brand/compose/sol-experiment/shots/shoot_sections.mjs runs/remote/brand/compose/sol-experiment/index.html runs/remote/brand/compose/sol-experiment/shots`

## Results

- Composition render: PASS, 0 unresolved slots.
- On-brand hard gate: OVERALL PASS.
- Anti-slop audit: PASS at 1440px and 1180px.
- Visual review: all ten section closeups and full-page screenshot inspected; no 1440px collision or unexplained content scaffold found.
