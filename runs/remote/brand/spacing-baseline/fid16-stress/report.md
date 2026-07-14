# Spacing-conformance baseline report

Generated 2026-07-10T18:32:58Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/stress-playbook | 2026-07-10 19:32:21 | 162 | 160 | 0 | 0 | 0 | 2 | **0** |

## compose/stress-playbook

`runs/remote/brand/compose/stress-playbook/index.html` (mtime 2026-07-10 19:32:21)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `header.body-to-meta` | 16px x2 | heading-to-body (16px) | sec-0(pb-hero), sec-10(pb-form) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (pb-hero) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (pb-hero) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (pb-hero) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (pb-hero) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (pb-hero) | `header.body-to-meta` | 16px | — | — | unmapped | .cs-hero-panel-content |
| sec-0 (pb-hero) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (pb-hero) | `split.column-gap` | 48px | column-to-column (48px) | +0px | conform | hero panel columns |
| sec-0 (pb-hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-left (computed) |
| sec-0 (pb-hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-top (computed) |
| sec-0 (pb-hero) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-0 (pb-hero) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-1 (pb-stats) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (pb-stats) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (pb-stats) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-flow |
| sec-1 (pb-stats) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-flow |
| sec-1 (pb-stats) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-1 (pb-stats) | `stat.column-gap` | 48px | column-to-column (48px) | +0px | conform | .cs-stat-band column |
| sec-1 (pb-stats) | `stat.column-gap` | 48px | column-to-column (48px) | +0px | conform | .cs-stat-band column |
| sec-1 (pb-stats) | `stat.column-gap` | 48px | column-to-column (48px) | +0px | conform | .cs-stat-band column |
| sec-1 (pb-stats) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-1 (pb-stats) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-2 (pb-statement) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-2 (pb-statement) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-2 (pb-statement) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-2 (pb-statement) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-3 (pb-chapters) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (pb-chapters) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (pb-chapters) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-3 (pb-chapters) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-3 (pb-chapters) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (pb-chapters) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (pb-chapters) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (pb-chapters) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (pb-chapters) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (pb-chapters) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (pb-chapters) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (pb-chapters) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (pb-chapters) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (pb-chapters) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (pb-chapters) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (pb-chapters) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (pb-chapters) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (pb-chapters) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (pb-chapters) | `card.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | min across 3 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-3 (pb-chapters) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-3 (pb-chapters) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-4 (pb-process) | `section.pad-top` | 64px | feature-accordion-deep-accent.bandPadding.top (64px) | +0px | conform |  |
| sec-4 (pb-process) | `section.pad-bottom` | 64px | feature-accordion-deep-accent.bandPadding.bottom (64px) | +0px | conform |  |
| sec-4 (pb-process) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-split-intro |
| sec-4 (pb-process) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-acc-col--lead |
| sec-4 (pb-process) | `block.row-gap` | 64px | block-to-block (64px) | +0px | conform | .cs-acc-col--lead |
| sec-4 (pb-process) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-4 (pb-process) | `split.column-gap` | 101px | feature-accordion-deep-accent.deviceGeometry.columnGap (101px) | +0px | conform | accordion split columns |
| sec-4 (pb-process) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-4 (pb-process) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-4 (pb-process) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-4 (pb-process) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform | open item |
| sec-4 (pb-process) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-4 (pb-process) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-4 (pb-process) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-4 (pb-process) | `container.width` | 1168px | feature-accordion-deep-accent.deviceGeometry.contentSpan (1168px) | +0px | conform |  |
| sec-4 (pb-process) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 136px / 136px |
| sec-5 (pb-compare) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (pb-compare) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (pb-compare) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-split-intro |
| sec-5 (pb-compare) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-split-intro |
| sec-5 (pb-compare) | `split.column-gap` | 48px | column-to-column (48px) | +0px | conform | split columns |
| sec-5 (pb-compare) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-5 (pb-compare) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-6 (pb-banner) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (pb-banner) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (pb-banner) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-conversion |
| sec-6 (pb-banner) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-6 (pb-banner) | `container.centering` | 0.02px | centered (0px) | +0.02px | conform | gutters 135.38px / 135.36px |
| sec-7 (pb-stories) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-7 (pb-stories) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-7 (pb-stories) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-7 (pb-stories) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-7 (pb-stories) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-7 (pb-stories) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-7 (pb-stories) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-7 (pb-stories) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-7 (pb-stories) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-7 (pb-stories) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-7 (pb-stories) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-7 (pb-stories) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-7 (pb-stories) | `card.body-to-author` | 64px | quote-to-attribution (64px) | +0px | conform | min across 3 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-7 (pb-stories) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-7 (pb-stories) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-8 (pb-badges) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (pb-badges) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (pb-badges) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-8 (pb-badges) | `block.row-gap` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-8 (pb-badges) | `block.content-to-actions` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-8 (pb-badges) | `strip.gap` | 64px | badge-award-strip.strip.gap.badges (64px) | +0px | conform | median of 5 inter-mark gaps |
| sec-8 (pb-badges) | `strip.gap` | 32px | badge-award-strip.strip.gap.ratings (32px) | +0px | conform | median of 2 inter-mark gaps |
| sec-8 (pb-badges) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-8 (pb-badges) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-9 (pb-faq) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-9 (pb-faq) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-9 (pb-faq) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-faq |
| sec-9 (pb-faq) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
| sec-9 (pb-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-9 (pb-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-9 (pb-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-9 (pb-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-9 (pb-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-9 (pb-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-9 (pb-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-9 (pb-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-9 (pb-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-9 (pb-faq) | `container.stack-width` | 720px | header-measure (720px) | +0px | conform |  |
| sec-9 (pb-faq) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 360px / 360px |
| sec-10 (pb-form) | `section.pad-top` | 80px | cta-closing-noise.bandPadding.top (80px) | +0px | conform |  |
| sec-10 (pb-form) | `section.pad-bottom` | 80px | cta-closing-noise.bandPadding.bottom (80px) | +0px | conform |  |
| sec-10 (pb-form) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-conversion |
| sec-10 (pb-form) | `header.body-to-meta` | 16px | — | — | unmapped | .cs-conversion |
| sec-10 (pb-form) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-conversion |
| sec-10 (pb-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-10 (pb-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-10 (pb-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-10 (pb-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-10 (pb-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-10 (pb-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-10 (pb-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-10 (pb-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-10 (pb-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-10 (pb-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-10 (pb-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-10 (pb-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-10 (pb-form) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-10 (pb-form) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-10 (pb-form) | `container.stack-width` | 870px | cta-closing-noise.stackMeasure (870px) | +0px | conform |  |
| sec-10 (pb-form) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 285px / 285px |
| sec-11 (closing-bookend) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-11 (closing-bookend) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-11 (closing-bookend) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-11 (closing-bookend) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-11 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 9 link gaps |
| sec-11 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 5 link gaps |
| sec-11 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 2 link gaps |
| sec-11 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 11 link gaps |
| sec-11 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 5 link gaps |
| sec-11 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 3 link gaps |
| sec-11 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 8 link gaps |
| sec-11 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 7 link gaps |
| sec-11 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-11 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-11 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-11 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-11 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-0→sec-1 (pb-hero→pb-stats) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-1→sec-2 (pb-stats→pb-statement) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-2→sec-3 (pb-statement→pb-chapters) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-3→sec-4 (pb-chapters→pb-process) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-4→sec-5 (pb-process→pb-compare) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-5→sec-6 (pb-compare→pb-banner) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-6→sec-7 (pb-banner→pb-stories) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-7→sec-8 (pb-stories→pb-badges) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-8→sec-9 (pb-badges→pb-faq) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-9→sec-10 (pb-faq→pb-form) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |
| sec-10→sec-11 (pb-form→closing-bookend) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-7 (pb-stories): .cs-modules — staggered editorial grid (no uniform row/column gap)

