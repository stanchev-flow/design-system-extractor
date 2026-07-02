// Reveal-safe full-page screenshot for the A/B experiment.
// Both arms use an IntersectionObserver scroll-reveal that leaves below-fold content
// at opacity:0 during a fullPage capture. Both pages honour prefers-reduced-motion by
// skipping the reveal (content stays fully visible), so we emulate reduced motion —
// applied identically to BOTH arms, so the comparison stays fair.
// Usage: node shoot_reveal_safe.mjs <file> <out.png> [width] [height]
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , inArg, outArg, wArg, hArg] = process.argv;
const url = inArg.startsWith("http") || inArg.startsWith("file:")
  ? inArg
  : pathToFileURL(path.resolve(inArg)).href;
const width = parseInt(wArg || "1440", 10);
const height = parseInt(hArg || "900", 10);

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width, height },
  deviceScaleFactor: 2,
  reducedMotion: "reduce",   // both pages skip the reveal -> all content visible
});
await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(800); // let self-hosted webfonts settle
await page.screenshot({ path: outArg, fullPage: true });
await browser.close();
console.log("shot", outArg);
