#!/usr/bin/env python3
"""The AUTHORED media-assets.v1 artifacts (hubspot-v2 + remote) and their
integration through the real pipeline surfaces:

- both artifacts load, validate C26/C27/C28-clean, and register every file the
  layout-library patterns bind (the superset contract vs assets-tagged.json);
- the authored mediaComposition cases: hubspot hero background-with-foreground +
  logo tiled-grid + integration scattered-cluster + agent carousel + testimonial
  tab state-swap; Remote accordion active-item state-swap + logo MARQUEE vs
  partner TILED-GRID contrast + hero art-surface background (the deduped noise
  asset covering both bound filenames);
- variant dedupe on real evidence: Remote's byte-identical noise files and the
  nav-icon twins live under ONE logical asset each;
- treatmentDefaults mirror the assets-tagged resolution (asset_render_mode
  byte-parity — the replica-safety invariant);
- prompt injection: artifact brands carry the [[MEDIA-FACTS]] block; an
  artifact-less brand's prompt has none (fact-gated byte-identity);
- END-TO-END no-match-ladder walk-through: a composition binding a real assetRef
  plus a declared gap renders, emits asset-requests.json, folds the state-swap
  media through the accordion device, and the onbrand media rows report clean;
- gate rows: check_media_bindings fact-gates on composition + registry presence.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))
sys.path.insert(0, str(REPO / "tools" / "extract"))

import compose_from_composition as cfc  # noqa: E402
import compose_section as cs  # noqa: E402
import component_render as cr  # noqa: E402
import generate_composition as gc  # noqa: E402
import media_semantics as ms  # noqa: E402
import onbrand_check as oc  # noqa: E402
from validate_brand_evidence import Report, _check_media_assets  # noqa: E402

HUBSPOT = REPO / "runs" / "hubspot-v2" / "brand"
REMOTE = REPO / "runs" / "remote" / "brand"
WOODWAVE = REPO / "runs" / "woodwave" / "brand"


def _slot(lib: dict, pattern_id: str, slot_name: str) -> dict:
    pat = next(p for p in lib["patterns"] if p["id"] == pattern_id)
    return next(s for s in pat["contentShape"]["slots"]
                if isinstance(s, dict) and s.get("name") == slot_name)


class AuthoredArtifactsValidate(unittest.TestCase):
    """C26/C27/C28 hold on the real authored artifacts — the proof the schema
    fits reality, not just fixtures."""

    def _check(self, brand_dir: Path):
        rep = Report(brand_dir)
        lib = yaml.safe_load((brand_dir / "layout-library.yaml").read_text())
        _check_media_assets(rep, brand_dir, lib)
        return rep

    def test_hubspot_clean(self):
        rep = self._check(HUBSPOT)
        self.assertEqual(rep.errors, [])
        self.assertEqual([w for w in rep.warnings if w.startswith("C28")], [])

    def test_remote_clean(self):
        rep = self._check(REMOTE)
        self.assertEqual(rep.errors, [])
        self.assertEqual([w for w in rep.warnings if w.startswith("C28")], [])

    def test_registries_are_supersets_of_pattern_bindings(self):
        """Every file a pattern's assets: list binds is REGISTERED (canonical or
        variant) — the C27 orphan rule, asserted directly on real data."""
        for brand_dir in (HUBSPOT, REMOTE):
            reg = ms.load_media_assets(brand_dir)
            files = set(ms.file_index(reg))
            lib = yaml.safe_load((brand_dir / "layout-library.yaml").read_text())
            for p in lib["patterns"]:
                for s in (p.get("contentShape") or {}).get("slots") or []:
                    for f in (s.get("assets") or []) if isinstance(s, dict) else []:
                        self.assertIn(Path(str(f)).name, files,
                                      f"{brand_dir.name}/{p['id']}: {f} unregistered")

    def test_rights_taxonomy_on_real_marks(self):
        """AS-67's machine substrate: every third-party mark family carries the
        rights flag; the brand's own art never does."""
        for brand_dir in (HUBSPOT, REMOTE):
            reg = ms.load_media_assets(brand_dir)
            for a in ms.asset_entries(reg):
                kind = a["assetSemantics"]["kind"]
                if kind in ("logo-third-party", "badge-review-award",
                            "badge-appstore", "social-icon"):
                    self.assertEqual(a["usageRights"], "third-party-mark",
                                     f"{brand_dir.name}:{a['id']}")
                if kind == "logo-own":
                    self.assertEqual(a["usageRights"], "own")

    def test_photography_fingerprints_measured(self):
        hs = ms.load_media_assets(HUBSPOT)["photographyFingerprint"]["measured"]
        self.assertEqual(hs["temperatureCast"], "warm")
        self.assertEqual(hs["source"], "measured")
        rm = ms.load_media_assets(REMOTE)["photographyFingerprint"]["measured"]
        self.assertEqual(rm["temperatureCast"], "cool")

    def test_generated_visuals_licensed_with_posters(self):
        hs = ms.generated_index(ms.load_media_assets(HUBSPOT))
        wash = hs["warm-accent-band-wash"]
        self.assertEqual(wash["kind"], "css-gradient")
        self.assertEqual(wash["recipe"]["tokenRoles"],
                         ["accent/pink", "accent/peach", "accent/coral"])
        self.assertTrue((HUBSPOT / "assets" / Path(wash["poster"]).name).is_file()
                        or (HUBSPOT / "assets" / wash["poster"]).is_file())
        rm = ms.generated_index(ms.load_media_assets(REMOTE))
        glow = rm["panel-edge-soft-glow"]
        self.assertEqual(glow["recipe"]["shape"], "radial")
        self.assertEqual(glow["degrade"], ["live", "poster", "omit"])


class AuthoredMediaCompositions(unittest.TestCase):
    """The authored arrangements on the clearest existing patterns."""

    @classmethod
    def setUpClass(cls):
        cls.hs_lib = yaml.safe_load((HUBSPOT / "layout-library.yaml").read_text())
        cls.rm_lib = yaml.safe_load((REMOTE / "layout-library.yaml").read_text())
        cls.hs_reg = ms.load_media_assets(HUBSPOT)
        cls.rm_reg = ms.load_media_assets(REMOTE)

    def test_hubspot_hero_background_with_foreground(self):
        mc = _slot(self.hs_lib, "hero-photo-overlay", "background")["mediaComposition"]
        self.assertEqual(mc["mode"], "background-with-foreground")
        self.assertEqual(ms.resolve_ref(self.hs_reg, mc["layers"][0]["assetRef"]),
                         "018-hs-full-bleed-1-optmised.webp")

    def test_hubspot_logo_tiled_grid(self):
        mc = _slot(self.hs_lib, "logo-proof-strip", "logos")["mediaComposition"]
        self.assertEqual(mc["mode"], "tiled-grid")
        self.assertEqual(len(mc["layers"]), 5)

    def test_hubspot_integration_scattered_cluster(self):
        mc = _slot(self.hs_lib, "integration-collage-banner", "media")["mediaComposition"]
        self.assertEqual(mc["mode"], "scattered-cluster")
        self.assertEqual(len(mc["layers"]), 6)
        self.assertEqual(len(mc["scatter"]["rotationRange"]), 2)

    def test_hubspot_testimonial_tab_state_swap(self):
        mc = _slot(self.hs_lib, "testimonial-tab-stats", "media")["mediaComposition"]
        self.assertEqual((mc["mode"], mc["trigger"]), ("state-swap", "tab"))
        by_item = {l["forItem"]: ms.resolve_ref(self.hs_reg, l["assetRef"])
                   for l in mc["layers"]}
        self.assertEqual(by_item["Enterprise"], "045-unipart-1.png")
        self.assertEqual(by_item["Small Business"], "047-youth-on-course.png")

    def test_remote_accordion_active_item_state_swap(self):
        mc = _slot(self.rm_lib, "feature-accordion-deep-accent", "media")["mediaComposition"]
        self.assertEqual((mc["mode"], mc["trigger"]), ("state-swap", "active-item"))
        self.assertEqual(len(mc["layers"]), 5)
        for layer in mc["layers"]:
            self.assertTrue(ms.resolve_ref(self.rm_reg, layer["assetRef"]),
                            layer["assetRef"])
        # the layers bind by ITEM LABEL — the same labels the section-copy items use
        copy_doc = yaml.safe_load((REMOTE / "section-copy.yaml").read_text())
        acc = None
        for entry in (copy_doc.get("layoutCopy") or {}).values():
            items = entry.get("items") if isinstance(entry, dict) else None
            if isinstance(items, list) and any(
                    isinstance(i, dict) and i.get("media") for i in items):
                acc = items
                break
        self.assertIsNotNone(acc, "accordion items with media not found in copy")
        labels = {str(i.get("heading") or i.get("label") or "") for i in acc}
        for layer in mc["layers"]:
            self.assertTrue(any(str(layer["forItem"]).lower() in l.lower()
                                or l.lower() in str(layer["forItem"]).lower()
                                for l in labels), layer["forItem"])

    def test_remote_marquee_vs_tiled_grid_contrast(self):
        marquee = _slot(self.rm_lib, "logo-marquee-strip", "logos")["mediaComposition"]
        grid = _slot(self.rm_lib, "partner-proof-row", "logos")["mediaComposition"]
        self.assertEqual(marquee["mode"], "marquee")
        self.assertEqual(len(marquee["layers"]), 12)
        self.assertEqual(grid["mode"], "tiled-grid")
        self.assertEqual(len(grid["layers"]), 4)

    def test_remote_noise_dedupe_covers_both_bound_names(self):
        """The hero pattern binds bg-noise-top-2x.webp; the closing band's family
        cites the -grey-green-blue name — ONE logical asset covers both."""
        idx = ms.file_index(self.rm_reg)
        self.assertIs(idx["bg-noise-top-2x.webp"],
                      idx["bg-noise-grey-green-blue-top.webp"])
        mc = _slot(self.rm_lib, "hero-inset-noise-panel", "background")["mediaComposition"]
        self.assertEqual(mc["mode"], "background-with-foreground")
        self.assertEqual(mc["layers"][0]["assetRef"], "art-surface-noise-gradient")


class TreatmentDefaultParity(unittest.TestCase):
    """Replica safety: the per-asset fits mirror what the tagged rules resolve for
    each file's ACTUAL rendered role — asset_render_mode answers identically with
    and without the media-assets registry attached."""

    CASES = {
        HUBSPOT: [("018-hs-full-bleed-1-optmised.webp", "hero-background"),
                  ("028-producticons-marketinghub-icon-orange.webp", "card-media"),
                  ("036-customer-agent-en-2x.png", "card-media"),
                  ("045-unipart-1.png", "card-media"),
                  ("019-ebay-logo.svg", "logo-strip"),
                  ("048-badge-leader-small-business.png", "badge-row")],
        REMOTE: [("hero-globe-illustration.webp", "split-media"),
                 ("collage-eor-ui.webp", "accordion-media"),
                 ("card-api-first.webp", "card-media"),
                 ("panel-infrastructure-ui-snippet.webp", "split-media")],
    }

    def test_fit_parity_per_exercised_role(self):
        for brand_dir, cases in self.CASES.items():
            doc = yaml.safe_load((brand_dir / "brand.yaml").read_text())
            cs.attach_asset_inventory(doc, brand_dir)
            self.assertIsInstance(doc.get("_mediaAssets"), dict, brand_dir.name)
            for fname, role in cases:
                with_reg = cr.asset_render_mode(doc, fname, role)
                stripped = {**doc, "_mediaAssetsFit": {}}
                without = cr.asset_render_mode(stripped, fname, role)
                self.assertEqual(with_reg, without,
                                 f"{brand_dir.name}:{fname}@{role}")


class PromptInjection(unittest.TestCase):
    def test_artifact_brands_carry_media_block(self):
        for brand_dir, probe in ((HUBSPOT, "hero-office-photo · photograph"),
                                 (REMOTE, "disclosure-collage-eor · product-ui-collage")):
            prompt = gc.build_prompt("Launch page brief.",
                                     brand_dir / "brand.yaml", "editorial-luxury",
                                     seeds="")
            self.assertIn(ms.MEDIA_FACTS_BEGIN, prompt, brand_dir.name)
            self.assertIn(probe, prompt, brand_dir.name)
            self.assertIn("NO-MATCH LADDER", prompt)
            self.assertIn("AS-67", prompt)

    def test_artifactless_brand_prompt_has_no_media_bytes(self):
        """Fact-gated byte-identity: with no media-assets.yaml the injected block
        is the EMPTY STRING (same contract as the pass-1 artifacts), so the
        assembly is byte-identical to the pre-media prompt."""
        self.assertEqual(ms.media_rules_block(ms.load_media_assets(WOODWAVE)), "")
        prompt = gc.build_prompt("Launch page brief.",
                                 WOODWAVE / "brand.yaml", "editorial-luxury",
                                 seeds="")
        self.assertNotIn(ms.MEDIA_FACTS_BEGIN, prompt)
        self.assertNotIn("NO-MATCH LADDER", prompt)


class EndToEndLadderWalkthrough(unittest.TestCase):
    """The no-match ladder demo: one composition binds a real assetRef (rung 0 —
    compatible asset exists, BIND), declares one honest gap (rung 2), and swaps
    disclosure media per item; the lane renders, the manifest lands, the gate's
    media rows read clean."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="media-lane-"))
        cls.brand_yaml = REMOTE / "brand.yaml"
        cls.comp = {
            "schemaVersion": "composition.v1",
            "brief": {"id": "ladder-demo"},
            "brand": {"ref": str(cls.brand_yaml)},
            "style": {"id": "editorial-luxury"},
            "sections": [
                {"id": "features", "useCase": "features", "archetype": "split",
                 "surfaceIntent": "primary", "novelty": "reuse",
                 "seededFrom": {"lib": "project", "id": "feature-accordion-deep-accent"},
                 "slots": [
                     {"name": "heading", "role": "section-title", "contract": "header",
                      "copy": {"heading": "Every employment need"}},
                     {"name": "list", "role": "disclosure rows", "contract": "accordion",
                      "copy": [{"label": "Employer of Record", "value": "Hire anywhere."},
                               {"label": "Global Payroll", "value": "Pay everywhere."}]},
                     {"name": "media", "role": "product media well", "contract": "image",
                      "mediaComposition": {"mode": "state-swap", "trigger": "active-item",
                                           "layers": [
                                               {"assetRef": "disclosure-collage-eor",
                                                "forItem": "Employer of Record"},
                                               {"assetRef": "disclosure-collage-global-payroll",
                                                "forItem": "Global Payroll"}]}},
                     {"name": "team-shot", "role": "supporting photo", "contract": "image",
                      "mediaAspect": "landscape",
                      "noCompatibleAsset": {"reason": "no team photography extracted",
                                            "requiredKind": "team-photo",
                                            "surface": "primary"}}],
                 "treatments": [], "knobs": {}}]}
        cls.summary = cfc.render_composition(cls.comp, cls.brand_yaml, cls.tmp,
                                             style_id=None, brand_dir=REMOTE)
        cls.html = (cls.tmp / "index.html").read_text()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_lints_clean_before_render(self):
        self.assertEqual(
            ms.lint_media_bindings(self.comp, ms.load_media_assets(REMOTE)), [])

    def test_state_swap_renders_through_accordion_device(self):
        self.assertIn("assets/collage-eor-ui.webp", self.html)
        self.assertIn("assets/collage-global-payroll-ui.webp", self.html)
        self.assertIn("cs-acc-media-item", self.html)

    def test_asset_request_manifest_emitted(self):
        payload = json.loads((self.tmp / ms.ASSET_REQUESTS_NAME).read_text())
        self.assertEqual(payload["schemaVersion"], "asset-requests.v1")
        self.assertEqual(len(payload["requests"]), 1)
        req = payload["requests"][0]
        self.assertEqual(req["slot"], "team-shot")
        self.assertEqual(req["requiredKind"], "team-photo")
        self.assertEqual(req["aspect"], "landscape")
        self.assertEqual(req["reason"], "no team photography extracted")

    def test_gate_media_rows_clean(self):
        rows = oc.check_media_bindings(self.tmp)
        self.assertEqual({r[0] for r in rows},
                         {"media-binding", "mark-legality", "slot-role-eligibility"})
        for rid, _label, passed, detail in rows:
            self.assertTrue(passed, f"{rid}: {detail}")

    def test_gate_rows_flag_a_silent_drop(self):
        bad = json.loads(json.dumps(self.comp))
        bad["sections"][0]["slots"][3] = {
            "name": "team-shot", "role": "supporting photo", "contract": "image",
            "asset": None}
        with tempfile.TemporaryDirectory() as tmp2:
            (Path(tmp2) / "composition.json").write_text(json.dumps(bad))
            rows = oc.check_media_bindings(Path(tmp2))
            binding = next(r for r in rows if r[0] == "media-binding")
            self.assertFalse(binding[2])
            self.assertIn("team-shot", binding[3])

    def test_gate_rows_fact_gate_on_registry(self):
        """A composition for an artifact-less brand produces NO media rows."""
        comp = {"schemaVersion": "composition.v1",
                "brand": {"ref": str(WOODWAVE / "brand.yaml")},
                "sections": [{"id": "s", "slots": [
                    {"name": "m", "contract": "image", "asset": None}]}]}
        with tempfile.TemporaryDirectory() as tmp2:
            (Path(tmp2) / "composition.json").write_text(json.dumps(comp))
            self.assertEqual(oc.check_media_bindings(Path(tmp2)), [])


class ReplicaByteStability(unittest.TestCase):
    """The replica HTML is byte-identical with the media layer in place (verified
    end-to-end at authoring time; this pins the CHANNEL — the registry attaches
    but no replica-path consumer changes output for mirrored fits)."""

    def test_attach_is_pure_metadata_for_replica_paths(self):
        for brand_dir in (HUBSPOT, REMOTE):
            doc = yaml.safe_load((brand_dir / "brand.yaml").read_text())
            cs.attach_asset_inventory(doc, brand_dir)
            fits = doc["_mediaAssetsFit"]
            self.assertTrue(fits)
            # every fit the registry asserts equals the legacy resolution for the
            # file's exercised role set (spot checks live in TreatmentDefaultParity;
            # here: no registry fit CONTRADICTS an explicit per-asset tagged fit).
            tags = doc.get("_assetTags") or {}
            for name, fit in fits.items():
                direct = ((tags.get(name) or {}).get("mediaTreatment") or {}).get("fit")
                if direct:
                    self.assertEqual(fit, direct, name)


if __name__ == "__main__":
    unittest.main()
