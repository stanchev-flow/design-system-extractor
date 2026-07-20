# WoodWave v2 benchmark evidence log

- 2026-07-17T13:10:23Z — Recovery benchmark started in the same process as the
  extraction run. Phase timestamps and monotonic durations will be persisted
  after every executable stage; unexposed token/cost data will remain null and
  explicitly marked `not_instrumented`.
- 2026-07-17T13:23Z — STOP directive received: the separate completed lane is
  authoritative. All timings produced by the duplicate recovery attempt were
  invalidated and excluded from `metrics.json` / `REPORT.md`. No further writes
  were made under `runs/woodwave-v2/brand/`.
- Completed a read-only benchmark from authoritative lane evidence only:
  `changes.md`, `compose/replica/replica-report.json`,
  `compose/exhibition-storybrand/page/generation-telemetry.json`,
  `compose/exhibition-storybrand/page/composition.json`, the assembled prompt,
  final page HTML, and `shots/heartwood-exhibition-fullpage.png`.
- Precise phase values absent from authoritative telemetry remain
  `null` / `not_instrumented`; no duplicate-run value was retained. The only
  precise page latency retained is 90.55s from authoritative generation
  telemetry. The 2,400s harness authoring value is explicitly low-confidence,
  minute-resolution wall evidence from the lane changelog.
- Wrote `metrics.json` and `REPORT.md`; validated sources are named on every
  non-null metric. No commit or push was performed.

- 2026-07-17 — Created this observer-only benchmark directory. No files under
  `runs/woodwave-v2/`, pipeline source, or shared changelogs were modified.
- Inspected `runs/woodwave-v2/brand/manifest.json` first, then
  `runs/woodwave-v2/brand/changes.md`, as required by the run-folder protocol.
- Recorded the in-progress artifact inventory and disk usage with `ls -la` and
  `du -sk` for `runs/woodwave-v2/brand/` and `screenshots/woodwave-v2/`.
- Inspected extraction evidence including `evidence/section-rects.json`,
  `assets-manifest.json`, and the authored `brand.yaml`.
- Inspected historical context only after each available manifest:
  `runs/hubspot-v2/brand/manifest.json` then its `changes.md`;
  `runs/hubspot-sol-clean-v2/manifest.json` then its `changes.md`,
  `telemetry-summary.json`, `telemetry.jsonl`, `MODEL-ACCOUNTING.md`, and
  `REPORT.md`; `runs/remote/brand/` had no manifest, so its `changes.md` was read
  directly.
- Historical command-runtime evidence inspected from persisted terminal records:
  HubSpot v2 vision grounding (`214.523s`), HubSpot Sol deterministic evidence
  (`1.835s` forced rerun), and Remote replica composition (`8.153s`).
- The active manifest was still `status: not_run` /
  `pipeline_run_completed: false` at the first observation, so final metrics
  remained pending while the run continued.

## Observer timing and telemetry reconstruction

- The original manifest observed before concurrent recovery rewrites recorded
  `started_utc: 2026-07-17T12:12:00Z`. Its later narrative completion timestamp was
  rejected because it was in the future relative to filesystem time.
- Original authoritative filesystem snapshots (local timezone UTC+1):
  - source full-page screenshot: `2026-07-17T13:14:30+0100`, 5,930,146 bytes;
  - extraction-complete `changes.md` snapshot: modified by approximately 13:30;
  - `brand.yaml` birth: 13:35:56; final `layout-library.yaml` mtime: 13:46:57;
  - replica report birth: 13:47:18;
  - copy brief birth: 13:52:26;
  - authoritative page HTML final mtime: 14:17:55, 187,670 bytes;
  - final screenshot birth: 14:19:07, 4,020,798 bytes;
  - authoritative final changelog mtime: 14:21:58.
- Derived wall intervals used in the report: raw extraction upper bound 18m;
  harness/validation/replica about 17m18s; copy-brief upper bound 5m08s; page
  generation through screenshot 26m41s; total start-to-screenshot about 67m07s.
- `du -sk` observer snapshots: core harness before compose output 9,632 KiB;
  `screenshots/woodwave-v2/` final footprint 8,868 KiB; assets 3,392 KiB; evidence
  7,508 KiB; replica output 10,876 KiB; authoritative page directory 3,416 KiB.
- Generation telemetry was overwritten between generator invocations. The observer
  captured all three versions before overwrite:
  1. 3 calls: latencies 165.89/120.35/116.08s; inputs
     22,886/23,094/23,094; outputs 13,896/10,129/9,813; all render-fail.
  2. 3 calls: latencies 146.86/91.61/83.56s; inputs
     25,791/26,037/25,937; outputs 12,478/8,296/7,848; gate-fail/lint-fail/gate-fail.
  3. 1 successful call: 90.55s; 26,355 input; 7,951 output; gate PASS.
  Aggregate observed composition usage: 7 calls, 814.90s model latency,
  173,194 input tokens, and 70,411 output tokens. Cost was not recorded.
- Final page evidence: 9 rendered sections including footer, 14 local asset
  references, 0 asset requests, 0 silent placeholders, and 7/8 applicable gates
  passing. Anti-slop retained one AS-12 failure; conversion was fact-gated and
  skipped.
- Concurrent recovery timing values were excluded because that process rewrote the
  active lane after the authoritative run. Its scripts were not used as current-run
  timing evidence.

## Reconciliation result — 2026-07-17
- Revalidated the benchmark against the reconciled final lane. Duplicate recovery
  phase timings remain invalid and must stay `null` / `not_instrumented`; no timing
  was reconstructed or invented. The existing 90.55s generation latency comes from
  the retained canonical page telemetry, while the 2,400s harness-authoring value is
  explicitly a low-confidence minute-resolution estimate from the original lane
  changelog.
- Final authoritative artifact counts remain 7 grounded crops, 19 tagged/curated
  assets, 20 logical media assets, 6 measured patterns, 3 recipes, and 5 synthesized
  components. C1-C28 remains 0 errors / 2 warnings / 1 note; measured-only replica
  score is 0.5435.
- `REPORT.md`'s earlier spacing-PASS statement is superseded by
  `runs/woodwave-v2/brand/compose/exhibition-storybrand/page/gate-reconciliation.json`.
  The strict spacing command exits 1 (3 wrong-step + 1 off-ladder); the prior PASS
  claim resulted from a pipe masking the audit exit code. Other final statuses:
  onbrand/signature/voice/section-rules/media-binding/mark-legality PASS, conversion
  SKIP, slop FAIL with one AS-12 residual.

## Replica metric correction — 2026-07-17
- Corrected the factual source inventory to six content sections plus navbar/footer
  chrome. The prior ten-entry measurement included a fixed noise overlay, navbar,
  footer, and Webflow template-store buy box as content.
- Replica changed from 0.5435 with four unmapped bands to 0.7673 with zero unmapped
  bands. Updated only the affected replica metrics and diagnosis in `REPORT.md` and
  `metrics.json`; all timing uncertainty and generated-page gate results remain
  unchanged.
