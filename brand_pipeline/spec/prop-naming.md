---
name: prop-naming
description: >-
  Formalize the existing webflow-library-aisb prop grammar so the assembler names
  props consistently and a brand.yaml componentMapping slot-role maps to a real
  prop name predictably. Use when creating or naming a component prop, grouping
  props (content/style/layout/visibility/state), labeling booleans, adding variant
  props for enumerated choices, forwarding a primitive's prop onto a composite, or
  deciding whether to reuse an existing prop name vs invent one. Matches the library
  conventions (Title Case grouped props, Group/Name variables, FlowKit
  property_value classes) — it does not introduce a new grammar. Both
  webflow-token-mapping and webflow-component-build lean on this.
---

# prop-naming

> **STATUS: SPEC / review draft — not active until `brand.yaml` is validated; install
> as a skill only after the Art Director + render gate pass.** This file lives in the
> review folder `design-system-extractor-mine/brand_pipeline/spec/`. Do **not** copy it
> into `.cursor/skills/` yet. Links below resolve from **this review folder**
> (`brand_pipeline/spec/`); on install they get rewritten to be relative to
> `.cursor/skills/prop-naming/` (mirroring `brand-layout-analyst`).

This doc **formalizes the prop grammar the `webflow-library-aisb` library already uses** so
the assembler ([webflow-component-build.md](webflow-component-build.md)) names new props
consistently and a `brand.yaml` `componentMapping[slot-role]` resolves to a real prop name
**predictably** (the machine-composability point). It does **not** invent a new grammar — it
writes down the existing one. The full class/variable/component conventions are canonical in
the library skill; this is the prop-naming companion.

## Canonical references (read first — do not restate)

- Naming conventions (components, props, variables, **classes**) + prop-type distribution:
  [webflow-library-aisb SKILL.md](../../../.cursor/skills/webflow-library-aisb/SKILL.md) "Naming conventions".
  **The FlowKit class grammar (`property_value` + `is-*`/`on-*`/`gap-*` combos) lives there —
  link to it, do not duplicate it here.**
- How `componentMapping[].props` is expressed: [brand-schema.md](brand-schema.md) §4.2.
- Where prop names are applied in the build: [webflow-component-build.md](webflow-component-build.md).

## The existing grammar (formalized)

### Prop names: Title Case, grouped

- **Title Case** prop names, multi-word with spaces: `Media side`, `Align vertical`,
  `Space bottom`, `Content width`, `Aspect ratio`, `Form ID`. (Not snake_case, not
  `group_property`.)
- Props are **grouped in the panel by component area** (e.g. a card's media controls vs its
  text controls). Keep a new prop in the group its element belongs to.

### Logical groups (how the library already expresses them)

Every prop falls into one of these logical roles. Use them to decide *whether a prop is needed*
and *what to call it* — they describe the existing kit, they are not new field prefixes:

| group | controls | how the library expresses it |
|---|---|---|
| **content** | the words/media a slot shows | `textContent` (`Title`, `Label`, `Text`), `image`, `richText`, `altText`, `link`, `headingTag` (`Tag`), `id` (`Form ID`) |
| **style** | visual treatment within a fixed layout | `variant` (`Style`, `Color`, `Size`, `Aspect ratio`, `Variant`) |
| **layout** | arrangement/position of slots | `variant` (`Media side`, `Align`, `Align vertical`, `Columns`, `Gap size`, `Direction`, `Width`, `Content width`, `Side`) |
| **visibility** | whether an element renders | `boolean` (`Media`, `Background`, `Overlay`, `Space bottom`, `Radius`, `Interaction`) |
| **state** | interaction/behavior modes | `boolean`/`variant` (`Interactivity`, `Wrap down`, animated-state utilities) |

(Prop-type counts across the kit: variant 155, boolean 98, textContent 64, slot 30, image 25,
link 18, string 6, headingTag 5, richText 3, altText 3, id 1 — see the library skill.)

### Booleans: visibility/toggle with true/false labels

- Booleans are **toggles** (mostly visibility/state): `Background`, `Overlay`, `Media`,
  `Radius`, `Space bottom`, `Interaction`, `Wrap down`.
- They carry **true/false labels** that read naturally in the panel (e.g. `Auto`/`None`), not
  bare `true`/`false`. Name the prop after *what it shows/does*, phrased so "on" is the
  affirmative (`Background` on = background shown).

### Variant props: enumerated choices

- Any **enumerated** choice is a `variant` prop, not a string: `Style`, `Color`, `Size`,
  `Align`, `Media side`, `Columns`, `Aspect ratio`, `Variant`.
- Variant **values take the variant ID** at build time (defaults in `components.json`, or
  `get_component` with `includeVariants`) — never a free-text label.
- Add a new variant **option** only when an existing option doesn't cover the need
  (reuse-before-create at the option level too).

## Reuse the name before inventing one

Before creating a prop, **search the inventory for an existing prop with the same role and
reuse its exact name** (grep `components.json`). Library precedent wins:

- a side/position toggle → `Media side` / `Side` (not `mediaPosition`, not `image_side`)
- vertical alignment → `Align vertical` (not `vAlign`, not `vertical_align`)
- a show/hide media toggle → `Media` (not `showMedia`, not `media_visible`)
- a width preset → `Width` / `Content width` (not `maxWidth`, not `container_width`)
- a visual treatment → `Style` (not `appearance`, not `style_variant`)

When forwarding a primitive's prop onto a composite ([webflow-component-build.md →
forward primitive props](webflow-component-build.md#forward-primitive-props)), **reuse the inner
primitive's prop name on the outer component** so the binding reads 1:1 (outer `Text` → inner
`Heading.Text`). Invent a name only when no precedent exists; then keep it Title Case + in the
right group.

## brand.yaml slot-role → real prop name (predictable mapping)

`brand.yaml` `componentMapping[]` gives each slot a semantic `role` and a `props` object. The
assembler resolves it **deterministically**:

1. The `component`/`componentId` fixes which real component (and therefore which **prop
   namespace**) applies.
2. Each `props` **key is already the real Title Case prop name** (the analyst wrote it from the
   library inventory — analyst phase 3). The assembler does **not** translate or rename it; it
   looks up that prop id on the live component and sets it.
3. If a `role` needs a control with no `props` key yet, choose the prop by **logical group +
   reuse-the-name** above, then (if it truly doesn't exist) create it.

Worked example (from the schema's Woodwave `brand.yaml`):

```yaml
componentMapping:
  - { slot: "Slot 2", role: "panel title", component: "Heading",
      componentId: "b2fd0399-…", props: { Tag: "h3" } }
  - { slot: "Slot 2", role: "action row",  component: "Link / Secondary",
      componentId: "75c4556a-…", props: { Label: "Buy Tickets", Style: "arrow" } }
```

→ `Tag` (headingTag/content), `Label` (textContent/content), `Style` (variant/style) are each
**real existing prop names** set directly on the instance — no invented grammar, no renaming.

## Classes (cross-reference only)

Spacing/behavior on real pages is applied via **Utility components and variants**, not by
hand-writing classes (library Operating rules). The FlowKit class grammar — `property_value`
with underscores (`padding-bottom_medium`, `max-width_xlarge`), `is-*` state combos, `on-*`
scheme combos, `gap-*` gap utilities, responsive helpers — is **fully documented in the
library skill**; reuse those, never invent a parallel convention. See
[webflow-library-aisb SKILL.md](../../../.cursor/skills/webflow-library-aisb/SKILL.md) "Naming conventions".
