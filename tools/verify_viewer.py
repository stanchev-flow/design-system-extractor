import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:1500/viewer.html?version=greenhouse"
OUT = "runs/greenhouse/_viewer_unified.png"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)

        final_url = page.url
        body_text = page.inner_text("body")
        has_loading = "Loading" in body_text and "screenshots" not in body_text
        # Lane 1 screenshot
        shot_visible = page.eval_on_selector(
            "#o-shot", "el => el && el.style.display !== 'none' && !!el.getAttribute('src')"
        )
        # Lanes 2 & 3 selects + iframes
        sel_counts = page.eval_on_selector_all(
            'select[data-lane]', "els => els.map(e => e.options.length)"
        )
        frame_srcs = page.eval_on_selector_all(
            'iframe[data-lane]', "els => els.map(e => e.getAttribute('src') || '')"
        )
        # Sidebar present + toggle
        sidebar_display = page.eval_on_selector("#sidebar", "el => getComputedStyle(el).display")
        side_tab_count = page.eval_on_selector_all("#side-tabs button", "els => els.length")
        # Toggle off then on to prove it works
        page.click("#info-toggle")
        page.wait_for_timeout(300)
        sidebar_after_toggle = page.eval_on_selector("#sidebar", "el => getComputedStyle(el).display")
        page.click("#info-toggle")
        page.wait_for_timeout(600)

        page.screenshot(path=OUT, full_page=False)
        browser.close()

        print("final_url:", final_url)
        print("has_stuck_loading:", has_loading)
        print("lane1_screenshot_ok:", shot_visible)
        print("lane_select_option_counts:", sel_counts)
        print("lane_iframe_srcs:", [s[:70] for s in frame_srcs])
        print("sidebar_display_initial:", sidebar_display)
        print("sidebar_display_after_toggle:", sidebar_after_toggle)
        print("sidebar_tab_count:", side_tab_count)
        print("console_errors:", errors)
        print("screenshot:", OUT)

        ok = (
            "/project/greenhouse" in final_url
            and not has_loading
            and shot_visible
            and len(sel_counts) == 2
            and all(c >= 1 for c in sel_counts)
            and len(frame_srcs) == 2
            and all(s for s in frame_srcs)
            and sidebar_display == "flex"
            and sidebar_after_toggle == "none"
            and side_tab_count >= 4
        )
        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
