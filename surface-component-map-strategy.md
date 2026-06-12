# Surface Component Map Strategy

## Short Answer

Do not remove the model-backed `surface-component-map.md` step immediately.

The section grounding YAML already contains most of the raw facts, but it does not yet contain them in a compact, normalized, generation-safe contract. The current surface/component map is useful because it compresses hundreds of section-local YAML nodes into explicit host surface -> child component recipes that the design-system synthesis step treats as normative.

The right optimization is not "skip the map." It is:

1. Build a deterministic `surface-component-contract.yaml` from raw section grounding YAML.
2. Add coverage and leakage audits for that contract.
3. Let design-system synthesis consume the contract instead of the model-written map when the contract passes.
4. Keep the model map as fallback/debug until the deterministic contract proves equal or better across runs.

I am confident in that staged strategy. I am not confident in deleting or bypassing the current map step without first building the replacement contract, because the current deterministic draft is demonstrably not extracting the raw section YAML correctly.

## Current Pipeline Role

The current step is here:

- `run_pipeline.py` builds `surface-component-map-deterministic-draft.md`.
- If no prior/best surface map is reused, it calls `synthesize_surface_component_map(...)`.
- The output is saved as `surface-component-map.md`.
- `synthesize_design_system_from_grounding(...)` then includes this map with language that says it is the most explicit reference for host-surface and nested-element relationships.

This means the surface map is not only an informational artifact. It is part of the design-system synthesis contract.

## What The Surface Map Adds

The raw section YAML is detailed, but section-local. For Better Nights v172:

- section YAML files: 12
- section YAML total size: about 394 KB
- grounded nodes with `id`, `kind`, or `role`: about 922
- nodes with `style`: about 210
- unique explicit color values in YAML: about 105
- generated surface map size: about 58 KB
- generated host entries: 17
- generated child recipes: about 115
- critical color pairings: 23
- typography/casing pairings: 31
- graphics/depth/edge recipes: 21

The map's value is mainly:

- Compression: 394 KB of raw YAML becomes a 50-60 KB design-system-oriented artifact.
- Normalization: raw `badge`, `icon_button`, `media_frame`, `container`, `text_stack`, etc. are translated into a smaller set of useful roles like `control`, `labelControl`, `cardPanel`, `edgeDivider`, `graphicMedia`, `layout`, and `text`.
- Parent/child binding: colors are tied to host surfaces instead of becoming global tokens.
- Cross-section grouping: repeated patterns become shared roles without forcing page order into the final design system.
- Implementation focus: typography/casing, imagery direction, edge behavior, depth, and do-not-generalize rules are extracted into sections the design-system step can preserve.

## What Already Exists In Section YAML

The section YAML often contains the facts the map later uses:

- root and nested surface backgrounds
- child panel/card fills
- text colors and approximate type sizes
- text transform/casing
- badge/button fills, borders, and sizing
- imagery category and creative direction
- border radius, shadows, dividers, and edge behavior
- local do-not-generalize clues such as logo art, decorative media, embedded UI, and showcase-only details

Example from Better Nights `04-bestsellers-product-carousel.yaml`:

- root canvas background estimate: `#fff8ef`
- inset carousel panel fill estimate: `#efd0a1`
- rotated label text color estimate: `#0c1b24`
- featured card media, badge, text stack, and card action recipes nested under the actual panel/card hosts

So yes: the raw ingredients are already there.

## Why We Still Should Not Skip It Directly

The current deterministic draft is not a valid replacement.

Across v171 generated sites, the draft repeatedly failed to parse nested components from raw YAML:

- Better Nights: 12 empty section component lists
- Function: 13 empty section component lists
- Bradford: 11 empty section component lists
- Maple: 14 empty section component lists
- Roma: 7 empty section component lists

For Better Nights v172, `surface-component-map-deterministic-draft.md` says `no nested components parsed` for every section and contains 60 `not explicit` placeholders. That means the parser is still built around an older markdown component format, while the current section groundings are raw YAML trees.

If we skip the model map now, the design-system step would lose the only working normalized host/component map.

## Recommended New Strategy

### 0. Tighten Section YAML Component Typing

Before building the deterministic contract, make the raw section YAML easier to compile by tightening the first section-grounding schema.

Today, the raw section YAML allows loose `kind` values such as `icon_button`, `media_frame`, `text_stack`, `layout_region`, `input_action_group`, `repeated_content_group`, `navigation_header`, or site-specific component labels. The later merge prompt has a broader normalized enum, but the first section YAML prompt does not enforce that enum on `tree` nodes. That makes deterministic normalization harder than it needs to be.

Use a primitive `kind` plus a kind-specific role field instead of one open-ended `kind` string or one overloaded `component_family`.

```yaml
kind: section | surface | layout | text | control | media | divider | effect | unknown
section_role: navbar | footer | hero_header | compact_header | feature | cta | contact | gallery | pricing | testimonial | faq | logo_bar | team | content_feed | content_detail | stats_metrics | events_feed | banner | product_showcase | collection_showcase | utility_bar | unknown
layout_role: container | row | column | wrap | grid | masonry_grid | bento_grid | split | rail | carousel | tabs | table | timeline | inline_media_text | overlay | floating | off_grid | unknown
surface_role: canvas | module | card | frame | overlay | unknown
text_role: display | heading | subheading | body | label | caption | metadata | code | unknown
text_scale: display_xl | display | heading_xl | heading_lg | heading_md | heading_sm | body_lg | body | body_sm | label | caption | micro | unknown
html_level_hint: h1 | h2 | h3 | h4 | p | span | unknown
control_role: button | icon_button | text_link | input | checkbox | radio | switch | select | slider | tab | chip_tag | badge_status | pagination | accordion_trigger | menu_trigger | search | unknown
media_category: icon | illustration_graphic | interface | photo | unknown
media_context: page_ui | embedded_in_media | decorative | background | unknown
component_subtype: generic_content_neutral_subtype_or_null
semantic_role: generic_visual_or_structural_role
```

Rules:

- `kind` should be a closed enum and should describe the visual/structural primitive.
- Include only fields that apply to the node. Do not emit `none` placeholders for nonmatching role axes in raw section YAML.
- Omit absent visual attributes instead of writing `none`, `none_observed`, `not_observed`, or empty arrays. For example, if a node has no visible border, omit `border`; if it has no visible shadow, omit `shadow`.
- Omit default visibility. Visible elements are implied by being captured. Include `visibility` only for exceptional cases such as `structural_only`, `partial`, `obscured`, or `unclear`.
- Exactly one kind-specific role field should be populated for the node's `kind`.
- Do not use business-specific roles such as `comparison_table`, `payment_badge`, `pricing`, `product_card`, or `testimonial_card` in the closed enum. Put that nuance in `semantic_role`, `component_subtype`, or content-neutral notes when it is truly needed.
- `section_role` is the exception: it should use website-section purpose categories similar to Relume's library categories, because whole sections are meaningfully selected and composed by purpose.
- `text_role` should preserve typography hierarchy from the first grounding pass. Use `display`, `heading`, `subheading`, `body`, `label`, `caption`, `metadata`, or `code`.
- `text_scale` should capture the observed visual size/treatment independently from semantic HTML levels. Do not infer H1/H2/H3 from page order alone.
- `html_level_hint` is optional and should be `unknown` unless the visual role is very likely, such as one dominant page heading in a hero. It is a hint, not the design-system token name.
- `media_category` should use the same categories expected by downstream image generation: `icon`, `illustration_graphic`, `interface`, and `photo`.
- `media_context` should distinguish actual page media from media/interface details embedded inside screenshots, thumbnails, product images, mockups, or illustrations.
- Buttons, links, inputs, checkboxes, tabs, chips, badges, and icon actions should all use `kind: control`; keep their anatomy in `control_role`.
- `component_subtype` can be freeform but must stay content-neutral.
- `semantic_role` can remain freeform/generic, because visual role often needs more nuance than type.
- If no closed role fits for the node's actual kind, use the matching role field value `unknown` plus a short `component_subtype` and `why_unknown_role`.
- UI-like details inside screenshots, thumbnails, illustrations, device mockups, logos, payment marks, and decorative media should use `kind: media`, `media_category: interface | icon | illustration_graphic | photo`, and `media_context: embedded_in_media | decorative`, not a real page UI control role.
- Every normal section should assume an inner structural container when content is not truly edge-to-edge. Represent it as `kind: layout`, `layout_role: container`, with dynamic constraints such as `max_width`, `padding_inline`, `padding_block`, and alignment.
- Text groups, rows, wrappers, grids, and repeated groups should usually be `kind: layout` with a geometry-based `layout_role`, not a component role.
- Prefer website implementation sizing over screenshot annotation. Use `padding`, `margin`, `gap`, `max_width`, `min_height`, `aspect_ratio`, `content_width_behavior`, `overflow`, and `visible_peek` before raw `width_px`, `height_px`, `x_px`, or `y_px`.
- Pixel measurements are evidence only. Use them sparingly for crop bounds, approximate visual scale, or when a fixed-size behavior is visibly important; otherwise translate observations into responsive/dynamic layout constraints.
- Do not put uncertainty words or ranges inside implementation values. Avoid values like `approximately_313px`, `about_50px`, or `300-313px`. If a value is useful, choose one clean normalized value; if it is not useful or too uncertain, omit it.

This makes normalization faster and more reliable while preserving visual nuance in `semantic_role`, `style`, `layout`, and child relationships.

#### Kind And Role Mapping

Use this as the default parent mapping. A concept like navigation can appear at different levels, but it should move across role axes instead of becoming an overloaded component family. For example, a whole navigation/header crop can be `kind: section`, `section_role: navbar`, while the nav row inside it should be `kind: layout`, `layout_role: nav_layout`.

For readability, examples may omit non-applicable fields. The contract compiler may normalize omitted values internally, but generation-facing raw YAML should prefer absent fields over `none` placeholders, empty lists, and default `visibility: visible`.

| `kind` | Role field | Typical values | Use when |
| --- | --- | --- |
| `section` | `section_role` | `navbar`, `footer`, `hero_header`, `compact_header`, `feature`, `cta`, `contact`, `gallery`, `pricing`, `testimonial`, `faq`, `logo_bar`, `team`, `content_feed`, `content_detail`, `stats_metrics`, `events_feed`, `banner`, `product_showcase`, `collection_showcase`, `utility_bar` | The node is the root/full bounded website section or full-width semantic region. This is intentionally purpose-oriented, similar to website section libraries. |
| `surface` | `surface_role` | `canvas`, `module`, `card`, `frame`, `overlay` | The node's main job is visible containment: fill, border, radius, clipping, elevation, section-like module shell, card, media frame, or overlay surface. |
| `layout` | `layout_role` | `container`, `row`, `column`, `wrap`, `grid`, `masonry_grid`, `bento_grid`, `split`, `rail`, `carousel`, `tabs`, `table`, `timeline`, `inline_media_text`, `overlay`, `floating`, `off_grid` | The node groups or arranges children but is not itself a distinct surfaced object or direct control. These values should describe observable website geometry, not content purpose. |
| `text` | `text_role` + `text_scale` | roles: `display`, `heading`, `subheading`, `body`, `label`, `caption`, `metadata`, `code`; scales: `display_xl`, `display`, `heading_xl`, `heading_lg`, `heading_md`, `heading_sm`, `body_lg`, `body`, `body_sm`, `label`, `caption`, `micro` | The node is rendered text. `text_role` describes function; `text_scale` describes observed visual size/treatment. |
| `control` | `control_role` | `button`, `icon_button`, `text_link`, `input`, `checkbox`, `radio`, `switch`, `select`, `slider`, `tab`, `chip_tag`, `badge_status`, `pagination`, `accordion_trigger`, `menu_trigger`, `search` | The node is an action, affordance, form element, selectable item, link, pill, chip, badge, tab, disclosure, or UI state indicator. |
| `media` | `media_category` + `media_context` | `icon`, `illustration_graphic`, `interface`, `photo`; `page_ui`, `embedded_in_media`, `decorative`, `background` | The node is image/asset-like or generated-asset-relevant. |
| `divider` | `semantic_role` | `separator`, `underline`, `grid_line`, `timeline_line`, `progress_line`, `edge_rule` | The node is a structural rule, separator, underline, hairline, grid line, timeline line, or passive progress line. |
| `effect` | `semantic_role` | `scrim`, `vignette`, `glow`, `blur`, `mask`, `grain`, `texture`, `tonal_overlay`, `shadow_layer` | The node is a non-content visual treatment or background effect layer. |
| `unknown` | `semantic_role` | `unknown` | Evidence is too ambiguous to classify. Must include `why_unknown`. |

Notes:

- Navigation is usually `kind: section`, `section_role: navbar` only at the root of a captured nav/header section. Inside it, use observable layout roles such as `row`, `column`, `wrap`, or `split`; put nav semantics in `semantic_role`.
- Hero/opening sections should usually use `section_role: hero_header`, matching website-library language where "header sections" are hero-like opening sections, not nav bars.
- Non-homepage page intros should use `section_role: compact_header` when they introduce a page, article, collection, category, or resource without the immersive/full hero treatment.
- Footer follows the same pattern: root footer band can be `kind: section`, `section_role: footer`; inner footer columns should use geometry roles such as `grid`, `row`, `column`, or `wrap`.
- Forms are usually `kind: layout` with geometry roles such as `column`, `row`, `grid`, or `inline_media_text` for the wrapper inside a `section_role: contact` or `cta`; input, checkbox, select, and submit children are `kind: control`.
- Use `section_role: feature` for generic product/service/value-prop content sections rather than inventing a narrower content-specific role.
- Use `section_role: content_feed` for blog/article/news/resource/event/card feeds; use `events_feed` only when event timing/date/listing behavior is visually central.
- Use `section_role: content_detail` for article/body/detail content sections, including blog-post-like longform sections.
- Use `section_role: stats_metrics` for proof/stat rows, KPI bands, number-led claims, or metric grids.
- Use `section_role: utility_bar` when the section is a thin operational strip, assurance bar, legal/contact strip, or service info band that does not behave like a full content section.
- `display` is for oversized hero/brand/editorial type that behaves as a dominant visual object. `heading` is for normal section/card headings. `subheading` is for supporting heading-like text below or above a heading. Avoid separate `headline` and `title` roles because they are too subjective.
- Use `text_scale` to prevent display/H1/H2/H3 confusion. For example: a hero headline might be `text_role: display`, `text_scale: display_xl`, `html_level_hint: h1`; a large section heading might be `text_role: heading`, `text_scale: heading_xl`, `html_level_hint: h2`; a card title might be `text_role: heading`, `text_scale: heading_sm`, `html_level_hint: h3`; a metric number may be `text_role: display`, `text_scale: heading_lg`, `html_level_hint: none`.
- If multiple sections use different heading sizes, capture each observed text node's scale locally first. The later design-system step should consolidate these into reusable type tokens based on scale/frequency, not source section order.
- Legal copy is usually `text_role: metadata` or `caption` with `semantic_role: legal_microcopy`; it is not a core text role.
- Wordmarks and logo typography should usually be `kind: media`, `media_category: icon` or `illustration_graphic`, with `semantic_role: wordmark` or `logo_wordmark`, unless the text is genuinely live selectable page text.
- Keep `surface_role` intentionally small. The role should describe different downstream CSS behavior, not content purpose or marketing language.
- `canvas`: broad section/page/background host surface, usually full-bleed or parent-level.
- `module`: large container-sized card/shell that almost behaves like a section inside a section. It has differentiated background, radius/border/depth, and may contain nested cards or complex layouts. This absorbs previous `panel`, `tray`, `inset`, and section-like shells.
- `card`: repeated or standalone item-like content container with its own fill/border/radius/depth. Cards may sit inside a `module`.
- `frame`: structural/visual boundary around media, logos, badges, cells, or small elements only when the frame itself has visible border, radius, clipping, divider, or background behavior. If it is only layout sizing, use `kind: layout` or `kind: media`, not `surface_role: frame`.
- `overlay`: translucent or layered surface placed over media/another surface for contrast, tint, or legibility.
- Carousel is usually `kind: layout`, `layout_role: carousel`; individual carousel cards are `kind: surface`; carousel arrows/dots are `kind: control` or `divider` depending on whether they are clickable controls or passive progress.
- Logo walls should not have a dedicated layout role. Use `layout_role: wrap` for free wrapping logo groups, `grid` for equal tracks, `row` for single-line distributions, or `carousel` for scrolling logo rails, then set `semantic_role: logo_wall`.
- Use `layout_role: container` for structural max-width wrappers, section inner containers, content-width limiters, and centered gutters. Do not use `surface` unless the wrapper has a visible fill, border, radius, clipping, or shadow.
- Do not emit generic `section_padding_estimate` as a loose field. Put section spacing into the section/root layout as `padding_block` and `padding_inline`, and put content width into a child `layout_role: container` node.
- For repeated cards/items, prefer generic responsive sizing fields such as `width_behavior`, `item_width`, `min_item_width_px`, `max_item_width_px`, `aspect_ratio`, `padding`, and `gap` over fixed pixel width/height or CSS-specific properties. Use `visible_peek` or `overflow_behavior` for clipped carousel items instead of only `visible_width_px`.
- When a measured value is useful, write it as a clean scalar such as `item_width_px: 313` or `padding_inline_px: 50`. Do not add `confidence`, `evidence`, `measurement_basis`, or other uncertainty metadata for normal layout/style fields.
- Ratings are usually a layout row plus media icons/text; only use `kind: control`, `control_role: badge_status` or `control_role: chip_tag` if the rating element is visibly interactive or status-like.
- Payment marks are usually `kind: media`, `media_category: icon`, `media_context: page_ui`; the surrounding badge rectangle, if visually important, is `kind: surface`, `surface_role: frame`.

### 1. Add A Deterministic Surface Contract

Create `surface-component-contract.yaml` as the new canonical non-model intermediate.

It should be generated directly from raw section YAML and source style ledger data, not from prose markdown scraping.

Suggested top-level shape:

```yaml
schema_version: surface_component_contract.v1
source:
  section_grounding_schema: raw_section_yaml.v1
  source_style_ledger: source-style-ledger.yaml
contracts:
      host_surfaces:
    - trace_id: section_04.root
      generation_role: inset_tray_on_light_canvas
      frequency: occasional
      host:
        background: "#fff8ef"
        background_source: groundedApprox
        edge: continuous_light_canvas
        border: none_observed
        depth: flat
      children:
        - trace_id: section_04.inset_carousel_panel
          generation_role: rounded_inset_tray
          kind: surface
          surface_role: module
          semantic_role: rounded_inset_tray
          fill: "#efd0a1"
          text: "#0c1b24"
          border: none_observed
          shadow: none_observed
          radius: approximately_16px
          width_behavior: wide_inset_with_overflow
          evidence_visibility: generation_safe
  critical_pairings: []
  typography_pairings: []
  graphics_depth_edge_recipes: []
  imagery_creative_directions: {}
  repeated_layout_patterns: []
  do_not_generalize: []
  ambiguities: []
audits:
  coverage: {}
  source_order_leakage: {}
```

Important: keep `trace_id` for debugging, but do not pass trace IDs or source section numbers into generation-facing design-system prose unless they are stripped before synthesis.

### 2. Make Model Surface Map Optional, Not Required

Add a config/CLI option:

```yaml
surface-map-mode: auto
```

Modes:

- `model`: current behavior.
- `contract`: use deterministic `surface-component-contract.yaml`, no model map call.
- `auto`: use contract when audits pass; otherwise fall back to model map.
- `skip`: only for experiments; design-system synthesis receives compacted section grounding and source ledger, no map/contract.

Default should initially be `auto`, with fallback to `model`.

After the contract passes across several runs, default can become `contract`.

### 3. Feed The Contract To Design-System Synthesis

Design-system synthesis should prefer:

1. structural analysis / normalized site AST
2. compacted high-detail section grounding
3. deterministic surface-component contract
4. source-style ledger
5. source CSS report only as fallback/reference

The prompt wording should treat the contract as normative for:

- host surface backgrounds
- child fills
- text colors by host
- button/label/card/divider recipes
- typography and casing
- imagery creative direction
- do-not-generalize boundaries

### 4. Keep Existing Style Replacement Logic

The source-style-ledger strategy still applies:

- Use source CSS values only when they are visually close to the grounded approximate value and role-compatible.
- If no close source value exists, keep the grounded approximate value.
- Preserve host/child pairings over global palette neatness.
- Preserve alpha, gradients, shadows, borders, and typography role rules.

This contract should carry both values where useful:

```yaml
fill:
  grounded: "#efd0a1"
  source_backed: "#ECCBA2"
  decision: use_source_backed
  delta: 2.1
  role_compatible: true
```

## Loophole Matrix

| Loophole | Why It Matters | Proper Fix |
| --- | --- | --- |
| Tight role enum is too narrow | The grounding model may force unusual visual objects into wrong buckets. | Use strict kind-specific role enums plus `component_subtype`, `semantic_role`, and `why_unknown_role` escape hatches. |
| One `kind` field mixes structure and UI anatomy | Values like `text_stack`, `icon_button`, and `media_frame` describe different axes. | Split into `kind` for visual primitive and kind-specific roles such as `layout_role`, `control_role`, `surface_role`, and `media_category`. |
| Embedded UI mockups are typed as real controls | Interface screenshots can pollute the actual page component system. | Type them as `kind: media`, `media_category: interface`, and `media_context: embedded_in_media`. |
| Image-generation categories are not captured early | Later asset generation needs icon/graphic/interface/photo creative directions. | Add `media_category` to section YAML and keep creative direction under that category from the first grounding pass. |
| Raw YAML has facts but is too large | The design-system prompt compacts section grounding to about 30K chars, so important nested facts can be dropped. | Compile a compact deterministic contract before design-system synthesis. |
| Current deterministic draft parser targets old markdown | It produces empty component recipes from current raw YAML. | Replace parser with schema-aware YAML traversal over `tree`, `children`, `items`, `layers`, `style`, `layout`, and `position`. |
| Section-local IDs leak source order | The final design system can recreate the original page sequence. | Separate debug `trace_id` from generation-facing `generation_role`; strip trace IDs before final site input. |
| Cross-section recurrence is not visible inside one YAML | Reusable design-system roles need frequency and similarity across sections. | Add aggregation pass that clusters host/child recipes by kind, color relationship, anatomy, and edge/depth behavior. |
| Similar colors can mean different roles | A cream root canvas and a cream card fill are not interchangeable. | Cluster by host/child relationship, not color alone. |
| Different colors can share one role | Same component recipe may use surface-specific variants. | Create generic roles with on-surface variants instead of one global value. |
| Typography facts are buried in nested text nodes | Casing and type color may be lost if only host surfaces are extracted. | Emit explicit `typography_pairings` keyed by host + role. |
| Imagery direction can become local subject copying | Raw descriptions include product/site-specific subjects. | Extract medium, density, palette, crop/framing, edge behavior, and avoid rules separately from subject matter. |
| Decorative/showcase UI may become real UI components | Embedded screenshots, logos, payment marks, and product internals can contaminate component recipes. | Preserve `do_not_generalize` and classify decorative/showcase material as `kind: media` with `media_context: embedded_in_media` or `decorative`. |
| Source style sync can overwrite grounded pairings | A frequent source color can be wrong for a local component if not visually close. | Carry current closeness/role-compatible matching into the contract and audit replacements. |
| Removing reviews reduces safety net | Reviews are now disabled by default, so quality must not depend on review agents. | Add deterministic contract audits: coverage, leakage, parse validity, and value provenance. |
| Contract may overfit Better Nights schema quirks | Other sites may use different `kind` labels and nesting patterns. | Build the compiler around generic YAML traversal and key semantics, not site-specific labels. |
| Model map currently repairs missing/ambiguous facts | A deterministic contract cannot infer context as flexibly. | Use `auto` fallback to model when coverage/confidence drops below thresholds. |

## Confidence Gates

Only skip the model surface map when all gates pass.

Required deterministic audits:

- Every tree node uses an allowed `kind`.
- Every node populates the role field that matches its `kind` when that role is visually knowable.
- Raw section YAML omits nonmatching role fields instead of emitting `none` placeholders.
- Raw section YAML omits absent style attributes instead of emitting `none_observed` values.
- Raw section YAML omits `visibility: visible`; visibility appears only for exceptional visibility states.
- Normal sections with constrained content include a `layout_role: container` node or equivalent container layout evidence.
- Layout sizing uses responsive website constraints before raw pixel bounds.
- Implementation values are clean scalars/enums and do not contain uncertainty words, ranges, confidence, evidence, or measurement-basis metadata; omit fields that are too uncertain to be useful.
- Every text node has a `text_role` when hierarchy is visible.
- Every meaningful text node has `text_scale`, approximate size/weight/line-height evidence, and avoids using H1/H2/H3 as the primary visual scale.
- Nodes with unknown role values include `why_unknown_role`.
- Every media node uses `media_category: icon | illustration_graphic | interface | photo` when the category is visible, and `media_context` to mark page media versus embedded/decorative/background media.
- Layout-only wrappers such as stacks, rows, tracks, grids, and repeated groups are not promoted to component families unless they are visible reusable UI anatomy.
- Parse all section YAML files successfully.
- Extract at least one host surface per section.
- Extract nested children for at least 90% of sections that have `tree.children`, `tree.items`, or `tree.layers`.
- No section with visible child style data should emit only `not explicit`.
- Preserve all explicit hex/rgb/rgba/gradient values from relevant style-bearing nodes, either directly or as audited alternates.
- Emit typography pairings for every visible text role with color/size/casing evidence.
- Emit imagery directions for every observed category: icons, illustrations, interfaces, photography.
- Emit do-not-generalize rules for logo art, decorative graphics, embedded UI, product/media internals, and payment/trust art.
- Generation-facing contract contains no source section labels, page sequence recipes, or run-order instructions.
- Design-system freshness audit still reports zero high-risk source-order leaks.

Comparison audits before changing the default:

- Run Better Nights with `surface-map-mode=model`.
- Run Better Nights with `surface-map-mode=contract`.
- Compare design-system YAML for retained critical pairings.
- Compare generated HTML for supported source style values and absence of source-order leaks.
- Repeat on at least 3-5 diverse v171 sites.

## Implementation Plan

1. Add `src/screenshot_to_template/surface_contract.py`.
2. Tighten the section-grounding prompt/schema so raw section YAML emits closed `kind` and kind-specific role fields.
3. Implement schema-aware raw YAML traversal:
   - recurse through dictionaries/lists
   - identify visual nodes by `id`, `kind`, `role`, `style`, `layout`, `layers`, `children`, `items`
   - collect surfaces, child recipes, text roles, imagery, dividers, borders, shadows, and do-not-generalize facts
4. Add color/style normalization hooks from `source-style-ledger.yaml`.
5. Write `surface-component-contract.yaml` beside `surface-component-map.md`.
6. Add deterministic audit output:
   - `surface-component-contract-audit.json`
   - `surface-component-contract-audit.md`
7. Add `surface-map-mode` config and CLI flag.
8. In `auto`, use contract when audit passes; otherwise call the existing model map step.
9. Update design-system synthesis to accept `surface_component_contract`.
10. Update pipeline walkthrough/viewer rendering to include the new contract and audit.
11. Run v173 on Better Nights using v172/v171 reused grounding.
12. If clean, run a small cross-site bakeoff against v171 sites.

## Final Recommendation

The surface/component map is currently useful and should not be simply removed.

But the model call can probably be removed later, because the raw section YAML already has most of the necessary facts. The missing piece is a deterministic, audited compiler that turns raw section trees into a compact surface/component contract.

So the reliable strategy is:

- Keep the current map path as fallback.
- Build the YAML contract.
- Add hard audits.
- Switch default only after the contract proves it preserves the same host/component pairings without source-order leakage.
