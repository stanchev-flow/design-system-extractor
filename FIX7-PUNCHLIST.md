# FIX7 — Accent application, list/stat devices, heading fit (gallery review round 3)

User review of the hero-archetype gallery (developer + demo heroes, 2026-07-14) surfaced
seven defects. All fixes are SYSTEM-LEVEL: shared mechanics stay palette-agnostic and
brand-agnostic; brand specifics live in brand data. Do not patch the two lanes cosmetically.

STATUS: **LANDED** (2026-07-14, after the two queued agents — steals Stage B and
pass 3 — landed). Full record: root `changes.md` (fix7 entry) +
`runs/hubspot-v2/brand/changes.md` (fix7 section). Suite **1347 passed** (baseline
1259, zero lost; +76 fix7 tests, +12 from a concurrent eval-matrix baseline file
that landed mid-pass — green under the combined code); replicas **improved**:
hubspot-v2 0.956 → **0.957**, Remote 0.950 → **0.951** — the replica CAUTION
below confirmed in the right direction (the source hero DOES carry the orange
period; applying the device closed a gap).

## Per-item landing table

| # | item | what landed | where | tests |
|---|---|---|---|---|
| 1 | Accent device application (floor) | `accentDevices:` license block (brand-schema **§4.11**) + renderer punctuation-accent (terminal-mark wrap on landmark headings, incl. composer-declared hero-split landmarks) + `--c-accent-mark` device-role var + signature FLOOR mode (`check_accent_device_floors`: per-context floors/ceilings over rendered `data-accent-device` stamps) + licensed-roster block in the pass-3 prompt injection. hubspot-v2 data: 3 licenses authored (orange-period floor 1 on hero; checkmark list; underline roster entry) + `accentDevice` joined the accent-scope signature's allowedRoles. Remote checked: hover-only underline = interaction treatment, NO devices authored (documented, not invented) | `component_render.py` (render_heading/`_wrap_terminal_mark`/`accent_device_css`), `compose_section.py` (landmark flag on split-hero headings), `signature_audit.py`, `generate_composition.py` (`_accent_device_lines`), `runs/hubspot-v2/brand/brand.yaml` | `test_fix7_devices.py` PunctuationAccentDevice (9) |
| 2 | Knob-consumption lint (AS-63) | NEW `brand_pipeline/composition_lint.py` `lint_knobs`: every knob must be code-consumed (`KNOB_CONSUMERS` registry, test-pinned to real consuming source) or archetype-declared with an in-enum value (YAML-boolean spellings accepted). Wired as generation-loop prefilter 4c (hard, repairable) + `knob-consumption` gate row in `onbrand_check --composition`. `supportKind: "list"` proved the case; 5 gallery knob values sat outside their enums and were normalized (render-neutral data fixes) | `composition_lint.py`, `generate_composition.py`, `onbrand_check.py`, gallery compositions | `test_fix7_lints.py` KnobConsumptionLint (9) |
| 3 | Checklist device (marked list) | `render_marked_list` (semantic `<ul.c-marked-list>`: licensed glyph markers via the sanitized inline-SVG channel, hanging indent by grid construction, `--space-list-item-gap` stride, typographic-dot degrade) + `attach_accent_devices` glyph resolver + form-split `supportKind` consumption (`data-list-intent` stamp). hubspot glyph: `icon-success.svg` already harvested (32-grid currentColor sprite, fix5-repaired) — licensed via accentDevices. AS-64: hard arm (declared intent rendering plain paragraphs) + advisory arm (3+ parallel short siblings) on the new slop ADVISORY channel. AS-14 counts substantive marked-list items as the form's stated reason | `component_render.py`, `compose_section.py`, `compose_from_composition.py`, `slop_audit.mjs`, `contracts/archetypes/heroes-saas.yaml` (supportKind enum += list) | `test_fix7_devices.py` MarkedListDevice (7) |
| 4 | Stat pair binding | `.c-stat` internal gap re-registered from the leaked eyebrow-to-heading seam to `--space-stat-pair` (brand token when authored; 0.5rem structural default) + `.cs-split-body > * + .c-stat` separation margin (+0.5x the column's sibling gap). NEW spacing cells `stat.pair-binding` / `stat.pair-separation` (relational: pair <= 0.5x sibling gap, separation >= 1.5x — violation px on the center-family scale; spec §statPair). Demo measures pair 8px vs sibling 32 (budget 16) and separation 48 vs 48 — both conform | `component_render.py`, `compose_section.py`, `spacing_audit.py`, `spec/spacing-conformance.md` | `test_fix7_devices.py` StatPairBinding (3); live cells in the demo spacing report |
| 5 | Heading fit-to-measure stepping | Deterministic step-down: `heading_fit_level` (greedy word-wrap projection, 0.6em mean advance calibrated on the stage-B measured wraps) walks display→h1→h2 MEASURED rungs until the hero cap (3 lines) fits the `split_half_measure_px` column (container + column-gutter facts → 500px for hubspot). The heading keeps its display class/semantics; SIZE re-registers via `data-fit-rung` CSS (the pass1 overlay-panel channel — every magnitude on the ladder, AS-62-safe). `data-fit-cap` stamps the contract; AS-66 (slop) hard-fails a stamped column whose heading exceeds its cap. Demo: 80px/4-lines → 48px h1 rung/2 lines | `compose_section.py` (`heading_fit_level`/`projected_line_count`/`split_half_measure_px`, `_compose_form_split`), `slop_audit.mjs` | `test_fix7_devices.py` HeadingFitToMeasure (8) |
| 6 | Note discipline + redundancy (AS-65) | Foot-form notes route to the CAPTION register and render BELOW the control inside the control-width `.cs-hero-form` wrapper (balanced wrap via the component base). `lint_redundancy`: no two sibling slots may enumerate the same content in two registers (separator-split normalized item sets, nested note/caption strings included; >= 2 shared items at >= 50% of the smaller set). Wired beside AS-63 (prefilter + `content-redundancy` gate row) + a COPY QUALITY prompt rule. Developer data fix: the "Popular: …" note dropped (it duplicated the quick-links rail — the structured device is the keeper) | `compose_from_composition.py`, `compose_section.py`, `composition_lint.py`, `generate_composition.py`, developer composition | `test_fix7_lints.py` ContentRedundancyLint (4), `test_fix7_devices.py` FormNoteAttachment (3) |
| 7 | Stack anchor coherence for captions | `.c-caption` / `.cs-hero-form` children joined the `header.stack-coherence` stance census (spacing audit) — a ragged meta floater off the stack anchor is now the cell's failure shape; renderer side: the attached note stretches to the control width and rides the component base's `text-wrap: balance` | `spacing_audit.py`, `compose_section.py`, `spec/spacing-conformance.md` | coherence cells green across the battery; FormNoteAttachment pins the renderer contract |

## Secondary follow-ups landed in the same pass (stage B + pass 3 catalogues)

| follow-up | what landed | tests |
|---|---|---|
| bento `--lead` stamp (stage B) | `compose_bento_grid` stamps the de-facto lead (first cell whose anatomy strictly supersets the identical sibling set — mirrors SR-GRID-01's inference exactly); declared `lead: true` unchanged | BentoDeFactoLead (3) |
| form-split display register (stage B) | IS punch 5 | — |
| `knobs.columns` consumer (schema example knob) | `_moduleCols`: the knob is the MODULE-RUN track count (12 registration columns ≠ 12 card tracks — the swiss letter-squeeze); `_grid` fallback when no registration grid declared | KnobColumnsConsumer (4) |
| (1) `cta`-contract actions | `_cta_mapping` expands cta-contract list/string copy into real buttons (first primary, siblings quiet); the invented signup form only renders for genuinely actionless legacy conversions | CtaContractActions (4) |
| (2) `_cta_copy` string echo | dict-guarded header fallbacks (the pass-2 `_split_copy` fix mirrored) | CtaCopyDictGuards (2) |
| (3) stat vocabulary | dict-shaped stat copy (singular {value,label} or a nested item list) binds the stat renderer in the flow path | StatVocabulary (4) |
| (4) art-panel inset | `.cs-hero-panel` pads `var(--space-panel-padding, var(--c-module-gap, 6rem))` — the measured fact the `hero.panel-inset` law always expected | BentoDeFactoLead::test_art_panel… |
| (5) AS-11 stat visibility | `.c-stat` joined the primary-content inventory | StatVocabulary::test_slop_inventory… |
| (6) flow header→paragraph 40 vs 32 | header-contract flow items stamp `data-row="heading"` — the lead-in paragraph rides the heading→body rung | FlowHeaderRowStamp (1) |
| (7) testimonial split | `_split_copy` binds the testimonial CONTRACT (quote + name—role attribution) and the split renders the attribution caption | TestimonialSplitBinding (3) |
| (8) scrim-surface eyebrow ink | `section_vars` contrast-guards the accent section's eyebrow deployment (< 4.5:1 → primary ink; photo-hero 2.68:1 flips to cream = the capture's own measured ink; inverse 4.65:1 keeps accent) | EyebrowContrastGuard (3) |
| (9) archetype-less composed surface | every generated composition.v1 render takes the creative fidelity scope (stamped brand surface roles; authored heading identity), with or without `data-archetype`; replicas (replica-composition.v1) unchanged | ComposedPageCreativeScope (2) |
| (10) prompt vocabulary | COPY QUALITY block gains PROVEN AUTHORING SHAPES (button contracts, stat arrays, list intent, knob vocabulary) + the AS-65 redundancy rule; the licensed accent-device roster rides the pass-3 facts block | prompt tests + battery |
| stat-band column seam | `.cs-stat-band` rides `--space-column-to-column` FIRST (the stat.column-gap law); the registration gutter is the degrade — clears the recorded swiss `stat.column-gap 32 vs 80 ×2` red | bakeoff battery delta |
| uniform-grid row seam | `.cs-modules--cols` row-gap gained `--space-grid-gap` behind the declared gutter (a knob-declared grid carries none) | fid6 pin updated |

## Evidence (what the user saw, confirmed against data — as filed)

- Developer hero (`runs/hubspot-v2/brand/compose/hero-archetypes/developer/`):
  heading ends in an INK period although `brand.yaml` carries the signature
  "landmark serif headings may CLOSE with an orange period accent" — extracted, never applied.
  The form `note` ("Popular: …") renders as a free-floating ragged 2-line caption BETWEEN
  lede and search control, duplicating the quick-links row below the control. Reads as
  two subheadings + broken alignment. Zero accent devices anywhere → "no visual touches".
- Demo hero (`.../demo/`): composition declares `knobs.supportKind: "list"` but NO consumer
  exists in brand_pipeline (grep: zero hits) — the 3 parallel benefit items silently rendered
  as stacked plain paragraphs. Stat (`contract: stat`, value "299,000+" + label) renders with
  no visual binding: label-gap ≈ list-gap, so hierarchy collapses. Display-rung heading in a
  6-col split column wraps to 6 lines — no fit-stepping.

## After landing (all done)

- 8 gallery lanes re-rendered (`--rerender`, saved compositions, no model calls) +
  re-shot + contact sheet + lane index refreshed; full battery green (incl. the new
  Stage-B gates): onbrand PASS ×8 · slop PASS @1440+@1180 ×8 (0 advisories) ·
  interaction strict 0 ×8 · spacing strict 0 hard / 0 off-scale ×8 (statPair cells
  conform) · signature strict PASS ×8 + replica (floors enforced) · voice PASS ×8 ·
  section-rules strict PASS ×9 · conversion honest skips (no campaignType).
- 3 pass-3 style-bakeoff lanes re-rendered DETERMINISTICALLY (NEW lane script
  `style-bakeoff/rerender.py` — saved compositions, no model calls, no edits) +
  contact sheet re-shot. Battery delta (recorded in `battery-summary.json`, before
  → after): swiss slop 1→0 + spacing 1→0, editorial-magazine spacing 1→0,
  neumorphism spacing 1→0 — **all 3 lanes GREEN** (the checkpoint-D C1 residuals
  this pass's fixes addressed all cleared; section-rules adds 1 pre-existing
  SR-STAT-02 advisory per lane, conversion PASS 0 WARN ×3).
- Replicas rebuilt + re-scored with the final code: hubspot-v2 **0.957**, Remote
  **0.951** — both IMPROVED (+0.001 each; the devices + the eyebrow ink guard close
  real source gaps). Replica gates re-verified: slop PASS ×2, spacing 0 hard ×2,
  signature strict PASS ×2.
- Suite green: **1347 passed / 0 failed** (baseline 1259; +88 net new, zero lost).
- Changelogs updated: root `changes.md`, `runs/hubspot-v2/brand/changes.md`,
  `runs/remote/brand/changes.md`, both lane changelogs,
  `contracts/style-library/changes.md` + `evals/matrix/changes.md` follow-up
  annotations. `viewer.html` untouched (no viewer-affecting code).
