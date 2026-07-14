# Spacing-conformance baseline report

Generated 2026-07-14T16:31:13Z · viewport 1440x900 · contract: `brand_pipeline/spec/spacing-conformance.md` · tolerance: max(2px, 10%) for rhythm; max(2px, 1%) for widths; drift = within 2x tolerance.

Severity: `conform` pass · `drift` advisory · `wrong-step`/`off-ladder` **hard fail** · `unmapped` extraction gap (advisory, listed apart).

## Lane summary

| lane | audited file (mtime) | total | conform | drift | wrong-step | off-ladder | unmapped | hard fails |
|---|---|---|---|---|---|---|---|---|
| compose/hero-archetypes/demo | 2026-07-14 17:27:43 | 33 | 18 | 1 | 0 | 0 | 14 | **0** |

## compose/hero-archetypes/demo

`runs/hubspot-v2/brand/compose/hero-archetypes/demo/index.html` (mtime 2026-07-14 17:27:43)

### Unmapped relationships (extraction gaps — capture work, not render bugs)

| relationship | measured | nearest sanctioned | where |
|---|---|---|---|
| `footer.link-gap` | 4px x6 | --spacing-xs (4px) | sec-1(closing-bookend) |
| `form.field-gap` | 16px x2 | list-item-gap (16px) | sec-0(demo-hero) |
| `form.label-to-input` | 8px x3 | radius-global (8px) | sec-0(demo-hero) |
| `form.stack-gap` | 16px x3 | list-item-gap (16px) | sec-0(demo-hero) |

### Scale adherence (pass1 — generative lane; style-scale.v1 derived steps)

6 measured-fact · 8 on-scale · **0 off-scale** — novel geometry must sit on a measured fact (always wins) or a derived step; chrome + replica lanes exempt by construction.

| kind | sec | value | verdict | anchor | examples |
|---|---|---|---|---|---|
| type | sec-0 (demo-hero) | 13.6px x1 | measured | type fact 14px | cs-signup-consent.cs-form-split-note |
| type | sec-0 (demo-hero) | 14px x1 | measured | type fact 14px | c-eyebrow |
| type | sec-1 (closing-bookend) | 14px x1 | measured | type fact 14px | c-foot-legal |
| type | sec-0 (demo-hero) | 16px x5 | measured | type fact 16px | c-button, c-paragraph |
| type | sec-0 (demo-hero) | 24px x1 | measured | type fact 24px | c-heading.c-heading--h3 |
| type | sec-0 (demo-hero) | 80px x1 | measured | type fact 80px | c-heading.c-heading--display |
| space | sec-0 (demo-hero) | 16px x1 | on-scale | derived step 16px | form.field-gap |
| space | sec-0 (demo-hero) | 16px x1 | on-scale | derived step 16px | form.field-gap |
| space | sec-0 (demo-hero) | 8px x1 | on-scale | derived step 8px | form.label-to-input |
| space | sec-0 (demo-hero) | 8px x1 | on-scale | derived step 8px | form.label-to-input |
| space | sec-0 (demo-hero) | 8px x1 | on-scale | derived step 8px | form.label-to-input |
| space | sec-0 (demo-hero) | 16px x1 | on-scale | derived step 16px | form.stack-gap |
| space | sec-0 (demo-hero) | 16px x1 | on-scale | derived step 16px | form.stack-gap |
| space | sec-0 (demo-hero) | 16px x1 | on-scale | derived step 16px | form.stack-gap |

### All measurements

| sec | relationship | measured | declared | Δ | severity | note |
|---|---|---|---|---|---|---|
| sec-0 (demo-hero) | `section.pad-top` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (demo-hero) | `section.pad-bottom` | 64px | section-padding-light (64px) | +0px | conform |  |
| sec-0 (demo-hero) | `header.heading-to-body` | 32px | heading-to-body (32px) | +0px | conform | .cs-split-body |
| sec-0 (demo-hero) | `block.header-to-content` | 32px | block-to-block (40px) | -8px | drift | .cs-split-body |
| sec-0 (demo-hero) | `header.eyebrow-to-heading` | 24px | eyebrow-to-heading (24px) | +0px | conform | .c-header |
| sec-0 (demo-hero) | `form.field-gap` | 16px | — | — | unmapped | .cs-signup-grid row |
| sec-0 (demo-hero) | `form.field-gap` | 16px | — | — | unmapped | .cs-signup-grid row |
| sec-0 (demo-hero) | `split.column-gap` | 80px | column-to-column (80px) | +0px | conform | split columns |
| sec-0 (demo-hero) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (demo-hero) | `header.stack-coherence` | 0px | centered (0px) | +0px | conform | coherent |
| sec-0 (demo-hero) | `form.label-to-input` | 8px | — | — | unmapped |  |
| sec-0 (demo-hero) | `form.label-to-input` | 8px | — | — | unmapped |  |
| sec-0 (demo-hero) | `form.label-to-input` | 8px | — | — | unmapped |  |
| sec-0 (demo-hero) | `form.stack-gap` | 16px | — | — | unmapped | form internal seam |
| sec-0 (demo-hero) | `form.stack-gap` | 16px | — | — | unmapped | form internal seam |
| sec-0 (demo-hero) | `form.stack-gap` | 16px | — | — | unmapped | form internal seam |
| sec-0 (demo-hero) | `container.width` | 1080px | container-max (1080px) | +0px | conform |  |
| sec-0 (demo-hero) | `container.centering` | 0px | centered (0px) | +0px | conform | gutters 180px / 180px |
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
| sec-0→sec-1 (demo-hero→closing-bookend) | `section.seam` | 128px | case-study-header-rail.bandPadding.top+case-study-header-rail.bandPadding.top (128px) | +0px | conform |  |

