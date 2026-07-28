# 06 Remote Variant — Proof & Conversion

- Added an isolated Studio composition under `runs/relume-test/brand/compose/`; no shared builder, discovery, canonical brand, or sibling variant files were edited.
- Inspected the requested Remote lane location first. `runs/remote/brand/manifest.json` is absent; then inspected `runs/remote/brand/changes.md` and used the available canonical brand, asset, media-semantics, style-scale, and voice files.
- Built a proof/conversion-led alternate page: trust-forward hero, logo and stat evidence, provider comparison matrix, FAQ disclosure with extracted product companion media, customer proof rail, ratings and awards, conversion panel, and full Remote footer.
- Structural recipes come from `brand_pipeline/contracts/section-recipes/catalog.generated.yaml`; visual styling comes only from Remote facts.
- All media is existing extracted Remote media. No generated media or placeholders were added.
- Split media uses intrinsic dimensions, `min-size: 0`, centered alignment, and role-specific fit. No generic 4:3 ratio is used.
- Canonical Remote primary, secondary, neutral, text-link, menu, and rail control states are implemented, including hover, active, disabled where applicable, and focus-visible treatment.
- Honest gaps: the requested canonical manifest and a local Bossa font file are absent. The canonical declared Lexend Deca render proxy is used.
- Verification artifacts: `verification-report.json`, `verification-report.md`, `screenshot.png`, and `screenshot-mobile.png`.

## Recipe sequence

1. `navbar-link-columns`
2. `hero-content-media-split`
3. `logo-wall-carousel`
4. `stats-repeated-grid`
5. `comparison-repeated-grid`
6. `faq-disclosure-list + companion intrinsic media`
7. `testimonial-carousel`
8. `logo-wall-repeated-grid`
9. `cta-content-media-split`
10. `footer-link-columns`
