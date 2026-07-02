#!/usr/bin/env python3
"""Phase-0 (alignment quick wins) re-gate driver.

Extends tools/batch1_regate.py's job list with EVERY page that renders through the shared
compose_section/compose_page scaffolds (adds full-layout-patterns-v2-luxury, the Part B
showcase, the ablation arms, and the anchored hero page). Two modes:

  --baseline   gate the CURRENT renders and snapshot each scorecard to /tmp/phase0-baseline
  (default)    gate again and diff each scorecard against the /tmp/phase0-baseline snapshot;
               exit 2 on ANY PASS->FAIL regression.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = str(REPO / "venv" / "bin" / "python")
GATE = str(REPO / "brand_pipeline" / "onbrand_check.py")
BASE = Path("/tmp/phase0-baseline")

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
    ("full-lp-v2-luxury", RUNS_BRAND, "runs/woodwave/brand/compose/full-layout-patterns-v2-luxury",
     "onbrand-report.md", ["--layout", "opening-bookend", "--style", "editorial-luxury"]),
    ("arm-a-structured", AB_BRAND, "experiments/woodwave-ab/arm-a-structured",
     "onbrand-report.md", ["--layout", "opening-bookend", "--style", "editorial-luxury"]),
    ("arm-a-structured(comp)", AB_BRAND, "experiments/woodwave-ab/arm-a-structured",
     "onbrand-report-comp.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
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
    ("showcase", HY_BRAND, "experiments/woodwave-hybrid/showcase", "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
    ("ablation-arm-on", HY_BRAND, "experiments/woodwave-hybrid/ablation/arm-on",
     "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
    ("ablation-arm-off", HY_BRAND, "experiments/woodwave-hybrid/ablation/arm-off",
     "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "editorial-luxury", "--composition"]),
    ("ablation-arm-control", HY_BRAND, "experiments/woodwave-hybrid/ablation/arm-control",
     "onbrand-report.md",
     ["--layout", "opening-bookend", "--style", "corporate-saas-clean", "--composition"]),
    ("page-anchored", RUNS_BRAND, "experiments/woodwave-hero-gallery/page-anchored",
     "onbrand-report.md",
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


def main():
    make_baseline = "--baseline" in sys.argv
    if make_baseline:
        BASE.mkdir(parents=True, exist_ok=True)
    rows, regressions = [], []
    for label, brand, rdir, report, flags in JOBS:
        cmd = [PY, GATE, brand, rdir, "--report", report, *flags]
        subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
        jname = report.replace(".md", ".json")
        newp = REPO / rdir / jname
        new = json.load(open(newp)) if newp.exists() else None
        if make_baseline:
            if new is not None:
                baseline_path(rdir, report).write_text(json.dumps(new, indent=2))
            rows.append((label, "-", "PASS" if (new and new.get("overall")) else "FAIL",
                         (new or {}).get("invariants", {}).get("mode", "?"), "saved"))
            continue
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
        if os_ and ns:
            for rid, ov in os_["neverDo"].items():
                if ov and not ns["neverDo"].get(rid):
                    regressions.append((label, f"neverDo {rid} PASS->FAIL"))
            for k in ("fidelity", "slop", "invariants"):
                if os_[k] and not ns[k]:
                    regressions.append((label, f"{k} PASS->FAIL"))
        rows.append((label, base_verdict, verdict, ns["inv_mode"] if ns else "?", reg))

    print(f"{'PAGE':26} {'BASE':6} {'NOW':6} {'INV':9} NOTE")
    print("-" * 70)
    for label, bv, v, invm, reg in rows:
        print(f"{label:26} {bv:6} {v:6} {invm:9} {reg}")
    if make_baseline:
        print(f"\nBaseline snapshots -> {BASE}")
        return 0
    print("\n=== REGRESSIONS (PASS->FAIL vs baseline) ===")
    if regressions:
        for label, r in regressions:
            print(f"  [{label}] {r}")
        return 2
    print("  NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
