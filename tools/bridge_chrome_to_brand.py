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

Usage:
    ./venv/bin/python tools/bridge_chrome_to_brand.py --brand hubspot
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
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
def _strip_nav_link(link: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"label": link.get("label") or ""}
    out["href"] = link.get("href") or ""
    menu = link.get("menu") if isinstance(link.get("menu"), dict) else None
    if menu:
        out["menu"] = {
            "columns": [
                {
                    "heading": col.get("heading") or "",
                    "links": [
                        {"label": l.get("label") or "", "href": l.get("href") or ""}
                        for l in (col.get("links") or [])
                    ],
                }
                for col in (menu.get("columns") or [])
            ],
            "featured": [
                {"label": f.get("label") or "", "href": f.get("href") or ""}
                for f in (menu.get("featured") or [])
            ],
        }
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
        out["logo"] = {
            "kind": lg.get("kind") or "img",
            "alt": lg.get("alt") or "",
            "href": lg.get("href") or "/",
            "width": lg.get("width") or 0,
            "height": lg.get("height") or 0,
            "srcContract": "../assets/source-chrome.v2.json#nav.logo.src",
        }
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
        out["measured"] = nav["measured"]
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
        out["logo"] = {
            "kind": lg.get("kind") or "img",
            "alt": lg.get("alt") or "",
            "href": lg.get("href") or "/",
            "width": lg.get("width") or 0,
            "height": lg.get("height") or 0,
            "srcContract": "../assets/source-chrome.v2.json#footer.logo.src",
        }
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
    out["social"] = [
        {
            "network": s.get("network") or "link",
            "kind": (s.get("kind") or "").lower() or "icon",
            "href": s.get("href") or "",
        }
        for s in (footer.get("social") or [])
    ]
    legal = footer.get("legal") or {}
    out["legal"] = {
        "text": legal.get("text") or "",
        "links": [
            {"label": l.get("label") or "", "href": l.get("href") or ""}
            for l in (legal.get("links") or [])
        ],
    }
    nl = footer.get("newsletter")
    out["newsletter"] = nl if isinstance(nl, dict) else {"present": False}
    if isinstance(footer.get("measured"), dict):
        out["measured"] = footer["measured"]
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


def _social_item_html(s: dict[str, Any], style_default: str) -> str:
    """Render ONE social link honoring its real source representation.

    icon → monochrome glyph (only when the source link used an icon); text →
    the real visible label. Per-item `kind` wins; falls back to the footer-level
    style. NEVER injects an icon the page didn't show.
    """
    kind = (s.get("kind") or style_default or "icon").lower()
    href = _esc(s.get("href") or "#")
    net = s.get("network") or "link"
    if kind == "text":
        label = _esc((s.get("label") or net or "").strip())
        return f'<a class="social social-text" href="{href}">{label}</a>'
    return (
        f'<a class="social" href="{href}" aria-label="{_esc(net)}">'
        f"{_social_svg(net)}</a>"
    )


def _social_row_html(social: list[dict[str, Any]], style: str, *, indent: str) -> str:
    """Join social links; text style uses visible slash separators between labels."""
    items = [_social_item_html(s, style) for s in social]
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


def _mega_panel_html(menu: dict[str, Any]) -> str:
    """Render a primary tab's captured mega-menu (columns + featured)."""
    columns = menu.get("columns") or []
    featured = menu.get("featured") or []
    col_parts = []
    for col in columns:
        heading = _esc(col.get("heading"))
        head_html = f'<h4 class="mega-col-head">{heading}</h4>' if heading else ""
        items = "\n".join(
            f'            <li><a href="{_esc(l.get("href") or "#")}">{_esc(l.get("label"))}</a></li>'
            for l in (col.get("links") or [])
        )
        col_parts.append(
            '          <div class="mega-col">'
            + head_html
            + ("\n            <ul>\n" + items + "\n            </ul>" if items else "")
            + "</div>"
        )
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
    return (
        '\n        <div class="mega-panel"><div class="mega-inner">\n'
        '          <div class="mega-cols">\n'
        + "\n".join(col_parts)
        + "\n          </div>"
        + feat_html
        + "\n        </div></div>"
    )


def _primary_nav_html(primary: list[dict[str, Any]]) -> str:
    """Primary tabs; tabs that own a captured mega-menu expand on hover/focus."""
    out = []
    for ln in primary:
        label = _esc(ln.get("label"))
        href = ln.get("href") or "#"
        menu = ln.get("menu") if isinstance(ln.get("menu"), dict) else None
        if menu and (menu.get("columns") or menu.get("featured")):
            out.append(
                '      <div class="nav-tab has-menu">\n'
                f'        <a class="nav-link" href="{_esc(href)}">{label}'
                '<span class="caret" aria-hidden="true">▾</span></a>'
                + _mega_panel_html(menu)
                + "\n      </div>"
            )
        else:
            out.append(f'      <a class="nav-link" href="{_esc(href)}">{label}</a>')
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
    brand: str, contract: dict[str, Any], doc: dict[str, Any]
) -> str:
    nav = contract.get("nav") or {}
    footer = contract.get("footer") or {}
    nm = nav.get("measured") or {}
    fm = footer.get("measured") or {}

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

    nav_bg = _mget(nm, "bar", "bg", default=nav.get("bg")) or "#ffffff"
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
    nav_content_max = _px(nm.get("contentMaxWidth"), 1080)
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
    foot_content_max = _px(fm.get("contentMaxWidth"), 1080)
    foot_pad_top = _px(_mget(fm, "padding", "top"), 48)
    foot_pad_bottom = _px(_mget(fm, "padding", "bottom"), 48)
    foot_head_fs = _px(_mget(fm, "heading", "fontSize"), 18)
    foot_head_fw = _mget(fm, "heading", "fontWeight", default="500")
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

    # nav content
    nav_logo = nav.get("logo") or {}
    logo_src = nav_logo.get("src") or ""
    logo_href = nav_logo.get("href") or "/"
    logo_alt = nav_logo.get("alt") or brand
    utility = nav.get("utility") or []
    primary = nav.get("primary") or (nav.get("links") or [])
    ctas = nav.get("ctas") or []

    util_html = _nav_link_row(utility, "util-link")
    utility_block = (
        '  <div class="nav-utility"><div class="inner nav-utility-inner">\n'
        + util_html
        + "\n  </div></div>\n"
        if utility
        else ""
    )
    primary_html = _primary_nav_html(primary)
    cta_html = "\n".join(
        f'      <a class="nav-cta" href="{_esc(c.get("href") or "#")}">{_esc(c.get("label"))}</a>'
        for c in ctas
    )

    # footer content
    f_logo = footer.get("logo") or {}
    f_logo_src = f_logo.get("src") or ""
    f_logo_href = f_logo.get("href") or "/"
    f_logo_alt = f_logo.get("alt") or brand
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
        # column layout: widen the link-heavy first column, give the next two their
        # own cells, and stack any trailing columns together. (HubSpot.)
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

        col_parts = []
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
        social_html = _social_row_html(social, social_style, indent="        ")

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
          <a class="footer-brand" href="{_esc(f_logo_href)}">
            <img src="{_esc(f_logo_src)}" alt="{_esc(f_logo_alt)}" />
          </a>
        </div>
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
        social_html = _social_row_html(social, social_style, indent="          ")
        logo_html = (
            f'      <a class="footer-brand" href="{_esc(f_logo_href)}">\n'
            f'        <img src="{_esc(f_logo_src)}" alt="{_esc(f_logo_alt)}" />\n'
            f"      </a>\n"
            if f_logo_src
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
  .nav-logo {{ display: inline-flex; align-items: center; }}
  .nav-logo img {{ height: {nav_logo_h}px; width: auto; max-width: {nav_logo_w}px; display: block; }}
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

  /* ---- mega-menu panel: shows on hover/focus of a primary tab ---- */
  .mega-panel {{
    position: absolute;
    left: 0;
    right: 0;
    top: 100%;
    background: var(--nav-bg);
    border-top: 1px solid var(--border-default);
    border-bottom: 1px solid var(--border-default);
    box-shadow: 0 18px 40px rgba(0,0,0,0.10);
    display: none;
    z-index: 20;
  }}
  .nav-tab.has-menu:hover .mega-panel,
  .nav-tab.has-menu:focus-within .mega-panel {{ display: block; }}
  .mega-inner {{
    width: min({nav_content_max}px, 92cqi);
    margin: 0 auto;
    padding: 3cqh 4cqi;
    display: flex;
    gap: 4cqi;
    align-items: flex-start;
  }}
  .mega-cols {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 2cqh 3cqi;
    flex: 1 1 auto;
  }}
  .mega-featured {{ flex: 0 0 auto; min-width: 180px; }}
  .mega-col-head {{
    display: block;
    font-size: {nav_link_fs}px;
    font-weight: 600;
    color: var(--nav-color);
    margin: 0 0 0.8cqh;
  }}
  .mega-panel ul {{ list-style: none; margin: 0; padding: 0; }}
  .mega-panel li {{ margin-bottom: 0.6cqh; }}
  .mega-panel a {{ font-size: {nav_link_fs - 2}px; color: rgba(31,31,31,0.7); }}
  .mega-panel a:hover {{ color: var(--nav-link-hover); }}

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
    font-family: var(--font-display);
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
  .footer-brand img {{ height: {foot_logo_h}px; width: auto; max-width: {foot_logo_w}px; display: block; }}
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
</style>
</head>
<body>
  <!-- EXACT extracted nav/footer — content is 1:1 from the saved {_esc(brand)} homepage
       (source_chrome.v2 offline extraction); proportions from measured computed styles. -->
  <header class="nav">
{utility_block}  <div class="nav-primary"><div class="inner nav-inner">
      <a class="nav-logo" href="{_esc(logo_href)}">
        <img src="{_esc(logo_src)}" alt="{_esc(logo_alt)}" />
      </a>
      <nav class="nav-links">
{primary_html}
      </nav>
      <div class="nav-actions">
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

    navbar = _merge_navbar(doc.get("navbar"), contract.get("nav") or {})
    footer = _merge_footer(doc.get("footer"), contract.get("footer") or {})

    _write_brand_yaml_atomic(brand_yaml, navbar, footer)
    print(f"[bridge] brand.yaml updated atomically: {brand_yaml}")
    print(f"  nav: utility={len(navbar['utility'])} primary={len(navbar['primary'])} ctas={len(navbar['ctas'])}")
    print(f"  footer: columns={len(footer['columns'])} social={len(footer['social'])} legal={len(footer['legal']['links'])}")

    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(render_chrome_index_html(brand, contract, doc), encoding="utf-8")
    print(f"[bridge] preview regenerated: {out_html}")


if __name__ == "__main__":
    main()
