from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
for path in (REPO / "brand_pipeline", REPO / "tools" / "extract"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import author_brand as ab  # noqa: E402
import pipeline_flow as pf  # noqa: E402
import staged_author as sa  # noqa: E402
import validate_brand_evidence as vbe  # noqa: E402

SNAPSHOT = (
    "Fixture is an evidence-grounded product system with measured typography, "
    "surface, spacing, interaction, and component rules preserved across every "
    "authoring stage and deterministic projection."
)


class Report:
    def __init__(self, errors=None, warnings=None):
        self.errors = errors or []
        self.warnings = warnings or []
        self.ok = not self.errors


class FixtureProvider:
    model = "fixture-author"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.last_usage = {}

    def text_query(self, *args, **kwargs):
        self.calls += 1
        self.last_usage = {"input_tokens": 10, "output_tokens": 5}
        return self.responses.pop(0)


def response(files):
    return json.dumps({"files": files})


def patch_response(patches):
    return json.dumps({"patches": patches})


def golden_files():
    return {
        "brand.yaml": yaml.safe_dump({
            "brand": {"name": "Fixture", "sourceUrl": "https://example.test",
                      "snapshot": {"value": SNAPSHOT}},
            "tokens": {
                "type": {},
                "spacing": {
                    "relationalLadder": {
                        "notObserved": True,
                        "reason": "fixture has no measured text stack",
                    }
                },
            },
            "layouts": [],
            "blocks": {},
        }, sort_keys=False),
        "brand-chrome.yaml": yaml.safe_dump({
            "navbar": {"links": []},
            "footer": {"columns": []},
        }, sort_keys=False),
        "layout-library.yaml": yaml.safe_dump({
            "schemaVersion": "layout-patterns.v1", "patterns": [{
                "id": "fixture-designed-pattern",
                "origin": "designed",
                "archetypeRef": "stack",
                "contentShape": {"slots": []},
            }]}),
        "section-copy.yaml": yaml.safe_dump({
            "sectionCopy": {"wordmark": "Fixture"}, "layoutCopy": {}}),
        "assets-tagged.json": json.dumps({
            "schemaVersion": "assets-tagged.v1", "assets": []}),
        "media-assets.yaml": yaml.safe_dump({
            "schemaVersion": "media-assets.v1",
            "brand": "Fixture",
            "photographyFingerprint": {
                "notObserved": True, "reason": "no photographs in fixture"},
            "assets": [],
        }),
        "media-guidance.yaml": yaml.safe_dump({
            "schemaVersion": "media-guidance.v1",
            "photographyFingerprint": {
                "notObserved": True, "reason": "no photographs in fixture"},
            "tagRules": {},
        }),
        "voice-facts.yaml": yaml.safe_dump({
            "schemaVersion": "voice-facts.v1", "source": "fixture"}),
        "voice.md": "# Fixture voice\n",
    }


def grouped_responses(files=None):
    files = files or golden_files()
    return [response({name: files[name] for name in group}) for group in ab.AUTHOR_GROUPS]


def make_bundle(lane: Path):
    evidence = lane / "evidence"
    (evidence / "crops").mkdir(parents=True)
    (evidence / "grounding").mkdir()
    for name in (
        "dom-sections.json", "css-facts.json", "computed-styles.json",
        "section-rects.json", "motion-audit.json",
    ):
        (evidence / name).write_text("{}")
    (evidence / "crops" / "crops-manifest.json").write_text('{"crops":[]}')
    (evidence / "grounding" / "section-00.yaml").write_text(
        "schemaVersion: section-grounding.v1\ncopy: {heading: Fixture}\n")
    (lane / "assets-manifest.json").write_text('{"assets":[]}')
    (lane / "media-assets-draft.yaml").write_text(
        "schemaVersion: media-assets.v1\nassets: []\n")


class AuthorBrandTests(unittest.TestCase):
    def setUp(self):
        self.orig_derive = ab._derive_outputs

        def derive(lane):
            ab.atomic_write_group(Path(lane), {
                "brand.md": "# Fixture\n",
                "style-scale.yaml": "schemaVersion: style-scale.v1\n",
            })
        ab._derive_outputs = derive

    def tearDown(self):
        ab._derive_outputs = self.orig_derive

    def test_input_bundle_contains_fresh_evidence_and_specs(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            bundle = ab.build_input_bundle(lane, source_url="https://example.test")
        self.assertIn("evidence/dom-sections.json", bundle["evidence"])
        self.assertIn("evidence/grounding/section-00.yaml", bundle["evidence"])
        self.assertIn("brand-schema.md", bundle["specs"])
        self.assertEqual(bundle["sourceUrl"], "https://example.test")

    def test_expected_output_set(self):
        self.assertEqual(set(ab.EXPECTED_OUTPUTS), {
            "brand.yaml", "brand.md", "section-copy.yaml", "layout-library.yaml",
            "assets-tagged.json", "media-assets.yaml", "style-scale.yaml",
            "voice-facts.yaml", "voice.md",
        })

    def test_response_group_is_atomic_on_parse_failure(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            with self.assertRaises(ab.AuthorBlocked):
                files = ab.parse_model_files(
                    response({"brand.yaml": "brand: {name: Fixture}\n"}),
                    ("brand.yaml", "section-copy.yaml"))
                ab.atomic_write_group(lane, files)
            self.assertFalse((lane / "brand.yaml").exists())

    def test_missing_provider_blocks_before_validation(self):
        original = ab._provider_available
        ab._provider_available = lambda: False
        validations = {"n": 0}
        try:
            with tempfile.TemporaryDirectory() as td:
                lane = Path(td)
                make_bundle(lane)
                with self.assertRaises(ab.AuthorBlocked):
                    ab.author_brand(
                        lane, validator=lambda p: validations.__setitem__(
                            "n", validations["n"] + 1))
                report = json.loads((lane / ab.AUTHOR_REPORT).read_text())
            self.assertEqual(validations["n"], 0)
            self.assertEqual(report["status"], "blocked")
            self.assertIn("ANTHROPIC_API_KEY", report["reason"])
        finally:
            ab._provider_available = original

    def test_bounded_repair_stops_at_configured_limit(self):
        files = golden_files()
        provider = FixtureProvider(
            grouped_responses(files)
            + [
                patch_response([{
                    "file": "brand.yaml", "op": "merge", "path": "/buttons",
                    "value": {"primary": {
                        "style": "filled", "bg": "#000", "fg": "#fff",
                        "radius": "4px", "focus": "visible",
                    }},
                }]),
                patch_response([{
                    "file": "brand.yaml", "op": "merge", "path": "/buttons",
                    "value": {"primary": {"focus": "visible"}},
                }]),
            ])
        validations = {"n": 0}

        def invalid(_):
            validations["n"] += 1
            return Report(["C3: fixture failure"])

        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            with self.assertRaises(ab.AuthorBlocked):
                ab.author_brand(lane, provider=provider, validator=invalid,
                                max_repairs=2)
            report = json.loads((lane / ab.AUTHOR_REPORT).read_text())
        self.assertEqual(validations["n"], 3)
        self.assertEqual(provider.calls, 6)
        self.assertEqual(report["status"], "needs_iteration")
        self.assertEqual(report["repairs"], 2)

    def test_idempotent_resume_and_force(self):
        files = golden_files()
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            ab.atomic_write_group(lane, {
                **files, "brand.md": "# Fixture\n",
                "style-scale.yaml": "schemaVersion: style-scale.v1\n",
            })
            skipped_provider = FixtureProvider([])
            result = ab.author_brand(
                lane, provider=skipped_provider, validator=lambda p: Report())
            self.assertTrue(result.skipped)
            self.assertEqual(skipped_provider.calls, 0)

            forced_provider = FixtureProvider(grouped_responses(files))
            result = ab.author_brand(
                lane, provider=forced_provider, validator=lambda p: Report(),
                force=True)
            self.assertFalse(result.skipped)
            self.assertEqual(forced_provider.calls, 4)

    def test_fake_provider_golden_fixture_writes_valid_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)

            def valid(path):
                complete, missing = ab.authored_complete(path)
                self.assertTrue(complete, missing)
                for name in ("brand.yaml", "layout-library.yaml",
                             "section-copy.yaml", "media-assets.yaml"):
                    self.assertIsInstance(yaml.safe_load((path / name).read_text()), dict)
                self.assertIsInstance(
                    json.loads((path / "assets-tagged.json").read_text()), dict)
                return Report()

            result = ab.author_brand(
                lane, provider=FixtureProvider(grouped_responses()),
                validator=valid)
            self.assertTrue(result.ok)
            self.assertEqual(result.calls, 4)
            self.assertEqual(result.usage["input_tokens"], 40)

    def test_validation_never_runs_before_author_completeness(self):
        provider = FixtureProvider([
            response({"wrong.yaml": "x: 1\n"}),
        ])
        validations = {"n": 0}
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            with self.assertRaises(ab.AuthorBlocked):
                ab.author_brand(
                    lane, provider=provider,
                    validator=lambda p: validations.__setitem__(
                        "n", validations["n"] + 1))
        self.assertEqual(validations["n"], 0)


class FlowAuthorFailureTests(unittest.TestCase):
    def test_flow_catches_author_failure_and_writes_report(self):
        originals = pf.brand_dir_for, pf._run_extraction
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            pf.brand_dir_for = lambda brand: lane
            pf._run_extraction = lambda *a, **k: (_ for _ in ()).throw(
                RuntimeError("author failed"))
            try:
                result = pf.run_flow("fixture", write_report=True)
            finally:
                pf.brand_dir_for, pf._run_extraction = originals
            report = json.loads((lane / pf.FLOW_REPORT_JSON).read_text())
        self.assertFalse(result.ok)
        self.assertEqual(result.blocked_gate, "G1")
        self.assertEqual(report["blockedGate"], "G1")
        self.assertIn("author failed", report["gates"][0]["reason"])

    def test_flow_reports_exact_blocked_author_stage(self):
        originals = pf.brand_dir_for, pf._run_extraction
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            (lane / ab.AUTHOR_REPORT).write_text(json.dumps({
                "stages": [{
                    "name": "media", "status": "blocked", "inputBytes": 97000,
                    "model": "fixture", "durationS": 12.5, "reason": "capped",
                }]
            }))
            pf.brand_dir_for = lambda brand: lane
            pf._run_extraction = lambda *a, **k: (_ for _ in ()).throw(
                RuntimeError("media failed"))
            try:
                result = pf.run_flow("fixture", write_report=False)
            finally:
                pf.brand_dir_for, pf._run_extraction = originals
        self.assertEqual(result.gates[0].detail["authorStage"], "media")
        self.assertEqual(result.gates[0].detail["authorStageInputBytes"], 97000)


class StagedAuthorContractTests(unittest.TestCase):
    def test_stage_dag_and_bounded_evidence_scopes(self):
        self.assertEqual([s.name for s in sa.STAGES], [
            "foundation", "copy-chrome", "patterns-recipes", "media",
            "projections"])
        self.assertEqual(sa.STAGE_BY_NAME["projections"].dependencies[-1], "media")
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            for stage in sa.MODEL_STAGES:
                bundle = sa.build_stage_bundle(lane, stage.name)
                text = sa._prompt(stage, bundle)
                size = sa._input_size(sa._stage_system(stage), text)
                self.assertLessEqual(size, stage.max_input_bytes)
                self.assertNotIn("base64", text.lower())
                self.assertNotIn(
                    "evidence/css-rules.json", bundle.get("evidenceRefs", []))
            media = sa.build_stage_bundle(lane, "media")
            self.assertNotIn("computedStyles", media)
            self.assertNotIn("mediaDraft", media)
            self.assertNotIn("assetManifest", media)
            copy = sa.build_stage_bundle(lane, "copy-chrome")
            self.assertNotIn("cssFacts", copy)

    def test_media_contract_is_tag_level_and_projects_compat_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            draft_assets = []
            for i in range(12):
                draft_assets.append({
                    "id": f"asset-{i}",
                    "file": f"asset-{i}.png",
                    "tagGuess": "decorative" if i < 8 else "logo-wall-logo",
                    "assetSemantics": {
                        "kind": "photograph" if i < 8 else "logo-third-party"},
                    "facts": {"intrinsic": {"w": 100, "h": 50}},
                    "usageRights": "own" if i < 8 else "third-party-mark",
                    "treatmentDefaults": {"fit": "cover" if i < 8 else "mark"},
                    "compositionRoles": [],
                    "provenance": {
                        "source": "capture-files", "sections": [],
                        "confidence": "high"},
                })
            (lane / "media-assets-draft.yaml").write_text(yaml.safe_dump({
                "schemaVersion": "media-assets.v1", "assets": draft_assets}))
            bundle = sa.build_stage_bundle(lane, "media")
            prompt = sa._prompt(sa.STAGE_BY_NAME["media"], bundle)
            self.assertLess(sa._input_size(
                sa._stage_system(sa.STAGE_BY_NAME["media"]), prompt), 20_000)
            self.assertEqual(
                sum(len(v) for v in bundle["mediaEvidence"]["representativeAssets"].values()),
                4)
            guidance = yaml.safe_dump({
                "schemaVersion": "media-guidance.v1",
                "photographyFingerprint": {
                    "notObserved": True, "reason": "fixture"},
                "tagRules": {
                    "decorative": {"treatmentDefaults": {"fit": "contain"}},
                    "logo-wall-logo": {"usageRights": "third-party-mark"},
                },
            })
            (lane / "media-guidance.yaml").write_text(guidance)
            (lane / "brand.yaml").write_text("brand: {name: Fixture}\n")
            tagged = json.loads(sa._project_assets_tagged(lane))
            self.assertEqual(len(tagged["assets"]), 12)
            self.assertEqual(tagged["assets"][0]["mediaTreatment"]["fit"], "contain")

    def test_media_guidance_rejects_per_asset_output(self):
        bad = yaml.safe_dump({
            "schemaVersion": "media-guidance.v1",
            "photographyFingerprint": {"notObserved": True, "reason": "fixture"},
            "tagRules": {"decorative": {}},
            "assetAnnotations": {"asset-1": {"usageRights": "own"}},
        })
        with self.assertRaisesRegex(ab.AuthorBlocked, "forbidden top-level"):
            sa._validate_media_guidance(bad, {"decorative"})

    def test_repair_errors_route_only_to_owner(self):
        routed = sa._errors_by_owner([
            "C4: copy invalid", "C7: chrome invalid", "C26: media invalid",
            "C20: grid invalid"])
        self.assertEqual(set(routed), {"copy-chrome", "media", "patterns-recipes"})
        self.assertEqual(len(routed["copy-chrome"]), 2)

    def test_repair_groups_by_owner_and_schema_path(self):
        groups = sa.group_repair_errors([
            "C3: buttons.primary: missing radius",
            "C3: buttons.secondary: missing radius",
            "C4: section-copy.yaml: unknown top-level key(s) ['brand']",
            "C20: card-grid pattern 'cards-a' records no grid-equalization stance",
        ])
        indexed = {(g.owner, g.schema_path): len(g.errors) for g in groups}
        self.assertEqual(indexed[("foundation", "/buttons")], 2)
        self.assertEqual(indexed[("copy-chrome", "/")], 1)
        self.assertEqual(
            indexed[("patterns-recipes", "/patterns/cards-a/contentShape")], 1)

    def test_repair_bundle_is_fragment_and_spec_scoped(self):
        files = golden_files()
        files["brand.yaml"] = yaml.safe_dump({
            "brand": {"name": "Fixture", "snapshot": {"value": SNAPSHOT}},
            "tokens": {"motion": {"durations": {"fast": "100ms"}}},
            "blocks": {},
            "buttons": {"primary": {"style": "filled"}},
            "unrelatedHugeBranch": {"secret": "do-not-send"},
        })
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            for name, text in files.items():
                (lane / name).write_text(text)
            group = sa.group_repair_errors([
                "C3: buttons.primary: missing radius, a state fact"])[0]
            bundle = sa.build_repair_bundle(lane, group)
            encoded = json.dumps(bundle)
        self.assertIn("buttons", encoded)
        self.assertNotIn("unrelatedHugeBranch", encoded)
        self.assertNotIn("do-not-send", encoded)
        self.assertIn("10.2 `buttons:", encoded)
        self.assertNotIn("FILLED-IN WoodWave example", encoded)
        self.assertNotIn("domSections", encoded)
        self.assertNotIn("rawHtml", encoded)

    def test_repair_cap_splits_multi_error_group(self):
        files = golden_files()
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            for name, text in files.items():
                (lane / name).write_text(text)
            errors = tuple(
                f"C3: buttons.primary: missing fact {i} " + ("x" * 21_000)
                for i in range(4)
            )
            groups = sa.split_repair_group_to_cap(
                lane, sa.RepairGroup("foundation", "/buttons", errors))
            sizes = [
                sa._input_size(
                    sa._repair_system(group),
                    sa._repair_prompt(sa.build_repair_bundle(lane, group)))
                for group in groups
            ]
        self.assertGreater(len(groups), 1)
        self.assertTrue(all(size <= sa.REPAIR_INPUT_CAP_BYTES for size in sizes))

    def test_repair_patch_validation_is_atomic_and_path_bounded(self):
        files = golden_files()
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            for name, text in files.items():
                (lane / name).write_text(text)
            before = (lane / "brand.yaml").read_text()
            group = sa.RepairGroup(
                "foundation", "/buttons", ("C3: buttons.primary invalid",))
            raw = patch_response([
                {"file": "brand.yaml", "op": "merge", "path": "/buttons",
                 "value": {"primary": {"radius": "4px"}}},
                {"file": "brand.yaml", "op": "remove", "path": "/blocks"},
            ])
            with self.assertRaisesRegex(ab.AuthorBlocked, "outside group scope"):
                sa.parse_and_apply_repair(lane, group, raw)
            after = (lane / "brand.yaml").read_text()
        self.assertEqual(before, after)

    def test_repair_accepts_fenced_json_but_rejects_invalid_layout_shape(self):
        files = golden_files()
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            for name, text in files.items():
                (lane / name).write_text(text)
            button_group = sa.RepairGroup(
                "foundation", "/buttons", ("C3: buttons.primary invalid",))
            touched = sa.parse_and_apply_repair(
                lane, button_group,
                "```json\n" + patch_response([{
                    "file": "brand.yaml", "op": "merge", "path": "/buttons",
                    "value": {"primary": {"radius": "4px"}},
                }]) + "\n```")
            self.assertEqual(touched, ["brand.yaml"])
            before = (lane / "brand.yaml").read_text()
            layouts_group = sa.RepairGroup(
                "foundation", "/layouts", ("C11: layout invalid",))
            with self.assertRaisesRegex(ab.AuthorBlocked, "layouts must be a list"):
                sa.parse_and_apply_repair(
                    lane, layouts_group, patch_response([{
                        "file": "brand.yaml", "op": "replace", "path": "/layouts",
                        "value": {"-": {"id": "bad"}},
                    }]))
            self.assertEqual(before, (lane / "brand.yaml").read_text())

    def test_path_repair_checkpoint_and_resume_skips_valid_stages(self):
        files = golden_files()
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            ab.atomic_write_group(lane, {
                **files,
                "brand.md": "# Fixture\n",
                "style-scale.yaml": "schemaVersion: style-scale.v1\n",
            })
            checkpoint = {
                "schemaVersion": "brand-author-stages.v1",
                "stages": {
                    stage.name: sa._stage_record(
                        stage, "completed", inputBytes=1, durationS=0)
                    for stage in sa.STAGES
                },
            }
            (lane / sa.CHECKPOINT).write_text(json.dumps(checkpoint))
            validations = {"n": 0}

            def validate(_):
                validations["n"] += 1
                return Report(
                    ["C3: buttons.primary: missing radius"]
                    if validations["n"] <= 2 else [])

            provider = FixtureProvider([
                patch_response([{
                    "file": "brand.yaml", "op": "merge", "path": "/buttons",
                    "value": {"primary": {
                        "style": "filled", "bg": "#000", "fg": "#fff",
                        "radius": "4px", "focus": "visible",
                    }},
                }])
            ])
            result = ab.author_brand(
                lane, provider=provider, validator=validate, max_repairs=2)
            saved = json.loads((lane / sa.CHECKPOINT).read_text())
        self.assertTrue(result.ok)
        self.assertEqual(provider.calls, 1)
        repair = saved["stages"]["foundation"]["pathRepairs"][-1]
        self.assertEqual(repair["status"], "completed")
        self.assertLess(repair["inputBytes"], sa.REPAIR_INPUT_CAP_BYTES)

    def test_hard_timeout_uses_child_process_boundary(self):
        original = subprocess.run
        subprocess.run = lambda *a, **k: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(a[0], k["timeout"]))
        try:
            with self.assertRaisesRegex(TimeoutError, "hard timeout"):
                sa.child_provider_call(
                    model="fixture", reasoning_effort="none", system="s", user="u",
                    max_tokens=10, timeout=0.01)
        finally:
            subprocess.run = original

    def test_stage_shape_validation_precedes_install(self):
        with self.assertRaisesRegex(ab.AuthorBlocked, "required stage keys"):
            sa.validate_stage_files({"brand.yaml": "brand: {name: Fixture}\n"})

    def test_legacy_scalar_brand_is_normalized_before_install(self):
        files = {"brand.yaml": yaml.safe_dump({
            "brand": "fixture-brand", "tokens": {}, "blocks": {}})}
        with self.assertRaisesRegex(ab.AuthorBlocked, "snapshot"):
            sa.validate_stage_files(files)

    def test_canonical_brand_mapping_is_preserved(self):
        identity = {
            "name": "Fixture", "sourceUrl": "https://example.test",
            "snapshot": {"value": SNAPSHOT},
        }
        files = {"brand.yaml": yaml.safe_dump({
            "brand": identity, "tokens": {}, "blocks": {}})}
        sa.validate_stage_files(files)
        self.assertEqual(yaml.safe_load(files["brand.yaml"])["brand"], identity)

    def test_malformed_brand_identity_types_fail_clearly(self):
        for malformed in (None, 7, ["Fixture"], {}):
            with self.subTest(malformed=malformed):
                files = {"brand.yaml": yaml.safe_dump({
                    "brand": malformed, "tokens": {}, "blocks": {}})}
                with self.assertRaisesRegex(
                        ab.AuthorBlocked, "brand.*(?:mapping|name)"):
                    sa.validate_stage_files(files)

    def test_foundation_rejects_noncanonical_blocks_list(self):
        files = {"brand.yaml": yaml.safe_dump({
            "brand": {"name": "Fixture", "snapshot": {"value": SNAPSHOT}}, "tokens": {},
            "blocks": [{"id": "legacy-block"}]})}
        with self.assertRaisesRegex(
                ab.AuthorBlocked, "blocks.*contract-keyed mapping"):
            sa.validate_stage_files(files)

    def test_projection_normalizes_legacy_brand_and_c1_sees_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            lane = Path(td)
            make_bundle(lane)
            (lane / "brand.yaml").write_text(yaml.safe_dump({
                "brand": {"name": "Fixture", "snapshot": {"value": SNAPSHOT}},
                "tokens": {"type": {}, "spacing": {}},
                "blocks": [{
                    "id": "legacy-block",
                    "value": {"archetype": "fixture"},
                    "source": "creation",
                }],
                "layouts": [],
            }))
            (lane / "brand-chrome.yaml").write_text(
                "navbar: {links: []}\nfooter: {columns: []}\n")
            (lane / "media-guidance.yaml").write_text(yaml.safe_dump({
                "schemaVersion": "media-guidance.v1",
                "photographyFingerprint": {
                    "notObserved": True, "reason": "fixture"},
                "tagRules": {},
            }))
            (lane / "voice-facts.yaml").write_text(
                "schemaVersion: voice-facts.v1\n")

            def derive(path):
                from render_brand_md import render
                doc = yaml.safe_load((Path(path) / "brand.yaml").read_text())
                ab.atomic_write_group(Path(path), {
                    "brand.md": render(doc, brand_dir=path),
                    "style-scale.yaml": "schemaVersion: style-scale.v1\n",
                })

            sa._run_projections(lane, derive)
            projected = yaml.safe_load((lane / "brand.yaml").read_text())
            self.assertEqual(
                projected["brand"], {"name": "Fixture", "snapshot": {"value": SNAPSHOT}})
            self.assertTrue((lane / "brand.md").is_file())
            report = vbe.validate_brand_dir(
                lane, contracts_path=lane / "missing-contracts.yaml",
                allow_no_vision=True, smoke=False)
            self.assertEqual(
                [error for error in report.errors
                 if error.split(":", 1)[0] == "C1"], [])

    def test_checkpoint_and_stage_telemetry_are_persisted(self):
        files = golden_files()
        original = ab._derive_outputs
        ab._derive_outputs = lambda lane: ab.atomic_write_group(Path(lane), {
            "brand.md": "# Fixture\n",
            "style-scale.yaml": "schemaVersion: style-scale.v1\n",
        })
        try:
            with tempfile.TemporaryDirectory() as td:
                lane = Path(td)
                make_bundle(lane)
                result = ab.author_brand(
                    lane, provider=FixtureProvider(grouped_responses(files)),
                    validator=lambda _: Report())
                checkpoint = json.loads((lane / sa.CHECKPOINT).read_text())
                report = json.loads((lane / ab.AUTHOR_REPORT).read_text())
            self.assertTrue(result.ok)
            self.assertEqual(checkpoint["stages"]["foundation"]["status"], "completed")
            self.assertGreater(checkpoint["stages"]["foundation"]["inputBytes"], 0)
            self.assertEqual(report["stages"][-1]["model"], "deterministic")
            self.assertEqual(report["usage"]["input_tokens"], 40)
        finally:
            ab._derive_outputs = original


if __name__ == "__main__":
    unittest.main()
