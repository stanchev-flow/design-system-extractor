# Spacing-conformance baseline report

Generated 2026-07-14T15:02:45Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/replica | 2026-07-14 15:37:11 | 138 | 138 | 0 | 0 | 0 | 0 | **0** |
| compose/event-genlaunch | 2026-07-14 15:36:48 | 122 | 120 | 0 | 0 | 0 | 2 | **0** |
| compose/components | 2026-07-14 15:37:40 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |

## compose/replica

`runs/remote/brand/compose/replica/index.html` (mtime 2026-07-14 15:37:11)

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (hero) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (hero) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (hero) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (hero) | `split.column-gap` | 48px | column-to-column (48px) | +0px | conform | hero panel columns |
| sec-0 (hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-left (computed) |
| sec-0 (hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-top (computed) |
| sec-0 (hero) | `actions.item-gap` | 16px | action-group-gap (16px) | +0px | conform | median of 1 inter-action gap(s) |
| sec-0 (hero) | `actions.alignment` | 0px | centered (0px) | +0px | conform | stamped start; painted edges vs column 0px / 205px (column = widest sibling) |
| sec-0 (hero) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-0 (hero) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-1 (logo-wall) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (logo-wall) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (logo-wall) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-1 (logo-wall) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-2 (feature-accordion) | `section.pad-top` | 64px | feature-accordion-deep-accent.bandPadding.top (64px) | +0px | conform |  |
| sec-2 (feature-accordion) | `section.pad-bottom` | 64px | feature-accordion-deep-accent.bandPadding.bottom (64px) | +0px | conform |  |
| sec-2 (feature-accordion) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-acc-col--lead |
| sec-2 (feature-accordion) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-2 (feature-accordion) | `split.column-gap` | 101px | feature-accordion-deep-accent.deviceGeometry.columnGap (101px) | +0px | conform | accordion split columns |
| sec-2 (feature-accordion) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (feature-accordion) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (feature-accordion) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (feature-accordion) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (feature-accordion) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-2 (feature-accordion) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform | open item |
| sec-2 (feature-accordion) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (feature-accordion) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (feature-accordion) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (feature-accordion) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-2 (feature-accordion) | `container.width` | 1168px | feature-accordion-deep-accent.deviceGeometry.contentSpan (1168px) | +0px | conform |  |
| sec-2 (feature-accordion) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 136px / 136px |
| sec-3 (infra-panel) | `section.pad-top` | 64px | infra-proof-split.bandPadding.top (64px) | +0px | conform |  |
| sec-3 (infra-panel) | `section.pad-bottom` | 64px | infra-proof-split.bandPadding.bottom (64px) | +0px | conform |  |
| sec-3 (infra-panel) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-split-body |
| sec-3 (infra-panel) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-3 (infra-panel) | `split.column-gap` | 97.44px | infra-proof-split.columnGap(note) (101px) | -3.56px | conform | split columns |
| sec-3 (infra-panel) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-3 (infra-panel) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-3 (infra-panel) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-4 (banner-cta) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (banner-cta) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (banner-cta) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-conversion |
| sec-4 (banner-cta) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-4 (banner-cta) | `container.centering` | 0.02px | centered (0px) | +0.02px | conform | gutters 135.38px / 135.36px |
| sec-5 (workflow-cards) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (workflow-cards) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (workflow-cards) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-5 (workflow-cards) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-5 (workflow-cards) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-5 (workflow-cards) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-5 (workflow-cards) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-5 (workflow-cards) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-5 (workflow-cards) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-5 (workflow-cards) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-5 (workflow-cards) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-5 (workflow-cards) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-5 (workflow-cards) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-5 (workflow-cards) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-5 (workflow-cards) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-5 (workflow-cards) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-5 (workflow-cards) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-5 (workflow-cards) | `card.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | min across 3 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-5 (workflow-cards) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-5 (workflow-cards) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-5 (workflow-cards) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-5 (workflow-cards) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-5 (workflow-cards) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-5 (workflow-cards) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-6 (partner-logos) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (partner-logos) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (partner-logos) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-flow |
| sec-6 (partner-logos) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-flow |
| sec-6 (partner-logos) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-6 (partner-logos) | `block.content-to-actions` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-6 (partner-logos) | `strip.gap` | 64px | strip-gap (64px) | +0px | conform | median of 3 inter-mark gaps |
| sec-6 (partner-logos) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-6 (partner-logos) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-6 (partner-logos) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-7 (testimonials) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-7 (testimonials) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-7 (testimonials) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-7 (testimonials) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-7 (testimonials) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-7 (testimonials) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-7 (testimonials) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-7 (testimonials) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-7 (testimonials) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-7 (testimonials) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-7 (testimonials) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-7 (testimonials) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-7 (testimonials) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-top |
| sec-7 (testimonials) | `card.mark-to-quote` | 24px | mark-to-quote (24px) | +0px | conform | quote-card mark seam |
| sec-7 (testimonials) | `card.body-to-author` | 64px | quote-to-attribution (64px) | +0px | conform | min across 3 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-7 (testimonials) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-7 (testimonials) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-8 (badge-strip) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (badge-strip) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (badge-strip) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-8 (badge-strip) | `block.row-gap` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-8 (badge-strip) | `block.content-to-actions` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-8 (badge-strip) | `strip.gap` | 64px | badge-award-strip.strip.gap.badges (64px) | +0px | conform | median of 5 inter-mark gaps |
| sec-8 (badge-strip) | `strip.gap` | 32px | badge-award-strip.strip.gap.ratings (32px) | +0px | conform | median of 2 inter-mark gaps |
| sec-8 (badge-strip) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-8 (badge-strip) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-9 (closing-cta) | `section.pad-top` | 80px | cta-closing-noise.bandPadding.top (80px) | +0px | conform |  |
| sec-9 (closing-cta) | `section.pad-bottom` | 80px | cta-closing-noise.bandPadding.bottom (80px) | +0px | conform |  |
| sec-9 (closing-cta) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-conversion |
| sec-9 (closing-cta) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-conversion |
| sec-9 (closing-cta) | `container.stack-width` | 870px | cta-closing-noise.stackMeasure (870px) | +0px | conform |  |
| sec-9 (closing-cta) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 285px / 285px |
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
| sec-0→sec-1 (hero→logo-wall) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-1→sec-2 (logo-wall→feature-accordion) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-2→sec-3 (feature-accordion→infra-panel) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |
| sec-3→sec-4 (infra-panel→banner-cta) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-4→sec-5 (banner-cta→workflow-cards) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-5→sec-6 (workflow-cards→partner-logos) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-6→sec-7 (partner-logos→testimonials) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-7→sec-8 (testimonials→badge-strip) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-8→sec-9 (badge-strip→closing-cta) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |
| sec-9→sec-10 (closing-cta→closing-bookend) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |

## compose/event-genlaunch

`runs/remote/brand/compose/event-genlaunch/index.html` (mtime 2026-07-14 15:36:48)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `header.body-to-meta` | 16px x2 | heading-to-body (16px) | sec-0(event-hero), sec-7(event-signup) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

27 measured-fact · 2 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-8 (closing-bookend) | 12px x1 | measured | type fact 12px | c-foot-disclaimer |
| type | sec-0 (event-hero) | 14px x2 | measured | type fact 14px | c-caption.cs-hero-panel-meta, c-eyebrow |
| type | sec-1 (event-proof) | 14px x2 | measured | type fact 14px | c-caption, c-eyebrow |
| type | sec-2 (event-bento) | 14px x8 | measured | type fact 14px | c-eyebrow |
| type | sec-3 (event-agenda) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-4 (event-quote) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-5 (event-passes) | 14px x5 | measured | type fact 14px | c-caption.cs-tier-name, c-caption.cs-tiers-note, c-eyebrow |
| type | sec-6 (event-faq) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-7 (event-signup) | 14px x1 | measured | type fact 14px | c-caption.cs-signup-meta |
| type | sec-8 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-7 (event-signup) | 15.3px x1 | measured | type fact 16px | cs-signup-consent |
| type | sec-0 (event-hero) | 18px x2 | measured | type fact 18px | c-button, c-button.c-button--secondary |
| type | sec-2 (event-bento) | 18px x8 | measured | type fact 18px | c-paragraph |
| type | sec-3 (event-agenda) | 18px x5 | measured | type fact 18px | c-faq-a, c-paragraph |
| type | sec-4 (event-quote) | 18px x2 | measured | type fact 18px | c-button.c-button--secondary, c-paragraph |
| type | sec-5 (event-passes) | 18px x7 | measured | type fact 18px | c-button, c-button.c-button--secondary, c-paragraph |
| type | sec-6 (event-faq) | 18px x6 | measured | type fact 18px | c-faq-a |
| type | sec-7 (event-signup) | 18px x2 | measured | type fact 18px | c-button, c-paragraph |
| type | sec-2 (event-bento) | 20px x7 | measured | type fact 20px | c-heading.c-heading--h5 |
| type | sec-0 (event-hero) | 20.6px x1 | measured | type fact 20px | cs-sub |
| type | sec-2 (event-bento) | 36px x1 | measured | type fact 36px | c-heading.c-heading--h2 |
| type | sec-3 (event-agenda) | 36px x1 | measured | type fact 36px | c-heading.c-heading--h2 |
| type | sec-4 (event-quote) | 36px x2 | measured | type fact 36px | c-heading.c-heading--h2, c-paragraph |
| type | sec-5 (event-passes) | 36px x1 | measured | type fact 36px | c-heading.c-heading--h2 |
| type | sec-6 (event-faq) | 36px x1 | measured | type fact 36px | c-heading.c-heading--h2 |
| type | sec-7 (event-signup) | 36px x1 | measured | type fact 36px | c-heading.c-heading--h2 |
| type | sec-0 (event-hero) | 46px x1 | measured | type fact 46px | c-heading.c-heading--display |
| space | sec-0 (event-hero) | 16px x1 | on-scale | derived step 16px | header.body-to-meta |
| space | sec-7 (event-signup) | 16px x1 | on-scale | derived step 16px | header.body-to-meta |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (event-hero) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (event-hero) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (event-hero) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (event-hero) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (event-hero) | `header.body-to-meta` | 16px | — | — | unmapped | .cs-hero-panel-content |
| sec-0 (event-hero) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (event-hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-left (computed) |
| sec-0 (event-hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-top (computed) |
| sec-0 (event-hero) | `actions.item-gap` | 16px | action-group-gap (16px) | +0px | conform | median of 1 inter-action gap(s) |
| sec-0 (event-hero) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-0 (event-hero) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-1 (event-proof) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (event-proof) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (event-proof) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-1 (event-proof) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-2 (event-bento) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-2 (event-bento) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-2 (event-bento) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-2 (event-bento) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-2 (event-bento) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (event-bento) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (event-bento) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (event-bento) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (event-bento) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (event-bento) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (event-bento) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (event-bento) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-2 (event-bento) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-2 (event-bento) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-3 (event-agenda) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (event-agenda) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (event-agenda) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-faq |
| sec-3 (event-agenda) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-faq |
| sec-3 (event-agenda) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
| sec-3 (event-agenda) | `block.content-to-actions` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
| sec-3 (event-agenda) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-3 (event-agenda) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-3 (event-agenda) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-3 (event-agenda) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-3 (event-agenda) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-3 (event-agenda) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-3 (event-agenda) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-3 (event-agenda) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-3 (event-agenda) | `container.stack-width` | 720px | header-measure (720px) | +0px | conform |  |
| sec-3 (event-agenda) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 360px / 360px |
| sec-4 (event-quote) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (event-quote) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (event-quote) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-4 (event-quote) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-4 (event-quote) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-4 (event-quote) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-4 (event-quote) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-5 (event-passes) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (event-passes) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (event-passes) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-5 (event-passes) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-5 (event-passes) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-5 (event-passes) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-5 (event-passes) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-6 (event-faq) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (event-faq) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (event-faq) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-faq |
| sec-6 (event-faq) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
| sec-6 (event-faq) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-6 (event-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-6 (event-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-6 (event-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-6 (event-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-6 (event-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-6 (event-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-6 (event-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-6 (event-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-6 (event-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-6 (event-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-6 (event-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-6 (event-faq) | `container.stack-width` | 720px | header-measure (720px) | +0px | conform |  |
| sec-6 (event-faq) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 360px / 360px |
| sec-7 (event-signup) | `section.pad-top` | 80px | cta-closing-noise.bandPadding.top (80px) | +0px | conform |  |
| sec-7 (event-signup) | `section.pad-bottom` | 80px | cta-closing-noise.bandPadding.bottom (80px) | +0px | conform |  |
| sec-7 (event-signup) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-conversion |
| sec-7 (event-signup) | `header.body-to-meta` | 16px | — | — | unmapped | .cs-conversion |
| sec-7 (event-signup) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-conversion |
| sec-7 (event-signup) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-7 (event-signup) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-7 (event-signup) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-7 (event-signup) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-7 (event-signup) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-7 (event-signup) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-7 (event-signup) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-7 (event-signup) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-7 (event-signup) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-7 (event-signup) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-7 (event-signup) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-7 (event-signup) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-7 (event-signup) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-7 (event-signup) | `container.stack-width` | 870px | cta-closing-noise.stackMeasure (870px) | +0px | conform |  |
| sec-7 (event-signup) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 285px / 285px |
| sec-8 (closing-bookend) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (closing-bookend) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (closing-bookend) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-8 (closing-bookend) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-8 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 9 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 5 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 2 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 11 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 5 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 3 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 8 link gaps |
| sec-8 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 7 link gaps |
| sec-8 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-8 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-8 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-8 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-8 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-0→sec-1 (event-hero→event-proof) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-1→sec-2 (event-proof→event-bento) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-2→sec-3 (event-bento→event-agenda) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-3→sec-4 (event-agenda→event-quote) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-4→sec-5 (event-quote→event-passes) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-5→sec-6 (event-passes→event-faq) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-6→sec-7 (event-faq→event-signup) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |
| sec-7→sec-8 (event-signup→closing-bookend) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |

## compose/components

`runs/remote/brand/compose/components/index.html` (mtime 2026-07-14 15:37:40)

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|

### Skipped (absent/inapplicable anatomy)

- — (—): whole lane — no composed sections (div.cs-surface[data-layout] > section.cs-section) — not a composed lane

