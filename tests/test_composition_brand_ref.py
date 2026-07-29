"""`composition.json` records the brand it was written against repo-relative.

`brand.ref` held this checkout's absolute path, which put every `composition.json`
outside the committed Studio subset (`tools/track_studio_subset.py` refuses any
text artifact carrying it). The producer now records it the way
`compose_replica.report_path()` already did, and both readers resolve it against
the repo root rather than the process working directory — otherwise a relative
ref would only be readable from the one cwd that happened to produce it.

Existing stored compositions are NOT migrated: regenerating one is a model call.
They stay untracked until their lane is re-generated.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "brand_pipeline"))

from screenshot_to_template import repo_paths  # noqa: E402

import section_wireframe as sw  # noqa: E402


def test_a_brand_inside_the_repo_is_recorded_relative_to_it():
    inside = repo_paths.REPO_ROOT / "runs" / "acme" / "brand" / "brand.yaml"
    assert repo_paths.report_path(inside) == "runs/acme/brand/brand.yaml"


def test_a_recorded_ref_resolves_against_the_repo_not_the_cwd(tmp_path, monkeypatch):
    monkeypatch.setattr(repo_paths, "REPO_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path.parent)
    brand = tmp_path / "runs" / "acme" / "brand" / "brand.yaml"
    brand.parent.mkdir(parents=True)
    brand.write_text("brand:\n  name: Acme\n")

    resolved = repo_paths.resolve_report_path("runs/acme/brand/brand.yaml")
    assert resolved == brand
    assert resolved.exists()


def test_the_wireframe_reader_finds_a_brand_named_by_a_relative_ref(tmp_path, monkeypatch):
    monkeypatch.setattr(repo_paths, "REPO_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path.parent)
    brand = tmp_path / "runs" / "acme" / "brand" / "brand.yaml"
    brand.parent.mkdir(parents=True)
    brand.write_text("brand:\n  name: Acme\n")

    doc, _registry = sw._brand_context({"brand": {"ref": "runs/acme/brand/brand.yaml"}})
    assert (doc.get("brand") or {}).get("name") == "Acme"


def test_a_genuinely_external_brand_path_is_left_absolute(tmp_path, monkeypatch):
    monkeypatch.setattr(repo_paths, "REPO_ROOT", tmp_path / "repo")
    outside = tmp_path / "elsewhere" / "brand.yaml"
    outside.parent.mkdir(parents=True)
    outside.write_text("brand:\n  name: Outside\n")

    recorded = repo_paths.report_path(outside)
    assert Path(recorded).is_absolute()
    assert repo_paths.resolve_report_path(recorded) == outside
