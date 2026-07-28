# Structural Analysis

## Section Inventory

Here are the visually distinct top-level sections from top to bottom:

- **Announcement Bar**: A thin dark green strip at the very top promoting an upcoming live demo webinar with a "Register now" link. It is a separate section because it sits above the navigation as a narrow standalone promo banner.

- **Navigation / Header**: A white bar with the Greenhouse logo, menu links (Platform, Why Greenhouse, Resources, About, Community), and "Sign In" / "Request a demo" buttons. It is its own section because it is the persistent top navigation distinct from the content below.

- **Hero**: A mint-green block with the headline "The only hiring platform you'll ever need," supporting text, CTA buttons, and surrounding photos plus UI snippet graphics. It is separate because it is the primary introductory banner with its own background color.

- **Acquisition Notice Bar**: A dark green strip stating Greenhouse has entered an agreement to acquire Ezra AI Labs, with a "Go to Newsroom" link. It is distinct due to its contrasting dark background and standalone announcement role.

- **Three Product Feature Cards**: A white section with three columns (Greenhouse AI, Real Talent, MyGreenhouse), each with an image, description, and "Learn more" button. It is a separate section grouping parallel product highlights on a clean white background.

- **Customer Logos**: A section titled "Great companies hire with Greenhouse" with a "Read customer stories" button beside a grid of brand logos (NFL, Coursera, Anthropic, Datavant, Revlon, SeatGeek). It is distinct as a social-proof logo block with its own layout.

- **Best Teams Feature Section**: A heading "The best teams start with hiring..." followed by three image-and-text columns (Everything you need, Flex and scale, Future-proof). It is a separate section combining its heading with the related three-column content below.

- **CTA Banner**: A large dark green block with "Everything you need to get better at hiring" and a "Request a demo" button alongside a leaf graphic. It is distinct because of its full-width dark background and standalone call-to-action role.

- **Footer**: A darker green area with multiple link columns (Platform, Why Greenhouse, About, etc.), newsletter signup, language selector, social icons, and legal text. It is the closing section with site-wide navigation and legal info.

## Section 1: Announcement Bar

- **Approximate boundaries:** y=0 to y=22
- **Generic role:** see grounded section observations below
- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.

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

## Section 2: Navigation / Header

- **Approximate boundaries:** y=22 to y=58
- **Generic role:** see grounded section observations below
- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.

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

## Section 3: Hero

- **Approximate boundaries:** y=58 to y=390
- **Generic role:** see grounded section observations below
- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.

schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: 3
  total_sections: 9
  detected_label: "Hero section"
  previous_section_label: "Navigation / header"
  next_section_label: "Acquisition notice bar"
  bounds:
    original_y_start: 55
    original_y_end: 393
    crop_y_start: 55
    crop_y_end: 393
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: hero_visual_collage_top
  role: hero_section
  confidence: medium
tree:
  id: root
  kind: section
  role: hero_section
  visibility: visible
  size:
    width: full_bleed
    height: tall_partial_in_crop
    note: "Crop shows top band of hero plus a thin continuation of the nav/header at the very top edge"
  layout:
    type: layered_collage
    arrangement: "Central headline/value-prop column flanked by floating media cards and photo tiles; multiple overlapping foreground graphics on a flat mint canvas"
    alignment: center_anchored_with_peripheral_media
  position:
    in_page: third_section
  style:
    background_color:
      role: section_canvas
      value: pale_mint_green
      confidence: medium
      note: "Flat soft mint/aqua fill reaches left and right crop edges as the hero canvas; thin white nav band visible at top edge belongs to previous section"
  layers:
    - id: canvas_fill
      role: base_surface
      description: "Flat pale mint-green field spanning full width"
      implementation_assumption: likely_dom_or_layout_element
    - id: floating_graphics_layer
      role: foreground_overlay
      description: "Floating candidate card, pill chip, connector line, and photo tiles overlapping the mint canvas"
      implementation_assumption: likely_dom_or_layout_element
  children:
    - id: top_nav_continuation
      kind: region
      role: header_edge_continuation
      visibility: visible
      note: "Top sliver of the white navigation/header from previous section appears at crop top; not owned by this hero"
      style:
        background_color: white
      children:
        - id: nav_logo_slot
          kind: logo
          role: brand_wordmark
          style:
            text_color: green_brand
          notes: "Lowercase wordmark, green"
        - id: nav_links
          kind: nav_list
          role: primary_nav
          layout: { type: horizontal_row }
          items:
            - { id: nav_item, role: nav_link, repeat: ~5, style: { text_color: near_black } }
        - id: nav_signin_btn
          kind: button
          role: secondary_button
          style:
            child_surface: transparent
            border: pill_outline_thin
            text_color: near_black
            radius: pill
        - id: nav_demo_btn
          kind: button
          role: primary_button
          style:
            child_surface: blue
            text_color: white
            radius: pill
        - id: nav_search_icon
          kind: icon_button
          role: search_affordance
          style:
            icon_color: near_black
    - id: hero_canvas
      kind: container
      role: hero_collage_canvas
      visibility: visible
      style:
        background_color: pale_mint_green
      layout:
        type: free_overlap
      children:
        - id: candidate_card
          kind: card
          role: floating_profile_card
          visibility: visible
          position: { area: upper_center }
          style:
            child_surface: white
            radius: medium_rounded
            shadow: soft_elevation
          children:
            - id: candidate_avatar
              kind: image
              role: profile_thumbnail
              style: { shape: rounded_square }
            - id: candidate_name
              kind: text
              role: card_title
              style: { weight: medium, size: small, color: near_black }
            - id: candidate_role_label
              kind: text
              role: card_subtitle
              style: { size: x_small, color: muted_gray }
            - id: status_badge
              kind: badge
              role: status_tag
              style:
                child_surface: green_solid
                text_color: white
                radius: small_rounded
                leading_icon: true
              note: "embedded_showcase_only style badge inside product card"
            - id: card_meta_row
              kind: text
              role: secondary_meta
              style: { size: x_small, color: muted_gray, leading_icon: true }
        - id: connector_line
          kind: graphic
          role: connector_path
          visibility: visible
          style:
            stroke: thin_green_line
            shape: curved_bezier
          implementation_assumption: likely_svg_or_canvas_graphic
          note: "Thin green curved line linking candidate card to pill chip"
        - id: source_pill_chip
          kind: chip
          role: feature_pill_label
          visibility: visible
          position: { area: center_right }
          style:
            child_surface: muted_teal_green
            text_color: dark_green
            radius: pill
            leading_icon: true
          children:
            - id: chip_icon
              kind: icon
              role: support_glyph
              style: { color: dark_green }
            - id: chip_text
              kind: text
              role: chip_label
              style: { size: small, weight: medium, color: dark_green }
        - id: photo_tile_left
          kind: image
          role: collage_photo
          visibility: partial_in_crop
          position: { area: lower_left }
          style:
            radius: rounded_corner_top
          note: "Person with curly dark hair, cropped at bottom of crop"
        - id: photo_tile_right
          kind: image
          role: collage_photo
          visibility: partial_in_crop
          position: { area: right }
          style:
            radius: rounded_corner_left
          note: "Seated man in suit against office windows, cropped at bottom of crop"
component_anatomy:
  actual_page_ui_components:
    - id: nav_signin_btn
      type: outline_pill_button
      note: "from header edge continuation"
    - id: nav_demo_btn
      type: solid_primary_pill_button
    - id: nav_search_icon
      type: icon_button
    - id: source_pill_chip
      type: decorative_feature_pill
      note: "hero collage pill, likely non-interactive label"
  embedded_or_showcase_only_ui:
    - id: candidate_card
      type: product_profile_card_mockup
      note: "Represents in-product candidate profile; status badge and meta are embedded_showcase_only"
    - id: status_badge
      type: showcase_status_tag
  absent_common_components:
    - primary_hero_headline_text_in_crop
    - hero_body_paragraph_in_crop
    - hero_cta_buttons_in_crop
    - note: "Crop only captures top band; main headline/CTAs sit below crop"
observed_values:
  colors:
    - { id: canvas_mint, role: section_background, value_approx: "#CDEBDD", path: tree.children[1].style.background_color, confidence: medium }
    - { id: card_white, role: card_surface, value_approx: "#FFFFFF", path: tree.children[1].children[0].style.child_surface }
    - { id: green_solid, role: badge_surface, value_approx: "#2E7D5B", path: candidate_card.status_badge }
    - { id: teal_chip, role: chip_surface, value_approx: "#7FBFA0", path: source_pill_chip }
    - { id: dark_green_text, role: chip_text, value_approx: "#13402C", path: source_pill_chip.chip_text }
    - { id: near_black_text, role: nav_text, value_approx: "#1A1A1A", path: top_nav_continuation }
    - { id: blue_primary, role: primary_button_fill, value_approx: "#3B6FE0", path: nav_demo_btn }
    - { id: muted_gray, role: card_meta_text, value_approx: "#7A7A7A", path: candidate_card }
    - { id: brand_green_logo, role: logo_text, value_approx: "#1F6B45", path: nav_logo_slot }
  gradients: []
  patterns: []
  background_systems:
    - id: hero_flat_mint_canvas
      type: single_flat_fill
      layers:
        - { layer: base, value: canvas_mint, coverage: full_width }
      path: tree.children[1]
      confidence: medium
      note: "Flat mint fill is the hero base; not a gradient"
  typography:
    - id: nav_link_type
      role: nav_link
      category: sans_serif
      size: small
      weight: regular
      case: none
      color: near_black_text
      path: top_nav_continuation.nav_links
    - id: card_title_type
      role: card_title
      category: sans_serif
      size: small
      weight: medium
      color: near_black_text
      path: candidate_card.candidate_name
    - id: card_meta_type
      role: card_meta
      category: sans_serif
      size: x_small
      weight: regular
      color: muted_gray
      path: candidate_card
    - id: chip_label_type
      role: feature_pill
      category: sans_serif
      size: small
      weight: medium
      color: dark_green_text
      path: source_pill_chip.chip_text
    - id: badge_label_type
      role: status_tag
      category: sans_serif
      size: x_small
      weight: medium
      color: card_white
      path: candidate_card.status_badge
  font_characteristics:
    - { id: ui_sans, note: "Clean geometric/humanist sans across nav and card UI; no serif visible in crop content" }
  spacing:
    - { id: nav_horizontal_gap, role: nav_item_gap, approx: comfortable, path: top_nav_continuation.nav_links }
    - { id: card_inner_padding, role: card_padding, approx: medium, path: candidate_card }
    - { id: chip_inner_padding, role: chip_padding, approx: compact_horizontal, path: source_pill_chip }
  radius:
    - { id: pill_radius, value_approx: full_pill, path: source_pill_chip }
    - { id: card_radius, value_approx: "~10px", path: candidate_card }
    - { id: badge_radius, value_approx: "~4px", path: candidate_card.status_badge }
    - { id: button_pill_radius, value_approx: full_pill, path: nav_demo_btn }
  sizes:
    - { id: card_width, approx: medium_compact, path: candidate_card }
    - { id: avatar_size, approx: small, path: candidate_card.candidate_avatar }
  opacity: []
  borders:
    - { id: signin_outline, style: thin_solid, color: near_black_or_gray, path: nav_signin_btn }
  shadows:
    - { id: card_soft_shadow, style: soft_diffuse_low, path: candidate_card }
  effects: []
  icons:
    - id: search_glyph
      icon_asset_class: single-color-icon
      style: thin_stroke
      color: near_black
      path: top_nav_continuation.nav_search_icon
    - id: chip_glyph
      icon_asset_class: single-color-icon
      style: simple_pictogram
      color: dark_green
      path: source_pill_chip.chip_icon
    - id: badge_leading_glyph
      icon_asset_class: single-color-icon
      style: sparkle_like_glyph
      color: white
      path: candidate_card.status_badge
    - id: card_meta_glyph
      icon_asset_class: single-color-icon
      style: small_pictogram
      color: muted_gray
      path: candidate_card.card_meta_row
    - id: brand_logo
      icon_asset_class: logo/wordmark
      footprint: small_horizontal_wordmark
      color: brand_green_logo
      approximatable_as: text_block
      path: nav_logo_slot
  imagery_categories:
    icons:
      - { id: ui_glyph_set, icon_asset_class: single-color-icon, density: low, simplicity: high, palette_relationship: "single tone matching local surface (green or gray)" }
      - { id: brand_wordmark, icon_asset_class: logo/wordmark, note: "green lowercase wordmark" }
    illustrations: []
    interfaces:
      - id: candidate_profile_card_ui
        framing: floating_cropped_card
        realism_level: flat_product_ui
        composition: "avatar + name/role + status badge + meta row"
        color_treatment: white_surface_with_green_accents
        placement: foreground_graphic
        detail_level: low_medium
        edge_behavior: contained_card
        note: "embedded_showcase_only product UI snippet"
    photography:
      - id: collage_portraits
        category: photography
        framing: tight_to_medium_portrait
        crop: "tiles cropped at bottom of section crop; partial subjects"
        perspective: eye_level
        realism_level: real_photo
        lighting: natural_soft
        material_texture: skin_fabric_glass
        color_treatment: natural_slightly_warm
        composition: "subjects placed at left and right edges of collage"
        placement: foreground_media
        edge_behavior: "photo content extends to tile rounded-corner edges; bottom edge cut by crop"
        density: medium
        detail_level: high
        subject_context_local: "candidate/people portraits and office worker; subject is slot context only"
  media:
    - { id: photo_tile_left, type: photo, path: tree.children[1].children[4] }
    - { id: photo_tile_right, type: photo, path: tree.children[1].children[5] }
    - { id: candidate_avatar, type: photo_thumbnail, path: candidate_card.candidate_avatar }
  creative_direction:
    - id: hero_collage_direction
      summary: "Flat mint canvas with floating real-photo portrait tiles, a clean white product-UI card, and connector lines tying UI affordances to feature pills"
      imagery_mix: "real photography + flat product UI mock + thin connector graphics"
      mood: approachable_modern_saas
      palette_relationship: "green/teal accents on white UI over pale mint field"
  implementation_assumptions:
    - { id: canvas_fill_assumption, target: hero_canvas, value: likely_dom_or_layout_element }
    - { id: connector_assumption, target: connector_line, value: likely_svg_or_canvas_graphic }
    - { id: photo_assumption, target: collage_portraits, value: likely_raster_image }
    - { id: card_assumption, target: candidate_card, value: likely_dom_or_layout_element }
  components:
    - { id: feature_pill_chip, type: rounded_pill_label_with_icon, host_surface: mint_canvas, child_surface: teal, text_color: dark_green, separation: fill_contrast }
    - { id: floating_profile_card, type: elevated_white_card, host_surface: mint_canvas, child_surface: white, separation: shadow_plus_radius }
    - { id: status_tag_badge, type: solid_green_pill_tag, host_surface: white_card, text_color: white, separation: fill_contrast }
consolidation_notes:
  likely_tokens:
    colors:
      - { alias_hint: surface_mint_hero, from: canvas_mint }
      - { alias_hint: accent_green_solid, from: green_solid }
      - { alias_hint: accent_teal_soft, from: teal_chip }
      - { alias_hint: text_on_light, from: near_black_text }
      - { alias_hint: primary_action_blue, from: blue_primary }
    gradients: []
    patterns: []
    background_systems:
      - { alias_hint: hero_flat_mint, from: hero_flat_mint_canvas }
    typography:
      - { alias_hint: ui_card_title_sm, from: card_title_type }
      - { alias_hint: ui_meta_xs, from: card_meta_type }
      - { alias_hint: pill_label_sm, from: chip_label_type }
    spacing:
      - { alias_hint: card_padding_md, from: card_inner_padding }
    radius:
      - { alias_hint: radius_pill, from: pill_radius }
      - { alias_hint: radius_card_md, from: card_radius }
    shadow:
      - { alias_hint: shadow_card_soft, from: card_soft_shadow }
    dividers: []
  likely_components:
    - { alias_hint: feature_pill, from: feature_pill_chip }
    - { alias_hint: floating_ui_card, from: floating_profile_card }
    - { alias_hint: status_badge, from: status_tag_badge }
  likely_section_patterns:
    - { alias_hint: layered_collage_hero, note: "central messaging with peripheral floating media and product-UI snippets" }
  surface_specific_recipes:
    - { alias_hint: pill_on_mint, note: "teal pill + dark green icon/text on mint canvas" }
    - { alias_hint: card_on_mint, note: "white elevated card with green accents over mint field" }
  spacing_and_rhythm_mechanics:
    - "Floating elements positioned freely rather than on a strict grid; connector lines imply relationships"
  link_action_mechanics:
    - "Header has outline-pill secondary and solid-blue primary actions; hero pill chip appears decorative/labeling"
  distinct_visual_motifs:
    - "Thin curved connector lines linking UI cards to feature labels"
    - "Mixed real-photo portrait tiles with rounded corners"
  imagery_direction_candidates:
    icons:
      - "single-color thin UI glyphs and a green lowercase wordmark"
    illustrations: []
    interfaces:
      - "flat white product-UI cards with green accent badges, low-to-medium detail"
    photography:
      - "natural-lit candid portraits/office people, slightly warm, high detail, cropped into rounded tiles"
  do_not_generalize:
    - "Nav/header content belongs to previous section; included only as top-edge continuation"
    - "Candidate card UI is embedded_showcase_only and should not become real page UI"
  uncertainties:
    - "Exact hero background hue approximate"
    - "Crop captures only top band of hero; main headline, body copy, and CTA buttons fall below this crop"
    - "Whether source pill chip is interactive is unclear (treated as decorative label)"

## Section 4: Acquisition Notice Bar

- **Approximate boundaries:** y=390 to y=445
- **Generic role:** see grounded section observations below
- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.

schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: 4
  total_sections: 9
  detected_label: "Acquisition notice bar"
  previous_section_label: "Hero section"
  next_section_label: "Three feature cards"
  bounds:
    original_y_start: 393
    original_y_end: 437
    crop_y_start: 393
    crop_y_end: 437
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: thin_horizontal_band_section
  role: generic_full_width_band
  confidence: low
tree:
  id: root
  kind: section
  role: generic_full_width_band
  visibility: visible
  size:
    width: full_bleed
    height: very_short_band
    note: "thin horizontal strip, height roughly 40-45px at crop scale"
  layout:
    type: horizontal_band
    arrangement: "single full-width mint surface with photographic fragments bleeding in at left and right edges; large empty center"
    content_alignment: edges_only
  position:
    in_page: "below hero upper area, above feature cards per sequence metadata"
  style:
    background_color:
      value: pale_mint_green
      note: "light desaturated teal/mint fills the full-width band; reads as section/hero canvas color"
      confidence: medium
  layers:
    - id: base_canvas_layer
      role: section_background_fill
      style:
        fill: pale_mint_green
        coverage: full_width
      implementation_assumption: likely_dom_or_layout_element
    - id: edge_photo_fragments_layer
      role: foreground_photo_bleed
      note: "photographic content intrudes only at far left and far right crop edges; not a full media well"
      implementation_assumption: likely_raster_image
  children:
    - id: left_photo_fragment
      kind: image_fragment
      role: foreground_media
      visibility: visible
      size:
        width: small_edge_sliver
        height: full_band_height
      position:
        anchor: left_edge
      style:
        note: "fragment of a person with dark curly hair / head silhouette against light surroundings; appears to be top portion of a portrait bleeding up from below or down from above"
      implementation_assumption: likely_raster_image
    - id: right_photo_fragment
      kind: image_fragment
      role: foreground_media
      visibility: visible
      size:
        width: small_edge_sliver
        height: full_band_height
      position:
        anchor: right_edge
      style:
        note: "darker photographic fragment showing dark clothing and what appears to be a hand/arm; muted tones"
      implementation_assumption: likely_raster_image
    - id: center_empty_zone
      kind: spacer
      role: empty_canvas_region
      visibility: visible
      size:
        width: majority_of_band
      style:
        fill: pale_mint_green
      note: "no text or controls visibly resolved in this crop; metadata label suggests a notice bar with text+link but it is not visible in this slice"
      implementation_assumption: likely_dom_or_layout_element
component_anatomy:
  actual_page_ui_components: []
  embedded_or_showcase_only_ui: []
  absent_common_components:
    - note: "detected_label 'Acquisition notice bar' implies a one-line text notice plus inline/under link, but no legible text or link is recoverable in this crop"
observed_values:
  colors:
    - id: color_band_mint
      value: pale_mint_green
      approx_hex: "#cfe9df"
      path: tree.style.background_color
      confidence: medium
    - id: color_left_fragment_dark
      value: dark_brown_black
      approx_hex: "#23201d"
      path: tree.children[0]
      note: "dark hair tones"
      confidence: low
    - id: color_right_fragment_muted
      value: muted_dark_neutral
      approx_hex: "#3a3833"
      path: tree.children[1]
      confidence: low
  gradients: []
  patterns: []
  background_systems:
    - id: section_canvas_system
      type: flat_fill_with_edge_media
      layers:
        - flat pale mint fill (full width)
        - foreground photo fragments at left/right edges
      path: tree.layers
      confidence: medium
  typography: []
  font_characteristics: []
  spacing:
    - id: band_height
      value: very_short
      note: "thin horizontal strip"
      path: tree.size.height
  radius: []
  sizes:
    - id: edge_fragment_width
      value: small_sliver_each_side
      path: tree.children
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
      - id: edge_portrait_fragments
        slot_context: "human portrait fragments bleeding in from page hero imagery at left and right edges"
        framing: extreme_crop_edge_only
        crop: "only sliver of subject visible; head/hair at left, torso/hand at right"
        perspective: eye_level
        realism_level: photographic_real
        lighting: soft_natural
        material_texture: skin_hair_fabric
        color_treatment: natural_slightly_muted
        composition: edge_bleed
        placement_relationship: foreground_media_bleeding_into_mint_canvas
        edge_behavior: reaches_left_and_right_crop_edges
        density: sparse
        simplicity: low_visible_detail_due_to_crop
        detail_level: low_in_this_slice
        confidence: low
  media:
    - id: left_photo_fragment_media
      type: raster_photo_fragment
      path: tree.children[0]
      confidence: low
    - id: right_photo_fragment_media
      type: raster_photo_fragment
      path: tree.children[1]
      confidence: low
  creative_direction:
    - id: band_creative_direction
      summary: "pale mint full-width band acting as breathing space between photographic content zones; photographs touch the edges while the center is open"
      confidence: low
  implementation_assumptions:
    - id: ia_root
      target: tree
      assumption: likely_dom_or_layout_element
    - id: ia_photos
      target: "tree.children[0..1]"
      assumption: likely_raster_image
  components: []
consolidation_notes:
  likely_tokens:
    colors:
      - "pale mint section/hero canvas fill"
    gradients: []
    patterns: []
    background_systems:
      - "flat mint band with edge-bleeding photo media"
    typography: []
    spacing:
      - "thin band height"
    radius: []
    shadow: []
    dividers: []
  likely_components: []
  likely_section_patterns:
    - "full-width flat-color band used as a divider/notice strip or as vertical whitespace within a media-rich hero region"
  surface_specific_recipes:
    - "photographic fragments may sit as foreground_media on a flat mint canvas rather than inside a media well"
  spacing_and_rhythm_mechanics:
    - "narrow vertical strip; center reserved as open canvas"
  link_action_mechanics: []
  distinct_visual_motifs:
    - "edge-bleed portrait fragments over mint"
  imagery_direction_candidates:
    icons: []
    illustrations: []
    interfaces: []
    photography:
      - "natural soft-lit human portraits, lightly muted, cropped to bleed off section edges"
  do_not_generalize:
    - "do not treat the mint band as a dark notice bar; visible crop is light mint, which conflicts with the detected_label"
  uncertainties:
    - "STRONG MISMATCH: detected_label 'Acquisition notice bar' describes a dark green strip with white text + link in the full-page overview, but the provided crop (Image 1) shows a light pale-mint band with photographic edge fragments and no legible text. The crop appears to correspond to upper hero/canvas content rather than the dark acquisition strip."
    - "No text, button, eyebrow, or link is recoverable in this crop."
    - "Subjects of edge photo fragments are inferred from partial detail and are low confidence."
    - "Top and bottom transition behavior cannot be reliably determined from this thin slice; appears as same mint surface continuation with photo bleed."

## Section 5: Three Product Feature Cards

- **Approximate boundaries:** y=445 to y=2250
- **Generic role:** see grounded section observations below
- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.

schema_version: raw_section_yaml.v1
type: raw_section_capture
source:
  type: screenshot
  section_scope: single_website_section
  section_index: 5
  total_sections: 9
  detected_label: "Three feature cards"
  previous_section_label: "Acquisition notice bar"
  next_section_label: "Customer logos"
  bounds:
    original_y_start: 437
    original_y_end: 2150
    crop_y_start: 437
    crop_y_end: 2150
  fidelity: visually_approximated_from_screenshot
  literal_text_included: false
section:
  id: feature_cards_triple_section
  role: feature_grid_section
  confidence: high
tree:
  id: root
  kind: section
  role: feature_grid_section
  visibility: visible
  size:
    width: full_bleed
    height: tall
  layout:
    type: vertical_stack
    note: "Crop over-includes tail of prior hero + dark acquisition bar above the actual 3-card grid; primary content is a 3-column card row on white canvas"
    content_max_width: centered_constrained
  position:
    in_page: middle
  style:
    background_color:
      role: section_canvas
      value: "white / near-white"
      confidence: high
  layers:
    - id: section_bg
      role: base_canvas
      implementation_assumption: likely_dom_or_layout_element
      style:
        fill: "white"
  children:
    - id: upper_continuation_band
      kind: group
      role: previous_section_bleed
      visibility: visible
      note: "Mint hero remainder + dark green acquisition notice bar visible at top of crop; belongs to sections 3-4, included only as edge continuity"
      layout:
        type: stacked
      children:
        - id: hero_mint_panel_tail
          kind: panel
          role: hero_surface_tail
          style:
            background_color:
              value: "pale mint green"
              confidence: high
          children:
            - id: hero_headline
              kind: text
              role: display_heading
              style:
                font_category: serif
                style_description: "large serif display with italic emphasis word"
                color: "deep green"
                alignment: center
            - id: hero_subcopy
              kind: text
              role: body_text
              style:
                font_category: serif
                color: "deep green"
                alignment: center
            - id: hero_primary_cta
              kind: button
              role: primary_button
              style:
                fill: "deep green"
                text_color: "white"
                shape: pill
            - id: hero_secondary_cta
              kind: link
              role: text_link
              style:
                text_color: "deep green"
                decoration: underline
            - id: hero_floating_chip_1
              kind: badge
              role: floating_label_chip
              style:
                fill: "muted green"
                text_color: "deep green"
                shape: rounded
                icon: leading_small_icon
            - id: hero_floating_chip_2
              kind: badge
              role: floating_label_chip
              style:
                fill: "muted green"
                text_color: "deep green"
            - id: hero_floating_card_candidates
              kind: card
              role: floating_ui_card
              implementation_assumption: visual_sublayer_only
              note: "white mini card with avatar row + green pill, embedded showcase UI"
            - id: hero_floating_card_report
              kind: card
              role: floating_ui_card
              implementation_assumption: visual_sublayer_only
              note: "white report builder mockup with bar chart"
            - id: hero_photo_topleft
              kind: image
              role: photo_portrait
              implementation_assumption: likely_raster_image
            - id: hero_photo_bottomright
              kind: image
              role: photo_group
              implementation_assumption: likely_raster_image
        - id: acquisition_notice_bar
          kind: panel
          role: notice_band
          style:
            background_color:
              value: "very dark green"
              confidence: high
          children:
            - id: notice_text
              kind: text
              role: body_text
              style:
                color: "off-white"
                font_category: sans-serif
                weight: "mixed bold + regular"
            - id: notice_link
              kind: link
              role: text_link
              style:
                color: "white"
                decoration: underline
    - id: feature_cards_row
      kind: group
      role: card_grid
      visibility: visible
      note: "PRIMARY content of target section"
      size:
        width: constrained
      layout:
        type: horizontal_grid
        columns: 3
        gap: medium
        alignment: top
        item_widths: equal
      position:
        in_section: lower
      style:
        background_color:
          value: "transparent over white canvas"
      items:
        - id: feature_card
          kind: card
          role: feature_card
          repeat_count: 3
          note: "Three peer cards; card 2 media well differs (dark green showcase) vs cards 1 and 3 (photo)"
          layout:
            type: vertical_stack
            order: [media_well, heading, body, cta]
            gap: small_to_medium
          style:
            background_color:
              value: "transparent (no card surface fill; image + text stacked on white)"
              confidence: medium
            border: none_observed
            shadow: none_observed
          children:
            - id: card_media_well
              kind: image
              role: feature_media
              implementation_assumption: likely_raster_image
              style:
                shape: rounded_rectangle
                radius: medium
                aspect: landscape
              variants:
                - id: media_photo_variant
                  note: "cards 1 & 3: warm-lit indoor people photography"
                  implementation_assumption: likely_raster_image
                - id: media_dark_showcase_variant
                  note: "card 2: dark green panel with overlapping circular profile thumbnails + flagged status pill"
                  implementation_assumption: likely_raster_image
              children:
                - id: media_overlay_pill
                  kind: badge
                  role: overlay_label_chip
                  note: "white pill with leading icon overlaid on lower area of media (e.g. action/feature label); card 2 overlay is a status alert pill with red dot"
                  style:
                    fill: "white"
                    text_color: "deep green / dark"
                    shape: pill
                    icon: leading_small_icon
                  implementation_assumption: visual_sublayer_only
            - id: card_heading
              kind: text
              role: card_title
              style:
                font_category: serif
                size: large
                weight: regular
                color: "deep green / near-black green"
                alignment: left
            - id: card_body
              kind: text
              role: body_text
              style:
                font_category: sans-serif
                size: small_to_medium
                color: "dark gray-green"
                line_height: comfortable
                alignment: left
            - id: card_cta
              kind: button
              role: secondary_button
              note: "outlined pill 'Learn more'; absent or styled same across cards (card 2 has it too)"
              style:
                fill: "transparent"
                text_color: "deep green / dark"
                border: "thin solid muted border"
                shape: pill
component_anatomy:
  actual_page_ui_components:
    - id: feature_card_component
      role: feature_card
      count: 3
      parts: [media_well, overlay_pill, serif_title, body_paragraph, outlined_cta]
    - id: outlined_pill_button
      role: secondary_button
      host_surface: white_canvas
      style: "transparent fill, thin border, dark text, pill radius"
    - id: overlay_label_chip
      role: media_overlay_badge
      host_surface: image_media_well
      style: "white pill, leading icon, dark text"
    - id: primary_button_hero_tail
      role: primary_button
      note: "from hero bleed, deep green solid pill"
    - id: text_link
      role: inline_link
      note: "underlined, hero subordinate CTA and notice link"
  embedded_or_showcase_only_ui:
    - id: card2_profile_thumbnails
      note: "overlapping circular avatars + named card + risk status pill inside dark media well"
      classification: embedded_showcase_only
    - id: hero_report_mockup
      note: "report builder card with dropdowns and bar chart"
      classification: embedded_showcase_only
    - id: hero_candidate_card
      note: "view-all-candidates mini card with avatar row + summarize pill"
      classification: embedded_showcase_only
  absent_common_components:
    - tabs
    - accordion
    - pagination
    - form_inputs
observed_values:
  colors:
    - id: canvas_white
      value: "#FFFFFF approx"
      role: section_background
      path: tree.style.background_color
      confidence: high
    - id: hero_mint
      value: "pale mint green ~#BFE9D8"
      role: prior_section_panel
      path: tree.children.upper_continuation_band.children.hero_mint_panel_tail
      confidence: high
    - id: dark_green_strong
      value: "very dark green ~#16352B"
      role: notice_band_and_card2_media
      path: tree.children.upper_continuation_band.children.acquisition_notice_bar
      confidence: high
    - id: deep_green_text
      value: "deep green ~#1F3D2E"
      role: heading_and_primary_button
      path: tree.children.feature_cards_row.items.children.card_heading
      confidence: high
    - id: body_text_gray_green
      value: "muted dark gray-green ~#3A4A41"
      role: body_copy
      path: tree.children.feature_cards_row.items.children.card_body
      confidence: medium
    - id: chip_muted_green
      value: "muted desaturated green ~#7FB79C"
      role: hero_floating_chip_fill
      path: tree.children.upper_continuation_band.children.hero_mint_panel_tail.children.hero_floating_chip_1
      confidence: medium
    - id: alert_red_dot
      value: "red accent"
      role: status_indicator
      path: tree.children.feature_cards_row.items.children.card_media_well.children.media_overlay_pill
      confidence: medium
  gradients: []
  patterns: []
  background_systems:
    - id: section_canvas_system
      type: flat_fill
      layers:
        - role: base
          value: "white"
      path: tree.layers.section_bg
      confidence: high
    - id: card2_media_dark_system
      type: dark_panel_with_subtle_texture
      note: "dark green field with faint leaf/line motif behind profile thumbnails"
      path: tree.children.feature_cards_row.items.children.card_media_well.variants.media_dark_showcase_variant
      confidence: low
  typography:
    - id: card_title_type
      role: card_title
      font_category: serif
      style_description: "transitional serif, regular weight, generous size"
      size: large
      weight: regular
      case: none
      alignment: left
      color: deep_green_text
      path: tree.children.feature_cards_row.items.children.card_heading
      confidence: high
    - id: card_body_type
      role: body_text
      font_category: sans-serif
      style_description: "neutral grotesque, regular"
      size: small_to_medium
      line_height: comfortable
      alignment: left
      color: body_text_gray_green
      path: tree.children.feature_cards_row.items.children.card_body
      confidence: high
    - id: cta_label_type
      role: button_label
      font_category: sans-serif
      size: small
      weight: medium
      color: deep_green_text
      path: tree.children.feature_cards_row.items.children.card_cta
      confidence: medium
    - id: overlay_chip_type
      role: chip_label
      font_category: sans-serif
      size: small
      weight: medium
      path: tree.children.feature_cards_row.items.children.card_media_well.children.media_overlay_pill
      confidence: medium
    - id: hero_display_type
      role: display_heading
      font_category: serif
      style_description: "large serif with italic emphasis word"
      size: very_large
      alignment: center
      color: deep_green_text
      path: tree.children.upper_continuation_band.children.hero_mint_panel_tail.children.hero_headline
      confidence: high
  font_characteristics:
    - serif_for_headings_display
    - sans_serif_for_body_and_ui
    - italic_emphasis_within_serif_display
  spacing:
    - id: card_grid_gap
      role: column_gap
      value: medium
      path: tree.children.feature_cards_row.layout.gap
      confidence: medium
    - id: card_internal_stack_gap
      role: vertical_gap
      value: small_to_medium
      path: tree.children.feature_cards_row.items.layout.gap
      confidence: medium
    - id: section_top_padding
      role: gap_above_card_row
      value: large
      note: "generous whitespace between notice band bottom and card row top"
      confidence: medium
  radius:
    - id: media_well_radius
      value: medium
      path: tree.children.feature_cards_row.items.children.card_media_well
      confidence: high
    - id: pill_full_radius
      value: full
      note: "buttons and overlay chips fully rounded"
      confidence: high
  sizes:
    - id: card_column_width
      value: equal_thirds_constrained
      path: tree.children.feature_cards_row.layout
      confidence: high
    - id: media_well_aspect
      value: landscape_~4:3
      confidence: medium
  opacity: []
  borders:
    - id: cta_outline
      value: "thin solid muted gray/green border"
      path: tree.children.feature_cards_row.items.children.card_cta.style.border
      confidence: high
  shadows:
    - id: floating_ui_card_shadow
      value: "soft subtle drop shadow on hero mini-cards"
      path: tree.children.upper_continuation_band.children.hero_mint_panel_tail.children.hero_floating_card_candidates
      confidence: low
  effects:
    - id: overlapping_avatar_stack
      note: "card 2 overlapping circular profile thumbnails layered with depth"
      path: tree.children.feature_cards_row.items.children.card_media_well.variants.media_dark_showcase_variant
      confidence: medium
  icons:
    - id: overlay_chip_icon
      role: leading_chip_icon
      icon_asset_class: single-color-icon
      style: "small simple glyph (sparkle/bell/etc), single color, light weight"
      container: inside_white_pill
      path: tree.children.feature_cards_row.items.children.card_media_well.children.media_overlay_pill
      confidence: medium
    - id: alert_status_dot
      role: status_icon
      icon_asset_class: single-color-icon
      style: "small red circular alert mark"
      confidence: medium
    - id: hero_chip_icons
      role: leading_chip_icon
      icon_asset_class: single-color-icon
      style: "tiny line/solid pictograms in green"
      confidence: medium
  imagery_categories:
    icons:
      - id: ui_support_glyphs
        icon_asset_class: single-color-icon
        usage: overlay_chip_and_status
        rendering: "simple single-color, minimal detail"
        palette_relationship: "dark or red on white pill"
        confidence: medium
    illustrations: []
    interfaces:
      - id: card2_candidate_panel_showcase
        category: interfaces
        framing: "dark panel with overlapping rounded profile cards + name label + risk pill"
        realism_level: stylized_ui
        placement: embedded_showcase
        detail_level: medium
        note: "embedded_showcase_only"
        confidence: medium
      - id: hero_report_and_candidate_cards
        category: interfaces
        framing: "white mini cards with dropdowns, bar chart, avatar row"
        placement: embedded_showcase
        note: "from hero bleed, embedded_showcase_only"
        confidence: medium
    photography:
      - id: feature_card_photo
        category: photography
        framing: "candid workplace/people scenes, medium shots"
        crop: "fills rounded media well to edges"
        perspective: eye_level
        realism_level: photographic
        lighting: "warm natural interior light"
        material_texture: "skin, fabric, indoor environments"
        color_treatment: "warm neutral, soft"
        composition: "subject-centered, people interacting"
        placement_relationship: foreground_media
        edge_behavior: "photo reaches all four edges of rounded media well; well is rounded frame not photo content"
        density: medium
        simplicity: medium
        detail_level: high
        slot_context: "card 1: people in conversation; card 3: single portrait by wall with plant"
        confidence: high
      - id: hero_bleed_photos
        category: photography
        framing: "portrait + group seated scene"
        placement: foreground_media
        note: "from hero bleed above target"
        confidence: medium
  media:
    - id: card_media_wells
      type: image_block
      count: 3
      note: "2 photographic + 1 dark UI showcase well"
      path: tree.children.feature_cards_row.items.children.card_media_well
      confidence: high
  creative_direction:
    - id: feature_card_photography_direction
      summary: "Warm, candid, human-centered workplace photography in rounded media wells; people-focused, soft natural lighting, realistic, edge-to-edge within frame"
      reusable_as: photography_style
      confidence: high
    - id: interface_showcase_direction
      summary: "Dark green UI panel with overlapping rounded profile cards and small status pills; clean, minimal, product-screenshot feel"
      reusable_as: interface_style
      confidence: medium
    - id: overlay_chip_direction
      summary: "White pill labels with small single-color leading icon floated over media corners"
      reusable_as: badge_style
      confidence: medium
  implementation_assumptions:
    - target: feature card media wells
      assumption: likely_raster_image
    - target: overlay pills + embedded thumbnails
      assumption: visual_sublayer_only
    - target: section background
      assumption: likely_dom_or_layout_element
    - target: card2 dark panel
      assumption: likely_raster_image
  components:
    - id: feature_card
      summary: "media well + overlay chip + serif title + body + outlined pill CTA"
      count: 3
      confidence: high
    - id: outlined_secondary_button
      summary: "transparent pill with thin border, dark label"
      confidence: high
consolidation_notes:
  likely_tokens:
    colors:
      - "white canvas surface"
      - "deep green heading/primary"
      - "very dark green panel/notice"
      - "muted gray-green body text"
      - "pale mint hero panel"
    gradients: []
    patterns: []
    background_systems:
      - "flat white section canvas"
      - "dark green media panel with faint texture"
    typography:
      - "serif display/title scale"
      - "sans-serif body + ui scale"
    spacing:
      - "3-column equal grid with medium gap"
      - "large section top padding"
    radius:
      - "medium media-well radius"
      - "full pill radius for buttons/chips"
    shadow:
      - "soft subtle shadow on floating mini-cards"
    dividers: []
  likely_components:
    - "feature_card (media + serif title + body + outlined CTA)"
    - "media_overlay_pill"
    - "outlined_secondary_button"
  likely_section_patterns:
    - "three-up feature card grid on light canvas"
  surface_specific_recipes:
    - "outlined_secondary_button_on_white_surface"
    - "white_overlay_chip_on_image_media"
    - "embedded_ui_showcase_on_dark_panel"
  spacing_and_rhythm_mechanics:
    - "equal-width columns, consistent internal vertical rhythm per card"
  link_action_mechanics:
    - "each card terminates in outlined pill CTA"
    - "media overlay chips are non-actionable labels (likely)"
  distinct_visual_motifs:
    - "serif titles paired with photographic media"
    - "white pill chips floated on imagery"
    - "one dark UI-showcase card breaking photographic pattern"
  imagery_direction_candidates:
    icons:
      - "single-color support glyphs in white pills"
    illustrations: []
    interfaces:
      - "dark-panel profile/candidate UI showcase"
    photography:
      - "warm candid human workplace photography, edge-to-edge in rounded wells"
  do_not_generalize:
    - "card 2 dark media well is local variant, not all cards"
    - "upper mint hero + dark notice belong to prior sections (crop bleed)"
    - "embedded UI thumbnails are showcase only, not real page UI"
  uncertainties:
    - "whether cards have an actual surface fill/border vs bare stack on white (appears bare)"
    - "exact gap and padding values"
    - "whether all three cards include a CTA button (card 2 appears to)"
    - "exact section top/bottom boundaries given crop over-inclusion"

## Section 6: Customer Logos

- **Approximate boundaries:** y=2250 to y=2960
- **Generic role:** see grounded section observations below
- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.

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

## Section 7: Best Teams Feature Section

- **Approximate boundaries:** y=2960 to y=4150
- **Generic role:** see grounded section observations below
- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.

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

## Section 8: CTA Banner

- **Approximate boundaries:** y=4150 to y=4985
- **Generic role:** see grounded section observations below
- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.

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

## Section 9: Footer

- **Approximate boundaries:** y=4985 to y=6171
- **Generic role:** see grounded section observations below
- **Evidence notes:** generated from cached per-section grounding because the final merge response was incomplete.

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

## Cross-section Notes

- The model merge step did not return a complete structural document after retries, so this fallback preserves the per-section grounding without additional synthesis.
- Treat repeated patterns, surface relationships, and typography hierarchy as grounded in the individual section notes above.

## Ambiguities

- Cross-section synthesis may be less normalized than usual because the fallback document avoided inventing details after merge failure.
