"""Tests for the Studio brand-surface PAGE discovery/classification.

Covers `studio_server.brand_pages()` and `_lane_thumb()`, which power the
project-view "Pages" section and the /compare/<version> side-by-side view.
The logic must be generic across brands/lanes: the measured REPLICA (lane dir
named "replica") vs harness-GENERATED lanes (everything else with an index.html).
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import studio_server


class BrandPagesDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.project_dir = Path(self._tmp.name)
        self.runs_dir = self.project_dir / "runs"
        # Point the module globals at the throwaway tree for the duration of the
        # test so discovery reads our synthetic lanes, not the real repo.
        self._patches = [
            mock.patch.object(studio_server, "PROJECT_DIR", self.project_dir),
            mock.patch.object(studio_server, "RUNS_DIR", self.runs_dir),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def _compose(self, version: str) -> Path:
        d = self.runs_dir / version / "brand" / "compose"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _lane(self, version: str, lane: str, *, index: bool = True) -> Path:
        d = self._compose(version) / lane
        d.mkdir(parents=True, exist_ok=True)
        if index:
            (d / "index.html").write_text("<html></html>", encoding="utf-8")
        return d

    def test_classifies_replica_vs_generated_generically(self) -> None:
        # Arbitrary brand name + arbitrary lane names — nothing hardcoded.
        self._lane("acme-co", "replica")
        self._lane("acme-co", "campaign-launch")
        self._lane("acme-co", "webinar-signup")

        pages = studio_server.brand_pages("acme-co")

        self.assertIsNotNone(pages["replica"])
        self.assertEqual(pages["replica"]["kind"], "replica")
        self.assertEqual(pages["replica"]["lane"], "replica")
        self.assertEqual(pages["replica"]["label"], "Replica (measured)")
        self.assertEqual(
            pages["replica"]["url"],
            "/runs/acme-co/brand/compose/replica/index.html",
        )

        gen_lanes = {g["lane"] for g in pages["generated"]}
        self.assertEqual(gen_lanes, {"campaign-launch", "webinar-signup"})
        for g in pages["generated"]:
            self.assertEqual(g["kind"], "generated")
            # generated lanes are labeled by their lane name, not "Replica ..."
            self.assertEqual(g["label"], g["lane"])

    def test_lane_without_index_html_is_skipped(self) -> None:
        # A lane whose index.html lives under a nested page/ dir (not a direct
        # compose/<lane>/index.html) is not a browsable top-level page here.
        self._lane("brandx", "replica")
        nested = self._lane("brandx", "event-registration", index=False)
        (nested / "page").mkdir()
        (nested / "page" / "index.html").write_text("<html></html>", encoding="utf-8")

        pages = studio_server.brand_pages("brandx")
        self.assertIsNotNone(pages["replica"])
        self.assertEqual(pages["generated"], [])

    def test_missing_replica_still_lists_generated(self) -> None:
        self._lane("nobrand", "product-launch")
        pages = studio_server.brand_pages("nobrand")
        self.assertIsNone(pages["replica"])
        self.assertEqual([g["lane"] for g in pages["generated"]], ["product-launch"])

    def test_no_compose_dir_degrades_to_empty(self) -> None:
        # Brand exists but never composed anything: no crash, empty lists.
        (self.runs_dir / "empty-brand" / "brand").mkdir(parents=True)
        pages = studio_server.brand_pages("empty-brand")
        self.assertEqual(pages, {"replica": None, "generated": []})

    def test_replica_case_insensitive(self) -> None:
        self._lane("caps", "Replica")
        pages = studio_server.brand_pages("caps")
        self.assertIsNotNone(pages["replica"])
        self.assertEqual(pages["generated"], [])

    def test_lane_thumb_prefers_fullpage_over_diff_composite(self) -> None:
        lane = self._lane("thumbs", "gen-lane")
        # A diff/contact composite must lose to a real full-page capture.
        (lane / "contact-sheet-vs-source.png").write_bytes(b"x")
        (lane / "gen-lane-fullpage-1440.png").write_bytes(b"x")

        pages = studio_server.brand_pages("thumbs")
        thumb = pages["generated"][0]["thumb"]
        self.assertTrue(thumb.endswith("gen-lane-fullpage-1440.png"), thumb)

    def test_lane_thumb_reads_shots_subdir(self) -> None:
        lane = self._lane("thumbs2", "gen-lane")
        shots = lane / "shots"
        shots.mkdir()
        (shots / "gen-lane-1440.png").write_bytes(b"x")

        pages = studio_server.brand_pages("thumbs2")
        thumb = pages["generated"][0]["thumb"]
        self.assertEqual(
            thumb, "/runs/thumbs2/brand/compose/gen-lane/shots/gen-lane-1440.png"
        )

    def test_lane_thumb_absent_is_empty_string(self) -> None:
        self._lane("nothumb", "gen-lane")
        pages = studio_server.brand_pages("nothumb")
        self.assertEqual(pages["generated"][0]["thumb"], "")


if __name__ == "__main__":
    unittest.main()
