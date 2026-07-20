#!/usr/bin/env python3
"""Bridge an extracted source_chrome.v2 contract into brand.yaml + regenerate the
exact nav/footer preview at runs/<brand>/brand/chrome/index.html.

This is the GENERATOR for the chrome preview — never hand-edit the output HTML;
re-run this so changes persist. It:

  1. reads runs/<brand>/assets/source-chrome.v2.json (offline-extracted),
  2. merges nav (utility + primary tiers, ctas, logo, surface) and footer
     (columns, social, legal, logo, surface) into brand.yaml WITHOUT disturbing
     any other section — an ATOMIC write (temp file → yaml.safe_load validation
     asserting every unrelated top-level key + the full `layouts` list survive →
     os.replace),
  3. renders runs/<brand>/brand/chrome/index.html:
       - two-tier nav (utility row above the primary bar),
       - footer with network-typed monochrome ICON glyphs (not text pills),
         a centered bottom block (social → logo → copyright/legal), and a column
         layout that widens the link-heavy first column and stacks the trailing
         columns together,
       - container-query units ONLY (cqw/cqh/cqi; container-type:size on
         html/body). NEVER vh/vw/dvh.

Everything rendered comes from the saved DOM via the contract; nothing is
fabricated. Generic across brands (also runs for woodwave).

STANDALONE by decision (Path-2 reconcile, 2026-07): the evidence-first authoring
skill (spec/layout-analyst-skill.md, Phase 0) INVOKES this tool as its first step
and then verifies presentation devices against css-facts — the bridge is the
generator, the skill is the caller; neither re-implements the other.

Usage:
    ./venv/bin/python tools/bridge_chrome_to_brand.py --brand hubspot
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

PROJECT_DIR = Path(__file__).resolve().parents[1]


# ── monochrome social glyphs (Simple Icons, CC0; viewBox 0 0 24 24) ──────────
# Keyed by the contract's network name. Rendered with fill="currentColor" so the
# footer link color drives them — no external assets, no invented marks.
_SOCIAL_GLYPHS: dict[str, str] = {
    "facebook": "M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073",
    "instagram": "M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z",
    "youtube": "M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z",
    "twitter": "M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z",
    "x": "M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z",
    "linkedin": "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z",
    "reddit": "M24 11.779c0-1.459-1.192-2.645-2.657-2.645-.715 0-1.363.286-1.84.746-1.81-1.191-4.259-1.949-6.971-2.046l1.483-4.669 4.016.95c0 1.192.964 2.157 2.16 2.157 1.196 0 2.16-.965 2.16-2.157 0-1.192-.964-2.157-2.16-2.157-.851 0-1.582.5-1.926 1.215l-4.273-1.01a.434.434 0 00-.516.31l-1.658 5.214c-2.752.081-5.241.838-7.075 2.043-.477-.46-1.125-.746-1.84-.746C1.193 9.134 0 10.32 0 11.779c0 .967.526 1.81 1.307 2.275-.045.243-.069.49-.069.745 0 3.785 4.426 6.857 9.876 6.857 5.451 0 9.876-3.072 9.876-6.857 0-.255-.024-.502-.069-.745.781-.465 1.307-1.308 1.307-2.275zM6.926 13.347c0-.81.652-1.469 1.458-1.469.806 0 1.458.659 1.458 1.469 0 .811-.652 1.47-1.458 1.47-.806 0-1.458-.659-1.458-1.47zm8.314 4.077c-1.018 1.018-2.964 1.097-3.532 1.097-.568 0-2.514-.079-3.532-1.097a.386.386 0 010-.546.39.39 0 01.546 0c.642.643 2.016.871 2.986.871.97 0 2.344-.228 2.986-.871a.39.39 0 01.546 0 .386.386 0 010 .546zm-.273-2.606c-.806 0-1.458-.659-1.458-1.47 0-.81.652-1.469 1.458-1.469.806 0 1.458.659 1.458 1.469 0 .811-.652 1.47-1.458 1.47z",
    "tiktok": "M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z",
    "github": "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12",
    "threads": "M17.3 11.1c-.1 0-.2-.1-.3-.1-.2-3.2-1.9-5-4.8-5-1.7 0-3.2.8-4 2.1l1.6 1.1c.6-1 1.5-1.2 2.4-1.2 1.1 0 2 .3 2.5 1 .3.4.5 1 .7 1.7-.9-.2-1.9-.2-3-.1-3 .2-4.9 1.9-4.8 4.3 0 1.2.7 2.3 1.7 2.9.9.6 2 .8 3.2.8 1.6-.1 2.8-.7 3.7-1.8.6-.9 1-2 1.2-3.3.7.4 1.2 1 1.5 1.7.5 1.1.5 3-1 4.5-1.3 1.3-2.9 1.9-5.2 1.9-2.6 0-4.5-.8-5.8-2.4C5.7 17.3 5 15.1 5 12c0-3.1.7-5.3 2-6.9 1.3-1.6 3.2-2.4 5.8-2.4 2.6 0 4.5.8 5.9 2.5.7.8 1.2 1.9 1.5 3.1l1.9-.5c-.4-1.5-1-2.8-1.9-3.9C19.4 1.6 16.9.5 13.6.5h-.1C10.3.5 7.8 1.6 6.1 3.7 4.6 5.6 3.8 8.2 3.8 11.6v.2c0 3.4.8 6 2.3 7.9 1.7 2.1 4.2 3.2 7.4 3.2h.1c2.8 0 4.8-.7 6.5-2.4 2.2-2.2 2.1-5 1.4-6.7-.5-1.2-1.5-2.2-2.8-2.7z",
    "pinterest": "M12.017 0C5.396 0 .029 5.367.029 11.987c0 5.079 3.158 9.417 7.618 11.162-.105-.949-.199-2.403.041-3.439.219-.937 1.406-5.957 1.406-5.957s-.359-.72-.359-1.781c0-1.663.967-2.911 2.168-2.911 1.024 0 1.518.769 1.518 1.688 0 1.029-.653 2.567-.992 3.992-.285 1.193.6 2.165 1.775 2.165 2.128 0 3.768-2.245 3.768-5.487 0-2.861-2.063-4.869-5.008-4.869-3.41 0-5.409 2.562-5.409 5.199 0 1.033.394 2.143.889 2.741.099.12.112.225.085.345-.09.375-.293 1.199-.334 1.363-.053.225-.172.271-.402.165-1.495-.69-2.433-2.878-2.433-4.646 0-3.776 2.748-7.252 7.92-7.252 4.158 0 7.392 2.967 7.392 6.923 0 4.135-2.607 7.462-6.233 7.462-1.214 0-2.357-.629-2.748-1.378l-.747 2.853c-.271 1.043-1.002 2.35-1.492 3.146C9.57 23.812 10.763 24 12.017 24c6.624 0 11.99-5.367 11.99-11.988C24.007 5.367 18.641.001 12.017.001z",
}
_FALLBACK_GLYPH = "M12 2a10 10 0 100 20 10 10 0 000-20zm0 2c1.7 0 3.2.6 4.4 1.6-.5.9-1.2 1.7-2 2.4-.7-.2-1.5-.3-2.4-.3s-1.7.1-2.4.3c-.8-.7-1.5-1.5-2-2.4C8.8 4.6 10.3 4 12 4zm-7.8 6c.5.1 1.1.2 1.8.2.9 0 1.9-.1 2.9-.3.2 1 .3 2 .3 3.1s-.1 2.1-.3 3.1c-1-.2-2-.3-2.9-.3-.7 0-1.3.1-1.8.2C4.1 14.7 4 13.4 4 12s.1-1.7.2-2z"


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── token resolution from brand.yaml (generic, with fallbacks) ───────────────
def _color(doc: dict[str, Any], key: str, default: str) -> str:
    node = (((doc.get("tokens") or {}).get("colors")) or {}).get(key)
    if isinstance(node, dict) and node.get("value"):
        return str(node["value"])
    return default


def _accent(doc: dict[str, Any]) -> str:
    """This brand's accent color for link-hover / CTA fill — resolved GENERICALLY
    from its own tokens with NO hardcoded cross-brand hue. Precedence:

      1. ``brand/primary``          (e.g. HubSpot's real #ff4800)
      2. any ``accent/*`` token     (prefer ``accent/highlight``; e.g. WoodWave gold)
      3. a link / text-accent token (``text/link`` / ``text/accent`` / ``link/default``)

    Returns "" when the brand genuinely defines none, so the caller can fall back
    to the link's OWN base color (no hover shift) rather than a foreign hue.
    """
    cols = (((doc.get("tokens") or {}).get("colors")) or {})

    def val(key: str) -> str:
        node = cols.get(key)
        return str(node["value"]) if isinstance(node, dict) and node.get("value") else ""

    primary = val("brand/primary")
    if primary:
        return primary
    highlight = val("accent/highlight")
    if highlight:
        return highlight
    for key, node in cols.items():
        if str(key).startswith("accent/") and isinstance(node, dict) and node.get("value"):
            return str(node["value"])
    for key in ("text/link", "text/accent", "link/default"):
        link = val(key)
        if link:
            return link
    return ""


def _radius(doc: dict[str, Any], key: str, default: str) -> str:
    node = (((doc.get("tokens") or {}).get("radius")) or {}).get(key)
    if isinstance(node, dict) and node.get("value"):
        return str(node["value"])
    return default


def _font(doc: dict[str, Any], key: str, default: str) -> str:
    fams = (((doc.get("tokens") or {}).get("type")) or {}).get("families") or {}
    node = fams.get(key)
    if isinstance(node, dict) and node.get("value"):
        return str(node["value"])
    return default


def _surface_base(doc: dict[str, Any], default: str) -> str:
    node = (((doc.get("tokens") or {}).get("surfaces")) or {}).get("surface/base")
    if isinstance(node, dict) and node.get("bg") and "image" not in str(node["bg"]):
        return str(node["bg"])
    return default


def _font_stack(name: str, *, serif: bool) -> str:
    tail = (
        'Georgia, "Times New Roman", serif'
        if serif
        else '-apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
    )
    return f'"{name}", {tail}'


# ── nav/footer merge into existing brand.yaml dicts (preserve curation) ──────
def _deep_merge_measured(existing: Any, fresh: Any) -> Any:
    """Per-key deep merge of a re-extracted ``measured`` block into the existing one.

    FRESH extractor facts win key-by-key; agent-enriched keys the extractor does not
    measure (e.g. ``link.hoverBg``, ``cta.height``, ``bar.effectiveBg`` curation)
    SURVIVE a re-bridge (sysfix 2026-07: the old whole-dict replacement clobbered
    every enrichment on each re-run)."""
    if not isinstance(existing, dict) or not isinstance(fresh, dict):
        return fresh
    out = dict(existing)
    for k, v in fresh.items():
        if isinstance(v, dict):
            out[k] = _deep_merge_measured(out.get(k), v)
        elif v in (0, "", None) and out.get(k) not in (0, "", None):
            # a zero/empty re-measure never overwrites a real existing measure
            # (e.g. contentMaxWidth: 0 when the source page uses only %-based
            # containers must not clobber an agent-verified 1216)
            continue
        else:
            out[k] = v
    return out


def _transparent(color: Any) -> bool:
    c = str(color or "").strip().lower().replace(" ", "")
    return (not c) or c == "transparent" or c in ("rgba(0,0,0,0)", "rgb(0,0,0,0)")


# ── chrome asset materialization (fid4 2026-07, brand-agnostic) ──────────────
# The extractor captures REAL artwork references (per-link menu icons as inline
# svg markup or saved <img> files, the promo card image, store badges, social
# glyph masks). Materialize each into the brand's assets/ folder and stamp the
# fact with ``asset: "assets/<name>"`` so renderers bind the brand's own files.
# Nothing is fabricated: no on-disk source ⇒ no asset stamp ⇒ renderers degrade.

_IMG_MAGIC = (
    (b"RIFF", ".webp"),
    (b"\x89PNG", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF8", ".gif"),
    (b"<svg", ".svg"),
    (b"<?xm", ".svg"),
)


def _slug(text: str, fallback: str = "asset") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return s[:60] or fallback


def _sniff_ext(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".svg", ".png", ".webp", ".jpg", ".jpeg", ".gif", ".avif"):
        return ".jpg" if ext == ".jpeg" else ext
    try:
        head = path.read_bytes()[:16]
    except OSError:
        return ""
    for magic, sniffed in _IMG_MAGIC:
        if head.startswith(magic) or magic in head[:12]:
            return sniffed
    return ""


def _ensure_svg_ns(markup: str) -> str:
    """outerHTML of an inline <svg> legally omits xmlns inside HTML, but the
    materialized FILE is consumed standalone (data: URI masks, <img>) where it
    is XML — without the namespace the glyph silently paints nothing."""
    i = markup.find("<svg")
    j = markup.find(">", i) if i != -1 else -1
    if i == -1 or j == -1:
        return markup
    if "xmlns=" not in markup[i:j]:
        markup = markup[:i + 4] + ' xmlns="http://www.w3.org/2000/svg"' + markup[i + 4:]
    if "xlink:" in markup and "xmlns:xlink=" not in markup:
        i = markup.find("<svg")
        markup = (markup[:i + 4] + ' xmlns:xlink="http://www.w3.org/1999/xlink"'
                  + markup[i + 4:])
    return markup


def _place_asset(assets_dir: Path, name: str, *, src_file: Path | None = None,
                 svg_markup: str = "") -> str | None:
    """Copy/write one artwork file into assets/ (never overwrite an existing
    curated file with different content is NOT checked — existing name wins).
    Returns the relative ``assets/<name>`` ref, or None when nothing usable."""
    dest = assets_dir / name
    if dest.exists():
        return f"assets/{name}"
    try:
        assets_dir.mkdir(parents=True, exist_ok=True)
        if svg_markup:
            dest.write_text(_ensure_svg_ns(svg_markup), encoding="utf-8")
            return f"assets/{name}"
        if src_file is not None and src_file.is_file():
            shutil.copy2(src_file, dest)
            return f"assets/{name}"
    except OSError:
        return None
    return None


def _materialize_icon(icon: dict[str, Any], assets_dir: Path, base_name: str) -> None:
    """Stamp ``icon.asset`` from the icon's REAL artwork (inline svg markup or a
    saved on-disk file). In place; absent artwork leaves the fact stamp-free."""
    if not isinstance(icon, dict):
        return
    kind = icon.get("kind") or ""
    if kind == "svg" and str(icon.get("svg") or "").lstrip().startswith("<svg"):
        ref = _place_asset(assets_dir, f"{base_name}.svg", svg_markup=str(icon["svg"]))
        if ref:
            icon["asset"] = ref
        return
    saved = icon.get("savedFile")
    if saved:
        p = Path(str(saved))
        ext = _sniff_ext(p)
        if ext:
            ref = _place_asset(assets_dir, f"{base_name}{ext}", src_file=p)
            if ref:
                icon["asset"] = ref


def _materialize_chrome_assets(contract: dict[str, Any], assets_dir: Path) -> list[str]:
    """Materialize every harvested chrome artwork fact (menu link icons, promo
    card images, store badges, social glyphs) into assets/ and stamp asset refs
    on the contract nodes IN PLACE (the merge then carries the refs into
    brand.yaml). Returns the list of asset refs stamped."""
    stamped: list[str] = []

    def note(ref: str | None) -> None:
        if ref:
            stamped.append(ref)

    nav = contract.get("nav") if isinstance(contract.get("nav"), dict) else {}
    # bar-affordance glyphs (fid15): utility-control icons + chevrons and the
    # dropdown-trigger family chevron — all harvested inline-svg artwork.
    for u in nav.get("utility") or []:
        if not isinstance(u, dict):
            continue
        base = _slug(u.get("role") or u.get("label"), "control")
        ic = u.get("icon") if isinstance(u.get("icon"), dict) else None
        if isinstance(ic, dict):
            _materialize_icon(ic, assets_dir, f"nav-utility-{base}")
            note(ic.get("asset"))
        ch = u.get("chevron") if isinstance(u.get("chevron"), dict) else None
        if isinstance(ch, dict):
            _materialize_icon(ch, assets_dir, "nav-trigger-chevron")
            note(ch.get("asset"))
    trig_ch = (((nav.get("measured") or {}).get("trigger") or {}).get("chevron"))
    if isinstance(trig_ch, dict):
        _materialize_icon(trig_ch, assets_dir, "nav-trigger-chevron")
        note(trig_ch.get("asset"))
    banner_cta = ((nav.get("banner") or {}).get("cta")
                  if isinstance(nav.get("banner"), dict) else None)
    if isinstance(banner_cta, dict) and isinstance(banner_cta.get("arrow"), dict):
        _materialize_icon(banner_cta["arrow"], assets_dir, "banner-cta-arrow")
        note(banner_cta["arrow"].get("asset"))
    for link in (nav.get("links") or []) + (nav.get("primary") or []):
        menu = link.get("menu") if isinstance(link, dict) and isinstance(link.get("menu"), dict) else None
        if not menu:
            continue
        for col in menu.get("columns") or []:
            for l in col.get("links") or []:
                ic = l.get("icon") if isinstance(l, dict) else None
                if isinstance(ic, dict):
                    _materialize_icon(ic, assets_dir, f"nav-icon-{_slug(l.get('label'))}")
                    note(ic.get("asset"))
        card = menu.get("card") if isinstance(menu.get("card"), dict) else None
        if card and isinstance(card.get("image"), dict):
            img = card["image"]
            saved = img.get("savedFile")
            if saved:
                p = Path(str(saved))
                ext = _sniff_ext(p)
                if ext:
                    ref = _place_asset(
                        assets_dir,
                        f"nav-card-{_slug(link.get('label'), 'panel')}{ext}",
                        src_file=p,
                    )
                    if ref:
                        img["asset"] = ref
                        note(ref)

    footer = contract.get("footer") if isinstance(contract.get("footer"), dict) else {}
    for s in footer.get("social") or []:
        ic = s.get("icon") if isinstance(s, dict) else None
        if not isinstance(ic, dict):
            continue
        base = f"social-{_slug(s.get('network'), 'link')}"
        # a fetched glyph curated as assets/social-<network>.svg binds directly
        if (assets_dir / f"{base}.svg").exists():
            ic["asset"] = f"assets/{base}.svg"
            note(ic["asset"])
        else:
            _materialize_icon(ic, assets_dir, base)
            note(ic.get("asset"))
    bb = footer.get("bottomBar") if isinstance(footer.get("bottomBar"), dict) else {}
    for b in bb.get("storeBadges") or []:
        img = b.get("img") if isinstance(b, dict) else None
        if not isinstance(img, dict) or not img.get("savedFile"):
            continue
        p = Path(str(img["savedFile"]))
        ext = _sniff_ext(p)
        if ext:
            ref = _place_asset(
                assets_dir,
                f"badge-{_slug(img.get('alt') or p.stem, 'store')}{ext}",
                src_file=p,
            )
            if ref:
                img["asset"] = ref
                note(ref)
    return stamped


def _strip_menu_link(l: dict[str, Any]) -> dict[str, Any]:
    """One mega-menu link fact: label/href + the menu-card anatomy the DOM
    carried (description, hover-reveal flag, icon asset ref)."""
    out: dict[str, Any] = {"label": l.get("label") or "", "href": l.get("href") or ""}
    if l.get("description"):
        out["description"] = l["description"]
    if l.get("descriptionOnHover"):
        out["descriptionOnHover"] = True
    ic = l.get("icon") if isinstance(l.get("icon"), dict) else None
    if ic:
        icon_out: dict[str, Any] = {"kind": ic.get("kind") or ""}
        if ic.get("asset"):
            icon_out["asset"] = ic["asset"]
        elif ic.get("src"):
            icon_out["src"] = ic["src"]
        if ic.get("size"):
            icon_out["size"] = ic["size"]
        out["icon"] = icon_out
    return out


def _strip_chevron(ch: dict[str, Any]) -> dict[str, Any]:
    """Trigger-chevron affordance fact (fid15): harvested artwork ref + geometry +
    open-state motion. The raw svg markup stays in the contract; brand.yaml binds
    the materialized asset."""
    out: dict[str, Any] = {"kind": ch.get("kind") or "svg"}
    if ch.get("asset"):
        out["asset"] = ch["asset"]
    if isinstance(ch.get("box"), dict):
        out["box"] = {"w": ch["box"].get("w") or 0, "h": ch["box"].get("h") or 0}
    if ch.get("gap") is not None:
        out["gap"] = ch["gap"]
    if ch.get("transition"):
        out["transition"] = ch["transition"]
    if ch.get("openTransform"):
        out["openTransform"] = ch["openTransform"]
    return out


def _strip_nav_link(link: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"label": link.get("label") or ""}
    out["href"] = link.get("href") or ""
    # bar-affordance anatomy (fid15 2026-07): utility controls carry their KIND
    # (link vs dropdown), source-semantic ROLE (login/language — from the control's
    # own href/aria contract), harvested glyph, chevron, and dropdown open-state
    # facts. Plain primary tabs carry none of these keys.
    for key in ("kind", "role", "bar", "ariaLabel", "collapsedLabel"):
        if link.get(key):
            out[key] = link[key]
    ic = link.get("icon") if isinstance(link.get("icon"), dict) else None
    if ic:
        icon_out: dict[str, Any] = {"kind": ic.get("kind") or ""}
        if ic.get("asset"):
            icon_out["asset"] = ic["asset"]
        elif ic.get("src"):
            icon_out["src"] = ic["src"]
        if ic.get("size"):
            icon_out["size"] = ic["size"]
        out["icon"] = icon_out
    if isinstance(link.get("chevron"), dict):
        out["chevron"] = _strip_chevron(link["chevron"])
    dd = link.get("dropdown") if isinstance(link.get("dropdown"), dict) else None
    if dd:
        dd_out: dict[str, Any] = {
            "items": [
                {k: v for k, v in {
                    "label": i.get("label") or "",
                    "href": i.get("href") or "",
                    "lang": i.get("lang"),
                    "current": i.get("current"),
                }.items() if v not in (None, "")}
                for i in (dd.get("items") or []) if isinstance(i, dict)
            ],
        }
        if isinstance(dd.get("panel"), dict):
            p = dd["panel"]
            dd_out["panel"] = {k: v for k, v in {
                "w": p.get("w"), "h": p.get("h"), "bg": p.get("bg"),
                "radius": p.get("radius"), "border": p.get("border"),
                "shadow": p.get("shadow"), "paddingY": p.get("paddingY"),
            }.items() if v not in (None, "")}
        if isinstance(dd.get("item"), dict):
            dd_out["item"] = dd["item"]
        if isinstance(dd.get("currentItem"), dict):
            dd_out["currentItem"] = dd["currentItem"]
        out["dropdown"] = dd_out
    menu = link.get("menu") if isinstance(link.get("menu"), dict) else None
    if menu:
        out["menu"] = {
            "columns": [
                {
                    "heading": col.get("heading") or "",
                    "area": col.get("area") or "main",
                    "links": [_strip_menu_link(l) for l in (col.get("links") or [])],
                }
                for col in (menu.get("columns") or [])
            ],
            "featured": [
                {"label": f.get("label") or "", "href": f.get("href") or ""}
                for f in (menu.get("featured") or [])
            ],
        }
        # SIDEBAR RAIL (fix 2026-07): the vertical category tabs (left rail) that a
        # tabbed mega layout renders beside its column groups — ordered labels only,
        # captured structurally from the hidden DOM. Absent ⇒ no key.
        rail = [str(t).strip() for t in (menu.get("sidebarTabs") or []) if str(t).strip()]
        if rail:
            out["menu"]["sidebarTabs"] = rail
        card = menu.get("card") if isinstance(menu.get("card"), dict) else None
        if card:
            img = card.get("image") if isinstance(card.get("image"), dict) else None
            card_out: dict[str, Any] = {
                "title": card.get("title") or "",
                "body": card.get("body") or "",
                "href": card.get("href") or "",
                "area": card.get("area") or "aside",
            }
            if card.get("groupHeading"):
                card_out["groupHeading"] = card["groupHeading"]
            if isinstance(card.get("cta"), dict) and card["cta"].get("label"):
                card_out["cta"] = {"label": card["cta"]["label"], "href": card["cta"].get("href") or ""}
            if img:
                img_out: dict[str, Any] = {"alt": img.get("alt") or ""}
                if img.get("asset"):
                    img_out["asset"] = img["asset"]
                elif img.get("src"):
                    img_out["src"] = img["src"]
                card_out["image"] = img_out
            if isinstance(card.get("surface"), dict):
                card_out["surface"] = {
                    "bg": card["surface"].get("bg") or "",
                    "radius": card["surface"].get("radius") or 0,
                }
            out["menu"]["card"] = card_out
    return out


def _merge_navbar(existing: dict[str, Any] | None, nav: dict[str, Any]) -> dict[str, Any]:
    out = dict(existing) if isinstance(existing, dict) else {}
    out.setdefault("origin", "extracted")
    out.setdefault("source", "extracted")
    out.setdefault("scope", "site-chrome")
    out.setdefault("confidence", "high")
    out.setdefault("archetype", "nav")
    out["twoTier"] = bool(nav.get("twoTier"))
    out["sticky"] = bool(nav.get("sticky"))
    out["surface"] = {
        "bg": nav.get("bg") or "",
        "color": nav.get("color") or "",
        "height": nav.get("height") or 0,
    }
    if isinstance(nav.get("logo"), dict):
        lg = nav["logo"]
        # falsy-preserving merge: curated keys (e.g. a local ``src`` asset) survive
        out["logo"] = _deep_merge_measured(out.get("logo"), {
            "kind": lg.get("kind") or "img",
            "alt": lg.get("alt") or "",
            "href": lg.get("href") or "/",
            "width": lg.get("width") or 0,
            "height": lg.get("height") or 0,
            "srcContract": "../assets/source-chrome.v2.json#nav.logo.src",
        })
    out["utility"] = [_strip_nav_link(l) for l in (nav.get("utility") or [])]
    out["primary"] = [_strip_nav_link(l) for l in (nav.get("primary") or [])]
    out["links"] = [_strip_nav_link(l) for l in (nav.get("links") or [])]
    out["ctas"] = [
        {
            "label": c.get("label") or "",
            "href": c.get("href") or "",
            "filled": bool(c.get("filled")),
            "hasIcon": bool(c.get("hasIcon")),
            "bg": c.get("bg") or "",
            "color": c.get("color") or "",
            "borderRadius": c.get("borderRadius") or 0,
        }
        for c in (nav.get("ctas") or [])
    ]
    if isinstance(nav.get("measured"), dict):
        out["measured"] = _deep_merge_measured(out.get("measured"), nav["measured"])
        # the trigger-chevron family fact binds its materialized ASSET; the raw
        # svg markup stays in the contract (brand.yaml never carries markup blobs)
        m_trig = (out["measured"].get("trigger") or {}).get("chevron") \
            if isinstance(out["measured"].get("trigger"), dict) else None
        if isinstance(m_trig, dict):
            m_trig.pop("svg", None)
    # utility BANNER anatomy (fid15 2026-07): the captured banner's full anatomy
    # (message / cta link + its style / close glyph + box) refreshes the existing
    # utilityBanner fact; provenance/dismissible/surface keys the capture didn't
    # see are preserved. Bg/ink adopt the OBSERVED render (the strip that actually
    # painted at capture), not a component stylesheet's alternate.
    if isinstance(nav.get("banner"), dict) and nav["banner"].get("observed"):
        b = nav["banner"]
        ub = dict(out.get("utilityBanner") or {})
        ub["observed"] = True
        if str(b.get("text") or "").strip():
            ub["text"] = str(b["text"]).strip()
        # BACKDROP-AWARE bg (W1, stress-playbook 2026-07): when the capture carries
        # bgEffective (the alpha declaration composited over its live ancestors —
        # the color the eye actually sees), THAT becomes the brand fact; the raw
        # translucent declaration rides along as bgRaw provenance. A capture
        # without the effective measurement keeps the old behavior verbatim.
        if b.get("bgEffective"):
            ub["bg"] = b["bgEffective"]
            if b.get("bg") and b["bg"] != b["bgEffective"]:
                ub["bgRaw"] = b["bg"]
        elif b.get("bg"):
            ub["bg"] = b["bg"]
        if b.get("ink"):
            ub["ink"] = b["ink"]
        if b.get("fontSize"):
            ub["fontSize"] = b["fontSize"]
        cta = b.get("cta") if isinstance(b.get("cta"), dict) else None
        if cta and cta.get("label"):
            cta_out: dict[str, Any] = {"label": cta["label"], "href": cta.get("href") or "#"}
            for k in ("underline", "color", "fontWeight"):
                if cta.get(k) not in (None, ""):
                    cta_out[k] = cta[k]
            if isinstance(cta.get("arrow"), dict) and cta["arrow"].get("asset"):
                cta_out["arrow"] = {"kind": "svg", "asset": cta["arrow"]["asset"]}
            ub["cta"] = cta_out
        close = b.get("close") if isinstance(b.get("close"), dict) else None
        if close:
            ub["dismissible"] = True
            close_out: dict[str, Any] = {"kind": close.get("kind") or "box-only"}
            if isinstance(close.get("box"), dict):
                close_out["box"] = close["box"]
            for k in ("strokeWidth", "ink", "ariaLabel"):
                if close.get(k) not in (None, ""):
                    close_out[k] = close[k]
            if close.get("asset"):
                close_out["asset"] = close["asset"]
            ub["close"] = close_out
        prov = list(ub.get("provenance") or [])
        frag = str(b.get("fragment") or "").strip()
        src_note = ("captured banner fragment " + Path(frag).name) if frag \
            else "live bar-affordance pass"
        if src_note not in prov:
            prov.append(src_note)
        ub["provenance"] = prov
        ub["source"] = "measured"
        out["utilityBanner"] = ub
    # OPEN-STATE mega-panel geometry (fid4 2026-07): per-tab rendered panel rect,
    # padding, group boxes (+ link-column counts), aside split, card box, and the
    # evidence screenshot name — measured by the Playwright open pass.
    if isinstance(nav.get("megaOpen"), list) and nav["megaOpen"]:
        out["megaOpen"] = [dict(item) for item in nav["megaOpen"] if isinstance(item, dict)]
    out["rules"] = {
        "layout": "split",
        "tiers": "utility-over-primary" if nav.get("twoTier") else "single",
        "justify": "space-between",
        "align": "center",
        "anyButtonHasIcon": bool(nav.get("anyButtonHasIcon")),
    }
    menu_tabs = sum(1 for p in out["primary"] if isinstance(p, dict) and p.get("menu"))
    changelog = list(out.get("changelog") or [])
    changelog.append(
        {
            "ts": _now_iso(),
            "action": "updated",
            "from": None,
            "to": (
                f"two-tier nav: {len(out['utility'])} utility + {len(out['primary'])} primary "
                f"links ({menu_tabs} with mega-menu), {len(out['ctas'])} cta, "
                f"measured={'yes' if out.get('measured') else 'no'}"
            ),
            "by": "chrome-bridge",
            "signalId": None,
            "note": "re-bridged from source_chrome.v2 (mega-menu columns/featured via aria-controls + measured computed styles carried)",
        }
    )
    out["changelog"] = changelog
    return out


def _merge_footer(existing: dict[str, Any] | None, footer: dict[str, Any]) -> dict[str, Any]:
    out = dict(existing) if isinstance(existing, dict) else {}
    out.setdefault("origin", "extracted")
    out.setdefault("source", "extracted")
    out.setdefault("scope", "site-chrome")
    out.setdefault("confidence", "high")
    out.setdefault("archetype", "grid")
    out["surface"] = {"bg": footer.get("bg") or "", "color": footer.get("color") or ""}
    if isinstance(footer.get("logo"), dict):
        lg = footer["logo"]
        out["logo"] = _deep_merge_measured(out.get("logo"), {
            "kind": lg.get("kind") or "img",
            "alt": lg.get("alt") or "",
            "href": lg.get("href") or "/",
            "width": lg.get("width") or 0,
            "height": lg.get("height") or 0,
            "srcContract": "../assets/source-chrome.v2.json#footer.logo.src",
        })
    out["columns"] = [
        {
            "heading": col.get("heading") or "",
            "links": [
                {"label": l.get("label") or "", "href": l.get("href") or ""}
                for l in (col.get("links") or [])
            ],
        }
        for col in (footer.get("columns") or [])
    ]
    social_out: list[dict[str, Any]] = []
    for s in footer.get("social") or []:
        entry: dict[str, Any] = {
            "network": s.get("network") or "link",
            "kind": (s.get("kind") or "").lower() or "icon",
            "href": s.get("href") or "",
        }
        # ICON + BOX facts (fid4 2026-07): the REAL glyph source (asset ref when
        # materialized, else the captured url) + the link's box (size/radius/bg)
        # so renderers draw the source's own artwork — never an invented mark.
        ic = s.get("icon") if isinstance(s.get("icon"), dict) else None
        if ic:
            icon_out: dict[str, Any] = {"kind": ic.get("kind") or ""}
            if ic.get("asset"):
                icon_out["asset"] = ic["asset"]
            elif ic.get("src"):
                icon_out["src"] = ic["src"]
            if ic.get("size"):
                icon_out["size"] = ic["size"]
            if ic.get("ink"):
                icon_out["ink"] = ic["ink"]
            entry["icon"] = icon_out
        box = s.get("box") if isinstance(s.get("box"), dict) else None
        if box:
            entry["box"] = {
                "width": box.get("width") or 0,
                "height": box.get("height") or 0,
                "radius": box.get("radius") or 0,
                "bg": box.get("bg") or "",
            }
        social_out.append(entry)
    out["social"] = social_out
    legal = footer.get("legal") or {}
    # keep agent-authored legal enrichments (e.g. compliance ``disclaimer``) —
    # only the extractor-owned keys are replaced (sysfix 2026-07)
    out_legal = dict(out.get("legal") or {})
    out_legal["text"] = legal.get("text") or out_legal.get("text") or ""
    out_legal["links"] = [
        {"label": l.get("label") or "", "href": l.get("href") or ""}
        for l in (legal.get("links") or [])
    ]
    out["legal"] = out_legal
    # BOTTOM BAR structure (fid4 2026-07): divider/rows/disclaimer/badges/policy
    # facts pass through as extracted — the renderer reproduces the measured row
    # composition instead of guessing. Absent ⇒ key absent (renderers degrade).
    bb = footer.get("bottomBar") if isinstance(footer.get("bottomBar"), dict) else None
    if bb:
        bb_out: dict[str, Any] = {
            "divider": bb.get("divider") or {"present": False},
            "rows": bb.get("rows") or [],
            "gap": bb.get("gap") or 0,
        }
        if bb.get("gapAbove"):
            bb_out["gapAbove"] = bb["gapAbove"]
        if bb.get("disclaimer"):
            bb_out["disclaimer"] = bb["disclaimer"]
        badges = []
        for b in bb.get("storeBadges") or []:
            img = b.get("img") if isinstance(b, dict) else None
            badge: dict[str, Any] = {"href": (b or {}).get("href") or "",
                                     "label": (b or {}).get("label") or ""}
            if isinstance(img, dict):
                img_out: dict[str, Any] = {"alt": img.get("alt") or ""}
                if img.get("asset"):
                    img_out["asset"] = img["asset"]
                elif img.get("src"):
                    img_out["src"] = img["src"]
                badge["img"] = img_out
            badges.append(badge)
        if badges:
            bb_out["storeBadges"] = badges
        if bb.get("policyLinks"):
            bb_out["policyLinks"] = [
                {"label": p.get("label") or "", "href": p.get("href") or ""}
                for p in bb["policyLinks"]
            ]
        out["bottomBar"] = bb_out
    nl = footer.get("newsletter")
    out["newsletter"] = nl if isinstance(nl, dict) else {"present": False}
    if isinstance(footer.get("measured"), dict):
        out["measured"] = _deep_merge_measured(out.get("measured"), footer["measured"])
    # ── layout shape + social style driven by the ACTUAL extracted structure ──
    # grid (HubSpot-style multi-column with headings) vs centered flat link list
    # (WoodWave). socialStyle reflects whether the SOURCE socials were icon glyphs
    # or text labels — never force one or the other.
    has_headings = any((c.get("heading") or "").strip() for c in out["columns"])
    measured = footer.get("measured") if isinstance(footer.get("measured"), dict) else {}
    m_social = measured.get("social") if isinstance(measured.get("social"), dict) else {}
    icon_n = sum(1 for s in out["social"] if s.get("kind") == "icon")
    text_n = sum(1 for s in out["social"] if s.get("kind") == "text")
    if m_social.get("kind") in ("icon", "text"):
        social_style = m_social["kind"]
    elif icon_n or text_n:
        social_style = "icon" if icon_n >= text_n and icon_n > 0 else "text"
    else:
        social_style = "icon"
    out["rules"] = {
        "columns": len(out["columns"]),
        "layout": "grid" if has_headings else "centered",
        "hasColumnHeadings": has_headings,
        "align": "center-bottom",
        "darkInverse": True,
        "socialStyle": social_style,
    }
    changelog = list(out.get("changelog") or [])
    max_links = max((len(c["links"]) for c in out["columns"]), default=0)
    changelog.append(
        {
            "ts": _now_iso(),
            "action": "updated",
            "from": None,
            "to": (
                f"footer {len(out['columns'])} cols (max {max_links} links/col), "
                f"{len(out['social'])} social, {len(out['legal']['links'])} legal links, "
                f"measured={'yes' if out.get('measured') else 'no'}"
            ),
            "by": "chrome-bridge",
            "signalId": None,
            "note": "re-bridged from source_chrome.v2 (per-column cap removed; legal walks copyright nav so Security is captured; measured computed styles carried)",
        }
    )
    out["changelog"] = changelog
    return out


# ── atomic brand.yaml write (preserve comments on every other section) ───────
def _write_brand_yaml_atomic(
    brand_yaml: Path, navbar: dict[str, Any], footer: dict[str, Any]
) -> None:
    raw = brand_yaml.read_text(encoding="utf-8")
    before_doc = yaml.safe_load(raw) or {}
    before_keys = [k for k in before_doc.keys() if k not in ("navbar", "footer")]
    before_layouts = before_doc.get("layouts")
    layouts_len = len(before_layouts) if isinstance(before_layouts, list) else None

    # Splice: replace the trailing top-level navbar:/footer: blocks textually so
    # every other section (and its comments) is byte-preserved. navbar/footer are
    # emitted last by this pipeline; find the first of them at column 0.
    lines = raw.splitlines(keepends=True)
    cut = None
    for i, ln in enumerate(lines):
        if ln.startswith("navbar:") or ln.startswith("footer:"):
            cut = i
            break
    # Keep everything before navbar/footer BYTE-IDENTICAL. navbar/footer are the
    # trailing top-level blocks, so `head` already carries its own separator
    # newlines; appending the regenerated block directly is idempotent (a second
    # run produces the same bytes — no creeping blank lines before navbar).
    head = "".join(lines[:cut]) if cut is not None else raw
    if cut is None and head and not head.endswith("\n"):
        head += "\n"

    block = yaml.safe_dump(
        {"navbar": navbar, "footer": footer},
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=10**9,
    )
    new_text = head + block

    # Validate the candidate text BEFORE replacing the real file.
    after_doc = yaml.safe_load(new_text)
    if not isinstance(after_doc, dict):
        raise RuntimeError("validation failed: regenerated brand.yaml is not a mapping")
    for k in before_keys:
        if k not in after_doc:
            raise RuntimeError(f"validation failed: top-level section '{k}' was dropped")
    if layouts_len is not None:
        after_layouts = after_doc.get("layouts")
        if not isinstance(after_layouts, list) or len(after_layouts) != layouts_len:
            raise RuntimeError(
                f"validation failed: layouts list changed ({layouts_len} -> "
                f"{len(after_layouts) if isinstance(after_layouts, list) else 'missing'})"
            )
    if "navbar" not in after_doc or "footer" not in after_doc:
        raise RuntimeError("validation failed: navbar/footer missing after splice")
    if not after_doc["navbar"].get("primary"):
        raise RuntimeError("validation failed: navbar.primary tier is empty")

    tmp = brand_yaml.with_suffix(brand_yaml.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, brand_yaml)


# ── chrome/index.html generator ─────────────────────────────────────────────
def _social_svg(network: str) -> str:
    path = _SOCIAL_GLYPHS.get((network or "").lower(), _FALLBACK_GLYPH)
    return (
        '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        f'<path d="{path}" /></svg>'
    )


def _glyph_data_uri(asset_ref: str, assets_root: Path | None) -> str:
    """A data: URI for a small harvested SVG glyph (CSS mask-image is a CORS
    fetch, which file:// previews cannot satisfy — inline the artwork instead).
    "" when the file is missing/unreadable (caller degrades)."""
    if not assets_root:
        return ""
    p = assets_root / Path(asset_ref).name
    try:
        data = p.read_bytes()
    except OSError:
        return ""
    if b"<svg" not in data[:300]:
        return ""
    import base64

    return "data:image/svg+xml;base64," + base64.b64encode(data).decode("ascii")


def _social_item_html(s: dict[str, Any], style_default: str,
                      assets_root: Path | None = None) -> str:
    """Render ONE social link honoring its real source representation.

    HARVESTED artwork first (fid4 2026-07): an ``icon.asset`` glyph renders as a
    CSS-mask span painted with the captured ink color — the source's own SVG via
    the source's own mechanic (mask). Inlined as a data: URI so the offline
    file:// preview can paint it. Then: icon kind → bundled monochrome glyph
    fallback; text → the real visible label. NEVER injects an icon the page
    didn't show.
    """
    kind = (s.get("kind") or style_default or "icon").lower()
    href = _esc(s.get("href") or "#")
    net = s.get("network") or "link"
    if kind == "text":
        label = _esc((s.get("label") or net or "").strip())
        return f'<a class="social social-text" href="{href}">{label}</a>'
    ic = s.get("icon") if isinstance(s.get("icon"), dict) else {}
    if ic.get("asset"):
        uri = _glyph_data_uri(str(ic["asset"]), assets_root)
        if uri:
            size = int(ic.get("size") or 20)
            style = f"--glyph: url('{uri}'); width:{size}px; height:{size}px;"
            return (
                f'<a class="social" href="{href}" aria-label="{_esc(net)}">'
                f'<span class="social-glyph" style="{style}" aria-hidden="true"></span></a>'
            )
    return (
        f'<a class="social" href="{href}" aria-label="{_esc(net)}">'
        f"{_social_svg(net)}</a>"
    )


def _social_row_html(social: list[dict[str, Any]], style: str, *, indent: str,
                     assets_root: Path | None = None) -> str:
    """Join social links; text style uses visible slash separators between labels."""
    items = [_social_item_html(s, style, assets_root) for s in social]
    if not items:
        return ""
    if style == "text":
        sep = '<span class="social-sep" aria-hidden="true">/</span>'
        joined = f"\n{indent}{sep}\n{indent}".join(items)
    else:
        joined = f"\n{indent}".join(items)
    return indent + joined


def _nav_link_row(links: list[dict[str, Any]], cls: str) -> str:
    out = []
    for ln in links:
        label = _esc(ln.get("label"))
        href = ln.get("href") or "#"
        out.append(f'      <a class="{cls}" href="{_esc(href)}">{label}</a>')
    return "\n".join(out)


def _logo_inner_html(logo: dict[str, Any], alt_text: str, brand: str) -> str:
    """The renderable INNER markup for an extracted logo (sysfix 2026-07): an inline
    <svg> logo (kind=svg) embeds its captured markup verbatim — the old
    unconditional <img src=""> rendered svg-logo brands as an empty broken image.
    Precedence: captured svg markup → src img → text wordmark (the brand name; real
    text, never a fabricated mark)."""
    logo = logo if isinstance(logo, dict) else {}
    svg_markup = str(logo.get("svg") or "")
    if (logo.get("kind") == "svg" or not logo.get("src")) and svg_markup.lstrip().startswith("<svg"):
        return svg_markup
    src = logo.get("src") or ""
    if src:
        return f'<img src="{_esc(src)}" alt="{_esc(alt_text)}" />'
    return f'<span class="logo-wordmark">{_esc(alt_text or brand)}</span>'


# ── measured-value access (safe nested get with default) ─────────────────────
def _mget(node: Any, *path: str, default: Any = None) -> Any:
    cur = node
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def _px(value: Any, default: int) -> int:
    try:
        n = int(round(float(value)))
        return n if n > 0 else default
    except (TypeError, ValueError):
        return default


def _content_px(value: Any, default: int) -> int:
    """A CONTENT-MEASURE px value with a plausibility floor (sysfix 2026-07): a
    measured content max-width below 480px is capture noise (e.g. a percentage
    max-width mis-parsed as px upstream), never a real page measure — fall back
    instead of rendering 100px-wide chrome."""
    n = _px(value, default)
    return n if n >= 480 else default


def _mega_icon_html(icon: dict[str, Any], asset_prefix: str) -> str:
    """A per-link menu icon from the REAL captured artwork (asset ref); "" when
    none was harvested (never a placeholder glyph)."""
    if not isinstance(icon, dict):
        return ""
    ref = icon.get("asset") or ""
    if not ref:
        return ""
    return (f'<span class="mega-link-icon"><img src="{_esc(asset_prefix + ref)}" '
            f'alt="" aria-hidden="true" /></span>')


def _mega_link_html(l: dict[str, Any], asset_prefix: str) -> str:
    """One mega-menu link with its captured anatomy: icon + title + description.
    Links whose description reveals on hover carry the .desc-hover class (the
    grid-template-rows reveal rides the measured motion facts)."""
    icon_html = _mega_icon_html(l.get("icon"), asset_prefix)
    desc = l.get("description") or ""
    desc_cls = " desc-hover" if l.get("descriptionOnHover") else ""
    desc_html = (
        f'\n              <span class="mega-link-desc"><span>{_esc(desc)}</span></span>'
        if desc else ""
    )
    return (
        f'            <li><a class="mega-link{desc_cls}" href="{_esc(l.get("href") or "#")}">'
        + icon_html
        + f'<span class="mega-link-text"><span class="mega-link-title">{_esc(l.get("label"))}</span>'
        + desc_html
        + "</span></a></li>"
    )


def _mega_card_html(card: dict[str, Any], asset_prefix: str) -> str:
    """The panel's right-side PROMO/FEATURE card, from captured facts only:
    group heading, image asset, title, optional body + CTA label."""
    if not isinstance(card, dict) or not (card.get("title") or card.get("image")):
        return ""
    head = card.get("groupHeading") or ""
    head_html = f'\n            <h4 class="mega-col-head">{_esc(head)}</h4>' if head else ""
    img = card.get("image") if isinstance(card.get("image"), dict) else None
    img_html = ""
    if img and img.get("asset"):
        img_html = (f'\n              <img class="mega-card-img" src="{_esc(asset_prefix + img["asset"])}" '
                    f'alt="{_esc(img.get("alt"))}" />')
    cta = card.get("cta") if isinstance(card.get("cta"), dict) else None
    cta_html = (f'\n              <span class="mega-card-cta">{_esc(cta["label"])} &rarr;</span>'
                if cta and cta.get("label") else "")
    body = card.get("body") or ""
    body_html = f'\n              <p class="mega-card-body">{_esc(body)}</p>' if body else ""
    return (
        f'\n          <div class="mega-aside-card">{head_html}\n'
        f'            <a class="mega-card" href="{_esc(card.get("href") or "#")}">'
        + img_html
        + f'\n              <p class="mega-card-title">{_esc(card.get("title"))}</p>'
        + body_html
        + cta_html
        + "\n            </a>\n          </div>"
    )


def _mega_panel_html(menu: dict[str, Any], asset_prefix: str) -> str:
    """Render a primary tab's captured mega-menu: MAIN column groups + the ASIDE
    rail (compact link group and/or the promo card), mirroring the measured
    panel regions. Facts only — headings, links (icon/description anatomy),
    featured, card."""
    columns = menu.get("columns") or []
    featured = menu.get("featured") or []
    card = menu.get("card") if isinstance(menu.get("card"), dict) else None

    def col_html(col: dict[str, Any]) -> str:
        heading = _esc(col.get("heading"))
        head_html = f'<h4 class="mega-col-head">{heading}</h4>' if heading else ""
        items = "\n".join(_mega_link_html(l, asset_prefix) for l in (col.get("links") or []))
        return (
            '          <div class="mega-col">'
            + head_html
            + ("\n            <ul>\n" + items + "\n            </ul>" if items else "")
            + "</div>"
        )

    main_cols = [c for c in columns if (c.get("area") or "main") != "aside"]
    aside_cols = [c for c in columns if (c.get("area") or "main") == "aside"]
    main_html = "\n".join(col_html(c) for c in main_cols)
    feat_html = ""
    if featured:
        feat_items = "\n".join(
            f'            <li><a href="{_esc(f.get("href") or "#")}">{_esc(f.get("label"))}</a></li>'
            for f in featured
        )
        feat_html = (
            '\n          <div class="mega-featured">\n'
            '            <span class="mega-col-head">Featured</span>\n'
            "            <ul>\n" + feat_items + "\n            </ul>\n          </div>"
        )
    aside_html = ""
    card_html = _mega_card_html(card, asset_prefix) if card else ""
    if aside_cols or card_html:
        aside_html = (
            '\n        <div class="mega-aside">\n'
            + "\n".join(col_html(c) for c in aside_cols)
            + card_html
            + "\n        </div>"
        )
    return (
        '\n        <div class="mega-panel"><div class="mega-inner">\n'
        '        <div class="mega-main"><div class="mega-cols">\n'
        + main_html
        + "\n          </div>"
        + feat_html
        + "\n        </div>"
        + aside_html
        + "\n        </div></div>"
    )


def _caret_html(chevron_uri: str) -> str:
    """The dropdown-trigger caret: the brand's HARVESTED chevron glyph when the
    extraction captured one (CSS-mask data URI, rides currentColor), else the
    text fallback (degrade, never invent artwork)."""
    if chevron_uri:
        return ('<span class="caret caret-glyph" aria-hidden="true" '
                f'style="-webkit-mask-image:url({chevron_uri}); mask-image:url({chevron_uri})">'
                "</span>")
    return '<span class="caret" aria-hidden="true">▾</span>'


def _primary_nav_html(primary: list[dict[str, Any]], asset_prefix: str = "../",
                      chevron_uri: str = "") -> str:
    """Primary tabs; tabs that own a captured mega-menu expand on hover/focus."""
    out = []
    for ln in primary:
        label = _esc(ln.get("label"))
        href = ln.get("href") or "#"
        menu = ln.get("menu") if isinstance(ln.get("menu"), dict) else None
        if menu and (menu.get("columns") or menu.get("featured") or menu.get("card")):
            out.append(
                '      <div class="nav-tab has-menu">\n'
                f'        <a class="nav-link" href="{_esc(href)}">{label}'
                + _caret_html(chevron_uri) + "</a>"
                + _mega_panel_html(menu, asset_prefix)
                + "\n      </div>"
            )
        else:
            out.append(f'      <a class="nav-link" href="{_esc(href)}">{label}</a>')
    return "\n".join(out)


def _utility_bar_html(controls: list[dict[str, Any]], assets_root: Path | None,
                      chevron_uri: str = "") -> str:
    """IN-BAR utility controls (fid15): the bar's trailing cluster — icon links
    (login etc.) and icon dropdowns (locale switchers). Harvested glyphs render
    as CSS-mask data URIs riding currentColor; a control whose glyph wasn't
    captured degrades to its text label. Dropdowns are <details> panels (open
    state works without JS; keyboard-accessible by construction)."""
    out = []
    for u in controls:
        label = _esc(u.get("label"))
        icon = u.get("icon") if isinstance(u.get("icon"), dict) else {}
        icon_uri = _glyph_data_uri(icon.get("asset") or "", assets_root)
        icon_html = (f'<span class="util-icon" aria-hidden="true" '
                     f'style="-webkit-mask-image:url({icon_uri}); mask-image:url({icon_uri})"></span>'
                     if icon_uri else "")
        dd = u.get("dropdown") if isinstance(u.get("dropdown"), dict) else None
        if u.get("kind") == "dropdown" and dd and dd.get("items"):
            shown = _esc(u.get("collapsedLabel") or "")
            aria = _esc(u.get("ariaLabel") or u.get("label"))
            items = "\n".join(
                f'            <li><a class="util-menu-item{" is-current" if i.get("current") else ""}"'
                f' href="{_esc(i.get("href") or "#")}"'
                + (f' hreflang="{_esc(i["lang"])}"' if i.get("lang") else "")
                + (' aria-current="true"' if i.get("current") else "")
                + f">{_esc(i.get('label'))}</a></li>"
                for i in dd["items"]
            )
            out.append(
                '      <details class="util-dropdown">\n'
                f'        <summary class="util-link" aria-label="{aria}">{icon_html}'
                + (f'<span class="util-collapsed-label">{shown}</span>' if shown else "")
                + _caret_html(chevron_uri)
                + "</summary>\n"
                '          <ul class="util-menu" role="menu">\n'
                + items
                + "\n          </ul>\n      </details>"
            )
        else:
            out.append(
                f'      <a class="util-link" href="{_esc(u.get("href") or "#")}">'
                f"{icon_html}{label}</a>"
            )
    return "\n".join(out)


def _footer_col_html(col: dict[str, Any]) -> str:
    heading = _esc(col.get("heading"))
    items = "\n".join(
        f'          <li><a href="{_esc(l.get("href") or "#")}">{_esc(l.get("label"))}</a></li>'
        for l in (col.get("links") or [])
    )
    head_html = f'\n        <h3 class="col-head">{heading}</h3>' if heading else ""
    return (
        '      <nav class="footer-col">'
        + head_html
        + "\n        <ul>\n"
        + items
        + "\n        </ul>\n      </nav>"
    )


def render_chrome_index_html(
    brand: str, contract: dict[str, Any], doc: dict[str, Any],
    assets_root: Path | None = None,
) -> str:
    nav = contract.get("nav") or {}
    footer = contract.get("footer") or {}
    nm = nav.get("measured") or {}
    fm = footer.get("measured") or {}
    if assets_root is None:
        assets_root = PROJECT_DIR / "runs" / brand / "brand" / "assets"
    # merged brand.yaml chrome (asset refs stamped by _materialize_chrome_assets
    # ride on doc's navbar/footer — the contract's own nodes carry them too when
    # the bridge ran materialization first)
    mega_facts = nm.get("megaPanel") if isinstance(nm.get("megaPanel"), dict) else {}
    mega_open = [m for m in (nav.get("megaOpen") or []) if isinstance(m, dict) and m.get("open")]

    # tokens (used only as fallbacks / accent — measured computed styles win)
    action_fg = _color(doc, "action/primary-fg", "#ffffff")
    surface_base = _surface_base(doc, "#ffffff")
    text_default = _color(doc, "text/default", "#1f1f1f")
    # Brand accent for CTA fill + link-hover. Resolved generically from THIS
    # brand's tokens (brand/primary → accent/* → link token) — NEVER a hardcoded
    # cross-brand hue. Falls back to the brand's own text color so a foreign
    # brand's color (e.g. HubSpot's #ff4800) can never leak into another brand.
    brand_accent = _accent(doc)
    brand_primary = brand_accent or text_default
    brand_primary_hover = _color(doc, "brand/primary-hover", brand_primary)
    radius_input = _radius(doc, "input", "0.25rem")
    font_sans = _font_stack(_font(doc, "sans", "Inter"), serif=False)
    font_display = _font_stack(_font(doc, "display", _font(doc, "sans", "Inter")), serif=True)

    # nav surface: a TRANSPARENT bar paints as its ancestor's fill — prefer the
    # captured effectiveBg, then the page surface; never render rgba(0,0,0,0) as
    # if it were a surface (sysfix 2026-07).
    nav_bg = _mget(nm, "bar", "bg", default=nav.get("bg"))
    if _transparent(nav_bg):
        nav_bg = _mget(nm, "bar", "effectiveBg", default="")
    if _transparent(nav_bg):
        nav_bg = surface_base
    nav_color = _mget(nm, "link", "color", default=nav.get("color")) or text_default
    footer_bg = fm.get("bg") or footer.get("bg") or "#1f1f1f"
    # primary inverted text: prefer the measured heading color, then the measured
    # LINK color (the footer element's own inherited `color` is often the page
    # default — dark — even on a dark footer, so it's a poor fallback).
    text_inverted = (
        _mget(fm, "heading", "color", default=None)
        or _mget(fm, "link", "color", default=None)
        or fm.get("color")
        or footer.get("color")
        or "#ffffff"
    )
    footer_link_color = _mget(fm, "link", "color", default="rgba(255,255,255,0.62)")

    # ── link-HOVER color (generic precedence; NEVER a hardcoded brand hue) ──
    #   a) MEASURED a:hover color from the real DOM (nav / footer link),
    #   b) else this brand's accent token (brand/primary → accent/* → link),
    #   c) else the link's OWN base color → no hover color shift at all.
    def _concrete(value: Any) -> str:
        # accept only a usable color literal; reject empty / unresolved var(...)
        s = str(value or "").strip()
        return s if s and "var(" not in s else ""

    nav_hover_measured = _concrete(
        _mget(nm, "linkHoverColor", default="") or _mget(nm, "link", "hoverColor", default="")
    )
    nav_link_hover = nav_hover_measured or brand_accent or nav_color
    footer_hover_measured = _concrete(
        _mget(fm, "linkHoverColor", default="") or _mget(fm, "link", "hoverColor", default="")
    )
    # centered sitemap links sit on the inverted footer surface (base color is
    # text_inverted), so a missing accent → no shift (stays text_inverted).
    footer_link_hover = footer_hover_measured or brand_accent or text_inverted

    # ---- MEASURED nav metrics (rendered px; px is allowed, only vh/vw/dvh banned)
    # content width: extractor measure wins when real; an agent-verified measure in
    # brand.yaml fills the gap (e.g. %-based containers measure as 0); floor+default last.
    doc_nav_max = _mget((doc.get("navbar") or {}), "measured", "contentMaxWidth", default=0)
    nav_content_max = _content_px(nm.get("contentMaxWidth") or doc_nav_max, 1080)
    util_bar_h = _px(nm.get("utilityBarHeight"), 40)
    prim_bar_h = _px(nm.get("primaryBarHeight"), 64)
    nav_logo_w = _px(_mget(nm, "logo", "width"), 120)
    nav_logo_h = _px(_mget(nm, "logo", "height"), 28)
    nav_link_fs = _px(_mget(nm, "link", "fontSize"), 16)
    nav_link_fw = _mget(nm, "link", "fontWeight", default="500")
    nav_link_gap = max(_px(nm.get("linkGap"), 24), 16)
    util_fs = _px(_mget(nm, "utilityLink", "fontSize"), 13)
    util_fw = _mget(nm, "utilityLink", "fontWeight", default="400")
    util_color = _mget(nm, "utilityLink", "color", default=nav_color)
    cta_bg = _mget(nm, "cta", "bg", default=brand_primary) or brand_primary
    cta_color = _mget(nm, "cta", "color", default=action_fg) or action_fg
    cta_fs = _px(_mget(nm, "cta", "fontSize"), 14)
    cta_fw = _mget(nm, "cta", "fontWeight", default="500")
    cta_pt = _px(_mget(nm, "cta", "paddingTop"), 8)
    cta_pb = _px(_mget(nm, "cta", "paddingBottom"), 8)
    cta_pl = _px(_mget(nm, "cta", "paddingLeft"), 16)
    cta_pr = _px(_mget(nm, "cta", "paddingRight"), 16)
    cta_radius = _px(_mget(nm, "cta", "radius"), 8)

    # ---- MEASURED footer metrics
    doc_foot_max = _mget((doc.get("footer") or {}), "measured", "contentMaxWidth", default=0)
    foot_content_max = _content_px(fm.get("contentMaxWidth") or doc_foot_max, 1080)
    foot_pad_top = _px(_mget(fm, "padding", "top"), 48)
    foot_pad_bottom = _px(_mget(fm, "padding", "bottom"), 48)
    foot_head_fs = _px(_mget(fm, "heading", "fontSize"), 18)
    foot_head_fw = _mget(fm, "heading", "fontWeight", default="500")
    # measured heading family wins (a UI-font group label must not restyle into the
    # display serif just because the preview's display var defaults that way)
    foot_head_ff = _mget(fm, "heading", "fontFamily", default="") or "var(--font-display)"
    foot_link_fs = _px(_mget(fm, "link", "fontSize"), 14)
    foot_link_fw = _mget(fm, "link", "fontWeight", default="400")
    foot_link_lh = _px(_mget(fm, "link", "lineHeight"), foot_link_fs + 16)
    # legal/copyright micro-text uses its OWN measured typography (NOT the big
    # sitemap column-link size). Fall back to a small ~13px default when the
    # legal row could not be measured from the real DOM.
    foot_legal_fs = _px(_mget(fm, "legal", "fontSize"), 13)
    foot_legal_fw = _mget(fm, "legal", "fontWeight", default="400")
    foot_logo_w = _px(_mget(fm, "logo", "width"), 120)
    foot_logo_h = _px(_mget(fm, "logo", "height"), 30)
    foot_social_size = _px(_mget(fm, "social", "size"), 22)
    foot_social_fs = _px(_mget(fm, "social", "fontSize"), max(foot_legal_fs, 14))
    foot_social_transform = _mget(fm, "social", "textTransform", default="uppercase") or "uppercase"
    foot_social_ls = _mget(fm, "social", "letterSpacing", default="normal") or "normal"
    foot_col_gap = max(_px(_mget(fm, "grid", "columnGap"), 32), 24)
    bottom_align_raw = (_mget(fm, "bottom", "textAlign", default="center") or "center").lower()
    _align_map = {"start": "left", "left": "left", "center": "center", "end": "right", "right": "right", "justify": "left"}
    bottom_text_align = _align_map.get(bottom_align_raw, "center")
    _flex_map = {"left": "flex-start", "center": "center", "right": "flex-end"}
    bottom_flex_align = _flex_map[bottom_text_align]
    bottom_dir = "column" if bottom_text_align == "center" else "row"

    # ---- MEASURED bottom-bar + social-box facts (fid4 2026-07) ----
    bb_facts = footer.get("bottomBar") if isinstance(footer.get("bottomBar"), dict) else {}
    _bb_div = bb_facts.get("divider") if isinstance(bb_facts.get("divider"), dict) else {}
    bb_div_color = _bb_div.get("color") or "var(--footer-border)"
    try:
        bb_div_opacity = float(_bb_div.get("opacity", 1) or 1)
    except (TypeError, ValueError):
        bb_div_opacity = 1.0
    bb_gap = _px(bb_facts.get("gap"), 28)
    _bb_rows = [r for r in (bb_facts.get("rows") or []) if isinstance(r, dict)]
    _soc_row = next((r for r in _bb_rows if "social" in (r.get("kinds") or [])), {})
    bb_row2_justify = _soc_row.get("justify") or ""
    if bb_row2_justify in ("", "normal"):
        bb_row2_justify = "flex-end"
    bb_row2_gap = _px(_soc_row.get("gap"), 40)
    _copy_row = next((r for r in _bb_rows if "copyright" in (r.get("kinds") or [])), {})
    bb_row1_align = _copy_row.get("align") or ""
    if bb_row1_align in ("", "normal"):
        bb_row1_align = "flex-end"
    bb_row1_gap = _px(_copy_row.get("gap"), 26)
    _soc_box = next((s.get("box") for s in (footer.get("social") or [])
                     if isinstance(s, dict) and isinstance(s.get("box"), dict)), None) or {}
    soc_box_w = _px(_soc_box.get("width"), 0)
    soc_box_h = _px(_soc_box.get("height"), 0)
    soc_box_r = _px(_soc_box.get("radius"), 0)
    soc_box_bg = _soc_box.get("bg") or ""
    _soc_ic = next((s.get("icon") for s in (footer.get("social") or [])
                    if isinstance(s, dict) and isinstance(s.get("icon"), dict)), None) or {}
    soc_ink = _soc_ic.get("ink") or ""

    # nav content
    nav_logo = nav.get("logo") or {}
    logo_href = nav_logo.get("href") or "/"
    logo_alt = nav_logo.get("alt") or brand
    logo_inner = _logo_inner_html(nav_logo, logo_alt, brand)
    utility = nav.get("utility") or []
    primary = nav.get("primary") or (nav.get("links") or [])
    ctas = nav.get("ctas") or []

    # trailing utility controls live IN the primary bar (fid15); only a genuine
    # above-bar tier renders the utility row.
    tier_utility = [u for u in utility if u.get("bar") != "trailing"]
    bar_utility = [u for u in utility if u.get("bar") == "trailing"]
    trig_chev = _mget(nav, "measured", "trigger", "chevron", default=None)
    chevron_uri = _glyph_data_uri((trig_chev or {}).get("asset") or "", assets_root) \
        if isinstance(trig_chev, dict) else ""
    util_html = _nav_link_row(tier_utility, "util-link")
    utility_block = (
        '  <div class="nav-utility"><div class="inner nav-utility-inner">\n'
        + util_html
        + "\n  </div></div>\n"
        if tier_utility
        else ""
    )
    bar_util_html = _utility_bar_html(bar_utility, assets_root, chevron_uri)
    primary_html = _primary_nav_html(primary, asset_prefix="../", chevron_uri=chevron_uri)

    # ---- utility banner (fid15): captured anatomy — message / cta / close ----
    banner = nav.get("banner") if isinstance(nav.get("banner"), dict) else None
    banner_html = ""
    banner_css = ""
    if banner and banner.get("observed") and str(banner.get("text") or "").strip():
        b_cta = banner.get("cta") if isinstance(banner.get("cta"), dict) else None
        cta_frag = ""
        if b_cta and b_cta.get("label"):
            cta_frag = (f' <a class="banner-cta" href="{_esc(b_cta.get("href") or "#")}">'
                        f"{_esc(b_cta['label'])}</a>")
        b_close = banner.get("close") if isinstance(banner.get("close"), dict) else None
        close_frag = ""
        if b_close:
            cw = _px((b_close.get("box") or {}).get("w"), 16)
            chh = _px((b_close.get("box") or {}).get("h"), 16)
            sw = _px(b_close.get("strokeWidth"), 2)
            if b_close.get("kind") == "svg" and b_close.get("asset"):
                uri = _glyph_data_uri(b_close["asset"], assets_root)
                glyph = (f'<span class="banner-close-glyph" style="-webkit-mask-image:url({uri}); '
                         f'mask-image:url({uri})"></span>') if uri else "&#215;"
            else:
                # box-only capture: the close X drawn FROM the measured facts
                # (box + stroke width + ink) — reconstruction, not invented artwork
                glyph = (f'<svg viewBox="0 0 {cw} {chh}" width="{cw}" height="{chh}" '
                         f'fill="none" stroke="currentColor" stroke-width="{sw}" '
                         'stroke-linecap="round" aria-hidden="true">'
                         f'<path d="M{sw} {sw}L{cw - sw} {chh - sw}M{cw - sw} {sw}L{sw} {chh - sw}"/></svg>')
            close_frag = (f'<button class="banner-close" type="button" '
                          f'aria-label="{_esc(b_close.get("ariaLabel") or "Dismiss")}">{glyph}</button>')
        banner_html = (
            '  <div class="banner">\n'
            f'    <p class="banner-text">{_esc(banner.get("text"))}{cta_frag}</p>\n'
            f"    {close_frag}\n"
            "  </div>\n"
        )
        cta_deco = "underline" if (b_cta or {}).get("underline") else "none"
        cta_weight = str((b_cta or {}).get("fontWeight") or "600")
        banner_css = f"""
  /* ---- utility banner (fid15): captured anatomy, measured presentation ---- */
  .banner {{
    position: relative; display: flex; align-items: center; justify-content: center;
    background: {banner.get('bg') or 'var(--nav-color)'};
    color: {banner.get('ink') or 'var(--nav-bg)'};
    font-size: {_px(banner.get('fontSize'), 14)}px;
    padding: 10px 56px; text-align: center;
  }}
  .banner-text {{ margin: 0; }}
  .banner-cta {{
    color: {(b_cta or {}).get('color') or 'inherit'};
    font-weight: {cta_weight}; text-decoration: {cta_deco}; text-underline-offset: 2px;
  }}
  .banner-close {{
    position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
    display: inline-flex; align-items: center; justify-content: center;
    width: {_px(((b_close or {}).get('box') or {}).get('w'), 16) + 10}px;
    height: {_px(((b_close or {}).get('box') or {}).get('h'), 16) + 10}px;
    background: none; border: 0; cursor: pointer;
    color: {(b_close or {}).get('ink') or 'inherit'};
  }}
"""

    # ---- measured bar-affordance presentation facts (fid15) ----
    chev_w = _px((trig_chev or {}).get("box", {}).get("w") if isinstance(trig_chev, dict) else 0, 14)
    chev_h = _px((trig_chev or {}).get("box", {}).get("h") if isinstance(trig_chev, dict) else 0, 14)
    chev_gap = _px((trig_chev or {}).get("gap") if isinstance(trig_chev, dict) else 0, 4)
    chev_open_tf = str((trig_chev or {}).get("openTransform") or "") if isinstance(trig_chev, dict) else ""
    if not chev_open_tf:
        chev_open_tf = "rotate(180deg)"
    _dd0 = next((u.get("dropdown") for u in bar_utility
                 if isinstance(u.get("dropdown"), dict)), None) or {}
    _ddp = _dd0.get("panel") if isinstance(_dd0.get("panel"), dict) else {}
    _ddi = _dd0.get("item") if isinstance(_dd0.get("item"), dict) else {}
    _ddc = _dd0.get("currentItem") if isinstance(_dd0.get("currentItem"), dict) else {}
    util_panel_bg = _ddp.get("bg") or "var(--nav-bg)"
    util_panel_border = _ddp.get("border") or "1px solid var(--border-default)"
    util_panel_radius = _px(_ddp.get("radius"), 6)
    util_panel_pad_y = _px(_ddp.get("paddingY"), 8)
    util_panel_minw = max(150, min(_px(_ddp.get("w"), 180), 320))
    util_item_fs = _px(_ddi.get("fontSize"), nav_link_fs)
    util_item_pad = str(_ddi.get("padding") or "10px 12px")
    util_item_radius = _px(_ddi.get("radius"), 2)
    util_cur_bg = _ddc.get("bg") or "var(--nav-color)"
    util_cur_ink = _ddc.get("color") or "var(--nav-bg)"
    cta_html = "\n".join(
        f'      <a class="nav-cta" href="{_esc(c.get("href") or "#")}">{_esc(c.get("label"))}</a>'
        for c in ctas
    )

    # ---- MEASURED mega-panel presentation facts (fid4 2026-07) ----
    # Panel MODE from rendered open-state geometry: a panel spanning ~the full
    # viewport is a full-bleed band under the bar; anything narrower stays the
    # bounded card. Aside split + link-column counts come from the same pass.
    mega_full_bleed = any(
        (m.get("panel") or {}).get("w", 0) >= 1280 and (m.get("panel") or {}).get("x", 99) <= 8
        for m in mega_open
    )
    mega_bg = _mget(mega_facts, "surface", "bg", default="") or nav_bg
    mega_border_top = str(_mget(mega_facts, "surface", "borderTop", default="") or "")
    mega_motion = mega_facts.get("motion") if isinstance(mega_facts.get("motion"), dict) else {}
    _mp = mega_motion.get("panel") if isinstance(mega_motion.get("panel"), dict) else {}
    mega_dur = (str(_mp.get("duration") or "0.2s").split(",")[0].strip()) or "0.2s"
    mega_ease = (str(_mp.get("easing") or "ease").split(",")[0].strip()) or "ease"
    hidden_tf = str(_mget(mega_facts, "hiddenState", "transform", default="") or "")
    # matrix(1,0,0,1,tx,ty) → the panel's closed-state y offset
    mega_shift = 8
    m_match = re.search(r"matrix\([^)]*,\s*(-?\d+(?:\.\d+)?)\)\s*$", hidden_tf)
    if m_match:
        try:
            mega_shift = max(0, int(round(float(m_match.group(1)))))
        except ValueError:
            pass
    _ml = mega_facts.get("link") if isinstance(mega_facts.get("link"), dict) else {}
    mega_link_fs = _px(_ml.get("fontSize"), max(nav_link_fs - 1, 13))
    mega_link_radius = _px(_ml.get("radius"), 4)
    mega_link_pad = str(_ml.get("padding") or "8px")
    mega_link_color = _ml.get("color") or "inherit"
    mega_link_hover_bg = _ml.get("hoverBg") or ""
    _md = mega_motion.get("description") if isinstance(mega_motion.get("description"), dict) else {}
    mega_desc_dur = (str(_md.get("duration") or "0.3s").split(",")[0].strip()) or "0.3s"
    _mc = mega_motion.get("chevron") if isinstance(mega_motion.get("chevron"), dict) else {}
    mega_caret_dur = (str(_mc.get("duration") or "0.2s").split(",")[0].strip()) or "0.2s"
    _mg = mega_facts.get("groupTitle") if isinstance(mega_facts.get("groupTitle"), dict) else {}
    mega_head_fs = _px(_mg.get("fontSize"), 13)
    mega_head_color = _mg.get("color") or "inherit"
    mega_head_tt = _mg.get("textTransform") or "none"
    mega_head_ls = _mg.get("letterSpacing") or "normal"
    mega_head_fw = _mg.get("fontWeight") or "500"
    _ma = mega_facts.get("aside") if isinstance(mega_facts.get("aside"), dict) else {}
    mega_aside_border = str(_ma.get("borderLeft") or "")
    mega_aside_pad = _px(_ma.get("paddingLeft"), 16)
    # aside width: measured open-state fraction of the panel width
    aside_fracs = [float((m.get("aside") or {}).get("widthFraction") or 0) for m in mega_open]
    aside_fracs = [f for f in aside_fracs if 0.1 <= f <= 0.6]
    mega_aside_pct = round((sum(aside_fracs) / len(aside_fracs)) * 100, 1) if aside_fracs else 24.0
    # main groups render their links over N measured columns (mode of linkColumns)
    link_cols: list[int] = []
    for m in mega_open:
        for g in m.get("groups") or []:
            if not g.get("aside") and g.get("linkColumns"):
                link_cols.append(int(g["linkColumns"]))
    mega_link_columns = max(set(link_cols), key=link_cols.count) if link_cols else 3
    mega_open_shift_css = f"translateY({mega_shift}px)" if mega_shift else "none"

    # footer content
    f_logo = footer.get("logo") or {}
    f_logo_src = f_logo.get("src") or ""
    f_logo_href = f_logo.get("href") or "/"
    f_logo_alt = f_logo.get("alt") or brand
    f_logo_renderable = bool(f_logo_src) or str(f_logo.get("svg") or "").lstrip().startswith("<svg")
    f_logo_inner = _logo_inner_html(f_logo, f_logo_alt, brand) if f_logo_renderable else ""
    columns = footer.get("columns") or []
    social = footer.get("social") or []
    legal = footer.get("legal") or {}
    legal_copy = _esc(legal.get("text"))
    legal_links = legal.get("links") or []

    # ── decide footer SHAPE + social STYLE from the real extracted structure ──
    # grid: source has real column headings (HubSpot). centered: flat link list
    # with NO headings (WoodWave). socialStyle: icon glyphs ONLY when the source
    # socials were icon-based; text labels when the source used text.
    has_headings = any((c.get("heading") or "").strip() for c in columns)
    footer_layout = "grid" if has_headings else "centered"
    m_social = fm.get("social") if isinstance(fm.get("social"), dict) else {}
    icon_n = sum(1 for s in social if (s.get("kind") or "").lower() == "icon")
    text_n = sum(1 for s in social if (s.get("kind") or "").lower() == "text")
    if m_social.get("kind") in ("icon", "text"):
        social_style = m_social["kind"]
    elif icon_n or text_n:
        social_style = "icon" if icon_n >= text_n and icon_n > 0 else "text"
    else:
        social_style = "icon"

    legal_links_html = "\n".join(
        f'        <a href="{_esc(l.get("href") or "#")}">{_esc(l.get("label"))}</a>'
        for l in legal_links
    )

    # always defined (the .footer-cols CSS rule references it even in centered mode)
    grid_template = "1fr"

    if footer_layout == "grid":
        # ── MEASURED grid tracks win (sysfix 2026-07): when the extraction measured
        # the footer's real column geometry (grid templateColumns, else the counted
        # physical column wrappers), chunk the headed groups evenly into that many
        # cells (an 8-group / 4-column footer stacks two groups per column — the
        # source geometry). Only fall back to the legacy heuristic (widen link-heavy
        # first column, stack the tail) when nothing was measured.
        m_template = str(_mget(fm, "grid", "templateColumns", default="") or "")
        m_tracks = len([t for t in m_template.split() if t and "(" not in t])
        if not (2 <= m_tracks <= 8):
            m_tracks = _px(_mget(fm, "grid", "wrapperCount"), 0)
        # measured per-wrapper distribution (e.g. [1,2,1,2,1,1]) reproduces the
        # source stacking exactly; fall back to even chunking when absent/stale.
        m_sizes = _mget(fm, "grid", "wrapperSizes", default=None)
        if not (isinstance(m_sizes, list) and all(isinstance(n, int) and n > 0 for n in m_sizes)
                and sum(m_sizes) == len(columns) and 2 <= len(m_sizes) <= 8):
            m_sizes = None
        col_parts = []
        if m_sizes:
            cells, pos = [], 0
            for n in m_sizes:
                cells.append(columns[pos:pos + n])
                pos += n
            grid_template = " ".join(["1fr"] * len(cells))
            for cell in cells:
                inner = "\n".join(_footer_col_html(c) for c in cell)
                cls = "footer-cell footer-cell-stack" if len(cell) > 1 else "footer-cell"
                col_parts.append(f'      <div class="{cls}">\n' + inner + "\n      </div>")
        elif 2 <= m_tracks <= 8 and len(columns) >= m_tracks:
            per = -(-len(columns) // m_tracks)  # ceil
            cells = [columns[i:i + per] for i in range(0, len(columns), per)]
            grid_template = " ".join(["1fr"] * len(cells))
            for cell in cells:
                inner = "\n".join(_footer_col_html(c) for c in cell)
                cls = "footer-cell footer-cell-stack" if len(cell) > 1 else "footer-cell"
                col_parts.append(f'      <div class="{cls}">\n' + inner + "\n      </div>")
        else:
            wide = columns[:1]
            solo = columns[1:3]
            stacked = columns[3:]
            track = []
            if wide:
                track.append("1.7fr")
            track.extend(["1fr"] * len(solo))
            if stacked:
                track.append("1fr")
            grid_template = " ".join(track) or "1fr"
            if wide:
                col_parts.append(
                    '      <div class="footer-cell cell-wide">\n'
                    + _footer_col_html(wide[0])
                    + "\n      </div>"
                )
            for col in solo:
                col_parts.append(
                    '      <div class="footer-cell">\n' + _footer_col_html(col) + "\n      </div>"
                )
            if stacked:
                inner = "\n".join(_footer_col_html(c) for c in stacked)
                col_parts.append('      <div class="footer-cell footer-cell-stack">\n' + inner + "\n      </div>")
        cols_html = "\n".join(col_parts)
        social_html = _social_row_html(social, social_style, indent="        ",
                                       assets_root=assets_root)
        # brand mark only when the extraction found a RENDERABLE one (sysfix
        # 2026-07): no empty <img>, and never a third-party badge stand-in.
        f_logo_block = (
            f'          <a class="footer-brand" href="{_esc(f_logo_href)}" aria-label="{_esc(f_logo_alt)}">\n'
            f"            {f_logo_inner}\n"
            f"          </a>\n"
            if f_logo_inner
            else ""
        )

        # ── MEASURED bottom bar (fid4 2026-07): copyright + disclaimer left with
        # store badges right, a divider rule, then the policy-link + social row
        # aligned per the measured row facts. Only when the extraction captured
        # bottomBar structure; other brands keep the legacy composition below.
        bb = footer.get("bottomBar") if isinstance(footer.get("bottomBar"), dict) else None
        if bb:
            badges_html = ""
            badge_frags = []
            for b in bb.get("storeBadges") or []:
                img = b.get("img") if isinstance(b, dict) else None
                ref = (img or {}).get("asset") or ""
                if not ref:
                    continue
                badge_frags.append(
                    f'          <a href="{_esc(b.get("href") or "#")}">'
                    f'<img src="{_esc("../" + ref)}" alt="{_esc((img or {}).get("alt"))}" /></a>'
                )
            if badge_frags:
                badges_html = ('        <div class="fb-badges">\n'
                               + "\n".join(badge_frags) + "\n        </div>")
            disclaimer = str(bb.get("disclaimer") or "")
            disclaimer_html = (
                f'\n          <p class="fb-disclaimer">{_esc(disclaimer)}</p>' if disclaimer else ""
            )
            policy = bb.get("policyLinks") or legal_links
            policy_html = "\n".join(
                f'            <a href="{_esc(p.get("href") or "#")}">{_esc(p.get("label"))}</a>'
                for p in policy
            )
            fb_logo_block = (
                f'      <a class="footer-brand" href="{_esc(f_logo_href)}" aria-label="{_esc(f_logo_alt)}">\n'
                f"        {f_logo_inner}\n      </a>\n"
                if f_logo_inner else ""
            )
            footer_html = f"""  <footer class="footer">
    <div class="inner">
      <div class="footer-cols">
{cols_html}
      </div>
      <div class="footer-bottom footer-bottom-bar">
{fb_logo_block}        <div class="fb-row fb-row1">
          <div class="fb-copy">
            <span class="copyright">{legal_copy}</span>{disclaimer_html}
          </div>
{badges_html}
        </div>
        <div class="fb-divider" role="presentation"></div>
        <div class="fb-row fb-row2">
          <nav class="fb-policy" aria-label="Legal">
{policy_html}
          </nav>
          <div class="social-row">
{social_html}
          </div>
        </div>
      </div>
    </div>
  </footer>"""
        else:
            footer_html = f"""  <footer class="footer">
    <div class="inner">
      <div class="footer-cols">
{cols_html}
      </div>
      <div class="footer-bottom">
        <div class="footer-bottom-brand">
          <div class="social-row">
{social_html}
          </div>
{f_logo_block}        </div>
        <div class="footer-legal">
          <span class="copyright">{legal_copy}</span>
{legal_links_html}
        </div>
      </div>
    </div>
  </footer>"""
    else:
        # ── CENTERED flat layout (WoodWave): oversized slash sitemap, centered text
        # social row, thin rule, small centered legal/copyright. The sitemap links
        # are the footer's flat link list MINUS the social + legal links (so they
        # are not double-rendered). All real, nothing fabricated. ──
        social_hrefs = {(s.get("href") or "").strip() for s in social}
        social_labels = {(s.get("label") or "").strip().lower() for s in social}
        social_labels |= {(s.get("network") or "").strip().lower() for s in social}
        legal_hrefs = {(l.get("href") or "").strip() for l in legal_links}
        legal_labels = {(l.get("label") or "").strip().lower() for l in legal_links}
        sitemap_links: list[dict[str, Any]] = []
        seen_site: set[str] = set()
        for col in columns:
            for l in col.get("links") or []:
                lbl = (l.get("label") or "").strip()
                href = (l.get("href") or "").strip()
                low = lbl.lower()
                if not lbl:
                    continue
                if href in social_hrefs or low in social_labels:
                    continue
                if href in legal_hrefs or low in legal_labels:
                    continue
                if low in seen_site:
                    continue
                seen_site.add(low)
                sitemap_links.append({"label": lbl, "href": href})

        sep = '<span class="sitemap-sep" aria-hidden="true">/</span>'
        sitemap_html = f"\n          {sep}\n          ".join(
            f'<a class="sitemap-link" href="{_esc(l["href"] or "#")}">{_esc(l["label"])}</a>'
            for l in sitemap_links
        )
        social_html = _social_row_html(social, social_style, indent="          ",
                                       assets_root=assets_root)
        logo_html = (
            f'      <a class="footer-brand" href="{_esc(f_logo_href)}" aria-label="{_esc(f_logo_alt)}">\n'
            f"        {f_logo_inner}\n"
            f"      </a>\n"
            if f_logo_inner
            else ""
        )
        sitemap_block = (
            f'      <nav class="footer-sitemap">\n          {sitemap_html}\n      </nav>\n'
            if sitemap_links
            else ""
        )
        social_block = (
            f'      <div class="footer-social-row">\n{social_html}\n      </div>\n'
            if social_html
            else ""
        )
        legal_block = (
            f'        <div class="footer-legal-links">\n{legal_links_html}\n        </div>\n'
            if legal_links_html
            else ""
        )
        copy_block = (
            f'        <div class="footer-copy">{legal_copy}</div>\n' if legal_copy else ""
        )

        footer_html = f"""  <footer class="footer footer-centered">
    <div class="inner">
{logo_html}{sitemap_block}{social_block}      <div class="footer-rule"></div>
      <div class="footer-legal footer-legal-center">
{legal_block}{copy_block}      </div>
    </div>
  </footer>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{_esc(brand)} — exact nav/footer (extracted)</title>
<meta name="robots" content="noindex" />
<style>
  /* Tokens + MEASURED computed styles from runs/{_esc(brand)}/brand/brand.yaml
     (navbar.measured / footer.measured) + source-chrome.v2.json. Measured px
     values render as px; ONLY viewport-relative sizing uses cqi/cqh — never vh/vw/dvh. */
  :root {{
    --brand-primary: {brand_primary};
    --brand-primary-hover: {brand_primary_hover};
    --nav-link-hover: {nav_link_hover};
    --footer-link-hover: {footer_link_hover};
    --action-primary-fg: {action_fg};
    --surface-base: {surface_base};
    --text-default: {text_default};
    --text-inverted: {text_inverted};
    --footer-link: {footer_link_color};
    --border-default: rgba(0,0,0,0.11);
    --footer-border: rgba(255,255,255,0.16);
    --radius-input: {radius_input};
    --font-sans: {font_sans};
    --font-display: {font_display};
    --nav-bg: {nav_bg};
    --nav-color: {nav_color};
    --footer-bg: {footer_bg};
  }}

  /* CRITICAL: container-query frame. ONLY cqw/cqh/cqi sizing — never vh/vw/dvh. */
  html, body {{
    container-type: size;
    container-name: frame;
    margin: 0;
  }}
  html {{ height: 100%; }}
  body {{
    height: 100cqh;
    overflow-y: auto;
    background: var(--surface-base);
    color: var(--text-default);
    font-family: var(--font-sans);
    font-weight: 400;
    -webkit-font-smoothing: antialiased;
  }}
  * {{ box-sizing: border-box; }}
  a {{ text-decoration: none; color: inherit; }}

  .wrap {{ width: 100cqi; }}
  .inner {{
    width: min({nav_content_max}px, 92cqi);
    margin: 0 auto;
    padding-inline: 4cqi;
  }}

  /* ---- NAV (two tiers: utility row above the primary bar) — measured px ---- */
  header.nav {{
    background: var(--nav-bg);
    color: var(--nav-color);
    border-bottom: 1px solid var(--border-default);
    position: sticky;
    top: 0;
    z-index: 10;
  }}
  .nav-utility {{ border-bottom: 1px solid var(--border-default); }}
  .nav-utility-inner {{
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 2.2cqi;
    min-height: {util_bar_h}px;
  }}
  .util-link {{
    font-size: {util_fs}px;
    font-weight: {util_fw};
    color: {util_color};
    opacity: 0.82;
    white-space: nowrap;
  }}
  .util-link:hover {{ opacity: 1; color: var(--nav-link-hover); }}
  .nav-inner {{
    display: flex;
    align-items: center;
    gap: 3cqi;
    min-height: {prim_bar_h}px;
  }}
  .nav-logo {{ display: inline-flex; align-items: center; color: var(--nav-color); }}
  .nav-logo img, .nav-logo svg {{ height: {nav_logo_h}px; width: auto; max-width: {nav_logo_w}px; display: block; }}
  .logo-wordmark {{ font-family: var(--font-display); font-size: {max(nav_logo_h - 8, 16)}px; font-weight: 600; white-space: nowrap; }}
  .nav-links {{
    display: flex;
    align-items: center;
    gap: {nav_link_gap}px;
    flex: 1 1 auto;
  }}
  .nav-tab {{ position: static; }}
  .nav-link {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: {nav_link_fs}px;
    font-weight: {nav_link_fw};
    color: var(--nav-color);
    white-space: nowrap;
    cursor: pointer;
  }}
  .nav-link:hover {{ color: var(--nav-link-hover); }}
  .nav-link .caret {{ font-size: 0.7em; opacity: 0.6; }}
  .nav-actions {{ display: flex; align-items: center; gap: 1.5cqi; margin-left: auto; }}
  .nav-cta {{
    background: {cta_bg};
    color: {cta_color};
    font-weight: {cta_fw};
    font-size: {cta_fs}px;
    padding: {cta_pt}px {cta_pr}px {cta_pb}px {cta_pl}px;
    border-radius: {cta_radius}px;
    white-space: nowrap;
  }}
  .nav-cta:hover {{ filter: brightness(0.92); }}

  /* ---- mega-menu panel: shows on hover/focus of a primary tab ----
     GEOMETRY + MOTION ARE MEASURED (fid4 2026-07): panel MODE comes from the
     rendered open-state rect (a ~viewport-wide panel is a full-bleed band under
     the bar; narrower stays a bounded card); surface/border/hidden-state offset/
     durations/easings come from the panel's computed styles; the main/aside
     split + per-group link columns come from the open-state measurement. */
  .nav-tab {{ position: {('static' if mega_full_bleed else 'relative')}; }}
  .mega-panel {{
    position: absolute;
    left: 0;
    {('right: 0; width: auto; max-width: none; border-radius: 0; border-left: 0; border-right: 0;'
      if mega_full_bleed else
      f'right: auto; width: max-content; max-width: min({nav_content_max}px, 88cqi); border-radius: 12px;')}
    top: 100%;
    background: {mega_bg};
    {(f'border-top: 1px solid {mega_border_top.split(" ", 1)[1]};' if ' ' in mega_border_top else 'border-top: 1px solid var(--border-default);')}
    border-bottom: 1px solid var(--border-default);
    box-shadow: 0 18px 40px rgba(0,0,0,0.10);
    visibility: hidden;
    opacity: 0;
    transform: {mega_open_shift_css};
    transition: opacity {mega_dur} {mega_ease}, transform {mega_dur} {mega_ease}, visibility {mega_dur} {mega_ease};
    z-index: 20;
  }}
  .nav-tab.has-menu:hover .mega-panel,
  .nav-tab.has-menu:focus-within .mega-panel {{
    visibility: visible;
    opacity: 1;
    transform: none;
  }}
  .nav-tab.has-menu:hover .caret,
  .nav-tab.has-menu:focus-within .caret {{ transform: {chev_open_tf}; }}
  .nav-link .caret {{ transition: transform {mega_caret_dur} {mega_ease}; }}

  /* ---- bar affordances (fid15): HARVESTED glyphs as currentColor masks;
     geometry (chevron box/gap, dropdown panel/item) is measured. ---- */
  .caret-glyph {{
    display: inline-block; width: {chev_w}px; height: {chev_h}px;
    margin-left: {chev_gap}px; background: currentColor;
    -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;
    -webkit-mask-position: center; mask-position: center;
    -webkit-mask-size: contain; mask-size: contain;
    transition: transform {mega_caret_dur} {mega_ease};
  }}
  .util-icon {{
    display: inline-block; width: 1.35em; height: 1.35em;
    background: currentColor; flex: 0 0 auto;
    -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;
    -webkit-mask-position: center; mask-position: center;
    -webkit-mask-size: contain; mask-size: contain;
  }}
  .nav-actions .util-link {{
    display: inline-flex; align-items: center; gap: 8px;
    font-size: {nav_link_fs}px; font-weight: {nav_link_fw};
    color: var(--nav-color); white-space: nowrap; cursor: pointer;
    list-style: none;
  }}
  .nav-actions .util-link::-webkit-details-marker {{ display: none; }}
  .nav-actions .util-link:hover {{ color: var(--nav-link-hover); }}
  .util-dropdown {{ position: relative; }}
  .util-dropdown[open] .caret,
  .util-dropdown[open] .caret-glyph {{ transform: {chev_open_tf}; }}
  .util-dropdown .util-collapsed-label:empty {{ display: none; }}
  .util-menu {{
    position: absolute; right: 0; top: calc(100% + 8px);
    margin: 0; padding: {util_panel_pad_y}px;
    list-style: none; min-width: {util_panel_minw}px; max-height: 60vh; overflow-y: auto;
    background: {util_panel_bg}; border: {util_panel_border};
    border-radius: {util_panel_radius}px;
    box-shadow: 0 12px 32px rgba(0,0,0,0.12);
    z-index: 30;
  }}
  .util-menu-item {{
    display: block; padding: {util_item_pad};
    font-size: {util_item_fs}px; color: var(--nav-color);
    border-radius: {util_item_radius}px; white-space: nowrap;
  }}
  .util-menu-item:hover {{ background: var(--border-default); }}
  .util-menu-item.is-current {{ background: {util_cur_bg}; color: {util_cur_ink}; }}
  .mega-inner {{
    {(f'width: min({nav_content_max}px, 92cqi); margin: 0 auto; padding: 2rem 4cqi 2.5rem;'
      if mega_full_bleed else 'width: auto; margin: 0; padding: 1.75rem 2rem;')}
    display: flex;
    gap: 2.5rem;
    align-items: stretch;
  }}
  .mega-main {{ flex: 1 1 auto; min-width: 0; }}
  /* main groups STACK vertically; each group's links flow over the measured
     column count */
  .mega-main .mega-cols {{
    display: flex;
    flex-direction: column;
    gap: 1.6rem;
  }}
  .mega-main .mega-col ul {{
    display: grid;
    grid-template-columns: repeat({mega_link_columns}, minmax(0, 1fr));
    gap: 0.35rem 1.25rem;
  }}
  .mega-aside {{
    flex: 0 0 {mega_aside_pct}%;
    max-width: {mega_aside_pct}%;
    {(f'border-left: 1px solid {mega_aside_border.split(" ", 1)[1]};' if ' ' in mega_aside_border else '')}
    padding-left: {max(mega_aside_pad, 16)}px;
    display: flex;
    flex-direction: column;
    gap: 1.4rem;
  }}
  .mega-aside .mega-col ul {{ display: flex; flex-direction: column; gap: 0.15rem; }}
  .mega-featured {{ flex: 0 0 auto; min-width: 180px; }}
  .mega-col-head {{
    display: block;
    font-size: {mega_head_fs}px;
    font-weight: {mega_head_fw};
    color: {mega_head_color};
    text-transform: {mega_head_tt};
    letter-spacing: {mega_head_ls};
    margin: 0 0 0.7rem;
  }}
  .mega-panel ul {{ list-style: none; margin: 0; padding: 0; }}
  .mega-panel li {{ margin: 0; }}
  /* menu-card link anatomy: icon + title + (hover-revealed) description */
  .mega-link {{
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: {mega_link_pad};
    border-radius: {mega_link_radius}px;
    transition: background-color 0.15s ease;
  }}
  {(f'.mega-link:hover {{ background: {mega_link_hover_bg}; }}' if mega_link_hover_bg else '.mega-link:hover { background: rgba(0,0,0,0.04); }')}
  .mega-link-icon {{ flex: 0 0 auto; display: inline-flex; margin-top: 1px; }}
  .mega-link-icon img {{ width: 20px; height: 20px; display: block; }}
  .mega-link-text {{ display: block; min-width: 0; }}
  .mega-link-title {{
    display: block;
    font-size: {mega_link_fs}px;
    font-weight: 500;
    color: {mega_link_color};
    line-height: 1.35;
  }}
  .mega-link-desc {{
    display: grid;
    grid-template-rows: 1fr;
    transition: grid-template-rows {mega_desc_dur} {mega_ease};
  }}
  .mega-link-desc > span {{
    overflow: hidden;
    font-size: {max(mega_link_fs - 2, 12)}px;
    color: rgba(31,31,31,0.62);
    line-height: 1.4;
  }}
  .mega-link.desc-hover .mega-link-desc {{ grid-template-rows: 0fr; }}
  .mega-link.desc-hover:hover .mega-link-desc,
  .mega-link.desc-hover:focus-visible .mega-link-desc {{ grid-template-rows: 1fr; }}
  /* the panel's right-side PROMO/FEATURE card (captured object) */
  .mega-aside-card {{ min-width: 0; }}
  .mega-card {{
    display: block;
    background: #fff;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  }}
  .mega-card-img {{ display: block; width: 100%; height: auto; }}
  .mega-card-title {{
    margin: 0;
    padding: 12px 14px 4px;
    font-size: {mega_link_fs}px;
    font-weight: 500;
    line-height: 1.35;
    color: {mega_link_color};
  }}
  .mega-card-body {{
    margin: 0;
    padding: 0 14px;
    font-size: {max(mega_link_fs - 2, 12)}px;
    color: rgba(31,31,31,0.62);
  }}
  .mega-card-cta {{
    display: block;
    padding: 8px 14px 14px;
    font-size: {max(mega_link_fs - 2, 12)}px;
    font-weight: 500;
    color: var(--nav-link-hover);
  }}

  /* ---- spacer band so the frame shows page surface between chrome ---- */
  .spacer {{
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 26cqh;
    color: rgba(0,0,0,0.28);
    font-family: var(--font-display);
    font-size: 1.5rem;
    letter-spacing: 0.04em;
  }}

  /* ---- FOOTER (measured proportions) ---- */
  footer.footer {{
    background: var(--footer-bg);
    color: var(--text-inverted);
    padding-block: {foot_pad_top}px {foot_pad_bottom}px;
  }}
  footer.footer .inner {{ width: min({foot_content_max}px, 92cqi); }}
  .footer-cols {{
    display: grid;
    grid-template-columns: {grid_template};
    gap: {foot_col_gap}px;
    align-items: start;
  }}
  .footer-cell-stack {{ display: flex; flex-direction: column; gap: 4cqh; }}
  /* the link-heavy first column flows into two sub-columns */
  .cell-wide .footer-col ul {{ columns: 2; column-gap: {foot_col_gap}px; }}
  .footer-col .col-head {{
    font-family: {foot_head_ff};
    font-size: {foot_head_fs}px;
    font-weight: {foot_head_fw};
    margin: 0 0 1.4cqh;
    color: var(--text-inverted);
  }}
  .footer-col ul {{ list-style: none; margin: 0; padding: 0; }}
  .footer-col li {{ margin-bottom: 0.6cqh; break-inside: avoid; }}
  .footer-col a {{ font-size: {foot_link_fs}px; font-weight: {foot_link_fw}; line-height: {foot_link_lh}px; color: var(--footer-link); }}
  .footer-col a:hover {{ color: var(--text-inverted); }}

  /* ---- bottom block (alignment driven by measured textAlign) ---- */
  .footer-bottom {{
    margin-top: 6cqh;
    padding-top: 4cqh;
    border-top: 1px solid var(--footer-border);
    display: flex;
    flex-direction: {bottom_dir};
    align-items: {bottom_flex_align};
    justify-content: space-between;
    gap: 3cqh;
    text-align: {bottom_text_align};
    flex-wrap: wrap;
  }}
  .footer-bottom-brand {{ display: flex; flex-direction: column; gap: 2cqh; align-items: {bottom_flex_align}; }}
  .social-row {{ display: flex; align-items: center; gap: 2cqi; flex-wrap: wrap; }}
  .social {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--footer-link);
  }}
  .social svg {{ width: {foot_social_size}px; height: {foot_social_size}px; fill: currentColor; }}
  .social:hover {{ color: var(--text-inverted); }}
  /* HARVESTED social glyphs render via the source's own CSS-mask mechanic:
     the captured SVG masks a span painted with the measured ink color. Box
     size/radius/fill are the measured link box. */
  {(f'.social {{ width: {soc_box_w}px; height: {soc_box_h}px; border-radius: {soc_box_r}px;'
    + (f' background: {soc_box_bg};' if soc_box_bg and 'rgba(0, 0, 0, 0)' not in soc_box_bg else '')
    + ' }' if soc_box_w else '')}
  .social-glyph {{
    display: inline-block;
    background-color: {soc_ink or 'currentColor'};
    -webkit-mask: var(--glyph) no-repeat 50% / contain;
    mask: var(--glyph) no-repeat 50% / contain;
  }}

  /* ---- MEASURED bottom bar (fid4 2026-07): divider + row composition ---- */
  .footer-bottom-bar {{
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: {bb_gap}px;
    border-top: 0;
    text-align: left;
  }}
  .fb-row {{ display: flex; flex-wrap: wrap; }}
  .fb-row1 {{
    justify-content: space-between;
    align-items: {bb_row1_align};
    gap: {bb_row1_gap}px;
  }}
  .fb-copy {{ max-width: 72ch; }}
  .fb-copy .copyright {{ display: block; }}
  .fb-disclaimer {{
    margin: 8px 0 0;
    font-size: {foot_legal_fs}px;
    font-weight: {foot_legal_fw};
    line-height: 1.5;
    color: var(--footer-link);
  }}
  .fb-badges {{ display: flex; align-items: center; gap: 12px; flex: 0 0 auto; }}
  .fb-badges img {{ display: block; height: 40px; width: auto; }}
  .fb-divider {{
    height: 1px;
    background: {bb_div_color};
    opacity: {bb_div_opacity};
  }}
  .fb-row2 {{
    justify-content: {bb_row2_justify};
    align-items: center;
    gap: {bb_row2_gap}px;
  }}
  .fb-policy {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2em;
    font-size: {foot_legal_fs}px;
    font-weight: {foot_legal_fw};
  }}
  .fb-policy a {{ color: var(--footer-link); }}
  .fb-policy a:hover {{ color: var(--text-inverted); }}
  .footer-brand {{ color: var(--text-inverted); }}
  .footer-brand img, .footer-brand svg {{ height: {foot_logo_h}px; width: auto; max-width: {foot_logo_w}px; display: block; }}
  .footer-legal {{
    display: flex;
    align-items: center;
    justify-content: {bottom_flex_align};
    gap: 1.6cqi;
    flex-wrap: wrap;
    font-size: {foot_legal_fs}px;
    font-weight: {foot_legal_fw};
    color: var(--footer-link);
  }}
  .footer-legal a {{ color: var(--footer-link); }}
  .footer-legal a:hover {{ color: var(--text-inverted); }}

  /* ---- TEXT social links (only when the SOURCE used text, not icon glyphs) ---- */
  .social-text {{
    font-size: {foot_social_fs}px;
    font-weight: {foot_social_transform == 'uppercase' and '400' or '500'};
    text-transform: {foot_social_transform};
    letter-spacing: {foot_social_ls};
    color: var(--footer-link);
    white-space: nowrap;
  }}
  .social-sep {{ color: var(--footer-link); opacity: 0.5; }}

  /* ---- CENTERED flat footer (no column headings — flat-sitemap brands) ---- */
  footer.footer-centered .inner {{
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 5cqh;
  }}
  footer.footer-centered .footer-sitemap {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: baseline;
    gap: 0.2em 0.5em;
    max-width: 100%;
  }}
  footer.footer-centered .sitemap-link {{
    font-family: var(--font-display);
    font-size: {foot_link_fs}px;
    line-height: 1.05;
    font-weight: {foot_link_fw};
    color: var(--text-inverted);
    text-transform: uppercase;
    white-space: nowrap;
  }}
  footer.footer-centered .sitemap-link:hover {{ color: var(--footer-link-hover); }}
  footer.footer-centered .sitemap-sep {{
    font-family: var(--font-display);
    font-size: {foot_link_fs}px;
    line-height: 1.05;
    color: var(--text-inverted);
    opacity: 0.55;
  }}
  footer.footer-centered .footer-social-row {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    gap: 0 1.4cqi;
  }}
  footer.footer-centered .footer-rule {{
    width: 100%;
    height: 1px;
    background: var(--footer-border);
  }}
  footer.footer-centered .footer-legal-center {{
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2cqh;
  }}
  footer.footer-centered .footer-legal-links {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 1.6cqi;
  }}
  footer.footer-centered .footer-copy {{
    font-size: {foot_legal_fs}px;
    font-weight: {foot_legal_fw};
    color: var(--footer-link);
    opacity: 0.8;
  }}
  footer.footer-centered .footer-brand img {{ margin: 0 auto; }}
{banner_css}</style>
</head>
<body>
  <!-- EXACT extracted nav/footer — content is 1:1 from the saved {_esc(brand)} homepage
       (source_chrome.v2 offline extraction); proportions from measured computed styles. -->
{banner_html}  <header class="nav">
{utility_block}  <div class="nav-primary"><div class="inner nav-inner">
      <a class="nav-logo" href="{_esc(logo_href)}" aria-label="{_esc(logo_alt)}">
        {logo_inner}
      </a>
      <nav class="nav-links">
{primary_html}
      </nav>
      <div class="nav-actions">
{bar_util_html}
{cta_html}
      </div>
  </div></div>
  </header>

  <div class="wrap">
    <div class="inner spacer">{_esc(brand)} — extracted site chrome preview</div>
  </div>

{footer_html}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Bridge chrome contract → brand.yaml + preview")
    parser.add_argument("--brand", required=True)
    parser.add_argument("--contract", default=None, help="source-chrome.v2.json (default runs/<brand>/assets/...)")
    parser.add_argument("--brand-yaml", default=None, help="brand.yaml (default runs/<brand>/brand/brand.yaml)")
    parser.add_argument("--out-html", default=None, help="preview path (default runs/<brand>/brand/chrome/index.html)")
    args = parser.parse_args()

    brand = args.brand
    contract_path = Path(args.contract) if args.contract else PROJECT_DIR / "runs" / brand / "assets" / "source-chrome.v2.json"
    brand_yaml = Path(args.brand_yaml) if args.brand_yaml else PROJECT_DIR / "runs" / brand / "brand" / "brand.yaml"
    out_html = Path(args.out_html) if args.out_html else PROJECT_DIR / "runs" / brand / "brand" / "chrome" / "index.html"

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    doc = yaml.safe_load(brand_yaml.read_text(encoding="utf-8")) or {}

    # materialize harvested chrome artwork (menu icons, promo card image, store
    # badges, social glyphs) into the brand's assets/ + stamp asset refs
    stamped = _materialize_chrome_assets(contract, brand_yaml.parent / "assets")
    if stamped:
        print(f"[bridge] chrome assets materialized: {len(stamped)} "
              f"({', '.join(sorted(set(r.rsplit('/', 1)[-1] for r in stamped))[:6])}"
              f"{' …' if len(set(stamped)) > 6 else ''})")

    navbar = _merge_navbar(doc.get("navbar"), contract.get("nav") or {})
    footer = _merge_footer(doc.get("footer"), contract.get("footer") or {})

    _write_brand_yaml_atomic(brand_yaml, navbar, footer)
    print(f"[bridge] brand.yaml updated atomically: {brand_yaml}")
    print(f"  nav: utility={len(navbar['utility'])} primary={len(navbar['primary'])} ctas={len(navbar['ctas'])}")
    print(f"  footer: columns={len(footer['columns'])} social={len(footer['social'])} legal={len(footer['legal']['links'])}")

    # render with the MERGED chrome visible so agent-verified measures
    # (contentMaxWidth etc.) can backfill gaps the extractor could not measure
    doc["navbar"], doc["footer"] = navbar, footer
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render_chrome_index_html(brand, contract, doc), encoding="utf-8")
    print(f"[bridge] preview regenerated: {out_html}")


if __name__ == "__main__":
    main()
