#!/usr/bin/env python3
"""Signature auditor — verifies the brand's declared SIGNATURES on rendered lanes
(pass1 2026-07; data: brand.yaml `signatures:` per brand-schema §4.7).

Two gates ride this tool:
  signature_check — every declared signature holds on every gated page
                    (present where mode=always, absent where mode=never);
  accent_budget   — an accent-scope signature carrying check.maxPaintSharePct is
                    additionally budget-audited: the accent family's painted share
                    of the page (computed-paint classifier) must stay inside it.

Palette comes from the SIGNATURE (brand data), never from this file — the checks
are generic per `kind`; brands supply the values. Pages without a `signatures:`
block skip cleanly (fact-gated, like every brand device).

Lane scoping: PAGE lanes (any `[id^="sec-"]` present) get all kinds. SPECIMEN
lanes (the components previews / spec book) get shape-motif + type-treatment only:
a spec book legitimately swatches the whole palette and voids page-level
surface/accent claims, but its rendered CONTROLS must still wear the brand's
silhouette and type voice.

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m brand_pipeline.signature_audit \\
      <lane dirs/html...> --brand runs/<brand>/brand [--strict] [--out DIR]

--strict: exit 1 on any FAIL (gate wiring). Default exit 0 (report only).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

DEFAULT_VIEWPORT = (1440, 900)
LANE_TIMEOUT_MS = 120_000

# structural role vocabulary (pipeline classes, brand-agnostic) — an accent-scope
# signature names WHICH of these roles may carry the accent family; the selectors
# are the render substrate's own structural classes, not brand styling.
ROLE_SELECTORS = {
    "action":  ".c-button, button, [role=button], input[type=submit]",
    "link":    "a, .c-arrow-link",
    "glyph":   "svg, path, use, .c-arrow, .cl-icon, .c-glyph",
    "eyebrow": ".c-eyebrow, .cs-eyebrow, .cs-kicker",
    "mark":    ".c-logo, .cs-nav-brand, .c-foot-brand, .c-foot-wordmark",
    "chip":    ".cs-chip, .c-chip, .spec-chip",
    "focus":   ":focus-visible",  # not statically reachable; kept for schema completeness
}

SETTLE_CSS = "*, *::before, *::after { animation: none !important; transition: none !important; }"


MEASURE_JS = """
(args) => {
  const { roleSelectors } = args;
  const parse = (c) => {
    const m = /rgba?\\(([^)]+)\\)/.exec(c || '');
    if (!m) return null;
    const p = m[1].split(',').map(parseFloat);
    if (p.length === 4 && p[3] < 0.05) return null;
    return p.slice(0, 3);
  };
  const hex2rgb = (h) => [parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16)];
  const lum = (rgb) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2]);
  };
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    const cs = getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden';
  };
  const clsOf = (el) => {
    const c = el.className;
    return typeof c === 'string' ? c : (c && c.baseVal) || '';
  };
  const label = (el) => el.tagName.toLowerCase() +
    (clsOf(el) ? '.' + clsOf(el).trim().split(/\\s+/).slice(0, 2).join('.') : '');
  const secOf = (el) => { const s = el.closest('[id^="sec-"]'); return s ? s.id : null; };

  // ---- element walk: paint census (accent classification happens in Python) ----
  const paints = [];
  for (const el of document.querySelectorAll('*')) {
    if (!vis(el)) continue;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const entry = { label: label(el), sec: secOf(el), area: r.width * r.height, roles: [] };
    for (const [role, sel] of Object.entries(roleSelectors)) {
      if (role === 'focus') continue;
      try { if (el.matches(sel) || el.closest(sel)) entry.roles.push(role); } catch (e) {}
    }
    const bg = parse(cs.backgroundColor);
    if (bg) { paints.push({ ...entry, prop: 'bg', rgb: bg }); }
    const ink = parse(cs.color);
    // ink counts on paint-bearing leaves (text/controls/glyph hosts), not wrappers
    if (ink && (el.childElementCount === 0 ||
                el.matches('a, button, p, h1, h2, h3, h4, h5, h6, li, span, [role=button]'))) {
      paints.push({ ...entry, prop: 'ink', rgb: ink });
    }
    const bw = parseFloat(cs.borderTopWidth) || 0;
    const bc = parse(cs.borderTopColor);
    if (bc && bw >= 1) { paints.push({ ...entry, prop: 'border', rgb: bc }); }
    const fill = cs.fill && cs.fill !== 'none' ? parse(cs.fill) : null;
    if (fill && el.namespaceURI === 'http://www.w3.org/2000/svg') {
      paints.push({ ...entry, prop: 'fill', rgb: fill });
    }
  }

  // ---- buttons: silhouette + type probes. Scope = the CTA button FAMILY
  // (.c-button), the family the brand's button facts describe. Excluded on
  // purpose: .c-arrow-link nav triggers (semantic <button> text links), round
  // carousel/tab controls (their own measured device families — hubspot's
  // avoid rule: 'only tab chips and round carousel controls curve further'),
  // and non-substrate UI (spec-book chrome buttons). ----
  const buttons = [];
  for (const el of document.querySelectorAll('.c-button:not(.c-arrow-link)')) {
    if (!vis(el)) continue;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    buttons.push({ label: label(el), sec: secOf(el),
                   radiusPx: parseFloat(cs.borderTopLeftRadius) || 0,
                   heightPx: r.height,
                   family: cs.fontFamily, weight: parseInt(cs.fontWeight, 10) || 400 });
  }

  // ---- type probes by rank role ----
  const typeProbes = { display: [], heading: [], body: [], eyebrow: [], button: [] };
  const push = (k, el) => {
    const cs = getComputedStyle(el);
    typeProbes[k].push({ label: label(el), sec: secOf(el), family: cs.fontFamily,
                         weight: parseInt(cs.fontWeight, 10) || 400,
                         sizePx: parseFloat(cs.fontSize) });
  };
  for (const el of document.querySelectorAll('.c-heading--display, h1'))
    if (vis(el)) push('display', el);
  for (const el of document.querySelectorAll('h2, h3, .c-heading:not(.c-heading--display)'))
    if (vis(el)) push('heading', el);
  // the page's own heading family — used to spot REGISTER-PROMOTED statements
  // (a <p> deliberately riding the heading register, e.g. a bento lead quote at
  // the h2 tier): those audit under the HEADING contract, not body. Running
  // text in the heading family at body size still lands in `body` and fails.
  const hEl = document.querySelector('h1, h2, h3, .c-heading');
  const headingFam = hEl ? getComputedStyle(hEl).fontFamily : null;
  for (const el of document.querySelectorAll('p')) {
    if (!vis(el) || (el.textContent || '').trim().length <= 30) continue;
    const cs = getComputedStyle(el);
    const promoted = headingFam && cs.fontFamily === headingFam &&
                     parseFloat(cs.fontSize) >= 24;
    push(promoted ? 'heading' : 'body', el);
  }
  for (const el of document.querySelectorAll('.c-eyebrow'))
    if (vis(el)) push('eyebrow', el);
  for (const el of document.querySelectorAll('.c-button:not(.c-arrow-link)'))
    if (vis(el)) push('button', el);

  // ---- section surfaces (opaque own paint only; image-backed flagged) ----
  const sections = [];
  for (const wrap of document.querySelectorAll('[id^="sec-"]')) {
    const sec = wrap.querySelector('section') || wrap;
    const cs = getComputedStyle(sec);
    const rgb = parse(cs.backgroundColor);
    sections.push({ id: wrap.id, layout: wrap.dataset.layout || null,
                    rgb, luminance: rgb ? lum(rgb) : null,
                    hasImage: cs.backgroundImage !== 'none' ||
                              !!sec.querySelector(':scope > .c-image, :scope > picture, :scope .cs-hero-media') });
  }

  const de = document.documentElement;
  return { paints, buttons, typeProbes, sections,
           pageArea: de.scrollWidth * de.scrollHeight,
           hasSections: sections.length > 0 };
}
"""


# ── color helpers (Python side) ──────────────────────────────────────────────────

def _hex2rgb(h: str) -> tuple[int, int, int]:
    h = h.strip().lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _dist(a, b) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _in_family(rgb, family, tol: float = 40.0) -> bool:
    return any(_dist(rgb, f) <= tol for f in family)


# ── per-kind verifiers ───────────────────────────────────────────────────────────

def check_accent_scope(sig: dict, m: dict) -> list[dict]:
    """mode=never: the color family must not paint outside the allowed roles
    (or: must not paint the forbidden roles). Optional maxPaintSharePct rides the
    same walk as the accent_budget gate."""
    chk = sig.get("check") or {}
    family = [_hex2rgb(c) for c in (chk.get("colors") or [])]
    allowed = set(chk.get("allowedRoles") or [])
    forbidden = set(chk.get("forbiddenRoles") or [])
    rows = []
    hits = [p for p in m["paints"] if _in_family(p["rgb"], family)]

    if forbidden:
        bad = [p for p in hits if forbidden & set(p["roles"])]
        rows.append({
            "check": "scope(forbidden)", "ok": not bad,
            "detail": (f"{len(bad)} paint(s) on forbidden role(s) "
                       f"{sorted(forbidden)}: "
                       + "; ".join(f"{p['label']} [{p['prop']}]" for p in bad[:4])
                       if bad else
                       f"family never paints {sorted(forbidden)} "
                       f"({len(hits)} in-family paints checked)")})
    if allowed:
        stray = [p for p in hits if not (allowed & set(p["roles"]))]
        rows.append({
            "check": "scope(allowed)", "ok": not stray,
            "detail": (f"{len(stray)} paint(s) outside allowed roles "
                       f"{sorted(allowed)}: "
                       + "; ".join(f"{p['label']} [{p['prop']}] sec={p['sec']}"
                                   for p in stray[:4])
                       if stray else
                       f"all {len(hits)} in-family paints sit on allowed roles")})

    budget = chk.get("maxPaintSharePct")
    if isinstance(budget, (int, float)) and m.get("pageArea"):
        acc = 0.0
        for p in hits:
            acc += p["area"] if p["prop"] == "bg" else 0.25 * p["area"]
        share = 100.0 * acc / m["pageArea"]
        rows.append({"check": "accent_budget", "ok": share <= float(budget),
                     "sharePct": round(share, 3), "budgetPct": float(budget),
                     "detail": f"accent paint share {share:.3f}% of page "
                               f"(budget {budget}%)"})
    return rows


def check_shape_motif(sig: dict, m: dict) -> list[dict]:
    chk = sig.get("check") or {}
    btn_spec = chk.get("buttons") or {}
    rows = []
    buttons = m["buttons"]
    if not buttons:
        rows.append({"check": "buttons", "ok": True,
                     "detail": "no rendered buttons on this lane (vacuous pass)"})
        return rows
    if btn_spec.get("pill"):
        bad = [b for b in buttons if b["radiusPx"] < b["heightPx"] / 2 - 1.5]
        rows.append({"check": "buttons(pill)", "ok": not bad,
                     "detail": (f"{len(bad)}/{len(buttons)} button(s) not pill: "
                                + "; ".join(f"{b['label']} r={b['radiusPx']:.0f} "
                                            f"h={b['heightPx']:.0f}" for b in bad[:4])
                                if bad else f"all {len(buttons)} buttons pill "
                                            f"(radius >= height/2)")})
    if isinstance(btn_spec.get("radiusPx"), (int, float)):
        want = float(btn_spec["radiusPx"])
        tol = float(btn_spec.get("tolerancePx", 1.5))
        bad = [b for b in buttons if abs(b["radiusPx"] - want) > tol
               # a radius >= half height is a DIFFERENT silhouette (pill) — flagged
               # by neverPill below; here only non-matching square-ish radii count
               and b["radiusPx"] < b["heightPx"] / 2 - 1.5]
        rows.append({"check": f"buttons(radius {want:g}px)", "ok": not bad,
                     "detail": (f"{len(bad)}/{len(buttons)} off-radius: "
                                + "; ".join(f"{b['label']} r={b['radiusPx']:.1f}"
                                            for b in bad[:4])
                                if bad else
                                f"all {len(buttons)} buttons at {want:g}px "
                                f"(±{tol:g})")})
    if chk.get("neverPill"):
        pills = [b for b in buttons if b["radiusPx"] >= b["heightPx"] / 2 - 1.5
                 and b["heightPx"] >= 24]
        rows.append({"check": "buttons(neverPill)", "ok": not pills,
                     "detail": (f"{len(pills)} pill button(s): "
                                + "; ".join(b["label"] for b in pills[:4])
                                if pills else "no pill silhouettes")})
    return rows


def check_type_treatment(sig: dict, m: dict) -> list[dict]:
    rows = []
    for probe in ((sig.get("check") or {}).get("probes") or []):
        # YAML 1.1 footgun: an unquoted `on:` key parses as boolean True —
        # accept both spellings, and FAIL a probe with neither (a malformed
        # probe must never vacuously pass; caught live at pass1 verification,
        # where every type probe silently reported 'no rendered rank').
        on = str(probe.get("on") or probe.get(True) or "")
        if on not in ("display", "heading", "body", "eyebrow", "button"):
            rows.append({"check": f"type({on or '?'})", "ok": False,
                         "detail": f"malformed probe: no rank role ({probe!r}) "
                                   "— quote the `on:` key"})
            continue
        samples = m["typeProbes"].get(on) or []
        if not samples:
            rows.append({"check": f"type({on})", "ok": True,
                         "detail": f"no rendered {on} rank on this lane "
                                   "(vacuous pass)"})
            continue
        fams = [str(f) for f in (probe.get("familyIncludesAny") or [])]
        bad_fam = [s for s in samples
                   if fams and not any(f.lower() in s["family"].lower() for f in fams)]
        wmax = probe.get("weightMax")
        bad_w = [s for s in samples
                 if isinstance(wmax, (int, float)) and s["weight"] > wmax]
        ok = not bad_fam and not bad_w
        bits = []
        if bad_fam:
            bits.append(f"{len(bad_fam)}/{len(samples)} off-family: "
                        + "; ".join(f"{s['label']} '{s['family'][:40]}'"
                                    for s in bad_fam[:3]))
        if bad_w:
            bits.append(f"{len(bad_w)} over weight {wmax}: "
                        + "; ".join(f"{s['label']} w{s['weight']}"
                                    for s in bad_w[:3]))
        rows.append({"check": f"type({on})", "ok": ok,
                     "detail": "; ".join(bits) if bits else
                               f"{len(samples)} sample(s) on family "
                               f"{fams or 'any'}"
                               + (f", weight <= {wmax:g}" if wmax else "")})
    return rows


def check_surface_habit(sig: dict, m: dict) -> list[dict]:
    chk = sig.get("check") or {}
    rows = []
    secs = [s for s in m["sections"] if s.get("rgb")]
    if not secs:
        rows.append({"check": "surfaces", "ok": True,
                     "detail": "no section surfaces (vacuous pass)"})
        return rows
    if "darkAllowedColors" in chk:
        licensed = [_hex2rgb(c) for c in (chk.get("darkAllowedColors") or [])]
        thr = float(chk.get("darkMaxLuminance", 0.25))
        dark = [s for s in secs if s["luminance"] is not None and s["luminance"] < thr]
        bad = [s for s in dark if not _in_family(s["rgb"], licensed, tol=24.0)]
        rows.append({"check": "surfaces(dark family)", "ok": not bad,
                     "detail": (f"{len(bad)} dark section(s) off the licensed "
                                "family: "
                                + "; ".join(f"{s['id']}({s['layout']}) "
                                            f"rgb{tuple(s['rgb'])}" for s in bad[:4])
                                if bad else
                                f"{len(dark)} dark section(s), all in the "
                                f"licensed family; {len(secs)} sections checked")})
    if "sectionMinLuminance" in chk:
        thr = float(chk["sectionMinLuminance"])
        bad = [s for s in secs
               if not s["hasImage"] and s["luminance"] is not None
               and s["luminance"] < thr]
        rows.append({"check": "surfaces(light canvas)", "ok": not bad,
                     "detail": (f"{len(bad)} section(s) cut below luminance "
                                f"{thr}: "
                                + "; ".join(f"{s['id']}({s['layout']}) "
                                            f"rgb{tuple(s['rgb'])}" for s in bad[:4])
                                if bad else
                                f"all {len(secs)} sections on the light canvas")})
    return rows


KIND_CHECKS = {
    "accent-scope": check_accent_scope,
    "shape-motif": check_shape_motif,
    "type-treatment": check_type_treatment,
    "surface-habit": check_surface_habit,
    # spacing-habit signatures are audited by the spacing/scale machinery — the
    # auditor reports them as delegated rather than silently passing them.
}

SPECIMEN_KINDS = {"shape-motif", "type-treatment"}


# ── driver ───────────────────────────────────────────────────────────────────────

def audit_lane(pw, html: Path, signatures: list[dict],
               viewport=DEFAULT_VIEWPORT) -> dict:
    browser = pw.chromium.launch()
    try:
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]},
                                device_scale_factor=1, reduced_motion="reduce")
        page.set_default_timeout(LANE_TIMEOUT_MS)
        page.goto(html.resolve().as_uri(), wait_until="load", timeout=LANE_TIMEOUT_MS)
        page.add_style_tag(content=SETTLE_CSS)
        page.evaluate("document.fonts && document.fonts.ready")
        page.wait_for_timeout(500)
        m = page.evaluate(MEASURE_JS, {"roleSelectors": ROLE_SELECTORS})
    finally:
        browser.close()

    specimen = not m["hasSections"]
    out = {"specimenLane": specimen, "signatures": []}
    for sig in signatures:
        kind = str(sig.get("kind") or "")
        entry = {"id": sig.get("id"), "kind": kind, "mode": sig.get("mode")}
        if specimen and kind not in SPECIMEN_KINDS:
            entry["skipped"] = ("specimen lane — page-level "
                                f"{kind} claims void on a spec book")
            out["signatures"].append(entry)
            continue
        fn = KIND_CHECKS.get(kind)
        if fn is None:
            entry["skipped"] = (f"kind '{kind}' delegated to other machinery "
                                "(spacing/scale) or unknown — C25 validates "
                                "authorship")
            out["signatures"].append(entry)
            continue
        rows = fn(sig, m)
        entry["checks"] = rows
        entry["ok"] = all(r["ok"] for r in rows)
        out["signatures"].append(entry)
    return out


def run_audit(lane_paths: list[Path], brand_dir: Path, out_dir: Path | None,
              viewport=DEFAULT_VIEWPORT) -> dict:
    from playwright.sync_api import sync_playwright

    doc = yaml.safe_load((brand_dir / "brand.yaml").read_text()) or {}
    signatures = [s for s in (doc.get("signatures") or []) if isinstance(s, dict)]
    report = {"generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "brandDir": str(brand_dir), "viewport": f"{viewport[0]}x{viewport[1]}",
              "signatureCount": len(signatures), "lanes": []}
    if not signatures:
        report["note"] = "no signatures: block — nothing to audit (fact-gated skip)"
        return report

    with sync_playwright() as pw:
        for html in lane_paths:
            lane = str(html.parent.relative_to(brand_dir)) \
                if brand_dir in html.parents else str(html)
            entry = {"lane": lane, "html": str(html)}
            if not html.exists():
                entry["error"] = "file not found"
            else:
                try:
                    entry.update(audit_lane(pw, html, signatures, viewport))
                except Exception as exc:
                    entry["error"] = f"{type(exc).__name__}: {exc}"[:300]
            report["lanes"].append(entry)

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(json.dumps(report, indent=2))
        (out_dir / "report.md").write_text(render_md(report))
    return report


def render_md(report: dict) -> str:
    lines = ["# Signature audit — signature_check + accent_budget",
             "",
             f"Brand: `{report['brandDir']}` — {report['signatureCount']} declared "
             f"signature(s) · viewport {report['viewport']} · {report['generatedAt']}",
             ""]
    for lane in report["lanes"]:
        if lane.get("error"):
            lines.append(f"## {lane['lane']} — ERROR: {lane['error']}\n")
            continue
        verdict = "PASS" if all(s.get("ok", True) for s in lane["signatures"]) else "FAIL"
        kind = " (specimen lane)" if lane.get("specimenLane") else ""
        lines.append(f"## {lane['lane']} — {verdict}{kind}\n")
        lines.append("| signature | kind | check | verdict | detail |")
        lines.append("|---|---|---|---|---|")
        for s in lane["signatures"]:
            if s.get("skipped"):
                lines.append(f"| `{s['id']}` | {s['kind']} | — | skipped | "
                             f"{s['skipped']} |")
                continue
            for r in s.get("checks", []):
                lines.append(f"| `{s['id']}` | {s['kind']} | {r['check']} | "
                             f"{'PASS' if r['ok'] else 'FAIL'} | {r['detail']} |")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lanes", nargs="+", help="lane dirs (index.html assumed) or .html files")
    ap.add_argument("--brand", type=Path, required=True, help="brand run dir (brand.yaml)")
    ap.add_argument("--out", type=Path, default=None,
                    help="report dir (default <brand>/signature-baseline)")
    ap.add_argument("--viewport", default="1440x900")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any FAIL")
    args = ap.parse_args(argv)
    w, h = (int(x) for x in args.viewport.lower().split("x"))
    paths = [(Path(l) / "index.html") if Path(l).is_dir() else Path(l)
             for l in args.lanes]
    out_dir = args.out or (args.brand / "signature-baseline")
    report = run_audit(paths, args.brand, out_dir, viewport=(w, h))

    fails = 0
    for lane in report["lanes"]:
        if lane.get("error"):
            fails += 1
            print(f"[signature-audit] {lane['lane']}: ERROR {lane['error']}",
                  file=sys.stderr)
            continue
        bad = [s for s in lane["signatures"] if s.get("ok") is False]
        fails += len(bad)
        budget = next((r for s in lane["signatures"] for r in s.get("checks", [])
                       if r["check"] == "accent_budget"), None)
        share = f" · accent share {budget['sharePct']}%" if budget else ""
        verdict = "PASS" if not bad else "FAIL " + ",".join(str(s["id"]) for s in bad)
        print(f"[signature-audit] {lane['lane']}: {verdict}{share}")
    if report.get("note"):
        print(f"[signature-audit] {report['note']}")
    if out_dir:
        print(f"[signature-audit] report: {out_dir / 'report.md'}")
    return 1 if (args.strict and fails) else 0


if __name__ == "__main__":
    sys.exit(main())
