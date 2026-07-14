# Spacing-conformance baseline report

Generated 2026-07-10T19:05:26Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/bakeoff-sol | 2026-07-10 20:01:40 | 176 | 173 | 0 | 2 | 1 | 0 | **3** |

## compose/bakeoff-sol

`runs/remote/brand/compose/bakeoff-sol/index.html` (mtime 2026-07-10 20:01:40)

### Top offenders (hard fails, ranked frequency x magnitude)

| # | relationship | measured | expected | Δ | hits | where |
|---|---|---|---|---|---|---|
| 1 | `container.width` | ~720px | container-span (1169.28px) | 449.3px | 1 | sec-6(remote-customer-perspectives) |
| 2 | `header.heading-to-body` | ~64px | heading-to-body (16px) | 48px | 1 | sec-5(workflow-comparison) |
| 3 | `container.stack-width` | ~736px | header-measure (720px) | 16px | 1 | sec-9(qualified-demo-request) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (workforce-intelligence-hero) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (workforce-intelligence-hero) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (workforce-intelligence-hero) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (workforce-intelligence-hero) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (workforce-intelligence-hero) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (workforce-intelligence-hero) | `split.column-gap` | 48px | column-to-column (48px) | +0px | conform | hero panel columns |
| sec-0 (workforce-intelligence-hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-left (computed) |
| sec-0 (workforce-intelligence-hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-top (computed) |
| sec-0 (workforce-intelligence-hero) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-0 (workforce-intelligence-hero) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-1 (reporting-gap) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (reporting-gap) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (reporting-gap) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-1 (reporting-gap) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-1 (reporting-gap) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (reporting-gap) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-1 (reporting-gap) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-1 (reporting-gap) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-1 (reporting-gap) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (reporting-gap) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-1 (reporting-gap) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-1 (reporting-gap) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-1 (reporting-gap) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (reporting-gap) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-1 (reporting-gap) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-1 (reporting-gap) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-1 (reporting-gap) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-1 (reporting-gap) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-2 (decision-layer-capabilities) | `section.pad-top` | 64px | feature-accordion-deep-accent.bandPadding.top (64px) | +0px | conform |  |
| sec-2 (decision-layer-capabilities) | `section.pad-bottom` | 64px | feature-accordion-deep-accent.bandPadding.bottom (64px) | +0px | conform |  |
| sec-2 (decision-layer-capabilities) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-acc-col--lead |
| sec-2 (decision-layer-capabilities) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-2 (decision-layer-capabilities) | `split.column-gap` | 101px | feature-accordion-deep-accent.deviceGeometry.columnGap (101px) | +0px | conform | accordion split columns |
| sec-2 (decision-layer-capabilities) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (decision-layer-capabilities) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (decision-layer-capabilities) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (decision-layer-capabilities) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform | open item |
| sec-2 (decision-layer-capabilities) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (decision-layer-capabilities) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (decision-layer-capabilities) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (decision-layer-capabilities) | `container.width` | 1168px | feature-accordion-deep-accent.deviceGeometry.contentSpan (1168px) | +0px | conform |  |
| sec-2 (decision-layer-capabilities) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 136px / 136px |
| sec-3 (how-workforce-intelligence-works) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-3 (how-workforce-intelligence-works) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-3 (how-workforce-intelligence-works) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (how-workforce-intelligence-works) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (how-workforce-intelligence-works) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (how-workforce-intelligence-works) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (how-workforce-intelligence-works) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (how-workforce-intelligence-works) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (how-workforce-intelligence-works) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (how-workforce-intelligence-works) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (how-workforce-intelligence-works) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-3 (how-workforce-intelligence-works) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-4 (leadership-views) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (leadership-views) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (leadership-views) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-4 (leadership-views) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-4 (leadership-views) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (leadership-views) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (leadership-views) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-4 (leadership-views) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-4 (leadership-views) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (leadership-views) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (leadership-views) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-4 (leadership-views) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-4 (leadership-views) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-4 (leadership-views) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-4 (leadership-views) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-4 (leadership-views) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-4 (leadership-views) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-4 (leadership-views) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-5 (workflow-comparison) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (workflow-comparison) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (workflow-comparison) | `header.heading-to-body` | 64px | heading-to-body (16px) | +48px | **wrong-step** | .cs-flow |
| sec-5 (workflow-comparison) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-5 (workflow-comparison) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-5 (workflow-comparison) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-5 (workflow-comparison) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-6 (remote-customer-perspectives) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (remote-customer-perspectives) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (remote-customer-perspectives) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-6 (remote-customer-perspectives) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-6 (remote-customer-perspectives) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-6 (remote-customer-perspectives) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-6 (remote-customer-perspectives) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-6 (remote-customer-perspectives) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-6 (remote-customer-perspectives) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-6 (remote-customer-perspectives) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-6 (remote-customer-perspectives) | `card.body-to-author` | 64px | quote-to-attribution (64px) | +0px | conform | min across 2 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-6 (remote-customer-perspectives) | `container.width` | 720px | container-span (1169.28px) | -449.28px | **wrong-step** |  |
| sec-6 (remote-customer-perspectives) | `container.centering` | 0.04px | centered (0px) | +0.04px | conform | gutters 359.98px / 360.02px |
| sec-7 (operational-trust) | `section.pad-top` | 64px | infra-proof-split.bandPadding.top (64px) | +0px | conform |  |
| sec-7 (operational-trust) | `section.pad-bottom` | 64px | infra-proof-split.bandPadding.bottom (64px) | +0px | conform |  |
| sec-7 (operational-trust) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-split-body |
| sec-7 (operational-trust) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-7 (operational-trust) | `split.column-gap` | 97.44px | infra-proof-split.columnGap(note) (101px) | -3.56px | conform | split columns |
| sec-7 (operational-trust) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-7 (operational-trust) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-8 (workforce-intelligence-faq) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (workforce-intelligence-faq) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (workforce-intelligence-faq) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-faq |
| sec-8 (workforce-intelligence-faq) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-faq |
| sec-8 (workforce-intelligence-faq) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
| sec-8 (workforce-intelligence-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (workforce-intelligence-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (workforce-intelligence-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (workforce-intelligence-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (workforce-intelligence-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (workforce-intelligence-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (workforce-intelligence-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (workforce-intelligence-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (workforce-intelligence-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (workforce-intelligence-faq) | `container.stack-width` | 720px | header-measure (720px) | +0px | conform |  |
| sec-8 (workforce-intelligence-faq) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 360px / 360px |
| sec-9 (qualified-demo-request) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-conversion |
| sec-9 (qualified-demo-request) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-conversion |
| sec-9 (qualified-demo-request) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-9 (qualified-demo-request) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-9 (qualified-demo-request) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-9 (qualified-demo-request) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-9 (qualified-demo-request) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (qualified-demo-request) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (qualified-demo-request) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (qualified-demo-request) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (qualified-demo-request) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (qualified-demo-request) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-9 (qualified-demo-request) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-9 (qualified-demo-request) | `container.stack-width` | 736px | header-measure (720px) | +16px | **off-ladder** |  |
| sec-9 (qualified-demo-request) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 352px / 352px |
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
| sec-0→sec-1 (workforce-intelligence-hero→reporting-gap) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-1→sec-2 (reporting-gap→decision-layer-capabilities) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-2→sec-3 (decision-layer-capabilities→how-workforce-intelligence-works) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-3→sec-4 (how-workforce-intelligence-works→leadership-views) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-4→sec-5 (leadership-views→workflow-comparison) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-5→sec-6 (workflow-comparison→remote-customer-perspectives) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-6→sec-7 (remote-customer-perspectives→operational-trust) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-7→sec-8 (operational-trust→workforce-intelligence-faq) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-8→sec-9 (workforce-intelligence-faq→qualified-demo-request) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-9→sec-10 (qualified-demo-request→closing-bookend) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-1 (reporting-gap): .cs-modules — staggered editorial grid (no uniform row/column gap)
- sec-3 (how-workforce-intelligence-works): .cs-modules — staggered editorial grid (no uniform row/column gap)
- sec-4 (leadership-views): .cs-modules — staggered editorial grid (no uniform row/column gap)
- sec-6 (remote-customer-perspectives): .cs-modules — staggered editorial grid (no uniform row/column gap)

