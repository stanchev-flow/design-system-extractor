# changes — compose/ai-product-launch (hubspot-v3)

## Hero fix: overlap + oversize (2026-07-22) — HELD FOR REVIEW, not committed

The generated hero had **misaligned (overlapping) text** and was **too large**. Root cause
classification: **(c) both** — a bad composition structure AND two shared-renderer defects.
An end-to-end regeneration attempt (current pipeline, bounded Anthropic call, no SDK
retries) REPRODUCED the same `overlay` / `hero-product-canvas-panel` / left-anchor hero and
regressed further (h1 demoted to a caption, 3 dropped copy strings, on-brand gate FAIL), so
the frozen curated `composition.json` was restored and the fix was made at the
archetype/renderer level (deterministic re-render inherits it + the held font/card fixes).

### Root cause
- **Overlap ("misaligned"):** the authored hero copy slots (eyebrow/heading/subheading)
  each declared a `colStart`; `compose_overlay` emitted each as an INDEPENDENT
  absolutely-positioned `cs-ov-placed` at the SAME `top: calc(6*baseline)` → they piled on
  top of each other, while the CTA group centered separately via `cs-ov-onmedia` (split
  alignment).
- **Oversize ("too large"):** the generation path never consumed the measured hero-height
  fact, so the full-bleed canvas fell back to the inflated `min(90svh, 54rem)` default
  (measured band @1440 = **1088px** vs the source's measured **772px**).

### Fix (generic, fact-gated, brand/palette-agnostic — files:lines)
1. `brand_pipeline/compose_section.py` `compose_overlay` — co-column front text slots are
   GROUPED into ONE flowing `cs-ov-placed--stack` per column (reading order preserved), the
   co-anchored CTA group folds into that stack, and a full-bleed hero's left-edge column
   insets to the content-container gutter (`_OV_BLEED_LEAD_INSET`, honoring the archetype's
   `containment: content-container`). A lone single-slot column stays a plain `cs-ov-placed`
   (byte-identical). New `SCAFFOLD_OVERLAY_STACK_CSS` (flex column + left-aligned folded
   CTAs + a narrow-viewport rule that keeps the stack over the fixed-height photo) ships
   ONLY via a `compose_page.build_page` gate (`"cs-ov-placed--stack" in blocks`), so every
   stack-less page — **all replicas** — is byte-identical.
2. `brand_pipeline/responsive_facts.py` + `compose_from_composition.py` — the hero family is
   SPLIT: its geometry-neutral HEIGHT mechanic (`heightRule` + `navOffset` →
   `calc(100dvh - var(--c-hero-nav-offset))`) and its hero-SCOPED heading-shrink ladder now
   cross over to generation (consumed by the existing `component_render.hero_responsive_css`);
   only the absolute primary-button box stays generation-excluded. `composition_to_doc` now
   carries `useCase` onto the composed layout (set in the SHARED `adapt_brand_section` so
   the replica-direct and catalog lanes stay parity-identical) so the fact merge can find
   the hero layout. `fact_consumption_audit.py` exclusion keys updated to match.

### Result (measured hero band, `fix-shots/gen-hero-{before,after}@{1440,375}.png`)
- @1440: **1088px → 772px** (exactly the source's measured `viewport-minus-nav`).
- @375: copy stack now sits over the photo (48px measured mobile h1 via the shrink ladder),
  no overflow; counterweight card steps aside.
- Copy renders as ONE left-anchored column (eyebrow → heading → subheading → CTAs), no
  overlap, gutter-inset. See `fix-shots/gen-hero-before-after@{1440,375}.png`.

### Verification
- C1–C28 on hubspot-v3 / v2 / remote / woodwave-v2: **0 errors** (advisory warnings only).
- Replica byte-identity: v3 + woodwave-v2 BYTE-IDENTICAL; v2 + remote differ ONLY by the
  pre-existing uncommitted held font/card fixes (0 hero/overlay/useCase-related lines).
- `brand_pipeline/tests/`: **2042 passed, 0 failed** (added
  `test_overlay_hero_alignment.py` ×7; updated `test_fact_consumption_audit.py`). Root
  `tests/`: only the 3 known pre-existing failures (relume ×2, runtime-defaults) — no new.
- New regression tests pin: grouped stack (no piled layers), folded CTA alignment,
  content-container inset, measured-height consumption, and the byte-safe CSS gate.

---


## Proof-section + bookend defect batch (2026-07-22, follow-up)

Re-rendered deterministically from the frozen `composition.json` after the shared-renderer
defect batch (see `runs/hubspot-v3/brand/changes.md` for the full 6-defect table). The one
defect that lands on THIS generated page is **D2 — dark bookend surface**: the hero (`sec-0`)
and closing CTA (`sec-7`) resolved the coarse `inverse` intent to the generic
`surface/inverse` (#1f1f1f) instead of the brand's measured dark bookend
`surfaceGrammar.bookend` = `surface/inverse-teal` (#002b28). Fixed in
`compose_from_composition.adapt_brand_section` (fact-gated bookend re-role); the closing
`sec-8` footer bookend correctly stays `#1f1f1f`. Light sections were already measured cream
`#fcfcfa` (D3 not reproduced here). Re-render byte-identical before the fix (page was NOT
stale — the defect was genuine). No commit/push (held for review).

---


GENERATION-PATH fidelity repair. The earlier lane worked AROUND missing generation
consumers (dropped tabs, split stats out, flagged silent drops as "pre-existing").
This pass fixes each defect SYSTEMICALLY in the shared generation path (generic,
brand-agnostic), regenerates the page deterministically from the frozen
`composition.json`, and verifies. No commit/push (held for review). The v3 REPLICA and
the v2/remote baselines stay BYTE-IDENTICAL (all shared-renderer changes are fact-gated
so only a composition that DECLARES the new anatomy renders it).

## Per-defect: root cause → fix → resolved

1. **Mega-nav had no background (transparent panel over hero).**
   - Root cause: the generation doc builder (`compose_from_composition.composition_to_doc`)
     loaded `brand.yaml` directly and never merged the Phase-2 `responsive-facts.yaml`
     the replica gets via `compose_page.load_doc`. So `nav_mega_css` never saw
     `responsive.nav.panelSurface.background` and left the measured-transparent outer
     wrapper (`rgba(0,0,0,0)`).
   - Fix: merge the measured CHROME responsive facts (`nav` + `buttons` + footer grid)
     onto the composed doc in `composition_to_doc`. `.cs-mega` now paints `#ffffff`.
   - Resolved: **yes** (open-dropdown screenshot shows a solid white panel).

2. **No tabs (tabbed-testimonial degraded to a flat quote).**
   - Root cause: the `tabs` contract had NO generation consumer — `_split_copy` never
     surfaced panel/label copy, so `compose_info_band`'s tab branch never fired even
     though `stamp_pattern_devices` stamps `_tabs` from the seeded pattern.
   - Fix: `_split_copy` now extracts a `tabs`/`tab-panels` slot's panels + labels;
     `compose_info_band` composes the real WAI-ARIA tab device (`_compose_tab_split` +
     `_IX_TABS_JS`). The composition's `testimonial` section was restored to the faithful
     source `tabbed-testimonial-with-stats` (3 real case panels, per-panel stats).
     Wireframe planner (`_testimonial_plan`), `composition_lint._VISUAL_CONTRACTS`, and
     `section_wireframe._slot_has_visual` now recognise the tabbed testimonial as ONE
     complete testimonial with a visual anchor (AS-70/71/76 pass by RENDERING).
   - Resolved: **yes** (Enterprise / Mid-Sized / Small Business tab rail + swapping
     photo/quote/attribution/stat pair).

3. **Missing text (silent slot drop on the generation path).**
   - Root cause: three declared strings never rendered — the split translator dropped a
     distinct `subheading` slot, mis-bound a testimonial `attribution` as the `body`
     (shadowing the quote), and the overlay proof-card read only its first copy field.
   - Fix: `_split_copy` captures a distinct subheading + a real attribution (quote no
     longer shadowed); `compose_info_band` renders subheading + quote + attribution;
     `_ov_render_text` renders a multi-field card's full claim + caption. Added a LOUD
     `lint_declared_copy` (writes `copy-lint.json`, shouts on stderr) — the recurring
     silent-drop detector. `copy-lint.json`: **0 misses**.
   - Resolved: **yes** (product-education subheading, testimonial quotes, hero
     utility-card line all render).

4. **Icons too small (spot icons at nav-mark size).**
   - Root cause / status: AS-80 coercion already keeps icon/mark-kind assets at MARK
     height in their icon role (never a card media well), and feature-card marks ride the
     card spot size (`.cs-module-media--mark` 2.25rem / measured icon-slot size), not the
     nav logo (28px). This composition's feature cards bind 640×640 agent PHOTOS as lead
     media (correct). Not reproduced as a visible defect here; the sizing path is
     verified + pinned (`test_spot_icon_coerced_to_mark_never_media_well`). AS-80 intact.
   - Resolved: **verified-correct** (no tiny icons on the regenerated page).

5. **Heading too large (section applied display/hero tier).**
   - Root cause / status: the below-hero heading demotion (`adapt_brand_section` →
     `section_heading_level`) demotes a non-hero section heading to the measured section
     tier even when it declares `sizeClass: display`. Verified: only the hero renders
     `--display` (h1); every interior section renders `--h2` (40px). Pinned by
     `test_non_hero_display_heading_demotes_to_section_tier`.
   - Resolved: **yes** (no oversized section headings).

6. **Accordion pushes the page.**
   - Root cause / status: the generation accordion consumers (FAQ `is_faq` →
     `compose_faq_accordion`; the split inset-emphasis device) use native `<details>`
     and are COLLAPSED-by-default (`_faq_stamp` sets no open index by default) — native
     details never JS-mis-compute height or push layout. This page declares no accordion.
     Not reproduced; verified-correct + pinned (`AccordionCollapsedByDefault`).
   - Resolved: **verified-correct** (no accordion overflow).

7. **Nav did not collapse at 375 on generated pages.**
   - Root cause: same as #1 — `responsive.nav.collapse` was never merged onto the
     composed doc, so `nav_collapse_css` emitted nothing (burger count 0).
   - Fix: the chrome-fact merge (see #1) now feeds the collapse breakpoint.
   - Resolved: **yes** — 375 nav `scrollWidth` 375 (was overflowing), burger renders,
     document `scrollWidth` 700→395 (residual is the pre-existing edge-cut card track,
     scoped out-of-scope in the v3 manifest — not the nav).

8. **`spacing_audit` crashed v3-wide (mediaScale `cover|contain` string).**
   - Root cause: `load_brand_facts` called `.get("gap")` on `slot.mediaScale` assuming a
     dict; the v3 layout-library declares it as the string `cover`/`contain`.
   - Fix: guard so only a dict `mediaScale` is mined for a strip gap.
   - Resolved: **yes** — the spacing gate now RUNS (see below).

## Deliberate type-register exclusion (why this did NOT regress AS-16)
The Phase-2 sidecar's `headings.lineHeights` (28px) and `hero` height are measured
against the SOURCE's own heading REGISTER; forcing the absolute 28px line-height onto a
composed page's 40px h2 crashed the lines together (AS-16 text-intersects-image on the
customer-proof heading). The generation merge takes ONLY geometry-neutral CHROME facts
(nav + buttons + footer grid) and deliberately EXCLUDES `hero`/`headings`.

## Gate battery (`run_battery.py`)
| gate | before | after |
|---|---|---|
| onbrand `--composition` (+anatomy AS-81) | PASS | **PASS** |
| slop (AS-68..81) | PASS | **PASS** |
| interaction | PASS | **PASS** |
| spacing | **BLOCKED (crash)** | **RUNS** — 2 `split.column-gap` wrong-step drifts (~90px vs measured 24/64) that ALSO fail on the held REPLICA baseline (brand-wide split-gutter mechanic; fixing it would alter the replica → out of scope). Not a regression, not one of the 8 defects. |
| signature / voice / section_rules / conversion | PASS | **PASS** |
| media-binding + mark-legality | PASS | **PASS** |
| anatomy-presence (AS-81, incl. tab-controls + stat-items) | PASS | **PASS** |

## Baselines (byte-identical / held)
- v3 replica **0.9241** (≥0.90), v2 **0.9556**, remote **0.9509** — all three replica
  `index.html` re-render BYTE-IDENTICAL after every shared-code change.

## Tests
- `brand_pipeline/tests/test_generation_path_fixes.py` — 16 new tests (nav chrome facts,
  tabs consumer, silent-copy binding + lint, type-tier demotion, spacing mediaScale,
  wireframe tabbed-testimonial, section-rules tab-stats, accordion collapse, icon role).
- Fixed `test_pass2_ab_findings.SplitCopyBinding::test_role_keyword_lookup_still_wins`
  (adjusted subheading extraction so a lone lede stays the body).
- Full suite: **1977 passed, 3 failed** — all 3 failures PRE-EXISTING on clean HEAD
  (relume prompt-guidance ×2, runtime model-defaults); **zero new failures**.

## Screenshots + Studio
- 1440: `shots/ai-product-launch-1440.png` · 375: `shots/ai-product-launch-375.png`
- Studio: `http://localhost:1500/runs/hubspot-v3/brand/compose/ai-product-launch/index.html`

## Files changed (shared, fact-gated)
`brand_pipeline/spacing_audit.py`, `compose_from_composition.py`, `compose_section.py`,
`section_wireframe.py`, `composition_lint.py`, `section_rules_audit.py`; lane
`composition.json` (faithful tabbed testimonial); new test file. No prompt defaults
changed.
