"""Extract navigation and footer structure from a live-page HTML snapshot.

Produces a machine-readable contract (source_chrome.v1) so framework generation
can rebuild nav/footer with the same links, labels, and grouping — styled only
with design-system tokens, not copied inline CSS from the source site.
"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

CHROME_SCHEMA = "source_chrome.v1"


def get_attr(tag: str, name: str) -> str:
    m = re.search(rf"{name}\s*=\s*([\"'])(.*?)\1", tag, re.IGNORECASE | re.DOTALL)
    return unescape(m.group(2).strip()) if m else ""
MAX_BLOCK_CHARS = 80_000
MAX_LINKS_NAV = 24
MAX_LINKS_FOOTER = 80

OPEN_TAG_RE = re.compile(
    r"<(header|nav|footer)\b([^>]*)>",
    re.IGNORECASE,
)
CLOSE_TAG_RE = re.compile(
    r"</(header|nav|footer)\s*>",
    re.IGNORECASE,
)
A_TAG_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
BUTTON_TAG_RE = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.IGNORECASE | re.DOTALL)
IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
SVG_TAG_RE = re.compile(r"<svg\b[^>]*>.*?</svg>", re.IGNORECASE | re.DOTALL)
STRIP_TAGS_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def _to_abs(url: str, base: str) -> str:
    url = (url or "").strip()
    if not url or url.startswith("#") or url.startswith("javascript:"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http"):
        return url
    return urljoin(base.rstrip("/") + "/", url.lstrip("/"))


def _visible_text(html_fragment: str) -> str:
    text = STRIP_TAGS_RE.sub(" ", html_fragment)
    text = unescape(text)
    return WS_RE.sub(" ", text).strip()


def extract_balanced_block(html: str, tag: str, start: int = 0) -> tuple[str, int, int] | None:
    """Return (inner_html, start_pos, end_pos) for the first balanced <tag>…</tag> at/after start."""
    tag_l = tag.lower()
    open_re = re.compile(rf"<{tag_l}\b", re.IGNORECASE)
    close_re = re.compile(rf"</{tag_l}\s*>", re.IGNORECASE)
    m = open_re.search(html, start)
    if not m:
        return None
    depth = 0
    pos = m.start()
    while pos < len(html):
        next_open = open_re.search(html, pos)
        next_close = close_re.search(html, pos)
        if not next_close:
            return None
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
            continue
        depth -= 1
        pos = next_close.end()
        if depth == 0:
            return html[m.start() : pos], m.start(), pos
    return None


def _pick_nav_block(html: str) -> tuple[str, str]:
    """Prefer top <header>, else first <nav> in the document head area."""
    head = html[: min(len(html), 120_000)]
    for tag in ("header", "nav"):
        block = extract_balanced_block(head, tag, 0)
        if block:
            fragment, _, _ = block
            if len(fragment) >= 40:
                return fragment, tag
    return "", ""


def _pick_footer_block(html: str) -> tuple[str, str]:
    """Last <footer> in the document."""
    last: tuple[str, int, int] | None = None
    pos = 0
    while pos < len(html):
        block = extract_balanced_block(html, "footer", pos)
        if not block:
            break
        last = block
        pos = block[2]
    if not last:
        return "", ""
    fragment = last[0]
    if len(fragment) > MAX_BLOCK_CHARS:
        fragment = fragment[:MAX_BLOCK_CHARS]
    return fragment, "footer"


def _parse_links(fragment: str, base_url: str, *, limit: int) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for m in A_TAG_RE.finditer(fragment):
        attrs = m.group(1)
        inner = m.group(2)
        href = get_attr("<a " + attrs + ">", "href")
        label = _visible_text(inner)
        if not label or len(label) > 120:
            continue
        if href and href.startswith("#") and len(label) < 2:
            continue
        key = (label.lower(), (href or "").lower())
        if key in seen:
            continue
        seen.add(key)
        abs_href = _to_abs(href, base_url) if href else ""
        host = urlparse(base_url).netloc
        external = bool(abs_href.startswith("http") and host and host not in urlparse(abs_href).netloc)
        links.append(
            {
                "label": label,
                "href": abs_href or href or "#",
                "external": external,
            }
        )
        if len(links) >= limit:
            break
    return links


def _parse_actions(fragment: str, base_url: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for m in BUTTON_TAG_RE.finditer(fragment):
        attrs = m.group(1)
        inner = m.group(2)
        label = _visible_text(inner)
        if not label:
            continue
        href = get_attr("<button " + attrs + ">", "formaction") or ""
        actions.append(
            {
                "label": label,
                "href": _to_abs(href, base_url) if href else "",
                "kind": "button",
            }
        )
    # CTA-style links (class hints)
    for link in _parse_links(fragment, base_url, limit=12):
        low = link["label"].lower()
        if any(
            w in low
            for w in (
                "sign in",
                "log in",
                "login",
                "get started",
                "start free",
                "try",
                "demo",
                "contact",
                "book",
                "subscribe",
            )
        ) or re.search(r"\b(cta|btn|button)\b", link.get("href", ""), re.I):
            actions.append({**link, "kind": "cta"})
    # Dedupe actions by label
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for a in actions:
        k = a["label"].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(a)
    return out[:6]


def _parse_logo(fragment: str, base_url: str) -> dict[str, Any] | None:
    for m in IMG_TAG_RE.finditer(fragment):
        tag = m.group(0)
        src = get_attr(tag, "src") or get_attr(tag, "data-src")
        if not src:
            continue
        parent_ctx = fragment[max(0, m.start() - 200) : m.start()].lower()
        if "logo" in parent_ctx or "brand" in parent_ctx or m.start() < len(fragment) // 3:
            href = ""
            for am in A_TAG_RE.finditer(fragment[: m.start() + 400]):
                if am.end() >= m.start():
                    href = get_attr("<a " + am.group(1) + ">", "href")
                    break
            return {
                "href": _to_abs(href, base_url) if href else "/",
                "src": _to_abs(src, base_url),
                "alt": get_attr(tag, "alt") or "Logo",
                "asset_role": "navigation/logo",
            }
    for m in SVG_TAG_RE.finditer(fragment):
        block = m.group(0)
        if len(block) > 8000:
            continue
        cls = get_attr(block, "class").lower()
        aria = get_attr(block, "aria-label")
        if "logo" in cls or "brand" in cls or aria.lower() in ("logo", "home"):
            return {
                "href": "/",
                "src": "",
                "alt": aria or "Logo",
                "asset_role": "navigation/logo",
                "inline_svg": block,
            }
    return None


def _infer_nav_layout(fragment: str, link_count: int) -> str:
    low = fragment.lower()
    if "justify-between" in low or "space-between" in low:
        return "split"
    if "justify-center" in low and link_count <= 8:
        return "centered"
    return "split"


def _footer_columns(fragment: str, base_url: str) -> list[dict[str, Any]]:
    """Group footer links into columns using nearest preceding heading text."""
    columns: list[dict[str, Any]] = []
    current_heading = ""
    current_links: list[dict[str, Any]] = []

    parts = re.split(
        r"(<h[1-6]\b[^>]*>.*?</h[1-6]>|<p\b[^>]*class=[^>]*(?:heading|title|label)[^>]*>.*?</p>)",
        fragment,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for part in parts:
        if re.match(r"<h[1-6]\b", part, re.I) or re.search(r"(?:heading|title|label)", part, re.I):
            if current_links:
                columns.append({"heading": current_heading, "links": current_links})
            current_heading = _visible_text(part)
            current_links = []
            continue
        for link in _parse_links(part, base_url, limit=20):
            current_links.append(link)
    if current_links:
        columns.append({"heading": current_heading, "links": current_links})

    if len(columns) >= 2:
        return columns[:8]

    links = _parse_links(fragment, base_url, limit=MAX_LINKS_FOOTER)
    if not links:
        return []
    chunk = max(4, len(links) // 4)
    cols = []
    for i in range(0, len(links), chunk):
        cols.append({"heading": "", "links": links[i : i + chunk]})
    return cols[:6]


def extract_chrome_from_html(html: str, base_url: str, *, source_url: str = "") -> dict[str, Any]:
    nav_fragment, nav_tag = _pick_nav_block(html)
    footer_fragment, footer_tag = _pick_footer_block(html)

    nav_links = _parse_links(nav_fragment, base_url, limit=MAX_LINKS_NAV) if nav_fragment else []
    nav_actions = _parse_actions(nav_fragment, base_url) if nav_fragment else []
    nav_logo = _parse_logo(nav_fragment, base_url) if nav_fragment else None

    # Remove nav-primary links duplicated as CTAs from the link row
    action_labels = {a["label"].lower() for a in nav_actions}
    nav_primary = [ln for ln in nav_links if ln["label"].lower() not in action_labels]

    footer_columns = _footer_columns(footer_fragment, base_url) if footer_fragment else []
    footer_logo = _parse_logo(footer_fragment, base_url) if footer_fragment else None

    return {
        "schema_version": CHROME_SCHEMA,
        "source_url": source_url or base_url,
        "nav": {
            "found": bool(nav_fragment),
            "tag": nav_tag,
            "layout": _infer_nav_layout(nav_fragment, len(nav_primary)),
            "sticky": "sticky" in nav_fragment.lower() or "fixed" in nav_fragment.lower(),
            "logo": nav_logo,
            "links": nav_primary,
            "actions": nav_actions,
        },
        "footer": {
            "found": bool(footer_fragment),
            "tag": footer_tag,
            "logo": footer_logo,
            "columns": footer_columns,
        },
    }


def write_chrome_contract(path: Path, contract: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return path


def load_chrome_contract(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if isinstance(data, dict) and data.get("schema_version") == CHROME_SCHEMA:
        return data
    return None


def summarize_chrome_contract(contract: dict[str, Any] | None) -> str:
    if not contract:
        return ""
    nav = contract.get("nav") if isinstance(contract.get("nav"), dict) else {}
    footer = contract.get("footer") if isinstance(contract.get("footer"), dict) else {}
    lines = [
        "Source chrome contract (1:1 nav/footer — labels, hrefs, grouping; style with tokens only):",
        f"- source: {contract.get('source_url', '')}",
    ]
    if nav.get("found"):
        logo = nav.get("logo") or {}
        actions = nav.get("actions") or nav.get("ctas") or []
        lines.append(f"- nav: {len(nav.get('links') or [])} link(s), {len(actions)} action(s)")
        for cta in actions[:4]:
            lines.append(f"  · CTA: {cta.get('label')} → {cta.get('href') or '(button)'}")
        if logo.get("alt"):
            lines.append(f"- nav logo: {logo.get('alt')}")
        for ln in (nav.get("links") or [])[:12]:
            lines.append(f"  · {ln.get('label')} → {ln.get('href')}")
    else:
        lines.append("- nav: not found in HTML snapshot")
    if footer.get("found"):
        cols = footer.get("columns") or []
        lines.append(f"- footer: {len(cols)} column(s)")
        for col in cols[:6]:
            heading = col.get("heading") or "(links)"
            lines.append(f"  · {heading}: {len(col.get('links') or [])} link(s)")
    else:
        lines.append("- footer: not found in HTML snapshot")
    return "\n".join(lines) + "\n"
