You are correcting a generated single-file HTML document so its explicit visual values match the source-of-truth CSS styles and the provided design-system markdown.

Rules:
- Preserve the existing HTML structure, content, and layout as closely as possible.
- Focus on correcting explicit CSS values only: colors, gradients, font-family, font-size, font-weight, line-height, and letter-spacing.
- Use the source CSS style report as authoritative for exact explicit values.
- If the design-system markdown includes an explicit exact value and that value is supported by the source CSS style report, prefer it.
- Preserve the design-system Typography Normalization Contract when correcting typography: source CSS font values are evidence, not an override, for body/paragraph `14px-16px`, subhead/lead/intro/supporting-heading max `1.5x` body, text-link/control body-size matching, and h1/h2 role separation. Keep h1 values tied to page-heading evidence and h2 values tied to section-heading evidence; do not let card titles, local content headings, controls, labels, nav/footer links, buttons, tabs, badges, or metadata override h1/h2 weight.
- Do not invent new hex/rgb/rgba/hsl colors, gradients, or font-family stacks.
- Do not introduce approximate alpha variants, blended shades, or softened contrast values that are not supported by the source CSS style report.
- If an explicit visual value is unsupported, replace it with the closest supported explicit value from the design-system markdown or source CSS style report.
- Preserve existing component width behavior while correcting explicit visual values. Do not introduce `display: block`, `width: 100%`, or stretch alignment on content-hugging buttons, eyebrows, badges, tags, chips, or compact metadata labels.
- Do not rewrite layout, markup, or copy unless that is required to keep the HTML valid.
- Return ONLY the corrected full HTML document.
