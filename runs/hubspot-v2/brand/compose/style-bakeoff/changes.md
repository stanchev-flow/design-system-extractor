# style-bakeoff — pass 3 checkpoint D (2026-07-14)

Shared folder for the 3-style bakeoff. Primary log:
`brand_pipeline/contracts/style-library/changes.md` (stage 4 section — the
UPFRONT pass criteria live there and were written BEFORE any generation).
This file is the lane-local record.

## Criteria summary (authoritative copy in the contracts changelog)

- **C1 — full gate battery green per page**: onbrand `--composition` PASS ·
  slop @1440+@1180 exit 0 · interaction `--strict` exit 0 · spacing
  `--strict` exit 0 (0 hard / 0 off-scale) · signature `--strict` PASS ·
  voice `--strict` exit 0.
- **C2 — style distinctiveness observable**: not all three heroes on one
  skeleton; ≥1 non-hero section differs in the directive's predicted
  direction; per-style directive echo readable on the shots (structural, not
  palette — brand tokens paint everything by precedence).
- **C3 — brand recognizability maintained**: signature strict PASS ×3 (accent
  scope, serif display/sans body, 8px never-pill controls, licensed dark
  family); neumorphism additionally proves graceful demotion (gates green,
  brand contrast wins over the style's low-contrast pull).

## Setup

- Brand: hubspot-v2 · brief: `evals/matrix/briefs/hubspot-v2/product-launch.md`
  (READ-ONLY, shared) · base style: `corporate-saas-clean` · model:
  claude-opus-4-8 (repo default path) · `force_off_grid=True` (gallery-lane
  convention) · `max_repairs=2` (the iteration budget — initial attempt + ≤2
  repair round-trips, no outer regeneration).
- Pass-3 delta per lane: `style_directives` = resolver block for
  {hero, feature-trio, metrics-band, testimonial, cta-band} resolved against
  the hubspot bundle (style-library styles: swiss / editorial-magazine /
  neumorphism).
- Lanes: `../style-bakeoff-swiss/product-launch/`,
  `../style-bakeoff-editorial-magazine/product-launch/`,
  `../style-bakeoff-neumorphism/product-launch/`.
- Driver: `run_bakeoff.py` (this folder). Battery reports per lane under
  `<lane>/battery/`. Contact sheet:
  `../style-bakeoff-contact-sheet.png`.

## Iteration log

Authoritative stage-4 log (round-by-round, per page, with root causes):
`brand_pipeline/contracts/style-library/changes.md`. Summary:

- **Round 1** (original directive block): neumorphism PASS attempt 0; swiss
  FAIL ×3 attempts (schema, then alignment-resolution ×2 + archetype-physics);
  editorial-magazine FAIL ×3 attempts (alignment-resolution ×2, then a repair
  regression). Root cause: flush-asymmetric directive postures + reused
  patterns' own counterweight-less left stance. Round-1 artifacts:
  `../style-bakeoff-{swiss,editorial-magazine}/_iter1-fail/`.
- **Prompt fix** (stage-2 code, test-pinned): the directive block gained the
  generic HARD alignment contract.
- **Iteration 1 (swiss, e-m)**: regeneration → both onbrand PASS attempt 0.
- **Iteration 2 (swiss, e-m)** + **iterations 1–4 (neumorphism — budget
  overrun, logged)**: composition-level re-shapes into the adapter's proven
  vocabulary (button contracts, stat arrays, header body keys, real assets,
  archetype re-author for the neumorphism hero). Driver: `iterate_fix.py`.
- **Final battery** (`run_battery.py`, true exit codes in
  `battery-summary.json`): onbrand PASS ×3 · interaction 0 ×3 · signature
  PASS ×3 · voice PASS ×3 · scale 0 off-scale ×3 · slop PASS ×2 (swiss AS-12
  residual) · spacing FAIL ×3 (systemic header.heading-to-body cell + swiss
  stat gutter) — all residuals catalogued as renderer/adapter/audit follow-ups
  in the contracts changelog.

## Verdict (against the upfront criteria)

**C1 NOT MET · C2 MET · C3 MET → checkpoint-D NO-PASS; no style graduates**
(swiss / editorial-magazine / neumorphism remain `unvalidated seed`). The
style-resolution + injection layer performed as designed (visible, distinct,
on-brand structure); the residual reds are pre-existing composition-vocabulary
and renderer↔audit mismatches newly exposed by style-shaped compositions.
Contact sheet: `../style-bakeoff-contact-sheet.png`. Replicas after
everything: hubspot-v2 0.956 · Remote 0.950 (held exactly).
