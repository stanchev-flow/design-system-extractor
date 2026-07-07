#!/usr/bin/env python3
"""mine_motion.py — per-selector MOTION audit from already-mined CSS evidence.

Reads ``css-rules.json`` (the mine-css stage's raw rule corpus, which records
@keyframes as their own rows) and derives the motion fidelity contract the
Claude-Design-style kits carry: every transition / animation rule attributed to
its source selector, with property / duration / easing / delay parsed out, plus
the keyframes inventory, a resolved custom-property table for var()-driven
timings, and duration/easing censuses. Brand-agnostic: nothing here names a
brand, a section, or a hue.

Output ``motion-audit.json``:
  transitions[]   {file, media, selector, transitions:[{property,duration,easing,delay,raw}]}
  animations[]    {file, media, selector, animations:[{name,duration,easing,delay,extras,raw}]}
  keyframes[]     {file, name, frames}
  motionVars      {--custom-prop: value} for props whose name/value smells of timing
  durationCensus  {"200ms": count, ...}   (var() references resolved when possible)
  easingCensus    {"ease": count, ...}
  jsTimingNotes[] EMPTY — the authoring agent records JS-driven timings here
                  (autoplay intervals, slide durations) where CSS is silent.

The downstream authoring stage (spec/layout-analyst-skill.md) derives
``brand.yaml tokens.motion`` — the duration ladder, easings and named signature
moves — from this file; validator C13 enforces the result.

Usage:
    ./venv/bin/python tools/extract/mine_motion.py \
        --evidence runs/<brand>/brand/evidence/ [--out motion-audit.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

SCHEMA = "motion-audit.v1"

_TIME_RE = re.compile(r"^-?(?:\d+\.?\d*|\.\d+)m?s$")
# easing keywords + functional forms the shorthand can carry
# (incl. the modern `linear(0, 0.006 2.2%, …)` stop-list spring syntax)
_EASING_RE = re.compile(
    r"^(?:ease(?:-in|-out|-in-out)?|linear|step-start|step-end"
    r"|cubic-bezier\([^)]*\)|steps\([^)]*\)|linear\([^)]*\)|var\(--[^)]*\))$")
_VAR_RE = re.compile(r"var\((--[a-zA-Z0-9-_]+)(?:\s*,\s*([^)]+))?\)")
_DECL_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;]+)")
_CUSTOM_PROP_RE = re.compile(r"(--[a-zA-Z0-9-_]+)\s*:\s*([^;}]+)")
# custom props that plausibly carry timing/easing data
_MOTION_VAR_NAME_RE = re.compile(
    r"duration|easing|delay|transition|speed|timing|travel", re.I)

_ANIM_KEYWORDS = {
    "infinite", "normal", "reverse", "alternate", "alternate-reverse",
    "none", "forwards", "backwards", "both", "running", "paused",
}


def _split_top_level(value: str) -> list[str]:
    """Split a shorthand list on commas that are not inside parentheses."""
    parts, depth, buf = [], 0, ""
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    return parts


def _tokenize(chunk: str) -> list[str]:
    """Whitespace-split respecting parentheses (cubic-bezier(.4, 0, .2, 1))."""
    toks, depth, buf = [], 0, ""
    for ch in chunk:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch.isspace() and depth == 0:
            if buf:
                toks.append(buf)
            buf = ""
        else:
            buf += ch
    if buf:
        toks.append(buf)
    return toks


def _is_time(tok: str) -> bool:
    return bool(_TIME_RE.match(tok)) or (
        tok.startswith("var(") and bool(re.search(r"duration|delay|speed|time", tok, re.I)))


def _is_easing(tok: str) -> bool:
    if _EASING_RE.match(tok) and not _is_time(tok):
        # a var() counts as easing only when its NAME smells of easing
        if tok.startswith("var("):
            return bool(re.search(r"eas|timing|bezier", tok, re.I))
        return True
    return False


def _clean_token(tok: str) -> str:
    tok = tok.strip()
    if tok.endswith("!important"):
        tok = tok[:-len("!important")].strip()
    return tok


def parse_transition_value(value: str) -> list[dict]:
    """One entry per comma-separated transition: property, duration, easing, delay."""
    out = []
    for chunk in _split_top_level(value):
        toks = _tokenize(chunk)
        if not toks:
            continue
        entry = {"property": None, "duration": None, "easing": None,
                 "delay": None, "raw": chunk}
        times = []
        unresolved_vars = []
        for tok in toks:
            low = _clean_token(tok)
            if not low or low == "!important":
                continue
            if _is_time(low):
                times.append(low)
            elif _is_easing(low):
                entry["easing"] = entry["easing"] or low
            elif low.startswith("var("):
                # a var() whose NAME doesn't betray its role — assign positionally
                # below (shorthand grammar: duration comes before easing/delay)
                unresolved_vars.append(low)
            elif entry["property"] is None:
                entry["property"] = low
        if times:
            entry["duration"] = times[0]
        if len(times) > 1:
            entry["delay"] = times[1]
        for v in unresolved_vars:
            if entry["duration"] is None:
                entry["duration"] = v
            elif entry["easing"] is None:
                entry["easing"] = v
            elif entry["delay"] is None:
                entry["delay"] = v
        out.append(entry)
    return out


def parse_animation_value(value: str) -> list[dict]:
    """One entry per comma-separated animation: name, duration, easing, delay, extras."""
    out = []
    for chunk in _split_top_level(value):
        toks = _tokenize(chunk)
        if not toks:
            continue
        entry = {"name": None, "duration": None, "easing": None,
                 "delay": None, "extras": [], "raw": chunk}
        times = []
        for tok in toks:
            low = _clean_token(tok)
            if not low or low == "!important":
                continue
            if _is_time(low):
                times.append(low)
            elif _is_easing(low):
                entry["easing"] = entry["easing"] or low
            elif low in _ANIM_KEYWORDS or low.isdigit():
                entry["extras"].append(low)
            elif entry["name"] is None:
                entry["name"] = low
            else:
                entry["extras"].append(low)
        if times:
            entry["duration"] = times[0]
        if len(times) > 1:
            entry["delay"] = times[1]
        out.append(entry)
    return out


def _norm_ms(tok: str | None) -> str | None:
    """'0.3s' / '.3s' / '300ms' → '300ms' (census normalization only)."""
    if not tok or not _TIME_RE.match(tok):
        return tok
    try:
        if tok.endswith("ms"):
            v = float(tok[:-2])
        else:
            v = float(tok[:-1]) * 1000.0
    except ValueError:
        return tok
    return f"{int(v) if v == int(v) else v}ms"


def collect_motion_vars(rows: list[dict]) -> dict:
    """Custom-property definitions whose name or value smells of timing/easing —
    the table that resolves var()-driven durations (e.g. design-system button
    timing variables)."""
    out: dict[str, str] = {}
    for r in rows:
        if r.get("kind") != "rule":
            continue
        for name, val in _CUSTOM_PROP_RE.findall(r.get("decls", "")):
            val = val.strip()
            if _MOTION_VAR_NAME_RE.search(name) or _TIME_RE.match(val) \
                    or "cubic-bezier" in val:
                # first definition wins (base scope tends to come first);
                # scope-specific redefinitions are appended with the selector.
                if name not in out:
                    out[name] = val
                elif out[name] != val and f"{name}@" not in out:
                    out[f"{name}@{r.get('selector', '')[:60]}"] = val
    return out


def resolve_var(tok: str | None, motion_vars: dict, depth: int = 0) -> str | None:
    """Best-effort var(--x[, fallback]) resolution against the mined var table."""
    if not tok or depth > 4 or not tok.startswith("var("):
        return tok
    m = _VAR_RE.match(tok)
    if not m:
        return tok
    name, fallback = m.group(1), m.group(2)
    val = motion_vars.get(name)
    if val is None:
        return resolve_var(fallback.strip(), motion_vars, depth + 1) if fallback else tok
    return resolve_var(val.strip(), motion_vars, depth + 1)


def build_audit(rules_doc: dict) -> dict:
    rows = rules_doc.get("rules") or []
    motion_vars = collect_motion_vars(rows)
    transitions, animations, keyframes = [], [], []
    dur_census: Counter = Counter()
    ease_census: Counter = Counter()

    for r in rows:
        if r.get("kind") == "keyframes":
            name = re.sub(r"^@(?:-webkit-)?keyframes\s+", "", r.get("selector", "")).strip()
            keyframes.append({"file": r.get("file"), "name": name,
                              "frames": r.get("decls", "")})
            continue
        decls = {}
        for prop, val in _DECL_RE.findall(r.get("decls", "")):
            decls[prop.lower()] = val.strip()
        row_tr, row_an = [], []
        for prop, val in decls.items():
            if prop in ("transition", "-webkit-transition"):
                row_tr.extend(parse_transition_value(val))
            elif prop == "transition-duration":
                row_tr.append({"property": "(shorthand-split)", "duration": val,
                               "easing": None, "delay": None, "raw": f"{prop}:{val}"})
            elif prop in ("animation", "-webkit-animation"):
                row_an.extend(parse_animation_value(val))
        if row_tr:
            transitions.append({"file": r.get("file"), "media": r.get("media", ""),
                                "selector": r.get("selector", "")[:200],
                                "transitions": row_tr})
        if row_an:
            animations.append({"file": r.get("file"), "media": r.get("media", ""),
                               "selector": r.get("selector", "")[:200],
                               "animations": row_an})
        for e in row_tr + row_an:
            dur = resolve_var(e.get("duration"), motion_vars)
            ease = resolve_var(e.get("easing"), motion_vars)
            if dur and _TIME_RE.match(dur):
                dur_census[_norm_ms(dur)] += 1
            if ease and not ease.startswith("var("):
                ease_census[ease] += 1

    return {
        "schemaVersion": SCHEMA,
        "sourceRuleCount": len(rows),
        "transitions": transitions,
        "animations": animations,
        "keyframes": keyframes,
        "motionVars": motion_vars,
        "durationCensus": dict(dur_census.most_common(40)),
        "easingCensus": dict(ease_census.most_common(20)),
        "jsTimingNotes": [],
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence", type=Path, required=True,
                    help="evidence dir containing css-rules.json (mine-css output)")
    ap.add_argument("--out", type=Path,
                    help="output path (default: <evidence>/motion-audit.json)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    rules_path = args.evidence / "css-rules.json"
    if not rules_path.is_file():
        raise SystemExit(f"{rules_path} not found — run the mine-css stage first")
    rules_doc = json.loads(rules_path.read_text())
    audit = build_audit(rules_doc)
    out = args.out or (args.evidence / "motion-audit.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    # jsTimingNotes are AUTHORED evidence (JS-driven timings CSS cannot see) —
    # carry them forward across re-mines instead of wiping them.
    if out.is_file():
        try:
            prior = json.loads(out.read_text())
            if prior.get("jsTimingNotes"):
                audit["jsTimingNotes"] = prior["jsTimingNotes"]
        except (json.JSONDecodeError, OSError):
            pass
    out.write_text(json.dumps(audit, indent=1) + "\n")
    print(f"[done] motion-audit: {len(audit['transitions'])} transition rules, "
          f"{len(audit['animations'])} animation rules, "
          f"{len(audit['keyframes'])} keyframes, "
          f"{len(audit['motionVars'])} motion vars -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
