# Greenhouse — published extraction results

- source site: https://www.greenhouse.com/
- run of record: `runs/greenhouse-4` (gitignored; this directory is the shareable export)
- published: 2026-07-28T19:31:15Z
- bundle size: 19.4 MB · 65 media files
- replica fidelity score: 0.7437 (from the report beside the published page)

## Run status — gates not passed

This run did not pass its own quality gates. The artifacts below are its current best output, published for browsing and review — not a certified-good build.

- The orchestrator writes a flow report when it finishes its gate spine, and this run has none — so the run never reached the end of that spine. (`brand/flow-report.json (missing)`)
- The last recorded flow run crashed at gate G3 (harness): render_components_preview failed (exit 1) — harness quality failed. (`logs/flow-g3g4.log`)
- Replica fidelity is 0.7437 against this run's 0.90 bar — below the bar. (`replica/replica-report.json`)
- The gate did flag the weakest sections numerically: featureGrid 0.2783, testimonial 0.3088, hero 0.7719. Low band scores are where the composed page diverges most from the source (1 band with no measurable source height is left out of this list). (`replica/replica-report.md`)
- Do not trust the run manifest over the report beside the page: the run manifest records status "completed" / pipeline_run_completed true, which the gate evidence above does not support; and the manifest's replica score (0.8206) predates the replica that is published here (0.7437 in the report beside the page). (`logs/manifest.json`)
- The harness quality artifact on disk reports ok=true — it was written after the flow log above, so it reflects a later rebuild rather than a passing flow run. (`harness/harness-quality.json`)

Browse it through the local Studio server (`./start-studio.sh`, port 1500):

    http://127.0.0.1:1500/artifacts/published/greenhouse-4/index.html

Or open `index.html` directly — every path in the bundle is relative, so it also works
from `file://` or any static host.

## Contents

- **Composed replica of the source page** — `replica/index.html`  
  Rebuilt from the extracted facts alone. Fidelity score 0.7437 against the source capture; per-band scores and the punch list are in replica-report.md.
- **Components & layout harness** — `harness/index.html`  
  Primitives, surfaces, blocks and every measured layout pattern rendered from the design system. Each pattern is also a standalone page under harness/layouts/.
- **Component catalog** — `catalog/index.html`  
  Machine-readable inventory of the components the extraction declared.
- **Framework build (React + Vite, single file)** — `framework/index.html`  
  The opt-in framework lane: a real React + Tailwind app generated from the same facts, built to one self-contained HTML file. Source stays in the run dir (runs/greenhouse-4/brand/framework/single/framework-claude).
- **Brand facts** — `brand/`  
  The authored extraction output (yaml/json); every page above is derived from it.
- **Logs & manifest** — `logs/`  
  Run logs, schema validation output, and `changes.md`.
- **Media** — `assets/`  
  One deduped copy of the media the pages actually reference.

## Regenerating

```sh
./venv/bin/python tools/publish_run_bundle.py --run runs/greenhouse-4 \
    --out artifacts/published/greenhouse-4
```

The script copies only finished artifacts, rewrites every asset reference to this
bundle's `assets/` dir, then loads each page in headless Chromium to assert it renders
content with no broken images (add `--base-url http://127.0.0.1:1500` to check it over the
running Studio, `--no-verify` to skip). Results land in `verify.json`.
