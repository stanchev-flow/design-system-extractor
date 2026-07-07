# remote-fix batch — changes.md (2026-07-03)

Working-tree only; no git operations. Sole writer on `brand_pipeline/**`, `styles/**`,
`tools/**` (fence snapshots: `fence-snapshot-start.txt` / `fence-snapshot-close.txt` —
10 changed files, all this batch's own edits; zero foreign writes).

## Source edits (pipeline)

- `brand_pipeline/compose_section.py`
  - `brand_image_inventory` (recursive asset scan) + `attach_asset_inventory` (doc-attached,
    in-memory) + `brand_default_art` / `_brand_art` evidence-checked default-art resolution
    (AS-34; blockers 2/6).
  - `copy_assets` recursive globbing incl. subdirectories, preserving relative paths
    (blocker 6); `find_font_source`, `brand_self_hosted_fonts`, `self_hosted_families`,
    `copy_fonts`, `font_face_css` generalized to the brand.yaml `selfHostedFonts` registry
    (schema-gap 8; WoodWave Melodrama module default preserved as fallback).
  - `_LAYER_FALLBACK` / `_OVERLAY_FALLBACKS` / `_props_for` / `_ov_media_html` / collage +
    timeline composers: WoodWave literal srcs demoted to preferences resolved through
    `_brand_art`; alt text derived from role (blocker 2).
  - `_SafeCopy` + `copy_for` returning it (blocker 7 crash: `KeyError: 'panelTitle'`).
  - hero CTA law-first: `compose_stack_hero` consumes bound `button` slots via
    `render_button` in a `.cs-hero-actions` wrap (AS-27 hero extension; blocker 3);
    `compose_stack` routing prefers the hero useCase for compositions.
  - scaffold literal `var()` fallbacks stripped for provenance-scanned spacing props
    (`6.25rem`/`2.5rem`/`1.75rem`/`6rem` family; AS-24, blocker 4); `rhythm_vars_css`
    emits structural `--c-section-pad-x` / `--c-nav-pad-block`.
  - inset art-panel device (schema-gap 9, AS-37): `_art_panel_permitted` (brand neverDo
    no-radius/no-gradients + style `artPanel` gating), `_hero_treatment_art`,
    `_stack_hero_art_panel` composer variant, `SCAFFOLD_ART_PANEL_CSS` split OUT of
    `SCAFFOLD_HERO_CSS` and emitted only when `layout._artPanel` is present (regate had
    flagged the unconditional rule as a WoodWave `neverDo no-radius` PASS→FAIL).
- `brand_pipeline/compose_from_composition.py`
  - `_logo_item_mapping` accepts bare-string items (disk-evidence coercion in
    `_sanitize_assets`, caption fallback otherwise; blocker 1); raw-list iteration for
    logo walls.
  - `_hero_mapping` slot-faithful media (no WoodWave placeholder injection; blocker 2)
    + bound-button pass-through (blocker 3) + `art_panel` awareness.
  - `_ART_PANEL_KINDS` / `_is_art_panel_bg_slot` / `_art_panel_payload`; split-hero-with-
    panel routes to the stack-hero panel variant (`is_hero` extension, `_artPanel` flag).
  - `_valid_asset_names` uses the recursive inventory; `composition_to_doc` attaches it.
- `brand_pipeline/compose_page.py`
  - `FOOTER_SURFACE` → `FOOTER_SURFACE_DEFAULT` + `_parse_color_rgb` +
    `footer_surface_role` measured-chrome resolution (blockers 5/10, AS-35).
  - conditional `SCAFFOLD_ART_PANEL_CSS` emission in `build_page` (AS-37).
  - `load_doc` attaches the asset inventory.
- `brand_pipeline/onbrand_check.py`
  - `_brand_asset_corpus` + slop row "No foreign-brand asset references" (AS-34 gate).
- `brand_pipeline/render_components_preview.py`
  - crash fix + `_specimen` / `_brand_law` brand-derived preview copy/captions; `main()`
    attaches the active brand's asset inventory (blocker 7, AS-36).
- `brand_pipeline/styles.py` — `StyleStructure.art_panel` + `artPanel` front-matter parse.
- `styles/corporate-saas-clean.md` — `artPanel: inset`; `styles/editorial-luxury.md`,
  `styles/radical-editorial.md` — `artPanel: none` (identical structure, qualitative).
- `brand_pipeline/spec/anti-ai-slop.md` — new entries AS-34, AS-35, AS-36, AS-37.
- `brand_pipeline/tests/test_remote_fix.py` — NEW, 28 tests across all 10 items.

## brand.yaml ADDITIONS (documented; no measured value altered)

- `runs/remote/brand/brand.yaml` — appended `selfHostedFonts:` block registering Bossa
  (weight 400, `Bossa-Regular.woff2/.woff`). Files are NOT in the capture (commercial
  face) → no `@font-face` emitted; type stack falls through to the measured renderProxy
  (Lexend Deca). Follow-up documented in the block comment.
- `runs/woodwave/brand/brand.yaml` — appended `selfHostedFonts:` block mirroring the
  module's Melodrama registry (parity proof: renders byte-equal through either path).

## Regenerated pipeline-owned outputs (live pipeline, prior batches' commands)

- compose CLI: `runs/woodwave/brand/compose/{full-editorial-luxury, full-radical-editorial,
  full-layout-patterns-v1}` (order v1) and `{full-layout-patterns-v2,
  full-layout-patterns-v2-luxury}` (order v2), styles as before.
- `tools/build_blessed_monument.py`: `full-wildcard-centered-monument`.
- NEW additive compose dirs:
  - `runs/remote/brand/compose/signup-launch-fixed/` — `run_live_remote.py` (this dir),
    live seeded generation, gate PASS under `--composition` (attempts=3).
  - `runs/hubspot/brand/compose/signup-launch-remotefix-live/` — `run_live_hubspot.py`
    (verbatim hubspot-fix directive), gate PASS (attempts=2), logo wall image-backed.
- `experiments/remote-fix/preview-remote/` — Remote components preview (blocker-7 proof;
  no crash, brand-derived copy).

## Verification commands

- `./venv/bin/python -m unittest discover -s brand_pipeline/tests -t . -q` → 187 OK
  (159 baseline + 28 new).
- `./venv/bin/python tools/phase0_regate.py` → zero PASS→FAIL (page-anchored FAIL→FAIL
  pre-existing).
- WoodWave parity: `/tmp/ww-before` snapshot vs regenerated matrix — DOM byte-identical;
  CSS diffs are exactly the documented mechanics (fallback strip, structural vars,
  conditional device CSS, tokens-banner sha from the additive brand.yaml block); pixel
  diff 0.0000% on 11 before/after shots (`parity/`, `shoot_parity.py`).
- Studio `:1500` → HTTP 200; `/api/projects` lists remote + hubspot + woodwave lanes.

## Artifacts in this dir

- `REPORT.md` (fix-by-fix disposition) · `DECISIONS-NEEDED.md` · `changes.md` (this file)
- `run_live_remote.py` / `remote-live-results.json` · `run_live_hubspot.py` /
  `hubspot-live-results.json`
- `shoot_parity.py` + `parity/{before,after}/` (11 pairs, pixel-identical)
- `shoot_remote.py` + `shots/` (remote before/after full/hero/footer; hubspot after)
- `preview-remote/` · `fence-snapshot-start.txt` / `fence-snapshot-close.txt`
