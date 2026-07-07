# changes.md — token-layer implementation batch (2026-07-03)

Running log, repo convention. No commits; working tree only.

## Source changes (brand_pipeline/)

- `tokens_css.py` **NEW** — layer-1 generator + resolvers (migrated from
  render_section: `color_value`, `type_role`, `spacing_value`, `base_size`, `css_len`,
  `font_stack`), `build_page_tokens()` (style tag + manifest w/ brand-yaml sha,
  style-md sha, token index), `write_manifest()`, `TokenGenerationError` fail-loud on
  missing REQUIRED tokens; aspectPalette optional.
- `token_provenance.py` **NEW** — `check_token_provenance()`: scans emitted style blocks
  minus `<style id="tokens">`; errors (color/spacing/radius/type) vs warnings
  (duration/easing); `provenance: structural` declaration allowlist +
  `provenance: preview-chrome` whole-block suppression; nearest-token suggestion +
  foreign-brand callout; var-ref masking (pure refs blanked, fallbacks unwrapped and
  checked).
- `onbrand_check.py` — token_provenance wired as the `token-provenance` check
  (advisory default / HARD under `--composition`); `extract_facts` loads
  `tokens.manifest.json` (None ⇒ legacy skip); regeneration hint retargeted
  render_section → compose_section.
- `component_render.py` — `_color_ref`/`_font_ref`/`_size_ref`/`_tier_ref` helpers;
  `component_vars(surface_role=…)` alias emission as var-refs (colors, type tiers incl.
  case/tracking, buttons, inputs, logo); `_MOTION_DEFAULTS` deleted (motion tokens
  REQUIRED); `input_shape()`/`cta_shape()` structural flags; `.c-button` +
  `.c-field--boxed` extracted from COMPONENT_CSS into `_BUTTON_VARIANT_CSS` /
  `_BOXED_FIELD_VARIANT_CSS`, emitted via **`structural_variant_css(doc,
  include_all=False)`** so no-button/underline brands ship no dormant variant grammar
  (was tripping neverDo no-radius/no-shadows/no-boxed-inputs on regenerated pages);
  hover = measured bg swap; structural allowlist comments on shape-not-magnitude em
  paddings.
- `compose_section.py` — tokens block injection in `build_document`; `root_vars`
  var-ification (legacy gate literals retained); ghost ladder → calc-of-var; panel
  fallback strips; baseline fallback strips; mobile recrop allowlists (split 4/3,
  interlock 3/2 — latter added this session); interlock base aspect fallback stripped
  (`var(--c-aspect-landscape)` bare, this session); `+ cr.structural_variant_css(doc)`
  in css assembly (this session); manifest write in `main`.
- `compose_page.py` — tokens bundle + manifest; `legacy_root_vars` alias var-refs;
  `cr.structural_variant_css(doc)` in `css_parts` (this session); structural comments
  on grid/baseline.
- `compose_from_composition.py` — `tokens_css.write_manifest` after render.
- `render_components_preview.py` — tokens block + per-surface alias blocks
  (`component_alias_css`), `_bind_gallery_ctx`, preview-chrome banner, RP-1 accent fix,
  `structural_variant_css(doc, include_all=True)` (this session; gallery keeps labeled
  specimens for all variants), brand.example specimen URL.
- `export_kit.py` — `build_tokens_css` wraps `tokens_css.emit_layer1` (+ font-faces,
  hosted/missing/disabled notes).
- `styles.py` — docstring: render_section retirement + style-numeric discipline note.
- `render_section.py` → **moved** `legacy/render_section.py`; `legacy/README.md` NEW.
- `spec/anti-ai-slop.md` — **AS-24** brand-DNA-leak entry.
- `tokens_drift.py` **NEW** — standalone non-blocking staleness report (SPEC §F);
  signals.log INFO line; exit 0 always.
- `tests/test_tokens_css.py` **NEW**, `tests/test_token_provenance.py` **NEW**,
  `tests/test_structural_variants.py` **NEW** (this session: boxed-variant test moved to
  conditional `structural_variant_css`, + empty-for-underline-brand, gallery-mode, and
  filled-brand emission tests). Suite: **108/108 OK**.

## Experiment-tool changes (comparison artifacts, not pipeline)

- `experiments/woodwave-hero-gallery/build_anchored_variants.py` — comparison shim
  marked `provenance: preview-chrome` (divider strip is gallery furniture; its raw 4rem
  was flagged as a HubSpot value by the new gate — correct catch).
- `experiments/woodwave-showcase/build_showcase.py` — divider-label shim marked
  `provenance: preview-chrome` (same convention).

## Artifacts regenerated (live pipeline only)

- compose CLI: full-editorial-luxury, full-radical-editorial, full-layout-patterns-v1,
  full-layout-patterns-v2, full-layout-patterns-v2-luxury (+ tokens.manifest.json each)
- tools/build_blessed_monument.py: full-wildcard-centered-monument
- compose_from_composition replays: woodwave-hybrid run-1..5, smoke/render, showcase,
  ablation arm-on/arm-off (editorial-luxury), arm-control (corporate-saas-clean)
- gen_arm_a.py: woodwave-ab/arm-a-structured
- build_anchored_variants.py --assemble-only: page-anchored + standalone-gates (6/6 PASS)
- build_showcase.py patterns: 4/4 pages gate-green
- parity shots: experiments/token-layer-impl/parity/{before,after} + pixel diffs
  (details identical; full pages ≤0.0399% subpixel AA jitter, max delta 5/255)

## Verification commands

- `./venv/bin/python -m unittest discover brand_pipeline/tests` → 108 OK
- `./venv/bin/python tools/phase0_regate.py` → 17/18 PASS, zero PASS→FAIL,
  page-anchored FAIL→FAIL pre-existing (single-accent; provenance clean after shim marker)
- `./venv/bin/python experiments/token-layer-impl/scan_worklist.py` → 0 errors / 0 warnings
- `./venv/bin/python brand_pipeline/tokens_drift.py woodwave` → 16 fresh / 10 stale
  (pre-batch variants/ mirrors, expected) / 1 unstamped; exit 0
- Studio: restarted via start-studio.sh (was down at close), HTTP 200 on :1500

## Incidents

- 05:07 self-inflicted false alarm: a zsh `set -- $spec` loop passed unsplit args,
  creating junk `compose/"<name> <style> <order>"` dirs while the gate read the REAL
  (stale, pre-variant-fix) dirs — looked like a foreign `.c-button` write. Diagnosed via
  live-module import check (COMPONENT_CSS clean) + compose dir listing; junk dirs
  removed, real dirs regenerated explicitly.
- Conflict protocol: zero foreign modifications on owned files across the batch
  (taste_sync.py / generate_composition.py byte-identical to 03:02 baseline at close).

## Known follow-ups

- HubSpot regeneration + provenance run after the external worker exits (fence).
- Fold tokens_drift into taste_sync once that file is free.
- CS-4 collage/split media spans + hoverColor() @media recursion + knob-vs-stance lint —
  other batches' items (inventory in alignment REPORT).
