// Batch-1 verification screenshots.
// Proves (a) the top gap above the hero is normalized (nav is a page-level sibling, not
// padded inside the hero) and (b) nav + footer + inline link hovers go gold (#edd580).
// Usage: node shoot_batch1.mjs <index.html> <outDir> <tag> [width] [height]
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";
import fs from "node:fs";

const [, , inArg, outDir, tag, wArg, hArg] = process.argv;
const url = pathToFileURL(path.resolve(inArg)).href;
const width = parseInt(wArg || "1440", 10);
const height = parseInt(hArg || "900", 10);
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width, height },
  deviceScaleFactor: 2,
  reducedMotion: "reduce", // skip the scroll-reveal so all content is visible
});
await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(700);

const out = (name) => path.join(outDir, `${tag}-${name}.png`);

// (a) top-of-page: the slim nav bar flush above the hero (normalized top gap).
await page.screenshot({ path: out("top"), clip: { x: 0, y: 0, width, height } });

// authentic nav hover → the hovered nav link turns gold.
const navLink = page.locator("#page-nav .c-arrow-link").first();
if (await navLink.count()) {
  await navLink.hover();
  await page.waitForTimeout(250);
  const nav = page.locator("#page-nav");
  const box = await nav.boundingBox();
  if (box) {
    await page.screenshot({
      path: out("nav-hover"),
      clip: { x: 0, y: 0, width, height: Math.min(height, Math.ceil(box.y + box.height + 40)) },
    });
  }
}

// authentic inline arrow-link hover (first arrow-link inside a content section).
const inlineLink = page.locator('[id^="sec-"] .c-arrow-link').first();
if (await inlineLink.count()) {
  await inlineLink.scrollIntoViewIfNeeded();
  await inlineLink.hover();
  await page.waitForTimeout(250);
  const box = await inlineLink.boundingBox();
  if (box) {
    const y = Math.max(0, Math.floor(box.y - 220));
    await page.screenshot({ path: out("inline-hover"), clip: { x: 0, y, width, height: 460 } });
  }
}

// authentic footer sitemap-link hover → gold.
const footLink = page.locator(".c-foot-sitemap-link").first();
if (await footLink.count()) {
  await footLink.scrollIntoViewIfNeeded();
  await footLink.hover();
  await page.waitForTimeout(250);
  const box = await footLink.boundingBox();
  if (box) {
    const y = Math.max(0, Math.floor(box.y - 160));
    await page.screenshot({ path: out("footer-hover"), clip: { x: 0, y, width, height: 520 } });
  }
}

// all-links-gold proof: force the color-shift hover color on every link class at once so a
// single frame shows nav + footer + inline links in the resolved gold (var(--c-link-hover)).
await page.addStyleTag({
  content:
    ".c-arrow-link, .c-foot-sitemap-link, .c-foot-social-link { color: var(--c-link-hover) !important; }",
});
await page.waitForTimeout(150);
await page.screenshot({ path: out("all-hover-full"), fullPage: true });

await browser.close();
console.log("shot", tag, "->", outDir);
