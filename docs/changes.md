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

### `pip install -e .` dirtied a fresh clone

Caught on the origin clone: `src/screenshot_to_template.egg-info/` is tracked, and
setuptools rewrites it during the documented install step, so a teammate's very first
`git status` after following the instructions shows three modified files.

- `.gitignore`: `*.egg-info/` added, with a comment noting that the already-tracked
  copy still shows as modified until someone untracks it — a separate decision that was
  not made here.
- Documented as expected and harmless in `docs/getting-started.md`.
- Suggested follow-up for the maintainer:
  `git rm -r --cached src/screenshot_to_template.egg-info`.

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

## 2026-07-28 — The README points at the setup doc and states the real framework default

Closes the three follow-ups left open above, now that `README.md` is no longer being
edited by another agent. Documentation and git bookkeeping only: no config value, no
prompt, and no runtime behaviour changed.

### The setup doc was unreachable from the README

A new contributor lands on `README.md`, and nothing there led to
`docs/getting-started.md`. Two one-line pointers, no duplicated instructions:

- The intro blockquote now says to start at `docs/getting-started.md` to get a clone
  installed and running.
- `## Quick Start` opens by sending a new clone to that doc — Python 3.12+,
  dependencies, Playwright browsers, API keys — and states that the commands below
  assume the install is done. The Quick Start had always assumed `./venv/` existed
  without ever saying where it comes from.

### `README.md` claimed framework generation is on by default. It is off.

Verified before writing, not taken on trust: `load_config()` returns
`framework_generation_enabled=False` with no `--config`, and `True` for
`config-anthropic.yaml`; `FrameworkDefaultOff` passes.

- The heading "Framework site generation (React + Tailwind v4) — **default**" is now
  "— **opt-in on the CLI**".
- The section's opening claim, previously "**Framework-first** is on by default", now
  reads: *"Framework generation is off in the CLI baseline and on in the Studio.
  `config.default.yaml` — always loaded first — sets `framework-generation-enabled:
  false`, because brand compose (token CSS + static HTML) is the canonical CLI path;
  `--framework-sites` is the per-run opt-in. The Studio needs no flag: its base config
  `config-anthropic.yaml` sets the key to `true` because the Studio's path is
  framework-first."* The vanilla-skip behaviour is unchanged and now stated as
  conditional on framework generation being on, which is what `run_pipeline.py`'s
  `skip_vanilla_html` actually computes.
- The defaults line (was `framework-generation-enabled: true`) states `false`, names the
  test that pins it, says Studio project configs are *written* with `true` into
  `runs/.studio/{version}.config.yaml` by `make_run_config()` rather than "inheriting the
  same" as `config.default.yaml`, and disposes of the apparent contradiction of
  `AppConfig`'s `True` dataclass default.

### Two more stale claims found next to it, both fixed

Both are demonstrably wrong against the files they describe, not judgement calls:

1. The first run recipe in that code block was commented "Full pipeline (framework
   only; vanilla skipped unless `--vanilla-sites`)" but passed no flags — with the
   baseline default it builds no framework sites at all. It now passes
   `--framework-sites`, and the separate "force framework on a run that disabled it"
   recipe was folded into it, since with the real default those are the same command.
   The "also generate vanilla" recipe passed `--vanilla-sites` alone, which yields
   vanilla *only*; it now passes both flags to match its own description.
2. `## Local Changes` said `config-anthropic.yaml` routes to
   `anthropic/claude-opus-4-1-20250805`. The file says `claude-opus-4-8`. Corrected, and
   the entry now also mentions that the file turns framework generation on and is the
   Studio's base config.

Nothing else in the README makes a claim about a default value: `provider: openai` /
`model: gpt-5.5`, `site-asset-generation-enabled`, `surface-map-mode: contract` and
`vanilla-site-generation-enabled: false` all check out against
`config.default.yaml` and `config-anthropic.yaml` as loaded.

### `src/screenshot_to_template.egg-info/` is untracked

`git rm -r --cached src/screenshot_to_template.egg-info` — six files removed from the
index, all six still on disk. `*.egg-info/` was already in `.gitignore`, and
`git check-ignore -v` confirms line 18 of `.gitignore` is what catches them, so the
directory `pip install -e .` rewrites no longer appears in `git status` at all.

- `.gitignore`: the comment no longer tells the reader to expect a dirty tree and to
  `git checkout --` the directory; it records that the tracked copy was untracked and
  that a fresh clone now stays clean through install.
- `docs/getting-started.md`: the "`git status` dirty right after install" row in the
  symptom table said this was expected and harmless. It now says it should not happen,
  and that anything dirty is the reader's own change.

### Verification

```
./venv/bin/python -c "load_config().framework_generation_enabled"   # False
./venv/bin/python -c "load_config('config-anthropic.yaml')…"        # True
./venv/bin/python -m pytest brand_pipeline/tests/test_brand_signal_composition.py \
  -k FrameworkDefaultOff -q                                        # 1 passed
git check-ignore -v src/screenshot_to_template.egg-info/PKG-INFO    # .gitignore:18
```

Staged file-by-file — `README.md`, `.gitignore`, `docs/getting-started.md`,
`docs/changes.md` and the six index deletions — because other agents have uncommitted
work in `brand_pipeline/compose_replica.py`, `studio_server.py`, `tests/` and
`runs/hubspot-v2/` in this tree. None of it was staged. No secrets in the diff; no key,
token, or URL was added.

## 2026-07-28 — A run says which site-generation lanes it took, and why it skipped the rest

The README fix above exposed the real defect behind it. The flagless recipe built zero
framework sites because `config.default.yaml` sets `framework-generation-enabled:
false`, and **nothing in the run said so** — not the console, not `manifest.json`. The
lane simply produced no file and the run reported success. Same silence for
`vanilla-site-generation-enabled`. This is the repo's recurring failure class (a
component declines to do its job while the layer above reports success), so it is fixed
the same way the manifest/gate work was: derive the facts from what actually happened,
and state them.

The defaults are unchanged. `framework-generation-enabled: false` stays false, and
`FrameworkDefaultOff` still pins it. This is a disclosure fix, not a behaviour flip.

### The lanes, and how each is gated

`run_pipeline.py` is the only entry point with site-generation lanes (the brand flow in
`brand_pipeline/pipeline_flow.py` already discloses G1–G5 through `flow-report.json`).
There are two, each gated independently:

| lane | artifacts | gates |
|---|---|---|
| framework sites | `site-{claude,gpt55}-framework.html` | `framework-generation-enabled` OR `--framework-sites`; membership in `site-generation-providers.txt`; `--design-only` / `--surface-map-only`; then the fail-closed brand-lane gate (G1–G4) inside `generate_framework_site` |
| vanilla one-shot HTML | `site-{claude,gemini,gpt55}.html` | `run_pipeline`'s `skip_vanilla_html`, i.e. skipped when `--sites-only --framework-sites`, or when framework generation is on and `vanilla-site-generation-enabled` is false; plus the same provider list and mode flags |

Worth recording because it is not what the key names suggest:
`vanilla-site-generation-enabled: false` does **not** switch the vanilla lane off. It
only suppresses vanilla while framework generation is on. With the CLI baseline
(framework off) the vanilla lane runs regardless of its own key — which is why the
flagless recipe still produced HTML and looked successful. The disclosure says this in
those words rather than implying the key was honoured.

### `src/screenshot_to_template/lane_disclosure.py` (new)

Owns the vocabulary and the derivation, and is unit-testable without a model call:

- `plan_site_generation_lanes()` resolves both lanes' gate state once, before any model
  work, mirroring `run_pipeline`'s own `framework_generation_enabled` /
  `skip_vanilla_html` expressions so the disclosure cannot drift from the decision.
- `LaneLedger` records one outcome per lane × provider × run item and **derives** the
  lane-level outcome from those records. A lane can only claim it produced output if a
  target reported a file it wrote; nothing is hand-authored.
- Outcomes are kept distinct because the reader's next action differs: `produced`,
  `skipped_disabled` (a switch), `skipped_not_requested` (provider list / mode),
  `skipped_no_input` (`--sites-only` with nothing saved to rebuild from),
  `skipped_gate` (the fail-closed G1–G4 refusal), `failed`, and `not_reached` for a lane
  an earlier crash never got to.
- The same rows render the console summary and the manifest payload, so the log and
  `manifest.json` cannot disagree.

### What a user now sees

Up front, before any model work, and again at the end. For the documented default
invocation (`./venv/bin/python run_pipeline.py --screenshots-dir … --version …`):

```
Site generation lane summary:
  framework sites (React + Tailwind v4) — SKIPPED — disabled in config
      framework-generation-enabled is false in the resolved config (config.default.yaml
      is the always-loaded CLI baseline) — set framework-generation-enabled: true in a
      --config override or pass --framework-sites
      nothing built for provider(s): claude, gpt55
  vanilla one-shot HTML — PRODUCED (1 file(s))
      wrote hatch/single/site-claude.html
```

A skipped-because-disabled lane names its config key **and** the flag that would enable
it, so the reader can act without opening source.

### The manifest

`manifest.json` gains `site_generation_lanes` (schema `site-generation-lanes.v1`) on
both the full and `--sites-only` paths: `mode`, `expectsSiteOutput`,
`producedOutputCount` / `producedAnyOutput`, and per lane `configKey`, `enableFlag`,
`configValue`, `enabled`, `outcome`, `outcomeReason`, `outputs`, `unbuiltProviders` and
the individual `targets`. Every field is derived from the recorded targets, following
the existing pattern where the flow derives `status` / `pipeline_run_completed` /
`generationAllowed` / `blockedGate` from real gate outcomes.

### A run that produces no site output now fails

Two guards, and both are scoped so they cannot break an invocation that never intended
to generate a site — `--design-only`, `--surface-map-only` and `--assets-only` are
exempt by construction (`expects_site_output=False`, or an early return before the
plan):

1. **Up front**, before any model work: if no lane is enabled, the run refuses and
   prints each lane's reason. Today the interlock makes this unreachable (vanilla is
   only suppressed while framework is on, and `parse_provider_list` never returns
   empty), which a truth-table test pins. It is here because that interlock is
   incidental: the moment someone makes `skip_vanilla_html` honour
   `vanilla-site-generation-enabled` directly — the reading the key name invites —
   both-false becomes a silently empty run. This turns that into a refusal.
2. **At the end**: if no lane produced a single file, the run exits non-zero after
   printing the summary and writing the manifest. This one is reachable today.
   `--sites-only` against a run with no saved design-system input skipped every item and
   still logged "Done! Site outputs refreshed", and a run where every provider errored
   wrote error-page HTML and exited 0. Both now exit 1 with the lane summary explaining
   which lane failed and why. `studio_server.py` already marks a non-zero pipeline exit
   as an errored job, so the Studio degrades correctly rather than reporting a green run
   with no site.

### Also fixed while in there

A framework gate refusal was being retried like a transient error, logged as "framework
retry after error", and recorded as a failure. Retrying cannot change a lane's gate
state, so `gen_framework_site` now breaks on the first refusal and discloses it as
`skipped_gate` rather than `failed`. `framework_generator.generation_blocked_error()` is
the new lazy accessor for that exception class, so a caller can tell a refusal from a
failure without importing the orchestrator.

### Verification

```
./venv/bin/python -m pytest tests/ -q                     # 221 passed
./venv/bin/python -m pytest brand_pipeline/tests -q        # 2214 passed, 9 failed
./venv/bin/python run_pipeline.py --sites-only --version v-lane-smoke \
  --screenshots-dir /tmp/… --runs-dir /tmp/…               # exit 1 + full disclosure
```

`tests/test_lane_disclosure.py` (23 tests + a 16-case truth table) covers the plan for
every flag/key combination, the derivation precedence, the exact user-facing strings for
a skipped-because-disabled lane, summary/manifest agreement, and that
`--design-only`-style runs are never failed for producing no site.

The 9 `brand_pipeline` failures are pre-existing and unrelated — Playwright
connection errors in `test_fix3_containment_alignment.py`, `test_fix4_inline_svg.py` and
`test_fix5_gallery_defects.py`, confirmed identical with this change stashed.

`viewer.html` regenerated per `AGENTS.md` (it reads `manifest["screenshots"]`, which is
untouched, so its layout is unchanged).

### Silent-success paths noticed and NOT fixed

Recorded rather than fixed, to keep this change to one thing:

- `process_single_mode`'s outer `except` writes error-page HTML into
  `site-claude.html` / `site-gemini.html` / `site-gpt55.html`, so a failed item leaves
  files that look like output to anything globbing for site HTML. It is now disclosed
  (the lane reports `not_reached` and the run exits non-zero), but the placeholder
  content is still indistinguishable from a real page by filename alone.
- `apply_site_assets` swallows every asset-generation exception into a single
  `asset generation ERROR` log line and returns `None`; the run's status is unaffected
  and no artifact records the failure.
- The surface/component map falls back to the deterministic draft on any synthesis
  error (`surface/component map synthesis fell back to deterministic draft`), which is
  logged but not recorded in the manifest, so a run whose map was never model-authored
  cannot be told apart afterwards.
- `parse_provider_list` silently drops `gemini` (it is in
  `DISABLED_SITE_GENERATION_PROVIDERS`) and falls back to `["gpt55"]` for an
  otherwise-empty list, so a version folder asking for `gemini` gets GPT-5.5 with no
  warning.

Staged file-by-file — `run_pipeline.py`,
`src/screenshot_to_template/framework_generator.py`,
`src/screenshot_to_template/lane_disclosure.py`, `tests/test_lane_disclosure.py`,
`README.md` and `docs/changes.md` — because other agents have uncommitted work in
`brand_pipeline/compose_replica.py`, `studio_server.py`, `tools/track_studio_subset.py`,
`runs/hubspot-v2/` and `evals/matrix/runs/` in this tree. None of it was staged. No
secrets in the diff; no key, token, or URL was added.

## 2026-07-29 — A run builds the lane it was asked for, or says it did not

Three of the silent-success paths the lane-disclosure work above catalogued. All three
are the same shape: a component declines to do what it was asked, and the layer above
reports success. Each is fixed by making the component's own decision reachable to the
reader, and each outcome goes through the existing `LaneLedger`, so the console summary,
`manifest.json` and now `run-steps.json` cannot disagree.

### `vanilla-site-generation-enabled: false` now switches the vanilla lane off

`run_pipeline.py` computed
`skip_vanilla_html = (framework_sites and sites_only) or (framework_generation_enabled and not vanilla_site_generation_enabled)`.
The key therefore only suppressed the vanilla lane **while framework generation was on**.
Under the CLI baseline — `config.default.yaml` sets `framework-generation-enabled:
false` — the vanilla lane ran regardless of what its own key said, which is why a
flagless recipe still emitted HTML and looked successful. The second clause is now just
`not vanilla_site_generation_enabled`, mirrored in
`lane_disclosure.plan_site_generation_lanes`.

This is a deliberate behaviour change, and it makes the up-front refusal reachable:
each key governs its own lane, so both false is a run with no enabled lane, which is
exactly what the guard added above refuses. **Verified end-to-end, not assumed** — a
flagless `run_pipeline.py --screenshots-dir … --version …` against a temp `--runs-dir`
now prints both lanes' reasons and exits 1 before any model work, and the same run with
`--vanilla-sites` reports `vanilla one-shot HTML — ENABLED; will build
site-claude.html` and proceeds.

What depends on the old behaviour, checked before changing:

| config | framework | vanilla | effect of this change |
|---|---|---|---|
| `config.default.yaml` (CLI baseline) | false | false | **changed** — a flagless run is refused instead of emitting vanilla HTML |
| `config-anthropic.yaml` (Studio base) | true | false | none — framework on, vanilla skipped, as before |
| `runs/.studio/{greenhouse,greenhouse-4,woodwave}.config.yaml` | true | false | none |
| `studio_server.make_run_config()` (every new Studio project) | true | false | none |

Every config in the repo that sets `vanilla-site-generation-enabled: false` also sets
`framework-generation-enabled: true`, except the CLI baseline. So no Studio project and
no tracked run config loses output or newly hard-fails; the only changed invocation is
the flagless CLI one, which is the invocation the change is about.
`studio_server.framework_first_mode()` (`fw and not vanilla`) is unaffected.

The 16-case truth table in `tests/test_lane_disclosure.py` no longer asserts the
interlock. It now asserts the reachability: each lane is enabled exactly when its own
key or flag says so, and "no lane enabled" is exactly the all-false corner.
`README.md`'s description of the key was accurate as a config value and misleading
about behaviour; it now states that each key switches off its own lane and that the
shipped baseline therefore enables neither.

### A failed generation no longer writes a page

`gen_site`, `gen_framework_site` and `process_single_mode`'s outer `except` all wrote
error-page HTML into the real `site-*.html` names, so a failed item left files that
anything globbing for site HTML read as genuine output. Three new module-level helpers
in `run_pipeline.py` replace that:

- `write_site_failure_artifacts()` writes the error text to
  `site-{provider}.error.html` and a machine-readable
  `site-{provider}.failure.json` (schema `site-generation-failure.v1`: lane, provider,
  stage, expected output, error, timestamp), and leaves **nothing** at the real name.
  A failure is now distinguishable by filename alone, with no HTML parsing.
- Any file already at the real name is removed, because it is not this run's output
  either — leaving a previous run's page in place would move the ambiguity rather than
  remove it. The old code destroyed that file too, by overwriting it.
- `clear_site_failure_artifacts()` drops a stale marker, called from `record_lane` on
  `produced` and from `write_site_skipped_output`, so a later success can never be
  misread as the earlier failure.

`is_generated_site_html()` consults the marker before the markup, and gained
`<h1>framework error</h1>` — the framework variant of the placeholder was not in its
marker list, so a framework error page counted as generated output. No such file exists
on disk, so nothing was actually misclassified; the gap was latent and is now closed.

Also fixed, because leaving it would have shipped a contradiction: after the generator
pool, `run-steps.json` marked `site_generation_{provider}` **completed** for every
submitted provider, including ones that had just failed and written an error page. That
is visible in `runs/v171`, where two items record `site_generation_gemini: completed`
next to a 503/499 error page. Step status is now derived from the lane target's recorded
outcome (`LaneLedger.outcome_for()` + a total `LANE_OUTCOME_STEP_STATUS` map), so the
third surface agrees with the other two.

### A retired provider is disclosed, and never substituted

`parse_provider_list` dropped `gemini` silently and fell back to `["gpt55"]` for an
otherwise-empty list, so a version folder asking for `gemini` got GPT-5.5 with no
warning. `gemini` is genuinely retired, not vestigial: `generate_website_html` raises
"Gemini site generation is disabled for future pipeline runs." for it, and
`ALLOWED_SITE_GENERATION_PROVIDERS` is `("claude", "gpt55")`. (The `GoogleProvider`
class stays — it is still used for analysis and image work. Only site generation is
retired.)

`resolve_provider_list()` now returns a `ProviderSelection` carrying both what will be
built and what was dropped:

- A retired provider alongside supported ones is still dropped — old version folders
  keep working — but it is **reported**: the run logs "Retired site generation
  provider(s) requested and NOT built: gemini", and its lane target's reason says it is
  named in the file but retired, instead of the previous "not in this run's
  `site-generation-providers.txt`", which would have sent the reader to edit a file that
  already said what they meant.
- A list that resolves to nothing is **refused**. Substituting `gpt55` would let a run
  claim it compared what its own config named. Refusing covers both the retired-only
  case and a file that names no provider at all.

`parse_provider_list` stays as the list-returning wrapper for existing callers.

### Forensics: did any run silently get GPT-5.5 instead of Gemini?

**No.** Read-only check; no run data was modified, re-run, or cleaned up.

Exactly two run folders name `gemini` in `site-generation-providers.txt` — `runs/v170`
and `runs/v171` — and both genuinely ran Gemini. `token-usage.jsonl` in every item of
both records `site_generation_gemini | google | gemini-3.1-pro-preview`; `run-steps.json`
records the step; and the outputs are 25–55 KB pages with `site-gemini.assets.json`
sidecars. The `["gpt55"]` fallback could not have fired for either: both files also name
`claude` and `gpt55`, so the parsed list was never empty. Independent confirmation that
neither was re-run after `gemini` was retired: `run_pipeline` rewrites
`site-generation-providers.txt` with the parsed list on every run, and both files still
say `gemini`.

Everything else checked, all clear:

- `v172`–`v178`, `v200-hatch`–`v202-hatch`, `v300-mine`, `v301-mine`, `greenhouse`,
  `woodwave`: `claude gpt55` or `claude`. No gemini.
- `hubspot-sol`, `hubspot-sol-clean-v2`, `style-calibration`, `claude-distillation`,
  and the other brand lanes (`greenhouse-4`, `greenhouse-v2`, `hubspot`, `hubspot-v2`,
  `hubspot-v3`, `hubspot-v4`, `relume-test`, `remote`, `woodwave-v2`) have no
  `site-generation-providers.txt` at all, so they used
  `DEFAULT_SITE_GENERATION_PROVIDERS = ("claude",)` and never requested gemini.
- `evals/matrix/runs/` holds one round (`2026-07-14-baseline`) and no provider list.

So no recorded comparison in this repo compared something other than what it claimed.
One thing that is *not* a substitution but reads like one in the logs: the gemini lane's
`site_style_sync_gemini` step runs on `openai/gpt-5.5`. Style sync is a separate model
by design; the site generator itself was Gemini.

### Forensics: has any scoring or eval path been consuming error-page HTML?

**No.** No score recorded in this repo was computed over an error page.

- `evaluate_site_match()` is the only thing that scores site HTML, and its only caller
  is `tools/run_design_system_prompt_bakeoff.py`, which raises on
  `not html_document_is_complete(html)` before scoring. There are **zero**
  `site-*-review.json` artifacts anywhere under `runs/`, so it has not produced a score
  in this repo at all. `tools/generate_version_scoreboard.py` reads those same
  non-existent files.
- The eval matrix (`tools/run_eval_matrix.py`, `evals/matrix/`) runs its gate battery on
  `runs/<brand>/brand/compose/<brief>/index.html`. It never opens `site-*.html`. Neither
  does `tools/publish_run_bundle.py`, nor anything in `brand_pipeline/`.
- What the masquerade *did* affect is display and publishing, not scoring: the Studio's
  `site_rel()` picked the file on existence alone and served an error page as the lane
  preview, the viewer embedded it as the lane's output, and
  `tools/track_studio_subset.py`'s `*/single/**` rule copied it into the published
  subset. All three now see no file, and the `.failure.json` travels with the subset.

The error pages currently on disk, for the record: `runs/v171/.../site-gemini.html` for
`2025-12-19_88524-function-100-healthy-years` (Gemini 503) and `2026-02-20_bradford`
(Gemini 499), and all three vanilla providers in `runs/v200-hatch/hatch/single/`
(missing `OPENAI_API_KEY`) and `runs/v202-hatch/hatch/single/` (empty design-system
synthesis). Left exactly as they are.

### Verification

```
./venv/bin/python -m pytest tests/ -q                      # 356 passed
./venv/bin/python -m pytest brand_pipeline/tests -q        # see below
./venv/bin/python run_pipeline.py --screenshots-dir /tmp/… --runs-dir /tmp/…
                                                           # exit 1, no lane enabled
./venv/bin/python run_pipeline.py … --vanilla-sites --sites-only
                                                           # vanilla ENABLED, exit 1 (no input)
```

`tests/test_site_output_honesty.py` (new, 12 tests) covers the failure artifacts, the
marker beating the markup, the legacy framework error page, an offline `--sites-only`
run whose generator raises (real page absent, `.error.html` and `.failure.json` written,
lane target `failed`, exit 1), the retired-provider reason reaching the manifest, and
the shipped defaults refusing the run. `tests/test_lane_disclosure.py` gained the
rewritten truth table, the two vanilla-key cases, `outcome_for()` and the step-status
map. `tests/test_design_system_review.py` and `tests/test_runtime_defaults.py` swap the
old `parse_provider_list("gemini\n") == ["gpt55"]` assertions for the refusal.

`brand_pipeline/tests` currently fails well above the 9 Playwright errors this repo has
been quoting, because other agents have uncommitted work across twelve
`brand_pipeline/` modules in this tree, and consecutive whole-suite runs disagree with
each other (32 failed / 15 errors, then 17) as those files change mid-run. So the
comparison was made against a fixed subset instead of a moving total: the ten failing
files were run with `run_pipeline.py` and `lane_disclosure.py` reverted to `HEAD`, and
again with this change applied. Both runs: **13 failed, 170 passed, 4 errors** —
identical. None of those tests import `run_pipeline` or `lane_disclosure` either. This
change adds no `brand_pipeline` failure.

`viewer.html` regenerated per `AGENTS.md`; its content is unchanged, because the stub
bakes in no default version and nothing here alters `manifest["screenshots"]`.

Staged file-by-file — `run_pipeline.py`,
`src/screenshot_to_template/lane_disclosure.py`, `tests/test_lane_disclosure.py`,
`tests/test_site_output_honesty.py`, `tests/test_design_system_review.py`,
`tests/test_runtime_defaults.py`, `README.md` and `docs/changes.md` — because other
agents have uncommitted work in `brand_pipeline/`, `studio_server.py`, `tools/extract/`,
`tools/track_studio_subset.py`, `tests/test_studio_http_routes.py`,
`src/screenshot_to_template/{site_assets,source_colors,source_style_ledger}.py`,
`run_brand_extraction.py`, `runs/hubspot-v2/` and `evals/matrix/runs/` in this tree.
None of it was staged, and `git commit` was given explicit paths. No secrets in the
diff; no key, token, or URL was added.

## 2026-07-29 — Eleven projects, checked from a clone instead of from here

An independent walk of the teammate promise — clone `origin/main`, follow
`docs/getting-started.md`, start the Studio, see all eleven brand lanes — done in a
fresh clone at `/tmp`, never against this working tree. Every claim below came from
HTTP against the clone's own Studio on port 1599, plus Chromium for what actually
renders. Verified at `3a41077`.

### The install doc holds up; the clone step does not

`python3` on this machine is 3.9.6, so the doc's interpreter warning is not
hypothetical — it is the first thing a newcomer hits, and the doc catches it. From
there `python3.14 -m venv venv`, `pip install -e '.[dev]'`, `playwright install
chromium` all worked as written, `git status` was clean immediately after install, and
`tests/` came back **222 passed, 19 subtests, in 12.7 s** with no browser and no key.

The one step that does not work as written is the first one. **A plain `git clone`
failed twice**, at 5:12 and 2:32, with `RPC failed; curl 92 HTTP/2 stream 5 was not
closed cleanly: CANCEL` then `fatal: early EOF`, leaving no directory behind.
`--depth 1` failed identically, so shallow is not an escape hatch. `git -c
http.version=HTTP/1.1 clone` succeeded in 3:37 for the full 2.5 GB. Documented in
`docs/getting-started.md`, in the install block and in the troubleshooting table,
because a newcomer who hits this twice has no reason to suspect the transport.

### Browsing needs no API key

Started with no `.env.local`, and with `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`GOOGLE_API_KEY` and `GEMINI_API_KEY` all explicitly unset in the launching
environment. The dashboard, all eleven project pages, every document tab, every
generated lane and the published `greenhouse-4` bundle all served. No key prompt, no
degraded mode, nothing in the server log. **Nothing in the read path touches a
provider.** Keys are a generation concern only, which is what the doc claims.

### All eleven, over HTTP and in a browser

`/api/projects` in the clone returns exactly the eleven brand lanes and nothing else.
Every one: `/project/<v>` 200, dashboard card carrying a real image (4 KB–5.9 MB,
`image/*`), zero occurrences of "no preview" anywhere on the dashboard, and a live
asset count where the run produced one.

Crawled every lane, composed page, replica, harness, variant, static lane and
published bundle each project offers — 131 pages — and then fetched every local asset
each of them references, following linked CSS one level in. **Three broken references
in total**, all on one page (below). Chromium confirms it: zero failed requests and
zero console errors on ten of the eleven project pages.

`greenhouse` and `relume-test` carry no `brand.yaml`, no `brand.md`, no assets
manifest and no document tabs — but neither does this working tree. They are
single-lane projects that never ran brand extraction, so that is the run's shape, not
the clone's loss. Same for the "Exact nav/footer" lane, absent on eight of eleven:
`brand/chrome/index.html` does not exist locally either.

### What a teammate genuinely does not get

Compared file by file against this tree's `runs/` for the same eleven projects.
**Nothing exists in the clone that is not also here** — no phantom files. The
local-only mass is what the doc already says it is: `brand/framework/` builds
(~11,400 files per lane), `_archive/`, `captured page/*_files/` source mirrors,
`brand/kit/`, per-page crops, `__pycache__`.

Beyond that, the real teammate-visible gap is eight document tabs across seven
projects, listed exactly in `docs/getting-started.md`. That list was wrong before this
change in three ways: it claimed `hubspot-v3` and `hubspot-v4` have no Author report
(both do), it omitted `hubspot-v3` from the Replica fidelity list, and it omitted
`greenhouse-4` Validation and `relume-test` Changelog entirely. It also gave one
reason for all of them — that the backing file records an absolute path — which holds
only for `greenhouse-v2/brand/author-report.json` (49 occurrences) and
`runs/relume-test/changes.md` (1). The five missing replica reports and
`greenhouse-4/validate-final.log` contain none, so those are a size decision.

The project list itself differs — eleven here versus twenty-nine locally — but the
eighteen extra are the experiment and pipeline-version lanes the doc excludes on
purpose.

### Reported, not fixed

- **This checkout's absolute path in 317 tracked files** (128 under `runs/`, 189 under
  `experiments/`; none under `docs/`, `artifacts/` or the root HTML). Three reach a
  teammate's screen: **Structural evidence** and **Replica fidelity** on `hubspot-v2`,
  and **Replica fidelity** on `remote`, each rendering this machine's home directory
  as the source-screenshot path. Left alone: another agent has
  `src/screenshot_to_template/repo_paths.py`, `tests/test_producer_report_paths.py`
  and `tools/verify_clone_parity.py` uncommitted in this tree, which is this exact
  work, and a partial scrub would collide with it.
- **`hubspot` → "Composed: signup-launch-tokenized" renders three broken images.** The
  generator wrote a Python dict repr into the attribute —
  `src="assets/{'src': 'assets/ProductIcons_DataHub_Icon_Orange.webp'}"` — for the
  DataHub, SalesHub and SmartCRM icons. The real files are present and tracked; only
  the markup is wrong. The file is byte-identical here, so this is a generation defect
  every viewer sees, not a clone gap. Fixing it means re-running composition, and an
  uncommitted `tests/test_asset_binding_markup.py` in this tree suggests it is already
  claimed.
- **Two thumbnail URLs are emitted unencoded.** `hubspot` and `remote` have a literal
  space in the capture filename, and `/api/projects` returns it raw, so a strict HTTP
  client cannot request it. Browsers percent-encode on the way out, so both cards
  render — this is latent, not visible. The fix belongs in `studio_server.py`, which
  has ~310 uncommitted lines from another agent.
- **Five Replica fidelity tabs could be closed cheaply** (6–11 KB each, no local paths)
  but were left untouched: `runs/*/brand/compose/replica/` is being actively rewritten
  in this tree right now — the reports' mtimes moved during this session, and one
  file's path leak disappeared between two reads.

Only `docs/getting-started.md` was staged. `docs/changes.md` carries 205 uncommitted
lines from another agent, so this section is recorded here but deliberately not
committed with it. No secrets in the diff; no key, token or URL was added.

## 2026-07-29 — History rewritten: `experiments/` purged, checkout path scrubbed

**Every commit SHA in this repository changed on this date.** History was rewritten with
`git filter-repo` and force-pushed, so any SHA cited in this file or any other doc from
before 2026-07-29 no longer resolves — including `3a41077` above, and the `1932b5d`,
`9ed7860`, `c8e7b5f`, `c839b4b`, `64d41c8`, `3d6f84d` and `089a968` cited in the root
`changes.md`, `HANDOFF-2026-07-02.md` and `brand_pipeline/spec/convergence-loop.md`.
They are left as written rather than rewritten: the prose around them describes what
changed and why, which is still true, and inventing replacement SHAs would imply a
mapping that was never recorded. Read them as "an earlier commit", not as something to
`git show`. Anyone holding a clone from before this date has to re-clone; a pull will be
rejected as a non-fast-forward, which is the intended behaviour rather than a fault.

### Why

Two problems, one fix. `experiments/` was 1,977 tracked files and 981 MB packed — the
single largest thing in the repo, and the reason `.git` was 953 MB and a clone regularly
died mid-transfer. 189 of those files also embedded this checkout's absolute path, which
is a username this public repo does not publish. Untracking would have fixed neither:
the blobs stay in history and stay fetchable. The repo was about to be shared for the
first time and nobody held a clone yet, so the rewrite was cheap then and would only
have got more expensive.

### What the rewrite did

- Removed `experiments/` from all 99 commits (`--path experiments/ --invert-paths`).
- Replaced the author's home-directory prefix with `/Users/redacted` in every blob in
  every commit (`--replace-text`). The literal string is not repeated here, so that this
  file does not reintroduce what it documents. This scrub was needed on top of the
  purge: the leak was **not**
  confined to `experiments/`. 44 tracked files under `runs/hubspot-v2/` and
  `runs/remote/` carried it too, and one of them —
  `runs/hubspot-v2/brand/assets-manifest.json` — is a file the Studio's Assets tab
  reads, so deleting it was not an option. Scrubbing the string keeps every one of them
  working; all 35 JSON and every YAML file among them still parse.

Verified afterwards by streaming all 3,814 blobs in the rewritten history (587 MB of
content, reachable and unreachable alike) and searching each for the string: zero hits.
Checking the tip alone would not have been enough.

### Preserving woodwave's lanes

`woodwave` reached 28 of its variant lanes through 56 tracked symlinks into
`experiments/`, and a 29th — the anchored hero-variants page — was served straight from
`experiments/woodwave-hero-gallery/`, which the Studio degrades to an absent lane rather
than a 404, so losing it would have been silent.

All 29 were materialized as ordinary tracked files under `runs/` first, following the
rule `tools/track_studio_subset.py` already applies: each page plus the assets it
actually references, not the directory behind the symlink. That is 457 files and 51.7 MB
in the working tree, but only about 6.9 MB of distinct content, because the same fonts
and photographs recur across lanes and git stores each blob once. Shipping the
directories wholesale would have cost 74 MB for 22 MB of files nothing requests. None of
the 457 files contains the absolute path, so the leak was not relocated from
`experiments/` into `runs/`.

The hero page went under `brand/hero-gallery/` rather than `brand/variants/`, which the
Studio scans automatically — putting it there would have listed the lane twice and moved
woodwave's variant count off 42.

### Result

| | before | after |
|---|---|---|
| `.git` (fresh mirror) | 934 MB | 415 MB |
| clone `.git` | — | 417 MB |
| clone on disk | ~2.5 GB | ~1.1 GB |
| tracked files | 11,236 | 9,259 |
| tracked `runs/` files | 8,554 | 8,554 |

`runs/` came through the rewrite with a byte-identical path set. Against the
pre-materialization commit it is +429 / −28, and every one of those paths is inside the
lanes named above.

`experiments/` is now in `.gitignore` so it cannot be re-added by a stray `git add -A`,
while staying on disk where the variant lanes are produced.

### Left alone

`viewer-image.html` (25 MB, tracked) was **not** purged. It is the live output of
`run_image_pipeline.py --viewer-only`, which writes that exact path, and `README.md`
documents it, so it is a generated artifact of a working tool rather than dead weight.
It contains no local paths. Purging it would have cut the clone by a further 25 MB and
broken a documented entry point; if that trade is wanted it should be a deliberate
decision about whether the image-crop pipeline is still current.

The `backup/*` tags and the six `experiment/shadcn-*` branches were rewritten locally
but not published: `origin` has only ever had `main`, and a repo being shared for the
first time is not the place to publish six stale spikes as a side effect. The
pre-rewrite state is kept as a verified `git bundle` outside the working tree.
