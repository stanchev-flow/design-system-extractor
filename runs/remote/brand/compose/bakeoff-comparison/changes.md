# Bakeoff comparison changes

- Created the comparison lane for a normalized, read-only evaluation of the two completed compositions.
- Candidate A maps to `bakeoff-opus`; Candidate B maps to `bakeoff-sol` (mapping withheld from scoring until final reveal).
- Preserved authored composition inputs and shared source code; only deterministic lane outputs, reports, screenshots, and comparison artifacts are written.
- Recorded one renderer/input hash snapshot in `RENDER-STATE.json`.
- Rerendered both candidates through `brand_pipeline/render_composition.py`; restored each authored composition's exact bytes and mtime after the canonical renderer's provenance write.
- Captured identical 1440×1000 @1x reduced-motion, reveal-stabilized full-page and ten-section screenshots.
- Ran schema validation, composition-mode onbrand, anti-slop at 1440/1180, strict interaction, strict spacing, unresolved-slot, and onbrand readability checks.
- Wrote `normalized-gates.json`, `geometry.json`, `scorecard.json`, `REPORT.md`, and eleven Pillow-built side-by-side comparisons under `shots/`.
- Installed the matching Playwright Chromium binary in Cursor's temporary browser cache after the initial restricted launch failed; reran strict browser gates successfully. No repository dependency or source file changed.
