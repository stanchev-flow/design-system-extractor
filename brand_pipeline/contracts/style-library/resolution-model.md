# Resolution model — the cascade

> provenance: authored-prior (Claude design chat, 2026-07-14) — NOT evidence; requires bakeoff validation before brand use.
>
> Package doc, kept verbatim below (only file references updated to the YAML-canonical
> names; the content-identical `resolution-model.json` mirror was dropped at import).
> ADAPTATION REQUIRED before implementation: this model's "locked invariants" and its
> single brandOverride level do not distinguish measured brand EVIDENCE from authored
> brand preference — our law (brand evidence always wins; brand-schema §5.3, Appendix B
> precedence, AS-44) requires the invariant classes and level-4 semantics defined in
> `INTEGRATION-PLAN.md` §4/stage A. Implement against that adaptation, not this file alone.

A concrete section spec is **computed**, never stored per (style, section).

## Four levels (low → high precedence)
1. **sectionDefault** — Rules true for a section in any style (from sections/catalog.yaml).
2. **styleDirective** — Cross-cutting bias for a style across all sections (from styles/directives.yaml).
3. **override** — Specific (style × section) patch — the 'this style treats this section differently' case (from overrides/overrides.yaml).
4. **brandOverride** — Final brand-specific say (from brand.tokens.json).

## Merge semantics
- **Scalars** — replace — higher level wins (e.g. radius: 0 beats radius: md).
- **Objects** — deep per-key merge — an override touches only the keys it names.
- **Lists** — tagged: { $replace:[...] } swaps the list; { $append:[...] } extends it; { $remove:[...] } subtracts. Bare arrays default to $replace.
- **layoutBias** — style/override values RERANK a section's allowed layouts; anything not in the section's `layouts` is ignored.

## Invariants
Keys under a section's `invariants` are LOCKED. No directive, override, or brand value may violate them (e.g. hero always keeps exactly one primary CTA). Violations are rejected at stage 05, not silently applied.

## Algorithm
- 1. spec = deepClone(sectionDefault[section])
- 2. spec = merge(spec, project(styleDirective[style]))   // constraints + layoutBias rerank
- 3. spec = merge(spec, overrides?.[style]?.[section] ?? {})
- 4. spec = merge(spec, brand.overrides?.[section] ?? {})
- 5. spec.layout = firstAllowed(spec.layoutBias, sectionDefault[section].layouts) ?? sectionDefault[section].defaultLayout
- 6. assert(invariantsHold(spec, sectionDefault[section].invariants))  // else reject → repair
- 7. bind brand tokens (font, color, radius value, spacing) → concrete section

## Variations
To emit N on-style variants, perturb one variationAxis at a time (from the section's variationAxes) and re-run steps 5–7. Every result already satisfies style + invariants, so all variants are valid by construction.

```js
function resolve(section, style, brand){
  let spec = clone(SECTIONS[section]);
  spec = merge(spec, projectDirective(STYLES[style]));
  spec = merge(spec, OVERRIDES?.[style]?.[section] ?? {});
  spec = merge(spec, brand.overrides?.[section] ?? {});
  spec.layout = spec.layoutBias.find(l => SECTIONS[section].layouts.includes(l))
              ?? SECTIONS[section].defaultLayout;
  assertInvariants(spec, SECTIONS[section].invariants);
  return bindTokens(spec, brand.tokens);
}
```
