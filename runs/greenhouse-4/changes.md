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
