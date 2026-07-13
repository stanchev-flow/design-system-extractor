#!/usr/bin/env python3
"""compose_replica.py — the REPLICA GATE: mechanized rebuild-as-proof (P0.2).

Assemble the SOURCE HOMEPAGE 1:1 for a brand from its extracted evidence, then
measure how close the rebuild gets — per section, against the source full-page
screenshot. The score is DIAGNOSTIC (a renderer-capability audit), not blocking:
every low-scoring band becomes a named RENDERER-GAP punch-list entry, and the
scores are structured so a threshold could gate later (``--fail-under``).

The lane composes through the REAL machinery — never bespoke markup:

  1. SECTIONS IN SOURCE ORDER: every ``layout-library.yaml`` pattern maps back to
     the source section that evidenced it (``provenance[0]`` names the referencing
     ``brand.yaml`` layout; the layouts are authored in capture order, which the
     evidence section census fixes). Each (layout, pattern) pair is hydrated by
     the components preview's OWN demo builder
     (``render_components_preview._demo_section_for_pattern`` — verbatim authored
     copy from section-copy.yaml + tagged slot assets), adapted by the PROVEN
     composition adapter (``compose_from_composition.composition_to_layout``),
     and composed into ONE page by ``compose_page.build_page`` — which also
     renders the REAL chrome (page-level navbar + closing footer from brand.yaml).
  2. SCREENSHOT with a SCROLL PASS (Playwright): the composed page reveals
     content via IntersectionObserver, so the replica is scrolled end-to-end
     before the full-page shot; per-section rects are measured from the live DOM.
  3. PER-SECTION DIFF vs the source full-page screenshot: source bands come from
     ``evidence/section-rects.json`` (the same rects that drove crop slicing);
     replica bands from step 2. Similarity is a Pillow-only metric (no heavy
     deps): downsampled RGB structure + full-res RGB pixel MAE + band-height
     ratio. Side-by-side crops render per band, plus one combined strip.
  4. ``replica-report.md`` (+ ``.json``): per-section scores, overall score, crop
     references, and the RENDERER-GAP PUNCH LIST — each entry names the missing
     capability in generic vocabulary (marquee animation, accordion open-state,
     carousel statics, mega-menu open panels, composite hero art, …) with the
     measured evidence beside it.

Usage:
    ./venv/bin/python brand_pipeline/compose_replica.py runs/<brand>/brand/brand.yaml
        [-o runs/<brand>/brand/compose/replica] [--viewport 1440x900]
        [--source-shot <fullpage.png>] [--skip-shoot] [--fail-under 0.0]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import compose_from_composition as cfc  # noqa: E402
import compose_page as cp               # noqa: E402
import compose_section as cs            # noqa: E402
import render_components_preview as rp  # noqa: E402
import tokens_css                       # noqa: E402
from styles import inactive_context     # noqa: E402

REPO_ROOT = _HERE.parent

# similarity weights: structure (layout/tonal organization at coarse scale) carries
# the most signal for "did the rebuild draw the same section"; pixel keeps texture/
# color honest; height keeps the band's physical size honest.
W_STRUCTURE, W_PIXEL, W_HEIGHT = 0.5, 0.3, 0.2
PUNCH_THRESHOLD = 0.85          # bands scoring below this get a punch-list entry
STRUCTURE_W = 64                # px width of the coarse structure grid
PIXEL_W = 720                   # px width of the fine pixel comparison

CHROME_IDS = {"navbar", "footer"}


# ── source order: layout-library provenance → brand layouts (capture order) ──────

def source_order_sections(doc: dict, patterns: list[dict]) -> list[tuple[dict, dict]]:
    """(layout, pattern) pairs in SOURCE ORDER. Every pattern's ``provenance[0]``
    names the brand layout extracted from that source section; the brand's
    ``layouts[]`` are authored in capture order (the extraction skill's census
    walk), so ordering by layout position IS the source page order. Fails loud on
    a pattern whose provenance doesn't resolve — a replica with silently dropped
    sections would prove nothing."""
    layouts = [l for l in (doc.get("layouts") or [])
               if isinstance(l, dict) and not _is_chrome(l)]
    by_id = {l.get("id"): i for i, l in enumerate(layouts)}
    pairs: list[tuple[int, dict, dict]] = []
    unmapped: list[str] = []
    for pat in patterns:
        prov = [str(p) for p in (pat.get("provenance") or []) if p]
        lid = next((p for p in prov if p in by_id), None)
        if lid is None:
            # fall back to the first layout whose patternRef points here
            layout = rp.layout_for_pattern(doc, pat.get("id"))
            lid = (layout or {}).get("id")
        if lid is None or lid not in by_id:
            unmapped.append(str(pat.get("id")))
            continue
        pairs.append((by_id[lid], layouts[by_id[lid]], pat))
    if unmapped:
        raise SystemExit(
            f"compose_replica: pattern(s) with no resolvable source section: "
            f"{', '.join(unmapped)} — every layout-library pattern must carry "
            "provenance naming its source layout (or a patternRef back-link).")
    pairs.sort(key=lambda t: t[0])
    return [(layout, pat) for _, layout, pat in pairs]


def _is_chrome(layout: dict) -> bool:
    return (str(layout.get("archetype") or "") == "nav"
            or str(layout.get("id") or "") in CHROME_IDS)


# ── 1) compose the replica page ───────────────────────────────────────────────────

def build_replica_page(brand_yaml: Path, out_dir: Path) -> dict:
    """Compose the full source-order page into ``out_dir/index.html`` via the same
    demo-hydration + composition-adapter path the components preview's pattern
    demos use, then ``compose_page.build_page`` (page nav + closing footer).
    Returns {"order": [...], "sections": [...], "errors": {...}}."""
    doc = cp.load_doc(brand_yaml)
    patterns = rp.load_layout_library(brand_yaml)
    if not patterns:
        raise SystemExit(f"compose_replica: no layout-library patterns beside {brand_yaml}")
    pairs = source_order_sections(doc, patterns)

    brand_dir = brand_yaml.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    hydrate_all = rp._demo_hydration_active(doc)
    comp_sections: list[dict] = []
    adapted_layouts: list[dict] = []
    layout_copy: dict = {}
    errors: dict[str, str] = {}
    for layout, pat in pairs:
        lid = layout.get("id")
        try:
            if hydrate_all or rp._layout_needs_asset_hydration(doc, layout):
                sec = rp._demo_section_for_pattern(doc, pat, layout)
                comp = cfc._sanitize_assets({"sections": [sec]}, brand_dir)
                # the SHARED brand-aware adaptation (fid10 2026-07): one path for
                # both lanes — authored layoutCopy over the composition's copy,
                # brand-layout declarations (eyebrowRegister) ridden through.
                adapted, merged, _ = cfc.adapt_brand_section(comp["sections"][0], doc)
                if merged:
                    layout_copy[adapted["id"]] = merged
                comp_sections.append(sec)
                adapted_layouts.append(adapted)
            else:
                # a layout with its own blockMapping renders directly (no hydration)
                comp_sections.append({"id": lid, "note": "direct (blockMapping)"})
                adapted_layouts.append(layout)
        except Exception as exc:  # record, keep composing the rest — the report names it
            errors[str(lid)] = f"{type(exc).__name__}: {exc}"
    if not adapted_layouts:
        raise SystemExit(f"compose_replica: nothing composed ({errors})")

    order = [l["id"] for l in adapted_layouts]
    page_doc = dict(doc)
    page_doc["layouts"] = adapted_layouts

    style_ctx = inactive_context()
    saved_layout_copy = cs.LAYOUT_COPY
    try:
        cs.LAYOUT_COPY = {**cs.LAYOUT_COPY, **layout_copy}
        cs.prepare_nav_logo(page_doc, brand_dir, out_dir / "assets")
        # REPLICA LANE: honor_curation=False (brand-schema §4.4c). This lane rebuilds
        # the SOURCE 1:1 and its gate scores against the source — a curator's ruling
        # ("follow-grammar") applies to generation lanes only; the measured pattern
        # fact stays this lane's truth.
        html = cp.build_page(page_doc, brand_yaml, order, style_ctx,
                             honor_curation=False)
        (out_dir / "index.html").write_text(html)
        tokens_css.write_manifest(
            out_dir, tokens_css.build_page_tokens(page_doc, style_ctx,
                                                  brand_yaml_path=brand_yaml))
        cs.copy_assets(brand_dir, out_dir / "assets")
        cs.copy_fonts(brand_dir, out_dir / "assets", page_doc)
    finally:
        cs.LAYOUT_COPY = saved_layout_copy

    (out_dir / "composition.json").write_text(json.dumps(
        {"schemaVersion": "replica-composition.v1", "order": order,
         "sections": comp_sections, "errors": errors}, indent=1) + "\n")
    return {"order": order, "doc": page_doc, "errors": errors}


# ── 2) screenshot with a scroll pass + live section rects ─────────────────────────

def shoot_replica(out_dir: Path, viewport: tuple[int, int] = (1440, 900)) -> dict:
    """Full-page screenshot of the composed replica AFTER a scroll pass (so the
    IntersectionObserver reveal choreography fires and settles), plus the live
    per-band rects (#page-nav, every #sec-N). dpr=1 so screenshot px == CSS px."""
    from playwright.sync_api import sync_playwright
    index = out_dir / "index.html"
    shot = out_dir / "replica-fullpage.png"
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]},
                                device_scale_factor=1)
        page.goto(index.resolve().as_uri(), wait_until="load", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass  # webfont CDNs may dribble; "load" + settle below is enough
        page.evaluate("document.fonts && document.fonts.ready")
        page.wait_for_timeout(500)
        # scroll pass: step to the bottom so every IO reveal fires, then back up.
        height = page.evaluate("document.body.scrollHeight")
        step, y = max(400, viewport[1] - 200), 0
        while y < height:
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(120)
            y += step
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(400)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        # Freeze any marquee track at its t=0 resting offset before the shot: the
        # SOURCE capture renders its marquee paused at offset 0 (the JS-set duration
        # never ran under static capture), so pausing ours at the same frame keeps
        # the band diff apples-to-apples. Scoped to the marquee keyframe only —
        # reveal transitions have already settled and are not touched.
        page.evaluate("""document.getAnimations().forEach(a => {
          if (a.animationName === 'cs-marquee-scroll') {
            try { a.currentTime = 0; a.pause(); } catch (e) {}
          }
        })""")
        page.wait_for_timeout(100)
        rects = page.evaluate("""() => {
          const grab = el => { const r = el.getBoundingClientRect();
            return { x: r.x, y: r.y + window.scrollY, w: r.width, h: r.height }; };
          const out = { docHeight: document.body.scrollHeight, bands: [] };
          const nav = document.getElementById('page-nav');
          if (nav) out.bands.push({ id: 'page-nav', kind: 'nav',
                                    layout: 'navbar', rect: grab(nav) });
          document.querySelectorAll('[id^=sec-]').forEach(el => {
            out.bands.push({ id: el.id, kind: 'section',
                             layout: el.getAttribute('data-layout') || el.id,
                             rect: grab(el) });
          });
          return out;
        }""")
        page.screenshot(path=str(shot), full_page=True)
        browser.close()
    rects["schemaVersion"] = "replica-rects.v1"
    (out_dir / "replica-rects.json").write_text(json.dumps(rects, indent=1) + "\n")
    return rects


def shoot_chrome_mega(brand_dir: Path, out_dir: Path,
                      viewport: tuple[int, int] = (1440, 900)) -> Path | None:
    """DIAGNOSTIC (P2): if the brand's chrome preview exists and renders hover/focus
    mega-panels, capture ONE open-panel state into ``diff/chrome-mega-open.png``.
    Not scored — the source full-page shot has no open panel to diff against; this
    exercises the open-panel capability the closed-bar diff can't see. Returns the
    shot path, or None when the preview / panel markup is absent (degrade, never
    fails the gate)."""
    chrome_index = brand_dir / "chrome" / "index.html"
    if not chrome_index.is_file():
        return None
    try:
        if "mega-panel" not in chrome_index.read_text(errors="replace"):
            return None
        from playwright.sync_api import sync_playwright
        shot = out_dir / "diff" / "chrome-mega-open.png"
        shot.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": viewport[0],
                                              "height": viewport[1]},
                                    device_scale_factor=1)
            page.goto(chrome_index.resolve().as_uri(), wait_until="load",
                      timeout=30000)
            page.wait_for_timeout(400)
            tab = page.locator(".nav-tab.has-menu").first
            if tab.count() == 0:
                browser.close()
                return None
            tab.hover()
            page.wait_for_timeout(300)
            page.screenshot(path=str(shot))  # viewport shot: bar + open panel
            browser.close()
        return shot
    except Exception as exc:  # diagnostic only — never take the gate down
        print(f"[replica] chrome mega-menu shot skipped: {type(exc).__name__}: {exc}")
        return None


# ── 3) per-section diff vs the source screenshot ──────────────────────────────────

def load_source_bands(brand_dir: Path) -> tuple[Path, list[dict]]:
    """(source screenshot path, bands) from the extraction evidence. Bands are the
    measured section rects in y order, with the chrome header/footer as their own
    nav/footer bands — the same coordinate space as the source full-page PNG."""
    rects_p = brand_dir / "evidence" / "section-rects.json"
    if not rects_p.is_file():
        raise SystemExit(f"compose_replica: {rects_p} missing — run the measure stage")
    rects = json.loads(rects_p.read_text())
    manifest_p = brand_dir / "evidence" / "crops" / "crops-manifest.json"
    shot = None
    if manifest_p.is_file():
        rel = (json.loads(manifest_p.read_text()) or {}).get("screenshot")
        if rel:
            cand = (REPO_ROOT / rel).resolve()
            shot = cand if cand.is_file() else None
    bands: list[dict] = []
    for c in rects.get("chrome") or []:
        if c.get("name") == "header":
            bands.append({"id": "page-nav", "kind": "nav", "layout": "navbar",
                          "rect": c["rect"]})
    for s in rects.get("sections") or []:
        bands.append({"id": f"src-{s['index']}", "kind": "section",
                      "layout": s.get("heading") or f"section-{s['index']}",
                      "index": s["index"], "rect": s["rect"]})
    for c in rects.get("chrome") or []:
        if c.get("name") == "footer":
            bands.append({"id": "footer", "kind": "footer", "layout": "footer",
                          "rect": c["rect"]})
    return shot, bands


def _crop_band(im, rect) -> "object":
    from PIL import Image  # noqa: F401 (typing only)
    w, h = im.size
    y0 = max(0, int(round(rect["y"])))
    y1 = min(h, int(round(rect["y"] + rect["h"])))
    x0 = max(0, int(round(rect.get("x", 0))))
    x1 = min(w, int(round(rect.get("x", 0) + rect.get("w", w))))
    if y1 <= y0 or x1 <= x0:
        return None
    return im.crop((x0, y0, x1, y1))


def band_similarity(src_im, rep_im) -> dict:
    """Pillow-only similarity between two band crops:
      structure — 1 - MAE/255 over a coarse RGB grid (both resized to the same
                  STRUCTURE_W-wide thumbnail): layout + tonal organization.
      pixel     — 1 - MAE/255 over the same-size PIXEL_W-wide RGB render.
      height    — min(h)/max(h) of the two band heights (physical size honesty).
      score     — W_STRUCTURE*structure + W_PIXEL*pixel + W_HEIGHT*height."""
    from PIL import Image, ImageChops, ImageStat

    def _mae(a, b, width: int) -> float:
        ah = max(4, round(width * a.height / a.width))
        base = a.convert("RGB").resize((width, ah), Image.LANCZOS)
        other = b.convert("RGB").resize((width, ah), Image.LANCZOS)
        diff = ImageChops.difference(base, other)
        return sum(ImageStat.Stat(diff).mean) / 3.0

    structure = 1.0 - _mae(src_im, rep_im, STRUCTURE_W) / 255.0
    pixel = 1.0 - _mae(src_im, rep_im, PIXEL_W) / 255.0
    hs, hr = src_im.height, rep_im.height
    height = (min(hs, hr) / max(hs, hr)) if max(hs, hr) else 0.0
    score = W_STRUCTURE * structure + W_PIXEL * pixel + W_HEIGHT * height
    # WIDTH FIDELITY (fid6 2026-07, diagnostic — NOT folded into `score`, so scores
    # stay comparable across runs): ratio of the two bands' detected CONTENT spans.
    # Catches the failure the averaged-MAE metric is nearly blind to: a centered
    # stack collapsed to a fraction of the content width still leaves most of the
    # band as matching background, so structure/pixel barely move (the partner band
    # scored 0.982 while visibly collapsed to ~40% of the source's content span).
    ws = _content_span(src_im)
    wr = _content_span(rep_im)
    width_fid = (min(ws, wr) / max(ws, wr)) if max(ws, wr) > 0 else 1.0
    return {"structure": round(structure, 4), "pixel": round(pixel, 4),
            "height": round(height, 4), "score": round(score, 4),
            "widthFidelity": round(width_fid, 4),
            "srcContentFrac": round(ws, 4), "replicaContentFrac": round(wr, 4),
            "srcHeight": hs, "replicaHeight": hr}


def _content_span(im, sample_w: int = 320, threshold: float = 8.0) -> float:
    """FRACTION of the band width occupied by content: columns of the downsampled
    grayscale crop whose mean deviates from the band's background (estimated from
    the outermost columns — section content is inset from the page edges) by more
    than ``threshold`` gray levels. 0.0 when the band reads empty/uniform."""
    from PIL import Image
    g = im.convert("L")
    h = max(4, round(sample_w * g.height / g.width))
    g = g.resize((sample_w, h), Image.LANCZOS)
    px = g.tobytes()  # mode L: one byte per pixel, row-major
    col_means = [sum(px[x::sample_w]) / h for x in range(sample_w)]
    edge = col_means[:6] + col_means[-6:]
    bg = sorted(edge)[len(edge) // 2]
    content = [x for x, m in enumerate(col_means) if abs(m - bg) > threshold]
    if not content:
        return 0.0
    return (content[-1] - content[0] + 1) / sample_w


def side_by_side(src_im, rep_im, out_path: Path, label: str) -> None:
    """SOURCE | REPLICA side-by-side crop for one band, with a small header bar."""
    from PIL import Image, ImageDraw
    half_w = 640
    def _fit(im):
        h = max(1, round(half_w * im.height / im.width))
        return im.convert("RGB").resize((half_w, h), Image.LANCZOS)
    a, b = _fit(src_im), _fit(rep_im)
    bar, gap = 28, 4
    canvas = Image.new("RGB", (half_w * 2 + gap, bar + max(a.height, b.height)),
                       (24, 24, 26))
    d = ImageDraw.Draw(canvas)
    d.text((8, 7), f"SOURCE — {label}", fill=(235, 235, 235))
    d.text((half_w + gap + 8, 7), "REPLICA", fill=(235, 235, 235))
    canvas.paste(a, (0, bar))
    canvas.paste(b, (half_w + gap, bar))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)


def build_strip(pair_paths: list[Path], out_path: Path, width: int = 1200) -> None:
    """One combined vertical strip of every side-by-side pair (report hero image)."""
    from PIL import Image
    ims = [Image.open(p).convert("RGB") for p in pair_paths if p.is_file()]
    if not ims:
        return
    scaled = []
    for im in ims:
        h = max(1, round(width * im.height / im.width))
        scaled.append(im.resize((width, h), Image.LANCZOS))
    gap = 6
    total_h = sum(im.height for im in scaled) + gap * (len(scaled) - 1)
    canvas = Image.new("RGB", (width, total_h), (24, 24, 26))
    y = 0
    for im in scaled:
        canvas.paste(im, (0, y))
        y += im.height + gap
    canvas.save(out_path)


# ── 4) renderer-gap punch list + report ────────────────────────────────────────────

def _known_gaps(doc: dict, layout: dict | None, pat: dict | None,
                replica_html: str = "") -> list[str]:
    """Named capability gaps this band is EXPECTED to show in a static rebuild —
    detected from the brand's own evidence (generic capability vocabulary; the
    per-run measurements ride in the report rows, not here). RESOLUTION-AWARE (P2):
    a capability whose device markup is present in the composed page no longer
    reports as a gap — the punch list names only what the renderer still can't do."""
    probe = " ".join([
        str((layout or {}).get("useCase") or ""), str((layout or {}).get("id") or ""),
        str((pat or {}).get("id") or ""), str((pat or {}).get("useCase") or ""),
        json.dumps((pat or {}).get("specialTreatments") or []),
    ]).lower()
    gaps: list[str] = []
    if ("marquee" in probe or "auto-scroll" in probe) \
            and "cs-marquee-track" not in replica_html:
        gaps.append("marquee animation — the source strip is a continuously "
                     "translating track (JS-timed; see motion-audit jsTimingNotes); "
                     "the composer renders a static spaced row")
    if "accordion" in probe and not ("c-acc-item" in replica_html
                                     and " open>" in replica_html):
        gaps.append("accordion open-state — the source renders one ACTIVE item "
                     "expanded on its inverted inset panel; the composed accordion "
                     "draws all rows idle/closed")
    if ("carousel" in probe or "edge cards cut" in probe or "viewport" in probe) \
            and "cs-modules--edgecut" not in replica_html:
        gaps.append("carousel statics — the source is an edge-cut sliding track "
                     "(cards clipped at the viewport); the composer renders a "
                     "contained grid")
    if "video" in probe or "play" in probe:
        gaps.append("video static — the source embeds motion media; the composer "
                     "renders a still")
    if "hero" in probe and ("floating" in probe or "illustration" in probe
                            or "globe" in probe or "cards" in probe):
        gaps.append("composite hero art — the source layers an illustration with "
                     "floating product-UI chips; the composer binds one asset per "
                     "media slot (no multi-layer collage of tagged crops)")
    return gaps


def _chrome_gaps(doc: dict, brand_dir: Path, replica_html: str) -> list[dict]:
    """Global/chrome capability gaps detected from brand data vs the composed page."""
    out: list[dict] = []
    nav = doc.get("navbar") or {}
    if any(isinstance(i, dict) and i.get("menu") for i in (nav.get("primary") or [])):
        mega_shot = brand_dir / "compose" / "replica" / "diff" / "chrome-mega-open.png"
        note = ("the brand declares mega-menu columns; the replica (and the source "
                "shot) render the closed bar only — open-panel fidelity is "
                "unexercised by this gate")
        if mega_shot.is_file():
            note += (" (diagnostic open-panel capture from the chrome preview: "
                     "diff/chrome-mega-open.png)")
        out.append({"section": "navbar", "capability": "mega-menu open panels",
                    "note": note})
    ub = nav.get("utilityBanner")
    # honest-absence marker (validator C21 convention): utilityBanner.notObserved
    # declares the source shows NO banner — nothing for the replica to render.
    if isinstance(ub, dict) and ub and not ub.get("notObserved"):
        # compare against the ESCAPED text too — the page HTML-escapes the copy, so
        # a probe carrying quotes/ampersands would false-positive (fid15).
        probe = str(ub.get("text") or ub.get("copy") or "")[:40]
        esc_probe = cp.cr.esc(probe)
        if not probe or (probe not in replica_html
                         and esc_probe not in replica_html):
            out.append({"section": "navbar", "capability": "utility banner",
                        "note": "the source carries a promo/utility banner above the "
                                "nav; the composed page-level chrome does not render it"})
    # display face self-hosting: a display family that is neither a local font file
    # nor a Google-loadable family renders in a fallback stack.
    fam = str((tokens_css.type_role(doc, "display-hero") or {}).get("family") or "")
    if fam:
        fonts_dir = brand_dir / "assets" / "fonts"
        # match space-insensitively: files ship PostScript-style stems
        # ("HubSpotSerif-Book") while the family is spaced ("HubSpot Serif").
        fam_key = fam.lower().replace(" ", "")
        local = fonts_dir.is_dir() and any(
            fam_key in f.stem.lower().replace(" ", "")
            for f in fonts_dir.glob("*.woff2"))
        if fam not in cs.loadable_proxies(doc) and not local:
            out.append({"section": "page", "capability": f"display font ({fam})",
                        "note": "not self-hosted and not Google-loadable — headings "
                                "render in the declared fallback stack; extract the "
                                "woff2 files into assets/fonts/"})
    return out


def build_report(out_dir: Path, rows: list[dict], punch: list[dict],
                 overall: float, meta: dict) -> None:
    lines = [
        "# Replica gate — rebuild-as-proof report", "",
        f"- brand: **{meta.get('brand')}**",
        f"- source screenshot: `{meta.get('sourceShot')}`",
        f"- replica page: `index.html` → `replica-fullpage.png` "
        f"(doc {meta.get('replicaHeight')}px vs source {meta.get('sourceHeight')}px)",
        f"- metric: score = {W_STRUCTURE}·structure + {W_PIXEL}·pixel + "
        f"{W_HEIGHT}·height (Pillow RGB MAE; structure at {STRUCTURE_W}px, "
        f"pixel at {PIXEL_W}px)",
        "- `width` = content-span ratio (diagnostic, not in score): detected content "
        "width fraction of each band, min/max ratio — catches centered stacks "
        "collapsed to a fraction of the source's content width, which the averaged "
        "pixel metric barely registers",
        f"- **overall score (height-weighted): {overall:.3f}**", "",
        "| band | source section | score | structure | pixel | height | width | src h | replica h | crops |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        crop = f"[side-by-side]({r['pair']})" if r.get("pair") else "—"
        wf = r.get("widthFidelity")
        wf_cell = f"{wf:.3f}" if isinstance(wf, (int, float)) else "—"
        lines.append(
            f"| {r['id']} | {r['label']} | **{r['score']:.3f}** | {r['structure']:.3f} "
            f"| {r['pixel']:.3f} | {r['height']:.3f} | {wf_cell} | {r['srcHeight']}px "
            f"| {r['replicaHeight']}px | {crop} |")
    lines += ["", f"![strip](diff/strip.png)", "", "## Renderer-gap punch list", ""]
    if punch:
        for i, p in enumerate(punch, 1):
            score = f" (score {p['score']:.3f})" if p.get("score") is not None else ""
            lines.append(f"{i}. **{p['section']} — {p['capability']}**{score}: {p['note']}")
    else:
        lines.append("_no gaps above threshold_")
    lines += ["", "Diagnostic, not blocking — re-run with `--fail-under <score>` to gate.", ""]
    (out_dir / "replica-report.md").write_text("\n".join(lines))
    (out_dir / "replica-report.json").write_text(json.dumps(
        {"schemaVersion": "replica-report.v1", "overall": overall, "bands": rows,
         "punchList": punch, **meta}, indent=1) + "\n")


def run_diff(brand_dir: Path, out_dir: Path, doc: dict,
             pairs: list[tuple[dict, dict]], replica_rects: dict,
             source_shot: Path | None) -> tuple[list[dict], list[dict], float, dict]:
    from PIL import Image
    src_shot_path, src_bands = load_source_bands(brand_dir)
    src_shot_path = source_shot or src_shot_path
    if not src_shot_path or not Path(src_shot_path).is_file():
        raise SystemExit("compose_replica: source full-page screenshot not found — "
                         "pass --source-shot")
    src_im = Image.open(src_shot_path)
    rep_im = Image.open(out_dir / "replica-fullpage.png")

    # replica bands by kind/order: nav, sections (sec-0..N-1), footer (last sec-N)
    rbands = replica_rects.get("bands") or []
    r_nav = next((b for b in rbands if b["kind"] == "nav"), None)
    r_secs = [b for b in rbands if b["kind"] == "section"]
    r_secs.sort(key=lambda b: int(re.sub(r"\D", "", b["id"]) or 0))
    r_foot = r_secs[-1] if r_secs and r_secs[-1].get("layout") == "closing-bookend" else None
    r_content = r_secs[:-1] if r_foot else r_secs

    s_nav = next((b for b in src_bands if b["kind"] == "nav"), None)
    s_secs = [b for b in src_bands if b["kind"] == "section"]
    s_foot = next((b for b in src_bands if b["kind"] == "footer"), None)

    layout_by_pos = [layout.get("id") for layout, _ in pairs]
    matched: list[tuple[str, str, dict | None, dict | None]] = []
    matched.append(("page-nav", "navbar (chrome header)", s_nav, r_nav))
    for i, s in enumerate(s_secs):
        lid = layout_by_pos[i] if i < len(layout_by_pos) else f"(unmapped-{i})"
        r = next((b for b in r_content if b.get("layout") == lid),
                 r_content[i] if i < len(r_content) else None)
        matched.append((f"sec-{i}", f"{lid} — {s.get('layout') or ''}".strip(" —"), s, r))
    matched.append(("footer", "footer (closing bookend)", s_foot, r_foot))

    rows, pair_paths = [], []
    diff_dir = out_dir / "diff"
    diff_dir.mkdir(parents=True, exist_ok=True)
    for bid, label, s, r in matched:
        if not s or not r:
            rows.append({"id": bid, "label": label, "score": 0.0, "structure": 0.0,
                         "pixel": 0.0, "height": 0.0,
                         "srcHeight": int((s or {}).get("rect", {}).get("h", 0)),
                         "replicaHeight": int((r or {}).get("rect", {}).get("h", 0)),
                         "pair": None,
                         "note": "band missing on one side"})
            continue
        sc = _crop_band(src_im, s["rect"])
        rc = _crop_band(rep_im, r["rect"])
        if sc is None or rc is None:
            rows.append({"id": bid, "label": label, "score": 0.0, "structure": 0.0,
                         "pixel": 0.0, "height": 0.0, "srcHeight": 0,
                         "replicaHeight": 0, "pair": None, "note": "empty crop"})
            continue
        m = band_similarity(sc, rc)
        pair_p = diff_dir / f"{bid}.png"
        side_by_side(sc, rc, pair_p, label)
        pair_paths.append(pair_p)
        rows.append({"id": bid, "label": label, **m,
                     "pair": str(pair_p.relative_to(out_dir))})
    build_strip(pair_paths, diff_dir / "strip.png")

    total_h = sum(r["srcHeight"] for r in rows) or 1
    overall = round(sum(r["score"] * r["srcHeight"] for r in rows) / total_h, 4)

    # punch list: known capability gaps (evidence-detected) + low-scoring bands
    layout_by_id = {layout.get("id"): (layout, pat) for layout, pat in pairs}
    punch: list[dict] = []
    replica_html = (out_dir / "index.html").read_text(errors="replace")
    for row in rows:
        lid = row["label"].split(" — ")[0]
        layout, pat = layout_by_id.get(lid, (None, None))
        gaps = _known_gaps(doc, layout, pat, replica_html) if layout else []
        low = row["score"] < PUNCH_THRESHOLD
        for g in gaps:
            cap = g.split(" — ")[0]
            punch.append({"section": lid if layout else row["id"], "capability": cap,
                          "score": row["score"], "note": g})
        # WIDTH-COLLAPSE flag (fid6 2026-07): a band whose content span diverges
        # hard from the source gets its own punch entry even when the averaged
        # score looks healthy (the metric blind spot the partner band exposed).
        wf = row.get("widthFidelity")
        if isinstance(wf, (int, float)) and wf < 0.72 \
                and row["id"] not in ("page-nav", "footer"):
            punch.append({
                "section": lid if layout else row["id"],
                "capability": "content width diverges",
                "score": row["score"],
                "note": (f"content span {row.get('replicaContentFrac', 0):.2f} of band "
                         f"vs source {row.get('srcContentFrac', 0):.2f} "
                         f"(width fidelity {wf:.2f}) — check hug/measure collapse "
                         f"or over-wide container")})
        if low and not gaps and row["id"] not in ("page-nav", "footer"):
            drivers = []
            if row["height"] < 0.8:
                direction = "taller" if row["replicaHeight"] > row["srcHeight"] else "shorter"
                drivers.append(f"band renders {direction} "
                               f"({row['replicaHeight']}px vs {row['srcHeight']}px)")
            if row["structure"] < 0.8:
                drivers.append("coarse layout structure diverges (module geometry / "
                               "art direction)")
            if row["pixel"] < 0.7:
                drivers.append("surface color / texture diverges")
            punch.append({"section": lid if layout else row["id"],
                          "capability": "fidelity below threshold",
                          "score": row["score"],
                          "note": "; ".join(drivers) or "inspect the side-by-side crop"})
        elif low and gaps:
            pass  # the named capability entries already cover this band
    for g in _chrome_gaps(doc, brand_dir, replica_html):
        row = next((r for r in rows if r["id"] in ("page-nav",)
                    and g["section"] == "navbar"), None)
        punch.append({**g, "score": (row or {}).get("score")})

    meta = {"sourceShot": str(src_shot_path),
            "sourceHeight": src_im.height, "replicaHeight": rep_im.height}
    return rows, punch, overall, meta


# ── CLI ────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("brand_yaml", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None,
                    help="lane dir (default: <brand_dir>/compose/replica)")
    ap.add_argument("--viewport", default="1440x900")
    ap.add_argument("--source-shot", type=Path, default=None,
                    help="source full-page png (default: crops-manifest.screenshot)")
    ap.add_argument("--skip-shoot", action="store_true",
                    help="compose only (no screenshot / diff)")
    ap.add_argument("--fail-under", type=float, default=None,
                    help="exit 1 when the overall score is below this (gate mode)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    brand_yaml = args.brand_yaml.resolve()
    brand_dir = brand_yaml.parent
    out_dir = (args.out or (brand_dir / "compose" / "replica")).resolve()
    w, h = (int(x) for x in args.viewport.lower().split("x"))

    built = build_replica_page(brand_yaml, out_dir)
    print(f"[replica] composed {len(built['order'])} sections -> {out_dir / 'index.html'}")
    if built["errors"]:
        for lid, err in built["errors"].items():
            print(f"[replica] SECTION FAILED: {lid}: {err}")
    if args.skip_shoot:
        return 0

    rects = shoot_replica(out_dir, (w, h))
    print(f"[replica] screenshot + {len(rects.get('bands') or [])} live bands -> "
          f"replica-fullpage.png")

    mega_shot = shoot_chrome_mega(brand_dir, out_dir, (w, h))
    if mega_shot:
        print(f"[replica] chrome mega-menu open-panel diagnostic -> "
              f"{mega_shot.relative_to(out_dir)}")

    doc = built["doc"]
    patterns = rp.load_layout_library(brand_yaml)
    pairs = source_order_sections(cp.load_doc(brand_yaml), patterns)
    rows, punch, overall, meta = run_diff(brand_dir, out_dir, doc, pairs, rects,
                                          args.source_shot)
    meta["brand"] = (doc.get("brand") or {}).get("name")
    for lid, err in built["errors"].items():
        punch.insert(0, {"section": lid, "capability": "section failed to compose",
                         "score": 0.0, "note": err})
    build_report(out_dir, rows, punch, overall, meta)
    print(f"[replica] overall score {overall:.3f}; {len(punch)} punch-list entries -> "
          f"replica-report.md")
    if args.fail_under is not None and overall < args.fail_under:
        print(f"[replica] FAIL: overall {overall:.3f} < --fail-under {args.fail_under}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
