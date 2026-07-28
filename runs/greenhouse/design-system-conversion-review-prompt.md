You are evaluating design-system conversion loss.

You will receive:
- One `surface-component-map.md`
- One `design-system.md`

No screenshot is available. Treat the surface-component map as the factual source of truth. Evaluate whether the design system preserved, translated, merged, distorted, omitted, or overgeneralized the map's factual host-surface and nested-component pairings.

## Scoring

Use strict 0-10 scores for each dimension:
- `factual_pairing_preservation`: whether the design system preserves critical pairings for host surface, heading text, body text, primary/secondary buttons, compact labels, cards/panels, borders, dividers, shadows, gradients, and image/graphic slots.
- `surface_specificity`: whether surface-specific recipes remain tied to their host surface roles instead of becoming generic global accent/default rules.
- `component_recipe_translation`: whether map facts become reusable implementation recipes, tokens, variants, or rules with enough detail to drive generation.
- `typography_and_casing`: whether heading/body/label hierarchy, host-specific text color, casing such as `textTransform: uppercase`, and emphasis rules are preserved.
- `constraints_and_exceptions`: whether `doNotGeneralize`, one-off/rare facts, ambiguity notes, and source-vs-grounded confidence boundaries are carried forward as useful constraints.
- `unsupported_overgeneralization`: whether the design system avoids inventing unsupported colors, surfaces, cards, buttons, section-specific token names, or broad rules that the map does not support.

## Rules

- Be strict. A polished design system that loses map-specific pairings should score poorly.
- Reward faithful translation into generic reusable roles, not verbatim copying.
- Penalize omitted factual pairings even if the design system looks internally consistent.
- Penalize conversion that preserves source CSS typography too literally when it violates the Typography Normalization Contract: body/paragraph tokens must be `14px-16px`, subhead/lead/intro/supporting-heading tokens must be at most `1.5x` body, text-bearing controls and text links must use canonical body size, h1 must be grounded in page-heading evidence, h2 must be grounded in section-heading evidence, and card/local/control/label/metadata evidence must not change h1/h2 weight.
- Do not treat source CSS font-size values as mandatory when they conflict with those normalized design-system roles. Exact source values may inform h3, card-title, content-heading, display, or decorative tokens, but generation-facing h1/h2 typography must remain role-grounded.
- Penalize conversion that turns exact source section order or one-off component positions into design-system layout rules instead of leaving them for `layouts.yaml`.

## v172 Source-Order Conversion Gate

- Request changes when the final design system contains source-section IDs, source-section label names, `derived_from`, `evidenceSections`, `run_order`, `source_order`, `page_sequence`, `section_sequence`, `patterns.sections`, or `patterns.surface_runs` as generation-facing content.
- Request changes when surface runs or section patterns encode a chronological source-page recipe rather than reusable parent/child ownership and boundary primitives.
- A strong conversion preserves host/component facts but strips generation-facing provenance. Exact source values may survive; exact source section order must not.
- Penalize conversion that omits the four imagery creative-direction categories (`icons`, `illustrations`, `interfaces`, `photography`) or loses density/simplicity/detail limits between the map and the design system.
- Penalize merging distinct map surfaces when that would change component colors or contrast behavior.
- Penalize overgeneralizing a one-off pairing into a global default.
- Penalize section/content-specific token names, but do not penalize section-local evidence notes if they preserve the factual relationship.
- Do not ask for screenshot evidence. The map is the only factual reference for this review.
- Keep notes concrete enough to guide the next design-system synthesis prompt.
- Return JSON only, with no markdown fences.

Use this exact shape:

{
  "summary": "short overall summary",
  "scores": {
    "factual_pairing_preservation": {"score": 0, "notes": "short note"},
    "surface_specificity": {"score": 0, "notes": "short note"},
    "component_recipe_translation": {"score": 0, "notes": "short note"},
    "typography_and_casing": {"score": 0, "notes": "short note"},
    "constraints_and_exceptions": {"score": 0, "notes": "short note"},
    "unsupported_overgeneralization": {"score": 0, "notes": "short note"}
  },
  "preserved_pairings": ["bullet", "bullet"],
  "conversion_losses": ["bullet", "bullet"],
  "distortions_or_overgeneralizations": ["bullet", "bullet"],
  "actionable_learnings": ["bullet", "bullet"],
  "verdict": "short verdict"
}
