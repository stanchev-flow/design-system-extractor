"""Tests for publishing a run's final results as a tracked, browsable bundle.

Covers `tools/publish_run_bundle.py` (what gets exported, and the asset-reference
rewriting that makes a relocated bundle browse from anywhere) plus the Studio-side
discovery in `studio_server.published_bundles()` / `published_links()`.

Everything must stay generic over brand/run: the fixtures below use an invented
brand with invented lane content, and nothing in the assertions depends on a real
run existing on disk.
"""

import json
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
    """A minimal run tree with the three asset-reference styles a real run uses."""

    def __init__(self, root: Path, name: str = "acme-co"):
        self.run_dir = root / "runs" / name
        self.brand = self.run_dir / "brand"
        _write(self.run_dir / "manifest.json", json.dumps({"brand": "Acme", "source_url": "https://acme.test/"}))
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
        _write(self.brand / "compose" / "replica" / "replica-report.json", json.dumps({"overall": 0.42}))
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
        for entry in ("index.html", "README.md", "published.json"):
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
        framework = (self.out / "framework" / "index.html").read_text()
        self.assertIn('src="../assets/hero.png"', framework)
        self.assertNotIn("/runs/acme-co/", framework)

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
        self.assertNotIn("scaffold-name", (self.out / "framework" / "index.html").read_text())

    def test_logs_and_facts_travel_with_the_bundle(self) -> None:
        self.assertTrue((self.out / "logs" / "changes.md").is_file())
        self.assertTrue((self.out / "logs" / "build.log").is_file())
        self.assertTrue((self.out / "brand" / "brand.yaml").is_file())
        self.assertTrue((self.out / "brand" / "asset-placements.json").is_file())

    def test_re_export_is_idempotent_and_drops_stale_files(self) -> None:
        stale = self.out / "harness" / "layouts" / "removed-upstream.html"
        stale.write_text("<html></html>", encoding="utf-8")
        before = {
            p.relative_to(self.out): p.read_bytes()
            for p in self.out.rglob("*")
            if p.is_file() and p.name not in ("published.json", "index.html", "README.md") and p != stale
        }
        prb.export(self.run.run_dir, self.out)
        after = {
            p.relative_to(self.out): p.read_bytes()
            for p in self.out.rglob("*")
            if p.is_file() and p.name not in ("published.json", "index.html", "README.md")
        }
        self.assertEqual(before, after)
        self.assertFalse(stale.exists())


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

    def _bundle(self, name: str, *, published_at: str, run: str | None = None) -> None:
        _write(
            self.published / name / "published.json",
            json.dumps(
                {
                    "name": name,
                    "title": name.title(),
                    "brand": name.title(),
                    "run": run or f"runs/{name}",
                    "published_at": published_at,
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
        self.assertEqual(
            [(l["kind"], l["url"]) for l in bundle["links"]],
            [
                ("replica", "/artifacts/published/acme-co/replica/index.html"),
                ("published", "/artifacts/published/acme-co/other/index.html"),
            ],
        )

    def test_unreadable_manifest_is_skipped_not_fatal(self) -> None:
        _write(self.published / "broken" / "published.json", "{not json")
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z")
        self.assertEqual([b["name"] for b in studio_server.published_bundles()], ["acme-co"])

    def test_project_links_match_on_bundle_name_or_run_dir(self) -> None:
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z", run="runs/acme-co-final")
        self.assertTrue(studio_server.published_links("acme-co"))
        self.assertTrue(studio_server.published_links("acme-co-final"))
        self.assertEqual(studio_server.published_links("someone-else"), [])

    def test_dashboard_band_is_hidden_until_something_is_published(self) -> None:
        self.assertEqual(studio_server.render_published_html(), "")
        self._bundle("acme-co", published_at="2026-01-01T00:00:00Z")
        band = studio_server.render_published_html()
        self.assertIn("Published results", band)
        self.assertIn("/artifacts/published/acme-co/index.html", band)


if __name__ == "__main__":
    unittest.main()
