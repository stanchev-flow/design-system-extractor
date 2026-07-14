# spacing-baseline — changes.md

## Phase 2 (2026-07-10, remediation session): all hard fails fixed, re-audited

`report-after.md`/`report-after.json` hold the post-fix strict run over the same 5
lanes (re-rendered once after the composer fixes): **0 hard fails everywhere**,
unmapped 72 → 4. Per lane (hard fails / unmapped): compose 2/5 → 0/0 (129/129
conform), replica 2/5 → 0/0, event-genlaunch 0/33 → 0/2, stress-playbook 8/29 →
0/2, components-preview still the whole-lane skip. Fixes B1–B7 in
`compose_section.py` (see root `changes.md` for the full table); B8 mined 8 new
facts into `brand.yaml` from `evidence/css-rules.json` (`field-to-field`,
`field-label-gap`, `form-stack`, `list-item-gap`, `list-item-inset`,
`mark-to-quote`, `quote-to-attribution`, `strip-gap`) — the auditor resolves them
via the extended `RELATIONSHIPS` map. The 4 remaining unmapped cells are all
`header.body-to-meta` (16px, hero-panel/conversion scopes): the corpus carries no
generic body→caption stack seam, so it stays the extraction follow-up (the
resolver step `body-to-meta` is pre-wired for a future re-mine). Offender
close-up proof: `../shots/remed-*.png`. Regression locks:
`brand_pipeline/tests/test_spacing_remediation.py`.

## Phase 1 (baseline)

Phase 1 of the spacing-conformance gate: contract + auditor + baseline diagnosis.
Measure/classify/rank only — **no remediation** was performed on any lane or composer.

## What was added (all NEW files; no existing file was edited)

- `brand_pipeline/spec/spacing-conformance.md` — the contract: named relationships
  (header-stack rhythm, section band padding + seams, block rows, grid/split/strip
  gutters, card anatomy, container law, list rhythm, form rhythm), the tolerance rule
  (`max(2px, 10%)` for rhythm families, `max(2px, 1%)` for widths, drift = within 2x),
  the severity ladder (`conform | drift | wrong-step | off-ladder | unmapped`), the
  measurement protocol, and the output contract.
- `brand_pipeline/spacing_audit.py` — standalone Playwright auditor.
  Run from repo root:
  `env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m brand_pipeline.spacing_audit <lanes…> --brand runs/remote/brand`
  Flags: `--out`, `--viewport WxH` (default 1440x900 = canonical tier), `--annotate`
  (lane substring for offender close-ups, default "stress"), `--top`, `--no-shots`,
  `--strict` (exit 1 on hard fails / lane errors — future gate wiring; default exit 0).
- `brand_pipeline/tests/test_spacing_audit.py` — 48 unit tests for the non-browser
  parts (fact loading from synthetic brand docs, `parse_length`, scale mining,
  resolver semantics, tolerance/severity classification, nearest-step matching,
  offender ranking, report shaping, path helpers). No Playwright in unit tests.
- `runs/remote/brand/spacing-baseline/` — this directory: `report.md`, `report.json`,
  5 annotated offender close-ups (stress-playbook lane), this changelog.

## Fact sources the auditor consumes

- `brand.yaml` `tokens.spacing.*` values at the canonical tier (1440), incl. the
  relational ladder rungs (`eyebrow-to-heading`, `heading-to-body`, `body-to-cta`,
  `block-to-block`, `column-to-column`, `grid-gap`, `panel-padding`, section paddings,
  container widths, `header-measure`).
- Token role prose magnitudes as weaker opt-in facts (`token-prose`) — e.g.
  `panel-padding`'s documented contextual ladder ("cards ~40px, hero panel up to 80px").
- `layout-library.yaml` pattern facts: `bandPadding`, `deviceGeometry.columnGap/rowGap/
  contentSpan`, `list.itemGap/triggerMinHeight`, `stackMeasure`, `slots[].mediaScale.gap`;
  plus prose-note fallback when a measured gutter lives only in `deviceGeometry.note`
  (`pattern-note`), never overriding structured keys.
- Chrome measurements: `navbar/footer.measured.contentMaxWidth`, `linkGap`,
  `footer.measured.grid.columnGap/rowGap`.
- The brand's own authored spacing scale mined from `evidence/css-rules.json`
  (`--…spacing…` custom properties, 4–160px) — the "sanctioned set" that separates
  `wrong-step` from `off-ladder`.

## Verification

- `./venv/bin/python -m pytest brand_pipeline/tests -q` → **669 passed**
  (was 621 before this work; +48 from `test_spacing_audit.py`; no failures).
- Full audit run 2026-07-10 over `compose`, `compose/replica`,
  `compose/event-genlaunch`, `compose/stress-playbook`, `components-preview`
  (HTML mtimes 2026-07-10 15:46–15:47 recorded in the report).
- Control (replica): 122/129 conform, 0 drift, 2 hard fails, 5 unmapped. Both hard
  fails were verified at the DOM/CSS-rule level as real composer mechanics (see
  report + final diagnosis), not auditor or fact errors:
  1. `.cs-split-body .c-header` re-adds the flex `gap: var(--c-eyebrow-gap)` on top of
     the ladder owl margin `.c-header > * + *` → eyebrow→heading renders 24px (2x the
     12px rung) in split-body scopes.
  2. Equalized-card grids pin the action row with `margin-top: auto` with no minimum
     seam → on the tallest-content card the body text sits 0px from the CTA
     (`body-to-cta` rung is 32px).
- `components-preview` (spec book) contains no composed `cs-surface` sections; the
  auditor records an explicit whole-lane skip note rather than fabricating
  measurements. Auditing the spec book's own internal layout is out of scope for the
  composed-page contract.

## Known follow-up work (phase 2+, not done here)

- Composer fixes for the two control-lane mechanics above (they reproduce on every
  lane that uses those scaffolds).
- Stress-playbook render drift listed in the report's top offenders (compare-band
  container 1360px vs 1216 law, flush 0px compare split, 48px chapter-grid gutter vs
  32px fact, accordion lead-column rows on 32px vs 64px rung, interlock foot on 64px
  vs 48px rung, `cs-split-intro` missing the heading→body ladder margin).
- Extraction gaps (unmapped): form rhythm (field gap / label→input / stack), logo
  strip inter-mark gap fact for the partner-logos band, quote-card mark→quote +
  body→author rungs, FAQ/agenda list item gap + inset, body→meta caption rung.
- Multi-tier audit (modeLadder tiers), motion-state audit, and gate wiring
  (`--strict`) once the composer fixes land.
