schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: 6
  total_sections: 9
  detected_label: "Customer logos"
  previous_section_label: "Three feature cards"
  next_section_label: "Value proposition section"
  bounds:
    original_y_start: 2150
    original_y_end: 2980
    crop_y_start: 2150
    crop_y_end: 2980
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: social_proof_logo_section
  role: generic_section_role
  confidence: high
tree:
  id: root
  kind: section
  role: generic_section_role
  visibility: visible
  size:
    width: full_bleed
    height: tall_band
  layout:
    type: two_column_split
    columns: 2
    split_ratio: approx_balanced_left_text_right_logos
    vertical_divider: thin_vertical_rule_between_columns
    alignment: left_column_vertically_centered
  position:
    in_page: middle_band
  style:
    background_color:
      value: "#ffffff"
      note: full_width_white_canvas_visible_at_left_right_edges_and_gutters
      confidence: high
  layers:
    - id: base_canvas
      role: section_background
      implementation_assumption: likely_dom_or_layout_element
      style:
        fill: "#ffffff"
  children:
    - id: left_text_column
      kind: container
      role: heading_and_cta_stack
      layout:
        type: vertical_stack
        gap: medium
        alignment: left
        vertical_position: centered_in_band
      children:
        - id: heading_block
          kind: text
          role: section_heading
          style:
            typography_ref: heading_serif
            color: "#1f3d2f"
          notes: "two_line_serif_heading_on_light_surface"
        - id: cta_button
          kind: button
          role: primary_pill_button
          style:
            surface: "#1f7a52"
            text_color: "#ffffff"
            radius: full_pill
            padding: medium_horizontal_small_vertical
            sizing: hug_content
          notes: "primary_button_on_light_surface_solid_green_pill"
    - id: vertical_divider
      kind: divider
      role: column_separator
      style:
        orientation: vertical
        thickness: hairline
        color: "#d8e0db"
      notes: "thin_vertical_rule_separating_text_and_logo_columns"
    - id: right_logo_grid
      kind: container
      role: customer_logo_grid
      layout:
        type: grid
        columns: 2
        rows: 3
        gap: large
        alignment: center_each_cell
      children:
        - id: logo_cell_representative
          kind: image
          role: customer_logo_slot
          repeated: true
          count: 6
          implementation_assumption: likely_raster_image
          style:
            footprint: small_to_medium_wordmark_or_mark
            background_relationship: directly_on_white_surface_no_container
          notes: "six_brand_logos_2x3_grid_mixed_color_marks_on_white"
component_anatomy:
  actual_page_ui_components:
    - id: cta_button
      type: primary_pill_button
      host_surface: white_section_canvas
      child_fill: solid_green
      text_color: white
      border: none
      shadow: none
      sizing: hug_content
      separation: color_contrast_against_white
    - id: vertical_divider
      type: column_divider
      orientation: vertical
      color: pale_green_gray
    - id: logo_grid
      type: logo_wall
      layout: 2x3
      cells_on: white_surface_no_individual_containers
  embedded_or_showcase_only_ui: []
  absent_common_components:
    - secondary_button
    - eyebrow_label
    - body_paragraph
    - card_containers
observed_values:
  colors:
    - id: canvas_white
      value: "#ffffff"
      role: section_background
      path: tree.style.background_color
      confidence: high
    - id: heading_green
      value: "#1f3d2f"
      role: heading_text
      path: tree.children[0].children[0]
      confidence: high
    - id: button_green
      value: "#1f7a52"
      role: primary_button_surface
      path: tree.children[0].children[1]
      confidence: high
    - id: button_text_white
      value: "#ffffff"
      role: button_label
      path: tree.children[0].children[1]
      confidence: high
    - id: divider_pale
      value: "#d8e0db"
      role: divider
      path: tree.children[1]
      confidence: medium
    - id: logo_blue
      value: "#1a47c2"
      role: customer_logo_color
      note: blue_wordmark_top_right
      confidence: medium
    - id: logo_orange_red
      value: "#ff5240"
      role: customer_logo_color
      note: orange_red_wordmark_bottom_right
      confidence: medium
    - id: logo_black
      value: "#111111"
      role: customer_logo_color
      note: black_wordmarks
      confidence: medium
  gradients: []
  patterns: []
  background_systems:
    - id: section_bg_system
      type: flat_single_color
      layers:
        - flat_white_fill
      path: tree.layers[0]
      confidence: high
  typography:
    - id: heading_serif
      role: section_heading
      font_category: serif
      style_description: classic_high_contrast_serif
      visual_characteristics: refined_editorial_two_line
      size: large
      line_height: tight_to_medium
      weight: regular_to_medium
      letter_spacing: normal
      case: sentence
      alignment: left
      color: "#1f3d2f"
      path: tree.children[0].children[0]
    - id: button_label
      role: button_text
      font_category: sans_serif
      style_description: clean_geometric_sans
      size: small
      weight: medium
      letter_spacing: slight
      case: sentence
      alignment: center
      color: "#ffffff"
      path: tree.children[0].children[1]
  font_characteristics:
    - id: heading_serif_traits
      contrast: high_stroke_contrast
      terminals: bracketed_serifs
      mood: editorial_trustworthy
  spacing:
    - id: section_vertical_padding
      role: band_padding
      value: generous
      note: tall_whitespace_above_below_content
    - id: heading_to_button_gap
      value: medium
    - id: logo_grid_gap
      value: large
  radius:
    - id: button_radius
      value: full_pill
      path: tree.children[0].children[1]
  sizes:
    - id: button_size
      value: compact_pill
    - id: logo_footprint
      value: small_medium_uniform_optical
  opacity: []
  borders:
    - id: divider_border
      value: hairline_vertical
      color: "#d8e0db"
  shadows: []
  effects: []
  icons: []
  imagery_categories:
    icons: []
    illustrations: []
    interfaces: []
    photography: []
  media:
    - id: customer_logos
      type: logo_wall
      count: 6
      arrangement: 2x3_grid
      placement: foreground_graphic
      surface_relationship: logos_directly_on_white_no_frames
  creative_direction:
    - id: logo_wall_direction
      imagery_category: icons
      icon_asset_class: logo/wordmark
      framing: each_logo_optically_centered_in_grid_cell
      crop: full_logo_visible
      realism_level: flat_brand_marks
      color_treatment: native_brand_colors_mixed_blue_red_black_plus_one_multicolor_shield
      composition: even_2x3_grid_with_large_whitespace
      density: sparse_airy
      simplicity: high
      placement_relationship: right_column_beside_text
      edge_behavior: contained_within_column_not_bleeding
      detail_level: low_each_mark_simple_wordmark_or_small_emblem
      note: "treat_as_logo_slots_approximable_as_text_or_small_rect_blocks_do_not_promote_to_reusable_illustration"
  implementation_assumptions:
    - id: section_root
      target: tree
      assumption: likely_dom_or_layout_element
    - id: logos
      target: tree.children[2]
      assumption: likely_raster_image
    - id: button
      target: tree.children[0].children[1]
      assumption: likely_dom_or_layout_element
  components:
    - id: primary_pill_button
      path: tree.children[0].children[1]
      summary: solid_green_pill_white_label_hug_width
    - id: logo_grid_2x3
      path: tree.children[2]
      summary: six_customer_logos_on_white_split_layout
consolidation_notes:
  likely_tokens:
    colors:
      - canvas_white
      - heading_green_dark
      - primary_green
      - button_text_white
      - divider_pale_green_gray
    gradients: []
    patterns: []
    background_systems:
      - flat_white_section
    typography:
      - editorial_serif_heading
      - sans_button_label
    spacing:
      - generous_band_padding
      - logo_grid_large_gap
    radius:
      - full_pill
    shadow: []
    dividers:
      - hairline_vertical_column_rule
  likely_components:
    - primary_pill_button
    - customer_logo_wall
    - vertical_column_divider
  likely_section_patterns:
    - split_text_left_logos_right_social_proof
  surface_specific_recipes:
    - primary_button_on_light_surface
    - logo_marks_directly_on_white_no_card
  spacing_and_rhythm_mechanics:
    - vertically_centered_left_text_against_taller_logo_grid
  link_action_mechanics:
    - single_primary_cta_pill
  distinct_visual_motifs:
    - airy_logo_wall_with_native_brand_colors
    - editorial_serif_headline
  imagery_direction_candidates:
    icons:
      - logo_wordmark_slots_simple_low_detail_native_colors
    illustrations: []
    interfaces: []
    photography: []
  do_not_generalize:
    - specific_brand_marks_are_slot_context_only
  uncertainties:
    - exact_brand_logo_hex_values_approximate
    - divider_color_low_confidence
    - top_bottom_transition_to_neighbors_assumed_same_white_canvas
