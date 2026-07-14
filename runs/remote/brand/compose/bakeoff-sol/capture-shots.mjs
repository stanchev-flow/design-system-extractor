import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

const lane = path.resolve("runs/remote/brand/compose/bakeoff-sol");
const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1440, height: 1000 },
  deviceScaleFactor: 1,
});

await page.emulateMedia({ reducedMotion: "reduce" });
await page.goto(pathToFileURL(path.join(lane, "index.html")).href, {
  waitUntil: "networkidle",
});
await page.evaluate(() => document.fonts.ready);
await page.screenshot({
  path: path.join(lane, "shots", "full-page-1440.png"),
  fullPage: true,
});

const sectionNames = [
  "01-hero",
  "02-reporting-gap",
  "03-capabilities",
  "04-how-it-works",
  "05-leadership-views",
  "06-comparison",
  "07-customer-proof",
  "08-operational-trust",
  "09-faq",
  "10-lead-form",
];

for (let index = 0; index < sectionNames.length; index += 1) {
  const section = page.locator(`#sec-${index}`);
  await section.scrollIntoViewIfNeeded();
  await page.waitForTimeout(100);
  await section.screenshot({
    path: path.join(lane, "shots", `${sectionNames[index]}-1440.png`),
  });
}

await browser.close();
console.log(`Captured ${sectionNames.length + 1} screenshots.`);

