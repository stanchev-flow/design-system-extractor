"""HARD INVARIANT: designed (synthesized-from-brand-signals) components must NEVER
enter the measured replica or contaminate measured facts.

The replica composes ONLY from measured patterns — ``doc["layouts"]`` resolved via
provenance-backed ``layout-library.patterns`` — never from ``doc["blocks"]``/
``primitives`` and never from ``layout-library.synthesizedComponents``. These tests
prove designed components are structurally excluded, so replica fidelity stays honest.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import compose_replica as cx  # noqa: E402
import designed_components as dc  # noqa: E402
import render_components_preview as rp  # noqa: E402

REPO_ROOT = _BRAND_PIPELINE.parent
BRANDS = ["woodwave-v2", "hubspot-v2", "remote"]


def _brand_dir(brand: str) -> Path:
    return REPO_ROOT / "runs" / brand / "brand"


def _load(brand: str) -> dict:
    return yaml.safe_load((_brand_dir(brand) / "brand.yaml").read_text())


def test_synthesized_records_are_marked_not_in_replica():
    doc = _load("woodwave-v2")
    for name, spec in (doc.get("blocks") or {}).items():
        if dc.classify(spec) == "designed":
            assert dc.synthesize(name, spec, doc)["notInReplica"] is True, name


def test_replica_source_order_uses_only_measured_layouts():
    for brand in BRANDS:
        doc = _load(brand)
        patterns = rp.load_layout_library(_brand_dir(brand) / "brand.yaml")
        pairs = cx.source_order_sections(doc, patterns)
        layout_ids = {l.get("id") for l, _ in pairs}
        # every replica section resolves to a real measured brand layout
        real_layouts = {l.get("id") for l in doc.get("layouts") or []}
        assert layout_ids.issubset(real_layouts)
        # NONE of the designed catalog components leak in as a composed section
        designed = {n for n, s in (doc.get("blocks") or {}).items() if dc.classify(s) == "designed"}
        designed |= {n for n, s in (doc.get("primitives") or {}).items() if dc.classify(s) == "designed"}
        assert layout_ids.isdisjoint(designed)


def test_layout_library_synthesized_components_excluded_from_replica_patterns():
    for brand in BRANDS:
        lib_path = _brand_dir(brand) / "layout-library.yaml"
        if not lib_path.exists():
            continue
        lib = yaml.safe_load(lib_path.read_text()) or {}
        synth_ids = {c.get("id") for c in (lib.get("synthesizedComponents") or [])}
        pattern_ids = {p.get("id") for p in (lib.get("patterns") or [])}
        # synthesized components are a SEPARATE list, never in the replica patterns
        assert synth_ids.isdisjoint(pattern_ids)
        # and each is explicitly flagged notInReplica
        for c in (lib.get("synthesizedComponents") or []):
            assert c.get("notInReplica") is True, (brand, c.get("id"))


def test_measured_patterns_all_carry_provenance():
    # a designed component has no source provenance; every replica pattern must.
    for brand in BRANDS:
        patterns = rp.load_layout_library(_brand_dir(brand) / "brand.yaml")
        for pat in patterns:
            prov = [p for p in (pat.get("provenance") or []) if p]
            ref = (pat.get("patternRef") or {}).get("id")
            assert prov or ref, (brand, pat.get("id"))
