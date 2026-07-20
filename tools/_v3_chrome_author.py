#!/usr/bin/env python3
"""Author the v3 chrome contract into v3 brand.yaml with an in-place block splice.

v3's brand.yaml keeps `navbar:`/`footer:` MID-FILE (signatures/motion/…/layouts
follow), so the trailing-splice in bridge_chrome_to_brand cannot be used. This
replaces ONLY the `navbar:` and `footer:` top-level blocks in place, preserving
every other section byte-for-byte, then validates that all top-level keys and the
layouts list survive. It reuses the proven bridge merge functions + asset
materialization so the authored shape matches the schema the renderer consumes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "tools"))
import bridge_chrome_to_brand as bridge  # noqa: E402

BRAND = "hubspot-v3"
contract_path = PROJECT_DIR / "runs" / BRAND / "assets" / "source-chrome.v2.json"
brand_yaml = PROJECT_DIR / "runs" / BRAND / "brand" / "brand.yaml"

contract = json.loads(contract_path.read_text(encoding="utf-8"))
raw = brand_yaml.read_text(encoding="utf-8")
doc = yaml.safe_load(raw) or {}
assets_dir = brand_yaml.parent / "assets"

# Stale social glyphs: the bridge binds an EXISTING assets/social-<net>.svg directly
# instead of re-materializing, so a previously-written broken (<use> sprite ref) file
# would stick. Remove them so the freshly RESOLVED standalone symbol markup lands.
import base64 as _b64
import re as _re
for f in assets_dir.glob("social-*.svg"):
    f.unlink()

# materialize harvested chrome artwork (menu icons, promo card, store badges,
# social glyphs) into the brand's assets/ and stamp asset refs into the contract
stamped = bridge._materialize_chrome_assets(contract, assets_dir)
print(f"[author] chrome assets materialized: {len(stamped)}")

# FOOTER WORDMARK: the saved DOM inlines the footer logo as a data:image/svg+xml
# base64 (cream wordmark). The bridge stores only a srcContract ref, so prepare_
# chrome_glyphs can't resolve it → the centered-stack wordmark never paints. Decode
# it to a real local asset and stamp footer.logo.src so it resolves at compose.
_flogo_src = str(((contract.get("footer") or {}).get("logo") or {}).get("src") or "")
_footer_logo_materialized = False
if _flogo_src.startswith("data:"):
    try:
        header, _, payload = _flogo_src.partition(",")
        data = _b64.b64decode(payload) if ";base64" in header else payload.encode("utf-8")
        assets_dir.mkdir(parents=True, exist_ok=True)
        (assets_dir / "footer-logo.svg").write_bytes(data)
        _footer_logo_materialized = True
    except Exception as exc:
        print(f"[author] footer logo decode failed: {exc}")

navbar = bridge._merge_navbar(doc.get("navbar"), contract.get("nav") or {})
footer = bridge._merge_footer(doc.get("footer"), contract.get("footer") or {})

# Footer track model: the extractor's DOM-wrapper split (wrapperSizes [1, 4]) is a
# 2-wrapper capture, but the source PAINTS 5 side-by-side columns. Feeding [1,4] to
# the renderer stacks 4 groups into one very tall cell (footer 1081px vs 656px
# source). The visual truth is one track per headed column, so drop the wrapper
# grouping and let the flat multi-column directory render (each column its own
# track). Keep every other measured footer fact.
_fg = (footer.get("measured") or {}).get("grid")
if isinstance(_fg, dict):
    for k in ("wrapperSizes", "wrappers", "wrapperCount"):
        _fg.pop(k, None)

# A single OVERLONG directory column (e.g. an 18-link "Popular Features" group) is
# painted by the source across TWO side-by-side columns (a headed column + a
# headless continuation), which keeps the footer band short. Rendering it as one
# tall column overshoots the band height. Split the longest column into two near-
# equal halves (continuation carries no heading) when it dwarfs the rest — generic,
# structure-preserving (no links added/removed), matches the source's track count.
# Footer heading register: the source column headings are the muted small label
# (measured fontSizeMeasured ~15px); the extractor's `fontSize` sometimes latches a
# larger sibling (22px here). Clamp the authored heading size to the smaller measured
# value so headings don't render oversized against the source.
_mh = (footer.get("measured") or {}).get("heading")
if isinstance(_mh, dict):
    fsm = str(_mh.get("fontSizeMeasured") or "").replace("px", "").strip()
    try:
        fsm_v = int(round(float(fsm))) if fsm else 0
    except ValueError:
        fsm_v = 0
    if isinstance(_mh.get("fontSize"), (int, float)) and (fsm_v and _mh["fontSize"] > fsm_v + 2):
        _mh["fontSize"] = fsm_v

# Footer bottom composition: the source paints a CENTERED STACK (social glyph row →
# cream wordmark → copyright/legal), the same anatomy v2 captured. Declare it so the
# renderer draws the centered stack instead of the inline badge+legal row.
_bb = footer.get("bottomBar")
if isinstance(_bb, dict):
    _bb["anatomy"] = "centered-stack"
    if not _bb.get("policyLinks"):
        _bb["policyLinks"] = [{"label": l.get("label"), "href": l.get("href")}
                              for l in ((footer.get("legal") or {}).get("links") or [])]
    # Bottom-bar row rhythm: the JS-off static snapshot collapses the stack (measured
    # gap 0 → wordmark/copyright/legal touch). Bind the row gap to the footer's
    # measured spacing rhythm — the captured copyright margin-top (16px) plus the
    # footer's own row rhythm — so copyright↔legal (and the whole stack) is not cramped.
    if not isinstance(_bb.get("gap"), (int, float)) or _bb.get("gap", 0) < 12:
        _bb["gap"] = 16
    _bb["gapProvenance"] = ("footer bottom stack collapses in the JS-off saved snapshot "
                            "(measured 0); bound to the captured copyright margin-top "
                            "(16px) so copyright↔legal is not cramped")

# Social + wordmark INK: bind the glyphs to the footer's measured muted link color
# (the source paints monochrome muted glyphs / cream wordmark, not the accent hue that
# currentColor otherwise inherits). Fact-gated to the measured footer link color.
_flink = ((footer.get("measured") or {}).get("link") or {}).get("color")
if _flink:
    for _s in footer.get("social") or []:
        ic = _s.get("icon") if isinstance(_s, dict) else None
        if isinstance(ic, dict) and not ic.get("ink"):
            ic["ink"] = _flink

# Footer wordmark asset: bind the decoded local SVG so prepare_chrome_glyphs stamps
# its data-URI (+ intrinsic aspect) and the centered-stack renders the real wordmark.
if _footer_logo_materialized and isinstance(footer.get("logo"), dict):
    footer["logo"]["src"] = "footer-logo.svg"

cols = footer.get("columns") or []
if len(cols) >= 3:
    counts = sorted((len(c.get("links") or []) for c in cols), reverse=True)
    longest_i = max(range(len(cols)), key=lambda i: len(cols[i].get("links") or []))
    longest = len(cols[longest_i].get("links") or [])
    second = counts[1] if len(counts) > 1 else 0
    if longest >= 14 and longest >= 1.6 * max(second, 1):
        links = cols[longest_i].get("links") or []
        half = (len(links) + 1) // 2
        head_col = {"heading": cols[longest_i].get("heading") or "", "links": links[:half]}
        cont_col = {"heading": "", "links": links[half:]}
        footer["columns"] = cols[:longest_i] + [head_col, cont_col] + cols[longest_i + 1:]

# Utility dropdowns: the item STRUCTURE is captured from the static DOM, but the
# open-state PANEL paint (w/h/bg) is not present in a saved snapshot (panels portal
# on open) — mark dropdownNotObserved so the honest structure-captured/paint-absent
# state validates (C21) without inventing panel geometry.
for u in navbar.get("utility") or []:
    if isinstance(u, dict) and str(u.get("kind") or "") == "dropdown":
        dd = u.get("dropdown") if isinstance(u.get("dropdown"), dict) else None
        if dd and (dd.get("items") or []):
            u["dropdownNotObserved"] = True
            u.setdefault("notObservedReason",
                         "items captured from saved DOM; open-state panel paint "
                         "(w/h/bg) not in a static snapshot (portals on open)")
# Trigger chevron: if the caret glyph rides a shared sprite <use> (no standalone
# artwork) but the geometry was measured, keep the box facts; if nothing was
# measured, mark chevronNotObserved so C21 stays honest rather than silent.
trig = (navbar.get("measured") or {}).get("trigger")
if not (isinstance(trig, dict) and isinstance(trig.get("chevron"), dict)
        and (trig["chevron"].get("box") or {}).get("w")):
    navbar.setdefault("measured", {}).setdefault("trigger", {})["chevronNotObserved"] = True

# ── utilityTier (renderer gates the thin top bar on THIS explicit key, not on
# twoTier alone). Split the captured utility run into leading (left region) and
# trailing (right region) clusters. Measured heights come from the contract.
nav_c = contract.get("nav") or {}
measured = nav_c.get("measured") or {}
util_labels = [str(u.get("label") or "").strip() for u in (navbar.get("utility") or [])]
# right region of the top bar (source order): Log in + About (+ Search when present)
trailing = [l for l in util_labels if l.lower() in ("log in", "about", "search")]
# Two-tier heights: the split-derived utilityBarHeight is the PRIMARY-row top
# (overstates the thin bar), so keep a conservative thin utility band and give the
# remainder to the primary bar so the two tiers SUM to the measured bar height —
# the replica diffs the whole nav band's height (matching 128px lifts height
# fidelity vs the 52+52=104 the raw split produced).
bar_h = int((measured.get("bar") or {}).get("height")
            or (navbar.get("surface") or {}).get("height") or 128)
util_h = 52
navbar["utilityTier"] = {
    "height": util_h,
    "bg": (navbar.get("surface") or {}).get("bg") or "rgb(255, 255, 255)",
    "fontSize": 12,
    "trailing": trailing,
}
if bar_h > util_h:
    navbar.setdefault("measured", {})["primaryBarHeight"] = bar_h - util_h

# ── in-place block splice ────────────────────────────────────────────────────
lines = raw.splitlines(keepends=True)
col0 = [(i, ln) for i, ln in enumerate(lines) if ln[:1].isalpha() or ln.startswith("_")]
key_at = {}
for i, ln in col0:
    name = ln.split(":", 1)[0].strip()
    key_at.setdefault(name, i)


def block_range(name: str) -> tuple[int, int]:
    start = key_at[name]
    after = [i for i, _ in col0 if i > start]
    end = after[0] if after else len(lines)
    return start, end


nb_dump = yaml.safe_dump({"navbar": navbar}, sort_keys=False, allow_unicode=True, width=10**9)
ft_dump = yaml.safe_dump({"footer": footer}, sort_keys=False, allow_unicode=True, width=10**9)

# splice footer first (higher line numbers) so navbar indices stay valid
fs, fe = block_range("footer")
lines = lines[:fs] + [ft_dump] + lines[fe:]
ns, ne = block_range("navbar")  # recompute-safe: navbar precedes footer
lines = lines[:ns] + [nb_dump] + lines[ne:]
new_text = "".join(lines)

after_doc = yaml.safe_load(new_text)
before_keys = [k for k in doc.keys()]
for k in before_keys:
    if k not in after_doc:
        raise SystemExit(f"VALIDATION FAILED: top-level key '{k}' dropped")
if isinstance(doc.get("layouts"), list):
    if len(after_doc.get("layouts") or []) != len(doc["layouts"]):
        raise SystemExit("VALIDATION FAILED: layouts list length changed")
brand_yaml.write_text(new_text, encoding="utf-8")
print(f"[author] navbar/footer spliced in place; top-level keys preserved: {len(before_keys)}")
print(f"  nav: twoTier={navbar.get('twoTier')} utilityTier.trailing={navbar['utilityTier']['trailing']} "
      f"primary={len(navbar['primary'])} ctas={len(navbar['ctas'])}")
menus = [(p.get('label'), len((p.get('menu') or {}).get('columns') or []), (p.get('menu') or {}).get('sidebarTabs'))
         for p in navbar['primary'] if isinstance(p, dict) and p.get('menu')]
print(f"  menus: {menus}")
print(f"  footer: cols={len(footer['columns'])} social={len(footer['social'])} "
      f"bottomBar={'yes' if footer.get('bottomBar') else 'no'}")
