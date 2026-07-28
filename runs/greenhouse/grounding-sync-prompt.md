You are correcting a structural grounding markdown file using a source-of-truth CSS style report extracted from the original HTML.

## Goal

The grounding file should remain a faithful text-based copy of the screenshot, not a design system rewrite. Correct and upgrade the parts that should be sourced from the HTML/CSS: explicit colors, gradients, and explicit typography values.

## Rules

- Preserve the exact document structure, section order, headings, bullets, and general wording as closely as possible.
- Use the source CSS style report as authoritative for:
  - exact color values
  - exact gradient values
  - exact font family names
  - exact font sizes
  - exact font weights
  - exact line heights
  - exact letter spacing values
- When the grounding file contains approximate explicit color values, replace them with source-supported values when a clear match exists.
- When the grounding file contains approximate explicit typography values, replace them with source-supported values when a clear match exists.
- Preserve existing text-role distinctions and role labels. Do not rewrite page headings, section headings, card titles, local content headings, controls, labels, metadata, buttons, nav/footer links, or body text into one generic heading category while syncing source CSS values.
- When adding or correcting font descriptions, keep readable visual characteristics for the role instead of underscore-separated labels.
- When a background, border style, divider style, or typography style line is written only in vague descriptive language but the source CSS clearly supports a more explicit exact value, rewrite that line to include the exact source-backed value while preserving the grounded observation.
- Prefer explicit source-backed hex / rgba / gradient values over vague phrases like "light green" or "dark gray" when the source report makes the value clear.
- Prefer explicit source-backed font family, size, weight, line-height, and letter-spacing values over vague phrases like "sans-serif" or "medium size" when the source report makes the value clear.
- Do not return numeric ranges for CSS-like values. If the input contains a range such as `33-38px`, `33–38px`, `0.25–0.35`, `221-227`, `14-16px`, or `96-98%`, replace it with the closest exact source-supported value when available.
- If the source report does not support a precise replacement for a numeric range, collapse it to one representative approximate value or use semantic wording. Never leave a hyphen/en-dash numeric range in font-size, font-weight, line-height, letter-spacing, width, height, spacing, radius, opacity, shadow, percentage, or ratio text.
- If the source report does not support an exact explicit value, prefer semantic wording instead of invented precision.
- Do not invent colors or typography values that do not appear in the source report.
- Do not remove grounded structural observations like layout, grouping, transitions, spacing, graphics direction, or depth/elevation.
- Return the full corrected grounding markdown document.
