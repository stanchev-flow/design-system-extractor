# PROMPT — bakeoff candidate B (Claude Opus 4.8 Thinking High)

Model label: **Claude Opus 4.8 Thinking High**
Lane: `runs/remote/brand/compose/bakeoff-opus/`

This file preserves the EXACT marketer brief and operational requirements as received.
Nothing below is paraphrased.

---

## EXACT MARKETER BRIEF — treat this as the entire creative/content request

Create a launch landing page for Remote’s new Workforce Intelligence product. Target VP People, CFO, and HR Operations leaders at international companies with 500+ employees. The goal is qualified demo requests. Build approximately 10 sections that explain the problem, product value, key capabilities, how it works, customer proof, comparison with the current way of working, FAQ, and a lead form. Keep the copy concise, credible, and specific; do not invent customer claims or statistics. Use the extracted Remote design system and existing assets to create a page that feels natively Remote but is not a copy of its homepage.

## Neutral operational requirements (not creative guidance)
- Read only the canonical Remote design-system inputs needed to execute the brief: `runs/remote/brand/brand.yaml`, `layout-library.yaml`, `section-copy.yaml`, `voice.md`, and kit/agent docs; shared schemas/rendering code as needed.
- Do not read prior generated-page artifacts.
- Create `PROMPT.md` preserving the exact marketer brief, `PLAN.md`, `copy-brief.md`, valid `composition.json`, deterministic `index.html`, lane-local `changes.md`, gate outputs, `REPORT.md`, and `shots/` with a 1440px full-page image plus per-section closeups.
- Use the current deterministic composition renderer; never hand-edit generated HTML.
- Run available onbrand/slop checks scoped to the lane.
- Visually inspect screenshots and correct composition/copy mistakes only. Document shared renderer defects rather than editing shared code.
- In REPORT.md record elapsed time, model label, section/pattern mapping, gates, artifact paths, and an honest self-critique.

## Bakeoff isolation constraints (as instructed)
- Independently author and render; do NOT consult any prior generated page, stress-playbook, Sol experiment, their plans/copy/compositions/reports/screenshots, or the other bakeoff lane.
- Write ONLY under `runs/remote/brand/compose/bakeoff-opus/`.
- Do not edit shared source, brand files, viewer, root changelog, other lanes, or Studio.
- Record SHA-256 hashes and mtimes of the shared renderer files used at render time in `RENDER-STATE.json`.
- Do not compensate for shared renderer bugs by hand-editing HTML (the parent will re-render both candidates against one final code state).
