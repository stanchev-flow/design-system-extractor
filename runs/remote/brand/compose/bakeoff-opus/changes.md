# changes.md — bakeoff-opus lane (candidate B)

Lane-local changelog. All work is confined to
`runs/remote/brand/compose/bakeoff-opus/`. No shared source, brand files, viewer,
root changelog, other lanes, or Studio were edited.

## Model
Claude Opus 4.8 Thinking High.

## Canonical inputs read (read-only)
- `runs/remote/brand/brand.yaml`, `layout-library.yaml`, `section-copy.yaml`, `voice.md`
- `runs/remote/brand/kit/{SKILL.md, readme.md}`
- Shared schema/rendering code: `brand_pipeline/spec/composition-schema.md`,
  `composition.v1.schema.json`, `compose_from_composition.py`, `compose_section.py`
  (dispatch + composers), `render_composition.py`, `onbrand_check.py`, `slop_audit.mjs`.
- No prior generated-page artifacts, stress-playbook, Sol experiment, or the other
  bakeoff lane were read.

## Artifacts written (this lane only)
- `PROMPT.md` — exact marketer brief + operational/isolation constraints preserved.
- `PLAN.md` — concept + section→pattern→archetype→composer mapping + asset list.
- `copy-brief.md` — all authored copy (headings/eyebrows/bodies/CTAs/FAQ/form).
- `composition.json` — valid `composition.v1` (10 authored sections; schema-validated).
- `index.html` — deterministic render (never hand-edited).
- `composition.json`, `tokens.manifest.json`, `assets/` — emitted by the renderer.
- `RENDER-STATE.json` — SHA-256 + mtime of shared renderer/brand inputs at render time.
- `onbrand-report.md`, `onbrand-report.json`, `onbrand-console.txt` — onbrand gate.
- `slop-console.txt` — slop-audit gate output.
- `shots/full-1440.png` + `shots/00..10-*.png` — 1440px full page + per-section closeups.
- `shoot-sections.mjs` — lane-local screenshot helper.
- `REPORT.md`.

## Render command
```
venv/bin/python brand_pipeline/render_composition.py \
  runs/remote/brand/compose/bakeoff-opus/composition.json \
  runs/remote/brand/brand.yaml \
  -o runs/remote/brand/compose/bakeoff-opus --style corporate-saas-clean
```

## Iterations (composition/copy-level only — no HTML or shared-code edits)
1. Authored 10-section composition; schema validation failed on enum values
   (`sizeClass:control`, `width:half/full`, `useCase:comparison/contact`). Fixed to
   schema enums (control→body, half→media/stretch, full→stretch, comparison/contact→
   features/cta). Re-validated OK.
2. First render: 0 unresolved slots. Slop audit FLAGGED sec-2 (accordion) "empty column"
   because the accordion's counterweight media well was unbound. Bound
   `panel-infrastructure-ui-snippet.webp` to the accordion media slot → slop PASS.
3. Onbrand `alignment-resolution` FAILED: sec-3 (capabilities) stamped align source
   `curation` and sec-8 (faq) stamped source `brand`; the gate's source enum only
   accepts `section|pattern|style`. Declared explicit `alignment` on both sections
   (capabilities: left+counterweight cards, matching the pattern's measured geometry;
   faq: centered) so the winning source becomes `section` and the resolved anchor is
   unchanged. Onbrand OVERALL → PASS.
4. Visual inspection fixes (composition-level):
   - `how-it-works` cards were rendering empty noise-gradient media wells (the cards
     composer backfills brand default art when a module declares no asset). Bound three
     real product-UI collages (`collage-eor-ui`, `collage-contractor-management-ui`,
     `collage-global-payroll-ui`) and added STEP 1/2/3 eyebrows.
   - `capabilities` + `how-it-works` were rendering a 2-up editorial stagger instead of a
     clean 3-up grid, because the N-up grid is toggled by `section.grid.columns`
     (re-scopes `--grid-cols`), NOT `knobs.columns`. Added `grid: {columns:3, gutter:"2rem"}`
     to both → clean equal-height 3-up card grids.
   - `comparison` was converted from a 2-card grid (which forced default-art media wells)
     to a `split` seeded from `infra-proof-split` with a 4-row ruled comparison table
     (dimension → before/after) beside a product-UI media panel.
5. Re-rendered, re-shot, re-ran both gates on the final render. RENDER-STATE.json
   refreshed against the final render's shared-code state.

## Final gate status
- neverDo: PASS (never-typographic-primary, never-zero-radius, never-allcaps-headings).
- composition invariants (HARD): all PASS (single-accent, primitive-only, rhythm,
  data-composition, slot-resolution, text-contrast, decoration-salience, occlusion,
  band-attribution, alignment-resolution, media-registration, interaction-contrast,
  token-provenance, logo-wall-integrity).
- slop audit: PASS @1440 and @1180.
- OVERALL: PASS. Advisory style WARNs recorded in REPORT (never gate).

## Shared-renderer observations (documented, NOT worked around by hand-editing)
- Alignment-source enum mismatch: `resolve_alignment` legitimately emits sources
  `curation` and `brand`, but the `alignment-resolution` gate only accepts
  `section|pattern|style` — so a composition that relies on a curated/brand-grammar
  anchor fails the HARD gate until it re-declares the same anchor at the section layer.
- Hero/section secondary CTA `family: "outlined"` did not visibly render as an outlined
  pill (both hero CTAs render filled); the brand's cta-shape dispatch appears to force
  the filled family. Left as-is (no HTML edit).

## Follow-up (for the parent normalization pass)
- Re-render `composition.json` against the final agreed shared-code state and re-run
  gates; RENDER-STATE.json records the code versions this lane's HTML was produced against.
