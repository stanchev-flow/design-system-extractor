#!/usr/bin/env python3
"""Conversion-structure checker — validates a composition's ordered section-family
sequence against contracts/conversion-structure.yaml (conversion-structure.v1;
law: spec/conversion-structure.md; stage B of the quality steals).

The checker is a small deterministic interpreter over the seven constraint kinds
(opens / closes / present / window / afterIndex / before / adjacent), plus the
campaign depth band and (post-render) the form-depth band. Zero LLM calls.

Family resolution (two grounds, spec §deterministic-checker):
  composition — useCase via the contracts' familyMap + bySlots (a form-contract
                slot binds capture-form; >=2 stat-contract slots bind stat-band);
  rendered    — the section-rules family detector re-grounds the same sequence on
                real markup (AUTHORITATIVE when index.html exists: a single stat
                slot that renders a 4-stat band is a stat band).

Severity doctrine (ADVISORY-first wiring):
  - every constraint row reports WARN on violation — advisory AND required rows
    alike gate nothing at wiring time;
  - the two hardFloor rows gate from birth (exit 1): a capture-form campaign
    without a capture-form section; a pricing campaign whose form precedes (or
    replaces) its tiers;
  - ``--strict`` additionally gates failed ``required`` rows — the graduation
    lever for after the eval-matrix baseline proves them (fixture-proven
    doctrine). The BRIEF outranks the grammar: contradictions explicitly stated
    in a brief record OVERRIDE, not FAIL (surfaced today via the report's
    per-row severity — automated brief-contradiction parsing is out of scope).

Campaign binding is FACT-GATED: a lane binds through (in order) an explicit
``--campaign``, its brief's ``campaignType:`` frontmatter (copy-brief.md /
brief.md beside the composition), or ``brief.campaignType`` inside
composition.json. Unbound lanes skip with a note.

Usage (repo root):
  ./venv/bin/python -m brand_pipeline.conversion_audit \\
      <lane dirs...> --brand runs/<brand>/brand [--campaign id] [--strict] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
CONTRACTS_PATH = HERE / "contracts" / "conversion-structure.yaml"
SCHEMA_VERSION = "conversion-structure.v1"

try:  # package + direct-script import contexts (spacing_audit precedent)
    from brand_pipeline import section_rules_audit as sra
except ImportError:  # pragma: no cover
    import section_rules_audit as sra


# ── contracts ────────────────────────────────────────────────────────────────────

def load_contracts(path: Path = CONTRACTS_PATH) -> dict:
    doc = yaml.safe_load(path.read_text()) or {}
    if doc.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f"{path.name}: schemaVersion {doc.get('schemaVersion')!r}"
                         f" != {SCHEMA_VERSION!r}")
    return doc


def campaign_by_id(doc: dict, cid: str) -> dict | None:
    for c in doc.get("campaigns") or []:
        if isinstance(c, dict) and c.get("id") == cid:
            return c
    return None


# ── family resolution ────────────────────────────────────────────────────────────

def composition_families(composition: dict, contracts: dict) -> list[dict]:
    """Ordered content sections -> bound family sets, resolved at composition
    level (familyMap + bySlots). Chrome never appears in compositions."""
    fmap = {k: v for k, v in (contracts.get("familyMap") or {}).items()
            if k != "bySlots" and isinstance(v, str)}
    out = []
    for i, sec in enumerate(composition.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or f"sec-{i}")
        uc = str(sec.get("useCase") or "")
        fams: set[str] = set()
        contracts_list = [str((sl or {}).get("contract") or "").lower()
                          for sl in (sec.get("slots") or [])]
        if uc in fmap:
            if uc == "about":
                # familyMap note: about binds the grid family only when moduled
                if sum(1 for c in contracts_list
                       if c in ("feature-item", "card")) >= 2:
                    fams.add(fmap[uc])
            else:
                fams.add(fmap[uc])
        if "form" in contracts_list:
            fams.add("capture-form")
        if sum(1 for c in contracts_list if c == "stat") >= 2:
            fams.add("stat-band")
        out.append({"id": sid, "useCase": uc, "families": fams})
    return out


def rendered_families(lane_dir: Path, html: Path) -> list[dict]:
    """Re-ground the sequence on rendered markup via the section-rules family
    detector (chrome + closing bookend excluded by that detector). The
    section-header pseudo-family is page grammar, not a sequence family."""
    from bs4 import BeautifulSoup
    comp_map = sra.composition_sections(lane_dir)
    soup = BeautifulSoup(html.read_text(), "html.parser")
    sections, _chrome = sra.split_page(soup, comp_map)
    out = []
    for s in sections:
        fams = set(s.families) - {"section-header"}
        out.append({"id": s.layout or s.sid, "useCase": s.use_case,
                    "families": fams})
    return out


# ── constraint interpreter ───────────────────────────────────────────────────────

def _named(row: dict, *keys) -> list[str]:
    fams: list[str] = []
    for key in keys:
        v = row.get(key)
        if isinstance(v, str):
            fams.append(v)
        elif isinstance(v, list):
            fams.extend(str(x) for x in v)
    return fams


def _idx_binding(seq: list[dict], fams: list[str]) -> list[int]:
    """1-based indices of sections binding ANY of the named families."""
    want = set(fams)
    return [i + 1 for i, s in enumerate(seq) if want & s["families"]]


def interpret_constraint(row: dict, seq: list[dict]) -> tuple[bool, str]:
    """(ok, detail) for one constraint row against the ordered family sequence."""
    kind = str(row.get("kind") or "")
    if kind == "opens":
        fam = str(row.get("family"))
        if not seq:
            return False, "no content sections"
        ok = fam in seq[0]["families"]
        return ok, (f"opens with {fam}" if ok else
                    f"first section binds {sorted(seq[0]['families']) or 'nothing'}"
                    f", not {fam}")
    if kind == "closes":
        fams = _named(row, "family", "anyOf")
        if not seq:
            return False, "no content sections"
        ok = bool(set(fams) & seq[-1]["families"])
        return ok, (f"closes on {sorted(set(fams) & seq[-1]['families'])}" if ok
                    else f"last section binds "
                         f"{sorted(seq[-1]['families']) or 'nothing'}, wanted "
                         f"one of {fams}")
    if kind == "present":
        fams = _named(row, "family", "anyOf")
        n = len(_idx_binding(seq, fams))
        lo = int(row.get("min", 0))
        hi = row.get("max")
        hi = int(hi) if hi is not None else 10 ** 6
        ok = lo <= n <= hi
        return ok, (f"{n} section(s) bind {fams} (budget {lo}"
                    f"{'-' + str(hi) if hi < 10**6 else '+'})")
    if kind == "window":
        fams = _named(row, "family", "anyOf")
        first_n = int(row.get("firstN", 1))
        hits = _idx_binding(seq, fams)
        if not hits:
            return False, f"no section binds {fams} (window firstN {first_n})"
        ok = hits[0] <= first_n
        return ok, (f"first {fams} match at index {hits[0]} "
                    f"({'within' if ok else 'past'} the first {first_n})")
    if kind == "afterIndex":
        fam = str(row.get("family"))
        min_idx = int(row.get("minIndex", 1))
        hits = _idx_binding(seq, [fam])
        early = [i for i in hits if i < min_idx]
        if not hits:
            return True, f"no {fam} section (vacuous)"
        ok = not early
        return ok, (f"first {fam} at index {hits[0]} "
                    f"({'>=' if ok else '<'} minIndex {min_idx})")
    if kind == "before":
        first, then = str(row.get("first")), str(row.get("then"))
        fi = _idx_binding(seq, [first])
        ti = _idx_binding(seq, [then])
        if not fi or not ti:
            return True, (f"{first if not fi else then} absent (vacuous)")
        ok = fi[0] < ti[0]
        return ok, (f"first {first} at {fi[0]}, first {then} at {ti[0]}"
                    + ("" if ok else f" — {then} precedes {first}"))
    if kind == "adjacent":
        fams = _named(row, "family")
        to = _named(row, "toAnyOf")
        gap = int(row.get("maxGap", 1))
        hits = _idx_binding(seq, fams)
        anchors = _idx_binding(seq, to)
        if not hits:
            return True, f"no {fams} section (vacuous)"
        if not anchors:
            return False, f"{fams} present but no {to} beat anywhere"
        best = min(abs(h - a) for h in hits for a in anchors)
        ok = best <= gap
        return ok, (f"nearest {to} beat {best} step(s) from {fams} "
                    f"(maxGap {gap})")
    return False, f"unknown constraint kind '{kind}'"


# ── the checker ──────────────────────────────────────────────────────────────────

def check_conversion_structure(composition: dict, campaign: dict,
                               families: list[dict] | None = None,
                               form_field_count: int | None = None,
                               contracts: dict | None = None) -> dict:
    """Evaluate one campaign grammar. ``families`` overrides the composition-level
    projection (pass the render-grounded sequence when available).
    ``form_field_count`` is the rendered visible-control count (None = unknown,
    formDepth reports skip)."""
    contracts = contracts or load_contracts()
    seq = families if families is not None \
        else composition_families(composition, contracts)
    rows: list[dict] = []

    for row in campaign.get("constraints") or []:
        ok, detail = interpret_constraint(row, seq)
        rows.append({"kind": row.get("kind"),
                     "families": _named(row, "family", "anyOf", "toAnyOf",
                                        "first", "then"),
                     "severity": row.get("severity", "advisory"),
                     "ok": ok, "detail": detail,
                     "why": str(row.get("why") or "").strip()})

    band = campaign.get("depthBand") or {}
    n = len(seq)
    lo, hi = int(band.get("min", 0)), int(band.get("max", 10 ** 6))
    rows.append({"kind": "depthBand", "families": [],
                 "severity": "advisory", "ok": lo <= n <= hi,
                 "detail": f"{n} content section(s) (band {lo}-{hi}, "
                           f"funnel {campaign.get('funnelStage')})",
                 "why": "depth follows the funnel stage"})

    fd = campaign.get("formDepth") or {}
    has_form = bool(_idx_binding(seq, ["capture-form"]))
    if not has_form:
        fd_row = {"ok": True, "detail": "no capture form (formDepth vacuous)"}
    elif form_field_count is None:
        fd_row = {"ok": True,
                  "detail": "form present; field count unmeasured (no render)"}
    else:
        flo = int(fd.get("minFields", 0))
        fhi = int(fd.get("maxFields", 10 ** 6))
        fd_row = {"ok": flo <= form_field_count <= fhi,
                  "detail": f"{form_field_count} visible field(s) "
                            f"(band {flo}-{fhi})"}
    rows.append({"kind": "formDepth", "families": ["capture-form"],
                 "severity": "advisory", **fd_row,
                 "why": str(fd.get("note") or "").strip()})

    # hardFloor rows — gate from birth (structural dishonesty in any campaign)
    floors: list[dict] = []
    if campaign.get("conversionMoment") == "capture-form":
        ok = has_form
        floors.append({"rule": "hardFloor:conversion-moment", "ok": ok,
                       "detail": ("capture-form present" if ok else
                                  "declared conversionMoment capture-form but "
                                  "no capture-form section renders")})
    if campaign.get("id") == "pricing":
        tiers = _idx_binding(seq, ["pricing-tiers"])
        forms = _idx_binding(seq, ["capture-form"])
        if forms and not tiers:
            floors.append({"rule": "hardFloor:never-gate-the-price", "ok": False,
                           "detail": "capture-form renders but the tier band "
                                     "never does — the price is gated"})
        elif forms and tiers and forms[0] < tiers[0]:
            floors.append({"rule": "hardFloor:never-gate-the-price", "ok": False,
                           "detail": f"capture-form at index {forms[0]} precedes "
                                     f"tiers at {tiers[0]}"})
        else:
            floors.append({"rule": "hardFloor:never-gate-the-price", "ok": True,
                           "detail": "no form gates the tier band"})

    return {"campaign": campaign.get("id"),
            "funnelStage": campaign.get("funnelStage"),
            "sequence": [{"id": s["id"],
                          "families": sorted(s["families"])} for s in seq],
            "rows": rows, "hardFloor": floors,
            "ok": all(f["ok"] for f in floors)}


# ── lane binding ─────────────────────────────────────────────────────────────────

_FRONTMATTER_RX = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def lane_campaign_id(lane_dir: Path, composition: dict) -> str | None:
    """Fact-gated campaign binding: brief frontmatter beside the composition
    (copy-brief.md / brief.md), else composition.brief.campaignType."""
    for name in ("copy-brief.md", "brief.md"):
        p = lane_dir / name
        if not p.exists():
            continue
        m = _FRONTMATTER_RX.match(p.read_text())
        if not m:
            continue
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        if isinstance(meta, dict) and meta.get("campaignType"):
            return str(meta["campaignType"])
    brief = composition.get("brief")
    if isinstance(brief, dict) and brief.get("campaignType"):
        return str(brief["campaignType"])
    return None


def _rendered_form_fields(lane_dir: Path, html: Path) -> int | None:
    """Visible-control count of the page's capture form(s) — the section-rules
    form census (radio groups count once)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html.read_text(), "html.parser")
    total, found = 0, False
    for form in soup.select("form"):
        if form.find_parent("nav") is not None or \
                form.find_parent(class_="c-foot") is not None:
            continue
        controls, _req = sra._visible_controls(form)
        total += len(controls)
        found = True
    return total if found else None


# ── lane audit + CLI ─────────────────────────────────────────────────────────────

def audit_lane(lane_dir: Path, contracts: dict,
               campaign_override: str | None = None) -> dict:
    entry: dict = {"lane": str(lane_dir)}
    comp_path = lane_dir / "composition.json"
    if not comp_path.exists():
        entry["note"] = "no composition.json — nothing to check"
        return entry
    composition = json.loads(comp_path.read_text())

    cid = campaign_override or lane_campaign_id(lane_dir, composition)
    if not cid:
        entry["note"] = ("no campaignType declared (brief frontmatter / "
                         "composition) — fact-gated skip")
        return entry
    campaign = campaign_by_id(contracts, cid)
    if campaign is None:
        entry["error"] = f"unknown campaign id '{cid}'"
        return entry
    entry["campaign"] = cid
    entry["binding"] = "explicit" if campaign_override else "declared"

    html = lane_dir / "index.html"
    families = None
    form_fields = None
    if html.exists():
        try:
            families = rendered_families(lane_dir, html)
            form_fields = _rendered_form_fields(lane_dir, html)
            entry["ground"] = "rendered"
        except Exception as exc:  # fall back to the composition projection
            entry["ground"] = f"composition (render parse failed: {exc})"
    else:
        entry["ground"] = "composition"

    entry.update(check_conversion_structure(
        composition, campaign, families=families,
        form_field_count=form_fields, contracts=contracts))
    return entry


def render_md(report: dict) -> str:
    lines = ["# Conversion-structure check (conversion-structure.v1)", "",
             f"{report['generatedAt']} — advisory-first wiring; hardFloor rows "
             "gate from birth", ""]
    for lane in report["lanes"]:
        head = f"## {lane['lane']}"
        if lane.get("note"):
            lines += [head + f" — SKIP ({lane['note']})", ""]
            continue
        if lane.get("error"):
            lines += [head + f" — ERROR ({lane['error']})", ""]
            continue
        warns = [r for r in lane["rows"] if not r["ok"]]
        floor_bad = [f for f in lane["hardFloor"] if not f["ok"]]
        verdict = "FAIL (hardFloor)" if floor_bad else \
            (f"PASS with {len(warns)} WARN(s)" if warns else "PASS")
        lines += [head + f" — {verdict} — campaign `{lane['campaign']}` "
                  f"({lane.get('binding')}, ground: {lane.get('ground')})", ""]
        seq = " -> ".join(f"{s['id']}[{','.join(s['families']) or '-'}]"
                          for s in lane["sequence"])
        lines += [f"sequence: {seq}", ""]
        lines.append("| kind | families | sev | verdict | detail |")
        lines.append("|---|---|---|---|---|")
        for r in lane["rows"]:
            lines.append(f"| {r['kind']} | {', '.join(r['families']) or '—'} | "
                         f"{r['severity'][:3]} | "
                         f"{'ok' if r['ok'] else 'WARN'} | {r['detail']} |")
        for f in lane["hardFloor"]:
            lines.append(f"| {f['rule']} | — | hard | "
                         f"{'ok' if f['ok'] else 'FAIL'} | {f['detail']} |")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lanes", nargs="+", help="lane dirs (composition.json)")
    ap.add_argument("--brand", type=Path, default=None,
                    help="brand run dir (report default location)")
    ap.add_argument("--campaign", default=None,
                    help="explicit campaign id (overrides brief binding)")
    ap.add_argument("--out", type=Path, default=None,
                    help="report dir (default <brand>/conversion-baseline)")
    ap.add_argument("--strict", action="store_true",
                    help="also exit 1 on failed required rows (graduation "
                         "lever; default gates hardFloor only)")
    args = ap.parse_args(argv)

    contracts = load_contracts()
    report = {"generatedAt": datetime.now(timezone.utc)
              .strftime("%Y-%m-%dT%H:%M:%SZ"), "lanes": []}
    hard = 0
    for lane in args.lanes:
        lane_dir = Path(lane)
        if lane_dir.is_file():
            lane_dir = lane_dir.parent
        entry = audit_lane(lane_dir, contracts, args.campaign)
        report["lanes"].append(entry)
        if entry.get("note"):
            print(f"[conversion] {lane_dir}: SKIP — {entry['note']}")
            continue
        if entry.get("error"):
            hard += 1
            print(f"[conversion] {lane_dir}: ERROR — {entry['error']}",
                  file=sys.stderr)
            continue
        floor_bad = [f for f in entry["hardFloor"] if not f["ok"]]
        warns = [r for r in entry["rows"] if not r["ok"]]
        req_warns = [r for r in warns if r["severity"] == "required"]
        hard += len(floor_bad)
        if args.strict:
            hard += len(req_warns)
        verdict = "FAIL" if floor_bad else "PASS"
        print(f"[conversion] {lane_dir}: {verdict} — campaign "
              f"{entry['campaign']} ({entry.get('binding')}), "
              f"{len(warns)} WARN(s) ({len(req_warns)} required), "
              f"{len(floor_bad)} hardFloor violation(s)")
        for r in warns:
            print(f"    WARN [{r['severity'][:3]}] {r['kind']} "
                  f"{','.join(r['families'])}: {r['detail']}")
        for f in floor_bad:
            print(f"    HARD {f['rule']}: {f['detail']}")

    out_dir = args.out or (args.brand / "conversion-baseline"
                           if args.brand else None)
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(json.dumps(report, indent=2))
        (out_dir / "report.md").write_text(render_md(report))
        print(f"[conversion] report: {out_dir / 'report.md'}")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
