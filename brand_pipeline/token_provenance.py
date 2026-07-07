#!/usr/bin/env python3
"""token_provenance.py — the `token-provenance` scanner (SPEC §D).

Prime directive: a composed page for brand X may not contain a visual value that is
not traceable to brand X's brand.yaml (or an allowlisted structural constant).

Scans the emitted HTML's <style> blocks MINUS the generated `<style id="tokens">`
block (layer 1 is the source of truth, not a violation). For every declaration of a
visual property whose value contains a raw literal (#hex / rgb[a]() / bare px/rem/em/
ms number / named weight / uppercase / cubic-bezier) that is NOT:
  1. equal (after normalization) to a value in the active brand's generated token
     index (a literal that matches the brand's own measured value IS traceable),
  2. inside a declaration whose value is purely var(...) references (fallback-less), or
  3. covered by a provenance allowlist comment —
it records a violation.

Severity (SPEC §D.4 + DECISIONS.md #3): colors / spacing-on-sections / radius /
font-size / weight / case / tracking / shadow / aspect = ERROR; durations + easing =
WARNING (reported, never gates).

Allowlist: `/* provenance: structural <id> — <why> */` immediately preceding a
declaration (or at the rule head, covering the whole rule) suppresses + counts;
`/* provenance: preview-chrome */` anywhere in a style block suppresses that whole
block (the gallery-chrome banner). Only these two provenance classes exist — there is
deliberately NO brand-specific escape hatch.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# ── property → category ───────────────────────────────────────────────────────────

_COLOR_PROPS = {
    "color", "background", "background-color", "border-color", "border-top-color",
    "border-right-color", "border-bottom-color", "border-left-color", "outline-color",
    "fill", "stroke", "caret-color", "column-rule-color",
}
# shorthands scanned for COLOR literals only (thickness/style are structural — C.2)
_BORDER_SHORTHANDS = {"border", "border-top", "border-right", "border-bottom",
                      "border-left", "outline", "column-rule"}
_TYPE_PROPS = {"font-size", "font-weight", "letter-spacing", "text-transform"}
_RADIUS_PROPS = {"border-radius", "border-top-left-radius", "border-top-right-radius",
                 "border-bottom-left-radius", "border-bottom-right-radius"}
_SHADOW_PROPS = {"box-shadow", "text-shadow"}
_SPACING_PROPS = {"padding", "padding-top", "padding-right", "padding-bottom",
                  "padding-left", "margin", "margin-top", "margin-right",
                  "margin-bottom", "margin-left", "margin-block-start",
                  "margin-block-end", "margin-inline", "padding-block", "padding-inline",
                  "gap", "row-gap", "column-gap"}
_MOTION_PROPS = {"transition", "transition-duration", "transition-delay",
                 "transition-timing-function", "animation", "animation-duration",
                 "animation-timing-function", "animation-delay"}
_ASPECT_PROPS = {"aspect-ratio"}

# spacing gates only on SECTION-LEVEL selectors (SPEC §D.2); micro-gaps inside
# components are CR-8 "opportunistic", not gate errors.
_SECTION_SEL_RE = re.compile(r"\.cs-section\b|\.cs-spacer\b|\.[a-z0-9-]*-sec\b")

_STYLE_BLOCK_RE = re.compile(r"<style([^>]*)>(.*?)</style>", re.S | re.I)
_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_DECL_RE = re.compile(r"(?:^|;)\s*(-{0,2}[a-zA-Z][a-zA-Z0-9-]*)\s*:\s*([^;{}]+)")

_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_FUNC_COLOR_RE = re.compile(r"\b(rgba?|hsla?)\(([^)]*)\)")
_LEN_RE = re.compile(r"(?<![a-zA-Z0-9_.-])(-?\d*\.?\d+)(px|rem|em)(?![a-zA-Z%])")
_DUR_RE = re.compile(r"(?<![a-zA-Z0-9_.-])(\d*\.?\d+)(ms|s)\b")
_WEIGHT_RE = re.compile(r"(?<![\d.#-])([1-9]00)\b|\bbold\b")
_CASE_RE = re.compile(r"\b(uppercase|capitalize)\b")
_EASE_RE = re.compile(r"cubic-bezier\([^)]*\)|\bease(?:-in-out|-in|-out)?\b|\bsteps\([^)]*\)")
_ASPECT_LIT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\b")


# ── normalization ──────────────────────────────────────────────────────────────────

def _parse_color(s: str):
    """→ (r, g, b, a) or None. Handles #rgb/#rrggbb/#rrggbbaa + rgb[a]()/int args."""
    s = s.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3,8})", s)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) == 4:
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            h += "ff"
        if len(h) != 8:
            return None
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16),
                round(int(h[6:8], 16) / 255, 3))
    m = re.fullmatch(r"rgba?\(([^)]*)\)", s)
    if m:
        parts = [p.strip() for p in re.split(r"[,/ ]+", m.group(1)) if p.strip()]
        if len(parts) < 3:
            return None
        try:
            rgb = [round(float(p[:-1]) * 2.55) if p.endswith("%") else int(round(float(p)))
                   for p in parts[:3]]
            a = 1.0
            if len(parts) >= 4:
                a = float(parts[3][:-1]) / 100 if parts[3].endswith("%") else float(parts[3])
            return (rgb[0], rgb[1], rgb[2], round(a, 3))
        except ValueError:
            return None
    return None


def _norm_len(num: str, unit: str):
    try:
        return (round(float(num), 4), unit)
    except ValueError:
        return None


def _norm_ms(num: str, unit: str):
    try:
        v = float(num)
        return round(v * 1000 if unit == "s" else v, 3)
    except ValueError:
        return None


def _norm_ease(s: str) -> str:
    return re.sub(r"\s+", "", s.lower())


def _norm_aspect(a: str, b: str) -> str:
    try:
        return f"{float(a):g}/{float(b):g}"
    except ValueError:
        return f"{a}/{b}"


class _Index:
    """Pre-normalized lookup tables for ONE brand's token index."""

    def __init__(self, index: dict[str, str]):
        self.colors: dict[tuple, str] = {}
        self.lengths: dict[tuple, str] = {}
        self.weights: dict[int, str] = {}
        self.cases: set[str] = set()
        self.durations: dict[float, str] = {}
        self.eases: dict[str, str] = {}
        self.aspects: dict[str, str] = {}
        for tok, raw in (index or {}).items():
            v = str(raw).strip()
            c = _parse_color(v)
            if c:
                self.colors.setdefault(c, tok)
                continue
            for m in _LEN_RE.finditer(v):
                n = _norm_len(m.group(1), m.group(2))
                if n:
                    self.lengths.setdefault(n, tok)
            m = re.fullmatch(r"([1-9]00)", v)
            if m:
                self.weights.setdefault(int(m.group(1)), tok)
            if v in ("uppercase", "capitalize", "none"):
                self.cases.add(v)
            m = re.fullmatch(r"(\d*\.?\d+)(ms|s)", v)
            if m:
                d = _norm_ms(m.group(1), m.group(2))
                if d is not None:
                    self.durations.setdefault(d, tok)
            if "cubic-bezier" in v or v in ("ease", "ease-in", "ease-out", "ease-in-out",
                                            "linear"):
                self.eases.setdefault(_norm_ease(v), tok)
            m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", v)
            if m:
                self.aspects.setdefault(_norm_aspect(m.group(1), m.group(2)), tok)

    def nearest_color(self, c: tuple):
        best, tok = None, None
        for k, t in self.colors.items():
            d = sum((a - b) ** 2 for a, b in zip(k[:3], c[:3])) + (abs(k[3] - c[3]) * 255) ** 2
            if best is None or d < best:
                best, tok = d, t
        return tok

    def nearest_length(self, n: tuple):
        cands = [(abs(k[0] - n[0]), k, t) for k, t in self.lengths.items() if k[1] == n[1]]
        if not cands:
            return None
        _, k, tok = min(cands)
        return tok


# ── the scanner ─────────────────────────────────────────────────────────────────────

def _iter_rules(css: str, start: int, end: int):
    """Yield (selector, sel_span_start, body_start, body_end); recurses into at-rules."""
    i = start
    sel_start = start
    while i < end:
        ch = css[i]
        if ch == "}":
            i += 1
            sel_start = i
            continue
        if ch == "{":
            sel = css[sel_start:i].strip()
            depth, j = 1, i + 1
            while j < end and depth:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                j += 1
            body_start, body_end = i + 1, j - 1
            if sel.startswith("@") and "{" in css[body_start:body_end]:
                yield from _iter_rules(css, body_start, body_end)
            elif not sel.startswith("@"):
                yield sel, sel_start, body_start, body_end
            i = j
            sel_start = j
        else:
            i += 1


def _mask_var_refs(value: str) -> str:
    """Blank pure var(--x) references (their NAMES must not be scanned as literals —
    e.g. --c-motion-ease contains 'ease') while UNWRAPPING var(--x, fallback) so the
    fallback literal stays visible: fallback literals are provenance violations."""
    out = re.sub(r"var\(\s*--[a-zA-Z0-9-]+\s*\)", " ", value)
    out = re.sub(r"var\(\s*--[a-zA-Z0-9-]+\s*,", "(", out)
    return out


def _strip_traceable(value: str, prop: str, idx: _Index):
    """Return the list of (category, literal, normalized) UNTRACEABLE literals in one
    declaration value, given the active-brand index."""
    value = _mask_var_refs(value)
    out = []
    scan_colors = prop in _COLOR_PROPS or prop in _BORDER_SHORTHANDS or prop in _SHADOW_PROPS
    if scan_colors:
        for m in _HEX_RE.finditer(value):
            c = _parse_color(m.group(0))
            if c and c not in idx.colors:
                out.append(("color", m.group(0), c))
        for m in _FUNC_COLOR_RE.finditer(value):
            c = _parse_color(m.group(0))
            if c and c not in idx.colors:
                out.append(("color", m.group(0), c))
    if prop in ("font-size", "letter-spacing") or prop in _RADIUS_PROPS \
            or prop in _SPACING_PROPS or prop in _SHADOW_PROPS:
        cat = ("radius" if prop in _RADIUS_PROPS else
               "shadow" if prop in _SHADOW_PROPS else
               "spacing" if prop in _SPACING_PROPS else "type")
        for m in _LEN_RE.finditer(value):
            n = _norm_len(m.group(1), m.group(2))
            if n and n[0] != 0 and n not in idx.lengths:
                out.append((cat, m.group(0), n))
    if prop == "font-weight":
        for m in _WEIGHT_RE.finditer(value):
            w = 700 if m.group(0) == "bold" else int(m.group(1))
            if w not in idx.weights:
                out.append(("weight", m.group(0), w))
    if prop == "text-transform":
        for m in _CASE_RE.finditer(value):
            if m.group(0) not in idx.cases:
                out.append(("case", m.group(0), m.group(0)))
    if prop in _MOTION_PROPS:
        for m in _DUR_RE.finditer(value):
            d = _norm_ms(m.group(1), m.group(2))
            if d is not None and d != 0 and d not in idx.durations:
                out.append(("duration", m.group(0), d))
        for m in _EASE_RE.finditer(value):
            e = _norm_ease(m.group(0))
            if e not in idx.eases:
                out.append(("easing", m.group(0), e))
    if prop in _ASPECT_PROPS:
        for m in _ASPECT_LIT_RE.finditer(value):
            a = _norm_aspect(m.group(1), m.group(2))
            if a not in idx.aspects:
                out.append(("aspect", m.group(0), a))
    return out


def _suggest(cat, literal, norm, idx: _Index, brand: str,
             foreign: dict[str, _Index] | None) -> str:
    tip = f"no {brand or 'brand'} token resolves to this value"
    if cat == "color":
        near = idx.nearest_color(norm)
        if near:
            tip = (f"no {brand or 'brand'} token resolves to this value; "
                   f"nearest color token: {near}")
    elif cat in ("type", "spacing", "radius", "shadow"):
        near = idx.nearest_length(norm)
        if near:
            tip = (f"no {brand or 'brand'} token resolves to this value; "
                   f"nearest token: {near}")
    elif cat == "weight" and idx.weights:
        near = min(idx.weights, key=lambda w: abs(w - norm))
        tip = f"use var({idx.weights[near]}) (resolves to {near} for {brand})"
    elif cat == "case" and idx.cases:
        tip = f"case tiers for {brand} resolve to {sorted(idx.cases)} — use var(--c-case-*)"
    elif cat == "duration" and idx.durations:
        near = min(idx.durations, key=lambda d: abs(d - norm))
        tip = f"use var({idx.durations[near]}) (resolves to {near:g}ms for {brand})"
    elif cat == "easing" and idx.eases:
        tok = next(iter(idx.eases.values()))
        tip = f"use var({tok})"
    elif cat == "aspect" and idx.aspects:
        tip = f"aspect palette for {brand}: {sorted(idx.aspects)} — use var(--c-aspect-*)"
    for fbrand, fidx in (foreign or {}).items():
        hit = None
        if cat == "color" and norm in fidx.colors:
            hit = fidx.colors[norm]
        elif cat in ("type", "spacing", "radius", "shadow") and norm in fidx.lengths:
            hit = fidx.lengths[norm]
        elif cat == "weight" and norm in fidx.weights:
            hit = fidx.weights[norm]
        elif cat == "duration" and norm in fidx.durations:
            hit = fidx.durations[norm]
        elif cat == "easing" and norm in fidx.eases:
            hit = fidx.eases[norm]
        elif cat == "aspect" and norm in fidx.aspects:
            hit = fidx.aspects[norm]
        if hit:
            tip += f" [foreign-brand value: matches {fbrand} {hit}]"
            break
    return tip


_WARN_CATS = ("duration", "easing")


def check_token_provenance(html: str, index: dict[str, str], *, brand: str = "",
                           foreign_indexes: dict[str, dict] | None = None,
                           max_items: int = 8) -> dict:
    """Scan one rendered document. Returns {passed, errors, warnings, allowlisted,
    detail} — ``passed`` is True when there are zero ERROR-severity violations
    (duration/easing are warnings per DECISIONS.md #3). ``detail`` is machine-stable,
    pipe-free (the report row wraps it in `| id | FAIL | detail |`)."""
    idx = _Index(index)
    foreign = {b: _Index(i) for b, i in (foreign_indexes or {}).items()}
    errors: list[str] = []
    warnings: list[str] = []
    allowlisted = 0
    for battrs, bcss in _STYLE_BLOCK_RE.findall(html):
        if re.search(r'id\s*=\s*"tokens"', battrs):
            continue  # the generated layer-1 block is the source of truth
        if "provenance: preview-chrome" in bcss:
            allowlisted += 1
            continue
        comments = [(m.start(), m.group(0)) for m in _COMMENT_RE.finditer(bcss)]
        structural = [pos for pos, text in comments if "provenance: structural" in text]
        stripped = _COMMENT_RE.sub(lambda m: " " * len(m.group(0)), bcss)
        for sel, sel_start, body_start, body_end in _iter_rules(stripped, 0, len(stripped)):
            body = stripped[body_start:body_end]
            for dm in _DECL_RE.finditer(body):
                prop = dm.group(1).lower()
                if prop.startswith("--"):
                    continue  # custom properties = layer 2; purity enforced by unit tests
                value = dm.group(2).strip()
                known = (prop in _COLOR_PROPS or prop in _BORDER_SHORTHANDS
                         or prop in _TYPE_PROPS or prop in _RADIUS_PROPS
                         or prop in _SHADOW_PROPS or prop in _SPACING_PROPS
                         or prop in _MOTION_PROPS or prop in _ASPECT_PROPS)
                if not known:
                    continue
                if prop in _SPACING_PROPS and not _SECTION_SEL_RE.search(sel):
                    continue
                hits = _strip_traceable(value, prop, idx)
                if not hits:
                    continue
                decl_pos = body_start + dm.start(1)  # property-name position
                covered = any(sel_start <= cpos <= decl_pos for cpos in structural)
                if covered:
                    allowlisted += len(hits)
                    continue
                sel_short = re.sub(r"\s+", " ", sel)[:60]
                for cat, literal, norm in hits:
                    item = (f"{sel_short}{{{prop}}}: raw `{literal}` — "
                            f"{_suggest(cat, literal, norm, idx, brand, foreign)}")
                    (warnings if cat in _WARN_CATS else errors).append(item)
    def _cap(items):
        extra = f" (+{len(items) - max_items} more)" if len(items) > max_items else ""
        return "; ".join(items[:max_items]) + extra
    parts = []
    if errors:
        parts.append(_cap(errors))
    if warnings:
        parts.append("warnings (duration/easing, non-gating): " + _cap(warnings))
    parts.append(f"allowlisted: {allowlisted}")
    detail = "; ".join(parts) if (errors or warnings) else \
        f"all emitted visual values trace to the {brand or 'brand'} token index; " \
        f"allowlisted: {allowlisted}"
    return {"passed": not errors, "errors": errors, "warnings": warnings,
            "allowlisted": allowlisted, "detail": detail.replace("|", "/")}


# ── index loading helpers (gate-side) ───────────────────────────────────────────────

def load_manifest_index(render_dir) -> dict | None:
    """The active render's token index from tokens.manifest.json (SPEC §D.2 — the
    checker never re-parses brand.yaml when a manifest is present)."""
    p = Path(render_dir) / "tokens.manifest.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        return data.get("index") or None
    except Exception:
        return None


def build_index_from_doc(doc) -> dict:
    """Fallback for manifest-less (legacy) renders: build the index directly from the
    already-loaded brand doc. Never raises — a token-incomplete brand still yields a
    partial index (the scan is advisory for legacy pages)."""
    import tokens_css
    try:
        lines, bp, index, missing, disabled = tokens_css.emit_layer1(doc)
        return index
    except Exception:
        return {}


def foreign_brand_indexes(runs_root, active_brand: str) -> dict[str, dict]:
    """Token indexes of every OTHER brand under runs/ (the DNA-leak smoking-gun list).
    Defensive: unreadable/token-incomplete brands are skipped silently."""
    import yaml
    out: dict[str, dict] = {}
    root = Path(runs_root)
    if not root.is_dir():
        return out
    for by in sorted(root.glob("*/brand/brand.yaml")):
        try:
            doc = yaml.safe_load(by.read_text()) or {}
            name = (doc.get("brand") or {}).get("name") or by.parent.parent.name
            if name.strip().lower() == (active_brand or "").strip().lower():
                continue
            idx = build_index_from_doc(doc)
            if idx:
                out[name] = idx
        except Exception:
            continue
    return out
