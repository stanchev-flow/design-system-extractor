# REPORT — Remote Workforce Intelligence launch page (bakeoff candidate B)

- **Model:** Claude Opus 4.8 Thinking High
- **Lane:** `runs/remote/brand/compose/bakeoff-opus/`
- **Elapsed:** ~34 minutes (start ~19:21, finish ~19:55 WEST, 2026-07-10), including
  three ~90s onbrand-gate runs (headless-measured).
- **Render:** deterministic composition renderer, style `corporate-saas-clean`
  (brand.yaml wins on every token it sets); `index.html` never hand-edited.

## Concept

**Workforce Intelligence** = the analytics / insight layer on top of the employment
infrastructure Remote already runs. The wedge is brand-true: because Remote owns
payroll, EOR, contractor, and compliance operations in-house ("one system of record"),
the data already lives in one place — so the product turns it into a single, current,
decision-ready view of **global headcount, total workforce cost, and compliance risk**,
plus benchmarking/planning for VP People, CFO, and HR Operations at 500+ employee
international companies. The page opens on a demo CTA and closes on a tailored demo lead
form (the qualified-demo goal). It deliberately avoids the homepage's "hire and pay
anyone" narrative, so it reads natively Remote without copying the home page.

## Section count

**10 authored sections** (+ the renderer's auto-appended footer bookend):

| # | id | Brief need | seededFrom (pattern) | archetype | composer |
|---|---|---|---|---|---|
| 1 | hero | product hook | `hero-inset-noise-panel` (project) | split→hero | stack-hero panel |
| 2 | problem | the problem | `infra-proof-split` (project) | split | info-band (media \| copy) |
| 3 | product-value | product value | `feature-accordion-deep-accent` (project) | split | info-band → accordion |
| 4 | capabilities | key capabilities | `features-card-grid-navy-media` (project) | cards | 3-up navy-media grid |
| 5 | how-it-works | how it works | `features-card-grid-navy-media` (project) | cards | 3-up product-UI grid |
| 6 | comparison | comparison vs current way | `infra-proof-split` (project) | split | info-band ruled table |
| 7 | proof | customer proof | `testimonial-card-row` (project) | cards | edge-cut quote cards |
| 8 | conversion-beat | conversion beat | `cta-inline-banner` (project) | stack | conversion inset panel |
| 9 | faq | FAQ | (declared `faq`) | stack | faq accordion |
| 10 | lead-form | lead form | (declared `contact`/multi-field) | stack | conversion signup form |

Surface is one continuous light canvas (voice.md). The single sanctioned accent is the
hero noise panel; the one inverted deep-accent emphasis is the accordion's active row —
both pattern-native.

## Credibility discipline (brief: no invented claims/stats)

- No invented metrics/ROI/adoption numbers in authored body copy.
- Customer proof uses the **verbatim** captured Remote testimonials from
  `section-copy.yaml` (Luke McKinlay, Marisol Jiménez, Maria Shkaruppa) with their real
  avatars; they speak to Remote generally and are **not** reattributed to this product.
- Security claims (SOC 2 Type 2, ISO 27001) are the ones already asserted for the owned
  infrastructure in `section-copy.yaml` — reused, not invented.
- No award badges / rating chips (would imply third-party ratings for a brand-new product).
- The footer disclaimer line about onboarding numbers is brand.yaml footer chrome
  (deterministic), not authored page copy.

## Assets used (real brand files only)

Hero: `bg-noise-top-2x.webp` (inset panel art), `hero-globe-illustration.webp`.
Problem / product-value / comparison media: `panel-infrastructure-ui-snippet.webp`,
`collage-global-payroll-ui.webp`. Capability card wells: `card-api-first.webp`,
`card-integrations.webp`, `card-mcp-agents.webp`. How-it-works wells:
`collage-eor-ui.webp`, `collage-contractor-management-ui.webp`,
`collage-global-payroll-ui.webp`. Proof: `logo-fountain.svg`, `logo-reversetech.svg`,
`logo-homeproject.svg` + `avatar-luke-mckinlay/marisol-jimenez/maria-shkaruppa.webp`.
(Card/collage art is reused as generic Remote product-UI, not for its homepage labels.)

## Gates (final render)

- **neverDo (HARD):** PASS — never-typographic-primary, never-zero-radius, never-allcaps-headings.
- **composition invariants (HARD, `--composition`):** ALL PASS — single-accent,
  primitive-only, rhythm, data-composition, slot-resolution, text-contrast,
  decoration-salience, occlusion, band-attribution, alignment-resolution,
  media-registration, interaction-contrast, token-provenance, logo-wall-integrity.
- **slop audit:** PASS @1440px and @1180px.
- **OVERALL: PASS.** `unresolved slots: 0`.
- **Advisory style WARNs (never gate):** "one disciplined accent" and "radius matches
  brand choice" (style-layer defaults the Remote brand overrides), and
  "container-query units only" — advisory only; the brand neverDo/fidelity/composition
  layers all pass.
- Gate outputs: `onbrand-report.md`, `onbrand-report.json`, `onbrand-console.txt`,
  `slop-console.txt`.

## Artifacts

`PROMPT.md`, `PLAN.md`, `copy-brief.md`, `composition.json`, `index.html`,
`tokens.manifest.json`, `assets/`, `RENDER-STATE.json`, `changes.md`, gate outputs,
`shots/full-1440.png` + `shots/00..10-*.png`, `shoot-sections.mjs`.

## Visual inspection notes

All 10 sections + footer inspected at 1440px. Hero (inset noise panel + orbiting
product-UI globe + filled/secondary pills), the deep-accent accordion (active row
inverts to maroon with the circle-arrow affordance), the two 3-up card grids
(capabilities on navy wells, how-it-works on light product-UI wells), the ruled
before/after comparison table, the edge-cut testimonial carousel, the inline
conversion banner, the FAQ disclosure, and the multi-field demo form all render
cleanly and read natively Remote. Corrections made were composition/copy-level only
(see changes.md §Iterations); no HTML or shared code was edited.

## Shared-renderer defects observed (documented, not worked around by hand-editing HTML)

1. **Alignment-source enum mismatch (HARD-gate friction).** `resolve_alignment`
   legitimately emits `data-align-source="curation"` (a pattern's `follow-grammar`
   curation, e.g. `features-card-grid-navy-media`) and `data-align-source="brand"`
   (header-context grammar, e.g. a bare FAQ), but the `alignment-resolution` gate only
   accepts `section|pattern|style`. A composition that relies on the curated/brand
   grammar therefore FAILS the HARD gate until it re-declares the same anchor at the
   section layer. Worked around at the composition layer (declared `alignment` so source
   = `section`; resolved anchor unchanged) — not by editing shared code. Suggest the gate
   accept `curation`/`brand` (or the composer down-map them) so composed pages that
   correctly defer to curation/grammar are not forced to hard-code the anchor.
2. **Cards composer default-art backfill.** A `cards` module with no bound asset
   backfills the brand's default hero/detail art into its media well, so a text-only
   card section renders large empty noise-gradient wells. Fixed at the composition layer
   by binding real product-UI assets; a "media-less feature card" mode (like the quote
   card's) would let a steps/text card grid render without wells.
3. **N-up grid toggle keyed to `section.grid`, not `knobs.columns`.** `compose_features_cards`
   only produces the uniform N-up grid (`cs-modules--cols`, `--grid-cols` re-scope) when
   the composition declares `section.grid.columns`; `knobs.columns` is inert here, so a
   `knobs.columns:3` card section renders the 2-up editorial stagger. Documented; fixed by
   declaring `grid`.
4. **Secondary CTA `family:"outlined"` not honored in the hero/cards routes** — both hero
   pills and the testimonial closing pill render filled. voice.md describes a filled +
   outlined hero pair, so the outlined secondary is a minor fidelity miss. Left as-is.

## Honest self-critique

- **Strengths:** clean end-to-end brand fit; every section maps to a real Remote project
  pattern or a native scaffold; all HARD gates pass with 0 unresolved slots; the brief's
  full section list (problem → value → capabilities → how-it-works → proof → comparison →
  FAQ → lead form) is covered plus a conversion beat; copy is concise, second-person,
  sentence-case, and invents no stats; customer proof is verbatim real evidence.
- **Weaknesses / risks:**
  - **Pattern reuse density.** Two card grids (capabilities + how-it-works) back to back
    and two info-band splits (problem + comparison) lean heavily on two patterns; the
    page is cohesive but its structural variety is moderate. A bespoke "steps" device
    would differentiate how-it-works better.
  - **Comparison media coupling.** The info-band comparison forces a media half; I reused
    a payroll product-UI shot as the "after" panel, which is slightly generic relative to
    the table's specificity.
  - **Product substantiation.** Because I honored "no invented claims", the page describes
    capabilities without a real product screenshot of Workforce Intelligence itself
    (none exists in the asset set) — the media is repurposed Remote product-UI, so a
    skeptical buyer sees adjacent UI rather than the actual product view.
  - **Testimonial fit.** The verbatim quotes are about Remote broadly, not this product;
    honest, but slightly less on-message for a launch page than a product-specific quote
    would be (which I declined to fabricate).
  - **Secondary CTA fidelity.** The outlined hero secondary renders filled (renderer
    behavior), a small deviation from the brand's filled+outlined hero pair.
