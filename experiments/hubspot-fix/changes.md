# hubspot-fix batch — running log (2026-07-03)

Worker: fix-batch (sole writer on `brand_pipeline/**`, `styles/**`, `tools/**`).
No commits/pushes — working-tree only. Fences respected: `runs/hubspot/**` pre-existing
files read-only (additive under `runs/hubspot/brand/compose/`), `experiments/hubspot-e2e/**`
+ `experiments/hubspot-validation/**` read-only.

## Snapshot / conflict protocol

- `input-hashes.txt` — sha256+mtime of every file to be edited, recorded at batch start.
- Re-checked after source edits: changed set == exactly my own edit set; zero foreign
  writes. `tools/phase0_regate.py` untouched.

## Source edits (brand_pipeline/**, styles/**)

- `tokens_css.py` — `_pick_scale_entry`: EXACT tier-name match (e.g. `display-hero`)
  is authoritative before family-keyword heuristics (AS-32 / B11). Bare-family
  keywords (`body`, `display`) keep the lead-register heuristic.
- `styles.py` — `StyleStructure.display_source` (`poster`|`brand`, parsed from the
  `type:` front-matter block, default `poster`) + `StyleStructure.primary_action`
  (parsed from the `primary-action` soft-option default: `*button*`→`filled`,
  `*link*`→`typographic`).
- `styles/corporate-saas-clean.md` — `display_source: brand` + `primary-action`
  soft option (default `filled-button`); prose updated (brand-owned display
  magnitude; filled primary grammar). Structure kept identical to the other two.
- `styles/editorial-luxury.md` — explicit `display_source: poster` (existing
  `primary-action: pill-button` soft option already present).
- `styles/radical-editorial.md` — explicit `display_source: poster` +
  `primary-action` soft option (default `ghost-link`); prose note.
- `compose_page.py` — `page_display_size()` (brand tier when the active style declares
  `display_source: brand`, else the style poster clamp; brand tier when unstyled);
  `page_style_override(..., poster=...)`; `footer_content()` derives the sitemap
  nav-set from the brand's own `navbar.primary`+CTA labels (WoodWave tuple no longer
  hardcoded) and passes `footer.columns` through for columns-grammar brands;
  `compose_section_block` resolves `ctx.cta` style-aware.
- `component_render.py` — `ComponentContext.cta`; `cta_shape(doc, style=None)`
  (law > style primaryAction > measured buttons > typographic); `render_button`
  dispatches on the resolved shape (typographic ⇒ arrow link); `render_input` submit
  rides the same dispatch; footer sitemap CSS moved out of `COMPONENT_CSS` into
  per-grammar constants (`_FOOT_DISPLAY_LINKS_CSS` / `_FOOT_COLUMNS_CSS`) selected by
  `footer_grammar(doc)`; `render_footer` renders sitemap vs columns per grammar;
  `component_vars` emits `--c-input-radius/-border/-bg` (boxed inputs),
  `--c-body-weight`, and `--c-foot-link-size/-weight` (columns grammar);
  `.c-paragraph` consumes `--c-body-weight`.
- `compose_section.py` — overlay `var(--c-display-size, 5rem)` fallbacks removed ×3
  (AS-24; alias always emitted per section); conversion stack renders bound `button`
  contracts as a `.cs-conversion-actions` row (form only when a form slot is bound or
  no explicit actions exist — legacy path byte-identical); gallery showcase renders
  real action slots (primary via `render_button`, companions arrow links);
  `compose_features_cards` unwraps `{src, alt}` asset dicts + brand-derived alt text;
  `_props_for` alt literals now derive from `brand.name`; `_inline_props` handles
  `contract: button`; `compose_stack` routes button-bound stacks to the conversion
  composer; `.cs-gallery-cta` gains gap/align for multi-action rows.
- `compose_from_composition.py` — `_cta_mapping(section)` slot-faithful (buttons
  preserved; form only when bound or legacy-default); `_cta_copy` reads the header
  block's `text` as body fallback; `_gallery_copy` surfaces `actions` from button
  slots; `_cards_copy` unwraps sanitized asset dicts to src/alt strings; stack routing
  by evidence (conversion useCase / form slot / button slots ⇒ conversion; other
  non-hero stacks ⇒ generic-flow); generic-flow mapping normalizes logo walls →
  captions, link lists → link entries, testimonial/quote → paragraph+attribution
  caption, label → caption, subheading → paragraph.
- `onbrand_check.py` — facts: `css_vars` (full custom-property map, last-wins) +
  `content_attr_texts` (alt/aria-label/title); `_resolve_css_var_chain()` resolves
  radius aliases through the page's own declarations before the radius-scale check
  judges them (AS-31); new slop row `No foreign-brand content literals
  (alt/aria/title)` against the `runs/*/brand` corpus (AS-29); style Rule 1 is
  display_source-aware (`_display_rides_brand_tier` for `brand`-sourced styles).
- `brand_pipeline/spec/anti-ai-slop.md` — registry entries **AS-26 … AS-32**.

## Tests

- `tests/test_fix_batch.py` (new, 24 tests): radius var-chain resolver (6), footer
  grammar (4), style-aware cta shape + dispatch (4), exact-role picker (2),
  display_source (2), adapter slot-faithfulness (5, incl. dict-src unwrap), foreign
  brand content (2). (Counts approximate per class listing.)
- `tests/test_structural_variants.py` — variant-layer test updated: the footer grammar
  is now part of the variant layer (exactly one grammar per brand; gallery mode
  carries both). Documented intended test change.
- Suite: **132/132 OK** (baseline 108 + 24 new).

## Late edits (post-initial-suite)

- `brand_pipeline/readability.py` — `check_text_contrast(measured_pairs=...)`:
  fidelity-over-floor exemption for the brand's MEASURED buttons.* (fg,bg) pairs,
  reported inline ("exempt as MEASURED brand pairs"); non-measured pairings still
  fail. Call site in `onbrand_check.py` builds the pairs from brand.yaml. NOTE:
  readability.py was not in the batch-start snapshot list (added to the owned edit
  set here). Registry note appended to AS-27. Tests: `MeasuredPairContrastExemption`.
- Suite after late edits: **134/134 OK**.

## Artifacts regenerated (live pipeline only)

- compose CLI: full-editorial-luxury, full-radical-editorial, full-layout-patterns-v1
  (order v1), full-layout-patterns-v2, full-layout-patterns-v2-luxury (order v2)
- tools/build_blessed_monument.py: full-wildcard-centered-monument
- compose_from_composition replays: woodwave-hybrid run-1..5, smoke/render, showcase,
  ablation arm-on / arm-off (editorial-luxury), arm-control (corporate-saas-clean)
- gen_arm_a.py: woodwave-ab/arm-a-structured
- build_anchored_variants.py --assemble-only: page-anchored + standalone-gates 6/6 PASS
- build_showcase.py patterns: 4/4 gate-green
- HubSpot (additive under runs/hubspot/brand/compose/):
  - `signup-launch-fixed/` — deterministic replay of the RED run's persisted
    composition.json → gate `--composition` **OVERALL: PASS**
  - `signup-launch-fixed-live/` — live seeded rerun (run_live_fixed.py, same args as
    run_validation.py) → **ok=true, attempts=1**, 84.5s, scorecard PASS
    (live-results.json, live-run.log)

## Verification commands

- `./venv/bin/python -m unittest discover -s brand_pipeline/tests -t .` → 134 OK
- `./venv/bin/python tools/phase0_regate.py` → 17/18 PASS, zero PASS→FAIL (run before
  AND after the matrix re-render; page-anchored FAIL→FAIL pre-existing single-accent)
- parity: tools/shoot_alignment_fix.mjs ×10 pages before/after + PIL pixel diff →
  hybrid-run-1 0.0000%; non-intended pages ≤0.0385% (ALL of it the documented nav
  register row); intended diffs: showcase (forms→flow, +282px), arm-control
  (brand-tier display, −524px)
- HubSpot gate: `onbrand_check.py runs/hubspot/brand/brand.yaml
  runs/hubspot/brand/compose/signup-launch-fixed --layout footer
  --style corporate-saas-clean --composition` → OVERALL: PASS
- Studio: :1500 → 200; lanes "Composed: signup-launch-fixed(-live)" present;
  page serves 200 via studio route

## Incidents

- Playwright browsers path: sandbox cache path empty → shots run with
  `PLAYWRIGHT_BROWSERS_PATH=$HOME/Library/Caches/ms-playwright` (no repo impact).
- Parity investigation: the ≤0.0385% full-page residue traced to the nav links row —
  the token batch's parked `--c-nav-size` measured-register single-sourcing
  materializing on re-render (their session authored it; see REPORT intended diff (c),
  `shots/nav-stack.png`). Not a fix-batch change; kept + documented.
- Zero foreign writes across the batch (snapshot re-checks mid-batch + at close);
  hubspot brand.yaml sha 96d08de4… intact.
