# GPT-5.6 Sol comparison run

Model label: **GPT-5.6 Sol**

## Experiment brief

Generate a new experimental Remote marketing page using original reasoning and writing. Own the page concept, copy, composition planning, deterministic render, screenshots, and evaluation. The purpose is to test whether GPT-5.6 Sol can use the extracted Remote design system more coherently than the prior generation attempt.

Write only under `runs/remote/brand/compose/sol-experiment/`. Read shared inputs, but do not modify shared renderers, CSS, schemas, `brand.yaml`, `layout-library.yaml`, root changelogs, or `viewer.html`. Studio is supervised on port 1500; do not start or stop a server. Author first, then render once against the latest shared renderer state.

Study these sources:

- `runs/remote/brand/brand.yaml`
- `runs/remote/brand/layout-library.yaml`
- `runs/remote/brand/section-copy.yaml`
- `runs/remote/brand/voice.md`
- relevant files under `runs/remote/brand/kit/agent/`
- `brand_pipeline/spec/anti-ai-slop.md`
- `brand_pipeline/spec/composition-rules.md` if present
- prior planning and machine inputs only: `stress-playbook/PLAN.md`, `copy-brief.md`, and `composition.json`
- diagnoses: `stress-playbook/REPORT.md`, `spacing-baseline/report.md`, and `interaction-baseline/report.md`

Do not copy the prior concept, copy, or section sequence. Treat its reports as failure modes to avoid.

## Goal

Create a polished, coherent Remote-branded lead-generation page of approximately ten sections around a new concept appropriate for Remote's business and voice. Demonstrate generative range, while prioritizing clarity and captured brand grammar over novelty. Select and compose captured patterns without visual slop.

## Composition requirements

1. Use conventional mechanics for simple content. A standard split is a two-column grid with a complete, left-aligned header stack on one side and media on the other. Use editorial interlocks, floats, offsets, or overlaps only when both evidence and content require them.
2. Center standalone headers above stacked content, including text and actions. Keep headers inside split columns left-aligned.
3. Keep all content inside the captured capped, centered brand container. Only backgrounds may be full bleed.
4. Use captured card-grid gutters. Equalize cards and preserve a minimum CTA seam, allowing body slack to absorb extra height.
5. Let media treatment follow content kind: fill product screenshots and photographs edge-to-edge with the appropriate crop; contain transparent illustrations. Do not float small screenshots in unexplained empty wells.
6. Give comparison rows and repeated records stable columns and aligned text starts.
7. Use captured spacing rungs and relational facts for eyebrow-to-heading, heading-to-body, body-to-actions, grid gutters, card padding, list rhythm, and section padding. Do not apply one uniform gap to heterogeneous stacks.
8. Do not invent component anatomy for variety. Compose novel pages from captured brand grammar and reusable roles.
9. Avoid unsupported decoration: arbitrary gradients, blobs, shadows, pills, excessive rounded cards, random overlap, and oversized non-hero display text.
10. Use only current renderer interaction semantics. Accordions must author intended single-open grouping; avoid unsupported anatomy.

## Required process and artifacts

Create incrementally:

1. `PROMPT.md`
2. `PLAN.md` with concept, audience, narrative arc, section list, selected pattern/device, and content-shape qualification
3. `copy-brief.md` with final copy and microcopy
4. schema-valid `composition.json`
5. deterministic `index.html` emitted by `brand_pipeline/compose_from_composition.py`, never hand-edited
6. lane-scoped on-brand and anti-slop gate outputs
7. `shots/` containing a 1440px full-page capture and one closeup per section, with reduced motion and reveal stabilization
8. `REPORT.md` with pattern mapping, gates, visual review, renderer deficiencies, and deliberate simpler-over-novel choices
9. lane-local `changes.md`

After rendering, inspect screenshots for standalone versus split alignment, container widths, card gutters and equalization, padding and CTA seams, media crop/fill, repeated-row alignment, relational header spacing, unexplained voids, and collisions at 1440px. Fix composition defects in `composition.json` and re-render. Document shared renderer defects with section id, emitted class, symptom, and likely cause; never patch emitted HTML.

The final handoff must report the concept, section count and pattern mapping, artifacts, gates, screenshots, and a concise comparison against the documented stress-playbook failures.
