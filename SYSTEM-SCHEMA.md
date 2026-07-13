# SYSTEM SCHEMA — Brand Extraction & Composition Pipeline

> The exact map of how this system works: what is extracted, which rules consume it,
> how the agents/skills operate, what the deliverables are — and why the approach is
> different from ordinary "LLM, please clone this website" generation.

---

## 0. The thesis (the unique approach in one paragraph)

Plain LLM site generation produces generic output because taste is fed in as vibes
("premium", "editorial") and the model writes free-form HTML nobody can verify. This
system inverts that: **taste is compiled into measurable facts, and the LLM is never
allowed to write HTML.** A live site is mined into a machine-verifiable evidence bundle;
an agent authors a canonical, library-agnostic `brand.yaml` from that evidence; a
deterministic renderer is the only thing that emits markup; and every rendered pixel is
policed by five rule engines with named rule IDs (C1–C23, AS-01–AS-60, IC-*, spacing
severity ladder, neverDo gate). The proof of fidelity is mechanized: the system rebuilds
the source homepage 1:1 through its own machinery and pixel-diffs it (the **replica
gate**). Every visual defect ever found is converted into a permanent mechanical rule —
composer discipline (can't emit it) + gate check (fails if emitted) — so the system
**ratchets**: it can only get better, never silently regress.

Five load-bearing principles:

1. **Evidence-first, mechanics beat vibes.** Nothing enters `brand.yaml` without a
   measured source (computed style, mined CSS, DOM census, vision grounding) or an
   explicit `notObserved: true`. Spacing, type ladders, surface nesting > adjectives.
2. **The LLM emits structure, never HTML.** Generation is a structured `composition.v1`
   JSON object; a deterministic composer draws it. Hallucination surface ≈ zero.
3. **One source of truth per component.** `component_render.py` owns exactly one renderer
   per catalog component; the gallery, single sections, full pages, and the replica all
   assemble from the same renderers. Edit once, changes everywhere.
4. **Every defect becomes a rule.** No silent fall-throughs; resolution sources are
   stamped into the DOM (`data-pattern`, `data-align-source`, `data-ag-gap`) so audits
   can check the render against its own declared intent.
5. **Fact-gated, brand-agnostic devices.** Shared renderer code activates only on brand
   facts; a brand without the fact renders **byte-identically** to before the feature
   existed (test-pinned). Features can't leak one brand's DNA into another.

---

## 1. Big picture — the four layers

```
              LIVE SITE (URL)
                    │
   ┌────────────────▼────────────────┐
   │ LAYER 1 — EXTRACTION (scripts)  │  deterministic miners + one vision LLM pass
   │ run_brand_extraction.py stages: │
   │ mine-dom · mine-css · mine-     │──► runs/<brand>/brand/evidence/*  (9 artifacts)
   │ motion · measure · slice ·      │──► runs/<brand>/assets/source-chrome.v2.json
   │ ground · curate                 │──► runs/<brand>/brand/assets/*
   └────────────────┬────────────────┘
                    │ evidence bundle
   ┌────────────────▼────────────────┐
   │ LAYER 2 — AUTHORING (agent)     │  "author" stage = agent work, not a script
   │ skill: brand-layout-analyst     │──► brand.yaml        (CANONICAL design language)
   │ (5 phases, layout-analyst-      │──► section-copy.yaml (verbatim copy per layout)
   │  skill.md doctrine)             │──► layout-library.yaml (brand's own patterns)
   │ gate: validate_brand_evidence   │──► assets-tagged.json
   │       C1..C23 must exit 0       │
   └────────────────┬────────────────┘
                    │ canonical brand facts
   ┌────────────────▼────────────────┐
   │ LAYER 3 — COMPOSITION (hybrid)  │  LLM plans, deterministic code draws
   │ generate_composition.py         │──► composition.json  (composition.v1, NEVER html)
   │   └► compose_from_composition   │
   │        └► compose_page /        │──► index.html  (full page, real chrome, iframe-safe)
   │           compose_section       │
   │ SSOT: component_render.py       │──► components-preview (spec book + gallery)
   │ tokens: tokens_css.py           │──► tokens.css + tokens.manifest.json
   └────────────────┬────────────────┘
                    │ rendered HTML
   ┌────────────────▼────────────────┐
   │ LAYER 4 — GATES (5 engines)     │  named rule IDs, fail-loud, test-pinned
   │ onbrand_check (neverDo HARD)    │──► onbrand-report.{md,json}
   │ slop_audit.mjs (AS-*)           │──► exit 1 on any flag, @1440+@1180
   │ interaction_audit (IC-*)        │──► strict: exit 1 on required fail
   │ spacing_audit (severity ladder) │──► strict: exit 1 on hard cell
   │ compose_replica (REPLICA GATE)  │──► replica-report + renderer-gap punch list
   └─────────────────────────────────┘
                    │
        DELIVERABLE: the exported BRAND KIT (runs/<brand>/brand/kit/)
        a self-contained "taste skill" any agent can load — see §7
```

Two orchestrators sit above this:

- **`run_brand_extraction.py`** — the evidence pipeline. Stage list (each re-runnable via
  `--stages`): `mine-dom, mine-css, mine-motion, measure, slice, ground, curate, author,
  validate`. `author` is deliberately **not a script** — it prints the specs the agent
  must follow.
- **`run_pipeline.py` + `studio_server.py`** — the legacy screenshot→site pipeline and
  its Studio UI (port 1500: project dashboard, job runner via subprocess, viewers).
  It shares the `runs/` tree but is a separate flow (design-system synthesis from
  screenshots, framework React+Tailwind site generation).

---

## 2. LAYER 1 — Extraction: exactly what is measured

Input: a URL → `tools/extract/capture_page.py` (Playwright: scroll pass for lazy media,
consent-banner dismissal, downloads every stylesheet + rendered image, rewrites DOM to
local refs) → a "Save Page As, Complete"-shaped capture in `screenshots/<brand>/`
(`<name>.html` + `<name>_files/` + full-page PNG). All miners read this offline capture;
two passes go back to the live URL for states a snapshot can't show (open mega-menus,
accordion/tab states).

| Stage / script | What it measures (concrete fields) | Output (schema) |
|---|---|---|
| `measure_computed.py` (JS **off** — static CSS truth) | chrome surfaces (`background-color, color, padding, border-*, position, max-width`), first h1–h6+p typography (`font-family/size/weight, line-height, letter-spacing, text-transform` + rects), **button variant matrix** (every `<a>/<button>` grouped by class signature: bg, fg, border, radius, padding, type, `widthBehavior: stretch/hug/near-full`, count), visible content sections (chrome-nested + hidden nodes filtered), chrome band rects, **canonical tier ladder** at 1920/1440/960/375 (per-tier heading sizes, container facts: `cssMaxWidth, usedWidthPx, viewportFraction, padding, owner`, heading-emphasis weights) | `evidence/computed-styles.json` (`computed-measure.v2`), `evidence/section-rects.json` |
| `mine_css.py` | raw rule dump + censuses: `hoverRules, radiusCensus, fontFamilyCensus, fontWeightCensus, transitionCensus, letterSpacingCensus, textTransformCensus, colorCensus, mediaBreakpoints` | `evidence/css-rules.json`, `css-facts.json` (`css-mine.v1`) |
| `mine_dom.py` | section order + per-section tag/class/text/img inventory, repeated-module counts, surface-scheme classes, button census, eyebrow candidates, **chrome census** (header links/ctas; footer columns/social/legal), inline-style color evidence | `evidence/dom-sections.json` (`dom-mine.v1`) |
| `mine_motion.py` (reads `css-rules.json`) | per-selector `transitions[]` / `animations[]` / `keyframes[]`, timing custom-props, duration + easing censuses | `evidence/motion-audit.json` (`motion-audit.v1`) |
| `slice_sections.py` (reads `section-rects.json`) | per-section screenshot crops (viewport-ratio scaled) | `evidence/crops/` + `crops-manifest.json` |
| `ground_sections_vision.py` — **the one LLM pass** (`claude-opus-4-8`, system prompt = `spec/extraction-grounding-prompt.md`, one call per crop) | per-crop vision grounding: `sectionRole, layout, surfaces, typography, relationalSpacingPx, components, copy (verbatim), media, chrome, componentAnatomies, motionHints` | `evidence/grounding/*.yaml` (`section-grounding.v1`) |
| `curate_assets.py` | real raster/vector files + inline SVGs (logos, icons, art) | `brand/assets/*` + `assets-manifest.json` |
| `capture_disclosure_states.py` (live) | accordion/tab per-item body copy + media-swap artwork | `disclosure-<slug>.json` + PNGs |
| `browser_chrome_extractor.py` via `tools/extract_chrome_saved.py` (JS **on** — real visibility) | the full **chrome contract**: nav logo/links/tiers, mega-menu panels (columns, links w/ descriptions+icons, featured cards, surfaces), CTAs (`label, href, bg, filled`), measured `contentMaxWidth`, open-panel geometry + motion facts, utility banner anatomy; footer columns, social, legal, newsletter, bottomBar (divider/policy/badges), measured grid | `runs/<brand>/assets/source-chrome.v2.json` (`source_chrome.v2`) |
| `tools/bridge_chrome_to_brand.py` (Phase 0 of authoring) | merges the chrome contract into `brand.yaml` (atomic write) + renders chrome preview | `brand/chrome/index.html` |

Design point: screenshots are for **vision grounding and diffing only**; every number in
the system comes from the DOM/CSS measurement, not from a model eyeballing pixels. Where
vision and computed values conflict, computed wins and the contradiction is documented
in the token's role note.

---

## 3. LAYER 2 — Authoring: the agent + the C1–C23 contract

The `author` stage is **agent work by design**. The agent loads the
**`brand-layout-analyst` skill** (`spec/layout-analyst-skill.md`) — a 5-phase doctrine:

- **Phase 0** — run the chrome bridge (nav/footer land in `brand.yaml` first).
- **Phase 1** — section census: reconcile `dom-sections.json` × `section-rects.json` ×
  crops into an ordered section list.
- **Phase 2** — tokens + component matrices from evidence: color roles, type tiers
  (multi-breakpoint ladders), **relational spacing ladder** (named rungs:
  `eyebrow-to-heading`, `heading-to-body`, `body-to-cta`…), radius, motion, button
  families, card variants, recipes (recurring anatomies used by 2+ sections).
- **Phase 3** — per-section layouts: `archetype` + named `slots[]` + `blockMapping[]`
  `{slot, role, contract, usage}` binding each slot to a catalog component; patterns
  promoted into the brand's own `layout-library.yaml` (`origin: extracted`).
- **Phase 4** — rule synthesis (`do[]` / `avoid[]` / `neverDo[]`, surface grammar,
  composition rules) + run the validator.

The agent hand-writes four files (per `spec/brand-schema.md`, the 108 KB canonical schema):

| File | Role |
|---|---|
| `brand.yaml` | **The canon.** Library-agnostic: tokens (intent+value+provenance+confidence), surfaceGrammar, layouts[], compositionRules, `do/avoid/neverDo`, primitives/blocks overrides, recipes, voice, chrome. Substrate IDs only in optional `targetMappings:` |
| `section-copy.yaml` | Verbatim copy per layout (`sectionCopy, layoutCopy, layoutImages, defaultArt, wildcardCopy`) — `spec/section-copy-schema.md` |
| `layout-library.yaml` | The brand's reusable, use-case-keyed patterns |
| `assets-tagged.json` | Every asset tagged with role/kind + reusable `mediaTreatmentRules` |

**The contract gate:** `tools/extract/validate_brand_evidence.py` must exit 0. Its checks
(E = error, W = warning) are the extraction OUTPUT CONTRACT (brand-schema.md §10):

| Check | Enforces |
|---|---|
| C1 | `brand.yaml` exists + parses |
| C2 | every contract block type attempted with evidence or explicit `notObserved: true` |
| C3 | button variant matrix complete (radius+surface+state facts, hover pairing, filled needs height+padding) |
| C4 | `section-copy.yaml` present, schema-conformant, every content layout has copy |
| C5 | layout↔pattern coverage (patternRef or noPatternReason) |
| C6 | logos use-case backed by real asset files on disk |
| C7 | chrome integrity (nav links/surface, footer columns/social/legal, contentMaxWidth 480–2200px, renderable logos) |
| C8 | assets-tagged.json complete, every file exists |
| C9 | ≥1 vision grounding file |
| C10 | card variants enumerated or `singleVariantConfirmed` |
| C11 | composed-demo smoke: every pattern renders w/o placeholders/empty captions |
| C12 | escape hygiene (no double-escaped entities) |
| C13 | motion evidence (≥1 duration + ≥1 easing, interactive blocks name a timing fact) |
| C14 | canonical-tier discipline (every sized type role has ≥2-breakpoint ladder) |
| C15 | relational spacing ladder (≥2 named `<role>-to-<role>` rungs) |
| C16 | chrome DEPTH facts (mega-panel geometry/motion, icon+card assets on disk, footer grid sums) |
| C17 | disclosure per-item content (all bodies + media exist) |
| C18 | contextual header-alignment grammar authored when corroborated |
| C19 | radius value sanity |
| C20 | card-grid equalization facts recorded |
| C21 | bar-level affordances (chevrons, dropdown panels live-captured, banner cta/close anatomy) |
| C22 (adv.) | measured utility-bar height without declared `navbar.utilityTier` warns |
| C23 (adv.) | recurring rail anatomies bound to a `recipes:` entry (no dangling refs) |

**Projection discipline:** `render_brand_md.py` renders `brand.yaml → brand.md` as a
pure deterministic function. `brand.md` is never hand-edited; drift is a warning. When
they disagree, `brand.yaml` wins.

---

## 4. LAYER 3 — Composition: LLM plans, deterministic code draws

### 4.1 The hybrid split

- **`generate_composition.py`** makes **one structured LLM call** (default
  `claude-opus-4-8`). The prompt is deterministically assembled from: the brief,
  `brand.yaml` (tokens, neverDo, measured tiers, spacing rungs), the merged STYLE layer,
  catalog signatures, composition rules, and **seed patterns** from the layout library
  ("REUSE these; tune only these knobs; you MAY depart with `novelty: novel`" — seeds
  bias, they don't cage). The model returns a **`composition.v1` JSON object** (ordered
  sections → archetype/slots/treatments/copy refs) — validated against
  `spec/composition.v1.schema.json`. **It never returns HTML.**
- **Generate→validate→repair loop** (≤2 repairs): schema validation → `neverDo`
  prefilter → off-grid prefilter → render → on-brand gate; failing rule IDs are fed back
  as a repair note.
- **`compose_from_composition.py`** adapts the object onto the deterministic composers.

### 4.2 The deterministic renderer (single source of truth)

```
brand.yaml layout                      component_render.py (SSOT)
  archetype + slots[] +                  ONE renderer per catalog component
  blockMapping[]{slot,role,              (heading, eyebrow, image, arrow-link,
    contract, usage}                      logo, header, navbar, …) + COMPONENT_CSS
        │        contract ──► resolve_renderer(contract)
        ▼
  compose_section.py — render each slot, then an ARCHETYPE COMPOSER arranges them
        (24 composers: stack, split, collage, cards, media-split, overlay, banded,
         interlock, edge-cut carousels, tab-split, generic-flow fallback, …)
        ▼
  compose_page.py — full page in pageOrder + real chrome (nav/footer from the contract)
```

- `tokens_css.py` is the token SSOT: emits layer-1 CSS custom properties
  (`--color-*, --surface-*, --font-*, --space-*, --radius-*, --motion-*`) +
  `tokens.manifest.json` for provenance/drift.
- Per-surface token values are re-emitted as CSS vars so the **same classes** read
  correctly on a dark hero or a cream canvas (surface grammar, not per-section CSS).
- Iframe-safe: container-query units only (`cqw/cqi`), never `vh/vw`.
- The **gallery/spec book** (`render_components_preview.py`) imports the same renderers —
  a one-line change to a primitive propagates to the gallery, every composed section,
  the full page, and the replica simultaneously.

### 4.3 The layout library (reuse before create)

`layout_library.py` stacks two tiers: **standard** (`contracts/layout-patterns/*.yaml`,
brand-agnostic, ~35 patterns over 10 use-cases: hero/features/pricing/testimonial/
gallery/cta/about/faq/logos/footer) and **project** (`runs/<brand>/brand/
layout-library.yaml`, `origin: extracted`). `match()` scores candidates
(archetype 1.0, slots 2.0, size-relations 1.0, treatments 2.0, surface 0.5; project
tie-break +0.75) and classifies: **≥4.5 reuse** as-is · **2.5–4.5 adapt** via
variantKnobs · **<2.5 miss** → invent, then `promote()` into the project tier. A pattern
whose treatments would violate the brand's `neverDo` is filtered **before** scoring —
neverDo is the only hard gate everywhere.

### 4.4 The STYLE × BRAND two-layer generation

A page = **STYLE** (`styles/*.md`: qualitative structure — shape, alignment stances per
archetype, density, freedom-budget ladder; no px/hex ever) merged with **BRAND**
(`brand.yaml`: all measured values). Style CSS is appended after brand base so structure
rules win while the brand keeps hues + fonts. The **freedom budget** (0–5 per section,
declared by the style, chosen by the human, never by the model) governs sanctioned
divergence; blessed one-offs live in `magic-trick.md`.

---

## 5. LAYER 4 — The gates: which rules police what

Five engines, all deterministic (no LLM judges), each with named rule IDs:

| Engine | Spec | Rule IDs | Hard/advisory | What it checks |
|---|---|---|---|---|
| `onbrand_check.py` + `readability.py` | brand.yaml rules | brand's own `neverDo` ids (e.g. `no-radius`, `no-typographic-only-cta`) | **neverDo = the ONLY non-overridable hard layer**; fidelity + slop + composition invariants gate under `--composition` | neverDo registry (unknown ids degrade to heuristics, never false-fail); brand tokens actually present; `text-contrast` ≥3.0 display / ≥4.5 body vs *composited* effective background; `decoration-salience` ≤1.19 (ghost type stays quiet); occlusion geometry; **token provenance** — every visual literal must trace to the brand's token index or carry `/* provenance: structural */`; a literal matching *another* brand's index = foreign-DNA leak |
| `slop_audit.mjs` (Playwright @1440 + @1180) | `spec/anti-ai-slop.md` | **AS-01…AS-60** | exit 1 on any flag | generation-failure shapes: AS-11 metadata-only section, AS-12 empty grid column, AS-13 map/chart without data text, AS-14 form with no reason, AS-16 text flush against media, AS-23 image-placeholder lifecycle, AS-49 scaffold-habit alignment, AS-59 exactly one filled primary per action group, AS-60 computed layout must match the group's own `data-ag-*` stamps |
| `interaction_audit.py` (static + Playwright behavioral) | `spec/interaction-contracts.md` | **IC-<FAMILY>-NN** over 9 families: NAV-01..08, LANG-01..07, ACC-01..08, BAN-01..04, CAR-01..05, MARQ-01..03, TAB-01..06, FORM-01..07, REV-01..04 | `--strict` exits 1 on required fails | WAI-ARIA APG conformance: disclosure semantics, aria-expanded/controls, roving tabindex, Escape-beats-hover (WCAG 1.4.13), single-open accordion, keyboard arrows/Home/End, reduced-motion, form labelling |
| `spacing_audit.py` (Playwright, 1440×900) | `spec/spacing-conformance.md` | severity ladder: `conform / drift / wrong-step / off-ladder / unmapped` | hard = `wrong-step` + `off-ladder`; `--strict` exits 1 | every rendered gap vs the brand's captured facts: header-stack rhythm, band rhythm, grid geometry, card anatomy (`cardActionGap`), container law, action groups; tolerance `max(2px, 10%)` rhythm / `max(2px, 1%)` widths |
| `compose_replica.py` — **the replica gate** | — | per-band score | diagnostic (opt-in `--fail-under`) | rebuilds the **source homepage 1:1** through the real composers, screenshots it, per-section diff vs the source screenshot. Score = 0.5·structure + 0.3·pixel + 0.2·height, height-weighted overall. Bands <0.85 become the **renderer-gap punch list** (named missing capabilities). Current: hubspot-v2 **0.956**, Remote **0.950** |

Plus the extraction-side gate (`validate_brand_evidence.py` C1–C23, §3) and the
regression harness: **842 pytest tests** pin every device, gate, and fact-gated
byte-identity guarantee; `phase0_regate.py` enforces zero PASS→FAIL across changes.

The recurring green-board cited on every change:
`validate C1–C23 0 errors · onbrand PASS · slop PASS @1440+@1180 · interaction strict 0 ·
spacing strict exit 0 · replica ≥ baseline · full suite N passed`.

---

## 6. The agents & skills roster

### In-pipeline LLM calls (automated)
| Agent | Where | Model | Emits |
|---|---|---|---|
| **Vision grounder** | `ground_sections_vision.py`, system prompt = `spec/extraction-grounding-prompt.md` | claude-opus-4-8 | `section-grounding.v1` YAML per crop |
| **Composition generator** | `generate_composition.py` | claude-opus-4-8 | `composition.v1` JSON (never HTML), with validate/repair loop |

### Authoring skills (agent reads doctrine, hand-writes canon)
| Skill | File | Owns |
|---|---|---|
| **Layout Analyst** (`brand-layout-analyst`) | `spec/layout-analyst-skill.md` | extracts `brand.yaml` + layouts + recipes from evidence; emits creation signals |
| **Art Director** (`brand-art-director`) | `spec/brand-designer-skill.md` + `spec/signal-loop.md` | owns `brand.yaml`/`brand.md`, the `do/avoid/neverDo` lists, and the signal-consolidation loop |

### The downstream production chain (`brand_pipeline/prompts/`)
Four role prompts, each consuming the previous one's artifact:

```
brand.yaml + screenshot ─► ART DIRECTOR ─► brand.md   (judgment layer: relationships,
                                                       surface rhythm, never-do diffs vs
                                                       generic-web defaults)
brand.md + brief ────────► COPYWRITER ──► voice.md    (voice contract + verbatim copy,
                                                       length budgets per type role)
asset manifest + brand.md► ASSET DIRECTOR ► assets.md (slot map: real assets only, by id;
                                                       gaps get generation briefs)
all three + chrome + vars► ASSEMBLER ────► build.md   (per-section Webflow build plan:
                                                       layout-first, reuse-before-create,
                                                       FlowKit class contract, executed
                                                       via Webflow MCP)
```

### Site-generation garnish skills (`skills/`)
`motion-design-gsap` (GSAP-only motion doctrine: no-FOUC three-step reveal, reduced-motion,
one entrance owner per element) and `shader-effects` — loaded into the legacy pipeline's
site-gen prompt via `load_site_generation_skills`.

### The self-education loop (`spec/signal-loop.md`)
```
creation signals (analyst) ┐
iteration signals (human edits) ├─► signals.log (JSONL) ─► consolidation pass
build-failure signals (assembler) ┘         │  (manual, on-demand)
                                            ▼
              promotion gate: user must confirm design-language promotions
              EXCEPT build-failures, which auto-promote to neverDo/recipePolicy
              contradictions → apply once (scope: one-off) + queue a question
                               in pending-questions.yaml — never block, never auto-promote
```
Field agents using an exported kit obey a **one-way ratchet**: they append to
`learning/proposals.yaml` + `learning/signals.log` but may never edit the canon —
"field proposes, home ratifies, the next kit export supersedes."

---

## 7. Deliverables

Per brand (`runs/<brand>/brand/`):

| Deliverable | What it is |
|---|---|
| **`brand.yaml`** | The canonical machine design language (validated C1–C23) |
| **`brand.md`** | Human-readable projection (generated, never edited) |
| **`voice.md`, `assets.md`** | Copy contract + asset slot map from the agent chain |
| **`layout-library.yaml`** | Brand's reusable patterns (origin: extracted/designed) |
| **`components-preview/index.html`** | The **spec book**: 6+ chapters (color chips, measured type ladders, true-size spacing bars, radius, live motion demos, button state-matrices on every surface, component recipes) — every exhibit cites its `brand.yaml` key |
| **`compose/index.html`** (+ lanes) | Composed full pages through the live pipeline, gate-green only |
| **`compose/replica/`** + `replica-report.{md,json}` | The 1:1 rebuild proof + per-band scores + renderer-gap punch list |
| **`chrome/index.html`** | Rendered nav/footer contract preview |
| **`evidence/`** | The full measurable evidence bundle (9 artifacts, §2) |
| **`kit/`** — **the flagship export** | A **self-contained, machine-actionable brand system**: `kit/SKILL.md` (the compiled per-brand "taste skill" — operating loop, freedom-budget protocol, learn-by-proposing rules), `agent/` (brand.yaml, layout-library, tokens.css, motion.json, quality/rules.yaml + the portable slop/contrast audits), `human/` (brand.md, voice.md, previews), `magic-trick.md` (blessed one-offs). Any agent, anywhere, can load this and build on-brand with zero access to the pipeline. |

Repo-level: `viewer.html` (side-by-side run comparison), Studio (`:1500/studio` —
paste-a-URL project intake, job logs, lanes), `version-scoreboard.html`, and the
append-only `changes.md` engineering log with the gate scores for every change.

---

## 8. Why this is different (summary of the unique approach)

1. **Compiled taste, not prompted taste.** The brand is a validated data structure with
   provenance and confidence per fact — not a mood-board paragraph. The exported kit
   makes taste *portable*: a brand becomes a loadable skill.
2. **Zero-hallucination rendering.** The only HTML author is deterministic Python; the
   LLM's entire output surface is a schema-validated JSON plan filtered through the
   brand's neverDo before it is ever drawn.
3. **Adversarial self-verification.** Five independent rule engines with ~150 named
   rules (C1–C23, AS-01–60, IC-* ×9 families, spacing ladder, neverDo) run on every
   render; "gate-green only" is the definition of done.
4. **The replica as an honesty metric.** The system must be able to rebuild the source
   site through its own machinery; the pixel-scored gap list *names the renderer
   capabilities that are missing* — fidelity failures become a work queue, not a shrug.
5. **The ratchet.** Every defect → a mechanical rule + a pinned test; fact-gated devices
   guarantee other brands render byte-identically; regression = zero PASS→FAIL, ever.
6. **Human-in-the-loop where it matters, nowhere else.** Freedom budgets, rule
   promotions, and magic-trick blessings are human decisions; everything mechanical is
   automated and fail-loud.
