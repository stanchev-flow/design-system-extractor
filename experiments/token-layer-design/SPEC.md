# SPEC — Per-brand generated token layer with provenance gating

**Status:** implementation-ready batch spec (paper only — no code edited by this worker).
**Depends on:** `hardcode-audit.md` (same folder) for the cluster IDs referenced here (CR-*, CS-*, CP-*, RP-*, ST-*).
**Prime directive:** a composed page for brand X may not contain a visual value that is not
traceable to brand X's `brand.yaml` (or an allowlisted structural constant). WoodWave keeps
rendering byte-similar because its values now arrive *through* tokens instead of *being* the code.

---

## A. Token schema — three-layer indirection adapted to this pipeline

The key discovery of the audit: **the pipeline already has layers 2 and 3.** The `--c-*`
namespace (`component_vars`/`root_vars` emit it, every `c-*`/`cs-*` rule consumes it,
per-surface re-scoping already works) is the semantic alias layer, and component CSS is the
usage layer. What's missing is a generated layer 1 and *closure* (no literals surviving in
layers 2–3). `export_kit.build_tokens_css()` already generates a flat layer-1 file for kits
(`--color-*`, `--surface-*`, `--space-*`, `--font-*`, `--size-*`, `--weight-*`,
`--leading-*`, `--aspect-*`, `--size-nav`) — the schema below adopts and extends that naming
rather than inventing a parallel `--ds-*` dialect.

```
LAYER 1  measured brand values     — generated from brand.yaml, flat, one var per measured fact
         --color-accent-highlight: #edd580;         --weight-display-hero: 500;
         --space-section-padding-dark: 6.25rem;     --motion-fast: 320ms;
LAYER 2  semantic role aliases     — the existing --c-* contract, generated per surface scope
         --c-accent: var(--color-accent-highlight); --c-button-weight: var(--weight-button, var(--weight-control-text));
         (re-scoped per surface: .cs-panel { --c-link-hover: var(--color-text-on-primary); })
LAYER 3  renderer usage            — component/scaffold CSS references ONLY var(--c-*) / var(--space-*) etc.
         .c-button { font-weight: var(--c-button-weight); }   ← never `700`
```

### A.1 Layer-1 namespaces (flat — Webflow-mappable)

| namespace | source in brand.yaml | notes |
|---|---|---|
| `--color-<role>` | `tokens.colors.*` (slugified role) | includes rgba values |
| `--surface-<role>` | `tokens.surfaces.*.bg` | |
| `--font-/-size-/-weight-/-leading-/-case-/-tracking-<tier>` | `tokens.type.*` (WoodWave shape) or `tokens.type.scale.*` + `families` (HubSpot shape) — generator normalizes both | **new:** `--case-*` (`text-transform` value; `sentence`→`none`) and `--tracking-*` (letterSpacing), closing CR-1 |
| `--space-<step>` | `tokens.spacing.*` | |
| `--radius-<role>` | `tokens.radius.*` (HubSpot) or `tokens.spacing.radius-global` (WoodWave) | normalized: `--radius-global` always exists; `--radius-button/-card/-input/-image/-pill` when measured |
| `--shadow-<level>` | `tokens.shadow.*` | absent ⇒ not emitted (flat brands) |
| `--aspect-<name>` | `tokens.imagery.aspectPalette.*` | |
| `--motion-fast/-base/-slow`, `--motion-ease`, `--motion-shift` | `voice.motionSpec.durations/easing/scrollReveal` | closes CR-3 |
| `--button-<prop>` (`-bg/-fg/-bg-hover/-border/-pad/-radius/-weight/-size`) | `buttons.primary.*` (+ `-secondary-*`, `-tertiary-*` when measured) | closes CR-2 |
| `--chrome-nav-*`, `--chrome-foot-*` | `navbar.measured.*`, `footer.measured.*` (px→rem) | extends the existing `--size-nav` precedent |

### A.2 brand.yaml → layer-1 mapping table (keys actually present, both brands)

| brand.yaml key | WoodWave value | HubSpot value | layer-1 token |
|---|---|---|---|
| `tokens.colors.accent/highlight` | `#edd580` | `#ff4800` | `--color-accent-highlight` |
| `tokens.colors.surface/primary` … `inverse-strong` | cream/browns | `#fcfcfa`/`#1f1f1f` | `--color-surface-*` / `--surface-*` |
| `tokens.colors.text/on-primary`, `on-inverse`, `*-muted` | ✓ | ✓ (added 2026-07-02 refresh) | `--color-text-on-*` |
| `tokens.colors.text/ghost-on-primary` | `rgba(31,26,20,0.06)` | `rgba(0,0,0,0.05)` | `--color-text-ghost-on-primary` |
| `tokens.colors.border/hairline-on-primary` (+`-on-inverse` HS) | ✓ | ✓ | `--color-border-hairline-on-*` |
| HS-only: `brand/primary-hover/-pressed`, `overlay/scrim`, `overlay/hover-wash(-inverse)`, `text/link-hover(-on-inverse)`, `accent/sage|lilac|pink`, `border/default|medium|strong|brand`, `action/primary-fg` | — | ✓ | `--color-<slug>` (interaction + accent families) |
| `tokens.type.<tier>` (WW: 10 tiers incl. `ghost-watermark`, `counter-display`, `footer-sitemap-link`) | ✓ | via `type.scale` (12 tiers incl. `display-02`, `h4`, `body-lg/-md/-sm`, `button-md/-lg`) | `--font/-size/-weight/-leading/-case/-tracking-<tier>` |
| `tokens.type.<tier>.sizeRem.{tablet,mobileL,mobile}` | ✓ | — (single rem) | responsive ladder `@media` blocks (kit generator already does this — reuse) |
| `tokens.spacing.*` | 7 steps | 13 steps | `--space-<step>` |
| `tokens.radius.*` | — (`radius-global: 0rem`) | 6 roles | `--radius-*` |
| `tokens.shadow.*` | — | `sm/card/lg` | `--shadow-*` |
| `tokens.imagery.aspectPalette` | 4 ratios | — (**extraction gap**, see Open Questions) | `--aspect-*` |
| `voice.motionSpec.durations` | 320/480/620ms | 150/200/300ms | `--motion-*` |
| `voice.motionSpec.easing.primary` | `cubic-bezier(.22,1,.36,1)` | `ease-in-out` | `--motion-ease` |
| `voice.motionSpec.link.mode` | color-shift-to-gold | underline-draw + arrow | structural flag (§C.3), not a token |
| `buttons.primary/.secondary/.tertiary` | — (typographic CTA brand) | full measured set | `--button-*`; absence ⇒ typographic-CTA structural variant (§C.3) |
| `navbar.measured.{bar,link,logo,contentMaxWidth}` | ✓ | ✓ | `--chrome-nav-*` |
| `footer.measured.{bg,link,heading,padding,grid}` | ✓ | ✓ | `--chrome-foot-*` |
| `heroTreatment` (HS-only) | — | scrim rgba(0,0,0,0.5), align center | `--color-overlay-scrim` + structural flags |
| `surfaceGrammar`, `primitives`, `neverDo`, `compositionRules` | ✓ | ✓ | **not tokens** — structure/laws (feed §C.3 flags and the gate) |

**Measured values with no token home (by design):** `primitives.button.use: never` /
`link.remapFrom: cta` (structural), `navbar.archetype/twoTier/sticky`, `footer.columns/social`
(chrome composition), `imageParallax.enabled` (motion structure), `recipePolicy`,
`targetMappings`, `provenanceIndex`. These are structure, not values — they select *which*
tokens/variants apply.

### A.3 Layer-2 aliases (the `--c-*` contract — generated, per-surface)

Layer 2 is emitted per render *scope* (page root + each section's surface + panel/card/band
sub-scopes), exactly where `root_vars`/`component_vars`/band scoping emit today. The change:
every right-hand side becomes `var(--layer-1-token)` (or a var of a var), **never a literal,
never a Python-interpolated hex.** Naming keeps the existing contract (`--c-ink`,
`--c-ink-muted`, `--c-accent`, `--c-hairline`, `--c-panel`, `--c-panel-ink`, `--c-ghost`,
`--c-motion-*`, `--c-eyebrow-ls`, …) and adds the audit's missing roles:
`--c-case-heading/-eyebrow/-control` (CR-1), `--c-button-*` (CR-2), `--c-input-*` (CR-5),
`--c-logo-*` (CR-4), `--c-foot-link-*` (CP-3), `--c-ghost-size` (CS-2, now
brand-derived), `--c-section-pad-x/-y`, `--c-module-gap`, `--c-stack-*` (CS-3),
`--c-aspect-*` (CR-6).

Surface-relationship names (`--c-link-hover` re-scoped per surface, incl. cards — AS-20;
`button-primary-on-inverse-strong`-style variant hooks) are legal; section/content names
(`heroAccent`, `ctaCardBackground`) remain forbidden, per repo token guidance.

### A.4 Webflow export note

Layer 1 is deliberately **flat values only** (no `calc()`, no nested `var()`), so each maps
1:1 to a Webflow native variable. Layer 2 is pure alias (`var(--x)`), which maps to Webflow
variable-references-variable. Fluid expressions (clamp ladders) live in layer 2/3 **as
structure**, with their endpoints as layer-1 vars — where Webflow can't express a clamp, the
export maps the layer-1 endpoints and picks the base value. The generator must precompute any
derived value (e.g. rgba-from-hex alpha ladder, px→rem chrome conversions) into layer-1
*static* values rather than emitting `calc()`/`color-mix()` chains.

---

## B. Generation — where tokens.css comes from

### B.1 Generator

New module **`brand_pipeline/tokens_css.py`** (new file — can land independently of the
anti-slop batch):

- `build_page_tokens(doc, style=None, *, fonts_rel="assets/fonts") -> TokensBundle` where
  `TokensBundle = {css: str, index: dict[token→resolved value], missing: list[str],
  manifest: dict}`.
- Normalizes the two brand.yaml type shapes (WoodWave per-tier dicts vs HubSpot
  `families`+`scale`), buttons, chrome, motion, radius/shadow/aspect per the §A.2 table.
- `manifest` = `{brand, brand_yaml_sha256, style_id, generator_version, generated_at,
  token_count}` — embedded as a CSS header comment **and** written as
  `tokens.manifest.json` next to the render (drift detection, §F).
- `export_kit.build_tokens_css()` becomes a thin wrapper over the same module (kit adds
  @font-face + `./fonts/` paths; page render points at its own assets). One generator, two
  emission targets — no drift between kit and page tokens.

### B.2 Invocation & opt-in

- `compose_page.py` calls the generator once per page render and inlines the result as the
  **first** `<style id="tokens">` block (before scaffold/component CSS). Single-section
  renders (`render_section.py`, `render_components_preview.py`) include the same block.
- **Opt-in is universal:** any brand with a `brand.yaml` gets a generated token block; there
  is no flag. A brand is "token-complete" when the generator reports `missing == []` for the
  **required set** (below); the E2E harness asserts token-completeness before composing.

### B.3 Fallback behavior — recommendation: **fail loud at generation, with a declared optional set**

- **Required tokens** (surfaces, text-on-*, hairlines, type tiers display/h1/h2/body/eyebrow/
  control, spacing scale, radius-global, motion trio): a missing source key **raises** at
  generation time with the exact brand.yaml path to fix (`tokens.colors.text/on-inverse
  missing — re-extract or author it`). No silent inheritance: tonight's `KeyError:
  'surface/inverse-strong'` (gen.log) is the fail-loud behavior we *want*, but moved to
  tokens-generation time with an actionable message instead of mid-render.
- **Optional tokens** (ghost tier, aspect palette, shadows, buttons.secondary/tertiary,
  counter/footer-sitemap display tiers): absence **disables the device** (the composer must
  not emit a ghost word for a brand with no ghost tier; must not emit shadows for a flat
  brand) — never substitute another brand's magnitude. The generator emits an explicit
  manifest list `disabledDevices: [ghost-watermark, …]` the composers read.
- **Why not inherit:** inheritance is exactly how WoodWave DNA leaked — a "reasonable
  default" is always *somebody's* brand. Fail-loud converts extraction gaps into visible,
  attributable work items (extraction worker's queue) instead of silent cross-brand bleed.
- Python-side `or "#F7EFE6"`-style fallbacks (CP-1, CS-1) are **deleted**, not re-pointed;
  layers 2–3 reference vars with **no literal fallback** so a missing var is visible
  (property drops to initial) *and* caught by the provenance gate + generator fail-loud
  before it ever ships. This also retires the AS-02 truthy-string trap sites.

---

## C. Renderer changes (reference-level; implementation worker executes)

### C.1 Cluster → token replacement table

| audit cluster | today | becomes |
|---|---|---|
| CR-1 uppercase ×10 | `text-transform: uppercase` | `text-transform: var(--c-case-heading|eyebrow|control)` per element family |
| CR-2 button | `font-weight:700; letter-spacing:0.01em; padding:0.8em 1.6em; font-size:max(1.17rem,…)` | `var(--c-button-weight/-ls/-pad/-size/-radius/-bg/-fg)`; hover = `--c-button-bg-hover` (bg swap) with brightness-filter only as the *typographic-CTA* variant's mechanism |
| CR-3 motion | `var(--c-motion-fast, 320ms)` etc. | `var(--c-motion-fast)` — fallback literals stripped; `_MOTION_DEFAULTS` deleted (generator fail-loud owns absence) |
| CR-4 logo | `font-weight:600; letter-spacing:0.08em; uppercase` | `var(--c-logo-weight/-ls/-case)`; image-logo branch reads `--chrome-nav-logo-w/-h` |
| CR-5 field | underline-only archetype | structural flag `input-shape` (§C.3) selecting underline vs boxed variant; boxed reads `--c-input-radius/-border/-bg` |
| CR-6 aspects | `var(--c-aspect-*, 3 / 2)` | `var(--c-aspect-*)` ← `--aspect-*`; brands without a palette: composer restricts to intrinsic ratios (device disabled) |
| CR-7/CP-1/CS-1 color fallbacks | `or "#F7EFE6"`, `var(--c-panel, #F7EFE6)` | Python fallbacks deleted; CSS fallbacks stripped to bare `var(--c-panel)` |
| CS-2 ghost scale | `clamp(6rem, 22cqw, 18rem)` ladder | `--c-ghost-size: clamp(calc(var(--size-ghost-watermark) * .35), 26cqw, var(--size-ghost-watermark))` — multipliers are structure, magnitude is brand; device disabled when tier absent |
| CS-3 rhythm | `padding: 4cqh 5cqw 8cqh`, `gap: 2.5rem`, … | `var(--c-section-pad-x/-y)` (per-surface: light/dark padding steps), `var(--c-module-gap)`, `var(--c-stack-sm/-md/-lg)`; clamp *endpoints* from `--space-*`, cq midpoints stay structural |
| CP-2 hero override | `max-width: 18ch; text-align: center` | measure → `--c-hero-measure` (brand `heroTreatment`/style structure); alignment already resolved by the in-flight AS-18 batch — override block reads the same resolution |
| CP-3 footer | Melodrama-scale sitemap links for all | `--c-foot-link-size/-family/-case/-weight` from `footer-sitemap-link` tier when present else `footer.measured.link` |
| RP-1 gallery | `--c-accent: var(--ink)`; `is_dark=False` | gallery consumes generated tokens.css + per-surface layer-2 scopes; specimen canvases render each surface role, not one hardcoded light canvas |
| ST-1 style numerics | dataclass literals | style keeps *stances/ratios*; any numeric that reaches emitted CSS must pass through a token or carry `provenance: style-structure` (§D.4) |

### C.2 What stays literal (allowlisted structural constants)

z-index ladder (CS-5), grid templates/breakpoints/resets (CS-6), focus-ring offsets,
`aspect-ratio: auto`, `1px` hairline *thickness* (thickness is structural; *color* is token),
occlusion geometry math, cq fluid midpoints. Each gets a one-line provenance comment at the
definition site: `/* provenance: structural — layering registration, brand-independent */`.

### C.3 Where a token is insufficient — structural variants (style flag + brand token combine)

Four devices differ in *kind*, not magnitude. Resolution order: brand structure law
(primitives/neverDo/buttons) > style soft-option default > style invariant.

| device | structural flag (from) | brand tokens consumed by each variant |
|---|---|---|
| primary CTA | `cta-shape: filled\|outline\|typographic` — `buttons.renderHint.useFilledButton` / `primitives.button.use: never` / style soft-option `primary-action` | filled: `--c-button-bg/-fg/-radius/-pad`; typographic: `--c-link-*` + arrow motion |
| input | `input-shape: underline\|boxed` — `neverDo.no-boxed-inputs` vs `tokens.radius.input` | underline: `--c-hairline`; boxed: `--c-input-radius/-border/-bg` |
| corner language | `radius stance` — existing soft-option machinery (`styles.py` + `detect_brand_overrides`) | `--radius-global/-card/-button/-input` |
| link interaction | `link-mode: color-shift\|underline-draw` — `voice.motionSpec.link.mode` | `--c-link-hover` (per surface), `--motion-*` |

This is the existing soft-option pattern (`onbrand_check.detect_brand_overrides`) extended
from 2 options (radius, primary-action) to a small closed enum — no new mechanism invented.

### C.4 Preview harness split (RP-2)

Gallery chrome (page header, spec labels, swatch grids) may keep literal styling under a
single `/* provenance: preview-chrome */` banner — it is never brand output. Everything
*inside* a specimen frame must resolve from the generated tokens.css. The gallery gains one
specimen row per surface role so interaction re-scoping (AS-20) is visually reviewable.

---

## D. Gate check design — `token-provenance`

### D.1 Hook point

New invariant row in `onbrand_check.check_composition()` (id `token-provenance`), joining
G8–G11 in section 5 of the report: **advisory WARN by default, HARD under `--composition`**
— identical gating to its siblings, so deterministic legacy pages never regress, and the
E2E/repair loop (which passes `--composition`) treats it as FAIL. Scorecard: standard
`invariants.checks["token-provenance"]` entry + a `details` payload listing violations.

### D.2 What it scans

The emitted HTML's `<style>` blocks (the same surface `extract_facts` already parses), minus
the generated `<style id="tokens">` block (layer 1 is the *source* of truth, not a
violation). For every declaration of a **visual property** (color/background/border*-color/
fill/stroke; font-size/-weight/letter-spacing/text-transform; border-radius; box-shadow;
padding/margin/gap/row-gap on section-level selectors; transition/animation durations +
easing; aspect-ratio) whose value contains a raw literal (`#hex`, `rgb[a]()`, bare
`px/rem/em/ms` number, named weight, `uppercase`, `cubic-bezier`) **not**:
1. equal (after normalization) to a value in the generated token index for the active brand, or
2. inside a declaration whose value is purely `var(...)` references, or
3. covered by a provenance allowlist comment (§D.4) —
it records a violation. Value→token matching uses the generator's `index` (§B.1) loaded from
`tokens.manifest.json`, so the checker never re-parses brand.yaml.

### D.3 Violation format (feeds `generate_composition._repair_note` via `_parse_gate_failures`)

One row per violation, detail string machine-stable:

```
| `token-provenance` | FAIL | .c-button{font-weight}: raw `700` — use var(--c-button-weight) (resolves to 500 for HubSpot); .cs-panel{background}: raw `#F7EFE6` — no HubSpot token resolves to this value; nearest surface token: --surface-surface-panel (#f8f5ee) [foreign-brand value: matches WoodWave --color-surface-panel] |
```

Rules: each item = `selector{property}: raw <value> — <suggestion>`. Suggestion tiers:
(a) exact-match token (`use var(--x)`), (b) nearest same-category token with resolved value
shown, (c) **foreign-brand callout** when the raw value exactly matches another run's token
index (that's a DNA leak smoking gun). The repair loop already forwards `(check_id, detail)`
pairs verbatim to the model, so suggestions are phrased as imperatives.

### D.4 Severity + allowlist

- **error (gates under `--composition`):** color, spacing-on-sections, radius, font-size/
  weight/case/tracking, shadow, aspect.
- **warning (reported, never gates):** durations, easing — until both live brands carry a
  complete motionSpec and the team flips them to error (single constant list in the checker).
- **Allowlist with provenance:** a CSS comment immediately preceding the declaration —
  `/* provenance: structural <short-id> — <why brand-independent> */` — suppresses the
  violation and increments an audited `allowlisted: N` count in the detail (so allowlist
  growth is visible in review). Only `structural` and `preview-chrome` provenance classes
  exist; there is deliberately **no** `brand-specific` escape hatch.

---

## E. Anti-slop registry entry — DRAFT (do not apply; registry owner lands it)

Proposed as **AS-24** (next free id after AS-23; renumber if the in-flight batch takes it).

> ## AS-24 — Brand DNA leak: raw visual values in shared renderers
>
> **Rule**: a shared renderer/composer may never emit a literal visual value (hex/rgba, px/
> rem magnitude, weight, case transform, radius, shadow, duration, easing, aspect) — every
> visual value resolves through the generated token layer (`tokens.css` from the ACTIVE
> brand's brand.yaml), or carries an explicit `provenance: structural` comment. A `var(--x,
> LITERAL)` fallback **is** a raw emission: the fallback is somebody's brand.
>
> **Why it happens**: renderers get built against the first brand that exercised them; its
> measured values feel like "the defaults" and calcify into the shared CSS. Every later brand
> then renders brand-one's typography/shape/rhythm with its own hues swapped in — plausible
> at a glance, off-brand everywhere.
>
> **Caught here**: the HubSpot E2E page (2026-07-02) rendered "WoodWave brand with HubSpot
> colors": uppercase editorial headings (`text-transform: uppercase` ×10 in
> component_render), WoodWave button weight/padding (`700` / `0.8em 1.6em`), WoodWave motion
> (`320/480/620ms cubic-bezier(.22,1,.36,1)` fallbacks), WoodWave panel surfaces
> (`var(--c-panel, #F7EFE6)`, `#1F1A14` inks, `rgba(31,26,20,.30)` hairlines) — while
> HubSpot's brand.yaml measured `sentence` case, weight 500 buttons `0.75rem 1.5rem`,
> `150/200/300ms ease-in-out`, `#f8f5ee` panels the whole time.
>
> **Composer discipline**: layers — measured brand values (generated `tokens.css`) →
> semantic `--c-*` aliases (generated per surface scope) → component CSS references ONLY
> vars. No literal fallbacks in `var()`. Missing required token = fail-loud at generation;
> missing optional token = the device is disabled, never substituted.
>
> **Gate check**: `onbrand_check.py` invariant `token-provenance` (advisory by default, HARD
> under `--composition`) — scans emitted CSS for raw visual values not traceable to the
> active brand's token index; each violation names the offending value AND the correct token
> (or flags a foreign-brand match); structural constants allowlist via
> `/* provenance: structural … */` comments.
>
> **Verify**: `rg -n "var\(--[a-z-]+,\s*[#0-9]" brand_pipeline/*.py` returns zero var-with-
> literal-fallback sites in renderer CSS; render the same composition for two brands and diff
> the emitted CSS — every diff line must be a token value, never a selector's literal.

(Optional companion note, same entry, not a new id: the preview gallery's light-canvas
`--c-accent: var(--ink)` pinning is the same shape in harness form — RP-1.)

---

## F. Staleness / drift sync — extension of what already exists

**Already in place (audited):** `taste_sync.py --check` drafts gate failures into
`signals.log` as PENDING lessons; `--import` pulls field kit learning; `--ratify` promotes
patterns; `--export-if-changed` re-exports the kit when canon changed. The kit
(`runs/*/brand/kit/SKILL.md` + `agent/tokens.css`) is regenerated wholesale from brand.yaml
on export — kit tokens can't drift *if* export runs, but nothing today tells you **which
downstream artifacts** reference stale values between exports, and composed pages/preview
galleries embed resolved values with no version stamp. `brand-designer-skill.md` §"Feed the
loop" already names `--export-if-changed` as the release step — the design below extends
that loop, it does not replace it.

**Extension (non-blocking report, no new namespace):**

1. Every generator emission embeds the manifest (§B.1): `brand_yaml_sha256` + generator
   version, as a header comment in tokens.css and `tokens.manifest.json` beside the render.
2. New `taste_sync.py --drift <brand>` (or standalone `tokens_drift.py` if taste_sync is
   contended): computes current `sha256(brand.yaml)` (+ per-style file hashes), then scans
   known artifact roots — `kit/agent/tokens.css`, `kit/SKILL.md`, `agent/layout-library.yaml`
   (patterns store size *classes*, so only flag ones carrying resolved values),
   `components-preview/index.html`, composed page dirs, `magic-trick.md` blessed wildcards
   (these embed rendered HTML) — for embedded manifests/hashes that mismatch.
3. Output: a table `artifact | embedded hash | current hash | verdict (FRESH/STALE/UNSTAMPED)`
   printed and appended to `signals.log` as an INFO line. **Exit 0 always** — drift is a
   to-regenerate list, not a failure; `--export-if-changed` remains the fix-action.
4. Style-file changes: style md files get hashed into the same manifest (structure affects
   emitted CSS), so a style edit flags composed pages as stale too.

---

## G. Test + verification plan

### G.1 Unit tests (new `tests/test_tokens_css.py`, `tests/test_token_provenance.py`)

- Generator, per fixture brand (woodwave + hubspot brand.yaml snapshots checked into
  `tests/fixtures/`): required set complete; both type shapes normalize to identical
  namespaces; motion trio correct (`320/480/620` vs `150/200/300`); buttons emitted for
  HubSpot, absent + `disabledDevices` for WoodWave typographic CTA; responsive ladder for
  WoodWave sizeRem dicts; **no literal in any layer-2 alias**; manifest hash stable across
  two runs (determinism); fail-loud raise on a brand.yaml with `text/on-inverse` deleted;
  Webflow-cleanliness: layer-1 values contain no `var(`/`calc(`.
- Provenance checker: HTML fixture with a planted `#F7EFE6` on `.cs-panel` for HubSpot →
  exactly one error naming the value, the nearest token, and the WoodWave foreign-brand
  match; `var(--c-x, 320ms)` fallback → duration **warning**; provenance-comment allowlist
  suppresses + counts; report row format parses through `_parse_gate_failures` round-trip.

### G.2 Fixture pages + phase0 regate

- Fixtures: the WoodWave matrix (existing composed pages / `render-*` dirs) + the HubSpot
  E2E composition (whatever `experiments/hubspot-e2e` settles on once the live worker lands).
- **phase0_regate expectation: zero PASS→FAIL.** Composition invariants stay advisory for
  deterministic pages (token-provenance follows G8–G11 gating), so legacy pages mechanically
  cannot regress OVERALL; the assertion to make explicit is: every previously-PASS neverDo/
  fidelity/slop row stays PASS.
- **WoodWave byte-similarity:** render the matrix before/after. Expected diffs are exactly:
  (1) the inserted `<style id="tokens">` block, (2) literal→`var()` rewrites whose *resolved*
  values are identical. Verify mechanically: dump resolved computed styles (the readability.py
  var-resolution path or a headless computed-style dump) and diff **resolved** values — must
  be empty; plus screenshot diff (existing shot tooling) with zero visual delta. Any
  intentional diff (e.g. a WoodWave value that was ITSELF mis-hardcoded and now corrects)
  gets documented in the batch changes.md before landing.

### G.3 HubSpot acceptance — the "off brand" verdict as mechanical checks

1. **Zero foreign values:** provenance scan of the emitted page reports zero errors; zero
   values matching the WoodWave token index (mechanical restatement of "WoodWave brand with
   HubSpot colors" → no WoodWave *anything*).
2. Headings/body render `text-transform: none`-equivalent (case from `type.scale`), serif
   display family from `families.display` — `never-allcaps-headings` + `no-serif-body` PASS.
3. Primary CTA is the filled variant: bg `#ff4800`, fg `#ffffff`, radius `0.5rem`, weight
   500, padding `0.75rem 1.5rem`, hover bg `#c93700` (interaction-contrast check green).
4. Radius/shadow resolve from `tokens.radius`/`tokens.shadow` (`never-zero-radius` PASS).
5. Motion durations 150/200/300ms + `ease-in-out` (no 320/480/620 anywhere).
6. Gate green end-to-end under `--composition` (all HARD invariants incl. token-provenance),
   and `results.json.ok == true` in the E2E harness.

---

## H. Sequencing

| chunk | contents | depends on | est. effort |
|---|---|---|---|
| 1 | `tokens_css.py` generator + manifest + unit tests (**new files only**) | nothing — can land during the anti-slop batch | 0.5–1 day |
| 2 | provenance checker as importable function + tests (new file; not yet wired to gate) | chunk 1 (token index) | 0.5 day |
| 3 | composer integration: compose_page/-section/component_render literal strips per §C.1, structural-variant flags §C.3, allowlist comments §C.2; wire `token-provenance` into `check_composition` | **anti-slop batch close** (composers/gate are contended) + chunks 1–2 | 1–2 days |
| 4 | WoodWave matrix regate + byte-similarity verification (§G.2) | chunk 3 | 0.5 day |
| 5 | preview harness re-plumb (RP-1/RP-2 split §C.4) + `render_section.py` legacy retrofit + export_kit unification (§B.1) | chunk 3 | 1 day |
| 6 | drift sync `--drift` (§F) + HubSpot E2E rerun to §G.3 acceptance | chunks 3–5 + extraction worker's asset fixes | 0.5 day |

Rollout: chunks 1–2 immediately (no contention); 3 is the batch head after anti-slop closes;
4 gates 5–6. Nothing here requires hand-authored HTML/JSON or post-processing repair — every
change is generator/renderer/gate-level.

---

## I. Feed into the queued per-brand "taste skill" consolidation (pointers only)

The article's tier structure maps onto artifacts this batch produces or firms up:
**foundations** = brand.yaml + the style layer (already exist); **tokens** = the generated
tokens.css + manifest (chunk 1 — becomes the tier-2 spec file the skill reads every
session); **components** = the `c-*` SSOT, which after §C.1 is *describable purely in token
terms* — the 8-section component template's "Uses" section falls out of each component's
`var(--c-*)` consumption list (mechanically greppable), and "Used-by" from the archetype
composers' component calls; **patterns** = `layout-library.yaml` + magic-trick blessed
wildcards, already cross-referenced by taste_sync. The provenance gate doubles as the
article's "audit script" tier-guard, and §F is its drift detector. The taste-skill batch
should therefore consume: `tokens.manifest.json` (session-load token truth), the per-
component token-consumption index (generate from the same scanner as §D.2), and the kit
SKILL.md operating loop unchanged. Do not spec further here.

---

## Open questions for the user

1. **Alias-layer naming:** keep the existing `--c-*` contract as layer 2 (this spec's
   recommendation — zero churn in component CSS) vs adopt the article's `--ds-*`/project-
   alias split verbatim (cleaner article-parity, large diff)?
2. **Fail-loud scope:** confirm generation-time hard-fail for required tokens (blocks a
   compose run on an extraction gap) vs render-with-visible-sentinel (page renders with
   obvious `MISSING` blocks, gate red). Spec recommends hard-fail; the E2E harness then
   surfaces extraction gaps before spending model tokens.
3. **Durations severity:** warning now → error once both live brands have full motionSpec
   (they do today) — flip immediately instead?
4. **`render_section.py` legacy path:** retrofit (chunk 5) or retire in favor of the
   composer path for single sections?
5. **Aspect palette for HubSpot:** extraction gap — should the extraction worker add
   `tokens.imagery.aspectPalette` to HubSpot's brand.yaml, or is aspect-restriction-to-
   intrinsic the intended behavior for photography-led brands?
6. **Fluid clamp endpoints as calc-of-var:** `clamp(calc(var(--size-ghost-watermark)*.35), …)`
   conflicts mildly with the Webflow "no calc chains" preference — accept calc in layer 2/3
   (layer 1 stays flat; export maps endpoints), or precompute static clamp strings into
   layer 1 per brand (flatter, but N tokens per fluid role)?
