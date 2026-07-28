"""Rules that decide what a clean clone gets to see, so they cannot drift silently.

The interesting failures here are quiet ones: a glob that crosses a directory
separator pulls a 160 MB build tree back into the commit, and a `.gitignore`
negation that names a deep path without opening its parents is simply ignored by
git. Both look fine in a diff.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import track_studio_subset as tss  # noqa: E402


def test_star_stops_at_a_separator():
    assert tss._match("home/screenshot.png", "*/screenshot.*")
    assert not tss._match("brand/framework/single/site.html", "*/single/**")
    assert tss._match("brand/single/site.html", "*/single/**")


def test_doublestar_spans_separators():
    assert tss._match("brand/compose/replica/assets/a.png", "brand/compose/**")
    assert tss._match("a/b/c/node_modules/x/y.js", "**/node_modules/**")
    assert tss._match("notes.bak", "**/*.bak")


def test_run_root_docs_do_not_match_nested_docs():
    assert tss._match("learnings.md", "*.md")
    assert not tss._match("brand/compose/replica/report.md", "*.md")


def test_js_workspace_is_dropped_wholesale(tmp_path):
    run = tmp_path / "proj"
    single = run / "item" / "single"
    build = single / "app"
    build.mkdir(parents=True)
    (single / "site-claude.html").write_text("<html></html>")
    (build / "package.json").write_text("{}")
    (build / "main.js").write_text("x")

    result = tss.classify_run(run)
    kept = {p.relative_to(run).as_posix() for p, _, _ in result["kept"]}
    assert kept == {"item/single/site-claude.html"}
    reasons = {p.relative_to(run).as_posix(): why for p, _, why in result["dropped"]}
    assert "JS build workspace" in reasons["item/single/app/main.js"]


def test_local_absolute_paths_are_held_back(tmp_path):
    run = tmp_path / "proj"
    (run / "brand").mkdir(parents=True)
    (run / "brand" / "brand.md").write_text(f"produced in {tss.REPO_ROOT}\n")
    (run / "brand" / "brand.yaml").write_text("name: x\n")

    result = tss.classify_run(run)
    kept = {p.name for p, _, _ in result["kept"]}
    assert kept == {"brand.yaml"}

    allowed = tss.classify_run(run, allow_local_paths=True)
    assert {p.name for p, _, _ in allowed["kept"]} == {"brand.yaml", "brand.md"}


def test_gitignore_opens_every_parent_before_naming_a_file():
    lines = tss.gitignore_block([_fake_plan(["runs/p/brand/catalog/catalog.json"])])
    assert lines.index("!runs/") < lines.index("!runs/p/")
    assert lines.index("!runs/p/") < lines.index("!runs/p/brand/")
    assert lines.index("!runs/p/brand/") < lines.index("!runs/p/brand/catalog/")
    # Each opened directory is immediately re-closed, so siblings stay ignored.
    for opened in ("runs", "runs/p", "runs/p/brand", "runs/p/brand/catalog"):
        assert lines.index(f"!{opened}/") + 1 == lines.index(f"{opened}/*")
    assert lines[-1] == "!runs/p/brand/catalog/catalog.json"


def test_only_shown_images_survive(tmp_path):
    """A lane keeps its media and one thumbnail; its spare captures do not."""
    run = tmp_path / "proj"
    lane = run / "brand" / "compose" / "replica"
    (lane / "assets").mkdir(parents=True)
    (lane / "shots").mkdir()
    (lane / "index.html").write_text('<img src="assets/hero.png"><img src="inline-diagram.png">')
    (lane / "assets" / "hero.png").write_bytes(b"a")
    (lane / "inline-diagram.png").write_bytes(b"b")
    (lane / "replica-fullpage-375.png").write_bytes(b"d")
    (lane / "replica-fullpage.png").write_bytes(b"c")
    (lane / "shots" / "contact-sheet.png").write_bytes(b"e")
    # The server breaks a scoring tie on mtime, so pin them rather than racing.
    os.utime(lane / "replica-fullpage-375.png", (1, 1))
    os.utime(lane / "replica-fullpage.png", (2, 2))
    os.utime(lane / "shots" / "contact-sheet.png", (3, 3))

    kept = {p.name for p, _, _ in tss.classify_run(run)["kept"]}
    assert kept == {"index.html", "hero.png", "inline-diagram.png", "replica-fullpage.png"}


def test_sections_gallery_thumbnail_is_kept_alongside_the_generic_pick(tmp_path):
    run = tmp_path / "proj"
    lane = run / "brand" / "sections"
    (lane / "shots").mkdir(parents=True)
    (lane / "index.html").write_text("<html></html>")
    (lane / "shots" / "gallery.png").write_bytes(b"g")
    (lane / "after-fullpage-1440.png").write_bytes(b"f")

    kept = {p.name for p, _, _ in tss.classify_run(run)["kept"]}
    assert kept == {"index.html", "gallery.png", "after-fullpage-1440.png"}


def test_a_lane_that_is_a_link_into_the_repo_still_travels(tmp_path, monkeypatch):
    """A lane symlinked to a tracked sibling is the link, not a copy of it."""
    repo = tmp_path
    monkeypatch.setattr(tss, "REPO_ROOT", repo)
    real = repo / "experiments" / "arm-a"
    real.mkdir(parents=True)
    (real / "index.html").write_text("<html></html>")
    run = repo / "runs" / "proj"
    lane = run / "brand" / "variants" / "arm-a"
    lane.mkdir(parents=True)
    (lane / "index.html").symlink_to(real / "index.html")
    (lane / "label.txt").write_text("arm a")
    outside = lane / "elsewhere.html"
    outside.symlink_to(tmp_path.parent / "not-in-the-repo.html")

    out = tss.classify_run(run)
    assert [p.name for p, _ in out["links"]] == ["index.html"]
    assert ("elsewhere.html", "symlink to a path outside the repo") in [
        (p.name, why) for p, _, why in out["dropped"]
    ]
    # The file behind the link is counted where it lives, not twice.
    assert all("experiments" not in p.parts for p, _, _ in out["kept"])


def test_title_keeps_the_version_token_lowercase():
    assert tss._pretty_title("hubspot-v3", "HubSpot") == "HubSpot v3"
    assert tss._pretty_title("hubspot-v3", "") == "Hubspot v3"
    assert tss._pretty_title("relume-test", "") == "Relume Test"


def _fake_plan(rels: list[str]) -> dict:
    paths = [tss.REPO_ROOT / r for r in rels]
    return {
        "run": {"kept": [(p, 0, "") for p in paths]},
        "capture": {"kept": [], "link": None},
        "config": [],
    }
