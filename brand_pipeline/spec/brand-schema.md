# brand-schema.md — `brand.yaml` schema (SPEC)

> Status: **design / for review**. This document specifies the canonical
> `brand.yaml` artifact and its rendered `brand.md` projection. It does **not**
> change any runtime. Token values, primitive/block usage, and the worked WoodWave
> example are real (sourced from `runs/woodwave/brand/*` and the shared contracts in
> `brand_pipeline/contracts/{primitives,blocks,scaffolds}.yaml`).

## 0. Where this sits — agent vocabulary, canonical vs rendered, render substrate

### 0.1 The pipeline and its agents (standard vocabulary)

```
Brand Extractor (pipeline)
   ├─ Layout Analyst      — skill `brand-layout-analyst`
   │                        extracts a first-pass brand.yaml, emits creation signals
   └─ Art Director        — skill `brand-art-director`
                            OWNS brand.yaml / brand.md + do[]/avoid[]/neverDo[]
                            + the signal loop (manual, confirm-before-promote)

DEFERRED (not built / not the current target):
   • Page Composer        — compose_page.py (assembles a whole page from brand.yaml)
   • Webflow Assembler     — webflow-library-aisb + Webflow MCP (live-site build)
```

### 0.2 Canonical vs rendered

```
brand.yaml   ── canonical, machine-authored, the single source of truth
   │
   │  render_brand_md(brand.yaml)  (pure projection, deterministic, no new facts)
   ▼
brand.md     ── human-readable projection. NEVER hand-edited.
```

- **`brand.yaml` is canonical.** Every rule, token, layout, contract-usage, and
  constraint lives here with provenance and confidence. The Layout Analyst seeds it;
  the Art Director consolidates into it.
- **`brand.md` is a rendered projection.** It is regenerated from `brand.yaml` by a
  pure function `render_brand_md(brand.yaml) -> brand.md`. It contains **no
  information that is not derivable from `brand.yaml`**.
- **Never hand-edit `brand.md`.** Edit `brand.yaml` (or file a signal — see
  `signal-loop.md`) and re-render. **(SIGN-OFF #1)** Drift between `brand.md` and
  `render_brand_md(brand.yaml)` is a **WARNING, not a build blocker**.

### 0.3 Render substrate (the agnostic contract)

**`brand.yaml` is library-AGNOSTIC.** Canonical nodes describe *intent* — archetype,
slot role, primitive/block contract, token semantics, responsive ladder, surface
intent — and never bake in substrate names. Substrates project the same intent:

- **Tailwind/shadcn renderer** (the build target **NOW**): intent → utility classes
  + shadcn markup, static HTML on a Tailwind CDN.
- **Webflow Assembler** (**DEFERRED**): intent → library components + variables.

Any substrate-specific identifiers (Webflow variable ids, collection/mode ids,
component ids) live ONLY in the **optional, non-canonical `targetMappings:`**
annotation block (§7) — consumed later by the deferred Webflow Assembler — never on
the canonical token/layout nodes.

## 1. Top-level keys

```yaml
version:          # schema version string, e.g. "2.0"
brand:            # identity block: name, sourceUrl, snapshot (one-paragraph thesis)
tokens:           # colors / type / spacing / surfaces → intent + value (library-AGNOSTIC)
surfaceGrammar:   # the surface role system + transition/nesting rules
buttons:          # measured ACTION-STYLE families (state matrices) — §10.2
navbar:           # extracted nav chrome: links/ctas + measured registers + presentation (§3 note)
footer:           # extracted footer chrome: columns/social + legal.text + measured registers (§10.3)
contracts:        # refs to the shared universal catalogs (primitives.yaml, blocks.yaml)
primitives:       # [] THIS brand's overrides/usage rules AGAINST the primitive contracts
blocks:           # [] THIS brand's overrides/usage rules AGAINST the block contracts
layouts:          # [] archetype instances extracted from real sections (slots → blocks/media)
compositionRules: # [] cross-cutting composition mechanics (overlap, stagger, z-order…)
do:               # [] positive prescriptions (affirmative house style)
avoid:            # [] soft discouragements (prefer-not, not absolute)
neverDo:          # [] hard prohibitions (absolute)
voice:            # ref to voice.md + inline locked dials (variance/motion/density)
recipePolicy:     # how sections are built (reuse-before-create, scaffold-first, theme-via-modes)
targetMappings:   # OPTIONAL, NON-CANONICAL. substrate-specific ids (Webflow) for the assembler
provenanceIndex:  # sectionId → source screenshot / url / DOM node (resolves provenance refs)
indexes:          # OPTIONAL refs to sibling artifacts this brand.yaml indexes (SIGN-OFF #6)
```

> `brand.yaml` is one file of a REQUIRED sibling set: `section-copy.yaml` (authored
> verbatim copy — schema in `spec/section-copy-schema.md`), `layout-library.yaml`
> (`layout-patterns.v1`, §4.4), curated `assets/` (logos included when observed), and
> the extraction `evidence/` bundle. §10 records the output contract the validator
> (`tools/extract/validate_brand_evidence.py`) enforces across the set.

## 2. The universal rule-entry envelope

**Every** leaf that expresses a *design decision* (not a raw token value) is wrapped
in this envelope so the self-education loop (`signal-loop.md`) can reason about it:

```yaml
<ruleKey>:
  value:        <any>            # the decision itself (string | number | object | enum)
  confidence:   high|medium|low  # evidence strength
  source:       creation|iteration|failure   # where this value came from
  scope:        design-language|one-off       # promoted rule vs single-instance exception
  changelog:                     # append-only audit trail
    - { ts: <iso8601>, action: created|updated|promoted|demoted|reverted,
        from: <prev value|null>, to: <new value>, by: creation|iteration|failure,
        signalId: <id|null>, note: <string> }
```

Field rules:

- `source` — `creation` (first-pass extraction by the Layout Analyst), `iteration`
  (human redirect), `failure` (build-failure fact).
- `scope` — `design-language` (promoted, governs all future sections) or `one-off`
  (single-instance exception; the **default landing scope** for any contradicting
  signal — apply once, do not promote, queue the question).
- `confidence` gates promotion (see `signal-loop.md`).
- `changelog` is append-only; never rewrite history.

Token *values* (raw hex/rem) do **not** carry the envelope individually — they carry
`provenance` + intent metadata in `tokens` (§3). The envelope is for *rules*
(`do[]`, `avoid[]`, `neverDo[]`, `compositionRules[]`, `surfaceGrammar`, dials, …).

## 3. `tokens` — intent + value, library-AGNOSTIC

Tokens record **semantic role + value + responsive ladder + surface intent** only.
They do **not** carry Webflow variable names/ids/modes — those move to
`targetMappings` (§7). A token name *is* its semantic role (`surface/primary`,
`text/on-inverse`, `display-hero`, `section-padding-light`).

> **Canonical tier (C14).** A brand whose type carries sized roles declares
> `meta.canonicalTier: {viewport, label, note}` at the TOP level — the measured
> breakpoint every canonical value (`sizeRem.base`, spacing `value:`) refers to.
> The measure stage samples the capture at a viewport ladder (default
> 1920/1440/960/375, `computed-styles.json tiers`, every block stamped with its
> tier); the authored ladders and per-role `tiers` stamps trace back to it.

```yaml
tokens:
  colors:
    <semanticRole>:                  # surface/primary, text/on-inverse, accent/highlight…
      value:        "<hex|rgba>"
      role:         "<short intent>" # e.g. "canvas background", "body text on dark"
      provenance:   [<sectionId>…]
  type:
    <roleName>:                      # display-hero, h1, h2, h3, eyebrow, body, control-text, …
      family:       "<font family>"
      sizeRem:      { base: …, tablet: …, mobileL: …, mobile: … }   # responsive ladder —
                                     # C14: ≥ 2 breakpoints per sized role, OR
      singleTierConfirmed: true      # measured constant across the tier ladder (explicit)
      tiers:                         # per-viewport MEASURED stamps (canonical-tier ladder,
        w1440: { px: …, source: computed|saved-css }   # measure stage `tiers` samples)
        w960:  { px: …, source: … }  # every stamp names the tier it was measured at
      lineHeight:   "<em|unitless>"
      weight:       <int>            # REQUIRED on EVERY tier — the measured computed font-weight
      letterSpacing:"<rem|em>"
      case:         uppercase|sentence|none
  spacing:
    <roleName>:                      # section-padding-light, module-gap-editorial, …
      value:        "<rem>"
      role:         "<short intent>"
      modeLadder:   { base: …, tablet: …, mobileL: …, mobile: … }   # responsive
    <role>-to-<role>:                # RELATIONAL LADDER (C15): named gaps BETWEEN content
      value:        "<rem>"          # roles — eyebrow-to-heading, heading-to-body,
      modeLadder:   { … }            # body-to-cta, … (or relationalLadder:
                                     # {notObserved: true, reason: …} when truly absent)
                                     # COMPLETENESS (C15, fid11): when the source's mined
                                     # CSS exposes relational spacing custom properties
                                     # (vars pairing two content roles — label/headline/
                                     # description/button "spacing" ladders — or row-gap/
                                     # column-gap rhythm vars), EVERY exposed rung must be
                                     # authored under its GENERIC canonical name:
                                     #   pair vars      → eyebrow-to-heading /
                                     #                    heading-to-body / body-to-cta
                                     #   row-gap var    → block-to-block (content-block
                                     #                    row rhythm)
                                     #   split col var  → column-to-column (split gutter)
                                     # Source var/selector names are PROVENANCE ONLY
                                     # (cite them in role:) — never token names. Rungs
                                     # ride the canonical tier; register swaps go in
                                     # modeLadder. CONSUMPTION: ladder-bearing brands
                                     # render header/anatomy stacks as NO-GAP columns
                                     # with per-pair margins (AS-48); uniform stack gap
                                     # is ONLY the no-ladder degrade. Optional companion
                                     # measures from the same ladder family (e.g.
                                     # body-measure — description column measure;
                                     # header-measure — bounded header-stack measure)
                                     # are authored as plain spacing roles.
    container-max:                   # measured content max-width (nav/footer cap)
      value:        "<rem>"
    container-span:                  # OPTIONAL measured outer-container LAW as one CSS
      value:        "min(<N>cqw, <cap>rem)"   # expression (from tier containerFacts:
                                     # fluid used-width fraction + wide-tier cap). When
                                     # authored, --content-measure rides it page-wide
                                     # (every section container centers this span);
                                     # else container-max, else the structural 86rem.
  surfaces:
    <surfaceRole>:                   # surface/primary, surface/inverse, …
      bg:           "<hex>"          # or token ref
      intent:       "<role>"         # e.g. "default canvas", "dark bookend band"
      textPrimary:  "<token ref>"
      textSecondary: "<token ref|null>" # OPTIONAL: this surface's measured secondary
                                     # (muted) ink. Declare it when the source's
                                     # secondary register on THIS surface is not the
                                     # global muted role — e.g. a photographic band
                                     # whose sub/eyebrow measured FULL-strength ink
                                     # (the art carries the contrast). Absent ⇒ the
                                     # global text/on-*-muted resolution applies.
      textAccent:   "<token ref|null>"
      provenance:   [<sectionId>…]
```

> **Typography weight — EVERY tier carries a measured `weight`.** `weight` is a
> first-class, REQUIRED field on **every** `tokens.type` tier — headings (`display-hero`,
> `h1`–`h3`, `counter-display`, `ghost-watermark`, `footer-sitemap-link`) **and** body /
> paragraph / `eyebrow` / `control-text` alike — never hand-set downstream. Brand
> EXTRACTION measures the source's real computed `font-weight` (the browser chrome
> extractor already records `fontWeight` for every measured chrome text role — nav link,
> utility link, cta, footer heading/link/social/legal — and the chrome bridge persists it
> verbatim under `navbar.measured`/`footer.measured`), and the layout-analyst seeds that
> numeric value onto the tier. Use a documented default of `400` (normal) **only** when the
> source genuinely declares no weight for that role. The composer reads these weights
> (`component_render.component_vars` → `--c-display-weight` / `--c-heading-weight`), so an
> unmeasured tier silently falls back to a guess — capture it.
>
> **Substrate projection.** The Tailwind/shadcn renderer maps each token's *intent*
> to classes (e.g. `surface/inverse` → a dark `bg-*` + scheme utilities). The future
> Webflow Assembler maps the SAME intent to a variable + Color-schemes mode using the
> ids recorded in `targetMappings`. Canonical tokens never name either substrate.

> **Chrome PRESENTATION devices are brand declarations, never renderer defaults**
> (nav-fix 2026-07). Casing, decorative separators, chrome surfaces, and chrome
> interactions all derive from the brand's own data, degrading to NEUTRAL when silent:
>
> - `tokens.type.<tier>.case` — the register's measured case (`uppercase` / `sentence`
>   / `title` / `none`). ALL rendered casing (headings, eyebrows, controls, nav links,
>   footer links, gallery specimens) rides the generated `--case-<tier>` variables;
>   shared CSS never hardcodes `text-transform`. A silent tier renders as authored
>   (`none`), and content passes through Python untransformed (no `.upper()` styling).
> - `tokens.type.<tier>.prefix` — OPTIONAL decorative text device for the register
>   (e.g. an eyebrow slash prefix observed on the live site). Consumed by specimen /
>   preview surfaces; composed section copy authors its own prefixes. Silent = none.
> - `navbar.separator` / `footer.separator` — the decorative inter-link separator
>   GLYPH observed in the brand's chrome (e.g. `"/"`). Silent = links separated by
>   spacing alone; a glyph is never inherited from another brand.
> - `navbar.surface.bg` — the measured bar color. The composer resolves it to one of
>   the brand's OWN `tokens.surfaces` roles by nearest RGB (`nav_surface_role`, same
>   discipline as the AS-35 footer resolution); a TRANSPARENT/unmeasured bar keeps the
>   opening section's surface (the extracted nav sits over what it overlaps).
> - `navbar.measured.link.hoverBg` / `.hoverRadius` — the measured nav-link hover
>   WASH (pill/underlay). Emitted as `--chrome-nav-link-hover-*` layer-1 tokens and
>   rendered only when extracted; hover-less brands keep the default link interaction.
> - The nav CTA renders through the same law-first `cta-shape` dispatch as every other
>   action (`render_button`): a filled-primary brand gets its measured pill in the nav,
>   a typographic brand keeps the ink arrow link. WHICH primary item is the action is
>   itself evidence, never a vocabulary guess: an explicit `navbar.ctas[]` entry wins,
>   else a `navbar.links[].style` filled-pill marker, else `navbar.measured.cta`
>   promotes the LAST primary item; a brand declaring none renders links only.

> **Chrome DEPTH facts (fid4 2026-07 — mega-menus + footer hierarchy; validator C16).**
> All optional; every requirement below triggers off the brand's OWN captured evidence
> (observed-but-incomplete is a C16 error; a brand whose chrome lacks the pattern owes
> nothing and renders exactly as before). Asset refs (`asset:`) are brand-dir-relative
> paths that MUST exist on disk — artwork binds only when actually harvested.
>
> - `navbar.primary[].menu` — the captured MEGA-MENU for one top-level item:
>   `columns: [{heading, area: main|aside, links: [{label, href, description?,
>   descriptionOnHover?, icon?: {kind: svg|img|mask|bg, asset?, size?}}]}]` plus an
>   optional right-side object `card: {title, href, body?, groupHeading?, area: aside,
>   image?: {asset, alt?}, cta?: {label, href}}`. Column groups are heading+links
>   units in source order; `area: aside` marks the bordered right rail.
>   `descriptionOnHover: true` records a description the source reveals on hover
>   (`grid-template-rows` 0fr→1fr device) vs one open at rest.
> - `navbar.measured.megaPanel` — the open-panel PRESENTATION register, measured from
>   computed styles: `surface {bg, borderTop?, radius?}`, `hiddenState {opacity,
>   transform}` (the close pose the open transition animates from), `motion {panel,
>   link, description?, chevron?}` (each `{property, duration, easing, delay}` — at
>   least one time literal REQUIRED when menus exist), `link {padding, radius,
>   fontSize, hoverBg?}`, `groupTitle {fontSize, fontWeight, color, textTransform?,
>   letterSpacing?}`, `aside {borderLeft?, maxWidth?, paddingLeft?}`.
> - `navbar.megaOpen[]` — OPEN-STATE geometry per tab (Playwright hover/force pass):
>   `{label, open, panel {x,y,w,h}, aside? {widthFraction, borderLeft?}, groups:
>   [{rect, links, linkColumns?, aside}], card?, shot?}`. Renderers read the aside
>   width fraction + main-group link column count from here; each open entry must
>   carry a real panel box and a matching `menu` on the same-labeled primary link.
> - `navbar.measured.trigger.chevron` — the dropdown-trigger AFFORDANCE family fact
>   (fid15 2026-07): the small trailing glyph a menu-owning tab carries. `{kind: svg,
>   asset, box {w, h}, gap?, transition?, openTransform?}` — `asset` is the HARVESTED
>   artwork (inline svg materialized under assets/), `gap` the measured label→glyph
>   space, `openTransform` the open-state transform measured by flipping the trigger's
>   expanded state (e.g. `matrix(-1,0,0,-1,0,0)` = 180° rotation), `transition` the
>   chevron's own motion. REQUIRED when menu-owning triggers render an inline glyph
>   (DOM-detectable) — capture it or mark `chevronNotObserved: true` on `measured.trigger`.
> - `navbar.utility[]` — IN-BAR utility CONTROLS (fid15), distinct from nav
>   destinations: the bar's trailing cluster (account links, locale switchers) and any
>   above-bar tier rows. Each entry: `{label, href, kind: link|dropdown, role?
>   (login|language|… — derived from the control's OWN semantics: auth-endpoint href,
>   language/locale accessible name; never content vocabulary), bar? (trailing),
>   ariaLabel?, collapsedLabel? (the short label the bar actually shows), icon?
>   {kind: svg|img|mask|bg, asset, size?}, chevron? (trigger-chevron shape above),
>   dropdown? {items: [{label, href, lang?, current?}], panel {w, h, bg, radius,
>   border?, shadow?, paddingY?}, item {fontSize, color, padding, radius?},
>   currentItem? {bg, color}}}`. A `kind: dropdown` control's open state is captured
>   live (panels portal on open); items must come from the source DOM. A control whose
>   glyph wasn't harvested renders as a text link (degrade, never invent artwork).
> - `navbar.utilityBanner` — the dismissible promo strip ABOVE the bar, full anatomy
>   (fid15): `{observed, text, bg, ink, fontSize?, cta? {label, href, underline?,
>   color?, fontWeight?, arrow? {kind: svg, asset}}, close? {kind: svg|box-only|text,
>   box {w, h}, strokeWidth?, ink?, ariaLabel?, asset?}, dismissible, provenance,
>   source}`. `close.kind: box-only` records a measured close BOX whose glyph artwork
>   the capture could not harvest (runtime-injected) — renderers may draw the X from
>   the measured box/strokeWidth facts (fact reconstruction), never from imagination.
>   When the live page no longer serves the banner, a saved banner-embed FRAGMENT
>   (its own captured document) is a valid measurement source (`provenance` names it).
> - **Validator (C21)** enforces the affordance family: corpus-named trigger chevrons /
>   locale switchers demand the fact or its `…NotObserved` marker, bound assets must
>   exist on disk, dropdown-kind utility controls need live-captured items + panel
>   paint, href-less menu-less primary entries flag as flattened bar controls, and an
>   observed banner owes cta + close anatomy (or explicit not-observed markers).
> - `footer.measured.grid` — the directory's column→group HIERARCHY from DOM geometry:
>   `wrapperSizes: [n, …]` (groups stacked per MAJOR column, source order; the sum
>   must equal the extracted group count), plus `columnGap`, `wrappers[]` provenance.
>   `footer.measured.heading` — the group-heading register (`color`, `fontSize`,
>   `fontWeight`, `textTransform?`, `letterSpacing?`) — REQUIRED when columns carry
>   headings (headed columns must not default to link styling).
> - `footer.bottomBar` — the legal-row structure: `divider {present, color?, opacity?}`
>   (REQUIRED shape), `rows: [{kinds, justify?, align?, gap?}]` (observed composition),
>   `disclaimer?`, `storeBadges?: [{href, img: {asset, alt}}]`, `policyLinks:
>   [{label, href}]` (the bottom bar's OWN links, distinct from `legal.links` keyword
>   matches). Social + legal WITHOUT any bottomBar facts warns (stale capture).
> - `footer.social[]` icon facts: `kind: icon` entries MUST bind harvested artwork —
>   `icon {kind: svg|mask|img|bg, asset, size?, ink?}` + optional `box {width, height,
>   radius?, bg?}` (the tappable box). No artwork harvested ⇒ author `kind: text`;
>   renderers degrade to accessible text links, never invented glyphs.
> - **Single-color glyph RENDERING CONTRACT (fix4 2026-07)** — the chrome's SVG
>   glyph facts above (trigger/utility chevrons, utility icons, banner arrow/close,
>   social icons) and the text-CTA `glyph` (§10.2) all emit as SANITIZED INLINE
>   `<svg>` markup (`prepare_chrome_glyphs` stamps `_inlineSvg` beside `_dataUri`;
>   `sanitize_inline_svg` strips script/foreignObject/event-attrs/external refs,
>   guarantees xmlns + viewBox, drops width/height/foreign classes, dedupes ids
>   per emitted instance, stamps `aria-hidden="true" focusable="false"`, and
>   normalizes ink to `currentColor` ONLY after verifying the artwork is genuinely
>   single-ink). The measured ink facts (`icon.ink` etc.) keep working — they ride
>   the host's `color` chain now instead of a mask fill. Artwork that fails
>   verification (multi-color, gradient, `<style>`-driven) keeps the fix2 data-URI
>   currentColor-mask channel under a `--mask` modifier class; multi-color MARKS
>   (store badges, wordmark `<img>` bindings, mega-panel item icons) stay on the
>   image channel entirely. Brand data is unchanged by this contract — it is an
>   emission technique, not a fact.
> - **Glyph asset `viewBox` is EVIDENCE, not a template (fix5 2026-07).** When
>   harvest materializes a sprite `<use>`/`<symbol>` reference into a standalone
>   asset file, the asset's `viewBox` MUST be copied from the source symbol —
>   never assumed from a common icon-grid convention. A wrong viewBox crops the
>   artwork identically in BOTH channels (mask and inline render the same
>   coordinate system), so replica pixel-parity cannot catch it; the guard is
>   geometric: every chrome glyph asset's painted extent (`getBBox`) must fit its
>   declared viewBox (≤5% spill tolerance for source-faithful bleed) —
>   `test_fix5_gallery_defects.GlyphCropTest`. Caught: 15 hubspot-v2 assets
>   authored `0 0 24 24` over 32-grid (and custom-grid social) artwork.

> **Two-tier chrome + action groups (fix1 2026-07 — validator C22 advisory).**
> All optional; brands without the facts render byte-identically.
>
> - `navbar.utilityTier` — the EXPLICIT opt-in for a distinct thin utility bar
>   ABOVE the primary bar: `{height, bg?, fontSize?, trailing?: [labels]}`.
>   `render_navbar` gates the two-tier markup on THIS key — never on `twoTier`
>   alone, because a brand can declare `twoTier: true` with a measured
>   `utilityBarHeight` of 0 (collapsed tier) and must keep its single bar. The
>   captured `navbar.utility[]` run splits into the leading cluster (source
>   order) and the trailing cluster (`trailing` placement labels, declared
>   order) — placement facts win over any structural default. The primary tier
>   keeps logo + primary links + actions with unchanged trigger markup (mega
>   bindings and the fid15 chevron/glyph discipline ride as before).
> - `navbar.ctas[]` as an ACTION GROUP — when the extraction declares TWO OR MORE
>   bar actions, each entry carries its own measured register facts
>   (`{label, href, style: primary|secondary|…, bg, color, border?, borderRadius,
>   height?, padX?, fontSize?}`) and the bar renders the N-action run, each action
>   painted from its own facts (`--navcta-*` consumption vars incl. the border
>   channel). Single-cta brands keep the existing one-action markup byte-identically.
>   Register hierarchy inside any group is auditable (anti-ai-slop AS-59: exactly
>   one filled primary register per group).
> - `footer.bottomBar.anatomy: centered-stack` — the bottom block renders as a
>   centered COLUMN: social glyph row flanked by same-row hairline rules
>   (`bottomBar.divider.color`), then the brand wordmark (`footer.logo` art
>   recolored to the footer ink via CSS mask), then the centered legal line, then
>   the underlined policy row. Brands without the key keep the inline row1/row2
>   bottom-bar grammar unchanged.
> - `tokens` button families may declare `onInverse: {bg?, color?, border?}` —
>   the register the family takes on surfaces that declare `controls: onInverse`
>   (surface-scoped variable re-pointing; see tokens §3).
> - Pattern `contentShape.bandRhythm` (layout library) — authored per-band
>   relational rungs `{eyebrowToHeading?, headingToBody?, bodyToCta?}` consumed as
>   scoped gap variables by the band's composer (measured ladder values, not
>   structural defaults).
> - **Validator (C22, advisory)** — when measured chrome shows a real utility tier
>   (`navbar.measured.utilityBarHeight` > 0) but the authored contract lacks
>   `navbar.utilityTier`, advise (not error): the tier is evidence the authoring
>   should declare.

> **Vertical rhythm (spacing) — STYLE owns the scale, BRAND owns the measured values.**
> The active STYLE layer (`styles/<id>.md`, front-matter `spacing:` — authoritative — with
> the prose *Density & rhythm → Vertical rhythm & spacing scale* subsection as the parser
> fallback) owns a brand-agnostic vertical-rhythm scale: named rem STEPS plus which step
> each structural gap defaults to (section vertical padding top/bottom, inter-block gap,
> tight cluster gap). It is the fallback. **Brand EXTRACTION should capture the
> source's REAL vertical spacing into `tokens.spacing`** — the section's actual top/bottom
> padding (`section-padding-*`, ideally with a `modeLadder`) and the real gaps between
> modules/blocks (`module-gap-*`, `*-to-*`) — so future generations are on-brand to the
> source rhythm, not a generic scale. The composer **PREFERS these brand spacing tokens**
> when present and falls back to the style scale only where the brand is silent; section
> vertical padding is applied symmetrically (top = bottom) unless the brand commits
> otherwise. Capture spacing with the same provenance discipline as every other token.

## 4. `surfaceGrammar`, `layouts[]`, `compositionRules[]`, rule lists, `voice`, `recipePolicy`

### 4.1 `surfaceGrammar`

```yaml
surfaceGrammar:
  roles:        [ <surfaceRole>… ]           # enumerated, must each exist in tokens.surfaces
  pageRhythm:   { value: [<surfaceRole>…], …envelope }
  transition:   { value: "hard-cut|gradient|fade", …envelope }
  nesting:
    - { child: <surfaceRole>, allowedParents: [<surfaceRole>…], …envelope }
```

### 4.2 `layouts[]` — archetype instances (slots → blocks/media)

`archetype` is a **library-agnostic enum** describing the structural shape of a
section (`stack`, `split`, `grid`, `bento`, `collage`, `overlay`, `band`, …). A
layout exposes **slots filled by blocks/media**; blocks expose slots filled by
primitives — slots are recursive (scaffold → block → primitive).

```yaml
layouts:
  - id:            <slug>                     # e.g. "opening-bookend"
    archetype:     stack|split|split-fullbleed|stack-fullbleed|grid|bento|row|band|collage|overlay
    surfaceIntent: <surfaceRole>              # which surface this section defaults to
    slots:                                    # the layout's named slots
      - { name: "<slot>", role: <semantic role>, fill: [<block|primitive|media ref>…] }
    gridRules:     { columns, stagger, overlap, gap: { value }, …envelope }
    widthRules:    { container: "<intent: full-bleed|wide|standard|narrow|rem>", measure: "<fraction|ch>", …envelope }
    overlapRules:  { types: [<overlap type>…], zOrder: [<layer>…], …envelope }
    blockMapping:                             # slot semantic → block/primitive contract + brand usage
      - slot:      "<slot name>"
        role:      "<semantic role>"
        contract:  "<block or primitive key from contracts>"   # e.g. "header", "image"
        usage:     { <intent prop>: <value> }                  # library-agnostic props only
    patternRef:    { lib: project|standard, id: <patternId> }  # OPTIONAL back-ref: the reusable
                                                               # use-case layout PATTERN (§4.4) this
                                                               # section was generated from / promoted to
    eyebrowRegister: <color token role>       # OPTIONAL: the section's declared eyebrow
                                              # color family — a `tokens.colors` ROLE the
                                              # section's theme scope selects (e.g. an
                                              # accent family or the muted ink family)
    confidence:    high|medium|low
    provenance:    [<sectionId>…]
```

> `patternRef` is additive and optional — a layout with no `patternRef` behaves exactly as
> before. It links a concrete section instance to the reusable **use-case layout pattern**
> (§4.4) it reuses, so generation looks the pattern up instead of reinventing structure.

> `eyebrowRegister` implements theme-scoped eyebrow families ("eyebrow color follows the
> section's declared scope"): when present, the composed section's eyebrow microlabel
> reads that color role (section-scoped `--c-eyebrow-color` → the layer-1 `--color-*`
> var); undeclared layouts keep the render path's default register (muted ink, or the
> active style's single-accent deployment). The value must name a role the brand's own
> `tokens.colors` carries — an unknown role fails loud at composition. Role names stay
> generic/reusable (an accent family, a muted ink family), never section-specific.

> Substrate ids for the scaffold/components a layout maps to (Webflow component ids,
> Section/Layout names) are **not** here — record them per-section in `targetMappings`
> (§7) for the deferred assembler.

### 4.3 `compositionRules[]`, the three rule lists, `voice`, `recipePolicy`

```yaml
compositionRules:
  - id: <slug>                    # overlap, stagger, z-order, counter-row, panel-offset…
    statement: "<rule text>"
    value: <object|string>
    confidence: …; source: …; scope: …; changelog: […]
```

**The rule model is THREE symmetric lists**, each entry a rule envelope:

```yaml
do:                               # POSITIVE prescriptions — the affirmative house style
  - { id: <slug>, statement: "<text>", value: true|<object>,
      confidence, source, scope, changelog }

avoid:                            # SOFT discouragements — prefer-not, not absolute
  - { id: <slug>, statement: "<text>", value: true|<object>,
      confidence, source, scope, changelog }

neverDo:                          # HARD prohibitions — absolute
  - { id: <slug>, statement: "<text>", value: true,
      confidence, source, scope, changelog }
```

- `do[]` = what the brand *does* on purpose (e.g. "all actions are typographic with
  arrows/slashes"). The affirmative twin of `avoid`/`neverDo`.
- `avoid[]` = soft "prefer not to" — discouraged but not a build failure if violated.
- `neverDo[]` = hard prohibitions — an on-brand check fails if violated.

```yaml
voice:
  ref: "./voice.md"
  factsRef: "./voice-facts.yaml"  # structured voice facts (§4.8, pass1 2026-07)
  dials:
    variance: { value: high|medium|low, …envelope }
    motion:   { value: high|medium|low, …envelope }
    density:  { value: high|medium|low, …envelope }

recipePolicy:
  scaffoldFirst:        { value: true, … }   # instantiate the scaffold, then fill
  reuseBeforeCreate:    { value: true, … }   # map onto existing contracts before creating
  composeFromPrimitives:{ value: true, … }   # build blocks from primitives + bind props
  themeViaModes:        { value: true, … }   # surface = a theme mode, never hardcoded colors
  slotsTakeInstancesOnly:{ value: true, … }  # only contract instances inside slots
  magicTrick:                                 # WILDCARD (variant C) variance policy
    wildcardScope:      { value: hero-only, … }  # one-off neverDo relaxation is HERO-only
```

> **Wildcard scope (hero-only).** The WILDCARD variant's one-off `neverDo` relaxation
> (`scope: one-off`, logged to `signals.log`, never promoted) is permitted on **HERO
> sections only** (archetype `hero` / `opening-bookend`); every non-hero section
> enforces ALL `neverDo` rules.

### 4.7 `signatures:` — the brand's recognizable moves (pass1 2026-07)

The 3-5 moves that make THIS brand recognizable, each a **machine-checkable
always/never rule with evidence provenance**. Authoring them is a REQUIRED
extraction step (layout-analyst-skill.md §10); the C25 validator advisory is the
enforcement backstop; `brand_pipeline/signature_audit.py` verifies them on every
gated page (`signature_check`) and walks the accent paint budget
(`accent_budget`).

```yaml
signatures:
  - id: <slug>                    # brand-specific NAME, generic KIND
    kind: accent-scope | shape-motif | type-treatment | surface-habit | spacing-habit
    mode: always | never          # the rule's polarity — machine-checkable, not prose
    claim: "<one-sentence prose companion>"
    check:                        # kind-specific machine parameters, e.g.:
      colors: ["#ff5c35"]         #   accent-scope: family + role scoping
      allowedRoles: [action-primary, arrow-link, logo-mark]
      forbiddenRoles: [body-text, heading]
      maxPaintSharePct: 5         #   optional accent_budget rider
      # shape-motif: buttons: {radiusPx: 8 | pill: true} | neverPill: true
      # type-treatment: probes: [{on: display, familyIncludesAny: […], weightMax: 500}]
      # surface-habit: darkAllowedColors/darkMaxLuminance | sectionMinLuminance
    evidence: ["<sections/computed facts that license the rule>", …]
    confidence: {value: high, source: measured}
    changelog: […]
```

Laws:
- **3-5, not 20** — signatures are the brand's *recognizable* moves, not a rule
  dump; fewer than 3 means the extraction hasn't found the brand's voice yet.
- **Generic key vocabulary, brand-specific values** — the `kind` set is shared
  pipeline vocabulary; names/values describe this brand (`action-orange-scope`
  names a reusable accent-scoping move, never a section).
- **Every signature cites evidence** — the sections/computed facts that license
  it, same provenance discipline as every other fact.
- `spacing-habit` signatures are verified by the spacing/scale machinery, not
  the signature auditor — the auditor reports them as delegated.
- **Specimen lanes** (spec books / component previews — no composed sections):
  page-level claims (accent-scope, surface-habit) are void; element-level claims
  (shape-motif, type-treatment) still bind.

### 4.8 `voice.factsRef` — structured voice facts (pass1 2026-07)

`voice.md` stays the prose companion; the machine-checkable layer is a sibling
`voice-facts.yaml` (schema `voice-facts.v1`) referenced from the voice block:

```yaml
voice:
  ref: "./voice.md"
  factsRef: "./voice-facts.yaml"   # structured facts the voice gate audits against
  dials: …
```

`voice-facts.yaml` carries: tone descriptors, sentence-length stats
(mean/median/p90/max words) **with gate budgets** (measured envelope +
documented headroom), reading-level band (Flesch-Kincaid), casing rules per role
(headings/eyebrows/CTAs, with the brand-term allowlist — multi-word product
names strip as phrases), verb-led CTA share, punctuation facts (exclamation
ban), and a banned-hype lexicon (words the captured corpus never uses). All
derived from the CAPTURED copy corpus (section-copy + grounding) —
deterministic, regenerable, provenance recorded. `brand_pipeline/voice_audit.py`
audits generated copy against it (advisory severity by default, `--strict` to
gate); brands without the file skip cleanly (fact-gated).

### 4.9 `style-scale.yaml` — the derived-scale artifact (pass1 2026-07)

The QUANTIZATION layer: `tools/extract/normalize_scales.py` derives, from the
existing captured evidence, one quantized scale artifact per brand
(`<brand>/style-scale.yaml`, schema `style-scale.v1`):

- `type` — modular ratio + base size fit against the measured type ladder
  (parsimony: the COARSEST candidate ratio whose RMSE clears the bar wins — a
  denser ratio fits anything, which would be vacuous quantization);
- `space` — base unit + step multiples + section rhythm from the measured
  spacing ladder AND the brand's own authored `--spacing-*` custom properties in
  the evidence CSS corpus;
- `radius` — corner modes grouped from the measured radius facts;
- `grid` — content max-width/gutter/card gap where measured (columns never
  invented);
- `motion` — the measured duration band.

**Dual-artifact law:** raw evidence and `brand.yaml` are never touched; every
derived value records provenance (which raw facts produced it) and fit error;
a brand that genuinely doesn't follow a scale is recorded honestly
(`fitQuality.verdict: poor`, `followsScale: false` — a poor fit is NOT consumed).

**Consumption law** (`brand_pipeline/style_scale.py`): GENERATIVE composers may
prefer a derived step for NEW geometry **only where no measured fact binds** (a
measured fact always wins); the REPLICA lane never loads the artifact —
byte-identical by construction, test-pinned. Current consumer: the `bandHeight`
knob's degrade (`compose_section.band_height_derived_px`) — a composed section
whose knob has no measured rung in its direction rides the nearest derived
section-rhythm step and stamps `data-band-rung="derived:<px>"`, which the
spacing auditor treats as a deliberate declaration (same hard gate).

Validator advisory **C24** checks internal consistency (steps on the base,
rhythm a subset of steps, type steps on the ratio) and fit honesty (recorded
errors back the verdict; stale `sourceDigest` flagged). The `scale_adherence`
gate (spacing auditor) audits generative-lane novel geometry against the
artifact (spec/spacing-conformance.md).

### 4.10 Section-scoped rules + conversion grammars (quality steals 2026-07)

Two shared, brand-INDEPENDENT contract files sit beside the vocabulary catalogs
(they are law about generated OUTPUT, so they live in `contracts/`, not in any
`brand.yaml`):

- **`contracts/section-rules.yaml`** (`section-rules.v1`) — per-section-family
  falsifiable quality rules (hero, stat-band, logo-strip, capture-form,
  pricing-tiers, quote, feature-grid, faq, cta-band, nav, footer, carousel).
  Law text: `spec/section-rules.md`; checker: `section_rules_audit.py`
  (battery member). Rules with `enforcement: delegated` name existing law
  (`delegatedTo`: an AS rule / gate / IC family) and are never re-implemented.
- **`contracts/conversion-structure.yaml`** (`conversion-structure.v1`) — per
  campaign-type section-SEQUENCE grammars (funnel depth bands, form placement,
  proof ordering). Law text: `spec/conversion-structure.md`; checker:
  `conversion_audit.py` (advisory; hardFloor rows gate); prompt-side guidance
  projection: `conversion_structure.render_guidance_block` behind the
  opt-in `inject_conversion_guidance` flag (default OFF — byte-identical
  prompts otherwise).

A brief opts into a grammar with ONE frontmatter key — `campaignType: <id>` —
beside the existing `pageType`/`taskIntents`/`variance` keys. Briefs without it
are untouched by both layers (fact-gated). The standing 12-brief instrument
that exercises both contracts is `evals/matrix/` (protocol in its README).

## 5. `contracts` — the universal THREE-TIER vocabulary layer (NEW)

Three shared, library-agnostic catalogs define the full structural vocabulary
**ONCE** for all brands. They form a single recursive slot model:

```
SCAFFOLD  (Tier 3 — section shell + surface)
   └─ slots filled by ─→  BLOCK     (Tier 2 — a composed cluster)
                             └─ slots filled by ─→  PRIMITIVE  (Tier 1 — atomic leaf)
```

| file | tier | what it defines |
|---|---|---|
| `brand_pipeline/contracts/primitives.yaml` | **Tier 1 — atomic primitives** (~36) | the universal leaf elements grouped Text / Action / Media / Indicators & utility / Form (eyebrow, heading, subheading, paragraph, label, caption, quote, stat, list, code, button, link, cta, icon-button, image, video, icon, logo, avatar, illustration, pill, badge, rating, progress, tooltip, divider, spacer, input, textarea, select, checkbox, radio, toggle, slider, file-upload, form-field) — each with `intent`, grouped `props` (content/style/layout/state/visibility per `prop-naming.md`), and `slots` |
| `brand_pipeline/contracts/blocks.yaml` | **Tier 2 — composed blocks** (~23) | recurring clusters with an internal slot grammar (header, content-block, card, feature-item, form, testimonial, stat-block, logo-bar, navbar, footer, accordion, tabs, pricing-card, banner, modal, dropdown-menu, breadcrumb, pagination, table, carousel, steps, cta-block, media-text) — slots reference primitive/block contract keys; **slots are recursive** |
| `brand_pipeline/contracts/scaffolds.yaml` | **Tier 3 — structural scaffolds** (12) | the section shell + surface (section-stack, section-split, section-split-content-form, section-split-fullbleed, section-stack-fullbleed, layout-grid, layout-bento, layout-row, layout-stack, layout-split, header-scaffold, logos-wrapper) — each with `archetype` (matching `layouts[].archetype`), slot count, and intended use. Composites `band`/`collage`/`overlay` have no native scaffold: they reuse `section-stack` and build the offset/overlap composition from primitives inside the slot |

`brand.yaml` references all three and **never redefines a contract** — it records
**ONLY per-item usage rules** against them (exactly the token model: universal
contract + brand override):

```yaml
contracts:
  primitives: "../../../brand_pipeline/contracts/primitives.yaml"
  blocks:     "../../../brand_pipeline/contracts/blocks.yaml"
  scaffolds:  "../../../brand_pipeline/contracts/scaffolds.yaml"
```

> Prop groups (`content` / `style` / `layout` / `state` / `visibility`) are defined
> once in `prop-naming.md` and shared by every primitive/block contract. This schema
> references that grouping; it does not restate it.

### 5.1 Brand overrides — `primitives[]` and `blocks[]`

`brand.yaml` gets `primitives:` and `blocks:` sections that record **ONLY THIS
brand's usage rules, chosen variants, slot omissions/remaps, and prohibitions**
against the shared contracts. A brand expands these **brand-by-brand**, only for what
its sections actually need; it does NOT re-list the whole catalog. (Scaffold usage is
recorded per-section in `layouts[]`, §4.2 — each layout is a brand INSTANCE of a
scaffold contract.)

```yaml
primitives:
  <contractKey>:                  # MUST exist in contracts/primitives.yaml
    origin:     extracted|designed     # REQUIRED — see §5.2
    use:        always|never|<when>    # this brand's stance on the primitive
    variant:    <variant from the contract's variants>   # the brand's chosen shape
    remapFrom:  <otherContractKey>     # optional: brand expresses role X as this primitive
    rules:      [ <ruleKey ref or short statement> ]      # brand-specific usage rules (brand-UNIQUE only)
    refs:       [ neverDo.<id>, … ]    # optional: structured reference to the neverDo (or do)
                                       # that ALREADY expresses this constraint — use instead of
                                       # restating a neverDo as prose (single source of truth).
    # origin=extracted →  provenance: [<sectionId>…]      (required)
    # origin=designed  →  designedFrom: {…}; overridable: true   (required)
    confidence: …; source: …; scope: …; changelog: […]

blocks:
  <contractKey>:                  # MUST exist in contracts/blocks.yaml
    origin:     extracted|designed     # REQUIRED — see §5.2
    slots:                        # per-slot brand stance (omit / require / variant)
      <slotName>: { use: require|omit|optional, note: "<text>" }
    rules:      [ <ruleKey ref or short statement> ]   # brand-UNIQUE prose only
    refs:       [ neverDo.<id>, … ]    # optional: reference a neverDo/do instead of restating it
    confidence: …; source: …; scope: …; changelog: […]

  <contractKey>:                  # a block the source pages genuinely NEVER show
    notObserved: true             # explicit absence marker (§10) — never just omit the key
    note: "<where you looked>"    # optional: which grounding/DOM evidence confirms the absence
```

> **Every contract block type is ATTEMPTED — evidence or explicit absence.** Extraction
> must leave each `contracts/blocks.yaml` key either populated with evidence
> (`origin`/`use`/`slots`/`provenance`) or explicitly marked `notObserved: true`. A
> silently-missing key is indistinguishable from "extraction never looked", which is how
> a source site's card component vanished from a brand (`card` prose lived only in layout
> useCase text). The output-contract validator (§10) fails on silent gaps.

> **`refs` vs `rules` (de-duplication).** A primitive/block should NOT restate a rule that
> a `neverDo` (or a `use`/`variant`/`remapFrom` binding) already expresses. When the only
> content of `rules` would duplicate a `neverDo`, drop the prose and record a structured
> `refs: [neverDo.<id>]` instead. `rules` is reserved for brand-UNIQUE guidance not already
> captured elsewhere. `render_brand_md.py` projects `use`/`variant`/`remapFrom`/`refs` and
> suppresses rule prose when `refs` is present, so `brand.md` restates nothing.

> Example intent: WoodWave has no buttons, so it **remaps the CTA role onto the
> `link` primitive** with `variant: arrow`, and marks the `button` primitive
> `use: never`. It records this as a brand override — it does not edit the universal
> `button` contract.

### 5.2 `origin` — `extracted` vs `designed` (provenance discipline)

**Every** `primitives[]` and `blocks[]` entry carries a REQUIRED `origin` field that
declares whether the brand rule was *observed* on a real page or *synthesized* to keep
the brand consistent. This keeps real evidence separable from confident invention.

```yaml
origin: extracted | designed
```

- **`extracted`** — the item was **actually observed** on a source page. It REQUIRES
  `provenance: [<sectionId>…]` (resolved via `provenanceIndex`, §6). An extracted
  entry is grounded fact.

  ```yaml
  primitives:
    link:
      origin: extracted
      use: always
      variant: arrow
      remapFrom: cta
      rules: [ "CTA realized as a typographic arrow link, never a button" ]
      provenance: [opening-bookend, about-run]      # REQUIRED for extracted
      confidence: high; source: creation; scope: design-language; changelog: []
  ```

- **`designed`** — the item was **NOT on the page**; it was synthesized to be
  brand-consistent (so a future section that needs it has a coherent rule). It
  REQUIRES a `designedFrom` note (the `do`/`avoid`/`neverDo` rules and tokens it was
  derived from) and `overridable: true` (a designed entry must always yield to a later
  real observation).

  ```yaml
  primitives:
    badge:
      origin: designed
      use: <when>
      designedFrom:                                 # REQUIRED for designed
        do:      [ surface-flip-hierarchy ]
        avoid:   [ avoid-accent-overuse ]
        neverDo: [ no-radius, no-shadows ]
        tokens:  [ accent/highlight, text/on-inverse ]
        note: "no badge observed; synthesized as a flat, square, accent-on-dark chip to match the system"
      overridable: true                             # REQUIRED for designed
      confidence: low; source: creation; scope: design-language; changelog: []
  ```

> A `designed` entry is a placeholder built from the brand's own rules and tokens —
> never from another brand or a generic default. It is always lower-confidence than an
> `extracted` entry and is always `overridable`.

### 5.3 The OVERRIDE RULE (extracted supersedes designed)

When a future page is fed and an item that was previously `designed` is now **actually
observed**, the extracted observation **SUPERSEDES** the designed entry:

1. Flip `origin: designed` → `origin: extracted`.
2. Replace the synthesized rule/value with the observed one; set `provenance:
   [<sectionId>…]` and **drop** `designedFrom` / `overridable` (no longer designed).
3. Append a changelog entry recording the promotion:

   ```yaml
   changelog:
     - { ts: <iso8601>, action: promoted-from-designed,
         from: <designed value>, to: <extracted value>,
         by: iteration, signalId: <id|null>,
         note: "observed on <sectionId>; designed placeholder superseded" }
   ```

Direction rules (one-way ratchet toward evidence):

- **`extracted` is never silently overwritten by a `designed` value.** A synthesized
  rule can never clobber a real observation; designed only fills gaps.
- **`designed` → `extracted`** on first real observation (the promotion above).
- **Two `extracted` observations across pages** (the same item seen on multiple pages)
  do NOT use this rule — they reconcile via the normal rule-entry envelope +
  confidence/`scope` reconciliation (§2): conflicting observations land `one-off`,
  agreeing ones raise confidence and may promote to `design-language`.

### 5.4 Combined usage example (`extracted` + `designed` side by side)

```yaml
primitives:
  link:                                   # OBSERVED on the page → extracted
    origin: extracted
    use: always
    variant: arrow
    remapFrom: cta
    rules: [ "CTA realized as a typographic arrow link, never a button" ]
    provenance: [opening-bookend, about-run]
    confidence: high; source: creation; scope: design-language; changelog: []

  badge:                                  # NOT on the page → designed (synthesized to fit)
    origin: designed
    use: <when>
    designedFrom:
      do:      [ surface-flip-hierarchy ]
      neverDo: [ no-radius, no-shadows ]
      tokens:  [ accent/highlight, text/on-inverse ]
      note: "no badge observed; synthesized as a flat square accent-on-dark chip"
    overridable: true
    confidence: low; source: creation; scope: design-language; changelog: []

blocks:
  header:                                 # OBSERVED → extracted
    origin: extracted
    slots:
      heading: { use: require }
      cta:     { use: optional, note: "arrow link only (see primitives.link)" }
    rules: [ "header centered only in bookend/conversion; editorial runs anchored" ]
    provenance: [opening-bookend]
    confidence: high; source: creation; scope: design-language; changelog: []
```

## 6. `recipePolicy`, `provenanceIndex`, `indexes`

`recipePolicy` is in §4.3. `provenanceIndex` maps each `sectionId` to its source
(url / DOM node / screenshot). `indexes` (optional) points at sibling artifacts this
`brand.yaml` indexes without superseding (SIGN-OFF #6).

## 7. `targetMappings` — OPTIONAL, NON-CANONICAL substrate annotations

This block is **not part of the canonical design language**. It is an annotation
layer consumed **only by the deferred Webflow Assembler** to bind library-agnostic
intent to real Webflow ids. The Tailwind/shadcn renderer ignores it entirely.

```yaml
targetMappings:
  webflow:                                   # one block per substrate; only "webflow" today
    site: { name: "<site name>", siteId: "<id>" }
    tokens:
      colors:
        <semanticRole>:                      # MUST match a tokens.colors key
          mapsTo:     "<Group/Name>"         # real variable name in the library
          variableId: "variable-…"
          collection: "Brand colors|Color schemes|Card color schemes"
          mode:       "<mode name|base|null>"
          modeId:     "mode-…|null"
          status:     mapped|created
      type:
        <roleName>: { mapsTo: "<Group/Name>", variableId: "…", sizeVar: "<Group/Name>" }
      spacing:
        <roleName>: { mapsTo: "<Group/Name>", variableId: "…", status: mapped|created }
      surfaces:
        <surfaceRole>: { schemeMode: "<mode name>", schemeModeId: "mode-…" }
    layouts:
      <layoutId>:                            # MUST match a layouts[].id
        scaffold:    { component: "<library component name>", componentId: "<id>" }
        surfaceMode: { mode: "<mode name>", modeId: "mode-…" }
        components:                          # slot → real library component for the assembler
          - { slot: "<slot>", role: "<role>", component: "<name>", componentId: "<id>", props: { … } }
```

The mapping keys (`tokens.colors.<role>`, `layouts.<id>`) are **back-references** into
the canonical nodes. If a canonical node has no `targetMappings` entry, the Tailwind
renderer still works; only the deferred assembler needs the mapping.

## 8. FILLED-IN WoodWave example — `brand.yaml` (NON-NORMATIVE)

> **Illustrative only — never copy example values.** The SHAPE is a real extraction;
> the color values below are replaced with obviously-fake placeholders so no example
> hex can be mistaken for a default. A different brand fills every node with its own
> measured values (rounded, buttoned, light-chrome brands are equally valid). Canonical
> nodes are library-agnostic; all Webflow ids live under `targetMappings.webflow`.
> Changelog timestamps use the run date.

```yaml
version: "2.0"

brand:
  name: "WoodWave Gallery"
  sourceUrl: "https://woodwavegallery.webflow.io"
  snapshot:
    value: >-
      A warm, two-tone editorial system built on a single high-contrast didone
      serif set uppercase at every display tier. Cream canvas hosting staggered,
      hard-edged photography with marginal micro-captions; deep warm-brown bands as
      bookends; enormous ghost watermark words behind content; zero interface
      chrome. Hierarchy is carried by type size, surface flips, and overlap.
    confidence: high
    source: creation
    scope: design-language
    changelog:
      - { ts: "2026-06-12T00:26:00Z", action: created, from: null,
          to: "editorial two-tone didone system", by: creation, signalId: null,
          note: "first-pass extraction from live site" }

contracts:
  primitives: "../../../brand_pipeline/contracts/primitives.yaml"
  blocks:     "../../../brand_pipeline/contracts/blocks.yaml"
  scaffolds:  "../../../brand_pipeline/contracts/scaffolds.yaml"

tokens:
  colors:
    # ILLUSTRATIVE hexes (obviously fake) — a real brand.yaml carries MEASURED values.
    surface/primary: { value: "#FEFEF0", role: "light canvas background", provenance: [opening-bookend, about-run] }
    surface/inverse: { value: "#010203", role: "dark bookend band", provenance: [opening-bookend] }
    accent/highlight:{ value: "#ABC123", role: "accent, scoped per brand rules", provenance: [opening-bookend] }
    text/on-primary: { value: "#0F0F0F", role: "body/display text on light", provenance: [about-run] }
    text/on-inverse: { value: "#FAFAFA", role: "text on dark bands", provenance: [opening-bookend] }
  type:
    display-hero: { family: "Playfair Display", sizeRem: { base: 6, tablet: 4.5, mobileL: 3.5, mobile: 3 }, lineHeight: "1.05em", weight: 400, letterSpacing: "0rem", case: uppercase }
    eyebrow:      { family: "Inter", sizeRem: { base: 0.6875 }, lineHeight: "1.2em", weight: 400, letterSpacing: "0.08em", case: uppercase }
  spacing:
    section-padding-light: { value: "6.875rem", role: "vertical section padding on cream", modeLadder: { base: "6.875rem", tablet: "5rem", mobileL: "4rem", mobile: "4rem" } }
  surfaces:
    surface/primary: { bg: "#FEFEF0", intent: "default light canvas", textPrimary: text/on-primary, textAccent: null, provenance: [about-run] }
    surface/inverse: { bg: "#010203", intent: "dark bookend band", textPrimary: text/on-inverse, textAccent: accent/highlight, provenance: [opening-bookend] }

surfaceGrammar:
  roles: [ surface/primary, surface/inverse ]
  pageRhythm:
    value: [ surface/inverse, surface/primary, surface/inverse ]
    confidence: high; source: creation; scope: design-language
    changelog: [ { ts: "2026-06-12T00:26:00Z", action: created, from: null, to: "inverse→primary→inverse", by: creation, signalId: null, note: "observed page rhythm" } ]
  transition:
    value: "hard-cut"
    confidence: high; source: creation; scope: design-language
    changelog: [ { ts: "2026-06-12T00:26:00Z", action: created, from: null, to: "hard-cut", by: creation, signalId: null, note: "no gradients/fades at seams" } ]

primitives:
  heading:
    origin: extracted
    use: always
    rules: [ "display tiers use the didone serif, uppercase" ]
    provenance: [opening-bookend, about-run]
    confidence: high; source: creation; scope: design-language; changelog: []
  eyebrow:
    origin: extracted
    use: always
    rules: [ "micro-captions live in the margin, never over photos" ]
    provenance: [about-run]
    confidence: high; source: creation; scope: design-language; changelog: []
  image:
    origin: extracted
    use: always
    variant: null
    rules: [ "hard-edged, radius 0, no shadow/border" ]
    provenance: [opening-bookend, about-run]
    confidence: high; source: creation; scope: design-language; changelog: []
  button:
    origin: extracted
    use: never
    rules: [ "brand has no buttons; CTA role remaps to the link primitive" ]
    provenance: [opening-bookend, about-run]
    confidence: high; source: creation; scope: design-language; changelog: []
  link:
    origin: extracted
    use: always
    variant: arrow
    remapFrom: cta
    rules: [ "CTA realized as a typographic arrow link, never a button" ]
    provenance: [opening-bookend, about-run]
    confidence: high; source: creation; scope: design-language; changelog: []
  badge:
    origin: designed
    use: <when>
    designedFrom:
      do:      [ surface-flip-hierarchy ]
      neverDo: [ no-radius, no-shadows ]
      tokens:  [ accent/highlight, text/on-inverse ]
      note: "no badge observed on captured sections; synthesized as a flat square accent-on-dark chip to match the system"
    overridable: true
    confidence: low; source: creation; scope: design-language; changelog: []

blocks:
  header:
    origin: extracted
    slots:
      eyebrow:    { use: optional, note: "margin micro-caption style" }
      heading:    { use: require }
      subheading: { use: optional }
      cta:        { use: optional, note: "arrow link only (see primitives.link)" }
    rules: [ "header centered only in bookend/conversion; editorial runs anchored" ]
    provenance: [opening-bookend, about-run]
    confidence: high; source: creation; scope: design-language; changelog: []

layouts:
  - id: opening-bookend
    archetype: stack
    surfaceIntent: surface/inverse
    slots:
      - { name: "main", role: "display title over layered photo collage", fill: [header, image] }
    gridRules:   { columns: 1, stagger: true, overlap: true, gap: { value: "module" }, confidence: high, source: creation, scope: design-language, changelog: [] }
    widthRules:  { container: "full-bleed", measure: "centered display title; media wide", confidence: high, source: creation, scope: design-language, changelog: [] }
    overlapRules:{ types: [ display-text-over-media, media-over-media ], zOrder: [ media, text ], confidence: high, source: creation, scope: design-language, changelog: [] }
    blockMapping:
      - { slot: "main", role: "display title", contract: "header", usage: { heading: "WOODWAVE GALLERY", case: upper } }
      - { slot: "main", role: "hero photography", contract: "image", usage: { ratio: landscape, radius: "0" } }
    confidence: high
    provenance: [opening-bookend]

compositionRules:
  - id: overlap-primary-ornament
    statement: "Overlap is the brand's primary ornament. Sanctioned types only: display-text-over-media, media-over-media, panel-over-media, media-over-seam."
    value: { sanctioned: [ display-text-over-media, media-over-media, panel-over-media, media-over-seam ] }
    confidence: high; source: creation; scope: design-language
    changelog: [ { ts: "2026-06-12T00:26:00Z", action: created, from: null, to: "4 sanctioned overlap types", by: creation, signalId: null, note: "" } ]

do:
  - { id: typographic-actions, statement: "All actions are typographic — arrow/slash links, never buttons.", value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  - { id: margin-captions,     statement: "Captions live in the margin beside media, as uppercase eyebrows.", value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  - { id: surface-flip-hierarchy, statement: "Carry hierarchy with type size, surface flips, and overlap — not chrome.", value: true, confidence: high, source: creation, scope: design-language, changelog: [] }

avoid:
  - { id: prefer-asymmetry, statement: "Prefer anchored/asymmetric editorial runs; reserve centering for bookend/conversion stacks.", value: true, confidence: medium, source: creation, scope: design-language, changelog: [] }
  - { id: avoid-accent-overuse, statement: "Use the gold accent sparingly and only on dark surfaces.", value: true, confidence: medium, source: creation, scope: design-language, changelog: [] }

neverDo:
  - { id: no-buttons,           statement: "No filled, outlined, or pill buttons — all actions are typographic with arrows/slashes.", value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  - { id: no-radius,            statement: "No rounded corners anywhere (radius globally 0).", value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  - { id: no-shadows,           statement: "No drop shadows, borders, or mats — separation is fill contrast only.", value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  - { id: no-gradients,         statement: "No gradients, tints, or fade transitions between sections — hard cuts only.", value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  - { id: no-text-on-photos,    statement: "No text overlaid on photographs (captions live in the margin). Display title over media in the bookend is the sanctioned exception.", value: true, confidence: high, source: creation, scope: design-language, changelog: [] }

voice:
  ref: "./voice.md"
  dials:
    variance: { value: high, confidence: high, source: creation, scope: design-language, changelog: [] }
    motion:   { value: low,  confidence: medium, source: creation, scope: design-language, changelog: [ { ts: "2026-06-12T00:26:00Z", action: created, from: null, to: low, by: creation, signalId: null, note: "hover inferred, not observed" } ] }
    density:  { value: low,  confidence: high, source: creation, scope: design-language, changelog: [] }

recipePolicy:
  scaffoldFirst:         { value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  reuseBeforeCreate:     { value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  composeFromPrimitives: { value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  themeViaModes:         { value: true, confidence: high, source: creation, scope: design-language, changelog: [] }
  slotsTakeInstancesOnly:{ value: true, confidence: high, source: creation, scope: design-language, changelog: [] }

# OPTIONAL, NON-CANONICAL — consumed only by the DEFERRED Webflow Assembler.
targetMappings:
  webflow:
    site: { name: "AISB v2 - test 1", siteId: "6a2b244f98ab655811c13cc2" }
    tokens:
      colors:
        surface/primary: { mapsTo: "Core Neutral/Neutral Primary", variableId: "variable-a52cdc97", collection: "Brand colors", mode: null, modeId: null, status: mapped }
        surface/inverse: { mapsTo: "Core Neutral/Neutral Inverse", variableId: "variable-fb18c5a3", collection: "Brand colors", mode: null, modeId: null, status: mapped }
        accent/highlight:{ mapsTo: "Core Accent/Accent Primary",   variableId: "variable-737d0293-2c72-7b85-e513-e4e3ba7a79df", collection: "Brand colors", mode: null, modeId: null, status: mapped }
      type:
        display-hero: { mapsTo: "Font/Heading Font", variableId: "variable-Font-Heading", sizeVar: "H0 Heading/H0 Size" }
      spacing:
        section-padding-light: { mapsTo: "Section/Section Padding Vertical", variableId: "variable-Section-Padding-Vertical", status: mapped }
      surfaces:
        surface/inverse: { schemeMode: "Inverse", schemeModeId: "mode-abd1040c-54d0-3fe0-9a11-6840f7051e5a" }
    layouts:
      opening-bookend:
        scaffold:    { component: "Section / Stack", componentId: "185a3d3a-0806-d61b-7c06-c5fdd636b093" }
        surfaceMode: { mode: "Inverse", modeId: "mode-abd1040c-54d0-3fe0-9a11-6840f7051e5a" }
        components:
          - { slot: "main", role: "display title",   component: "Heading", componentId: "b2fd0399-aede-b4e1-bd06-56c8171fc86e", props: { Tag: "h1", Style: "display", Text: "WOODWAVE GALLERY" } }
          - { slot: "main", role: "hero photography", component: "Image",  componentId: "abb0f607-d4f3-9dbd-b285-a92cf7e61685", props: { Radius: false, "Aspect ratio": "landscape" } }

provenanceIndex:
  opening-bookend: { url: "https://woodwavegallery.webflow.io", node: "section:nth-of-type(1)", screenshot: "../../../screenshots/woodwave/woodwave.webp#0-1900" }
  about-run:       { url: "https://woodwavegallery.webflow.io", node: "section:nth-of-type(2..4)", screenshot: "../../../screenshots/woodwave/woodwave.webp#about" }
```

## 9. Rendered `brand.md` projection (output of `render_brand_md(brand.yaml)`)

The renderer walks `brand.yaml` deterministically and emits prose. The mapping is
fixed (no model creativity): `brand.snapshot` → "Brand snapshot"; `surfaceGrammar` →
"Surface grammar"; `tokens.colors` → "Color tokens"; `tokens.type` → typography
table; `tokens.spacing` → "Spacing system"; `layouts[]` → "Layout grammar";
`compositionRules[]` → "Composition mechanics"; **`do[]` → "Do", `avoid[]` →
"Avoid", `neverDo[]` → "Never-do"** (three separate sections); `primitives[]`/
`blocks[]` → "Primitive & block rules"; low-confidence entries → "Confidence flags".

```markdown
# brand.md — woodwavegallery.webflow.io   <!-- rendered from brand.yaml v2.0; do not edit -->

## 1. Brand snapshot
WoodWave Gallery is a warm, two-tone editorial system …

## 2. Surface grammar
Two surface roles: surface/primary (cream canvas), surface/inverse (deep warm brown).
Page rhythm: inverse → primary → inverse. Transitions are hard cuts.

## 6. Layout grammar
- Stack (opening-bookend, surface/inverse): full-bleed display title overlapping a
  layered photo collage.

## Do
- All actions are typographic — arrow/slash links, never buttons.
- Captions live in the margin beside media, as uppercase eyebrows.

## Avoid
- Prefer anchored/asymmetric editorial runs; reserve centering for bookend/conversion.

## Never-do
- No filled, outlined, or pill buttons …
- No rounded corners anywhere …

## Primitive & block rules
- `link` (variant: arrow, remap of cta): CTA realized as a typographic arrow link.
- `button` (never): brand has no buttons.
- block `header`: heading required; cta is arrow link only.

## Confidence flags
- MOTION dial: low confidence — hover behavior inferred, not observed.
```

> Renderer contract: every line in `brand.md` is traceable to a `brand.yaml` node;
> `targetMappings` is **not projected** into `brand.md` (it is substrate annotation,
> not design language). A `--check` mode re-renders and diffs; per SIGN-OFF #1 this
> is a **warning only** and never fails a build.

### 9b. "Component recipes" — the style-md recipe surface (fix2 2026-07)

The brand's style markdown carries a **"Component recipes"** section describing each
`recipes:` entry (§4.4e) in prose: its anatomy, variants, and use cases, written in
the brand's own voice so any generator consuming the kit reads recipes as part of the
brand's genre. Genre framing is **descriptive per-brand prose** ("this SaaS brand
opens working sections with a headrail…", "this editorial brand carries a folio-rule
family…") — never a shared genre taxonomy or enum in code.

- **Projection-rendered brand.md** (render_brand_md.py): the section is emitted
  deterministically from the sibling `layout-library.yaml` `recipes:` layer — same
  contract as §17 "Layout patterns".
- **Extraction-summary brand.md** (hand-authored human summary): the Layout Analyst
  writes the section as part of authoring (layout-analyst-skill §recipes) — one
  paragraph or bullet per recipe: anatomy → variants → which sections deploy which
  variant and why.

---

## Appendix B — The two-layer site-generation model (STYLE + BRAND)

The renderer composes a page from **two stacked layers**. Build order is strict:
**STYLE is the base; BRAND layers on top.**

```
  ┌───────────────────────────────────────────────────────────┐
  │ BRAND layer  (runs/<brand>/brand/brand.yaml + brand.md)     │  ← hues + fonts
  │   fills the style's named SLOTS; may override TOKENS it sets │
  ├───────────────────────────────────────────────────────────┤
  │ STYLE layer  (styles/<id>.md)                               │  ← STRUCTURE only
  │   shape · depth · type scale/leading/tracking · density ·   │
  │   color-DEPLOYMENT (not hues) · motion · structural devices │
  └───────────────────────────────────────────────────────────┘
```

- **STYLE (base)** — `styles/<id>.md` (legacy `styles/style-<id>.md` also accepted), parsed by `brand_pipeline/styles.py`.
  Supplies **structure + defaults** and is **brand-agnostic**: it NEVER hardcodes a hue
  or a font family. It references named brand **slots** — `paper`, `ink`, `accent`,
  `font-display`, `font-body`, `font-mono` — plus its core rules under a
  **`## Style definition`** heading and failure modes. The `Style definition` rules are
  **brand-overridable defaults**, not absolute floors. The style also owns a
  **vertical-rhythm / spacing scale**: named rem steps + the step each structural gap
  (section padding, inter-block gap, cluster gap) defaults to. This is the **fallback**
  rhythm — the composer prefers the brand's measured `tokens.spacing` values
  (`section-padding-*`, `module-gap-*`) whenever they exist.

  **A style's machine-consumed values live in a structured YAML FRONT-MATTER block** (the
  authoritative parsed source — deterministic, mirroring how `brand.yaml` is consumed),
  while the **markdown prose body stays as authored design guidance**. Front-matter keys:
  `id`, `layer`, `owns[]`, `never_sets[]`, optional `composes_with[]`; plus the structured
  structure blocks `type:` (`display_min_rem`, `display_vw`, `display_max_rem`,
  `display_leading`, `display_tracking`), `motion:` (`min_ms`, `base_ms`), `radius:`,
  `shape:` (`flat`, `centered`, `single_accent`), `spacing:` (`scale:` map + `*_slot`
  assignments), and `soft_options:` (`{id: {allowed, default}}`). The parser is
  **front-matter-first with a prose-regex fallback**: any field ABSENT from the
  front-matter is still derived from the prose body exactly as before, so a non-migrated
  style file — or a single un-migrated field — loads unchanged. The prose-parsed lists
  (`## Brand slots`, `## Style definition`, `## Invariants`, `## Failure modes`) may also
  be provided as front-matter (`slots:`, `style_rules:`, `invariants:`, `failure_modes:`)
  but are otherwise read from the prose body via the fallback path.
- **BRAND (on top)** — the canonical `brand.yaml`. Fills the style's slots from its
  token values and **wins on any value it explicitly sets**, including a value that
  contradicts a `Style definition` rule.

### Slot mapping (brand.yaml token → style slot)

| slot | brand.yaml source | fallback if brand silent |
|---|---|---|
| `paper` | default page surface bg (`tokens.surfaces."surface/primary".bg`) | near-white `#FCFCFA` |
| `ink` | that surface's `textPrimary` value (`text/on-primary`) | near-black `#111111` |
| `accent` | first `accent/*` color value | `ink` (monochrome — **never invent a 2nd accent**) |
| `font-display` | `tokens.type.display-hero.family` | a serif stack |
| `font-body` | `tokens.type.body.family` (or `control-text`) | a system sans stack |
| `font-mono` | (brand carries none) | `ui-monospace, …, monospace` |

### Precedence (enforced by `styles.merge` + CSS source order + the on-brand gate)

1. **Brand wins on any value it explicitly sets** — colors, fonts, tokens (the *hues*),
   AND any `Style definition` core rule the brand explicitly contradicts.
2. **Style supplies structure + defaults** for everything the brand leaves unset —
   layout structure, shape, depth model, type scale, density, color-**deployment**,
   motion. It is the base the brand layers on top of, NOT an absolute floor. In the
   renderer the style's structural defaults are appended *after* the brand base in **CSS
   source order**; an explicit, more-specific brand override (e.g. a `#sec-0`-scoped
   rule) still wins where the brand commits to one.
3. **There are NO absolute style non-negotiables.** The `Style definition` rules are
   brand-overridable defaults. **The only hard, non-overridable layer is the brand's own
   `neverDo`** (enforced by `onbrand_check.py`); a `neverDo` violation is the only thing
   that fails the gate.

> **The hero `#sec-0` override is the canonical example.** Under `radical-editorial` the
> WoodWave hero is **centered** and its display heading is the single committed **accent**
> (gold) on the brand's dark inverse surface — a deliberate brand-over-style override
> scoped to `#sec-0` (`compose_page.hero_brand_override_css`). The style's `Style
> definition` defaults are *left-anchored, ink-display, asymmetric*; the brand explicitly
> commits to the opposite for the hero, so the brand wins there. The on-brand gate
> (`onbrand_check.py --style`) detects this documented override and reports it as an
> **INTENTIONAL OVERRIDE (blessed, logged)** rather than a failure. Every non-hero section
> still follows the style defaults (or is itself an advisory `WARN` if it deviates with no
> backing brand override — never a hard fail). The brand still owns *what* each hue is; the
> style only contributes *where/how* hues are deployed by default.

### Pipeline wiring

- `brand_pipeline/styles.py` — `load_style(id)`, `brand_slots(doc)`, `merge(style, doc)`
  → a `RenderContext` (style **structure** + brand **slot values**). Inspect a merge:
  `python3 brand_pipeline/styles.py <style-id> <brand.yaml>`.
- `brand_pipeline/render_hero_variants.py --style <id>` — applies the structure
  (poster-scale type in `cqw`, 0 radius, flat, asymmetric, slow motion, single committed
  accent) over the brand hues/fonts. Omitting `--style` preserves current behavior.
- `brand_pipeline/onbrand_check.py --style <id>` — ALSO reports the style's
  `Style definition` core rules (poster scale, flat/no-card/no-shadow,
  asymmetric-not-centered, single accent, container-query-units-only) as
  **brand-overridable defaults** alongside the brand `neverDo` checks. Each style row is
  PASS, **OVERRIDE** (a documented brand override blesses the deviation — e.g. the hero
  `#sec-0` centered / accent-gold exception, logged as intentional), or **WARN** (an
  advisory deviation with no backing override). Style rows are advisory and **never flip
  OVERALL**; only the brand `neverDo` (+ fidelity/slop) layers gate the build.

---

## 4.4 `layout-patterns.v1` — reusable USE-CASE layout patterns (NEW)

`scaffolds.yaml` gives the STRUCTURAL vocabulary (`stack`/`split`/`grid`/`bento`…) and
`layouts[]` (§4.2) records THIS page's concrete sections. Neither is **use-case-keyed** or
**reusable across projects** — so every hero/pricing/etc. is re-derived from scratch. The
**layout pattern** is the missing middle tier: a reusable, use-case-keyed recipe that
REFERENCES a scaffold archetype and captures the *content-shape signature* (text lengths,
text↔media size relationships, ghost/watermark words, overlap/stagger treatments) as a
PATTERN — never a px-literal copy.

```
scaffold (structural shell)  ◀── archetypeRef ──  LAYOUT PATTERN (use-case recipe)  ──▶  layouts[] instance
contracts/scaffolds.yaml                          contracts/layout-patterns/*.yaml (standard)     brand.yaml
                                                  runs/<brand>/brand/layout-library.yaml (project)  layouts[].patternRef
```

A pattern file (one per use-case). Same schema for the standard library and each project
library — only `origin` differs (standard = `designed`, project = `extracted`, §5.2):

```yaml
schemaVersion: layout-patterns.v1
useCase: hero            # hero|features|pricing|testimonial|gallery|cta|about|faq|logos|footer
patterns:
  - id:            <slug>                    # unique within its library, e.g. hero-ghostword-staggered
    useCase:       hero
    archetypeRef:  stack                     # -> contracts/scaffolds.yaml archetype (structural)
    surfaceIntent: any|primary|inverse|inverse-strong|panel   # project patterns may pin one
    intent:        "<one-line description of the signature>"

    # CONTENT-SHAPE SIGNATURE — the fine-grained capture (relationships/classes, NEVER px)
    contentShape:
      # ALIGNMENT-COHERENCE (REQUIRED whenever any slot in the pattern is centered).
      # Captures NOT JUST the block's alignment but whether SIBLING slots inherit it —
      # this is the single most-missed class of extraction gap: a `variantKnobs.align`
      # choice was recorded but never wired to actually center sibling slots or share a
      # measure, so the render silently drifted from the source (WoodWave conversion-
      # stack: heading centered, but body/form stayed left-anchored/full-width until an
      # iteration signal caught it against the reference).
      alignment:
        value:       centered|left|right|space-between|edge-to-edge|mixed   # ('center' accepted, normalizes to 'centered'; 'space-between' was previously dropped as out-of-enum — AS-18)
        counterweight: <named slot or device>   # REQUIRED for an asymmetric (left/right) anchor: the thing that fills the opposite side
        inheritance: block-inherits|per-slot-override
        rule: >-
          NOT UNIVERSAL — state the actual behavior observed, per pattern family:
          - CTA/conversion-type blocks: a centered heading conventionally implies EVERY
            sibling slot (body, form/control) is ALSO centered AND shares the SAME
            measure as the body text (a control/form slot must NOT default to full
            column width — see the `width`/`sizeRel` requirement below).
          - Section-level HEADER blocks (an intro heading over a longer body run,
            hero-style): a centered heading does NOT imply the body run is centered —
            declare `width`/alignment per-slot instead of inheriting.
      slots:
        - name:       <slot>
          role:       <semantic role>
          textLen:    none|word|short|medium|long   # short≈eyebrow(≤6w) · long≈body(>40w)
          sizeClass:  colossal|hero|display|title|body|caption|control
          sizeRel:    { to: <otherSlot>, ratio: <num>, axis: width|height }  # relative size link
          width:      hug|stretch|fixed|media|full-bleed                     # harvest width class
          mediaAspect:portrait|landscape|square|freeform                     # media slots
          mediaScale: { of: container|slot, fraction: <0..1>, gap: <CSS len>,  # media slots; optional MEASURED inter-item gap (rem/em/px) for mark rows
                        item: { width: <CSS len>, height: <CSS len> } }        # optional MEASURED per-mark box (fix2): the strip's own item size at the canonical tier — when present the renderer locks mark height/width to the measurement instead of deriving size from fraction/flex weights (whose viewBox padding skews artwork scale)
          opacityClass: solid|tint|ghost                                     # for watermark/ghost slots
          z:          back|mid|front

      # MEASURED STACK FACTS (optional, additive — source: computed only; JS-off
      # geometry against the capture, recorded in resolution-independent units):
      #   stackMeasure: { value: <CSS len>, source: computed }   # the centered stack's
      #     content-column cap (e.g. a closing band whose heading AND body span a
      #     measured 870px column — the composer sizes the column at the brand's real
      #     measure instead of the structural default, and the body spans it).
      #   bandPadding: { top: <CSS len>, bottom: <CSS len>, source: computed }  # the
      #     band's own measured vertical padding when it diverges from the brand's
      #     site-average section-padding token (bookend bands often breathe more).
      #   deviceGeometry:              # measured device-band proportions (fid9) —
      #     headerPlacement: list-column   # header stack = first row of the list column
      #     columns: equal                 # equal split columns (vs the structural 6|5)
      #     contentSpan: <CSS len>         # band content max-width when it diverges
      #     columnGap: <CSS len>           #   from the brand's container token
      #     rowGap: <CSS len>              # header row -> device row gap
      #     media: { aspect: "<w / h>", align: top }   # fixed-aspect media region,
      #     list: { triggerMinHeight: <CSS len>, itemGap: <CSS len> }  # list rhythm
      # All degrade to absent — composers keep their structural defaults.

      # CONTROL-MEASURE REQUIREMENT: any slot with `sizeClass: control` (a form/input/
      # button row) MUST carry an explicit `width` or `sizeRel` — never leave it
      # unspecified. Unlike a paragraph, a control has no natural "measure" behavior of
      # its own; an unspecified control silently defaults to stretching the full
      # container in the renderer, which is how this class of bug happens. Prefer
      # `sizeRel: { to: body, ratio: 1.0, axis: width }` (matches the body's measure)
      # over a bare `width: stretch` unless the source genuinely shows edge-to-edge.

    # SPECIAL TREATMENTS — the signature devices (kind-specific fields)
    specialTreatments:
      - { kind: ghost-word, target: <slot>, anchor: behind-media|straddle-media|margin|full-bleed, bleed: none|partial|full }
      - { kind: overlap,    pair: [<slotA>, <slotB>], zOrder: [<slot>…], amount: { class: light|medium|heavy } }
      - { kind: stagger,    target: <slot>, axis: vertical|horizontal, amount: { class: light|medium|heavy } }
      - { kind: bleed,      target: <slot>, edge: left|right|top|bottom|all }
      - { kind: marginal-caption, target: <slot>, side: left|right }
      - { kind: scroll-parallax, target: <slot>, mode: mask-pan|depth, amount: { class: light|medium|heavy } }

    responsive:
      collapse:   stack-below-tablet|reflow|none
      mediaFirst: true|false                 # source-order flip at narrow widths
      # optional per-slot narrow-width overrides, e.g. ghostwordAt: { base: colossal, mobile: hidden }

    variantKnobs:                            # what a generator may tune WITHOUT leaving the pattern
      <knob>: { type: string|enum, values: [...]|from: [...], default: <val> }

    # ORIGIN / PROVENANCE — mirrors §5.2 exactly
    origin:     extracted|designed
    provenance: [<sectionId>…]               # REQUIRED when origin=extracted
    # origin=designed -> designedFrom: {...}; overridable: true   (REQUIRED when designed)
    confidence: high|medium|low
    source:     creation|iteration|failure
    scope:      design-language|one-off
    changelog:  [ { ts, action, from, to, by, signalId, note } ]
```

> **Why relationships, never px.** `sizeRel`, `mediaScale`, `amount.class`, and the
> `textLen`/`width` classes resolve at generation time against the merged STYLE spacing/
> type scale (`styles.py` `StyleStructure.space_scale`) + brand `tokens`. So one pattern
> adapts to any brand's rhythm and type scale — it stays brand-agnostic and does not
> overfit one source page. This is what makes a pattern REUSABLE rather than a replica.

### 4.4b `layoutGrammar.headerContext` — contextual header-alignment grammar (fid11)

Per-pattern `contentShape.alignment` facts record WHERE each observed section anchors —
but sources typically also carry a *system* behind those choices: ONE header component
(kicker/eyebrow/icon/tag optional + heading + subheading optional + actions optional)
whose alignment is decided by its **layout context**, not per-section whim. When the
observed patterns corroborate a contextual rule, author it as a top-level brand block:

```yaml
layoutGrammar:
  headerContext:
    splitColumn:                       # header sits inside a column of a split row
      anchor: left|centered|right
      counterweight: <device>          # optional; same rule as patterns — an asymmetric
                                       # anchor should name what fills the opposite side
                                       # (author it when the observations corroborate one)
      evidence: "<which observed patterns/rules corroborate it>"
    standaloneStack:                   # header stands alone atop a stack/grid section
      anchor: left|centered|right
      evidence: "<…>"
    confidence: high|medium
    source: [saved-css, vision, computed]
    scope: design-language
```

Rules:

- **Derivation is measured, generic, and majority-honest.** Each observed section's
  layout context is known (split vs standalone stack/grid); the header's computed
  alignment in each is the evidence. Author a context rung only when its observations
  agree; a context with mixed evidence stays un-authored (the per-pattern facts already
  carry those sections). Cite dissenting patterns in `evidence` — an explicit pattern
  fact outranks this grammar by resolution order, so exceptions are not contradictions.
- **Validator (C18):** when the observed pattern library corroborates both contexts
  (≥2 split patterns agreeing and ≥2 standalone stack/grid patterns agreeing), the
  grammar MUST be authored — fail loud, same doctrine as C15.
- **Consumption (AS-49):** `resolve_alignment` consults this grammar as the
  brand-default layer BENEATH explicit facts:
  `section alignment > pattern curation (generation lanes, §4.4c) > pattern
  contentShape.alignment > layoutGrammar.headerContext > style role default`. The
  resolved stance stamps `data-align-source="brand"`. This is exactly the layer newly
  GENERATED sections need: a novel pattern with no alignment fact inherits the brand's
  grammar instead of a scaffold-hardcoded anchor.

### 4.4c pattern `curation` — a curator's ruling on a fact-vs-grammar dissent (fid13)

Sometimes a source dissents from its own grammar: a pattern's measured fact is REAL
(re-verified against the capture) yet a human design curator rules that OUR generated
output should follow the brand's corroborated grammar instead — "the original looks
strange here." That ruling is recorded on the pattern as a first-class block, never by
editing the measured fact:

```yaml
patterns:
  - id: <pattern-id>
    contentShape:
      alignment: { value: left, ... }   # the MEASURED fact — never rewritten by curation
    curation:
      alignment:                        # aspect key mirrors the fact it rules on
        resolve: follow-grammar         # the only defined resolution today
        by: user                        # who ruled (user | creation)
        ts: "<ISO timestamp>"
        reason: "<the curator's words / rationale>"
    changelog:
      - { ts: ..., action: curated, ... }   # the ruling is a changelog event too
```

Rules:

- **Lane semantics.** GENERATION lanes (composed catalog, event/wildcard pages, preview
  demos) resolve through the curation: `follow-grammar` retires the pattern's dissenting
  fact and hands the decision to `layoutGrammar` (the winning stance stamps
  `data-align-source="curation"`). The REPLICA lane passes `honor_curation=False` — it
  rebuilds the source 1:1 and its gate scores against the source, so the measured fact
  stays that lane's truth. A curation must therefore NEVER move the replica gate score.
- **Precedence (AS-49).** `section explicit > curation > pattern fact > grammar >
  style`. Curation beats the pattern's own fact (that is its whole job) but never a
  section-explicit instruction: a composition author's direct `alignment:` knob remains
  supreme. If no grammar rung covers the pattern's context, the retired fact is still
  skipped (falling to the style layer) — silently reverting to a look the curator
  rejected would be worse than the default.
- **The fact survives.** `contentShape.alignment` keeps the measured value with its
  re-measurement changelog; curation is an overlay, so re-extraction, the replica lane,
  and future audits still see the source's truth.
- **Validator (C18).** A dissent with a recorded curation downgrades from the advisory
  WARN to an informational NOTE ("dissent curated toward grammar") — review is done;
  uncurated dissents keep warning until verified or curated.
- **Chrome facts curate the same way (fix5 2026-07).** The mechanism is not
  pattern-only: a measured CHROME fact can carry a curator's ruling under its own
  `curation` key with the same lane semantics. First instance:
  `navbar.measured.trigger.chevron.curation.motion: { resolve: instant, by, ts,
  reason }` — the user ruled the open-state chevron flip must swap instantly in
  generation lanes; `component_render.nav_affordance_css(doc, honor_curation=…)`
  honors it (transition: none) while the replica keeps the measured tween
  (`transform 0.3s`/`0.2s` stay the facts' evidence truth). Same invariants: the
  measured fact survives untouched, and the curation never moves the replica score.

### 4.4d `contentShape.gridEqualize` — card-row height behavior (fid14)

Whether a card grid equalizes card heights per row is a measurable SOURCE fact, and the
anatomy that makes equalization work travels with it — equalizing without knowing where
the slack goes produces floating CTAs mid-card (AS-50). Every observed card-grid
pattern (grid / cards / mosaic archetypes) records the stance on its `contentShape`:

```yaml
patterns:
  - id: <card-grid pattern>
    contentShape:
      gridEqualize:
        heights: stretch        # stretch (row-equalized) | hug (content-sized)
        slack: body             # the card-internal region that absorbs the extra
                                # height (the source's flex-grow:1 slot) — a generic
                                # anatomy name (body | media | quote), never a
                                # source class name
        actionPinned: true      # does the trailing action/author row anchor to the
                                # card bottom (margin-top:auto seam, or a flexing
                                # region above it — same morphology)
        evidence: "<the JS-off @1440 measurement: per-card heights with differing
                    content, the flex-grow slot, the pinned row>"
```

Rules:

- **Measure, don't infer.** `heights: stretch` requires cards of DIFFERING natural
  content rendering the SAME height (equal heights with equal content proves nothing).
  Cross-check at least two grid families where the corpus offers them.
- **The trio travels together.** `heights` without `slack`/`actionPinned` is an
  incomplete observation — the renderer needs all three to reproduce the morphology
  (stretch alignment, slack absorption, bottom-pinned actions).
- **Not observable?** Mark `contentShape.gridEqualizeNotObserved: true` (e.g. the
  capture never shows the grid with uneven content and no flex anatomy is inspectable).
- **Consumption.** Pattern-backed grids render per the fact
  (`compose_section.pattern_equalize_css`); the pattern-less generated card scaffolds
  (bento mosaic, pricing tiers) consume the BRAND grammar derived from these facts
  (`grid_equalize_grammar`: all-hug ⇒ hug, any-stretch ⇒ stretch, no facts ⇒ built-in
  behavior unchanged). Fact-less brands are byte-identical (degrade discipline).
- **Validator (C20).** A card-grid pattern with neither `gridEqualize` nor the
  not-observed marker is an extraction gap — error.

### 4.4e `recipes:` — brand-owned COMPONENT RECIPES (fix2 2026-07)

A **recipe** is a named recurring component anatomy the brand itself repeats across
sections: the same ordered slots, restyled per context. Patterns capture one section's
shape; a recipe captures the SHARED anatomy several patterns instantiate (e.g. a
section-opening head rail: identity kicker + dotted leader rule + far-edge quiet CTA,
seen as an icon chip on one band, a label pill on another, a badge on a third). Missing
this layer is how three sections sharing one component get re-derived three times with
three sets of small errors.

Recipes are **brand data, written during extraction** — they live in the brand's own
`layout-library.yaml` under a top-level `recipes:` key (sibling of `patterns:`), never
in shared code or the standard library. The grounding pass names anatomies seen in 2+
crops; the Layout Analyst records the recipe; patterns bind to it via `recipeRef`.

```yaml
recipes:
  - id: <slug>                       # e.g. section-headrail — generic anatomy name,
                                     # NEVER a section/content name (no "agents-rail")
    name: "<human name>"
    intent: "<one-line: what the anatomy is and where the brand deploys it>"
    anatomy:                         # ordered slots (generic roles)
      - { slot: kicker,  role: leading identity mark (chip/pill/badge), required: true }
      - { slot: rule,    role: leader line joining kicker to the far edge, required: false }
      - { slot: trail,   role: far-edge quiet action, required: false }
    geometry:                        # shared MEASURED facts (source: computed)
      railAlignment: content         # the anatomy spans the CONTENT container (or: column)
      railToHeading: <CSS len>       # seam to the following element, when measured
    variants:                        # each variant = one observed styling of the anatomy
      - id: <slug>                   # e.g. icon-chip / label-pill / badge-with-icon
        useCase: "<when the brand picks this variant>"
        kicker: { shape: chip|pill|badge, radius: <CSS len>, size: <CSS len>,
                  icon: { asset: <file>, size: <CSS len> },   # optional identity icon
                  label: true|false }                          # text label present?
        rule:  { style: dotted|solid|none }
        trail: { present: true|false }
    usedBy: [<pattern id>…]          # the patterns instantiating this recipe
    origin: extracted                # recipes are observed, not invented
    provenance: [<sectionId>…]
    confidence: high|medium|low
    changelog: [ { ts, action, from, to, by, signalId, note } ]
```

Patterns bind with a top-level key on the pattern mapping:

```yaml
patterns:
  - id: <pattern>
    recipeRef: { recipe: <recipe id>, variant: <variant id> }
```

Rules:

- **Record during extraction, not post-hoc.** Detecting recurring anatomy across
  sections is a REQUIRED authoring step (layout-analyst-skill §recipes); the C23
  validator advisory is the backstop for patterns sharing a rail-like slot signature
  with no recipe.
- **Generic anatomy names.** Slot and variant ids describe shape (`icon-chip`,
  `label-pill`), never the section or content they appeared in.
- **Facts ride the recipe, styling stays per-variant.** Shared geometry (alignment
  span, seams) lives once in `geometry:`; per-context looks (chip vs pill, icon size,
  rule style, trailing action presence) live in the variant the pattern binds.
- **Consumption + degrade.** Composers resolve `recipeRef` via
  `layout_library.resolve_recipe_ref` and render the variant's measured facts; a
  pattern with no `recipeRef` (or a dangling id) keeps the structural device
  unchanged.
- **Style surface.** Each recipe is ALSO described in prose in the brand's style md
  ("Component recipes" section — §9b): anatomy, variants, use cases, in the brand's
  own voice, so any generator consuming the kit reads recipes as part of the brand's
  genre (a SaaS brand may lead sections with a headrail; an editorial brand may carry
  a folio-rule family instead). Genre framing is descriptive per-brand prose — never
  a shared enum in code.

### 4.4f `contentShape.actionGroup` — measured action-row layout facts (fix2 2026-07)

How a brand lays out a MULTI-ACTION row (primary + secondary CTA pair, card action
rows) is a measured fact family, not a scaffold habit: inter-action gap, orientation,
wrap behavior, alignment, the seam above the row, and the register composition. The
scaffold's uniform defaults (1em gap, reading-edge alignment) survive ONLY as the
no-facts degrade.

Brand-level default (brand.yaml, sibling of `layoutGrammar.headerContext`):

```yaml
layoutGrammar:
  actionGroup:
    gap: <CSS len>                  # measured inter-action gap (flex gap)
    orientation: row|column
    wrap: wrap|nowrap
    align: start|center|end         # alignment INSIDE the group's context; contexts
                                    # with their own anchor (centered bands) still win
    crossAlign: start|center|end|stretch  # OPTIONAL measured cross-axis placement;
                                    # absent = the scaffold's structural align-items
                                    # (center) holds — only author when the source
                                    # computably deviates (fix3)
    marginAbove: <CSS len|ladder>   # seam from the preceding body/heading; `ladder`
                                    # = ride the relational rung (--space-body-to-cta)
    registers: [primary, secondary] # observed register order (AS-59's subject)
    source: computed
    provenance: [<sectionId>…]
```

Per-pattern override (layout-library.yaml, when one band measures differently):

```yaml
patterns:
  - id: <pattern>
    contentShape:
      actionGroup: { gap: <CSS len>, align: <enum>, marginAbove: <CSS len> }  # partial OK
```

Rules:

- **Computed provenance.** Values come from JS-off computed geometry (flex gap,
  justify-content, margin seams) at the canonical tier — vision estimates don't
  qualify for the fact (they inform, the measurement decides).
- **Consumption.** `compose_section` emits the brand default as the action-row law
  and stamps each emitted group with its declared facts
  (`data-ag-gap`/`data-ag-align`); per-pattern overrides re-stamp per band. The
  spacing auditor measures `actions.item-gap` / `actions.alignment` as first-class
  relationships; AS-60 flags a rendered group whose computed gap/alignment
  contradicts its own stamped declaration (scaffold-habit override).
- **Alignment ownership (fix3).** A declared `align` claims the main-axis placement
  property itself: the law emits `justify-content` on every emitted group (brand
  default page-wide at 0-1-0; a pattern override per `#sec-N` at 1-1-0). Anchor-
  owning contexts (`.cs-foot`, `[data-align="centered"]`, panel-center) still win
  by specificity — the sanctioned exception. Box-level centering (`max-width` +
  `margin-inline: auto`) is NOT an alignment channel: the containment law owns the
  box (a contained group spans its column via `width: 100%`, so auto margins are
  structurally inert — the fix3 centering-leak vector closed by construction, see
  spacing-conformance §Container law). `crossAlign` claims `align-items` the same
  way, and ONLY when declared: the structural cross-axis default (`center` —
  vertically centering unequal-height actions, which the captured sources bear) is
  not a fact and stays scaffold-owned.
- **Degrade.** No facts ⇒ no stamps, no law emission — the structural defaults hold
  byte-identical.

### 4.4.1 `scroll-parallax` — the motion rule for editorial/collage-style sites

Captured from a live site's Webflow IX2 scroll interaction (`.about-second-img-wrp`: a
masked wrapper whose inner `<img>` translates vertically, scroll-scrubbed — observed as
different `translate3d(0, Ypx, 0)` values at different scroll depths on the SAME element).
This is a **brand-level MOTION TREATMENT**, not a one-off per-image hack: it is declared
ONCE (`brand.yaml voice.motionSpec.imageParallax`) and applies to every module image the
composer renders, the same way `do[]`/`neverDo[]` apply globally rather than per-section.

**Two modes**, both driven by the SAME brand toggle + `amount.class` (light/medium/heavy,
resolved to a `yPercent` range — never px, so it is breakpoint/resolution-safe):

- **`mask-pan`** — a SINGLE image inside an `overflow:hidden` wrapper pans vertically
  within its own frame as the page scrolls. Requires the image to be visually oversized
  (CSS `transform: scale(...)`, never a larger intrinsic asset) so the pan never reveals
  empty space at the mask's edge. Applies to any module-photo slot (the editorial-
  collage/heritage-timeline/mission-statement/curator-quote/visit/gallery media — every
  slot whose `width` is `media` and is NOT part of an `overlap` special treatment).
- **`depth`** — the MOTION counterpart of an existing `overlap` special treatment between
  two MEDIA slots (e.g. the hero's media-over-media collage): the two images move at
  DIFFERENT rates during scroll so the overlap visibly deepens/shifts rather than sitting
  static, reinforcing the depth cue the overlap already implies structurally. NO mask —
  overflow stays visible, since the crossing between the two images IS the intended
  effect; masking would clip it. Applies ONLY to the MEDIA pair inside an `overlap`
  treatment, never to a text-over-media overlap (a display title over its photo stays
  static; only the photo LAYERS get differential rates).

> **Reuse-before-invent**: `depth` mode is not a new capture — it rides on the `overlap`
> treatment's existing `pair`/`zOrder` data. When extracting a NEW site with overlapping
> photo pairs, do not invent a separate motion-only record; add `scroll-parallax` mode
> `depth` referencing the SAME `pair` the `overlap` treatment already names.

```yaml
# brand.yaml voice.motionSpec — the single brand-level toggle (mirrors easing/durations)
voice:
  motionSpec:
    imageParallax:
      enabled: true
      amount: light          # light|medium|heavy — the brand's own voice.dials.motion wins
      mask: true               # informational: mask-pan mode requires overflow:hidden
      origin: extracted
      provenance: [<sectionId>…]
```

`enabled` defaults to `false` when the brand is silent — this is opt-in per project, never
a global default; a brand that never extracted this treatment renders byte-identical to
before. `amount` should agree with the brand's locked `voice.dials.motion` — a brand
locked to `motion: low` gets `amount: light`, never `heavy`.

**Render-side (generation)**: implemented ONCE in `component_render.py`
(`image_parallax_spec`, `parallax_css`, `parallax_script_tags`) and consumed by BOTH
`compose_page.py` and `compose_section.py` — never hand-duplicated per builder (see
`compose_page.page_style_override`'s docstring for why that class of drift is dangerous).
Uses GSAP + ScrollTrigger (CDN, opt-in-loaded only when `imageParallax.enabled`), respects
`prefers-reduced-motion: reduce` (skips entirely, matching the existing scroll-reveal
script's discipline), and never uses viewport units (container-query-safe `yPercent`).

## 5.5 The two-tier layout library (standard base + project override)

Exactly the STYLE+BRAND model (Appendix B), applied to layouts:

| library | path | tier | `origin` | authored by |
|---|---|---|---|---|
| **standard** | `brand_pipeline/contracts/layout-patterns/<useCase>.yaml` (+ `index.yaml`) | base (like STYLE) | `designed` (blessed, `overridable: true`) | hand-blessed from `harvest_patterns.py` output |
| **project** | `runs/<brand>/brand/layout-library.yaml` | override (like BRAND) | `extracted` (this project's real sections) | the Layout Analyst, per run |

- The standard library is a shared, deliberately-general base of use-case recipes so a new
  section starts from a close match instead of blank HTML/CSS.
- The project library accumulates THIS project's unique layouts (e.g. WoodWave's colossal
  ghost-word hero) across runs — **append/reconcile, never overwrite** (§2 envelope: agreeing
  `extracted` observations raise confidence / may promote `one-off`→`design-language`;
  conflicting ones land `one-off` and queue a signal).
- The **origin ratchet** (§5.3) spans the two libraries: a standard pattern truly observed in
  a project is promoted INTO the project library as `extracted`, never the reverse.
- `runs/*/single/layouts.yaml` (`source_layouts.v1`) is unchanged — it is only the harvest
  FEEDSTOCK for seeding the standard library, still `do_not_use_as_design_system`.

## 5.6 Genre archetype libraries (`contracts/archetypes/*.yaml`) — structure above the pattern tiers

A THIRD structural tier sits above §5.5 (normative spec: `spec/archetype-library.md`;
first genre: `contracts/archetypes/heroes-saas.yaml`, `hero-archetypes.v1`): genre
structural vocabulary — skeletons a competent designer knows that the SOURCE SITE never
had to show. The law is **style-invariant / structure-variable / physics-hard**:
instantiation draws every visible property from the brand's extracted facts; only the
skeleton comes from the library; the physics fact families named by the archetype's
`physicsBindings` bind exactly as in replica mode.

Wiring (phase-2 2026-07, all fact-gated so refless lanes stay byte-identical):

- **Selection** — `archetype_library.shortlist()` filters by the brief's
  `pageType`/`taskIntents` (brief frontmatter or caller kwargs) and injects 2–3
  candidates into the generation prompt (`generate_composition.build_prompt
  hero_candidates`) ONLY when the run has off-grid expansion. The composition records
  the choice as the OPTIONAL section key `archetypeRef` (composition.v1).
- **Instantiation** — `compose_from_composition.adapt_brand_section` normalizes the
  section against the archetype FIRST (family, variantKnob defaults, `knobs.bandHeight`
  from the archetype geometry), THEN runs brand adaptation — so brand recipes/tokens
  win by ordering, not by special case. Unknown ids or unresolvable physics families
  strip the ref (fail closed to the brand's own evidenced anatomy) with a note on
  `layout._archetypeNotes`.
- **`knobs.bandHeight`** (`compact|standard|tall`; `viewport` degrades to `tall`) —
  the archetype's band character re-registers the section's vertical padding to the
  NEAREST rung of the brand's OWN `section-*` spacing family
  (`compose_section.band_height_css`, emitted as a `var(--space-…)` layer-1 reference).
  The knob never invents a length; no rung in the wanted direction → standard rhythm.
- **Audit** — the rendered wrapper stamps `data-archetype` (like `data-pattern`);
  `onbrand_check` adds HARD `archetype-physics:<section>` rows mapping each bound
  family to the row that verifies it (families owned by sibling gates are reported
  `delegated[...]` and enforced by the lane runner: spacing_audit, slop_audit,
  interaction_audit). Two source-identity fidelity cells re-scope on stamped renders
  (creative-mode scope): the section surface must be one of the brand's OWN surface
  roles (not necessarily the source layout's), and authored display copy replaces the
  source-heading-snippet check.
- **Precedence** — brand recipes WIN over archetype anatomy wherever both describe the
  same role (§5.3 ratchet extends: extracted > designed > genre-designed).

## Appendix C — Layout precedence & retrieval (parallel to Appendix B)

Resolution is a near-mirror of `styles.py` (`brand_pipeline/layout_library.py`):
`load_standard_patterns(useCase)` (base) + `load_project_patterns(brand.yaml)` (override) →
`resolve_library(useCase, brand.yaml)` → candidates ordered **PROJECT-FIRST**.

**Retrieval** — `match(query)` where `query = {useCase, contentShape (observed slot
text-lengths / media aspect / has-ghost-word), brandRules (neverDo ids), surfaceIntent}`:

```
score = useCaseGate(0|1)                 # wrong use-case → discarded
      + wArchetype·archetypeCompatible
      + wSlots·slotShapeSimilarity        # slot count + textLen-class overlap (short/long)
      + wSizeRel·sizeRelConsistency       # query text↔media size ratios vs pattern's
      + wTreatments·treatmentOverlap      # ghost-word / overlap / stagger presence match
      + wSurface·surfaceCompat
      + LIB_BIAS if lib == project        # PROJECT WINS on ties → enforces precedence
      − ∞ if any specialTreatment violates a brand neverDo   # hard filter (brand-safe)
```
Result `matchKind`: `reuse` (score ≥ REUSE), `adapt` (nearest + tuned `variantKnobs`), or
`miss` (invent, then PROMOTE the new pattern into the project library).

Precedence rules (the only hard gate is still the brand's own `neverDo`, like Appendix B):
1. **Project patterns win** — an equal-or-better project match always beats a standard one.
2. **Standard supplies the base** — used when the project library has no adequate match.
3. **Brand `neverDo` is the hard gate** — a pattern whose treatments would violate a
   `neverDo` (e.g. WoodWave `no-text-on-photos`) is filtered out before scoring.

## 10. Extraction OUTPUT CONTRACT — validator conventions (Path-2, 2026-07)

A brand evidence folder (`runs/<brand>/brand/`) is DONE only when
`tools/extract/validate_brand_evidence.py` passes (checks C1–C15). The validator encodes
repo-observed failure shapes (a missing `section-copy.yaml` rendering every section as
wordmark+arrow; a single stretched button variant; a logo wall with zero logo files; a
`legal.copyright` key the composers cannot see) as hard contract errors. This section
records the schema-side conventions those checks rely on; the evidence-first authoring
method that PRODUCES them is `spec/layout-analyst-skill.md`.

### 10.1 `blocks.<type>.notObserved` — explicit absence (C2)

Every block key in `contracts/blocks.yaml` is either populated with evidence or marked
`notObserved: true` (§5.1). Silence is a contract violation: an unmarked gap cannot be
distinguished from an extraction miss, and `card` is historically the block this bites.

### 10.2 `buttons:` — the measured action-style family matrix (C3)

`buttons:` records EVERY observed action style as its own family, each with a usable
state matrix. Family names are generic action tiers (`primary` / `secondary` /
`tertiary` / `textCta` — never section- or content-specific names):

```yaml
buttons:
  renderHint: { useFilledButton: true|false, note: "<one-liner>" }   # optional dispatch hint
  <family>:                       # primary, secondary, tertiary, textCta, …
    style:     filled|outline|filled-neutral|text-link-arrow|…
    bg:        "<hex|transparent>"    # fill (filled/outline families)
    fg:        "<hex>"                # label ink
    border:    "<css border|null>"
    radius:    "<css length>"         # REQUIRED — pill vs square is brand identity
    padding:   "<css shorthand>"
    font:      "<family>"; weight: <int>; sizeRem: <number>
    bgHover:   "<hex>";  bgPressed: "<hex>"   # state facts — at least ONE state fact
    fgHover:   "<hex>";  focus: "<prose>"     # (bgHover/fgHover/decoration/focus) REQUIRED
    decoration: "<prose>"             # text families: idle/hover decoration behavior
    glyph:                            # OPTIONAL (fix2): the family's MEASURED trailing
      asset: <file in assets/>        # glyph as a real harvested SVG (sprite symbol /
      size: <CSS len>                 # inline path from the capture) + its rendered
      source: computed                # box. When present the arrow-link device renders
                                      # the SVG instead of the Unicode fallback; hover
                                      # motion is unchanged.
                                      # No glyph fact -> Unicode degrade, byte-identical.
                                      # RENDERING CONTRACT (fix4 2026-07): single-color
                                      # glyph facts (this glyph, nav chevrons/utility
                                      # icons, footer social icons, banner arrow/close)
                                      # emit SANITIZED INLINE <svg> markup — script/
                                      # foreignObject/event-attrs/external refs stripped,
                                      # xmlns+viewBox guaranteed, width/height dropped
                                      # (CSS owns the box), ids deduped per instance,
                                      # ink normalized to currentColor ONLY after
                                      # single-ink verification. Artwork that fails
                                      # verification (multi-color/gradient/<style>)
                                      # keeps the fix2 data-URI currentColor-mask
                                      # channel under a `--mask` modifier class —
                                      # never a silent recolor. The fact schema is
                                      # unchanged; only the emission technique moved.
    confidence: …; source: …; provenance: […]
  singleVariantConfirmed: true      # ONLY after re-checking evidence: the source truly
                                    # carries ONE action style (C3 otherwise fails a
                                    # one-family matrix — sites almost always have ≥ 2)
```

C3-STRICT pairing + geometry (sysfix 2026-07):

- A family measuring `bgHover` MUST also measure `fgHover` — the label's hover ink is a
  state fact, not a default. When the label truly does not change, record the same hex
  (or an explicit "unchanged" note); silence leaves the renderer guessing mid-state
  contrast.
- A FILLED family (`style: filled*`, or an opaque `bg`) MUST measure `height` and
  `padding` — control geometry is brand identity (pill h48 vs squat h36), never a
  renderer default.

Layer 1 (`tokens_css.py`) emits `--button[-<family>]-*` custom properties from the
`primary`/`secondary`/`tertiary` families; `textCta`-style families drive the arrow-link
device. Absence of `buttons:` entirely = the typographic-CTA structural variant.
A composition slot whose evidence prose names an outline/ghost/quiet treatment selects
the family whose `style:` fact matches (component_render.button_family_for_style) — the
`style:` word is therefore normative vocabulary, not a free-text note.

### 10.3 `footer.legal.text` — the normative legal-line key (C7)

The composers read the footer legal line from `footer.legal.text`
(`component_render.footer_content`). `text:` is the NORMATIVE key; synonyms
(`copyright:`, `line:`, …) are invisible to the renderer and fail validation. Social
entries need `{network, href}` shapes; columns pass through verbatim.

### 10.3b Chrome range + integrity checks (C7, sysfix 2026-07)

- `navbar.measured.contentMaxWidth` / `footer.measured.contentMaxWidth`: when present
  and non-zero, the value must sit in **[480, 2200] px**. `0`/absent means "could not
  measure" (e.g. a %-based container) and is allowed — the bridge then falls back to an
  agent-verified measure or the structural default. Out-of-range values are viewport
  artifacts, not content columns.
- A GRID-grammar footer (`footer.archetype: grid`, `rules.layout: grid`, or
  `rules.hasColumnHeadings: true`) must carry at least one headed column — losing every
  heading is the heading-in-link DOM-nesting capture bug, not real IA.
- A declared `navbar.logo` dict must be RENDERABLE: an on-disk `src`, `kind: svg` (with
  markup or a `srcContract` pointer), or a text fallback. Otherwise drop the dict and
  let the wordmark device render.
- `footer.logo` must be the brand's own mark — src/alt/href matching store/review badge
  vocabulary (`app-store`, `google-play`, `badge`, `rating`) fails; those files belong
  to content sections and asset tags.
- Mega-menu integrity: a `navbar.primary[].menu.columns[]` heading must not be a strict
  PREFIX of its first link's label — that shape is the label-concatenation capture bug
  (heading text swallowed into the link at extraction).

### 10.3c `blocks.card.variants` — card variant coverage (C10, sysfix 2026-07)

A usable `blocks.card` (declared, not `notObserved`, `use` ≠ never) must either
enumerate the OBSERVED card registers under `variants:` (e.g.
`[{ id: media-well, … }, { id: text-only, … }]` — generic register names, never
section-/content-specific ones) or carry `singleVariantConfirmed: true` after
re-checking the grounding crops. One measured card is a claim about the whole site's
card grammar; the claim must be explicit.

### 10.3d Composed-demo smoke + escape hygiene (C11–C12, sysfix 2026-07)

C11 composes every referenced layout-library pattern through the REAL preview harness
(`render_components_preview.compose_pattern_docs`) into a temp dir and rejects:

- patterns that fail to compose at all (token-generation errors surface here);
- srcless `c-image-ph` placeholder markup — every content media slot binds a real
  on-disk asset or is dropped;
- empty module captions when the brand AUTHORED per-module items (item copy must reach
  the modules);
- a pattern declaring centered alignment whose composed layout carries no anchor (the
  declared alignment was dropped on the way to the composer — checked on the
  demo-hydration path).

C12 scans generated HTML (`components-preview/`, `chrome/` under the brand dir, plus
the C11 smoke renders) for double-escaped entity text (`&amp;mdash;` etc.) — author
literal characters (`—`) in copy fed to renderers, never entity strings.
`--no-smoke` skips C11 for environments without the harness.

### 10.3e Motion + tier + relational-ladder tokens (C13–C15, P0/P1 2026-07)

- **C13 `tokens.motion`** — authored from `evidence/motion-audit.json`: ≥ 1 evidenced
  duration AND ≥ 1 easing (duration ladder / easing census / `signatureMoves[]`), or
  `tokens.motion: {notObserved: true, reason: …}`. Evidenced interactive blocks
  (accordion/tabs/modal/dropdown-menu/carousel) each carry a timing fact or a
  `motion: {notObserved, reason}` note.
- **C14 canonical tier** — `meta.canonicalTier` present when sized type roles exist;
  every sized role's `sizeRem` carries ≥ 2 breakpoints or the role carries
  `singleTierConfirmed: true` (verified against the measured tier ladder, both token
  shapes — flat roles and `type.scale` entries). Per-role `tiers:` stamps
  (`w<viewport>: {px, source}`) trace the ladder to the measure stage samples.
- **C15 relational spacing ladder** — ≥ 2 named `<role>-to-<role>` rungs in
  `tokens.spacing` (eyebrow-to-heading, heading-to-body, body-to-cta, …) each with a
  value, or `tokens.spacing.relationalLadder: {notObserved: true, reason: …}`. Rung
  names describe role relationships, never sections or content.

### 10.3f Asset-kind media treatment

`assets-tagged.json` may carry `mediaTreatmentRules[]` facts with
`{assetKind, role, fit, evidence}`. `assetKind` is a reusable visual kind
(`transparent-illustration`, `product-UI`, `screenshot`, `photo`, `mark`, …);
`role` is a reusable media slot (`card-media`, `split-media`, or `*`); and `fit`
is `contain` or `cover`. An asset may override the rule with
`mediaTreatment: {fit, evidence}`.

Treatment resolution is asset fact → matching kind/role rule → photographic
`cover` degrade. Basenames, brand names, section IDs, and content-specific token
names are not evidence and MUST NOT influence fit. Transparent illustrations
with meaningful outer silhouette generally evidence `contain`; photos,
screenshots, and product-UI collages authored as full-bleed regions generally
evidence `cover`. Exact source decisions remain curator/evidence facts rather
than universal filename conventions.

### 10.4 Required sibling outputs (C4–C6, C8–C9)

- `section-copy.yaml` — authored verbatim copy per content-bearing layout
  (`sectionCopy` base incl. `wordmark:`, `layoutCopy.<layoutId>` per section; full
  schema + merge precedence in **`spec/section-copy-schema.md`**). Without it the
  composers degrade every section to empty copy by design.
- `layout-library.yaml` — one `layout-patterns.v1` pattern per OBSERVED section shape;
  every `layouts[]` entry carries `patternRef` (or an explicit `noPatternReason`).
- Curated `assets/` — including ≥ 3 real logo files whenever a logo wall was observed
  (a logos use-case with no logo assets renders a text-caption wall), plus
  `assets-tagged.json` naming only files that exist on disk.
- `evidence/` — the extraction bundle (dom-mine / css-mine / measured / section crops /
  per-section vision grounding YAMLs) that every extracted value traces back to.
