// Lane-local: full-page + per-section screenshots at 1440px.
// Usage: node shoot-sections.mjs <index.html> <outdir>
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , inArg, outDir] = process.argv;
const url = pathToFileURL(path.resolve(inArg)).href;
const width = 1440;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height: 1024 }, deviceScaleFactor: 2 });
await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1000);

await page.screenshot({ path: path.join(outDir, "full-1440.png"), fullPage: true });
console.log("shot full-1440.png");

const els = await page.$$("section.cs-section");
const ids = ["hero","problem","product-value","capabilities","how-it-works",
  "comparison","proof","conversion-beat","faq","lead-form","closing-bookend"];
for (let i = 0; i < els.length; i++) {
  const el = els[i];
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  const label = ids[i] || `section-${i}`;
  const name = `${String(i).padStart(2, "0")}-${label}.png`;
  await el.screenshot({ path: path.join(outDir, name) });
  console.log("shot", name);
}
await browser.close();
