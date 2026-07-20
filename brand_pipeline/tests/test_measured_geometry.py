#!/usr/bin/env python3
"""Regression tests for measured per-component geometry (hubspot-v3 2026-07).

Covers:
* ``measured_geometry`` — the deterministic, evidence-driven enricher that fills
  absent measured geometry (bandPadding / bandRhythm / deviceGeometry / gridEqualize
  / mediaScale / measured hero aspect) onto extracted patterns from a lane's own
  grounding + section-rect evidence. FILL-ABSENT-ONLY + idempotent.
* ``compose_from_composition._aspect_css`` — the fact-gated renderer support that
  honors a MEASURED ``W / H`` aspect ratio on a media slot (in addition to the coarse
  named enum classes), so an overlay hero renders at its measured band height.
* v3 chrome anatomy fidelity — nav utility/mega structure + footer columns/social/
  divider are authored at the v2 parity bar.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_measured_geometry
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BP = _REPO / "brand_pipeline"
for p in (str(_BP),):
    if p not in sys.path:
        sys.path.insert(0, p)

import yaml  # noqa: E402
import measured_geometry as mg  # noqa: E402
import compose_from_composition as cfc  # noqa: E402

V3 = _REPO / "runs" / "hubspot-v3" / "brand"


class TestAspectRatioPassthrough(unittest.TestCase):
    """The renderer honors measured aspect ratios AND the named enum classes."""

    def test_named_enum_classes_unchanged(self):
        self.assertEqual(cfc._aspect_css("wide"), "21 / 9")
        self.assertEqual(cfc._aspect_css("square"), "1 / 1")
        self.assertEqual(cfc._aspect_css("portrait"), "3 / 4")
        self.assertIsNone(cfc._aspect_css("landscape"))  # intrinsic default

    def test_measured_ratio_string_is_honored(self):
        # a measured band aspect (e.g. a 1440×772 hero) passes through verbatim
        self.assertEqual(cfc._aspect_css("36 / 19"), "36 / 19")
        self.assertEqual(cfc._aspect_css("1440 / 772"), "1440 / 772")
        self.assertEqual(cfc._aspect_css("16/9"), "16 / 9")

    def test_unknown_or_blank_is_intrinsic(self):
        self.assertIsNone(cfc._aspect_css(""))
        self.assertIsNone(cfc._aspect_css(None))
        self.assertIsNone(cfc._aspect_css("gibberish"))


class TestRegisterMapping(unittest.TestCase):
    def test_size_to_register_tiers(self):
        self.assertEqual(mg.register_for_size(80), "display")
        self.assertEqual(mg.register_for_size(48), "h1")
        self.assertEqual(mg.register_for_size(40), "h2")
        self.assertEqual(mg.register_for_size(24), "h3")
        self.assertEqual(mg.register_for_size(20), "h4")
        self.assertIsNone(mg.register_for_size(None))


class TestEnricherOnEvidence(unittest.TestCase):
    """The enricher derives measured facts from the lane's own grounding evidence."""

    @classmethod
    def setUpClass(cls):
        if not (V3 / "layout-library.yaml").is_file():
            raise unittest.SkipTest("hubspot-v3 lane not present")
        cls.doc = yaml.safe_load((V3 / "layout-library.yaml").read_text())

    def _fresh_pattern(self, pid):
        """A copy of a shipped pattern with its measured facts stripped, to prove the
        enricher RE-DERIVES them from evidence (not just reads the authored file)."""
        import copy
        pat = copy.deepcopy(next(p for p in self.doc["patterns"] if p["id"] == pid))
        cs = pat.get("contentShape") or {}
        for k in ("bandPadding", "bandRhythm", "deviceGeometry", "gridEqualize"):
            cs.pop(k, None)
        return pat

    def test_hero_gets_band_padding_and_rhythm_and_measured_aspect(self):
        pat = self._fresh_pattern("full-bleed-photo-hero")
        # strip the measured hero aspect too, restoring the coarse enum class
        for s in pat["contentShape"]["slots"]:
            if "background" in str(s.get("role") or ""):
                s["mediaAspect"] = "wide"
        doc = {"patterns": [pat]}
        summary = mg.enrich_layout_library(doc, V3)
        cs = pat["contentShape"]
        self.assertIn("bandPadding", cs, "hero must carry measured band padding")
        self.assertIn("bandRhythm", cs, "hero must carry measured box-to-box rhythm")
        bg = next(s for s in cs["slots"] if "background" in str(s.get("role") or ""))
        # the coarse enum was replaced with the measured band aspect (W / H)
        self.assertRegex(str(bg.get("mediaAspect")), r"^\d+ / \d+$")

    def test_card_grid_geometry_is_extractable(self):
        """Per-card geometry (deliverable 1): a measured card-grid pattern's cards
        must be able to carry measured register + grid-equalization from evidence —
        no card slot ships as name/role-only when the grounding has card geometry."""
        pat = self._fresh_pattern("sticky-copy-with-card-grid")
        doc = {"patterns": [pat]}
        mg.enrich_layout_library(doc, V3, fields=mg.ALL_FIELDS)
        cs = pat["contentShape"]
        geo = cs.get("deviceGeometry") or {}
        self.assertIn("cardRegister", geo, "card grid must carry a measured card register")
        self.assertIn("gridEqualize", cs, "card grid must carry measured equalization")
        self.assertEqual(cs["gridEqualize"]["heights"], "stretch")

    def test_fill_absent_only_is_idempotent(self):
        """Re-running the enricher on the already-authored library adds nothing (the
        v2/remote baselines stay byte-identical)."""
        import copy
        doc = copy.deepcopy(self.doc)
        summary = mg.enrich_layout_library(doc, V3, fields=mg.FIDELITY_FIELDS)
        self.assertEqual(summary, {}, f"shipped library should be complete: {summary}")

    def test_does_not_overwrite_authored_facts(self):
        pat = self._fresh_pattern("dark-band-cta")
        pat["contentShape"]["bandPadding"] = {"top": "9rem", "bottom": "9rem"}
        doc = {"patterns": [pat]}
        mg.enrich_layout_library(doc, V3)
        self.assertEqual(pat["contentShape"]["bandPadding"],
                         {"top": "9rem", "bottom": "9rem"})


class TestChromeAnatomyFidelity(unittest.TestCase):
    """v3 nav + footer are authored at the v2 parity bar (structure, not values)."""

    @classmethod
    def setUpClass(cls):
        p = V3 / "brand-chrome.yaml"
        if not p.is_file():
            raise unittest.SkipTest("hubspot-v3 chrome not present")
        cls.chrome = yaml.safe_load(p.read_text())

    def test_nav_utility_primary_and_mega_structure(self):
        nav = self.chrome["navbar"]
        # utility bar affordances
        util_labels = {str(u.get("label")) for u in (nav.get("utility") or [])}
        self.assertTrue({"Customer Support", "Contact Sales", "Log in"} <= util_labels)
        # primary links with mega-nav triggers
        primary = nav.get("primary") or []
        self.assertTrue(any(i.get("hasDropdown") for i in primary),
                        "primary links must declare mega-nav triggers")
        # a language affordance and an about menu
        self.assertIn("languageSwitcher", nav)
        self.assertIn("aboutMenu", nav)
        # CTA action group carries painted visibleLabel provenance
        ctas = nav.get("ctas") or []
        self.assertTrue(ctas and all("labelProvenance" in c for c in ctas),
                        "nav CTAs must carry visible-label provenance")

    def test_footer_columns_social_divider_legal(self):
        foot = self.chrome["footer"]
        cols = foot.get("columns") or []
        self.assertGreaterEqual(len(cols), 5, "footer must carry the measured columns")
        self.assertTrue(all(c.get("heading") and c.get("links") for c in cols))
        self.assertGreaterEqual(len(foot.get("social") or []), 5,
                                "footer must bind the harvested social glyph row")
        legal = foot.get("legal") or {}
        self.assertTrue(legal.get("text") and legal.get("links"))
        self.assertTrue(foot.get("separator"), "footer must carry the divider token")


if __name__ == "__main__":
    unittest.main()
