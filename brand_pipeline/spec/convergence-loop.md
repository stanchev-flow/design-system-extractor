# Convergence loops — system-level 1:1 brand extraction

> Status: design / for review. Specifies the closed-loop convergence layer that
> makes `run_pipeline_flow.py` iterate the harness to 1:1 with the source brand
> autonomously. Grounded in machinery that already exists; the ONLY new
> component is the G4 `repair_hook` implementation (`replica_repair.py`) plus
> its ledger/ratchet protocol.

## 0. Principle

A loop may only exist where a **mechanical objective function** exists. Every
loop below iterates against a deterministic scorer/gate, never against vibes.
The LLM appears only inside bounded, fragment-scoped repair calls; the loop
controller, scoring, classification, apply, and revert are deterministic
Python. This is the same doctrine as the rest of the pipeline: the model
proposes facts, the machine measures, gates decide.

## 1. Loop taxonomy (L1–L4)

```
L1 EVIDENCE loop      objective: evidence self-consistency
   re-run targeted extract stage(s) when a sanity gate names impossible
   measurements (e.g. text-vs-geometry: a 14px-font 40-char sample cannot
   paint inside a 113px control — the visibleLabel bug class).
   EXISTS: stage re-runnability (run_brand_extraction --stages), geometry
   sanity gates in measure_computed. Loop trigger wiring: NEW (small).

L2 AUTHORING loop     objective: validator C1–C29 == 0 errors
   staged author → validate → group failing rows by owner/schema-path →
   bounded fragment-repair LLM call → atomic apply → re-validate.
   EXISTS COMPLETELY: staged_author.group_repair_errors /
   extract_repair_fragments / build_repair_bundle / parse_and_apply_repair,
   checkpointed in author-stage-status.json.

L3 REPLICA loop       objective: replica score >= bar, all gates green
   gate_g4_replica already runs: score → repair_hook(brand_dir, report) →
   re-score, with no-progress early stop and trajectory recording.
   MISSING: the repair_hook itself. Specified in §2 — this is the feature.

L4 DRIFT loop         objective: kit stays 1:1 over time (scheduled)
   cron: re-capture source → L1–L3 → diff brand.yaml vs stored canon →
   report drift as proposals (never auto-ratify; signal-loop.md rules).
   OPTIONAL, after L3 lands.
```

## 2. The G4 `repair_hook` — `brand_pipeline/replica_repair.py` (NEW)

Signature (already fixed by `pipeline_flow.gate_g4_replica`):

```python
def repair_hook(brand_dir: Path, replica_report: dict) -> bool:
    """One bounded repair round. True = something changed and re-scoring is
    worthwhile; False = nothing self-fixable remains (loop must stop)."""
```

### 2.1 Band-gap classification (deterministic)

Every below-bar band's punch reason maps to exactly one gap type:

| punch reason (compose_replica emits)        | gap type   | action |
|---|---|---|
| `content width diverges` / hug-measure collapse | AUTHORING  | band fragment-repair call (§2.2) — width/measure facts |
| missing/wrong copy, empty slots, wrong assets   | AUTHORING  | band fragment-repair call — copy/asset bindings |
| impossible geometry vs evidence (L1 sanity)     | EVIDENCE   | targeted re-extract of the section's stage, then re-author fragment |
| `carousel statics` / `video static` / `composite hero art` / `accordion open-state` | RENDERER | FILE punch item; band excluded from self-repair |
| `display font not self-hosted`                  | ASSET      | deterministic: fetch/copy woff2 into assets/fonts + @font-face fact |

RENDERER gaps are shared-code capabilities — the hook NEVER edits composer
code. It writes them to the ledger as work orders and returns False when only
renderer gaps remain (honest stop, mirrors "don't game the metric").

### 2.2 Band fragment-repair call (reuses L2 machinery)

For each AUTHORING band (worst-first, max `BANDS_PER_ROUND = 2` per round):

bundle = band's diff crop path (side-by-side) + the band's section grounding
YAML + its measured rects/computed fragments + ONLY the owning brand.yaml /
layout-library.yaml / section-copy.yaml fragments (resolved layout id →
pattern → copy entry) + the relevant spec excerpts. Same envelope discipline
as `staged_author.build_repair_bundle`: allowed-target whitelist, output-token
cap, hard child timeout, parse-and-apply with schema validation. The call may
ONLY move facts toward evidence — it receives the evidence and the diff, not
the score.

### 2.3 Ratchet protocol (no banked regressions)

Before apply: snapshot the three canon files (`.loop/<iter>/` in the lane).
After apply, the hook itself re-runs cheap gates (validator; smoke compose of
the touched bands). `gate_g4_replica` then re-scores. The NEXT hook invocation
reads the trajectory: if the previous round's score DROPPED or any gate went
PASS→FAIL, it reverts that snapshot first and marks those bands
`no-self-fix` in the ledger (they stop being candidates). v3's history is the
cautionary case: repair round 3 went 0.8701→0.8591 and was kept; under this
protocol it auto-reverts.

### 2.4 Loop ledger (`<brand>/loop-ledger.json`)

Append-only per round: iteration, trajectory score, bands attempted, gap
classes, fragments touched, gate results, revert events, renderer work orders.
The ledger is the loop's changes.md — the flow report links it, and
`EXPERIMENT-REPORT.md`-style honesty ("blocked after N repairs") comes from it
for free.

## 3. Exit criteria — what "1:1" means mechanically

The loop exits PASS when: score >= bar AND validator 0 errors AND
onbrand/slop/interaction/spacing green on the replica. It exits
NEEDS-CAPABILITY (honest, not failure) when the remaining below-bar bands are
all RENDERER work orders — the ledger then IS the 1:1 backlog. The score
ceiling is structural (~0.95–0.97): video motion, live carousels, and layered
hero art cannot score higher on a still-page metric (hubspot-v2's verified
best: 0.956). `--bar` therefore defaults to 0.90 (DEFAULT_REPLICA_BAR) with
`--bar 0.95 --max-iterations 8` as the "push to ceiling" profile.

## 4. CLI surface

```
run_pipeline_flow.py <lane> --converge            # wires repair_hook into G4
run_pipeline_flow.py <lane> --converge --bar 0.95 --max-iterations 8
```

No behavior change without `--converge` (repair_hook stays None — current
semantics preserved exactly).

## 5. Test plan

- Unit: classification table (each punch reason → gap type), ledger append,
  snapshot/revert, no-progress → False, renderer-only → False.
- Hook-level with a FAKE repair call (deterministic mutation): loop converges
  on a fixture whose authored width fact is wrong; loop reverts a mutation
  that lowers the score; loop stops honestly on a renderer-gap fixture.
- Integration (no LLM): gate_g4_replica(repair_hook=...) trajectory recorded,
  G5 refusal stays closed until PASS.
- Parity: hubspot-v2 / remote / woodwave-v2 flows unchanged without
  `--converge`.

## 6. Ownership / serialization

`replica_repair.py` is a NEW module (no collision). Wiring = ~5 lines in
`run_pipeline_flow.py` + one import; land it only when the staged-author
repair session is quiescent (its fragment machinery is a dependency). The
hook never writes composer/gate code — renderer work orders route to a human
or a dedicated session per the one-writer rule.

## 7. Phase 2 — wiring plan (`--converge` + LLM band-repair adapter)

> Ready-to-execute the moment the working tree is committed. Phase 1
> (`replica_repair.py` core + 15 tests) is landed and inert; nothing below
> changes behavior without the `--converge` flag.

### 7.1 Preconditions (hard gates on starting)

1. **Commit checkpoint exists** — the tree stacked since `089a968` is
   committed; the ratchet's revert semantics assume a stable git baseline
   under the lane snapshots.
2. **staged_author API frozen** — these signatures are the dependency
   surface and must not move after landing:
   `RepairGroup {owner, schema_path, errors, group_id}`,
   `build_repair_bundle(brand_dir, group) -> dict`,
   `split_repair_group_to_cap(brand_dir, group, cap)`,
   `parse_and_apply_repair(brand_dir, group, raw) -> list[str]`,
   plus `author_brand.atomic_write_group` / `_make_provider` /
   `_call_provider` and the caps (`REPAIR_INPUT_CAP_BYTES`, output-token
   cap, hard child timeout).
3. **Capability strings stable** — `compose_replica`'s punchList
   `capability` vocabulary is a contract with
   `replica_repair.CAPABILITY_RULES` (§2.1). Renames move in lockstep.

### 7.2 CLI wiring (exact changes)

`run_pipeline_flow.py` (new flags; all existing flags reused as-is):

```
--converge                    # wire the repair hook into G4 (default: off)
--converge-bands-per-round N  # default 2 (replica_repair.DEFAULT_BANDS_PER_ROUND)
```

Construction (in `main`, before `run_flow`):

```python
repair_hook = None
if args.converge:
    from brand_pipeline.replica_repair import make_repair_hook
    from brand_pipeline.band_repair import make_llm_repair_call
    from validate_brand_evidence import validate_brand_dir   # tools/extract
    repair_hook = make_repair_hook(
        make_llm_repair_call(model=args.author_model,
                             timeout=args.author_timeout),
        bar=args.replica_bar,
        bands_per_round=args.converge_bands_per_round,
        validator=lambda d: validate_brand_dir(d, smoke=False))
```

`pipeline_flow.run_flow(...)` gains one passthrough parameter
`repair_hook: Callable | None = None`, forwarded verbatim to
`gate_g4_replica(repair_hook=...)`. Default `None` ⇒ current semantics
byte-identical (parity-tested).

Profiles: `--converge` (bar 0.90, max-iterations 3 — clear the gate);
`--converge --replica-bar 0.95 --max-iterations 8` (push to the still-page
ceiling, §3).

### 7.3 The adapter — NEW `brand_pipeline/band_repair.py`

`make_llm_repair_call(model, timeout, ...) -> Callable[[Path, dict], bool]`
returns the `repair_call` that `make_repair_hook` accepts. Per candidate:

- **Gap routing.** `asset` gap ⇒ DETERMINISTIC branch, no LLM: e.g. the
  self-host-font order copies the woff2 into `assets/fonts/` + writes the
  `@font-face` fact. `evidence` gap ⇒ phase 2b (below); until then it
  returns False (band lands in noSelfFix — safe degradation, honest stop).
  `authoring` gap ⇒ the LLM branch:
- **Band fragment resolution** (`band_fragments(brand_dir, candidate)`):
  candidate `section` → `layouts[].id` match → its `patternRef` pattern in
  `layout-library.yaml` → its `layoutCopy` entry. Bundle = ONLY those
  fragments + the band's grounding YAML + its measured-rects slice + the
  side-by-side diff crop path + the relevant spec excerpts (brand-schema
  width/measure §§, spacing-conformance container law). Same envelope
  discipline as `build_repair_bundle`: allowed-target whitelist naming the
  resolved schema paths, input capped via the `split_repair_group_to_cap`
  mechanism, one provider call per band per round.
- **Prompt contract.** System: fact-fence doctrine — move authored facts
  toward the ATTACHED evidence only; never invent values; edit only the
  whitelisted fragments; output the bounded-patch JSON that
  `parse_and_apply_repair` validates. User: the bundle. The call receives
  evidence + diff, NEVER the score (no metric-gaming gradient).
- **Apply.** Through `parse_and_apply_repair` + `atomic_write_group` —
  a patch touching an unlisted fragment raises `AuthorBlocked`, which the
  hook's exception path converts into revert + noSelfFix (already tested).
- **Budget ceiling.** ≤ `bands_per_round` calls/round × `max_iterations`
  rounds (default profile: ≤6 calls; ceiling profile: ≤16). Per-call
  bytes/tokens/duration appended to the round's ledger entry (same
  telemetry discipline as `author-stage-status.json`).

### 7.4 Phase 2b — L1 evidence trigger (separable)

`evidence`-gap candidates run
`run_brand_extraction --stages measure --sections <band>` (targeted
re-measure), then re-enter the next round as `authoring`. Lands only after
the targeted-stage flag exists; until then the phase-2a degradation (mark
noSelfFix) holds.

### 7.5 Test plan

- `test_band_repair.py`: fragment resolution (section→layout→pattern→copy
  join), asset-branch determinism, fence rejection (patch outside whitelist
  ⇒ `AuthorBlocked` ⇒ hook reverts — integration with the phase-1 exception
  test), fake-provider round trip, budget/telemetry entries.
- CLI parity: flow WITHOUT `--converge` produces a byte-identical
  flow-report on the fixture lane (repair_hook is None).
- CLI smoke WITH `--converge`: fixture lane + fake replica runner + fake
  provider converges in ≤2 rounds; ledger trajectory recorded.
- Real-lane guard: hubspot-v2 / remote / woodwave-v2 flow tests unchanged.

### 7.6 Landing checklist (in order)

1. Confirm commit checkpoint + `git diff --stat` clean.
2. Grep-verify §7.1 signatures unchanged since this spec.
3. Land `band_repair.py` + tests → full suite green.
4. Land the `--converge` wiring (+ parity test) → full suite green.
5. Pilot: `run_pipeline_flow.py --brand hubspot-v3 --converge` (bar 0.90)
   — expect immediate PASS (already 0.901); then the ceiling profile
   `--replica-bar 0.95 --max-iterations 8`; review `loop-ledger.json`
   (trajectory, reverts, work orders) before blessing the profile as
   default for new extractions.
6. changes.md entry with the pilot's trajectory + ledger link.
