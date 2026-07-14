# evals/matrix — changes (Stage B: steals gate wiring)

> Stage-B changelog for the quality-steals enforcement wiring (section-rules +
> conversion-structure gates). Stage A (contracts + corpus authoring) is logged in
> the root `changes.md` and the contracts' own changelog blocks. This file is the
> system of record for: wiring decisions, the lane × gate findings table, data
> fixes (with lane-changelog cross-refs), gate calibrations, and renderer-level
> follow-ups discovered by the new gates.

## 2026-07-14 — Stage B wiring (COMPLETE)

### Activation

- `brand_pipeline/tests/staged_test_quality_steals.py` → renamed into discovery
  as `brand_pipeline/tests/test_quality_steals.py` (the file's own prescribed
  route; assertions unchanged, header re-framed for stage B). 20 tests.
- Verified: `./venv/bin/python -m pytest brand_pipeline/tests/test_quality_steals.py -q`
  → **20 passed, exit 0**.

### New modules

- **`brand_pipeline/section_rules_audit.py`** — the section-scoped rule auditor
  (spec/section-rules.md enforcement shape). Detection table → per-family rules;
  STATIC layer (bs4 parse: word/sentence counts, anatomy-parity sets, shape-class
  parses, roster diffs, casing censuses) + GEOMETRY layer (Playwright @1440:
  rendered line counts via box-height/line-height, mark/icon box censuses,
  computed register sizes; `--static-only` skips it, its rules report skip).
  Checker code exists ONLY for `enforcement: new` rows (41), keyed by rule id;
  `delegated` rows (16) are reported with their `delegatedTo` law, never
  re-implemented; absent families emit skip rows, never silence. Lane scoping
  mirrors `spacing_audit`'s generative-lane law (composition.v1 OR briefed legacy
  composition); briefless replicas report the evidence-lane skip; specimen lanes
  skip page-scoped rules. OVERRIDE verdicts where measured facts outrank genre
  budgets (e.g. SR-NAV-03 under harvested chrome cites `navbar.primary`).
  Reports `report.json` + `report.md`; baseline exit 0; `--strict` exits 1 on
  failing `required` rows / lane errors. CLI mirrors the established auditors:
  `<lanes...> --brand <brand-dir> [--out DIR] [--strict] [--static-only]`.
- **`brand_pipeline/conversion_audit.py`** — the conversion-structure checker
  (spec/conversion-structure.md). Pure interpreter over the seven constraint
  kinds + depthBand + formDepth; `check_conversion_structure(composition,
  campaign, families=None, form_field_count=None)` is importable for the future
  composition-gate wiring. Family grounds: composition-level familyMap + bySlots
  (form-contract slot → capture-form; ≥2 stat slots → stat-band; `about` binds
  the grid family only when moduled), re-grounded post-render through the
  section-rules family detector (AUTHORITATIVE when index.html exists — e.g.
  stress-playbook's single `stat` slot renders a 4-stat band only the render
  ground sees). Campaign binding is fact-gated: `--campaign` > brief
  `campaignType:` frontmatter (copy-brief.md / brief.md) > composition
  `brief.campaignType`; unbound lanes skip with a note. ADVISORY-first wiring:
  all constraint rows WARN; the two hardFloor rows gate from birth (exit 1);
  `--strict` additionally gates `required` rows (the post-baseline graduation
  lever). Report `report.json`/`report.md` via `--out`.
- **Tests** — `brand_pipeline/tests/test_section_rules_audit.py` (86) +
  `brand_pipeline/tests/test_conversion_structure.py` (29): the file names the
  staged header prescribes. Fixture doctrine held: every `enforcement: new` rule
  has a failing synthetic-bad fixture (checker-level, synthetic HTML/geometry
  payloads — the signature-gate test pattern); real-lane green is spot-pinned on
  the event lane (static) and recorded here for the full battery.

### Wiring decisions (doctrine applied)

- Replica lanes are EVIDENCE: every section-rules row skips there by
  construction; the conversion checker skips unbound lanes (replicas declare no
  campaign). Result: neither gate can fire on a replica — the "gate must not
  flag the mirror of a real site" bar holds by scope, not by tuning.
- Chrome fact-parity (SR-NAV-01 / SR-FOOT-01) grounds on `.cs-navlinks` labels
  vs `navbar.primary[].label`, and `.c-foot-col` groups/`.c-foot-glyph` roster/
  legal line vs `footer.columns/social/legal` — the parity unit is the column
  GROUP (rendered cells legitimately pack multiple groups).
- Quote semantics: the substrate's attribution device (`.c-person` beside the
  quote paragraph — the bento-lead quote shape) counts as quote marking for
  SR-QUOTE-01/02; register-promoted quotes stay licensed (pass1 routing), the
  geometry check only fails a quote REACHING the page's display size.
- SR-HERO-05 proof rows exclude `.c-stat` devices (the stat register is ladder
  law — scale_adherence / SR-STAT-05 territory), so a stat-contract proof beat
  in a hero is never register-capped to body size.
- SR-STAT-01/02 shape grammar: values with a numeric magnitude + short unit word
  ("90 days", "6–12 months") classify INT-UNIT — genuine magnitudes (never
  "wordy"), censused apart from bare counts since "+" grammar can't apply.
- Prompt-side guidance injection (`generate_composition.build_prompt` projecting
  campaign grammar) is NOT wired: `generate_composition.py` is under the
  concurrency file fence. Recorded as follow-up.
- `onbrand_check.py` untouched: the staged tests do not require integration
  there; both gates are standalone battery members (the established pattern).
  `check_conversion_structure` is exposed as a pure function for that future
  wiring.
- Offline LLM judge (spec/conversion-structure.md): DESIGNED, NOT BUILT — not
  trivially cheap, per the spec's own build condition. Unchanged.

### Findings table (lane × gate, final state)

section-rules (SR) verdict = required fails / advisory warns; conversion (CS)
verdict = hardFloor / WARNs (advisory-first wiring; informational bindings are
gate-calibration runs on lanes that predate `campaignType:`).

| lane | SR verdict | SR findings | CS binding | CS verdict |
|---|---|---|---|---|
| hubspot-v2 hero: homepage | PASS 0/0 | — | none declared | skip (fact-gated) |
| hubspot-v2 hero: pricing | PASS 0/0 | — | none declared | skip |
| hubspot-v2 hero: product | PASS 0/0 | — | none declared | skip |
| hubspot-v2 hero: about | PASS 0/0 | — | none declared | skip |
| hubspot-v2 hero: blog | PASS 0/0 | — | none declared | skip |
| hubspot-v2 hero: demo | PASS 0/0 (was FAIL SR-HERO-01) | display heading 5 lines in the form-split half measure → **copy fixed** (below) | none declared | skip |
| hubspot-v2 hero: developer | PASS 0/0 | — | none declared | skip |
| hubspot-v2 hero: event | PASS 0/0 | pre-calibration SR-HERO-04 hit was the meta ROW (date·time·format), not a kicker → detection scoped | none declared | skip |
| hubspot-v2 replica | PASS (replica skip) | evidence lane by scope | none declared | skip |
| remote event-genlaunch | PASS 0/2 adv | SR-HERO-02 lede 5 lines (adv); SR-TIER-02 filled CTA on Virtual while Builder carries the inset-head emphasis — deliberate authored split (composition note), rule demoted (below) | webinar-event (explicit) | **PASS 0 hardFloor / 0 WARN** |
| remote stress-playbook | PASS 0/4 adv | SR-STAT-03 12–15w stat labels; SR-FORM-06 5w question label; SR-GRID-02 10w cell heading; SR-HERO-02 lede 5 lines — all authored stress-lane copy, advisory by design | leadgen-gated-content (informational) | PASS, 4 WARN: form at index 11 (required window firstN 3), proof 2 steps from form, depth 11 vs 4–6, form 7 fields vs 2–4 — honest diagnoses of a deliberately deep stress page |
| remote bakeoff-sol | PASS 0/3 adv | SR-FORM-01 8/8 required fields; SR-FORM-06 5–6w question labels; SR-CAR-02 2-frame edge-cut carousel | product-launch (informational) | PASS, 3 WARN: 6 feature-grids vs 1–3, depth 10 vs 5–9, form 8 fields vs 0–3 |
| remote bakeoff-opus | PASS 0/2 adv | SR-FORM-06 6w question label; SR-HERO-02 lede 5 lines | product-launch (informational) | PASS, 3 WARN: 5 feature-grids vs 1–3, depth 10 vs 5–9, form 6 fields vs 0–3 |
| remote replica | PASS (replica skip) | evidence lane by scope | none declared | skip |

No hardFloor violation anywhere; no gate fires on a replica. Bakeoff lanes are
frozen A/B eval artifacts — their advisory warns are recorded here, their data
deliberately untouched (changing eval-record copy would falsify the comparison).

### Data fixes (lane-local, with lane changelog cross-refs)

- **hubspot-v2 hero demo** (`runs/hubspot-v2/brand/compose/hero-archetypes/demo/composition.json`)
  — SR-HERO-01 (required) catch: display "See the customer platform work for
  your team." rendered 5 lines @1440 (80px display in the 500px form-split
  column; even the half-measure budget of 4 was exceeded). Copy tightened per
  the rule's remedy to "See the customer platform at work." (same claim,
  display-length). Re-rendered `--rerender --only demo` (no model calls),
  onbrand PASS; full battery re-run green (exit codes in Verification); gallery
  shots + contact sheet + lane index refreshed. Lane log:
  `runs/hubspot-v2/brand/compose/hero-archetypes/changes.md` (steals stage B).

### Gate calibrations (all recorded in contracts/section-rules.yaml changelog)

1. **Measure-aware wrap budgets** (SR-HDR-01 / SR-HERO-01 / SR-HERO-02): the
   authored line budgets describe FULL-measure boxes; a split/half-measure
   column (box < 720px at the 1440 tier) licenses ONE extra line — same ink,
   half the measure. Real-lane contradictions that proved it: bakeoff-sol split
   h2 at 3 lines/487px; stress hero display 4 lines/481px (licensed geometry,
   not copy defects). The demo's 5-line display still failed the licensed 4 —
   the rule kept its teeth.
2. **SR-TIER-02 demoted required → advisory** (staged-severity doctrine): the
   event-passes band deliberately splits the upsell highlight (Builder's
   sanctioned inset head band, per its composition note) from the conversion
   register (the free Virtual pass CTA — the brief's single action). A licensed
   pattern, not unambiguous dishonesty; still reported as WARN.
3. **faq detection scoped**: the disclosure-device selectors (`.cs-faq`,
   `details[name]`) bind the faq family only when the section does not declare
   a DIFFERENT content use — the event agenda (useCase `agenda`, accordion
   rows "16:00 UTC — The launch keynote") is IC-ACC/AS-40 disclosure law, not
   FAQ content law. SR-FAQ-01 keeps firing on statement triggers in true FAQ
   sections (synthetic fixture pinned).
4. **SR-HERO-04 kicker budget scoped to kickers**: a dot-separated logistics
   row riding the eyebrow register (the meta-forward archetype's meta row,
   e.g. "Oct 8, 2026 · 9:00 AM ET · Streamed live") audits as a proof/meta row
   (SR-HERO-05), never against the 5-word kicker cap.
5. **SR-STAT-01 "wordy" = no numeric magnitude** (implementation precision, not
   a budget change): unit-worded magnitudes classify INT-UNIT and pass; pure
   words ("Global", "Trusted") fail. The YAML's budget ("0 wordy values") is
   enforced verbatim.

### Renderer-level follow-ups (NOT touched — fence)

- **Prompt wiring**: ~~`generate_composition.build_prompt` does not yet project
  campaign grammar~~ — RESOLVED CONCURRENTLY: the parallel agent landed
  `brand_pipeline/conversion_structure.py` (guidance projection, opt-in
  `inject_conversion_guidance`, default OFF/byte-identical) + the
  `generate_composition.py` threading + `tools/run_eval_matrix.py` (which calls
  THIS stage's `section_rules_audit` / `conversion_audit` CLIs as the round
  battery) while this changelog was being finalized. Division of law holds:
  `conversion_structure.py` owns the prompt side, `conversion_audit.py` (this
  stage) stays the one checker — see spec/conversion-structure.md (their status
  note names both owners). No file was co-edited by both agents.
- **Bento lead stamping**: ~~the event-bento's lead cell (media+link anatomy)
  carries no `cs-bento-cell--lead` class — the auditor infers a de-facto lead
  (first cell, strict anatomy superset). A renderer stamp would make SR-GRID-01
  exact; inference documented in the module.~~ — **RESOLVED (fix7 2026-07-14)**:
  `compose_bento_grid` stamps the de-facto lead itself (first card whose
  authored anatomy strictly supersets the identical sibling set — the exact
  mirror of this auditor's inference), so SR-GRID-01 reads the renderer's own
  declaration on fresh renders; the inference stays as the fallback for
  pre-fix7 pages. Root log: repo `changes.md` (fix7).
- **Form-split display register**: ~~an 80px display on a ~500px half measure
  leaves ~10 chars/line — nearly any claim wraps past budget. A future
  register-step-down for form-split heroes (like pass1's overlay-panel 0.6
  re-registration) would fix the class; today the copy budget carries it.~~ —
  **RESOLVED (fix7 2026-07-14, punch item 5 / AS-66)**: deterministic
  fit-to-measure stepping — the display rung in a sub-measure column steps
  down the brand's MEASURED heading ladder until the hero cap (3 lines) fits
  (greedy word-wrap projection calibrated on THIS stage's measured 5-line /
  4-line wraps); the class/SR-budget stay display, the size re-registers via
  `data-fit-rung`, and slop AS-66 polices the stamped `data-fit-cap`. The demo
  display now renders 2 lines at the 48px h1 rung. SR-HERO-01 stays the
  copy-budget gate.
- **`hero-archetypes` gallery lane briefs** predate `campaignType:` — single-
  hero galleries have no campaign grammar to bind (honest skip), but future
  full-page campaign lanes should declare it in frontmatter.

### Verification (exact commands, true exit codes — `cmd > log 2>&1; echo exit=$?`)

```
./venv/bin/python -m pytest brand_pipeline/tests/test_quality_steals.py -q                 exit=0 (20 passed)
./venv/bin/python -m pytest brand_pipeline/tests/test_section_rules_audit.py -q            exit=0 (86 passed)
./venv/bin/python -m pytest brand_pipeline/tests/test_conversion_structure.py -q           exit=0 (29 passed)
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/pytest brand_pipeline/tests -q                  exit=0 (1259 passed, 0 failed)
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m brand_pipeline.section_rules_audit \
    <8 hero lanes> runs/hubspot-v2/brand/compose/replica \
    --brand runs/hubspot-v2/brand --out runs/hubspot-v2/brand/section-rules-baseline --strict   exit=0
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m brand_pipeline.section_rules_audit \
    event-genlaunch stress-playbook bakeoff-sol bakeoff-opus replica \
    --brand runs/remote/brand --out runs/remote/brand/section-rules-baseline --strict           exit=0
./venv/bin/python -m brand_pipeline.conversion_audit runs/remote/brand/compose/event-genlaunch \
    --campaign webinar-event --out runs/remote/brand/conversion-baseline/event-webinar          exit=0
./venv/bin/python -m brand_pipeline.conversion_audit runs/remote/brand/compose/stress-playbook \
    --campaign leadgen-gated-content --out runs/remote/brand/conversion-baseline/stress-leadgen exit=0
./venv/bin/python -m brand_pipeline.conversion_audit runs/remote/brand/compose/bakeoff-sol \
    runs/remote/brand/compose/bakeoff-opus --campaign product-launch \
    --out runs/remote/brand/conversion-baseline/bakeoffs-launch                                 exit=0
./venv/bin/python -m brand_pipeline.conversion_audit runs/remote/brand/compose/replica \
    --out runs/remote/brand/conversion-baseline/replica-unbound                                 exit=0
./venv/bin/python -m brand_pipeline.conversion_audit runs/hubspot-v2/brand/compose/replica \
    <8 hero lanes> --out runs/hubspot-v2/brand/conversion-baseline                              exit=0
```

Demo-lane battery after the copy fix (all exit 0):

```
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python tools/run_hero_archetype_gallery.py \
    --brand runs/hubspot-v2/brand --style corporate-saas-clean \
    --lane runs/hubspot-v2/brand/compose/hero-archetypes --rerender --only demo   exit=0 (gate PASS)
node brand_pipeline/slop_audit.mjs .../demo/index.html                            exit=0 (PASS @1440 + @1180)
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m brand_pipeline.interaction_audit .../demo --strict   exit=0 (0 required fails)
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m brand_pipeline.spacing_audit .../demo \
    --brand runs/hubspot-v2/brand --strict --no-shots   exit=0 (18 conform / 1 drift / 0 wrong-step / 0 off-ladder; scale 6 measured / 8 on-scale / 0 OFF-SCALE)
env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m brand_pipeline.signature_audit .../demo \
    --brand runs/hubspot-v2/brand --strict              exit=0 (PASS, accent 0.669%)
./venv/bin/python -m brand_pipeline.voice_audit .../demo --brand runs/hubspot-v2/brand --strict   exit=0 (PASS)
tools/run_hero_archetype_gallery.py --shots                                        exit=0 (8 shots + contact sheet + lane index)
```

Suite accounting: baseline 1060 at stage A → **1259 passed** now, zero failures,
zero lost. This stage adds 135 discovered tests (86 section-rules + 29
conversion + 20 activated from staged_); the remainder of the growth is the
concurrent agent's parallel work in this repo.

Note on one full-suite run inside the sandbox: 9 fails + 4 errors, all
Playwright browser-launch failures under the sandbox (pre-existing tests in
test_fix3/fix4/fix5); the same suite outside the sandbox passes 1259/1259 with
exit 0. No test content was touched to achieve this.

### Files created / edited (fence compliance)

- NEW `brand_pipeline/section_rules_audit.py`, `brand_pipeline/conversion_audit.py`
- NEW `brand_pipeline/tests/test_section_rules_audit.py`,
  `brand_pipeline/tests/test_conversion_structure.py`
- RENAMED `brand_pipeline/tests/staged_test_quality_steals.py` →
  `test_quality_steals.py` (header re-framed, assertions unchanged)
- CALIBRATED `brand_pipeline/contracts/section-rules.yaml` (changelog entries
  17:40Z + 18:05Z; SR-TIER-02 severity; faq detection row; wrap-budget notes;
  SR-HERO-04 selector note)
- DATA FIX `runs/hubspot-v2/brand/compose/hero-archetypes/demo/composition.json`
  (+ re-rendered index.html/tokens.manifest/onbrand-report, refreshed lane
  shots/index) + lane `changes.md` entry
- REPORTS `runs/{hubspot-v2,remote}/brand/section-rules-baseline/`,
  `runs/{hubspot-v2,remote}/brand/conversion-baseline/`
- THIS changelog. No renderer, spec-book, style-bakeoff, root-changelog, or
  viewer files touched; `spec/anti-ai-slop.md` unchanged (no new universal rule
  needed — the two registryCandidates stay candidates).

## 2026-07-14 — BASELINE ROUND run (steal 2 protocol step 2–4) + first matrix finding fixed

*(the parallel stage-B agent — prompt-side/matrix lane; the auditor wiring
above is consumed as-is)*

- **Runner**: NEW `tools/run_eval_matrix.py` — generate (real loop, style pin
  `corporate-saas-clean`, `force_off_grid`, `max_repairs=3`) + full battery
  (slop / interaction / spacing / signature / voice `--strict` + section-rules
  baseline mode + conversion advisory) + results.json/md + shots/contact sheet;
  per-brief `generateSeconds` and per-gate `gateSeconds` recorded separately
  (README §Timing). Resumable (`page_passed` skip, `--only`, `--skip-gen`,
  `--force`, `--shots-only`). Briefs ride into each page dir as `brief.md` —
  conversion_audit's own binding channel, zero flags needed.
- **Round**: `evals/matrix/runs/2026-07-14-baseline/` — 12/12 generated +
  gated + shot; guidance flag OFF (measures the un-guided pipeline). Headline:
  onbrand 6/12 within 4 attempts; slop FLAG 9/12 (all AS-11/AS-12); spacing 4
  FAILs (hubspot); section-rules 3 req + 9 adv rows across 12 pages;
  **conversion hardFloor 4/12 — both leadgen-gated-content cells + both
  webinar-event cells render ZERO `<form>` elements** (briefs author the field
  lists verbatim). Full numbers + root-cause traces: the round's `round.md` +
  `results.md`.
- **Finding fixed renderer-side (AS-26 class)**: the model's natural
  registration emission — dedicated register section (`useCase: cta`,
  `archetype: split`) with a `form-field` contract slot whose copy IS the
  field list — dropped to a button-only band: the stamp reader only knew the
  dict shape and only conversion STACKS route form anatomy. FIX in
  `compose_from_composition.py`: (1) `_form_fields_stamp` resolves the LIST
  shape (help→helper, "A / B / C" option-string → list, option-run coerces
  text→select, sibling checkbox = opt-in row, consent-slot sentence rides
  `consent`); (2) conversion-use sections with a validated stamp normalize to
  the conversion stack (`is_conversion`), whatever archetype they declared —
  `_composition.archetype` keeps the declared value (provenance). Fact-gated
  both ways: form-less conversion splits keep their shape; repo scan found
  zero existing compositions in the newly-routed class; A/B renders (old stamp
  vs new) byte-identical on event-genlaunch, gallery-demo, both replicas.
  Tests: NEW `tests/test_baseline_findings.py` (12 — list-shape stamp, dict
  shape pinned verbatim, routing both directions, end-to-end render proof).
  The round's pages predate the fix (immutable record); the next round
  measures it.
- **Recorded, not patched** (fix level: guidance/prompt, per round.md): the
  leadgen hero-form-centered 3-fields-into-single-row fold (archetype-choice
  error — the campaign grammar wants a dedicated capture section; the flag-ON
  A/B round is the test); AS-11/AS-12 under-filled beats (repair loop never
  sees slop); alignment-resolution as the dominant hubspot attempt-killer.
- **Verification**: suite **1346 passed, exit 0** (1259 at the entry above +
  12 findings tests + concurrent agents' growth; zero failures). Replicas
  re-scored post-fix: hubspot **0.9567**, remote **0.9509** — the +0.001-class
  movements vs the 0.956/0.950 pins trace to concurrent testimonial-seam/
  hero-height renderer improvements (band diffs in the lane reports), not to
  steal wiring (A/B byte-identity above). Section-rules `--strict` re-run
  exit 0 across hubspot 8 heroes + replica and remote event-genlaunch +
  replica; conversion exit 0 (event lane binds via `--campaign`/brief only —
  gallery lanes fact-gated skip); slop spot-checks PASS @1440+@1180 on demo /
  event-genlaunch / both replicas.
