"""Origin catalog + component-preview: measured-vs-designed provenance split.

Proves the reported bug is fixed: standard-catalog components a brand did NOT measure
(explicit ``notObserved`` markers) render populated + badged as DESIGNED, never as a
bare ``"?"`` placeholder — while MEASURED (extracted) components are byte-unchanged and
never relabeled. Covers both the Studio origin catalog (render_catalog.build_origin_catalog)
and the standalone component-preview gallery badge.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import render_catalog as rc  # noqa: E402
import render_components_preview as rcp  # noqa: E402

REPO_ROOT = _BRAND_PIPELINE.parent
BRANDS = ["woodwave-v2", "hubspot-v2", "remote"]

# extracted-block counts BEFORE the designed fix (regression guard: measured
# components must not change count or be relabeled designed).
MEASURED_BLOCK_COUNT = {"woodwave-v2": 12, "hubspot-v2": 17, "remote": 16}


def _load(brand: str) -> dict:
    return yaml.safe_load((REPO_ROOT / "runs" / brand / "brand" / "brand.yaml").read_text())


def test_no_empty_origin_placeholder_in_any_tier():
    for brand in BRANDS:
        oc = rc.build_origin_catalog(_load(brand))
        assert oc["hasOrigin"] is True
        for tier in oc["tiers"]:
            empties = [it["name"] for it in tier["items"] if not it["origin"]]
            assert not empties, f"{brand} {tier['label']} still renders '?': {empties}"


def test_measured_components_unchanged_and_not_relabeled():
    for brand in BRANDS:
        oc = rc.build_origin_catalog(_load(brand))
        blocks = next(t for t in oc["tiers"] if t["key"] == "blocks")
        assert blocks["extracted"] == MEASURED_BLOCK_COUNT[brand], brand
        # extracted items stay extracted and never acquire designed provenance fields
        for it in blocks["items"]:
            if it["origin"] == "extracted":
                assert not it["designedFrom"], f"{brand} {it['name']} relabeled designed"
                assert not it["licensedSignals"], f"{brand} {it['name']} got licensedSignals"


def test_designed_components_carry_note_and_confidence():
    oc = rc.build_origin_catalog(_load("woodwave-v2"))
    blocks = next(t for t in oc["tiers"] if t["key"] == "blocks")
    designed = [it for it in blocks["items"] if it["origin"] == "designed"]
    assert len(designed) == 13
    for it in designed:
        assert it["designedFrom"], it["name"]
        assert it["confidence"] in ("low", "medium")
        assert it["overridable"] is True


def test_origin_catalog_html_pills_have_no_question_mark():
    doc = _load("woodwave-v2")
    model = {"originCatalog": rc.build_origin_catalog(doc)}
    html_out = rc._origin_catalog_html(model)
    assert 'cat-pill-designed' in html_out
    assert 'cat-pill-extracted' in html_out
    # the fallthrough placeholder pill must not appear
    assert '>?<' not in html_out


def test_preview_gallery_badges_designed_blocks_populated():
    brand_dir = REPO_ROOT / "runs" / "woodwave-v2" / "brand"
    doc = _load("woodwave-v2")
    # a notObserved block renders a DESIGNED (synthesized) card, not a '?'
    item = doc["blocks"]["accordion"]
    assert rcp._card_origin(item) == "designed"
    assert "synthesized" in rcp._origin_badge(item)
    note = rcp._designed_note(doc, "accordion", item)
    assert "Designed" in note and "?" not in note
    # a measured block stays extracted
    header = doc["blocks"]["header"]
    assert rcp._card_origin(header) == "extracted"
    assert "extracted" in rcp._origin_badge(header)
