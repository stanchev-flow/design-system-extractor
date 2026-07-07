#!/usr/bin/env python3
"""Screenshot the tokenized HubSpot validation page: full page + hero + actions/cta +
footer-end crops, plus computed-style samples for the mechanical verdict table."""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
PAGE = REPO / "runs/hubspot/brand/compose/signup-launch-tokenized/index.html"
SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)

SAMPLES = [
    # (label, selector, properties)
    ("hero display heading", ".cs-gallery-head .c-heading--display",
     ["font-family", "font-size", "font-weight", "text-transform", "letter-spacing", "color"]),
    ("eyebrow", ".c-eyebrow",
     ["font-family", "font-size", "font-weight", "text-transform", "letter-spacing", "color"]),
    ("arrow link (rendered CTA)", ".c-arrow-link",
     ["font-family", "font-size", "font-weight", "text-transform", "color", "text-decoration-line"]),
    ("paragraph", ".c-paragraph", ["font-family", "font-size", "font-weight", "color"]),
    ("boxed field", ".c-field--boxed", ["border-radius", "background-color", "border"]),
    ("section (2nd)", "section.cs-section:nth-of-type(2)", ["background-color", "padding-top"]),
    ("caption", ".c-caption", ["font-size", "text-transform", "letter-spacing"]),
]

VARS = ["--c-motion-fast", "--c-motion-base", "--c-motion-slow", "--c-ease",
        "--motion-fast", "--motion-base", "--motion-slow", "--motion-ease",
        "--radius", "--radius-button", "--button-bg", "--button-bg-hover",
        "--surface-surface-panel", "--color-accent-highlight", "--case-h2",
        "--size-display-hero-base", "--weight-display-hero", "--space-section-y-md"]


def main() -> None:
    out: dict = {"page": str(PAGE), "samples": {}, "root_vars": {}}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(PAGE.as_uri())
        pg.wait_for_timeout(1200)

        pg.screenshot(path=str(SHOTS / "tokenized-full.png"), full_page=True)
        # hero = first section
        hero = pg.locator("section.cs-section").first
        hero.screenshot(path=str(SHOTS / "tokenized-hero.png"))
        # actions: the conversion/cta stack (first cs-conversion-sec)
        cta = pg.locator("section.cs-conversion-sec").first
        cta.screenshot(path=str(SHOTS / "tokenized-cta.png"))
        # footer-end: last section
        last = pg.locator("section.cs-section").last
        last.screenshot(path=str(SHOTS / "tokenized-footer-end.png"))

        for label, sel, props in SAMPLES:
            loc = pg.locator(sel).first
            if loc.count() == 0:
                out["samples"][label] = None
                continue
            vals = loc.evaluate(
                "(el, props) => Object.fromEntries(props.map(p => "
                "[p, getComputedStyle(el).getPropertyValue(p)]))", props)
            out["samples"][label] = vals
        out["root_vars"] = pg.evaluate(
            "(vars) => { const cs = getComputedStyle(document.documentElement);"
            " return Object.fromEntries(vars.map(v => [v, cs.getPropertyValue(v).trim()])); }",
            VARS)
        # hero-scoped display size (the style poster clamp lives on #sec-0)
        out["hero_scope"] = pg.evaluate(
            "() => { const s = document.querySelector('section.cs-section');"
            " const cs = getComputedStyle(s);"
            " return { displaySize: cs.getPropertyValue('--c-display-size').trim(),"
            "          caseHeading: cs.getPropertyValue('--c-case-heading').trim(),"
            "          bg: cs.backgroundColor }; }")
        b.close()
    (HERE / "computed-samples.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
