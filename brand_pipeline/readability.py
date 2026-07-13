#!/usr/bin/env python3
"""readability.py — static READABILITY + DECORATION-SALIENCE analysis for the on-brand gate.

Motivating failure: the v4 "ghost" hero rendered a huge near-cream WOODWAVE watermark on
the dark hero surface, bright enough to visually drown the gold display heading and the
small text around it — and nothing in the gate measured contrast, so it passed. This
module adds the two mechanical checks `onbrand_check.py` wires into the composition
invariant set:

  1. text-contrast       — every REAL text element (headings, paragraphs, captions, CTA
                           labels — not aria-hidden decorations) must clear a WCAG-ish
                           contrast ratio against its EFFECTIVE background: the nearest
                           painted ancestor background (section surface, cream panel, …)
                           additionally composited with any decoration layer that sits
                           behind text in the same section (ghost word / watermark).
                           Thresholds: >= 3.0 for display-scale text (resolved font-size
                           >= 24px), >= 4.5 for body/small text.
  2. decoration-salience — decorative layers (ghost-word / watermark treatments, i.e. the
                           `.cs-ghost` element the composers emit) must stay CLOSE to the
                           surface they sit on: the contrast ratio between the decoration
                           composited over its surface and the bare surface must stay
                           below a small ceiling. The known-good 6%-ink ghost on cream
                           measures 1.124; the v4 bright-cream ghost on the dark hero
                           measures 1.256; the ceiling sits centered between them at 1.19.

Everything is computed STATICALLY from the emitted HTML: a DOM-lite tree (html.parser), a
CSS-cascade-lite over the page's <style> blocks (specificity + document order, desktop
state only — max-width/media blocks are skipped), and CSS custom-property resolution that
walks the element's ancestor chain (so `#sec-N { --c-ink: … }` and the cream panel's
`--c-ink` re-scoping both resolve correctly). The analysis is deliberately CONSERVATIVE:
any element whose color or background cannot be confidently resolved statically is
SKIPPED (reported in the detail), never failed — so bespoke markup can't produce false
FAILs. A headless pixel-sample fallback was considered and intentionally NOT wired in:
the static path resolves every page in the current corpus.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

# ── thresholds (tuned against the known-good corpus; see module docstring) ────────
TEXT_CONTRAST_DISPLAY_MIN = 3.0   # display-scale text (resolved font-size >= 24px)
TEXT_CONTRAST_BODY_MIN = 4.5      # body / small text
DISPLAY_PX_FLOOR = 24.0           # WCAG "large text" floor (18pt)
DECOR_SALIENCE_MAX_RATIO = 1.19   # decoration composite vs its surface: centered between
                                  # the known-good corpus (6%-ink ghost on cream = 1.124,
                                  # PASSES) and the v4 dark-hero bright-cream ghost (1.256,
                                  # FAILS) with ~5% margin on each side

# class-name signature of a decoration layer (what the composers emit for ghost-word /
# watermark treatments: `.cs-ghost`, `.cs-ghost--numerals`), plus generic ghost/watermark
# names so AI-authored bespoke decorations are still caught.
_DECOR_CLASS_RE = re.compile(r"(?:^|-)?(?:ghost|watermark)(?:$|[-_])|^cs-ghost", re.I)

_VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
              "meta", "param", "source", "track", "wbr"}
_SKIP_SUBTREES = {"script", "style", "svg", "head", "title", "noscript", "template"}

_NAMED_COLORS = {
    "white": (255, 255, 255, 1.0), "black": (0, 0, 0, 1.0),
    "transparent": (0, 0, 0, 0.0),
}


# ── color math ────────────────────────────────────────────────────────────────────

def parse_color(value):
    """Parse a CSS color literal -> (r, g, b, a) floats, or None if not a literal color.

    Supports #rgb/#rrggbb/#rrggbbaa, rgb()/rgba() and a tiny named set. `currentcolor`
    and unresolved var()/keywords return None (the caller handles inheritance/skip)."""
    if not value:
        return None
    v = value.strip().lower()
    if v in _NAMED_COLORS:
        return _NAMED_COLORS[v]
    m = re.fullmatch(r"#([0-9a-f]{3})", v)
    if m:
        r, g, b = (int(c * 2, 16) for c in m.group(1))
        return (r, g, b, 1.0)
    m = re.fullmatch(r"#([0-9a-f]{6})([0-9a-f]{2})?", v)
    if m:
        h = m.group(1)
        a = int(m.group(2), 16) / 255.0 if m.group(2) else 1.0
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)"
                     r"(?:\s*,\s*([\d.]+%?))?\s*\)", v)
    if m:
        r, g, b = float(m.group(1)), float(m.group(2)), float(m.group(3))
        a = m.group(4)
        if a is None:
            alpha = 1.0
        elif a.endswith("%"):
            alpha = float(a[:-1]) / 100.0
        else:
            alpha = float(a)
        return (r, g, b, max(0.0, min(1.0, alpha)))
    return None


def composite(fg, bg):
    """Source-over composite an (r,g,b,a) foreground onto an opaque (r,g,b) background."""
    r, g, b, a = fg
    return (r * a + bg[0] * (1 - a),
            g * a + bg[1] * (1 - a),
            b * a + bg[2] * (1 - a))


def rel_luminance(rgb):
    """WCAG relative luminance of an opaque (r,g,b)."""
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb1, rgb2):
    """WCAG contrast ratio (>= 1.0) between two opaque colors."""
    y1, y2 = rel_luminance(rgb1), rel_luminance(rgb2)
    hi, lo = max(y1, y2), min(y1, y2)
    return (hi + 0.05) / (lo + 0.05)


def hex_of(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(int(round(max(0, min(255, c)))) for c in rgb[:3]))


# ── DOM-lite ────────────────────────────────────────────────────────────────────────


class _Node:
    __slots__ = ("tag", "attrs", "classes", "parent", "children", "texts", "style")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.classes = set((attrs.get("class") or "").split())
        self.parent = parent
        self.children = []
        self.texts = []
        # inline style declarations (highest cascade priority)
        self.style = _parse_decls(attrs.get("style") or "")

    def direct_text(self):
        return " ".join(t.strip() for t in self.texts if t.strip())

    def ancestors(self):
        n = self.parent
        while n is not None:
            yield n
            n = n.parent

    def is_hidden(self):
        n = self
        while n is not None:
            if (n.attrs.get("aria-hidden") or "").lower() == "true":
                return True
            n = n.parent
        return False


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("#document", {}, None)
        self.stack = [self.root]
        self.styles = []
        self._in_skip = 0
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in _SKIP_SUBTREES:
            self._in_skip += 1
            if tag == "style":
                self._in_style = True
            return
        node = _Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in _VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        if tag in _SKIP_SUBTREES:
            return
        self.stack[-1].children.append(_Node(tag, dict(attrs), self.stack[-1]))

    def handle_endtag(self, tag):
        if tag in _SKIP_SUBTREES:
            self._in_skip = max(0, self._in_skip - 1)
            if tag == "style":
                self._in_style = False
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._in_style:
            self.styles.append(data)
        elif not self._in_skip and data.strip():
            self.stack[-1].texts.append(data)


def _walk(node):
    yield node
    for c in node.children:
        yield from _walk(c)


# ── CSS-cascade-lite ────────────────────────────────────────────────────────────────

def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.S)


def _parse_decls(body):
    decls = {}
    for part in body.split(";"):
        if ":" not in part:
            continue
        prop, _, val = part.partition(":")
        prop = prop.strip().lower()
        val = val.strip()
        if prop and val:
            decls[prop] = val
    return decls


# a compound = one element's worth of simple selectors; unsupported pseudo => rule skipped
_UNSUPPORTED_PSEUDO_RE = re.compile(
    r"::|:hover|:focus|:active|:visited|:checked|:first-child|:last-child|:nth-|:not\(|:where\(")


def _split_selector(sel):
    """Split a single selector into descendant compounds ('>' treated as descendant).
    Returns None when the selector uses combinators/pseudos we don't model."""
    sel = sel.strip()
    if not sel or "+" in sel or "~" in sel or _UNSUPPORTED_PSEUDO_RE.search(sel):
        return None
    sel = sel.replace(">", " ")
    # protect whitespace inside :is(...) / attribute brackets while splitting
    out, depth, cur = [], 0, ""
    for ch in sel:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch.isspace() and depth == 0:
            if cur:
                out.append(cur)
                cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out or None


_SIMPLE_RE = re.compile(
    r"(?P<tag>^[a-zA-Z][a-zA-Z0-9-]*)|"
    r"\#(?P<id>[A-Za-z0-9_-]+)|"
    r"\.(?P<cls>[A-Za-z0-9_-]+)|"
    r"\[(?P<attr>[A-Za-z0-9_-]+)(?:(?P<op>[~^|$*]?=)[\"']?(?P<val>[^\"'\]]*)[\"']?)?\]|"
    r":(?P<pseudo>root|is\([^)]*\))")


def _match_compound(compound, node):
    """Does one compound (e.g. `div#sec-0.cs-surface[data-layout^="hero-"]`) match node?"""
    pos = 0
    matched_any = False
    while pos < len(compound):
        m = _SIMPLE_RE.match(compound, pos)
        if not m:
            return False  # unparseable simple selector -> no match (conservative)
        pos = m.end()
        matched_any = True
        if m.group("tag"):
            if node.tag != m.group("tag").lower():
                return False
        elif m.group("id"):
            if node.attrs.get("id") != m.group("id"):
                return False
        elif m.group("cls"):
            if m.group("cls") not in node.classes:
                return False
        elif m.group("attr"):
            got = node.attrs.get(m.group("attr").lower())
            if got is None:
                return False
            op, want = m.group("op"), m.group("val") or ""
            if op == "=" and got != want:
                return False
            if op == "^=" and not got.startswith(want):
                return False
            if op == "$=" and not got.endswith(want):
                return False
            if op == "*=" and want not in got:
                return False
            if op == "~=" and want not in got.split():
                return False
        elif m.group("pseudo"):
            p = m.group("pseudo")
            if p == "root":
                if node.tag != "html":
                    return False
            elif p.startswith("is("):
                alts = p[3:-1].split(",")
                if not any(_match_compound(a.strip(), node) for a in alts if a.strip()):
                    return False
    return matched_any


def _specificity(sel):
    ids = len(re.findall(r"#[A-Za-z0-9_-]+", sel))
    classes = len(re.findall(r"\.[A-Za-z0-9_-]+|\[[^\]]*\]|:(?!:)[a-z-]+", sel))
    tags = len(re.findall(r"(?:^|[\s>+~(,])([a-zA-Z][a-zA-Z0-9-]*)", sel))
    return (ids, classes, tags)


class Stylesheet:
    """All desktop-state rules from the page's <style> blocks, in cascade order."""

    def __init__(self, css_text):
        self.rules = []  # (compounds, specificity, order, decls)
        order = 0
        for sel_text, body in self._iter_rules(_strip_comments(css_text)):
            decls = _parse_decls(body)
            if not decls:
                continue
            for sel in sel_text.split(","):
                compounds = _split_selector(sel)
                if compounds:
                    self.rules.append((compounds, _specificity(sel), order, decls))
                    order += 1

    @staticmethod
    def _iter_rules(css):
        """Yield (selector, body) for top-level rules; skip @-blocks entirely (media
        queries, font-face, keyframes) — the gate evaluates the DESKTOP default state."""
        i, n = 0, len(css)
        while i < n:
            brace = css.find("{", i)
            if brace == -1:
                break
            sel = css[i:brace].strip()
            # find the matching closing brace
            depth, j = 1, brace + 1
            while j < n and depth:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                j += 1
            body = css[brace + 1:j - 1]
            if not sel.startswith("@"):
                yield sel, body
            i = j

    def _matches(self, compounds, node):
        if not _match_compound(compounds[-1], node):
            return False
        # remaining compounds must match ancestors, outermost-first (descendant semantics)
        anc = list(node.ancestors())
        idx = 0
        for comp in reversed(compounds[:-1]):
            while idx < len(anc) and not _match_compound(comp, anc[idx]):
                idx += 1
            if idx >= len(anc):
                return False
            idx += 1
        return True

    def declaration(self, node, prop):
        """The winning declared value of `prop` on `node` (inline style beats rules)."""
        if prop in node.style:
            return node.style[prop]
        best = None
        best_key = None
        for compounds, spec, order, decls in self.rules:
            if prop not in decls:
                continue
            if not self._matches(compounds, node):
                continue
            key = (spec, order)
            if best_key is None or key >= best_key:
                best, best_key = decls[prop], key
        return best


# ── resolution (vars, inheritance, backgrounds) ─────────────────────────────────────

_VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)")


class Resolver:
    def __init__(self, sheet, root):
        self.sheet = sheet
        self.root = root

    def custom_property(self, node, name, depth=0):
        """Look up a custom property for `node`: nearest declaring ancestor wins (CSS
        custom properties inherit). Returns the raw declared value or None."""
        if depth > 16:
            return None
        n = node
        while n is not None and n.tag != "#document":
            val = self.sheet.declaration(n, name)
            if val is not None:
                return val
            n = n.parent
        return None

    def resolve_value(self, node, value, depth=0):
        """Substitute every var(--x[, fallback]) in `value` against `node`'s scope."""
        if value is None or depth > 16:
            return value
        out = value
        for _ in range(8):
            m = _VAR_RE.search(out)
            if not m:
                break
            name, fallback = m.group(1), m.group(2)
            sub = self.custom_property(node, name, depth + 1)
            if sub is None:
                sub = fallback if fallback is not None else ""
            sub = self.resolve_value(node, sub.strip(), depth + 1)
            out = out[:m.start()] + (sub or "") + out[m.end():]
        return out.strip()

    def _own_opacity(self, node):
        v = self.sheet.declaration(node, "opacity")
        if v is None:
            return 1.0
        v = self.resolve_value(node, v)
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return 1.0

    def cumulative_opacity(self, node):
        o = 1.0
        n = node
        while n is not None and n.tag != "#document":
            o *= self._own_opacity(n)
            n = n.parent
        return o

    def effective_color(self, node, depth=0):
        """The element's computed text color (r,g,b,a) — walks inheritance and resolves
        currentcolor; None when not statically resolvable."""
        if depth > 32:
            return None
        n = node
        while n is not None and n.tag != "#document":
            raw = self.sheet.declaration(n, "color")
            if raw is not None:
                val = self.resolve_value(n, raw)
                if val and val.strip().lower() in ("currentcolor", "inherit"):
                    n = n.parent
                    continue
                return parse_color(val)
            n = n.parent
        return None

    def effective_background(self, node, default_bg=None):
        """Nearest painted background behind `node`, compositing semi-transparent layers.
        Returns opaque (r,g,b) or None when not statically resolvable."""
        layers = []
        n = node
        while n is not None and n.tag != "#document":
            raw = self.sheet.declaration(n, "background-color") \
                or self.sheet.declaration(n, "background")
            if raw is not None:
                val = self.resolve_value(n, raw)
                # `background` shorthand: take the first color-looking token
                col = parse_color(val)
                if col is None and val:
                    for tok in re.split(r"\s+", val):
                        col = parse_color(tok)
                        if col:
                            break
                if col is not None and col[3] > 0:
                    if col[3] >= 1.0:
                        base = col[:3]
                        for layer in reversed(layers):
                            base = composite(layer, base)
                        return base
                    layers.append(col)
            n = n.parent
        base = parse_color(default_bg) if default_bg else None
        if base is None:
            return None
        base = base[:3]
        for layer in reversed(layers):
            base = composite(layer, base)
        return base

    def font_size_px(self, node):
        """Best-effort resolved font-size in px (min across rem/px candidates in the
        winning declaration, i.e. the worst-case rendered size). None if unresolvable."""
        n = node
        raw = None
        while n is not None and n.tag != "#document":
            raw = self.sheet.declaration(n, "font-size")
            if raw is not None:
                val = self.resolve_value(n, raw)
                cands = [float(x) * 16.0 for x in re.findall(r"([\d.]+)rem", val or "")]
                cands += [float(x) for x in re.findall(r"([\d.]+)px", val or "")]
                cands += [float(x) * 16.0 for x in re.findall(r"([\d.]+)em", val or "")]
                return min(cands) if cands else None
            n = n.parent
        return None

    def rest_hidden(self, node):
        """True when the node is INVISIBLE AT REST in the resting-state cascade —
        `visibility: hidden` (nearest declaring ancestor wins; it inherits),
        `display: none` on any ancestor, or a zero opacity anywhere up the chain.
        Hover/focus un-hide rules carry unsupported pseudos and are deliberately
        absent from this cascade, so a closed mega-panel/disclosure body reads
        hidden here. Rest-hidden subtrees are NOT resting reading surface: gating
        their text against contrast floors measures colors no reader can see
        (the closed chrome dropdown was failing at ratio 1.0 — its own opacity)."""
        seen_visibility = False
        n = node
        while n is not None and n.tag != "#document":
            if not seen_visibility:
                v = self.sheet.declaration(n, "visibility")
                if v is not None:
                    seen_visibility = True
                    if str(self.resolve_value(n, v) or "").strip().lower() == "hidden":
                        return True
            d = self.sheet.declaration(n, "display")
            if d is not None and str(self.resolve_value(n, d) or "").strip().lower() == "none":
                return True
            o = self.sheet.declaration(n, "opacity")
            if o is not None:
                try:
                    if float(str(self.resolve_value(n, o) or "").strip()) == 0.0:
                        return True
                except ValueError:
                    pass
            n = n.parent
        return False


# ── interaction-state (hover) rules ──────────────────────────────────────────────────
# AS-20: interaction tokens must survive contrast checks against their OWN surface —
# WoodWave's measured gold #edd580 hover (dark footer truth) leaked onto cream card
# panels at ~1.3:1, and no static check ever saw it because :hover rules are skipped by
# the resting-state cascade. These helpers re-bind each :hover/:focus-visible color rule
# to its RESTING element so the hover color can be resolved in that element's var scope
# (a panel that re-scopes --c-link-hover resolves to its own ink here) and measured
# against the element's own effective background (card bg, not section bg).

_HOVER_PSEUDO_RE = re.compile(r":(?:hover|focus-visible|focus)\b")


def _hover_rules_css(css_text):
    """Extract every top-level rule whose selector carries :hover/:focus(-visible),
    re-emitted with the pseudo stripped and only the `color` (+ its OWN `background`,
    when the same rule swaps both) kept. An invert-on-hover control (outline family
    filling with ink + paper flip) changes color and surface TOGETHER — measuring its
    hover ink against the RESTING surface manufactures a fail no hover state shows."""
    out = []
    for sel_text, body in Stylesheet._iter_rules(_strip_comments(css_text)):
        if not _HOVER_PSEUDO_RE.search(sel_text):
            continue
        decls = _parse_decls(body)
        color = decls.get("color")
        if not color:
            continue
        hover_bg = decls.get("background-color") or decls.get("background")
        bg_decl = f" background: {hover_bg};" if hover_bg else ""
        sels = [_HOVER_PSEUDO_RE.sub("", s).strip() for s in sel_text.split(",")
                if _HOVER_PSEUDO_RE.search(s)]
        sels = [s for s in sels if s]
        if sels:
            out.append(f"{', '.join(sels)} {{ color: {color};{bg_decl} }}")
    return "\n".join(out)


def _subtree_text(node):
    return " ".join(t for n in _walk(node) if n.tag != "#document"
                    for t in (n.direct_text(),) if t)


# ── decoration + text analysis ──────────────────────────────────────────────────────

def _is_decoration(node):
    return any(_DECOR_CLASS_RE.search(c) for c in node.classes) \
        or "data-decoration" in node.attrs


def _section_of(node):
    """The enclosing `cs-surface` section wrapper (or the outermost sectioning div)."""
    n = node
    while n is not None and n.tag != "#document":
        if "cs-surface" in n.classes or (n.attrs.get("id") or "").startswith("sec-"):
            return n
        n = n.parent
    return None


def _describe(node):
    sec = _section_of(node)
    sid = (sec.attrs.get("id") or sec.attrs.get("data-layout") or "?") if sec else "-"
    cls = ".".join(sorted(node.classes)[:3]) or node.tag
    txt = node.direct_text()[:24]
    return f"{sid}/{cls}('{txt}')" if txt else f"{sid}/{cls}"


_ALNUM_RE = re.compile(r"[A-Za-z0-9]")


def analyze(html, default_bg=None):
    """Run the full static readability analysis over a rendered page.

    Returns {"text": [rows], "decorations": [rows], "skipped": int}. Each text row:
    {desc, color, bg, bg_decor, ratio, threshold, tier, passed}; each decoration row:
    {desc, composite, surface, ratio, luminance_delta, passed}. Rows are only emitted
    for elements whose colors resolved statically — unresolvable elements are counted
    in "skipped", never failed."""
    tb = _TreeBuilder()
    tb.feed(html)
    sheet = Stylesheet("\n".join(tb.styles))
    res = Resolver(sheet, tb.root)

    # ── decorations first (their composite also feeds text rows in the same section) ──
    dec_rows = []
    ghost_by_section = {}
    for node in _walk(tb.root):
        if node.tag == "#document" or not _is_decoration(node):
            continue
        text = node.direct_text()
        if not text or not _ALNUM_RE.search(text):
            continue  # empty ghost slot renders nothing
        color = res.effective_color(node)
        surface = res.effective_background(node.parent or node, default_bg=default_bg)
        if color is None or surface is None:
            continue  # not statically resolvable -> skip, never fail
        alpha = color[3] * res.cumulative_opacity(node)
        comp = composite((color[0], color[1], color[2], alpha), surface)
        ratio = contrast_ratio(comp, surface)
        d_lum = abs(rel_luminance(comp) - rel_luminance(surface))
        passed = ratio <= DECOR_SALIENCE_MAX_RATIO
        dec_rows.append({
            "desc": _describe(node), "composite": hex_of(comp), "surface": hex_of(surface),
            "alpha": round(alpha, 4), "ratio": round(ratio, 3),
            "luminance_delta": round(d_lum, 4), "passed": passed,
        })
        sec = _section_of(node)
        if sec is not None:
            prev = ghost_by_section.get(id(sec))
            if prev is None or ratio > prev[1]:
                ghost_by_section[id(sec)] = ((color[0], color[1], color[2], alpha), ratio)

    # ── real text elements ────────────────────────────────────────────────────────────
    text_rows = []
    skipped = 0
    for node in _walk(tb.root):
        if node.tag == "#document":
            continue
        text = node.direct_text()
        if len(text) < 2 or not _ALNUM_RE.search(text):
            continue
        if node.is_hidden() or _is_decoration(node):
            continue
        if any(_is_decoration(a) for a in node.ancestors()):
            continue
        if res.rest_hidden(node):
            skipped += 1          # closed chrome/disclosure body: no resting surface
            continue
        color = res.effective_color(node)
        bg = res.effective_background(node, default_bg=default_bg)
        if color is None or bg is None:
            skipped += 1
            continue
        alpha = color[3] * res.cumulative_opacity(node)
        fg = composite((color[0], color[1], color[2], alpha), bg)
        ratio = contrast_ratio(fg, bg)
        # effective background WITH the section's decoration layer behind the text
        bg_decor = None
        ratio_decor = None
        sec = _section_of(node)
        if sec is not None and id(sec) in ghost_by_section:
            ghost_rgba, _r = ghost_by_section[id(sec)]
            bg_decor = composite(ghost_rgba, bg)
            fg2 = composite((color[0], color[1], color[2], alpha), bg_decor)
            ratio_decor = contrast_ratio(fg2, bg_decor)
        eff_ratio = min(r for r in (ratio, ratio_decor) if r is not None)
        px = res.font_size_px(node)
        tier = "display" if (px is None or px >= DISPLAY_PX_FLOOR) else "body"
        threshold = TEXT_CONTRAST_DISPLAY_MIN if tier == "display" else TEXT_CONTRAST_BODY_MIN
        text_rows.append({
            "desc": _describe(node), "color": hex_of(fg), "bg": hex_of(bg),
            "bg_decor": hex_of(bg_decor) if bg_decor else None,
            "ratio": round(eff_ratio, 2), "threshold": threshold, "tier": tier,
            "font_px": round(px, 1) if px is not None else None,
            "passed": eff_ratio >= threshold,
        })

    # ── interaction (hover) colors vs the element's OWN surface (AS-20) ───────────────
    link_rows = []
    hover_css = _hover_rules_css("\n".join(tb.styles))
    if hover_css:
        hsheet = Stylesheet(hover_css)
        for node in _walk(tb.root):
            if node.tag == "#document" or node.is_hidden():
                continue
            if res.rest_hidden(node):
                continue          # closed chrome/disclosure: no reachable hover state
            raw = None
            raw_bg = None
            for compounds, _spec, _order, decls in hsheet.rules:
                if "color" in decls and hsheet._matches(compounds, node):
                    raw = decls["color"]  # cascade order preserved by rule order
                    # the SAME winning rule's surface swap rides along (invert-on-hover)
                    raw_bg = decls.get("background-color") or decls.get("background")
            if raw is None:
                continue
            label = _subtree_text(node)
            if len(label) < 2 or not _ALNUM_RE.search(label):
                continue
            # resolve the hover value in the element's OWN var scope (a panel/card that
            # re-scopes --c-link-hover resolves here to its own ink, not the section's)
            color = parse_color(res.resolve_value(node, raw))
            bg = res.effective_background(node, default_bg=default_bg)
            if color is None or bg is None:
                skipped += 1
                continue
            # an invert-on-hover rule swaps ink AND surface together: its hover ink is
            # read against its OWN hover fill (composited over the resting surface for
            # translucent washes), not against a surface the hover state never shows.
            if raw_bg:
                hb = parse_color(res.resolve_value(node, raw_bg))
                if hb is not None:
                    bg = composite(hb, bg)
            alpha = color[3] * res.cumulative_opacity(node)
            fg = composite((color[0], color[1], color[2], alpha), bg)
            ratio = contrast_ratio(fg, bg)
            px = res.font_size_px(node)
            tier = "display" if (px is not None and px >= DISPLAY_PX_FLOOR) else "body"
            threshold = TEXT_CONTRAST_DISPLAY_MIN if tier == "display" else TEXT_CONTRAST_BODY_MIN
            link_rows.append({
                "desc": _describe(node), "hover_color": hex_of(fg), "bg": hex_of(bg),
                "ratio": round(ratio, 2), "threshold": threshold, "tier": tier,
                "passed": ratio >= threshold,
            })

    return {"text": text_rows, "decorations": dec_rows, "links": link_rows,
            "skipped": skipped}


def check_text_contrast(html, default_bg=None, analysis=None, measured_pairs=None):
    """(passed, detail) for the `text-contrast` invariant.

    ``measured_pairs`` (fix-batch 2026-07, fidelity-over-floor): an optional set of
    (fg, bg) hex pairs the BRAND ITSELF measured on the live site (e.g.
    ``buttons.primary.fg`` on ``buttons.primary.bg`` from brand.yaml). An element whose
    resolved pair matches EXACTLY is exempt from the generic floor and reported as a
    measured-brand pair: this check targets AI-authored drift, and a provenance-verified
    component pair is brand truth, not drift (many real brands ship sub-AA primary
    buttons). Any OTHER low-contrast combination — including the same hues in a
    non-measured pairing — still fails."""
    a = analysis if analysis is not None else analyze(html, default_bg=default_bg)
    rows = a["text"]
    fails = [r for r in rows if not r["passed"]]
    if not rows:
        return True, f"no statically-resolvable text elements found (skipped={a['skipped']})"
    exempt = []
    if fails and measured_pairs:
        pairs = {(str(f).strip().lower(), str(b).strip().lower())
                 for f, b in measured_pairs if f and b}
        still = []
        for r in fails:
            key = (str(r["color"]).strip().lower(),
                   str(r["bg_decor"] or r["bg"]).strip().lower())
            (exempt if key in pairs else still).append(r)
        fails = still
    exempt_note = (f"; {len(exempt)} element(s) exempt as MEASURED brand pairs "
                   f"({'; '.join(sorted({r['color'] + ' on ' + str(r['bg_decor'] or r['bg']) for r in exempt}))})"
                   if exempt else "")
    if fails:
        shown = "; ".join(
            f"{r['desc']} {r['color']} on {r['bg_decor'] or r['bg']} = {r['ratio']} "
            f"(< {r['threshold']} {r['tier']})" for r in fails[:4])
        more = f" (+{len(fails) - 4} more)" if len(fails) > 4 else ""
        return False, (f"{len(fails)}/{len(rows)} text elements below WCAG-ish floor "
                       f"(display >= {TEXT_CONTRAST_DISPLAY_MIN}, body >= "
                       f"{TEXT_CONTRAST_BODY_MIN}): {shown}{more}{exempt_note}")
    worst = min(rows, key=lambda r: r["ratio"] / r["threshold"])
    return True, (f"{len(rows)} text elements measured against their effective background "
                  f"(surface + decoration layer); worst = {worst['desc']} at "
                  f"{worst['ratio']} (floor {worst['threshold']}); skipped={a['skipped']}"
                  f"{exempt_note}")


def check_link_hover_contrast(html, default_bg=None, analysis=None):
    """(passed, detail) for the `interaction-contrast` invariant (AS-20): every
    statically-resolvable :hover/:focus color, resolved in the element's OWN custom-
    property scope, must clear the contrast floor against the element's OWN effective
    background (card/panel background, not the section surface). Gold-on-cream fails
    mechanically; the measured dark-footer gold hover passes untouched."""
    a = analysis if analysis is not None else analyze(html, default_bg=default_bg)
    rows = a.get("links", [])
    if not rows:
        return True, "no statically-resolvable :hover colors in this render"
    fails = [r for r in rows if not r["passed"]]
    if fails:
        shown = "; ".join(
            f"{r['desc']} hover {r['hover_color']} on own surface {r['bg']} = "
            f"{r['ratio']} (< {r['threshold']} {r['tier']})" for r in fails[:4])
        more = f" (+{len(fails) - 4} more)" if len(fails) > 4 else ""
        return False, (f"{len(fails)}/{len(rows)} hover colors below the contrast floor "
                       f"vs their OWN surface: {shown}{more}")
    worst = min(rows, key=lambda r: r["ratio"] / r["threshold"])
    return True, (f"{len(rows)} hover color(s) measured against their own surface; "
                  f"worst = {worst['desc']} at {worst['ratio']} "
                  f"(floor {worst['threshold']})")


def check_decoration_salience(html, default_bg=None, analysis=None):
    """(passed, detail) for the `decoration-salience` invariant."""
    a = analysis if analysis is not None else analyze(html, default_bg=default_bg)
    rows = a["decorations"]
    if not rows:
        return True, "no decoration layers (ghost word / watermark) in this render"
    fails = [r for r in rows if not r["passed"]]
    if fails:
        shown = "; ".join(
            f"{r['desc']} composite {r['composite']} vs surface {r['surface']}: "
            f"ratio {r['ratio']} / luminance delta {r['luminance_delta']}"
            for r in fails[:3])
        return False, (f"{len(fails)}/{len(rows)} decoration layers exceed the salience "
                       f"ceiling (ratio <= {DECOR_SALIENCE_MAX_RATIO} vs surface): {shown}")
    worst = max(rows, key=lambda r: r["ratio"])
    return True, (f"{len(rows)} decoration layer(s) all within the salience ceiling "
                  f"(<= {DECOR_SALIENCE_MAX_RATIO}); loudest = {worst['desc']} at ratio "
                  f"{worst['ratio']} (luminance delta {worst['luminance_delta']})")
