#!/usr/bin/env python3
"""Regression tests: hand-authored lanes must resolve their measured bands too.

Two authoring conventions ship in this repo, and only one of them put a band
IDENTIFIER in ``provenance[]``:

  PROJECTED    ``tools/extract/project_sections_to_patterns`` stamps the band slug
               itself (``<page>-<grounding stem>``), so provenance resolves directly.
  HAND-AUTHORED the authoring pass wrote a semantic ROLE label there instead — a name
               for what the band does, not for which band it was. Those labels match
               no slug, and the role vocabulary the grounding itself declares repeats
               across many bands, so they are ambiguous by construction and can never
               become band keys.

Hand-authored patterns therefore resolved to NOTHING, and silently composed with no
measured band geometry at all — no padding, no rhythm, no device geometry. What they
do carry is an explicit reference to their source band in their own authoring notes,
which is read as a second provenance channel.

The refusal behaviour is as important as the resolution: matching is exact, and a
token that could name more than one band fills nothing rather than guessing, because
attributing one band's measured geometry to another is worse than attributing none.

Everything here is synthetic except the committed-lane guards, and every value is
generic (no brand palette, section naming, or copy).

Run:  ./venv/bin/python -m unittest \
          brand_pipeline.tests.test_measured_geometry_declared_bands
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BP = _REPO / "brand_pipeline"
if str(_BP) not in sys.path:
    sys.path.insert(0, str(_BP))

import yaml  # noqa: E402
import measured_geometry as mg  # noqa: E402

# The hand-authored lanes: role labels in provenance, source band in the notes.
ROLE_PROVENANCE_LANES = ("hubspot-v2", "woodwave-v2", "remote")
# A projected lane, for the guarantee that the primary channel still wins.
SLUG_PROVENANCE_LANE = _REPO / "runs" / "hubspot-v3" / "brand"


def _grounding(pad_top: int, pad_bottom: int, role: str = "section") -> dict:
    return {
        "sectionRole": role,
        "layout": {"structure": "band", "columns": 2, "gapPx": 32,
                   "approxPaddingPx": {"top": pad_top, "bottom": pad_bottom}},
        "typography": [{"role": "h1", "approxSizePx": 48}],
    }


def _write_flat_band(brand_dir: Path, filename: str, doc: dict) -> None:
    gdir = brand_dir / "evidence" / "grounding"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / filename).write_text(yaml.safe_dump(doc, sort_keys=False))


def _write_page_band(brand_dir: Path, page: str, filename: str, doc: dict) -> None:
    gdir = brand_dir / "evidence" / "pages" / page / "grounding"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / filename).write_text(yaml.safe_dump(doc, sort_keys=False))


def _write_rects(brand_dir: Path, rows: list[tuple[int, str, int]]) -> None:
    """A measured band census: ``(index, class list, height)`` per content section."""
    path = brand_dir / "evidence" / "section-rects.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schemaVersion": "section-rects.v1",
        "sections": [{"index": i, "classes": classes,
                      "rect": {"x": 0, "y": 0, "w": 1440, "h": h}}
                     for i, classes, h in rows],
    }))


def _aspect(pattern: dict, slot_name: str = "backdrop") -> str:
    slot = next(s for s in (pattern.get("contentShape") or {}).get("slots") or []
                if s.get("name") == slot_name)
    return str(slot.get("mediaAspect") or "")


def _hand_authored(pid: str, role_label: str, notes: list[str],
                   source_pages: list[str] | None = None) -> dict:
    """A pattern shaped like the hand-authored lanes: a role label in provenance and
    the source band named in the authoring notes."""
    pat = {
        "id": pid,
        "origin": "extracted",
        "provenance": [role_label],
        "changelog": [{"action": "created", "note": note} for note in notes],
        "contentShape": {"slots": [{"name": "heading", "role": "section-heading"}]},
    }
    if source_pages is not None:
        pat["sourcePages"] = list(source_pages)
    return pat


def _pad(pattern: dict) -> dict:
    return (pattern.get("contentShape") or {}).get("bandPadding") or {}


def _stripped(doc: dict) -> dict:
    """A library copy with the measured facts removed, so an already-authored lane
    still exercises the enricher (which is fill-absent-only)."""
    out = copy.deepcopy(doc)
    for pat in out.get("patterns") or []:
        cs = pat.get("contentShape")
        if isinstance(cs, dict):
            for key in mg.ALL_FIELDS | {"deviceGeometry"}:
                cs.pop(key, None)
    return out


# ── the declared-reference channel ────────────────────────────────────────────

class DeclaredBandTokenTests(unittest.TestCase):
    def test_a_single_declared_band_is_read(self):
        pat = _hand_authored("p", "closing-cta",
                             ["grounding section-04: measured from the source band"])
        self.assertEqual(mg.declared_band_tokens(pat), ["section-04"])

    def test_notes_naming_two_bands_are_refused(self):
        """Unlike ``provenance[]``, note order carries no first-source contract, so
        two declared bands is ambiguity — not a list to pick the head of."""
        pat = _hand_authored("p", "role", ["grounding section-02 and section-05"])
        self.assertEqual(mg.declared_band_tokens(pat), [])

    def test_two_notes_disagreeing_are_refused(self):
        pat = _hand_authored("p", "role", ["from section-02", "reworked section-07"])
        self.assertEqual(mg.declared_band_tokens(pat), [])

    def test_the_same_band_repeated_across_notes_is_still_one_band(self):
        pat = _hand_authored("p", "role", ["from section-03", "section-03 revisited"])
        self.assertEqual(mg.declared_band_tokens(pat), ["section-03"])

    def test_notes_without_a_band_reference_declare_nothing(self):
        pat = _hand_authored("p", "role", ["first extraction", "spacing pass"])
        self.assertEqual(mg.declared_band_tokens(pat), [])

    def test_a_malformed_changelog_is_not_fatal(self):
        pat = _hand_authored("p", "role", [])
        pat["changelog"] = ["not a mapping", None, {"note": "from section-01"}]
        self.assertEqual(mg.declared_band_tokens(pat), ["section-01"])


class RoleLabelResolutionTests(unittest.TestCase):
    def _lane(self, td: str) -> Path:
        bd = Path(td)
        _write_flat_band(bd, "section-00-first.yaml", _grounding(40, 40, "hero"))
        _write_flat_band(bd, "section-01-second.yaml", _grounding(80, 80, "features"))
        _write_flat_band(bd, "section-02-third.yaml", _grounding(120, 120, "features"))
        return bd

    def test_a_role_label_alone_resolves_nothing(self):
        """The label is not a band key: it matches no slug, and the role the
        grounding declares repeats across bands."""
        with tempfile.TemporaryDirectory() as td:
            bd = self._lane(td)
            bands = mg._load_grounding(bd)
            pat = _hand_authored("p", "feature-showcase", [])
            self.assertIsNone(mg.resolve_pattern_band(pat, bands))

    def test_the_declared_band_resolves_the_pattern(self):
        with tempfile.TemporaryDirectory() as td:
            bd = self._lane(td)
            pat = _hand_authored("p", "feature-showcase",
                                 ["grounding section-02: two-column band"])
            doc = {"patterns": [pat]}
            summary = mg.enrich_layout_library(doc, bd, fields=mg.FIDELITY_FIELDS)
            self.assertEqual(mg.unresolved_patterns(doc, bd), [])
        self.assertIn("bandPadding", summary["p"])
        self.assertEqual(_pad(pat), {"top": "7.5rem", "bottom": "7.5rem"})

    def test_each_pattern_gets_its_own_declared_bands_geometry(self):
        """Two patterns carrying the SAME role label must still land on different
        bands — the whole point of resolving the declared reference."""
        with tempfile.TemporaryDirectory() as td:
            bd = self._lane(td)
            first = _hand_authored("first", "feature-showcase", ["from section-01"])
            second = _hand_authored("second", "feature-showcase", ["from section-02"])
            mg.enrich_layout_library({"patterns": [first, second]}, bd,
                                     fields=mg.FIDELITY_FIELDS)
        self.assertEqual(_pad(first), {"top": "5rem", "bottom": "5rem"})
        self.assertEqual(_pad(second), {"top": "7.5rem", "bottom": "7.5rem"})

    def test_resolvable_provenance_wins_over_the_notes(self):
        """The declared reference is a FALLBACK. A pattern whose provenance names a
        band is measured from that band even when its notes name another."""
        with tempfile.TemporaryDirectory() as td:
            bd = self._lane(td)
            pat = _hand_authored("p", "section-00", ["later reworked from section-02"])
            mg.enrich_layout_library({"patterns": [pat]}, bd,
                                     fields=mg.FIDELITY_FIELDS)
        self.assertEqual(_pad(pat), {"top": "2.5rem", "bottom": "2.5rem"})

    def test_a_declared_band_that_does_not_exist_fills_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            bd = self._lane(td)
            pat = _hand_authored("p", "role", ["from section-99"])
            doc = {"patterns": [pat]}
            summary = mg.enrich_layout_library(doc, bd, fields=mg.FIDELITY_FIELDS)
            self.assertEqual(mg.unresolved_patterns(doc, bd), ["p"])
        self.assertEqual(summary, {})
        self.assertNotIn("bandPadding", pat["contentShape"])


class DeclaredReferenceAmbiguityTests(unittest.TestCase):
    """A declared token that could name more than one band must REFUSE."""

    def test_two_bands_sharing_an_ordinal_refuse_the_declared_token(self):
        """One capture wrote the same ordinal twice, so ``section-01`` names two
        bands with different measured geometry. Guessing would silently attribute
        one band's padding to a pattern from the other."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_flat_band(bd, "section-01-alpha.yaml", _grounding(40, 40))
            _write_flat_band(bd, "section-01-beta.yaml", _grounding(200, 200))
            bands = mg._load_grounding(bd)
            self.assertEqual(len(bands), 2)
            pat = _hand_authored("p", "role", ["from section-01"])
            self.assertIsNone(mg.resolve_pattern_band(pat, bands))
            doc = {"patterns": [pat]}
            summary = mg.enrich_layout_library(doc, bd, fields=mg.FIDELITY_FIELDS)
            self.assertEqual(mg.unresolved_patterns(doc, bd), ["p"])
        self.assertEqual(summary, {})
        self.assertEqual(_pad(pat), {})

    def test_the_same_ordinal_on_two_pages_refuses_without_a_declared_page(self):
        """On a page-qualified lane a bare ordinal is ambiguous across pages, and a
        hand-authored pattern declares no ``sourcePages[]`` to narrow it."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_page_band(bd, "pageone", "section-01-div.yaml", _grounding(40, 40))
            _write_page_band(bd, "pagetwo", "section-01-div.yaml", _grounding(200, 200))
            bands = mg._load_grounding(bd)
            pat = _hand_authored("p", "role", ["from section-01"])
            self.assertIsNone(mg.resolve_pattern_band(pat, bands))
            self.assertEqual(mg.unresolved_patterns({"patterns": [pat]}, bd), ["p"])

    def test_source_pages_narrow_an_otherwise_ambiguous_declared_token(self):
        """The page contract that already exists is honoured: a declared ordinal plus
        a declared page names exactly one band."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_page_band(bd, "pageone", "section-01-div.yaml", _grounding(40, 40))
            _write_page_band(bd, "pagetwo", "section-01-div.yaml", _grounding(200, 200))
            pat = _hand_authored("p", "role", ["from section-01"], ["pagetwo"])
            mg.enrich_layout_library({"patterns": [pat]}, bd,
                                     fields=mg.FIDELITY_FIELDS)
        self.assertEqual(_pad(pat), {"top": "12.5rem", "bottom": "12.5rem"})

    def test_two_declared_pages_sharing_the_ordinal_still_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_page_band(bd, "pageone", "section-01-div.yaml", _grounding(40, 40))
            _write_page_band(bd, "pagetwo", "section-01-div.yaml", _grounding(200, 200))
            bands = mg._load_grounding(bd)
            pat = _hand_authored("p", "role", ["from section-01"],
                                 ["pageone", "pagetwo"])
            self.assertIsNone(mg.resolve_pattern_band(pat, bands))


# ── the band's rect must be its OWN, not whatever sits at its ordinal ─────────

class RectOrdinalOffsetTests(unittest.TestCase):
    """A band's ordinal counts the chrome bands cropped alongside it; the rect census
    lists content sections only. On a lane whose page header became its own crop the
    two therefore disagree by one, and every band was measured against its neighbour.
    """

    def _offset_lane(self, td: str) -> Path:
        bd = Path(td)
        # ordinal 00 is the page header (chrome) — it has no census row at all, so
        # every later ordinal sits one ahead of its own census index.
        _write_flat_band(bd, "section-00-header.yaml", _grounding(10, 10, "navbar"))
        _write_flat_band(bd, "section-01-band-alpha.yaml", _grounding(40, 40, "hero"))
        _write_flat_band(bd, "section-02-band-beta.yaml", _grounding(80, 80, "features"))
        _write_rects(bd, [(0, "band-alpha", 900), (1, "band-beta", 300)])
        return bd

    def _pattern(self, pid: str, note: str) -> dict:
        pat = _hand_authored(pid, "role", [note])
        pat["contentShape"]["slots"].append(
            {"name": "backdrop", "role": "full-bleed-background", "type": "media",
             "width": "full-bleed", "mediaAspect": "wide"})
        return pat

    def test_a_band_measures_its_own_rect_across_the_offset(self):
        with tempfile.TemporaryDirectory() as td:
            bd = self._offset_lane(td)
            pat = self._pattern("p", "from section-01")
            mg.enrich_layout_library({"patterns": [pat]}, bd, fields=mg.ALL_FIELDS)
        # ordinal 1, but its OWN census row is index 0 (h=900) — not index 1 (h=300)
        self.assertEqual(_aspect(pat), "1440 / 900")

    def test_the_neighbouring_bands_rect_is_never_borrowed(self):
        with tempfile.TemporaryDirectory() as td:
            bd = self._offset_lane(td)
            first = self._pattern("first", "from section-01")
            second = self._pattern("second", "from section-02")
            mg.enrich_layout_library({"patterns": [first, second]}, bd,
                                     fields=mg.ALL_FIELDS)
        self.assertEqual(_aspect(first), "1440 / 900")
        self.assertEqual(_aspect(second), "1440 / 300")

    def test_an_identity_naming_no_census_row_measures_nothing(self):
        """A chrome band has no census row. Refusing leaves the coarse enum in place
        rather than stamping a content band's height onto it."""
        with tempfile.TemporaryDirectory() as td:
            bd = self._offset_lane(td)
            pat = self._pattern("p", "from section-00")
            mg.enrich_layout_library({"patterns": [pat]}, bd, fields=mg.ALL_FIELDS)
        self.assertEqual(_aspect(pat), "wide")

    def test_an_ambiguous_identity_measures_nothing(self):
        """Two census rows share a class list and neither sits at the band's ordinal,
        so the band's identity names two candidate rows. Refuse."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_flat_band(bd, "section-00-header.yaml", _grounding(10, 10))
            _write_flat_band(bd, "section-03-shared.yaml", _grounding(40, 40))
            _write_rects(bd, [(0, "shared", 500), (1, "shared", 700)])
            pat = self._pattern("p", "from section-03")
            mg.enrich_layout_library({"patterns": [pat]}, bd, fields=mg.ALL_FIELDS)
        self.assertEqual(_aspect(pat), "wide")

    def test_an_aligned_lane_uses_its_indexed_row_directly(self):
        """The common case: ordinals and census indices agree, including when several
        bands legitimately share one class list."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_flat_band(bd, "section-00-shared.yaml", _grounding(40, 40))
            _write_flat_band(bd, "section-01-shared.yaml", _grounding(80, 80))
            _write_rects(bd, [(0, "shared", 500), (1, "shared", 700)])
            first = self._pattern("first", "from section-00")
            second = self._pattern("second", "from section-01")
            mg.enrich_layout_library({"patterns": [first, second]}, bd,
                                     fields=mg.ALL_FIELDS)
        self.assertEqual(_aspect(first), "1440 / 500")
        self.assertEqual(_aspect(second), "1440 / 700")


# ── committed lanes ───────────────────────────────────────────────────────────

class CommittedRoleProvenanceLaneTests(unittest.TestCase):
    """The reported gap: three shipped lanes resolved no band at all."""

    def _lane(self, name: str) -> tuple[Path, dict]:
        brand_dir = _REPO / "runs" / name / "brand"
        library = brand_dir / "layout-library.yaml"
        if not library.is_file():
            self.skipTest(f"lane {name} is not present")
        return brand_dir, yaml.safe_load(library.read_text())

    def test_every_extracted_pattern_now_resolves(self):
        for name in ROLE_PROVENANCE_LANES:
            with self.subTest(lane=name):
                brand_dir, doc = self._lane(name)
                self.assertEqual(mg.unresolved_patterns(doc, brand_dir), [])

    def test_provenance_alone_would_still_resolve_nothing(self):
        """Pins WHY these lanes needed a second channel: their provenance tokens are
        role labels, so dropping the declared reference resolves nothing at all."""
        for name in ROLE_PROVENANCE_LANES:
            with self.subTest(lane=name):
                brand_dir, doc = self._lane(name)
                bands = mg._load_grounding(brand_dir)
                for pat in doc["patterns"]:
                    label_only = {k: v for k, v in pat.items() if k != "changelog"}
                    self.assertIsNone(
                        mg.resolve_pattern_band(label_only, bands),
                        f"{pat['id']}: a role label must not resolve a band")

    def test_each_pattern_resolves_to_the_band_its_notes_declare(self):
        for name in ROLE_PROVENANCE_LANES:
            with self.subTest(lane=name):
                brand_dir, doc = self._lane(name)
                bands = mg._load_grounding(brand_dir)
                for pat in doc["patterns"]:
                    declared = mg.declared_band_tokens(pat)
                    band = mg.resolve_pattern_band(pat, bands)
                    self.assertEqual(len(declared), 1, f"{pat['id']} declares one band")
                    self.assertTrue(
                        band.slug.startswith(declared[0]),
                        f"{pat['id']} measured from {band.slug}, declared {declared[0]}")

    def test_measured_facts_now_flow_and_trace_to_the_declared_band(self):
        for name in ROLE_PROVENANCE_LANES:
            with self.subTest(lane=name):
                brand_dir, doc = self._lane(name)
                bands = mg._load_grounding(brand_dir)
                enriched = _stripped(doc)
                summary = mg.enrich_layout_library(enriched, brand_dir,
                                                   fields=mg.FIDELITY_FIELDS)
                self.assertTrue(summary, "the lane must gain measured facts")
                checked = 0
                for pat in enriched["patterns"]:
                    band = mg.resolve_pattern_band(pat, bands)
                    if band is None:
                        continue
                    src = (band.doc.get("layout") or {}).get("approxPaddingPx") or {}
                    expected = {k: mg._rem(float(src[k])) for k in ("top", "bottom")
                                if src.get(k) is not None}
                    if not expected:
                        continue
                    self.assertEqual(
                        _pad(pat), expected,
                        f"{pat['id']} padding did not come from {band.slug}")
                    checked += 1
                self.assertGreater(checked, 0, "no measured padding was verified")


class ProjectedLaneIsUnaffectedTests(unittest.TestCase):
    def test_slug_provenance_still_resolves_through_provenance(self):
        """The projected lanes must not start depending on the fallback channel."""
        library = SLUG_PROVENANCE_LANE / "layout-library.yaml"
        if not library.is_file():
            self.skipTest("projected lane is not present")
        doc = yaml.safe_load(library.read_text())
        bands = mg._load_grounding(SLUG_PROVENANCE_LANE)
        for pat in doc["patterns"]:
            without_notes = {k: v for k, v in pat.items() if k != "changelog"}
            band = mg.resolve_pattern_band(without_notes, bands)
            self.assertIsNotNone(band, f"{pat['id']} must resolve on provenance alone")


if __name__ == "__main__":
    unittest.main()
