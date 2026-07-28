# hubspot-v4 — capture-prompt upgrades → VISIBLE results

Baseline commit: `30f52c3` (landed the Archaeologist capture-prompt/schema upgrades but
nothing consumed the new facts and no brand was re-extracted with them).

Goal: make the new fact families **captured** for hubspot AND **consumed** by the
renderers so they produce visible results — fact-gated, brand-agnostic, no hardcoded
brand values, no section-specific token names. Existing brands (v2/v3/remote/woodwave-v2)
stay byte-identical (absent fact ⇒ current behavior).

## Lane setup
- Rebuilt `runs/hubspot-v4/` from the committed `hubspot-v3` lane (same source capture
  bundle / evidence). `brand.yaml`, `evidence/`, `assets/`, and all sidecars copied so the
  v3 base facts are preserved verbatim; the new fact families are layered on top.

## PART 1 — capture (DONE)
Deterministic, evidence-scoped derivation — the SAME discipline as
`brand_pipeline/responsive_facts.py` (evidence → generic provenance-tagged fact block →
reviewable sidecar → fact-gated consumer → AS-83 audit). No LLM call (so no oversized-
evidence timeout); every value traces to a measured CSS rule / token.

- **New tool:** `tools/extract/capture_interaction_facts.py` — derives the new families
  from `evidence/css-rules.json` + `dom-sections.json` + `color-roles.json` (var chains
  resolved to literals). Brand-agnostic regexes (role words / closed control vocab), never
  a source class name.
- **Capture artifact:** `runs/hubspot-v4/brand/interaction-facts.yaml`.

Captured families (sample values):
- `blocks.carousel.carousel`: `transitionMs: 300`, `easing: ease-in-out`,
  `slidesPerView: 3`, `controls: [arrows, dots]`, `dots: true`, `autoplay: true`,
  `loop: true`. `intervalMs` **omitted** — the JS autoplay timer is not exposed by the
  static capture (`motion-audit.jsTimingNotes` is empty); never guessed.
- `interactionStates` (button/link/tab/input): e.g. button
  `focus {outline: 2px solid #7aa485}`, `active {background: rgba(0,0,0,0.47)}`,
  `disabled {color: rgba(0,0,0,0.2)}`.
- `navbar.sticky`: `behavior: scroll-shrink`, `toRegister {bg: #ffffff,
  shadow: 0 2px 4px rgba(33,51,67,.12)}`, `transitionMs: 300`, `easing: ease-in-out`.
- `navbar.mobile`: `trigger {kind: hamburger}`, `drawerSurface {bg: #ffffff, side: full}`,
  `drawerAnim {durationMs: 300, easing: ease-in-out}`, `closeAffordance {kind: x-glyph}`.
- `tokens.shadow`: `sticky-nav: 0 2px 4px rgba(33,51,67,.12)`,
  `raised: 0 1px 24px rgba(33,51,67,.12)`, `overlay: 0 8px 28px rgba(0,0,0,.28)`.
- `tokens.zIndex`: `sticky-nav: 95`, `dropdown: 99`, `overlay: 999`, `modal: 2`.
- `footer.localeSelector`: `kind: dropdown`, 6 language options (日本語 / Deutsch / English
  / Español / Português / Français) with locale hrefs (the observed locale-link cluster;
  DOM census filed it under chrome.header — materialized at the footer locale slot).

Validation: `run_brand_extraction.py --brand hubspot-v4 --stages validate` → **PASS**
(0 errors, 11 warnings — same warning set as the v3 base).

## PART 2 — consumption (DONE)
`brand_pipeline/responsive_facts.py`:
- `load_interaction_facts` + `merge_interaction_facts` merge the sidecar into the canonical
  brand-schema paths AND stash it under a PRIVATE `doc._interactionFacts` namespace that
  the consumers read from. Reading the private namespace (not the canonical paths) is what
  guarantees byte-identical output for a brand that authored a same-named key but has no
  sidecar. Called from the single `merge_brand_facts` path (replica + generation + AS-83).

`brand_pipeline/component_render.py` — fact-gated consumers (each emits a
`/* … (fact-gated: <path>) … */` marker; "" without the fact):
- `navbar_sticky_css` + `navbar_sticky_script` — `#page-nav { position: sticky }` + a
  `.is-scrolled` scrolled register (measured bg + shadow), transitioned at the measured
  duration/easing; JS toggles `.is-scrolled` on scroll.
- `navbar_mobile_drawer_css` — the burger drawer adopts the measured surface (bg) and
  slides in with the measured duration/easing (reuses the existing burger toggle).
- `carousel_timing_css` — measured slide transition duration/easing as CSS custom props on
  the carousel/slider tracks + reveals a captured dots affordance. No fake autoplay timer.
- `interaction_states_css` — measured focus-visible / pressed / disabled registers for
  `.c-button` + content links (hover already handled by the button/link families).
- `elevation_tokens_css` — `tokens.shadow` → `--c-shadow-<role>`, `tokens.zIndex` →
  `--c-z-<role>`; the `sticky-nav` roles map onto `#page-nav`.
- `footer_locale_selector_html` + `FOOTER_LOCALE_CSS` — a native `<details>` locale control
  in the footer listing the measured language options.

`brand_pipeline/compose_page.py` — wires the consumers into `build_page` css_parts +
scripts + the footer section (all empty-safe so fact-less brands stay byte-identical).

`brand_pipeline/fact_consumption_audit.py` — `_INTERACTION_FAMILIES` adds one AS-83 family
per new fact so a captured-but-unconsumed interaction fact FAILS loud.

### Consumer sites (file:line)
- `component_render.py` navbar_sticky_css ~L802, navbar_mobile_drawer_css, carousel_timing_css,
  interaction_states_css, elevation_tokens_css, footer_locale_selector_html, navbar_sticky_script.
- `responsive_facts.py` merge_interaction_facts (+ call inside merge_brand_facts).
- `compose_page.py` footer locale injection + css_parts block + `ix_script` append.
- `fact_consumption_audit.py` `_INTERACTION_FAMILIES` + audit loop.

## Renders + gate
- Replica: `compose_replica.py runs/hubspot-v4/brand/brand.yaml` → **overall score 0.921**
  (baseline 0.922; −0.001, negligible). Viewport health 1440/1920/960 = 1.0, 375 = 0.893
  (pre-existing 20px `cs-edgecut` overflow, unchanged).
- Generated page: `compose/ai-product-launch` (composed from the v3 composition against the
  v4 brand). AS-83 target=generation → 12 consumed / **0 unconsumed**.
- AS-83 target=replica → 26 consumed / **0 unconsumed** (all 7 new families CONSUMED).
- Demonstration screenshots: `brand/compose/replica/interaction-demo/`
  - `m375-drawer-open.png` — mobile drawer OPEN (measured white surface + full nav links).
  - `d1440-nav-scrolled.png` — sticky nav with the measured scrolled shadow.
  - `d1440-footer-locale.png` — footer locale selector open with the 6 language options.

## Verification
- `pytest brand_pipeline/tests` → **1989 passed**, 0 failures (incl. new
  `test_interaction_facts.py`, 14 tests).
- `pytest tests` → 81 passed, **3 failed = the known pre-existing failures only**
  (relume_recipe_catalog ×2, runtime_defaults ×1). No new failures.
- Byte-identical: v3 + remote replica HTML byte-identical vs committed; woodwave-v2 +
  hubspot-v2 byte-identical **with-vs-without** these changes (their committed artifacts are
  stale vs the baseline commit's own compose changes, unrelated to this work).
- `viewer.html` regenerated via the venv.

## Facts that could NOT be captured/consumed
- Carousel `intervalMs` (JS autoplay dwell) — not exposed by the static capture
  (`jsTimingNotes` empty). Captured everything observable (transition/easing/controls/
  dots/autoplay-present/loop/slidesPerView); the consumer therefore emits NO fake timer.
- `pauseOnHover` — not observable statically; omitted (never guessed).
- Interaction `states` are consumed as CSS (focus/pressed/disabled) but are only visible
  under interaction (keyboard focus / press / disabled), not in a static full-page shot.
