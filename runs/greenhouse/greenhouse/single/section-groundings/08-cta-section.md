schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: 8
  total_sections: 9
  detected_label: "CTA section"
  previous_section_label: "Value proposition section"
  next_section_label: "Footer"
  bounds:
    original_y_start: 4040
    original_y_end: 4980
    crop_y_start: 4040
    crop_y_end: 4980
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: cta_banner_section
  role: call_to_action_section
  confidence: high
tree:
  id: root
  kind: section
  role: call_to_action_section
  visibility: visible
  size:
    width: full_bleed
    height: tall_banner
    note: "approx 940px tall in original coords"
  layout:
    type: full_width_band
    content_alignment: left
    vertical_anchor: center
    note: "white gutter strip at very top is prior-section continuation; main dark band fills remainder"
  position:
    flow: in_flow
  style:
    background_color:
      role: section_canvas
      value: "deep desaturated green ~#163328"
      confidence: high
  layers:
    - id: top_white_continuation_strip
      role: neighbor_continuation
      kind: surface
      coverage: full_width_thin_top
      style:
        background_color: "white ~#ffffff"
      note: "thin white band at top of crop, belongs to previous section background bleed"
      implementation_assumption: likely_dom_or_layout_element
    - id: main_dark_band
      role: primary_background
      kind: surface
      coverage: full_width_majority
      style:
        background_color: "dark green ~#163328"
      implementation_assumption: likely_dom_or_layout_element
    - id: bottom_tonal_band
      role: lower_tonal_shift
      kind: surface
      coverage: full_width_thin_bottom
      style:
        background_color: "slightly lighter/greener ~#1d4034"
      note: "subtle horizontal tonal band near bottom edge, transition toward footer"
      implementation_assumption: likely_dom_or_layout_element
    - id: decorative_fingerprint_graphic
      role: decorative_background_motif
      kind: graphic
      coverage: right_half
      style:
        treatment: "low-contrast tonal line-pattern, slightly darker than band"
      note: "fingerprint-textured flower/plant motif occupying right portion"
      implementation_assumption: likely_svg_or_canvas_graphic
  children:
    - id: content_column
      kind: container
      role: text_and_action_stack
      layout:
        type: vertical_stack
        align: left
        position: left_inset
      position:
        horizontal: left_aligned_with_page_gutter
        vertical: vertically_centered
      style:
        background_color: transparent
      children:
        - id: headline
          kind: text
          role: section_heading
          content_role: primary_cta_headline
          style:
            font_category: serif
            weight: regular
            size: very_large
            line_height: tight
            color: "off-white ~#f3f1ea"
            alignment: left
            transform: none
          note: "three visual lines, multi-line wrap"
        - id: cta_button
          kind: button
          role: primary_action
          content_role: demo_request_action
          style:
            shape: pill
            background_color: "blue ~#2f6fe0"
            text_color: "white ~#ffffff"
            font_category: sans_serif
            size: small_label
            padding: comfortable_horizontal
            border: none
            shadow: none
          surface_relationship: primary_button_on_inverse_dark_surface
    - id: graphic_zone
      kind: container
      role: decorative_media_zone
      position:
        horizontal: right_half
        vertical: spans_band
      style:
        background_color: transparent
      children:
        - id: fingerprint_flower_motif
          kind: graphic
          role: brand_decorative_illustration
          placement: background_blended
          style:
            treatment: tonal_line_texture
            contrast: very_low
            color: "marginally darker green than band"
          implementation_assumption: likely_svg_or_canvas_graphic
component_anatomy:
  actual_page_ui_components:
    - id: cta_button
      type: pill_button
      role: primary_cta
      host_surface: dark_green_band
      child_fill: "blue ~#2f6fe0"
      text_color: white
      border: none
      shadow: none
      sizing: hug_content
      separation: color_contrast_against_dark_bg
    - id: headline
      type: heading_block
      role: section_headline
      host_surface: dark_green_band
  embedded_or_showcase_only_ui: []
  absent_common_components:
    - secondary_button
    - eyebrow_label
    - supporting_paragraph
    - form_inputs
observed_values:
  colors:
    - id: color_section_bg
      role: section_canvas
      value: "#163328"
      path: tree.style.background_color
      confidence: high
    - id: color_bottom_band
      role: lower_band
      value: "#1d4034"
      path: tree.layers.bottom_tonal_band
      confidence: medium
    - id: color_top_white_strip
      role: neighbor_continuation
      value: "#ffffff"
      path: tree.layers.top_white_continuation_strip
      confidence: high
    - id: color_headline_text
      role: heading_text_on_dark
      value: "#f3f1ea"
      path: tree.children.content_column.children.headline
      confidence: high
    - id: color_button_fill
      role: primary_button_fill
      value: "#2f6fe0"
      path: tree.children.content_column.children.cta_button
      confidence: high
    - id: color_button_text
      role: primary_button_text
      value: "#ffffff"
      path: tree.children.content_column.children.cta_button
      confidence: high
  gradients: []
  patterns:
    - id: pattern_fingerprint_texture
      role: decorative_line_texture
      description: "concentric ridge / fingerprint line pattern forming plant shape"
      contrast: very_low
      path: tree.layers.decorative_fingerprint_graphic
      confidence: high
  background_systems:
    - id: bg_system_cta
      type: layered_solid_with_decorative_motif
      layers:
        - base_solid_dark_green
        - bottom_tonal_band
        - right_side_fingerprint_motif
        - top_white_continuation_strip_from_prior_section
      path: tree.layers
      confidence: high
  typography:
    - id: type_headline
      role: section_heading
      font_category: serif
      weight: regular
      size: very_large
      line_height: tight
      letter_spacing: normal
      transform: none
      alignment: left
      color: "#f3f1ea"
      path: tree.children.content_column.children.headline
    - id: type_button_label
      role: button_label
      font_category: sans_serif
      weight: medium
      size: small
      transform: none
      alignment: center
      color: "#ffffff"
      path: tree.children.content_column.children.cta_button
  font_characteristics:
    - id: font_serif_display
      observation: "high-contrast transitional serif, classic editorial feel, used for headline"
    - id: font_sans_ui
      observation: "neutral grotesque sans for button label"
  spacing:
    - id: space_content_left_inset
      role: left_gutter
      value: large
      note: "content column inset from left edge by sizeable margin"
    - id: space_headline_to_button
      role: vertical_gap
      value: medium_large
    - id: space_band_vertical_padding
      role: section_padding
      value: generous
  radius:
    - id: radius_button_pill
      role: button_radius
      value: full_pill
      path: tree.children.content_column.children.cta_button
  sizes:
    - id: size_button
      role: cta_button
      width: hug_content
      height: small_compact
    - id: size_section_height
      role: band_height
      value: tall_banner
  opacity:
    - id: opacity_motif
      role: decorative_graphic
      value: low_contrast_subtle
      path: tree.layers.decorative_fingerprint_graphic
  borders: []
  shadows: []
  effects:
    - id: effect_tonal_band_shift
      role: bottom_edge_transition
      description: "subtle lighter green horizontal band before footer"
      path: tree.layers.bottom_tonal_band
  icons:
    imagery_categories_note: "no discrete icons observed"
  imagery_categories:
    icons: []
    illustrations:
      - id: illus_fingerprint_motif
        icon_or_role: decorative_brand_motif
        subject_slot_context: "fingerprint-textured plant/flower silhouette"
        category_style: line_texture_organic
        framing: partial_bleed_right
        crop: right_edge_clipped
        realism_level: abstract_stylized
        rendering_complexity: medium_fine_line_detail
        palette_relationship: tonal_monochrome_on_dark
        density: medium
        simplicity: low_to_medium_detail
        placement: background_blended
        edge_behavior: extends_toward_right_edge
        path: tree.layers.decorative_fingerprint_graphic
    interfaces: []
    photography: []
  media:
    - id: media_decorative_motif
      type: vector_decorative_graphic
      placement: background_blended
      path: tree.layers.decorative_fingerprint_graphic
  creative_direction:
    - id: cd_cta_banner
      intent: "calm, premium, editorial CTA on dark inverse surface with subtle brand texture"
      contrast_strategy: "high-contrast white serif headline + saturated blue pill button against muted dark green"
      imagery_role: "low-contrast textural brand motif, non-distracting"
  implementation_assumptions:
    - target: decorative_fingerprint_graphic
      assumption: likely_svg_or_canvas_graphic
    - target: main_dark_band
      assumption: likely_dom_or_layout_element
    - target: cta_button
      assumption: likely_dom_or_layout_element
    - target: top_white_continuation_strip
      assumption: likely_dom_or_layout_element
  components:
    - id: comp_primary_cta_button
      type: pill_button
      surface_relationship: primary_button_on_inverse_dark_surface
    - id: comp_cta_headline
      type: serif_heading
consolidation_notes:
  likely_tokens:
    colors:
      - "dark_green_canvas #163328"
      - "cta_blue #2f6fe0"
      - "heading_on_dark #f3f1ea"
    gradients: []
    patterns:
      - fingerprint_line_texture_motif
    background_systems:
      - inverse_dark_band_with_subtle_motif
    typography:
      - serif_display_heading
      - sans_button_label
    spacing:
      - generous_section_band_padding
      - left_gutter_inset
    radius:
      - full_pill_button
    shadow: []
    dividers: []
  likely_components:
    - primary_pill_button_on_dark
    - left_aligned_cta_headline_block
  likely_section_patterns:
    - left_text_cta_with_right_decorative_motif_on_dark_band
  surface_specific_recipes:
    - "blue pill primary button reads as the single high-saturation accent on inverse dark green"
  spacing_and_rhythm_mechanics:
    - "content vertically centered in tall band, left-anchored"
  link_action_mechanics:
    - "single primary CTA, no secondary link"
  distinct_visual_motifs:
    - fingerprint_textured_botanical_silhouette
  imagery_direction_candidates:
    icons: []
    illustrations:
      - "low-contrast tonal line-texture organic motif, monochrome on dark, partial right bleed"
    interfaces: []
    photography: []
  do_not_generalize:
    - "top white strip belongs to previous section, not this band's background"
    - "bottom lighter green band may belong to footer transition rather than CTA"
  uncertainties:
    - "exact boundary between this section bottom band and footer top"
    - "precise hex values approximate"
