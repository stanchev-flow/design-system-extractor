---
name: webflow-token-mapping
description: >-
  Map a validated brand.yaml's tokens onto the webflow-library-aisb variable
  system once per brand, before any section is built. Use when bridging brand
  colors/type/spacing/surfaces onto real Webflow variables by ROLE, creating
  missing variables in the Brand colors collection, choosing color-scheme vs
  responsive modes, theming surfaces via Color schemes modes (never hand-set raw
  values), or recording the token→variable map + created-variables provenance back
  into brand.yaml. Pairs with webflow-library-aisb (the site-specific ID/token map)
  and webflow-component-build (the per-section build loop).
---

# webflow-token-mapping

> **STATUS: SPEC / review draft — not active until `brand.yaml` is validated; install
> as a skill only after the Art Director + render gate pass.** This file lives in the
> review folder `design-system-extractor-mine/brand_pipeline/spec/`. Do **not** copy it
> into `.cursor/skills/` yet. Links below resolve from **this review folder**
> (`brand_pipeline/spec/`); on install they get rewritten to be relative to
> `.cursor/skills/webflow-token-mapping/` (mirroring `brand-layout-analyst`).

Take a **validated** `brand.yaml` and bridge its tokens onto the real
`webflow-library-aisb` variable system **once per brand**, as setup before any section
is built. This skill is a **method an agent invokes** — it reads brand tokens, matches
each to an existing library variable **by role**, creates only what is genuinely
missing (in the Brand colors collection), and records the mapping + provenance back
into `brand.yaml`. It never hand-sets raw hex/px in styles and never edits `brand.md`.

## When to use this

- **Brand bridge / retarget**: a new `brand.yaml` is validated and the library must be
  re-themed to it before building pages.
- **Map-then-extend tokens**: match each brand token to an existing variable role; create
  a new variable only on a true miss.
- **Decide modes**: pick the right collection + mode meaning (surface theme vs responsive
  breakpoint) for a token.
- **Record provenance**: write the token→variable map + created-variables list into
  `brand.yaml` `tokens` (status `mapped|created`).

## Canonical references (read before deep work — do not duplicate)

- Library variable/token/ID map + the MCP how-to: [webflow-library-aisb SKILL.md](../../../.cursor/skills/webflow-library-aisb/SKILL.md)
  (Operating rule 3 *map-then-extend*, rule 4 *theme with modes*). **All site-specific IDs
  live there — grep `variables.json` for a specific variable/collection/mode id; never load
  it whole and never invent ids.**
- How `brand.yaml` expresses tokens + provenance: [brand-schema.md](brand-schema.md) §3 `tokens`.
- The per-section build loop this setup precedes: [webflow-component-build.md](webflow-component-build.md).
- The build-failure signal contract: [signal-loop.md](signal-loop.md).

## Inputs / Output

- **Inputs:** a validated `runs/<brand>/brand/brand.yaml` (its `tokens` block);
  the live library variable system via the **webflow-library-aisb** skill (grep
  `variables.json` for names + ids).
- **Output:** updated/created Webflow variables on the site, **plus** mutations to
  `brand.yaml` `tokens` recording each token's `mapsTo` / `variableId` / `collection` /
  `mode` / `modeId` / `status` (`mapped|created`) — see [Output artifact](#output-artifact).
  Writes no other artifact; never edits `brand.md`; never touches the live page tree.

## The core rule: theme via modes and collections, never hand-set raw values

Every brand token resolves through a **variable**, and every per-surface or per-viewport
difference resolves through a **mode** on a *style* — not a literal value pasted onto an
element. Concretely:

1. **Map by role, not by name.** `accent → Core Accent/Accent Primary`,
   `body font → Typography > Font/Body Font`, `radius → Sizes > Radius/*`,
   `section padding → Sizes > Section/Section Padding Vertical`.
2. **Update the variable's value** with `update_*_variable` (map-then-extend, library rule 3).
3. **Bind styles to the variable** (`variable_as_value`), never a raw hex/px.
4. **Theme surfaces/breakpoints by switching modes** on the style (`set_style_variable_mode`),
   never by overriding the value (library rule 4).

## Collections and modes — the precise surface-vs-responsive model

**Both colors and sizes use modes. What differs is the *meaning* of a mode switch.**
(The loose framing "colors live in modes, sizes live in responsive collections" is
*imprecise* — sizes are also moded; the distinction below is what matters.)

| mode meaning | collections | modes | a mode switch is triggered by… |
|---|---|---|---|
| **SURFACE THEME** | `Color schemes`, `Card color schemes` | 6 / 5 | a **section/card surface change** (Primary / Secondary / Accent / Inverse). |
| **RESPONSIVE BREAKPOINT** | `Sizes`, `Typography`, `Grid gap`, `Width`, `Section padding`, `Shadows` | 3–4 | a **viewport change** (base / Tablet / Mobile). |

**The rule, stated precisely:**

- A **surface** difference (this band is dark, this card is accent-colored) = a
  **color-scheme mode** switch applied to the section/card style — *or* a component
  scheme prop / `on-*` combo. Never a hand-set color.
- **Responsiveness** (smaller type/spacing/gap/width on tablet/mobile) = a **size/type
  mode** switch carried automatically by the responsive collections. Never a per-element
  size override.
- `Brand colors` has **no modes** — it holds the raw brand surface values. `Color schemes`
  / `Card color schemes` alias *into* `Brand colors` per surface mode. (Layering detail:
  webflow-library-aisb → "How the system layers".)

## Mapping procedure (run once per validated brand)

```
Token mapping progress:
- [ ] 1. Snapshot the library variable system
- [ ] 2. For each brand token: match an existing variable ROLE
- [ ] 3. Update matched variables (map-then-extend)
- [ ] 4. Create only true-miss variables — in Brand colors
- [ ] 5. Wire surface modes on schemes; confirm responsive modes
- [ ] 6. Record the map + created-variables provenance into brand.yaml
- [ ] 7. Verify, then hand off to webflow-component-build
```

**1. Snapshot.** `variable_tool > get_variable_collections`, then `get_variables`
(`include_all_modes: true`) — discover roles + ids. (Use the site id from the library skill.)

**2. Match by role.** For each `brand.yaml` token, find the existing variable whose **role**
fits (colors → `Core Accent/*`, `Core Neutral/*`, `Core Text Color/*`; type → `Font/*`,
`H*/*`, `Text *`; spacing → `Spacing/*`, `Gap/*`, `Section/*`, `Container/*`, `Radius/*`).
Prefer a match over a new variable (library rule 2/3).

**3. Update matched.** `variable_tool > update_*_variable` to set the variable's value to the
brand token value. For a brand bridge, updating `Brand colors` values + `Typography > Font/*`
re-themes the whole library through the alias chain.

**4. Create only on a true miss.** When no role fits, create the variable **in the `Brand
colors` collection only** (per library rule 3 — new colors go nowhere else). Mark the token
`status: created` and add it to the created-variables list (step 6).

**5. Modes.** For each surface role in `brand.yaml` (`tokens.surfaces`), confirm the
`Color schemes` mode it maps to (`schemeMode`/`schemeModeId`); the section/card style gets
that mode at build time via `set_style_variable_mode` (read back with
`get_style_variable_modes`). Responsive collections (`Sizes`/`Typography`/…) carry their own
base/Tablet/Mobile modes — no per-token work beyond confirming the size/type variable exists.

**6. Record provenance** (see below).

**7. Verify** the updated/created variables read back as expected, then hand off to
[webflow-component-build.md](webflow-component-build.md).

## MCP calls (reference the library how-to for exact ids)

All calls use the site id and conventions in [webflow-library-aisb SKILL.md](../../../.cursor/skills/webflow-library-aisb/SKILL.md)
("MCP how-to"). Designer must be open on the site.

- **Discover:** `variable_tool > get_variable_collections` → `get_variables`
  (`include_all_modes: true`).
- **Map-then-extend (update existing):** `variable_tool > update_*_variable` with the
  matched `variableId`.
- **Create a true-miss variable:** create it in the **Brand colors** collection only.
- **Bind a style to a variable:** `style_tool > create_style`/`update_style` with
  `variable_as_value: "<variable-id>"`.
- **Apply a surface mode to a style:** `variable_tool > set_style_variable_mode`
  (`{style_name, modes: [{collection_id, mode_id}]}`); read back with `get_style_variable_modes`.

**Never** paste a raw hex/px into a style when a variable exists; **never** create color
variables outside `Brand colors`.

## Output artifact

The mapping is recorded **into `brand.yaml`'s `tokens` block** (it is the canonical home —
this skill does not invent a new file). Per [brand-schema.md](brand-schema.md) §3, each token
carries:

```yaml
tokens:
  colors:
    accent/highlight:
      value:      "#E9DC8C"
      mapsTo:     "Core Accent/Accent Primary"   # role match, not name match
      variableId: "variable-…"                   # from variables.json (grep) or create
      collection: "Brand colors"
      mode:       null                            # Brand colors has no modes
      modeId:     null
      status:     mapped                          # mapped | created
      provenance: [<sectionId>…]
```

Two derived records the build loop relies on:

- **token→variable map** = the set of `{token → mapsTo/variableId/collection/mode/status}`
  rows above (every token resolved to a real variable).
- **created-variables list** = every token with `status: created` (each a new `Brand colors`
  variable). These are the only additions to the library; surface them in the run's
  provenance so the user can review what was created vs reused.

Surface mode bindings live in `tokens.surfaces[*].schemeMode/schemeModeId`; responsive
ladders live in `tokens.type[*].sizeRem{base,tablet,mobileL,mobile}` and
`tokens.spacing[*].modeLadder` — the build loop reads these to pick modes, never raw values.

## Build-failure signals

If the variable API rejects a value (e.g. a `clamp()` expression on a size variable, an
out-of-range mode), **emit a `build-failure` signal** per [signal-loop.md](signal-loop.md)
so it auto-promotes into `recipePolicy`/`neverDo` (`source: failure`, `confidence: high`).
Signal shape and emission are documented in [webflow-component-build.md](webflow-component-build.md#build-failure-signal-emission).

## Sequencing (wired LAST)

This setup runs **only after `brand.yaml` is validated** via the fast extractor-side render
+ on-brand gate (`render_section.py` → `onbrand_check.py`, see `brand-layout-analyst`). Do
not debug brand quality and flaky MCP at the same time: validate the brand first, then map
tokens, then build sections.
