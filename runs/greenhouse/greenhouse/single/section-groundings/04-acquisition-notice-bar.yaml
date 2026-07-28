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
