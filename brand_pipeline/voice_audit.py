#!/usr/bin/env python3
"""Voice auditor — generated copy metrics vs the brand's STRUCTURED VOICE FACTS
(pass1 2026-07; data: <brand>/voice-facts.yaml, schema voice-facts.v1).

ADVISORY severity to start (exit 0, findings printed as WARN) — hard gating only
under --strict, per the staged-severity doctrine. Brands without voice-facts.yaml
skip cleanly (fact-gated).

What it measures, per lane (static HTML parse — copy is static; CSS-owned casing
like the eyebrow text-transform is NOT audited here, the type token owns it):
  sentence-length — mean + p90 words across section body/heading copy vs the
                    facts' gate budgets (measured envelope + documented headroom)
  exclamations    — count vs the measured ban (both brands: 0)
  banned-hype     — lexicon hits (words the captured corpus never uses)
  heading-casing  — sentence-case rule with the brand-term allowlist (title-cased
                    words beyond the allowlist + threshold flag)

Chrome subtrees (nav / footer / mega / utility banner) are EXCLUDED — chrome copy
is harvested source text, not generated copy.

Usage (repo root):
  ./venv/bin/python -m brand_pipeline.voice_audit <lanes...> --brand runs/<brand>/brand [--strict]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import yaml

CHROME_CLASS_RX = re.compile(
    r"\b(cs-nav|c-foot|cs-mega|cs-utility-banner|cs-navlinks|spec-|sb-)")


class _CopyExtract(HTMLParser):
    """Visible section copy by role: headings (h1-h3/.c-heading), body (p),
    eyebrows (.c-eyebrow), CTAs (.c-button labels). Skips chrome subtrees and
    script/style. Text outside [id^=sec-] counts only when no sections exist."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[dict] = []
        self.headings: list[str] = []
        self.bodies: list[str] = []
        self.eyebrows: list[str] = []
        self.ctas: list[str] = []
        self.has_sections = False
        self._buf: list[str] | None = None
        self._buf_kind: str | None = None
        self._depth_at_open = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        frame = {"tag": tag, "cls": cls,
                 "chrome": bool(CHROME_CLASS_RX.search(cls)) or tag in ("nav", "footer"),
                 "skip": tag in ("script", "style", "svg", "noscript")}
        if (a.get("id") or "").startswith("sec-"):
            self.has_sections = True
            frame["section"] = True
        self.stack.append(frame)
        if self._buf is not None or self._in_chrome() or self._in_skip():
            return
        kind = None
        if tag in ("h1", "h2", "h3") or "c-heading" in cls:
            kind = "headings"
        elif "c-eyebrow" in cls:
            kind = "eyebrows"
        elif "c-button" in cls and "c-arrow-link" not in cls:
            kind = "ctas"
        elif tag == "p":
            kind = "bodies"
        if kind:
            self._buf, self._buf_kind = [], kind
            self._depth_at_open = len(self.stack)

    def handle_endtag(self, tag):
        if self._buf is not None and len(self.stack) <= self._depth_at_open:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                getattr(self, self._buf_kind).append(text)
            self._buf = self._buf_kind = None
        while self.stack and self.stack[-1]["tag"] != tag:
            self.stack.pop()
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self._buf is not None and not self._in_skip():
            self._buf.append(data)

    def _in_chrome(self):
        return any(f.get("chrome") for f in self.stack)

    def _in_skip(self):
        return any(f.get("skip") for f in self.stack)


def extract_copy(html_text: str) -> dict:
    p = _CopyExtract()
    p.feed(html_text)
    return {"headings": p.headings, "bodies": p.bodies,
            "eyebrows": p.eyebrows, "ctas": p.ctas}


def _sentences(texts: list[str]) -> list[str]:
    out = []
    for t in texts:
        for s in re.split(r"(?<=[.!?])\s+", t.strip()):
            s = s.strip()
            if s and len(s.split()) >= 2:
                out.append(s)
    return out


def _title_words(heading: str, brand_terms: set[str]) -> list[str]:
    """Mid-heading capitalized words not covered by the brand-term allowlist,
    numerals, or acronyms — the sentence-case violation candidates. Multi-word
    brand terms ('Small Business Bundle', 'Marketing Hub') strip as PHRASES
    first: product names are proper nouns, not casing choices."""
    for phrase in sorted((t for t in brand_terms if " " in t), key=len, reverse=True):
        heading = heading.replace(phrase, " ")
    words = heading.split()
    out = []
    for w in words[1:]:
        core = w.strip(".,!?—–-:;()'\"’®™+")
        if not core or not core[:1].isupper():
            continue
        if core.isupper() or any(ch.isdigit() for ch in core):
            continue  # acronyms + numerals are not casing choices
        if core in brand_terms or core.rstrip("s’'") in brand_terms:
            continue
        out.append(core)
    return out


def audit_copy(copy: dict, facts: dict) -> list[dict]:
    rows: list[dict] = []
    sens = _sentences(copy["bodies"] + copy["headings"])
    lens = sorted(len(s.split()) for s in sens)

    gate = ((facts.get("sentences") or {}).get("gate") or {})
    if lens and gate:
        mean = sum(lens) / len(lens)
        p90 = lens[max(0, int(round(0.9 * len(lens))) - 1)]
        mean_max = float(gate.get("meanWordsMax", 1e9))
        p90_max = float(gate.get("p90WordsMax", 1e9))
        # the MEAN budget describes a habit — over a tiny sample (a hero lane
        # with 2-3 sentences) it's noise, so it binds only at n>=4; the p90
        # cap still bounds every run-on regardless of sample size.
        mean_ok = mean <= mean_max or len(lens) < 4
        ok = mean_ok and p90 <= p90_max
        rows.append({"check": "sentence-length", "ok": ok,
                     "detail": f"mean {mean:.1f}w (max {mean_max:g}"
                               f"{', n<4 advisory-only' if len(lens) < 4 else ''}), "
                               f"p90 {p90}w (max {p90_max:g}), "
                               f"{len(sens)} sentences"})

    excl_gate = (((facts.get("punctuation") or {}).get("exclamations") or {})
                 .get("gate") or {})
    if excl_gate:
        n = sum(t.count("!") for t in copy["headings"] + copy["bodies"] + copy["ctas"])
        cap = int(excl_gate.get("max", 0))
        rows.append({"check": "exclamations", "ok": n <= cap,
                     "detail": f"{n} exclamation mark(s) (max {cap}) — the "
                               "measured corpus has none"})

    lexicon = [str(w).lower() for w in ((facts.get("bannedHype") or {})
                                        .get("lexicon") or [])]
    if lexicon:
        corpus = " ".join(copy["headings"] + copy["bodies"] + copy["ctas"]).lower()
        hits = sorted({w for w in lexicon
                       if re.search(rf"\b{re.escape(w)}\b", corpus)})
        rows.append({"check": "banned-hype", "ok": not hits,
                     "detail": (f"hype lexicon hit(s): {', '.join(hits)}" if hits
                                else f"0 hits across {len(lexicon)}-word ban list")})

    casing = ((facts.get("casing") or {}).get("headings") or {})
    if str(casing.get("rule") or "") == "sentence" and copy["headings"]:
        terms = {str(t) for t in (casing.get("brandTerms") or [])}
        bad = []
        for h in copy["headings"]:
            stray = _title_words(h, terms)
            # one stray capital is usually a proper noun the allowlist missed;
            # a run of them is a TITLE-CASED heading — the actual violation shape
            if len(stray) >= 2 and len(stray) >= 0.4 * max(1, len(h.split()) - 1):
                bad.append((h, stray))
        rows.append({"check": "heading-casing", "ok": not bad,
                     "detail": ("; ".join(f"'{h[:50]}' (title-cased: "
                                          f"{', '.join(s[:4])})" for h, s in bad[:3])
                                if bad else
                                f"{len(copy['headings'])} heading(s) sentence-case "
                                "(brand terms allowed)")})
    return rows


def run_audit(lane_paths: list[Path], brand_dir: Path,
              out_dir: Path | None) -> dict:
    facts_path = brand_dir / "voice-facts.yaml"
    report = {"generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "brandDir": str(brand_dir), "lanes": []}
    if not facts_path.exists():
        report["note"] = "no voice-facts.yaml — nothing to audit (fact-gated skip)"
        return report
    facts = yaml.safe_load(facts_path.read_text()) or {}
    if facts.get("schema") != "voice-facts.v1":
        report["note"] = f"unknown voice facts schema {facts.get('schema')!r} — skip"
        return report

    for html in lane_paths:
        lane = str(html.parent.relative_to(brand_dir)) \
            if brand_dir in html.parents else str(html)
        entry = {"lane": lane, "html": str(html)}
        if not html.exists():
            entry["error"] = "file not found"
        else:
            copy = extract_copy(html.read_text())
            entry["copyCounts"] = {k: len(v) for k, v in copy.items()}
            entry["checks"] = audit_copy(copy, facts)
            entry["ok"] = all(r["ok"] for r in entry["checks"])
        report["lanes"].append(entry)

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lanes", nargs="+")
    ap.add_argument("--brand", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None,
                    help="report dir (default <brand>/voice-baseline)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on findings (default: advisory — exit 0)")
    args = ap.parse_args(argv)
    paths = [(Path(l) / "index.html") if Path(l).is_dir() else Path(l)
             for l in args.lanes]
    out_dir = args.out or (args.brand / "voice-baseline")
    report = run_audit(paths, args.brand, out_dir)

    fails = 0
    for lane in report["lanes"]:
        if lane.get("error"):
            fails += 1
            print(f"[voice-audit] {lane['lane']}: ERROR {lane['error']}",
                  file=sys.stderr)
            continue
        bad = [r for r in lane["checks"] if not r["ok"]]
        fails += len(bad)
        if bad:
            for r in bad:
                print(f"[voice-audit] {lane['lane']}: WARN {r['check']} — {r['detail']}")
        else:
            checked = ", ".join(r["check"] for r in lane["checks"])
            print(f"[voice-audit] {lane['lane']}: PASS ({checked})")
    if report.get("note"):
        print(f"[voice-audit] {report['note']}")
    return 1 if (args.strict and fails) else 0


if __name__ == "__main__":
    sys.exit(main())
