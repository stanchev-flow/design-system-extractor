"""A "Framework build" link must not silently go nowhere.

The Studio used to register framework builds at hardcoded `localhost:5179`–`5182`
dev-server ports from a seed baked into the source. Those Vite servers exist only
on the machine that built the lane, so on anyone else's clone — and usually
locally too — the links were dead, and clicking one looked like a broken build.

Framework lanes are now resolved from disk evidence, with exactly two honest
outcomes:

  * built output under `runs/<version>/` is served by the Studio as a same-origin
    lane, so it works wherever the run does;
  * a dev-server registration with no built output behind it is presented as a
    required local step (`available: False` + a hint naming the directory), and
    renders as a statement rather than an anchor.

`runs/.studio/framework-builds.json` is gitignored, so its absence is the normal
case and nothing here may depend on it — nor may the server re-create it.
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import studio_server


class FrameworkTreeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.project_dir = Path(self._tmp.name).resolve()
        self.runs_dir = self.project_dir / "runs"
        self.studio_dir = self.runs_dir / ".studio"
        self.registry = self.studio_dir / "framework-builds.json"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        (self.project_dir / "screenshots").mkdir(parents=True, exist_ok=True)
        self._patches = [
            mock.patch.object(studio_server, "PROJECT_DIR", self.project_dir),
            mock.patch.object(studio_server, "RUNS_DIR", self.runs_dir),
            mock.patch.object(studio_server, "SCREENSHOTS_DIR", self.project_dir / "screenshots"),
            mock.patch.object(studio_server, "STUDIO_DIR", self.studio_dir),
            mock.patch.object(studio_server, "FRAMEWORK_BUILDS_REGISTRY", self.registry),
            mock.patch.object(
                studio_server, "PUBLISHED_DIR", self.project_dir / "artifacts" / "published"
            ),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def write(self, rel: str, text: str = "<html>built</html>") -> Path:
        path = self.project_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def register(self, *entries: dict) -> None:
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        self.registry.write_text(json.dumps(list(entries)), encoding="utf-8")


class RegistryTests(FrameworkTreeTestCase):
    """The registry is read-only, optional, and never seeded."""

    def test_absent_registry_is_empty(self) -> None:
        (self.runs_dir / "acme").mkdir()
        self.assertEqual(studio_server._load_framework_registry(), [])

    def test_reading_does_not_create_the_registry(self) -> None:
        # It is gitignored, so a fresh clone has none; writing a seed there is what
        # put the dead dev-server ports in front of every reader.
        studio_server._load_framework_registry()
        self.assertFalse(self.registry.exists())

    def test_unparseable_registry_degrades_to_empty(self) -> None:
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        self.registry.write_text("{not json", encoding="utf-8")
        self.assertEqual(studio_server._load_framework_registry(), [])

    def test_no_framework_lane_without_disk_evidence_or_registration(self) -> None:
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.assertEqual(studio_server.framework_builds("acme"), [])


class BuiltOutputDiscoveryTests(FrameworkTreeTestCase):
    """`framework_build_page()` — what counts as servable built output."""

    def test_published_single_file_build(self) -> None:
        page = self.write("runs/acme/brand/framework/index.html")
        self.assertEqual(studio_server.framework_build_page("acme"), page)

    def test_vite_dist_build(self) -> None:
        page = self.write("runs/acme/brand/framework/dist/index.html")
        self.assertEqual(studio_server.framework_build_page("acme"), page)

    def test_per_app_dist_build(self) -> None:
        page = self.write("runs/acme/brand/framework/single/framework-claude/dist/index.html")
        self.assertEqual(studio_server.framework_build_page("acme"), page)

    def test_old_lane_dist_build(self) -> None:
        page = self.write("runs/acme/acme/single/framework/dist/index.html")
        self.assertEqual(studio_server.framework_build_page("acme"), page)

    def test_vite_source_entry_is_not_built_output(self) -> None:
        # `single/<app>/index.html` is the module-script SOURCE entry: served
        # statically it renders blank, so offering it would be the same silent
        # nowhere by another route.
        self.write(
            "runs/acme/brand/framework/single/framework-claude/index.html",
            '<script type="module" src="/src/main.tsx"></script>',
        )
        self.assertIsNone(studio_server.framework_build_page("acme"))

    def test_zero_byte_build_is_absent(self) -> None:
        self.write("runs/acme/brand/framework/index.html", "")
        self.assertIsNone(studio_server.framework_build_page("acme"))

    def test_no_framework_dir_at_all(self) -> None:
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.assertIsNone(studio_server.framework_build_page("acme"))

    def test_unknown_project_is_none(self) -> None:
        self.assertIsNone(studio_server.framework_build_page("ghost"))

    def test_traversal_is_refused(self) -> None:
        self.assertIsNone(studio_server.framework_build_page("../.."))


class DevHintTests(FrameworkTreeTestCase):
    """What the reader is told when there is no built output."""

    def test_hint_names_the_app_directory_when_the_source_is_here(self) -> None:
        self.write("runs/acme/brand/framework/single/framework-claude/package.json", "{}")
        hint = studio_server.framework_dev_hint("acme")
        self.assertIn("runs/acme/brand/framework/single/framework-claude", hint)
        self.assertIn("npm run", hint)

    def test_dev_dir_is_the_directory_holding_package_json(self) -> None:
        self.write("runs/acme/brand/framework/package.json", "{}")
        self.assertEqual(
            studio_server.framework_dev_dir("acme"),
            self.runs_dir / "acme" / "brand" / "framework",
        )

    def test_hint_says_so_plainly_when_the_directory_is_absent(self) -> None:
        # Nothing under the run holds the app, so the honest answer is that the
        # lane cannot be produced here — not a command that would fail if run.
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        hint = studio_server.framework_dev_hint("acme")
        self.assertIn("runs/acme/", hint)
        self.assertNotIn("npm run", hint)

    def test_hint_does_not_blame_tracking_for_a_locally_absent_app(self) -> None:
        """The three dev-port projects have no framework workspace in this working
        copy either, so "a clone does not carry it" would be a guess that misreads
        the cause. The hint must describe the checkout it is running in."""
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        hint = studio_server.framework_dev_hint("acme")
        self.assertNotIn("tracked", hint)
        self.assertNotIn("clone", hint)


class FrameworkLaneTests(FrameworkTreeTestCase):
    """`framework_builds()` — the two honest states, and no duplicates."""

    def test_built_output_is_served_by_the_studio_with_no_registration(self) -> None:
        self.write("runs/acme/brand/framework/index.html")
        builds = studio_server.framework_builds("acme")
        self.assertEqual(len(builds), 1)
        self.assertEqual(builds[0]["url"], "/runs/acme/brand/framework/index.html")
        self.assertTrue(builds[0]["available"])
        self.assertFalse(builds[0]["external"])

    def test_dev_server_registration_without_a_build_is_not_a_link(self) -> None:
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.register({"version": "acme", "label": "shadcn full page", "url": "http://localhost:5179/"})
        builds = studio_server.framework_builds("acme")
        self.assertEqual(len(builds), 1)
        self.assertEqual(builds[0]["url"], "")
        self.assertFalse(builds[0]["available"])
        self.assertIn("shadcn full page", builds[0]["label"])
        self.assertTrue(builds[0]["hint"])

    def test_registration_pointing_at_this_studio_becomes_a_relative_url(self) -> None:
        # A registration made against `http://127.0.0.1:1500/runs/...` stops
        # resolving the moment the Studio moves port; the same file served
        # same-origin works on whatever port the reader is on.
        self.write("runs/acme/brand/framework/index.html")
        self.register(
            {
                "version": "acme",
                "label": "token skin",
                "url": "http://127.0.0.1:1500/runs/acme/brand/framework/index.html",
            }
        )
        builds = studio_server.framework_builds("acme")
        self.assertEqual(len(builds), 1, builds)
        self.assertEqual(builds[0]["url"], "/runs/acme/brand/framework/index.html")
        self.assertEqual(builds[0]["label"], "Framework build — token skin")

    def test_registration_pointing_at_a_file_that_is_gone_is_not_a_link(self) -> None:
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.register(
            {
                "version": "acme",
                "label": "token skin",
                "url": "http://127.0.0.1:1500/runs/acme/brand/framework/index.html",
            }
        )
        builds = studio_server.framework_builds("acme")
        self.assertEqual([b["available"] for b in builds], [False])

    def test_a_hosted_origin_stays_an_external_link(self) -> None:
        # The defect is a dev server on THIS machine that nobody is running. A
        # deliberately registered hosted preview is somebody else's uptime problem
        # and is not ours to reclassify.
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.register(
            {"version": "acme", "label": "hosted preview", "url": "https://preview.example.com/"}
        )
        builds = studio_server.framework_builds("acme")
        self.assertEqual(builds[0]["url"], "https://preview.example.com/")
        self.assertTrue(builds[0]["available"])
        self.assertTrue(builds[0]["external"])

    def test_a_hosted_origin_is_not_pulled_into_the_lane_dropdown(self) -> None:
        # Another origin cannot be iframed and scaled like a Studio-served lane.
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.register({"version": "acme", "label": "hosted", "url": "https://preview.example.com/"})
        self.assertEqual(studio_server.project_detail("acme")["lanes"], [])

    def test_a_registration_for_another_project_is_ignored(self) -> None:
        self.write("runs/other/brand/framework/index.html")
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.register({"version": "other", "label": "x", "url": "http://localhost:5179/"})
        self.assertEqual(studio_server.framework_builds("acme"), [])

    def test_a_stale_dev_registration_is_dropped_once_a_build_exists(self) -> None:
        # The built page IS the lane; repeating it as an unavailable dev-server row
        # would only tell the reader to start a server they do not need.
        self.write("runs/acme/brand/framework/index.html")
        self.register({"version": "acme", "label": "shadcn", "url": "http://localhost:5179/"})
        builds = studio_server.framework_builds("acme")
        self.assertEqual([b["available"] for b in builds], [True])

    def test_malformed_registry_entries_are_skipped(self) -> None:
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.register("not a dict", {"version": "acme"}, {"version": "acme", "url": "   "})
        self.assertEqual(studio_server.framework_builds("acme"), [])

    def test_no_hardcoded_dev_server_port_is_advertised(self) -> None:
        # Nothing in the module may put a port in front of a reader on its own.
        for version in ("greenhouse-v2", "hubspot-v3", "woodwave-v2", "acme"):
            (self.runs_dir / version).mkdir(parents=True, exist_ok=True)
            self.assertEqual(studio_server.framework_builds(version), [], version)


class FrameworkLanePayloadTests(FrameworkTreeTestCase):
    """How the lane reaches the page: dropdown lane + sidebar row."""

    def test_a_built_lane_joins_the_lane_dropdown(self) -> None:
        self.write("runs/acme/brand/framework/index.html")
        lanes = studio_server.project_detail("acme")["lanes"]
        urls = [l["url"] for l in lanes]
        self.assertIn("/runs/acme/brand/framework/index.html", urls)

    def test_an_unavailable_lane_never_joins_the_lane_dropdown(self) -> None:
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.register({"version": "acme", "label": "shadcn", "url": "http://localhost:5179/"})
        detail = studio_server.project_detail("acme")
        self.assertEqual(detail["lanes"], [])
        self.assertEqual([b["available"] for b in detail["framework_builds"]], [False])

    def test_unavailable_build_link_renders_as_a_statement_not_an_anchor(self) -> None:
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.register({"version": "acme", "label": "shadcn", "url": "http://localhost:5179/"})
        html = studio_server.render_project_builds_html("acme")
        self.assertNotIn("<a ", html)
        self.assertIn("shadcn", html)
        self.assertIn(studio_server.framework_dev_hint("acme"), html)
        self.assertNotIn("5179", html)

    def test_available_build_link_renders_as_an_anchor(self) -> None:
        self.write("runs/acme/brand/framework/index.html")
        html = studio_server.render_project_builds_html("acme")
        self.assertIn('href="/runs/acme/brand/framework/index.html"', html)

    def test_dashboard_client_renderer_makes_the_same_distinction(self) -> None:
        # The dashboard's loadBuildIndex() replaces the server-rendered sidebar as
        # soon as the page loads, so a JS renderer that still emits an anchor would
        # undo this a second after the reader sees it.
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.register({"version": "acme", "label": "shadcn", "url": "http://localhost:5179/"})
        html = studio_server.render_dashboard()
        self.assertIn("l.available === false", html)
        self.assertNotIn("5179", html)

    def test_dev_step_is_named_in_the_row_when_the_source_is_here(self) -> None:
        self.write("runs/acme/brand/framework/single/framework-claude/package.json", "{}")
        self.register({"version": "acme", "label": "shadcn", "url": "http://localhost:5179/"})
        html = studio_server.render_project_builds_html("acme")
        self.assertIn("runs/acme/brand/framework/single/framework-claude", html)
        self.assertNotIn("<a ", html)


if __name__ == "__main__":
    unittest.main()
