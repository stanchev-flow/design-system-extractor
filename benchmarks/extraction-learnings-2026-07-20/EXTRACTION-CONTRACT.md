# Extraction Contract — HubSpot v2/Remote learnings → automated 1:1 extraction

> **Date:** 2026-07-20 · **Scope:** read-only synthesis from `runs/hubspot-v2`, `runs/remote`, `runs/hubspot-v3`, AS/C rule corpus, and pipeline specs. **Purpose:** deduplicated contract for the next initiative (per-section diff-correction loop + per-family completeness + computed-styles-as-truth). **Quality bar:** hubspot-v2 replica **0.956**, remote **0.951**; hubspot-v3 **0.8955** (blocked at G4 0.90).

---

## 1. FIX CORPUS TABLE

Each row: learned fix → failure corrected → measured fact/geometry → extraction stage owner → enforcement (AS/C id or **GAP**).

### fix1 — user punch list (2026-07-12)

| Fix ID | Failure | Measured fact / geometry | Stage owner | Enforced |
|--------|---------|--------------------------|-------------|----------|
| fix1-1 hero padding | Hero band used site-average 64/64 pad; replica 0.771 | `contentShape.bandPadding {top: 11rem, bottom: 11rem}` from section-rects + pixel scan (~177px top/bottom) | **patterns-recipes** (`layout-library.yaml`) | **GAP** (no C-rule on bandPadding vs section-rects) |
| fix1-2 hero overlay | Wrong “baked into photo” claim | Flat scrim `rgba(0,0,0,0.4)` from `css-rules.json` `::after` | **ground** + **patterns** | **GAP** (vision vs css-rules precedence not gated) |
| fix1-3 hero button hierarchy | Both buttons rendered primary | Secondary = white fill + 2px #ff4800 border; actions slot must name “outlined white secondary” | **patterns** slot roles + **foundation** `buttons.secondary` | C3 (matrix); AS-59 (register hierarchy) |
| fix1-4 hero band rhythm | Global ladder 24/32/56 wrong for hero | Box rungs: eyebrow→heading ~10px, heading→body ~28px, body→cta ~44px → `contentShape.bandRhythm` | **patterns** | **GAP** (C15 ladder exists; per-pattern override not checked) |
| fix1-5 action register | Multi-primary action groups | Exactly one primary per group | **foundation** prose | **AS-59** |
| fix1-6 platform carousel | Missing static split carousel + controls | Split copy-left / art-right; round prev/next + 3-dot rail; `specialTreatments[kind=carousel]` | **patterns** + **copy-chrome** | C11 smoke; IC-TAB/CAR interaction contracts |
| fix1-7 product-grid split | Cards full-width; header actions dropped | ~35/65 split; copy rail + 2-col card grid; `archetypeRef: split` + `alignment.counterweight: cards` | **patterns** + **layouts** | C5; side-rail gated on `archetypeRef: split` (Remote regression) |
| fix1-8 section headrail | Section-level rail absent (only card icon placement) | Chip/pill — rule — trailing CTA; `dotted-rule-rail` treatment | **patterns** + **recipes** | **C23** (recipe coverage, advisory) |
| fix1-9 testimonial tabs | Pill-tab prose vs captured text tabs | Text tabs + orange underline active; `activeUnderline: rgb(255,72,0)`; photo col 600px / ~0.56 fraction | **patterns** + **ground** | C13 (motion); **GAP** (tab anatomy vs grounding) |
| fix1-10 onInverse buttons | Dark-band secondary used light-surface hover ink | `buttons.secondary.onInverse` + `surface/inverse.controls: onInverse` | **foundation** surfaces + buttons | C3 strict states; onbrand interaction-contrast |
| fix1-11 footer bottom bar | Legacy row layout vs centered stack | `footer.bottomBar.anatomy: centered-stack`; social between hairlines → wordmark → legal | **copy-chrome** `brand-chrome.yaml` / **foundation** footer | C7/C16 chrome depth |
| fix1-12 two-tier nav | Extractor `twoTier:false`; measured 128px bar | `navbar.utilityTier {height:40, trailing:[…]}` — **never** gate on `twoTier` alone | **copy-chrome** + **measure** | **C22** (advisory: utilityBarHeight>0 without utilityTier) |
| fix1-12b nav CTA group | Single CTA path | `navbar.ctas[]` with per-cta measured registers (height, pad, border) | **copy-chrome** | C7; C3 |
| fix1 closing | Nav content width | `navbar.measured.contentMaxWidth: 1080` | **measure** → **copy-chrome** | C7 range |
| fix1 closing | Edge-cut card geometry | `deviceGeometry {cardWidth:306px, cardGap:17px}` | **patterns** | C15/C19 spacing; **GAP** (cardGap vs grid token) |
| fix1 closing | Testimonial media fraction | 0.35 → 0.56 (600px of ~1075px) | **patterns** | **GAP** |
| fix1 closing | Closing stack measure | `stackMeasure: 62rem` for one-line 48px heading | **patterns** | compose_replica widthFidelity |
| fix1 closing | Secondary onInverse hover | `fgHover: #f8f5ee` | **foundation** | C3 strict |

**Evidence contradictions logged:** hero scrim is CSS not photo (`runs/hubspot-v2/brand/changes.md:169-171`); grounding ink-to-ink ≠ box rungs (`:172-173`); tab anatomy vs pattern prose (`:174-175`); chrome JSON twoTier false vs measured heights (`:179-180`).

### fix2 — recipes · glyphs · action groups · logo boxes (2026-07-13)

| Fix ID | Failure | Measured fact | Stage owner | Enforced |
|--------|---------|---------------|-------------|----------|
| fix2-U1 recipes | Three headrail bands shared unrecognized anatomy | `recipes.section-headrail` variants: icon-chip 66×66 r16, label-pill 32px r4, badge-with-icon 138×32; `railToHeading: 2rem`, `kickerGap: 1rem` | **patterns-recipes** | **C23** |
| fix2-U2 textCta glyph | Unicode arrow / invisible mask file:// | `buttons.textCta.glyph {asset: icon-next.svg, size}` | **foundation** + **curate** | C8 assets |
| fix2-U3 actionGroup | Drifting 16/24px gaps; body-to-cta over-read | `layoutGrammar.actionGroup {gap:1rem, marginAbove}`; closing override 1.5rem; ladder `body-to-cta: 2.5rem` (40px computed) | **foundation** + **patterns** | **AS-60**; spacing auditor `actions.*` |
| fix2-A1 logo item box | Aspect-weighted logos undersized | `mediaScale.item {153×76}`, gap 69px | **patterns** | **GAP** (no extraction gate on item box vs computed) |
| fix2 gate | Siderail full bleed | Container at 1080 spine | **patterns** alignment | **AS-56** containment law (fix3) |
| fix2 gate | Edge-cut cardGap | 17px declared step vs 32px site token | **patterns** | spacing advisory |

### fix3 — containment · alignment · slider · link hug · hero measure (2026-07-13)

| Fix ID | Failure | Measured fact | Stage owner | Enforced |
|--------|---------|---------------|-------------|----------|
| fix3 containment | Private max-width + auto margins center action rows | Single `CONTAINMENT_LAW_CSS` on 22 device selectors | **renderer** (consumes pattern facts) | **AS-56**; spacing `actions.alignment` painted-edge |
| fix3 AG align | `data-ag-align=start` ignored | `actionGroup.align` owns `justify-content`; no nested containment | **foundation** | **AS-60** |
| fix3 carousel | Full-bleed slider; paddles over text | `controls {placement: rail, size: 3.5rem}`; `.cs-panelcar` in containment law | **patterns** | **GAP** at extraction |
| fix3 arrow-link | Underline spans full card width | `width: fit-content` on `.c-arrow-link` | **foundation** link facts | **AS-61** |
| fix3 hero measure | H1 one line on wide screens | `stackMeasure: 49rem` (742px measured; font advance calibration) | **patterns** | spacing `container.stack-width` |

### fix4 — inline SVG glyph channel (2026-07-13)

| Fix ID | Failure | Measured fact | Stage owner | Enforced |
|--------|---------|---------------|-------------|----------|
| fix4 inline svg | Mask channel invisible / AA diffs | Sanitized inline `<svg>` for single-ink glyphs (arrow, chevrons, socials) | **curate** + **renderer** | C8; glyph crop tests (fix5) |

### fix5 — gallery defects (2026-07-14)

| Fix ID | Failure | Measured fact | Stage owner | Enforced |
|--------|---------|---------------|-------------|----------|
| fix5-D1 panel alignment | Heading centered, siblings left | `anatomy.alignment.context: splitColumn` → resolved anchor pack | **patterns** + **layouts** | **AS-49**; spacing `header.stack-coherence` |
| fix5-D2/3 glyph crop | 24×24 viewBox on 32-grid art | viewBox from source sprite symbols | **curate** | **GAP** (C8 file exists; viewBox not validated) |
| fix5-D4 chevron motion | User wants instant open | `navbar.measured.trigger.chevron.curation.motion: instant` | **copy-chrome** | **AS-47** |

### fix6 — copy-first · surfaces · slot fidelity (2026-07-14)

| Fix ID | Failure | Measured fact | Stage owner | Enforced |
|--------|---------|---------------|-------------|----------|
| fix6-F1 copy-first | Generic event hero | Copy → layout → build; optional agenda slot | **generation** doctrine | **AS-11**, **AS-53** |
| fix6-F2 surface mandate | 8/8 heroes forced inverse | Licensed surface roster; `surfaceIntent` any declared role | **patterns** | **AS-22** |
| fix6 slots | Silent slot drops (form, links, agenda) | Archetype slot binding; form-split, quiet-link rail | **patterns** + **layouts** | **AS-26**, **AS-53** |

### fix7 — accent devices · list/stat/fit (2026-07-14)

| Fix ID | Failure | Measured fact | Stage owner | Enforced |
|--------|---------|---------------|-------------|----------|
| fix7 orange-period | Landmark headings missing accent | `accentDevices.orange-period` floor on hero | **foundation** | signatures; **GAP** extraction-time floor |
| fix7 checkmark list | List glyph not consumed | `accentDevices.orange-checkmark-list` + `icon-success.svg` | **foundation** + **curate** | **GAP** |
| fix7 stat pair | Value→label seam wrong | `statPair` spacing rung | **patterns** | section-rules |
| fix7 heading fit | Display overflow measure | Heading fit-to-measure device | **patterns** | **AS-66** |
| fix7 form note | Caption placement | Note below control (AS-14) | **patterns** | **AS-14** |

### Remote lane additions

| Fix ID | Failure | Measured fact | Stage owner | Enforced |
|--------|---------|---------------|-------------|----------|
| remote fix7 skip | No standing underline accent | Hover-only links — do not invent `accentDevices` | **foundation** | doctrine in layout-analyst |
| remote 2026-07-20 | Testimonials flattened to logo row | Slot role “company marks” must not override authored card records | **harness inference** | regression test in `test_harness_regression_quality.py` |
| remote media | 57 assets, variant dedupe, `mediaComposition` modes | `media-assets.yaml` + pattern bindings | **media** stage | **C26**, **C27** |

### hubspot-v3 failure classes (harness + G4)

| Class | Failure | Should be computed | Stage owner | Enforced |
|-------|---------|-------------------|-------------|----------|
| v3 join drift | `layoutCopy.hero` vs `full-bleed-photo-hero` | Canonical `layouts[].id` = `layoutCopy` keys = `patterns[].id` | **staged_author** + **contract_projection** | **C4**, staged join validation |
| v3 slot type blindness | No `type: content` on slots → C4 skipped | Every text slot `type: content` | **patterns-recipes** | **C4** |
| v3 internal-id leak | `brand.name: hubspot-v3` in UI | Public `brand.name` + rich snapshot | **foundation** | **C29** |
| v3 button sample | 140px nav wrapper chosen vs 68px `.cl-button` | `_sample_for_family` prefers real control rects | **contract_projection** | **C3** label-fit |
| v3 stale harness | Demos at SHA `805e…` vs brand `256260f3…` | `projection_input_digest` on all projections | **G3** pipeline | digest gate |
| v3 section-04 routing | Primary canvas grid vs soft-accent split + edge-cut | Measured `#f9c9c0` surface + split headrail + edge-cut track | **patterns** + **measure** | **GAP** (auto surface role from computed) |
| v3 fonts | Generic stack vs self-hosted WOFF2 | Full `@font-face` from captured registry | **foundation** + **curate** | **GAP** |
| v3 G4 residuals @0.8955 | Hero composite, testimonial tabs/stats, platform carousel dims, product-grid height | Per-band measured rects + anatomy | **patterns** + **measure** | compose_replica punch-list |

**Pre-fix1 infrastructure (not punch-list):** phantom sections in `section-rects` (nav dropdowns as bands) — fixed in `measure_computed.py` (`runs/hubspot-v2/brand/changes.md:31`).

---

## 2. PER-FAMILY COMPLETENESS CHECKLISTS

Required **measured** facts (from computed-styles.json, section-rects, css-rules, chrome contract, grounding). Extraction must author before validation passes; renderer consumes.

### 2.1 Navbar chrome

| Fact | Source | Example (HubSpot v2) | Validator / AS |
|------|--------|----------------------|----------------|
| Tier count + gate key | computed chrome rects | `utilityTier.height:40`, `primaryBarHeight:88`, total 128; **not** `twoTier` alone | C22 |
| Utility trailing cluster | chrome contract + crop | `trailing: [Log in, About, Search]` | C21 |
| Primary tabs + mega menus | source-chrome.v2 + open panels | 4 tabs, 5 mega panels w/ box + shot | C16 |
| Per-CTA register | computed actionGroups | height, padX/Y, radius, border per CTA | C3 |
| Content max width | computed | `contentMaxWidth: 1080` | C7 |
| Trigger chevron glyph + motion | motion-audit + corpus | asset, box, open transform; curation allowed | C21, AS-47 |
| Utility icons | harvested sprites | globe, search, chevrons; **viewBox = evidence** | C21, fix5 |
| Logo renderable | assets | wordmark svg + dimensions | C7 |
| Bar affordances | corpus | language dropdown, search icon-button | C21 |
| Surface presentation | computed | bg, ink, link colors, separator | C7 |

### 2.2 Footer chrome

| Fact | Source | Example | Validator / AS |
|------|--------|---------|----------------|
| Column grid | measured.grid | 5 tracks, `wrapperSizes`, heading/link styles | C16 |
| Muted heading style | computed | 14px/500 cream headings | C7 |
| Social row | chrome + assets | 7 glyphs, kind icon, ink 62% cream | C16 |
| Legal + policy links | grounding + contract | `legal.text` + `{label,href}[]` | C7 |
| Divider presence | crop | hairlines flanking social | C16 |
| Bottom bar anatomy | crop | `bottomBar.anatomy: centered-stack`, `textAlign: center` | C7 |
| Wordmark placement | pixel measure | centered 98×28 between social and legal | fix1-11 |
| Surface | computed | `#1f1f1f` bg, cream ink | C7 |
| `controls: onInverse` | N/A on footer links | icon-link register for socials | AS-35 |

### 2.3 Section / band patterns (shared)

| Fact | Source | When required |
|------|--------|---------------|
| `contentShape.bandPadding` | section-rects vs css `--cl-section-padding-*` | Band deviates from site ladder |
| `contentShape.bandRhythm` | box-to-box rects | Hero / asymmetric stacks |
| `stackMeasure` | computed h1 width + line-break probe | Display headings that wrap |
| `surfaceIntent` + measured surface role | computed band bg | Every pattern |
| `archetypeRef` + `alignment` | grounding layout | split vs grid (Remote gate) |
| `recipeRef` | 2+ sections same rail anatomy | headrail, card plate families |
| `specialTreatments` | grounding + interaction captures | carousel, tabs, edge-cut, dotted-rule-rail |
| `deviceGeometry` | computed | cardWidth, cardGap, contentSpan, media fraction |
| `mediaScale.item` | computed uniform frames | logo strips, mark rows |
| `actionGroup` override | computed group rects | When ≠ brand default gap |
| `mediaComposition` | grounding arrangement | state-swap, marquee, bg+fg |
| `headingRegister` | computed tier map | When pattern ≠ default h2 |

### 2.4 Card / module families

| Fact | Source | Notes |
|------|--------|-------|
| Card rect + inter-card gap | computed grid gap / edge-cut track | 17px edge-cut vs 32px grid = record both |
| Inter-item gap (in-card) | computed body→link seam | cardActionGap per pattern |
| Action-group seam | computed | body-to-cta rung or override |
| Media aspect + scale | grounding + assets | product-ui vs spot-icon vs photograph |
| Type register | computed | h3 24px cards vs h4 22px statements |
| Container width | computed content column | 1080 spine |
| Band padding | css-rules section utilities | xs/s/md/lg ladder |
| Alignment + counterweight | grounding | split + cards; grid stays header-above |
| Grid equalization | observed row heights | C20 when card-grid |
| Surface + border + radius | computed + css tokens | 8 vs 16 radius families |

### 2.5 Primitives & control families

| Primitive | Required measured facts |
|-----------|-------------------------|
| **Eyebrow** | size (14px), case, weight, gap to heading (bandRhythm or ladder) |
| **Tag/pill** | height, pad, radius, border, bg; chip box for headrail |
| **List item** | gap, glyph asset (checkmark), indent; marked-list device license |
| **Content block** | heading/body registers, stack gaps |
| **Card variants** | pad, radius, border, media-well fill, in-card CTA family |
| **Stat** | value/label registers, pair gap, separator rule |
| **Badge** | dimensions, rating chip if present |
| **Link** | ink, underline device, arrow glyph, hover motion |
| **Button states** | per family: bg/fg/border/radius/height/pad + hover/active/disabled; onInverse variant when dark band |
| **Text CTA** | glyph asset + size; fit-content width behavior |
| **Round/icon control** | diameter 48×48, icon-only, no label bleed | AS-78 |
| **Toggle** | capsule track, circular knob, state vars | AS-79 |

---

## 3. COMPUTED-STYLES-AS-TRUTH MAP

### 3.1 Must bind to `evidence/computed-styles.json` (or css-rules / section-rects / motion-audit)

| Domain | Facts | Vision may corroborate, not override |
|--------|-------|-------------------------------------|
| **Tokens** | Color rgb/hex per role, type px/rem tiers, spacing px, radius px | Approximate hex in grounding |
| **Buttons** | Family matrix: height, padding, border, radius, states; **visibleLabel** vs **accessibleName** | Button labels in grounding |
| **Chrome** | Bar heights, contentMaxWidth, footer grid, link styles | Nav/footer prose |
| **Action groups** | gap, alignment rects, painted edges | “two CTAs side by side” |
| **Containers** | 1080px spine, column widths, card grids | “contained layout” |
| **Hero** | h1 rect width, line count, scrim from css-rules | Photo description |
| **Carousel/tabs** | Control size, placement rail vs overlay, tab underline color | Tab “pill” misread |
| **Logo strip** | Uniform item boxes 153×76, gap 69 | Logo count |
| **Motion** | durations/easing per selector | “smooth transition” |
| **Fonts** | computed font-family stack → self-hosted files | Serif/sans names |
| **Surfaces** | band bg colors → surface roles (incl. `#f9c9c0` accent-soft) | “warm band” |

**Projection boundary:** `brand_pipeline/contract_projection.py` must fill measured controls from computed samples (`test_harness_regression_quality.py:25-38` — prefer 68px `.cl-button` over 140px nav wrapper).

### 3.2 Vision grounding owns (semantics / copy / intent)

| Domain | `evidence/grounding/*.yaml` | Never guessed from CSS alone |
|--------|----------------------------|------------------------------|
| Verbatim copy | All visible text → `section-copy.yaml` | — |
| Component anatomy labels | split vs grid, testimonial photo+quote | — |
| Media creative direction | roles, collage vs screenshot | — |
| `componentAnatomies` → recipes | recurring rails | — |
| `mediaAssets` kind/rights | partner vs client marks | — |
| Use-case / intent | “closing bookend”, “proof strip” | — |
| Slot role prose | drives action hints (outlined secondary) | — |
| Disclosure/tab panel copy | per-tab content | — |

### 3.3 v3 facts authored from vision that should have been computed

| Fact | v3 symptom | Correct source |
|------|------------|----------------|
| Button height 140px | Square mega-sized CTAs in harness | computed `.cl-button` rect h=68 |
| Primary canvas for sec-04 | Wrong surface + layout archetype | computed band bg `#f9c9c0` |
| Missing edge-cut + headrail | Agent carousel 0.82→0.89 band | grounding + computed track geometry |
| Font family generic | Metric drift product-grid height | css `--cl-font-*` + woff2 files |
| layoutCopy namespace | Blank “Powered by AI / hubspot-v3” | deterministic rekey to layout ids |
| `brand.name` lane slug | Specimen heading leak | public brand identity + C29 |
| Carousel static layout | Platform carousel residual | section-rects + controls placement |

---

## 4. PER-SECTION DIFF-CORRECTION LOOP DESIGN

### 4.1 Existing scorer (baseline)

`brand_pipeline/compose_replica.py`:

1. Compose measured-only page → Playwright shoot @1440 → `replica-fullpage.png`
2. Pair bands: source `section-rects.json` ↔ live replica DOM bands (`page-nav`, `#sec-N`, footer)
3. Score per band (`band_similarity`, lines 351-381):
   - **structure** (0.5): 64px-wide grayscale downsample
   - **pixel** (0.3): 720px RGB MAE
   - **height** (0.2): min(h)/max(h)
   - **widthFidelity**: content span fraction (catches hug-collapse blind spot, lines 660-673)
4. Overall = height-weighted mean of band scores (lines 644-645)
5. Outputs: `compose/replica/replica-report.md`, `diff/*.png` pairs, `punch_list` (threshold **0.85**, line 69)

`brand_pipeline/pipeline_flow.py` G4 (lines 331-464): bounded loop (`DEFAULT_MAX_ITERATIONS=3`), optional `repair_hook`; stops if no progress; status `needs_iteration` with `bandDiagnostics`.

### 4.2 Proposed extraction-time loop (replaces manual fix1…fix7)

```
FOR each layout in capture order:
  1. MEASURE  → slice band rect; refresh computed-styles for band scope
  2. AUTHOR   → patch pattern/layout/chrome facts (single section)
  3. RENDER   → compose_replica section-scoped OR full page
  4. DIFF     → band_similarity vs source crop
  5. AUTO-TUNE → map low subscores to fact knobs (table below)
  6. REPEAT   → until band ≥ 0.90 OR 3 no-progress iterations
AFTER all sections: full-page G4 ≥ 0.90
```

**Stop criteria per band:** score ≥ 0.90; or Δscore < 0.01 for 2 iterations; or iteration budget exhausted → emit punch-list row for human review.

**Stop criteria overall:** weighted overall ≥ `DEFAULT_REPLICA_BAR` (0.90); all bands ≥ 0.85; zero C errors.

### 4.3 Band-type → auto-tune knobs

| Low subscore / band type | Tune (computed-first) |
|--------------------------|------------------------|
| **height** < 0.8 | bandPadding, bandRhythm, missing slots, card count, static carousel panels |
| **widthFidelity** < 0.72 | stackMeasure, contentMaxWidth, media fraction, collapse hug-center (containment) |
| **structure** < 0.8 | archetypeRef (split/grid), recipeRef, specialTreatments (tabs/carousel/edge-cut), column counts |
| **pixel** < 0.7 | surfaceIntent, onInverse registers, scrim/overlay color, glyph channel, font files |
| **hero** | bandPadding, scrim rgba, stackMeasure, bandRhythm, secondary family hint |
| **logo-wall** | mediaScale.item, gap, headingRegister |
| **platform-carousel** | controls.placement=rail, panelcar containment, slide copy binding |
| **product-grid** | split alignment, recipe headrail, cardActionGap, accent surface |
| **agent-carousel** | edge-cut cardWidth/Gap, headrail recipe, pause control |
| **testimonial-tabs** | tabs treatment, media fraction 0.56, activeUnderline, panel copy |
| **closing-cta** | stackMeasure, actionGroup gap, onInverse secondary |
| **page-nav** | utilityTier, ctas[], contentMaxWidth, chevron assets |
| **footer** | bottomBar anatomy, column wrapperSizes, social glyphs |

### 4.4 Replaces manual fix passes

| Manual era | Automated equivalent |
|------------|---------------------|
| fix1 punch list (12 items) | Per-band diff loop + completeness checklists §2 |
| fix2 recipes/glyphs | C23 + extraction recipe promotion from grounding |
| fix3 containment/AG | AS-56/60/61 as post-author lint + measure-driven stamps |
| fix4 glyphs | curate single-ink verification at asset harvest |
| fix5 viewBox | C8 extension: glyph viewBox vs getBBox |
| fix7 devices | accentDevices authored when grounding + css agree |

**Repair hook interface:** extend `repair_replica_data.py` pattern — deterministic projection from `last_report["bandDiagnostics"]`, no model call, until pluggable LLM repair for semantic copy only.

---

## 5. GAP LIST (prioritized extraction-time checks)

| P | Gap | Candidate gate | Evidence |
|---|-----|----------------|----------|
| P0 | **Join-key integrity** (layout/layoutCopy/pattern id) | C4 (done) | hubspot-v3 harness-regression-audit.md:27-38 |
| P0 | **Internal lane id in public copy** | C29 (done) | changes.md:2026-07-20 |
| P0 | **Button family sample = tallest wrapper not control** | C3 + projection (done) | harness-regression-audit.md:20 |
| P1 | **bandPadding vs section-rects** | **C30**: band content box inset matches authored padding ±8px | fix1-1 |
| P1 | **Per-pattern bandRhythm overrides** | **C31**: when hero rect seams differ >20% from ladder, require bandRhythm | fix1-4 |
| P1 | **Vision/css scrim precedence** | **C32**: photo-hero must cite css-rules overlay when present | fix1-2 |
| P1 | **mediaScale.item for logo strips** | **C33**: logos pattern requires item box or notObserved | fix2-A1 |
| P1 | **Carousel control placement** | **C34**: carousel treatment requires controls.placement from computed | fix3 |
| P1 | **Tab anatomy vs grounding** | **C35**: tabs treatment must match grounding underline/pill flag | fix1-9 |
| P1 | **Glyph viewBox evidence** | **C36**: chrome glyph viewBox spill ≤5% (extend C8) | fix5 |
| P1 | **Surface role from measured band bg** | **C37**: band bg maps to declared surfaceIntent | v3 sec-04 |
| P2 | **accentDevices floors** | **C38**: hero/closing contexts require licensed device or waiver | fix7 |
| P2 | **Recipe auto-promotion** | strengthen C23 to error when ≥2 grounding anatomies match | fix2-U1 |
| P2 | **Split archetype gate** | **C39**: alignment.counterweight:cards requires archetypeRef split | Remote fix1 triage |
| P2 | **Harness digest freshness** | G3 digest (done) — extend to layout demos in CI | v3 stale SHA |
| P3 | **Video-static capability** | punch-list capability flag, not extraction | manifest punch_list |
| P3 | **Mega open panel scoring** | optional open-state chrome shot in diff | manifest |

**AS rules without strong extraction counterpart:** AS-62 (off-ladder invented magnitudes) → style-scale gate; AS-63 (declared knob no consumer) → composition lint; AS-67 (third-party marks) → media-assets C26.

---

## 6. SEQUENCED IMPLEMENTATION PLAN

> **Prerequisite:** hubspot-v3 re-author lands (parallel agent). **Do not collide** on shared author/renderer files until that merge settles.

### Phase A — Contract & gates (extraction-only, low collision)

| Step | Work | File targets | Tests |
|------|------|--------------|-------|
| A1 | Add C30–C37 as specified in §5 | `tools/extract/validate_brand_evidence.py` | `brand_pipeline/tests/test_brand_evidence_contract.py` |
| A2 | Document per-family checklists in schema | `brand_pipeline/spec/brand-schema.md` §4.x cross-refs | — |
| A3 | Extend layout-analyst skill: computed-first precedence table | `brand_pipeline/spec/layout-analyst-skill.md` | — |
| A4 | Staged-author prompts: require bandPadding/bandRhythm/stackMeasure when measure differs | `brand_pipeline/staged_author.py` | `test_harness_regression_quality.py` |

### Phase B — Projection & measure (collision-sensitive)

| Step | Work | File targets | Tests |
|------|------|--------------|-------|
| B1 | Band-scoped computed refresh helper | `tools/extract/measure_computed.py` | fixture rects |
| B2 | Auto surface role from band bg clustering | `brand_pipeline/contract_projection.py` | v3 sec-04 fixture |
| B3 | Recipe promoter from grounding anatomies | `brand_pipeline/contract_projection.py` | `test_contract_projection.py` |
| B4 | Glyph viewBox validator at curate | `tools/extract/curate_assets.py` | fix5 GlyphCropTest pattern |

### Phase C — Per-section diff loop (collision-sensitive)

| Step | Work | File targets | Tests |
|------|------|--------------|-------|
| C1 | `section_diff_loop.py`: measure→author patch→render→score | **new** under `brand_pipeline/` | synthetic band fixtures |
| C2 | Wire `repair_hook` in `pipeline_flow.py` G4 to deterministic tuner | `brand_pipeline/pipeline_flow.py` | `test_pipeline_flow.py` |
| C3 | Fact knob mapper from punch-list drivers | shares `compose_replica.run_diff` outputs | replay hubspot-v2 bands pre/post fix1 |
| C4 | Section-scoped compose entry | `brand_pipeline/compose_replica.py` | band score regression |

### Phase D — Verification

| Step | Work | Target |
|------|------|--------|
| D1 | hubspot-v3 G4 ≥ 0.90 without manual YAML edits | `runs/hubspot-v3/brand/` |
| D2 | hubspot-v2 ≥ 0.956, remote ≥ 0.951 regression | manifest replica scores |
| D3 | Full suite green | `brand_pipeline/tests` |
| D4 | Benchmark record | `benchmarks/extraction-learnings-2026-07-20/metrics.json` |

### Collision-sensitive files (coordinate before edit)

- `brand_pipeline/staged_author.py`
- `brand_pipeline/contract_projection.py`
- `brand_pipeline/compose_replica.py`
- `brand_pipeline/compose_page.py` / `compose_section.py` / `component_render.py`
- `brand_pipeline/render_components_preview.py`
- `runs/hubspot-v3/brand/*`

**Safe writes:** `tools/extract/validate_brand_evidence.py`, new test files, spec docs, benchmarks.

---

## Appendix A — AS rule index (intent → extraction fact)

| AS | Intent | Polices |
|----|--------|---------|
| AS-01 | Surface-aware color tokens | `tokens.surfaces.*`, per-surface borders/ink |
| AS-02 | Truthy fallback traps | token resolution in authored CSS vars |
| AS-03–04 | Geometry-derived spacing | bandRhythm, spacer derivation |
| AS-05 | Absolute positioning anchor | pattern device geometry |
| AS-08 | max-width + centering | containment law inputs |
| AS-11 | Under-filled sections | layoutCopy completeness |
| AS-14 | Form purpose copy | form slot + note |
| AS-20 | Hover colors per surface | button state facts per surface |
| AS-26 | Slot-faithful adapters | layouts[].slots ↔ archetype |
| AS-27 | CTA shape brand-law-first | buttons.* radius/height |
| AS-28 | Footer grammar variant | footer.bottomBar, grid |
| AS-44 | Pattern facts beat defaults | pattern overrides vs scaffold |
| AS-45 | Centered stack measure | stackMeasure vs prose width |
| AS-48 | Relational rhythm | tokens.spacing ladder |
| AS-49 | Header alignment grammar | layoutGrammar.headerContext |
| AS-50 | Grid equalization | card grid equalize facts |
| AS-53 | Silent slot drops | slot binding coverage |
| AS-56 | Container law | no private max-width on devices |
| AS-59 | One primary per action group | action slot role hints |
| AS-60 | Action group declared layout | actionGroup.align/gap |
| AS-61 | Text-link content hug | link width behavior |
| AS-62 | Off-ladder invented sizes | style-scale adherence |
| AS-66 | Display fit to measure | stackMeasure |
| AS-67 | Third-party mark legality | media-assets usageRights |
| AS-78 | Circle integrity | round control diameter |
| AS-79 | Control-family coherence | toggle vs button families |

Full list: `brand_pipeline/spec/anti-ai-slop.md` (AS-01–AS-79).

## Appendix B — C rule index (intent → extraction fact)

| C | Intent | Polices |
|---|--------|---------|
| C1 | brand.yaml parses + identity | `brand.name` mapping |
| C2 | Block contract coverage | `blocks.*` or notObserved |
| C3 | Button matrix + label fit | `buttons.*` families/states |
| C4 | Copy + join keys | section-copy, layoutCopy, slot types |
| C5 | Layout↔pattern | patternRef coverage |
| C6 | Logo assets | logo wall files |
| C7 | Chrome content + ranges | navbar/footer measured |
| C8 | Tagged assets exist | assets-tagged.json |
| C9 | Vision grounding | grounding/*.yaml |
| C10 | Card variants | blocks.card |
| C11 | Harness smoke | pattern compose |
| C12 | Escape hygiene | HTML entities |
| C13 | Motion evidence | tokens.motion |
| C14 | Canonical tier | meta.canonicalTier + ladders |
| C15 | Relational spacing | tokens.spacing rungs |
| C16 | Chrome depth | mega, footer grid, social |
| C17 | Disclosure bodies/media | layoutCopy items |
| C18 | Header alignment grammar | layoutGrammar.headerContext |
| C19 | Radius fidelity | tokens.radius vs census |
| C20 | Grid equalization | card-grid patterns |
| C21 | Bar affordances | chevrons, utility controls |
| C22 | Two-tier utility | utilityTier vs measured height |
| C23 | Recipe coverage | recipes + recipeRef |
| C24 | style-scale consistency | style-scale.yaml |
| C25 | Signatures | brand signatures block |
| C26–28 | Media semantics | media-assets.yaml |
| C29 | Internal-id leak | brand.name/wordmark ≠ lane slug |

Source: `tools/extract/validate_brand_evidence.py:12-158`.

---

## References

- HubSpot v2 fix history: `runs/hubspot-v2/brand/changes.md` (fix1–fix7, pass1–3)
- Pattern facts: `runs/hubspot-v2/brand/layout-library.yaml`
- Chrome/nav/footer: `runs/hubspot-v2/brand/brand.yaml:1208-1690`
- Remote lane: `runs/remote/brand/changes.md`
- v3 harness audit: `runs/hubspot-v3/brand/harness-regression-audit.md`
- v3 G4 residuals: `runs/hubspot-v3/brand/changes.md:6-29`, `manifest.json:331-342`
- Replica scorer: `brand_pipeline/compose_replica.py:65-699`
- Pipeline G4 loop: `brand_pipeline/pipeline_flow.py:331-464`, `brand_pipeline/spec/pipeline-flow.md:44-52`
- Extraction doctrine: `brand_pipeline/spec/extraction-grounding-prompt.md`, `brand_pipeline/spec/layout-analyst-skill.md`
