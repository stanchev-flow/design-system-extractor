#!/usr/bin/env python3
"""ANATOMY PRESENCE (anti-slop AS-81) + the HubSpot v3 tabbed-testimonial anatomy.

The failure this closes: a section whose DECLARATION names a tabbed/multi-panel
switcher or a stat device renders as a plain single block — no tab rail, no stats
(a renderer/anatomy capability gap invisible to a CSS-property diff). This module
covers:

- ``_declares_devices``: word-anchored device detection from slot names/roles,
  treatment kinds and useCase — and the NON-matches ("sans stat heading" is a
  heading, "deep-accent active state" is an accordion state, "inset rounded panel"
  is not a tab device);
- ``anatomy_presence_hits``: a rendered tab+stat section passes; a flattened plain
  quote for the SAME declaration fails both the tab-controls and stat-items rules;
  and the alignment guard fails OPEN (no false positives) on count mismatch;
- the HubSpot v3 acceptance: the composed replica renders the full tabbed-testimonial
  anatomy (3-tab rail, first active, all three DOM-verbatim panels, per-panel stat
  footer, measured active-underline + media fraction) — reusing the existing APG tab
  device, not a parallel mechanism;
- a regression guard: the held brands (hubspot-v2 / remote) raise no AS-81 hit.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import compose_replica as cr  # noqa: E402
import onbrand_check as ob  # noqa: E402

V3_YAML = REPO / "runs" / "hubspot-v3" / "brand" / "brand.yaml"


def _tab_section(html: str) -> str:
    i = html.find("cs-tabs-sec")
    if i < 0:
        return ""
    start = html.rfind("<section", 0, i)
    end = html.find("</section>", i)
    return html[start:end + len("</section>")]


class DeviceDeclaration(unittest.TestCase):
    """Word-anchored device detection — generic, brand-agnostic."""

    def test_tab_row_and_stat_row_slots_declare_both(self):
        sec = {"id": "t", "slots": [{"name": "tab-row", "role": "tab-row"},
                                    {"name": "stat-row", "role": "stat-row"}]}
        self.assertEqual(ob._declares_devices(sec), (True, True))

    def test_named_tabs_and_stat_rows_slots(self):
        sec = {"id": "t", "slots": [
            {"name": "tabs", "role": "segment pill run — 3 tab pills"},
            {"name": "stat-rows", "role": "ruled stat list — 2 serif numerals"}]}
        self.assertEqual(ob._declares_devices(sec), (True, True))

    def test_treatment_kinds_declare_devices(self):
        sec = {"id": "t", "slots": [],
               "treatments": [{"kind": "tabs"}, {"kind": "stat-rule"}]}
        self.assertEqual(ob._declares_devices(sec), (True, True))

    def test_usecase_tabbed_declares_tabs(self):
        self.assertTrue(ob._declares_devices({"id": "x", "useCase": "tabbed testimonial"})[0])

    def test_stat_heading_is_not_a_stat_device(self):
        # a heading whose copy happens to contain "stat" must NOT read as a stat device
        sec = {"id": "logo-wall", "slots": [
            {"name": "heading", "role": "heading — sans stat heading ('299,000+ customers…')"}]}
        self.assertEqual(ob._declares_devices(sec), (False, False))

    def test_active_state_and_panel_are_not_devices(self):
        # "deep-accent active state" (accordion) / "inset rounded panel" (media) must not
        # misfire as stat / tab devices respectively.
        acc = {"id": "acc", "slots": [
            {"name": "list", "role": "accordion items w/ deep-accent active state"}]}
        panel = {"id": "hero", "slots": [
            {"name": "background", "role": "inset rounded panel w/ noise-gradient art"}],
            "treatments": [{"kind": "panel-on-media"}]}
        self.assertEqual(ob._declares_devices(acc), (False, False))
        self.assertEqual(ob._declares_devices(panel), (False, False))


class AnatomyPresenceHits(unittest.TestCase):
    """The pure (comp, html) → hits contract."""

    COMP = {"sections": [
        {"id": "intro", "slots": [{"name": "heading", "role": "h2"}]},
        {"id": "tabbed-testimonial-with-stats",
         "slots": [{"name": "tab-row", "role": "tab-row"},
                   {"name": "stat-row", "role": "stat-row"}]},
    ]}

    RENDERED_OK = (
        '<section class="cs-section cs-intro"><h2>Hi</h2></section>'
        '<section class="cs-section cs-tabs-sec"><div role="tablist">'
        '<button role="tab" aria-selected="true">Enterprise</button>'
        '<button role="tab">Mid</button><button role="tab">Small</button></div>'
        '<div class="cs-tabcard-stats"><div class="cs-tabcard-stat">'
        '<span class="c-stat-value">12</span></div></div></section>')

    RENDERED_FLAT = (
        '<section class="cs-section cs-intro"><h2>Hi</h2></section>'
        '<section class="cs-section cs-split-sec"><p class="c-paragraph">a quote</p>'
        '<span class="c-caption">Adam Jones</span></section>')

    def test_rendered_device_passes(self):
        self.assertEqual(ob.anatomy_presence_hits(self.COMP, self.RENDERED_OK), [])

    def test_flattened_render_fails_both_rules(self):
        hits = ob.anatomy_presence_hits(self.COMP, self.RENDERED_FLAT)
        rules = {r for _sid, r, _m in hits}
        self.assertEqual(rules, {"anatomy-tab-controls", "anatomy-stat-items"})
        self.assertTrue(all(sid == "tabbed-testimonial-with-stats" for sid, _r, _m in hits))

    def test_count_mismatch_fails_open(self):
        # one rendered section vs two declared → unmappable → no hits (no false alarm)
        one = '<section class="cs-section cs-split-sec"><p>x</p></section>'
        self.assertEqual(ob.anatomy_presence_hits(self.COMP, one), [])

    def test_no_declared_device_is_vacuous(self):
        comp = {"sections": [{"id": "a", "slots": [{"name": "heading", "role": "h2"}]}]}
        html = '<section class="cs-section"><h2>x</h2></section>'
        self.assertEqual(ob.anatomy_presence_hits(comp, html), [])

    def test_footer_section_excluded_from_alignment(self):
        comp = {"sections": [
            {"id": "tabbed", "slots": [{"name": "tab-row", "role": "tab-row"}]}]}
        html = (self.RENDERED_OK.replace("cs-intro", "cs-tabs-sec-x")  # keep 1 body sec
                if False else
                '<section class="cs-section cs-tabs-sec"><div role="tablist">'
                '<button role="tab">a</button><button role="tab">b</button></div>'
                '<span class="c-stat-value">1</span></section>'
                '<section class="cs-footer-sec">footer</section>')
        # footer excluded → 1 body section aligns with 1 declared → passes
        self.assertEqual(ob.anatomy_presence_hits(comp, html), [])


class HubspotV3TabbedTestimonial(unittest.TestCase):
    """End-to-end: the composed v3 replica renders the full measured anatomy and clears
    AS-81; a synthetic flatten of the SAME page fails."""

    @classmethod
    def setUpClass(cls):
        if not V3_YAML.exists():
            raise unittest.SkipTest("hubspot-v3 brand lane not present")
        import tempfile
        cls._tmp = tempfile.TemporaryDirectory()
        out = Path(cls._tmp.name) / "replica"
        cr.build_replica_page(V3_YAML, out)
        cls.html = (out / "index.html").read_text()
        cls.comp = json.loads((out / "composition.json").read_text())
        cls.seg = _tab_section(cls.html)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "_tmp"):
            cls._tmp.cleanup()

    def test_tab_rail_three_controls_first_active(self):
        self.assertEqual(self.seg.count('role="tab"'), 3)
        self.assertIn('aria-selected="true"', self.seg)
        for label in ("Enterprise", "Mid-Sized Business", "Small Business"):
            self.assertIn(label, self.seg)

    def test_three_panels_all_dom_verbatim(self):
        self.assertEqual(self.seg.count('role="tabpanel"'), 3)
        for who in ("Adam Jones", "Whitney Hallock", "John Mothershead"):
            self.assertIn(who, self.seg)
        for src in ("045-unipart-1.png", "046-angel-fc.png", "047-youth-on-course.png"):
            self.assertIn(src, self.seg)

    def test_stat_footer_values_per_panel(self):
        # active Enterprise panel = 2 stats; the others = 3 (source DOM, verbatim)
        for value in ("12", "5", "300%+", "~350", "59%", "17%"):
            self.assertIn(f'>{value}<', self.seg)
        self.assertGreaterEqual(self.seg.count("cs-tabcard-stat"), 6)

    def test_measured_active_underline_and_media_fraction(self):
        self.assertIn("--cs-tab-active-rule: rgb(255, 72, 0)", self.seg)
        self.assertIn("--cs-tabs-media-frac: 0.56", self.seg)

    def test_reuses_apg_tab_device_script(self):
        # the shared structural tabs script (roving tabindex + arrow keys), not a parallel
        # mechanism, drives the rail.
        self.assertIn("data-tabs", self.seg)
        self.assertIn('querySelectorAll(\'[role="tab"]\'', self.html)

    def test_as81_passes_on_fixed_page(self):
        self.assertEqual(ob.anatomy_presence_hits(self.comp, self.html), [])

    def test_as81_catches_flattened_regression(self):
        import re
        defect = re.sub(
            r'<section class="cs-section cs-tabs-sec".*?</section>',
            '<section class="cs-section cs-split-sec">'
            '<p class="c-paragraph">a plain quote</p></section>',
            self.html, count=1, flags=re.S)
        hits = ob.anatomy_presence_hits(self.comp, defect)
        rules = {r for _sid, r, _m in hits}
        self.assertEqual(rules, {"anatomy-tab-controls", "anatomy-stat-items"})


class HeldBrandsNoFalsePositive(unittest.TestCase):
    """The held brands render their declared devices — AS-81 must not fire on them."""

    def test_committed_replicas_clear_as81(self):
        for brand in ("hubspot-v2", "remote"):
            d = REPO / "runs" / brand / "brand" / "compose" / "replica"
            ip, cp = d / "index.html", d / "composition.json"
            if not (ip.exists() and cp.exists()):
                continue
            hits = ob.anatomy_presence_hits(json.loads(cp.read_text()), ip.read_text())
            self.assertEqual(hits, [], f"{brand} raised an AS-81 hit: {hits}")


if __name__ == "__main__":
    unittest.main()
