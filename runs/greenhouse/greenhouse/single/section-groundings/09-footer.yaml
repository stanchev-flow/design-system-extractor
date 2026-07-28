schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: 9
  total_sections: 9
  detected_label: "Footer"
  previous_section_label: "CTA section"
  next_section_label: "N/A"
  bounds:
    original_y_start: 4980
    original_y_end: 6171
    crop_y_start: 4980
    crop_y_end: 6171
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: footer_multicolumn_with_newsletter
  role: site_footer
  confidence: high
tree:
  id: root
  kind: section
  role: site_footer
  visibility: visible
  size:
    width: full_bleed
    height: tall
  layout:
    type: multi_column_link_grid_plus_aside
    structure: "4 link-column cluster on left ~3/4 width, newsletter+language aside on right, bottom utility row spanning width"
    horizontal_padding: large
    vertical_padding: large
  position:
    in_page: bottom
  style:
    background_color: "deep desaturated green, near #14352b (estimate)"
    background_confidence: high
  layers:
    - id: root_canvas_fill
      role: section_background
      implementation_assumption: likely_dom_or_layout_element
      note: "full-width dark green canvas; reaches all crop edges; continuous with CTA section above (same dark green family) but treated as own footer surface"
  children:
    - id: link_columns_cluster
      kind: container
      role: navigation_link_grid
      layout:
        type: four_column_grid
        columns: 4
        column_alignment: top
        gap: large
      position: {area: left_two_thirds}
      style:
        background_color: inherit_transparent
      children:
        - id: link_column_1
          kind: container
          role: footer_link_column
          layout: {type: vertical_stack_of_grouped_lists, gap: small}
          children:
            - id: group_heading_a
              kind: text
              role: column_group_eyebrow
              style:
                color: "muted/desaturated green, near #5f9c84 (estimate)"
                font_category: sans_serif
                size: small
                weight: medium
                case: none
            - id: link_list_a
              kind: list
              role: footer_link_list
              layout: {type: vertical_stack, gap: small}
              items:
                count_estimate: 8
                representative_child:
                  id: footer_link_item
                  kind: link
                  role: nav_link
                  style:
                    color: "off-white / pale cream, near #f1ede4 (estimate)"
                    font_category: serif
                    size: medium
                    weight: regular
                    underline: none
            - id: group_heading_a2
              kind: text
              role: column_group_eyebrow
              style: {color: muted_green, font_category: sans_serif, size: small, weight: medium}
            - id: link_list_a2
              kind: list
              role: footer_link_list
              items:
                count_estimate: 9
                representative_child: {ref: footer_link_item}
        - id: link_column_2
          kind: container
          role: footer_link_column
          layout: {type: vertical_stack_of_grouped_lists, gap: small}
          children:
            - id: group_heading_b
              kind: text
              role: column_group_eyebrow
              style: {color: muted_green, font_category: sans_serif, size: small, weight: medium}
            - id: link_list_b
              kind: list
              role: footer_link_list
              items: {count_estimate: 3, representative_child: {ref: footer_link_item}}
            - id: group_heading_b2
              kind: text
              role: column_group_eyebrow
            - id: link_list_b2
              kind: list
              role: footer_link_list
              items: {count_estimate: 4, representative_child: {ref: footer_link_item}}
            - id: group_heading_b3
              kind: text
              role: column_group_eyebrow
            - id: link_list_b3
              kind: list
              role: footer_link_list
              items: {count_estimate: 4, representative_child: {ref: footer_link_item}}
        - id: link_column_3
          kind: container
          role: footer_link_column
          layout: {type: vertical_stack_of_grouped_lists, gap: small}
          children:
            - id: group_heading_c
              kind: text
              role: column_group_eyebrow
            - id: link_list_c
              kind: list
              role: footer_link_list
              items: {count_estimate: 4, representative_child: {ref: footer_link_item}}
            - id: group_heading_c2
              kind: text
              role: column_group_eyebrow
            - id: link_list_c2
              kind: list
              role: footer_link_list
              items: {count_estimate: 5, representative_child: {ref: footer_link_item}}
            - id: group_heading_c3
              kind: text
              role: column_group_eyebrow
            - id: link_list_c3
              kind: list
              role: footer_link_list
              items: {count_estimate: 3, representative_child: {ref: footer_link_item}}
    - id: newsletter_aside
      kind: container
      role: newsletter_signup_block
      position: {area: right_column}
      layout: {type: vertical_stack, gap: medium}
      children:
        - id: newsletter_heading
          kind: text
          role: block_title
          style:
            color: pale_cream
            font_category: serif
            size: large
            weight: regular
        - id: newsletter_subtext
          kind: text
          role: supporting_paragraph
          style:
            color: pale_cream
            font_category: serif
            size: medium
            weight: regular
            max_width: narrow
        - id: email_field_group
          kind: container
          role: form_field
          layout: {type: vertical_stack, gap: x_small}
          children:
            - id: email_label
              kind: text
              role: input_label
              style:
                color: pale_cream
                font_category: sans_serif
                size: small
                note: "trailing required-asterisk in amber/orange accent"
            - id: email_input
              kind: input
              role: text_input
              style:
                fill: "white #ffffff"
                radius: medium
                height: large
                border: none_visible
                shadow: none
        - id: subscribe_button
          kind: button
          role: secondary_submit_button
          style:
            fill: transparent
            text_color: pale_cream
            border: "1px solid pale outline (estimate)"
            radius: pill
            padding: "medium horizontal, small vertical"
            note: outline_button_on_dark_surface
        - id: language_selector
          kind: container
          role: language_switcher
          layout: {type: vertical_stack, gap: x_small}
          children:
            - id: language_label
              kind: text
              role: group_label
              style: {color: pale_cream, font_category: serif, size: medium}
            - id: language_options
              kind: list
              role: language_option_list
              items:
                count_estimate: 3
                representative_child:
                  id: language_option
                  kind: link
                  role: language_link
                  style:
                    color: pale_cream
                    font_category: serif
                    size: medium
                    note: "active option underlined; others plain"
    - id: footer_bottom_row
      kind: container
      role: footer_utility_row
      position: {area: full_width_bottom}
      layout: {type: row_with_left_content_and_right_legal_links, justify: space_between}
      children:
        - id: social_icons_row
          kind: list
          role: social_link_row
          layout: {type: horizontal_row, gap: small}
          items:
            count_estimate: 5
            representative_child:
              id: social_icon
              kind: icon_button
              role: social_link
              style:
                shape: circle
                fill: "muted green, near #5f9c84 (estimate)"
                glyph_color: "dark green (knockout)"
                size: medium
        - id: copyright_block
          kind: text
          role: legal_copyright
          style:
            color: pale_cream
            font_category: sans_serif
            size: x_small
            note: "multi-line copyright + trademark statement, low emphasis"
        - id: legal_links_row
          kind: list
          role: legal_link_row
          layout: {type: horizontal_row, gap: large}
          position: {area: bottom_right}
          items:
            count_estimate: 3
            representative_child:
              id: legal_link
              kind: link
              role: legal_nav_link
              style:
                color: pale_cream
                font_category: sans_serif
                size: small
                underline: present
    - id: brand_mark_corner
      kind: icon
      role: brand_logo_mark
      position: {area: bottom_right_corner}
      style:
        shape: circle
        fill: "muted green, near #5f9c84 (estimate)"
        glyph: "lowercase letter mark"
        glyph_color: dark_green
      implementation_assumption: likely_svg_or_canvas_graphic
    - id: chat_widget_overlay
      kind: container
      role: floating_chat_widget
      position: {area: bottom_right, overlay: true}
      style:
        fill: "white #ffffff"
        radius: medium
        shadow: soft_elevated
      note: "overlay component, not part of footer flow; contains greeting title, prompt line, and fine-print disclaimer with inline link"
      children:
        - id: chat_title
          kind: text
          role: widget_title
          style: {color: near_black, font_category: sans_serif, size: medium, weight: semibold}
        - id: chat_prompt
          kind: text
          role: widget_subtext
          style: {color: dark_gray, font_category: sans_serif, size: medium}
        - id: chat_disclaimer
          kind: text
          role: fine_print
          style: {color: gray, font_category: sans_serif, size: x_small, note: "inline underlined policy link"}
component_anatomy:
  actual_page_ui_components:
    - footer_link_columns_with_group_eyebrows
    - newsletter_email_input
    - subscribe_outline_button
    - language_switcher_links
    - social_icon_buttons
    - legal_utility_links
    - brand_logo_mark
    - floating_chat_widget_overlay
  embedded_or_showcase_only_ui: []
  absent_common_components:
    - back_to_top_button
    - footer_logo_lockup_full
observed_values:
  colors:
    - id: footer_canvas_green
      value: "#14352b approx"
      role: section_background
      path: root.layers.root_canvas_fill
      confidence: high
    - id: eyebrow_green
      value: "#5f9c84 approx"
      role: group_heading_text
      path: tree.link_columns_cluster..group_heading_a
      confidence: medium
    - id: link_cream
      value: "#f1ede4 approx"
      role: link_and_body_text
      path: tree..footer_link_item
      confidence: high
    - id: input_white
      value: "#ffffff"
      role: input_fill
      path: tree.newsletter_aside.email_field_group.email_input
      confidence: high
    - id: accent_amber
      value: "amber/orange (required asterisk)"
      role: minor_accent
      path: tree.newsletter_aside.email_field_group.email_label
      confidence: medium
    - id: social_chip_green
      value: "#5f9c84 approx"
      role: icon_button_fill
      path: tree.footer_bottom_row.social_icons_row
      confidence: medium
  gradients: []
  patterns: []
  background_systems:
    - id: footer_surface
      type: solid_dark_fill
      layers: [root_canvas_fill]
      note: "single flat dark green; no visible texture in footer body (decorative leaf motif belongs to prior CTA section)"
      path: root.layers
      confidence: high
  typography:
    - id: type_group_eyebrow
      sample_role: column_heading
      font_category: sans_serif
      size: small
      weight: medium
      case: none
      color: eyebrow_green
      path: tree..group_heading_a
    - id: type_footer_link
      sample_role: nav_link
      font_category: serif
      size: medium
      weight: regular
      line_height: comfortable
      color: link_cream
      path: tree..footer_link_item
    - id: type_block_title
      sample_role: newsletter_title
      font_category: serif
      size: large
      weight: regular
      color: link_cream
      path: tree.newsletter_aside.newsletter_heading
    - id: type_body
      sample_role: newsletter_subtext
      font_category: serif
      size: medium
      color: link_cream
      path: tree.newsletter_aside.newsletter_subtext
    - id: type_label_small
      sample_role: input_label
      font_category: sans_serif
      size: small
      color: link_cream
      path: tree.newsletter_aside.email_field_group.email_label
    - id: type_legal
      sample_role: copyright_finerprint
      font_category: sans_serif
      size: x_small
      color: link_cream
      path: tree.footer_bottom_row.copyright_block
  font_characteristics:
    - note: "two-family system: serif for content/links/titles, sans-serif for eyebrows, labels, legal text"
  spacing:
    - id: column_gap
      value: large
      path: tree.link_columns_cluster
    - id: link_item_gap
      value: small
    - id: section_padding
      value: large_all_sides
  radius:
    - id: input_radius
      value: medium
      path: tree.newsletter_aside.email_field_group.email_input
    - id: button_radius
      value: pill
      path: tree.newsletter_aside.subscribe_button
    - id: social_chip_radius
      value: full_circle
      path: tree.footer_bottom_row.social_icons_row
  sizes:
    - id: social_icon_size
      value: medium_circle
    - id: input_height
      value: large
  opacity: []
  borders:
    - id: subscribe_outline
      value: "1px pale outline"
      path: tree.newsletter_aside.subscribe_button
      confidence: medium
  shadows:
    - id: chat_widget_shadow
      value: soft_elevated
      path: tree.chat_widget_overlay
  effects: []
  icons:
    - id: social_glyphs
      icon_asset_class: single-color-icon
      style: "filled knockout glyphs inside solid green circles"
      set: "social platform marks x5"
      container_relationship: circular_chip
      path: tree.footer_bottom_row.social_icons_row
    - id: brand_corner_mark
      icon_asset_class: logo/wordmark
      style: "single-letter mark in circular green chip"
      note: "approximate as small circular badge"
      path: tree.brand_mark_corner
  imagery_categories:
    icons:
      - id: footer_social_icons
        icon_asset_class: single-color-icon
        placement: foreground_graphic
        density: low
        simplicity: high
        palette_relationship: "green chip with dark knockout glyph on dark surface"
      - id: footer_brand_mark
        icon_asset_class: logo/wordmark
        placement: foreground_graphic
    illustrations: []
    interfaces: []
    photography: []
  media: []
  creative_direction:
    - id: footer_icon_direction
      category: icons
      framing: contained_in_circular_chip
      realism_level: flat_vector
      color_treatment: two_tone_monochrome
      composition: evenly_spaced_horizontal_row
      placement: foreground_graphic
      simplicity: high
      detail_level: low
  implementation_assumptions:
    - target: root.layers.root_canvas_fill
      assumption: likely_dom_or_layout_element
    - target: tree.footer_bottom_row.social_icons_row
      assumption: likely_svg_or_canvas_graphic
    - target: tree.brand_mark_corner
      assumption: likely_svg_or_canvas_graphic
    - target: tree.chat_widget_overlay
      assumption: likely_dom_or_layout_element
  components:
    - id: footer_link_column
      role: navigation
      surface: transparent_on_dark
      separation: whitespace_and_color_contrast
    - id: newsletter_form
      role: email_capture
      surface: transparent_on_dark
      controls: [white_input, outline_pill_button]
    - id: social_icon_chip
      role: social_link
      surface: green_chip_on_dark
consolidation_notes:
  likely_tokens:
    colors:
      - "footer.bg = deep green"
      - "footer.eyebrow = muted green"
      - "footer.text = pale cream"
      - "input.bg = white"
    gradients: []
    patterns: []
    background_systems:
      - "flat dark footer surface"
    typography:
      - "serif link/body, sans-serif eyebrow/label/legal"
    spacing:
      - "large section padding, large column gap, small link gap"
    radius:
      - "pill button, medium input, full-circle social chip"
    shadow:
      - "elevated overlay shadow for chat widget"
    dividers: []
  likely_components:
    - footer_multicolumn_nav
    - inline_newsletter_signup
    - language_switcher
    - social_icon_row
    - legal_utility_row
  likely_section_patterns:
    - "dark footer with 4 link columns + right newsletter aside + bottom utility row"
  surface_specific_recipes:
    - "outline_button_on_dark_surface for Subscribe"
    - "white_input_on_dark_surface for email field"
    - "green_chip_with_knockout_glyph for social icons"
  spacing_and_rhythm_mechanics:
    - "grouped link lists stacked with sub-eyebrows within single columns"
  link_action_mechanics:
    - "footer nav links plain (no underline); legal links underlined; active language underlined"
  distinct_visual_motifs:
    - "serif body links over flat dark green"
    - "circular green social chips"
  imagery_direction_candidates:
    icons:
      - "flat two-tone monochrome glyphs in circular chips, high simplicity"
    illustrations: []
    interfaces: []
    photography: []
  do_not_generalize:
    - "chat_widget_overlay is a floating product widget, not a footer layout module"
    - "leaf/texture motif visible above belongs to prior CTA section, not this footer"
  uncertainties:
    - "exact hex values approximate"
    - "subscribe button border presence low-confidence on dark surface"
    - "asterisk accent color (amber) approximate"
