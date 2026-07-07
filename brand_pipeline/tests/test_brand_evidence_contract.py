#!/usr/bin/env python3
"""Unit tests for tools/extract/validate_brand_evidence.py — the fail-loud
extraction output contract (Phase A of the extraction redo).

Each test builds a minimal SYNTHETIC fixture brand in a temp dir (values
deliberately generic — no real brand's data) and asserts that the exact gaps
that broke the Remote run fail loud with actionable messages: missing
section-copy.yaml, single button variant, unattempted `card` block, logo wall
without logo assets, `legal.copyright` instead of `legal.text`, missing vision
grounding.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_brand_evidence_contract
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

_REPO = Path(__file__).resolve().parents[2]
_TOOLS_EXTRACT = _REPO / "tools" / "extract"
if str(_TOOLS_EXTRACT) not in sys.path:
    sys.path.insert(0, str(_TOOLS_EXTRACT))

import validate_brand_evidence as vbe  # noqa: E402


FIXTURE_CONTRACTS = {
    "blocks": {
        "header": {"slots": ["wordmark", "links"]},
        "card": {"slots": ["media", "heading", "body"]},
        "button": {"slots": ["label"]},
        "form": {"slots": ["field", "submit"]},
    }
}

FIXTURE_BRAND = {
    "brand": {"name": "Fixture"},
    "blocks": {
        "header": {"origin": "extracted"},
        "card": {"origin": "extracted", "slots": ["media", "heading"]},
        "button": {"origin": "extracted"},
        "form": {"notObserved": True},
    },
    "buttons": {
        "primary": {"bg": "#101828", "fg": "#ffffff", "radius": "12px",
                    "bgHover": "#243040"},
        "outlined": {"fg": "#101828", "border": "1px solid #101828",
                     "radius": "12px", "decoration": "underline"},
    },
    "navbar": {
        "primary": ["Products", "Pricing"],
        "surface": {"bg": "#ffffff"},
        "presentation": {"case": "sentence", "separators": "none"},
    },
    "footer": {
        "columns": [{"heading": "Products",
                     "links": [{"label": "Alpha", "href": "/alpha"}]}],
        "social": [{"network": "linkedin", "href": "https://example.com/li"}],
        "legal": {"text": "© 2026 Fixture"},
    },
    "layouts": [
        {"id": "hero-split", "archetype": "split", "useCase": "hero",
         "patternRef": {"id": "fx-hero"},
         "slots": [{"name": "copy", "type": "content"},
                   {"name": "art", "type": "image"}]},
        {"id": "logo-strip", "archetype": "strip",
         "useCase": "customer-proof-strip",
         "patternRef": {"id": "fx-logos"},
         "slots": [{"name": "logo-wall", "type": "image"}]},
        {"id": "navbar", "archetype": "nav"},
        {"id": "footer", "archetype": "grid"},
    ],
}

FIXTURE_LIBRARY = {
    "patterns": [
        {"id": "fx-hero", "useCase": "hero"},
        {"id": "fx-logos", "useCase": "logos"},
    ]
}

FIXTURE_COPY = {
    "sectionCopy": {"wordmark": "Fixture", "eyebrow": "SYNTHETIC"},
    "layoutCopy": {"hero-split": {"heading": "A real heading",
                                  "body": "Real fixture body copy."}},
}

LOGO_FILES = ("logo-alpha.svg", "logo-beta.svg", "logo-gamma.svg")


class BrandEvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="brand-evidence-fixture-")
        self.root = Path(self._tmp)
        self.brand_dir = self.root / "brand"
        self.contracts = self.root / "blocks.yaml"
        self._build_complete_fixture()

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ── fixture plumbing ─────────────────────────────────────────────────────

    def _build_complete_fixture(self):
        self.brand_dir.mkdir(parents=True)
        self.contracts.write_text(yaml.safe_dump(FIXTURE_CONTRACTS))
        self._write_brand(FIXTURE_BRAND)
        (self.brand_dir / "layout-library.yaml").write_text(
            yaml.safe_dump(FIXTURE_LIBRARY))
        (self.brand_dir / "section-copy.yaml").write_text(
            yaml.safe_dump(FIXTURE_COPY))
        assets = self.brand_dir / "assets"
        assets.mkdir()
        for name in LOGO_FILES:
            (assets / name).write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        (self.brand_dir / "assets-tagged.json").write_text(json.dumps({
            "schemaVersion": 2,
            "assets": [{"filename": n, "useCase": "logo-wall-logo"}
                       for n in LOGO_FILES]}))
        grounding = self.brand_dir / "evidence" / "grounding"
        grounding.mkdir(parents=True)
        (grounding / "section-00-hero.yaml").write_text(yaml.safe_dump({
            "schemaVersion": "section-grounding.v1", "sectionRole": "hero",
            "copy": {"heading": "A real heading"}}))

    def _write_brand(self, doc: dict):
        (self.brand_dir / "brand.yaml").write_text(yaml.safe_dump(doc))

    def _mutate_brand(self, fn):
        doc = yaml.safe_load((self.brand_dir / "brand.yaml").read_text())
        fn(doc)
        self._write_brand(doc)

    def _validate(self, **kw):
        kw.setdefault("contracts_path", self.contracts)
        return vbe.validate_brand_dir(self.brand_dir, **kw)

    @staticmethod
    def _joined(messages):
        return "\n".join(messages)

    # ── the complete fixture passes ──────────────────────────────────────────

    def test_complete_fixture_passes(self):
        rep = self._validate()
        self.assertEqual(rep.errors, [], f"expected clean pass, got: {rep.errors}")
        self.assertTrue(rep.ok)

    # ── missing copy fails loud ──────────────────────────────────────────────

    def test_missing_section_copy_fails(self):
        (self.brand_dir / "section-copy.yaml").unlink()
        rep = self._validate()
        self.assertFalse(rep.ok)
        msg = self._joined(rep.errors)
        self.assertIn("section-copy.yaml", msg)
        self.assertTrue(any(e.startswith("C4") for e in rep.errors))

    def test_layout_without_copy_entry_fails(self):
        copy = dict(FIXTURE_COPY)
        copy["layoutCopy"] = {}
        (self.brand_dir / "section-copy.yaml").write_text(yaml.safe_dump(copy))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("hero-split", self._joined(rep.errors))

    def test_missing_wordmark_fails(self):
        copy = {"sectionCopy": {"eyebrow": "X"},
                "layoutCopy": FIXTURE_COPY["layoutCopy"]}
        (self.brand_dir / "section-copy.yaml").write_text(yaml.safe_dump(copy))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("wordmark", self._joined(rep.errors))

    # ── button variant matrix ────────────────────────────────────────────────

    def test_single_button_variant_unconfirmed_fails(self):
        self._mutate_brand(lambda d: d.__setitem__(
            "buttons", {"primary": dict(FIXTURE_BRAND["buttons"]["primary"])}))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("ONE family", self._joined(rep.errors))

    def test_single_button_variant_confirmed_passes(self):
        self._mutate_brand(lambda d: d.__setitem__(
            "buttons", {"primary": dict(FIXTURE_BRAND["buttons"]["primary"]),
                        "singleVariantConfirmed": True}))
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)

    def test_button_family_without_state_fact_fails(self):
        def strip_hover(d):
            d["buttons"]["primary"].pop("bgHover")
        self._mutate_brand(strip_hover)
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("buttons.primary", self._joined(rep.errors))

    # ── block coverage (incl. card) ──────────────────────────────────────────

    def test_missing_card_attempt_fails(self):
        self._mutate_brand(lambda d: d["blocks"].pop("card"))
        rep = self._validate()
        self.assertFalse(rep.ok)
        msg = self._joined(rep.errors)
        self.assertIn("card", msg)
        self.assertTrue(any(e.startswith("C2") for e in rep.errors))

    def test_not_observed_marker_counts_as_attempted(self):
        self._mutate_brand(lambda d: d["blocks"].__setitem__(
            "card", {"notObserved": True}))
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)

    # ── logo evidence ────────────────────────────────────────────────────────

    def test_logo_wall_without_logo_assets_fails(self):
        for name in LOGO_FILES:
            (self.brand_dir / "assets" / name).unlink()
        (self.brand_dir / "assets-tagged.json").write_text(json.dumps({
            "schemaVersion": 2, "assets": []}))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertTrue(any(e.startswith("C6") for e in rep.errors),
                        rep.errors)

    # ── chrome contract ──────────────────────────────────────────────────────

    def test_legal_copyright_key_fails_with_actionable_message(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "legal", {"copyright": "© 2026 Fixture"}))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("legal.text", self._joined(rep.errors))

    def test_navbar_without_presentation_evidence_fails(self):
        def strip(d):
            d["navbar"].pop("presentation")
        self._mutate_brand(strip)
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("presentation", self._joined(rep.errors))

    def test_navbar_measured_link_counts_as_presentation_evidence(self):
        def swap(d):
            d["navbar"].pop("presentation")
            d["navbar"]["measured"] = {"link": {"fontSize": "14px",
                                                "textTransform": "none"}}
        self._mutate_brand(swap)
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)

    # ── asset manifest matches disk ──────────────────────────────────────────

    def test_tagged_asset_missing_on_disk_fails(self):
        (self.brand_dir / "assets-tagged.json").write_text(json.dumps({
            "schemaVersion": 2,
            "assets": [{"filename": "logo-alpha.svg", "useCase": "logo-wall-logo"},
                       {"filename": "ghost-file.webp", "useCase": "hero"}]}))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("ghost-file.webp", self._joined(rep.errors))

    # ── vision grounding evidence ────────────────────────────────────────────

    def test_missing_grounding_fails(self):
        shutil.rmtree(self.brand_dir / "evidence")
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertTrue(any(e.startswith("C9") for e in rep.errors), rep.errors)

    def test_allow_no_vision_downgrades_to_warning(self):
        shutil.rmtree(self.brand_dir / "evidence")
        rep = self._validate(allow_no_vision=True)
        self.assertEqual(rep.errors, [], rep.errors)
        self.assertTrue(any(w.startswith("C9") for w in rep.warnings))

    # ── pattern coverage ─────────────────────────────────────────────────────

    def test_orphan_pattern_warns_but_passes(self):
        lib = {"patterns": FIXTURE_LIBRARY["patterns"]
               + [{"id": "fx-orphan", "useCase": "cta"}]}
        (self.brand_dir / "layout-library.yaml").write_text(yaml.safe_dump(lib))
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)
        self.assertIn("fx-orphan", self._joined(rep.warnings))

    def test_dangling_pattern_ref_fails(self):
        def dangle(d):
            d["layouts"][0]["patternRef"] = {"id": "does-not-exist"}
        self._mutate_brand(dangle)
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("does-not-exist", self._joined(rep.errors))

    def test_missing_brand_yaml_fails_immediately(self):
        (self.brand_dir / "brand.yaml").unlink()
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertTrue(any(e.startswith("C1") for e in rep.errors))


if __name__ == "__main__":
    unittest.main()
