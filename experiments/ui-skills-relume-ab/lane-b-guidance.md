## SECTION RECIPE CANDIDATES (content-structure baseline; NEVER a visual template)

FALLBACK ONLY. Choose structure and ingredient axes from these normalized families. Mirrored orientations and media substitutions are knobs, not separate templates. Preserve the listed responsive transitions; do not reduce them to desktop-only geometry.
Relume contributes topology ONLY. Brand tokens, surfaces, spacing, components, media and copy bind after selection. No source visual or concrete value is available. Measured brand patterns > designed-from-brand patterns > compatible brand/style archetypes > this fallback. Stamp a chosen fallback with `structureProvenance: relume-fallback` and its `structureRecipeId`.
This baseline is biased toward conventional SaaS, marketing, and application UI. Do not infer that it covers editorial or experimental structures. Those candidates belong to separate curated genre libraries and may be merged only at selection time.

- `pricing-content-stack` — section `pricing`, archetype `stack`, skeleton `content-stack`
    - slots: required heading; optional actions, icons, list, plans
    - variant axes: columns=1; textAlign=center,left; ingredients=actions,icons,list,plans
    - responsive: source inspection pending; do not infer unsupported transitions
- `pricing-repeated-grid` — section `pricing`, archetype `cards`, skeleton `repeated-grid`
    - slots: required heading; optional actions, comparison, icons, list, plans
    - variant axes: columns=1,2,3,4; textAlign=center,left; ingredients=actions,comparison,icons,list,plans
    - responsive: columns: 1 → md:2
- `pricing-table` — section `pricing`, archetype `cards`, skeleton `table`
    - slots: required heading; optional actions, comparison, plans, table
    - variant axes: textAlign=center,left; interaction=tabs; ingredients=actions,comparison,plans,table
    - responsive: columns: 3 → md:asymmetric-4-column; display: hidden → md:block; columns: 3 → md:asymmetric-4-column; sticky: enabled
