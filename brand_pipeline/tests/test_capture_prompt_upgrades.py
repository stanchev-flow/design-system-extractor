#!/usr/bin/env python3
"""Tests for the CAPTURE-PROMPT UPGRADES (Archaeologist) capture/spec/schema side.

Covers the fact-gated, backward-compatible additions landed on the capture arm:

  - The OPTIONAL structured `carousel:` recipe (brand-schema §10.3g):
    `_check_carousel_recipe` well-formedness (advisory warnings only), and its
    integration into the C13 interactive-block timing gate (a numeric
    intervalMs/transitionMs satisfies the timing fact; malformed present recipes
    warn but never hard-fail a brand that lacks the field).
  - Spec/prompt-doc presence of the show-before-build contract, exhaustive
    per-component states mandate, mobile-drawer + sticky nav slots, shadow/z-index
    scales, and the footer locale selector — the capture-side deliverables.

All new schema fields are OPTIONAL: a brand lacking them validates byte-identically.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_capture_prompt_upgrades
"""
from __future__ import annotations

import copy
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

from brand_pipeline.tests.test_brand_evidence_contract import (  # noqa: E402
    ART_FILES,
    FIXTURE_BRAND,
    FIXTURE_CONTRACTS,
    FIXTURE_COPY,
    FIXTURE_LIBRARY,
    LOGO_FILES,
)

_SPEC = _REPO / "brand_pipeline" / "spec"


# ── unit: _check_carousel_recipe (pure, no fixture) ──────────────────────────
class CarouselRecipeUnitTests(unittest.TestCase):
    def _run(self, recipe: dict):
        rep = vbe.Report(brand_dir=Path("."))
        satisfies = vbe._check_carousel_recipe(rep, "carousel", recipe)
        return rep, satisfies

    def test_wellformed_recipe_satisfies_timing_no_warnings(self):
        rep, satisfies = self._run({
            "autoplay": True, "intervalMs": 5000, "transitionMs": 400,
            "easing": "cubic-bezier(0.2, 0, 0, 1)", "controls": ["arrows", "dots"],
            "dots": True, "pauseOnHover": True, "loop": True, "slidesPerView": 1,
        })
        self.assertTrue(satisfies)
        self.assertEqual(rep.warnings, [], rep.warnings)

    def test_transition_only_recipe_satisfies_timing(self):
        _, satisfies = self._run({"transitionMs": 350, "controls": ["none"]})
        self.assertTrue(satisfies)

    def test_recipe_without_numeric_timing_does_not_satisfy(self):
        _, satisfies = self._run({"autoplay": False, "controls": ["arrows"]})
        self.assertFalse(satisfies)

    def test_bad_controls_vocab_warns(self):
        rep, _ = self._run({"controls": ["swipe"], "transitionMs": 300})
        self.assertTrue(any("controls" in w for w in rep.warnings), rep.warnings)

    def test_non_numeric_interval_warns(self):
        rep, _ = self._run({"intervalMs": "5s"})
        self.assertTrue(any("intervalMs" in w for w in rep.warnings), rep.warnings)

    def test_boolean_ms_field_warns(self):
        rep, _ = self._run({"intervalMs": True})
        self.assertTrue(any("intervalMs" in w for w in rep.warnings), rep.warnings)

    def test_non_boolean_flag_warns(self):
        rep, _ = self._run({"autoplay": "yes", "transitionMs": 300})
        self.assertTrue(any("autoplay" in w for w in rep.warnings), rep.warnings)


# ── integration: C13 interactive-block timing gate ───────────────────────────
class CarouselC13IntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="capture-upgrade-fixture-")
        self.root = Path(self._tmp)
        self.brand_dir = self.root / "brand"
        self.contracts = self.root / "blocks.yaml"
        self._build_complete_fixture()

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _build_complete_fixture(self):
        self.brand_dir.mkdir(parents=True)
        self.contracts.write_text(yaml.safe_dump(FIXTURE_CONTRACTS))
        (self.brand_dir / "brand.yaml").write_text(yaml.safe_dump(FIXTURE_BRAND))
        (self.brand_dir / "layout-library.yaml").write_text(
            yaml.safe_dump(FIXTURE_LIBRARY))
        (self.brand_dir / "section-copy.yaml").write_text(
            yaml.safe_dump(FIXTURE_COPY))
        assets = self.brand_dir / "assets"
        assets.mkdir()
        for name in LOGO_FILES:
            (assets / name).write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        for name in ART_FILES:
            (assets / name).write_bytes(b"RIFF\x00\x00\x00\x00WEBP")
        (self.brand_dir / "assets-tagged.json").write_text(json.dumps({
            "schemaVersion": 2,
            "assets": [{"filename": n, "useCase": "logo-wall-logo"}
                       for n in LOGO_FILES]}))
        grounding = self.brand_dir / "evidence" / "grounding"
        grounding.mkdir(parents=True)
        (grounding / "section-00-hero.yaml").write_text(yaml.safe_dump({
            "schemaVersion": "section-grounding.v1", "sectionRole": "hero",
            "copy": {"heading": "A real heading"}}))

    def _mutate(self, fn):
        doc = yaml.safe_load((self.brand_dir / "brand.yaml").read_text())
        fn(doc)
        (self.brand_dir / "brand.yaml").write_text(yaml.safe_dump(doc))

    def _validate(self):
        return vbe.validate_brand_dir(self.brand_dir, contracts_path=self.contracts,
                                      smoke=False)

    def test_baseline_fixture_passes(self):
        # sanity: the borrowed fixture is a clean pass before any carousel is added
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)

    def test_carousel_recipe_numeric_timing_satisfies_c13(self):
        def add(d):
            d.setdefault("blocks", {})["carousel"] = {
                "origin": "extracted",
                "carousel": {"autoplay": True, "intervalMs": 6000,
                             "transitionMs": 400, "controls": ["dots"]},
            }
        self._mutate(add)
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C13")], [], rep.errors)

    def test_carousel_block_without_any_timing_fails_c13(self):
        def add(d):
            d.setdefault("blocks", {})["carousel"] = {"origin": "extracted"}
        self._mutate(add)
        rep = self._validate()
        self.assertTrue(any(e.startswith("C13") and "carousel" in e
                            for e in rep.errors), rep.errors)

    def test_carousel_notObserved_recipe_needs_reason(self):
        def add(d):
            d.setdefault("blocks", {})["carousel"] = {
                "origin": "extracted",
                "motion": {"notObserved": True, "reason": "static-only capture"},
                "carousel": {"notObserved": True},
            }
        self._mutate(add)
        rep = self._validate()
        self.assertTrue(any("carousel.notObserved" in w for w in rep.warnings),
                        rep.warnings)

    def test_malformed_recipe_warns_but_does_not_error(self):
        def add(d):
            d.setdefault("blocks", {})["carousel"] = {
                "origin": "extracted",
                "carousel": {"transitionMs": 300, "controls": ["swipe"]},
            }
        self._mutate(add)
        rep = self._validate()
        self.assertTrue(any("controls" in w for w in rep.warnings), rep.warnings)
        self.assertEqual([e for e in rep.errors if e.startswith("C13")], [], rep.errors)

    def test_no_carousel_block_is_byte_identical(self):
        # a brand with no carousel block never triggers the new checks
        rep = self._validate()
        self.assertEqual([w for w in rep.warnings if "carousel" in w], [], rep.warnings)


# ── docs: the capture-side spec deliverables are present ──────────────────────
class CaptureSpecDocPresenceTests(unittest.TestCase):
    def _read(self, name: str) -> str:
        return (_SPEC / name).read_text()

    def test_show_before_build_contract_in_skill_and_prompt(self):
        skill = self._read("layout-analyst-skill.md")
        prompt = self._read("extraction-grounding-prompt.md")
        self.assertIn("SHOW-BEFORE-BUILD", skill)
        self.assertIn("evidence → author → validate → render", skill)
        self.assertIn("Show-before-build", prompt)

    def test_exhaustive_states_mandate_present(self):
        skill = self._read("layout-analyst-skill.md")
        schema = self._read("brand-schema.md")
        self.assertIn("Exhaustive per-component STATES", skill)
        self.assertIn("statesObserved", schema)
        self.assertIn("Exhaustive per-component interaction STATES", schema)

    def test_carousel_recipe_schema_and_instruction(self):
        schema = self._read("brand-schema.md")
        skill = self._read("layout-analyst-skill.md")
        self.assertIn("10.3g", schema)
        self.assertIn("slidesPerView", schema)
        self.assertIn("Structured carousel/slider recipe", skill)

    def test_mobile_drawer_and_sticky_slots_present(self):
        schema = self._read("brand-schema.md")
        self.assertIn("navbar.mobile", schema)
        self.assertIn("navbar.sticky", schema)
        self.assertIn("scroll-shrink", schema)

    def test_shadow_zindex_and_locale_selector_present(self):
        schema = self._read("brand-schema.md")
        self.assertIn("footer.localeSelector", schema)
        self.assertIn("zIndex:", schema)
        self.assertIn("shadow:", schema)


if __name__ == "__main__":
    unittest.main()
