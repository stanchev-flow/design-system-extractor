# Spacing-conformance baseline report

Generated 2026-07-10T18:26:07Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose | 2026-07-10 19:23:00 | 77 | 74 | 0 | 3 | 0 | 0 | **3** |
| compose/sol-experiment | 2026-07-10 19:23:00 | 147 | 144 | 0 | 2 | 0 | 1 | **2** |
| compose/event-genlaunch | 2026-07-10 19:23:01 | 109 | 107 | 0 | 0 | 0 | 2 | **0** |
| compose/stress-playbook | 2026-07-10 19:25:15 | 162 | 160 | 0 | 0 | 0 | 2 | **0** |
| compose/replica | 2026-07-10 18:45:44 | 129 | 129 | 0 | 0 | 0 | 0 | **0** |

## compose

`runs/remote/brand/compose/index.html` (mtime 2026-07-10 19:23:00)

### Top offenders (hard fails, ranked frequency x magnitude)

| # | relationship | measured | expected | Δ | hits | where |
|---|---|---|---|---|---|---|
| 1 | `container.width` | ~720px | container-span (1169.28px) | 449.3px | 2 | sec-6(workflow-cards), sec-8(testimonials) |
| 2 | `split.column-gap` | ~97.4px | column-to-column (48px) | 49.4px | 1 | sec-1(hero) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (navbar) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (navbar) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (hero) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (hero) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (hero) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-split-body |
| sec-1 (hero) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-split-body |
| sec-1 (hero) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-1 (hero) | `split.column-gap` | 97.44px | column-to-column (48px) | +49.44px | **wrong-step** | split columns |
| sec-1 (hero) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-1 (hero) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-2 (logo-wall) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-2 (logo-wall) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (feature-accordion) | `section.pad-top` | 64px | feature-accordion-deep-accent.bandPadding.top (64px) | +0px | conform |  |
| sec-3 (feature-accordion) | `section.pad-bottom` | 64px | feature-accordion-deep-accent.bandPadding.bottom (64px) | +0px | conform |  |
| sec-3 (feature-accordion) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-split-body |
| sec-3 (feature-accordion) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-3 (feature-accordion) | `split.column-gap` | 97.44px | feature-accordion-deep-accent.deviceGeometry.columnGap (101px) | -3.56px | conform | split columns |
| sec-3 (feature-accordion) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-3 (feature-accordion) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-4 (infra-panel) | `section.pad-top` | 64px | infra-proof-split.bandPadding.top (64px) | +0px | conform |  |
| sec-4 (infra-panel) | `section.pad-bottom` | 64px | infra-proof-split.bandPadding.bottom (64px) | +0px | conform |  |
| sec-4 (infra-panel) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-split-body |
| sec-4 (infra-panel) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-split-body |
| sec-4 (infra-panel) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-4 (infra-panel) | `split.column-gap` | 97.44px | infra-proof-split.columnGap(note) (101px) | -3.56px | conform | split columns |
| sec-4 (infra-panel) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-4 (infra-panel) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-5 (banner-cta) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (banner-cta) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (workflow-cards) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (workflow-cards) | `section.pad-bottom` | 112px | section-y-xl (112px) | +0px | conform | computed padding-bottom 48px |
| sec-6 (workflow-cards) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-6 (workflow-cards) | `container.width` | 720px | container-span (1169.28px) | -449.28px | **wrong-step** |  |
| sec-6 (workflow-cards) | `container.centering` | 0.04px | centered (0px) | +0.04px | conform | gutters 359.98px / 360.02px |
| sec-7 (partner-logos) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-7 (partner-logos) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (testimonials) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (testimonials) | `section.pad-bottom` | 112px | section-y-xl (112px) | +0px | conform | computed padding-bottom 48px |
| sec-8 (testimonials) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-8 (testimonials) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-8 (testimonials) | `container.width` | 720px | container-span (1169.28px) | -449.28px | **wrong-step** |  |
| sec-8 (testimonials) | `container.centering` | 0.04px | centered (0px) | +0.04px | conform | gutters 359.98px / 360.02px |
| sec-9 (badge-strip) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-9 (badge-strip) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-10 (closing-cta) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-10 (closing-cta) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-11 (footer) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-11 (footer) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-12 (closing-bookend) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-12 (closing-bookend) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-12 (closing-bookend) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-12 (closing-bookend) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-12 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 9 link gaps |
| sec-12 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 5 link gaps |
| sec-12 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 2 link gaps |
| sec-12 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 11 link gaps |
| sec-12 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 5 link gaps |
| sec-12 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 3 link gaps |
| sec-12 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 8 link gaps |
| sec-12 (closing-bookend) | `footer.link-gap` | 12px | navbar.linkGap (12px) | +0px | conform | median of 7 link gaps |
| sec-12 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-12 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-12 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-12 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-12 (closing-bookend) | `footer.column-gap` | 26px | footer.grid.columnGap (26px) | +0px | conform | directory columns |
| sec-0→sec-1 (navbar→hero) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-1→sec-2 (hero→logo-wall) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-2→sec-3 (logo-wall→feature-accordion) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-3→sec-4 (feature-accordion→infra-panel) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |
| sec-4→sec-5 (infra-panel→banner-cta) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-5→sec-6 (banner-cta→workflow-cards) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-6→sec-7 (workflow-cards→partner-logos) | `section.seam` | 160px | section-padding-light+section-y-xl (160px) | +0px | conform |  |
| sec-7→sec-8 (partner-logos→testimonials) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-8→sec-9 (testimonials→badge-strip) | `section.seam` | 160px | section-padding-light+section-y-xl (160px) | +0px | conform |  |
| sec-9→sec-10 (badge-strip→closing-cta) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-10→sec-11 (closing-cta→footer) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-11→sec-12 (footer→closing-bookend) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |

### Skipped (absent/inapplicable anatomy)

- sec-0 (navbar): container — no max-width-constrained scaffold found
- sec-2 (logo-wall): container — no max-width-constrained scaffold found
- sec-5 (banner-cta): container — no max-width-constrained scaffold found
- sec-6 (workflow-cards): .cs-modules — staggered editorial grid (no uniform row/column gap)
- sec-7 (partner-logos): container — no max-width-constrained scaffold found
- sec-8 (testimonials): .cs-modules — staggered editorial grid (no uniform row/column gap)
- sec-9 (badge-strip): container — no max-width-constrained scaffold found
- sec-10 (closing-cta): container — no max-width-constrained scaffold found
- sec-11 (footer): container — no max-width-constrained scaffold found

## compose/sol-experiment

`runs/remote/brand/compose/sol-experiment/index.html` (mtime 2026-07-10 19:23:00)

### Top offenders (hard fails, ranked frequency x magnitude)

| # | relationship | measured | expected | Δ | hits | where |
|---|---|---|---|---|---|---|
| 1 | `header.heading-to-body` | ~64px | heading-to-body (16px) | 48px | 2 | sec-4(sol-scale), sec-6(sol-decision) |

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `header.body-to-meta` | 16px x1 | heading-to-body (16px) | sec-9(sol-plan-form) |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (sol-hero) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (sol-hero) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-0 (sol-hero) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (sol-hero) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (sol-hero) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-hero-panel-content |
| sec-0 (sol-hero) | `split.column-gap` | 48px | column-to-column (48px) | +0px | conform | hero panel columns |
| sec-0 (sol-hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-left (computed) |
| sec-0 (sol-hero) | `hero.panel-inset` | 80px | panel-padding~80px(role) (80px) | +0px | conform | panel padding-top (computed) |
| sec-0 (sol-hero) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-0 (sol-hero) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-1 (sol-proof) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (sol-proof) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-1 (sol-proof) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-1 (sol-proof) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-2 (sol-control) | `section.pad-top` | 64px | infra-proof-split.bandPadding.top (64px) | +0px | conform |  |
| sec-2 (sol-control) | `section.pad-bottom` | 64px | infra-proof-split.bandPadding.bottom (64px) | +0px | conform |  |
| sec-2 (sol-control) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-split-body |
| sec-2 (sol-control) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-split-body |
| sec-2 (sol-control) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-2 (sol-control) | `split.column-gap` | 97.44px | infra-proof-split.columnGap(note) (101px) | -3.56px | conform | split columns |
| sec-2 (sol-control) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-2 (sol-control) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-3 (sol-workstreams) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (sol-workstreams) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (sol-workstreams) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-3 (sol-workstreams) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-3 (sol-workstreams) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (sol-workstreams) | `grid.column-gap` | 32px | grid-gap (32px) | +0px | conform | .cs-modules column |
| sec-3 (sol-workstreams) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (sol-workstreams) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (sol-workstreams) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (sol-workstreams) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (sol-workstreams) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (sol-workstreams) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (sol-workstreams) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (sol-workstreams) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (sol-workstreams) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-3 (sol-workstreams) | `card.media-to-content` | 32px | panel-padding (32px) | +0px | conform | full-bleed well seam |
| sec-3 (sol-workstreams) | `card.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform |  |
| sec-3 (sol-workstreams) | `card.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform |  |
| sec-3 (sol-workstreams) | `card.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | min across 3 equalized cards (pinned slack sanctioned by gridEqualize) |
| sec-3 (sol-workstreams) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-3 (sol-workstreams) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-4 (sol-scale) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (sol-scale) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-4 (sol-scale) | `header.heading-to-body` | 64px | heading-to-body (16px) | +48px | **wrong-step** | .cs-flow |
| sec-4 (sol-scale) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-4 (sol-scale) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-4 (sol-scale) | `stat.column-gap` | 48px | column-to-column (48px) | +0px | conform | .cs-stat-band column |
| sec-4 (sol-scale) | `stat.column-gap` | 48px | column-to-column (48px) | +0px | conform | .cs-stat-band column |
| sec-4 (sol-scale) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-4 (sol-scale) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-5 (sol-process) | `section.pad-top` | 64px | feature-accordion-deep-accent.bandPadding.top (64px) | +0px | conform |  |
| sec-5 (sol-process) | `section.pad-bottom` | 64px | feature-accordion-deep-accent.bandPadding.bottom (64px) | +0px | conform |  |
| sec-5 (sol-process) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-split-intro |
| sec-5 (sol-process) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-acc-col--lead |
| sec-5 (sol-process) | `block.row-gap` | 64px | block-to-block (64px) | +0px | conform | .cs-acc-col--lead |
| sec-5 (sol-process) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-5 (sol-process) | `split.column-gap` | 101px | feature-accordion-deep-accent.deviceGeometry.columnGap (101px) | +0px | conform | accordion split columns |
| sec-5 (sol-process) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-5 (sol-process) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-5 (sol-process) | `list.item-gap` | 16px | feature-accordion-deep-accent.list.itemGap (16px) | +0px | conform | accordion items |
| sec-5 (sol-process) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform | open item |
| sec-5 (sol-process) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-5 (sol-process) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-5 (sol-process) | `list.trigger-height` | 80px | feature-accordion-deep-accent.list.triggerMinHeight (80px) | +0px | conform |  |
| sec-5 (sol-process) | `container.width` | 1168px | feature-accordion-deep-accent.deviceGeometry.contentSpan (1168px) | +0px | conform |  |
| sec-5 (sol-process) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 136px / 136px |
| sec-6 (sol-decision) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (sol-decision) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (sol-decision) | `header.heading-to-body` | 64px | heading-to-body (16px) | +48px | **wrong-step** | .cs-flow |
| sec-6 (sol-decision) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-6 (sol-decision) | `block.content-to-actions` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-6 (sol-decision) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-6 (sol-decision) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-6 (sol-decision) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-7 (sol-ecosystem) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-7 (sol-ecosystem) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-7 (sol-ecosystem) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-flow |
| sec-7 (sol-ecosystem) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-flow |
| sec-7 (sol-ecosystem) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-7 (sol-ecosystem) | `block.content-to-actions` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-7 (sol-ecosystem) | `strip.gap` | 64px | strip-gap (64px) | +0px | conform | median of 3 inter-mark gaps |
| sec-7 (sol-ecosystem) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-7 (sol-ecosystem) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-8 (sol-faq) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (sol-faq) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-8 (sol-faq) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-faq |
| sec-8 (sol-faq) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
| sec-8 (sol-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (sol-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (sol-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (sol-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (sol-faq) | `list.item-inset` | 24px | list-item-inset (24px) | +0px | conform | faq item top inset |
| sec-8 (sol-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (sol-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (sol-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (sol-faq) | `list.item-gap` | 16px | list-item-gap (16px) | +0px | conform | faq item stride |
| sec-8 (sol-faq) | `container.stack-width` | 720px | header-measure (720px) | +0px | conform |  |
| sec-8 (sol-faq) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 360px / 360px |
| sec-9 (sol-plan-form) | `section.pad-top` | 80px | cta-closing-noise.bandPadding.top (80px) | +0px | conform |  |
| sec-9 (sol-plan-form) | `section.pad-bottom` | 80px | cta-closing-noise.bandPadding.bottom (80px) | +0px | conform |  |
| sec-9 (sol-plan-form) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-conversion |
| sec-9 (sol-plan-form) | `header.body-to-meta` | 16px | — | — | unmapped | .cs-conversion |
| sec-9 (sol-plan-form) | `header.body-to-actions` | 32px | body-to-cta (32px) | +0px | conform | .cs-conversion |
| sec-9 (sol-plan-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-9 (sol-plan-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid column |
| sec-9 (sol-plan-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (sol-plan-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (sol-plan-form) | `form.field-gap` | 16px | field-to-field (16px) | +0px | conform | .cs-signup-grid row |
| sec-9 (sol-plan-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (sol-plan-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (sol-plan-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (sol-plan-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (sol-plan-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (sol-plan-form) | `form.label-to-input` | 4px | field-label-gap (4px) | +0px | conform |  |
| sec-9 (sol-plan-form) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-9 (sol-plan-form) | `form.stack-gap` | 32px | form-stack (32px) | +0px | conform | form internal seam |
| sec-9 (sol-plan-form) | `container.stack-width` | 870px | cta-closing-noise.stackMeasure (870px) | +0px | conform |  |
| sec-9 (sol-plan-form) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 285px / 285px |
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
| sec-0→sec-1 (sol-hero→sol-proof) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-1→sec-2 (sol-proof→sol-control) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-2→sec-3 (sol-control→sol-workstreams) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-3→sec-4 (sol-workstreams→sol-scale) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-4→sec-5 (sol-scale→sol-process) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-5→sec-6 (sol-process→sol-decision) | `section.seam` | 112px | section-padding-light+infra-proof-split.bandPadding.bottom (112px) | +0px | conform |  |
| sec-6→sec-7 (sol-decision→sol-ecosystem) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-7→sec-8 (sol-ecosystem→sol-faq) | `section.seam` | 96px | section-padding-light+section-padding-light (96px) | +0px | conform |  |
| sec-8→sec-9 (sol-faq→sol-plan-form) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |
| sec-9→sec-10 (sol-plan-form→closing-bookend) | `section.seam` | 128px | section-padding-light+cta-closing-noise.bandPadding.bottom (128px) | +0px | conform |  |

## compose/event-genlaunch

`runs/remote/brand/compose/event-genlaunch/index.html` (mtime 2026-07-10 19:23:01)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `header.body-to-meta` | 16px x2 | heading-to-body (16px) | sec-0(event-hero), sec-7(event-signup) |

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
| sec-2 (event-bento) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-2 (event-bento) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-3 (event-agenda) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (event-agenda) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-3 (event-agenda) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-faq |
| sec-3 (event-agenda) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-faq |
| sec-3 (event-agenda) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
| sec-3 (event-agenda) | `block.content-to-actions` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
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
| sec-4 (event-quote) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-4 (event-quote) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-5 (event-passes) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (event-passes) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-5 (event-passes) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-modules-intro |
| sec-5 (event-passes) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .c-header |
| sec-5 (event-passes) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-5 (event-passes) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-6 (event-faq) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (event-faq) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (event-faq) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-faq |
| sec-6 (event-faq) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-faq |
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

## compose/stress-playbook

`runs/remote/brand/compose/stress-playbook/index.html` (mtime 2026-07-10 19:25:15)

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

## compose/replica

`runs/remote/brand/compose/replica/index.html` (mtime 2026-07-10 18:45:44)

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
| sec-5 (workflow-cards) | `container.width` | 1169.27px | container-span (1169.28px) | -0.01px | conform |  |
| sec-5 (workflow-cards) | `container.centering` | 0.01px | centered (0px) | +0.01px | conform | gutters 135.36px / 135.37px |
| sec-6 (partner-logos) | `section.pad-top` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (partner-logos) | `section.pad-bottom` | 48px | section-padding-light (48px) | +0px | conform |  |
| sec-6 (partner-logos) | `header.eyebrow-to-heading` | 12px | eyebrow-to-heading (12px) | +0px | conform | .cs-flow |
| sec-6 (partner-logos) | `header.heading-to-body` | 16px | heading-to-body (16px) | +0px | conform | .cs-flow |
| sec-6 (partner-logos) | `block.header-to-content` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-6 (partner-logos) | `block.content-to-actions` | 64px | block-to-block (64px) | +0px | conform | .cs-flow |
| sec-6 (partner-logos) | `strip.gap` | 64px | strip-gap (64px) | +0px | conform | median of 3 inter-mark gaps |
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

