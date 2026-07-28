# Changes — environment and setup

Changelog for the clone-and-run story: interpreter floor, dependency declaration,
setup docs, and the failure modes a fresh clone used to hit. Kept here rather than in
the root `changes.md` because these changes are not tied to a `runs/vNNN/` version
folder, and because the root changelog was being edited concurrently.

## 2026-07-28 — A fresh clone can install and run

Established empirically on a clean clone that a teammate could not get the repo
running, and that the first failure was silent and misleading rather than loud.

### The interpreter floor was wrong by two minor versions

`pyproject.toml` declared `requires-python = ">=3.10"`. `run_pipeline.py` (the section
grounding block around line 2740) and `src/screenshot_to_template/models/__init__.py`
use PEP 701 f-strings — nested same-quote quoting — which needs **3.12+**. On macOS
system Python 3.9.6 those two files do not parse at all; they are the only two in
`src/` + `tools/` + `brand_pipeline/` + `tests/` that fail to.

- `pyproject.toml`: `requires-python = ">=3.12"`, with the reason in a comment so it is
  not "tightened" back later.

### `start-studio.sh` failed silently, hours late

`start-studio.sh` fell back to system `python3` whenever `venv/` was absent. Because
`studio_server.py` sets `PY = sys.executable`, the Studio then started, served a
healthy-looking UI, and the Run button launched the pipeline under 3.9 — which died
with a SyntaxError much later, far from the actual cause.

- `start-studio.sh`: the fallback is gone. Three fatal, actionable checks before exec:
  no interpreter at `$PY`, interpreter older than 3.12 (reported with the version it
  found), and dependencies not installed in that interpreter. Each prints the exact
  commands to fix it and points at `docs/getting-started.md`. `PY` and `STUDIO_PORT`
  overrides still work, and an explicitly-set `PY` is version-checked too.
- `studio_server.py` was **not** modified (it is owned by another agent this session).
  No change is needed there: deriving the pipeline interpreter from `sys.executable` is
  correct once the launcher guarantees the interpreter.

### Three undeclared dependencies, and no documented install step

`playwright` (imported by 29 tracked modules), `jsonschema`
(`tests/test_relume_recipe_catalog.py`) and `pytest` (the whole suite) were nowhere in
`pyproject.toml`, and no install step was documented anywhere.

- `pyproject.toml`: `playwright>=1.40` and `jsonschema>=4.0` added to `dependencies`;
  `pytest>=8.0` added under a new `[project.optional-dependencies] dev` extra.
- `requirements.txt` (new): a one-line `-e .[dev]` pointer so there is exactly one
  dependency list, plus the `playwright install chromium` reminder in a comment.
- The Playwright browser download was undocumented despite ~29 modules needing a
  browser. Documented, including the `env -u PLAYWRIGHT_BROWSERS_PATH` convention that
  the repo's own docstrings use — a stale value in the environment is what makes
  Playwright report "Executable doesn't exist".

### A missing screenshots directory crashed and left a phantom project

`run_pipeline()` created `runs/<version>/` before validating its input, so a bad
`--screenshots-dir` (the README Quick Start path is gitignored, so this was every
clone) produced an unhandled `FileNotFoundError` from `screenshots_dir.iterdir()` and
left an empty `runs/v001/` behind. The Studio then listed that empty directory as a
project.

- `run_pipeline.py`: input is validated first, and `version_dir.mkdir()` moved after
  both checks. A missing directory now exits 1 with an explanation and the
  `capture_page.py` command to fix it; an existing-but-empty directory says which file
  extensions it wanted. Verified against a temp `--runs-dir`: nothing is created.

### The `viewer.html` stub was a dead end in a clone

The generated stub baked in whichever project was newest on the *generating* machine
(`woodwave`), which no clone has, and redirected to an absolute `/project/...` path
even when opened as a `file://` URL where no server exists.

- `run_pipeline.py` (`generate_viewer`): the stub bakes in no default version. With no
  `?version=` it goes to `/studio`, which lists what actually exists. Over `file://`
  it does not navigate at all and explains how to start the Studio instead.
- `viewer.html` regenerated with the repo venv per `AGENTS.md`.
- Note: `studio_server.py` already 302s `/viewer.html` → `/studio` server-side, so the
  stub's own script only runs for `file://` or a non-Studio static server. The two
  behaviours now agree.

### The config contradiction is intentional; the README is stale

`config.default.yaml` says `framework-generation-enabled: false`;
`config-anthropic.yaml` says `true`. Both are deliberate and neither was changed:

- `config.default.yaml` is the always-loaded CLI baseline. `false` is pinned by
  `brand_pipeline/tests/test_brand_signal_composition.py::FrameworkDefaultOff`; brand
  compose (token CSS + static HTML) is the canonical CLI product path, and
  `--framework-sites` is the per-run opt-in.
- `config-anthropic.yaml` is the Studio's base config (`studio_server.py`) and the
  Studio's path is framework-first, so Studio projects inherit it on.
- `README.md:449` claims `true` is the default in `config.default.yaml`. That is wrong
  and predates the change; the README is owned by another agent this session and was
  not edited.
- **No runtime behaviour changed.** Both files gained comments stating the
  relationship, and `framework-generation-allow-ungated` was left untouched.
- Also documented, because it reads like a contradiction and is not: `AppConfig`'s
  dataclass default is `True`, which only applies when a config is constructed without
  `load_config()` — and `load_config()` always reads `config.default.yaml`.

### Three tests failed on a clean clone

Treated as "known pre-existing" for a while; a teammate hits them on first run. Both
root causes were real defects in source, not stale assertions, except where noted.

1. `test_prompt_guidance_includes_responsive_rules_and_variant_axes` and
   `test_prompt_guidance_enforces_brand_style_precedence_and_corpus_boundary` —
   `render_recipe_guidance(recipes, *, limit=10)` guards `if limit > 3: raise`, so
   **every call that omitted `limit` raised**. The hard cap is the intended contract
   (all in-repo callers pass ≤ 3); the default was never lowered to match. Fixed in
   `brand_pipeline/relume_recipe_catalog.py`: default is now `3`.
2. The second test additionally required the emitted guidance to state the precedence
   the catalog declares in `source.selectionPrecedence`
   (`active-brand-facts` → `active-style-structure` → `brand-neverDo-and-physics` →
   `selected-structural-prior`). The prose ranked *pattern sources* but never said that
   active brand facts win outright, so a candidate could silently outrank a fact. Added
   one palette-agnostic, section-agnostic sentence to `render_recipe_guidance`.
3. `test_site_generation_default_keeps_both_final_site_models` — here the **test** was
   stale. `DEFAULT_SITE_GENERATION_PROVIDERS` is deliberately `("claude",)`
   (framework-first: one build; `run_pipeline.py:143` says so), and the test still
   asserted `("claude", "gpt55")`. Updated and renamed to
   `test_site_generation_default_is_a_single_claude_build`, and strengthened to also
   pin that `gpt55` remains *allowed* and selectable via
   `site-generation-providers.txt` — which is the part that actually matters.

### Tracked `runs/` data contradicted its own ignore rule

`.gitignore` says "Large generated artifacts — regenerate locally" directly above
`runs/`, while ~248 MB of `runs/remote/` and `runs/hubspot-v2/` remains tracked from
before that rule.

- `.gitignore`: comment clarifies that those two are frozen legacy snapshots, not
  current output, and that untracking them is a separate unmade decision. **Nothing was
  deleted, untracked, or removed from the ignore rule.**

### New documentation

- `docs/getting-started.md` (new): requirements and the macOS `python3`-is-3.9 trap,
  install, Playwright browsers, API keys, what a clone does and does not contain, how
  to browse `artifacts/published/` with no server, running the Studio, the two configs,
  what re-running actually costs, and a symptom/cause table.
- It states plainly that `greenhouse-4` — the one published run in the repo — did not
  clear its own gates, and that re-running means hours of wall clock, a real API bill
  for high-effort vision calls, and nondeterministic output.
- It also documents that the Studio UI loads Tailwind from `https://cdn.tailwindcss.com`
  and therefore renders unstyled offline. Nothing was vendored.
- **Follow-up: `README.md` needs a link to `docs/getting-started.md`.** The README is
  owned by another agent this session, so the link was not added.

## Verification

Everything below was run on a clean `git clone` into `/tmp/dse-clean`, not in the
working tree, following `docs/getting-started.md` verbatim.

```
python3 --version                                  # 3.9.6 → doc's "use an explicit
python3.14 -m venv venv                            #   interpreter" path, as written
./venv/bin/pip install -e '.[dev]'                 # playwright, jsonschema, pytest land
./venv/bin/playwright install chromium
./venv/bin/python -m pytest tests/ -q              # 114 passed
STUDIO_PORT=1533 ./start-studio.sh                 # /studio → 200
```

- `tests/` on the clean clone: **114 passed, 0 failed** — including the three that
  failed before this change. (The working tree collects more because other agents have
  uncommitted tests there; that suite is green too: 133 passed.)
- `brand_pipeline/tests/` on the clean clone: 1982 passed, 62 failed, 26 errors. Those
  are not install failures — a large part of that suite reads gitignored run output
  (`runs/<brand>/brand/brand.yaml` and similar) and cannot pass without a local run.
  Documented as such in `docs/getting-started.md` so nobody reads it as a broken setup.

- Browser proven working from the clone, both with `PLAYWRIGHT_BROWSERS_PATH` set and
  with `env -u PLAYWRIGHT_BROWSERS_PATH`: `chromium.launch()` → 149.0.7827.55, page
  content read back.
- Studio in the clone: `/studio` 200, `/api/projects` lists exactly `remote` and
  `hubspot-v2`, and the page surfaces the `greenhouse-4` published bundle — matching
  what the doc promises.
- `viewer.html` over `file://`: does not navigate, shows the start-the-Studio message.
  Served by the Studio: 302 → `/studio`, and `?version=remote` → `/project/remote`.
- `artifacts/published/greenhouse-4/index.html` over `file://`: renders with no server.
- Loud-failure paths: `PY=./nope/bin/python ./start-studio.sh` → exit 1 with venv
  setup instructions; `PY=/usr/bin/python3 ./start-studio.sh` → exit 1 naming
  "Python 3.9.6" and the 3.12 requirement. Neither starts a server.
- Missing-screenshots path against a temp `--runs-dir`, both with an explicit
  `--version v001` and with auto-versioning: exit 1, clear message, **no run directory
  created**.
- Maintainer environment untouched: `venv/` (3.14.6) was neither modified nor deleted,
  and `./venv/bin/python -m pytest tests/ -q` passes there.

No expensive model or authoring stage was run. Framework generation was not invoked and
the ungated override was not used.
