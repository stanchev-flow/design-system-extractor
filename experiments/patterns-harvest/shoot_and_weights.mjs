// Reveal-safe full-page screenshot + computed Melodrama-weight probe for the harvested
// layout-pattern demo page. Emulates reduced motion so the IntersectionObserver reveal
// leaves all content visible for a fullPage capture (identical treatment across pages).
// Usage: node shoot_and_weights.mjs <file> <out.png> [width] [height]
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , inArg, outArg, wArg, hArg] = process.argv;
const url = inArg.startsWith("http") || inArg.startsWith("file:")
  ? inArg : pathToFileURL(path.resolve(inArg)).href;
const width = parseInt(wArg || "1440", 10);
const height = parseInt(hArg || "900", 10);

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width, height },
  deviceScaleFactor: 2,
  reducedMotion: "reduce",
});
await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(900); // let self-hosted webfonts settle

// Probe computed font-weight + family for the hero display heading vs a section heading,
// and confirm the harvested sections actually rendered their structure.
const probe = await page.evaluate(() => {
  const cs = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const c = getComputedStyle(el);
    return { weight: c.fontWeight, family: c.fontFamily.split(",")[0].replace(/["']/g, "") };
  };
  return {
    hero: cs("#sec-0 .c-heading--display"),
    interlockStatement: cs("#sec-2 .cs-interlock .c-heading--display"),
    modules: document.querySelectorAll("#sec-1 .cs-module").length,
    moduleImgs: document.querySelectorAll("#sec-1 .cs-module-media .c-image").length,
    insetFloat: (() => {
      const el = document.querySelector("#sec-2 .cs-interlock-media");
      return el ? getComputedStyle(el).float : null;
    })(),
    insetWidthPx: (() => {
      const el = document.querySelector("#sec-2 .cs-interlock-media");
      return el ? Math.round(el.getBoundingClientRect().width) : null;
    })(),
  };
});
console.log(JSON.stringify(probe, null, 2));
await page.screenshot({ path: outArg, fullPage: true });
console.log("shot", outArg);
await browser.close();
