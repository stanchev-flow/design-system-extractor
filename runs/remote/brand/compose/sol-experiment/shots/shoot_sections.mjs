// Lane-local deterministic screenshot capture for the GPT-5.6 Sol experiment.
// Usage: node shots/shoot_sections.mjs index.html shots
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , inArg, outDir] = process.argv;
const url = pathToFileURL(path.resolve(inArg)).href;
const browser = await chromium.launch({
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const page = await browser.newPage({
  viewport: { width: 1440, height: 1024 },
  deviceScaleFactor: 2,
});

await page.emulateMedia({ reducedMotion: "reduce" });
await page.goto(url, { waitUntil: "networkidle" });
await page.waitForTimeout(900);

await page.screenshot({
  path: path.join(outDir, "full-page-1440.png"),
  fullPage: true,
});
console.log("shot full page");

for (let index = 0; index < 10; index += 1) {
  const id = `sec-${index}`;
  const el = await page.$(`#${id}`);
  if (!el) {
    console.log("missing", id);
    continue;
  }
  const box = await el.boundingBox();
  if (!box || box.height < 4) {
    console.log("skip", id, box);
    continue;
  }
  const name = (await el.getAttribute("data-layout")) || id;
  await page.screenshot({
    path: path.join(outDir, `${id}-${name}.png`),
    clip: {
      x: 0,
      y: Math.max(0, box.y - 8),
      width: 1440,
      height: Math.min(box.height + 16, 6000),
    },
    fullPage: true,
  });
  console.log("shot", id, name, Math.round(box.height));
}

await browser.close();
