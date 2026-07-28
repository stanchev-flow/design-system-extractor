#!/usr/bin/env python3
"""Regression tests for the composer MULTI-COLUMN preservation fix (2026-07).

Root cause fixed: a section whose authored ``archetype`` is a DESCRIPTIVE / structural
label the renderer has no bespoke composer for (e.g. ``three-column-media-top-cards``)
used to route straight to the single-column ``generic-flow`` safety net, collapsing
every authored multi-column module into one narrow vertical stack. ``composition_to_layout``
now INFERS the closest drawable archetype from the section's own anatomy facts
(brand-/palette-agnostic), so multi-column module geometry survives.

These tests pin the inference so a future refactor cannot silently reintroduce the
collapse, and guard that sections using a DRAWABLE archetype are byte-identical (no
re-routing → zero cross-brand regression).

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_composer_multicolumn
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))
_REPO = _BRAND_PIPELINE.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import compose_from_composition as cfc  # noqa: E402


def _card_section(archetype, use_case, n=3):
    items = [{"heading": f"Feature {i}", "text": f"Body copy {i}", "link": "Learn more"}
             for i in range(n)]
    return {
        "id": "feat", "archetype": archetype, "useCase": use_case,
        "_requiresHydration": True,
        "slots": [
            {"name": "heading", "role": "section-heading", "contract": "heading",
             "copy": {"heading": "Section heading"}},
            # a media WELL whose ROLE merely contains the word "card" must NOT be
            # mistaken for the module collection.
            {"name": "itemMedia", "role": "card-media-well", "contract": "image"},
            {"name": "items", "role": "feature-card-list", "contract": "card",
             "copy": items},
        ],
    }


class InferDrawableArchetype(unittest.TestCase):
    def test_card_collection_under_descriptive_archetype_routes_to_cards(self):
        layout = cfc.composition_to_layout(
            _card_section("three-column-media-top-cards", "feature grid"))
        self.assertEqual(layout["archetype"], "cards")

    def test_inferred_cards_get_a_multi_column_default(self):
        layout = cfc.composition_to_layout(
            _card_section("three-column-media-top-cards", "feature grid", n=3))
        grid = layout.get("_grid") or {}
        self.assertEqual(grid.get("source"), "inferred")
        self.assertEqual(grid.get("columns"), 3)      # declared "three-column"
        self.assertEqual(layout.get("_moduleCols"), 3)

    def test_column_default_never_exceeds_item_count(self):
        # only 2 authored modules under a "three-column" label → 2 columns, not 3.
        layout = cfc.composition_to_layout(
            _card_section("three-column-quote-blocks", "testimonial row", n=2))
        self.assertEqual((layout.get("_grid") or {}).get("columns"), 2)

    def test_module_slot_is_the_real_collection_not_a_media_role(self):
        # regression for the empty-grid bug: _cards_copy must build cards from the
        # `card`-contract collection, not the media well whose role says "card".
        copy = cfc._cards_copy(_card_section("x-cards", "feature grid", n=3))
        self.assertEqual(len(copy.get("cards") or []), 3)

    def test_comparison_vocabulary_with_media_routes_to_split(self):
        section = {
            "id": "cmp", "archetype": "pill-filtered-comparison-card",
            "useCase": "comparison of two columns with a media panel",
            "slots": [
                {"name": "heading", "role": "section-heading", "contract": "heading",
                 "copy": {"heading": "How we compare"}},
                {"name": "rows", "role": "comparison-list", "contract": "list",
                 "copy": [{"label": "Row A", "title": "Row A", "text": ""},
                          {"label": "Row B", "title": "Row B", "text": ""}]},
                {"name": "media", "role": "decorative-media-well", "contract": "image",
                 "mediaAspect": "portrait"},
            ],
        }
        self.assertEqual(cfc.composition_to_layout(section)["archetype"], "split")

    def test_numeric_list_does_not_invent_stats_without_brand_license(self):
        section = {
            "id": "stats", "archetype": "three-column-number-over-caption",
            "useCase": "big number over caption columns",
            "slots": [{"name": "items", "role": "stat-column-list", "contract": "list",
                       "copy": [{"label": "25%", "title": "25%", "text": "Reduction"},
                                {"label": "39%", "title": "39%", "text": "Lower spend"},
                                {"label": "92%", "title": "92%", "text": "Fewer firms"}]}],
        }
        layout = cfc.composition_to_layout(section)
        self.assertEqual(layout["archetype"], "generic-flow")
        contracts = [m.get("contract") for m in layout.get("blockMapping") or []]
        self.assertNotIn("stat", contracts)

    def test_brand_licensed_numeric_list_maps_to_stat_band(self):
        section = {
            "id": "stats", "archetype": "three-column-number-over-caption",
            "useCase": "big number over caption columns",
            "proofRequired": True,
            "slots": [{"name": "items", "role": "stat-column-list", "contract": "list",
                       "copy": [{"label": "25%", "title": "25%", "text": "Reduction"},
                                {"label": "39%", "title": "39%", "text": "Lower spend"},
                                {"label": "92%", "title": "92%", "text": "Fewer firms"}]}],
        }
        layout = cfc.composition_to_layout(section)
        contracts = [m.get("contract") for m in layout.get("blockMapping") or []]
        self.assertIn("stat", contracts)
        self.assertNotIn("caption", contracts)

    def test_hero_declaring_floating_media_routes_to_the_collage_family(self):
        """A hero whose declared label states LAYERED media is drawn as a collage,
        not a single-track stack (fid16 2026-07).

        The declared structure is a measured fact about the source band, so
        honouring it preserves evidence. Layered media is deliberately NOT a
        column split: the media does not occupy a track of its own, so a
        two-column shell would squeeze copy that ran at full measure.
        """
        section = {
            "id": "hero", "archetype": "centered-copy-with-floating-media",
            "useCase": "Full-bleed opening hero: centered copy with floating media",
            "slots": [
                {"name": "heading", "role": "primary-heading", "contract": "heading",
                 "copy": {"heading": "The only platform"}},
                {"name": "cta", "role": "primary-action", "contract": "button",
                 "copy": {"label": "Get started"}},
                {"name": "art", "role": "decorative-media", "contract": "image",
                 "mediaAspect": "portrait"},
            ],
        }
        layout = cfc.composition_to_layout(section)
        self.assertEqual(layout["archetype"], "collage")
        # the hero path (not the conversion stack) owns the mapping — it attaches the
        # hero SECTION_COPY payload the hero composers read.
        self.assertIn("_sectionCopy", layout)
        # provenance keeps the DECLARED label, not the normalized "stack".
        self.assertEqual(layout["_composition"]["archetype"],
                         "centered-copy-with-floating-media")


class NoRegressionForDrawableArchetypes(unittest.TestCase):
    def test_stack_with_cards_still_degrades_to_generic_flow(self):
        # a DRAWABLE archetype is never re-routed by the inference — a plain `stack`
        # carrying a card collection keeps its historical generic-flow degrade, so
        # brands using drawable archetypes are byte-identical.
        section = {
            "id": "about", "archetype": "stack", "useCase": "about",
            "slots": [
                {"name": "heading", "role": "heading", "contract": "heading",
                 "copy": {"heading": "About"}},
                {"name": "items", "role": "cards", "contract": "card",
                 "copy": [{"heading": "A", "text": "a"}, {"heading": "B", "text": "b"}]},
            ],
        }
        self.assertEqual(cfc.composition_to_layout(section)["archetype"], "generic-flow")

    def test_explicit_cards_archetype_untouched(self):
        section = {
            "id": "wf", "archetype": "cards", "useCase": "workflow cards",
            "slots": [{"name": "items", "role": "cards", "contract": "card",
                       "copy": [{"heading": "A", "text": "a"},
                                {"heading": "B", "text": "b"}]}],
        }
        self.assertEqual(cfc.composition_to_layout(section)["archetype"], "cards")


class QuoteCardShaping(unittest.TestCase):
    def test_quote_context_yields_attribution_without_media(self):
        section = {
            "id": "t", "archetype": "three-column-quote-blocks",
            "useCase": "quote blocks with attribution",
            "slots": [
                {"name": "heading", "role": "section-heading", "contract": "heading",
                 "copy": {"heading": "What customers say"}},
                {"name": "items", "role": "testimonial-card-list", "contract": "card",
                 "copy": [{"heading": "Maciek K.", "text": "Great tool."},
                          {"heading": "Verified user", "text": "Very useful."}]},
            ],
        }
        cards = cfc._cards_copy(section)["cards"]
        self.assertEqual(len(cards), 2)
        for c in cards:
            self.assertTrue(c.get("name"))          # attribution rides the person row
            self.assertFalse(c.get("asset"))        # no backfilled media well
            self.assertFalse(c.get("caption"))      # not a feature caption


class Helpers(unittest.TestCase):
    def test_declared_column_count(self):
        self.assertEqual(cfc._declared_column_count("three-column-media-top-cards"), 3)
        self.assertEqual(cfc._declared_column_count("a 3-up card row"), 3)
        self.assertEqual(cfc._declared_column_count("two column split"), 2)
        self.assertEqual(cfc._declared_column_count("no columns here"), 0)

    def test_is_stat_figure(self):
        for ok in ("25%", "1,600+", "3x", "92", "$4M", "170+"):
            self.assertTrue(cfc._is_stat_figure(ok), ok)
        for no in ("Greenhouse", "G2 98% customer satisfaction rating", "", "Real Talent"):
            self.assertFalse(cfc._is_stat_figure(no), no)


if __name__ == "__main__":
    unittest.main()
