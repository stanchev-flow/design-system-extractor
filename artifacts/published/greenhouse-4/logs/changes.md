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
