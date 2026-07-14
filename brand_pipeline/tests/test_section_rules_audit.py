"""Enforcement tests for brand_pipeline/section_rules_audit.py (stage B of the
quality steals; law: spec/section-rules.md, data: contracts/section-rules.yaml).

Fixture doctrine (the YAML's own bar): every ``enforcement: new`` rule fails a
synthetic-bad fixture here; the real-lane green side is proven by the stage-B
battery run recorded in evals/matrix/changes.md (and spot-pinned below on the
event lane, static layer only, so the suite stays browserless).

Geometry rules are tested against synthetic measurement payloads (the
signature-gate test pattern) — no Playwright in unit tests.

Run: ./venv/bin/python -m pytest brand_pipeline/tests/test_section_rules_audit.py -q
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import section_rules_audit as sra  # noqa: E402

REPO = HERE.parent
EVENT_LANE = REPO / "runs/remote/brand/compose/event-genlaunch"

RULES = {r["id"]: r for r in sra.load_rules()["rules"]}


def make_lane(tmp: Path, body_html: str, sections=None, schema="composition.v1",
              brief=True, brand=None, geometry=None) -> sra.LaneCtx:
    """Synthetic lane: index.html + composition.json in a tmp dir."""
    comp = {"schemaVersion": schema, "sections": sections or []}
    if brief:
        comp["brief"] = {"id": "fixture"}
    (tmp / "composition.json").write_text(json.dumps(comp))
    html = tmp / "index.html"
    html.write_text(f"<!doctype html><html><body>{body_html}</body></html>")
    return sra.LaneCtx(tmp, html, brand or {}, geometry)


def run_rule(rule_id: str, lane: sra.LaneCtx) -> list[dict]:
    return sra.CHECKERS[rule_id](RULES[rule_id], lane)


def verdicts(rows: list[dict]) -> set[str]:
    return {r["verdict"] for r in rows}


class Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def lane(self, body_html: str, **kw) -> sra.LaneCtx:
        return make_lane(self.tmp, body_html, **kw)


SEC = '<div id="sec-{i}" class="cs-surface" data-layout="{layout}">{inner}</div>'


def sec(i: int, inner: str, layout: str | None = None) -> str:
    return SEC.format(i=i, layout=layout or f"sec-{i}", inner=inner)


# ── coverage + scoping ───────────────────────────────────────────────────────────

class CheckerCoverage(unittest.TestCase):
    def test_every_new_rule_has_a_checker(self):
        new_ids = {r["id"] for r in RULES.values() if r["enforcement"] == "new"}
        missing = new_ids - set(sra.CHECKERS)
        self.assertFalse(missing, f"new rules without checker code: {missing}")

    def test_no_checker_shadows_delegated_law(self):
        delegated = {r["id"] for r in RULES.values()
                     if r["enforcement"] == "delegated"}
        shadowed = delegated & set(sra.CHECKERS)
        self.assertFalse(shadowed, f"delegated rules re-implemented: {shadowed}")


class LaneScope(Fixture):
    def test_composition_v1_is_generative(self):
        lane = self.lane("", sections=[], schema="composition.v1")
        self.assertEqual(lane.scope, "generative")

    def test_briefed_legacy_composition_is_generative(self):
        lane = self.lane("", schema="replica-composition.v1", brief=True)
        self.assertEqual(lane.scope, "generative")

    def test_briefless_replica_is_evidence(self):
        lane = self.lane("", schema="replica-composition.v1", brief=False)
        self.assertEqual(lane.scope, "replica")

    def test_compositionless_lane_is_specimen(self):
        html = self.tmp / "index.html"
        html.write_text("<html><body></body></html>")
        self.assertEqual(sra.lane_scope(self.tmp), "specimen")

    def test_replica_lane_audit_is_one_skip_row(self):
        lane_dir = self.tmp
        make_lane(lane_dir, sec(0, "<h2>Anything</h2><h2>Anything</h2>"),
                  schema="replica-composition.v1", brief=False)
        entry = sra.audit_lane_html(lane_dir, lane_dir / "index.html",
                                    sra.load_rules(), {}, None)
        self.assertEqual(entry["scope"], "replica")
        self.assertEqual(verdicts(entry["findings"]), {"skip"})


class FamilyDetection(Fixture):
    def test_device_classes_and_usecases_bind(self):
        html = (
            sec(0, '<h1 class="c-heading c-heading--display">Claim</h1>')
            + sec(1, '<div class="cs-stat-band"><div class="c-stat"></div>'
                     '<div class="c-stat"></div></div>')
            + sec(2, '<div class="cs-logo-strip"></div>')
            + sec(3, '<form><input type="email"></form>')
            + sec(4, '<div class="cs-tiers"><article class="cs-tier"></article>'
                     '</div>')
            + sec(5, '<blockquote>Quoted</blockquote>')
            + sec(6, '<div class="cs-modules"><article class="cs-module">'
                     '</article><article class="cs-module"></article></div>')
            + sec(7, '<div class="cs-faq"><details name="g"><summary>Q?'
                     '</summary></details></div>')
            + sec(8, '<section class="cs-conversion-sec"></section>')
            + sec(9, '<div class="cs-edgecut"></div>'))
        lane = self.lane(html)
        fams = {s.sid: s.families for s in lane.sections}
        self.assertIn("hero", fams["sec-0"])
        self.assertIn("stat-band", fams["sec-1"])
        self.assertIn("logo-strip", fams["sec-2"])
        self.assertIn("capture-form", fams["sec-3"])
        self.assertIn("pricing-tiers", fams["sec-4"])
        self.assertIn("quote", fams["sec-5"])
        self.assertIn("feature-grid", fams["sec-6"])
        self.assertIn("faq", fams["sec-7"])
        self.assertIn("cta-band", fams["sec-8"])
        self.assertIn("carousel", fams["sec-9"])

    def test_declared_non_faq_use_suppresses_device_detection(self):
        """An agenda authored as accordion rows is a disclosure device
        (IC-ACC/AS-40 law), not an FAQ — the stage-B detection calibration."""
        inner = ('<div class="cs-faq"><details name="agenda"><summary>'
                 '16:00 — Keynote</summary><p>Session</p></details></div>')
        sections = [{"id": "sec-0", "useCase": "agenda", "slots": []}]
        lane = self.lane(sec(0, inner), sections=sections)
        self.assertNotIn("faq", lane.sections[0].families)

    def test_undeclared_details_group_still_binds_faq(self):
        inner = ('<details name="g"><summary>Statement trigger</summary>'
                 '<p>Body</p></details>')
        lane = self.lane(sec(0, inner))
        self.assertIn("faq", lane.sections[0].families)

    def test_closing_bookend_is_chrome_not_content(self):
        html = (sec(0, "<h2>One</h2>")
                + '<div id="sec-1" class="cs-surface" '
                  'data-layout="closing-bookend"><section class="cs-section '
                  'cs-footer-sec"><p class="c-foot-legal">©</p></section></div>')
        lane = self.lane(html)
        self.assertEqual([s.sid for s in lane.sections], ["sec-0"])
        self.assertIsNotNone(lane.chrome["footer"])


# ── section-header rules ─────────────────────────────────────────────────────────

class HdrRules(Fixture):
    def test_hdr01_three_line_heading_fails(self):
        geometry = {"sections": {"sec-0": {"headings": [
            {"tag": "h2", "cls": "c-heading", "text": "Wrapped long heading",
             "lines": 3, "fontPx": 32, "display": False}]}}, "page": {}}
        lane = self.lane(sec(0, "<h2>Wrapped long heading</h2>"),
                         geometry=geometry)
        rows = run_rule("SR-HDR-01", lane)
        self.assertIn("fail", verdicts(rows))

    def test_hdr01_half_measure_column_licenses_three_lines(self):
        """Measure-aware wrap budgets (contracts changelog 18:05Z): a split
        half-measure heading at 3 lines is licensed geometry; the same 3 lines
        on a full measure is copy past the measure."""
        def geo(width):
            return {"sections": {"sec-0": {"headings": [
                {"tag": "h2", "cls": "", "text": "Split heading", "lines": 3,
                 "w": width, "fontPx": 36, "display": False}]}}, "page": {}}
        half = self.lane(sec(0, "<h2>Split heading</h2>"), geometry=geo(487))
        self.assertEqual(verdicts(run_rule("SR-HDR-01", half)), {"pass"})
        full = make_lane(Path(tempfile.mkdtemp()),
                         sec(0, "<h2>Split heading</h2>"), geometry=geo(1100))
        self.assertIn("fail", verdicts(run_rule("SR-HDR-01", full)))

    def test_hdr01_two_lines_pass_and_static_only_skips(self):
        geometry = {"sections": {"sec-0": {"headings": [
            {"tag": "h2", "cls": "", "text": "Tight", "lines": 2,
             "fontPx": 32, "display": False}]}}, "page": {}}
        lane = self.lane(sec(0, "<h2>Tight</h2>"), geometry=geometry)
        self.assertEqual(verdicts(run_rule("SR-HDR-01", lane)), {"pass"})
        lane2 = self.lane(sec(0, "<h2>Tight</h2>"), geometry=None)
        self.assertEqual(verdicts(run_rule("SR-HDR-01", lane2)), {"skip"})

    def test_hdr02_duplicate_and_ellipsis_fail(self):
        html = (sec(0, "<h2>Grow faster…</h2>")
                + sec(1, "<h2>Grow Faster</h2>")
                + sec(2, "<h2>grow faster</h2>"))
        rows = run_rule("SR-HDR-02", self.lane(html))
        self.assertIn("fail", verdicts(rows))
        detail = rows[0]["detail"]
        self.assertIn("ellipsis", detail)
        self.assertIn("duplicates", detail)

    def test_hdr02_clean_headings_pass(self):
        html = sec(0, "<h2>One message</h2>") + sec(1, "<h2>Another beat</h2>")
        self.assertEqual(verdicts(run_rule("SR-HDR-02", self.lane(html))),
                         {"pass"})


# ── hero rules ───────────────────────────────────────────────────────────────────

HERO_SEC = sec(0, '<p class="c-eyebrow">{eyebrow}</p>'
                  '<h1 class="c-heading c-heading--display">Claim</h1>'
                  '<p class="c-paragraph">{sub}</p>')


class HeroRules(Fixture):
    def _hero_lane(self, eyebrow="Platform", sub="Short lede.", geometry=None):
        return self.lane(HERO_SEC.format(eyebrow=eyebrow, sub=sub),
                         sections=[{"id": "sec-0", "useCase": "hero",
                                    "slots": []}], geometry=geometry)

    def test_hero01_four_line_display_fails(self):
        geometry = {"sections": {"sec-0": {"headings": [
            {"tag": "h1", "cls": "c-heading--display", "text": "Claim",
             "lines": 4, "fontPx": 56, "display": True}]}}, "page": {}}
        rows = run_rule("SR-HERO-01", self._hero_lane(geometry=geometry))
        self.assertIn("fail", verdicts(rows))

    def test_hero01_half_measure_licenses_four_lines_never_five(self):
        def geo(lines, width):
            return {"sections": {"sec-0": {"headings": [
                {"tag": "h1", "cls": "c-heading--display", "text": "Claim",
                 "lines": lines, "w": width, "fontPx": 80, "display": True}]}},
                "page": {}}
        four = self._hero_lane(geometry=geo(4, 500))
        self.assertEqual(verdicts(run_rule("SR-HERO-01", four)), {"pass"})
        five = self._hero_lane(geometry=geo(5, 500))
        self.assertIn("fail", verdicts(run_rule("SR-HERO-01", five)))
        four_full = self._hero_lane(geometry=geo(4, 1100))
        self.assertIn("fail", verdicts(run_rule("SR-HERO-01", four_full)))

    def test_hero01_two_line_display_passes(self):
        geometry = {"sections": {"sec-0": {"headings": [
            {"tag": "h1", "cls": "c-heading--display", "text": "Claim",
             "lines": 2, "fontPx": 56, "display": True}]}}, "page": {}}
        rows = run_rule("SR-HERO-01", self._hero_lane(geometry=geometry))
        self.assertEqual(verdicts(rows), {"pass"})

    def test_hero02_three_sentences_fail_statically(self):
        lane = self._hero_lane(sub="One thing. Two things. Three things now.")
        self.assertIn("fail", verdicts(run_rule("SR-HERO-02", lane)))

    def test_hero02_five_rendered_lines_fail(self):
        geometry = {"sections": {"sec-0": {"headings": [], "paragraphs": [
            {"text": "long lede", "lines": 5, "fontPx": 20,
             "cls": "c-paragraph"}]}}, "page": {}}
        lane = self._hero_lane(sub="A perfectly short lede.",
                               geometry=geometry)
        self.assertIn("fail", verdicts(run_rule("SR-HERO-02", lane)))

    def test_hero04_sentence_eyebrow_fails(self):
        lane = self._hero_lane(
            eyebrow="We are launching the next platform today.")
        rows = run_rule("SR-HERO-04", lane)
        self.assertIn("fail", verdicts(rows))

    def test_hero04_register_label_passes(self):
        lane = self._hero_lane(eyebrow="NEW · AGENTS")
        self.assertEqual(verdicts(run_rule("SR-HERO-04", lane)), {"pass"})

    def test_hero04_meta_row_is_not_a_kicker(self):
        """A dot-separated logistics row riding the eyebrow register (the
        meta-forward archetype device) audits under SR-HERO-05, never against
        the 5-word kicker cap."""
        lane = self._hero_lane(
            eyebrow="Oct 8, 2026 · 9:00 AM ET · Streamed live")
        self.assertEqual(verdicts(run_rule("SR-HERO-04", lane)), {"skip"})

    def test_hero05_promoted_proof_row_fails(self):
        geometry = {"sections": {"sec-0": {
            "headings": [], "paragraphs": [], "bodyFontPx": 16,
            "proofRows": [{"cls": "cs-hero-trust", "fontPx": 24}]}},
            "page": {"bodyPx": 16}}
        lane = self._hero_lane(geometry=geometry)
        self.assertIn("fail", verdicts(run_rule("SR-HERO-05", lane)))


# ── stat-band rules ──────────────────────────────────────────────────────────────

def stat_band(*pairs) -> str:
    items = "".join(
        f'<div class="cs-stat-band-item"><div class="c-stat">'
        f'<span class="c-stat-value">{v}</span>'
        f'<span class="c-stat-label">{l}</span></div></div>'
        for v, l in pairs)
    return sec(0, f'<div class="cs-stat-band">{items}</div>')


class StatRules(Fixture):
    def test_stat01_wordy_value_fails(self):
        lane = self.lane(stat_band(("Global", "Reach"), ("12,000", "Seats")))
        rows = run_rule("SR-STAT-01", lane)
        self.assertIn("fail", verdicts(rows))
        self.assertIn("Global", rows[0]["detail"])

    def test_stat01_unit_worded_magnitudes_pass(self):
        lane = self.lane(stat_band(("90 days", "Update cadence"),
                                   ("6–12 months", "Entity setup"),
                                   ("$0", "Cost")))
        self.assertEqual(verdicts(run_rule("SR-STAT-01", lane)), {"pass"})

    def test_stat02_ratio_among_measured_fails(self):
        lane = self.lane(stat_band(("10,000+", "Users"), ("99.9%", "Uptime"),
                                   ("24/7", "Support")))
        rows = run_rule("SR-STAT-02", lane)
        self.assertIn("fail", verdicts(rows))
        self.assertIn("RATIO", rows[0]["detail"])

    def test_stat02_qualifier_drift_fails(self):
        lane = self.lane(stat_band(("170+", "Countries"), ("135", "Regions")))
        self.assertIn("fail", verdicts(run_rule("SR-STAT-02", lane)))

    def test_stat02_parallel_band_passes(self):
        lane = self.lane(stat_band(("170+", "Countries"), ("12,000+", "Seats"),
                                   ("98%", "Retention")))
        self.assertEqual(verdicts(run_rule("SR-STAT-02", lane)), {"pass"})

    def test_stat03_essay_label_fails(self):
        lane = self.lane(stat_band(
            ("170+", "Countries where the guidance is grounded in our own "
                     "local entities today"),
            ("12,000+", "Seats")))
        self.assertIn("fail", verdicts(run_rule("SR-STAT-03", lane)))

    def test_stat04_duplicate_and_overflow_fail(self):
        pairs = [(f"{n}%", "Growth") for n in range(10, 17)]
        pairs.append(("10%", "Growth"))
        self.assertIn("fail",
                      verdicts(run_rule("SR-STAT-04", self.lane(stat_band(*pairs)))))


# ── logo-strip rules ─────────────────────────────────────────────────────────────

def logo_strip(n: int) -> str:
    items = "".join(f'<div class="cs-logo-strip-item">'
                    f'<img src="m{i}.svg" alt="mark {i}"></div>'
                    for i in range(n))
    return sec(0, f'<div class="cs-logo-strip">{items}</div>')


class LogoRules(Fixture):
    def test_logo01_oversized_mark_fails_factless(self):
        geometry = {"sections": {"sec-0": {"strips": [
            {"itembox": False,
             "marks": [{"w": 90, "h": 40}, {"w": 90, "h": 40},
                       {"w": 200, "h": 70}]}]}}, "page": {}}
        lane = self.lane(logo_strip(3), geometry=geometry)
        self.assertIn("fail", verdicts(run_rule("SR-LOGO-01", lane)))

    def test_logo01_itembox_exact_binds_when_declared(self):
        geometry = {"sections": {"sec-0": {"strips": [
            {"itembox": True,
             "marks": [{"w": 153, "h": 76}, {"w": 153, "h": 70}]}]}},
            "page": {}}
        lane = self.lane(logo_strip(2), geometry=geometry)
        self.assertIn("fail", verdicts(run_rule("SR-LOGO-01", lane)))

    def test_logo02_three_marks_fail(self):
        self.assertIn("fail",
                      verdicts(run_rule("SR-LOGO-02", self.lane(logo_strip(3)))))

    def test_logo02_marquee_duplicates_dedupe(self):
        items = "".join(f'<div class="cs-logo-strip-item">'
                        f'<img src="m{i % 5}.svg"></div>' for i in range(10))
        lane = self.lane(sec(0, f'<div class="cs-logo-strip cs-marquee">'
                                f'{items}</div>'))
        rows = run_rule("SR-LOGO-02", lane)
        self.assertEqual(verdicts(rows), {"pass"})
        self.assertIn("5 distinct", rows[0]["detail"])

    def test_logo04_heading_scale_caption_fails(self):
        geometry = {"sections": {"sec-0": {
            "strips": [{"itembox": False, "marks": []}],
            "eyebrows": [{"text": "TRUSTED BY", "fontPx": 28}],
            "captions": [], "bodyFontPx": 16}}, "page": {"bodyPx": 16}}
        lane = self.lane(logo_strip(4), geometry=geometry)
        self.assertIn("fail", verdicts(run_rule("SR-LOGO-04", lane)))


# ── capture-form rules ───────────────────────────────────────────────────────────

def form_sec(fields_html: str, actions_html: str = "", extra: str = "") -> str:
    return sec(0, f'<section class="cs-conversion-sec"><form class='
                  f'"cs-signup-panel">{fields_html}{actions_html}</form>'
                  f'{extra}</section>')


class FormRules(Fixture):
    def test_form01_nine_visible_controls_fail(self):
        fields = "".join(f'<div class="cs-field"><label>F{i}</label>'
                         f'<input type="text" required></div>' for i in range(9))
        lane = self.lane(form_sec(fields))
        rows = run_rule("SR-FORM-01", lane)
        self.assertIn("fail", verdicts(rows))

    def test_form01_radio_group_counts_once(self):
        fields = ('<input type="radio" name="size"><input type="radio" '
                  'name="size"><input type="radio" name="size">'
                  '<input type="email">')
        lane = self.lane(form_sec(fields))
        rows = run_rule("SR-FORM-01", lane)
        self.assertIn("2 visible", rows[0]["detail"])

    def test_form04_two_submits_fail(self):
        lane = self.lane(form_sec(
            '<input type="email">',
            '<button type="submit" class="c-button">Go</button>'
            '<button type="submit" class="c-button">Also go</button>'))
        self.assertIn("fail", verdicts(run_rule("SR-FORM-04", lane)))

    def test_form04_filled_sibling_fails(self):
        lane = self.lane(form_sec(
            '<input type="email">',
            '<button type="submit" class="c-button">Go</button>'
            '<a class="c-button">Second loud action</a>'))
        self.assertIn("fail", verdicts(run_rule("SR-FORM-04", lane)))

    def test_form04_one_filled_submit_quiet_sibling_passes(self):
        lane = self.lane(form_sec(
            '<input type="email">',
            '<button type="submit" class="c-button">Go</button>'
            '<a class="c-button c-button--secondary">Quiet</a>'))
        self.assertEqual(verdicts(run_rule("SR-FORM-04", lane)), {"pass"})

    def test_form05_pii_without_consent_fails(self):
        lane = self.lane(form_sec('<label>Work email</label>'
                                  '<input type="email">'))
        self.assertIn("fail", verdicts(run_rule("SR-FORM-05", lane)))

    def test_form05_consent_line_passes(self):
        lane = self.lane(form_sec(
            '<input type="email">',
            extra='<p class="cs-signup-consent">We handle data per the '
                  'Privacy Policy.</p>'))
        self.assertEqual(verdicts(run_rule("SR-FORM-05", lane)), {"pass"})

    def test_form06_label_grammar_drift_fails(self):
        fields = ('<div class="cs-field"><label>Full name</label>'
                  '<input type="text"></div>'
                  '<div class="cs-field"><label>PLEASE ENTER YOUR WORK '
                  'EMAIL:</label><input type="email"></div>')
        lane = self.lane(form_sec(fields))
        self.assertIn("fail", verdicts(run_rule("SR-FORM-06", lane)))


# ── pricing-tier rules ───────────────────────────────────────────────────────────

def tier(name, price, tagline="Tag line.", bullets=3, cta="Choose plan",
         cta_cls="c-button c-button--secondary", head_extra="", badge=""):
    lis = "".join(f"<li>Item {i}</li>" for i in range(bullets))
    lst = f'<ul class="cs-tier-list">{lis}</ul>' if bullets else ""
    btn = f'<a class="{cta_cls}">{cta}</a>' if cta else ""
    return (f'<article class="cs-tier">{badge}<header class="cs-tier-head'
            f'{head_extra}"><p class="c-caption cs-tier-name">{name}</p>'
            f'<div class="cs-tier-price">{price}</div>'
            f'<p class="cs-tier-tagline">{tagline}</p></header>{lst}{btn}'
            f'</article>')


def tier_band(*cards) -> str:
    return sec(0, f'<div class="cs-tiers">{"".join(cards)}</div>')


class TierRules(Fixture):
    def test_tier01_missing_cta_breaks_parity(self):
        lane = self.lane(tier_band(tier("Free", "Free"),
                                   tier("Pro", "$99", cta="")))
        self.assertIn("fail", verdicts(run_rule("SR-TIER-01", lane)))

    def test_tier01_identical_anatomy_passes(self):
        lane = self.lane(tier_band(tier("Free", "Free"), tier("Pro", "$99")))
        self.assertEqual(verdicts(run_rule("SR-TIER-01", lane)), {"pass"})

    def test_tier02_two_emphasized_cards_fail(self):
        lane = self.lane(tier_band(
            tier("Free", "Free", head_extra=" cs-tier-head--surface"),
            tier("Pro", "$99", head_extra=" cs-tier-head--surface"),
            tier("Max", "$199")))
        self.assertIn("fail", verdicts(run_rule("SR-TIER-02", lane)))

    def test_tier02_filled_cta_off_the_emphasized_card_fails(self):
        lane = self.lane(tier_band(
            tier("Free", "Free", cta_cls="c-button"),
            tier("Pro", "$99", head_extra=" cs-tier-head--surface")))
        rows = run_rule("SR-TIER-02", lane)
        self.assertIn("fail", verdicts(rows))
        self.assertEqual(rows[0]["severity"], "advisory",
                         "stage-B demotion: a real lane licenses the "
                         "highlight/conversion split")

    def test_tier03_off_shape_price_fails(self):
        lane = self.lane(tier_band(tier("A", "$99"),
                                   tier("B", "99 dollars")))
        self.assertIn("fail", verdicts(run_rule("SR-TIER-03", lane)))

    def test_tier03_mixed_period_suffix_fails(self):
        lane = self.lane(tier_band(tier("A", "$99/mo"), tier("B", "$199")))
        self.assertIn("fail", verdicts(run_rule("SR-TIER-03", lane)))

    def test_tier03_seat_qualifier_is_not_a_period_suffix(self):
        lane = self.lane(tier_band(tier("A", "$149"),
                                   tier("B", "$549 five seats"),
                                   tier("C", "Free")))
        self.assertEqual(verdicts(run_rule("SR-TIER-03", lane)), {"pass"})

    def test_tier04_runaway_list_fails(self):
        lane = self.lane(tier_band(tier("A", "$9", bullets=3),
                                   tier("B", "$99", bullets=12)))
        self.assertIn("fail", verdicts(run_rule("SR-TIER-04", lane)))

    def test_tier05_five_tiers_fail(self):
        lane = self.lane(tier_band(*(tier(f"T{i}", f"${i}9")
                                     for i in range(5))))
        self.assertIn("fail", verdicts(run_rule("SR-TIER-05", lane)))


# ── quote rules ──────────────────────────────────────────────────────────────────

class QuoteRules(Fixture):
    def test_quote01_unmarked_quote_copy_fails(self):
        inner = ('<p class="c-paragraph">“A long unmarked customer quote that '
                 'reads like testimony but carries no quote semantics at '
                 'all.”</p>')
        lane = self.lane(sec(0, inner),
                         sections=[{"id": "sec-0", "useCase": "testimonial",
                                    "slots": []}])
        self.assertIn("fail", verdicts(run_rule("SR-QUOTE-01", lane)))

    def test_quote01_person_anatomy_counts_as_marked(self):
        inner = ('<article class="cs-bento-cell cs-bento-cell--lead">'
                 '<p class="c-paragraph">“The agent flagged three things in '
                 'our first supervised run.”</p>'
                 '<div class="c-person">Elena Marchetti</div></article>')
        lane = self.lane(sec(0, f'<div class="cs-bento">{inner}</div>'),
                         sections=[{"id": "sec-0", "useCase": "testimonial",
                                    "slots": []}])
        self.assertEqual(verdicts(run_rule("SR-QUOTE-01", lane)), {"pass"})

    def test_quote01_display_scale_quote_fails_geometry(self):
        inner = ('<article class="cs-module cs-module--quote"><p>“Big quote '
                 'here that rides the display register itself.”</p>'
                 '<div class="c-person">Name</div></article>')
        geometry = {"sections": {"sec-0": {"quotes": [56]}},
                    "page": {"displayPx": 56}}
        lane = self.lane(sec(0, inner), geometry=geometry)
        self.assertIn("fail", verdicts(run_rule("SR-QUOTE-01", lane)))

    def test_quote02_unattributed_quote_fails(self):
        inner = ('<article class="cs-module cs-module--quote"><p>“We shipped '
                 'faster than we ever have before, full stop.”</p></article>')
        lane = self.lane(sec(0, inner))
        self.assertIn("fail", verdicts(run_rule("SR-QUOTE-02", lane)))

    def test_quote04_slogan_length_quote_fails(self):
        inner = ('<article class="cs-module cs-module--quote"><p>“Just '
                 'great.”</p><div class="c-person">Ana</div></article>')
        lane = self.lane(sec(0, inner))
        self.assertIn("fail", verdicts(run_rule("SR-QUOTE-04", lane)))


# ── feature-grid rules ───────────────────────────────────────────────────────────

def module(heading="Feature name", body="One useful sentence.", icon=False,
           link=False, eyebrow=False):
    bits = []
    if icon:
        bits.append('<img src="i.svg">')
    if eyebrow:
        bits.append('<p class="c-eyebrow">KIND</p>')
    bits.append(f"<h3>{heading}</h3>")
    if body:
        bits.append(f"<p>{body}</p>")
    if link:
        bits.append('<a href="#">More</a>')
    return f'<article class="cs-module">{"".join(bits)}</article>'


def grid(*cells) -> str:
    return sec(0, f'<div class="cs-modules">{"".join(cells)}</div>')


class GridRules(Fixture):
    def test_grid01_divergent_cell_fails(self):
        lane = self.lane(grid(module(icon=True), module(icon=True),
                              module(icon=False)))
        self.assertIn("fail", verdicts(run_rule("SR-GRID-01", lane)))

    def test_grid01_bento_defacto_lead_is_exempt(self):
        cells = ('<article class="cs-bento-cell"><h3>Lead</h3><p>Body copy '
                 'here.</p><img src="x.png"><a href="#">Go</a></article>'
                 + "".join(f'<article class="cs-bento-cell"><h3>C{i}</h3>'
                           f'<p>Body copy here.</p></article>'
                           for i in range(3)))
        lane = self.lane(sec(0, f'<div class="cs-bento">{cells}</div>'))
        self.assertEqual(verdicts(run_rule("SR-GRID-01", lane)), {"pass"})

    def test_grid02_essay_heading_fails(self):
        lane = self.lane(grid(
            module(heading="Ship"),
            module(heading="A fourteen word heading that keeps going well "
                           "past any reasonable scan budget entirely")))
        self.assertIn("fail", verdicts(run_rule("SR-GRID-02", lane)))

    def test_grid03_depth_spread_fails(self):
        lane = self.lane(grid(
            module(body="Short."),
            module(body="This body runs much longer than its sibling with "
                        "clause after clause piling up detail because the "
                        "generator padded one cell instead of writing the "
                        "actual delta between the two plans on offer.")))
        self.assertIn("fail", verdicts(run_rule("SR-GRID-03", lane)))

    def test_grid04_mixed_icon_scale_fails(self):
        geometry = {"sections": {"sec-0": {"icons": [
            {"w": 24, "h": 24}, {"w": 24, "h": 24}, {"w": 44, "h": 44}]}},
            "page": {}}
        lane = self.lane(grid(module(icon=True), module(icon=True),
                              module(icon=True)), geometry=geometry)
        self.assertIn("fail", verdicts(run_rule("SR-GRID-04", lane)))


# ── faq rules ────────────────────────────────────────────────────────────────────

def faq(*items) -> str:
    body = "".join(f'<details name="g"><summary>{q}</summary><p>{a}</p>'
                   f"</details>" for q, a in items)
    return sec(0, f'<div class="cs-faq">{body}</div>')


ANSWER = ("Yes — the plan covers this in full, and the details live in the "
          "policy document that ships with every seat you buy today.")


class FaqRules(Fixture):
    def test_faq01_statement_trigger_fails(self):
        lane = self.lane(faq(("Our features", ANSWER),
                             ("Is it secure?", ANSWER),
                             ("What does it cost?", ANSWER)))
        rows = run_rule("SR-FAQ-01", lane)
        self.assertIn("fail", verdicts(rows))
        self.assertIn("Our features", rows[0]["detail"])

    def test_faq01_question_forms_pass(self):
        lane = self.lane(faq(("Is it secure?", ANSWER),
                             ("How does billing work?", ANSWER),
                             ("Can I cancel anytime?", ANSWER)))
        self.assertEqual(verdicts(run_rule("SR-FAQ-01", lane)), {"pass"})

    def test_faq02_objection_theater_fails(self):
        lane = self.lane(faq(("Is it secure?", "Yes, very."),
                             ("How fast?", ANSWER), ("Why us?", ANSWER)))
        self.assertIn("fail", verdicts(run_rule("SR-FAQ-02", lane)))

    def test_faq03_two_items_fail(self):
        lane = self.lane(faq(("Is it secure?", ANSWER),
                             ("How fast is it?", ANSWER)))
        self.assertIn("fail", verdicts(run_rule("SR-FAQ-03", lane)))

    def test_faq04_cta_in_every_answer_fails(self):
        link_answer = ANSWER + ' <a href="#">Start free</a>'
        lane = self.lane(faq(("Is it secure?", link_answer),
                             ("How fast?", link_answer),
                             ("Why us?", link_answer)))
        self.assertIn("fail", verdicts(run_rule("SR-FAQ-04", lane)))


# ── cta-band rules ───────────────────────────────────────────────────────────────

class CtaRules(Fixture):
    def test_cta01_feature_grid_inside_band_fails(self):
        inner = ('<section class="cs-conversion-sec"><h2>Ready?</h2>'
                 '<div class="cs-modules"><article class="cs-module">'
                 "</article></div></section>")
        lane = self.lane(sec(0, inner))
        self.assertIn("fail", verdicts(run_rule("SR-CTA-01", lane)))

    def test_cta01_long_support_copy_fails(self):
        words = " ".join(["word"] * 35)
        inner = (f'<section class="cs-conversion-sec"><h2>Ready?</h2>'
                 f'<p class="c-paragraph">{words}</p></section>')
        lane = self.lane(sec(0, inner))
        self.assertIn("fail", verdicts(run_rule("SR-CTA-01", lane)))

    def test_cta03_noun_pile_label_fails(self):
        inner = ('<section class="cs-conversion-sec"><h2>Go</h2>'
                 '<a class="c-button">Platform information</a></section>')
        lane = self.lane(sec(0, inner))
        self.assertIn("fail", verdicts(run_rule("SR-CTA-03", lane)))

    def test_cta03_verb_led_label_passes(self):
        inner = ('<section class="cs-conversion-sec"><h2>Go</h2>'
                 '<a class="c-button">Start your migration</a></section>')
        lane = self.lane(sec(0, inner))
        self.assertEqual(verdicts(run_rule("SR-CTA-03", lane)), {"pass"})


# ── chrome parity rules ──────────────────────────────────────────────────────────

NAV = ('<nav class="cs-nav"><span class="cs-navlinks">{items}</span></nav>')
BRAND_NAV = {"navbar": {"primary": [{"label": "Products"},
                                    {"label": "Pricing"}]}}


def nav_html(*labels) -> str:
    return NAV.format(items="".join(
        f'<span class="cs-nav-tab"><button>{l}</button></span>'
        for l in labels))


class NavRules(Fixture):
    def test_nav01_invented_and_dropped_labels_fail(self):
        lane = self.lane(nav_html("Products", "Why us") + sec(0, "<h2>x</h2>"),
                         brand=BRAND_NAV)
        rows = run_rule("SR-NAV-01", lane)
        self.assertIn("fail", verdicts(rows))
        self.assertIn("Why us", rows[0]["detail"])
        self.assertIn("Pricing", rows[0]["detail"])

    def test_nav01_matching_roster_passes(self):
        lane = self.lane(nav_html("Products", "Pricing") + sec(0, "<h2>x</h2>"),
                         brand=BRAND_NAV)
        self.assertEqual(verdicts(run_rule("SR-NAV-01", lane)), {"pass"})

    def test_nav03_measured_chrome_records_override(self):
        lane = self.lane(nav_html("Products") + sec(0, "<h2>x</h2>"),
                         brand=BRAND_NAV)
        self.assertEqual(verdicts(run_rule("SR-NAV-03", lane)), {"override"})

    def test_nav03_factless_pitchy_label_fails(self):
        lane = self.lane(nav_html("Get started free today now")
                         + sec(0, "<h2>x</h2>"), brand={})
        self.assertIn("fail", verdicts(run_rule("SR-NAV-03", lane)))


FOOT = ('<div id="sec-9" class="cs-surface" data-layout="closing-bookend">'
        '<section class="cs-section cs-footer-sec"><div class="c-footer">'
        "{cols}{tail}</div></section></div>")
BRAND_FOOT = {"footer": {
    "columns": [{"heading": "Product", "links": [{"label": "A"}]},
                {"heading": "Company", "links": [{"label": "B"}]}],
    "social": [{"network": "x"}, {"network": "youtube"}],
    "legal": "© Fixture Inc."}}


def foot_html(headings, social=2, legal=True) -> str:
    cols = "".join(f'<div class="c-foot-col"><span class="c-foot-col-head">'
                   f"{h}</span><a class=\"c-foot-col-link\">L</a></div>"
                   for h in headings)
    tail = "".join(f'<a class="c-foot-glyph" href="#s{i}"></a>'
                   for i in range(social))
    if legal:
        tail += '<p class="c-foot-legal">© Fixture Inc.</p>'
    return FOOT.format(cols=cols, tail=tail)


class FootRules(Fixture):
    def test_foot01_dropped_column_fails(self):
        lane = self.lane(foot_html(["Product"]) + sec(0, "<h2>x</h2>"),
                         brand=BRAND_FOOT)
        self.assertIn("fail", verdicts(run_rule("SR-FOOT-01", lane)))

    def test_foot01_matching_anatomy_passes(self):
        lane = self.lane(foot_html(["Product", "Company"])
                         + sec(0, "<h2>x</h2>"), brand=BRAND_FOOT)
        self.assertEqual(verdicts(run_rule("SR-FOOT-01", lane)), {"pass"})

    def test_foot02_missing_legal_line_fails(self):
        lane = self.lane(foot_html(["Product", "Company"], legal=False)
                         + sec(0, "<h2>x</h2>"), brand=BRAND_FOOT)
        self.assertIn("fail", verdicts(run_rule("SR-FOOT-02", lane)))


# ── carousel rules ───────────────────────────────────────────────────────────────

class CarouselRules(Fixture):
    def test_car01_divergent_slides_fail(self):
        inner = ('<div class="cs-edgecut"><div class="cs-modules">'
                 + module(icon=True) + module(icon=True) + module(icon=False)
                 + "</div></div>")
        lane = self.lane(sec(0, inner))
        self.assertIn("fail", verdicts(run_rule("SR-CAR-01", lane)))

    def test_car02_two_frame_carousel_fails(self):
        inner = ('<div class="cs-edgecut"><div class="cs-modules">'
                 + module() + module() + "</div></div>")
        lane = self.lane(sec(0, inner))
        self.assertIn("fail", verdicts(run_rule("SR-CAR-02", lane)))


# ── orchestration + real lane ────────────────────────────────────────────────────

class Orchestration(Fixture):
    def test_delegated_rows_reported_absent_families_skip(self):
        lane_dir = self.tmp
        make_lane(lane_dir, sec(0, '<p class="c-eyebrow">GO</p>'
                                   '<h1 class="c-heading--display">Hi</h1>'),
                  sections=[{"id": "sec-0", "useCase": "hero", "slots": []}])
        entry = sra.audit_lane_html(lane_dir, lane_dir / "index.html",
                                    sra.load_rules(), {}, None)
        by_rule = {}
        for f in entry["findings"]:
            by_rule.setdefault(f["rule"], []).append(f["verdict"])
        self.assertIn("delegated", by_rule.get("SR-HERO-03", []),
                      "delegated hero row must be reported")
        self.assertIn("skip", by_rule.get("pricing-tiers", []),
                      "absent family must emit a skip finding")

    def test_lane_verdict_gates_required_only(self):
        entry = {"findings": [
            {"rule": "a", "severity": "advisory", "verdict": "fail"},
            {"rule": "b", "severity": "required", "verdict": "pass"}]}
        self.assertEqual(sra.lane_verdict(entry), ("PASS", 0, 1))
        entry["findings"][1]["verdict"] = "fail"
        self.assertEqual(sra.lane_verdict(entry), ("FAIL", 1, 1))


@unittest.skipUnless(EVENT_LANE.exists(), "event lane not present")
class RealLaneStatic(unittest.TestCase):
    """The static layer holds green (no required fails) on the copy-first
    event lane — the real-lane side of the fixture doctrine (the full battery
    run is recorded in evals/matrix/changes.md)."""

    def test_event_lane_static_required_green(self):
        entry = sra.audit_lane_html(
            EVENT_LANE, EVENT_LANE / "index.html", sra.load_rules(),
            {}, None)
        self.assertEqual(entry["scope"], "generative")
        required_fails = [f for f in entry["findings"]
                          if f["verdict"] == "fail"
                          and f["severity"] == "required"]
        self.assertFalse(required_fails, required_fails)

    def test_event_agenda_not_detected_as_faq(self):
        entry = sra.audit_lane_html(
            EVENT_LANE, EVENT_LANE / "index.html", sra.load_rules(), {}, None)
        self.assertNotIn("faq", entry["sections"].get("sec-3", []),
                         "agenda accordion must not bind the faq family")
        self.assertIn("faq", entry["sections"].get("sec-6", []))


if __name__ == "__main__":
    unittest.main()
