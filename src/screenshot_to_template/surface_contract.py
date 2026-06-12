"""Compile raw section YAML into a deterministic surface/component contract."""

from __future__ import annotations

import copy
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml


ALLOWED_KINDS = {
    "section",
    "surface",
    "layout",
    "text",
    "control",
    "media",
    "divider",
    "effect",
    "unknown",
}
VISIBILITY_EXCEPTIONS = {"structural_only", "partial", "obscured", "unclear"}
PLACEHOLDER_RE = re.compile(r"\b(?:none|none_observed|not_observed|not explicit|n/a|null)\b", re.IGNORECASE)
UNCERTAINTY_VALUE_RE = re.compile(
    r"\b(?:approximately|approx\.?|about|around|roughly|unclear|low confidence|medium confidence|high confidence)\b|\d+\s*-\s*\d+",
    re.IGNORECASE,
)
COLOR_RE = re.compile(
    r"#(?:[0-9A-Fa-f]{3,8})\b|rgba?\([^)]*\)|hsla?\([^)]*\)|(?:linear|radial)-gradient\([^)]*\)",
    re.IGNORECASE,
)


def build_surface_component_contract(
    section_grounding_markdown: str,
    source_style_ledger: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical deterministic surface/component contract payload."""
    documents, parse_errors = parse_section_grounding_documents(section_grounding_markdown)
    ledger = _load_ledger(source_style_ledger)
    ledger_colors = _extract_ledger_colors(ledger)

    audit_state: dict[str, Any] = {
        "parse_errors": parse_errors,
        "raw_kind_violations": [],
        "missing_role_field": [],
        "none_placeholder_paths": [],
        "default_visibility_paths": [],
        "uncertain_implementation_values": [],
        "unknown_role_without_reason": [],
        "section_count": len(documents),
        "sections_with_host_surface": set(),
        "sections_with_tree_children": set(),
        "sections_with_nested_children": set(),
        "explicit_colors": set(),
        "preserved_colors": set(),
    }

    records: list[dict[str, Any]] = []
    for doc_index, doc in enumerate(documents, start=1):
        section_label = _section_label(doc, doc_index)
        tree = doc.get("tree") if isinstance(doc.get("tree"), dict) else doc
        source = doc.get("source") if isinstance(doc.get("source"), dict) else {}
        section_index = source.get("section_index") or doc_index
        if isinstance(tree, dict) and _has_nested_children(tree):
            audit_state["sections_with_tree_children"].add(section_index)
        _audit_raw_node(tree, f"section_{section_index:02d}.tree", audit_state)
        _walk_node(
            tree,
            records=records,
            audit_state=audit_state,
            section_index=section_index,
            section_label=section_label,
            parent_trace_id=None,
            parent_host_trace_id=None,
            path=f"section_{section_index:02d}.tree",
        )

    records_by_trace = {record["trace_id"]: record for record in records}
    host_records = [
        record for record in records
        if record["kind"] in {"section", "surface"}
    ]
    child_records = [
        record for record in records
        if record["kind"] not in {"section", "unknown"} and record.get("parent_host_trace_id")
    ]

    host_surfaces = []
    for host in host_records:
        host_children = [
            _contract_child(child, ledger_colors, audit_state)
            for child in child_records
            if child.get("parent_host_trace_id") == host["trace_id"] and child["trace_id"] != host["trace_id"]
        ]
        if host_children:
            audit_state["sections_with_nested_children"].add(host["section_index"])
        audit_state["sections_with_host_surface"].add(host["section_index"])
        host_surfaces.append(
            {
                "trace_id": host["trace_id"],
                "generation_role": _generation_role(host),
                "frequency": "occasional",
                "host": _contract_host(host, ledger_colors, audit_state),
                "children": host_children,
            }
        )

    critical_pairings = _critical_pairings(host_surfaces)
    typography_pairings = _typography_pairings(records, records_by_trace, ledger_colors, audit_state)
    imagery = _imagery_directions(records)
    graphics_depth_edge = _graphics_depth_edge_recipes(records)
    do_not_generalize = _do_not_generalize(records)
    repeated_layouts = _repeated_layout_patterns(records)

    audit = _build_audit(audit_state, host_surfaces, records)
    payload = {
        "schema_version": "surface_component_contract.v1",
        "type": "surface_component_contract",
        "source": {
            "section_grounding_schema": "raw_section_yaml.v1",
            "source_style_ledger": "source-style-ledger.yaml" if ledger else "",
            "section_count": len(documents),
        },
        "contracts": {
            "host_surfaces": host_surfaces,
            "critical_pairings": critical_pairings,
            "typography_pairings": typography_pairings,
            "graphics_depth_edge_recipes": graphics_depth_edge,
            "imagery_creative_directions": imagery,
            "repeated_layout_patterns": repeated_layouts,
            "do_not_generalize": do_not_generalize,
            "ambiguities": audit["ambiguities"],
        },
        "audits": audit,
    }
    return payload


def contract_audit_passed(contract: dict[str, Any]) -> bool:
    """Return true when the deterministic contract is safe to use without model fallback."""
    audits = contract.get("audits") if isinstance(contract.get("audits"), dict) else {}
    return bool(audits.get("passed"))


def dump_surface_component_contract(contract: dict[str, Any]) -> str:
    """Serialize a contract as stable YAML."""
    return yaml.safe_dump(contract, sort_keys=False, allow_unicode=False, width=120)


def render_surface_component_contract_for_prompt(contract: dict[str, Any]) -> str:
    """Render generation-facing contract YAML with debug/source-order fields stripped."""
    payload = copy.deepcopy(contract)
    payload.pop("audits", None)
    if isinstance(payload.get("source"), dict):
        payload["source"].pop("section_count", None)
    _strip_debug_keys(payload)
    return dump_surface_component_contract(payload)


def surface_component_contract_audit_to_markdown(contract: dict[str, Any]) -> str:
    """Render a compact human-readable audit report."""
    audit = contract.get("audits") if isinstance(contract.get("audits"), dict) else {}
    coverage = audit.get("coverage") if isinstance(audit.get("coverage"), dict) else {}
    validity = audit.get("validity") if isinstance(audit.get("validity"), dict) else {}
    lines = [
        "# Surface Component Contract Audit",
        "",
        f"- Passed: **{bool(audit.get('passed'))}**",
        f"- Sections parsed: {coverage.get('parsed_sections', 0)} / {coverage.get('total_sections', 0)}",
        f"- Host surfaces: {coverage.get('host_surface_count', 0)}",
        f"- Child recipes: {coverage.get('child_recipe_count', 0)}",
        f"- Nested child coverage: {coverage.get('nested_child_coverage', 0):.2f}",
        f"- Explicit colors preserved: {coverage.get('explicit_colors_preserved', 0)} / {coverage.get('explicit_colors_observed', 0)}",
        "",
        "## Validity Gates",
        "",
    ]
    for key, value in validity.items():
        lines.append(f"- `{key}`: {value}")
    ambiguities = audit.get("ambiguities") or []
    if ambiguities:
        lines.extend(["", "## Ambiguities", ""])
        lines.extend(f"- {item}" for item in ambiguities[:80])
    return "\n".join(lines).rstrip() + "\n"


def write_surface_component_contract_artifacts(
    output_dir: str | Path,
    contract: dict[str, Any],
) -> tuple[Path, Path, Path]:
    """Write contract YAML plus JSON/Markdown audits beside the pipeline artifacts."""
    output = Path(output_dir)
    contract_path = output / "surface-component-contract.yaml"
    audit_json_path = output / "surface-component-contract-audit.json"
    audit_md_path = output / "surface-component-contract-audit.md"
    contract_path.write_text(dump_surface_component_contract(contract))
    audit_json_path.write_text(json.dumps(contract.get("audits", {}), indent=2) + "\n")
    audit_md_path.write_text(surface_component_contract_audit_to_markdown(contract))
    return contract_path, audit_json_path, audit_md_path


def parse_section_grounding_documents(section_grounding_markdown: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse raw section YAML documents from the collected section-grounding bundle."""
    documents: list[dict[str, Any]] = []
    errors: list[str] = []
    if not section_grounding_markdown.strip():
        return documents, ["No section grounding content provided."]

    blocks = re.split(r"\n\s*---\s*\n", section_grounding_markdown.strip())
    for index, block in enumerate(blocks, start=1):
        yaml_text = _extract_yaml_from_block(block)
        if not yaml_text:
            continue
        try:
            parsed = yaml.safe_load(yaml_text)
        except yaml.YAMLError as exc:
            errors.append(f"block {index}: {exc}")
            continue
        if isinstance(parsed, dict):
            documents.append(parsed)
        else:
            errors.append(f"block {index}: parsed YAML was not a mapping")
    if not documents and not errors:
        errors.append("No parseable raw section YAML documents found.")
    return documents, errors


def _extract_yaml_from_block(block: str) -> str:
    lines = block.strip().splitlines()
    for index, line in enumerate(lines):
        if re.match(r"^(schema_version|type|source|section|tree):\s*", line):
            return "\n".join(lines[index:]).strip()
    return ""


def _load_ledger(source_style_ledger: str | dict[str, Any] | None) -> dict[str, Any] | None:
    if isinstance(source_style_ledger, dict):
        return source_style_ledger
    if isinstance(source_style_ledger, str) and source_style_ledger.strip():
        try:
            parsed = yaml.safe_load(source_style_ledger)
        except yaml.YAMLError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _extract_ledger_colors(ledger: dict[str, Any] | None) -> list[str]:
    if not ledger:
        return []
    colors: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str):
            for match in COLOR_RE.findall(value):
                normalized = _normalize_color(match)
                if normalized.startswith("#") and normalized not in colors:
                    colors.append(normalized)

    visit(ledger)
    return colors


def _section_label(doc: dict[str, Any], index: int) -> str:
    source = doc.get("source") if isinstance(doc.get("source"), dict) else {}
    section = doc.get("section") if isinstance(doc.get("section"), dict) else {}
    return str(source.get("detected_label") or section.get("role") or f"section {index}")


def _has_nested_children(node: Any) -> bool:
    return isinstance(node, dict) and any(isinstance(node.get(key), list) and node.get(key) for key in ("children", "items", "layers"))


def _audit_raw_node(value: Any, path: str, audit_state: dict[str, Any]) -> None:
    if isinstance(value, dict):
        raw_kind = value.get("kind")
        if isinstance(raw_kind, str) and raw_kind not in ALLOWED_KINDS:
            audit_state["raw_kind_violations"].append(f"{path}.kind={raw_kind}")
        normalized_kind = _normalize_kind(value, is_root=path.endswith(".tree"))
        role_field = _role_field_for_kind(normalized_kind)
        if role_field and _visible_role_knowable(value) and role_field not in value and raw_kind in ALLOWED_KINDS:
            audit_state["missing_role_field"].append(f"{path}.{role_field}")
        if raw_kind == "text" and _visible_role_knowable(value) and "text_scale" not in value:
            audit_state["missing_role_field"].append(f"{path}.text_scale")
        if raw_kind == "media" and _visible_role_knowable(value) and "media_context" not in value:
            audit_state["missing_role_field"].append(f"{path}.media_context")
        if value.get("visibility") == "visible":
            audit_state["default_visibility_paths"].append(f"{path}.visibility")
        if normalized_kind == "unknown" and value.get("semantic_role") == "unknown" and not (value.get("why_unknown") or value.get("why_unknown_role")):
            audit_state["unknown_role_without_reason"].append(path)
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in {"id", "role", "kind", "description", "semantic_role"}:
                continue
            if isinstance(child, str):
                for color in COLOR_RE.findall(child):
                    audit_state["explicit_colors"].add(_normalize_color(color))
                if PLACEHOLDER_RE.search(child):
                    audit_state["none_placeholder_paths"].append(child_path)
                if key not in {"description", "notes", "implementation_assumption"} and UNCERTAINTY_VALUE_RE.search(child):
                    audit_state["uncertain_implementation_values"].append(child_path)
            else:
                _audit_raw_node(child, child_path, audit_state)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _audit_raw_node(child, f"{path}[{index}]", audit_state)
    elif isinstance(value, str):
        for color in COLOR_RE.findall(value):
            audit_state["explicit_colors"].add(_normalize_color(color))


def _walk_node(
    node: Any,
    *,
    records: list[dict[str, Any]],
    audit_state: dict[str, Any],
    section_index: int,
    section_label: str,
    parent_trace_id: str | None,
    parent_host_trace_id: str | None,
    path: str,
) -> None:
    if not isinstance(node, dict):
        return

    is_root = path.endswith(".tree")
    kind = _normalize_kind(node, is_root=is_root)
    node_id = _slug(str(node.get("id") or path.rsplit(".", 1)[-1] or "node"))
    trace_id = f"section_{section_index:02d}.{node_id}"
    if any(record["trace_id"] == trace_id for record in records):
        trace_id = f"{trace_id}_{len(records) + 1}"
    host_trace_id = trace_id if kind in {"section", "surface"} else parent_host_trace_id
    record = {
        "trace_id": trace_id,
        "section_index": section_index,
        "section_label": section_label,
        "path": path,
        "id": node.get("id") or node_id,
        "kind": kind,
        "original_kind": node.get("kind") or "",
        "role": _role_for_node(node, kind, is_root=is_root),
        "semantic_role": _semantic_role(node, kind),
        "parent_trace_id": parent_trace_id,
        "parent_host_trace_id": parent_host_trace_id,
        "style": _extract_style(node),
        "layout": _extract_layout(node),
        "description": _short_text(node.get("description") or node.get("implementation_assumption") or ""),
    }
    records.append(record)

    for key in ("children", "items", "layers"):
        children = node.get(key)
        if not isinstance(children, list):
            continue
        for index, child in enumerate(children):
            if isinstance(child, dict):
                _walk_node(
                    child,
                    records=records,
                    audit_state=audit_state,
                    section_index=section_index,
                    section_label=section_label,
                    parent_trace_id=trace_id,
                    parent_host_trace_id=host_trace_id,
                    path=f"{path}.{key}[{index}]",
                )


def _normalize_kind(node: dict[str, Any], *, is_root: bool = False) -> str:
    raw_kind = str(node.get("kind") or "").lower().strip()
    raw_role = str(node.get("role") or node.get("semantic_role") or "").lower()
    haystack = f"{raw_kind} {raw_role} {node.get('id', '')}".lower()
    if raw_kind in ALLOWED_KINDS:
        return raw_kind
    if is_root or raw_kind == "section":
        return "section"
    if re.search(r"\b(panel|tray|card|tile|shell|surface|frame|overlay|modal|cell)\b", haystack):
        return "surface"
    if re.search(r"\b(button|cta|link|badge|chip|tag|pill|tab|input|select|checkbox|radio|switch|pagination|control)\b", haystack):
        return "control"
    if raw_kind == "text" or re.search(r"\b(text|heading|headline|title|copy|paragraph|caption|label|metadata)\b", haystack):
        if not re.search(r"\b(stack|group|rail|area)\b", haystack):
            return "text"
    if re.search(r"\b(image|photo|media|graphic|illustration|icon|logo|mockup|wordmark|art|background)\b", haystack):
        return "media"
    if re.search(r"\b(divider|separator|rule|line|border|underline)\b", haystack):
        return "divider"
    if re.search(r"\b(gradient|scrim|glow|blur|mask|texture|shadow|overlay)\b", haystack):
        return "effect"
    if re.search(r"\b(stack|group|row|column|grid|track|rail|carousel|container|wrapper|layout|region|cluster|list|nav)\b", haystack):
        return "layout"
    return "unknown"


def _role_field_for_kind(kind: str) -> str | None:
    return {
        "section": "section_role",
        "surface": "surface_role",
        "layout": "layout_role",
        "text": "text_role",
        "control": "control_role",
        "media": "media_category",
    }.get(kind)


def _visible_role_knowable(node: dict[str, Any]) -> bool:
    visibility = node.get("visibility")
    return visibility not in VISIBILITY_EXCEPTIONS


def _role_for_node(node: dict[str, Any], kind: str, *, is_root: bool = False) -> str:
    explicit_field = _role_field_for_kind(kind)
    if explicit_field and node.get(explicit_field):
        return str(node[explicit_field])
    raw_kind = str(node.get("kind") or "").lower()
    raw_role = str(node.get("role") or node.get("semantic_role") or node.get("id") or "").lower()
    haystack = f"{raw_kind} {raw_role}"
    if kind == "section":
        return _section_role(haystack)
    if kind == "surface":
        if is_root:
            return "canvas"
        if "overlay" in haystack:
            return "overlay"
        if re.search(r"\b(card|tile|item)\b", haystack):
            return "card"
        if re.search(r"\b(frame|cell|media)\b", haystack):
            return "frame"
        return "module"
    if kind == "layout":
        return _layout_role(haystack)
    if kind == "text":
        return _text_role(haystack)
    if kind == "control":
        return _control_role(haystack)
    if kind == "media":
        return _media_category(node, haystack)
    if kind == "divider":
        return "separator"
    if kind == "effect":
        return _effect_role(haystack)
    return "unknown"


def _section_role(haystack: str) -> str:
    candidates = [
        ("navbar", r"\b(nav|navigation)\b"),
        ("footer", r"\bfooter\b"),
        ("hero_header", r"\b(hero|opening|header)\b"),
        ("compact_header", r"\b(intro|page header|compact)\b"),
        ("pricing", r"\bpricing\b"),
        ("testimonial", r"\b(testimonial|review)\b"),
        ("faq", r"\bfaq|accordion\b"),
        ("logo_bar", r"\blogo\b"),
        ("stats_metrics", r"\b(stat|metric|proof)\b"),
        ("cta", r"\b(cta|call to action|newsletter)\b"),
        ("gallery", r"\b(gallery|collage)\b"),
        ("product_showcase", r"\b(product|listing|showcase|carousel)\b"),
        ("contact", r"\b(contact|form)\b"),
        ("utility_bar", r"\b(bar|promise|assurance|strip)\b"),
    ]
    for role, pattern in candidates:
        if re.search(pattern, haystack):
            return role
    return "feature"


def _layout_role(haystack: str) -> str:
    for role in (
        "container",
        "carousel",
        "masonry_grid",
        "bento_grid",
        "grid",
        "split",
        "row",
        "column",
        "wrap",
        "rail",
        "tabs",
        "table",
        "timeline",
        "overlay",
        "floating",
    ):
        if role in haystack:
            return role
    if "track" in haystack:
        return "carousel"
    if "stack" in haystack:
        return "column"
    return "container" if "wrapper" in haystack else "row"


def _text_role(haystack: str) -> str:
    if re.search(r"\b(display|hero|poster|metric|number)\b", haystack):
        return "display"
    if re.search(r"\b(heading|headline|title|h1|h2|h3)\b", haystack):
        return "heading"
    if re.search(r"\b(subheading|kicker|lede)\b", haystack):
        return "subheading"
    if re.search(r"\b(label|button|badge|eyebrow|nav)\b", haystack):
        return "label"
    if re.search(r"\b(caption|legal|micro)\b", haystack):
        return "caption"
    if "metadata" in haystack:
        return "metadata"
    return "body"


def _control_role(haystack: str) -> str:
    if "icon" in haystack and ("button" in haystack or "control" in haystack):
        return "icon_button"
    for role in (
        "button",
        "text_link",
        "input",
        "checkbox",
        "radio",
        "switch",
        "select",
        "slider",
        "tab",
        "chip_tag",
        "pagination",
        "accordion_trigger",
        "menu_trigger",
        "search",
    ):
        if role.replace("_", " ") in haystack or role in haystack:
            return role
    if re.search(r"\b(badge|status|pill|tag|chip|eyebrow)\b", haystack):
        return "badge_status"
    if "link" in haystack:
        return "text_link"
    return "button"


def _media_category(node: dict[str, Any], haystack: str) -> str:
    explicit = str(node.get("media_category") or node.get("imagery_category") or "").lower()
    haystack = f"{explicit} {haystack}"
    if re.search(r"\b(photo|photography|raster)\b", haystack):
        return "photo"
    if re.search(r"\b(interface|mockup|screenshot|ui)\b", haystack):
        return "interface"
    if re.search(r"\b(icon|logo|mark|wordmark)\b", haystack):
        return "icon"
    if re.search(r"\b(illustration|graphic|art|ornament)\b", haystack):
        return "illustration_graphic"
    return "unknown"


def _effect_role(haystack: str) -> str:
    for role in ("scrim", "vignette", "glow", "blur", "mask", "grain", "texture", "tonal_overlay", "shadow_layer"):
        if role.replace("_", " ") in haystack or role in haystack:
            return role
    if "gradient" in haystack:
        return "tonal_overlay"
    return "shadow_layer"


def _semantic_role(node: dict[str, Any], kind: str) -> str:
    value = node.get("semantic_role") or node.get("role") or node.get("id") or kind
    return _slug(str(value).replace("_", "-"))


def _extract_style(node: dict[str, Any]) -> dict[str, Any]:
    style = node.get("style") if isinstance(node.get("style"), dict) else {}
    layers = node.get("layers") if isinstance(node.get("layers"), list) else []
    out: dict[str, Any] = {}
    out["fill"] = _first_present(style, "background_color_estimate", "background", "background_color", "fill", "color_estimate")
    out["text"] = _first_present(style, "text_color", "text_color_estimate", "color_estimate", "color")
    out["border"] = _first_present(style, "border", "border_color_estimate", "border_color")
    out["shadow"] = _first_present(style, "shadow", "box_shadow", "depth")
    out["radius"] = _first_present(style, "border_radius", "radius")
    out["font_size"] = _first_present(style, "font_size")
    out["font_weight"] = _first_present(style, "font_weight")
    out["line_height"] = _first_present(style, "line_height")
    out["letter_spacing"] = _first_present(style, "letter_spacing")
    out["text_transform"] = _first_present(style, "text_transform")
    if layers:
        descriptions = []
        for layer in layers:
            if isinstance(layer, dict):
                descriptions.append(_short_text(layer.get("description") or layer.get("gradient_estimate") or layer.get("color_treatment") or ""))
        if descriptions:
            out["layering"] = [item for item in descriptions if item][:4]
    return {key: value for key, value in out.items() if _useful_value(value)}


def _extract_layout(node: dict[str, Any]) -> dict[str, Any]:
    layout = node.get("layout") if isinstance(node.get("layout"), dict) else {}
    size = node.get("size") if isinstance(node.get("size"), dict) else {}
    out = {}
    for source in (layout, size):
        for key in (
            "display",
            "direction",
            "gap",
            "padding",
            "padding_top",
            "padding_bottom",
            "padding_left",
            "padding_right",
            "padding_inline",
            "padding_block",
            "content_width_behavior",
            "width_behavior",
            "overflow",
            "overflow_x",
            "aspect_ratio",
            "width",
            "height",
            "visible_width",
        ):
            value = source.get(key)
            if _useful_value(value):
                out[key] = value
    return out


def _first_present(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if _useful_value(value):
            return value
    return None


def _useful_value(value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    if isinstance(value, str) and PLACEHOLDER_RE.fullmatch(value.strip()):
        return False
    return True


def _contract_host(record: dict[str, Any], ledger_colors: list[str], audit_state: dict[str, Any]) -> dict[str, Any]:
    style = record.get("style") or {}
    host = {
        "generation_role": _generation_role(record),
        "kind": record["kind"],
        "surface_role": record["role"] if record["kind"] == "surface" else "canvas",
        "semantic_role": record["semantic_role"],
        "background": _style_value(style.get("fill"), ledger_colors, audit_state),
        "text": _style_value(style.get("text"), ledger_colors, audit_state),
        "edge": _edge_summary(style),
        "border": style.get("border"),
        "depth": style.get("shadow"),
        "radius": style.get("radius"),
        "layout": _compact_mapping(record.get("layout") or {}, max_items=8),
    }
    return {key: value for key, value in host.items() if _useful_value(value)}


def _contract_child(record: dict[str, Any], ledger_colors: list[str], audit_state: dict[str, Any]) -> dict[str, Any]:
    style = record.get("style") or {}
    role_field = _role_field_for_kind(record["kind"])
    child = {
        "trace_id": record["trace_id"],
        "generation_role": _generation_role(record),
        "kind": record["kind"],
        "semantic_role": record["semantic_role"],
        "fill": _style_value(style.get("fill"), ledger_colors, audit_state),
        "text": _style_value(style.get("text"), ledger_colors, audit_state),
        "border": style.get("border"),
        "shadow": style.get("shadow"),
        "radius": style.get("radius"),
        "typography": _typography_recipe(record),
        "layout": _compact_mapping(record.get("layout") or {}, max_items=8),
        "evidence_visibility": "generation_safe",
    }
    if role_field:
        child[role_field] = record["role"]
    return {key: value for key, value in child.items() if _useful_value(value)}


def _style_value(value: Any, ledger_colors: list[str], audit_state: dict[str, Any]) -> Any:
    if not _useful_value(value):
        return None
    text = str(value)
    color = next((match for match in COLOR_RE.findall(text) if match.startswith("#")), "")
    if not color:
        return value
    grounded = _normalize_color(color)
    audit_state["preserved_colors"].add(grounded)
    nearest, delta = _nearest_color(grounded, ledger_colors)
    if nearest and delta <= 6:
        return {
            "grounded": grounded,
            "source_backed": nearest,
            "decision": "use_source_backed",
            "delta": round(delta, 2),
            "role_compatible": True,
        }
    return {
        "grounded": grounded,
        "decision": "use_grounded",
    }


def _edge_summary(style: dict[str, Any]) -> str | None:
    parts = []
    if style.get("radius"):
        parts.append(f"radius {style['radius']}")
    if style.get("border"):
        parts.append(f"border {style['border']}")
    if style.get("shadow"):
        parts.append(f"depth {style['shadow']}")
    return "; ".join(parts) if parts else None


def _typography_recipe(record: dict[str, Any]) -> dict[str, Any]:
    style = record.get("style") or {}
    recipe = {}
    for key in ("font_size", "font_weight", "line_height", "letter_spacing", "text_transform"):
        if _useful_value(style.get(key)):
            recipe[key] = style[key]
    if record["kind"] == "text":
        recipe["text_role"] = record["role"]
        recipe["text_scale"] = _text_scale(style.get("font_size"), record["role"])
    return recipe


def _text_scale(font_size: Any, role: str) -> str:
    text = str(font_size or "")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    size = float(match.group(1)) if match else 0
    if size >= 64:
        return "display_xl"
    if size >= 48:
        return "display"
    if size >= 36:
        return "heading_xl"
    if size >= 28:
        return "heading_lg"
    if size >= 22:
        return "heading_md"
    if size >= 18:
        return "heading_sm" if role == "heading" else "body_lg"
    if size >= 13:
        return "body"
    if size > 0:
        return "caption"
    return "unknown"


def _critical_pairings(host_surfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairings = []
    for host in host_surfaces:
        host_summary = host.get("host") or {}
        for child in host.get("children") or []:
            if any(child.get(key) for key in ("fill", "text", "border", "shadow", "radius")):
                pairings.append(
                    {
                        "host_generation_role": host.get("generation_role"),
                        "host_background": host_summary.get("background"),
                        "child_generation_role": child.get("generation_role"),
                        "child_kind": child.get("kind"),
                        "child_fill": child.get("fill"),
                        "child_text": child.get("text"),
                        "child_border": child.get("border"),
                    }
                )
    return pairings[:180]


def _typography_pairings(
    records: list[dict[str, Any]],
    records_by_trace: dict[str, dict[str, Any]],
    ledger_colors: list[str],
    audit_state: dict[str, Any],
) -> list[dict[str, Any]]:
    pairings = []
    for record in records:
        if record["kind"] != "text":
            continue
        host = records_by_trace.get(record.get("parent_host_trace_id") or "")
        pairings.append(
            {
                "host_generation_role": _generation_role(host) if host else "",
                "text_role": record["role"],
                "text_scale": _text_scale((record.get("style") or {}).get("font_size"), record["role"]),
                "color": _style_value((record.get("style") or {}).get("text"), ledger_colors, audit_state),
                "typography": _typography_recipe(record),
            }
        )
    return pairings


def _imagery_directions(records: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record["kind"] != "media":
            continue
        category = record["role"]
        text = _short_text(record.get("description") or record.get("semantic_role") or "")
        if text and text not in grouped[category]:
            grouped[category].append(text)
    return {key: values[:12] for key, values in grouped.items()}


def _graphics_depth_edge_recipes(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recipes = []
    for record in records:
        style = record.get("style") or {}
        if record["kind"] in {"media", "divider", "effect"} or any(style.get(key) for key in ("border", "shadow", "radius", "layering")):
            recipes.append(
                {
                    "generation_role": _generation_role(record),
                    "kind": record["kind"],
                    "edge": _edge_summary(style),
                    "layers": style.get("layering"),
                }
            )
    return [_compact_mapping(item, max_items=5) for item in recipes[:120]]


def _do_not_generalize(records: list[dict[str, Any]]) -> list[str]:
    items = []
    for record in records:
        haystack = f"{record.get('original_kind')} {record.get('role')} {record.get('semantic_role')} {record.get('description')}".lower()
        if re.search(r"\b(logo|wordmark|payment|embedded|showcase|decorative|mockup|screenshot|background)\b", haystack):
            item = f"{_generation_role(record)}: preserve as {record['kind']} evidence, not as a global component default."
            if item not in items:
                items.append(item)
    return items[:80]


def _repeated_layout_patterns(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter = Counter(
        record["role"]
        for record in records
        if record["kind"] == "layout" and record.get("role")
    )
    return [
        {"layout_role": role, "frequency": count}
        for role, count in counter.most_common()
        if count >= 2
    ]


def _build_audit(audit_state: dict[str, Any], host_surfaces: list[dict[str, Any]], records: list[dict[str, Any]]) -> dict[str, Any]:
    section_count = int(audit_state["section_count"])
    sections_with_tree_children = audit_state["sections_with_tree_children"]
    sections_with_nested_children = audit_state["sections_with_nested_children"]
    nested_denominator = len(sections_with_tree_children)
    nested_coverage = (len(sections_with_nested_children) / nested_denominator) if nested_denominator else 1.0
    child_recipe_count = sum(len(host.get("children") or []) for host in host_surfaces)
    raw_schema_ok = not any(
        audit_state[key]
        for key in (
            "raw_kind_violations",
            "missing_role_field",
            "none_placeholder_paths",
            "default_visibility_paths",
            "uncertain_implementation_values",
            "unknown_role_without_reason",
        )
    )
    coverage_ok = (
        not audit_state["parse_errors"]
        and section_count > 0
        and len(audit_state["sections_with_host_surface"]) >= section_count
        and nested_coverage >= 0.9
        and child_recipe_count > 0
    )
    ambiguities = []
    for key in (
        "parse_errors",
        "raw_kind_violations",
        "missing_role_field",
        "none_placeholder_paths",
        "default_visibility_paths",
        "uncertain_implementation_values",
        "unknown_role_without_reason",
    ):
        for item in list(audit_state[key])[:20]:
            ambiguities.append(f"{key}: {item}")
    return {
        "passed": bool(raw_schema_ok and coverage_ok),
        "coverage": {
            "total_sections": section_count,
            "parsed_sections": section_count - len(audit_state["parse_errors"]),
            "visual_node_count": len(records),
            "host_surface_count": len(host_surfaces),
            "child_recipe_count": child_recipe_count,
            "sections_with_host_surface": len(audit_state["sections_with_host_surface"]),
            "sections_with_tree_children": nested_denominator,
            "sections_with_nested_children": len(sections_with_nested_children),
            "nested_child_coverage": round(nested_coverage, 3),
            "explicit_colors_observed": len(audit_state["explicit_colors"]),
            "explicit_colors_preserved": len(audit_state["preserved_colors"]),
        },
        "validity": {
            "parse_all_section_yaml": not audit_state["parse_errors"],
            "raw_schema_uses_closed_kind_enum": not audit_state["raw_kind_violations"],
            "raw_schema_uses_kind_specific_role_fields": not audit_state["missing_role_field"],
            "raw_schema_omits_none_placeholders": not audit_state["none_placeholder_paths"],
            "raw_schema_omits_default_visible": not audit_state["default_visibility_paths"],
            "raw_schema_uses_clean_implementation_values": not audit_state["uncertain_implementation_values"],
            "unknown_roles_explain_why": not audit_state["unknown_role_without_reason"],
            "extract_at_least_one_host_per_section": len(audit_state["sections_with_host_surface"]) >= section_count,
            "extract_nested_children_for_90_percent": nested_coverage >= 0.9,
            "extract_nonempty_child_recipes": child_recipe_count > 0,
        },
        "source_order_leakage": {
            "generation_facing_renderer_strips_trace_ids": True,
            "contract_file_keeps_trace_ids_for_debug": True,
        },
        "ambiguities": ambiguities,
    }


def _style_source(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("source_backed") or value.get("grounded") or "")
    return str(value or "")


def _generation_role(record: dict[str, Any] | None) -> str:
    if not record:
        return ""
    role = record.get("role") or record.get("semantic_role") or record.get("kind")
    kind = record.get("kind") or "node"
    return _slug(f"{kind}_{role}").replace("-", "_")


def _compact_mapping(mapping: dict[str, Any], max_items: int = 6) -> dict[str, Any]:
    out = {}
    for key, value in mapping.items():
        if _useful_value(value):
            out[key] = value
        if len(out) >= max_items:
            break
    return out


def _strip_debug_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key in list(value.keys()):
            if key in {"trace_id", "path", "section_index", "section_label"}:
                value.pop(key, None)
            else:
                _strip_debug_keys(value[key])
    elif isinstance(value, list):
        for child in value:
            _strip_debug_keys(child)


def _nearest_color(color: str, candidates: list[str]) -> tuple[str | None, float]:
    rgb = _hex_to_rgb(color)
    if not rgb:
        return None, math.inf
    best: tuple[str | None, float] = (None, math.inf)
    for candidate in candidates:
        candidate_rgb = _hex_to_rgb(candidate)
        if not candidate_rgb:
            continue
        delta = math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb, candidate_rgb)))
        if delta < best[1]:
            best = (candidate, delta)
    return best


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    value = _normalize_color(value)
    if not value.startswith("#"):
        return None
    hex_part = value[1:]
    if len(hex_part) == 3:
        hex_part = "".join(ch * 2 for ch in hex_part)
    if len(hex_part) < 6:
        return None
    try:
        return int(hex_part[0:2], 16), int(hex_part[2:4], 16), int(hex_part[4:6], 16)
    except ValueError:
        return None


def _normalize_color(value: str) -> str:
    value = value.strip()
    return value.upper() if value.startswith("#") else value


def _short_text(value: Any, max_len: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[: max_len - 3].rstrip() + "..." if len(text) > max_len else text


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "node"
