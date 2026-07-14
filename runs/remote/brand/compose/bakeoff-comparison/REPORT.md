# Remote Workforce Intelligence bakeoff — normalized comparison

## Verdict

Candidate A wins **83–81** (2 points), with **medium confidence**. A is materially more compact, pattern-qualified, and launch-ready, but its unsupported product-detail claims make the result close. Candidate B is more disciplined about evidence and has an excellent qualification form, yet its card-grid declarations produce a 31% longer authored page with repeated staggered/orphan modules.

The candidates were scored under neutral labels before model identity was consulted. Neither composition or authored brief artifact was changed.

## Normalization

- Shared renderer state is recorded once in `RENDER-STATE.json`.
- Both lanes were regenerated through `brand_pipeline/render_composition.py` from their untouched `composition.json`.
- Authored style choice was preserved: A declared `corporate-saas-clean`; B declared the non-file `brand-default`, so B used the renderer's inactive/default style path.
- Screenshots used Chromium at 1440×1000, device scale 1, reduced motion, fonts/images settled, animations disabled, and reveal targets forced visible.
- Each lane has one full-page image and ten identically named authored-section closeups.
- Authoring and normalized render elapsed times are kept separate:
  - Candidate A: previously reported authoring ~34 minutes; normalized render 1.3826s.
  - Candidate B: previously reported authoring ~12 minutes; normalized render 1.8928s.

## Normalized gates

| Gate | Candidate A | Candidate B |
|---|---:|---:|
| composition.v1 schema | PASS | PASS |
| onbrand hard gate | PASS | PASS |
| readability / contrast | PASS; 184 measured, worst 4.91 | PASS; 203 measured, worst 4.91 |
| anti-slop 1440 | PASS | PASS |
| anti-slop 1180 | PASS | PASS |
| interaction strict | PASS; 0 required failures | PASS; 0 required failures |
| spacing strict | **FAIL**; 1/157 hard | **FAIL**; 3/176 hard |
| unresolved slots | PASS; 0 | PASS; 0 |

Spacing failures remain visible:

- Shared, excluded from model judgment: both forms resolve to a 736px stack against the extracted 720px header measure (`off-ladder`, +16px).
- Candidate B only: comparison heading-to-body gap is 64px where 16px is declared (`wrong-step`); testimonial container resolves to 720px where 1169.28px is declared (`wrong-step`).
- Candidate A has no candidate-specific strict-spacing failure after the shared form-width item is excluded.

Raw reports are under each lane's `normalized-gates/`; normalized machine-readable results are in `normalized-gates.json`.

## Objective geometry at 1440px

Both candidates obey the main container law: wide sections are 1169.27–1169.28px with approximately 135.36px symmetric gutters and ≤0.02px centering error. Narrow FAQ stacks are 720px; forms are 736px. Both heroes use a 1169.27px centered panel, 48px section padding, and a 48px split gap.

Candidate A:

- Authored page before shared closing bookend: 8,009.84px; full page: 8,923px.
- Section padding is 48px except the two evidence-backed split sections at 64px.
- Product-value accordion: 1168px container, 101px split gap.
- Capabilities and how-it-works: true three-column grids, 32px gutters, 368.42px equal-width/equal-height cards, 0px height spread, 32px card padding.
- Comparison: 1169.27px split, 48px gutter, 560.63px columns; ruled rows remain stable at 480.64px.
- Form: 736px panel, 672px field grid, 328px half fields, 16px column/row rhythm.
- Testimonial rail intentionally extends beyond the viewport as the shared edge-cut carousel pattern; it is keyboard-operable and is not unexplained overflow.

Candidate B:

- Authored page before shared closing bookend: 10,762.11px; full page: 11,675px.
- Section padding is 48px except accordion and operational-trust splits at 64px.
- Accordion: 1168px container, 101px split gap.
- Reporting-gap and leadership grids render 662.06px / 459.19px staggered cards with 56px vertical offset and an orphan third card. How-it-works repeats the same stagger with four cards over two rows. This comes from authored `knobs.columns` without the renderer-supported `section.grid.columns`.
- Semantic comparison table is stable at 1016.95px across all six rows; the authored 64px header/body gap is a spacing wrong-step.
- Form: 736px panel, 672px field grid, 328px half fields, 16px column/row rhythm; eight fields provide stronger qualification than A's six.
- No unexplained collisions or horizontal page overflow were measured.

Both accordion media columns leave a visible lower well because a square image sits in a taller split column (A ~188.8px vertical remainder; B ~160.9px). This is shared renderer geometry and is excluded from model scoring. Full values and spacing-fact conformance are in `geometry.json`.

## Rubric scores

Scores were assigned independently before totals were compared.

| Category | Max | Candidate A | Candidate B |
|---|---:|---:|---:|
| Marketing strategy and narrative flow | 20 | 19 | 18 |
| Copy clarity, specificity, credibility, CTA progression | 20 | 18 | 17 |
| Pattern/content qualification | 15 | 14 | 11 |
| Remote brand fidelity | 15 | 14 | 14 |
| Layout coherence and spacing | 15 | 14 | 10 |
| Visual variety without unsupported novelty | 10 | 8 | 9 |
| Lead-generation effectiveness | 5 | 5 | 5 |
| **Base score** | **100** | **92** | **84** |

Separate penalties:

- Candidate A: −8 unsupported/invented product-detail claims; −1 adjacent repeated card-grid family. **Final 83.**
- Candidate B: −1 repetitive decision/review/context language; −2 composition-induced stagger/orphan layouts. **Final 81.**
- No hard-gate, interaction, unresolved-slot, or renderer-induced penalty was applied to either candidate.

## Qualitative findings

### Candidate A

Strongest sections:

- Hero: concise, product-oriented, immediately actionable, and visually native to Remote.
- Product-value accordion: strongest connection between product claim, interaction, and UI evidence.
- Capabilities/how-it-works: clean 3-up geometry and excellent scanability.
- Lead form: compact and polished, with a useful region and open-ended intent field.

Weakest sections:

- Proof: broad Remote testimonials are clearly attributed but are not evidence for Workforce Intelligence; the edge-cut third card is partially off-canvas by design.
- Comparison: the split is readable, but its payroll image is adjacent-product evidence rather than a Workforce Intelligence view.
- Credibility: “always current,” payroll-triggered refresh, compliance status, compensation benchmarking, day-one population, connectors/uploads, and role-based product/security behavior are not established by the marketer brief. Specificity is valuable, but these claims require product evidence.

Composition decisions responsible for A's advantage are explicit `section.grid.columns`, a compact mid-page conversion beat, a split comparison with supporting media, and three testimonials. Its main risk is treating plausible Remote-platform capabilities as verified launch-product facts.

### Candidate B

Strongest sections:

- Hero: equally strong visual execution with safer, cross-functional decision-layer positioning.
- Capability accordion: credible, restrained copy and useful per-item UI states.
- Comparison: the wide semantic table communicates operating change clearly without unsupported feature detail.
- FAQ and lead form: best buyer qualification and strongest credibility discipline; role, company size, footprint, and a real workforce question align tightly to qualified-demo intent.

Weakest sections:

- Reporting-gap, how-it-works, and leadership views: staggered two-up layouts with orphan modules substantially lengthen the page and weaken scan rhythm.
- Product story: repeated “workforce view,” “review,” “context,” and “decision” language avoids invention but remains abstract.
- Proof: only two broad-platform testimonials, with no mid-page CTA before FAQ/form.

Composition decisions responsible for B's result are the novel wide table, role-specific leadership section, explicit operational-trust split, broader FAQ, and eight-field form. Its main loss comes from declaring card count through inert `knobs.columns` rather than the supported grid contract.

## Shared renderer behavior excluded from model judgment

- Both secondary hero CTAs render filled despite authored outlined/secondary intent.
- Both 736px form stacks miss the extracted 720px measure by 16px.
- Both accordion splits leave a lower media remainder when square art occupies a taller column.
- Navigation, footer, edge-cut carousel mechanics, reduced-motion/reveal lifecycle, and image-loading hatch lifecycle are shared. They passed the applicable normalized gates and were not scored as model differentiation.
- The renderer's two-column semantic comparison contract constrains both candidates; A used a split row list and B used a wide `current → product` table. The contract itself was not penalized.

## Final reveal

- **Candidate A: Claude Opus 4.8 Thinking High**
- **Candidate B: GPT-5.6 Sol**

Winner: **Claude Opus 4.8 Thinking High by 2 points**, medium confidence. A's visual and structural advantage is clear; confidence is not high because the unsupported-claims penalty is judgment-sensitive and B is materially stronger on evidence discipline.

## Artifacts

- Comparison: `runs/remote/brand/compose/bakeoff-comparison/`
- Full report: `REPORT.md`
- Scores: `scorecard.json`
- Gates: `normalized-gates.json`
- Geometry: `geometry.json`
- Shared code state: `RENDER-STATE.json`
- Side-by-side screenshots: `shots/`
- Candidate A normalized screenshots/gates: `runs/remote/brand/compose/bakeoff-opus/normalized-shots/`, `normalized-gates/`
- Candidate B normalized screenshots/gates: `runs/remote/brand/compose/bakeoff-sol/normalized-shots/`, `normalized-gates/`
