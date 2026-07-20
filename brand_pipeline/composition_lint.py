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

_GROUPED_ITEM_CONTRACTS = {"feature-item", "content-block", "card", "testimonial"}
_ACTION_CONTRACTS = {"button", "cta", "form", "input"}
_VISUAL_CONTRACTS = {
    "image", "video", "stat", "stat-block", "testimonial", "quote",
    "logo", "logo-bar", "feature-item", "content-block", "card",
}

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


def _visible_strings(value, role: str, section_id: str):
    """Yield normalized substantive strings with their visible role."""
    if isinstance(value, str):
        text = " ".join(value.split()).strip()
        if len(text.split()) >= 5:
            yield re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip(), role, section_id
    elif isinstance(value, dict):
        for key, child in value.items():
            if key not in {"asset", "src", "alt", "href", "styleHint", "family"}:
                yield from _visible_strings(child, f"{role}.{key}", section_id)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _visible_strings(child, f"{role}[{index}]", section_id)


def lint_cross_slot_duplicates(comp: dict) -> list[tuple[str, str]]:
    """Substantive visible copy cannot repeat across roles/sections without a license."""
    seen: dict[str, tuple[str, str]] = {}
    hits: list[tuple[str, str]] = []
    for sec in comp.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or sec.get("useCase") or "section")
        licenses = {re.sub(r"[^a-z0-9 ]+", "", str(x).lower()).strip()
                    for x in (sec.get("repeatedProofLicense") or [])}
        for slot in sec.get("slots") or []:
            if not isinstance(slot, dict):
                continue
            role = str(slot.get("name") or slot.get("role") or "slot")
            for normalized, visible_role, owner in _visible_strings(slot.get("copy"), role, sid):
                if normalized in licenses:
                    continue
                prior = seen.get(normalized)
                if prior and prior != (owner, visible_role):
                    hits.append((sid, f"substantive copy repeats in `{prior[0]}.{prior[1]}` "
                                      f"and `{owner}.{visible_role}` without a repeated-proof license"))
                else:
                    seen[normalized] = (owner, visible_role)
    return hits


def lint_grouping(comp: dict) -> list[tuple[str, str]]:
    """AS-68: repeated semantic records stay atomic, never become a primitive waterfall."""
    hits: list[tuple[str, str]] = []
    for sec in comp.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or sec.get("useCase") or "section")
        orphan_labels = 0
        orphan_bodies = 0
        for slot in sec.get("slots") or []:
            if not isinstance(slot, dict):
                continue
            contract = str(slot.get("contract") or "").lower()
            copy = slot.get("copy")
            if contract in {"eyebrow", "label", "caption"} and isinstance(copy, str):
                orphan_labels += 1
            if contract == "paragraph" and isinstance(copy, str):
                orphan_bodies += 1
            if not isinstance(copy, list) or len(copy) < 2:
                continue
            records = [x for x in copy if isinstance(x, dict)]
            semantic = len(records) >= 2 and all(
                any(str(item.get(k) or "").strip() for k in ("eyebrow", "heading", "title", "label"))
                and any(str(item.get(k) or "").strip() for k in ("text", "body", "action", "cta"))
                for item in records)
            if semantic and contract not in _GROUPED_ITEM_CONTRACTS:
                hits.append((sid, f"`{slot.get('name') or slot.get('role')}` carries "
                                  f"{len(records)} semantic records but contract `{contract}` "
                                  "would flatten them; bind one repeatable feature-item/"
                                  "content-block/card slot"))
        # Only the alternating waterfall shape is illegal. Multiple independent
        # labels (pricing toggles, metadata rails, filters) are valid when they are
        # not paired with a sibling run of loose paragraph bodies.
        if orphan_labels >= 2 and orphan_bodies >= 2:
            hits.append((sid, f"{orphan_labels} sibling label/eyebrow primitives form a "
                              "waterfall; bind them with their bodies as repeated item records"))
    return hits


def lint_wireframe_quality(comp: dict, wireframe: dict) -> list[tuple[str, str, str]]:
    """AS-69..72: completeness, visual rhythm, hero balance, required consumption."""
    hits: list[tuple[str, str, str]] = []
    by_id = {str(s.get("id")): s for s in comp.get("sections") or [] if isinstance(s, dict)}
    wf_sections = [s for s in (wireframe.get("sections") or []) if isinstance(s, dict)]
    sparse = 0
    for wf in wf_sections:
        sid = str(wf.get("id") or "section")
        sec = by_id.get(sid, {})
        slots = [s for s in sec.get("slots") or [] if isinstance(s, dict)]
        names = {str(s.get("name") or s.get("role") or "slot") for s in slots}
        contracts = {str(s.get("contract") or "").lower() for s in slots}
        missing = [n for n in wf.get("requiredSlots") or [] if n not in names]
        if missing:
            hits.append((sid, "wireframe-consumption",
                         f"required wireframe slots are not consumed: {missing}"))
        if wf.get("ctaRequired") and not (contracts & _ACTION_CONTRACTS):
            hits.append((sid, "section-completeness",
                         "conversion job requires a rendered action"))
        if wf.get("proofRequired") and not (contracts & _VISUAL_CONTRACTS):
            hits.append((sid, "section-completeness",
                         "proof/story job requires proof, media, or a component cluster"))
        anchored = bool(wf.get("visualAnchor")) or bool(wf.get("licensedTextOnly"))
        sparse = 0 if anchored else sparse + 1
        if not anchored:
            hits.append((sid, "visual-anchor",
                         "substantive section has no visual anchor or licensed text-only monument"))
        if sparse > 1:
            hits.append((sid, "page-rhythm",
                         "consecutive visually sparse substantive sections are forbidden"))
        if str(sec.get("useCase") or "").lower() == "hero":
            counter = str((sec.get("alignment") or {}).get("counterweight") or "")
            if counter:
                counter_slot = next((s for s in slots
                                     if str(s.get("name") or s.get("role") or "") == counter), None)
                if not counter_slot or str(counter_slot.get("contract") or "").lower() \
                        not in _VISUAL_CONTRACTS:
                    hits.append((sid, "hero-balance",
                                 f"side hero counterweight `{counter}` is not a painted device"))
        for collection in wf.get("collections") or []:
            fit = collection.get("componentFit") or {}
            candidates = fit.get("candidateWidths") or []
            chosen = int(collection.get("columns") or 0)
            selected = next((c for c in candidates
                             if int(c.get("columns") or 0) == chosen), None)
            if not selected or not selected.get("feasible"):
                hits.append((sid, "component-fit",
                             "collection columns do not select a feasible content-demand candidate"))
            if fit.get("internalAnatomy") not in {
                    "icon-top", "icon-inline", "media-top", "text-stack"}:
                hits.append((sid, "component-fit",
                             "component family has no coherent internal anatomy"))
            strategy = str(collection.get("fillStrategy") or "")
            columns = max(1, int(collection.get("columns") or 1))
            spans = [int(item.get("span") or 1) for item in collection.get("items") or []]
            counterweight = collection.get("balancingCounterweight")
            licensed = (
                strategy == "licensed-asymmetry"
                and isinstance(counterweight, dict)
                and bool(str(counterweight.get("role") or counterweight.get("contract") or ""))
                and any(counterweight.get(key)
                        for key in ("asset", "contract", "component", "visual"))
            )
            used = 0
            orphan = False
            for span in spans:
                if span < 1 or span > columns or (used and used + span > columns):
                    orphan = True
                    break
                used = (used + span) % columns
            if (used or orphan) and not licensed:
                hits.append((sid, "grid-fill",
                             "collection leaves unused final-row tracks without a "
                             "declared strategy and painted counterweight"))
        testimonial = wf.get("testimonial")
        if testimonial is not None:
            if testimonial.get("componentContract") != "testimonial" \
                    or not testimonial.get("complete"):
                hits.append((sid, "testimonial-integrity",
                             "testimonial intent must preserve quote + attribution in one component"))
            if testimonial.get("assetStatus") not in {"bound", "requested"}:
                hits.append((sid, "testimonial-integrity",
                             "compatible testimonial media was neither bound nor requested"))
    return hits


def lint_composition(comp: dict, wireframe: dict | None = None) -> list[tuple[str, str, str]]:
    """All hard composition lints: [(section_id, rule, message)].
    rule ∈ {"knob-consumption", "content-redundancy"} (AS-63 / AS-65)."""
    out = [(sid, "knob-consumption", msg) for sid, msg in lint_knobs(comp or {})]
    out += [(sid, "content-redundancy", msg) for sid, msg in lint_redundancy(comp or {})]
    out += [(sid, "duplicate-copy", msg) for sid, msg in lint_cross_slot_duplicates(comp or {})]
    out += [(sid, "semantic-grouping", msg) for sid, msg in lint_grouping(comp or {})]
    if wireframe:
        out += lint_wireframe_quality(comp or {}, wireframe)
    return out
