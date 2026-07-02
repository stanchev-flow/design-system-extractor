// Headless screenshot of a rendered section for on-brand fidelity checking.
// Usage: node shoot.mjs <file-url-or-path> <out.png> [width] [height]
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

const [, , inArg, outArg, wArg, hArg] = process.argv;
const url = inArg.startsWith("http") || inArg.startsWith("file:")
  ? inArg
  : pathToFileURL(path.resolve(inArg)).href;
const width = parseInt(wArg || "1440", 10);
const height = parseInt(hArg || "1024", 10);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 2 });
await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
await page.waitForTimeout(800); // let webfonts settle
await page.screenshot({ path: outArg, fullPage: true });
await browser.close();
console.log("shot", outArg);
