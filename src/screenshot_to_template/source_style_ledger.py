"""Build and apply a generation-facing source style ledger."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .source_colors import (
    DECLARATION_RE,
    GRADIENT_RE,
    HEX_RE,
    HSL_RE,
    RGB_RE,
    STYLE_ATTR_RE,
    TYPOGRAPHY_PROPERTIES,
    _extract_css_segments,
    _parse_css_color_literal,
    _rgba_to_lab,
    _lab_distance,
    collect_allowed_source_color_literals,
    extract_document_color_literals,
    find_non_source_document_font_families,
    normalize_color_literal,
    normalize_font_family_literal,
)


CLOSE_COLOR_DISTANCE_THRESHOLD = 14.0

COLOR_PROPERTIES = {
    "color",
    "background",
    "background-color",
    "border",
    "border-color",
    "border-top-color",
    "border-right-color",
    "border-bottom-color",
    "border-left-color",
    "outline",
    "outline-color",
    "box-shadow",
    "text-shadow",
    "fill",
    "stroke",
}

ROLE_FAMILIES = {
    "surface",
    "text",
    "border",
    "action_fill",
    "icon",
    "shadow",
    "scrim",
}

ROLE_SELECTOR_HINTS = {
    "action_fill": ("button", ".btn", "cta", "submit", "link-button", "primary"),
    "surface": ("card", "tile", "panel", "tray", "surface", "section", "main", "body"),
    "text": ("text", "copy", "body", "headline", "heading", "title", "label", "eyebrow"),
    "border": ("border", "divider", "rule", "stroke"),
    "icon": ("icon", "svg"),
    "shadow": ("shadow",),
    "scrim": ("scrim", "overlay", "backdrop", "veil"),
}


def _strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _split_selector_list(selector: str) -> list[str]:
    selectors = []
    for item in selector.split(","):
        item = re.sub(r"\s+", " ", item).strip()
        if item:
            selectors.append(item)
    return selectors or [selector.strip()]


def _iter_css_rules(css: str) -> list[tuple[str, str]]:
    """Return best-effort (selector, body) pairs without attempting cascade."""
    css = _strip_css_comments(css)
    rules: list[tuple[str, str]] = []
    cursor = 0
    length = len(css)
    while cursor < length:
        open_index = css.find("{", cursor)
        if open_index < 0:
            break

        selector_start = css.rfind("}", cursor, open_index)
        selector_start = cursor if selector_start < cursor else selector_start + 1
        selector = re.sub(r"\s+", " ", css[selector_start:open_index]).strip()

        depth = 1
        index = open_index + 1
        while index < length and depth:
            char = css[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1
        if depth:
            break

        body = css[open_index + 1 : index - 1].strip()
        cursor = index
        if not selector or not body:
            continue
        lowered_selector = selector.lower()
        if lowered_selector.startswith(("@media", "@supports", "@container", "@layer")):
            rules.extend(_iter_css_rules(body))
            continue
        if lowered_selector.startswith(("@font-face", "@keyframes", "@property")):
            continue
        if "{" in body or "}" in body:
            continue
        rules.append((selector, body))
    return rules


def _extract_value_color_literals(value: str) -> list[str]:
    literals: list[str] = []
    literals.extend(normalize_color_literal(match) for match in HEX_RE.findall(value))
    literals.extend(normalize_color_literal(match) for match in RGB_RE.findall(value))
    literals.extend(normalize_color_literal(match) for match in HSL_RE.findall(value))
    if re.search(r"\btransparent\b", value, re.IGNORECASE):
        literals.append("transparent")
    for match in GRADIENT_RE.finditer(value):
        literals.append(re.sub(r"\s+", " ", match.group(0).strip()))
    return list(dict.fromkeys(literals))


def _kind_for_value(value: str, property_name: str, parsed: tuple[float, float, float, float] | None) -> str:
    lowered_value = value.lower()
    lowered_property = property_name.lower()
    if GRADIENT_RE.search(value):
        return "gradient"
    if lowered_property in {"box-shadow", "text-shadow"}:
        return "shadow"
    if "scrim" in lowered_value or "overlay" in lowered_value:
        return "scrim"
    if parsed is not None and parsed[3] < 1.0:
        return "alpha_overlay"
    if "transparent" in lowered_value:
        return "alpha_overlay"
    if "border" in lowered_property or "outline" in lowered_property or lowered_property in {"stroke"}:
        return "border"
    return "solid"


def _selector_role_hints(selector: str) -> set[str]:
    lowered = selector.lower()
    roles: set[str] = set()
    for role, hints in ROLE_SELECTOR_HINTS.items():
        if any(hint in lowered for hint in hints):
            roles.add(role)
    if re.search(r"\bh[1-6]\b|\.h[1-6]\b", lowered):
        roles.add("text")
    if re.search(r"\bnav\b|header|menu", lowered):
        roles.add("surface")
        roles.add("text")
    if "footer" in lowered or "legal" in lowered:
        roles.add("surface")
        roles.add("text")
    return roles


def _property_role_hints(property_name: str) -> set[str]:
    prop = property_name.lower()
    if prop == "color":
        return {"text"}
    if prop in {"fill", "stroke"}:
        return {"icon"}
    if prop in {"background", "background-color"}:
        return {"surface"}
    if "border" in prop or "outline" in prop:
        return {"border"}
    if "shadow" in prop:
        return {"shadow"}
    return set()


def _infer_role_families(selector: str, property_name: str, value: str) -> set[str]:
    roles = _property_role_hints(property_name)
    selector_roles = _selector_role_hints(selector)
    prop = property_name.lower()
    if prop in {"background", "background-color"} and "action_fill" in selector_roles:
        roles.add("action_fill")
        roles.discard("surface")
    roles |= selector_roles & {"scrim", "shadow", "border", "icon"}
    if not roles:
        roles = selector_roles & ROLE_FAMILIES
    if "overlay" in selector.lower() or "scrim" in selector.lower() or "backdrop" in selector.lower():
        roles.add("scrim")
    if not roles and prop in {"background", "background-color"}:
        return {"surface"}
    return roles


def _confidence(frequency: int, selectors: set[str], properties: set[str], aliases: set[str]) -> str:
    strong_selector = any(
        any(hint in selector.lower() for hint in ("button", "btn", "cta", "card", "nav", "footer", "body", "h1", "heading"))
        for selector in selectors
    )
    if aliases and frequency >= 2:
        return "high"
    if strong_selector and frequency >= 2 and len(properties) >= 1:
        return "high"
    if frequency >= 2 or strong_selector or aliases:
        return "medium"
    return "low"


def _is_unresolved_color(value: str) -> bool:
    lowered = value.lower()
    return "var(" in lowered or "<alpha-value>" in lowered or "color-mix(" in lowered


def _is_parseable_generation_value(value: str, kind: str) -> bool:
    if kind == "gradient":
        return bool(GRADIENT_RE.search(value)) and not _is_unresolved_color(value)
    if kind in {"shadow", "scrim"}:
        return not _is_unresolved_color(value)
    return _parse_css_color_literal(value) is not None


def extract_source_style_declarations(extracted: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract selector/property/value contexts from the source HTML."""
    source_html = extracted.get("source_html")
    if not isinstance(source_html, str) or not source_html:
        return []
    source_path = Path(source_html)
    if not source_path.exists():
        return []

    html = source_path.read_text(errors="ignore")
    css_segments, _, _ = _extract_css_segments(html, source_path)
    declarations: list[dict[str, Any]] = []

    for css_text, _base_url in css_segments:
        for selector_text, body in _iter_css_rules(css_text):
            selectors = _split_selector_list(selector_text)
            for property_name, raw_value in DECLARATION_RE.findall(body):
                property_name = property_name.strip().lower()
                value = re.sub(r"\s+", " ", raw_value.strip())
                if not value:
                    continue
                for selector in selectors:
                    if property_name.startswith("--"):
                        color_literals = _extract_value_color_literals(value)
                        if color_literals:
                            for literal in color_literals:
                                declarations.append(
                                    {
                                        "selector": selector,
                                        "property": property_name,
                                        "value": literal,
                                        "raw_value": value,
                                        "custom_property": property_name,
                                        "kind": _kind_for_value(literal, property_name, _parse_css_color_literal(literal)),
                                        "evidence_source": "custom_property",
                                    }
                                )
                        continue
                    if property_name in COLOR_PROPERTIES or any(token in property_name for token in ("color", "shadow")):
                        literals = _extract_value_color_literals(value)
                        for literal in literals:
                            declarations.append(
                                {
                                    "selector": selector,
                                    "property": property_name,
                                    "value": literal,
                                    "raw_value": value,
                                    "custom_property": None,
                                    "kind": _kind_for_value(literal, property_name, _parse_css_color_literal(literal)),
                                    "evidence_source": "css_declaration",
                                }
                            )
                    if property_name in TYPOGRAPHY_PROPERTIES:
                        declarations.append(
                            {
                                "selector": selector,
                                "property": property_name,
                                "value": value,
                                "raw_value": value,
                                "custom_property": None,
                                "kind": "typography",
                                "evidence_source": "css_declaration",
                            }
                        )

    for inline_index, match in enumerate(STYLE_ATTR_RE.finditer(html), start=1):
        style_text = match.group(2)
        selector = f"[inline-style-{inline_index}]"
        for property_name, raw_value in DECLARATION_RE.findall(style_text):
            property_name = property_name.strip().lower()
            value = re.sub(r"\s+", " ", raw_value.strip())
            if property_name in COLOR_PROPERTIES or any(token in property_name for token in ("color", "shadow")):
                for literal in _extract_value_color_literals(value):
                    declarations.append(
                        {
                            "selector": selector,
                            "property": property_name,
                            "value": literal,
                            "raw_value": value,
                            "custom_property": None,
                            "kind": _kind_for_value(literal, property_name, _parse_css_color_literal(literal)),
                            "evidence_source": "inline_style",
                        }
                    )
            if property_name in TYPOGRAPHY_PROPERTIES:
                declarations.append(
                    {
                        "selector": selector,
                        "property": property_name,
                        "value": value,
                        "raw_value": value,
                        "custom_property": None,
                        "kind": "typography",
                        "evidence_source": "inline_style",
                    }
                )

    return declarations


def _append_unique(values: list[Any], value: Any, limit: int = 8) -> None:
    if value in values:
        return
    if len(values) < limit:
        values.append(value)


def _ledger_role_name(role_family: str, value: str) -> str:
    suffix = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")[:32] or "value"
    return f"{role_family}_{suffix}"


def build_source_style_ledger(extracted: dict[str, Any]) -> dict[str, Any]:
    """Build a role-oriented source-style ledger from extracted source styles."""
    declarations = extract_source_style_declarations(extracted)
    raw_values = sorted(collect_allowed_source_color_literals(extracted))

    color_usage: dict[str, dict[str, Any]] = {}
    excluded_values: list[dict[str, Any]] = []
    for declaration in declarations:
        if declaration.get("kind") == "typography":
            continue
        value = normalize_color_literal(str(declaration.get("value", "")).strip())
        if not value:
            continue
        entry = color_usage.setdefault(
            value,
            {
                "value": value,
                "frequency": 0,
                "selectors": [],
                "properties": [],
                "aliases": [],
                "role_families": set(),
                "kinds": set(),
                "evidence_sources": set(),
            },
        )
        entry["frequency"] += 1
        _append_unique(entry["selectors"], declaration.get("selector", ""))
        _append_unique(entry["properties"], declaration.get("property", ""))
        if declaration.get("custom_property"):
            _append_unique(entry["aliases"], declaration["custom_property"])
        entry["role_families"].update(
            _infer_role_families(
                str(declaration.get("selector", "")),
                str(declaration.get("property", "")),
                value,
            )
        )
        entry["kinds"].add(declaration.get("kind") or "solid")
        entry["evidence_sources"].add(declaration.get("evidence_source") or "css_declaration")

    for value in raw_values:
        color_usage.setdefault(
            value,
            {
                "value": value,
                "frequency": 1,
                "selectors": [],
                "properties": [],
                "aliases": [],
                "role_families": set(),
                "kinds": {"solid"},
                "evidence_sources": {"raw_extraction"},
            },
        )

    generation_palette: list[dict[str, Any]] = []
    role_entries: dict[str, dict[str, Any]] = {}
    for value, entry in sorted(color_usage.items(), key=lambda item: (-item[1]["frequency"], item[0])):
        role_families = sorted(entry["role_families"] & ROLE_FAMILIES)
        kinds = sorted(entry["kinds"])
        kind = kinds[0] if kinds else "solid"
        parseable = _is_parseable_generation_value(value, kind)
        generation_safe: bool | str = bool(parseable and role_families)
        if not parseable:
            reason = "unresolved_variable_color" if _is_unresolved_color(value) else "parse_failed"
            excluded_values.append({"value": value, "excluded_reason": reason, "kind": kind})
        elif not role_families:
            excluded_values.append({"value": value, "excluded_reason": "no_role_evidence", "kind": kind})

        evidence = {
            "frequency": entry["frequency"],
            "selectors": entry["selectors"],
            "properties": entry["properties"],
            "evidence_sources": sorted(entry["evidence_sources"]),
        }
        confidence = _confidence(
            int(entry["frequency"]),
            set(entry["selectors"]),
            set(entry["properties"]),
            set(entry["aliases"]),
        )
        palette_entry = {
            "value": value,
            "kind": kind,
            "generation_safe": generation_safe,
            "role_families": role_families,
            "aliases": entry["aliases"],
            "evidence": evidence,
            "confidence": confidence,
        }
        if generation_safe:
            generation_palette.append(palette_entry)
            for role in role_families:
                role_name = _ledger_role_name(role, value)
                role_entries.setdefault(
                    role_name,
                    {
                        "value": value,
                        "kind": kind,
                        "generation_safe": True,
                        "aliases": entry["aliases"],
                        "evidence": evidence,
                        "confidence": confidence,
                    },
                )

    typography_roles = _build_typography_roles(extracted, declarations)
    component_hints = _build_component_hints(generation_palette)

    return {
        "schema_version": "source_style_ledger.v1",
        "type": "source_style_ledger",
        "source": {
            "html_path": extracted.get("source_html", ""),
            "extraction": {
                "style_blocks": int(extracted.get("style_block_count") or 0),
                "inline_styles": int(extracted.get("inline_style_count") or 0),
                "declaration_contexts": len(declarations),
            },
        },
        "palette": {
            "raw_values": raw_values,
            "generation_palette": generation_palette,
            "roles": role_entries,
        },
        "typography": {"roles": typography_roles},
        "component_hints": component_hints,
        "computed_evidence": [],
        "audit": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "excluded_values": excluded_values,
            "notes": [
                "Parser-based ledger; browser-computed cascade evidence is reserved for a later pass.",
                "Generation palette excludes unparsable or unresolved CSS variable colors.",
            ],
        },
    }


def _build_typography_roles(extracted: dict[str, Any], declarations: list[dict[str, Any]]) -> dict[str, Any]:
    selector_counts: dict[str, Counter[str]] = defaultdict(Counter)
    selector_examples: dict[str, list[str]] = defaultdict(list)
    for declaration in declarations:
        if declaration.get("kind") != "typography" or declaration.get("property") != "font-family":
            continue
        selector = str(declaration.get("selector", ""))
        value = str(declaration.get("value", "")).strip()
        if not value or value.lower().startswith("var("):
            continue
        lowered = selector.lower()
        role = "unknown"
        if re.search(r"\bbody\b|\bp\b|html", lowered):
            role = "body"
        elif re.search(r"\bh[1-6]\b|heading|title|display|hero", lowered):
            role = "heading"
        elif re.search(r"button|btn|label|eyebrow|badge|chip|nav|menu", lowered):
            role = "label"
        selector_counts[role][value] += 1
        _append_unique(selector_examples[role], selector)

    body_stack = extracted.get("source_font_stack")
    heading_stack = extracted.get("source_heading_font_stack")
    if isinstance(body_stack, str) and body_stack.strip():
        selector_counts["body"][body_stack.strip()] += 5
    if isinstance(heading_stack, str) and heading_stack.strip():
        selector_counts["display"][heading_stack.strip()] += 5
        selector_counts["heading"][heading_stack.strip()] += 3

    font_faces_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for face in extracted.get("font_faces", []):
        family = face.get("font_family") if isinstance(face, dict) else None
        if isinstance(family, str) and family.strip():
            font_faces_by_family[normalize_font_family_literal(family)].append(face)

    roles: dict[str, Any] = {}
    for role in ("body", "heading", "display", "label", "decorative", "unknown"):
        stack = ""
        count = 0
        if selector_counts[role]:
            stack, count = selector_counts[role].most_common(1)[0]
        family_key = normalize_font_family_literal(stack.split(",", 1)[0]) if stack else ""
        roles[role] = {
            "stack": stack,
            "font_faces": font_faces_by_family.get(family_key, []),
            "generation_safe": bool(stack),
            "evidence": {
                "frequency": count,
                "selectors": selector_examples.get(role, []),
                "evidence_sources": ["source_font_stack"] if role in {"body", "heading", "display"} and stack else [],
            },
            "confidence": "medium" if stack else "low",
        }
    return roles


def _build_component_hints(generation_palette: list[dict[str, Any]]) -> dict[str, Any]:
    hints = {
        "button": {"background_candidates": [], "text_candidates": [], "border_candidates": []},
        "card": {"surface_candidates": [], "text_candidates": []},
        "navigation": {"surface_candidates": [], "text_candidates": []},
        "footer": {"surface_candidates": [], "text_candidates": []},
    }
    for entry in generation_palette:
        value = entry["value"]
        roles = set(entry.get("role_families") or [])
        selectors = " ".join(entry.get("evidence", {}).get("selectors", [])).lower()
        if "action_fill" in roles:
            _append_unique(hints["button"]["background_candidates"], value)
        if "text" in roles and any(token in selectors for token in ("button", "btn", "cta")):
            _append_unique(hints["button"]["text_candidates"], value)
        if "border" in roles and any(token in selectors for token in ("button", "btn", "cta")):
            _append_unique(hints["button"]["border_candidates"], value)
        if "surface" in roles and any(token in selectors for token in ("card", "tile", "panel", "tray")):
            _append_unique(hints["card"]["surface_candidates"], value)
        if "text" in roles and any(token in selectors for token in ("card", "tile", "panel", "tray")):
            _append_unique(hints["card"]["text_candidates"], value)
        if any(token in selectors for token in ("nav", "header", "menu")):
            key = "surface_candidates" if "surface" in roles else "text_candidates" if "text" in roles else ""
            if key:
                _append_unique(hints["navigation"][key], value)
        if any(token in selectors for token in ("footer", "legal")):
            key = "surface_candidates" if "surface" in roles else "text_candidates" if "text" in roles else ""
            if key:
                _append_unique(hints["footer"][key], value)
    return hints


def write_source_style_ledger_artifact(output_dir: str | Path, ledger: dict[str, Any]) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "source-style-ledger.yaml"
    path.write_text(yaml.safe_dump(ledger, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return path


def source_style_ledger_prompt_block(ledger: dict[str, Any], max_chars: int = 24000) -> str:
    """Return a concise YAML block suitable for model prompts."""
    if not ledger:
        return ""
    prompt_ledger = {
        "schema_version": ledger.get("schema_version"),
        "type": ledger.get("type"),
        "palette": {
            "generation_palette": ledger.get("palette", {}).get("generation_palette", [])[:48],
            "roles": dict(list((ledger.get("palette", {}).get("roles") or {}).items())[:40]),
        },
        "typography": ledger.get("typography", {}),
        "component_hints": ledger.get("component_hints", {}),
        "audit": {
            "excluded_values_count": len(ledger.get("audit", {}).get("excluded_values", []) or []),
            "notes": ledger.get("audit", {}).get("notes", []),
        },
    }
    text = yaml.safe_dump(prompt_ledger, sort_keys=False, allow_unicode=False)
    return text[:max_chars].rstrip()


def _generation_palette_entries(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in ledger.get("palette", {}).get("generation_palette", []) or []
        if isinstance(entry, dict) and entry.get("generation_safe")
    ]


def generation_safe_color_literals(ledger: dict[str, Any]) -> set[str]:
    values = set()
    for entry in _generation_palette_entries(ledger):
        value = entry.get("value")
        if isinstance(value, str) and value.strip():
            values.add(normalize_color_literal(value))
    return values


def _infer_document_role(text: str, literal: str) -> str | None:
    lines = text.splitlines()
    literal_lower = literal.lower()
    for line in lines:
        if literal_lower not in line.lower():
            continue
        lowered = line.lower()
        if "shadow" in lowered:
            return "shadow"
        if "border" in lowered or "outline" in lowered or "divider" in lowered:
            return "border"
        if any(token in lowered for token in ("button", "cta", "action", "primary fill", "background/fill")):
            return "action_fill"
        if any(token in lowered for token in ("background", "surface", "canvas", "card", "panel", "fill")):
            return "surface"
        if any(token in lowered for token in ("text", "heading", "body", "copy", "foreground", "color")):
            return "text"
    return None


def _role_compatible(entry: dict[str, Any], role: str | None) -> bool:
    if not role:
        return True
    roles = set(entry.get("role_families") or [])
    if role == "action_fill" and "action_fill" in roles:
        return True
    return role in roles


def audit_document_styles(
    text: str,
    extracted: dict[str, Any],
    ledger: dict[str, Any],
    allowed_approximate_literals: set[str] | None = None,
) -> dict[str, Any]:
    """Audit a generated document against the ledger generation palette."""
    safe = generation_safe_color_literals(ledger)
    raw_source = {normalize_color_literal(value) for value in collect_allowed_source_color_literals(extracted)}
    allowed_approximate_literals = allowed_approximate_literals or set()
    document_literals = [normalize_color_literal(value) for value in extract_document_color_literals(text)]
    unsupported: set[str] = set()
    raw_source_not_generation_safe: set[str] = set()
    approximate_retained: set[str] = set()
    for literal in document_literals:
        if literal in safe:
            continue
        if literal in allowed_approximate_literals:
            approximate_retained.add(literal)
        elif literal in raw_source:
            raw_source_not_generation_safe.add(literal)
            unsupported.add(literal)
        else:
            unsupported.add(literal)

    role_mismatch_warnings = []
    palette_by_value = {normalize_color_literal(entry["value"]): entry for entry in _generation_palette_entries(ledger)}
    for literal in sorted(set(document_literals)):
        entry = palette_by_value.get(literal)
        if not entry:
            continue
        role = _infer_document_role(text, literal)
        if role and not _role_compatible(entry, role):
            role_mismatch_warnings.append(
                {
                    "value": literal,
                    "document_role": role,
                    "ledger_role_families": entry.get("role_families", []),
                    "warning": "source-backed value appears in a suspicious role context",
                }
            )

    return {
        "unsupported_colors": sorted(unsupported),
        "unsupported_color_count": len(unsupported),
        "unsupported_fonts": find_non_source_document_font_families(text, extracted),
        "raw_source_but_not_generation_safe": sorted(raw_source_not_generation_safe),
        "retained_approximate_values": sorted(approximate_retained),
        "role_mismatch_warnings": role_mismatch_warnings,
    }


def reconcile_document_styles(
    text: str,
    extracted: dict[str, Any],
    ledger: dict[str, Any],
    allowed_approximate_literals: set[str] | None = None,
    close_match_threshold: float = CLOSE_COLOR_DISTANCE_THRESHOLD,
) -> tuple[str, dict[str, Any]]:
    """Deterministically replace unsupported colors when a close ledger match exists."""
    before = audit_document_styles(text, extracted, ledger, allowed_approximate_literals)
    candidates = []
    for entry in _generation_palette_entries(ledger):
        value = normalize_color_literal(str(entry.get("value", "")))
        parsed = _parse_css_color_literal(value)
        if parsed is None:
            continue
        candidates.append(
            {
                "value": value,
                "lab": _rgba_to_lab(parsed),
                "role_families": entry.get("role_families", []),
                "frequency": entry.get("evidence", {}).get("frequency", 0),
            }
        )

    replacements: dict[str, str] = {}
    replaced_records = []
    retained_records = []
    unresolved_records = []
    allowed_approximate_literals = allowed_approximate_literals or set()

    for literal in before["unsupported_colors"]:
        parsed = _parse_css_color_literal(literal)
        role = _infer_document_role(text, literal)
        if parsed is None:
            unresolved_records.append({"value": literal, "role": role, "reason": "unparseable_document_color"})
            continue
        source_lab = _rgba_to_lab(parsed)
        compatible = [candidate for candidate in candidates if _role_compatible(candidate, role)]
        search_space = compatible or candidates
        if not search_space:
            unresolved_records.append({"value": literal, "role": role, "reason": "no_generation_palette_candidates"})
            continue
        best = min(
            search_space,
            key=lambda candidate: (
                round(_lab_distance(source_lab, candidate["lab"]), 6),
                -int(candidate.get("frequency") or 0),
                candidate["value"],
            ),
        )
        distance = _lab_distance(source_lab, best["lab"])
        record = {
            "value": literal,
            "role": role,
            "candidate": best["value"],
            "candidate_role_families": best.get("role_families", []),
            "perceptual_distance": round(distance, 3),
            "threshold": close_match_threshold,
            "role_unknown": role is None,
        }
        if distance <= close_match_threshold and (compatible or role is None):
            replacements[literal] = best["value"]
            replaced_records.append(record)
        elif literal in allowed_approximate_literals:
            retained_records.append({**record, "reason": "grounding_approximate_allowed"})
        else:
            unresolved_records.append({**record, "reason": "no_close_role_compatible_match"})

    reconciled = _apply_literal_replacements(text, replacements)
    after = audit_document_styles(reconciled, extracted, ledger, allowed_approximate_literals)
    audit = {
        "close_match_threshold": close_match_threshold,
        "before": before,
        "after": after,
        "replaced_with_close_source_match": replaced_records,
        "retained_approximate_no_close_source_match": retained_records,
        "unresolved_no_role_compatible_match": unresolved_records,
        "replacement_count": len(replacements),
    }
    return reconciled, audit


def _apply_literal_replacements(text: str, replacements: dict[str, str]) -> str:
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


def write_style_audit(path: str | Path, audit: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
