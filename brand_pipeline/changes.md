# Brand-signal composition + retire shadcn defaults (2026-07-28)

## Intent

Stop HubSpot-era / SaaS globals from homogenizing every brand. Drive composition from measured brand signals (layouts → slots → components). Fresh composition only when inventing new sections. Framework/shadcn path off by default.

## Source changes

- `styles/composition-rules.md` — `section_select_and_order: reuse-captured-order-invent-freely`; freedom envelope scoped to invented sections.
- `run_pipeline.py` — Fresh Composition Contract + site-gen layout freshness: preserve measured inventories; invent only net-new sections; no invented proof/stats.
- `brand_pipeline/compose_page.py` — removed unconditional `#sec-0 { min-height: 100cqh }`.
- `brand_pipeline/compose_section.py` — hero scaffold content-sized; removed overlay `90svh` default; banded media height auto.
- `brand_pipeline/generate_composition.py` — wireframe rules no longer force visual anchors/proof; injects `compositionSignals` prompt block.
- `brand_pipeline/section_wireframe.py` + `composition_lint.py` — `proofRequired` brand-gated; text-forward sections legal; consecutive sparse ban only when brand sets `maxConsecutiveTextOnly`.
- `brand_pipeline/compose_from_composition.py` — `_has_brand_anatomy` / `_brand_wants_stat_device`; slot pass-through for measured anatomy; numeric list→stat only when brand licenses.
- `brand_pipeline/composition_signals.py` — **new** extractor + prompt + section stamping.
- `config.default.yaml` — `framework-generation-enabled: false`.
- `website-gen-framework-prompt.md` — token/headless contract; no shadcn-as-shipped.
- `src/screenshot_to_template/chrome_codegen.py` — native token chrome; no `@/components/ui` Button/Section requirement.
- `handoff/scaffold/framework-site/src/components/ui/{card,section}.tsx` — strip default shadow/radius/py-24 SaaS skin.
- Spec/contracts language updated away from “NOW = Tailwind/shadcn”.

## Tests

- `brand_pipeline/tests/test_brand_signal_composition.py` (new)
- Updated `test_section_wireframe.py`, `test_composer_multicolumn.py`

```bash
./venv/bin/python -m unittest brand_pipeline.tests.test_brand_signal_composition \
  brand_pipeline.tests.test_section_wireframe \
  brand_pipeline.tests.test_composer_multicolumn
```

## Follow-ups

- Optional Radix headless wrappers for interactive chrome (opt-in framework only).
- Persist `compositionSignals` onto brand.yaml at extract time (currently derived on the fly from `layouts[]`).

## Verification run — greenhouse-4 (2026-07-28)

- Built `runs/greenhouse-4/` from greenhouse-v2 facts; harness + replica under brand-signal path.
- Fixed `composition_signals._slots_of` to enrich slot contracts from `blockMapping` (Greenhouse stats).
- Harness quality ok; replica overall 0.7496; viewer regenerated.

# Gate the framework generation lane (2026-07-28)

## Intent

Framework generation was the ONE generation path with no gate. It did model work
and wrote a React app without ever calling the validator, reading the replica
score, or calling `assert_generation_allowed`. Every recurring fidelity failure
attributed to that lane (invented stats/testimonial bands, assets bound to the
wrong slots, a blank page, srcless placeholder plates, a cross-brand overlapping
header, literal `\uXXXX` escapes in rendered text) was produced by a lane that a
gate would have stopped. It also skipped `tsc`, discarded the assembled payload
it sent to the model, and let a hand-authored `manifest.json` claim a run
completed after the orchestrator had crashed at G3.

## Source changes

- `src/screenshot_to_template/framework_generator.py` — the tracked chokepoint every
  framework generation goes through (`run_pipeline.py` and per-run lane scripts both
  call `generate_framework_site`), so all four fixes live here:
  - FAIL-CLOSED GATE. `resolve_brand_lane_dir` walks up from the output dir to the
    brand lane; `assert_framework_generation_allowed` refuses via
    `pipeline_flow.generation_gate_detail` BEFORE any scaffold or model work, naming
    the blocking gate (`G3 (harness)`, `G4 (replica) 0.7437 < bar 0.90`).
  - OVERRIDE, opt-in and default OFF: `allow_ungated=` /
    `FRAMEWORK_GENERATION_ALLOW_UNGATED=1` / `framework-generation-allow-ungated`.
    The refusal is logged in full and recorded in `framework-report.json`.
  - FROZEN INPUTS. `freeze_generation_snapshot` writes `site-generation-input.md`
    (the exact assembled payload), `site-generation-prompt.md` (the prompt used) and
    `site-generation-request.json` into the run's `single/` dir BEFORE the model call.
  - TYPECHECK. `build_framework_project` runs `npm run build` (`tsc -b && vite build`)
    instead of `build:nocheck`.
- `handoff/scaffold/framework-site/package.json` — `build:nocheck` script removed so
  the shortcut cannot be re-taken.
- `brand_pipeline/pipeline_flow.py`
  - `generation_gate_detail` — structured gate state (`blockedGate` / `gateName` /
    `source` / `replica` / `recordedReplica`), so a refusal is actionable.
    `generation_gate_status` is now a tuple view over it.
  - `measured_replica_overall` — `compose/replica/replica-report.json` is the SINGLE
    SOURCE OF TRUTH for the score. When `manifest.json` disagrees the measured report
    wins and the drift is named in the refusal.
  - `honest_manifest_fields` / `_update_manifest_status` — `status`,
    `pipeline_run_completed`, `generationAllowed` and `blockedGate` are all derived
    from the gate outcome, and `replica.overall` is copied from the measured report.
    A lane that failed a gate can no longer describe itself as a completed run.
  - The manifest reader accepts both `validation.errors` and
    `validation.c1_c28_errors`, and reads a run-root manifest ONLY to explain a
    refusal, never to grant generation.
- `tools/extract/validate_brand_evidence.py` — C12 widened to `framework` via
  `_check_escape_hygiene`, with two deliberately different scopes (see below).
- `config.default.yaml` + `src/screenshot_to_template/config.py` +
  `run_pipeline.py` — `framework-generation-allow-ungated: false`.

## C12 scoping

- Double-escaped HTML entities: scanned in `*.html` of every generated dir including
  the built framework page. Measured false positives on greenhouse-4's real bundle: 0.
- Literal `\uXXXX`: scanned in model-authored framework SOURCE (`**/src/**`
  `.tsx/.ts/.jsx/.css`) only. The built single-file page inlines the minified vendor
  bundle, which legitimately carries 51 `\uXXXX` regex literals (React's XML-name
  char classes, `/\u0000|\uFFFD/g`), so scanning it would report ~50 false positives
  per run. `node_modules` is pruned during the walk, not filtered after it.

## Manifest discrepancy — verdict

`pipeline_run_completed` is written by NO tracked code; it was hand-authored, as was
`replica.overall: 0.8206`. The measured `replica-report.json` (17:08) says `0.7437`,
and this changelog recorded `0.7496` for the same lane — three numbers for one run,
which is what a hand-maintained cache produces. The manifest was stale, not
malicious. Fixed by making the flow own those fields and by treating the measured
report as authoritative. `runs/greenhouse-4/manifest.json` is left as the record of
what happened.

## Tests

- `brand_pipeline/tests/test_framework_lane_gating.py` (new, 27 tests)

```bash
./venv/bin/python -m pytest brand_pipeline/tests/test_framework_lane_gating.py \
  brand_pipeline/tests/test_pipeline_flow.py \
  brand_pipeline/tests/test_brand_evidence_contract.py \
  brand_pipeline/tests/test_brand_signal_composition.py -q   # 181 passed
./venv/bin/python -m pytest brand_pipeline/tests -q           # 2075 passed
```

Full-suite failures (12 failed / 4 errors) are all
`BrowserType.launch: Executable doesn't exist` — Playwright browsers are absent in
this environment. They reproduce on files this change does not touch.

## Verification

- `npm run build` (with `tsc -b`) on greenhouse-4's generated app: clean. The one
  defect `build:nocheck` had hidden — a `className` prop `BrandMark.tsx` did not
  accept — was already fixed at the scaffold level, so enabling the check surfaced
  no new errors.
- `tsc -b` on `handoff/scaffold/framework-site`: clean.
- C12 on greenhouse-4's real framework output: 0 errors in 0.01s. With `\u2019`
  injected into a copy of the generated `App.tsx`: exactly 1 error, and the vendor
  bundle's 51 legitimate escapes stay silent.
- `assert_framework_generation_allowed` on the real greenhouse-4 lane: refused,
  naming the stale 0.8206 vs measured 0.7437.

## Follow-ups

- The legacy screenshot→template lane in `run_pipeline.py` has no brand lane above
  its output dir and therefore no G1–G4 state to consult; it records
  `gate.enforced: false` and proceeds. Gating it needs a gate concept for that lane.
- `runs/greenhouse-4/build_framework_lane.py` is hand-written and gitignored (the
  publisher only archives it). It inherits the gate through
  `generate_framework_site`, but nothing stops a future lane script from calling the
  provider directly.
- Existing per-run `package.json` copies still carry `build:nocheck`; only new runs
  scaffold without it.

# Page-qualified measured geometry + diagnosable gate failures (2026-07-28)

## Intent

Two silent-failure bugs, both of which destroyed information rather than producing
a wrong answer loudly.

1. **Measured band geometry was discarded on every page-qualified lane.**
   `measured_geometry._load_grounding` globbed `evidence/grounding/section-*.yaml`
   and keyed the result on the bare section NUMBER. A single-page lane names its
   grounding `section-NN-*.yaml`, so that worked. A multi-page lane names it
   `<page>-section-NN-*.yaml` (and keeps the unabridged capture under
   `evidence/pages/<page>/grounding/`), so the glob matched nothing, the index came
   back empty, every pattern was skipped at the `idx not in grounding` guard, and
   100% of measured `bandPadding` / `bandRhythm` / `deviceGeometry` was dropped.
   Fixing only the glob would have swapped one bug for a worse one: two pages
   routinely both have a `section-01`, so a number-only key collides and attributes
   one page's geometry to another page's pattern — wrong output instead of no
   output, and invisible either way.

2. **A failing gate's diagnosis did not survive the child process.**
   `pipeline_flow._run_module_cli` clipped the child's stderr to 400 characters, so
   a real harness-quality failure was cut off immediately after its header and the
   issue list existed nowhere. The same call also raised straight out of
   `gate_g3_harness` and past `write_flow_report`, so the run kept no record at all.

## Source changes

- `brand_pipeline/measured_geometry.py`
  - Band identity is now the PAGE-QUALIFIED slug the rest of the pipeline already
    uses — `tools/extract/project_sections_to_patterns.load_bands` names a band
    `<page>-<grounding stem>` and stamps that same string into `provenance[]` plus
    the page set into `sourcePages[]`. No third convention was invented.
  - `_load_grounding` returns `{slug: GroundedBand(slug, page, index, doc)}` and
    reads BOTH shapes: `evidence/pages/<page>/grounding/*.yaml` (page from the
    directory) and the flat `evidence/grounding/*.yaml` (page recovered from the
    merge's prefix when the lane has a page tree, else `""`). Overlapping slugs are
    the same band twice; the per-page capture wins. Page keys are matched
    longest-first so `a` cannot claim `a-b`'s bands.
  - `_load_section_rects` is keyed `{page: {index: rect}}`. On a multi-page lane the
    lane-canonical `evidence/section-rects.json` is ONE page's census promoted, so a
    band that knows its page reads its own page's file and never falls back to the
    canonical one. This was a second, independent mis-attribution: the measured hero
    aspect was reading the canonical page's band heights for every page.
  - `resolve_pattern_band` matches provenance tokens the same way
    `project_sections_to_patterns.coverage` does (equality or a slug prefix ending at
    a segment boundary), tries tokens in provenance order so a recurring pattern is
    measured from its first source, disambiguates a bare token through
    `sourcePages[]`, and REFUSES a token that resolves to more than one band.
  - `unresolved_patterns` (new) + a CLI line: detection for extracted patterns that
    resolve to no single band and therefore forfeit every measured fact.
  - `_provenance_index` removed (replaced by the slug resolution above).
- `brand_pipeline/pipeline_flow.py`
  - `_run_module_cli(..., log_dir=)` writes the child's COMPLETE combined output to
    `<run root>/<module>.log` and raises `ModuleCliError` carrying the output, the
    exit code and the log path. `MODULE_CLI_EXCERPT_CHARS = 4000` bounds only the
    console message, which now also names the log.
  - `_flow_log_dir` puts gate logs beside the run's other `*.log` files (the run root
    for a `runs/<lane>/brand` layout), which is where the bundle publisher already
    collects them. Log names avoid `flow` so they don't shadow the publisher's
    `*flow*.log` selection.
  - `gate_g3_harness` catches `ModuleCliError` and returns a BLOCKED `GateResult`
    carrying `failedModule` / `exitCode` / `childLog` / `childOutput`, so the failure
    reaches `flow-report.json` instead of escaping before the report is written.
  - `_run_extraction` tees the extraction runner's output: still streamed live (the
    stage is long) and now also written to `run_brand_extraction.log`. It previously
    kept no record and pointed at "output above".
  - `write_flow_report` marks a clipped markdown reason cell and points at the JSON,
    which holds every reason in full. `gate_g2_validation` already summarized in
    `reason` while keeping the complete list in `detail`; left as is.

## Tests

- `brand_pipeline/tests/test_measured_geometry_page_scope.py` (new, 16 tests) —
  page-prefixed loading, bare single-page names still loading, flat-merge page
  recovery, longest-page-prefix wins, two pages sharing a section number attributed
  correctly, no cross-page bleed, per-page rect census, ambiguous bare token refused,
  `sourcePages` disambiguation, recurring pattern measured from its first source, and
  committed-lane guards for both lane shapes.
- `brand_pipeline/tests/test_gate_failure_diagnostics.py` (new, 8 tests) — full child
  output in the log, message no longer clipped at 400 chars, oversized output elided
  in the message but whole in the log and on the exception, unwritable log dir does
  not mask the real failure, G3 records the failure as blocked, `run_flow` writes a
  report containing the complete child output.

```bash
./venv/bin/python -m unittest \
  brand_pipeline.tests.test_measured_geometry_page_scope \
  brand_pipeline.tests.test_gate_failure_diagnostics \
  brand_pipeline.tests.test_measured_geometry \
  brand_pipeline.tests.test_pipeline_flow                       # 117 passed
PLAYWRIGHT_BROWSERS_PATH="$HOME/Library/Caches/ms-playwright" \
  ./venv/bin/python -m unittest discover -s brand_pipeline/tests -t . -p 'test_*.py'
                                                                # 2074 passed
```

## Verification

- A page-qualified lane (`greenhouse-4`, pages `home` / `compare` /
  `talent-sourcing`): `_load_grounding` went 0 → 26 bands. All 17 extracted patterns
  resolve, each to a band on a page its own `sourcePages[]` declares, 0 unresolved.
  Enrichment goes 0 → 17 patterns / 40 facts under `FIDELITY_FIELDS`
  (17 `bandPadding`, 14 `bandRhythm`, 9 `deviceGeometry.columnGap`).
- Every filled `bandPadding` was traced back to the `approxPaddingPx` of the band its
  own provenance names — 17/17 exact.
- Collision proof: in that lane section numbers 0-5 are shared by three pages and 6-8
  by two, so a number-only key would have collided on EVERY band.
- Rect page-awareness proof: a `compare` band at index 5 measures its own 713.7px
  band height; the canonical (home) census would have given it 629.5px.
- Single-page lanes did not regress: `hubspot-v3` / `hubspot-v4` resolve the same 10
  bands as the old index and stay fill-absent-only complete (empty diff under
  `FIDELITY_FIELDS`, 10 patterns under `ALL_FIELDS`, unchanged). `hubspot-v2`,
  `woodwave-v2` and `remote` name bands with non-`section-NN` provenance, matched
  nothing before and match nothing now — deliberately, since fuzzy matching would be
  a new source of mis-attribution.
- No lane artifacts were rewritten; every check ran on in-memory copies.

## Not measured

The rendering / replica-score impact of the newly-flowing facts was NOT measured.
Scoring it means running the composer and replica modules, which were being edited
concurrently in this working tree, so any number would be attributable to those
in-flight changes rather than to this one. Prior measurement put consuming measured
`bandPadding` at roughly +0.005 overall on one run, with at least one band where the
composer OVER-responds and withholding the fact scored better. This change makes the
facts available and correctly attributed; whether the composer should consume all of
them is a separate calibration question and is deliberately left open rather than
gated off here.

## Follow-ups

- `brand_pipeline/render_components_preview.py` cannot record a harness-quality
  FAILURE. `main` raises at line 3378 when `harness_quality_issues` returns anything,
  and only writes `harness-quality.json` afterwards at lines 3382-3394 with all six
  checks hardcoded `True`. So the artifact is structurally always a pass, and G3's
  `quality.get("ok") is not True` branch can only ever fire on a MISSING or stale
  file, never on a recorded failure. It should write the report with `ok: false` and
  the real per-check results before failing. Left alone here: that file is owned by
  another agent in this working tree.
- Lanes whose provenance tokens are role names rather than `section-NN` slugs
  (`hubspot-v2`, `woodwave-v2`, `remote`) get no measured geometry at all. That is
  pre-existing and unchanged, but `unresolved_patterns` now makes it visible.
