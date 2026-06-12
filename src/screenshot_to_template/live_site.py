"""Helpers for working with live-site HTML snapshots and DOM-only grounding."""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag


CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/135.0.0.0 Safari/537.36"
)
SECTION_KEYWORDS = (
    "hero",
    "section",
    "feature",
    "product",
    "pricing",
    "faq",
    "footer",
    "header",
    "nav",
    "testimonial",
    "case",
    "customer",
    "logo",
    "cta",
    "intro",
    "platform",
    "solutions",
)
INLINE_STYLE_MARKER = "/* === External:"


def derive_live_url_from_stem(stem: str) -> str:
    """Convert a filename stem like 'highnote-com' into a live-site URL."""
    parts = stem.split("-")
    if len(parts) < 2:
        raise ValueError(f"Cannot derive URL from stem: {stem!r}")
    host = "-".join(parts[:-1]) + "." + parts[-1]
    return f"https://{host}"


def dump_rendered_dom(url: str, virtual_time_budget_ms: int = 12000) -> str:
    """Use headless Chrome to dump the rendered DOM after scripts settle."""
    result = subprocess.run(
        [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            f"--virtual-time-budget={virtual_time_budget_ms}",
            "--dump-dom",
            url,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _stylesheet_hrefs(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    hrefs: list[str] = []
    for link in soup.find_all("link", href=True):
        rel = " ".join(link.get("rel", [])).lower()
        as_attr = (link.get("as") or "").lower()
        if "stylesheet" in rel or as_attr == "style":
            hrefs.append(link["href"])
    return hrefs


def inline_linked_stylesheets(html: str, url: str, timeout_s: int = 30) -> str:
    """Append external CSS into a single <style> block for downstream parsing."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    seen: set[str] = set()
    styles: list[str] = []
    for href in _stylesheet_hrefs(html):
        full_url = urljoin(url, href)
        if full_url in seen:
            continue
        seen.add(full_url)
        try:
            resp = session.get(full_url, timeout=timeout_s)
            resp.raise_for_status()
            styles.append(f"{INLINE_STYLE_MARKER} {full_url} === */\n{resp.text}")
        except Exception as exc:  # pragma: no cover - network failures are input-specific
            styles.append(f"/* === Failed to fetch stylesheet: {full_url} ({exc}) === */")

    if not styles:
        return html

    style_block = "\n<style>\n" + "\n\n".join(styles) + "\n</style>\n"
    if "</head>" in html:
        return html.replace("</head>", style_block + "</head>", 1)
    return style_block + html


def snapshot_live_site_html(
    url: str,
    output_path: Path,
    fetched_label: str | None = None,
    virtual_time_budget_ms: int = 12000,
) -> Path:
    """Dump rendered DOM, inline stylesheets, and save a standalone HTML snapshot."""
    rendered_html = dump_rendered_dom(url, virtual_time_budget_ms=virtual_time_budget_ms)
    inlined_html = inline_linked_stylesheets(rendered_html, url)
    fetched = fetched_label or datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    decorated = f"<!-- Source: {url} -->\n<!-- Fetched: {fetched} -->\n{inlined_html}"
    output_path.write_text(decorated)
    return output_path


def ensure_live_site_html_snapshot(screenshot_path: Path) -> tuple[str, Path]:
    """Create a sibling HTML snapshot for a screenshot when missing."""
    url = derive_live_url_from_stem(screenshot_path.stem)
    html_path = screenshot_path.with_suffix(".html")
    if not html_path.exists():
        snapshot_live_site_html(url, html_path)
    return url, html_path


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _descriptor_for_tag(tag: Tag) -> str:
    tag_id = tag.get("id")
    classes = [cls for cls in tag.get("class", []) if cls]
    attrs: list[str] = [tag.name]
    if tag_id:
        attrs.append(f"#{tag_id}")
    if classes:
        attrs.extend(f".{cls}" for cls in classes[:4])
    return "".join(attrs)


def _section_keyword_score(tag: Tag) -> int:
    haystack = " ".join(
        [
            tag.name,
            tag.get("id", ""),
            " ".join(tag.get("class", [])),
            tag.get("aria-label", ""),
            tag.get("role", ""),
        ]
    ).lower()
    return sum(keyword in haystack for keyword in SECTION_KEYWORDS)


def _visible_texts(tag: Tag, selector: str, limit: int = 8, max_len: int = 120) -> list[str]:
    items: list[str] = []
    for node in tag.select(selector):
        text = _clean_text(node.get_text(" ", strip=True))
        if not text:
            continue
        if len(text) > max_len:
            text = text[: max_len - 1].rstrip() + "…"
        if text not in items:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def _primary_text_snippet(tag: Tag, max_len: int = 300) -> str:
    block_texts = _visible_texts(tag, "p, li", limit=10, max_len=200)
    joined = " | ".join(block_texts)
    if len(joined) > max_len:
        return joined[: max_len - 1].rstrip() + "…"
    return joined


def _summarize_candidate(tag: Tag) -> dict:
    descendant_tags = [node.name for node in tag.find_all(True)]
    counts = Counter(descendant_tags)
    return {
        "descriptor": _descriptor_for_tag(tag),
        "keyword_score": _section_keyword_score(tag),
        "headings": _visible_texts(tag, "h1, h2, h3, h4", limit=6, max_len=120),
        "buttons": _visible_texts(tag, "button, a", limit=10, max_len=80),
        "body_text": _primary_text_snippet(tag),
        "images": counts["img"],
        "videos": counts["video"],
        "lists": counts["ul"] + counts["ol"],
        "cards": counts["article"],
    }


def _candidate_tags(soup: BeautifulSoup) -> list[Tag]:
    body = soup.body
    if body is None:
        return []

    main = body.find("main")
    root = main if main is not None else body

    candidates: list[Tag] = []
    semantic_names = {"header", "nav", "section", "article", "aside", "footer"}
    for tag in body.find_all(True):
        if tag.name in semantic_names:
            candidates.append(tag)
            continue
        if tag.name == "div" and _section_keyword_score(tag) > 0:
            candidates.append(tag)

    if not candidates:
        candidates.extend([child for child in root.find_all(recursive=False) if isinstance(child, Tag)])

    deduped: list[Tag] = []
    seen: set[int] = set()
    for tag in candidates:
        if id(tag) in seen:
            continue
        if len(_clean_text(tag.get_text(" ", strip=True))) < 24 and not tag.find(["img", "video", "svg"]):
            continue
        seen.add(id(tag))
        deduped.append(tag)
    return deduped


def build_dom_outline(html_text: str, url: str) -> str:
    """Create a compact markdown outline of the rendered live DOM."""
    soup = BeautifulSoup(html_text, "html.parser")
    for doomed in soup(["script", "style", "noscript", "template"]):
        doomed.decompose()

    title = _clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = _clean_text(meta_desc_tag.get("content", "")) if meta_desc_tag else ""

    nav_links: list[str] = []
    for nav in soup.find_all(["nav", "header"], limit=2):
        nav_links.extend(_visible_texts(nav, "a, button", limit=12, max_len=60))
    nav_links = list(dict.fromkeys(nav_links))[:14]

    footer_links: list[str] = []
    footer = soup.find("footer")
    if footer is not None:
        footer_links = _visible_texts(footer, "a, button", limit=16, max_len=60)

    headings = []
    for heading in soup.find_all(["h1", "h2", "h3"], limit=40):
        text = _clean_text(heading.get_text(" ", strip=True))
        if not text:
            continue
        ancestor = heading.find_parent(["section", "article", "aside", "header", "footer", "nav", "div"])
        descriptor = _descriptor_for_tag(ancestor) if ancestor is not None else heading.name
        headings.append(f"- `{heading.name}` in `{descriptor}`: {text}")

    candidates = sorted(
        (_summarize_candidate(tag) for tag in _candidate_tags(soup)),
        key=lambda item: (-item["keyword_score"], item["descriptor"]),
    )

    lines = [
        "# Live DOM Outline",
        "",
        f"- URL: `{url}`",
        f"- Title: {title or 'N/A'}",
        f"- Meta description: {meta_desc or 'N/A'}",
        "",
        "## Primary Navigation Labels",
        "",
    ]

    if nav_links:
        lines.extend(f"- {text}" for text in nav_links)
    else:
        lines.append("- None found")

    lines.extend(["", "## Heading Outline", ""])
    if headings:
        lines.extend(headings)
    else:
        lines.append("- None found")

    lines.extend(["", "## Candidate Sections", ""])
    if candidates:
        for index, candidate in enumerate(candidates[:24], start=1):
            lines.append(f"### Candidate {index}: `{candidate['descriptor']}`")
            lines.append(f"- Heading texts: {', '.join(candidate['headings']) if candidate['headings'] else 'None'}")
            lines.append(f"- CTA/button texts: {', '.join(candidate['buttons']) if candidate['buttons'] else 'None'}")
            lines.append(f"- Body text snippet: {candidate['body_text'] or 'None'}")
            lines.append(
                "- Media counts: "
                f"{candidate['images']} images, {candidate['videos']} videos, "
                f"{candidate['lists']} lists, {candidate['cards']} article/card elements"
            )
            lines.append("")
    else:
        lines.append("- None found")

    lines.extend(["## Footer Labels", ""])
    if footer_links:
        lines.extend(f"- {text}" for text in footer_links)
    else:
        lines.append("- None found")

    return "\n".join(lines).rstrip() + "\n"
