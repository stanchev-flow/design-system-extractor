#!/usr/bin/env python3
"""taste_sync.py - the write-back hooks that close the brand's self-education loop.

The kit (export_kit.py) is the brand's compiled taste; the gates are its immune system;
the layout library + magic-trick are its memory. What was missing is the LOOP — this
module is that loop, home-side. Everything lands as a PENDING entry for a human to
ratify (confirm-before-promote, per signal-loop discipline); nothing self-ratifies.

    --check <render-dir>...   run all three gates on rendered pages; every failure is
                              DRAFTED as a pending lesson into runs/<brand>/brand/signals.log
    --import <kit-copy>       read a FIELD kit copy's learning/ folder back home:
                              field signals -> home signals.log (tagged [field]);
                              field proposals -> pending-proposals.yaml for review
    --ratify <pattern-id>     promote a reviewed pending proposal into the project
                              layout library (layout_library.promote), with changelog
    --export-if-changed       re-export the kit when the canon (brand.yaml,
                              layout-library.yaml, magic-trick.md) is newer than the kit —
                              "clients always build from the current version"

The ratchet: field proposes -> home ratifies -> next export supersedes every kit copy.

Usage:
  python3 brand_pipeline/taste_sync.py <brand.yaml> [--check d1 d2 …] [--import kitdir]
                                       [--ratify id] [--export-if-changed]
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout_library as ll  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
PY = str(REPO_ROOT / "venv" / "bin" / "python")


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")


def _append_signal(brand_dir: Path, line: str) -> None:
    log = brand_dir / "signals.log"
    with log.open("a") as f:
        f.write(line.rstrip() + "\n")


# ── --check: gates -> drafted lessons ────────────────────────────────────────────

def check(brand_yaml: Path, render_dirs: list[Path], style: str | None) -> int:
    """Run onbrand + contrast + slop on each render; DRAFT a pending lesson per failure.
    Returns the number of failures (0 = all clean)."""
    brand_dir = brand_yaml.parent
    failures = 0
    for rd in render_dirs:
        index = rd / "index.html"
        if not index.exists():
            print(f"  skip {rd} (no index.html)")
            continue
        # brand gate
        cmd = [PY, str(REPO_ROOT / "brand_pipeline" / "onbrand_check.py"),
               str(brand_yaml), str(rd), "--report", "onbrand-report.md"]
        if style:
            cmd += ["--style", style]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
        out = r.stdout + r.stderr
        fails = re.findall(r"\[FAIL\]\s*(\S+)", out)
        overall = (re.search(r"OVERALL:\s*(\w+)", out) or [None, "UNKNOWN"])[1]
        # scripted audits
        audits = {}
        for audit in ("contrast_audit.mjs", "slop_audit.mjs"):
            a = subprocess.run(["node", str(REPO_ROOT / "brand_pipeline" / audit), str(index)],
                               capture_output=True, text=True, cwd=REPO_ROOT)
            audits[audit] = (a.returncode == 0, (a.stdout or "").strip().splitlines())

        verdicts = [f"onbrand={overall}"] + [
            f"{k.split('_')[0]}={'PASS' if ok else 'FAIL'}" for k, (ok, _) in audits.items()]
        print(f"  {rd.name}: {' · '.join(verdicts)}")

        # draft lessons (PENDING — a human reviews signals.log and ratifies/dismisses)
        if fails:
            failures += 1
            _append_signal(brand_dir, f"{_now()} | taste-sync | PENDING lesson | "
                                      f"onbrand FAIL [{', '.join(fails)}] on {rd.name} — "
                                      f"review render + consider a neverDo/anti-slop entry")
        for audit, (ok, lines) in audits.items():
            if not ok:
                failures += 1
                detail = next((l.strip() for l in lines if l.strip().startswith(("AS-", "TEXT", "HOVER"))), "")
                _append_signal(brand_dir, f"{_now()} | taste-sync | PENDING lesson | "
                                          f"{audit} FAIL on {rd.name} — {detail}")
    if failures:
        print(f"  -> {failures} pending lesson(s) drafted into {brand_dir / 'signals.log'}")
    return failures


# ── --import: field kit copy -> home pending queue ───────────────────────────────

def import_kit(brand_yaml: Path, kit_copy: Path) -> None:
    brand_dir = brand_yaml.parent
    learning = kit_copy / "learning"
    if not learning.is_dir():
        raise SystemExit(f"{kit_copy} has no learning/ folder (not a kit copy?)")

    # field signals -> home signals.log, tagged so provenance is never lost
    sig = learning / "signals.log"
    n_sig = 0
    if sig.exists():
        for line in sig.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            _append_signal(brand_dir, f"{_now()} | taste-sync | [field:{kit_copy.name}] {line}")
            n_sig += 1

    # field proposals -> pending-proposals.yaml (NOT the project library — review first)
    props = learning / "proposals.yaml"
    n_prop = 0
    if props.exists():
        data = yaml.safe_load(props.read_text()) or {}
        incoming = [p for p in (data.get("patterns") or []) if isinstance(p, dict) and p.get("id")]
        if incoming:
            pending_path = brand_dir / "pending-proposals.yaml"
            pending = yaml.safe_load(pending_path.read_text()) if pending_path.exists() else {}
            if not isinstance(pending, dict):
                pending = {}
            pending.setdefault("schemaVersion", "layout-patterns.v1")
            existing = {p.get("id") for p in (pending.get("patterns") or [])}
            merged = pending.get("patterns") or []
            for p in incoming:
                if p["id"] in existing:
                    continue
                p.setdefault("origin", "designed")
                p["fieldSource"] = kit_copy.name
                merged.append(p)
                n_prop += 1
            pending["patterns"] = merged
            pending_path.write_text(yaml.safe_dump(pending, sort_keys=False, width=100,
                                                   allow_unicode=True))
    print(f"imported from {kit_copy.name}: {n_sig} field signal(s) -> signals.log, "
          f"{n_prop} proposal(s) -> pending-proposals.yaml")
    if n_prop:
        print("review, then ratify with: taste_sync.py <brand.yaml> --ratify <pattern-id>")


# ── --ratify: pending proposal -> project layout library ────────────────────────

def ratify(brand_yaml: Path, pattern_id: str) -> None:
    brand_dir = brand_yaml.parent
    pending_path = brand_dir / "pending-proposals.yaml"
    if not pending_path.exists():
        raise SystemExit("no pending-proposals.yaml to ratify from")
    pending = yaml.safe_load(pending_path.read_text()) or {}
    pats = pending.get("patterns") or []
    match = next((p for p in pats if p.get("id") == pattern_id), None)
    if match is None:
        raise SystemExit(f"pattern '{pattern_id}' not in pending-proposals.yaml "
                         f"(pending: {[p.get('id') for p in pats]})")
    match.setdefault("changelog", []).append({
        "ts": _now(), "action": "ratified-from-field", "from": "pending",
        "to": "project library", "by": "iteration", "signalId": None,
        "note": f"field proposal ({match.get('fieldSource', 'unknown kit')}) reviewed and "
                f"ratified at home; ships in the next kit export"})
    ll.promote(match, brand_yaml)
    pending["patterns"] = [p for p in pats if p.get("id") != pattern_id]
    pending_path.write_text(yaml.safe_dump(pending, sort_keys=False, width=100,
                                           allow_unicode=True))
    _append_signal(brand_dir, f"{_now()} | taste-sync | RATIFIED field proposal "
                              f"'{pattern_id}' into layout-library.yaml")
    print(f"ratified '{pattern_id}' -> layout-library.yaml (run --export-if-changed to ship it)")


# ── --export-if-changed: canon newer than kit -> fresh kit ───────────────────────

def export_if_changed(brand_yaml: Path) -> bool:
    brand_dir = brand_yaml.parent
    kit = brand_dir / "kit"
    canon = [brand_dir / f for f in ("brand.yaml", "layout-library.yaml", "magic-trick.md")]
    # The kit also SHIPS the portable gates + the anti-slop spec (agent/quality/) — an
    # upgraded auditor is a canon change too, or every field copy keeps certifying with
    # the old, weaker gate.
    pipeline = Path(__file__).parent
    canon += [pipeline / f for f in
              ("contrast_audit.mjs", "slop_audit.mjs", "spec/anti-ai-slop.md")]
    kit_stamp = (kit / "readme.md")
    if kit_stamp.exists():
        newest = max(f.stat().st_mtime for f in canon if f.exists())
        if newest <= kit_stamp.stat().st_mtime:
            print("kit is current — no export needed")
            return False
    from export_kit import export
    out = export(brand_yaml, None)
    print(f"canon changed -> kit re-exported ({out})")
    return True


def main():
    ap = argparse.ArgumentParser(description="Close the brand's self-education loop.")
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("--check", nargs="+", type=Path, metavar="RENDER_DIR")
    ap.add_argument("--style", default="radical-editorial")
    ap.add_argument("--import", dest="import_kit", type=Path, metavar="KIT_COPY")
    ap.add_argument("--ratify", metavar="PATTERN_ID")
    ap.add_argument("--export-if-changed", action="store_true")
    args = ap.parse_args()
    by = args.brand_yaml.resolve()

    if args.check:
        check(by, args.check, args.style)
    if args.import_kit:
        import_kit(by, args.import_kit.resolve())
    if args.ratify:
        ratify(by, args.ratify)
    if args.export_if_changed:
        export_if_changed(by)
    if not any([args.check, args.import_kit, args.ratify, args.export_if_changed]):
        print("nothing to do — pass --check / --import / --ratify / --export-if-changed")


if __name__ == "__main__":
    main()
