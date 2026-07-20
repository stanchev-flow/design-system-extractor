"""Chrome DOM-fidelity tests (nav two-tier + mega rail + logo, footer directory).

Covers the 2026-07 chrome-fidelity pass: the generic saved-DOM parser fixes
(logo-container guard, tab-rail area, sidebar-rail capture, description climb),
the sidebar-rail renderer support, the data-URI logo resolution, and byte-stability
for single-tier / rail-less navs. Deterministic — no browser, no network.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

import yaml

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR / "brand_pipeline"))

import component_render as cr  # noqa: E402
import compose_section as cs  # noqa: E402

V3_BRAND = PROJECT_DIR / "runs" / "hubspot-v3" / "brand" / "brand.yaml"


def _ctx(doc, mega=False):
    ctx = cr.make_context(doc, "surface/primary",
                          ((doc.get("tokens") or {}).get("surfaces") or {}).get("surface/primary", {}))
    ctx.mega_nav = mega
    return ctx


def _v3_doc():
    return yaml.safe_load(V3_BRAND.read_text())


# ── authored v3 chrome structure (from the saved DOM via the generic parser) ──

def test_v3_navbar_is_two_tier_with_regions():
    nav = _v3_doc()["navbar"]
    assert nav.get("twoTier") is True
    tier = nav.get("utilityTier")
    assert isinstance(tier, dict) and tier.get("trailing"), "utilityTier w/ right-region cluster required"
    # right region = login + about; left region = the remaining utility run
    assert any("log in" == str(t).lower() for t in tier["trailing"])


def test_v3_primary_tabs_and_mega_structure():
    nav = _v3_doc()["navbar"]
    labels = [p.get("label") for p in nav.get("primary") or []]
    assert labels == ["Products", "Solutions", "Pricing", "Resources"], labels
    sol = next(p for p in nav["primary"] if p["label"] == "Solutions")
    menu = sol.get("menu") or {}
    # sidebar rail captured from the hidden DOM
    assert menu.get("sidebarTabs") == ["By Use Case", "By Team Size", "Why HubSpot?"]
    heads = [c.get("heading") for c in menu.get("columns") or []]
    for expected in ("Marketing", "Sales", "Customer Service", "Content", "Artificial Intelligence"):
        assert expected in heads, (expected, heads)
    # each item carries a title + description line (screenshot fidelity)
    marketing = next(c for c in menu["columns"] if c["heading"] == "Marketing")
    gen = next(l for l in marketing["links"] if l["label"] == "Generate leads")
    assert gen.get("description", "").startswith("Convert visitors into contacts")


def test_v3_utility_roles_and_language_switcher():
    nav = _v3_doc()["navbar"]
    util = {u.get("label"): u for u in nav.get("utility") or []}
    assert util["Log in"].get("role") == "login"
    lang = util["English"]
    assert lang.get("kind") == "dropdown" and lang.get("role") == "language"
    items = [i.get("label") for i in (lang.get("dropdown") or {}).get("items") or []]
    assert "日本語" in items and "Deutsch" in items and len(items) >= 6
    # open-state paint honestly marked notObserved (panels portal on open)
    assert lang.get("dropdownNotObserved") is True


def test_v3_navbar_ctas_and_logo():
    nav = _v3_doc()["navbar"]
    cta_labels = [c.get("label") for c in nav.get("ctas") or []]
    assert "Get a demo" in cta_labels
    logo = nav.get("logo") or {}
    assert logo.get("srcContract", "").endswith("#nav.logo.src") or logo.get("src")


def test_v3_footer_directory_social_legal():
    foot = _v3_doc()["footer"]
    heads = [c.get("heading") for c in foot.get("columns") or [] if c.get("heading")]
    for expected in ("Popular Features", "Free Tools", "Company", "Customers", "Partners"):
        assert expected in heads, (expected, heads)
    nets = [s.get("network") for s in foot.get("social") or []]
    assert {"facebook", "instagram", "youtube", "linkedin"}.issubset(set(nets))
    legal_links = [l.get("label") for l in (foot.get("legal") or {}).get("links") or []]
    assert "Privacy Policy" in legal_links
    assert (foot.get("legal") or {}).get("text", "").startswith("Copyright")


# ── renderer: two-tier + mega rail + byte-stability ──────────────────────────

def test_render_two_tier_and_mega_rail():
    doc = _v3_doc()
    html = cr.render_navbar(doc, _ctx(doc, mega=True), cs._navbar_props(doc))
    assert "cs-nav--twotier" in html
    assert "cs-nav-tier--utility" in html and "cs-nav-tier--primary" in html
    assert "cs-mega" in html and "cs-mega-rail" in html
    assert "By Use Case" in html
    assert "Convert visitors into contacts" in html  # description rendered


def test_mega_rail_is_fact_gated_byte_stable():
    """A menu WITHOUT sidebarTabs must emit NO rail element (byte-stability)."""
    menu = {"columns": [{"heading": "Group", "area": "main",
                         "links": [{"label": "A", "href": "#"}]}]}
    frag = cr._mega_panel_fragment(menu, "cs-mega-1")
    assert "cs-mega-rail" not in frag
    menu2 = dict(menu, sidebarTabs=["One", "Two"])
    frag2 = cr._mega_panel_fragment(menu2, "cs-mega-1")
    assert "cs-mega-rail" in frag2 and "One" in frag2 and "Two" in frag2


def test_single_tier_nav_has_no_utility_tier_markup():
    """A brand without navbar.utilityTier renders the single-bar grammar."""
    doc = {"navbar": {"primary": [{"label": "Home", "href": "#"}], "twoTier": False},
           "tokens": {"surfaces": {}}}
    html = cr.render_navbar(doc, _ctx(doc), cs._navbar_props(doc))
    assert "cs-nav--twotier" not in html
    assert "cs-nav-tier--utility" not in html


# ── data-URI logo resolution (real captured mark, not a text fallback) ───────

def test_copy_logo_file_decodes_data_uri(tmp_path):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"></svg>'
    data_uri = "data:image/svg+xml;base64," + base64.b64encode(svg).decode()
    out = tmp_path / "assets"
    local = cs._copy_logo_file(tmp_path, data_uri, out)
    assert local == cs.NAV_LOGO_LOCAL
    written = (out / cs.NAV_LOGO_LOCAL).read_bytes()
    assert written == svg


def test_v3_logo_resolves_to_captured_svg(tmp_path):
    doc = _v3_doc()
    brand_dir = V3_BRAND.parent
    res = cs.prepare_nav_logo(doc, brand_dir, tmp_path / "assets")
    assert res == f"assets/{cs.NAV_LOGO_LOCAL}"
    f = tmp_path / "assets" / cs.NAV_LOGO_LOCAL
    assert f.exists() and f.read_text(errors="ignore").lstrip().startswith("<")
    html = cr.render_navbar(doc, _ctx(doc, mega=True), cs._navbar_props(doc))
    assert f"assets/{cs.NAV_LOGO_LOCAL}" in html  # real logo bound, not text wordmark


# ── footer socials + wordmark paint (sprite-symbol resolution + stamping) ─────

def test_footer_social_glyphs_are_standalone_not_sprite_refs():
    """Materialized social glyphs must be real standalone SVG artwork, never a bare
    `<use href="#...">` sprite reference (which paints nothing once extracted)."""
    assets = V3_BRAND.parent / "assets"
    svgs = sorted(assets.glob("social-*.svg"))
    assert len(svgs) >= 5, f"expected materialized social glyphs, found {svgs}"
    for f in svgs:
        t = f.read_text(errors="ignore")
        assert "<use" not in t, f"{f.name} is still a sprite <use> ref"
        assert any(tag in t for tag in ("<path", "<circle", "<polygon", "<g")), f.name


def test_footer_socials_and_wordmark_paint_after_glyph_prep():
    doc = _v3_doc()
    n = cr.prepare_chrome_glyphs(doc, V3_BRAND.parent)
    assert n > 0
    socs = doc["footer"].get("social") or []
    inline = sum(1 for s in socs if (s.get("icon") or {}).get("_inlineSvg"))
    assert inline >= 5, f"social glyphs did not stamp inline SVG ({inline})"
    assert (doc["footer"].get("logo") or {}).get("_dataUri"), "footer wordmark not stamped"
    fc = cr.footer_content(doc)
    assert len(fc.get("socialGlyphs") or []) >= 5
    assert fc.get("footLogo")
    html = cr.render_footer(doc, cr.make_context(doc, "surface/footer", {}), fc)
    assert html.count('c-foot-glyph"') >= 5      # social row paints
    assert "c-foot-wordmark" in html             # wordmark paints


# ── continuation-column baseline alignment (fact-gated, byte-stable) ──────────

def test_footer_continuation_column_reserves_heading_spacer():
    """A headingless continuation column in a HEADED footer reserves a heading-row
    spacer so its first link shares the link-start baseline."""
    doc = {"footer": {"columns": [
        {"heading": "Popular", "links": [{"label": "A", "href": "#"}]},
        {"heading": "", "links": [{"label": "B", "href": "#"}]},
    ]}, "tokens": {"surfaces": {}}}
    html = cr.render_footer(doc, cr.make_context(doc, "surface/footer", {}),
                            {"columns": doc["footer"]["columns"]})
    assert "c-foot-col-head--spacer" in html


def test_footer_all_headless_columns_have_no_spacer_byte_stable():
    """A footer whose columns are ALL headingless (no headed siblings) emits no
    spacer — byte-stable for footers that don't have the continuation pattern."""
    doc = {"footer": {"columns": [
        {"heading": "", "links": [{"label": "A", "href": "#"}]},
        {"heading": "", "links": [{"label": "B", "href": "#"}]},
    ]}, "tokens": {"surfaces": {}}}
    html = cr.render_footer(doc, cr.make_context(doc, "surface/footer", {}),
                            {"columns": doc["footer"]["columns"]})
    assert "c-foot-col-head--spacer" not in html


# ── bottom-bar measured spacing (copyright↔legal not cramped) ────────────────

def test_footer_bottom_bar_gap_is_measured_not_zero():
    foot = _v3_doc()["footer"]
    gap = (foot.get("bottomBar") or {}).get("gap")
    assert isinstance(gap, (int, float)) and gap >= 12, f"bottom-bar gap too tight: {gap}"
    fc = cr.footer_content(_v3_doc())
    assert fc.get("bbGap") == gap
    html = cr.render_footer(_v3_doc(), cr.make_context(_v3_doc(), "surface/footer", {}), fc)
    assert f"--cf-bb-gap: {int(gap)}px" in html
