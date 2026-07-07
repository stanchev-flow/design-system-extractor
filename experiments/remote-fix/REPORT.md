# remote-fix batch — REPORT

Date: 2026-07-03 · Worker: Remote-blockers fix-batch · Working-tree only (NO git ops).
Mission: the 7 pipeline blockers + 3 schema gaps from `experiments/remote-e2e/REPORT.md`
§5, all three brands staying gate-green.

**Result: all 10 items closed. Suite 187/187 (159 baseline + 28 new). Regate zero
PASS→FAIL. WoodWave matrix pixel-identical (0.0000% × 11 shots) with byte-identical DOM.
HubSpot live rerun gate-GREEN (image-backed logo wall). Remote live rerun gate-GREEN
under `--composition` — split hero ON the inset noise panel, filled pill CTA, light
chrome footer, zero foreign assets.**

---

## 1. Fix-by-fix disposition

| # | Item | Disposition |
|---|---|---|
| 1 | `_logo_item_mapping` drops bare-string logo items | **FIXED** — raw-list iteration; `_sanitize_assets` coerces a bare string on disk evidence into `{alt: stem, asset}`; an unsanitized string still lands as its own text caption (AS-33's evidence routing, never dict-filtered away). Tests: `BareStringLogoItems`. |
| 2 | `_hero_mapping` injects WoodWave placeholder art cross-brand | **FIXED + GATED** — slot-faithful hero media (an image entry only for a BOUND slot; zero-media legacy pair stays srcless); every composer default/fallback (`_props_for`, `_LAYER_FALLBACK`, `_OVERLAY_FALLBACKS`, `_ov_media_html`, collage/timeline/testimonial paths) resolves through `_brand_art` against the ACTIVE brand's recursive inventory or is omitted. New gate row: slop "No foreign-brand asset references" (`_brand_asset_corpus`) FAILs a sibling-brand-owned basename. Registry AS-34. Tests: `BrandOwnedDefaultArt`, `ForeignAssetGate`. |
| 3 | `compose_stack_hero` forces typographic hero CTAs | **FIXED** — bound `button` slots map through `_hero_mapping` and render via `render_button`'s law-first cta-shape dispatch (AS-27) in a `.cs-hero-actions` wrap; `never-typographic-primary` brands get their measured filled pill, typographic brands' dispatch still downgrades, no bound slot ⇒ legacy arrow link (WoodWave byte-identical). A `compose_stack` routing bug (hero useCase lost for compositions) fixed en route. Tests: `LawFirstHeroCta`. |
| 4 | Scaffold `6.25rem` literal `var()` fallbacks trip provenance | **FIXED** — provenance-scanned spacing props in all scaffold blobs (`--c-section-pad*`, `--c-block-gap`, `--c-nav-pad-block`, grid gutters in section-scoped selectors) are bare var-refs; `rhythm_vars_css` emits the structural `--c-section-pad-x` / `--c-nav-pad-block` per scope (AS-24 discipline). Tests: `StructuralScaffoldPads` (scanner-faithful). |
| 5 | `FOOTER_SURFACE` hardcoded `inverse-strong` | **FIXED** — `footer_surface_role(doc)`: parses the brand's MEASURED chrome footer bg (brand.yaml `footer.surface.bg`), nearest-RGB-matches it to the brand's OWN `tokens.surfaces` roles (ties prefer the historical default; silent brand keeps `FOOTER_SURFACE_DEFAULT`). Palette-agnostic; WoodWave's `#181313` resolves to its own `inverse-strong`, byte-unchanged. Registry AS-35. Tests: `FooterSurfaceRole`. |
| 6 | Asset globbing ignores subdirectories | **FIXED** — `brand_image_inventory` (recursive scan, attached to the doc via `attach_asset_inventory`) feeds `_valid_asset_names` + `_brand_art`; `copy_assets` walks recursively and preserves relative paths. Tests: `RecursiveAssetDiscovery`. |
| 7 | Preview tier crashes (`KeyError: 'panelTitle'`) + WoodWave caption leaks | **FIXED** — `copy_for` returns `_SafeCopy` (missing key → "", composers' emptiness guards skip the fragment); `render_components_preview` derives all specimen copy/captions from the ACTIVE brand (`_specimen` headline from measured blockMapping/name; `_brand_law` caption facts: real fonts, radius stance, cta shape) and attaches the brand's asset inventory so preview art rides AS-34. Proof artifact: `preview-remote/` (renders clean; remaining "WoodWave" strings are non-rendering shared-CSS comments — see DECISIONS-NEEDED #5). Registry AS-36. Tests: `PreviewTierSafety`. |
| 8 | Self-hosted font registry (schema gap) | **IMPLEMENTED** — brand.yaml `selfHostedFonts:` registry (family → faces → weight + files) merged over the module's legacy `SELF_HOSTED_FONTS` in `brand_self_hosted_fonts`; `copy_fonts`/`font_face_css`/`self_hosted_families` consume it. WoodWave's Melodrama mirrored through the brand.yaml path as the parity proof (byte-equal render either way). Remote's Bossa REGISTERED but files absent from the capture (commercial face, NOT fabricated): no `@font-face` emitted, stack falls through to the measured renderProxy (Lexend Deca); follow-up documented in the brand.yaml block. Tests: `SelfHostedFontRegistry`. |
| 9 | Inset art-panel surface concept (schema gap) | **IMPLEMENTED** — generic, style-gated device (AS-37): composition declares it via the sanctioned `panel-on-media` treatment or a z:back/full-bleed background/panel slot (`_art_panel_payload`); a split hero carrying it routes to the stack-hero panel variant (`_stack_hero_art_panel`) — whole hero inside one rounded panel painted with the brand's OWN art (`heroTreatment`/inventory via `_brand_art`, else the plain panel surface). Law order: brand neverDo (`no-radius`/`no-gradients` refuse) → style front-matter `artPanel: inset|none` (all three style files, identical structure) → brand tokens (`--radius-panel → --radius`). Device CSS (`SCAFFOLD_ART_PANEL_CSS`) ships ONLY on pages that render it. Tests: `InsetArtPanel`. |
| 10 | Brand-selectable chrome footer surface (schema half) | **IMPLEMENTED** — the resolution consumes the extraction schema's existing measured chrome facts (top-level `footer.surface.bg`, present in all three brands' brand.yaml) — no new key needed; the schema gap was that nothing CONSUMED it. Same tests as item 5. |

## 2. Three-brand verification (in mission order)

- **Unit suite** (repo venv, unittest): **187/187 OK** — 159 baseline + 28 new in
  `brand_pipeline/tests/test_remote_fix.py`.
- **`tools/phase0_regate.py`**: **zero PASS→FAIL**; 17× PASS→PASS, `page-anchored`
  FAIL→FAIL (pre-existing, acceptable per mission). One real regression was caught and
  fixed DURING the batch: the art-panel CSS first shipped unconditionally inside
  `SCAFFOLD_HERO_CSS` and tripped WoodWave's `neverDo no-radius` on every page — now
  conditional per-page emission (registry AS-37 records the class).
- **WoodWave parity** (token/logo-batch protocol; 6 matrix pages regenerated through the
  live CLI + `build_blessed_monument.py` with the prior batches' orders/styles):
  - DOM: **byte-identical** body markup vs the pre-batch snapshot (`/tmp/ww-before`);
    diffs confined to `<style>` (documented mechanics: literal-fallback strip,
    structural `--c-*` vars, conditional logo-strip/hero-actions blobs) + the tokens
    banner sha (the additive `selfHostedFonts` brand.yaml block).
  - Visual: **0.0000% pixel diff on all 11 before/after shots** (full pages, statement
    sections, panel-hover states — `parity/`).
  - **Melodrama still resolves** after the font-registry work: `@font-face` emitted from
    the brand.yaml registry path, font files copied per page, 5 weights.
- **HubSpot live regen** (`run_live_hubspot.py`, verbatim hubspot-fix directive, NEW dir
  `runs/hubspot/brand/compose/signup-launch-remotefix-live/`): **ok=true, attempts=2,
  gate OVERALL PASS**; logo wall stays image-backed (6 real `.c-logo-img` svgs;
  `logo-wall-integrity` PASS); zero foreign art; hero visually matches the ratified
  hubspot-fix run (`shots/hubspot-after-*.png`).
- **Remote live regen** (`run_live_remote.py`, NEW dir
  `runs/remote/brand/compose/signup-launch-fixed/`): **ok=true, attempts=3, gate OVERALL
  PASS under `--composition`**; zero foreign callouts (both foreign-brand slop rows
  PASS); footer on Remote's measured light surface (`data-surface="surface/raised"`,
  `#f6f7f8`); hero CTA a filled blue pill inside `.cs-hero-actions`; no WoodWave art
  anywhere (every src Remote-owned).
- **Studio :1500**: answers **200**; `/api/projects` lists the **remote + hubspot +
  woodwave** lanes (thumbs + catalog stats intact).

### Remote visual deltas — closed vs remaining (vs e2e REPORT §4 list)

| e2e delta | Status |
|---|---|
| 1. Hero not split-on-panel (WoodWave-DNA centered stack, title/media collision) | **CLOSED** — split left-copy / right-illustration INSIDE the inset pastel noise panel (`shots/remote-after-hero.png`) |
| 2. Hero CTA typographic arrow | **CLOSED** — filled blue pill (law-first dispatch) |
| 3. Noise-panel treatment didn't ship | **CLOSED** — panel painted with `bg-noise-grey-green-blue-top.webp` via the sanctioned `panel-on-media` treatment |
| 4. Chrome footer navy | **CLOSED** (surface half) — light `#f6f7f8` with dark links. The model still composes its own small link-stack section above the chrome footer ("double footer" half): model behavior under the harness directive, unchanged this batch |
| 5. CTA copy tripled | **REMAINS** — model copy quality (eyebrow/heading/paragraph echo); not a pipeline defect |
| 6. Density vs real homepage | **N/A** — brief-scoped 6-section signup page, per e2e |

Honest new observation: the generator declared the hero's secondary action as a `link`
contract slot; `_hero_mapping` maps only `button` contracts, so the hero shows one pill
(source pattern shows filled + outlined pair). Slot-faithfulness for hero link-contract
actions is AS-26-family follow-up work — listed in DECISIONS-NEEDED (#6) rather than
patched at batch close (it would touch every existing composition's hero mapping and
re-open the parity/regate cycle).

## 3. Registry entries added (`brand_pipeline/spec/anti-ai-slop.md`)

- **AS-34** — Default/fallback art borrowed across brands (asset resolution without
  active-brand evidence): recursive inventory + `_brand_art` + foreign-asset gate row +
  bare-string coercion.
- **AS-35** — Chrome surface roles hardcoded to one brand's grammar: measured
  chrome-footer bg → own-role nearest-RGB resolution, palette-agnostic.
- **AS-36** — Composer copy contracts keyed to the dev brand: `_SafeCopy` +
  brand-derived preview specimens.
- **AS-37** — Device CSS shipped unconditionally (dormant grammar tripping other
  brands' law): style-gated art panel + conditional CSS emission; records this batch's
  own no-radius regate catch.

All in the registry's three-part form (Rule / Why it happens / Caught here / Verify).

## 4. DECISIONS-NEEDED

See `DECISIONS-NEEDED.md`: (1) Bossa licensing/sourcing, (2) Remote hero panel inset
geometry at 1440px, (3) logo-strip marquee motion stance, (4) footer-surface RGB
tie-breaking, (5) WoodWave mentions in shared CSS comments, plus (6) hero link-contract
secondary actions (AS-26 family, above).

## 5. Fences + no-commit confirmation

- Sole writer honored: `fence-snapshot-start.txt` vs `fence-snapshot-close.txt` — the
  ONLY changed files under `brand_pipeline/**`, `styles/**`, `tools/**` are this batch's
  10 own edits; zero foreign writes detected at close.
- `runs/*/brand/**`: pre-existing files read-only except the sanctioned classes —
  regenerated pipeline-owned WoodWave compose outputs (prior batches' precedent, exact
  commands in `changes.md`), NEW additive compose dirs (`signup-launch-fixed`,
  `signup-launch-remotefix-live`), and documented ADDITIVE `selfHostedFonts` blocks in
  Remote + WoodWave brand.yaml (no measured value altered; every added line commented).
  `runs/remote/brand/components-preview/` untouched (preview proof rendered into this
  experiment dir instead).
- All experiment folders read-only except `experiments/remote-fix/`.
- **No git operations of any kind; working tree only. Everything rendered through the
  live pipeline — no hand-authored HTML/JSON.**
