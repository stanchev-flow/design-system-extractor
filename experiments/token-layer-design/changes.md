# changes.md — token-layer design batch (read-only audit worker)

**Date:** 2026-07-03 ~00:10–00:50 (UTC+1)
**Worker:** READ-ONLY design/audit worker; write-fence = `experiments/token-layer-design/` only.
**Concurrent workers:** alignment-resolution batch (composers/gate in flight), HubSpot
extraction/E2E worker (`runs/hubspot/**`, `experiments/hubspot-e2e/**` live). No pipeline
runs, no regates, no server start/stop, no git operations performed by this worker.

## Written (complete list — nothing else touched)

- `experiments/token-layer-design/hardcode-audit.md` — hardcoded-visual-value inventory,
  ~40 curated clusters over 1,151 raw pattern hits across 6 files; REPORT.md cross-reference.
- `experiments/token-layer-design/SPEC.md` — implementation-ready token layer spec
  (schema, generation, renderer changes, token-provenance gate, AS-24 draft, drift sync,
  tests, sequencing, taste-skill pointers, open questions).
- `experiments/token-layer-design/changes.md` — this file.

## Read (context, in order)

1. `HANDOFF-2026-07-02.md` — architecture/operating rules (authoritative).
2. HubSpot E2E: report found at **`runs/hubspot/brand/REPORT.md`** (the prompt's
   `experiments/hubspot-e2e/REPORT.md` path does not exist); `experiments/hubspot-e2e/gen.log`
   … `gen5.log`, `results.json`, `run_page.py`.
3. https://hvpandya.com/llm-design-systems (fetched successfully).
4. Renderers audited: `brand_pipeline/component_render.py`, `compose_section.py`,
   `compose_page.py`, `render_components_preview.py`, `styles.py`, `render_section.py`,
   `compose_from_composition.py` (surface-intent map).
5. Gate/loop: `onbrand_check.py` (full), `readability.py` (skim), `generate_composition.py`
   (gate_composition + repair loop), `slop_audit.mjs` (header), `taste_sync.py`.
6. Brand layer: `runs/woodwave/brand/brand.yaml`, `runs/hubspot/brand/brand.yaml`
   (keys + values enumerated programmatically, read-only).
7. Kit/skill: `runs/woodwave/brand/kit/SKILL.md`, `kit/agent/tokens.css`,
   `brand_pipeline/export_kit.py` (`build_tokens_css`), `brand_pipeline/spec/anti-ai-slop.md`
   (AS-01…AS-23 ids), `brand_pipeline/spec/brand-designer-skill.md`.

## mtimes of volatile inputs at read time (live workers may have advanced them since)

- `runs/hubspot/brand/REPORT.md` — Jul 2 23:08:00 2026
- `runs/hubspot/brand/brand.yaml` — Jul 2 23:23:57 2026
- `experiments/hubspot-e2e/gen.log` 20:31:30 / `gen2.log` 20:41:00 / `gen3.log` 23:11:35 /
  `gen4.log` 23:35:50 / `gen5.log` 23:44:31 / `results.json` 23:44:31 (all Jul 2 2026)
- `brand_pipeline/component_render.py` — Jul 2 23:43:37 (**edited mid-audit by the other
  worker**; line anchors in the audit may drift — selector/function anchors are primary)
- `compose_section.py` 18:21:32; `compose_page.py` 18:53:07;
  `render_components_preview.py` 17:58:54; `onbrand_check.py` 17:45:01;
  `spec/anti-ai-slop.md` Jul 2 23:43:53 (also moving — AS-24 id may need renumbering)
- `runs/woodwave/brand/brand.yaml` — Jul 2 13:38:47

## Key findings log (for future debugging)

- The pipeline already has token layers 2–3 (`--c-*` contract + component CSS) and a
  layer-1 generator in `export_kit.build_tokens_css` (kit-only). The batch is: promote that
  generator to the compose path, close the loop (strip literals/fallbacks), gate provenance.
- The `gen.log` `KeyError: 'surface/inverse-strong'` was fail-loud-at-render on a then-missing
  HubSpot role token; the 23:23 brand.yaml refresh added the alias roles. SPEC moves that
  failure to tokens-generation time with an actionable message.
- AS-02 (truthy-string fallback trap) applies to live `compose_page` fallback sites (CP-1).

## Open questions (also in SPEC.md tail)

1. Layer-2 naming: keep `--c-*` vs article-style `--ds-*` aliases.
2. Fail-loud at generation vs render-with-sentinel for required tokens.
3. Flip duration/easing severity to error now (both brands have full motionSpec)?
4. Retrofit or retire `render_section.py` legacy single-section path.
5. HubSpot `tokens.imagery.aspectPalette` extraction gap — add or accept intrinsic-only.
6. Fluid clamp endpoints: calc-of-var in layer 2/3 vs precomputed static clamp in layer 1
   (Webflow variable mapping cleanliness).

---

IMPLEMENTED 2026-07-03: this spec shipped (decisions 1-6 applied) — see `experiments/token-layer-impl/REPORT.md` + `changes.md` (108/108 tests, 17/18 regate zero PASS→FAIL, WoodWave matrix parity-verified; HubSpot validation deferred behind the external worker fence).
