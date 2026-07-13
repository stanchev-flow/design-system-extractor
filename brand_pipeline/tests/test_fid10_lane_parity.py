#!/usr/bin/env python3
"""Fixture tests for the fid10 pass (2026-07): composed-from-catalog lane parity.

  1. SHARED LANE ADAPTATION — ``compose_from_composition.adapt_brand_section`` is THE
     one brand-aware adaptation path: authored layoutCopy overlays the composition's
     translator copy (authored voice heals lossy slot translations), and brand-layout
     declarations the composition vocabulary doesn't model (``eyebrowRegister``) ride
     onto the adapted layout. The catalog lane (``composition_to_doc``) must emit the
     SAME adapted layout + LAYOUT_COPY entry as calling the helper directly (the
     replica lane's path) — the catalog lane previously skipped the authored merge and
     dropped the eyebrow register, so the composed page lost authored headings/
     subheads and per-section eyebrow colors.
  2. STAMP PARITY — both lanes' adapted layouts stamp identical pattern-fact hints
     (_accGeometry / _stackMeasure / _bandPadding / alignment resolution inputs) since
     the stamps derive from the SAME patternRef the adapter carries.
  3. CONTAINER LAW — every major section container (generic flow, split, conversion
     panel, page footer content) rides the ONE shared content measure and centers;
     --content-measure prefers the brand's measured container-span law token.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fid10_lane_parity
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import compose_from_composition as cfc  # noqa: E402
import compose_page as cp               # noqa: E402
import compose_section as cs            # noqa: E402
import layout_library as ll             # noqa: E402


BRAND_YAML = """\
brand: { name: Fixture }
tokens:
  colors:
    text/on-primary: { value: "#111111" }
  surfaces:
    surface/primary: { bg: "#ffffff", textPrimary: text/on-primary }
  type:
    body: { family: Inter, sizeRem: { base: 1.0 } }
  spacing: {}
layouts:
  - id: sec-x
    archetype: cards
    surfaceMode: light
    useCase: features
    eyebrowRegister: muted
    patternRef: { lib: project, id: pat-x }
    slots: []
"""

SECTION_COPY_YAML = """\
layoutCopy:
  sec-x:
    heading: "Authored heading"
    subhead: "Authored subhead"
"""

# a composition section as generate_composition emits it: seeded from the same
# pattern, copy present only where the composition "speaks" (no heading/subhead).
COMP_SECTION = {
    "id": "sec-x",
    "useCase": "features",
    "archetype": "cards",
    "surfaceIntent": "primary",
    "novelty": "reuse",
    "seededFrom": {"lib": "project", "id": "pat-x"},
    "slots": [
        {"name": "heading", "role": "heading — section header stack",
         "contract": "eyebrow", "copy": {"eyebrow": "COMP EYEBROW"}},
        {"name": "cards", "role": "cards — feature modules", "contract": "card",
         "copy": [{"heading": "Card A", "text": "Body A."},
                  {"heading": "Card B", "text": "Body B."}]},
    ],
}


def _brand_dir() -> tempfile.TemporaryDirectory:
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    (root / "brand.yaml").write_text(BRAND_YAML)
    (root / "section-copy.yaml").write_text(SECTION_COPY_YAML)
    return td


def _doc_for(root: Path) -> dict:
    import yaml
    doc = yaml.safe_load((root / "brand.yaml").read_text())
    cs.attach_brand_copy(doc, root)
    return doc


class AdaptBrandSectionTest(unittest.TestCase):
    """The shared helper: authored overlay + declaration ride-through."""

    def test_authored_copy_overlays_translator_copy(self):
        with _brand_dir() as td:
            doc = _doc_for(Path(td))
            layout, merged, sect_copy = cfc.adapt_brand_section(
                json.loads(json.dumps(COMP_SECTION)), doc)
        self.assertEqual(merged.get("heading"), "Authored heading")
        self.assertEqual(merged.get("subhead"), "Authored subhead")
        # keys the authored layer doesn't declare keep the composition's voice
        self.assertEqual(merged.get("eyebrow"), "COMP EYEBROW")
        self.assertIsNone(sect_copy)  # not a hero

    def test_brand_layout_declarations_ride_through(self):
        with _brand_dir() as td:
            doc = _doc_for(Path(td))
            layout, _, _ = cfc.adapt_brand_section(
                json.loads(json.dumps(COMP_SECTION)), doc)
        self.assertEqual(layout.get("eyebrowRegister"), "muted")
        self.assertEqual(layout.get("patternRef"), {"lib": "project", "id": "pat-x"})

    def test_unmatched_section_id_keeps_composition_copy_only(self):
        sec = {**json.loads(json.dumps(COMP_SECTION)), "id": "novel-section"}
        with _brand_dir() as td:
            doc = _doc_for(Path(td))
            layout, merged, _ = cfc.adapt_brand_section(sec, doc)
        # no authored leak: the translator's own (empty) heading stands untouched
        self.assertEqual(merged.get("heading"), "")
        self.assertEqual(merged.get("eyebrow"), "COMP EYEBROW")
        self.assertNotIn("eyebrowRegister", layout)  # no brand layout to ride from


class LaneParityTest(unittest.TestCase):
    """The catalog lane (composition_to_doc) emits the SAME adapted layout and
    LAYOUT_COPY entry as the direct helper call (the replica lane's path)."""

    def test_catalog_path_matches_direct_path(self):
        with _brand_dir() as td:
            root = Path(td)
            # direct (replica-style) path
            direct_doc = _doc_for(root)
            direct_layout, direct_copy, _ = cfc.adapt_brand_section(
                json.loads(json.dumps(COMP_SECTION)), direct_doc)
            # catalog path
            doc, order = cfc.composition_to_doc(
                {"schemaVersion": "composition.v1",
                 "sections": [json.loads(json.dumps(COMP_SECTION))]},
                root / "brand.yaml")
        self.assertEqual(order, ["sec-x"])
        catalog_layout = doc["layouts"][0]
        catalog_copy = doc["_hybridCopy"]["layout_copy"]["sec-x"]
        self.assertEqual(catalog_layout, direct_layout)
        self.assertEqual(catalog_copy, direct_copy)

    def test_stamp_parity_for_every_fact_class(self):
        """Both lanes' adapted layouts produce IDENTICAL pattern-fact stamps for
        every stamped fact class (the stamps read the pattern via patternRef —
        equal layouts must yield equal stamps)."""
        content_shape = {
            "alignment": {"value": "center", "inheritance": "block-inherits"},
            "stackMeasure": {"value": "54.375rem", "source": "computed"},
            "bandPadding": {"top": "4rem", "bottom": "4rem", "source": "computed"},
            "deviceGeometry": {
                "source": "computed", "headerPlacement": "list-column",
                "columns": "equal", "contentSpan": "73rem",
                "columnGap": "6.3125rem", "rowGap": "4rem",
                "media": {"aspect": "1 / 1", "align": "top", "fit": "contain"},
                "list": {"triggerMinHeight": "5rem", "itemGap": "1rem"},
            },
        }
        pattern = ll.Pattern(
            id="pat-x", use_case="features", archetype_ref="split",
            surface_intent="any", intent="test", content_shape=content_shape,
            special_treatments=[], responsive={}, variant_knobs={},
            origin="extracted", confidence="high", scope="design-language",
            provenance=[])
        with _brand_dir() as td:
            root = Path(td)
            direct_doc = _doc_for(root)
            direct_layout, _, _ = cfc.adapt_brand_section(
                json.loads(json.dumps(COMP_SECTION)), direct_doc)
            doc, _ = cfc.composition_to_doc(
                {"schemaVersion": "composition.v1",
                 "sections": [json.loads(json.dumps(COMP_SECTION))]},
                root / "brand.yaml")
            catalog_layout = doc["layouts"][0]
            stamps = {}
            for name, layout in (("direct", dict(direct_layout)),
                                 ("catalog", dict(catalog_layout))):
                with mock.patch.object(cs, "resolve_pattern",
                                       return_value=(pattern, "project")):
                    cs.stamp_pattern_devices(direct_doc, layout, root / "brand.yaml")
                stamps[name] = {k: v for k, v in layout.items()
                                if k.startswith("_") and k != "_composition"}
        self.assertEqual(stamps["direct"], stamps["catalog"])
        # every fact class the lanes carry must actually be present (not vacuous)
        for fact in ("_stackMeasure", "_bandPadding", "_accGeometry"):
            self.assertIn(fact, stamps["catalog"],
                          f"{fact} missing from the catalog lane's stamps")
        # the full geometry fact set survives the stamp, letterbox fit included
        self.assertTrue(stamps["catalog"]["_accGeometry"].get("mediaContain"),
                        "media fit: contain did not stamp as mediaContain")


class ContainerLawTest(unittest.TestCase):
    """One shared content measure, centered, on every major section container."""

    def test_flow_split_and_panel_ride_the_shared_measure(self):
        # fix3: containment moved from per-device declarations to the ONE shared
        # CONTAINMENT LAW rule — membership is the contract now (the law rule
        # itself carries the cap + centering; see test_fix3_containment_alignment).
        for cls in (".cs-flow", ".cs-split", ".cs-conversion-panel"):
            self.assertIn(cls, cs.CONTAINED_DEVICES,
                          f"{cls} escaped the containment law")
        self.assertIn("max-width: var(--content-measure, 86rem);"
                      " margin-inline: auto;", cs.CONTAINMENT_LAW_CSS)

    def test_page_footer_content_rides_the_shared_measure(self):
        css = cp.page_scaffold_css()
        self.assertIn(".cs-footer-sec > .c-footer", css)
        rule = css[css.index(".cs-footer-sec > .c-footer"):]
        rule = rule[:rule.index("}")]
        self.assertIn("max-width: var(--content-measure", rule)
        self.assertIn("margin-inline: auto", rule)

    def test_content_measure_prefers_measured_span_law(self):
        doc = {"brand": {"name": "F"},
               "tokens": {"colors": {"text/on-primary": {"value": "#111111"}},
                          "surfaces": {"surface/primary": {
                              "bg": "#ffffff", "textPrimary": "text/on-primary"}},
                          "type": {"body": {"family": "Inter",
                                            "sizeRem": {"base": 1.0}}},
                          "spacing": {}}}
        block = cs.root_vars(doc, doc["tokens"]["surfaces"]["surface/primary"],
                             display_size="4rem", title_overlap="-2.75rem",
                             surface_role="surface/primary")
        self.assertIn("--content-measure: var(--space-container-span, "
                      "var(--space-container-max, 86rem))", block)


if __name__ == "__main__":
    unittest.main()
