# Section Recipe Catalog

This directory contains brand-agnostic structural recipes compiled from component
libraries. It stores abstractions and source metadata, not third-party component code.

## Product role and boundaries

Relume is a **content-structure baseline** for generating new pages. It contributes
conventional section purposes, content anatomy, layout skeletons, ingredient options,
interaction families, and responsive mechanics. It is not a visual-style source and it
is not a template collection to reproduce.

The compiler keeps raw evidence separate from a strict prompt projection. Prompt/runtime
recipes contain no colors, typography, concrete spacing or geometry, CSS units,
queries, class names, preview URLs, copy, assets, or icons. Selection precedence is:

1. measured brand patterns and recipes
2. designed-from-brand components and patterns
3. compatible brand/style archetypes
4. Relume structural fallback, only for a still-unsupported section job

Relume's coverage is intentionally described as biased toward conventional SaaS,
marketing, and application UI structures. The 50-category inventory does **not** claim
editorial, experimental, art-directed, or other high-variance structural coverage.

Editorial and other high-variance corpora should remain separate genre libraries,
curated from real examples with explicit provenance, physics bindings, and slop traps.
Their candidates may be merged with Relume candidates at selection time. They must not
be folded into or used to cosmetically broaden the Relume baseline.

## Relume import

`inventory/*.json` records the category, slug, tags, and preview URL returned by the
authenticated Relume Library MCP:

```json
{
  "schemaVersion": "relume-inventory.v1",
  "categories": [
    {
      "slug": "feature-sections",
      "name": "Feature Sections",
      "components": [
        {
          "slug": "layout635",
          "name": "Layout 635",
          "tags": ["2 Columns", "Image/Video Right", "Buttons", "Image"],
          "preview": "https://..."
        }
      ]
    }
  ]
}
```

Run:

```sh
./venv/bin/python brand_pipeline/relume_recipe_catalog.py
```

The compiler writes raw `catalog.generated.yaml`, prompt-safe
`catalog.structural.yaml`, `coverage.generated.json`, and `coverage.generated.md`.
The structural projection is the only catalog loaded for prompt selection. Its
normalization rules:

- Left/right mirrors become one recipe with a `mediaSide` axis.
- Image/video/multiple-image differences become `mediaMode` ingredients.
- Icons, lists, logos, ratings, and actions become optional ingredient axes.
- Structural differences such as split, grid, carousel, tabs, overlay, collage, and
  stack remain distinct recipe families.
- Every source slug remains attached as provenance for coverage and later inspection.
- Breakpoint queries become semantic tiers (for example the observed 991-pixel query
  becomes `lg`); source query text is removed.
- Dialog widths become `containerWidth: medium/large`; long viewport stages become
  `scrollStage: long/extended`; viewport-minus-header calculations become
  `viewportHeight: viewport-minus-header`.
- Unknown literal lengths are omitted. A recursive scanner fails catalog generation and
  prompt injection if a visual/source key, CSS unit, color, calculation, query, or URL
  survives.
- Prompt retrieval is capped at three candidates total.

Composition generation keeps the resolver behind
`enable_relume_fallback=False`. Enabling it does not bypass precedence or scanner
gates; explicit empty guidance remains the control/opt-out path.

## Responsive evidence

Responsiveness is part of the recipe contract, not a generic afterthought. Representative
TSX for every normalized family is inspected for:

- breakpoint column/flex transitions and ordering
- hidden/shown controls and CTA duplication
- menu, dropdown, disclosure, tab, dialog, filter, and carousel interaction changes
- overflow, clipped peeks, sticky/full-height mechanics
- media aspect, basis, crop, and sizing transitions
- navigation desktop/mobile anatomy and mega-menu behavior
- footer column, newsletter, social, legal, contact, and brand-art rows

The temporary MCP source responses are compiled with:

```sh
./venv/bin/python brand_pipeline/relume_responsive_parser.py <mcp-response.txt> [...]
```

`responsive-evidence.yaml` is raw provenance evidence and may retain exact inspected
mechanics. It is never prompt input. Third-party TSX is not stored. The generated
structural projection strips source classes and concrete values before selection;
all 132 families must pass its scanner. The checked-in catalog currently requires zero
pending recipe families.

Metadata-derived recipes remain structural priors. Responsive source inspection makes
their behavior explicit, but deterministic renderer promotion still requires contract
mapping and gate coverage.
