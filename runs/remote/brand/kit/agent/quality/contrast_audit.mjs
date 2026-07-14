// contrast_audit.mjs — WCAG contrast audit for a rendered page (anti-ai-slop.md AS-01/AS-10).
//
// Loads the page headless, walks EVERY visible text element, resolves its computed color
// against its EFFECTIVE background (nearest ancestor with a non-transparent
// background-color — the surface it actually paints on, not an assumed one), and flags
// WCAG failures: < 4.5:1 for normal text, < 3:1 for large text (>=24px, or >=18.66px bold).
// Also audits each section's --c-link-hover custom property against that section's
// background — the hover-state check a screenshot review structurally misses (AS-10).
//
// Usage: node brand_pipeline/contrast_audit.mjs <path-to-index.html> [more.html ...]
// Exit code 1 if any page has failures.
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

function luminance([r, g, b]) {
  const c = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b);
}
function ratio(a, b) {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}
function parseRgb(s) {
  const m = /rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/.exec(s || "");
  if (!m) return null;
  const alpha = m[4] === undefined ? 1 : parseFloat(m[4]);
  return { rgb: [+m[1], +m[2], +m[3]], alpha };
}
// composite a semi-transparent fg over its bg (hairlines/ghosts use rgba)
function composite(fg, bg) {
  return fg.rgb.map((c, i) => Math.round(c * fg.alpha + bg[i] * (1 - fg.alpha)));
}

const browser = await chromium.launch();
let anyFail = false;

for (const target of process.argv.slice(2)) {
  const url = target.startsWith("http") ? target : pathToFileURL(path.resolve(target)).href;
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);

  const raw = await page.evaluate(() => {
    function effectiveBg(el) {
      let n = el;
      while (n && n !== document.documentElement) {
        const bg = getComputedStyle(n).backgroundColor;
        if (bg && !/rgba\(\s*0,\s*0,\s*0,\s*0\s*\)/.test(bg) && bg !== "transparent") return bg;
        n = n.parentElement;
      }
      return getComputedStyle(document.documentElement).backgroundColor || "rgb(255,255,255)";
    }
    const out = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const seen = new Set();
    while (walker.nextNode()) {
      const t = walker.currentNode;
      if (!t.textContent.trim()) continue;
      const el = t.parentElement;
      if (!el || seen.has(el)) continue;
      seen.add(el);
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none" || parseFloat(cs.opacity) === 0) continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (el.closest('[aria-hidden="true"]')) continue;   // ghost watermarks are decorative by contract
      out.push({
        text: t.textContent.trim().slice(0, 40),
        sel: el.className ? "." + String(el.className).trim().split(/\s+/)[0] : el.tagName.toLowerCase(),
        color: cs.color, bg: effectiveBg(el),
        px: parseFloat(cs.fontSize), weight: parseInt(cs.fontWeight, 10) || 400,
      });
    }
    // per-section link-hover vs section bg (the AS-10 hover check)
    const hovers = [];
    for (const sec of document.querySelectorAll('[id^="sec-"], body')) {
      const link = sec.querySelector(".c-arrow-link, .c-foot-sitemap-link, .c-foot-social-link");
      if (!link) continue;
      const hv = getComputedStyle(link).getPropertyValue("--c-link-hover").trim();
      if (!hv) continue;
      // resolve var refs to computed color by assigning it
      link.style.setProperty("color", `var(--c-link-hover)`);
      const resolved = getComputedStyle(link).color;
      link.style.removeProperty("color");
      hovers.push({ sec: sec.id || "body", hover: resolved, bg: (function eff(n){
        while (n && n !== document.documentElement) {
          const bg = getComputedStyle(n).backgroundColor;
          if (bg && !/rgba\(\s*0,\s*0,\s*0,\s*0\s*\)/.test(bg) && bg !== "transparent") return bg;
          n = n.parentElement;
        } return getComputedStyle(document.documentElement).backgroundColor; })(link) });
    }
    return { texts: out, hovers };
  });

  const fails = [];
  for (const t of raw.texts) {
    const fg = parseRgb(t.color), bg = parseRgb(t.bg);
    if (!fg || !bg) continue;
    const fgFlat = fg.alpha < 1 ? composite(fg, bg.rgb) : fg.rgb;
    const rr = ratio(fgFlat, bg.rgb);
    const large = t.px >= 24 || (t.px >= 18.66 && t.weight >= 700);
    const need = large ? 3.0 : 4.5;
    if (rr < need) fails.push(`  TEXT  ${rr.toFixed(2)}:1 (need ${need}) ${t.sel} "${t.text}" ${t.color} on ${t.bg}`);
  }
  for (const h of raw.hovers) {
    const fg = parseRgb(h.hover), bg = parseRgb(h.bg);
    if (!fg || !bg) continue;
    const rr = ratio(fg.alpha < 1 ? composite(fg, bg.rgb) : fg.rgb, bg.rgb);
    if (rr < 4.5) fails.push(`  HOVER ${rr.toFixed(2)}:1 (need 4.5) ${h.sec} --c-link-hover ${h.hover} on ${h.bg}`);
  }

  const name = target.split("/").slice(-2).join("/");
  if (fails.length) {
    anyFail = true;
    console.log(`FAIL ${name}  (${fails.length} contrast failures)`);
    for (const f of fails.slice(0, 12)) console.log(f);
    if (fails.length > 12) console.log(`  ... +${fails.length - 12} more`);
  } else {
    console.log(`PASS ${name}  (${raw.texts.length} text elements, ${raw.hovers.length} hover checks)`);
  }
  await page.close();
}
await browser.close();
process.exit(anyFail ? 1 : 0);
