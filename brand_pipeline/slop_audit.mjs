// slop_audit.mjs — section-completeness audit (anti-ai-slop.md AS-11..AS-14).
//
// Checks every section of a rendered page for the CONTENT-completeness failure shapes
// that a brand-rule gate and a contrast audit both structurally miss:
//   AS-11 under-filled section (metadata-only: eyebrow/caption/counter/CTA but no
//         heading + no substantive element)
//   AS-12 empty column in a grid/split layout (one side filled, the other structurally empty)
//   AS-13 information-bearing media (map/chart) without its data as text
//   AS-14 an input/form with no stated reason (no body copy before it in the section)
//
// Heuristic by design — it flags for HUMAN review, it does not prove correctness. A PASS
// means "no obvious empty-frame sections", not "the content is good".
//
// Usage: node brand_pipeline/slop_audit.mjs <index.html> [more.html ...]   (exit 1 on flags)
import { chromium } from "playwright";
import { pathToFileURL } from "node:url";
import path from "node:path";

const browser = await chromium.launch();
let anyFlag = false;

const WIDTHS = [1440, 1180];   // multi-viewport (anti-ai-slop AS-16): the collage
                               // head/body collision only appeared below ~1280px —
                               // single-width audits certify the one width you looked at.
for (const target of process.argv.slice(2)) {
  const url = target.startsWith("http") ? target : pathToFileURL(path.resolve(target)).href;
  for (const width of WIDTHS) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForTimeout(400);

  const flags = await page.evaluate(() => {
    const out = [];
    const sections = [...document.querySelectorAll('[id^="sec-"]')];
    const scope = sections.length ? sections : [document.body];

    const visible = (el) => {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden") return false;
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    };
    const realText = (el) => (el.textContent || "").trim();

    for (const sec of scope) {
      const id = sec.id || "page";
      if (sec.querySelector(".c-footer")) continue;   // footer is a chrome bookend, not a content section

      // ---- inventory of PRIMARY vs METADATA content ----
      const headings = [...sec.querySelectorAll("h1,h2,h3,.c-heading")]
        .filter(visible).filter(h => realText(h).length >= 8);
      const paras = [...sec.querySelectorAll("p")]
        .filter(visible)
        .filter(p => !p.matches(".c-eyebrow,.c-caption") && !p.closest('[aria-hidden="true"]'))
        .filter(p => realText(p).length >= 40);
      const media = [...sec.querySelectorAll("img,video,svg.c-image")]
        .filter(visible).filter(m => !m.closest(".cs-nav,.c-footer"));
      const rows = [...sec.querySelectorAll(".c-row, li, details")].filter(visible);
      const forms = [...sec.querySelectorAll("input,.c-field,form")].filter(visible);
      const metadata = [...sec.querySelectorAll(".c-eyebrow,.c-caption,.c-arrow-link")]
        .filter(visible);

      const primary = headings.length + paras.length + media.length + rows.length;

      // AS-11: metadata-only frame, or lone short heading
      if (primary === 0 && metadata.length > 0) {
        out.push(`AS-11 ${id}: metadata-only section (eyebrow/caption/CTA, no heading, no content)`);
      } else if (primary === headings.length && paras.length + media.length + rows.length + forms.length === 0) {
        const longest = Math.max(...headings.map(h => realText(h).length));
        if (longest < 40)
          out.push(`AS-11 ${id}: heading-only section and the heading is short (${longest} chars) — needs media, list, or description`);
      }

      // AS-12: empty column in a grid/split (direct children of a multi-col container)
      for (const grid of sec.querySelectorAll("*")) {
        const cs = getComputedStyle(grid);
        const isMultiCol = cs.display === "grid" &&
          (cs.gridTemplateColumns.split(" ").filter(x => x !== "0px").length >= 2);
        if (!isMultiCol || !visible(grid)) continue;
        // decorative overlays (ghost watermarks: absolute, aria-hidden) are not columns —
        // they don't occupy a grid track, so they must not count as an "empty column".
        const cols = [...grid.children].filter(visible)
          .filter(c => getComputedStyle(c).position !== "absolute")
          .filter(c => !c.matches('[aria-hidden="true"]') && !c.closest('[aria-hidden="true"]'));
        if (cols.length < 2) continue;
        const filled = cols.map(c =>
          realText(c).length >= 8 || c.querySelector("img,video,input,.c-field"));
        if (filled.some(Boolean) && filled.some(f => !f)) {
          out.push(`AS-12 ${id}: multi-column layout with an empty column (${filled.filter(f => !f).length} of ${cols.length} empty)`);
        }
      }

      // AS-23: naked image slots — every content image needs the surface-derived
      // placeholder backing (repeating-linear-gradient hatch). Logos/icons exempt.
      for (const im of media.filter(m => m.tagName === "IMG")) {
        const r = im.getBoundingClientRect();
        if (r.width < 80 || r.height < 80) continue;               // logo/icon scale
        if (im.closest(".c-logo--img,.cs-nav,.c-footer")) continue;
        const bg = getComputedStyle(im).backgroundImage;
        if (!/repeating-linear-gradient/.test(bg))
          out.push(`AS-23 ${id}: content image without placeholder backing (src=${(im.getAttribute("src") || "").slice(-40)})`);
      }

      // AS-13: map/chart media without data-like text in the same section
      // word-bounded: a bare /graph/ matched inside "photoGRAPHy" (every brand photo!) —
      // the classic substring-vs-word false positive.
      const infoMedia = media.filter(m =>
        /\b(map|chart|graph|diagram|floor ?plan)\b/i.test((m.getAttribute("alt") || "") + " " + (m.getAttribute("src") || "")));
      if (infoMedia.length) {
        const dataText = rows.length > 0 ||
          /\d{1,4}\s+\w+|\bstreet\b|\blane\b|\bave\b|\d{2}[:.]\d{2}|\bopen\b|\bhours\b/i.test(realText(sec));
        if (!dataText)
          out.push(`AS-13 ${id}: map/chart media but no address/data text in the section`);
      }

      // AS-16: text flush against media (missing gutter). Per-LINE boxes via Range so a
      // wrapped statement's individual lines are measured, not one giant bounding box.
      // Exempt: hero (#sec-0 sanctioned display-over-media), captions, aria-hidden.
      if (id !== "sec-0") {
        const textEls = [...sec.querySelectorAll("h1,h2,h3,.c-heading,p")]
          .filter(visible)
          .filter(t => !t.matches(".c-caption,.c-eyebrow") && !t.closest('[aria-hidden="true"]'))
          .filter(t => realText(t).length >= 8);
        for (const img of media) {
          const ir = img.getBoundingClientRect();
          for (const t of textEls) {
            if (t.contains(img) || img.contains(t)) continue;
            const range = document.createRange();
            range.selectNodeContents(t);
            for (const r of range.getClientRects()) {
              if (r.width < 4 || r.height < 4) continue;
              const vOverlap = !(r.bottom <= ir.top || r.top >= ir.bottom);
              const hOverlap = !(r.right <= ir.left || r.left >= ir.right);
              if (vOverlap && hOverlap) {
                out.push(`AS-16 ${id}: text intersects image ("${realText(t).slice(0, 30)}…")`);
                break;
              }
              if (vOverlap) {
                const gap = r.left >= ir.right ? r.left - ir.right
                          : r.right <= ir.left ? ir.left - r.right : null;
                if (gap !== null && gap < 16) {
                  out.push(`AS-16 ${id}: text ${Math.round(gap)}px from image edge (needs >=16px gutter)`);
                  break;
                }
              }
              if (hOverlap && r.top >= ir.bottom && r.top - ir.bottom < 16) {
                out.push(`AS-16 ${id}: text ${Math.round(r.top - ir.bottom)}px below image (needs >=16px gap)`);
                break;
              }
            }
          }
        }
      }

      // AS-14: form present, but no body copy (>=40 chars) BEFORE it in the section
      if (forms.length) {
        const firstForm = forms[0];
        const before = paras.some(p =>
          p.compareDocumentPosition(firstForm) & Node.DOCUMENT_POSITION_FOLLOWING);
        if (!before)
          out.push(`AS-14 ${id}: input/form with no stated reason (no body copy before it)`);
      }
    }
    return out;
  });

  const name = target.split("/").slice(-2).join("/") + ` @${width}px`;
  if (flags.length) {
    anyFlag = true;
    console.log(`FLAG ${name}  (${flags.length})`);
    for (const f of flags) console.log(`  ${f}`);
  } else {
    console.log(`PASS ${name}`);
  }
  await page.close();
  }
}
await browser.close();
process.exit(anyFlag ? 1 : 0);
