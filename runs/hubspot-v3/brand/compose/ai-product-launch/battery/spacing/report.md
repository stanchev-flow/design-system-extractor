# Spacing-conformance baseline report

Generated 2026-07-28T23:54:01Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/ai-product-launch | 2026-07-28 19:39:25 | 74 | 55 | 2 | 2 | 2 | 13 | **4** |

## compose/ai-product-launch

`runs/hubspot-v3/brand/compose/ai-product-launch/index.html` (mtime 2026-07-28 19:39:25)

### Top offenders (hard fails, ranked frequency x magnitude)

| # | relationship | measured | expected | Δ | hits | where |
|---|---|---|---|---|---|---|
| 1 | `split.column-gap` | ~90px | column-to-column (24px) | 66px | 1 | sec-4(integrations) |
| 2 | `section.pad-top` | ~0px | section-padding-light (64px) | 64px | 1 | sec-0(hero) |
| 3 | `section.pad-bottom` | ~0px | section-padding-light (64px) | 64px | 1 | sec-0(hero) |
| 4 | `split.column-gap` | ~90px | copy-left-illustration-right-carousel.deviceGeometry.columnGap (64px) | 26px | 1 | sec-2(product-education) |

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `actions.item-gap` | 12px x1 | block-to-block (12px) | sec-7(closing) |
| `container.stack-width` | 736px x1 | container-max (1080px) | sec-7(closing) |
| `footer.column-gap` | 64px x3 | section-padding-light (64px) | sec-8(closing-bookend) |
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-8(closing-bookend) |
| `strip.gap` | 12px x1 | block-to-block (12px) | sec-4(integrations) |
| `strip.gap` | 130px x1 | centered-heading-over-logo-row.bandPadding.bottom (110px) | sec-1(customer-proof) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

16 measured-fact · 2 on-scale · **2 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (hero) | 13px x2 | measured | type fact 13px | c-caption, c-eyebrow |
| type | sec-3 (feature-proof) | 13px x4 | measured | type fact 13px | c-caption, c-eyebrow |
| type | sec-5 (results) | 13px x1 | measured | type fact 13px | c-eyebrow |
| type | sec-8 (closing-bookend) | 13px x1 | measured | type fact 13px | c-foot-legal |
| type | sec-0 (hero) | 16px x4 | measured | type fact 16px | c-button, c-button.c-button--secondary, c-paragraph |
| type | sec-2 (product-education) | 16px x2 | measured | type fact 16px | c-paragraph |
| type | sec-3 (feature-proof) | 16px x5 | measured | type fact 16px | c-button, c-paragraph |
| type | sec-6 (testimonial) | 16px x1 | measured | type fact 16px | c-paragraph |
| type | sec-7 (closing) | 16px x2 | measured | type fact 16px | c-button, c-button.c-button--secondary |
| type | sec-1 (customer-proof) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-2 (product-education) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-3 (feature-proof) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-4 (integrations) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-5 (results) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-7 (closing) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-0 (hero) | 80px x1 | measured | type fact 80px | c-heading.c-heading--display |
| space | sec-1 (customer-proof) | 130px x1 | **off-scale** | no derived step within 2.6px (unit 4) | strip.gap |
| space | sec-4 (integrations) | 12px x1 | on-scale | derived step 12px | strip.gap |
| space | sec-7 (closing) | 12px x1 | on-scale | derived step 12px | actions.item-gap |
| space | sec-7 (closing) | 736px x1 | **off-scale** | no derived step within 14.72px (unit 4) | container.stack-width |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero) | `section.pad-top` | 0px | section-padding-light (64px) | -64px | **off-ladder** |  |
| sec-0 (hero) | `section.pad-bottom` | 0px | section-padding-light (64px) | -64px | **off-ladder** |  |
| sec-0 (hero) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-1 (customer-proof) | `section.pad-top` | 70px | centered-heading-over-logo-row.bandPadding.top (70px) | +0px | conform |  |
| sec-1 (customer-proof) | `section.pad-bottom` | 110px | centered-heading-over-logo-row.bandPadding.bottom (110px) | +0px | conform |  |
| sec-1 (customer-proof) | `block.header-to-content` | 12px | block-to-block (12px) | +0px | conform | .cs-flow |
| sec-1 (customer-proof) | `strip.gap` | 130px | — | — | unmapped | median of 3 inter-mark gaps |
| sec-1 (customer-proof) | `container.width` | 1080px | container-span (1080px) | +0px | conform |  |
| sec-1 (customer-proof) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-2 (product-education) | `section.pad-top` | 80px | copy-left-illustration-right-carousel.bandPadding.top (80px) | +0px | conform |  |
| sec-2 (product-education) | `section.pad-bottom` | 90px | copy-left-illustration-right-carousel.bandPadding.bottom (90px) | +0px | conform |  |
| sec-2 (product-education) | `header.heading-to-body` | 40px | heading-to-body (40px) | +0px | conform | .cs-split-body |
| sec-2 (product-education) | `split.column-gap` | 90px | copy-left-illustration-right-carousel.deviceGeometry.columnGap (64px) | +26px | **wrong-step** | split columns |
| sec-2 (product-education) | `container.width` | 1080px | container-span (1080px) | +0px | conform |  |
| sec-2 (product-education) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-3 (feature-proof) | `section.pad-top` | 90px | headrail-split-with-card-carousel.bandPadding.top (90px) | +0px | conform |  |
| sec-3 (feature-proof) | `section.pad-bottom` | 60px | headrail-split-with-card-carousel.bandPadding.bottom (60px) | +0px | conform |  |
| sec-3 (feature-proof) | `grid.column-gap` | 32px | headrail-split-with-card-carousel.deviceGeometry.columnGap (40px) | -8px | drift | .cs-modules column |
| sec-3 (feature-proof) | `grid.column-gap` | 32px | headrail-split-with-card-carousel.deviceGeometry.columnGap (40px) | -8px | drift | .cs-modules column |
| sec-3 (feature-proof) | `card.inset` | 24px | panel-padding (24px) | +0px | conform | computed padding-left |
| sec-3 (feature-proof) | `card.media-to-content` | 23.98px | panel-padding (24px) | -0.02px | conform | full-bleed well seam |
| sec-3 (feature-proof) | `card.inset` | 24px | panel-padding (24px) | +0px | conform | computed padding-left |
| sec-3 (feature-proof) | `card.media-to-content` | 23.98px | panel-padding (24px) | -0.02px | conform | full-bleed well seam |
| sec-3 (feature-proof) | `card.inset` | 24px | panel-padding (24px) | +0px | conform | computed padding-left |
| sec-3 (feature-proof) | `card.media-to-content` | 23.98px | panel-padding (24px) | -0.02px | conform | full-bleed well seam |
| sec-3 (feature-proof) | `container.width` | 1080px | container-span (1080px) | +0px | conform |  |
| sec-3 (feature-proof) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-4 (integrations) | `section.pad-top` | 70px | centered-heading-over-logo-row.bandPadding.top (70px) | +0px | conform |  |
| sec-4 (integrations) | `section.pad-bottom` | 110px | centered-heading-over-logo-row.bandPadding.bottom (110px) | +0px | conform |  |
| sec-4 (integrations) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-split-body |
| sec-4 (integrations) | `split.column-gap` | 90px | column-to-column (24px) | +66px | **wrong-step** | split columns |
| sec-4 (integrations) | `strip.gap` | 12px | — | — | unmapped | median of 5 inter-mark gaps |
| sec-4 (integrations) | `container.width` | 1080px | container-span (1080px) | +0px | conform |  |
| sec-4 (integrations) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-5 (results) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (results) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (results) | `header.eyebrow-to-heading` | 20px | eyebrow-to-heading (20px) | +0px | conform | .cs-flow |
| sec-5 (results) | `block.header-to-content` | 12px | block-to-block (12px) | +0px | conform | .cs-flow |
| sec-5 (results) | `stat.column-gap` | 24px | column-to-column (24px) | +0px | conform | .cs-stat-band column |
| sec-5 (results) | `stat.column-gap` | 24px | column-to-column (24px) | +0px | conform | .cs-stat-band column |
| sec-5 (results) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-5 (results) | `container.width` | 1080px | container-span (1080px) | +0px | conform |  |
| sec-5 (results) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-6 (testimonial) | `section.pad-top` | 24px | tabbed-testimonial-with-stats.bandPadding.top (24px) | +0px | conform |  |
| sec-6 (testimonial) | `section.pad-bottom` | 40px | tabbed-testimonial-with-stats.bandPadding.bottom (40px) | +0px | conform |  |
| sec-6 (testimonial) | `container.width` | 1080px | container-span (1080px) | +0px | conform |  |
| sec-6 (testimonial) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-7 (closing) | `section.pad-top` | 90px | dark-band-cta.bandPadding.top (90px) | +0px | conform |  |
| sec-7 (closing) | `section.pad-bottom` | 80px | dark-band-cta.bandPadding.bottom (80px) | +0px | conform |  |
| sec-7 (closing) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-conversion |
| sec-7 (closing) | `actions.item-gap` | 12px | — | — | unmapped | median of 1 inter-action gap(s) |
| sec-7 (closing) | `container.stack-width` | 736px | — | — | unmapped |  |
| sec-7 (closing) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 352px / 352px |
| sec-8 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-8 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-8 (closing-bookend) | `container.width` | 1080px | container-span (1080px) | +0px | conform |  |
| sec-8 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-8 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-8 (closing-bookend) | `footer.column-gap` | 64px | — | — | unmapped | directory columns |
| sec-8 (closing-bookend) | `footer.column-gap` | 64px | — | — | unmapped | directory columns |
| sec-8 (closing-bookend) | `footer.column-gap` | 64px | — | — | unmapped | directory columns |
| sec-0→sec-1 (hero→customer-proof) | `section.seam` | 70px | headrail-two-col-header.bandPadding.bottom+centered-heading-over-logo-row.bandPadding.top (70px) | +0px | conform |  |
| sec-1→sec-2 (customer-proof→product-education) | `section.seam` | 190px | dark-band-cta.bandPadding.bottom+centered-heading-over-logo-row.bandPadding.bottom (190px) | +0px | conform |  |
| sec-2→sec-3 (product-education→feature-proof) | `section.seam` | 180px | centered-heading-over-logo-row.bandPadding.top+centered-heading-over-logo-row.bandPadding.bottom (180px) | +0px | conform |  |
| sec-3→sec-4 (feature-proof→integrations) | `section.seam` | 130px | heading-left-award-badges-right.bandPadding.top+dark-band-cta.bandPadding.top (130px) | +0px | conform |  |
| sec-4→sec-5 (integrations→results) | `section.seam` | 174px | section-padding-light+centered-heading-over-logo-row.bandPadding.bottom (174px) | +0px | conform |  |
| sec-5→sec-6 (results→testimonial) | `section.seam` | 88px | headrail-two-col-header.bandPadding.bottom+headrail-two-col-header.bandPadding.top (88px) | +0px | conform |  |
| sec-6→sec-7 (testimonial→closing) | `section.seam` | 130px | heading-left-award-badges-right.bandPadding.top+dark-band-cta.bandPadding.top (130px) | +0px | conform |  |
| sec-7→sec-8 (closing→closing-bookend) | `section.seam` | 144px | section-padding-light+dark-band-cta.bandPadding.bottom (144px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-0 (hero): container — no max-width-constrained scaffold found
- sec-5 (results): .c-stat pair — no non-stat sibling gaps in the block
- sec-5 (results): .c-stat pair — no non-stat sibling gaps in the block
- sec-5 (results): .c-stat pair — no non-stat sibling gaps in the block
- sec-6 (testimonial): .c-stat pair — no non-stat sibling gaps in the block
- sec-6 (testimonial): .c-stat pair — no non-stat sibling gaps in the block

