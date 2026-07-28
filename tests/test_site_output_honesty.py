"""A run must not claim site output it does not have.

Three silent-success paths are locked down here:

  * ``vanilla-site-generation-enabled: false`` now switches the vanilla lane off
    on its own, so the shipped CLI baseline enables no lane and the run is
    refused up front instead of quietly emitting HTML the config had disabled.
  * A failed generation no longer writes error-page HTML into ``site-*.html``,
    so a failure is distinguishable from a real page by filename alone.
  * A retired provider named in ``site-generation-providers.txt`` is disclosed
    through the lane ledger rather than dropped in silence.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

import run_pipeline
from run_pipeline import (
    clear_site_failure_artifacts,
    is_generated_site_html,
    site_failure_marker_path,
    site_failure_page_path,
    site_output_needs_regeneration,
    write_site_failure_artifacts,
)
from screenshot_to_template.lane_disclosure import (
    LANE_VANILLA,
    OUTCOME_PRODUCED,
    OUTCOME_SKIPPED_NOT_REQUESTED,
)

COMPLETE_PAGE = (
    "<html><head><style>body{margin:0}</style></head>"
    "<body><h1>Hatch</h1></body></html>"
)


class SiteFailureArtifactTests(unittest.TestCase):
    def test_a_failure_leaves_nothing_at_the_real_site_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "site-claude.html"

            error_page = write_site_failure_artifacts(
                output,
                lane=LANE_VANILLA,
                provider="claude",
                stage="site_generation",
                error="provider timeout",
            )

            # The whole point: a consumer globbing for site HTML sees no file.
            self.assertFalse(output.exists())
            self.assertTrue(error_page.exists())
            self.assertEqual(error_page.name, "site-claude.error.html")
            self.assertIn("provider timeout", error_page.read_text())

    def test_the_marker_records_the_failure_in_machine_readable_form(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "site-gpt55.html"

            write_site_failure_artifacts(
                output,
                lane=LANE_VANILLA,
                provider="gpt55",
                stage="site_generation",
                error="429 rate limited",
            )
            payload = json.loads(site_failure_marker_path(output).read_text())

            self.assertEqual(payload["schemaVersion"], "site-generation-failure.v1")
            self.assertEqual(payload["lane"], LANE_VANILLA)
            self.assertEqual(payload["provider"], "gpt55")
            self.assertEqual(payload["expectedOutput"], "site-gpt55.html")
            self.assertEqual(payload["errorPage"], "site-gpt55.error.html")
            self.assertIn("429", payload["error"])

    def test_a_page_from_an_earlier_run_is_not_left_behind_as_this_run_s(self) -> None:
        # Leaving it would move the ambiguity rather than remove it: the file
        # would still be read as output this run produced.
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "site-claude.html"
            output.write_text(COMPLETE_PAGE)

            write_site_failure_artifacts(
                output,
                lane=LANE_VANILLA,
                provider="claude",
                stage="site_generation",
                error="boom",
            )

            self.assertFalse(output.exists())

    def test_a_missing_page_still_asks_to_be_regenerated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "site-claude.html"
            write_site_failure_artifacts(
                output,
                lane=LANE_VANILLA,
                provider="claude",
                stage="site_generation",
                error="boom",
            )

            self.assertTrue(site_output_needs_regeneration(output))

    def test_real_output_clears_the_previous_failure_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "site-claude.html"
            write_site_failure_artifacts(
                output,
                lane=LANE_VANILLA,
                provider="claude",
                stage="site_generation",
                error="boom",
            )

            clear_site_failure_artifacts(output)
            output.write_text(COMPLETE_PAGE)

            self.assertFalse(site_failure_marker_path(output).exists())
            self.assertFalse(site_failure_page_path(output).exists())
            self.assertTrue(is_generated_site_html(output))


class GeneratedSiteDetectionTests(unittest.TestCase):
    def test_a_marker_beats_the_markup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "site-claude.html"
            output.write_text(COMPLETE_PAGE)
            site_failure_marker_path(output).write_text("{}")

            self.assertFalse(is_generated_site_html(output))

    def test_a_legacy_framework_error_page_is_not_generated_output(self) -> None:
        # Run folders written before the failure marker existed still hold these,
        # and the framework variant used to slip past the content check.
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "site-claude-framework.html"
            output.write_text("<html><body><h1>Framework Error</h1><p>x</p></body></html>")

            self.assertFalse(is_generated_site_html(output))


def build_refreshable_run(root: Path, providers: str) -> tuple[Path, Path]:
    """A version folder --sites-only can refresh without any model call."""
    shots = root / "shots"
    shots.mkdir()
    Image.new("RGB", (32, 32), "white").save(shots / "probe.png")

    runs = root / "runs"
    version_dir = runs / "v-probe"
    single = version_dir / "probe" / "single"
    single.mkdir(parents=True)
    (single / "design-system.md").write_text(
        "# Design System\n\nSurfaces: base, inverse. Buttons hug their content.\n"
    )
    # Complete and current, so the refresh keeps it instead of regenerating.
    (single / "site-claude.html").write_text(COMPLETE_PAGE)
    (version_dir / "site-generation-providers.txt").write_text(providers)
    return shots, runs


def run_sites_only(shots: Path, runs: Path, **kwargs) -> None:
    """Invoke the real pipeline against a temp run, with no model call reachable.

    ``generate_viewer`` is stubbed because it writes the repo's own
    ``viewer.html``, which a test must not touch.
    """
    with mock.patch.object(run_pipeline, "generate_viewer"), mock.patch.object(
        run_pipeline, "RUNS_DIR", runs
    ):
        run_pipeline.run_pipeline(
            "v-probe",
            shots,
            sites_only=True,
            run_reviews=False,
            skip_design_system_review=True,
            **kwargs,
        )


def refresh(shots: Path, runs: Path, **kwargs) -> dict:
    run_sites_only(shots, runs, vanilla_sites=True, **kwargs)
    return json.loads((runs / "v-probe" / "manifest.json").read_text())


def vanilla_lane(manifest: dict) -> dict:
    lanes = manifest["site_generation_lanes"]["lanes"]
    return next(row for row in lanes if row["lane"] == LANE_VANILLA)


class RetiredProviderDisclosureTests(unittest.TestCase):
    def test_a_retired_provider_is_named_as_retired_in_the_lane_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            shots, runs = build_refreshable_run(Path(temp_dir), "claude\ngemini\n")

            manifest = refresh(shots, runs)
            lane = vanilla_lane(manifest)
            gemini = next(t for t in lane["targets"] if t["provider"] == "gemini")
            claude = next(t for t in lane["targets"] if t["provider"] == "claude")

            self.assertEqual(claude["outcome"], OUTCOME_PRODUCED)
            self.assertEqual(gemini["outcome"], OUTCOME_SKIPPED_NOT_REQUESTED)
            # Not "gemini is not in this run's list" — the file does name it.
            self.assertIn("retired", gemini["reason"])
            self.assertIn("site-generation-providers.txt", gemini["reason"])

    def test_an_unrequested_provider_still_reads_as_unrequested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            shots, runs = build_refreshable_run(Path(temp_dir), "claude\n")

            lane = vanilla_lane(refresh(shots, runs))
            gpt55 = next(t for t in lane["targets"] if t["provider"] == "gpt55")

            self.assertEqual(gpt55["outcome"], OUTCOME_SKIPPED_NOT_REQUESTED)
            self.assertNotIn("retired", gpt55["reason"])

    def test_a_list_of_only_retired_providers_stops_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            shots, runs = build_refreshable_run(Path(temp_dir), "gemini\n")

            with self.assertRaises(ValueError) as caught:
                refresh(shots, runs)

            self.assertIn("gemini", str(caught.exception))


class FailedGenerationTests(unittest.TestCase):
    def test_a_failed_generation_writes_no_page_at_the_real_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            shots, runs = build_refreshable_run(root, "claude\n")
            single = runs / "v-probe" / "probe" / "single"
            # Truncated, so the refresh regenerates it and the generator fails.
            (single / "site-claude.html").write_text("<html><body>truncated")

            with mock.patch.object(
                run_pipeline,
                "generate_website_html",
                side_effect=RuntimeError("provider exploded"),
            ):
                with self.assertRaises(SystemExit) as caught:
                    run_sites_only(shots, runs, vanilla_sites=True)

            manifest = json.loads((runs / "v-probe" / "manifest.json").read_text())
            claude = next(
                t
                for t in vanilla_lane(manifest)["targets"]
                if t["provider"] == "claude"
            )
            output = single / "site-claude.html"

            self.assertEqual(caught.exception.code, 1)
            self.assertFalse(output.exists())
            self.assertTrue(site_failure_page_path(output).exists())
            self.assertIn(
                "provider exploded",
                json.loads(site_failure_marker_path(output).read_text())["error"],
            )
            self.assertEqual(claude["outcome"], "failed")
            self.assertIn("provider exploded", claude["reason"])


class NoEnabledLaneTests(unittest.TestCase):
    def test_the_shipped_defaults_refuse_the_run_before_any_model_work(self) -> None:
        # Reachable only because vanilla-site-generation-enabled now governs its
        # own lane. Before that, framework-off always left vanilla running.
        with tempfile.TemporaryDirectory() as temp_dir:
            shots, runs = build_refreshable_run(Path(temp_dir), "claude\n")

            with self.assertRaises(SystemExit) as caught:
                run_sites_only(shots, runs)

            self.assertEqual(caught.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
