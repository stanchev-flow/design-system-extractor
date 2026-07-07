# HubSpot token-layer validation — decisive E2E retest (2026-07-03)

Worker: hubspot-validation. Scope: regenerate the HubSpot `signup-launch` page through the
LIVE tokenized pipeline (post token-layer batch, `experiments/token-layer-impl/REPORT.md`),
gate with `--composition` (provenance HARD), deliver visual verdict + blocker disposition.
Prior state under test: the 2026-07-02 page the user rejected as *"completely off brand —
WoodWave brand with HubSpot colors."*

## 0. Verdict (one paragraph)

**The token layer works; the composers are now the off-brand surface.** Every visual
*value* on the new page traces to HubSpot's `brand.yaml` — palette, surfaces, type tiers,
case, tracking, motion, radius scale, hairlines — and the old failure classes (WoodWave
literal hexes, hardcoded uppercase, universal darken-hover, WoodWave motion timings) are
gone from the emitted CSS entirely. The gate is still RED (correctly): 3 residual
provenance errors from **dormant** scaffold fallbacks (2 foreign-brand callouts naming
WoodWave values), plus two structural failures that are *composer/adapter* gaps, not token
gaps — no composer ever emits a `.c-button` even though the brand demands filled CTAs and
the fully-tokenized button CSS is sitting in the page unused, and the features-cards asset
path is malformed by an adapter bug. The page no longer reads as "WoodWave with HubSpot
colors"; it reads as "HubSpot tokens on WoodWave-shaped scaffolds." That is real progress
and a correctly-diagnosing red gate.

## 1. Generation outcome

- Runner: `run_validation.py` (this dir) — same live path as the prior harness
  (`generate_composition.py`: structured Anthropic call → schema validate → neverDo +
  off-grid prefilters → `compose_from_composition` render → `--composition` gate → ≤2
  repairs), style `corporate-saas-clean`, brand `runs/hubspot/brand/brand.yaml`
  (UNTOUCHED, sha `96d08de4…`), gate layout context `footer` (real HubSpot layout id;
  B8 workaround, same as prior harness).
- Output (new dir, additive fence): `runs/hubspot/brand/compose/signup-launch-tokenized/`.
- **No hard-fail token gaps.** Layer-1 generation succeeded: **213 tokens**, required set
  complete. `disabledDevices = [ghost-watermark, footer-display-links, aspect-palette]` —
  all legitimate (optional-token policy; aspectPalette intrinsic-only is BINDING per
  `DECISIONS.md` #5). `tokens.manifest.json` stamps `brand_yaml_sha256 = 96d08de4…` —
  exactly the snapshot hash, provenance chain closed.
- Model composed 7 sections (hero `stack-fullbleed`, features `cards`, logos / testimonial
  / cta / footer as `stack`, + form) with plausible HubSpot content (DoorDash/eBay/Reddit
  logo strip, testimonial quote, filled-button CTA slots).
- Result: `ok=false`, 3 attempts (1 + 2 repairs), 334s wall. Repairs could not converge
  because all three remaining failure classes are **deterministic renderer/adapter
  behavior**, invisible to the LLM (it *did* declare `contract: button` slots; the
  composers dropped them).

## 2. Gate scorecard (`--composition`, provenance HARD)

Overall: **FAIL** — 5 failing lines, 24 passing. Full report:
`runs/hubspot/brand/compose/signup-launch-tokenized/onbrand-report.md`.

| # | Check | Detail | Class |
|---|-------|--------|-------|
| 1 | `never-typographic-primary` | filled primary CTA present=False | Composer gap: composition declared `button` slots; gallery-hero/conversion/cards composers render arrow-links + form submits, never `render_button` (page CSS has zero `.c-button` elements — while the fully tokenized `.c-button` rules ARE in the page, unused) |
| 2 | Brand assets present | 3 module srcs malformed `assets/{'src': 'assets/…webp'}` | Adapter bug: `_sanitize_assets` dict-ifies bare-string module assets; `compose_features_cards` interpolates the dict into `src` |
| 3 | All brand image assets present | same 3 | same |
| 4 | Rounding matches radius scale | off-scale=`['var(--button-radius)']` | Checker false-positive: slop radius check doesn't resolve var-refs; resolved value 0.5rem IS on-scale (`tokens.radius.button`) |
| 5 | **token-provenance** | 3 errors, 11 allowlisted | Residual scaffold fallbacks (below) |

### Provenance detail (the decisive check)

3 errors, **2 distinct foreign-brand callouts, both naming WoodWave** — requirement was
zero, NOT met, but the blast radius collapsed from "the entire renderer vocabulary"
(pre-batch) to **three dormant declarations in two scaffold selectors**:

- `.c-foot-sitemap-link{font-size}`: raw `3rem` — clamp endpoint fallback in the footer
  sitemap scaffold (`var(--c-foot-link-size, clamp(...3rem))`); `--c-foot-link-size` is
  unresolved for HubSpot (no `footer-display-links` device). Callout: *matches WoodWave
  Gallery `--size-display-hero@mobile`*. **Dormant** — no `.c-foot-sitemap-link` element
  on this page (the composed footer routed elsewhere); the literal ships only as CSS text.
- `.cs-ov-panel .c-heading--display{font-size}` and `.cs-ov-behind …`: raw `5rem`
  fallbacks in overlay scaffold CSS. Callout: *matches WoodWave Gallery
  `--chrome-foot-link-size`*. **Dormant** — no overlay archetype on this page.

These are exactly the `var(--x, LITERAL)` class the batch eliminated elsewhere (AS-24);
these two selectors were missed. Fix shape (queued, NOT applied per fences): conditional
emission or token-ref fallback, same treatment `.c-button`/`.c-field` got. Zero
duration/easing warnings. Also for the record: page-level trace shows the eyebrow-tier
`allowlisted` entries are structural (em-padding, z-index) — none are brand values.

### Pre/post gate comparison (same brief, same style, same brand)

| Check | 2026-07-02 (gen5) | Now |
|-------|-------------------|-----|
| No off-palette hex | **FAIL** (`#1f1a14`, `#f7efe6` — WoodWave literals in CSS) | **PASS** (zero off-palette) |
| never-allcaps-headings | FAIL (hardcoded uppercase tiers) | **PASS** (`--case-*` = `none` from `scale.*.case: sentence`) |
| token-provenance | (gate didn't exist) | FAIL: 3 dormant-literal errors |
| never-typographic-primary | FAIL | FAIL (unchanged — composer gap) |
| assets present | FAIL (same dict-src malformation) | FAIL (unchanged — adapter gap) |
| text contrast | PASS | PASS (worst 4.85 = measured orange-on-inverse eyebrow) |

## 3. Visual verdict

Shots in `shots/`: `tokenized-full.png`, `tokenized-hero.png`, `tokenized-cta.png`,
`tokenized-footer-end.png`, per-section `sec-0..6.png` (captured with
`reduced_motion=reduce`; the page's scroll-reveal honors it — below-fold sections are
opacity-0 until IntersectionObserver fires, so naive full-page shots show blanks; that is
a screenshot artifact, not a page defect). References compared:
`experiments/hubspot-e2e/shots/real-top.png`, `real-footer.png`, `preview-after.png`
(rejected state), `preview-before.png` (real-asset compose preview).

### vs the rejected before-state (`preview-after.png`) — what the token batch visibly fixed

- **Case**: uppercase serif display tiers → sentence case everywhere
  (`--c-case-heading: var(--case-h2)` ← `scale.h2.case: sentence`). This was the single
  loudest "WoodWave" signal and it is gone.
- **Palette**: WoodWave cream/ink literals (`#f7efe6`, `#1f1a14`) → zero foreign hexes;
  page/panel/inverse surfaces are `#fcfcfa` / `#f8f5ee` / `#1f1f1f` ← `tokens.surfaces`.
- **Accent deployment**: orange now *renders* (hero eyebrow #ff4800, form focus ring,
  links) instead of appearing only in swatches.
- **Motion**: 150/200/300ms `ease-in-out` ← `voice.motionSpec` (computed
  `--c-motion-fast: 150ms`); reveal shift 16px ← `scrollReveal.translateY`. WoodWave's
  320/480/620ms + cubic-bezier are absent (one comment mention only).
- **Inputs**: boxed variant conditionally emitted (`input_shape(doc)='boxed'` ←
  `tokens.radius.input` presence) — the rejected state's WoodWave underline-input is gone.
- **No prohibition specimens**: the composed path renders no "avoid"-struck WoodWave
  button cards.

### Mechanical traceability (computed values → brand.yaml keys)

Sampled via Playwright (`computed-samples.json`):

| Computed (rendered page) | Traces to |
|---|---|
| Hero heading family `"HubSpot Serif"` | `--c-font-heading: var(--font-display-hero)` ← `tokens.type.families.display` |
| Heading `text-transform: none` | `--case-h2` ← `type.scale.h2.case: sentence` |
| Body `"HubSpot Sans"` 18px | `--font-body` ← `families.sans`; `--size-body-lg` ← `scale.body-lg.sizeRem: 1.125` |
| Eyebrow 14px / ls 0.56px (0.04em) / #ff4800 | `scale.eyebrow.sizeRem: 0.875`, `.letterSpacing: 0.04em`; `colors.brand/primary` |
| Section bgs rgb(252,252,250) / rgb(248,245,238) / rgb(31,31,31) | `surfaces.surface/primary·panel·inverse(-strong).bg` |
| `--radius: 1rem`, `--radius-button: 0.5rem` (root) | `spacing.radius-global`, `tokens.radius.button` |
| `.c-button` CSS chain bg #ff4800 → hover #c93700, pad 0.75rem 1.5rem, weight 500, radius .5rem | `buttons.primary.{bg,bgHover,padding,fontWeight,radius}` — **present and correct in CSS, zero elements use it** |
| Link hover on inverse `#f8f5ee` | `--chrome-link-hover` ← `footer.measured.linkHoverColor` (B12 data recovered manually) |
| Boxed field border 1px rgba(0,0,0,0.11) | `border/hairline-on-primary` (via `--c-hairline` fallback) |
| Motion vars 150/200/300ms ease-in-out | `voice.motionSpec.durations/easing` |

### Strongest remaining deltas vs the real site (`real-top.png` / `real-footer.png`)

1. **No filled orange CTA anywhere** — every primary action is a typographic arrow link.
   The real site's dominant conversion device is the filled orange button. Composer
   realization gap (B5's composer half), *not* a token gap — the tokenized button CSS is
   in the page, unused.
2. **Hero scale + face**: display renders at 172.8px (style poster clamp
   `clamp(9rem,12cqw,16rem)`, B3 — style structure not brand-overridable) vs real ~65px;
   face is `HubSpot Serif` w500 (scale-picker chose `display-02`) vs the measured hero
   tier `HubSpot Serif Page Header Human` w300 4.0625rem (B11 exact-role-first still
   missing). Both values are HubSpot-sourced (provenance-clean) but not the *hero* ones.
3. **Page shape monotony / content drop**: logos strip and testimonial quote sections were
   silently converted to near-identical signup forms (`stack` → `_cta_mapping()` fixed
   heading+form shape) — 4 "Start today / you@company.com / Start free" blocks on one
   page; the composed DoorDash/eBay/Reddit logo content and the quote never rendered.
4. **Broken feature-card images** (adapter dict-src bug) with hardcoded
   `alt="WoodWave editorial photography"` — a literal brand-string leak in
   `compose_features_cards` (content-level, so provenance's CSS scan can't see it).
5. **Footer grammar**: WoodWave's social slash-list bookend vs the real multi-column dark
   footer (B6); the model's composed footer links were also swallowed by the stack→form
   routing.

## 4. Blocker disposition — B1–B12 (`runs/hubspot/brand/REPORT.md` §6) + audit's 5

Note: `hardcode-audit.md` §7's cross-ref table renumbered the blockers; dispositions below
use the ORIGINAL B-numbers from the prior worker's REPORT (the task's cited source).

| # | Blocker (short) | Disposition | Proof / pointer |
|---|---|---|---|
| B1 | Component gallery has no style layer | **OPEN (harness wiring; out of token-batch scope)** | `render_components_preview.py:1122` still `inactive_context()`, no `--style` flag. Gallery's *token* sins fixed (RP-1 accent pinning, per-surface alias blocks, brand-agnostic specimen copy — impl REPORT) |
| B2 | `brand.baseStyle` consumed nowhere | **OPEN** | `rg baseStyle brand_pipeline/` → 0 hits; harnesses still pass `--style` explicitly |
| B3 | Style structure not brand-overridable (poster display scale) | **OPEN — KEPT BY DESIGN this batch (ST-1)** | `styles.py merge()` patches radius only; hero renders 172.8px from style clamp. The #1 visual delta on this page; needs the style-layer follow-up |
| B4 | Hardcoded uppercase + accent-on-dark pinning | **CLOSED** | Zero `text-transform: uppercase` declarations in emitted CSS; all case/tracking via `--case-*`/`--tracking-*` ← `scale.*.case/letterSpacing`; `never-allcaps` PASS; accent resolves per-surface via `component_vars` (hero eyebrow #ff4800 computed) |
| B5 | CTA/button realization (gallery prohibitions + composer arrow-links) | **HALF-CLOSED** | Token/CSS half CLOSED: `.c-button` fully token-driven incl. measured hover bg-swap (page CSS, traces `buttons.primary.*`), conditional on `cta_shape(doc)='filled'` ✓. Composer half **OPEN**: no composer emits `.c-button`; `contract: button` slots dropped → `never-typographic-primary` FAIL. **Top unresolved item** |
| B6 | Footer = WoodWave closing bookend | **OPEN** | Composed footer still social/slash grammar; sitemap tier alias (`--c-foot-link-size`) prepared but unresolved for HubSpot; its 3rem clamp fallback is provenance error #1 |
| B7 | Surface role names are WoodWave literals | **MITIGATED (data contract + fail-loud)** | Code still literal-keyed (`compose_page.py:415` `FOOTER_SURFACE`), but `_REQUIRED_SURFACES` hard-fails generation when roles are missing, and HubSpot's brand.yaml now carries the alias roles (prior worker's refresh). Schema-level rename still open |
| B8 | Gate default layout id is WoodWave's (`opening-bookend`) | **OPEN** | `generate_composition.py:763` default unchanged; harness must pass `layout="footer"` |
| B9 | Silent unresolved-token passthrough | **MITIGATED** | `color_value()` passthrough remains (`tokens_css.py:46`), but: required-token hard-fail at generation + `token-provenance` HARD downstream + the `or`-fallback trap sites (AS-02) deleted. Live risk now limited to optional-token typos |
| B10 | Two-tier radius (1rem global / .5rem buttons / .25rem inputs) | **CLOSED for button+card tiers; input tier gapped** | Layer-1 emits `--radius-global/-button/-input/-card/…`; `.c-button` consumes 0.5rem ✓, images/cards 1rem ✓. **`--c-input-radius` alias never emitted** → boxed field computed 16px ≠ measured 4px (new finding N5) |
| B11 | Display-role scale picker ignores requested role | **PARTIAL** | Data-side workaround holds (no 7rem inflation; display-01 out of scale). Exact-role-first still missing: `display-hero` → `display-02` (4.5rem/500) not measured hero tier (4.0625rem/300). Provenance-clean, fidelity-wrong |
| B12 | Chrome extractor misses @media-nested hover | **OPEN — extraction-side, explicitly deferred** | Impl REPORT: "hoverColor() @media recursion — deferred". Data recovered manually in brand.yaml; value flows (`--c-link-hover` = #f8f5ee on inverse scope). Extractor bug remains for future brands |
| A1 | Aspect fallback palette (CR-6) | **CLOSED + INTENTIONAL** | Interlock aspect fallback stripped (bare `var()`); HubSpot: `aspect-palette` disabled → intrinsic ratios, per DECISIONS #5 (binding). Cards' 16/10 / 4/3 inline ladder is composer-structural (noted N9, borderline) |
| A2 | Logo wordmark styling (CR-4) | **CLOSED** | `.c-logo` weight/tracking via `--c-logo-weight/-ls` token refs (impl REPORT + unit tests) |
| A3 | Unreachable `or`-fallbacks in compose_page (AS-02) | **CLOSED** | Fallback expressions deleted (CP-1); page aliases are bare var-refs (`--c-panel: var(--surface-surface-panel)` in output; CS-1 comment block in page CSS) |
| A4 | Ghost watermark ladder (CS-2) | **CLOSED + INTENTIONAL for HubSpot** | Ladder token-driven when tier exists; HubSpot has no ghost tier → device disabled (in manifest `disabledDevices`) — nothing rendered, no fallback literal |
| A5 | styles.py paper/ink placeholders (ST-1) | **OPEN BY DESIGN (documented discipline)** | Placeholders never reached output (brand supplies paper/ink); the style's *numeric structure* (poster clamp) did — that is B3, not a token leak |

**Counts (17 items = B1–B12 + A1–A5): 4 CLOSED (B4, A2, A3, A4) · 3 PARTIAL (B5 token-half closed / composer-half open; B10 button+card tiers closed / input alias gap; B11 inflation fixed / role-picker open) · 2 MITIGATED (B7, B9) · 2 INTENTIONAL per decisions (A1 aspectPalette intrinsic-only; A5 style-discipline by design) · 1 OPEN extraction-side (B12, explicitly deferred) · 5 OPEN pipeline-side, out of token-batch scope (B1, B2, B3, B6, B8).**
Standouts: **B5 composer half** (declared `button` slots must reach `render_button` when
`cta_shape='filled'`), **B3** (style poster scale overrides brand hero tier), and the
**adapter asset dict bug** (new, below) — those three account for every user-visible
"still off-brand" impression on this page.

## 5. New findings from this run (not in B1–B12 / audit)

- **N1 (blocker-class)**: `compose_from_composition._sanitize_assets` wraps bare-string
  module assets into dicts; `compose_features_cards` interpolates the dict →
  `src="assets/{'src': …}"` → 2 gate FAILs + broken images. Pre-existing (identical in
  gen5 logs), unfixed by token batch (out of its scope).
- **N2 (blocker-class)**: non-hero `stack` sections all route to `_cta_mapping()` (fixed
  heading+form) — logos/testimonial/footer-link content silently dropped; 4 near-identical
  signup forms on one page.
- **N3**: the 3 provenance literals (`.c-foot-sitemap-link` 3rem clamp; `.cs-ov-*` 5rem) —
  the AS-24 class, two selectors missed by the batch; both dormant on this page.
- **N4**: `.c-paragraph` has no `font-weight` property — HubSpot's body weight 300
  (`scale.body-lg.weight`) never consumed; renders 400.
- **N5**: `--c-input-radius/-border/-bg` aliases never emitted by `component_vars` —
  boxed field radius falls back to `--radius` (1rem ≠ measured 0.25rem), bg transparent
  (≠ measured white).
- **N6**: slop radius check counts `var(--button-radius)` as off-scale (doesn't resolve
  var-refs) — false-positive FAIL line; needs alias-aware resolution.
- **N7**: hardcoded `alt="WoodWave editorial photography"` default in
  `compose_section.py` (~1524) — content-level brand leak, invisible to CSS provenance.
- **N8**: `--size-display-hero` picks `display-02` over the exact `heroDisplay` tier
  (B11's remaining half, restated with this brand's numbers: 4.5rem/500 vs 4.0625rem/300).
- **N9**: features-cards aspect ladder (`16/10`, `4/3`) is a hardcoded composer default,
  emitted as inline styles (outside provenance scan). Borderline structural; flag for the
  aspect-device follow-up.

## 6. Studio lane

`http://localhost:1500` answers 200 (server relaunched persistently after the initial
nohup died with its parent shell). `/project/hubspot` lists the new lane:
**`v04 · 07-03 12:41 · Composed: signup-launch-tokenized`** alongside the prior worker's
v03. Red-gate pages still land as lanes (Studio versions from output mtimes), so the lane
is inspectable side-by-side with the rejected state.

## 7. Fences + conflict protocol

- Fences respected: zero modifications under pre-existing `runs/hubspot/**` /
  `experiments/hubspot-e2e/**`; pipeline output only in NEW
  `runs/hubspot/brand/compose/signup-launch-tokenized/`; all artifacts in
  `experiments/hubspot-validation/`; no `brand_pipeline/**`/`styles/**`/`tools/**` edits;
  no hand-authored HTML/JSON, no post-processing, no gate loosening; no commits/pushes.
- Conflict protocol: start snapshot (`input-hashes.txt`, 12:30) vs finish re-check
  (13:05): `brand.yaml` sha `96d08de4…` unchanged, `REPORT.md` sha `19c4578f…` unchanged,
  all 11 tracked `brand_pipeline/*.py` mtimes unchanged. **No conflicts.** The generated
  page's `tokens.manifest.json` stamps the same `brand.yaml` sha — full provenance chain.
- Tests/regate: **no wiring bug was fixed, so no regate was required.** Unit suite was run
  once pre-flight as a sanity baseline: 108/108 OK.
