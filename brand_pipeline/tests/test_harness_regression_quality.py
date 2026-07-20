from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
BP = REPO / "brand_pipeline"
if str(BP) not in sys.path:
    sys.path.insert(0, str(BP))

import contract_projection as cp  # noqa: E402
import compose_page as page_compose  # noqa: E402
import compose_replica as replica  # noqa: E402
import component_render as cr  # noqa: E402
import render_components_preview as rp  # noqa: E402
import staged_author as sa  # noqa: E402
from artifact_digest import projection_input_digest  # noqa: E402


def test_button_projection_prefers_real_control_over_tall_nav_container():
    samples = [
        {
            "classes": "global-nav-header-cta -primary -medium mega-panel",
            "widthBehavior": "hug",
            "measured": {"padding": "12px 24px", "_rect": {"w": 180, "h": 140}},
        },
        {
            "classes": "cl-button -primary -large homepage-hero",
            "widthBehavior": "hug",
            "measured": {"padding": "16px 40px", "_rect": {"w": 183, "h": 68}},
        },
    ]
    assert cp._sample_for_family(samples, "primary")["measured"]["_rect"]["h"] == 68


def test_projection_keeps_visible_and_accessible_button_labels_separate():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "evidence").mkdir()
        (root / "evidence" / "computed-styles.json").write_text(json.dumps({
            "actionGroups": [{
                "classes": "cl-button -primary -small nav-action",
                "sample": "Get a demo",
                "visibleLabel": "Get a demo",
                "accessibleName": "Get a demo of the complete premium software",
                "labelFit": {"visibleFits": True},
                "widthBehavior": "hug",
                "measured": {"padding": "8px 16px", "_rect": {"w": 113.375, "h": 42}},
            }],
        }))
        doc = {"buttons": {"primary": {
            "style": "filled", "bg": "#f50", "fg": "#fff",
            "height": "42px", "padding": "8px 16px",
        }}}
        cp._canonical_buttons(doc, root, [])
    family = doc["buttons"]["primary"]
    assert family["visibleLabel"] == "Get a demo"
    assert family["ariaLabel"] == "Get a demo of the complete premium software"


def test_chrome_projection_repairs_visible_label_without_losing_accessible_name():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "evidence").mkdir()
        (root / "evidence" / "computed-styles.json").write_text(json.dumps({
            "actionGroups": [{
                "classes": "cl-button -primary -small nav-action",
                "visibleLabel": "Request demo",
                "accessibleName": "Request a personalized product demonstration",
                "semanticText": "Request demo Request a personalized product demonstration",
                "measured": {"_rect": {"x": 1000, "y": 20, "w": 120, "h": 42}},
            }],
        }))
        (root / "evidence" / "section-rects.json").write_text(json.dumps({
            "chrome": [{"name": "header", "rect": {"h": 100}}],
        }))
        chrome, _ = cp.project_chrome_labels(root, {"navbar": {"ctas": [{
            "label": "Request demo Request a personalized product demonstration",
            "href": "#", "style": "primary",
        }]}})
    cta = chrome["navbar"]["ctas"][0]
    assert cta["label"] == "Request demo"
    assert cta["ariaLabel"] == "Request a personalized product demonstration"


def test_copy_projection_repairs_only_action_fields():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "evidence").mkdir()
        (root / "evidence" / "computed-styles.json").write_text(json.dumps({
            "actionGroups": [{
                "classes": "btn primary",
                "visibleLabel": "Start",
                "accessibleName": "Start the guided onboarding workflow",
                "semanticText": "Start the guided onboarding workflow",
                "measured": {"_rect": {"w": 90, "h": 40}},
            }],
        }))
        copy_doc, _ = cp.project_copy_labels(root, {"layoutCopy": {"hero": {
            "heading": "Start the guided onboarding workflow",
            "cta": "Start the guided onboarding workflow",
        }}})
    payload = copy_doc["layoutCopy"]["hero"]
    assert payload["heading"] == "Start the guided onboarding workflow"
    assert payload["cta"] == "Start"
    assert payload["ctaAriaLabel"] == "Start the guided onboarding workflow"


def test_renderer_paints_short_label_and_keeps_long_aria_label():
    doc = {
        "buttons": {"primary": {"style": "filled", "bg": "#f50", "fg": "#fff"}},
        "neverDo": [{"id": "never-typographic-primary"}],
    }
    ctx = cr.make_context(doc, "surface/primary", {})
    rendered = cr.render_button(doc, ctx, {
        "label": "Get a demo",
        "ariaLabel": "Get a demo of the complete premium software",
    })
    assert ">Get a demo</a>" in rendered
    assert 'aria-label="Get a demo of the complete premium software"' in rendered


def test_staged_author_prompt_requires_dual_label_channels():
    foundation = sa._stage_system(sa.STAGE_BY_NAME["foundation"])
    copy_chrome = sa._stage_system(sa.STAGE_BY_NAME["copy-chrome"])
    assert "visibleLabel" in foundation and "accessibleName" in foundation
    assert "visibleLabel" in copy_chrome and "ariaLabel" in copy_chrome


def test_stage_schema_rejects_lane_id_and_thin_snapshot():
    with pytest.raises(Exception, match="public source brand"):
        sa._required_shape("brand.yaml", {
            "brand": {"name": "hubspot-v3", "snapshot": {"value": "x" * 140}},
            "tokens": {}, "blocks": {},
        })
    with pytest.raises(Exception, match="rich evidence-grounded"):
        sa._required_shape("brand.yaml", {
            "brand": {"name": "HubSpot", "snapshot": {"value": "too short"}},
            "tokens": {}, "blocks": {},
        })


def test_projection_preserves_pattern_slots_in_layout_instance():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "evidence" / "grounding").mkdir(parents=True)
        (root / "evidence" / "grounding" / "s.yaml").write_text("components: []\n")
        for name in ("computed-styles.json", "motion-audit.json", "css-rules.json"):
            (root / "evidence" / name).write_text("{}")
        brand = {"brand": {"name": "Fixture"}, "tokens": {}, "blocks": {}, "layouts": []}
        library = {"patterns": [{
            "id": "hero", "origin": "extracted", "archetypeRef": "stack",
            "contentShape": {"slots": [
                {"name": "heading", "role": "display"},
                {"name": "background", "role": "photo", "assets": ["hero.webp"]},
            ]},
        }]}
        out, _, _ = cp.project_contract_complete(root, brand, library)
    assert out["layouts"][0]["slots"][1]["assets"] == ["hero.webp"]


def test_custom_measured_blocks_resolve_real_renderers():
    cases = {
        "hero": rp.render_b_media_text,
        "logos": rp.render_b_logo_bar,
        "features": rp.render_b_carousel,
        "cta": rp.render_b_cta_block,
        "testimonial": rp.render_b_testimonial,
        "footer": rp.render_b_footer,
    }
    for archetype, expected in cases.items():
        assert rp._measured_block_renderer(
            {"archetype": archetype, "origin": "extracted", "slots": {}}
        ) is expected


def test_round_family_is_icon_only_and_square_in_harness():
    doc = {
        "buttons": {
            "primary": {
                "style": "filled", "bg": "#111", "fg": "#fff", "radius": "8px",
                "height": "48px", "padding": "12px 24px",
            },
            "round": {
            "style": "filled", "bg": "#fff", "fg": "#111", "radius": "50%",
            "height": "48px", "diameter": "48px", "padding": "0px",
            },
        },
        "tokens": {"surfaces": {"surface/primary": {"bg": "#fff"}}},
    }
    rp._SPEC_CTA = "Get started free"
    html = rp.render_button(doc, "button", {})
    css = rp.button_family_css(doc)
    assert "btnf-round" in html
    assert 'class="btnf btnf-round' in html
    assert not __import__("re").search(
        r'class="btnf btnf-round[^"]*"[^>]*>Get started free<', html)
    assert "width: 48px" in css


def test_designed_toggle_uses_capsule_track_and_brand_state_vars():
    assert ".ex-switch .track" in rp.BASE_CSS
    assert "border-radius: 999px" in rp.BASE_CSS
    assert ".ex-switch .knob" in rp.BASE_CSS
    assert "border-radius: 50%" in rp.BASE_CSS
    assert "var(--surface-primary)" in rp.BASE_CSS
    assert "var(--ease)" in rp.BASE_CSS


def test_as78_as79_are_registered_in_spec_and_machine_gate():
    spec = (BP / "spec" / "anti-ai-slop.md").read_text()
    audit = (BP / "slop_audit.mjs").read_text()
    for rule in ("AS-78", "AS-79"):
        assert rule in spec
        assert rule in audit


def test_stage_join_gate_rejects_drift_missing_type_and_sourcecopy():
    files = {"layout-library.yaml": __import__("yaml").safe_dump({
        "patterns": [{
            "id": "measured-layout", "origin": "extracted",
            "contentShape": {"slots": [{
                "name": "heading", "sourceCopy": "layoutCopy.other.heading",
            }]},
        }],
    })}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "section-copy.yaml").write_text(
            "sectionCopy: {wordmark: Fixture}\nlayoutCopy: {other: {heading: Hello}}\n")
        with pytest.raises(Exception, match="cross-stage join validation"):
            sa.validate_stage_joins(root, files)


def test_projection_digest_invalidates_on_copy_or_layout_change():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for name in (
            "brand.yaml", "section-copy.yaml", "layout-library.yaml",
            "brand-chrome.yaml", "media-assets.yaml", "assets-tagged.json",
        ):
            (root / name).write_text(f"{name}: one\n")
        before = projection_input_digest(root)
        (root / "section-copy.yaml").write_text("section-copy: two\n")
        assert projection_input_digest(root) != before


def test_internal_lane_id_gate_is_registered_and_current_public_copy_is_clean():
    validator = (REPO / "tools" / "extract" / "validate_brand_evidence.py").read_text()
    assert "internal lane id" in validator
    copy_path = REPO / "runs" / "hubspot-v3" / "brand" / "section-copy.yaml"
    if copy_path.is_file():
        assert "hubspot-v3" not in copy_path.read_text().lower()


def test_remote_complete_testimonials_remain_atomic_in_replica():
    """New-lane harness inference must not rewrite a complete measured legacy band."""
    brand_yaml = REPO / "runs" / "remote" / "brand" / "brand.yaml"
    if not brand_yaml.is_file():
        pytest.skip("Remote measured-brand fixture is absent")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        replica.build_replica_page(brand_yaml, out)
        composition = json.loads((out / "composition.json").read_text())
        section = next(
            item for item in composition["sections"] if item.get("id") == "testimonials")
        cards = next(slot for slot in section["slots"] if slot.get("name") == "cards")
        html = (out / "index.html").read_text()

    assert cards["contract"] == "card"
    assert len(cards["copy"]) == 3
    assert [item["name"] for item in cards["copy"]] == [
        "Luke McKinlay", "Marisol Jiménez", "Maria Shkaruppa"]
    assert html.count(
        '<article class="cs-module cs-module--plate cs-module--quote">') == 3
    assert "If we had to manage and coordinate everything in-house" in html
    assert 'src="assets/logo-fountain.svg"' in html
    assert 'src="assets/avatar-luke-mckinlay.webp"' in html


def test_projected_canonical_mark_row_still_routes_as_logo_collection():
    brand_yaml = REPO / "runs" / "hubspot-v3" / "brand" / "brand.yaml"
    if not brand_yaml.is_file():
        pytest.skip("HubSpot v3 projected-lane fixture is absent")
    doc = page_compose.load_doc(brand_yaml)
    pattern = next(
        item for item in rp.load_layout_library(brand_yaml)
        if item.get("id") == "centered-heading-over-logo-row")
    layout = rp.layout_for_pattern(doc, pattern["id"])
    section = rp._demo_section_for_pattern(doc, pattern, layout)
    logo_row = next(slot for slot in section["slots"] if slot.get("name") == "logo-row")
    assert layout["requiresHydration"] is True
    assert logo_row["contract"] == "logo"
