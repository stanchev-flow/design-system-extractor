#!/usr/bin/env python3
"""replica_repair.py — the G4 convergence repair hook (spec/convergence-loop.md §2).

Deterministic core of the L3 replica loop: classifies each below-bar band's
punch item into a gap type, drives bounded per-band repair calls (injected —
the LLM-backed adapter reuses staged_author's fragment machinery and is wired
separately), and enforces the ratchet protocol (snapshot before apply, revert
any round that dropped the score or broke a gate, never bank a regression).

The hook itself NEVER edits composer/gate code: RENDERER-gap bands are filed
as work orders in the loop ledger and excluded from self-repair — when only
renderer gaps remain the hook returns False so ``gate_g4_replica`` stops
honestly instead of gaming the metric.

Contract (fixed by pipeline_flow.gate_g4_replica):
    hook = make_repair_hook(repair_call, ...)
    hook(brand_dir, replica_report) -> bool   # True = re-score is worthwhile

This module is intentionally dependency-light (stdlib only) so it can land
while the staged-author surface is still moving; nothing imports it until
run_pipeline_flow gains --converge.
"""
from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path
from typing import Callable

SCHEMA_VERSION = "loop-ledger.v1"
DEFAULT_BAR = 0.90            # mirrors pipeline_flow.DEFAULT_REPLICA_BAR
DEFAULT_BANDS_PER_ROUND = 2   # bounded: worst-first, small steps
RATCHET_EPS = 0.001           # score drop below this is metric noise, not regression

# canon files the loop may mutate (via repair calls) and must snapshot/revert
CANON_FILES = ("brand.yaml", "layout-library.yaml", "section-copy.yaml")

LEDGER_NAME = "loop-ledger.json"
SNAPSHOT_DIR = ".loop"

# ── gap taxonomy (spec §2.1) ──────────────────────────────────────────────────

GAP_AUTHORING = "authoring"   # fix facts in canon files from evidence
GAP_EVIDENCE = "evidence"     # re-extract, then re-author the fragment
GAP_RENDERER = "renderer"     # shared-code capability — work order, no self-fix
GAP_ASSET = "asset"           # deterministic asset work (e.g. self-host a font)

# capability → gap type. Keys are matched as lowercase substrings of the punch
# item's `capability` field; NOTE_RULES run against the free-text note as a
# fallback. Unknown capabilities default to AUTHORING (the repair call is
# fact-fenced, so the worst case is a no-op round, never a code edit).
CAPABILITY_RULES: tuple[tuple[str, str], ...] = (
    ("composite hero art", GAP_RENDERER),
    ("carousel statics", GAP_RENDERER),
    ("video static", GAP_RENDERER),
    ("accordion open-state", GAP_RENDERER),
    ("marquee", GAP_RENDERER),
    ("mega-menu", GAP_RENDERER),
    ("multi-layer", GAP_RENDERER),
    ("display font", GAP_ASSET),
    ("font", GAP_ASSET),
    ("content width diverges", GAP_AUTHORING),
    ("fidelity below threshold", GAP_AUTHORING),
)
NOTE_RULES: tuple[tuple[str, str], ...] = (
    (r"impossible|cannot (?:physically )?fit|evidence contradict", GAP_EVIDENCE),
    (r"not self-hosted|woff2", GAP_ASSET),
    (r"hug/measure|content span", GAP_AUTHORING),
)


def classify_capability(capability: str, note: str = "") -> str:
    cap = (capability or "").strip().lower()
    for needle, gap in CAPABILITY_RULES:
        if needle in cap:
            return gap
    text = (note or "").lower()
    for rx, gap in NOTE_RULES:
        if re.search(rx, text):
            return gap
    return GAP_AUTHORING


# ── report → candidates ───────────────────────────────────────────────────────

def band_candidates(report: dict, bar: float = DEFAULT_BAR) -> list[dict]:
    """Below-bar work items, worst-first: punchList entries joined with their
    band scores, each classified. Bands below bar WITHOUT a punch item still
    surface (gap authoring, capability 'fidelity below threshold') so the loop
    never silently skips a failing band."""
    bands = [b for b in (report.get("bands") or []) if isinstance(b, dict)]
    by_section: dict[str, dict] = {}
    for b in bands:
        label = str(b.get("label") or b.get("id") or "")
        section = label.split("—")[0].strip() or str(b.get("id") or "")
        by_section[section] = b
    items: list[dict] = []
    seen: set[str] = set()
    for p in (report.get("punchList") or []):
        if not isinstance(p, dict):
            continue
        section = str(p.get("section") or "")
        capability = str(p.get("capability") or "")
        note = str(p.get("note") or "")
        band = by_section.get(section, {})
        score = p.get("score", band.get("score"))
        if score is not None and float(score) >= bar:
            continue
        items.append({
            "section": section,
            "bandId": band.get("id"),
            "score": float(score) if score is not None else None,
            "capability": capability,
            "gap": classify_capability(capability, note),
            "note": note,
        })
        seen.add(section)
    for section, band in by_section.items():
        score = band.get("score")
        if section in seen or score is None or float(score) >= bar:
            continue
        items.append({
            "section": section, "bandId": band.get("id"),
            "score": float(score),
            "capability": "fidelity below threshold",
            "gap": GAP_AUTHORING,
            "note": "band below bar with no punch item",
        })
    items.sort(key=lambda it: (it["score"] is None, it["score"]))
    return items


# ── ledger ────────────────────────────────────────────────────────────────────

def _ledger_path(brand_dir: Path) -> Path:
    return Path(brand_dir) / LEDGER_NAME


def load_ledger(brand_dir: Path) -> dict:
    path = _ledger_path(brand_dir)
    if path.is_file():
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict) and isinstance(data.get("rounds"), list):
                return data
        except Exception:
            pass
    return {"schemaVersion": SCHEMA_VERSION, "rounds": [],
            "rendererWorkOrders": [], "noSelfFix": []}


def save_ledger(brand_dir: Path, ledger: dict) -> None:
    _ledger_path(brand_dir).write_text(json.dumps(ledger, indent=2) + "\n")


# ── snapshot / ratchet ────────────────────────────────────────────────────────

def snapshot_canon(brand_dir: Path, iteration: int) -> Path:
    brand_dir = Path(brand_dir)
    snap = brand_dir / SNAPSHOT_DIR / f"iter-{iteration:03d}"
    snap.mkdir(parents=True, exist_ok=True)
    for name in CANON_FILES:
        src = brand_dir / name
        if src.is_file():
            shutil.copy2(src, snap / name)
    return snap


def restore_snapshot(brand_dir: Path, iteration: int) -> bool:
    brand_dir = Path(brand_dir)
    snap = brand_dir / SNAPSHOT_DIR / f"iter-{iteration:03d}"
    if not snap.is_dir():
        return False
    for name in CANON_FILES:
        src = snap / name
        if src.is_file():
            shutil.copy2(src, brand_dir / name)
    return True


# ── the hook ──────────────────────────────────────────────────────────────────

def make_repair_hook(
    repair_call: Callable[[Path, dict], bool],
    *,
    bar: float = DEFAULT_BAR,
    bands_per_round: int = DEFAULT_BANDS_PER_ROUND,
    validator: Callable[[Path], object] | None = None,
) -> Callable[[Path, dict], bool]:
    """Build the ``repair_hook`` for ``gate_g4_replica``.

    ``repair_call(brand_dir, candidate) -> bool`` performs ONE bounded band
    repair (fact edits only — the LLM adapter is fenced to canon fragments)
    and reports whether anything changed. ``validator`` (optional) is run
    after applying a round; any error reverts the round (a gate break is
    never banked).
    """

    def hook(brand_dir: Path, report: dict) -> bool:
        brand_dir = Path(brand_dir)
        ledger = load_ledger(brand_dir)
        rounds: list[dict] = ledger["rounds"]
        no_self_fix: set[str] = set(ledger.get("noSelfFix") or [])
        overall = report.get("overall")

        # ── ratchet: settle the PREVIOUS round against this fresh score ──
        if rounds and rounds[-1].get("overallAfter") is None:
            prev = rounds[-1]
            prev["overallAfter"] = overall
            before = prev.get("overallBefore")
            if (overall is not None and before is not None
                    and float(overall) < float(before) - RATCHET_EPS):
                prev["reverted"] = True
                prev["revertReason"] = (f"score regressed "
                                        f"{before:.4f} -> {float(overall):.4f}")
                restore_snapshot(brand_dir, int(prev["iteration"]))
                for section in prev.get("bandsAttempted") or []:
                    no_self_fix.add(section)

        candidates = band_candidates(report, bar)
        renderer = [c for c in candidates if c["gap"] == GAP_RENDERER]
        fixable = [c for c in candidates
                   if c["gap"] != GAP_RENDERER and c["section"] not in no_self_fix]

        # renderer work orders accumulate (dedup by section+capability)
        orders = ledger.get("rendererWorkOrders") or []
        known = {(o.get("section"), o.get("capability")) for o in orders}
        for c in renderer:
            key = (c["section"], c["capability"])
            if key not in known:
                orders.append({k: c[k] for k in
                               ("section", "capability", "score", "note")})
                known.add(key)
        ledger["rendererWorkOrders"] = orders
        ledger["noSelfFix"] = sorted(no_self_fix)

        if not fixable:
            ledger["stopped"] = {
                "reason": ("renderer-capability work orders only"
                           if renderer else "no below-bar candidates"),
                "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "overall": overall,
            }
            save_ledger(brand_dir, ledger)
            return False

        iteration = len(rounds) + 1
        snapshot_canon(brand_dir, iteration)
        attempted: list[str] = []
        changed_any = False
        for cand in fixable[:max(1, bands_per_round)]:
            attempted.append(cand["section"])
            try:
                changed = bool(repair_call(brand_dir, cand))
            except Exception as exc:
                rounds.append({
                    "iteration": iteration, "overallBefore": overall,
                    "overallAfter": overall, "bandsAttempted": attempted,
                    "error": f"{type(exc).__name__}: {exc}", "reverted": True,
                })
                restore_snapshot(brand_dir, iteration)
                for section in attempted:
                    no_self_fix.add(section)
                ledger["noSelfFix"] = sorted(no_self_fix)
                save_ledger(brand_dir, ledger)
                return False
            changed_any = changed_any or changed

        if not changed_any:
            rounds.append({"iteration": iteration, "overallBefore": overall,
                           "overallAfter": overall,
                           "bandsAttempted": attempted, "changed": False})
            save_ledger(brand_dir, ledger)
            return False

        if validator is not None:
            rep = validator(brand_dir)
            errors = list(getattr(rep, "errors", []) or [])
            if errors:
                restore_snapshot(brand_dir, iteration)
                for section in attempted:
                    no_self_fix.add(section)
                rounds.append({
                    "iteration": iteration, "overallBefore": overall,
                    "overallAfter": overall, "bandsAttempted": attempted,
                    "reverted": True,
                    "revertReason": f"validator: {len(errors)} error(s)",
                    "validatorErrors": errors[:5],
                })
                ledger["noSelfFix"] = sorted(no_self_fix)
                save_ledger(brand_dir, ledger)
                return False

        rounds.append({"iteration": iteration, "overallBefore": overall,
                       "overallAfter": None,   # settled by the NEXT invocation
                       "bandsAttempted": attempted, "changed": True,
                       "gaps": [c["gap"] for c in fixable[:max(1, bands_per_round)]]})
        save_ledger(brand_dir, ledger)
        return True

    return hook
