#!/usr/bin/env python3
"""Batch-1 re-gate driver: gate every affected page with baseline-matching flags and diff
the new scorecard against the saved pre-Batch-1 baseline (/tmp/batch1-baseline)."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = str(REPO / "venv" / "bin" / "python")
GATE = str(REPO / "brand_pipeline" / "onbrand_check.py")
BASE = Path("/tmp/batch1-baseline")

RUNS_BRAND = "runs/woodwave/brand/brand.yaml"
AB_BRAND = "experiments/woodwave-ab/inputs/brand.yaml"
HY_BRAND = "experiments/woodwave-ab/inputs/brand/brand.yaml"

# (label, brand_yaml, render_dir, report_name, extra_flags)
JOBS = [
    ("full-editorial-luxury", RUNS_BRAND, "runs/woodwave/brand/compose/full-editorial-luxury",
     "onbrand-report.md", ["--layout", "opening-bookend", "--style", "editorial-luxury"]),
    ("full-radical-editorial", RUNS_BRAND, "runs/woodwave/brand/compose/full-radical-editorial",
     "onbrand-report.md", ["--layout", "opening-bookend", "--style", "radical-editorial"]),
    ("full-layout-patterns-v1", RUNS_BRAND, "runs/woodwave/brand/compose/full-layout-patterns-v1",
     "onbrand-report.md", ["--layout", "opening-bookend", "--style", "radical-editorial"]),
    ("full-layout-patterns-v2", RUNS_BRAND, "runs/woodwave/brand/compose/full-layout-patterns-v2",
     "onbrand-report.md", ["--layout", "opening-bookend", "--style", "radical-editorial"]),
    ("arm-a-structured", AB_BRAND, "experiments/woodwave-ab/arm-a-structured",
     "onbrand-report.md", ["--layout", "opening-bookend", "--style", "editorial-luxury"]),
    ("arm-a-structured(comp)", AB_BRAND, "experiments/woodwave-ab/arm-a-structured",
     "onbrand-report-comp.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
    ("arm-b-html", AB_BRAND, "experiments/woodwave-ab/arm-b-html",
     "onbrand-report.md", ["--layout", "opening-bookend", "--style", "editorial-luxury"]),
    ("hybrid-run-1", HY_BRAND, "experiments/woodwave-hybrid/run-1", "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
    ("hybrid-run-2", HY_BRAND, "experiments/woodwave-hybrid/run-2", "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
    ("hybrid-run-3", HY_BRAND, "experiments/woodwave-hybrid/run-3", "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
    ("hybrid-run-4", HY_BRAND, "experiments/woodwave-hybrid/run-4", "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
    ("hybrid-run-5", HY_BRAND, "experiments/woodwave-hybrid/run-5", "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
    ("hybrid-smoke", HY_BRAND, "experiments/woodwave-hybrid/smoke/render", "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
]


def baseline_path(render_dir, report_name):
    return BASE / (render_dir.replace("/", "__") + "__" + report_name.replace(".md", ".json"))


def summarize(sc):
    return {
        "overall": sc.get("overall"),
        "neverDo": sc.get("neverDo", {}),
        "fidelity": sc.get("fidelity", {}).get("pass"),
        "slop": sc.get("slop", {}).get("pass"),
        "invariants": sc.get("invariants", {}).get("pass"),
        "inv_mode": sc.get("invariants", {}).get("mode"),
    }


rows = []
regressions = []
for label, brand, rdir, report, flags in JOBS:
    cmd = [PY, GATE, brand, rdir, "--report", report, *flags]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    jname = report.replace(".md", ".json")
    newp = REPO / rdir / jname
    new = json.load(open(newp)) if newp.exists() else None
    bp = baseline_path(rdir, report)
    old = json.load(open(bp)) if bp.exists() else None
    ns = summarize(new) if new else None
    os_ = summarize(old) if old else None
    verdict = "PASS" if (ns and ns["overall"]) else "FAIL"
    base_verdict = ("PASS" if (os_ and os_["overall"]) else ("FAIL" if os_ else "N/A"))
    reg = ""
    if os_ and os_["overall"] and not (ns and ns["overall"]):
        reg = "REGRESSION overall PASS->FAIL"
        regressions.append((label, reg))
    # per-neverDo flips PASS->FAIL
    if os_ and ns:
        for rid, ov in os_["neverDo"].items():
            nv = ns["neverDo"].get(rid)
            if ov and not nv:
                regressions.append((label, f"neverDo {rid} PASS->FAIL"))
        for k in ("fidelity", "slop", "invariants"):
            if os_[k] and not ns[k]:
                regressions.append((label, f"{k} PASS->FAIL"))
    rows.append((label, base_verdict, verdict, ns["inv_mode"] if ns else "?", reg))

print(f"{'PAGE':28} {'BASE':6} {'NOW':6} {'INV':9} NOTE")
print("-" * 70)
for label, bv, v, invm, reg in rows:
    print(f"{label:28} {bv:6} {v:6} {invm:9} {reg}")

print("\n=== REGRESSIONS (PASS->FAIL vs baseline) ===")
if regressions:
    for label, r in regressions:
        print(f"  [{label}] {r}")
    sys.exit(2)
else:
    print("  NONE")
