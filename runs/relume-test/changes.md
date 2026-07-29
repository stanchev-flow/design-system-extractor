# Relume test changes

## 2026-07-17

- Registered a manual Studio project named `Relume test` using the existing `runs/<version>/studio-project.json` discovery convention.
- Mirrored the standalone annotated Remote homepage content-structure wireframe into `remote-homepage-wireframe/single/`.
- Added `site-claude.html` as the standard Studio preview lane artifact, with local `styles.css` and `script.js`.
- Added the exact supplied source image as `remote-homepage-wireframe/screenshot.png`, following Studio's standard per-item `screenshot.*` original-site convention.
- Preserved the standalone source project in the sibling `relume-test` checkout beside this repo.
- No pipeline prompts or source defaults were changed.
- No `manifest.json` was created because existing manually registered Studio projects use `studio-project.json` without a pipeline manifest.
- `viewer.html` regeneration is not required: this addition does not alter viewer code, viewer data shape, or embedded run-output rendering.

## Verification

- Parsed both standalone and mirrored HTML with Python's standard-library HTML parser.
- Checked both JavaScript files with `node --check`.
- Confirmed `studio_server.list_projects()` returns title `Relume test`, status `ready`, and item `remote-homepage-wireframe`.
- Confirmed `studio_server.project_detail("relume-test")` exposes `/runs/relume-test/remote-homepage-wireframe/single/site-claude.html` as a preview lane.
- Confirmed the copied source screenshot has the same SHA-256 digest as the supplied image: `362f26a476b96cca9a80ef945f40346bc870fa0253ffe42e14f05c536b70c433`.
- Confirmed `/api/project/relume-test` reports both `screenshot` and `site_claude`; both URLs return HTTP 200, and the source returns `image/png`.
- Loaded the mirrored artifact through the running Studio server and captured desktop and mobile-breakpoint headless browser screenshots.
- Checked edited HTML, CSS, and JavaScript with IDE diagnostics; no linter errors were reported.

## Three-brand structure comparison

- Added three ordered Studio composed-page lanes under the existing `Relume test` project:
  - `brand/compose/01 HubSpot/index.html`
  - `brand/compose/02 Remote/index.html`
  - `brand/compose/03 WoodWave/index.html`
- Preserved the original `remote-homepage-wireframe` item and its exact source screenshot comparison.
- All three pages use the same approved 12-part structural sequence: navigation, split hero, trust strip, disclosure split, second feature split, centered CTA, resource grid, centered proof, horizontal proof rail, awards rail, closing CTA, and multi-column footer.
- Removed all wireframe annotations from the branded pages.
- Added `composition.json`, `tokens.manifest.json`, and lane-local `changes.md` for each generated page.
- Media policy is fail-closed: every rendered media URL was validated against that brand's canonical `assets-tagged.json` and on-disk `assets/` directory. No generated or synthesized media is used.
- HubSpot resolves 23/23 media slots from `runs/hubspot-v2/brand/assets/`.
- Remote resolves 24/24 media slots from `runs/remote/brand/assets/`.
- WoodWave resolves 14/22 media slots from `runs/woodwave-v2/brand/assets/`; four trust-logo and four award-logo slots are explicit accessible `Media unavailable` gaps because the extracted inventory contains only the WoodWave own-brand mark and no customer/award marks.
- WoodWave is labeled honestly as based on available extracted facts. Its canonical manifest remains `needs_iteration`, `pipeline_run_completed: false`, `generationAllowed: false`; this comparison lane does not claim the canonical extraction is complete or quality-bar-ready.
- Captured each page at desktop and 390px mobile as `preview.png` and `preview-mobile.png`.
- Browser checks passed for all three pages: desktop/mobile load, mobile menu interaction, no console errors, and every rendered image URL returned HTTP 200.
- Brand-specific rhythm checks passed at desktop and mobile. The generated `composition.json` in each lane records its exact 11-band surface sequence, canonical `brand.yaml`/layoutGrammar/style-scale sources, and resolved section/container/relational spacing.
- HubSpot computed rhythm: 176px hero / 64px working section cadence, 1080px container, 80/32/16px column/grid/action gaps; 11/11 surfaces matched the HubSpot page rhythm projection.
- Remote computed rhythm: 80px hero / 48px working section cadence, 1216px container, 48/32/16px column/grid/action gaps; 11/11 surfaces matched the all-light Remote rhythm projection.
- WoodWave computed rhythm: 150px hero / 120px working section cadence, 1300px container, 64/32/24px column/grid/action gaps; 11/11 surfaces matched the available dark-first WoodWave rhythm projection. Mobile uses its extracted 64px hero / 48px working cadence.
- Browser-computed readability gates passed at 1440px and 390px, including nested cards, nav/footer, buttons, disclosures, hover text, focus indicators, and control boundaries: HubSpot worst 4.66:1; Remote 4.91:1; WoodWave 5.24:1. Reports live beside each page as `verification-report.json` and `.md`.
- Existing `brand_pipeline/onbrand_check.py` ran against each active canonical `brand.yaml`; all three returned `OVERALL: PASS`, including rhythm, text contrast, interaction contrast, token provenance, media registration, logo integrity, and brand neverDo checks. The custom primitive-vocabulary row is advisory because these are standalone static pages.
- Studio discovery code was not changed. The pages use the supported `runs/<project>/brand/compose/<brief>/index.html` lane convention, which preserves the existing Original Site item while exposing all three generated pages in the lane selectors.
- `viewer.html` was not regenerated because no viewer code, viewer data shape, `run_pipeline.py`, or embedded viewer output was changed.

## Exact component-contract rebuild

- Replaced the shared generic `.btn`, `.menu`, and `.rail-control` visual mapping with brand-scoped component CSS generated from each canonical `brand.yaml#buttons` matrix.
- Removed the forced `border-color: var(--button-outline)` override and the invented generic `control-border` channel.
- Primary, secondary, tertiary, text-link, menu, and rail/icon controls now preserve declared rest/hover/pressed/focus/disabled geometry and paint, including transparent/none borders, exact widths, radii, height, padding, type, and `onInverse` variants.
- Missing menu/rail/state contracts degrade to a named nearest declared variant and are recorded in each `composition.json`.
- Added `component_fidelity_audit.py`. It creates browser probes on primary/inverse surfaces and compares computed background, ink, border width/style/color, radius, height, padding, font size/weight, and focus outline for all states.
- Component fidelity PASS: HubSpot 332 properties / 0 failures; Remote 284 / 0; WoodWave 368 / 0.
- Desktop/mobile assets, menu toggle, horizontal rail controls, screenshots, and on-brand gates passed for all three pages.
- Readability remains honestly blocked where the exact source contract itself violates the requested thresholds:
  - HubSpot primary white on idle orange is 3.40:1; its required transparent border gives 2.68:1 boundary contrast on accent-wash.
  - WoodWave light-surface text-link hover gold on cream is 1.34:1. Rest-state text is 5.24:1.
  - Remote passes all readability checks; worst 4.91:1.
- Canonical brand data was not modified. HubSpot and WoodWave lanes are marked blocked in their generated composition manifests; Remote is marked pass.
- `viewer.html` remains unchanged because Studio discovers the updated compose outputs directly and no viewer code/data-shape contract changed.

## Intrinsic split-media geometry

- Root cause: the shared builder applied both `min-height: 430px` and `aspect-ratio: 4 / 3` to every hero/feature media wrapper. In a two-column grid, that artificial media block-size became the row's max-content height; `align-items: center` then re-centered the shorter copy stack inside the expanded row, visually swallowing the intended internal/section rhythm.
- Evidence: none of the nine active hero/feature assets is 4:3. Feature assets measure HubSpot 604×353 and 640×640; Remote 1068×1068 and 1526×1100; WoodWave 800×923 and 500×652.
- Fixed in `brand/compose/build_pages.py`: removed generic 4:3 and generic minimum heights, added `min-width/min-height: 0`, intrinsic image sizing, centered self-alignment, max-content grid tracks, and per-slot `fit`/optional canonical-ratio mapping.
- No slot currently declares an explicit canonical ratio, so all wrappers compute `aspect-ratio: auto` and hug the extracted asset ratio. The mapping supports a future explicit ratio only when a brand/recipe supplies it.
- Added `media_geometry_audit.py`. At 1440px and 390px it checks computed aspect ratio, intrinsic image/frame ratio, zero minimum size, row max-content height, sibling centering, section padding, split gaps, and eyebrow/heading/body/action gaps.
- Media geometry PASS: HubSpot, Remote, WoodWave — desktop/mobile, 0 failures each.
- Rebuilt all pages and preview screenshots. Component fidelity remains 332/284/368 properties with 0 mismatches; on-brand passes all three; Remote readability passes, while the previously documented exact-source contrast conflicts remain unchanged for HubSpot and WoodWave.
- `viewer.html` was not regenerated: Studio serves these compose outputs directly and no viewer implementation or data-shape contract changed.
