from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[2]
BP = REPO / "brand_pipeline"
if str(BP) not in sys.path:
    sys.path.insert(0, str(BP))

import contract_projection as cp  # noqa: E402


def _fixture(root: Path) -> tuple[dict, dict]:
    evidence = root / "evidence"
    (evidence / "grounding").mkdir(parents=True)
    (evidence / "grounding" / "section.yaml").write_text(
        yaml.safe_dump({"components": [{"kind": "card"}, {"kind": "tabs"}]})
    )
    (evidence / "computed-styles.json").write_text(json.dumps({
        "actionFamilies": [{
            "classes": "cl-button -primary -large",
            "measured": {
                "padding": "12px 24px",
                "_rect": {"w": 180, "h": 56},
            },
        }, {
            "classes": "cl-round-button",
            "measured": {
                "padding": "0px",
                "_rect": {"w": 48, "h": 48},
            },
        }],
    }))
    (evidence / "motion-audit.json").write_text(json.dumps({
        "transitions": [{
            "selector": ".cl-tabs-panel",
            "transitions": [{
                "property": "opacity", "duration": "200ms",
                "easing": "ease", "raw": "opacity 200ms ease",
            }],
        }],
    }))
    (evidence / "css-rules.json").write_text(json.dumps({
        "rules": [{
            "selector": ".grid",
            "decls": "--row-gap: 1rem;display:grid;row-gap:var(--row-gap)",
        }],
    }))
    brand = {
        "brand": {"name": "Fresh Fixture"},
        "tokens": {
            "colors": {
                "text/primary": {"value": "#111"},
                "text/secondary": {"value": "#555"},
                "border/subtle": {"value": "#ddd"},
            },
            "type": {"body": {"sizeRem": 1}},
            "spacing": {
                "heading-to-body": {"value": "1rem"},
                "body-to-cta": {"value": "1.5rem"},
            },
            "surfaces": {
                "surface/primary": {"bg": "#fff"},
                "surface/card": {"bg": "#fafafa"},
                "surface/inverse": {"bg": "#111"},
            },
            "motion": {
                "durations": {"fast": "100ms", "base": "200ms", "slow": "400ms"},
                "easings": {"standard": "ease"},
            },
        },
        "blocks": {
            "custom-cluster": {
                "value": {"slots": ["heading", "media"]},
                "source": "creation",
                "confidence": "high",
                "changelog": [{"note": "from section-03"}],
            },
            "card": {
                "value": {"variants": ["media-well"], "paddingPx": ["20 24"]},
                "source": "grounding",
                "confidence": "high",
                "changelog": [{"note": "from section-01"}],
            },
            "tabs": {
                "value": {"variants": ["underline"]},
                "source": "grounding",
                "confidence": "high",
                "changelog": [{"note": "from section-02"}],
            },
        },
        "buttons": {
            "primary": {
                "style": "filled", "bg": "#111", "fg": "#fff",
                "radius": "8px", "focus": "visible",
            },
            "round": {
                "style": "filled", "bg": "#fff", "fg": "#111",
                "radius": "50%", "focus": "visible",
            },
        },
        "actionGroup": {
            "value": {"layout": "row"},
            "source": "grounding",
            "confidence": "high",
            "changelog": [{"note": "from section-01"}],
        },
        "signatures": {"value": [{"name": "measured-move"}]},
        "navbar": {
            "utility": {
                "languageSwitcher": {
                    "trigger": "Language",
                    "options": [{"label": "English", "href": "/en"}],
                },
            },
        },
        "layouts": [],
    }
    library = {
        "schemaVersion": "layout-patterns.v1",
        "patterns": [{
            "id": "cards",
            "archetypeRef": "grid",
            "useCase": "Cards",
            "contentShape": {},
            "origin": "extracted",
            "provenance": ["section-01"],
        }],
    }
    return brand, library


def test_projects_every_residual_family_from_contracts_and_fresh_evidence():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        brand, library = _fixture(root)
        out, out_library, audit = cp.project_contract_complete(root, brand, library)

    contract_keys = set(cp._contract_map("blocks.yaml", "blocks"))
    assert contract_keys <= set(out["blocks"])
    assert out["blocks"]["card"]["origin"] == "extracted"
    assert out["blocks"]["custom-cluster"]["origin"] == "extracted"
    assert set(out["blocks"]["custom-cluster"]["slots"]) == {"heading", "media"}
    assert out["blocks"]["tabs"]["motion"]["duration"] == "200ms"
    assert out["blocks"]["form"]["notObserved"] is True
    assert out["blocks"]["form"]["origin"] == "designed"
    assert out["blocks"]["form"]["notInReplica"] is True
    assert out["buttons"]["primary"]["height"] == "56px"
    assert out["buttons"]["primary"]["padding"] == "12px 24px"
    assert out["buttons"]["round"]["height"] == "48px"
    assert out["tokens"]["spacing"]["block-to-block"]["value"] == "1rem"
    assert out["tokens"]["spacing"]["panel-padding"]["value"] == "20px 24px"
    assert out["tokens"]["spacing"]["radius-global"]["value"] == "8px"
    assert out["tokens"]["colors"]["text/on-primary"]["value"] == "#111"
    assert out["tokens"]["surfaces"]["surface/panel"]["bg"] == "#fafafa"
    assert out["voice"]["motionSpec"]["durations"]["base"] == "200ms"
    assert out["layouts"][0]["patternRef"]["id"] == "cards"
    assert out_library["patterns"][0]["contentShape"]["gridEqualizeNotObserved"] is True
    assert out["navbar"]["utility"][0]["kind"] == "dropdown"
    assert out["navbar"]["utility"][0]["dropdownNotObserved"] is True
    assert isinstance(out["signatures"], list)
    assert audit


def test_projection_is_deterministic_idempotent_and_brand_local():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        brand, library = _fixture(root)
        first_brand, first_library, _ = cp.project_contract_complete(root, brand, library)
        second_brand, second_library, _ = cp.project_contract_complete(
            root, first_brand, first_library
        )

    assert first_brand == second_brand
    assert first_library == second_library
    encoded = json.dumps(first_brand)
    assert "Fresh Fixture" in encoded
    assert "hubspot-v2" not in encoded.lower()
    assert "woodwave" not in encoded.lower()
