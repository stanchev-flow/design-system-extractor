#!/usr/bin/env python3
"""pipeline_flow.py — the CANONICAL ORDERED FLOW with HARD, FAIL-CLOSED GATES.

The extraction pipeline (run_brand_extraction.py), the validator
(tools/extract/validate_brand_evidence.py), the harness renderers
(render_components_preview.py / render_catalog.py), the replica gate
(compose_replica.py) and the creative generator (generate_composition.py) all
existed as SEPARATE steps an operator invoked by name. Nothing enforced their
ORDER or their QUALITY BARS between steps, so a run could go
``extract → generate`` — skipping the harness build and accepting a 0.543
replica — because the flow depended on the operator naming each sub-step.

This module bakes that flow in as a FIRST-CLASS ORCHESTRATOR. One high-level
intent ("extract brand <url>", "build replica for <lane>") runs the whole ordered
sequence from the right entry stage and FAILS CLOSED when a gate isn't met: a
failed gate STOPS the flow, writes an honest ``flow-report.json`` (status
``blocked`` / ``needs_iteration`` naming the gate + reason), and creative page
generation REFUSES to run.

CANONICAL ORDERED GATES (each individually re-runnable + idempotent):

  G1  extraction complete  — every evidence + authored artifact the downstream
                             gates read is present on disk.
  G2  validation           — validate_brand_evidence (C1–C28) → 0 ERRORS. Warnings
                             and notes are allowed and recorded. Block on errors.
  G3  harness built+reachable — the components-preview spec book exists at the
                             canonical lane path (Studio serves it there); the
                             slot-contract catalog is built when missing.
  G4  replica fidelity     — build the measured-only replica, score SSIM-style
                             similarity, enforce a THRESHOLD (default 0.90) with a
                             BOUNDED iteration loop. Below the bar after N ⇒ block
                             with status ``needs_iteration`` + per-band diagnostics.
  G5  creative generation  — runs ONLY after G1–G4 pass. generate_composition also
                             independently refuses (assert_generation_allowed) for
                             a lane whose recorded flow state isn't cleared.

THRESHOLD: the default replica bar is 0.90. It PASSES the committed quality-bar
lanes (hubspot-v2 0.956, remote 0.951) and BLOCKS the failing case
(woodwave-v2 0.767). It is configurable (``--replica-bar`` / ``replica_bar=``)
and lives here in ONE place, never scattered.

The heavy dependencies (Playwright for the replica shoot, the validator, the
generator) are imported lazily inside each gate so importing this module is cheap
and side-effect free — the gate LOGIC is unit-testable without any of them.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

try:
    from .artifact_digest import projection_input_digest
except ImportError:  # script/module import path
    from artifact_digest import projection_input_digest

_HERE = Path(__file__).resolve().parent
REPO_ROOT = _HERE.parent
RUNS_DIR = REPO_ROOT / "runs"
TOOLS_EXTRACT = REPO_ROOT / "tools" / "extract"
for _p in (str(_HERE), str(TOOLS_EXTRACT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── configuration ──────────────────────────────────────────────────────────────
# The replica quality bar. ONE source of truth (never hardcode this in scattered
# places). 0.90 passes hubspot-v2 (0.956) + remote (0.951) and blocks
# woodwave-v2 (0.767). See brand_pipeline/spec/pipeline-flow.md for the rationale.
DEFAULT_REPLICA_BAR = 0.90
# Default cap on the G4 diagnose→repair→re-score loop.
DEFAULT_MAX_ITERATIONS = 3

FLOW_REPORT_JSON = "flow-report.json"
FLOW_REPORT_MD = "flow-report.md"
FLOW_SCHEMA = "pipeline-flow.v1"

# The ordered gate ids (the canonical flow). ``generate`` (G5) only runs when the
# caller opts into creative generation; the extraction→replica spine (G1–G4)
# always runs.
GATE_ORDER = ("G1", "G2", "G3", "G4", "G5")
GATE_NAMES = {
    "G1": "extraction",
    "G2": "validation",
    "G3": "harness",
    "G4": "replica",
    "G5": "generation",
}

# G1 — the artifacts the downstream gates actually read. Kept generic (no brand
# specifics): every evidence-first lane produces these.
REQUIRED_EVIDENCE = (
    "dom-sections.json",
    "css-facts.json",
    "computed-styles.json",
    "section-rects.json",
    "motion-audit.json",
)
REQUIRED_AUTHORED = (
    "brand.yaml",
    "layout-library.yaml",
    "section-copy.yaml",
    "assets-tagged.json",
)

# G3 — the canonical harness artifacts. The spec book (components-preview) is the
# REQUIRED reachable harness; the slot-contract catalog is built when missing.
HARNESS_PREVIEW = ("components-preview", "index.html")
HARNESS_CATALOG = ("catalog", "index.html")
HARNESS_CATALOG_JSON = ("catalog", "catalog.json")


class GenerationBlocked(RuntimeError):
    """Raised by ``assert_generation_allowed`` when a lane has NOT cleared the
    ordered gates — the fail-closed refusal that stops page generation from
    running on an ungated / failing lane."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def brand_dir_for(brand: str) -> Path:
    """runs/<brand>/brand for a brand key; a path is returned as-is."""
    p = Path(brand)
    if p.is_dir() and (p / "brand.yaml").is_file():
        return p.resolve()
    return (RUNS_DIR / brand / "brand").resolve()


# ── gate result ─────────────────────────────────────────────────────────────────

@dataclass
class GateResult:
    gate: str                     # G1..G5
    name: str                     # extraction/validation/harness/replica/generation
    ok: bool
    status: str                   # pass | skip | blocked | needs_iteration | error
    reason: str = ""
    detail: dict = field(default_factory=dict)
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "gate": self.gate, "name": self.name, "ok": self.ok,
            "status": self.status, "reason": self.reason,
            "detail": self.detail, "durationS": round(self.duration_s, 3),
        }


# ── G1: extraction complete ───────────────────────────────────────────────────

def gate_g1_extraction(brand_dir: Path) -> GateResult:
    """Every evidence + authored artifact the downstream gates read is present.
    Fails CLOSED (never lets the flow jump to generation on a half-extracted
    lane) and names EXACTLY what is missing."""
    t0 = time.time()
    brand_dir = Path(brand_dir)
    evidence = brand_dir / "evidence"
    missing: list[str] = []
    for name in REQUIRED_AUTHORED:
        if not (brand_dir / name).is_file():
            missing.append(name)
    for name in REQUIRED_EVIDENCE:
        if not (evidence / name).is_file():
            missing.append(f"evidence/{name}")
    grounding = evidence / "grounding"
    if not (grounding.is_dir() and any(grounding.glob("*.yaml"))):
        missing.append("evidence/grounding/*.yaml (vision grounding)")
    ok = not missing
    return GateResult(
        "G1", GATE_NAMES["G1"], ok,
        "pass" if ok else "blocked",
        "" if ok else f"extraction incomplete — missing: {', '.join(missing)}",
        {"missing": missing,
         "checked": list(REQUIRED_AUTHORED) + [f"evidence/{n}" for n in REQUIRED_EVIDENCE]},
        time.time() - t0)


# ── G2: validation (C1–C28) ───────────────────────────────────────────────────

def gate_g2_validation(brand_dir: Path, *, allow_no_vision: bool = False,
                       min_logo_assets: int = 3, smoke: bool = True) -> GateResult:
    """Run the C1–C28 evidence contract. PASS iff 0 ERRORS (warnings + notes are
    recorded, never blocking). Blocks on any error, naming them."""
    t0 = time.time()
    try:
        import validate_brand_evidence as vbe
    except Exception as exc:  # pragma: no cover - import guard
        return GateResult("G2", GATE_NAMES["G2"], False, "error",
                          f"could not import validator: {type(exc).__name__}: {exc}",
                          {}, time.time() - t0)
    rep = vbe.validate_brand_dir(brand_dir, allow_no_vision=allow_no_vision,
                                 min_logo_assets=min_logo_assets, smoke=smoke)
    ok = rep.ok
    return GateResult(
        "G2", GATE_NAMES["G2"], ok,
        "pass" if ok else "blocked",
        "" if ok else f"{len(rep.errors)} validation error(s): "
                      + "; ".join(rep.errors[:6]),
        {"errors": rep.errors, "warnings": rep.warnings, "notes": rep.notes,
         "checks": "C1-C28"},
        time.time() - t0)


# ── G3: harness built + reachable ─────────────────────────────────────────────

def _http_ok(url: str, timeout: float = 4.0) -> bool | None:
    """True/False for an HTTP 200 at ``url``; None when the probe can't run
    (no server / network) so the caller falls back to the file-route contract."""
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return 200 <= resp.status < 300
    except Exception:
        return None


def gate_g3_harness(brand_dir: Path, *, build: bool = True,
                    studio_url: str | None = None) -> GateResult:
    """The lane's harness exists at the canonical path Studio serves and is
    reachable. The components-preview spec book is REQUIRED (block if missing);
    the slot-contract catalog is BUILT when missing (idempotent) so a lane always
    ends up with both. When ``studio_url`` is given we additionally verify an
    HTTP 200 for the preview route; otherwise we verify the file/route contract
    (studio_server.static_brand_lanes lists the preview exactly when this file
    exists)."""
    t0 = time.time()
    brand_dir = Path(brand_dir)
    brand_yaml = brand_dir / "brand.yaml"
    preview = brand_dir.joinpath(*HARNESS_PREVIEW)
    catalog = brand_dir.joinpath(*HARNESS_CATALOG)
    catalog_json = brand_dir.joinpath(*HARNESS_CATALOG_JSON)
    quality_path = preview.parent / "harness-quality.json"
    brand_digest = projection_input_digest(brand_dir)
    quality = {}
    if quality_path.is_file():
        try:
            quality = json.loads(quality_path.read_text())
        except Exception:
            quality = {}
    stale = quality.get("inputDigest") != brand_digest or quality.get("ok") is not True
    catalog_stale = True
    if catalog_json.is_file():
        try:
            catalog_stale = json.loads(catalog_json.read_text()).get("inputDigest") != brand_digest
        except Exception:
            catalog_stale = True

    built: list[str] = []
    if build and (not preview.is_file() or stale):
        _run_module_cli("render_components_preview",
                        [str(brand_yaml), "-o", str(preview.parent)])
        if preview.is_file():
            built.append("components-preview")
    if build and (catalog_stale or not (catalog.is_file() and catalog_json.is_file())):
        _run_module_cli("render_catalog",
                        [str(brand_yaml), "-o", str(catalog.parent)])
        if catalog.is_file():
            built.append("catalog")

    if not preview.is_file():
        return GateResult(
            "G3", GATE_NAMES["G3"], False, "blocked",
            "harness spec book missing — components-preview/index.html not "
            "rendered (run render_components_preview.py)",
            {"previewPath": _rel(preview), "built": built}, time.time() - t0)
    if not quality_path.is_file():
        return GateResult(
            "G3", GATE_NAMES["G3"], False, "blocked",
            "harness rendered without a passing substance/quality report",
            {"previewPath": _rel(preview), "built": built, "stale": stale},
            time.time() - t0)
    quality = json.loads(quality_path.read_text())
    if quality.get("ok") is not True or quality.get("inputDigest") != brand_digest:
        return GateResult(
            "G3", GATE_NAMES["G3"], False, "blocked",
            "harness quality report failed or does not match current brand data",
            {"previewPath": _rel(preview), "qualityPath": _rel(quality_path),
             "built": built, "stale": stale}, time.time() - t0)
    digest_attr = f'data-projection-input-digest="{brand_digest}"'
    stale_outputs = []
    for path in [preview, *sorted((preview.parent / "layouts").glob("*.html"))]:
        if digest_attr not in path.read_text(errors="replace"):
            stale_outputs.append(_rel(path))
    if catalog_json.is_file():
        try:
            if json.loads(catalog_json.read_text()).get("inputDigest") != brand_digest:
                stale_outputs.append(_rel(catalog_json))
        except Exception:
            stale_outputs.append(_rel(catalog_json))
    if stale_outputs:
        return GateResult(
            "G3", GATE_NAMES["G3"], False, "blocked",
            "harness dependent projection digest mismatch",
            {"staleOutputs": stale_outputs, "inputDigest": brand_digest,
             "built": built}, time.time() - t0)

    # Studio route contract: the preview is served at this site-relative path.
    try:
        route = "/" + str(preview.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        route = str(preview)
    http_status = None
    if studio_url:
        http_status = _http_ok(studio_url.rstrip("/") + route)

    detail = {
        "previewPath": _rel(preview),
        "catalogPath": _rel(catalog) if catalog.is_file() else None,
        "route": route,
        "built": built,
        "qualityPath": _rel(quality_path),
        "inputDigest": brand_digest,
        "httpChecked": bool(studio_url),
        "httpOk": http_status,
    }
    # A studio HTTP probe that ran and FAILED is a real reachability failure;
    # a probe that couldn't run (None) falls back to the file/route contract.
    if studio_url and http_status is False:
        return GateResult("G3", GATE_NAMES["G3"], False, "blocked",
                          f"harness not reachable over HTTP at {route}",
                          detail, time.time() - t0)
    return GateResult("G3", GATE_NAMES["G3"], True, "pass", "", detail,
                      time.time() - t0)


# ── G4: replica fidelity ──────────────────────────────────────────────────────

def read_replica_overall(brand_dir: Path,
                         out_dir: Path | None = None) -> tuple[float | None, dict]:
    """(overall score, report) from an existing replica-report.json, else
    (None, {}). Lets the gate resume from an already-scored replica without
    re-shooting."""
    out_dir = Path(out_dir) if out_dir else Path(brand_dir) / "compose" / "replica"
    report = out_dir / "replica-report.json"
    if report.is_file():
        try:
            data = json.loads(report.read_text())
            return float(data.get("overall")), data
        except Exception:
            return None, {}
    return None, {}


def _default_replica_runner(brand_dir: Path, out_dir: Path,
                            source_shot: Path | None, bar: float) -> float:
    """Run compose_replica (Playwright shoot + diff) and return the overall score.
    Isolated so tests can inject a fake runner and never touch Playwright."""
    import compose_replica as cr
    brand_yaml = Path(brand_dir) / "brand.yaml"
    argv = [str(brand_yaml), "-o", str(out_dir)]
    if source_shot:
        argv += ["--source-shot", str(source_shot)]
    cr.main(argv)
    overall, _ = read_replica_overall(brand_dir, out_dir)
    if overall is None:
        raise RuntimeError("compose_replica wrote no replica-report.json")
    return overall


def _band_diagnostics(report: dict, bar: float) -> list[dict]:
    """Per-band rows scoring below the bar — the honest 'what to repair' list."""
    bands = report.get("bands") or []
    low = []
    for b in bands:
        score = b.get("score")
        if isinstance(score, (int, float)) and score < bar:
            low.append({"id": b.get("id"), "label": b.get("label"),
                        "score": round(float(score), 4),
                        "height": b.get("height"), "structure": b.get("structure"),
                        "widthFidelity": b.get("widthFidelity")})
    low.sort(key=lambda r: r["score"])
    return low


def gate_g4_replica(brand_dir: Path, *, bar: float = DEFAULT_REPLICA_BAR,
                    source_shot: Path | None = None,
                    max_iterations: int = DEFAULT_MAX_ITERATIONS,
                    run: bool = True,
                    runner: Callable[[Path, Path, Path | None, float], float] | None = None,
                    repair_hook: Callable[[Path, dict], bool] | None = None,
                    out_dir: Path | None = None,
                    trusted_score: float | None = None) -> GateResult:
    """Build the measured-only replica, score it, and enforce ``bar`` with a
    BOUNDED iteration loop (max ``max_iterations``).

    Each iteration: (re)score the replica → if >= bar PASS; else record the score
    on the trajectory, run the optional ``repair_hook`` (agent/data repair) and
    re-score. The loop stops early when a repair makes no progress (so it never
    games the metric by looping without improvement). Below the bar after the
    budget is spent ⇒ status ``needs_iteration`` with the per-band diagnostics.

    Resume/verify modes:
      - ``trusted_score`` — score a caller vouches for (recorded verified number);
        used to verify a committed lane without re-shooting.
      - ``run=False``     — read the existing replica-report.json only (resume).
    """
    t0 = time.time()
    brand_dir = Path(brand_dir)
    out_dir = Path(out_dir) if out_dir else brand_dir / "compose" / "replica"
    runner = runner or _default_replica_runner
    trajectory: list[float] = []
    last_report: dict = {}

    def _finish(ok: bool, overall: float | None, iterations: int,
                reason: str = "") -> GateResult:
        low = _band_diagnostics(last_report, bar) if last_report else []
        status = "pass" if ok else "needs_iteration"
        return GateResult(
            "G4", GATE_NAMES["G4"], ok, status,
            reason or ("" if ok else
                       f"replica {overall:.4f} < bar {bar:.2f} after "
                       f"{iterations} iteration(s)"),
            {"overall": overall, "bar": bar,
             "iterationTrajectory": [round(s, 4) for s in trajectory],
             "iterations": iterations, "bandDiagnostics": low,
             "reportPath": _rel(out_dir / "replica-report.json"),
             "scoreSource": "trusted" if trusted_score is not None
                            else ("recorded" if not run else "measured")},
            time.time() - t0)

    if trusted_score is not None:
        trajectory.append(float(trusted_score))
        _, last_report = read_replica_overall(brand_dir, out_dir)
        ok = trusted_score >= bar
        return _finish(ok, float(trusted_score), 0)

    if not run:
        overall, last_report = read_replica_overall(brand_dir, out_dir)
        if overall is None:
            return GateResult("G4", GATE_NAMES["G4"], False, "needs_iteration",
                              "no replica-report.json to resume from — run G4 "
                              "with run=True to score the replica",
                              {"bar": bar, "reportPath": _rel(out_dir / "replica-report.json")},
                              time.time() - t0)
        trajectory.append(overall)
        return _finish(overall >= bar, overall, 0)

    overall = None
    iterations = 0
    for i in range(max(1, max_iterations)):
        iterations = i + 1
        try:
            overall = runner(brand_dir, out_dir, source_shot, bar)
        except Exception as exc:
            return GateResult("G4", GATE_NAMES["G4"], False, "error",
                              f"replica scoring failed: {type(exc).__name__}: {exc}",
                              {"bar": bar,
                               "iterationTrajectory": [round(s, 4) for s in trajectory]},
                              time.time() - t0)
        trajectory.append(overall)
        _, last_report = read_replica_overall(brand_dir, out_dir)
        if overall >= bar:
            return _finish(True, overall, iterations)
        if repair_hook is None:
            break  # nothing can improve the score — stop, don't game the metric
        improved = repair_hook(brand_dir, last_report)
        if not improved:
            break
    return _finish(False, overall, iterations)


# ── G5 refusal guard ──────────────────────────────────────────────────────────

def generation_gate_status(brand_dir: Path,
                           bar: float = DEFAULT_REPLICA_BAR) -> tuple[bool, str]:
    """(allowed, reason) for creative page generation on a lane.

    Priority: the orchestrator's ``flow-report.json`` (authoritative) → the run
    ``manifest.json`` → no record. Allowed ONLY when the recorded state shows
    G1–G4 cleared. FAIL-CLOSED: a lane with no record, a blocked/needs_iteration
    status, or a below-bar replica is REFUSED."""
    brand_dir = Path(brand_dir)
    report = brand_dir / FLOW_REPORT_JSON
    if report.is_file():
        try:
            data = json.loads(report.read_text())
        except Exception:
            return False, f"{FLOW_REPORT_JSON} is unreadable — re-run the flow"
        if data.get("generationAllowed") is True:
            return True, "gates cleared (flow-report.json)"
        gate = data.get("blockedGate") or "a gate"
        status = data.get("status") or "not_cleared"
        return False, (f"flow status '{status}': {gate} not cleared — "
                       f"run run_pipeline_flow.py to clear the gates")
    manifest = brand_dir / "manifest.json"
    if manifest.is_file():
        try:
            m = json.loads(manifest.read_text())
        except Exception:
            return False, "manifest.json unreadable"
        status = str(m.get("status") or "")
        replica = (m.get("replica") or {}).get("overall")
        val_errors = ((m.get("validation") or {}).get("errors"))
        harness_ok = str((m.get("harness") or {}).get("status") or "") in (
            "available", "pass", "ok")
        below = isinstance(replica, (int, float)) and replica < bar
        if status == "completed" and not below and (val_errors in (0, None)) \
                and (harness_ok or m.get("harness") is None):
            return True, "manifest status 'completed' with cleared gates"
        why = []
        if status and status != "completed":
            why.append(f"status '{status}'")
        if below:
            why.append(f"replica {replica} < bar {bar}")
        if val_errors not in (0, None):
            why.append(f"{val_errors} validation error(s)")
        return False, ("manifest shows the lane is not cleared: "
                       + (", ".join(why) or "no completion recorded"))
    return False, ("no flow-report.json or manifest.json — the lane has not been "
                   "run through the gated flow (run run_pipeline_flow.py first)")


def assert_generation_allowed(brand_dir: Path,
                              bar: float = DEFAULT_REPLICA_BAR) -> None:
    """Raise ``GenerationBlocked`` when the lane has not cleared the gates. The
    fail-closed refusal wired into generate_composition."""
    allowed, reason = generation_gate_status(brand_dir, bar)
    if not allowed:
        bd = Path(brand_dir)
        lane = bd.parent.name if bd.name == "brand" else bd.name
        raise GenerationBlocked(
            f"page generation refused for {lane}: {reason}")


# ── module CLI helper ─────────────────────────────────────────────────────────

def _run_module_cli(module: str, argv: list[str]) -> None:
    """Invoke a sibling render module's CLI in a subprocess (their main() reads
    sys.argv directly). Mirrors compose_replica's subprocess call to
    onbrand_check."""
    import subprocess
    cmd = [sys.executable, str(_HERE / f"{module}.py"), *argv]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"{module} failed (exit {proc.returncode}): "
            f"{(proc.stderr or proc.stdout or '').strip()[:400]}")


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(REPO_ROOT))
    except Exception:
        return str(p)


# ── the orchestrator ──────────────────────────────────────────────────────────

@dataclass
class FlowResult:
    brand: str
    brand_dir: Path
    ok: bool
    status: str                      # completed | blocked | needs_iteration
    replica_bar: float
    gates: list[GateResult] = field(default_factory=list)
    blocked_gate: str | None = None
    generation_allowed: bool = False
    report_path: Path | None = None

    def to_dict(self) -> dict:
        return {
            "schemaVersion": FLOW_SCHEMA,
            "brand": self.brand,
            "brandDir": _rel(self.brand_dir),
            "replicaBar": self.replica_bar,
            "status": self.status,
            "ok": self.ok,
            "generationAllowed": self.generation_allowed,
            "blockedGate": self.blocked_gate,
            "gates": [g.to_dict() for g in self.gates],
            "completedAt": _now(),
        }


def write_flow_report(result: FlowResult) -> Path:
    """Persist flow-report.json (+ a human .md) into the lane — the per-run flow
    telemetry (stage timings + gate pass/fail + reasons)."""
    brand_dir = Path(result.brand_dir)
    brand_dir.mkdir(parents=True, exist_ok=True)
    jpath = brand_dir / FLOW_REPORT_JSON
    jpath.write_text(json.dumps(result.to_dict(), indent=2) + "\n")
    lines = [
        f"# Pipeline flow report — {result.brand}", "",
        f"- status: **{result.status}**",
        f"- generation allowed: **{result.generation_allowed}**",
        f"- replica bar: {result.replica_bar}",
        f"- blocked gate: {result.blocked_gate or '—'}", "",
        "| gate | name | status | duration | reason |",
        "|---|---|---|---|---|",
    ]
    for g in result.gates:
        reason = (g.reason or "").replace("|", "\\|")[:200]
        lines.append(f"| {g.gate} | {g.name} | {g.status} | "
                     f"{g.duration_s:.2f}s | {reason} |")
    g4 = next((g for g in result.gates if g.gate == "G4"), None)
    if g4 and g4.detail.get("bandDiagnostics"):
        lines += ["", "## G4 band diagnostics (below bar)", "",
                  "| band | score | height | structure |", "|---|---|---|---|"]
        for b in g4.detail["bandDiagnostics"]:
            lines.append(f"| {b.get('label') or b.get('id')} | {b.get('score')} "
                         f"| {b.get('height')} | {b.get('structure')} |")
    (brand_dir / FLOW_REPORT_MD).write_text("\n".join(lines) + "\n")
    return jpath


def _update_manifest_status(brand_dir: Path, result: FlowResult) -> None:
    """Best-effort honest status write-through into manifest.json (if present).
    Never fails the flow on a manifest write problem."""
    manifest = Path(brand_dir) / "manifest.json"
    if not manifest.is_file():
        return
    try:
        m = json.loads(manifest.read_text())
    except Exception:
        return
    m["status"] = result.status
    m["flowReport"] = FLOW_REPORT_JSON
    m["generationAllowed"] = result.generation_allowed
    try:
        manifest.write_text(json.dumps(m, indent=2) + "\n")
    except Exception:
        pass


def run_flow(brand: str, *,
             replica_bar: float = DEFAULT_REPLICA_BAR,
             capture: Path | None = None,
             start_from: str = "G1",
             run_generation: bool = False,
             brief: Path | None = None,
             style: str = "editorial-luxury",
             max_iterations: int = DEFAULT_MAX_ITERATIONS,
             source_shot: Path | None = None,
             studio_url: str | None = None,
             build_harness: bool = True,
             replica_run: bool = True,
             trusted_replica_score: float | None = None,
             replica_runner: Callable | None = None,
             allow_no_vision: bool = False,
             smoke: bool = True,
             author_model: str = "claude-opus-4-8",
             author_timeout: float = 300.0,
             author_max_repairs: int = 2,
             force_author: bool = False,
             force_author_stage: str | None = None,
             write_report: bool = True,
             log=print) -> FlowResult:
    """Run the canonical ordered flow G1→G4 (+ optional G5), FAIL-CLOSED.

    A failed gate STOPS the flow immediately, records status
    (``blocked``/``needs_iteration``) + the blocking gate + reason, writes the
    flow report, and leaves ``generation_allowed=False`` so page generation
    refuses. Idempotent + resumable: ``start_from`` skips already-passing gates,
    and each gate no-ops the expensive work it already did (harness present,
    replica report present) unless asked to redo it.
    """
    brand_dir = brand_dir_for(brand)
    brand_key = brand_dir.parent.name if brand_dir.name == "brand" else Path(brand).name
    result = FlowResult(brand_key, brand_dir, ok=False, status="blocked",
                        replica_bar=replica_bar)

    start_idx = GATE_ORDER.index(start_from) if start_from in GATE_ORDER else 0

    # Fresh-extraction leg: a single "extract brand <url>" intent supplies a
    # capture dir. When we're entering at G1 and a capture is given, run the real
    # extraction stage runner FIRST so G1 verifies genuinely-produced artifacts.
    # Without a capture the flow verifies/resumes an already-extracted lane.
    if start_idx == 0:
        authored_missing = [
            name for name in REQUIRED_AUTHORED if not (brand_dir / name).is_file()
        ]
        evidence_ready = all(
            (brand_dir / "evidence" / name).is_file() for name in REQUIRED_EVIDENCE
        ) and (brand_dir / "assets-manifest.json").is_file()
        extraction_args = {
            "model": author_model,
            "timeout": author_timeout,
            "max_repairs": author_max_repairs,
            "force_author": force_author,
            "force_author_stage": force_author_stage,
        }
        extraction_t0 = time.time()
        try:
            if capture is not None:
                log(f"[flow] extraction: run_brand_extraction --brand {brand_key}")
                _run_extraction(brand_key, Path(capture), log=log, **extraction_args)
            elif evidence_ready and (
                    authored_missing or force_author or force_author_stage):
                # Resume an evidence-complete lane directly at AUTHOR. Capture/mine/
                # vision/curate are intentionally not repeated.
                log(f"[flow] author resume: run_brand_extraction --brand {brand_key} "
                    "--stages author,validate")
                _run_extraction(brand_key, None, stages="author,validate",
                                log=log, **extraction_args)
        except Exception as exc:
            author_detail = {}
            author_report_path = brand_dir / "author-report.json"
            if author_report_path.is_file():
                try:
                    author_report = json.loads(author_report_path.read_text())
                    blocked_stage = next(
                        (row for row in author_report.get("stages", [])
                         if row.get("status") == "blocked"), None)
                    if blocked_stage:
                        author_detail = {
                            "authorStage": blocked_stage.get("name"),
                            "authorStageInputBytes": blocked_stage.get("inputBytes"),
                            "authorStageModel": blocked_stage.get("model"),
                            "authorStageDurationS": blocked_stage.get("durationS"),
                            "authorStageReason": blocked_stage.get("reason"),
                        }
                except Exception:
                    pass
            gr = GateResult(
                "G1", GATE_NAMES["G1"], False, "blocked",
                f"author/extraction stage failed: {type(exc).__name__}: {exc}",
                {"phase": "author" if capture is None else "extraction",
                 "authorOutputCompleteness": list(REQUIRED_AUTHORED),
                 **author_detail},
                time.time() - extraction_t0,
            )
            result.gates.append(gr)
            result.blocked_gate = "G1"
            result.status = "blocked"
            if write_report:
                result.report_path = write_flow_report(result)
                _update_manifest_status(brand_dir, result)
            return result

    spine = ["G1", "G2", "G3", "G4"]
    if run_generation:
        spine.append("G5")

    for gate in spine:
        if GATE_ORDER.index(gate) < start_idx:
            result.gates.append(GateResult(gate, GATE_NAMES[gate], True, "skip",
                                           "resumed past this gate (start_from)"))
            continue
        log(f"[flow] {gate} {GATE_NAMES[gate]} …")
        if gate == "G1":
            gr = gate_g1_extraction(brand_dir)
        elif gate == "G2":
            gr = gate_g2_validation(brand_dir, allow_no_vision=allow_no_vision,
                                    smoke=smoke)
        elif gate == "G3":
            gr = gate_g3_harness(brand_dir, build=build_harness,
                                 studio_url=studio_url)
        elif gate == "G4":
            gr = gate_g4_replica(brand_dir, bar=replica_bar,
                                 source_shot=source_shot,
                                 max_iterations=max_iterations,
                                 run=replica_run, runner=replica_runner,
                                 trusted_score=trusted_replica_score)
        else:  # G5 — only reached when G1–G4 already passed
            gr = _run_generation_gate(brand_dir, brief=brief, style=style,
                                      replica_bar=replica_bar, log=log)
        result.gates.append(gr)
        log(f"[flow] {gate} {gr.status.upper()}"
            + (f" — {gr.reason}" if gr.reason else ""))
        if not gr.ok:
            result.status = gr.status if gr.status in (
                "needs_iteration", "blocked") else "blocked"
            result.blocked_gate = gate
            result.generation_allowed = False
            if write_report:
                result.report_path = write_flow_report(result)
                _update_manifest_status(brand_dir, result)
            return result
        # G1–G4 cleared ⇒ generation is now allowed; persist BEFORE running G5 so
        # the guard inside generate_composition sees the cleared state.
        if gate == "G4":
            result.generation_allowed = True
            result.status = "completed"
            if write_report:
                result.report_path = write_flow_report(result)
                _update_manifest_status(brand_dir, result)

    result.ok = True
    result.status = "completed"
    result.generation_allowed = True
    if write_report:
        result.report_path = write_flow_report(result)
        _update_manifest_status(brand_dir, result)
    return result


def _run_extraction(brand: str, capture: Path | None, *, stages: str = "all",
                    model: str = "claude-opus-4-8", timeout: float = 300.0,
                    max_repairs: int = 2, force_author: bool = False,
                    force_author_stage: str | None = None,
                    log=print) -> None:
    """Invoke the real extraction stage runner (run_brand_extraction.py) for a
    fresh capture. Subprocess so its module-level sys.path juggling and stage
    imports stay isolated from the orchestrator process."""
    import subprocess
    cmd = [sys.executable, str(REPO_ROOT / "run_brand_extraction.py"),
           "--brand", brand, "--stages", stages, "--model", model,
           "--author-timeout", str(timeout),
           "--author-max-repairs", str(max_repairs)]
    if capture is not None:
        cmd += ["--capture", str(capture)]
    if force_author:
        cmd.append("--force-author")
    if force_author_stage:
        cmd += ["--force-author-stage", force_author_stage]
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        detail = ""
        author_report = RUNS_DIR / brand / "brand" / "author-report.json"
        if author_report.is_file():
            try:
                reason = json.loads(author_report.read_text()).get("reason")
                if reason:
                    detail = f"; author gate: {reason}"
            except Exception:
                pass
        raise RuntimeError(
            f"extraction failed (exit {proc.returncode}) — see run_brand_extraction "
            f"output above{detail}")


def _run_generation_gate(brand_dir: Path, *, brief: Path | None, style: str,
                         replica_bar: float, log=print) -> GateResult:
    """G5 — creative generation. Reached ONLY after G1–G4 pass. Requires a brief;
    invokes generate_composition (which independently re-checks the guard)."""
    t0 = time.time()
    if brief is None:
        return GateResult("G5", GATE_NAMES["G5"], False, "error",
                          "no --brief supplied for generation (G1–G4 passed; "
                          "the lane is cleared and generation is allowed)",
                          {}, time.time() - t0)
    brief = Path(brief)
    if not brief.is_file():
        return GateResult("G5", GATE_NAMES["G5"], False, "error",
                          f"brief not found: {brief}", {}, time.time() - t0)
    try:
        import generate_composition as gc
    except Exception as exc:  # pragma: no cover
        return GateResult("G5", GATE_NAMES["G5"], False, "error",
                          f"could not import generator: {type(exc).__name__}: {exc}",
                          {}, time.time() - t0)
    brand_yaml = Path(brand_dir) / "brand.yaml"
    out_dir = Path(brand_dir) / "compose" / (brief.stem or "page") / "page"
    try:
        res = gc.generate_composition(brief.read_text(), brand_yaml, style,
                                      out_dir=out_dir, enforce_gates=True,
                                      log=log)
    except gc_generation_blocked() as exc:  # type: ignore[misc]
        return GateResult("G5", GATE_NAMES["G5"], False, "blocked",
                          str(exc), {}, time.time() - t0)
    except Exception as exc:
        return GateResult("G5", GATE_NAMES["G5"], False, "error",
                          f"generation failed: {type(exc).__name__}: {exc}",
                          {}, time.time() - t0)
    ok = bool(getattr(res, "ok", False))
    return GateResult("G5", GATE_NAMES["G5"], ok,
                      "pass" if ok else "blocked",
                      "" if ok else "generation did not pass its on-brand gate",
                      {"attempts": getattr(res, "attempts", None),
                       "outDir": _rel(out_dir)}, time.time() - t0)


def gc_generation_blocked():
    """The GenerationBlocked class (this module's), resolved lazily so G5 can
    catch the guard's refusal regardless of import order."""
    return GenerationBlocked


if __name__ == "__main__":  # pragma: no cover - thin manual entry; see run_pipeline_flow.py
    raise SystemExit(
        "run the flow via ./venv/bin/python run_pipeline_flow.py --brand <brand> "
        "(this module is the importable orchestrator library)")
