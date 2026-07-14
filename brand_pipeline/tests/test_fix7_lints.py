#!/usr/bin/env python3
"""fix7 composition lints + adapter/audit follow-ups:

- punch 2 (AS-63)  knob-consumption lint: registry honesty (every entry names real
  consuming code), no-consumer knobs fail, out-of-vocabulary values fail (the
  supportKind proving case), archetype-declared enums pass (YAML-boolean footgun
  included), all 11 live lanes lint clean.
- punch 6 (AS-65)  content-redundancy lint: the developer note shape fires; novel
  notes / structured lists alone stay clean.
- pass-3 follow-ups: cta-contract actions expand to real buttons (1), _cta_copy
  dict-guards (2), dict-shaped stat vocabulary (3), AS-11 stat visibility (5, via
  the slop source), flow header row stamp (6), testimonial split binding (7),
  eyebrow contrast guard on scrim surfaces (8), composed-page creative scope (9).
- stage-B follow-up: knobs.columns finally consumed (schema example knob).
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import composition_lint as cl  # noqa: E402
import compose_from_composition as cfc  # noqa: E402


class KnobConsumptionLint(unittest.TestCase):
    """AS-63: a knob with no consumer / an unconsumable value is a HARD lint."""

    def test_registry_entries_name_real_consuming_code(self):
        """Registry honesty: every registered knob name literally appears in the
        adapter/composer source — an entry without a consumer is the lie the
        lint exists to catch."""
        adapter = (REPO / "brand_pipeline" / "compose_from_composition.py").read_text()
        composer = (REPO / "brand_pipeline" / "compose_section.py").read_text()
        for name in cl.KNOB_CONSUMERS:
            self.assertTrue(name in adapter or name in composer,
                            f"registry knob {name!r} has no consuming code")

    def test_unknown_knob_fails(self):
        comp = {"sections": [{"id": "x", "knobs": {"wobble": "on"}, "slots": []}]}
        hits = cl.lint_knobs(comp)
        self.assertEqual(len(hits), 1)
        self.assertIn("NO consumer", hits[0][1])

    def test_support_kind_out_of_vocabulary_fails(self):
        """The proving case's failure shape: a value no consumer can render."""
        comp = {"sections": [{"id": "demo", "archetypeRef": "hero-form-split",
                              "knobs": {"supportKind": "carousel"}, "slots": []}]}
        hits = cl.lint_knobs(comp)
        self.assertEqual(len(hits), 1)
        self.assertIn("vocabulary", hits[0][1])

    def test_support_kind_list_now_consumable(self):
        comp = {"sections": [{"id": "demo", "archetypeRef": "hero-form-split",
                              "knobs": {"supportKind": "list"}, "slots": []}]}
        self.assertEqual(cl.lint_knobs(comp), [])

    def test_archetype_declared_enum_accepts_yaml_boolean_spellings(self):
        # heroes-saas [on, off] enums parse as [True, False] (the pass-1 YAML 1.1
        # footgun) — both spellings must validate, never a vacuous mismatch.
        comp = {"sections": [{"id": "dev", "archetypeRef": "hero-search-first",
                              "knobs": {"popularRow": "on"}, "slots": []}]}
        self.assertEqual(cl.lint_knobs(comp), [])

    def test_archetype_enum_violation_fails(self):
        comp = {"sections": [{"id": "dev", "archetypeRef": "hero-form-split",
                              "knobs": {"formFrame": "floating"}, "slots": []}]}
        self.assertEqual(len(cl.lint_knobs(comp)), 1)

    def test_code_consumed_knobs_pass_without_an_archetype(self):
        comp = {"sections": [{"id": "s", "knobs": {
            "columns": "3", "align": "left", "mediaSide": "right"}, "slots": []}]}
        self.assertEqual(cl.lint_knobs(comp), [])

    def test_bad_columns_value_fails(self):
        comp = {"sections": [{"id": "s", "knobs": {"columns": "wide"}, "slots": []}]}
        self.assertEqual(len(cl.lint_knobs(comp)), 1)

    def test_all_live_lanes_lint_clean(self):
        lanes = sorted((REPO / "runs/hubspot-v2/brand/compose/hero-archetypes")
                       .glob("*/composition.json"))
        lanes += sorted((REPO / "runs/hubspot-v2/brand/compose")
                        .glob("style-bakeoff-*/product-launch/composition.json"))
        checked = 0
        for p in lanes:
            if "_before" in str(p) or "_iter1" in str(p):
                continue
            hits = cl.lint_composition(json.loads(p.read_text()))
            self.assertEqual(hits, [], f"{p} fails the composition lint")
            checked += 1
        self.assertGreaterEqual(checked, 11)


class ContentRedundancyLint(unittest.TestCase):
    """AS-65: two sibling slots enumerating the same content in two registers."""

    OLD_DEVELOPER = {"sections": [{"id": "sec-0", "slots": [
        {"name": "search", "contract": "form",
         "copy": {"fields": [{"label": "Search the docs"}], "submit": "Search",
                  "note": "Popular: CRM API \u00b7 UI extensions \u00b7 OAuth \u00b7 webhooks"}},
        {"name": "popular", "contract": "link",
         "copy": [{"text": "CRM API"}, {"text": "UI extensions"},
                  {"text": "OAuth"}, {"text": "Webhooks"}]},
    ]}]}

    def test_the_developer_note_shape_fires(self):
        hits = cl.lint_redundancy(self.OLD_DEVELOPER)
        self.assertEqual(len(hits), 1)
        self.assertIn("structured device", hits[0][1])

    def test_a_novel_note_is_clean(self):
        comp = json.loads(json.dumps(self.OLD_DEVELOPER))
        comp["sections"][0]["slots"][0]["copy"]["note"] = \
            "We'll email you within one business day to schedule."
        self.assertEqual(cl.lint_redundancy(comp), [])

    def test_a_structured_list_alone_is_clean(self):
        comp = {"sections": [{"id": "s", "slots": [
            {"name": "popular", "contract": "link",
             "copy": [{"text": "CRM API"}, {"text": "OAuth"}]}]}]}
        self.assertEqual(cl.lint_redundancy(comp), [])

    def test_current_developer_composition_is_clean(self):
        comp = json.loads((REPO / "runs/hubspot-v2/brand/compose/hero-archetypes"
                           / "developer/composition.json").read_text())
        self.assertEqual(cl.lint_redundancy(comp), [])


class OnbrandLintRows(unittest.TestCase):
    """The gate rows are fact-gated on a generated composition.json."""

    def test_composed_lane_gets_clean_rows(self):
        import onbrand_check as oc
        rows = oc.check_composition_lints(
            REPO / "runs/hubspot-v2/brand/compose/hero-archetypes/demo")
        self.assertEqual([r[0] for r in rows],
                         ["knob-consumption", "content-redundancy"])
        self.assertTrue(all(passed for _rid, _l, passed, _d in rows))

    def test_replica_lane_gets_no_rows(self):
        import onbrand_check as oc
        rows = oc.check_composition_lints(
            REPO / "runs/hubspot-v2/brand/compose/replica")
        self.assertEqual(rows, [])

    def test_generation_loop_carries_the_prefilter(self):
        src = (REPO / "brand_pipeline" / "generate_composition.py").read_text()
        self.assertIn("composition_lint.lint_composition", src)
        self.assertIn("lint-fail", src)


class CtaContractActions(unittest.TestCase):
    """Pass-3 follow-up 1: `cta`-contract action slots expand into real buttons —
    the conversion composer never invents a signup form over declared actions."""

    def _section(self, copy):
        return {"id": "close", "useCase": "cta", "archetype": "stack",
                "slots": [
                    {"name": "heading", "role": "closing-header",
                     "contract": "header", "copy": {"heading": "Start today"}},
                    {"name": "actions", "role": "closing-actions",
                     "contract": "cta", "copy": copy},
                ]}

    def test_list_cta_copy_expands_to_buttons_and_no_form(self):
        mapping = cfc._cta_mapping(self._section(
            [{"label": "Get a demo"}, {"label": "See pricing"}]))
        contracts = [m["contract"] for m in mapping]
        self.assertEqual(contracts.count("button"), 2)
        self.assertNotIn("form", contracts)
        second = [m for m in mapping if m["contract"] == "button"][1]
        self.assertIn("styleHint", second["usage"])

    def test_string_cta_copy_expands_to_one_button(self):
        mapping = cfc._cta_mapping(self._section("Get a demo"))
        contracts = [m["contract"] for m in mapping]
        self.assertEqual(contracts.count("button"), 1)
        self.assertNotIn("form", contracts)

    def test_actionless_legacy_conversion_keeps_the_form(self):
        sec = {"id": "close", "useCase": "cta", "archetype": "stack",
               "slots": [{"name": "heading", "role": "header",
                          "contract": "header", "copy": {"heading": "Join"}}]}
        mapping = cfc._cta_mapping(sec)
        self.assertIn("form", [m["contract"] for m in mapping])

    def test_button_slots_still_win_over_cta_expansion(self):
        sec = self._section([{"label": "Ghost"}])
        sec["slots"].append({"name": "real", "role": "primary",
                             "contract": "button", "copy": "Get started"})
        mapping = cfc._cta_mapping(sec)
        labels = [m["usage"].get("label") for m in mapping
                  if m["contract"] == "button"]
        self.assertEqual(labels, ["Get started"])


class CtaCopyDictGuards(unittest.TestCase):
    """Pass-3 follow-up 2: a plain-string heading never echoes into eyebrow/body."""

    def test_string_heading_copy_stays_out_of_eyebrow_and_body(self):
        sec = {"id": "close", "useCase": "cta", "archetype": "stack",
               "slots": [{"name": "heading", "role": "closing-title",
                          "contract": "heading", "copy": "One clear claim."}]}
        copy = cfc._cta_copy(sec)
        self.assertEqual(copy["heading"], "One clear claim.")
        self.assertEqual(copy["eyebrow"], "")
        self.assertEqual(copy["body"], "")

    def test_dict_header_keys_still_bind(self):
        sec = {"id": "close", "useCase": "cta", "archetype": "stack",
               "slots": [{"name": "heading", "role": "closing-title",
                          "contract": "header",
                          "copy": {"eyebrow": "Next step", "heading": "Start",
                                   "body": "One supporting line."}}]}
        copy = cfc._cta_copy(sec)
        self.assertEqual(copy["eyebrow"], "Next step")
        self.assertEqual(copy["body"], "One supporting line.")


class StatVocabulary(unittest.TestCase):
    """Pass-3 follow-up 3: dict-shaped stat copy binds the stat renderer."""

    def _flow_mapping(self, copy):
        sec = {"id": "proof", "useCase": "gallery", "archetype": "stack",
               "slots": [{"name": "stats", "role": "metrics-band",
                          "contract": "stat-block", "copy": copy}]}
        return cfc.composition_to_layout(sec)["blockMapping"]

    def test_singular_dict_stat_binds(self):
        mapping = self._flow_mapping({"value": "299,000+", "label": "customers"})
        stats = [m for m in mapping if m["contract"] == "stat"]
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]["usage"]["value"], "299,000+")
        self.assertEqual(stats[0]["group"], "stats")

    def test_nested_list_dict_stat_expands(self):
        mapping = self._flow_mapping({"stats": [
            {"value": "1,500+", "label": "beta teams"},
            {"value": "92%", "label": "kept it on"}]})
        stats = [m for m in mapping if m["contract"] == "stat"]
        self.assertEqual(len(stats), 2)

    def test_array_stat_copy_unchanged(self):
        mapping = self._flow_mapping([
            {"value": "1,500+", "label": "beta teams"},
            {"value": "92%", "label": "kept it on"}])
        stats = [m for m in mapping if m["contract"] == "stat"]
        self.assertEqual(len(stats), 2)

    def test_slop_inventory_counts_stat_cells(self):
        src = (REPO / "brand_pipeline" / "slop_audit.mjs").read_text()
        self.assertIn('".c-row, li, details, .c-stat"', src)


class FlowHeaderRowStamp(unittest.TestCase):
    """Pass-3 follow-up 6: a header block stamps the heading row, so a lead-in
    sibling paragraph rides the heading→body rung, not the block stride."""

    def test_header_contract_stamps_data_row_heading(self):
        import compose_section as cs
        doc = yaml.safe_load((REPO / "runs/hubspot-v2/brand/brand.yaml").read_text())
        cs.attach_asset_inventory(doc, REPO / "runs/hubspot-v2/brand")
        surf = (doc.get("tokens") or {}).get("surfaces", {}).get("surface/primary")
        ctx = cs.cr.make_context(doc, "surface/primary", surf)
        rendered = [
            {"slot": "flow", "role": "section header", "contract": "header",
             "html": '<div class="c-header"><h2 class="c-heading">T</h2></div>',
             "group": None, "origin": None},
            {"slot": "flow", "role": "lead-in", "contract": "paragraph",
             "html": '<p class="c-paragraph">Lead-in body copy.</p>',
             "group": None, "origin": None},
        ]
        html = cs.compose_generic_flow(doc, {"id": "s", "archetype": "generic-flow"},
                                       ctx, rendered, None)
        self.assertIn('data-row="heading"', html.split("c-header")[0] + "c-header")
        self.assertIn('data-row="body"', html)


class TestimonialSplitBinding(unittest.TestCase):
    """Pass-3 follow-up 7: the testimonial contract binds in the split copy path."""

    SEC = {"id": "who-believes", "useCase": "testimonial", "archetype": "split",
           "slots": [
               {"name": "quote", "role": "pull-quote", "contract": "testimonial",
                "copy": {"quote": "It kept our pipeline honest.",
                         "name": "Dana Reyes", "role": "VP Marketing"}},
               {"name": "media", "role": "supporting-figure", "contract": "image",
                "copy": None},
           ]}

    def test_split_copy_binds_quote_and_attribution(self):
        copy = cfc._split_copy(self.SEC)
        self.assertEqual(copy["quote"], "It kept our pipeline honest.")
        self.assertEqual(copy["body"], "It kept our pipeline honest.")
        self.assertEqual(copy["attribution"], "Dana Reyes — VP Marketing")

    def test_role_keyword_quote_still_wins(self):
        sec = json.loads(json.dumps(self.SEC))
        sec["slots"].insert(0, {"name": "lede", "role": "quote", "contract":
                                "paragraph", "copy": {"quote": "Role-bound quote."}})
        self.assertEqual(cfc._split_copy(sec)["quote"], "Role-bound quote.")

    def test_attribution_renders_in_the_split(self):
        import compose_section as cs
        doc = yaml.safe_load((REPO / "runs/hubspot-v2/brand/brand.yaml").read_text())
        cs.attach_asset_inventory(doc, REPO / "runs/hubspot-v2/brand")
        layout, merged, _ = cfc.adapt_brand_section(
            json.loads(json.dumps(self.SEC)), doc)
        surf = (doc.get("tokens") or {}).get("surfaces", {}).get("surface/primary")
        ctx = cs.cr.make_context(doc, "surface/primary", surf)
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, layout["id"]: merged}
        try:
            html = cs.compose_info_band(doc, layout, ctx, [], None)
        finally:
            cs.LAYOUT_COPY.pop(layout["id"], None)
        self.assertIn("It kept our pipeline honest.", html)
        self.assertIn("Dana Reyes — VP Marketing", html)


class KnobColumnsConsumer(unittest.TestCase):
    """Stage-B/schema follow-up: knobs.columns (the schema's own example) is the
    MODULE-RUN track count — distinct from the registration grid (12 registration
    columns are not 12 card tracks)."""

    def test_columns_knob_sets_module_cols_and_the_grid_fallback(self):
        sec = {"id": "s", "useCase": "features", "archetype": "cards",
               "knobs": {"columns": "4"}, "slots": []}
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(layout["_moduleCols"], 4)
        self.assertEqual(layout["_grid"], {"columns": 4, "source": "knob"})

    def test_declared_grid_keeps_registration_but_knob_owns_module_tracks(self):
        sec = {"id": "s", "useCase": "features", "archetype": "cards",
               "grid": {"columns": 12, "gutter": "2rem"},
               "knobs": {"columns": "4"}, "slots": []}
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(layout["_grid"], {"columns": 12, "gutter": "2rem"})
        self.assertEqual(layout["_moduleCols"], 4)

    def test_knobless_sections_unchanged(self):
        sec = {"id": "s", "useCase": "features", "archetype": "cards", "slots": []}
        layout = cfc.composition_to_layout(sec)
        self.assertNotIn("_grid", layout)
        self.assertNotIn("_moduleCols", layout)

    def test_module_track_count_re_scopes_the_card_grid(self):
        """The swiss bakeoff regression shape: 12 registration columns + a 4-column
        module knob → the card track re-scopes --grid-cols to 4, never 12."""
        import compose_section as cs
        doc = yaml.safe_load((REPO / "runs/hubspot-v2/brand/brand.yaml").read_text())
        cs.attach_asset_inventory(doc, REPO / "runs/hubspot-v2/brand")
        surf = (doc.get("tokens") or {}).get("surfaces", {}).get("surface/primary")
        ctx = cs.cr.make_context(doc, "surface/primary", surf)
        layout = {"id": "s", "archetype": "cards", "_moduleCols": 4,
                  "_grid": {"columns": 12, "gutter": "2rem"}}
        cards = [{"caption": c, "body": "Body."} for c in ("A", "B", "C", "D")]
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY,
                          "s": {"heading": "", "eyebrow": "", "cards": cards}}
        try:
            html = cs.compose_features_cards(doc, layout, ctx, [], None)
        finally:
            cs.LAYOUT_COPY.pop("s", None)
        self.assertIn("cs-modules--cols", html)
        self.assertIn("--grid-cols: 4", html)


class EyebrowContrastGuard(unittest.TestCase):
    """Pass-3 follow-up 8: the accent section's eyebrow deployment is contrast-
    guarded — a scrim surface whose textAccent can't carry small text re-registers
    the eyebrow to primary ink; high-contrast pairs are untouched."""

    def _vars(self, surf_role):
        import compose_page as cp
        doc = yaml.safe_load((REPO / "runs/hubspot-v2/brand/brand.yaml").read_text())
        surf = (doc.get("tokens") or {}).get("surfaces", {}).get(surf_role)
        return cp.section_vars(doc, "#sec-0", surf, display_size="5rem",
                               accent_on=True, surf_role=surf_role, style_ctx=None)

    def test_photo_scrim_surface_re_registers_the_eyebrow(self):
        css = self._vars("surface/photo-hero")     # #ff4800 on #55453e = 2.68:1
        self.assertIn("--c-eyebrow-color: var(--c-ink)", css)

    def test_deep_inverse_surface_keeps_the_accent(self):
        css = self._vars("surface/inverse")        # #ff4800 on #042729 >= 4.5:1
        self.assertNotIn("--c-eyebrow-color", css)

    def test_non_accent_sections_unchanged(self):
        import compose_page as cp
        doc = yaml.safe_load((REPO / "runs/hubspot-v2/brand/brand.yaml").read_text())
        surf = (doc.get("tokens") or {}).get("surfaces", {}).get("surface/primary")
        css = cp.section_vars(doc, "#sec-1", surf, display_size="5rem",
                              accent_on=False, surf_role="surface/primary",
                              style_ctx=None)
        self.assertIn("--c-accent: var(--c-ink)", css)


class ComposedPageCreativeScope(unittest.TestCase):
    """Pass-3 follow-up 9: a generated composition.v1 render takes the creative
    fidelity scope with or without a data-archetype stamp; replicas never do."""

    def test_generated_composition_detection(self):
        import onbrand_check as oc
        self.assertIsNotNone(oc._generated_composition(
            REPO / "runs/hubspot-v2/brand/compose/hero-archetypes/demo"))
        self.assertIsNone(oc._generated_composition(
            REPO / "runs/hubspot-v2/brand/compose/replica"))

    def test_fidelity_uses_the_stamped_surface_roles_for_composed_pages(self):
        import onbrand_check as oc
        doc = yaml.safe_load((REPO / "runs/hubspot-v2/brand/brand.yaml").read_text())
        layout = (doc.get("layouts") or [{}])[0]
        html = ('<div id="sec-0" class="cs-surface" data-layout="hero-x" '
                'data-surface="surface/primary"><section></section></div>')
        facts = {"bg_in_css": False, "heading_family": None, "local_imgs": ["x.png"],
                 "missing_imgs": []}
        checks = oc.check_fidelity(
            doc, html, layout, facts,
            render_dir=REPO / "runs/hubspot-v2/brand/compose/hero-archetypes/demo")
        surface_row = next(c for c in checks if c[0].startswith("Surface"))
        self.assertIn("creative-mode scope", surface_row[0])


if __name__ == "__main__":
    unittest.main()
