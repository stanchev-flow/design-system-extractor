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
      sizeRem:      { base: …, tablet: …, mobileL: …, mobile: … }   # responsive ladder
      lineHeight:   "<em|unitless>"
      weight:       <int>            # REQUIRED on EVERY tier — the measured computed font-weight
      letterSpacing:"<rem|em>"
      case:         uppercase|sentence|none
  spacing:
    <roleName>:                      # section-padding-light, module-gap-editorial, …
      value:        "<rem>"
      role:         "<short intent>"
      modeLadder:   { base: …, tablet: …, mobileL: …, mobile: … }   # responsive
  surfaces:
    <surfaceRole>:                   # surface/primary, surface/inverse, …
      bg:           "<hex>"          # or token ref
      intent:       "<role>"         # e.g. "default canvas", "dark bookend band"
      textPrimary:  "<token ref>"
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
    confidence:    high|medium|low
    provenance:    [<sectionId>…]
```

> `patternRef` is additive and optional — a layout with no `patternRef` behaves exactly as
> before. It links a concrete section instance to the reusable **use-case layout pattern**
> (§4.4) it reuses, so generation looks the pattern up instead of reinventing structure.

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
```

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
          mediaScale: { of: container|slot, fraction: <0..1> }               # media slots
          opacityClass: solid|tint|ghost                                     # for watermark/ghost slots
          z:          back|mid|front

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
