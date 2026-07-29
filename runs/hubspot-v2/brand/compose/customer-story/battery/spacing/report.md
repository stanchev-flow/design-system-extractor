# Spacing-conformance baseline report

Generated 2026-07-28T23:52:12Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/customer-story | 2026-07-17 18:46:49 | 88 | 82 | 0 | 0 | 0 | 6 | **0** |

## compose/customer-story

`runs/hubspot-v2/brand/compose/customer-story/index.html` (mtime 2026-07-17 18:46:49)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-7(closing-bookend) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

18 measured-fact · 0 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (hero) | 14px x3 | measured | type fact 14px | c-caption, c-eyebrow |
| type | sec-1 (story) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-4 (more-stories) | 14px x2 | measured | type fact 14px | c-eyebrow |
| type | sec-7 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (hero) | 16px x2 | measured | type fact 16px | c-paragraph |
| type | sec-1 (story) | 16px x4 | measured | type fact 16px | c-button.c-button--secondary, c-paragraph |
| type | sec-3 (quote) | 16px x1 | measured | type fact 16px | c-paragraph |
| type | sec-4 (more-stories) | 16px x2 | measured | type fact 16px | c-paragraph |
| type | sec-6 (closing) | 16px x2 | measured | type fact 16px | c-button, c-button.c-button--secondary |
| type | sec-1 (story) | 18px x3 | measured | type fact 18px | c-heading.c-heading--h5 |
| type | sec-4 (more-stories) | 18px x2 | measured | type fact 18px | c-heading.c-heading--h5 |
| type | sec-5 (logos) | 22px x1 | measured | type fact 22px | c-heading.c-heading--h4 |
| type | sec-0 (hero) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-1 (story) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-2 (results) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-4 (more-stories) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-6 (closing) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
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
| sec-1 (story) | `grid.row-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules row |
| sec-1 (story) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (story) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-1 (story) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-1 (story) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (story) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-1 (story) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-1 (story) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (story) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-1 (story) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-1 (story) | `actions.alignment` | 0px | centered (0px) | +0px | conform | stamped start; painted edges vs column 0px / 187px (column = widest sibling) |
| sec-1 (story) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-1 (story) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-1 (story) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-1 (story) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (story) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-2 (results) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (results) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (results) | `block.header-to-content` | 40px | block-to-block (40px) | +0px | conform | .cs-flow |
| sec-2 (results) | `stat.column-gap` | 80px | column-to-column (80px) | +0px | conform | .cs-stat-band column |
| sec-2 (results) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-2 (results) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-3 (quote) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-3 (quote) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-3 (quote) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-3 (quote) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-4 (more-stories) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (more-stories) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (more-stories) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-4 (more-stories) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (more-stories) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (more-stories) | `card.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform |  |
| sec-4 (more-stories) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-4 (more-stories) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (more-stories) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (more-stories) | `card.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform |  |
| sec-4 (more-stories) | `card.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform |  |
| sec-4 (more-stories) | `card.body-to-actions` | 48px | product-grid-split.deviceGeometry.cardActionGap (48px) | +0px | conform | min across 2 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-4 (more-stories) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-4 (more-stories) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-4 (more-stories) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-4 (more-stories) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-5 (logos) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (logos) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-5 (logos) | `block.header-to-content` | 40px | block-to-block (40px) | +0px | conform | .cs-flow |
| sec-5 (logos) | `strip.gap` | 69px | logo-proof-strip.strip.gap.logos (69px) | +0px | conform | median of 4 inter-mark gaps |
| sec-5 (logos) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-5 (logos) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-6 (closing) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-6 (closing) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-6 (closing) | `header.body-to-actions` | 40px | body-to-cta (40px) | +0px | conform | .cs-conversion |
| sec-6 (closing) | `actions.item-gap` | 24px | closing-cta-dark.actionGroup.gap (24px) | +0px | conform | median of 1 inter-action gap(s) |
| sec-6 (closing) | `actions.alignment` | 0px | centered (0px) | +0px | conform | stamped start; painted edges vs column 0px / 659px (column = widest sibling) |
| sec-6 (closing) | `container.stack-width` | 992px | closing-cta-dark.stackMeasure (992px) | +0px | conform | side-anchored: acting column = widest capped text child |
| sec-6 (closing) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-7 (closing-bookend) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-7 (closing-bookend) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-7 (closing-bookend) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-7 (closing-bookend) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-7 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-7 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 8 link gaps |
| sec-7 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-7 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 7 link gaps |
| sec-7 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 1 link gaps |
| sec-7 (closing-bookend) | `footer.link-gap` | 4px | — | — | unmapped | median of 4 link gaps |
| sec-7 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-7 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-7 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-7 (closing-bookend) | `footer.column-gap` | 52px | footer.grid.columnGap (52px) | +0px | conform | directory columns |
| sec-0→sec-1 (hero→story) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-1→sec-2 (story→results) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-2→sec-3 (results→quote) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-3→sec-4 (quote→more-stories) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-4→sec-5 (more-stories→logos) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-5→sec-6 (logos→closing) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-6→sec-7 (closing→closing-bookend) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-2 (results): .c-stat pair — no non-stat sibling gaps in the block
- sec-2 (results): .c-stat pair — no non-stat sibling gaps in the block

