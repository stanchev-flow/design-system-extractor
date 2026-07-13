#!/usr/bin/env python3
"""fix1 2026-07 — hubspot-v2 fidelity punch list, shared-code devices.

Covers the brand-agnostic, fact-gated devices this batch added:

  item-12a  navbar.utilityTier → two-tier bar (explicit opt-in; never gates on
            `twoTier` alone); trailing-cluster placement facts win
  item-12b  navbar.ctas[] as an ACTION GROUP — N measured registers per bar
            (single-cta brands keep the existing markup byte-identically)
  item-11   footer.bottomBar.anatomy: centered-stack (social row between
            hairlines → masked wordmark → legal → policy) — brands without the
            fact keep the inline row1/row2 bottom bar
  item-5    AS-59 (slop_audit.mjs): one filled primary register per action group
  item-9    IC-TAB static contract checks (interaction_audit tabs family)

Every device asserts BOTH arms: the fact-carrying brand gets the new anatomy,
the fact-less brand renders the pre-existing markup (Remote parity)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from unittest import mock  # noqa: E402

import brand_pipeline.compose_section as cs  # noqa: E402
import brand_pipeline.layout_library as ll  # noqa: E402
from brand_pipeline.component_render import (  # noqa: E402
    ComponentContext,
    footer_content,
    render_footer,
    render_navbar,
)
from brand_pipeline.compose_section import _navbar_props  # noqa: E402
from brand_pipeline.interaction_audit import audit_static  # noqa: E402

_BP = _REPO / "brand_pipeline"


def _doc(navbar: dict | None = None, footer: dict | None = None) -> dict:
    d: dict = {"brand": {"name": "Fixture"},
               "tokens": {"colors": {}, "surfaces": {}}}
    if navbar is not None:
        d["navbar"] = navbar
    if footer is not None:
        d["footer"] = footer
    return d


def _ctx(doc: dict) -> ComponentContext:
    return ComponentContext(doc, False)


_NAV_TWO_TIER = {
    "primary": [{"label": "Products", "href": "#p"},
                {"label": "Pricing", "href": "#r"}],
    "utility": [
        {"label": "Locale", "kind": "language-switcher"},
        {"label": "Support", "href": "#s"},
        {"label": "Log in", "href": "#l"},
        {"label": "Search", "kind": "icon-button"},
    ],
    "utilityTier": {"height": 40, "bg": "rgb(255, 255, 255)", "fontSize": 12,
                    "trailing": ["Log in", "Search"]},
    "ctas": [
        {"label": "Get one", "href": "#a", "style": "primary",
         "bg": "rgb(10, 10, 10)", "color": "rgb(255, 255, 255)",
         "borderRadius": 8, "height": 42, "padX": 16, "fontSize": 14},
        {"label": "Start free", "href": "#b", "style": "secondary",
         "bg": "rgb(255, 255, 255)", "color": "rgb(10, 10, 10)",
         "border": "2px solid rgb(10, 10, 10)", "borderRadius": 8,
         "height": 42, "padX": 16, "fontSize": 14},
    ],
    "measured": {"utilityBarHeight": 40, "primaryBarHeight": 88},
}


class TwoTierNavTest(unittest.TestCase):
    def test_utility_tier_renders_two_bars_with_placement(self):
        doc = _doc(navbar=dict(_NAV_TWO_TIER))
        html = render_navbar(doc, _ctx(doc), _navbar_props(doc))
        self.assertIn("cs-nav--twotier", html)
        self.assertEqual(html.count('class="cs-nav-tier '), 2)
        util_tier = html.split('cs-nav-tier--utility">')[1] \
                        .split('<div class="cs-nav-tier--primary')[0]
        # leading cluster keeps source order; trailing cluster follows the
        # declared placement labels (Log in before Search)
        self.assertLess(util_tier.index("Locale"), util_tier.index("Support"))
        self.assertLess(util_tier.index("Support"), util_tier.index("Log in"))
        self.assertLess(util_tier.index("Log in"), util_tier.index("Search"))
        # the tier run splits into two utility clusters (leading + trailing)
        self.assertEqual(util_tier.count('class="cs-nav-util"'), 2)
        # measured tier register rides scoped vars
        self.assertIn("--cs-utier-h: 40px", html)
        self.assertIn("--cs-utier-size: 12px", html)
        self.assertIn("--cs-ptier-h: 88px", html)
        # primary tier keeps logo + links + the action group
        primary_tier = html.split('cs-nav-tier--primary">')[1]
        self.assertIn("cs-navlinks", primary_tier)
        self.assertIn("cs-nav-actions", primary_tier)

    def test_factless_brand_keeps_single_bar(self):
        nav = dict(_NAV_TWO_TIER)
        nav.pop("utilityTier")
        doc = _doc(navbar=nav)
        html = render_navbar(doc, _ctx(doc), _navbar_props(doc))
        self.assertNotIn("cs-nav--twotier", html)
        self.assertNotIn("cs-nav-tier", html)
        self.assertIn('<nav class="cs-nav">', html)
        # the whole utility run stays inline in the single bar
        self.assertEqual(html.count('class="cs-nav-util"'), 1)

    def test_tier_never_gates_on_twotier_alone(self):
        # a brand can declare twoTier with a measured 0-height tier (collapsed);
        # only the explicit utilityTier contract may build the second bar
        nav = dict(_NAV_TWO_TIER)
        nav.pop("utilityTier")
        nav["twoTier"] = True
        nav["measured"] = {"utilityBarHeight": 0, "primaryBarHeight": 81}
        doc = _doc(navbar=nav)
        html = render_navbar(doc, _ctx(doc), _navbar_props(doc))
        self.assertNotIn("cs-nav--twotier", html)


class NavActionGroupTest(unittest.TestCase):
    def test_multi_cta_group_renders_measured_registers(self):
        doc = _doc(navbar=dict(_NAV_TWO_TIER))
        html = render_navbar(doc, _ctx(doc), _navbar_props(doc))
        self.assertIn('class="cs-nav-actions"', html)
        self.assertEqual(html.count("c-button--navcta"), 2)
        # each action paints its OWN register; the outlined secondary carries
        # its measured stroke through the border channel
        self.assertIn("--navcta-bg: rgb(10, 10, 10)", html)
        self.assertIn("--navcta-bg: rgb(255, 255, 255)", html)
        self.assertIn("--navcta-border: 2px solid rgb(10, 10, 10)", html)
        # exactly one action carries the border override (the secondary)
        self.assertEqual(html.count("--navcta-border:"), 1)

    def test_single_cta_keeps_existing_markup(self):
        nav = dict(_NAV_TWO_TIER)
        nav.pop("utilityTier")
        nav["ctas"] = [dict(_NAV_TWO_TIER["ctas"][0])]
        doc = _doc(navbar=nav)
        props = _navbar_props(doc)
        self.assertNotIn("actions", props)
        html = render_navbar(doc, _ctx(doc), props)
        self.assertNotIn("cs-nav-actions", html)
        self.assertEqual(html.count("c-button--navcta"), 1)

    def test_props_builder_gates_on_two_actions(self):
        doc = _doc(navbar=dict(_NAV_TWO_TIER))
        props = _navbar_props(doc)
        self.assertEqual([a["label"] for a in props["actions"]],
                         ["Get one", "Start free"])
        self.assertEqual(props["actions"][1]["style"]["border"],
                         "2px solid rgb(10, 10, 10)")


_REMOTE_BRAND = _REPO / "runs" / "remote" / "brand" / "brand.yaml"


@unittest.skipUnless(_REMOTE_BRAND.is_file(), "Remote run fixture not present")
class RemoteNavParityTest(unittest.TestCase):
    """The fact-less brand's bar must keep the single-tier grammar: Remote
    declares twoTier + a single cta but NO utilityTier — structural parity."""

    @classmethod
    def setUpClass(cls):
        import yaml
        cls.doc = yaml.safe_load(_REMOTE_BRAND.read_text())
        cls.html = render_navbar(cls.doc, _ctx(cls.doc), _navbar_props(cls.doc))

    def test_single_bar_no_tier_markup(self):
        self.assertIn('<nav class="cs-nav">', self.html)
        self.assertNotIn("cs-nav--twotier", self.html)
        self.assertNotIn("cs-nav-tier", self.html)

    def test_single_cta_no_action_group(self):
        self.assertNotIn("cs-nav-actions", self.html)
        self.assertEqual(self.html.count("c-button--navcta"), 1)
        self.assertNotIn("--navcta-border:", self.html)

    def test_remote_bottom_bar_keeps_inline_grammar(self):
        from brand_pipeline.component_render import prepare_chrome_glyphs
        brand_dir = _REMOTE_BRAND.parent
        doc = dict(self.doc)
        prepare_chrome_glyphs(doc, brand_dir)
        props = footer_content(doc)
        html = render_footer(doc, _ctx(doc), props)
        self.assertNotIn("c-foot-cstack", html)
        self.assertNotIn("c-footer--cstack", html)


_CSTACK_PROPS = {
    "columns": [{"heading": "Products",
                 "links": [{"label": "Alpha", "href": "#a"}]}],
    "social": [{"label": "LinkedIn", "href": "#li"}],
    "legal": "© 2026 Fixture",
    "legalLinks": [],
    "bottomBar": {
        "anatomy": "centered-stack",
        "divider": {"present": True, "color": "rgba(255, 255, 255, 0.11)"},
        "policyLinks": [{"label": "Privacy", "href": "#p"},
                        {"label": "Security", "href": "#s"}],
    },
    "footLogo": {"alt": "Fixture", "_dataUri": "data:image/svg+xml;base64,AAAA",
                 "_aspect": 3.5},
}


class FooterCenteredStackTest(unittest.TestCase):
    def test_centered_stack_renders_ordered_rows(self):
        doc = _doc(footer={})
        html = render_footer(doc, _ctx(doc), dict(_CSTACK_PROPS))
        self.assertIn("c-footer--cstack", html)
        stack = html.split('c-foot-cstack"')[1]
        # captured order: social row → wordmark → legal line → policy row
        self.assertLess(stack.index("c-foot-cstack-social"),
                        stack.index("c-foot-wordmark"))
        self.assertLess(stack.index("c-foot-wordmark"),
                        stack.index("c-foot-legal"))
        self.assertLess(stack.index("c-foot-legal"),
                        stack.index("c-foot-policy"))
        # wordmark = the brand's own art recolored via mask, sized by aspect
        self.assertIn("--cfw-mask:url('data:image/svg+xml;base64,AAAA')", html)
        self.assertIn("height:28px; width:98px", html)
        # measured hairline color rides the rule var
        self.assertIn("--cf-rule: rgba(255, 255, 255, 0.11)", html)

    def test_wordmark_without_aspect_degrades_to_img(self):
        props = dict(_CSTACK_PROPS)
        props["footLogo"] = {"alt": "Fixture",
                             "_dataUri": "data:image/svg+xml;base64,AAAA"}
        doc = _doc(footer={})
        html = render_footer(doc, _ctx(doc), props)
        self.assertIn('<img class="c-foot-wordmark"', html)
        self.assertNotIn("--cfw-mask", html)

    def test_inline_bottom_bar_grammar_unchanged(self):
        props = dict(_CSTACK_PROPS)
        props["bottomBar"] = {
            "divider": {"present": True, "color": "#ddd"},
            "policyLinks": [{"label": "Privacy", "href": "#p"}],
        }
        props.pop("footLogo")
        doc = _doc(footer={})
        html = render_footer(doc, _ctx(doc), props)
        self.assertNotIn("c-foot-cstack", html)
        self.assertIn("c-foot-bb-row1", html)
        self.assertIn("c-foot-bb-row2", html)

    def test_footer_content_rides_logo_only_with_anatomy(self):
        foot = {
            "columns": [{"heading": "Products",
                         "links": [{"label": "Alpha", "href": "#a"}]}],
            "logo": {"kind": "svg", "alt": "Fixture", "src": "wordmark.svg"},
            "bottomBar": {"anatomy": "centered-stack",
                          "divider": {"present": True}},
        }
        out = footer_content(_doc(footer=foot))
        self.assertIn("footLogo", out)
        foot2 = dict(foot)
        foot2["bottomBar"] = {"divider": {"present": True}}
        out2 = footer_content(_doc(footer=foot2))
        self.assertNotIn("footLogo", out2)


class SlopAS59SourceTest(unittest.TestCase):
    """AS-23-style source assertions: the AS-59 classifier + both scan passes."""

    def setUp(self):
        self.src = (_BP / "slop_audit.mjs").read_text()

    def test_register_classifier_compares_computed_paint(self):
        block = self.src[self.src.index("actionRegister"):]
        block = block[:block.index("auditActionGroup")]
        # computed paint shape, never brand hexes
        self.assertIn("backgroundColor", block)
        self.assertIn("borderTopWidth", block)
        self.assertIn("outlined:", block)
        self.assertIn("filled:", block)

    def test_flag_fires_on_duplicate_filled_registers(self):
        block = self.src[self.src.index("auditActionGroup"):]
        block = block[:block.index("for (const sec of scope)")]
        self.assertIn('startsWith("filled:")', block)
        self.assertIn("AS-59", block)
        # fewer than two actions is never a group violation
        self.assertIn("btns.length < 2", block)

    def test_both_scan_passes_exist(self):
        # in-section pass (nav excluded there) + the page-level chrome pass
        self.assertIn('sec.querySelectorAll(\'[class*="-actions"], .c-actions\')',
                      self.src)
        self.assertIn('g.closest(".cs-nav")', self.src)
        self.assertIn('.cs-nav [class*="-actions"], .cs-nav .c-actions',
                      self.src)
        self.assertIn('auditActionGroup(g, "page-nav")', self.src)


_TABS_OK = """
<div class="cs-tablist" role="tablist" aria-label="Case studies">
  <button class="cs-tab" type="button" role="tab" id="t-0" aria-selected="true"
          aria-controls="p-0">One</button>
  <button class="cs-tab" type="button" role="tab" id="t-1" aria-selected="false"
          tabindex="-1" aria-controls="p-1">Two</button>
</div>
<div role="tabpanel" id="p-0" aria-labelledby="t-0" tabindex="0">Panel one</div>
<div role="tabpanel" id="p-1" aria-labelledby="t-1" tabindex="0" hidden>Panel two</div>
"""


class TabsStaticAuditTest(unittest.TestCase):
    @staticmethod
    def _status(findings, check):
        return {f.check: f.status for f in findings
                if f.family == "tabs"}.get(check)

    def test_apg_shape_passes_all_static_checks(self):
        findings = audit_static(_TABS_OK, "fixture")
        for check in ("IC-TAB-01", "IC-TAB-02", "IC-TAB-03", "IC-TAB-04"):
            self.assertEqual(self._status(findings, check), "pass", check)

    def test_two_selected_tabs_fail_ic_tab_01(self):
        broken = _TABS_OK.replace('aria-selected="false"', 'aria-selected="true"')
        findings = audit_static(broken, "fixture")
        self.assertEqual(self._status(findings, "IC-TAB-01"), "fail")

    def test_missing_panel_wiring_fails_ic_tab_02(self):
        broken = _TABS_OK.replace('id="p-1"', 'id="p-x"')
        findings = audit_static(broken, "fixture")
        self.assertEqual(self._status(findings, "IC-TAB-02"), "fail")

    def test_missing_roving_tabindex_fails_ic_tab_03(self):
        broken = _TABS_OK.replace(' tabindex="-1"', "")
        findings = audit_static(broken, "fixture")
        self.assertEqual(self._status(findings, "IC-TAB-03"), "fail")

    def test_two_visible_panels_fail_ic_tab_03(self):
        broken = _TABS_OK.replace(' hidden>', ">")
        findings = audit_static(broken, "fixture")
        self.assertEqual(self._status(findings, "IC-TAB-03"), "fail")

    def test_unnamed_tablist_is_advisory_ic_tab_04(self):
        broken = _TABS_OK.replace(' aria-label="Case studies"', "")
        findings = audit_static(broken, "fixture")
        self.assertEqual(self._status(findings, "IC-TAB-04"), "advisory")

    def test_no_tablist_skips_family(self):
        findings = audit_static("<main><p>No tabs here.</p></main>", "fixture")
        self.assertEqual(self._status(findings, "IC-TAB-01"), "skip")


def _cards_pattern(archetype: str) -> ll.Pattern:
    return ll.Pattern(
        id=f"cards-{archetype}", use_case="features", archetype_ref=archetype,
        surface_intent="any", intent="test",
        content_shape={"alignment": {"value": "left", "counterweight": "cards"}},
        special_treatments=[], responsive={}, variant_knobs={},
        origin="extracted", confidence="high", scope="design-language",
        provenance=[])


class SideRailArchetypeGateTest(unittest.TestCase):
    """item-7 regression guard: `alignment: {value: left, counterweight: cards}`
    only owes the side-rail split when the pattern IS a split. A grid pattern
    with the same alignment fact ("full-width grid balances the left header",
    Remote's workflow-cards) must keep its header-above anatomy."""

    def _stamp(self, archetype: str) -> dict:
        layout = {"id": "sec"}
        with mock.patch.object(cs, "resolve_pattern",
                               return_value=(_cards_pattern(archetype), "ref")):
            cs.stamp_pattern_devices({}, layout, Path("/tmp/x.yaml"))
        return layout

    def test_split_archetype_stamps_side_rail(self):
        self.assertTrue(self._stamp("split").get("_sideRail"))

    def test_grid_archetype_does_not_stamp(self):
        self.assertNotIn("_sideRail", self._stamp("grid"))

    def test_stack_archetype_does_not_stamp(self):
        self.assertNotIn("_sideRail", self._stamp("stack"))


if __name__ == "__main__":
    unittest.main()
