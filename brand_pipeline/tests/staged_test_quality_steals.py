"""Data-contract validation for the three quality steals (stage A).

STAGED, NOT YET DISCOVERED: this file is deliberately named outside the suite's
``test*.py`` discovery pattern while pass 2 is in flight (stage-A concurrency
fence: the running pass-2 verification pins a suite count that stage-A files
must not move). Stage B renames it to ``test_quality_steals.py`` — content is
final; only the rename is deferred.

Covers, as DATA (no gate wiring yet — that is stage B):
  - contracts/section-rules.yaml     (section-rules.v1): shape, scoping,
    delegation integrity against the AS registry, severity doctrine;
  - contracts/conversion-structure.yaml (conversion-structure.v1): campaign
    grammar shape, constraint vocabulary, family-vocabulary consistency,
    funnel depth bands, composition useCase mapping;
  - evals/matrix/: the 12-brief corpus parses through the REAL brief
    frontmatter reader and binds to real campaigns/page types.

Run (stage B): ./venv/bin/python -m unittest brand_pipeline.tests.test_quality_steals
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import archetype_library as al            # noqa: E402

REPO = HERE.parent
SECTION_RULES = HERE / "contracts" / "section-rules.yaml"
CONVERSION = HERE / "contracts" / "conversion-structure.yaml"
ANTI_SLOP = HERE / "spec" / "anti-ai-slop.md"
COMPOSITION_SCHEMA = HERE / "spec" / "composition.v1.schema.json"
MATRIX = REPO / "evals" / "matrix"

SEVERITIES = {"advisory", "required"}
ENFORCEMENTS = {"new", "delegated"}
PROVENANCES = {"sibling-team-scorer", "as-history", "typographic-cro",
               "style-library-catalog"}
CONSTRAINT_KINDS = {"opens", "closes", "present", "window", "afterIndex",
                    "before", "adjacent"}
CAMPAIGN_IDS = {"leadgen-gated-content", "demo-request", "product-launch",
                "webinar-event", "comparison", "pricing"}
BRANDS = ("hubspot-v2", "remote")


def _rules_doc():
    return yaml.safe_load(SECTION_RULES.read_text())


def _conv_doc():
    return yaml.safe_load(CONVERSION.read_text())


def _as_ids() -> set[str]:
    ids = set(re.findall(r"^## (AS-\d+)", ANTI_SLOP.read_text(), re.MULTILINE))
    return ids


class SectionRulesLibraryShape(unittest.TestCase):
    """section-rules.yaml is valid, complete data for a generic auditor."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _rules_doc()
        cls.rules = cls.doc["rules"]

    def test_schema_and_unique_wellformed_ids(self):
        self.assertEqual(self.doc["schemaVersion"], "section-rules.v1")
        ids = [r["id"] for r in self.rules]
        self.assertEqual(len(ids), len(set(ids)), "duplicate rule ids")
        for rid in ids:
            self.assertRegex(rid, r"^SR-[A-Z]+-\d{2}$", rid)

    def test_every_rule_carries_the_full_contract(self):
        for r in self.rules:
            for key in ("id", "scope", "assertion", "severity", "enforcement",
                        "check", "rationale", "provenance"):
                self.assertIn(key, r, f"{r.get('id')}: missing {key}")
            self.assertIn(r["severity"], SEVERITIES, r["id"])
            self.assertIn(r["enforcement"], ENFORCEMENTS, r["id"])
            self.assertIn(r["provenance"], PROVENANCES, r["id"])
            self.assertTrue(str(r["assertion"]).strip(), r["id"])

    def test_scopes_bind_to_the_detection_table(self):
        detection = set(self.doc["detection"])
        for r in self.rules:
            self.assertIn(r["scope"], detection, r["id"])

    def test_rule_budget_per_family(self):
        """The library's own bar: 3-8 falsifiable rules per section family."""
        by_scope: dict[str, int] = {}
        for r in self.rules:
            by_scope[r["scope"]] = by_scope.get(r["scope"], 0) + 1
        for scope, n in by_scope.items():
            self.assertGreaterEqual(n, 3, scope)
            self.assertLessEqual(n, 8, scope)

    def test_delegated_rows_name_real_existing_law(self):
        """Delegation must point at law that exists TODAY: AS ids resolve
        against the registry; non-AS delegations name a known gate/contract
        family. Delegated rows never carry `new`-style check layers."""
        as_ids = _as_ids()
        known_non_as = {"scale_adherence", "interaction-contracts form family",
                        "interaction-contracts carousel family",
                        "interaction-contracts acc family"}
        for r in self.rules:
            if r["enforcement"] != "delegated":
                continue
            self.assertIn("delegatedTo", r, r["id"])
            targets = r["delegatedTo"]
            self.assertIsInstance(targets, list, r["id"])
            self.assertTrue(targets, r["id"])
            for t in targets:
                t = str(t)
                if t.startswith("AS-"):
                    self.assertIn(t, as_ids, f"{r['id']}: dangling {t}")
                else:
                    self.assertIn(t, known_non_as, f"{r['id']}: unknown law {t}")
            self.assertEqual(r["check"].get("layer"), "delegated", r["id"])

    def test_new_rules_declare_a_measurable_check(self):
        for r in self.rules:
            if r["enforcement"] != "new":
                continue
            chk = r["check"]
            self.assertIn(chk.get("layer"),
                          {"static", "geometry", "static+geometry",
                           "geometry+static"}, r["id"])
            for key in ("selector", "metric", "budget"):
                self.assertTrue(str(chk.get(key) or "").strip(),
                                f"{r['id']}: check.{key}")

    def test_sibling_team_proven_checks_present(self):
        """The two imported proven checks: heading line budget (generalized
        beyond hero via the section-header scope) + stat-unit parallelism."""
        by_id = {r["id"]: r for r in self.rules}
        hdr = by_id["SR-HDR-01"]
        self.assertEqual(hdr["scope"], "section-header")
        self.assertEqual(hdr["provenance"], "sibling-team-scorer")
        self.assertIn("2 lines", hdr["assertion"])
        stat = by_id["SR-STAT-02"]
        self.assertEqual(stat["scope"], "stat-band")
        self.assertEqual(stat["provenance"], "sibling-team-scorer")
        # the hero keeps its own display-band budget alongside the generalization
        self.assertEqual(by_id["SR-HERO-01"]["scope"], "hero")

    def test_no_duplication_of_registry_law(self):
        """Rules that touch AS-covered ground must be delegated, not `new`:
        spot-pin the cross-referenced ids the user named (AS-59 single filled
        primary; AS-14 stated exchange; AS-33 disk-backed logos)."""
        by_id = {r["id"]: r for r in self.rules}
        self.assertEqual(by_id["SR-HERO-03"]["enforcement"], "delegated")
        self.assertIn("AS-59", by_id["SR-HERO-03"]["delegatedTo"])
        self.assertEqual(by_id["SR-FORM-02"]["enforcement"], "delegated")
        self.assertIn("AS-14", by_id["SR-FORM-02"]["delegatedTo"])
        self.assertEqual(by_id["SR-LOGO-03"]["enforcement"], "delegated")
        self.assertIn("AS-33", by_id["SR-LOGO-03"]["delegatedTo"])

    def test_registry_candidates_stay_out_and_stay_few(self):
        cands = self.doc.get("registryCandidates") or []
        self.assertGreaterEqual(len(cands), 1)
        self.assertLessEqual(len(cands), 2, "universal tells: max 1-2 candidates")
        rule_ids = {r["id"] for r in self.rules}
        for c in cands:
            for ref in c.get("generalizes") or []:
                self.assertIn(ref, rule_ids, ref)


class ConversionStructureShape(unittest.TestCase):
    """conversion-structure.yaml is checkable grammar over the shared family
    vocabulary, sized to the declared constraint interpreter."""

    @classmethod
    def setUpClass(cls):
        cls.doc = _conv_doc()
        cls.campaigns = cls.doc["campaigns"]
        cls.families = set(_rules_doc()["detection"]) - {"section-header"}

    def test_schema_and_campaign_roster(self):
        self.assertEqual(self.doc["schemaVersion"], "conversion-structure.v1")
        self.assertEqual({c["id"] for c in self.campaigns}, CAMPAIGN_IDS)

    def test_campaign_contract_completeness(self):
        for c in self.campaigns:
            for key in ("id", "name", "funnelStage", "conversionMoment",
                        "intent", "depthBand", "formDepth", "constraints"):
                self.assertIn(key, c, f"{c.get('id')}: missing {key}")
            self.assertIn(c["conversionMoment"], self.families, c["id"])
            self.assertTrue(c["constraints"], c["id"])

    def test_depth_bands_nest_inside_funnel_bands(self):
        bands = self.doc["funnelDepthBands"]
        for c in self.campaigns:
            self.assertIn(c["funnelStage"], bands, c["id"])
            outer, inner = bands[c["funnelStage"]], c["depthBand"]
            self.assertLessEqual(outer["min"], inner["min"], c["id"])
            self.assertLessEqual(inner["max"], outer["max"], c["id"])
            fd = c["formDepth"]
            self.assertLessEqual(fd["minFields"], fd["maxFields"], c["id"])

    def test_constraints_use_declared_kinds_and_known_families(self):
        for c in self.campaigns:
            for r in c["constraints"]:
                self.assertIn(r["kind"], CONSTRAINT_KINDS,
                              f"{c['id']}: {r['kind']}")
                named: set[str] = set()
                for key in ("family", "anyOf", "toAnyOf", "first", "then"):
                    v = r.get(key)
                    if isinstance(v, str):
                        named.add(v)
                    elif isinstance(v, list):
                        named.update(v)
                self.assertTrue(named, f"{c['id']}: {r['kind']} names no family")
                self.assertFalse(named - self.families,
                                 f"{c['id']}: unknown {named - self.families}")
                self.assertIn(r.get("severity", "advisory"), SEVERITIES)
                self.assertTrue(str(r.get("why") or "").strip(),
                                f"{c['id']}: {r['kind']} missing why (the "
                                f"prompt-guidance projection source)")

    def test_family_map_binds_to_the_composition_schema(self):
        schema = json.loads(COMPOSITION_SCHEMA.read_text())
        use_cases = set(schema["$defs"]["useCase"]["enum"])
        fmap = self.doc["familyMap"]
        for uc, fam in fmap.items():
            if uc == "bySlots":
                self.assertLessEqual(set(fam), {"capture-form", "stat-band"})
                continue
            self.assertIn(uc, use_cases, uc)
            self.assertIn(fam, self.families, f"{uc} -> {fam}")
        self.assertLessEqual(set(self.doc["proofFamilies"]), self.families)

    def test_conversion_campaigns_require_their_conversion_moment(self):
        """hardFloor row 1: capture-form campaigns carry a present min>=1
        required constraint on capture-form."""
        for c in self.campaigns:
            if c["conversionMoment"] != "capture-form":
                continue
            rows = [r for r in c["constraints"]
                    if r["kind"] == "present"
                    and r.get("family") == "capture-form"]
            self.assertTrue(rows, c["id"])
            self.assertTrue(any(r.get("min", 0) >= 1 and
                                r.get("severity") == "required" for r in rows),
                            c["id"])

    def test_pricing_never_gates_the_price(self):
        """hardFloor row 2 exists as a required before-constraint."""
        pricing = next(c for c in self.campaigns if c["id"] == "pricing")
        rows = [r for r in pricing["constraints"]
                if r["kind"] == "before" and r.get("first") == "pricing-tiers"
                and r.get("then") == "capture-form"]
        self.assertTrue(rows)
        self.assertEqual(rows[0].get("severity"), "required")


class EvalMatrixCorpus(unittest.TestCase):
    """The 12-brief corpus is complete and parses through the REAL brief
    reader; every brief binds to a real campaign grammar and page type."""

    @classmethod
    def setUpClass(cls):
        cls.conv = _conv_doc()
        cls.genre = al.load_genre("heroes-saas")
        cls.page_types = {str(p).lower() for p in cls.genre["pageTypes"]}

    def test_corpus_is_complete_6x2(self):
        for brand in BRANDS:
            stems = {p.stem for p in (MATRIX / "briefs" / brand).glob("*.md")}
            self.assertEqual(stems, CAMPAIGN_IDS, brand)
        self.assertTrue((MATRIX / "README.md").exists())

    def test_briefs_parse_and_bind(self):
        for brand in BRANDS:
            for path in sorted((MATRIX / "briefs" / brand).glob("*.md")):
                meta, body = al.parse_brief_frontmatter(path.read_text())
                self.assertTrue(meta, path.name)
                self.assertEqual(meta.get("campaignType"), path.stem, path)
                self.assertIn(meta.get("campaignType"), CAMPAIGN_IDS, path)
                self.assertIn(str(meta.get("pageType", "")).lower(),
                              self.page_types, path)
                self.assertIn(meta.get("variance"), ("low", "mid", "high"), path)
                self.assertIsInstance(meta.get("taskIntents"), list, path)
                # a complete brief, not a stub: copy block + omissions doctrine
                self.assertGreater(len(body), 1200, path)
                self.assertIn("## Copy block", body, path)
                self.assertIn("## Deliberate omissions", body, path)

    def test_briefs_stay_style_and_palette_agnostic(self):
        """Briefs carry copy + structure intent; visual style belongs to the
        brand's extracted data (no hex values, no font names)."""
        rx = re.compile(r"#[0-9a-fA-F]{6}\b|font-family|border-radius")
        for brand in BRANDS:
            for path in sorted((MATRIX / "briefs" / brand).glob("*.md")):
                self.assertIsNone(rx.search(path.read_text()), path)

    def test_readme_defines_the_protocol_surfaces(self):
        text = (MATRIX / "README.md").read_text()
        for needle in ("runs/", "results.json", "results.md", "round",
                       "corporate-saas-clean", "generateSeconds"):
            self.assertIn(needle, text, needle)


if __name__ == "__main__":
    unittest.main()
