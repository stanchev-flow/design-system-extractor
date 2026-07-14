# style-library INTEGRATION PLAN — audit + staged pass-3 execution

Status: plan of record for the revised pass 3 (portable style layer + create-from-style
mode). Authored 2026-07-14 from a full audit of the imported 15-file package.
Fence note: written while pass 1 (signatures + derived scales + voice + gates) is
in flight in a parallel lane; this plan touches NO shared code, NO existing specs, NO
changelogs — the root `changes.md` entry for this import is deferred to pass-3 execution.

Provenance of everything in this directory:
`authored-prior (Claude design chat, 2026-07-14) — NOT evidence; requires bakeoff
validation before brand use.` Every file carries the stamp.

---

## 1. Inventory — what actually landed

**The package never landed in the repo.** The claimed import location
(`brand_pipeline/spec/`, subfolders sections/styles/overrides/layouts/variations) did
not exist; `brand_pipeline/spec/` contains only our own specs. The package was found
OUTSIDE the repo in `~/Downloads/spec/` (15/15 files, all parseable), with a
byte-identical sibling copy `~/Downloads/spec 2/` and the source archive
`~/Downloads/Training on website design layouts.zip` (all timestamped 2026-07-14
12:06–12:15). Nothing was missing; nothing was malformed beyond the defects below.
The Downloads copies were left untouched.

Authored inventory (15 files, 163 KB):

| Authored file | Size | Disposition after normalization |
|---|---|---|
| `README.md` | 2.2 K | KEPT (file map updated to YAML-canonical names; provenance + import notes added) |
| `pipeline.json` | 6.7 K | → `pipeline.yaml` (canonical-only JSON converted; marked package doc, NOT our pipeline) |
| `token-schema.json` | 1.6 K | → `token-schema.yaml` |
| `resolution-model.md` | 2.6 K | KEPT as package doc (+ adaptation-required banner) |
| `resolution-model.json` | 3.0 K | DROPPED — verified field-for-field duplicate of the MD (levels/merge/invariants/algorithm/pseudocode) |
| `sections/catalog.yaml` | 15 K | KEPT canonical, with 2 transparent fixes (below) |
| `sections/catalog.json` | 20 K | DROPPED — content-identical to YAML *after* the bool fix (it carried the authored truth) |
| `sections/catalog.md` | 11 K | DROPPED — pure prose projection, no unique content (verified head-to-tail) |
| `styles/directives.yaml` | 28 K | KEPT canonical (verified content-identical to JSON) |
| `styles/directives.json` | 36 K | DROPPED — content-identical |
| `styles/directives.md` | 24 K | DROPPED — pure prose projection |
| `overrides/overrides.yaml` | 3.3 K | KEPT canonical (verified content-identical to JSON) |
| `overrides/overrides.json` | 4.7 K | DROPPED — content-identical |
| `layouts/primitives.json` | 3.2 K | → `layouts/primitives.yaml` |
| `variations/axes.json` | 5.6 K | → `variations/axes.yaml` — `global` axes kept; `perSection` deduplicated (verified byte-identical 21/21 to `sections/catalog.yaml` `variationAxes`) |

Canonical package now lives at **`brand_pipeline/contracts/style-library/`** (this
directory): `README.md`, `resolution-model.md`, `pipeline.yaml`, `token-schema.yaml`,
`sections/catalog.yaml`, `styles/directives.yaml`, `overrides/overrides.yaml`,
`layouts/primitives.yaml`, `variations/axes.yaml`, `INTEGRATION-PLAN.md`.

**Content defects found (and how they were handled):**

1. **YAML-1.1 bool coercion corrupted 8 authored values.** `catalog.yaml` wrote axis
   values `on`/`off` bare, so YAML parsers read them as booleans in 4 sections'
   `variationAxes` (`feature-alternating.bullets`, `comparison-table.sticky`,
   `blog-resources.thumb`, `footer.newsletter`); `catalog.json` carried the authored
   strings. Fixed at import by quoting (`- "on"` / `- "off"`); the canonical YAML now
   verifies content-identical to the authored JSON. Lesson for stage B: our loader
   tests must pin string-typed axis values.
2. **Slot-name typo `dropddown`** in `nav.slots.optional`, consistent across all three
   authored formats. Fixed to `dropdown` with an inline comment.
3. **Dangling layout ids in `layoutBias`.** `grid-aligned` and `asymmetric` appear in
   15 of 51 style directives but exist neither in `layouts/primitives.yaml` (17
   primitives) nor in any section's `layouts`. Under the package's own rule ("anything
   not in the section's `layouts` is ignored") they silently no-op, so e.g. `swiss`'s
   effective bias starts at `split-left`. NOT edited (meaning-preserving import);
   resolved in stage A by a data-side translation map (§4.3).
4. **Two overrides select layouts their section does not allow.**
   `brutalist.pricing.layout: list-rows` and `brutalist.testimonial.layout: list-rows`
   — `list-rows` is absent from both sections' `layouts`. Under the authored algorithm
   these silently degrade to `defaultLayout` (grid-3 / minimal), contradicting the
   override's own `$append` rules ("tiers stacked…"). NOT edited; stage A decision
   (§4.3): extend the two sections' `layouts` OR re-author the overrides — and make
   out-of-vocabulary layout picks LOUD (reject), never silent.
5. **Internal duplication drift**: `pipeline.yaml` embeds its own `token_schema` copy
   that differs from `token-schema.yaml` (adds `layout.heroPattern`, example brand
   fonts/accent). Treated as doc-only illustration; `token-schema.yaml` is the schema
   of record for binding. Its example values ("Space Grotesk", `oklch(0.56 0.13 250)`)
   must never leak as defaults (AS-24/AS-38).

Counts verified: 21 sections, 51 styles (both match their declared `count`), 17
primitives, 9 override styles / 18 override pairs, 21/21 per-section axes.
Cross-file referential integrity is otherwise clean: every section layout resolves to
a primitive; every override targets a real style × section.

---

## 2. Quality audit per layer

### Layer 1 — 21-section catalog: GOOD BONES, SHALLOWER THAN OUR TIER

Coherent and internally consistent: every section has purpose, required/optional
slots, allowed layouts + default, invariants, variation axes, soft rules. The slot
vocabulary maps cleanly onto ours (their `headline`/`primaryCTA`/`media` ≈ our
`heading`/`actionGroup`/`media` slot grammar; their required/optional ≈ our
`required:` flags). Compatible, with three systematic gaps vs our
`layout-patterns.v1`/archetype vocabulary:

- **No physical slot classes** — nothing like `textLen`/`sizeClass`/`width`/`z`/
  `mediaAspect`, no alignment/headerContext grammar, no geometry ranges. Their
  "layouts" carry ALL the geometry, and those are one-word primitive refs.
- **No physics contract** — no equivalent of `physicsBindings`, slopTraps, or
  exemplar discipline (archetype-library §6). Their `invariants` mix three different
  kinds of law (see §4.1) without marking which is which.
- **Genre-mean numbers as locks** — "≤ 7 top-level links", "3–5 steps",
  "label ≤ 4 words", "logos monochrome or unified treatment": reasonable priors,
  wrong as unconditional locks (a measured brand violating one is EVIDENCE, and
  evidence wins).

**Coverage against our stack** (standard pattern tier = 8 use-case files; blocks.yaml;
chrome facts; 29 hero archetypes):

- Already covered DEEPER by us (adopt nothing structural, harvest axes/invariant ideas
  only): `hero` (29 archetypes vs their 1×5-layouts), `nav` + `footer` +
  `announcement-bar` (our measured chrome + navbar/footer/banner blocks),
  `cta-band` (cta.yaml + cta-block), `pricing` (pricing.yaml + pricing-card),
  `testimonial`, `feature-trio` (features.yaml + feature-item).
- Covered as BLOCKS but missing a standard section-pattern file (merge: adopt their
  section entry as the pattern-file seed, enrich to our slot classes): `faq`
  (accordion blocks + IC-family), `how-it-works` (steps blocks), `metrics-band`
  (stat-block), `product-split` (media-text + split scaffolds), `comparison-table`
  (table block + semantic table renderer), `logo-wall` (logo-bar block + strip
  devices), `newsletter` (form block), `feature-alternating` (media-text rows /
  interlock).
- Genuinely NEW use-case keys for the standard tier: `case-study` (exists today only
  as a hubspot-v2 brand-tier pattern), `integrations-grid`, `security-trust`,
  `blog-resources`, `team` (about.yaml covers mission/values; a people-grid pattern is
  new).

### Layer 2 — 51 style directives: REAL SEEDS, TWO DEAD AXES, A THIN TAIL

Sampled across all 7 families (swiss, brutalist, editorial-magazine, newspaper,
saas-product, dashboard-data, glassmorphism, luxury-fashion, y2k, neumorphism,
maximalist, poster-typographic, high-contrast-mono…). Each directive is a compact
17-key constraint set + layoutBias + 3 signature moves. Verdict: **meaningful
constraint sets, not thin labels, for roughly 35–40 of 51** — the differentiation
lives in `radius/border/shadow/palette/density/accentUsage/case/tracking/layoutBias/
imagery/typeDisplay` and in mostly-structural signatures ("one accent, used
structurally not decoratively", "thick black borders, hard offset drop shadows",
"tabular figures, chart accents"). Honest negative findings:

- **Two axes carry ZERO signal**: `motion: subtle` on 51/51; `scaleRatio: 1.25` on
  49/51 (only `newspaper` 1.2 and `editorial-magazine` 1.333 differ). These are
  filler, not measurements — they must never override pass-1 derived scales or
  captured motion tokens (AS-47's spirit: "subtle" is not a token).
- **Type fields are prose, not bindable constraints** ("Helvetica/Neue grotesk",
  "groovy rounded", "default/ugly-on-purpose") — they need a translation into our
  style front-matter type structure (`display_min_rem`, family-class slots) at seed
  time.
- **A thin tail** (~10–15, mostly Expressive/Texture: y2k, vaporwave, psychedelic,
  memphis, grunge…) leans on imagery + mood-label signatures ("early-web optimism",
  "nostalgic dreamscape"). Usable as creative-direction seeds; not enforceable
  constraint sets without enrichment.
- Compared to our existing style layer (`styles/<id>.md` with parsed front-matter:
  spacing scale + slot assignments, type ranges in rem, motion ms, invariants, failure
  modes): theirs is coarser per-style but 10× broader in coverage. That is exactly the
  right raw material for a SEED library, and exactly why bakeoff validation (stage C)
  is mandatory before any style is trusted in a lane.

### Layer 3 — resolution model: IMPLEMENTABLE, WITH THREE ADAPTATIONS

The 4-level cascade (sectionDefault < styleDirective < override < brandOverride) with
per-key deep merge, tagged list ops (`$replace`/`$append`/`$remove`, bare array =
replace), layoutBias rerank, and locked invariants is small, clean, and implementable
against our stack in about a day including tests. Its precedence DIRECTION agrees with
our law on the headline question: **brand (level 4) outranks style (level 2) — brand
evidence wins is preserved**, matching Appendix B precedence 1 and §5.3. The
contradictions are narrower but real — see §4.

---

## 3. Vocabulary mapping tables

### 3.1 Their section ids ↔ our patterns / blocks / archetypes

| Theirs | Ours today | Stage-B disposition |
|---|---|---|
| `hero` | `layout-patterns/hero.yaml` + 29 `hero-*` archetypes | ours wins; harvest their axes as knob cross-check |
| `nav` | chrome facts (`navbar`, utilityTier) + `blocks.navbar` | ours wins (measured chrome); their axes → chrome knob ideas |
| `announcement-bar` | `blocks.banner` + `utilityBanner` chrome | merge (axes: tone/position) |
| `logo-wall` | `blocks.logo-bar` + strip devices, AS-33 | merge → new standard pattern file; DEMOTE "logos monochrome" lock to soft (evidence: full-color strips exist) |
| `feature-trio` | `features.yaml` + `feature-item` | ours wins; keep their parallel-grammar rule as soft |
| `feature-alternating` | `media-text` rows / `interlock` | ADOPT as new pattern key |
| `product-split` | `media-text` + split scaffolds | ADOPT as new pattern key |
| `how-it-works` | `blocks.steps`/`step-item` | ADOPT as new pattern key |
| `metrics-band` | `blocks.stat-block` | ADOPT as new pattern key |
| `testimonial` | `testimonial.yaml` + block | ours wins |
| `case-study` | brand-tier only (hubspot-v2 `case-study-header-rail`) | ADOPT (genuinely new standard key) |
| `pricing` | `pricing.yaml` + `pricing-card` | ours wins; their `highlight: none` axis is a good addition |
| `comparison-table` | `blocks.table` + semantic table renderer + `hero-comparison-dual` | ADOPT as new pattern key |
| `integrations-grid` | — | ADOPT (new) |
| `faq` | `blocks.accordion` + IC-TAB/disclosure contracts, AS-40 | ADOPT as pattern key; their "one item open at a time" = AS-40 ✓ |
| `security-trust` | — | ADOPT (new) |
| `team` | `about.yaml` (partially) | ADOPT people-grid variant |
| `blog-resources` | — | ADOPT (new) |
| `newsletter` | `blocks.form` (+AS-14 stated-reason law) | ADOPT as pattern key; "privacy/consent note" invariant ≈ AS-14 ally |
| `cta-band` | `cta.yaml` + `cta-block` | ours wins |
| `footer` | `footer.yaml` + chrome + `blocks.footer` | ours wins |

### 3.2 Their 17 layout primitives ↔ our scaffolds / devices

| Theirs | Ours |
|---|---|
| `center-stack` | `section-stack` (+ centered headerContext) |
| `split-left` / `split-right` | `section-split` + `mediaSide` knob |
| `full-bleed` | `section-stack-fullbleed` / `stack-fullbleed` archetype + text-on-media law (AS-22) |
| `grid-2/3/4` | `layout-grid` + columns knob |
| `bento` | `layout-bento` |
| `list-rows` | `layout-row` stacks / list-rows devices |
| `table` | `blocks.table` + semantic table renderer |
| `accordion` | `blocks.accordion` + IC contracts |
| `tabs` | `blocks.tabs` + `_compose_tab_split` (IC-TAB) |
| `carousel` | `blocks.carousel` + edge-cut/panelcar devices |
| `marquee` | marquee device + AS-42 seam law |
| `sticky-bar` | navbar/utility chrome (not a section scaffold) |
| `columns-footer` | footer scaffold |
| `minimal` | `section-stack` (sparse) |
| *(dangling)* `grid-aligned` | not a layout — an alignment discipline; map → `layout-grid` + left-flush headerContext bias |
| *(dangling)* `asymmetric` | not a layout — map → `collage`/`interlock`/offset devices (requiresOffGrid territory) |

### 3.3 Their token-schema keys ↔ our brand.yaml + pass-1 artifacts

| Their key | Ours |
|---|---|
| `style.type.pair [displayFont, bodyFont]` | style slots `font-display`/`font-body` (Appendix B) ← `tokens.type.display-hero.family` / `body.family` |
| `style.type.scaleRatio/baseSize/weights` | pass-1 DERIVED TYPE SCALE (quantized ratio+base) over the measured `tokens.type` ladder |
| `style.space.base/scale/sectionRhythm` | pass-1 derived spacing scale over `tokens.spacing` (`section-padding-*`, `module-gap-*`) + relational ladder (C15) |
| `style.shape.radius/borderWidth/elevation` | radius/border tokens + shadow policy (style front-matter `radius:`, `shape.flat`) |
| `style.color.roles [bg,surface,text,muted,border,accent]`, `space: oklch` | `tokens.surfaces` role grammar (`surface/*`, `text/on-*`, `accent/*`) — theirs is FLAT six-role; ours is per-surface with onInverse variants. oklch solving = already-planned pass-3 work ✓ |
| `style.layout.cols/maxWidth/gutter` | grid facts + `--content-measure` (containment law) |
| `style.motion.easing/durationMs` | motion tokens / `voice.motionSpec` (C13); degrade instant (AS-47) |
| `brand.font/accent/logo` | `tokens.*` + assets inventory (AS-33 disk-backed law) |
| `brand.signatures` (3–5 always/never) | pass-1 SIGNATURE MOVES + `do/avoid/neverDo` lists ✓ direct fit |
| `brand.voice {tone, readingLevel, sentenceLength}` | `voice:` + section-copy voice evidence |
| `brand.overrides` (level 4 per-section) | brand recipes / curation / pattern facts (see §4.2 — splits into our three brand sub-tiers) |
| stage-05 gates (contrast/scale_adherence/accent_budget/signature_check/grid_alignment/voice) | our gate battery: AS-01/10 contrast, AS-31/32 scale, accent discipline, pass-1 signature gates, spacing/containment audits, voice checks ✓ nothing new needed |

### 3.4 Their variation axes ↔ our wildcard/variance machinery

| Theirs | Ours |
|---|---|
| global `density/accentUsage/mediaPresence/motion` | FreedomBudget intensity ladder (styles.py, levels 1–5) + variance dial (archetype-library §3.5) |
| per-section axes (= catalog `variationAxes`) | archetype `variantKnobs` (`mediaSide`, `frame`, `proofRow`, `ctaEmphasis`…) — same shape, ours already declared per archetype |
| "perturb ONE axis, re-resolve" | wildcard one-mutation discipline (machine-PROPOSED, human-BLESSED) |
| "valid by construction" | **REJECTED** — every variant still runs the full gate battery; construction-validity never bypasses gates |

---

## 4. Cascade contradictions with our fact-resolution order — and the adaptations

Our law (brand-schema §5.3, Appendix B, AS-44): **measured facts > curation > recipes
> structural defaults; brand evidence always wins over anything designed.**

### 4.1 LOCKED invariants vs brand-evidence-wins — the one real doctrine conflict

Their model: "Keys under a section's `invariants` are LOCKED. No directive, override,
**or brand value** may violate them." That last clause contradicts our law wherever an
invariant encodes a genre prior rather than physics. Concrete collisions: "logos
monochrome or unified treatment" (measured full-color logo strips are common — our
own hubspot-v2 evidence), "≤ 7 top-level links" (a measured nav with 8 is a fact),
"one recommended tier highlighted" (their own authors wobble: "unless style forbids").

**Adaptation (stage A, normative):** classify every invariant into two classes at
import:

- **physics-class** → delegate to the EXISTING gate law, stay hard in every lane:
  "exactly one primary CTA" = AS-59; "high contrast with neighbors" / text-on-media =
  AS-01/AS-22; "headline is the focal point" = AS-32/AS-51 display ownership;
  "one item open at a time" = AS-40; containment/equal-optical-weight = container law
  + AS-50 family. These were already our law before the package.
- **genre-class** → demote to SOFT DEFAULTS (advisory, same posture as style
  `Style definition` rules in Appendix B): any brand fact or curation may override
  with provenance; the onbrand report shows OVERRIDE (blessed) not FAIL. Examples:
  link-count caps, "3–5 steps", "label ≤ 4 words", logo treatment, "≤ 2 supporting
  lines".

Their "violations are rejected at stage 05, not silently applied" survives for the
physics class only — and that is exactly our existing repair-loop posture.

### 4.2 Level 4 is too coarse — no evidence tier inside "brand"

Their `brandOverride` is one authored blob (`brand.tokens.json`). Our brand layer is
three-tiered (measured facts > curation > recipes/authored). The merged single
precedence for the pass-3 resolver (strongest → weakest):

```
gate battery (physics — a rejection layer, not a merge level)
  brand measured facts            ┐
  brand curation                  ├─ their "level 4", split into our tiers
  brand recipes / authored prefs  ┘
  style×section override          (their level 3)
  style directive                 (their level 2)
  section default                 (their level 1)
  scaffold/structural defaults    (our existing bottom vocabulary)
```

Their internal order (4 > 3 > 2 > 1) is preserved verbatim; their whole stack slots in
BELOW our entire brand evidence stack and ABOVE bare scaffold defaults. In
create-from-style mode there are no measured facts, so the style stack is the
strongest voice below intake-authored brand tokens — which is the package's intended
use and is consistent with Appendix B ("style supplies structure + defaults for
everything the brand leaves unset").

### 4.3 Algorithm defects to fix in OUR implementation (not silently inherited)

- **Step-5 layout recompute clobbers explicit `layout:` overrides.** As authored,
  `resolve()` recomputes `spec.layout` from `layoutBias` AFTER merging overrides, so
  an override's direct `layout:` pick is dead code. Worse, `brutalist.pricing` picks
  `list-rows`, which pricing's `layouts` doesn't allow → silently degrades to
  `grid-3`, contradicting the override's own appended rules. OUR resolver: an explicit
  `layout` at override/brand level wins IF it is in the section's `layouts`; if not,
  REJECT loudly (fail closed with a note, never silent degrade). Data decision at
  stage B: extend `pricing.layouts` and `testimonial.layouts` with `list-rows`
  (genre-plausible: stacked prestige tiers, blockquote rows) so the brutalist
  overrides become resolvable as authored.
- **Dangling bias ids** (`grid-aligned`, `asymmetric`, 15 styles): resolve via a
  declared data-side translation map in the resolver's directive projection
  (`grid-aligned → layout-grid + left-flush header discipline`,
  `asymmetric → collage/interlock (requiresOffGrid)`), so the styles' intent survives
  instead of silently no-op'ing.
- **Bare-array = `$replace`** is fine and matches the overrides' axis-narrowing usage
  (`variationAxes.highlight: [none]`), but our implementation must treat unknown `$`
  tags as errors, not keys.

---

## 5. Slop-risk assessment (genre-mean vs structural)

- **Genre-mean prior content** — `layoutBias`, `palette` (mono/duo/vivid), `density`,
  `imagery` assignments are means of each genre. LEGITIMATE as create-from-style
  seeds (no evidence exists yet); **FORBIDDEN as correctors on extracted brands**
  (AS-44 facts-must-win, §5.3 extracted-over-designed ratchet). The resolver enforces
  this by construction via §4.2 precedence.
- **Zero-signal axes** — `motion: subtle` ×51 and `scaleRatio: 1.25` ×49 are filler
  (§2). Binding them as real constraints would create false confidence and would
  collide with AS-47 (motion rides captured tokens or degrades instant — "subtle" is
  not a token). Stage C treats both as UNSET unless a style genuinely differs
  (newspaper 1.2, editorial-magazine 1.333).
- **Mood-label signatures** ("early-web optimism", "nostalgic dreamscape",
  "atomic-age optimism") — creative-direction prose. Keep as descriptive `signatures`
  for brief/copy guidance; never turn into gates or token values.
- **Overrides carrying CSS mechanics as prose** ("thick 2px borders", "prices in
  monospace") — must resolve through token/fact vocabulary at instantiation; a
  directive naming a px value is a designed prior that brand evidence outranks.
- **Example values in `pipeline.yaml`** (Space Grotesk / Instrument Sans /
  `oklch(0.56 0.13 250)`) — illustration only; leaking them as defaults would be
  AS-24/AS-38 brand-DNA contamination. The file is stamped doc-only.
- **Known gate collisions to bakeoff deliberately**: `neumorphism` (monochrome
  low-contrast) and `glassmorphism` (translucent panels) will stress AS-01/AS-10
  contrast law — include one in stage C to prove the repair loop demotes the style
  gracefully instead of shipping inaccessible output.
- **Nothing in the package violates existing AS rules as data** — the risks above are
  all about WHERE the data is allowed to speak, which the precedence model settles.

---

## 6. Staged pass-3 execution plan

### Stage A — resolver against OUR precedence, with two-class invariants (~1–1.5 days)

New `brand_pipeline/style_library.py` (data loader + resolver; shared code but NEW
module — no existing-code edits, safe next to pass 1):

- Load this package (sections/styles/overrides/primitives/axes); schema-validate;
  string-typed axis guard (defect §1.1); unknown-`$`-tag errors.
- `resolve(section, style, brand_doc)` per resolution-model.md WITH the §4
  adaptations: merged precedence (§4.2), explicit-layout override semantics + loud
  rejection (§4.3), dangling-bias translation map (§4.3), invariant two-class split
  (§4.1) — physics-class delegates to existing gate ids (the archetype
  `physicsBindings` pattern: names, not reimplementations), genre-class emits
  advisory rows.
- Tests: merge semantics table, every override pair resolves (incl. the two brutalist
  repairs), 21×3 smoke resolutions, invariant-class fixtures (brand fact overrides a
  genre lock → OVERRIDE; violates AS-59 → REJECT).
- Deliverable: resolver + `tests/test_style_library.py`; no consumer wiring yet.

### Stage B — section-catalog merge into our contracts (~1–2 days, data authoring)

- ADOPT as new standard `layout-patterns/` use-case files (enriched to
  `layout-patterns.v1` slot classes — textLen/sizeClass/width/z, alignment context,
  origin: designed, provenance: style-library): `case-study`, `integrations-grid`,
  `security-trust`, `team` (people-grid), `blog-resources`, then the
  blocks-only-today keys: `faq`, `how-it-works`, `metrics-band`, `product-split`,
  `comparison-table`, `feature-alternating`, `newsletter`, `logo-wall`.
- MERGE (harvest axes/soft rules into existing files, no structural change): `hero`,
  `feature-trio`, `pricing` (+`highlight: none` axis), `testimonial`, `cta-band`,
  `footer`, `nav`, `announcement-bar`.
- DEFER: nothing — 21/21 have a disposition; but pattern-file authoring is phased
  (genuinely-new five first, blocks-only-today eight second).
- Extend `pricing.layouts`/`testimonial.layouts` with `list-rows` (§4.3).
- Update `layout-patterns/index.yaml` as files land (this is pass-3 execution, not
  this import).

### Stage C — style directives as SEED style library + bakeoff protocol (~2 days)

- Bind directives to our style front-matter shape via a generator: 17 keys → style
  front-matter (`radius:`, `shape:`, `spacing:` defaults, type family-class slots,
  `single_accent` from accentUsage minimal…), signatures → `## Style definition`
  prose; zero-signal axes emitted UNSET (§5). Output: `styles/<id>.md` candidates,
  origin: designed, provenance: style-library, **status: unvalidated seed**.
- **Bakeoff validation protocol (first worked run, 3 styles):** `swiss`
  (foundational, strong constraints), `editorial-magazine` (the one genuinely
  different scaleRatio + serif system), `neumorphism` (deliberate gate-collision
  probe, §5). For each: resolve hero + features + pricing + cta against one intake
  brand (stage D tokens) AND one extracted brand (Remote) → render → full gate
  battery (onbrand, slop @1440+@1180, interaction strict, spacing strict) → judge
  style legibility (does swiss read swiss?) + brand-evidence precedence proofs
  (extracted brand's measured facts visibly beat directive values in every dissent).
  A style graduates from `unvalidated seed` only on a green bakeoff; graduation is
  recorded per style.
- Remaining 48 styles graduate in batches through the same protocol; thin-tail styles
  (§2) need signature enrichment before their bakeoff.

### Stage D — create-from-style intake mode (~2–3 days)

- Intake/brief flow (their stage 00, our shape): brief captures target pageTypes,
  style pick (from validated library), brand instance tokens (fonts, accent in oklch,
  logo asset, 3–5 signatures, voice) — keyed to `token-schema.yaml` names mapped per
  §3.3.
- oklch role solving fills the flat six-role model, then EXPANDS to our surface-role
  grammar (surface/primary + inks + accent family) — the flat model is the intake
  format, never the internal one.
- Composition: page = ordered resolved sections (stage-A resolver) → existing
  composers via the pattern/archetype vocabulary (§3.1/3.2 mappings); hero routes
  through the EXISTING archetype shortlist (copy-first doctrine intact — the
  directive's layoutBias only reranks candidates, the copy brief still picks).
- Style detection (their stage 01–02) stays OUT of this pass: our extraction pipeline
  already measures deeper; from-style mode starts from a picked style, not a detected
  one.

### Stage E — pass-1 artifact key alignment (~0.5 day, blocked on pass 1 landing)

What pass 1's artifacts must expose for token binding (exact key names to be
confirmed against pass 1's landed schema, then frozen in an adapter, not scattered):

- **Derived type scale**: quantized ratio + base size + weights census → binds
  `style.type.scaleRatio/baseSize/weights`.
- **Derived spacing scale**: base unit + quantized scale steps + section rhythm →
  binds `style.space.*`; the relational ladder stays the finer authority above it.
- **Signature moves**: 3–5 always/never rules with gate hooks → binds
  `brand.signatures` + their `signature_check` gate (pass 1 is building exactly this
  gate family — no duplicate implementation; from-style mode consumes it).
- **Voice**: tone/readingLevel/sentenceLength equivalents → binds `brand.voice`.
- **Color roles in oklch** (or convertible): surface/text/accent role census → binds
  `style.color.roles` intake + stage-D solving.
- Acceptance: a `token-schema.yaml`→pass-1-artifact adapter table with zero unmapped
  keys, tested on both extracted brands.

**Total effort: ~7–10 working days** across the five stages; A and B are
parallelizable after A's loader lands; C blocks on A; D blocks on A+C(first 3); E
blocks on pass 1.

### Explicitly OUT (contradicts evidence-first doctrine or regresses our stack)

- Locked genre invariants binding against brand evidence (§4.1) — demoted to soft.
- Style directives (or overrides) correcting/overriding measured facts in extraction
  lanes — AS-44/§5.3; directives speak only below the brand evidence stack.
- "Valid by construction" variation claims — every variant runs the full gate battery.
- Their stage 01–02 style detection replacing our extraction — out of pass 3 entirely.
- Their stage-04 12-archetype list — our 29-archetype hero library + blocks stay the
  vocabulary; no regression to the coarser list.
- The flat six-role color model as our internal surface grammar — intake format only.
- `motion: subtle` / blanket `scaleRatio: 1.25` as bindable constraints — filler (§5).
- pipeline.yaml example fonts/colors anywhere near defaults — AS-24/AS-38.
