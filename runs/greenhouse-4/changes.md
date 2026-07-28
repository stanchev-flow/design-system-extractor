# runs/greenhouse-4 — change log

Fresh MULTI-PAGE Greenhouse brand extraction under **brand-signal composition**
(token skin / no shadcn defaults). Does **not** clobber `runs/greenhouse` or
`runs/greenhouse-v2`.

## 2026-07-28 — fresh extraction + framework lane

### Intent
Re-extract from existing captures (screenshots + HTML/CSS), rebuild harness +
replica, then add an **opt-in framework lane** (token skin; Radix only if interactive
chrome needs it — not required here).

### Source captures
`screenshots/greenhouse-4` → symlink to `screenshots/greenhouse-v2`:
1. home (primary / replica target)
2. talent-sourcing
3. compare

### Pipeline
- Archived mistaken v2-facts copy → `runs/greenhouse-4/_archive/brand-copied-from-v2-*`
- Per-page evidence: mine-dom/css/motion, measure, slice, curate (`extract_pages.sh evidence`)
- Vision ground all crops (`extract_pages.sh ground`) — home 6 + talent 11 + compare 9
- Merged → canonical evidence (`evidence/merge_pages.py`); hoverRules trimmed to 50;
  canonical grounding held to 11 docs (author foundation ≤180KB)
- Authored staged DAG (foundation → copy-chrome → patterns-recipes → media → projections);
  repair stalled on non-JSON response (same class as v2)
- Fact-gated contract completion (`evidence/fix_contract.py` + `fix_contract2.py` +
  brand.yaml chrome sync) → **C1–C28: 0 errors / 14 warnings**
- G3 harness + catalog rebuilt; components-preview → harness
- G4 replica: **overall 0.8206**, primary viewport health **1.0** @1440
- Opt-in framework lane: `brand/framework/index.html` (Vite single-file, brand tokens,
  native SiteNav/SiteFooter — **no Radix**, **no shadcn-as-shipped**). Registered in
  `runs/.studio/framework-builds.json`. Config: `runs/.studio/greenhouse-4.config.yaml`

### Studio
- Project title **Greenhouse 4** — http://127.0.0.1:1500/project/greenhouse-4
- Lanes: source, harness, replica, framework (token skin)

### Known follow-ups
- Replica still below 0.90 bar (multi-page pairing ceiling; sec-1/featureGrid ~0.20)
- Framework LLM invents some mid-page stats/copy vs measured 25%/39%/92% — skin/tokens
  are brand-owned; copy fidelity is a prompt follow-up
- C25 signatures remain prose-only warnings

### 2026-07-28 — framework empty-page fix
Root cause: curation `assets-manifest.json` was copied as `brand-assets.json` (no `byRole`),
so React crashed on `byRole['hero']`. Rebuilt `byRole` from media-assets + local URLs,
hardened `assets.ts`, synced Greenhouse `@theme` tokens, republished `framework/index.html`.

### 2026-07-28 — homepage stats / asset misuse
**Cause:** multi-page author union put talent-sourcing `stats` + compare `testimonial` into
`brand.yaml`; homepage replica composed ALL layouts; framework LLM also invented a stats
band and used slot-rank (`heroMedia`/`featureMedia`/`logoWall`) which assigns assets by
role/type/aspect — not by measured home bindings.

**Fix:**
- `compose_replica.py --page home` (auto from source-shot path): skip off-page patterns;
  sort remaining by provenance section index.
- Framework `App.tsx`: home anatomy only (no stats/testimonials); explicit hero pick;
  no featureMedia roulette.
- Replica HTML order now: hero → logoWall → featureGrid → cta (stats/testimonial skipped).

### 2026-07-28 — harness breadth, page lanes, measured asset binding

**Cause:** the harness only ever held the 6 LLM-authored patterns while grounding
described 23 content bands, page membership was inferred by parsing provenance
strings, and slot art was pooled across every band a pattern recurred in.

**Pipeline / tooling**
- `tools/extract/project_sections_to_patterns.py`: censuses grounded bands,
  authors the uncovered ones, dedupes recurrences, reconciles copy only when the
  heading proves it came from another band, and stamps `sourcePages[]` on every
  layout and pattern. Coverage 6/23 → 23/23 (17 composed patterns).
- `tools/extract/bind_media_assets.py`: binds one representative band's art per
  pattern (not the union), prefers VISIBLE placements over hidden responsive
  twins, and fills content-typed card runs.
- `tools/extract/validate_brand_evidence.py`: C4 accepts an item-level `body` as
  the quote alias, matching the payload-level alias it already had.

**Composer / renderer**
- `compose_section.py`: `.avif` joins the image inventory (curated AVIF art was
  invisible and its slots rendered as placeholder plates); a hero media block
  that resolved to no src drops the collage instead of drawing an empty plate.
- `compose_from_composition.py`: a card run declares its device by contract or by
  `card-list`/`card-media`/`media-well` role words when it carries art, and
  authored words no longer erase per-card media bindings read off the slot.
- `render_components_preview.py`: a layout whose archetype is descriptive rather
  than renderer vocabulary goes through the adapter (it used to fall through to
  the hero composer, which invented hero+overlap photography).
- `compose_replica.py`: page lane reads the declared `sourcePages` contract;
  `--source-shot` inference matches the brand's own declared pages.

**Framework lane**
- The generator states which chrome modules exist on disk; the prompt forbids
  importing a chrome file that was never written (the vite build failure).
- `build_framework_lane.py` appends `brand-chrome.yaml` when no live chrome
  contract exists, so nav/footer links are measured rather than invented.

**Verification**
- `validate_brand_evidence.py --brand-dir runs/greenhouse-4/brand` → PASS
  (0 errors, 15 warnings).
- `render_components_preview` → 17 patterns listed, 17 composed, gate green.
- `compose_replica --source-shot screenshots/greenhouse-4/home/home-fullpage.png`
  → 5 home sections, score 0.582 → 0.744; stats/testimonial no longer composed.
- `pytest brand_pipeline/tests` → 2066 passed, 3 pre-existing node-driven
  failures (AS-75/AS-77 fixtures, round-glyph audit) confirmed failing on a
  stash of these edits.

**Known follow-ups**
- Framework page still invents a stats band and testimonials: the page-lane
  contract exists in data (`sourcePages`) but is not yet fed to the generator.
- Framework copy carries literal `\u2019` escapes; BrandMark renders "Brand"
  instead of the measured wordmark.
- 18 curated assets remain `unplaced` (never observed rendering at 1440).

### 2026-07-28 — fact-gate the title-over-media pull (leaked WoodWave hero offset)

**Cause:** `component_render.component_vars()` declared
`title_overlap="-2.75rem"` as its signature default and emitted
`--c-title-overlap` unconditionally, while `compose_page.section_vars()` never
passed the argument at all. `-2.75rem` is one brand's measured
`overlapRules.offsets.titleOverMediaTop` (`experiments/woodwave-ab/inputs/brand.yaml`,
layout `opening-bookend`, `~-2.75rem`), so on the full-page/replica lane EVERY
section of EVERY brand inherited that brand's straddle magnitude via
`SCAFFOLD_HERO_CSS`'s `.cs-title { margin-bottom: var(--c-title-overlap) }`.
Greenhouse's `hero` layout declares no `overlapRules` at all (archetype
`centered-copy-with-floating-media`), yet its display title was pulled 44px down
over the mint media band's top edge — a device its source homepage does not have.
The single-section lane (`compose_section.build_document`) already read the fact,
so the defect was page-lane only and invisible to single-section previews.

**Fix (mechanic-level, brand-agnostic):**
- `component_render.py`: `title_overlap` default is now `None` and
  `--c-title-overlap` is emitted ONLY when the layout carries the offset fact
  (same absence-emits-nothing discipline as the aspect palette / deleted
  `_MOTION_DEFAULTS`).
- `compose_section.py`: new shared reader `title_overlap_offset(layout)` is the
  single source of the fact for both lanes; `SCAFFOLD_HERO_CSS` resolves
  `var(--c-title-overlap, 0rem)`, so a fact-less layout has no pull by
  construction instead of needing a negating class.
- `compose_page.py`: `section_vars()` takes `title_overlap` and the section build
  passes `cs.title_overlap_offset(layout)`; chrome/banner/footer scopes pass None.
- `wildcard_generator.py`: the hero ladder's `calc()` crank reads the same
  `0rem` fallback.
No brand or section named anywhere; no post-processing rewrite.

**Verification**
- Replica hero at 1440: `.cs-title` margin-bottom `-44px` → `0px`; collage top
  266.5px (inside the title box, bottom 310.5px) → 310.5px (flush below it).
- `compose_replica --source-shot screenshots/greenhouse-4/home/home-fullpage.png`
  → 5 sections, score 0.744, 8 punch-list entries (unchanged from pre-fix run).
- `render_components_preview` → 17 patterns listed, 17 composed, gate green.
- `validate_brand_evidence.py --brand-dir runs/greenhouse-4/brand` → PASS
  (0 errors, 15 warnings).
- `pytest brand_pipeline/tests -q` → 2073 passed (the 3 node-driven AS-75/AS-77 /
  round-glyph failures did not reproduce on this run); includes the new
  `test_fid10_lane_parity.TitleOverMediaGateTest` (4 cases) that locks the gate:
  declaring layout keeps its measured pull on BOTH lanes, fact-less layout gets
  none on either, and the scaffold carries the `0rem` fallback.
- WoodWave regression check: `compose_page experiments/woodwave-ab/inputs/brand.yaml`
  still emits `--c-title-overlap: -2.75rem`, now scoped to `#sec-0` only (1
  occurrence, was repeated on every section scope) — its overlap survives because
  its FACTS declare it.
- Viewer regenerated.

**Known follow-ups**
- Remaining hero fidelity gap (separate from the overlap): the source paints the
  mint band full-bleed from the nav's bottom edge with the copy centered INSIDE
  it, while the replica renders the band as an in-flow media block below the
  title on the white page surface. That is a surface-banding / media-placement
  fact, not the title pull.

### 2026-07-28 — framework page lane

**Cause:** the framework generator received `brand.md` + the union `brand.yaml`, so
it had no way to tell which bands belong to the homepage. It composed a plausible
SaaS outline (invented stats band, testimonial wall), bound no measured art, and
fell back to the literal word "Brand" for the wordmark.

**Fix**
- `tools/page_lane_brief.py` (new): renders ONE captured page's measured section
  inventory as prompt facts — order, copy, type registers, the `sectionAssets()`
  band call, and one `assetById("<file>")` line per image the section shows. The
  lane is a filter over the `sourcePages` contract, not a guess.
- `build_framework_lane.py` appends the `home` lane brief to the generation brief.
- `website-gen-framework-prompt.md`: a per-page inventory is the whole body;
  render one image per named file; copy is UTF-8 (a `\uXXXX` escape renders
  literally in JSX text, which is what shipped before).
- `handoff/scaffold/.../brand/assets.ts`: `assetById` accepts an id OR a filename
  (the brand artifacts name assets by file), and the bundle's new `brand` block
  exposes the brand name + chrome wordmark URL.
- `tools/build_brand_assets.py`: carries `brand.name` and `assets/nav-logo.svg`
  into the bundle.
- `handoff/scaffold/.../chrome/BrandMark.tsx`: falls back to the BRAND's name
  instead of "Brand", and accepts `className` (generated code passed one, which
  failed typecheck and silently dropped the nav mark styling).

**Verification** (`http://127.0.0.1:1500/runs/greenhouse-4/brand/framework/index.html`)
- 5 body sections — exactly the measured home lane; no stats band, no testimonials.
- 13 images, 0 broken: hero media cluster, 3 dark product cards, 6 client logos,
  3 feature-card images.
- 0 `\uXXXX` escapes; nav reads "Greenhouse"; `h1` on the 70px display register.
- `npx tsc --noEmit` on the generated app: clean.
- `validate_brand_evidence` PASS (0 errors, 15 warnings);
  `pytest brand_pipeline/tests` 2069 passed.

**Known follow-ups**
- Framework hero is a centered stack; the source hero is copy-left / media-right.
- Hero action pair renders one link where the source shows two buttons.
- The brand's own wordmark was never curated as an asset (no `navbar.logo` fact),
  so the nav renders the brand name as text.

## 2026-07-28 — published as a tracked bundle (browsable without this run dir)

This run dir is 325 MB and `runs/` is gitignored, so nothing here reached anyone
else. The FINAL results are now exported to a tracked, self-contained bundle that
the Studio serves as-is.

**Where**
- `artifacts/published/greenhouse-4/` — 19.4 MB, committed
- Studio: `http://127.0.0.1:1500/artifacts/published/greenhouse-4/index.html`
  (also listed on the Studio dashboard and in the greenhouse-4 build links)

**What's in it**
- `replica/` composed replica + `replica-report.md` (overall **0.7437**) + diff strips
  + `replica-fullpage.png`
- `harness/` components/layout harness + all 18 layout pattern pages
- `catalog/` component catalog
- `framework/` the built React+Vite single-file app (rebuilt from
  `brand/framework/single/framework-claude`; byte-identical to the 17:12 build)
- `brand/` 12 authored fact files (brand.yaml/md, layout-library, section-copy,
  media-assets, brand-chrome, style-scale, voice, assets-manifest, asset-placements…)
- `logs/` every run log + `manifest.json` + this changelog
- `assets/` ONE deduped copy of the 65 media files the pages actually reference
- `index.html` / `README.md` landing page with previews; `published.json` manifest
- deliberately excluded: source captures, per-page crops, `evidence/`, the framework
  app source + `node_modules`, and the 960/375/1920 replica shots (all stay here)

**How to regenerate**
    ./venv/bin/python tools/publish_run_bundle.py --run runs/greenhouse-4 \
        --base-url http://127.0.0.1:1500

**Verification**
- 22/22 pages loaded over the Studio (`verify.json`): landing, replica, harness,
  catalog, framework + 18 layout pages — 0 broken images, 0 4xx, 0 console errors
- framework build renders content (3215 chars of text, 13 images, 0 broken) — the
  earlier blank-page failure mode is not present
- no run-absolute `/runs/greenhouse-4/...` reference survives in the bundle
- `git check-ignore` over every bundle file: nothing ignored

## 2026-07-28 — the published bundle now states this run's real gate outcome

The bundle previously showed a fidelity number and nothing else, so a reader had no way
to know the run was never green. `tools/publish_run_bundle.py` now derives the run's
status from disk and renders it above the artifact links on the landing page, mirrors it
into `README.md`, and records it structurally in `published.json` (`status`).

**What it says for this run** (verdict `not-passed`)
- no `brand/flow-report.json` exists, so the flow never reached the end of its gate spine
- the last flow run crashed at gate **G3 (harness)**: `render_components_preview failed
  (exit 1) — harness quality failed` (`logs/flow-g3g4.log`)
- replica fidelity **0.7437** against this run's **0.90** bar — below the bar
- weakest bands named: `featureGrid 0.2783`, `testimonial 0.3088`, `hero 0.7719`
- the manifest's `status: completed` / `pipeline_run_completed: true` and its `0.8206`
  score are contradicted by the evidence above and must not be trusted over the report
  beside the page (`manifest.json` itself was left untouched — it is the record of what
  happened; a separate change fixes the code that writes it)
- `harness/harness-quality.json` reports `ok=true`, but it post-dates the flow log, so it
  reflects a later rebuild rather than a passing flow run

**Cross-brand scan** (new, report-only) — 38 matches in 19 files, none in visible content:
21 are developer CSS comments in composed pages naming other brands ("HubSpot-era",
"Remote's landscape aspect") emitted by the composer/harness renderers — generator-side
fix, not an export fix; 11 are the legitimate `…-remote-logo.avif` customer logo; 5 are
provenance mentions in `logs/changes.md` and the `fieldnote-design-system` package name in
`logs/framework-vite.log`. The framework `<title>` is still normalised on relocation.

**Verification** — 22/22 pages over `file://` and 22/22 over the Studio after the change
(the landing page is now checked last, so its own lane previews exist when it is loaded).

## 2026-07-28 — cross-brand commentary out of emitted output; scaffold brand defaults; C30

The report-only scan above found 21 cross-brand references emitted by our own renderers
into shipped CSS comments. They are gone from every rendered page in this bundle. Fixed at
the renderer, comment text only — **no CSS value, selector or markup changed anywhere**.

**Emitted comment sites rewritten brand-agnostically** (all were genuine engineering
context, so the mechanic was kept and the run-specific anecdote dropped):
- `compose_section.py` interlock mobile recrop — a plain landscape ratio coinciding with
  some brand's measured aspect does not make it brand-derived
- `compose_section.py` overlay bleed canvas — "never as an unconditional viewport-height
  default" (was a named brand's era)
- `compose_section.py` overlay panel display step — the 0.6 step is described as a
  QUANTIZING ratio (an unrounded multiplier lands between measured type rungs); the two
  brands' pixel arithmetic that motivated it is no longer shipped
- `compose_section.py` testimonial pull-quote glyph — round rem values in a device clamp
  coincide with some brands' spacing rungs without deriving from them
- `compose_section.py` section-padding rhythm note — the AS-24 reason (an unwrapped
  literal `var()` fallback reads as one brand's value inside another's page) with the
  work-phase label removed
- `compose_page.py` page section min-height — "never as an unconditional full-frame default"
- `render_components_preview.py` NON-STRETCH stage alignment, measured button families,
  buttons-on-surfaces band chrome — the last now states the general rule: an on-inverse
  muted ink carries the hue of the surface it was measured against
- `css_fidelity.py` fidelity-report heading — "Known acceptance divergences (recurring
  source-vs-replica gaps)"; the listed properties were already generic
- `framework_generator.py` emitted `@theme` alias comment — "the scaffold ui components'
  own token names"

**Scaffold brand defaults, fixed generator-side** (`handoff/scaffold/framework-site/`)
- `package.json` + `package-lock.json` name → `design-system-scaffold`; description no
  longer names a past extraction. Chosen NEUTRAL rather than brand-templated: the package
  name is never visible in the built single-file page, and package.json must stay in step
  with the committed lock or `npm ci` refuses to run.
- `index.html` `<title>` → `Design system scaffold`, and `scaffold_framework_project()`
  now stamps `"<Brand> — design system"` from `brand-assets.json` (`brand.name`), falling
  back to the lane's `brand.yaml`. No brand facts ⇒ the neutral placeholder stays, so an
  unstamped run is unbranded rather than mis-branded.
- The exporter's `<title>` normalisation in `publish_run_bundle.py` was KEPT: it still
  guards already-generated runs, and the lane titles it writes ("… — composed replica")
  describe the page's role in the bundle, which the generators have no reason to know.

**C30 cross-brand leak check** (`tools/extract/validate_brand_evidence.py`) — fails when a
generated artifact names a brand belonging to a different run. Vocabulary is derived from
the lane names under `runs/` plus one documented fallback list (runs/ is git-ignored, so a
fresh clone would otherwise derive nothing). Scoped to three regions that can never
legitimately name another company: renderer-emitted comments, the generated `<title>`, and
the generated npm package name/description. Visible page copy and data files are NOT
scanned — a logo wall, testimonial or asset id names real customers on purpose, so
`…-remote-logo.avif` and `alt="Remote"` must not fire. Brand names that are ordinary
English words only count as proper nouns, possessives or with a provenance suffix
(`remote-fix`), which is why this harness's own "diagonal-hatch plate" and "hatch
fallback" comments stay clean.

**Verification**
- harness + 17 layout pages re-rendered, replica re-composed (`--skip-shoot --skip-ladder`):
  the only diff versus the previously published pages is the comment text and the
  exporter's `<title>`; `harness-quality.json` and `tokens.manifest.json` byte-identical
- bundle re-exported: **0 `page` findings** in the export's own cross-brand scan (the 21
  remaining matches are the legitimate customer logo and provenance mentions in
  `logs/`), 22/22 pages verified over `file://`
- C30 on this lane: 33 → 11 errors, all 11 inside `framework/` — the stale pre-fix
  framework build. Framework generation is gated for this run and was not re-run; the
  ungated override was not used. `framework/index.html` still carries one scaffold HTML
  comment naming a past brand's typeface. It clears when the lane is rebuilt.

**Left in place, deliberately**
- `handoff/scaffold/framework-site/src/index.css` base layer sets `font-stretch: 87.5%`
  (body) and `82%` (h1–h3), tuned for a past brand's SemiCondensed typeface and applied
  unconditionally to every generated app. That is a brand-specific VALUE, not commentary,
  so it was not changed; the comment beside it now says so explicitly.
- `handoff/scaffold/framework-site/index.html` still hardcodes one Google Fonts link for a
  past brand's typeface. Same reason, and webfont handling is being reviewed separately.
- `handoff/scaffold/framework-site/src/brand/brand-assets.json` is a past brand's asset
  manifest. It is overwritten per run when the lane passes one, so it only leaks if a run
  scaffolds without a manifest.

## 2026-07-28 — this run becomes visible in a clean clone

### Intent
`runs/` is git-ignored, so cloning the repo gave you a Studio with nothing real in it.
Rather than publish a preview site, track the **subset of this run that the Studio
actually reads** — in place, via `.gitignore` negations, with no second copy of the data.

### New: `tools/track_studio_subset.py`
Generic over projects (no brand name appears in it). Given `--run runs/<project>` it
classifies every file in the run against an include list mirroring what
`studio_server.py` opens, prints the size before doing anything, and can then write the
`.gitignore` negations (`--write-gitignore`) and stage the paths (`--stage`). Both are
idempotent, so re-running after this run regenerates artifacts adds what appeared and
drops what vanished. `tests/test_track_studio_subset.py` pins the two rules that fail
quietly: `*` must not cross a separator (or `*/single/**` re-admits the framework build
tree), and a negation must open every parent directory before naming a file.

### What this run now ships, and what it does not
Tracked, **39.1 MB** total: `studio-project.json`, `manifest.json`, this changelog,
`brand/brand.yaml`, `brand/brand.md`, `brand/catalog/`, `brand/compose/replica/`,
`brand/harness/` (index + 17 layout pages + their media), `runs/.studio/greenhouse-4.config.yaml`,
and 3 full-page source captures (6.2 MB) reached through the `screenshots/greenhouse-4`
symlink — the link and `screenshots/greenhouse-v2/*/*-fullpage.png` are both tracked,
because git will not add a path that traverses a symlink.

Held back, **262 MB**:

| bytes | why |
| --- | --- |
| 144.2 MB | `brand/framework/` — Vite build tree; the Studio links framework builds by port, not by file |
| 94.5 MB | `_archive/` — archived copy of an earlier run |
| 17.7 MB | `screenshots/**/[page]_files/` — "Save Page As" mirrors of the original site |
| 15.3 MB | `brand/evidence/` — extraction evidence; never served |
| 11.9 MB | `brand/assets/` — harvested pool; each lane carries the copy its page references |
| 2.6 MB | `brand/compose/replica/diff/` — per-page crops, only a last-resort Source fallback |
| 12.5 KB | `replica-report.{json,md}` — embed this checkout's absolute path (see below) |

12.1 MB of the tracked subset is media duplicated between the replica and harness lanes.
It stays: each page references `assets/<name>` relative to itself, so dropping a copy
silently breaks that lane's images.

### Absolute-path exposure
`brand/compose/replica/replica-report.json` and `.md` record
`/Users/<user>/…/screenshots/greenhouse-v2/home/home-fullpage.png` as the compared source.
The tool refuses to track any text artifact containing this checkout's absolute path, so
both are excluded; nothing reads them from the Studio. They would need the capture path
rewritten repo-relative to be trackable. Nothing key-shaped was found anywhere in the
tracked set (scanned for `sk-`/`sk-ant-`, `AKIA`, `gh[pousr]_`, `AIza`, PEM private-key
headers and `key|secret|token|password =` assignments).

### `runs/.studio/`
Only `greenhouse-4.config.yaml` is tracked (3 lines: the framework/vanilla lane toggles
the server merges over `config-anthropic.yaml`). The rest of that directory is left
ignored: 14 job `*.log` files, a `capture_woodwave.py` scratch script, and
`framework-builds.json`, which registers builds at `http://localhost:517x/` and
`http://127.0.0.1:1500/…` — dead links in anyone else's clone, and the server re-seeds it
when absent.

### Known gaps in a clean clone (same as locally)
- **Docs tab is empty.** `project_detail()` reads them from `runs/<project>/<item>/single/`;
  this run's outputs live under `brand/`, and it has no run-item `single/` directory.
- **Assets tab is empty.** It reads `runs/<project>/assets/assets-manifest.json`; this run
  wrote `brand/assets-manifest.json` instead.
- **No framework lane.** `has_site` globs `*/single/site-*.html`, one level above this
  run's `brand/framework/single/`, so the Studio never offered the lane anyway.

## 2026-07-28 — the Studio shows a brand-lane run

Closes the three "known gaps" recorded above, which were all one root cause: the
Studio was written against the older `screenshot_to_template` lane and read
`runs/<project>/<item>/single/`. A brand-lane run never creates that directory, so
`first_item_dir()` returned `None`, all thirteen document lookups returned `""`,
and `availableDocs` filtered every tab away.

### Brand-lane documents are their own tab set (`studio_server.py`)
A new `BRAND_DOCS` registry sits ALONGSIDE the old `DOCS` list rather than
replacing it, so an old-lane project is untouched. Each entry names the brand
artifact that now carries what the old document carried:

| tab | reads | present in |
| --- | --- | --- |
| Structural evidence | `brand/evidence/{dom-sections,css-facts,computed-styles,motion-audit}.json` | greenhouse-4, remote, hubspot-v2 |
| Grounding | `brand/evidence/grounding/*.yaml` (11 / 19 / 12 files) | greenhouse-4, remote, hubspot-v2 |
| Ledger | `brand/style-scale.yaml` | greenhouse-4, remote, hubspot-v2 |
| Contract audit | `brand/contract-projection-audit.json` | greenhouse-4 only |
| Sections | `brand/layout-library.yaml` + `brand/section-copy.yaml` | all four lanes |
| Validation | `validate-final.log`, else `brand/validation-report.md` | greenhouse-4, hubspot-v2 |
| Author report | `brand/author-report.json` + `brand/author-stage-status.json` | greenhouse-4 only |
| Replica fidelity | `brand/compose/replica/replica-report.md` | greenhouse-4, remote, hubspot-v2 |
| Voice | `brand/voice.md` + `brand/voice-facts.yaml` | all four lanes |
| Changelog | `changes.md`, else `brand/changes.md` | greenhouse-4, remote, hubspot-v2 |

Mechanics worth knowing:

- `groups` is a tuple of ALTERNATE GROUPS: every group contributes a file, and
  within a group the first pattern that resolves wins. That is what lets one entry
  concatenate several files while still tolerating a lane that puts its changelog
  at the run root instead of under `brand/`.
- Every backing file is emitted under a `===== <path> =====` header, so a
  multi-file tab reads as one document and a single-file tab still says which of
  the alternates it found.
- A zero-byte file counts as absent, so availability and content always agree —
  no tab can render blank.
- `supersedes` names the old-lane `docs` key an entry stands in for. When a project
  has both (an old-lane run that later grew a `brand/` dir, e.g. `runs/woodwave`)
  the original wins and the successor is dropped, so no label appears twice.
- Bodies are NOT embedded in the project payload; the tab row is metadata only and
  the body is fetched from a new `/api/rundoc?version=&doc=` endpoint, the same way
  `brand.yaml` / `brand.md` already load. Structural evidence alone is 147 KB for
  this run, and 162 KB for hubspot-v2.

Deliberately NOT wired: no "design system" document is synthesized from parts
(`brand.yaml` / `brand.md` already have their own tabs), `brand/catalog/catalog.json`
is left to the existing Catalog tab rather than duplicated into Sections, and the
old `Contract`, `Generation input` and `Prompts` tabs have no brand-lane equivalent
to show.

### Assets counter and gallery (`studio_server.py`)
`load_assets()` read only `runs/<project>/assets/assets-manifest.json` with the old
`total_logical_assets` / `assets[]` keys, so this run reported `Assets (0)`. It now
tries that manifest first (old-lane behaviour byte for byte) and falls back to the
brand lane's `brand/assets-manifest.json` (`assets-curation.v1`, an `entries[]`
array). Real counts: greenhouse-4 **68**, hubspot-v2 66, remote 34.

Each entry maps to the gallery as: group by `tagGuess` (present on 100% of entries
in all three lanes); badge = the authored `assetSemantics.kind` from
`brand/media-assets.yaml` when it binds that file, else `unbound` — which surfaces
the 65-of-68 binding gap instead of hiding it; `url` resolves `dest` against
`brand/assets/` and then every `brand/compose/*/assets/` directory, because the
curation pool is not in the committed subset while the lane copies are.

Also fixed a latent bug this made reachable: the gallery's inline
`onerror="…innerHTML='<span class=\'…\'>load failed</span>'"` needed a quote nested
four deep (Python → JS template literal → HTML attribute → JS string) and lost a
backslash, so the handler was a syntax error. A failed image rendered as a blank
tile plus a console error instead of a caption. Replaced with a named
`imgFailed(el, cls)` function; no nested quoting.

### Dashboard thumbnail (`studio_server.py`)
`project_meta()` looked for a run-item `screenshot.*` and then a ROOT-LEVEL image in
`screenshots/<project>/`. A modern capture has only per-page subdirectories, so
neither matched and the card said "no preview" — while the project page's Source
pane worked, because `resolve_source_image()` does handle them. `project_meta()` now
falls back to that same resolver. For this run the capture folder is a SYMLINK
(`screenshots/greenhouse-4` → `screenshots/greenhouse-v2`) and the resolver maps the
target back under the project dir, so the card renders
`/screenshots/greenhouse-v2/home/home-fullpage.png`. Across the dashboard this took
"no preview" from 29 cards down to 3, and those 3 are prompt-version folders
(`v178`, `style-calibration`, `claude-distillation`) with no capture at all.

### `/project/<unknown>` returns 404 (`studio_server.py`)
It used to answer 200 with a fully rendered page, so a link pasted from a machine
with more runs than yours produced a plausible-looking project whose every pane was
empty. It now returns a real 404 naming the missing version and listing the projects
this checkout does have. The check is `run_dir_for()`, which keys off the run
DIRECTORY, never off how much is in it — a project with almost nothing generated
still renders — and doubles as the traversal guard for the new `/api/rundoc`.

### Replica report records the compared source repo-relative (`compose_replica.py`)
The absolute-path exposure noted above is fixed at the source: `report_path()`
writes a path inside the repo relative to the repo root
(`screenshots/greenhouse-v2/home/home-fullpage.png`) and leaves a genuinely external
path alone. One field, `meta.sourceShot`, feeds both the `.json` and the `.md`.

Existing stored reports are deliberately NOT migrated — the next re-score
regenerates them. Verified with the tracker's own `leaks_local_path()` gate: freshly
written reports pass, the stored ones still fail. **16 of the 20** existing
`replica-report.{json,md}` files across 8 projects carry the absolute path, and in
every one of them it is this single field, so a re-score unblocks all 16 for
tracking. (The larger held-back counts for `woodwave`/`remote` come from other
producers — `onbrand-report.md`, `composition.json`, `css-diff.json`, battery
reports — which this change does not touch.)

### Verification
- `tests/test_studio_brand_pages.py` grew from 8 to 40 tests (brand-doc resolution,
  alternates, dedupe-vs-old-lane, both manifest shapes, thumbnail incl. the symlink
  case, `run_dir_for`). New `tests/test_studio_http_routes.py` (12) runs a real
  server on an ephemeral port for the 404 and `/api/rundoc`. New
  `tests/test_compose_replica_report_path.py` (6). `tests/` is 195 passed / 0 failed.
- Headless Chromium against a Studio on port 1577 (NOT 1500): greenhouse-4 shows 15
  tabs, remote 12, hubspot-v2 13, and old-lane `runs/greenhouse` still shows its
  original 15 — no tab has an empty body, and there are no console errors on any of
  them. All 68 greenhouse-4 and 34 remote asset images load; 6 of hubspot-v2's 66 do
  not, and now say "load failed" — they are DOM-harvested inline `<svg>` fragments
  written without an `xmlns` attribute (`brand/assets/logo-inline-0[2-7].svg`), which
  no browser will render as a standalone image. That is a defect in that run's
  harvested data, not in the Studio, and is left alone.

### Still open
- `brand/evidence/`, `brand/style-scale.yaml`, `brand/layout-library.yaml`,
  `brand/section-copy.yaml`, `brand/author-report.json`,
  `brand/contract-projection-audit.json` and `validate-final.log` are not in the
  committed subset, so on a CLEAN CLONE those tabs are correctly absent rather than
  broken. Closing that needs include rules in `tools/track_studio_subset.py` plus a
  regenerated `.gitignore` block; both were owned by another agent during this
  change and were left untouched.

### Clean-clone result (verified against a fresh `--depth 1` clone of `main`)
The clone carries 11 projects, and the tab row is data-driven, so it degrades by
project rather than breaking:

| project | in the clone | vs local |
| --- | --- | --- |
| `remote` | 12 tabs, Assets (34), all 34 images load | identical |
| `hubspot-v2` | 13 tabs, Assets (66) | identical |
| `greenhouse-4` | 6 tabs — `Changelog` is its only brand doc, Assets (0) | loses 9 tabs |
| `greenhouse` (old lane) | 14 tabs, Assets (39) | no brand tabs either way |
| `woodwave` (hybrid) | 16 tabs, all old-lane | loses `Sections`, `Voice` |

Zero console errors and no empty tab body on any of them, and all 11 dashboard
cards render a thumbnail (`greenhouse-4`'s through the capture symlink). The gap
is entirely about what is tracked: `remote` and `hubspot-v2` ship their
`brand/evidence/`, `style-scale.yaml`, `layout-library.yaml`, `assets-manifest.json`
and `media-assets.yaml`; `greenhouse-4`'s subset does not, so those tabs are
correctly ABSENT rather than blank. Closing that needs include rules in
`tools/track_studio_subset.py` and a regenerated `.gitignore` block — both owned by
another agent during this change, so they were left untouched.

## 2026-07-28 — every brand lane is now a real project in a clone

The mechanism above is applied to the rest of the brand lanes. A clone now
carries **eleven** Studio projects instead of `greenhouse-4` plus two half-empty
legacy folders, and a headless walk of every project page and every lane in a
fresh clone of `origin/main` is **identical to the same walk against the author's
own Studio** — same lane counts, same catalogs, same tabs, same failures.

### The set
Brand lanes only. `greenhouse`, `greenhouse-4`, `greenhouse-v2`, `hubspot`,
`hubspot-v2`, `hubspot-v3`, `hubspot-v4`, `relume-test`, `remote`, `woodwave`,
`woodwave-v2`. Deliberately out: the experiment lanes (`hubspot-sol`,
`hubspot-sol-clean-v2`, `style-calibration`, `claude-distillation`) and the
pipeline version folders (`v170`–`v178`, `v200`–`v202-hatch`, `v300`/`v301-mine`).
They still list on the dashboard from a local checkout; in a clone they are
absent, which is correct.

### Size

| project | tracked subset | new bytes |
| --- | --- | --- |
| `greenhouse` | 12.0 MB | 12.0 MB |
| `greenhouse-4` | 34.5 MB | 0.7 MB |
| `greenhouse-v2` | 59.6 MB | 53.4 MB |
| `hubspot` | 19.0 MB | 19.0 MB |
| `hubspot-v2` | 68.0 MB | 9.9 MB |
| `hubspot-v3` | 21.9 MB | 21.9 MB |
| `hubspot-v4` | 13.2 MB | 13.2 MB |
| `relume-test` | 14.4 MB | 14.4 MB |
| `remote` | 49.3 MB | 5.4 MB |
| `woodwave` | 124.8 MB | 124.8 MB |
| `woodwave-v2` | 18.1 MB | 19.2 MB |
| **total** | **434.9 MB** | **293 MB** |

`hubspot-v2` and `remote` cost so little because 248 MB of them was already
tracked from before the ignore rule; what they were missing was the catalog, the
source capture and a handful of lane assets. `woodwave` is the outlier and it is
not fat with waste — it is ten composed page lanes, each carrying the media its
own page references. Git stores identical blobs once, so the 293 MB of new files
is **162 MB of distinct content** in history; the rest is the working-tree cost
of lane-relative asset copies. Clone measured at **2.5 GB** (867 MB of it `.git`).

### Two tracking rules earned their keep

**Only images something shows.** A lane directory accumulates the page at several
viewport widths, contact sheets, before/after pairs and re-shoots. The Studio
displays exactly ONE of them (`_lane_thumb()`) and the pages load their media
from `assets/`. Images now survive only if a tracked page references them by
name, or they are the lane's thumbnail — mirroring `_lane_thumb()`'s own scoring
so the pick always matches what the Studio will ask for. That took the set from
560 MB to 435 MB, `hubspot-v3` alone from 45.8 MB to 19.2 MB.

**Whatever a tracked page loads gets tracked.** Lanes borrow across runs —
`runs/relume-test/brand/compose/03 WoodWave/index.html` renders from
`runs/woodwave-v2/brand/assets/`, a pool the rules exclude — and no static include
list predicts that. The references win: `rescue_references()` pulls in 13 such
files, and `--check` reports any local reference from a tracked page that would
still 404 in a clone. The only two it still reports are files that do not exist
on the author's disk either.

### Five runs had no Studio identity
`greenhouse-v2`, `hubspot-v2`, `hubspot-v3`, `hubspot-v4` and `woodwave-v2` had no
`studio-project.json`, so they listed with a raw directory name and no link back
to the site they came from. `--register` writes one, deriving the title and url
from the run's own `manifest.json` or `brand/brand.yaml` — never inventing either.

### The greenhouse card
`screenshots/greenhouse-v2/` is a per-page capture, which `project_meta()` cannot
thumbnail, so `greenhouse-4` and `greenhouse-v2` both showed "no preview" — in a
clone AND locally. A 293 KB card poster cropped from that capture's own home page
now sits at the capture root, which is the shape the resolver already looks for.
Both cards render, and all eleven now have a real thumbnail.

### Clean-clone verification
Fresh `git clone` of `origin/main` into `/tmp`, venv on 3.14, Studio on port 1577,
headless Chromium over the dashboard, all eleven project pages, and all 111 lanes
they advertise, recording every request that 404'd or failed. The identical walk
was run against the author's Studio on 1500 for comparison.

- dashboard: 11 cards, every thumbnail 200, zero failed requests
- every project page: zero failed requests
- Source pane resolves for all ten projects that have a capture (`relume-test` is
  a wireframe lane and has none, locally too)
- catalogs, document tabs, asset counts and lane counts match local exactly

Failures, all of which reproduce identically against the author's own Studio:

| what | why |
| --- | --- |
| `brand/chrome/index.html` 404 on 8 projects | `static_lanes()` always offers the lane and lets it 404; only `hubspot`, `remote`, `woodwave` ever generated one |
| "Framework build" links to `localhost:5179`–`5182` | `_DEFAULT_FRAMEWORK_BUILDS`, a hardcoded seed of dev-server ports; they are labelled external and are dead on any machine that is not running those servers |
| `greenhouse-4`'s framework link | points into `brand/framework/`, a 144 MB Vite build tree that is deliberately not tracked |
| `hubspot`'s `signup-launch-tokenized` 404s 3 images | the generated HTML contains `src="{'src': 'assets/….webp'}"` — a Python dict repr that leaked into the template at generation time |

### Held back for embedding this checkout's absolute path
237 files, 2.8 MB, across all eleven lanes. Consequences a teammate sees: no
Author report tab on `greenhouse-v2`/`hubspot-v3`/`hubspot-v4`, no Replica
fidelity tab on `greenhouse-4`/`greenhouse-v2`/`hubspot-v4`/`woodwave-v2`, and no
Changelog tab on `relume-test`. `compose_replica.py` now writes that field
repo-relative, so re-scoring unblocks the replica reports; `author-stage-status.json`,
`composition.json`, `onbrand-report.md` and the battery `report.json`s need the
same treatment at their producers. Secret scan over the whole tracked set
(`sk-`/`sk-ant-`, `AKIA`, `gh[pous]_`, bearer tokens, `key|secret|token|password =`):
one hit, the words "token-provenance" in a fidelity report. Nothing key-shaped.

### Running it for the next project

    ./venv/bin/python tools/track_studio_subset.py --run runs/<project> \
        --register --check --write-gitignore --stage

`--write-gitignore` regenerates the whole managed block from the plans it was
given, so pass **every** tracked project, not just the new one. Staging skips any
tracked path with uncommitted edits rather than committing someone else's
in-progress work, and prints what it skipped.
