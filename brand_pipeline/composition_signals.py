"""Per-brand composition signals derived from measured layouts.

These are PRESENCE facts for one brand — never universal SaaS composition law.
Consumed by generate_composition (prompt shaping), section_wireframe / composition_lint
(brand-local validation), and compose_from_composition (slot preservation / preferred
archetype / proof-stat licensing).
"""
from __future__ import annotations

from typing import Any

_BESPOKE = {
    "stack", "collage", "split", "media-split", "stack-fullbleed",
    "cards", "interlock", "overlay", "banded",
}
_STAT_CONTRACTS = {"stat", "stat-block", "metric"}
_MEDIA_CONTRACTS = {"image", "media", "photo", "video", "figure"}
_ACTION_CONTRACTS = {"button", "cta", "link", "form", "input"}
_PROOF_CONTRACTS = _STAT_CONTRACTS | {"logo", "logo-strip", "testimonial", "quote", "badge"}


def _slots_of(layout: dict) -> list[dict]:
    """Prefer slots; enrich missing contracts from blockMapping. When only
    blockMapping exists, synthesize slot recipes from it."""
    slots = [s for s in (layout.get("slots") or []) if isinstance(s, dict)]
    mapping = [m for m in (layout.get("blockMapping") or []) if isinstance(m, dict)]
    by_slot: dict[str, dict] = {}
    for m in mapping:
        key = str(m.get("slot") or m.get("role") or "").strip()
        if key:
            by_slot[key] = m
    if slots:
        out = []
        for s in slots:
            item = dict(s)
            key = str(s.get("name") or s.get("role") or "").strip()
            if not item.get("contract") and key in by_slot:
                bm = by_slot[key]
                if bm.get("contract"):
                    item["contract"] = bm["contract"]
                if not item.get("role") and bm.get("role"):
                    item["role"] = bm["role"]
            out.append(item)
        return out
    out = []
    for m in mapping:
        out.append({
            "name": m.get("slot") or m.get("role") or "slot",
            "role": m.get("role") or m.get("slot") or "",
            "contract": m.get("contract") or "paragraph",
        })
    return out


def _band_height_of(layout: dict) -> str | None:
    geom = layout.get("geometry") if isinstance(layout.get("geometry"), dict) else {}
    knobs = layout.get("knobs") if isinstance(layout.get("knobs"), dict) else {}
    responsive = layout.get("responsive") if isinstance(layout.get("responsive"), dict) else {}
    for src in (geom, knobs, layout, responsive):
        for key in ("bandHeight", "heightRule", "height"):
            val = str(src.get(key) or "").strip().lower()
            if val in ("content", "compact", "standard", "tall", "viewport",
                       "viewport-minus-nav"):
                return val
    return None


def signal_for_layout(layout: dict) -> dict[str, Any]:
    """Derive one layout's compositionSignals block from measured evidence only."""
    slots = _slots_of(layout)
    recipe = []
    contracts: list[str] = []
    for s in slots:
        name = str(s.get("name") or s.get("role") or "slot")
        contract = str(s.get("contract") or "paragraph").lower()
        contracts.append(contract)
        recipe.append({
            "name": name,
            "contract": contract,
            "repeatable": bool(s.get("repeatable")) or isinstance(s.get("copy"), list),
        })
    presence = {
        "media": any(c in _MEDIA_CONTRACTS or c.startswith("image") for c in contracts),
        "proof": any(c in _PROOF_CONTRACTS or c.startswith("logo") for c in contracts),
        "stat": any(c in _STAT_CONTRACTS for c in contracts),
        "actions": any(c in _ACTION_CONTRACTS for c in contracts),
        "textOnly": bool(slots) and not any(
            c in _MEDIA_CONTRACTS | _PROOF_CONTRACTS | _ACTION_CONTRACTS
            or c.startswith("image") or c.startswith("logo")
            for c in contracts
        ),
    }
    arch = str(layout.get("archetype") or "").strip().lower()
    preferred = arch if arch in _BESPOKE else None
    band = _band_height_of(layout)
    flush = None
    width_rules = layout.get("widthRules") if isinstance(layout.get("widthRules"), dict) else {}
    if str(width_rules.get("section") or "").lower() in ("full-bleed", "edge-to-edge", "bleed"):
        flush = True
    elif layout.get("flushBands") is True or layout.get("edgeToEdge") is True:
        flush = True

    return {
        "layoutId": layout.get("id"),
        "useCase": layout.get("useCase"),
        "preferredArchetype": preferred,
        "bandHeight": band,
        "flushBands": flush,
        "slotRecipe": recipe,
        "presence": presence,
        "proofRequired": bool(presence.get("proof") or presence.get("stat")),
        "wantsStat": bool(presence.get("stat")),
        "textForward": bool(presence.get("textOnly")),
    }


def extract_composition_signals(doc: dict) -> dict[str, Any]:
    """Build brand-level compositionSignals from ``layouts[]`` (and an existing
    doc-level block when present — measured extract wins per layout id)."""
    existing = doc.get("compositionSignals") if isinstance(doc.get("compositionSignals"), dict) else {}
    by_id: dict[str, dict] = {}
    if isinstance(existing.get("byLayoutId"), dict):
        by_id.update({str(k): v for k, v in existing["byLayoutId"].items()
                      if isinstance(v, dict)})

    layouts = [l for l in (doc.get("layouts") or []) if isinstance(l, dict) and l.get("id")]
    order: list[str] = []
    for layout in layouts:
        lid = str(layout["id"])
        order.append(lid)
        by_id[lid] = signal_for_layout(layout)

    # Page-level presence aggregates (what THIS brand actually uses).
    page_presence = {
        "hasStats": any(s.get("wantsStat") for s in by_id.values()),
        "hasProof": any(s.get("proofRequired") for s in by_id.values()),
        "hasTextForward": any(s.get("textForward") for s in by_id.values()),
        "viewportOpening": any(
            str(s.get("bandHeight") or "") in ("viewport", "viewport-minus-nav", "tall")
            for s in by_id.values()
            if str(s.get("useCase") or "").lower() in ("hero", "opening", "")
            or str(s.get("layoutId") or "").startswith(("opening", "hero", "sec-0"))
        ),
        "flushBands": any(s.get("flushBands") is True for s in by_id.values()),
        "layoutOrder": order,
    }
    return {
        "schemaVersion": "compositionSignals.v1",
        "byLayoutId": by_id,
        "page": page_presence,
    }


def attach_signals_to_doc(doc: dict) -> dict:
    """Return a shallow-copied doc with ``compositionSignals`` derived/updated."""
    out = dict(doc)
    out["compositionSignals"] = extract_composition_signals(doc)
    return out


def signals_for_section(section: dict, doc: dict | None = None) -> dict[str, Any] | None:
    """Resolve the compositionSignals block for one composition section."""
    if isinstance(section.get("_compositionSignals"), dict):
        return section["_compositionSignals"]
    doc = doc or {}
    bag = doc.get("compositionSignals")
    if not isinstance(bag, dict):
        bag = extract_composition_signals(doc) if doc.get("layouts") else {}
    by_id = bag.get("byLayoutId") if isinstance(bag.get("byLayoutId"), dict) else {}
    for key in (section.get("id"), (section.get("seededFrom") or {}).get("id")
                if isinstance(section.get("seededFrom"), dict) else None):
        if key and str(key) in by_id:
            return by_id[str(key)]
    return None


def apply_signals_to_section(section: dict, doc: dict | None = None) -> dict:
    """Stamp ``_compositionSignals`` + brand-local proofRequired on a section."""
    sig = signals_for_section(section, doc)
    if not sig:
        return section
    out = dict(section)
    out["_compositionSignals"] = sig
    out["_preserveAnatomy"] = True
    if "proofRequired" not in out:
        out["proofRequired"] = bool(sig.get("proofRequired")) and not bool(sig.get("textForward"))
    if sig.get("textForward") and "licensedTextOnly" not in out:
        out["licensedTextOnly"] = True
    return out


def render_signals_prompt_block(doc: dict) -> str:
    """Prompt-facing prose for brand-local composition rules. Empty when no layouts."""
    bag = doc.get("compositionSignals")
    if not isinstance(bag, dict) or not bag.get("byLayoutId"):
        if not (doc.get("layouts") or []):
            return ""
        bag = extract_composition_signals(doc)
    page = bag.get("page") or {}
    by_id = bag.get("byLayoutId") or {}
    lines = [
        "## Brand compositionSignals (measured — per THIS brand only)",
        "These are presence facts from the brand's layouts. Do NOT apply SaaS defaults",
        "(forced full-height hero, inventing stats, mandatory visual anchors) that this",
        "brand does not evidence. When reusing a layout id below, KEEP its slot recipe",
        "and order; invent freely only for sections absent from this inventory.",
    ]
    if page.get("layoutOrder"):
        lines.append("Measured section order: " + " → ".join(str(x) for x in page["layoutOrder"]))
    lines.append(
        f"Page presence: stats={bool(page.get('hasStats'))} "
        f"proof={bool(page.get('hasProof'))} "
        f"textForward={bool(page.get('hasTextForward'))} "
        f"viewportOpening={bool(page.get('viewportOpening'))} "
        f"flushBands={bool(page.get('flushBands'))}"
    )
    for lid, sig in list(by_id.items())[:24]:
        recipe = sig.get("slotRecipe") or []
        slot_s = ", ".join(
            f"{s.get('name')}:{s.get('contract')}" for s in recipe[:8] if isinstance(s, dict)
        ) or "(no slots)"
        lines.append(
            f"- `{lid}` useCase={sig.get('useCase') or '—'} "
            f"archetype={sig.get('preferredArchetype') or '—'} "
            f"bandHeight={sig.get('bandHeight') or 'content'} "
            f"textForward={bool(sig.get('textForward'))} "
            f"proofRequired={bool(sig.get('proofRequired'))} "
            f"slots=[{slot_s}]"
        )
    if len(by_id) > 24:
        lines.append(f"- … {len(by_id) - 24} more layouts omitted")
    return "\n".join(lines)
