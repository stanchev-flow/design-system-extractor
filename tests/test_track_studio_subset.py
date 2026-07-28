"""Rules that decide what a clean clone gets to see, so they cannot drift silently.

The interesting failures here are quiet ones: a glob that crosses a directory
separator pulls a 160 MB build tree back into the commit, and a `.gitignore`
negation that names a deep path without opening its parents is simply ignored by
git. Both look fine in a diff.
"""

from __future__ import annotations

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


def _fake_plan(rels: list[str]) -> dict:
    paths = [tss.REPO_ROOT / r for r in rels]
    return {
        "run": {"kept": [(p, 0, "") for p in paths]},
        "capture": {"kept": [], "link": None},
        "config": [],
    }
