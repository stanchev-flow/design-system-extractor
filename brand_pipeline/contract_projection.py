"""Deterministic, evidence-honest projection of staged author deltas.

The model authors facts and choices.  This module owns schema completeness:
universal contract coverage, canonical wrapper shapes, measured control geometry,
pattern/layout references, interaction timing, and explicit absence markers.
It never imports values from another lane and never invents measured values.
"""
from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from designed_components import synthesize


CONTRACTS_DIR = Path(__file__).resolve().parent / "contracts"
TIME_RE = re.compile(r"(?<![\w.])(?:\d*\.?\d+m?s)(?!\w)")


def _load(path: Path) -> Any:
    if not path.is_file():
        return {}
    if path.suffix == ".json":
        return json.loads(path.read_text())
    return yaml.safe_load(path.read_text()) or {}


def _dump(doc: dict) -> str:
    return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)


def _contract_map(filename: str, key: str) -> dict:
    doc = _load(CONTRACTS_DIR / filename)
    value = doc.get(key) if isinstance(doc, dict) else None
    return value if isinstance(value, dict) else {}


def _grounding_component_kinds(brand_dir: Path) -> set[str]:
    kinds: set[str] = set()
    for path in sorted((brand_dir / "evidence" / "grounding").glob("*.yaml")):
        doc = _load(path)

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                kind = value.get("kind") or value.get("type")
                if isinstance(kind, str):
                    kinds.add(kind.strip().lower())
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(doc.get("components") if isinstance(doc, dict) else None)
    return kinds


def _provenance_from_wrapper(entry: dict) -> list[str]:
    refs: list[str] = []
    existing = entry.get("provenance")
    if isinstance(existing, list):
        refs.extend(str(v) for v in existing if v)
    for row in entry.get("changelog") or []:
        if not isinstance(row, dict):
            continue
        if row.get("signalId"):
            refs.append(str(row["signalId"]))
        note = str(row.get("note") or "")
        refs.extend(re.findall(r"\b(?:section-\d+|footer|chrome\.[a-z-]+)\b", note))
    return list(dict.fromkeys(refs))


def _canonical_blocks(doc: dict, brand_dir: Path, audit: list[dict]) -> None:
    contracts = _contract_map("blocks.yaml", "blocks")
    blocks = doc.setdefault("blocks", {})
    if not isinstance(blocks, dict):
        return
    observed_kinds = _grounding_component_kinds(brand_dir)
    aliases = {
        alias: name
        for name, contract in contracts.items()
        for alias in (contract.get("aliases") or [])
    }
    observed_contracts = {
        aliases.get(kind, kind) for kind in observed_kinds
        if aliases.get(kind, kind) in contracts
    }
    authored_blob = " ".join(
        f"{name} {block.get('archetype', '')} {block.get('usage', '')}"
        for name, block in blocks.items() if isinstance(block, dict)
        and block.get("origin") in (None, "extracted")
    ).lower()
    for current in blocks.values():
        if isinstance(current, dict) and isinstance(current.get("slots"), list):
            declared = [str(slot) for slot in current["slots"] if str(slot).strip()]
            current["declaredSlots"] = declared
            current["slots"] = {
                slot: {"optional": True, "source": "staged-author-declared-slot"}
                for slot in declared
            }
    for name, current in list(blocks.items()):
        if not (isinstance(current, dict) and isinstance(current.get("value"), dict)):
            continue
        wrapper = current
        projected = copy.deepcopy(wrapper["value"])
        if isinstance(projected.get("slots"), list):
            declared = [str(slot) for slot in projected["slots"] if str(slot).strip()]
            projected["declaredSlots"] = declared
            projected["slots"] = {
                slot: {"optional": True, "source": "staged-author-declared-slot"}
                for slot in declared
            }
        refs = _provenance_from_wrapper(wrapper)
        projected.setdefault(
            "origin",
            "extracted" if wrapper.get("source") in {"grounding", "computed", "measurement"}
            or refs else "designed",
        )
        if refs:
            projected.setdefault("provenance", refs)
        if wrapper.get("confidence"):
            projected.setdefault("confidence", wrapper["confidence"])
        if projected["origin"] == "designed":
            projected.update(synthesize(name, wrapper, doc))
        blocks[name] = projected
        audit.append({
            "family": "blocks", "id": name, "owner": "deterministic-contract",
            "source": "staged author wrapper", "action": "canonicalized",
        })
    authored_blob = " ".join(
        f"{name} {block.get('archetype', '')} {block.get('usage', '')}"
        for name, block in blocks.items() if isinstance(block, dict)
        and block.get("origin") in (None, "extracted")
    ).lower()
    for name in contracts:
        current = blocks.get(name)
        observed_by_author = bool(re.search(
            rf"\b{re.escape(name)}s?\b", authored_blob))
        if name == "card" and isinstance(current, dict) \
                and current.get("origin") == "extracted" and not current.get("variants"):
            variants = []
            if "card-grid" in authored_blob:
                variants.append("icon-card")
            if "card-carousel" in authored_blob or "media-well" in authored_blob:
                variants.append("media-well")
            if variants:
                current["variants"] = variants
        if isinstance(current, dict) and (
                current.get("notObserved") is True or current.get("origin")
                or current.get("use") or current.get("slots")
                or current.get("provenance")):
            if not (current.get("origin") == "designed" and observed_by_author):
                continue
        if name in observed_contracts or observed_by_author:
            observed_entry = {
                "origin": "extracted",
                "provenance": [
                    "evidence/grounding/*.yaml#components[]"
                    if name in observed_contracts else "brand.yaml#measured-block-archetypes"
                ],
                "confidence": "medium",
                "note": "Observed in fresh grounding or a measured extracted block archetype.",
            }
            if name == "card":
                variants = []
                if "card-grid" in authored_blob:
                    variants.append("icon-card")
                if "card-carousel" in authored_blob or "media-well" in authored_blob:
                    variants.append("media-well")
                if variants:
                    observed_entry["variants"] = variants
            blocks[name] = observed_entry
            audit.append({
                "family": "blocks", "id": name, "owner": "deterministic-contract",
                "source": "fresh grounding + measured block archetypes",
                "action": "observed contract slot",
            })
            continue
        absence = {
            "notObserved": True,
            "reason": (
                f"Universal block contract '{name}' was not present in fresh "
                "grounding components[]."
            ),
        }
        designed = synthesize(name, absence, doc)
        blocks[name] = {**absence, **designed}
        audit.append({
            "family": "blocks", "id": name, "owner": "deterministic-contract",
            "source": "contracts/blocks.yaml + fresh grounding component census",
            "action": "designed-notObserved",
            "groundingKindObserved": name in observed_contracts,
        })


def _canonical_catalog_tier(
    doc: dict, brand_dir: Path, tier: str, filename: str, audit: list[dict]
) -> None:
    contracts = _contract_map(filename, tier)
    current = doc.get(tier)
    if isinstance(current, list):
        current = {
            str(row.get("id") or row.get("name")): row
            for row in current if isinstance(row, dict) and (row.get("id") or row.get("name"))
        }
    if not isinstance(current, dict):
        current = {}
    observed = _grounding_component_kinds(brand_dir)
    authored_terms: set[str] = set()
    block_values = (doc.get("blocks") or {}).values() \
        if isinstance(doc.get("blocks"), dict) else []
    for block in block_values:
        if not isinstance(block, dict) or block.get("origin") not in (None, "extracted"):
            continue
        payload = block.get("value") if isinstance(block.get("value"), dict) else block
        authored_terms.add(str(payload.get("archetype") or "").lower())
        payload_slots = payload.get("slots") or {}
        if isinstance(payload_slots, list):
            payload_slots = {str(name): {} for name in payload_slots}
        for slot_name, slot in payload_slots.items():
            authored_terms.add(str(slot_name).lower())
            if isinstance(slot, dict):
                authored_terms.add(str(slot.get("role") or "").lower())
    for layout in doc.get("layouts") or []:
        if not isinstance(layout, dict):
            continue
        for slot in layout.get("slots") or []:
            if isinstance(slot, dict):
                authored_terms.update({
                    str(slot.get("name") or "").lower(),
                    str(slot.get("role") or "").lower(),
                })
    for name, contract in contracts.items():
        aliases = {str(v).lower() for v in contract.get("aliases") or []}
        observed_by_author = any(
            candidate and any(
                re.search(rf"\b{re.escape(candidate)}s?\b", term)
                for term in authored_terms
            )
            for candidate in {name.lower(), *aliases}
        )
        existing = current.get(name)
        if name == "card" and isinstance(existing, dict) \
                and existing.get("origin") == "extracted" and not existing.get("variants"):
            variants = []
            if "card-grid" in authored_blob:
                variants.append("icon-card")
            if "card-carousel" in authored_blob or "media-well" in authored_blob:
                variants.append("media-well")
            if variants:
                existing["variants"] = variants
        if isinstance(existing, dict) and not (
                existing.get("origin") == "designed" and observed_by_author):
            continue
        if name.lower() in observed or aliases & observed or observed_by_author:
            current[name] = {
                "origin": "extracted",
                "provenance": [
                    "evidence/grounding/*.yaml#components[]"
                    if not observed_by_author else "brand.yaml#measured-block-slots"
                ],
                "confidence": "medium",
                "note": "Observed in fresh grounding or measured block/layout slots; detailed facts live in the owning family.",
            }
            action = "observed contract slot"
        else:
            absence = {
                "notObserved": True,
                "reason": (
                    f"Universal {tier} contract '{name}' was not present in fresh "
                    "grounding components[]."
                ),
            }
            current[name] = {**absence, **synthesize(name, absence, doc)}
            action = "designed-notObserved"
        audit.append({
            "family": tier, "id": name, "owner": "deterministic-contract",
            "source": f"contracts/{filename} + fresh grounding component census",
            "action": action,
        })
    doc[tier] = current


def _button_samples(computed: dict) -> list[dict]:
    candidates: list[dict] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            classes = value.get("classes")
            measured = value.get("measured")
            if isinstance(classes, str) and isinstance(measured, dict):
                candidates.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(computed)
    return candidates


def _sample_for_family(samples: list[dict], family: str) -> dict | None:
    family_token = re.compile(rf"(?:^|\s)-{re.escape(family)}(?:\s|$)")
    matches = [
        row for row in samples
        if (
            family_token.search(str(row.get("classes") or ""))
            or (family == "round" and any(
                needle in str(row.get("classes") or "")
                for needle in ("cl-round-button", "cl-roundButton")
            ))
        )
        and isinstance((row.get("measured") or {}).get("_rect"), dict)
    ]
    if not matches:
        return None
    # The saved page contains wrapper/mega-menu controls whose class names include
    # a family word but whose measured rect is the enclosing panel (the HubSpot
    # primary false-positive was 140px tall). Prefer the source's actual reusable
    # control classes, then a hug-width control, before selecting the largest
    # measured size tier inside that evidence class.
    def rank(row: dict) -> tuple[int, int, float]:
        classes = str(row.get("classes") or "")
        is_control_class = int(
            "cl-button" in classes
            or (family == "round" and "cl-round" in classes)
        )
        is_hug = int(str(row.get("widthBehavior") or "") == "hug")
        height = float(((row.get("measured") or {}).get("_rect") or {}).get("h") or 0)
        return is_control_class, is_hug, height
    return max(matches, key=rank)


def _canonical_buttons(doc: dict, brand_dir: Path, audit: list[dict]) -> None:
    buttons = doc.get("buttons")
    if not isinstance(buttons, dict):
        return
    computed = _load(brand_dir / "evidence" / "computed-styles.json")
    samples = _button_samples(computed)
    if "round" not in buttons:
        sample = _sample_for_family(samples, "round")
        measured = sample.get("measured") if isinstance(sample, dict) else None
        rect = measured.get("_rect") if isinstance(measured, dict) else None
        if isinstance(rect, dict) and rect.get("h") and rect.get("w"):
            buttons["round"] = {
                "role": "icon-only round control",
                "style": "filled",
                "bg": measured.get("background-color") or "transparent",
                "fg": measured.get("color") or "currentColor",
                "border": measured.get("border") or "none",
                "radius": measured.get("border-radius") or "50%",
                "height": f"{rect['h']:g}px",
                "diameter": f"{rect['w']:g}px",
                "padding": measured.get("padding") or "0px",
                "focus": "focus ring preserves the measured square host geometry",
                "geometryProvenance": {
                    "source": "evidence/computed-styles.json",
                    "selectorClasses": sample.get("classes"),
                    "confidence": "high",
                },
            }
            audit.append({
                "family": "buttons", "id": "round", "owner": "fresh-evidence-projector",
                "source": "evidence/computed-styles.json", "action": "measured icon control",
            })
    for name, family in list(buttons.items()):
        if name == "singleVariantConfirmed" or not isinstance(family, dict):
            continue
        if isinstance(family.get("value"), dict):
            wrapper = family
            family = copy.deepcopy(wrapper["value"])
            refs = _provenance_from_wrapper(wrapper)
            if refs:
                family.setdefault("provenance", refs)
            if wrapper.get("confidence"):
                family.setdefault("confidence", wrapper["confidence"])
            buttons[name] = family
            audit.append({
                "family": "buttons", "id": name, "owner": "deterministic-contract",
                "source": "staged author wrapper", "action": "canonicalized",
            })
        sample = _sample_for_family(samples, name)
        if isinstance(sample, dict):
            visible = str(sample.get("visibleLabel") or sample.get("sample") or "").strip()
            accessible = str(sample.get("accessibleName") or "").strip()
            if visible:
                family["visibleLabel"] = visible
            if accessible:
                family["accessibleName"] = accessible
            if accessible and accessible != visible:
                family["ariaLabel"] = accessible
            fit = sample.get("labelFit")
            if isinstance(fit, dict):
                family["labelFit"] = copy.deepcopy(fit)
            if visible or accessible:
                family["labelProvenance"] = {
                    "source": "evidence/computed-styles.json",
                    "selectorClasses": sample.get("classes"),
                    "confidence": "high",
                }
                audit.append({
                    "family": "buttons", "id": name, "owner": "fresh-evidence-projector",
                    "source": "evidence/computed-styles.json",
                    "action": "separated visible and accessible labels",
                })
        style = str(family.get("style") or "").lower()
        bg = str(family.get("bg") or "").lower()
        filled = style.startswith("filled") or (
            bg and bg not in {"transparent", "none"} and not bg.startswith("rgba(0, 0, 0, 0")
        )
        if not filled or (family.get("height") and family.get("padding")):
            continue
        measured = sample.get("measured") if isinstance(sample, dict) else None
        rect = measured.get("_rect") if isinstance(measured, dict) else None
        height = rect.get("h") if isinstance(rect, dict) else None
        padding = measured.get("padding") if isinstance(measured, dict) else None
        if height and padding is not None:
            family.setdefault("height", f"{height:g}px" if isinstance(height, float) else f"{height}px")
            family.setdefault("padding", padding)
            family.setdefault("geometryProvenance", {
                "source": "evidence/computed-styles.json",
                "selectorClasses": sample.get("classes"),
                "confidence": "high",
            })
            audit.append({
                "family": "buttons", "id": name, "owner": "fresh-evidence-projector",
                "source": "evidence/computed-styles.json", "action": "measured geometry",
            })


def _motion_for(kind: str, motion_audit: dict) -> dict | None:
    aliases = {
        "tabs": ("tab",),
        "carousel": ("carousel", "slider"),
        "accordion": ("accordion",),
        "modal": ("modal", "dialog"),
        "dropdown-menu": ("dropdown", "menu"),
    }.get(kind, (kind,))
    for row in motion_audit.get("transitions") or []:
        if not isinstance(row, dict):
            continue
        selector = str(row.get("selector") or "").lower()
        if not any(alias in selector for alias in aliases):
            continue
        for transition in row.get("transitions") or []:
            if not isinstance(transition, dict):
                continue
            raw = str(transition.get("raw") or "")
            if TIME_RE.search(raw):
                return {
                    "duration": transition.get("duration"),
                    "easing": transition.get("easing"),
                    "property": transition.get("property"),
                    "source": "evidence/motion-audit.json",
                    "selector": row.get("selector"),
                    "confidence": "high",
                }
    return None


def _canonical_motion(doc: dict, brand_dir: Path, audit: list[dict]) -> None:
    blocks = doc.get("blocks")
    if not isinstance(blocks, dict):
        return
    motion_audit = _load(brand_dir / "evidence" / "motion-audit.json")
    for kind in ("accordion", "tabs", "modal", "dropdown-menu", "carousel"):
        block = blocks.get(kind)
        if not isinstance(block, dict) or block.get("notObserved"):
            continue
        if TIME_RE.search(json.dumps(block)):
            continue
        measured = _motion_for(kind, motion_audit)
        if measured:
            block["motion"] = measured
            audit.append({
                "family": "motion", "id": kind, "owner": "fresh-evidence-projector",
                "source": "evidence/motion-audit.json", "action": "measured timing",
            })
        else:
            block["motion"] = {
                "notObserved": True,
                "reason": (
                    f"No selector-specific {kind} timing was recoverable from the "
                    "fresh motion-audit transition table."
                ),
            }


def _canonical_spacing(doc: dict, brand_dir: Path, audit: list[dict]) -> None:
    spacing = (doc.get("tokens") or {}).get("spacing")
    if not isinstance(spacing, dict):
        return
    corpus = _load(brand_dir / "evidence" / "css-rules.json")
    for row in corpus.get("rules") or []:
        if not isinstance(row, dict):
            continue
        decls = str(row.get("decls") or "")
        if not (isinstance(spacing.get("block-to-block"), dict)
                and spacing["block-to-block"].get("value")):
            match = re.search(r"--(?P<var>[a-z0-9-]*row-gap[a-z0-9-]*)\s*:\s*(?P<value>[\d.]+(?:px|rem|em))", decls)
            if match:
                spacing["block-to-block"] = {
                    "value": match.group("value"),
                    "role": "content-block row rhythm",
                    "provenance": {
                        "source": "evidence/css-rules.json",
                        "sourceVariable": f"--{match.group('var')}",
                        "selector": row.get("selector"),
                        "confidence": "high",
                    },
                }
        column = spacing.get("column-to-column")
        if not (isinstance(column, dict) and column.get("value")):
            match = re.search(
                r"--(?P<var>[a-z0-9-]*(?:column|content)-(?:image-)?gap[a-z0-9-]*)"
                r"\s*:\s*(?P<value>[\d.]+(?:px|rem|em))", decls)
            if match:
                spacing["column-to-column"] = {
                    "value": match.group("value"),
                    "role": "measured split-column gutter",
                    "provenance": {
                        "source": "evidence/css-rules.json",
                        "sourceVariable": f"--{match.group('var')}",
                        "selector": row.get("selector"),
                        "confidence": "high",
                    },
                }
                audit.append({
                    "family": "spacing", "id": "column-to-column",
                    "owner": "fresh-evidence-projector",
                    "source": "evidence/css-rules.json", "action": "measured column rung",
                })
        if (isinstance(spacing.get("block-to-block"), dict)
                and spacing["block-to-block"].get("value")
                and isinstance(spacing.get("column-to-column"), dict)
                and spacing["column-to-column"].get("value")):
            return


def _canonical_layouts(doc: dict, library: dict, audit: list[dict]) -> None:
    patterns = [p for p in library.get("patterns") or [] if isinstance(p, dict) and p.get("id")]
    layouts = doc.get("layouts")
    if not isinstance(layouts, list):
        layouts = []
    by_ref = {
        (row.get("patternRef") or {}).get("id"): row
        for row in layouts if isinstance(row, dict) and isinstance(row.get("patternRef"), dict)
    }
    surface_roles = (doc.get("tokens") or {}).get("surfaces") or {}

    def canonical_surface(raw) -> str:
        value = str(raw or "")
        if value in surface_roles:
            return value
        lower = value.lower()
        if "inverse" in lower:
            for candidate in ("surface/inverse-teal", "surface/inverse-strong", "surface/inverse"):
                if candidate in surface_roles:
                    return candidate
        if any(word in lower for word in ("warm", "white", "canvas", "card")):
            for candidate in ("surface/primary", "surface/warm", "surface/card"):
                if candidate in surface_roles:
                    return candidate
        return value
    for pattern in patterns:
        pid = str(pattern["id"])
        shape = pattern.setdefault("contentShape", {})
        raw_slots = shape.get("slots") if isinstance(shape, dict) else []
        raw_slots = raw_slots if isinstance(raw_slots, list) else []
        media_slots = shape.pop("media", []) if isinstance(shape, dict) else []
        if isinstance(media_slots, list):
            raw_slots.extend(copy.deepcopy(media_slots))
        canonical_slots = []
        seen: dict[str, int] = {}
        for index, raw in enumerate(raw_slots):
            if not isinstance(raw, dict):
                continue
            slot = copy.deepcopy(raw)
            name = str(slot.get("name") or slot.get("role") or f"slot-{index + 1}").strip()
            name = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-") or f"slot-{index + 1}"
            seen[name] = seen.get(name, 0) + 1
            if seen[name] > 1:
                name = f"{name}-{seen[name]}"
            slot["name"] = name
            if isinstance(slot.get("z"), (int, float)):
                slot["z"] = "back" if slot["z"] <= 0 else "front"
            canonical_slots.append(slot)
        if isinstance(shape, dict):
            shape["slots"] = canonical_slots
        def contract_for(slot: dict) -> str:
            label = f"{slot.get('name', '')} {slot.get('role', '')}".lower()
            if any(word in label for word in ("background", "media", "photo", "portrait", "image", "illustration")):
                return "image"
            if any(word in label for word in ("logo", "mark", "badge")):
                return "logo-bar"
            if "tab" in label:
                return "tabs"
            if "stat" in label:
                return "stat-block"
            if "card" in label:
                return "card"
            if any(word in label for word in ("action", "button", "cta", "link")):
                return "button"
            if any(word in label for word in ("heading", "display", "title", "h1", "h2", "h3", "eyebrow")):
                return "header"
            if "quote" in label or "testimonial" in label:
                return "testimonial"
            return "content-block"
        mappings = []
        for slot in canonical_slots:
            contract = contract_for(slot)
            slot.setdefault(
                "type", "media" if contract in {"image", "logo-bar"} else "content")
            mappings.append({
                "slot": slot["name"], "role": slot.get("role") or slot["name"],
                "contract": contract,
            })
        if isinstance(shape, dict):
            shape["slots"] = canonical_slots
        surface = canonical_surface(pattern.get("surfaceIntent"))
        if surface:
            pattern["surfaceIntent"] = surface
        grid_rules = copy.deepcopy(pattern.get("gridRules") or {})
        if not grid_rules and isinstance(shape, dict) and shape.get("columns"):
            grid_rules = {
                "columns": shape["columns"],
                **({"gap": f"{shape['gapPx']}px"} if shape.get("gapPx") else {}),
                **({"split": shape["splitRatio"]} if shape.get("splitRatio") else {}),
            }
            pattern["gridRules"] = copy.deepcopy(grid_rules)
        if pid in by_ref:
            layout = by_ref[pid]
            if canonical_slots and layout.get("slots") != canonical_slots:
                layout["slots"] = copy.deepcopy(canonical_slots)
                audit.append({
                    "family": "layouts", "id": pid, "owner": "deterministic-contract",
                    "source": "layout-library.yaml contentShape.slots",
                    "action": "synchronized measured slots/assets",
                })
            layout["blockMapping"] = copy.deepcopy(mappings)
            layout["requiresHydration"] = True
            if surface:
                layout["surfaceIntent"] = surface
            if grid_rules:
                layout["gridRules"] = copy.deepcopy(grid_rules)
            continue
        archetype = str(pattern.get("archetypeRef") or "stack")
        layouts.append({
            "id": pid,
            "archetype": archetype,
            "useCase": pattern.get("useCase") or pid,
            "patternRef": {"lib": "project", "id": pid},
            "slots": copy.deepcopy(canonical_slots),
            "blockMapping": copy.deepcopy(mappings),
            "requiresHydration": True,
            **({"surfaceIntent": surface} if surface else {}),
            **({"gridRules": copy.deepcopy(grid_rules)} if grid_rules else {}),
            "origin": pattern.get("origin") or "extracted",
            "provenance": copy.deepcopy(pattern.get("provenance") or []),
        })
        audit.append({
            "family": "layouts", "id": pid, "owner": "deterministic-contract",
            "source": "layout-library.yaml patterns[]", "action": "pattern instance",
        })
    doc["layouts"] = layouts


def _canonical_asset_bindings(library: dict, brand_dir: Path, audit: list[dict]) -> None:
    """Resolve model-authored semantic asset handles to fresh registry filenames."""
    registry = _load(brand_dir / "media-assets.yaml")
    rows = [row for row in (registry.get("assets") or []) if isinstance(row, dict)]
    if not rows:
        return
    files = {str(row.get("file")): str(row.get("file")) for row in rows if row.get("file")}
    by_id = {str(row.get("id")): str(row.get("file")) for row in rows
             if row.get("id") and row.get("file")}
    generic = {"logo", "badge", "g2", "icon", "image", "asset", "media"}

    def terms(value: str) -> set[str]:
        return {
            token[:-1] if token.endswith("s") and len(token) > 3 else token
            for token in re.findall(r"[a-z0-9]+", value.lower())
            if token not in generic and not token.isdigit()
        }

    def resolve(value) -> str:
        raw = str(value)
        if raw in files:
            return raw
        if raw in by_id:
            return by_id[raw]
        wanted = terms(raw)
        if not wanted:
            return raw
        scored = []
        for row in rows:
            candidate = terms(f"{row.get('id', '')} {row.get('file', '')}")
            overlap = len(wanted & candidate)
            if overlap:
                scored.append((overlap / max(len(wanted), len(candidate)), overlap,
                               str(row.get("file"))))
        if not scored:
            return raw
        best = max(scored)
        return best[2] if best[1] >= 1 and best[0] >= 0.3 else raw

    for pattern in library.get("patterns") or []:
        if not isinstance(pattern, dict):
            continue
        for slot in ((pattern.get("contentShape") or {}).get("slots") or []):
            if not isinstance(slot, dict):
                continue
            if isinstance(slot.get("assets"), list):
                before = [str(value) for value in slot["assets"]]
                slot["assets"] = [resolve(value) for value in slot["assets"]]
                if "badge" in f"{slot.get('name', '')} {slot.get('role', '')}".lower():
                    badge_files = [
                        str(row.get("file")) for row in rows
                        if str((row.get("assetSemantics") or {}).get("kind") or "").startswith("badge-")
                        and row.get("file")
                    ]
                    for index, value in enumerate(slot["assets"]):
                        if before[index] not in files and value == before[index] \
                                and index < len(badge_files):
                            slot["assets"][index] = badge_files[index]
                if slot["assets"] != before:
                    audit.append({
                        "family": "media-bindings", "id": pattern.get("id"),
                        "owner": "fresh-evidence-projector",
                        "source": "media-assets.yaml", "action": "semantic handle to file",
                    })


def _canonical_grid_equalization(library: dict, audit: list[dict]) -> None:
    for pattern in library.get("patterns") or []:
        if not isinstance(pattern, dict):
            continue
        archetype = str(pattern.get("archetypeRef") or pattern.get("archetype") or "").lower()
        if archetype not in {"grid", "cards", "mosaic"}:
            continue
        shape = pattern.setdefault("contentShape", {})
        if not isinstance(shape, dict) or shape.get("gridEqualize") \
                or shape.get("gridEqualizeNotObserved") is True:
            continue
        shape["gridEqualizeNotObserved"] = True
        shape["gridEqualizeEvidence"] = (
            "Fresh section geometry does not include per-card natural and rendered "
            "heights or flex slack anatomy; no measured stance is asserted."
        )
        audit.append({
            "family": "grid-equalization", "id": pattern.get("id"),
            "owner": "deterministic-contract",
            "source": "fresh section geometry capability check",
            "action": "explicit notObserved",
        })


def _canonical_narrative(doc: dict, audit: list[dict]) -> None:
    """Preserve authored prose as a useful canonical brand snapshot.

    Staged authoring may emit factual envelopes while omitting the optional
    ``brand.snapshot`` projection. Contract completion must not replace that
    omission with an empty generic sentence: compose a deterministic summary
    from authored typography/surface/signature prose already in this lane.
    """
    grammar = doc.get("surfaceGrammar")
    if isinstance(grammar, dict) and isinstance(grammar.get("value"), dict):
        doc["surfaceGrammar"] = {
            **copy.deepcopy(grammar["value"]),
            **{key: copy.deepcopy(grammar[key])
               for key in ("confidence", "source", "scope", "provenance")
               if grammar.get(key) is not None},
        }
        grammar = doc["surfaceGrammar"]
        audit.append({
            "family": "narrative", "id": "surfaceGrammar",
            "owner": "deterministic-contract",
            "source": "surfaceGrammar.value", "action": "canonical envelope",
        })

    brand = doc.setdefault("brand", {})
    snapshot = brand.get("snapshot") if isinstance(brand, dict) else None
    existing = snapshot.get("value") if isinstance(snapshot, dict) else snapshot
    if str(existing or "").strip():
        return
    fragments: list[str] = []
    scale_note = str((doc.get("typography") or {}).get("scaleNote") or "").strip()
    if scale_note:
        fragments.append(scale_note.rstrip("."))
    nesting = str((grammar or {}).get("nesting") or "").strip() \
        if isinstance(grammar, dict) else ""
    if nesting:
        fragments.append(nesting.rstrip("."))
    signature_notes = [
        str(row.get("description") or row.get("claim") or "").strip().rstrip(".")
        for row in (doc.get("signatures") or []) if isinstance(row, dict)
        and str(row.get("description") or row.get("claim") or "").strip()
    ]
    if signature_notes:
        fragments.append("Signature moves: " + "; ".join(signature_notes[:4]))
    if fragments:
        brand["snapshot"] = {
            "value": ". ".join(fragments) + ".",
            "projectionProvenance": [
                "typography.scaleNote",
                "surfaceGrammar.nesting",
                "signatures[].description",
            ],
        }
        audit.append({
            "family": "narrative", "id": "brand.snapshot",
            "owner": "deterministic-contract",
            "source": "authored factual prose", "action": "rich deterministic projection",
        })


def _canonical_nav_utility(doc: dict, audit: list[dict]) -> None:
    nav = doc.get("navbar")
    if not isinstance(nav, dict):
        return
    utility = nav.get("utility")
    if isinstance(utility, list):
        for row in utility:
            if not isinstance(row, dict) or row.get("kind") != "dropdown":
                continue
            dropdown = row.get("dropdown")
            if isinstance(dropdown, dict) and dropdown.get("items") \
                    and not isinstance(dropdown.get("panelPresentation"), dict):
                row.setdefault("dropdownNotObserved", True)
                row.setdefault(
                    "notObservedReason",
                    "Fresh saved-page evidence contains labels but no open-state "
                    "panel geometry/paint measurement.")
        for row in nav.get("primary") or []:
            if not isinstance(row, dict):
                continue
            if row.get("hasDropdown") and not row.get("menu") \
                    and str(row.get("href") or "") in {"", "#"}:
                row["utilityNotObserved"] = True
                row["notObservedReason"] = (
                    "Fresh capture did not include the open dropdown panel."
                )
        audit.append({
            "family": "navbar-utility", "id": "utility",
            "owner": "deterministic-contract",
            "source": "staged chrome factual delta",
            "action": "explicit unobserved open-state markers",
        })
        return
    if not isinstance(utility, dict):
        return
    rows: list[dict] = []
    switcher = utility.get("languageSwitcher")
    if isinstance(switcher, dict):
        options = [
            {"label": row.get("label"), "href": row.get("href")}
            for row in switcher.get("options") or []
            if isinstance(row, dict) and row.get("label")
        ]
        rows.append({
            "kind": "dropdown",
            "role": "locale switcher",
            "label": switcher.get("trigger") or "Locale",
            "dropdown": {"items": options},
            "dropdownNotObserved": True,
            "notObservedReason": (
                "Menu labels were present in fresh chrome facts, but no fresh open-state "
                "panel geometry/paint measurement was captured."
            ),
            "provenance": ["brand-chrome.yaml#navbar.utility.languageSwitcher"],
        })
    for row in utility.get("links") or []:
        if isinstance(row, dict):
            rows.append({**row, "kind": "link"})
    about = utility.get("aboutDropdown")
    if isinstance(about, dict):
        rows.append({
            "kind": "dropdown",
            "role": "about menu",
            "label": about.get("trigger") or "About",
            "dropdown": {"items": copy.deepcopy(about.get("links") or [])},
            "dropdownNotObserved": True,
            "notObservedReason": "No fresh open-state panel geometry/paint measurement was captured.",
            "provenance": ["brand-chrome.yaml#navbar.utility.aboutDropdown"],
        })
    nav["utility"] = rows
    audit.append({
        "family": "navbar-utility", "id": "utility",
        "owner": "deterministic-contract",
        "source": "staged chrome factual delta", "action": "canonical control list",
    })


def _canonical_chrome_measurements(doc: dict, audit: list[dict]) -> None:
    """Normalize measured px strings where consumers require numeric px values."""
    for owner in ("navbar", "footer"):
        measured = (doc.get(owner) or {}).get("measured")
        if not isinstance(measured, dict):
            continue
        for register in ("link", "heading"):
            node = measured.get(register)
            if not isinstance(node, dict):
                continue
            raw = node.get("fontSize")
            match = re.fullmatch(r"\s*([\d.]+)px\s*", str(raw or ""))
            if match:
                node["fontSizeMeasured"] = raw
                node["fontSize"] = float(match.group(1))
                audit.append({
                    "family": "chrome-measurements",
                    "id": f"{owner}.{register}.fontSize",
                    "owner": "deterministic-contract",
                    "source": f"{owner}.measured.{register}.fontSize",
                    "action": "canonical numeric px shape",
                })


def _canonical_nav_ctas(doc: dict, brand_dir: Path, audit: list[dict]) -> None:
    """Keep only controls measured inside the closed header bar."""
    nav = doc.get("navbar")
    ctas = nav.get("ctas") if isinstance(nav, dict) else None
    if not isinstance(ctas, list) or not ctas:
        return
    computed = _load(brand_dir / "evidence" / "computed-styles.json")
    rects_doc = _load(brand_dir / "evidence" / "section-rects.json")
    header_h = next(
        (float(((row.get("rect") or {}).get("h") or 0))
         for row in (rects_doc.get("chrome") or [])
         if isinstance(row, dict) and row.get("name") == "header"), 0)
    measured_controls = []
    for row in _button_samples(computed):
        rect = ((row.get("measured") or {}).get("_rect") or {})
        classes = str(row.get("classes") or "").lower()
        visible = " ".join(
            str(row.get("visibleLabel") or row.get("sample") or "").split())
        accessible = " ".join(str(row.get("accessibleName") or "").split())
        semantic = " ".join(str(row.get("semanticText") or "").split())
        if visible and header_h and rect.get("y", 9999) < header_h and "nav" in classes:
            measured_controls.append({
                "visibleLabel": visible,
                "accessibleName": accessible or semantic or visible,
                "semanticText": semantic,
                "classes": row.get("classes"),
            })
    if not measured_controls:
        return
    utility_keys = {
        (str(row.get("label") or "").strip().lower(),
         str(row.get("href") or "").strip())
        for row in (nav.get("utility") or []) if isinstance(row, dict)
    }
    kept = []
    for cta in ctas:
        if not isinstance(cta, dict):
            continue
        label = " ".join(str(cta.get("label") or "").split()).lower()
        if (label, str(cta.get("href") or "").strip()) in utility_keys:
            continue
        measured = next((
            row for row in measured_controls
            if label and any(
                label.startswith(candidate[:24]) or candidate.startswith(label[:24])
                for candidate in (
                    str(row.get("visibleLabel") or "").lower(),
                    str(row.get("accessibleName") or "").lower(),
                    str(row.get("semanticText") or "").lower(),
                ) if candidate)
        ), None)
        if measured:
            visible = str(measured["visibleLabel"])
            accessible = str(measured.get("accessibleName") or visible)
            cta["label"] = visible
            if accessible != visible:
                cta["ariaLabel"] = accessible
            else:
                cta.pop("ariaLabel", None)
            cta["labelProvenance"] = {
                "source": "evidence/computed-styles.json",
                "selectorClasses": measured.get("classes"),
                "confidence": "high",
            }
            family = (doc.get("buttons") or {}).get(cta.get("style"))
            if isinstance(family, dict):
                cta.setdefault("bg", family.get("bg"))
                cta.setdefault("color", family.get("fg"))
                cta.setdefault("border", family.get("border"))
                cta.setdefault("borderRadius", family.get("radius"))
                cta.setdefault("height", family.get("height"))
            kept.append(cta)
    if kept and len(kept) < len(ctas):
        nav["ctas"] = kept
        audit.append({
            "family": "navbar", "id": "ctas",
            "owner": "fresh-evidence-projector",
            "source": "evidence/computed-styles.json header control rects",
            "action": "removed dropdown/utility controls from CTA cluster",
        })


def project_chrome_labels(brand_dir: Path, chrome_doc: dict) -> tuple[dict, list[dict]]:
    """Repair authored chrome labels from measured visible/accessibility channels.

    This keeps the staged author artifact itself canonical, not only the merged
    brand projection. The matching is evidence-based and brand-agnostic.
    """
    projected = copy.deepcopy(chrome_doc)
    audit: list[dict] = []
    _canonical_nav_ctas(
        {"navbar": projected.get("navbar") or {}, "buttons": {}},
        Path(brand_dir),
        audit,
    )
    return projected, audit


def project_copy_labels(brand_dir: Path, copy_doc: dict) -> tuple[dict, list[dict]]:
    """Replace action-like semantic text with its measured painted label.

    A sibling ``<key>AriaLabel`` retains the exact longer accessible name. Only
    action-bearing keys are eligible; body/headline prose is never rewritten.
    """
    computed = _load(Path(brand_dir) / "evidence" / "computed-styles.json")
    replacements: dict[str, tuple[str, str]] = {}
    for row in _button_samples(computed):
        visible = " ".join(
            str(row.get("visibleLabel") or row.get("sample") or "").split())
        accessible = " ".join(str(
            row.get("accessibleName") or row.get("semanticText") or ""
        ).split())
        semantic = " ".join(str(row.get("semanticText") or accessible).split())
        if visible and accessible and visible != accessible:
            replacements[semantic] = (visible, accessible)
            replacements[accessible] = (visible, accessible)
    projected = copy.deepcopy(copy_doc)
    changed = 0
    action_keys = {"cta", "ghost", "action", "button", "link"}

    def walk(value: Any) -> None:
        nonlocal changed
        if isinstance(value, dict):
            for key, child in list(value.items()):
                if key in action_keys and isinstance(child, str):
                    normalized = " ".join(child.split())
                    replacement = replacements.get(normalized)
                    if replacement:
                        visible, accessible = replacement
                        value[key] = visible
                        value[f"{key}AriaLabel"] = accessible
                        changed += 1
                        continue
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(projected)
    audit = []
    if changed:
        audit.append({
            "family": "section-copy", "id": "action-labels",
            "owner": "fresh-evidence-projector",
            "source": "evidence/computed-styles.json",
            "action": f"separated {changed} painted labels from accessible names",
        })
    return projected, audit


def _canonical_contract_refs(doc: dict, brand_dir: Path, audit: list[dict]) -> None:
    refs = doc.setdefault("contracts", {})
    for kind in ("primitives", "blocks", "scaffolds"):
        target = CONTRACTS_DIR / f"{kind}.yaml"
        relative = os.path.relpath(target, brand_dir)
        if refs.get(kind) == relative:
            continue
        refs[kind] = relative
        audit.append({
            "family": "contract-references", "id": kind,
            "owner": "deterministic-contract", "source": str(target),
            "action": "canonical relative reference",
        })


def _canonical_wrappers(doc: dict, audit: list[dict]) -> None:
    action = doc.get("actionGroup")
    if isinstance(action, dict) and isinstance(action.get("value"), dict):
        wrapper = action
        doc["actionGroup"] = {
            **copy.deepcopy(wrapper["value"]),
            "origin": "extracted" if wrapper.get("source") in {"grounding", "computed"} else "designed",
            "confidence": wrapper.get("confidence"),
            "provenance": _provenance_from_wrapper(wrapper),
        }
        audit.append({
            "family": "action-group", "id": "default",
            "owner": "deterministic-contract", "source": "staged author wrapper",
            "action": "canonicalized",
        })
    signatures = doc.get("signatures")
    if isinstance(signatures, dict) and isinstance(signatures.get("value"), list):
        doc["signatures"] = copy.deepcopy(signatures["value"])
        audit.append({
            "family": "signatures", "id": "all",
            "owner": "deterministic-contract", "source": "staged author wrapper",
            "action": "canonicalized",
        })
    motion = doc.get("motion")
    if isinstance(motion, dict) and isinstance(motion.get("value"), dict):
        tokens = doc.setdefault("tokens", {})
        tokens.setdefault("motion", copy.deepcopy(motion["value"]))
        audit.append({
            "family": "motion", "id": "tokens.motion",
            "owner": "deterministic-contract", "source": "motion.value",
            "action": "canonicalized",
        })


def _first_mapping(mapping: dict, keys: tuple[str, ...]) -> tuple[str, dict] | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, dict):
            return key, value
    return None


def _canonical_required_tokens(doc: dict, brand_dir: Path, audit: list[dict]) -> None:
    """Fill renderer-required semantic roles by aliasing existing brand facts."""
    tokens = doc.setdefault("tokens", {})
    colors = tokens.setdefault("colors", {})
    css_rules = _load(brand_dir / "evidence" / "css-rules.json")
    declarations = "\n".join(
        str(row.get("decls") or "") for row in (css_rules.get("rules") or [])
        if isinstance(row, dict)
    )

    def css_var(*needles: str) -> str | None:
        for needle in needles:
            match = re.search(
                rf"--[a-z0-9-]*{re.escape(needle)}[a-z0-9-]*\s*:\s*([^;]+)",
                declarations, re.I)
            if match:
                return match.group(1).strip()
        return None

    if "text/secondary" not in colors:
        value = css_var("text-02", "text-secondary")
        if value:
            colors["text/secondary"] = {
                "value": value, "role": "measured secondary ink on light",
                "provenance": {"source": "evidence/css-rules.json", "sourceVariable": "text-02"},
            }
    if "border/subtle" not in colors:
        value = css_var("border-03", "border-subtle", "divider-01")
        if value:
            colors["border/subtle"] = {
                "value": value, "role": "measured subtle control/card border",
                "provenance": {"source": "evidence/css-rules.json", "sourceVariable": "border-03"},
            }
    color_aliases = {
        "text/on-primary": ("text/primary",),
        "text/on-primary-muted": ("text/secondary", "text/muted"),
        "border/hairline-on-primary": ("border/subtle", "border/hairline"),
        "text/ghost-on-primary": ("text/secondary", "text/on-primary-muted"),
    }
    for required, candidates in color_aliases.items():
        if required in colors:
            continue
        source = _first_mapping(colors, candidates)
        if not source:
            continue
        source_key, source_node = source
        colors[required] = {
            **copy.deepcopy(source_node),
            "canonicalAliasOf": source_key,
            "projectionProvenance": "existing measured color role",
        }
        audit.append({
            "family": "tokens.colors", "id": required,
            "owner": "deterministic-contract", "source": f"tokens.colors.{source_key}",
            "action": "semantic alias",
        })

    surfaces = tokens.setdefault("surfaces", {})
    surface_aliases = {
        "surface/panel": ("surface/card", "surface/primary"),
        "surface/inverse-strong": ("surface/inverse-teal", "surface/inverse"),
    }
    for required, candidates in surface_aliases.items():
        if required in surfaces:
            continue
        source = _first_mapping(surfaces, candidates)
        if not source:
            continue
        source_key, source_node = source
        surfaces[required] = {
            **copy.deepcopy(source_node),
            "canonicalAliasOf": source_key,
            "projectionProvenance": "existing measured surface role",
        }
        audit.append({
            "family": "tokens.surfaces", "id": required,
            "owner": "deterministic-contract", "source": f"tokens.surfaces.{source_key}",
            "action": "semantic alias",
        })

    spacing = tokens.setdefault("spacing", {})
    if "panel-padding" not in spacing:
        block_map = doc.get("blocks") if isinstance(doc.get("blocks"), dict) else {}
        card = block_map.get("card")
        values = card.get("paddingPx") if isinstance(card, dict) else None
        raw = values[0] if isinstance(values, list) and values else values
        if raw is not None:
            parts = str(raw).split()
            value = " ".join(
                part if re.search(r"[a-z%]$", part, re.I) else f"{part}px"
                for part in parts
            )
            spacing["panel-padding"] = {
                "value": value,
                "role": "panel inner padding",
                "provenance": {
                    "source": "blocks.card.paddingPx",
                    "confidence": card.get("confidence") or "medium",
                },
            }
            audit.append({
                "family": "tokens.spacing", "id": "panel-padding",
                "owner": "fresh-evidence-projector", "source": "blocks.card.paddingPx",
                "action": "measured role projection",
            })
        else:
            value = css_var("card-interactive-padding", "card-padding")
            if value:
                spacing["panel-padding"] = {
                    "value": value,
                    "role": "measured panel/card inner padding",
                    "provenance": {
                        "source": "evidence/css-rules.json",
                        "sourceVariable": "card-interactive-padding",
                        "confidence": "high",
                    },
                }
    if "radius-global" not in spacing and not (
            isinstance(tokens.get("radius"), dict)
            and isinstance(tokens["radius"].get("global"), dict)
            and tokens["radius"]["global"].get("value")):
        button_map = doc.get("buttons") if isinstance(doc.get("buttons"), dict) else {}
        for name, button in button_map.items():
            if isinstance(button, dict) and button.get("radius"):
                spacing["radius-global"] = {
                    "value": button["radius"],
                    "role": "shared control and component radius",
                    "provenance": {
                        "source": f"buttons.{name}.radius",
                        "confidence": "high",
                    },
                }
                audit.append({
                    "family": "tokens.spacing", "id": "radius-global",
                    "owner": "fresh-evidence-projector",
                    "source": f"buttons.{name}.radius",
                    "action": "measured role projection",
                })
                break

    types = tokens.setdefault("type", {})
    h1 = types.get("h1") if isinstance(types.get("h1"), dict) else None
    h1_tiers = h1.get("tiers") if isinstance(h1, dict) else None
    if (not isinstance(h1_tiers, dict) or len(h1_tiers) < 2) \
            and isinstance(types.get("display-hero"), dict):
        display = copy.deepcopy(h1 or types["display-hero"])
        computed = _load(brand_dir / "evidence" / "computed-styles.json")
        tier_rows = (computed.get("tiers") or {}) if isinstance(computed, dict) else {}
        measured_tiers = {}
        for width, tier in tier_rows.items():
            raw_px = (((tier.get("headings") or {}).get("h1") or {}).get("font-size")
                      if isinstance(tier, dict) else None)
            match = re.fullmatch(r"\s*([\d.]+)px\s*", str(raw_px or ""))
            if match:
                measured_tiers[f"w{width}"] = {
                    "px": float(match.group(1)), "source": "computed"}
        if measured_tiers:
            desktop = measured_tiers.get("w1440") or next(iter(measured_tiers.values()))
            mobile = measured_tiers.get("w375") or desktop
            display["sizeRem"] = {
                "base": desktop["px"] / 16,
                "tablet": (measured_tiers.get("w960") or desktop)["px"] / 16,
                "mobileL": mobile["px"] / 16,
                "mobile": mobile["px"] / 16,
            }
            display["tiers"] = measured_tiers
        display["projectionProvenance"] = "display-hero family + measured h1 tier ladder"
        types["h1"] = display
        audit.append({
            "family": "tokens.type", "id": "h1", "owner": "fresh-evidence-projector",
            "source": "evidence/css-rules.json", "action": "measured role projection",
        })

    meta = doc.setdefault("meta", {})
    if not isinstance(meta.get("canonicalTier"), dict):
        measured = _load(brand_dir / "evidence" / "section-rects.json")
        viewport = (measured.get("viewport") or {}).get("w")
        if viewport:
            meta["canonicalTier"] = {
                "viewport": viewport,
                "note": "canonical values measured from evidence/section-rects.json",
            }

    motion = tokens.get("motion")
    voice = doc.setdefault("voice", {})
    if isinstance(motion, dict):
        raw_durations = motion.get("durations")
        durations = raw_durations if isinstance(raw_durations, dict) else {}
        if isinstance(raw_durations, list) and raw_durations:
            parsed = sorted(
                raw_durations,
                key=lambda value: float(re.search(r"[\d.]+", str(value)).group())
                * (1000 if str(value).strip().endswith("s") and not str(value).strip().endswith("ms") else 1),
            )
            durations = {
                "fast": parsed[0],
                "base": motion.get("dominantDuration") or parsed[len(parsed) // 2],
                "slow": parsed[-1],
            }
            motion["durations"] = copy.deepcopy(durations)
        raw_easings = motion.get("easings")
        easings = raw_easings if isinstance(raw_easings, dict) else {}
        if isinstance(raw_easings, list) and raw_easings:
            easings = {"standard": raw_easings[0]}
            motion["easings"] = copy.deepcopy(easings)
    else:
        durations, easings = {}, {}
    if isinstance(motion, dict) and not isinstance(voice.get("motionSpec"), dict):
        if all(durations.get(k) for k in ("fast", "base", "slow")) and easings:
            voice["motionSpec"] = {
                "durations": {
                    key: durations[key] for key in ("fast", "base", "slow")
                },
                "easing": {
                    "primary": easings.get("standard") or next(iter(easings.values()))
                },
                "projectionProvenance": "tokens.motion",
            }
            audit.append({
                "family": "voice.motionSpec", "id": "motionSpec",
                "owner": "deterministic-contract", "source": "tokens.motion",
                "action": "canonical shape projection",
            })


def project_contract_complete(
    brand_dir: Path, brand_doc: dict, library_doc: dict
) -> tuple[dict, dict, list[dict]]:
    """Return canonical copies and an audit; input mappings are never mutated."""
    doc = copy.deepcopy(brand_doc)
    library = copy.deepcopy(library_doc)
    audit: list[dict] = []
    _canonical_wrappers(doc, audit)
    _canonical_asset_bindings(library, brand_dir, audit)
    _canonical_layouts(doc, library, audit)
    _canonical_catalog_tier(doc, brand_dir, "primitives", "primitives.yaml", audit)
    _canonical_blocks(doc, brand_dir, audit)
    _canonical_catalog_tier(doc, brand_dir, "scaffolds", "scaffolds.yaml", audit)
    _canonical_buttons(doc, brand_dir, audit)
    _canonical_required_tokens(doc, brand_dir, audit)
    _canonical_motion(doc, brand_dir, audit)
    _canonical_spacing(doc, brand_dir, audit)
    _canonical_grid_equalization(library, audit)
    _canonical_narrative(doc, audit)
    _canonical_nav_utility(doc, audit)
    _canonical_nav_ctas(doc, brand_dir, audit)
    _canonical_chrome_measurements(doc, audit)
    _canonical_contract_refs(doc, brand_dir, audit)
    return doc, library, audit


def project_files(brand_dir: Path) -> list[dict]:
    """Project current staged outputs in-place using an atomic caller boundary."""
    brand_path = brand_dir / "brand.yaml"
    library_path = brand_dir / "layout-library.yaml"
    brand = _load(brand_path)
    library = _load(library_path)
    if not isinstance(brand, dict) or not isinstance(library, dict):
        raise ValueError("brand.yaml and layout-library.yaml must be mappings")
    projected, projected_library, audit = project_contract_complete(
        brand_dir, brand, library
    )
    brand_path.write_text(_dump(projected))
    library_path.write_text(_dump(projected_library))
    return audit
