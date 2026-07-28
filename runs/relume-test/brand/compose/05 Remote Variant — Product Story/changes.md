# 05 Remote Variant — Product Story

- Built Variant B as an item-local Studio compose lane; no shared builder, discovery, canonical brand data, or sibling variant was edited.
- `runs/remote/brand/manifest.json` was requested but is not present in the working tree. Read `runs/remote/brand/changes.md` and used the active canonical Remote artifacts under `runs/remote/brand/`.
- Brand and content foundation: `runs/remote/brand/brand.yaml`, `assets-tagged.json`, `media-assets.yaml`, `style-scale.yaml`, and existing Remote copy/composition evidence.
- Structural prior: `brand_pipeline/contracts/section-recipes/catalog.generated.yaml`.
- Recipe sequence: `navigation-standard-nav → product-header-content-media-split → logo-wall-carousel → feature-tabs → feature-content-media-split ×3 → feature-repeated-grid → timeline-timeline → testimonial-carousel → cta-media-background → footer-link-columns`.
- The product-led sequence is materially distinct from the existing Remote page: product-interface opener, proof rail, keyboard-operable five-state product tabs, three alternating feature splits, asymmetric capability bento, four-step process, testimonial carousel, closing CTA, and full Remote navigation/footer chrome.
- Every rendered image comes from `runs/remote/brand/assets/`; no generated, invented, or external image asset is used.
- Product media uses intrinsic extracted dimensions and `aspect-ratio:auto`; split media is center self-aligned with zero min-size. No generic media ratio was introduced.
- Remote invariants retained: all-light page bands, deep navy only inside media wells, pastel extracted noise art for the closing CTA, Bossa/Lexend Deca display proxy at weight 400, Inter body/control type, blue/crimson extracted state colors, 48px pill controls, 1216px container, 48px desktop section rhythm, and 32px mobile rhythm.
- Exact Remote primary, secondary, neutral, focus, pressed, hover, and disabled control states are represented. Product tabs use the extracted maroon active and pink hover states.
- Browser verification passed at 1440×1000 and 390×844: no horizontal overflow, all 34 rendered images loaded with valid intrinsic dimensions, no console/network errors, computed text contrast passed WCAG thresholds, tabs passed keyboard/roving-tabindex checks, the mobile menu opened from the keyboard, and carousel controls moved the focusable scroll track.
- Component fidelity passed 34/34 computed properties across primary, secondary, neutral chrome, focus, hover, pressed, geometry, and extracted product-tab states.
- Wrote `composition.json`, `tokens.manifest.json`, `verification-report.json`, `verification-report.md`, `preview.png`, and `preview-mobile.png` beside the page.
- Confirmed `/api/project/relume-test` discovers the lane as `Composed: 05 Remote Variant — Product Story` through normal Studio discovery.
- Direct URL: `http://127.0.0.1:1500/runs/relume-test/brand/compose/05%20Remote%20Variant%20%E2%80%94%20Product%20Story/index.html`.
