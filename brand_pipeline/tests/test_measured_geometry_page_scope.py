#!/usr/bin/env python3
"""Regression tests for PAGE-QUALIFIED measured-geometry grounding.

The enricher used to index a lane's grounding by a bare section NUMBER parsed out
of ``evidence/grounding/section-*.yaml``. That has two failure modes:

  DATA LOSS      a multi-page lane names its grounding ``<page>-section-NN-*.yaml``
                 (and keeps the unabridged capture under
                 ``evidence/pages/<page>/grounding/``), so the glob matched nothing,
                 the index came back empty, and every measured band fact was
                 silently dropped.
  MIS-ATTRIBUTION two pages both have a ``section-01``, so a number-only key
                 collides and one page's measured geometry lands on another page's
                 pattern — worse than filling nothing, and invisible in the output.

Band identity is therefore the page-qualified slug the rest of the pipeline already
uses (``tools/extract/project_sections_to_patterns.load_bands`` →
``provenance[]`` / ``sourcePages[]``).

Everything here is synthetic except the committed-lane guards, and every value is
generic (no brand palette, section naming, or copy).

Run:  ./venv/bin/python -m unittest \
          brand_pipeline.tests.test_measured_geometry_page_scope
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

MULTI_PAGE_LANE = _REPO / "runs" / "greenhouse-4" / "brand"
SINGLE_PAGE_LANE = _REPO / "runs" / "hubspot-v3" / "brand"


# ── synthetic lane builders ───────────────────────────────────────────────────

def _grounding(pad_top: int, pad_bottom: int, *, columns: int = 3,
               gap_px: int = 32, heading_px: int = 48) -> dict:
    """A minimal grounded band carrying the measured facts the enricher reads."""
    return {
        "sectionRole": "section",
        "layout": {
            "structure": "band",
            "columns": columns,
            "gapPx": gap_px,
            "approxPaddingPx": {"top": pad_top, "bottom": pad_bottom},
        },
        "relationalSpacingPx": {
            "eyebrowToHeading": 12, "headingToBody": 16, "bodyToCta": 24,
        },
        "typography": [{"role": "h1", "approxSizePx": heading_px}],
    }


def _pattern(pid: str, provenance: list[str],
             source_pages: list[str] | None = None) -> dict:
    pat = {
        "id": pid,
        "origin": "extracted",
        "provenance": list(provenance),
        "contentShape": {"slots": [
            {"name": "heading", "role": "section-heading", "type": "content"},
            {"name": "backdrop", "role": "full-bleed-background", "type": "media",
             "width": "full-bleed", "mediaAspect": "wide"},
        ]},
    }
    if source_pages is not None:
        pat["sourcePages"] = list(source_pages)
    return pat


def _write_rects(path: Path, rows: list[tuple[int, int, int]],
                 classes: str = "div") -> None:
    """A measured band census. Rows carry ``classes`` exactly as a real census does:
    that class list is what a band's crop (and so its grounding file) is named after,
    and it is how a band is matched to its own row rather than to whatever row happens
    to sit at its ordinal."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schemaVersion": "section-rects.v1",
        "sections": [{"index": i, "classes": classes,
                      "rect": {"x": 0, "y": 0, "w": w, "h": h}}
                     for i, w, h in rows],
    }))


def _write_page_band(brand_dir: Path, page: str, filename: str,
                     doc: dict) -> None:
    gdir = brand_dir / "evidence" / "pages" / page / "grounding"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / filename).write_text(yaml.safe_dump(doc, sort_keys=False))


def _write_flat_band(brand_dir: Path, filename: str, doc: dict) -> None:
    gdir = brand_dir / "evidence" / "grounding"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / filename).write_text(yaml.safe_dump(doc, sort_keys=False))


def _pad(pattern: dict) -> dict:
    return (pattern.get("contentShape") or {}).get("bandPadding") or {}


def _stripped(doc: dict) -> dict:
    """A copy of a library with the measured facts removed.

    Enrichment is fill-absent-only, so a lane whose shipped library was ALREADY
    enriched by its authoring run legitimately gains nothing on a re-run. Asserting
    that the enricher refills facts therefore has to start from a library that is
    missing them, or the assertion measures the lane's current on-disk state instead
    of the enricher's behaviour."""
    out = copy.deepcopy(doc)
    for pat in out.get("patterns") or []:
        cs = pat.get("contentShape")
        if isinstance(cs, dict):
            for key in mg.ALL_FIELDS | {"deviceGeometry"}:
                cs.pop(key, None)
    return out


# ── loading: both naming conventions ──────────────────────────────────────────

class GroundingLoadTests(unittest.TestCase):
    def test_page_prefixed_grounding_loads(self):
        """A multi-page lane's ``evidence/pages/<page>/grounding/`` bands load and
        carry their page — the case that used to return an empty index."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_page_band(bd, "home", "section-01-div.yaml", _grounding(140, 120))
            _write_page_band(bd, "other", "section-02-block.yaml", _grounding(80, 80))
            bands = mg._load_grounding(bd)
        self.assertEqual(set(bands), {"home-section-01-div",
                                      "other-section-02-block"})
        self.assertEqual(bands["home-section-01-div"].page, "home")
        self.assertEqual(bands["home-section-01-div"].index, 1)
        self.assertEqual(bands["other-section-02-block"].page, "other")
        self.assertEqual(bands["other-section-02-block"].index, 2)

    def test_bare_single_page_names_still_load(self):
        """The older single-page lanes name bands ``section-NN-*.yaml`` in one flat
        directory with no page tree at all. They must keep loading unchanged."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_flat_band(bd, "section-00-header.yaml", _grounding(64, 64))
            _write_flat_band(bd, "section-01-body.yaml", _grounding(96, 96))
            bands = mg._load_grounding(bd)
        self.assertEqual(set(bands), {"section-00-header", "section-01-body"})
        for band in bands.values():
            self.assertEqual(band.page, "", "a single-page lane has no page key")
        self.assertEqual(bands["section-00-header"].index, 0)
        self.assertEqual(bands["section-01-body"].index, 1)

    def test_flat_merged_bundle_recovers_the_page_from_the_prefix(self):
        """A multi-page lane also promotes a merged, page-prefixed subset into the
        flat directory. Those bands must be attributed to the page they name, and
        must not duplicate the per-page copy of the same band."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_page_band(bd, "home", "section-01-div.yaml", _grounding(140, 120))
            (bd / "evidence" / "pages" / "extra").mkdir(parents=True)
            _write_flat_band(bd, "home-section-01-div.yaml", _grounding(140, 120))
            _write_flat_band(bd, "extra-section-04-block.yaml", _grounding(40, 40))
            bands = mg._load_grounding(bd)
        self.assertEqual(set(bands), {"home-section-01-div",
                                      "extra-section-04-block"})
        self.assertEqual(bands["extra-section-04-block"].page, "extra")
        self.assertEqual(bands["extra-section-04-block"].index, 4)

    def test_longer_page_name_wins_the_prefix(self):
        """A page key that prefixes another ("a" vs "a-b") must not steal the longer
        page's flat-bundle bands."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            for page in ("alpha", "alpha-beta"):
                (bd / "evidence" / "pages" / page).mkdir(parents=True)
            _write_flat_band(bd, "alpha-beta-section-03-x.yaml", _grounding(50, 50))
            bands = mg._load_grounding(bd)
        self.assertEqual(bands["alpha-beta-section-03-x"].page, "alpha-beta")
        self.assertEqual(bands["alpha-beta-section-03-x"].index, 3)

    def test_unreadable_band_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_page_band(bd, "home", "section-00-ok.yaml", _grounding(20, 20))
            (bd / "evidence" / "pages" / "home" / "grounding"
             / "section-01-bad.yaml").write_text("{[not: valid: yaml")
            bands = mg._load_grounding(bd)
        self.assertIn("home-section-00-ok", bands)
        self.assertNotIn("home-section-01-bad", bands)


# ── page attribution: the collision that must never happen ────────────────────

class PageAttributionTests(unittest.TestCase):
    """Two pages that BOTH have the same section number."""

    def _two_page_lane(self, td: str) -> Path:
        bd = Path(td)
        # identical ordinals, deliberately different measured geometry
        _write_page_band(bd, "pageone", "section-01-div.yaml", _grounding(140, 120))
        _write_page_band(bd, "pagetwo", "section-01-div.yaml", _grounding(180, 160))
        _write_rects(bd / "evidence" / "pages" / "pageone" / "section-rects.json",
                     [(0, 1440, 500), (1, 1440, 600)])
        _write_rects(bd / "evidence" / "pages" / "pagetwo" / "section-rects.json",
                     [(0, 1440, 700), (1, 1440, 800)])
        # the lane-canonical census is ONE page promoted; it must never be used as
        # a fallback for a band that knows its own page.
        _write_rects(bd / "evidence" / "section-rects.json",
                     [(0, 1440, 500), (1, 1440, 600)])
        return bd

    def test_same_section_number_on_two_pages_is_attributed_correctly(self):
        with tempfile.TemporaryDirectory() as td:
            bd = self._two_page_lane(td)
            doc = {"patterns": [
                _pattern("first", ["pageone-section-01-div"], ["pageone"]),
                _pattern("second", ["pagetwo-section-01-div"], ["pagetwo"]),
            ]}
            summary = mg.enrich_layout_library(doc, bd, fields=mg.FIDELITY_FIELDS)
        self.assertEqual(set(summary), {"first", "second"})
        first, second = doc["patterns"]
        self.assertEqual(_pad(first), {"top": "8.75rem", "bottom": "7.5rem"})
        self.assertEqual(_pad(second), {"top": "11.25rem", "bottom": "10rem"})

    def test_no_cross_page_bleed_between_the_two_patterns(self):
        """Neither pattern may carry the OTHER page's measured values."""
        with tempfile.TemporaryDirectory() as td:
            bd = self._two_page_lane(td)
            doc = {"patterns": [
                _pattern("first", ["pageone-section-01-div"], ["pageone"]),
                _pattern("second", ["pagetwo-section-01-div"], ["pagetwo"]),
            ]}
            mg.enrich_layout_library(doc, bd, fields=mg.FIDELITY_FIELDS)
        first, second = doc["patterns"]
        self.assertNotEqual(_pad(first), _pad(second))
        self.assertNotIn(_pad(second)["top"], _pad(first).values())
        self.assertNotIn(_pad(first)["top"], _pad(second).values())

    def test_measured_aspect_reads_its_own_pages_rect_census(self):
        """The band aspect comes from the band's own page's rect census, not from
        the lane-canonical file (which is another page's census)."""
        with tempfile.TemporaryDirectory() as td:
            bd = self._two_page_lane(td)
            doc = {"patterns": [
                _pattern("second", ["pagetwo-section-01-div"], ["pagetwo"]),
            ]}
            mg.enrich_layout_library(doc, bd, fields=mg.ALL_FIELDS)
        backdrop = next(s for s in doc["patterns"][0]["contentShape"]["slots"]
                        if s["name"] == "backdrop")
        self.assertEqual(backdrop["mediaAspect"], "1440 / 800")  # pagetwo idx 1
        self.assertNotEqual(backdrop["mediaAspect"], "1440 / 600")  # canonical

    def test_band_without_its_own_page_census_fills_no_aspect(self):
        """Degrade quietly: a missing per-page census leaves the aspect alone rather
        than borrowing another page's numbers."""
        with tempfile.TemporaryDirectory() as td:
            bd = Path(td)
            _write_page_band(bd, "pageone", "section-01-div.yaml", _grounding(90, 90))
            _write_rects(bd / "evidence" / "section-rects.json",
                         [(1, 1440, 999)])
            doc = {"patterns": [
                _pattern("only", ["pageone-section-01-div"], ["pageone"]),
            ]}
            mg.enrich_layout_library(doc, bd, fields=mg.ALL_FIELDS)
        backdrop = next(s for s in doc["patterns"][0]["contentShape"]["slots"]
                        if s["name"] == "backdrop")
        self.assertEqual(backdrop["mediaAspect"], "wide")
        self.assertEqual(_pad(doc["patterns"][0]),
                         {"top": "5.625rem", "bottom": "5.625rem"})

    def test_ambiguous_bare_token_fills_nothing(self):
        """A bare ``section-NN`` on a multi-page lane names two bands. Refusing is
        the point: guessing would attribute one page's geometry to the other."""
        with tempfile.TemporaryDirectory() as td:
            bd = self._two_page_lane(td)
            pat = _pattern("ambiguous", ["section-01"])
            doc = {"patterns": [pat]}
            summary = mg.enrich_layout_library(doc, bd, fields=mg.FIDELITY_FIELDS)
            self.assertEqual(mg.unresolved_patterns(doc, bd), ["ambiguous"])
        self.assertEqual(summary, {})
        self.assertNotIn("bandPadding", pat["contentShape"])

    def test_bare_token_is_disambiguated_by_source_pages(self):
        """``sourcePages[]`` is the existing page contract, so a bare token plus a
        declared page resolves to exactly one band."""
        with tempfile.TemporaryDirectory() as td:
            bd = self._two_page_lane(td)
            pat = _pattern("declared", ["section-01"], ["pagetwo"])
            doc = {"patterns": [pat]}
            mg.enrich_layout_library(doc, bd, fields=mg.FIDELITY_FIELDS)
        self.assertEqual(_pad(pat), {"top": "11.25rem", "bottom": "10rem"})

    def test_recurring_pattern_measures_from_its_first_source(self):
        """One pattern claimed by bands on several pages is measured from the first
        source its provenance names — deterministic, never a blend."""
        with tempfile.TemporaryDirectory() as td:
            bd = self._two_page_lane(td)
            pat = _pattern("recurring",
                           ["pagetwo-section-01-div", "pageone-section-01-div"],
                           ["pageone", "pagetwo"])
            doc = {"patterns": [pat]}
            mg.enrich_layout_library(doc, bd, fields=mg.FIDELITY_FIELDS)
        self.assertEqual(_pad(pat), {"top": "11.25rem", "bottom": "10rem"})

    def test_designed_patterns_are_never_measured(self):
        with tempfile.TemporaryDirectory() as td:
            bd = self._two_page_lane(td)
            pat = _pattern("designed", ["pageone-section-01-div"], ["pageone"])
            pat["origin"] = "designed"
            doc = {"patterns": [pat]}
            summary = mg.enrich_layout_library(doc, bd, fields=mg.FIDELITY_FIELDS)
        self.assertEqual(summary, {})
        self.assertNotIn("bandPadding", pat["contentShape"])


# ── committed lanes: the fix lands, the older lanes do not regress ────────────

class CommittedLaneTests(unittest.TestCase):
    def test_multi_page_lane_now_reaches_every_extracted_pattern(self):
        """The reported bug: a page-prefixed lane loaded ZERO grounding and enriched
        nothing. Every extracted pattern must now resolve to a band on a page it
        declares."""
        if not (MULTI_PAGE_LANE / "layout-library.yaml").is_file():
            self.skipTest("multi-page lane not present")
        bands = mg._load_grounding(MULTI_PAGE_LANE)
        self.assertGreater(len(bands), 0, "page-prefixed grounding must load")
        doc = yaml.safe_load((MULTI_PAGE_LANE / "layout-library.yaml").read_text())
        extracted = [p for p in doc["patterns"]
                     if str(p.get("origin") or "").lower() in ("extracted", "",
                                                               "creation")]
        self.assertEqual(mg.unresolved_patterns(doc, MULTI_PAGE_LANE), [])
        for pat in extracted:
            band = mg.resolve_pattern_band(pat, bands)
            pages = pat.get("sourcePages") or []
            if pages and band.page:
                self.assertIn(band.page, pages,
                              f"{pat['id']} measured from a page it does not declare")
        summary = mg.enrich_layout_library(_stripped(doc), MULTI_PAGE_LANE,
                                           fields=mg.FIDELITY_FIELDS)
        self.assertEqual(len(summary), len(extracted),
                         "every extracted pattern should gain measured facts")

    def test_multi_page_band_padding_traces_to_its_own_band(self):
        """Every filled ``bandPadding`` must equal the measured padding of the band
        the pattern's own provenance names."""
        if not (MULTI_PAGE_LANE / "layout-library.yaml").is_file():
            self.skipTest("multi-page lane not present")
        doc = yaml.safe_load((MULTI_PAGE_LANE / "layout-library.yaml").read_text())
        bands = mg._load_grounding(MULTI_PAGE_LANE)
        enriched = _stripped(doc)
        mg.enrich_layout_library(enriched, MULTI_PAGE_LANE,
                                 fields=mg.FIDELITY_FIELDS)
        checked = 0
        for pat in enriched["patterns"]:
            band = mg.resolve_pattern_band(pat, bands)
            if band is None:
                continue
            src = ((band.doc.get("layout") or {}).get("approxPaddingPx")) or {}
            expected = {k: mg._rem(float(src[k])) for k in ("top", "bottom")
                        if src.get(k) is not None}
            if not expected:
                continue
            self.assertEqual(_pad(pat), expected,
                             f"{pat['id']} padding did not come from {band.slug}")
            checked += 1
        self.assertGreater(checked, 0, "no measured padding was verified")

    def test_single_page_lane_is_unchanged(self):
        """The older bare-named lanes keep resolving to the same bands and stay
        fill-absent-only complete (the shipped library gains nothing)."""
        if not (SINGLE_PAGE_LANE / "layout-library.yaml").is_file():
            self.skipTest("single-page lane not present")
        doc = yaml.safe_load((SINGLE_PAGE_LANE / "layout-library.yaml").read_text())
        bands = mg._load_grounding(SINGLE_PAGE_LANE)
        self.assertTrue(all(b.page == "" for b in bands.values()))
        self.assertEqual(mg.unresolved_patterns(doc, SINGLE_PAGE_LANE), [])
        for pat in doc["patterns"]:
            band = mg.resolve_pattern_band(pat, bands)
            self.assertIsNotNone(band, f"{pat['id']} lost its band")
            # the slug still carries the ordinal the bare provenance token names
            self.assertTrue(band.slug.startswith(str(pat["provenance"][0])))
        summary = mg.enrich_layout_library(copy.deepcopy(doc), SINGLE_PAGE_LANE,
                                           fields=mg.FIDELITY_FIELDS)
        self.assertEqual(summary, {},
                         f"shipped single-page library should be complete: {summary}")


if __name__ == "__main__":
    unittest.main()
