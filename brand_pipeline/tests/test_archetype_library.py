"""Archetype library (phase-2 wiring) — loader, selection, skeleton application,
prompt injection, bandHeight knob, and the fail-closed demotion posture.

Law under test (spec/archetype-library.md): style-invariant / structure-variable /
physics-hard; the library is DATA (no archetype id in shared code); everything is
fact-gated so lanes without ``archetypeRef`` stay byte-identical.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import archetype_library as al            # noqa: E402
import compose_from_composition as cfc    # noqa: E402
import compose_section as cs              # noqa: E402
import generate_composition as gc         # noqa: E402

REPO = HERE.parent
HUBSPOT = REPO / "runs" / "hubspot-v2" / "brand" / "brand.yaml"

CORE_FAMILIES = {"containment", "headingTier", "headerContext",
                 "relationalRhythm", "surfaceContrast"}
KNOWN_FAMILIES = CORE_FAMILIES | {"actionGroup", "stackMeasure", "textOnMedia",
                                  "gridEqualize", "controlMeasure", "assetFidelity",
                                  "interaction", "motion"}
ATOMIC_CONTRACTS = {"eyebrow", "heading", "paragraph", "button", "badge",
                    "label", "link", "image", "video"}


def _hubspot_doc():
    return yaml.safe_load(HUBSPOT.read_text())


class LibraryShape(unittest.TestCase):
    """The genre YAML is valid data for the loader's generic consumption."""

    @classmethod
    def setUpClass(cls):
        cls.doc = al.load_genre("heroes-saas")
        cls.arts = cls.doc["archetypes"]

    def test_schema_version_and_unique_ids(self):
        self.assertEqual(self.doc["schemaVersion"], al.SCHEMA_VERSION)
        ids = [a["id"] for a in self.arts]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 20)

    def test_core_physics_on_every_entry_and_known_families_only(self):
        for a in self.arts:
            fams = set(al.physics_checklist(a))
            self.assertTrue(CORE_FAMILIES <= fams, a["id"])
            self.assertFalse(fams - KNOWN_FAMILIES, a["id"])

    def test_structure_vocabulary_resolves(self):
        scaffolds = yaml.safe_load(
            (HERE / "contracts" / "scaffolds.yaml").read_text())
        blocks = set((yaml.safe_load(
            (HERE / "contracts" / "blocks.yaml").read_text()).get("blocks") or {}))
        scaffold_keys = set()

        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    scaffold_keys.add(str(k))
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(scaffolds)
        drawable = {"stack", "split", "stack-fullbleed", "cards", "collage",
                    "interlock", "overlay", "banded"}
        for a in self.arts:
            st = a["structure"]
            self.assertIn(st["archetype"], drawable, a["id"])
            if st.get("scaffoldRef"):
                self.assertIn(st["scaffoldRef"], scaffold_keys, a["id"])
            for s in a["anatomy"]["slots"]:
                self.assertIn(s["contract"], blocks | ATOMIC_CONTRACTS,
                              (a["id"], s.get("slot")))

    def test_exemplar_evidence_paths_exist(self):
        for a in self.arts:
            ev = (a.get("exemplar") or {}).get("evidence")
            if not ev:
                continue
            for p in ([ev] if isinstance(ev, str) else ev):
                self.assertTrue((REPO / str(p)).exists(), (a["id"], p))

    def test_page_type_coverage(self):
        covered = set()
        for a in self.arts:
            covered |= set(a["useCases"]["pageTypes"])
        self.assertEqual(covered, set(self.doc["pageTypes"]))


class Selection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = al.load_genre("heroes-saas")

    def test_page_type_filter_and_determinism(self):
        a = al.shortlist(self.lib, "pricing", ["price transparency"])
        b = al.shortlist(self.lib, "pricing", ["price transparency"])
        self.assertEqual([x["id"] for x in a], [x["id"] for x in b])
        for x in a:
            self.assertIn("pricing", x["useCases"]["pageTypes"])
        self.assertTrue(1 <= len(a) <= 3)

    def test_variance_dial_moves_ranking(self):
        low = al.shortlist(self.lib, "homepage", [], variance="low", brand_hero="stack", k=6)
        high = al.shortlist(self.lib, "homepage", [], variance="high", brand_hero="stack", k=6)
        self.assertNotEqual([x["id"] for x in low], [x["id"] for x in high])

    def test_requires_off_grid_demotion(self):
        allowed = al.shortlist(self.lib, "homepage", [], off_grid=False, k=99)
        for a in allowed:
            self.assertFalse(a.get("requiresOffGrid"), a["id"])
        full = al.shortlist(self.lib, "homepage", [], off_grid=True, k=99)
        self.assertGreater(len(full), len(allowed))

    def test_candidate_block_contract_language(self):
        block = al.render_candidate_block(al.shortlist(self.lib, "developer", []))
        self.assertIn("HERO STRUCTURE CANDIDATES", block)
        self.assertIn("archetypeRef", block)
        self.assertEqual(al.render_candidate_block([]), "")


class SkeletonApplication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = _hubspot_doc()

    def test_no_ref_is_identity(self):
        sec = {"id": "x", "useCase": "hero", "archetype": "stack", "slots": []}
        out, notes = al.apply_archetype_skeleton(sec, self.doc)
        self.assertIs(out, sec)
        self.assertEqual(notes, [])

    def test_unknown_ref_fails_closed(self):
        sec = {"id": "x", "useCase": "hero", "archetype": "stack",
               "archetypeRef": "hero-does-not-exist", "slots": []}
        out, notes = al.apply_archetype_skeleton(sec, self.doc)
        self.assertNotIn("archetypeRef", out)
        self.assertTrue(any("not found" in n for n in notes))

    def test_archetype_and_knob_defaults_normalize(self):
        sec = {"id": "x", "useCase": "hero", "archetype": "stack",
               "archetypeRef": "hero-form-split", "slots": [], "knobs": {}}
        out, notes = al.apply_archetype_skeleton(sec, self.doc)
        self.assertEqual(out["archetype"], "split")
        self.assertIn("bandHeight", out["knobs"])
        self.assertTrue(any("normalized" in n for n in notes))

    def test_unresolved_physics_demotes(self):
        bare = copy.deepcopy(self.doc)
        bare.pop("layoutGrammar", None)
        sec = {"id": "x", "useCase": "hero", "archetype": "split",
               "archetypeRef": "hero-form-split", "slots": []}
        out, notes = al.apply_archetype_skeleton(sec, bare)
        self.assertNotIn("archetypeRef", out)
        self.assertTrue(any("demoted" in n for n in notes))
        art = al.find_archetype("hero-form-split")
        missing = al.unresolved_bindings(art, bare)
        self.assertIn("actionGroup", missing)
        self.assertIn("headerContext", missing)

    def test_viewport_band_height_degrades_to_tall(self):
        sec = {"id": "x", "useCase": "hero", "archetype": "stack",
               "archetypeRef": "hero-announcement-crest", "slots": []}
        out, _ = al.apply_archetype_skeleton(sec, self.doc)
        self.assertEqual(out["knobs"]["bandHeight"], "tall")

    def test_archetype_section_skips_pattern_alignment_layer(self):
        """A genre-skeleton section takes structure from the archetype + brand
        grammar, never from the seeded pattern's own alignment fact (the pattern
        keeps donating treatments). Without the ref the pattern layer still wins."""
        import layout_library as ll
        pat = ll.Pattern(
            id="donor", use_case="cta", archetype_ref="stack", surface_intent="any",
            intent="t", content_shape={"alignment": {"value": "left"}},
            special_treatments=[], responsive={}, variant_knobs={},
            origin="extracted", confidence="high", scope="brand", provenance=[])
        base = {"id": "x", "archetype": "stack"}
        r = cs.resolve_alignment(dict(base), pat, None, doc=self.doc)
        self.assertEqual((r["anchor"], r["source"]), ("left", "pattern"))
        r2 = cs.resolve_alignment({**base, "archetypeRef": "hero-pricing-value-forward"},
                                  pat, None, doc=self.doc)
        self.assertEqual(r2["source"], "brand")   # headerContext.standaloneStack
        self.assertEqual(r2["anchor"], "centered")

    def test_gate_accepts_brand_align_source(self):
        import onbrand_check as oc
        html = ('<html data-align-stance="declared">'
                '<div id="sec-0" class="cs-surface" data-align="centered" '
                'data-align-source="brand"></div></html>')
        passed, detail = oc._check_alignment_resolution(html)
        self.assertTrue(passed, detail)


class PromptInjection(unittest.TestCase):
    def test_absent_candidates_keep_prompt_byte_identical(self):
        doc = gc.load_brand(HUBSPOT)
        seeds = gc.seed_patterns(doc, HUBSPOT)
        base = gc.build_prompt("Brief.", HUBSPOT, "corporate-saas-clean", seeds)
        again = gc.build_prompt("Brief.", HUBSPOT, "corporate-saas-clean", seeds,
                                hero_candidates=None)
        self.assertEqual(base, again)
        with_c = gc.build_prompt("Brief.", HUBSPOT, "corporate-saas-clean", seeds,
                                 hero_candidates="## HERO STRUCTURE CANDIDATES\n- x")
        self.assertIn("HERO STRUCTURE CANDIDATES", with_c)
        self.assertNotIn("HERO STRUCTURE CANDIDATES", base)

    def test_schema_accepts_archetype_ref_and_rejects_unknown_keys(self):
        comp = {
            "schemaVersion": "composition.v1",
            "brief": {"id": "t"}, "brand": {"ref": str(HUBSPOT)},
            "style": {"id": "corporate-saas-clean"},
            "sections": [{
                "id": "hero", "useCase": "hero", "archetype": "stack",
                "archetypeRef": "hero-pricing-value-forward",
                "surfaceIntent": "primary", "novelty": "novel", "seededFrom": None,
                "slots": [{"name": "h", "role": "claim", "contract": "heading"}],
                "treatments": [],
            }],
        }
        self.assertEqual(gc.validate_schema(comp), [])
        bad = copy.deepcopy(comp)
        bad["sections"][0]["archetypeBogus"] = 1
        self.assertTrue(gc.validate_schema(bad))

    def test_brief_frontmatter_parses_and_plain_briefs_untouched(self):
        meta, body = al.parse_brief_frontmatter(
            "---\npageType: pricing\ntaskIntents: [price transparency]\n---\nBrief body.")
        self.assertEqual(meta["pageType"], "pricing")
        self.assertEqual(body, "Brief body.")
        meta2, body2 = al.parse_brief_frontmatter("No frontmatter here.")
        self.assertEqual(meta2, {})
        self.assertEqual(body2, "No frontmatter here.")


class BandHeightKnob(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = _hubspot_doc()

    def test_layout_passthrough_and_normalization(self):
        sec = {"id": "hero", "useCase": "hero", "archetype": "stack",
               "archetypeRef": "hero-x", "novelty": "novel", "surfaceIntent": "any",
               "slots": [{"name": "h", "role": "claim", "contract": "heading"}],
               "knobs": {"bandHeight": "compact"}}
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(layout["archetypeRef"], "hero-x")
        self.assertEqual(layout["_bandHeight"], "compact")
        sec["knobs"]["bandHeight"] = "viewport"      # degrade: no viewport units
        self.assertEqual(cfc.composition_to_layout(sec)["_bandHeight"], "tall")
        sec["knobs"]["bandHeight"] = "standard"      # standard = no hint
        self.assertNotIn("_bandHeight", cfc.composition_to_layout(sec))

    def test_css_snaps_to_brand_ladder_rung(self):
        from styles import inactive_context
        css = cs.band_height_css(self.doc, {"_bandHeight": "compact"}, "#sec-0",
                                 "surface/primary", inactive_context())
        self.assertIn("var(--space-section-y-sm)", css)   # hubspot's own smaller rung
        css_tall = cs.band_height_css(self.doc, {"_bandHeight": "tall"}, "#sec-0",
                                      "surface/primary", inactive_context())
        self.assertIn("var(--space-section-y-lg)", css_tall)
        self.assertEqual(cs.band_height_css(self.doc, {}, "#sec-0",
                                            "surface/primary", inactive_context()), "")

    def test_no_rung_in_direction_degrades_silently(self):
        doc = copy.deepcopy(self.doc)
        sp = doc["tokens"]["spacing"]
        for k in [k for k in sp if k.startswith("section") and k != "section-padding-light"]:
            sp.pop(k)
        from styles import inactive_context
        css = cs.band_height_css(doc, {"_bandHeight": "compact"}, "#sec-0",
                                 "surface/primary", inactive_context())
        self.assertEqual(css, "")


if __name__ == "__main__":
    unittest.main()
