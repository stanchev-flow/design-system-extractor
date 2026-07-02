# WoodWave A/B — Structured vs HTML-first (signup-launch, editorial-luxury)

A controlled comparison of two **generation representations**, holding brand + style +
brief constant, to inform whether a structured pipeline or an HTML-first approach yields
more on-brand output.

- **Brand:** WoodWave Gallery · **Style:** `editorial-luxury` · **Brief:** `signup-launch`
- **Arm A (structured):** structured contracts → deterministic renderer (the existing
  `compose_page` → `compose_section` → `component_render` pipeline).
- **Arm B (HTML-first):** the model (me) authored a single self-contained `index.html`
  directly from the same tokens + style guidance + brief — no contract, no renderer.

All experiment artifacts live under `experiments/woodwave-ab/`. Nothing under
`runs/woodwave/**` was written; the pipeline modules were imported read-only.

---

## 0. Inputs snapshot (reproducibility + concurrency insulation)

A separate worker is concurrently editing `runs/woodwave/brand/brand.yaml` (swapping the
display font to **Melodrama**) and regenerating `runs/woodwave/brand/compose/*`. To insulate
this experiment I snapshotted the inputs **once**, up front, into
`experiments/woodwave-ab/inputs/`, and ran **both** arms against that snapshot.

| snapshotted input | source (read-only) | notes |
|---|---|---|
| `inputs/brand.yaml` | `runs/woodwave/brand/brand.yaml` | **md5 `269af905cb2ab3b4d4bad33167821216`** |
| `inputs/editorial-luxury.md` | `styles/editorial-luxury.md` | style guide (invariants + soft options + prose) |
| `inputs/signup-launch.md` | `brand_pipeline/test-briefs/signup-launch.md` | the brief |
| `inputs/assets/657…_Logo.svg` | `runs/woodwave/assets/source_complete/` | wordmark (baked gold `#EDD580`) |
| `inputs/assets/source-chrome.v2.json`, `brand-assets.json` | `runs/woodwave/assets/` | nav/footer chrome + asset manifest |
| `inputs/assets/*.jpg`, `inputs/brand/…` | `runs/woodwave/brand/variants/a/assets/` | hero + overlap photography; a mini brand-dir for the composer |

**Snapshotted `brand.yaml` revision:** the display tiers were **`Playfair Display`** (8
`Playfair` references, **0** `Melodrama`). So this experiment captured the *pre-Melodrama*
revision; the concurrent swap did not affect either arm.

---

## Step 0 — the intended brief-driven structured path (what actually exists)

I traced how briefs are meant to drive generation:

- `brand_pipeline/compose_page.py` is the page composer. It walks the brand's `layouts[]`
  in **story order** (`DEFAULT_ORDER = opening-bookend → editorial-collage → info-band →
  conversion-stack`, + a `closing-bookend` footer), and for each layout runs the same
  slot→catalog→archetype machinery as the single-section composer
  (`compose_section.render_slots` + `ARCHETYPE_COMPOSERS`), rendering every slot through the
  shared `component_render.py` renderers. Style structure (`editorial-luxury`) is layered
  over per-section brand hues/fonts via `styles.py`.
- **There is no standing brief-consuming entrypoint.** `compose_page.py` takes
  `<brand.yaml> -o <out> --style --order` — no `--brief`. The copy it emits comes from
  hardcoded dicts in `compose_section.py` (`SECTION_COPY` + `LAYOUT_COPY`), which currently
  hold WoodWave's *gallery* copy (“About the gallery”, “Ticket prices”…), **not** the brief.
- The existing `runs/woodwave/brand/compose/signup-launch/` dir contains a `plan.json`
  (brief → section-selection + per-section slot bindings + gap rationale) and a rendered
  `index.html` carrying brief copy. `plan.json` is **not produced by any current `.py`** — it
  is the structured *contract* a prior agent authored by hand as the “SELECT + ORDER + BIND”
  stage the brief describes. So the intended flow is:
  **brief → (plan.json: select/order/bind) → compose_page renders the bound layouts.**

**What I did for Arm A (faithful structured path).** I reused the existing pipeline
unchanged and performed only the missing *bind* stage in-memory: a small generator
(`gen_arm_a.py`) loads the snapshot `brand.yaml`, overrides `compose_section.SECTION_COPY` /
`LAYOUT_COPY` with the **brief's** copy mapped onto WoodWave's layouts (mirroring
`plan.json`'s bindings), mutates the `opening-bookend` display-title slot to the brief
headline, then calls the **unmodified** `compose_page.build_page(...)` with
`--style editorial-luxury`. No pipeline source was edited; no `runs/woodwave` write.

---

## Arm A — method (structured)

- Command equivalent: `gen_arm_a.py` → `compose_page.build_page(doc, snapshot_brand,
  DEFAULT_ORDER, editorial-luxury)`.
- Brief consumed by **binding copy into the layouts' typed slots** (the pipeline's copy
  dicts): hero eyebrow/headline/subhead/CTA; value_props → the `editorial-collage` module;
  social_proof (stat + quote) + value_props → the `info-band` intro + cream-panel ruled rows;
  conversion → the underline `conversion-stack`; footer from brand chrome.
- Output: `arm-a-structured/index.html` + `assets/` (nav logo + 2 photos, copied from the
  snapshot). Container-query units only. 0 unresolved slots across all 5 sections.

## Arm B — method (HTML-first)

- I authored one self-contained `arm-b-html/index.html` (inline CSS) directly from the
  snapshot `brand.yaml` tokens (colours, type families/scale, spacing, radius 0, motion
  spec) + the `editorial-luxury` invariants/soft-options/prose + the brief.
- **Offline + self-hosted:** Playfair Display + Inter woff2 downloaded once into
  `assets/fonts/` and referenced via `@font-face`; logo + photos copied into `assets/`. **No
  external CDN at runtime.**
- Brand fidelity by construction: brand token hexes only; radius 0; no shadows/borders
  shorthand/gradients; typographic arrow links (no buttons); underline-only field; ghost
  watermark; asymmetric anchored value-prop modules; gold accent on dark surfaces only;
  container-query units (cqw/cqh/cqi), zero viewport units.

---

## Gate results — side by side

Gate: `onbrand_check.py <snapshot brand.yaml> <arm> --layout opening-bookend --style
editorial-luxury`. `opening-bookend` is the layout that best matches the brief's hero-led
signup page (and the layout both prior WoodWave composes were gated against). OVERALL =
`neverDo` (hard) ∧ `fidelity` ∧ `slop`; style rows are advisory and never gate.

| metric | Arm A (structured) | Arm B (HTML-first) |
|---|---|---|
| **OVERALL** | **PASS** | **FAIL** |
| neverDo pass count | **11 / 11** | **9 / 11** |
| — fails | none | `no-boxed-inputs`, `no-default-fonts` |
| Fidelity | PASS (6/6) | PASS (6/6) |
| Slop | PASS (6/6) | **FAIL (5/6)** — `Webfonts loaded` |
| Viewport units | **0** | **0** |
| Unresolved slots | **0** | n/a (hand-authored; effectively 0) |
| Poster display ≥ 8rem | yes (`clamp(8rem,11cqw,14.4rem)`) | yes (`clamp(8rem,13cqw,14.4rem)`) |
| Style invariants | 5 PASS + 4 OVERRIDE | 3 PASS + **2 WARN** + 2 OVERRIDE |
| off-palette hexes | none | none |

### neverDo breakdown (all 11)

| rule | Arm A | Arm B |
|---|---|---|
| `no-buttons` | PASS | PASS |
| `no-radius` | PASS | PASS |
| `no-shadows` | PASS | PASS |
| `no-gradients` | PASS | PASS |
| `no-cards-on-cream` | PASS | PASS |
| `no-accent-on-light` | PASS | PASS |
| `no-boxed-inputs` | PASS | **FAIL** (real `<input>` present; gate proxies the rule as “0 `<input>` elements”) |
| `no-text-on-photos` | PASS | PASS |
| `no-section-hairlines` | PASS | PASS (rules drawn as pseudo-element strips, not CSS borders) |
| `no-default-fonts` | PASS | **FAIL** (fonts self-hosted; gate requires a `fonts.googleapis.com` link) |
| `no-centered-everything` | PASS | PASS |

### Why Arm B's two neverDo fails and one slop fail are *mechanism coupling*, not off-brand output

All three failures share one root cause: **the gate is co-designed with the deterministic
renderer**, so its static heuristics look for the *pipeline's specific delivery mechanisms*
rather than the brand rule itself.

- `no-default-fonts` **and** slop `Webfonts loaded` both key on the literal string
  `fonts.googleapis.com`. Arm A links Google Fonts (a CDN), so it passes. Arm B **self-hosts
  the identical brand fonts offline** (the brief-fair choice) — the rendered display family
  is verifiably `Playfair Display` (the gate even reports `display font=Playfair Display` and
  the “No default/system display font” slop row PASSES) — yet it FAILs because there is no
  Google link. This penalises the *more* robust, offline implementation.
- `no-boxed-inputs` is proxied as `<input> count == 0`. The pipeline never emits a real
  input — `render_input` fakes the field with a `<label><span>`. Arm B ships a **real,
  functional `<input type="email">` styled underline-only** (no box, no fill, radius 0,
  hairline via pseudo-element) — which *is* exactly what the brand rule (“underline only,
  inline text submit”) asks for — but any `<input>` trips the proxy.
- The two Arm-B style **WARNs** (asymmetric grid; single accent) are the same story: the
  checker keys on the pipeline's canonical `.hv-title.is-display` selector, which a
  from-scratch page doesn't emit. Arm B *is* asymmetric (three margin-anchored value-prop
  modules) and single-accent (gold on dark only, 0 off-palette) — the heuristic just can't
  see it without the pipeline's class names. These are advisory and don't gate.

Both arms independently PASS everything that is a *genuine visual brand rule* checkable
without a specific selector: radius 0, no shadows/gradients, no cards on cream, accent on
dark only, hard cuts, poster serif, container-query units, brand palette only.

---

## Qualitative comparison (from the rendered screenshots)

**On-brand fidelity.** Both read unmistakably as WoodWave editorial-luxury: cream/warm-brown
two-tone rhythm, uppercase Playfair display at poster scale, Inter tracked-uppercase
functional text, gold reserved for dark surfaces, hard-edged staggered photography, ghost
watermark, typographic slash/arrow actions, zero rounding/shadow. Visually they are near
peers; neither looks generic-AI.

**Structural variety / brief handling — Arm B is stronger.** The brief carries **three**
value_props. Arm A's deterministic `editorial-collage` is a **single module**, so all three
props are compressed into one prose paragraph under one heading — the count is lost. Arm B
renders the three props as **three distinct staggered editorial modules** (01/02/03 index
counters, alternating left/indented/right anchors, ruled bars, per-prop title+body) — an
open-collage answer to a feature grid that both honours `no-cards-on-cream` **and** preserves
the brief's structure. This is the clearest quality gap, and it favours HTML-first.

**Editorial-luxury invariants.** Arm A leans on the pipeline's committed hero exception
(centered + accent scoped to `#sec-0`) and passes every invariant row cleanly. Arm B satisfies
the invariants in substance (poster serif, two flat fields, asymmetry, single accent,
photography-led, one motif) but is dinged by selector-coupled WARNs. Arm A's asymmetry is
mostly *within* the single collage; Arm B's asymmetry is more legible across the value section.

**Signup / conversion intent.** Both close with a narrow centered underline stack (eyebrow →
headline → `you@company.com` → `START FREE →`) and repeat the CTA in the hero, nav, value
section, and social-proof panel. Arm B's field is a **real, submittable** email input; Arm A's
is a visual placeholder (`<label><span>`, non-functional) — better for a real signup page in
Arm B, though the automated gate rewards Arm A's fake field.

**Failure modes.**
- *Arm A:* brief structure can be flattened to whatever the fixed layout inventory affords
  (3 props → 1 module); copy binding is a manual/out-of-band step (no `--brief` entrypoint),
  so “brief-driven” is really “human authored a plan.json, then render”. Very consistent, but
  ceilinged by the catalog.
- *Arm B:* free-form authoring must **reverse-engineer the gate's exact conventions**
  (pseudo-element hairlines, Google-Fonts link, no real `<input>`, canonical class names) to
  score well; miss one and OVERALL flips even when the pixels are on-brand. Higher ceiling,
  less guard-railed, and not automatically gate-clean.

---

## Recommendation (tied to the evidence)

For *this* brief, **both representations produced on-brand output, but they win on different
axes**, and the honest read is **hybrid**, not a clean victory for either:

1. **Structured (Arm A) wins on gate-conformance and consistency.** It passed OVERALL 11/11
   with zero effort to satisfy heuristics, because the renderer and the gate are co-designed.
   If the goal is a reliably gate-green, brand-safe page, structured is the safe default.

2. **HTML-first (Arm B) wins on brief fidelity and structural expressiveness.** It was the
   only arm that actually rendered the brief's three value_props as three units, shipped a
   functional signup field, and self-hosts fonts offline. Its two hard fails and one slop
   fail are **artifacts of gate↔renderer coupling** (Google-Fonts string, `<input>` proxy),
   **not** genuine off-brand output — confirmed by the screenshot and by the fidelity/slop
   font row passing.

3. **Where the difference came from:** *not* from taste or palette (both nailed the tokens),
   but from **representation constraints** — Arm A is ceilinged by a fixed layout catalog (a
   single collage module can't express 3 props), and its “on-brand” score is partly a measure
   of *co-design with the gate* rather than intrinsic quality. Arm B removes the catalog
   ceiling but loses the automatic gate-safety net.

4. **Therefore: adopt the hybrid** the brief hypothesises — a **structured contract →
   deterministic renderer, using an HTML-first reference to expand the renderer's vocabulary.**
   Concretely: (a) add a real brief-driven entrypoint (`plan.json` → `compose_page`) so
   “brief-driven” is first-class, not manual; (b) grow the `editorial-collage` archetype to a
   **multi-module** variant (the single biggest fidelity gap Arm B exposed); and (c)
   **decouple the gate from delivery mechanism** — accept self-hosted `@font-face` as a webfont
   and treat a real underline `<input>` as compliant when it is visibly unboxed — so the gate
   measures on-brand *output*, not the pipeline's implementation fingerprints. That keeps
   Arm A's consistency and gate-safety while capturing Arm B's structural richness.

---

## Artifacts (absolute paths)

- Arm A HTML: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/woodwave-ab/arm-a-structured/index.html`
- Arm A screenshot: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/woodwave-ab/arm-a-structured/assets/_preview.png`
- Arm A gate report: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/woodwave-ab/arm-a-structured/onbrand-report.md`
- Arm B HTML: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/woodwave-ab/arm-b-html/index.html`
- Arm B screenshot: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/woodwave-ab/arm-b-html/assets/_preview.png`
- Arm B gate report: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/woodwave-ab/arm-b-html/onbrand-report.md`
- Inputs snapshot: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/woodwave-ab/inputs/`
- Arm A generator: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/woodwave-ab/gen_arm_a.py`
- Reveal-safe screenshot script: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/experiments/woodwave-ab/shoot_reveal_safe.mjs`

### Reproduce

```bash
cd /Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine
# Arm A (structured)
python3 experiments/woodwave-ab/gen_arm_a.py
# Gate both arms
python3 brand_pipeline/onbrand_check.py experiments/woodwave-ab/inputs/brand.yaml \
  experiments/woodwave-ab/arm-a-structured --layout opening-bookend --style editorial-luxury
python3 brand_pipeline/onbrand_check.py experiments/woodwave-ab/inputs/brand.yaml \
  experiments/woodwave-ab/arm-b-html --layout opening-bookend --style editorial-luxury
# Screenshot both arms (reveal-safe, fair to both)
node experiments/woodwave-ab/shoot_reveal_safe.mjs experiments/woodwave-ab/arm-a-structured/index.html experiments/woodwave-ab/arm-a-structured/assets/_preview.png 1440 900
node experiments/woodwave-ab/shoot_reveal_safe.mjs experiments/woodwave-ab/arm-b-html/index.html experiments/woodwave-ab/arm-b-html/assets/_preview.png 1440 900
```

> Note on screenshots: both pages use an IntersectionObserver scroll-reveal that leaves
> below-fold content at `opacity:0` in a naive `fullPage` capture. Both honour
> `prefers-reduced-motion: reduce` by skipping the reveal, so the previews are captured with
> reduced-motion emulation — applied identically to both arms, so the comparison stays fair.
