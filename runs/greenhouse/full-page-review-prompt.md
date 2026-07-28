You are reviewing a full-page website screenshot after section-by-section grounding has already been completed.

Your job in this step is not to rewrite the whole grounding file. Your job is only to determine:

1. the final transition into and out of each section
2. whether the navigation is nested inside the hero, visually separate from it, or overlaid on it
3. which sections belong to the same background group because they share one continuous or effectively shared background treatment
4. which sections share the same container-width pattern
5. which contiguous adjacent sections should be grouped together into section groups because they behave like one shared surface run
6. any other cross-section-only judgments that depend on seeing multiple adjacent sections together, such as long shared-surface runs or repeated global wrapper behavior

## Inputs you will receive

- The full-page screenshot as a single image
- A text summary of the grounded per-section observations
- The final detected section order and bounds

## Rules

- Use the screenshot as the source of truth for transitions and grouped backgrounds.
- Use the grounded per-section observations to understand what each detected section contains.
- The grounded per-section observations may contain provisional navigation/transition judgments. Treat those as non-authoritative. The screenshot is the final authority for these fields.
- Focus only on judgments that require full-page context and cannot be reliably established from an isolated crop.
- Do not spend time refining local component styling, local card details, or single-section typography details in this step.
- Treat this as a cross-section reconciliation pass, not a local design analysis pass.
- Do not change the section count.
- Do not merge sections.
- A background group means sections share the same or continuous background treatment across their boundary.
- A section group is a contiguous top-to-bottom run of adjacent sections that should be presented together in the final structural grounding because they share one higher-level surface run or grouped wrapper behavior.
- Section groups must be contiguous. Do not put non-adjacent sections in the same section group, even if they reuse the same background family later on the page.
- Sections can be in the same background group while still remaining separate sections because their content roles differ.
- Judge background groups by the section wrapper background, not by dark or contrasting large modules/cards inside the container.
- Judge background graphics by their visible edges. A graphic, illustration, shader-like field, texture, or glow that blends seamlessly or softly fades into the section surface is part of the wrapper/background treatment, even if it occupies a reserved visual zone. A clipped rectangle, framed media edge, card edge, or embedded screenshot/mockup edge is foreground or contained media, not proof of a separate background group.
- If a section contains a full-width dark card or large module on the same section wrapper as its neighbors, do not move that section into a different background group just because the contained module is visually strong.
- If the header/navigation and hero sit on the same continuous atmospheric field, soft gradient, or shared background color with no clear surface reset, they should be in the same background group and `navigation_relationship_to_hero` should be `nested inside hero` or `overlaid on hero`, not `visually separate from hero`.
- Do not call header and hero visually separate just because the section detector split them apart. Only call them separate if the screenshot clearly shows a surface reset between them.
- Container-width groups should be based on the main centered content width, not decorative overflow, background art, or full-width cards/modules inside the container.
- If the nav, hero, and footer share one width while the middle sections use another, represent that as separate container-width groups.
- Prefer `gradient/tonal continuity` when a gradient or tonal wash visibly flows across the section boundary.
- Prefer `whitespace continuity` when adjacent sections sit on the same stable surface and are separated mainly by spacing.
- Prefer `hard cut` only when the surface clearly resets at the boundary with an abrupt full-width change and no visible tonal fade, shared wrapper, overlap, or divider.
- Do not call a boundary a hard cut just because the content role changes, the section detector split the rows, or the next section uses a different internal module. Judge only the full-width wrapper/background edge.
- If a boundary moves from an atmospheric/gradient field into a flatter surface through a visible fade or wash, classify it as `gradient/tonal continuity`, not `hard cut`.
- If a closing or opening run starts with a glow/wash and settles into a calmer solid field, keep those adjacent sections in one section group and describe the transition inside the group as tonal continuity unless a visible divider separates them.
- For section-group transitions, derive the group-level transition from the actual boundary between the last section in the previous group and the first section in the next group. Do not downgrade a section-level `gradient/tonal continuity` boundary to group-level `hard cut`.
- Use `divider-based` only when a visible divider or rule clearly defines the section boundary.
- Use `overlapping` only when elements physically overlap across the boundary.
- For the first section, `transition_from_previous_section` should be `N/A`.
- For the last section, `transition_to_next_section` should be `N/A`.
- If the first section is navigation and the second section is hero, explicitly determine `navigation_relationship_to_hero`.
- Use stable group ids like `G1`, `G2`, `G3` in top-to-bottom order.
- Use stable container-width group ids like `C1`, `C2`, `C3` in top-to-bottom order.

## Output

Return JSON only in this exact shape:

```json
{{
  "sections": [
    {{
      "section_num": 1,
      "transition_from_previous_section": "N/A",
      "transition_to_next_section": "gradient/tonal continuity",
      "transition_edge_evidence": "brief visible evidence for this transition classification",
      "background_graphic_relationship": "brief note when a major visual reads as a seamless section-background layer, foreground/concrete-edged media, embedded showcase, or unclear",
      "navigation_relationship_to_hero": "nested inside hero",
      "background_group_id": "G1",
      "container_width_relationship": "primary site width",
      "container_width_group_id": "C1"
    }}
  ],
  "background_groups": [
    {{
      "group_id": "G1",
      "sections": [1, 2],
      "summary": "Header and hero share one continuous atmospheric background."
    }}
  ],
  "section_groups": [
    {{
      "group_id": "SG1",
      "sections": [1, 2],
      "summary": "Navigation and hero form one contiguous atmospheric opening run.",
      "background_group_id": "G1",
      "transition_from_previous_section_group": "N/A",
      "transition_to_next_section_group": "gradient/tonal continuity",
      "run_edge_evidence": "brief visible evidence for the group start/end transitions and internal continuity"
    }}
  ],
  "container_width_groups": [
    {{
      "group_id": "C1",
      "sections": [1, 2, 11],
      "summary": "Navigation, hero, and footer use the same wide primary container."
    }}
  ],
  "cross_section_notes": [
    "Sections 1 and 2 behave like one shared atmospheric surface even though they remain separate sections.",
    "Sections 6 and 7 share the same outer wrapper treatment and should be read as one grouped surface run.",
    "Describe any major run boundary that is a tonal fade rather than an abrupt hard surface reset."
  ]
}}
```
