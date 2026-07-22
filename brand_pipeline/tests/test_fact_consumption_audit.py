#!/usr/bin/env python3
"""Tests for the unified fact-merge path (responsive_facts.merge_brand_facts) and the
fact-consumption audit (AS-83, fact_consumption_audit.py).

Two durable, systemic fixes for the "captured but not consumed" bug class:
  A. ONE canonical merge routine the replica AND generation both call, with an explicit,
     documented, TESTED exclusion set (never a silent drop).
  B. a generic, provenance-aware audit that FAILS loud when a captured measured fact is
     not consumed in the output, honoring the documented exclusions as a PASS.
"""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import responsive_facts as rf  # noqa: E402
import fact_consumption_audit as fca  # noqa: E402


# a complete planted sidecar spanning every measured responsive family (generic values).
_FULL_SIDECAR = {
    "hero": {
        "schema": "responsive.v1", "heightRule": "viewport-minus-nav",
        "navOffset": {"var": "--nav-h", "base": "56px"},
        "headingSizeLadder": [{"maxWidth": 599, "fontSize": "48px"}],
        "primaryButton": {"schema": "responsive.v1", "fontSize": "18px",
                          "provenance": {"origin": "extracted", "source": "action-1"}},
        "provenance": {"origin": "extracted", "source": "section-00"},
    },
    "footer": {"schema": "responsive.v1", "grid": {"breakpoint": 900, "columnsBelow": 1},
               "provenance": {"origin": "extracted", "source": "chrome-footer"}},
    "nav": {"schema": "responsive.v1", "panelSurface": {"background": "#abcdef"},
            "collapse": {"breakpoint": 1080, "burger": True},
            "provenance": {"origin": "extracted", "source": "chrome-header"}},
    "buttons": {"schema": "responsive.v1", "purgeHoverTransform": True,
                "provenance": {"origin": "extracted", "source": "action-1"}},
    "headings": {"schema": "responsive.v1", "lineHeights": {"h2": "28px"},
                 "provenance": {"origin": "extracted", "source": "heading-h2"}},
}


def _doc_with_hero_footer():
    return {"layouts": [{"id": "hero", "useCase": "hero"}], "footer": {}}


class MergeParity(unittest.TestCase):
    """Deliverable A: replica and generation merge through the SAME routine and merge every
    family IDENTICALLY except the explicit, documented exclusion set."""

    def setUp(self):
        # patch the sidecar loader so the test needs no disk fixture.
        self._orig = rf.load_sidecar
        rf.load_sidecar = lambda _dir: copy.deepcopy(_FULL_SIDECAR)

    def tearDown(self):
        rf.load_sidecar = self._orig

    def _facts(self, doc):
        hero = next((l for l in doc.get("layouts") or []
                     if l.get("useCase") == "hero"), {})
        return {
            "hero.responsive": "responsive" in hero,
            "footer.responsive": "responsive" in (doc.get("footer") or {}),
            "responsive": sorted((doc.get("responsive") or {}).keys()),
        }

    def test_replica_merges_every_family(self):
        doc = rf.merge_brand_facts(_doc_with_hero_footer(), Path("/x"), target="replica")
        self.assertEqual(self._facts(doc), {
            "hero.responsive": True, "footer.responsive": True,
            "responsive": ["buttons", "headings", "nav"]})

    def test_generation_excludes_only_the_documented_register_families(self):
        doc = rf.merge_brand_facts(_doc_with_hero_footer(), Path("/x"),
                                   target="generation")
        # fix2 2026-07: hero is the ONLY withheld family now (headings promoted, AS-82
        # unitless); footer/nav/buttons/headings all cross over identically to the replica.
        self.assertEqual(self._facts(doc), {
            "hero.responsive": False, "footer.responsive": True,
            "responsive": ["buttons", "headings", "nav"]})

    def test_shared_families_are_byte_identical_across_targets(self):
        rep = rf.merge_brand_facts(_doc_with_hero_footer(), Path("/x"), target="replica")
        gen = rf.merge_brand_facts(_doc_with_hero_footer(), Path("/x"),
                                   target="generation")
        # the families that DO cross over must be the exact same merged objects
        self.assertEqual(rep["footer"]["responsive"], gen["footer"]["responsive"])
        self.assertEqual(rep["responsive"]["nav"], gen["responsive"]["nav"])
        self.assertEqual(rep["responsive"]["buttons"], gen["responsive"]["buttons"])

    def test_excluded_families_table_is_the_single_source_of_truth(self):
        self.assertEqual(rf.excluded_families_for("replica"), {})
        # fix2 2026-07: headings PROMOTED into generation (AS-82 unitless line-height);
        # hero stays excluded (its absolute register fact has no generation consumer).
        self.assertEqual(set(rf.excluded_families_for("generation")), {"hero"})
        # the exclusion carries a documented REASON (never a silent, reasonless drop)
        for fam, reason in rf.excluded_families_for("generation").items():
            self.assertTrue(isinstance(reason, str) and len(reason) > 20, fam)

    def test_unknown_target_is_a_hard_error(self):
        with self.assertRaises(ValueError):
            rf.merge_brand_facts(_doc_with_hero_footer(), Path("/x"), target="banana")


class ByteIdentityFactlessBrand(unittest.TestCase):
    """Deliverable A #3: a brand/page WITHOUT a fact family is a no-op → byte-identical."""

    def setUp(self):
        self._orig = rf.load_sidecar

    def tearDown(self):
        rf.load_sidecar = self._orig

    def test_no_sidecar_is_a_noop_for_both_targets(self):
        rf.load_sidecar = lambda _dir: {}
        for target in ("replica", "generation"):
            base = {"layouts": [{"id": "hero", "useCase": "hero"}], "footer": {},
                    "tokens": {"type": {}}}
            out = rf.merge_brand_facts(copy.deepcopy(base), Path("/nope"), target=target)
            self.assertEqual(out, base, target)

    def test_absent_family_leaves_that_slot_untouched(self):
        # a sidecar carrying ONLY nav.collapse (the v2/remote shape) merges nothing else
        rf.load_sidecar = lambda _dir: {
            "nav": {"collapse": {"breakpoint": 1080, "burger": True},
                    "provenance": {"origin": "extracted"}}}
        base = {"layouts": [{"id": "hero", "useCase": "hero"}], "footer": {}}
        out = rf.merge_brand_facts(copy.deepcopy(base), Path("/x"), target="replica")
        self.assertNotIn("responsive", next(l for l in out["layouts"]
                                            if l["useCase"] == "hero"))
        self.assertNotIn("responsive", out["footer"])
        self.assertEqual(sorted(out["responsive"].keys()), ["nav"])


# a page whose emitted CSS carries EVERY consumer's fact-gated marker + structural signals.
_CONSUMED_HTML = """<style>
/* responsive hero (fact-gated: layouts[].responsive) — ... */
/* responsive hero primary button (fact-gated: layouts[].responsive.primaryButton) — ... */
/* responsive footer (fact-gated: footer.responsive) — ... */
/* responsive headings (fact-gated: responsive.headings.lineHeights) — ... */
/* nav mobile collapse (fact-gated: responsive.nav.collapse) — ... */
.cs-mega { background: #abcdef; }
</style>
<section data-surface="surface/primary"><div style="position: sticky"></div></section>"""

# a page that consumed NOTHING (no markers, no panel paint, no sticky, no data-surface).
_DROPPED_HTML = "<style>.c-button:hover { transform: translateY(-1px); }</style><section></section>"


class AuditConsumption(unittest.TestCase):
    """Deliverable B: the audit passes a consumed fact, flags an unconsumed one, and honors
    the documented exclusions — provenance-aware."""

    def test_consumed_facts_pass(self):
        findings = fca.audit_facts(sidecar=_FULL_SIDECAR, doc={}, library={},
                                   html=_CONSUMED_HTML, target="replica")
        by = {f.family: f for f in findings}
        for fam in ("responsive.hero", "responsive.hero.primaryButton",
                    "responsive.footer", "responsive.headings.lineHeights",
                    "responsive.nav.collapse", "responsive.nav.panelSurface"):
            self.assertEqual(by[fam].status, fca.CONSUMED, fam)
        # purge is consumed because the translateY lift is ABSENT from this html
        self.assertEqual(by["responsive.buttons.purgeHoverTransform"].status, fca.CONSUMED)

    def test_unconsumed_measured_fact_fails_loud(self):
        findings = fca.audit_facts(sidecar=_FULL_SIDECAR, doc={}, library={},
                                   html=_DROPPED_HTML, target="replica")
        errors = [f for f in findings if f.is_error]
        fams = {f.family for f in errors}
        # the marker-bearing families all dropped; each is a MEASURED error
        self.assertIn("responsive.hero", fams)
        self.assertIn("responsive.footer", fams)
        self.assertIn("responsive.nav.collapse", fams)
        # the purge fact is UNCONSUMED here (the un-grounded translateY lift is present)
        self.assertIn("responsive.buttons.purgeHoverTransform", fams)
        for f in errors:
            self.assertTrue(f.is_measured, f.family)  # provenance-aware: extracted → error
        self.assertFalse(fca.summarize(findings)["ok"])

    def test_documented_exclusion_is_a_pass_not_a_failure(self):
        # under generation, the hero family is a documented exclusion → EXCLUDED, never a
        # silent drop and never an error, EVEN with a page that consumed nothing.
        findings = fca.audit_facts(sidecar=_FULL_SIDECAR, doc={}, library={},
                                   html=_DROPPED_HTML, target="generation")
        by = {f.family: f for f in findings}
        self.assertEqual(by["responsive.hero"].status, fca.EXCLUDED)
        self.assertEqual(by["responsive.hero.primaryButton"].status, fca.EXCLUDED)
        # fix2 2026-07: headings is PROMOTED into generation now — it is a real audited
        # family, not an exclusion, so a page that dropped it is a loud UNCONSUMED error.
        self.assertEqual(by["responsive.headings.lineHeights"].status, fca.UNCONSUMED)
        excluded_fams = {f.family for f in findings if f.status == fca.EXCLUDED}
        errors = {f.family for f in findings if f.is_error}
        self.assertFalse(excluded_fams & errors)  # an excluded fact is never an error

    def test_sticky_column_flagged_when_unconsumed(self):
        library = {"patterns": [{"id": "sticky-x", "origin": "extracted",
                                 "specialTreatments": [{"kind": "sticky-column"}]}]}
        # no `position: sticky` in the html → UNCONSUMED (the sticky-column driver finding)
        findings = fca.audit_facts(sidecar={}, doc={}, library=library,
                                   html="<section></section>", target="replica")
        sticky = [f for f in findings if f.family.endswith("sticky-column")]
        self.assertEqual(len(sticky), 1)
        self.assertEqual(sticky[0].status, fca.UNCONSUMED)
        # ...and CONSUMED once the device renders position:sticky
        ok = fca.audit_facts(sidecar={}, doc={}, library=library,
                             html="<style>.x{position: sticky}</style>", target="replica")
        self.assertEqual([f for f in ok if f.family.endswith("sticky-column")][0].status,
                         fca.CONSUMED)

    def test_per_section_surface_consumed_via_data_surface(self):
        doc = {"layouts": [{"id": "band", "surfaceIntent": "surface/inverse",
                            "origin": "extracted"}]}
        html = '<section data-surface="surface/inverse"></section>'
        f = [x for x in fca.audit_facts(sidecar={}, doc=doc, library={}, html=html,
                                        target="replica")
             if x.family == "layout.surfaceIntent"][0]
        self.assertEqual(f.status, fca.CONSUMED)
        # absent data-surface → UNCONSUMED
        f2 = [x for x in fca.audit_facts(sidecar={}, doc=doc, library={}, html="<section>",
                                         target="replica")
              if x.family == "layout.surfaceIntent"][0]
        self.assertEqual(f2.status, fca.UNCONSUMED)

    def test_generation_delegates_source_reproduction_families(self):
        # on generation, per-section surface + specialTreatments delegate (a composed page
        # uses its own sections), so they never false-fail as captured-fact drops.
        doc = {"layouts": [{"id": "band", "surfaceIntent": "surface/inverse",
                            "origin": "extracted"}]}
        library = {"patterns": [{"id": "s", "origin": "extracted",
                                 "specialTreatments": [{"kind": "sticky-column"}]}]}
        findings = fca.audit_facts(sidecar={}, doc=doc, library=library,
                                   html="<section></section>", target="generation")
        statuses = {f.family: f.status for f in findings}
        self.assertEqual(statuses.get("layout.surfaceIntent"), fca.DELEGATED)
        self.assertEqual(statuses.get("layout.specialTreatment"), fca.DELEGATED)
        self.assertTrue(fca.summarize(findings)["ok"])


class AuditRealArtifacts(unittest.TestCase):
    """Integration smoke tests against the real v3 replica + generated page (skipped when
    the fixtures are absent)."""

    def test_v3_replica_sticky_column_now_consumed(self):
        # AS-83 sticky-column-now-consumed assertion (fix1 2026-07): the sticky-copy
        # column device is the queued driver the AS-83 audit flagged; once the renderer
        # emits `position: sticky` (side-rail device + measured per-section pin) it is
        # CONSUMED, so the v3 replica has ZERO captured-but-unconsumed measured facts.
        brand = REPO / "runs" / "hubspot-v3" / "brand" / "brand.yaml"
        rep = REPO / "runs" / "hubspot-v3" / "brand" / "compose" / "replica"
        if not (brand.is_file() and (rep / "index.html").is_file()):
            self.skipTest("hubspot-v3 replica fixture not present")
        findings = fca.audit_render(brand, rep, target="replica")
        errors = {f.family for f in findings if f.is_error}
        self.assertEqual(errors, set(), f"unexpected unconsumed measured facts: {errors}")
        sticky = [f for f in findings
                  if f.family == "layout.specialTreatment.sticky-column"]
        self.assertEqual(len(sticky), 1)
        self.assertEqual(sticky[0].status, fca.CONSUMED)

    def test_v3_generation_has_no_silent_drops(self):
        brand = REPO / "runs" / "hubspot-v3" / "brand" / "brand.yaml"
        gen = REPO / "runs" / "hubspot-v3" / "brand" / "compose" / "ai-product-launch"
        if not (brand.is_file() and (gen / "index.html").is_file()):
            self.skipTest("hubspot-v3 generated page fixture not present")
        findings = fca.audit_render(brand, gen, target="generation")
        # fix2 2026-07: hero is the sole documented exclusion; headings is now PROMOTED and
        # CONSUMED (unitless line-height). Everything else consumed/delegated → no
        # captured-but-unconsumed measured fact on the generated page.
        self.assertTrue(fca.summarize(findings)["ok"],
                        [f.family for f in findings if f.is_error])
        excluded = {f.family for f in findings if f.status == fca.EXCLUDED}
        self.assertEqual(excluded, {"responsive.hero", "responsive.hero.primaryButton"})
        headings = [f for f in findings
                    if f.family == "responsive.headings.lineHeights"]
        self.assertEqual(headings[0].status, fca.CONSUMED)


if __name__ == "__main__":
    unittest.main()
