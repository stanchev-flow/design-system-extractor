# Section wireframing (`wireframe.v1`)

`wireframe.v1` is the machine-validated stage between copy intent and final
composition rendering. It plans the whole page before HTML exists.

## Required decisions

At page level it records story rhythm, density and surface sequences, the maximum
text-only run, and structural precedence:

1. measured brand patterns and recipes;
2. designed-from-brand components and patterns;
3. compatible brand/style archetypes;
4. a structure-only Relume fallback, only when the section job remains unsupported.

Each section records its job, density, surface role, visual anchor, conversion
role, skeleton, required/optional slots, component family, CTA/proof obligations,
asset requirements or requests, responsive behavior, and a renderer-capability
result for every required slot. An unsupported skeleton is rejected before render.
The plan preserves `structureProvenance` and `structureRecipeId`. A Relume-stamped
section without a selected prompt-safe recipe id fails, and composition generation
fails earlier if that fallback competes with any compatible higher-tier source. Brand
tokens, surfaces, spacing, components, media and copy bind after structure selection.

## Atomic collections

Repeated semantic records are never a primitive waterfall. A collection carries:

- `itemContract`: existing `feature-item`, `content-block`, `card`, or `testimonial`;
- `items[]`: complete records such as `{eyebrow|heading, text|body, action?}`;
- `layout`: grid, stacked list, rail, or open cards;
- `columns`, `wrap`, and responsive collapse.

The item wrapper is atomic. Internal label-to-body rhythm uses the brand relational
ladder; inter-item rhythm belongs to the parent collection and is larger. Mobile
collapse changes collection tracks, never item boundaries.

### Component fit / layout feasibility

`columns` is an output of the fit solver, not an item-count default. Every
collection records per-item `contentDemand`, the measured (or conservative)
container allocation, gutters and padding, family `minItemWidth`, reading
measure and line caps, all rejected candidate widths, the selected columns, one
family-wide `internalAnatomy`, fill-strategy candidates/rejections, explicit
per-item spans, and feasibility-derived responsive thresholds.

The solver chooses the maximum count for which every item clears minimum width,
line caps, and unbreakable-token fit. It steps `3 → 2 → 1`; it never squeezes.
Icons remain inline only when the reduced text measure still clears every cap;
otherwise all siblings use `icon-top`. After track selection, the planner rejects
an orphan final-row void. It evaluates: a uniquely strongest authored lead spanning
the row; a tail span for peer items; one-column reading when a full-span measure
would be excessive; or a higher track count only when component fit passes. A
partial row is allowed only as `licensed-asymmetry` with a real painted balancing
counterweight. Spanning cards may constrain their internal content measure while
their painted plate fills every selected track.

## Testimonial components

A testimonial/quote job with attribution is atomic. Quote and attribution are
required; avatar/client image, mark, result/stat, and action are optional roles.
Compatible extracted `avatar`, `portrait`, or `client-photo` media is matched
from `media-assets.v1` by subject and attribution. If none exists, the plan emits
an asset request and chooses a deliberate no-photo `quote-card`; it never
reserves an unexplained empty media column.

Anatomy follows evidence: `portrait-side`, `avatar-top`, `quote-card`,
`logo-quote`, or `stat-quote`. Brand recipes, surfaces, typography, spacing, and
licensed accent signals outrank generic defaults.

## Hard failure conditions

- required slot has no consuming adapter/renderer path;
- substantive section lacks media, proof, component cluster, action cluster, or a
  licensed text-only monument;
- conversion job lacks an action;
- proof/story job lacks proof, media, or a meaningful component cluster;
- side hero's named counterweight is not painted;
- two consecutive substantive sections are visually sparse;
- required wireframe slot is absent from composition;
- repeated records use a flattening primitive contract;
- rendered item width, line caps, overflow, or sibling anatomy contradicts the
  component-fit plan (AS-75);
- testimonial intent renders as bare primitives, drops quote/attribution or a
  compatible bound asset, or leaves an unlicensed empty-space monument (AS-76).
- a collection leaves unused final-row tracks without an explicit fill strategy,
  or licensed asymmetry lacks a real balancing counterweight (AS-77).

Schema: `brand_pipeline/spec/wireframe.v1.schema.json`.
