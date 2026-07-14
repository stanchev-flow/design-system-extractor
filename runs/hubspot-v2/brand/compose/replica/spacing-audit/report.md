# Spacing-conformance baseline report

Generated 2026-07-10T22:57:25Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/replica | 2026-07-10 23:57:01 | 118 | 107 | 2 | 0 | 0 | 9 | **0** |

## compose/replica

`runs/hubspot-v2/brand/compose/replica/index.html` (mtime 2026-07-10 23:57:01)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `container.stack-width` | 1080px x2 | container-max (1080px) | sec-4(agent-carousel), sec-9(closing-cta) |
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-10(closing-bookend) |
| `strip.gap` | 40px x1 | section-y-sm (40px) | sec-1(logo-wall) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (hero) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (logo-wall) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (logo-wall) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (logo-wall) | `block.header-to-content` | 40px | block-to-block (40px) | +0px | conform | .cs-flow |
| sec-1 (logo-wall) | `strip.gap` | 40px | — | — | unmapped | median of 4 inter-mark gaps |
| sec-1 (logo-wall) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (logo-wall) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-2 (platform-carousel) | `section.pad-top` | 88px | section-y-lg (96px) | -8px | conform | computed padding-top 64px (content stretches) |
| sec-2 (platform-carousel) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (platform-carousel) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-split-intro |
| sec-2 (platform-carousel) | `split.column-gap` | 80px | column-to-column (80px) | +0px | conform | split columns |
| sec-2 (platform-carousel) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-2 (platform-carousel) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-3 (product-grid) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-3 (product-grid) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-3 (product-grid) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-modules-intro |
| sec-3 (product-grid) | `header.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform | .c-header |
| sec-3 (product-grid) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (product-grid) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (product-grid) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (product-grid) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (product-grid) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (product-grid) | `grid.row-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules row |
| sec-3 (product-grid) | `grid.row-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules row |
| sec-3 (product-grid) | `grid.row-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules row |
| sec-3 (product-grid) | `grid.row-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules row |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (product-grid) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-3 (product-grid) | `card.body-to-actions` | 48px | product-grid-split.deviceGeometry.cardActionGap (48px) | +0px | conform | min across 10 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-3 (product-grid) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-3 (product-grid) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-4 (agent-carousel) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (agent-carousel) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (agent-carousel) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-modules-intro |
| sec-4 (agent-carousel) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-4 (agent-carousel) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-4 (agent-carousel) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (agent-carousel) | `card.media-to-content` | 31.98px | panel-padding (32px) | -0.02px | conform | full-bleed well seam |
| sec-4 (agent-carousel) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (agent-carousel) | `card.media-to-content` | 31.98px | panel-padding (32px) | -0.02px | conform | full-bleed well seam |
| sec-4 (agent-carousel) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (agent-carousel) | `card.media-to-content` | 31.98px | panel-padding (32px) | -0.02px | conform | full-bleed well seam |
| sec-4 (agent-carousel) | `card.body-to-actions` | 31.98px | agent-card-carousel.deviceGeometry.cardActionGap (32px) | -0.02px | conform | min across 1 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-4 (agent-carousel) | `container.stack-width` | 1080px | — | — | unmapped |  |
| sec-4 (agent-carousel) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-5 (integration-banner) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (integration-banner) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (integration-banner) | `header.body-to-actions` | 56px | body-to-cta (56px) | +0px | conform | .cs-split-body |
| sec-5 (integration-banner) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-5 (integration-banner) | `strip.gap` | 20px | integration-collage-banner.strip.gap.media (20px) | +0px | conform | median of 5 inter-mark gaps |
| sec-5 (integration-banner) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-5 (integration-banner) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-6 (case-study-header) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-6 (case-study-header) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-6 (case-study-header) | `header.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform | .cs-flow |
| sec-6 (case-study-header) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-flow |
| sec-6 (case-study-header) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-6 (case-study-header) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-7 (testimonial-tabs) | `section.pad-top` | 96px | section-y-lg (96px) | +0px | conform | computed padding-top 64px (content stretches) |
| sec-7 (testimonial-tabs) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-7 (testimonial-tabs) | `header.body-to-actions` | 56px | body-to-cta (56px) | +0px | conform | .cs-split-intro |
| sec-7 (testimonial-tabs) | `split.column-gap` | 80px | column-to-column (80px) | +0px | conform | split columns |
| sec-7 (testimonial-tabs) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-7 (testimonial-tabs) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-8 (badge-row) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-8 (badge-row) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-8 (badge-row) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-8 (badge-row) | `strip.gap` | 12px | award-badge-row.strip.gap.media (12px) | +0px | conform | median of 5 inter-mark gaps |
| sec-8 (badge-row) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-8 (badge-row) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-9 (closing-cta) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-9 (closing-cta) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-9 (closing-cta) | `header.body-to-actions` | 56px | body-to-cta (56px) | +0px | conform | .cs-conversion |
| sec-9 (closing-cta) | `container.stack-width` | 1080px | — | — | unmapped |  |
| sec-9 (closing-cta) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-10 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-10 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-10 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-10 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-10 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-10 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-10 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-10 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-10 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (hero→logo-wall) | `section.seam` | 128px | section-padding-light+section-padding-light (128px) | +0px | conform |  |
| sec-1→sec-2 (logo-wall→platform-carousel) | `section.seam` | 152px | section-padding-light+section-y-lg (160px) | -8px | conform |  |
| sec-2→sec-3 (platform-carousel→product-grid) | `section.seam` | 128px | section-padding-light+section-padding-light (128px) | +0px | conform |  |
| sec-3→sec-4 (product-grid→agent-carousel) | `section.seam` | 128px | section-padding-light+section-padding-light (128px) | +0px | conform |  |
| sec-4→sec-5 (agent-carousel→integration-banner) | `section.seam` | 128px | section-padding-light+section-padding-light (128px) | +0px | conform |  |
| sec-5→sec-6 (integration-banner→case-study-header) | `section.seam` | 128px | section-padding-light+section-padding-light (128px) | +0px | conform |  |
| sec-6→sec-7 (case-study-header→testimonial-tabs) | `section.seam` | 160px | section-padding-light+section-y-lg (160px) | +0px | conform |  |
| sec-7→sec-8 (testimonial-tabs→badge-row) | `section.seam` | 128px | section-padding-light+section-padding-light (128px) | +0px | conform |  |
| sec-8→sec-9 (badge-row→closing-cta) | `section.seam` | 128px | section-padding-light+section-padding-light (128px) | +0px | conform |  |
| sec-9→sec-10 (closing-cta→closing-bookend) | `section.seam` | 128px | section-padding-light+section-padding-light (128px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-0 (hero): container — no max-width-constrained scaffold found

