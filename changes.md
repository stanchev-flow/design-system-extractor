# Changes

## 2026-05-08

- Moved local API-key loading to repo-local `.env.local`, added `.env.example`, ignored `.env` / `.env.*` secrets, and removed hard-coded references to the previous personal env-file path.
- Rewrote `README.md` with current project goals, opportunity framing, high-level challenges, current pipeline mechanics, grounding/schema/surface-contract learnings, generated asset flow, and repo-local key setup.
- Made GPT-5.5/high the baked-in default for analysis and section detection, persisted resolved model settings into each version folder, and stopped analysis overrides from implicitly changing section detection.
- Kept new run defaults generating both Claude Opus 4.6 and GPT-5.5 final sites while preserving GPT-5.5/high for analysis and section detection.
- Added regression coverage for runtime model defaults and section-detection override isolation.
- Ran full pipeline version `v173` with the same screenshot/HTML inputs and `no-assets-config.yaml` used by `v171`; all five sites completed and `viewer.html` was regenerated.
- Added a `runs/v173` section-grounding prompt override with closed primitive `kind` typing and kind-specific role fields so the run exercises the surface/component contract strategy without mutating older run prompts.
- Fixed concurrent `run-steps.json` updates by serializing status writes and replacing files atomically, preventing malformed or stale step-status output during parallel provider work.
- Validated `runs/v173` artifacts: five manifest items, parseable status/audit JSON, generated contract/map/input artifacts, and complete Claude/GPT-5.5 final HTML for every site.
- Verified with `./venv/bin/python -m py_compile run_pipeline.py src/screenshot_to_template/cli.py src/screenshot_to_template/config.py src/screenshot_to_template/output.py src/screenshot_to_template/pipeline/sectioned.py src/screenshot_to_template/prompts.py src/screenshot_to_template/surface_contract.py src/screenshot_to_template/tracking.py tests/test_surface_contract.py` and `./venv/bin/python -m unittest discover -s tests`.
- Added `--assets-only`, `--site-assets`, and `--no-site-assets` pipeline controls so generated image assets can be backfilled for an existing run and config-level asset settings can be explicitly overridden.
- Fixed generated-site asset replacement so completed local assets do not keep active `data-stt-asset-brief` markers and resumed backfills do not overwrite existing `asset-*.png` files.
- Backfilled `runs/v173` generated site assets after diagnosing that the inherited `runs/v171/no-assets-config.yaml` disabled image generation; generated 132 PNG assets across the five sites and regenerated `viewer.html`.
- Added source section-crop reference support for generated graphics, illustrations, diagrams, interfaces, icons, and badges: asset generation now picks a source crop with matching illustration/graphic/interface style and sends it as an image reference while keeping photographic/background assets text-only.
- Strengthened referenced graphic prompts to preserve the requested aspect ratio, keep the whole artwork safely inside the canvas, and avoid cropped edges so chroma-key transparency removal still works.
- Created `runs/v174` from v172 prompts for a Petspan and Monologue validation run with generated assets enabled.
- Changed design-system artifact writing so pure `design_system_yaml.v1` outputs are saved as `design-system.md` with YAML front matter plus categorized Markdown body sections, preserving the nested YAML surface/component data while restoring the v078-style readable structure.
- Added regression tests for hybrid design-system artifact writing and stale `design-system.yaml` cleanup.
- Created `runs/v175` to compare the hybrid Markdown design-system structure against v174's pure YAML baseline on the same Petspan and Monologue inputs; reused v174 grounding and surface maps where provider calls stalled, regenerated Claude/GPT-5.5 sites, backfilled generated assets, and regenerated `viewer.html`.
- Corrected copied run display names for v173 and v174 so the viewer no longer shows them as duplicate v171/v172 entries.
- Fixed source font injection to resolve source CSS custom-property font stacks before writing `--stt-source-font-family`, preventing unresolved `var(...)` stacks from overriding generated pages into browser-default fonts.
- Made generated transparent logo/icon asset replacement preserve compact slot sizing (`height: 100%; width: auto`) instead of applying full-width media-well sizing to small brand/logo slots.
- Tightened site-generation input sanitization so source-subject helper metadata such as `embedded_showcase_only`, source-specific embedded UI names, and self-referential business/product/industry copy warnings are removed or generalized before website generation.
- Hardened source font extraction for captured `/vendor-assets/<host>/...` URLs, trying later `@font-face src` fallbacks when the first URL fails and injecting source font rules with `!important` so generated page CSS cannot silently override them.
- Added Google WebFont loader extraction so source fonts declared via `WebFont.load({ google: { families: [...] } })` are fetched from Google Fonts, downloaded locally, and included in generated pages.
- Preserved split typography roles for sources like Petspan by extracting the real body/base font stack separately from decorative italic emphasis stacks, then emitting a source-backed italic emphasis CSS rule for generated headings.
- Raised OpenAI section-grounding merge budgets for large assets so the first merge starts at 32k output tokens and the first retry escalates to 49k before the existing 65k final retry.
- Added optional grounding-generated sidecar site support to the viewer payload and output grid: when `site-gpt55-grounding.html` or `site-claude-grounding.html` exists for an item, selecting the Grounding tab swaps the corresponding generated-site iframe and open-in-new-tab target to that sidecar.
- Backfilled v177 GPT-5.5 grounding sidecar sites and generated image assets for Roma and Petspan, retried failed asset slots until no generated-asset placeholders remained, persisted sidecar manifest paths, and regenerated `viewer.html` plus `viewer-data/v177.js`.
- Ran a strict source HTML/CSS style post-pass on the v177 grounding sidecar sites, forcing remaining grounding-approximate fallback colors to source-backed palette values and regenerating the viewer payload.

## 2026-05-07

- Implemented `source-style-ledger.yaml` generation with selector/property evidence, generation-safe palette roles, typography role hints, excluded-value reasons, and prompt-ready ledger compaction.
- Fed the source style ledger into surface/component map and design-system synthesis, added deterministic ledger-aware design-system reconciliation with `design-system.pre-style-sync.md` and `design-system-style-audit.json`, and kept model color sync as a fallback.
- Made generated-site style sync conditional on deterministic ledger repair, saving `site-*.pre-style-sync.html`, `site-*-style-audit.before.json`, and `site-*-style-audit.after.json` for provider outputs.
- Added viewer tabs and manifest fields for source-style ledgers and design-system style audits.
- Added unit coverage for source-style ledger construction and close-match color reconciliation; verified the suite with `./venv/bin/python -m unittest discover -s tests -v`.
- Disabled review model calls by default in `run_pipeline.py` and `config.default.yaml`; full-page, surface-map, design-system, and conversion reviews now require `--run-reviews` or `run-reviews: true`.
- Added `source-style-ledger-plan.md` as an implementation handoff for a YAML source-style ledger, post-design-system style reconciliation, and conditional site-style sync optimization.
- Expanded `source-style-ledger-plan.md` with a loophole matrix covering raw CSS noise, malformed variable colors, role mismatch, selector unreliability, cascade gaps, gradients/alpha/shadows, font-role ambiguity, fallback model drift, approximate grounding influence, and generated HTML drift.
- Updated `source-style-ledger-plan.md` to preserve the existing intended behavior that source colors should replace approximated screenshot values only when perceptually close enough; otherwise the approximate grounded value should be retained and audited.
- Reorganized `source-style-ledger-plan.md` carry-over rules into ledger construction, post-design-system reconciliation, and generated HTML fallback rules, and reduced grounding sync to a non-goal note.
- Added `surface-component-map-strategy.md` documenting why the current model-backed surface/component map is still useful, why the existing deterministic draft cannot replace it yet, and a gated strategy for replacing it with an audited YAML `surface-component-contract`.
- Updated `surface-component-map-strategy.md` to recommend stricter first-pass section YAML typing with separate closed `kind` and `component_family` axes before replacing the surface/component map model step.
- Refined the proposed section YAML typing list after mining recent groundings: consolidated form controls into `kind: control`, added `effect`, and expanded `component_family` for observed navigation, proof, data, media, and decorative families.
- Revised the proposed section YAML typing so embedded interface/mockup details are captured as `kind: media` with `media_category` and `media_context`, aligning first-pass grounding with downstream image-generation categories.
- Added a `kind` to `component_family` mapping table to `surface-component-map-strategy.md`, clarifying root-level section families like nav/footer versus inner layout/control/surface/media nodes.
- Reworked the proposed raw section YAML taxonomy after checking Material, Carbon, Polaris, and USWDS component models: replaced the overloaded `component_family` enum with kind-specific role fields such as `section_role`, `layout_role`, `surface_role`, `text_role`, and `control_role`.
- Updated `section_role` in `surface-component-map-strategy.md` to follow website-section-library categories inspired by Relume, including navbar, footer, hero/header, feature, CTA, contact, gallery, pricing, testimonial, FAQ, logo, team, blog, banner, product, collection, application UI, content, and utility sections.
- Refined the proposed `section_role` enum to remove app-specific and duplicate roles, adding `compact_header`, `content_feed`, `content_detail`, `stats_metrics`, and `events_feed`.
- Refined `text_role` in `surface-component-map-strategy.md` by replacing subjective `headline`/`title` roles with `heading`/`subheading`, treating legal text as semantic metadata/caption copy, and moving wordmarks/logotype into media/logo handling.
- Reworked `layout_role` in `surface-component-map-strategy.md` around observable geometry such as row, column, wrap, grid, masonry, bento, split, rail, carousel, tabs, table, timeline, inline-media-text, overlay, floating, and off-grid, removing content-specific nav/footer/logo-wall roles.
- Added `text_scale` and `html_level_hint` guidance to `surface-component-map-strategy.md` so first-pass section grounding records visual type scale separately from inferred H1/H2/H3 semantics.
- Simplified `surface_role` in `surface-component-map-strategy.md` to canvas, panel, card, frame, and overlay, folding tile/tray/inset/table-shell distinctions into semantic roles when needed.
- Refined `surface_role` again around scale and nesting: replaced `panel` with `module` for large section-like shells, kept `card` for item containers, and narrowed `frame` to visible border/radius/clipping/divider surfaces around media or small elements.
- Updated the proposed raw section YAML schema guidance to omit non-applicable role fields instead of emitting `none` placeholders, while allowing the deterministic contract compiler to normalize missing fields internally for audits.
- Added raw section YAML cleanup guidance to omit absent style attributes such as border/shadow instead of writing `none_observed`, and to omit default `visibility: visible` unless the element is structural-only, partial, obscured, or unclear.
- Added structural website-layout guidance to `surface-component-map-strategy.md`: model inner max-width containers as `layout_role: container`, replace loose `section_padding_estimate` with padding/container constraints, and prefer responsive sizing fields over raw pixel bounds.
- Added value-normalization guidance to keep implementation values as clean scalars/enums, omit overly uncertain fields, and avoid both uncertainty words/ranges and downstream-useless confidence/evidence/measurement-basis metadata.
- Replaced CSS-specific sizing examples such as `flex_basis_px` in `surface-component-map-strategy.md` with generic responsive sizing fields such as `item_width_px`, `min_item_width_px`, `max_item_width_px`, and `width_behavior`.
- Updated viewer jump-link CSS so long screenshot names truncate in the top navigation instead of stretching the header.
- Kept viewer toggle and Output Docs tab button labels on one line.
- Prevented fixed top-bar controls from flex-shrinking so labels like "Show Structural Output" do not wrap.
- Prevented sticky cell header labels such as "Output Docs" from wrapping beside the tab controls.
- Added deterministic `surface-component-contract.yaml` compilation from raw section YAML trees, including schema/coverage audits, source-style color matching hooks, prompt-safe rendering with trace IDs stripped, and unit coverage.
- Added `surface-map-mode` config/CLI support (`auto`, `model`, `contract`, `skip`); `auto` now uses the deterministic contract only when audits pass and otherwise falls back to the model surface map.
- Fed the deterministic contract into design-system synthesis as a normative surface/component reference when selected, while keeping the existing model map path available as fallback/debug.
- Added viewer and manifest support for `surface-component-contract.yaml` and `surface-component-contract-audit.md`, then regenerated `viewer.html`.
- Tightened the default section-analysis prompt so future raw section YAML uses closed primitive `kind` values, kind-specific role fields, omitted default visibility, omitted `none` placeholders, and clean implementation scalars.
- Verified the contract compiler on v172 Better Nights cached section YAML: extracted 25 host surfaces, 104 child recipes, and 63 critical pairings; the audit correctly keeps `auto` on model fallback for legacy open-kind YAML.
- Verified with `./venv/bin/python -m unittest discover -s tests` and `./venv/bin/python -m py_compile run_pipeline.py src/screenshot_to_template/config.py src/screenshot_to_template/cli.py src/screenshot_to_template/prompts.py src/screenshot_to_template/surface_contract.py`.

## 2026-05-06

- Disabled Gemini as a future site-generation provider, filtering inherited `gemini` provider entries out of new version configs and guarding direct Gemini site generation calls before they can invoke `gemini-3.1-pro-preview`.
- Added YAML pipeline quality evaluator for normalized AST and design-system YAML artifacts, combining deterministic parse/schema checks with screenshot-based review scoring.
- Added full-site global grounding support to the section-grounding pipeline so grouped layer relationships such as shared nav/hero backgrounds, section runs, and hard resets can feed the normalized AST.
- Added `--reuse-section-groundings-from` support to `run_pipeline.py` to reuse cached raw section YAML while rerunning full-site grounding, merge, design-system synthesis, generated sites, reviews, image generation, and viewer regeneration.
- Hardened YAML design-system color sync so invalid diff/patch repair responses do not replace valid YAML artifacts; added deterministic fallback color replacement for YAML design systems.
- Fixed source color alpha parsing for range-like values such as `rgba(..., 0.45-0.75)` so grounding style sync no longer skips on those values.
- Ran v160-v169 YAML/global experiments and regenerated `viewer.html`; later runs were reduced to clean and funky per user request.
- Fixed generated site asset candidate scanning so explicit `data-stt-asset-brief` placeholders fall back to a static HTML scan when the headless browser scan returns no candidates or errors.
- Fixed generated site asset candidate scanning for reveal-prep hidden placeholders: browser scanning now includes explicit `data-stt-asset-brief` nodes with measurable boxes even when `visibility:hidden` or `opacity:0`, merges browser candidates with static explicit-brief candidates, reads SVG data-URI placeholder dimensions in static fallback, retries transient image API failures, and writes manifest/HTML progress incrementally during long asset batches.
- Updated generated site asset handling so illustration/graphic/diagram/badge assets use a transparent cutout path while photographic and atmospheric/background assets stay opaque; `gpt-image-2` cutouts now use a chroma-key generation prompt followed by local alpha removal.
- Fixed generated asset HTML rewriting so replacement `<img>` assets force visible opacity instead of inheriting near-zero placeholder opacity from generated-site CSS.
- Fixed transparent generated asset rewriting to clear the immediate placeholder visual-well background, avoiding stacked generated imagery over CSS placeholder art.
- Tightened transparent asset prompts and rewrite styles so cutout graphics fill the target content width instead of inheriting placeholder `cover` sizing or generating extra inset card/panel compositions.
- Strengthened generated image prompts to imbue brand direction from structured design-system YAML, including image/graphics patterns, surface cues, color roles, imagery rules, card/spacing/container rules, and do-not-generalize constraints.
- Tested asset generation/background removal on copied v169 generated sites with a deterministic fake image provider and regenerated `viewer.html` after updating v169 notes.
- Disabled shader/Three.js-style site generation skills by default and filtered them out of version skill lists, so bespoke visual wells should be emitted as `gpt-image-2` asset placeholders instead of procedural shader/canvas artwork.
- Added a separate `layouts.yaml` artifact derived from the normalized AST so exact source section order and component positioning stay outside the reusable design-system artifact.
- Made `design-system.yaml` the canonical artifact when design-system output is parseable YAML, while keeping `design-system.md` as a compatibility copy for older tools.
- Strengthened site-generation instructions for grounded shared-parent surface continuity, centered compact labels inside centered stacks, circular icon-action controls, and white-to-tint gradient starts.

## 2026-05-05

- Added root `README.md` for Design System Extractor with developer setup, main pipeline entry points, output locations, prompt/versioning rules, viewer regeneration instructions, and verification commands.
- Expanded `README.md` to clarify extracted source styles/site variables, pipeline stages, source-style artifacts, and common run artifact meanings.
- Added `run_image_pipeline.py`, a separate image-crop pipeline that detects sections, saves all section crops, sends three selected crop images directly to the model, and generates a Services page without sending design-system markdown.
- Added `viewer-image.html` for reviewing image-crop pipeline runs, including the source screenshot, selected crop images, generated Services page, and prompt artifact.
- Verified `run_image_pipeline.py` syntax with `./venv/bin/python -m py_compile run_image_pipeline.py`.
- Generated `viewer-image.html` with `./venv/bin/python run_image_pipeline.py --viewer-only`.
- Regenerated `viewer.html` with the repository viewer regeneration command.
- Updated image-crop selection to automatically send the hero section, one center/body section, and footer section unless manual `--crop-indices` are provided.
- Ran image-crop Services pipeline `runs/image/v001` across the default test screenshots and regenerated `viewer-image.html`.
- Added explicit selected-crop roles (`hero`, `center/body`, `footer/bottom`) to prompts and viewer rendering.

## 2026-05-04

- Updated `run_pipeline.py` viewer generation to mark dropdown versions with an image emoji when they contain real non-direct generated site HTML.
- Added detection that includes both design-system-generated and grounding-to-site outputs while excluding screenshot-direct-only, missing, skipped, and placeholder/error site HTML.
- Regenerated `viewer.html` and `viewer-data/vNNN.js` payload files.
- Verified `run_pipeline.py` syntax with `./venv/bin/python -m py_compile run_pipeline.py`.
- Verified the generated-site detector currently flags 71 dropdown versions, including `v060`.

## 2026-05-01

- Added `tools/generate_version_scoreboard.py` to scan `runs/vNNN` folders for scored review artifacts and generate a horizontal version scoreboard landing page.
- Generated `version-scoreboard.html` with per-version score columns, grouped jump navigation, scoreless artifact links, and each run's `changes.md` content.
- Verified the scoreboard generator with `./venv/bin/python -m py_compile tools/generate_version_scoreboard.py`.
- Updated `run_pipeline.py` viewer generation to write per-version payload scripts under `viewer-data/`.
- Changed `viewer.html` to embed only the latest run payload and lazy-load other version payloads when selected.
- Kept text-compare loading bounded to the compared versions instead of all versions.
- Regenerated `viewer.html` and generated `viewer-data/vNNN.js` payload files.
- Verified `run_pipeline.py` syntax with `./venv/bin/python -m py_compile run_pipeline.py`.
- Verified `viewer.html` opens at `v145` and lazy-loads `v144` in Playwright without page or console errors.
