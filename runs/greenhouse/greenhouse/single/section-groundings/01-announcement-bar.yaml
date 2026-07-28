schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: 1
  total_sections: 9
  detected_label: "Announcement bar"
  previous_section_label: "N/A"
  next_section_label: "Navigation / header"
  bounds:
    original_y_start: 0
    original_y_end: 21
    crop_y_start: 0
    crop_y_end: 21
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: announcement_bar
  role: promo_announcement_strip
  confidence: high
tree:
  id: root
  kind: section
  role: promo_announcement_strip
  visibility: visible
  size:
    width: full_bleed
    height: very_short_strip
    note: "thin horizontal bar spanning full viewport width"
  layout:
    type: single_centered_row
    direction: horizontal
    align: center
    justify: center
    note: "single inline message with trailing inline link, horizontally centered; close affordance likely at far right"
  position:
    placement: page_top_edge
    sticky: unclear
  style:
    background_color:
      role: inverse_dark_surface
      value_approx: "#16332a"
      note: "deep desaturated green full-bleed strip; reaches both crop edges"
    text_alignment: center
  layers:
    - id: bg_fill
      kind: background_layer
      role: solid_inverse_surface
      implementation_assumption: likely_dom_or_layout_element
      style:
        fill: "deep green solid, no visible gradient or texture"
  children:
    - id: announcement_message
      kind: text_block
      role: inline_promo_message
      visibility: visible
      layout:
        type: inline_run
        align: center
      style:
        color: inverse_light_text_low_emphasis
      note: "short promo sentence in light/muted tone against dark green"
      children:
        - id: announcement_link
          kind: link
          role: inline_text_link
          visibility: visible
          style:
            color: inverse_light_text_high_emphasis
            text_decoration: underline
            font_weight: bold
          note: "trailing call-to-action link, bold + underlined, brighter than surrounding text"
    - id: close_affordance
      kind: icon_button
      role: dismiss_control
      visibility: low_confidence
      position:
        placement: far_right_edge
      note: "small close/x glyph implied at right edge from full-page context; not clearly resolvable in crop"
component_anatomy:
  actual_page_ui_components:
    - id: announcement_message
      type: promo_text_with_inline_link
      host_surface: inverse_dark_strip
      text_color: light_on_dark
      link_treatment: bold_underline_inline
      sizing_behavior: full_width_centered
      separation_mechanism: color_contrast_against_lighter_navbar_below
      note: "primary_inline_link_on_inverse_strong"
    - id: close_affordance
      type: dismiss_icon_button
      host_surface: inverse_dark_strip
      icon_color: light_on_dark
      confidence: low
  embedded_or_showcase_only_ui: []
  absent_common_components:
    - buttons
    - inputs
    - tabs
    - badges
observed_values:
  colors:
    - id: color_strip_bg
      role: section_background_inverse
      value_approx: "#16332a"
      path: tree.style.background_color
      confidence: high
    - id: color_message_text
      role: inverse_text_low_emphasis
      value_approx: "#cdd6d0"
      path: tree.children[0].style.color
      confidence: medium
    - id: color_link_text
      role: inverse_text_high_emphasis
      value_approx: "#ffffff"
      path: tree.children[0].children[0].style.color
      confidence: medium
  gradients: []
  patterns: []
  background_systems:
    - id: bg_inverse_solid
      type: solid_surface
      layers:
        - solid_deep_green_fill
      path: tree.layers[0]
      confidence: high
  typography:
    - id: type_announcement_message
      role: promo_body_inline
      font_category: sans_serif
      style_description: "small, regular weight, centered"
      size: very_small
      weight: regular
      case: sentence
      alignment: center
      color: inverse_text_low_emphasis
      path: tree.children[0]
      confidence: medium
    - id: type_announcement_link
      role: promo_inline_link
      font_category: sans_serif
      style_description: "small, bold, underlined inline link"
      size: very_small
      weight: bold
      text_decoration: underline
      color: inverse_text_high_emphasis
      path: tree.children[0].children[0]
      confidence: medium
  font_characteristics:
    - "neutral grotesque/sans, no notable distinctive features at this size"
  spacing:
    - id: strip_vertical_padding
      role: minimal_vertical_padding
      value_approx: tight
      note: "very thin bar; only a few px above/below single text line"
      confidence: medium
  radius: []
  sizes:
    - id: strip_height
      role: bar_height
      value_approx: "~21px"
      path: tree.size.height
      confidence: high
  opacity:
    - id: message_text_opacity
      role: muted_inverse_text
      note: "message slightly lower contrast than link"
      confidence: low
  borders: []
  shadows: []
  effects: []
  icons:
    - id: icon_close
      role: dismiss_control_glyph
      icon_asset_class: single-color-icon
      style: thin_stroke_x_glyph
      color: light_on_dark
      container_relationship: bare_glyph_far_right
      confidence: low
  imagery_categories:
    icons:
      - id: icon_close
        icon_asset_class: single-color-icon
        placement: foreground_graphic
        confidence: low
        note: "implied close affordance at right; not clearly visible in crop"
    illustrations: []
    interfaces: []
    photography: []
  media: []
  creative_direction:
    - scope: section
      summary: "Minimal full-bleed inverse announcement strip; pure typographic message with one bold underlined inline link; no imagery, no decoration."
      palette_relationship: "light text on deep green inverse surface"
      density: very_low
      simplicity: very_high
  implementation_assumptions:
    - target: tree
      assumption: likely_dom_or_layout_element
    - target: bg_fill
      assumption: likely_dom_or_layout_element
    - target: close_affordance
      assumption: likely_svg_or_canvas_graphic
  components:
    - id: announcement_message
      role: promo_text_with_inline_link
      confidence: high
    - id: close_affordance
      role: dismiss_icon_button
      confidence: low
consolidation_notes:
  likely_tokens:
    colors:
      - "inverse_dark_surface_green (~#16332a)"
      - "inverse_text_high_emphasis (~#ffffff)"
      - "inverse_text_low_emphasis (~#cdd6d0)"
    gradients: []
    patterns: []
    background_systems:
      - "solid_inverse_strip"
    typography:
      - "promo_inline_small_regular"
      - "promo_inline_small_bold_underline_link"
    spacing:
      - "tight_announcement_bar_padding"
    radius: []
    shadow: []
    dividers: []
  likely_components:
    - "announcement_bar_with_inline_link_and_dismiss"
  likely_section_patterns:
    - "full_bleed_inverse_promo_strip_top_of_page"
  surface_specific_recipes:
    - "primary_inline_link_on_inverse_strong: bold + underline, brighter than body text"
  spacing_and_rhythm_mechanics:
    - "single line height defines bar height; minimal vertical padding"
  link_action_mechanics:
    - "inline trailing CTA link distinguished by bold weight and underline"
  distinct_visual_motifs:
    - "deep green inverse strip distinct from white nav below it"
  imagery_direction_candidates:
    icons:
      - "single-color light close glyph on dark surface"
    illustrations: []
    interfaces: []
    photography: []
  do_not_generalize:
    - "do not treat deep green here as global page background; it is a localized inverse strip"
  uncertainties:
    - "close icon presence and exact placement low confidence"
    - "exact text colors and sizes approximate due to very small crop height"
    - "top edge stickiness unknown"
