# WoodWave v2 — production-planning benchmark

## Executive summary

The authoritative fresh WoodWave run took approximately **67m 07s wall time** from
the original manifest start to the final generated-page screenshot. The best
evidence-supported split is: brand extraction and measured replica **35m 18s
one-time**, copy-brief preparation up to **5m 08s**, and first marginal page
generation/repair/capture **26m 41s**.

These are observer-reconstructed wall intervals, not a complete monotonic trace. The
lane wrote future/inconsistent narrative timestamps, and a later recovery process
overwrote some extraction evidence. This report therefore uses original observer
snapshots and filesystem birth/mtime evidence. Exact authoritative runtimes for
capture, mine, measure, slice, grounding, curation, validation, deterministic render,
individual gates, and screenshot capture remain **not instrumented**.

The generated page is not fully production-ready: 7/8 applicable gates passed, with
one residual anti-slop AS-12 empty-column failure. Replica repair corrected the
source inventory from ten noisy entries to six real content sections plus chrome,
removing four unmapped bands. The corrected measured replica scores **0.7673**,
still below the 0.90 quality bar because the generic renderer drops several
multi-part measured anatomies.

## Phase timing

| Phase | Observed wall time | Evidence quality |
|---|---:|---|
| Raw extraction: capture → mine/measure/slice → 7-crop grounding → curation | ≤18m 00s | Low; original start to extraction-complete changelog mtime |
| Harness authoring + validation + measured replica | ~17m 18s | Medium; extraction-summary mtime to replica-report birth |
| Core harness file authoring within that interval | 11m 01s | Medium; first `brand.yaml` birth to final `layout-library.yaml` mtime |
| Copy/creative brief preparation | ≤5m 08s | Low; replica completion to brief birth |
| Page generation + repairs + deterministic outputs + final screenshot | 26m 41s | High; brief birth to screenshot birth |
| Total end to end | **67m 07s** | Medium; original manifest start to screenshot birth |

Known active compute is only a lower bound: seven observed composition calls consumed
**814.90s (13m 35s)** of model latency, or 20.2% of total wall time. The remaining
**53m 32s** combines agent reasoning, vision grounding, deterministic commands, gate
runs, waits, retries, and idle gaps; the records cannot separate those categories.

Authoritative deterministic command and gate runtimes are null. A concurrent recovery
rerun briefly recorded timings but rewrote the active lane, so those values are
excluded rather than mixed with the authoritative execution.

## Coverage and quality metrics

- Input: 1 source page, 32 mined DOM modules, 6 measured content patterns, and 2
  chrome systems (navbar/footer).
- Vision/assets: 7/7 crops grounded with 0 failures; 19 tagged files and 20 logical
  media assets.
- Reusability: 3 recurring measured recipes and 5 explicitly
  `synthesized-from-brand-signals` components, kept out of the measured replica.
- Validator: C1–C28, 0 errors, 2 warnings, 1 note.
- Replica: 0.7673 SSIM-style aggregate; 0 source bands unmapped. Section scores are
  navbar 0.9785, hero 0.7813, about 0.7661, gallery 0.7696, founder 0.7267,
  visit 0.6813, newsletter 0.9250, and footer 0.8432.
- Generated page: 9 sections including footer; 14 local asset references; 0 asset
  requests; 0 silent placeholders.
- Gate battery: 7/8 applicable gates passed (87.5%); conversion skipped because it
  was fact-gated.
- Artifacts: pre-compose harness snapshot ~9,632 KiB; source screenshot/assets
  8,868 KiB; final HTML 187,670 bytes; final screenshot 4,020,798 bytes.

## LLM calls, tokens, and cost

Grounding used 7 model calls, but authoritative grounding tokens and latency were not
retained. During page generation the observer captured three successive versions of
an overwritten telemetry file: 7 calls total, 6 failed before the successful call,
**173,194 input tokens**, **70,411 output tokens**, and **814.90s** aggregate model
latency. The final successful call was 90.55s with 26,355 input and 7,951 output
tokens.

No cost was recorded. Cost remains null; no model-price assumptions are applied.

The outer workflow documents 2 repair iterations, while internal generation telemetry
shows 7 actual model calls across three generator invocations. Production telemetry
must preserve both levels rather than overwriting prior attempts.

## Page result and gates

The copy-first scenario is **HEARTWOOD — Ten Makers, One Material**, with the visitor
as hero and WoodWave as guide. `editorial-luxury` was rendered with the
`luxury-fashion` preset auto-resolved beneath measured brand facts. Both
`[[PASS3-STYLE]]` and `[[MEDIA-FACTS]]` were present.

Final status after the two outer repair iterations:

- PASS: on-brand, spacing, signature, voice, section rules (2 advisories), media
  binding, and mark legality.
- FAIL: anti-slop, one AS-12 empty proof-band column.
- SKIP: conversion, fact-gated.

## One-time versus marginal work

One-time per brand:

- Capture, DOM/CSS/motion mining, multi-tier measurement, slicing, grounding, and
  asset curation.
- Brand/voice/media harness authoring, measured recipes, synthesized gaps, validation,
  and measured replica.
- Observed wall time through replica: approximately **35m 18s**.

Marginal per generated page:

- Copy brief, composition model calls, deterministic render, repairs, gate battery,
  and screenshot.
- First observed page: **26m 41s**, including unusually high repair churn.
- A one-sample serial projection is **2.25 pages/hour**. This is a low-confidence
  planning illustration, not an SLA; parallelism, cache behavior, page complexity,
  and fewer repairs could materially change it.

Historical context only: `hubspot-sol-clean-v2` recorded 838s end to end but finished
partial with failed gates and a 0.503 replica. `hubspot-v2` spans 18,030s and includes
extensive fidelity remediation to ~0.956. Neither is directly comparable to this
first-page production path.

## Bottlenecks

1. Generation repair churn: 6 failed calls before success consumed most known model
   compute, and one structural slop failure still remained.
2. Harness authoring/replica: about 17 minutes after extraction, mostly unsegmented
   agent authoring and validation work.
3. Section measurement initially included a fixed overlay, navbar, footer, and
   template-store buy box as content. Lane evidence was corrected to the six factual
   source sections; the remaining replica deficit is renderer anatomy support, not
   unmapped score bands.

## Top instrumentation improvements

1. Persist one append-only monotonic event stream for the authoritative run: every
   stage, generator invocation/attempt, repair, exit code, and wait interval. Never
   overwrite attempt telemetry.
2. Record deterministic render and every gate independently with start/end,
   duration, exit status, findings, and repair linkage.
3. Finalize a machine-readable inventory with model usage/cost, bound assets,
   requests/placeholders, section counts, file bytes, and active-compute versus queue
   or agent-reasoning time.

## Planning verdict

The harness has useful breadth and clean measured-versus-synthesized provenance, but
the run does not yet establish a production SLA. The dominant opportunities are
append-only telemetry, reliable section segmentation, and a section-level
wireframing/planning step that constrains synthesized anatomy to renderer-supported
structures before spending model calls.
