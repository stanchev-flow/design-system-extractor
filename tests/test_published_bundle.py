"""Tests for publishing a run's final results as a tracked, browsable bundle.

Covers `tools/publish_run_bundle.py` (what gets exported, and the asset-reference
rewriting that makes a relocated bundle browse from anywhere) plus the Studio-side
discovery in `studio_server.published_bundles()` / `published_links()`.

Everything must stay generic over brand/run: the fixtures below use an invented
brand with invented lane content, and nothing in the assertions depends on a real
run existing on disk.
"""

import json
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import studio_server

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import publish_run_bundle as prb  # noqa: E402


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class SyntheticRun:
    """A minimal run tree with the three asset-reference styles a real run uses.

    The gate-evidence inputs (flow report, flow log, manifest claims, replica report)
    are parameters, so the status disclosure can be exercised for a crashed run, a
    clean run, and a run whose logs say nothing conclusive.
    """

    def __init__(
        self,
        root: Path,
        name: str = "acme-co",
        *,
        manifest_extra: dict | None = None,
        replica_report: dict | None = None,
        flow_report: dict | None = None,
        flow_log: str | None = None,
    ):
        self.run_dir = root / "runs" / name
        self.brand = self.run_dir / "brand"
        manifest = {"brand": "Acme", "source_url": "https://acme.test/", **(manifest_extra or {})}
        _write(self.run_dir / "manifest.json", json.dumps(manifest))
        if flow_report is not None:
            _write(self.brand / "flow-report.json", json.dumps(flow_report))
        if flow_log is not None:
            _write(self.run_dir / "flow-g1g5.log", flow_log)
        _write(self.run_dir / "studio-project.json", json.dumps({"title": "Acme Co"}))
        _write(self.run_dir / "changes.md", "# acme-co\n")
        _write(self.run_dir / "build.log", "ok\n")

        for holder in (self.brand, self.brand / "harness" / "layouts", self.brand / "compose" / "replica"):
            _write(holder / "assets" / "hero.png", "PNGDATA")
        _write(self.brand / "assets" / "logo.svg", "<svg/>")
        _write(self.brand / "assets" / "unused.png", "NOTREFERENCED")

        # Replica: sibling-relative refs, one of them an external URL that must survive.
        _write(
            self.brand / "compose" / "replica" / "index.html",
            '<html><head><title>stale</title></head><body><img src="assets/hero.png">'
            '<img src="https://cdn.acme.test/assets/remote.png">'
            '<div style="background:url(assets/logo.svg)"></div></body></html>',
        )
        _write(
            self.brand / "compose" / "replica" / "replica-report.json",
            json.dumps(replica_report if replica_report is not None else {"overall": 0.42}),
        )
        _write(self.brand / "compose" / "replica" / "replica-report.md", "# report\n")

        # Harness: an index plus a nested layout page (a deeper relative prefix).
        _write(self.brand / "harness" / "index.html", '<html><body><iframe src="layouts/hero.html"></iframe></body></html>')
        _write(self.brand / "harness" / "layouts" / "hero.html", '<html><body><img src="assets/hero.png"></body></html>')

        # Framework build: run-ABSOLUTE refs, which break the moment the page moves.
        _write(
            self.brand / "framework" / "single" / "app" / "dist" / "index.html",
            "<html><head><title>scaffold-name</title></head><body>"
            f'<img src="/runs/{name}/brand/assets/hero.png"></body></html>',
        )
        _write(self.brand / "framework" / "framework-report.json", json.dumps({"status": "completed"}))

        _write(self.brand / "brand.yaml", "brand: Acme\n")
        _write(self.brand / "evidence" / "asset-placements.json", "{}")


class ExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._patch = mock.patch.object(prb, "REPO_ROOT", self.root)
        self._patch.start()
        self.run = SyntheticRun(self.root)
        self.out = self.root / "artifacts" / "published" / "acme-co"
        self.manifest = prb.export(self.run.run_dir, self.out)

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmp.cleanup()

    def test_exports_every_lane_that_exists(self) -> None:
        self.assertEqual(
            [lane["kind"] for lane in self.manifest["lanes"]], ["replica", "harness", "framework"]
        )
        for lane in self.manifest["lanes"]:
            self.assertTrue((self.out / lane["path"]).is_file(), lane["path"])
        for entry in ("index.html", "pipeline.html", "README.md", "published.json"):
            self.assertTrue((self.out / entry).is_file(), entry)

    def test_relative_refs_are_repointed_at_the_bundle_asset_pool(self) -> None:
        replica = (self.out / "replica" / "index.html").read_text()
        self.assertIn('src="../assets/hero.png"', replica)
        self.assertIn("url(../assets/logo.svg)", replica)
        # Depth is per-page, so a nested layout gets a deeper prefix.
        self.assertIn(
            'src="../../assets/hero.png"', (self.out / "harness" / "layouts" / "hero.html").read_text()
        )

    def test_run_absolute_refs_survive_relocation(self) -> None:
        # The generated site sits at the bundle ROOT, so its prefix is bare
        # `assets/` — re-derived from where the page lands, not the framework/ depth
        # it used to be written at.
        site = (self.out / "index.html").read_text()
        self.assertIn('src="assets/hero.png"', site)
        self.assertNotIn("/runs/acme-co/", site)
        self.assertNotIn("../assets/hero.png", site)

    def test_third_party_urls_are_left_alone(self) -> None:
        self.assertIn(
            'src="https://cdn.acme.test/assets/remote.png"',
            (self.out / "replica" / "index.html").read_text(),
        )

    def test_only_referenced_media_ships_and_is_deduped(self) -> None:
        published = sorted(p.name for p in (self.out / "assets").iterdir())
        self.assertEqual(published, ["hero.png", "logo.svg"])
        self.assertEqual(self.manifest["assets_published"], 2)
        self.assertEqual(self.manifest["assets_unresolved"], [])

    def test_headline_fidelity_comes_from_the_report_beside_the_page(self) -> None:
        self.assertEqual(self.manifest["replica_overall"], 0.42)

    def test_relocated_pages_get_an_honest_title(self) -> None:
        self.assertIn("<title>Acme — composed replica</title>", (self.out / "replica" / "index.html").read_text())
        # The site is titled with the brand alone: it is the deliverable, not a lane.
        site = (self.out / "index.html").read_text()
        self.assertIn("<title>Acme</title>", site)
        self.assertNotIn("scaffold-name", site)

    def test_logs_and_facts_travel_with_the_bundle(self) -> None:
        self.assertTrue((self.out / "logs" / "changes.md").is_file())
        self.assertTrue((self.out / "logs" / "build.log").is_file())
        self.assertTrue((self.out / "brand" / "brand.yaml").is_file())
        self.assertTrue((self.out / "brand" / "asset-placements.json").is_file())

    def test_re_export_is_idempotent_and_drops_stale_files(self) -> None:
        # The entry points carry the export timestamp, so they are compared for
        # existence elsewhere; everything that is payload must be byte-identical.
        timestamped = ("published.json", "pipeline.html", "README.md")
        stale = self.out / "harness" / "layouts" / "removed-upstream.html"
        stale.write_text("<html></html>", encoding="utf-8")
        before = {
            p.relative_to(self.out): p.read_bytes()
            for p in self.out.rglob("*")
            if p.is_file() and p.name not in timestamped and p != stale
        }
        prb.export(self.run.run_dir, self.out)
        after = {
            p.relative_to(self.out): p.read_bytes()
            for p in self.out.rglob("*")
            if p.is_file() and p.name not in timestamped
        }
        self.assertEqual(before, after)
        self.assertFalse(stale.exists())


class FrontPageTests(unittest.TestCase):
    """The bundle leads with the generated site; the process is one link away."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._patch = mock.patch.object(prb, "REPO_ROOT", self.root)
        self._patch.start()
        self.published = self.root / "artifacts" / "published"

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmp.cleanup()

    def _publish(self, name: str = "acme-co", **kwargs) -> tuple[dict, Path]:
        run = SyntheticRun(self.root, name, **kwargs)
        out = self.published / name
        return prb.export(run.run_dir, out), out

    def test_the_bundle_front_page_is_the_generated_site(self) -> None:
        manifest, out = self._publish()
        self.assertEqual(manifest["site"], {"kind": "framework", "path": "index.html", "source": mock.ANY})
        site = (out / "index.html").read_text()
        # The site's own markup, not a review page: no artifact tables, no status block.
        self.assertIn('src="assets/hero.png"', site)
        self.assertNotIn("Rendered results", site)
        self.assertNotIn('class="status', site)

    def test_the_site_carries_one_provenance_line_that_reaches_the_disclosure(self) -> None:
        _, out = self._publish(flow_log=CRASHED_FLOW_LOG)
        site = (out / "index.html").read_text()
        self.assertEqual(site.count('id="published-provenance"'), 1)
        self.assertIn("did not pass its own quality gates", site)
        self.assertIn('href="pipeline.html"', site)
        # A footnote, not a banner, and never a claim of approval.
        self.assertLess(site.index("<footer"), site.index("</body>"))
        for forbidden in ("certified", "verified", "approved"):
            self.assertNotIn(forbidden, site.lower())
        # The footer is styled inline so it cannot inherit (or fight) the app's CSS.
        # Those styles go in a style="…" attribute, so a double quote anywhere in
        # them would close the attribute early and spill CSS into the page.
        for inline in (prb._PROV_BOX, prb._PROV_LINK):
            self.assertNotIn('"', inline)
        self.assertIn(f'style="{prb._PROV_BOX}"', site)
        # The footer follows the app's mount node, which scaffolds pin to the
        # viewport height — without this the footer renders mid-document, under
        # the app's own overflowing content.
        self.assertIn(f"<style>{prb._PROV_RESET}</style>", site)
        self.assertIn("height:auto", prb._PROV_RESET)

    def test_the_provenance_line_tracks_the_verdict_it_was_given(self) -> None:
        # One run dir per case: gate evidence is read off disk, so a shared run would
        # let one case's flow report decide the next case's verdict.
        for name, kwargs, expected in (
            ("crashed-co", {"flow_log": CRASHED_FLOW_LOG}, "did not pass its own quality gates"),
            (
                "clean-co",
                {"flow_report": PASSING_FLOW_REPORT, "replica_report": {"overall": 0.93, "bands": []}},
                "passed its own quality gates",
            ),
            ("quiet-co", {"flow_log": "[flow] G1 extraction …\n[flow] G1 PASS\n"}, "could not be determined"),
        ):
            with self.subTest(expected=expected):
                _, out = self._publish(name, **kwargs)
                self.assertIn(expected, (out / "index.html").read_text())

    def test_the_details_page_keeps_everything_that_was_on_the_old_landing(self) -> None:
        _, out = self._publish(flow_log=CRASHED_FLOW_LOG)
        details = (out / "pipeline.html").read_text()
        for section in ("Rendered results", "Brand facts", "logs &amp; manifest", 'class="status'):
            self.assertIn(section, details)
        # And it points back at the site and at the other brands.
        self.assertIn('href="index.html"', details)
        self.assertIn('href="../brands.html"', details)

    def test_a_run_with_no_generated_site_still_opens_on_something(self) -> None:
        run = SyntheticRun(self.root, "acme-co")
        shutil.rmtree(run.brand / "framework")
        manifest = prb.export(run.run_dir, self.published / "acme-co")
        self.assertIsNone(manifest["site"])
        index = (self.published / "acme-co" / "index.html").read_text()
        self.assertIn("Rendered results", index)
        self.assertEqual(index, (self.published / "acme-co" / "pipeline.html").read_text())

    def test_the_published_root_serves_the_site_at_its_own_depth(self) -> None:
        _, out = self._publish()
        root_index = (self.published / "index.html").read_text()
        # Same page, one directory up: the asset prefix is re-derived, not inherited.
        self.assertIn('src="acme-co/assets/hero.png"', root_index)
        self.assertNotIn('src="assets/hero.png"', root_index)
        self.assertIn('href="acme-co/pipeline.html"', root_index)
        self.assertIn("<title>Acme</title>", root_index)

    def test_third_party_urls_survive_the_second_relocation(self) -> None:
        # The re-path only moves names that exist in the pool it is pointed at.
        text, hits = prb.repoint_assets(
            '<img src="https://cdn.acme.test/assets/remote.png"><img src="assets/hero.png">'
            '<img src="assets/never-published.png">',
            self.root / "pool",
            self.root / "page.html",
        )
        (self.root / "pool").mkdir()
        (self.root / "pool" / "hero.png").write_text("PNG")
        text, hits = prb.repoint_assets(text, self.root / "pool", self.root / "page.html")
        self.assertIn('src="https://cdn.acme.test/assets/remote.png"', text)
        self.assertIn('src="pool/hero.png"', text)
        self.assertIn('src="assets/never-published.png"', text)
        self.assertEqual(hits, 1)

    def test_the_root_leads_with_the_newest_brand_and_keeps_the_others_reachable(self) -> None:
        self._publish("acme-co")
        self._publish("zeta-labs")
        for name, when in (("acme-co", "2026-01-01T00:00:00Z"), ("zeta-labs", "2026-06-01T00:00:00Z")):
            path = self.published / name / "published.json"
            data = json.loads(path.read_text())
            data["published_at"] = when
            path.write_text(json.dumps(data))
        prb.write_published_index(self.published)

        root_index = (self.published / "index.html").read_text()
        self.assertIn('src="zeta-labs/assets/hero.png"', root_index)
        self.assertIn('href="zeta-labs/pipeline.html"', root_index)
        # With a second brand on disk the root gains its one extra way out.
        self.assertIn('href="brands.html"', root_index)
        brands = (self.published / "brands.html").read_text()
        for name in ("acme-co", "zeta-labs"):
            self.assertIn(f'href="{name}/index.html"', brands)
            self.assertIn(f'href="{name}/pipeline.html"', brands)

    def test_a_lone_brand_gets_no_pointless_brand_switcher_link(self) -> None:
        self._publish()
        self.assertNotIn('href="brands.html"', (self.published / "index.html").read_text())
        self.assertTrue((self.published / "brands.html").is_file())

    def test_stamping_the_provenance_footer_twice_leaves_one(self) -> None:
        page = "<html><body><p>hi</p></body></html>"
        once = prb.stamp_provenance(page, prb.provenance_footer({}, "pipeline.html"))
        twice = prb.stamp_provenance(once, prb.provenance_footer({}, "pipeline.html"))
        self.assertEqual(twice.count('id="published-provenance"'), 1)
        self.assertEqual(prb.stamp_provenance(twice, prb.provenance_footer({}, "pipeline.html")), twice)


class LocalPathRedactionTests(unittest.TestCase):
    """A committed bundle must not name the machine that produced it."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._patch = mock.patch.object(prb, "REPO_ROOT", self.root)
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmp.cleanup()

    def test_the_repo_prefix_goes_and_the_rest_of_the_path_stays(self) -> None:
        line = f"ERROR at {self.root}/runs/acme/brand/x.yaml:12: bad value"
        self.assertEqual(
            prb.redact_local_paths(line), "ERROR at <repo>/runs/acme/brand/x.yaml:12: bad value"
        )

    def test_file_urls_and_json_values_are_reached_without_breaking_them(self) -> None:
        payload = json.dumps({"page": f"file://{self.root}/artifacts/out/index.html", "ok": True})
        restored = json.loads(prb.redact_local_paths(payload))
        self.assertEqual(restored, {"page": "file://<repo>/artifacts/out/index.html", "ok": True})

    def test_a_home_path_outside_the_repo_is_redacted_too(self) -> None:
        with mock.patch.object(prb.Path, "home", staticmethod(lambda: self.root / "home")):
            prb.REPO_ROOT = self.root / "home" / "work" / "repo"
            text = f"cache {self.root}/home/Library/Caches/x and src {self.root}/home/work/repo/tools/y.py"
            # Longest prefix first: the in-repo path must not be half-rewritten.
            self.assertEqual(
                prb.redact_local_paths(text), "cache <home>/Library/Caches/x and src <repo>/tools/y.py"
            )

    def test_exported_logs_and_reports_carry_no_local_paths(self) -> None:
        run = SyntheticRun(self.root)
        _write(run.run_dir / "build.log", f"wrote {self.root}/runs/acme-co/brand/framework/dist/index.html\n")
        _write(
            run.brand / "framework" / "framework-report.json",
            json.dumps({"out": f"{self.root}/runs/acme-co/brand/framework/single/app"}),
        )
        out = self.root / "artifacts" / "published" / "acme-co"
        prb.export(run.run_dir, out)
        offenders = [
            str(p.relative_to(out))
            for p in out.rglob("*")
            if p.is_file() and p.suffix.lower() in prb.TEXT_SUFFIXES and str(self.root) in p.read_text(errors="replace")
        ]
        self.assertEqual(offenders, [])
        self.assertIn("<repo>/runs/acme-co/", (out / "logs" / "build.log").read_text())
        report = json.loads((out / "framework" / "framework-report.json").read_text())
        self.assertEqual(report["out"], "<repo>/runs/acme-co/brand/framework/single/app")


CRASHED_FLOW_LOG = """[flow] G1 extraction …
[flow] G1 PASS
[flow] G2 validation …
[flow] G2 PASS
[flow] G3 harness …
Traceback (most recent call last):
  File "run_pipeline_flow.py", line 218, in <module>
    sys.exit(main())
RuntimeError: render_components_preview failed (exit 1): Traceback (most recent call last):
  File "brand_pipeline/render_components_preview.py", line 3365, in main
    raise RuntimeError("harness quality failed:
"""

PASSING_FLOW_REPORT = {
    "schemaVersion": "pipeline-flow.v1",
    "status": "completed",
    "ok": True,
    "generationAllowed": True,
    "blockedGate": None,
    "replicaBar": 0.9,
    "gates": [{"gate": g, "ok": True, "status": "pass", "reason": ""} for g in ("G1", "G2", "G3", "G4")],
}


class StatusDisclosureTests(unittest.TestCase):
    """The bundle has to state what the run's own gates said, from evidence on disk."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._patch = mock.patch.object(prb, "REPO_ROOT", self.root)
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmp.cleanup()

    def _publish(self, **kwargs) -> tuple[dict, str, str]:
        run = SyntheticRun(self.root, **kwargs)
        out = self.root / "artifacts" / "published" / run.run_dir.name
        manifest = prb.export(run.run_dir, out)
        # The disclosure lives on the details page now; its wording is unchanged.
        return manifest, (out / "pipeline.html").read_text(), (out / "README.md").read_text()

    def test_crashed_run_is_disclosed_with_the_gate_it_died_on(self) -> None:
        manifest, page, readme = self._publish(
            manifest_extra={
                "status": "completed",
                "pipeline_run_completed": True,
                "replica": {"overall": 0.82, "bar": 0.9},
            },
            replica_report={
                "overall": 0.7437,
                "bands": [
                    {"id": "sec-0", "label": "navbar — chrome", "score": 0.0, "srcHeight": 0},
                    {"id": "sec-1", "label": "featureGrid — invented copy", "score": 0.2783, "srcHeight": 132},
                    {"id": "sec-2", "label": "footer — links", "score": 0.94, "srcHeight": 600},
                ],
            },
            flow_log=CRASHED_FLOW_LOG,
        )
        status = manifest["status"]
        self.assertEqual(status["verdict"], "not-passed")
        self.assertFalse(status["flow_report"]["present"])
        self.assertEqual((status["gate_outcome"]["state"], status["gate_outcome"]["gate"]), ("crashed", "G3"))
        self.assertIn("harness quality failed", status["gate_outcome"]["reason"])
        self.assertEqual(status["fidelity"]["overall"], 0.7437)
        self.assertIs(status["fidelity"]["meets_bar"], False)
        # A band with no source height to diff against is counted, never ranked.
        self.assertEqual([b["id"] for b in status["fidelity"]["bands_below_bar"]], ["sec-1"])
        self.assertEqual(status["fidelity"]["bands_unmeasurable"], ["sec-0"])
        self.assertEqual(len(status["manifest_disagreements"]), 2)
        for rendered in (page, readme):
            self.assertIn("did not pass its own quality gates", rendered)
            self.assertIn("crashed at gate G3", rendered)
            self.assertIn("0.7437", rendered)
            self.assertIn("0.90 bar", rendered)
            self.assertIn("0.82", rendered)  # the stale manifest score, named as stale

    def test_status_block_precedes_the_artifact_links(self) -> None:
        _, page, _ = self._publish(flow_log=CRASHED_FLOW_LOG)
        self.assertLess(page.index('class="status'), page.index("Rendered results"))

    def test_passing_run_says_so_instead_of_inventing_a_problem(self) -> None:
        manifest, page, readme = self._publish(
            flow_report=PASSING_FLOW_REPORT,
            replica_report={"overall": 0.93, "bands": [{"id": "sec-0", "score": 0.95, "srcHeight": 400}]},
        )
        status = manifest["status"]
        self.assertEqual(status["verdict"], "passed")
        self.assertTrue(status["flow_report"]["present"])
        self.assertEqual(status["gate_outcome"]["state"], "completed")
        self.assertIs(status["fidelity"]["meets_bar"], True)
        self.assertEqual(status["fidelity"]["bar_source"], "brand/flow-report.json")
        self.assertEqual(status["manifest_disagreements"], [])
        for rendered in (page, readme):
            self.assertIn("passed its own quality gates", rendered)
            self.assertIn("cleared every gate (G1, G2, G3, G4)", rendered)
            self.assertIn("the bar is met", rendered)
            self.assertNotIn("did not pass", rendered)
        self.assertIn('class="status ok"', page)

    def test_blocked_gate_from_the_flow_report_is_reported_as_not_passed(self) -> None:
        manifest, page, _ = self._publish(
            flow_report={
                **PASSING_FLOW_REPORT,
                "status": "blocked",
                "ok": False,
                "blockedGate": "G4",
                "gates": [{"gate": "G4", "ok": False, "status": "fail", "reason": "replica 0.71 below 0.90 bar"}],
            },
            replica_report={"overall": 0.71, "bands": []},
        )
        self.assertEqual(manifest["status"]["verdict"], "not-passed")
        self.assertIn("stopped at gate G4: replica 0.71 below 0.90 bar", page)

    def test_inconclusive_logs_say_so_rather_than_claiming_a_pass(self) -> None:
        manifest, page, _ = self._publish(flow_log="[flow] G1 extraction …\n[flow] G1 PASS\n")
        status = manifest["status"]
        self.assertEqual(status["verdict"], "undetermined")
        self.assertFalse(status["gate_outcome"]["determined"])
        self.assertIn("could not be determined from run logs", page)
        self.assertIn('class="status unknown"', page)

    def test_a_foreign_flow_report_in_an_archive_never_certifies_this_run(self) -> None:
        run = SyntheticRun(self.root, flow_log=CRASHED_FLOW_LOG)
        _write(run.run_dir / "_archive" / "brand-copied-from-elsewhere" / "flow-report.json", json.dumps(PASSING_FLOW_REPORT))
        manifest = prb.export(run.run_dir, self.root / "artifacts" / "published" / "acme-co")
        self.assertEqual(manifest["status"]["verdict"], "not-passed")
        self.assertFalse(manifest["status"]["flow_report"]["present"])

    def test_a_stale_manifest_score_is_flagged_even_when_gates_passed(self) -> None:
        manifest, _, _ = self._publish(
            flow_report=PASSING_FLOW_REPORT,
            manifest_extra={"replica": {"overall": 0.99, "bar": 0.9}},
            replica_report={"overall": 0.93, "bands": []},
        )
        self.assertEqual(manifest["status"]["verdict"], "passed")
        self.assertEqual(len(manifest["status"]["manifest_disagreements"]), 1)
        self.assertIn("predates the replica that is published here", manifest["status"]["manifest_disagreements"][0])


class ForeignStringScanTests(unittest.TestCase):
    """Cross-brand and scaffold leakage is reported, with benign hits kept separate."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._patch = mock.patch.object(prb, "REPO_ROOT", self.root)
        self._patch.start()
        (self.root / "runs" / "woodwave-v2").mkdir(parents=True)
        (self.root / "runs" / "zeta-labs-3").mkdir(parents=True)

    def tearDown(self) -> None:
        self._patch.stop()
        self._tmp.cleanup()

    def _scan(self, files: dict[str, str], assets: tuple[str, ...] = ()) -> list[dict]:
        out = self.root / "bundle"
        for name in assets:
            _write(out / "assets" / name, "DATA")
        for rel, text in files.items():
            _write(out / rel, text)
        return prb.scan_foreign_strings(out, "Acme", "acme-co")

    def test_flags_scaffold_defaults_and_other_run_names_in_markup(self) -> None:
        found = self._scan(
            {
                "framework/index.html": "<title>Fieldnote</title><p>built for WoodWave</p>",
                "logs/changes.md": "fixed a leaked woodwave offset",
            }
        )
        by_token = {(f["token"], f["kind"], f["file"]) for f in found}
        self.assertIn(("fieldnote", "page", "framework/index.html"), by_token)
        self.assertIn(("woodwave", "page", "framework/index.html"), by_token)
        self.assertIn(("woodwave", "provenance", "logs/changes.md"), by_token)

    def test_separates_comment_leaks_from_visible_markup(self) -> None:
        found = self._scan({"replica/index.html": "<style>/* a WoodWave-era default */</style><p>hello</p>"})
        self.assertEqual([(f["kind"], f["in_comment"]) for f in found], [("page", True)])

    def test_media_filenames_that_contain_a_brand_are_not_leaks(self) -> None:
        found = self._scan(
            {"replica/index.html": '<img src="../assets/040-abc-woodwave-logo.avif">'},
            assets=("040-abc-woodwave-logo.avif",),
        )
        self.assertEqual({f["kind"] for f in found}, {"asset-name"})

    def test_the_published_brand_and_generated_entry_points_are_never_flagged(self) -> None:
        (self.root / "runs" / "acme-co").mkdir(parents=True)
        found = self._scan(
            {
                "replica/index.html": "<h1>Acme</h1><p>acme-co run</p>",
                "pipeline.html": "<p>WoodWave mentioned by the report itself</p>",
                "published.json": '{"token": "woodwave"}',
            }
        )
        self.assertEqual(found, [])


class StudioDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.published = self.root / "artifacts" / "published"
        self._patches = [
            mock.patch.object(studio_server, "PROJECT_DIR", self.root),
            mock.patch.object(studio_server, "PUBLISHED_DIR", self.published),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def _bundle(
        self, name: str, *, published_at: str, run: str | None = None, status: dict | None = None
    ) -> None:
        _write(
            self.published / name / "published.json",
            json.dumps(
                {
                    "name": name,
                    "title": name.title(),
                    "brand": name.title(),
                    "run": run or f"runs/{name}",
                    "published_at": published_at,
                    **({"status": status} if status else {}),
                    "site": {"kind": "framework", "path": "index.html"},
                    "details": "pipeline.html",
                    "bytes": 1024,
                    "lanes": [
                        {"kind": "replica", "label": "Composed replica", "path": "replica/index.html"},
                        {"kind": "invented-kind", "label": "Something new", "path": "other/index.html"},
                    ],
                }
            ),
        )

    def test_discovers_bundles_newest_first(self) -> None:
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z")
        self._bundle("zeta-labs", published_at="2026-06-01T00:00:00Z")
        self.assertEqual([b["name"] for b in studio_server.published_bundles()], ["zeta-labs", "acme-co"])

    def test_lane_urls_are_studio_servable_and_unknown_kinds_degrade(self) -> None:
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z")
        (bundle,) = studio_server.published_bundles()
        self.assertEqual(bundle["url"], "/artifacts/published/acme-co/index.html")
        self.assertEqual(bundle["details_url"], "/artifacts/published/acme-co/pipeline.html")
        self.assertEqual(
            [(l["kind"], l["url"]) for l in bundle["links"]],
            [
                ("replica", "/artifacts/published/acme-co/replica/index.html"),
                ("published", "/artifacts/published/acme-co/other/index.html"),
            ],
        )

    def test_a_bundle_predating_the_details_page_still_resolves_one(self) -> None:
        _write(
            self.published / "old" / "published.json",
            json.dumps({"name": "old", "brand": "Old", "published_at": "2025-01-01T00:00:00Z", "lanes": []}),
        )
        (bundle,) = studio_server.published_bundles()
        self.assertEqual(bundle["details_url"], "/artifacts/published/old/pipeline.html")

    def test_unreadable_manifest_is_skipped_not_fatal(self) -> None:
        _write(self.published / "broken" / "published.json", "{not json")
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z")
        self.assertEqual([b["name"] for b in studio_server.published_bundles()], ["acme-co"])

    def test_project_links_match_on_bundle_name_or_run_dir(self) -> None:
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z", run="runs/acme-co-final")
        self.assertTrue(studio_server.published_links("acme-co"))
        self.assertTrue(studio_server.published_links("acme-co-final"))
        self.assertEqual(studio_server.published_links("someone-else"), [])

    def test_the_sidebar_offers_the_site_and_the_details_page(self) -> None:
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z")
        self.assertEqual(
            [(l["label"], l["url"]) for l in studio_server.published_links("acme-co")],
            [
                ("Published site — Acme-Co (shareable)", "/artifacts/published/acme-co/index.html"),
                ("Published pipeline details — Acme-Co", "/artifacts/published/acme-co/pipeline.html"),
            ],
        )

    def test_dashboard_carries_the_published_run_gate_outcome(self) -> None:
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z", status={"verdict": "not-passed"})
        self._bundle("zeta-labs", published_at="2026-02-01T00:00:00Z", status={"verdict": "passed"})
        self._bundle("nostatus", published_at="2026-03-01T00:00:00Z")
        self.assertEqual(
            {b["name"]: b["verdict"] for b in studio_server.published_bundles()},
            {"acme-co": "not-passed", "zeta-labs": "passed", "nostatus": "undetermined"},
        )
        band = studio_server.render_published_html()
        for text in ("gates not passed", "gates passed", "gates unknown"):
            self.assertIn(text, band)

    def test_dashboard_band_is_hidden_until_something_is_published(self) -> None:
        self.assertEqual(studio_server.render_published_html(), "")
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z")
        band = studio_server.render_published_html()
        self.assertIn("Published results", band)
        self.assertIn("/artifacts/published/acme-co/index.html", band)
        # Both destinations, so local browsing matches what the public site does.
        self.assertIn("/artifacts/published/acme-co/pipeline.html", band)
        self.assertIn("Open site", band)


if __name__ == "__main__":
    unittest.main()
