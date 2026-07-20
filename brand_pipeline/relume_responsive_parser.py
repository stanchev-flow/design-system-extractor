#!/usr/bin/env python3
"""Extract structured responsive rules from temporary Relume MCP TSX responses.

The input is the markdown returned by ``get_components``. Component source remains
temporary; only normalized behavior and anatomy evidence are merged into the catalog.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

try:
    from .relume_recipe_catalog import RESPONSIVE_EVIDENCE, RESPONSIVE_SCHEMA_VERSION
except ImportError:  # direct script execution
    from relume_recipe_catalog import RESPONSIVE_EVIDENCE, RESPONSIVE_SCHEMA_VERSION

_COMPONENT_RE = re.compile(
    r"^### .+?  \(slug: ([^)]+)\)\s*\n// File: [^\n]+\n```tsx\n(.*?)^```",
    re.MULTILINE | re.DOTALL,
)
_CLASS_RE = re.compile(r'className="([^"]+)"')
_BREAKPOINTS = ("sm", "md", "lg", "xl", "2xl")


def _axis_value(token: str) -> tuple[str, str] | None:
    if token in {"hidden", "block", "flex", "grid", "inline", "inline-flex"}:
        return "display", token
    for prefix, axis in (
        ("grid-cols-", "columns"),
        ("flex-", "flexDirection"),
        ("order-", "order"),
        ("overflow-", "overflow"),
        ("aspect-", "mediaAspect"),
        ("object-", "mediaCrop"),
        ("basis-", "itemBasis"),
        ("min-h-", "minHeight"),
        ("h-", "height"),
    ):
        if token.startswith(prefix):
            value = token.removeprefix(prefix)
            if axis == "flexDirection" and value not in {
                "row", "row-reverse", "col", "col-reverse"
            }:
                continue
            if axis in {"height", "minHeight"} and not any(
                marker in value for marker in ("vh", "dvh", "svh", "lvh", "screen", "full", "auto", "calc")
            ):
                # Fixed design-system dimensions are visual styling, not responsive
                # structure. Keep only viewport/full/auto mechanics.
                continue
            return axis, value
    return None


def _split_breakpoint(token: str) -> tuple[str, str]:
    prefix, separator, rest = token.partition(":")
    if separator and prefix in _BREAKPOINTS:
        return prefix, rest
    return "base", token


def _responsive_class_rules(source: str) -> list[dict]:
    rules = []
    for class_index, class_text in enumerate(_CLASS_RE.findall(source)):
        states: dict[str, dict[str, str]] = {}
        for token in class_text.split():
            breakpoint, plain = _split_breakpoint(token)
            parsed = _axis_value(plain)
            if not parsed:
                continue
            axis, value = parsed
            states.setdefault(axis, {})[breakpoint] = value
        for axis, values in states.items():
            transitions = [(bp, values[bp]) for bp in _BREAKPOINTS if bp in values]
            if not transitions and axis not in {
                "overflow", "mediaAspect", "mediaCrop", "height", "minHeight", "itemBasis"
            }:
                continue
            rule = {
                "axis": axis,
                # Never retain source class names. The ordinal only correlates rules
                # extracted from the same element within this one observation.
                "scope": f"element-{class_index}",
                "base": values.get("base", "default"),
            }
            if transitions:
                first_bp, first_value = transitions[0]
                rule.update({"at": first_bp, "value": first_value})
                for bp, value in transitions[1:]:
                    rule[f"at{bp.title()}"] = value
            elif values.get("base"):
                rule["value"] = values["base"]
            rules.append(rule)
    return rules


def _mechanic_rules(source: str) -> list[dict]:
    rules = []
    query = re.search(r'useMediaQuery\("([^"]+)"\)', source)
    if query:
        rules.append({
            "axis": "breakpointQuery",
            "base": "mobile",
            "at": "lg",
            "value": "desktop",
            "query": query.group(1),
        })
    if "onMouseEnter" in source and ("isMobile" in source or query):
        rules.append({
            "axis": "interaction",
            "base": "tap-or-click",
            "at": "lg",
            "value": "hover-or-click",
        })
    if "Carousel" in source:
        rules.append({
            "axis": "carouselInteraction",
            "base": "swipe-or-controls",
            "at": "md",
            "value": "drag-or-controls",
        })
    if "Dialog" in source:
        rules.append({
            "axis": "dialogInteraction",
            "base": "tap-trigger",
            "at": "lg",
            "value": "click-trigger",
        })
    if "sticky" in source:
        rules.append({"axis": "sticky", "base": "enabled", "value": "enabled"})
    if "AnimatePresence" in source:
        rules.append({"axis": "conditionalMotion", "base": "animated-presence", "value": "animated-presence"})
    return rules


def _anatomy(source: str) -> dict:
    props_match = re.search(r"type Props = \{(.*?)^\};", source, re.MULTILINE | re.DOTALL)
    props = []
    if props_match:
        props = re.findall(r"^\s{2}([A-Za-z][A-Za-z0-9_]*)\??:", props_match.group(1), re.MULTILINE)
    primitives = sorted(set(re.findall(r'@/components/ui/([^"]+)', source)))
    mechanics = []
    for marker, name in (
        ("Carousel", "carousel"),
        ("Dialog", "dialog"),
        ("Tabs", "tabs"),
        ("Accordion", "accordion"),
        ("sticky", "sticky"),
        ("overflow-auto", "scroll-container"),
        ("useMediaQuery", "breakpoint-state"),
        ("AnimatePresence", "conditional-motion"),
    ):
        if marker in source:
            mechanics.append(name)
    return {
        "props": sorted(set(props)),
        "primitives": primitives,
        "mechanics": mechanics,
    }


def parse_response(text: str) -> list[dict]:
    observations = []
    for slug, source in _COMPONENT_RE.findall(text):
        rules = _responsive_class_rules(source) + _mechanic_rules(source)
        # Stable de-duplication without losing source order.
        rules = list({
            yaml.safe_dump(rule, sort_keys=True): rule for rule in rules
        }.values())
        if not rules:
            rules = [{
                "axis": "responsiveInvariant",
                "base": "no-breakpoint-transition-observed",
                "value": "no-breakpoint-transition-observed",
            }]
        observations.append({
            "componentSlug": slug.strip(),
            "inspection": "deterministic-tsx-responsive-parser.v1",
            "anatomy": _anatomy(source),
            "rules": rules,
        })
    return observations


def merge_evidence(observations: list[dict], output: Path = RESPONSIVE_EVIDENCE) -> Path:
    existing = yaml.safe_load(output.read_text()) if output.exists() else {}
    if existing and existing.get("schemaVersion") != RESPONSIVE_SCHEMA_VERSION:
        raise ValueError(f"{output}: unsupported schemaVersion")
    existing = existing or {
        "schemaVersion": RESPONSIVE_SCHEMA_VERSION,
        "source": "Relume Library MCP get_components",
    }
    # Existing hand-inspected observations win over generated observations.
    by_slug = {
        str(observation["componentSlug"]): observation
        for observation in existing.get("observations") or []
        if isinstance(observation, dict) and observation.get("componentSlug")
    }
    for observation in observations:
        slug = str(observation["componentSlug"])
        current = by_slug.get(slug)
        if current is None or str(current.get("inspection") or "").startswith("deterministic-"):
            by_slug[slug] = observation
    existing["observations"] = [by_slug[slug] for slug in sorted(by_slug)]
    output.write_text(yaml.safe_dump(existing, sort_keys=False, width=110))
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("responses", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=RESPONSIVE_EVIDENCE)
    args = parser.parse_args()
    observations = []
    for path in args.responses:
        observations.extend(parse_response(path.read_text()))
    output = merge_evidence(observations, args.output)
    print(f"merged {len(observations)} responsive source inspections into {output}")


if __name__ == "__main__":
    main()
