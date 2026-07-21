#!/usr/bin/env python3
"""ASSET-KIND ↔ SLOT-ROLE ELIGIBILITY (media-assets-schema §6.1; anti-slop AS-80).

The failure this closes: an ICON-family asset (spot-icon/ui-glyph/social-icon/logo
mark) bound as a card's HERO/LEAD media — blown up to fill a media well where an
image belongs. An icon may sit INSIDE a card at mark height (above the heading);
it must NEVER be the card's lead/hero/full-bleed image. This module covers:

- the declarative eligibility table + helpers (kind_family / is_icon_family /
  role_demands_image / eligible_render_mode) — generic, brand-agnostic;
- the render-time coercion arm in ``component_render.asset_render_mode``: an
  EXPLICIT media-well fit authored on an icon/mark asset renders at ``mark``, while
  the unset default stays ``cover`` (held-baseline byte-identity);
- the AS-80 gate row in ``media_semantics.lint_media_bindings``: an icon bound into
  an image/hero-lead/full-bleed role OR carrying an explicit media-well fit FAILS;
- the HubSpot v3 product-platform acceptance: the two glyphs that were mis-scaled as
  lead media (small-business sprocket, Breeze/AEO sparkle) resolve to ``mark`` and
  the replica renders them in the mark row, never a media well.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import compose_section as cs  # noqa: E402
import component_render as cr  # noqa: E402
import media_semantics as ms  # noqa: E402
import onbrand_check as oc  # noqa: E402

V3 = REPO / "runs" / "hubspot-v3" / "brand"


class EligibilityTable(unittest.TestCase):
    """The generic, brand-agnostic declarative table + helpers."""

    def test_kind_families(self):
        for k in ("spot-icon", "ui-glyph", "social-icon", "logo-own",
                  "logo-third-party"):
            self.assertEqual(ms.kind_family(k), "icon", k)
            self.assertTrue(ms.is_icon_family(k), k)
        for k in ("photograph", "portrait", "illustration",
                  "product-ui-screenshot", "product-packshot", "3d-render",
                  "diagram", "background-art"):
            self.assertEqual(ms.kind_family(k), "image", k)
            self.assertFalse(ms.is_icon_family(k), k)
        for k in ("badge-review-award", "badge-compliance", "badge-appstore"):
            self.assertEqual(ms.kind_family(k), "badge", k)

    def test_role_demands_image(self):
        for role in ("hero-media", "background-media", "full-bleed", "feature-image",
                     "product-shot", "portrait-media", "illustration-media",
                     "split-media", "lead visual"):
            self.assertTrue(ms.role_demands_image(role), role)
        for role in ("spot-icon", "above-heading glyph", "nav", "social row",
                     "card-grid", "eyebrow"):
            self.assertFalse(ms.role_demands_image(role), role)

    def test_eligible_render_mode_coerces_only_explicit_icon_media_well(self):
        # icon-family + EXPLICIT media-well fit -> mark (never blown up)
        self.assertEqual(ms.eligible_render_mode("spot-icon", "cover"), "mark")
        self.assertEqual(ms.eligible_render_mode("logo-third-party", "contain"), "mark")
        # icon-family + mark -> mark (unchanged)
        self.assertEqual(ms.eligible_render_mode("spot-icon", "mark"), "mark")
        # icon-family + UNSET -> not coerced here (renderer keeps its cover default)
        self.assertEqual(ms.eligible_render_mode("spot-icon", ""), "")
        # image-family passes through unchanged on every fit (byte-identity)
        for fit in ("cover", "contain", "mark", ""):
            self.assertEqual(ms.eligible_render_mode("photograph", fit), fit)
            self.assertEqual(ms.eligible_render_mode("illustration", fit), fit)


class RenderModeCoercion(unittest.TestCase):
    def _doc(self):
        doc = {}
        cs.attach_asset_inventory(doc, V3)
        return doc

    def test_icon_family_never_covers_when_fit_explicit(self):
        doc = self._doc()
        # a synthetic explicit cover fit on an icon is coerced to mark
        doc = {**doc, "_mediaAssetsFit": {**doc["_mediaAssetsFit"],
                                          "035-breeze-20icon.svg": "cover"}}
        self.assertEqual(
            cr.asset_render_mode(doc, "035-breeze-20icon.svg", "card-media"), "mark")

    def test_reclassified_v3_glyphs_render_mark(self):
        doc = self._doc()
        for f in ("009-small-business.svg", "027-ai-20sparkle.svg"):
            self.assertEqual(cr.asset_render_mode(doc, f, "card-media"), "mark", f)

    def test_photograph_still_covers(self):
        doc = self._doc()
        self.assertEqual(
            cr.asset_render_mode(doc, "018-hs-full-bleed-1-optmised.webp",
                                 "hero-background"), "cover")


class AS80Audit(unittest.TestCase):
    """The hard gate row: icon-family bound as image/lead media FAILS."""

    def setUp(self):
        self.reg = ms.load_media_assets(V3)

    def _hits(self, comp):
        return [h for h in ms.lint_media_bindings(comp, self.reg)
                if h[1] == "slot-role-eligibility"]

    def test_icon_in_hero_lead_role_fails(self):
        comp = {"sections": [{"id": "hero", "slots": [
            {"name": "background-media", "role": "background-media",
             "contract": "image", "assetRef": "small-business"}]}]}
        hits = self._hits(comp)
        self.assertEqual(len(hits), 1)
        self.assertIn("small-business", hits[0][2])

    def test_icon_via_card_item_in_image_role_fails(self):
        comp = {"sections": [{"id": "s", "slots": [
            {"name": "lead", "role": "feature-image", "contract": "image",
             "copy": [{"heading": "x", "asset": "027-ai-20sparkle.svg"}]}]}]}
        self.assertEqual(len(self._hits(comp)), 1)

    def test_icon_with_explicit_cover_fit_fails(self):
        # a registry entry whose kind is icon but fit is a media well is a mis-scale
        reg = json.loads(json.dumps(self.reg))
        for a in reg["assets"]:
            if a.get("id") == "small-business":
                a["treatmentDefaults"] = {"fit": "cover"}
        comp = {"sections": [{"id": "cards", "slots": [
            {"name": "card-grid", "role": "card-grid", "contract": "card",
             "copy": [{"heading": "Bundle", "asset": "009-small-business.svg"}]}]}]}
        hits = [h for h in ms.lint_media_bindings(comp, reg)
                if h[1] == "slot-role-eligibility"]
        self.assertEqual(len(hits), 1)
        self.assertIn("mis-scaled", hits[0][2])

    def test_icon_as_mark_in_card_role_passes(self):
        comp = {"sections": [{"id": "cards", "slots": [
            {"name": "card-grid", "role": "card-grid", "contract": "card",
             "copy": [{"heading": "Bundle", "asset": "009-small-business.svg"},
                      {"heading": "Marketing", "asset":
                       "028-producticons-marketinghub-icon-orange.webp"}]}]}]}
        self.assertEqual(self._hits(comp), [])

    def test_image_family_in_image_role_passes(self):
        comp = {"sections": [{"id": "hero", "slots": [
            {"name": "background-media", "role": "background-media",
             "contract": "image", "asset": {
                 "src": "018-hs-full-bleed-1-optmised.webp"}}]}]}
        self.assertEqual(self._hits(comp), [])


class V3ProductPlatformAcceptance(unittest.TestCase):
    """The concrete run this fix was cut against: the product-platform card grid."""

    def test_v3_composition_lints_eligibility_clean(self):
        reg = ms.load_media_assets(V3)
        comp = json.loads((V3 / "compose/replica/composition.json").read_text())
        hits = ms.lint_media_bindings(comp, reg)
        self.assertEqual([h for h in hits if h[1] == "slot-role-eligibility"], [])

    def test_gate_row_registered_and_clean_for_v3_product_cards(self):
        # the composed-lane gate (onbrand_check --composition) surfaces the AS-80
        # row; a v3 product card grid binding the reclassified glyphs as marks reads
        # clean. (The replica lane is a replica-composition.v1, not a generated
        # composition.v1, so it is exercised via lint_media_bindings above.)
        import tempfile
        comp = {"schemaVersion": "composition.v1", "brand": {
            "ref": str(V3 / "brand.yaml")},
            "sections": [{"id": "product-platform", "useCase": "features",
                          "slots": [{"name": "card-grid", "role": "card-grid",
                                     "contract": "card", "copy": [
                              {"heading": "Small Business Bundle",
                               "asset": "009-small-business.svg"},
                              {"heading": "AEO (Beta)",
                               "asset": "027-ai-20sparkle.svg"},
                              {"heading": "Marketing Hub",
                               "asset":
                               "028-producticons-marketinghub-icon-orange.webp"}]}]}]}
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "composition.json").write_text(json.dumps(comp))
            rows = oc.check_media_bindings(Path(td))
        rules = {r[0] for r in rows}
        self.assertIn("slot-role-eligibility", rules)
        for rid, _label, passed, detail in rows:
            self.assertTrue(passed, f"{rid}: {detail}")

    def test_v3_replica_renders_glyphs_as_mark_not_media_well(self):
        html = (V3 / "compose/replica/index.html").read_text()
        self.assertIn("cs-module-media--mark", html)
        for f in ("009-small-business.svg", "027-ai-20sparkle.svg"):
            # the glyph is NOT inside a media-well figure (aspect-ratio well)
            self.assertNotIn(f'cs-module-media" style="aspect-ratio: 16 / 10;">'
                             f'<img class="c-image" src="assets/{f}"', html)


if __name__ == "__main__":
    unittest.main()
