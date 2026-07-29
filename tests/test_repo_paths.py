"""The shared answer to "how should an artifact record a path".

`screenshot_to_template.repo_paths.report_path()` is the helper every producer
that records a filesystem path into run output goes through. It generalises what
`brand_pipeline/compose_replica.py` established for the replica report: a path
inside the repo is written relative to the repo root, and a genuinely external
path is left alone, because shortening that one would make it meaningless.

Two things ride on getting this right. Run output is committed for a PUBLIC repo,
so an absolute path names the machine the run happened on; and
`tools/track_studio_subset.py` holds back any text artifact containing this
checkout's absolute path, so a leaked path silently drops the artifact — and its
Studio tab — out of the committed subset.

`resolve_report_path()` is the inverse, for the artifacts that get read back.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "brand_pipeline"))

import compose_replica  # noqa: E402
from screenshot_to_template.repo_paths import (  # noqa: E402
    REPO_ROOT as HELPER_REPO_ROOT,
    report_path,
    resolve_report_path,
)


class ReportPathTests(unittest.TestCase):
    def test_repo_root_is_the_checkout(self) -> None:
        # Guards the helper's premise: REPO_ROOT is the repo, not src/ or the
        # package dir, even though the helper ships inside the package.
        self.assertTrue((HELPER_REPO_ROOT / "studio_server.py").is_file())
        self.assertEqual(HELPER_REPO_ROOT, REPO_ROOT)

    def test_path_inside_the_repo_is_written_repo_relative(self) -> None:
        inside = HELPER_REPO_ROOT / "screenshots" / "acme" / "home" / "home-fullpage.png"
        self.assertEqual(report_path(inside), "screenshots/acme/home/home-fullpage.png")

    def test_result_leaks_neither_the_checkout_nor_the_home_dir(self) -> None:
        out = report_path(HELPER_REPO_ROOT / "runs" / "acme" / "brand" / "brand.yaml")
        self.assertFalse(Path(out).is_absolute(), out)
        self.assertNotIn(str(HELPER_REPO_ROOT), out)
        self.assertNotIn(str(Path.home()), out)

    def test_a_string_argument_is_accepted(self) -> None:
        # Producers hold paths as both Path and str; both must normalise.
        inside = str(HELPER_REPO_ROOT / "runs" / "acme" / "brand" / "brand.yaml")
        self.assertEqual(report_path(inside), "runs/acme/brand/brand.yaml")

    def test_already_relative_path_is_unchanged(self) -> None:
        # A relative path resolves against the cwd; when that is the repo (the
        # documented way to run every lane) it stays exactly as given.
        self.assertEqual(
            report_path(Path("screenshots/acme/home/home-fullpage.png")),
            "screenshots/acme/home/home-fullpage.png",
        )

    def test_external_path_is_left_absolute(self) -> None:
        with TemporaryDirectory() as tmp:
            outside = Path(tmp).resolve() / "capture.png"
            self.assertEqual(report_path(outside), str(outside))

    def test_posix_separators(self) -> None:
        inside = HELPER_REPO_ROOT / "screenshots" / "acme" / "sub" / "shot.png"
        self.assertNotIn("\\", report_path(inside))

    def test_agrees_with_the_compose_replica_original(self) -> None:
        # compose_replica keeps its own copy for its own tests; the shared helper
        # must not have drifted from the behaviour it generalises.
        for candidate in (
            HELPER_REPO_ROOT / "screenshots" / "acme" / "home" / "home-fullpage.png",
            Path("runs/acme/brand/brand.yaml"),
            Path("/definitely/not/in/this/repo/shot.png"),
        ):
            self.assertEqual(
                report_path(candidate), compose_replica.report_path(candidate), candidate
            )


class ResolveReportPathTests(unittest.TestCase):
    def test_recorded_relative_path_resolves_against_the_repo_not_the_cwd(self) -> None:
        # The point of the inverse: an artifact stays readable from any cwd.
        self.assertEqual(
            resolve_report_path("runs/acme/brand/brand.yaml"),
            HELPER_REPO_ROOT / "runs" / "acme" / "brand" / "brand.yaml",
        )

    def test_recorded_absolute_path_is_returned_as_is(self) -> None:
        with TemporaryDirectory() as tmp:
            outside = Path(tmp).resolve() / "capture.html"
            self.assertEqual(resolve_report_path(str(outside)), outside)

    def test_round_trips_a_path_inside_the_repo(self) -> None:
        original = HELPER_REPO_ROOT / "screenshots" / "acme" / "acme.html"
        self.assertEqual(resolve_report_path(report_path(original)), original)


if __name__ == "__main__":
    unittest.main()
