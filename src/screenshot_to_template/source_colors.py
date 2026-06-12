"""Extract source-of-truth style data from the archived HTML/CSS files."""

from __future__ import annotations

import json
import math
import re
from html import unescape
from colorsys import hls_to_rgb
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.IGNORECASE | re.DOTALL)
SCRIPT_BLOCK_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.IGNORECASE | re.DOTALL)
STYLE_ATTR_RE = re.compile(r"\sstyle\s*=\s*(['\"])(.*?)\1", re.IGNORECASE | re.DOTALL)
EXTERNAL_STYLE_MARKER_RE = re.compile(r"/\*\s*===\s*External:\s*([^=]+?)\s*===\s*\*/")
CUSTOM_PROPERTY_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+);")
DECLARATION_RE = re.compile(r"([A-Za-z-]+)\s*:\s*([^;{}]+);")
VAR_REF_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,\s*([^)]+))?\)")
HEX_RE = re.compile(r"(?<!&)#[0-9A-Fa-f]{3,8}\b")
RGB_RE = re.compile(r"rgba?\([^)]+\)")
HSL_RE = re.compile(r"hsla?\([^)]+\)")
GRADIENT_RE = re.compile(r"(linear|radial|conic)-gradient\((?:[^)(]+|\([^)(]*\))*\)", re.IGNORECASE)
FONT_FACE_RE = re.compile(r"@font-face\s*{(?P<body>[^{}]*)}", re.IGNORECASE | re.DOTALL)
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(?P<url>[^'\"\)]+)\1\s*\)", re.IGNORECASE)
FONT_FAMILY_DECL_RE = re.compile(r"font-family\s*:\s*([^;}{]+);", re.IGNORECASE)
WEBFONT_GOOGLE_FAMILIES_RE = re.compile(
    r"WebFont\.load\s*\(\s*\{.*?google\s*:\s*\{.*?families\s*:\s*\[(?P<families>.*?)\]",
    re.IGNORECASE | re.DOTALL,
)
JS_STRING_RE = re.compile(r"(['\"])(?P<value>(?:\\.|(?!\1).)*?)\1", re.DOTALL)
FONT_VALUE_SKIP = {"inherit", "initial", "unset", "revert"}
TYPOGRAPHY_PROPERTIES = (
    "font",
    "font-family",
    "font-size",
    "font-weight",
    "line-height",
    "letter-spacing",
)
FONT_ASSET_EXTENSIONS = {
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".eot": "application/vnd.ms-fontobject",
}


def find_source_html_for_screenshot(screenshot_path: str | Path) -> Path | None:
    """Return source HTML for a screenshot: sibling .html or Studio harvest path."""
    screenshot_path = Path(screenshot_path)
    candidate = screenshot_path.with_suffix(".html")
    if candidate.exists():
        return candidate
    # screenshots/{version}/{name}.png → runs/{version}/assets/source.html
    if screenshot_path.parent.name and screenshot_path.parent.parent.name == "screenshots":
        harvested = (
            screenshot_path.parent.parent.parent
            / "runs"
            / screenshot_path.parent.name
            / "assets"
            / "source.html"
        )
        if harvested.exists():
            return harvested
    return None


def _expand_short_hex(value: str) -> str:
    body = value[1:]
    if len(body) in (3, 4):
        body = "".join(ch * 2 for ch in body)
    return f"#{body.upper()}"


def normalize_color_literal(value: str) -> str:
    """Normalize a CSS color literal for stable reporting."""
    value = value.strip()
    lowered = value.lower()
    if lowered == "transparent":
        return "transparent"
    if HEX_RE.fullmatch(value):
        return _expand_short_hex(value)
    if RGB_RE.fullmatch(value):
        return re.sub(r"\s+", "", value.lower())
    if HSL_RE.fullmatch(value):
        return re.sub(r"\s+", "", value.lower())
    return value


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _parse_alpha_token(token: str | None) -> float:
    if token is None:
        return 1.0
    raw = token.strip()
    percent = raw.endswith("%")
    token = raw.rstrip("%").strip()
    if not token:
        return 1.0
    range_match = re.fullmatch(r"(\d*\.?\d+)\s*-\s*(\d*\.?\d+)", token)
    if range_match:
        value = (float(range_match.group(1)) + float(range_match.group(2))) / 2.0
    else:
        try:
            value = float(token)
        except ValueError:
            return 1.0
    if percent:
        value /= 100.0
    return _clamp01(value)


def _parse_rgb_channel(token: str) -> float:
    token = token.strip()
    if token.endswith("%"):
        return _clamp01(float(token[:-1]) / 100.0)
    return _clamp01(float(token) / 255.0)


def _parse_hsl_hue(token: str) -> float:
    token = token.strip().lower()
    if token.endswith("deg"):
        token = token[:-3]
    elif token.endswith("turn"):
        return (float(token[:-4]) * 360.0) % 360.0
    elif token.endswith("rad"):
        return math.degrees(float(token[:-3])) % 360.0
    return float(token) % 360.0


def _parse_percentage_channel(token: str) -> float:
    token = token.strip()
    if not token.endswith("%"):
        return _clamp01(float(token))
    return _clamp01(float(token[:-1]) / 100.0)


def _parse_css_color_literal(value: str) -> tuple[float, float, float, float] | None:
    value = normalize_color_literal(value)
    lowered = value.lower()
    if lowered == "transparent":
        return (0.0, 0.0, 0.0, 0.0)

    if HEX_RE.fullmatch(value):
        body = value[1:]
        if len(body) == 6:
            r = int(body[0:2], 16) / 255.0
            g = int(body[2:4], 16) / 255.0
            b = int(body[4:6], 16) / 255.0
            return (r, g, b, 1.0)
        if len(body) == 8:
            r = int(body[0:2], 16) / 255.0
            g = int(body[2:4], 16) / 255.0
            b = int(body[4:6], 16) / 255.0
            a = int(body[6:8], 16) / 255.0
            return (r, g, b, a)
        return None

    if RGB_RE.fullmatch(value):
        inner = value[value.find("(") + 1 : value.rfind(")")]
        if "/" in inner:
            color_part, alpha_part = inner.split("/", 1)
            alpha = _parse_alpha_token(alpha_part)
        else:
            color_part, alpha = inner, None
        parts = [part.strip() for part in re.split(r",|\s+", color_part.strip()) if part.strip()]
        if len(parts) < 3:
            return None
        r = _parse_rgb_channel(parts[0])
        g = _parse_rgb_channel(parts[1])
        b = _parse_rgb_channel(parts[2])
        a = _parse_alpha_token(parts[3]) if len(parts) > 3 else _parse_alpha_token(alpha)
        return (r, g, b, a)

    if HSL_RE.fullmatch(value):
        inner = value[value.find("(") + 1 : value.rfind(")")]
        if "/" in inner:
            color_part, alpha_part = inner.split("/", 1)
            alpha = _parse_alpha_token(alpha_part)
        else:
            color_part, alpha = inner, None
        parts = [part.strip() for part in re.split(r",|\s+", color_part.strip()) if part.strip()]
        if len(parts) < 3:
            return None
        hue = _parse_hsl_hue(parts[0]) / 360.0
        sat = _parse_percentage_channel(parts[1])
        light = _parse_percentage_channel(parts[2])
        r, g, b = hls_to_rgb(hue, light, sat)
        a = _parse_alpha_token(parts[3]) if len(parts) > 3 else _parse_alpha_token(alpha)
        return (r, g, b, a)

    return None


def _srgb_to_linear(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def _rgba_to_lab(color: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    r, g, b, a = color
    r_lin = _srgb_to_linear(r)
    g_lin = _srgb_to_linear(g)
    b_lin = _srgb_to_linear(b)

    x = r_lin * 0.4124564 + g_lin * 0.3575761 + b_lin * 0.1804375
    y = r_lin * 0.2126729 + g_lin * 0.7151522 + b_lin * 0.0721750
    z = r_lin * 0.0193339 + g_lin * 0.1191920 + b_lin * 0.9503041

    xr = x / 0.95047
    yr = y / 1.00000
    zr = z / 1.08883

    def f(t: float) -> float:
        if t > 216 / 24389:
            return t ** (1 / 3)
        return (24389 / 27 * t + 16) / 116

    fx, fy, fz = f(xr), f(yr), f(zr)
    l = 116 * fy - 16
    a_star = 500 * (fx - fy)
    b_star = 200 * (fy - fz)
    return (l, a_star, b_star, a)


def _lab_distance(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> float:
    dl = left[0] - right[0]
    da = left[1] - right[1]
    db = left[2] - right[2]
    dalpha = (left[3] - right[3]) * 100.0
    return math.sqrt(dl * dl + da * da + db * db + dalpha * dalpha)


def build_source_color_frequency_map(extracted: dict) -> dict[str, int]:
    """Return normalized source color literal frequencies for tie-breaking."""
    counts: dict[str, int] = {}

    for entry in extracted.get("frequent_color_literals", []):
        value = entry.get("value")
        if not isinstance(value, str):
            continue
        normalized = normalize_color_literal(value)
        counts[normalized] = counts.get(normalized, 0) + int(entry.get("count") or 0)

    for collection_name in ("resolved_custom_properties", "gradient_custom_properties"):
        for value in extracted.get(collection_name, {}).values():
            if not isinstance(value, str):
                continue
            for literal in extract_document_color_literals(value):
                counts[literal] = counts.get(literal, 0) + 1

    return counts


def suggest_nearest_source_color_replacements(text: str, extracted: dict) -> dict[str, str]:
    """Map unsupported explicit colors in a document to nearest source-backed colors."""
    unsupported = find_non_source_document_colors(text, extracted)
    if not unsupported:
        return {}

    frequency_map = build_source_color_frequency_map(extracted)
    candidate_literals = []
    seen: set[str] = set()
    for literal in collect_allowed_source_color_literals(extracted):
        normalized = normalize_color_literal(literal)
        if normalized in seen:
            continue
        parsed = _parse_css_color_literal(normalized)
        if parsed is None:
            continue
        seen.add(normalized)
        candidate_literals.append(
            {
                "literal": normalized,
                "lab": _rgba_to_lab(parsed),
                "frequency": frequency_map.get(normalized, 0),
            }
        )

    replacements: dict[str, str] = {}
    for literal in unsupported:
        parsed = _parse_css_color_literal(literal)
        if parsed is None:
            continue
        source_lab = _rgba_to_lab(parsed)
        best = min(
            candidate_literals,
            key=lambda candidate: (
                round(_lab_distance(source_lab, candidate["lab"]), 6),
                -candidate["frequency"],
                candidate["literal"],
            ),
        )
        replacements[literal] = best["literal"]

    return replacements


def apply_document_color_replacements(text: str, replacements: dict[str, str]) -> str:
    """Replace explicit color literals in a document using a normalized mapping."""
    if not replacements:
        return text

    def replace_match(match: re.Match[str]) -> str:
        literal = normalize_color_literal(match.group(0))
        return replacements.get(literal, match.group(0))

    text = HEX_RE.sub(replace_match, text)
    text = RGB_RE.sub(replace_match, text)
    text = HSL_RE.sub(replace_match, text)
    if "transparent" in replacements:
        text = re.sub(
            r"\btransparent\b",
            lambda match: replacements.get("transparent", match.group(0)),
            text,
            flags=re.IGNORECASE,
        )
    return text


def _is_color_like_value(value: str) -> bool:
    lowered = value.lower()
    return bool(
        HEX_RE.search(value)
        or RGB_RE.search(value)
        or HSL_RE.search(value)
        or GRADIENT_RE.search(value)
        or "transparent" in lowered
    )


def _extract_style_blocks(html: str) -> list[str]:
    return [block.strip() for block in STYLE_BLOCK_RE.findall(html) if block.strip()]


def _extract_script_blocks(html: str) -> list[str]:
    return [block.strip() for block in SCRIPT_BLOCK_RE.findall(html) if block.strip()]


def _extract_inline_style_declarations(html: str) -> list[str]:
    return [unescape(match.group(2)).strip() for match in STYLE_ATTR_RE.finditer(html) if match.group(2).strip()]


def _source_html_base_url(source_html_path: Path) -> str:
    return source_html_path.resolve().parent.as_uri().rstrip("/") + "/"


def _split_css_segments(css_text: str, default_base_url: str) -> list[tuple[str, str]]:
    """Split concatenated CSS into chunks with the URL used to resolve relative assets."""
    matches = list(EXTERNAL_STYLE_MARKER_RE.finditer(css_text))
    if not matches:
        return [(css_text, default_base_url)]

    segments: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        segments.append((css_text[: matches[0].start()], default_base_url))

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(css_text)
        base_url = match.group(1).strip()
        segments.append((css_text[start:end], base_url))
    return [(text, base_url) for text, base_url in segments if text.strip()]


def _google_font_variant_axes(variants: list[str]) -> str:
    parsed: list[tuple[int, int]] = []
    for variant in variants:
        token = variant.strip().lower()
        if not token:
            continue
        italic = 1 if "italic" in token else 0
        weight_match = re.search(r"\d{3}", token)
        if weight_match:
            weight = int(weight_match.group(0))
        elif token == "regular" or not token:
            weight = 400
        else:
            weight = 400
        parsed.append((italic, weight))

    if not parsed:
        parsed.append((0, 400))
    parsed = sorted(set(parsed))
    if any(italic for italic, _ in parsed):
        values = ";".join(f"{italic},{weight}" for italic, weight in parsed)
        return f"ital,wght@{values}"
    values = ";".join(str(weight) for _, weight in parsed)
    return f"wght@{values}"


def _google_fonts_css2_url(families: list[str]) -> str | None:
    params: list[str] = []
    seen: set[str] = set()
    for family_spec in families:
        raw = family_spec.strip()
        if not raw:
            continue
        family, sep, variants_text = raw.partition(":")
        family = family.strip()
        if not family:
            continue
        variants = [variant.strip() for variant in variants_text.split(",") if variant.strip()] if sep else ["regular"]
        query_value = f"{family}:{_google_font_variant_axes(variants)}"
        if query_value in seen:
            continue
        seen.add(query_value)
        params.append("family=" + query_value.replace(" ", "+"))
    if not params:
        return None
    return "https://fonts.googleapis.com/css2?" + "&".join(params) + "&display=swap"


def _extract_webfont_google_families(html: str) -> list[str]:
    families: list[str] = []
    seen: set[str] = set()
    for script in _extract_script_blocks(html):
        for match in WEBFONT_GOOGLE_FAMILIES_RE.finditer(script):
            for string_match in JS_STRING_RE.finditer(match.group("families")):
                value = string_match.group("value").encode("utf-8").decode("unicode_escape").strip()
                if value and value not in seen:
                    seen.add(value)
                    families.append(value)
    return families


def _fetch_google_fonts_css_segments(families: list[str]) -> list[tuple[str, str]]:
    url = _google_fonts_css2_url(families)
    if not url:
        return []
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
    except Exception:
        return []
    return [(response.text, url)]


def _extract_css_segments(html: str, source_html_path: Path) -> tuple[list[tuple[str, str]], int, int]:
    default_base_url = _source_html_base_url(source_html_path)
    style_blocks = _extract_style_blocks(html)
    inline_styles = _extract_inline_style_declarations(html)
    segments: list[tuple[str, str]] = []
    segments.extend(_fetch_google_fonts_css_segments(_extract_webfont_google_families(html)))
    for block in style_blocks:
        segments.extend(_split_css_segments(block, default_base_url))
    if inline_styles:
        segments.append(("\n".join(inline_styles), default_base_url))
    return segments, len(style_blocks), len(inline_styles)


def _extract_custom_properties(css_text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for name, value in CUSTOM_PROPERTY_RE.findall(css_text):
        props[name.strip()] = value.strip()
    return props


def _extract_property_values(css_text: str, property_name: str, limit: int = 80) -> list[dict]:
    counts: Counter[str] = Counter()
    property_name = property_name.lower()
    for name, value in DECLARATION_RE.findall(css_text):
        if name.lower() != property_name:
            continue
        normalized = re.sub(r"\s+", " ", value.strip())
        lowered = normalized.lower()
        if not normalized or lowered in FONT_VALUE_SKIP:
            continue
        counts[normalized] += 1
    return [
        {"value": value, "count": count}
        for value, count in counts.most_common(limit)
    ]


def _iter_css_rules(css_segments: list[tuple[str, str]]) -> list[tuple[str, dict[str, str]]]:
    rules: list[tuple[str, dict[str, str]]] = []
    for css_text, _ in css_segments:
        for match in re.finditer(r"(?P<selector>[^{}@][^{}]*)\{(?P<body>[^{}]*)\}", css_text, flags=re.DOTALL):
            selector = re.sub(r"\s+", " ", match.group("selector").strip())
            declarations = _declaration_dict(match.group("body"))
            if selector and declarations:
                rules.append((selector, declarations))
    return rules


def _selector_list_contains(selector: str, target: str) -> bool:
    return any(part.strip().lower() == target for part in selector.split(","))


def _first_font_family_name(stack: str | None) -> str | None:
    if not stack:
        return None
    return _normalize_font_family_name(stack)


def _extract_body_font_stack(css_segments: list[tuple[str, str]], typography_props: dict[str, str]) -> str | None:
    body_stack: str | None = None
    for selector, declarations in _iter_css_rules(css_segments):
        if not _selector_list_contains(selector, "body"):
            continue
        resolved = _resolve_font_family_value(declarations.get("font-family"), typography_props)
        if resolved:
            body_stack = resolved
    return body_stack


def _extract_typography_custom_properties(raw_props: dict[str, str]) -> dict[str, str]:
    matches: dict[str, str] = {}
    for name, value in raw_props.items():
        lowered = name.lower()
        if any(token in lowered for token in ("font", "line-height", "letter-spacing", "tracking")):
            matches[name] = value
    return matches


def _resolve_custom_property(name: str, props: dict[str, str], stack: tuple[str, ...] = ()) -> str | None:
    if name in stack:
        return props.get(name)
    value = props.get(name)
    if value is None:
        return None

    def replace(match: re.Match[str]) -> str:
        ref_name = match.group(1)
        fallback = match.group(2)
        resolved = _resolve_custom_property(ref_name, props, stack + (name,))
        return resolved or (fallback.strip() if fallback else match.group(0))

    previous = None
    current = value
    while previous != current:
        previous = current
        current = VAR_REF_RE.sub(replace, current)
    return current.strip()


def _resolve_font_family_value(value: str | None, props: dict[str, str]) -> str | None:
    """Return a generation-safe font-family stack with source CSS vars resolved."""
    if not isinstance(value, str):
        return None
    current = value.strip().rstrip(";")
    if not current:
        return None
    current = re.sub(r"\s*!important\b", "", current, flags=re.IGNORECASE).strip()

    def replace(match: re.Match[str]) -> str:
        resolved = _resolve_custom_property(match.group(1), props)
        if resolved:
            return resolved
        fallback = match.group(2)
        return fallback.strip() if fallback else match.group(0)

    previous = None
    while previous != current:
        previous = current
        current = VAR_REF_RE.sub(replace, current).strip()

    lowered = current.lower()
    if not current or lowered in FONT_VALUE_SKIP or "var(" in lowered:
        return None
    if "webflow-icons" in lowered:
        return None
    return current


def _extract_color_literals(css_text: str) -> Counter[str]:
    values: Counter[str] = Counter()

    for match in HEX_RE.findall(css_text):
        values[normalize_color_literal(match)] += 1
    for match in RGB_RE.findall(css_text):
        values[normalize_color_literal(match)] += 1
    for match in HSL_RE.findall(css_text):
        values[normalize_color_literal(match)] += 1
    values["transparent"] += len(re.findall(r"\btransparent\b", css_text, re.IGNORECASE))

    if "transparent" in values and values["transparent"] == 0:
        values.pop("transparent", None)

    return values


def _declaration_dict(css_body: str) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for name, value in DECLARATION_RE.findall(css_body):
        declarations[name.strip().lower()] = re.sub(r"\s+", " ", value.strip())
    return declarations


def _normalize_font_family_name(value: str) -> str:
    value = value.strip()
    if "," in value:
        value = value.split(",", 1)[0]
    return value.strip().strip("'\"")


def _font_format_from_url(url: str, declared_format: str | None = None) -> str:
    if declared_format:
        cleaned = declared_format.strip().strip("'\"").lower()
        if cleaned:
            return cleaned
    suffix = Path(urlparse(url).path).suffix.lower().lstrip(".")
    return suffix or "font"


def _resolve_css_asset_url(raw_url: str, base_url: str) -> str:
    """Resolve CSS asset URLs, unwrapping captured /vendor-assets/<host>/ paths."""
    stripped = raw_url.strip()
    parsed = urlparse(stripped)
    if parsed.scheme:
        return stripped
    if stripped.startswith("/vendor-assets/"):
        rest = stripped[len("/vendor-assets/") :]
        host, sep, path = rest.partition("/")
        if sep and "." in host:
            return f"https://{host}/{path}"
    return urljoin(base_url, stripped)


def _safe_font_filename(index: int, url: str, family: str, weight: str, style: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in FONT_ASSET_EXTENSIONS:
        suffix = ".woff2"
    stem_source = "-".join(part for part in (family, weight, style) if part)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem_source).strip("-").lower() or "font"
    return f"{index:02d}-{stem}{suffix}"


def _local_file_from_url(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        return None
    return Path(parsed.path)


def _download_font_asset(url: str, output_path: Path, timeout_s: int = 30) -> str:
    parsed = urlparse(url)
    local_file = _local_file_from_url(url)
    if local_file and local_file.exists():
        output_path.write_bytes(local_file.read_bytes())
        return "copied"

    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported font URL scheme: {parsed.scheme or '(relative)'}")

    response = requests.get(
        url,
        timeout=timeout_s,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return "downloaded"


def _extract_font_faces(css_segments: list[tuple[str, str]], font_assets_dir: str | Path | None = None) -> list[dict]:
    font_faces: list[dict] = []
    seen_sources: set[str] = set()
    assets_dir = Path(font_assets_dir) if font_assets_dir else None
    if assets_dir:
        assets_dir.mkdir(parents=True, exist_ok=True)

    for css_text, base_url in css_segments:
        for face_match in FONT_FACE_RE.finditer(css_text):
            body = face_match.group("body")
            declarations = _declaration_dict(body)
            family = _normalize_font_family_name(declarations.get("font-family", ""))
            style = declarations.get("font-style", "normal")
            weight = declarations.get("font-weight", "400")
            display = declarations.get("font-display", "")
            src = declarations.get("src", "")

            if not family or not src:
                continue

            candidate_entries: list[dict] = []
            for url_match in CSS_URL_RE.finditer(src):
                raw_url = url_match.group("url").strip()
                if not raw_url or raw_url.startswith("data:"):
                    continue
                resolved_url = _resolve_css_asset_url(raw_url, base_url)
                if resolved_url in seen_sources:
                    continue

                format_match = re.search(
                    r"format\(\s*(['\"]?)([^'\")]+)\1\s*\)",
                    src[url_match.end() : url_match.end() + 80],
                    flags=re.IGNORECASE,
                )
                font_format = _font_format_from_url(
                    resolved_url,
                    format_match.group(2) if format_match else None,
                )
                entry = {
                    "font_family": family,
                    "font_style": style,
                    "font_weight": weight,
                    "font_display": display,
                    "source_url": resolved_url,
                    "format": font_format,
                    "status": "referenced",
                }
                candidate_entries.append(entry)

            if not candidate_entries:
                continue

            saved_entry: dict | None = None
            failed_entries: list[dict] = []
            if assets_dir:
                for entry in candidate_entries:
                    resolved_url = entry["source_url"]
                    if resolved_url in seen_sources:
                        continue
                    seen_sources.add(resolved_url)
                    filename = _safe_font_filename(len(font_faces) + 1, resolved_url, family, weight, style)
                    local_path = assets_dir / filename
                    try:
                        status = _download_font_asset(resolved_url, local_path)
                        saved_entry = {
                            **entry,
                            "status": status,
                            "local_path": str(local_path.resolve()),
                            "relative_path": f"{assets_dir.name}/{filename}",
                        }
                        break
                    except Exception as exc:  # pragma: no cover - depends on external font hosts
                        failed_entries.append(
                            {
                                **entry,
                                "status": "failed",
                                "error": str(exc),
                            }
                        )
                if saved_entry:
                    font_faces.append(saved_entry)
                elif failed_entries:
                    failed = failed_entries[0]
                    if len(failed_entries) > 1:
                        failed["fallback_errors"] = [
                            {
                                "source_url": item.get("source_url"),
                                "error": item.get("error"),
                            }
                            for item in failed_entries[1:]
                        ]
                    font_faces.append(failed)
            else:
                for entry in candidate_entries:
                    resolved_url = entry["source_url"]
                    if resolved_url in seen_sources:
                        continue
                    seen_sources.add(resolved_url)
                    font_faces.append(entry)
                    break

    return font_faces


def build_source_font_css(extracted: dict) -> str:
    """Return local @font-face CSS for downloaded source fonts."""
    rules: list[str] = []
    for face in extracted.get("font_faces", []):
        src_path = face.get("relative_path") or face.get("source_url")
        family = face.get("font_family")
        if not src_path or not family:
            continue
        font_format = face.get("format") or _font_format_from_url(src_path)
        lines = [
            "@font-face {",
            f"  font-family: {json.dumps(family)};",
            f"  src: url({json.dumps(src_path)}) format({json.dumps(font_format)});",
            f"  font-weight: {face.get('font_weight') or '400'};",
            f"  font-style: {face.get('font_style') or 'normal'};",
        ]
        if face.get("font_display"):
            lines.append(f"  font-display: {face['font_display']};")
        lines.append("}")
        rules.append("\n".join(lines))
    return "\n\n".join(rules)


def primary_source_font_stack(extracted: dict) -> str | None:
    """Return the most likely source-backed CSS font stack."""
    typography_props = extracted.get("typography_custom_properties", {})
    if not isinstance(typography_props, dict):
        typography_props = {}
    body_stack = _resolve_font_family_value(extracted.get("source_body_font_stack"), typography_props)
    if body_stack:
        return body_stack
    downloaded_families = [
        face.get("font_family")
        for face in extracted.get("font_faces", [])
        if face.get("font_family") and (face.get("relative_path") or face.get("source_url"))
    ]
    family_counts = Counter(downloaded_families)
    downloaded_family_names = {str(family).lower() for family in family_counts}
    for entry in extracted.get("frequent_font_families", []):
        resolved = _resolve_font_family_value(entry.get("value"), typography_props)
        first_family = _first_font_family_name(resolved)
        if first_family and first_family.lower() in downloaded_family_names:
            return resolved

    primary_family = family_counts.most_common(1)[0][0] if family_counts else None
    if not primary_family:
        for entry in extracted.get("frequent_font_families", []):
            resolved = _resolve_font_family_value(entry.get("value"), typography_props)
            if resolved:
                return resolved
        return None
    for entry in extracted.get("frequent_font_families", []):
        resolved = _resolve_font_family_value(entry.get("value"), typography_props)
        if isinstance(resolved, str) and primary_family.lower() in resolved.lower():
            return resolved
    return f'"{primary_family}", sans-serif'


def source_decorative_italic_font_stack(extracted: dict) -> str | None:
    """Return a distinct source font stack used for italic/decorative emphasis."""
    stack = extracted.get("source_decorative_italic_font_stack")
    if isinstance(stack, str) and stack.strip():
        return _resolve_font_family_value(stack, extracted.get("typography_custom_properties", {}))
    return None


def _source_font_stack_from_variables(extracted: dict, variable_names: tuple[str, ...]) -> str | None:
    typography_props = extracted.get("typography_custom_properties", {})
    if not isinstance(typography_props, dict):
        return None

    for variable_name in variable_names:
        resolved = _resolve_custom_property(variable_name, typography_props)
        if not resolved:
            continue
        resolved = _resolve_font_family_value(resolved, typography_props)
        if not resolved:
            continue
        lowered = resolved.lower()
        if not resolved or lowered in FONT_VALUE_SKIP or lowered.startswith("var("):
            continue
        return resolved

    return None


def source_heading_font_stack(extracted: dict) -> str | None:
    """Return the source-backed heading/display font stack when one is declared."""
    return _source_font_stack_from_variables(
        extracted,
        (
            "--_typography---h1--font",
            "--_typography---h2--font",
            "--_typography---h3--font",
            "--font-display",
            "--display-font",
            "--heading-font",
        ),
    )


def _extract_decorative_italic_font_stack(
    css_segments: list[tuple[str, str]],
    typography_props: dict[str, str],
    primary_stack: str | None,
) -> str | None:
    primary_family = (_first_font_family_name(primary_stack) or "").lower()
    scores: Counter[str] = Counter()
    last_value: dict[str, str] = {}
    for selector, declarations in _iter_css_rules(css_segments):
        resolved = _resolve_font_family_value(declarations.get("font-family"), typography_props)
        if not resolved:
            continue
        family = _first_font_family_name(resolved)
        if not family or family.lower() == primary_family:
            continue
        lowered_selector = selector.lower()
        style = (declarations.get("font-style") or "").lower()
        score = 0
        if "italic" in style or "oblique" in style:
            score += 3
        if any(token in lowered_selector for token in ("italic", "emphasis", "script")) or re.search(
            r"(^|[\s>+~,.#])em($|[\s>+~,.#:\[])", lowered_selector
        ):
            score += 2
        if "heading" in lowered_selector or re.search(r"\bh[1-6]\b", lowered_selector):
            score += 1
        if score <= 0:
            continue
        key = normalize_font_family_literal(resolved)
        scores[key] += score
        last_value[key] = resolved
    if not scores:
        return None
    return last_value[scores.most_common(1)[0][0]]


def build_source_font_implementation_css(extracted: dict) -> str:
    """Return @font-face CSS plus a conservative type-element font-family rule."""
    font_css = build_source_font_css(extracted)
    body_stack = primary_source_font_stack(extracted)
    heading_stack = source_heading_font_stack(extracted)
    decorative_italic_stack = source_decorative_italic_font_stack(extracted)
    if heading_stack and body_stack and normalize_font_family_literal(heading_stack) == normalize_font_family_literal(body_stack):
        heading_stack = None
    if decorative_italic_stack and body_stack and normalize_font_family_literal(decorative_italic_stack) == normalize_font_family_literal(body_stack):
        decorative_italic_stack = None

    if not font_css and not body_stack and not heading_stack and not decorative_italic_stack:
        return ""
    rules = [font_css] if font_css else []
    root_vars: list[str] = []
    body_stack = _resolve_font_family_value(body_stack, extracted.get("typography_custom_properties", {}))
    heading_stack = _resolve_font_family_value(heading_stack, extracted.get("typography_custom_properties", {}))
    decorative_italic_stack = _resolve_font_family_value(
        decorative_italic_stack,
        extracted.get("typography_custom_properties", {}),
    )
    if body_stack:
        root_vars.append(f"--stt-source-font-family: {body_stack};")
    if heading_stack:
        root_vars.append(f"--stt-source-heading-font-family: {heading_stack};")
    if decorative_italic_stack:
        root_vars.append(f"--stt-source-decorative-italic-font-family: {decorative_italic_stack};")
    if root_vars:
        rules.append(":root { " + " ".join(root_vars) + " }")
    if body_stack:
        rules.append("html, body, button, input, textarea, select { font-family: var(--stt-source-font-family) !important; }")
    if heading_stack:
        rules.append(
            "h1, h2, h3, h4, h5, h6, "
            ".display, .heading, .heading-lg, .heading-md, .heading-sm, "
            "[class*=\"display\"], [class*=\"heading\"] { "
            "font-family: var(--stt-source-heading-font-family) !important; }"
        )
    elif body_stack:
        rules.append(
            "h1, h2, h3, h4, h5, h6, "
            ".display, .heading, .heading-lg, .heading-md, .heading-sm, "
            "[class*=\"display\"], [class*=\"heading\"] { "
            "font-family: var(--stt-source-font-family) !important; }"
        )
    if decorative_italic_stack:
        rules.append(
            "h1 em, h2 em, h3 em, h4 em, h5 em, h6 em, "
            ".display em, .heading em, [class*=\"display\"] em, [class*=\"heading\"] em, "
            ".emphasis, .italic, [class*=\"emphasis\"], [class*=\"italic\"] { "
            "font-family: var(--stt-source-decorative-italic-font-family) !important; "
            "font-style: italic; }"
        )
    return "\n\n".join(rules)


def append_source_font_implementation(markdown: str, extracted: dict) -> str:
    """Append source font instructions to a generation markdown artifact."""
    css = build_source_font_implementation_css(extracted)
    if not css:
        return markdown

    if re.search(r"^## Source Font Implementation\s*$", markdown, flags=re.MULTILINE):
        return markdown
    if re.search(r"^source_font_implementation:\s*$", markdown, flags=re.MULTILINE):
        return markdown

    stack = primary_source_font_stack(extracted)
    heading_stack = source_heading_font_stack(extracted)
    decorative_italic_stack = source_decorative_italic_font_stack(extracted)
    stripped = markdown.rstrip()
    if stripped.startswith("schema_version: design_system_yaml.") or stripped.startswith("yaml\nschema_version: design_system_yaml."):
        if stripped.startswith("yaml\n"):
            stripped = stripped.split("\n", 1)[1]
        lines = [
            stripped,
            "source_font_implementation:",
            '  guidance: "Use the downloaded source font files for generated HTML rather than substituting a guessed web font."',
        ]
        if stack:
            lines.append(f'  primaryStack: "{stack.replace(chr(34), chr(92) + chr(34))}"')
        if heading_stack and normalize_font_family_literal(heading_stack) != normalize_font_family_literal(stack or ""):
            lines.append(f'  headingStack: "{heading_stack.replace(chr(34), chr(92) + chr(34))}"')
        if decorative_italic_stack:
            lines.append(f'  decorativeItalicStack: "{decorative_italic_stack.replace(chr(34), chr(92) + chr(34))}"')
        lines.append("  css: |")
        lines.extend(f"    {line}" if line else "" for line in css.splitlines())
        lines.append("")
        return "\n".join(lines)

    lines = [
        stripped,
        "",
        "## Source Font Implementation",
        "",
        "- Use the downloaded source font files for generated HTML rather than substituting a guessed web font.",
    ]
    if stack:
        lines.append(f"- Primary source font stack: `{stack}`")
    if heading_stack and normalize_font_family_literal(heading_stack) != normalize_font_family_literal(stack or ""):
        lines.append(f"- Source heading/display font stack: `{heading_stack}`")
    if decorative_italic_stack:
        lines.append(f"- Source decorative italic font stack: `{decorative_italic_stack}`")
    lines.extend(
        [
            "- Include this CSS in the generated page and keep generated type elements on this font stack unless a more specific source-backed type rule is listed above.",
            "",
            "```css",
            css,
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def extract_source_colors(source_html_path: str | Path, font_assets_dir: str | Path | None = None) -> dict:
    """Extract resolved CSS colors plus typography/style signals from HTML/CSS."""
    source_html_path = Path(source_html_path)
    html = source_html_path.read_text(errors="ignore")
    css_segments, style_block_count, inline_style_count = _extract_css_segments(html, source_html_path)
    css_text = "\n\n".join(css_text for css_text, _ in css_segments)

    raw_props = _extract_custom_properties(css_text)
    typography_custom_props = _extract_typography_custom_properties(raw_props)
    resolved_props: dict[str, str] = {}
    gradient_props: dict[str, str] = {}
    for name in sorted(raw_props):
        resolved = _resolve_custom_property(name, raw_props)
        if not resolved or not _is_color_like_value(resolved):
            continue
        if GRADIENT_RE.search(resolved):
            gradient_props[name] = resolved
        else:
            resolved_props[name] = resolved

    literal_counts = _extract_color_literals(css_text)
    frequent_literals = [
        {"value": value, "count": count}
        for value, count in literal_counts.most_common(80)
    ]

    typography_property_counts = {
        "font_shorthands": _extract_property_values(css_text, "font"),
        "font_families": _extract_property_values(css_text, "font-family"),
        "font_sizes": _extract_property_values(css_text, "font-size"),
        "font_weights": _extract_property_values(css_text, "font-weight"),
        "line_heights": _extract_property_values(css_text, "line-height"),
        "letter_spacings": _extract_property_values(css_text, "letter-spacing"),
    }
    font_faces = _extract_font_faces(css_segments, font_assets_dir=font_assets_dir)

    extracted = {
        "source_html": str(source_html_path.resolve()),
        "style_block_count": style_block_count,
        "inline_style_count": inline_style_count,
        "resolved_custom_properties": resolved_props,
        "gradient_custom_properties": gradient_props,
        "frequent_color_literals": frequent_literals,
        "typography_custom_properties": typography_custom_props,
        "font_faces": font_faces,
        "source_font_stack": None,
        "source_body_font_stack": _extract_body_font_stack(css_segments, typography_custom_props),
        "source_heading_font_stack": None,
        "source_decorative_italic_font_stack": None,
        "frequent_font_families": typography_property_counts["font_families"],
        "frequent_font_shorthands": typography_property_counts["font_shorthands"],
        "frequent_font_sizes": typography_property_counts["font_sizes"],
        "frequent_font_weights": typography_property_counts["font_weights"],
        "frequent_line_heights": typography_property_counts["line_heights"],
        "frequent_letter_spacings": typography_property_counts["letter_spacings"],
    }
    extracted["source_font_stack"] = primary_source_font_stack(extracted)
    extracted["source_heading_font_stack"] = source_heading_font_stack(extracted)
    extracted["source_decorative_italic_font_stack"] = _extract_decorative_italic_font_stack(
        css_segments,
        typography_custom_props,
        extracted["source_font_stack"],
    )
    return extracted


def render_source_color_report(extracted: dict) -> str:
    """Render extracted source colors and typography into a compact markdown report."""
    lines = [
        "# Source CSS Styles",
        "",
        f"- Source HTML: `{extracted['source_html']}`",
        f"- Style blocks parsed: {extracted['style_block_count']}",
        f"- Inline style attributes parsed: {extracted.get('inline_style_count', 0)}",
        "",
        "## Resolved Color Variables",
        "",
    ]

    resolved_props: dict[str, str] = extracted.get("resolved_custom_properties", {})
    if resolved_props:
        for name, value in sorted(resolved_props.items()):
            lines.append(f"- `{name}`: `{value}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Resolved Gradient Variables", ""])
    gradient_props: dict[str, str] = extracted.get("gradient_custom_properties", {})
    if gradient_props:
        for name, value in sorted(gradient_props.items()):
            lines.append(f"- `{name}`: `{value}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Frequent Literal Colors", ""])
    frequent_literals: list[dict] = extracted.get("frequent_color_literals", [])
    if frequent_literals:
        for entry in frequent_literals:
            lines.append(f"- `{entry['value']}` — {entry['count']} uses")
    else:
        lines.append("- None")

    lines.extend(["", "## Typography Variables", ""])
    typography_props: dict[str, str] = extracted.get("typography_custom_properties", {})
    if typography_props:
        for name, value in sorted(typography_props.items()):
            lines.append(f"- `{name}`: `{value}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Downloaded Font Assets", ""])
    font_faces: list[dict] = extracted.get("font_faces", [])
    if font_faces:
        for face in font_faces:
            descriptor = (
                f"`{face.get('font_family')}` "
                f"weight `{face.get('font_weight') or '400'}`, "
                f"style `{face.get('font_style') or 'normal'}`"
            )
            rel_path = face.get("relative_path")
            status = face.get("status", "referenced")
            if rel_path:
                lines.append(f"- {descriptor}: `{rel_path}` ({status})")
            else:
                lines.append(f"- {descriptor}: `{face.get('source_url', '')}` ({status})")
    else:
        lines.append("- None")

    stack = extracted.get("source_font_stack")
    if stack:
        lines.extend(["", "## Source Font Stack", "", f"- `{stack}`"])

    heading_stack = extracted.get("source_heading_font_stack")
    if heading_stack:
        lines.extend(["", "## Source Heading Font Stack", "", f"- `{heading_stack}`"])

    decorative_italic_stack = extracted.get("source_decorative_italic_font_stack")
    if decorative_italic_stack:
        lines.extend(["", "## Source Decorative Italic Font Stack", "", f"- `{decorative_italic_stack}`"])

    font_css = build_source_font_implementation_css(extracted)
    if font_css:
        lines.extend(["", "## Source Font Implementation CSS", "", "```css", font_css, "```"])

    typography_sections = (
        ("Frequent Font Shorthands", extracted.get("frequent_font_shorthands", [])),
        ("Frequent Font Families", extracted.get("frequent_font_families", [])),
        ("Frequent Font Sizes", extracted.get("frequent_font_sizes", [])),
        ("Frequent Font Weights", extracted.get("frequent_font_weights", [])),
        ("Frequent Line Heights", extracted.get("frequent_line_heights", [])),
        ("Frequent Letter Spacings", extracted.get("frequent_letter_spacings", [])),
    )
    for title, entries in typography_sections:
        lines.extend(["", f"## {title}", ""])
        if entries:
            for entry in entries:
                lines.append(f"- `{entry['value']}` — {entry['count']} uses")
        else:
            lines.append("- None")

    return "\n".join(lines).rstrip() + "\n"


def write_source_color_artifacts(output_dir: str | Path, extracted: dict) -> tuple[Path, Path]:
    """Write both JSON and markdown artifacts for extracted source colors."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source-colors.json"
    md_path = output_dir / "source-colors.md"
    json_path.write_text(json.dumps(extracted, indent=2) + "\n")
    md_path.write_text(render_source_color_report(extracted))
    return json_path, md_path


def collect_allowed_source_color_literals(extracted: dict) -> set[str]:
    """Return a normalized set of exact color literals/gradients allowed by the source HTML."""
    allowed: set[str] = set()

    for value in extracted.get("resolved_custom_properties", {}).values():
        if isinstance(value, str) and value.strip():
            normalized = normalize_color_literal(value.strip())
            allowed.add(normalized)
            allowed.add(value.strip())
            for literal in extract_document_color_literals(value):
                allowed.add(literal)

    for value in extracted.get("gradient_custom_properties", {}).values():
        if isinstance(value, str) and value.strip():
            allowed.add(value.strip())
            for literal in extract_document_color_literals(value):
                allowed.add(literal)

    for entry in extracted.get("frequent_color_literals", []):
        value = entry.get("value")
        if isinstance(value, str) and value.strip():
            allowed.add(normalize_color_literal(value))

    return allowed


def normalize_font_family_literal(value: str) -> str:
    """Normalize a font-family value for stable comparison."""
    value = value.strip().strip("`").strip()
    value = re.sub(r"\s*,\s*", ",", value)
    value = re.sub(r"\s+", " ", value)
    return value.lower()


def collect_allowed_source_font_family_literals(extracted: dict) -> set[str]:
    """Return normalized explicit font-family values allowed by the source HTML."""
    allowed: set[str] = set()

    source_stack = extracted.get("source_font_stack")
    if isinstance(source_stack, str) and source_stack.strip():
        allowed.add(normalize_font_family_literal(source_stack))

    heading_stack = extracted.get("source_heading_font_stack")
    if isinstance(heading_stack, str) and heading_stack.strip():
        allowed.add(normalize_font_family_literal(heading_stack))

    for face in extracted.get("font_faces", []):
        family = face.get("font_family") if isinstance(face, dict) else None
        if isinstance(family, str) and family.strip():
            allowed.add(normalize_font_family_literal(family))
            allowed.add(normalize_font_family_literal(f'"{family}"'))

    for name, value in extracted.get("typography_custom_properties", {}).items():
        if "font-family" not in name.lower():
            continue
        resolved = _resolve_font_family_value(value, extracted.get("typography_custom_properties", {}))
        if resolved:
            allowed.add(normalize_font_family_literal(resolved))

    for entry in extracted.get("frequent_font_families", []):
        resolved = _resolve_font_family_value(entry.get("value"), extracted.get("typography_custom_properties", {}))
        if resolved:
            allowed.add(normalize_font_family_literal(resolved))

    return allowed


def extract_document_color_literals(text: str) -> list[str]:
    """Extract explicit color literals/gradients from a markdown document."""
    literals: list[str] = []
    literals.extend(normalize_color_literal(match) for match in HEX_RE.findall(text))
    literals.extend(normalize_color_literal(match) for match in RGB_RE.findall(text))
    literals.extend(normalize_color_literal(match) for match in HSL_RE.findall(text))
    if re.search(r"\btransparent\b", text, re.IGNORECASE):
        literals.extend(["transparent"] * len(re.findall(r"\btransparent\b", text, re.IGNORECASE)))
    return literals


def find_non_source_document_colors(text: str, extracted: dict) -> list[str]:
    """Return sorted explicit color literals present in a document but absent from source HTML."""
    allowed = collect_allowed_source_color_literals(extracted)
    unsupported = {
        literal.strip()
        for literal in extract_document_color_literals(text)
        if literal.strip() and literal.strip() not in allowed
    }
    return sorted(unsupported)


def find_non_source_document_font_families(text: str, extracted: dict) -> list[str]:
    """Return explicit font-family declarations absent from source HTML."""
    allowed = collect_allowed_source_font_family_literals(extracted)
    unsupported: set[str] = set()

    for match in FONT_FAMILY_DECL_RE.findall(text):
        raw_value = match.strip()
        lowered = raw_value.lower()
        if not raw_value or lowered in FONT_VALUE_SKIP or lowered.startswith("var("):
            continue
        normalized = normalize_font_family_literal(raw_value)
        if normalized and normalized not in allowed:
            unsupported.add(raw_value)

    return sorted(unsupported)
