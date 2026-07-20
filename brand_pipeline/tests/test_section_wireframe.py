from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import composition_lint as cl  # noqa: E402
import compose_from_composition as cfc  # noqa: E402
import section_wireframe as sw  # noqa: E402


def item_section(contract="content-block", archetype="cards"):
    return {
        "id": "story", "useCase": "features", "archetype": archetype,
        "surfaceIntent": "primary", "knobs": {"columns": "3"},
        "slots": [
            {"name": "heading", "role": "heading", "contract": "heading",
             "copy": "Keep the connection."},
            {"name": "items", "role": "benefits", "contract": contract, "copy": [
                {"heading": "Growing club.", "text": "Scattered fan data slowed the team."},
                {"heading": "One platform.", "text": "Every interaction stayed together."},
                {"heading": "Personal at scale.", "text": "Each fan still felt known."},
            ]},
        ],
    }


class WireframePlannerTest(unittest.TestCase):
    def test_exact_three_item_shape_stays_atomic(self):
        comp = {"sections": [item_section()]}
        wf = sw.plan_wireframe(comp)
        collection = wf["sections"][0]["collections"][0]
        self.assertEqual(collection["itemContract"], "content-block")
        self.assertEqual(len(collection["items"]), 3)
        self.assertEqual(collection["layout"], "grid")
        self.assertEqual(collection["responsive"]["collapse"], "preserve-item")
        self.assertEqual(sw.validate_wireframe(wf, comp), [])

    def test_renderer_capability_rejects_flattening_list(self):
        sec = item_section(contract="list", archetype="stack")
        wf = sw.plan_wireframe({"sections": [sec]})
        errors = sw.validate_wireframe(wf, {"sections": [sec]})
        self.assertTrue(any("not consumable" in e for e in errors))

    def test_media_aware_case_split_is_consumable(self):
        sec = {
            "id": "hero", "useCase": "hero", "archetype": "split",
            "alignment": {"anchor": "left", "counterweight": "case"},
            "slots": [
                {"name": "heading", "contract": "heading", "role": "heading",
                 "copy": "Proof that grows."},
                {"name": "case", "contract": "card", "role": "case-card",
                 "asset": {"src": "customer.png"}, "copy": {
                     "heading": "300%+", "text": "A grounded outcome.",
                 }},
            ],
        }
        wf = sw.plan_wireframe({"sections": [sec]})
        self.assertEqual(sw.validate_wireframe(wf, {"sections": [sec]}), [])

    def test_consecutive_empty_sections_fail_rhythm(self):
        sections = [
            {"id": f"s{i}", "useCase": "features", "archetype": "stack",
             "slots": [{"name": "heading", "role": "heading",
                        "contract": "heading", "copy": f"Heading number {i} here."}]}
            for i in range(2)
        ]
        wf = sw.plan_wireframe({"sections": sections})
        errors = sw.validate_wireframe(wf, {"sections": sections})
        self.assertTrue(any("consecutive visually empty" in e for e in errors))

    def test_required_slot_consumption_fails(self):
        comp = {"sections": [item_section()]}
        wf = sw.plan_wireframe(comp)
        wf["sections"][0]["requiredSlots"].append("missing-action")
        self.assertTrue(any("not consumed" in e for e in sw.validate_wireframe(wf, comp)))


class HardQualityLintTest(unittest.TestCase):
    def test_cross_section_duplicate_sentence_fails(self):
        sentence = "Teams in every market grow with one connected platform."
        comp = {"sections": [
            {"id": "a", "slots": [{"name": "heading", "copy": sentence}]},
            {"id": "b", "slots": [{"name": "body", "copy": sentence}]},
        ]}
        self.assertEqual(len(cl.lint_cross_slot_duplicates(comp)), 1)

    def test_primitive_waterfall_fails(self):
        comp = {"sections": [item_section(contract="list", archetype="stack")]}
        self.assertEqual(len(cl.lint_grouping(comp)), 1)

    def test_grouped_feature_items_pass(self):
        self.assertEqual(cl.lint_grouping({"sections": [item_section("feature-item")]}), [])

    def test_conversion_without_action_fails(self):
        sec = {"id": "close", "useCase": "cta", "archetype": "stack",
               "slots": [{"name": "heading", "contract": "heading",
                          "role": "heading", "copy": "Take the next step today."}]}
        comp = {"sections": [sec]}
        wf = sw.plan_wireframe(comp)
        hits = cl.lint_wireframe_quality(comp, wf)
        self.assertTrue(any(rule == "section-completeness" for _, rule, _ in hits))

    def test_hero_unpainted_counterweight_fails(self):
        sec = {"id": "hero", "useCase": "hero", "archetype": "split",
               "alignment": {"anchor": "left", "counterweight": "copy"},
               "slots": [{"name": "copy", "contract": "paragraph", "role": "body",
                          "copy": "This is a substantive supporting sentence."}]}
        comp = {"sections": [sec]}
        wf = sw.plan_wireframe(comp)
        hits = cl.lint_wireframe_quality(comp, wf)
        self.assertTrue(any(rule == "hero-balance" for _, rule, _ in hits))


class GroupedRendererTest(unittest.TestCase):
    def test_grouped_items_render_n_card_wrappers(self):
        sec = item_section("feature-item")
        copy = cfc._cards_copy(sec)
        self.assertEqual(len(copy["cards"]), 3)
        for card, source in zip(copy["cards"], sec["slots"][1]["copy"]):
            self.assertEqual(card["heading"], source["heading"])
            self.assertEqual(card["body"], source["text"])

    def test_case_card_asset_reaches_split_mapping(self):
        sec = {
            "id": "hero", "useCase": "hero", "archetype": "split",
            "slots": [
                {"name": "heading", "role": "heading", "contract": "heading",
                 "copy": "Customer results."},
                {"name": "case", "role": "case-card", "contract": "card",
                 "mediaAspect": "landscape",
                 "asset": {"src": "assets/customer.png", "alt": "Customer"},
                 "copy": {"heading": "300%+", "text": "Growth.", "cta": "Read"}},
            ],
        }
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(layout["_caseCard"]["asset"], "assets/customer.png")
        self.assertTrue(any(m["contract"] == "image" for m in layout["blockMapping"]))

    def test_action_group_array_renders_every_conversion_action(self):
        sec = {
            "id": "close", "useCase": "cta", "archetype": "stack",
            "slots": [
                {"name": "heading", "role": "heading", "contract": "heading",
                 "copy": "Take the next step."},
                {"name": "actions", "role": "actionGroup", "contract": "button",
                 "copy": [
                     {"label": "Get a demo", "styleHint": "filled"},
                     {"label": "Start free", "styleHint": "outlined"},
                 ]},
            ],
        }
        mapping = cfc._cta_mapping(sec)
        labels = [m["usage"]["label"] for m in mapping if m["contract"] == "button"]
        self.assertEqual(labels, ["Get a demo", "Start free"])

    def test_collection_css_has_larger_parent_than_internal_gap(self):
        source = (REPO / "brand_pipeline" / "compose_section.py").read_text()
        self.assertIn("cs-modules", source)
        self.assertIn("cs-module--anatomy", source)
        self.assertIn("@container", source)


class CustomerStoryRegressionTest(unittest.TestCase):
    def test_lane_builds_strict_wireframe(self):
        path = REPO / "runs/hubspot-v2/brand/compose/customer-story/composition.json"
        comp = json.loads(path.read_text())
        wf = sw.plan_wireframe(comp)
        self.assertEqual(sw.validate_wireframe(wf, comp), [])
        story = next(s for s in wf["sections"] if s["id"] == "story")
        self.assertEqual(len(story["collections"][0]["items"]), 3)
        self.assertTrue(next(s for s in wf["sections"] if s["id"] == "hero")["visualAnchor"])
        self.assertEqual(cl.lint_composition(comp, wireframe=wf), [])


if __name__ == "__main__":
    unittest.main()
