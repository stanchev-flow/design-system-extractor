# evals/matrix — the fixed evaluation matrix (standing brief corpus)

> **Status: stage A authored (2026-07-14).** The corpus is the standard OFFLINE
> instrument for measuring pipeline quality across checkpoints (style bakeoffs,
> prompt changes, gate additions, archetype-library growth). It costs generation
> time only when a round is deliberately run — never inside any lane's loop.

## The matrix

6 campaign/page types × 2 extracted brands = **12 standing briefs**, one complete
composition brief each, in the hero-gallery brief shape (YAML frontmatter +
copy-grounded body):

| campaignType (conversion-structure.yaml) | pageType | hubspot-v2 | remote |
|---|---|---|---|
| `leadgen-gated-content` | signup | `briefs/hubspot-v2/leadgen-gated-content.md` | `briefs/remote/leadgen-gated-content.md` |
| `demo-request` | demo | `briefs/hubspot-v2/demo-request.md` | `briefs/remote/demo-request.md` |
| `product-launch` | product | `briefs/hubspot-v2/product-launch.md` | `briefs/remote/product-launch.md` |
| `webinar-event` | event | `briefs/hubspot-v2/webinar-event.md` | `briefs/remote/webinar-event.md` |
| `comparison` | comparison | `briefs/hubspot-v2/comparison.md` | `briefs/remote/comparison.md` |
| `pricing` | pricing | `briefs/hubspot-v2/pricing.md` | `briefs/remote/pricing.md` |

Brief doctrine:

- **Copy-first** (spec/archetype-library.md §3): every brief carries real,
  brand-voiced copy facts to bind — the generator selects/sequences/expresses,
  it never invents the campaign.
- **Brand-true**: copy respects each brand's voice-facts budgets (sentence
  lengths, casing, no-hype lexicon) and cites only brand-plausible product
  facts; proof numbers are the brands' own published shapes.
- **Frozen between rounds**: briefs change ONLY with a changelog entry here —
  a moving instrument measures nothing. Fixing a brief defect resets baselines
  for that cell (note it in the round log).
- `campaignType:` frontmatter binds each brief to its conversion-structure
  grammar (brief-time guidance + the stage-B checker).

## Round protocol

A ROUND is one full pass over all 12 briefs at a named checkpoint.

1. **Allocate** `evals/matrix/runs/<yyyy-mm-dd>-<label>/` (label = the thing
   being measured: `baseline`, `style-swiss-bakeoff`, `prompt-vNNN`…). Record
   the repo state (commit / dirty-file note) in the round's `round.md`.
2. **Generate** each brief through the REAL generation loop
   (`generate_composition.generate_composition` — shortlist → model → validate →
   prefilters → render → onbrand gate → bounded repair, `max_repairs=3`), style
   pin `corporate-saas-clean` (the proven generative-lane setup), outputs under
   `runs/<round>/<brand>/<campaignType>/`. Wall-clock the generation of each
   brief (see Timing below).
3. **Gate** every page with the full post-render battery: onbrand composition
   gate (recorded during generation) · slop @1440+@1180 · interaction `--strict`
   · spacing `--strict` (scale cells bind: generative lanes) · signature
   `--strict` · voice — plus, once stage B lands, section-rules and the
   conversion-structure checker. Gates READ pages; they never touch the
   generation loop.
4. **Record** in the round dir:
   - `results.json` — per brief: gate pass/fail vector, finding counts by gate,
     spacing conformance counts (conform/drift/hard/unmapped), attempts/repairs,
     archetypes + section-family sequence, timing seconds;
   - `results.md` — the human table (12 rows), plus deltas vs the previous
     round (new failures, cleared failures, conformance movement);
   - `round.md` — checkpoint context, repo state, anomalies, follow-ups;
   - `shots/` — 1440×900 reduced-motion full-page PNG per page + contact sheet
     (the gallery runner's shot recipe).
5. **Judge (optional, offline)** — the conversion-structure rubric
   (spec/conversion-structure.md) scores matrix pages 1–5 per criterion in
   eval rounds only. Judge scores are trend lines, never gates.

## What a round measures

- **Gate deltas**: a checkpoint that turns any green cell red is a regression
  to explain or revert — the matrix is the standing tripwire for "the prompt
  change helped heroes but broke pricing pages".
- **Conformance movement**: spacing conform/hard counts and slop finding counts
  per cell, compared round-over-round.
- **Structure fidelity**: section-family sequence per page vs the campaign's
  conversion grammar (advisory rows included), so composition drift is visible
  even while gates stay green.
- **Cost honesty**: per-brief timing so any pipeline change carries a
  before/after generation-time comparison (the neutrality proof for gate-side
  work: post-render audits must move gate time, never generation time).

## Timing discipline

`results.json` records per brief: `generateSeconds` (model + repair loop, as
reported by the runner), `attempts`, and `gateSeconds` (post-render battery,
separately). Rounds compare LIKE to LIKE: generation-time deltas call out model/
prompt changes; gate-time deltas call out battery growth. The first completed
round (`baseline`) is the reference budget for both.

## Changelog

- 2026-07-14 — stage A: corpus authored (12 briefs), protocol defined. No round
  run yet; the baseline round is stage-B work (post pass-2).
