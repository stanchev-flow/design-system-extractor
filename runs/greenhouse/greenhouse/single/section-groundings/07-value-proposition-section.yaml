yaml
schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: 7
  total_sections: 9
  detected_label: "Value proposition section"
  previous_section_label: "Customer logos"
  next_section_label: "CTA section"
  bounds:
    original_y_start: 2980
    original_y_end: 4040
    crop_y_start: 2980
    crop_y_end: 4040
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: value_prop_three_column_feature
  role: feature_grid_section
  confidence: high
tree:
  id: root
  kind: section
  role: feature_grid_section
  visibility: visible
  size:
    width: full_bleed
    height: tall_section
  layout:
    type: vertical_stack
    structure: section_heading_over_three_column_card_grid
    content_max_width: centered_constrained_container
    horizontal_gutters: generous
  position:
    in_page: lower_middle
  style:
    background_color: white_or_near_white
    background_confidence: high
    background_evidence: full_width_left_right_edges_and_top_bottom_gutters_uniform_white
  layers:
    - id: section_canvas
      role: base_surface
      implementation_assumption: likely_dom_or_layout_element
      style:
        fill: white
  children:
    - id: section_heading_block
      kind: text_block
      role: section_title
      visibility: visible
      layout:
        type: single_block
        alignment: left
        max_width: roughly_half_to_two_thirds_container
      style:
        typography_ref: heading_serif_xl
        color: dark_green
      notes: "Large multi-line serif headline, left aligned, primary section title"
    - id: feature_grid
      kind: grid
      role: three_column_feature_grid
      visibility: visible
      layout:
        type: horizontal_grid
        columns: 3
        column_gap: medium_large
        alignment: top
      children:
        - id: feature_card_representative
          kind: card
          role: feature_item
          visibility: visible
          repeated: true
          instances: 3
          layout:
            type: vertical_stack
            order: [image, title, body, link]
            gap: small_medium
          style:
            background_color: transparent_inherits_section
            border: none
            shadow: none
          children:
            - id: feature_image
              kind: image_frame
              role: feature_media
              visibility: visible
              layout:
                aspect: landscape_wide
                fill: full_column_width
              style:
                radius: small_rounded_corners
              children:
                - id: feature_photo
                  kind: image
                  role: photographic_asset
                  imagery_category: photography
                  notes: "Candid workplace/people photography, warm natural lighting"
            - id: feature_title
              kind: text
              role: card_heading
              style:
                typography_ref: heading_serif_md
                color: dark_green
              notes: "Two-line serif subheading"
            - id: feature_body
              kind: text
              role: card_body
              style:
                typography_ref: body_sans_md
                color: dark_neutral_gray
              notes: "Short supporting paragraph"
            - id: feature_link
              kind: link
              role: text_link
              style:
                typography_ref: link_sans_md
                color: dark_green
                decoration: underline
              notes: "Inline underlined text link, accent-on-light"
component_anatomy:
  actual_page_ui_components:
    - id: section_title
      type: heading
      notes: "Large serif section headline"
    - id: feature_card
      type: feature_item
      count: 3
      notes: "Image + serif subhead + body + underlined link, no card chrome"
    - id: text_link
      type: inline_link
      count: 3
      notes: "Underlined dark-green link under each feature"
  embedded_or_showcase_only_ui: []
  absent_common_components:
    - buttons_with_fill
    - badges
    - icons
    - dividers
observed_values:
  colors:
    - id: surface_white
      value: "#ffffff"
      role: section_background
      path: tree.style.background_color
      confidence: high
    - id: text_dark_green
      value: "#1f3b2c_approx"
      role: heading_and_link_color
      path: tree.children[0]
      confidence: high
    - id: text_body_gray
      value: "#444a47_approx"
      role: body_text
      path: feature_card_representative.children.feature_body
      confidence: medium
  gradients: []
  patterns: []
  background_systems:
    - id: section_bg_system
      type: flat_fill
      layers:
        - flat_white_canvas
      path: tree.layers.section_canvas
      confidence: high
  typography:
    - id: heading_serif_xl
      role: section_title
      font_category: serif
      style_description: high_contrast_traditional_serif
      size: very_large
      line_height: tight
      weight: regular_to_medium
      case: sentence
      alignment: left
      color: dark_green
      path: tree.children[0]
    - id: heading_serif_md
      role: card_heading
      font_category: serif
      size: large
      line_height: snug
      weight: regular
      case: sentence
      alignment: left
      color: dark_green
      path: feature_card_representative.children.feature_title
    - id: body_sans_md
      role: card_body
      font_category: sans_serif
      size: medium
      line_height: relaxed
      weight: regular
      case: sentence
      alignment: left
      color: dark_neutral_gray
      path: feature_card_representative.children.feature_body
    - id: link_sans_md
      role: text_link
      font_category: sans_serif
      size: medium
      weight: medium
      decoration: underline
      color: dark_green
      path: feature_card_representative.children.feature_link
  font_characteristics:
    - serif_headings_high_contrast_editorial
    - sans_body_neutral_humanist
  spacing:
    - id: heading_to_grid_gap
      value: large
      path: tree.children
    - id: image_to_title_gap
      value: medium
      path: feature_card_representative
    - id: column_gap
      value: medium_large
      path: feature_grid.layout.column_gap
  radius:
    - id: image_corner_radius
      value: small
      path: feature_image.style.radius
  sizes:
    - id: feature_image_aspect
      value: landscape_wide_approx_3x2
      path: feature_image
  opacity: []
  borders: []
  shadows: []
  effects: []
  icons: []
  imagery_categories:
    icons: []
    illustrations: []
    interfaces: []
    photography:
      - id: feature_photo_set
        count: 3
        subject_context_local: "people in workplace/collaboration settings"
        framing: medium_close_portrait_and_environmental
        crop: tight_to_subjects
        perspective: eye_level
        realism_level: realistic_photographic
        lighting: warm_natural_soft
        material_texture: natural_skin_fabric_foliage
        color_treatment: warm_earthy_muted
        composition: subject_centered_with_environmental_context
        placement: foreground_media
        edge_behavior: photo_reaches_frame_edges_within_rounded_mask
        density: medium
        simplicity: moderate_detail
        detail_level: high
        path: feature_card_representative.children.feature_image.children.feature_photo
  media:
    - id: feature_media_slots
      type: photographic_image
      count: 3
      placement: foreground_media
      path: feature_image
  creative_direction:
    - id: photography_direction
      category: photography
      intent: humanized_authentic_workplace_imagery
      framing: portrait_and_candid
      realism: photographic
      lighting: warm_natural
      palette_relationship: earthy_warm_complementary_to_green_brand
      edge: rounded_rect_masked_full_bleed_photo
      notes: "Consistent warm candid people photography across three slots"
  implementation_assumptions:
    - id: section_is_layout_element
      target: tree
      implementation_assumption: likely_dom_or_layout_element
    - id: photos_are_raster
      target: feature_photo
      implementation_assumption: likely_raster_image
  components:
    - id: feature_card_pattern
      summary: "Chrome-less feature item: rounded photo, serif heading, body, underlined link"
      count: 3
consolidation_notes:
  likely_tokens:
    colors:
      - white_section_surface
      - dark_green_text_and_link
      - neutral_gray_body
    gradients: []
    patterns: []
    background_systems:
      - flat_white_section
    typography:
      - serif_display_heading
      - serif_subheading
      - sans_body
      - underlined_text_link
    spacing:
      - section_vertical_rhythm_large
      - card_internal_gap_medium
    radius:
      - small_image_radius
    shadow: []
    dividers: []
  likely_components:
    - three_column_feature_grid
    - chromeless_feature_card
    - inline_underlined_text_link
  likely_section_patterns:
    - heading_plus_three_feature_columns_with_photos
  surface_specific_recipes:
    - "text_link_accent_on_light_surface underlined dark-green"
    - "serif_heading_on_light_surface dark-green"
  spacing_and_rhythm_mechanics:
    - heading_left_aligned_constrained_width
    - equal_three_column_distribution
  link_action_mechanics:
    - underlined_inline_links_below_each_column
  distinct_visual_motifs:
    - editorial_serif_headings
    - warm_candid_human_photography
  imagery_direction_candidates:
    icons: []
    illustrations: []
    interfaces: []
    photography:
      - warm_authentic_workplace_people_photography_rounded_full_bleed
  do_not_generalize:
    - photo_subjects_are_slot_context_not_required_subjects
  uncertainties:
    - exact_body_text_gray_value_approx
    - precise_image_corner_radius
