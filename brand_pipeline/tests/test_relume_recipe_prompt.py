from __future__ import annotations

import sys
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import generate_composition as gc  # noqa: E402


REPO_ROOT = _BRAND_PIPELINE.parent
BRAND_YAML = REPO_ROOT / "runs" / "woodwave" / "brand" / "brand.yaml"


def test_section_recipe_guidance_is_fact_gated_in_prompt():
    baseline = gc.build_prompt(
        "Build one hero.",
        BRAND_YAML,
        "corporate-saas-clean",
        "",
    )
    guided = gc.build_prompt(
        "Build one hero.",
        BRAND_YAML,
        "corporate-saas-clean",
        "",
        section_recipe_guidance=(
            "## SECTION RECIPE CANDIDATES\n"
            "- `hero-content-media-split`\n"
            "  responsive: columns 1 → md:2"
        ),
    )

    assert "hero-content-media-split" not in baseline
    assert "hero-content-media-split" in guided
    assert "columns 1 → md:2" in guided


def test_empty_guidance_preserves_prompt_bytes():
    omitted = gc.build_prompt(
        "Build one hero.",
        BRAND_YAML,
        "corporate-saas-clean",
        "",
    )
    suppressed = gc.build_prompt(
        "Build one hero.",
        BRAND_YAML,
        "corporate-saas-clean",
        "",
        section_recipe_guidance="",
    )
    assert omitted == suppressed
