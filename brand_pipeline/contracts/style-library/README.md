# Style → Brand → SaaS Site — implementation spec

> provenance: authored-prior (Claude design chat, 2026-07-14) — NOT evidence; requires bakeoff validation before brand use.
>
> Imported 2026-07-14 from the authors' 15-file export (`spec/` zip, "Training on website
> design layouts"). Normalized to ONE canonical format per file (YAML for data, MD for
> docs); the original JSON/MD mirrors were verified content-identical (or projections)
> and dropped. Two content defects were fixed transparently at import (YAML on/off bool
> coercion; `dropddown` slot typo) — see file headers and `INTEGRATION-PLAN.md` §1.
> This package is DATA, not doctrine: nothing here outranks measured brand evidence
> (brand-schema §5.3, Appendix B). Integration status and staging: `INTEGRATION-PLAN.md`.

Build sites from a **style grammar** × a **brand instance**. Rules are *factored*, not enumerated: you author finite catalogs that **compose** at runtime, instead of a style×section mega-matrix.

## The model in one line
```
resolve(section, style, brand) = merge(sectionDefault, styleDirective, override, brandOverride) → bindTokens
```

## File map
| File | Cascade level | What it is |
|---|---|---|
| `pipeline.yaml` | — | The authors' 7-stage agent pipeline (intake → ship). Package doc — NOT our pipeline. |
| `token-schema.yaml` | — | Style grammar + brand instance keys (source of truth shape). |
| `resolution-model.md` | engine | The 4-level cascade, merge semantics, locked invariants, algorithm. |
| `sections/catalog.yaml` | **1** | Every section: slots, allowed layouts, invariants, variation axes. |
| `styles/directives.yaml` | **2** | Every style: constraints + layout bias + signatures. |
| `overrides/overrides.yaml` | **3** | Sparse (style × section) patches — only pairs that break defaults. |
| `variations/axes.yaml` | — | Global variation knobs. Per-section knobs live in `sections/catalog.yaml` `variationAxes` (deduplicated at import; verified identical 21/21). |
| `layouts/primitives.yaml` | — | The layout patterns sections reference. |

## Why this shape
- **Author `styles + sections`, not `styles × sections`.** 21 sections + 51 styles ≈ 72 authored units, not 1071+ matrix cells.
- **Cascade + per-key merge** means specializations are tiny patches, never re-authored sections.
- **Locked invariants** keep every resolution purposeful (a hero always has one primary CTA).
- **Variations are free** — perturb one axis, re-resolve; results are valid by construction.

## Implementation order
1. Load `layouts/primitives.yaml` + `sections/catalog.yaml` (level 1).
2. Load `styles/directives.yaml` (level 2).
3. Implement `resolve()` per `resolution-model.md` (merge + invariant assertion).
4. Wire `overrides/overrides.yaml` (level 3) and brand overrides (level 4).
5. Compose pages = ordered list of resolved sections → render with bound tokens.
6. Run stage-05 gates; on invariant/gate failure, repair and re-resolve.

Counts: **21 sections**, **51 styles**, **17 layout primitives**.
