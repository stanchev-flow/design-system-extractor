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
