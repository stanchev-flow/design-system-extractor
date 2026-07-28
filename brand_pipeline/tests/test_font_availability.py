#!/usr/bin/env python3
"""Tests for the typography availability fact (spec/font-availability-schema.md).

The hole these close: ``mine_css.py`` has always dumped every ``@font-face`` rule into
the evidence, but nothing read a ``src:`` URL, so a brand could declare a family the
pipeline had no way of delivering and no artifact recorded that it could not. The
harvester turns those captured rules into a delivery fact per family, and the fact must
survive being run against REAL evidence — not just a hand-written fixture.

Run:  ./venv/bin/python -m pytest brand_pipeline/tests/test_font_availability.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
for _p in (str(_REPO / "tools" / "extract"), str(_REPO / "brand_pipeline")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import harvest_font_faces as hff  # noqa: E402
import tokens_css as tc  # noqa: E402

# A capture's worth of @font-face rows in exactly the shape mine_css.py writes them:
# a remote brand face, an openly licensed webfont, and a data-URI icon font.
FIXTURE_RULES = {
    "schemaVersion": "css-mine.v1",
    "sources": ["site.css"],
    "rules": [
        {"file": "site.css", "media": "", "kind": "rule", "selector": "@font-face",
         "decls": ("font-family:Fixture Sans;src:url(https://cdn.example.test/"
                   "FixtureSansWeb-Regular.woff2)format(\"woff2\");font-weight:400;"
                   "font-style:normal;font-display:swap")},
        {"file": "site.css", "media": "", "kind": "rule", "selector": "@font-face",
         "decls": ("font-family:Fixture Sans;src:url(https://cdn.example.test/"
                   "FixtureSansWeb-Medium.woff2)format(\"woff2\");font-weight:500;"
                   "font-style:italic")},
        {"file": "site.css", "media": "", "kind": "rule", "selector": "@font-face",
         "decls": ("font-family:'Open Face';src:url(https://fonts.gstatic.com/s/of/"
                   "x.woff2)format(\"woff2\");font-weight:400")},
        {"file": "site.css", "media": "", "kind": "rule", "selector": "@font-face",
         "decls": ("font-family:site-icons;src:url(data:application/x-font-ttf;"
                   "charset=utf-8;base64,AAEAAAALAIAAAwAwT1MvMg8SBiUAAAC8AAAAYA==)"
                   "format(\"truetype\")")},
        {"file": "site.css", "media": "", "kind": "rule", "selector": "body",
         "decls": "font-family:Fixture Sans, Arial, sans-serif"},
    ],
}

BRAND_YAML = """
brand:
  name: Fixture Brand
tokens:
  type:
    display-hero:
      family: "'Fixture Serif', Georgia, serif"
      sizeRem: {base: 4}
    body:
      family: "'Fixture Sans', Arial, sans-serif"
      sizeRem: {base: 1}
"""


def _evidence_dir(tmp: Path, rules=None) -> Path:
    page = tmp / "evidence" / "pages" / "home"
    page.mkdir(parents=True)
    (page / "css-rules.json").write_text(json.dumps(rules or FIXTURE_RULES))
    return tmp / "evidence"


class HarvesterParsesCapturedRules(unittest.TestCase):

    def setUp(self):
        self.faces = hff.harvest_faces([("home", FIXTURE_RULES)])
        self.families = {f["family"]: f for f in hff.group_families(self.faces)}

    def test_only_font_face_rules_are_harvested(self):
        self.assertEqual(len(self.faces), 4)   # the body rule is not a @font-face

    def test_family_weights_and_styles_are_recorded(self):
        fam = self.families["Fixture Sans"]
        self.assertEqual(fam["weights"], ["400", "500"])
        self.assertEqual(sorted(fam["styles"]), ["italic", "normal"])
        self.assertEqual(fam["faceCount"], 2)

    def test_source_urls_are_recorded_never_fetched(self):
        fam = self.families["Fixture Sans"]
        self.assertEqual(fam["sourceKinds"], ["remote"])
        self.assertEqual(fam["hosts"], ["cdn.example.test"])
        self.assertTrue(all(u.startswith("https://") for u in fam["urls"]))

    def test_quoted_family_names_are_unwrapped(self):
        self.assertIn("Open Face", self.families)

    def test_license_hint_only_from_supportable_evidence(self):
        # an openly licensed webfont host IS evidence; any other host is UNKNOWN
        self.assertEqual(self.families["Open Face"]["licenseHint"], "google-fonts")
        self.assertIsNone(self.families["Fixture Sans"]["licenseHint"])

    def test_inline_bytes_are_flagged_and_not_dumped(self):
        icons = self.families["site-icons"]
        self.assertTrue(icons["bytesInline"])
        self.assertEqual(icons["urls"], [])          # a data: payload is not a source
        self.assertLess(len(self.faces[-1]["sources"][0]["url"]), 80)


class AvailabilityFactShape(unittest.TestCase):

    def _availability(self, brand_yaml=BRAND_YAML, fonts=()):
        tmp = Path(self._tmp.name)
        (tmp / "brand.yaml").write_text(brand_yaml)
        if fonts:
            (tmp / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
            for name in fonts:
                (tmp / "assets" / "fonts" / name).write_bytes(b"x")
        faces = hff.harvest_faces([("home", FIXTURE_RULES)])
        return hff.build_availability(faces, hff._load_brand(tmp), tmp)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_every_declared_family_gets_exactly_one_status(self):
        rows = self._availability()["declared"]
        self.assertTrue(rows)
        for row in rows:
            self.assertIn(row["status"], {tc.DELIVERY_SELF_HOSTED, tc.DELIVERY_PROXY,
                                          tc.DELIVERY_UNAVAILABLE})

    def test_captured_face_is_cross_referenced_with_the_declaration(self):
        rows = {r["family"]: r for r in self._availability()["declared"]}
        self.assertTrue(rows["Fixture Sans"]["capturedFontFace"])
        self.assertEqual(rows["Fixture Sans"]["capturedWeights"], ["400", "500"])
        # declared but never seen in any stylesheet — still recorded, not dropped
        self.assertFalse(rows["Fixture Serif"]["capturedFontFace"])

    def test_discoverable_but_not_vendored_is_the_reviewable_list(self):
        """The families whose real files the capture located but the project does not
        ship. That is exactly the set where a licensing decision is owed."""
        summary = self._availability()["summary"]
        self.assertEqual(summary["discoverableButNotVendored"], ["Fixture Sans"])
        self.assertEqual(summary["selfHosted"], [])

    def test_self_hosted_family_flips_the_status(self):
        availability = self._availability(
            BRAND_YAML + """
selfHostedFonts:
  - family: Fixture Sans
    faces:
      - weight: 400
        files: [FixtureSans-Regular.woff2]
""", fonts=["FixtureSans-Regular.woff2"])
        rows = {r["family"]: r for r in availability["declared"]}
        self.assertEqual(rows["Fixture Sans"]["status"], tc.DELIVERY_SELF_HOSTED)
        self.assertEqual(availability["summary"]["selfHosted"], ["Fixture Sans"])
        self.assertNotIn("Fixture Sans",
                         availability["summary"]["discoverableButNotVendored"])

    def test_availability_without_a_brand_is_pure_observation(self):
        faces = hff.harvest_faces([("home", FIXTURE_RULES)])
        out = hff.build_availability(faces, None, None)
        self.assertNotIn("declared", out)
        self.assertEqual(out["schemaVersion"], "font-availability.v1")

    def test_brand_snippet_is_one_entry_per_family(self):
        snippet = hff.brand_snippet(self._availability())
        self.assertEqual(snippet.count("- family:"), 2)
        self.assertIn("discovered (not fetched)", snippet)
        self.assertIn("fontAvailability:", snippet)


class HarvesterEndToEnd(unittest.TestCase):

    def test_cli_writes_both_documents(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            evidence = _evidence_dir(tmp)
            (tmp / "brand.yaml").write_text(BRAND_YAML)
            rc = hff.main(["--evidence", str(evidence), "--brand-dir", str(tmp),
                           "--emit-brand-snippet"])
            self.assertEqual(rc, 0)
            availability = json.loads((evidence / "font-availability.json").read_text())
            self.assertEqual(availability["schemaVersion"], "font-availability.v1")
            self.assertTrue((evidence / "font-faces.json").is_file())
            self.assertTrue(
                (evidence / "font-availability.brand-snippet.yaml").is_file())

    def test_real_capture_evidence_yields_font_faces(self):
        """Runs against a REAL lane's evidence when it is present locally (runs/ is
        gitignored). A hand-written fixture cannot prove the parser survives minified
        production CSS, which is where the original miss happened."""
        rules = sorted((_REPO / "runs").glob("*/brand/evidence/**/css-rules.json"))
        if not rules:
            self.skipTest("no local run evidence checked out")
        docs = [(p.parent.name, json.loads(p.read_text())) for p in rules[:6]]
        faces = hff.harvest_faces(docs)
        self.assertTrue(faces, "no @font-face harvested from real capture evidence")
        self.assertTrue(any(s["kind"] == "remote"
                            for f in faces for s in f["sources"]))


if __name__ == "__main__":
    unittest.main()
