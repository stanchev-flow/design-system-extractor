# spacing-conformance.md — the rendered-gap ⇄ captured-fact contract

> **Status: phase 1 (contract + auditor + baseline).** This spec defines WHAT the
> spacing audit measures on composed pages and HOW a measurement is judged against the
> brand's captured spacing facts. The auditor (`brand_pipeline/spacing_audit.py`)
> implements it mechanically; it measures, classifies and ranks — it does **not**
> remediate. Remediation lands in the composers/prompts per the repo doctrine
> (fix at the generation level, never a post-processing rewrite).

## Why this exists

"Spacing feels off" is the one complaint a brand-rule checker cannot catch: every
individual value can be a valid token while the *relationship* it renders is the wrong
rung of the brand's rhythm. A page whose eyebrow→heading seam rides the section-row
rung looks generically airy; a card grid whose gutter rides the split-column rung looks
loose — no color, type, or radius gate will ever flag either. The fix is the same
discipline the rest of the pipeline uses: name the relationships, resolve each one to
the brand's own captured facts, and diff the *rendered geometry* against them, by
machine.

## Vocabulary

- **Fact** — a captured spacing magnitude with provenance: a `tokens.spacing.*` entry
  in `brand.yaml`, a pattern-level magnitude in `layout-library.yaml`
  (`contentShape.bandPadding`, `deviceGeometry.columnGap/rowGap`,
  `deviceGeometry.list.itemGap/triggerMinHeight`, `contentShape.stackMeasure`,
  `slots[].mediaScale.gap`, `deviceGeometry.contentSpan`), or a chrome measurement
  (`navbar.measured.*`, `footer.measured.*`). Facts are read at the **canonical tier**
  (`meta.canonicalTier`, 1440 for the current brand): the `value:` key IS the canonical
  magnitude; `modeLadder` tiers are out of scope for phase 1.
- **Prose-derived fact** — extraction sometimes parks a measured magnitude in a fact's
  own provenance prose instead of a structured key (a token role documenting a
  contextual ladder range, a `deviceGeometry.note` recording a measured gutter). When
  the structured key is absent the auditor mines those px magnitudes as fallback facts,
  marked `token-prose` / `pattern-note` in the report so their weaker provenance is
  visible. A prose-documented range is evidence, not license: only its recorded
  magnitudes are sanctioned, never interpolations between them.
- **Scale** — the brand's own authored spacing scale, mined from the evidence CSS
  corpus (`evidence/css-rules.json`): every `:root`-level custom property whose name
  contains `spacing`/`space` and resolves to a plain px/rem length. This is the set of
  rungs the source site itself declared, whether or not a named token consumed each one.
- **Relationship** — a named pair/measurement on the *rendered* page (below). Every
  relationship belongs to a **family** — `gap`, `inset`, `width`, or `height` — and is
  only ever compared against facts of its own family (a 571px description *measure* is
  a sanctioned width, not a sanctioned gap).
- **Declared step(s)** — the specific fact(s) a relationship is contracted to ride.
  E.g. the heading→body seam rides the ladder's `heading-to-body` rung, not merely
  "some sanctioned value".
- **Sanctioned set** — all facts + scale rungs of the relationship's family. Used to
  distinguish "the wrong rung" from "not a rung at all".

## 1. Measured relationships

The auditor discovers these on every audited lane (skip-with-note when a lane simply
does not render the anatomy). Discovery keys off the renderer's own emitted structure
(`cs-*` / `c-*` scaffold classes and `data-layout` / `data-pattern` stamps), which is
shared pipeline vocabulary — never brand- or section-specific markup.

### Header-stack rhythm (family: gap)

| id | pair | declared step(s) |
| --- | --- | --- |
| `header.eyebrow-to-heading` | eyebrow → heading inside one header cluster | ladder `eyebrow-to-heading` |
| `header.heading-to-body` | heading → supporting body | ladder `heading-to-body` (alias `stack-md`) |
| `header.body-to-actions` | last text row → action row | ladder `body-to-cta` (hero register alias `stack-lg`) |
| `header.body-to-meta` | body → micro-caption row | *(no ladder rung — reported `unmapped` when rendered)* |

A header cluster is one eyebrow/heading/body/actions run regardless of scaffold: a
`.c-header` block plus its trailing paragraph, a hero panel content column, a
flow-section's `data-row` items, or a conversion stack. **The header cluster is one
typographic unit**: the source mechanic is per-pair semantic margins, so each seam has
its own rung — a uniform container gap across the whole cluster is exactly the failure
this contract exists to catch. An inline form directly after cluster text is an action
row (the ladder mechanic groups form scaffolds with buttons on the body→cta rung), not
a content block.

### Section band rhythm (family: inset / gap)

| id | measurement | declared step(s) |
| --- | --- | --- |
| `section.pad-top` | section top edge → first in-flow content top | the section's pattern `bandPadding.top` when captured, else the section-rhythm tokens (`section-padding-light`, `section-y-lg`, `section-y-xl`) |
| `section.pad-bottom` | last in-flow content bottom → section bottom edge | same as above (`bandPadding.bottom` first) |
| `section.seam` | previous section's content bottom → next section's content top | pairwise sums of the sanctioned band paddings (the between-section whitespace a reader actually sees is `padBottom(N) + padTop(N+1)`) |

### Block rows inside a section (family: gap)

| id | pair | declared step(s) |
| --- | --- | --- |
| `block.header-to-content` | header cluster → first content row (grid, strip, list, media, form) | ladder `block-to-block` |
| `block.row-gap` | content row → next content row | ladder `block-to-block` |
| `block.content-to-actions` | last content row → trailing action row | ladder `block-to-block` (the source's `ctasAfterContent` rides the same rung) |

### Grid geometry (family: gap)

| id | measurement | declared step(s) |
| --- | --- | --- |
| `grid.column-gap` | horizontal gap between cards in one row of an N-up grid | pattern `deviceGeometry.columnGap` (an edge-cut track's measured `cardGap` is the same fact in its device spelling) when captured, else token `grid-gap` |
| `grid.row-gap` | vertical gap between grid rows | pattern `deviceGeometry.rowGap` when captured, else token `grid-gap` |
| `split.column-gap` | gap between the two columns of a split scaffold | pattern `deviceGeometry.columnGap` when captured, else ladder `column-to-column` |
| `strip.gap` | inter-mark gap in a logo/badge/rating strip | the pattern's `mediaScale.gap` facts when captured, else *(unmapped)* |
| `stat.column-gap` | gutter between stat columns | ladder `column-to-column` |

Staggered editorial grids (odd/even span scaffolds without a declared uniform grid) are
skipped-with-note: their interleaved geometry has no single row/column gap.

### Card anatomy (family: inset / gap)

| id | measurement | declared step(s) |
| --- | --- | --- |
| `card.inset` | plate padding (computed, per side) | token `panel-padding` (incl. its role-documented contextual range) |
| `card.media-to-content` | full-bleed media well bottom → first content row | token `panel-padding` (the well is inset by the plate pad) |
| `card.eyebrow-to-heading` | in-card eyebrow → heading | ladder `eyebrow-to-heading` |
| `card.heading-to-body` | in-card heading → body | ladder `heading-to-body` |
| `card.body-to-actions` | in-card body → text action | pattern `deviceGeometry.cardActionGap` when captured, else ladder `body-to-cta` |
| `card.body-to-author` | in-card body → attribution row | *(unmapped unless a fact exists)* |
| `card.mark-to-quote` | quote-card company mark → quote body | *(unmapped unless a fact exists)* |
| `hero.panel-inset` | inset panel padding (computed, left + top) | token `panel-padding` (incl. its role-documented contextual range — panel insets legitimately ride higher rungs at the hero tier) |

Bottom-pinned rows on equalized stretch grids (body → author/action pinned by
`margin-top:auto`) carry sanctioned variable slack per card, so per-card slack is not a
conformance seam. The auditor audits only the **minimum seam across the row** — the
tightest card is where the authored rung must still hold; a minimum of ~0px means body
text collides with the pinned row on the tallest-content card.

### Container law (family: width)

| id | measurement | declared step(s) |
| --- | --- | --- |
| `container.width` | rendered width of a section's shared content container | the container facts: `container-span` resolved at the audit viewport, `container-max` / measured `contentMaxWidth`, pattern `contentSpan` |
| `container.stack-width` | width of a deliberately narrow centered stack; on a SIDE-ANCHORED stack (fid10 container law: the anchor releases the stack box to the shared content spine and the measure cap moves to the text children) the acting column is the widest max-width-capped descendant, not the spine box | the brand's captured stack measures: pattern `stackMeasure` facts (own pattern first) and the bounded header-stack measure token when the brand carries one |
| `container.centering` | abs(left gutter − right gutter) of the container inside its section | 0 (absolute tolerance ±2px; skipped for sanctioned edge-cut/bleed scaffolds) |

**CONTAINMENT vs MEASURE (fix3 2026-07).** The emitted CSS carries exactly ONE
containment mechanism: the shared CONTAINMENT LAW rule
(`compose_section.CONTAINMENT_LAW_CSS`, membership in `CONTAINED_DEVICES`) —
every major section container **spans its parent (`width: 100%`), caps at
`var(--content-measure)` and centers with auto margins** from that single rule.
Devices never re-declare `max-width: var(--content-measure)` /
`margin-inline: auto` privately: the scattered copies were how the action-row
centering leak shipped (a private copy inside an already-contained column
resolves its auto margins before flex stretch, so the box hugs and floats
centered) and how the split-panel carousel painted full-bleed (its device simply
lacked the pair). `width: 100%` makes nesting safe by construction — auto
margins never see free space inside a narrower column. Deliberately NARROWER
caps are the separate MEASURE vocabulary (pattern `stackMeasure` →
`--cs-stack-measure` text columns, prose `ch` clamps, device art caps): they
constrain text/media runs inside a contained column and never own the column.
Releases (edge-cut rails, overlay bleeds, side-anchor spine releases, measured
chrome widths) carry a `contain-exempt:` tag at the declaration site; the fix3
containment lint (test_fix3) fails any untagged containment declaration outside
the law. The auditor's classifier mirrors the vocabulary: measure-capped stacks
(`.cs-modules-intro`, `.cs-conversion`, `.cs-faq`, and fix3's `.cs-title` /
`.cs-foot` hero text boxes) audit as `container.stack-width`, never as the
section container.

### List rhythm (family: gap / height / inset)

| id | measurement | declared step(s) |
| --- | --- | --- |
| `list.item-gap` | disclosure/list item → next item | pattern `deviceGeometry.list.itemGap` when captured, else *(unmapped)* |
| `list.trigger-height` | disclosure trigger row height | pattern `deviceGeometry.list.triggerMinHeight` when captured, else *(unmapped)* |
| `list.item-inset` | list item's internal block padding | *(unmapped unless captured)* |
| `footer.link-gap` | footer directory link → next link | chrome link-rhythm fact when captured (e.g. `navbar.measured.linkGap`) |
| `footer.column-gap` | footer directory column gutter | `footer.measured.grid.columnGap` |

### Form rhythm (family: gap)

| id | measurement | declared step(s) |
| --- | --- | --- |
| `form.field-gap` | field row → next field row (grid row gap) | *(unmapped unless a form rhythm fact was captured)* |
| `form.label-to-input` | label → its input | *(unmapped unless captured)* |
| `form.stack-gap` | form-internal cluster seams (grid → consent → actions) | *(unmapped unless captured)* |

### Action groups (family: gap / center — fix2 2026-07, brand-schema §4.4f)

| id | measurement | declared step(s) |
| --- | --- | --- |
| `actions.item-gap` | median same-row gap between actions in one emitted group (`.cs-hero-actions` / `.cs-modules-actions` / `.cs-conversion-actions`) | pattern `contentShape.actionGroup.gap` first, then the brand-level `layoutGrammar.actionGroup.gap`; *(unmapped)* for fact-less brands |
| `actions.alignment` | PAINTED-EDGE conformance (fix3): the group's ITEMS against the CONTENT COLUMN a reader compares them to — the widest in-flow sibling sharing the group's parent (the intro/heading stack above the row), else the parent's content box. `start` ⇒ first item's left edge vs the column's left edge, `center` ⇒ abs(left − right edge delta), `end` ⇒ trailing delta. The fix2 cell measured item edges inside the group's OWN content box, which read 0px while the box itself was displaced (max-width + auto margins hug-centering it in its column) — the audit blind spot that let the stamped side-rail group paint 21px off its column | 0 (center-family verdict scale: conform ≤2px / drift ≤4px / off-ladder); contexts that own their anchor (`.cs-foot`, `[data-align="centered"]`, `.cs-hero-panel--center`, a centering flex parent) are skipped — the schema's sanctioned exception, not drift |
| `header.stack-coherence` | STACK-STANCE conformance (fix5): a header stack (eyebrow / heading / body / action row sharing one flex column that contains a heading) must paint ONE alignment stance. Each child's PAINTED span (text line bounds via Range for text, border box otherwise) classifies as `left` / `center` / `right` / `full` against the stack's content box; the measurement is the largest px displacement any child needs to match the stack's dominant stance. Every per-child alignment cell can conform to its OWN declaration while the STACK mixes stances (the fix5 panel: a heading centered by a leaked page-level rule over a left kicker/body/actions — every existing cell passed). Side-by-side children (row devices: heading \| body two-column intros, vertical overlap > 50% of the shorter box) are skipped — coherence is a claim about one COLUMN | 0 (center-family verdict scale: conform ≤2px / drift ≤4px / off-ladder); `full`-stance children (measure-capped body filling the column) are compatible with any stance |

Unmapped form rhythm is an **expected extraction gap** for brands whose source forms
live in unrendered modals — the audit surfaces it as capture work, not render drift.

## 2. Conformance rule

Every measured value `m` for a relationship with declared steps `D` (px values at the
canonical tier) and family sanctioned set `S`:

```
tol(v)   = max(2px, 10% of v)        # gap / inset / height families
tol_w(v) = max(2px, 1% of v)         # width family (containers are two orders larger;
                                     # 10% of 1200px would sanction a 120px miss)
conform    ⇔ ∃ d ∈ D:  |m − d| ≤ tol(d)
```

**Why ±2px or ±10%, whichever is larger.** The facts are authored in rem at the
canonical tier and re-rendered through fonts, flex and grid: sub-pixel line boxes and
device-pixel rounding legitimately move an edge by up to ~1px on each side of a gap —
that is the ±2px floor. Fluid-by-construction values (`clamp()`/`cqw` terms measured
against a container a few px narrower than the viewport) drift proportionally — that is
the 10% arm. Anything past both arms is not rendering noise; it is a different
magnitude. The width family keeps the 2px floor but tightens the relative arm to 1%
because the container facts themselves were measured to the pixel (used 1168px @1440)
and a 10% arm would make the check vacuous.

Measurement is `boundingClientRect` edge deltas (bottom of A → top of B in page
coordinates), which equals the authored margin/flex-gap between border boxes — line-box
half-leading lives *inside* an element's rect, so rect deltas compare 1:1 with the
facts' margin/gap vocabulary (same technique as `tools/extract/measure_computed.py`).

## 3. Severity ladder

| severity | condition | gate class |
| --- | --- | --- |
| `conform` | within `tol` of a declared step | pass |
| `drift` | within `2 × tol` of a declared step | **advisory** — watch, don't block |
| `wrong-step` | outside `2 × tol` of every declared step, but within `tol` of some *other* sanctioned value of the family | **hard fail** — the renderer picked a real rung, but not the one the relationship declares |
| `off-ladder` | matches nothing in the sanctioned set within `tol` | **hard fail** — the magnitude is foreign to the brand |
| `unmapped` | the relationship renders but the brand carries **no declared fact** for it | **advisory, reported separately** — an extraction gap (capture work), not a render bug. The nearest sanctioned value is still reported so a human can see whether the render at least stayed on the brand's scale. |

A relationship may be flagged `advisory-only` in the auditor's relationship registry
(reason recorded in the report) when its hard fails cannot be attributed cleanly —
none are currently registered; prose-derived facts (vocabulary §) cover the
documented-range cases instead.

### 3b. `scale_adherence` — the derived-scale gate (pass1 2026-07)

On **generative lanes only**, novel geometry must lie on the brand's derived
scale (`style-scale.yaml`, brand-schema §4.9): the lane's rendered
section-content font sizes plus its `unmapped` section-level space measurements
each classify as

| verdict | meaning | gate class |
| --- | --- | --- |
| `measured` | matches a measured type/space fact (facts always win) | pass |
| `on-scale` | no fact, but sits on a derived step within tolerance (max(1px, 2%) type; max(2px, 2%) space) | pass |
| `off-scale` | matches neither — an arbitrary number in novel geometry | **hard fail** |

Scope laws:
- **Generative lanes only** — the marker is the lane's `composition.json`:
  `schemaVersion: composition.v1`, or the legacy `replica-composition.v1` WITH a
  `brief` (a briefed composition is a novel page). The replica's briefless
  assembler composition and the marker-less previews are exempt **by
  construction**; replica output never consumes the artifact.
- **Chrome is excluded** — chrome renders harvested measured facts at
  source-exact sizes (nav 12/13/15px…) the content ladder never declared; the
  type census skips chrome subtrees and `footer.*`/`nav.*` space relationships
  are filtered out.
- A lane whose brand has no usable `style-scale.yaml` (absent, or
  `followsScale: false` — an honest poor fit) gets no scale cells at all:
  inventing steps from a bad fit would be the arbitrary-number failure this
  gate exists to remove.
- A composed section that consumed a derived step for its `bandHeight` knob
  stamps `data-band-rung="derived:<px>"`; `section.pad-top/-bottom` then audit
  against that deliberate declaration on the standard severity ladder above
  (same hard gate as a token rung).

Caught at introduction (2026-07): the overlay panel's stepped-down display
(0.62 × 80px = 49.6px — on NO ladder; re-registered to 0.6 so the stepped rank
lands on the brand's own h1 rung), and an 8px form label seam read off-scale
because the normalizer had not mined the brand's own authored `--spacing-*`
custom properties (miner extended; 8px is a declared step).

## 4. Measurement protocol

- Headless Chromium via Playwright, `file://` URL, viewport **1440×900** to match the
  facts' canonical tier, `deviceScaleFactor 1`.
- `prefers-reduced-motion: reduce` emulated **and** a belt-and-braces style injection
  that force-reveals scroll-choreography content (`.cs-reveal` → fully visible, no
  transform/transition) so measured rects are settled geometry, never mid-entrance.
- Wait for `document.fonts.ready` plus a settle delay before measuring: web-font swaps
  reflow every text rect.
- Per-lane timeout budget 120s; a lane that cannot be measured is recorded as an error
  in the report and the audit moves on — the auditor never hangs and never lets one
  lane sink the run.
- Report records each audited file's mtime so a stale-artifact diff is visible.

## 5. Output contract

`report.json` + `report.md` in the audit output directory:

- per lane → per relationship instance: measured px, declared step (name + px), delta,
  nearest sanctioned fact (name + px), severity, section id / `data-layout` /
  `data-pattern` context, and the gap rectangle (page coordinates) for annotation;
- per lane severity counts and a per-relationship rollup;
- a ranked **top offenders** list: hard fails grouped by
  (relationship, rounded measurement, expected step) signature, scored by
  `frequency × mean |delta|` — the failures a human eye hits first are the ones that
  are both big and everywhere;
- `unmapped` findings listed separately as extraction gaps;
- annotated close-up screenshots for the top offenders of the designated diagnosis
  lane, with the measured gap drawn and labeled in place.

Exit code: `0` in baseline mode regardless of findings; `--strict` exits `1` when any
hard fail (or lane error) is present — that is the future gate wiring.

## 6. What phase 1 does NOT do

- No remediation, no HTML/CSS rewriting, no composer edits.
- No multi-tier audit (only the canonical tier; `modeLadder` tiers are phase 2).
- No source-page re-measure: the facts are trusted as captured. The replica lane is the
  control — if the *replica* fails a relationship, suspect the fact or the auditor
  before the composers, and investigate before trusting that row of results.
