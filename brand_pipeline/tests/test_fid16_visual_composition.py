#!/usr/bin/env python3
"""FID16 regressions: simple-device degradation, fact-driven media treatment,
standalone header alignment, and stable semantic comparison anatomy."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_BP = Path(__file__).resolve().parent.parent
if str(_BP) not in sys.path:
    sys.path.insert(0, str(_BP))

import component_render as cr  # noqa: E402
import compose_from_composition as cfc  # noqa: E402
import compose_section as cs  # noqa: E402


DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {"surfaces": {
        "surface/primary": {"bg": "#fff", "textPrimary": "text/default"}}},
}


def _ctx():
    return cr.make_context(DOC, "surface/primary",
                           DOC["tokens"]["surfaces"]["surface/primary"])


class MediaTreatmentFactsTest(unittest.TestCase):
    def test_filename_words_and_brand_names_never_control_fit(self):
        doc = {"_assetTags": {
            "brand-illustration-screenshot.svg": {"assetKind": "photo"},
            "opaque.bin": {"assetKind": "transparent-illustration"},
        }, "_mediaTreatmentRules": [
            {"assetKind": "transparent-illustration", "role": "*", "fit": "contain"},
            {"assetKind": "photo", "role": "*", "fit": "cover"},
        ]}
        self.assertEqual(
            "cover", cr.asset_render_mode(doc, "brand-illustration-screenshot.svg", "card-media"))
        self.assertEqual("contain", cr.asset_render_mode(doc, "opaque.bin", "card-media"))

    def test_slot_role_can_authorize_full_bleed_product_ui(self):
        doc = {"_assetTags": {"asset.webp": {"assetKind": "product-UI"}},
               "_mediaTreatmentRules": [
                   {"assetKind": "product-UI", "role": "card-media", "fit": "cover"}]}
        self.assertEqual("cover", cr.asset_render_mode(doc, "asset.webp", "card-media"))

    def test_inventory_loader_consumes_generic_rules(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "assets-tagged.json").write_text(json.dumps({
                "assets": [{"filename": "asset.webp",
                            "useCase": "transparent-illustration"}],
                "mediaTreatmentRules": [{
                    "assetKind": "transparent-illustration", "role": "*", "fit": "contain"}],
            }))
            doc = {}
            cs.attach_asset_inventory(doc, root)
            self.assertEqual("contain", cr.asset_render_mode(doc, "asset.webp", "split-media"))


class SimplestDeviceTest(unittest.TestCase):
    def test_media_split_is_first_class_adapter_archetype(self):
        layout = cfc.composition_to_layout({
            "id": "statement", "useCase": "statement", "archetype": "media-split",
            "slots": [
                {"role": "caption", "contract": "caption", "copy": {"text": "Label"}},
                {"role": "statement", "contract": "heading", "copy": {"heading": "Claim"}},
                {"role": "support", "contract": "paragraph", "copy": {"text": "Support"}},
                {"role": "media", "contract": "image", "mediaAspect": "landscape",
                 "asset": {"src": "asset.webp"}},
                {"role": "action", "contract": "link", "copy": {"label": "Go"}},
            ],
        })
        self.assertEqual("media-split", layout["archetype"])
        self.assertEqual("Support", layout["_composerCopy"]["support"])
        self.assertEqual("Go", layout["_composerCopy"]["cta"])

    def test_interlock_requires_every_shape_precondition(self):
        canonical = {
            "caption": "Label", "statement": "Long statement", "asset": "asset.webp",
            "mediaOrientation": "landscape", "interlockEvidence": {"source": "capture"},
        }
        self.assertTrue(cs.interlock_preconditions(canonical, {}))
        for missing in ("caption", "statement", "asset", "interlockEvidence"):
            probe = dict(canonical)
            probe.pop(missing)
            self.assertFalse(cs.interlock_preconditions(probe, {}), missing)
        self.assertFalse(cs.interlock_preconditions(canonical, {"support": "extra"}))
        self.assertFalse(cs.interlock_preconditions(
            {**canonical, "mediaOrientation": "square"}, {}))

    def test_interlock_css_uses_grid_not_float_clear(self):
        css = cs.SCAFFOLD_INTERLOCK_CSS
        self.assertIn("display: grid", css)
        self.assertNotRegex(css, r"\bfloat\s*:")
        self.assertNotRegex(css, r"\bclear\s*:")


class ComparisonAnatomyTest(unittest.TestCase):
    def test_comparison_rows_have_fixed_label_track_and_mobile_stack(self):
        html = cr.render_table(DOC, _ctx(), {
            "comparison": True,
            "rows": [{"label": "Short", "value": "Value"},
                     {"label": "A much longer label", "value": "Other"}],
        })
        self.assertIn('class="c-table c-table--comparison"', html)
        self.assertIn('<col class="c-table-label-col">', html)
        self.assertEqual(2, html.count('<th scope="row">'))
        self.assertIn("table-layout: fixed", cr.COMPONENT_CSS)
        self.assertIn(".c-table--comparison col.c-table-label-col { width: 9rem; }",
                      cr.COMPONENT_CSS)
        self.assertIn("@media (max-width: 767px)", cr.COMPONENT_CSS)

    def test_comparison_header_resolves_standalone_grammar(self):
        section = {
            "id": "compare", "useCase": "comparison", "archetype": "split",
            "slots": [{"role": "heading", "contract": "heading",
                       "copy": {"heading": "Compare"}}],
        }
        layout = cfc.composition_to_layout(section)
        self.assertEqual("standaloneStack", layout["_headerContext"])
        grammar = {"layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left"},
            "standaloneStack": {"anchor": "centered"},
        }}}
        self.assertEqual("centered", cs.resolve_alignment(layout, doc=grammar)["anchor"])

    def test_ordinary_split_header_stays_split_column(self):
        layout = {"id": "split", "archetype": "split"}
        grammar = {"layoutGrammar": {"headerContext": {
            "splitColumn": {"anchor": "left"},
            "standaloneStack": {"anchor": "centered"},
        }}}
        self.assertEqual("left", cs.resolve_alignment(layout, doc=grammar)["anchor"])


if __name__ == "__main__":
    unittest.main()
