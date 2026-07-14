# Stress-Playbook — REPORT

Generative stress-test page for the **Remote** brand: *The Global Hiring Playbook*, an
11-section resource lead-gen page. Every section exercises a catalog device that
`event-genlaunch` (bento, pricing tiers, logo wall, signup form, banded CTA) did **not**.
Composition was hand-authored (`composition.v1`), rendered deterministically via
`brand_pipeline/compose_from_composition.py`, and gated with `onbrand_check.py --composition`
plus `slop_audit.mjs`.

The page renders clean end-to-end: real brand assets, Bossa display type, on-scale radii and
rhythm, one accent, 0 unresolved slot markers in the HTML. The gate failures that remain are
**all traced to shared chrome or gate/renderer contradictions** — documented below as
weaknesses, which was the point of the exercise.

---

## 1. Sections and the unique device each exercises

| # | id | archetype / pattern | Unique device stressed (not in event-genlaunch) | Result |
|---|----|---------------------|--------------------------------------------------|--------|
| 0 | `pb-hero` | split · `hero-inset-noise-panel` | Split hero w/ inset art panel, meta fact line, dual CTA, media counterweight | ✅ clean |
| 1 | `pb-stats` | stack · generic flow (no pattern stamp) | `stats` useCase → **falls back to generic flow**; stat values render as eyebrow-size text | ⚠️ W4, W5 |
| 2 | `pb-statement` | interlock | Editorial statement w/ offset media; heading between eyebrow and late body | ⚠️ W6, W9 |
| 3 | `pb-chapters` | cards · `features-card-grid-navy-media` | 3-col chapter card grid, per-card eyebrow + product-UI media well, explicit `grid.columns` | ✅ clean |
| 4 | `pb-process` | split · `feature-accordion-deep-accent` | Deep-accent (maroon) accordion w/ per-step `rowMedia` swap in navy well | ⚠️ W8 |
| 5 | `pb-compare` | split · info-band (stamped wrong) | `comparison` useCase — **no table renderer**; faked via ruled label/text rows in a panel | ⚠️ W4, W5, W6 |
| 6 | `pb-banner` | stack · `cta-inline-banner` | Compact inset-glow banner, question-form heading, single CTA — no form variant | ✅ clean |
| 7 | `pb-stories` | cards · `testimonial-card-row` | Edge-cut testimonial carousel (3rd card bleeds off-viewport by design), per-card logo pin | ⚠️ W7 (worked around) |
| 8 | `pb-badges` | stack · `badge-award-strip` | Award badge strip + 3 rating groups (G2/Trustpilot/Capterra) + outline CTA | ✅ clean |
| 9 | `pb-faq` | stack · faq knobs (no pattern stamp) | FAQ accordion, `exclusive:false` + `activeSurface: surface/inverse` (navy active card) | ✅ clean |
| 10 | `pb-form` | stack · `cta-closing-noise` | Resource form on closing noise band: 2-col fields, `tel` kind, select, help text, consent checkbox | ⚠️ W12 (textarea coerced) |

Device coverage vs `event-genlaunch`: split art-panel hero, stats flow, interlock statement,
navy-media card grid, deep-accent accordion + media swap, comparison rows, inline glow banner,
edge-cut carousel, badge/rating strips, non-exclusive navy FAQ, tel/textarea form — **11 new
devices**, zero pattern overlap with the event page (which used homepage hero, bento,
tiers, logo wall, banded CTA, basic signup form).

---

## 2. Gate results

### `onbrand_check.py --composition` (HARD invariants) — `onbrand-report.md` / `.json`

| Block | Result |
|---|---|
| neverDo (3 rules) | **PASS** |
| Fidelity vs source (surface, Bossa, assets) | **PASS** |
| Slop checklist (8 checks) | **PASS** |
| Composition invariants | **FAIL — 2 of 14**, both in shared chrome, not the composition |

Invariant detail: 12/14 pass — `single-accent`, `primitive-only`, `rhythm`, `data-composition`,
`slot-resolution` (0 markers), `decoration-salience`, `occlusion`, `band-attribution`,
`alignment-resolution`, `media-registration`, `interaction-contrast` (78 hover pairs, worst
4.91:1 ≥ 4.5 floor), `logo-wall-integrity`.

Failing:

- `text-contrast` — 2/197 elements: **both in the shared `page-banner` utility banner chrome**
  (`#ffffff` on effective `#91a0b0` = 2.69:1). See **W1**.
- `token-provenance` — 4 raw literals, **all in shared navbar chrome CSS** (`.cs-nav-util-link`,
  `.cs-nav-lang-item`): `18px`, `2px`, `rgba(0,0,0,0.05)`; one flagged as matching a HubSpot
  token value. See **W2**.

Both fail on `event-genlaunch` too if re-gated today — they're chrome regressions, not
composition drift. Per the concurrency fence I did not touch shared code.

### `slop_audit.mjs` — 10 flags @1440px, same 10 @1180px

All ten are **AS-23** ("content image without placeholder backing") firing on `"art"`-tagged
contained images (UI collages, globe illustration, panel snippet). This is a
**gate-vs-renderer contradiction** (see **W3**), not a composition defect: the renderer
*deliberately* strips the hatch backing for art-tagged images.

---

## 3. Design-system weaknesses found (primary product)

### W1 — Utility banner fails WCAG contrast: chrome extraction loses compositing context
- **Symptom:** `page-banner` white text/CTA on `rgba(51,79,111,0.5)` composites to
  `#91a0b0` over the light page → 2.69:1 (< 4.5). Fails `text-contrast` on every composed page.
- **Files:** `runs/remote/brand/brand.yaml` (`navbar.utilityBanner.bg` stores the
  semi-transparent color), `brand_pipeline/compose_page.py` (renders the banner standalone over
  `surface/primary`), extraction via `src/screenshot_to_template/browser_chrome_extractor.py`.
- **Suspected cause:** on the live site the banner sits over a dark hero, so 50 %-alpha navy is
  fine. The extractor captured the raw `rgba` without resolving the effective composited color
  or recording the backdrop dependency; the composer then re-hosts it on a light surface.
- **Fix direction:** extraction should store the *effective* composited color (or backdrop
  constraint) for chrome surfaces, not the raw alpha value.

### W2 — Navbar chrome CSS emits raw literals that fail `token-provenance`
- **Symptom:** `.cs-nav-util-link{font-size:18px}`, `.cs-nav-lang-item{font-size:18px}`,
  `.cs-nav-lang-item{border-radius:2px}`, `.cs-nav-lang-item:hover{background:rgba(0,0,0,0.05)}`
  — none trace to a Remote token; the hover wash literally matches a **HubSpot** token value
  (foreign-brand cross-contamination flag).
- **Files:** chrome CSS emitted by `brand_pipeline/compose_page.py`; token index built by
  `brand_pipeline/tokens_css.py`.
- **Suspected cause:** navbar chrome styles are hardcoded strings, written before the
  provenance gate existed, and were never migrated to token references or allowlisted.

### W3 — AS-23 slop rule contradicts the `c-image--art` renderer contract
- **Symptom:** all 10 slop flags are art-tagged contained images with no
  `repeating-linear-gradient` hatch behind them.
- **Files:** `brand_pipeline/component_render.py` (`render_image` sets `background:none` on
  `c-image--art`, deliberately, so transparent-PNG collages don't show a hatch through their
  alpha); `brand_pipeline/slop_audit.mjs` (AS-23 requires hatch backing on *every* content
  image); `brand_pipeline/spec/anti-ai-slop.md`.
- **Suspected cause:** the art-mode exemption was added to the renderer but AS-23 was never
  updated to skip `c-image--art`. Any page using art-tagged assets can never pass the audit.
  (`event-genlaunch` passed only because its collage wasn't tagged "art" and rendered `cover`.)

### W4 — Contracted primitives with no renderer: `stat` and `table`
- **Symptom:** `kit/agent/contracts/primitives.yaml` + `blocks.yaml` define `stat`,
  `stat-block`, `table`, but `compose_from_composition.py` / `compose_section.py` have no
  composer for them. `pb-stats` falls to generic flow — stat *values* ("170+", "$0") render as
  tiny uppercase eyebrows above paragraphs (see `shots/sec-1-pb-stats.png`), inverted hierarchy.
  `pb-compare` had to fake a comparison table with label/text ruled rows.
- **Files:** `brand_pipeline/compose_from_composition.py` (`_slot_to_mapping`, useCase routing),
  `brand_pipeline/compose_section.py` (`ARCHETYPE_COMPOSERS`).
- **Suspected cause:** contracts vocabulary was authored ahead of renderer coverage; there is no
  gate that fails when a contract has no renderer, so the gap is silent.

### W5 — Generic-flow and info-band headings default to display size (multiple H1-scale heads)
- **Symptom:** any generic-flow section heading without an explicit `level` renders display
  size; `compose_info_band` hardcodes its intro heading to display. `pb-stats` / `pb-badges`
  needed manual `"level":"h2"` in copy; `pb-compare`'s heading cannot be demoted at all.
- **Files:** `brand_pipeline/compose_from_composition.py` (`_inline_props` level default),
  `brand_pipeline/compose_section.py` (`compose_info_band`).
- **Suspected cause:** defaults were tuned for hero-led single-section renders; composed
  multi-section pages need a "one display heading per page" rule or positional demotion.

### W6 — Retrieval matcher misattributes patterns (`hero-inset-noise-panel` stamped on non-heroes)
- **Symptom:** `pb-statement` (interlock) and `pb-compare` (comparison split) both carry
  `data-pattern="hero-inset-noise-panel"` in the render.
- **Files:** pattern retrieval in `brand_pipeline/compose_from_composition.py`;
  `runs/remote/brand/layout-library.yaml`.
- **Suspected cause:** the layout library has no interlock or comparison patterns, and the
  nearest-neighbour matcher has no distance floor — it stamps the closest hero pattern instead
  of "no match". Pollutes provenance stamps and `data-composition` audits. Related: `pb-stats`
  and `pb-faq` get **no** stamp at all (inconsistent stamping paths).

### W7 — Card composer injects default media into quote cards
- **Symptom:** first render of `pb-stories` showed random assets (`bg-noise-top-2x.webp`,
  `panel-infrastructure-ui-snippet.webp`) inside testimonial cards' media wells.
- **Files:** `brand_pipeline/compose_section.py` (`compose_features_cards` default-media fill).
- **Suspected cause:** the card composer assumes every card wants a media well and backfills
  from the brand asset pool; quote/testimonial cards need an opt-out. **Worked around** by
  pinning explicit `asset` (company logo SVGs) per module in `composition.json`.

### W8 — Split-accordion composer silently drops the section `action` slot
- **Symptom:** `pb-process` declares an `action` link ("Get the playbook"); rendered sec-4
  contains zero instances — verified by scoping the search to the section markup.
- **Files:** `brand_pipeline/compose_section.py` (feature-accordion path of the split composer).
- **Suspected cause:** the accordion branch consumes only intro + rows + media slots; the
  section-level action is never mapped, and no unresolved-slot marker is emitted (silent loss —
  worse than a visible failure).

### W9 — Interlock composer overrides authored alt text
- **Symptom:** `pb-statement` media alt in `composition.json` was replaced by a default
  brand alt in the render.
- **Files:** `brand_pipeline/compose_section.py` (interlock copy resolution; `_asset_src` path).
- **Suspected cause:** interlock resolves media by asset name against brand defaults and never
  reads the slot's `asset.alt`.

### W10 — No stats-band pattern in the layout library
- **Symptom:** `stats` useCase exists in the schema and `stat-block` in contracts, but
  `layout-library.yaml` has no stats pattern, so retrieval can't seed one (feeds W4/W6).
- **Files:** `runs/remote/brand/layout-library.yaml`; extraction/curation pipeline that builds it.
- **Suspected cause:** the source site's stats bands weren't captured as patterns during
  extraction/curation.

### W11 — CLI parity counter reports phantom unresolved slots
- **Symptom:** `compose_from_composition.py` prints `unresolved: 2` for this page while the
  rendered HTML contains **0** unresolved-slot markers and `onbrand_check` `slot-resolution`
  passes.
- **Files:** `brand_pipeline/compose_from_composition.py` (parity accounting around list-copy
  slots in generic-flow rows, `feature-item` contracts).
- **Suspected cause:** the counter counts slots that resolve through the list-copy path as
  unmatched because they don't map to a shared renderer 1:1. Misleading diagnostics.

### W12 — Form schema coerces `textarea` to a single-line input
- **Symptom:** `pb-form`'s "Your biggest hiring question" declared `kind:"textarea"`; render
  emits `<input type="text">` (line 3022 of `index.html`).
- **Files:** `brand_pipeline/compose_from_composition.py` (`_form_fields_stamp`),
  `brand_pipeline/component_render.py` (form field renderer).
- **Suspected cause:** field-kind whitelist maps unknown kinds to `text` silently; no multiline
  control exists in the vocabulary. (`tel` worked correctly, including placeholder.)

---

## 4. Artifacts

All inside `runs/remote/brand/compose/stress-playbook/`:

| File | What |
|---|---|
| `PLAN.md` | Concept + 11-section plan w/ device mapping |
| `copy-brief.md` | Hand-authored on-voice copy (all headlines/body/CTAs/microcopy) |
| `composition.json` | Hand-authored `composition.v1` (11 sections, knobs, treatments) |
| `index.html` | Rendered page (deterministic render, no LLM in the render path) |
| `tokens.manifest.json` | Token provenance manifest from the render |
| `onbrand-report.md` / `.json` | Fidelity gate output (final run) |
| `assets/` | Brand assets copied by the composer |
| `changes.md` | Lane change log |

Render command used:

```
./venv/bin/python brand_pipeline/compose_from_composition.py \
  runs/remote/brand/compose/stress-playbook/composition.json \
  --brand runs/remote/brand/brand.yaml \
  -o runs/remote/brand/compose/stress-playbook
./venv/bin/python brand_pipeline/onbrand_check.py \
  runs/remote/brand/brand.yaml \
  runs/remote/brand/compose/stress-playbook \
  --layout navbar --composition --report onbrand-report.md
node brand_pipeline/slop_audit.mjs runs/remote/brand/compose/stress-playbook/index.html
```

## 5. Screenshot index (`shots/`, 1440px, reduced-motion)

| File | Shows |
|---|---|
| `full-page-1440.png` | Entire page |
| `sec-0-pb-hero.png` | Split art-panel hero + meta line + dual CTA |
| `sec-1-pb-stats.png` | **W4/W5 evidence** — stats as eyebrow text, display H-scale heading |
| `sec-2-pb-statement.png` | Interlock statement + globe illustration |
| `sec-3-pb-chapters.png` | 3-col chapter cards, navy media wells |
| `sec-4-pb-process.png` | Deep-accent accordion + per-step media (note: **no action link** — W8) |
| `sec-5-pb-compare.png` | Comparison via ruled rows (**no table renderer** — W4) |
| `sec-6-pb-banner.png` | Inline glow banner |
| `sec-7-pb-stories.png` | Edge-cut testimonial carousel w/ pinned logos |
| `sec-8-pb-badges.png` | Badge strip + rating groups |
| `sec-9-pb-faq.png` | Navy active-card FAQ (non-exclusive) |
| `sec-10-pb-form.png` | Closing noise-band form (`tel` ok, `textarea` coerced — W12) |

`shots/shoot_sections.mjs` is the capture script (Playwright, `reducedMotion: reduce`,
full-page render then per-section clips).

---

## 6. Resolution (system-level fix pass, 2026-07-10)

All twelve weaknesses were resolved in shared code — no composition edits, no
section-specific variables, every fix palette-agnostic per the evidence-first doctrine.
Regression locks: `brand_pipeline/tests/test_stress_playbook_weaknesses.py` (44 tests).
New anti-slop rules: **AS-51** (heading-scale inflation below the hero, W5),
**AS-52** (phantom media in attributed/quote modules, W7), **AS-53** (silent slot
drops, W8) in `brand_pipeline/spec/anti-ai-slop.md`.

| W | Status | Fix (system-level) | Files | Tests |
|---|--------|--------------------|-------|-------|
| W1 | **fixed** (fid15 band-aid removed) | Backdrop-aware chrome paint: the extractor composites an alpha `backgroundColor` over its live ancestors and records `bgEffective`; the bridge prefers it as the brand fact (`utilityBanner.bg = rgb(36,50,66)`) keeping the raw declaration as `bgRaw` provenance. The fid15 measured-pair **exemption for the chrome banner is deleted** — the banner now passes the same WCAG floor as everything else (13.13:1). | `src/screenshot_to_template/browser_chrome_extractor.py`, `tools/bridge_chrome_to_brand.py`, `brand_pipeline/onbrand_check.py`, `runs/remote/brand/brand.yaml` | `BannerBackdropTest` (4) |
| W2 | **superseded-by-fid15, finished here** | fid15 already covered `18px`/`2px` with `provenance: structural` comments and made the hover wash measured-only — `token-provenance` passes. The one remaining warning (`.cs-mega-link-desc` transition `0.3s`) now carries its provenance comment (measured `megaPanel.motion.description` duration, structural fallback). | `brand_pipeline/component_render.py` | gate-verified (`token-provenance` PASS, 0 warnings) |
| W3 | **fixed** | `slop_audit.mjs` AS-23 exempts exactly the classes the renderer stamps for the deliberate art contract (`.c-image--art`, `.c-acc-media--contain`) — the renderer's tag decision is the single shared law. AS-23 rule prose gains a **Scope** paragraph documenting the exemption. | `brand_pipeline/slop_audit.mjs`, `brand_pipeline/spec/anti-ai-slop.md` | `SlopAuditArtExemptionTest` |
| W4 | **fixed** | Real renderers for the contracted kinds: `render_stat` (value on the brand's measured h2 register via `--c-stat-size, --c-h2-size` chain + muted body-register label; `metric` alias) and `render_table` (semantic `<table>`, caption/columns/rows, `.c-rows` hairline discipline; dict-rows supported). Registered in `PRIMITIVE_RENDERERS`/`BLOCK_RENDERERS`; adapter folds `value/prefix/suffix/columns/rows`; repeatable stat slots expand to per-metric stat contracts grouped for banding; generic flow bands consecutive stats into one `cs-stat-band` grid row. | `brand_pipeline/component_render.py`, `brand_pipeline/compose_section.py`, `brand_pipeline/compose_from_composition.py` | `StatRendererTest` (5), `TableRendererTest` (4), `StatAdapterAndBandingTest` (4) |
| W5 | **fixed** + AS-51 | Heading-level demotion below the hero: a NON-hero section's heading/header slot that declares no `level` demotes to the brand's measured section tier (`section_heading_level` → h2 for ladder-bearing brands; ladderless brands keep the display degrade). Authored `copy.level` always wins. `_split_copy` carries `headingLevel`; `compose_info_band`'s band heading honors it. | `brand_pipeline/compose_from_composition.py`, `brand_pipeline/compose_section.py` | `HeadingDemotionTest` (6) |
| W6 | **fixed** | Retrieval honesty: `infer_use_case` resolves the DECLARED `section.useCase` first (canonical passthrough, semantic keyword mapping), and an unknown section belongs to **no** bucket (`""`) instead of defaulting to `hero` — `score_pattern`'s use-case gate then fails every candidate → honest miss. Retrieval outcome is a visible stamp: `data-pattern-match="ref|reuse|adapt|miss"` on every section wrapper + a MISS advisory comment. | `brand_pipeline/layout_library.py`, `brand_pipeline/compose_section.py`, `brand_pipeline/compose_page.py`, `brand_pipeline/generate_composition.py` | `InferUseCaseTest` (6), `RetrievalStampTest` |
| W7 | **fixed** + AS-52 | Quote/testimonial modules (person attribution: name/role/avatar) never inherit the defaultArt backfill — only an explicitly bound asset renders; an asset-less quote card composes media-less (no empty figure). Stamped `cs-module--quote` for audit traceability. Non-quote cards keep the backfill byte-identically. (The lane's pinned-logo workaround in `composition.json` still renders — explicit assets are unaffected.) | `brand_pipeline/compose_section.py` | `QuoteCardMediaTest` (3) |
| W8 | **fixed** + AS-53 | The split-accordion renders the authored section action as its list-column foot (`cs-acc-foot`, arrow-link register, left-anchored per the split grammar) when no bound action slot already renders — never a silent drop. `sec-4` now shows "Get the playbook →" below the steps. | `brand_pipeline/compose_section.py` | `AccordionActionSlotTest` (4) |
| W9 | **fixed** | `_interlock_copy` reads the slot's own `asset.alt`; authored alt wins, brand-default alt only when absent. `sec-2` now emits "Globe illustration with orbiting Remote product-UI chips". | `brand_pipeline/compose_from_composition.py` | `InterlockAltTest` (2) |
| W10 | **by-design (no fabrication)** | remote.com's homepage evidence shows **no stats band** — authoring a `layout-library.yaml` pattern would invent brand evidence. The W4 stat renderer + generic-flow banding IS the system fix: any composition's `stats` section renders correctly with no pattern, and the retrieval miss is now visibly stamped (W6). If future extraction captures a real stats band, the pattern lands via the normal evidence path. | — | covered by W4/W6 tests |
| W11 | **fixed** | The CLI parity counter now counts `<!-- unresolved slot` markers in the **emitted page** instead of side-re-rendering slots per layout (which counted fragments the bespoke composers never place). `unresolved: 0` now matches the gate's slot-resolution invariant. | `brand_pipeline/compose_from_composition.py` | `UnresolvedCounterTest` |
| W12 | **fixed** | `textarea` is a real form vocabulary member: `_FORM_FIELD_KINDS` accepts it and `_signup_field_html` renders a real `<textarea class="cs-input cs-input--multiline">` on the same brand input-anatomy chain (border/radius/bg/focus tokens), `rows="4"` structural, vertical-only resize. | `brand_pipeline/compose_from_composition.py`, `brand_pipeline/compose_section.py` | `TextareaFieldTest` (3) |

### Post-fix gate results (this lane, re-rendered from `composition.json`)

| Gate | Before | After |
|---|---|---|
| `onbrand_check --composition` | FAIL 2/14 invariants (`text-contrast` banner 2.69:1, `token-provenance` 4 chrome literals) → fid15 exempted the banner | **OVERALL PASS** — `text-contrast` PASS with the banner exemption **removed** (banner now 13.13:1; remaining exemptions are the fid14 measured link-blue pairs), `token-provenance` PASS (28 allowlisted, 0 warnings) |
| `slop_audit.mjs` | 10× AS-23 flags @1440 + @1180 | **PASS @1440 + @1180** (0 flags) |
| CLI parity | `unresolved: 2` (phantom) | `unresolved: 0` (matches emitted HTML) |

Side benefit: the composed homepage's 7 pre-existing AS-23 blind-spot flags (documented
fid11) are gone for the same W3 reason — homepage slop audit now **PASS @1440 + @1180**.

Post-fix visual evidence (all shots re-taken after the fix pass, same 1440px
reduced-motion method): `sec-1-pb-stats.png` (stat band at the h2 register, section-tier
heading), `sec-5-pb-compare.png` (section-tier heading), `sec-4-pb-process.png` (accordion
foot action link), `sec-7-pb-stories.png` (text-first quote cards), `sec-10-pb-form.png`
(real multiline textarea), `page-banner-page-banner.png` (legible composited banner),
`full-page-1440.png`.

Cross-lane verification: composed homepage onbrand **PASS** + slop **PASS**, event
onbrand **PASS** + slop **PASS @1440+@1180**, replica gate **0.949** (4 punch entries,
unchanged), spec book regenerated, validator **PASS** (0 errors, known C5 warn, fid13
C18 note), suite **592 passed** (548 + 44 new locks).

---

## 7. FID16 visual-composition closure (2026-07-10)

The final visual review found six composition issues beyond W1–W12. They are
resolved at the adapter/composer/fact-schema layers; `index.html` was regenerated
from `composition.json`, never edited.

1. **`pb-statement`: fixed.** Rebound from `interlock` to the ordinary
   `media-split` archetype. The complete caption/heading/support/action stack is
   the left grid child and the landscape globe is the right child. At 1440 the
   centered container is 1169.27px and tracks are 560.63/560.64px; the globe
   computes `object-fit: contain`.
2. **Chapter grid: verified.** Computed column gap is 32px. All three cards are
   591.78px high; CTA y positions are identical, with minimum body→CTA seams
   32/59.91/32px. Product-UI collages compute `cover` and fill the full-bleed
   media wells.
3. **Media treatment: fixed as facts.** `assets-tagged.json`
   `mediaTreatmentRules` resolve generic asset kind + slot role: transparent
   illustration → contain; product UI/product graphic in card media → cover;
   product UI in bounded accordion media → contain. `asset_render_mode` no
   longer reads filename or brand vocabulary.
4. **Comparison container: verified.** Intro and split obey the same centered
   1169.27px content law.
5. **Comparison header: fixed.** The adapter stamps `standaloneStack`; Remote's
   captured context grammar resolves `data-align="centered"` and computed
   `text-align:center`, independent of the two-column content beneath.
6. **Comparison rows: fixed.** Rows render through the semantic `<table>`
   component with one 144px label column and 336.64px value column inside the
   560.64px panel. All label x starts match; all value x starts match; separators
   belong to rows; below 767px cells stack.

The advanced interlock is also hardened under new **AS-58**: explicit evidence,
landscape media, canonical caption/statement/media slots, and no unsupported
foot cluster are required. A failed precondition degrades to `media-split`.
Qualified interlocks now use a 5/7 CSS grid; float/clear/drop arithmetic is gone.

Verification: full suite **721 tests OK**; stress spacing strict **0 hard fails**; all-five-lane interaction
strict **0 required fails**; homepage/sol/event/stress onbrand **PASS**; affected
slop gates **PASS @1440+1180**; replica **0.949**. The full cross-lane spacing
sweep additionally reported five pre-existing non-stress hard cells (three
homepage audit-classification/legacy-hero cells and two sol generic-flow seam
double-classifications); stress, event, and replica remained at zero hard.

FID16 proofs (1440px, reduced motion):

- `runs/remote/brand/shots/fid16-statement-split.png`
- `runs/remote/brand/shots/fid16-chapter-cards.png`
- `runs/remote/brand/shots/fid16-comparison.png`
