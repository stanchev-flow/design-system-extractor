from __future__ import annotations

import sys
from pathlib import Path

import pytest

BP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BP))

import generate_composition as gc  # noqa: E402
import relume_recipe_catalog as rrc  # noqa: E402


def test_all_132_families_have_safe_structural_projection():
    raw = rrc.load_catalog(rrc.GENERATED_CATALOG)
    projected = rrc.structural_projection(raw)
    assert len(projected["recipes"]) == 132
    assert rrc.scan_prompt_values(projected) == []
    assert all(set(recipe) <= rrc._PROMPT_RECIPE_KEYS for recipe in projected["recipes"])


@pytest.mark.parametrize(
    ("rule", "expected"),
    [
        (
            {"axis": "breakpointQuery", "query": "(max-width: 991px)", "base": "mobile"},
            ("breakpointTier", "lg"),
        ),
        (
            {"axis": "width", "value": "738px", "atLg": "940px", "base": "default"},
            ("containerWidth", "medium"),
        ),
        ({"axis": "height", "base": "[200vh]", "value": "[200vh]"}, ("scrollStage", "long")),
        ({"axis": "height", "base": "[400vh]", "value": "[400vh]"}, ("scrollStage", "extended")),
        (
            {"axis": "height", "base": "[calc(100vh-8.75rem)]"},
            ("viewportHeight", "viewport-minus-header"),
        ),
    ],
)
def test_literal_geometry_normalizes_to_semantic_classes(rule, expected):
    projected = rrc._semantic_rule(rule)
    assert projected["axis"] == expected[0]
    assert expected[1] in projected.values()
    assert rrc.scan_prompt_values(projected) == []


def test_unknown_literal_is_omitted_and_unsafe_guidance_fails():
    assert rrc._semantic_rule(
        {"axis": "height", "base": "713px", "value": "713px"}
    ) is None
    with pytest.raises(ValueError, match="unsafe Relume"):
        rrc.assert_prompt_safe("width: 713px; background: #fff; calc(100vh - 2rem)")


def test_fallback_excludes_higher_tiers_caps_top_k_and_stamps_ids():
    catalog = rrc.load_catalog()
    guidance, selected = rrc.fallback_guidance(
        ["hero", "pricing"],
        higher_tier={"hero": "measured-brand-pattern"},
        ingredients_by_use_case={"pricing": ("plans", "cards", "actions")},
        catalog=catalog,
        top_k=3,
    )
    assert "hero-" not in guidance
    assert 1 <= len(selected["pricing"]) <= 3
    assert rrc.scan_prompt_values(guidance) == []

    good = {
        "sections": [{
            "id": "plans",
            "useCase": "pricing",
            "structureProvenance": "relume-fallback",
            "structureRecipeId": selected["pricing"][0],
            "seededFrom": None,
        }]
    }
    assert gc.relume_precedence_lint(good, selected, {"hero": "measured-brand-pattern"}) == []


def test_precedence_lint_rejects_relume_competition():
    comp = {
        "sections": [{
            "id": "hero",
            "useCase": "hero",
            "structureProvenance": "relume-fallback",
            "structureRecipeId": "hero-content-stack",
            "seededFrom": {"lib": "project", "id": "measured-hero"},
        }]
    }
    hits = gc.relume_precedence_lint(
        comp,
        {"hero": ["hero-content-stack"]},
        {"hero": "measured-brand-pattern"},
    )
    assert any("cannot override" in message for _, message in hits)
    assert any("cannot also carry" in message for _, message in hits)


def test_brief_jobs_drive_missing_use_case_detection():
    assert gc.brief_use_cases(
        "## Hero — orient\n## Pricing — choose\n## Closing — convert"
    ) == ["hero", "pricing", "cta"]
