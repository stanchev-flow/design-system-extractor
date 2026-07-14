// Per-section closeups for the stress-playbook lane (lane-local tool, shared code untouched).
// Usage: node shoot_sections.mjs <index.html> <outdir> [secId ...]
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , inArg, outDir, ...only] = process.argv;
const url = pathToFileURL(path.resolve(inArg)).href;
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1024 }, deviceScaleFactor: 2 });
// reduced motion disables the scroll-reveal choreography (opacity-0 initial state),
// so below-fold sections are captured visible instead of mid-reveal / blank.
await page.emulateMedia({ reducedMotion: "reduce" });
await page.goto(url, { waitUntil: "networkidle" });
await page.waitForTimeout(900);
if (only[0] === "--full") {
  await page.screenshot({ path: path.join(outDir, "full-page-1440.png"), fullPage: true });
  console.log("shot full page");
  await browser.close();
  process.exit(0);
}
const ids = only.length ? only : await page.$$eval('[id^="sec-"]', els => els.map(e => e.id));
for (const id of ids) {
  const el = await page.$(`#${id}`);
  if (!el) continue;
  const box = await el.boundingBox();
  if (!box || box.height < 4) { console.log("skip", id, box); continue; }
  const name = await el.getAttribute("data-layout") || id;
  const clip = { x: 0, y: Math.max(0, box.y - 8), width: 1440, height: Math.min(box.height + 16, 6000) };
  await page.screenshot({ path: path.join(outDir, `${id}-${name}.png`), clip, fullPage: true });
  console.log("shot", id, name, Math.round(box.height));
}
await browser.close();
