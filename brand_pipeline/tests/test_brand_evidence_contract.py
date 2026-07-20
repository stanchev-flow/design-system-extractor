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

# tokens + motion voice: the MINIMAL complete set the layer-1 generator requires —
# the C11 composed-demo smoke runs the real composers, which fail loud without it.
FIXTURE_TOKENS = {
    "colors": {
        "text/default": {"value": "#101828"},
        "text/muted": {"value": "#475467"},
        "text/on-primary": {"value": "#101828"},
        "text/on-primary-muted": {"value": "#475467"},
        "text/on-inverse": {"value": "#ffffff"},
        "text/on-inverse-muted": {"value": "#d0d5dd"},
        "text/ghost-on-primary": {"value": "#e4e7ec"},
        "border/hairline-on-primary": {"value": "#e4e7ec"},
        "surface/primary": {"value": "#ffffff"},
        "surface/panel": {"value": "#f2f4f7"},
        "surface/inverse": {"value": "#101828"},
        "action/primary": {"value": "#101828"},
        "action/primary-fg": {"value": "#ffffff"},
    },
    "surfaces": {
        "surface/primary": {"bg": "#ffffff", "textPrimary": "text/on-primary"},
        "surface/panel": {"bg": "#f2f4f7", "textPrimary": "text/on-primary"},
        "surface/inverse": {"bg": "#101828", "textPrimary": "text/on-inverse"},
        "surface/inverse-strong": {"bg": "#0c111d", "textPrimary": "text/on-inverse"},
    },
    # C14: sized roles carry a MEASURED multi-breakpoint ladder, or confirm the
    # single tier explicitly (measured constant across the tier ladder)
    "type": {
        "display-hero": {"family": "Georgia", "weight": 700,
                         "sizeRem": {"base": 3.0, "tablet": 2.5, "mobile": 2.0}},
        "h1": {"family": "Georgia", "weight": 700,
               "sizeRem": {"base": 2.5, "tablet": 2.0, "mobile": 1.75}},
        "h2": {"family": "Georgia", "weight": 700,
               "sizeRem": {"base": 2.0, "tablet": 1.75}},
        "h3": {"family": "Georgia", "weight": 600,
               "sizeRem": {"base": 1.5, "tablet": 1.25}},
        "body": {"family": "Helvetica", "weight": 400,
                 "sizeRem": {"base": 1.0}, "singleTierConfirmed": True},
        "small": {"family": "Helvetica", "weight": 400,
                  "sizeRem": {"base": 0.875}, "singleTierConfirmed": True},
        "eyebrow": {"family": "Helvetica", "weight": 600,
                    "sizeRem": {"base": 0.8125}, "singleTierConfirmed": True},
        "control-text": {"family": "Helvetica", "weight": 500,
                         "sizeRem": {"base": 0.9375}, "singleTierConfirmed": True},
    },
    # C15: the relational rungs (X-to-Y) are the formalized rhythm ladder
    "spacing": {
        "section-padding-light": {"value": "5rem"},
        "eyebrow-to-heading": {"value": "1rem"},
        "heading-to-body": {"value": "1.25rem"},
        "body-to-cta": {"value": "2rem"},
        "panel-padding": {"value": "2rem"},
        "radius-global": {"value": "12px"},
        "radius-card": {"value": "12px"},
    },
    # C13: motion is part of the token contract — an evidenced duration ladder +
    # easing set (synthetic values, envelope-shaped like the authored files)
    "motion": {
        "durations": {"state": {"value": "150ms"}, "reveal": {"value": "300ms"}},
        "easings": [{"value": "cubic-bezier(0.2, 0, 0, 1)", "use": "enter"}],
        "signatureMoves": [{"name": "icon-slide", "duration": "300ms",
                            "sourceSelectors": [".btn .icon"]}],
    },
}

FIXTURE_VOICE = {
    "motionSpec": {"durations": {"fast": "120ms", "base": "200ms", "slow": "320ms"},
                   "easing": {"primary": "cubic-bezier(0.2, 0, 0, 1)"}},
}

FIXTURE_BRAND = {
    "brand": {"name": "Fixture"},
    # C14: the brand declares which measured breakpoint its canonical values cite
    "meta": {"canonicalTier": {"viewport": 1440,
                               "note": "sizeRem.base == computed @1440"}},
    "tokens": FIXTURE_TOKENS,
    "voice": FIXTURE_VOICE,
    "blocks": {
        "header": {"origin": "extracted"},
        "card": {"origin": "extracted", "slots": ["media", "heading"],
                 # C10: variant coverage is part of complete card evidence
                 "variants": [{"id": "media-top"}, {"id": "text-only"}]},
        "button": {"origin": "extracted"},
        "form": {"notObserved": True},
    },
    "buttons": {
        # C3-strict: filled family carries the full state + geometry matrix
        "primary": {"style": "filled", "bg": "#101828", "fg": "#ffffff",
                    "radius": "12px", "bgHover": "#243040", "fgHover": "#ffffff",
                    "height": "2.75rem", "padding": "0 1.25rem"},
        "outlined": {"style": "outline", "fg": "#101828",
                     "border": "1px solid #101828",
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
                   # dual-action role: the demo splits this into a primary +
                   # secondary button pair (C11 asserts the primary leads)
                   {"name": "actions", "type": "content",
                    "role": "primary filled pill + outlined secondary pill"},
                   {"name": "art", "type": "image"}]},
        {"id": "logo-strip", "archetype": "stack",
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
                                  "body": "Real fixture body copy.",
                                  "cta": "Start now"}},
    # the hero split's media slot binds REAL on-disk art (C11: srcless media slots
    # compose placeholder plates, which the smoke check rejects)
    "defaultArt": {"hero": ["art-hero.webp"]},
}

LOGO_FILES = ("logo-alpha.svg", "logo-beta.svg", "logo-gamma.svg")
ART_FILES = ("art-hero.webp",)


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

    def _write_brand(self, doc: dict):
        (self.brand_dir / "brand.yaml").write_text(yaml.safe_dump(doc))

    def _mutate_brand(self, fn):
        doc = yaml.safe_load((self.brand_dir / "brand.yaml").read_text())
        fn(doc)
        self._write_brand(doc)

    def _validate(self, **kw):
        kw.setdefault("contracts_path", self.contracts)
        # most tests target one specific check — skip the (real-composer) C11
        # smoke unless a test opts in, so the suite stays fast and focused.
        kw.setdefault("smoke", False)
        return vbe.validate_brand_dir(self.brand_dir, **kw)

    @staticmethod
    def _joined(messages):
        return "\n".join(messages)

    # ── the complete fixture passes ──────────────────────────────────────────

    def test_complete_fixture_passes(self):
        # smoke ON: the complete fixture must also compose cleanly through the
        # real archetype composers (C11) and carry clean generated-html hygiene.
        rep = self._validate(smoke=True)
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
            d["buttons"]["primary"].pop("fgHover")
        self._mutate_brand(strip_hover)
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("buttons.primary", self._joined(rep.errors))

    # ── C3-strict: hover pairing + filled-family geometry ────────────────────

    def test_bghover_without_fghover_fails(self):
        self._mutate_brand(lambda d: d["buttons"]["primary"].pop("fgHover"))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("fgHover", self._joined(rep.errors))

    def test_filled_family_without_geometry_fails(self):
        def strip_geom(d):
            d["buttons"]["primary"].pop("height")
            d["buttons"]["primary"].pop("padding")
        self._mutate_brand(strip_geom)
        rep = self._validate()
        self.assertFalse(rep.ok)
        msg = self._joined(rep.errors)
        self.assertIn("height", msg)
        self.assertIn("padding", msg)

    def test_outline_family_needs_no_geometry(self):
        # the outlined fixture family has no bg fill — geometry is not demanded
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if "outlined" in e], [])

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

    # ── C7 range + integrity (sysfix 2026-07) ────────────────────────────────

    def test_content_max_width_out_of_range_fails(self):
        self._mutate_brand(lambda d: d["navbar"].__setitem__(
            "measured", {"link": {"fontSize": "14px"}, "contentMaxWidth": 4000}))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("contentMaxWidth", self._joined(rep.errors))

    def test_content_max_width_in_range_passes(self):
        self._mutate_brand(lambda d: d["navbar"].__setitem__(
            "measured", {"link": {"fontSize": "14px"}, "contentMaxWidth": 1216}))
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)

    def test_footer_zero_content_max_width_is_tolerated(self):
        # 0 = "could not measure" (e.g. %-based container) — allowed, not an error
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "measured", {"contentMaxWidth": 0}))
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)

    def test_grid_footer_without_headings_fails(self):
        def strip_heads(d):
            d["footer"]["rules"] = {"layout": "grid"}
            for col in d["footer"]["columns"]:
                col.pop("heading", None)
        self._mutate_brand(strip_heads)
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("heading", self._joined(rep.errors))

    def test_unrenderable_nav_logo_fails(self):
        self._mutate_brand(lambda d: d["navbar"].__setitem__(
            "logo", {"kind": "img", "alt": "Fixture"}))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("logo", self._joined(rep.errors))

    def test_svg_nav_logo_passes(self):
        self._mutate_brand(lambda d: d["navbar"].__setitem__(
            "logo", {"kind": "svg", "alt": "Fixture",
                     "srcContract": "../assets/source-chrome.v2.json#nav.logo.src"}))
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)

    def test_app_badge_footer_logo_fails(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "logo", {"kind": "img", "src": "app-store-badge.svg", "alt": "store"}))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("badge", self._joined(rep.errors).lower())

    def test_mega_menu_heading_prefix_of_first_link_fails(self):
        self._mutate_brand(lambda d: d["navbar"].__setitem__(
            "primary",
            [{"label": "Products",
              "menu": {"columns": [
                  {"heading": "Global Employment",
                   "links": [{"label": "Global Employment Payroll Run compliant "
                                       "payroll everywhere"}]}]}}]))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertIn("prefix", self._joined(rep.errors))

    def test_mega_menu_clean_heading_passes(self):
        def mut(d):
            d["navbar"]["primary"] = [
                {"label": "Products",
                 "menu": {"columns": [
                     {"heading": "Global Employment",
                      "links": [{"label": "Payroll Run"}]}]}}]
            # a captured menu owes measured open-panel facts (C16) — this test
            # targets the C7 heading-prefix rule, so carry the minimal set.
            d["navbar"]["measured"] = {"megaPanel": {
                "motion": {"panel": {"duration": "0.3s"}}}}
        self._mutate_brand(mut)
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

    # ── C23 component-recipe coverage (fix2, brand-schema §4.4e) ─────────────

    @staticmethod
    def _railish(pid):
        return {"id": pid, "useCase": "features",
                "specialTreatments": [{"kind": "dotted-rule-rail"}]}

    def _write_library(self, lib: dict):
        (self.brand_dir / "layout-library.yaml").write_text(yaml.safe_dump(lib))

    def _c23(self, rep):
        return [w for w in rep.warnings if w.startswith("C23")]

    def test_shared_rail_anatomy_without_recipe_advises(self):
        self._write_library({"patterns": FIXTURE_LIBRARY["patterns"]
                             + [self._railish("fx-rail-a"),
                                self._railish("fx-rail-b")]})
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)   # advisory, never an error
        msgs = self._joined(self._c23(rep))
        self.assertIn("fx-rail-a", msgs)
        self.assertIn("fx-rail-b", msgs)

    def test_recipe_bound_both_ways_is_quiet(self):
        rail_a = {**self._railish("fx-rail-a"),
                  "recipeRef": {"recipe": "section-headrail", "variant": "chip"}}
        rail_b = {**self._railish("fx-rail-b"),
                  "recipeRef": {"recipe": "section-headrail", "variant": "pill"}}
        self._write_library({
            "recipes": [{"id": "section-headrail", "name": "section headrail",
                         "intent": "opener",
                         "anatomy": [{"slot": "kicker", "role": "mark"}],
                         "variants": [{"id": "chip", "useCase": "feature"},
                                      {"id": "pill", "useCase": "editorial"}],
                         "usedBy": ["fx-rail-a", "fx-rail-b"]}],
            "patterns": FIXTURE_LIBRARY["patterns"] + [rail_a, rail_b]})
        rep = self._validate()
        self.assertEqual(self._c23(rep), [])

    def test_dangling_recipe_ref_advises(self):
        rail = {**self._railish("fx-rail-a"),
                "recipeRef": {"recipe": "no-such-recipe"}}
        self._write_library({"patterns": FIXTURE_LIBRARY["patterns"] + [rail]})
        rep = self._validate()
        self.assertIn("no-such-recipe", self._joined(self._c23(rep)))

    def test_one_way_used_by_advises(self):
        # recipe lists the pattern but the pattern carries no recipeRef back
        self._write_library({
            "recipes": [{"id": "section-headrail", "name": "rail", "intent": "x",
                         "anatomy": [{"slot": "kicker", "role": "mark"}],
                         "variants": [{"id": "chip", "useCase": "feature"}],
                         "usedBy": ["fx-hero"]}],
            "patterns": FIXTURE_LIBRARY["patterns"]})
        rep = self._validate()
        self.assertIn("bind both directions", self._joined(self._c23(rep)))

    def test_anatomyless_recipe_advises(self):
        self._write_library({
            "recipes": [{"id": "bare", "name": "bare", "intent": "x",
                         "variants": [{"id": "only", "useCase": "y"}]}],
            "patterns": FIXTURE_LIBRARY["patterns"]})
        rep = self._validate()
        self.assertIn("no anatomy", self._joined(self._c23(rep)))

    # ── C10 card variant coverage ────────────────────────────────────────────

    def test_card_without_variant_coverage_fails(self):
        self._mutate_brand(lambda d: d["blocks"]["card"].pop("variants"))
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertTrue(any(e.startswith("C10") for e in rep.errors), rep.errors)

    def test_card_single_variant_confirmed_passes(self):
        def confirm(d):
            d["blocks"]["card"].pop("variants")
            d["blocks"]["card"]["singleVariantConfirmed"] = True
        self._mutate_brand(confirm)
        rep = self._validate()
        self.assertEqual(rep.errors, [], rep.errors)

    def test_not_observed_card_needs_no_variants(self):
        self._mutate_brand(lambda d: d["blocks"].__setitem__(
            "card", {"notObserved": True}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C10")], [])

    # ── C13 motion evidence ──────────────────────────────────────────────────

    def test_missing_motion_tokens_fails(self):
        self._mutate_brand(lambda d: d["tokens"].pop("motion"))
        rep = self._validate()
        self.assertFalse(rep.ok)
        msg = self._joined(rep.errors)
        self.assertTrue(any(e.startswith("C13") for e in rep.errors), rep.errors)
        self.assertIn("motion-audit.json", msg)

    def test_motion_not_observed_with_reason_passes(self):
        self._mutate_brand(lambda d: d["tokens"].__setitem__(
            "motion", {"notObserved": True,
                       "reason": "motion-audit.json empty — static capture, no "
                                 "authored transitions"}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C13")], [],
                         rep.errors)

    def test_motion_not_observed_without_reason_fails(self):
        self._mutate_brand(lambda d: d["tokens"].__setitem__(
            "motion", {"notObserved": True}))
        rep = self._validate()
        self.assertTrue(any(e.startswith("C13") and "reason" in e
                            for e in rep.errors), rep.errors)

    def test_motion_without_duration_fails(self):
        self._mutate_brand(lambda d: d["tokens"].__setitem__(
            "motion", {"easings": [{"value": "ease-out"}]}))
        rep = self._validate()
        self.assertTrue(any(e.startswith("C13") and "duration" in e
                            for e in rep.errors), rep.errors)

    def test_motion_without_easing_fails(self):
        self._mutate_brand(lambda d: d["tokens"].__setitem__(
            "motion", {"durations": {"state": {"value": "150ms"}}}))
        rep = self._validate()
        self.assertTrue(any(e.startswith("C13") and "easing" in e
                            for e in rep.errors), rep.errors)

    def test_interactive_block_without_timing_fails(self):
        self._mutate_brand(lambda d: d["blocks"].__setitem__(
            "accordion", {"origin": "extracted", "use": "faq rows"}))
        rep = self._validate()
        self.assertTrue(any(e.startswith("C13") and "accordion" in e
                            for e in rep.errors), rep.errors)

    def test_interactive_block_with_timing_passes(self):
        self._mutate_brand(lambda d: d["blocks"].__setitem__(
            "accordion", {"origin": "extracted", "use": "faq rows",
                          "motion": {"duration": "800ms",
                                     "easing": "cubic-bezier(.16,1,.3,1)"}}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C13")], [],
                         rep.errors)

    def test_interactive_block_motion_not_observed_passes(self):
        self._mutate_brand(lambda d: d["blocks"].__setitem__(
            "carousel", {"origin": "extracted", "use": "testimonial slides",
                         "motion": {"notObserved": True,
                                    "reason": "JS-driven; no CSS timing mined"}}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C13")], [],
                         rep.errors)

    # ── C14 canonical-tier discipline ────────────────────────────────────────

    def test_missing_canonical_tier_meta_fails(self):
        self._mutate_brand(lambda d: d.pop("meta"))
        rep = self._validate()
        self.assertTrue(any(e.startswith("C14") and "canonicalTier" in e
                            for e in rep.errors), rep.errors)

    def test_single_breakpoint_role_unconfirmed_fails(self):
        def strip(d):
            d["tokens"]["type"]["body"].pop("singleTierConfirmed")
        self._mutate_brand(strip)
        rep = self._validate()
        self.assertTrue(any(e.startswith("C14") and "body" in e
                            for e in rep.errors), rep.errors)

    def test_single_breakpoint_role_confirmed_passes(self):
        # the complete fixture carries confirmed single-tier roles already
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C14")], [],
                         rep.errors)

    def test_scalar_size_rem_unconfirmed_fails(self):
        self._mutate_brand(lambda d: d["tokens"]["type"].__setitem__(
            "caption", {"family": "Helvetica", "sizeRem": 0.75, "weight": 400}))
        rep = self._validate()
        self.assertTrue(any(e.startswith("C14") and "caption" in e
                            for e in rep.errors), rep.errors)

    def test_families_scale_shape_checked_by_c14(self):
        # the families+scale token shape gets the same discipline
        self._mutate_brand(lambda d: d["tokens"].__setitem__(
            "type", {"families": {"display": {"value": "Georgia"}},
                     "scale": {"display-xl": {"family": "display",
                                              "sizeRem": 4.0}}}))
        rep = self._validate()
        self.assertTrue(any(e.startswith("C14") and "display-xl" in e
                            for e in rep.errors), rep.errors)

    # ── C15 relational spacing ladder ────────────────────────────────────────

    def test_missing_relational_ladder_fails(self):
        def strip(d):
            for k in ("eyebrow-to-heading", "heading-to-body", "body-to-cta"):
                d["tokens"]["spacing"].pop(k)
        self._mutate_brand(strip)
        rep = self._validate()
        self.assertTrue(any(e.startswith("C15") for e in rep.errors), rep.errors)

    def test_single_relational_rung_fails(self):
        def strip(d):
            d["tokens"]["spacing"].pop("heading-to-body")
            d["tokens"]["spacing"].pop("body-to-cta")
        self._mutate_brand(strip)
        rep = self._validate()
        msg = self._joined(rep.errors)
        self.assertTrue(any(e.startswith("C15") for e in rep.errors), rep.errors)
        self.assertIn("eyebrow-to-heading", msg)

    def test_two_relational_rungs_pass(self):
        self._mutate_brand(lambda d: d["tokens"]["spacing"].pop("body-to-cta"))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C15")], [],
                         rep.errors)

    def test_relational_ladder_not_observed_with_reason_passes(self):
        def swap(d):
            for k in ("eyebrow-to-heading", "heading-to-body", "body-to-cta"):
                d["tokens"]["spacing"].pop(k)
            d["tokens"]["spacing"]["relationalLadder"] = {
                "notObserved": True,
                "reason": "single-viewport landing page — no measurable "
                          "role-to-role rhythm beyond section padding"}
        self._mutate_brand(swap)
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C15")], [],
                         rep.errors)

    def test_relational_ladder_not_observed_without_reason_fails(self):
        def swap(d):
            for k in ("eyebrow-to-heading", "heading-to-body", "body-to-cta"):
                d["tokens"]["spacing"].pop(k)
            d["tokens"]["spacing"]["relationalLadder"] = {"notObserved": True}
        self._mutate_brand(swap)
        rep = self._validate()
        self.assertTrue(any(e.startswith("C15") and "reason" in e
                            for e in rep.errors), rep.errors)

    # ── C15 completeness against the mined corpus (fid11) ───────────────────

    def _write_corpus(self, *decls):
        ev = self.brand_dir / "evidence"
        ev.mkdir(exist_ok=True)
        (ev / "css-rules.json").write_text(json.dumps({
            "schemaVersion": 1,
            "rules": [{"selector": ":root", "media": "", "decls": d} for d in decls]}))

    def test_exposed_pair_vars_demand_their_canonical_rungs(self):
        # the corpus exposes all three pair ladders; the fixture authored only two.
        self._write_corpus(
            "--x-label-headline-spacing: 0.5rem",
            "--x-headline-description-spacing: 0.75rem",
            "--x-description-button-spacing: 1.5rem")
        self._mutate_brand(lambda d: d["tokens"]["spacing"].pop("body-to-cta"))
        rep = self._validate()
        msg = self._joined(rep.errors)
        self.assertTrue(any(e.startswith("C15") and "INCOMPLETE" in e
                            for e in rep.errors), rep.errors)
        self.assertIn("body-to-cta", msg)
        self.assertIn("--x-description-button-spacing", msg)

    def test_complete_ladder_passes_the_corpus_check(self):
        self._write_corpus(
            "--x-label-headline-spacing: 0.5rem",
            "--x-headline-description-spacing: 0.75rem",
            "--x-description-button-spacing: 1.5rem")
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C15")], [],
                         rep.errors)

    def test_not_observed_contradicting_exposed_vars_fails(self):
        self._write_corpus("--x-label-headline-spacing: 0.5rem")
        def swap(d):
            for k in ("eyebrow-to-heading", "heading-to-body", "body-to-cta"):
                d["tokens"]["spacing"].pop(k)
            d["tokens"]["spacing"]["relationalLadder"] = {
                "notObserved": True, "reason": "looked everywhere, honest"}
        self._mutate_brand(swap)
        rep = self._validate()
        self.assertTrue(any(e.startswith("C15") and "contradicts" in e
                            for e in rep.errors), rep.errors)

    def test_exposed_row_gap_var_demands_a_row_rung(self):
        self._write_corpus("--x-row-gap-spacing: 3rem")
        rep = self._validate()
        self.assertTrue(any(e.startswith("C15") and "block-to-block" in e
                            for e in rep.errors), rep.errors)
        # authoring the row rung satisfies it
        self._mutate_brand(lambda d: d["tokens"]["spacing"].update(
            {"block-to-block": {"value": "3rem"}}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C15")], [],
                         rep.errors)

    def test_exposed_column_gap_var_demands_a_column_rung(self):
        self._write_corpus("--x-split-column-gap: 3rem")
        rep = self._validate()
        self.assertTrue(any(e.startswith("C15") and "column-to-column" in e
                            for e in rep.errors), rep.errors)
        self._mutate_brand(lambda d: d["tokens"]["spacing"].update(
            {"grid-gap": {"value": "2rem"}}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C15")], [],
                         rep.errors)

    def test_single_role_spacing_vars_demand_nothing(self):
        # a var naming ONE role (or none) is not a relational pair — no rung owed.
        self._write_corpus("--x-content-spacing: 2rem", "--x-title-spacing: 1rem")
        self._mutate_brand(lambda d: d["tokens"]["spacing"].pop("body-to-cta"))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors
                          if e.startswith("C15") and "INCOMPLETE" in e], [],
                         rep.errors)

    # ── C18 contextual header-alignment grammar (fid11) ─────────────────────

    def _write_grammar_library(self):
        lib = {"patterns": [
            {"id": "fx-hero", "useCase": "hero", "archetypeRef": "split",
             "contentShape": {"alignment": {"value": "left",
                                            "counterweight": "media"}}},
            {"id": "fx-infra", "useCase": "about", "archetypeRef": "split",
             "contentShape": {"alignment": {"value": "left",
                                            "counterweight": "media"}}},
            {"id": "fx-logos", "useCase": "logos", "archetypeRef": "stack",
             "contentShape": {"alignment": {"value": "center"}}},
            {"id": "fx-cta", "useCase": "cta", "archetypeRef": "stack",
             "contentShape": {"alignment": {"value": "centered"}}},
        ]}
        (self.brand_dir / "layout-library.yaml").write_text(yaml.safe_dump(lib))

    def test_corroborated_contexts_demand_the_grammar(self):
        self._write_grammar_library()
        rep = self._validate()
        hits = [e for e in rep.errors if e.startswith("C18")]
        self.assertEqual(2, len(hits), rep.errors)
        self.assertIn("splitColumn", self._joined(hits))
        self.assertIn("standaloneStack", self._joined(hits))

    def test_authored_grammar_passes(self):
        self._write_grammar_library()
        self._mutate_brand(lambda d: d.update({"layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left", "counterweight": "media"},
            "standaloneStack": {"anchor": "centered"}}}}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C18")], [],
                         rep.errors)

    def test_grammar_contradicting_the_majority_fails(self):
        self._write_grammar_library()
        self._mutate_brand(lambda d: d.update({"layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left"},
            "standaloneStack": {"anchor": "left"}}}}))
        rep = self._validate()
        self.assertTrue(any(e.startswith("C18") and "contradicts" in e
                            for e in rep.errors), rep.errors)

    def test_dissenting_pattern_fact_warns_for_review(self):
        # fid12: an explicit fact that CONTRADICTS a corroborated grammar outranks
        # it silently (AS-49) — the validator must surface it as an advisory.
        lib = {"patterns": [
            {"id": "fx-hero", "useCase": "hero", "archetypeRef": "split",
             "contentShape": {"alignment": {"value": "left",
                                            "counterweight": "media"}}},
            {"id": "fx-infra", "useCase": "about", "archetypeRef": "split",
             "contentShape": {"alignment": {"value": "left",
                                            "counterweight": "media"}}},
            {"id": "fx-logos", "useCase": "logos", "archetypeRef": "stack",
             "contentShape": {"alignment": {"value": "center"}}},
            {"id": "fx-cta", "useCase": "cta", "archetypeRef": "stack",
             "contentShape": {"alignment": {"value": "center"}}},
            {"id": "fx-grid", "useCase": "features", "archetypeRef": "grid",
             "contentShape": {"alignment": {"value": "left",
                                            "counterweight": "cards"}}},
        ]}
        (self.brand_dir / "layout-library.yaml").write_text(yaml.safe_dump(lib))
        self._mutate_brand(lambda d: d.update({"layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left", "counterweight": "media"},
            "standaloneStack": {"anchor": "centered"}}}}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C18")], [],
                         rep.errors)
        hits = [w for w in rep.warnings
                if w.startswith("C18") and "fx-grid" in w and "dissents" in w]
        self.assertEqual(1, len(hits), rep.warnings)
        # agreeing patterns never warn
        self.assertFalse(any("fx-cta" in w for w in rep.warnings
                             if w.startswith("C18")), rep.warnings)

    def test_curated_dissent_downgrades_to_a_note(self):
        # fid13 (brand-schema §4.4c): a dissent the curator already RULED ON is
        # resolved — informational note, no advisory warn.
        lib = {"patterns": [
            {"id": "fx-hero", "useCase": "hero", "archetypeRef": "split",
             "contentShape": {"alignment": {"value": "left",
                                            "counterweight": "media"}}},
            {"id": "fx-infra", "useCase": "about", "archetypeRef": "split",
             "contentShape": {"alignment": {"value": "left",
                                            "counterweight": "media"}}},
            {"id": "fx-logos", "useCase": "logos", "archetypeRef": "stack",
             "contentShape": {"alignment": {"value": "center"}}},
            {"id": "fx-cta", "useCase": "cta", "archetypeRef": "stack",
             "contentShape": {"alignment": {"value": "center"}}},
            {"id": "fx-grid", "useCase": "features", "archetypeRef": "grid",
             "contentShape": {"alignment": {"value": "left",
                                            "counterweight": "cards"}},
             "curation": {"alignment": {"resolve": "follow-grammar", "by": "user",
                                        "ts": "2026-07-09T19:25:00Z",
                                        "reason": "curator ruling"}}},
        ]}
        (self.brand_dir / "layout-library.yaml").write_text(yaml.safe_dump(lib))
        self._mutate_brand(lambda d: d.update({"layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left", "counterweight": "media"},
            "standaloneStack": {"anchor": "centered"}}}}))
        rep = self._validate()
        self.assertFalse(any(w.startswith("C18") and "fx-grid" in w
                             for w in rep.warnings), rep.warnings)
        notes = [n for n in rep.notes
                 if n.startswith("C18") and "fx-grid" in n and "curated" in n]
        self.assertEqual(1, len(notes), rep.notes)

    def test_one_context_alone_demands_nothing(self):
        # dissent/mixed or single-context evidence: the grammar is not demanded
        # (per-pattern facts already carry those sections).
        lib = {"patterns": [
            {"id": "fx-hero", "useCase": "hero", "archetypeRef": "split",
             "contentShape": {"alignment": {"value": "left"}}},
            {"id": "fx-infra", "useCase": "about", "archetypeRef": "split",
             "contentShape": {"alignment": {"value": "left"}}},
            {"id": "fx-logos", "useCase": "logos", "archetypeRef": "stack",
             "contentShape": {"alignment": {"value": "center"}}},
        ]}
        (self.brand_dir / "layout-library.yaml").write_text(yaml.safe_dump(lib))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C18")], [],
                         rep.errors)

    # ── C19 radius fidelity vs the mined census (fid13) ──────────────────────

    def _write_radius_census(self, census: dict, *corpus_decls: str):
        ev = self.brand_dir / "evidence"
        ev.mkdir(exist_ok=True)
        (ev / "css-facts.json").write_text(json.dumps(
            {"schemaVersion": 1, "radiusCensus": census}))
        (ev / "css-rules.json").write_text(json.dumps({
            "rules": [{"selector": ":root", "decls": "; ".join(corpus_decls)}]}))

    def test_radius_outside_the_published_ladder_fails(self):
        # the source publishes its OWN radius tokens (2/4/10/40) — an authored
        # 12px vision estimate is an invented fact, even though a 12px literal
        # exists in the census (third-party embed noise).
        self._write_radius_census(
            {"var(--x-radius-a)": 27, "var(--x-radius-b)": 7, "12px": 3, "0": 12},
            "--x-radius-a:10px", "--x-radius-b:40px")
        self._mutate_brand(lambda d: d["tokens"].update(
            {"radius": {"card": {"value": "0.75rem"}}}))
        rep = self._validate()
        hits = [e for e in rep.errors if e.startswith("C19") and "card" in e]
        self.assertEqual(1, len(hits), rep.errors)
        self.assertIn("published radius ladder", hits[0])

    def test_radius_on_the_ladder_passes_and_zero_is_always_legitimate(self):
        self._write_radius_census(
            {"var(--x-radius-a)": 27, "var(--x-radius-b)": 7},
            "--x-radius-a:10px", "--x-radius-b:40px")
        self._mutate_brand(lambda d: d["tokens"].update(
            {"radius": {"card": {"value": "0.625rem"},
                        "button": {"value": "2.5rem"},
                        "media": {"value": "0"}}}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C19")], [],
                         rep.errors)

    def test_literal_census_is_the_fallback_vocabulary(self):
        # no var()-backed entries: raw literals become the (weaker) vocabulary.
        self._write_radius_census({"6px": 9, "50%": 4, "0": 2})
        self._mutate_brand(lambda d: d["tokens"].update(
            {"radius": {"card": {"value": "6px"},
                        "panel": {"value": "1.25rem"}}}))
        rep = self._validate()
        errs = [e for e in rep.errors if e.startswith("C19")]
        self.assertEqual(1, len(errs), rep.errors)
        self.assertIn("panel", errs[0])
        self.assertIn("literal radius census", errs[0])

    def test_no_census_demands_nothing(self):
        self._mutate_brand(lambda d: d["tokens"].update(
            {"radius": {"card": {"value": "3rem"}}}))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C19")], [],
                         rep.errors)

    # ── C20 grid-equalization facts (fid14, brand-schema §4.4d, AS-50) ───────

    def _write_grid_library(self, shape: dict):
        lib = {"patterns": [
            {"id": "fx-hero", "useCase": "hero"},
            {"id": "fx-grid", "useCase": "features", "archetypeRef": "grid",
             "contentShape": shape},
        ]}
        (self.brand_dir / "layout-library.yaml").write_text(yaml.safe_dump(lib))

    def test_card_grid_without_an_equalization_stance_fails(self):
        self._write_grid_library({"alignment": {"value": "left"}})
        rep = self._validate()
        hits = [e for e in rep.errors if e.startswith("C20") and "fx-grid" in e]
        self.assertEqual(1, len(hits), rep.errors)
        self.assertIn("gridEqualize", hits[0])

    def test_authored_fact_or_not_observed_marker_passes(self):
        self._write_grid_library({"gridEqualize": {
            "heights": "stretch", "slack": "body", "actionPinned": True}})
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C20")], [],
                         rep.errors)
        self._write_grid_library({"gridEqualizeNotObserved": True})
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C20")], [],
                         rep.errors)

    def test_out_of_enum_heights_is_no_stance(self):
        self._write_grid_library({"gridEqualize": {"heights": "equalish"}})
        rep = self._validate()
        self.assertEqual(1, len([e for e in rep.errors if e.startswith("C20")]),
                         rep.errors)

    def test_non_grid_archetypes_are_exempt(self):
        lib = {"patterns": [
            {"id": "fx-hero", "useCase": "hero", "archetypeRef": "split"},
            {"id": "fx-logos", "useCase": "logos", "archetypeRef": "stack"},
        ]}
        (self.brand_dir / "layout-library.yaml").write_text(yaml.safe_dump(lib))
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C20")], [],
                         rep.errors)

    # ── C11 composed-demo smoke ──────────────────────────────────────────────

    def test_srcless_media_placeholder_fails_smoke(self):
        # remove the hero art + its defaultArt binding: the split hero's media
        # slot now composes the c-image-ph placeholder plate.
        for name in ART_FILES:
            (self.brand_dir / "assets" / name).unlink()
        copy = dict(FIXTURE_COPY)
        copy.pop("defaultArt")
        (self.brand_dir / "section-copy.yaml").write_text(yaml.safe_dump(copy))
        rep = self._validate(smoke=True)
        self.assertFalse(rep.ok)
        self.assertTrue(any(e.startswith("C11") and "c-image-ph" in e
                            for e in rep.errors), rep.errors)

    def test_uncomposable_pattern_fails_smoke(self):
        # a brand whose token set cannot drive the layer-1 generator must fail
        # C11 loudly (the composer refuses) instead of silently skipping.
        self._mutate_brand(lambda d: d.pop("voice"))
        rep = self._validate(smoke=True)
        joined = self._joined(rep.errors)
        self.assertFalse(rep.ok)
        self.assertTrue(any(e.startswith("C11") for e in rep.errors), rep.errors)
        self.assertIn("fx-hero", joined)

    def _center_aligned_library(self):
        # the alignment probe only runs on the hydration path — remove the
        # authored copy file so the harness hydrates the patterns (same gating
        # as compose_pattern_docs), then declare centered alignment on fx-hero.
        (self.brand_dir / "section-copy.yaml").unlink()
        lib = {"patterns": [
            {"id": "fx-hero", "useCase": "hero",
             "contentShape": {"alignment": {"value": "center"}}},
            {"id": "fx-logos", "useCase": "logos"},
        ]}
        (self.brand_dir / "layout-library.yaml").write_text(yaml.safe_dump(lib))

    def test_dropped_center_alignment_fails_smoke(self):
        # the pattern DECLARES centered alignment; if the demo-hydration path stops
        # stamping it onto the composition, C11 must catch the drop.
        self._center_aligned_library()
        import render_components_preview as rp  # brand_pipeline on sys.path via vbe
        real = rp._demo_section_for_pattern

        def dropping(doc, pat, layout):
            sec = real(doc, pat, layout)
            sec.pop("alignment", None)   # simulate the pre-fix regression
            return sec

        rp._demo_section_for_pattern = dropping
        try:
            rep = self._validate(smoke=True)
        finally:
            rp._demo_section_for_pattern = real
        self.assertFalse(rep.ok)
        self.assertTrue(any(e.startswith("C11") and "alignment" in e
                            for e in rep.errors), rep.errors)

    def test_declared_center_alignment_passes_smoke(self):
        self._center_aligned_library()
        rep = self._validate(smoke=True)
        self.assertEqual([e for e in rep.errors if "alignment" in e], [],
                         rep.errors)

    def test_action_pair_composes_primary_first(self):
        # the fixture hero declares "primary filled pill + outlined secondary
        # pill" — the composed pair must lead with the plain primary (and the
        # complete fixture stays green under the C11 order assertion).
        rep = self._validate(smoke=True)
        self.assertTrue(rep.ok, rep.errors)

    def test_empty_panel_split_fails_smoke(self):
        # simulate the pre-fix defect class: a split shipping the cream panel
        # with NO title/rows/foot (the invented-content removal left an empty
        # box). The composer now elides the panel; C11 polices regressions.
        import compose_section as cs2
        real = cs2.compose_info_band

        def empty_panel(doc, layout, ctx, rendered, style_ctx):
            return ('<section class="cs-section cs-split-sec"><div class="cs-split">'
                    '<div class="cs-panel">\n      \n      '
                    '<div class="c-rows"></div>\n      \n    </div>'
                    '</div></section>')

        cs2.compose_info_band = empty_panel
        try:
            rep = self._validate(smoke=True)
        finally:
            cs2.compose_info_band = real
        self.assertTrue(any(e.startswith("C11") and "EMPTY panel" in e
                            for e in rep.errors), rep.errors)

    def test_crossed_action_pair_fails_smoke(self):
        # simulate the pre-fix defect class: the whole-role prose reaches the
        # family dispatch, so the FIRST (primary) button takes the outline
        # family and the pair renders secondary-before-primary.
        import render_components_preview as rp
        real = rp._demo_section_for_pattern

        def crossing(doc, pat, layout):
            sec = real(doc, pat, layout)
            btns = [s for s in (sec.get("slots") or [])
                    if s.get("contract") == "button"]
            if len(btns) >= 2:
                btns[0]["role"] = "outlined secondary cta"
                btns[0].setdefault("copy", {})["styleHint"] = "outlined"
                (btns[1].get("copy") or {}).pop("styleHint", None)
                btns[1]["role"] = "primary cta"
            return sec

        rp._demo_section_for_pattern = crossing
        try:
            rep = self._validate(smoke=True)
        finally:
            rp._demo_section_for_pattern = real
        self.assertTrue(any(e.startswith("C11") and "primary" in e
                            for e in rep.errors), rep.errors)

    # ── C12 escape hygiene ───────────────────────────────────────────────────

    def test_double_escaped_entity_in_generated_html_fails(self):
        gen = self.brand_dir / "components-preview"
        gen.mkdir()
        (gen / "index.html").write_text(
            "<html><body>Global payroll &amp;mdash; everywhere</body></html>")
        rep = self._validate()
        self.assertFalse(rep.ok)
        self.assertTrue(any(e.startswith("C12") for e in rep.errors), rep.errors)

    def test_clean_generated_html_passes(self):
        gen = self.brand_dir / "components-preview"
        gen.mkdir()
        (gen / "index.html").write_text(
            "<html><body>Global payroll — everywhere &rarr;</body></html>")
        rep = self._validate()
        self.assertEqual([e for e in rep.errors if e.startswith("C12")], [])

    # ── C16 chrome depth facts (fid4 2026-07) ────────────────────────────────

    @staticmethod
    def _c16(rep):
        return [e for e in rep.errors if e.startswith("C16")]

    def _add_mega_menu(self, d, with_measured=True):
        d["navbar"]["primary"] = [
            {"label": "Products", "href": "/products", "menu": {
                "columns": [{"heading": "Things", "area": "main",
                             "links": [{"label": "Alpha", "href": "/a"}]}]}},
            {"label": "Pricing", "href": "/pricing"}]
        if with_measured:
            d["navbar"]["measured"] = {"megaPanel": {
                "surface": {"bg": "#ffffff"},
                "motion": {"panel": {"duration": "0.3s", "easing": "ease"}}}}

    def test_mega_menu_with_motion_facts_passes_c16(self):
        self._mutate_brand(self._add_mega_menu)
        self.assertEqual(self._c16(self._validate()), [])

    def test_mega_menu_without_megapanel_facts_fails_c16(self):
        self._mutate_brand(lambda d: self._add_mega_menu(d, with_measured=False))
        errs = self._c16(self._validate())
        self.assertTrue(any("measured.megaPanel" in e for e in errs), errs)

    def test_mega_menu_motion_without_time_literal_fails_c16(self):
        def mut(d):
            self._add_mega_menu(d)
            d["navbar"]["measured"]["megaPanel"]["motion"] = {"panel": {}}
        self._mutate_brand(mut)
        errs = self._c16(self._validate())
        self.assertTrue(any("no time literal" in e for e in errs), errs)

    def test_mega_menu_empty_column_fails_c16(self):
        def mut(d):
            self._add_mega_menu(d)
            d["navbar"]["primary"][0]["menu"]["columns"][0]["links"] = []
        self._mutate_brand(mut)
        errs = self._c16(self._validate())
        self.assertTrue(any("has no links" in e for e in errs), errs)

    def test_mega_open_without_menu_fails_c16(self):
        self._mutate_brand(lambda d: d["navbar"].__setitem__(
            "megaOpen", [{"label": "Products", "open": True,
                          "panel": {"w": 1440, "h": 400}}]))
        errs = self._c16(self._validate())
        self.assertTrue(any("megaOpen" in e for e in errs), errs)

    def test_icon_social_without_artwork_fails_c16(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "social", [{"network": "linkedin", "kind": "icon",
                        "href": "https://example.com/li"}]))
        errs = self._c16(self._validate())
        self.assertTrue(any("binds no artwork" in e for e in errs), errs)

    def test_icon_social_with_on_disk_asset_passes_c16(self):
        (self.brand_dir / "assets" / "social-linkedin.svg").write_text(
            "<svg xmlns='http://www.w3.org/2000/svg'/>")
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "social", [{"network": "linkedin", "kind": "icon",
                        "href": "https://example.com/li",
                        "icon": {"kind": "mask",
                                 "asset": "assets/social-linkedin.svg"}}]))
        self.assertEqual(self._c16(self._validate()), [])

    def test_icon_social_with_missing_asset_file_fails_c16(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "social", [{"network": "linkedin", "kind": "icon",
                        "href": "https://example.com/li",
                        "icon": {"kind": "mask",
                                 "asset": "assets/social-linkedin.svg"}}]))
        errs = self._c16(self._validate())
        self.assertTrue(any("not on disk" in e for e in errs), errs)

    def test_footer_wrapper_sizes_mismatch_fails_c16(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "measured", {"heading": {"color": "#595b5f", "fontSize": 14},
                         "grid": {"wrapperSizes": [2, 1]}}))
        errs = self._c16(self._validate())
        self.assertTrue(any("wrapperSizes" in e for e in errs), errs)

    def test_footer_headed_columns_without_heading_facts_fails_c16(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "measured", {"grid": {"wrapperSizes": [1]}}))
        errs = self._c16(self._validate())
        self.assertTrue(any("measured.heading" in e for e in errs), errs)

    def test_footer_hierarchy_facts_pass_c16(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "measured", {"heading": {"color": "#595b5f", "fontSize": 14},
                         "grid": {"wrapperSizes": [1]}}))
        self.assertEqual(self._c16(self._validate()), [])

    def test_bottom_bar_without_divider_presence_fails_c16(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "bottomBar", {"policyLinks": [{"label": "Privacy", "href": "/p"}]}))
        errs = self._c16(self._validate())
        self.assertTrue(any("divider" in e for e in errs), errs)

    def test_bottom_bar_malformed_policy_links_fail_c16(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "bottomBar", {"divider": {"present": True, "color": "#d2d3d5"},
                          "policyLinks": [{"label": "Privacy"}]}))
        errs = self._c16(self._validate())
        self.assertTrue(any("policyLinks" in e for e in errs), errs)

    def test_bottom_bar_complete_passes_c16(self):
        self._mutate_brand(lambda d: d["footer"].__setitem__(
            "bottomBar", {"divider": {"present": True, "color": "#d2d3d5"},
                          "policyLinks": [{"label": "Privacy", "href": "/p"}]}))
        self.assertEqual(self._c16(self._validate()), [])

    def test_social_and_legal_without_bottom_bar_warns_c16(self):
        rep = self._validate()
        self.assertEqual(self._c16(rep), [])
        self.assertTrue(any(w.startswith("C16") for w in rep.warnings), rep.warnings)

    # ── C17 disclosure per-item interaction content (fid8 2026-07) ───────────

    @staticmethod
    def _c17(rep):
        return [e for e in rep.errors if e.startswith("C17")]

    def _write_copy_items(self, items, **entry_extra):
        copy = dict(FIXTURE_COPY)
        copy["layoutCopy"] = dict(FIXTURE_COPY["layoutCopy"])
        copy["layoutCopy"]["hero-split"] = dict(copy["layoutCopy"]["hero-split"])
        copy["layoutCopy"]["hero-split"]["items"] = items
        copy["layoutCopy"]["hero-split"].update(entry_extra)
        (self.brand_dir / "section-copy.yaml").write_text(yaml.safe_dump(copy))

    def test_partial_disclosure_bodies_fail_c17(self):
        self._write_copy_items([
            {"heading": "Alpha", "body": "Open-state copy."},
            {"heading": "Beta"},
            {"heading": "Gamma"},
        ])
        errs = self._c17(self._validate())
        self.assertTrue(any("Beta" in e and "Gamma" in e for e in errs), errs)

    def test_full_disclosure_bodies_pass_c17(self):
        self._write_copy_items([
            {"heading": "Alpha", "body": "One."},
            {"heading": "Beta", "body": "Two."},
        ])
        self.assertEqual(self._c17(self._validate()), [])

    def test_body_not_observed_marker_passes_c17(self):
        self._write_copy_items([
            {"heading": "Alpha", "body": "One."},
            {"heading": "Beta", "bodyNotObserved": True},
        ])
        self.assertEqual(self._c17(self._validate()), [])

    def test_entry_level_not_observed_marker_passes_c17(self):
        self._write_copy_items(
            [{"heading": "Alpha", "body": "One."}, {"heading": "Beta"}],
            itemBodiesNotObserved=True)
        self.assertEqual(self._c17(self._validate()), [])

    def test_label_only_items_owe_nothing_c17(self):
        self._write_copy_items([{"heading": "Alpha"}, {"heading": "Beta"}])
        self.assertEqual(self._c17(self._validate()), [])

    def test_partial_item_media_fails_c17(self):
        self._write_copy_items([
            {"heading": "Alpha", "body": "One.", "media": "art-hero.webp"},
            {"heading": "Beta", "body": "Two."},
        ])
        errs = self._c17(self._validate())
        self.assertTrue(any("media" in e and "Beta" in e for e in errs), errs)

    def test_full_item_media_on_disk_passes_c17(self):
        self._write_copy_items([
            {"heading": "Alpha", "body": "One.", "media": "art-hero.webp"},
            {"heading": "Beta", "body": "Two.", "media": "art-hero.webp"},
        ])
        self.assertEqual(self._c17(self._validate()), [])

    def test_item_media_missing_file_fails_c17(self):
        self._write_copy_items([
            {"heading": "Alpha", "body": "One.", "media": "art-hero.webp"},
            {"heading": "Beta", "body": "Two.", "media": "ghost-collage.webp"},
        ])
        errs = self._c17(self._validate())
        self.assertTrue(any("ghost-collage.webp" in e for e in errs), errs)

    def test_media_not_observed_marker_passes_c17(self):
        self._write_copy_items([
            {"heading": "Alpha", "body": "One.", "media": "art-hero.webp"},
            {"heading": "Beta", "body": "Two.", "mediaNotObserved": True},
        ])
        self.assertEqual(self._c17(self._validate()), [])

    # ── C22: two-tier chrome contract advisory (fix1 2026-07) ────────────────

    def test_measured_utility_tier_without_contract_warns_c22(self):
        self._mutate_brand(lambda d: d["navbar"].__setitem__(
            "measured", {"utilityBarHeight": 40, "primaryBarHeight": 88}))
        rep = self._validate()
        self.assertTrue(any(w.startswith("C22") for w in rep.warnings),
                        rep.warnings)
        self.assertTrue(any(e.startswith("C22") for e in rep.warnings
                            if "utilityTier" in e))
        # advisory, never an error
        self.assertFalse(any(e.startswith("C22") for e in rep.errors))

    def test_declared_utility_tier_silences_c22(self):
        def mut(d):
            d["navbar"]["measured"] = {"utilityBarHeight": 40,
                                       "primaryBarHeight": 88}
            d["navbar"]["utilityTier"] = {"height": 40, "bg": "#ffffff",
                                          "trailing": ["Log in"]}
        self._mutate_brand(mut)
        rep = self._validate()
        self.assertFalse(any(w.startswith("C22") for w in rep.warnings),
                         rep.warnings)

    def test_collapsed_utility_tier_owes_nothing_c22(self):
        self._mutate_brand(lambda d: d["navbar"].__setitem__(
            "measured", {"utilityBarHeight": 0, "primaryBarHeight": 81}))
        rep = self._validate()
        self.assertFalse(any(w.startswith("C22") for w in rep.warnings),
                         rep.warnings)

    # ── C4 join-key integrity + C29 internal-id leak (hubspot-v3 regression
    #    2026-07: staged author emitted slots without `type: content`, keyed
    #    layoutCopy by invented names, minted an unconsumed `sourceCopy:`
    #    indirection, and briefly wrote the lane slug as brand.name — all of
    #    which validated green and rendered internal ids as display copy) ────

    def test_layoutcopy_without_any_content_slot_fails_c4(self):
        # strip `type:` from every slot — the coverage check must fail loud,
        # not silently skip every layout
        def mut(d):
            for lay in d["layouts"]:
                for s in lay.get("slots") or []:
                    s.pop("type", None)
        self._mutate_brand(mut)
        rep = self._validate()
        self.assertFalse(rep.ok)
        msg = self._joined(rep.errors)
        self.assertIn("type: content", msg)
        self.assertTrue(any(e.startswith("C4") for e in rep.errors))

    def test_orphan_layoutcopy_keys_fail_c4(self):
        copy_doc = yaml.safe_load(
            (self.brand_dir / "section-copy.yaml").read_text())
        copy_doc["layoutCopy"]["heroCamelKey"] = {"heading": "Orphaned"}
        (self.brand_dir / "section-copy.yaml").write_text(
            yaml.safe_dump(copy_doc))
        rep = self._validate()
        self.assertFalse(rep.ok)
        msg = self._joined(rep.errors)
        self.assertIn("heroCamelKey", msg)
        self.assertIn("NO layout id", msg)

    def test_sourcecopy_indirection_fails_c4(self):
        self._mutate_brand(lambda d: d["layouts"][0]["slots"][0].__setitem__(
            "sourceCopy", "layoutCopy.hero.heading"))
        rep = self._validate()
        self.assertFalse(rep.ok)
        msg = self._joined(rep.errors)
        self.assertIn("sourceCopy", msg)
        self.assertTrue(any(e.startswith("C4") for e in rep.errors))

    def _clone_fixture_under_lane(self, lane: str) -> Path:
        lane_dir = self.root / lane
        lane_dir.mkdir()
        cloned = lane_dir / "brand"
        shutil.copytree(self.brand_dir, cloned)
        return cloned

    def test_lane_slug_as_brand_name_fails_c29(self):
        cloned = self._clone_fixture_under_lane("acme-v3")
        doc = yaml.safe_load((cloned / "brand.yaml").read_text())
        doc["brand"]["name"] = "acme-v3"
        (cloned / "brand.yaml").write_text(yaml.safe_dump(doc))
        rep = vbe.validate_brand_dir(cloned, contracts_path=self.contracts,
                                     smoke=False)
        self.assertTrue(any(e.startswith("C29") for e in rep.errors),
                        rep.errors)

    def test_lane_slug_as_wordmark_fails_c29(self):
        cloned = self._clone_fixture_under_lane("acme-v7")
        copy_doc = yaml.safe_load((cloned / "section-copy.yaml").read_text())
        copy_doc["sectionCopy"]["wordmark"] = "acme-v7"
        (cloned / "section-copy.yaml").write_text(yaml.safe_dump(copy_doc))
        rep = vbe.validate_brand_dir(cloned, contracts_path=self.contracts,
                                     smoke=False)
        self.assertTrue(any(e.startswith("C29") for e in rep.errors),
                        rep.errors)

    def test_markerless_lane_named_after_brand_passes_c29(self):
        # runs/remote -> brand "Remote" is legitimate: no version/scratch
        # marker in the slug means no leak, even though name == slug
        cloned = self._clone_fixture_under_lane("fixture")
        doc = yaml.safe_load((cloned / "brand.yaml").read_text())
        doc["brand"]["name"] = "Fixture"
        (cloned / "brand.yaml").write_text(yaml.safe_dump(doc))
        rep = vbe.validate_brand_dir(cloned, contracts_path=self.contracts,
                                     smoke=False)
        self.assertFalse(any(e.startswith("C29") for e in rep.errors),
                         rep.errors)


if __name__ == "__main__":
    unittest.main()
