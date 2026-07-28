#!/usr/bin/env python3
"""Regression tests for the replica CENSUS + STRUCTURAL GATE (fid16 2026-07).

Four failures this locks down, all of which previously produced a
plausible-looking score instead of a visible failure:

  1. the scoring pair list ignoring the page filter, so a multi-page brand
     scored source bands against sections that were never composed;
  2. a composed/scoring census divergence passing silently;
  3. a section's ``surfaceIntent`` derived from a nested component surface
     rather than the section's own page-parented ground;
  4. a measured multi-track band composed into a single-track family, and a
     collapsed content span — neither of which an averaged-MAE score can see.

Synthetic fixtures only: no brand data, no Playwright, no network.

Run:  ./venv/bin/python -m unittest \
          brand_pipeline.tests.test_fid16_replica_census_gate
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
for _p in (_REPO / "brand_pipeline", _REPO / "tools" / "extract"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import compose_replica as cx                  # noqa: E402
import project_sections_to_patterns as proj   # noqa: E402


def _doc(layout_ids):
    return {"layouts": [{"id": i, "archetype": "stack",
                         "patternRef": {"id": f"pat-{i}"}} for i in layout_ids]
            + [{"id": "navbar", "archetype": "nav"},
               {"id": "footer", "archetype": "grid"}]}


# ── 1) the page-filtered scoring pair list ────────────────────────────────────────

class PageFilteredPairListTests(unittest.TestCase):
    """The pair list that drives SCORING must accept the same page filter that
    drives COMPOSITION, or band i is compared against an unrelated section."""

    def setUp(self):
        self.doc = _doc(["opener", "band-a", "band-b", "closer"])
        self.patterns = [
            {"id": "pat-opener", "provenance": ["opener"],
             "sourcePages": ["page-one"]},
            {"id": "pat-band-a", "provenance": ["band-a"],
             "sourcePages": ["page-one"]},
            {"id": "pat-band-b", "provenance": ["band-b"],
             "sourcePages": ["page-two"]},
            {"id": "pat-closer", "provenance": ["closer"],
             "sourcePages": ["page-two"]},
        ]

    def test_pair_list_accepts_a_page_filter(self):
        pairs = cx.source_order_sections(self.doc, self.patterns, page="page-one")
        self.assertEqual([l["id"] for l, _ in pairs], ["opener", "band-a"])

    def test_unfiltered_list_keeps_off_page_sections(self):
        # the pre-fix behaviour, kept as the contrast the guard below catches
        pairs = cx.source_order_sections(self.doc, self.patterns)
        self.assertEqual(len(pairs), 4)


# ── 2) the count-divergence guard ────────────────────────────────────────────────

class PairingCensusGuardTests(unittest.TestCase):
    def _pairs(self, ids):
        return [({"id": i}, {"id": f"pat-{i}"}) for i in ids]

    def test_identical_census_passes(self):
        cx.assert_pairing_census(["a", "b"], self._pairs(["a", "b"]))

    def test_count_divergence_raises(self):
        with self.assertRaises(cx.PairingCensusError) as ctx:
            cx.assert_pairing_census(["a", "b"], self._pairs(["a", "b", "c"]))
        self.assertIn("COUNT DIVERGENCE", str(ctx.exception))

    def test_equal_length_but_different_identity_raises(self):
        """The dangerous case: same cardinality, different membership. A
        cardinality-only check would pass this and score every band against the
        wrong section."""
        with self.assertRaises(cx.PairingCensusError) as ctx:
            cx.assert_pairing_census(["a", "b"], self._pairs(["a", "z"]))
        msg = str(ctx.exception)
        self.assertIn("scored but never composed", msg)
        self.assertIn("composed but never scored", msg)

    def test_order_divergence_raises(self):
        with self.assertRaises(cx.PairingCensusError):
            cx.assert_pairing_census(["a", "b"], self._pairs(["b", "a"]))


# ── 3) the section-ground surface rule ───────────────────────────────────────────

class SectionGroundSurfaceTests(unittest.TestCase):
    """A section's own ground is its page-parented canvas; a nested surface of
    any contrast is a COMPONENT-level variant, never the section's ground."""

    def test_nested_inverse_panel_does_not_become_the_section_ground(self):
        surfaces = [
            {"role": "canvas", "bgApprox": "#ffffff", "parent": "page"},
            {"role": "band", "bgApprox": "#101010", "parent": "card"},
        ]
        ground = proj.section_ground_surface(surfaces)
        self.assertEqual(ground.get("bgApprox"), "#ffffff")

    def test_rule_is_polarity_agnostic(self):
        """The same rule must hold when the page ground is the DARK one and the
        nested panel is the light one — the rule is about parentage and role
        authority, not about which side is darker."""
        surfaces = [
            {"role": "canvas", "bgApprox": "#101010", "parent": "page"},
            {"role": "band", "bgApprox": "#ffffff", "parent": "card"},
        ]
        ground = proj.section_ground_surface(surfaces)
        self.assertEqual(ground.get("bgApprox"), "#101010")

    def test_page_parented_band_wins_over_a_nested_canvas(self):
        surfaces = [
            {"role": "canvas", "bgApprox": "#ffffff", "parent": "panel"},
            {"role": "band", "bgApprox": "#202020", "parent": "page"},
        ]
        ground = proj.section_ground_surface(surfaces)
        self.assertEqual(ground.get("bgApprox"), "#202020")

    def test_authored_intent_is_only_rewritten_on_a_real_contradiction(self):
        """A richer authored variant survives; only an intent that paints against
        the measured ground's polarity is a contradiction."""
        # authored says the band inverts the page ground, the measured ground
        # sits WITH it → contradiction
        self.assertTrue(proj.surface_intent_contradicts(
            "surface/inverse", "surface/primary"))
        # a richer non-inverting variant is not contradicted by a non-inverting
        # derivation, so a reconcile must leave it alone
        self.assertFalse(proj.surface_intent_contradicts(
            "surface/muted", "surface/primary"))

    def test_derivation_reads_the_page_ground_not_the_nested_panel(self):
        """End to end, and stated twice with the polarity reversed so the rule is
        demonstrably about PARENTAGE, not about which side is darker.

        A section whose page-parented ground sits WITH the brand's prevailing
        ground is not inverting, however dark or light that ground happens to be
        — even when it contains a nested panel of the opposite polarity.
        """
        # brand whose prevailing ground carries dark ink on light (polarity -1)
        section_on_light = [
            {"role": "canvas", "bgApprox": "#ffffff", "inkApprox": "#101010",
             "parent": "page"},
            {"role": "band", "bgApprox": "#101010", "inkApprox": "#ffffff",
             "parent": "card"},
        ]
        self.assertNotIn(
            proj.derive_surface_intent(section_on_light, dominant=-1),
            proj.INVERTING_INTENTS)

        # mirror brand: prevailing ground carries light ink on dark (polarity +1)
        section_on_dark = [
            {"role": "canvas", "bgApprox": "#101010", "inkApprox": "#ffffff",
             "parent": "page"},
            {"role": "band", "bgApprox": "#ffffff", "inkApprox": "#101010",
             "parent": "card"},
        ]
        self.assertNotIn(
            proj.derive_surface_intent(section_on_dark, dominant=1),
            proj.INVERTING_INTENTS)

        # and a section that really does paint against the prevailing ground
        # still reads as inverting
        against = [{"role": "canvas", "bgApprox": "#101010",
                    "inkApprox": "#ffffff", "parent": "page"}]
        self.assertIn(proj.derive_surface_intent(against, dominant=-1),
                      proj.INVERTING_INTENTS)


# ── 4) the structural gate signals ───────────────────────────────────────────────

def _row(bid, *, width=1.0, height=100, unauthored=False, scored=True):
    return {"id": bid, "widthFidelity": width, "srcHeight": height,
            "scored": scored, "unauthored": unauthored, "score": 0.9,
            "structure": 0.9, "pixel": 0.9, "height": 0.9}


def _pair(lid, columns=None, slots=()):
    return ({"id": lid, "archetype": "stack"},
            {"id": f"pat-{lid}", "layout": ({"columns": columns} if columns
                                            else {}),
             "slots": list(slots)})


class StructuralGateTests(unittest.TestCase):
    def test_all_signals_pass_on_a_faithful_rebuild(self):
        rows = [_row("sec-0"), _row("sec-1"), _row("footer")]
        pairs = [_pair("a", 1), _pair("b", 2, [{"contract": "media"}])]
        gate = cx.structural_gate(
            rows, {"sectionOrdinals": [0, 1]},
            {"a": "stack", "b": "split"}, pairs)
        self.assertTrue(gate["ok"], gate["blocking"])
        self.assertEqual(gate["signals"]["bandCountAgreement"]["value"], 1.0)
        self.assertEqual(gate["signals"]["archetypeFamilyAgreement"]["value"], 1.0)

    def test_band_count_catches_a_measured_band_nobody_authored(self):
        rows = [_row("sec-0"), _row("sec-1", unauthored=True)]
        gate = cx.structural_gate(rows, {"sectionOrdinals": [0]},
                                  {"a": "stack"}, [_pair("a", 1)])
        sig = gate["signals"]["bandCountAgreement"]
        self.assertFalse(sig["ok"])
        self.assertEqual(sig["unauthoredBands"], ["sec-1"])
        self.assertFalse(gate["ok"])

    def test_band_count_catches_an_authored_section_no_band_anchors(self):
        rows = [_row("sec-0")]
        gate = cx.structural_gate(rows, {"sectionOrdinals": [0, None]},
                                  {"a": "stack", "b": "stack"},
                                  [_pair("a", 1), _pair("b", 1)])
        sig = gate["signals"]["bandCountAgreement"]
        self.assertFalse(sig["ok"])
        self.assertEqual(sig["unpairedSections"], ["b"])

    def test_family_agreement_catches_a_multi_track_band_drawn_single_track(self):
        rows = [_row("sec-0")]
        pairs = [_pair("a", 2, [{"contract": "media"}])]
        gate = cx.structural_gate(rows, {"sectionOrdinals": [0]},
                                  {"a": "generic-flow"}, pairs)
        sig = gate["signals"]["archetypeFamilyAgreement"]
        self.assertFalse(sig["ok"])
        self.assertEqual(sig["value"], 0.0)
        self.assertIn("measured 2 track(s)", sig["mismatches"][0])

    def test_family_mismatch_without_a_counterweight_names_the_real_cause(self):
        """A section with nothing to put in a second track cannot be ROUTED into
        one; the divergence is that projection dropped the band's secondary
        occupant, and the message must say so rather than blame routing."""
        rows = [_row("sec-0")]
        pairs = [_pair("a", 2, [{"contract": "heading"}, {"contract": "button"}])]
        gate = cx.structural_gate(rows, {"sectionOrdinals": [0]},
                                  {"a": "generic-flow"}, pairs)
        note = gate["signals"]["archetypeFamilyAgreement"]["mismatches"][0]
        self.assertIn("no slot able to occupy the secondary track", note)

    def test_family_agreement_accepts_a_multi_track_family_for_a_split_band(self):
        rows = [_row("sec-0")]
        pairs = [_pair("a", 2, [{"contract": "media"}])]
        for fam in ("split", "media-split", "cards", "interlock", "collage"):
            gate = cx.structural_gate(rows, {"sectionOrdinals": [0]},
                                      {"a": fam}, pairs)
            self.assertTrue(
                gate["signals"]["archetypeFamilyAgreement"]["ok"], fam)

    def test_unmeasured_track_count_is_not_counted_either_way(self):
        rows = [_row("sec-0")]
        gate = cx.structural_gate(rows, {"sectionOrdinals": [0]},
                                  {"a": "generic-flow"}, [_pair("a")])
        sig = gate["signals"]["archetypeFamilyAgreement"]
        self.assertEqual(sig["checked"], 0)
        self.assertEqual(sig["unmeasured"], ["a"])
        self.assertTrue(sig["ok"])

    def test_content_span_is_height_weighted_so_a_tall_collapse_shows(self):
        rows = [_row("sec-0", width=1.0, height=100),
                _row("sec-1", width=0.3, height=900)]
        gate = cx.structural_gate(rows, {"sectionOrdinals": [0, 1]},
                                  {"a": "stack", "b": "stack"},
                                  [_pair("a", 1), _pair("b", 1)])
        sig = gate["signals"]["contentSpanFidelity"]
        self.assertFalse(sig["ok"])
        self.assertLess(sig["value"], 0.5)

    def test_excluded_and_chrome_bands_do_not_enter_the_signals(self):
        rows = [_row("page-nav", width=0.0, scored=False), _row("sec-0")]
        gate = cx.structural_gate(rows, {"sectionOrdinals": [0]},
                                  {"a": "stack"}, [_pair("a", 1)])
        self.assertTrue(gate["ok"], gate["blocking"])


class ContentSpanMeasureTests(unittest.TestCase):
    """``_content_span`` feeds a gate signal, so a sparse-but-occupied band must
    not read as empty."""

    def _band(self, w, h, bg, marks):
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (w, h), bg)
        d = ImageDraw.Draw(im)
        for box in marks:
            d.rectangle(box, fill=(255, 255, 255) if sum(bg) < 380
                              else (0, 0, 0))
        return im

    def test_a_short_centered_stack_in_a_tall_band_is_not_empty(self):
        # content on ~4% of the band height: a column-mean test averages it away
        im = self._band(1440, 900, (20, 24, 22), [(500, 420, 940, 460)])
        span = cx._content_span(im)
        self.assertGreater(span, 0.2)

    def test_a_uniform_band_still_reads_empty(self):
        im = self._band(1440, 400, (240, 240, 240), [])
        self.assertEqual(cx._content_span(im), 0.0)

    def test_span_tracks_the_occupied_width(self):
        narrow = self._band(1440, 600, (255, 255, 255), [(620, 280, 820, 320)])
        wide = self._band(1440, 600, (255, 255, 255), [(120, 280, 1320, 320)])
        self.assertLess(cx._content_span(narrow), cx._content_span(wide))


# ── 5) archetype routing for declared two-column intents ─────────────────────────

class DeclaredStructuralRoutingTests(unittest.TestCase):
    """A section whose DECLARED archetype states its structure must be drawn with
    that structure, even though it also carries brand anatomy. Before this,
    every projected pattern short-circuited the inference and landed in the
    single-column safety net."""

    def setUp(self):
        import compose_from_composition as cfc
        self.cfc = cfc

    def _route(self, archetype, slots, use_case="section"):
        return self.cfc._declared_structural_archetype(
            archetype, {"useCase": use_case}, slots)

    def test_declared_split_with_a_media_counterweight_routes_to_split(self):
        self.assertEqual(
            self._route("split-copy-left-media-right",
                        [{"contract": "heading"}, {"contract": "image"}]),
            "split")

    def test_declared_split_with_a_logo_collection_routes_to_split(self):
        self.assertEqual(
            self._route("split-copy-plus-logo-grid",
                        [{"contract": "heading"},
                         {"contract": "logo", "copy": ["a", "b", "c"]}]),
            "split")

    def test_declared_side_placement_with_a_list_counterweight_routes_to_split(self):
        self.assertEqual(
            self._route("full-bleed-band-copy-left-table-right",
                        [{"contract": "heading"}, {"contract": "table"}]),
            "split")

    def test_floating_media_reads_as_a_collage_not_a_column_split(self):
        """Layered media does not occupy a track of its own, so a two-column
        shell would squeeze copy the source ran at full measure."""
        self.assertEqual(
            self._route("centered-copy-with-floating-media",
                        [{"contract": "heading"}, {"contract": "image"}]),
            "collage")

    def test_no_counterweight_declares_no_structure(self):
        """Nothing to place in a second track ⇒ no structural claim to honour.
        The renderer must not open a track it cannot fill; the divergence is
        reported by the structural gate instead."""
        self.assertIsNone(
            self._route("full-bleed-band-copy-left-art-right",
                        [{"contract": "heading"}, {"contract": "button"}]))

    def test_a_label_with_no_structural_vocabulary_declares_nothing(self):
        self.assertIsNone(
            self._route("editorial-statement",
                        [{"contract": "heading"}, {"contract": "image"}]))


# ── 6) the validator rows ────────────────────────────────────────────────────────

class ValidatorRowTests(unittest.TestCase):
    def setUp(self):
        import validate_brand_evidence as vbe
        self.mod = vbe
        self.rep = None

    def _check(self, brand_dir: Path):
        self.rep = self.mod.Report(brand_dir)
        self.mod._check_structural_gate(self.rep, brand_dir)
        return self.rep

    def _write_report(self, tmp: Path, gate) -> Path:
        import json
        d = tmp / "compose" / "replica"
        d.mkdir(parents=True)
        payload = {"overall": 0.99, "bands": []}
        if gate is not None:
            payload["structuralGate"] = gate
        (d / "replica-report.json").write_text(json.dumps(payload))
        return tmp

    def test_structural_divergence_is_an_error_even_at_a_high_score(self):
        """The point of the row: a rebuild can clear the similarity bar and still
        be the wrong comparison."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            brand = self._write_report(Path(td), {
                "ok": False,
                "signals": {"bandCountAgreement": {"value": 0.8, "floor": 1.0,
                                                   "ok": False}},
                "blocking": ["bandCountAgreement: 0.8 < floor 1.0 (…)"]})
            rep = self._check(brand)
        self.assertFalse(rep.ok)

    def test_a_faithful_gate_does_not_block(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            brand = self._write_report(Path(td), {
                "ok": True,
                "signals": {"bandCountAgreement": {"value": 1.0, "floor": 1.0,
                                                   "ok": True}},
                "blocking": []})
            rep = self._check(brand)
        self.assertTrue(rep.ok)

    def test_a_report_predating_the_gate_is_a_note_not_a_failure(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            brand = self._write_report(Path(td), None)
            rep = self._check(brand)
        self.assertTrue(rep.ok)

    def test_no_replica_yet_is_silent(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            rep = self._check(Path(td))
        self.assertTrue(rep.ok)


if __name__ == "__main__":
    unittest.main()
