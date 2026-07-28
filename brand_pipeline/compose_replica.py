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
from artifact_digest import projection_input_digest  # noqa: E402
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

def _provenance_list(layout: dict | None, pat: dict | None) -> list[str]:
    """Prefer pattern provenance; fall back to the brand layout's own list."""
    for src in (pat, layout):
        if not isinstance(src, dict):
            continue
        prov = [str(p) for p in (src.get("provenance") or []) if p]
        if prov:
            return prov
    return []


def _declared_pages(layout: dict | None, pat: dict | None) -> set[str]:
    """The capture pages a section DECLARES it came from (``sourcePages``)."""
    pages: set[str] = set()
    for src in (pat, layout):
        if isinstance(src, dict):
            pages |= {str(p).strip().lower()
                      for p in (src.get("sourcePages") or []) if str(p).strip()}
    return pages


def _provenance_page_key(token: str) -> str | None:
    """``home-section-03-…`` / ``talent-sourcing-section-07`` → page key.

    The fallback for artifacts authored before ``sourcePages`` was declared.
    """
    t = str(token or "").strip().lower()
    if not t or t in {"footer", "chrome.footer"} or t.endswith("-footer"):
        return None
    if "-section-" in t:
        return t.split("-section-", 1)[0]
    return None


def brand_source_pages(doc: dict, patterns: list[dict]) -> list[str]:
    """Every capture page this brand's sections declare — the page-lane keys."""
    pages: set[str] = set()
    for node in list(doc.get("layouts") or []) + list(patterns or []):
        if isinstance(node, dict):
            pages |= _declared_pages(node, None)
    return sorted(pages)


def _provenance_section_index(token: str) -> int:
    """``home-section-03-div`` → 3; unknown → large sentinel for stable sort."""
    import re
    m = re.search(r"-section-(\d+)", str(token or "").lower())
    return int(m.group(1)) if m else 10_000


def source_order_sections(
    doc: dict,
    patterns: list[dict],
    *,
    page: str | None = None,
) -> list[tuple[dict, dict]]:
    """(layout, pattern) pairs in SOURCE ORDER.

    For single-page brands, ``layouts[]`` capture order matches the page. For
    MULTI-PAGE brands the union includes other pages (e.g. stats from
    talent-sourcing) — pass ``page='home'`` when the replica target is the
    homepage screenshot so off-page patterns are excluded and remaining
    sections sort by provenance section index, not authored-array order.
    """
    layouts = [l for l in (doc.get("layouts") or [])
               if isinstance(l, dict) and not _is_chrome(l)]
    by_id = {l.get("id"): i for i, l in enumerate(layouts)}
    page_key = (page or "").strip().lower() or None
    pairs: list[tuple[int, int, dict, dict]] = []
    unmapped: list[str] = []
    skipped_other_page: list[str] = []
    for pat in patterns:
        layout = rp.layout_for_pattern(doc, pat.get("id"))
        prov = _provenance_list(layout if isinstance(layout, dict) else None, pat)
        # Footer chrome is rendered once by compose_page from the measured
        # ``footer`` contract. Some authoring lanes also project the footer crop
        # into a layout-library pattern; treating that pattern as an ordinary
        # section duplicates the closing bookend and shifts every band pairing.
        if any(p.lower() in {"footer", "chrome.footer"} or
               p.lower().endswith("-footer") for p in prov):
            continue
        if page_key:
            pages = _declared_pages(layout if isinstance(layout, dict) else None, pat)
            if not pages:
                pages = {p for p in (_provenance_page_key(t) for t in prov) if p}
            if pages and page_key not in pages:
                skipped_other_page.append(str(pat.get("id")))
                continue
        lid = next((p for p in prov if p in by_id), None)
        if lid is None:
            if not isinstance(layout, dict):
                layout = rp.layout_for_pattern(doc, pat.get("id"))
            lid = (layout or {}).get("id")
        if lid is None or lid not in by_id:
            unmapped.append(str(pat.get("id")))
            continue
        layout = layouts[by_id[lid]]
        sec_i = min((_provenance_section_index(p) for p in prov), default=10_000)
        order_key = sec_i if page_key else by_id[lid]
        pairs.append((order_key, by_id[lid], layout, pat))
    if unmapped and not page_key:
        raise SystemExit(
            f"compose_replica: pattern(s) with no resolvable source section: "
            f"{', '.join(unmapped)} — every layout-library pattern must carry "
            "provenance naming its source layout (or a patternRef back-link).")
    if page_key and skipped_other_page:
        print(f"[replica] page={page_key}: skipped off-page patterns: "
              f"{', '.join(skipped_other_page)}")
    if page_key and not pairs:
        raise SystemExit(
            f"compose_replica: page={page_key!r} matched no patterns — check "
            "layout/pattern provenance (expected tokens like 'home-section-00').")
    pairs.sort(key=lambda t: (t[0], t[1]))
    return [(layout, pat) for _, _, layout, pat in pairs]


def _is_chrome(layout: dict) -> bool:
    return (str(layout.get("archetype") or "") == "nav"
            or str(layout.get("id") or "") in CHROME_IDS)


# ── pairing census: the composed page and the scoring pair list must agree ────────

class PairingCensusError(RuntimeError):
    """The sections that were COMPOSED and the sections being SCORED diverge.

    Raised loudly on purpose. The band diff pairs source section *i* against the
    *i*-th entry of the scoring pair list, so any divergence between the list
    that drove composition and the list that drives scoring silently compares
    unrelated bands and still produces a plausible-looking overall number. A
    wrong score that looks reasonable is worse than a crash.
    """


def assert_pairing_census(composed_order: list[str],
                          pairs: list[tuple[dict, dict]]) -> None:
    """Fail loudly unless the scoring pair list IS the composed section list.

    ``composed_order`` is what ``build_replica_page`` actually rendered (in DOM
    order); ``pairs`` is what the diff will score against the source bands.
    Identity is checked, not just cardinality: an equal-length list drawn from a
    different filter is exactly the failure mode that reads as a real score.
    """
    scored_order = [str((layout or {}).get("id")) for layout, _ in pairs]
    composed = [str(x) for x in (composed_order or [])]
    if composed == scored_order:
        return
    detail = [
        f"composed {len(composed)} section(s): {composed}",
        f"scoring   {len(scored_order)} section(s): {scored_order}",
    ]
    if len(composed) != len(scored_order):
        detail.append(
            "COUNT DIVERGENCE — the diff pairs source band i against scoring "
            "entry i, so every band from the first mismatch onward is scored "
            "against the wrong replica section.")
    only_scored = [x for x in scored_order if x not in set(composed)]
    only_composed = [x for x in composed if x not in set(scored_order)]
    if only_scored:
        detail.append(f"scored but never composed: {only_scored} "
                      "(these have no replica band; the diff will fall back to a "
                      "positional band that belongs to a different section)")
    if only_composed:
        detail.append(f"composed but never scored: {only_composed}")
    raise PairingCensusError(
        "compose_replica: composed-section census != scoring-pair census. "
        + " | ".join(detail)
        + " | Both lists must come from the same source_order_sections() call "
          "with the same `page` filter.")


# ── source-band alignment: authored provenance → measured section rect ────────────

def _page_evidence_dir(brand_dir: Path, page: str | None) -> Path:
    """The per-page evidence dir when the capture set has one, else the root."""
    if page:
        cand = brand_dir / "evidence" / "pages" / page
        if cand.is_dir():
            return cand
    return brand_dir / "evidence"


def _load_crops_manifest(brand_dir: Path, page: str | None) -> dict | None:
    p = _page_evidence_dir(brand_dir, page) / "crops" / "crops-manifest.json"
    if not p.is_file():
        p = brand_dir / "evidence" / "crops" / "crops-manifest.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def crop_index_to_band(crops: dict, s_secs: list[dict],
                       viewport_w: int | None = None) -> dict[int, int]:
    """Map each CROP ordinal to the measured section band it covers.

    Crop ordinals and section-rect ordinals are NOT the same index space: the
    slicer prepends measured page chrome as its own crop and drops rects below
    its minimum-height floor, so the two sequences drift apart on any page whose
    measured bands and sliced crops disagree about what counts as a section.
    The crops manifest records each crop's y-range in SOURCE SCREENSHOT space —
    the same space the section rects live in — so vertical overlap is the only
    trustworthy link between an authored section index and a scorable band.

    Returns {crop index: index into ``s_secs``} for crops that cover exactly one
    band best; a crop whose strongest overlap is negligible is left unmapped.
    """
    img_w = ((crops.get("imageSize") or {}).get("w")) or viewport_w or 0
    scale = (img_w / viewport_w) if (img_w and viewport_w) else 1.0
    spans = []
    for i, s in enumerate(s_secs):
        r = s.get("rect") or {}
        y0 = float(r.get("y", 0)) * scale
        spans.append((i, y0, y0 + float(r.get("h", 0)) * scale))
    out: dict[int, int] = {}
    for c in crops.get("crops") or []:
        try:
            ci = int(c.get("index"))
            cy0, cy1 = float(c.get("yTop")), float(c.get("yBottom"))
        except (TypeError, ValueError):
            continue
        best, best_ov = None, 0.0
        for i, y0, y1 in spans:
            ov = min(cy1, y1) - max(cy0, y0)
            if ov > best_ov:
                best, best_ov = i, ov
        # a crop must cover most of the band it claims: the slicer pads every
        # crop by a fixed margin, so a neighbour always overlaps a little.
        if best is None:
            continue
        _, y0, y1 = spans[best]
        if best_ov <= 0 or best_ov < 0.5 * max(1.0, y1 - y0):
            continue
        out[ci] = best
    return out


def align_source_bands(brand_dir: Path, pairs: list[tuple[dict, dict]],
                       s_secs: list[dict], *, page: str | None = None,
                       viewport_w: int | None = None) -> tuple[list[int | None], dict]:
    """Which measured source band each scoring pair rebuilds.

    Returns ``(aligned, census)`` where ``aligned[i]`` indexes ``s_secs`` for
    ``pairs[i]`` (or None when that pair cannot be anchored).

    PROVENANCE-ANCHORED when every pair carries a resolvable source-section
    ordinal and those ordinals resolve to distinct bands through the crops
    manifest. That is the only mode that survives a capture whose crop ordinals
    and measured-band ordinals differ, and it is what makes an unauthored source
    band visible as unauthored instead of shifting every later pairing by one.

    POSITIONAL otherwise (authoring lanes that name sections rather than
    numbering them): pair *i* takes band *i*, the historical behaviour.
    """
    census: dict = {"mode": "positional", "notes": []}
    n = len(pairs)
    crops = _load_crops_manifest(brand_dir, page)
    if crops:
        idx_by_crop = crop_index_to_band(crops, s_secs, viewport_w)
        ordinals: list[int | None] = []
        for layout, pat in pairs:
            prov = _provenance_list(layout, pat)
            got = [_provenance_section_index(t) for t in prov]
            got = [g for g in got if g < 10_000]
            ordinals.append(min(got) if got else None)
        resolved = [idx_by_crop.get(o) if o is not None else None for o in ordinals]
        anchored = [r for r in resolved if r is not None]
        if len(anchored) == n and len(set(anchored)) == n:
            census["mode"] = "provenance-anchored"
            census["sectionOrdinals"] = ordinals
            unauthored = [i for i in range(len(s_secs)) if i not in set(anchored)]
            if unauthored:
                census["notes"].append(
                    f"{len(unauthored)} measured source band(s) have no authored "
                    f"pattern (index {unauthored}) — scored as unauthored, not "
                    "absorbed into a neighbour")
            return resolved, census
        if anchored:
            census["notes"].append(
                f"provenance anchoring unavailable ({len(anchored)}/{n} pairs "
                f"resolved, {len(set(anchored))} distinct) — falling back to "
                "positional band pairing")
    aligned: list[int | None] = [i if i < len(s_secs) else None for i in range(n)]
    return aligned, census


# ── 1) compose the replica page ───────────────────────────────────────────────────

def build_replica_page(brand_yaml: Path, out_dir: Path, *, page: str | None = None) -> dict:
    """Compose the full source-order page into ``out_dir/index.html`` via the same
    demo-hydration + composition-adapter path the components preview's pattern
    demos use, then ``compose_page.build_page`` (page nav + closing footer).
    Returns {"order": [...], "sections": [...], "errors": {...}}.

    ``page`` (e.g. ``home``) limits composition to patterns whose provenance
    belongs to that capture page — required for multi-page brand unions whose
    replica target is a single screenshot.
    """
    doc = cp.load_doc(brand_yaml)
    patterns = rp.load_layout_library(brand_yaml)
    if not patterns:
        raise SystemExit(f"compose_replica: no layout-library patterns beside {brand_yaml}")
    pairs = source_order_sections(doc, patterns, page=page)

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
                # carry the Phase-2 RESPONSIVE fact block through adaptation (the demo
                # hydration / composition adapter builds a fresh layout object that would
                # otherwise drop it, leaving the composed hero non-responsive).
                if isinstance(layout, dict) and layout.get("responsive") \
                        and isinstance(adapted, dict) and "responsive" not in adapted:
                    adapted["responsive"] = layout["responsive"]
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
    # A replica always rebuilds the captured full page, including measured
    # chrome. compose_page's historical opener-family heuristic intentionally
    # omits chrome for standalone section renders; this marker selects its
    # existing composed-page chrome path without changing section semantics.
    page_doc["_composedPage"] = True

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
        input_digest = projection_input_digest(brand_dir)
        html = html.replace(
            "<html", f'<html data-projection-input-digest="{input_digest}"', 1)
        (out_dir / "index.html").write_text(html)
        tokens_css.write_manifest(
            out_dir, tokens_css.build_page_tokens(page_doc, style_ctx,
                                                  brand_yaml_path=brand_yaml))
        cs.copy_assets(brand_dir, out_dir / "assets")
        cs.copy_fonts(brand_dir, out_dir / "assets", page_doc)
    finally:
        cs.LAYOUT_COPY = saved_layout_copy

    # The DRAWABLE family each section actually resolved to (after adaptation),
    # recorded so the structural gate can compare it against the family the
    # source's own measured geometry implies. Without this the report can only
    # say how closely two images average out, never whether the replica used the
    # same KIND of layout as the thing it claims to rebuild.
    families = {l.get("id"): l.get("archetype") for l in adapted_layouts
                if isinstance(l, dict)}
    (out_dir / "composition.json").write_text(json.dumps(
        {"schemaVersion": "replica-composition.v1", "order": order,
         "sections": comp_sections, "drawableArchetypes": families,
         "errors": errors}, indent=1) + "\n")
    return {"order": order, "doc": page_doc, "errors": errors,
            "drawableArchetypes": families}


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


# ── Phase 5: multi-viewport replica gate ──────────────────────────────────────────
#
# The SSIM band diff scores the replica against the SOURCE full-page screenshot, which
# was captured at ONE viewport (1440, primary). That number is the desktop FIDELITY
# score. But it says nothing about whether the rebuild stays coherent as the viewport
# narrows — the exact axis the responsive-fact work targets. This pass loads the composed
# replica at the viewport LADDER (1440 primary + 375/960/1920) and records a per-viewport
# RESPONSIVENESS-HEALTH score: no horizontal overflow, every band still present, and the
# reflow the facts promise actually happens (hero height tracks the viewport; the footer
# directory collapses its columns on narrow). It is DISTINCT from the source-fidelity
# score (there is no source shot at the other viewports to diff against) and is labeled
# as such — honest per-viewport numbers, not a faked cross-viewport SSIM.

VIEWPORT_LADDER = (1440, 1920, 960, 375)   # 1440 primary; others surface responsiveness
_LADDER_VP_HEIGHT = {1920: 1080, 1440: 900, 960: 720, 375: 812}


def _viewport_health_js() -> str:
    return r"""
    () => {
      const de = document.documentElement;
      const vw = window.innerWidth;
      const scrollW = Math.max(de.scrollWidth, document.body.scrollWidth);
      const overflowPx = Math.max(0, scrollW - vw);
      const secs = Array.from(document.querySelectorAll('[id^=sec-]'));
      const nav = document.getElementById('page-nav');
      const bands = (nav ? 1 : 0) + secs.length;
      const hero = document.getElementById('sec-0');
      const heroH = hero ? Math.round(hero.getBoundingClientRect().height) : 0;
      const cols = document.querySelector('.c-foot-cols');
      let footCols = 0;
      if (cols) {
        const gt = getComputedStyle(cols).gridTemplateColumns || '';
        footCols = gt && gt !== 'none' ? gt.split(' ').filter(Boolean).length : 0;
      }
      // widest element that pokes past the viewport (diagnostic for overflow source)
      let widest = '';
      if (overflowPx > 1) {
        for (const el of document.querySelectorAll('*')) {
          const r = el.getBoundingClientRect();
          if (r.right > vw + 2 && r.width > 40) {
            widest = (el.id ? '#'+el.id : el.className || el.tagName).toString().slice(0,50);
            break;
          }
        }
      }
      return { viewport: vw, scrollWidth: scrollW, overflowPx, bands, heroHeight: heroH,
               footerColumns: footCols, docHeight: de.scrollHeight, overflowEl: widest };
    }
    """


def measure_viewport_ladder(out_dir: Path, viewports=VIEWPORT_LADDER,
                            primary: int = 1440, shoot: bool = True) -> list[dict]:
    """Load the composed replica at each viewport and record a responsiveness-health
    score per viewport, saving a full-page screenshot (``replica-fullpage-<w>.png``).
    Health = 1.0 penalized for horizontal overflow (content wider than the viewport) and
    for any missing band. Diagnostic (never blocks); the primary viewport is tagged."""
    from playwright.sync_api import sync_playwright
    index = out_dir / "index.html"
    rows: list[dict] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for w in viewports:
            h = _LADDER_VP_HEIGHT.get(w, 900)
            page = browser.new_page(viewport={"width": w, "height": h},
                                    device_scale_factor=1)
            page.goto(index.resolve().as_uri(), wait_until="load", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=6000)
            except Exception:
                pass
            page.evaluate("document.fonts && document.fonts.ready")
            page.wait_for_timeout(300)
            # scroll pass so IO reveals fire (content that stays hidden reads as overflow-free
            # falsely); then settle back to top.
            height = page.evaluate("document.body.scrollHeight")
            y, step = 0, max(400, h - 200)
            while y < height:
                page.evaluate(f"window.scrollTo(0, {y})")
                page.wait_for_timeout(60)
                y += step
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(200)
            m = page.evaluate(_viewport_health_js())
            if shoot:
                shot = out_dir / f"replica-fullpage-{w}.png"
                page.screenshot(path=str(shot), full_page=True)
                m["screenshot"] = shot.name
            # health: overflow costs up to 0.5 (scaled by overflow fraction of the
            # viewport, capped), a missing band costs 0.1 each below the primary count.
            overflow_frac = min(1.0, (m.get("overflowPx", 0) or 0) / max(1, w))
            health = 1.0 - min(0.5, overflow_frac * 2.0)
            m["responsivenessHealth"] = round(max(0.0, health), 4)
            m["primary"] = (w == primary)
            rows.append(m)
            page.close()
        browser.close()
    return rows


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


def _content_span(im, sample_w: int = 320, threshold: float = 8.0,
                  min_rows: int = 2) -> float:
    """FRACTION of the band width occupied by content: columns of the downsampled
    grayscale crop that DEVIATE from the band's background (estimated from the
    outermost columns — section content is inset from the page edges) by more
    than ``threshold`` gray levels on at least ``min_rows`` rows. 0.0 when the
    band reads empty/uniform.

    Deviation is counted PER ROW rather than against the column's mean: a tall
    band holding a short centered stack averages its content away, so a
    column-mean test reports a genuinely occupied band as empty (and, folded
    into a gate, would fail a faithful band for being sparse). Requiring several
    deviating rows keeps resampling ringing and single-pixel noise out.
    """
    from PIL import Image
    g = im.convert("L")
    h = max(4, round(sample_w * g.height / g.width))
    g = g.resize((sample_w, h), Image.LANCZOS)
    px = g.tobytes()  # mode L: one byte per pixel, row-major
    edge_cols = list(range(6)) + list(range(sample_w - 6, sample_w))
    edge_px = sorted(px[y * sample_w + x] for y in range(h) for x in edge_cols)
    bg = edge_px[len(edge_px) // 2]
    content = []
    for x in range(sample_w):
        hits = 0
        for y in range(h):
            if abs(px[y * sample_w + x] - bg) > threshold:
                hits += 1
                if hits >= min_rows:
                    content.append(x)
                    break
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
        # ("HubSpotSerif-Book") while each CSS-stack member is spaced
        # ("HubSpot Serif"). Compare concrete members, not the serialized stack.
        fam_keys = [
            part.strip().strip("\"'").lower().replace(" ", "")
            for part in fam.split(",")
            if part.strip().strip("\"'").lower() not in {
                "serif", "sans-serif", "monospace", "system-ui"
            }
        ]
        local = fonts_dir.is_dir() and any(
            any(key in f.stem.lower().replace(" ", "") for key in fam_keys)
            for f in fonts_dir.glob("*.woff2"))
        if fam not in cs.loadable_proxies(doc) and not local:
            out.append({"section": "page", "capability": f"display font ({fam})",
                        "note": "not self-hosted and not Google-loadable — headings "
                                "render in the declared fallback stack; extract the "
                                "woff2 files into assets/fonts/"})
    return out


def build_report(out_dir: Path, rows: list[dict], punch: list[dict],
                 overall: float, meta: dict, per_viewport: list[dict] | None = None) -> None:
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
    if per_viewport:
        lines += [
            "", "## Multi-viewport replica gate (Phase 5)", "",
            "Desktop **fidelity** (the `overall` above) is scored against the source "
            "full-page screenshot, captured at the primary viewport only. The other "
            "viewports have no source shot to diff against, so they record a "
            "**responsiveness-health** number instead (1.0 = no horizontal overflow, "
            "every band present, reflow intact) — responsiveness is *verified*, not a "
            "faked cross-viewport SSIM.", "",
            "| viewport | role | health | overflow px | bands | hero h | footer cols | doc h | shot |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for v in per_viewport:
            role = "primary (fidelity)" if v.get("primary") else "responsiveness"
            shot = f"`{v['screenshot']}`" if v.get("screenshot") else "—"
            over = v.get("overflowPx", 0)
            over_cell = f"{over}" + (f" (`{v['overflowEl']}`)" if over > 1 and v.get("overflowEl") else "")
            lines.append(
                f"| {v.get('viewport')} | {role} | {v.get('responsivenessHealth')} | "
                f"{over_cell} | {v.get('bands')} | {v.get('heroHeight')}px | "
                f"{v.get('footerColumns')} | {v.get('docHeight')}px | {shot} |")
    lines += ["", f"![strip](diff/strip.png)", ""]
    gate = meta.get("structuralGate") or {}
    if gate.get("signals"):
        lines += ["## Structural gate", "",
                  "Signals the averaged-MAE score cannot carry: whether the "
                  "rebuild used the same number of bands, the same kind of "
                  "layout, and the same content span as the source.", "",
                  "| signal | value | floor | ok | detail |",
                  "| --- | --- | --- | --- | --- |"]
        for name, sig in gate["signals"].items():
            lines.append(f"| {name} | {sig.get('value')} | {sig.get('floor')} | "
                         f"{'yes' if sig.get('ok') else '**no**'} | "
                         f"{sig.get('detail')} |")
        lines += ["", f"**Structural gate: "
                      f"{'pass' if gate.get('ok') else 'FAIL'}**", ""]
    lines += ["## Renderer-gap punch list", ""]
    if punch:
        for i, p in enumerate(punch, 1):
            score = f" (score {p['score']:.3f})" if p.get("score") is not None else ""
            lines.append(f"{i}. **{p['section']} — {p['capability']}**{score}: {p['note']}")
    else:
        lines.append("_no gaps above threshold_")
    lines += ["", "Diagnostic, not blocking — re-run with `--fail-under <score>` to gate.", ""]
    (out_dir / "replica-report.md").write_text("\n".join(lines))
    (out_dir / "replica-report.json").write_text(json.dumps(
        {"schemaVersion": "replica-report.v1",
         "overall": overall, "bands": rows,
         "perViewport": per_viewport or [],
         "punchList": punch, **meta}, indent=1) + "\n")


# ── structural gate: the signals an averaged-MAE score cannot carry ───────────────
#
# The similarity score is a mean absolute error between two images. That makes it
# blind, by construction, to the failures that matter most in a rebuild: a solid
# rectangle of the right background colour scores very high against a real band;
# blank padding raises a band's score for zero content; and making a band
# structurally MORE correct can lower it, because moving content into a second
# column raises per-pixel error faster than the height term rewards it. A gate
# built on that number alone is therefore gameable in the exact direction that
# looks like progress. These signals are categorical or geometric instead: they
# ask whether the rebuild used the same NUMBER of bands, the same KIND of layout,
# and the same CONTENT SPAN as the thing it claims to reproduce — none of which
# can be bought with a flat fill.
#
# Families that place content in more than one horizontal track, and families
# that place it in a single track. ``collage`` and ``banded`` appear in both:
# neither is a column grid, so either multiplicity can be faithful.
_MULTI_TRACK_FAMILIES = {"split", "media-split", "interlock", "cards",
                         "collage", "banded"}
_SINGLE_TRACK_FAMILIES = {"stack", "stack-fullbleed", "generic-flow", "overlay",
                          "collage", "banded"}
# A rebuild that claims to be 1:1 must pair every measured content band exactly
# once, and honor each band's measured track multiplicity: both are categorical
# facts, so the only principled floor is full agreement. Content span is a
# ratio, and a 0.80 floor is about one container-width step of error — tighter
# than that would flag ordinary inset/gutter differences.
GATE_FLOORS = {"bandCountAgreement": 1.0,
               "archetypeFamilyAgreement": 1.0,
               "contentSpanFidelity": 0.80}


def _measured_tracks(pat: dict | None) -> int | None:
    """Measured horizontal track count for a pattern, or None when unmeasured."""
    layout = (pat or {}).get("layout")
    if not isinstance(layout, dict):
        return None
    try:
        cols = int(layout.get("columns"))
    except (TypeError, ValueError):
        return None
    return cols if cols > 0 else None


_COUNTERWEIGHT_CONTRACTS = {"media", "image", "logo", "list", "table", "card",
                            "quote", "stat", "video", "chart"}


def _has_counterweight_slot(pat: dict | None, layout: dict | None) -> bool:
    """Does this section carry anything a SECOND horizontal track could hold?

    Generic by contract kind — a media panel, a repeated collection, a list or a
    table — never by section name or brand vocabulary.
    """
    for node in (pat, layout):
        for slot in ((node or {}).get("slots") or []):
            if not isinstance(slot, dict):
                continue
            probe = f"{slot.get('contract') or ''} {slot.get('role') or ''}".lower()
            if any(w in probe for w in _COUNTERWEIGHT_CONTRACTS):
                return True
    return False


def structural_gate(rows: list[dict], align_census: dict,
                    families: dict | None,
                    pairs: list[tuple[dict, dict]]) -> dict:
    """Non-MAE fidelity signals for the scored replica (see block comment above).

    Returns ``{"ok": bool, "signals": {...}, "blocking": [...]}``. The signals
    are reported ALONGSIDE ``overall``, never folded into it: the similarity
    number stays comparable across runs and keeps working as a coarse regression
    tripwire, while these say whether it is measuring the right comparison.
    """
    content_rows = [r for r in rows
                    if r.get("id") not in ("page-nav",) and r.get("scored", True)]
    signals: dict[str, dict] = {}

    # 1) BAND-COUNT AGREEMENT — measured content bands paired 1:1 with authored
    #    sections. Counted in BOTH directions: a measured band no authored
    #    section rebuilds, and an authored section no measured band anchors, are
    #    each a census divergence. Both are invisible to the score, which simply
    #    averages over whatever pairs it was handed.
    unauthored = [r.get("id") for r in content_rows if r.get("unauthored")]
    ordinals = align_census.get("sectionOrdinals")
    unpaired_authored = ([str((pairs[i][0] or {}).get("id"))
                          for i, band in enumerate(ordinals or [])
                          if band is None and i < len(pairs)]
                         if isinstance(ordinals, list) else [])
    denom = len(content_rows) + len(unpaired_authored)
    diverged = len(unauthored) + len(unpaired_authored)
    count_val = ((denom - diverged) / denom) if denom else 1.0
    signals["bandCountAgreement"] = {
        "value": round(count_val, 4),
        "floor": GATE_FLOORS["bandCountAgreement"],
        "ok": count_val >= GATE_FLOORS["bandCountAgreement"],
        "scoredBands": len(content_rows), "authoredSections": len(pairs),
        "unauthoredBands": unauthored, "unpairedSections": unpaired_authored,
        "detail": ("every measured content band is rebuilt by exactly one "
                   "authored section" if not diverged else
                   f"{diverged} of {denom} band slots diverge"
                   + (f" — measured but unauthored: {unauthored}" if unauthored else "")
                   + (f" — authored but unanchored: {unpaired_authored}"
                      if unpaired_authored else "")
                   + "; the score averages over a census that does not match "
                     "the source page"),
    }

    # 2) ARCHETYPE-FAMILY AGREEMENT — the composed drawable family honors each
    #    band's MEASURED track multiplicity. Catches multi-column source
    #    sections collapsed into single-column flow (and the converse), which
    #    the averaged metric can even reward.
    families = families or {}
    agree = 0
    checked = 0
    mismatches: list[str] = []
    unknown: list[str] = []
    for layout, pat in pairs:
        lid = str((layout or {}).get("id"))
        fam = families.get(lid) or (layout or {}).get("archetype")
        tracks = _measured_tracks(pat)
        if not fam or tracks is None:
            unknown.append(lid)
            continue
        checked += 1
        allowed = (_MULTI_TRACK_FAMILIES if tracks >= 2 else _SINGLE_TRACK_FAMILIES)
        if str(fam) in allowed:
            agree += 1
        else:
            why = ""
            if tracks >= 2 and not _has_counterweight_slot(pat, layout):
                # The renderer cannot draw a second track with nothing in it, so
                # a single-track family is the correct RENDERING of an authored
                # section that carries no counterweight. The divergence is then
                # upstream: the measured band's secondary occupant (media panel,
                # list, logo collection, decorative treatment) was never carried
                # into the authored slots.
                why = (" — the authored section carries no slot able to occupy "
                       "the secondary track, so the measured band's second "
                       "occupant was lost in projection, not in routing")
            mismatches.append(f"{lid}: measured {tracks} track(s) composed as "
                              f"'{fam}'{why}")
    fam_val = (agree / checked) if checked else 1.0
    signals["archetypeFamilyAgreement"] = {
        "value": round(fam_val, 4),
        "floor": GATE_FLOORS["archetypeFamilyAgreement"],
        "ok": fam_val >= GATE_FLOORS["archetypeFamilyAgreement"],
        "checked": checked, "agreed": agree,
        "unmeasured": unknown,
        "mismatches": mismatches,
        "detail": ("composed layout families honor the measured track "
                   "multiplicity of every band" if not mismatches else
                   "; ".join(mismatches)),
    }

    # 3) CONTENT-SPAN FIDELITY — folded INTO the gate rather than reported
    #    beside it. Height-weighted so a tall collapsed band cannot hide behind
    #    several short faithful ones.
    spans = [(r.get("widthFidelity"), r.get("srcHeight") or 0) for r in content_rows
             if isinstance(r.get("widthFidelity"), (int, float))]
    weight = sum(h for _, h in spans)
    span_val = (sum(v * h for v, h in spans) / weight) if weight else \
               (sum(v for v, _ in spans) / len(spans) if spans else 1.0)
    worst = sorted(((r.get("widthFidelity"), r.get("id")) for r in content_rows
                    if isinstance(r.get("widthFidelity"), (int, float))))[:3]
    signals["contentSpanFidelity"] = {
        "value": round(span_val, 4),
        "floor": GATE_FLOORS["contentSpanFidelity"],
        "ok": span_val >= GATE_FLOORS["contentSpanFidelity"],
        "worstBands": [{"id": bid, "widthFidelity": round(float(v), 4)}
                       for v, bid in worst],
        "detail": ("rebuilt content occupies the measured share of each band"
                   if span_val >= GATE_FLOORS["contentSpanFidelity"] else
                   "rebuilt content spans a different share of the band than "
                   "the source — a collapsed or over-wide container leaves most "
                   "of the band as matching background, so the averaged metric "
                   "barely registers it"),
    }

    blocking = [f"{k}: {v['value']} < floor {v['floor']} ({v['detail']})"
                for k, v in signals.items() if not v["ok"]]
    return {"ok": not blocking, "signals": signals, "blocking": blocking,
            "bandCensusNotes": list(align_census.get("notes") or [])}


def run_diff(brand_dir: Path, out_dir: Path, doc: dict,
             pairs: list[tuple[dict, dict]], replica_rects: dict,
             source_shot: Path | None, *,
             composed_order: list[str] | None = None,
             families: dict | None = None,
             page: str | None = None) -> tuple[list[dict], list[dict], float, dict]:
    from PIL import Image
    if composed_order is not None:
        assert_pairing_census(composed_order, pairs)
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

    src_rects_doc = json.loads(
        (_page_evidence_dir(brand_dir, page) / "section-rects.json").read_text()) \
        if (_page_evidence_dir(brand_dir, page) / "section-rects.json").is_file() else {}
    viewport_w = ((src_rects_doc.get("viewport") or {}).get("w")) or None
    aligned, align_census = align_source_bands(brand_dir, pairs, s_secs,
                                               page=page, viewport_w=viewport_w)
    pair_for_band: dict[int, int] = {b: p for p, b in enumerate(aligned)
                                     if b is not None}
    layout_by_pos = [layout.get("id") for layout, _ in pairs]

    matched: list[tuple[str, str, dict | None, dict | None, str | None]] = []
    # PAGE CHROME: only scorable when the source evidence measured a header band
    # of its own. When it did not, the source's chrome pixels are inside the
    # first content band and there is nothing separable to diff against — the
    # nav is then EXCLUDED DELIBERATELY (named in the census + punch list),
    # never scored as a silent 0.
    if s_nav is None:
        align_census["notes"].append(
            "source chrome census has no measured header band — the page nav is "
            "excluded from scoring by declaration (its source pixels sit inside "
            "the first content band); fix the measure stage to score it")
        matched.append(("page-nav", "navbar (chrome header)", None, r_nav,
                        "excluded: no measured source header band"))
    else:
        matched.append(("page-nav", "navbar (chrome header)", s_nav, r_nav, None))
    unauthored_bands: list[str] = []
    for i, s in enumerate(s_secs):
        pi = pair_for_band.get(i)
        if pi is None:
            unauthored_bands.append(f"sec-{i}")
            matched.append((f"sec-{i}", f"(unauthored) — {s.get('layout') or ''}"
                            .strip(" —"), s, None,
                            "no authored pattern rebuilds this measured source "
                            "band — the authoring census is short a section"))
            continue
        lid = layout_by_pos[pi]
        r = next((b for b in r_content if b.get("layout") == lid),
                 r_content[pi] if pi < len(r_content) else None)
        matched.append((f"sec-{i}", f"{lid} — {s.get('layout') or ''}".strip(" —"),
                        s, r, None))
    matched.append(("footer", "footer (closing bookend)", s_foot, r_foot, None))

    rows, pair_paths = [], []
    diff_dir = out_dir / "diff"
    diff_dir.mkdir(parents=True, exist_ok=True)
    for bid, label, s, r, excluded in matched:
        if excluded is not None and s is None:
            rows.append({"id": bid, "label": label, "score": 0.0, "structure": 0.0,
                         "pixel": 0.0, "height": 0.0, "srcHeight": 0,
                         "replicaHeight": int((r or {}).get("rect", {}).get("h", 0)),
                         "pair": None, "scored": False, "note": excluded})
            continue
        if not s or not r:
            rows.append({"id": bid, "label": label, "score": 0.0, "structure": 0.0,
                         "pixel": 0.0, "height": 0.0,
                         "srcHeight": int((s or {}).get("rect", {}).get("h", 0)),
                         "replicaHeight": int((r or {}).get("rect", {}).get("h", 0)),
                         "pair": None, "scored": True,
                         "unauthored": bid in unauthored_bands,
                         "note": excluded or "band missing on one side"})
            continue
        sc = _crop_band(src_im, s["rect"])
        rc = _crop_band(rep_im, r["rect"])
        if sc is None or rc is None:
            rows.append({"id": bid, "label": label, "score": 0.0, "structure": 0.0,
                         "pixel": 0.0, "height": 0.0, "srcHeight": 0,
                         "replicaHeight": 0, "pair": None, "scored": True,
                         "note": "empty crop"})
            continue
        m = band_similarity(sc, rc)
        pair_p = diff_dir / f"{bid}.png"
        side_by_side(sc, rc, pair_p, label)
        pair_paths.append(pair_p)
        rows.append({"id": bid, "label": label, **m, "scored": True,
                     "pair": str(pair_p.relative_to(out_dir))})
    build_strip(pair_paths, diff_dir / "strip.png")

    # Height-weighted over the bands the source actually offers for scoring. An
    # explicitly EXCLUDED band contributes neither score nor weight; an
    # unauthored source band contributes its weight at 0.0, because failing to
    # rebuild a measured section is a fidelity failure, not an exemption.
    scored_rows = [r for r in rows if r.get("scored", True)]
    total_h = sum(r["srcHeight"] for r in scored_rows) or 1
    overall = round(sum(r["score"] * r["srcHeight"] for r in scored_rows) / total_h, 4)

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
    for note in align_census.get("notes") or []:
        punch.append({"section": "page", "capability": "band census",
                      "score": None, "note": note})

    gate = structural_gate(rows, align_census, families, pairs)
    for reason in gate["blocking"]:
        punch.append({"section": "page", "capability": "structural gate",
                      "score": None, "note": reason})

    meta = {"inputDigest": projection_input_digest(brand_dir),
            "sourceShot": str(src_shot_path),
            "sourceHeight": src_im.height, "replicaHeight": rep_im.height,
            "bandAlignment": align_census,
            "structuralGate": gate}
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
    ap.add_argument("--skip-ladder", action="store_true",
                    help="skip the Phase-5 multi-viewport responsiveness ladder")
    ap.add_argument("--viewports-ladder",
                    default=",".join(str(v) for v in VIEWPORT_LADDER),
                    type=lambda s: [int(v) for v in s.split(",") if v.strip()],
                    help="csv responsiveness-ladder widths (default 1440,1920,960,375)")
    ap.add_argument("--fail-under", type=float, default=None,
                    help="exit 1 when the overall score is below this (gate mode); "
                         "in gate mode a structural-gate failure also exits 1")
    ap.add_argument("--allow-structural-divergence", action="store_true",
                    help="gate mode: enforce the score bar only, and report the "
                         "structural signals without failing on them")
    ap.add_argument("--page", default=None,
                    help="multi-page brands: only compose patterns whose provenance "
                         "belongs to this capture page (e.g. home). Auto-detected "
                         "from --source-shot path when omitted.")
    return ap


def _infer_page_from_source_shot(source_shot: Path | None,
                                 known_pages: list[str]) -> str | None:
    """screenshots/.../home/home-fullpage.png → 'home'.

    Matched against the pages the BRAND declares, never a hardcoded list, so the
    inference works for any capture set. The longest match wins so a page key
    that contains another ('talent-sourcing' vs 'talent') can't be shadowed.
    """
    if source_shot is None or not known_pages:
        return None
    parts = [p.lower() for p in Path(source_shot).parts]
    stem = Path(source_shot).stem.lower()
    for key in sorted(known_pages, key=len, reverse=True):
        if key in parts or stem.startswith(f"{key}-") or stem == key:
            return key
    return None


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    brand_yaml = args.brand_yaml.resolve()
    brand_dir = brand_yaml.parent
    out_dir = (args.out or (brand_dir / "compose" / "replica")).resolve()
    w, h = (int(x) for x in args.viewport.lower().split("x"))
    page = args.page or _infer_page_from_source_shot(
        args.source_shot,
        brand_source_pages(cp.load_doc(brand_yaml), rp.load_layout_library(brand_yaml)))

    built = build_replica_page(brand_yaml, out_dir, page=page)
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
    # SAME page filter as composition (fid16 2026-07): the diff pairs source band
    # i against scoring entry i, so an unfiltered scoring list silently scores
    # bands against sections that were never composed — see assert_pairing_census.
    pairs = source_order_sections(cp.load_doc(brand_yaml), patterns, page=page)
    rows, punch, overall, meta = run_diff(brand_dir, out_dir, doc, pairs, rects,
                                          args.source_shot,
                                          composed_order=built["order"],
                                          families=built.get("drawableArchetypes"),
                                          page=page)
    meta["brand"] = (doc.get("brand") or {}).get("name")
    for lid, err in built["errors"].items():
        punch.insert(0, {"section": lid, "capability": "section failed to compose",
                         "score": 0.0, "note": err})
    # Phase 5: multi-viewport responsiveness ladder (primary = the shot viewport).
    per_viewport: list[dict] = []
    if not args.skip_ladder:
        ladder = tuple(dict.fromkeys([w] + [v for v in args.viewports_ladder
                                            if v != w]))
        try:
            per_viewport = measure_viewport_ladder(out_dir, ladder, primary=w)
            for v in per_viewport:
                tag = "primary" if v.get("primary") else "responsiveness"
                print(f"[replica] viewport {v['viewport']:>4} ({tag}): health "
                      f"{v['responsivenessHealth']:.3f}, overflow {v['overflowPx']}px, "
                      f"{v['bands']} bands, footer cols {v['footerColumns']}")
        except Exception as exc:
            print(f"[replica] viewport ladder skipped: {type(exc).__name__}: {exc}")
    build_report(out_dir, rows, punch, overall, meta, per_viewport)
    print(f"[replica] overall score {overall:.3f}; {len(punch)} punch-list entries -> "
          f"replica-report.md")
    gate = meta.get("structuralGate") or {}
    for name, sig in (gate.get("signals") or {}).items():
        mark = "ok  " if sig.get("ok") else "FAIL"
        print(f"[replica] {mark} {name} {sig.get('value')} "
              f"(floor {sig.get('floor')})")
    if gate and not gate.get("ok"):
        print("[replica] STRUCTURAL GATE FAILED — the similarity score above is "
              "not measuring a faithful comparison:")
        for reason in gate.get("blocking") or []:
            print(f"[replica]   - {reason}")
    # GATE MODE. The similarity bar is a coarse tripwire on an averaged error,
    # and a rebuild can clear it while comparing the wrong census or drawing the
    # wrong kind of layout — so in gate mode BOTH must hold. Score-only gating
    # stays available with --allow-structural-divergence for diagnostic runs.
    if args.fail_under is not None:
        if overall < args.fail_under:
            print(f"[replica] FAIL: overall {overall:.3f} < --fail-under "
                  f"{args.fail_under}")
            return 1
        if gate and not gate.get("ok") and not args.allow_structural_divergence:
            print("[replica] FAIL: structural gate — the score cleared "
                  f"{args.fail_under} but the rebuild is not a faithful "
                  "comparison (see the signals above)")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
