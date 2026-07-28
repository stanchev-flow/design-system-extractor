You are evaluating how well a surface-component map preserves factual visual relationships from a source website screenshot and its section grounding.

You will receive:
- One original source screenshot
- A compacted section-grounding reference
- One `surface-component-map.md`

Evaluate the map itself, not the final design system and not a generated website.

## Scoring

Use strict 0-10 scores for each dimension:
- `surface_inventory`: whether the map identifies the real host surfaces, section bands, inverse/light/tinted runs, gradients, and parent surfaces without collapsing unrelated surfaces.
- `nested_element_pairings`: whether the map preserves child elements on each host surface: headings, body text, buttons, compact labels, cards, panels, borders, dividers, shadows/glows, media/graphics.
- `critical_color_pairings`: whether the map captures accurate approximate/source-backed colors for host surface, heading text, body text, primary/secondary buttons, compact labels, cards, borders, dividers, and shadows.
- `typography_and_casing`: whether text roles include useful heading/body/label distinctions, casing, emphasis, and host-surface text-color behavior.
- `background_depth_graphics`: whether gradients, image/graphic slots, decorative motifs, shadows, glows, masks, and edge behavior are represented with enough implementation detail.
- `actionability_and_constraints`: whether the map is normalized enough for design-system synthesis, avoids noisy irrelevant evidence, and includes useful `doNotGeneralize` / ambiguity constraints.

## Rules

- Be strict. A noisy evidence dump with the right words but unclear role grouping should not score highly.
- Reward factual completeness and correct host-surface grouping more than polished prose.
- Penalize maps that collapse all evidence into one section, merge distinct surfaces, omit body/heading/button/card color relationships, or fail to separate parent surfaces from child cards/panels.
- Penalize maps that omit the four imagery creative-direction categories (`icons`, `illustrations`, `interfaces`, `photography`) or fail to preserve density, simplicity/detail level, rendering medium, and style-vs-subject separation.
- Penalize maps that treat exact source section order and one-off component positions as reusable layout rules instead of distinguishing repeated layout patterns from source-specific layout artifact material.
- Penalize page-specific names only when they prevent generic synthesis; section-local evidence labels are acceptable if the factual pairings remain clear.
- Ignore whether the map already has final token names. It is an intermediate grounding artifact.
- Return JSON only, with no markdown fences.

Use this exact shape:

{
  "summary": "short overall summary",
  "scores": {
    "surface_inventory": {"score": 0, "notes": "short note"},
    "nested_element_pairings": {"score": 0, "notes": "short note"},
    "critical_color_pairings": {"score": 0, "notes": "short note"},
    "typography_and_casing": {"score": 0, "notes": "short note"},
    "background_depth_graphics": {"score": 0, "notes": "short note"},
    "actionability_and_constraints": {"score": 0, "notes": "short note"}
  },
  "strengths": ["bullet", "bullet"],
  "major_mismatches": ["bullet", "bullet"],
  "actionable_learnings": ["bullet", "bullet"],
  "verdict": "short verdict"
}
