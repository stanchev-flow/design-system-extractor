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
