#!/usr/bin/env python3
"""designed_components.py — GENERIC synthesis of DESIGNED (synthesized-from-brand-
signals) provenance for standard-catalog components a brand did NOT measure.

A brand's harness should be COMPLETE: every standard-catalog component (the
universal primitives/blocks/scaffolds vocabulary in ``contracts/``) is present in
the catalog view, tagged either

  • ``extracted`` — measured on the live source page (grounded fact), or
  • ``designed``  — SYNTHESIZED on-brand from the brand's OWN measured signals
                    (tokens, type scale, spacing ladder, radius/border/shadow
                    grammar, button + actionGroup facts, surface grammar, measured
                    recipes, accent devices, motion axis).

The extraction stage records a genuinely-absent catalog component with the schema's
explicit absence marker ``notObserved: true`` (brand-schema §5 / §10). Left alone
that marker has no ``origin``, so the Studio origin catalog printed a bare ``"?"``
placeholder for it. This module promotes each ``notObserved`` catalog component into
a ``designed`` harness component whose definition is LICENSED FROM MEASURED SIGNALS
ONLY — no invention from nowhere, no cross-brand borrowing. Every designed component
carries provenance ``designed`` (a.k.a. ``synthesized-from-brand-signals``), the list
of licensing signals, a confidence, ``overridable: true`` and ``notInReplica: true``
so it stays DISTINCT from measured components and NEVER enters the measured replica.

The brand.yaml itself is NEVER mutated here: the honest ``notObserved`` absence marker
remains the system of record; the designed component is derived at render time. This
keeps measured facts byte-untouched (replica fidelity stays honest) while the harness
renders complete + correctly badged.

Brand-agnostic + palette-agnostic: nothing about any specific brand, color, hue,
section, or content is encoded. Given any brand.yaml the module derives which measured
signal FAMILIES exist (by PRESENCE only, never by value) and licenses the designed
components from exactly those families.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_CONTRACTS = Path(__file__).resolve().parent / "contracts"


# ── measured signal families a designed component may license ────────────────────
# Each family is (id, human label, predicate(doc)). The predicate checks PRESENCE
# of a measured family in the brand.yaml — never a specific value — so the same
# logic licenses any brand from its own signals, palette-agnostic by construction.

def _t(doc, *path):
    cur = doc
    for p in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def _nonempty(v) -> bool:
    return bool(v) if not isinstance(v, (dict, list)) else len(v) > 0


_SIGNAL_FAMILIES = [
    ("color-tokens", "color token families", lambda d: _nonempty(_t(d, "tokens", "colors"))),
    ("type-scale", "measured type scale", lambda d: _nonempty(_t(d, "tokens", "type"))),
    ("spacing-ladder", "relational spacing ladder", lambda d: _nonempty(_t(d, "tokens", "spacing"))),
    ("radius-grammar", "radius / corner grammar", lambda d: _nonempty(_t(d, "tokens", "radius"))),
    ("border-shadow-grammar", "border / shadow grammar", lambda d: _nonempty(_t(d, "tokens", "shadow"))),
    ("surface-grammar", "surface-role grammar", lambda d: _nonempty(_t(d, "tokens", "surfaces"))),
    ("imagery-grammar", "imagery / media grammar", lambda d: _nonempty(_t(d, "tokens", "imagery"))),
    ("motion-axis", "motion duration / easing axis", lambda d: _nonempty(_t(d, "tokens", "motion")) or _nonempty(d.get("motion"))),
    ("button-facts", "button family + state facts", lambda d: _nonempty(d.get("buttons"))),
    ("accent-devices", "accent devices", lambda d: _nonempty(d.get("accentDevices"))),
    ("signatures", "brand signatures", lambda d: _nonempty(d.get("signatures"))),
    ("measured-recipes", "measured layout recipes", lambda d: _nonempty(d.get("recipes")) or _nonempty(d.get("recipePolicy"))),
]

# Families that make a brand's grammar rich enough to synthesize with medium (vs low)
# confidence. Palette-agnostic: this is about breadth of measured structure, not values.
_CORE_FAMILIES = {"color-tokens", "type-scale", "spacing-ladder", "surface-grammar"}


def licensed_signals(doc: dict) -> list[dict]:
    """Measured signal families PRESENT in this brand.yaml, as [{"id","label"}].

    Presence only — never a value — so it is palette/brand-agnostic. This is the
    exact, honest set a designed component is allowed to be licensed from.
    """
    if not isinstance(doc, dict):
        return []
    out = []
    for sig_id, label, pred in _SIGNAL_FAMILIES:
        try:
            present = bool(pred(doc))
        except Exception:
            present = False
        if present:
            out.append({"id": sig_id, "label": label})
    return out


def _rule_ids(rules) -> list[str]:
    out = []
    for r in rules or []:
        if isinstance(r, dict):
            rid = r.get("id") or r.get("name")
            if rid:
                out.append(str(rid))
        elif r is not None and str(r).strip():
            out.append(str(r).strip())
    return out


def _token_roles(doc: dict) -> list[str]:
    """A few generic token GROUPS present (never specific values/palette)."""
    roles = []
    tokens = _t(doc, "tokens") or {}
    for group in ("colors", "type", "spacing", "radius", "surfaces"):
        if _nonempty(tokens.get(group)):
            roles.append(group)
    return roles


def derive_confidence(doc: dict, spec: dict | None = None) -> str:
    """Designed confidence — ALWAYS lower than an extracted observation (schema §5.2).

    ``medium`` when the brand carries broad measured grammar (all core families plus
    breadth) so the synthesis is well-grounded; ``low`` otherwise. Never ``high``.
    A per-entry ``confidence`` already on the spec is respected when present.
    """
    if isinstance(spec, dict) and spec.get("confidence") in ("low", "medium", "high"):
        # never let a designed entry claim 'high'
        return "medium" if spec["confidence"] == "high" else spec["confidence"]
    sigs = {s["id"] for s in licensed_signals(doc)}
    if _CORE_FAMILIES.issubset(sigs) and len(sigs) >= 6:
        return "medium"
    return "low"


def classify(spec) -> str:
    """Provenance class of a primitives/blocks/scaffolds entry.

    ``extracted`` — measured; ``designed`` — synthesized-from-brand-signals (either an
    explicit ``origin: designed`` OR the ``notObserved`` absence marker promoted to a
    designed harness component); ``""`` — malformed/unknown (renders as a genuine
    placeholder so it is never silently synthesized).
    """
    if not isinstance(spec, dict):
        return ""
    if spec.get("origin") == "extracted":
        return "extracted"
    if spec.get("origin") == "designed" or spec.get("notObserved"):
        return "designed"
    return ""


def _compose_note(name: str, absence_note: str, signals: list[dict]) -> str:
    fam = ", ".join(s["label"] for s in signals) or "the brand's measured tokens"
    base = (f"No {name} was observed on the source page; synthesized on-brand from "
            f"measured signals ({fam}). Not used in the measured replica.")
    absence_note = (absence_note or "").strip()
    if absence_note:
        return f"{base} Absence evidence: {absence_note}"
    return base


def synthesize(name: str, spec: dict | None, doc: dict) -> dict:
    """Build the ``designed`` provenance record for one un-measured catalog component.

    Licensed FROM MEASURED SIGNALS ONLY. Carries the schema's required designed fields
    (``designedFrom`` + ``overridable``), the licensing signals, a (never-high)
    confidence, and ``notInReplica: true`` so it is structurally excluded from the
    measured replica. Palette-agnostic: only rule IDs / token GROUP names / signal
    family labels that actually exist in this brand.yaml are referenced.
    """
    spec = spec if isinstance(spec, dict) else {}
    signals = licensed_signals(doc)
    return {
        "origin": "designed",
        "provenance": "synthesized-from-brand-signals",
        "designedFrom": {
            "do": _rule_ids(doc.get("do"))[:4],
            "avoid": _rule_ids(doc.get("avoid"))[:4],
            "neverDo": _rule_ids(doc.get("neverDo")),  # ALL of them — obeyed by construction
            "tokens": _token_roles(doc),
            "signatures": _rule_ids(doc.get("signatures"))[:4],
            "note": _compose_note(name, spec.get("note", ""), signals),
        },
        "licensedSignals": [s["label"] for s in signals],
        "confidence": derive_confidence(doc, spec),
        "overridable": True,
        "notInReplica": True,
    }


# ── standard-catalog vocabulary (loaded from the universal contracts) ─────────────

def _load_contract_keys(filename: str, top_key: str) -> set[str]:
    path = _CONTRACTS / filename
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return set()
    section = data.get(top_key)
    return set(section.keys()) if isinstance(section, dict) else set()


def standard_catalog() -> dict[str, set[str]]:
    """The universal component vocabulary, per tier key, from ``contracts/``."""
    return {
        "primitives": _load_contract_keys("primitives.yaml", "primitives"),
        "blocks": _load_contract_keys("blocks.yaml", "blocks"),
        "scaffolds": _load_contract_keys("scaffolds.yaml", "scaffolds"),
    }


def is_standard_catalog(tier_key: str, name: str) -> bool:
    return name in standard_catalog().get(tier_key, set())
