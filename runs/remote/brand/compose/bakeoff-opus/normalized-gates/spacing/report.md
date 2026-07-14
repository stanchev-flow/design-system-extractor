# Spacing-conformance baseline report

Generated 2026-07-10T19:05:26Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/bakeoff-opus | 2026-07-10 20:01:34 | 157 | 156 | 0 | 0 | 1 | 0 | **1** |

## compose/bakeoff-opus

`runs/remote/brand/compose/bakeoff-opus/index.html` (mtime 2026-07-10 20:01:34)

### Top offenders (hard fails, ranked frequency x magnitude)

| # | relationship | measured | expected | Δ | hits | where |
|---|---|---|---|---|---|---|
| 1 | `container.stack-width` | ~736px | header-measure (720px) | 16px | 1 | sec-9(lead-form) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (hero) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (hero) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (hero) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (hero) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (hero) | `split.column-gap` | 48px | column-to-column (48px) | +0px | conform | hero panel columns |
| sec-0 (hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-left (computed) |
| sec-0 (hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-top (computed) |
| sec-0 (hero) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-0 (hero) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-1 (problem) | `section.pad-top` | 64px | infra-proof-split.bandPadding.top (64px) | +0px | conform |  |
| sec-1 (problem) | `section.pad-bottom` | 64px | infra-proof-split.bandPadding.bottom (64px) | +0px | conform |  |
| sec-1 (problem) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-split-body |
| sec-1 (problem) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-1 (problem) | `split.column-gap` | 97.44px | infra-proof-split.columnGap(note) (101px) | -3.56px | conform | split columns |
| sec-1 (problem) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-1 (problem) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-2 (product-value) | `section.pad-top` | 64px | feature-accordion-deep-accent.bandPadding.top (64px) | +0px | conform |  |
| sec-2 (product-value) | `section.pad-bottom` | 64px | feature-accordion-deep-accent.bandPadding.bottom (64px) | +0px | conform |  |
| sec-2 (product-value) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-acc-col--lead |
| sec-2 (product-value) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-2 (product-value) | `split.column-gap` | 101px | feature-accordion-deep-accent.deviceGeometry.columnGap (101px) | +0px | conform | accordion split columns |
| sec-2 (product-value) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (product-value) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (product-value) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (product-value) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform | open item |
| sec-2 (product-value) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (product-value) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (product-value) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (product-value) | `container.width` | 1168px | feature-accordion-deep-accent.deviceGeometry.contentSpan (1168px) | +0px | conform |  |
| sec-2 (product-value) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 136px / 136px |
| sec-3 (capabilities) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (capabilities) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (capabilities) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-3 (capabilities) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (capabilities) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (capabilities) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (capabilities) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (capabilities) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (capabilities) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (capabilities) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (capabilities) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (capabilities) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (capabilities) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (capabilities) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (capabilities) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (capabilities) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (capabilities) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (capabilities) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-3 (capabilities) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-4 (how-it-works) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (how-it-works) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (how-it-works) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-4 (how-it-works) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-4 (how-it-works) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-4 (how-it-works) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (how-it-works) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (how-it-works) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-4 (how-it-works) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-4 (how-it-works) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (how-it-works) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (how-it-works) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-4 (how-it-works) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-4 (how-it-works) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (how-it-works) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (how-it-works) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-4 (how-it-works) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-4 (how-it-works) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-4 (how-it-works) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-5 (comparison) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (comparison) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (comparison) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-split-intro |
| sec-5 (comparison) | `split.column-gap` | 48px | column-to-column (48px) | +0px | conform | split columns |
| sec-5 (comparison) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-5 (comparison) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-6 (proof) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (proof) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (proof) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-6 (proof) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-6 (proof) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-6 (proof) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-6 (proof) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-6 (proof) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-6 (proof) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-6 (proof) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-6 (proof) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-6 (proof) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-6 (proof) | `card.body-to-author` | 64px | quote-to-attribution (64px) | +0px | conform | min across 3 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-6 (proof) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-6 (proof) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-7 (conversion-beat) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-7 (conversion-beat) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-7 (conversion-beat) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-conversion |
| sec-7 (conversion-beat) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-7 (conversion-beat) | `container.centering` | 0.02px | centered (0px) | +0.02px | conform | gutters 135.38px / 135.36px |
| sec-8 (faq) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (faq) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (faq) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-faq |
| sec-8 (faq) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
| sec-8 (faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (faq) | `container.stack-width` | 720px | header-measure (720px) | +0px | conform |  |
| sec-8 (faq) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 360px / 360px |
| sec-9 (lead-form) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-9 (lead-form) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-9 (lead-form) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-conversion |
| sec-9 (lead-form) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-conversion |
| sec-9 (lead-form) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-9 (lead-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-9 (lead-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-9 (lead-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (lead-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (lead-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (lead-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (lead-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (lead-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (lead-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (lead-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (lead-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (lead-form) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-9 (lead-form) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-9 (lead-form) | `container.stack-width` | 736px | header-measure (720px) | +16px | **off-ladder** |  |
| sec-9 (lead-form) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 352px / 352px |
| sec-10 (closing-bookend) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-10 (closing-bookend) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-10 (closing-bookend) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-10 (closing-bookend) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-10 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 9 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 5 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 2 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 11 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 5 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 3 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 8 link gaps |
| sec-10 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 7 link gaps |
| sec-10 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-10 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-10 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-10 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-10 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-0→sec-1 (hero→problem) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-1→sec-2 (problem→product-value) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |
| sec-2→sec-3 (product-value→capabilities) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-3→sec-4 (capabilities→how-it-works) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-4→sec-5 (how-it-works→comparison) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-5→sec-6 (comparison→proof) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-6→sec-7 (proof→conversion-beat) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-7→sec-8 (conversion-beat→faq) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-8→sec-9 (faq→lead-form) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-9→sec-10 (lead-form→closing-bookend) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-6 (proof): .cs-modules — staggered editorial grid (no uniform row/column gap)

