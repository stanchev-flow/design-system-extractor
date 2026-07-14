#!/usr/bin/env python3
"""Section-rules auditor — enforces contracts/section-rules.yaml (section-rules.v1)
on rendered lanes (stage B of the quality steals; law: spec/section-rules.md).

The rule library is DATA: this module implements checker code for the library's
``enforcement: new`` rows only, keyed by rule id (the same shape as
interaction_audit's IC checks). ``enforcement: delegated`` rows are REPORTED with
their ``delegatedTo`` law — never re-implemented here. Absent families emit
``skip`` findings, never silence.

Layers (spec/section-rules.md enforcement shape):
  STATIC   — bs4 HTML parse: word counts, anatomy-parity sets, shape-class
             parses, roster diffs, punctuation/casing censuses.
  GEOMETRY — Playwright at the 1440 tier: rendered line counts (round(box
             height / line-height)), mark/icon box censuses, computed register
             sizes. ``--static-only`` skips the layer (its rules report skip).

Lane scoping (pass1 scale_adherence doctrine, spacing-conformance §3b — the
same composition.json law spacing_audit applies):
  generative — composition.v1 marker OR briefed legacy composition: all rules
               bind (content families + chrome fact-parity).
  replica    — briefless replica-composition.v1: EVIDENCE, never an audit
               target; every rule reports skip.
  specimen   — no composition (previews / spec books): page-scoped rules skip.

Precedence: measured brand facts outrank genre budgets (brand-schema §5.3,
AS-44) — a fact-contradicted budget records OVERRIDE with the fact cited, not
FAIL (e.g. SR-NAV-03 label budgets under harvested chrome).

Exit codes: baseline 0 (report only); ``--strict`` exits 1 on failing
``severity: required`` rows or lane errors — advisory rows never gate.

Usage (repo root):
  env -u PLAYWRIGHT_BROWSERS_PATH ./venv/bin/python -m brand_pipeline.section_rules_audit \\
      <lane dirs/html...> --brand runs/<brand>/brand [--strict] [--static-only] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
RULES_PATH = HERE / "contracts" / "section-rules.yaml"
SCHEMA_VERSION = "section-rules.v1"
DEFAULT_VIEWPORT = (1440, 900)
LANE_TIMEOUT_MS = 120_000

SETTLE_CSS = ("*, *::before, *::after { animation: none !important; "
              "transition: none !important; }")

CONTENT_FAMILIES = ("section-header", "hero", "stat-band", "logo-strip",
                    "capture-form", "pricing-tiers", "quote", "feature-grid",
                    "faq", "cta-band", "carousel")
CHROME_FAMILIES = ("nav", "footer")

# Measure-aware wrap budgets (stage-B calibration, recorded in the contracts'
# changelog): the authored line budgets describe FULL-measure headings; a
# split/half-measure column (media or form counterweight) halves the measure,
# so the same tight copy wraps ~2x — such boxes license ONE extra line. A box
# narrower than 60% of the ~1200px content measure at the 1440 tier is a
# half-measure column.
HALF_MEASURE_PX = 720.0


def _wrap_budget(base: int, box_width) -> int:
    try:
        if box_width and float(box_width) < HALF_MEASURE_PX:
            return base + 1
    except (TypeError, ValueError):
        pass
    return base

# button register classification (static approximation of the AS-59 computed-paint
# classifier): the substrate's filled-primary is the UNMODIFIED .c-button family;
# any register modifier demotes it to a quieter register.
_QUIET_BUTTON_RX = re.compile(
    r"c-button--(secondary|ghost|outline|quiet|link|text|navcta)")

_INTERROGATIVES = {
    "what", "how", "why", "when", "where", "who", "whose", "whom", "which",
    "can", "could", "do", "does", "did", "is", "are", "will", "would",
    "should", "may", "might", "must", "am", "was", "were", "have", "has", "had"}

# closed-class words that can NEVER lead a verb-led CTA label (SR-CTA-03 uses a
# structural non-verb screen, not a shared verb lexicon — brand verb habits are
# voice-facts law).
_NON_VERB_LEADS = {
    "a", "an", "the", "our", "your", "my", "their", "its", "this", "that",
    "these", "those", "it", "we", "you", "they", "and", "or", "of", "for",
    "with", "from", "about", "more", "most", "all", "info", "information",
    "platform", "pricing", "features", "product", "products", "overview",
    "details", "solutions"}

_URGENCY_TAILS = {"now", "today", "free"}


# ── rule library ─────────────────────────────────────────────────────────────────

def load_rules(path: Path = RULES_PATH) -> dict:
    doc = yaml.safe_load(path.read_text()) or {}
    if doc.get("schemaVersion") != SCHEMA_VERSION:
        raise ValueError(f"{path.name}: schemaVersion {doc.get('schemaVersion')!r} "
                         f"!= {SCHEMA_VERSION!r}")
    return doc


# ── lane scoping (mirrors spacing_audit._is_generative_lane — one doctrine) ──────

def lane_scope(lane_dir: Path) -> str:
    """'generative' | 'replica' | 'specimen' (spec/section-rules.md lane scope)."""
    comp = lane_dir / "composition.json"
    if not comp.exists():
        return "specimen"
    try:
        head = json.loads(comp.read_text())
    except (OSError, json.JSONDecodeError):
        return "specimen"
    schema = str(head.get("schemaVersion") or "")
    if schema == "composition.v1":
        return "generative"
    if schema == "replica-composition.v1":
        return "generative" if head.get("brief") else "replica"
    return "specimen"


def composition_sections(lane_dir: Path) -> dict[str, dict]:
    """data-layout id -> {useCase, contracts, archetypeRef} from the lane's
    composition.json (empty for compositionless lanes). Sections without an id
    key fall back to their positional sec-N (the composer's stamp)."""
    comp = lane_dir / "composition.json"
    out: dict[str, dict] = {}
    if not comp.exists():
        return out
    try:
        doc = json.loads(comp.read_text())
    except (OSError, json.JSONDecodeError):
        return out
    for i, sec in enumerate(doc.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or f"sec-{i}")
        out[sid] = {
            "useCase": str(sec.get("useCase") or ""),
            "contracts": [str((sl or {}).get("contract") or "")
                          for sl in (sec.get("slots") or [])],
            "archetypeRef": str(sec.get("archetypeRef") or ""),
        }
    return out


# ── text helpers ─────────────────────────────────────────────────────────────────

def _txt(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def _words(s: str) -> list[str]:
    return [w for w in re.split(r"\s+", s or "") if re.search(r"[A-Za-z0-9]", w)]


def _sentences(s: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+", s or "")
            if len(_words(p)) >= 2]


def _casing_class(s: str) -> str:
    """'upper' | 'title' | 'sentence' | 'any' (single words / numerals match any
    rule — the lenient census avoids proper-noun false flags)."""
    ws = [w for w in _words(s) if re.search(r"[A-Za-z]", w)]
    if not ws:
        return "any"
    if s == s.upper():
        return "upper"
    if len(ws) < 2:
        return "any"
    caps = sum(1 for w in ws if w[:1].isupper())
    return "title" if caps / len(ws) > 0.6 else "sentence"


def _casing_conflict(classes: list[str]) -> bool:
    definite = {c for c in classes if c != "any"}
    return len(definite) > 1


def _is_filled_button(el) -> bool:
    cls = " ".join(el.get("class") or [])
    if "c-button" not in cls or "c-arrow-link" in cls:
        return False
    return not _QUIET_BUTTON_RX.search(cls)


def _stat_shape(value: str) -> str:
    """Licensed stat shape classes (SR-STAT-01/02). Values carrying a numeric
    magnitude with a short unit word ('90 days', '6–12 months') classify
    INT-UNIT — a genuine magnitude (never 'wordy'), censused apart from bare
    counts because '+' qualifier grammar cannot apply to them."""
    s = (value or "").strip()
    if not s:
        return "WORDY"
    if re.fullmatch(r"\d+\s*/\s*\d+", s):
        return "RATIO"
    if re.match(r"^[$€£¥]", s):
        return "CUR"
    if re.search(r"^\d[\d,.]*\s*%", s):
        return "PCT"
    if re.fullmatch(r"\d[\d,.]*\s*[x×]", s, re.I):
        return "MULT"
    m = re.match(r"^\d[\d,.]*(?:\s*[–—-]\s*\d[\d,.]*)?", s)
    if m:
        rest = s[m.end():].strip()
        if rest.startswith("+") and not _words(rest[1:]):
            return "INT+"
        if not rest:
            return "INT"
        if len(_words(rest)) <= 2:
            return "INT-UNIT"
        return "WORDY"
    return "WORDY"


def _price_shape(text: str) -> tuple[str, str | None, bool]:
    """(shape, currency symbol, period-suffix present) — SR-TIER-03 vocabulary."""
    s = (text or "").strip()
    if re.match(r"^free\b", s, re.I):
        return ("ZERO", None, False)
    m = re.match(r"^([$€£¥])\s*[\d,]+(?:\.\d+)?", s)
    if m:
        rest = s[m.end():].strip()
        period = bool(re.match(r"^(/|per\b|a month|monthly|annual|/?mo\b|/?yr\b)",
                               rest, re.I))
        return ("CUR", m.group(1), period)
    if re.match(r"^(custom|contact|talk to|let'?s talk|get in touch|enterprise)",
                s, re.I):
        return ("CONTACT", None, False)
    return ("OFF", None, False)


# ── section model + family detection ─────────────────────────────────────────────

class SectionCtx:
    def __init__(self, node, sid: str, layout: str, comp: dict | None):
        self.node = node
        self.sid = sid
        self.layout = layout
        self.use_case = (comp or {}).get("useCase") or ""
        self.archetype = str(node.get("data-archetype") or "")
        self.families: set[str] = set()

    def __repr__(self):  # pragma: no cover - debug aid
        return f"<{self.sid} {self.layout} {sorted(self.families)}>"


def _grid_cells(node):
    """Feature-grid cells: .cs-module cells (quote modules belong to the quote
    family, not the grid census) + .cs-bento cells."""
    cells = [c for c in node.select(".cs-modules .cs-module")
             if "cs-module--quote" not in (c.get("class") or [])]
    bento = node.select(".cs-bento .cs-bento-cell")
    return cells, bento


def detect_families(sections: list[SectionCtx]) -> None:
    """Bind content families per the contracts' detection table (device classes +
    declared useCase + data-archetype stamps). A section may bind several."""
    first_content = sections[0] if sections else None
    for sec in sections:
        n, uc = sec.node, sec.use_case
        fams = sec.families
        if (uc == "hero" or sec.archetype.startswith("hero-")
                or (sec is first_content and n.select_one(".c-heading--display"))):
            fams.add("hero")
        if n.select_one(".cs-stat-band") or len(n.select(".c-stat")) >= 2:
            fams.add("stat-band")
        if n.select_one(".cs-logo-strip") or uc == "logos":
            fams.add("logo-strip")
        if n.find("form") or n.select_one(".cs-signup-panel, .cs-signup-grid"):
            fams.add("capture-form")
        if n.select_one(".cs-tiers") or uc == "pricing":
            fams.add("pricing-tiers")
        if (n.select_one(".cs-quote-grid, .cs-module--quote, blockquote,"
                         " .cs-quote-text")
                or uc == "testimonial" or n.select_one(".c-person")):
            fams.add("quote")
        cells, bento = _grid_cells(n)
        if len(cells) >= 2 or bento or uc == "features":
            fams.add("feature-grid")
        # faq: declared useCase is authoritative; the disclosure-device selectors
        # bind only when the section does not declare a DIFFERENT content use
        # (an agenda/schedule authored as accordion rows is a disclosure device —
        # IC-ACC/AS-40 law — not an FAQ; stage-B detection calibration).
        if uc == "faq" or (not uc and n.select_one(".cs-faq, details[name]")):
            fams.add("faq")
        if n.select_one(".cs-conversion-sec") or uc == "cta":
            fams.add("cta-band")
        if n.select_one(".cs-edgecut, .cs-panelcar, .cs-marquee"):
            fams.add("carousel")
        if fams - {"carousel"} or n.select_one("h1, h2, .c-heading"):
            fams.add("section-header")


def split_page(soup, comp_map: dict[str, dict]) -> tuple[list[SectionCtx], dict]:
    """Content sections ([id^=sec-] wrappers, chrome bands excluded) + chrome
    nodes. The closing-bookend footer band is chrome (compose_page's shared
    footer renderer), not a content section."""
    sections: list[SectionCtx] = []
    chrome = {"nav": soup.select_one("nav.cs-nav, .cs-nav"),
              "footer": soup.select_one(".cs-footer-sec, .c-footer, .c-foot")}
    for w in soup.select("[id^=sec-]"):
        layout = str(w.get("data-layout") or w.get("id") or "")
        if layout == "closing-bookend" or w.select_one(".cs-footer-sec"):
            continue
        comp = comp_map.get(layout) or comp_map.get(str(w.get("id") or ""))
        sections.append(SectionCtx(w, str(w.get("id")), layout, comp))
    detect_families(sections)
    return sections, chrome


# ── geometry layer ───────────────────────────────────────────────────────────────

MEASURE_JS = r"""
() => {
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const cs = getComputedStyle(el);
    return cs.display !== 'none' && cs.visibility !== 'hidden';
  };
  const clsOf = (el) => {
    const c = el.className;
    return typeof c === 'string' ? c : (c && c.baseVal) || '';
  };
  const lineCount = (el) => {
    const cs = getComputedStyle(el);
    let lh = parseFloat(cs.lineHeight);
    if (!lh || Number.isNaN(lh)) lh = 1.2 * parseFloat(cs.fontSize);
    const h = el.getBoundingClientRect().height;
    return Math.max(1, Math.round(h / lh));
  };
  const fontPx = (el) => parseFloat(getComputedStyle(el).fontSize);
  const maxLeafFont = (root) => {
    let m = 0;
    const walk = (el) => {
      for (const c of el.children) walk(c);
      if (!el.children.length && (el.textContent || '').trim() && vis(el))
        m = Math.max(m, fontPx(el));
    };
    walk(root);
    return m || (vis(root) ? fontPx(root) : 0);
  };

  const out = { sections: {}, page: {} };
  let pageDisplay = 0;
  const bodySizes = [];

  for (const wrap of document.querySelectorAll('[id^="sec-"]')) {
    const s = { headings: [], paragraphs: [], eyebrows: [], captions: [],
                proofRows: [], quotes: [], strips: [], icons: [],
                bodyFontPx: null };

    for (const el of wrap.querySelectorAll('h1, h2, h3, .c-heading')) {
      if (!vis(el) || !(el.textContent || '').trim()) continue;
      const cls = clsOf(el);
      s.headings.push({ tag: el.tagName.toLowerCase(), cls,
                        text: (el.textContent || '').trim().slice(0, 90),
                        lines: lineCount(el), fontPx: fontPx(el),
                        w: el.getBoundingClientRect().width,
                        display: /c-heading--display/.test(cls) ||
                                 el.tagName === 'H1' });
      if ((/c-heading--display/.test(cls) || el.tagName === 'H1'))
        pageDisplay = Math.max(pageDisplay, fontPx(el));
    }
    let nP = 0;
    for (const el of wrap.querySelectorAll('p')) {
      if (nP >= 6) break;
      const cls = clsOf(el);
      if (/c-eyebrow|c-caption|c-stat|foot-/.test(cls)) continue;
      const text = (el.textContent || '').trim();
      if (!vis(el) || text.length < 15) continue;
      s.paragraphs.push({ text: text.slice(0, 90), lines: lineCount(el),
                          fontPx: fontPx(el), cls,
                          w: el.getBoundingClientRect().width });
      if (s.bodyFontPx === null) { s.bodyFontPx = fontPx(el);
                                   bodySizes.push(fontPx(el)); }
      nP += 1;
    }
    for (const el of wrap.querySelectorAll('.c-eyebrow'))
      if (vis(el)) s.eyebrows.push({ text: (el.textContent || '').trim().slice(0, 60),
                                     fontPx: fontPx(el) });
    for (const el of wrap.querySelectorAll('.c-caption'))
      if (vis(el)) s.captions.push({ cls: clsOf(el), fontPx: fontPx(el) });

    // proof/meta/trust rows — quiet hero devices; .c-stat devices are excluded
    // (the stat register is ladder law: scale_adherence / SR-STAT-05).
    for (const el of wrap.querySelectorAll(
        '[class*="proof"], [class*="trust"], [class*="-meta"], [class*="meta-"]')) {
      if (!vis(el) || el.closest('.c-stat')) continue;
      if (el.querySelector('.c-stat')) continue;
      s.proofRows.push({ cls: clsOf(el), fontPx: maxLeafFont(el) });
    }
    for (const el of wrap.querySelectorAll(
        '.cs-module--quote p, blockquote, .cs-quote-text'))
      if (vis(el)) s.quotes.push(fontPx(el));
    for (const el of wrap.querySelectorAll('.cs-bento-cell--lead p'))
      if (vis(el) && el.parentElement.querySelector('.c-person')
          && !/c-person/.test(clsOf(el.closest('.c-person') || el)))
        s.quotes.push(fontPx(el));

    for (const strip of wrap.querySelectorAll('.cs-logo-strip')) {
      const marks = [];
      for (const el of strip.querySelectorAll(
          '.cs-logo-strip-item img, .cs-logo-strip-item svg, img.c-logo-img')) {
        const r = el.getBoundingClientRect();
        if (r.width >= 1 && r.height >= 1)
          marks.push({ w: Math.round(r.width * 10) / 10,
                       h: Math.round(r.height * 10) / 10 });
      }
      s.strips.push({ itembox: /cs-logo-strip--itembox/.test(clsOf(strip)),
                      marks });
    }
    for (const el of wrap.querySelectorAll(
        '.cs-module img, .cs-module svg, .cs-bento-cell img, .cs-bento-cell svg')) {
      if (!vis(el) || el.closest('.cs-logo-strip')) continue;
      const r = el.getBoundingClientRect();
      if (r.height > 0 && r.height <= 96)   // icon/mark scale; larger = media well
        s.icons.push({ w: Math.round(r.width), h: Math.round(r.height) });
    }
    out.sections[wrap.id] = s;
  }
  out.page.displayPx = pageDisplay || null;
  out.page.bodyPx = bodySizes.length
    ? bodySizes.sort((a, b) => a - b)[Math.floor(bodySizes.length / 2)] : null;
  return out;
}
"""


def measure_lane(pw, html: Path, viewport=DEFAULT_VIEWPORT) -> dict:
    browser = pw.chromium.launch()
    try:
        page = browser.new_page(
            viewport={"width": viewport[0], "height": viewport[1]},
            device_scale_factor=1, reduced_motion="reduce")
        page.set_default_timeout(LANE_TIMEOUT_MS)
        page.goto(html.resolve().as_uri(), wait_until="load",
                  timeout=LANE_TIMEOUT_MS)
        page.add_style_tag(content=SETTLE_CSS)
        page.evaluate("document.fonts && document.fonts.ready")
        page.wait_for_timeout(400)
        return page.evaluate(MEASURE_JS)
    finally:
        browser.close()


# ── lane context ─────────────────────────────────────────────────────────────────

class LaneCtx:
    def __init__(self, lane_dir: Path, html: Path, brand_doc: dict,
                 geometry: dict | None):
        self.lane_dir = lane_dir
        self.html_path = html
        self.brand = brand_doc or {}
        self.geometry = geometry           # None => geometry layer skipped
        self.scope = lane_scope(lane_dir)
        comp_map = composition_sections(lane_dir)
        self.soup = BeautifulSoup(html.read_text(), "html.parser")
        self.sections, self.chrome = split_page(self.soup, comp_map)

    def by_family(self, family: str) -> list[SectionCtx]:
        return [s for s in self.sections if family in s.families]

    def geo(self, sec: SectionCtx) -> dict:
        if not self.geometry:
            return {}
        return (self.geometry.get("sections") or {}).get(sec.sid) or {}

    def page_geo(self) -> dict:
        return (self.geometry or {}).get("page") or {}


def _f(rule: dict, verdict: str, detail: str, sec: str | None = None) -> dict:
    out = {"rule": rule["id"], "scope": rule["scope"],
           "severity": rule.get("severity", "advisory"),
           "verdict": verdict, "detail": detail}
    if sec:
        out["sec"] = sec
    return out


def _geo_skip(rule: dict) -> dict:
    return _f(rule, "skip", "geometry layer not run (--static-only)")


# ── checkers: section-header ─────────────────────────────────────────────────────

def _section_headings(lane: LaneCtx) -> list[tuple[SectionCtx, object]]:
    """Section-register headings: the h2 run of every content section (card/cell
    headings ride h3+/module registers; the hero display is SR-HERO-01's)."""
    out = []
    for sec in lane.sections:
        for h in sec.node.select("h2"):
            if _txt(h):
                out.append((sec, h))
    return out


def check_hdr_01(rule: dict, lane: LaneCtx) -> list[dict]:
    if lane.geometry is None:
        return [_geo_skip(rule)]
    bad, n = [], 0
    for sec in lane.sections:
        if "hero" in sec.families:
            continue
        for h in (lane.geo(sec).get("headings") or []):
            if h.get("tag") != "h2":
                continue
            n += 1
            budget = _wrap_budget(2, h.get("w"))
            if h["lines"] > budget:
                bad.append(f"{sec.sid} '{h['text'][:40]}' = {h['lines']} lines "
                           f"(budget {budget})")
    if not n:
        return [_f(rule, "skip", "no non-hero section headings rendered")]
    if bad:
        return [_f(rule, "fail", f"{len(bad)} heading(s) past the line budget: "
                                 + "; ".join(bad[:4]))]
    return [_f(rule, "pass", f"{n} non-hero section heading(s) within the "
                             "2-line budget (half-measure columns license 3)")]


def check_hdr_02(rule: dict, lane: LaneCtx) -> list[dict]:
    heads = []
    for sec in lane.sections:
        for h in sec.node.select("h1, h2"):
            t = _txt(h)
            if t:
                heads.append((sec.sid, t))
    if not heads:
        return [_f(rule, "skip", "no section headings rendered")]
    problems = []
    seen: dict[str, str] = {}
    for sid, t in heads:
        if t.endswith("…") or t.endswith("..."):
            problems.append(f"{sid} terminal ellipsis: '{t[:40]}'")
        if re.search(r"[!?]{2,}|(?<!\.)\.\.(?!\.)", t):
            problems.append(f"{sid} double punctuation: '{t[:40]}'")
        key = re.sub(r"\W+", " ", t.lower()).strip()
        if key in seen:
            problems.append(f"{sid} duplicates {seen[key]}: '{t[:40]}'")
        else:
            seen[key] = sid
    if problems:
        return [_f(rule, "fail", "; ".join(problems[:4]))]
    return [_f(rule, "pass", f"{len(heads)} heading(s): 0 duplicates, 0 ellipses, "
                             "0 double punctuation")]


# ── checkers: hero ───────────────────────────────────────────────────────────────

def check_hero_01(rule: dict, lane: LaneCtx) -> list[dict]:
    heroes = lane.by_family("hero")
    if not heroes:
        return [_f(rule, "skip", "no hero section")]
    if lane.geometry is None:
        return [_geo_skip(rule)]
    out = []
    for sec in heroes:
        disp = [h for h in (lane.geo(sec).get("headings") or []) if h.get("display")]
        if not disp:
            out.append(_f(rule, "skip", "no display heading rendered", sec.sid))
            continue
        bad = [h for h in disp if h["lines"] > _wrap_budget(3, h.get("w"))]
        if bad:
            out.append(_f(rule, "fail",
                          "; ".join(f"'{h['text'][:40]}' = {h['lines']} lines "
                                    f"(budget {_wrap_budget(3, h.get('w'))})"
                                    for h in bad[:2]), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"display renders {disp[0]['lines']} line(s) within "
                          "the 3-line budget (half-measure columns license 4)",
                          sec.sid))
    return out


def _hero_subheading(lane: LaneCtx, sec: SectionCtx):
    """First supporting paragraph of the hero (static node + geometry record)."""
    node = None
    for p in sec.node.select("p"):
        cls = " ".join(p.get("class") or [])
        if re.search(r"c-eyebrow|c-caption|c-stat|consent|foot-", cls):
            continue
        if len(_txt(p)) >= 15:
            node = p
            break
    geo = None
    for p in (lane.geo(sec).get("paragraphs") or []):
        geo = p
        break
    return node, geo


def check_hero_02(rule: dict, lane: LaneCtx) -> list[dict]:
    heroes = lane.by_family("hero")
    if not heroes:
        return [_f(rule, "skip", "no hero section")]
    out = []
    for sec in heroes:
        node, geo = _hero_subheading(lane, sec)
        if node is None:
            out.append(_f(rule, "skip", "no supporting paragraph", sec.sid))
            continue
        n_sent = len(_sentences(_txt(node)))
        bits, ok = [], True
        if n_sent > 2:
            ok = False
            bits.append(f"{n_sent} sentences (max 2)")
        if lane.geometry is None:
            bits.append("lines unmeasured (--static-only)")
        elif geo:
            budget = _wrap_budget(3, geo.get("w"))
            if geo["lines"] > budget:
                ok = False
                bits.append(f"{geo['lines']} rendered lines (budget {budget})")
        out.append(_f(rule, "pass" if ok else "fail",
                      "; ".join(bits) or
                      f"{n_sent} sentence(s), "
                      f"{geo['lines'] if geo else '?'} line(s)", sec.sid))
    return out


def check_hero_04(rule: dict, lane: LaneCtx) -> list[dict]:
    heroes = lane.by_family("hero")
    if not heroes:
        return [_f(rule, "skip", "no hero section")]
    out = []
    for sec in heroes:
        eyes = [_txt(e) for e in sec.node.select(".c-eyebrow") if _txt(e)]
        # a dot-separated META ROW riding the eyebrow register (event date ·
        # time · format — the meta-forward archetype's metaPlacement device) is
        # a proof/meta row (SR-HERO-05's register law), not a kicker: the
        # 5-word kicker budget does not police logistics rows.
        eyes = [e for e in eyes if len(re.findall(r"[·•|]", e)) < 2]
        if not eyes:
            out.append(_f(rule, "skip",
                          "no hero kicker (meta rows are SR-HERO-05 territory)",
                          sec.sid))
            continue
        bad = [e for e in eyes
               if len(_words(e)) > 5 or e.rstrip().endswith(".")]
        if bad:
            out.append(_f(rule, "fail",
                          "; ".join(f"'{e[:40]}' ({len(_words(e))}w"
                                    f"{', terminal .' if e.rstrip().endswith('.') else ''})"
                                    for e in bad[:2]), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(eyes)} eyebrow(s) <= 5 words, no terminal period",
                          sec.sid))
    return out


def check_hero_05(rule: dict, lane: LaneCtx) -> list[dict]:
    heroes = lane.by_family("hero")
    if not heroes:
        return [_f(rule, "skip", "no hero section")]
    if lane.geometry is None:
        return [_geo_skip(rule)]
    out = []
    for sec in heroes:
        g = lane.geo(sec)
        rows = g.get("proofRows") or []
        if not rows:
            out.append(_f(rule, "skip", "no proof/meta row", sec.sid))
            continue
        body = g.get("bodyFontPx") or lane.page_geo().get("bodyPx")
        if not body:
            out.append(_f(rule, "skip", "no body register to compare against",
                          sec.sid))
            continue
        bad = [r for r in rows if r["fontPx"] > body + 0.6]
        if bad:
            out.append(_f(rule, "fail",
                          "; ".join(f"{r['cls'].split()[0] if r['cls'] else '?'} "
                                    f"{r['fontPx']:.1f}px > body {body:.1f}px"
                                    for r in bad[:3]), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(rows)} proof row(s) at or below body "
                          f"({body:.1f}px)", sec.sid))
    return out


# ── checkers: stat-band ──────────────────────────────────────────────────────────

def _stat_items(sec: SectionCtx) -> list[tuple[str, str]]:
    items = []
    for stat in sec.node.select(".c-stat"):
        v = stat.select_one(".c-stat-value")
        l = stat.select_one(".c-stat-label")
        items.append((_txt(v) if v else "", _txt(l) if l else ""))
    return items


def check_stat_01(rule: dict, lane: LaneCtx) -> list[dict]:
    bands = lane.by_family("stat-band")
    if not bands:
        return [_f(rule, "skip", "no stat band")]
    out = []
    for sec in bands:
        vals = [v for v, _ in _stat_items(sec) if v]
        if not vals:
            out.append(_f(rule, "skip", "no stat values rendered", sec.sid))
            continue
        wordy = [v for v in vals if _stat_shape(v) == "WORDY"]
        if wordy:
            out.append(_f(rule, "fail",
                          f"{len(wordy)} wordy value(s): "
                          + "; ".join(f"'{v[:30]}'" for v in wordy[:4]), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(vals)} value(s) all carry magnitudes "
                          f"({', '.join(sorted({_stat_shape(v) for v in vals}))})",
                          sec.sid))
    return out


def check_stat_02(rule: dict, lane: LaneCtx) -> list[dict]:
    bands = lane.by_family("stat-band")
    if not bands:
        return [_f(rule, "skip", "no stat band")]
    out = []
    for sec in bands:
        vals = [v for v, _ in _stat_items(sec) if v]
        if len(vals) < 2:
            out.append(_f(rule, "skip", "fewer than 2 values", sec.sid))
            continue
        shapes = {v: _stat_shape(v) for v in vals}
        problems = []
        counts = [v for v, s in shapes.items() if s in ("INT", "INT+")]
        if counts:
            plus = {shapes[v] == "INT+" for v in counts}
            if len(plus) > 1:
                problems.append("count qualifier drift (some '+', some bare): "
                                + ", ".join(f"'{v}'" for v in counts[:4]))
        pcts = [v for v, s in shapes.items() if s == "PCT"]
        if len(pcts) >= 2:
            prec = {len(v.split(".")[1].rstrip("%")) if "." in v else 0
                    for v in pcts}
            if len(prec) > 1:
                problems.append("percent precision drift: "
                                + ", ".join(f"'{v}'" for v in pcts[:4]))
        ratios = [v for v, s in shapes.items() if s == "RATIO"]
        measured = [v for v, s in shapes.items() if s not in ("RATIO", "WORDY")]
        if ratios and measured:
            problems.append(f"RATIO pseudo-stat among measured magnitudes: "
                            + ", ".join(f"'{v}'" for v in ratios[:2]))
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          "qualifier grammar parallel across "
                          f"{len(vals)} value(s)", sec.sid))
    return out


def check_stat_03(rule: dict, lane: LaneCtx) -> list[dict]:
    bands = lane.by_family("stat-band")
    if not bands:
        return [_f(rule, "skip", "no stat band")]
    out = []
    for sec in bands:
        labels = [l for _, l in _stat_items(sec) if l]
        if not labels:
            out.append(_f(rule, "skip", "no stat labels", sec.sid))
            continue
        problems = []
        counts = [len(_words(l)) for l in labels]
        long = [l for l, n in zip(labels, counts) if n > 6 or n < 1]
        if long:
            problems.append(f"{len(long)} label(s) outside 1-6 words: "
                            + "; ".join(f"'{l[:36]}…' ({len(_words(l))}w)"
                                        for l in long[:3]))
        if len(counts) >= 2 and min(counts) > 0 and max(counts) / min(counts) > 3:
            problems.append(f"word-count spread {max(counts)}/{min(counts)} > 3x")
        if _casing_conflict([_casing_class(l) for l in labels]):
            problems.append("mixed casing rules across labels")
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass", f"{len(labels)} parallel label(s)",
                          sec.sid))
    return out


def check_stat_04(rule: dict, lane: LaneCtx) -> list[dict]:
    bands = lane.by_family("stat-band")
    if not bands:
        return [_f(rule, "skip", "no stat band")]
    out = []
    for sec in bands:
        items = [(v, l) for v, l in _stat_items(sec) if v or l]
        problems = []
        if not 2 <= len(items) <= 6:
            problems.append(f"{len(items)} stat(s) (band budget 2-6)")
        seen = set()
        for v, l in items:
            key = (v.lower(), l.lower())
            if key in seen:
                problems.append(f"duplicate stat '{v} / {l[:24]}'")
            seen.add(key)
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass", f"{len(items)} stat(s), no duplicates",
                          sec.sid))
    return out


# ── checkers: logo-strip ─────────────────────────────────────────────────────────

def check_logo_01(rule: dict, lane: LaneCtx) -> list[dict]:
    strips = lane.by_family("logo-strip")
    if not strips:
        return [_f(rule, "skip", "no logo strip")]
    if lane.geometry is None:
        return [_geo_skip(rule)]
    out = []
    for sec in strips:
        for i, strip in enumerate(lane.geo(sec).get("strips") or []):
            marks = strip.get("marks") or []
            if len(marks) < 2:
                out.append(_f(rule, "skip", "fewer than 2 rendered marks",
                              sec.sid))
                continue
            heights = sorted(m["h"] for m in marks)
            med = statistics.median(heights)
            if strip.get("itembox"):
                spread = max(heights) - min(heights)
                ok = spread <= 2.0
                out.append(_f(rule, "pass" if ok else "fail",
                              f"declared itembox: mark heights within {spread:.1f}px"
                              + ("" if ok else " (exact box expected)"), sec.sid))
            else:
                ratio = max(heights) / med if med else 0
                ok = ratio <= 1.5
                out.append(_f(rule, "pass" if ok else "fail",
                              f"fact-less strip: max/median height "
                              f"{ratio:.2f} ({'<=' if ok else '>'} 1.5), "
                              f"{len(marks)} mark(s)", sec.sid))
    return out


def _strip_marks(sec: SectionCtx) -> list[str]:
    seen, out = set(), []
    for item in sec.node.select(".cs-logo-strip-item"):
        img = item.select_one("img, svg")
        key = (img.get("src") or img.get("alt") or _txt(item) or str(len(out))
               if img else _txt(item))
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def check_logo_02(rule: dict, lane: LaneCtx) -> list[dict]:
    strips = lane.by_family("logo-strip")
    if not strips:
        return [_f(rule, "skip", "no logo strip")]
    out = []
    for sec in strips:
        marks = _strip_marks(sec)
        if not marks:
            out.append(_f(rule, "skip", "no strip items", sec.sid))
        elif len(marks) < 4:
            out.append(_f(rule, "fail",
                          f"{len(marks)} distinct mark(s) (< 4 reads as "
                          "name-dropping)", sec.sid))
        else:
            out.append(_f(rule, "pass", f"{len(marks)} distinct mark(s)",
                          sec.sid))
    return out


def check_logo_04(rule: dict, lane: LaneCtx) -> list[dict]:
    strips = lane.by_family("logo-strip")
    if not strips:
        return [_f(rule, "skip", "no logo strip")]
    if lane.geometry is None:
        return [_geo_skip(rule)]
    out = []
    for sec in strips:
        g = lane.geo(sec)
        sizes = ([e["fontPx"] for e in (g.get("eyebrows") or [])]
                 + [c["fontPx"] for c in (g.get("captions") or [])])
        if not sizes:
            out.append(_f(rule, "skip", "no strip caption", sec.sid))
            continue
        body = g.get("bodyFontPx") or lane.page_geo().get("bodyPx")
        if not body:
            out.append(_f(rule, "skip", "no body register on page", sec.sid))
            continue
        big = [s for s in sizes if s > body + 0.6]
        if big:
            out.append(_f(rule, "fail",
                          f"caption at {max(big):.1f}px exceeds body "
                          f"{body:.1f}px", sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"caption register <= body ({body:.1f}px)", sec.sid))
    return out


# ── checkers: capture-form ───────────────────────────────────────────────────────

def _visible_controls(form) -> tuple[list, int]:
    controls, radio_groups = [], set()
    required = 0
    for el in form.select("input, select, textarea"):
        typ = (el.get("type") or "text").lower()
        if typ in ("hidden", "submit", "button", "image", "reset"):
            continue
        if typ == "radio":
            name = el.get("name") or "radio"
            if name in radio_groups:
                continue
            radio_groups.add(name)
        controls.append(el)
        if el.has_attr("required"):
            required += 1
    return controls, required


def check_form_01(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("capture-form")
    if not secs:
        return [_f(rule, "skip", "no capture form")]
    out = []
    for sec in secs:
        forms = sec.node.select("form")
        if not forms:
            out.append(_f(rule, "skip", "signup panel without a form element",
                          sec.sid))
            continue
        for form in forms:
            controls, required = _visible_controls(form)
            ok = len(controls) <= 8 and required <= 5
            out.append(_f(rule, "pass" if ok else "fail",
                          f"{len(controls)} visible control(s) (max 8), "
                          f"{required} required (max 5)", sec.sid))
    return out


def check_form_04(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("capture-form")
    if not secs:
        return [_f(rule, "skip", "no capture form")]
    out = []
    for sec in secs:
        for form in sec.node.select("form"):
            submits = [b for b in form.select("button, input[type=submit]")
                       if b.name == "input"
                       or (b.get("type") or "submit").lower() == "submit"]
            problems = []
            if len(submits) != 1:
                problems.append(f"{len(submits)} submit control(s) (exactly 1)")
            for b in submits:
                if not _is_filled_button(b):
                    problems.append("submit is not on the filled-primary register")
            siblings = [a for a in form.select(".c-button, a.c-button")
                        if a not in submits]
            loud = [a for a in siblings if _is_filled_button(a)]
            if loud:
                problems.append(f"{len(loud)} filled sibling action(s) beside "
                                "the submit")
            if problems:
                out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
            else:
                out.append(_f(rule, "pass",
                              "1 filled submit; siblings quiet", sec.sid))
        if not sec.node.select("form"):
            out.append(_f(rule, "skip", "signup panel without a form element",
                          sec.sid))
    return out


_PII_RX = re.compile(r"(mail|name|phone|tel)", re.I)


def check_form_05(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("capture-form")
    if not secs:
        return [_f(rule, "skip", "no capture form")]
    out = []
    for sec in secs:
        pii = False
        for el in sec.node.select("input"):
            typ = (el.get("type") or "text").lower()
            hint = " ".join(str(el.get(a) or "") for a in ("name", "id",
                                                           "placeholder",
                                                           "aria-label"))
            if typ in ("email", "tel") or _PII_RX.search(hint):
                pii = True
        if not pii:
            # labels name the fields when attrs don't
            for lab in sec.node.select("label"):
                if _PII_RX.search(_txt(lab)):
                    pii = True
        if not pii:
            out.append(_f(rule, "skip", "no PII inputs", sec.sid))
            continue
        consent = sec.node.select_one(".cs-signup-consent")
        if consent is None:
            for el in sec.node.select("p, span, label"):
                if re.search(r"privacy|terms|consent|agree|unsubscribe",
                             _txt(el), re.I):
                    consent = el
                    break
        if consent is not None:
            out.append(_f(rule, "pass", "consent/privacy line present", sec.sid))
        else:
            out.append(_f(rule, "fail",
                          "PII form without a consent/privacy register line",
                          sec.sid))
    return out


def check_form_06(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("capture-form")
    if not secs:
        return [_f(rule, "skip", "no capture form")]
    out = []
    for sec in secs:
        labels = []
        for lab in sec.node.select("form label"):
            cls = " ".join(lab.get("class") or [])
            if lab.find_parent(class_="cs-choice-group") is not None \
                    or "cs-choice" in cls:
                continue  # option/consent choice labels are values, not field labels
            direct = "".join(t for t in lab.find_all(string=True, recursive=False))
            t = re.sub(r"\s+", " ", direct).strip() or _txt(lab)
            if t:
                labels.append(t)
        if not labels:
            out.append(_f(rule, "skip", "no field labels", sec.sid))
            continue
        problems = []
        long = [l for l in labels if len(_words(l)) > 4]
        if long:
            problems.append(f"{len(long)} label(s) over 4 words: "
                            + "; ".join(f"'{l[:30]}'" for l in long[:3]))
        colons = {l.rstrip().endswith(":") for l in labels}
        if len(colons) > 1:
            problems.append("mixed colon usage across labels")
        if _casing_conflict([_casing_class(l) for l in labels]):
            problems.append("mixed casing rules across labels")
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass", f"{len(labels)} parallel field label(s)",
                          sec.sid))
    return out


# ── checkers: pricing-tiers ──────────────────────────────────────────────────────

def _tier_cards(sec: SectionCtx) -> list:
    return sec.node.select(".cs-tier")


def _tier_slots(card) -> dict:
    return {
        "name": card.select_one(".cs-tier-name") is not None,
        "price": card.select_one(".cs-tier-price") is not None,
        "tagline": card.select_one(".cs-tier-tagline, .cs-tier-period") is not None,
        "list": card.select_one(".cs-tier-list") is not None,
        "cta": card.select_one(".c-button") is not None,
        "badge": card.select_one("[class*=badge]") is not None,
    }


def _tier_emphasized(card) -> bool:
    cls = " ".join(card.get("class") or [])
    if re.search(r"cs-tier--emph|--featured|--highlight", cls):
        return True
    if card.select_one(".cs-tier-head--surface, [class*=badge]"):
        return True
    return False


def check_tier_01(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("pricing-tiers")
    if not secs:
        return [_f(rule, "skip", "no tier band")]
    out = []
    for sec in secs:
        cards = _tier_cards(sec)
        if len(cards) < 2:
            out.append(_f(rule, "skip", f"{len(cards)} card(s) — parity needs 2+",
                          sec.sid))
            continue
        sets = []
        for card in cards:
            slots = _tier_slots(card)
            slots.pop("badge", None)  # badge exempt (SR-TIER-02 owns its count)
            sets.append(frozenset(k for k, v in slots.items() if v))
        if len(set(sets)) > 1:
            detail = "; ".join(f"card {i+1}: {{{', '.join(sorted(s))}}}"
                               for i, s in enumerate(sets))
            out.append(_f(rule, "fail", f"anatomy sets differ — {detail}",
                          sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(cards)} card(s) share anatomy "
                          f"{{{', '.join(sorted(sets[0]))}}}", sec.sid))
    return out


def check_tier_02(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("pricing-tiers")
    if not secs:
        return [_f(rule, "skip", "no tier band")]
    out = []
    for sec in secs:
        cards = _tier_cards(sec)
        if not cards:
            out.append(_f(rule, "skip", "no tier cards", sec.sid))
            continue
        emph = [i for i, c in enumerate(cards) if _tier_emphasized(c)]
        filled = [i for i, c in enumerate(cards)
                  if any(_is_filled_button(b) for b in c.select(".c-button"))]
        problems = []
        if len(emph) > 1:
            problems.append(f"{len(emph)} emphasized card(s) (max 1)")
        if emph and filled and set(filled) - set(emph):
            stray = sorted(set(filled) - set(emph))
            problems.append(
                f"filled-primary CTA on non-emphasized card(s) "
                f"{[i + 1 for i in stray]} while card {emph[0] + 1} carries "
                "the emphasis treatment")
        if not emph and len(filled) > 1:
            problems.append(f"{len(filled)} filled CTAs in a no-highlight band")
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(emph)} emphasized / {len(filled)} filled CTA "
                          "— hierarchy holds", sec.sid))
    return out


def check_tier_03(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("pricing-tiers")
    if not secs:
        return [_f(rule, "skip", "no tier band")]
    out = []
    for sec in secs:
        prices = [_txt(p) for p in sec.node.select(".cs-tier-price") if _txt(p)]
        if not prices:
            out.append(_f(rule, "skip", "no price nodes", sec.sid))
            continue
        shapes = [(_price_shape(p), p) for p in prices]
        problems = []
        off = [p for (s, _, _), p in shapes if s == "OFF"]
        if off:
            problems.append(f"{len(off)} off-shape price(s): "
                            + "; ".join(f"'{p[:24]}'" for p in off[:3]))
        curs = [(sym, per) for (s, sym, per), _ in shapes if s == "CUR"]
        if len({sym for sym, _ in curs}) > 1:
            problems.append("mixed currency symbols")
        if len({per for _, per in curs}) > 1:
            problems.append("period suffix on some currency prices, not all")
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(prices)} price(s) share one grammar", sec.sid))
    return out


def check_tier_04(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("pricing-tiers")
    if not secs:
        return [_f(rule, "skip", "no tier band")]
    out = []
    for sec in secs:
        counts = [len(c.select(".cs-tier-list li")) for c in _tier_cards(sec)
                  if c.select_one(".cs-tier-list")]
        if not counts:
            out.append(_f(rule, "skip", "no feature lists", sec.sid))
            continue
        problems = []
        outside = [n for n in counts if not 2 <= n <= 8]
        if outside:
            problems.append(f"bullet counts outside 2-8: {outside}")
        if len(counts) >= 2 and min(counts) and max(counts) / min(counts) > 2:
            problems.append(f"list spread {max(counts)}/{min(counts)} > 2x")
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass", f"bullets per card {counts}", sec.sid))
    return out


def check_tier_05(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("pricing-tiers")
    if not secs:
        return [_f(rule, "skip", "no tier band")]
    out = []
    for sec in secs:
        n = len(_tier_cards(sec))
        if not n:
            out.append(_f(rule, "skip", "no tier cards", sec.sid))
        elif 2 <= n <= 4:
            out.append(_f(rule, "pass", f"{n} tier(s)", sec.sid))
        else:
            out.append(_f(rule, "fail", f"{n} tier(s) (band budget 2-4)",
                          sec.sid))
    return out


# ── checkers: quote ──────────────────────────────────────────────────────────────

def _quote_units(sec: SectionCtx) -> list[dict]:
    """Quote units: marked modules (blockquote / .cs-quote-* / .cs-module--quote)
    plus attribution-device cells (a paragraph beside a .c-person node is the
    substrate's quote anatomy — the bento-lead quote shape)."""
    units = []
    for node in sec.node.select(".cs-module--quote, blockquote, .cs-quote-text"):
        units.append({"node": node, "marked": True})
    marked_nodes = [u["node"] for u in units]
    for person in sec.node.select(".c-person"):
        cell = person.parent
        if any(cell is m or m in cell.parents or cell in m.parents
               for m in marked_nodes):
            continue
        units.append({"node": cell, "marked": True})
    return units


def _quote_body_text(unit) -> str:
    node = unit["node"]
    ps = [p for p in node.select("p")
          if not re.search(r"c-person|c-eyebrow|c-caption",
                           " ".join(p.get("class") or []))]
    if ps:
        return max((_txt(p) for p in ps), key=len)
    return _txt(node)


def check_quote_01(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("quote")
    if not secs:
        return [_f(rule, "skip", "no quote section")]
    out = []
    for sec in secs:
        units = _quote_units(sec)
        problems = []
        # static: quote-register copy outside any marked unit = a heading that
        # grew quotation marks
        unit_nodes = [u["node"] for u in units]
        for p in sec.node.select("p"):
            t = _txt(p)
            if len(t) >= 20 and t[:1] in "\u201c\"'\u2018" and not any(
                    p is n or n in p.parents for n in unit_nodes):
                problems.append(f"unmarked quote copy: '{t[:36]}…'")
        if not units and not problems:
            out.append(_f(rule, "skip", "no quote units rendered", sec.sid))
            continue
        # geometry: quote register stays below the page display
        if lane.geometry is not None:
            disp = lane.page_geo().get("displayPx")
            sizes = lane.geo(sec).get("quotes") or []
            if disp and sizes:
                big = [s for s in sizes if s >= disp]
                if big:
                    problems.append(f"quote at {max(big):.0f}px reaches the "
                                    f"display register ({disp:.0f}px)")
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems[:3]), sec.sid))
        else:
            tail = ("register below display" if lane.geometry is not None
                    else "register unmeasured (--static-only)")
            out.append(_f(rule, "pass",
                          f"{len(units)} quote unit(s) marked; {tail}", sec.sid))
    return out


def check_quote_02(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("quote")
    if not secs:
        return [_f(rule, "skip", "no quote section")]
    out = []
    for sec in secs:
        units = _quote_units(sec)
        if not units:
            out.append(_f(rule, "skip", "no quote units rendered", sec.sid))
            continue
        missing = []
        for u in units:
            att = (u["node"].select_one(".c-person, cite, figcaption")
                   or (u["node"].parent.select_one(".c-person")
                       if u["node"].parent else None))
            if att is None or not _txt(att):
                missing.append(_quote_body_text(u)[:36])
        if missing:
            out.append(_f(rule, "fail",
                          f"{len(missing)} unattributed quote(s): "
                          + "; ".join(f"'{t}…'" for t in missing[:3]), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(units)} quote(s) all attributed", sec.sid))
    return out


def check_quote_04(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("quote")
    if not secs:
        return [_f(rule, "skip", "no quote section")]
    out = []
    for sec in secs:
        units = _quote_units(sec)
        if not units:
            out.append(_f(rule, "skip", "no quote units rendered", sec.sid))
            continue
        bad = []
        for u in units:
            n = len(_words(_quote_body_text(u)))
            if not 10 <= n <= 70:
                bad.append(f"{n}w '{_quote_body_text(u)[:30]}…'")
        if bad:
            out.append(_f(rule, "fail",
                          f"{len(bad)} quote(s) outside 10-70 words: "
                          + "; ".join(bad[:3]), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(units)} quote(s) within 10-70 words", sec.sid))
    return out


# ── checkers: feature-grid ───────────────────────────────────────────────────────

def _grid_cell_slots(cell) -> frozenset:
    slots = set()
    if cell.select_one("img, svg, .c-image"):
        slots.add("media")
    if cell.select_one(".c-eyebrow"):
        slots.add("eyebrow")
    if cell.select_one("h3, h4, h5, .c-heading, .cs-module-title"):
        slots.add("heading")
    for p in cell.select("p"):
        if not re.search(r"c-eyebrow|c-caption|c-person",
                         " ".join(p.get("class") or [])) and _txt(p):
            slots.add("body")
            break
    if cell.select_one("a"):
        slots.add("link")
    return frozenset(slots)


def _feature_cells(sec: SectionCtx) -> tuple[list, list, list]:
    """(plain cells, bento supporting cells, bento lead cells). The bento lead
    is the ``--lead``-stamped cell; when no stamp exists, a FIRST cell whose
    anatomy strictly supersets its siblings' shared set is the de-facto lead
    (SR-GRID-01: 'its richer anatomy is the device') — a divergent middle cell
    still fails parity."""
    cells, bento = _grid_cells(sec.node)
    lead = [c for c in bento
            if "cs-bento-cell--lead" in (c.get("class") or [])]
    support = [c for c in bento if c not in lead]
    if bento and not lead and len(support) >= 3:
        first, rest = support[0], support[1:]
        rest_sets = {_grid_cell_slots(c) for c in rest}
        if len(rest_sets) == 1:
            shared = next(iter(rest_sets))
            if _grid_cell_slots(first) > shared:
                lead, support = [first], rest
    return cells, support, lead


def check_grid_01(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("feature-grid")
    if not secs:
        return [_f(rule, "skip", "no feature grid")]
    out = []
    for sec in secs:
        cells, support, _lead = _feature_cells(sec)
        groups = [g for g in (cells, support) if len(g) >= 2]
        if not groups:
            out.append(_f(rule, "skip", "fewer than 2 comparable cells",
                          sec.sid))
            continue
        problems = []
        for group in groups:
            sets = [_grid_cell_slots(c) for c in group]
            if len(set(sets)) > 1:
                detail = "; ".join(f"cell {i+1}: {{{', '.join(sorted(s)) or '-'}}}"
                                   for i, s in enumerate(sets))
                problems.append(detail)
        if problems:
            out.append(_f(rule, "fail",
                          "cell anatomy differs — " + " | ".join(problems),
                          sec.sid))
        else:
            n = sum(len(g) for g in groups)
            out.append(_f(rule, "pass",
                          f"{n} cell(s) share slot anatomy (bento lead exempt)",
                          sec.sid))
    return out


def _grid_headings(sec: SectionCtx) -> list[str]:
    cells, support, lead = _feature_cells(sec)
    out = []
    for c in cells + support + lead:
        h = c.select_one("h3, h4, h5, .c-heading, .cs-module-title")
        if h is not None and _txt(h):
            out.append(_txt(h))
    return out


def check_grid_02(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("feature-grid")
    if not secs:
        return [_f(rule, "skip", "no feature grid")]
    out = []
    for sec in secs:
        heads = _grid_headings(sec)
        if len(heads) < 2:
            out.append(_f(rule, "skip", "fewer than 2 cell headings", sec.sid))
            continue
        counts = [len(_words(h)) for h in heads]
        problems = []
        outside = [h for h, n in zip(heads, counts) if not 1 <= n <= 8]
        if outside:
            problems.append(f"{len(outside)} heading(s) outside 1-8 words: "
                            + "; ".join(f"'{h[:32]}'" for h in outside[:3]))
        if min(counts) and max(counts) / min(counts) > 3:
            problems.append(f"word spread {max(counts)}/{min(counts)} > 3x")
        if _casing_conflict([_casing_class(h) for h in heads]):
            problems.append("mixed casing rules")
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(heads)} parallel cell heading(s)", sec.sid))
    return out


def check_grid_03(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("feature-grid")
    if not secs:
        return [_f(rule, "skip", "no feature grid")]
    out = []
    for sec in secs:
        cells, support, lead = _feature_cells(sec)
        bodies = []
        for c in cells + support + lead:
            ps = [p for p in c.select("p")
                  if not re.search(r"c-eyebrow|c-caption|c-person",
                                   " ".join(p.get("class") or [])) and _txt(p)]
            if ps:
                bodies.append(" ".join(_txt(p) for p in ps))
        if len(bodies) < 2:
            out.append(_f(rule, "skip", "fewer than 2 cell bodies", sec.sid))
            continue
        problems = []
        sent_counts = [len(_sentences(b)) or 1 for b in bodies]
        outside = [n for n in sent_counts if not 1 <= n <= 3]
        if outside:
            problems.append(f"sentence counts outside 1-3: {outside}")
        word_counts = [len(_words(b)) for b in bodies]
        if min(word_counts) and max(word_counts) / min(word_counts) > 2.5:
            problems.append(
                f"body depth spread {max(word_counts)}/{min(word_counts)}w > 2.5x")
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(bodies)} cell bodies parallel in depth",
                          sec.sid))
    return out


def check_grid_04(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("feature-grid")
    if not secs:
        return [_f(rule, "skip", "no feature grid")]
    if lane.geometry is None:
        return [_geo_skip(rule)]
    out = []
    for sec in secs:
        icons = lane.geo(sec).get("icons") or []
        if len(icons) < 2:
            out.append(_f(rule, "skip", "fewer than 2 cell icons", sec.sid))
            continue
        heights = sorted(i["h"] for i in icons)
        med = statistics.median(heights)
        off = [h for h in heights if med and abs(h - med) / med > 0.10]
        if off:
            out.append(_f(rule, "fail",
                          f"{len(off)}/{len(icons)} icon box(es) beyond ±10% of "
                          f"median {med:.0f}px: {sorted(set(off))}", sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(icons)} icon box(es) uniform (median "
                          f"{med:.0f}px ±10%)", sec.sid))
    return out


# ── checkers: faq ────────────────────────────────────────────────────────────────

def _faq_items(sec: SectionCtx) -> list:
    return sec.node.select("details")


def _trigger_text(d) -> str:
    s = d.find("summary")
    t = _txt(s) if s else ""
    return re.sub(r"[\s+\-–—›»^v↓]+$", "", t).strip()


def _answer_text(d) -> str:
    s = d.find("summary")
    full = _txt(d)
    if s:
        st = _txt(s)
        if full.startswith(st):
            full = full[len(st):]
    return full.strip()


def check_faq_01(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("faq")
    if not secs:
        return [_f(rule, "skip", "no FAQ")]
    out = []
    for sec in secs:
        triggers = [_trigger_text(d) for d in _faq_items(sec)]
        triggers = [t for t in triggers if t]
        if not triggers:
            out.append(_f(rule, "skip", "no accordion triggers", sec.sid))
            continue
        bad = []
        for t in triggers:
            first = (_words(t)[0].lower() if _words(t) else "")
            if not (t.rstrip().endswith("?") or first in _INTERROGATIVES):
                bad.append(t[:44])
        if bad:
            out.append(_f(rule, "fail",
                          f"{len(bad)}/{len(triggers)} statement trigger(s): "
                          + "; ".join(f"'{t}'" for t in bad[:3]), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(triggers)} trigger(s) all question-form",
                          sec.sid))
    return out


def check_faq_02(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("faq")
    if not secs:
        return [_f(rule, "skip", "no FAQ")]
    out = []
    for sec in secs:
        answers = [_answer_text(d) for d in _faq_items(sec)]
        answers = [a for a in answers if a]
        if not answers:
            out.append(_f(rule, "skip", "no answer bodies", sec.sid))
            continue
        bad = [f"{len(_words(a))}w '{a[:30]}…'" for a in answers
               if not 15 <= len(_words(a)) <= 120]
        if bad:
            out.append(_f(rule, "fail",
                          f"{len(bad)} answer(s) outside 15-120 words: "
                          + "; ".join(bad[:3]), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(answers)} answer(s) within 15-120 words",
                          sec.sid))
    return out


def check_faq_03(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("faq")
    if not secs:
        return [_f(rule, "skip", "no FAQ")]
    out = []
    for sec in secs:
        n = len(_faq_items(sec))
        if not n:
            out.append(_f(rule, "skip", "no accordion items", sec.sid))
        elif 3 <= n <= 8:
            out.append(_f(rule, "pass", f"{n} item(s)", sec.sid))
        else:
            out.append(_f(rule, "fail", f"{n} item(s) (band budget 3-8)",
                          sec.sid))
    return out


def check_faq_04(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("faq")
    if not secs:
        return [_f(rule, "skip", "no FAQ")]
    out = []
    for sec in secs:
        items = _faq_items(sec)
        if not items:
            out.append(_f(rule, "skip", "no accordion items", sec.sid))
            continue
        with_link = 0
        for d in items:
            links = [a for a in d.select("a") if a.find_parent("summary") is None]
            if links:
                with_link += 1
        if with_link * 3 > len(items):
            out.append(_f(rule, "fail",
                          f"{with_link}/{len(items)} answers carry action links "
                          "(> 1/3)", sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{with_link}/{len(items)} answers with links (<= 1/3)",
                          sec.sid))
    return out


# ── checkers: cta-band ───────────────────────────────────────────────────────────

def check_cta_01(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("cta-band")
    if not secs:
        return [_f(rule, "skip", "no CTA band")]
    out = []
    for sec in secs:
        problems = []
        support = [p for p in sec.node.select("p")
                   if "c-paragraph" in (p.get("class") or [])
                   and p.find_parent("form") is None]
        n_words = sum(len(_words(_txt(p))) for p in support)
        if len(support) > 1:
            problems.append(f"{len(support)} support paragraphs (one decision "
                            "moment wants at most 1)")
        if n_words > 30:
            problems.append(f"support copy {n_words}w (max 30)")
        devices = []
        for selector, label in ((".cs-modules", "card grid"),
                                (".cs-bento", "bento grid"),
                                (".cs-tiers", "tier band")):
            if sec.node.select_one(selector):
                devices.append(label)
        for ul in sec.node.select("ul, ol"):
            if ul.find_parent("form") is None and \
                    ul.find_parent(class_="cs-navlinks") is None:
                devices.append("list")
                break
        if devices:
            problems.append("competing device(s) in the band: "
                            + ", ".join(sorted(set(devices))))
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"one decision moment ({n_words}w support)", sec.sid))
    return out


def check_cta_03(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("cta-band")
    if not secs:
        return [_f(rule, "skip", "no CTA band")]
    out = []
    for sec in secs:
        actions = [b for b in sec.node.select(".c-button")
                   if "c-arrow-link" not in (b.get("class") or [])]
        primary = next((b for b in actions if _is_filled_button(b)),
                       actions[0] if actions else None)
        if primary is None:
            out.append(_f(rule, "skip", "no band action", sec.sid))
            continue
        label = _txt(primary)
        ws = _words(label)
        problems = []
        if not 2 <= len(ws) <= 5:
            problems.append(f"'{label}' is {len(ws)} word(s) (budget 2-5)")
        if ws and ws[0].lower().strip(".,!?") in _NON_VERB_LEADS:
            problems.append(f"'{label}' leads with a non-verb")
        if problems:
            out.append(_f(rule, "fail", "; ".join(problems), sec.sid))
        else:
            out.append(_f(rule, "pass", f"primary label '{label}' verb-led, "
                                        f"{len(ws)} words", sec.sid))
    return out


# ── checkers: chrome (nav / footer fact parity) ──────────────────────────────────

def _nav_rendered_labels(nav) -> list[str]:
    labels = []
    for child in nav.select(".cs-navlinks > *"):
        lab = child.select_one("summary, button, a") or child
        direct = "".join(t for t in lab.find_all(string=True, recursive=False))
        t = re.sub(r"\s+", " ", direct).strip()
        if not t:
            t = _txt(lab).split("  ")[0].strip()
        if t:
            labels.append(t)
    return labels


def check_nav_01(rule: dict, lane: LaneCtx) -> list[dict]:
    nav = lane.chrome.get("nav")
    if nav is None:
        return [_f(rule, "skip", "no nav chrome on this lane")]
    facts = [str((l or {}).get("label") or "")
             for l in ((lane.brand.get("navbar") or {}).get("primary") or [])]
    facts = [f for f in facts if f]
    if not facts:
        return [_f(rule, "skip", "no harvested navbar facts (fact-gated)")]
    rendered = _nav_rendered_labels(nav)
    invented = [r for r in rendered if r not in facts]
    dropped = [f for f in facts if f not in rendered]
    if invented or dropped:
        return [_f(rule, "fail",
                   (f"invented: {invented[:4]} " if invented else "")
                   + (f"dropped: {dropped[:4]}" if dropped else ""))]
    return [_f(rule, "pass",
               f"{len(rendered)} primary-bar label(s) match the harvested "
               "roster")]


def check_nav_03(rule: dict, lane: LaneCtx) -> list[dict]:
    nav = lane.chrome.get("nav")
    if nav is None:
        return [_f(rule, "skip", "no nav chrome on this lane")]
    facts = ((lane.brand.get("navbar") or {}).get("primary") or [])
    if facts:
        return [_f(rule, "override",
                   "harvested chrome — measured labels are brand evidence "
                   "(navbar.primary cited)")]
    rendered = _nav_rendered_labels(nav)
    if not rendered:
        return [_f(rule, "skip", "no rendered nav labels")]
    bad = []
    for r in rendered:
        ws = _words(r)
        if len(ws) > 3 or re.search(r"[.!?]$", r) \
                or (ws and ws[-1].lower() in _URGENCY_TAILS):
            bad.append(r)
    if bad:
        return [_f(rule, "fail", f"{len(bad)} pitchy label(s): "
                                 + "; ".join(f"'{b}'" for b in bad[:4]))]
    return [_f(rule, "pass", f"{len(rendered)} destination label(s)")]


def _footer_rendered(foot) -> dict:
    groups = foot.select(".c-foot-col")
    heads = []
    for g in groups:
        h = g.select_one(".c-foot-col-head")
        heads.append(_txt(h) if h else "")
    social = foot.select(".c-foot-glyph, [class*=social] a")
    return {"groups": len(groups), "heads": heads, "social": len(social),
            "legal": foot.select_one(".c-foot-legal") is not None}


def check_foot_01(rule: dict, lane: LaneCtx) -> list[dict]:
    foot = lane.chrome.get("footer")
    if foot is None:
        return [_f(rule, "skip", "no footer chrome on this lane")]
    fb = lane.brand.get("footer") or {}
    cols = fb.get("columns") or []
    if not cols:
        return [_f(rule, "skip", "no harvested footer facts (fact-gated)")]
    r = _footer_rendered(foot)
    fact_heads = [str((c or {}).get("heading") or "") for c in cols]
    problems = []
    if r["groups"] != len(cols):
        problems.append(f"column groups {r['groups']} != harvested {len(cols)}")
    if sorted(h.lower() for h in r["heads"]) != \
            sorted(h.lower() for h in fact_heads):
        problems.append(f"group headings drift: rendered {r['heads'][:6]} vs "
                        f"facts {fact_heads[:6]}")
    n_social = len(fb.get("social") or [])
    if n_social and r["social"] != n_social:
        problems.append(f"social roster {r['social']} != harvested {n_social}")
    if fb.get("legal") and not r["legal"]:
        problems.append("harvested legal line missing")
    if problems:
        return [_f(rule, "fail", "; ".join(problems))]
    return [_f(rule, "pass",
               f"{r['groups']} column group(s), {r['social']} social mark(s), "
               "legal line — all match the harvested anatomy")]


def check_foot_02(rule: dict, lane: LaneCtx) -> list[dict]:
    foot = lane.chrome.get("footer")
    if foot is None:
        return [_f(rule, "skip", "no footer chrome on this lane")]
    fb = lane.brand.get("footer") or {}
    r = _footer_rendered(foot)
    if r["legal"]:
        return [_f(rule, "pass", "legal register line present")]
    if fb and not fb.get("legal"):
        return [_f(rule, "override",
                   "the measured footer carries no legal line (evidence cited)")]
    return [_f(rule, "fail", "no legal register line in the footer")]


# ── checkers: carousel ───────────────────────────────────────────────────────────

def _carousel_items(sec: SectionCtx) -> list:
    ec = sec.node.select_one(".cs-edgecut")
    if ec is not None:
        return ec.select(".cs-module")
    pc = sec.node.select_one(".cs-panelcar")
    if pc is not None:
        return pc.select("[class*=panel], [class*=slide]") or \
            pc.find_all(recursive=False)
    mq = sec.node.select_one(".cs-marquee")
    if mq is not None:
        return mq.select(".cs-logo-strip-item")
    return []


def check_car_01(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("carousel")
    if not secs:
        return [_f(rule, "skip", "no carousel")]
    out = []
    for sec in secs:
        items = _carousel_items(sec)
        if len(items) < 2:
            out.append(_f(rule, "skip", "fewer than 2 slides", sec.sid))
            continue
        sets = [_grid_cell_slots(i) for i in items]
        if len(set(sets)) > 1:
            out.append(_f(rule, "fail",
                          "slide anatomy differs: "
                          + "; ".join(f"slide {i+1} {{{', '.join(sorted(s)) or '-'}}}"
                                      for i, s in enumerate(sets[:5])), sec.sid))
        else:
            out.append(_f(rule, "pass",
                          f"{len(items)} slide(s) share anatomy", sec.sid))
    return out


def check_car_02(rule: dict, lane: LaneCtx) -> list[dict]:
    secs = lane.by_family("carousel")
    if not secs:
        return [_f(rule, "skip", "no carousel")]
    out = []
    for sec in secs:
        n = len(_carousel_items(sec))
        if n >= 3:
            out.append(_f(rule, "pass", f"{n} item(s)", sec.sid))
        elif n:
            out.append(_f(rule, "fail",
                          f"{n} item(s) — a 2-frame carousel is a split "
                          "wearing controls", sec.sid))
        else:
            out.append(_f(rule, "skip", "no carousel items", sec.sid))
    return out


# ── registry + lane audit ────────────────────────────────────────────────────────

CHECKERS = {
    "SR-HDR-01": check_hdr_01, "SR-HDR-02": check_hdr_02,
    "SR-HERO-01": check_hero_01, "SR-HERO-02": check_hero_02,
    "SR-HERO-04": check_hero_04, "SR-HERO-05": check_hero_05,
    "SR-STAT-01": check_stat_01, "SR-STAT-02": check_stat_02,
    "SR-STAT-03": check_stat_03, "SR-STAT-04": check_stat_04,
    "SR-LOGO-01": check_logo_01, "SR-LOGO-02": check_logo_02,
    "SR-LOGO-04": check_logo_04,
    "SR-FORM-01": check_form_01, "SR-FORM-04": check_form_04,
    "SR-FORM-05": check_form_05, "SR-FORM-06": check_form_06,
    "SR-TIER-01": check_tier_01, "SR-TIER-02": check_tier_02,
    "SR-TIER-03": check_tier_03, "SR-TIER-04": check_tier_04,
    "SR-TIER-05": check_tier_05,
    "SR-QUOTE-01": check_quote_01, "SR-QUOTE-02": check_quote_02,
    "SR-QUOTE-04": check_quote_04,
    "SR-GRID-01": check_grid_01, "SR-GRID-02": check_grid_02,
    "SR-GRID-03": check_grid_03, "SR-GRID-04": check_grid_04,
    "SR-FAQ-01": check_faq_01, "SR-FAQ-02": check_faq_02,
    "SR-FAQ-03": check_faq_03, "SR-FAQ-04": check_faq_04,
    "SR-CTA-01": check_cta_01, "SR-CTA-03": check_cta_03,
    "SR-NAV-01": check_nav_01, "SR-NAV-03": check_nav_03,
    "SR-FOOT-01": check_foot_01, "SR-FOOT-02": check_foot_02,
    "SR-CAR-01": check_car_01, "SR-CAR-02": check_car_02,
}


def audit_lane_html(lane_dir: Path, html: Path, rules_doc: dict,
                    brand_doc: dict, geometry: dict | None) -> dict:
    lane = LaneCtx(lane_dir, html, brand_doc, geometry)
    entry: dict = {"scope": lane.scope,
                   "sections": {s.sid: sorted(s.families)
                                for s in lane.sections},
                   "findings": []}
    rules = rules_doc.get("rules") or []

    if lane.scope == "replica":
        entry["findings"].append(
            {"rule": "*", "scope": "*", "severity": "advisory",
             "verdict": "skip",
             "detail": "replica lane — evidence, never an audit target "
                       "(section-rules lane scope)"})
        return entry
    if lane.scope == "specimen":
        entry["findings"].append(
            {"rule": "*", "scope": "*", "severity": "advisory",
             "verdict": "skip",
             "detail": "specimen/preview lane — page-scoped rules skip"})
        return entry

    present = set()
    for s in lane.sections:
        present |= s.families
    if lane.chrome.get("nav") is not None:
        present.add("nav")
    if lane.chrome.get("footer") is not None:
        present.add("footer")

    for fam in (*CONTENT_FAMILIES, *CHROME_FAMILIES):
        if fam not in present:
            entry["findings"].append(
                {"rule": fam, "scope": fam, "severity": "advisory",
                 "verdict": "skip", "detail": "family absent on this lane"})

    for rule in rules:
        fam = rule.get("scope")
        if fam not in present:
            continue
        if rule.get("enforcement") == "delegated":
            entry["findings"].append(_f(
                rule, "delegated",
                "enforced by " + ", ".join(str(t) for t in
                                           (rule.get("delegatedTo") or []))))
            continue
        fn = CHECKERS.get(rule["id"])
        if fn is None:
            entry["findings"].append(_f(rule, "skip",
                                        "no checker implemented (reported, "
                                        "never silent)"))
            continue
        try:
            entry["findings"].extend(fn(rule, lane))
        except Exception as exc:  # checker crash = lane error, not silence
            entry["findings"].append(_f(rule, "error",
                                        f"{type(exc).__name__}: {exc}"[:200]))
    return entry


def run_audit(lane_paths: list[Path], brand_dir: Path, out_dir: Path | None,
              static_only: bool = False, viewport=DEFAULT_VIEWPORT) -> dict:
    rules_doc = load_rules()
    brand_doc = {}
    by = brand_dir / "brand.yaml"
    if by.exists():
        brand_doc = yaml.safe_load(by.read_text()) or {}
    report = {"generatedAt": datetime.now(timezone.utc)
              .strftime("%Y-%m-%dT%H:%M:%SZ"),
              "brandDir": str(brand_dir),
              "rules": len(rules_doc.get("rules") or []),
              "staticOnly": static_only, "lanes": []}

    pw_ctx = None
    pw = None
    try:
        if not static_only:
            from playwright.sync_api import sync_playwright
            pw_ctx = sync_playwright()
            pw = pw_ctx.__enter__()
        for html in lane_paths:
            lane_dir = html.parent
            lane = str(lane_dir.relative_to(brand_dir)) \
                if brand_dir in lane_dir.parents else str(lane_dir)
            entry: dict = {"lane": lane, "html": str(html)}
            if not html.exists():
                entry["error"] = "file not found"
                report["lanes"].append(entry)
                continue
            geometry = None
            if pw is not None and lane_scope(lane_dir) == "generative":
                try:
                    geometry = measure_lane(pw, html, viewport)
                except Exception as exc:
                    entry["error"] = f"geometry: {type(exc).__name__}: {exc}"[:300]
                    report["lanes"].append(entry)
                    continue
            entry.update(audit_lane_html(lane_dir, html, rules_doc, brand_doc,
                                         geometry))
            report["lanes"].append(entry)
    finally:
        if pw_ctx is not None:
            pw_ctx.__exit__(None, None, None)

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(json.dumps(report, indent=2))
        (out_dir / "report.md").write_text(render_md(report))
    return report


def lane_verdict(entry: dict) -> tuple[str, int, int]:
    """(PASS/FAIL, required fails, advisory warns) for one lane entry."""
    req = sum(1 for f in entry.get("findings", [])
              if f["verdict"] in ("fail", "error")
              and f.get("severity") == "required")
    adv = sum(1 for f in entry.get("findings", [])
              if f["verdict"] in ("fail", "error")
              and f.get("severity") != "required")
    return ("FAIL" if req else "PASS", req, adv)


def render_md(report: dict) -> str:
    lines = ["# Section-rules audit (section-rules.v1)", "",
             f"Brand: `{report['brandDir']}` · {report['rules']} rules · "
             f"{report['generatedAt']}"
             + (" · STATIC ONLY" if report.get("staticOnly") else ""), ""]
    for lane in report["lanes"]:
        if lane.get("error"):
            lines.append(f"## {lane['lane']} — ERROR: {lane['error']}\n")
            continue
        verdict, req, adv = lane_verdict(lane)
        lines.append(f"## {lane['lane']} — {verdict} "
                     f"({req} required fail(s), {adv} advisory warn(s)) — "
                     f"scope: {lane.get('scope')}\n")
        rows = [f for f in lane["findings"]
                if f["verdict"] not in ("skip", "delegated")]
        skips = [f for f in lane["findings"] if f["verdict"] == "skip"]
        delegated = [f for f in lane["findings"] if f["verdict"] == "delegated"]
        if rows:
            lines.append("| rule | scope | sev | verdict | detail |")
            lines.append("|---|---|---|---|---|")
            for f in rows:
                lines.append(f"| `{f['rule']}` | {f['scope']} | "
                             f"{f['severity'][:3]} | "
                             f"{f['verdict'].upper()} | "
                             f"{f.get('sec', '')} {f['detail']} |")
            lines.append("")
        if delegated:
            lines.append(f"delegated: {', '.join(sorted({f['rule'] for f in delegated}))}")
        if skips:
            lines.append(f"skips: {len(skips)} "
                         f"({', '.join(sorted({f['rule'] for f in skips})[:12])})")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lanes", nargs="+",
                    help="lane dirs (index.html assumed) or .html files")
    ap.add_argument("--brand", type=Path, required=True,
                    help="brand run dir (brand.yaml)")
    ap.add_argument("--out", type=Path, default=None,
                    help="report dir (default <brand>/section-rules-baseline)")
    ap.add_argument("--viewport", default="1440x900")
    ap.add_argument("--static-only", action="store_true",
                    help="skip the Playwright geometry layer")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on failing required rows / lane errors")
    args = ap.parse_args(argv)
    w, h = (int(x) for x in args.viewport.lower().split("x"))
    paths = [(Path(l) / "index.html") if Path(l).is_dir() else Path(l)
             for l in args.lanes]
    out_dir = args.out or (args.brand / "section-rules-baseline")
    report = run_audit(paths, args.brand, out_dir, static_only=args.static_only,
                       viewport=(w, h))

    hard = 0
    for lane in report["lanes"]:
        if lane.get("error"):
            hard += 1
            print(f"[section-rules] {lane['lane']}: ERROR {lane['error']}",
                  file=sys.stderr)
            continue
        verdict, req, adv = lane_verdict(lane)
        hard += req
        fams = {f["rule"] for f in lane["findings"]
                if f["verdict"] in ("fail", "error")}
        extra = f" [{', '.join(sorted(fams))}]" if fams else ""
        print(f"[section-rules] {lane['lane']}: {verdict} — {req} required "
              f"fail(s), {adv} advisory warn(s) (scope {lane.get('scope')})"
              + extra)
    if out_dir:
        print(f"[section-rules] report: {out_dir / 'report.md'}")
    return 1 if (args.strict and hard) else 0


if __name__ == "__main__":
    sys.exit(main())
