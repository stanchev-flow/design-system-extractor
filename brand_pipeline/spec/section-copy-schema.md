# section-copy-schema.md — `runs/<brand>/brand/section-copy.yaml` (v1)

> Status: **v1, Phase A of the extraction redo.** Documents the file
> `compose_section.py` ALREADY consumes (`load_brand_copy` /
> `attach_brand_copy` / `copy_for` — this spec describes, it does not change,
> that behavior). The extraction flow must EMIT this file for every brand:
> a brand without one composes every section with empty copy (the
> "wordmark + arrow" degraded renders the Remote run shipped with).
> `tools/extract/validate_brand_evidence.py` C4 enforces presence + shape.

## 1. Role in the pipeline

`section-copy.yaml` is BRAND DATA: the brand's authored voice bound to the
brand's extracted layouts. Composers read copy through three layers, merged in
`copy_for(layout, doc)` (later wins):

1. `sectionCopy` — page-global base (file, this schema)
2. runtime `SECTION_COPY` module patches (adapters/tests only, normally empty)
3. the layout layer for this section id: a runtime-registered `LAYOUT_COPY`
   entry (composition adapter / wildcard generator) replaces the file's
   `layoutCopy[<id>]` **wholesale**; otherwise the file entry applies.

The merged dict is a `_SafeCopy`: any key no layer declares resolves to `""`,
and renderers elide empty devices. Degradation is silent BY DESIGN — which is
why the validator, not the composer, is where absence fails loud.

Loading (`load_brand_copy`) is defensive: a missing file, unparseable YAML, or
a non-mapping top level all degrade to empty layers. Non-dict `layoutCopy`
values and non-dict `layoutImages` values are dropped silently; `defaultArt`
values must be lists.

## 2. Top-level keys (all optional, no others are read)

```yaml
sectionCopy:   {…}   # page-global copy base
layoutCopy:    {…}   # per-layout-id overrides, merged over the base
layoutImages:  {…}   # per-layout REAL photography bindings
defaultArt:    {…}   # preferred default/fallback art filenames per role kind
wildcardCopy:  {…}   # copy blocks for wildcard-generator candidates
```

## 3. `sectionCopy` — page-global base

Keys any composer may read. The load-bearing ones:

| key | consumed by | notes |
|---|---|---|
| `wordmark` | nav/footer wordmark device | REQUIRED in practice — nav renders wordmark-only without it |
| `nav` | nav link labels (list of strings) | brand.yaml `navbar.primary` is the chrome source; this is the copy-level fallback some harnesses use |
| `specimenEyebrow` | components-preview eyebrow specimen | numbered-register text; any prefix device comes from `tokens.type.eyebrow.prefix`, not this string |
| `eyebrow`, `subhead`, `cta` | hero + generic section composers | page-global defaults when a layout doesn't override |

Extraction rule: populate from the SOURCE site's real voice (grounding YAML
`copy` blocks), never invented, never borrowed from another brand.

## 4. `layoutCopy` — per-layout-id copy layers

`layoutCopy.<layout-id>` is a dict merged OVER `sectionCopy` for that section
only. Keys are composer-defined; the working vocabulary across the current
composers (`compose_section.py` `copy["…"]` reads):

- common: `eyebrow`, `heading`, `subhead`, `body`, `caption`, `cta`, `ghost`
- quote/testimonial: `quote`, `caption` (attribution)
- panel/info composers: `panelTitle`, `rows` (list of `[label, value]` pairs)
- visit/map composer: `mapCaption`, `ticketsTitle`, `ticketsRows`, `ticketsCta`,
  `visitTitle`, `visitRows`, `visitCta`
- form/conversion: `placeholder`
- counters/meta: `counter`

Multi-line headings use YAML block/quoted scalars with `\n` line breaks
(composers honor explicit breaks). A key a composer needs but the layer lacks
renders as empty copy for that device — list every content slot's copy for
every content-bearing layout (validator C4 checks coverage).

## 5. `layoutImages` — per-layout photography

```yaml
layoutImages:
  <layout-id>: { <role-substring>: <filename-in-brand-inventory> }
```

Read via `brand_layout_images(doc)` in `_props_for` BEFORE the generic image
fallback: when a slot's role/description contains `<role-substring>`
(case-insensitive), that file is bound as the slot's art. Filenames must exist
in the brand's own on-disk inventory (recursive under the brand dir — AS-34);
a name with no disk evidence simply never matches.

```yaml
# example shape (values are per-brand data, not part of the schema)
layoutImages:
  mission-statement: {statement photography: About-img-2.jpg}
```

## 6. `defaultArt` — preferred fallback art per generic role kind

```yaml
defaultArt:
  hero:     [<preferred-filename>, …]   # first that EXISTS in inventory wins
  detail:   […]
  gallery:  […]
  portrait: […]
  map:      […]
  overlays: […]        # layered-hero overlay cycle IN ORDER (overlay N prefers overlays[N])
  occlusion-main: […]
```

Resolved through `_brand_art`: first preferred name present in the ACTIVE
brand's inventory, else the generic keyword match for the kind (`hero` →
"hero/full-bleed/cover", `detail` → "overlap/detail/closeup/texture", `gallery`
→ "gallery/interior/showcase", `portrait` → "portrait/avatar/curator", `map` →
"map"), else the device is OMITTED — art is only emitted on disk evidence,
never borrowed cross-brand.

## 7. `wildcardCopy` — wildcard-candidate copy blocks

```yaml
wildcardCopy:
  <candidate-render-id>:   # e.g. wildcard-hero-ghost
    ghost: …
    eyebrow: …
    heading: "line one\nline two"
    body: >-
      …
    caption: …
    cta: …
```

Read via `brand_wildcard_copy(doc)`. A candidate that NEEDS brand voice and has
no block here is SKIPPED (logged) — wildcard copy is never seeded from another
brand.

## 8. Authoring rules for the extraction flow

- Source of truth: the per-section grounding YAMLs' verbatim `copy` blocks
  (vision pass) cross-checked against the DOM mine. Real site copy, adapted
  minimally to the layout's slot vocabulary.
- One `layoutCopy` entry per content-bearing layout in `brand.yaml` — the
  validator errors on uncovered layouts (chrome layouts exempt: nav archetype,
  `footer`).
- `wordmark` always set; eyebrow specimen text always from the brand's own
  register.
- No cross-brand text: `test_no_cross_brand_dna.py` treats another brand's
  distinctive strings in shared code as contamination; the same discipline
  applies inside a brand's own copy file (only THIS brand's voice).
- Keep the file's top level to the five documented keys — anything else is
  ignored silently today and may collide with future schema growth.
