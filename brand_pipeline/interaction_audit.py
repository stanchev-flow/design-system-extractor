#!/usr/bin/env python3
"""Interaction-contract audit gate (phase 1: measurement only).

Audits composed HTML lanes against brand_pipeline/spec/interaction-contracts.md
(WAI-ARIA APG-derived per-family contracts). Two layers:

- STATIC: parses the lane HTML (BeautifulSoup / html.parser) and verifies
  attribute/semantic requirements. No browser needed; unit-testable.
- BEHAVIORAL: drives the lane in headless Chromium (Playwright, file:// URLs) and
  probes focus order, Enter/Space/Escape handling, single-open accordion behavior,
  reduced-motion computed styles, and browser-computed form labelling.

Component instances are detected by structural signatures of the renderer's output
(cs-nav-tab, details.cs-nav-lang, details[name] groups, cs-edgecut, cs-marquee,
cs-utility-banner, forms, the cs-reveal choreography). When a family is absent from
a lane the auditor emits a `skip` finding with a note rather than silence.

Findings are keyed IC-<FAMILY>-<NN> with severity (required/advisory), a locator
(line + snippet for static, selector + snippet for behavioral), and the lane.

Usage:
  ./venv/bin/python -m brand_pipeline.interaction_audit <path-to-lane-html-or-dir>...
      [--out DIR] [--static-only] [--strict] [--lane-timeout SECONDS]

Baseline mode always exits 0; --strict exits 1 when any REQUIRED check fails
(future gate wiring). Reports: report.md + report.json in --out
(default runs/remote/brand/interaction-baseline/).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import Tag

AUDITOR_VERSION = "1.0.0"
PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT = PROJECT_DIR / "runs" / "remote" / "brand" / "interaction-baseline"

SEV_REQUIRED = "required"
SEV_ADVISORY = "advisory"

# status values: pass | fail | advisory | skip
# (advisory == an advisory-severity check that did not hold)

FAMILIES = ("nav", "lang", "acc", "banner", "carousel", "marquee", "tabs", "form",
            "reveal")


@dataclass
class Finding:
    check: str            # e.g. "IC-NAV-02"
    family: str           # nav | lang | acc | banner | carousel | marquee | form | reveal
    severity: str         # required | advisory
    status: str           # pass | fail | advisory | skip
    lane: str
    layer: str            # static | behavioral
    message: str
    line: int | None = None
    snippet: str | None = None


@dataclass
class LaneResult:
    lane: str
    path: str
    mtime_iso: str
    sha256_12: str
    findings: list[Finding] = field(default_factory=list)


# --------------------------------------------------------------------------- utils

def _snippet(el: Tag, limit: int = 160) -> str:
    raw = str(el)
    raw = re.sub(r"\s+", " ", raw)
    return raw[:limit] + ("…" if len(raw) > limit else "")


def _line(el: Tag) -> int | None:
    return getattr(el, "sourceline", None)


def _acc_text(el: Tag) -> str:
    """Visible text of an element, excluding aria-hidden subtrees."""
    parts: list[str] = []

    def walk(node) -> None:
        if isinstance(node, Tag):
            if (node.get("aria-hidden") or "").lower() == "true":
                return
            for child in node.children:
                walk(child)
        else:
            text = str(node)
            if text.strip():
                parts.append(text.strip())

    walk(el)
    return " ".join(parts).strip()


def _aria_hidden_or_inherited(el: Tag, stop: Tag) -> bool:
    """True if el or any ancestor up to (and including) `stop` is aria-hidden."""
    node: Tag | None = el
    while isinstance(node, Tag):
        if (node.get("aria-hidden") or "").lower() == "true":
            return True
        if node is stop:
            break
        node = node.parent
    return False


def _has_accessible_name(el: Tag) -> bool:
    if (el.get("aria-label") or "").strip():
        return True
    if (el.get("aria-labelledby") or "").strip():
        return True  # static layer trusts the reference; behavioral verifies resolution
    return bool(_acc_text(el))


def _classes(el: Tag) -> list[str]:
    value = el.get("class") or []
    if isinstance(value, str):
        return value.split()
    return list(value)


def _class_str(el: Tag) -> str:
    return " ".join(_classes(el))


def _first_element_child(el: Tag) -> Tag | None:
    for child in el.children:
        if isinstance(child, Tag):
            return child
    return None


def _css_blocks(soup: BeautifulSoup) -> str:
    return "\n".join(style.get_text() for style in soup.find_all("style"))


def _script_blocks(soup: BeautifulSoup) -> str:
    return "\n".join(s.get_text() for s in soup.find_all("script"))


def _reduced_motion_blocks(css: str) -> list[str]:
    """Extract bodies of @media blocks that target prefers-reduced-motion: reduce."""
    blocks: list[str] = []
    for match in re.finditer(r"@media[^{]*prefers-reduced-motion\s*:\s*reduce[^{]*\{", css):
        depth = 1
        i = match.end()
        start = i
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        blocks.append(css[start:i - 1])
    return blocks


def _css_rules(css: str) -> list[tuple[str, str]]:
    """Very small CSS rule splitter -> (selector, body). Ignores nested at-rules'
    grouping (their inner rules still surface, which is fine for our checks)."""
    rules: list[tuple[str, str]] = []
    cleaned = re.sub(r"/\*.*?\*/", " ", css, flags=re.S)
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", cleaned):
        selector = match.group(1).strip()
        body = match.group(2).strip()
        if selector.startswith("@"):
            continue
        rules.append((selector, body))
    return rules


# --------------------------------------------------------------- static: families

def _detect_nav_tabs(soup: BeautifulSoup) -> list[Tag]:
    return [el for el in soup.select(".cs-nav-tab") if isinstance(el, Tag)]


def _detect_lang(soup: BeautifulSoup) -> list[Tag]:
    found = [el for el in soup.select("details.cs-nav-lang")]
    if found:
        return found
    # generic fallback: a details in nav chrome whose list items carry hreflang
    out = []
    for det in soup.find_all("details"):
        if det.find("a", attrs={"hreflang": True}):
            out.append(det)
    return out


def _lang_is_selector(det: Tag) -> bool:
    """True when the details.cs-nav-lang disclosure IS a selector (language /
    locale / region / currency switcher) — the device the IC-LANG selection
    checks were written for. Evidence: any item carries hreflang facts, any
    item already carries a current/selected marker, or the toggle's accessible
    name declares selector purpose. A generic navigation-menu disclosure
    (About, Company, Resources…) that merely reuses the same rendered device is
    APG disclosure-navigation: no selection concept exists, and aria-current
    applies only when an item is the CURRENT PAGE — demanding it there would
    force dishonest markup."""
    if det.find("a", attrs={"hreflang": True}) is not None:
        return True
    if det.find(attrs={"aria-current": True}) is not None or \
            det.find(attrs={"aria-selected": "true"}) is not None:
        return True
    summary = det.find("summary")
    name = ""
    if summary is not None:
        name = str(summary.get("aria-label") or "") or summary.get_text(" ", strip=True)
    return bool(re.search(r"\b(language|locale|region|country|currency)\b", name, re.I))


def _detect_accordion_details(soup: BeautifulSoup, lang_nodes: list[Tag]) -> list[Tag]:
    lang_set = set(id(n) for n in lang_nodes)
    out = []
    for det in soup.find_all("details"):
        if id(det) in lang_set:
            continue
        if det.find("a", attrs={"hreflang": True}):
            continue
        out.append(det)
    return out


def _accordion_groups(details: list[Tag]) -> list[list[Tag]]:
    """Group details by shared parent; 2+ siblings = an accordion group."""
    by_parent: dict[int, list[Tag]] = {}
    order: list[int] = []
    for det in details:
        key = id(det.parent)
        if key not in by_parent:
            by_parent[key] = []
            order.append(key)
        by_parent[key].append(det)
    return [by_parent[k] for k in order if len(by_parent[k]) >= 2]


def _authored_multi(det: Tag) -> bool:
    """True when the group's shared parent DECLARES multi-open behavior
    (data-acc-multi="authored", the composer's stamp for an explicit
    exclusive:false knob) — a deliberate independent-disclosure family,
    distinct from an accidentally ungrouped single-open accordion."""
    parent = det.parent
    return isinstance(parent, Tag) and \
        (parent.get("data-acc-multi") or "").strip().lower() == "authored"


def _detect_banner_close(soup: BeautifulSoup) -> list[Tag]:
    out: list[Tag] = []
    for el in soup.find_all(True):
        if "banner-close" in _class_str(el):
            out.append(el)
    # renderer signature: dismiss control inside a *utility-banner* container
    for container in soup.find_all(True):
        if "utility-banner" not in _class_str(container):
            continue
        for candidate in container.find_all(("button", "a")):
            label = (candidate.get("aria-label") or "").lower()
            if "close" in _class_str(candidate) or label in ("dismiss", "close"):
                out.append(candidate)
    seen: set[int] = set()
    unique = []
    for el in out:
        if id(el) not in seen:
            seen.add(id(el))
            unique.append(el)
    return unique


def _detect_rails(soup: BeautifulSoup) -> list[Tag]:
    rails = [el for el in soup.select(".cs-edgecut")]
    for el in soup.find_all(attrs={"aria-roledescription": "carousel"}):
        if el not in rails:
            rails.append(el)
    return rails


def _detect_marquees(soup: BeautifulSoup) -> list[Tag]:
    out = []
    for el in soup.find_all(True):
        cls = _classes(el)
        if "cs-marquee" in cls and el.select_one(".cs-marquee-track"):
            out.append(el)
    return out


def _form_controls(scope: Tag) -> list[Tag]:
    skip_types = {"hidden", "submit", "button", "reset", "image"}
    controls = []
    for el in scope.find_all(("input", "select", "textarea")):
        if el.name == "input" and (el.get("type") or "text").lower() in skip_types:
            continue
        controls.append(el)
    return controls


def _label_for_map(soup: BeautifulSoup) -> dict[str, Tag]:
    mapping: dict[str, Tag] = {}
    for label in soup.find_all("label"):
        target = label.get("for")
        if target:
            mapping.setdefault(target, label)
    return mapping


def _control_is_labelled(control: Tag, label_map: dict[str, Tag]) -> bool:
    if (control.get("aria-label") or "").strip():
        return True
    if (control.get("aria-labelledby") or "").strip():
        return True
    cid = control.get("id")
    if cid and cid in label_map and _acc_text(label_map[cid]):
        return True
    parent = control.parent
    while isinstance(parent, Tag):
        if parent.name == "label":
            return bool(_acc_text(parent))
        if parent.name in ("form", "body", "html"):
            break
        parent = parent.parent
    return False


# ------------------------------------------------------------------ static audit

def audit_static(html_text: str, lane: str) -> list[Finding]:
    soup = BeautifulSoup(html_text, "html.parser")
    css = _css_blocks(soup)
    scripts = _script_blocks(soup)
    findings: list[Finding] = []

    def add(check: str, family: str, severity: str, ok: bool | None, message: str,
            el: Tag | None = None, skip: bool = False) -> None:
        if skip:
            status = "skip"
        elif ok:
            status = "pass"
        else:
            status = "fail" if severity == SEV_REQUIRED else "advisory"
        findings.append(Finding(
            check=check, family=family, severity=severity, status=status, lane=lane,
            layer="static", message=message,
            line=_line(el) if el is not None else None,
            snippet=_snippet(el) if el is not None else None,
        ))

    # ---- family: nav (disclosure navigation / mega-menu)
    nav_tabs = _detect_nav_tabs(soup)
    navs = soup.find_all("nav")
    if nav_tabs:
        for tab in nav_tabs:
            trigger = None
            for child in tab.children:
                if isinstance(child, Tag) and child.name in ("a", "button"):
                    trigger = child
                    break
            panel = tab.select_one(".cs-mega")
            if trigger is None:
                add("IC-NAV-01", "nav", SEV_REQUIRED, False,
                    "nav tab has no button/link trigger as first control", tab)
                continue
            label = _acc_text(trigger) or "(unnamed)"
            if trigger.name == "button":
                add("IC-NAV-01", "nav", SEV_REQUIRED, True,
                    f"trigger '{label}' is a native button", trigger)
            else:
                href = (trigger.get("href") or "").strip()
                ok = href not in ("", "#")
                add("IC-NAV-01", "nav", SEV_REQUIRED, ok,
                    (f"trigger '{label}' is a link with a real destination" if ok else
                     f"trigger '{label}' is an <a href=\"{href}\"> serving only to open the panel — "
                     "should be a <button> (or a link with a real destination)"), trigger)
            has_exp = trigger.has_attr("aria-expanded")
            add("IC-NAV-02", "nav", SEV_REQUIRED, has_exp,
                (f"trigger '{label}' carries aria-expanded" if has_exp else
                 f"trigger '{label}' lacks aria-expanded — collapsed state invisible to AT"),
                trigger)
            if panel is not None:
                has_controls = bool((trigger.get("aria-controls") or "").strip())
                add("IC-NAV-04", "nav", SEV_ADVISORY, has_controls,
                    ("trigger references its panel via aria-controls" if has_controls else
                     f"trigger '{label}' has no aria-controls reference to its panel"), trigger)
    if navs:
        offenders = []
        for nav in navs:
            for el in nav.find_all(attrs={"role": re.compile(r"^(menu|menubar|menuitem)$", re.I)}):
                offenders.append(el)
        add("IC-NAV-03", "nav", SEV_REQUIRED, not offenders,
            ("no ARIA menu/menubar roles in site nav" if not offenders else
             "ARIA menu/menubar/menuitem roles used on site navigation (APG anti-pattern)"),
            offenders[0] if offenders else None)
        role_button_links = [el for nav in navs for el in nav.find_all("a", attrs={"role": "button"})]
        add("IC-NAV-05", "nav", SEV_ADVISORY, not role_button_links,
            ("no role=button anchors in nav chrome" if not role_button_links else
             "anchor with role=button in nav chrome — promises Space activation anchors don't have"),
            role_button_links[0] if role_button_links else None)
    if not nav_tabs and not navs:
        add("IC-NAV-01", "nav", SEV_REQUIRED, None,
            "no disclosure-nav instances detected in this lane", skip=True)

    # ---- family: lang (select-only dropdown)
    lang_nodes = _detect_lang(soup)
    if lang_nodes:
        for det in lang_nodes:
            summary = det.find("summary")
            add("IC-LANG-01", "lang", SEV_REQUIRED, summary is not None,
                ("toggle is a native <summary> inside <details>" if summary is not None else
                 "details-based dropdown missing a <summary> toggle"), summary or det)
            if summary is not None:
                named = _has_accessible_name(summary)
                add("IC-LANG-02", "lang", SEV_REQUIRED, named,
                    ("toggle has an accessible name" if named else
                     "icon-only summary with no accessible name"), summary)
            if _lang_is_selector(det):
                current = det.find(attrs={"aria-current": True}) or det.find(attrs={"aria-selected": "true"})
                add("IC-LANG-03", "lang", SEV_REQUIRED, current is not None,
                    ("current selection marked via aria-current/aria-selected" if current is not None else
                     "no aria-current/aria-selected marking of the current selection"),
                    current or det)
                items = det.find_all("a")
                all_hreflang = bool(items) and all(a.get("hreflang") for a in items)
                add("IC-LANG-04", "lang", SEV_ADVISORY, all_hreflang,
                    ("locale items are links carrying hreflang" if all_hreflang else
                     "locale items missing hreflang metadata"), det)
            else:
                add("IC-LANG-03", "lang", SEV_REQUIRED, None,
                    "disclosure-navigation menu (plain nav links, no selection concept) — "
                    "selection marking not applicable", skip=True)
    else:
        add("IC-LANG-01", "lang", SEV_REQUIRED, None,
            "no language-switcher instances detected in this lane", skip=True)

    # ---- family: acc (accordion groups + standalone disclosures)
    acc_details = _detect_accordion_details(soup, lang_nodes)
    if acc_details:
        groups = _accordion_groups(acc_details)
        for group in groups:
            names = [(det.get("name") or "").strip() for det in group]
            shared = all(names) and len(set(names)) == 1
            # an AUTHORED multi-open family (composer stamps the shared parent with
            # data-acc-multi="authored" for an explicit exclusive:false knob) is a
            # declared behavior, not an accidentally ungrouped single-open group —
            # see interaction-contracts.md §Resolution notes.
            declared_multi = _authored_multi(group[0])
            if declared_multi and not shared:
                add("IC-ACC-01", "acc", SEV_REQUIRED, True,
                    (f"group of {len(group)} details is a declared multi-open family "
                     "(data-acc-multi=\"authored\") — single-open grouping waived"), group[0])
            else:
                add("IC-ACC-01", "acc", SEV_REQUIRED, shared,
                    (f"group of {len(group)} details shares name=\"{names[0]}\" (exclusive single-open)"
                     if shared else
                     f"accordion group of {len(group)} details does not share a name attribute — "
                     "single-open behavior not enforced"), group[0])
            open_count = sum(1 for det in group if det.has_attr("open"))
            add("IC-ACC-05", "acc", SEV_ADVISORY, open_count <= 1,
                (f"{open_count} item(s) authored open" if open_count <= 1 else
                 f"{open_count} items authored open in an exclusive group"), group[0])
        for det in acc_details:
            first = _first_element_child(det)
            has_summary = first is not None and first.name == "summary"
            add("IC-ACC-02", "acc", SEV_REQUIRED, has_summary,
                ("details has a <summary> as first element child" if has_summary else
                 "details missing a leading <summary> — browser synthesizes an unlabeled toggle"),
                det)
            summary = det.find("summary")
            if summary is not None:
                named = bool(_acc_text(summary)) or bool((summary.get("aria-label") or "").strip())
                add("IC-ACC-03", "acc", SEV_REQUIRED, named,
                    ("summary has accessible text" if named else
                     "summary text is empty / only aria-hidden icons"), summary)
                icons = [el for el in summary.find_all(("svg", "span"))
                         if not _acc_text(el) and ("icon" in _class_str(el) or "chev" in _class_str(el)
                                                   or "arrow" in _class_str(el) or el.name == "svg")]
                bad = [el for el in icons if not _aria_hidden_or_inherited(el, summary)]
                if icons:
                    add("IC-ACC-04", "acc", SEV_ADVISORY, not bad,
                        ("decorative summary icons are aria-hidden" if not bad else
                         "decorative icon in summary not aria-hidden"),
                        bad[0] if bad else icons[0])
    else:
        add("IC-ACC-01", "acc", SEV_REQUIRED, None,
            "no accordion/disclosure details detected in this lane", skip=True)

    # ---- family: banner (utility banner dismiss)
    closers = _detect_banner_close(soup)
    if closers:
        for btn in closers:
            is_button = btn.name == "button" or (
                (btn.get("role") or "") == "button" and btn.get("tabindex") is not None)
            add("IC-BAN-01", "banner", SEV_REQUIRED, is_button,
                ("close control is a native button" if is_button else
                 "close control is not a button (nor role=button + tabindex)"), btn)
            named = _has_accessible_name(btn)
            add("IC-BAN-02", "banner", SEV_REQUIRED, named,
                ("close control has an accessible name" if named else
                 "icon-only close control with no accessible name"), btn)
            svgs = btn.find_all("svg")
            svg_ok = all((s.get("aria-hidden") or "").lower() == "true" for s in svgs) if svgs else True
            add("IC-BAN-03", "banner", SEV_ADVISORY, svg_ok,
                ("icon inside close control is aria-hidden" if svg_ok else
                 "icon inside close control not aria-hidden"), btn)
    else:
        add("IC-BAN-01", "banner", SEV_REQUIRED, None,
            "no dismissible banner detected in this lane", skip=True)

    # ---- family: carousel (edge-cut rails / carousels)
    rails = _detect_rails(soup)
    if rails:
        for rail in rails:
            scope = rail.parent if isinstance(rail.parent, Tag) else rail
            buttons = []
            for btn in scope.find_all("button"):
                blob = " ".join([_class_str(btn), btn.get("aria-label") or "", _acc_text(btn)]).lower()
                if re.search(r"prev|next|back|forward|previous|→|←|later|earlier", blob):
                    buttons.append(btn)
            if buttons:
                unnamed = [b for b in buttons if not _has_accessible_name(b)]
                ok = not unnamed
                add("IC-CAR-01", "carousel", SEV_REQUIRED, ok,
                    ("prev/next controls are buttons with accessible names" if ok else
                     "prev/next control lacks an accessible name"),
                    unnamed[0] if unnamed else buttons[0])
            else:
                focusable_region = (rail.get("tabindex") == "0"
                                    and (rail.get("role") or "") in ("region", "group")
                                    and _has_accessible_name(rail))
                add("IC-CAR-01", "carousel", SEV_REQUIRED, focusable_region,
                    ("rail is an accessible keyboard-scrollable region" if focusable_region else
                     "scroll rail has no prev/next buttons and is not an accessible "
                     "keyboard-scrollable region (tabindex=0 + role + name)"), rail)
            has_rd = (rail.get("aria-roledescription") or "").lower() == "carousel" and _has_accessible_name(rail)
            add("IC-CAR-02", "carousel", SEV_ADVISORY, has_rd,
                ("container has aria-roledescription=carousel and a label" if has_rd else
                 "container lacks aria-roledescription=\"carousel\" + accessible label"), rail)
            slides = rail.find_all(attrs={"aria-roledescription": "slide"})
            add("IC-CAR-03", "carousel", SEV_ADVISORY, bool(slides),
                ("slide containers use role=group + aria-roledescription=slide" if slides else
                 "no slide-level group/roledescription semantics"), rail)
            findings.append(Finding(
                check="IC-CAR-04", family="carousel", severity=SEV_ADVISORY, status="skip",
                lane=lane, layer="static",
                message="no auto-rotation on this rail — pause-control contract not applicable",
                line=_line(rail), snippet=_snippet(rail)))
    else:
        add("IC-CAR-01", "carousel", SEV_REQUIRED, None,
            "no carousel/edge-cut rail detected in this lane", skip=True)

    # ---- family: tabs (WAI-ARIA APG tabs — IC-TAB, fix1 2026-07)
    tablists = soup.find_all(attrs={"role": "tablist"})
    if tablists:
        panel_by_id = {p.get("id"): p for p in soup.find_all(attrs={"role": "tabpanel"})
                       if p.get("id")}
        for tl in tablists:
            tabs = tl.find_all(attrs={"role": "tab"})
            selected = [t for t in tabs
                        if (t.get("aria-selected") or "").lower() == "true"]
            ok01 = bool(tabs) and all(t.name == "button" for t in tabs) \
                and len(selected) == 1
            add("IC-TAB-01", "tabs", SEV_REQUIRED, ok01,
                ("tabs are native buttons with exactly one aria-selected" if ok01 else
                 f"tablist shape broken: {len(tabs)} tabs, "
                 f"{sum(1 for t in tabs if t.name != 'button')} non-button, "
                 f"{len(selected)} selected"), tl)
            own_panels = [panel_by_id.get(t.get("aria-controls") or "") for t in tabs]
            wired = all(p is not None for p in own_panels)
            tab_ids = {t.get("id") for t in tabs if t.get("id")}
            back = wired and all((p.get("aria-labelledby") or "") in tab_ids
                                 for p in own_panels)
            add("IC-TAB-02", "tabs", SEV_REQUIRED, back,
                ("tab↔panel aria-controls/aria-labelledby wiring is two-way" if back else
                 "tab→panel wiring broken (aria-controls id missing or panel "
                 "aria-labelledby does not reference its tab)"), tl)
            roving = all(
                (t in selected and t.get("tabindex") in (None, "0"))
                or (t not in selected and t.get("tabindex") == "-1")
                for t in tabs)
            visible_panels = [p for p in own_panels if p is not None
                              and not p.has_attr("hidden")]
            sel_panel = panel_by_id.get(
                (selected[0].get("aria-controls") or "")) if selected else None
            vis_ok = wired and len(visible_panels) == 1 \
                and sel_panel is visible_panels[0] \
                and visible_panels[0].get("tabindex") == "0"
            ok03 = roving and vis_ok
            add("IC-TAB-03", "tabs", SEV_REQUIRED, ok03,
                ("roving tabindex + single visible focusable panel" if ok03 else
                 f"roving/visibility broken: roving={roving}, "
                 f"visible panels={len(visible_panels)}, "
                 f"panel focusable={bool(visible_panels) and visible_panels[0].get('tabindex') == '0'}"),
                tl)
            # tablist naming must be explicit (aria-label/labelledby) — role=tablist
            # does not name itself from its tab contents.
            named = bool((tl.get("aria-label") or "").strip()
                         or (tl.get("aria-labelledby") or "").strip())
            add("IC-TAB-04", "tabs", SEV_ADVISORY, named,
                ("tablist has an accessible name" if named else
                 "tablist lacks an accessible name (aria-label/labelledby)"), tl)
    else:
        add("IC-TAB-01", "tabs", SEV_REQUIRED, None,
            "no tab devices detected in this lane", skip=True)

    # ---- family: marquee
    marquees = _detect_marquees(soup)
    if marquees:
        for mq in marquees:
            halves = mq.select(".cs-marquee-half")
            if len(halves) >= 2:
                clones = halves[1:]
                bad = [h for h in clones if (h.get("aria-hidden") or "").lower() != "true"]
                add("IC-MARQ-01", "marquee", SEV_REQUIRED, not bad,
                    ("duplicated seam half is aria-hidden" if not bad else
                     "duplicated marquee half not aria-hidden — AT reads the logo list twice"),
                    bad[0] if bad else clones[0])
            else:
                add("IC-MARQ-01", "marquee", SEV_REQUIRED, True,
                    "single-half marquee: no duplicated seam content to hide", mq)
            rm = _reduced_motion_blocks(css)
            calmed = any(re.search(r"marquee[^{}]*\{[^{}]*animation(-play-state)?\s*:\s*(none|paused)", blk)
                         for blk in rm)
            add("IC-MARQ-02", "marquee", SEV_REQUIRED, calmed,
                ("prefers-reduced-motion neutralizes the marquee animation" if calmed else
                 "no prefers-reduced-motion rule disabling the marquee animation"), mq)
    else:
        add("IC-MARQ-01", "marquee", SEV_REQUIRED, None,
            "no marquee detected in this lane", skip=True)

    # ---- family: form
    controls = _form_controls(soup)
    labels = soup.find_all("label")
    forms = soup.find_all("form")
    if controls or labels or forms:
        label_map = _label_for_map(soup)
        for control in controls:
            labelled = _control_is_labelled(control, label_map)
            ident = control.get("id") or control.get("name") or control.get("type") or control.name
            add("IC-FORM-01", "form", SEV_REQUIRED, labelled,
                (f"control '{ident}' is programmatically labelled" if labelled else
                 f"control '{ident}' has no programmatic label (for/id, wrapping label, or aria-*)"),
                control)
        for form in forms:
            submits = [b for b in form.find_all("button")
                       if (b.get("type") or "submit").lower() == "submit"]
            submits += form.find_all("input", attrs={"type": "submit"})
            add("IC-FORM-02", "form", SEV_REQUIRED, bool(submits),
                ("form has a real submit button" if submits else
                 "form has no real submit control (button[type=submit] / input[type=submit])"),
                submits[0] if submits else form)
        control_ids = {c.get("id") for c in soup.find_all(("input", "select", "textarea", "button", "output", "meter", "progress")) if c.get("id")}
        for label in labels:
            target = label.get("for")
            if target:
                ok = target in control_ids
            else:
                ok = label.find(("input", "select", "textarea", "button")) is not None
            add("IC-FORM-03", "form", SEV_REQUIRED, ok,
                ("label is associated with a real control" if ok else
                 "label is not associated with any form control (display-only field mock?)"),
                label)
        flagged = [c for c in controls if c.get("data-error") is not None]
        if flagged:
            bad = [c for c in flagged
                   if not (c.has_attr("required") or (c.get("aria-required") or "").lower() == "true")]
            add("IC-FORM-04", "form", SEV_REQUIRED, not bad,
                ("fields with error copy communicate requiredness programmatically" if not bad else
                 "field carries error copy but neither required nor aria-required"),
                bad[0] if bad else flagged[0])
        elif any(c.has_attr("required") or (c.get("aria-required") or "").lower() == "true"
                 for c in controls):
            add("IC-FORM-04", "form", SEV_REQUIRED, True,
                "required fields use the required attribute", controls[0] if controls else None)
        else:
            findings.append(Finding(
                check="IC-FORM-04", family="form", severity=SEV_REQUIRED, status="skip",
                lane=lane, layer="static",
                message="no required-field signals detected in this lane"))
        helps = [el for el in soup.find_all(True) if "field-help" in _class_str(el)]
        if helps:
            described_ids: set[str] = set()
            for c in soup.find_all(attrs={"aria-describedby": True}):
                described_ids.update((c.get("aria-describedby") or "").split())
            bad = [h for h in helps if not h.get("id") or h.get("id") not in described_ids]
            add("IC-FORM-05", "form", SEV_ADVISORY, not bad,
                ("help text is linked via aria-describedby" if not bad else
                 "field help text not linked to its control via aria-describedby"),
                bad[0] if bad else helps[0])
        if flagged:
            wired = [c for c in flagged if (c.get("aria-describedby") or "").strip()]
            add("IC-FORM-06", "form", SEV_ADVISORY, len(wired) == len(flagged),
                ("error copy is wired via aria-describedby" if len(wired) == len(flagged) else
                 "error copy lives only in data-error attributes — invisible to AT"),
                flagged[0])
    else:
        add("IC-FORM-01", "form", SEV_REQUIRED, None,
            "no form controls or labels detected in this lane", skip=True)

    # ---- family: reveal (scroll-reveal choreography)
    reveal_in_css = "cs-reveal" in css
    reveal_in_js = "cs-reveal" in scripts or "IntersectionObserver" in scripts
    if reveal_in_css or reveal_in_js:
        hiding_rules = []
        for selector, body in _css_rules(css):
            if "cs-reveal" in selector and re.search(r"opacity\s*:\s*0(?![.\d])", body):
                hiding_rules.append((selector, body))
        ungated = []
        for selector, body in hiding_rules:
            for part in selector.split(","):
                part = part.strip()
                if "cs-reveal" not in part:
                    continue
                tokens = re.findall(r"\.[A-Za-z0-9_-]+", part)
                gate = [t for t in tokens if "cs-reveal" not in t and "is-in" not in t]
                if not gate:
                    ungated.append(part)
        if hiding_rules:
            ok = not ungated
            findings.append(Finding(
                check="IC-REV-01", family="reveal", severity=SEV_REQUIRED,
                status="pass" if ok else "fail", lane=lane, layer="static",
                message=("hidden initial state is gated on a JS-added class "
                         f"({hiding_rules[0][0][:60]}…)" if ok else
                         f"ungated hiding rule '{ungated[0]}' — content hidden even without JS"),
            ))
        else:
            findings.append(Finding(
                check="IC-REV-01", family="reveal", severity=SEV_REQUIRED,
                status="pass", lane=lane, layer="static",
                message="no CSS rule hides reveal targets (reveal is JS-additive only)"))
        rm = _reduced_motion_blocks(css)
        forced_visible = any(
            re.search(r"cs-reveal[^{}]*\{[^{}]*opacity\s*:\s*1", blk) for blk in rm)
        findings.append(Finding(
            check="IC-REV-02", family="reveal", severity=SEV_REQUIRED,
            status="pass" if forced_visible else "fail", lane=lane, layer="static",
            message=("prefers-reduced-motion forces reveal targets visible" if forced_visible else
                     "no prefers-reduced-motion override forcing reveal targets visible")))
        failsafe = bool(re.search(r"setTimeout", scripts)) and "is-in" in scripts
        findings.append(Finding(
            check="IC-REV-03", family="reveal", severity=SEV_ADVISORY,
            status="pass" if failsafe else "advisory", lane=lane, layer="static",
            message=("timed failsafe present (setTimeout forces all targets visible)" if failsafe
                     else "no timed failsafe in the reveal script")))
    else:
        findings.append(Finding(
            check="IC-REV-01", family="reveal", severity=SEV_REQUIRED, status="skip",
            lane=lane, layer="static",
            message="no scroll-reveal choreography detected in this lane"))

    return findings


# -------------------------------------------------------------- behavioral audit

JS_VISIBLE = """(el) => {
  if (!el) return false;
  const cs = getComputedStyle(el);
  if (cs.display === 'none' || cs.visibility === 'hidden') return false;
  if (parseFloat(cs.opacity || '1') < 0.5) return false;
  const r = el.getBoundingClientRect();
  return r.width > 1 && r.height > 1;
}"""

JS_CONTROL_NAMED = """(el) => {
  const aria = el.getAttribute('aria-label');
  if (aria && aria.trim()) return true;
  const lb = el.getAttribute('aria-labelledby');
  if (lb) {
    const t = lb.split(/\\s+/).map(id => {
      const n = document.getElementById(id);
      return n ? (n.textContent || '') : '';
    }).join(' ').trim();
    if (t) return true;
  }
  if (el.labels && el.labels.length) {
    for (const l of el.labels) { if ((l.textContent || '').trim()) return true; }
  }
  return false;
}"""


class _LaneBudget:
    def __init__(self, seconds: float):
        self.deadline = time.monotonic() + seconds

    @property
    def exhausted(self) -> bool:
        return time.monotonic() > self.deadline


def audit_behavioral(path: Path, lane: str, timeout_s: float = 120.0) -> list[Finding]:
    """Playwright probes. Import lazily so the static layer has no browser deps."""
    findings: list[Finding] = []

    def add(check: str, family: str, severity: str, ok: bool | None, message: str,
            snippet: str | None = None, skip: bool = False) -> None:
        status = "skip" if skip else ("pass" if ok else ("fail" if severity == SEV_REQUIRED else "advisory"))
        findings.append(Finding(check=check, family=family, severity=severity, status=status,
                                lane=lane, layer="behavioral", message=message, snippet=snippet))

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover
        add("IC-BEHAVIORAL", "nav", SEV_REQUIRED, None,
            f"Playwright unavailable ({exc}); behavioral layer skipped", skip=True)
        return findings

    budget = _LaneBudget(timeout_s)
    url = path.resolve().as_uri()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                context.set_default_timeout(5000)
                page = context.new_page()
                page.goto(url, wait_until="load", timeout=30000)
                page.wait_for_timeout(250)

                # ---------- nav probes
                nav_tab_count = page.locator(".cs-nav-tab").count()
                nav_present = nav_tab_count > 0
                if nav_present and not budget.exhausted:
                    # IC-NAV-06: tab-reachability of triggers/login/language
                    targets = {"trigger": False, "login": False, "lang": False}
                    page.evaluate("() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0,0); }")
                    for _ in range(250):
                        if all(targets.values()) or budget.exhausted:
                            break
                        page.keyboard.press("Tab")
                        step = page.evaluate("""() => {
                          const el = document.activeElement;
                          if (!el || el === document.body) return {repeat: false, body: true,
                            inTab: false, login: false, lang: false};
                          const repeat = !!el.__icVisited;
                          el.__icVisited = true;
                          return {
                            repeat, body: false,
                            inTab: !!el.closest('.cs-nav-tab'),
                            login: el.tagName === 'A' && String(el.className || '').includes('cs-nav-util-link'),
                            lang: el.tagName === 'SUMMARY' || !!el.closest('.cs-nav-lang'),
                          };
                        }""")
                        if step["repeat"]:
                            break
                        if step["inTab"]:
                            targets["trigger"] = True
                        if step["login"]:
                            targets["login"] = True
                        if step["lang"]:
                            targets["lang"] = True
                    missing = [k for k, v in targets.items() if not v]
                    add("IC-NAV-06", "nav", SEV_REQUIRED, not missing,
                        ("Tab reaches nav triggers, login, and language switcher" if not missing else
                         f"Tab never reached: {', '.join(missing)} (within 250 presses)"))

                    # IC-NAV-07: hover-open vs keyboard-open parity on first tab
                    tab1 = page.locator(".cs-nav-tab").first
                    panel1 = tab1.locator(".cs-mega").first
                    hover_open = False
                    kb_open = False
                    if panel1.count():
                        tab1.hover()
                        page.wait_for_timeout(350)
                        hover_open = bool(panel1.evaluate(JS_VISIBLE))
                        page.mouse.move(0, 500)
                        page.wait_for_timeout(350)
                        trigger1 = tab1.locator("a, button").first
                        trigger1.focus()
                        page.wait_for_timeout(350)
                        kb_open = bool(panel1.evaluate(JS_VISIBLE))
                        add("IC-NAV-07", "nav", SEV_REQUIRED, (not hover_open) or kb_open,
                            (f"hover opens panel={hover_open}, keyboard focus opens panel={kb_open}"
                             if ((not hover_open) or kb_open) else
                             "panel opens on hover but not on keyboard focus (no parity)"))

                        # IC-NAV-08: Escape closes the open panel
                        if kb_open and not budget.exhausted:
                            page.keyboard.press("Escape")
                            page.wait_for_timeout(250)
                            still_open = bool(panel1.evaluate(JS_VISIBLE))
                            focus_ok = page.evaluate(
                                "() => !!(document.activeElement && document.activeElement.closest('nav'))")
                            add("IC-NAV-08", "nav", SEV_REQUIRED, (not still_open) and focus_ok,
                                ("Escape closes the open panel and keeps focus in nav"
                                 if (not still_open) and focus_ok else
                                 f"Escape pressed: panel still open={still_open}, focus in nav={focus_ok} "
                                 "(CSS-only hover/focus panel has no Escape handling)"))
                        elif not kb_open:
                            add("IC-NAV-08", "nav", SEV_REQUIRED, None,
                                "panel never opened via keyboard; Escape probe not applicable", skip=True)
                    else:
                        add("IC-NAV-07", "nav", SEV_REQUIRED, None,
                            "nav tabs have no mega panels in this lane", skip=True)
                        add("IC-NAV-08", "nav", SEV_REQUIRED, None,
                            "nav tabs have no mega panels in this lane", skip=True)
                else:
                    for chk in ("IC-NAV-06", "IC-NAV-07", "IC-NAV-08"):
                        add(chk, "nav", SEV_REQUIRED, None,
                            "no disclosure-nav instances detected in this lane", skip=True)

                # ---------- lang probes
                lang = page.locator("details.cs-nav-lang").first
                if lang.count() and not budget.exhausted:
                    summary = lang.locator("summary").first
                    summary.focus()
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(150)
                    open_after_enter = lang.evaluate("el => el.open")
                    page.keyboard.press(" ")
                    page.wait_for_timeout(150)
                    toggled_back = lang.evaluate("el => el.open") != open_after_enter
                    add("IC-LANG-05", "lang", SEV_REQUIRED, open_after_enter and toggled_back,
                        (f"Enter opens (open={open_after_enter}), Space toggles back={toggled_back}"
                         if open_after_enter and toggled_back else
                         f"keyboard toggling broken: Enter->open={open_after_enter}, Space toggled={toggled_back}"))
                    # ensure open for Escape probe
                    lang.evaluate("el => { el.open = true; }")
                    summary.focus()
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(150)
                    closed = not lang.evaluate("el => el.open")
                    add("IC-LANG-06", "lang", SEV_REQUIRED, closed,
                        ("Escape closes the language dropdown" if closed else
                         "Escape does not close the open language dropdown (native details has no Escape handling)"))
                    lang.evaluate("el => { el.open = true; }")
                    summary.focus()
                    page.keyboard.press("Tab")
                    in_menu = page.evaluate(
                        "() => !!(document.activeElement && document.activeElement.closest('.cs-nav-lang'))")
                    add("IC-LANG-07", "lang", SEV_ADVISORY, in_menu,
                        ("open dropdown items are in the Tab order" if in_menu else
                         "Tab from the open toggle does not reach the locale items"))
                    lang.evaluate("el => { el.open = false; }")
                else:
                    for chk, sev in (("IC-LANG-05", SEV_REQUIRED), ("IC-LANG-06", SEV_REQUIRED),
                                     ("IC-LANG-07", SEV_ADVISORY)):
                        add(chk, "lang", sev, None,
                            "no language-switcher instances detected in this lane", skip=True)

                # ---------- accordion probes
                acc_groups = page.evaluate("""() => {
                  const dets = [...document.querySelectorAll('details')]
                    .filter(d => !d.closest('.cs-nav-lang') && !d.querySelector('a[hreflang]'));
                  const byParent = new Map();
                  dets.forEach(d => {
                    const k = d.parentElement;
                    if (!byParent.has(k)) byParent.set(k, []);
                    byParent.get(k).push(d);
                  });
                    let idx = 0; const groups = [];
                  for (const [, arr] of byParent) {
                    if (arr.length >= 2) {
                      arr.forEach((d, i) => d.setAttribute('data-ic-acc', idx + ':' + i));
                      groups.push({size: arr.length, named: arr.every(d => d.getAttribute('name')) &&
                                   new Set(arr.map(d => d.getAttribute('name'))).size === 1,
                                   multi: (arr[0].parentElement.getAttribute('data-acc-multi') || '')
                                     .toLowerCase() === 'authored'});
                      idx += 1;
                    }
                  }
                  return groups;
                }""")
                if acc_groups and not budget.exhausted:
                    first = page.locator('[data-ic-acc="0:0"]')
                    second = page.locator('[data-ic-acc="0:1"]')
                    s1 = first.locator("summary").first
                    s2 = second.locator("summary").first
                    # IC-ACC-06 Enter/Space toggling on item 1
                    initial = first.evaluate("el => el.open")
                    s1.focus()
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(120)
                    after_enter = first.evaluate("el => el.open")
                    page.keyboard.press(" ")
                    page.wait_for_timeout(120)
                    after_space = first.evaluate("el => el.open")
                    toggles = (after_enter != initial) and (after_space == initial)
                    add("IC-ACC-06", "acc", SEV_REQUIRED, toggles,
                        ("summary focusable; Enter and Space toggle the panel" if toggles else
                         f"toggle sequence broken: initial={initial}, after Enter={after_enter}, after Space={after_space}"))
                    # IC-ACC-07 single-open holds — probe group 0 and, if different,
                    # the first unnamed group (the likely offender). A group whose
                    # parent DECLARES multi-open (data-acc-multi="authored") is
                    # probed for the opposite: independent toggling must hold.
                    probe_idx = [0]
                    unnamed_idx = next((i for i, g in enumerate(acc_groups) if not g["named"]), None)
                    if unnamed_idx is not None and unnamed_idx != 0:
                        probe_idx.append(unnamed_idx)
                    for gi in probe_idx:
                        g_first = page.locator(f'[data-ic-acc="{gi}:0"]')
                        g_second = page.locator(f'[data-ic-acc="{gi}:1"]')
                        g_first.evaluate("el => { el.open = true; }")
                        g_second.locator("summary").first.focus()
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(120)
                        one_closed = not g_first.evaluate("el => el.open")
                        two_open = g_second.evaluate("el => el.open")
                        if acc_groups[gi].get("multi") and not acc_groups[gi]["named"]:
                            tag = (f"group {gi} (declared multi-open, "
                                   f"{acc_groups[gi]['size']} items)")
                            add("IC-ACC-07", "acc", SEV_REQUIRED, (not one_closed) and two_open,
                                (f"{tag}: items toggle independently (authored multi-open holds)"
                                 if (not one_closed) and two_open else
                                 f"{tag}: independent toggling broken — item1 open={not one_closed}, "
                                 f"item2 open={two_open}"))
                        else:
                            tag = f"group {gi} ({'named' if acc_groups[gi]['named'] else 'no name attr'}, {acc_groups[gi]['size']} items)"
                            add("IC-ACC-07", "acc", SEV_REQUIRED, one_closed and two_open,
                                (f"{tag}: opening item 2 closes item 1 (exclusive group holds)"
                                 if one_closed and two_open else
                                 f"{tag}: single-open does not hold — item1 open={not one_closed}, item2 open={two_open}"))
                        g_second.evaluate("el => { el.open = false; }")
                    # IC-ACC-08 revealed content visible
                    second.evaluate("el => { el.open = true; }")
                    page.wait_for_timeout(120)
                    content_visible = second.evaluate("""el => {
                      const kids = [...el.children].filter(c => c.tagName !== 'SUMMARY');
                      return kids.some(c => { const r = c.getBoundingClientRect();
                                              return r.height > 4 && r.width > 4; });
                    }""")
                    add("IC-ACC-08", "acc", SEV_REQUIRED, content_visible,
                        ("opened panel content is rendered and visible" if content_visible else
                         "opened panel content has no visible box"))
                    second.evaluate("el => { el.open = false; }")
                else:
                    for chk in ("IC-ACC-06", "IC-ACC-07", "IC-ACC-08"):
                        add(chk, "acc", SEV_REQUIRED, None,
                            "no accordion groups detected in this lane", skip=True)

                # ---------- banner probe
                closer = page.locator("button.cs-utility-banner-close").first
                if closer.count() and not budget.exhausted:
                    container = page.locator("#page-banner, .cs-utility-banner").first
                    closer.focus()
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(250)
                    gone = not container.count() or not bool(container.evaluate(JS_VISIBLE))
                    add("IC-BAN-04", "banner", SEV_REQUIRED, gone,
                        ("keyboard activation dismisses the banner" if gone else
                         "close button focused and Enter pressed — banner still visible (no dismiss handler wired)"))
                else:
                    add("IC-BAN-04", "banner", SEV_REQUIRED, None,
                        "no dismissible banner detected in this lane", skip=True)

                # ---------- carousel rail probe
                rail = page.locator(".cs-edgecut").first
                if rail.count() and not budget.exhausted:
                    result = rail.evaluate("""el => {
                      const out = {overflow: el.scrollWidth > el.clientWidth + 4,
                                   focusable: false, scrolled: false, childFocus: false};
                      el.focus();
                      out.focusable = document.activeElement === el;
                      if (out.focusable) {
                        el.scrollLeft = 0;
                        const evt = new KeyboardEvent('keydown', {key: 'ArrowRight', bubbles: true});
                        el.dispatchEvent(evt);
                      }
                      const focusables = el.querySelectorAll('a[href], button, input, select, textarea, [tabindex]');
                      out.childFocus = focusables.length > 0;
                      return out;
                    }""")
                    if not result["overflow"]:
                        add("IC-CAR-05", "carousel", SEV_REQUIRED, None,
                            "rail does not overflow at this viewport; keyboard-scroll probe not applicable",
                            skip=True)
                    else:
                        operable = False
                        detail = ""
                        if result["focusable"]:
                            # deterministic start state (remediation 2026-07): earlier
                            # probes (Tab reachability walks) may have auto-scrolled the
                            # rail to reveal focused children — a rail already at max
                            # scroll cannot demonstrate ArrowRight movement. Reset to 0;
                            # the requirement itself is unchanged.
                            rail.evaluate("el => { el.scrollLeft = 0; }")
                            rail.focus()
                            before = rail.evaluate("el => el.scrollLeft")
                            page.keyboard.press("ArrowRight")
                            page.keyboard.press("ArrowRight")
                            page.wait_for_timeout(200)
                            after = rail.evaluate("el => el.scrollLeft")
                            operable = after > before
                            detail = f"rail focusable; ArrowRight scrolls: {before}->{after}"
                        elif result["childFocus"]:
                            scrolled = rail.evaluate("""el => {
                              const f = el.querySelectorAll('a[href], button, input, select, textarea, [tabindex]');
                              const last = f[f.length - 1];
                              el.scrollLeft = 0; last.focus();
                              return el.scrollLeft > 0 || last.getBoundingClientRect().right <= innerWidth;
                            }""")
                            operable = bool(scrolled)
                            detail = "no rail focus; overflowed content reachable via focusable children"
                        else:
                            detail = ("rail not keyboard-focusable and contains no focusable children — "
                                      "overflowed content unreachable without a pointer")
                        add("IC-CAR-05", "carousel", SEV_REQUIRED, operable, detail)
                else:
                    add("IC-CAR-05", "carousel", SEV_REQUIRED, None,
                        "no carousel/edge-cut rail detected in this lane", skip=True)

                # ---------- tabs probes (IC-TAB-05/06, fix1 2026-07)
                tablist = page.locator('[role="tablist"]').first
                if tablist.count() and not budget.exhausted:
                    tabs_loc = page.locator('[role="tablist"] [role="tab"]')
                    n_tabs = tabs_loc.count()
                    if n_tabs >= 2:
                        state_js = """() => {
                          const tabs = [...document.querySelectorAll('[role="tablist"] [role="tab"]')];
                          const sel = tabs.findIndex(t => t.getAttribute('aria-selected') === 'true');
                          const foc = tabs.indexOf(document.activeElement);
                          const panels = [...document.querySelectorAll('[role="tabpanel"]')];
                          const vis = panels.filter(p => !p.hidden);
                          const wired = vis.length === 1 && sel >= 0 &&
                            tabs[sel].getAttribute('aria-controls') === vis[0].id;
                          return {sel, foc, visCount: vis.length, wired};
                        }"""
                        tabs_loc.nth(0).focus()
                        page.keyboard.press("ArrowRight")
                        page.wait_for_timeout(150)
                        s1 = page.evaluate(state_js)
                        arrows_ok = s1["foc"] == 1 and s1["sel"] == 1 and s1["wired"]
                        page.keyboard.press("ArrowLeft")
                        page.wait_for_timeout(150)
                        s2 = page.evaluate(state_js)
                        arrows_ok = arrows_ok and s2["foc"] == 0 and s2["sel"] == 0 \
                            and s2["wired"]
                        add("IC-TAB-05", "tabs", SEV_REQUIRED, arrows_ok,
                            ("ArrowRight/ArrowLeft move focus and selection; the visible "
                             "panel follows" if arrows_ok else
                             f"arrow-key state broken: after → focus={s1['foc']} sel={s1['sel']} "
                             f"wired={s1['wired']}; after ← focus={s2['foc']} sel={s2['sel']} "
                             f"wired={s2['wired']}"))
                        page.keyboard.press("End")
                        page.wait_for_timeout(150)
                        s3 = page.evaluate(state_js)
                        home_end_ok = s3["foc"] == n_tabs - 1 and s3["sel"] == n_tabs - 1 \
                            and s3["wired"]
                        page.keyboard.press("Home")
                        page.wait_for_timeout(150)
                        s4 = page.evaluate(state_js)
                        home_end_ok = home_end_ok and s4["foc"] == 0 and s4["sel"] == 0 \
                            and s4["wired"]
                        tabs_loc.nth(1).click()
                        page.wait_for_timeout(150)
                        s5 = page.evaluate(state_js)
                        click_ok = s5["sel"] == 1 and s5["wired"]
                        tabs_loc.nth(0).click()
                        page.wait_for_timeout(100)
                        add("IC-TAB-06", "tabs", SEV_REQUIRED, home_end_ok and click_ok,
                            ("Home/End jump selection; click selects (pointer parity)"
                             if home_end_ok and click_ok else
                             f"Home/End/click broken: End sel={s3['sel']} Home sel={s4['sel']} "
                             f"click sel={s5['sel']} wired={s5['wired']}"))
                    else:
                        for chk in ("IC-TAB-05", "IC-TAB-06"):
                            add(chk, "tabs", SEV_REQUIRED, None,
                                "tab device has fewer than two tabs; keyboard probes not applicable",
                                skip=True)
                else:
                    for chk in ("IC-TAB-05", "IC-TAB-06"):
                        add(chk, "tabs", SEV_REQUIRED, None,
                            "no tab devices detected in this lane", skip=True)

                context.close()

                # ---------- reduced-motion context: marquee + reveal
                rm_context = browser.new_context(reduced_motion="reduce",
                                                 viewport={"width": 1440, "height": 900})
                rm_context.set_default_timeout(5000)
                rm_page = rm_context.new_page()
                rm_page.goto(url, wait_until="load", timeout=30000)
                rm_page.wait_for_timeout(200)

                track = rm_page.locator(".cs-marquee-track").first
                if track.count():
                    anim = track.evaluate(
                        "el => { const cs = getComputedStyle(el); return {name: cs.animationName, state: cs.animationPlayState}; }")
                    visible = bool(track.evaluate(JS_VISIBLE))
                    calmed = anim["name"] in ("none", "") or anim["state"] == "paused"
                    add("IC-MARQ-03", "marquee", SEV_REQUIRED, calmed and visible,
                        (f"reduced motion: animation={anim['name']}/{anim['state']}, content visible={visible}"))
                else:
                    add("IC-MARQ-03", "marquee", SEV_REQUIRED, None,
                        "no marquee detected in this lane", skip=True)

                reveal_machinery = rm_page.evaluate(
                    "() => [...document.scripts].some(s => (s.textContent || '').includes('cs-reveal'))"
                    " || [...document.querySelectorAll('style')].some(s => (s.textContent || '').includes('cs-reveal'))")
                if reveal_machinery:
                    reveal_state = rm_page.evaluate("""() => {
                      const gated = document.documentElement.classList.contains('cs-motion-ready');
                      const targets = [...document.querySelectorAll('.cs-reveal')];
                      const hidden = targets.filter(t => parseFloat(getComputedStyle(t).opacity) < 0.9);
                      return {gated, tagged: targets.length, hidden: hidden.length};
                    }""")
                    # contract: under reduced motion, nothing gated-hidden. Either the
                    # script bails before gating (gated=false, tagged=0) or every
                    # tagged target still computes visible.
                    ok = reveal_state["hidden"] == 0
                    add("IC-REV-04", "reveal", SEV_REQUIRED, ok,
                        (f"reduced motion: gate applied={reveal_state['gated']}, "
                         f"{reveal_state['tagged']} tagged targets, {reveal_state['hidden']} hidden"))
                else:
                    add("IC-REV-04", "reveal", SEV_REQUIRED, None,
                        "no scroll-reveal machinery detected in this lane", skip=True)

                # ---------- form accessible-name probe (fresh default context)
                form_count = rm_page.evaluate(
                    "() => document.querySelectorAll('input, select, textarea').length")
                if form_count:
                    unnamed = rm_page.evaluate("""(fnSrc) => {
                      const named = eval(fnSrc);
                      const skip = new Set(['hidden', 'submit', 'button', 'reset', 'image']);
                      const out = [];
                      for (const el of document.querySelectorAll('input, select, textarea')) {
                        if (el.tagName === 'INPUT' && skip.has((el.type || 'text'))) continue;
                        if (!named(el)) out.push(el.id || el.name || el.type || el.tagName.toLowerCase());
                      }
                      return out;
                    }""", JS_CONTROL_NAMED)
                    add("IC-FORM-07", "form", SEV_REQUIRED, not unnamed,
                        ("all visible form controls have browser-computed labels" if not unnamed else
                         f"controls with empty computed accessible name: {', '.join(unnamed[:6])}"))
                else:
                    add("IC-FORM-07", "form", SEV_REQUIRED, None,
                        "no form controls detected in this lane", skip=True)

                rm_context.close()
            finally:
                browser.close()
    except Exception as exc:
        findings.append(Finding(
            check="IC-BEHAVIORAL", family="nav", severity=SEV_REQUIRED, status="skip",
            lane=lane, layer="behavioral",
            message=f"behavioral layer aborted: {type(exc).__name__}: {exc}"))
    if budget.exhausted:
        findings.append(Finding(
            check="IC-BUDGET", family="nav", severity=SEV_ADVISORY, status="skip",
            lane=lane, layer="behavioral",
            message=f"lane budget of {timeout_s:.0f}s exhausted; some probes may have been skipped"))
    return findings


# ----------------------------------------------------------------------- report

def _lane_name(path: Path) -> str:
    p = path.resolve()
    for anchor in ("brand",):
        parts = p.parts
        if anchor in parts:
            idx = parts.index(anchor)
            rel = Path(*parts[idx + 1:])
            name = str(rel.parent) if rel.name == "index.html" else str(rel)
            return name if name != "." else rel.name
    return str(p.parent.name)


def _aggregate(findings: list[Finding]) -> dict[tuple[str, str, str], str]:
    """(lane, family, check) -> worst status. fail > advisory > pass > skip."""
    rank = {"fail": 3, "advisory": 2, "pass": 1, "skip": 0}
    cells: dict[tuple[str, str, str], str] = {}
    for f in findings:
        key = (f.lane, f.family, f.check)
        if key not in cells or rank[f.status] > rank[cells[key]]:
            cells[key] = f.status
    return cells


def write_reports(out_dir: Path, lanes: list[LaneResult], strict: bool) -> tuple[Path, Path, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    all_findings = [f for lr in lanes for f in lr.findings]
    cells = _aggregate(all_findings)

    counts = {"pass": 0, "fail": 0, "advisory": 0, "skip": 0}
    for status in cells.values():
        counts[status] += 1

    required_fail_checks: dict[str, list[str]] = {}
    for (lane, _family, check), status in cells.items():
        if status == "fail":
            sample = next(f for f in all_findings
                          if f.lane == lane and f.check == check and f.status == "fail")
            if sample.severity == SEV_REQUIRED:
                required_fail_checks.setdefault(check, []).append(lane)

    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "generated_at": generated,
        "auditor_version": AUDITOR_VERSION,
        "spec": "brand_pipeline/spec/interaction-contracts.md",
        "mode": "strict" if strict else "baseline",
        "summary": {
            "cells": counts,
            "required_check_failures": {
                check: sorted(set(lanes_)) for check, lanes_ in sorted(required_fail_checks.items())
            },
        },
        "lanes": [
            {
                "lane": lr.lane,
                "path": lr.path,
                "audited_mtime": lr.mtime_iso,
                "sha256_12": lr.sha256_12,
                "findings": [asdict(f) for f in lr.findings],
            }
            for lr in lanes
        ],
    }
    json_path = out_dir / "report.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # ------- human report
    lines: list[str] = []
    lines.append("# Interaction-Contract Baseline Report")
    lines.append("")
    lines.append(f"Generated: {generated} — auditor v{AUDITOR_VERSION} — mode: "
                 f"{'strict' if strict else 'baseline (measurement only, exit 0)'}")
    lines.append("Contracts: `brand_pipeline/spec/interaction-contracts.md` "
                 "(WAI-ARIA APG primary; Base UI secondary; Radix tertiary)")
    lines.append("")
    lines.append("## Audited lanes")
    lines.append("")
    lines.append("| lane | file | mtime (UTC) | sha256/12 |")
    lines.append("|---|---|---|---|")
    for lr in lanes:
        lines.append(f"| {lr.lane} | `{lr.path}` | {lr.mtime_iso} | `{lr.sha256_12}` |")
    lines.append("")
    lines.append("If a lane is re-rendered by another agent, re-run the audit; the mtime/sha above "
                 "identify exactly which HTML was measured.")
    lines.append("")
    lines.append(f"## Summary — {counts['fail']} failing required cells, "
                 f"{counts['advisory']} advisory, {counts['pass']} passing, {counts['skip']} skipped")
    lines.append("")
    lines.append("### Most impactful gaps (required checks failing, by lane count)")
    lines.append("")
    ordered = sorted(required_fail_checks.items(), key=lambda kv: (-len(set(kv[1])), kv[0]))
    if ordered:
        for check, lanes_hit in ordered:
            uniq = sorted(set(lanes_hit))
            sample = next(f for f in all_findings if f.check == check and f.status == "fail")
            lines.append(f"- **{check}** ({sample.family}) — fails in {len(uniq)} lane(s): "
                         f"{', '.join(uniq)} — {sample.message}")
    else:
        lines.append("- none — all required checks pass")
    lines.append("")

    for lr in lanes:
        lines.append(f"## Lane: {lr.lane}")
        lines.append("")
        lines.append("| check | family | severity | layer | status | detail |")
        lines.append("|---|---|---|---|---|---|")
        rank = {"fail": 0, "advisory": 1, "pass": 2, "skip": 3}
        for f in sorted(lr.findings, key=lambda x: (rank[x.status], x.family, x.check)):
            loc = f" (line {f.line})" if f.line else ""
            msg = f.message.replace("|", "\\|")
            lines.append(f"| {f.check} | {f.family} | {f.severity} | {f.layer} | "
                         f"**{f.status}** | {msg}{loc} |")
        lines.append("")

    md_path = out_dir / "report.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, json_path, counts["fail"]


# -------------------------------------------------------------------------- cli

def _collect_lane_files(args_paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in args_paths:
        p = Path(raw)
        if p.is_dir():
            direct = p / "index.html"
            if direct.exists():
                files.append(direct)
            else:
                files.extend(sorted(p.rglob("index.html")))
        elif p.exists():
            files.append(p)
        else:
            print(f"warning: path not found, skipping: {p}", file=sys.stderr)
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in files:
        r = f.resolve()
        if r not in seen:
            seen.add(r)
            unique.append(r)
    return unique


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="interaction_audit",
        description="Audit composed HTML lanes against the interaction contracts "
                    "(brand_pipeline/spec/interaction-contracts.md).")
    parser.add_argument("paths", nargs="+", help="lane index.html files or directories")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help=f"report output directory (default: {DEFAULT_OUT})")
    parser.add_argument("--static-only", action="store_true",
                        help="skip the Playwright behavioral layer")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when any REQUIRED check fails (gate mode)")
    parser.add_argument("--lane-timeout", type=float, default=120.0,
                        help="hard budget per lane for the behavioral layer (seconds)")
    args = parser.parse_args(argv)

    lane_files = _collect_lane_files(args.paths)
    if not lane_files:
        print("error: no lane HTML files found", file=sys.stderr)
        return 2

    results: list[LaneResult] = []
    for path in lane_files:
        lane = _lane_name(path)
        html_text = path.read_text(encoding="utf-8", errors="replace")
        stat = path.stat()
        lr = LaneResult(
            lane=lane,
            path=str(path),
            mtime_iso=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
            sha256_12=hashlib.sha256(html_text.encode("utf-8")).hexdigest()[:12],
        )
        print(f"[static]     {lane} … ", end="", flush=True)
        lr.findings.extend(audit_static(html_text, lane))
        print(f"{sum(1 for f in lr.findings if f.status == 'fail')} required fails")
        if not args.static_only:
            print(f"[behavioral] {lane} … ", end="", flush=True)
            t0 = time.monotonic()
            behavioral = audit_behavioral(path, lane, timeout_s=args.lane_timeout)
            lr.findings.extend(behavioral)
            print(f"{sum(1 for f in behavioral if f.status == 'fail')} required fails "
                  f"({time.monotonic() - t0:.1f}s)")
        results.append(lr)

    out_dir = Path(args.out)
    md_path, json_path, fail_cells = write_reports(out_dir, results, strict=args.strict)
    print(f"\nreport: {md_path}\nreport: {json_path}")
    print(f"failing required cells: {fail_cells}")
    if args.strict and fail_cells:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
