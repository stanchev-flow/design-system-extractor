# Phase D — signup-launch-v2 live lane (2026-07-07)

Runner for the Phase D live composition lane. See root `changes.md` (Phase D entry)
for the full run report.

- `run_v2.py`: calls `generate_composition.generate_composition` against the
  re-extracted `runs/remote/brand/brand.yaml` (style `corporate-saas-clean`,
  brief `signup-launch`, layout context `hero`, **no variety directive** — the
  point was proving the derived fidelity rules alone hold the all-light grammar).
- `run.log` … `run4.log`: iterations of the live Anthropic call. Failures along
  the way drove real pipeline fixes (recorded in root `changes.md`):
  `_PANEL_INTENT_RULE` (hero came back `surfaceIntent: panel` → white band),
  seed-block slot shapes incl. z:back backgrounds (nav dropped when the model
  skipped the hero background asset), width vocab mapping (`full` → `stretch`),
  logo-slot conversion-classification fix (partner/badge strips lost media).
- `results.json`: final accepted run metadata.
- Output lane: `runs/remote/brand/compose/signup-launch-v2/` — gates PASS
  (`onbrand-report.md` OVERALL: PASS). Prior lanes untouched.
