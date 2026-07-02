# Brand Pipeline — Design Language Spec (overview)

> **Status: design / for review — NOT implemented.** These four documents specify a
> proposed evolution of the brand pipeline. Nothing here changes
> `run_brand_pipeline.py` or any runtime, and nothing touches the live Webflow site.
> All component names/ids and token values in the examples are real, sourced from
> `.cursor/skills/webflow-library-aisb/` and `runs/woodwave/brand/`.

## What this is

A spec for turning a captured site into a **canonical, self-correcting, library-AGNOSTIC
design language** (`brand.yaml`) that any render substrate can project.

### Pipeline vocabulary (standard names used across all specs/skills)

```
Brand Extractor (pipeline)
   ├─ Layout Analyst  — skill `brand-layout-analyst` (extracts brand.yaml, emits creation signals)
   └─ Art Director    — skill `brand-art-director` (OWNS brand.yaml/brand.md + do[]/avoid[]/neverDo[] + signal loop)

DEFERRED:  Page Composer (compose_page.py)  •  Webflow Assembler (webflow-library-aisb + MCP)
```

**Render substrate:** the build target **NOW** is **static Tailwind + shadcn** (HTML on
a Tailwind CDN). The **Webflow Assembler is DEFERRED**. `brand.yaml` stays library-agnostic;
the Tailwind/shadcn renderer maps intent → classes, and the future Webflow Assembler maps
the same intent → components. Substrate-specific ids live only in the optional, non-canonical
`targetMappings:` block — never on canonical nodes.

| file | what it specifies |
|---|---|
| [`brand-schema.md`](brand-schema.md) | The canonical, library-agnostic `brand.yaml` schema (tokens=intent+value, surfaceGrammar, **contracts** layer, brand `primitives[]`/`blocks[]` overrides, layouts[], compositionRules, the **three rule lists `do[]`/`avoid[]`/`neverDo[]`**, voice, recipePolicy, optional non-canonical `targetMappings`), the universal rule envelope, a filled-in **WoodWave** `brand.yaml`, and the rendered `brand.md`. |
| [`layout-analyst-skill.md`](layout-analyst-skill.md) | The **Layout Analyst** skill (`brand-layout-analyst`) any agent can invoke. 4-phase method: segmentation → archetype extraction → slot/contract mapping → rule synthesis. Archetypes are library-agnostic shapes; includes reuse-before-create / compose-from-primitives gap handling. |
| [`signal-loop.md`](signal-loop.md) | The **Art Director's** self-education loop: `signals.log` (JSONL), three signal sources (creation / iteration / build-failure), the consolidation pass (confirm-before-promote design-language promotion with changelog), and the contradiction protocol (one-off-and-queue default + question template + `pending-questions.yaml`). |
| [`../contracts/primitives.yaml`](../contracts/primitives.yaml) · [`blocks.yaml`](../contracts/blocks.yaml) | The shared **universal vocabulary** — atomic primitives and composed blocks, each defined ONCE (intent + props + recursive slots). Brands override, never redefine. |

## Three honored design decisions

1. **Layout Analyst is a skill, not a pipeline step.** Any agent invokes
   `brand-layout-analyst` (frontmatter + body, create-skill conventions). It is not
   a hardcoded stage in `run_brand_pipeline.py`.
2. **`brand.yaml` is canonical; `brand.md` is a rendered projection.**
   `render_brand_md(brand.yaml) → brand.md` is a pure, deterministic function.
   `brand.md` is never hand-edited; a drift check is a **WARNING, not a build blocker**
   (SIGN-OFF #1) — re-render to resolve.
3. **Contradictions default to one-off-and-queue.** When a signal contradicts an
   existing rule and the user hasn't responded: apply once (`scope: one-off`), do
   NOT auto-promote, do NOT block — queue the clarifying question and keep going.

## Data flow

```
   capture (screenshots + DOM)
        │
        ▼
  ┌─────────────────────┐    creation signals
  │ brand-layout-analyst │ ───────────────────┐
  │   skill (4 phases)   │                     ▼
  └─────────┬───────────┘             ┌──────────────────┐
            │ writes (canonical)      │   signals.log    │  ◄── iteration signals (human edits)
            ▼                         │     (JSONL)      │  ◄── build-failure signals (assembler/Webflow)
      ┌───────────┐                   └────────┬─────────┘
      │ brand.yaml │ ◄───────────────────────── │  consolidation pass
      │ (canonical)│   promote high-confidence  │  (promotion gate + changelog)
      └─────┬─────┘    design-language signals  │
            │                                    │  contradiction? → one-off + queue
            │ render_brand_md() (pure)           ▼
            ▼                          ┌─────────────────────┐
      ┌───────────┐                    │ pending-questions.  │ ──► user answers ──► update/one-off/keep
      │  brand.md  │ (projection,       │      yaml          │        │
      │ never edited)                   └─────────────────────┘        │
            │                                    ▲                     │
            │                                    └─────────────────────┘
            ▼                                     (answer feeds back into brand.yaml + changelog)
   ┌──────────────────────┐
   │  assembler / build    │  reads brand.yaml (canonical) + section-recipe + library
   │  (Webflow MCP)        │  emits build-failure signals back into signals.log
   └──────────────────────┘
```

Canonical truth flows **one way out** of `brand.yaml` (to `brand.md` and the
assembler) and **one way in** (from `signals.log` via the gated consolidation pass).
Every mutation lands in the per-rule append-only `changelog`.

## Sign-off decisions (authoritative — override the recommendations below)

The user has signed off on the following. Where any spec text above conflicts, these
win and the spec files have been annotated `(SIGN-OFF #n)` at the relevant spots.

1. **`brand.md` is generated from `brand.yaml`; drift-check is a WARNING, not a build
   blocker.** No CI gate is implemented. `render_brand_md.py --check` may report drift
   but never fails a build. (Resolves open question #1.)
2. **Consolidation runs on-demand / manual only** — never scheduled, never automatic
   before publish. (Resolves open question #2.)
3. **Design-language promotions REQUIRE explicit user confirmation.** ≥2 consistent
   signals only *flags a candidate*; it never auto-promotes. (Resolves open
   question #3 — the "auto-promote at ≥2 signals" bar is rejected.)
4. **`build-failure` signals AUTO-PROMOTE** to `neverDo`/`recipePolicy` at high
   confidence without asking. (Resolves open question #4.)
5. **Composite archetypes (`collage`/`overlay`/`band`) are expressed via ABSOLUTE
   OFFSETS inside a `Section / Stack` (or nearest `Section / *`) slot — no new library
   components are created yet.** (Resolves open question #5.)
6. **`brand.yaml` INDEXES the existing artifacts** (`variable-mapping.md`,
   `section-recipe.md`, `webflow-variables.json`); it sits above them as a referencing
   index and does NOT supersede, delete, or replace them. The analyst writes only
   `brand.yaml` (+ enqueues signals). (Resolves open questions #6 and #7.)

## Open questions for the user (original — now resolved by the sign-off above)

1. **Renderer ownership of `brand.md`.** OK to make `brand.md` fully generated and
   add a CI drift check that fails on hand-edits? (Existing `runs/woodwave/brand/brand.md`
   was hand-authored; it becomes the renderer's target output.)
2. **Consolidation cadence.** Run the consolidation pass automatically before each
   publish, on a fixed schedule, or only on explicit request?
3. **Promotion gate strictness.** Is "≥2 consistent signals across distinct sections
   → high confidence → auto-promote" the right bar, or should *all* design-language
   promotions wait for explicit user confirmation?
4. **build-failure authority.** Should build-failure signals auto-promote to
   `neverDo`/`recipePolicy` at high confidence without asking (current proposal), or
   also queue a question?
5. **Composite archetypes (`collage`/`overlay`/`band`).** These have no native
   library scaffold and are composed from primitives + offset utilities. Acceptable
   to express overlap/stagger via absolute offsets inside a `Section / Stack` slot,
   or should we propose creating dedicated reusable composite components in the
   library?
6. **`brand.yaml` ↔ existing artifacts.** Should `brand.yaml` supersede today's
   `webflow-variables.json` + `variable-mapping.md` + `section-recipe.md`, or sit
   above them as an index that references them?
7. **Scope of the analyst's write access.** Confirm the skill writes ONLY
   `brand.yaml` (+ enqueues signals), and that `variable-mapping.md`/`section-recipe.md`
   remain build-time artifacts produced by the assembler, not the analyst.
