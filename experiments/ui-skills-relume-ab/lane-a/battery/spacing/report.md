# Spacing-conformance baseline report

Generated 2026-07-18T23:36:25Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| lane-a | 2026-07-19 00:35:53 | 69 | 62 | 0 | 1 | 0 | 6 | **1** |

## lane-a

`/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/ui-skills-relume-ab/lane-a/index.html` (mtime 2026-07-19 00:35:53)

### Top offenders (hard fails, ranked frequency x magnitude)

| # | relationship | measured | expected | Δ | hits | where |
|---|---|---|---|---|---|---|
| 1 | `card.body-to-actions` | ~14.4px | body-to-cta (40px) | 25.6px | 1 | sec-4(pricing) |

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-6(closing-bookend) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

15 measured-fact · 0 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (hero) | 14px x3 | measured | type fact 14px | c-caption, c-eyebrow |
| type | sec-1 (story) | 14px x3 | measured | type fact 14px | c-caption |
| type | sec-4 (pricing) | 14px x3 | measured | type fact 14px | c-caption |
| type | sec-6 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (hero) | 16px x2 | measured | type fact 16px | c-paragraph |
| type | sec-1 (story) | 16px x3 | measured | type fact 16px | c-paragraph |
| type | sec-3 (testimonial) | 16px x1 | measured | type fact 16px | c-paragraph |
| type | sec-4 (pricing) | 16px x3 | measured | type fact 16px | c-paragraph |
| type | sec-5 (closing) | 16px x2 | measured | type fact 16px | c-button, c-button.c-button--secondary |
| type | sec-0 (hero) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-1 (story) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-2 (results) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-4 (pricing) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-5 (closing) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-0 (hero) | 80px x1 | measured | type fact 80px | c-heading.c-heading--display |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (hero) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (hero) | `header.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform | .c-header |
| sec-0 (hero) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-0 (hero) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-0 (hero) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (hero) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (hero) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-0 (hero) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (story) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (story) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (story) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-1 (story) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-1 (story) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (story) | `card.media-to-content` | 31.99px | panel-padding (32px) | -0.01px | conform | full-bleed well seam |
| sec-1 (story) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (story) | `card.media-to-content` | 31.99px | panel-padding (32px) | -0.01px | conform | full-bleed well seam |
| sec-1 (story) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (story) | `card.media-to-content` | 31.99px | panel-padding (32px) | -0.01px | conform | full-bleed well seam |
| sec-1 (story) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (story) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-2 (results) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (results) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (results) | `block.header-to-content` | 40px | block-to-block (40px) | +0px | conform | .cs-flow |
| sec-2 (results) | `stat.column-gap` | 80px | column-to-column (80px) | +0px | conform | .cs-stat-band column |
| sec-2 (results) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-2 (results) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-3 (testimonial) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-3 (testimonial) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-3 (testimonial) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-3 (testimonial) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-4 (pricing) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (pricing) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (pricing) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (pricing) | `card.media-to-content` | 31.99px | panel-padding (32px) | -0.01px | conform | full-bleed well seam |
| sec-4 (pricing) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (pricing) | `card.media-to-content` | 31.98px | panel-padding (32px) | -0.02px | conform | full-bleed well seam |
| sec-4 (pricing) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (pricing) | `card.media-to-content` | 31.98px | panel-padding (32px) | -0.02px | conform | full-bleed well seam |
| sec-4 (pricing) | `card.body-to-actions` | 14.39px | body-to-cta (40px) | -25.61px | **wrong-step** | min across 3 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-4 (pricing) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-4 (pricing) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-5 (closing) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (closing) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (closing) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-conversion |
| sec-5 (closing) | `actions.item-gap` | 24px | closing-cta-dark.actionGroup.gap (24px) | +0px | conform | median of 1 inter-action gap(s) |
| sec-5 (closing) | `actions.alignment` | 0px | centered (0px) | +0px | conform | stamped start; painted edges vs column 0px / 659px (column = widest sibling) |
| sec-5 (closing) | `container.stack-width` | 992px | closing-cta-dark.stackMeasure (992px) | +0px | conform | side-anchored: acting column = widest capped text child |
| sec-5 (closing) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-6 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-6 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-6 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-6 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-6 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-6 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-6 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-6 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-6 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-6 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-6 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-6 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-6 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-6 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (hero→story) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-1→sec-2 (story→results) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-2→sec-3 (results→testimonial) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-3→sec-4 (testimonial→pricing) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-4→sec-5 (pricing→closing) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-5→sec-6 (closing→closing-bookend) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-2 (results): .c-stat pair — no non-stat sibling gaps in the block
- sec-2 (results): .c-stat pair — no non-stat sibling gaps in the block
- sec-4 (pricing): .cs-modules — staggered editorial grid (no uniform row/column gap)

