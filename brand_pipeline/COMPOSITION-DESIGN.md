# Section composition from the catalog — design report (thin slice)

Status: **working end-to-end slice landed + green gate.** This documents the gap, the
composition architecture, what shipped, the proof, and how it rolls out to every layout
and to `compose_page.py`.

## 1. Current-flow gap (before this change)

There were **three** rendering pipelines, and each **hand-built bespoke markup**:

| file | what it does | reuses catalog renderers? |
|---|---|---|
| `render_section.py` | `build_document` dispatches on `renderKind` (`collage`/`hero-cta`/`cta-stack`) to `build_*` fns; each emits a full hand-written HTML+CSS section. Plus `build_fragment_*` for `compose_page`. | **No** — every `build_*`/`build_fragment_*` re-writes heading/eyebrow/image/link markup inline. |
| `render_hero_variants.py` | bespoke `hv-*` hero (A/B/C dial, style-aware). | **No** |
| `render_components_preview.py` | the gallery — has **one renderer per primitive/block** (`render_heading`, `render_eyebrow`, `render_image`, `render_link`/`render_cta`, `render_b_header`, …). | these ARE the per-component renderers we want to reuse, but only the gallery called them. |

A `layout` in `brand.yaml` already describes structure the right way — `archetype` + named
`slots[]` + a `blockMapping[]` of `{slot, role, contract, usage}`, where `contract` names a
catalog entry (`logo`, `header`, `image`, `link`, …) and the `primitives:`/`blocks:` catalog
carries each entry's `origin`/`use`/`rules`/`variant`. **But no code resolved a slot to its
catalog entry and rendered THAT component.** Sections ignored the catalog and hand-wrote
markup keyed on `renderKind`/`archetype`. Consequence: editing a catalog primitive changed
**only** the gallery, never any composed section — the catalog was not the source of truth.

## 2. The composition architecture (what we built)

```
brand.yaml layout                       component_render.py (SSOT)
  archetype + slots[]                      one renderer per catalog component
  blockMapping[] {slot,role,                 render_heading / render_eyebrow /
     contract, usage}                        render_image / render_arrow_link (cta+link) /
        │                                     render_logo / render_header / render_navbar
        │  contract ──► resolve_renderer(contract) ──┐
        ▼                                             ▼
  compose_section.py  ── for each slot, render the bound component ──►  assemble per archetype
                                                                        (positions / overlap / grid)
                                              ▲
                       render_components_preview.py (gallery) imports the SAME renderers
```

**Slot → component binding contract.** A `blockMapping[]` entry is the binding:
`contract` (which catalog component) + `usage` (its props) + `role`/`slot` (where it lands).
`component_render.resolve_renderer(contract)` maps the contract key to the shared renderer;
`compose_section._props_for(role, usage)` turns `usage` + section copy into the renderer's
`props`. So the binding is **data**, not code.

**One renderer per component (single source of truth).** `component_render.py` owns exactly
one function per catalog component. Each takes `(doc, ctx, props)` and returns HTML built from
shared `c-*` classes; the shared stylesheet is emitted once (`COMPONENT_CSS`), and per-surface
token VALUES are emitted as CSS vars so the *same* classes read on-brand on a dark hero band
**or** the cream gallery canvas. Both the gallery and the composer import these — so editing
one renderer changes every composed section **and** the gallery at once.

**Style precedence preserved.** The composer reuses `styles.py` `load_and_merge`; with
`--style`, the merged STYLE structure (radius, display scale, leading/tracking, density,
single-accent deployment) is appended **after** the brand base in CSS source order, so the
load-bearing style rules win while brand keeps hues+fonts. Default (no `--style`) path is
unchanged.

**Iframe-safe.** Container-query units only (`cqw/cqh/cqi` against `container-type:size`);
never `vh/vw/dvh`. Verified by grep (0 matches) on the composed + styled outputs.

## 3. Files created / edited

- **NEW `brand_pipeline/component_render.py`** (290 lines) — the SSOT. `ComponentContext` +
  `make_context` (57–80); `component_vars` per-surface vars (83–128); `COMPONENT_CSS` shared
  stylesheet (130–181, radius via gate-whitelisted `var(--radius)`); renderers `render_heading`/
  `render_eyebrow`/`render_image`/`render_arrow_link`/`render_logo`/`render_header`/
  `render_navbar` (184–269); registry `PRIMITIVE_RENDERERS`/`BLOCK_RENDERERS` +
  `resolve_renderer` (272–290).
- **NEW `brand_pipeline/compose_section.py`** — `resolve_surface_intent` (honors v2
  `surfaceIntent`), `loadable_proxies`, `_props_for` (role→props), `render_slots` (slot→catalog
  render loop), `compose_stack_hero` (archetype assembler) + `ARCHETYPE_COMPOSERS`,
  `scaffold_css`, `style_override_css`, `root_vars` (gate-readable legacy vars + `--c-*`
  aliases), `build_document`, CLI `main`.
- **EDIT `brand_pipeline/render_components_preview.py`** — imports `component_render as cr`;
  added `_GALLERY_CTX` + `COMPONENT_ALIAS_CSS` (maps `--c-*` onto the gallery's vars, accent
  pinned to ink on the light canvas); `render_heading`/`render_eyebrow`/`render_image`/
  `render_link`/`render_cta`/`render_b_header` now delegate to the shared renderers; page
  `<style>` now includes `COMPONENT_ALIAS_CSS` + `cr.COMPONENT_CSS`. 61 cards unchanged.
- **UNTOUCHED**: `render_section.py`, `render_hero_variants.py`, `styles.py`, `onbrand_check.py`,
  `studio_server.py`, and the entire chrome pipeline.

## 4. Proof

- Composed hero: `runs/woodwave/brand/render/composed-opening-bookend/index.html` —
  every slot resolved to a catalog component (`logo→render_logo`, `header→render_header`,
  `image→render_image` ×2; nav composes the logo primitive).
- On-brand gate (`onbrand_check.py --layout opening-bookend`): **OVERALL PASS** — neverDo PASS
  (all 11), Fidelity PASS, Slop PASS. 0 viewport units; container-query units present.
- **Reuse demonstration**: a one-line edit to the catalog primitive `render_arrow_link`
  (`&rarr;`→`&rarr;&rarr;` + a `data-reuse-demo` marker) propagated to **both** the composed
  section (2 ctas: nav + foot) **and** the gallery (3 ctas: link/cta/header) on re-render —
  proving the section is assembled from the catalog, not bespoke markup. Reverted cleanly; gate
  still PASS.

## 5. Rollout to all WoodWave layouts + `compose_page.py`

The thin slice implements the `stack` archetype (opening-bookend). To cover the rest:

1. **Add archetype assemblers** to `ARCHETYPE_COMPOSERS`, one per archetype, each consuming the
   generic `render_slots(...)` output and arranging fragments per the layout's `gridRules`/
   `overlapRules`/`widthRules`:
   - `collage` → editorial-collage: alternating-anchor `content-block` modules over the ghost
     watermark (z-order `ghost → media → text`).
   - `split` → info-band: two flush halves (`image` | cream `panel` of `header`+`link` rows).
   - `stack` (narrow) → conversion-stack: centered `header` + underline `form`.
2. **Add the remaining shared renderers** to `component_render.py` (`paragraph`, `form`/`input`,
   `divider`, the `content-block`/`media-text`/`cta-block`/`form` blocks). The gallery's
   existing bespoke stages are the reference implementations to fold in — finish migrating them
   so there is exactly one renderer per catalog key. Until then `resolve_renderer` returns
   `None` and the composer emits a typed `<!-- unresolved slot -->` (no crash), so migration is
   incremental.
3. **`compose_page.py` page flow**: today it concatenates `render_section.build_fragment_*`
   fragments. Re-point each selected section to `compose_section.build_document`'s section body
   (factor the `<section>…</section>` builder out of `build_document` so the page can request a
   fragment without the full `<html>` wrapper), bind the brief copy into `_props_for` (replace
   the `SECTION_COPY` constant with the brief's per-slot copy), and keep one shared
   `component_vars`/`COMPONENT_CSS` block for the whole page. Net: the page becomes a list of
   layouts, each composed from the same catalog — chrome (navbar/footer) stays owned by the
   chrome pipeline.

## 6. Proposed `brand.yaml` slot-binding shape (propose, do NOT mass-edit)

`blockMapping[]` already carries the binding; two small **additive** refinements make it fully
explicit and copy-driven (apply atomically: temp → `yaml.safe_load` validate → `os.replace`):

```yaml
# in each layouts[].blockMapping entry — add an explicit `bind` + named copy key:
- slot: main
  role: display title
  contract: header          # catalog key resolved by resolve_renderer()
  bind:                     # NEW (optional): pin the variant/level the slot wants
    level: display
    accent: onDark          # or a token role; composer maps onDark→accent on inverse
  copy: hero.heading        # NEW (optional): reference into the brief/section copy map
  usage: { heading: "WOODWAVE GALLERY", level: display, case: upper }  # fallback copy (unchanged)
```

- `bind` makes the slot's component variant explicit instead of inferred from `role` keywords
  (removes `_props_for`'s heuristics over time).
- `copy` lets the page composer inject brief copy by key (decouples copy from the layout),
  while `usage` remains the inline fallback so today's renders are unaffected.
- No schema break: `compose_section` reads `bind`/`copy` when present and falls back to
  `usage` + `role` heuristics otherwise. Nothing else in the file changes.
