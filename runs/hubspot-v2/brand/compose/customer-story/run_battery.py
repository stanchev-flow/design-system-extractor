#!/usr/bin/env python3
"""Full gate battery for the customer-story lane (true exit codes, never masked).

Gates (as used by existing hubspot-v2 lanes):
  a. onbrand_check.py --composition           (HARD invariants)
  b. slop_audit.mjs                            (@1440 + @1180 internally)
  c. interaction_audit.py --strict
  d. spacing_audit.py --strict
  e. signature_audit.py --strict               (signature/accent + accent-device floors)
  f. voice_audit.py --strict
  g. section_rules_audit.py --strict
  h. conversion_audit.py --strict
  i. media-binding + mark-legality             (media_semantics.lint_media_bindings)

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python \
      runs/hubspot-v2/brand/compose/customer-story/run_battery.py
"""
from __future__ import annotations

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
BASE_STYLE = "corporate-saas-clean"
LANE = HERE
BAT = LANE / "battery"


def hero_layout_id() -> str | None:
    import yaml
    doc = yaml.safe_load(BRAND_YAML.read_text()) or {}
    for layout in (doc.get("layouts") or []):
        lid = str((layout or {}).get("id") or "").lower()
        if "hero" in lid or "page-header" in lid:
            return layout.get("id")
    return None


def run(cmd: list[str], log_path: Path) -> int:
    proc = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=REPO)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"$ {' '.join(str(c) for c in cmd)}\n\n--- stdout ---\n{proc.stdout}\n"
        f"--- stderr ---\n{proc.stderr}\n--- exit={proc.returncode} ---\n")
    return proc.returncode


def media_lint() -> int:
    """media-binding + AS-67 mark-legality over the composition.json."""
    sys.path.insert(0, str(BP))
    import media_semantics as ms
    comp = json.loads((LANE / "composition.json").read_text())
    hits = ms.lint_media_bindings(comp, ms.load_media_assets(BRAND_DIR))
    out = ["media-binding + mark-legality lint (media_semantics.lint_media_bindings)"]
    if not hits:
        out.append("PASS — 0 hits (every media slot resolves or declares its gap; "
                   "refs resolve; third-party marks stay in factual proof contexts)")
    else:
        for sid, rule, msg in hits:
            out.append(f"FAIL [{rule}] section `{sid}`: {msg}")
    (BAT / "media-binding.log").write_text("\n".join(out) + "\n")
    return 0 if not hits else 1


def main() -> int:
    gate_layout = hero_layout_id()
    rows: dict[str, int] = {}

    rows["onbrand"] = run(
        [PY, BP / "onbrand_check.py", BRAND_YAML, LANE,
         "--layout", gate_layout, "--style", BASE_STYLE, "--composition",
         "--report", "onbrand-report.md"], BAT / "onbrand.log")
    rows["slop"] = run(
        ["node", BP / "slop_audit.mjs", LANE / "index.html"], BAT / "slop.log")
    rows["interaction"] = run(
        [PY, BP / "interaction_audit.py", LANE, "--strict",
         "--out", BAT / "interaction"], BAT / "interaction.log")
    rows["spacing"] = run(
        [PY, BP / "spacing_audit.py", LANE, "--brand", BRAND_DIR, "--strict",
         "--no-shots", "--out", BAT / "spacing"], BAT / "spacing.log")
    rows["signature"] = run(
        [PY, BP / "signature_audit.py", LANE, "--brand", BRAND_DIR, "--strict",
         "--out", BAT / "signature"], BAT / "signature.log")
    rows["voice"] = run(
        [PY, "-m", "brand_pipeline.voice_audit", LANE, "--brand", BRAND_DIR,
         "--strict", "--out", BAT / "voice"], BAT / "voice.log")
    rows["section_rules"] = run(
        [PY, BP / "section_rules_audit.py", LANE, "--brand", BRAND_DIR, "--strict",
         "--out", BAT / "section-rules"], BAT / "section-rules.log")
    rows["conversion"] = run(
        [PY, BP / "conversion_audit.py", LANE, "--brand", BRAND_DIR, "--strict",
         "--out", BAT / "conversion"], BAT / "conversion.log")
    rows["media_binding"] = media_lint()

    (HERE / "battery-summary.json").write_text(json.dumps(rows, indent=2) + "\n")
    verdict = "GREEN" if not any(rows.values()) else "RED"
    print(f"[customer-story] {verdict} " + " ".join(f"{k}={v}" for k, v in rows.items()))
    return 0 if not any(rows.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
