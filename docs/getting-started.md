# Getting started

Setup for a fresh clone, and an honest account of what the clone does and does not
contain. Verified end to end on a clean clone of `origin/main`.

## Requirements

- **Python 3.12 or newer.** This is a hard floor, not a preference: `run_pipeline.py`
  and `src/screenshot_to_template/models/__init__.py` use PEP 701 f-strings, which
  earlier interpreters cannot parse at all. macOS ships Python 3.9, so the system
  interpreter will not work — check with `python3 --version` before anything else.
- Roughly 2.5 GB of disk for the clone. A good part of that is run output committed
  so the Studio has something to show (see
  [What a clone gives you](#what-a-clone-gives-you)).
- An API key only if you intend to run the pipeline. Browsing published results
  needs none.

## Install

```bash
git clone <repo-url>
cd design-system-extractor

python3 --version                    # must be 3.12+
python3 -m venv venv
./venv/bin/pip install -e '.[dev]'
./venv/bin/playwright install chromium
```

**A plain `git clone` may die partway through.** At ~2.5 GB this repo is big enough that
GitHub's HTTP/2 transfer gets cut off — `RPC failed; curl 92 HTTP/2 stream … CANCEL`,
then `fatal: early EOF`, several minutes in, leaving nothing behind. It is not a
corrupt repo and retrying as-is does not reliably help. Force HTTP/1.1 instead:

```bash
git -c http.version=HTTP/1.1 clone <repo-url>
```

That completes in about four minutes on a normal connection. `--depth 1` is **not** a
workaround; the shallow fetch fails the same way.

**Check that version before creating the venv.** On macOS, `python3` on your `PATH` is
often Apple's `/usr/bin/python3`, which is 3.9 — building the venv with it produces a
venv that cannot run this project. If `python3 --version` is older than 3.12, name the
interpreter explicitly:

```bash
python3.13 -m venv venv              # or python3.12 / python3.14 / brew's python3
```

`pip install -r requirements.txt` does the same thing as `pip install -e '.[dev]'` —
that file just points at `pyproject.toml` so there is one dependency list.

The `playwright install chromium` step is not optional if you plan to run anything:
about 29 modules drive a headless browser, including page capture, computed-style
measurement, replica rendering and much of the test suite. It downloads roughly
150 MB into a per-user cache (`~/Library/Caches/ms-playwright` on macOS).

> If `PLAYWRIGHT_BROWSERS_PATH` is set in your environment — some sandboxes and CI
> images set it — Playwright will look for browsers somewhere they are not, and fail
> with "Executable doesn't exist". The repo convention is to unset it for the
> command: `env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python …`. You will see that
> prefix in a lot of the docstrings and changelogs.

API keys, if you need them:

```bash
cp .env.example .env.local     # then fill in the keys you actually use
```

`.env.local` is gitignored and is read automatically by `run_pipeline.py`. Only
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` and `GEMINI_API_KEY` are
picked up.

## Check the install

```bash
./venv/bin/python -m pytest tests/ -q
```

`tests/` is the suite to trust on a fresh clone: it takes seconds, needs no browser, no
API key and no run data, and should be fully green. If it is not, something about the
install is wrong.

**`brand_pipeline/tests/` will not pass on a clone, and that is not your fault.** It
takes a couple of minutes, renders in Chromium, and a large part of it reads local run
output under `runs/` — which is gitignored, so the files simply are not there
(`FileNotFoundError: runs/<brand>/brand/brand.yaml` and similar). On a clean clone
roughly 90 of its ~2000 tests fail or error for that reason. It is a suite for someone
who has run the pipeline locally, not an install check. Run it with
`env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m pytest brand_pipeline/tests/ -q`.

## What a clone gives you

Tracked, so you get it:

- All the source: pipeline, `brand_pipeline/`, extraction tools, prompts, contracts.
- `artifacts/published/` — self-contained exports of finished runs. Currently one:
  `greenhouse-4`.
- **Eleven working Studio projects.** `runs/` and `screenshots/` are gitignored, but
  the parts of each brand lane that the Studio actually opens are negated back in:
  `greenhouse`, `greenhouse-4`, `greenhouse-v2`, `hubspot`, `hubspot-v2`, `hubspot-v3`,
  `hubspot-v4`, `relume-test`, `remote`, `woodwave`, `woodwave-v2`. Start the Studio
  and they are all there, with thumbnails, source captures, catalogs, replica and
  harness lanes, composed pages and their media. About 435 MB of the clone.

Not tracked, so you do not get it:

- **Source captures beyond one full-page image per project.** The saved HTML page and
  its `_files` mirror stay out, so you cannot re-run extraction from the clone.
- **The framework build *workspaces*** (`brand/framework/single/<app>/`) — Vite sources
  and `node_modules`, hundreds of megabytes. The built page itself is a different
  matter: it is a single self-contained file, so `greenhouse` and `greenhouse-4` do
  ship theirs (~0.5 MB the pair) and the Studio serves them as ordinary lanes. Projects
  with no build get a row saying so rather than a link to a dev server you are not
  running.
- **`brand/evidence/`** beyond the handful of files the document tabs read,
  **`_archive/`**, per-page diff crops, and every extra viewport re-shoot of a lane.
- **The experiment lanes and pipeline version folders** (`hubspot-sol`,
  `style-calibration`, `v170`–`v178`, …). Brand lanes only.
- **`viewer-data/`** — the viewer's payload files.

Practical consequences:

- `viewer.html` is a stub that redirects into the Studio canvas. Opened as a file it
  cannot redirect anywhere and says so; served by the Studio with no `?version=`, it
  lands on `/studio`.
- A few document tabs a lane has locally are missing in a clone, and for two different
  reasons. Walked tab by tab over HTTP against a clean clone of this commit: no **Author
  report** on `greenhouse-v2`; no **Replica fidelity** on `greenhouse-v2`,
  `greenhouse-4`, `hubspot-v3`, `hubspot-v4` or `woodwave-v2`; no **Validation** on
  `greenhouse-4`; no **Changelog** on `relume-test`. Only two of those are about
  privacy: `runs/greenhouse-v2/brand/author-report.json` and
  `runs/relume-test/changes.md` record the absolute path of the machine that produced
  them, and this repo is public. The rest carry no local paths — leaving them out is a
  size decision, not a safety one. Every other tab, on every one of the eleven, a clone
  has too. A tab with nothing behind it is not rendered at all, so these show up as an
  absent pill rather than an empty pane.
- Re-running the pipeline against a source site means capturing that site yourself
  first. See [Re-running the pipeline](#re-running-the-pipeline).

### Adding another project to the clone

`tools/track_studio_subset.py` decides what a project needs, prices it, and writes the
`.gitignore` negations. It never copies run data — the Studio reads `runs/` in place.

```bash
./venv/bin/python tools/track_studio_subset.py --run runs/<project>   # price it first
./venv/bin/python tools/track_studio_subset.py --run runs/<project> \
    --register --check --write-gitignore --stage
```

`--write-gitignore` regenerates the whole managed block from the runs you pass it, so
pass every project that should stay tracked, not just the new one. `--check` reports
any local reference from a tracked page that would 404 in someone else's clone; treat
a non-empty result as a project that is not ready to commit.

## Browse the published results with no server

Open `artifacts/published/greenhouse-4/index.html` in a browser. The bundle is
self-contained and needs no server, no API key and no browser install. Everything that
run produced is reachable from there: the generated site, design system, tokens,
harness, replica with its fidelity report and diffs, and the raw logs.

Read `artifacts/published/greenhouse-4/README.md` first. It is blunt about that run's
status, and worth taking at face value: the run **did not pass its own gates** — it
crashed at G3 (harness) and its replica fidelity is 0.7437 against a declared 0.90
bar. The bundle is published for browsing and review, not as a certified-good build.
Its README also flags that the run's own `manifest.json` claims `completed`, which the
gate evidence does not support — trust the reports beside the page, not the manifest.

## Run the Studio

```bash
./start-studio.sh                 # http://localhost:1500/studio
```

The Studio serves the viewer, `runs/**`, the published bundles, and the project API on
one port. Set `STUDIO_PORT` to move it. Don't substitute `python3 -m http.server` —
that has no `/studio` route.

`start-studio.sh` refuses to start on a missing venv, an interpreter older than 3.12,
or a venv without dependencies installed, and tells you which. That is deliberate: the
Studio launches every pipeline run with its own interpreter, so a Studio started on the
wrong Python looks perfectly healthy right up until a run dies with a SyntaxError.

Two things worth knowing:

- **The Studio UI loads Tailwind from `https://cdn.tailwindcss.com`.** With no network
  it works but renders unstyled. Nothing is vendored.
- The Run button starts a real pipeline run, with the cost and duration described
  below.

## Configuration

`config.default.yaml` is the CLI baseline, always loaded first; a `--config` file is
merged over it. The two shipped configs differ on purpose:

| | `config.default.yaml` (CLI) | `config-anthropic.yaml` (Studio base) |
| --- | --- | --- |
| `framework-generation-enabled` | `false` | `true` |
| provider | `openai` / `gpt-5.5` | `anthropic` / `claude-opus-4-8` |

Plain CLI runs stop at brand compose — token CSS plus static HTML — which is the
canonical product path. The Studio's path is framework-first, so every Studio project
inherits framework generation on. `false` in `config.default.yaml` is pinned by
`brand_pipeline/tests/test_brand_signal_composition.py`; per-run opt-in on the CLI is
`--framework-sites`.

Framework generation is fail-closed behind ordered gates (G1 extraction → G2
validation → G3 harness → G4 replica ≥ bar) and will refuse for a lane that has not
cleared them. `framework-generation-allow-ungated` exists to override that knowingly;
leave it alone unless you mean it.

One wrinkle: `AppConfig`'s dataclass default for `framework_generation_enabled` is
`True`. It only applies when a config is built without `load_config()`, which always
reads `config.default.yaml` and so always lands on `false`.

## Re-running the pipeline

Read this before starting one.

The source captures are not in the repo, so you cannot reproduce a published run from
a clone alone. The sequence is:

```bash
# 1. capture the source pages (one per page)
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python tools/extract/capture_page.py \
    --url https://example.com --out screenshots/<brand>/<page> --name <page>

# 2. mine + ground the captures
#    the exact recipe used for the published run is committed at
#    artifacts/published/greenhouse-4/logs/extract_pages.sh
```

`extract_pages.sh` is the real recipe, not a sketch: per page it runs `mine_dom`,
`mine_css`, `mine_motion`, `measure_computed`, `slice_sections`, `curate_assets`, then
vision grounding over the crops. It expects captures at `screenshots/<brand>/<page>`
and writes into `runs/<brand>/brand/`.

Set expectations honestly:

- **Hours of wall clock** for a multi-page brand.
- **A real API bill.** Grounding is high-effort vision calls over every section crop
  of every page, and generation stages are large model calls on top of that.
- **Nondeterministic output.** Two runs of the same source do not produce the same
  design system or the same fidelity score.
- **A run can finish and still not be good.** `greenhouse-4`, the run published in
  this repo, did not clear its own gates. Check the gate evidence, not the manifest.

If you just want to see what the pipeline produces, the published bundle is the cheap
answer and needs no server, no key and no browser install.

## When something breaks

| Symptom | Cause |
| --- | --- |
| `fatal: early EOF` / `curl 92 … CANCEL` while cloning | HTTP/2 cutting off a 2.5 GB transfer. Clone with `git -c http.version=HTTP/1.1`. |
| `SyntaxError` in `run_pipeline.py` | Interpreter older than 3.12. |
| Studio refuses to start with a Python version message | Same, caught early. Rebuild `venv` on 3.12+. |
| `ModuleNotFoundError: playwright` | `pip install -e '.[dev]'` not run, or run against the wrong interpreter. |
| `Executable doesn't exist … chromium` | `playwright install chromium` not run, or `PLAYWRIGHT_BROWSERS_PATH` points elsewhere. |
| `Screenshots directory not found` | Expected on a clone — only one full-page image per project is tracked. Capture first. |
| A "Framework build" row is grey and not clickable | Working as intended. That project registered a dev server but has no built output, so the row states what to run instead of pretending to be a link. `greenhouse` and `greenhouse-4` ship a real build and do open. |
| A project has no "Exact nav/footer" lane | Working as intended. The lane is offered only by the runs that generated one; it is no longer advertised where it could only 404. |
| Studio renders unstyled | No network; its Tailwind comes from a CDN. |
| `git status` dirty right after install | Should no longer happen: `src/screenshot_to_template.egg-info/` is untracked and ignored. Anything else dirty is your own change. |
