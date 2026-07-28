schema_version: design_system_yaml.v1
type: design_system
metadata:
  name: editorial_evergreen_system
  description: "A calm, premium editorial aesthetic pairing high-contrast serif headings with a neutral humanist sans on deep-green inverse surfaces, mint and white canvases, and warm human-centered photography."
  source: normalized_site_ast
  generated_from:
    - normalized_site_ast
    - raw_section_yaml
    - surface_component_contract
    - source_style_ledger
    - source_css
  confidence: high

tokens:
  color:
    surface:
      primary: "#FFFFFF"
      secondary: "#CDEBDD"
      inverse: "#15372C"
      inverseRun: "#163328"
      inverseRunShift: "#1D4034"
      inverseFooter: "#14352B"
    text:
      primary: "#15372C"
      muted: "#4A5A52"
      onInverse: "#F3F1EA"
      onInverseMuted: "#5F9C84"
      onAccent: "#FFFFFF"
    border:
      onLight: "#D8E0DB"
      onInverse: "rgba(243,241,234,0.4)"
      accent: "#4CB398"
    accent:
      primary: "#4CB398"
      action: "#2F6FE0"
      deep: "#15372C"
    graphic:
      decorativeMotif: "#1D4034"
      iconOnInverse: "#5F9C84"
  typography:
    note: "Serif used only for page/section/content headings; Inter sans for body, controls, links, labels."
  spacing:
    scale: ["4px", "8px", "12px", "16px", "24px", "32px", "48px", "64px", "96px"]
    sectionPaddingTall: "96px"
    sectionPaddingMedium: "64px"
    gridGutter: "32px"
    textStackGap: "16px"
    cardInnerGap: "16px"
  radius:
    pill: "999px"
    card: "10px"
    media: "12px"
    badge: "4px"
    input: "8px"
  shadow:
    cardSoft: "0 8px 24px rgba(0,0,0,0.08)"
    widgetElevated: "0 12px 32px rgba(0,0,0,0.16)"
  divider:
    hairlineOnLight: "1px solid #D8E0DB"
  motion:
    note: "Restrained, system-native transitions; subtle hover color/opacity shifts on links and buttons; optional gentle reveal on photography and cards."

surfaces:
  page_canvas:
    value: "#FFFFFF"
    role: page_canvas
    text:
      default: "#15372C"
      muted: "#4A5A52"
      accent: "#4CB398"
    border: "#D8E0DB"
    shadow: "none"
    gradient: "none"
    usage: ["feature card grids", "social-proof / logo blocks", "content sections"]
    confidence: high
  mint_canvas:
    value: "#CDEBDD"
    role: section_run
    text:
      default: "#15372C"
      muted: "#4A5A52"
      accent: "#15372C"
    border: "none"
    shadow: "none"
    gradient: "none"
    usage: ["opening bookend / introductory banner canvas with floating media", "soft full-width breathing band with edge-bleeding photography"]
    confidence: medium
  inverse_strip:
    value: "#15372C"
    role: inverse_run
    text:
      default: "#F3F1EA"
      muted: "rgba(243,241,234,0.7)"
      accent: "#FFFFFF"
    border: "none"
    shadow: "none"
    gradient: "none"
    usage: ["thin promo/announcement strips", "standalone notice bands with inline link"]
    confidence: high
  inverse_action_run:
    value: "#163328"
    role: inverse_run
    text:
      default: "#F3F1EA"
      muted: "#5F9C84"
      accent: "#FFFFFF"
    border: "none"
    shadow: "none"
    gradient: "subtle tonal shift to #1D4034 within the run; not a hard gradient"
    usage: ["closing bookend call-to-action band with decorative brand motif"]
    confidence: high
  inverse_footer:
    value: "#14352B"
    role: inverse_run
    text:
      default: "#F3F1EA"
      muted: "#5F9C84"
      accent: "#F3F1EA"
    border: "rgba(243,241,234,0.4)"
    shadow: "none"
    gradient: "none"
    usage: ["site-wide closing footer with link columns, newsletter, legal"]
    confidence: high
  card_surface:
    value: "#FFFFFF"
    role: card
    text:
      default: "#15372C"
      muted: "#4A5A52"
      accent: "#4CB398"
    border: "none"
    shadow: "0 8px 24px rgba(0,0,0,0.08)"
    gradient: "none"
    usage: ["elevated white mini-cards over mint or light canvases", "floating chat/help widget"]
    confidence: medium

typography:
  display_heading:
    fontFamily: "Editorial serif (source family unconfirmed; pair a high-contrast transitional/modern serif)"
    fontFamilyCategory: serif
    visualCharacteristics:
      - "high stroke contrast between thick and thin strokes"
      - "moderate x-height"
      - "bracketed sharp serifs, vertical axis stress"
      - "editorial, refined, slightly classical feel"
      - "supports an italic emphasis variant used on a single word"
      - "generous size, tight line-height at large scale"
    fontSize: "clamp(40px, 6vw, 72px)"
    fontWeight: "400"
    lineHeight: "1.05"
    letterSpacing: "-0.01em"
    textTransform: preserve_authored_case
    role: page_heading / oversized marquee heading
    confidence: medium
  h1:
    fontFamily: "Editorial serif (as display_heading)"
    fontFamilyCategory: serif
    visualCharacteristics:
      - "high stroke contrast"
      - "vertical stress, bracketed serifs"
      - "italic emphasis word supported"
      - "tight leading at large size"
    fontSize: "clamp(36px, 5vw, 60px)"
    fontWeight: "400"
    lineHeight: "1.1"
    letterSpacing: "-0.01em"
    textTransform: preserve_authored_case
    role: page_heading
    confidence: medium
  h2:
    fontFamily: "Editorial serif (as display_heading)"
    fontFamilyCategory: serif
    visualCharacteristics:
      - "high-contrast serif, editorial tone"
      - "moderate x-height, vertical stress"
      - "comfortable leading"
    fontSize: "clamp(28px, 3.5vw, 44px)"
    fontWeight: "400"
    lineHeight: "1.15"
    letterSpacing: "-0.005em"
    textTransform: preserve_authored_case
    role: section_heading
    confidence: high
  h3:
    fontFamily: "Editorial serif (as display_heading)"
    fontFamilyCategory: serif
    visualCharacteristics:
      - "serif, slightly lower contrast at smaller size"
      - "often set as a two-line subheading"
      - "dark-green color on light surfaces"
    fontSize: "22px"
    fontWeight: "500"
    lineHeight: "1.25"
    letterSpacing: "normal"
    textTransform: preserve_authored_case
    role: content_heading / card_title
    confidence: high
  body:
    fontFamily: "'Inter'"
    fontFamilyCategory: sans_serif
    visualCharacteristics:
      - "humanist-grotesque sans"
      - "large x-height, low stroke contrast"
      - "open apertures, neutral wide proportions"
      - "even rhythm, highly legible at small sizes"
    fontSize: "15px"
    fontWeight: "400"
    lineHeight: "1.6"
    letterSpacing: "normal"
    textTransform: none
    role: body / paragraph
    confidence: high
  body_muted:
    fontFamily: "'Inter'"
    fontFamilyCategory: sans_serif
    visualCharacteristics:
      - "same Inter sans as body"
      - "rendered in muted gray-green for supporting copy"
      - "low emphasis"
    fontSize: "14px"
    fontWeight: "400"
    lineHeight: "1.6"
    letterSpacing: "normal"
    textTransform: none
    role: supporting / metadata body
    confidence: medium
  label_eyebrow:
    fontFamily: "'Inter'"
    fontFamilyCategory: sans_serif
    visualCharacteristics:
      - "small Inter sans"
      - "medium weight, group/column heading role"
      - "muted green on inverse surfaces"
    fontSize: "14px"
    fontWeight: "500"
    lineHeight: "1.4"
    letterSpacing: "0.02em"
    textTransform: preserve_authored_case
    role: label_metadata / column eyebrow
    confidence: medium
  control_text:
    fontFamily: "'Inter'"
    fontFamilyCategory: sans_serif
    visualCharacteristics:
      - "Inter sans, medium weight for emphasis"
      - "used in buttons, nav, footer links, inline links"
      - "underline applied to text links"
    fontSize: "15px"
    fontWeight: "500"
    lineHeight: "1.4"
    letterSpacing: "normal"
    textTransform: none
    role: control_text / link
    confidence: high

components:
  inline_text_link:
    kind: link
    actualPageUI: true
    confidence: high
    anatomy: ["text label", "underline"]
    base:
      typography: "{typography.control_text}"
      padding: "0"
      radius: "0"
      display: inline
      widthBehavior: content_hugging
      cssSizingHint: "display:inline; white-space:nowrap"
      textTransform: none
    variants:
      on_inverse:
        surface: inverse_strip
        textColor: "#FFFFFF"
        contrastSource: fill_contrast
      on_light:
        surface: page_canvas
        textColor: "#15372C"
        contrastSource: none
    doNotUseFor: ["primary CTAs that need a filled pill"]
  primary_button:
    kind: button
    actualPageUI: true
    confidence: high
    anatomy: ["text label", "pill container"]
    base:
      typography: "{typography.control_text}"
      padding: "12px 24px"
      radius: "999px"
      display: inline-flex
      widthBehavior: content_hugging
      cssSizingHint: "display:inline-flex; width:max-content; max-width:100%; white-space:nowrap; flex:0 0 auto"
      textTransform: none
    variants:
      solid_accent_on_light:
        surface: page_canvas
        backgroundColor: "#4CB398"
        textColor: "#FFFFFF"
        contrastSource: fill_contrast
      solid_deep_on_mint:
        surface: mint_canvas
        backgroundColor: "#15372C"
        textColor: "#FFFFFF"
        contrastSource: fill_contrast
      solid_action_on_inverse:
        surface: inverse_action_run
        backgroundColor: "#2F6FE0"
        textColor: "#FFFFFF"
        contrastSource: fill_contrast
    doNotUseFor: ["secondary or low-emphasis actions"]
  outline_button:
    kind: button
    actualPageUI: true
    confidence: high
    anatomy: ["text label", "thin border", "pill container"]
    base:
      typography: "{typography.control_text}"
      padding: "12px 24px"
      radius: "999px"
      display: inline-flex
      widthBehavior: content_hugging
      cssSizingHint: "display:inline-flex; width:max-content; max-width:100%; white-space:nowrap; flex:0 0 auto"
      textTransform: none
    variants:
      on_light:
        surface: page_canvas
        backgroundColor: "transparent"
        textColor: "#15372C"
        borderColor: "#15372C"
        contrastSource: same_surface_border
      on_inverse:
        surface: inverse_footer
        backgroundColor: "transparent"
        textColor: "#F3F1EA"
        borderColor: "rgba(243,241,234,0.5)"
        contrastSource: same_surface_border
    doNotUseFor: ["primary conversion actions"]
  icon_button:
    kind: icon_button
    actualPageUI: true
    confidence: medium
    anatomy: ["single-color glyph", "optional circular fill"]
    base:
      typography: "n/a (icon only)"
      padding: "8px"
      radius: "999px"
      display: inline-flex
      widthBehavior: icon_only
      cssSizingHint: "width:40px; height:40px; display:inline-flex; align-items:center; justify-content:center; flex:0 0 auto"
      textTransform: unclear
    variants:
      utility_on_light:
        surface: page_canvas
        backgroundColor: "transparent"
        iconColor: "#15372C"
        contrastSource: none
      dismiss_on_inverse:
        surface: inverse_strip
        backgroundColor: "transparent"
        iconColor: "#F3F1EA"
        contrastSource: fill_contrast
      social_chip_on_footer:
        surface: inverse_footer
        backgroundColor: "#5F9C84"
        iconColor: "#14352B"
        contrastSource: fill_contrast
    doNotUseFor: ["text-bearing actions"]
  feature_card:
    kind: card
    actualPageUI: true
    confidence: high
    anatomy: ["rounded media well", "optional overlay label chip", "serif heading", "body paragraph", "outlined CTA or text link"]
    base:
      typography: "{typography.h3}"
      padding: "0"
      radius: "0"
      display: flex
      widthBehavior: parent_stretched
      cssSizingHint: "display:flex; flex-direction:column; gap:16px"
      textTransform: preserve_authored_case
    variants:
      chromeless_on_light:
        surface: page_canvas
        backgroundColor: "transparent"
        textColor: "#15372C"
        borderColor: "none"
        shadow: "none"
        contrastSource: whitespace
    doNotUseFor: ["surfaces requiring a filled card chrome or border"]
  media_overlay_chip:
    kind: compact_label
    actualPageUI: true
    confidence: medium
    anatomy: ["leading single-color glyph", "label text", "pill container"]
    base:
      typography: "{typography.body_muted}"
      padding: "6px 12px"
      radius: "999px"
      display: inline-flex
      widthBehavior: content_hugging
      cssSizingHint: "display:inline-flex; width:max-content; max-width:100%; white-space:nowrap; flex:0 0 auto"
      textTransform: none
    variants:
      white_on_media:
        surface: media_host
        backgroundColor: "#FFFFFF"
        textColor: "#15372C"
        contrastSource: fill_contrast
    doNotUseFor: ["interactive primary actions"]
  text_input:
    kind: input
    actualPageUI: true
    confidence: medium
    anatomy: ["field", "optional label above"]
    base:
      typography: "{typography.body}"
      padding: "12px 16px"
      radius: "8px"
      display: block
      widthBehavior: full_width
      cssSizingHint: "width:100%"
      textTransform: none
    variants:
      on_inverse:
        surface: inverse_footer
        backgroundColor: "#FFFFFF"
        textColor: "#15372C"
        borderColor: "none"
        contrastSource: fill_contrast
    doNotUseFor: ["non-form decorative use"]
  divider_vertical:
    kind: other
    actualPageUI: true
    confidence: medium
    anatomy: ["thin vertical rule"]
    base:
      typography: "n/a"
      padding: "0"
      radius: "0"
      display: block
      widthBehavior: fixed_size
      cssSizingHint: "width:1px; align-self:stretch"
      textTransform: unclear
    variants:
      on_light:
        surface: page_canvas
        borderColor: "#D8E0DB"
        contrastSource: divider
    doNotUseFor: ["high-contrast separation where whitespace suffices"]
  floating_widget:
    kind: panel
    actualPageUI: true
    confidence: medium
    anatomy: ["white rounded panel", "title", "subtext", "fine print"]
    base:
      typography: "{typography.body}"
      padding: "16px"
      radius: "10px"
      display: flex
      widthBehavior: fixed_size
      cssSizingHint: "position:fixed; max-width:320px"
      textTransform: none
    variants:
      elevated:
        surface: card_surface
        backgroundColor: "#FFFFFF"
        textColor: "#15372C"
        shadow: "0 12px 32px rgba(0,0,0,0.16)"
        contrastSource: shadow
    doNotUseFor: ["primary in-flow content panels"]

patterns:
  layout:
    - "Constrained centered content column inside full-bleed section runs; section runs alternate light, mint, and deep-green inverse surfaces."
    - "Three-up equal-width feature column grid on a light canvas, each column an image-led chromeless stack."
    - "Split layout: left-aligned heading + single primary CTA column beside a multi-cell logo/proof grid, separated by a hairline vertical rule."
    - "Section heading stacked above a wider multi-column module."
    - "Footer link-column grid plus a newsletter/utility aside on a deep-green canvas."
  page_moments:
    - "Opening bookend: introductory banner on a soft mint canvas with central messaging flanked by floating media and embedded product-UI snippets."
    - "Closing bookend: full-width deep-green call-to-action band with an oversized heading, single primary action, and a subtle decorative brand motif."
    - "Utility band: thin deep-green inverse strip carrying a single line of promo/notice text with a trailing bold underlined inline link."
    - "Inset child-panel behavior: white elevated cards float over mint or light canvases via radius + soft shadow."
  content_composition:
    - "Image-led cards: rounded media well on top, serif heading, short sans body, then an outlined pill CTA or underlined text link."
    - "Editorial heading pattern: high-contrast serif heading with a single italic emphasis word."
    - "Proof rows: brand logo marks placed directly on white with no individual containers, native brand colors retained."
  adjacency_principles:
    - "Parent canvas color comes from edge/gutter continuity; cards and media wells remain child/inset surfaces unless they visibly become a full-width reset."
    - "Deep-green inverse runs are localized bands, not the global page background; white is the default page canvas."
    - "Adjacent deep-green runs may share a family hue while remaining distinct surfaces; do not merge a notice strip, CTA band, and footer into one surface."
    - "Photography may bleed to section edges as foreground media rather than sitting inside a framed well when a band acts as breathing space."
  background_systems:
    - "Flat single-color fills dominate; CTA run carries a subtle internal tonal shift, not a hard gradient."
    - "Entry into a tinted run may begin from the previous parent canvas color before settling into the run color."
  image_graphics:
    - "Single-color icons are inline glyphs, never image-generation candidates."
    - "Multi-color pictorial icons (if any) are the only icon class eligible for gpt-image-2."
    - "Logos/wordmarks and customer marks are not image-generation candidates; record footprint and color relationship only."
    - "Embedded product-UI cards and panels are showcase-only and must not become real page UI."
    - "Photography fills rounded media wells edge-to-edge; rounding/clipping belongs to the frame, not the photo asset."
  responsive:
    - "Multi-column grids collapse to single column on narrow viewports; centered intro stacks above modules."
    - "Compact controls stay content-hugging across breakpoints; inputs go full-width inside forms."

imagery:
  icons:
    observed: true
    iconAssetClasses: ["single-color-icon", "logo/wordmark"]
    generationStrategy: phosphor_currentColor_svg
    creativeDirection: "Minimal single-tone utility glyphs (search, dismiss, social, small leading marks) matching the local surface color."
    density: sparse
    simplicity: minimal
    rendering: line
    paletteRelationship: "single tone keyed to surface — dark glyphs on light, pale/light glyphs on inverse, knockout glyphs inside accent chips"
    surfaceRelationship: "inline on text rows, control interiors, footer social chips, and media overlay pills"
    edgeAndScale: "small, ~16-24px, even weight, no decorative framing"
    implementationRule: "Implement as inline Phosphor-style SVGs using currentColor; not image-generation candidates."
    subjectPolicy: "style from design system; subject from local component slot"
    avoid: ["multi-color rendering", "heavy detail", "treating logos as generated icons"]
  illustrations:
    observed: true
    creativeDirection: "Sparse, subtle decorative brand motif (e.g. soft organic/leaf-like vector) blended into deep-green CTA backgrounds; barely-there tonal contrast."
    density: sparse
    simplicity: minimal
    rendering: flat_vector
    paletteRelationship: "tone-on-tone, only marginally lighter/darker than the host band"
    surfaceRelationship: "background-blended within inverse runs"
    edgeAndScale: "large, soft, low-contrast; never a focal foreground element"
    subjectPolicy: "style from design system; subject from local component slot"
    avoid: ["high-detail or multi-color illustration", "literal scenes", "foreground prominence"]
  interfaces:
    observed: true
    creativeDirection: "Clean product-UI snippets — white mini cards with avatar rows, dropdowns, bar charts, status pills, and a dark-green candidate panel with overlapping profile thumbnails."
    density: moderate
    simplicity: simple
    rendering: stylized_ui
    paletteRelationship: "white surfaces with green accents; dark-green showcase panels"
    surfaceRelationship: "embedded showcase only — floated over mint/light canvases or inside media wells"
    edgeAndScale: "contained cards/panels with rounded corners and soft elevation"
    subjectPolicy: "style from design system; subject from local component slot"
    avoid: ["promoting embedded UI into real page UI", "device mockups"]
  photography:
    observed: true
    creativeDirection: "Warm, candid, human-centered workplace photography; soft natural lighting, realistic, slightly muted warm tones."
    density: moderate
    simplicity: moderate
    rendering: environmental
    paletteRelationship: "natural warm neutrals that harmonize with green canvases"
    surfaceRelationship: "foreground media in rounded wells, or edge-bleeding fragments on flat bands"
    edgeAndScale: "fills the frame to all edges"
    assetEdgeBehavior: edge_to_edge_photo_content
    subjectPolicy: "style from design system; subject from local component slot"
    avoid: ["studio-sterile or stocky compositions", "baking rounded frames into the photo asset"]

rules:
  color:
    - "Default page canvas is white (#FFFFFF); deep greens are localized inverse runs, not the global background."
    - "On inverse surfaces use pale-cream text (#F3F1EA) for primary, muted green (#5F9C84) for low emphasis."
    - "Primary green pill (#4CB398) is used on light surfaces; blue (#2F6FE0) primary appears only on the deep-green CTA run; deep-green fill primary appears on the mint canvas."
  typography:
    - "Body and paragraph tokens stay 14-16px Inter with ~160% line-height."
    - "Serif family is reserved for page/section/content headings; never for body, controls, or labels."
    - "Text links and text-bearing controls use canonical body-size sans; only icon-only controls drop text."
    - "Headings preserve authored case with a single italic emphasis word where present."
  spacing:
    - "Use generous vertical padding for tall sections; consistent grid gutters across multi-column rows."
    - "Maintain even internal vertical rhythm within each card stack."
  containers:
    - "Center constrained content inside full-bleed runs; logo grids and feature grids sit in a constrained container."
  components:
    - "Buttons, chips, and labels are content-hugging unless explicitly full-width (inputs) or parent-stretched (cards)."
    - "Do not bake positional align-self into compact control base recipes; alignment comes from parent layout."
  cards:
    - "Feature cards are chromeless on light canvases (no fill, no border, no shadow); separation is whitespace and the media well."
    - "Floating white mini-cards and the help widget use radius + soft shadow over tinted canvases."
    - "Do not add borders to high-contrast cards unless grounded."
  links_actions:
    - "Inline links are bold/underlined and brighter than surrounding body text on inverse surfaces."
    - "Each feature item terminates in an outlined pill CTA or an underlined text link."
  imagery_graphics:
    - "Illustrations stay sparse and tone-on-tone; do not increase illustration complexity beyond subtle background motifs."
    - "Single-color icons are inline SVGs; logos/wordmarks and customer marks are never generated assets — fall back to simple text/rectangle in the current surface color."
    - "Photography is generated edge-to-edge; framing/rounding lives in the component."
  motion_animation:
    - "Use restrained system-native transitions: hover color/opacity on links and buttons, gentle fade/translate reveals on cards and photography."
    - "No motion that breaks surface grammar, reflows the grid, or animates embedded showcase UI as if interactive."
  accessibility:
    - "Maintain high contrast for pale-cream text on deep-green runs and dark-green text on light/mint canvases."
    - "Icon-only controls require accessible labels."

do_not_generalize:
  - "Deep-green inverse strips/bands are localized runs; do not treat them as the global page background."
  - "Embedded product-UI cards, candidate panels, status badges, and floating mini-cards are showcase-only and must not become real reusable page UI."
  - "The dark-green media well inside a feature card is a local variant, not the default for all feature cards."
  - "Blue (#2F6FE0) primary fill is only observed on the deep-green CTA run; do not make it the global primary button color."
  - "Customer logo marks render in native brand colors directly on white with no container; do not stylize, recolor, or frame them."
  - "Mint canvas is a localized introductory/breathing surface, not a global accent fill."

embedded_showcase_only:
  - "Floating profile/candidate card with avatar row, status badge, and meta row."
  - "Report-builder mini card with dropdowns and bar chart."
  - "Dark-green candidate panel with overlapping circular profile thumbnails and risk/status pill."

open_questions:
  - "Exact serif heading family is unconfirmed; only Inter is present in source CSS while grounding clearly shows serif headings."
  - "Whether the mint introductory canvas hue is closer to #CDEBDD or a lighter desaturated mint."
  - "Presence/exact placement of a dismiss icon on the announcement strip (low confidence)."
  - "Whether all feature cards include a CTA control or some terminate only in a text link."
  - "Exact footer outline-button border color and social-chip fill hue."
