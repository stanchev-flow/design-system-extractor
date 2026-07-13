#!/usr/bin/env python3
"""FID17 regressions for the shared image loading/error placeholder lifecycle."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_BP = Path(__file__).resolve().parent.parent
if str(_BP) not in sys.path:
    sys.path.insert(0, str(_BP))

import component_render as cr  # noqa: E402


DOC = {
    "brand": {"name": "Fixture"},
    "tokens": {"surfaces": {
        "surface/primary": {"bg": "#fff", "textPrimary": "text/default"}}},
}
CTX = cr.make_context(DOC, "surface/primary",
                      DOC["tokens"]["surfaces"]["surface/primary"])


class ImagePlaceholderCssTest(unittest.TestCase):
    def test_unresolved_state_has_token_derived_hatch(self):
        rule = re.search(r"\.c-image \{(.*?)\n\}", cr.COMPONENT_CSS, re.S)
        self.assertIsNotNone(rule)
        self.assertIn("repeating-linear-gradient", rule.group(1))
        self.assertIn("var(--c-paper)", rule.group(1))
        self.assertIn("var(--c-ink)", rule.group(1))

    def test_loaded_state_removes_backing(self):
        self.assertIn(
            '.c-image[data-load-state="loaded"] { background: none; }',
            cr.COMPONENT_CSS)

    def test_error_state_retains_base_hatch(self):
        self.assertNotIn('.c-image[data-load-state="error"]', cr.COMPONENT_CSS)
        self.assertIn("set('error')", cr._IX_IMAGE_JS)

    def test_art_stays_hatch_free_without_javascript(self):
        rule = re.search(r"\.c-image--art \{([^}]*)\}", cr.COMPONENT_CSS)
        self.assertIsNotNone(rule)
        self.assertIn("background: none", rule.group(1))


class ImageLifecycleScriptTest(unittest.TestCase):
    def test_script_is_emitted_only_for_real_shared_images(self):
        image = cr.render_image(DOC, CTX, {"src": "assets/asset.bin", "alt": ""})
        self.assertIn("data-load-state", cr.interaction_script(image))
        self.assertEqual("", cr.interaction_script('<div class="c-image-ph">IMAGE</div>'))

    def test_cached_images_reconcile_complete_and_natural_width(self):
        script = cr._IX_IMAGE_JS
        self.assertIn("if (img.complete)", script)
        self.assertIn("if (img.naturalWidth > 0) loaded()", script)
        self.assertIn("else failed()", script)

    def test_lazy_images_keep_future_load_and_error_listeners(self):
        script = cr._IX_IMAGE_JS
        self.assertLess(script.index("addEventListener('load'"), script.index("if (img.complete)"))
        self.assertIn("addEventListener('error'", script)

    def test_state_logic_has_no_filename_extension_or_brand_heuristics(self):
        script = cr._IX_IMAGE_JS.lower()
        for forbidden in (".png", ".svg", ".webp", ".jpg", "fixture", "remote", "brand"):
            self.assertNotIn(forbidden, script)
        facts = {
            "_assetTags": {
                "looks-transparent.svg": {"assetKind": "photo"},
                "opaque-name.bin": {"assetKind": "transparent-illustration"},
            },
            "_mediaTreatmentRules": [
                {"assetKind": "photo", "role": "*", "fit": "cover"},
                {"assetKind": "transparent-illustration", "role": "*", "fit": "contain"},
            ],
        }
        self.assertEqual("cover", cr.asset_render_mode(facts, "looks-transparent.svg"))
        self.assertEqual("contain", cr.asset_render_mode(facts, "opaque-name.bin"))


if __name__ == "__main__":
    unittest.main()
