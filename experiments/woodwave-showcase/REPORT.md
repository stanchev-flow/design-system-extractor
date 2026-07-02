# WoodWave — Full Variation Showcase

One comprehensive run rendering **every variation axis the pipeline can currently
express** for WoodWave, published as Studio lanes. Built by
`experiments/woodwave-showcase/build_showcase.py` — no pipeline code, brand.yaml,
layout-library.yaml, or styles/*.md was modified. All content came through the real
pipeline (deterministic composers or the live LLM composition path); no hand-authored
HTML or composition.v1 JSON.

## 1 · The variation matrix inventoried

| Axis | Values found (from code/config, not guessed) |
|---|---|
| **Base styles** (offGridExpansion: true) | `radical-editorial`, `editorial-luxury` (`corporate-saas-clean` exists but is the flag-off control, not a WoodWave identity) |
| **Layout patterns — project tier** | 14 patterns in `runs/woodwave/brand/layout-library.yaml`, incl. harvested `features-staggered-caption-cards` (#04) and `editorial-interlocking-inset` (#11) |
| **Layout patterns — standard tier** | 27 patterns in `brand_pipeline/contracts/layout-patterns/*.yaml` across 8 use-cases |
| **Archetype composers** (`ARCHETYPE_COMPOSERS`) | `stack` (hero + conversion sub-composers), `collage` (ghost-word + ghost-numerals), `split` (info-band / mission-statement / curator-quote / visit-band by patternRef), `stack-fullbleed`, `cards`, `interlock`, `generic-flow` (safety net) |
| **Non-drawable archetypes** (degrade to generic-flow) | `row`, `grid`, `bento`, `band`, `overlay` — pending the grid/overlap contract + harvest work |
| **Treatment kinds** | `ghost-word`, `stagger`, `overlap`, `bleed`, `float-wrap`, `inset` (+ `text-on-media`, unsanctioned for WoodWave: neverDo *no text on photos*) |
| **Section-tunable levers today** | alignment anchor (center/left/right), interlock float side (left/right), cards module count (2/3), ghost word vs numerals, split sub-composer routing, gallery counter. Most `variantKnobs` are pattern **defaults**, not yet runtime-tunable |
| **offGridExpansion** | style-identity flag; ON for both editorial styles, forceable OFF per run in `generate_composition.py` |
| **Hybrid live generation** | `generate_composition.py` → composition.v1 → `compose_from_composition.py` (LLM, gate-repaired) |
| **Anchored hero variants** | `experiments/woodwave-hero-gallery/build_anchored_variants.py` — 6 measured variants of the original hero |

## 2 · Lanes published (all verified HTTP 200 on studio_server :1500)

| Lane | Content | Gate |
|---|---|---|
| WoodWave — all patterns · project tier (radical-editorial) | 15 sections: all 14 project patterns + auto footer | PASS |
| WoodWave — all patterns · project tier (editorial-luxury) | 15 sections | PASS |
| WoodWave — all patterns · standard tier (radical-editorial) | 28 sections: measured hero + all 27 standard patterns, 0 excluded | PASS (`--composition`) |
| WoodWave — all patterns · standard tier (editorial-luxury) | 28 sections, 0 excluded | PASS (`--composition`) |
| WoodWave — archetype × treatment sampler (editorial-luxury) | 11 sections: hero baseline · conversion center/left · collage ghost-word/numerals · split info-band · gallery band · cards ×2/×3 · interlock right/left | PASS (`--composition`) |
| WoodWave — hybrid live seed on-1…on-5 (off-grid ON) | 8–9 LLM sections each; on-2/3/5 contain `novelty:novel` sections | 5/5 PASS (`--composition`) |
| WoodWave — hybrid live seed off-1, off-2 (off-grid OFF, contrast) | 9 LLM sections each; off-grid treatments correctly refused by the prefilter | 2/2 PASS (`--composition`) |
| WoodWave — anchored hero variants (built-in hero_gallery lane) | original + 5 anchored variants, re-stitched | 6/6 standalone PASS; assembled comparison stitch fails `single-accent` **by construction** (6 heroes on one page — the documented hero-gallery artifact, not a regression) |

Deterministic pattern pages use quiet caption-scale divider labels (the hero-gallery
divider convention, injected as a post-render CSS shim — never display-tier type).

## 3 · Gate summary

- **Pages gated:** 4 pattern pages + 1 sampler + 7 hybrid renders + anchored (6 standalone + 1 stitch).
- **Pass:** 4/4 patterns, 1/1 sampler, 7/7 hybrid, 6/6 anchored standalone. **Zero sections excluded** from any lane.
- **Known-red kept out of "green" claims:** the anchored *comparison stitch* (single-accent, expected for a 6-hero page).
- Notable mid-run repairs (all inside the sanctioned harness layer, `experiments/` only):
  - `_split_copy` translator completion (in-memory wrapper): seeded splits routing to
    `compose_about_statement` / `compose_curator_quote` / `compose_visit_band` crashed
    with `KeyError: 'body'` — the wrapper surfaces the section's own LLM slot copy
    (statement text / quote / attribution) and aliases visit-band keys. No pipeline file
    edited; no copy invented.
  - Referenced-but-uncopied real brand assets (e.g. `About-img-3.jpg`, present in
    `runs/woodwave/brand/assets/` but outside `ASSET_SOURCES`) are copied into the page's
    `assets/` post-render so the gate's asset-presence rows see the real file.
  - Divider shim originally used a `border-top` hairline → tripped `no-section-hairlines`; removed.
  - Multi-accent on stitched catalog pages → non-first inverse sections render `primary` (single-accent invariant holds page-wide).
  - Live seeds on-2 and off-1 initially failed `single-accent` in generation; **fresh LLM runs** (gate-repair loop) fixed both — on-2 self-repaired on attempt 2, off-1 passed attempt 1.

## 4 · Font verification (Melodrama self-hosted)

All 13 lanes verified: `@font-face 'Melodrama'` present, per-weight faces incl.
**400** (section headings) and **500** (`--c-display-weight: 500`, hero), and
`Melodrama-Regular.woff2` + `Melodrama-Medium.woff2` on disk in each lane's `assets/`.
Visual check on screenshots (didone display headings render correctly) — see `shots/`.

## 5 · Axes NOT yet expressible (deferred to in-flight contract work)

- **Archetypes without composers:** `row`, `grid`, `bento`, `band`, `overlay` — the 5
  standard-tier archetypes render through the `generic-flow` safety net (labeled as such
  on the standard-tier pages). Pending the grid/overlap contract upgrade + harvest.
- **Runtime variant knobs:** most `variantKnobs` (`columnRatio`, `cardStagger`,
  `insetWidth`, aspect knobs…) are pattern defaults consumed at pattern-resolution time,
  not per-section levers a composition can set. The sampler shows the levers that ARE
  live today.
- **`text-on-media` treatment:** unsanctioned for WoodWave (neverDo *no text over
  photos*) — deliberately filtered everywhere.
- **Placed-media hero geometry (§4.6.5)** beyond the anchored variants: partially
  expressible; full per-slot placement vocabulary is part of the same in-flight contract.

## 6 · Artifacts

- Pages: `experiments/woodwave-showcase/pages/` · hybrids: `experiments/woodwave-showcase/hybrid/`
- Screenshots: `experiments/woodwave-showcase/shots/` (one per lane)
- Machine-readable results: `experiments/woodwave-showcase/results.json`
- Lanes: `runs/woodwave/brand/variants/showcase-*` (symlinks + label.txt, auto-versioned by studio_server)
