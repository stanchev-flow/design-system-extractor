# Logo-strip device — REPORT (2026-07-03)

**Mandate (verbatim):** "we need either logo from the extracted brand or if not
extracted show at least text." Never emit broken or invented image references.

## 1. Asset reality

- **HubSpot** (`runs/hubspot/brand/assets/` + `assets-tagged.json`): real third-party
  logo files EXIST on disk — 8 tagged `logo-wall-logo` (doordash, ebay, eventbrite,
  reddit, tripadvisor, weightwatchers, youth-on-course, monday[partial]) + 6
  `integration-logo` SVG/PNGs, plus the brand's own `smart-crm.svg` mark. The image
  device is therefore provable on HubSpot with zero fabrication.
- **WoodWave** (`experiments/woodwave-ab/inputs/brand/assets/`): editorial
  photography only — NO third-party/customer logo files. Any WoodWave logo wall
  would take the text-caption fallback (none of its existing compositions carries a
  non-hero logo slot, so nothing changes today).

## 2. Device + routing

- **Catalog**: `logo-bar` block (contracts/blocks.yaml) gains alias `logo-strip` and
  declared variants `image-strip` / `text-captions` with the evidence rule spelled
  out. Generic naming throughout — nothing HubSpot-specific.
- **Routing (adapter, `_logo_item_mapping`)**: per-entry DISK EVIDENCE, both
  composition shapes (one list-copy slot / one slot per mark):
  - asset file exists on disk (src survived `_sanitize_assets` → `assets/<name>`) →
    logo-strip IMAGE entry; alt from the entry's own alt/label metadata, else the
    filename stem (AS-29 — never an invented brand literal);
  - metadata but no file (filename-without-file included) → uppercase TEXT caption
    (the declared fallback device);
  - neither → mapped to nothing. Remote http(s)/data URLs are NOT disk assets →
    text fallback, by design.
- **Composer**: image entries group into ONE horizontal `.cs-logo-strip` row; the
  section stamps `data-logo-device="image|text|empty"`. `_inline_props` now unwraps
  src-bearing logo slots into image mode (AS-30) — this kills the found leak where
  HubSpot's live page rendered FIVE "WoodWave" wordmarks on its trust wall (the
  logo contract's nav-wordmark text default; see AS-33 "Caught here").
- **Style layer (qualitative flag)**: `logoStrip: monochrome | reduced | plain` in
  the three style files (corporate-saas-clean=monochrome, editorial-luxury=reduced,
  radical-editorial=plain), parsed into `StyleStructure.logo_strip`, realized once in
  `logo_strip_treatment_css` (motion rides brand tokens; style files carry no CSS
  values; strip geometry allowlisted structural with a `--c-logo-strip-h` token hook).

## 3. Gate / registry

- **Gate**: new composition-invariant row `logo-wall-integrity` (G14) — an
  `image`-stamped section must carry ≥1 `.c-logo-img` with non-empty src that exists
  on disk (cross-referenced against the gate's own `missing_imgs` scan) and non-empty
  alt; a `text`-stamped section must carry ≥1 non-empty caption; an `empty` stamp
  always fails (empty-container discipline). Vacuous pass on pages with no logo
  walls — zero retro-fails.
- **Registry**: AS-33 "Asset-role devices keyed to filenames instead of files (logo
  walls)" added in the three-part form.

## 4. Suite + regate

- Unit suite: **159/159 OK** (baseline 134 + 25 new in
  `brand_pipeline/tests/test_logo_strip.py`).
- `tools/phase0_regate.py`: **zero PASS→FAIL** (17 PASS→PASS; `page-anchored`
  FAIL→FAIL pre-existing, unchanged).

## 5. HubSpot regeneration

- **Deterministic replay** `runs/hubspot/brand/compose/signup-launch-logostrip/`
  (fixed-live composition through the new device): gate **GREEN** under
  `--composition` (hard invariants, `logo-wall-integrity` PASS). Logo section is
  **image-backed**: 5 real marks (DoorDash, eBay, Eventbrite, Reddit, Tripadvisor)
  with metadata alts; footer mark image-backed (`smart-crm.svg`, alt "HubSpot").
- **Live seeded run** `runs/hubspot/brand/compose/signup-launch-logostrip-live/`
  (same verbatim directive as the fix batch): ok=true, attempts=2, gate **GREEN**,
  logo wall **image-backed** (same 5 marks, `data-logo-device="image"`), zero foreign
  wordmarks in content (before-page had five).
- Shots in `shots/`: `before-fixed-live-logos-section.png` (five "WoodWave" text
  wordmarks) vs `after-replay-…`/`after-live-logos-section.png` (real grayscale
  logo strip, monochrome treatment) + full-page captures.

## 6. WoodWave impact

No WoodWave composition in the regate corpus carries a logo-wall-role slot (the only
logo contract is the hero wordmark, which routes through the hero path, untouched).
Re-rendered smoke + run-1: **DOM byte-identical**; the only byte delta is the
additive `.cs-logo-strip*` CSS whose selectors match nothing on those pages. Regate
covers all 17 pages: no scorecard movement. If a future WoodWave brief demands a
logo wall it renders text captions (no extracted logo files) — correct per AS-33.

## 7. Fences / hygiene

- Pre-existing `runs/hubspot/**` files untouched (verified by hash); new dirs under
  `compose/` additive only. `experiments/hubspot-e2e|validation|fix/**` read-only,
  untouched. `runs/remote/**` + `experiments/remote-e2e/**` not read or written.
- Write scope respected: `brand_pipeline/**`, `styles/*.md` (device flag),
  `experiments/logo-strip/**`, two new additive compose dirs.
- Snapshot discipline: `input-hashes.txt` (open) vs `close-hashes.txt` (close) —
  files I did not edit (`component_render.py`, `tools/phase0_regate.py`,
  `slop_audit.mjs`) byte-identical to the open snapshot; no foreign writes detected.
- **NO commits, NO pushes** — working tree only (HEAD still `64d41c8`).
- Studio :1500 answers **200**; both new lanes visible under
  `/runs/hubspot/brand/compose/`.
