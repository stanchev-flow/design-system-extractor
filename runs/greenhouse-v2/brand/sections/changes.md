# runs/greenhouse-v2/brand/sections — change log

On-brand greenhouse-v2 section bake-off driven by the **RELUME structural recipe
catalog** for STRUCTURE and the **measured greenhouse-v2 brand facts** for all
styling / copy / media. 25 sections = 5 types × 5 variations. **Held for review —
not committed.**

## Constraints honoured
- Did **not** edit any shared renderer/pipeline source (`component_render.py`,
  `compose_section.py`, `compose_page.py`, `tokens_css.py`,
  `relume_recipe_catalog.py`, etc.). Nothing imported from them either.
- All output lives under `runs/greenhouse-v2/brand/sections/` (NOT the `harness/`
  area the raw-harness sibling writes to).
- Did **not** regenerate `viewer.html` (parent will do it once at the end).
- Fact-gated + brand-agnostic in construction: tokens are READ from
  `components-preview/tokens.manifest.json`; copy from `section-copy.yaml`; media
  from `media-assets.yaml` (+ `assets/`); button/surface/signature facts from
  `brand.yaml` / `brand-chrome.yaml`. No brand colours/hexes are hand-typed into
  logic — they flow through measured CSS variables.

## The 5 types (default set kept)
Hero, Feature grid, Testimonial, Logo wall, CTA band — all universally reusable
and all present in the greenhouse cross-page inventory with real copy + measured
layout patterns. **No swap.** Stats was the strongest swap candidate (rich RELUME
coverage: `stats-repeated-grid` / `-content-media-split` / `-media-background`,
plus real greenhouse stat copy 25% / 39% / 92%), but Logo wall was retained for
universal reusability. Stat figures were still folded into `testimonial-v1`.

## RELUME recipes used (structure only)
- **Hero**: `hero-media-collage`, `hero-content-media-split`, `hero-content-stack`,
  `hero-media-background`, `hero-repeated-grid` (5 distinct skeletons).
- **Feature**: `feature-repeated-grid`, `feature-content-media-split`,
  `feature-tabs`, `feature-media-collage`, `feature-media-background` (5 distinct).
- **Testimonial**: `testimonial-repeated-grid`, `testimonial-content-media-split`,
  `testimonial-carousel`, `testimonial-content-stack`, `testimonial-media-background`
  (5 distinct).
- **Logo wall**: RELUME only ships **2** skeletons for `logo-wall`
  (`logo-wall-repeated-grid`, `logo-wall-carousel`). Distinctness across the 5
  variations is expressed through the recipe's own declared variant axes
  (`columns` 2/3/4/5, `textAlign`, mirrored orientation) + the brand's MEASURED
  split copy+logo-grid `logos` pattern + surface changes (canvas / tint / muted /
  inverse). v1/v2/v3/v5 = `logo-wall-repeated-grid`; v4 = `logo-wall-carousel`.
- **CTA band**: `cta-content-media-split`, `cta-content-stack`,
  `cta-media-background`, `cta-repeated-grid`, `cta-media-collage` (all 5).

## Signature devices bound (brand.yaml `signatures`)
Pill buttons (radius 24px, pad 12/32, emerald `#008561` / blue `#3574d6` /
outline) · Untitled-Serif sentence-case display with tight negative tracking on a
mint `#c9f0e6` canvas · dark forest `#15372c` bookend bands with decorative
fingerprint-leaf line art (generated inline SVG) · floating white product-UI cards
+ circle-cropped portraits over tinted panels · circular emerald `g` brand badge.
Fonts: measured families (`Untitled Serif`/`Untitled Sans`) are first in the
stack; close free stand-ins **Fraunces** + **Inter** load via Google Fonts for the
review gallery, then the measured `Georgia`/`Arial` fallbacks (see gap note).

## Output layout
```
sections/
  index.html                       # gallery of all 25 (image thumbnails)
  <type>/index.html                # per-type contact sheet (image based)
  <type>/v{1..5}/index.html        # 25 self-contained section pages
  assets/                          # 64 real greenhouse assets (copied)
  shots/                           # 25 per-section + 5 contact + 1 gallery @1440
  _build/{brandkit,generate,capture,build_gallery}.py, manifest.json
```

## Build / verify commands
```
cd runs/greenhouse-v2/brand/sections/_build
../../../../../venv/bin/python generate.py       # 25 pages + manifest
../../../../../venv/bin/python capture.py         # 25 @1440 per-section shots
../../../../../venv/bin/python build_gallery.py   # image gallery + contact sheets + their shots
```
Screenshots require running the venv playwright outside the sandbox (chromium
lives in the sandbox cache; arch differs inside the sandbox).

## Renderer / recipe gaps observed (reported, NOT patched)
1. **RELUME `logo-wall` coverage is thin — only 2 skeletons.** Genuine structural
   variety for logo walls had to come from the recipe's variant axes + the brand's
   measured split pattern, not from distinct RELUME families. Not a bug, a coverage
   limit worth noting for the logo-strip job.
2. **featureGrid (0.18) / testimonial (0.25) harness fidelity drags** flagged in
   the stage-1 replica were a *renderer-path* limitation, not a facts/structure
   limitation: driven directly from the same measured facts + RELUME structure,
   `feature-v1` (3-up media-top cards) and `testimonial-v1` (3-up quote blocks)
   render cleanly and on-brand here. This suggests the drag lives in the
   compose/renderer mapping for those two `cs-*` devices, not in the brand facts.
3. **Carousel / tabs interaction skeletons render as static** (first tab active,
   peek-clipped carousel with controls). RELUME exposes the interaction family but
   the section artifacts here are static HTML by design; no JS interaction layer.
4. **`.gh-body` colour needed a per-section override** on the photographic
   `cta-media-background` variant (muted-ink token is dark; the overlay is dark) —
   handled locally in the standalone generator, would need a surface-aware body
   ink role if promoted.
