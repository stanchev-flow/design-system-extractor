#!/usr/bin/env python3
"""Unit tests for the spacing-conformance auditor's non-browser parts
(spec/spacing-conformance.md): fact resolution from synthetic brand docs,
tolerance/severity classification, nearest-step matching, offender ranking and
report shaping. NO Playwright here — the browser payload is exercised by the
baseline runs, not the unit suite.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_spacing_audit
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import spacing_audit as sa  # noqa: E402


# ─────────────────────────────── synthetic brand dir ──────────────────────────────

BRAND_YAML = """\
meta:
  canonicalTier: 1440
tokens:
  spacing:
    eyebrow-to-heading: {value: 0.75rem, role: "label-headline gap"}
    heading-to-body: {value: 1rem}
    body-to-cta: {value: 2rem}
    block-to-block: {value: 4rem}
    column-to-column: {value: 3rem}
    grid-gap: {value: 2rem}
    panel-padding:
      value: 2rem
      role: "card/panel inset (testimonial cards ~40px, hero panel up to 80px @xl)"
    section-padding-light: {value: 3rem}
    section-y-lg: {value: 5rem}
    container-span: {value: "min(81.2cqw, 97.5rem)"}
    container-max: {value: 1216}
    not-a-length: {value: "1 / 1"}
navbar:
  measured: {contentMaxWidth: 1216, linkGap: 12}
footer:
  measured:
    contentMaxWidth: 1216
    linkGap: 12
    grid: {columnGap: 26, rowGap: 26}
"""

LIB_YAML = """\
patterns:
  - id: pat-split
    contentShape:
      bandPadding: {top: 4rem, bottom: 4rem}
      deviceGeometry:
        note: "JS-off @1440: split 1168px = cols 571px | 496px copy (gap 101px)"
        media: {aspect: "1 / 1"}
  - id: pat-accordion
    contentShape:
      bandPadding: {top: 4rem, bottom: 4rem}
      deviceGeometry:
        contentSpan: 1168px
        columnGap: 6.3125rem
        rowGap: 4rem
        note: "structured keys above win; note gap 999px must be ignored"
        list: {itemGap: 1rem, triggerMinHeight: 3.5rem}
      stackMeasure: {value: 46rem}
  - id: pat-logos
    contentShape:
      slots:
        - name: logos
          mediaScale: {gap: 4rem}
"""

CSS_RULES = {
    "rules": [
        {"sel": ":root", "decls": "--zora-spacing-x1: 4px; --zora-spacing-x2: 0.5rem;"
                                  " --zora-spacing-x16: 10rem; --color-red: red"},
        {"sel": ":root", "decls": "--zora-spacing-huge: 20rem"},  # > rhythm ceiling
        {"sel": ".x", "decls": 12345},                            # non-string decls
    ]
}


def make_brand_dir(root: Path) -> Path:
    brand = root / "brand"
    (brand / "evidence").mkdir(parents=True)
    (brand / "brand.yaml").write_text(BRAND_YAML)
    (brand / "layout-library.yaml").write_text(LIB_YAML)
    (brand / "evidence" / "css-rules.json").write_text(json.dumps(CSS_RULES))
    return brand


class BrandDirCase(unittest.TestCase):
    """Shared synthetic brand dir + loaded FactBook."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.brand_dir = make_brand_dir(Path(cls._tmp.name))
        cls.book = sa.load_brand_facts(cls.brand_dir, viewport_w=1440)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()


# ─────────────────────────────────── parse_length ─────────────────────────────────

class ParseLengthTest(unittest.TestCase):
    def test_px_rem_em_and_bare_numbers(self):
        self.assertEqual(sa.parse_length("48px"), 48.0)
        self.assertEqual(sa.parse_length("3rem"), 48.0)
        self.assertEqual(sa.parse_length("1.5em"), 24.0)
        self.assertEqual(sa.parse_length(1216), 1216.0)
        self.assertEqual(sa.parse_length("26"), 26.0)
        self.assertEqual(sa.parse_length("-4px"), -4.0)

    def test_rem_honours_root_font_size(self):
        self.assertEqual(sa.parse_length("2rem", rem_px=10.0), 20.0)

    def test_min_cqw_rem_resolves_at_viewport(self):
        # min(81.2cqw, 97.5rem) @1440 → min(1169.28, 1560)
        self.assertEqual(sa.parse_length("min(81.2cqw, 97.5rem)", viewport_w=1440),
                         1169.28)
        # …and the rem arm wins on a huge viewport
        self.assertEqual(sa.parse_length("min(81.2cqw, 97.5rem)", viewport_w=4000),
                         1560.0)

    def test_min_without_viewport_is_unresolvable(self):
        self.assertIsNone(sa.parse_length("min(81.2cqw, 97.5rem)"))

    def test_non_lengths_return_none(self):
        self.assertIsNone(sa.parse_length("1 / 1"))          # ratio
        self.assertIsNone(sa.parse_length("1rem 2rem"))      # shorthand
        self.assertIsNone(sa.parse_length(None))
        self.assertIsNone(sa.parse_length({"value": "1rem"}))
        self.assertIsNone(sa.parse_length("auto"))


# ─────────────────────────────────── mine_scale ────────────────────────────────────

class MineScaleTest(BrandDirCase):
    def test_scale_mined_from_css_corpus(self):
        px = [f.px for f in self.book.scale]
        self.assertEqual(px, [4.0, 8.0, 160.0])

    def test_scale_respects_rhythm_ceiling(self):
        self.assertNotIn(320.0, [f.px for f in self.book.scale])

    def test_missing_corpus_is_empty_not_fatal(self):
        self.assertEqual(sa.mine_scale(Path("/nonexistent/css-rules.json")), [])


# ─────────────────────────────────── fact loading ─────────────────────────────────

class LoadBrandFactsTest(BrandDirCase):
    def test_spacing_tokens_resolved_to_px(self):
        self.assertEqual(self.book.steps["eyebrow-to-heading"].px, 12.0)
        self.assertEqual(self.book.steps["block-to-block"].px, 64.0)
        self.assertEqual(self.book.steps["container-max"].px, 1216.0)
        self.assertEqual(self.book.steps["container-span"].px, 1169.28)

    def test_non_length_token_dropped(self):
        self.assertNotIn("not-a-length", self.book.steps)

    def test_chrome_measurements(self):
        self.assertEqual(self.book.chrome["navbar.contentMaxWidth"].px, 1216.0)
        self.assertEqual(self.book.chrome["footer.linkGap"].px, 12.0)
        self.assertEqual(self.book.chrome["footer.grid.columnGap"].px, 26.0)

    def test_pattern_structured_keys(self):
        acc = self.book.pattern_facts["pat-accordion"]
        self.assertEqual(acc["bandPadding.top"].px, 64.0)
        self.assertEqual(acc["deviceGeometry.columnGap"].px, 101.0)
        self.assertEqual(acc["deviceGeometry.contentSpan"].px, 1168.0)
        self.assertEqual(acc["list.itemGap"].px, 16.0)
        self.assertEqual(acc["list.triggerMinHeight"].px, 56.0)
        self.assertEqual(acc["stackMeasure"].px, 736.0)

    def test_prose_note_fallback_only_when_structured_key_absent(self):
        split = self.book.pattern_facts["pat-split"]
        self.assertEqual(split["deviceGeometry.columnGap"].px, 101.0)
        self.assertTrue(split["deviceGeometry.columnGap"].source
                        .startswith("pattern-note:"))
        # structured key wins: the accordion's decoy "999px" note is ignored
        acc = self.book.pattern_facts["pat-accordion"]
        self.assertEqual(acc["deviceGeometry.columnGap"].px, 101.0)
        self.assertEqual(acc["deviceGeometry.columnGap"].source,
                         "pattern:pat-accordion")

    def test_strip_gap_slots(self):
        logos = self.book.pattern_facts["pat-logos"]
        self.assertEqual(logos["strip.gap.logos"].px, 64.0)

    def test_role_prose_becomes_optin_facts(self):
        prose = {f.px for f in self.book.prose["panel-padding"]}
        self.assertEqual(prose, {40.0, 80.0})
        for f in self.book.prose["panel-padding"]:
            self.assertEqual(f.source, "token-prose")

    def test_sanctioned_families_split_at_rhythm_ceiling(self):
        gaps = {f.px for f in self.book.gap_sanctioned()}
        widths = {f.px for f in self.book.width_sanctioned()}
        self.assertIn(12.0, gaps)
        self.assertIn(101.0, gaps)
        self.assertNotIn(1216.0, gaps)
        self.assertIn(1216.0, widths)
        self.assertIn(1168.0, widths)
        self.assertNotIn(12.0, widths)

    def test_seam_sums_are_pairwise_band_padding_sums(self):
        sums = {f.px for f in self.book.seam_sums()}
        # bands: 48 (light), 80 (y-lg), 64 (pattern) → pairwise sums
        self.assertEqual(sums, {96.0, 112.0, 128.0, 144.0, 160.0})


# ─────────────────────────────────── resolve_steps ────────────────────────────────

class ResolveStepsTest(BrandDirCase):
    def test_plain_ladder_rung(self):
        steps = sa.resolve_steps("header.eyebrow-to-heading", None, self.book)
        self.assertEqual([(f.name, f.px) for f in steps],
                         [("eyebrow-to-heading", 12.0)])

    def test_pattern_band_padding_takes_priority(self):
        steps = sa.resolve_steps("section.pad-top", "pat-split", self.book)
        self.assertEqual(steps[0].px, 64.0)              # @bandPadding.top first
        self.assertIn(48.0, [f.px for f in steps])       # then the tokens

    def test_missing_pattern_falls_back_to_tokens(self):
        steps = sa.resolve_steps("section.pad-top", "no-such-pattern", self.book)
        self.assertEqual(steps[0].px, 48.0)

    def test_grid_gap_prefers_pattern_geometry(self):
        steps = sa.resolve_steps("grid.column-gap", "pat-accordion", self.book)
        self.assertEqual(steps[0].px, 101.0)
        self.assertIn(32.0, [f.px for f in steps])

    def test_container_widths_deduped_by_px(self):
        steps = sa.resolve_steps("container.width", "pat-accordion", self.book)
        px = [f.px for f in steps]
        self.assertEqual(px.count(1216.0), 1)            # token + chrome dedup
        self.assertIn(1169.28, px)
        self.assertIn(1168.0, px)                        # pattern contentSpan

    def test_prose_suffix_appends_optin_facts(self):
        steps = sa.resolve_steps("card.inset", None, self.book)
        self.assertEqual({f.px for f in steps}, {32.0, 40.0, 80.0})

    def test_strip_and_chrome_resolvers(self):
        self.assertEqual([f.px for f in
                          sa.resolve_steps("strip.gap", "pat-logos", self.book)],
                         [64.0])
        self.assertEqual([f.px for f in
                          sa.resolve_steps("footer.link-gap", None, self.book)],
                         [12.0])
        self.assertEqual([f.px for f in
                          sa.resolve_steps("footer.column-gap", None, self.book)],
                         [26.0])

    def test_seam_sums_resolver(self):
        steps = sa.resolve_steps("section.seam", None, self.book)
        self.assertEqual({f.px for f in steps}, {96.0, 112.0, 128.0, 144.0, 160.0})

    def test_unmapped_relationship_resolves_empty(self):
        self.assertEqual(sa.resolve_steps("form.field-gap", None, self.book), [])

    def test_every_registry_step_token_is_resolvable_syntax(self):
        """Registry hygiene: every non-@ step must be a token name or +prose form
        (typos here would silently unmap relationships)."""
        for rel_id, rel in sa.RELATIONSHIPS.items():
            for step in rel.steps:
                self.assertIsInstance(step, str)
                self.assertTrue(step[0].isalpha() or step.startswith("@"),
                                f"{rel_id}: malformed step {step!r}")


# ───────────────────────────── tolerance + classification ─────────────────────────

def _facts(*px):
    return [sa.Fact(f"f{v:g}", float(v), "token") for v in px]


class ToleranceTest(unittest.TestCase):
    def test_rhythm_floor_and_relative_arm(self):
        self.assertEqual(sa.tolerance(12.0, "gap"), 2.0)      # floor
        self.assertEqual(sa.tolerance(64.0, "gap"), 6.4)      # 10%
        self.assertEqual(sa.tolerance(0.0, "inset"), 2.0)

    def test_width_family_tightens_relative_arm(self):
        self.assertEqual(sa.tolerance(1216.0, "width"), 12.16)  # 1%
        self.assertEqual(sa.tolerance(100.0, "width"), 2.0)     # floor


class ClassifyTest(unittest.TestCase):
    def test_conform_within_tolerance(self):
        r = sa.classify(12.9, _facts(12), _facts(4, 8, 12, 16), "gap")
        self.assertEqual(r["severity"], "conform")
        self.assertEqual(r["declared"]["px"], 12.0)
        self.assertAlmostEqual(r["delta"], 0.9)

    def test_drift_within_double_tolerance(self):
        r = sa.classify(15.5, _facts(12), _facts(4, 8, 12), "gap")
        self.assertEqual(r["severity"], "drift")

    def test_wrong_step_hits_another_sanctioned_rung(self):
        r = sa.classify(24.0, _facts(12), _facts(4, 8, 12, 24, 64), "gap")
        self.assertEqual(r["severity"], "wrong-step")
        self.assertEqual(r["nearest"]["px"], 24.0)

    def test_off_ladder_matches_nothing(self):
        r = sa.classify(22.0, _facts(12), _facts(4, 8, 12, 64), "gap")
        self.assertEqual(r["severity"], "off-ladder")
        self.assertEqual(r["nearest"]["px"], 12.0)  # nearest still reported

    def test_multiple_declared_steps_pick_best(self):
        r = sa.classify(63.0, _facts(48, 64), _facts(48, 64), "gap")
        self.assertEqual(r["severity"], "conform")
        self.assertEqual(r["declared"]["px"], 64.0)

    def test_unmapped_when_nothing_declared(self):
        r = sa.classify(37.0, [], _facts(4, 8, 36), "gap")
        self.assertEqual(r["severity"], "unmapped")
        self.assertEqual(r["nearest"]["px"], 36.0)
        self.assertIsNone(r["declared"])

    def test_center_family_absolute_rule(self):
        self.assertEqual(sa.classify(1.2, [], [], "center")["severity"], "conform")
        self.assertEqual(sa.classify(3.0, [], [], "center")["severity"], "drift")
        self.assertEqual(sa.classify(9.0, [], [], "center")["severity"],
                         "off-ladder")

    def test_width_family_uses_tight_arm(self):
        sanctioned = _facts(1168, 1216)
        self.assertEqual(
            sa.classify(1210.0, _facts(1216), sanctioned, "width")["severity"],
            "conform")
        # 1168 is another sanctioned width — landing on it is wrong-step
        self.assertEqual(
            sa.classify(1168.0, _facts(1216), sanctioned, "width")["severity"],
            "wrong-step")


class ClassifyMeasurementTest(BrandDirCase):
    def _meas(self, rel, value, pattern=None):
        return {"rel": rel, "value": value, "sec": "sec-1", "layout": "test",
                "pattern": pattern, "a": "a", "b": "b", "rect": None,
                "note": "", "kind": "gap"}

    def test_gates(self):
        conform = sa.classify_measurement(
            self._meas("header.eyebrow-to-heading", 12.0), self.book)
        self.assertEqual((conform["severity"], conform["gate"]),
                         ("conform", "pass"))
        hard = sa.classify_measurement(
            self._meas("header.eyebrow-to-heading", 24.0), self.book)
        self.assertEqual((hard["severity"], hard["gate"]),
                         ("wrong-step", "hard"))
        unmapped = sa.classify_measurement(
            self._meas("form.field-gap", 24.0), self.book)
        self.assertEqual((unmapped["severity"], unmapped["gate"]),
                         ("unmapped", "advisory"))

    def test_advisory_only_relationship_never_gates_hard(self):
        orig = sa.RELATIONSHIPS["card.mark-to-quote"]
        sa.RELATIONSHIPS["card.mark-to-quote"] = sa.Rel(
            "gap", ("eyebrow-to-heading",), advisory_only=True, reason="test range")
        try:
            out = sa.classify_measurement(
                self._meas("card.mark-to-quote", 24.0), self.book)
            self.assertEqual(out["severity"], "wrong-step")
            self.assertEqual(out["gate"], "advisory")
            self.assertIn("test range", out["note"])
        finally:
            sa.RELATIONSHIPS["card.mark-to-quote"] = orig


# ─────────────────────────────── ranking + reporting ──────────────────────────────

def _classified(rel, measured, declared_px, severity, gate, sec="sec-1",
                layout="cards"):
    return {
        "rel": rel, "value": measured, "measured": measured,
        "declared": ({"name": f"tok{declared_px:g}", "px": declared_px,
                      "source": "token"} if declared_px is not None else None),
        "nearest": None, "delta": (round(measured - declared_px, 2)
                                   if declared_px is not None else None),
        "severity": severity, "gate": gate, "sec": sec, "layout": layout,
        "pattern": None, "a": "a", "b": "b", "note": "",
        "rect": {"x": 0, "y": 0, "w": 10, "h": 10}, "kind": "gap",
    }


class RankOffendersTest(unittest.TestCase):
    def test_groups_score_and_order(self):
        rows = (
            [_classified("grid.row-gap", 64.0, 32.0, "wrong-step", "hard",
                         sec=f"sec-{i}") for i in range(3)]
            + [_classified("header.eyebrow-to-heading", 22.0, 12.0,
                           "off-ladder", "hard")]
            + [_classified("card.inset", 33.0, 32.0, "conform", "pass")]
            + [_classified("strip.gap", 60.0, None, "unmapped", "advisory")]
        )
        ranked = sa.rank_offenders(rows)
        self.assertEqual(len(ranked), 2)                      # hard fails only
        self.assertEqual(ranked[0]["rel"], "grid.row-gap")    # 3×32 > 1×10
        self.assertEqual(ranked[0]["count"], 3)
        self.assertEqual(ranked[0]["score"], 96.0)
        self.assertEqual(ranked[0]["expected"]["px"], 32.0)
        self.assertEqual(ranked[1]["rel"], "header.eyebrow-to-heading")
        self.assertEqual(ranked[1]["score"], 10.0)

    def test_top_caps_output(self):
        rows = [_classified(f"rel-{i}", 40.0 + i, 20.0, "off-ladder", "hard")
                for i in range(15)]
        self.assertEqual(len(sa.rank_offenders(rows, top=5)), 5)

    def test_no_hard_fails_no_offenders(self):
        rows = [_classified("card.inset", 33.0, 32.0, "conform", "pass")]
        self.assertEqual(sa.rank_offenders(rows), [])


class SeverityCountsTest(unittest.TestCase):
    def test_counts_and_hard_fail_total(self):
        rows = [
            _classified("a", 1, 1, "conform", "pass"),
            _classified("b", 2, 1, "drift", "advisory"),
            _classified("c", 3, 1, "wrong-step", "hard"),
            _classified("d", 4, 1, "off-ladder", "hard"),
            _classified("e", 5, None, "unmapped", "advisory"),
        ]
        c = sa.severity_counts(rows)
        self.assertEqual((c["conform"], c["drift"], c["wrong-step"],
                          c["off-ladder"], c["unmapped"]), (1, 1, 1, 1, 1))
        self.assertEqual(c["hardFails"], 2)
        self.assertEqual(c["total"], 5)


class ReportShapingTest(BrandDirCase):
    def _report(self):
        rows = [
            _classified("grid.row-gap", 64.0, 32.0, "wrong-step", "hard"),
            _classified("card.inset", 33.0, 32.0, "conform", "pass"),
            _classified("strip.gap", 60.0, None, "unmapped", "advisory"),
        ]
        lane = {
            "lane": "compose/test", "html": "/tmp/x/index.html",
            "mtime": "2026-07-10 12:00:00", "counts": sa.severity_counts(rows),
            "measurements": rows, "skips": [
                {"sec": "sec-9", "layout": "editorial", "what": ".cs-modules",
                 "why": "staggered editorial grid"}],
            "offenders": sa.rank_offenders(rows),
        }
        errlane = {"lane": "compose/broken", "html": "/tmp/y/index.html",
                   "error": "TimeoutError: boom"}
        return sa.shape_report([lane, errlane], self.book, {
            "generatedAt": "2026-07-10T12:00:00Z", "brandDir": "x",
            "viewport": "1440x900"})

    def test_json_shape(self):
        rep = self._report()
        self.assertIn("toleranceRule", rep)
        self.assertEqual(len(rep["lanes"]), 2)
        self.assertEqual(rep["factbook"]["steps"]["eyebrow-to-heading"], 12.0)
        self.assertIn("pat-accordion", rep["factbook"]["patternFacts"])
        self.assertTrue(json.dumps(rep))  # serializable end-to-end

    def test_markdown_renders_all_blocks(self):
        rep = self._report()
        rep["screenshots"] = [{"file": "offender-01-grid-row-gap.png",
                               "lane": "compose/test", "label": "grid.row-gap"}]
        md = sa.render_md(rep)
        self.assertIn("## Lane summary", md)
        self.assertIn("compose/test", md)
        self.assertIn("ERROR: TimeoutError: boom", md)
        self.assertIn("Top offenders", md)
        self.assertIn("`grid.row-gap`", md)
        self.assertIn("Unmapped relationships", md)
        self.assertIn("Skipped", md)
        self.assertIn("staggered editorial grid", md)
        self.assertIn("Annotated evidence", md)
        self.assertIn("offender-01-grid-row-gap.png", md)

    def test_markdown_marks_hard_fails_bold(self):
        md = sa.render_md(self._report())
        self.assertIn("**wrong-step**", md)
        self.assertNotIn("**conform**", md)


# ─────────────────────────────────── path helpers ─────────────────────────────────

class PathHelpersTest(unittest.TestCase):
    def test_resolve_lane_paths_dir_gets_index_html(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "lane"
            d.mkdir()
            explicit = Path(td) / "page.html"
            out = sa.resolve_lane_paths([str(d), str(explicit)])
            self.assertEqual(out[0], d / "index.html")
            self.assertEqual(out[1], explicit)

    def test_lane_name_relative_to_brand_dir(self):
        with tempfile.TemporaryDirectory() as td:
            brand = Path(td) / "brand"
            html = brand / "compose" / "replica" / "index.html"
            html.parent.mkdir(parents=True)
            html.write_text("<html></html>")
            self.assertEqual(sa._lane_name(html, brand), "compose/replica")
            foreign = Path(td) / "elsewhere" / "index.html"
            foreign.parent.mkdir(parents=True)
            foreign.write_text("<html></html>")
            self.assertEqual(sa._lane_name(foreign, brand), "elsewhere")


if __name__ == "__main__":
    unittest.main()
