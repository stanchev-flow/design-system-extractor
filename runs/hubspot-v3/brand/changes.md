# HubSpot v3 — lane changelog

Fresh, clean-room HubSpot extraction and generation experiment using the current
uncommitted canonical pipeline. Source: `https://www.hubspot.com/`.

## Button geometry — primary/secondary render too large (2026-07-22, HELD FOR REVIEW)

The replica + generated primary/secondary CTAs rendered too large versus a source
getComputedStyle capture of the real HubSpot primary button (background `#ff4800`, color
`#fff`, `"HubSpot Sans"` 16px/500, line-height 28px, padding 12px/24px, height 56px, border
`2px solid transparent`, radius 8px). All fixes are **fact-gated, brand/palette-agnostic**
(no hardcoded brand values, no section-specific token names). **Held for review — no commit.**

### Fact → CSS trace (with file:line)

`buttons.primary.<fact>` (`runs/hubspot-v3/brand/brand.yaml`) → emitted `--button-*`
(`brand_pipeline/tokens_css.py` `emit_layer1`, L534–567: `pairs` loop + `_button_size_rem`)
→ aliased to `--c-button-*` (`brand_pipeline/component_render.py` `component_vars`, L239–258)
→ consumed by base `.c-button` (`_BUTTON_VARIANT_CSS`, L1639–1665) → replica/generated
`index.html`. The measured button family is a **faithful pass-through**: the renderer
emitted exactly the facts it was given.

### Root cause — wrong captured VARIANT (not a renderer defaulting bug for size/pad/height)

`evidence/computed-styles.json` carries THREE primary variants:
`-small` (14px / 8px 16px / 42px), **`-medium` (16px / 12px 24px / 56px, lh 28px, border
`2px solid transparent`)**, and `-large` hero CTA (18px / 16px 40px / 68px, lh 32px).
Extraction selected the oversized **`-large` hero instance** (`selectorClasses: cl-button
-primary -large … homepage-hero`) as the representative primary, so `buttons.primary`
carried the hero magnitudes. The user's ground truth is the **`-medium`** control — which is
*exactly* what `hubspot-v2` captured (`--button-height 3.5rem` = 56px, `--button-pad 0.75rem
1.5rem` = 12/24, border `2px solid transparent`), the cross-run reference confirming v3's
extraction regressed to the wrong variant.

### Per-value classification

| value | before | after | class |
|-------|--------|-------|-------|
| font-size (`--button-size`) | 1.125rem (18px) | **1rem (16px)** | wrong captured fact (`fontSize`) |
| padding (`--button-pad`) | 16px 40px | **12px 24px** | wrong captured fact (`padX/padY`,`padding`) |
| height (`--button-height`) | 68px | **56px** | wrong captured fact (`height`) |
| weight (`--button-weight`) | 500 | 500 | correct (no change) |
| radius (`--button-radius`) | 8px | 8px | correct (no change) |
| border (`--button-border`) | `none` → rendered `border: none` | **`2px solid transparent`** | BOTH: wrong captured fact (`border: none`) **AND** renderer default — base `.c-button` hardcoded `border: none` and never consumed `--c-button-border`, so even a correct fact could not render |
| line-height | (no button fact/var) | fact `lineHeight: 28px` added | documented (height is explicit + `box-sizing: border-box`, so lh does not change the box) |

### Fix (fact-gated, generic)

1. **Facts** (`runs/hubspot-v3/brand/brand.yaml`): corrected `buttons.primary` + `buttons.secondary`
   to the measured `-medium` geometry (16px / 12px 24px / 56px / lh 28px), set
   `buttons.primary.border: 2px solid transparent` (secondary already `2px solid #ff4800`),
   and updated `geometryProvenance` to the `-medium` selector + a `correction` note recording
   the extraction gap (variant selection should prefer the modal/default control, not the
   largest hero instance). Secondary corrected alongside to keep the measured CTA pair
   height-consistent.
2. **Replica hero override** (`runs/hubspot-v3/brand/responsive-facts.yaml` `hero.primaryButton`):
   this sidecar carried the SAME over-measured hero action (18px / 32px lh / 16px 40px, from
   `action-40`) and is applied hero-scoped (`component_render.hero_primary_button_css`,
   emitted only on the REPLICA target — `merge_brand_facts` excludes `hero.primaryButton` on
   GENERATION). Corrected to the `-medium` truth (16px / 28px lh / 12px 24px) so the replica
   hero button is consistent with the fixed `--button-height: 56px` (otherwise 18px+16/40 in a
   56px border-box would overflow). Documented the extraction gap in its `provenance.correction`.
3. **Renderer** (`brand_pipeline/component_render.py` `_BUTTON_VARIANT_CSS` L1654): base
   `.c-button` now emits `border: var(--c-button-border, none)` instead of hardcoded
   `border: none`, so the PRIMARY family (which rides the base rule) consumes its measured
   border. Fallback `none` keeps brands without a primary border fact byte-identical.

### Cross-brand impact (byte-identity)

The base-rule change is shared, so every brand's `.c-button` rule text gains
`var(--c-button-border, none)`. Computed effect (verified by re-composing each replica to a
temp dir + a getComputedStyle probe):
- **remote** — primary `border: none` → computed border **unchanged** (`0px none`): visually byte-identical.
- **hubspot-v2** — carries measured `border: 2px solid transparent` that was being dropped;
  now renders it. `box-sizing: border-box` keeps the 56px box unchanged and the border is
  transparent → **no visual change** (same defaulting bug, now consumed).
- **woodwave-v2** — carries measured `border: 1px solid #fbf4ed` that was being dropped; now
  renders a **visible hairline** (the correct measured value). **Shares the same defaulting
  bug** — its committed replica (stale) will gain the hairline when next re-rendered. Not
  re-rendered here (isolated worktree); documented as the expected correct behavior.

### Verification

- **Computed-style probe (post-fix, @1440)** — replica hero CTA + generated-page CTA both:
  `height 56px, font-size 16px, font-weight 500, font-family "HubSpot Sans", sans-serif,
  padding 12px 24px, border 2px solid rgba(0,0,0,0), border-radius 8px, line-height 28px,
  background rgb(255,72,0), color rgb(255,255,255)` — matches the user's snapshot exactly.
- **C1–C28** (`validate_brand_evidence`): hubspot-v3 / hubspot-v2 / remote / woodwave-v2 all
  **0 errors**. v3 `style-scale.yaml` digest refreshed (`normalize_scales.py`) so C24 stays clean.
- **Full suite** (`./venv/bin/python -m pytest brand_pipeline/tests tests`): **2127 passed,
  3 failed** — the 3 are the known pre-existing failures (relume prompt guidance ×2 +
  runtime site-model defaults) — **zero NEW failures**.
- **New tests**: `tests/test_tokens_css.py` `ButtonGeometryCorrectionTests` (medium-geometry
  pass-through, measured-border emission, hubspot-v2 reference) + `tests/test_responsive_facts.py`
  `test_base_button_consumes_measured_border` (base `.c-button` consumes `--c-button-border`).
- **Re-rendered**: `compose/replica` + `compose/ai-product-launch` `index.html`. `viewer.html`
  regenerated.
- **Before/after crops** in `fix-shots/`: `button-before-hero@1440.png`,
  `button-after-hero@1440.png`, `button-before-after@1440.png` (replica);
  `gen-button-before@1440.png`, `gen-button-after@1440.png`, `gen-button-before-after@1440.png`
  (generated page). Probe helper: `fix-shots/_shoot_button.py`.

**Files changed:** `brand_pipeline/component_render.py` (base-rule border consumption +
family-override comment), `runs/hubspot-v3/brand/brand.yaml` (primary/secondary facts),
`runs/hubspot-v3/brand/responsive-facts.yaml` (hero primaryButton correction),
`runs/hubspot-v3/brand/style-scale.yaml` (digest refresh),
`brand_pipeline/tests/test_tokens_css.py` + `brand_pipeline/tests/test_responsive_facts.py`
(new tests), re-rendered `compose/replica/*` + `compose/ai-product-launch/*`, `fix-shots/*`,
`viewer.html`. **Held for review — not committed.**

## Generated hero — overlap + oversize fix (2026-07-22, HELD FOR REVIEW)

Fixed the `compose/ai-product-launch` hero ("misaligned text" + "hero too large") at the
shared archetype/renderer level (fact-gated, brand/palette-agnostic). Two generic fixes:
(1) `compose_overlay` now GROUPS co-column overlay-hero copy slots into one flowing anchored
stack (folding the co-anchored CTA in reading order, insetting a full-bleed left column to
the content-container gutter) instead of piling each at a shared `top`; the stack CSS ships
only via a `build_page` gate so every stack-less page stays byte-identical. (2) The measured
hero-height mechanic (`heightRule`/`navOffset`) + hero-scoped heading-shrink ladder are
promoted into the generation fact-merge (consumed by `hero_responsive_css`), so a composed
full-bleed hero fills the measured `viewport-minus-nav` band (1088px→772px @1440) instead of
the inflated `min(90svh,54rem)` default. A current-pipeline regeneration attempt reproduced
the same bad hero (and regressed), confirming an archetype/renderer defect, not staleness.
Replicas: v3 + woodwave-v2 byte-identical; v2 + remote differ only by the earlier held
font/card fixes. Full detail + before/after shots: `compose/ai-product-launch/changes.md`
and `fix-shots/gen-hero-*`.

## shadcn-bakeoff harvest — button font family/size + spacing diagnosis (2026-07-22, held for review)

Harvest of the two axes where the `experiment/shadcn-radix-bakeoff` build read better than
our renderer for hubspot-v3 (bakeoff verdict = "harvest, don't migrate"). All fixes are
**fact-gated, brand/palette-agnostic** (no hardcoded brand values, no section-specific token
names). **Held for review — no commit.**

### Axis A — BUTTON FONT (real renderer binding bug ×2, class (i) → FIXED)

**Symptom (proven, not vibes).** Live computed-style probe of the pre-fix replica hero CTA
("Get a demo"): `font-family: "\"HubSpot Sans\", sans-serif", "Source Serif 4", serif` →
resolved to **Source Serif 4 (serif) at 14px**. The whole body/eyebrow/control register
rendered serif. shadcn's button (`button.tsx` `font-medium` + body `--font-sans: "HubSpot
Sans", …`) rendered crisp **HubSpot Sans 18px/500** — measured verbatim from
`brand.yaml#buttons.primary` (`fontSize:18px`, `fontWeight:500`) and
`tokens.manifest#--font-control-text`. The measured button font is **HubSpot Sans (body
sans), 18px, weight 500** — we were emitting a serif proxy at 14px.

**Root cause 1 — family stack (`brand_pipeline/tokens_css.py`).**
- `_generic_family()` substring-matched `"serif"` INSIDE `"sans-serif"`, so a declared sans
  family stack (`"HubSpot Sans", sans-serif`) was classed **serif** → pulled the serif Google
  proxy `Source Serif 4` and a `serif` generic fallback.
- `_emit_type_tier()` / `font_stack()` wrapped the WHOLE declared family stack in a single
  extra layer of quotes (`f"'{fam}'"`), turning `"HubSpot Sans", sans-serif` into ONE invalid
  family token `'"HubSpot Sans", sans-serif'` that no font matches — so the browser fell
  through to the serif proxy. (Self-hosted `@font-face 'HubSpot Sans'` was never reachable.)
- Fix: `_generic_family` now returns a declared stack's OWN trailing CSS generic keyword
  verbatim (via `_split_families`/`_unquote_family`, guarded by `_CSS_GENERICS`); a new shared
  `_family_css()` preserves a declared multi-member stack VERBATIM (members already valid
  tokens; no re-quoting) and injects NO off-brand auto-proxy ahead of a self-hosted face, while
  a BARE single family name keeps the historical single-quoted emission + loadable proxy
  (byte-stable). `_emit_type_tier`, `font_stack`, and the button-family stack builder all route
  through it. Result: `--font-body`/`--font-control-text`/`--font-eyebrow` = `"HubSpot Sans",
  sans-serif`; `--font-display-hero` = `"HubSpot Serif Page Header Human", "HubSpot Serif",
  serif`; the stray Google-Fonts `Source+Serif+4` `<link>` is gone (page is self-host correct).

**Root cause 2 — button size/weight (`tokens_css.py` + `component_render.py`).** hubspot-v3's
captured button facts carry the raw computed keys `fontSize:"18px"`/`fontWeight:500` (no
family), while the emitter only read the authored `sizeRem`/`weight`/`font` schema that the
other brands use — so `--button-size`/`--button-weight` were never emitted and the button
leaked the control-text size (`0.875rem` = 14px) + heading weight. Fix: `emit_layer1` now
also reads `fontSize` (px→rem via `_button_size_rem`), `fontWeight`, and `fontFamily`;
`component_render.component_vars` binds `--c-button-size`/`--c-button-weight` for either
schema. hubspot-v3 primary/secondary CTAs now render **HubSpot Sans 18px/500** (tertiary
utility keeps its measured 14px); the absent measured button family correctly rides the body
sans face (no `--button-font` invented).

**Verified (post-fix live probe).** hero CTAs `font-family: "HubSpot Sans", sans-serif`,
`font-size 18px`, `font-weight 500` — matches shadcn. Flows to generated pages too
(`compose/ai-product-launch` re-rendered deterministically: `--font-body: "HubSpot Sans",
sans-serif`, buttons 18px, no Google-Fonts link).

### Axis B — SPACING RHYTHM ("felt more structured")

Concrete rendered-px comparison (Playwright) vs shadcn:
- **Section vertical padding is measured PER-SECTION** and faithful — the inline
  `--c-section-pad-top/-bottom` values (70/110, 80/90, 90/60, 88, 24/40 px …) reproduce the
  source's own per-band rhythm and match shadcn's equivalent bands (both derive from the same
  facts). Snapping these to a single scale would DESTROY measured values → **not touched**.
- **Intra-stack relational rhythm already snaps to the measured scale**: eyebrow→heading
  `--space-eyebrow-to-heading` = 20px, heading→body / body→cta `--space-heading-to-body` /
  `--space-body-to-cta` = 40px, applied consistently via the header-cluster + `cs-module--anatomy`
  owl-margin ladders. Not a bug.
- **The dominant "less structured" perception was font-driven**: the serif mis-render (Axis A)
  gave the body a looser serif metric at `line-height:1.75`; the Axis-A fix restores the crisp
  sans register and materially tightens the perceived rhythm (see before/after strips).
- **Residual (class (ii) — needs a NEW captured fact, NOT a safe binding fix):** the flat
  card/module internal micro-gap default `--cs-module-gap: 0.9rem` (~14px, off the clean grid)
  is an INVENTED structural value. It cannot be snapped to an existing measured token: the only
  candidate section-level rung `--space-block-to-block` measures **12px on hubspot-v3 but
  40–64px on hubspot-v2/remote/woodwave**, so binding card gaps to it would blow out card
  interiors on 3 of 4 brands. **Capture path:** measure the source card/module internal block
  gap (caption→body→cta inside a `.cs-module`) and emit a generic `card-block-gap` (or
  `module-block-rhythm`) spacing token, then bind `--cs-module-gap: var(--space-card-block-gap,
  0.9rem)`. Not done here (no invented px).

### Hero alignment — SHARED miss, deferred

Our hero centers the eyebrow/heading/body/CTA stack; the source (and shadcn) left-anchor it.
This is the known left-anchor hero-archetype issue and is a SHARED weakness (shadcn missed it
too at some viewports) — **documented, deferred to the hero-archetype work**, not chased here.

### Files changed
- `brand_pipeline/tokens_css.py`: `_CSS_GENERICS`, `_split_families`, `_unquote_family`,
  `_button_size_rem`, rewrote `_generic_family`, new `_family_css`, `font_stack` +
  `_emit_type_tier` route through it, button emit reads `fontSize`/`fontWeight`/`fontFamily`.
- `brand_pipeline/component_render.py`: `component_vars` binds `--c-button-size`/`-weight`
  from either capture schema.
- Tests: `tests/test_tokens_css.py` (+`FontStackShapeTests`, +`ButtonFontFactSchemaTests`),
  `tests/test_structural_variants.py` (+2 `--c-button-*` binding cases).

### Verification
- New/relevant units: `test_tokens_css.py` 23 pass, `test_structural_variants.py` pass.
- Full suite: **3 failed, 2106 passed** — the 3 are the known pre-existing (relume ×2 +
  runtime-defaults ×1); **no NEW failures**.
- Byte-identical guard: `emit_layer1` index diffed vs on-disk token manifests →
  hubspot-v2/remote/woodwave-v2 **0 diffs**; hubspot-v3 exactly the 19 intended token diffs.
- C1–C28 validator: **0 errors** on hubspot-v3 / hubspot-v2 / remote / woodwave-v2.
- `css_fidelity` hubspot-v3: **critical 0** (5 high / 8 medium / 4 low — pre-existing crop
  artifacts; zero button-font divergences). Replica gate re-run: overall 0.921, desktop
  responsiveness-health 1.000 (375 = 0.893, pre-existing edgecut carousel gap).
- Re-rendered `compose/replica` + `compose/ai-product-launch`; regenerated `viewer.html`.
- Before/after @1440 shots in `fix-shots/`: `compare-hero-before-after-shadcn.png`,
  `compare-agents-before-after-shadcn.png`, `compare-generated-page-before-after.png`
  (+ raw `cmp-*` / `gen-*` frames). Held for review (no commit/push).

## Feature-card grid fidelity batch — inset-card-on-canvas (2026-07-22, held for review)

Fixes the `sticky-copy-with-card-grid` section (`sec-3`, "Growing a business is hard.
HubSpot makes it easier." — Marketing Hub / Sales Hub / …). The source shows each hub as
a **white card with a hairline outline border + rounded corners on the warm canvas**, a
**hairline rule under the icon+title header**, a **small icon inline-left of the title**,
and a **"Learn more →" arrow link**. Our render dropped the card surface/border entirely
(transparent on canvas), stacked an oversized glyph ABOVE the title, and dropped the header
rule. All fixes are **fact-gated, brand/palette-agnostic** (no hardcoded brand values, no
section-specific token names) and reuse the brand's own surface-role + card-device grammar.

### Per-sub-element classification

| sub-element | classification | evidence |
|-------------|----------------|----------|
| card surface (white) | **captured-but-dropped** | `surfaceGrammar.cardOn: surface/white`; `surface/white` `schemeMode: Container` (#ffffff); `blocks.featureGrid.surface: surface/white`; signature "white cards … on warm canvas" |
| hairline border | **captured-but-dropped** | signature "…hairline border"; `layout-library` `cardAnatomy.borderApprox: 1px hairline`; `border/hairline-on-primary` token |
| radius (8–12px) | **captured-and-applied** (was invisible) | `blocks.featureGrid.cardRadiusPx: 12`; `radius.card`; `--radius-card`. Applied all along but unseen with no border + same-as-canvas fill |
| header divider | **captured-but-dropped** | `layout-library` `specialTreatments: dotted-divider` (target card-grid, "dotted rules separate icon-header, bullet list, and link") |
| small inline icon | **never-captured** (v3) | source shows icon inline-left of title; v2 captured `slots.icon.placement: heading-row`, v3 did not — renderer fully supports the fact |
| "Learn more →" arrow link | **captured-and-rendered** (no defect) | `blocks.featureGrid.cardLink: text-arrow`; already emits `c-arrow-link` |
| eyebrow pill + dotted leader | **never-captured-as-headrail** (v3) | source "Powered by AI" is an outlined pill + dotted leader (v2 captured "bordered PILL … joined by a dotted rule"); v3 captured it as a plain `role: eyebrow`. NOT forced — see below |
| ✓ checkmark benefit markers | **never-captured** | the 2-bullet benefit list is flattened to a single `body` string in `section-copy.yaml`/composition — no list structure or marker fact exists to consume |

### Root cause

The renderer's `card_panel_role(doc)` (`compose_section.py:4129`) correctly SELECTS the
brand's Container surface role (v3 = `surface/white`), but its return value was only used as
a boolean (`plated`, `compose_section.py:4181`) — never wired into the plate paint. The
plate CSS (`SCAFFOLD_CARD_PLATE_CSS`, `compose_section.py:7602`) painted the generic page
panel `var(--c-panel)` (= `surface/panel`, which in v3 aliases `surface/primary` #fcfcfa =
the section canvas) and carried **no `border` rule at all**. So the white-card fill AND the
hairline border were both dropped. (In hubspot-v2/remote/woodwave the Container surface is
*named* `surface/panel`, so `--c-panel` already resolved to it — which is why only v3 mis-
rendered.) The inline icon needs a card-device `slots.icon.placement: heading-row` fact
(`compose_section.py:4334`) v3 never captured; the divider treatment is dropped at the demo
adapter (`render_components_preview.py:1957` `known_kinds` excludes `dotted-divider`).

### Fix (generic, fact-gated)

- **Card surface + outline** (`compose_section.py` `compose_features_cards` ~L4470 + `SCAFFOLD_CARD_PLATE_CSS` L7602):
  a plated grid whose brand declares a Container surface role DISTINCT from the page panel
  re-points `--c-card-plate-bg` at that role's own `var(--surface-…)`; when that surface's
  grammar records a resting `border` fact it draws `--c-card-plate-border: 1px solid
  var(--c-panel-hairline)` (or a verbatim CSS border value). The plate CSS now reads
  `background: var(--c-card-plate-bg, var(--c-panel))` and `border: var(--c-card-plate-border,
  none)`. **Doubly fact-gated:** a brand whose container role IS `surface/panel` emits no bg
  override, and a surface with no `border` fact draws no outline → byte-identical.
- **Card header divider** (`compose_features_cards` ~L4190/L4312 + plate CSS): a card device
  declaring `headerDivider` emits an `<hr class="cs-module-divider">` between the icon+title
  header and the body (only when the card renders a header + body). Absent ⇒ no rule.
- **Inline icon**: added the captured `blocks.card.slots.icon.placement: heading-row` fact to
  `brand.yaml` (the renderer's heading-row path already existed for hubspot-v2).
- **`brand.yaml` facts (v3 only):** `surface/white.border: hairline`; `blocks.card.headerDivider:
  hairline`; `blocks.card.slots.icon {placement: heading-row, size: 1.5rem}` — each with
  provenance prose tied to the section-03 measurement.

**Eyebrow pill + checkmarks NOT forced.** The eyebrow *should* route through the existing
`section-headrail` `outlined-pill` treatment, but this section's rail has **no trailing
action** (the dual CTA lives below the body), whereas the current headrail path renders a
trailing CTA whenever the section authors one — routing it as-is would inject a duplicate
`Get a demo` on the rail, and `legacy_pill_wrap=False` on the cards path would not even
produce the pill. Correct capture path: add a headrail `recipeRef {recipe: section-headrail,
variant: outlined-pill}` to the pattern's header slot **with a structured
`trail {present: false}` + dotted rule + bordered pill variant**. The ✓ checkmark markers have
**no captured list structure** (benefits are a single flattened `body` string); restoring them
needs re-authoring the benefit list into structured items + a checklist marker fact. Both are
left as documented never-captured gaps per fact-gating discipline ("absent facts → current
behavior"), not fabricated.

### Verification

- **C1–C28** (`validate_brand_evidence`): v3 / v2 / remote / woodwave-v2 all **PASS, 0
  errors** (v3 11 warnings, unchanged from baseline after refreshing the derived
  `style-scale.yaml` for the new brand.yaml hash).
- **Byte-identity:** `hubspot-v2` + `remote` replicas re-rendered to temp and diffed against
  the committed builds — the ONLY delta is the shared plate-CSS scaffold text (added var
  fallbacks that resolve to the identical computed values + `border: none` + an unused
  `.cs-module-divider` rule); **no HTML/structural change, no `--c-card-plate-*` decls, no
  divider elements** → rendering byte-identical.
- **Tests:** full `brand_pipeline/tests` suite **2013 passed, 0 failures**; top-level `tests`
  the 3 known pre-existing failures only (relume ×2, runtime-defaults) — **no NEW failures**.
  Added `brand_pipeline/tests/test_inset_card_on_canvas.py` (**12 tests**): plate-CSS var
  contract, distinct-vs-panel container bg gating, border-fact gating (+ verbatim CSS border),
  inline-icon headrow presence/absence, header-divider presence/absence.
- **Replica re-render:** `sec-3` fidelity **0.949** (health 1.000 @1440); overall replica
  **0.926**. Generated page (`ai-product-launch`) re-rendered — its card carousel now paints
  crisp white cards + hairline on the accent band (surface/border fix flows through
  `card_panel_role`, no icon/divider since those cards are media-well, not icon+title).
- **Screenshots** in `fix-shots/`: `replica-{before,after}-featuregrid-sec-3@1440.png`,
  `replica-featuregrid-sec-3-before-after@1440.png` (combined), `gen-{before,after}-cards-sec-3@1440.png`.
  Shot helper: `fix-shots/_shoot_featuregrid.py`.
- **viewer.html** regenerated.

**Files changed:** `brand_pipeline/compose_section.py` (renderer + scaffold CSS),
`runs/hubspot-v3/brand/brand.yaml` (3 fact additions), `runs/hubspot-v3/brand/style-scale.yaml`
(digest refresh), new test file, re-rendered `runs/hubspot-v3/brand/compose/replica/*`,
`fix-shots/*`, `viewer.html`. **Held for review — not committed.**

## Header / CTA / tab fidelity batch — D1/D3/D4 (2026-07-22, held for review)

Follow-up to `header-cta-tab-diagnostic.md` (READ-ONLY diagnosis of the proof region
`sec-6`/`sec-7` + hero `sec-0`). Three defects fixed at the shared-renderer / audit
level; all fact-gated, brand/palette-agnostic (no hardcoded brand values, no
section-specific token names). **D2 (background warmth) was NOT chased** — our token
`#fcfcfa` already matches the true HubSpot source pixel-for-pixel; Claude's warmer
cream is an embellishment that would *reduce* source fidelity.

| # | defect | classification | root cause (file:line) | fix | before → after |
|---|--------|----------------|------------------------|-----|----------------|
| D1 | two hero CTAs both filled/primary | captured-in-facts → dropped-in-render (replica overlay path) | overlay action emitter read `variant` (absent) not the authored `styleHint`, and processed the pair's two sibling slots (`actions` + `actions-secondary`) independently so `_outline` never became true | `compose_section.py` overlay emitter (~L5936): sibling action slots + list-authored pairs **coalesce into ONE `cs-ov-actions` group**; new `_action_register_outlined` / `_ov_actions_html` read the register per action from `styleHint`/`variant`/role and apply AS-59 (exactly one filled primary; siblings take the measured secondary register). Fallback `_i>0` demotion kept for unhinted list pairs. AS-59 audit gains an advisory split-group guard in `slop_audit.mjs` (~L77) for adjacent single-action groups | hero: `Get a demo` + `Get started free` **both filled** → filled primary + **outlined secondary** in one row |
| D3 | tab rail left-aligned (should be centered) | **regression** introduced by commit `30f52c3` | `compose_section.py:8184-8189` forced a `mixed`-anchored tabbed section's tablist to `justify-content: flex-start`, deriving tab justification from the section text anchor and overriding the centered scaffold default | tab-rail alignment is now its **OWN captured fact** (`tabAlignment` start/center/end), captured on the tab device INDEPENDENTLY of the section text anchor (`compose_section.py` tabs branch); the placement CSS (~L8184) emits a tablist override **only** from that measured fact and **never** from `resolved.anchor`. Absent fact ⇒ centered scaffold default (byte-identical). Helpers `_normalize_tab_alignment` / `_TAB_ALIGN_FLEX` added near `_ANCHOR_FLEX` | `#sec-7 .cs-tablist { justify-content: flex-start }` emitted → **removed**; rail centers (matches the real source) |
| D4 | proof-header archetype flattened (no pill, no rule, no top-right button) | captured-in-facts → dropped-in-render | the `_headRail` composite only stamped on treatment kind `dotted-rule-rail`; `headrail-two-col-header`'s treatment is the synonym `dotted-leader-rule` AND carried no `sanctioned` flag, so the `elif` never fired and the section fell to plain flow | (a) treatment-kind **synonym canonicalization** — `_canonical_treatment_kind` + `_TREATMENT_KIND_SYNONYMS` map `dotted-leader-rule`/`leader-rule`/`header-rail`/… → canonical `dotted-rule-rail`; (b) a **recipe-bound rail slot is sanctioned by its recipe binding** (keyed on the slot `recipeRef`, generic, never a brand/section name); (c) the captured device vocabulary (treatment kind + bound recipe/variant name, e.g. `outlined-pill`) is folded into the rail prose so a PROSE-authored recipe still lights up the pill kicker + dotted leader + outlined trailing register in `_headrail_html`. All in `compose_section.py` `stamp_pattern_devices` (~L690, ~L830) | `sec-6` bare `CASE STUDIES` eyebrow → **outlined `Case Studies` pill (left) + dotted leader rule + top-right outlined `See all case studies` button** |

**D3 regression explicitly reverted.** Commit `30f52c3`'s anchor→tablist coupling is
removed; tab alignment is now fact-driven with a centered default. The pin that locked
the regression (`test_hubspot_v3_defect_fixes.py::test_d6_tab_rail_follows_left_anchor`)
was corrected to `test_d6_tab_rail_is_fact_driven_not_anchor_coupled` and now guards the
fixed behavior (no per-section tablist override derived from the section anchor).

**Byte-identity (shared-fix scope).** `remote` and `woodwave-v2` replicas:
**byte-identical** (before/after, same renderer entrypoint). `hubspot-v2` replica: **−1
line only** — the same `#sec-7 .cs-tablist { justify-content: flex-start }` override is
removed by the D3 fix (same-brand, consistent: v2's tabbed testimonial had the identical
mis-coupled override; its committed HTML is stale and already renders centered, so no
regeneration was needed). D1 is a no-op on remote/woodwave heroes (list-authored or
typographic). D4 touches only patterns whose headrail slot binds a recipe (hubspot-v3
`sec-6`; `sec-4` stays **byte-identical** — its `sparkle-chip` prose carries no
pill/outline word so no decision changes). hubspot-v4 (same source/recipe shape) gets the
same D3/D4 improvement consistently.

**Files changed.** `brand_pipeline/compose_section.py` (D1 overlay coalesce + register
law; D3 fact-driven tab alignment + capture; D4 kind canonicalization + recipe-binding
sanction + prose enrichment), `brand_pipeline/slop_audit.mjs` (AS-59 split-group
advisory), `brand_pipeline/tests/test_hubspot_v3_defect_fixes.py` (D6 pin corrected to the
fixed behavior), `brand_pipeline/tests/test_headcta_tab_fixes.py` (NEW — 24 focused
regression tests for D1/D3/D4). Incidental: `run_pipeline.py` gained three defensive
`isinstance(entry, dict)` guards in the viewer-classification path so a pre-existing
malformed (bare-string) manifest screenshot entry no longer aborts `generate_viewer`
(unblocks the required viewer regen; behavior unchanged for well-formed entries).

**Artifacts.** hubspot-v3 replica + `ai-product-launch` `index.html` re-rendered (surgical
application of the three isolated diffs, preserving the rest of the stale-vs-current
pipeline output for a clean Studio review). Before/after `@1440` + `@375` section
screenshots in `runs/hubspot-v3/brand/fix-shots/`. `viewer.html` regenerated.

**Verification.** C1–C28 (`validate_brand_evidence`): v3 / v2 / remote / woodwave-v2 all
**0 errors**. Full suite (`./venv/bin/python -m pytest brand_pipeline/tests tests`):
**2093 passed**, only the **3 known pre-existing failures** (relume prompt top-k ×2,
runtime site-model defaults) — **zero new failures** (the D6 pin that initially failed was
the regression lock, now corrected). New/updated pins all green. Held for review — NOT
committed/pushed.

## Proof-section + bookend defect batch — 6 defects (2026-07-22)

User reviewed the Studio (`hubspot-v3`, replica + generated `ai-product-launch` side by
side) and reported 6 defects. **First established landed-vs-stale:** a deterministic
re-render of BOTH pages was BYTE-IDENTICAL to the on-disk HTML — so nothing was a stale
render; every defect was a GENUINE renderer/composition defect the prior generation-path
batch missed. All fixes are shared-renderer, fact-gated, brand-agnostic (no hardcoded
brand values, no section-specific token names).

| # | defect | page | root cause | fix (file:line) | before → after |
|---|--------|------|-----------|-----------------|----------------|
| 1 | secondary/"ghost" CTA missing | replica hero + closing CTA | a `dual-cta` actionGroup slot rendered only the lead CTA — the demo-section builder emitted ONE button and never expanded the group | `render_components_preview._demo_section_for_pattern` action branch (~L1810): when a slot declares `actionGroupRef` / an "action-group" role AND `doc.actionGroup.order` ≥ 2 with a resolvable secondary label, emit a companion `-secondary` button slot (filled primary + outlined secondary), consumed by both the overlay hero row and the flow CTA row | hero + CTA rendered 1 button → now render `Get a demo` + `Get started free` |
| 2 | closing CTA (and hero) wrong dark surface | generated `ai-product-launch` | the composition enum's coarse `inverse` intent mapped to the generic `surface/inverse` (#1f1f1f); the brand's measured dark bookend is `surfaceGrammar.bookend` = `surface/inverse-teal` (#002b28) | `compose_from_composition.adapt_brand_section` (~L2358): re-role a composed `surface/inverse` section to `surfaceGrammar.bookend` when the brand declares a distinct bookend role its `tokens.surfaces` carries; footer/closing-bookend chrome keeps `surfaceGrammar.footer` | hero + closing `#1f1f1f` → measured teal `#002b28`; footer bookend stays `#1f1f1f` (correct) |
| 3 | light section renders `#fff` | both | NOT reproduced — both pages already bind `--surface-surface-primary` (#fcfcfa cream) on every light-section canvas; the only literal `#fff` is the MEASURED white nav mega-panel (`responsive.nav.panelSurface`), which is correct | n/a (verified: sampled section bg = `rgb(252,252,250)` on both paths) | already cream on both paths |
| 4 | duplicate copy (eyebrow-above + subhead-below) | replica proof band | the `headrail`/section-headrail slot fell through the classifier to the paragraph `else`, binding the section BODY a second time; the authored `eyebrow: Case Studies` never bound | (a) `render_components_preview._demo_section_for_pattern` (~L1782, ~L1878): classify a `headrail`/`kicker` slot as `eyebrow`; (b) AS-84 single-voice dedup in `compose_section` generic-flow (~L4944): drop a text row whose visible copy repeats an earlier row in the same section | `"Scale your business…"` rendered twice → once, with `CASE STUDIES` eyebrow bound |
| 5 | G2 award badges tiny / cramped | replica badge band | the measured `mediaScale.item` box (96×132) was ignored: the `_logoScale` stamp required `of: container` + a `fraction`, and rejected the bare-number px values; the per-filename badge regex also failed (typo `bagde`, `best-relationships`) | `compose_section.stamp_pattern_devices` `_logoScale` stamp (~L861): capture a mark-row `mediaScale.item` box independent of a container fraction, coerce bare numbers to px, and take the row gap | badges 31×132→ measured **96×132** via `cs-logo-strip--itembox`, even row |
| 6 | tab rail centered vs left header | replica proof (tabs) | `.cs-tablist` hardcoded `justify-content: center`; the `mixed`/side anchor emitted no per-section tablist rule | `compose_section.layout_placement_css` (~L8175): for a section carrying the tab device, emit `#sec-N .cs-tablist { justify-content: <anchor flex> }` from the resolved anchor (centered → no override, byte-identical) | tabs centered → `flex-start` (left), consistent with the left header + badges |

**New anti-slop rule.** `AS-84 — One measured copy string bound to two roles in one
section` added to `brand_pipeline/spec/anti-ai-slop.md` (headrail/kicker classifies as a
microlabel; the flow composer keeps only the first occurrence of a visible text string).

**Byte-identity (shared-fix scope).** `remote` replica: **byte-identical**. `hubspot-v2`
replica: **+1 line only** — `#sec-7 .cs-tablist { justify-content: flex-start; }` — the
SAME defect-6 fix (v2 `sec-7` is `data-align="left"`, so its tab rail correctly left-aligns
to match its header). Defects 1 + 2 are no-ops on v2/remote (neither declares an
`actionGroup.order` ≥ 2 nor a `surfaceGrammar.bookend`). v3 replica hero/closing already
carried `surface/inverse-teal` via the brand-layout surfaceIntent, so the D2 remap is a
no-op there (guarded on `== surface/inverse`).

**Verification.** C1–C28 (`validate_brand_evidence`): v3/v2/remote all **PASS, 0 errors**.
Full suite: `brand_pipeline/tests` **1948 passed, 0 failed** + `tests/` 81 passed / **3
pre-existing failures** (relume prompt top-k ×2, runtime site-model defaults) — **zero new
failures**. New pins: `brand_pipeline/tests/test_hubspot_v3_defect_fixes.py` (9 tests, all
pass). Both pages re-rendered; `@1440` + `@375` screenshots captured (the residual 20px
`@375` overflow is the pre-existing `cs-edgecut` card track, out-of-scope). `viewer.html`
regenerated. Held for review — NOT committed/pushed.

## Type line-height unitless (AS-82 units-ethos) (2026-07-22)

**Concern.** The renderer emitted absolute px line-height for type roles (replica:
`:is(h2,.c-heading--h2){line-height:28px}` + h3 28px from `heading_responsive_css`; hero
shrink rung `line-height:55px`; primary button `line-height:32px`). Absolute px freezes the
box — a composed 40px h2 got a 28px line box (< its glyphs) → multi-line heading overlap
(the reason the generation path had to withhold the hero/heading register facts).

**Fix (source-code only; brand.yaml + facts unchanged).** UNITS-ETHOS: type line-height is
authored + rendered UNITLESS (a ratio) or `em`, never px.
`component_render.heading_responsive_css` now emits the brand's OWN authored
`tokens.type[tier].lineHeight` (h2 `1.1`, h3 `1.42`) for the fact-flagged tiers (the
`responsive.headings` fact gates WHICH tiers; never emits px). `hero_responsive_css` +
`hero_primary_button_css` convert their measured px pair to a unitless ratio
(`lineHeightPx/fontSizePx` = `1.1458` / `1.7778`) on the same rule as font-size — identical
box at the measured size, yet scales. New helpers `_px_val/_fmt_ratio/_lh_ratio/
_relative_lh/_type_lh_ratio`. New lint `css_fidelity.type_line_height_px_lint` fails on
`line-height:<n>px` for type-role selectors; documented `spec/anti-ai-slop.md` **AS-82** +
`brand-schema.md`.

**Applied.** Recomposed replica: 0 px line-heights on type roles (lint clean); h2 `1.1`,
h3 `1.42`, hero rung `1.1458`, button `1.7778`. `ai-product-launch` re-rendered from its
frozen `composition.json`: byte-identical (was already px-free).

**Verification.** Replica overall v3 `0.9241 → 0.9239` (Δ −0.0002 sub-perceptual noise);
v2 `0.9556` / remote `0.9509` HOLD (composed `index.html` byte-identical — no
headings/hero/button facts there). +8 tests; full suite 0 NEW failures (3 pre-existing
unrelated). No commit/push (held for review). Unblocks the queued hero-alignment /
register-fact merge (not done here — scope = line-height units only).

## Spacing / radius / color CSS-VARIABLE-FIRST token extraction (2026-07-21)

**Thesis (proven by the type-scale fix, now generalized).** A design system declares its
token SCALES in CSS custom properties; reading those tokens (var()/alias/calc/rem
resolution, @media variants, consuming-selector binding) reproduces the true scale from the
vars alone — never sample a scale from one measured instance. `tools/extract/type_scale.py`
established the pattern for type; this change extends it to SPACING, RADIUS and COLOR.

**Which families the source actually declares (grep of the saved CSS first):**
- **COLOR — fully CSS-var.** A 106-role semantic palette `--cl-color-*` aliasing
  `--light-theme-*` / `--dark-theme-*` down to hex (`container-01`=#fff,
  `background-01`=#fcfcfa, `text-01`=#1f1f1f, `border-03`=rgba(0,0,0,.11),
  `border-brand-01`/`button-primary-fill-idle`=#ff4800, …).
- **RADIUS — fully CSS-var.** `--cl-border-radius-{small=4,medium=8,container=16,round=9999,
  input=4}` + `--cl-border-width-{medium=1,heavy=2}`.
- **SPACING — partial CSS-var.** Section vertical rhythm (`--csol-section-padding-*` =
  0/16/24/40/64/96px), content padding, and control padding (`--cl-button-padding-*`,
  `--cl-card-*-padding`) ARE declared tokens; there is NO single named gap/step scale, so
  the generic step ladder is clustered corpus-wide (the improved computed-cluster fallback).

**New shared reader `tools/extract/token_families.py`** (reuses type_scale.py's machinery).
Emits `evidence/{spacing-scale,radius-scale,color-roles}.json`, each token provenance-tagged
`{source: css-var, sourceVariable, confirmedBy:[computed,…]}` (or `computed-cluster`):
- RADIUS: control/input/card/pill + small/medium via border-radius consumers, with STRICT
  component-name binding (a class token ENDING in the role keyword) so `.cl-card`→16px wins
  over `.global-nav-card-cta-text-link`→8px and nested card descendants never mis-bind.
- SPACING: section rhythm (named steps), control padding scale, named gutters, and the
  corpus-wide step ladder; `definedButUnused` flagged.
- COLOR: THEME-AWARE resolution (the default/light-scoped def wins over a later
  `[data-cl-theme=dark]`/`.-dark` redefinition), generic role classification by paint
  property + value (background/surface/surfaceInverse/text/textMuted/textOnInverse/
  border/borderStrong/borderBrand/accent/accentHover/accentText), `definedButUnused`, the
  MEASURED section band surfaces (captures the section-4 decorative band #fcded2 the
  semantic palette never names), and a measured-instance confirmation channel.
- Brand-agnostic cross-check: the reader also runs on **remote** (`--zora-*` tokens, a
  different palette, no section-rhythm tokens → step-ladder fallback) — it drives off "a
  custom property consumed as <property> by a role selector", never HubSpot var names.

**css_fidelity token-tier audits (new, analogous to the heading-tier audit).**
`spacing_tier_divergences` / `radius_tier_divergences` / `color_role_divergences` diff the
authored brand.yaml tokens against the css-var truth and surface drift by construction; a
hex-aware `_color_close` was added (the old `_color_tuple` parsed rgb() only, so hex-vs-hex
band comparisons collapsed to string equality). Severities are high/medium (never critical —
the css-diff critical==0 invariant holds). Divergences BEFORE→AFTER: spacing **2→0**,
radius **2→0**, color **1→0**.

**Re-authored v3 tokens from the css-var truth:**
- COLOR: `surface/accent-soft` **#f9c9c0 → #fcded2** (the section-4 measured breeze band; the
  authored token had drifted). Clears the css-diff section-4 background row (20→19 divergences).
- RADIUS: added `tokens.radius` {control 8, input 4, card 16, small 4, medium 8} from
  `--cl-border-radius-*`. The pill (9999px round) is recorded in radius-scale.json but NOT
  authored as a px fact (it is not in the consumed C19 radius ladder; badge dots use 50%).
- SPACING: `section-padding-light` **5rem (80px, off-scale) → 4rem (64px, the declared lg
  rhythm step)**; the normalizer now reports "section rhythm [64]".

**Verification.** C1–C28 **0 errors / 11 warnings** (C24 style-scale digest refreshed; the
initial `tokens.radius.pill=9999px` tripped C19 and was removed from the authored block). v3
replica **0.9236 → 0.924** (≥0.90; the section-padding correction did not regress — css-diff
compares the section OUTER band surface, not padding). hubspot-v2 / remote brand.yaml
**byte-identical** (SHA v2 `b25970e7…`, remote `1dae928f…`) — the reader is read-only and
was NOT run against their authored scales. Full suite **1940 passed**, **+24** new tests
(`brand_pipeline/tests/test_token_families.py`), **0 NEW failures** (the 3 remaining are the
pre-existing relume-recipe-catalog ×2 + runtime-defaults ×1, unrelated). Harness rebuilt
(7/7 chapters); token-chapter screenshots `harness/after-{color-roles,spacing-scale,
radius-scale}-fixed.png` show the corrected surface swatch (#fcded2) + the 5-tier radius scale.

**Systemic principle.** Extract EVERY token family from CSS custom properties first, bind by
consuming selector, confirm with measured instances + vision; cluster corpus-wide only where
no scale token is declared. Type / spacing / radius / color are now all css-var-first.

## Asset-kind ↔ slot-role eligibility (AS-80) — icon blown up as card lead media — 2026-07-21

Single-concern fix: two product-platform cards rendered an ICON stretched to fill the
card's lead media well where the other eight cards correctly showed a small spot icon
above the heading. Fixed systemically as an asset-kind↔slot-role eligibility rule plus
a hard audit, then applied to v3 by binding the source truth. Generic, brand-agnostic,
byte-stable for hubspot-v2 / remote.

- **Source truth.** The source DOM (`screenshots/hubspot-v3/hubspot.html`) renders EVERY
  product card — Marketing/Sales/Service/Content/Data/Revenue Hub, Smart CRM, Breeze,
  **Small Business Bundle**, **AEO (Beta)** — with the same small `global-nav-card-icon`
  glyph (`width="22" height="26"` etc.), never a photograph/screenshot. So the correct
  lead media for all of them is a small spot icon; there is no image to bind.
- **Root cause.** `009-small-business.svg` (22×26 orange sprocket) and `027-ai-20sparkle.svg`
  (16×17 gradient sparkle) were tagged `assetKind: photograph` in `assets-tagged.json` +
  `media-assets.yaml`, so `component_render.asset_render_mode` fell to the `cover` default
  and the card renderer drew them in a `16 / 10` media well (blown-up lead glyphs). The
  eight product-hub `spot-icon` cards beside them (`fit: mark`) rendered as small marks.
- **Systemic eligibility rule (`brand_pipeline/media_semantics.py`).** New declarative,
  brand-agnostic table + helpers: `ICON_FAMILY_KINDS` (spot-icon/ui-glyph/social-icon/logo
  marks), `IMAGE_FAMILY_KINDS`, `kind_family`, `is_icon_family`, `role_demands_image`,
  `eligible_render_mode`, `kind_map`/`_mediaAssetsKind`. IMAGE/media-well roles accept only
  image-family kinds; icon/mark-family kinds render at `mark` and are never blown up. See
  `spec/media-assets-schema.md` §6.1.
- **Render arm.** `asset_render_mode` coerces an EXPLICIT media-well fit (`cover`/`contain`)
  authored on an icon/mark asset to `mark`; the unset default `cover` is left untouched so
  held baselines whose icon/mark assets legitimately fall to the cover default (e.g. remote's
  `logo-fountain.svg` testimonial company mark) stay byte-identical.
- **Hard audit (AS-80).** `media_semantics.lint_media_bindings` emits a new
  `slot-role-eligibility` row (surfaced by `onbrand_check.check_media_bindings`): an
  icon-family asset bound into an image/hero-lead/full-bleed role FAILS, and an icon-family
  asset carrying an explicit media-well fit FAILS (a mis-scaled icon). Registered in
  `spec/anti-ai-slop.md` (AS-80) + the schema enforcement map.
- **Applied to v3.** Reclassified the two glyphs to their true `spot-icon` kind with
  `fit: mark` (+ measured intrinsic dims) in `media-assets.yaml` and `assets-tagged.json`.
  Regenerated the replica: both now render inside `cs-module-media--mark` (small icons), no
  `16 / 10` media well. Overall replica score **0.9155** (≥0.90); the 375px overflow is the
  pre-existing mobile responsiveness limitation, unchanged.
- **Verification.** C1-C28 **0 errors**; hubspot-v2 / remote / hubspot replica HTML
  **byte-identical** to committed HEAD (SHA-256 match); full suite **1898 passed** (+14 new
  eligibility/AS-80/v3-acceptance tests in `tests/test_asset_kind_role_eligibility.py`;
  updated `test_media_artifacts_brands` gate-row set), the only failures being 3 PRE-EXISTING
  unrelated ones (relume recipe-catalog ×2, runtime-defaults ×1) that also fail at HEAD.
- **Latent case reported, not changed.** A blanket render coercion (icon-family → mark even
  on the unset default) WOULD additionally rewrite remote's testimonial company mark
  (`logo-fountain.svg`, currently a `cover` well) — since remote byte-identity is HELD, the
  coercion is scoped to explicit fits only; the AS-80 gate row is the arm that would flag
  such a case without mutating the held render.
- **Files.** `brand_pipeline/media_semantics.py`, `brand_pipeline/component_render.py`
  (`asset_render_mode`), `brand_pipeline/onbrand_check.py`, `brand_pipeline/spec/anti-ai-slop.md`,
  `brand_pipeline/spec/media-assets-schema.md`, `runs/hubspot-v3/brand/media-assets.yaml`,
  `runs/hubspot-v3/brand/assets-tagged.json`, `brand_pipeline/tests/test_asset_kind_role_eligibility.py`,
  `brand_pipeline/tests/test_media_artifacts_brands.py`. Before/after screenshots under
  `runs/hubspot-v3/brand/compose/replica/eligibility-fix/`.

## Footer socials + wordmark + column-alignment + bottom-bar spacing — 2026-07-20

Follow-up fixing the footer residual (blank center) plus continuation-column baseline
and cramped copyright↔legal spacing. All generic, fact-gated, byte-stable for v2/remote.

- **Social glyphs now paint.** Root cause: the footer social icons are shared-sprite
  `<use href="#cl-icon-…">` references; the `<symbol>` artwork lives in the hidden inline
  sprite map (`<svg class="cl-svg-map">`) at the bottom of `hubspot.html`. The extractor's
  `outer_or` now **resolves a `<use>` ref into a standalone single-ink SVG** (inlines the
  referenced symbol's viewBox + children, `fill=currentColor`). All **7** networks
  (Facebook, Instagram, YouTube, X/Twitter, LinkedIn, Reddit, TikTok) materialize as real
  `assets/social-*.svg` and stamp `_inlineSvg`; glyph ink bound to the measured muted footer
  link color. Sprite source: **inline symbol map in the saved DOM** (present — not a capture
  gap).
- **Footer wordmark now paints.** The saved DOM inlines the footer logo as a
  `data:image/svg+xml;base64` (cream wordmark); the bridge only stored a `srcContract` ref so
  `prepare_chrome_glyphs` couldn't resolve it. The author now decodes it to
  `assets/footer-logo.svg` and sets `footer.logo.src`, so the centered-stack wordmark stamps
  `_dataUri` (+ intrinsic aspect 3.53) and renders.
- **Continuation-column baseline.** A headingless continuation column (e.g. "Popular
  Features"'s overflow) now renders an aria-hidden heading-row spacer (`.c-foot-col-head--
  spacer`) so its first link shares the headed columns' link baseline instead of floating to
  y=0. Fact-gated: only when sibling columns are headed; byte-stable for all-headless footers.
- **Bottom-bar spacing.** `bottomBar.gap` was 0 (the JS-off static snapshot collapses the
  stack), so the centered stack rendered copyright↔legal touching. Bound the row gap to the
  captured copyright `margin-top` (16px) so the stack is not cramped.

Results: footer band **0.9549 → 0.950** with the center now fully painted (socials + wordmark
+ aligned columns + comfortable spacing) — the earlier 0.968 had a blank center. Overall
**0.901** (≥ 0.90). C1-C28 0 errors; harness digest-fresh (7/7); baselines held (v2 **0.957**,
remote **0.951**); full suite **1716 passed** (+15 new), 0 failures. Residual: footer renders
~794px vs 656px source (the now-correct social row + wordmark + comfortable stack add height);
faint wordmark tint. Evidence: `compose/replica/diff/footer.png`.

## DOM-faithful nav + footer chrome pass — 2026-07-20

**Problem.** The v3 nav was flattened to a single row (no two-tier, no mega-nav, wrong
logo, loose spacing) and the footer was ~50% (missing measured structure). Root cause:
the lane never ran the generic chrome extractor (no `assets/source-chrome.v2.json`) — the
staged author had emitted a degraded flat nav.

**Generic parser fixed** (`src/screenshot_to_template/browser_chrome_extractor.py` — brand
-agnostic, parses the SAVED DOM offline over a localhost static server; no recapture):
- **Logo-container swallow**: `[class*=logo]` matched the layout utility class
  `-burger-logo-slide-left` on the full-width `global-nav-main-inner`; with no ancestor
  `<a>` that bar-wide `<div>` became the logo anchor, so `logoAnchor.contains(el)` skipped
  EVERY primary tab + CTA (nav collapsed to the utility bar). Guard: a logo candidate with
  no ancestor `<a>` must not hold more than one link/button.
- **Tabbed-mega area**: a `role=tablist` layout wrapper (`global-nav-sidebar`) matched the
  `sidebar` aside token; its panels are now MAIN, and the rail is captured separately.
- **Card-title headings**: a heading that wraps its own link is a card title, not a column
  heading (was splitting each card into a one-item column).
- **Descriptions**: captured by climbing to the card wrapper's sibling `<p>` (not only
  inside the anchor) — every mega item now carries its title + description line.
- **`sidebarTabs`**: the left category rail captured structurally from the hidden DOM.
- **Utility anatomy**: every utility control annotated (kind/role/icon/chevron + dropdown
  items via aria-controls); the locale switcher + About menu now carry their items.

**Authored** into `brand.yaml` via `tools/_v3_chrome_author.py` (in-place navbar/footer
splice — they sit mid-file in v3, unlike v2's trailing blocks — reusing
`bridge_chrome_to_brand` merge + asset materialization). Added the explicit
`navbar.utilityTier` (left/right regions; tiers sum to the measured 128px bar), marked the
utility dropdowns `dropdownNotObserved` (items captured, open-state panel paint absent from
a static snapshot) and the trigger caret `chevronNotObserved` (shared-sprite `<use>`, no
standalone artwork). Footer: dropped the 2-wrapper `wrapperSizes` (rendered flat columns),
split the 18-link "Popular Features" column across two tracks, clamped the mis-measured
22px heading to the muted 14px token, and declared the source's `bottomBar.anatomy:
centered-stack`.

**Renderer support** (generic, fact-gated, byte-stable):
- `_mega_panel_fragment` draws a left category rail from `menu.sidebarTabs` (+ `.cs-mega-rail`
  CSS); rail-less menus emit byte-identical markup.
- `_copy_logo_file` decodes a `data:image/svg+xml;base64,…` logo to the local asset — the
  real captured HubSpot wordmark renders instead of the text fallback.

**Results** (measured replica, 1440×900):
- nav band **0.9382 → 0.979** (height now 128px == source; two-tier + real logo + regions).
- footer band **0.9549 → 0.968** (columns/headings/legal/divider/centered-stack match).
- overall **0.901 → 0.903** (≥ 0.90). C1–C28: **0 errors**, 11 warnings. Harness digest-fresh
  (7/7 chapters). Baselines held: hubspot-v2 **0.957**, remote **0.951**. Full suite **1711
  passed** (+10 new `test_chrome_dom_fidelity.py`), 0 failures.

**Residual (notObserved / capture limits):** footer social-glyph row + centered wordmark do
not paint — social icons are shared-sprite `<use>` references (no standalone artwork) and the
footer wordmark data-URI did not stamp; hrefs/structure captured. Nav collapsed bar omits the
High-Contrast a11y toggle and icon-only search (filtered as non-destinations). Mega open-state
paint (panel background/rect) is a static disclosure — geometry notObserved by design.
Evidence: `compose/replica/diff/page-nav.png`, `diff/footer.png`,
`harness/nav-collapsed-after.png`, `harness/nav-mega-open-after.png`.

## Measured per-component geometry re-author — 2026-07-20 (G4 cleared 0.90)

- Root cause confirmed against the evidence: the staged author named every slot/role
  and the join keys were sound, but patterns shipped WITHOUT the v2-bar measured
  geometry (band padding, box-to-box rhythm, per-card register/grid-equalize,
  container-relative media scale, and the hero's measured band aspect). The renderer
  already CONSUMES all of these (`compose_section.stamp_pattern_devices`), so the gap
  was authored data, not renderer capability — except one genuine renderer gap below.
- Added `brand_pipeline/measured_geometry.py`: a deterministic, evidence-driven
  enricher that fills absent measured geometry on every extracted pattern from the
  lane's OWN grounding YAMLs + `section-rects.json` (generic register/rhythm/aspect
  rules; fill-absent-only + provenance-gated, so the hand-authored v2/remote baselines
  are byte-identical). Wired into the staged-author deterministic projection so
  extraction is now measured-accurate BY ITSELF and reproducible.
- Fact-gated renderer support (the one genuine capability gap): `compose_from_composition`
  `_aspect_css` now honors a MEASURED `W / H` media aspect ratio in addition to the five
  coarse enum classes. The full-bleed hero canvas was locked to `wide` (21/9 ≈ 617px);
  it now renders at the measured band aspect (section 1440×772). Enum classes are
  byte-identical, so v2/remote are unaffected.
- Calibrated which facts to APPLY vs WITHHOLD by the replica gate: the shipped set
  (`FIDELITY_FIELDS` = bandPadding, bandRhythm, columnGap, mediaScale, heroMediaAspect)
  improves or holds every band. `headingRegister` / `cardRegister` / `cardActionGap` /
  `gridEqualize` are extractable (proven by test) but WITHHELD from the shipped library
  because the composer over-responds (oversized card headings, stretch-taller grids) —
  a named residual RENDERER gap, not a data gap.
- Replica gate **0.8955 → 0.9010** (>= 0.90). Per-band before → after:
  nav .9382→.9382, hero .8097→**.8371** (623→739px vs 772), logo .9562→**.9768**,
  platform .8749→.8781, product grid .9043→.9042, agents .8867→.8868,
  integrations .9207→.9147, case header .8999→**.9283**, testimonial .8649→**.8699**,
  badges .9664→.9648, CTA .9347→**.9396**, footer .9549→.9549.
- Nav + footer verified at the v2 parity bar: nav renders the utility row
  (Customer Support / Contact Sales / Log in), primary links with mega-nav triggers
  (panels `notObserved`, structure preserved), language switcher, About menu, and the
  dual CTA action group with painted `visibleLabel` provenance; footer renders all five
  measured columns with muted headings, the seven-glyph social row, the legal/copyright
  row, and the divider separator. Nav .9382 / footer .9549.
- Gates: C1–C28 **0 errors** / 13 advisory warnings; G3 harness digest-current
  (7/7 chapters, 36 primitives, 32 blocks, 10/10 patterns) and rebuilt fresh; G4 passes.
  Full canonical flow now reports **completed / generation ALLOWED** (was blocked).
- Baseline protection (shared `_aspect_css` touched): hubspot-v2 re-scored **0.957**
  (>= 0.9567) and remote **0.951** (>= 0.9509) — both held. Full suite **1686 passed**
  (1676 baseline + 10 new measured-geometry / aspect / chrome tests), 8 existing Pillow
  warnings, 4 subtests, zero regressions.
- Pages: G4 clearing 0.90 UNBLOCKS generation, but the three pages
  (`ai-product-launch`, `event-registration`, `research-report`) were NOT generated in
  this session — the generator is model-driven (Anthropic `claude-opus-4-8`), the API is
  outside the sandbox allowlist and has a documented multi-thousand-second hang history
  in this environment, and the three named briefs are not materialized in the repo.
  Honest stop, generation-ready.
- Residuals (the bands still below the v2 bar are RENDERER, not data): the platform
  split (sec-2, 486 vs 742px, width 0.66) does not render its subhead + slide stack +
  carousel controls; the product-card grid (sec-3, 2298 vs 1600px) over-heights per
  card; the withheld card-register/grid-equalize facts await composer calibration.

## Final focused G4 pass — 2026-07-20

- Ranked the pre-repair weighted deficit: agent carousel 0.02545, hero 0.02103,
  product grid 0.01887, testimonial 0.01381, and platform carousel 0.01329.
- Confirmed section-04's current projection contradicted fresh evidence: the
  measured soft-accent band, split headrail, and edge-cut fixed-card track were
  routed as a primary-canvas contained grid. Added the generic
  `surface/accent-soft` role from section-04's measured `#f9c9c0` endpoint and
  fact-gated the existing headrail/edge-cut renderer capability.
- Fixed generic self-hosted-font stack resolution. The four fresh v3 WOFF2 files
  captured from source-authorized URLs now emit seven `@font-face` rules and are
  copied into the replica; the diagnostic no longer falsely flags a full CSS
  family stack as missing.
- One bounded repair plus verification improved G4 **0.8891 → 0.8955**. Agent
  carousel improved **0.8208 → 0.8867**, height **1237 → 894px** vs source
  992px, and width fidelity **0.7725 → 0.9551**. Product grid regressed
  **0.9176 → 0.9043** because hosted font metrics increased its height
  **2072 → 2297px**; all other principal residuals held.
- G4 remains below 0.90, so generation stayed refused. No
  `ai-product-launch`, `event-registration`, or `research-report` page was
  generated.
- C1-C28: 0 errors / 13 advisory warnings. G3 rebuilt digest-current and passed
  with Studio HTTP 200. Remote re-scored **0.9509** and HubSpot v2 **0.9567**.
  Full suite: **1676 passed**, 8 existing warnings, zero losses.

## Log

- 2026-07-17T20:38:09Z — allocated `runs/hubspot-v3/brand/` and
  `screenshots/hubspot-v3/`; initialized an in-progress manifest before capture.
  Read HubSpot v2 manifest and changelog only as the quality-bar and artifact-shape
  reference. No v2 authored brand, layout, copy, or media artifacts were copied.
- 2026-07-17T20:38:35Z–20:39:38Z — fresh live capture completed from
  `https://www.hubspot.com/` with no redirect and no capture failures. Canonical
  1440×900 Save-Page-As capture: 693,870-character HTML, 25 stylesheets, 55
  rendered images, 1440×6986 full-page screenshot. Additional fresh full-page
  tiers: 1920×1080 (7166px document), 960×900 (7426px), 375×812 (9824px).
- 2026-07-17T20:39:58Z–20:44:02Z — ran the required single-intent canonical
  command: `run_pipeline_flow.py --brand hubspot-v3 --capture
  screenshots/hubspot-v3 --replica-bar 0.90 --max-iterations 3`. Fresh evidence
  extraction succeeded through curate: 61 module sections, 1,683 CSS rules from
  41 sheets, 59 transitions, 48 action families, 10 measured content sections,
  4 responsive tiers, 11 coherent crops, 11/11 vision grounding calls successful,
  and 66 curated assets (30 with measured media facts).
- 2026-07-17T20:44:02Z — **PIPELINE BLOCKER; stopped as instructed.** The canonical
  fresh-flow leg invokes `run_brand_extraction.py` with every stage. That runner's
  `author` stage only prints that `brand.yaml`, `layout-library.yaml`,
  `section-copy.yaml`, `assets-tagged.json`, `brand.md`, and `voice.md` are
  missing; it cannot author them. It nevertheless immediately runs nested
  validation, which fails C1 on missing `brand.yaml`. `_run_extraction` then
  raises an uncaught `RuntimeError`, before the orchestrator writes
  `flow-report.json` or evaluates G1. This makes the advertised completely fresh
  single-intent G1→G5 flow impossible without manually stepping outside the
  canonical command. Per experiment rules, no shared source was patched and no
  manual gate bypass was attempted. Harness, replica, and creative generation
  were not run.
- 2026-07-17T20:45Z–20:51Z — implemented and verified the missing executable
  author stage in shared source. It builds a current-lane-only evidence/spec
  bundle, invokes the existing Anthropic provider in transactional artifact
  groups, records returned usage without estimating it, derives projections,
  runs bounded C1-C28 repairs, skips valid existing output unless forced, and
  blocks before validation when provider/output completeness fails. The
  orchestrator now resumes an evidence-complete lane at `author,validate` and
  converts extraction exceptions into a persisted blocked G1 report. Focused
  author/flow tests: 34 passed. Full brand-pipeline suite: 1,611 passed, 8
  existing Pillow deprecation warnings, zero losses.
- 2026-07-17T20:51Z–21:26Z — first live resume initiated one logical
  `claude-opus-4-8` author call. It returned neither a completed response nor
  usage telemetry and was operator-terminated after 2,108.372s; no artifact
  group had been installed. This exposed that the provider's HTTP stream timeout
  was not a true whole-call bound.
- 2026-07-17T21:27Z–21:47:59Z — added a real wall-clock author bound and resumed
  the same lane again without rerunning capture/mine/ground/curate. One logical
  `claude-opus-4-8` call again returned no completed response or token usage
  before the 300s bound. The SDK's inherited retry policy prolonged teardown to
  1,246.539s, so author-specific provider retries are now disabled; future calls
  respect the author layer's own bounded repair/timeout policy. The canonical
  flow exited blocked at G1 and wrote `author-report.json`,
  `flow-report.json`, and `flow-report.md`; no authored candidates were
  installed and C1-C28 was not invoked.
- Per the experiment stop rule, no manual HubSpot v3 authoring or v2 data copy
  was attempted. Harness, Studio URL checks, replica scoring, page generation,
  screenshots, and visual review remain prohibited/not run.
- 2026-07-17T23:xxZ — replaced the oversized shared author bundle with a
  checkpointed DAG: foundation → copy-chrome → patterns-recipes → media →
  deterministic projections. HubSpot v3 measured prompt sizes before calls:
  150,184 / 95,728 / 79,220 / 78,063 bytes respectively; no raw CSS rules,
  screenshots, base64, or full HTML are inlined. Each provider call now runs in
  a disposable child process with a ≤240s hard timeout and zero retries.
  C1-C28 repair errors route only to their owning stage. Added stage DAG,
  scoping/caps, hard-timeout, response-shape, checkpoint, telemetry, and repair
  routing tests. Focused tests pass; the first full run reached 1,614 passed with
  two unrelated Node Playwright-browser misses, then the missing official browser
  was installed and those focused gates passed.
- 2026-07-17T23:08:40Z–23:28:53Z — resumed only the existing evidence lane with
  `claude-opus-4-8`; no capture/evidence stages reran. Foundation completed in
  123.409s (150,184 bytes; 68,130 input / 12,328 output tokens), copy-chrome in
  95.501s (120,360 bytes; 53,194 / 9,831), and patterns-recipes in 90.328s
  (109,202 bytes; 47,766 / 8,336). The original combined media response reached
  20,000 output tokens without closing JSON; it was split and changed to a
  deterministic measured-draft projection. The bounded compact-guidance attempt
  still reached its 10,000-output-token cap after 101.604s (97,196 bytes; 42,906
  input tokens). Per the explicit stop rule, live authoring stopped at `media`;
  no hand-authored files, model switch, C1-C28, harness, replica, or creative page
  generation followed. The source implementation now constrains future media
  guidance to tag-level rules (never per-asset repetition), but that post-blocker
  refinement was not called live.
- Final verification after the flow's stage-specific failure telemetry was added:
  1,617 tests passed with 8 existing Pillow deprecation warnings and zero
  failures; lints and `git diff --check` were clean.
- 2026-07-18T23:02Z–23:05Z — final recovery compacted the live media request
  from 97,196 to 14,776/14,945 bytes. The request contains a seven-tag census,
  twelve representative records, and photography grounding; it contains neither
  the 66-record draft nor the asset manifest. The complete measured draft remains
  on disk for deterministic projection. Output is capped dynamically at 3,450
  tokens (4,000 hard stage cap), with exact tag-vocabulary and nested fingerprint
  validation.
- Recovery media call 1 completed in 27.419s on `claude-opus-4-8` (6,608 input /
  2,039 output tokens). It exposed an under-specified fingerprint schema and a
  deterministic projection assumption about `brand:` shape. The one permitted
  systemic repair tightened schema/enums, fixed the media projection's brand-name
  read, made `--force-author-stage` effective for complete output sets, and removed
  the redundant model-authored media-tags stage in favor of deterministic
  `assets-tagged.json`.
- Recovery media call 2 completed in 15.736s (14,945 bytes; 6,689 input / 1,208
  output tokens) and returned valid `media-guidance.v1` with all seven tag rules.
  The deterministic projection prelude installed `media-assets.yaml` (35,633
  bytes) and `assets-tagged.json` (8,660 bytes) from the measured draft.
  Projection then blocked at `render_brand_md.render`: the checkpointed foundation
  authored `brand: hubspot-v3` as a scalar, while the renderer requires
  `brand: {name: ...}` and raised `AttributeError: 'str' object has no attribute
  'get'`. Per the second-retry stop policy, no third media call, remaining derived
  projection install, C1-C28 repair, harness, replica, or page generation followed.
- Verification: focused author/flow tests 43 passed; metadata robustness tests 55
  passed; full suite 1,620 passed with 8 existing Pillow deprecation warnings;
  `git diff --check` and edited-file lints passed. Completed foundation,
  copy-chrome, and patterns-recipes stages were skipped on both recovery calls.
- 2026-07-18T23:12Z–23:18Z — repaired the deterministic projection boundary.
  `brand` is normatively an identity mapping per `brand-schema.md`; staged output
  now normalizes only a non-empty legacy scalar before install/projection,
  preserves canonical mappings, rejects malformed types, instructs future
  foundation calls to emit the mapping, and C1 verifies `brand.name`. The renderer
  can project the checkpoint's legacy list-shaped `blocks` without converting it
  into canonical data; stage validation now requires future `blocks` output to be
  a contract-keyed mapping, so C2 remains fail-loud.
- Deterministic projections completed with no author call. Initial C1-C28 produced
  24 errors / 6 warnings and C1 passed. A canonical bounded resume then re-authored
  only the invalid foundation stage (150,317 bytes; 122.010s; 68,178 input /
  11,869 output tokens). Copy-chrome, patterns-recipes, and media were checkpoint-
  skipped; capture, mining, measurement, grounding, and curation did not rerun.
- The new deterministic projections completed in 0.356s. Residual C1-C28 is
  23 errors / 6 warnings. Before owner repair call 1, the foundation repair prompt
  measured 187,910 bytes, exceeding its 180,000-byte hard cap. No repair model
  call started. Per stop policy the lane remains blocked; harness, replica, and
  all three creative pages were not run.
- Focused compatibility/contract tests: 135 passed plus 4 subtests. Full
  `brand_pipeline/tests`: 1,635 passed plus 4 subtests, with 8 existing Pillow
  deprecation warnings and zero failures. Updated
  `manifest.json`, both experiment reports, `validation-report-full.json`, and
  author/checkpoint telemetry. No recapture, v2 copy, manual brand authoring,
  viewer change, commit, or push.
- 2026-07-18T23:25Z–23:35Z — replaced whole-stage repair re-emission with
  owner/schema-path groups, failing-fragment extraction, exact spec-section
  selection, affected-field evidence, immutable dependency summaries, an 80,000
  byte repair cap with splitting, bounded merge/JSON patches, structural patch
  validation, rollback, and per-group checkpoint telemetry. Added tests for
  grouping, fragments, spec selection, cap splitting, unrelated-evidence
  exclusion, atomicity, fenced JSON, malformed layout rejection, and resume.
- Live compact payloads were 17,704; 17,902; 21,414; 5,658; 7,256; 19,939;
  22,147; and 22,116 bytes. All were below 80,000 bytes. Eight repair calls
  started on `claude-opus-4-8`; seven returned usage totaling 50,179 input /
  25,612 output tokens, while the first truncated response returned no persisted
  usage. Completed patches narrowed block/button errors and fixed
  `section-copy.yaml`; deterministic canonical projections unwrapped
  `footer.social.icons` to `footer.social[]` and projected the already-authored
  `motion.value` into `tokens.motion`, with provenance in the checkpoint.
- The first call returned truncated JSON. A later `/layouts` patch encoded a
  list marker as a mapping; it was removed, and structural validation plus
  automatic rollback now prevent recurrence. The final button response was
  fenced JSON; it was rolled back by the then-strict parser. Fenced JSON support
  is now tested, but the two-cycle live repair budget was exhausted and no
  additional model call was made.
- Final diagnostic validation is 22 errors / 7 warnings. Harness, Studio,
  replica, and three-page generation remain fail-closed and were not run. No
  capture, mining, grounding, curation, valid author stage, or media stage reran;
  no v2 copy, viewer change, commit, or push occurred.
- Verification: focused compact-repair suite 28 passed plus 4 subtests; full
  `brand_pipeline/tests` 1,641 passed plus 4 subtests with 8 existing Pillow
  deprecation warnings and zero losses. Refreshed the fail-closed G2 flow report.
- 2026-07-19T00:xxZ — replaced schema-heavy residual repair with a generic
  contract-complete projection boundary. Universal primitive/block/scaffold keys
  now come from shared contracts; absent source components become honest designed
  `notObserved` entries excluded from replica. Existing staged wrappers, pattern
  layout instances, contract refs, action-group/signature envelopes, and chrome
  measurement types are canonicalized deterministically.
- Fresh evidence projectors now fill button height/padding from exact computed-style
  family samples, selector-specific tab/carousel timing from `motion-audit.json`,
  row rhythm from the CSS custom-property declaration, and semantic renderer roles
  only as aliases of existing measured tokens. Unobservable card-grid equalization
  is explicit rather than guessed. Added the exhaustive 22-error classification in
  `contract-completeness-audit.md`. No semantic/model repair call was made.
- C1-C28 now passes with 0 errors and 25 advisory warnings. Focused projection/author
  tests pass (30 tests + 4 subtests). Harness regeneration produced 7/7 spec chapters,
  36 primitives, 35 blocks, 11/11 composed patterns, and no unknown-origin `?`
  placeholders; Studio served the spec book with HTTP 200. Captured the served page
  to `harness/studio-spec-book.png`.
- The measured-only replica ran once and scored 0.6897 versus the 0.90 gate. The
  bounded loop stopped because no evidence repair hook was available; repeating an
  identical render was intentionally not counted as an iteration. G4 remains
  `needs_iteration`, so the three requested creative pages were not generated.
- Full regression suite passed outside the browser sandbox using the installed arm64
  Playwright cache: 1,643 passed + 4 subtests, 8 existing Pillow deprecation warnings,
  zero regressions. (Two sandboxed attempts could not launch the matching browser;
  no test assertion failure remained once run in the supported browser environment.)

## G4 measured replica repair — 2026-07-20

- Diagnosed the 0.6897 replica as a projection/renderer-routing failure rather
  than a weak visual approximation. All projected `brand.yaml layouts[]` had
  `slots: []`; `layout-library.yaml` used semantic `role` values where the
  renderer requires canonical slot `name`s and left measured assets unbound.
  This produced a missing navbar, blank 160px fallback bands, duplicated footer
  treatment, and no hero/card/logo/testimonial anatomy.
- Added `repair_replica_data.py`, a reproducible measured-lane correction using
  only HubSpot v3's fresh section rects, grounding descriptions, section copy,
  computed 68px CTA rect, and curated v3 asset inventory. It canonicalizes slot
  names, binds the observed assets, restores semantic use-case/archetype routing,
  records the section-04 accent-wash surface, fixes two copy-ID aliases, and
  marks icon/logo/badge assets with their observed `mark` fit.
- Added brand-agnostic, fact-gated renderer repairs: replicas force the existing
  composed-page chrome path; footer-crop patterns are excluded from ordinary
  section order so footer chrome is rendered once; measured footer columns
  outrank a compact footer-link type token; measured navbar height can set the
  chrome box. Added focused regression tests for footer exclusion, footer grammar
  precedence, and retained designed-component replica exclusion.
- Bounded score trajectory (new repair iterations):
  - iteration 1: **0.7943**. Bands: nav .8738, hero .5450, logo .9312,
    platform .8718, product grid .8275, agents .8569, integrations .9009,
    case header .9171, testimonial .8392, badges .8078, closing CTA .3137,
    footer .8477.
  - iteration 2: **0.8701**. Bands: nav .8738, hero .7988, logo .9312,
    platform .9243, product grid .8445, agents .8477, integrations .9009,
    case header .9167, testimonial .8070, badges .9321, closing CTA .9179,
    footer .9553.
  - iteration 3: **0.8591**. Bands: nav .9574, hero .7611, logo .9312,
    platform .9243, product grid .8078, agents .8477, integrations .9009,
    case header .9167, testimonial .8070, badges .9321, closing CTA .9179,
    footer .9553.
- Final G4 remains **blocked**: 0.8591 < 0.90 after the three permitted
  evidence-backed repairs. Exact blockers are product-grid media semantics
  (spot icons still expand as full card media, making the band 4,243px vs
  1,600px), incomplete active testimonial/stat anatomy (408px vs 714px),
  hero photo/scrim/stack treatment mismatch (.7611), and static edge-cut agent
  carousel capability (.8477). No source bands were deleted and designed
  components remain excluded.
- Final source-vs-replica band pairs and contact strip are in
  `compose/replica/diff/` (`strip.png` plus nav/sec-0..9/footer pairs). The
  scorer overwrites its output directory, so exact iteration-1/2 strips were not
  retained; their scores and diagnostics above were recorded before each rerun.
- C1-C28 remains 0 errors (26 advisory warnings; one additional stale
  style-scale digest warning after measured brand-data correction). Focused
  tests: 46 passed. HubSpot v2 re-rendered at **0.957** and Remote at **0.951**,
  both holding/improving their 0.957/0.950 baselines.
- Per stop policy, G5 was not entered. `ai-product-launch`,
  `event-registration`, and `research-report` were not generated; no page gates,
  screenshots, visual URLs, viewer regeneration, commit, or push occurred.

## Harness forensic correction and safe repair — 2026-07-20

- Corrected the earlier conflation: the user screenshots were stale
  `components-preview/layouts/*.html` demos stamped from brand SHA `805e…`,
  not the then-current measured replica. The real replica already carried all
  ten source sections, measured nav/footer, and source copy at 0.8591.
- Archived corrupt author/projection/harness outputs under
  `_pre-repair-corrupt-author/`; evidence, grounding, crops, and curated assets
  were not moved or modified.
- Re-authored staged factual outputs from the existing fresh evidence. Public
  identity is `HubSpot`, with a rich evidence-grounded snapshot. C1-C28 now
  passes with 0 errors and 11 advisory warnings.
- Closed the exact stale-demo chain:
  - C4 now hard-fails zero content-slot bypass, invalid/missing slot types,
    layout/layoutCopy join drift, missing consumed copy roles, unsupported
    `sourceCopy`, and internal lane ids in renderable public content.
  - staged-author pre-install validation rejects the same namespace/type joins.
  - projection rekeys copy by canonical layout id, removes `sourceCopy`,
    preserves slots/assets/block mappings, and resolves measured button/control
    facts without replacing them with generic defaults.
  - composite projection digests cover brand/copy/library/chrome/media/assets
    and stamp main harness, every layout demo, catalog, and replica.
  - G3 regenerates stale projections and rejects any digest mismatch.
- Added AS-78 Circle Integrity and AS-79 Control-Family Coherence to
  `anti-ai-slop.md` and `slop_audit.mjs`. The repaired harness passes the full
  slop audit at 1440 and 1180: round controls are 48×48 icon-only, focus rings
  stay bounded, and designed toggles use capsule tracks/circular knobs with
  brand surfaces/motion/focus.
- Regenerated the current v3 harness and catalog. Quality gate:
  7/7 chapters, 36 primitives, 32 blocks, 10/10 extracted patterns, current
  composite digest, Studio HTTP 200. Targeted screenshots:
  `harness/after-description.png`, `after-round-focus.png`,
  `after-toggle.png`, `after-tier2-*.png`, and direct `after-*-direct.png`
  pattern proofs. URL:
  `http://127.0.0.1:1500/runs/hubspot-v3/brand/components-preview/index.html`.
- Downloaded the four font files referenced by the saved v3 source HTML and
  registered self-hosted HubSpot Sans/Serif/Page Header Human faces. No v2 font
  or authored data was copied.
- Real post-harness replica trajectory: preserved baseline 0.8591; new renders
  0.8542 → 0.8542 → **0.8633**. Final bands: nav .9159, hero .8099, logo
  .9562, platform .8749, product grid .8086, agents .8209, integrations .9207,
  case headrail .8999, testimonial .8649, badges .9656, CTA .9243, footer
  .9549. Remaining blockers are carousel statics, product-grid 4,242px vs
  1,600px anatomy, and width collapse. G5/pages remain prohibited.
- Regression safety: HubSpot v2 holds 0.957. Remote re-render currently records
  0.936 versus its requested 0.951 baseline; this unresolved safety delta is
  explicitly blocking any success claim. No commit, push, viewer change, or
  creative page generation occurred.
- Final verification: changed-area suite 179 passed + 4 subtests; full
  `brand_pipeline/tests` 1,655 passed + 4 subtests with 8 existing Pillow
  deprecation warnings; edited-file lints clean. C1-C28 0 errors / 11 warnings;
  digest-current G3 and AS-78/79 pass.

## Remote regression closure — 2026-07-20

- Causal bisect isolated the safety loss to the harness-side Tier-3 asset
  classifier, not scoped media merge, chrome/footer precedence, replica routing,
  digest stamping, or the new component-fit/wireframe paths.
- The classifier's new `mark`/`badge` substring branch misread Remote's
  testimonial anatomy phrase `company marks` as an explicit logo collection,
  replacing three authored quote cards with seven media-only modules.
- Narrowed the behavior generically: complete authored repeated records win over
  incidental anatomy prose; projected canonical collection names such as this
  lane's `logo-row`, `logo-collage`, and `badge-row` retain the new routing.
  A focused regression arm verifies this lane's hydrated canonical `logo-row`
  still emits the `logo` contract.
- Remote restored exactly to **0.9509** (`sec-7` **0.8283 → 0.9577**);
  HubSpot v2 held **0.9567**. This lane is semantically unaffected, so its last
  measured replica remains **0.8633**, below the unchanged 0.90 gate; generation
  remains refused. C4 joins/types/provenance, digest invalidation, G3 freshness,
  AS-78, AS-79, and harness quality checks are unchanged. Focused tests:
  **27 passed**; full suite: **1,657 passed + 4 subtests**, 8 existing warnings,
  zero losses.

## CTA visible-label evidence repair — 2026-07-20

- Proven root cause: computed action evidence used raw element `textContent`.
  The measured 113.375px / 141.781px nav controls therefore carried screen-reader
  suffixes as if they were painted labels, despite those strings being unable to
  fit at 14px with 16px horizontal padding.
- Re-ran measurement against the existing saved v3 HTML (no recapture). Evidence
  now separates painted `visibleLabel` from `accessibleName`, with browser text
  width and host geometry facts. It records `Get a demo` at an estimated
  109.364px inside 113.375px and `Get started free` at 137.77px inside
  141.781px; the longer semantic names are explicitly flagged as non-layout text.
- Deterministic projection repaired button families and `brand-chrome.yaml`.
  Shared renderers now paint the short labels and preserve the full descriptions
  only in `aria-label`.
- Regenerated the v3 harness and catalog. Harness quality remains passing and
  digest-current; no painted long-form CTA descriptions remain. Targeted
  extraction, exact-geometry, labelledby, projection, staged-prompt, and
  renderer regressions: **25 passed**.
- Refreshed the digest-current measured replica after this proven correction:
  overall **0.8633 → 0.8891**, nav **0.9159 → 0.9382**, and the formerly
  label-expanded product grid **0.8086 → 0.9161** (4,242px collapsed to 2,072px
  versus the 1,600px source). G4 remains blocked below 0.90; carousel statics and
  remaining platform/agent/headrail/testimonial width-height divergence are the
  active residuals.
- Final full suite: **1,674 passed + 4 subtests**, 8 existing Pillow warnings,
  zero failures; edited-file lints clean.

## Responsive-fidelity vertical slice — HERO + FOOTER (2026-07)

Scope: the FIRST vertical slice of the responsive-fidelity plan, taking ONLY the hero and
footer through Phase 2 (responsive-fact schema) → Phase 3 (purge un-grounded defaults) →
Phase 4 (renderer consumes), proving the CSS-first → responsive-render chain end-to-end.
Driven by `compose/replica/css-diff.md`, fixed by exact rows (not by eye).

- **Phase 2 (schema + populate).** New `brand_pipeline/responsive_facts.py` derives a
  generic, provenance-tagged `responsive` fact block for the hero and footer from
  `evidence/joined-evidence.json` and writes the `responsive-facts.yaml` sidecar (merged
  into the doc at `compose_page.load_doc` → `apply_responsive_facts`; `brand.yaml` stays
  byte-identical). Hero: `heightRule: viewport-minus-nav` (from `calc(100dvh -
  var(--global-nav-header-height))`), nav offset ladder 56px/128px@1080, heading ladder
  48px/55px → 80px/95px@600. Footer: grid breakpoint 900 (1→2 columns, from
  `column-count:2 @media(width>=900px)`), measured `maxWidth: 1080`.
- **Phase 3 (purge).** The invented footer band `max-width: 1080px` cap is removed (source
  band measured `max-width: none`); the band paints full-bleed and the inner content caps
  at the measured `maxWidth`. Token-provenance doctrine extended from color to layout +
  motion for the hero/footer paths (documented in `spec/brand-schema.md §4.4h`).
- **Phase 4 (renderer).** `component_render.hero_responsive_css` /
  `footer_responsive_css` emit the grounded responsive CSS (hero full-bleed
  `calc(100dvh - nav)` viewport band + heading shrink + aspect-ratio neutralization;
  footer `@media` column reflow + measured content cap). Fact-gated: `""` when the block
  is absent → byte-identical output for brands/components without it. `compose_replica`
  carries the `responsive` block through demo-hydration adaptation.
- **Harness.** `css_fidelity.vp_height_signature` compares the viewport-height MECHANIC
  (not the source-specific var name), so our generic `--c-hero-nav-offset` and the
  source's nav var read as the same grounded mechanic.

Results (css-diff before → after): **27 → 22** divergences, **critical 3 → 1**. Dropped:
`hero.height-rule` (critical), `footer.responsive-columns` (critical), `footer.max-width`
(invented-default), `heading-h1.font-size @375`, `heading-h1.line-height @375`. **Zero new
divergences.** Only remaining hero/footer row is `footer.padding` (medium, out of the
slice's must-fix list). Studio screenshots at 1440 + 375 under
`compose/replica/slice-shots/` prove the hero fills viewport-height (772px @1440, 756px
@375) and the footer re-columns (5 columns @1440 → 1 column @375).

Verification: C1–C28 **0 errors**; v3 replica overall **0.8891 → 0.9026 → 0.9109** (≥0.90;
hero band 0.857 → 0.933, repH 772 = source 772); hubspot-v2 **0.9556** / remote **0.9509**
re-scored — composed HTML proven BYTE-IDENTICAL with the responsive code active vs
disabled, so the ~0.001 v2 SSIM delta is screenshot noise, not a renderer change (the
committed v2/remote replica artifacts were left untouched). Full suite **1856 passed / 3
pre-existing unrelated fails** (relume recipe prompt text + runtime model defaults) — zero
NEW failures; +14 new tests (`test_responsive_facts.py` + `test_css_fidelity.py`
slice-acceptance + `vp_height_signature`). Generalizing to the other components is the
next step.

## Responsive-fidelity GENERALIZATION + Phase 5 multi-viewport gate (2026-07-21)

Extended the proven hero+footer responsive-fact mechanism (commit `3b4de60`) to the
REMAINING computed-CSS divergences in `compose/replica/css-diff.md`, driven by the report
rows (not by eye). Same pattern: evidence-derived, provenance-tagged, GENERIC fact blocks
in the `responsive-facts.yaml` sidecar, merged at `load_doc`, consumed by fact-gated
emitters that return `""` (byte-stable) without a block.

- **New sidecar fact blocks (`responsive_facts.py`).** All derived from
  `evidence/joined-evidence.json`, all generic/provenance-tagged:
  - `nav.panelSurface.background` — the mega-nav PANEL CONTAINER surface, resolved through
    the source's CSS-var chain (`var(--cl-color-container-01)` → measured `#ffffff`). The
    measured `megaPanel.surface.bg` had captured the transparent OUTER wrapper (the CRITICAL
    missing surface the harness flagged).
  - `hero.primaryButton` — measured @1440 control box (font-size 18px, line-height 32px,
    padding 16px 40px, transparent 2px reserved border) + `motionPurge.hoverTransform`.
  - `buttons.purgeHoverTransform` (doc-level) — the source button state rules swap
    bg/border/color only, so the composer's `translateY(-1px)` hover lift is un-grounded
    MOTION (provenance doctrine) and is purged brand-wide when grounded.
  - `headings.lineHeights` — measured per generic heading tag (h2/h3 = 28px; the composer
    type scale mis-derived 1.3em = 23.4px).
- **Emitters (`component_render.py`), fact-gated + scoped.** `nav_mega_css` prefers the
  responsive panel-surface when the measured surface reads transparent; new
  `hero_primary_button_css` (scoped `#sec-N .c-button:not(.c-button--navcta)`) and
  `heading_responsive_css` (`:is(h2, .c-heading--h2)…`, emitted after the base rules so the
  measured value wins); `_button_variant_css` drops the hover-transform line only under the
  purge fact. Wired into `compose_page.build_page`.
- **Purge (provenance rule).** The un-grounded button hover `translateY(-1px)` is removed
  for brands whose measured buttons carry no hover transform; brands without the fact keep
  it (byte-identical).

Results (css-diff before → after): **22 → 13** divergences, **critical 1 → 0**. Resolved:
`nav.panel-background` (CRITICAL), `button-primary.transform:hover` (invented-default,
purged), `button-primary.font-size` (14→18), `button-primary.line-height`,
`button-primary.border`, and `heading-h2.line-height` ×4 viewports. All FOUR acceptance
divergences now report resolved. **Zero new divergences.**

Residual (documented capability limits, not faked):
- `button-primary.display` (flex vs block) + `.width` (176 vs 183px) — a box-model
  equivalence: our inline-flex renders an identically-centered content-hugging pill; the
  computed keyword differs and the ~7px width gap is font-fallback metrics.
- `section-4.background-color` (rgb 249,201,192 vs 252,222,210) — an AUTHORED surface-token
  drift in `brand.yaml`, not a responsive fact (left untouched per scope).
- `footer.padding` (0 vs 48px 32px) — probe-vs-element mismatch (the harness probes the
  inner `.c-footer`; the band padding is on `#sec-N`), same apples-to-oranges class the
  harness already documents for section max-width.
- 9× `font-family` (low) — pre-existing computed-stack quoting/order artifact (present in
  the 22-row baseline), not introduced here.

**Phase 5 — multi-viewport replica gate (`compose_replica.py`).** New
`measure_viewport_ladder` scores the composed replica at the viewport ladder (1440 primary
+ 1920/960/375). 1440 stays the source-FIDELITY score; the other viewports record a
RESPONSIVENESS-HEALTH number (1.0 = no horizontal overflow, every band present, reflow
intact) since there is no source shot at those viewports to SSIM against — labeled as such
(honest, not a faked cross-viewport score). `replica-report.{md,json}` gain a per-viewport
section; full-page screenshots saved at every viewport (`replica-fullpage-<w>.png`).

Per-viewport (v3): 1440 fidelity **0.9111** (≥0.90); 1920/960 health **1.000**; 375 health
**0.500** (389px overflow from `.cs-nav-util` — a PRE-EXISTING nav mobile-collapse
capability gap, unchanged by this work and shared by all brands; the v3 footer correctly
collapses 5→1 columns at 375 via the responsive facts). Baselines RECORDED (not failed):
v2 1440 **0.9556** / 375 health 0.500; remote 1440 **0.9509** / 375 health 0.500 — their
footers stay multi-column at 375 (no responsive facts → byte-stable), the intended contrast.

Verification: C1–C28 **0 errors** (12 advisory warnings). v3 replica **0.9109 → 0.9111**
(held). hubspot-v2 **0.957 → 0.9556** / remote **0.9509** HELD — composed HTML proven
BYTE-IDENTICAL with the responsive code active vs the HEAD baseline (per-brand diff = 0),
so the ~0.001 v2 SSIM delta is screenshot noise. Full suite **1773 passed**, zero NEW
failures (the 11 failed + 4 errors are pre-existing environment-dependent Playwright/glyph
tests, identical on HEAD); +16 new tests (nav/button/heading fact derivation + emitters +
brand-wide purge gate + multi-viewport report shape; `test_css_fidelity` acceptance updated
to the all-resolved state). v3 harness rebuilt digest-current (7/7 chapters, 36 primitives,
32 blocks, 10/10 composed).

## CSS-variable-first type scale — collapsed heading ladder repair (2026-07-21)

**Root cause.** The type-scale evidence came from `measure_computed`'s `q(tag)` probe —
the FIRST `h1`/`h2`/… in DOM order — and the authoring stamped a `singleTierConfirmed`
size per tag. The first `h2` in source order is a hero CTA control (18px), and the first
`h1` is the hero override (80px), so the authored ladder collapsed to h1=80 / h2=18 /
h3=16 with h4–h6 absent. A single measured instance is never authoritative for a tier.

**Fix (systemic, brand-agnostic).** Extract the scale CSS-FIRST from the source's own
font-size design tokens:
- New `tools/extract/type_scale.py` collects every `--*font-size*` custom property,
  resolves `var()` alias chains + rem→px, evaluates `@media` responsive overrides
  (mobile-first base + `min-width` desktop bump), binds each token to the heading/text/
  control role via its CONSUMING selector (STRICT: a bare `hN` tag or a sole `.cl-hN`
  utility — not substrings inside instance classes like `.-h2-on-mobile`), resolves the
  suffix-matched line-height/weight/family tokens, and emits a canonical tier ladder to
  `evidence/type-scale.json`. Where a brand declares NO font-size tokens it falls back to
  clustering the computed sizes of ALL headings (never a single instance).
- Extraction on hubspot-v3 (36 font-size tokens) yields: display 112 / h1 48 / h2 40 /
  h3 24 / h4 22 / h5 18 / h6 16 / body 16 / small 14 / micro 12 — with lh + weight +
  serif/sans per tier. The confirmation channel records that the measured first-instance
  h2 (18px) and h1 (80px) DISAGREE with the css-var truth (proof of the single-instance
  bug). This reproduces the hand-authored (protected) hubspot-v2 scale from CSS vars
  alone — strong cross-check that the reader is correct and brand-agnostic.

**Re-authored `tokens.type`** from the css-var truth (replacing the collapsed scale):
display-hero 80/48 serif; h1 48/40 serif; h2 40/32 serif; h3 24, h4 22, h5 18, h6 16 sans;
body 16 w300, small 14 w300, micro 12 — correct line-heights (1.15/1.1/1.42/1.45/1.56/1.75/
1.75) + weights (headings 500, body/small 300) + family split (serif display/h1/h2, sans
the rest). Each tier carries `provenance {source: css-var, sourceVariable, confirmedBy}`.
The false `singleTierConfirmed` was removed from the responsive tiers (h1/h2 vary 48→40 /
40→32); it is kept only on the tiers that are genuinely constant across the ladder.

**css_fidelity heading-tier audit (new).** `css_fidelity.py` now probes h1..h6 in the
replica AND diffs the AUTHORED scale against the css-var truth (`type-scale.json`) per
heading tier — so a collapsed/mis-authored ladder that renders self-consistently is
catchable by construction. Heading-tier divergences BEFORE→AFTER: **8 → 0**
(before: h1 80↛48, h2 18↛40 +lh, h3 16↛24 +lh, h4/h5/h6 absent).

**Verification.** C1–C28 **0 errors** (11 advisory warnings; C24 style-scale digest
refreshed). v3 replica **0.911 → 0.910** (≥0.90; the corrected larger headings barely move
the bands — reported honestly). hubspot-v2 / remote brand.yaml **byte-identical** (SHA
unchanged: v2 b25970e7…, remote 1dae928f…) — the css-var reader was NOT run against their
authored scales. Full suite **1884 passed**, +14 new type-scale/heading-audit tests; the
3 remaining failures (`test_runtime_defaults` site-gen providers, `test_relume_recipe_catalog`
prompt guidance) are pre-existing and unrelated (verified failing with this change reverted).
v3 harness rebuilt (7/7 chapters); type-scale chapter screenshot
`harness/after-type-scale-fixed.png` shows the true descending ladder.

**Systemic principle.** Extract token SCALES from CSS custom properties FIRST, then confirm
with measured instances + vision — never author a tier from a single sampled element.
Type is done here; spacing / radius / color scales are the natural follow-ups (same pattern:
read the declared `--*` tokens, resolve consumers + responsive variants, confirm).

## Tabbed-testimonial-with-stats anatomy + AS-81 anatomy-presence gate (2026-07-21)

**Root cause.** `tabbed-testimonial-with-stats` rendered as a plain single quote (no tab
rail, no stats). The layout-library pattern declared `kind: tabbed-content-swap` (not the
sanctioned `kind: tabs` the renderer stamps into `_tabs`) and section-copy carried no
`panels`/`tabs`, so `compose_info_band`'s tab guard (`copy.panels` + `_tabs` stamp) was
false and the section degraded to the default split (heading + body + one image). A
renderer/anatomy CAPABILITY gap — invisible to a CSS-property diff.

**Source truth (saved DOM, verbatim).** 3-tab switcher — Enterprise (active, 4px `#ff4800`
underline = `--cl-color-border-brand-01`), Mid-Sized Business, Small Business. Each panel:
photo-left / quote + bold author + role + "Read full case study" link right, closed by a
stat footer. Stat counts vary per panel: Enterprise 12 / 5 (2); Mid-Sized 300%+ / ~350 / 7
(3, Angel City FC); Small Business 59% / 17% / 7% (3, Youth on Course). All three panels
authored into `section-copy.yaml` under `panels` (+ `tabs` labels). The section heading
"Remarkable results…" belongs to the preceding headrail band and rides here only as the
tablist aria-label.

**Fix — REUSE the existing devices, no parallel mechanism.**
- `section-copy.yaml`: added `tabs` + 3 `panels` (quote/name/role/caption/media/stats).
- `layout-library.yaml`: promoted the treatment to a sanctioned `tabs`
  (`activeUnderline: rgb(255, 72, 0)`) + `stat-rule`; gave the portrait slot the measured
  `mediaScale {of: container, fraction: 0.56}` and a `state-swap` mediaComposition binding
  the three registered logical assets (`unipart-1`/`angel-fc`/`youth-on-course` — C27-clean).
- `compose_section.py`: `stamp_pattern_devices` tabs branch now reads the panel media
  fraction from the media slot by ROLE (portrait/photo/media/image) as well as by name, so
  the `portrait` swap slot carries `--cs-tabs-media-frac`. `name=="media"` still matches
  first ⇒ v2's tab pattern is byte-identical. The WAI-ARIA APG tab device
  (`_compose_tab_split` + `_IX_TABS_JS`) and `render_stat` do the rest unchanged.

**New AS-81 anatomy-presence audit.** `onbrand_check.anatomy_presence_hits` /
`check_anatomy_presence` (wired into the composition-invariant rows): a section whose
declared pattern is a tabbed/multi-panel or stat device MUST render its tab controls
(≥2 `role="tab"`) and its stat items (`c-stat-value`/`cs-tabcard-stat`). Word-anchored
device detection (so "sans stat heading" / "deep-accent active state" / "inset rounded
panel" never misfire); order-aligns declared composition sections to rendered non-chrome
`<section>`s; fails OPEN on count mismatch. Structural, not a CSS-property diff — analogous
to AS-80. Registered in `spec/anti-ai-slop.md` AS-81. Tests:
`brand_pipeline/tests/test_anatomy_presence.py`.

**Verification.** C1–C28 **0 errors** (11 pre-existing warnings). Section band `sec-7`
**0.8673 → 0.946** (structure 0.8444→0.9423, pixel 0.8315→0.9254; height 730→704px vs 714
source). Replica overall **0.9155 → 0.9236** (≥0.90). hubspot-v2 / remote composed
`index.html` proven **byte-identical** with vs without the `compose_section` change (same
SHA) — v2 0.957 / remote 0.951 HELD, not re-shot. Full suite **0 NEW failures**, +19 new
tests (the 3 remaining are pre-existing relume-recipe-catalog ×2 + runtime-defaults ×1).
Harness screenshots: `harness/after-tabbed-testimonial-{enterprise,midsized,smallbiz}.png`;
before/after band `compose/replica/diff/sec-7.png`.

---

## Nav mobile-collapse — responsive-collapse fact + renderer (2026-07-22)

**Concern (top remaining multi-viewport gap).** The composed page nav did not collapse to
a mobile bar below the source breakpoint: at 375px the two-tier utility row + primary link
rail + bar CTAs stayed in the bar and overflowed (v3 `overflowEl=cs-nav-util`, 389px; nav
page `scrollWidth` 764). The 375 responsiveness-health floored at **0.500** across
v3/v2/remote.

**Source truth (chrome-header CSS, joined-evidence).** The source nav is MOBILE-FIRST:
`.global-nav-top-bar` (utility) and `.global-nav-main-tab-list` (primary rail) are
`display:none` at base and `display:flex` only in `@media(width >= 1080px)`; the burger
group (`.-mobile-only` / `.global-nav-burger-btn`) shows below 1080 and hides at/above it.
Below the breakpoint the bar is a **logo + burger** mobile bar. `remote` (a DIFFERENT
source) declares the identical mechanic at **1200px** via CSS-module classes
(`menuToggle`/`navMobileBar`/`mainNav`) — the pattern is brand-agnostic.

**Root cause.** `render_navbar` never implemented the collapse; the one partial guard
(`@media(max-width:991px){.cs-nav-util{display:none}}`) LOST the specificity battle to the
two-tier base rule `.cs-nav-tier--utility .cs-nav-util{display:inline-flex}`, so the
utility cluster never left the bar.

**Fix — REUSE the responsive-facts mechanism (no parallel path).**
- `responsive_facts.py`: `_nav_collapse_from_evidence` derives a generic, provenance-tagged
  `collapse {breakpoint, burger}` fact from the mobile-first `display:none` rows + the
  burger-hide `@media` (separators optional → kebab and camelCase module names both match).
  Folded into the nav responsive block beside `panelSurface`.
- `compose_section._navbar_props`: fact-gated `mobileCollapse` prop (measured breakpoint +
  the captured `mobile-burger` utilityControl label, default `Menu`).
- `component_render.render_navbar`: emits a burger disclosure `<button>` (aria-expanded /
  aria-controls) + a hidden mobile drawer (top-level primary + utility labels) ONLY when the
  prop is present. Both nav paths (two-tier + single-tier).
- `component_render.nav_collapse_css`: fact-gated, `#page-nav`-scoped burger chrome + an
  `@media(max-width: breakpoint-1)` that hides the utility tier / navlinks / bar CTAs and
  shows the burger (ID specificity beats the two-tier base rule). Wired into `compose_page`
  css_parts after the nav base/affordance CSS.
- `_IX_BURGER_JS`: disclosure wiring (CSS-only fallback keeps the burger shown + drawer
  closed with JS off). `render_components_preview` pops the prop (gallery bar byte-unchanged).

**Byte-stability.** The burger is `display:none` at/above the breakpoint and the drawer is
`hidden` at rest, so DESKTOP is byte-identical. Proven: the collapse fact yields an HTML
strict-superset (0 lines removed/modified; only burger + hidden drawer + scoped CSS/JS
added); the sole rendered pixel delta is <=3/255 sub-perceptual footer font-AA jitter that
ALSO appears between two identical builds (maxdiff 1) — cross-process noise, not this change.
The v3 1440 full-page shot is pixel-identical to the pre-change on-disk baseline.

**Verification.** C1-C28 **0 errors** (v3/v2/remote). css_fidelity v3 **critical 0**. 375
nav overflow **gone** (nav scrollWidth 375; burger shown; utility/links `display:none`).
375 responsiveness-health: v3 **0.500 -> 0.893** (residual 20px overflow is `cs-edgecut`, a
carousel gap, out of scope); v2/remote page-health stays 0.500 because their DOMINANT 375
overflow is a different component (v2 `cs-edgecut` 573px; remote `cs-marquee-track` 654px) —
but their nav overflow is likewise eliminated. Breakpoints: hubspot 1080, remote 1200. Full
suite **0 NEW failures**, +13 new tests (`test_responsive_facts.py`). Before/after 375 nav
screenshots: `compose/replica/nav-collapse-shots/nav-375-{before,after}.png`. Held for
review (no commit/push).
