# remote-e2e — running log

Worker: Remote-brand end-to-end (third brand). Write fence: `runs/remote/**`,
`experiments/remote-e2e/**` only. No git operations. No `brand_pipeline/**`,
`styles/**`, `tools/**` edits.

## Inputs (read-only, `screenshots/remote/`)

- HTML: `Remote — Global Employment Infrastructure _ EOR, Payroll & Compliance, Worldwide.html` (2.1MB)
- Assets dir: `…_files/` (144 files, incl. 22 CSS)
- Ground-truth screenshot: `Remote-—-…-07-01-2026_09_35_PM copy.webp`
- Input hashes: `input-hashes.txt` (this folder)

## Log

- 2026-07-03 16:20 — Read HANDOFF-2026-07-02.md, runs/hubspot/brand/REPORT.md,
  experiments/token-layer-design/SPEC.md, experiments/hubspot-fix/REPORT.md +
  DECISIONS.md. Confirmed `experiments/logo-strip/REPORT.md` does NOT exist yet
  (only input-hashes.txt + shots/) → phase-2 safety gate not yet satisfied via
  route A; will check `find brand_pipeline -mmin -10` before any pipeline run.
- 2026-07-03 16:22 — Created experiments/remote-e2e/, snapshotted input hashes.

## Phase 1 complete — brand folder authored (2026-07-03T17:28)

- `runs/remote/brand/brand.yaml` — full schema: 50 color tokens (incl. canonical aliases),
  flat type roles w/ ladders (Bossa->Lexend Deca proxy, Inter), spacing (12 keys), radius
  (5 tiers), shadow (hover-only), aspectPalette, 7 surfaces, heroTreatment (noise panel),
  surfaceGrammar (all-light rhythm), buttons (primary/secondary/tertiary/textCta with full
  measured state matrices), primitives/blocks, 12 layouts, 9 compositionRules, do/avoid/
  neverDo, motionSpec (measured: ease 300/500/1000ms, color-shift links, marquee, no
  reduced-motion declared), navbar+footer chrome with measured blocks + 6 real columns.
- tokens_css build_page_tokens: **BUILD OK, missing == []** (6930 chars CSS).
  disabledDevices: counter-display, ghost-watermark, footer-display-links (footer grammar
  -> columns). surface/hero-noise bg fixed to sampled art average #dae2e8.
- `assets-tagged.json/md` — 44 assets: 12 logo-wall-logo SVGs + 1 wordmark + 4
  integration-logo + 6 award-badge + 3 rating-badge + 4 avatars + 6 feature-icon +
  1 hero-illustration + 1 background-art + 6 product-graphic.
- `layout-library.yaml` — 7 extracted patterns (hero-inset-noise-panel, logo-marquee-strip,
  feature-accordion-deep-accent, features-card-grid-navy-media, cta-inline-banner,
  cta-closing-noise, testimonial-card-row).
- `brand.md`, `voice.md`, `signals.log` (4 signals incl. the light-footer/inverse-strong
  schema-gap defer).

## Phase-2 safety gate — SAFE at 2026-07-03T17:28:29

- experiments/logo-strip/REPORT.md: does NOT exist
- brand_pipeline/ files modified in last 10 min: **0** -> quiet-window condition MET
- Proceeding to components preview + live generation.

## Phase-2 safety gate — DELAY at 2026-07-03T17:37:50

- Pre-generation re-check found `brand_pipeline/compose_from_composition.py` modified at
  17:34 (4 min ago) — the pipeline worker is ACTIVE. Holding live generation.
- Note: components-preview render at ~17:30 happened inside their edit window (no
  logo-strip REPORT.md yet at that point either; the 17:28 check showed 0 files <10min).
  Will RE-RENDER the preview after the quiet window for a clean artifact.
- Asset layout change: flattened assets/logos/*.svg -> assets/*.svg because BOTH
  generate_composition's asset inventory (brand_dir + brand_dir/assets root only) and
  compose_section.copy_assets (assets_root.glob("*")) ignore subdirectories.
  assets-tagged.json/md updated to flat filenames.
- experiments/remote-e2e/run_page.py authored (mirrors hubspot-validation runner;
  gate layout="hero"; stack/cards-only directive; logo wall bound to the 12 tagged SVGs).

## Phase-2 safety gate — GREEN at 2026-07-03T17:56:12

- `experiments/logo-strip/REPORT.md` EXISTS (worker finished) AND 0 brand_pipeline files
  modified <10min (last edits ~17:46: test_logo_strip.py, anti-ai-slop.md, onbrand_check.py).
- Delay incurred: ~18 min (17:37:50 -> 17:56:12). Used for report drafting + asset polish.
- Proceeding: re-render components preview (post-edit pipeline + flat assets), then live gen.

## Live generation

- Components preview re-rendered clean -> `runs/remote/brand/components-preview/index.html`
  (preview tier has known cosmetic defects — WoodWave-flavored captions/placeholder assets and
  a `KeyError: 'panelTitle'` on custom layout ids in the split archetype — logged as BLOCKERS,
  live path unaffected).
- gen1 (`gen1.log`): model composed 7 sections; gate FAIL with 7 findings — logo wall empty
  (bare-string copy items vs `_logo_item_mapping`'s alt/asset dicts), off-palette #dae2e8,
  token-provenance 6.25rem scaffold fallback untraceable (+ foreign-brand match on it),
  alignment-resolution (left anchors w/o counterweight in 3 patterns), hero surfaceIntent
  inverse vs surface/primary fidelity row, WoodWave placeholder leaks via non-layered hero +
  testimonial-cards fallbacks, model-composed duplicate footer.
- Fixes (all inside my fence): brand.yaml + `surface/art-pastel` color token + `badge-tier`
  6.25rem spacing token (measured: .iconBox.badge height:100px, .remote-logo max-width:100px);
  layout-library.yaml counterweights (media/cards) on the 3 left-anchored patterns;
  run_page.py directive pinned hero surfaceIntent=primary, layered hero media (colSpan 6,
  z:front), logo copy as {alt,asset} objects, testimonial stack + contract slot, no
  model-composed footer beyond the arrow-link stack.
- gen2 (`gen2.log`): **PASS in 1 attempt, 88.3s** -> `runs/remote/brand/compose/signup-launch/`.
  Scorecard: neverDo PASS, fidelity PASS, slop PASS, invariants all PASS incl. token-provenance
  (0 errors, 7 allowlisted structural) and logo-wall-integrity (12 disk-backed logos).
- Three-way foreign-brand check verified standalone: foreign indexes loaded = HubSpot (213
  tokens) + WoodWave Gallery (124 tokens); **0 foreign-brand callouts** against the Remote render.

## Shots + Studio (2026-07-03 ~18:3x)

- Shots: `gen-full.png` / `gen-hero.png` / `gen-footer.png` + `gen-band-*.png` slices +
  `side-by-side.png` / `side-by-side-top.png` vs the ground-truth webp. NOTE: full-page
  screenshots need `reduced_motion='reduce'` (or a scroll pass) — the page's
  IntersectionObserver reveal keeps below-fold sections at opacity 0 otherwise.
- Studio: `:1500` answers 200 (studio_server.py pid 76615). Remote lane appears in
  /api/projects; wrote `runs/remote/studio-project.json` (mirrors the HubSpot precedent) ->
  lane now shows title "Remote", url, created, thumb from the ground-truth screenshot,
  pipeline_status "building" (same status tier as the HubSpot lane).
- REPORT.md written.
