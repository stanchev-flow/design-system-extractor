# Hardcode Audit — visual values in the deterministic rendering path

**Date:** 2026-07-03 (00:10–00:40 UTC+1)
**Auditor:** read-only token-layer design worker
**Working-tree state:** audited against IN-FLIGHT edits (alignment-resolution batch worker active on
composers/gate; extraction worker active on `runs/hubspot/**`). Line numbers are anchored to the
tree as of the mtimes in `changes.md` and **will drift** — every finding also carries its
function/selector anchor. Treat selector anchors as primary.

**Scope:** `brand_pipeline/component_render.py`, `compose_section.py`, `compose_page.py`,
`render_components_preview.py`, plus shared helpers `styles.py` and `render_section.py`
(token resolvers + legacy single-section renderer).

---

## 0. Headline numbers

Raw pattern hits (regex scan for hex/rgba/px/rem/em/cq*/weight/radius/shadow/duration/easing/
aspect/text-transform/letter-spacing/z-index/opacity literals, including `var(--x, LITERAL)`
fallbacks — categories overlap slightly, e.g. a `font-size: 1.17rem` counts in both
`font-size` and `rem`):

| file | raw hits | dominant categories |
|---|---|---|
| `compose_section.py` | **347** | rem/em 213, cq-units 31, z-index 24, px 21, hex 16, aspect 10 |
| `render_components_preview.py` | **399** | rem/em 182, px 45, font-size 32, text-transform 29, hex 22, easing 19 |
| `render_section.py` (legacy path + shared resolvers) | **232** | rem/em 110, text-transform 20, px 16, letter-spacing 11, hex 11 |
| `component_render.py` | **127** | rem/em 36, easing 24, px 16, duration 11, text-transform 10 |
| `styles.py` | **26** | rem/em 17, px 5, hex 2, duration 2 |
| `compose_page.py` | **20** | rem/em 9, px 4, hex 4, rgba 2 |
| **total** | **1,151** | |

Grand totals by category: rem/em **567**, px **107**, hex **61**, text-transform **60**,
container-query units **51**, font-size literals **48**, easing **45**, z-index **33**,
aspect-ratio **27**, letter-spacing **24**, radius **23**, weight (non-CSS-prop) **22**,
opacity **21**, duration **20**, rgba **18**, `font-weight:` **16**, shadow **8**.

**Interpretation discipline:** raw hits ≠ violations. Roughly a third are (a) genuinely
structural mechanics (z-index ladder, `repeat(12, 1fr)` grids, `margin:0` resets, breakpoint
widths), (b) values inside the *token resolvers themselves* (`render_section.py` converting
brand.yaml into vars — that's the token layer working), or (c) gallery-harness-only CSS.
The curated findings below are the ~40 clusters that actually leak brand DNA or block a
foreign brand. Each cluster lists representative anchors, not every one of its raw hits.

---

## 1. `component_render.py` — the `c-*` component SSOT

### CR-1 — Uppercase transform baked into the component vocabulary ⚠️ WoodWave DNA (top leak)
- **Anchors (10 sites):** `.c-heading` (L409), `.c-eyebrow` (L425), `.c-list` eyebrow row (L455),
  `.c-arrow-link` (L458), `.c-logo` (L482), stat eyebrow (L501), nav links (L513),
  field label (L523), `.c-foot-sitemap-link` (L539), footer heading (L547).
- **Raw value:** `text-transform: uppercase` (category: typography/case).
- **Judgment:** pure WoodWave editorial DNA. Both brand.yamls carry per-tier `case:` fields
  (WoodWave `uppercase` on display/h1–h3/eyebrow/control; HubSpot `sentence`/`none` everywhere,
  plus `never-allcaps-headings` in neverDo). The value exists in the brand layer and is ignored.
- **Proposed token:** `--c-case-heading`, `--c-case-eyebrow`, `--c-case-control`
  (from `tokens.type.<tier>.case`, emitted as `text-transform` value; `sentence`→`none`).
- **Cross-ref:** REPORT.md **B7** (allcaps headings on HubSpot render) — **confirmed**.

### CR-2 — Button cluster: weight/padding/size/letter-spacing/border are one brand's button ⚠️ WoodWave-adjacent DNA
- **Anchor:** `.c-button` block (L470–476).
- **Raw values:** `font-weight: 700`; `letter-spacing: 0.01em`; `font-size: max(1.17rem,
  var(--c-control-size))`; `padding: 0.8em 1.6em`; `border: none`; hover `filter:
  brightness(1.08)` + `transform` (L474–475).
- **Judgment:** DNA. HubSpot measures `buttons.primary = {weight 500, padding 0.75rem 1.5rem,
  radius 0.5rem, bg #ff4800, bgHover #c93700, fg #ffffff, sizeRem 1.0}` — none of it reachable.
  Hover-as-brightness-filter is also a motion-language assumption (HubSpot hover is a measured
  bg swap, not a filter).
- **Proposed tokens:** `--c-button-weight`, `--c-button-ls`, `--c-button-size`,
  `--c-button-pad`, `--c-button-radius`, `--c-button-bg`, `--c-button-fg`,
  `--c-button-bg-hover`, `--c-button-border` (from `buttons.primary.*` when present, else
  derived from `type.scale.button-md` + `tokens.radius.button` + `spacing.button-inset`).
- **Cross-ref:** REPORT.md **B3** (primary CTA renders as typographic link / wrong shape)
  — **confirmed and extended** (REPORT focused on filled-vs-typographic; the audit adds
  weight/padding/hover-mechanic leaks).

### CR-3 — Motion defaults are WoodWave's authored motion spec ⚠️ WoodWave DNA
- **Anchors:** `_MOTION_DEFAULTS` dict (L180–182: `cubic-bezier(.22, 1, .36, 1)`,
  `320ms/480ms/620ms`, `16px` shift); every `var(--c-motion-fast, 320ms)` / `var(--c-ease,
  cubic-bezier(.22,1,.36,1))` fallback literal (L289, 474–477, 566, 577–578); comment block
  "MOTION (calm / editorial) … ~320–620ms" (L553–554).
- **Judgment:** DNA in fallback position. WoodWave's `voice.motionSpec` IS 320/480/620 +
  that exact cubic-bezier; HubSpot measures `150/200/300ms ease-in-out`. The resolver
  (`motion_spec()`, L186–199) reads brand.yaml correctly — the *fallbacks* are the leak, and
  they fire for any brand with a partial motionSpec.
- **Proposed tokens:** `--motion-fast/-base/-slow`, `--motion-ease` (three-layer: generated
  from `voice.motionSpec.durations/easing`); fallback policy per SPEC §B (fail-loud, not inherit).
- **Cross-ref:** REPORT.md **B9** (motion timings) — **confirmed**.

### CR-4 — Logo wordmark styling ⚠️ editorial DNA
- **Anchor:** `.c-logo` (L481–482): `font-weight: 600; font-size: var(--c-control-size);
  letter-spacing: 0.08em; text-transform: uppercase`.
- **Judgment:** DNA (an uppercase tracked-out text logo is an editorial signature; HubSpot's
  logo is an image asset with measured 100×28px box in `navbar.measured.logo`).
- **Proposed tokens:** `--c-logo-weight/-ls/-case`; logo *kind* (image vs wordmark) is
  structural and comes from `navbar.logo` presence, not a token.

### CR-5 — Underline-only field as the only input archetype ⚠️ structural DNA (needs flag + tokens)
- **Anchors:** `.c-field` cluster (L506–523): `border: none; background: transparent`,
  pseudo-element hairline (`height: 1px`, L511/521), uppercase label.
- **Judgment:** the *mechanic* honors WoodWave `no-boxed-inputs`, but hardcodes the underline
  archetype for every brand. HubSpot measures boxed inputs (`tokens.radius.input: 0.25rem`).
  A token alone is insufficient — input *shape* is a structural variant (see SPEC §C.3).
- **Proposed:** structural flag `input-shape: underline|boxed` (from brand primitives/neverDo:
  `no-boxed-inputs` ⇒ underline; `tokens.radius.input` present ⇒ boxed) + tokens
  `--c-input-radius`, `--c-input-border`, `--c-input-bg`.
- **Cross-ref:** REPORT.md **B8** — **confirmed**.

### CR-6 — Aspect-ratio literals in media variants — mixed
- **Anchors:** `.c-image` aspect variants (4 `aspect-ratio:` sites, ~L430–450 region).
- **Raw values:** `3 / 2`, `4 / 5`, etc. as `var(--c-aspect-*, LITERAL)` fallbacks.
- **Judgment:** the *palette* belongs to the brand (`tokens.imagery.aspectPalette` exists in
  WoodWave; HubSpot has none yet — extraction gap). Fallback literals are the WoodWave palette.
- **Proposed tokens:** `--aspect-band/-landscape/-near-square/-portrait` (already exported by
  `export_kit.build_tokens_css` — reuse those names).
- **Cross-ref:** anti-slop AS-17 (aspect-ratio monotony) — related; REPORT.md silent. **Audit-only finding.**

### CR-7 — Hairline fallback + `--c-accent` fallbacks — universal mechanic, DNA values
- **Anchors:** `root_vars`/`component_vars` (L90–156): `or "#111111"`, `or "#ffffff"`,
  `"#141414"` (L104), hairline fallback to muted ink (L117–134, the AS-01/AS-02 fix).
- **Judgment:** mechanically universal (surface-aware resolution is correct); the literal
  fallback hexes are neutral-ish but still raw emission when a brand token is missing.
  Under token-provenance these become fail-loud instead (SPEC §B.3).

### CR-8 — Micro-spacing inside components — mostly universal, tokenizable via scale
- **Anchors:** ~36 rem/em hits: `.c-arrow-link` gap `0.5rem`, arrow hover `translateX(4px)`,
  stat gaps, checkbox `1.1em` box, etc.
- **Judgment:** universal *relationships* (icon-to-label gap) but the magnitudes should snap
  to the brand/style spacing scale per anti-slop AS-03. Low severity; tokenize opportunistically
  as `--space-inline-xs/-sm` aliases, do not block the batch on them.

**component_render.py counts:** 127 raw hits → 8 curated clusters; 5 DNA (CR-1..5), 1 mixed
(CR-6), 2 universal-with-token-work (CR-7, CR-8).

---

## 2. `compose_section.py` — archetype composers + `cs-*` scaffold CSS

### CS-1 — WoodWave panel surface hexes as var() fallbacks ⚠️ WoodWave DNA (most literal leak in the tree)
- **Anchors:** `SCAFFOLD_CONVERSION_CSS` `.cs-panel` (L2501–2510) and `SCAFFOLD_BANDED_CSS`
  band panel (L2746–2752): `var(--c-panel, #F7EFE6)`, `var(--c-panel-ink, #1F1A14)` (×7),
  `var(--c-panel-hairline, rgba(31,26,20,0.30))` (×2); ghost fallback
  `var(--c-ghost, rgba(31,26,20,0.06))` (L2450).
- **Judgment:** DNA — these are literally WoodWave's measured cream/ink/hairline/ghost values
  serving as the universal fallback for every brand.
- **Proposed tokens:** already var-first (`--c-panel`, `--c-panel-ink`, `--c-panel-hairline`,
  `--c-ghost`); the fix is fallback policy — generated tokens.css must always define them,
  fallbacks become `var(--c-panel)` with **no literal** (fail-loud).
- **Cross-ref:** REPORT.md **B4** (panel/card surface leaks) — **confirmed**, with exact hexes.

### CS-2 — Ghost-watermark scale ladder ⚠️ editorial DNA
- **Anchors:** `_GHOST_SIZE` (L392–394: `clamp(6rem, 22cqw, 18rem)` / `clamp(8rem, 30cqw,
  24rem)` / `clamp(10rem, 40cqw, 32rem)`), emission (L485), per-archetype ghost font-size
  fallbacks (L2449, 2581, 2486).
- **Judgment:** DNA. The ghost-word device itself is style-layer (radical-editorial); the
  *scale* belongs to the brand (WoodWave measures `type.ghost-watermark.sizeRem: 26.25`).
  HubSpot has no ghost tier — on a brand without the token the device should be unavailable,
  not WoodWave-sized.
- **Proposed:** `--size-ghost-watermark` (exists in kit tokens.css) driving `--c-ghost-size`;
  ladder becomes multipliers of the brand value (structure), not absolute rems.

### CS-3 — Section padding / rhythm constants ⚠️ editorial DNA (spacing character)
- **Anchors:** `.cs-section` padding + mobile override (L2432–2438), `.cs-nav` margin
  `clamp(2rem, 6cqw, 5rem)` (L2370), `.cs-spacer { height: clamp(4rem, 12cqw, 9.5rem) }`
  (L2403), `.cs-modules-intro` `clamp(2.5rem, 6cqw, 5rem)` (L2661), module row-gap baseline
  calc (L2662), dozens of `gap: 2.5rem`/`0.75rem`/`1.25rem`/`1.5rem` across
  `SCAFFOLD_{COLLAGE,FAQ,STATEMENT,QUOTE,GALLERY,CARDS,OVERLAY,BANDED,FLOW}_CSS`
  (L2469–2855 region). ~213 rem/em hits total.
- **Judgment:** DNA in magnitude, universal in relationship. WoodWave breathes at
  `6.875rem/6.25rem/7.5rem` (its measured spacing tokens); HubSpot at `4rem/6rem/2.5rem`.
  Both brands carry a full `tokens.spacing` scale that the scaffold never reads.
- **Proposed tokens:** `--space-section-pad-x/-y` (per-surface variants
  `section-padding-light/-dark` exist in WoodWave; `section-y-md/-lg` in HubSpot — SPEC §A
  maps both into shared roles), `--space-module-gap`, `--space-stack-sm/-md/-lg`,
  `--space-panel-pad`, `--c-inset-drop` derived from scale. Clamp *shape* (fluid min/max)
  stays structural; the rem endpoints resolve from tokens.
- **Cross-ref:** REPORT.md **B5** (spacing character) — **confirmed**.

### CS-4 — Editorial offset media spans — structural, but style-gated (AS-19 work in flight)
- **Anchors:** statement/quote media col `6 / -1` defaults + `--c-statement-media-col`
  overrides (grep `media-col`), `_STAGGER_OFFSET`/`_CARD_STAGGER` ladders (L399–410).
- **Judgment:** structural devices of the editorial style — legal to keep as style-layer
  structure, but the *offsets* should scale with the brand spacing unit. Not a token-alone fix
  (SPEC §C.3). The in-flight alignment batch already stamps/gates registration (G10/G11).

### CS-5 — z-index ladder — ✅ universal (allowlist)
- **Anchors:** 24 `z-index:` sites across scaffolds.
- **Judgment:** structural layering registration (ghost behind, media mid, content front).
  Keep as constants with a provenance comment; allowlist in the provenance gate.

### CS-6 — Grid templates + breakpoints — ✅ universal (allowlist)
- `repeat(12, 1fr)`, `grid-template-columns: 1fr` collapses, `@media (max-width: 767px/1280px)`,
  `* { margin:0; padding:0; box-sizing:border-box }` (L3361). Substrate mechanics; allowlist.
  (A future refinement could tokenize breakpoints; out of scope.)

### CS-7 — `_rgba_from_hex` helper — ✅ universal resolver
- L1702–1708 converts brand hexes to rgba at declared alphas: this is token *derivation*
  (alpha ladder), not a leak. The `rgba(17,17,17,…)` fallback inside it (L1706) follows the
  fail-loud policy in SPEC §B.3.

**compose_section.py counts:** 347 raw hits → 7 clusters; 3 DNA (CS-1..3), 1 style-structural
(CS-4), 3 universal (CS-5..7).

---

## 3. `compose_page.py` — page assembly

### CP-1 — WoodWave surface literals as page-level fallbacks ⚠️ WoodWave DNA
- **Anchors:** `page_scaffold_css` region: `or "#111111"` (L142), `or "#ffffff"` (L144),
  `panel = color_value(doc, "surface/panel") or "#F7EFE6"` (L150), `panel_ink … or "#1F1A14"`
  (L151), `ghost … or "rgba(31,26,20,0.06)"` (L149), `panel_hair … or "rgba(31,26,20,0.30)"` (L152).
- **Judgment:** same class as CS-1 — WoodWave measured values as universal fallback. Note
  AS-02 applies: `color_value(doc, tok) or fallback` also *mis-fires* (returns the token name
  string when missing), so some of these fallbacks are unreachable in exactly the broken way
  AS-02 documents.
- **Proposed:** generated tokens.css defines the full closed set; Python fallbacks removed in
  favor of fail-loud generation (SPEC §B.3).
- **Cross-ref:** REPORT.md **B4/B12** — **confirmed**.

### CP-2 — Hero brand-over-style override block — mixed (mechanic universal, values leak)
- **Anchor:** `hero_brand_override_css` (`#sec-0` scoped): `text-align: center`,
  `max-width: 18ch`, accent heading color.
- **Judgment:** the override *mechanism* is sound (gate blesses it, `detect_brand_overrides`
  reads its marker). The `18ch` measure and center anchoring are WoodWave hero decisions that
  should derive from brand.yaml (`heroTreatment.align: center` exists in HubSpot — happens to
  agree) — the *derivation* must move from hardcode to brand read.
- **Cross-ref:** REPORT.md **B6** (hero treatment) — **partially confirmed** (REPORT flags
  scrim/photo mismatch; the audit adds the measure/anchor hardcode).

### CP-3 — Footer/nav chrome CSS — ⚠️ DNA via `component_render` footer/nav emitters
- The page assembles nav as page-level sibling (correct per WoodWave truth) but the footer
  sitemap Melodrama-scale typography (`.c-foot-sitemap-link`, CR-1/CR-4 cluster) is WoodWave's
  measured `footer-sitemap-link` tier (2.5rem uppercase serif) applied to any brand.
  HubSpot footer measures 16px sans links, weight 400, 5-column flex.
- **Proposed tokens:** `--c-foot-link-size/-family/-case/-weight` from
  `tokens.type.footer-sitemap-link` when present, else `footer.measured.link.*`.
- **Cross-ref:** REPORT.md **B10** (footer) — **confirmed**.

**compose_page.py counts:** 20 raw hits → 3 clusters, all DNA-bearing (CP-1..3).

---

## 4. `render_components_preview.py` — component gallery harness

### RP-1 — `--c-accent: var(--ink)` alias pinning ⚠️ DNA-adjacent harness bug
- **Anchor:** `COMPONENT_ALIAS_CSS` (`--c-accent: var(--ink)` for the light canvas)
  + `_GALLERY_CTX.is_dark = False`.
- **Judgment:** the gallery force-resolves accent to ink on its light canvas — correct for
  WoodWave's accent-on-dark-only law, wrong as a universal (HubSpot's accent is legal on
  light). This is a harness assumption that the REPORT traced into real confusion (B2).
- **Proposed:** gallery resolves per-surface interaction tokens from the generated tokens.css
  (same `--c-*-on-<surface>` re-scoping as production; SPEC §A.4).
- **Cross-ref:** REPORT.md **B2** — **confirmed**.

### RP-2 — ~390 literal `ex-*` preview styles — harness-only, low severity
- Uppercase labels, `font-weight: 400`, `border-radius: 0`, paddings, 19 easing hits, etc.
  These never ship in a composed page; they style the gallery chrome. But they *display*
  specimens with WoodWave assumptions, which misleads visual review of a foreign brand.
- **Judgment:** universal harness chrome (keep literal, allowlist as `preview-chrome`) vs
  specimen styling (must come from tokens.css). Split enumerated in SPEC §C.4.
- **Cross-ref:** REPORT.md **B1** (gallery renders WoodWave-flavored components for HubSpot)
  — **confirmed**.

---

## 5. `styles.py` — style-layer structure defaults

### ST-1 — Numeric structure defaults on `StyleStructure` — style DNA by design, needs override discipline
- **Anchors:** dataclass defaults: `radius "0"`, `min_display_rem 9.0`, `display_vw 12.0`,
  `display_max_rem 16.0`, `display_leading 0.94`, `display_tracking "-0.02em"`,
  `motion_min_ms 500 / motion_ms 600`, `space_scale` dict (~17 rem entries),
  `paper #FCFCFA / ink #111111` (L59–60).
- **Judgment:** the style layer is *supposed* to define structure — but these numerics are
  radical-editorial's numbers acting as the base for every style, and `paper/ink` are
  placeholder colors that must never reach output. Under the token layer: style structure
  states **stances and ratios** (poster-scale floor, leading character); brand tokens supply
  measured magnitudes; placeholders become provenance-tagged `style-default` values the gate
  flags when they survive into emitted CSS.
- **Cross-ref:** REPORT.md **B11** (style defaults bleeding) — **confirmed**.

---

## 6. `render_section.py` — shared resolvers + legacy single-section renderer

- The resolvers (`color_value`, `type_role`, `spacing_value`, `base_size`, `css_len`,
  `font_stack`) are the *existing* brand→CSS bridge and are mostly sound; they are where the
  token generator should live or be extracted from.
- The legacy CSS template in this file repeats the same DNA clusters (uppercase ×20,
  letter-spacing ×11, radius ×6, shadow ×6). It renders the single-section previews, not
  composed pages. **Recommendation:** bring it under the same tokens.css include in phase 3
  (SPEC §H), not phase 1 — the composers are the live path that failed HubSpot.
- 232 raw hits → same cluster taxonomy as §1–2; no new cluster classes found.

---

## 7. Cross-reference vs `runs/hubspot/brand/REPORT.md` (mtime 2026-07-02 23:08)

| REPORT blocker | audit verdict |
|---|---|
| B1 gallery renders WoodWave-flavored specimens | **confirmed** (RP-1, RP-2) |
| B2 `--c-accent` pinned to ink on light canvas | **confirmed** (RP-1) |
| B3 CTA renders typographic/wrong shape | **confirmed + extended** (CR-2: weight/pad/hover too) |
| B4 WoodWave panel/cream surfaces leak | **confirmed with exact hexes** (CS-1, CP-1) |
| B5 spacing character | **confirmed** (CS-3) |
| B6 hero treatment mismatch | **partially confirmed** (CP-2; REPORT adds scrim/photo asset gaps the audit ratifies but which are extraction-side) |
| B7 allcaps headings | **confirmed** (CR-1) |
| B8 boxed vs underline inputs | **confirmed** (CR-5) |
| B9 motion timings | **confirmed** (CR-3) |
| B10 footer chrome | **confirmed** (CP-3) |
| B11 style numeric defaults | **confirmed** (ST-1) |
| B12 surface role name reliance (`surface/inverse-strong` KeyError, gen.log attempt 0/2) | **confirmed** (CP-1 + `SURFACE_INTENT_MAP` in `compose_from_composition.py` L55–61 maps composition intents to role keys that must exist; HubSpot's re-extraction added the alias roles 2026-07-02 23:23) |

**Found by audit, absent from REPORT.md:**
1. CR-6 aspect-ratio fallback palette (WoodWave ratios as universal fallback).
2. CR-4 logo wordmark styling (uppercase tracked wordmark vs HubSpot image logo).
3. AS-02-shaped unreachable fallbacks in `compose_page` (`color_value(...) or fallback` —
   the fallback can be *bypassed* by a truthy token-name return, emitting an invalid color).
4. CS-2 ghost scale ladder absolute rems (REPORT mentions ghost presence, not scale source).
5. ST-1 `paper/ink` placeholder hexes in `styles.py`.

**In REPORT.md, not independently verifiable by this audit (extraction-side):** missing
HubSpot asset files, `HS_Full_Bleed_1_optmised.webp` availability, live-worker items in
`gen4/gen5.log` (asset + text-contrast failures) — noted, owned by the extraction worker.

---

## 8. Category totals across curated clusters

| category | clusters | severity under token-provenance |
|---|---|---|
| color (hex/rgba fallbacks) | CS-1, CP-1, CR-7, ST-1 | **error** |
| typography case/weight/tracking | CR-1, CR-2, CR-4, CP-3 | **error** |
| spacing/rhythm | CS-3, CR-8 | **error** (scale-off) |
| radius/shape | CR-2, CR-5 | **error** |
| motion duration/easing | CR-3 | **warning** |
| aspect palette | CR-6 | **warning** |
| structural (z-index, grids, breakpoints, resets) | CS-5, CS-6 | **allowlisted** with provenance comments |
| style-structure numerics | ST-1, CS-4 | **info** → style/brand override discipline (SPEC §C.3) |
