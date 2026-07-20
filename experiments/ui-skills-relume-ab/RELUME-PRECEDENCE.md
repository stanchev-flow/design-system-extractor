# Relume precedence and bias audit

## 2026-07-19 implementation status

The structural-competition bug described below is fixed behind
`enable_relume_fallback=False`:

- raw `catalog.generated.yaml` and `responsive-evidence.yaml` remain provenance data;
  prompt selection loads only scanner-gated `catalog.structural.yaml`;
- automatic retrieval starts from ordered brief jobs, removes measured and compatible
  brand/style-archetype support, and exposes at most three candidates total;
- selected sections emit `structureProvenance: relume-fallback` and a prompt-safe recipe
  id; a pre-render lint rejects any higher-tier conflict;
- brand tokens, surfaces, spacing, components, media and copy remain downstream of
  structural selection.

The original audit below is retained as the pre-fix record.

## Current path

1. `relume_recipe_catalog.py:428-487` loads the ten inventory shards and collapses
   source metadata into section type, skeleton, archetype, slots, axes and responsive
   observations.
2. `relume_recipe_catalog.py:497-532` labels the catalog a structural prior, enumerates
   ignored visual properties, records brand/style-first precedence and declares the
   conventional SaaS/marketing/application bias.
3. `relume_responsive_parser.py:28-55` accepts only structural display/column/flex/order/
   overflow/media mechanics and excludes fixed design-system dimensions.
   `relume_responsive_parser.py:82-96` replaces class names with element ordinals.
4. `relume_recipe_catalog.py:608-640` retrieves by section type, broad builder use case,
   skeleton, ingredient overlap and responsive evidence.
5. `relume_recipe_catalog.py:643-697` renders normalized structure, slots, axes and
   responsive behavior with an explicit instruction to ignore visual style and copy.
6. `generate_composition.py:1569-1587` auto-resolves Relume whenever the caller does not
   explicitly pass `section_recipe_guidance`. It queries the *same use cases already
   represented by brand seeds*, excluding only footer.
7. `generate_composition.py:865-879` appends hero archetypes, then style directives, then
   Relume guidance to the system prompt. This textual order leaves Relume closest to the
   composition grammar, although the Relume block says brand/style facts win.
8. `section_wireframe.py:700-714` records only measured recipe → designed component →
   shared archetype precedence. Relume is not a first-class provenance source in
   `wireframe.v1`.

## Finding

No severe visual-style leak was found. Inventory source code is not vendored; the
compiler excludes colors, typography, spacing, class names, radii, shadows and aesthetic
defaults (`relume_recipe_catalog.py:504-512`), and the emitted guidance repeats that
boundary (`:648-659`). Preview URLs and source tags remain in catalog provenance but are
not emitted by `render_recipe_guidance`.

There **is a material structural-bias bug**: production auto-injection asks Relume for
every brand-seeded use case (`generate_composition.py:1575-1582`). That is the opposite
of fallback-only behavior. In addition:

- retrieval is not conditioned on a missing brand pattern;
- the automatic caller provides no copy-shape or asset-availability features;
- `match_recipes` returns the whole ranked set and `guidance_for_use_cases` takes two per
  broad use case rather than a job-specific top-k;
- no machine-readable `structureProvenance` survives into composition/wireframe output;
- broad `builderUseCase` mappings can degrade richer Relume types (for example contact to
  CTA and event feeds to gallery);
- prompt order relies on prose precedence rather than enforcing candidate exclusion.

This can make pages converge on conventional SaaS structure even while their colors and
type remain on-brand.

## Experiment policy

The isolated lane enforces:

1. measured brand pattern/recipe;
2. designed brand component synthesized from measured signals;
3. active brand/style archetype;
4. Relume **only** when the requested section job/use case has no candidates above.

Relume contributes only skeleton, anatomy, slots/ingredients, interaction family and
source-inspected responsive behavior. It never contributes tokens, colors, typography,
spacing, classes, radii, shadows, imagery, copy, component implementation or aesthetic
defaults.

Selection must use section job + copy shape + available asset/interaction needs and
expose no more than three candidates. The final renderable probe targets pricing because
HubSpot's measured layout library has hero, features and testimonial patterns but no
pricing pattern. Lane B queries `sectionType=pricing`, requests plan/card/action anatomy,
requires inspected responsive evidence and exposes top-3. All non-pricing sections
receive no Relume candidate. An initial FAQ probe was abandoned for both lanes after the
wireframe capability registry proved that accordion item contracts have no consuming
renderer path; `attempt-2-summary.json` preserves that blocker.

Because `composition.v1` and `wireframe.v1` do not currently permit a Relume provenance
field, the experiment writes a separate `structure-provenance.json`. Its stamps are
post-render inference and explicitly say so; they are not presented as model-emitted
ground truth.

## Promotion prerequisite

Do not promote current auto-resolution. First change candidate resolution to compute
missing use cases after measured/designed/style retrieval, add copy/asset scoring, cap
top-k, and add schema-backed provenance consumed by the wireframe. That production
change is intentionally outside this experiment.
