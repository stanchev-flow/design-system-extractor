# Remote Variant — Editorial Flow

- Added as an item-local Studio composition; no shared builder or discovery file was changed.
- Canonical source: `runs/remote/brand` (lane changelog inspected; no lane manifest exists on disk).
- Structure varies; Remote tokens, component contracts/states, section rhythm, surfaces, nav, and footer remain invariant.
- Relume structural priors are recorded in `composition.json#recipeSequence`; visual defaults were ignored.
- All rendered media resolves to the extracted Remote asset inventory. No generated or invented media is used.
- Media uses intrinsic/extracted ratios; no generic 4:3 ratio or stretch alignment is present.
- Browser verification: PASS at 1440×1000 and 390×844.
- Readability: 4.91:1 worst measured text contrast at both viewports; 0 failures.
- Geometry: 0 horizontal-overflow failures, 0 non-cover media-stretch failures, and no generic 4:3 ratio.
- Component fidelity: 236 browser-computed properties across extracted Remote control states; 0 mismatches.
- Assets/interactions: 21 rendered assets resolved at each viewport; mobile menu keyboard activation passed.
- Preview artifacts: `preview.png` and `preview-mobile.png`; detailed results in `verification-report.{md,json}`.
