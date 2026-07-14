# Spacing-conformance baseline report

Generated 2026-07-14T15:01:18Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/hero-archetypes/homepage | 2026-07-14 15:33:37 | 26 | 19 | 1 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/pricing | 2026-07-14 15:33:52 | 17 | 11 | 0 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/product | 2026-07-14 15:34:07 | 18 | 12 | 0 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/about | 2026-07-14 15:34:23 | 19 | 13 | 0 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/blog | 2026-07-14 15:51:38 | 24 | 17 | 1 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/demo | 2026-07-14 15:51:54 | 34 | 18 | 2 | 0 | 0 | 14 | **0** |
| compose/hero-archetypes/developer | 2026-07-14 15:35:11 | 17 | 11 | 0 | 0 | 0 | 6 | **0** |
| compose/hero-archetypes/event | 2026-07-14 15:35:28 | 19 | 12 | 0 | 0 | 0 | 7 | **0** |
| compose/replica | 2026-07-14 15:36:56 | 128 | 119 | 3 | 0 | 0 | 6 | **0** |
| compose/components | 2026-07-14 15:37:38 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |

## compose/hero-archetypes/homepage

`runs/hubspot-v2/brand/compose/hero-archetypes/homepage/index.html` (mtime 2026-07-14 15:33:37)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

4 measured-fact · 0 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (sec-hero) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-1 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (sec-hero) | 16px x3 | measured | type fact 16px | c-button, c-button.c-button--secondary, c-paragraph |
| type | sec-0 (sec-hero) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |

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

`runs/hubspot-v2/brand/compose/hero-archetypes/pricing/index.html` (mtime 2026-07-14 15:33:52)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

4 measured-fact · 0 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (sec-0) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-1 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (sec-0) | 18.3px x1 | measured | type fact 18px | cs-sub |
| type | sec-0 (sec-0) | 80px x1 | measured | type fact 80px | c-heading.c-heading--display |

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

`runs/hubspot-v2/brand/compose/hero-archetypes/product/index.html` (mtime 2026-07-14 15:34:07)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

4 measured-fact · 0 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (hero-marketing-hub) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-1 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (hero-marketing-hub) | 16px x1 | measured | type fact 16px | c-paragraph |
| type | sec-0 (hero-marketing-hub) | 48px x1 | measured | type fact 48px | c-heading.c-heading--display |

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

`runs/hubspot-v2/brand/compose/hero-archetypes/about/index.html` (mtime 2026-07-14 15:34:23)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

4 measured-fact · 0 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (about-hero) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-1 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (about-hero) | 18.3px x1 | measured | type fact 18px | cs-sub |
| type | sec-0 (about-hero) | 80px x1 | measured | type fact 80px | c-heading.c-heading--display |

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

`runs/hubspot-v2/brand/compose/hero-archetypes/blog/index.html` (mtime 2026-07-14 15:51:38)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

4 measured-fact · 0 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (blog-hero) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-1 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (blog-hero) | 16px x1 | measured | type fact 16px | c-paragraph |
| type | sec-0 (blog-hero) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |

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

`runs/hubspot-v2/brand/compose/hero-archetypes/demo/index.html` (mtime 2026-07-14 15:51:54)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |
| `form.field-gap` | 16px x2 | list-item-gap (16px) | sec-0(hero-demo) |
| `form.label-to-input` | 8px x3 | radius-global (8px) | sec-0(hero-demo) |
| `form.stack-gap` | 16px x3 | list-item-gap (16px) | sec-0(hero-demo) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

6 measured-fact · 8 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (hero-demo) | 13.6px x1 | measured | type fact 14px | cs-signup-consent.cs-form-split-note |
| type | sec-0 (hero-demo) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-1 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (hero-demo) | 16px x2 | measured | type fact 16px | c-button, c-paragraph |
| type | sec-0 (hero-demo) | 24px x1 | measured | type fact 24px | c-heading.c-heading--h3 |
| type | sec-0 (hero-demo) | 80px x1 | measured | type fact 80px | c-heading.c-heading--display |
| space | sec-0 (hero-demo) | 16px x1 | on-scale | derived step 16px | form.field-gap |
| space | sec-0 (hero-demo) | 16px x1 | on-scale | derived step 16px | form.field-gap |
| space | sec-0 (hero-demo) | 8px x1 | on-scale | derived step 8px | form.label-to-input |
| space | sec-0 (hero-demo) | 8px x1 | on-scale | derived step 8px | form.label-to-input |
| space | sec-0 (hero-demo) | 8px x1 | on-scale | derived step 8px | form.label-to-input |
| space | sec-0 (hero-demo) | 16px x1 | on-scale | derived step 16px | form.stack-gap |
| space | sec-0 (hero-demo) | 16px x1 | on-scale | derived step 16px | form.stack-gap |
| space | sec-0 (hero-demo) | 16px x1 | on-scale | derived step 16px | form.stack-gap |

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

`runs/hubspot-v2/brand/compose/hero-archetypes/developer/index.html` (mtime 2026-07-14 15:35:11)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

3 measured-fact · 0 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-1 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (hero) | 16px x2 | measured | type fact 16px | c-button, c-paragraph |
| type | sec-0 (hero) | 80px x1 | measured | type fact 80px | c-heading.c-heading--display |

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

`runs/hubspot-v2/brand/compose/hero-archetypes/event/index.html` (mtime 2026-07-14 15:35:28)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |
| `strip.gap` | 40px x1 | section-y-sm (40px) | sec-0(spotlight-hero) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

5 measured-fact · 1 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (spotlight-hero) | 14px x2 | measured | type fact 14px | c-caption, c-eyebrow |
| type | sec-1 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (spotlight-hero) | 16px x2 | measured | type fact 16px | c-button, c-button.c-button--secondary |
| type | sec-0 (spotlight-hero) | 18.3px x1 | measured | type fact 18px | cs-sub |
| type | sec-0 (spotlight-hero) | 80px x1 | measured | type fact 80px | c-heading.c-heading--display |
| space | sec-0 (spotlight-hero) | 40px x1 | on-scale | derived step 40px | strip.gap |

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

## compose/replica

`runs/hubspot-v2/brand/compose/replica/index.html` (mtime 2026-07-14 15:36:56)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-10(closing-bookend) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero) | `section.pad-top` | 176px | hero-photo-overlay.bandPadding.top (176px) | +0px | conform |  |
| sec-0 (hero) | `section.pad-bottom` | 176px | hero-photo-overlay.bandPadding.bottom (176px) | +0px | conform |  |
| sec-0 (hero) | `actions.item-gap` | 16px | action-group-gap (16px) | +0px | conform | median of 1 inter-action gap(s) |
| sec-0 (hero) | `container.stack-width` | 784px | hero-photo-overlay.stackMeasure (784px) | +0px | conform |  |
| sec-0 (hero) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 328px / 328px |
| sec-1 (logo-wall) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (logo-wall) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (logo-wall) | `block.header-to-content` | 40px | block-to-block (40px) | +0px | conform | .cs-flow |
| sec-1 (logo-wall) | `strip.gap` | 69px | logo-proof-strip.strip.gap.logos (69px) | +0px | conform | median of 4 inter-mark gaps |
| sec-1 (logo-wall) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (logo-wall) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-2 (platform-carousel) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (platform-carousel) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (platform-carousel) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-split-intro |
| sec-2 (platform-carousel) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (platform-carousel) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-2 (platform-carousel) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-3 (product-grid) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-3 (product-grid) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-3 (product-grid) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-modules-intro |
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
| sec-3 (product-grid) | `actions.item-gap` | 16px | action-group-gap (16px) | +0px | conform | median of 1 inter-action gap(s) |
| sec-3 (product-grid) | `actions.alignment` | 0px | centered (0px) | +0px | conform | stamped start; painted edges vs column 0px / 41px (column = widest sibling) |
| sec-3 (product-grid) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-3 (product-grid) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-4 (agent-carousel) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (agent-carousel) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (agent-carousel) | `grid.column-gap` | 17px | agent-card-carousel.deviceGeometry.columnGap (17px) | +0px | conform | .cs-modules column |
| sec-4 (agent-carousel) | `grid.column-gap` | 17px | agent-card-carousel.deviceGeometry.columnGap (17px) | +0px | conform | .cs-modules column |
| sec-4 (agent-carousel) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (agent-carousel) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (agent-carousel) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-4 (agent-carousel) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (agent-carousel) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (agent-carousel) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-4 (agent-carousel) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (agent-carousel) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (agent-carousel) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-4 (agent-carousel) | `card.body-to-actions` | 32px | agent-card-carousel.deviceGeometry.cardActionGap (32px) | +0px | conform | min across 1 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-4 (agent-carousel) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-4 (agent-carousel) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-4 (agent-carousel) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-4 (agent-carousel) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-4 (agent-carousel) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-5 (integration-banner) | `section.pad-top` | 64px | integration-collage-banner.bandPadding.top (64px) | +0px | conform |  |
| sec-5 (integration-banner) | `section.pad-bottom` | 24px | integration-collage-banner.bandPadding.bottom (24px) | +0px | conform |  |
| sec-5 (integration-banner) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-split-body |
| sec-5 (integration-banner) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-5 (integration-banner) | `strip.gap` | 20px | integration-collage-banner.strip.gap.media (20px) | +0px | conform | median of 5 inter-mark gaps |
| sec-5 (integration-banner) | `actions.alignment` | 0px | centered (0px) | +0px | conform | stamped start; painted edges vs column 0px / 224px (column = widest sibling) |
| sec-5 (integration-banner) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-5 (integration-banner) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-6 (case-study-header) | `section.pad-top` | 64px | case-study-header-rail.bandPadding.top (64px) | +0px | conform |  |
| sec-6 (case-study-header) | `section.pad-bottom` | 0px | case-study-header-rail.bandPadding.bottom (0px) | +0px | conform |  |
| sec-6 (case-study-header) | `block.row-gap` | 32px | block-to-block (40px) | -8px | drift | .cs-flow |
| sec-6 (case-study-header) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-6 (case-study-header) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-6 (case-study-header) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-7 (testimonial-tabs) | `section.pad-top` | 40px | testimonial-tab-stats.bandPadding.top (40px) | +0px | conform |  |
| sec-7 (testimonial-tabs) | `section.pad-bottom` | 24px | testimonial-tab-stats.bandPadding.bottom (24px) | +0px | conform |  |
| sec-7 (testimonial-tabs) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-7 (testimonial-tabs) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-8 (badge-row) | `section.pad-top` | 40px | award-badge-row.bandPadding.top (40px) | +0px | conform |  |
| sec-8 (badge-row) | `section.pad-bottom` | 96px | award-badge-row.bandPadding.bottom (96px) | +0px | conform |  |
| sec-8 (badge-row) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-8 (badge-row) | `strip.gap` | 12px | award-badge-row.strip.gap.media (12px) | +0px | conform | median of 5 inter-mark gaps |
| sec-8 (badge-row) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-8 (badge-row) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-9 (closing-cta) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-9 (closing-cta) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-9 (closing-cta) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-conversion |
| sec-9 (closing-cta) | `actions.item-gap` | 24px | closing-cta-dark.actionGroup.gap (24px) | +0px | conform | median of 1 inter-action gap(s) |
| sec-9 (closing-cta) | `actions.alignment` | 0px | centered (0px) | +0px | conform | stamped start; painted edges vs column 0px / 659px (column = widest sibling) |
| sec-9 (closing-cta) | `container.stack-width` | 992px | closing-cta-dark.stackMeasure (992px) | +0px | conform | side-anchored: acting column = widest capped text child |
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
| sec-0→sec-1 (hero→logo-wall) | `section.seam` | 240px | case-study-header-rail.bandPadding.top+hero-photo-overlay.bandPadding.bottom (240px) | +0px | conform |  |
| sec-1→sec-2 (logo-wall→platform-carousel) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-2→sec-3 (platform-carousel→product-grid) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-3→sec-4 (product-grid→agent-carousel) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-4→sec-5 (agent-carousel→integration-banner) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-5→sec-6 (integration-banner→case-study-header) | `section.seam` | 88px | testimonial-tab-stats.bandPadding.bottom+case-study-header-rail.bandPadding.top (88px) | +0px | conform |  |
| sec-6→sec-7 (case-study-header→testimonial-tabs) | `section.seam` | 40px | case-study-header-rail.bandPadding.bottom+award-badge-row.bandPadding.top (40px) | +0px | conform |  |
| sec-7→sec-8 (testimonial-tabs→badge-row) | `section.seam` | 64px | case-study-header-rail.bandPadding.bottom+case-study-header-rail.bandPadding.top (64px) | +0px | conform |  |
| sec-8→sec-9 (badge-row→closing-cta) | `section.seam` | 160px | case-study-header-rail.bandPadding.top+award-badge-row.bandPadding.bottom (160px) | +0px | conform |  |
| sec-9→sec-10 (closing-cta→closing-bookend) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |

## compose/components

`runs/hubspot-v2/brand/compose/components/index.html` (mtime 2026-07-14 15:37:38)

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|

### Skipped (absent/inapplicable anatomy)

- — (—): whole lane — no composed sections (div.cs-surface[data-layout] > section.cs-section) — not a composed lane

