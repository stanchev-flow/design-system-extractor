#!/usr/bin/env python3
"""measure_chrome.py — computed-style measurement of the saved Remote homepage.

Loads the local capture in headless Chromium with JavaScript DISABLED (static
CSS only — mirrors the source_chrome.v2 offline approach), viewport 1440x900,
and records getComputedStyle/rect facts for navbar, hero, buttons, footer.
Output: chrome-measured.json (this folder).
"""
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
HTML = REPO / "screenshots" / "remote" / (
    "Remote — Global Employment Infrastructure _ EOR, Payroll & Compliance, "
    "Worldwide.html")

JS = """
() => {
  const pick = (el, props) => {
    if (!el) return null;
    const cs = getComputedStyle(el);
    const out = {};
    for (const p of props) out[p] = cs.getPropertyValue(p);
    const r = el.getBoundingClientRect();
    out._rect = { x: r.x, y: r.y, w: r.width, h: r.height };
    return out;
  };
  const q = (sel) => document.querySelector(sel);
  const btnProps = ['background-color','color','border','border-radius','padding',
                    'font-family','font-size','font-weight','line-height','letter-spacing','text-transform'];
  const txtProps = ['color','font-family','font-size','font-weight','line-height','letter-spacing','text-transform'];
  return {
    header: pick(q('.theme-header-v2'), ['background-color','padding','border-bottom','position']),
    headerInner: pick(q('.theme-header-v2 .theme-container'), ['max-width']),
    navLink: pick(q('.nav-links a.menu-link'), txtProps.concat(['padding','border-radius'])),
    navLogin: pick(q('.theme-header-v2 .nav-login-cta a'), txtProps),
    navCta: pick(q('.theme-header-v2 a.button.boxed'), btnProps),
    heroModule: pick(q('.hero-module'), ['background-color']),
    heroPanel: pick(q('.hero-mod'), ['background-color','border-radius','padding']),
    heroH1: pick(q('.hero-content h1'), txtProps),
    heroBody: pick(q('.hero-content p'), txtProps),
    heroPrimaryBtn: pick(q('.hero-content a.button.boxed'), btnProps),
    heroSecondaryBtn: pick(q('.hero-content a.button.outlined'), btnProps),
    eyebrowSocial: pick(q('.social-proof .main-heading-area .theme-lebel'), txtProps),
    eyebrowRed: pick(q('.accordion-split .heading-container .theme-lebel'), txtProps),
    h2Accordion: pick(q('.accordion-split .heading-container .main-heading'), txtProps),
    accordionActive: pick(q('.accordion-split .custom_accord.active'), ['background-color','border-color','border-radius']),
    banner: pick(q('.main-banner .content-col-inner'), ['background-color','border-radius','padding']),
    bannerHeading: pick(q('.main-banner .main-heading'), txtProps),
    imageCard: pick(q('.imageGrid .imageGrid-card'), ['background-color','border-radius','padding']),
    imageCardImg: pick(q('.imageGrid .imageGrid-card .card-img'), ['background-color','border-radius']),
    testimonialBox: pick(q('.testimonial-mod-v3 .swiper-slide .slide-box'), ['background-color','border-radius','padding']),
    footer: pick(q('.footer'), ['background-color','padding']),
    footerColHead: pick(q('.footer-v2-top .footer-v2-col p'), txtProps),
    footerLink: pick(q('.footer-v2-top .footer-v2-col ul li a'), txtProps),
    footerSocial: pick(q('.footer-v2-social-links ul li a'), ['background-color','border-radius','opacity']),
    body: pick(document.body, txtProps.concat(['background-color'])),
    htmlFont: pick(document.documentElement, ['font-size']),
  };
}
"""


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 900},
                          java_script_enabled=False)
        page.goto(HTML.as_uri(), wait_until="load", timeout=60000)
        facts = page.evaluate(JS)
        b.close()
    out = HERE / "chrome-measured.json"
    out.write_text(json.dumps(facts, indent=2))
    print(json.dumps(facts, indent=2))


if __name__ == "__main__":
    main()
