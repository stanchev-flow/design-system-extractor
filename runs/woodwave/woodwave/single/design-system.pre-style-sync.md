schema_version: design_system_yaml.v1
type: design_system
metadata:
  name: editorial_didone_two_tone
  description: "A warm two-tone editorial system pairing oversized uppercase didone display type, hard-edged unframed photography, staggered collage layouts, ghost typographic watermarks, and chrome-free text-only actions."
  source: normalized_site_ast
  generated_from: []
  confidence: high
tokens:
  color:
    surface:
      primary: "#FAF0E8"
      inverse: "#3A2F23"
      inverseStrong: "#1B150F"
      panel: "#F7EFE6"
    text:
      onPrimary: "#1F1A14"
      onPrimaryMuted: "#4A4239"
      onInverse: "#F5EDE2"
      onInverseMuted: "#C9BFB2"
      accent: "#E9DC8C"
      ghostOnPrimary: "rgba(31,26,20,0.06)"
    border:
      hairlineOnPanel: "rgba(31,26,20,0.25)"
      hairlineOnPrimary: "rgba(31,26,20,0.30)"
    accent:
      highlight: "#E9DC8C"
    graphic:
      mapDesaturated: "#B9B5B0"
  typography:
    displaySerif: "high-contrast didone serif, uppercase"
    labelSans: "small tracked uppercase grotesque sans"
    bodySans: "humanist sans, sentence case"
  spacing:
    xs: "12px"
    sm: "16px"
    md: "24px"
    lg: "40px"
    xl: "56px"
    xxl: "100px"
    xxxl: "120px"
    sectionPaddingLight: "110px"
    sectionPaddingDark: "100px"
    moduleGapEditorial: "120px"
    captionToMedia: "12px"
    eyebrowToHeading: "24px"
    listRowHeight: "36px"
    panelPadding: "28px"
  radius:
    none: "0px"
  shadow:
    none: "none"
  divider:
    hairline: "1px solid rgba(31,26,20,0.25)"
    underlineInput: "1px solid rgba(31,26,20,0.30)"
  motion:
    durationShort: "200ms"
    durationMedium: "450ms"
    easing: "cubic-bezier(0.22, 1, 0.36, 1)"
surfaces:
  primary:
    value: "{tokens.color.surface.primary}"
    role: page_canvas
    text:
      default: "{tokens.color.text.onPrimary}"
      muted: "{tokens.color.text.onPrimaryMuted}"
      accent: "{tokens.color.text.onPrimary}"
    border: "{tokens.color.border.hairlineOnPrimary}"
    shadow: none
    gradient: none
    usage:
      - dominant editorial canvas for collage stacks, centered CTA stacks, and watermark layering
    confidence: high
  inverse:
    value: "{tokens.color.surface.inverse}"
    role: inverse_run
    text:
      default: "{tokens.color.text.onInverse}"
      muted: "{tokens.color.text.onInverseMuted}"
      accent: "{tokens.color.text.accent}"
    border: none
    shadow: none
    gradient: none
    usage:
      - opening bookend band hosting display title and layered media collage
      - mid-page informational band hosting high-contrast cream child panels
    confidence: high
  inverseStrong:
    value: "{tokens.color.surface.inverseStrong}"
    role: inverse_run
    text:
      default: "{tokens.color.text.onInverse}"
      muted: "{tokens.color.text.onInverseMuted}"
      accent: "{tokens.color.text.accent}"
    border: none
    shadow: none
    gradient: none
    usage:
      - closing bookend utility band; darkest tier on the page, reserved for the final stack
    confidence: high
  panel:
    value: "{tokens.color.surface.panel}"
    role: inset_panel
    text:
      default: "{tokens.color.text.onPrimary}"
      muted: "{tokens.color.text.onPrimaryMuted}"
      accent: "{tokens.color.text.onPrimary}"
    border: "{tokens.color.border.hairlineOnPanel}"
    shadow: none
    gradient: none
    usage:
      - light child panels placed on inverse runs, separated by fill contrast alone
      - hosts labeled info subgroups and ruled list rows
    confidence: high
  mediaHost:
    value: "transparent"
    role: media_host
    text:
      default: "{tokens.color.text.onInverse}"
      muted: "{tokens.color.text.onInverseMuted}"
      accent: "{tokens.color.text.onInverse}"
    border: none
    shadow: none
    gradient: none
    usage:
      - full-bleed photographic rhythm-break band with hard top and bottom edges; no overlaid UI
    confidence: high
typography:
  displayHero:
    fontFamily: "high-contrast didone display serif"
    fontFamilyCategory: serif
    visualCharacteristics:
      - very high stroke contrast with hairline thins and bold vertical thicks (didone construction)
      - tall, narrow, condensed uppercase letterforms
      - ball/teardrop terminals on curved strokes
      - flat, thin unbracketed serifs
      - closed apertures and vertical stress
      - elegant, fashion-editorial character
    fontSize: "96px"
    fontWeight: "400"
    lineHeight: "1.05"
    letterSpacing: "0.02em"
    textTransform: uppercase
    role: "page_heading / opening-bookend display title; may overlap media"
    confidence: high
  h1:
    fontFamily: "high-contrast didone display serif"
    fontFamilyCategory: serif
    visualCharacteristics:
      - extreme thick/thin stroke modulation
      - condensed uppercase proportions
      - thin flat serifs and ball terminals
      - vertical axis, closed counters
    fontSize: "56px"
    fontWeight: "400"
    lineHeight: "1.15"
    letterSpacing: "0.02em"
    textTransform: uppercase
    role: "page heading below display tier"
    confidence: high
  h2:
    fontFamily: "high-contrast didone display serif"
    fontFamilyCategory: serif
    visualCharacteristics:
      - same didone family as h1
      - hairline thins remain legible at mid-display sizes
      - uppercase multi-line blocks with airy line spacing
    fontSize: "36px"
    fontWeight: "400"
    lineHeight: "1.3"
    letterSpacing: "0.02em"
    textTransform: uppercase
    role: "section_heading for editorial blocks and panel titles"
    confidence: high
  h3:
    fontFamily: "high-contrast didone display serif"
    fontFamilyCategory: serif
    visualCharacteristics:
      - didone family at compact heading scale
      - uppercase, restrained tracking
    fontSize: "26px"
    fontWeight: "400"
    lineHeight: "1.3"
    letterSpacing: "0.02em"
    textTransform: uppercase
    role: "content_heading / panel title (e.g., titled inset panels)"
    confidence: medium
  ghostWatermark:
    fontFamily: "high-contrast didone display serif"
    fontFamilyCategory: serif
    visualCharacteristics:
      - same didone display family rendered at enormous background scale
      - extreme low contrast against the canvas (~6% opacity tone)
      - uppercase words or oversized numerals spanning near full section width
    fontSize: "clamp(200px, 28vw, 420px)"
    fontWeight: "400"
    lineHeight: "1.0"
    letterSpacing: "0.02em"
    textTransform: uppercase
    role: "decorative_emphasis background watermark; never replaces semantic headings"
    confidence: high
  counterDisplay:
    fontFamily: "high-contrast didone display serif"
    fontFamilyCategory: serif
    visualCharacteristics:
      - didone numerals with strong modulation
      - medium display scale, single short string
    fontSize: "32px"
    fontWeight: "400"
    lineHeight: "1.0"
    letterSpacing: "0.02em"
    textTransform: none
    role: "numeric counter / index label paired with an eyebrow on the same row"
    confidence: high
  eyebrow:
    fontFamily: "neutral grotesque sans"
    fontFamilyCategory: sans_serif
    visualCharacteristics:
      - small uppercase sans with wide letterspacing
      - moderate x-height, low stroke contrast, monoline feel
      - open apertures, plain squared terminals
    fontSize: "11px"
    fontWeight: "500"
    lineHeight: "1.2"
    letterSpacing: "0.14em"
    textTransform: uppercase
    role: "label_metadata: eyebrows, micro captions in margins, group labels inside panels"
    confidence: high
  body:
    fontFamily: "humanist grotesque sans"
    fontFamilyCategory: sans_serif
    visualCharacteristics:
      - low stroke contrast humanist sans
      - moderate x-height and open apertures
      - sentence case, quiet and neutral
      - comfortable reading rhythm at small sizes
    fontSize: "14px"
    fontWeight: "400"
    lineHeight: "1.55"
    letterSpacing: "0"
    textTransform: none
    role: "body paragraphs in narrow measures; label-value rows"
    confidence: high
  controlText:
    fontFamily: "neutral grotesque sans"
    fontFamilyCategory: sans_serif
    visualCharacteristics:
      - uppercase tracked sans matching the eyebrow family
      - monoline strokes, even color at small sizes
    fontSize: "14px"
    fontWeight: "500"
    lineHeight: "1.2"
    letterSpacing: "0.10em"
    textTransform: uppercase
    role: "control_text: nav links, arrow actions, inline submit, social links"
    confidence: high
  footerSitemapLink:
    fontFamily: "high-contrast didone display serif"
    fontFamilyCategory: serif
    visualCharacteristics:
      - didone display family used as oversized link text
      - uppercase, slash-separated inline run
    fontSize: "40px"
    fontWeight: "400"
    lineHeight: "1.4"
    letterSpacing: "0.02em"
    textTransform: uppercase
    role: "display-scale link tier inside the closing bookend; contextual, not a default link size"
    confidence: high
components:
  navBar:
    kind: other
    actualPageUI: true
    confidence: high
    anatomy:
      - left logo lockup
      - center slash-separated text link row
      - right utility text link
    base:
      typography: "{typography.controlText}"
      padding: "20px 0"
      radius: "0"
      display: flex
      widthBehavior: parent_stretched
      cssSizingHint: "justify-content: space-between; align-items: center"
      textTransform: uppercase
    variants:
      onInverse:
        surface: inverse
        backgroundColor: "transparent"
        textColor: "{tokens.color.text.onInverse}"
        borderColor: "none"
        iconColor: "{tokens.color.text.accent}"
        shadow: "none"
        contrastSource: fill_contrast
    doNotUseFor:
      - light-surface headers (not grounded)
  textLink:
    kind: link
    actualPageUI: true
    confidence: high
    anatomy:
      - uppercase tracked label
      - optional slash separator between siblings
    base:
      typography: "{typography.controlText}"
      padding: "0"
      radius: "0"
      display: inline-flex
      widthBehavior: content_hugging
      cssSizingHint: "display: inline-flex; width: max-content; max-width: 100%; white-space: nowrap; flex: 0 0 auto"
      textTransform: uppercase
    variants:
      onInverse:
        surface: inverse
        backgroundColor: "transparent"
        textColor: "{tokens.color.text.onInverse}"
        contrastSource: fill_contrast
      onPrimary:
        surface: primary
        backgroundColor: "transparent"
        textColor: "{tokens.color.text.onPrimary}"
        contrastSource: fill_contrast
    doNotUseFor:
      - filled or pill button styling (no filled buttons exist in this system)
  arrowTextAction:
    kind: link
    actualPageUI: true
    confidence: high
    anatomy:
      - uppercase tracked label
      - trailing long-arrow glyph (→)
    base:
      typography: "{typography.controlText}"
      padding: "0"
      radius: "0"
      display: inline-flex
      widthBehavior: content_hugging
      cssSizingHint: "display: inline-flex; align-items: center; gap: 8px; width: max-content; max-width: 100%; white-space: nowrap; flex: 0 0 auto"
      textTransform: uppercase
    variants:
      onPanel:
        surface: panel
        backgroundColor: "transparent"
        textColor: "{tokens.color.text.onPrimary}"
        iconColor: "{tokens.color.text.onPrimary}"
        contrastSource: fill_contrast
      onPrimary:
        surface: primary
        backgroundColor: "transparent"
        textColor: "{tokens.color.text.onPrimary}"
        iconColor: "{tokens.color.text.onPrimary}"
        contrastSource: fill_contrast
    doNotUseFor:
      - circular or boxed icon-button treatment (no enclosed controls grounded)
      - underlined link styling
  eyebrowLabel:
    kind: compact_label
    actualPageUI: true
    confidence: high
    anatomy:
      - single uppercase tracked word or short phrase
    base:
      typography: "{typography.eyebrow}"
      padding: "0"
      radius: "0"
      display: inline-flex
      widthBehavior: content_hugging
      cssSizingHint: "display: inline-flex; width: max-content; max-width: 100%; white-space: nowrap; flex: 0 0 auto"
      textTransform: uppercase
    variants:
      onPrimary:
        surface: primary
        backgroundColor: "transparent"
        textColor: "{tokens.color.text.onPrimaryMuted}"
        contrastSource: fill_contrast
      onInverse:
        surface: inverse
        backgroundColor: "transparent"
        textColor: "{tokens.color.text.onInverseMuted}"
        contrastSource: fill_contrast
    doNotUseFor:
      - pill, chip, or bordered badge styling (never grounded)
  microCaption:
    kind: compact_label
    actualPageUI: true
    confidence: high
    anatomy:
      - one-to-two-line uppercase metadata text placed in negative space beside media
    base:
      typography: "{typography.eyebrow}"
      padding: "0"
      radius: "0"
      display: inline-flex
      widthBehavior: content_hugging
      cssSizingHint: "display: inline-flex; width: max-content; max-width: 18ch; flex: 0 0 auto"
      textTransform: uppercase
    variants:
      onPrimary:
        surface: primary
        backgroundColor: "transparent"
        textColor: "{tokens.color.text.onPrimaryMuted}"
        contrastSource: whitespace
    doNotUseFor:
      - overlaying directly on photos (captions sit in adjacent margin space)
  mediaFrame:
    kind: media_frame
    actualPageUI: true
    confidence: high
    anatomy:
      - hard-edged photograph clipped to a sharp rectangle
    base:
      typography: ""
      padding: "0"
      radius: "0"
      display: block
      widthBehavior: intrinsic_media
      cssSizingHint: "object-fit: cover; border-radius: 0; box-shadow: none; border: none"
      textTransform: none
    variants:
      foreground:
        surface: primary
        backgroundColor: "transparent"
        contrastSource: fill_contrast
      foregroundOnInverse:
        surface: inverse
        backgroundColor: "transparent"
        contrastSource: fill_contrast
    doNotUseFor:
      - rounded, bordered, shadowed, or matted media (system is strictly frameless)
  infoPanel:
    kind: panel
    actualPageUI: true
    confidence: high
    anatomy:
      - cream panel
      - eyebrow group labels
      - body-text label-value rows (label left, value right)
    base:
      typography: "{typography.body}"
      padding: "{tokens.spacing.panelPadding}"
      radius: "0"
      display: block
      widthBehavior: fixed_size
      cssSizingHint: "max-width: ~320px when overlapping media; no border-radius; no shadow"
      textTransform: preserve_authored_case
    variants:
      onInverse:
        surface: inverse
        backgroundColor: "{tokens.color.surface.panel}"
        textColor: "{tokens.color.text.onPrimary}"
        dividerColor: "{tokens.color.border.hairlineOnPanel}"
        contrastSource: fill_contrast
    doNotUseFor:
      - same-surface cards on the cream canvas (not grounded; cream canvas uses open editorial modules)
  ruledListPanel:
    kind: panel
    actualPageUI: true
    confidence: high
    anatomy:
      - cream panel with didone title
      - stacked rows; left value + label, right arrow text action
      - hairline divider beneath each row
    base:
      typography: "{typography.body}"
      padding: "{tokens.spacing.panelPadding}"
      radius: "0"
      display: block
      widthBehavior: parent_stretched
      cssSizingHint: "rows ~36px tall; row: flex; justify-content: space-between; border-bottom: {tokens.divider.hairline}"
      textTransform: preserve_authored_case
    variants:
      onInverse:
        surface: inverse
        backgroundColor: "{tokens.color.surface.panel}"
        textColor: "{tokens.color.text.onPrimary}"
        dividerColor: "{tokens.color.border.hairlineOnPanel}"
        iconColor: "{tokens.color.text.onPrimary}"
        contrastSource: fill_contrast
    doNotUseFor:
      - dark-surface list rows (only cream-panel rows grounded)
  underlineInputRow:
    kind: input
    actualPageUI: true
    confidence: high
    anatomy:
      - uppercase placeholder text
      - shared hairline underline spanning the row
      - inline arrow text submit at the right end of the same underline
    base:
      typography: "{typography.controlText}"
      padding: "0 0 12px 0"
      radius: "0"
      display: flex
      widthBehavior: parent_stretched
      cssSizingHint: "width: 100% of its narrow centered column; border-bottom: {tokens.divider.underlineInput}; justify-content: space-between; align-items: baseline"
      textTransform: uppercase
    variants:
      onPrimary:
        surface: primary
        backgroundColor: "transparent"
        textColor: "{tokens.color.text.onPrimary}"
        borderColor: "{tokens.color.border.hairlineOnPrimary}"
        contrastSource: divider
    doNotUseFor:
      - boxed, filled, or rounded inputs; filled submit buttons
patterns:
  layout:
    - "Wide page container with generous side margins; content typically occupies only part of the container (paragraphs ~1/3 width, headings 1/2–2/3 width) with staggered horizontal anchor points per module."
    - "Editorial collage stack: loose one-column field of [media rectangle + margin micro-caption + narrow offset paragraph] modules at alternating left/center-right anchors, separated by ~120px gaps."
    - "Centered narrow stack: eyebrow → multi-line didone heading → single control row, used for quiet conversion and utility moments."
    - "Two-cell split panel: flush hard-edged photo on one side, cream titled panel with ruled action rows on the other, hosted on an inverse run."
    - "Overlay composite: contained media rectangle (e.g., desaturated map) with a light info panel overlapping its left edge and extending past its bottom edge."
    - "Eyebrow + oversized counter row: small uppercase label at left, didone numeral counter at right, full negative space between, preceding a media field."
    - "Full-bleed media band: edge-to-edge photograph with no container, no overlay UI, hard top and bottom edges, used as a rhythm break in long light runs."
  page_moments:
    - "Opening bookend: deep inverse band with centered oversized didone title overlapping the top edge of a layered photo collage; collage images stagger and overlap each other; the accent yellow may color the display title and logo here."
    - "Closing bookend: darkest surface tier with a fully centered stack — accent logo, display-scale slash-separated serif link run, small uppercase social row, compact utility/legal strip."
    - "Quiet conversion moment: centered eyebrow + didone heading + underline input row on the light canvas, immediately before the closing bookend."
    - "Inverse informational band: dark run hosting cream child panels (overlay composite and split list panel) with eyebrow + didone heading introducing it."
  content_composition:
    - "Heading-led modules: large multi-line uppercase didone block first, then media, then narrow supporting paragraph offset beside or below the media."
    - "Caption-in-margin: tiny uppercase metadata anchored in the negative-space column adjacent to a photo, ~12px from its edge."
    - "Ghost watermark layering: enormous low-contrast didone word or numerals anchored across the section width behind both headings and media; foreground content deliberately overlaps it; legibility preserved via ~6% opacity."
    - "Paragraphs keep narrow measures (~33% container width) with ~1.55 line-height; never full-width text."
  adjacency_principles:
    - "Parent canvases alternate between light cream and deep warm brown via hard fill resets; no gradients, fades, or divider rules at section seams."
    - "A seam may be softened by a small foreground photo deliberately straddling the boundary between two parent surfaces; this is an optional bridging device, not a default."
    - "Cream panels are always children of inverse runs, separated by fill contrast alone — no borders, radius, or shadows."
    - "The darkest surface tier is reserved for the final utility/closing moment and is never used mid-flow."
    - "Yellow accent appears only on dark surfaces (logo, display title); it never appears on the cream canvas."
  background_systems:
    - "Three flat surface tiers only: cream canvas, deep warm brown, near-black brown. Zero gradients, zero rounded corners, zero shadows anywhere."
    - "Ghost typographic watermarks are the only background decoration system; they use the display serif at background scale and extreme low contrast."
    - "Overlap is ornament: text over media, media over media, panel over media, media over seam — composed with hard rectangles, never with masks or soft edges."
  image_graphics:
    - "Photography is the dominant imagery class: hard-edged, unframed, clipped rectangles placed as foreground media; one band may go full-bleed with no container."
    - "Generated photography must fill its asset edge-to-edge; all clipping/positioning belongs to the page layout, never inside the asset."
    - "Functional graphics (map-style images) are desaturated grayscale, background-contained inside their rectangle, and may carry a simple pin marker and overlapping info panel."
    - "Single-color glyphs (arrows, slashes, pin) are typographic/inline-SVG accents using currentColor; they are not image-generation candidates."
    - "Multi-color icons are not part of this system; if ever needed they would be the only icon class eligible for gpt-image-2 generation."
    - "Logos/wordmarks are never generated assets; render as text/wordmark in the accent color on dark surfaces only."
  responsive:
    - "Staggered collage anchors collapse to a single left-aligned column on narrow viewports; captions move above or below their media."
    - "Display didone scales fluidly (clamp) and may drop the media-overlap behavior when vertical space is constrained."
    - "Overlay composites (panel over media) stack vertically on narrow viewports with the panel below the media."
    - "Slash-separated link runs wrap to multiple centered lines rather than truncating."
imagery:
  icons:
    observed: true
    iconAssetClasses:
      - single-color-icon
      - logo/wordmark
    generationStrategy: phosphor_currentColor_svg
    creativeDirection: "Minimal monoline glyph accents only: long trailing arrows on text actions, slash separators between links, a simple map pin. Rendered inline in currentColor at text scale."
    density: sparse
    simplicity: minimal
    rendering: line
    paletteRelationship: "Always currentColor of the host text role; never accent-colored independently."
    surfaceRelationship: "Sit inline with control text on cream or dark surfaces; no enclosing shapes."
    edgeAndScale: "Glyph-sized (~1em), thin monoline strokes, no containers."
    implementationRule: "Inline Phosphor-style SVG with stroke/fill = currentColor; logos/wordmarks render as text in the accent color, never as generated images."
    subjectPolicy: "style from design system; subject from local component slot"
    avoid:
      - filled icon buttons or circular icon enclosures
      - multi-color or dimensional icons
      - icon-only navigation
  illustrations:
    observed: false
    creativeDirection: "No illustrations in this system; decorative interest comes from ghost typography and photographic overlap, not drawn artwork."
    density: sparse
    simplicity: minimal
    rendering: none_observed
    paletteRelationship: "n/a"
    surfaceRelationship: "n/a"
    edgeAndScale: "n/a"
    subjectPolicy: "style from design system; subject from local component slot"
    avoid:
      - introducing illustration styles not present in the source
      - blobs, meshes, abstract shapes, or drawn ornament
  interfaces:
    observed: false
    creativeDirection: "No UI screenshots or device mockups appear; do not introduce them."
    density: sparse
    simplicity: minimal
    rendering: none_observed
    paletteRelationship: "n/a"
    surfaceRelationship: "n/a"
    edgeAndScale: "n/a"
    subjectPolicy: "style from design system; subject from local component slot"
    avoid:
      - device frames, browser chrome, dashboard mockups
  photography:
    observed: true
    creativeDirection: "Warm-toned architectural and interior photography with sculptural light: wood textures, curved structures, gallery interiors, quiet human presence at small scale. Ambient, editorial, unstaged feel; one desaturated grayscale functional image style permitted for map-like graphics. Portraits are calm, frontal, softly lit against neutral grounds."
    density: moderate
    simplicity: moderate
    rendering: environmental
    paletteRelationship: "Warm browns, ambers, and creams that harmonize with the two-tone surface palette; occasional cool sky accents; functional graphics fully desaturated."
    surfaceRelationship: "Placed as hard-edged foreground rectangles on cream or dark canvases; one full-bleed band per long light run is acceptable as a rhythm break."
    edgeAndScale: "Sharp unframed rectangles at varied scales — small seam-bridging tiles, mid-size editorial blocks, tall heroes, full-bleed bands."
    assetEdgeBehavior: edge_to_edge_photo_content
    subjectPolicy: "style from design system; subject from local component slot"
    avoid:
      - rounded corners, borders, mats, or drop shadows baked into the photo
      - cool/clinical color grading
      - busy stock-style staged scenes
rules:
  color:
    - "Three flat surface tiers only (cream, deep brown, near-black brown); never introduce gradients, tints between tiers, or additional canvas colors."
    - "Accent yellow is reserved for dark surfaces — logo lockups and the opening display title; it must never appear on the cream canvas or inside cream panels."
    - "Text flips strictly: near-black on cream/panels, cream-white on dark tiers; arrow actions inside cream panels stay dark even when the parent run is dark."
    - "Ghost watermark text uses the canvas text color at ~6% opacity; it must remain non-competitive with foreground legibility."
  typography:
    - "All headings, display text, watermarks, counters, and the closing-bookend sitemap use the single didone serif family in uppercase; weight stays regular — hierarchy is size-driven."
    - "h1/h2 derive only from page/section heading evidence: uppercase didone, regular weight, ~1.15–1.3 line-height; control and label text never influence heading weight."
    - "Body text is 14px humanist sans at ~1.55 line-height in narrow measures; never exceed 16px for body roles."
    - "All text controls and links use 14px uppercase tracked sans (controlText) except the contextual display-scale sitemap tier in the closing bookend."
    - "Eyebrows and micro captions are 11px uppercase with wide (~0.14em) tracking; they are metadata, not headings."
  spacing:
    - "Light editorial runs use ~110px section padding and ~120px module gaps; dark runs use ~100px padding and slightly denser stacks."
    - "Micro pairings are tight: caption-to-media ~12px, eyebrow-to-heading ~24px, list rows ~36px tall."
    - "Whitespace is structural: paragraphs and captions occupy dedicated negative-space columns rather than filling the container."
  containers:
    - "Full-bleed colored wrappers with a wide inset container are the default; the only containerless pattern is the full-bleed photo band."
    - "Centered narrow columns (~50% width) are reserved for conversion and closing-bookend moments."
  components:
    - "There are no filled, outlined, or pill buttons anywhere; all actions are typographic (tracked uppercase text, optionally with a trailing arrow)."
    - "Compact labels and links are content-hugging (inline-flex, max-content); center them inside centered stacks and start-align them inside left-aligned editorial modules via parent layout, not via the component recipe."
    - "Inputs are underline-only with an inline text submit sharing the same hairline; never box or fill form controls."
    - "Hairline dividers appear only inside cream panels (list rows) and as the form underline; never between sections."
  cards:
    - "Cream panels exist only as high-contrast children on dark runs, separated by fill alone — no borders, radius, or shadows."
    - "Do not create same-surface cards on the cream canvas; light-canvas content is composed as open collage modules."
    - "Panels may intentionally overlap their host media's edges (left edge and bottom edge), echoing the system's overlap motif."
  links_actions:
    - "Action emphasis is conveyed by size tier and arrow glyphs, never by fills, underlines, or color changes."
    - "Slash-separated inline link runs are the canonical multi-link pattern at three scales: header small caps, social small caps, and closing-bookend display serif."
    - "Repeated row actions in list panels use the arrowTextAction recipe right-aligned within each ruled row."
  imagery_graphics:
    - "All photos are hard-edged unframed rectangles; generated photo content must reach the asset edge."
    - "Ghost watermarks and overlap compositions are the only decoration systems; no blobs, glows, meshes, angled bands, or drawn ornament."
    - "Functional map-style graphics are desaturated grayscale and background-contained; they are static styled images, not interactive embeds, unless evidence says otherwise."
    - "Illustrations and interface mockups are absent from this system; do not generate them."
  motion_animation:
    - "Restrained editorial motion only: slow fade/translate reveals (~450ms, soft ease-out) on headings, media rectangles, and watermark text as they enter."
    - "Overlapping collage elements may use subtle differential scroll (gentle parallax) to reinforce the layering motif; keep offsets small so hard-rectangle composition stays intact."
    - "Link/action hovers: slight opacity shift or arrow nudge; never add fills, underlq-grow, or color flips that break the typographic-action grammar."
    - "No carousel autoplay or animated section transitions; surface resets remain instantaneous hard cuts."
  accessibility:
    - "Maintain strong contrast for foreground text on all three surface tiers; ghost watermarks must stay decorative and behind content with aria-hidden."
    - "Uppercase tracked control text must keep ≥14px sizing for legibility; arrow glyphs are decorative companions to text labels, never sole affordances."
    - "Underline inputs need programmatic labels despite their minimal visual chrome."
do_not_generalize:
  - "The seam-bridging photo straddling a dark-to-light boundary is an optional one-off device; do not apply it to every section seam."
  - "The numeric counter (didone '1/6') implies a slider but no controls were observed; do not generate carousel arrows/dots as system components."
  - "The display-scale serif sitemap link tier is exclusive to the closing bookend; never use display-serif links in body content or headers."
  - "Accent yellow on the opening display title is a bookend treatment, not a general heading color."
  - "The corner 'Buy $29' marketplace badge is a template overlay, not part of the design system."
  - "Photo reuse across modules is a source quirk, not a rule."
embedded_showcase_only:
  - "Framed paintings, wall labels, and display cases visible inside gallery photographs are photographic content, not page UI."
open_questions:
  - "Whether the counter belongs to an interactive media slider with offscreen controls; treated as a static index label."
  - "Exact ghost watermark opacity/color (estimated ~6% of canvas text color); tune for legibility per surface."
  - "Whether the header's right-aligned action carries any hover/active differentiation from nav links; none visible."
  - "Whether the map graphic is an embed or a static styled image; modeled as a static desaturated image with a pin."
  - "The truncated margin caption suggests stylized cropping; caption max-width treated as ~18ch with possible intentional truncation, low confidence."
