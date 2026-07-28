# Greenhouse — published extraction results

- source site: https://www.greenhouse.com/
- run of record: `runs/greenhouse-4` (gitignored; this directory is the shareable export)
- published: 2026-07-28T19:05:27Z
- bundle size: 19.4 MB · 65 media files
- replica fidelity score: 0.7437

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
