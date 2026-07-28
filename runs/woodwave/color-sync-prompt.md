You are correcting explicit color values in a design-system markdown file using a source-of-truth CSS color report extracted from the original HTML plus screenshot grounding when provided.

## Rules

- Preserve the existing section order, headings, bullets, and non-color wording as closely as possible.
- Preserve local component-on-surface color pairings from the screenshot grounding. A component recipe on a specific host surface must not be remapped to a global accent just because that accent appears more often in source CSS.
- Treat any `## Critical Color Pairings` inventory and detailed section-grounding component recipes as high-priority evidence for host surface, heading text, body/support text, primary/secondary buttons, cards/panels, borders/dividers, and shadows/glows.
- Use the source CSS color report as authoritative for exact hex, rgba, and gradient values when it contains a visually close match for the grounded color role.
- If the source CSS report does not contain a visually close match for a grounded component color, keep or restore the screenshot-grounded color value instead of forcing a distant source color.
- Focus on correcting explicit color values, especially in `## Color Tokens`.
- Do not invent colors that appear in neither the source report nor the screenshot grounding.
- If a clear source-backed or grounding-backed replacement does not exist, rewrite that wording to avoid an unsupported explicit color value instead of guessing.
- Return the full corrected markdown document.

## Component Color Pairing Rules

- Treat buttons, eyebrows, badges, chips, tags, inputs, tabs, cards, and other portable UI components as surface-paired recipes, not just references to global palette frequency.
- If the grounding says a compact control on an `inverseStrong`, dark, inverse, light, tonal, or card surface has a particular color family, preserve that family even when another source color token has a similar role name.
- For example, a warm/yellow highlight control on a darkest inverse surface should stay warm/yellow when no close source hex exists; do not replace it with a greener global `highlight` or `accent` merely because that green appears in the source palette.
- Prefer the closest source-supported hex only when it preserves the grounded hue, temperature, saturation, lightness, and component/host contrast relationship.
- If several source colors are available but none is close enough to preserve the screenshot vibe, use the explicit screenshot-grounded color as the fallback.
