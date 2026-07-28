# greenhouse-v2 — Brand Harness / Spec-Book (RAW renderer)

Status: **HELD FOR REVIEW — not committed.** Render/assembly task only; no shared
renderer/pipeline source files were edited.

## How it was built

- Generator: `brand_pipeline/render_components_preview.py` (the repo's canonical
  three-tier harness / spec-book renderer — Tier 0 spec book + Tier 2 primitives/blocks
  gallery + Tier 3 composed layouts).
- Invocation (read-only consumption of the validated Stage-1 facts):

```bash
./venv/bin/python brand_pipeline/render_components_preview.py \
  runs/greenhouse-v2/brand/brand.yaml \
  -o runs/greenhouse-v2/brand/harness
```

- Screenshots: standalone Playwright capture, Chromium, viewport width **1440**,
  `device_scale_factor=1` (screenshot px == CSS px), full-page after a scroll pass.

## Output paths

- Harness page: `runs/greenhouse-v2/brand/harness/index.html`
- Composed Tier-3 layouts: `runs/greenhouse-v2/brand/harness/layouts/*.html`
- Generated tokens: `runs/greenhouse-v2/brand/harness/tokens.manifest.json`
- Quality gate: `runs/greenhouse-v2/brand/harness/harness-quality.json` (ok: true)
- Screenshots (@1440): `runs/greenhouse-v2/brand/harness/shots/*.png`

> Written to the dedicated `harness/` dir (not `components-preview/`, not `sections/`)
> to avoid collisions with the concurrent relume (main, render-only) and shadcn
> (isolated worktree) workers. `viewer.html` was intentionally NOT regenerated (parent
> will regen once after all workers finish).

## Coverage

All exhibits render from the validated Stage-1 `brand.yaml` and cite their
`brand.yaml` source keys (monospace) in-page — provenance is on every exhibit.

### Tier 1 — Primitives (spec book): 7/7 chapters, 0 invented values
- **color** — 14 tokens across 4 families (`tokens.colors.text/*`, `accent/*`,
  `surface/*`, `border/*`), e.g. text/primary `#15372c`, accent/primary `#008561`,
  accent/secondary `#3574d6`, surface/canvas `#ffffff`, surface/inverse `#15372c`.
- **type** — 10 roles, Untitled Serif display/heading + Untitled Sans body, authored
  tier ladders with measured px stamps per breakpoint (`tokens.type.<role>`), specimen
  set in each role's own register.
- **spacing** — relational X-to-Y rungs as true-size gap bars.
- **radius** — brand pill radius exhibited (24–25px family → `radius` tokens).
- **motion** — duration/easing/signature-move ladders + live timing demos.
- **buttons × surfaces** — one band per declared surface role (6 roles:
  `surface/primary, tint, muted, inverse, panel, inverse-strong`), each carrying every
  button family's state row. Button families rendered: **primary-green `#008561`,
  primary-blue `#3574d6`, outline-dark, outline-white, text-green** (pill radius 24px).
- **recipes** — spec recipes chapter present.
- Form controls rendered as primitives: input, form-field, textarea, select, checkbox,
  radio, toggle, slider, file-upload (7 action elements carry live state matrices:
  button, link, cta, input, toggle, checkbox, icon-button).

### Tier 2 — Components: 36 primitives + 31 blocks rendered
Each carries a NAME, an origin BADGE (solid = extracted / observed on page; dashed
"synthesized" = designed / not-used-on-page), the universal intent, and a faithful
rendered example (+ state matrix for interactive kinds).

- primitives (36): heading, subheading, eyebrow, paragraph, label, button, link, cta,
  image, icon, logo, pill, badge, input, form-field, toggle, select, checkbox, radio,
  quote, avatar, rating, video, divider, stat, caption, list, code, icon-button,
  illustration, progress, tooltip, spacer, textarea, slider, file-upload.
- blocks (31): hero, featureGrid, logos, comparison, stats, testimonial, ctaBand,
  footer, header, content-block, card, form, stat-block, navbar, accordion,
  accordion-item, tabs, logo-bar, feature-item, pricing-card, banner, modal,
  dropdown-menu, breadcrumb, pagination, table, carousel, steps, step-item, cta-block,
  media-text — covering the requested buttons, two-tier nav/chrome, footer, cards,
  floating product-UI cards, testimonial cards, comparison module, logo wall, stats
  band, and badges.

### Tier 3 — Section layouts: 7/7 captured archetypes composed
Composed through the real ARCHETYPE_COMPOSERS into `layouts/<id>.html` (+ 35
standard-tier patterns listed): **hero, featureGrid, logos, comparison, stats,
testimonial, ctaBand**.

## Per-band render fidelity (from @1440 shots)

| Band | Fidelity | Notes |
|------|----------|-------|
| hero | strong | full 1440×2471 render |
| comparison | strong | tint surface, serif heading, arrow-link CTA, **floating product-UI cards** (pill-on-photo + report-builder card w/ green bar chart) and connector lines all render |
| ctaBand | good | dark forest-green bookend surface + emerald accent-on-dark heading + arrow link (surface/inverse + accent-on-dark rule validated) |
| featureGrid | **LOW** | single left-column text stack; right ~60% dead; a partner logo (REVLON) mis-slotted into the media slot |
| testimonial | **LOW** | single left-column quote stack; right ~60% dead; no card chrome / no multi-up card grid |
| stats | **LOW** | single left-column stack; big stat numerals rendered at tiny eyebrow scale (grey) instead of display numerals; right ~75% dead |
| logos | **LOW** | serif heading + arrow link + only a SINGLE logo; no logo-wall row/grid of the captured logo set |

## Renderer gaps observed (REPORT ONLY — not fixed, per no-source-edit constraint)

These are archetype-composer / raw-renderer gaps, not fact gaps (Stage-1 facts are
complete and C1–C28 clean). Common failure shape: archetypes that need a horizontal
multi-item row or a populated media/right column collapse into a single left column
with the repeat/media slots under-rendered.

1. **featureGrid low-fidelity band** — feature items stack in one left column; the
   media/right region is empty and a partner logo is mis-slotted into it. Expected:
   a multi-up feature grid with per-item media at the brand radius.
2. **testimonial low-fidelity band** — testimonials stack as left-column quotes with no
   card container and a dead right column. Expected: multi-up testimonial cards with
   card chrome/attribution/avatar.
3. **stats band numerals** — the big stat value renders at eyebrow scale in grey rather
   than as a large display numeral, and the band is single-column. Expected: a 3-up
   stats row with display-scale numerals.
4. **logo wall single-logo** — only one logo renders instead of the captured logo set
   arranged as a wall/row.

Strong renders (hero, comparison floating-card cluster, ctaBand inverse bookend)
confirm the token layer, surface roles, pill-button families, and floating product-UI
card archetype are all faithful; the gaps are concentrated in the row/grid/media
composers noted above.
