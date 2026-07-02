#!/usr/bin/env python3
"""consolidate.py - the MANUAL consolidation pass for the brand signal loop.

See spec/signal-loop.md S4 (consolidation) and S5 (contradiction protocol), and the
six sign-off decisions. Runs ON-DEMAND only (never scheduled, never auto-before-publish).

What it does:
  1. Read signals.log lines since the last watermark.
  2. Group by ruleKey (fallback: normalized text for keyless new rules).
  3. Compute aggregate confidence: >=2 consistent signals across distinct sections ->
     raise toward high; any build-failure -> high; single occurrence -> cap medium/low.
  4. Two-track promotion gate:
       - build-failure  -> AUTO-PROMOTE into neverDo/recipePolicy (source: failure,
                           confidence: high) with an appended changelog entry. No ask.
       - design-language-> CANDIDATE only. NEVER auto-writes brand.yaml; surfaces in the
                           report for explicit user confirmation (SIGN-OFF #3).
       - one-off / conflict -> recorded as "applied as one-off"; brand.yaml untouched.
       - low/medium DL  -> held candidate; re-evaluated next pass.
  5. Write consolidation-report.md and (if anything was promoted) re-render brand.md.
  6. Advance the watermark.

--dry-run reports the two-track outcome WITHOUT writing brand.yaml, re-rendering, or
advancing the watermark (used for sanity tests; the existing brand.yaml is never mutated).

Stdlib + pyyaml only.

Examples:
  python3 brand_pipeline/consolidate.py runs/woodwave --dry-run
  python3 brand_pipeline/consolidate.py runs/woodwave            # live pass
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yaml  # noqa: E402
from signals import (  # noqa: E402
    load_yaml,
    now_iso,
    resolve_brand_dir,
    resolve_rule,
)

HERE = Path(__file__).resolve().parent
WATERMARK = ".consolidation-watermark.json"


def read_signals(brand_dir: Path) -> List[Dict[str, Any]]:
    log = brand_dir / "signals.log"
    if not log.exists():
        return []
    out: List[Dict[str, Any]] = []
    for ln in log.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            sys.stderr.write(f"skipping malformed signals.log line: {ln[:80]}...\n")
    return out


def read_watermark(brand_dir: Path) -> int:
    p = brand_dir / WATERMARK
    if not p.exists():
        return 0
    try:
        return int(json.loads(p.read_text()).get("processed", 0))
    except (json.JSONDecodeError, ValueError):
        return 0


def write_watermark(brand_dir: Path, processed: int) -> None:
    (brand_dir / WATERMARK).write_text(
        json.dumps({"processed": processed, "updatedAt": now_iso()}, indent=2))


def group_key(sig: Dict[str, Any]) -> str:
    rk = sig.get("ruleKey")
    if rk:
        return rk
    return "text:" + (sig.get("text") or "").strip().lower()[:80]


def aggregate_confidence(group: List[Dict[str, Any]]) -> str:
    if any(s.get("type") == "build-failure" for s in group):
        return "high"
    distinct_sections = {s.get("sectionId") for s in group if s.get("sectionId")}
    if len(distinct_sections) >= 2:
        return "high"
    # single occurrence -> cap at medium (or low if the signal itself was low)
    declared = {s.get("confidence") for s in group}
    return "low" if declared == {"low"} else "medium"


def classify(group: List[Dict[str, Any]], agg_conf: str) -> str:
    """Return one of: auto-promote | candidate | one-off | held."""
    if any(s.get("type") == "build-failure" for s in group):
        return "auto-promote"
    if any(s.get("detectedConflict") or s.get("scope") == "one-off" for s in group):
        return "one-off"
    # design-language track
    if agg_conf == "high":
        return "candidate"      # SIGN-OFF #3: needs user confirmation, never auto-write
    return "held"


def promote_build_failure(doc: Dict[str, Any], rule_key: Optional[str],
                          group: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Upsert a build-failure fact into neverDo/recipePolicy with a changelog entry.
    Returns a delta description. Mutates `doc` in place."""
    sample = group[-1]
    statement = sample.get("text") or "platform constraint learned from build failure"
    signal_id = sample.get("id")
    ts = now_iso()
    target = "recipePolicy" if (rule_key or "").startswith("recipePolicy") else "neverDo"
    rule_id = (rule_key.split(".", 1)[1] if rule_key and "." in rule_key
               else (rule_key or statement[:40]))
    changelog_entry = {
        "ts": ts, "action": "promoted", "from": None, "to": True,
        "by": "failure", "signalId": signal_id, "note": "auto-promoted build-failure",
    }

    if target == "recipePolicy":
        node = doc.setdefault("recipePolicy", {})
        existing = node.get(rule_id)
        action = "updated" if existing else "promoted"
        cl = (existing.get("changelog") if isinstance(existing, dict) else None) or []
        changelog_entry["action"] = action
        cl.append(changelog_entry)
        node[rule_id] = {
            "value": True, "statement": statement, "confidence": "high",
            "source": "failure", "scope": "design-language", "changelog": cl,
        }
    else:
        node = doc.setdefault("neverDo", [])
        found = next((r for r in node if isinstance(r, dict) and r.get("id") == rule_id), None)
        action = "updated" if found else "promoted"
        if found:
            cl = found.get("changelog") or []
            changelog_entry["action"] = action
            cl.append(changelog_entry)
            found.update({"statement": statement, "confidence": "high",
                          "source": "failure", "scope": "design-language", "changelog": cl})
        else:
            node.append({
                "id": rule_id, "statement": statement, "value": True,
                "confidence": "high", "source": "failure", "scope": "design-language",
                "changelog": [changelog_entry],
            })
    return {"target": f"{target}.{rule_id}", "action": action, "statement": statement,
            "signalId": signal_id}


def render_brand_md(brand_yaml: Path) -> Optional[str]:
    script = HERE / "render_brand_md.py"
    if not script.exists():
        return "render_brand_md.py not found; skipped re-render"
    res = subprocess.run([sys.executable, str(script), str(brand_yaml)],
                         capture_output=True, text=True)
    if res.returncode != 0:
        return f"render_brand_md.py failed: {res.stderr.strip()}"
    return None


def build_report(brand: str, buckets: Dict[str, List[Dict[str, Any]]],
                 promoted_deltas: List[Dict[str, Any]], dry_run: bool,
                 n_new: int, n_total: int) -> str:
    L: List[str] = []
    w = L.append
    w(f"# Consolidation report - {brand}")
    w("")
    w(f"- generated: {now_iso()}")
    w(f"- mode: {'DRY-RUN (no writes)' if dry_run else 'LIVE'}")
    w(f"- signals processed this pass: {n_new} (log total: {n_total})")
    w(f"- auto-promoted (build-failure): {len(buckets['auto-promote'])}")
    w(f"- candidates (need confirmation): {len(buckets['candidate'])}")
    w(f"- applied as one-off: {len(buckets['one-off'])}")
    w(f"- held (low/medium): {len(buckets['held'])}")
    w("")

    w("## Auto-promoted (build-failure -> neverDo/recipePolicy, no ask)")
    w("")
    if buckets["auto-promote"]:
        w("| ruleKey | sections | agg confidence | target | action |")
        w("|---|---|---|---|---|")
        delta_by_key = {d.get("ruleKey"): d for d in promoted_deltas}
        for g in buckets["auto-promote"]:
            d = delta_by_key.get(g["ruleKey"], {})
            target = d.get("target", g["ruleKey"] or "(new)")
            action = ("would auto-promote" if dry_run else d.get("action", "promoted"))
            w(f"| `{g['ruleKey'] or '(none)'}` | {', '.join(g['sections']) or '-'} "
              f"| {g['aggConfidence']} | `{target}` | {action} |")
    else:
        w("_none_")
    w("")

    w("## Candidates - design-language (REQUIRE user confirmation, brand.yaml NOT written)")
    w("")
    if buckets["candidate"]:
        w("| ruleKey | sections | agg confidence | already in brand.yaml? | sample |")
        w("|---|---|---|---|---|")
        for g in buckets["candidate"]:
            present = "yes (no change)" if g["existsInBrand"] else "no (new)"
            w(f"| `{g['ruleKey'] or '(none)'}` | {', '.join(g['sections']) or '-'} "
              f"| {g['aggConfidence']} | {present} | {g['sample'][:60]} |")
        w("")
        w("> Confirm a candidate to upsert it into `brand.yaml` (then re-render `brand.md`). "
          "Two consistent signals only FLAG a candidate; they never auto-write the design language.")
    else:
        w("_none_")
    w("")

    w("## Applied as one-off (contradictions; brand.yaml design language unchanged)")
    w("")
    if buckets["one-off"]:
        w("| ruleKey/conflictWith | section | questionId | sample |")
        w("|---|---|---|---|")
        for g in buckets["one-off"]:
            w(f"| `{g['conflictWith'] or g['ruleKey'] or '(none)'}` "
              f"| {', '.join(g['sections']) or '-'} | {g['questionId'] or '-'} | {g['sample'][:50]} |")
    else:
        w("_none_")
    w("")

    w("## Held candidates (low/medium - re-evaluate next pass)")
    w("")
    if buckets["held"]:
        for g in buckets["held"]:
            w(f"- `{g['ruleKey'] or '(none)'}` ({g['aggConfidence']}): {g['sample'][:70]}")
    else:
        w("_none_")
    w("")
    return "\n".join(L).rstrip() + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Manual consolidation pass for the brand signal loop")
    ap.add_argument("run_dir", help="runs/<brand>, runs/<brand>/brand, or a brand.yaml path")
    ap.add_argument("--dry-run", action="store_true",
                    help="report outcome without writing brand.yaml / re-rendering / advancing watermark")
    ap.add_argument("--no-render", action="store_true", help="skip brand.md re-render even on a live pass")
    args = ap.parse_args(argv)

    brand_dir = resolve_brand_dir(args.run_dir)
    brand = brand_dir.parent.name if brand_dir.name == "brand" else brand_dir.name
    brand_yaml = brand_dir / "brand.yaml"
    doc = load_yaml(brand_yaml)

    all_signals = read_signals(brand_dir)
    watermark = read_watermark(brand_dir)
    new_signals = all_signals[watermark:]

    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for s in new_signals:
        groups[group_key(s)].append(s)

    buckets: Dict[str, List[Dict[str, Any]]] = {
        "auto-promote": [], "candidate": [], "one-off": [], "held": []}
    promoted_deltas: List[Dict[str, Any]] = []

    for gk, group in groups.items():
        agg = aggregate_confidence(group)
        kind = classify(group, agg)
        rule_key = group[-1].get("ruleKey")
        found, _, _ = resolve_rule(doc, rule_key)
        meta = {
            "groupKey": gk,
            "ruleKey": rule_key,
            "conflictWith": next((s.get("conflictWith") for s in group if s.get("conflictWith")), None),
            "questionId": next((s.get("questionId") for s in group if s.get("questionId")), None),
            "sections": sorted({s.get("sectionId") for s in group if s.get("sectionId")}),
            "aggConfidence": agg,
            "count": len(group),
            "sample": group[-1].get("text", ""),
            "existsInBrand": bool(found),
        }
        buckets[kind].append(meta)
        if kind == "auto-promote" and not args.dry_run:
            delta = promote_build_failure(doc, rule_key, group)
            delta["ruleKey"] = rule_key
            promoted_deltas.append(delta)

    wrote_brand_yaml = False
    render_note = None
    if promoted_deltas and not args.dry_run:
        brand_yaml.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
        wrote_brand_yaml = True
        if not args.no_render:
            render_note = render_brand_md(brand_yaml)

    report = build_report(brand, buckets, promoted_deltas, args.dry_run,
                          len(new_signals), len(all_signals))
    report_path = brand_dir / "consolidation-report.md"
    report_path.write_text(report)

    if not args.dry_run:
        write_watermark(brand_dir, len(all_signals))

    summary = {
        "brand": brand,
        "mode": "dry-run" if args.dry_run else "live",
        "processed": len(new_signals),
        "autoPromoted": len(buckets["auto-promote"]),
        "candidates": len(buckets["candidate"]),
        "oneOff": len(buckets["one-off"]),
        "held": len(buckets["held"]),
        "brandYamlWritten": wrote_brand_yaml,
        "report": str(report_path),
    }
    if render_note:
        summary["renderNote"] = render_note
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
