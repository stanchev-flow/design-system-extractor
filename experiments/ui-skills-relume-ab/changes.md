# Changes

## 2026-07-19

- Reworked the harness into a one-variable test: both lanes use identical brand, brief,
  style, assets, model and equal eight-attempt budget; UI-skill guidance is disabled.
- Lane A suppresses Relume. Lane B enables the production fallback resolver, which
  activates only for missing pricing and exposes three sanitized candidates.
- Both lanes rendered. A accepted on attempt 1; B accepted on attempt 7 and stamped
  `pricing-repeated-grid` as its sole first-class Relume provenance.
- Ran the complete nine-check battery on both lanes. Each passed seven and failed the
  same browser component-fit and pricing action-gap checks.
- Captured desktop/mobile screenshots and two-lane contact sheets.
- Updated the report with the valid paired visual read and revise/no-promotion verdict.

## 2026-07-17

- Read repository guidance and audited current Relume compiler, responsive parser,
  generated catalog/coverage, prompt injection, retrieval tests and wireframe precedence.
- Retrieved all ten listed ui-skills pages; the accessibility page succeeded on retry.
  Retrieved public Impeccable and ui.sh pages, but their full rule corpora were not
  available from those pages.
- Added a source-linked classification and deduplicated law/gap matrix in
  `SKILL-AUDIT.md`.
- Added current-path evidence, bias finding and fallback-only policy in
  `RELUME-PRECEDENCE.md`.
- Added isolated fixed brief/config and experiment runner. No generic source, spec,
  viewer or completed run folder was modified.
- Used gate-passing `hubspot-v2`, fixed model/style/brief/assets and equal bounded repair
  budgets. Ran Playwright with `PLAYWRIGHT_BROWSERS_PATH` unset.
- Preserved two no-render feasibility summaries. Replaced the impossible FAQ accordion
  probe with an unmeasured pricing-card job supported by the renderer registry.
- Final control A exhausted five attempts without an accepted render. Final treatment B
  passed generation on attempt 3.
- Ran on-brand, anti-slop, strict interaction, strict spacing, strict signature, strict
  voice, strict section-rule, strict conversion and media-binding checks on B.
- B passed eight checks and failed strict spacing at the pricing card body-to-action
  relation (14.39px rendered versus 40px brand fact).
- Captured B desktop/mobile screenshots and contact sheets with an explicit A no-render
  tile.
- Wrote post-render inferred structure provenance and the candid revise/no-promotion
  verdict.

Verification:

- `./venv/bin/python -m py_compile experiments/ui-skills-relume-ab/run_experiment.py`
- `env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python experiments/ui-skills-relume-ab/run_experiment.py`
- `env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python` partial-shot invocation via
  `runpy.run_path(...)[\"shoot\"]()`
- IDE lint: no issues in `run_experiment.py`

Known limitations:

- No model seed/replay, so the paired generation is not deterministic.
- A did not render, preventing a visual delta.
- Relume and surviving UI laws are bundled in B, preventing attribution.
- `structureProvenance` is external inference because the current schema lacks the field.
