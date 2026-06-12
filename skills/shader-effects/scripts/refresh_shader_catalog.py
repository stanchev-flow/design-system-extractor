#!/usr/bin/env python3
"""Refresh a compact Shaders.com docs-derived recipe catalog.

This helper is for maintainers. The site-generation pipeline loads SKILL.md,
so keep the important picker guidance summarized there after refreshing.
"""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE = "https://shaders.com"
DOC_PATHS = [
    "/docs/guide",
    "/docs/guide/composing-effects",
    "/docs/guide/blending-masking",
    "/docs/guide/dynamic-props",
    "/docs/components/aurora",
    "/docs/components/wavedistortion",
]


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "screenshot-to-template-shader-catalog/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def payload_url(path: str) -> str | None:
    page_url = urllib.parse.urljoin(BASE, path)
    match = re.search(r'href="([^"]*_payload\.json\?[^"]+)"', fetch(page_url))
    if not match:
        return None
    return urllib.parse.urljoin(page_url, html.unescape(match.group(1)))


def walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk_strings(item)


def component_types(components: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []

    def visit(component: dict[str, Any]) -> None:
        name = component.get("type")
        if isinstance(name, str) and name not in found:
            found.append(name)
        for child in component.get("children", []) or []:
            if isinstance(child, dict):
                visit(child)

    for component in components:
        visit(component)
    return found


def main() -> int:
    recipes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in DOC_PATHS:
        url = payload_url(path)
        if not url:
            continue
        payload = json.loads(fetch(url))
        for text in walk_strings(payload):
            if not text.startswith('{"components"'):
                continue
            config = json.loads(text)
            components = config.get("components")
            if not isinstance(components, list):
                continue
            key = json.dumps(components, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            recipes.append({
                "source": urllib.parse.urljoin(BASE, path),
                "components": component_types(components),
                "config": {"components": components},
            })

    output = Path(__file__).resolve().parents[1] / "shader-catalog.raw.json"
    output.write_text(json.dumps(recipes, indent=2) + "\n")
    print(f"wrote {len(recipes)} recipes to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
