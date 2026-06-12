"""Tests for live-URL nav/footer chrome extraction."""

from screenshot_to_template.chrome_extractor import extract_chrome_from_html
from screenshot_to_template.chrome_codegen import render_site_nav_tsx, render_site_footer_tsx


SAMPLE = """
<!DOCTYPE html><html><body>
<header class="sticky top-0 flex justify-between">
  <a href="/"><img src="/logo.svg" alt="Acme Co" /></a>
  <nav>
    <a href="/platform">Platform</a>
    <a href="/pricing">Pricing</a>
  </nav>
  <a href="/demo" class="btn-cta">Book a demo</a>
</header>
<main><h1>Hero</h1></main>
<footer>
  <h4>Product</h4>
  <a href="/features">Features</a>
  <a href="/security">Security</a>
  <h4>Company</h4>
  <a href="/about">About</a>
  <p>© 2026 Acme</p>
</footer>
</body></html>
"""


def test_extract_nav_and_footer_links():
    contract = extract_chrome_from_html(SAMPLE, "https://example.com", source_url="https://example.com")
    assert contract["schema_version"] == "source_chrome.v1"
    assert contract["nav"]["found"] is True
    labels = [ln["label"] for ln in contract["nav"]["links"]]
    assert "Platform" in labels
    assert "Pricing" in labels
    assert contract["footer"]["found"] is True
    cols = contract["footer"]["columns"]
    assert len(cols) >= 1
    all_footer = [ln["label"] for col in cols for ln in col["links"]]
    assert "Features" in all_footer or "About" in all_footer


def test_codegen_emits_site_nav_and_footer():
    contract = extract_chrome_from_html(SAMPLE, "https://example.com")
    nav_tsx = render_site_nav_tsx(contract)
    foot_tsx = render_site_footer_tsx(contract)
    assert "SiteNav" in nav_tsx
    assert "Platform" in nav_tsx
    assert "SiteFooter" in foot_tsx
    assert "Features" in foot_tsx or "About" in foot_tsx
