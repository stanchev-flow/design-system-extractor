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
