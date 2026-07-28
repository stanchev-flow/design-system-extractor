# runs/greenhouse-v2 — change log

Fresh, MULTI-PAGE brand extraction for the Greenhouse brand, synthesized into ONE
unified brand. STAGE 1 (gating) of a larger experiment. Does NOT reuse or clobber
`runs/greenhouse` (the old studio lane).

## 2026-07-27 — SHARED COMPOSER fix: preserve multi-column module geometry (HELD, not committed)

Root cause of the "every mid-page module collapses into one narrow column" defect:
`brand_pipeline/compose_from_composition.composition_to_layout` routed any section whose
authored `archetype` is a DESCRIPTIVE / structural label with no bespoke composer
(greenhouse-v2 uses `three-column-media-top-cards`, `pill-filtered-comparison-card`,
`three-column-number-over-caption`, `three-column-quote-blocks`, `split-copy-and-logo-grid`,
`centered-copy-with-floating-media`, …) straight to the single-column `generic-flow`
safety net. Every authored multi-column module therefore stacked vertically. This is
brand-agnostic (any brand authored with descriptive archetypes collapses identically).

Fix (all fact-gated + brand-/palette-agnostic; drawable-archetype brands untouched):
- `composition_to_layout` now INFERS the closest drawable archetype for a non-drawable
  label from the section's own anatomy facts (`_infer_drawable_archetype`,
  `_is_hero_like`): a repeated card collection → `cards`; a two-column/comparison label
  + a media/list counterweight → `split`; a hero label + heading/media/CTA → the real
  hero stack. Absent measured column facts, inferred card grids take a MULTI-COLUMN
  default (the declared "N-column"/"N-up" hint clamped to the item count, else min(n,3)).
- Numeric/figure LIST collections in `generic-flow` now map to the horizontal STAT band
  (value at display register), never a vertical caption fold.
- `_cards_copy`: the module slot is the real repeated collection (a media WELL whose
  role merely contains "card" no longer hijacks it → the empty-grid bug); quote/
  testimonial context renders attribution person-rows with no backfilled media; a
  sibling media-well slot's assets distribute across otherwise media-less cards
  (consumes declared media, no default-art / srcless-placeholder plate — C11).
- `compose_section.compose_info_band`: a split binding an award/review badge or partner
  mark AS WELL AS a media panel now renders the mark (contained strip) instead of
  dropping it once media occupies the half.
- `compose_section.compose_features_cards`: honors a `_cardsNoMedia` flag so a truly
  asset-less inferred card grid renders text cards (no placeholder plate).
- `render_components_preview.harness_quality_issues`: `c-stat`/`cs-stat-band` added to
  the substantive-anatomy whitelist (the horizontal stat band is a real device).

Files: `brand_pipeline/compose_from_composition.py`, `brand_pipeline/compose_section.py`,
`brand_pipeline/render_components_preview.py`. Regression tests:
`brand_pipeline/tests/test_composer_multicolumn.py` (12 tests).

Replica per-band (overall 0.746 → 0.759). The greenhouse-v2 replica pairs layouts to
HOME-page section rects by position, but several layouts are synthesized from the
talent-sourcing / compare pages — so featureGrid/stats/testimonial composite scores are
capped by a pre-existing MULTI-PAGE pairing mismatch (a source band ≠ the paired
layout). The honest collapse signal is WIDTH fidelity (content-span ratio):

| band        | score before→after | width before→after | note |
|-------------|--------------------|--------------------|------|
| hero        | 0.759 → 0.792 | 0.968 → 0.891 | real hero composer; 2471px → 1792px |
| featureGrid | 0.182 → 0.201 | 0.671 → 0.877 | 1637px single stack → compact 3-up card grid |
| logos       | 0.804 → 0.805 | 0.575 → 0.575 | unchanged (only 1 logo bound — evidence limit) |
| comparison  | 0.788 → 0.849 | 0.292 → 0.807 | narrow stack → side-by-side columns |
| stats       | 0.841 → 0.782 | 0.004 → 0.861 | collapsed → horizontal 3-numeral band (composite drop is a paired-source height mismatch, not a render regression) |
| testimonial | 0.253 → 0.305 | 0.532 → 0.773 | single stack → 2-up quote-card grid |

Cross-brand replicas (single-page, aligned) — NO regression: hubspot-v3 0.9211 → 0.9220,
woodwave-v2 0.7673 → 0.7673, remote 0.9509 → 0.9509 (0 bands worse on any brand).

Verification: C1–C28 = 0 errors on greenhouse-v2/hubspot-v3/woodwave-v2/remote; full
`brand_pipeline` suite 1997 tests OK; top-level `tests/` = only the known pre-existing
`test_runtime_defaults` failure (no new failures). Re-rendered: greenhouse-v2 replica,
raw harness (`harness/` + shots @1440), and the 3 cross-brand replicas. `viewer.html`
NOT regenerated (parent regenerates once). The 25-section bakeoff under `sections/` is a
separate relume-recipe lane that does not import the shared composers (per its own
`sections/changes.md`), so the composer fix does not alter its output — left as-is.

Known follow-ups (evidence/pairing, NOT composer bugs): logos binds a single partner
logo (author bound 1 asset); the hero binds one composite collage asset so no additional
tagged crops exist to layer; the replica's home-page section pairing mismatches the
multi-page layout provenance.

## Source pages (live capture, full network)

1. https://www.greenhouse.com/             → home  (primary + replica target) — 1440x5031, 6 css / 64 imgs
2. https://www.greenhouse.com/talent-sourcing → talent-sourcing (feature/product) — 1440x9339, 6 css / 55 imgs
3. https://www.greenhouse.com/compare          → compare (comparison)            — 1440x8101, 6 css / 55 imgs

Fallback/cross-check for the homepage: `screenshots/greenhouse/greenhouse.html`.
Captures live under `screenshots/greenhouse-v2/{home,talent-sourcing,compare}/`.

## Pipeline shape

- Canonical lane: `runs/greenhouse-v2/brand/` (standard evidence-first pipeline).
- Per-page evidence: `evidence/pages/{home,talent-sourcing,compare}/` (dom-sections,
  css-facts/css-rules, motion-audit, computed-styles, section-rects, crops/, grounding/).
- Merged canonical evidence (what the author consumed): `evidence/` — home canonical for
  chrome/computed-styles/section-rects/crops (replica target); sections, css censuses,
  action groups, grounding, and media unioned across all 3 pages with per-page provenance.
- Vision grounding: home 6 + talent-sourcing 11 + compare 9 = 26 grounded sections;
  11 promoted into canonical grounding (bounded so author bundles stay under the 180KB cap).

## Log

- Captured 3 live pages with `tools/extract/capture_page.py` (full_network).
- Mined each page (mine_dom, mine_css, mine_motion, measure_computed, slice_sections) into per-page evidence.
- Vision-grounded every crop per page (claude-opus-4-8, medium).
- Curated assets per page; unioned to 64 brand assets + media-assets-draft.
- Merged per-page evidence → canonical evidence (`evidence/merge_pages.py`).
- Trimmed canonical css-facts hoverRules + grounding keys/count so each staged-author
  bundle fits under the 180KB cap (history: oversized grounding bundles timed out).
- Authored with the staged, evidence-scoped author DAG (foundation → copy-chrome →
  patterns-recipes → media → projections), hard 300s per-call timeout, NO SDK retries.
- Ran the owner-routed C1-C28 repair loop; it cleared C3 (button matrices) and C10
  (card variants) but stalled at 19 errors (flaky/no-op LLM repair responses).
- Completed the remaining fact-gated contract fields directly from measured evidence
  (`evidence/fix_contract.py`, `evidence/fix_contract2.py`):
  - C11: added composer-required tokens — colors text/on-primary-muted,
    text/on-inverse-muted, border/hairline-on-primary, text/ghost-on-primary;
    tokens.type.eyebrow; tokens.spacing.eyebrow-to-heading + panel-padding;
    voice.motionSpec (durations 150/300/500ms, easing cubic-bezier(.645,.045,.355,1)).
  - C7: navbar.surface → measured dict {bg #ffffff, ink #15372c}; added measured.link.
  - C21: marked the 5 primary mega-menu dropdown triggers utilityNotObserved (panel
    anatomy genuinely not captured in the static snapshot).
  - C4: collapsed over-decomposed per-item content slots into single `items` slots
    (canonical passing shape); populated real testimonial quotes from compare grounding.
  - C27: unbound 4 mis-bound crop/grounding filenames from pattern media slots; bound
    the real home-hero asset to the hero and dropped 2 orphan decorative media slots.
- Ran the gated flow: G1 extraction PASS, G2 validation PASS (0 errors / 11 warnings),
  G3 harness PASS (spec book 7/7 chapters, catalog built), G4 replica rendered + scored.

## Results

- C1-C28: **0 errors, 11 warnings** (PASS). Warnings: C5 breadth, C16 footer bottomBar,
  C23 recipe variant ids, C24 section-rhythm step, C25 signature-entry prose form.
- Replica (homepage primary target): **overall 0.7458**; 1440 primary-viewport health
  1.000 (0px overflow). Per-band: footer 0.95, stats 0.84, logos 0.80, comparison 0.79,
  hero 0.76; featureGrid 0.18 and testimonial 0.25 are the main punch-list drags.
  Responsiveness lower at 960/375 (mobile ladders). Below the 0.90 flow bar → G4
  needs_iteration, but the brand FACTS are complete + validated.
- Regenerated `viewer.html` via the repo venv (per AGENTS.md).

## Scratch / provenance helper scripts (kept, not deleted)

- `evidence/merge_pages.py`     — multi-page → unified canonical evidence merge.
- `evidence/fix_contract.py`    — fact-gated contract completion pass 1 (tokens/chrome/copy).
- `evidence/fix_contract2.py`   — fact-gated contract completion pass 2 (layout-library slots/assets).
Kept as provenance for how the unified lane was assembled; safe to delete once reviewed.

## Uncommitted source edits (repo-level, NOT committed — for parent review)

- `brand_pipeline/staged_author.py` — foundation stage prompt now tells the model
  voice-facts.yaml MUST include `schemaVersion: voice-facts.v1` (mirrors the media stage;
  the model reliably omitted it, aborting authoring). General, brand-agnostic.
- `brand_pipeline/render_brand_md.py` — the layout-patterns table now tolerates
  `specialTreatments` entries authored as bare strings (coerces to {kind}) instead of
  crashing the deterministic brand.md projection. General robustness.
- `tools/extract/validate_brand_evidence.py` — C7 navbar check reads `navbar.surface`
  defensively (a non-dict surface becomes a proper C7 error instead of an AttributeError
  crash that aborted the whole validator). General robustness.

All three are general pipeline hardening, not greenhouse-specific; greenhouse-v2 validates
0-errors with them in place. Parent to decide on committing.
