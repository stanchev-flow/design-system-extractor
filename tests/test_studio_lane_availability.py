"""A lane the Studio advertises must have content behind it.

The project page used to offer `brand/chrome/index.html` on every project,
whether or not the run ever produced one — eight of eleven projects carried a
dropdown entry that could only 404. These tests hold every lane builder to the
same rule the brand-document tabs already follow: a zero-byte or missing file
counts as ABSENT, so availability and content always agree.

`versioned_lanes()` is covered too, because it is the backstop — whatever
assembled the list, a lane with nothing behind it does not reach the dropdown.

Everything runs against a throwaway tree, so nothing here depends on which runs
exist locally.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import studio_server


class StudioTreeTestCase(unittest.TestCase):
    """Base: point the module globals at a throwaway runs/ + screenshots/ tree."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.project_dir = Path(self._tmp.name).resolve()
        self.runs_dir = self.project_dir / "runs"
        self.shots_dir = self.project_dir / "screenshots"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        self._patches = [
            mock.patch.object(studio_server, "PROJECT_DIR", self.project_dir),
            mock.patch.object(studio_server, "RUNS_DIR", self.runs_dir),
            mock.patch.object(studio_server, "SCREENSHOTS_DIR", self.shots_dir),
            mock.patch.object(studio_server, "STUDIO_DIR", self.runs_dir / ".studio"),
            mock.patch.object(
                studio_server, "FRAMEWORK_BUILDS_REGISTRY",
                self.runs_dir / ".studio" / "framework-builds.json",
            ),
            # Also inside the throwaway tree: the real one holds published bundles
            # for real projects, which the payload would URL-map against
            # PROJECT_DIR and fail on.
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

    def write(self, rel: str, text: str = "<html></html>") -> Path:
        path = self.project_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class HasContentTests(StudioTreeTestCase):
    """The shared predicate: present, non-empty, and a file."""

    def test_file_with_bytes(self) -> None:
        self.assertTrue(studio_server.has_content(self.write("runs/acme/a.html")))

    def test_zero_byte_file_is_absent(self) -> None:
        self.assertFalse(studio_server.has_content(self.write("runs/acme/a.html", "")))

    def test_missing_file_is_absent(self) -> None:
        self.assertFalse(studio_server.has_content(self.project_dir / "nope.html"))

    def test_directory_is_not_content(self) -> None:
        (self.runs_dir / "acme").mkdir()
        self.assertFalse(studio_server.has_content(self.runs_dir / "acme"))

    def test_lane_url_resolves_against_project_dir(self) -> None:
        self.write("runs/acme/brand/chrome/index.html")
        self.assertTrue(studio_server.lane_has_content("/runs/acme/brand/chrome/index.html"))

    def test_lane_url_for_a_missing_page_is_absent(self) -> None:
        self.assertFalse(studio_server.lane_has_content("/runs/acme/brand/chrome/index.html"))

    def test_empty_lane_url_is_absent(self) -> None:
        self.assertFalse(studio_server.lane_has_content(""))

    def test_absolute_url_is_not_ours_to_verify(self) -> None:
        # Another origin: the Studio cannot check it, so it passes through here and
        # is classified where it is built (framework_builds).
        self.assertTrue(studio_server.lane_has_content("http://localhost:5179/"))


class StaticBrandLaneTests(StudioTreeTestCase):
    """`static_brand_lanes()` — the two fixed brand-level preview lanes."""

    def test_chrome_lane_is_not_offered_when_it_was_never_generated(self) -> None:
        # THE regression: this lane used to be listed unconditionally, so a project
        # that never ran the chrome stage advertised a guaranteed 404.
        (self.runs_dir / "acme" / "brand").mkdir(parents=True)
        self.assertEqual(studio_server.static_brand_lanes("acme"), [])

    def test_chrome_lane_is_offered_when_it_exists(self) -> None:
        self.write("runs/acme/brand/chrome/index.html")
        self.assertEqual(
            studio_server.static_brand_lanes("acme"),
            [{"label": "Exact nav/footer", "url": "/runs/acme/brand/chrome/index.html"}],
        )

    def test_zero_byte_chrome_page_is_not_a_lane(self) -> None:
        self.write("runs/acme/brand/chrome/index.html", "")
        self.assertEqual(studio_server.static_brand_lanes("acme"), [])

    def test_components_preview_is_offered_when_it_exists(self) -> None:
        self.write("runs/acme/brand/components-preview/index.html")
        self.assertEqual(
            [l["label"] for l in studio_server.static_brand_lanes("acme")],
            ["Components preview"],
        )

    def test_zero_byte_components_preview_is_not_a_lane(self) -> None:
        self.write("runs/acme/brand/components-preview/index.html", "")
        self.assertEqual(studio_server.static_brand_lanes("acme"), [])

    def test_both_lanes_when_both_exist(self) -> None:
        self.write("runs/acme/brand/components-preview/index.html")
        self.write("runs/acme/brand/chrome/index.html")
        self.assertEqual(
            [l["label"] for l in studio_server.static_brand_lanes("acme")],
            ["Components preview", "Exact nav/footer"],
        )

    def test_unknown_project_has_no_static_lanes(self) -> None:
        self.assertEqual(studio_server.static_brand_lanes("ghost"), [])


class VersionedLaneBackstopTests(StudioTreeTestCase):
    """`versioned_lanes()` drops anything with nothing behind it, whoever built it."""

    def test_lane_with_a_missing_page_is_dropped(self) -> None:
        real = self.write("runs/acme/brand/compose/replica/index.html")
        lanes = studio_server.versioned_lanes(
            [
                {"label": "Real", "url": "/" + str(real.relative_to(self.project_dir))},
                {"label": "Phantom", "url": "/runs/acme/brand/chrome/index.html"},
            ]
        )
        self.assertEqual([l["label"].split(" · ")[-1] for l in lanes], ["Real"])

    def test_zero_byte_lane_page_is_dropped(self) -> None:
        self.write("runs/acme/brand/harness/index.html", "")
        self.assertEqual(
            studio_server.versioned_lanes(
                [{"label": "Harness (raw)", "url": "/runs/acme/brand/harness/index.html"}]
            ),
            [],
        )

    def test_surviving_lane_keeps_its_version_prefix(self) -> None:
        self.write("runs/acme/brand/harness/index.html")
        lanes = studio_server.versioned_lanes(
            [{"label": "Harness (raw)", "url": "/runs/acme/brand/harness/index.html"}]
        )
        self.assertEqual(len(lanes), 1)
        self.assertTrue(lanes[0]["label"].startswith("v01 · "), lanes[0]["label"])
        self.assertTrue(lanes[0]["label"].endswith("Harness (raw)"), lanes[0]["label"])
        # A surviving lane always has a real mtime now, so the "--??" placeholder
        # that marked an absent page cannot appear.
        self.assertNotIn("--??", lanes[0]["label"])


class LaneBuilderContentTests(StudioTreeTestCase):
    """Every other lane builder holds to the same zero-byte rule."""

    def test_zero_byte_composed_page_is_not_a_lane(self) -> None:
        self.write("runs/acme/brand/compose/launch/index.html", "")
        self.assertEqual(studio_server.compose_pages("acme"), [])

    def test_composed_page_with_content_is_a_lane(self) -> None:
        self.write("runs/acme/brand/compose/launch/index.html")
        self.assertEqual(
            [l["label"] for l in studio_server.compose_pages("acme")], ["Composed: launch"]
        )

    def test_zero_byte_variant_is_not_a_lane(self) -> None:
        self.write("runs/acme/brand/variants/a/index.html", "")
        self.assertEqual(studio_server.variant_pages("acme"), [])

    def test_zero_byte_harness_is_not_a_lane(self) -> None:
        self.write("runs/acme/brand/harness/index.html", "")
        self.assertEqual(studio_server.harness_pages("acme"), [])

    def test_zero_byte_sections_gallery_is_not_a_lane(self) -> None:
        self.write("runs/acme/brand/sections/index.html", "")
        self.assertEqual(studio_server.sections_pages("acme"), [])

    def test_zero_byte_brand_page_is_not_listed(self) -> None:
        self.write("runs/acme/brand/compose/replica/index.html", "")
        self.assertEqual(studio_server.brand_pages("acme"), {"replica": None, "generated": []})

    def test_zero_byte_generated_site_is_not_a_lane(self) -> None:
        self.write("runs/acme/item/single/site-claude.html", "")
        self.assertEqual(studio_server.site_rel("acme", "item", "claude"), "")

    def test_generated_site_prefers_the_assets_applied_copy(self) -> None:
        self.write("runs/acme/item/single/site-claude.html")
        self.write("runs/acme/item/single/site-claude.assets-applied.html")
        self.assertEqual(
            studio_server.site_rel("acme", "item", "claude"),
            "/runs/acme/item/single/site-claude.assets-applied.html",
        )

    def test_empty_assets_applied_copy_falls_back_to_the_plain_one(self) -> None:
        self.write("runs/acme/item/single/site-claude.html")
        self.write("runs/acme/item/single/site-claude.assets-applied.html", "")
        self.assertEqual(
            studio_server.site_rel("acme", "item", "claude"),
            "/runs/acme/item/single/site-claude.html",
        )


class ProjectPayloadLaneTests(StudioTreeTestCase):
    """The lane list the project page is built from carries no dead entries."""

    def test_every_advertised_lane_has_content_behind_it(self) -> None:
        self.write("runs/acme/brand/compose/replica/index.html")
        self.write("runs/acme/brand/harness/index.html")
        self.write("runs/acme/brand/chrome/index.html", "")  # zero-byte: not a lane
        detail = studio_server.project_detail("acme")

        self.assertTrue(detail["lanes"])
        for lane in detail["lanes"]:
            self.assertTrue(
                studio_server.lane_has_content(lane["url"]),
                f"advertised lane with nothing behind it: {lane}",
            )
        labels = [l["label"] for l in detail["lanes"]]
        self.assertFalse([l for l in labels if "Exact nav/footer" in l], labels)

    def test_a_project_with_nothing_generated_advertises_no_lanes(self) -> None:
        (self.runs_dir / "bare").mkdir()
        self.assertEqual(studio_server.project_detail("bare")["lanes"], [])

    def test_build_links_only_carry_reachable_targets(self) -> None:
        self.write("runs/acme/brand/compose/replica/index.html")
        for link in studio_server.project_build_links("acme"):
            if link.get("external") or link.get("available") is False:
                continue
            self.assertTrue(
                studio_server.lane_has_content(link["url"]), f"dead build link: {link}"
            )


if __name__ == "__main__":
    unittest.main()
