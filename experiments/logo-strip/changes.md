# Logo-strip device — changes (2026-07-03)

Working-tree only; NO commits/pushes. Sole writer of `brand_pipeline/**` during this task.

## Code edits

- `brand_pipeline/compose_from_composition.py`
  - NEW `_logo_item_mapping(item)`: per-entry evidence routing for logo-wall entries
    (AS-33). Disk-backed src (`assets/…`, i.e. it survived `_sanitize_assets`) →
    `slot="logo-strip"`, `contract="logo"` image entry with metadata-derived alt
    (alt/label → filename stem fallback); metadata-without-file → uppercase text
    caption; neither → mapped to nothing.
  - Generic-flow branch: list-copy logo slots (`c_low.startswith("logo")`) now route
    through `_logo_item_mapping` per item (was: unconditional text captions).
  - NEW `elif c_low == "logo"` branch: single logo slots (the live-generation shape —
    one slot per mark) route through the same helper (was: fell through to
    `_slot_to_mapping` → `_inline_props` → foreign-brand wordmark leak).
  - Sections binding any logo-contract slot set `layout["_logoWall"] = True` so the
    composer stamps the resolved device.
- `brand_pipeline/compose_section.py`
  - `_inline_props` logo branch: a src-bearing usage now unwraps to IMAGE props
    (src/alt/variant — AS-30); text path unchanged.
  - `compose_generic_flow`: groups `slot="logo-strip"` entries into ONE horizontal
    `.cs-logo-strip` row (at the first entry's position); stamps
    `data-logo-device="image|text|empty"` on the section element when the layout is a
    logo wall.
  - `SCAFFOLD_FLOW_CSS`: `.cs-logo-strip` device CSS (flex row, brand block-gap
    rhythm; mark height/width caps allowlisted as structural device geometry with a
    `--c-logo-strip-h` brand-token hook).
  - NEW `logo_strip_treatment_css(style_ctx)`: single shared realization of the
    style-layer qualitative `logoStrip` flag (monochrome | reduced | plain), emitted
    from `style_density_css` so both override twins inherit it (AS-06).
- `brand_pipeline/styles.py`
  - `StyleStructure.logo_strip` field + front-matter parse of `logoStrip:` (enum
    monochrome/reduced/plain; absent → "" = silent/plain).
- `brand_pipeline/onbrand_check.py`
  - NEW `_check_logo_wall(html, facts)` + composition-invariant row
    `logo-wall-integrity` (G14, AS-33): image device needs ≥1 `.c-logo-img` with
    non-empty on-disk src (cross-ref `facts["missing_imgs"]`) and non-empty alt; text
    device needs ≥1 non-empty caption; `empty` stamp always fails; vacuous pass on
    pages without stamped logo walls.
- `brand_pipeline/contracts/blocks.yaml`
  - `logo-bar` block: added `logo-strip` alias, `variants: [image-strip,
    text-captions]`, and the evidence rule as catalog prose.
- `brand_pipeline/spec/anti-ai-slop.md`
  - NEW AS-33 "Asset-role devices keyed to filenames instead of files (logo walls)"
    in the three-part form (Rule / Why / Caught here / Verify).
- `styles/corporate-saas-clean.md` / `styles/editorial-luxury.md` /
  `styles/radical-editorial.md`
  - Identical `logoStrip:` front-matter key added after `soft_options`
    (monochrome / reduced / plain respectively) with qualitative-only prose comments.
- `brand_pipeline/tests/test_logo_strip.py` (NEW): 25 tests — adapter routing both
  shapes, sanitize→route end-to-end (filename-without-file), alt provenance,
  `_inline_props` unwrap, strip grouping + device stamps, gate rows, style-flag
  parse + treatment emission.

## Generated artifacts (additive only)

- `runs/hubspot/brand/compose/signup-launch-logostrip/` — deterministic replay of the
  fixed-live composition through the new device. Gate GREEN under `--composition`
  (hard invariants), logo wall image-backed (5 real third-party SVGs), footer logo
  image-backed (`smart-crm.svg`).
- `runs/hubspot/brand/compose/signup-launch-logostrip-live/` — fresh LIVE seeded run
  (same verbatim directive as `run_live_fixed.py`). ok=true, attempts=2, gate GREEN,
  logo wall image-backed with metadata alts.
- `experiments/logo-strip/`: `run_live_logostrip.py`, `live-results.json`,
  `input-hashes.txt` (open snapshot), `close-hashes.txt` (close snapshot),
  `shots/` (before/after logo-section + full-page), `REPORT.md`, this file.

## Verification

- Unit suite: `./venv/bin/python -m unittest discover -s brand_pipeline/tests -t .`
  → 159/159 OK (134 baseline + 25 new).
- `./venv/bin/python tools/phase0_regate.py` → zero PASS→FAIL; `page-anchored`
  FAIL→FAIL pre-existing, unchanged.
- WoodWave parity: smoke + run-1 compositions re-rendered → DOM byte-identical;
  only delta is the additive `.cs-logo-strip*` CSS (selectors match nothing on those
  pages). No WoodWave composition carries a non-hero logo-wall slot.
- Studio :1500 → HTTP 200; both new lanes browsable under
  `/runs/hubspot/brand/compose/`.
- Viewer regeneration: N/A (no change to `viewer.html` / `run_pipeline.py` — this
  task touched `brand_pipeline/**` only).

## Known follow-ups

- WoodWave extraction captured no third-party logo assets; if a WoodWave brief ever
  demands a logo wall it will render the text-caption device (correct per AS-33).
  Logo extraction for brands without tagged logo assets remains a separate task.
- `--c-logo-strip-h` chrome token: no brand currently measures a logo-strip mark
  height; the structural default (2.25rem) governs until an extractor captures one.
