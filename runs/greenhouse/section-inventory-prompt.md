You are analyzing a full-page website screenshot so a later workflow can ground each section separately.

Your only job in this step is to identify the visually distinct top-level sections from top to bottom.

## Rules

- Base your answer on visible evidence only.
- Do not estimate pixel coordinates.
- Do not output JSON.
- Do not talk about cropping.
- Focus on top-to-bottom section understanding before worrying about exact cut lines.
- Start with the navigation / header section if one is visible.
- End with the footer section if one is visible.
- The navigation/header must be its own section if visible. Do not merge it with the hero even if they share the same background.
- The hero must be its own section when it is visually distinct from the navigation.
- Different section types should not be combined into one section entry just because they share the same background color.
- Do not combine things like a logo row with stats, or navigation with hero, or a CTA block with the content above it, unless they are clearly one continuous section.
- Give strong weight to spacing rhythm, shared surface continuity, and shared container treatment when deciding whether adjacent blocks belong to one section.
- If an eyebrow / heading / intro block sits directly above cards, tabs, grids, media, or other modules on the same background or within the same enclosing surface, treat them as one section unless there is a strong visual break.
- Do not split a section just because the intro/header area and the content area use different internal layouts.
- Use content-role changes as weaker evidence than background continuity, shared borders or shells, and the vertical gap between a section header and the module below it.
- Prefer a split only when there is strong evidence such as a major spacing break, a clear change in background or enclosing surface, an obvious divider, or a standalone full-width module that reads independently.
- A section may begin with a heading, eyebrow, icon, card cluster, logo row, large feature block, or a clearly new background or surface treatment.
- Images and graphics count as section content.
- If uncertain, prefer preserving a likely heading-plus-content grouping rather than over-splitting it into multiple sections.

Return a markdown list from top to bottom.

For each section include:
- a short label
- one sentence describing what is visible
- one sentence explaining why it appears to be a separate section
