# WoodWave — editorial harvest implementation (editorial-harvest-2026-07)

Implements the two-round harvest spec (8 reference images, gaps G1–G9) into the
pipeline: new standard-tier patterns, the **overlay** + **banded** archetypes, the
overlay-family treatments, the G8 occlusion gate contract, and the G9 dual-surface
seam — proven by a deterministic showcase page **and** four seeded LIVE generation
runs, all gate-green, with zero regressions.

Harness: `build_harvest.py` (`showcase` / `live` / `lane` / `shots`), results in
`results.json`. Studio lane: **WoodWave — harvested reference patterns** (+ one lane
per live run), all verified HTTP 200.

---

## Step 0 — upstreamed harness fix

`compose_from_composition.py`'s split translator dropped per-section LLM slot copy for
patternRefs routed to `compose_about_statement` / `compose_curator_quote` /
`compose_visit_band` (KeyError `'body'`), and composition-declared brand assets were
sanitized but never copied. Both fixes ported from the showcase harness into the
adapter proper (`_split_copy` completion + `_declared_asset_names`/`_copy_declared_assets`).
Proof: `experiments/woodwave-showcase/hybrid/on-1` re-rendered from its persisted
`composition.json` **without** the harness wrapper → OVERALL PASS. A fresh
`tools/phase0_regate.py --baseline` was captured after the fix.

## P1 — patterns expressible today (8 pattern YAMLs, standard tier)

| pattern | file | ref | devices |
|---|---|---|---|
| `card-over-portrait-statement` | hero.yaml | #1 Borcelle | panel-on-media (G1) |
| `boundary-straddle-headline` | hero.yaml | #3 Design Philosophy | straddle z:front (G2) + scrim-band (G3) |
| `framed-inset-monument` | hero.yaml | #4 SAISEI | framed (G4) + bottom-edge straddle (+ break-frame knob, default off) |
| `stepped-overlay-statement` | hero.yaml | #5 “We design the feeling” | stepped-lines (G7) |
| `type-behind-media-masthead` | hero.yaml | #6 ÆBELE | type-behind-media (G8) |
| `tucked-headline-panorama` | hero.yaml | #7 HELLO THERE | straddle z:back tuck + occlusion params |
| `staggered-caption-columns-3` | gallery.yaml | #2 “the highlights” | per-column registered stagger + mixed-face masthead |
| `seam-straddle-portrait` | about.yaml | #8 KOJA | banded archetype + seam straddle (G9) |

`overlay` archetype coverage: hero.yaml referenced it with **no** composer — now a real
composer (`compose_overlay`); `banded` likewise (`compose_banded`). All 8 patterns are
retrievable for WoodWave (none silently neverDo-filtered — the retrieval filter now
distinguishes media-target straddles and sanctioned text treatments).

## P2 — new treatments, schema, gate

**Schema (`composition.v1.schema.json`, back-compatible — every persisted composition
that validated before still validates):** archetypes +`overlay`,`banded`; width
+`framed`; treatment kinds +`straddle`,`panel-on-media`,`scrim-band`,`framed`,
`type-behind-media`,`mixed-face`,`stepped-lines`,`break-frame`; treatment params
`registration` (incl. reserved `toSlot:"seam"`), `band`, `fill`, `distribute`,
`widthRel`, `maxOcclusion`, `endsVisible`, `steps`, `direction`, `spans`, `salience`;
section-level `bands {split, surfaces}`.

**Docs/prompt:** `composition-schema.md` §4.6.6, `composition-rules.md` (overlay family
§4a, typographic devices §4a-ii, banded seam, neverDo guards for straddle/
type-behind-media), and `generate_composition.build_prompt` (grammar + THE OVERLAY
FAMILY block). The new devices joined `OFF_GRID_TREATMENTS` /
`off_grid_treatments_gated`, so `offGridExpansion=false` styles stay pinned.

**Composers (`compose_section.py`):** `compose_overlay` — one positioning context:
in-flow canvas (full-bleed or framed with page margins), grid-registered children
positioned canvas-relative (`_ov_rel_left`): solid `panel-on-media`, sidebar rail,
flat `scrim-band` (surface-toned rgba, never a gradient), z:front straddles registered
to a slot edge/seam, z:back tucks (occlusion-stamped), stepped-lines, break-frame
decoration, corner-registered captions/cues; `_overlay_type_behind_media` — real
heading copy at z:0 with the media stack pulled up over it, pull depth **clamped so the
computed occlusion honors the declared cap**. `compose_banded` — two full-width
surface bands with a hard seam; the seam straddler is an in-flow pull-up; band
captions render on a panel chip (sanctioned panel-over-media, `no-text-on-photos`
honored outside heroes). `component_render.render_heading` gained `lines`
(stepped-lines) and `mixedFace` (falls back to weight/case contrast when the brand
ships no italic cut). Cards scaffold gained per-column `--c-col-N`/`--c-drop-N` vars
whose defaults reproduce the old odd/even geometry exactly.

**Gate (`onbrand_check.py`):** `occlusion` (G8) — reads each section’s
`data-occlusion-geom` stamp, **recomputes** horizFrac × vertFrac (never trusts the
stamped estimate), enforces the maxOcclusion budget, endsVisible, and stamp/geometry
agreement; `band-attribution` (G9) — every `data-bands` section carries exactly two
`data-band-surface` bands matching its declaration, each with real inline scoped
tokens. Both hard under `--composition`; the existing readability checks (text
contrast ≥3.0/≥4.5, decoration salience ≤1.19) apply unchanged to all new
text-over-media treatments.

## P3 — typographic devices

`mixed-face` (copy `{lead, emphasis}` → per-span face/weight contrast),
`stepped-lines` (authored line breakdown or balanced split, half-column indents via
`--c-step-N`), `break-frame` (corner-anchored decoration crossing the frame edge,
`aria-hidden` + `data-decoration`, salience-checked). All landed.

## Proof

**Deterministic showcase** (`pages/harvest-showcase/`, published lane): measured
opening bookend + one section per harvested pattern — gate **PASS** with the new rows
firing on real geometry: occlusion `0.208` and `0.19` vs cap `0.4` (endsVisible true),
1 banded section with 2 scoped bands. Per-section screenshots in
`pages/harvest-showcase/sections/`.

**Seeded LIVE generation** (`generate_composition.py`, claude-opus-4-8, seeds =
per-use-case seeds + all 8 harvested patterns; never hand-authored):

| run | gate | attempts | harvest seeds adopted | new devices used live |
|---|---|---|---|---|
| harvest-1 | PASS | 1 | boundary-straddle-headline, seam-straddle-portrait | straddle (sanctioned hero + media-over-seam), scrim-band, banded `bands` |
| harvest-2 | PASS | 1 | type-behind-media-masthead, framed-inset-monument | type-behind-media (occlusion 0.167 ≤ 0.4), framed, straddle |
| harvest-3 | PASS | 2 | stepped-overlay-statement, staggered-caption-columns-3 | stepped-lines, mixed-face |
| harvest-4 | PASS | 1 | card-over-portrait-statement, tucked-headline-panorama | panel-on-media, z:back tuck straddle, framed |

(harvest-2 needed a directive tightening — an earlier attempt failed the pre-existing
fidelity check that pins the opening surface to `surface/inverse` when the model chose
a leaner surface, plus one repair loop catching an unsanctioned text-on-media — the
gate doing its job.)

**Regression:** `tools/phase0_regate.py` — **zero PASS→FAIL** (18 pages; the single
FAIL, `page-anchored`, was already FAIL at baseline). Unit tests: 35/35 green,
including new `tests/test_harvest_checks.py` (occlusion budget/endsVisible/stamp-
disagreement, band attribution, treatment-kind registration, retrieval survival).

**Lane:** `WoodWave — harvested reference patterns` + 4 live-seed lanes, all HTTP 200,
screenshots in `shots/`. Melodrama markers on every page: @font-face 400 + 500,
`--c-display-weight: 500`, woff2 on disk.

## Fidelity vs the 8 references (eyeballed, section shots)

- **#1 Borcelle** — solid centered panel over the full-bleed portrait, wordmark top /
  statement center / caption bottom (space-between). Close.
- **#2 the highlights** — display masthead + three columns at colStart 1/4/9, spans
  3/4/4, distinct vertical drops, per-column captions. Close (mixed-face masthead
  degrades to weight/case, by design — no italic Melodrama cut).
- **#3 Design Philosophy** — cream rail cols 1–3, photo cols 4–12, display heading
  registered to the seam riding onto the photo, flat keyword scrim at 55–75%. Close
  after the canvas-relative positioning fix.
- **#4 SAISEI** — framed inset with visible margins, monument word straddling the
  bottom edge, corner break-frame decoration. Close; in-frame annotation is quieter
  than the reference.
- **#5 stepped statement** — full-bleed canvas, staircase lines stepping right,
  corner support + CTA. Good; line count follows the copy’s natural split.
- **#6 ÆBELE** — two-line masthead with the portrait stack occluding the second line,
  corner-registered detail image, flanking captions. Very close.
- **#7 HELLO THERE** — heading’s last line sinking ~40% behind the framed panorama,
  support paragraph sharing the first row. Very close.
- **#8 KOJA** — photo band / panel band hard seam, portrait straddling ~⅓ above the
  seam, chip caption on the photo, closing paragraph. Close.

## Deferred

- **break-frame live adoption**: proven deterministically (showcase §3) and legal in
  the prompt, but no live run elected it (harvest-4 was invited; the model chose
  panel/tuck devices instead). Device works; only live-LLM adoption evidence is thin.
- **Per-column stagger caps at 3 columns** (`--c-col-1..3`); a 4th+ module falls back
  to the odd/even rhythm. Matches the pattern’s `columnCount: [2,3]` envelope.
- **scrim-band items cap at 4 entries**; overflow is dropped, not wrapped.
- **Mixed-face true italic**: WoodWave ships no italic cut, so the fallback
  (weight/case contrast) is the permanent rendering for this brand.
- **`page-anchored` regate FAIL is pre-existing** (FAIL at baseline, unrelated to this
  work).
