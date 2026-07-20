from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import compose_from_composition as cfc  # noqa: E402
import composition_lint as cl  # noqa: E402
import section_wireframe as sw  # noqa: E402


def collection_section(items, columns=3, counterweight=False):
    slots = [
        {"name": "heading", "contract": "heading", "role": "heading",
         "copy": "A useful section heading."},
        {"name": "items", "contract": "feature-item", "role": "items", "copy": items},
    ]
    section = {
        "id": "fit", "useCase": "features", "archetype": "cards",
        "knobs": {"columns": str(columns)}, "slots": slots,
    }
    if counterweight:
        section["alignment"] = {"anchor": "left", "counterweight": "items"}
    return section


def item(heading="Clear outcome", body="A concise explanation supports the point.", asset=None):
    value = {"heading": heading, "text": body}
    if asset:
        value["asset"] = asset
    return value


class ComponentFitSolverTest(unittest.TestCase):
    def test_three_short_items_fit_three_columns(self):
        sec = collection_section([item(), item(), item()])
        fit = sw.solve_collection_fit(sec, sec["slots"][1])
        self.assertEqual(fit["chosenColumns"], 3)

    def test_three_long_peer_items_without_visual_choose_single_column(self):
        body = ("Fan sign-ups lived across ticketing, email, and social, with no "
                "single view of the supporter.")
        sec = collection_section([item("A growing club, scattered fan data.", body),
                                  item("One platform for marketing and service.", body),
                                  item("Personal at scale.", body)],
                                 counterweight=True)
        fit = sw.solve_collection_fit(sec, sec["slots"][1])
        self.assertEqual(fit["chosenColumns"], 1)
        self.assertEqual(fit["fillStrategy"], "single-column")
        self.assertFalse(fit["candidateWidths"][0]["feasible"])

    def test_three_over_two_with_explicit_lead_uses_lead_span(self):
        items = [item(asset="lead.svg"), item(asset="peer.svg"), item(asset="peer.svg")]
        items[0]["lead"] = True
        sec = collection_section(items, counterweight=True)
        fit = sw.solve_collection_fit(sec, sec["slots"][1])
        self.assertEqual(fit["chosenColumns"], 2)
        self.assertEqual(fit["fillStrategy"], "lead-span")
        self.assertEqual(fit["itemSpans"], [2, 1, 1])

    def test_three_over_two_peer_items_use_tail_span(self):
        sec = collection_section([item(asset="icon.svg")] * 3, counterweight=True)
        fit = sw.solve_collection_fit(sec, sec["slots"][1])
        self.assertEqual(fit["fillStrategy"], "tail-span")
        self.assertEqual(fit["itemSpans"], [1, 1, 2])

    def test_five_over_two_peer_items_use_tail_span(self):
        sec = collection_section([item(asset="icon.svg")] * 5, columns=2)
        fit = sw.solve_collection_fit(sec, sec["slots"][1], container_width=640)
        self.assertEqual(fit["chosenColumns"], 2)
        self.assertEqual(fit["fillStrategy"], "tail-span")
        self.assertEqual(fit["itemSpans"], [1, 1, 1, 1, 2])

    def test_four_over_two_needs_no_special_span(self):
        sec = collection_section([item()] * 4, columns=2)
        fit = sw.solve_collection_fit(sec, sec["slots"][1], container_width=640)
        self.assertEqual(fit["fillStrategy"], "complete-rows")
        self.assertEqual(fit["itemSpans"], [1, 1, 1, 1])

    def test_asymmetry_requires_real_counterweight(self):
        sec = collection_section([item(asset="icon.svg")] * 3, columns=2)
        slot = sec["slots"][1]
        slot["licensedAsymmetry"] = {"licensed": True, "counterweight": {"role": "art"}}
        rejected = sw.solve_collection_fit(sec, slot, container_width=640)
        self.assertNotEqual(rejected["fillStrategy"], "licensed-asymmetry")
        slot["licensedAsymmetry"]["counterweight"]["contract"] = "illustration"
        accepted = sw.solve_collection_fit(sec, slot, container_width=640)
        self.assertEqual(accepted["fillStrategy"], "licensed-asymmetry")
        self.assertEqual(accepted["itemSpans"], [1, 1, 1])

    def test_extreme_content_steps_to_one(self):
        huge = " ".join(["substantive"] * 90)
        sec = collection_section([item(body=huge)] * 3, counterweight=True)
        self.assertEqual(sw.solve_collection_fit(sec, sec["slots"][1])["chosenColumns"], 1)

    def test_narrow_icon_family_uses_icon_top(self):
        body = "A longer explanation that needs a coherent readable measure for every item."
        sec = collection_section([item(body=body, asset="icon.svg")] * 3, counterweight=True)
        fit = sw.solve_collection_fit(sec, sec["slots"][1])
        self.assertEqual(fit["internalAnatomy"], "icon-top")

    def test_width_math_accounts_for_padding_and_gutter(self):
        sec = collection_section([item(), item()], columns=2)
        fit = sw.solve_collection_fit(
            sec, sec["slots"][1], container_width=800, gutter=40, item_padding=24)
        self.assertEqual(fit["candidateWidths"][0]["itemWidth"], 380)
        self.assertEqual(fit["itemPadding"], 24)
        self.assertEqual(fit["gutter"], 40)

    def test_longest_visible_token_sets_minimum_not_asset_filename(self):
        demand = sw.content_demand(
            item(body="normal words Supercalifragilisticexpialidocious", asset="very-long-file-name.svg"))
        self.assertEqual(demand["longestUnbreakableToken"], 34)
        self.assertNotIn("asset", str(demand["longestUnbreakableToken"]))

    def test_responsive_thresholds_are_feasibility_derived(self):
        sec = collection_section([item(), item(), item()])
        fit = sw.solve_collection_fit(sec, sec["slots"][1])
        self.assertEqual(fit["responsiveBreakpoints"][-1]["columns"], fit["chosenColumns"])
        self.assertGreater(fit["responsiveBreakpoints"][-1]["minContainerWidth"],
                           fit["minItemWidth"])


class RendererConsumptionTest(unittest.TestCase):
    def test_adapter_consumes_declared_columns_and_anatomy(self):
        sec = collection_section([item(asset="icon.svg")] * 3)
        sec["_wireframeSection"] = {
            "collections": [{
                "columns": 2,
                "fillStrategy": "tail-span",
                "items": [{"span": 1}, {"span": 1}, {"span": 2}],
                "componentFit": {"chosenColumns": 2, "internalAnatomy": "icon-top"},
            }]
        }
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(layout["_moduleCols"], 2)
        self.assertEqual(layout["_collectionAnatomy"], "icon-top")
        self.assertEqual(layout["_collectionFill"]["strategy"], "tail-span")

    def test_rendered_customer_story_stamps_fit_and_testimonial(self):
        lane = REPO / "runs/hubspot-v2/brand/compose/customer-story"
        comp = json.loads((lane / "composition.json").read_text())
        brand = REPO / "runs/hubspot-v2/brand/brand.yaml"
        with tempfile.TemporaryDirectory() as tmp:
            cfc.render_composition(comp, brand, tmp, style_id="corporate-saas-clean",
                                   brand_dir=brand.parent)
            html = (Path(tmp) / "index.html").read_text()
        self.assertIn('data-fit-columns="2"', html)
        self.assertIn('data-fit-anatomy="icon-top"', html)
        self.assertIn('data-fill-strategy="tail-span"', html)
        self.assertIn('data-grid-span="2"', html)
        self.assertIn('data-component-contract="testimonial"', html)
        self.assertIn("046-angel-fc.png", html)


class TestimonialPlanningTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lane = REPO / "runs/hubspot-v2/brand/compose/customer-story"
        cls.comp = json.loads((cls.lane / "composition.json").read_text())
        cls.wf = sw.plan_wireframe(cls.comp)

    def test_copy_shape_selects_atomic_testimonial(self):
        quote = next(s for s in self.wf["sections"] if s["id"] == "quote")["testimonial"]
        self.assertEqual(quote["componentContract"], "testimonial")
        self.assertTrue(quote["complete"])
        self.assertEqual(quote["attribution"]["name"], "Whitney Hallock")

    def test_compatible_client_photo_binds(self):
        quote = next(s for s in self.wf["sections"] if s["id"] == "quote")["testimonial"]
        self.assertEqual(quote["asset"], "046-angel-fc.png")
        self.assertEqual(quote["internalAnatomy"], "portrait-side")

    def test_no_avatar_fallback_requests_asset_without_dead_media(self):
        sec = {
            "id": "q", "useCase": "testimonial", "archetype": "stack",
            "slots": [{"name": "quote", "contract": "testimonial", "copy": {
                "quote": "A grounded customer statement.", "name": "A Person",
                "role": "Operator",
            }}],
        }
        wf = sw.plan_wireframe({"sections": [sec]})
        plan = wf["sections"][0]["testimonial"]
        self.assertEqual(plan["assetStatus"], "requested")
        self.assertEqual(plan["internalAnatomy"], "quote-card")
        self.assertIsNotNone(plan["assetRequest"])

    def test_bare_testimonial_fails_semantic_gate(self):
        wf = json.loads(json.dumps(self.wf))
        quote = next(s for s in wf["sections"] if s["id"] == "quote")
        quote["testimonial"]["componentContract"] = "paragraph"
        hits = cl.lint_wireframe_quality(self.comp, wf)
        self.assertTrue(any(rule == "testimonial-integrity" for _, rule, _ in hits))

    def test_exact_customer_collection_is_two_column_icon_top(self):
        story = next(s for s in self.wf["sections"] if s["id"] == "story")
        collection = story["collections"][0]
        self.assertEqual(collection["columns"], 2)
        self.assertEqual(collection["componentFit"]["internalAnatomy"], "icon-top")
        self.assertEqual(collection["fillStrategy"], "tail-span")
        self.assertEqual([item["span"] for item in collection["items"]], [1, 1, 2])


class RenderedHardGateTest(unittest.TestCase):
    def test_as75_and_as76_catch_squeezed_and_empty_fixtures(self):
        html = """<!doctype html><style>
          #sec-0{width:700px}.grid{display:grid;grid-template-columns:repeat(3,100px)}
          .cs-module{width:100px}.empty{height:500px}.tiny{height:80px}
        </style>
        <div id="sec-0"><section>
          <div class="grid" data-component-fit="collection" data-fit-min-item="240"
            data-fit-max-heading-lines="3" data-fit-max-body-lines="5"
            data-fit-anatomy="icon-top">
            <article class="cs-module" data-internal-anatomy="icon-inline">
              <h3 class="c-heading">A heading that wraps too much</h3>
              <p class="c-paragraph">Body copy in a squeezed component.</p>
            </article>
          </div>
          <section class="empty" data-testimonial-intent="true">
            <article class="tiny" data-component-contract="testimonial"
              data-testimonial-asset="bound" data-testimonial-max-empty="0.68">
              <blockquote class="cs-testimonial-quote">Quote</blockquote>
              <div class="c-person">Person</div>
            </article>
          </section>
        </section></div>"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.html"
            path.write_text(html)
            proc = subprocess.run(
                ["node", str(REPO / "brand_pipeline/slop_audit.mjs"), str(path)],
                cwd=REPO, text=True, capture_output=True, check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("AS-75", proc.stdout)
        self.assertIn("AS-76", proc.stdout)

    def test_as77_catches_rendered_orphan_final_row(self):
        html = """<!doctype html><style>
          #sec-0{width:640px}.grid{display:grid;grid-template-columns:repeat(2,1fr);
          column-gap:32px}.cs-module{height:80px}
        </style><div id="sec-0"><section>
          <div class="grid" data-component-fit="collection" data-fit-columns="2"
            data-fill-strategy="complete-rows">
            <article class="cs-module" data-grid-span="1">One</article>
            <article class="cs-module" data-grid-span="1">Two</article>
            <article class="cs-module" data-grid-span="1">Three</article>
          </div></section></div>"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.html"
            path.write_text(html)
            proc = subprocess.run(
                ["node", str(REPO / "brand_pipeline/slop_audit.mjs"), str(path)],
                cwd=REPO, text=True, capture_output=True, check=False)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("AS-77", proc.stdout)


if __name__ == "__main__":
    unittest.main()
