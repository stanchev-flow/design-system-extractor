# Webflow library inventory — AISB v2 - test 1 (real export)

Site `6a2b244f98ab655811c13cc2`. This is the REAL component + variable inventory of the target Webflow site. Compose pages ONLY from these components and variables; reference both by their exact names below.

Operating rules:
1. Layout-first: every section starts from a `Section / *` scaffold (or `Layout / *` inside it); fill slots with component instances only.
2. Reuse-before-create: map needs onto existing components/variants/props; mint a new component only on a true miss, composed from these primitives.
3. Theme via Color schemes modes on styles (surface flips = scheme mode change), not new colors. Bind colors/sizes to variables, never raw hex.
4. Spacing/width/radius come from `Sizes`, `Width`, `Section padding`, `Grid gap` collections (mode-driven on styles).

## Components (87 usable, grouped)

Components with `[slot …]` are scaffolds: instantiate them first, then fill slots with other component instances (never raw elements). `variant` props take one of the component's predefined variant options.

### Layout (18)

Scaffolds (have slots):
- **`Button Group`** — slots: `Slot` — props: Visibility:boolean; Direction:variant; Alignment:variant
- **`Layout / Bento /4`** — slots: `Slot`, `Slot`, `Slot`, `Slot` — props: Variant:variant
- **`Layout / Grid`** — slots: `Slot` — props: Columns:variant; Gap size:variant
- **`Layout / Row`** — slots: `Slot` — props: Align:variant; Wrap down:boolean(On/Off)
- **`Layout / Split`** — slots: `Slot`, `Slot 2` — props: Vertical position:variant; Size:variant; Position:boolean(Right/Left)
- **`Layout / Stack`** — slots: `Slot`
- **`Logos Wrapper`** — slots: `Slot` — props: Size:variant; Layout:variant
- **`Section / Split / Content and form`** — slots: `Slot`, `Slot 2` — props: Media side:variant; Overlay:boolean(None/Gradient); Image:image; Width:variant; Align vertical:variant; Background:boolean(Color/Media); Overlay:variant; Blur:variant
- **`Section / Split / Content and media`** — slots: `Slot`, `Slot 2` — props: Media side:variant; Overlay:boolean(None/Gradient); Image:image; Overlay:variant; Width:variant; Align vertical:variant; Background:boolean(Color/Media); Blur:variant
- **`Section / Split / Full bleed / Content and media`** — slots: `Slot`, `Slot 2` — props: Background:boolean(Color/Media); Overlay:boolean(None/Gradient); Image:image; Media:boolean(Right/Left); Align vertical:variant; Content width:variant; Overlay:variant; Blur:variant
- **`Section / Split card / Content and media`** — slots: `Slot` — props: Background:boolean(Color/Media); Overlay:boolean(None/Gradient); Image:image; Media:boolean(Show/Hide); Layout:boolean(Stack/Split); Style:boolean(Plain/Card); Width:variant; Overlay:variant; Blur:variant
- **`Section / Split card / Content and media - v2`** — slots: `Slot`, `Slot` — props: Background:boolean(Color/Media); Overlay:boolean(None/Gradient); Image:image; Style:boolean(Plain/Card); Width:variant; Side:boolean(Right/Left); Padding:boolean(None/Default); Overlay:variant; Blur:variant
- **`Section / Stack`** — slots: `Slot 3` — props: Background:boolean(Color/Media); Overlay:boolean(None/Gradient); Image:image; Width:variant; Overlay:variant; Blur:variant
- **`Section / Stack / Full bleed / Content and media`** — slots: `Slot`, `Slot` — props: Color:variant; Media:boolean(Bottom/Top); Content width:variant

Leaf components:
- **`Button Icon`** — props: Variant:variant; Visibility:boolean
- **`Form Item / Button`** — props: Position:variant; Text:string; Loading state text:string
- **`Form Item / Consent`** — props: Visibility:boolean; Label:text("I agree to the"); Privacy policy:boolean; Link to privacy policy page:link
- **`Form Item / Field`** — props: Visibility:boolean; Type:variant; Size:variant; Label:text("Name")

### Blocks/Text (12)

Leaf components:
- **`Accordion / Item`** — props: Question:text("How do I get started?"); Answer:richText; Anssswer preview:boolean(Open/Close)
- **`Author Info`** — props: Layout:variant; Visibility:boolean; Image:image; Size:variant; Direction:variant; Author name:text("Cameron Brown"); Role, Company:text("Cameron Brown"); Variant:variant; Image:image; Logo:boolean; Color:boolean(Default/Invert)
- **`Badge`** — props: Text:text("Designed for clarity")
- **`Eyebrow`** — props: Visibility:boolean; Text:text("Designed for clarity"); Style:variant
- **`Heading`** — props: Text:text("Build better experiences"); Style:variant; Tag:headingTag
- **`Label`** — props: Content:text("Customers satisfaction")
- **`Label / With Divider`** — props: Divider:boolean; Divider position:variant; Title:text("Build better experiences"); Title size:variant; Description:text
- **`Paragraph`** — props: Text:text; Size:variant
- **`Paragraph With Heading Style`** — props: Content:text("Build better experiences"); Size:variant; Bottom space:boolean(Default/None)
- **`Quote`** — props: Quote:text; Size:variant
- **`Rich Text`** — props: Text:richText; Color:variant
- **`Subheading`** — props: Visibility:boolean; Text:text

### Blocks/CTA (9)

Scaffolds (have slots):
- **`Button Group / Primary, Secondary`** — slots: `Slot` — props: Visibility:boolean; Direction:variant; Alignment:variant
- **`Form / Webflow / Lead`** — slots: `Slot` — props: Type:variant; Visibility:boolean; Style:variant; Title:text; Tag:headingTag; Form ID:id; Visibility:boolean; Type:variant; Size:variant; Label:text("First Name"); Visibility:boolean; Type:variant; Size:variant; Label:text("Last name"); Visibility:boolean; Type:variant; Size:variant; Label:text("Email Address"); Visibility:boolean; Type:variant; Size:variant; Label:text("Phone Number"); Visibility:boolean; Type:variant; Size:variant; Label:text("Project type"); Visibility:boolean; Label:text("I agree to the"); Privacy policy:boolean; Link to privacy policy page:link; Position:variant; Text:string; Loading state text:string

Leaf components:
- **`Button / Primary`** — props: Visibility:boolean; Link:link; Label:text("Get started"); Style:variant; Size:variant; Visibility:boolean; Side:variant
- **`Button / Secondary`** — props: Visibility:boolean; Link:link; Label:text("Get started"); Size:variant; Style:variant; Visibility:boolean; Side:variant
- **`Footer Link`** — props: Text:text("Solutions"); Link:link
- **`Form / Email`** — props: Visibility:boolean; Layout:variant; Visibility:boolean(Visible/Hiddent); Text:text
- **`Form / Lead`** — props: Style:variant; Visibility:boolean; Style:variant; Title:text; Tag:headingTag
- **`Link / Primary`** — props: Visibility:boolean; Link:link; Label:text("Get started"); Size:variant; Style:variant; Visibility:boolean; Side:variant
- **`Link / Secondary`** — props: Visibility:boolean; Link:link; Label:text("Get started"); Size:variant; Style:variant; Visibility:boolean; Side:variant

### Blocks/Media (12)

Leaf components:
- **`Avatar`** — props: Visibility:boolean; Image:image; Size:variant
- **`Avatar / Full Width`** — props: Visibility:boolean; Image:image; Size:variant
- **`Company Logo`** — props: Variant:variant; Interactivity:boolean(Interactive/Static); Brand name:text("Brand"); Color scheme:boolean(On light/On dark)
- **`Icon`** — props: Visibility:boolean; Symbol:variant; Style:variant; Size:variant
- **`Icon / Facebook`** — props: Link:link
- **`Icon / Instagram`** — props: Link:link
- **`Icon / LinkedIn`** — props: Link:link
- **`Icon / Phosphor`** — props: Symbol:string; Color:variant; Size:variant; Style:variant
- **`Icon / X`** — props: Link:link
- **`Icon / YouTube`** — props: Link:link
- **`Image`** — props: Visibility:boolean; Image:image; Alt Text:altText; Aspect ratio:variant; Radius:boolean(Default/None); Interactivity:boolean(Interactive/Static); Screenreader text:text("Scale"); Link:link
- **`Logo`** — props: Image:image; Alt Text:altText; Color:boolean(Default/Invert); Size:variant

### Blocks/Content (15)

Scaffolds (have slots):
- **`Card / Left With Icon`** — slots: `Slot` — props: Style:variant; Interactivity:boolean(Interactive/Static); Aria label:text("Get started"); Link:link; Visibility:boolean; Style:variant; Align horizontal:variant
- **`Card / Wrapper`** — slots: `Slot` — props: Variant:variant; Interaction:boolean(Interactive/Static); Link:link
- **`Header`** — slots: `Slot` — props: Align:variant; Space bottom:boolean(Auto/None)
- **`Header / Split`** — slots: `Slot 2`, `Slot` — props: Sapce bottom:boolean(Default/None)

Leaf components:
- **`Author Info / Large Image`** — props: Layout:variant; Visibility:boolean; Image:image; Size:variant; Direction:variant; Author name:text("Cameron Brown"); Role, Company:text("Cameron Brown"); Variant:variant; Image:image; Logo:boolean
- **`Author Info / Name, Role`** — props: Direction:variant; Name:text("Cameron Brown"); Role, Company:text("Cameron Brown")
- **`Card / Overlay`** — props: Photo:image; Animation:boolean(Animated/Static); Visibility:boolean; Image:image; Alt Text:altText; Inverse:variant; Name:text("Cameron Brown"); Job title:text("Product designer"); Description visibility:boolean; Description:text; Visibility:boolean; Style:variant; Icon:boolean; Text:text("Learn more"); Link:link; Color:boolean(Default/Inverse)
- **`Card / Stack / Team `** — props: Layout:variant; Photo:image; Author name:text("Cameron Brown"); Role, Company:text("Cameron Brown"); Visibility:boolean; Variant:variant; Image:image; Interaction:boolean(Interactive/Static); Link:link; Size:variant
- **`Card / Team`** — props: Style:variant; Photo:image; Author name:text("Cameron Brown"); Role, Company:text("Cameron Brown"); Visibility:boolean; Variant:variant; Image:image; Interaction:boolean(Interactive/Static); Link:link; Layout:variant; Size:variant
- **`Content Block / With Icon`** — props: Symbol:variant; Style:variant; Size:variant; Position:variant; Title style:variant; Title:text("Build better experience"); Title Tag:headingTag; Text:richText
- **`Event / Details`** — props: Date:text("10 Feb 2024"); Location:text("Location"); Speaker:text("Speakers"); Space top:variant
- **`Metrics / Card`** — props: Style:variant; Align:boolean(Left/Center); Size:variant; Number:text("300%"); Description:text("Customers satisfaction")
- **`Metrics / Content Block`** — props: Type:variant; Align:boolean(Left/Center); Size:variant; Number:text("300%"); Description:text("Customers satisfaction")
- **`Testimonial / Split`** — props: Media Position:variant; Image:image; Text:text; Align:variant; Text size:variant; Text direction:variant; Author name:text("Cameron Brown"); Role, Company name:text("Cameron Brown"); Position:boolean(Top/Bottom); Logo:boolean; Color inverse:variant; Image:image; Visibility:boolean; Avatar Size:variant; Headshot:image; Color:boolean(Default/Invert)
- **`Testimonial / Stack`** — props: Quote:text; Size:variant; Align:variant; Text direction:variant; Author name:text("Cameron Brown"); Role, Company:text("Cameron Brown"); Position:boolean(Top/Bottom); Logo:boolean; Color inverse:variant; Image:image; Visibility:boolean; Avatar Size:variant; Headshot:image; Color:boolean(Default/Invert)

### Utility (18)

Leaf components:
- **`Utility / Align / Horizontal`** — props: Variant:variant
- **`Utility / Align / Horizontal / Left Center Right`** — props: Align horizontal:variant
- **`Utility / Align / Vertical`** — props: Variant:variant
- **`Utility / Container Width`** — props: Variant:variant
- **`Utility / Container Width / Variant`** — props: Container width:variant
- **`Utility / Field Type`** — props: Variant:variant
- **`Utility / Gap`** — props: Variant:variant
- **`Utility / Icon Style`** — props: Variant:variant
- **`Utility / Logos Bar Layout`** — props: Variant:variant
- **`Utility / Order / First`** — props: Variant:variant
- **`Utility / Order / First Last`** — props: Variant:variant; Position:boolean(Top/Bottom)
- **`Utility / Overlay`** — props: Overlay:variant; Visibility:boolean
- **`Utility / Overlay filter blur`** — props: Blur:variant
- **`Utility / Padding / Section`** — props: Variant:variant
- **`Utility / Size / S, M, L`** — props: Variant:variant
- **`Utility / Size / S, M, L / Dev`** — props: Variant:variant
- **`Utility / State / Animated`** — props: Animation:boolean(Animated/Static)
- **`Utility / Sticky Nav`** — props: Variant:variant

### FlowKit (2)

Leaf components:
- **`FlowKit Brand Fonts`** — (no props)
- **`FlowKit Icons — Phosphor`** — (no props)

### (ungrouped) (1)

Leaf components:
- **`3 cards`** — props: Columns:variant; Gap size:variant; Type:variant; Align:boolean(Left/Center); Number:text("74%"); Description:text; Type:variant; Align:boolean(Left/Center); Size:variant; Number:text("3.1×"); Description:text; Type:variant; Align:boolean(Left/Center); Number:text("41%"); Description:text

## Variable collections (the token system)

Layering: **Brand colors** (no modes) holds raw brand values; **Color schemes** / **Card color schemes** alias into it per surface mode (Primary=base, Secondary, Accent Primary, Accent Secondary, Accent Tertiary, Inverse); components and styles consume the scheme roles. Retargeting a brand = update Brand colors values + Typography fonts. Reference variables by `Collection > Group/Name`; never raw hex/px when a variable exists.

### Brand colors (49 variables — no modes)

- `Core Accent/Accent Primary` (color) = #2303fc
- `Core Accent/Accent Primary Hover` (color) = #1e382c
- `Core Accent/Accent Secondary` (color) = #1d0a9e
- `Core Accent/Accent Secondary Hover` (color) = #365849
- `Core Accent/Accent Tertiary` (color) = hsla(142.49999999999991, 11.43%, 86.27%, 1.00)
- `Core Accent/Accent Tertiary Hover` (color) = hsla(142.49999999999991, 7.00%, 78.42%, 1.00)
- `Core Neutral/Neutral Primary` (color) = #ffffff
- `Core Neutral/Neutral Secondary` (color) = #f0eeeb
- `Core Neutral/Neutral Inverse` (color) = #000000
- `Core Text Color/Text Primary` (color) = #000000
- `Core Text Color/Text On Secondary` (color) = #111111
- `Core Text Color/Text On Accent Primary` (color) = #ffffff
- `Core Text Color/Text On Accent Secondary` (color) = #ffffff
- `Core Text Color/Text On Accent Tertiary` (color) = hsla(0, 0.00%, 19.26%, 1.00)
- `Core Text Color/Text On Inverse` (color) = hsla(0, 0.00%, 100.00%, 1.00)
- `Current Tint/Current` (color) = custom: `color-mix(in srgb, currentColor 100%, transparent)`
- `Current Tint/Current A80` (color) = custom: `color-mix(in srgb, currentColor 80%, transparent)`
- `Current Tint/Current A70` (color) = custom: `color-mix(in srgb, currentColor 70%, transparent)`
- `Current Tint/Current A60` (color) = custom: `color-mix(in srgb, currentColor 60%, transparent)`
- `Current Tint/Current A50` (color) = custom: `color-mix(in srgb, currentColor 50%, transparent)`
- `Current Tint/Current A40` (color) = custom: `color-mix(in srgb, currentColor 40%, transparent)`
- `Current Tint/Current A30` (color) = custom: `color-mix(in srgb, currentColor 30%, transparent)`
- `Current Tint/Current A20` (color) = custom: `color-mix(in srgb, currentColor 20%, transparent)`
- `Current Tint/Current A10` (color) = custom: `color-mix(in srgb, currentColor 10%, transparent)`
- `Current Tint/Current A05` (color) = custom: `color-mix(in srgb, currentColor 5%, transparent)`
- `Core Tint/Accent Primary A10` (color) = custom: `color-mix(in srgb, var(--_brand-colors---core-accent--accent-primary) 10%, transparent)`
- `Core Tint/Accent Primary A20` (color) = custom: `color-mix(in srgb, var(--_brand-colors---core-accent--accent-primary) 20%, transparent)`
- `Core Tint/Accent Primary A90` (color) = custom: `color-mix(in srgb, var(--_brand-colors---core-accent--accent-primary) 90%, transparent)`
- `Neutral Tint/Neutral Primary A10` (color) = rgba(249, 248, 246, 0.1)
- `Neutral Tint/Neutral Primary A20` (color) = #f9f8f633
- `Neutral Tint/Neutral Primary A30` (color) = #f9f8f64d
- `Neutral Tint/Neutral Primary A40` (color) = #f9f8f666
- `Neutral Tint/Neutral Primary A50` (color) = #f9f8f680
- `Neutral Tint/Neutral Primary A60` (color) = #f9f8f699
- `Neutral Tint/Neutral Primary A70` (color) = #f9f8f6b3
- `Neutral Tint/Neutral Primary A80` (color) = #f9f8f6cc
- `Neutral Tint/Neutral Primary A90` (color) = #f9f8f6e6
- `Neutral Tint/Neutral Inverse A10` (color) = #1111111a
- `Neutral Tint/Neutral Inverse A20` (color) = #11111133
- `Neutral Tint/Neutral Inverse A30` (color) = #1111114d
- `Neutral Tint/Neutral Inverse A40` (color) = #11111166
- `Neutral Tint/Neutral Inverse A50` (color) = #11111180
- `Neutral Tint/Neutral Inverse A60` (color) = #11111199
- `Neutral Tint/Neutral Inverse A70` (color) = #111111b3
- `Neutral Tint/Neutral Inverse A80` (color) = #111111cc
- `Neutral Tint/Neutral Inverse A90` (color) = #111111e6
- `Misc/Overlay` (color) = custom: `color-mix(in oklab, var(--_brand-colors---core-accent--accent-primary) 45%, black)`
- `Misc/Gradient` (color) = custom: `color-mix(in oklab, var(--button--button-primary-bg) 20%, rgb(255 255 255 / 0.2))`
- `Misc/Error alert` (color) = #e51520

### Color schemes (34 variables — modes: base, Secondary, Accent Primary, Accent Secondary, Accent Tertiary, Inverse)

- `Background Color/Background` (color) = → Brand colors > Core Neutral/Neutral Primary | Secondary: → Brand colors > Core Neutral/Neutral Secondary; Accent Primary: → Brand colors > Core Accent/Accent Primary; Accent Secondary: → Brand colors > Core Accent/Accent Secondary; Accent Tertiary: → Brand colors > Core Accent/Accent Tertiary; Inverse: → Brand colors > Core Neutral/Neutral Inverse
- `Text Color/Text Primary` (color) = → Brand colors > Core Text Color/Text Primary | Secondary: #000000; Accent Primary: #ffffff; Accent Secondary: #ffffff; Accent Tertiary: #000000; Inverse: #ffffff
- `Text Color/Text Secondary` (color) = custom: `color-mix(in srgb, var(--text-color--text-primary) 70%, white)` | Secondary: #545454; Accent Primary: #bfbfbf; Accent Secondary: #bfbfbf; Accent Tertiary: #000000; Inverse: #bfbfbf
- `Text Color/Text Accent` (color) = → Brand colors > Core Accent/Accent Primary | Secondary: #2303fc; Accent Primary: #ffffff; Accent Secondary: #ffffff; Accent Tertiary: #2303fc; Inverse: #ffffff
- `Text Color/Text Accent Hover` (color) = → Brand colors > Core Accent/Accent Primary Hover | Secondary: #2107cf; Accent Primary: #ffffff; Accent Secondary: #ffffff; Accent Tertiary: #2107cf; Inverse: #ffffff
- `Text Color/Text On Overlay` (color) = → Brand colors > Core Neutral/Neutral Primary | Secondary: #000000; Accent Primary: #ffffff; Accent Secondary: #ffffff; Accent Tertiary: #000000; Inverse: #ffffff
- `Border Color/Border Primary` (color) = → Brand colors > Current Tint/Current A50
- `Border Color/Border Secondary` (color) = → Brand colors > Current Tint/Current A30
- `Border Color/Border Accent` (color) = → Brand colors > Core Tint/Accent Primary A90
- `Blockquote/Blockquote BG` (color) = transparent
- `Blockquote/Blockquote Text` (color) = → Color schemes > Text Color/Text Primary
- `Blockquote/Blockquote Border` (color) = → Color schemes > Text Color/Text Primary
- `Button/Button Primary - BG` (color) = → Brand colors > Core Accent/Accent Primary | Accent Primary: → Brand colors > Neutral Tint/Neutral Primary A90; Accent Secondary: → Brand colors > Neutral Tint/Neutral Primary A80; Inverse: → Brand colors > Core Neutral/Neutral Secondary
- `Button/Button Primary - BG Hover` (color) = → Brand colors > Core Accent/Accent Primary Hover | Accent Primary: → Brand colors > Core Neutral/Neutral Primary; Accent Secondary: → Brand colors > Core Neutral/Neutral Primary; Inverse: → Brand colors > Core Neutral/Neutral Primary
- `Button/Button Primary - Text` (color) = → Brand colors > Core Text Color/Text On Accent Primary | Accent Primary: → Brand colors > Neutral Tint/Neutral Inverse A90; Accent Secondary: → Brand colors > Neutral Tint/Neutral Inverse A80; Inverse: → Brand colors > Core Text Color/Text Primary
- `Button/Button Primary - Border` (color) = transparent
- `Button/Button Primary - Border Hover` (color) = transparent
- `Button/Button Secondary - BG` (color) = → Brand colors > Core Tint/Accent Primary A10 | Accent Primary: → Brand colors > Neutral Tint/Neutral Primary A30; Accent Secondary: → Brand colors > Neutral Tint/Neutral Primary A30; Inverse: → Brand colors > Neutral Tint/Neutral Primary A30
- `Button/Button Secondary - BG Hover` (color) = → Brand colors > Core Tint/Accent Primary A20 | Accent Primary: → Brand colors > Neutral Tint/Neutral Primary A10; Accent Secondary: → Brand colors > Neutral Tint/Neutral Primary A60; Inverse: → Brand colors > Neutral Tint/Neutral Primary A10
- `Button/Button Secondary - Text` (color) = → Color schemes > Text Color/Text Primary | Accent Tertiary: → Color schemes > Text Link/Link Primary
- `Button/Button Secondary - Border` (color) = transparent
- `Button/Button Secondary - Border Hover` (color) = transparent
- `Input/Input - BG` (color) = → Brand colors > Core Neutral/Neutral Primary | Accent Primary: → Brand colors > Neutral Tint/Neutral Primary A10; Accent Secondary: → Brand colors > Neutral Tint/Neutral Primary A10; Inverse: → Brand colors > Neutral Tint/Neutral Primary A10
- `Input/Input - BG Hover` (color) = → Brand colors > Core Neutral/Neutral Secondary | Accent Primary: → Brand colors > Neutral Tint/Neutral Primary A20; Accent Secondary: → Brand colors > Neutral Tint/Neutral Primary A20; Inverse: → Brand colors > Neutral Tint/Neutral Primary A20
- `Input/Input - Text` (color) = → Color schemes > Text Color/Text Primary
- `Input/Input - Text Placeholder` (color) = custom: `color-mix(in srgb, var(--text-color--text-primary) 20%, transparent)`
- `Input/Input - Border` (color) = → Color schemes > Border Color/Border Primary
- `Input/Input - Border Hover` (color) = → Color schemes > Border Color/Border Primary
- `Input/Input Control` (color) = → Color schemes > Text Color/Text Primary
- `Nav Link/Nav Link Primary` (color) = → Color schemes > Text Color/Text Primary
- `Text Link/Link Primary` (color) = → Brand colors > Core Accent/Accent Primary | Accent Primary: custom: `color-mix(in srgb, var(--_brand-colors---core-text-color--text-on-accent-primary) 70%, transparent)`; Accent Secondary: custom: `color-mix(in srgb, var(--_brand-colors---core-text-color--text-on-accent-secondary) 70%, transparent)`; Accent Tertiary: custom: `color-mix(in srgb, var(--_brand-colors---core-text-color--text-on-accent-tertiary) 70%, transparent)`; Inverse: custom: `color-mix(in srgb, var(--_brand-colors---core-text-color--text-on-inverse) 70%, transparent)`
- `Text Link/Link Primary Hover` (color) = → Brand colors > Core Accent/Accent Primary Hover | Accent Primary: → Brand colors > Core Text Color/Text On Accent Primary; Accent Secondary: → Brand colors > Core Text Color/Text On Accent Secondary; Accent Tertiary: → Brand colors > Core Text Color/Text On Accent Tertiary; Inverse: → Brand colors > Core Text Color/Text On Inverse
- `Text Link/Link Secondary` (color) = custom: `color-mix(in srgb, var(--text-color--text-primary) 70%, white)` | Secondary: custom: `color-mix(in srgb, var(--_brand-colors---core-text-color--text-on-secondary) 70%, white)`; Accent Primary: custom: `color-mix(in srgb, var(--_brand-colors---core-text-color--text-on-accent-primary) 70%, white)`; Accent Secondary: custom: `color-mix(in srgb, var(--_brand-colors---core-text-color--text-on-accent-secondary) 70%, white)`; Accent Tertiary: custom: `color-mix(in srgb, var(--_brand-colors---core-text-color--text-on-accent-tertiary) 70%, white)`; Inverse: custom: `color-mix(in srgb, var(--_brand-colors---core-text-color--text-on-inverse) 70%, white)`
- `Text Link/Link Secondary Hover` (color) = → Brand colors > Core Text Color/Text Primary | Secondary: → Color schemes > Text Color/Text Primary; Accent Primary: → Color schemes > Text Color/Text Primary; Accent Secondary: → Color schemes > Text Color/Text Primary; Accent Tertiary: → Color schemes > Text Color/Text Primary; Inverse: → Color schemes > Text Color/Text Primary

### Card color schemes (4 variables — modes: base, Secondary, Accent Primary, Accent Secondary, Accent Tertiary, Inverse)

- `Card/Card Primary - BG` (color) = → Brand colors > Core Neutral/Neutral Primary | Secondary: → Brand colors > Core Neutral/Neutral Secondary; Accent Primary: → Brand colors > Core Accent/Accent Primary; Accent Secondary: → Brand colors > Core Accent/Accent Secondary; Accent Tertiary: → Brand colors > Core Accent/Accent Tertiary; Inverse: → Brand colors > Core Neutral/Neutral Inverse
- `Card/Card Primary - BG Hover` (color) = → Brand colors > Core Neutral/Neutral Secondary | Accent Primary: → Brand colors > Core Accent/Accent Primary Hover; Accent Secondary: → Brand colors > Core Accent/Accent Secondary Hover; Accent Tertiary: → Brand colors > Core Accent/Accent Tertiary Hover
- `Card/Card Primary - Text` (color) = → Color schemes > Text Color/Text Primary | Accent Primary: → Brand colors > Core Text Color/Text On Accent Primary; Accent Secondary: → Brand colors > Core Text Color/Text On Accent Secondary; Accent Tertiary: → Brand colors > Core Text Color/Text On Accent Tertiary; Inverse: → Brand colors > Core Text Color/Text On Inverse
- `Card/Card Primary - Border` (color) = → Color schemes > Border Color/Border Secondary

### Typography (79 variables — modes: base, Tablet, Mobile (L), Mobile)

- `Font/Heading Font` (fontfamily) = sohne-var
- `Font/Body Font` (fontfamily) = sohne-var
- `Font/Button Font` (fontfamily) = sohne-var
- `Base Typography/Base Font` (fontfamily) = → Typography > Font/Body Font
- `Base Typography/Base Font Size` (size) = 1rem
- `Base Typography/Base Font Weight` (number) = 400
- `Base Typography/Base Font Weight Bold` (number) = 600
- `Base Typography/Base Letter Spacing` (size) = 0em
- `Base Typography/Base Line Height` (size) = 1.6em
- `Base Typography/Base Margin Bottom` (size) = 0.75em
- `H0 Heading/H0 Size` (size) = 3.5rem
- `H0 Heading/H0 Letter Spacing` (size) = -0.0875rem
- `H0 Heading/H0 Line Height` (size) = 1.03em
- `H0 Heading/H0 Weight` (number) = 300
- `H0 Heading/H0 Margin Bottom` (size) = 0.5em
- `H1 Heading/H1 Size` (size) = 3rem
- `H1 Heading/H1 Letter Spacing` (size) = -0.06rem
- `H1 Heading/H1 Line Height` (size) = 1.03em
- `H1 Heading/H1 Weight` (number) = 300
- `H1 Heading/H1 Margin Bottom` (size) = 0.5em
- `H2 Heading/H2 Size` (size) = 2.75rem
- `H2 Heading/H2 Letter Spacing` (size) = -0.055rem
- `H2 Heading/H2 Line Height` (size) = 1.15em
- `H2 Heading/H2 Weight` (number) = 300
- `H2 Heading/H2 Margin Bottom` (size) = 0.5em
- `H3 Heading/H3 Size` (size) = 2rem
- `H3 Heading/H3 Letter Spacing` (size) = -0.04rem
- `H3 Heading/H3 Line Height` (size) = 1.1em
- `H3 Heading/H3 Weight` (number) = 300
- `H3 Heading/H3 Margin Bottom` (size) = 0.5em
- `H4 Heading/H4 Size` (size) = 1.625rem
- `H4 Heading/H4 Letter Spacing` (size) = -0.0163rem
- `H4 Heading/H4 Line Height` (size) = 1.12em
- `H4 Heading/H4 Weight` (number) = 300
- `H4 Heading/H4 Margin Bottom` (size) = 0.5em
- `H5 Heading/H5 Size` (size) = 1.375rem
- `H5 Heading/H5 Letter Spacing` (size) = -0.0138rem
- `H5 Heading/H5 Line Height` (size) = 1.1em
- `H5 Heading/H5 Weight` (number) = 300
- `H5 Heading/H5 Margin Bottom` (size) = 0.5em
- `H6 Heading/H6 Size` (size) = 1.1875rem
- `H6 Heading/H6 Letter Spacing` (size) = -0.0138rem
- `H6 Heading/H6 Line Height` (size) = 1.1em
- `H6 Heading/H6 Weight` (number) = 300
- `H6 Heading/H6 Margin Bottom` (size) = 0.5em
- `Text SM/SM Text Size` (size) = 0.875rem
- `Text SM/SM Text Letter Spacing` (size) = 0em
- `Text SM/SM Text Line Height` (size) = 1.6em
- `Text/Text Size` (size) = 1rem
- `Text/Text Letter Spacing` (size) = 0em
- `Text/Text Line Height` (size) = 1.5em
- `Text LG/LG Text Size` (size) = 1.25rem | Mobile (L): 1.1rem; Mobile: 1.1rem
- `Text LG/LG Text Letter Spacing` (size) = 0em
- `Text LG/LG Text Line Height` (size) = 1.6em
- `Text XL/XL Text Size` (size) = 1.5rem | Tablet: 1.4rem; Mobile (L): 1.3rem
- `Text XL/XL Text Letter Spacing` (size) = 0em
- `Text XL/XL Text Line Height` (size) = 1.6em
- `Text XXL/XXL Text Size` (size) = 2rem | Tablet: 1.8rem; Mobile (L): 1.6rem; Mobile: 1.4rem
- `Text XXL/XXL Text Letter Spacing` (size) = 0em
- `Text XXL/XXL Text Line Height` (size) = 1.4em
- `Blockquote/Blockquote Radius` (size) = 0px
- `Blockquote/Blockquote Border Width` (size) = 3px
- `Blockquote/Blockquote Font` (fontfamily) = → Typography > Font/Body Font
- `Blockquote/Blockquote Size` (size) = custom: `clamp(1.125rem, 1.5vw + 0.25rem, 1.5rem)`
- `Blockquote/Blockquote Letter Spacing` (size) = 0.01em
- `Blockquote/Blockquote Line Height` (size) = 1.5em
- `Blockquote/Blockquote Padding Vertical` (size) = → Sizes > Spacing/0.75x
- `Blockquote/Blockquote Padding Horizontal` (size) = → Sizes > Spacing/1.25x | Mobile (L): → Sizes > Spacing/1x
- `Eyebrow/Eyebrow Font` (fontfamily) = → Typography > Font/Body Font
- `Eyebrow/Eyebrow Size` (size) = 0.8125rem
- `Eyebrow/Eyebrow Letter Spacing` (size) = 0.08em
- `Eyebrow/Eyebrow Line Height` (size) = 1.5em
- `Button/Button Font` (fontfamily) = sohne-var
- `Tag/Tag Size` (size) = 0.75rem
- `size` (size) = 0px
- `Fluid scale/H1 Min` (size) = 3.025rem
- `Fluid scale/H1 Max` (size) = 5.5rem
- `Fluid scale/Scale Ratio` (number) = 1.25
- `Fluid scale/Fluid VW` (number) = 2.5

### Sizes (60 variables — modes: base, Tablet, Mobile (L), Mobile)

- `Radius/SM Radius` (size) = 0.25rem
- `Radius/MD Radius` (size) = 0.5rem
- `Radius/LG Radius` (size) = 0.75rem
- `Radius/XL Radius` (size) = 1rem
- `Radius/Round` (size) = 100vw
- `Spacing/0.25x` (size) = 0.25rem
- `Spacing/0.5x` (size) = 0.5rem
- `Spacing/0.75x` (size) = 0.75rem
- `Spacing/1x` (size) = 1rem
- `Spacing/1.25x` (size) = 1.25rem
- `Spacing/1.5x` (size) = 1.5rem
- `Spacing/1.75x` (size) = 1.75rem
- `Spacing/2x` (size) = 2rem
- `Spacing/3x` (size) = 3rem
- `Spacing/4x` (size) = 4rem
- `Spacing/5x` (size) = 5rem
- `Spacing/6x` (size) = 6rem
- `Spacing/7x` (size) = 7rem
- `Spacing/8x` (size) = 8rem
- `Gap/XXS Gap` (size) = → Sizes > Spacing/0.5x
- `Gap/XS Gap` (size) = → Sizes > Spacing/1x
- `Gap/SM Gap` (size) = → Sizes > Spacing/2x
- `Gap/MD Gap` (size) = → Sizes > Spacing/3x
- `Gap/LG Gap` (size) = → Sizes > Spacing/4x
- `Gap/XL Gap` (size) = → Sizes > Spacing/5x
- `Gap/XXL Gap` (size) = → Sizes > Spacing/6x
- `Image/Image Radius` (size) = 0.375rem
- `Button/Button Radius` (size) = 0.25rem
- `Button/Button Padding Vertical` (size) = 0.75rem
- `Button/Button Padding Horizontal` (size) = 1.25rem
- `Button/Button Size` (size) = 1rem
- `Input/Input Radius` (size) = 0.5rem
- `Input/Input Padding Vertical` (size) = 0.75rem
- `Input/Input Padding Horizontal` (size) = 1rem
- `Card/Card Radius` (size) = 0.25rem
- `Card/Card Padding SM` (size) = 0.25rem
- `Card/Card Padding` (size) = 0.25rem
- `Container/Container Width` (size) = 90rem
- `Container/Container SM Width` (size) = 48rem
- `Container/Container LG Width` (size) = 80rem
- `Container/Container Padding Horizontal` (size) = custom: `calc(1rem + 2vw)`
- `Nav/Nav Height` (size) = 4rem
- `Footer/Logo Height` (size) = 1.5rem
- `Section/Section Padding Vertical` (size) = 6rem
- `Tag/Tag Radius` (size) = → Sizes > Radius/SM Radius
- `Tag/Tag Padding Vertical` (size) = → Sizes > Spacing/0.25x
- `Tag/Tag Padding Horizontal` (size) = → Sizes > Spacing/0.5x
- `Slider/Slider gap SM` (size) = → Sizes > Spacing/1x
- `Slider/5 slides` (number) = 5 | Tablet: 3; Mobile (L): 2; Mobile: 1
- `Slider/4 slides` (number) = 4 | Tablet: 3; Mobile (L): 2; Mobile: 1
- `Slider/3 slides` (number) = 3 | Tablet: 2; Mobile (L): 2; Mobile: 1
- `Slider/2 slides` (number) = 2 | Mobile (L): 1; Mobile: 1
- `Slider/1.5 slides` (number) = 1.5 | Mobile: 1
- `Slider/Navigation` (size) = → Sizes > Spacing/0.75x
- `Width/XXS` (size) = 12rem
- `Width / XS` (size) = 25rem
- `Width/SM` (size) = 35rem
- `Width / MD` (size) = 40rem
- `Width / LG` (size) = 50rem
- `Width / XL` (size) = 60rem

### Grid gap (3 variables — modes: base, Small, Medium, Large, XLarge)

- `Gap` (size) = 0rem | Small: → Sizes > Gap/XXS Gap; Medium: → Sizes > Gap/XS Gap; Large: → Sizes > Gap/SM Gap; XLarge: → Sizes > Gap/LG Gap
- `Vertical space` (size) = 0px | Small: → Sizes > Gap/XS Gap; Medium: → Sizes > Gap/SM Gap; Large: → Sizes > Gap/LG Gap; XLarge: → Sizes > Gap/XL Gap
- `Horizontal space` (size) = → Sizes > Gap/SM Gap | Small: → Sizes > Gap/XS Gap; Medium: → Sizes > Gap/MD Gap; Large: → Sizes > Gap/LG Gap; XLarge: → Sizes > Gap/XL Gap

### Card (2 variables — modes: base, Card)

- `Card padding` (size) = 0.25rem
- `Radius` (size) = 0.25rem

### Width (3 variables — modes: base, Small, Medium, Large)

- `Width` (size) = custom: `100%` | Small: custom: `var(--_sizes---width--xxs)`; Medium: custom: `var(--_sizes---width--xs)`; Large: custom: `var(--_sizes---width--md)`
- `Header` (size) = custom: `100%` | Small: → Sizes > Width/SM; Medium: → Sizes > Width / MD; Large: → Sizes > Width / LG
- `Container` (size) = custom: `var(--_sizes---container--container-width)` | Small: → Sizes > Container/Container SM Width; Medium: → Sizes > Container/Container LG Width; Large: custom: `100%`

### Section padding (1 variables — modes: base, Small, None)

- `Section` (size) = → Sizes > Section/Section Padding Vertical | Small: custom: `calc(var(--_sizes---section--section-padding-vertical) / 2)`; None: 0rem

### Card padding (1 variables — modes: base, Medium, Large, XLarge)

- `Card padding` (size) = 0.25rem

### Shadows (10 variables — modes: base, None, Small, Medium, Large)

- `Shadow / X` (size) = 0px
- `Shadow / Y` (size) = 4px | None: 0px; Small: 2px; Large: 6px
- `Shadow / Blur` (size) = 8px | None: 0px; Small: 5px; Large: 12px
- `Shadow / Size` (size) = 0px
- `Shadow / Color` (color) = rgba(0, 0, 0, 0.08) | None: rgba(0, 0, 0, 0); Small: rgba(0, 0, 0, 0.06); Large: rgba(0, 0, 0, 0.12)
- `Shadow hover / X` (size) = 0px
- `Shadow hover / Y` (size) = 8px | None: 0px; Small: 4px; Large: 10px
- `Shadow hover / Blur` (size) = 16px | None: 0px; Small: 8px; Large: 20px
- `Shadow hover / Size` (size) = 0px
- `Shadow hover / Color` (color) = rgba(0, 0, 0, 0.10) | None: rgba(0, 0, 0, 0); Small: rgba(0, 0, 0, 0.08); Large: rgba(0, 0, 0, 0.14)

## Class naming conventions (existing, reuse these)

- Utilities `property_value` (`padding-bottom_medium`, `max-width_xlarge`, `radius_none`, `text-color_inverse`); state combos `is-*` (`is-y-center`, `is-small`); scheme combos `on-*` (`on-inverse`, `on-accent-tertiary`); gap utilities `gap-small`; responsive `tablet-1-col`, `mobile-l-vertical`, `hide_mobile`; prefixes `ix_` (interactions), `nav_`, `form_`/`wf-form_`, `ratio_`/`image-ratio_`. Don't invent a parallel convention.
