"""HTTP-level checks for the Studio routes this change touched.

Two behaviours are only observable through a real request:

  * `/project/<unknown>` must answer 404. It used to answer 200 with a fully
    rendered page, so a link pasted from a machine with more runs than yours gave
    a plausible-looking project whose every pane was empty.
  * `/api/rundoc` serves the brand-lane document bodies, which are fetched on
    demand rather than embedded in the project payload.

The server runs against a throwaway tree on an ephemeral port, so this never
touches the user's Studio or depends on which runs exist locally.
"""

import json
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import studio_server


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = TemporaryDirectory()
        cls.project_dir = Path(cls._tmp.name).resolve()
        cls.runs_dir = cls.project_dir / "runs"
        cls.shots_dir = cls.project_dir / "screenshots"
        (cls.runs_dir / ".studio").mkdir(parents=True)
        cls.shots_dir.mkdir(parents=True)

        # One synthetic brand-lane project: no run item, so every OLD document tab
        # is empty — exactly the shape that lost its whole tab row.
        brand = cls.runs_dir / "acme" / "brand"
        brand.mkdir(parents=True)
        (cls.runs_dir / "acme" / "studio-project.json").write_text(json.dumps({"title": "Acme"}))
        (brand / "style-scale.yaml").write_text("type: style_scale\nsteps: [4, 8]\n")
        (brand / "voice.md").write_text("# Voice\n\nPlain and direct.\n")

        # A project directory with nothing generated in it at all: still a project.
        (cls.runs_dir / "thin").mkdir()

        cls._patches = [
            mock.patch.object(studio_server, "PROJECT_DIR", cls.project_dir),
            mock.patch.object(studio_server, "RUNS_DIR", cls.runs_dir),
            mock.patch.object(studio_server, "SCREENSHOTS_DIR", cls.shots_dir),
            mock.patch.object(studio_server, "STUDIO_DIR", cls.runs_dir / ".studio"),
            # Also inside the throwaway tree: the real one holds published bundles
            # for real projects, which the page would try to URL-map against
            # PROJECT_DIR and fail on.
            mock.patch.object(
                studio_server, "PUBLISHED_DIR", cls.project_dir / "artifacts" / "published"
            ),
        ]
        for p in cls._patches:
            p.start()

        cls.server = studio_server.StudioServer(("127.0.0.1", 0), studio_server.StudioHandler)
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=10)
        for p in cls._patches:
            p.stop()
        cls._tmp.cleanup()

    def get(self, path: str) -> tuple[int, str]:
        try:
            with urllib.request.urlopen(self.base + path, timeout=20) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")

    # ── /project/<version> ────────────────────────────────────────────────────
    def test_unknown_project_is_404(self) -> None:
        status, body = self.get("/project/no-such-project")
        self.assertEqual(status, 404)
        self.assertIn("Project not found", body)
        self.assertIn("no-such-project", body)

    def test_404_page_lists_the_projects_that_do_exist(self) -> None:
        _, body = self.get("/project/no-such-project")
        self.assertIn("/project/acme", body)

    def test_existing_project_renders(self) -> None:
        status, body = self.get("/project/acme")
        self.assertEqual(status, 200)
        self.assertIn("Acme", body)

    def test_project_with_almost_no_artifacts_still_renders(self) -> None:
        # The 404 keys off the run directory, never off how complete it is.
        status, _ = self.get("/project/thin")
        self.assertEqual(status, 200)

    def test_traversal_in_a_project_path_is_404(self) -> None:
        status, _ = self.get("/project/..%2f..%2fetc")
        self.assertEqual(status, 404)

    # ── /api/rundoc ───────────────────────────────────────────────────────────
    def test_rundoc_serves_a_resolved_brand_doc(self) -> None:
        status, body = self.get("/api/rundoc?version=acme&doc=brand_ledger")
        self.assertEqual(status, 200)
        self.assertIn("===== brand/style-scale.yaml =====", body)
        self.assertIn("steps: [4, 8]", body)

    def test_rundoc_404s_for_a_doc_that_does_not_exist(self) -> None:
        status, _ = self.get("/api/rundoc?version=acme&doc=brand_grounding")
        self.assertEqual(status, 404)

    def test_rundoc_rejects_an_unknown_key(self) -> None:
        status, _ = self.get("/api/rundoc?version=acme&doc=../../secrets")
        self.assertEqual(status, 400)

    def test_rundoc_404s_for_an_unknown_project(self) -> None:
        status, _ = self.get("/api/rundoc?version=nope&doc=brand_ledger")
        self.assertEqual(status, 404)

    # ── the tab row the project payload advertises ─────────────────────────────
    def test_project_payload_advertises_only_resolvable_brand_docs(self) -> None:
        status, body = self.get("/api/project/acme")
        self.assertEqual(status, 200)
        labels = [d["label"] for d in json.loads(body)["brand_docs"]]
        self.assertEqual(labels, ["Ledger", "Voice"])

    def test_project_payload_omits_brand_doc_bodies(self) -> None:
        # Tabs are metadata only; the evidence dumps behind them are far too big
        # to embed in every project page.
        _, body = self.get("/api/project/acme")
        for doc in json.loads(body)["brand_docs"]:
            self.assertEqual(sorted(doc), ["files", "key", "label"])

    def test_dashboard_still_renders(self) -> None:
        status, _ = self.get("/studio")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
