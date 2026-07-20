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
    // ADVISORY findings print for human review but never set the exit flag —
    // the channel AS-64's SHOULD arm rides (fix7; hard arms stay in `out`).
    const advisories = [];
    const sections = [...document.querySelectorAll('[id^="sec-"]')];
    const scope = sections.length ? sections : [document.body];

    const visible = (el) => {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden") return false;
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    };
    const realText = (el) => (el.textContent || "").trim();

    // AS-59: multi-action hierarchy. In any action GROUP exactly one action may
    // carry the filled primary register; siblings must take a DIFFERENT measured
    // register (outlined / ghost / text-link). Palette-agnostic: registers are
    // compared as COMPUTED paint (fill vs stroke vs bare text), never brand hexes —
    // two actions sharing one filled register in one group is the flag.
    const alphaOf = (c) => {
      const m = /rgba?\(([^)]+)\)/.exec(c || "");
      if (!m) return 0;
      const p = m[1].split(",");
      return p.length === 4 ? parseFloat(p[3]) : 1;
    };
    const actionRegister = (b) => {
      const cs = getComputedStyle(b);
      const bw = parseFloat(cs.borderTopWidth) || 0;
      const outlined = bw >= 1 && alphaOf(cs.borderTopColor) > 0.05 &&
        cs.borderTopColor !== cs.backgroundColor;
      if (outlined) return "outlined:" + cs.borderTopColor;
      if (alphaOf(cs.backgroundColor) > 0.05) return "filled:" + cs.backgroundColor;
      return "text";
    };
    const auditActionGroup = (g, where) => {
      const btns = [...g.querySelectorAll('.c-button, a[role="button"]')].filter(visible);
      if (btns.length < 2) return;
      const filled = btns.map(actionRegister).filter(r => r.startsWith("filled:"));
      const dupes = filled.filter((r, i) => filled.indexOf(r) !== i);
      if (dupes.length)
        out.push(`AS-59 ${where}: ${filled.length} same-register filled actions in one group (${dupes[0].slice(7)}) — exactly one primary; siblings take the measured secondary/ghost/text register`);
    };

    // AS-60: scaffold-habit action-group layout. A rendered multi-action group
    // that STAMPS its measured layout declaration (data-ag-gap / data-ag-align,
    // brand-schema §4.4f) must actually compute it — a group whose computed gap
    // or alignment contradicts its own stamp is running on scaffold habit over
    // brand facts. Declaration-driven and palette-agnostic: no stamps, no audit.
    const auditActionGroupFacts = (g, where) => {
      const kids = [...g.children].filter(visible);
      if (kids.length < 2) return;   // gap/alignment only observable on 2+ actions
      const cs = getComputedStyle(g);
      const declGap = parseFloat(g.getAttribute("data-ag-gap"));
      if (Number.isFinite(declGap)) {
        const computed = parseFloat(cs.columnGap) || 0;
        if (Math.abs(computed - declGap) > 2)
          out.push(`AS-60 ${where}: action-group gap ${Math.round(computed)}px contradicts its declared fact ${declGap}px (scaffold habit over measured actionGroup facts)`);
      }
      const declAlign = g.getAttribute("data-ag-align");
      if (declAlign) {
        // contexts that own their anchor are the schema's sanctioned exception
        const anchored = g.closest('.cs-foot, [data-align="centered"], .cs-hero-panel--center')
          || getComputedStyle(g.parentElement).alignItems === "center";
        // a group box that HUGS its content run leaves justify-content nothing
        // to distribute — the computed value is unobservable there, not a habit
        const first = kids[0].getBoundingClientRect();
        const last = kids[kids.length - 1].getBoundingClientRect();
        const free = g.clientWidth - (last.right - first.left);
        const J = { "flex-start": "start", "start": "start", "normal": "start", "left": "start",
                    "center": "center", "flex-end": "end", "end": "end", "right": "end" };
        const computedAlign = J[cs.justifyContent] || cs.justifyContent;
        if (!anchored && free > 4 && computedAlign !== declAlign)
          out.push(`AS-60 ${where}: action-group alignment '${computedAlign}' contradicts its declared fact '${declAlign}' outside any anchoring context`);
        // PAINTED-EDGE check (fix3 — the blind spot the justify comparison missed):
        // a group whose BOX is displaced off its content column (max-width + auto
        // margins hug-centering it) computes the right justify-content yet paints
        // the whole row off the column edge. Measure the ITEMS' painted edges
        // against the column a reader compares them to — the widest in-flow
        // sibling (the intro/heading stack), else the parent's content box.
        if (!anchored) {
          const sibs = [...g.parentElement.children].filter(
            (el) => el !== g && visible(el) &&
              getComputedStyle(el).position !== "absolute");
          let colL, colR;
          if (sibs.length) {
            const w = sibs.reduce((a, b) =>
              b.getBoundingClientRect().width > a.getBoundingClientRect().width ? b : a);
            const wr = w.getBoundingClientRect();
            colL = wr.left; colR = wr.right;
          } else {
            const pr = g.parentElement.getBoundingClientRect();
            const pcs = getComputedStyle(g.parentElement);
            colL = pr.left + parseFloat(pcs.paddingLeft);
            colR = pr.right - parseFloat(pcs.paddingRight);
          }
          const lg = first.left - colL, rg = colR - last.right;
          const dev = declAlign === "center" ? Math.abs(lg - rg)
            : declAlign === "end" ? Math.abs(rg) : Math.abs(lg);
          if (dev > 4)
            out.push(`AS-60 ${where}: action-group painted ${Math.round(dev)}px off its declared '${declAlign}' column edge (box-level centering over the stamped fact)`);
        }
      }
    };

    // AS-78: circle integrity — semantic round controls are square and icon-only.
    for (const host of document.querySelectorAll(
      '[data-control-shape="round"],[data-shape="circle"],.c-button--round,.btnf-round'
    )) {
      if (!visible(host)) continue;
      const r = host.getBoundingClientRect();
      const tol = Math.max(3, Math.max(r.width, r.height) * 0.06);
      const pill = host.matches('[data-control-shape="pill"],[data-shape="pill"],.is-pill');
      const hasMedia = !!host.querySelector('img,svg,[aria-hidden="true"]');
      const text = realText(host).replace(/[\s←→‹›«»+\-×]/g, "");
      if (!pill && Math.abs(r.width - r.height) > tol)
        out.push(`AS-78 circle: round host is ${Math.round(r.width)}×${Math.round(r.height)}px (must be approximately square)`);
      if (!pill && text && !hasMedia)
        out.push(`AS-78 circle: text-bearing control uses round/circle semantics instead of pill semantics`);
      const cs = getComputedStyle(host);
      const radii = cs.borderTopLeftRadius.split(/\s+/).map(parseFloat).filter(Number.isFinite);
      if (!pill && r.width !== r.height && radii.some(v => v >= Math.min(r.width, r.height) * 0.45))
        out.push(`AS-78 circle: percentage/circular radius paints an ellipse on a non-square host`);
      if (host.matches('.is-focus,:focus-visible')) {
        const before = getComputedStyle(host, "::before");
        const after = getComputedStyle(host, "::after");
        for (const pseudo of [before, after]) {
          if (pseudo.content && pseudo.content !== "none" && pseudo.content !== '""') {
            const pw = parseFloat(pseudo.width), ph = parseFloat(pseudo.height);
            if ((Number.isFinite(pw) && pw > r.width + 6) ||
                (Number.isFinite(ph) && ph > r.height + 6))
              out.push(`AS-78 circle: focus pseudo layer exceeds host geometry`);
          }
        }
        if ((parseFloat(cs.outlineOffset) || 0) > 6)
          out.push(`AS-78 circle: focus ring is not bounded to host geometry`);
      }
    }

    // AS-79: designed toggle/control-family coherence.
    for (const toggle of document.querySelectorAll(
      '[data-control-kind="toggle"],.ex-switch'
    )) {
      if (!visible(toggle)) continue;
      const track = toggle.querySelector('.track,[data-toggle-track]');
      const knob = toggle.querySelector('.knob,[data-toggle-knob]');
      if (!track || !knob || !visible(track) || !visible(knob)) {
        out.push(`AS-79 toggle: missing explicit track/knob anatomy`);
        continue;
      }
      const tr = track.getBoundingClientRect(), kr = knob.getBoundingClientRect();
      const ts = getComputedStyle(track), ks = getComputedStyle(knob);
      const trackRadius = parseFloat(ts.borderTopLeftRadius) || 0;
      const knobRadius = parseFloat(ks.borderTopLeftRadius) || 0;
      if (trackRadius < tr.height / 2 - 1)
        out.push(`AS-79 toggle: track is not a capsule (${Math.round(tr.width)}×${Math.round(tr.height)}px, radius ${Math.round(trackRadius)}px)`);
      if (Math.abs(kr.width - kr.height) > 2 || knobRadius < Math.min(kr.width, kr.height) / 2 - 1)
        out.push(`AS-79 toggle: knob is not a coherent circle`);
      const inset = Math.min(
        Math.abs(kr.left - tr.left), Math.abs(tr.right - kr.right),
        Math.abs(kr.top - tr.top), Math.abs(tr.bottom - kr.bottom));
      if (inset < 1 || inset > tr.height * 0.3)
        out.push(`AS-79 toggle: knob inset ${Math.round(inset)}px is incoherent with track`);
      if (toggle.closest('[data-origin="designed"]') &&
          !getComputedStyle(toggle).getPropertyValue('--radius').trim() &&
          !getComputedStyle(toggle).getPropertyValue('--button-radius').trim())
        out.push(`AS-79 toggle: designed control does not consume brand control-radius facts`);
      if (toggle.matches('.is-focus') && (parseFloat(ts.outlineWidth) || 0) < 1)
        out.push(`AS-79 toggle: focus state has no explicit branded focus treatment`);
    }

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
      // decorative DECLARED-HIDDEN art (empty-alt aria-hidden band/panel washes —
      // the sanctioned art-surface device) is decoration, not content media: same
      // aria-hidden exemption the text inventory below already applies.
      const media = [...sec.querySelectorAll("img,video,svg.c-image")]
        .filter(visible).filter(m => !m.closest(".cs-nav,.c-footer"))
        .filter(m => !m.matches('[aria-hidden="true"]') && !m.closest('[aria-hidden="true"]'));
      // .c-stat cells are PRIMARY content (fix7, pass-3 follow-up 5): a heading +
      // stat band used to read as "heading-only" because the inventory never
      // counted the stat device's value/label pairs.
      const rows = [...sec.querySelectorAll(".c-row, li, details, .c-stat")]
        .filter(visible);
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

      // AS-23: lifecycle-safe image backing. Unresolved/loading and error states need
      // the surface-derived hatch; a successfully loaded image must have NO hatch so
      // transparent pixels reveal the real parent surface. Logos/icons exempt.
      // ART-TAGGED media exempt too (W3, stress-playbook 2026-07): the renderer's
      // fid2 art contract (.c-image--art / .c-acc-media--contain) DELIBERATELY
      // strips the hatch — transparent illustration/product-UI PNGs would show the
      // plate through their alpha. The renderer's tag decision is the shared law;
      // the audit reads the class it stamps instead of re-litigating it.
      for (const im of media.filter(m => m.tagName === "IMG")) {
        const r = im.getBoundingClientRect();
        if (r.width < 80 || r.height < 80) continue;               // logo/icon scale
        if (im.closest(".c-logo--img,.cs-nav,.c-footer")) continue;
        if (im.matches(".c-image--art,.c-acc-media--contain")) continue; // art contract
        const bg = getComputedStyle(im).backgroundImage;
        const state = im.getAttribute("data-load-state");
        const hatched = /repeating-linear-gradient/.test(bg);
        if (state === "loaded" && hatched)
          out.push(`AS-23 ${id}: loaded image retains placeholder backing (src=${(im.getAttribute("src") || "").slice(-40)})`);
        if (state !== "loaded" && !hatched)
          out.push(`AS-23 ${id}: loading/error image without placeholder backing (src=${(im.getAttribute("src") || "").slice(-40)})`);
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

      // AS-14: form present, but no body copy (>=40 chars) BEFORE it in the section.
      // Substantive MARKED-LIST items count as the stated reason too (fix7: a
      // benefit checklist before a capture form states the exchange exactly like
      // a paragraph — the list is the paragraph run's structured form).
      if (forms.length) {
        const firstForm = forms[0];
        const reasons = paras.concat(
          [...sec.querySelectorAll(".c-marked-list li")].filter(visible)
            .filter(li => realText(li).length >= 40));
        const before = reasons.some(p =>
          p.compareDocumentPosition(firstForm) & Node.DOCUMENT_POSITION_FOLLOWING);
        if (!before)
          out.push(`AS-14 ${id}: input/form with no stated reason (no body copy before it)`);
      }

      // AS-64: parallel benefit runs SHOULD be a marked list (fix7 punch 3).
      // HARD arm: a container that DECLARED list intent (data-list-intent — the
      // renderer stamps it when a composition's supportKind said list) yet renders
      // 3+ sibling paragraphs and no marked list dropped the declaration.
      // ADVISORY arm: 3+ consecutive short sibling paragraphs of parallel length
      // anywhere read as an unmarked list — surfaced for review, never an exit flag.
      for (const box of sec.querySelectorAll("[data-list-intent]")) {
        const plainP = [...box.children].filter(
          (el) => el.matches("p.c-paragraph") && visible(el));
        if (!box.querySelector(".c-marked-list") && plainP.length >= 3)
          out.push(`AS-64 ${id}: declared list intent renders ${plainP.length} plain paragraphs and no marked list (dropped device)`);
      }
      for (const box of new Set([...sec.querySelectorAll("p")].map((p) => p.parentElement))) {
        if (!box || box.closest(".cs-nav,.c-footer")) continue;
        const kids = [...box.children].filter(visible);
        let run = 0;
        for (const el of kids) {
          const isShortP = el.matches("p.c-paragraph") && !el.matches(".c-eyebrow,.c-caption")
            && realText(el).length >= 24 && realText(el).length <= 160;
          run = isShortP ? run + 1 : 0;
          if (run === 3) {
            advisories.push(`AS-64 ${id}: 3+ consecutive short sibling paragraphs — parallel benefit phrasing usually wants the marked-list device`);
            break;
          }
        }
      }

      // AS-66: heading fit-to-measure (fix7 punch 5). A column stamped with its
      // fit cap (data-fit-cap — the renderer's own step-down contract) whose
      // heading still renders more lines than the cap means the deterministic
      // fit mechanic failed or was bypassed. Declaration-driven: no stamp, no audit.
      for (const box of sec.querySelectorAll("[data-fit-cap]")) {
        const cap = parseInt(box.getAttribute("data-fit-cap"), 10);
        const h = box.querySelector(".c-heading");
        if (!Number.isFinite(cap) || !h || !visible(h)) continue;
        const cs = getComputedStyle(h);
        const lh = parseFloat(cs.lineHeight) || 1.2 * parseFloat(cs.fontSize);
        const lines = Math.max(1, Math.round(h.getBoundingClientRect().height / lh));
        if (lines > cap)
          out.push(`AS-66 ${id}: heading renders ${lines} lines against its stamped fit cap ${cap} (rung ${box.getAttribute("data-fit-rung") || "display"}) — the register step-down did not fit the measure`);
      }

      // AS-75: component-fit feasibility. The wireframe solver stamps its chosen
      // minimum width, line caps, and family anatomy on repeated collections;
      // rendered geometry must honor the declaration (never squeeze silently).
      for (const group of sec.querySelectorAll('[data-component-fit="collection"]')) {
        const minWidth = parseFloat(group.getAttribute("data-fit-min-item")) || 0;
        const hCap = parseInt(group.getAttribute("data-fit-max-heading-lines"), 10) || 0;
        const bCap = parseInt(group.getAttribute("data-fit-max-body-lines"), 10) || 0;
        const declaredAnatomy = group.getAttribute("data-fit-anatomy") || "";
        const anatomies = new Set();
        for (const item of group.querySelectorAll(":scope > .cs-module")) {
          const r = item.getBoundingClientRect();
          const anatomy = item.getAttribute("data-internal-anatomy") || "";
          if (anatomy) anatomies.add(anatomy);
          if (minWidth && r.width + 1 < minWidth)
            out.push(`AS-75 ${id}: component item ${Math.round(r.width)}px wide below declared ${Math.round(minWidth)}px minimum`);
          for (const [el, cap, role] of [
            [item.querySelector(".c-heading"), hCap, "heading"],
            [item.querySelector(".c-paragraph"), bCap, "body"],
          ]) {
            if (!el || !cap || !visible(el)) continue;
            const cs = getComputedStyle(el);
            const lh = parseFloat(cs.lineHeight) || 1.2 * parseFloat(cs.fontSize);
            const lines = Math.max(1, Math.round(el.getBoundingClientRect().height / lh));
            if (lines > cap)
              out.push(`AS-75 ${id}: component ${role} renders ${lines} lines against ${cap}-line fit cap`);
          }
          if (item.scrollWidth > item.clientWidth + 1)
            out.push(`AS-75 ${id}: component content overflows its item box (likely unbreakable token)`);
        }
        if (anatomies.size > 1 || (declaredAnatomy && anatomies.size &&
            !anatomies.has(declaredAnatomy)))
          out.push(`AS-75 ${id}: sibling component anatomy differs (${[...anatomies].join(", ")}) without a licensed family variant`);
      }

      // AS-77: rendered grid occupancy. A feasible track count may still leave a
      // visible orphan void in its final row. The wireframe must fill that row via
      // explicit item spans, select one column, or license asymmetry with a real
      // painted counterweight; CSS positional selectors cannot invent a repair.
      for (const group of sec.querySelectorAll('[data-component-fit="collection"]')) {
        const columns = parseInt(group.getAttribute("data-fit-columns"), 10) || 1;
        if (columns <= 1) continue;
        const strategy = group.getAttribute("data-fill-strategy") || "";
        const counterweight = group.getAttribute("data-fill-counterweight") || "";
        const items = [...group.querySelectorAll(":scope > .cs-module")].filter(visible);
        const rows = [];
        for (const item of items) {
          const rect = item.getBoundingClientRect();
          let row = rows.find(entry => Math.abs(entry.top - rect.top) <= 2);
          if (!row) {
            row = {top: rect.top, items: []};
            rows.push(row);
          }
          row.items.push({item, rect});
        }
        rows.sort((a, b) => a.top - b.top);
        const last = rows[rows.length - 1];
        if (!last) continue;
        const style = getComputedStyle(group);
        const gap = parseFloat(style.columnGap) || 0;
        const painted = last.items.reduce((sum, entry) => sum + entry.rect.width, 0)
          + gap * Math.max(0, last.items.length - 1);
        const unused = Math.max(0, group.getBoundingClientRect().width - painted);
        const licensed = strategy === "licensed-asymmetry" && counterweight;
        if (unused > 3 && !licensed)
          out.push(`AS-77 ${id}: final component row leaves ${Math.round(unused)}px of unused grid tracks (${strategy || "no fill strategy"})`);
        if (strategy === "licensed-asymmetry" && !counterweight)
          out.push(`AS-77 ${id}: licensed grid asymmetry has no painted balancing counterweight`);
        for (const {item, rect} of last.items) {
          const span = parseInt(item.getAttribute("data-grid-span"), 10) || 1;
          if (span > 1 && rect.width < group.getBoundingClientRect().width - 3 &&
              last.items.length === 1)
            out.push(`AS-77 ${id}: declared ${span}-track item span did not fill its rendered row`);
        }
      }

      // AS-76: testimonial semantic integrity + section balance.
      for (const host of sec.querySelectorAll('[data-testimonial-intent="true"]')) {
        const component = host.querySelector('[data-component-contract="testimonial"]');
        if (!component) {
          out.push(`AS-76 ${id}: testimonial intent rendered without a testimonial component wrapper`);
          continue;
        }
        if (!realText(component.querySelector(".cs-testimonial-quote") || {textContent: ""}) ||
            !realText(component.querySelector(".c-person") || {textContent: ""}))
          out.push(`AS-76 ${id}: testimonial component is missing quote or attribution`);
        if (component.getAttribute("data-testimonial-asset") === "bound" &&
            !component.querySelector("img"))
          out.push(`AS-76 ${id}: compatible testimonial media was bound but silently dropped`);
        const maxEmpty = parseFloat(component.getAttribute("data-testimonial-max-empty")) || 0.68;
        const sr = host.getBoundingClientRect();
        const cr = component.getBoundingClientRect();
        const emptyRatio = sr.height > 0 ? Math.max(0, sr.height - cr.height) / sr.height : 0;
        if (emptyRatio > maxEmpty && !host.hasAttribute("data-monument-archetype"))
          out.push(`AS-76 ${id}: testimonial section empty-space ratio ${emptyRatio.toFixed(2)} exceeds ${maxEmpty.toFixed(2)} without a monument license`);
      }

      // AS-59: multi-action hierarchy — one primary register per action group
      // (in-section groups; the chrome bar's group is audited page-level below).
      for (const g of sec.querySelectorAll('[class*="-actions"], .c-actions')) {
        if (g.closest(".cs-nav")) continue;
        auditActionGroup(g, id);
      }

      // AS-60: stamped action-group facts must be what actually computes.
      for (const g of sec.querySelectorAll("[data-ag-gap], [data-ag-align]"))
        auditActionGroupFacts(g, id);

      // AS-61: typographic-action ink width. A text link's box — and therefore
      // its underline ink (border/pseudo-rules span the box) — must HUG its
      // label + glyph run in every placement. Column flex stacks blockify and
      // stretch inline-flex children by default, so an unhugged link paints its
      // underline to the card/container edge (the registry's content-hugging
      // mechanic, now explicit for text links). Nav links are excluded: their
      // padded hit-target boxes are deliberate chrome geometry.
      for (const a of sec.querySelectorAll(".c-arrow-link")) {
        if (a.closest(".cs-nav")) continue;
        const r = a.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        const range = document.createRange();
        range.selectNodeContents(a);
        const ink = range.getBoundingClientRect();
        if (ink.width > 0 && r.width - ink.width > 12)
          out.push(`AS-61 ${id}: text-link box ${Math.round(r.width)}px vs content run ${Math.round(ink.width)}px — underline ink spans the container, not the label (stretched in a column flex stack)`);
      }
    }

    // AS-59 page-level pass: the chrome bar's action group lives outside sec-* scope.
    for (const g of document.querySelectorAll('.cs-nav [class*="-actions"], .cs-nav .c-actions'))
      auditActionGroup(g, "page-nav");
    return { out, advisories };
  });

  const name = target.split("/").slice(-2).join("/") + ` @${width}px`;
  if (flags.out.length) {
    anyFlag = true;
    console.log(`FLAG ${name}  (${flags.out.length})`);
    for (const f of flags.out) console.log(`  ${f}`);
  } else {
    console.log(`PASS ${name}`);
  }
  for (const a of flags.advisories) console.log(`  ADVISORY ${a}`);
  await page.close();
  }
}
await browser.close();
process.exit(anyFlag ? 1 : 0);
