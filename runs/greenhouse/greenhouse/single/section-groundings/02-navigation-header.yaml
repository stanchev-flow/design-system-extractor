schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: 2
  total_sections: 9
  detected_label: "Navigation / header"
  previous_section_label: "Announcement bar"
  next_section_label: "Hero section"
  bounds:
    original_y_start: 21
    original_y_end: 55
    crop_y_start: 21
    crop_y_end: 55
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: announcement_promo_bar
  role: full_width_promo_announcement_strip
  confidence: medium
  note: >
    Detected label is 'Navigation / header', but the provided crop visually
    shows a slim full-width dark promo/announcement strip with centered
    promo text, an inline emphasized link, and a far-right close affordance.
    Captured per visible crop content; label/bounds mismatch flagged.
tree:
  id: root
  kind: section
  role: full_width_promo_announcement_strip
  visibility: visible
  size:
    width: full_bleed_viewport
    height: very_short_single_row
  layout:
    type: horizontal_inline_centered
    main_axis: horizontal
    content_alignment: center
    close_control_alignment: far_right
    vertical_alignment: middle
    note: centered promo message group with a corner-pinned utility control
  position:
    placement: top_of_page_strip
  style:
    background_color:
      role: dark_green_inverse_surface
      approx_hex: "#1f3d31"
      confidence: high
      note: full-bleed dark green strip reaching both crop edges
    text_default: light_on_dark_inverse
  layers:
    - id: bg_fill
      kind: background_layer
      role: solid_inverse_fill
      implementation_assumption: likely_dom_or_layout_element
      style:
        fill: "#1f3d31"
  children:
    - id: promo_message_group
      kind: inline_text_group
      role: centered_announcement_message
      layout:
        type: inline_horizontal
        alignment: center
        gap: small_inline_gap
      children:
        - id: promo_text
          kind: text
          role: announcement_body_text
          style:
            typography_ref: promo_body
            color: "#f3f1ea"
            weight: regular
        - id: promo_inline_link
          kind: link
          role: inline_emphasized_action_link
          style:
            typography_ref: promo_link
            color: "#ffffff"
            weight: bold
            text_decoration: underline
          note: inline call-to-action link, bold + underlined, on dark surface
    - id: close_control
      kind: icon_button
      role: dismiss_announcement_control
      position:
        placement: far_right_edge
      style:
        glyph: x_close
        glyph_color: "#f3f1ea"
        container_fill: none
        border: none
      implementation_assumption: likely_dom_or_layout_element
component_anatomy:
  actual_page_ui_components:
    - id: promo_inline_link
      type: inline_text_link
      host_surface: dark_green_inverse_strip
      child_surface: none
      text_color: "#ffffff"
      emphasis: bold_underline
      sizing_behavior: hug_content
      separation_mechanism: weight_and_underline_contrast_vs_adjacent_body_text
      note: accent_inline_link_on_inverse_strong
    - id: close_control
      type: icon_button
      host_surface: dark_green_inverse_strip
      child_surface: none
      icon_color: "#f3f1ea"
      border: none
      shadow: none
      sizing_behavior: fixed_small_square
      separation_mechanism: standalone_glyph_corner_pinned
      note: utility_dismiss_icon_on_inverse_strong
  embedded_or_showcase_only_ui: []
  absent_common_components:
    - logo_wordmark
    - primary_nav_links
    - search_control
    - auth_button
    - primary_cta_button
    note: >
      Expected navigation/header components (logo, nav links, search,
      sign-in, demo CTA) are NOT visible in this crop; only a promo strip
      is shown.
observed_values:
  colors:
    - id: inverse_surface_dark_green
      approx_hex: "#1f3d31"
      role: section_background_inverse
      path: tree.style.background_color
      confidence: high
    - id: text_light_neutral
      approx_hex: "#f3f1ea"
      role: body_text_on_inverse
      path: tree.children[0].children[0].style.color
      confidence: medium
    - id: text_pure_white
      approx_hex: "#ffffff"
      role: emphasized_link_on_inverse
      path: tree.children[0].children[1].style.color
      confidence: medium
  gradients: []
  patterns: []
  background_systems:
    - id: inverse_solid_strip
      type: single_solid_fill
      path: tree.layers[0]
      layers:
        - solid_dark_green_fill
      confidence: high
  typography:
    - id: promo_body
      role: announcement_body_text
      font_category: sans_serif
      style_description: clean_humanist_sans
      size: small
      weight: regular
      case: sentence_case
      alignment: center
      color: "#f3f1ea"
      path: tree.children[0].children[0]
      confidence: medium
    - id: promo_link
      role: inline_emphasized_action_link
      font_category: sans_serif
      style_description: clean_humanist_sans
      size: small
      weight: bold
      text_decoration: underline
      case: sentence_case
      color: "#ffffff"
      path: tree.children[0].children[1]
      confidence: medium
  font_characteristics:
    - family_guess: geometric_humanist_sans
      contrast: low
      terminals: clean
      confidence: low
  spacing:
    - id: strip_vertical_padding
      role: row_vertical_padding
      value: very_tight
      note: single_line_height_strip
      confidence: medium
    - id: inline_text_link_gap
      role: gap_between_body_and_link
      value: small
      confidence: low
  radius: []
  sizes:
    - id: strip_height
      role: section_height
      value: very_short
      note: slim_single_row_promo_strip
      confidence: high
  opacity: []
  borders: []
  shadows: []
  effects: []
  icons:
    - id: close_x_icon
      role: dismiss_control
      icon_asset_class: single-color-icon
      style: thin_stroke_x
      weight: light_to_regular
      corner_language: sharp
      color: "#f3f1ea"
      container_relationship: bare_glyph_no_container
      path: tree.children[1]
      confidence: medium
  imagery_categories:
    icons:
      - id: close_x_icon
        icon_asset_class: single-color-icon
        placement: foreground_graphic
        rendering: simple_single_stroke_glyph
        palette_relationship: light_glyph_on_inverse_surface
        detail_level: minimal
    illustrations: []
    interfaces: []
    photography: []
  media: []
  creative_direction:
    - target: close_x_icon
      imagery_category: icons
      framing: corner_pinned_utility
      realism_level: flat_vector
      simplicity: very_high
      density: single_glyph
      color_treatment: monochrome_light_on_dark
      placement_relationship: far_right_edge_of_strip
      edge_behavior: contained_with_edge_margin
  implementation_assumptions:
    - target: tree.layers[0]
      assumption: likely_dom_or_layout_element
    - target: close_x_icon
      assumption: likely_svg_or_canvas_graphic
    - target: promo_inline_link
      assumption: likely_dom_or_layout_element
  components:
    - id: promo_inline_link
      role: inline_emphasized_action_link
    - id: close_control
      role: dismiss_icon_button
consolidation_notes:
  likely_tokens:
    colors:
      - inverse_surface_dark_green
      - text_light_on_inverse
      - text_white_emphasis_on_inverse
    gradients: []
    patterns: []
    background_systems:
      - solid_inverse_strip
    typography:
      - promo_body_small_sans
      - promo_link_small_sans_bold_underline
    spacing:
      - very_tight_strip_padding
    radius: []
    shadow: []
    dividers: []
  likely_components:
    - inline_text_link_on_inverse
    - bare_dismiss_icon_button
  likely_section_patterns:
    - full_width_dismissible_promo_strip
  surface_specific_recipes:
    - name: inverse_promo_strip
      surface: dark_green
      text: light_neutral_body_with_white_bold_underline_link
      controls: bare_light_close_glyph
  spacing_and_rhythm_mechanics:
    - single_row_centered_message_with_corner_utility
  link_action_mechanics:
    - inline_link_distinguished_by_bold_weight_and_underline_on_inverse
  distinct_visual_motifs:
    - dark_green_inverse_brand_strip
  imagery_direction_candidates:
    icons:
      - single_color_utility_glyphs_light_on_inverse
    illustrations: []
    interfaces: []
    photography: []
  do_not_generalize:
    - close_x_icon_is_utility_not_decorative_imagery
  uncertainties:
    - detected_label_navigation_header_does_not_match_visible_promo_strip_crop_content
    - exact_strip_background_hex_approximate
    - typography_family_inferred_not_confirmed
    - body_vs_link_text_color_difference_subtle
