"""How a run artifact should record a filesystem path.

Run output under `runs/` is a text artifact of a PUBLIC repo, and a subset of it
is committed so a clone has real Studio projects to open
(`tools/track_studio_subset.py`). That tracker refuses to track any text file
containing the checkout's absolute path, because the path embeds a username —
so a report that records `/Users/<someone>/.../runs/<brand>/...` both names the
machine the run happened on and silently drops itself out of the committed
subset, taking its Studio tab with it.

`report_path()` is the one answer to that, first written for
`brand_pipeline/compose_replica.py` and shared from here so every producer that
records a path answers it the same way. It lives in the installed package
because the producers are spread across three trees that cannot import each
other: `brand_pipeline/`, `tools/extract/` and repo-root scripts.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def report_path(path: str | Path) -> str:
    """A path as an artifact should record it: repo-relative when it is in the repo.

    Repo-relative keeps the path a usable reference for anyone holding the repo;
    a genuinely external path is recorded as given, since shortening that one
    would make it meaningless. Separators are always POSIX so the same run
    output reads identically wherever it was produced.
    """
    try:
        return Path(path).resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


def resolve_report_path(recorded: str | Path) -> Path:
    """The inverse of `report_path()`: a recorded path back to a real one.

    A recorded relative path was written relative to the REPO ROOT, so it is
    joined there and not to the process working directory — otherwise an
    artifact would only be re-readable from the one cwd it was produced in. An
    absolute value is a genuinely external path and is already real.
    """
    path = Path(recorded)
    return path if path.is_absolute() else REPO_ROOT / path
