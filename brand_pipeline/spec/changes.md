# Specification changes

## 2026-07-17 — Executable author gate

- The canonical single-intent flow now includes real model-backed artifact
  authoring from the current lane's evidence, with transactional response groups,
  provider telemetry, deterministic projections, and a bounded C1-C28 repair loop.
- Evidence-complete lanes resume at author without repeating capture/mining/vision/
  curation. Missing provider configuration blocks at AUTHOR before validation.
- Extraction/author failures now produce an honest blocked G1 flow report and
  manifest reason instead of escaping before reporting.

## 2026-07-17 — Grid-fill feasibility / AS-77

- `wireframe.v1` collections now require a chosen fill strategy, scored fill
  candidates, and explicit per-item spans after AS-75 track selection.
- Row-complete options are `complete-rows`, `lead-span`, `tail-span`, and
  `single-column`. `licensed-asymmetry` is valid only with a real painted
  balancing counterweight.
- Spanning cards may cap their internal content measure while their outer plate
  occupies all declared tracks. Responsive collapse preserves item boundaries
  and resets spans to one track.
- Added AS-77: rendered final-row occupancy must not leave unused grid tracks.
  The gate checks painted row width and verifies that declared spans compute.
- Schema, section-wireframing guidance, composition lint, on-brand rows, and the
  browser slop audit were updated together.
