# WoodWave Hybrid — Scoring Rubric

The hybrid loop (structured `composition.v1` → deterministic renderer → `--composition`
gate → repair) is judged against the **same brief** the A/B arms used
(`signup-launch`, same `brand.yaml` + `editorial-luxury` style — md5s asserted in
`run_hybrid.py`). The bar it must clear: **Arm A's brand-safety WITH Arm B's variety.**

Baselines it is measured against (from `experiments/woodwave-ab/REPORT.md`):

| baseline | gate | brief fidelity (value_props) | structural variety |
|---|---|---|---|
| **Arm A** (structured renderer) | PASS | **1/3** (3 props melted into 1 editorial body) | fixed brand `layouts[]` order |
| **Arm B** (HTML-first) | **FAIL** (brand-coupling drift) | 3/3 | high, but off-brand |

## Dimensions (each run + the set)

### 1. Gate conformance — *weight 0.30*
`onbrand_check.py --composition` OVERALL (hard neverDo + hard composition invariants).
- **Per run:** PASS = 1, FAIL = 0.
- **Set score:** PASS rate across the 5 runs. Must NOT regress to Arm B's coupling failures.
- Green target: **≥ 4/5** runs OVERALL PASS.

### 2. Brief fidelity — *weight 0.25*
Do the brief's **three** `value_props` render as **three distinct modules** (not melted
into one body, which was Arm A's ceiling of 1/3)?
- Score per run = (# value_props rendered as their own module) / 3.
- Green target: **≥ 1 run at 3/3**; median ≥ 2/3. (Arm A = 1/3.)

### 3. Structural variety — *weight 0.20*
Count DISTINCT section structures (archetypes) across the 5 pages, and within each page.
- Set score = # distinct archetypes used across all runs (of the 6 drawable).
- Green target: **≥ 3 distinct archetypes** across the set (vs Arm A's single fixed order);
  at least one run with ≥ 4 distinct archetypes on one page (the `run-5` contrast lane).

### 4. Novelty — *weight 0.15*
Does the set contain **≥ 1 `novelty:novel` section that gates GREEN** and is therefore
promotion-eligible into the project layout-library (`layout_library.promote`)?
- Score = 1 if a novel section exists on a PASSING page, else 0.
- Green target: **≥ 1** promotion-eligible novel section (expected in `run-3`/`run-5`).

### 5. Cost / latency — *weight 0.10*
Tokens + wall-clock + **repair attempts** to reach green (from `generation-telemetry.json`).
- Lower is better; a run that greens on attempt 0 scores highest.
- Reported, not pass/fail: mean attempts, mean output tokens, mean wall seconds.

## Composite

```
score = 0.30·gatePassRate + 0.25·briefFidelity + 0.20·varietyNorm
      + 0.15·noveltyGreen + 0.10·costScore
```
where `varietyNorm = min(distinctArchetypes, 5)/5` and
`costScore = 1 − min(meanAttempts−1, 2)/2` (attempt-0 green ⇒ 1.0).

## Verdict test
The hybrid **wins** iff it simultaneously:
1. matches Arm A on gate safety (**PASS rate ≥ Arm A**, i.e. no coupling regressions), AND
2. beats Arm A on brief fidelity (**≥ 1 run at 3/3** vs Arm A's 1/3), AND
3. beats Arm A on structural variety (**≥ 3 distinct archetypes** across the set), AND
4. yields **≥ 1 gate-green novel** section (variety Arm A structurally cannot produce).

---

# PART B — style-gated off-grid EXPANSION (ablation rubric)

Part B adds a **base-style capability flag** `offGridExpansion` (parsed in
`brand_pipeline/styles.py` from `styles/<id>.md` front-matter). TRUE unlocks generation
BEYOND the captured layout set — novel sections + the off-grid treatment set
{`stagger`, `overlap`, `bleed`, `float-wrap`, `counter-rotate`} on non-hero sections; FALSE
pins the model to reuse/adapt (enforced by `generate_composition.offgrid_prefilter` + the
repair loop). The ablation holds **brand + brief + seeds + directive constant** and varies
ONLY the flag (+ style identity for CONTROL):

| arm | style | flag | isolates |
|---|---|---|---|
| **ON** | editorial-luxury | TRUE (identity) | the expansion ceiling |
| **OFF** | editorial-luxury | **FORCED false** | the flag alone (same style) |
| **CONTROL** | corporate-saas-clean | false (identity) | a natively-locked style |

## Metrics (per arm, from composition JSON + gate scorecard + screenshot)

1. **Expansion-rate** — `# novelty:"novel"` sections. Target **ON > 0, OFF = 0, CONTROL = 0**.
2. **Off-grid usage** — `#` non-hero sections carrying an off-grid treatment. **Only ON > 0.**
3. **On-brand retention** — % of shipped sections that are gate-green (incl. `--composition`
   invariants) AND capability-legal. Target **100% of shipped**.
4. **Concept-fidelity** — structural distance of each novel section from the captured seeds,
   via the `layout_library` scorer (`match`): a novel section should be **on-concept**
   (shares the use-case, drawable archetype) yet **structurally distinct** (nearest-seed
   score below the reuse/adapt threshold → genuinely new, not a copy).
5. **Variety / wow** — distinct archetypes + distinct treatment kinds.

## PASS criteria (all must hold)
- **ON** ships **≥ 1 novel off-grid** section, and **all shipped sections gate-green** on
  legal treatments (retention 100%).
- **OFF + CONTROL** produce **zero novel / zero off-grid**.
- **No regression** to the deterministic pages (no shared render file touched).

## Guardrails (must both demonstrate)
- **Adversarial expansion → repair loop.** A composition that violates a brand `neverDo`
  (unsanctioned text-on-media) and the off-grid lock (novel + stagger under FALSE) is
  **caught** by the pre-filters and either **fixed** (a corrected retry gates green) or
  **rejected** (no retry left → `ok=False`, never shipped).
- **Promotion loop.** A gate-green novel section is `promote()`d into a project
  `layout-library.yaml` (via `pattern_dict_from_section`) and is thereafter **retrievable**
  (a match now reuses it) — novelty compounds into the library.
