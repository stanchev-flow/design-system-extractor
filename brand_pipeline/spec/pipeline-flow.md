# Canonical pipeline flow — ordered stages with hard, fail-closed gates

This spec defines the ONE ordered flow that turns a source site into a
generation-ready brand lane, and the HARD QUALITY GATES enforced between stages.
It is brand-agnostic: nothing below encodes any brand's colors, sections, or copy.

## Why this exists

The stages already existed as separate scripts an operator invoked by name
(extract, validate, render the harness, score the replica, generate). Nothing
enforced their ORDER or their quality bars, so a run could go
`extract → page generation` — skipping the harness build and accepting a low
(0.543) replica — because the flow depended on the operator naming each sub-step.

The flow is now baked in as a first-class orchestrator
(`brand_pipeline/pipeline_flow.py`, driven by `run_pipeline_flow.py`). One
high-level intent runs the whole ordered sequence and **fails closed** at the
first gate it can't clear. A single intent ("extract brand `<url>`", "build
replica for `<lane>`") reproduces the full ordered flow end-to-end — the operator
never has to name the sub-steps.

## The ordered stages

```
capture ─▶ G1 extraction ─▶ G2 validation ─▶ G3 harness ─▶ G4 replica ─▶ G5 generation
             (evidence)       (C1–C28)         (spec book)    (fidelity)     (creative page)
```

Extraction itself is the evidence-first stage runner
(`run_brand_extraction.py`: mine-dom · mine-css · mine-motion · measure · slice ·
ground · curate · author · validate). The orchestrator runs it when a fresh
`--capture` is supplied, then verifies its output at G1. `author` is executable:
`brand_pipeline/author_brand.py` runs a declared author DAG implemented by
`staged_author.py`: `foundation → copy-chrome → patterns-recipes → media →
media-tags → projections`. Each model node receives a deterministic, stage-specific evidence
projection with referenced source paths, a byte cap, output-token cap, hard child
process timeout, zero provider retries, atomic install, and a persisted checkpoint.
The projection node deterministically renders `brand.md`, `style-scale.yaml`, and
`voice.md`. C1-C28 failures are routed only to their owning stage with that stage's
existing output and evidence; validation never starts until every node completes.
Missing credentials block at AUTHOR before validation. Existing valid checkpoints
skip unless `--force-author` or `--force-author-stage <name>` is supplied.

## The gates (each pass condition)

| Gate | Name        | PASS condition | On failure |
|------|-------------|----------------|------------|
| G1   | extraction  | Every evidence + authored artifact the downstream gates read is on disk (`brand.yaml`, `layout-library.yaml`, `section-copy.yaml`, `assets-tagged.json`; `evidence/{dom-sections,css-facts,computed-styles,section-rects,motion-audit}.json`; ≥1 `evidence/grounding/*.yaml`). | `blocked` — names exactly what is missing. |
| G2   | validation  | `validate_brand_evidence.py` (C1–C28) reports **0 errors**. Warnings + notes are recorded, never blocking. | `blocked` — lists the errors. |
| G3   | harness     | The components-preview **spec book** exists at the canonical lane path (`components-preview/index.html`), which is exactly where Studio serves it (`studio_server.static_brand_lanes`). The slot-contract **catalog** (`catalog/index.html` + `catalog.json`) is **built when missing** (idempotent). With `--studio-url`, an HTTP 200 on the preview route is additionally required. | `blocked` — spec book missing / not reachable. |
| G4   | replica     | The measured-only replica (`compose_replica.py`) scores **overall ≥ bar** (default **0.90**), within a bounded diagnose→repair→re-score loop. | `needs_iteration` — records the score, the iteration trajectory, and per-band diagnostics (the below-bar bands to repair). |
| G5   | generation  | Runs **only after G1–G4 pass**. `generate_composition` produces a page that clears its on-brand gate battery. | `blocked` — generation refused / did not pass its gate. |

## The replica threshold (0.90) and its rationale

The default bar is **0.90**. It is the obvious separating line for the committed
evidence:

- **hubspot-v2** replica **0.957** — PASSES (a complete, review-ready lane).
- **remote** replica **0.951** — PASSES (a complete, review-ready lane).
- **woodwave-v2** replica **0.767** — BLOCKS (`needs_iteration`; the measured
  renderer drops required multi-part anatomy — hero overlap layers, alternating
  media/copy rows, gallery carousel chrome, ticket-pricing row, footer link
  stack).

0.90 sits comfortably above the two passing brands and well above the failing
one, so raising it slightly would still pass the good brands and lowering it
toward 0.77 would wrongly admit the failing lane.

The bar lives in **one place** — `pipeline_flow.DEFAULT_REPLICA_BAR` — and is
configurable per run via `--replica-bar` (CLI) / `replica_bar=` (`run_flow`). It
is never hardcoded in scattered call sites.

## Fail-closed semantics

- A failed gate STOPS the flow immediately. No later gate runs; **G5 generation is
  never reached** on a failed spine.
- Extraction/author subprocess failures are converted into a blocked G1 result;
  the flow still writes both reports and the manifest reason. They never escape
  as an uncaught `RuntimeError`, and G2 is never invoked before author output
  completeness.
- The flow writes an honest `flow-report.json` (+ `flow-report.md`) into the lane
  with `status` (`completed` / `blocked` / `needs_iteration`), the `blockedGate`,
  and the reason — plus per-gate timings (the production telemetry that was
  missing). It also writes `status` + `generationAllowed` through to
  `manifest.json` when one is present.
- Creative page generation refuses independently: `generate_composition`
  (`enforce_gates=True`, the default) calls `assert_generation_allowed`, which
  reads the lane's `flow-report.json` (authoritative) or `manifest.json` and
  raises `GenerationBlocked` unless the record shows G1–G4 cleared. A lane with
  **no record at all** is refused (fail-closed). Isolated experiment harnesses may
  pass `enforce_gates=False` to opt out deliberately.

## Idempotency & resume

- Every gate is individually re-runnable. G1/G2 are read-only checks; G3 no-ops
  when the harness is already present (and only builds the missing catalog); G4
  can read an existing `replica-report.json` (`--no-replica-run`) instead of
  re-shooting.
- `--from G2|G3|G4` (or `--from validate|harness|replica`) resumes past the gates
  a lane already cleared, so a `needs_iteration` lane is repaired and re-scored
  without redoing the passing stages. Skipped gates are recorded as `skip` in the
  report.
- An evidence-complete but unauthored lane entered at G1 automatically resumes
  with `run_brand_extraction.py --stages author,validate`; it does not repeat
  capture, mining, vision grounding, or curation. Author model, timeout, repair
  budget, and force behavior are exposed as `--author-*` flags.
- `author-stage-status.json` is the resumable stage checkpoint. A failed node is
  marked `blocked` with its exact model, input bytes, timeout, duration, and reason;
  completed valid nodes skip. Forcing a node invalidates and reruns its descendants.

## One intent → the whole flow

`run_pipeline_flow.py` accepts either `--brand <key>` or a free-text `--intent`:

- `--intent "extract brand hubspot-v2"` → runs the full spine from extraction.
- `--intent "build replica for woodwave-v2"` → runs the full spine (harness
  **before** replica; it never lets "build the replica" skip the harness).
- add `--generate --brief <brief.md>` to also run G5 (only if G1–G4 pass).

The entry stage only chooses where a lane may RESUME; the ordered gate sequence
and their bars are always enforced.

## Files

- `brand_pipeline/pipeline_flow.py` — the orchestrator library (gates, threshold,
  fail-closed + resume semantics, flow report, generation guard).
- `brand_pipeline/author_brand.py` — executable evidence bundle, provider calls,
  transactional artifact writes, telemetry, validation and bounded repairs.
- `run_pipeline_flow.py` — the single high-level CLI entry.
- `brand_pipeline/generate_composition.py` — `generate_composition(enforce_gates=…)`
  calls the refusal guard before any output work.
- `brand_pipeline/tests/test_pipeline_flow.py` — threshold calibration, real-lane
  pass/block proof, fail-closed ordering, iteration bound, resume, and the
  generation refusal.
- `brand_pipeline/tests/test_author_brand.py` — author bundle/output contract,
  missing-provider block, atomic writes, bounded repairs, idempotency/force,
  golden fake provider, and extraction-failure reporting.
