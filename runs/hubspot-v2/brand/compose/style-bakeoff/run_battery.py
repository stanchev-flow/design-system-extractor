#!/usr/bin/env python3
"""Pass-3 checkpoint-D battery — the FULL existing gate battery per bakeoff page.

Runs, per lane (criteria C1, contracts/style-library/changes.md):
  a. onbrand_check.py --composition   (re-run fresh, same args as generation)
  b. slop_audit.mjs @1440+@1180       (exit code)
  c. interaction_audit.py --strict
  d. spacing_audit.py --strict        (0 hard fails / 0 off-scale)
  e. signature_audit.py --strict
  f. voice_audit.py --strict

True exit codes recorded per gate (never masked); reports under
<lane>/product-launch/battery/. Summary: battery-summary.json (this folder).

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python \
      runs/hubspot-v2/brand/compose/style-bakeoff/run_battery.py [--only STYLE]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
BRAND_DIR = REPO / "runs" / "hubspot-v2" / "brand"
BRAND_YAML = BRAND_DIR / "brand.yaml"
BP = REPO / "brand_pipeline"
PY = REPO / "venv" / "bin" / "python"
STYLES = ("swiss", "editorial-magazine", "neumorphism")
BASE_STYLE = "corporate-saas-clean"
PAGE = "product-launch"


def hero_layout_id() -> str | None:
    import yaml
    doc = yaml.safe_load(BRAND_YAML.read_text()) or {}
    for layout in (doc.get("layouts") or []):
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return layout.get("id")
    return None


def run(cmd: list[str], log_path: Path) -> int:
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"$ {' '.join(str(c) for c in cmd)}\n\n--- stdout ---\n{proc.stdout}\n"
        f"--- stderr ---\n{proc.stderr}\n--- exit={proc.returncode} ---\n")
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", default=None, choices=STYLES)
    args = ap.parse_args()

    gate_layout = hero_layout_id()
    summary_path = HERE / "battery-summary.json"
    summary: dict = {}
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text())
        except (OSError, json.JSONDecodeError):
            summary = {}

    exit_all = 0
    for style in STYLES:
        if args.only and style != args.only:
            continue
        lane = HERE.parent / f"style-bakeoff-{style}" / PAGE
        if not (lane / "index.html").exists():
            print(f"[{style}] no rendered page — skip")
            continue
        bat = lane / "battery"
        rows: dict[str, int] = {}

        rows["onbrand"] = run(
            [str(PY), str(BP / "onbrand_check.py"), str(BRAND_YAML), str(lane),
             "--layout", gate_layout, "--style", BASE_STYLE, "--composition",
             "--report", "onbrand-report.md"],
            bat / "onbrand.log")
        rows["slop"] = run(
            ["node", str(BP / "slop_audit.mjs"), str(lane / "index.html")],
            bat / "slop.log")
        rows["interaction"] = run(
            [str(PY), str(BP / "interaction_audit.py"), str(lane), "--strict",
             "--out", str(bat / "interaction")],
            bat / "interaction.log")
        rows["spacing"] = run(
            [str(PY), str(BP / "spacing_audit.py"), str(lane), "--brand",
             str(BRAND_DIR), "--strict", "--no-shots",
             "--out", str(bat / "spacing")],
            bat / "spacing.log")
        rows["signature"] = run(
            [str(PY), str(BP / "signature_audit.py"), str(lane), "--brand",
             str(BRAND_DIR), "--strict", "--out", str(bat / "signature")],
            bat / "signature.log")
        rows["voice"] = run(
            [str(PY), "-m", "brand_pipeline.voice_audit", str(lane), "--brand",
             str(BRAND_DIR), "--strict", "--out", str(bat / "voice")],
            bat / "voice.log")

        summary[style] = rows
        summary_path.write_text(json.dumps(summary, indent=2) + "\n")
        verdict = "GREEN" if not any(rows.values()) else "RED"
        print(f"[{style}] {verdict} " +
              " ".join(f"{k}={v}" for k, v in rows.items()))
        exit_all |= 1 if any(rows.values()) else 0

    return exit_all


if __name__ == "__main__":
    sys.exit(main())
