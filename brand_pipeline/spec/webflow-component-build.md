---
name: webflow-component-build
description: >-
  Build one Webflow section at a time from a validated brand.yaml against the
  webflow-library-aisb component inventory. Use when assembling a page section
  (decide reuse-vs-create, instantiate a Section/Layout scaffold, add logically
  grouped props, variants and slots, fill slots with component instances, forward
  primitive props by binding down), when running the proven duplicate→rename→open→
  props→bind→close Webflow MCP recipe, when a slot/prop/variable is rejected (emit
  a build-failure signal), or when verifying an assembled section. Recurses: a
  section is a component with slots whose contents are themselves components.
  Pairs with webflow-token-mapping (run once first) and prop-naming.
---

# webflow-component-build

> **STATUS: SPEC / review draft — not active until `brand.yaml` is validated; install
> as a skill only after the Art Director + render gate pass.** This file lives in the
> review folder `design-system-extractor-mine/brand_pipeline/spec/`. Do **not** copy it
> into `.cursor/skills/` yet. Links below resolve from **this review folder**
> (`brand_pipeline/spec/`); on install they get rewritten to be relative to
> `.cursor/skills/webflow-component-build/` (mirroring `brand-layout-analyst`).

Build a Webflow page **one section at a time** from a validated `brand.yaml`, composing
real `webflow-library-aisb` components. This skill is a **method an agent invokes**: per
section it decides reuse-vs-create, instantiates a scaffold, adds logically grouped props /
variants / slots, fills slots with component instances, and forwards primitive props by
binding down. It runs **after** [webflow-token-mapping.md](webflow-token-mapping.md) (variables
+ modes ready) and obeys [prop-naming.md](prop-naming.md).

## Assembler architecture (shared)

```
                         ┌──────────────────────────┐
   brand.yaml (validated)│  (carries tokens, layouts[],
        │                │   componentMapping[], do[]/avoid[],
        │                │   recipePolicy — see brand-schema.md)
        ├──────────────► │ webflow-token-mapping   (ONCE per brand)
        │                └──────────┬───────────────┘
        │                           ▼  variables + surface/responsive modes ready
        │                ┌──────────────────────────┐
        └──────────────► │ webflow-component-build  (PER SECTION) │ ──► Webflow page
                         └──────────┬───────────────┘
                                    │ both skills follow prop-naming.md
                                    ▼
                         build-failure signals ──► signals.log  (signal-loop.md)
                                    │  auto-promote → recipePolicy / neverDo
                                    └──► future builds avoid the rejected move
```

**Sequencing (wired LAST):** this assembler layer is connected only **after `brand.yaml`
is validated** via the fast extractor-side render + on-brand gate (`render_section.py` →
`onbrand_check.py`). Don't debug brand quality and flaky MCP at once — validate the brand,
map tokens once, then build sections.

## Canonical references (read before deep work — do not duplicate)

- Component inventory, IDs, slot flags, MCP how-to, Operating rules 1–4:
  [webflow-library-aisb SKILL.md](../../../.cursor/skills/webflow-library-aisb/SKILL.md). **Grep `components.json`
  for a specific component/prop/slot id; never load it whole, never invent ids.**
- The prop grammar both skills obey: [prop-naming.md](prop-naming.md).
- One-time variable setup that must precede this: [webflow-token-mapping.md](webflow-token-mapping.md).
- What `brand.yaml` supplies (`layouts[]` archetype + scaffold, `componentMapping[]`,
  `recipePolicy`, `neverDo`): [brand-schema.md](brand-schema.md) §4.
- Archetype → real scaffold table + composite handling: [brand-layout-analyst SKILL.md](../../../.cursor/skills/brand-layout-analyst/SKILL.md).
- The build-failure signal contract: [signal-loop.md](signal-loop.md).

## Inputs / Output

- **Inputs:** a validated `brand.yaml` (`layouts[]` with `archetype`/`scaffold`/`slots`/
  `componentMapping[]`, plus `recipePolicy`, `neverDo`); variables already mapped by
  webflow-token-mapping; the live library via webflow-library-aisb.
- **Output:** real Webflow components/instances on the page; `build-failure` signals into
  `signals.log` on any rejection. Does not edit `brand.yaml` design language (it consumes it)
  and never edits `brand.md`.

## The per-section build loop (deterministic, numbered)

Build **one section per pass**. The section is named by a `brand.yaml` `layouts[].id`; its
`archetype`/`scaffold` and `componentMapping[]` drive the choices.

```
Section build progress (one layouts[] entry):
- [ ] 1. Decide reuse-or-create for the section scaffold
- [ ] 2. Open the component
- [ ] 3. Add props to modify content (logically grouped — prop-naming.md)
- [ ] 4. Add variants if needed
- [ ] 5. Add slots
- [ ] 6. Close; fill slots with component instances
- [ ] 7. For each slot child: reuse closest library component → add to slot →
        open → modify → add content/visibility props + variants  (RECURSE)
- [ ] 8. Verify the assembled section
```

**1. Reuse-or-create the scaffold.** Read the layout's `archetype` + `scaffold` (the analyst
already mapped it to a real `Section / *` or `Layout / *` — reuse-before-create, library rule
2). Search the inventory to confirm (`query_components`, or grep `components.json`).
- **Reuse path (default):** `duplicate_component` the matched scaffold of that type, then
  rename. Composites (`band`/`collage`/`overlay`) reuse `Section / Stack` (nearest `Section /
  *`) + absolute offsets in the slot — **no new library component** (analyst SIGN-OFF #5).
- **Create path (true miss only):** create a new component, and **compose it from existing
  primitives**, forwarding their props (step 7 + [forward primitive props](#forward-primitive-props)).

**2. Open the component** to edit its internals (`open_canvas` with the component id;
`get_current_component`).

**3. Add content props**, logically grouped per [prop-naming.md](prop-naming.md) (content /
style / layout / visibility / state; Title Case grouped names that match the existing library —
e.g. `Media side`, `Align vertical`). Map each `componentMapping[].props` key onto a real prop
name predictably (prop-naming "slot-role → prop name").

**4. Add variants** for enumerated choices (variant props), only when a needed option is not
already covered by an existing variant.

**5. Add slots** that the composition requires (only when the scaffold lacks a needed slot).

**6. Close, then fill slots with component instances.** Exit the component (`open_canvas` with
the page id). Fill each slot via `component_builder` `insert_in_slot` (`slot_name` required) or
`insert_component_instance`. **Only component instances may go in slots — never raw elements**
(library rule 1 / `recipePolicy.slotsTakeInstancesOnly`).

**7. Recurse into slot children.** For each child the `componentMapping[]` calls for: reuse the
**closest** existing library component (prefer leaf primitives — `Heading`, `Subheading`,
`Eyebrow`, `Paragraph`, `Rich Text`, `Image`, `Logo`, `Link / *`, `Button / *`, `Card / *`,
`Form / Webflow / Lead`), add it to the slot, open it, modify it, and add its own content props
(text/image), variants, and **visibility props**. See recursion below.

**8. Verify** (see [Verification](#verification)).

## Recursion is explicit

A **section is a component with slots**. Each slot holds **components**, and those components
**themselves have props, variants, and slots**. The *same numbered procedure (1–8) applies at
every level*:

```
Section (component, has slots)
└─ Slot ── child component (has props/variants/slots)
            └─ Slot ── grandchild component (has props/variants/slots)
                        └─ … (leaf primitive: props only, no slots)
```

Stop descending at leaf primitives (no slots). At each non-leaf level you decide
reuse-or-create, open, add grouped props/variants/slots, close, and fill — identical to the
top-level loop.

## Reuse-before-create, compose-from-primitives, forward props

These map directly onto library Operating rules 1 & 2 and `recipePolicy`:

- **Reuse-before-create** (rule 2): map the need onto an existing component/variant/prop first;
  create only on a true miss.
- **Compose-from-primitives**: a new composite is assembled from existing primitives inside the
  scaffold's slots, not authored from scratch.

### Forward primitive props

When a new composite needs to expose an inner primitive's control, **create a matching prop on
the outer component and bind it down** (library "Expose primitive props on a composite"):

1. `de_component_tool > create_prop` on the new (outer) component (name it per prop-naming.md).
2. `open_canvas` (component_id) to enter the component.
3. On the inner element/instance: `element_tool > get_bindable_sources`.
4. Wire the outer prop down: `set_settings` (or `set_component_instance_prop_values` with
   `type: "bindable"`, `binding_source_type: "prop"`, `binding_prop_id: "<outer prop id>"`).

The outer prop name should reuse the inner primitive's prop name where sensible (prop-naming
"reuse the name before inventing one").

## Proven MCP build recipe (verified live)

This concrete sequence was confirmed against the live site via
`plugin-webflow-webflow > de_component_tool` and friends. Use it, not theory. Site id +
exact ids: [webflow-library-aisb SKILL.md](../../../.cursor/skills/webflow-library-aisb/SKILL.md).

```
duplicate_component(source_component_id, name: "<new section name>")   # reuse path
   → set_component_metadata(component_id, name: "<rename>")            # rename
   → open_canvas(component_id) + get_current_component                 # enter to edit
   → create_prop / update_prop                                        # add/adjust props
   → element_tool > get_bindable_sources                              # find bind targets
   → set_settings  (or set_component_instance_prop_values bindable)   # bind prop → element
   → open_canvas(page_id)                                             # exit back to page
```

Then fill slots on the page (`component_builder insert_in_slot` / `insert_component_instance`),
set instance props (`get_component_instance_props` → `set_component_instance_prop_values`;
re-fetch prop ids **per instance**), and apply surface modes on styles
(`set_style_variable_mode`).

Pitfalls (from the library skill): re-fetch instance prop ids per instance; `Form / Webflow /
Lead` needs a unique `Form ID`; drop `FlowKit Icons — Phosphor` on pages using `Icon /
Phosphor`; the `Width`/`Section padding`/`Grid gap`/`Shadows` collections theme via **modes on
styles**, not per-element values.

## Build-failure signal emission

When Webflow/MCP **rejects** a move, the platform just told you a rule. Emit a `build-failure`
signal so it auto-promotes into `recipePolicy`/`neverDo` (`source: failure`, `confidence: high`,
no user confirmation — [signal-loop.md](signal-loop.md) SIGN-OFF #4). Then adapt and continue.

Common rejections → signals:

| rejection | becomes |
|---|---|
| size variable rejects `clamp()` | `recipePolicy` "no clamp() in size variables" |
| duplicate `Form ID` on `Form / Webflow / Lead` | `recipePolicy.formIdUnique` |
| slot rejects a raw element | `recipePolicy.slotsTakeInstancesOnly` (reinforce) |
| color variable created outside `Brand colors` rejected | `recipePolicy` "new colors in Brand colors only" |

Signal shape (one JSONL line into `signals.log`, full schema in
[signal-loop.md](signal-loop.md) §2):

```jsonc
{
  "id": "sig-<ts>-<rand>",
  "type": "build-failure",
  "sectionId": "<layouts[].id>",
  "text": "Form/Webflow/Lead requires unique Form ID; build rejected duplicate",
  "ruleKey": "recipePolicy.formIdUnique",
  "detectedConflict": false,
  "conflictWith": null,
  "resolution": "promote",
  "scope": "design-language",
  "confidence": "high",
  "questionId": null,
  "timestamp": "<iso8601>"
}
```

## Verification

After each section is assembled:

- `element_snapshot_tool` on the section's element id (visual/structure check).
- `element_tool > get_all_elements` (style flags off) for a structure-only pass.
- Confirm: only instances in slots; surface modes applied via styles (not raw values);
  no `neverDo[]` violation from `brand.yaml`; created variables limited to `Brand colors`.

Only proceed to the next section once the current one verifies.
