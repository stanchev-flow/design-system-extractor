// AS-18/19/20 before/after proof shots.
// Usage: node shoot_alignment_fix.mjs <index.html> <outDir> <tag> [width]
//   <tag>-full.png            full page
//   <tag>-statement.png       the mission-statement ('What we hold') section, if present
//   <tag>-panel-hover.png     a cream-panel arrow link (GET DIRECTIONS) in :hover state
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";
import fs from "node:fs";

const [, , inArg, outDir, tag, wArg] = process.argv;
const url = pathToFileURL(path.resolve(inArg)).href;
const width = parseInt(wArg || "1440", 10);
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width, height: 900 },
  deviceScaleFactor: 2,
  reducedMotion: "reduce",
});
await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(700);
const out = (name) => path.join(outDir, `${tag}-${name}.png`);

await page.screenshot({ path: out("full"), fullPage: true });

const statement = page
  .locator('[data-layout="mission-statement"], .cs-statement-sec')
  .first();
if (await statement.count()) {
  await statement.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  const box = await statement.boundingBox();
  if (box) {
    await page.screenshot({
      path: out("statement"),
      clip: { x: 0, y: Math.max(0, box.y - 20), width, height: Math.min(1600, box.height + 60) },
    });
  }
}

const panelLink = page.locator(".cs-panel .c-arrow-link").first();
if (await panelLink.count()) {
  await panelLink.scrollIntoViewIfNeeded();
  await panelLink.hover();
  await page.waitForTimeout(300);
  const box = await panelLink.boundingBox();
  if (box) {
    const y = Math.max(0, Math.floor(box.y - 260));
    await page.screenshot({ path: out("panel-hover"), clip: { x: 0, y, width, height: 520 } });
  }
}

await browser.close();
console.log("shot", tag, "->", outDir);
