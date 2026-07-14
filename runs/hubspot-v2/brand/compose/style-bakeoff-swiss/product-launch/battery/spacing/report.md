# Spacing-conformance baseline report

Generated 2026-07-14T18:20:42Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/style-bakeoff-swiss/product-launch | 2026-07-14 19:12:58 | 53 | 41 | 3 | 3 | 0 | 6 | **3** |

## compose/style-bakeoff-swiss/product-launch

`/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/runs/hubspot-v2/brand/compose/style-bakeoff-swiss/product-launch/index.html` (mtime 2026-07-14 19:12:58)

### Top offenders (hard fails, ranked frequency x magnitude)

| # | relationship | measured | expected | Δ | hits | where |
|---|---|---|---|---|---|---|
| 1 | `stat.column-gap` | ~32px | column-to-column (80px) | 48px | 2 | sec-2(beta-proof) |
| 2 | `header.heading-to-body` | ~40px | heading-to-body (32px) | 8px | 1 | sec-2(beta-proof) |

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-5(closing-bookend) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

9 measured-fact · 0 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (hero-reveal) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-1 (what-shipped) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-5 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-2 (beta-proof) | 16px x1 | measured | type fact 16px | c-paragraph |
| type | sec-4 (the-ask) | 16px x1 | measured | type fact 16px | c-paragraph |
| type | sec-0 (hero-reveal) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-1 (what-shipped) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-2 (beta-proof) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |
| type | sec-4 (the-ask) | 40px x1 | measured | type fact 40px | c-heading.c-heading--h2 |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (hero-reveal) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (hero-reveal) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (hero-reveal) | `header.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform | .c-header |
| sec-0 (hero-reveal) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-0 (hero-reveal) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (hero-reveal) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-0 (hero-reveal) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-1 (what-shipped) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (what-shipped) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (what-shipped) | `card.inset` | 32px | panel-padding (32px) | +0px | conform | computed padding-left |
| sec-1 (what-shipped) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-1 (what-shipped) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-2 (beta-proof) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (beta-proof) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-2 (beta-proof) | `header.heading-to-body` | 40px | heading-to-body (32px) | +8px | **wrong-step** | .cs-flow |
| sec-2 (beta-proof) | `block.header-to-content` | 40px | block-to-block (40px) | +0px | conform | .cs-flow |
| sec-2 (beta-proof) | `stat.column-gap` | 32px | column-to-column (80px) | -48px | **wrong-step** | .cs-stat-band column |
| sec-2 (beta-proof) | `stat.column-gap` | 32px | column-to-column (80px) | -48px | **wrong-step** | .cs-stat-band column |
| sec-2 (beta-proof) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-2 (beta-proof) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-3 (who-believes) | `section.pad-top` | 40px | testimonial-tab-stats.bandPadding.top (40px) | +0px | conform |  |
| sec-3 (who-believes) | `section.pad-bottom` | 24px | testimonial-tab-stats.bandPadding.bottom (24px) | +0px | conform |  |
| sec-3 (who-believes) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-3 (who-believes) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-3 (who-believes) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
| sec-4 (the-ask) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (the-ask) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-4 (the-ask) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-split-body |
| sec-4 (the-ask) | `split.column-gap` | 90px | column-to-column (80px) | +10px | drift | split columns |
| sec-4 (the-ask) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-4 (the-ask) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
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
| sec-0→sec-1 (hero-reveal→what-shipped) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-1→sec-2 (what-shipped→beta-proof) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |
| sec-2→sec-3 (beta-proof→who-believes) | `section.seam` | 104px | award-badge-row.bandPadding.top+case-study-header-rail.bandPadding.top (104px) | +0px | conform |  |
| sec-3→sec-4 (who-believes→the-ask) | `section.seam` | 88px | testimonial-tab-stats.bandPadding.bottom+case-study-header-rail.bandPadding.top (88px) | +0px | conform |  |
| sec-4→sec-5 (the-ask→closing-bookend) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |

