import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:1500/project/greenhouse"
OUT = "runs/greenhouse/_sidebar_tabs.png"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page_errors = []
        console_errors = []
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.goto(URL, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(1500)

        # Ensure sidebar open
        disp = page.eval_on_selector("#sidebar", "el => getComputedStyle(el).display")
        if disp == "none":
            page.click("#info-toggle")
            page.wait_for_timeout(300)

        tabs = page.eval_on_selector_all(
            "#side-tabs button", "els => els.map(e => ({s: e.dataset.s, label: e.textContent.trim()}))"
        )
        print("TAB COUNT:", len(tabs))
        results = []
        for t in tabs:
            btn = page.query_selector(f'#side-tabs button[data-s="{t["s"]}"]')
            btn.click()
            page.wait_for_timeout(180)
            html_len = page.eval_on_selector("#side-body", "el => el.innerHTML.length")
            txt = page.eval_on_selector("#side-body", "el => el.innerText.trim().slice(0,40)")
            results.append((t["label"], t["s"], html_len, txt.replace("\n", " ")))

        page.screenshot(path=OUT, full_page=False)
        browser.close()

        print("\n%-22s %-20s %8s  %s" % ("LABEL", "KEY", "HTML_LEN", "PREVIEW"))
        for label, key, ln, txt in results:
            print("%-22s %-20s %8d  %s" % (label, key, ln, txt))
        print("\npage_errors:", page_errors)
        print("console_errors:", console_errors)
        print("screenshot:", OUT)

        empty = [r for r in results if r[2] < 30]
        ok = (not page_errors) and (not empty) and len(results) >= 10
        if empty:
            print("EMPTY TABS:", [r[0] for r in empty])
        print("RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
