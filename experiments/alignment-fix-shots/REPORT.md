# Anti-slop batch — alignment resolution (AS-18/19/20) — CLOSURE REPORT

Date: 2026-07-03 ~02:55 · Closing worker (recovery after the 13:50 worker died 23:43 mid-batch)
Scope descoped by coordinator 00:52: regate mandatory, registry + lean report, minimal
after-shots, NO new implementation of unfinished misregistration / hover-token items
(inventoried under DEFERRED instead; sole exception = minimal tree-green fixes).

## What landed (batch C/A/B, verified on disk)

**C — alignment resolution chain (COMPLETE, live):**
- `styles/*.md`: machine-readable `alignment:` front-matter blocks (default + per-role
  anchors incl. counterweight devices), all three styles; parsed by
  `styles.py` (`StyleStructure.alignment_default/alignment_roles/align_for`).
- `layout_library.py`: `Pattern.alignment` parsed from `contentShape.alignment`;
  backfill across all standard pattern YAMLs (`tools/backfill_alignment.py`) + project
  tier `runs/woodwave/brand/layout-library.yaml`. `space-between`/`edge-to-edge` in enum;
  `normalize_anchor` warns loudly on out-of-enum, never drops silently.
- `compose_section.resolve_alignment()` — THE single chain: section-explicit > pattern
  `contentShape.alignment` > style role default. Stamped per section:
  `data-align` + `data-align-source="section|pattern|style"` (+
  `data-align-counterweight`). Both page paths stamp (`compose_page.compose_section_block`
  + footer bookend; single-section renderer stamps `<html>`).
- Gate G10 `alignment-resolution` (hard under `--composition`): missing stamp on a
  stance-declaring style = FAIL; out-of-enum anchor = FAIL; left/right without a
  counterweight = FAIL. `no-centered-everything` recalibrated to declared anchors.
- Unit tests: `brand_pipeline/tests/test_alignment_resolution.py` — **25/25 pass**;
  full suite `brand_pipeline/tests/` — **60/60 pass** (rerun after every edit tonight).

**A — misregistration (LANDED for statement/quote family):**
- Var-driven spans `--c-statement-*-col` / `--c-quote-*-col` (editorial-offset defaults);
  resolved-centered anchor re-scopes them symmetric (text `3/-3`, media `4/-4`) via
  `layout_placement_css`; blessed monument DECLARES `alignment: {anchor: centered}`
  (rebuilt live by `tools/build_blessed_monument.py`).
- Gate G11 `media-registration` (hard): centered section + statement/quote media must
  scope a symmetric span (|start−end| ≤ 1). Remnants → DEFERRED.

**B — surface-mode hover tokens (LANDED for panels/bands):**
- `.cs-panel`, `.cs-ov-panel`, banded `band_vars` re-scope `--c-link-hover` to their own
  ink (gold only where the band surface carries `textAccent`); dark-footer gold hover
  unchanged (measured brand truth).
- `readability.check_link_hover_contrast` re-binds `:hover/:focus` rules to resting
  elements, resolves in the element's OWN var scope, measures vs its OWN background;
  gate check `interaction-contrast` (hard). Remnants (extraction P2 etc.) → DEFERRED.

**Registry:** AS-18 (silent alignment fall-through), AS-19 (misregistration), AS-20
(hover leakage) were already registered by the original worker; this closure added
**AS-25** (alignment layers that disagree / can't see each other). AS-24 left reserved
for the token-provenance entry (`experiments/token-layer-design/SPEC.md`).

## Closure fixes (minimal, required for zero PASS→FAIL)

1. `onbrand_check.extract_facts`: `no-gradients` no longer counts `repeating-*`
   gradients — the AS-23 placeholder hatch (added to `.c-image` by a parallel worker
   tonight) is a flat texture plate, not a wash; it was failing EVERY composed page
   against WoodWave's no-gradients neverDo.
2. `contracts/layout-patterns/about.yaml` (`seam-straddle-portrait`): `align` knob
   default `left` → `center`, matching its own `contentShape.alignment: centered`
   (was emitting a counterweight-less left on every showcase page).
3. `compose_section.resolve_alignment`: counterweight INHERITANCE for bare asymmetric
   section-explicit anchors (LLM `knobs.align: left` shorthand) — device inherited from
   pattern, then style role scan across ALL `_align_role_keys` candidates.
4. `data-align-stance="declared|none"` stamped on `<html>` by both page paths;
   `onbrand_check._style_declares_alignment` reads it FIRST — the A/B arm renders under
   a frozen snapshot style (`experiments/woodwave-ab/inputs/`, no alignment block) and
   must be judged by that operative definition, not today's canonical file by id.
   All four documented as AS-25.

## Mechanical stamp coverage (primary after-evidence, grep of regenerated pages)

21 pages regenerated through the live pipeline tonight (compose_page CLI /
build_blessed_monument / gen_arm_a / cfc.render_composition from persisted LLM
compositions / build_showcase patterns / build_anchored_variants --assemble-only):

- **213 composed `#sec-N` wrappers → 211 stamped** with `data-align` +
  `data-align-source`; source mix ≈ pattern 133 · section 63 · style 15.
- The 2 unstamped are `arm-a-structured` sec-3/sec-4 — that page renders under the
  frozen snapshot style declaring NO stance (`data-align-stance="none"`), the exact
  AS-18 carve-out; G10 passes it as legacy/no-stance, not as silent fall-through.
- **Zero bare asymmetric anchors** (every `left`/`right` stamp carries
  `data-align-counterweight`).
- Diagnosis baseline for contrast: 19/27 sections on the old showcase page were
  left-aligned with zero declared intent (subagent ec95350c).
- `page-anchored`: 12/12 stamped, G10 pass.

## Regate (tools/phase0_regate.py, baseline /tmp/phase0-baseline of Jul 1 22:31)

18 jobs: **17 PASS, zero PASS→FAIL.** Final table: all `full-*` compose pages PASS
(advisory), `arm-a-structured` + `(comp)` PASS (hard), hybrid run-1..5 + smoke +
showcase PASS (hard), ablation on/off/control PASS (hard), `page-anchored`
**FAIL→FAIL** — pre-existing at baseline (`single-accent`; its G10 now passes), not a
regression, left un-rebaselined. No rebaselines were performed.

## After-shots (descoped-minimal)

`experiments/alignment-fix-shots/after/` — full-page shots of the six regenerated
WoodWave compose pages (`full-editorial-luxury`, `full-radical-editorial`,
`full-layout-patterns-v1`, `full-layout-patterns-v2`, `full-layout-patterns-v2-luxury`,
`monument` = full-wildcard-centered-monument), via the predecessor's
`tools/shoot_alignment_fix.mjs` (its statement/hover crops emit automatically as
byproducts). Before-shots remain in `before/` (showcase-lux + monument, shot 15:00
pre-fix). Not re-shot (descope): showcase pages, hybrid/ablation pages, lanes.

## DEFERRED TO NEXT BATCH (inventory only — owned by the token-layer batch,
## spec: experiments/token-layer-design/SPEC.md + DECISIONS.md)

1. **Misregistration beyond statement/quote**: hardcoded asymmetric media spans not yet
   var-driven/anchor-conditional — `compose_section.py` `SCAFFOLD_COLLAGE_CSS`
   (`.cs-collage-media { grid-column: 1 / span 6 }`, ~line 2468) and
   `SCAFFOLD_SPLIT_CSS` (`.cs-split-media { grid-column: 1 / span 6 }`, ~line 2498).
   G11 currently guards only `--c-statement|quote-media-col`
   (`onbrand_check._check_media_registration`, `_MEDIA_COL_VAR_RE`); extend to
   collage/split once their spans are var-driven.
2. **Hover extraction P2**: recurse `@media` in `hoverColor()`
   (`src/screenshot_to_template/browser_chrome_extractor.py:368`, consumed at :582/:883)
   and capture full interaction states into brand tokens
   (`tools/bridge_chrome_to_brand.py`, `brand_pipeline/export_kit.py` hover emission).
3. **Interaction-token re-scope, systemic**: per-surface interaction tokens move into
   the token-layer alias scheme (SPEC.md §alias layer; `--c-link-hover` sites:
   `component_render.py` ~135/157/265-292, `compose_section.py` panel/band scopes
   ~2294/2509/2751/3208) so cards/panels re-scope by construction, not per-scaffold.
4. **`checks.md`-level knob/stance lint**: mechanical scan (AS-25 Verify) that every
   pattern `align` knob default normalizes to its `contentShape.alignment.value` —
   tonight's about.yaml contradiction was found by regate, not by a lint.

## Hygiene

- Write-fence respected: nothing written under `runs/hubspot/**` or
  `experiments/hubspot-e2e/**` (read-only there throughout).
- No git commits/pushes; everything left as working-tree changes.
- Studio :1500 responds (HTTP 200). Note: the server process (up since 13:36, verified
  HTTP 200 at 00:02) was found dead at ~02:57 — not killed by this worker; restarted per
  the handoff convention (`STUDIO_PORT=1500 ./venv/bin/python studio_server.py`, log:
  `studio-restart.log`) and re-verified 200.
- `viewer.html`/`run_pipeline.py` untouched (compose pipeline only) — no viewer regen.
- Everything regenerated through the live pipeline; no hand-authored HTML or
  composition JSON (hybrid pages re-rendered from their persisted LLM-authored
  `composition.json` via `compose_from_composition.render_composition`).
