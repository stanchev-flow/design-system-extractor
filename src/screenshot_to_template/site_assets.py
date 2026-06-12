"""Generate custom site image assets and rewrite generated HTML to use them."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote

import yaml
from bs4 import BeautifulSoup, Tag
from PIL import Image

from .config import AppConfig
from .models.google import GoogleProvider
from .models.openai import OpenAIProvider


CHROME_HEADLESS_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_SITE_ASSET_IMAGE_MODEL = "gpt-image-2"
SCAN_ATTRIBUTE = "data-stt-node-id"
ASSET_BRIEF_ATTRIBUTE = "data-stt-asset-brief"
ASSET_SCAN_SCRIPT = r"""
<script>
(function () {
  function stringValue(value) {
    if (value == null) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    if (typeof value === "object" && typeof value.baseVal === "string") return value.baseVal;
    if (typeof value === "object" && typeof value.animVal === "string") return value.animVal;
    return String(value);
  }

  function normalizeText(value, maxLen) {
    const text = stringValue(value).replace(/\s+/g, " ").trim();
    return text.length > maxLen ? text.slice(0, maxLen - 1).trimEnd() + "…" : text;
  }

  function parseColor(color) {
    if (!color) return null;
    const match = color.match(/rgba?\(([^)]+)\)/i);
    if (!match) return null;
    const parts = match[1].split(",").map((part) => part.trim());
    if (parts.length < 3) return null;
    const r = Math.max(0, Math.min(255, parseFloat(parts[0])));
    const g = Math.max(0, Math.min(255, parseFloat(parts[1])));
    const b = Math.max(0, Math.min(255, parseFloat(parts[2])));
    const a = parts.length > 3 ? Math.max(0, Math.min(1, parseFloat(parts[3]))) : 1;
    return { r, g, b, a };
  }

  function rgbaToHex(color) {
    const parsed = parseColor(color);
    if (!parsed) return "";
    if (parsed.a <= 0.02) return "";
    const toHex = (channel) => Math.round(channel).toString(16).padStart(2, "0").toUpperCase();
    return "#" + toHex(parsed.r) + toHex(parsed.g) + toHex(parsed.b);
  }

  function hasUsableBox(style, rect) {
    if (!style || !rect) return false;
    if (rect.width < 16 || rect.height < 16) return false;
    if (style.display === "none") return false;
    return true;
  }

  function visible(style, rect) {
    if (!hasUsableBox(style, rect)) return false;
    if (style.visibility === "hidden") return false;
    if (parseFloat(style.opacity || "1") <= 0.02) return false;
    return true;
  }

  function elementHint(el) {
    return normalizeText(
      [
        el.getAttribute("alt"),
        el.getAttribute("%ASSET_BRIEF_ATTR%"),
        el.getAttribute("aria-label"),
        el.getAttribute("title"),
        el.getAttribute("role"),
        el.id,
        stringValue(el.className),
      ]
        .filter(Boolean)
        .join(" | "),
      240
    );
  }

  function nearestSection(el) {
    let current = el;
    while (current && current !== document.body) {
        const tag = (current.tagName || "").toLowerCase();
      const hint = [
        current.id || "",
        stringValue(current.className),
        current.getAttribute("role") || "",
        current.getAttribute("aria-label") || "",
      ]
        .join(" ")
        .toLowerCase();
      if (["section", "article", "header", "footer", "main", "nav", "aside"].includes(tag)) {
        return current;
      }
      if (/(hero|section|feature|card|panel|media|image|graphic|visual|gallery|logo|story|testimonial|cta)/.test(hint)) {
        if (current !== el || current.querySelector("h1, h2, h3, h4")) {
          return current;
        }
      }
      current = current.parentElement;
    }
    return document.body;
  }

  function sectionHeading(section) {
    if (!section) return "";
    const heading = section.querySelector("h1, h2, h3, h4");
    return heading ? normalizeText(heading.innerText || "", 120) : "";
  }

  function sectionText(section) {
    if (!section) return "";
    return normalizeText(section.innerText || "", 320);
  }

  function nearestOpaqueBackground(el) {
    let current = el;
    while (current) {
      const bg = rgbaToHex(getComputedStyle(current).backgroundColor || "");
      if (bg) return bg;
      current = current.parentElement;
    }
    return rgbaToHex(getComputedStyle(document.body).backgroundColor || "") || "#FFFFFF";
  }

  function simpleUtilitySvg(el, rect) {
    const area = rect.width * rect.height;
    const primitives = el.querySelectorAll("path, rect, circle, ellipse, line, polyline, polygon, text").length;
    const hint = [el.id || "", el.className || "", el.getAttribute("aria-label") || ""].join(" ").toLowerCase();
    if (/(logo|brand|illustration|graphic|visual|badge)/.test(hint)) return false;
    return area < 4096 && primitives <= 4;
  }

  const candidates = [];
  const nodes = document.querySelectorAll("[" + JSON.stringify("%SCAN_ATTR%").slice(1, -1) + "]");
  nodes.forEach((el) => {
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    const tag = (el.tagName || "").toLowerCase();
    const assetBrief = normalizeText(el.getAttribute("%ASSET_BRIEF_ATTR%") || "", 320);
    const src = normalizeText(el.getAttribute("src") || "", 512);
    if (assetBrief && tag === "img" && src && !src.startsWith("data:")) return;
    if (assetBrief) {
      if (!hasUsableBox(style, rect)) return;
    } else if (!visible(style, rect)) {
      return;
    }

    let targetKind = "";
    if (tag === "img") {
      targetKind = "img";
    } else if (tag === "svg") {
      if (!assetBrief) return;
      if (simpleUtilitySvg(el, rect)) return;
      targetKind = "svg";
    } else if ((style.backgroundImage || "").includes("url(")) {
      targetKind = "css_background";
    } else {
      return;
    }

    const section = nearestSection(el);
    candidates.push({
      node_id: el.getAttribute("%SCAN_ATTR%"),
      tag_name: tag,
      target_kind: targetKind,
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      asset_brief: assetBrief,
      alt_text: normalizeText(el.getAttribute("alt") || "", 160),
      aria_label: normalizeText(el.getAttribute("aria-label") || "", 160),
      label_hint: elementHint(el),
      class_name: normalizeText(stringValue(el.className), 160),
      id_attr: normalizeText(el.id || "", 120),
      page_title: normalizeText(document.title || "", 120),
      section_heading: sectionHeading(section),
      nearby_text: sectionText(section),
      section_background: nearestOpaqueBackground(el),
      background_image: style.backgroundImage || "",
      background_size: style.backgroundSize || "",
      background_position: style.backgroundPosition || "",
      background_repeat: style.backgroundRepeat || "",
    });
  });

  const script = document.createElement("script");
  script.id = "stt-asset-scan";
  script.type = "application/json";
  script.textContent = JSON.stringify({ candidates });
  document.body.appendChild(script);
})();
</script>
"""


def _image_provider_for_model(model_name: str):
    if model_name.startswith("gpt-image") or model_name.startswith("dall-e"):
        return OpenAIProvider(model_name)
    return GoogleProvider(model_name)
ASSET_SCAN_SCRIPT = ASSET_SCAN_SCRIPT.replace("%SCAN_ATTR%", SCAN_ATTRIBUTE)
ASSET_SCAN_SCRIPT = ASSET_SCAN_SCRIPT.replace("%ASSET_BRIEF_ATTR%", ASSET_BRIEF_ATTRIBUTE)

SUPPORTED_ASPECT_RATIOS: tuple[tuple[str, float], ...] = (
    ("1:1", 1.0),
    ("4:5", 4 / 5),
    ("3:4", 3 / 4),
    ("2:3", 2 / 3),
    ("9:16", 9 / 16),
    ("5:4", 5 / 4),
    ("4:3", 4 / 3),
    ("3:2", 3 / 2),
    ("16:9", 16 / 9),
    ("21:9", 21 / 9),
)


def _safe_slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "asset"


def _append_style_declaration(existing_style: str | None, declarations: dict[str, str]) -> str:
    pieces = [segment.strip() for segment in (existing_style or "").split(";") if segment.strip()]
    style_map: dict[str, str] = {}
    for piece in pieces:
        if ":" not in piece:
            continue
        name, value = piece.split(":", 1)
        style_map[name.strip().lower()] = value.strip()
    for name, value in declarations.items():
        if value:
            style_map[name] = value
    return "; ".join(f"{name}: {value}" for name, value in style_map.items())


def _choose_aspect_ratio(width: int, height: int) -> str:
    safe_height = max(height, 1)
    ratio = width / safe_height
    return min(SUPPORTED_ASPECT_RATIOS, key=lambda item: abs(item[1] - ratio))[0]


def _choose_image_size(width: int, height: int) -> str:
    largest_edge = max(width, height)
    return "2K" if largest_edge >= 900 else "1K"


def _plain_text(value: str | None, max_chars: int = 240) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _candidate_text(candidate: dict, keys: tuple[str, ...] | None = None) -> str:
    keys = keys or (
        "asset_brief",
        "alt_text",
        "aria_label",
        "label_hint",
        "class_name",
        "id_attr",
        "section_heading",
        "nearby_text",
    )
    return " ".join(str(candidate.get(key) or "") for key in keys).lower()


def _icon_asset_class(candidate: dict) -> str:
    """Classify icon-like asset briefs into the deterministic generation route."""
    text = _candidate_text(candidate)
    if re.search(r"\b(logo|wordmark|brand\s*mark|customer\s*mark|payment\s*mark)\b", text):
        return "logo/wordmark"
    if re.search(r"\bmulti[-\s]?colou?r[-\s]?icon\b|\bmulti[-\s]?colou?r(?:ed)?\s+(?:pictorial\s+)?icon\b", text):
        return "multi-color-icon"
    if re.search(r"\b(single[-\s]?colou?r[-\s]?icon|one[-\s]?colou?r\s+icon|monochrome\s+icon)\b", text):
        return "single-color-icon"
    if re.search(
        r"\b(simple|utility|ui|stroke|line|outline|glyph)\b.*\b(icon|glyph|pictogram|symbol)\b",
        text,
    ) and not re.search(r"\b(multi[-\s]?colou?r|colorful|gradient|dimensional|pictorial)\b", text):
        return "single-color-icon"
    return ""


def _numeric_attr_or_style(tag: Tag, name: str, default: int) -> int:
    raw_attr = tag.get(name)
    if raw_attr:
        match = re.search(r"\d+(?:\.\d+)?", str(raw_attr))
        if match:
            return max(1, round(float(match.group(0))))

    style = tag.get("style") or ""
    match = re.search(rf"(?:^|;)\s*{re.escape(name)}\s*:\s*(\d+(?:\.\d+)?)px", style, flags=re.IGNORECASE)
    if match:
        return max(1, round(float(match.group(1))))

    return default


def _svg_dimensions_from_data_uri(src: str | None) -> tuple[int | None, int | None]:
    """Read simple width/height values from blank SVG data URI placeholders."""
    if not src or not src.startswith("data:image/svg+xml"):
        return None, None
    _, _, payload = src.partition(",")
    if not payload:
        return None, None
    svg = unquote(payload)

    def attr_value(name: str) -> int | None:
        match = re.search(rf"\b{name}\s*=\s*['\"]?(\d+(?:\.\d+)?)", svg, flags=re.IGNORECASE)
        if match:
            return max(1, round(float(match.group(1))))
        return None

    width = attr_value("width")
    height = attr_value("height")
    if width and height:
        return width, height

    viewbox = re.search(
        r"\bviewBox\s*=\s*['\"]\s*[-\d.]+\s+[-\d.]+\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)",
        svg,
        flags=re.IGNORECASE,
    )
    if viewbox:
        return (
            width or max(1, round(float(viewbox.group(1)))),
            height or max(1, round(float(viewbox.group(2)))),
        )
    return width, height


def _source_design_system_text(markdown: str) -> str:
    """Keep image prompts away from downstream implementation-skill prose."""
    text = markdown.strip()
    for marker in (
        "\n## Active Site Generation Skills",
        "\n# Active Site Generation Skills",
        "\n### shader-effects",
        "\n# Shader Effects",
        "\n### abstract-three-webgl",
        "\n# Abstract Three.js",
        "\n# Motion Design With GSAP",
    ):
        index = text.find(marker)
        if index != -1:
            text = text[:index].rstrip()
    return text


def _extract_heading_section(markdown: str, heading: str) -> str:
    pattern = re.compile(
        rf"^(?P<marks>#+)\s+{re.escape(heading)}\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(markdown)
    if not match:
        return ""
    level = len(match.group("marks"))
    next_heading = re.compile(rf"^#{{1,{level}}}\s+\S", flags=re.MULTILINE)
    next_match = next_heading.search(markdown, match.end())
    end = next_match.start() if next_match else len(markdown)
    return markdown[match.end() : end].strip()


def _extract_bullets(text: str, max_items: int = 5) -> list[str]:
    bullets: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            bullet = _plain_text(stripped[2:], 180)
            if bullet and bullet not in bullets:
                bullets.append(bullet)
        if len(bullets) >= max_items:
            break
    return bullets


def _extract_named_hex_colors(markdown: str, max_items: int = 8) -> list[str]:
    colors: list[str] = []
    seen: set[str] = set()
    for line in markdown.splitlines():
        match = re.search(r"^\s*([A-Za-z][A-Za-z0-9_-]*)\s*:\s*[\"']?(#[0-9A-Fa-f]{3,8})", line)
        if not match:
            match = re.search(r"-\s*`?([A-Za-z][A-Za-z0-9_-]*)`?.*?`?(#[0-9A-Fa-f]{3,8})`?", line)
        if not match:
            continue
        name, color = match.group(1), match.group(2).upper()
        if color in seen:
            continue
        seen.add(color)
        colors.append(f"{name}: {color}")
        if len(colors) >= max_items:
            break
    return colors


def _load_design_system_yaml(markdown: str) -> dict:
    source = _source_design_system_text(markdown).strip()
    if source.startswith("---"):
        match = re.match(r"^---\s*\n(?P<yaml>.*?)\n---(?:\s*\n|$)", source, flags=re.DOTALL)
        if match:
            source = match.group("yaml")
    try:
        loaded = yaml.safe_load(source)
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _metadata_value(data: dict, key: str) -> str:
    metadata = data.get("metadata")
    if isinstance(metadata, dict) and metadata.get(key):
        return str(metadata[key])
    if data.get(key):
        return str(data[key])
    return ""


def _collect_nested_hex_colors(value, max_items: int = 8) -> list[str]:
    colors: list[str] = []
    seen: set[str] = set()

    def visit(node, path: str = "") -> None:
        if len(colors) >= max_items:
            return
        if isinstance(node, dict):
            for child_key, child_value in node.items():
                next_path = f"{path}.{child_key}" if path else str(child_key)
                visit(child_value, next_path)
                if len(colors) >= max_items:
                    return
        elif isinstance(node, str) and re.fullmatch(r"#[0-9A-Fa-f]{3,8}", node.strip()):
            color = node.strip().upper()
            if color in seen:
                return
            seen.add(color)
            colors.append(f"{path}: {color}")

    visit(value)
    return colors


def _yaml_rule_cues(data: dict, categories: tuple[str, ...], max_items: int = 10) -> list[str]:
    rules = data.get("rules")
    if not isinstance(rules, dict):
        return []
    cues: list[str] = []
    for category in categories:
        items = rules.get(category)
        if not isinstance(items, list):
            continue
        for item in items:
            cue = _plain_text(str(item), 220)
            if cue and cue not in cues:
                cues.append(cue)
            if len(cues) >= max_items:
                return cues
    return cues


def _yaml_image_graphic_cues(data: dict, max_items: int = 8) -> list[str]:
    layout = data.get("layout_patterns")
    if not isinstance(layout, dict):
        layout = data.get("patterns")
    image_graphics = layout.get("image_graphics") if isinstance(layout, dict) else None
    if not isinstance(image_graphics, list):
        return []
    cues: list[str] = []
    for item in image_graphics:
        if not isinstance(item, dict):
            continue
        parts = [str(item[key]) for key in ("name", "placement", "edgeBehavior", "realism", "description") if item.get(key)]
        cue = _plain_text("; ".join(parts), 260)
        if cue:
            cues.append(cue)
        if len(cues) >= max_items:
            break
    return cues


def _collect_imagery_creative_directions(markdown: str, data: dict) -> dict[str, list[str]]:
    """Collect category-specific imagery direction from YAML and markdown sections."""
    directions: dict[str, list[str]] = {
        "icons": [],
        "illustrations": [],
        "interfaces": [],
        "photography": [],
    }

    imagery = data.get("imagery")
    if isinstance(imagery, dict):
        for category in directions:
            spec = imagery.get(category)
            values: list[str] = []
            if isinstance(spec, dict):
                for key in (
                    "creativeDirection",
                    "style",
                    "density",
                    "simplicity",
                    "detailLevel",
                    "rendering",
                    "composition",
                    "surfaceRelationship",
                    "colorTreatment",
                    "avoid",
                ):
                    value = spec.get(key)
                    if isinstance(value, list):
                        values.extend(str(item) for item in value)
                    elif value:
                        values.append(str(value))
            elif isinstance(spec, list):
                values.extend(str(item) for item in spec)
            elif isinstance(spec, str):
                values.append(spec)
            for value in values:
                cue = _plain_text(value, 220)
                if cue and cue not in directions[category]:
                    directions[category].append(cue)

    for heading, category in (
        ("Icons", "icons"),
        ("Illustrations", "illustrations"),
        ("Interfaces", "interfaces"),
        ("Photography", "photography"),
    ):
        for bullet in _extract_bullets(_extract_heading_section(markdown, heading), max_items=6):
            if bullet not in directions[category]:
                directions[category].append(bullet)

    return {key: values[:8] for key, values in directions.items()}


def _yaml_surface_cues(data: dict, max_items: int = 6) -> list[str]:
    surfaces = data.get("surfaces")
    if not isinstance(surfaces, dict):
        return []
    cues: list[str] = []
    for name, spec in surfaces.items():
        if not isinstance(spec, dict):
            continue
        role = spec.get("role") or spec.get("kind")
        visual = spec.get("visualCharacteristics") or spec.get("description")
        fill = spec.get("fill") or spec.get("background")
        parts = [str(part) for part in (name, role, visual, fill) if part]
        cue = _plain_text("; ".join(parts), 220)
        if cue:
            cues.append(cue)
        if len(cues) >= max_items:
            break
    return cues


def _yaml_avoid_cues(data: dict, max_items: int = 8) -> list[str]:
    cues: list[str] = []
    for key in ("do_not_generalize", "embedded_showcase_only"):
        items = data.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            text = item
            if isinstance(item, dict):
                text = item.get("item") or item.get("reason") or item
            cue = _plain_text(str(text), 220)
            if cue and cue not in cues:
                cues.append(cue)
            if len(cues) >= max_items:
                return cues
    return cues


def _build_asset_style_profile(design_system_markdown: str) -> dict:
    source_text = _source_design_system_text(design_system_markdown)
    yaml_data = _load_design_system_yaml(source_text)
    name_match = re.search(r"^\s*name\s*:\s*[\"']?([^\"'\n]+)", source_text, flags=re.MULTILINE)
    description_match = re.search(
        r"^\s*description\s*:\s*[\"']?([^\"'\n]+)",
        source_text,
        flags=re.MULTILINE,
    )

    overview = _extract_heading_section(source_text, "Overview")
    color = _extract_heading_section(source_text, "Color")
    photography = _extract_heading_section(source_text, "Photography")
    icons = _extract_heading_section(source_text, "Icons")
    illustrations = _extract_heading_section(source_text, "Illustrations")
    interfaces = _extract_heading_section(source_text, "Interfaces")
    graphics = _extract_heading_section(source_text, "Graphics")
    decorations = _extract_heading_section(source_text, "Unique Decorations")
    backgrounds = _extract_heading_section(source_text, "Backgrounds")

    style_cues: list[str] = []
    for section in (overview, color, backgrounds):
        style_cues.extend(_extract_bullets(section, max_items=4))
    image_cues: list[str] = []
    for section in (icons, illustrations, interfaces, photography, graphics, decorations):
        image_cues.extend(_extract_bullets(section, max_items=4))

    yaml_palette = _collect_nested_hex_colors((yaml_data.get("tokens") or {}).get("color", {}))
    yaml_image_cues = _yaml_image_graphic_cues(yaml_data)
    yaml_rule_cues = _yaml_rule_cues(
        yaml_data,
        ("imagery_graphics", "color", "cards", "spacing", "containers"),
    )
    yaml_surface_cues = _yaml_surface_cues(yaml_data)
    yaml_avoid_cues = _yaml_avoid_cues(yaml_data)

    system_name = _metadata_value(yaml_data, "name") or (_plain_text(name_match.group(1), 120) if name_match else "")
    description = _metadata_value(yaml_data, "description") or (
        _plain_text(description_match.group(1), 220) if description_match else ""
    )

    return {
        "system_name": _plain_text(system_name, 120),
        "description": _plain_text(description, 220),
        "palette": (yaml_palette or _extract_named_hex_colors(source_text))[:8],
        "style_cues": (style_cues + yaml_surface_cues + yaml_rule_cues)[:10],
        "image_cues": (yaml_image_cues + image_cues)[:10],
        "creative_directions": _collect_imagery_creative_directions(source_text, yaml_data),
        "brand_rules": yaml_rule_cues[:10],
        "avoid_cues": yaml_avoid_cues[:8],
    }


def _asset_creative_category(candidate: dict, asset_kind: str) -> str:
    text = _candidate_text(
        candidate,
        (
            "asset_brief",
            "alt_text",
            "aria_label",
            "label_hint",
            "class_name",
            "id_attr",
            "section_heading",
        ),
    )
    if asset_kind == "photographic":
        return "photography"
    if asset_kind == "diagrammatic" or re.search(r"\b(interface|ui|dashboard|screen|app|device|mockup|product\s+ui)\b", text):
        return "interfaces"
    if asset_kind in {"single_color_icon", "multi_color_icon", "brand_or_badge"} or re.search(r"\b(icon|icons|pictogram|glyph|symbol|emblem|badge|mark)\b", text):
        return "icons"
    return "illustrations"


def _classify_asset_kind(candidate: dict) -> str:
    text = _candidate_text(
        candidate,
        (
            "asset_brief",
            "alt_text",
            "aria_label",
            "label_hint",
            "class_name",
            "id_attr",
            "section_heading",
        ),
    )
    target_kind = str(candidate.get("target_kind", "")).lower()
    icon_asset_class = _icon_asset_class(candidate)

    if re.search(r"\b(photo|photograph|photography|portrait|documentary|crowd|person|people|venue|room|environment|product shot)\b", text):
        return "photographic"
    if re.search(r"\b(diagram|chart|map|timeline|flow|schematic|dashboard|interface|ui)\b", text):
        return "diagrammatic"
    if icon_asset_class == "multi-color-icon":
        return "multi_color_icon"
    if icon_asset_class == "single-color-icon":
        return "single_color_icon"
    if icon_asset_class == "logo/wordmark":
        return "brand_or_badge"
    if re.search(r"\b(logo|brand|badge|mark|seal|emblem)\b", text):
        return "brand_or_badge"
    if re.search(r"\b(abstract|collage|illustration|graphic|shape|pattern|projection|installation|mesh|particle|ribbon)\b", text):
        return "abstract_graphic"
    if re.search(r"\b(texture|grain|noise|noisy|atmosphere|ambient|background|backdrop|wash|field)\b", text):
        return "atmospheric_background"
    return "general_visual"


def _build_asset_plan(candidate: dict, style_profile: dict | None = None) -> dict:
    asset_kind = _classify_asset_kind(candidate)
    width = int(candidate.get("width") or 0)
    height = int(candidate.get("height") or 0)
    aspect_ratio = _choose_aspect_ratio(width or 1024, height or 1024)

    creative_category = _asset_creative_category(candidate, asset_kind)

    if asset_kind == "photographic":
        prompt_focus = "Create a natural, production-quality photographic asset for this exact slot."
        composition = "Use the requested subject and crop it for the target aspect ratio; favor believable lighting, depth, and source-site mood."
    elif asset_kind == "multi_color_icon":
        prompt_focus = "Create one multi-color pictorial icon asset for this exact slot."
        composition = "Use the requested icon subject and the attached source reference for style; keep the mark compact, legible, non-textual, and fitted to the target aspect ratio."
    elif asset_kind == "single_color_icon":
        prompt_focus = "Do not generate this icon as an image asset."
        composition = "This route is reserved for inline Phosphor/currentColor SVG implementation, not raster generation."
    elif asset_kind == "atmospheric_background":
        prompt_focus = "Create a background or texture plate for this exact slot."
        composition = "Keep the image low-detail enough to sit behind foreground content; avoid a poster-like focal subject unless the brief asks for one."
    elif asset_kind == "diagrammatic":
        prompt_focus = "Create a polished diagrammatic visual for this exact slot."
        composition = "Use simple shapes and spatial hierarchy; do not include readable text, labels, screenshots, or app chrome."
    elif asset_kind == "brand_or_badge":
        prompt_focus = "Create a simple emblem-like visual for this exact slot."
        composition = "Keep it bold and legible as a graphic mark, with no readable lettering unless explicitly requested by the slot."
    elif asset_kind == "abstract_graphic":
        prompt_focus = "Create a static abstract graphic for this exact slot."
        composition = "Translate any procedural, ribbon, mesh, or particle language into a still raster composition; do not include code, canvas, or WebGL instructions."
    else:
        prompt_focus = "Create one custom visual asset for this exact website slot."
        composition = "Use the requested subject and adapt it to the target dimensions without adding unrelated decorative content."

    return {
        "asset_kind": asset_kind,
        "render_medium": "raster_image",
        "aspect_ratio": aspect_ratio,
        "prompt_focus": prompt_focus,
        "composition": composition,
        "style_profile": (style_profile or {}).get("system_name", ""),
        "creative_category": creative_category,
    }


def _asset_should_have_transparent_background(candidate: dict, asset_plan: dict) -> bool:
    """Return whether the generated asset should be cut out instead of framed."""
    asset_kind = asset_plan.get("asset_kind", "")
    if asset_kind in {"photographic", "atmospheric_background"}:
        return False
    if asset_kind in {"abstract_graphic", "brand_or_badge", "diagrammatic", "multi_color_icon"}:
        return True
    if asset_kind == "single_color_icon":
        return False

    text = " ".join(
        str(candidate.get(key, ""))
        for key in (
            "asset_brief",
            "alt_text",
            "aria_label",
            "label_hint",
            "class_name",
            "id_attr",
        )
    ).lower()
    return bool(
        re.search(
            r"\b(transparent|cutout|cut-out|foreground|sticker|spot illustration|line art|"
            r"illustration|graphic mark|badge|emblem|icon-like)\b",
            text,
        )
    )


REFERENCE_STYLE_ASSET_KINDS = {"abstract_graphic", "brand_or_badge", "diagrammatic", "general_visual", "multi_color_icon"}
REFERENCE_STYLE_KEYWORDS = re.compile(
    r"\b(multi[-\s]?colou?r[-\s]?icon|illustration|illustrative|graphic|line\s*art|vector|doodle|drawn|cartoon|"
    r"mascot|character|icon|icons|emblem|badge|mark|sticker|diagram|schematic|"
    r"interface|ui|dashboard|mockup|device|screen|chart|map|flow)\b",
    flags=re.IGNORECASE,
)


def _tokenize_reference_text(value: str) -> set[str]:
    stop = {
        "the", "and", "for", "with", "from", "this", "that", "into", "onto",
        "site", "section", "asset", "image", "visual", "style", "page",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 2 and token not in stop
    }


def _crop_reference_text(crop_path: Path) -> str:
    parts = [crop_path.stem.replace("-", " ")]
    grounding_dir = crop_path.parent.parent / "section-groundings"
    for suffix in (".yaml", ".md"):
        grounding_path = grounding_dir / f"{crop_path.stem}{suffix}"
        if grounding_path.exists():
            parts.append(_plain_text(grounding_path.read_text(errors="ignore"), 4000))
            break
    return " ".join(parts)


def _collect_graphic_reference_images(crops_dir: Path | None) -> list[dict]:
    """Find source section crops that demonstrate illustration/graphic/interface style."""
    if not crops_dir or not crops_dir.exists():
        return []
    references: list[dict] = []
    for crop_path in sorted(crops_dir.glob("*.png")):
        reference_text = _crop_reference_text(crop_path)
        if not REFERENCE_STYLE_KEYWORDS.search(reference_text):
            continue
        references.append(
            {
                "path": crop_path,
                "label": crop_path.stem,
                "text": reference_text,
                "tokens": _tokenize_reference_text(reference_text),
            }
        )
    return references


def _candidate_reference_text(candidate: dict) -> str:
    return " ".join(
        str(candidate.get(key, ""))
        for key in (
            "asset_brief",
            "alt_text",
            "aria_label",
            "label_hint",
            "class_name",
            "id_attr",
            "section_heading",
            "nearby_text",
        )
    )


def _choose_reference_image_for_asset(candidate: dict, asset_plan: dict, references: list[dict]) -> Path | None:
    if not references or asset_plan.get("asset_kind") not in REFERENCE_STYLE_ASSET_KINDS:
        return None
    candidate_text = _candidate_reference_text(candidate)
    if asset_plan.get("asset_kind") != "multi_color_icon" and not REFERENCE_STYLE_KEYWORDS.search(candidate_text):
        return None
    candidate_tokens = _tokenize_reference_text(candidate_text)
    best_reference = max(
        references,
        key=lambda reference: (
            len(candidate_tokens & reference["tokens"]),
            len(reference["tokens"]),
            -len(reference["label"]),
        ),
    )
    return best_reference["path"]


def _asset_generation_skip_reason(candidate: dict, asset_plan: dict | None = None) -> str:
    asset_plan = asset_plan or _build_asset_plan(candidate)
    asset_kind = asset_plan.get("asset_kind", "")
    if asset_kind == "single_color_icon" or _icon_asset_class(candidate) == "single-color-icon":
        return "single-color-icon uses inline Phosphor/currentColor SVG, not image generation"
    if _icon_asset_class(candidate) == "logo/wordmark":
        return "logo/wordmark uses live text or a simple surface-colored block, not image generation"
    return ""


def _choose_chroma_key_color(candidate: dict) -> str:
    text = " ".join(str(value) for value in candidate.values()).lower()
    if re.search(r"\b(green|lime|olive|grass|leaf|leaves|plant|forest|foliage|botanical)\b", text):
        return "#FF00FF"
    return "#00FF00"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    if len(value) != 6:
        raise ValueError(f"Expected 6-digit hex color, got {hex_color!r}")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _remove_chroma_key_background(
    image_path: Path,
    *,
    key_color: str,
    transparent_threshold: float = 28.0,
    opaque_threshold: float = 118.0,
) -> None:
    """Convert a flat chroma-key background to alpha in-place."""
    key_r, key_g, key_b = _hex_to_rgb(key_color)
    with Image.open(image_path) as source:
        rgba = source.convert("RGBA")

    pixels = rgba.load()
    width, height = rgba.size
    threshold_span = max(opaque_threshold - transparent_threshold, 1.0)

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            distance = ((r - key_r) ** 2 + (g - key_g) ** 2 + (b - key_b) ** 2) ** 0.5
            if distance <= transparent_threshold:
                pixels[x, y] = (r, g, b, 0)
                continue
            if distance < opaque_threshold:
                alpha = round(((distance - transparent_threshold) / threshold_span) * a)
            else:
                alpha = a

            if key_color.upper() == "#00FF00" and g > r and g > b:
                g = min(g, round((r + b) / 2))
            elif key_color.upper() == "#FF00FF" and r > g and b > g:
                r = min(r, g)
                b = min(b, g)
            pixels[x, y] = (r, g, b, alpha)

    rgba.save(image_path, format="PNG")


def _build_asset_prompt(
    candidate: dict,
    design_system_markdown: str,
    *,
    transparent_background: bool,
    fallback_background: str | None = None,
    chroma_key_background: str | None = None,
    style_profile: dict | None = None,
    asset_plan: dict | None = None,
    reference_image_path: Path | None = None,
) -> str:
    style_profile = style_profile or _build_asset_style_profile(design_system_markdown)
    asset_plan = asset_plan or _build_asset_plan(candidate, style_profile)

    placement = []
    if candidate.get("asset_brief"):
        placement.append(f"Requested visual brief: {_plain_text(candidate['asset_brief'], 260)}")
    if candidate.get("page_title"):
        placement.append(f"Page title: {_plain_text(candidate['page_title'], 120)}")
    if candidate.get("section_heading"):
        placement.append(f"Section heading: {_plain_text(candidate['section_heading'], 120)}")
    if candidate.get("nearby_text"):
        placement.append(f"Nearby copy: {_plain_text(candidate['nearby_text'], 220)}")
    if candidate.get("label_hint"):
        placement.append(f"Element hint: {_plain_text(candidate['label_hint'], 180)}")
    if candidate.get("target_kind"):
        placement.append(f"Placement type: {candidate['target_kind']}")
    placement.append(f"Target size: {candidate.get('width', 0)}x{candidate.get('height', 0)} px")
    placement.append(f"Target aspect ratio: {asset_plan['aspect_ratio']}")

    if chroma_key_background:
        background_instruction = (
            f"Place the subject on a perfectly flat solid {chroma_key_background} chroma-key background "
            "for local background removal. The background must be one uniform color with no shadows, "
            "gradients, texture, reflections, floor plane, or lighting variation. Keep the subject fully "
            f"separated from the background with crisp edges and generous padding. Do not use {chroma_key_background} "
            "anywhere in the subject. No cast shadow, no contact shadow, and no reflection. The visible artwork "
            "must occupy the target slot width with only minimal safe padding; do not create an extra inset "
            "background plate, thumbnail frame, or second card inside the image."
        )
    elif transparent_background:
        background_instruction = (
            "The asset background must be fully transparent. Return a clean PNG with real alpha, "
            "no frame, no fake white backdrop, and no shadow clipped to a rectangle. The visible artwork "
            "must occupy the target slot width with only minimal safe padding; do not create an extra inset "
            "background plate, thumbnail frame, or second card inside the image."
        )
    else:
        background_instruction = (
            f"Use a flat solid background of exactly {fallback_background}. "
            "The background should blend seamlessly into that section color with no border or frame."
        )

    style_lines = []
    if style_profile.get("system_name"):
        style_lines.append(f"Design system: {style_profile['system_name']}")
    if style_profile.get("description"):
        style_lines.append(f"Overall style: {style_profile['description']}")
    if style_profile.get("palette"):
        style_lines.append("Palette cues: " + "; ".join(style_profile["palette"]))
    for cue in style_profile.get("style_cues", [])[:4]:
        style_lines.append(f"Style cue: {cue}")
    image_cue_limit = 5 if asset_plan["asset_kind"] in {"photographic", "atmospheric_background", "abstract_graphic"} else 3
    for cue in style_profile.get("image_cues", [])[:image_cue_limit]:
        style_lines.append(f"Image/graphics cue: {cue}")
    creative_category = asset_plan.get("creative_category") or "illustrations"
    creative_cues = (style_profile.get("creative_directions") or {}).get(creative_category, [])
    if creative_cues:
        style_lines.append(f"Imagery category: {creative_category}")
        for cue in creative_cues[:6]:
            style_lines.append(f"{creative_category} creative direction: {cue}")
    for cue in style_profile.get("brand_rules", [])[:6]:
        style_lines.append(f"Brand rule: {cue}")
    for cue in style_profile.get("avoid_cues", [])[:5]:
        style_lines.append(f"Do not copy/generalize: {cue}")

    brand_fit_instruction = (
        "Brand-fit requirements: obey the design-system cues as visual law. Match its graphic medium, "
        "surface relationship, edge behavior, color roles, density, depth/shadow level, and allowed accents. "
        "Use the category creative direction for style, density, and simplicity only; derive the subject matter "
        "from the placement context and requested visual brief. "
        "Do not introduce off-palette status colors, glossy/beveled UI, extra frames, stock illustration tropes, "
        "or a different rendering style unless the design system explicitly asks for them."
    )
    if reference_image_path:
        brand_fit_instruction += (
            "\n\nA website screenshot crop is attached as a visual style reference. Use it only for the "
            "graphic/illustration/interface style: line quality, rendering medium, color restraint, density, "
            "edge treatment, and how the artwork sits on the page. Do not copy its literal subject matter. "
            "Generate new content for the requested placement context instead. Preserve the requested aspect "
            f"ratio ({asset_plan['aspect_ratio']}) and keep the entire graphic safely inside the canvas with "
            "all edges visible. Do not crop off any part of the artwork, because this image may be converted "
            "to transparency after generation."
        )

    return (
        "Create exactly one raster image asset for a generated webpage.\n\n"
        f"Asset kind: {asset_plan['asset_kind']}\n"
        f"Imagery category: {asset_plan.get('creative_category', 'illustrations')}\n"
        f"Render medium: {asset_plan['render_medium']}\n"
        f"Goal: {asset_plan['prompt_focus']}\n"
        f"Composition: {asset_plan['composition']}\n\n"
        f"{background_instruction}\n\n"
        f"{brand_fit_instruction}\n\n"
        "Hard constraints: no readable text, no UI chrome, no browser frames, no watermarks, "
        "no stock-photo collage look, and no logos unless the placement explicitly requests a brand mark. "
        "The result must feel like an integrated website asset, not a standalone poster.\n\n"
        "## Placement Context\n"
        + "\n".join(f"- {line}" for line in placement)
        + "\n\n## Targeted Style Context\n"
        + "\n".join(f"- {line}" for line in style_lines)
    )


def _png_has_meaningful_transparency(image_path: Path) -> bool:
    with Image.open(image_path) as img:
        rgba = img.convert("RGBA")
        alpha = rgba.getchannel("A")
        min_alpha, max_alpha = alpha.getextrema()
        return max_alpha > 0 and min_alpha < 250


def _write_png_asset(asset_path: Path, image_bytes: bytes) -> None:
    """Persist provider image bytes as a real PNG, regardless of returned source format."""
    with Image.open(BytesIO(image_bytes)) as image:
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        image.save(asset_path, format="PNG")


def _image_generation_error_is_retryable(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code is None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
    if status_code in {408, 409, 429, 500, 502, 503, 504}:
        return True

    message = str(exc).lower()
    retryable_markers = (
        "server had an error",
        "server_error",
        "rate limit",
        "temporarily",
        "timeout",
        "timed out",
        "overloaded",
        "try again",
        "connection",
        "cancelled",
    )
    return any(marker in message for marker in retryable_markers)


def _generate_image_with_retries(
    provider,
    *,
    prompt: str,
    aspect_ratio: str,
    image_size: str,
    output_mime_type: str,
    transparent_background: bool,
    reference_image_paths: list[Path] | None = None,
    max_attempts: int = 3,
    sleep_seconds: float = 1.0,
) -> tuple[bytes, str]:
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return provider.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                output_mime_type=output_mime_type,
                transparent_background=transparent_background,
                reference_image_paths=reference_image_paths,
            )
        except Exception as exc:
            last_exc = exc
            if attempt >= max_attempts or not _image_generation_error_is_retryable(exc):
                raise
            time.sleep(sleep_seconds * attempt)
    assert last_exc is not None
    raise last_exc


def _inject_asset_scan_script(html_text: str) -> str:
    if "</body>" in html_text:
        return html_text.replace("</body>", ASSET_SCAN_SCRIPT + "\n</body>", 1)
    return html_text + "\n" + ASSET_SCAN_SCRIPT


def _annotate_dom_nodes(html_text: str) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    body = soup.body or soup
    for index, tag in enumerate(body.find_all(True), start=1):
        tag[SCAN_ATTRIBUTE] = f"node-{index:04d}"
    return str(soup)


def _scan_asset_candidates(html_path: Path) -> list[dict]:
    if not Path(CHROME_HEADLESS_PATH).exists():
        raise FileNotFoundError(f"Chrome not found at {CHROME_HEADLESS_PATH}")

    command = [
        CHROME_HEADLESS_PATH,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--allow-file-access-from-files",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=2500",
        "--dump-dom",
        html_path.resolve().as_uri(),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    dumped_soup = BeautifulSoup(result.stdout, "html.parser")
    scan_tag = dumped_soup.find("script", id="stt-asset-scan")
    if scan_tag is None or not scan_tag.string:
        return []
    payload = json.loads(scan_tag.string)
    return payload.get("candidates", [])


def _static_asset_candidates(html_text: str) -> list[dict]:
    """Fallback scanner for explicit asset-brief placeholders when browser dumping returns empty."""
    soup = BeautifulSoup(html_text, "html.parser")
    candidates: list[dict] = []

    for tag in soup.find_all(attrs={SCAN_ATTRIBUTE: True}):
        if not isinstance(tag, Tag):
            continue
        asset_brief = _plain_text(tag.get(ASSET_BRIEF_ATTRIBUTE), 320)
        if not asset_brief:
            continue

        tag_name = (tag.name or "").lower()
        style = tag.get("style") or ""
        if tag_name == "img":
            src = str(tag.get("src") or "").strip()
            if src and not src.startswith("data:"):
                continue
            target_kind = "img"
        elif tag_name == "svg":
            target_kind = "svg"
        elif "url(" in style:
            target_kind = "css_background"
        else:
            continue

        section = tag.find_parent(["section", "article", "header", "footer", "main", "nav", "aside"]) or tag.parent
        heading = ""
        nearby_text = ""
        if isinstance(section, Tag):
            heading_tag = section.find(["h1", "h2", "h3", "h4"])
            heading = _plain_text(heading_tag.get_text(" ") if heading_tag else "", 120)
            nearby_text = _plain_text(section.get_text(" "), 320)

        src_width, src_height = _svg_dimensions_from_data_uri(str(tag.get("src") or ""))
        width = _numeric_attr_or_style(tag, "width", src_width or 1024)
        height = _numeric_attr_or_style(tag, "height", src_height or 1024)
        label_hint = _plain_text(
            " | ".join(
                str(part)
                for part in (
                    tag.get("alt"),
                    asset_brief,
                    tag.get("aria-label"),
                    tag.get("title"),
                    tag.get("role"),
                    tag.get("id"),
                    " ".join(tag.get("class") or []),
                )
                if part
            ),
            240,
        )

        candidates.append(
            {
                "node_id": tag.get(SCAN_ATTRIBUTE),
                "tag_name": tag_name,
                "target_kind": target_kind,
                "width": width,
                "height": height,
                "asset_brief": asset_brief,
                "alt_text": _plain_text(tag.get("alt"), 160),
                "aria_label": _plain_text(tag.get("aria-label"), 160),
                "label_hint": label_hint,
                "class_name": _plain_text(" ".join(tag.get("class") or []), 160),
                "id_attr": _plain_text(tag.get("id"), 120),
                "page_title": _plain_text((soup.title.string if soup.title else ""), 120),
                "section_heading": heading,
                "nearby_text": nearby_text,
                "section_background": "",
                "background_image": "",
                "background_size": "",
                "background_position": "",
                "background_repeat": "",
            }
        )

    return candidates


def _merge_asset_candidates(browser_candidates: list[dict], static_candidates: list[dict]) -> list[dict]:
    """Prefer browser-measured candidates while preserving every explicit static brief."""
    if not browser_candidates:
        return static_candidates
    if not static_candidates:
        return browser_candidates

    browser_by_node = {
        str(candidate.get("node_id")): candidate
        for candidate in browser_candidates
        if candidate.get("node_id")
    }
    merged: list[dict] = []
    seen: set[int] = set()

    for static_candidate in static_candidates:
        node_id = str(static_candidate.get("node_id") or "")
        browser_candidate = browser_by_node.get(node_id)
        if browser_candidate is not None:
            merged.append(browser_candidate)
            seen.add(id(browser_candidate))
        else:
            merged.append(static_candidate)

    for browser_candidate in browser_candidates:
        if id(browser_candidate) not in seen:
            merged.append(browser_candidate)

    return merged


def _strip_scan_attributes(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(attrs={SCAN_ATTRIBUTE: True}):
        del tag[SCAN_ATTRIBUTE]


def _clear_parent_placeholder_background(node: Tag) -> None:
    parent = node.parent
    if not isinstance(parent, Tag):
        return
    parent["style"] = _append_style_declaration(
        parent.get("style"),
        {
            "background": "transparent",
            "background-image": "none",
            "background-color": "transparent",
        },
    )


def _replacement_is_compact_logo_or_icon(replacement: dict) -> bool:
    text = " ".join(
        str(replacement.get(key) or "")
        for key in ("asset_brief", "alt_text", "label_hint", "class_name", "id_attr", "aria_label")
    ).lower()
    width = float(replacement.get("width") or 0)
    height = float(replacement.get("height") or 0)
    compact_slot = bool(height and height <= 72 and (not width or width <= 260))
    named_compact = bool(re.search(r"\b(logo|wordmark|brand|badge|icon|glyph|emblem|mark|partner)\b", text))
    return named_compact and (compact_slot or _classify_asset_kind(replacement) == "brand_or_badge")


def _transparent_asset_style(replacement: dict | None = None) -> dict[str, str]:
    if replacement and _replacement_is_compact_logo_or_icon(replacement):
        return {
            "display": "block",
            "max-width": "100%",
            "height": "100%",
            "width": "auto",
            "object-fit": "contain",
            "opacity": "1",
        }
    return {
        "display": "block",
        "width": "100%",
        "height": "auto",
        "object-fit": "contain",
        "opacity": "1",
    }


def _rewrite_html_with_assets(html_text: str, replacements: list[dict]) -> str:
    soup = BeautifulSoup(html_text, "html.parser")

    for replacement in replacements:
        node = soup.find(attrs={SCAN_ATTRIBUTE: replacement["node_id"]})
        if not isinstance(node, Tag):
            continue
        asset_rel_path = replacement["asset_rel_path"]
        asset_url = replacement.get("asset_url") or asset_rel_path
        alt_text = replacement.get("alt_text") or replacement.get("label_hint") or "Generated site asset"
        target_kind = replacement["target_kind"]

        if target_kind == "img":
            node["src"] = asset_url
            if ASSET_BRIEF_ATTRIBUTE in node.attrs:
                del node.attrs[ASSET_BRIEF_ATTRIBUTE]
            if replacement.get("clear_parent_background"):
                node["style"] = _append_style_declaration(node.get("style"), _transparent_asset_style(replacement))
                _clear_parent_placeholder_background(node)
            else:
                node["style"] = _append_style_declaration(node.get("style"), {"opacity": "1"})
            if alt_text and not node.get("alt"):
                node["alt"] = alt_text
        elif target_kind == "svg":
            replacement_tag = soup.new_tag("img")
            for attr_name in ("class", "style", "role", "aria-label", "aria-hidden", "width", "height"):
                value = node.get(attr_name)
                if value:
                    replacement_tag[attr_name] = value
            if "width" not in replacement_tag and replacement.get("width"):
                replacement_tag["width"] = str(replacement["width"])
            if "height" not in replacement_tag and replacement.get("height"):
                replacement_tag["height"] = str(replacement["height"])
            replacement_tag["src"] = asset_url
            replacement_tag["alt"] = alt_text
            if ASSET_BRIEF_ATTRIBUTE in replacement_tag.attrs:
                del replacement_tag.attrs[ASSET_BRIEF_ATTRIBUTE]
            node.replace_with(replacement_tag)
            if replacement.get("clear_parent_background"):
                replacement_tag["style"] = _append_style_declaration(replacement_tag.get("style"), _transparent_asset_style(replacement))
                _clear_parent_placeholder_background(replacement_tag)
            else:
                replacement_tag["style"] = _append_style_declaration(replacement_tag.get("style"), {"opacity": "1"})
        elif target_kind == "css_background":
            if ASSET_BRIEF_ATTRIBUTE in node.attrs:
                del node.attrs[ASSET_BRIEF_ATTRIBUTE]
            background_image = replacement.get("background_image") or f"url('{asset_url}')"
            rewritten_bg = re.sub(
                r"url\((?:[^)(]+|\([^)(]*\))*\)",
                f"url('{asset_url}')",
                background_image,
            )
            node["style"] = _append_style_declaration(
                node.get("style"),
                {
                    "background-image": rewritten_bg,
                    "background-size": replacement.get("background_size") or "cover",
                    "background-position": replacement.get("background_position") or "center",
                    "background-repeat": replacement.get("background_repeat") or "no-repeat",
                },
            )

    _strip_scan_attributes(soup)
    return str(soup)


def _write_asset_manifest(
    asset_manifest_path: Path,
    *,
    status: str,
    model_name: str,
    html_path: Path,
    replacements: list[dict],
    manifest_candidates: list[dict],
) -> None:
    payload = {
        "status": status,
        "model": model_name,
        "html": str(html_path),
        "generated_count": len(replacements),
        "candidates": manifest_candidates,
    }
    asset_manifest_path.write_text(json.dumps(payload, indent=2) + "\n")


def apply_generated_site_assets(
    html_path: Path,
    design_system_markdown: str,
    config: AppConfig,
    source_crops_dir: Path | None = None,
) -> dict:
    """Generate custom site assets and rewrite the HTML in place."""
    if not getattr(config, "site_asset_generation_enabled", True):
        return {"status": "disabled", "candidates": []}

    html_text = html_path.read_text(errors="ignore")
    annotated_html = _annotate_dom_nodes(html_text)
    asset_manifest_path = html_path.with_suffix(".assets.json")

    with tempfile.TemporaryDirectory(prefix="stt-asset-scan-") as temp_dir:
        scan_html_path = Path(temp_dir) / "scan.html"
        scan_html_path.write_text(_inject_asset_scan_script(annotated_html))
        try:
            candidates = _scan_asset_candidates(scan_html_path)
            static_candidates = _static_asset_candidates(annotated_html)
            candidates = _merge_asset_candidates(candidates, static_candidates)
        except Exception as exc:
            candidates = _static_asset_candidates(annotated_html)
            if not candidates:
                payload = {"status": "scan_error", "error": str(exc), "candidates": []}
                asset_manifest_path.write_text(json.dumps(payload, indent=2) + "\n")
                return payload

    if not candidates:
        candidates = _static_asset_candidates(annotated_html)

    if not candidates:
        payload = {"status": "no_candidates", "candidates": []}
        asset_manifest_path.write_text(json.dumps(payload, indent=2) + "\n")
        return payload

    model_name = getattr(config, "site_asset_image_model", "") or DEFAULT_SITE_ASSET_IMAGE_MODEL
    try:
        provider = _image_provider_for_model(model_name)
    except Exception as exc:
        payload = {"status": "provider_error", "error": str(exc), "candidates": candidates}
        asset_manifest_path.write_text(json.dumps(payload, indent=2) + "\n")
        return payload

    asset_dir = html_path.parent / "generated-assets" / _safe_slug(html_path.stem)
    asset_dir.mkdir(parents=True, exist_ok=True)
    existing_indexes = []
    for existing_asset in asset_dir.glob("asset-*.png"):
        match = re.fullmatch(r"asset-(\d+)\.png", existing_asset.name)
        if match:
            existing_indexes.append(int(match.group(1)))
    next_asset_index = (max(existing_indexes) + 1) if existing_indexes else 1

    style_profile = _build_asset_style_profile(design_system_markdown)
    reference_images = _collect_graphic_reference_images(source_crops_dir or (html_path.parent / "crops"))
    replacements: list[dict] = []
    manifest_candidates: list[dict] = []
    _write_asset_manifest(
        asset_manifest_path,
        status="in_progress",
        model_name=model_name,
        html_path=html_path,
        replacements=replacements,
        manifest_candidates=manifest_candidates,
    )
    for index, candidate in enumerate(candidates, start=1):
        candidate_record = dict(candidate)
        candidate_record["status"] = "pending"
        candidate_record["asset_path"] = ""
        candidate_record["fallback_used"] = False
        manifest_candidates.append(candidate_record)

        supports_transparency = getattr(provider, "supports_transparent_image_background", lambda: True)()
        asset_plan = _build_asset_plan(candidate, style_profile)
        reference_image_path = _choose_reference_image_for_asset(candidate, asset_plan, reference_images)
        candidate_record["asset_plan"] = asset_plan
        candidate_record["reference_image_path"] = (
            str(reference_image_path.relative_to(html_path.parent))
            if reference_image_path and reference_image_path.is_relative_to(html_path.parent)
            else str(reference_image_path or "")
        )
        skip_reason = _asset_generation_skip_reason(candidate, asset_plan)
        if skip_reason:
            candidate_record["status"] = "skipped"
            candidate_record["skip_reason"] = skip_reason
            _write_asset_manifest(
                asset_manifest_path,
                status="in_progress",
                model_name=model_name,
                html_path=html_path,
                replacements=replacements,
                manifest_candidates=manifest_candidates,
            )
            continue
        if asset_plan.get("asset_kind") == "multi_color_icon" and not reference_image_path:
            candidate_record["status"] = "error"
            candidate_record["error"] = "multi-color-icon requires a source reference image"
            _write_asset_manifest(
                asset_manifest_path,
                status="in_progress",
                model_name=model_name,
                html_path=html_path,
                replacements=replacements,
                manifest_candidates=manifest_candidates,
            )
            continue
        should_have_transparency = _asset_should_have_transparent_background(candidate, asset_plan)
        native_transparency = should_have_transparency and supports_transparency
        chroma_key_background = None if native_transparency or not should_have_transparency else _choose_chroma_key_color(candidate)
        prompt = _build_asset_prompt(
            candidate,
            design_system_markdown,
            transparent_background=native_transparency,
            fallback_background=candidate.get("section_background"),
            chroma_key_background=chroma_key_background,
            style_profile=style_profile,
            asset_plan=asset_plan,
            reference_image_path=reference_image_path,
        )
        aspect_ratio = _choose_aspect_ratio(candidate.get("width", 1024), candidate.get("height", 1024))
        image_size = _choose_image_size(candidate.get("width", 1024), candidate.get("height", 1024))
        candidate_record["prompt"] = prompt
        candidate_record["fallback_prompt"] = ""
        candidate_record["aspect_ratio"] = aspect_ratio
        candidate_record["image_size"] = image_size
        candidate_record["transparent_background_requested"] = should_have_transparency
        candidate_record["native_transparency_requested"] = native_transparency
        candidate_record["chroma_key_background"] = chroma_key_background or ""
        candidate_record["background_removed"] = False

        try:
            image_bytes, _ = _generate_image_with_retries(
                provider,
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                output_mime_type="image/png",
                transparent_background=native_transparency,
                reference_image_paths=[reference_image_path] if reference_image_path else None,
            )
            asset_path = asset_dir / f"asset-{next_asset_index + index - 1:03d}.png"
            _write_png_asset(asset_path, image_bytes)

            if chroma_key_background:
                _remove_chroma_key_background(asset_path, key_color=chroma_key_background)
                candidate_record["background_removed"] = _png_has_meaningful_transparency(asset_path)

            if should_have_transparency and not _png_has_meaningful_transparency(asset_path) and candidate.get("section_background"):
                fallback_prompt = _build_asset_prompt(
                    candidate,
                    design_system_markdown,
                    transparent_background=False,
                    fallback_background=candidate["section_background"],
                    style_profile=style_profile,
                    asset_plan=asset_plan,
                    reference_image_path=reference_image_path,
                )
                candidate_record["fallback_prompt"] = fallback_prompt
                fallback_bytes, _ = _generate_image_with_retries(
                    provider,
                    prompt=fallback_prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                    output_mime_type="image/png",
                    transparent_background=False,
                    reference_image_paths=[reference_image_path] if reference_image_path else None,
                )
                _write_png_asset(asset_path, fallback_bytes)
                candidate_record["fallback_used"] = True

            asset_rel_path = str(asset_path.relative_to(html_path.parent))
            asset_url = f"{asset_rel_path}?v={asset_path.stat().st_mtime_ns}"
            candidate_record["status"] = "generated"
            candidate_record["asset_path"] = asset_rel_path
            replacements.append(
                {
                    **candidate,
                    "asset_rel_path": asset_rel_path,
                    "asset_url": asset_url,
                    "clear_parent_background": should_have_transparency,
                }
            )
            html_path.write_text(_rewrite_html_with_assets(annotated_html, replacements))
        except Exception as exc:
            candidate_record["status"] = "error"
            candidate_record["error"] = str(exc)
        _write_asset_manifest(
            asset_manifest_path,
            status="in_progress",
            model_name=model_name,
            html_path=html_path,
            replacements=replacements,
            manifest_candidates=manifest_candidates,
        )

    rewritten_html = _rewrite_html_with_assets(annotated_html, replacements)
    html_path.write_text(rewritten_html)
    _write_asset_manifest(
        asset_manifest_path,
        status="completed",
        model_name=model_name,
        html_path=html_path,
        replacements=replacements,
        manifest_candidates=manifest_candidates,
    )
    payload = json.loads(asset_manifest_path.read_text())
    return payload


__all__ = [
    "ASSET_BRIEF_ATTRIBUTE",
    "DEFAULT_SITE_ASSET_IMAGE_MODEL",
    "apply_generated_site_assets",
    "_build_asset_plan",
    "_build_asset_prompt",
    "_build_asset_style_profile",
    "_asset_should_have_transparent_background",
    "_choose_chroma_key_color",
    "_remove_chroma_key_background",
    "_png_has_meaningful_transparency",
    "_write_png_asset",
    "_clear_parent_placeholder_background",
    "_rewrite_html_with_assets",
    "_merge_asset_candidates",
    "_generate_image_with_retries",
]
