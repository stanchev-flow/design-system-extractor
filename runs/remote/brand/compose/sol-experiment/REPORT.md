# REPORT — GPT-5.6 Sol comparison run

## Outcome

**Concept:** Global Payroll Consolidation Plan  
**Authored sections:** 10, plus the shared closing footer  
**Primary conversion:** Get your payroll plan

The page is a direct lead-generation journey for finance, people, and payroll leaders replacing a country-by-country provider stack. It is not a resource-download page and does not reuse the prior stress-playbook concept, copy, editorial statement, or section order.

The final render is coherent at 1440px: one simple split hero, early customer proof, a media-left infrastructure explanation, a centered equalized card grid, factual stat band, exclusive implementation accordion, contained semantic comparison table, partner proof, exclusive FAQ, and one closing qualification form.

## Section and pattern mapping

1. **`sol-hero`** — split · `hero-inset-noise-panel`  
   Complete left-aligned offer stack with transparent illustration on the right. The captured inset art panel is the only hero device.
2. **`sol-proof`** — stack · `logo-marquee-strip`  
   Centered proof caption and eight real monochrome customer marks.
3. **`sol-control`** — split · `infra-proof-split`  
   Captured product proof on the left; complete left-aligned infrastructure copy on the right.
4. **`sol-workstreams`** — cards · `features-card-grid-navy-media`  
   Centered standalone header and three equal-height cards using the pattern’s own navy media assets.
5. **`sol-scale`** — stack · generic stats flow, honest pattern miss  
   Centered header and three real `stat` contracts: 170+, 1, and 4,000+.
6. **`sol-process`** — split · `feature-accordion-deep-accent`  
   Four single-open stages, one authored open, named exclusive group, distinct UI per stage, one deep-accent active card.
7. **`sol-decision`** — stack · semantic table, honest pattern miss  
   Centered header over a stable three-column table. No comparison split or viewport-wide scaffold.
8. **`sol-ecosystem`** — stack · `partner-proof-row`  
   Centered copy, four captured colored partner marks, one outlined action.
9. **`sol-faq`** — stack · FAQ composer, honest pattern miss  
   Centered standalone header and five single-open questions on the neutral surface.
10. **`sol-plan-form`** — stack · `cta-closing-noise`  
    Centered reason-for-contact copy and a compact, real qualification form on the captured closing art band.

## Gate results

- **Composition render:** PASS — `unresolved slots: 0`.
- **On-brand gate:** **OVERALL PASS** with all hard composition invariants passing.
  - neverDo: pass
  - source fidelity: pass
  - generic slop checklist: pass
  - composition invariants: pass
  - text and interaction contrast: pass
  - token provenance: pass with one non-gating marquee-duration warning
  - logo-wall integrity: pass
- **Anti-slop audit:** **PASS at 1440px and 1180px**.

The final on-brand outputs are `onbrand-report.md` and `onbrand-report.json`; the anti-slop result is preserved in `slop-report.txt`.

## Visual review

All ten closeups and the full page were inspected after the final render.

- **Header alignment:** standalone headers in workstreams, stats, comparison, ecosystem, FAQ, and form are centered. Split headers in hero, control, and process are left-aligned.
- **Containers:** content stays inside the centered Remote container. Only the closing noise-art background bleeds; the form remains on the measured 870px stack.
- **Card grid:** three equal-width/equal-height cards use the captured 32px gutter. The navy media fills each well edge-to-edge; text padding is consistent; actions share a bottom seam with visible body-to-action space.
- **Media treatment:** the hero globe and split proof are transparent illustrations and use contain. The workflow card assets include their navy surfaces and fill the media wells. Accordion product collages use contain on the captured square well.
- **Comparison alignment:** row labels and both comparison columns have fixed starts across every row. The table stays inside the standard container.
- **Relational spacing:** eyebrow-to-heading, heading-to-body, header-to-content, section padding, and action seams read as distinct captured rungs rather than one uniform gap.
- **Voids and collisions:** no collision was observed at 1440px. The open process item creates expected vertical continuation below the square media, but the list and closing action occupy that space; it is not an empty scaffold.

## Composition corrections made after inspection

1. The first comparison draft used a button slot. That made the stack resolve as a conversion section and dropped the table. The composition now uses a closing text link, so the generic stack renders the semantic table.
2. The first closing-form draft named its lede role only “supporting paragraph.” The conversion translator keys on a body-role slot, so the lede was dropped and AS-14 fired. The role now explicitly includes `body`.
3. The first card draft used transparent payroll collages. They contained correctly but did not express the captured navy-media grammar strongly enough. The final cards use the pattern’s own `card-integrations`, `card-api-first`, and `card-mcp-agents` assets, with copy revised to match their content.
4. The workstream intro role was made explicit as a body slot so the captured header → body → grid ladder renders.

No emitted HTML was hand-edited.

## Shared renderer notes

No material shared-renderer defect remains visible in the ten authored sections. Pattern misses for stats, comparison, and FAQ are honest and expected because the layout library has no matching captured pattern; the explicit contract renderers handle those sections cleanly.

One non-gating shared warning remains: `sol-proof` emits `.cs-marquee-track` CSS with a raw `30s` animation fallback, reported by token provenance even though the section carries its measured marquee-duration variable. This does not affect layout or legibility.

During the final visual pass, the shared Playwright browser cache disappeared while another lane was changing shared dependencies. The write fence prohibited reinstalling a browser outside this lane. `shots/shoot_sections.mjs` and `slop_chrome_preload.mjs` therefore point Playwright at the already-installed system Chrome; shared audit and renderer files remain untouched.

## Deliberately simpler choices

- Used a conventional split for the hero and infrastructure explanation instead of an editorial interlock, overlap, float, or offset.
- Used a semantic table instead of the prior run’s comparison split, which had a 1360px content width, zero split gutter, and broken heading/body seam.
- Used three peer cards instead of a bento mosaic.
- Avoided a testimonial carousel because the narrative did not require an edge-cut rail and the interaction burden would add no decision value.
- Authored both disclosure families as exclusive/single-open.
- Reserved the form for the closing destination rather than inserting a mid-page form or extra conversion banner.

## Comparison with the prior stress-playbook run

The stress-playbook intentionally maximized device novelty and exposed weak fallbacks: an unsupported-looking stats hierarchy before remediation, an editorial interlock with a wrong action seam, a comparison scaffold outside the container with no gutter, card-grid gutter drift, and non-exclusive FAQ behavior. This run is more coherent because selection follows content preconditions rather than coverage goals.

The clearest improvement is the comparison: stable semantic columns now replace pseudo-rows in an oversized split. The card grid uses its captured gutter, equalization, media family, and centered standalone header. Both accordion groups author single-open semantics. The result has less layout novelty, but better narrative continuity, fewer exception devices, and no composition-level gate failures.

The remaining self-critique is content density: the page is intentionally operational and may feel more like a considered product assessment than a high-energy campaign. That restraint is appropriate for the audience and Remote voice, but a production iteration could test one additional named customer proof point if fresh, attributable evidence were available.

## Artifacts

- `PROMPT.md`
- `PLAN.md`
- `copy-brief.md`
- `composition.json`
- `index.html`
- `tokens.manifest.json`
- `onbrand-report.md`
- `onbrand-report.json`
- `slop-report.txt`
- `assets/`
- `shots/full-page-1440.png`
- `shots/sec-0-sol-hero.png` through `shots/sec-9-sol-plan-form.png`
- `shots/shoot_sections.mjs`
- `changes.md`
