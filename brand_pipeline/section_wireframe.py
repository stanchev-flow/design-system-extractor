#!/usr/bin/env python3
"""Deterministic page wireframing between copy intent and composition rendering.

``wireframe.v1`` records page cadence and each section's semantic skeleton before
the renderer sees primitives.  It is deliberately brand-agnostic: choices are
derived from copy shape, section job, declared brand pattern provenance, and
available media—not from brand names, colors, or page-specific CSS.
"""
from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path

import yaml


SCHEMA_VERSION = "wireframe.v1"
ACTION_CONTRACTS = {"button", "cta", "form", "input"}
MEDIA_CONTRACTS = {"image", "video"}
PROOF_CONTRACTS = {"stat", "stat-block", "testimonial", "quote", "logo", "logo-bar"}
ITEM_CONTRACTS = {"feature-item", "content-block", "card", "testimonial"}
TEXT_CONTRACTS = {"heading", "header", "eyebrow", "paragraph", "caption", "label"}
TESTIMONIAL_CONTRACTS = {"testimonial", "quote"}
DEFAULT_CONTAINER_WIDTH = 1080.0
DEFAULT_GUTTER = 32.0
DEFAULT_ITEM_PADDING = 32.0
FILL_STRATEGIES = {
    "complete-rows", "lead-span", "tail-span", "single-column",
    "licensed-asymmetry",
}


class WireframeError(ValueError):
    """A wireframe decision cannot be consumed or violates page rhythm."""


def _slots(section: dict) -> list[dict]:
    return [s for s in (section.get("slots") or []) if isinstance(s, dict)]


def _copy_items(slot: dict) -> list[dict]:
    value = slot.get("copy")
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _has_asset(value) -> bool:
    if not isinstance(value, dict):
        return False
    asset = value.get("asset")
    if isinstance(asset, str):
        return bool(asset.strip())
    return isinstance(asset, dict) and bool(str(asset.get("src") or "").strip())


def _slot_has_visual(slot: dict) -> bool:
    contract = str(slot.get("contract") or "").lower()
    if contract in MEDIA_CONTRACTS | PROOF_CONTRACTS | ACTION_CONTRACTS:
        return True
    if _has_asset(slot):
        return True
    return any(_has_asset(item) for item in _copy_items(slot))


def _length_px(value, default: float) -> float:
    """Resolve a conservative CSS length without evaluating arbitrary CSS."""
    if isinstance(value, (int, float)):
        return float(value)
    match = re.fullmatch(r"\s*([\d.]+)\s*(px|rem|em)?\s*", str(value or ""))
    if not match:
        return default
    amount = float(match.group(1))
    return amount * 16.0 if match.group(2) in {"rem", "em"} else amount


def _brand_context(composition: dict, brand_dir: Path | str | None = None) -> tuple[dict, dict | None]:
    """Load optional measured brand/layout and media facts; silence stays generic."""
    root = Path(brand_dir) if brand_dir else None
    ref = str(((composition.get("brand") or {}).get("ref") or "")).strip()
    brand_path = Path(ref) if ref else None
    if root is None and brand_path:
        root = brand_path.parent
    doc: dict = {}
    if brand_path and brand_path.exists():
        try:
            doc = yaml.safe_load(brand_path.read_text()) or {}
        except Exception:
            doc = {}
    registry = None
    if root:
        media_path = root / "media-assets.yaml"
        if media_path.exists():
            try:
                loaded = yaml.safe_load(media_path.read_text())
                registry = loaded if isinstance(loaded, dict) else None
            except Exception:
                registry = None
    return doc, registry


def _deep_values(value, key: str):
    if isinstance(value, dict):
        for name, child in value.items():
            if name == key:
                yield child
            yield from _deep_values(child, key)
    elif isinstance(value, list):
        for child in value:
            yield from _deep_values(child, key)


def _container_width(brand: dict) -> float:
    for key in ("contentMaxWidth", "container-max"):
        for value in _deep_values(brand, key):
            width = _length_px(value.get("value") if isinstance(value, dict) else value, 0)
            if width >= 480:
                return width
    return DEFAULT_CONTAINER_WIDTH


def _project_lines(text: str, measure_ch: float) -> int:
    """Greedy word-wrap projection, shared in spirit with AS-66 heading fitting."""
    words = [w for w in str(text or "").split() if w]
    if not words:
        return 0
    lines, used = 1, 0
    cap = max(1, int(measure_ch))
    for word in words:
        width = max(1, len(word))
        if used and used + 1 + width > cap:
            lines += 1
            used = width
        else:
            used = width if not used else used + 1 + width
    return lines


def content_demand(item: dict, *, padding_px: float = DEFAULT_ITEM_PADDING) -> dict:
    """Brand-agnostic component demand from semantic roles and visible copy shape."""
    heading = str(item.get("heading") or item.get("title") or "")
    body = str(item.get("text") or item.get("body") or item.get("quote") or "")
    # Only visible copy creates text demand. Asset filenames/ids are not painted
    # tokens and must never force a wider track.
    strings = [
        str(item.get(key) or "") for key in (
            "eyebrow", "heading", "title", "text", "body", "quote",
            "action", "cta", "name", "role", "company",
        )
    ]
    tokens = re.findall(r"\S+", " ".join(strings))
    roles = [key for key in (
        "asset", "icon", "eyebrow", "heading", "title", "text", "body",
        "quote", "action", "cta", "name", "role", "company",
    ) if item.get(key)]
    longest = max((len(t) for t in tokens), default=0)
    max_heading_lines = 3
    max_body_lines = 5
    preferred_ch = 28 if len(body) >= 64 else 24
    # A line-cap-derived floor plus the preferred reading measure. Long
    # unbreakable tokens always win; padding belongs to the outer item box.
    content_px = max(
        preferred_ch * 8.0,
        longest * 8.0,
        math.ceil(len(heading) / max_heading_lines) * 8.8 if heading else 0,
        math.ceil(len(body) / max_body_lines) * 7.8 if body else 0,
    )
    return {
        "headingChars": len(heading),
        "bodyChars": len(body),
        "longestUnbreakableToken": longest,
        "childRoles": roles,
        "preferredMeasureCh": preferred_ch,
        "maxHeadingLines": max_heading_lines,
        "maxBodyLines": max_body_lines,
        "minItemWidth": round(content_px + 2 * padding_px, 1),
    }


def _explicit_priority(item: dict) -> int:
    """Return authored hierarchy only; copy order alone never invents a lead."""
    hierarchy = str(item.get("hierarchy") or item.get("prominence") or "").lower()
    if item.get("lead") is True or hierarchy == "lead":
        return 2
    if item.get("primary") is True or hierarchy == "primary":
        return 1
    return 0


def _real_counterweight(value) -> dict | None:
    """Normalize a licensed asymmetry counterweight with a painted role."""
    if not isinstance(value, dict):
        return None
    role = str(value.get("role") or value.get("contract") or "").strip()
    if not role:
        return None
    if not any(value.get(key) for key in ("asset", "contract", "component", "visual")):
        return None
    return copy.deepcopy(value)


def _solve_grid_fill(items: list[dict], fit: dict, slot: dict) -> dict:
    """Choose a row-complete fill strategy after AS-75 chooses feasible tracks."""
    item_count = len(items)
    columns = int(fit["chosenColumns"])
    preferred = float(fit.get("preferredMeasureCh") or 24)
    full_inner_ch = max(
        1.0,
        (float(fit.get("availableWidth") or 0)
         - 2 * float(fit.get("itemPadding") or 0)) / 8.0,
    )
    priorities = [_explicit_priority(item) for item in items]
    strongest = max(priorities, default=0)
    lead_indices = [i for i, value in enumerate(priorities) if value == strongest and value > 0]
    unique_lead = lead_indices[0] if len(lead_indices) == 1 else None
    demands = fit.get("contentDemand") or []
    demand_scores = [
        round(
            float(demand.get("headingChars") or 0)
            + float(demand.get("bodyChars") or 0)
            + (24 if any(item.get(key) for key in ("asset", "icon")) else 0),
            1,
        )
        for item, demand in zip(items, demands)
    ]
    candidates: list[dict] = []

    for width_candidate in fit.get("candidateWidths") or []:
        candidate_columns = int(width_candidate.get("columns") or 0)
        if candidate_columns <= columns:
            continue
        candidates.append({
            "strategy": "higher-columns",
            "columns": candidate_columns,
            "feasible": bool(width_candidate.get("feasible"))
                        and item_count % candidate_columns == 0,
            "score": 100 if width_candidate.get("feasible") else 0,
            "reasons": list(width_candidate.get("reasons") or [])
                       or (["higher track count leaves a partial final row"]
                           if item_count % candidate_columns else []),
        })

    if columns <= 1:
        candidates.append({
            "strategy": "single-column", "columns": 1, "feasible": True,
            "score": 100, "reasons": ["AS-75 selected one feasible track"],
        })
        return {
            "columns": 1, "strategy": "single-column", "spans": [1] * item_count,
            "candidates": candidates, "contentMeasureCh": None,
            "balancingCounterweight": None,
        }

    if item_count % columns == 0:
        candidates.append({
            "strategy": "complete-rows", "columns": columns, "feasible": True,
            "score": 100, "reasons": ["item count fills every selected track"],
        })
        return {
            "columns": columns, "strategy": "complete-rows",
            "spans": [1] * item_count, "candidates": candidates,
            "contentMeasureCh": None, "balancingCounterweight": None,
        }

    asymmetry = slot.get("licensedAsymmetry")
    counterweight = _real_counterweight(
        asymmetry.get("counterweight") if isinstance(asymmetry, dict) else None)
    licensed = isinstance(asymmetry, dict) and asymmetry.get("licensed") is True \
        and counterweight is not None
    candidates.append({
        "strategy": "licensed-asymmetry", "columns": columns,
        "feasible": licensed, "score": 95 if licensed else 0,
        "reasons": (["explicit license includes a painted balancing counterweight"]
                    if licensed else
                    ["partial rows require an explicit license and real balancing counterweight"]),
    })
    if licensed:
        return {
            "columns": columns, "strategy": "licensed-asymmetry",
            "spans": [1] * item_count, "candidates": candidates,
            "contentMeasureCh": None, "balancingCounterweight": counterweight,
        }

    span_fills = (item_count - 1) % columns == 0

    def span_candidate(strategy: str, index: int, hierarchy_ok: bool, hierarchy_reason: str):
        visual = any(items[index].get(key) for key in ("asset", "icon"))
        excessive = full_inner_ch > preferred * 1.8 and not visual
        feasible = span_fills and hierarchy_ok and not excessive
        score = (
            78
            + (18 if strategy == "lead-span" and unique_lead == index else 0)
            + (8 if visual else 0)
            + min(8, int((demand_scores[index] if demand_scores else 0) / 40))
            - (10 if full_inner_ch > preferred * 1.8 else 0)
        )
        reasons = []
        if not span_fills:
            reasons.append("removing one spanning item still leaves a partial row")
        if not hierarchy_ok:
            reasons.append(hierarchy_reason)
        if excessive:
            reasons.append(
                f"full-span inner measure {full_inner_ch:.1f}ch is excessive "
                f"for {preferred:.1f}ch preferred measure without a visual counterweight")
        if feasible and full_inner_ch > preferred:
            reasons.append(
                f"constrain full-span content to {preferred:.1f}ch inside the filled card")
        candidates.append({
            "strategy": strategy, "columns": columns, "targetIndex": index,
            "feasible": feasible, "score": score if feasible else 0,
            "reasons": reasons,
            "hierarchy": priorities,
            "demandScores": demand_scores,
            "fullSpanInnerMeasureCh": round(full_inner_ch, 1),
            "preferredMeasureCh": round(preferred, 1),
        })

    span_candidate(
        "lead-span", unique_lead if unique_lead is not None else 0,
        unique_lead is not None,
        "lead-span requires one explicitly strongest lead/primary item",
    )
    span_candidate(
        "tail-span", item_count - 1, unique_lead is None,
        "tail-span is reserved for peer items without a unique lead",
    )
    widest_without_visual = full_inner_ch > preferred * 1.8 and not any(
        any(item.get(key) for key in ("asset", "icon")) for item in items)
    single_score = 72 + (22 if widest_without_visual else 0)
    candidates.append({
        "strategy": "single-column", "columns": 1, "feasible": True,
        "score": single_score,
        "reasons": (["stacked reading avoids an excessively wide unbalanced span"]
                    if widest_without_visual else
                    ["row-complete fallback with the strongest stacked reading order"]),
    })
    feasible = [candidate for candidate in candidates if candidate.get("feasible")]
    chosen = max(feasible, key=lambda candidate: (candidate.get("score", 0),
                                                   candidate["strategy"] != "single-column"))
    strategy = chosen["strategy"]
    chosen_columns = int(chosen["columns"])
    spans = [1] * item_count
    measure = None
    if strategy in {"lead-span", "tail-span"}:
        spans[int(chosen["targetIndex"])] = chosen_columns
        measure = round(preferred, 1)
    return {
        "columns": chosen_columns, "strategy": strategy, "spans": spans,
        "candidates": candidates, "contentMeasureCh": measure,
        "balancingCounterweight": None,
    }


def _available_collection_width(section: dict, container_width: float, gutter: float) -> tuple[float, str]:
    """Account for a sibling intro rail before solving the collection's own tracks."""
    slots = _slots(section)
    collection_names = {
        str(s.get("name") or s.get("role") or "") for s in slots if len(_copy_items(s)) >= 2
    }
    counter = str((section.get("alignment") or {}).get("counterweight") or "")
    has_intro = any(str(s.get("contract") or "").lower() in TEXT_CONTRACTS for s in slots)
    if counter in collection_names and has_intro:
        # Generic split grammar: copy rail + column gutter + larger counterweight.
        # This is a feasibility allocation, not a rendered fixed fraction.
        return max(280.0, container_width * 0.60 - gutter), "counterweight-column"
    return container_width, "full-container"


def solve_collection_fit(
    section: dict,
    slot: dict,
    *,
    container_width: float = DEFAULT_CONTAINER_WIDTH,
    gutter: float = DEFAULT_GUTTER,
    item_padding: float = DEFAULT_ITEM_PADDING,
) -> dict:
    """Choose the maximum feasible track count and one coherent family anatomy."""
    items = _copy_items(slot)
    requested = max(1, int(str(((section.get("knobs") or {}).get("columns") or 1))))
    max_columns = min(requested, len(items))
    available, allocation = _available_collection_width(section, container_width, gutter)
    demands = [content_demand(item, padding_px=item_padding) for item in items]
    family_min = max((d["minItemWidth"] for d in demands), default=0)
    candidates = []
    chosen = 1
    chosen_width = available
    selected = False
    for columns in range(max_columns, 0, -1):
        item_width = (available - gutter * (columns - 1)) / columns
        inner = max(1.0, item_width - 2 * item_padding)
        measure_ch = inner / 8.0
        reasons = []
        if item_width + 0.5 < family_min:
            reasons.append(f"item width {item_width:.1f}px < family minimum {family_min:.1f}px")
        for index, (item, demand) in enumerate(zip(items, demands), 1):
            h_lines = _project_lines(item.get("heading") or item.get("title") or "", measure_ch)
            b_lines = _project_lines(
                item.get("text") or item.get("body") or item.get("quote") or "", measure_ch)
            if h_lines > demand["maxHeadingLines"]:
                reasons.append(f"item {index} heading projects to {h_lines} lines")
            if b_lines > demand["maxBodyLines"]:
                reasons.append(f"item {index} body projects to {b_lines} lines")
            if demand["longestUnbreakableToken"] > measure_ch:
                reasons.append(f"item {index} longest token exceeds measure")
        feasible = not reasons
        candidates.append({
            "columns": columns,
            "itemWidth": round(item_width, 1),
            "innerMeasureCh": round(measure_ch, 1),
            "feasible": feasible,
            "reasons": reasons,
        })
        if feasible and not selected:
            chosen, chosen_width = columns, item_width
            selected = True
    has_icons = any(any(item.get(k) for k in ("asset", "icon")) for item in items)
    # Inline marks spend horizontal measure and create cross-item baseline drift.
    # License them only when every item remains comfortably inside its line caps.
    inline_measure = max(1.0, (chosen_width - 2 * item_padding - 48.0) / 8.0)
    inline_ok = has_icons and chosen_width >= family_min + 48.0 and all(
        _project_lines(item.get("heading") or item.get("title") or "", inline_measure) <= 2
        and _project_lines(item.get("text") or item.get("body") or "", inline_measure) <= 4
        for item in items
    )
    anatomy = "icon-inline" if inline_ok else ("icon-top" if has_icons else "text-stack")
    collapse_at = round(max(320.0, family_min), 1)
    breakpoints = [{"minContainerWidth": collapse_at, "columns": 1}]
    if chosen >= 2:
        breakpoints.append({
            "minContainerWidth": round(chosen * family_min + (chosen - 1) * gutter, 1),
            "columns": chosen,
        })
    fit = {
        "contentDemand": demands,
        "containerWidth": round(container_width, 1),
        "availableWidth": round(available, 1),
        "allocation": allocation,
        "gutter": round(gutter, 1),
        "itemPadding": round(item_padding, 1),
        "minItemWidth": round(family_min, 1),
        "preferredMeasureCh": max((d["preferredMeasureCh"] for d in demands), default=24),
        "maxHeadingLines": max((d["maxHeadingLines"] for d in demands), default=3),
        "maxBodyLines": max((d["maxBodyLines"] for d in demands), default=5),
        "requestedColumns": requested,
        "candidateWidths": candidates,
        "chosenColumns": chosen,
        "internalAnatomy": anatomy,
        "familyAnatomyUniform": True,
        "responsiveBreakpoints": sorted(breakpoints, key=lambda row: row["minContainerWidth"]),
    }
    fill = _solve_grid_fill(items, fit, slot)
    fit["chosenColumns"] = fill["columns"]
    fit["fillStrategy"] = fill["strategy"]
    fit["fillCandidates"] = fill["candidates"]
    fit["itemSpans"] = fill["spans"]
    fit["fullSpanContentMeasureCh"] = fill["contentMeasureCh"]
    fit["balancingCounterweight"] = fill["balancingCounterweight"]
    if fill["columns"] != chosen:
        fit["responsiveBreakpoints"] = [
            {"minContainerWidth": round(max(320.0, family_min), 1), "columns": 1}
        ]
    return fit


def _testimonial_plan(section: dict, registry: dict | None, brand: dict) -> dict | None:
    slot = next((s for s in _slots(section)
                 if str(s.get("contract") or "").lower() in TESTIMONIAL_CONTRACTS), None)
    if not slot and str(section.get("useCase") or "").lower() != "testimonial":
        return None
    copy_value = (slot or {}).get("copy")
    if not isinstance(copy_value, dict):
        return {
            "componentContract": "testimonial",
            "complete": False,
            "missing": ["structured quote and attribution"],
        }
    quote = str(copy_value.get("quote") or copy_value.get("text") or "").strip()
    name = str(copy_value.get("name") or copy_value.get("author") or "").strip()
    role = str(copy_value.get("role") or copy_value.get("company") or "").strip()
    asset = copy_value.get("avatar") or copy_value.get("media") or copy_value.get("asset")
    if isinstance(asset, dict):
        asset = asset.get("src")
    asset = str(asset or "").strip()
    source = "composition" if asset else ""
    matched_kind = ""
    if not asset and registry:
        haystack = f"{name} {role}".lower()
        for entry in registry.get("assets") or []:
            if not isinstance(entry, dict):
                continue
            semantics = entry.get("assetSemantics") or {}
            facts = entry.get("facts") or {}
            kind = str(semantics.get("kind") or "")
            if kind not in {"avatar", "portrait", "client-photo", "team-photo", "photograph"}:
                continue
            labels = " ".join([
                str(semantics.get("subject") or ""),
                str(facts.get("altHarvested") or ""),
                str(entry.get("id") or ""),
            ]).lower()
            terms = [t for t in re.findall(r"[a-z0-9]+", haystack) if len(t) >= 4]
            if any(term in labels for term in terms):
                asset = str(entry.get("file") or "")
                matched_kind = kind
                source = "media-assets-subject-match"
                break
    if not matched_kind and asset and registry:
        for entry in registry.get("assets") or []:
            if Path(str(entry.get("file") or "")).name == Path(asset).name:
                matched_kind = str((entry.get("assetSemantics") or {}).get("kind") or "")
                break
    if asset:
        anatomy = "avatar-top" if matched_kind in {"avatar", "portrait"} else "portrait-side"
        asset_status = "bound"
        request = None
    else:
        anatomy = "quote-card"
        asset_status = "requested"
        request = {
            "role": "testimonial portrait or client-context image",
            "reason": "no compatible extracted subject asset",
            "fallback": "brand-legal no-photo quote card",
        }
    accent_devices = brand.get("accentDevices") or []
    accent_licensed = any(
        isinstance(device, dict) and str(device.get("kind") or "") in {
            "punctuation-accent", "underline-accent", "marked-list-glyph"}
        for device in accent_devices
    )
    return {
        "componentContract": "testimonial",
        "complete": bool(quote and (name or role)),
        "quote": quote,
        "attribution": {"name": name, "role": role},
        "asset": asset or None,
        "assetStatus": asset_status,
        "assetSource": source or None,
        "assetRequest": request,
        "internalAnatomy": anatomy,
        "optionalRoles": [
            key for key in ("stat", "result", "logo", "action", "cta") if copy_value.get(key)
        ],
        "preferredMeasureCh": 58,
        "minComponentWidth": 480,
        "maxEmptySpaceRatio": 0.68,
        "accentLicensed": accent_licensed,
    }


def _collection(slot: dict, section: dict, fit_context: dict) -> dict | None:
    items = _copy_items(slot)
    if len(items) < 2:
        return None
    contract = str(slot.get("contract") or "").lower()
    shape = any(
        any(str(item.get(k) or "").strip() for k in ("eyebrow", "heading", "title"))
        and any(str(item.get(k) or "").strip() for k in ("text", "body", "action", "cta"))
        for item in items
    )
    if contract not in ITEM_CONTRACTS and not shape:
        return None
    fit = solve_collection_fit(section, slot, **fit_context)
    columns = fit["chosenColumns"]
    planned_items = copy.deepcopy(items)
    for item, span in zip(planned_items, fit.get("itemSpans") or []):
        item["span"] = span
        if span > 1 and fit.get("fullSpanContentMeasureCh"):
            item["contentMeasureCh"] = fit["fullSpanContentMeasureCh"]
    return {
        "slot": str(slot.get("name") or slot.get("role") or "items"),
        "itemContract": contract if contract in ITEM_CONTRACTS else "content-block",
        "items": planned_items,
        "layout": "grid" if columns > 1 else "stacked-list",
        "columns": max(1, columns),
        "wrap": True,
        "fillStrategy": fit["fillStrategy"],
        "fillCandidates": fit["fillCandidates"],
        "balancingCounterweight": fit.get("balancingCounterweight"),
        "componentFit": fit,
        "responsive": {
            "mobileColumns": 1,
            "collapse": "preserve-item",
            "breakpoints": fit["responsiveBreakpoints"],
        },
    }


def renderer_capability(section: dict, slot: dict) -> tuple[bool, str]:
    """Return whether the selected renderer has a consuming path for ``slot``.

    This registry describes real adapter/composer paths.  In particular, a card
    carrying media in a split is unsupported unless the case-card adapter stamp is
    present; that is the exact class that previously dropped hero photography.
    """
    archetype = str(section.get("archetype") or "stack").lower()
    contract = str(slot.get("contract") or "").lower()
    repeated = len(_copy_items(slot)) > 1
    role = str(slot.get("role") or "").lower()

    if archetype == "cards":
        if repeated and contract not in ITEM_CONTRACTS:
            return False, "cards collections require feature-item/content-block/card/testimonial"
        return True, "cards adapter + grouped module renderer"
    if archetype == "split" and contract == "card":
        if _has_asset(slot) or any(_has_asset(x) for x in _copy_items(slot)):
            return True, "split single-case adapter + case-card renderer"
        return False, "split card has no painted media or proof payload"
    if archetype == "split" and repeated and contract in {"list", "content-block"}:
        return False, "split renderer has no grouped collection consumer"
    if repeated and contract == "list":
        return False, "generic list expansion would flatten semantic records"
    if contract in TEXT_CONTRACTS | ACTION_CONTRACTS | MEDIA_CONTRACTS | PROOF_CONTRACTS:
        return True, "shared primitive/block renderer"
    if contract in ITEM_CONTRACTS:
        return archetype == "cards", "item contracts require the cards collection path"
    return False, f"no registered consumer for contract {contract!r} in {archetype!r}"


def plan_wireframe(composition: dict, brand_dir: Path | str | None = None) -> dict:
    """Build a deterministic, machine-checkable whole-page ``wireframe.v1``."""
    brand, registry = _brand_context(composition, brand_dir)
    container_width = _container_width(brand)
    fit_context = {
        "container_width": container_width,
        "gutter": DEFAULT_GUTTER,
        "item_padding": DEFAULT_ITEM_PADDING,
    }
    planned = []
    sparse_run = 0
    for index, section in enumerate(composition.get("sections") or []):
        if not isinstance(section, dict):
            continue
        slots = _slots(section)
        sid = str(section.get("id") or f"section-{index + 1}")
        use_case = str(section.get("useCase") or "features").lower()
        collections = [c for c in (_collection(s, section, fit_context) for s in slots) if c]
        testimonial = _testimonial_plan(section, registry, brand)
        actions = [str(s.get("name") or s.get("role") or "action") for s in slots
                   if str(s.get("contract") or "").lower() in ACTION_CONTRACTS]
        proof = [str(s.get("name") or s.get("role") or "proof") for s in slots
                 if str(s.get("contract") or "").lower() in PROOF_CONTRACTS]
        visuals = [str(s.get("name") or s.get("role") or "visual") for s in slots
                   if _slot_has_visual(s)]
        if collections:
            visuals += [f"component-cluster:{c['slot']}" for c in collections]
        text_only = not visuals and not collections
        sparse_run = sparse_run + 1 if text_only else 0

        required = []
        capabilities = []
        for slot in slots:
            if slot.get("copy") in (None, "", []):
                continue
            name = str(slot.get("name") or slot.get("role") or "slot")
            required.append(name)
            ok, path = renderer_capability(section, slot)
            capabilities.append({"slot": name, "consumable": ok, "path": path})

        density = "dense" if len(slots) >= 4 or len(collections) else (
            "open" if len(slots) <= 2 else "balanced")
        conversion = "primary" if use_case == "cta" else ("supporting" if actions else "none")
        job = {
            "hero": "orient-and-prove",
            "testimonial": "human-proof",
            "logos": "scale-proof",
            "cta": "convert",
        }.get(use_case, "explain-or-prove")
        planned.append({
            "id": sid,
            "index": index,
            "job": job,
            "density": density,
            "surfaceRole": str(section.get("surfaceIntent") or "primary"),
            "visualAnchor": visuals,
            "conversionRole": conversion,
            "skeleton": str(section.get("archetypeRef") or section.get("archetype") or "stack"),
            "componentFamily": "collection" if collections else use_case,
            "structureProvenance": str(
                section.get("structureProvenance")
                or ("measured-brand-pattern" if section.get("seededFrom")
                    else "brand-style-archetype")
            ),
            "structureRecipeId": section.get("structureRecipeId"),
            "requiredSlots": required,
            "optionalSlots": [],
            "ctaRequired": use_case == "cta",
            "proofRequired": use_case in {"hero", "testimonial", "logos"},
            "collections": collections,
            "testimonial": testimonial,
            "responsive": {"collapse": "single-column", "preserveGrouping": True},
            "assetRequirements": [
                {"slot": str(s.get("name") or "media"), "status": "bound"}
                for s in slots if _slot_has_visual(s)
            ],
            "assetRequests": [
                {"slot": str(s.get("name") or "media"), **s["noCompatibleAsset"]}
                for s in slots if isinstance(s.get("noCompatibleAsset"), dict)
            ],
            "rendererCapabilities": capabilities,
            "licensedTextOnly": False,
            "sparseRun": sparse_run,
        })

    return {
        "schemaVersion": SCHEMA_VERSION,
        "page": {
            "storyRhythm": [s["job"] for s in planned],
            "densitySequence": [s["density"] for s in planned],
            "surfaceSequence": [s["surfaceRole"] for s in planned],
            "maxConsecutiveTextOnly": 1,
            "brandPrecedence": [
                "measured-pattern-or-recipe",
                "designed-from-brand-component-or-pattern",
                "brand-style-archetype",
                "relume-structural-fallback",
            ],
        },
        "sections": planned,
    }


def validate_wireframe(wireframe: dict, composition: dict | None = None) -> list[str]:
    """Return hard wireframe/consumption failures; empty means buildable."""
    errors: list[str] = []
    if wireframe.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {SCHEMA_VERSION}")
    sections = [s for s in (wireframe.get("sections") or []) if isinstance(s, dict)]
    for section in sections:
        sid = section.get("id") or "section"
        if section.get("structureProvenance") == "relume-fallback" and not section.get(
            "structureRecipeId"
        ):
            errors.append(f"{sid}: Relume fallback lacks structureRecipeId")
        bad = [c for c in (section.get("rendererCapabilities") or [])
               if isinstance(c, dict) and not c.get("consumable")]
        errors += [f"{sid}: required slot {c.get('slot')} is not consumable: {c.get('path')}"
                   for c in bad]
        if not section.get("visualAnchor") and not section.get("licensedTextOnly"):
            errors.append(f"{sid}: substantive section has no visual anchor/component cluster")
        if section.get("ctaRequired") and not section.get("conversionRole") == "primary":
            errors.append(f"{sid}: conversion section lacks a primary conversion role")
        for collection in section.get("collections") or []:
            if collection.get("itemContract") not in ITEM_CONTRACTS:
                errors.append(f"{sid}: collection itemContract is not a grouped component")
            if not isinstance(collection.get("items"), list) or len(collection["items"]) < 2:
                errors.append(f"{sid}: collection must preserve repeated semantic items")
            if ((collection.get("responsive") or {}).get("collapse") != "preserve-item"):
                errors.append(f"{sid}: responsive collection must preserve item grouping")
            fit = collection.get("componentFit") or {}
            if fit.get("chosenColumns") != collection.get("columns"):
                errors.append(f"{sid}: collection columns bypass component-fit decision")
            if not any(c.get("feasible") for c in fit.get("candidateWidths") or []):
                errors.append(f"{sid}: no feasible collection track count")
            if fit.get("internalAnatomy") not in {"icon-top", "icon-inline", "media-top", "text-stack"}:
                errors.append(f"{sid}: collection has no coherent internal anatomy")
            strategy = str(collection.get("fillStrategy") or "")
            if strategy not in FILL_STRATEGIES:
                errors.append(f"{sid}: collection has no declared grid-fill strategy")
            columns = max(1, int(collection.get("columns") or 1))
            spans = [int(item.get("span") or 1) for item in collection.get("items") or []]
            if strategy == "licensed-asymmetry":
                if _real_counterweight(collection.get("balancingCounterweight")) is None:
                    errors.append(
                        f"{sid}: licensed asymmetry lacks a real balancing counterweight")
            else:
                used = 0
                orphan = False
                for span in spans:
                    if span < 1 or span > columns:
                        orphan = True
                        break
                    if used and used + span > columns:
                        orphan = True
                        break
                    used = (used + span) % columns
                if used or orphan:
                    errors.append(
                        f"{sid}: collection leaves an orphan final-row void")
            if fit.get("fillStrategy") != strategy or fit.get("itemSpans") != spans:
                errors.append(f"{sid}: collection bypasses component-fit grid-fill decision")
        testimonial = section.get("testimonial")
        if testimonial is not None:
            if testimonial.get("componentContract") != "testimonial":
                errors.append(f"{sid}: testimonial intent must select testimonial component")
            if not testimonial.get("complete"):
                errors.append(f"{sid}: testimonial requires quote plus attribution")
            if testimonial.get("assetStatus") not in {"bound", "requested"}:
                errors.append(f"{sid}: testimonial media must bind or emit an asset request")
    for left, right in zip(sections, sections[1:]):
        if (not left.get("visualAnchor") and not left.get("licensedTextOnly")
                and not right.get("visualAnchor") and not right.get("licensedTextOnly")):
            errors.append(f"{left.get('id')}→{right.get('id')}: consecutive visually empty sections")

    if composition is not None:
        by_id = {str(s.get("id")): s for s in composition.get("sections") or []
                 if isinstance(s, dict)}
        for section in sections:
            comp = by_id.get(str(section.get("id")))
            names = {str(s.get("name") or s.get("role") or "slot") for s in _slots(comp or {})}
            missing = [name for name in section.get("requiredSlots") or [] if name not in names]
            errors += [f"{section.get('id')}: required wireframe slot {name!r} not consumed"
                       for name in missing]
    return errors


def write_wireframe(path: Path | str, composition: dict) -> dict:
    wireframe = plan_wireframe(composition)
    errors = validate_wireframe(wireframe, composition)
    if errors:
        raise WireframeError("\n".join(errors))
    Path(path).write_text(json.dumps(wireframe, indent=2) + "\n")
    return wireframe
