import unittest

from PIL import Image

from screenshot_to_template.config import AppConfig
from screenshot_to_template.pipeline import splitter


class SplitterBoundaryTests(unittest.TestCase):
    def test_add_vertical_ruler_expands_width_without_changing_height(self) -> None:
        img = Image.new("RGB", (640, 1200), "white")
        ruled = splitter.add_vertical_ruler(img, y_offset=500)

        self.assertEqual(ruled.size[0], img.size[0] + splitter.RULER_GUTTER_WIDTH)
        self.assertEqual(ruled.size[1], img.size[1])

    def test_build_detection_windows_overlaps_without_gaps(self) -> None:
        windows = splitter.build_detection_windows(image_height=7000, chunk_height=2400, overlap=400)

        self.assertEqual(windows[0], {"index": 1, "y_start": 0, "y_end": 2400})
        self.assertEqual(windows[-1]["y_end"], 7000)
        for current, nxt in zip(windows, windows[1:]):
            self.assertLess(current["y_start"], current["y_end"])
            self.assertLessEqual(nxt["y_start"], current["y_end"])

    def test_build_even_detection_windows_for_two_chunks(self) -> None:
        windows = splitter.build_even_detection_windows(image_height=30000, chunk_count=2, overlap=1600)

        self.assertEqual(windows[0]["y_start"], 0)
        self.assertEqual(windows[-1]["y_end"], 30000)
        self.assertEqual(len(windows), 2)
        self.assertLess(windows[1]["y_start"], windows[0]["y_end"])

    def test_auto_chunk_count_for_height(self) -> None:
        config = AppConfig(
            auto_chunk_tall_section_detection=True,
            auto_two_chunk_threshold_height=22000,
            auto_three_chunk_threshold_height=999999,
        )

        self.assertEqual(splitter._auto_chunk_count_for_height(12000, config), 1)
        self.assertEqual(splitter._auto_chunk_count_for_height(20000, config), 1)
        self.assertEqual(splitter._auto_chunk_count_for_height(23622, config), 2)
        self.assertEqual(splitter._auto_chunk_count_for_height(30000, config), 2)

    def test_merge_window_boundary_candidates_clusters_votes(self) -> None:
        merged = splitter._merge_window_boundary_candidates(
            [
                {"y": 1190, "upper_label": "Hero", "lower_label": "Logo row", "window_start": 0, "window_end": 2400},
                {"y": 1210, "upper_label": "Hero", "lower_label": "Logo row", "window_start": 2000, "window_end": 4400},
                {"y": 3205, "upper_label": "Logo row", "lower_label": "Stats", "window_start": 2000, "window_end": 4400},
            ],
            tolerance=40,
            image_height=5000,
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["upper_label"], "Hero")
        self.assertEqual(merged[0]["lower_label"], "Logo row")
        self.assertEqual(merged[0]["votes"], 2)

    def test_merge_window_boundary_candidates_keeps_nearby_different_labels_separate(self) -> None:
        merged = splitter._merge_window_boundary_candidates(
            [
                {"y": 780, "upper_label": "Hero", "lower_label": "Logo row", "window_start": 0, "window_end": 2400},
                {"y": 860, "upper_label": "Logo row", "lower_label": "Intro", "window_start": 0, "window_end": 2400},
            ],
            tolerance=90,
            image_height=3000,
        )

        self.assertEqual(len(merged), 2)

    def test_split_boundary_between_label_preserves_hyphenated_labels(self) -> None:
        upper, lower = splitter._split_boundary_between_label(
            "Dark call-to-action banner -> Read more / journal grid"
        )

        self.assertEqual(upper, "Dark call-to-action banner")
        self.assertEqual(lower, "Read more / journal grid")

    def test_sections_from_boundary_candidates_rebuilds_ordered_sections(self) -> None:
        sections = splitter._sections_from_boundary_candidates(
            [
                {"y": 1200, "upper_label": "Hero", "lower_label": "Logo row"},
                {"y": 1800, "upper_label": "Logo row", "lower_label": "Stats"},
            ],
            image_height=2600,
        )

        self.assertEqual(
            sections,
            [
                {"label": "Hero", "y_start": 0, "y_end": 1200},
                {"label": "Logo row", "y_start": 1200, "y_end": 1800},
                {"label": "Stats", "y_start": 1800, "y_end": 2600},
            ],
        )

    def test_sections_from_boundary_candidates_uses_next_boundary_label_when_middle_labels_conflict(self) -> None:
        sections = splitter._sections_from_boundary_candidates(
            [
                {"y": 1000, "upper_label": "Hero", "lower_label": "Wrong label"},
                {"y": 1800, "upper_label": "Actual middle", "lower_label": "Footer"},
            ],
            image_height=2400,
        )

        self.assertEqual(sections[1]["label"], "Actual middle")

    def test_collapse_duplicate_transition_boundaries_merges_repeated_overlap_votes(self) -> None:
        collapsed = splitter._collapse_duplicate_transition_boundaries(
            [
                {
                    "y": 15600,
                    "upper_label": "Case study",
                    "lower_label": "Client feedback / reviews",
                    "votes": 1,
                    "windows": [(0, 16912)],
                },
                {
                    "y": 16306,
                    "upper_label": "Case study",
                    "lower_label": "Client feedback / reviews",
                    "votes": 1,
                    "windows": [(13712, 30624)],
                },
                {
                    "y": 19607,
                    "upper_label": "Client feedback / reviews",
                    "lower_label": "Team",
                    "votes": 1,
                    "windows": [(13712, 30624)],
                },
            ],
            image_height=30624,
        )

        self.assertEqual(len(collapsed), 2)
        self.assertEqual(collapsed[0]["votes"], 2)
        self.assertGreater(collapsed[0]["y"], 15600)
        self.assertLess(collapsed[0]["y"], 16306)

    def test_collapse_duplicate_transition_boundaries_prefers_overlap_boundary_when_duplicate_is_far(self) -> None:
        collapsed = splitter._collapse_duplicate_transition_boundaries(
            [
                {
                    "y": 15600,
                    "upper_label": "Case study showcase",
                    "lower_label": "Client feedback / testimonials",
                    "votes": 1,
                    "windows": [(0, 16912)],
                },
                {
                    "y": 23364,
                    "upper_label": "Case study showcase",
                    "lower_label": "Client feedback / testimonials",
                    "votes": 1,
                    "windows": [(13712, 30624)],
                },
                {
                    "y": 24610,
                    "upper_label": "Client feedback / testimonials",
                    "lower_label": "Team",
                    "votes": 1,
                    "windows": [(13712, 30624)],
                },
            ],
            image_height=30624,
        )

        self.assertEqual(len(collapsed), 2)
        self.assertEqual(collapsed[0]["y"], 15600)
        self.assertEqual(collapsed[0]["votes"], 2)

    def test_merge_adjacent_same_label_sections_coalesces_duplicates(self) -> None:
        merged = splitter._merge_adjacent_same_label_sections(
            [
                {"label": "Client feedback / reviews", "y_start": 1000, "y_end": 1500},
                {"label": "Client feedback / reviews", "y_start": 1500, "y_end": 2200},
                {"label": "Team", "y_start": 2200, "y_end": 2600},
            ],
            image_height=2600,
        )

        self.assertEqual(
            merged,
            [
                {"label": "Client feedback / reviews", "y_start": 0, "y_end": 2200},
                {"label": "Team", "y_start": 2200, "y_end": 2600},
            ],
        )


if __name__ == "__main__":
    unittest.main()
