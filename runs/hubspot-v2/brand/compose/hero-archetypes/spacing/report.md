# Spacing-conformance baseline report

Generated 2026-07-14T13:21:44Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/hero-archetypes/homepage | 2026-07-14 14:13:06 | 26 | 19 | 1 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/pricing | 2026-07-14 14:13:21 | 17 | 11 | 0 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/product | 2026-07-14 14:13:35 | 18 | 12 | 0 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/about | 2026-07-14 14:13:51 | 19 | 13 | 0 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/blog | 2026-07-14 14:14:06 | 24 | 17 | 1 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/demo | 2026-07-14 14:21:04 | 34 | 18 | 2 | 0 | 0 | 14 | **0** |
| compose/hero-archetypes/developer | 2026-07-14 14:18:20 | 17 | 11 | 0 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/event | 2026-07-14 14:14:55 | 19 | 12 | 0 | 0 | 0 | 7 | **0** |

## compose/hero-archetypes/homepage

`runs/hubspot-v2/brand/compose/hero-archetypes/homepage/index.html` (mtime 2026-07-14 14:13:06)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (sec-hero) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (sec-hero) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (sec-hero) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-split-body |
| sec-0 (sec-hero) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-split-body |
| sec-0 (sec-hero) | `header.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform | .c-header |
| sec-0 (sec-hero) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-0 (sec-hero) | `actions.item-gap` | 16px | action-group-gap (16px) | +0px | conform | median of 1 inter-action gap(s) |
| sec-0 (sec-hero) | `actions.alignment` | 0px | centered (0px) | +0px | conform | stamped start; painted edges vs column 0px / 125px (column = widest sibling) |
| sec-0 (sec-hero) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (sec-hero) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-0 (sec-hero) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (sec-hero→closing-bookend) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |

## compose/hero-archetypes/pricing

`runs/hubspot-v2/brand/compose/hero-archetypes/pricing/index.html` (mtime 2026-07-14 14:13:21)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (sec-0) | `section.pad-top` | 40px | section-y-sm (40px) | +0px | conform |  |
| sec-0 (sec-0) | `section.pad-bottom` | 40px | section-y-sm (40px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (sec-0→closing-bookend) | `section.seam` | 104px | award-badge-row.bandPadding.top+case-study-header-rail.bandPadding.top (104px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-0 (sec-0): container — no max-width-constrained scaffold found

## compose/hero-archetypes/product

`runs/hubspot-v2/brand/compose/hero-archetypes/product/index.html` (mtime 2026-07-14 14:13:35)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero-marketing-hub) | `section.pad-top` | 96px | section-y-lg (96px) | +0px | conform |  |
| sec-0 (hero-marketing-hub) | `section.pad-bottom` | 96px | section-y-lg (96px) | +0px | conform |  |
| sec-0 (hero-marketing-hub) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-1 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (hero-marketing-hub→closing-bookend) | `section.seam` | 160px | case-study-header-rail.bandPadding.top+award-badge-row.bandPadding.bottom (160px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-0 (hero-marketing-hub): container — no max-width-constrained scaffold found

## compose/hero-archetypes/about

`runs/hubspot-v2/brand/compose/hero-archetypes/about/index.html` (mtime 2026-07-14 14:13:51)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (about-hero) | `section.pad-top` | 96px | section-y-lg (96px) | +0px | conform |  |
| sec-0 (about-hero) | `section.pad-bottom` | 96px | section-y-lg (96px) | +0px | conform |  |
| sec-0 (about-hero) | `container.stack-width` | 784px | hero-photo-overlay.stackMeasure (784px) | +0px | conform |  |
| sec-0 (about-hero) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 328px / 328px |
| sec-1 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (about-hero→closing-bookend) | `section.seam` | 160px | case-study-header-rail.bandPadding.top+award-badge-row.bandPadding.bottom (160px) | +0px | conform |  |

## compose/hero-archetypes/blog

`runs/hubspot-v2/brand/compose/hero-archetypes/blog/index.html` (mtime 2026-07-14 14:14:06)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (blog-hero) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (blog-hero) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (blog-hero) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-split-body |
| sec-0 (blog-hero) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-split-body |
| sec-0 (blog-hero) | `header.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform | .c-header |
| sec-0 (blog-hero) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-0 (blog-hero) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (blog-hero) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-0 (blog-hero) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (blog-hero→closing-bookend) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |

## compose/hero-archetypes/demo

`runs/hubspot-v2/brand/compose/hero-archetypes/demo/index.html` (mtime 2026-07-14 14:21:04)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |
| `form.field-gap` | 16px x2 | list-item-gap (16px) | sec-0(hero-demo) |
| `form.label-to-input` | 8px x3 | radius-global (8px) | sec-0(hero-demo) |
| `form.stack-gap` | 16px x3 | list-item-gap (16px) | sec-0(hero-demo) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero-demo) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (hero-demo) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (hero-demo) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-split-body |
| sec-0 (hero-demo) | `block.header-to-content` | 32px | block-to-block (40px) | -8px | drift | .cs-split-body |
| sec-0 (hero-demo) | `block.row-gap` | 32px | block-to-block (40px) | -8px | drift | .cs-split-body |
| sec-0 (hero-demo) | `header.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform | .c-header |
| sec-0 (hero-demo) | `form.field-gap` | 16px | — | — | unmapped | .cs-signup-grid row |
| sec-0 (hero-demo) | `form.field-gap` | 16px | — | — | unmapped | .cs-signup-grid row |
| sec-0 (hero-demo) | `split.column-gap` | 80px | column-to-column (80px) | +0px | conform | split columns |
| sec-0 (hero-demo) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (hero-demo) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (hero-demo) | `form.label-to-input` | 8px | — | — | unmapped |  |
| sec-0 (hero-demo) | `form.label-to-input` | 8px | — | — | unmapped |  |
| sec-0 (hero-demo) | `form.label-to-input` | 8px | — | — | unmapped |  |
| sec-0 (hero-demo) | `form.stack-gap` | 16px | — | — | unmapped | form internal seam |
| sec-0 (hero-demo) | `form.stack-gap` | 16px | — | — | unmapped | form internal seam |
| sec-0 (hero-demo) | `form.stack-gap` | 16px | — | — | unmapped | form internal seam |
| sec-0 (hero-demo) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-0 (hero-demo) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (hero-demo→closing-bookend) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |

## compose/hero-archetypes/developer

`runs/hubspot-v2/brand/compose/hero-archetypes/developer/index.html` (mtime 2026-07-14 14:18:20)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero) | `section.pad-top` | 40px | section-y-sm (40px) | +0px | conform |  |
| sec-0 (hero) | `section.pad-bottom` | 40px | section-y-sm (40px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (hero→closing-bookend) | `section.seam` | 104px | award-badge-row.bandPadding.top+case-study-header-rail.bandPadding.top (104px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-0 (hero): container — no max-width-constrained scaffold found

## compose/hero-archetypes/event

`runs/hubspot-v2/brand/compose/hero-archetypes/event/index.html` (mtime 2026-07-14 14:14:55)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |
| `strip.gap` | 40px x1 | section-y-sm (40px) | sec-0(spotlight-hero) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (spotlight-hero) | `section.pad-top` | 96px | section-y-lg (96px) | +0px | conform |  |
| sec-0 (spotlight-hero) | `section.pad-bottom` | 96px | section-y-lg (96px) | +0px | conform |  |
| sec-0 (spotlight-hero) | `strip.gap` | 40px | — | — | unmapped | median of 5 inter-mark gaps |
| sec-0 (spotlight-hero) | `actions.item-gap` | 16px | action-group-gap (16px) | +0px | conform | median of 1 inter-action gap(s) |
| sec-1 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-1 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-1 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (spotlight-hero→closing-bookend) | `section.seam` | 160px | case-study-header-rail.bandPadding.top+award-badge-row.bandPadding.bottom (160px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-0 (spotlight-hero): container — no max-width-constrained scaffold found

