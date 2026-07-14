# Spacing-conformance baseline report

Generated 2026-07-14T20:18:46Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/style-bakeoff-editorial-magazine/product-launch | 2026-07-14 21:16:53 | 75 | 67 | 1 | 0 | 0 | 7 | **0** |

## compose/style-bakeoff-editorial-magazine/product-launch

`/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/style-bakeoff-editorial-magazine/product-launch/index.html` (mtime 2026-07-14 21:16:53)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-5(closing-bookend) |
| `header.body-to-meta` | 40px x1 | section-y-sm (40px) | sec-3(belief) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

14 measured-fact · 1 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (hero) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-1 (what-shipped) | 14px x5 | measured | type fact 14px | c-eyebrow |
| type | sec-3 (belief) | 14px x1 | measured | type fact 14px | c-caption |
| type | sec-5 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (hero) | 16px x2 | measured | type fact 16px | c-button, c-paragraph |
| type | sec-1 (what-shipped) | 16px x4 | measured | type fact 16px | c-paragraph |
| type | sec-2 (beta-proof) | 16px x1 | measured | type fact 16px | c-paragraph |
| type | sec-3 (belief) | 16px x1 | measured | type fact 16px | c-paragraph |
| type | sec-4 (close) | 16px x2 | measured | type fact 16px | c-button, c-paragraph |
| type | sec-1 (what-shipped) | 18px x4 | measured | type fact 18px | c-heading.c-heading--h5 |
| type | sec-0 (hero) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-1 (what-shipped) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-2 (beta-proof) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-4 (close) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| space | sec-3 (belief) | 40px x1 | on-scale | derived step 40px | header.body-to-meta |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (hero) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (hero) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-split-body |
| sec-0 (hero) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-split-body |
| sec-0 (hero) | `header.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform | .c-header |
| sec-0 (hero) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-0 (hero) | `actions.alignment` | 0px | centered (0px) | +0px | conform | stamped start; painted edges vs column 0px / 272px (column = widest sibling) |
| sec-0 (hero) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (hero) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-0 (hero) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (what-shipped) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (what-shipped) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (what-shipped) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-1 (what-shipped) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-1 (what-shipped) | `grid.row-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules row |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-1 (what-shipped) | `card.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform |  |
| sec-1 (what-shipped) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-1 (what-shipped) | `card.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform |  |
| sec-1 (what-shipped) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-1 (what-shipped) | `card.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform |  |
| sec-1 (what-shipped) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-1 (what-shipped) | `card.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform |  |
| sec-1 (what-shipped) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-1 (what-shipped) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-1 (what-shipped) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-1 (what-shipped) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-1 (what-shipped) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-1 (what-shipped) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (what-shipped) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-2 (beta-proof) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (beta-proof) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (beta-proof) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-flow |
| sec-2 (beta-proof) | `block.header-to-content` | 40px | block-to-block (40px) | +0px | conform | .cs-flow |
| sec-2 (beta-proof) | `stat.column-gap` | 80px | column-to-column (80px) | +0px | conform | .cs-stat-band column |
| sec-2 (beta-proof) | `stat.column-gap` | 80px | column-to-column (80px) | +0px | conform | .cs-stat-band column |
| sec-2 (beta-proof) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-2 (beta-proof) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-3 (belief) | `section.pad-top` | 40px | testimonial-tab-stats.bandPadding.top (40px) | +0px | conform |  |
| sec-3 (belief) | `section.pad-bottom` | 24px | testimonial-tab-stats.bandPadding.bottom (24px) | +0px | conform |  |
| sec-3 (belief) | `header.body-to-meta` | 40px | — | — | unmapped | .cs-flow |
| sec-3 (belief) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-3 (belief) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-4 (close) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (close) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (close) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-conversion |
| sec-4 (close) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-conversion |
| sec-4 (close) | `container.stack-width` | 992px | closing-cta-dark.stackMeasure (992px) | +0px | conform |  |
| sec-4 (close) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 224px / 224px |
| sec-5 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-5 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-5 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-5 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-5 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-5 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-5 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-5 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-5 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-5 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-5 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-5 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (hero→what-shipped) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-1→sec-2 (what-shipped→beta-proof) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-2→sec-3 (beta-proof→belief) | `section.seam` | 104px | award-badge-row.bandPadding.top+case-study-header-rail.bandPadding.top (104px) | +0px | conform |  |
| sec-3→sec-4 (belief→close) | `section.seam` | 88px | testimonial-tab-stats.bandPadding.bottom+case-study-header-rail.bandPadding.top (88px) | +0px | conform |  |
| sec-4→sec-5 (close→closing-bookend) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-2 (beta-proof): .c-stat pair — no non-stat sibling gaps in the block
- sec-2 (beta-proof): .c-stat pair — no non-stat sibling gaps in the block
- sec-2 (beta-proof): .c-stat pair — no non-stat sibling gaps in the block

