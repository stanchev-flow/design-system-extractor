import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from brand_pipeline.relume_recipe_catalog import (
    INVENTORY_SCHEMA_VERSION,
    CATEGORY_TAXONOMY,
    compile_catalog,
    guidance_for_use_cases,
    load_inventory,
    load_responsive_evidence,
    match_recipes,
    render_recipe_guidance,
)
from brand_pipeline.relume_responsive_parser import parse_response


def _category(slug, components):
    return {"slug": slug, "name": slug, "components": components}


def _component(slug, *tags):
    return {"slug": slug, "name": slug, "tags": list(tags)}


def test_mirrors_and_media_kinds_collapse_into_variant_axes():
    doc = compile_catalog([
        _category("feature-sections", [
            _component("layout635", "2 Columns", "Image/Video Right", "Buttons", "Image"),
            _component(
                "layout636",
                "2 Columns",
                "Image/Video Right",
                "Buttons",
                "Video Lightbox",
            ),
            _component("layout659", "2 Columns", "Image/Video Left", "Buttons", "Image"),
        ])
    ])

    assert doc["coverage"]["recipeFamilyCount"] == 1
    recipe = doc["recipes"][0]
    assert recipe["id"] == "feature-content-media-split"
    assert recipe["structure"]["archetype"] == "split"
    assert recipe["variantAxes"]["mediaSide"] == ["left", "right"]
    assert recipe["variantAxes"]["mediaMode"] == ["image", "video-lightbox"]
    assert recipe["variantAxes"]["ingredients"] == ["actions"]
    assert recipe["provenance"]["componentCount"] == 3


def test_interaction_changes_structure_but_card_ingredients_do_not():
    doc = compile_catalog([
        _category("testimonial-sections", [
            _component("testimonial44", "2 Columns", "Cards", "Image", "Star Rating"),
            _component("testimonial45", "3 Columns", "Cards", "Image", "Star Rating"),
            _component("testimonial48", "2 Columns", "Cards", "Image", "Slider"),
        ])
    ])

    assert {r["structure"]["skeleton"] for r in doc["recipes"]} == {
        "carousel",
        "repeated-grid",
    }
    carousel = next(r for r in doc["recipes"] if r["structure"]["skeleton"] == "carousel")
    assert carousel["variantAxes"]["interaction"] == ["carousel"]
    assert "interaction" in carousel["physicsBindings"]


def test_inventory_shards_are_merged(tmp_path):
    for index, category_slug in enumerate(("hero-header-sections", "cta-sections")):
        payload = {
            "schemaVersion": INVENTORY_SCHEMA_VERSION,
            "categories": [
                _category(category_slug, [_component(f"component-{index}", "Text Align Center")])
            ],
        }
        (tmp_path / f"{index}.json").write_text(json.dumps(payload))

    assert len(load_inventory(tmp_path)) == 2


def test_all_relume_categories_are_mapped():
    assert len(CATEGORY_TAXONOMY) == 50


def test_responsive_evidence_is_first_class_and_matches_list_slug_aliases():
    categories = [
        _category("feature-sections", [
            _component(
                "section_layout635",
                "2 Columns",
                "Image/Video Right",
                "Buttons",
                "Image",
            )
        ])
    ]
    responsive = {
        "layout635": {
            "componentSlug": "layout635",
            "anatomy": {"content": ["heading", "actions"], "media": ["image"]},
            "rules": [
                {"axis": "columns", "base": 1, "at": "md", "value": 2},
                {"axis": "order", "base": "content-then-media", "at": "md",
                 "value": "content-left-media-right"},
            ],
        }
    }

    recipe = compile_catalog(categories, responsive)["recipes"][0]
    assert recipe["responsive"]["evidenceStatus"] == "source-inspected"
    assert recipe["responsive"]["rules"][0]["axis"] == "columns"
    assert recipe["anatomyEvidence"]["media"] == ["image"]


def test_navigation_and_footer_have_dedicated_recipe_families():
    doc = compile_catalog([
        _category("navbars", [
            _component("navbar1_component", "Logo Left", "Menu Right", "Navbar"),
            _component("navbar5_component", "Logo Left", "Menu Left", "Mega Menu", "Navbar"),
            _component(
                "navbar4_component",
                "Logo Left",
                "Hamburger Menu (Desktop)",
                "Navbar",
            ),
        ]),
        _category("footers", [
            _component("footer1_component", "4 Columns", "Newsletter Sign Up", "Footer"),
            _component("footer3_component", "3 Columns", "Contact Details", "Footer"),
            _component("footer4_component", "Text Align Center", "Footer"),
        ]),
    ])

    ids = {recipe["id"] for recipe in doc["recipes"]}
    assert {
        "navigation-standard-nav",
        "navigation-mega-menu",
        "navigation-overlay-menu",
        "footer-newsletter-columns",
        "footer-contact-columns",
        "footer-compact-centered",
    } <= ids
    nav = next(r for r in doc["recipes"] if r["id"] == "navigation-mega-menu")
    assert nav["slots"]["required"] == ["logo", "links", "mobileMenuToggle"]
    assert "megaMenu" in nav["slots"]["optional"]
    assert "interaction" in nav["physicsBindings"]


def test_checked_in_responsive_evidence_covers_navigation_footer_and_media():
    evidence = load_responsive_evidence()
    assert {
        "navbar1",
        "navbar4",
        "navbar5",
        "navbar20",
        "navbar24",
        "footer1",
        "footer3",
        "footer4",
        "footer12",
        "footer16",
        "layout635",
        "layout636",
        "layout659",
        "header155",
        "testimonial48",
        "pricing43",
    } <= evidence.keys()
    assert all(observation.get("rules") for observation in evidence.values())


def test_recipe_retrieval_prefers_responsive_source_inspection():
    categories = [
        _category("feature-sections", [
            _component("layout1", "2 Columns", "Image/Video Right", "Image"),
            _component("layout2", "3 Columns", "Cards", "Icons"),
        ])
    ]
    responsive = {
        "layout2": {
            "componentSlug": "layout2",
            "rules": [{"axis": "columns", "base": 1, "at": "lg", "value": 3}],
        }
    }
    catalog = compile_catalog(categories, responsive)

    matches = match_recipes(catalog, builder_use_case="features")
    assert matches[0]["responsive"]["evidenceStatus"] == "source-inspected"
    strict = match_recipes(catalog, builder_use_case="features", responsive_required=True)
    assert len(strict) == 1


def test_prompt_guidance_includes_responsive_rules_and_variant_axes():
    categories = [
        _category("feature-sections", [
            _component("layout1", "2 Columns", "Image/Video Right", "Image", "Buttons"),
        ])
    ]
    responsive = {
        "layout1": {
            "componentSlug": "layout1",
            "rules": [{"axis": "columns", "base": 1, "at": "md", "value": 2}],
        }
    }
    catalog = compile_catalog(categories, responsive)
    block = guidance_for_use_cases(["features"], catalog=catalog)

    assert "SECTION RECIPE CANDIDATES" in block
    assert "mediaSide=right" in block
    assert "columns: 1 → md:2" in block
    assert render_recipe_guidance([]) == ""


def test_checked_in_catalog_is_complete_and_schema_valid():
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (root / "brand_pipeline/spec/section-recipes.v1.schema.json").read_text()
    )
    catalog = yaml.safe_load(
        (root / "brand_pipeline/contracts/section-recipes/catalog.generated.yaml").read_text()
    )
    errors = list(Draft202012Validator(schema).iter_errors(catalog))

    assert not errors
    assert catalog["coverage"]["categoryCount"] == 50
    assert catalog["coverage"]["componentCount"] == 1757
    assert catalog["coverage"]["recipeFamilyCount"] == 132
    assert catalog["coverage"]["responsiveSourceInspectedRecipeCount"] == 132
    assert catalog["coverage"]["responsiveSourcePendingRecipeCount"] == 0
    assert catalog["coverage"]["duplicateComponentSlugs"] == []


def test_tsx_parser_extracts_breakpoints_visibility_overflow_and_interaction():
    response = """### Example  (slug: example1)
// File: Example1.tsx
```tsx
const Example = () => (
  <section className="grid grid-cols-1 overflow-hidden md:grid-cols-2">
    <button className="flex lg:hidden">Menu</button>
    <img className="aspect-square object-cover md:aspect-video" />
    <div className="h-16 px-6 font-bold md:px-8">Visual style is ignored</div>
  </section>
);
const isMobile = useMediaQuery("(max-width: 991px)");
const handlers = { onMouseEnter: () => !isMobile && open() };
```
"""
    observation = parse_response(response)[0]
    axes = {rule["axis"] for rule in observation["rules"]}

    assert {"columns", "overflow", "display", "mediaAspect", "mediaCrop",
            "breakpointQuery", "interaction"} <= axes
    serialized = json.dumps(observation)
    assert "px-6" not in serialized
    assert "font-bold" not in serialized
    assert "h-16" not in serialized


def test_relume_is_style_free_baseline_with_explicit_bias_and_precedence():
    root = Path(__file__).resolve().parents[1]
    catalog = yaml.safe_load(
        (root / "brand_pipeline/contracts/section-recipes/catalog.generated.yaml").read_text()
    )
    source = catalog["source"]

    assert source["productRole"] == "content-structure-baseline"
    assert {
        "colors", "typography", "spacing", "class-names", "aesthetic-defaults"
    } <= set(source["ignoredVisualStyle"])
    assert source["selectionPrecedence"] == [
        "active-brand-facts",
        "active-style-structure",
        "brand-neverDo-and-physics",
        "selected-structural-prior",
    ]
    assert "conventional-saas" in source["knownBiases"]
    assert "editorial" in source["coverageLimit"].lower()
    assert "separate" in source["genreMergePolicy"].lower()
    assert "selection time" in source["genreMergePolicy"].lower()

    forbidden_rule_keys = {
        "class", "className", "classes", "color", "font", "spacing",
        "radius", "shadow",
    }
    for recipe in catalog["recipes"]:
        for rule in recipe["responsive"]["rules"]:
            assert not (forbidden_rule_keys & set(rule))
            if "scope" in rule:
                assert rule["scope"].startswith("element-")


def test_prompt_guidance_enforces_brand_style_precedence_and_corpus_boundary():
    catalog = compile_catalog([
        _category("feature-sections", [
            _component("layout1", "2 Columns", "Image/Video Right", "Image"),
        ])
    ])
    block = render_recipe_guidance(catalog["recipes"])

    assert "NEVER a visual template" in block
    assert "active brand facts + active style structure ALWAYS win" in block
    assert "biased toward conventional SaaS" in block
    assert "separate curated genre libraries" in block
