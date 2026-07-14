#!/usr/bin/env python3
"""Pass-3 stage-1 golden tests — brand_pipeline/style_resolver.py (checkpoint C).

Covers, per INTEGRATION-PLAN.md stage A:
  - merge semantics table ($replace/$append/$remove, bare-array replace, scalar
    replace, deep per-key dict merge, unknown-$-tag errors);
  - library loading guards (declared counts; string-typed axis values — the
    YAML-1.1 on/off coercion defect must stay fixed);
  - GOLDEN resolutions (fixed inputs → exact expected merged output) including
    override precedence, the two repaired brutalist overrides, the one
    genuinely-differing scaleRatio, dangling-bias translation, and zero-signal
    axis suppression;
  - the two-class invariant split (physics delegates to gate ids; genre demotes
    to advisory);
  - explicit out-of-vocabulary layout picks REJECT loudly (§4.3);
  - §4.2 brand-evidence merge: brand facts REPLACE directive values with
    dissents recorded (extraction posture) while an empty bundle leaves the
    package resolution untouched (create-from-style posture);
  - 21×51 all-pairs smoke (every catalog section × every directive resolves).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import style_resolver as sr  # noqa: E402

REPO = _BRAND_PIPELINE.parent
HUBSPOT_DIR = REPO / "runs" / "hubspot-v2" / "brand"


def _lib() -> sr.StyleLibrary:
    return sr.load_library()


# ─────────────────────────── merge semantics table ────────────────────────────────

class MergeSemantics(unittest.TestCase):
    def test_scalar_replace(self):
        self.assertEqual(sr.merge_specs({"radius": "md"}, {"radius": "none"}),
                         {"radius": "none"})

    def test_deep_per_key_dict_merge(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        patch = {"a": {"y": 9}}
        self.assertEqual(sr.merge_specs(base, patch), {"a": {"x": 1, "y": 9}, "b": 3})
        # inputs never mutated
        self.assertEqual(base, {"a": {"x": 1, "y": 2}, "b": 3})

    def test_bare_array_replaces(self):
        self.assertEqual(sr.merge_specs({"axes": [1, 2, 3]}, {"axes": [9]}),
                         {"axes": [9]})

    def test_tagged_replace_append_remove(self):
        base = {"rules": ["a", "b"]}
        self.assertEqual(sr.merge_specs(base, {"rules": {"$replace": ["z"]}}),
                         {"rules": ["z"]})
        self.assertEqual(sr.merge_specs(base, {"rules": {"$append": ["c"]}}),
                         {"rules": ["a", "b", "c"]})
        self.assertEqual(sr.merge_specs(base, {"rules": {"$remove": ["a"]}}),
                         {"rules": ["b"]})

    def test_combined_tags_apply_in_order(self):
        base = {"rules": ["a", "b"]}
        out = sr.merge_specs(base, {"rules": {"$replace": ["x", "y"],
                                              "$append": ["z"],
                                              "$remove": ["x"]}})
        self.assertEqual(out, {"rules": ["y", "z"]})

    def test_unknown_dollar_tag_raises(self):
        with self.assertRaises(sr.StyleResolutionError):
            sr.merge_specs({"rules": ["a"]}, {"rules": {"$merge": ["b"]}})

    def test_unknown_tag_against_mapping_raises(self):
        with self.assertRaises(sr.StyleResolutionError):
            sr.merge_specs({"a": {"x": 1}}, {"a": {"$patch": 1}})


# ─────────────────────────── library loading guards ───────────────────────────────

class LibraryLoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()

    def test_declared_counts(self):
        self.assertEqual(len(self.lib.sections), 21)
        self.assertEqual(len(self.lib.styles), 51)
        self.assertEqual(len(self.lib.primitives), 17)

    def test_axis_values_are_strings_never_bools(self):
        # the YAML-1.1 on/off coercion defect (INTEGRATION-PLAN §1.1) stays fixed
        for sid, sec in self.lib.sections.items():
            for axis, values in (sec.get("variationAxes") or {}).items():
                for v in values or []:
                    self.assertNotIsInstance(
                        v, bool, f"{sid}.{axis} carries a boolean {v!r}")

    def test_boolean_axis_value_raises_at_load(self):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td)
            shutil.copytree(sr.LIBRARY_DIR, bad, dirs_exist_ok=True)
            cat = bad / "sections" / "catalog.yaml"
            # un-quote one axis value so YAML 1.1 parses it as a boolean again
            cat.write_text(cat.read_text().replace('- "on"', "- on", 1))
            with self.assertRaises(sr.StyleResolutionError):
                sr.load_library(bad)

    def test_stage_b_data_repair_present(self):
        # §4.3 prescribed repair: list-rows extended into the two sections whose
        # brutalist overrides pick it
        self.assertIn("list-rows", self.lib.sections["pricing"]["layouts"])
        self.assertIn("list-rows", self.lib.sections["testimonial"]["layouts"])

    def test_every_override_targets_real_style_and_section(self):
        for style, secs in self.lib.overrides.items():
            self.assertIn(style, self.lib.styles)
            for sid in secs:
                self.assertIn(sid, self.lib.sections)


# ─────────────────────────── golden resolutions ───────────────────────────────────

class GoldenResolutions(unittest.TestCase):
    """Fixed inputs → exact expected merged output (no brand: package cascade only)."""

    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()

    def test_swiss_feature_trio(self):
        """Override precedence: explicit layout + $append rules + directive constraints."""
        r = sr.resolve("feature-trio", "swiss", self.lib)
        self.assertEqual(r["layout"], "grid-3")           # explicit override layout
        self.assertEqual(r["rules"], [
            "parallel grammar across items",
            "no item longer than the others",
            "strict equal columns, left-flush",            # $append'ed by the override
            "no decorative icons — numerals or hairlines only",
        ])
        # directive constraints with zero-signal axes dropped (§5)
        self.assertEqual(r["constraints"], {
            "density": "airy", "radius": "none", "border": "hairline",
            "shadow": "none", "contrast": "normal", "accentUsage": "minimal",
            "palette": "mono", "typeDisplay": "Helvetica/Neue grotesk",
            "typeBody": "grotesk", "case": "mixed", "tracking": "tight",
            "imagery": "figure",
        })
        self.assertNotIn("scaleRatio", r["constraints"])   # 1.25 = filler
        self.assertNotIn("motion", r["constraints"])       # subtle = filler
        # dangling grid-aligned bias translated, not silently dropped
        self.assertTrue(any("grid-aligned" in d for d in r["layoutDisciplines"]))

    def test_brutalist_pricing_repaired_override(self):
        """The §4.3 repair: brutalist.pricing resolves AS AUTHORED (list-rows),
        highlight axis narrowed to [none], monospace rules appended."""
        r = sr.resolve("pricing", "brutalist", self.lib)
        self.assertEqual(r["layout"], "list-rows")
        self.assertEqual(r["variationAxes"]["highlight"], ["none"])
        self.assertEqual(r["rules"][-3:], [
            "prices in monospace",
            "tiers stacked, no 'recommended' highlight",
            "thick 2px borders, no cards",
        ])
        self.assertTrue(any("set explicitly by override" in n for n in r["notes"]))

    def test_brutalist_testimonial_repaired_override(self):
        r = sr.resolve("testimonial", "brutalist", self.lib)
        self.assertEqual(r["layout"], "list-rows")
        self.assertIn("quote as plain blockquote, no card or avatar", r["rules"])

    def test_editorial_magazine_hero_keeps_genuine_scale_ratio(self):
        """editorial-magazine's 1.333 is one of only two NON-filler ratios (§5) —
        it must survive projection; the override's split-right + single-CTA
        narrowing must land."""
        r = sr.resolve("hero", "editorial-magazine", self.lib)
        self.assertEqual(r["layout"], "split-right")
        self.assertEqual(r["constraints"]["scaleRatio"], 1.333)
        self.assertEqual(r["variationAxes"]["ctaEmphasis"], ["single"])
        self.assertIn("drop the secondary CTA", r["rules"])

    def test_newspaper_keeps_its_ratio_too(self):
        r = sr.resolve("hero", "newspaper", self.lib)
        self.assertEqual(r["constraints"]["scaleRatio"], 1.2)

    def test_directive_only_pair_bias_reranks(self):
        """No override: layoutBias reranks the section's allowed layouts."""
        r = sr.resolve("hero", "minimalist", self.lib)
        # minimalist bias: [minimal, center-stack, split-left] — all allowed for
        # hero; first allowed wins
        self.assertEqual(r["layout"], "minimal")
        self.assertEqual(r["layoutBias"], ["minimal", "center-stack", "split-left"])

    def test_dangling_bias_translates_and_falls_through(self):
        """swiss hero: grid-aligned dangles (translated); split-left is the first
        REAL bias entry and wins over the default."""
        r = sr.resolve("hero", "swiss", self.lib)
        self.assertEqual(r["layout"], "split-left")
        self.assertEqual(r["layoutDisciplines"],
                         ["grid-aligned → " + sr.DANGLING_BIAS_TRANSLATION["grid-aligned"]])

    def test_bias_with_no_allowed_entry_falls_to_default(self):
        """grid-typographic biases [grid-aligned, list-rows]; hero allows neither
        (grid-aligned dangles, list-rows not a hero layout) → defaultLayout."""
        r = sr.resolve("hero", "grid-typographic", self.lib)
        self.assertEqual(r["layout"], "split-left")        # hero defaultLayout
        self.assertTrue(any("rerank no-ops" in n for n in r["notes"]))

    def test_unknown_ids_fail_closed(self):
        with self.assertRaises(sr.StyleResolutionError):
            sr.resolve("hero", "not-a-style", self.lib)
        with self.assertRaises(sr.StyleResolutionError):
            sr.resolve("not-a-section", "swiss", self.lib)


# ─────────────────────────── invariant two-class split ────────────────────────────

class InvariantClasses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()

    def test_physics_delegations(self):
        self.assertEqual(sr.classify_invariant("exactly one primary CTA"),
                         ("physics", "AS-59"))
        self.assertEqual(sr.classify_invariant("headline is the focal point"),
                         ("physics", "AS-32/AS-51"))
        self.assertEqual(sr.classify_invariant("high contrast with neighbors"),
                         ("physics", "AS-01"))
        self.assertEqual(sr.classify_invariant("one item open at a time (accordion)"),
                         ("physics", "AS-40"))
        self.assertEqual(sr.classify_invariant("equal optical weight"),
                         ("physics", "AS-50/container-law"))

    def test_genre_priors_demote_to_soft(self):
        for text in ("≤ 7 top-level links", "3–5 steps", "label ≤ 4 words",
                     "logos monochrome or unified treatment", "≤ 2 supporting lines",
                     "one recommended tier highlighted (unless style forbids)"):
            cls_, gate = sr.classify_invariant(text)
            self.assertEqual(cls_, "genre", text)
            self.assertIsNone(gate, text)

    def test_hero_resolution_carries_classified_invariants(self):
        r = sr.resolve("hero", "swiss", self.lib)
        by_text = {i["text"]: i for i in r["invariants"]}
        self.assertEqual(by_text["exactly one primary CTA"]["class"], "physics")
        self.assertEqual(by_text["exactly one primary CTA"]["gate"], "AS-59")
        self.assertEqual(by_text["≤ 2 supporting lines"]["class"], "genre")
        self.assertNotIn("gate", by_text["≤ 2 supporting lines"])

    def test_every_catalog_invariant_classifies(self):
        classes = {"physics", "genre"}
        for sid in self.lib.sections:
            r = sr.resolve(sid, "swiss", self.lib)
            for inv in r["invariants"]:
                self.assertIn(inv["class"], classes)
                if inv["class"] == "physics":
                    self.assertTrue(inv.get("gate"))


# ─────────────────────────── §4.3 loud rejection ───────────────────────────────────

class ExplicitLayoutRejection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()

    def test_out_of_vocabulary_override_layout_rejects_loudly(self):
        import copy as _copy
        lib2 = sr.StyleLibrary(
            sections=_copy.deepcopy(self.lib.sections),
            styles=_copy.deepcopy(self.lib.styles),
            overrides=_copy.deepcopy(self.lib.overrides),
            primitives=self.lib.primitives, global_axes=self.lib.global_axes)
        lib2.overrides.setdefault("swiss", {})["hero"] = {"layout": "marquee"}
        with self.assertRaises(sr.StyleResolutionError) as ctx:
            sr.resolve("hero", "swiss", lib2)
        self.assertIn("marquee", str(ctx.exception))
        self.assertIn("rejecting loudly", str(ctx.exception))

    def test_brand_override_layout_wins_when_allowed(self):
        bundle = sr.BrandBundle(doc={"overrides": {"hero": {"layout": "center-stack"}}})
        r = sr.resolve("hero", "swiss", self.lib, bundle)
        self.assertEqual(r["layout"], "center-stack")
        self.assertTrue(any("brand override" in n for n in r["notes"]))

    def test_brand_override_out_of_vocabulary_rejects(self):
        bundle = sr.BrandBundle(doc={"overrides": {"hero": {"layout": "table"}}})
        with self.assertRaises(sr.StyleResolutionError):
            sr.resolve("hero", "swiss", self.lib, bundle)


# ─────────────────────────── §4.2 brand-evidence merge ─────────────────────────────

class BrandEvidenceMerge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()
        cls.bundle = sr.load_brand_bundle(HUBSPOT_DIR)

    def test_hubspot_bundle_loads_all_artifacts(self):
        self.assertTrue(self.bundle.doc)
        self.assertIsNotNone(self.bundle.style_scale)
        self.assertIsNotNone(self.bundle.voice_facts)
        self.assertTrue(self.bundle.recipes)

    def test_brand_facts_replace_directive_values_with_dissent(self):
        """editorial-magazine directive says serif display / ratio 1.333 / mixed
        case — hubspot's measured facts (HubSpot Serif family name, derived ratio
        1.125, sentence casing) must WIN, each dissent recorded with provenance."""
        r = sr.resolve("hero", "editorial-magazine", self.lib, self.bundle)
        c = r["constraints"]
        self.assertEqual(c["scaleRatio"], 1.125)
        self.assertEqual(c["typeDisplay"], "HubSpot Serif")
        self.assertEqual(c["typeBody"], "HubSpot Sans")
        self.assertEqual(c["case"], "sentence")
        dissent_keys = {d["key"] for d in r["dissents"]}
        self.assertLessEqual({"scaleRatio", "typeDisplay", "typeBody", "case"},
                             dissent_keys)
        for d in r["dissents"]:
            self.assertEqual(d["winner"], "brand")
            self.assertTrue(d["provenance"])

    def test_brand_bindings_carry_signatures_and_space(self):
        b = sr.brand_bindings(self.bundle)
        self.assertIn("signatures", b)
        sig_ids = {s["id"] for s in b["signatures"]["value"]}
        self.assertIn("action-orange-scope", sig_ids)
        self.assertEqual(b["space"]["value"]["sectionRhythmPx"], [24, 40, 64, 96])

    def test_empty_bundle_binds_nothing(self):
        """create-from-style posture: no evidence → the style speaks unchallenged."""
        r_plain = sr.resolve("hero", "editorial-magazine", self.lib)
        r_empty = sr.resolve("hero", "editorial-magazine", self.lib, sr.BrandBundle())
        self.assertEqual(r_plain["constraints"], r_empty["constraints"])
        self.assertEqual(r_empty["dissents"], [])
        self.assertEqual(r_empty["brandBindings"], {})

    def test_poor_fit_scale_never_binds(self):
        bundle = sr.BrandBundle(style_scale={
            "schema": "style-scale.v1",
            "type": {"followsScale": False, "ratio": 1.5, "stepsPx": [16, 24]},
            "space": {"followsScale": False, "stepsPx": [8]},
        })
        b = sr.brand_bindings(bundle)
        self.assertNotIn("scaleRatio", b)
        self.assertNotIn("space", b)

    def test_resolution_is_deterministic(self):
        a = sr.resolve("hero", "editorial-magazine", self.lib, self.bundle)
        b = sr.resolve("hero", "editorial-magazine", self.lib, self.bundle)
        self.assertEqual(a, b)


# ─────────────────────────── all-pairs smoke ───────────────────────────────────────

class AllPairsSmoke(unittest.TestCase):
    def test_every_section_x_every_style_resolves(self):
        lib = _lib()
        count = 0
        for style in lib.styles:
            for sid in lib.sections:
                r = sr.resolve(sid, style, lib)
                self.assertIn(r["layout"], r["layouts"], f"{style}×{sid}")
                count += 1
        self.assertEqual(count, 21 * 51)

    def test_all_pairs_resolve_under_the_hubspot_bundle_too(self):
        lib = _lib()
        bundle = sr.load_brand_bundle(HUBSPOT_DIR)
        for style in ("swiss", "editorial-magazine", "neumorphism"):
            res = sr.resolve_all(style, lib, bundle)
            self.assertEqual(len(res), 21)


# ─────────────────────────── stage-2 block rendering ───────────────────────────────

class DirectiveBlockRendering(unittest.TestCase):
    SECTIONS = ["hero", "feature-trio", "metrics-band", "testimonial", "cta-band"]

    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()
        cls.bundle = sr.load_brand_bundle(HUBSPOT_DIR)

    def test_block_is_sentinel_delimited_and_deterministic(self):
        res = sr.resolve_all("swiss", self.lib, self.bundle, self.SECTIONS)
        b1 = sr.render_style_directive_block("swiss", res, self.lib)
        b2 = sr.render_style_directive_block(
            "swiss", sr.resolve_all("swiss", self.lib, self.bundle, self.SECTIONS),
            self.lib)
        self.assertEqual(b1, b2)
        self.assertTrue(b1.startswith(sr.STYLE_BLOCK_BEGIN))
        self.assertTrue(b1.rstrip().endswith(sr.STYLE_BLOCK_END))

    def test_block_carries_guidance_signatures_and_dissents(self):
        res = sr.resolve_all("swiss", self.lib, self.bundle, self.SECTIONS)
        block = sr.render_style_directive_block("swiss", res, self.lib)
        self.assertIn("Swiss / International", block)
        self.assertIn("strict column grid, everything left-flush", block)
        self.assertIn("- hero: layout `split-left`", block)
        self.assertIn('archetype "cards" (columns: 3)', block)
        self.assertIn("brand fact HubSpot Serif WINS", block)
        # the precedence statement rides in the block itself
        self.assertIn("NEVER outranks brand facts", block)

    def test_empty_resolutions_render_empty(self):
        self.assertEqual(sr.render_style_directive_block("swiss", {}, self.lib), "")

    def test_block_states_the_alignment_contract(self):
        """Bakeoff round-1 finding: a flush-asymmetric directive posture without
        an explicit alignment contract let reused patterns' own left stance stamp
        counterweight-less and hard-fail alignment-resolution. The block must
        state the contract for every style."""
        for style in ("swiss", "editorial-magazine", "neumorphism"):
            res = sr.resolve_all(style, self.lib, self.bundle, ["hero", "cta-band"])
            block = sr.render_style_directive_block(style, res, self.lib)
            self.assertIn("Alignment contract (HARD", block, style)
            self.assertIn("counterweight", block, style)


if __name__ == "__main__":
    unittest.main(verbosity=2)
