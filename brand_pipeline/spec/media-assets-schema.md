# media-assets-schema.md — `media-assets.v1` (MEDIA SEMANTICS SYSTEM)

> Status: **normative** (2026-07-16). Defines the per-brand MEDIA SEMANTICS artifact
> `runs/<brand>/brand/media-assets.yaml`, the `generatedVisuals:` family (code
> recipes, not files), and the `mediaComposition` grammar that layout-library
> patterns (§4.4g) and `composition.v1` slots (§4.6.7) share. Enforced by
> validator checks **C26/C27/C28** (`tools/extract/validate_brand_evidence.py`),
> the composed-lane media-binding rows (`onbrand_check --composition` via
> `brand_pipeline/media_semantics.py`), and anti-slop rule **AS-67**.

## 0. The three families (why this artifact exists)

The pipeline previously conflated three different things inside `assets-tagged.json`
`useCase` strings and pattern prose:

1. **ASSET SEMANTICS** — what a file IS (a photograph, a third-party client logo, a
   product-UI collage that must never be cover-cropped). Facts about the file itself,
   stable across every section it appears in.
2. **COMPOSITION SEMANTICS** — how assets/components ARRANGE inside a section slot
   (a facepile, a logo marquee, a state-swap disclosure well, a photo with an
   accent-shape backplate). Facts about an arrangement, reusable across brands.
3. **GENERATED-VISUAL DEVICES** — visuals that are CODE RECIPES, not files (a CSS
   gradient, a mesh-gradient blob field, a shader canvas). Re-instantiable at any
   size from brand token roles; never flattened to a bitmap as their primary form.

`media-assets.v1` gives each family a first-class, machine-checkable home.
`assets-tagged.json` REMAINS VALID (renderer compat path, `attach_asset_inventory`);
`media-assets.yaml` is the richer superset and wins where both speak
(`asset_render_mode` consumes `treatmentDefaults` first, falling back to the tagged
facts). Brands without the artifact behave byte-identically everywhere (prompt
assembly, rendering, gates) — the same fact-gating contract as every pass-3 artifact.

## 1. Top-level shape (`runs/<brand>/brand/media-assets.yaml`)

```yaml
schemaVersion: media-assets.v1
brand: <brand name>                  # display name; brand names live ONLY in runs/<brand>/
source: "<capture provenance one-liner>"
note: >-
  Relationship line: assets-tagged.json remains the renderer-compat inventory;
  this artifact is the richer semantic superset authored from the same evidence.
photographyFingerprint: { … }        # §4 — brand-level imagery grammar (nullable)
assets: [ <asset>, … ]               # §2 — one entry per LOGICAL asset
generatedVisuals: [ <device>, … ]    # §5 — code recipes, not files (may be absent)
```

## 2. `assets[]` — one entry per LOGICAL asset

A **logical asset** is the deduped unit: srcset/retina/format siblings collapse into
ONE entry with `variants[]`; the `file` is the CANONICAL variant (highest resolution,
else the richest format). Stable `id` is a SLUG, never a filename — filenames may be
renamed/re-encoded between captures; the id survives.

```yaml
- id: <slug>                          # stable, unique, kebab-case; generic role words,
                                      #   NEVER campaign/section/content names
  file: <canonical filename>          # relative to assets/ (must exist on disk — C26)
  variants:                           # OPTIONAL — sibling files of the SAME logical asset
    - { file: <filename>, relation: retina|format|srcset|duplicate,
        scale: <number|null>, note: "<why it is the same asset>" }
  assetSemantics:
    kind: <enum §2.1>                 # REQUIRED, in the kind enum (C26)
    subtype: client|partner|press|integration   # logo-third-party only
    logoVariant: wordmark|monogram|inverse|favicon  # logo-own only
    decomposition: flat|decomposable  # product-ui-collage only: can layers separate?
    provider: <string>                # video-embed-third-party / embedded-3d only
    subject: "<generic role words>"   # what is pictured — NEVER brand/campaign names
                                      #   ("warm office scene", "orbiting product chips")
  facts:
    intrinsic: { w: <px|null>, h: <px|null> }
    intrinsicAspect: <w/h float|null>
    orientation: landscape|portrait|square|null
    alpha: true|false|null            # null = not measured (e.g. un-rasterized SVG)
    stats:                            # nullable block; when present, source REQUIRED
      dominantHue: <0-360|null>       # circular-mean hue of non-neutral pixels
      luminanceBand: dark|mid|light   # feeds text-over-media legality + dark/light pairing
      busyness: low|medium|high       # detail density (edge/variance proxy) — text-over-media legality
      saturationBand: muted|moderate|vivid
      source: measured|vision-estimated
    focalPoint: null | { x: <0..1>, y: <0..1>, source: measured|vision-estimated }
    safeCrop:   null | { top: <0..1>, right: <0..1>, bottom: <0..1>, left: <0..1>, source: … }
    altHarvested: <string|null>       # the source page's own alt text, verbatim
  usageRights: own|stock|third-party-mark    # REQUIRED (C26; AS-67 machine arm)
  treatmentDefaults: { fit: cover|contain|mark, salience: content|decorative }
  compositionRoles: [<generic role words>]   # where the brand deploys it (hero-background,
                                             #   proof-strip-mark, accent-backplate, …)
  provenance:
    source: capture-files|inline-svg|disclosure-crop|vision-inferred
    sections: [<sectionId>, …]        # provenanceIndex slugs; [] = chrome/unplaced
    confidence: high|medium|low
```

**`focalPoint`/`safeCrop` null semantics (normative):** `null` means UNKNOWN — the
value was never measured and consumers MUST NOT guess one (crop center-weighted, the
photographic default). A measured/vision value carries its `source`. Never author
`{x: 0.5, y: 0.5}` as a placeholder — a fabricated center IS a guess.

### 2.1 `assetSemantics.kind` enum (generic, extensible)

The CLOSED list validators accept today. Extending it is a spec edit (add the kind
here + a one-line gloss); kinds are generic visual classes, never brand/section/content
names.

| kind | gloss |
|---|---|
| `photograph` | real-world photography (scenes, workplaces, environments) |
| `portrait` | a person is the subject (headshots, team/founder portraits) |
| `avatar` | small identity portrait cropped for chip/circle use |
| `team-photo` | group photography of people |
| `client-photo` | customer-supplied workplace/case-study photography |
| `product-packshot` | physical product on a clean field |
| `product-ui-screenshot` | one product-UI surface (window, panel, mobile screen) |
| `device-framed-mockup` | UI inside a device frame (laptop/phone bezel) |
| `product-ui-collage` | multiple UI fragments composed into one artwork; carries `decomposition: flat\|decomposable` |
| `diagram` | explanatory line/flow diagram |
| `chart` | data visualization artwork |
| `illustration` | drawn/rendered non-photographic artwork |
| `spot-icon` | content-scale feature/product icon (the feature-icon family) |
| `ui-glyph` | chrome/control glyph (chevrons, arrows, search, close) — the existing inline-glyph channel |
| `social-icon` | social-network glyph (footer social row) |
| `logo-own` | the brand's own mark; `logoVariant: wordmark\|monogram\|inverse\|favicon` |
| `logo-third-party` | someone else's mark; `subtype: client\|partner\|press\|integration` (AS-67) |
| `badge-compliance` | compliance/certification badge art (SOC2, ISO, GDPR shields) |
| `badge-review-award` | review-platform award/rating art (G2 shields, star chips) |
| `badge-appstore` | app-store download badges |
| `background-art` | full-surface art paint (photo-derived or abstract washes baked as files) |
| `texture-noise` | tiling grain/noise texture |
| `pattern-tile` | repeating geometric pattern tile |
| `accent-shape` | decorative brand vector (organic backplate blob, corner shape) — the masked-media clip source |
| `3d-render` | pre-rendered 3D artwork shipped as an image |
| `map` | cartographic artwork |
| `social-proof-screenshot` | screenshot of a third-party post/review used as proof |
| `video-ambient-loop` | ambient/atmosphere motion file (no informational audio track) |
| `video-content` | informational video file |
| `video-embed-third-party` | provider + embed ref + poster ONLY — the file never ships |
| `video-poster` | still poster frame paired with a video asset |
| `animation` | lottie/rive/animated-image asset |

## 3. `mediaComposition` — arrangement grammar (shared with §4.4g / §4.6.7)

Declared on a MEDIA-BEARING SLOT (a layout-library pattern `contentShape.slots[]`
entry, or a `composition.v1` slot). It reuses the §4.6.5 registration/z/overlap
vocabulary VERBATIM — no parallel placement mechanism exists or may be invented.

```yaml
mediaComposition:
  mode: single | layered | masked-media | background-with-foreground
      | overlapping-cluster | scattered-cluster | facepile | tiled-grid
      | marquee | masonry | split-pair | carousel | state-swap
      | atomic-collage | icon-in-headline
  trigger: active-item|hover|tab       # state-swap ONLY — generalizes the accordion
                                       #   media swap (active-item), tab-panel swaps (tab)
                                       #   and hover-reveal swaps (hover)
  maskRef: <asset id>                  # masked-media ONLY: the accent-shape/logo asset
                                       #   whose silhouette clips the media layer
  scatter: { rotationRange: [<deg>, <deg>], jitterCols: <n> }   # scattered-cluster facts
  overlapClass: light|medium|heavy     # facepile: negative-margin stack depth class
  grid: { columns: <n>, gap: <CSS len> }   # tiled-grid / masonry facts
  layers:                              # ordered back→front where z ties
    - assetRef: <media-assets id>      # XOR componentRef — exactly one per layer
      componentRef: { contract: <blocks/primitives key>, usage: { … } }
                                       # a RENDERED COMPONENT floating over media (stat
                                       #   card, testimonial chip, notification toast);
                                       #   binds to the EXISTING block/primitive contracts
      z: back|mid|front
      registration: { toSlot: <slot>, edge: left|right|top|bottom,
                      depthCols: <n> | depthBaselines: <n>, z: back|mid|front }
      alignTo: { slot: <slot|omit=section>, edge: …, corner: tl|tr|bl|br }
      colSpan: <n>  offsetCols: <n>  offsetBaselines: <n>
      width: hug|media|full-bleed|framed
      forItem: <int|item label>        # state-swap: which item this layer swaps in for
      motion: { kind: parallax|scroll-coupled, amount: { class: light|medium|heavy } }
                                       # OPTIONAL motion facts — must agree with the
                                       #   brand's voice.motionSpec / motion dial axis
```

Mode notes (all generic; the mode never names a section or content):

- **`single`** — one asset fills the slot (the default; declaring it is optional).
- **`layered`** — N registered layers over a base (the §4.6.5 layered-hero grammar).
- **`masked-media`** — the media layer clips inside `maskRef`'s silhouette (an
  `accent-shape`/`logo-own` vector). The mask asset must carry alpha/vector geometry.
- **`background-with-foreground`** — a `z:back` full-bleed art layer with content or
  foreground media above (sanctioned text-on-media rules still apply).
- **`overlapping-cluster`** — 2-4 media layers with explicit registrations (the
  collage-cluster shape); **`scattered-cluster`** adds rotation/scatter facts.
- **`facepile`** — small `avatar`/`portrait` assets in a negative-margin stack
  (`overlapClass` sets depth). Proof-density device.
- **`tiled-grid`** — static grid of marks/photos (`grid` facts); **`marquee`** — the
  moving strip, aligned with the EXISTING marquee device (a marquee-capable strip's
  static form stays the measured resting frame); **`masonry`** — uneven flowing grid.
- **`split-pair`** — exactly two assets sharing the slot as a pair.
- **`carousel`** — assets swap by slide advance (aligns with the existing carousel
  devices; controls stay pattern facts).
- **`state-swap`** — layers swap on `trigger`. `trigger: active-item` SUBSUMES the
  accordion media-swap device (per-item media); renderers fold layers onto the
  existing per-item media channel (`items[].media` / `rowMedia`).
- **`atomic-collage`** — the file is ONE flat composed artwork: DO NOT split, crop
  into parts, or overlay content onto its internal elements.
- **`icon-in-headline`** — a `spot-icon`/`ui-glyph` asset rides inline within a
  heading's text run (the glyph channel, sized to the text tier).

## 4. `photographyFingerprint` — the brand's imagery grammar

Brand-level MEASURED facts about the photography family (computed from the actual
`photograph`/`portrait`/`client-photo` assets; Pillow stats or documented manual
reads). Generic, promptable, palette-agnostic in rule language — exact values live
here as values.

```yaml
photographyFingerprint:
  measured:
    temperatureCast: warm|neutral|cool      # dominant white-balance cast
    keyExposure: low-key|mid-key|high-key   # overall exposure family
    saturationBand: muted|moderate|vivid
    finish: matte|neutral|glossy            # contrast/sheen family
    sampleSize: <n assets measured>
    source: measured|vision-estimated
  prose: >-
    One short paragraph a generator can follow when sourcing/briefing NEW photography
    for this brand — generic descriptors only (subjects as role words, treatment as
    families), never campaign copy.
```

A brand with no photographs records `photographyFingerprint: {notObserved: true,
reason: …}` — never silence, never a fabricated fingerprint.

## 5. `generatedVisuals[]` — code recipes, not files

Visual devices the source EXECUTES rather than ships as files. Each entry is a
re-instantiable recipe whose color inputs are BRAND TOKEN ROLES (never hex-only, so
the device re-renders on any surface at any size), plus a captured poster.

```yaml
generatedVisuals:
  - id: <slug>                         # generic device words, never section/content names
    kind: css-gradient | mesh-gradient-blobs | shader-canvas | embedded-3d
        | noise-grain | dot-grid
    recipe: { … kind-specific, below … }
    poster: <filename|null>            # §5.1 poster-frame discipline
    posterNote: "<when poster is null: why + what renders instead>"
    degrade: [live, poster, omit]      # the ONLY legal degrade ladder, in order
    provenance: { source: …, sections: […], confidence: … }
```

Kind-specific recipe shapes:

- **`css-gradient`** — `{ stops: ["<color|token role> <pos>", …], angle: <deg>|
  shape: radial|conic, tokenRoles: [<color role>, …] }`. Literal CSS stops ARE the
  device; `tokenRoles` names which brand color roles the stops resolve from.
- **`mesh-gradient-blobs`** — `{ blobs: [{ hueRole: <brand color role>, sizeFrac:
  <0..1>, position: {x,y 0..1}, blurPx: <n> }, …], blendMode: <css blend>,
  animation: {drift: slow|none} }`. NEVER flattened to a bitmap as its primary form —
  the recipe re-instantiates at any size with the brand's hues.
- **`shader-canvas`** — `{ source: <file|null>, uniforms: {…}, fps: <n|null> }` +
  REQUIRED poster. Degrade ladder: live script → baked poster → omit; **silent
  substitution of a different visual is forbidden**.
- **`embedded-3d`** — `{ provider: <string>, sceneRef: <url|file|null>,
  glb: <file|null>, interaction: orbit|scroll|none }` + REQUIRED poster.
- **`noise-grain`** — `{ opacity: <0..1>, scalePx: <n>, blendMode: <css blend> }`.
- **`dot-grid`** — `{ gapPx: <n>, dotPx: <n>, inkRole: <brand color role> }`.

### 5.1 Poster-frame discipline

Every generated visual carries a captured `poster` (a crop from the run's own capture
or a baked render) so replicas and contact sheets render WITHOUT executing code.
Posters live under the brand's `assets/` tree (convention: `assets/generated/`).
Poster filenames MUST NOT contain default-art resolver keywords (`hero`, `noise`,
`texture`, `gradient`, `logo`, `panel-art`, `backdrop`, `cover`, `map`, `portrait`,
`avatar`) — a poster is provenance evidence, never a bindable art candidate for the
keyword resolver. A `poster: null` is legal ONLY for self-rendering declarative kinds
(`css-gradient`, `noise-grain`, `dot-grid`) whose recipe alone reproduces the visual
deterministically, and must carry a `posterNote` saying so.

### 5.2 Legality tie-in (evidence licenses devices)

Generated visuals are LICENSED BY MEASURED EVIDENCE only. A brand whose capture shows
no gradients must not receive one from a style preset or a generator's habit —
`neverDo`/flatness rules take precedence over any style-layer suggestion, exactly as
in Appendix B precedence. The composed-lane check treats an un-licensed generated
visual (an id absent from the ACTIVE brand's `generatedVisuals:`) the same as an
invented filename: a hard failure, never a silent substitution.

## 6. HARD GENERATION RULE + the NO-MATCH POLICY LADDER

Injected into the generation prompt ONLY when the brand ships `media-assets.yaml`
(fact-gated; artifact-less brands keep byte-identical prompts). Enforced by
`media_semantics.lint_media_bindings` as a generation prefilter and as composed-lane
gate rows.

**The hard rule.** For any media-bearing slot: when a COMPATIBLE extracted asset
exists (kind + compositionRole + aspect-class match), BIND it (`assetRef`, or an
`asset.src` naming the real file). Never invent filenames. Never synthesize,
regenerate, or describe-for-generation a visual when a compatible extracted asset
exists.

**The no-match ladder** (each rung explicit, in order):

1. **reuse-with-treatment** — bind the nearest compatible asset and declare the
   treatment that adapts it (recrop within `safeCrop`, brand-licensed tint/duotone
   per treatment rules). Still an `assetRef` binding.
2. **declared gap** — the slot carries `noCompatibleAsset: { reason, requiredKind,
   aspect?, surface? }`. The pipeline emits the gap into the lane's **ASSET-REQUEST
   MANIFEST** (`asset-requests.json` beside `composition.json`): one entry per gap
   with `{section, slot, role, requiredKind, aspect, surface, reason}` so a human/
   agent can source the missing asset later.
3. **brand-legal placeholder recipe** — the declared gap may name `placeholder:
   <generatedVisuals id>` — a NAMED device from the brand's own licensed
   `generatedVisuals:` roster that paints the slot until the asset arrives. Renderer
   default stripes/placeholder plates are NOT a rung.

**Silent placeholder = failure.** A media slot that resolves nothing and declares
nothing is the #1 recurring defect class this system exists to close; the composed
lane fails it loud (`media-binding` row).

## 7. Enforcement map

| layer | check | severity |
|---|---|---|
| `validate_brand_evidence.py` C26 | artifact shape: parses, ids unique/slug-form, files on disk, `kind` in enum, `usageRights` present, provenance present, generated-visual poster discipline | error (absence = note) |
| `validate_brand_evidence.py` C27 | reference integrity: `mediaComposition` layer `assetRef`/`maskRef` resolve into the registry; `componentRef.contract` exists in contracts; pattern-bound `assets:` files registered (no orphan bound assets); state-swap items resolve | error (fact-gated on artifact presence) |
| `validate_brand_evidence.py` C28 | variant dedupe sanity: byte-identical files under two ids; a variant higher-res than its canonical; dangling variant files | advisory |
| `media_semantics.lint_media_bindings` | composed-lane: every media slot resolves (`assetRef`/real `asset.src`) or declares `noCompatibleAsset {reason}`; refs resolve; placeholder recipes licensed; AS-67 mark legality | generation prefilter (repairable) + HARD gate rows under `--composition` |
| `anti-ai-slop.md` AS-67 | third-party-mark legality (usageRights × slot use-case) | slop registry + machine arm in the media lint |

## 8. Authoring rules (Layout Analyst contract — see layout-analyst-skill.md)

- Author FROM evidence: `assets-tagged.json`, capture files, grounding YAMLs,
  disclosure captures. Never invent an asset, a stat, or a fingerprint.
- Stable ids are generic role slugs (`customer-mark-<name>` is WRONG — use the
  third-party label field for the name; ids describe the asset class + discriminator,
  e.g. `client-logo-ebay` is acceptable because the mark IS that company's, but
  `hero-campaign-photo-q3` is not — no campaign/content words).
- Keep `assets-tagged.json` intact and consistent (compat path); note the
  relationship in both files and the brand changelog.
- Measured stats (`facts.stats`, fingerprint) come from Pillow (the curate tool's
  draft emission) or documented manual reads; vision estimates are marked
  `source: vision-estimated`.
- `mediaComposition` on patterns records only OBSERVED arrangements (provenance
  crops/DOM), same evidence discipline as `specialTreatments`.
