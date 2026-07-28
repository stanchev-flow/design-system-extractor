"""The replica report records the compared source screenshot repo-relative.

`replica-report.json` / `.md` are text artifacts of a public repo. Writing the
compared screenshot's ABSOLUTE path into them both names the machine the run
happened on and makes the files untrackable: the subset tracker
(`tools/track_studio_subset.py`) holds back any text artifact containing this
checkout's absolute path, which is why the two most useful fidelity artifacts
were missing from the committed Studio subset.

A path inside the repo must therefore be written relative to the repo root, and
a genuinely external path must be left alone — shortening that one would make it
meaningless.
"""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "brand_pipeline"))

import compose_replica  # noqa: E402


class ReportPathTests(unittest.TestCase):
    def test_path_inside_the_repo_is_written_repo_relative(self) -> None:
        inside = compose_replica.REPO_ROOT / "screenshots" / "acme" / "home" / "home-fullpage.png"
        self.assertEqual(
            compose_replica.report_path(inside),
            "screenshots/acme/home/home-fullpage.png",
        )

    def test_result_is_not_absolute_and_leaks_no_checkout_path(self) -> None:
        inside = compose_replica.REPO_ROOT / "runs" / "acme" / "brand" / "shot.png"
        out = compose_replica.report_path(inside)
        self.assertFalse(Path(out).is_absolute(), out)
        self.assertNotIn(str(compose_replica.REPO_ROOT), out)
        self.assertNotIn(str(Path.home()), out)

    def test_already_relative_path_is_unchanged(self) -> None:
        # A relative path resolves against the cwd; when that is the repo (the
        # documented way to run the lane) it stays exactly as given.
        self.assertEqual(
            compose_replica.report_path(Path("screenshots/acme/home/home-fullpage.png")),
            "screenshots/acme/home/home-fullpage.png",
        )

    def test_external_path_is_left_absolute(self) -> None:
        with TemporaryDirectory() as tmp:
            outside = Path(tmp).resolve() / "capture.png"
            self.assertEqual(compose_replica.report_path(outside), str(outside))

    def test_posix_separators(self) -> None:
        inside = compose_replica.REPO_ROOT / "screenshots" / "acme" / "sub" / "shot.png"
        self.assertNotIn("\\", compose_replica.report_path(inside))

    def test_repo_root_is_the_checkout(self) -> None:
        # Guards the helper's premise: REPO_ROOT is the repo, not brand_pipeline/.
        self.assertTrue((compose_replica.REPO_ROOT / "studio_server.py").is_file())


if __name__ == "__main__":
    unittest.main()
