#!/usr/bin/env python3
"""Browser verification and screenshots for this Studio item only."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from audit_pages import AUDIT_JS  # noqa: E402
from component_fidelity_audit import (  # noqa: E402
    SNAPSHOT_JS,
    compare,
    expected_contract,
    focus_expected,
    normalize_expected,
)

URL = "http://127.0.0.1:1500/runs/relume-test/brand/compose/" + quote(HERE.name) + "/index.html"


def verify() -> None:
    composition = json.loads((HERE / "composition.json").read_text())
    reports = []
    component_failures: list[dict] = []
    checked_component_properties = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for label, viewport, screenshot in (
            ("desktop", {"width": 1440, "height": 1000}, "preview.png"),
            ("mobile", {"width": 390, "height": 844}, "preview-mobile.png"),
        ):
            page = browser.new_page(viewport=viewport)
            response = page.goto(URL, wait_until="networkidle")
            assert response and response.ok
            page.evaluate(
                """async () => {
                  for (const image of document.images) {
                    image.loading = 'eager';
                    image.scrollIntoView({block:'center'});
                    try { await image.decode(); } catch (_) {}
                  }
                  scrollTo(0, 0);
                }"""
            )
            page.screenshot(path=str(HERE / screenshot), full_page=True)
            readability = page.evaluate(AUDIT_JS)
            geometry = page.evaluate(
                """() => ({
                  scrollWidth: document.documentElement.scrollWidth,
                  clientWidth: document.documentElement.clientWidth,
                  surfaces: [...document.querySelectorAll('[data-surface]')].map(x => x.dataset.surface),
                  images: [...document.images].map(i => ({
                    src: i.getAttribute('src'), complete: i.complete,
                    naturalWidth: i.naturalWidth, naturalHeight: i.naturalHeight,
                    renderedWidth: i.getBoundingClientRect().width,
                    renderedHeight: i.getBoundingClientRect().height,
                    fit: getComputedStyle(i).objectFit
                  })),
                  mediaStretchFailures: [...document.querySelectorAll('.opener-frame img,.media-frame img,.story-card img')]
                    .filter(i => Math.abs((i.getBoundingClientRect().width/i.getBoundingClientRect().height) -
                      (i.naturalWidth/i.naturalHeight)) > .035 && getComputedStyle(i).objectFit !== 'cover').length
                })"""
            )
            asset_failures = [x for x in geometry["images"] if x["naturalWidth"] == 0]
            interaction = {"menu": "not-applicable"}
            if label == "mobile":
                menu = page.locator(".menu-control")
                menu.focus()
                menu.press("Enter")
                interaction["menu"] = {
                    "expanded": menu.get_attribute("aria-expanded"),
                    "actionsVisible": page.locator(".nav-actions").is_visible(),
                }
            reports.append(
                {
                    "viewport": label,
                    "readability": readability,
                    "geometry": {
                        "horizontalOverflow": geometry["scrollWidth"] > geometry["clientWidth"],
                        "surfaces": geometry["surfaces"],
                        "mediaStretchFailures": geometry["mediaStretchFailures"],
                    },
                    "assetsChecked": len(geometry["images"]),
                    "assetFailures": asset_failures,
                    "interaction": interaction,
                }
            )
            page.close()

        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(URL, wait_until="networkidle")
        for name in ("primary", "secondary", "tertiary", "textCta", "menu"):
            contract = composition["componentContracts"][name]
            probe = page.evaluate_handle(
                """name => {
                  const e=document.createElement('button'); e.type='button';
                  e.dataset.control=name; e.className='control--'+name+(name==='menu'?' menu-control':'');
                  e.textContent=name; e.style.setProperty('display','inline-flex','important');
                  e.style.setProperty('transition','none','important'); document.body.append(e); return e
                }""",
                name,
            ).as_element()
            assert probe
            for state in ("rest", "hover", "pressed", "disabled"):
                probe.evaluate("el=>{el.disabled=false;el.blur()}")
                page.mouse.move(1000, 700)
                if state == "hover":
                    probe.hover(force=True)
                elif state == "pressed":
                    box = probe.bounding_box()
                    assert box
                    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    page.mouse.down()
                elif state == "disabled":
                    probe.evaluate("el=>el.disabled=true")
                actual = probe.evaluate(SNAPSHOT_JS)
                resolved = expected_contract(contract, state, False)
                expected = normalize_expected(page, resolved)
                keys = (
                    "background", "color", "borderWidth", "borderStyle", "borderColor",
                    "radius", "paddingTop", "paddingRight", "fontSize", "fontWeight",
                )
                if resolved.get("height", "auto") != "auto":
                    keys += ("height",)
                component_failures.extend(compare(actual, expected, keys, {"component": name, "state": state}))
                checked_component_properties += len(keys)
                if state == "pressed":
                    page.mouse.up()
            probe.evaluate("el=>{el.disabled=false;el.focus()}")
            actual = probe.evaluate(SNAPSHOT_JS)
            expected = focus_expected(page, contract["focus"])
            component_failures.extend(
                compare(actual, expected, ("outlineWidth", "outlineStyle", "outlineColor", "outlineOffset"), {"component": name, "state": "focus"})
            )
            checked_component_properties += 4
            probe.evaluate("el=>el.remove()")
        page.close()
        browser.close()

    css_has_generic_ratio = "4/3" in (HERE / "index.html").read_text()
    failures = []
    for report in reports:
        if report["readability"]["failures"]:
            failures.append({"kind": "contrast", "viewport": report["viewport"], "details": report["readability"]["failures"]})
        if report["geometry"]["horizontalOverflow"]:
            failures.append({"kind": "horizontal-overflow", "viewport": report["viewport"]})
        if report["geometry"]["surfaces"] != composition["surfaceSequence"]:
            failures.append({"kind": "surface-sequence", "viewport": report["viewport"]})
        if report["geometry"]["mediaStretchFailures"]:
            failures.append({"kind": "media-stretch", "viewport": report["viewport"]})
        if report["assetFailures"]:
            failures.append({"kind": "asset", "viewport": report["viewport"]})
    if css_has_generic_ratio:
        failures.append({"kind": "generic-4:3-ratio"})
    failures.extend({"kind": "component-fidelity", **x} for x in component_failures)
    if reports[1]["interaction"]["menu"] != {"expanded": "true", "actionsVisible": True}:
        failures.append({"kind": "mobile-menu"})

    result = {
        "schemaVersion": "relume-test.editorial-variant-verification.v1",
        "item": HERE.name,
        "url": URL,
        "status": "pass" if not failures else "fail",
        "viewports": reports,
        "componentFidelity": {
            "checkedProperties": checked_component_properties,
            "failures": component_failures,
        },
        "genericFourThreeRatio": css_has_generic_ratio,
        "failures": failures,
    }
    (HERE / "verification-report.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Remote Variant — Editorial Flow verification",
        "",
        f"- Status: **{result['status'].upper()}**",
        f"- Component fidelity: {checked_component_properties} browser-computed properties; {len(component_failures)} mismatches.",
        f"- Generic 4:3 media ratio: {'present' if css_has_generic_ratio else 'absent'}.",
    ]
    for report in reports:
        lines.append(
            f"- {report['viewport']}: {report['assetsChecked']} assets, worst text contrast "
            f"{report['readability']['worstTextContrast']}:1, "
            f"{len(report['readability']['failures'])} contrast failures, "
            f"overflow={report['geometry']['horizontalOverflow']}, "
            f"stretch failures={report['geometry']['mediaStretchFailures']}."
        )
    (HERE / "verification-report.md").write_text("\n".join(lines) + "\n")
    composition["acceptanceStatus"] = result["status"]
    (HERE / "composition.json").write_text(json.dumps(composition, indent=2) + "\n")
    if failures:
        raise SystemExit(json.dumps(failures, indent=2))


if __name__ == "__main__":
    verify()
