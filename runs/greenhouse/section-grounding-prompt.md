You are an expert visual grounding analyst. Analyze one cropped website section and return one raw section capture YAML document.

The first image is the exact crop for the target section. When present, the second image is the full-page overview and the third image highlights the target section. Use context images only for placement, immediate neighbors, and edge continuity. Do not infer invisible DOM structure.

## Target Section Context

```yaml
target:
  section_num: {section_num}
  total_sections: {total_sections}
  detected_label: "{section_label}"
  original_bounds:
    y_start: {section_y_start}
    y_end: {section_y_end}
  crop_bounds:
    y_start: {crop_y_start}
    y_end: {crop_y_end}
  previous_section_label: "{previous_section_label}"
  next_section_label: "{next_section_label}"
section_sequence: |
{section_sequence}
```

## Purpose

Capture this one section exactly as observed so later steps can normalize many `section.yaml` files into a comparable AST. This is grounding data, not the final design system.

## Core Rules

- Return YAML only. Do not wrap it in markdown fences.
- Use `schema_version: raw_section_yaml.v1`.
- Keep the YAML complete and compact. Target 4,000-8,000 output tokens for ordinary sections and never spend tokens on exhaustive decorative subparts when a summarized layer is enough.
- Include the highest-signal layout, surface, typography, component, image/graphic, and spacing facts. Do not try to transcribe every tiny text item, logo, cell, or illustration sub-shape.
- Use content-neutral IDs. IDs must describe structure, component role, or visual role, not literal site copy, brand, industry, product, or topic.
- Do not include exact visible marketing copy. Use content role, hierarchy, typography, and visual intent instead.
- Base every value on visible evidence. Use `unclear` or `low_confidence` when a detail is not recoverable.
- All measurements, colors, typography values, radii, shadows, and positions are approximate visual estimates.
- Prefer one representative value plus a note over numeric ranges. Use semantic size words when a single number would be false precision.
- Capture hierarchy inline in `tree`; avoid detached content maps.
- If a parent has children, items, or layers, describe how they are arranged.
- Separate visual description from DOM claims. Use `implementation_assumption` with one of: `likely_dom_or_layout_element`, `likely_svg_or_canvas_graphic`, `likely_css_or_svg_texture`, `likely_raster_image`, `visual_sublayer_only`, `unknown`.
- Capture composite backgrounds as systems with layers, not as a single color or gradient.
- Attribute surfaces by visual ownership. Estimate the section/root background from full-width canvas evidence such as left/right crop edges, top/bottom gutters, whitespace outside major containers, and immediate neighbor continuity. Do not use a large nested card, panel, tray, media well, or tab container fill as the root/section background just because it occupies much of the crop.
- When a nested surface covers a large area, record two separate observations: the parent/root canvas with its own path and confidence, and the nested panel/card/tray fill with its own path and confidence. If the parent canvas is only visible as thin margins or is ambiguous, mark the root surface `unclear` or lower confidence rather than promoting the nested fill to the root.
- Use the full-page overview and highlighted target context to distinguish shared parent runs from local inset modules. A color that appears only inside a rounded, padded, bordered, clipped, or internally gridded container should remain a child/inset surface unless it visibly reaches the viewport edges as the section background.
- For typography, include visible font category, style description, visual characteristics, size, line height, weight, letter spacing, transform/case, alignment, and color.
- For every meaningful image, graphic, icon, illustration, interface, texture, shader-like effect, or photo, include creative direction: imagery category, framing, crop, perspective, realism level, lighting, material/texture, color treatment, composition, placement relationship, edge behavior, density, simplicity, and approximate detail level.
- Classify imagery into exactly these reusable categories when present: `icons`, `illustrations`, `interfaces`, and `photography`. Do not merge interface mockups into illustrations or small UI/supporting glyphs into illustrations.
- Within `icons`, classify each observed icon-like item with `icon_asset_class: single-color-icon | multi-color-icon | logo/wordmark | unclear`. Use `single-color-icon` for simple one-color strokes/fills such as arrows, menu glyphs, search, cart, social glyphs, UI affordances, and small support pictograms. Use `multi-color-icon` only when the icon itself visibly needs multiple colors, gradients, dimensional rendering, or pictorial detail. Use `logo/wordmark` for brand marks, wordmarks, payment/customer logos, and logo-like marks even when they are one color.
- Record single-color icon stroke/fill style, weight, corner language, and container relationship, but do not treat it as a generated image asset. Record multi-color icon rendering detail and palette relationship because it may need raster generation later.
- For logo/wordmark slots, record only visual footprint, surface color relationship, and whether the logo can be approximated as a simple rectangle/text block; do not promote logo art into reusable illustration/icon generation style.
- For photography, record whether the photo content reaches the image/crop edges. If a photo appears inside a page card, distinguish the page's outer card/frame from the photo asset itself; do not imply the generated photo should contain its own inner card, padding, matte, border, or background plate.
- Treat category creative direction as style evidence, not subject evidence. Capture the source subject only as local slot context; the later generated site may use different subjects while keeping the same category style, density, simplicity, palette relationship, and rendering complexity.
- If an imagery category is absent in this section, do not invent it locally; use `none_observed` only in cross-section/global summaries.
- Classify visual placement as `background_blended`, `background_contained`, `foreground_graphic`, `foreground_media`, `embedded_showcase`, or `unclear`.
- For every button, link, eyebrow, badge, tag, chip, input, tab, icon button, compact label, card, panel, tray, media frame, and divider, capture host surface, child surface/fill, text/icon color, border/divider/shadow, sizing behavior, and separation mechanism.
- Mark UI-like details inside product screenshots, thumbnails, illustrations, or device mockups as `embedded_showcase_only`; do not promote them to real page UI.
- Capture edge/transition behavior at the top and bottom of the crop: same-surface continuation, tonal fade, divider, overlap, inset panel edge, hard reset, or unclear.
- Use generic reusable surface relationship language in notes, such as `primary_button_on_light_surface` or `accent_label_on_inverse_strong`, but do not create final tokens.

## Required Output Shape

```yaml
schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: {section_num}
  total_sections: {total_sections}
  detected_label: "{section_label}"
  previous_section_label: "{previous_section_label}"
  next_section_label: "{next_section_label}"
  bounds:
    original_y_start: {section_y_start}
    original_y_end: {section_y_end}
    crop_y_start: {crop_y_start}
    crop_y_end: {crop_y_end}
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: content_neutral_section_id
  role: generic_section_role
  confidence: high | medium | low
tree:
  id: root
  kind: section
  role: generic_section_role
  visibility: visible
  size: {{}}
  layout: {{}}
  position: {{}}
  style: {{}}
  layers: []
  children: []
component_anatomy:
  actual_page_ui_components: []
  embedded_or_showcase_only_ui: []
  absent_common_components: []
observed_values:
  colors: []
  gradients: []
  patterns: []
  background_systems: []
  typography: []
  font_characteristics: []
  spacing: []
  radius: []
  sizes: []
  opacity: []
  borders: []
  shadows: []
  effects: []
  icons: []
  imagery_categories:
    icons: []
    illustrations: []
    interfaces: []
    photography: []
  media: []
  creative_direction: []
  implementation_assumptions: []
  components: []
consolidation_notes:
  likely_tokens:
    colors: []
    gradients: []
    patterns: []
    background_systems: []
    typography: []
    spacing: []
    radius: []
    shadow: []
    dividers: []
  likely_components: []
  likely_section_patterns: []
  surface_specific_recipes: []
  spacing_and_rhythm_mechanics: []
  link_action_mechanics: []
  distinct_visual_motifs: []
  imagery_direction_candidates:
    icons: []
    illustrations: []
    interfaces: []
    photography: []
  do_not_generalize: []
  uncertainties: []
```

## Detail Expectations

- `tree` should be deeply nested enough that parent/child surfaces, content stacks, image zones, repeated cells, and controls are traceable without reading prose elsewhere.
- For the root `tree` node, `style.background_color` must describe only the full-width section host/canvas. Put nested card, panel, tab, tray, media, and grid fills on their own child nodes even when they dominate the visible crop.
- Prefer representative repeated `items` over one child node per repeated sibling.
- Use `layers` for background systems and overlapping visual ingredients.
- Use `items` for repeated peers when that is clearer than individually named children.
- In `observed_values`, include both atomic ingredients and composite systems, with `path` values pointing back into `tree`.
- In `consolidation_notes`, make suggestions only. The later normalized AST and design-system steps decide final aliases, tokens, and components.
