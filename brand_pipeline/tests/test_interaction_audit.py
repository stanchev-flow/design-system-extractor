#!/usr/bin/env python3
"""Unit tests for the interaction-contract auditor (brand_pipeline/interaction_audit.py).

STATIC layer only (no Playwright in unit tests). Synthetic fixtures are small inline
HTML strings shaped like the renderer's real output signatures (cs-nav-tab + cs-mega,
details.cs-nav-lang, details[name] accordion groups, cs-edgecut rails, cs-marquee
halves, cs-utility-banner, labelled forms, cs-reveal choreography), so the detectors
exercised here are the ones the baseline run uses on real lanes.

Contract reference: brand_pipeline/spec/interaction-contracts.md

Run:  ./venv/bin/python -m pytest brand_pipeline/tests/test_interaction_audit.py -q
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

import interaction_audit as ia  # noqa: E402


def statuses(findings, check):
    return [f.status for f in findings if f.check == check]


def worst(findings, check):
    rank = {"fail": 3, "advisory": 2, "pass": 1, "skip": 0}
    got = statuses(findings, check)
    if not got:
        return None
    return max(got, key=lambda s: rank[s])


def page(body: str, css: str = "", script: str = "") -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<style>{css}</style></head><body>{body}"
        f"<script>{script}</script></body></html>"
    )


# --------------------------------------------------------------------------- nav

PASSING_NAV = page("""
<nav class="cs-nav">
  <span class="cs-nav-tab">
    <button aria-expanded="false" aria-controls="mega-1">Products
      <span class="cs-nav-chev" aria-hidden="true"></span></button>
    <div class="cs-mega" id="mega-1"><ul><li><a href="/a">Item A</a></li></ul></div>
  </span>
</nav>
""")

FAILING_NAV = page("""
<nav class="cs-nav">
  <span class="cs-nav-tab">
    <a class="c-arrow-link" href="">Products<span class="cs-nav-chev" aria-hidden="true"></span></a>
    <div class="cs-mega"><ul><li><a href="/a">Item A</a></li></ul></div>
  </span>
</nav>
""")

MENU_ROLE_NAV = page("""
<nav class="cs-nav" role="menubar">
  <span class="cs-nav-tab" role="menuitem">
    <button aria-expanded="false">Products</button>
    <div class="cs-mega"><ul role="menu"><li><a href="/a">A</a></li></ul></div>
  </span>
</nav>
""")


class TestNavFamily(unittest.TestCase):
    def test_passing_disclosure_nav(self):
        findings = ia.audit_static(PASSING_NAV, "fixture")
        self.assertEqual(worst(findings, "IC-NAV-01"), "pass")
        self.assertEqual(worst(findings, "IC-NAV-02"), "pass")
        self.assertEqual(worst(findings, "IC-NAV-03"), "pass")
        self.assertEqual(worst(findings, "IC-NAV-04"), "pass")

    def test_failing_nav_no_aria_expanded_and_empty_href(self):
        findings = ia.audit_static(FAILING_NAV, "fixture")
        self.assertEqual(worst(findings, "IC-NAV-01"), "fail")   # <a href=""> trigger
        self.assertEqual(worst(findings, "IC-NAV-02"), "fail")   # no aria-expanded
        f = next(f for f in findings if f.check == "IC-NAV-02" and f.status == "fail")
        self.assertEqual(f.severity, "required")
        self.assertEqual(f.layer, "static")
        self.assertIsNotNone(f.line)          # locator: line number
        self.assertIn("c-arrow-link", f.snippet or "")  # locator: trigger snippet

    def test_menu_roles_in_nav_are_flagged(self):
        findings = ia.audit_static(MENU_ROLE_NAV, "fixture")
        self.assertEqual(worst(findings, "IC-NAV-03"), "fail")

    def test_nav_family_skips_when_absent(self):
        findings = ia.audit_static(page("<main><p>copy</p></main>"), "fixture")
        self.assertEqual(worst(findings, "IC-NAV-01"), "skip")


# -------------------------------------------------------------------------- lang

LANG_PASS = page("""
<nav class="cs-nav"><span class="cs-nav-util">
<details class="cs-nav-lang">
  <summary class="cs-nav-util-link" aria-label="Select language — current: English">
    <span class="cs-nav-util-icon" aria-hidden="true"></span></summary>
  <ul class="cs-nav-lang-menu">
    <li><a class="cs-nav-lang-item" href="/" hreflang="en-us" aria-current="true">English</a></li>
    <li><a class="cs-nav-lang-item" href="/fr-fr" hreflang="fr-fr">Français</a></li>
  </ul>
</details></span></nav>
""")

LANG_UNNAMED = page("""
<nav class="cs-nav">
<details class="cs-nav-lang">
  <summary class="cs-nav-util-link"><span class="cs-nav-util-icon" aria-hidden="true"></span></summary>
  <ul><li><a href="/" hreflang="en-us">English</a></li></ul>
</details></nav>
""")


class TestLangFamily(unittest.TestCase):
    def test_native_details_language_switcher_passes(self):
        findings = ia.audit_static(LANG_PASS, "fixture")
        self.assertEqual(worst(findings, "IC-LANG-01"), "pass")
        self.assertEqual(worst(findings, "IC-LANG-02"), "pass")
        self.assertEqual(worst(findings, "IC-LANG-03"), "pass")
        self.assertEqual(worst(findings, "IC-LANG-04"), "pass")

    def test_icon_only_summary_and_missing_current_marker_fail(self):
        findings = ia.audit_static(LANG_UNNAMED, "fixture")
        self.assertEqual(worst(findings, "IC-LANG-02"), "fail")
        self.assertEqual(worst(findings, "IC-LANG-03"), "fail")

    def test_disclosure_navigation_menu_skips_selection_marking(self):
        # a generic utility MENU rendered with the lang device (plain nav links,
        # no hreflang facts, non-selector name) has no selection concept —
        # IC-LANG-03 records as skipped, never as a required fail; the toggle
        # checks (LANG-01/02) still apply.
        menu = page("""
<nav class="cs-nav"><span class="cs-nav-util">
<details class="cs-nav-lang">
  <summary class="cs-nav-util-link" aria-label="About">About</summary>
  <ul class="cs-nav-lang-menu">
    <li><a class="cs-nav-lang-item" href="/our-story">About Us</a></li>
    <li><a class="cs-nav-lang-item" href="/careers">Careers</a></li>
  </ul>
</details></span></nav>
""")
        findings = ia.audit_static(menu, "fixture")
        self.assertEqual(worst(findings, "IC-LANG-01"), "pass")
        self.assertEqual(worst(findings, "IC-LANG-02"), "pass")
        self.assertEqual(worst(findings, "IC-LANG-03"), "skip")

    def test_selector_named_menu_still_requires_current_marker(self):
        # the SAME anatomy whose toggle declares selector purpose keeps the
        # required selection check (a real language switcher can't dodge it by
        # dropping hreflang).
        switcher = page("""
<nav class="cs-nav">
<details class="cs-nav-lang">
  <summary class="cs-nav-util-link" aria-label="Select language">Language</summary>
  <ul><li><a class="cs-nav-lang-item" href="/">English</a></li>
      <li><a class="cs-nav-lang-item" href="/fr">Français</a></li></ul>
</details></nav>
""")
        findings = ia.audit_static(switcher, "fixture")
        self.assertEqual(worst(findings, "IC-LANG-03"), "fail")


# --------------------------------------------------------------------- accordion

ACCORDION_PASS = page("""
<section><div class="cs-acc-col">
  <details class="c-acc-item" name="acc-fixture" open>
    <summary class="c-acc-trigger"><span class="c-acc-label">Payroll</span>
      <span class="c-acc-chev" aria-hidden="true"><svg viewBox="0 0 10 6"></svg></span></summary>
    <div class="c-acc-panel"><p>Panel one copy.</p></div>
  </details>
  <details class="c-acc-item" name="acc-fixture">
    <summary class="c-acc-trigger"><span class="c-acc-label">Benefits</span>
      <span class="c-acc-chev" aria-hidden="true"><svg viewBox="0 0 10 6"></svg></span></summary>
    <div class="c-acc-panel"><p>Panel two copy.</p></div>
  </details>
</div></section>
""")

ACCORDION_NO_NAME = page("""
<section>
  <details class="c-faq-item" open><summary class="c-faq-q">Is it free?</summary><p>Yes.</p></details>
  <details class="c-faq-item"><summary class="c-faq-q">Who writes it?</summary><p>We do.</p></details>
  <details class="c-faq-item"><summary class="c-faq-q">How current?</summary><p>Quarterly.</p></details>
</section>
""")

ACCORDION_EMPTY_SUMMARY = page("""
<section>
  <details class="c-faq-item" name="g"><summary class="c-faq-q">
    <span class="c-faq-icon" aria-hidden="true">+</span></summary><p>Body.</p></details>
  <details class="c-faq-item" name="g"><summary class="c-faq-q">Named item</summary><p>Body.</p></details>
</section>
""")


class TestAccordionFamily(unittest.TestCase):
    def test_native_details_accordion_passes(self):
        findings = ia.audit_static(ACCORDION_PASS, "fixture")
        self.assertEqual(worst(findings, "IC-ACC-01"), "pass")   # shared name
        self.assertEqual(worst(findings, "IC-ACC-02"), "pass")   # summary first child
        self.assertEqual(worst(findings, "IC-ACC-03"), "pass")   # summary labelled
        self.assertEqual(worst(findings, "IC-ACC-04"), "pass")   # icons aria-hidden
        self.assertEqual(worst(findings, "IC-ACC-05"), "pass")   # one item open

    def test_group_without_shared_name_fails_single_open_contract(self):
        findings = ia.audit_static(ACCORDION_NO_NAME, "fixture")
        self.assertEqual(worst(findings, "IC-ACC-01"), "fail")

    def test_icon_only_summary_fails_labelling(self):
        findings = ia.audit_static(ACCORDION_EMPTY_SUMMARY, "fixture")
        self.assertEqual(worst(findings, "IC-ACC-03"), "fail")

    def test_language_switcher_details_not_treated_as_accordion(self):
        findings = ia.audit_static(LANG_PASS, "fixture")
        self.assertEqual(worst(findings, "IC-ACC-01"), "skip")


# ------------------------------------------------------------------------ banner

BANNER_PASS = page("""
<div id="page-banner"><div class="cs-utility-banner">
  <p class="cs-utility-banner-text">Notice copy.</p>
  <button class="cs-utility-banner-close" type="button" aria-label="Dismiss">
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 2L14 14"/></svg></button>
</div></div>
""")

BANNER_UNNAMED = page("""
<div class="cs-utility-banner">
  <p class="cs-utility-banner-text">Notice copy.</p>
  <button class="cs-utility-banner-close" type="button">
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 2L14 14"/></svg></button>
</div>
""")

BANNER_NOT_A_BUTTON = page("""
<div class="cs-utility-banner">
  <p class="cs-utility-banner-text">Notice copy.</p>
  <a class="cs-utility-banner-close" aria-label="Dismiss"><svg aria-hidden="true"></svg></a>
</div>
""")


class TestBannerFamily(unittest.TestCase):
    def test_labelled_button_close_passes(self):
        findings = ia.audit_static(BANNER_PASS, "fixture")
        self.assertEqual(worst(findings, "IC-BAN-01"), "pass")
        self.assertEqual(worst(findings, "IC-BAN-02"), "pass")
        self.assertEqual(worst(findings, "IC-BAN-03"), "pass")

    def test_unnamed_close_fails(self):
        findings = ia.audit_static(BANNER_UNNAMED, "fixture")
        self.assertEqual(worst(findings, "IC-BAN-02"), "fail")

    def test_anchor_close_fails_button_contract(self):
        findings = ia.audit_static(BANNER_NOT_A_BUTTON, "fixture")
        self.assertEqual(worst(findings, "IC-BAN-01"), "fail")


# ---------------------------------------------------------------------- carousel

CAROUSEL_UNNAMED_CONTROLS = page("""
<section>
  <div class="cs-edgecut"><div class="cs-modules cs-modules--edgecut">
    <article class="cs-module"><p>Card one</p></article>
    <article class="cs-module"><p>Card two</p></article>
  </div></div>
  <div class="cs-rail-controls">
    <button class="cs-rail-prev"><svg aria-hidden="true"></svg></button>
    <button class="cs-rail-next"><svg aria-hidden="true"></svg></button>
  </div>
</section>
""")

CAROUSEL_NAMED_CONTROLS = page("""
<section>
  <div class="cs-edgecut"><div class="cs-modules cs-modules--edgecut">
    <article class="cs-module"><p>Card one</p></article>
  </div></div>
  <div class="cs-rail-controls">
    <button class="cs-rail-prev" aria-label="Previous cards"><svg aria-hidden="true"></svg></button>
    <button class="cs-rail-next" aria-label="Next cards"><svg aria-hidden="true"></svg></button>
  </div>
</section>
""")

BARE_RAIL = page("""
<section><div class="cs-edgecut"><div class="cs-modules cs-modules--edgecut">
  <article class="cs-module"><p>Quote card</p></article>
</div></div></section>
""")


class TestCarouselFamily(unittest.TestCase):
    def test_carousel_without_accessible_prev_next_fails(self):
        findings = ia.audit_static(CAROUSEL_UNNAMED_CONTROLS, "fixture")
        self.assertEqual(worst(findings, "IC-CAR-01"), "fail")
        f = next(f for f in findings if f.check == "IC-CAR-01" and f.status == "fail")
        self.assertIn("accessible name", f.message)

    def test_carousel_with_named_prev_next_passes(self):
        findings = ia.audit_static(CAROUSEL_NAMED_CONTROLS, "fixture")
        self.assertEqual(worst(findings, "IC-CAR-01"), "pass")

    def test_bare_rail_without_controls_or_region_fails(self):
        findings = ia.audit_static(BARE_RAIL, "fixture")
        self.assertEqual(worst(findings, "IC-CAR-01"), "fail")


# ----------------------------------------------------------------------- marquee

MARQUEE_CSS_CALMED = """
.cs-marquee-track { animation: cs-marquee-scroll 30s linear infinite; }
@media (prefers-reduced-motion: reduce) { .cs-marquee .cs-marquee-track { animation: none; } }
"""

MARQUEE_PASS = page("""
<div class="cs-logo-strip cs-marquee"><div class="cs-marquee-track">
  <div class="cs-marquee-half"><span class="cs-logo-strip-item">Logo</span></div>
  <div class="cs-marquee-half" aria-hidden="true"><span class="cs-logo-strip-item">Logo</span></div>
</div></div>
""", css=MARQUEE_CSS_CALMED)

MARQUEE_CLONE_NOT_HIDDEN = page("""
<div class="cs-logo-strip cs-marquee"><div class="cs-marquee-track">
  <div class="cs-marquee-half"><span class="cs-logo-strip-item">Logo</span></div>
  <div class="cs-marquee-half"><span class="cs-logo-strip-item">Logo</span></div>
</div></div>
""", css=MARQUEE_CSS_CALMED)

MARQUEE_NO_REDUCED_MOTION = page("""
<div class="cs-marquee"><div class="cs-marquee-track">
  <div class="cs-marquee-half"><span>Logo</span></div>
  <div class="cs-marquee-half" aria-hidden="true"><span>Logo</span></div>
</div></div>
""", css=".cs-marquee-track { animation: scroll 30s linear infinite; }")


class TestMarqueeFamily(unittest.TestCase):
    def test_hidden_clone_and_reduced_motion_pass(self):
        findings = ia.audit_static(MARQUEE_PASS, "fixture")
        self.assertEqual(worst(findings, "IC-MARQ-01"), "pass")
        self.assertEqual(worst(findings, "IC-MARQ-02"), "pass")

    def test_marquee_clone_without_aria_hidden_fails(self):
        findings = ia.audit_static(MARQUEE_CLONE_NOT_HIDDEN, "fixture")
        self.assertEqual(worst(findings, "IC-MARQ-01"), "fail")

    def test_missing_reduced_motion_rule_fails(self):
        findings = ia.audit_static(MARQUEE_NO_REDUCED_MOTION, "fixture")
        self.assertEqual(worst(findings, "IC-MARQ-02"), "fail")


# -------------------------------------------------------------------------- form

FORM_LABELLED = page("""
<form class="cs-signup-panel" action="#" method="post">
  <label class="cs-field-label" for="fx-email">Work email</label>
  <input class="cs-input" id="fx-email" type="email" name="email" required
         data-error="Check the email address." aria-describedby="fx-email-help">
  <span class="cs-field-help" id="fx-email-help">We never share it.</span>
  <label class="cs-choice"><input type="radio" name="pass" value="a" checked>Virtual</label>
  <button class="c-button" type="submit">Sign up</button>
</form>
""")

FORM_UNLABELLED = page("""
<form class="cs-signup-panel" action="#" method="post">
  <span class="cs-field-label">Work email</span>
  <input class="cs-input" type="email" name="email" placeholder="you@company.com">
  <button class="c-button" type="submit">Sign up</button>
</form>
""")

FORM_MOCK_LABEL = page("""
<div class="ex"><label class="c-field c-field--boxed">
  <span class="c-field-text">Enter your email</span></label></div>
""")

FORM_LINK_SUBMIT = page("""
<form action="#"><label for="n">Name</label><input id="n" type="text" name="n">
  <a class="c-button" role="button" href="#">Send</a></form>
""")


class TestFormFamily(unittest.TestCase):
    def test_labelled_field_passes(self):
        findings = ia.audit_static(FORM_LABELLED, "fixture")
        self.assertEqual(worst(findings, "IC-FORM-01"), "pass")
        self.assertEqual(worst(findings, "IC-FORM-02"), "pass")
        self.assertEqual(worst(findings, "IC-FORM-03"), "pass")
        self.assertEqual(worst(findings, "IC-FORM-04"), "pass")
        self.assertEqual(worst(findings, "IC-FORM-05"), "pass")

    def test_unlabelled_field_fails(self):
        findings = ia.audit_static(FORM_UNLABELLED, "fixture")
        self.assertEqual(worst(findings, "IC-FORM-01"), "fail")
        f = next(f for f in findings if f.check == "IC-FORM-01" and f.status == "fail")
        self.assertIn("email", f.message)

    def test_display_only_label_mock_fails_association(self):
        findings = ia.audit_static(FORM_MOCK_LABEL, "fixture")
        self.assertEqual(worst(findings, "IC-FORM-03"), "fail")

    def test_form_without_real_submit_fails(self):
        findings = ia.audit_static(FORM_LINK_SUBMIT, "fixture")
        self.assertEqual(worst(findings, "IC-FORM-02"), "fail")


# ------------------------------------------------------------------------ reveal

REVEAL_GATED = page(
    "<main><div class='cs-slot'><p>Copy</p></div></main>",
    css="""
.cs-motion-ready .cs-reveal { opacity: 0; transform: translateY(8px); }
.cs-motion-ready .cs-reveal.is-in { opacity: 1; transform: none; }
@media (prefers-reduced-motion: reduce) {
  .cs-reveal, .cs-motion-ready .cs-reveal { opacity: 1 !important; transform: none !important; }
}
""",
    script="""
(function () {
  if (!('IntersectionObserver' in window)) return;
  document.documentElement.classList.add('cs-motion-ready');
  var nodes = [].slice.call(document.querySelectorAll('.cs-slot > *'));
  nodes.forEach(function (n) { n.classList.add('cs-reveal'); });
  setTimeout(function () { nodes.forEach(function (n) { n.classList.add('is-in'); }); }, 4000);
})();
""")

REVEAL_UNGATED = page(
    "<main><div class='cs-slot'><p>Copy</p></div></main>",
    css=".cs-reveal { opacity: 0; } .cs-reveal.is-in { opacity: 1; }",
    script="document.querySelectorAll('.cs-slot > *').forEach(n => n.classList.add('cs-reveal'));")


class TestRevealFamily(unittest.TestCase):
    def test_gated_reveal_with_failsafe_passes(self):
        findings = ia.audit_static(REVEAL_GATED, "fixture")
        self.assertEqual(worst(findings, "IC-REV-01"), "pass")
        self.assertEqual(worst(findings, "IC-REV-02"), "pass")
        self.assertEqual(worst(findings, "IC-REV-03"), "pass")

    def test_ungated_hidden_state_fails(self):
        findings = ia.audit_static(REVEAL_UNGATED, "fixture")
        self.assertEqual(worst(findings, "IC-REV-01"), "fail")
        self.assertEqual(worst(findings, "IC-REV-02"), "fail")


# ------------------------------------------------------------- reports & CLI glue

class TestReportsAndCli(unittest.TestCase):
    def test_aggregate_takes_worst_status(self):
        f_pass = ia.Finding(check="IC-X-01", family="nav", severity="required",
                            status="pass", lane="l", layer="static", message="ok")
        f_fail = ia.Finding(check="IC-X-01", family="nav", severity="required",
                            status="fail", lane="l", layer="static", message="bad")
        cells = ia._aggregate([f_pass, f_fail])
        self.assertEqual(cells[("l", "nav", "IC-X-01")], "fail")

    def test_static_only_cli_writes_reports_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lane = tmp_path / "lane" / "index.html"
            lane.parent.mkdir(parents=True)
            lane.write_text(FAILING_NAV, encoding="utf-8")
            out = tmp_path / "out"
            rc = ia.main([str(lane), "--static-only", "--out", str(out)])
            self.assertEqual(rc, 0)  # baseline mode: exit 0 despite failures
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["auditor_version"], ia.AUDITOR_VERSION)
            self.assertTrue((out / "report.md").exists())
            checks = {f["check"]: f["status"] for f in report["lanes"][0]["findings"]
                      if f["status"] == "fail"}
            self.assertIn("IC-NAV-02", checks)
            self.assertIn("IC-NAV-02", report["summary"]["required_check_failures"])
            # lane provenance recorded for mid-run re-render correlation
            self.assertTrue(report["lanes"][0]["audited_mtime"])
            self.assertEqual(len(report["lanes"][0]["sha256_12"]), 12)

    def test_strict_flag_exits_one_on_required_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lane = tmp_path / "index.html"
            lane.write_text(FAILING_NAV, encoding="utf-8")
            rc = ia.main([str(lane), "--static-only", "--strict",
                          "--out", str(tmp_path / "out")])
            self.assertEqual(rc, 1)

    def test_strict_flag_exits_zero_when_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lane = tmp_path / "index.html"
            lane.write_text(PASSING_NAV, encoding="utf-8")
            rc = ia.main([str(lane), "--static-only", "--strict",
                          "--out", str(tmp_path / "out")])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
