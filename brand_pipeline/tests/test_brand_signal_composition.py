#!/usr/bin/env python3
"""Brand-signal composition + retire HubSpot/SaaS globals (2026-07).

Pins:
  - no unconditional #sec-0 / hero 100cqh full-frame height
  - numeric lists do not invent stats without brand license
  - measured brand anatomy preserves slot contracts
  - compositionSignals derived from layouts
  - framework generation off by default
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
_REPO = _BRAND_PIPELINE.parent
for p in (_BRAND_PIPELINE, _REPO):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import composition_signals as cosig  # noqa: E402
import compose_from_composition as cfc  # noqa: E402
import compose_page as cp  # noqa: E402
import yaml  # noqa: E402


class NoForcedFullHeight(unittest.TestCase):
    def test_page_css_does_not_force_sec0_viewport(self):
        css = cp.page_scaffold_css()
        self.assertNotIn("#sec-0 .cs-section { min-height: 100cqh; }", css)
        self.assertIn(".cs-section { min-height: auto; }", css)

    def test_hero_scaffold_is_content_sized(self):
        import compose_section as cs
        self.assertIn("min-height: auto", cs.SCAFFOLD_HERO_CSS)
        self.assertNotIn("min-height: 100cqh", cs.SCAFFOLD_HERO_CSS)
        self.assertNotIn("min-height: min(90svh", cs.SCAFFOLD_OVERLAY_CSS)


class SlotPreservation(unittest.TestCase):
    def test_numeric_list_does_not_become_stats_without_brand_license(self):
        section = {
            "id": "numbers",
            "archetype": "stack",
            "useCase": "features",
            "seededFrom": {"id": "numbers", "lib": "project"},
            "slots": [
                {"name": "heading", "contract": "heading", "copy": "By the numbers"},
                {"name": "items", "contract": "list", "copy": [
                    {"label": "170+", "text": "integrations"},
                    {"label": "50%", "text": "faster"},
                    {"label": "12k", "text": "customers"},
                ]},
            ],
        }
        layout = cfc.composition_to_layout(section)
        contracts = [m.get("contract") for m in (layout.get("blockMapping") or [])]
        self.assertNotIn("stat", contracts)
        # Brand anatomy → preserve the authored list contract.
        self.assertTrue(any(c == "list" for c in contracts) or
                        any(m.get("slot") == "items" for m in (layout.get("blockMapping") or [])))

    def test_explicit_stat_contract_still_maps(self):
        section = {
            "id": "stats",
            "archetype": "stack",
            "useCase": "features",
            "slots": [
                {"name": "stats", "contract": "stat", "copy": [
                    {"value": "170+", "label": "integrations"},
                    {"value": "50%", "label": "faster"},
                ]},
            ],
        }
        layout = cfc.composition_to_layout(section)
        contracts = [m.get("contract") for m in (layout.get("blockMapping") or [])]
        self.assertIn("stat", contracts)

    def test_brand_anatomy_prefers_slot_pass_through(self):
        section = {
            "id": "about",
            "archetype": "stack",
            "useCase": "about",
            "structureProvenance": "measured-brand-pattern",
            "slots": [
                {"name": "eyebrow", "contract": "eyebrow", "copy": "About"},
                {"name": "heading", "contract": "heading", "copy": "Our story"},
                {"name": "body", "contract": "paragraph", "copy": "We build tools."},
            ],
        }
        layout = cfc.composition_to_layout(section)
        mapping = layout.get("blockMapping") or []
        by_slot = {m.get("slot"): m.get("contract") for m in mapping}
        self.assertEqual(by_slot.get("eyebrow"), "eyebrow")
        self.assertEqual(by_slot.get("heading"), "heading")
        self.assertEqual(by_slot.get("body"), "paragraph")


class CompositionSignals(unittest.TestCase):
    def test_extract_from_layouts(self):
        doc = {
            "layouts": [
                {
                    "id": "opening-bookend",
                    "useCase": "hero",
                    "archetype": "stack",
                    "geometry": {"bandHeight": "viewport"},
                    "slots": [
                        {"name": "heading", "contract": "heading"},
                        {"name": "media", "contract": "image"},
                    ],
                },
                {
                    "id": "editorial",
                    "useCase": "about",
                    "archetype": "stack",
                    "slots": [
                        {"name": "heading", "contract": "heading"},
                        {"name": "body", "contract": "paragraph"},
                    ],
                },
            ]
        }
        bag = cosig.extract_composition_signals(doc)
        self.assertEqual(bag["schemaVersion"], "compositionSignals.v1")
        self.assertIn("opening-bookend", bag["byLayoutId"])
        self.assertTrue(bag["byLayoutId"]["opening-bookend"]["presence"]["media"])
        self.assertTrue(bag["byLayoutId"]["editorial"]["textForward"])
        self.assertFalse(bag["byLayoutId"]["editorial"]["wantsStat"])
        self.assertEqual(bag["page"]["layoutOrder"], ["opening-bookend", "editorial"])

    def test_apply_signals_stamps_preserve_anatomy(self):
        doc = {
            "layouts": [{
                "id": "editorial",
                "useCase": "about",
                "slots": [
                    {"name": "heading", "contract": "heading"},
                    {"name": "body", "contract": "paragraph"},
                ],
            }],
        }
        doc = cosig.attach_signals_to_doc(doc)
        section = cosig.apply_signals_to_section({"id": "editorial", "slots": []}, doc)
        self.assertTrue(section.get("_preserveAnatomy"))
        self.assertTrue(section.get("licensedTextOnly"))
        self.assertFalse(section.get("proofRequired"))


    def test_block_mapping_contracts_enrich_slot_signals(self):
        doc = {
            "layouts": [{
                "id": "stats",
                "useCase": "numbers",
                "slots": [{"name": "items", "role": "stat-column-list"}],
                "blockMapping": [{"slot": "items", "contract": "stat-block"}],
            }],
        }
        sig = cosig.extract_composition_signals(doc)["byLayoutId"]["stats"]
        self.assertEqual(sig["slotRecipe"][0]["contract"], "stat-block")
        self.assertTrue(sig["wantsStat"])
        self.assertFalse(sig["textForward"])


class FrameworkDefaultOff(unittest.TestCase):
    def test_config_default_disables_framework_generation(self):
        cfg = yaml.safe_load((_REPO / "config.default.yaml").read_text())
        self.assertFalse(cfg.get("framework-generation-enabled"))


if __name__ == "__main__":
    unittest.main()
