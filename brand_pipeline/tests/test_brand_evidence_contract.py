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
    "type": {
        "display-hero": {"family": "Georgia", "sizeRem": {"base": 3.0}, "weight": 700},
        "h1": {"family": "Georgia", "sizeRem": {"base": 2.5}, "weight": 700},
        "h2": {"family": "Georgia", "sizeRem": {"base": 2.0}, "weight": 700},
        "h3": {"family": "Georgia", "sizeRem": {"base": 1.5}, "weight": 600},
        "body": {"family": "Helvetica", "sizeRem": {"base": 1.0}, "weight": 400},
        "small": {"family": "Helvetica", "sizeRem": {"base": 0.875}, "weight": 400},
        "eyebrow": {"family": "Helvetica", "sizeRem": {"base": 0.8125}, "weight": 600},
        "control-text": {"family": "Helvetica", "sizeRem": {"base": 0.9375},
                         "weight": 500},
    },
    "spacing": {
        "section-padding-light": {"value": "5rem"},
        "eyebrow-to-heading": {"value": "1rem"},
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
                                  "body": "Real fixture body copy."}},
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
        self._mutate_brand(lambda d: d["navbar"].__setitem__(
            "primary",
            [{"label": "Products",
              "menu": {"columns": [
                  {"heading": "Global Employment",
                   "links": [{"label": "Payroll Run"}]}]}}]))
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


if __name__ == "__main__":
    unittest.main()
