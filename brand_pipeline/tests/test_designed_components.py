"""Generic designed-component synthesis (brand_pipeline/designed_components.py).

Proves that an un-measured standard-catalog component is synthesized on-brand from
MEASURED SIGNALS ONLY, carries the designed provenance discipline (origin/designedFrom/
overridable/confidence/notInReplica), stays distinct from measured components, and is
palette/brand-agnostic (no invention from nowhere, no cross-brand borrowing).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import designed_components as dc  # noqa: E402

REPO_ROOT = _BRAND_PIPELINE.parent
BRANDS = ["woodwave-v2", "hubspot-v2", "remote"]


def _load(brand: str) -> dict:
    return yaml.safe_load((REPO_ROOT / "runs" / brand / "brand" / "brand.yaml").read_text())


def test_classify_splits_measured_from_designed():
    extracted = {"origin": "extracted", "provenance": ["hero"]}
    not_observed = {"notObserved": True, "note": "absent on source"}
    designed = {"origin": "designed", "designedFrom": {"note": "x"}}
    malformed = {"foo": "bar"}
    assert dc.classify(extracted) == "extracted"
    assert dc.classify(not_observed) == "designed"
    assert dc.classify(designed) == "designed"
    # a genuinely malformed entry is NEVER silently synthesized
    assert dc.classify(malformed) == ""
    assert dc.classify(None) == ""


def test_licensed_signals_are_presence_only_and_brand_specific():
    doc = _load("woodwave-v2")
    sigs = dc.licensed_signals(doc)
    ids = {s["id"] for s in sigs}
    # WoodWave measured tokens, type, spacing, surfaces, buttons, accent devices, signatures
    assert {"color-tokens", "type-scale", "spacing-ladder", "surface-grammar"}.issubset(ids)
    assert "button-facts" in ids and "accent-devices" in ids and "signatures" in ids
    # an empty brand licenses nothing (no invention from nowhere)
    assert dc.licensed_signals({}) == []
    assert dc.licensed_signals({"tokens": {}}) == []


def test_synthesize_carries_designed_provenance_discipline():
    doc = _load("woodwave-v2")
    spec = (doc.get("blocks") or {}).get("accordion")
    rec = dc.synthesize("accordion", spec, doc)
    assert rec["origin"] == "designed"
    assert rec["provenance"] == "synthesized-from-brand-signals"
    assert rec["overridable"] is True
    # HARD INVARIANT: designed components never enter the measured replica
    assert rec["notInReplica"] is True
    # designed is ALWAYS lower-confidence than an extracted observation
    assert rec["confidence"] in ("low", "medium")
    df = rec["designedFrom"]
    assert df["note"] and "synthesized" in df["note"].lower()
    # licensed only from signals THIS brand actually measured
    assert rec["licensedSignals"], "designed must cite the measured signals it licenses"
    # neverDo rules are carried so the component obeys them by construction
    assert isinstance(df["neverDo"], list)


def test_synthesize_preserves_absence_evidence_and_never_high_confidence():
    doc = _load("woodwave-v2")
    spec = (doc.get("blocks") or {}).get("modal")  # note: 'Webflow lightbox chrome'
    rec = dc.synthesize("modal", spec, doc)
    assert "lightbox" in rec["designedFrom"]["note"].lower() or "chrome" in rec["designedFrom"]["note"].lower()
    assert rec["confidence"] != "high"


def test_synthesis_licenses_only_own_brand_no_cross_borrowing():
    # tokens/rule ids referenced by a designed record must be a subset of the SAME
    # brand.yaml's own measured facts — never borrowed from another brand.
    for brand in BRANDS:
        doc = _load(brand)
        own_do = set(dc._rule_ids(doc.get("do")))
        own_never = set(dc._rule_ids(doc.get("neverDo")))
        rec = dc.synthesize("table", (doc.get("blocks") or {}).get("table") or {}, doc)
        assert set(rec["designedFrom"]["do"]).issubset(own_do)
        assert set(rec["designedFrom"]["neverDo"]).issubset(own_never)


def test_standard_catalog_vocabulary_loads_from_contracts():
    cat = dc.standard_catalog()
    assert "accordion" in cat["blocks"] and "testimonial" in cat["blocks"]
    assert "heading" in cat["primitives"]
    assert dc.is_standard_catalog("blocks", "accordion")
    assert not dc.is_standard_catalog("blocks", "not-a-real-component")
