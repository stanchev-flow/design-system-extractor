"""Tests for the Studio's brand-lane surfaces.

Covers, in order:

  * `brand_pages()` / `_lane_thumb()` — the project-view "Pages" section and the
    /compare/<version> side-by-side view. The measured REPLICA (lane dir named
    "replica") vs harness-GENERATED lanes (everything else with an index.html).
  * `BRAND_DOCS` resolution — the brand-lane successors to the old
    `<item>/single/` documents: a tab appears only when its files resolve, and
    never alongside the old-lane original it stands in for.
  * `load_assets()` — both manifest shapes (the old harvested one and the brand
    lane's curated `assets-curation.v1`).
  * `project_meta()` thumbnails — including a capture folder that is a symlink.
  * `run_dir_for()` — the existence check behind the /project/<unknown> 404.

Everything is exercised against a throwaway tree, so nothing here depends on
which runs happen to exist locally.
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import studio_server


class StudioTreeTestCase(unittest.TestCase):
    """Base: point the module globals at a throwaway runs/ + screenshots/ tree."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        # Resolved, because the real PROJECT_DIR is (`Path(__file__).resolve()`)
        # and the server maps files to URLs by resolving them against it — on macOS
        # an unresolved temp dir is /var/... while its files resolve to /private/var/...
        self.project_dir = Path(self._tmp.name).resolve()
        self.runs_dir = self.project_dir / "runs"
        self.shots_dir = self.project_dir / "screenshots"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        self._patches = [
            mock.patch.object(studio_server, "PROJECT_DIR", self.project_dir),
            mock.patch.object(studio_server, "RUNS_DIR", self.runs_dir),
            mock.patch.object(studio_server, "SCREENSHOTS_DIR", self.shots_dir),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self._tmp.cleanup()

    def write(self, rel: str, text: str = "x") -> Path:
        """Write a file under the throwaway PROJECT_DIR, creating parents."""
        path = self.project_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class BrandPagesDiscoveryTests(StudioTreeTestCase):
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


class BrandDocTests(StudioTreeTestCase):
    """The brand-lane document set that replaced the old <item>/single/ docs.

    A brand-lane project has no run item at all, so every one of the old document
    tabs resolved empty and vanished. These entries surface the brand artifact
    that now carries the same information — and must stay silent when it is absent.
    """

    NO_OLD_DOCS: dict = {}

    def test_absent_files_yield_no_tabs(self) -> None:
        # A run directory with nothing in it must produce no tabs at all, which is
        # what keeps the sidebar honest on a half-finished project.
        (self.runs_dir / "bare" / "brand").mkdir(parents=True)
        self.assertEqual(studio_server.brand_docs_available("bare", self.NO_OLD_DOCS), [])

    def test_unknown_project_yields_no_tabs(self) -> None:
        self.assertEqual(studio_server.brand_docs_available("ghost", self.NO_OLD_DOCS), [])

    def test_tab_appears_only_for_the_docs_that_resolve(self) -> None:
        self.write("runs/acme/brand/style-scale.yaml", "type: style_scale\nsteps: [1, 2]\n")
        self.write("runs/acme/brand/layout-language.yaml", "ignored: true\n")

        labels = [d["label"] for d in studio_server.brand_docs_available("acme", self.NO_OLD_DOCS)]
        self.assertEqual(labels, ["Ledger"])

    def test_empty_file_is_not_a_tab(self) -> None:
        # Availability and content have to agree: a zero-byte artifact would render
        # a blank tab, which is the exact failure this whole change is about.
        self.write("runs/acme/brand/style-scale.yaml", "")
        self.assertEqual(studio_server.brand_docs_available("acme", self.NO_OLD_DOCS), [])

    def test_old_lane_original_suppresses_its_brand_successor(self) -> None:
        # A hybrid project (old-lane run that later grew a brand/ dir) must not show
        # two tabs with the same label.
        self.write("runs/hybrid/brand/style-scale.yaml", "steps: [1]\n")
        available = studio_server.brand_docs_available("hybrid", {"ledger": "type: source_style_ledger\n"})
        self.assertEqual([d["label"] for d in available], [])

    def test_brand_successor_survives_an_empty_old_lane_doc(self) -> None:
        self.write("runs/hybrid/brand/style-scale.yaml", "steps: [1]\n")
        available = studio_server.brand_docs_available("hybrid", {"ledger": "   \n"})
        self.assertEqual([d["label"] for d in available], ["Ledger"])

    def test_multi_file_doc_concatenates_with_per_file_headers(self) -> None:
        # Grounding is one YAML per section; the tab is readable only if each file
        # announces itself.
        self.write("runs/acme/brand/evidence/grounding/section-00-hero.yaml", "hero: true\n")
        self.write("runs/acme/brand/evidence/grounding/section-01-footer.yaml", "footer: true\n")

        available = studio_server.brand_docs_available("acme", self.NO_OLD_DOCS)
        self.assertEqual([(d["label"], d["files"]) for d in available], [("Grounding", 2)])

        text = studio_server.brand_doc_text("acme", "brand_grounding")
        self.assertIn("===== brand/evidence/grounding/section-00-hero.yaml =====", text)
        self.assertIn("===== brand/evidence/grounding/section-01-footer.yaml =====", text)
        self.assertIn("hero: true", text)
        self.assertIn("footer: true", text)
        # sorted by path, so the reader gets source order
        self.assertLess(text.index("section-00-hero"), text.index("section-01-footer"))

    def test_alternate_paths_take_the_first_that_resolves(self) -> None:
        # The changelog lives at the run root on some lanes and under brand/ on
        # others; only one of them should be shown.
        self.write("runs/acme/changes.md", "# root changelog\n")
        self.write("runs/acme/brand/changes.md", "# brand changelog\n")

        text = studio_server.brand_doc_text("acme", "brand_changelog")
        self.assertIn("===== changes.md =====", text)
        self.assertIn("root changelog", text)
        self.assertNotIn("brand changelog", text)

    def test_alternate_falls_through_to_the_second_path(self) -> None:
        self.write("runs/acme/brand/changes.md", "# brand changelog\n")
        text = studio_server.brand_doc_text("acme", "brand_changelog")
        self.assertIn("===== brand/changes.md =====", text)
        self.assertIn("brand changelog", text)

    def test_groups_each_contribute_a_file(self) -> None:
        # "Sections" is layout-library + section-copy: both, not the first.
        self.write("runs/acme/brand/layout-library.yaml", "patterns: []\n")
        self.write("runs/acme/brand/section-copy.yaml", "sections: []\n")

        available = studio_server.brand_docs_available("acme", self.NO_OLD_DOCS)
        self.assertEqual([(d["label"], d["files"]) for d in available], [("Sections", 2)])
        text = studio_server.brand_doc_text("acme", "brand_sections")
        self.assertIn("===== brand/layout-library.yaml =====", text)
        self.assertIn("===== brand/section-copy.yaml =====", text)

    def test_partial_group_still_resolves(self) -> None:
        self.write("runs/acme/brand/layout-library.yaml", "patterns: []\n")
        available = studio_server.brand_docs_available("acme", self.NO_OLD_DOCS)
        self.assertEqual([(d["label"], d["files"]) for d in available], [("Sections", 1)])

    def test_unknown_doc_key_is_empty(self) -> None:
        self.write("runs/acme/brand/style-scale.yaml", "steps: [1]\n")
        self.assertEqual(studio_server.brand_doc_text("acme", "not-a-doc"), "")

    def test_labels_are_unique(self) -> None:
        # Two tabs with the same caption would be unusable.
        labels = [d.label for d in studio_server.BRAND_DOCS]
        self.assertEqual(len(labels), len(set(labels)))

    def test_keys_are_unique(self) -> None:
        keys = [d.key for d in studio_server.BRAND_DOCS]
        self.assertEqual(len(keys), len(set(keys)))


class RunDirGuardTests(StudioTreeTestCase):
    """run_dir_for() is both the /project/<unknown> 404 check and a path guard."""

    def test_existing_project_resolves(self) -> None:
        (self.runs_dir / "acme").mkdir()
        self.assertEqual(studio_server.run_dir_for("acme"), self.runs_dir / "acme")

    def test_unknown_project_is_none(self) -> None:
        self.assertIsNone(studio_server.run_dir_for("nope"))

    def test_project_with_few_artifacts_still_resolves(self) -> None:
        # The 404 must key off the directory, never off how much is in it: a real
        # project with almost nothing generated has to keep rendering.
        (self.runs_dir / "thin").mkdir()
        self.write("runs/thin/studio-project.json", json.dumps({"title": "Thin"}))
        self.assertIsNotNone(studio_server.run_dir_for("thin"))

    def test_empty_version_is_none(self) -> None:
        self.assertIsNone(studio_server.run_dir_for(""))

    def test_traversal_is_refused(self) -> None:
        self.assertIsNone(studio_server.run_dir_for("../.."))
        self.assertIsNone(studio_server.run_dir_for("../../etc"))

    def test_file_is_not_a_project(self) -> None:
        self.write("runs/notadir", "x")
        self.assertIsNone(studio_server.run_dir_for("notadir"))


class LoadAssetsTests(StudioTreeTestCase):
    """Both asset-manifest shapes feed the same gallery payload."""

    def test_no_manifest_is_empty(self) -> None:
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.assertEqual(studio_server.load_assets("acme"), {"total": 0, "by_role": {}, "roles": []})

    def test_harvested_shape(self) -> None:
        self.write(
            "runs/acme/assets/assets-manifest.json",
            json.dumps(
                {
                    "total_logical_assets": 2,
                    "assets": [
                        {
                            "url": "https://cdn.example.com/a.svg",
                            "name": "a.svg",
                            "asset_type": "icon",
                            "role": "content",
                            "placement": {"landmark": "section"},
                        },
                        {"url": "https://cdn.example.com/b.png", "name": "b.png", "role": "hero"},
                    ],
                }
            ),
        )
        a = studio_server.load_assets("acme")
        self.assertEqual(a["total"], 2)
        self.assertEqual(sorted(a["roles"]), ["content", "hero"])
        self.assertEqual(a["by_role"]["content"][0]["url"], "https://cdn.example.com/a.svg")
        self.assertEqual(a["by_role"]["content"][0]["type"], "icon")
        self.assertEqual(a["by_role"]["content"][0]["landmark"], "section")

    def _curated(self, version: str, *, media: bool = True) -> None:
        self.write(
            f"runs/{version}/brand/assets-manifest.json",
            json.dumps(
                {
                    "schemaVersion": "assets-curation.v1",
                    "entries": [
                        {"dest": "logo.svg", "tagGuess": "logo", "bytes": 10, "pages": ["home"]},
                        {"dest": "hero.webp", "tagGuess": "decorative", "bytes": 20},
                        {"dest": "gone.png", "tagGuess": "decorative", "bytes": 30},
                    ],
                }
            ),
        )
        self.write(f"runs/{version}/brand/assets/logo.svg", "<svg/>")
        self.write(f"runs/{version}/brand/assets/hero.webp", "img")
        if media:
            self.write(
                f"runs/{version}/brand/media-assets.yaml",
                "schemaVersion: media-assets.v1\n"
                "assets:\n"
                "  - id: brand-wordmark\n"
                "    file: logo.svg\n"
                "    assetSemantics:\n"
                "      kind: logo-own\n",
            )

    def test_curated_shape_counts_every_entry(self) -> None:
        self._curated("acme")
        a = studio_server.load_assets("acme")
        # The count is what the manifest curated, including the one file that is
        # no longer on disk — the gallery says so per tile rather than under-counting.
        self.assertEqual(a["total"], 3)
        self.assertEqual(a["roles"], ["decorative", "logo"])

    def test_curated_shape_resolves_urls_and_semantics(self) -> None:
        self._curated("acme")
        a = studio_server.load_assets("acme")
        logo = a["by_role"]["logo"][0]
        self.assertEqual(logo["url"], "/runs/acme/brand/assets/logo.svg")
        self.assertEqual(logo["name"], "logo.svg")
        self.assertEqual(logo["landmark"], "home")
        # bound in media-assets.yaml → the authored media kind is the badge
        self.assertEqual(logo["type"], "logo-own")
        # not bound → said so, rather than left blank
        hero = next(x for x in a["by_role"]["decorative"] if x["name"] == "hero.webp")
        self.assertEqual(hero["type"], "unbound")
        missing = next(x for x in a["by_role"]["decorative"] if x["name"] == "gone.png")
        self.assertEqual(missing["url"], "")

    def test_curated_shape_without_media_bindings(self) -> None:
        self._curated("acme", media=False)
        a = studio_server.load_assets("acme")
        self.assertEqual(a["by_role"]["logo"][0]["type"], "")

    def test_curated_falls_back_to_a_compose_lane_copy(self) -> None:
        # The curation pool is not part of the committed subset but each compose
        # lane keeps its own copy of what it uses, so a clean clone resolves there.
        self.write(
            "runs/acme/brand/assets-manifest.json",
            json.dumps({"entries": [{"dest": "logo.svg", "tagGuess": "logo"}]}),
        )
        self.write("runs/acme/brand/compose/replica/assets/logo.svg", "<svg/>")
        a = studio_server.load_assets("acme")
        self.assertEqual(
            a["by_role"]["logo"][0]["url"], "/runs/acme/brand/compose/replica/assets/logo.svg"
        )

    def test_harvested_manifest_wins_when_both_exist(self) -> None:
        self.write(
            "runs/acme/assets/assets-manifest.json",
            json.dumps({"total_logical_assets": 1, "assets": [{"url": "u", "role": "hero"}]}),
        )
        self._curated("acme")
        a = studio_server.load_assets("acme")
        self.assertEqual(a["total"], 1)
        self.assertEqual(a["roles"], ["hero"])

    def test_unparseable_manifest_degrades(self) -> None:
        self.write("runs/acme/brand/assets-manifest.json", "{not json")
        self.assertEqual(studio_server.load_assets("acme")["total"], 0)

    def test_curated_entries_without_dest_are_skipped(self) -> None:
        self.write(
            "runs/acme/brand/assets-manifest.json",
            json.dumps({"entries": [{"tagGuess": "logo"}, {"dest": "a.svg", "tagGuess": "logo"}]}),
        )
        a = studio_server.load_assets("acme")
        self.assertEqual(len(a["by_role"]["logo"]), 1)


class ProjectThumbTests(StudioTreeTestCase):
    """The dashboard card thumbnail, which used to say "no preview" for a modern capture."""

    def _project(self, version: str) -> None:
        (self.runs_dir / version / "brand").mkdir(parents=True)

    def test_run_item_screenshot_still_wins(self) -> None:
        self.write("runs/acme/acme/screenshot.png", "img")
        (self.runs_dir / "acme" / "acme" / "single").mkdir(parents=True, exist_ok=True)
        self.assertEqual(studio_server.project_meta("acme")["thumb"], "/runs/acme/acme/screenshot.png")

    def test_per_page_capture_dir_is_found(self) -> None:
        # The regression: only per-page subdirectories exist, so the old root-level
        # scan found nothing even though the project page's Source pane worked.
        self._project("acme")
        self.write("screenshots/acme/home/home-fullpage.png", "img")
        self.assertEqual(
            studio_server.project_meta("acme")["thumb"], "/screenshots/acme/home/home-fullpage.png"
        )

    def test_symlinked_capture_dir_is_found(self) -> None:
        # A project can alias another project's capture (screenshots/<a> → <b>);
        # the thumbnail has to resolve to the real file, still under PROJECT_DIR.
        self._project("acme-4")
        self.write("screenshots/acme-v2/home/home-fullpage.png", "img")
        (self.shots_dir / "acme-4").symlink_to(self.shots_dir / "acme-v2")

        self.assertEqual(
            studio_server.project_meta("acme-4")["thumb"],
            "/screenshots/acme-v2/home/home-fullpage.png",
        )

    def test_root_level_capture_image_still_works(self) -> None:
        self._project("acme")
        self.write("screenshots/acme/acme-fullpage.png", "img")
        self.assertEqual(
            studio_server.project_meta("acme")["thumb"], "/screenshots/acme/acme-fullpage.png"
        )

    def test_no_capture_at_all_is_empty(self) -> None:
        self._project("acme")
        self.assertEqual(studio_server.project_meta("acme")["thumb"], "")


if __name__ == "__main__":
    unittest.main()
