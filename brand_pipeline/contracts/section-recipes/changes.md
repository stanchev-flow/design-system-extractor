# Changes

## 2026-07-19 — Structure-only projection and fallback precedence

- Added `catalog.structural.yaml` as the only prompt-facing projection of the raw
  catalog/evidence. It retains section jobs, skeletons, semantic slots/axes and
  responsive topology, plus recipe-id provenance.
- Normalized observed source geometry before projection: 991-pixel queries to `lg`,
  738/940-pixel dialog measures to medium/large container classes, 200/400 viewport
  stages to long/extended, and viewport calculations to `viewport-minus-header`.
- Added a recursive fail-closed scanner for visual/source keys, colors, CSS units,
  calculations, queries, URLs, and arbitrary CSS strings. All 132 recipe families scan
  clean; unknown literal lengths are omitted.
- Replaced broad automatic injection with brief-job retrieval that excludes measured
  and compatible archetype support, scores available ingredients, and exposes at most
  three candidates total.
- Added machine-readable composition/wireframe provenance and a hard precedence lint.
- Verification: focused sanitizer, prompt, and wireframe tests: 27 passed; complete
  `brand_pipeline/tests`: 1,643 passed with 8 existing Pillow warnings.

## 2026-07-17 — Relume recipe import

- Added the `section-recipes.v1` compiler and the 50-category Relume taxonomy bridge.
- Added an inventory format for MCP-returned component metadata.
- Normalized mirrored layouts, media substitutions, and optional ingredients into
  variant axes instead of separate templates.
- Kept Relume source code out of the repository; only metadata and structural
  abstractions are stored.
- Made the product boundary explicit in schema, generated data, prompt guidance, and
  documentation: Relume is a content-structure baseline, never a visual style source or
  a template collection to reproduce.
- The responsive parser strips source class names and ignores colors, typography,
  spacing, fixed visual dimensions, radii, shadows, and aesthetic defaults. Active brand
  facts and style structure always precede the structural prior.
- Recorded the conventional SaaS/marketing/application bias and the lack of claimed
  editorial/experimental coverage. Curated high-variance examples remain separate genre
  corpora with provenance and physics, merged only during candidate selection.
- Inventoried all 50 MCP categories and 1,757 component slugs into ten metadata shards.
- Compiled 132 recipe families with zero duplicate slugs.
- Added first-class responsive evidence and a deterministic TSX response parser covering
  column/order changes, visibility, overflow, carousel basis, media behavior, sticky/full-
  height mechanics, and breakpoint-specific interactions.
- Inspected at least one representative TSX source for all 132 recipe families; coverage
  reports show zero responsive-source-pending families.
- Added dedicated navigation families (`standard-nav`, `mega-menu`, `overlay-menu`) and
  footer families (`newsletter-columns`, `contact-columns`, `compact-centered`,
  `inset-columns`, `link-columns`) with desktop/mobile anatomy and transition rules.
- Confirmed all 17 footer sources keep link groups expanded rather than converting them
  to mobile accordions; this absence is recorded explicitly.
- Added catalog retrieval, use-case matching, prompt guidance rendering, and automatic
  fact-gated composition-prompt injection.
- Generated `catalog.generated.yaml`, `coverage.generated.json`, and
  `coverage.generated.md`.
- Verification:
  - `./venv/bin/python -m pytest tests/test_relume_recipe_catalog.py brand_pipeline/tests/test_relume_recipe_prompt.py -q`
  - `./venv/bin/python brand_pipeline/relume_recipe_catalog.py`
- Follow-up: map newly covered rich section types onto additional deterministic renderer
  contracts instead of degrading them through broad existing builder use-cases.
