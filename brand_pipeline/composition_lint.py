#!/usr/bin/env python3
"""composition_lint.py — composition-level HARD lints (fix7 2026-07).

Two failure shapes the render pipeline used to swallow silently, now failed loud
at the composition layer (same class as the silent-slot-drop guards from the
stress-test pass — declared intent must render or fail, never no-op):

  AS-63  KNOB CONSUMPTION — every ``knobs`` entry a composition section declares
         must have a CONSUMER: either a renderer/adapter device (the code
         registry below) or the section's chosen genre archetype's own
         ``variantKnobs`` vocabulary (whose structural realization is the
         skeleton's anatomy + the slots the author bound), with the used VALUE
         inside the consumer's declared vocabulary. ``supportKind: "list"`` was
         the proving case: declared on the demo hero, consumed by nothing, three
         parallel benefit items silently rendered as plain paragraphs.

  AS-65  SIBLING-SLOT CONTENT REDUNDANCY — no two sibling slots may carry the
         same enumerable content in different registers (a form ``note``
         enumerating the same links as an adjacent quick-links slot renders as
         a duplicated row + a floating caption). The structured device is the
         keeper; the prose line is the defect.

Wire points:
  - ``generate_composition``: a prefilter step (hard, repairable — the model
    gets the specific hits back);
  - ``onbrand_check --composition``: gate rows beside the other composition
    invariants (fact-gated on a ``composition.json`` beside the render).

Pure data-in/data-out; no brand or palette knowledge lives here.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import archetype_library as al  # noqa: E402  (variantKnobs vocabulary — data, not enum)

# ── the CODE-CONSUMER registry ──────────────────────────────────────────────────────
# Knob name -> {"consumer": "<module.device>", "values": <closed vocab or None=open>}.
# Every entry names REAL consuming code (test-pinned by literal source grep in
# test_fix7_lints.py) — an entry without a consumer is the lie this lint exists to
# catch, so never add one speculatively.
KNOB_CONSUMERS: dict[str, dict] = {
    "bandHeight": {"consumer": "compose_section.band_height_css (pad re-registration)",
                   "values": {"compact", "standard", "tall", "viewport"}},
    "align": {"consumer": "compose_from_composition.composition_to_layout (alignment fallback)",
              "values": {"center", "centered", "left", "right"}},
    "columns": {"consumer": "compose_from_composition.composition_to_layout (_grid fallback)",
                "values": None},        # int-able; validated below
    "mediaSide": {"consumer": "compose_from_composition.composition_to_layout (_floatSide)",
                  "values": {"left", "right"}},
    "formSide": {"consumer": "compose_from_composition._formSplit (capture-split side)",
                 "values": {"left", "right"}},
    "supportKind": {"consumer": "compose_section._compose_form_split (marked-list device, fix7)",
                    "values": {"paragraph", "bullets", "list"}},
    "faq": {"consumer": "compose_from_composition._faq_stamp", "values": None},
    "bento": {"consumer": "compose_from_composition._bento_stamp", "values": None},
    "tiers": {"consumer": "compose_from_composition._tiers_stamp", "values": None},
    "interlockEvidence": {"consumer": "compose_from_composition._interlock_copy",
                          "values": None},
}


def _knob_vocab(kspec) -> set[str] | None:
    """An archetype variantKnob's declared value vocabulary as strings (None = open).
    YAML 1.1 footgun (the pass-1 type-probe lesson): an unquoted ``[on, off]`` enum
    parses as booleans — both spellings are accepted, never a vacuous mismatch."""
    if not isinstance(kspec, dict):
        return None
    vals = kspec.get("values")
    if not isinstance(vals, list) or not vals:
        return None
    out: set[str] = set()
    for v in vals:
        if v is True:
            out |= {"on", "true", "yes"}
        elif v is False:
            out |= {"off", "false", "no"}
        else:
            out.add(str(v).strip().lower())
    return out


def lint_knobs(comp: dict) -> list[tuple[str, str]]:
    """[(section_id, message)] for every knob with no consumer / an unconsumable
    value. A knob passes when (a) the code registry consumes it and the value fits
    its vocabulary, or (b) the section's archetype declares it in ``variantKnobs``
    and the value is inside the declared enum (the skeleton's plan vocabulary —
    realized through the anatomy/slots the author bound)."""
    hits: list[tuple[str, str]] = []
    for sec in (comp.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or sec.get("useCase") or "section")
        knobs = sec.get("knobs")
        if not isinstance(knobs, dict):
            continue
        art = al.find_archetype(str(sec.get("archetypeRef") or "").strip()) \
            if sec.get("archetypeRef") else None
        art_knobs = (art or {}).get("variantKnobs") or {}
        for name, value in knobs.items():
            sval = str(value).strip().lower()
            reg = KNOB_CONSUMERS.get(name)
            if reg is not None:
                vocab = reg["values"]
                if name == "columns":
                    try:
                        ok = int(str(value)) >= 1
                    except (TypeError, ValueError):
                        ok = False
                    if not ok:
                        hits.append((sid, f"knob `{name}: {value!r}` is not a column "
                                          "count its consumer can render"))
                elif vocab is not None and sval not in vocab:
                    hits.append((sid, f"knob `{name}: {value!r}` is outside its "
                                      f"consumer's vocabulary {sorted(vocab)} — "
                                      "the declared value can never render"))
                continue
            if name in art_knobs:
                vocab = _knob_vocab(art_knobs[name])
                if vocab is not None and sval not in vocab:
                    hits.append((sid, f"knob `{name}: {value!r}` is outside the "
                                      f"archetype's declared vocabulary "
                                      f"{sorted(vocab)} — the declared value can "
                                      "never render (silent no-op)"))
                continue
            hits.append((sid, f"knob `{name}` has NO consumer (not in the renderer "
                              "registry, not a variantKnob of the section's "
                              "archetype) — declared intent would silently drop"))
    return hits


# ── AS-65: sibling-slot enumerable redundancy ────────────────────────────────────────

_ITEM_SEPS = re.compile(r"\s*[·•|/]\s*|\s*,\s*")
_LABEL_PREFIX = re.compile(r"^[^:]{0,24}:\s*")   # "Popular: a · b" -> "a · b"


def _norm_item(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", str(s).strip().lower()).strip()


def _enumerable_items(value) -> set[str]:
    """The normalized item set an enumerable payload carries: a LIST of labeled
    items, or a STRING that splits into >= 2 separator-delimited short items."""
    if isinstance(value, list):
        out = set()
        for it in value:
            if isinstance(it, str):
                out.add(_norm_item(it))
            elif isinstance(it, dict):
                label = it.get("label") or it.get("text") or it.get("heading") or ""
                if str(label).strip():
                    out.add(_norm_item(str(label)))
        return {x for x in out if x}
    if isinstance(value, str):
        body = _LABEL_PREFIX.sub("", value.strip())
        parts = [p for p in _ITEM_SEPS.split(body) if p.strip()]
        if len(parts) >= 2 and all(len(p.split()) <= 6 for p in parts):
            return {_norm_item(p) for p in parts if _norm_item(p)}
    return set()


def _slot_enumerables(slot: dict) -> list[tuple[str, set[str]]]:
    """(register-label, items) pairs a slot's copy carries — the slot's own copy
    plus nested enumerable strings (a form's ``note``, a caption's text)."""
    out: list[tuple[str, set[str]]] = []
    name = str(slot.get("name") or slot.get("role") or "slot")
    contract = str(slot.get("contract") or "").lower()
    c = slot.get("copy")
    items = _enumerable_items(c)
    if items:
        out.append((f"{name}({contract})", items))
    if isinstance(c, dict):
        for key in ("note", "caption", "meta", "text"):
            sub = _enumerable_items(c.get(key))
            if sub:
                out.append((f"{name}.{key}", sub))
    return out


def lint_redundancy(comp: dict) -> list[tuple[str, str]]:
    """[(section_id, message)] — two sibling slots (or a slot and another slot's
    nested prose line) carrying the SAME enumerable content in different registers.
    >= 2 shared items with >= 50% overlap of the smaller set = one content
    payload rendered twice; keep the structured device, drop the prose line."""
    hits: list[tuple[str, str]] = []
    for sec in (comp.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or sec.get("useCase") or "section")
        payloads: list[tuple[str, set[str]]] = []
        for slot in (sec.get("slots") or []):
            if isinstance(slot, dict):
                payloads.extend(_slot_enumerables(slot))
        for i in range(len(payloads)):
            for j in range(i + 1, len(payloads)):
                (la, a), (lb, b) = payloads[i], payloads[j]
                if la.split(".")[0].split("(")[0] == lb.split(".")[0].split("(")[0] \
                        and "." not in la and "." not in lb:
                    continue    # one slot's own list counted once, not against itself
                shared = a & b
                if len(shared) >= 2 and len(shared) >= 0.5 * min(len(a), len(b)):
                    hits.append((sid, f"`{la}` and `{lb}` enumerate the same content "
                                      f"({', '.join(sorted(shared)[:4])}) in two "
                                      "registers — keep the structured device, drop "
                                      "the prose line"))
    return hits


def lint_composition(comp: dict) -> list[tuple[str, str, str]]:
    """All hard composition lints: [(section_id, rule, message)].
    rule ∈ {"knob-consumption", "content-redundancy"} (AS-63 / AS-65)."""
    out = [(sid, "knob-consumption", msg) for sid, msg in lint_knobs(comp or {})]
    out += [(sid, "content-redundancy", msg) for sid, msg in lint_redundancy(comp or {})]
    return out
