import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from screenshot_to_template import source_colors
from screenshot_to_template.source_colors import (
    append_source_font_implementation,
    build_source_font_implementation_css,
    extract_source_colors,
    render_source_color_report,
)
from screenshot_to_template.source_style_ledger import (
    build_source_style_ledger,
    reconcile_document_styles,
    source_style_ledger_prompt_block,
)


class SourceStyleExtractionTests(unittest.TestCase):
    def test_extracts_downloads_and_reports_source_fonts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            font_dir = root / "fonts"
            font_dir.mkdir()
            (font_dir / "acme.woff2").write_bytes(b"fake-font-bytes")
            html_path = root / "source.html"
            html_path.write_text(
                """
<!doctype html>
<html>
  <head>
    <style>
      @font-face {
        font-family: "Acme Sans";
        src: url("fonts/acme.woff2") format("woff2");
        font-weight: 400 700;
        font-style: normal;
        font-display: swap;
      }
      :root { --brand: #abc; }
      :root {
        --_typography---fonts--primary-font: "Acme Sans", Arial, sans-serif;
        --_typography---fonts--secondary-font: "Acme Display", Arial, sans-serif;
        --_typography---h1--font: var(--_typography---fonts--secondary-font);
      }
      h1, p, button {
        font-family: "Acme Sans", Arial, sans-serif;
        font-size: 24px;
        font-weight: 600;
        line-height: 1.2;
      }
    </style>
  </head>
  <body>
    <h1 style="letter-spacing: 0.01em; color: rgb(1, 2, 3)">Hello</h1>
  </body>
</html>
""",
                encoding="utf-8",
            )

            extracted = extract_source_colors(html_path, font_assets_dir=root / "source-fonts")

            self.assertEqual(extracted["inline_style_count"], 1)
            self.assertEqual(extracted["font_faces"][0]["font_family"], "Acme Sans")
            self.assertEqual(extracted["font_faces"][0]["relative_path"], "source-fonts/01-acme-sans-400-700-normal.woff2")
            self.assertTrue((root / extracted["font_faces"][0]["relative_path"]).exists())
            self.assertIn("Acme Sans", extracted["source_font_stack"])
            self.assertEqual(extracted["source_heading_font_stack"], '"Acme Display", Arial, sans-serif')
            self.assertIn("0.01em", {entry["value"] for entry in extracted["frequent_letter_spacings"]})

            report = render_source_color_report(extracted)
            self.assertIn("## Source Font Implementation CSS", report)
            self.assertIn("@font-face", report)

            markdown = append_source_font_implementation("# Design System\n", extracted)
            self.assertIn("## Source Font Implementation", markdown)
            self.assertIn("source-fonts/01-acme-sans-400-700-normal.woff2", markdown)

    def test_source_font_css_resolves_frequent_font_family_variables(self) -> None:
        extracted = {
            "font_faces": [
                {
                    "font_family": "Seasonsans",
                    "source_url": "https://example.com/SeasonSans.woff2",
                    "format": "woff2",
                    "font_weight": "500",
                    "font_style": "normal",
                    "font_display": "swap",
                }
            ],
            "frequent_font_families": [
                {"value": "var(--_typography---font-styles--heading)", "count": 8},
                {"value": "var(--_typography---font-styles--body)", "count": 5},
            ],
            "typography_custom_properties": {
                "--_typography---font-styles--heading": "Seasonsans, Arial, sans-serif",
                "--_typography---font-styles--body": "Seasonsans, Arial, sans-serif",
            },
        }

        css = build_source_font_implementation_css(extracted)

        self.assertIn("--stt-source-font-family: Seasonsans, Arial, sans-serif;", css)
        self.assertNotIn("var(--_typography", css)
        self.assertIn("h1, h2, h3, h4, h5, h6", css)
        self.assertIn("font-family: var(--stt-source-font-family) !important", css)

    def test_extracts_google_webfont_loader_faces(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "source.html"
            html_path.write_text(
                """
<!doctype html>
<html>
  <head>
    <script>
      WebFont.load({
        google: {
          families: ["Old Standard TT:regular", "Be Vietnam Pro:300,regular", "Old Standard TT:700"]
        }
      });
    </script>
    <style>
      h1 { font-family: Old Standard TT, sans-serif; }
      h1 em { font-style: italic; }
      body { font-family: Be Vietnam Pro, sans-serif; }
    </style>
  </head>
</html>
""",
                encoding="utf-8",
            )
            google_css = """
@font-face {
  font-family: 'Old Standard TT';
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url(https://fonts.gstatic.com/old-regular.woff2) format('woff2');
}
@font-face {
  font-family: 'Old Standard TT';
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url(https://fonts.gstatic.com/old-bold.woff2) format('woff2');
}
@font-face {
  font-family: 'Be Vietnam Pro';
  font-style: normal;
  font-weight: 300;
  font-display: swap;
  src: url(https://fonts.gstatic.com/vietnam-300.woff2) format('woff2');
}
"""

            def fake_get(url: str, *args, **kwargs):
                class Response:
                    text = google_css
                    content = b"font"

                    def raise_for_status(self) -> None:
                        return None

                self.assertIn("fonts.google", url)
                return Response()

            def fake_download(url: str, output_path: Path, timeout_s: int = 30) -> str:
                output_path.write_bytes(url.encode("utf-8"))
                return "downloaded"

            with patch.object(source_colors.requests, "get", side_effect=fake_get):
                with patch.object(source_colors, "_download_font_asset", side_effect=fake_download):
                    extracted = extract_source_colors(html_path, font_assets_dir=root / "source-fonts")

            families = {(face["font_family"], face["font_weight"]) for face in extracted["font_faces"]}
            self.assertIn(("Old Standard TT", "400"), families)
            self.assertIn(("Old Standard TT", "700"), families)
            self.assertIn(("Be Vietnam Pro", "300"), families)
            self.assertEqual(extracted["source_font_stack"], "Be Vietnam Pro, sans-serif")
            self.assertEqual(extracted["source_decorative_italic_font_stack"], "Old Standard TT, sans-serif")
            css = build_source_font_implementation_css(extracted)
            self.assertIn("source-fonts/01-old-standard-tt-400-normal.woff2", css)
            self.assertIn("font-family: var(--stt-source-font-family) !important", css)
            self.assertIn("--stt-source-decorative-italic-font-family: Old Standard TT, sans-serif", css)
            self.assertIn("h1 em, h2 em", css)

    def test_extracts_font_from_unwrapped_vendor_asset_url(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "source.html"
            html_path.write_text(
                """
<!doctype html>
<html>
  <head>
    <style>
      @font-face {
        font-family: Seasonsans;
        src: url("/vendor-assets/cdn.prod.website-files.com/site/font.woff2") format("woff2");
        font-weight: 500;
        font-style: normal;
      }
      body { font-family: Seasonsans, Arial, sans-serif; }
    </style>
  </head>
</html>
""",
                encoding="utf-8",
            )

            def fake_download(url: str, output_path: Path, timeout_s: int = 30) -> str:
                self.assertEqual(url, "https://cdn.prod.website-files.com/site/font.woff2")
                output_path.write_bytes(b"font")
                return "downloaded"

            with patch.object(source_colors, "_download_font_asset", side_effect=fake_download):
                extracted = extract_source_colors(html_path, font_assets_dir=root / "source-fonts")

            self.assertEqual(extracted["font_faces"][0]["status"], "downloaded")
            self.assertEqual(extracted["font_faces"][0]["source_url"], "https://cdn.prod.website-files.com/site/font.woff2")
            self.assertTrue((root / extracted["font_faces"][0]["relative_path"]).exists())

    def test_extracts_font_face_from_later_src_when_first_download_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "source.html"
            html_path.write_text(
                """
<!doctype html>
<html>
  <head>
    <style>
      @font-face {
        font-family: "Fallback Sans";
        src: url("https://example.com/font.woff2") format("woff2"),
             url("https://example.com/font.woff") format("woff");
        font-weight: 400;
        font-style: normal;
      }
      body { font-family: "Fallback Sans", Arial, sans-serif; }
    </style>
  </head>
</html>
""",
                encoding="utf-8",
            )

            def fake_download(url: str, output_path: Path, timeout_s: int = 30) -> str:
                if url.endswith(".woff2"):
                    raise RuntimeError("blocked")
                output_path.write_bytes(b"fallback-font")
                return "downloaded"

            with patch.object(source_colors, "_download_font_asset", side_effect=fake_download):
                extracted = extract_source_colors(html_path, font_assets_dir=root / "source-fonts")

            face = extracted["font_faces"][0]
            self.assertEqual(face["status"], "downloaded")
            self.assertEqual(face["source_url"], "https://example.com/font.woff")
            self.assertEqual(face["relative_path"], "source-fonts/01-fallback-sans-400-normal.woff")
            self.assertTrue((root / face["relative_path"]).exists())

    def test_builds_generation_safe_source_style_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            html_path = root / "source.html"
            html_path.write_text(
                """
<!doctype html>
<html>
  <head>
    <style>
      :root {
        --color-canvas: #ffffff;
        --color-action: #2244cc;
        --broken-utility: rgb(var(--tw-text-opacity) / <alpha-value>);
      }
      body { background: #ffffff; color: #111111; font-family: Inter, Arial, sans-serif; }
      .btn-primary { background-color: #2244cc; color: #ffffff; border-color: #2244cc; }
      .card { background-color: #f8f8f4; color: #111111; border: 1px solid rgba(17, 17, 17, 0.12); }
      footer { background: #111111; color: #ffffff; }
    </style>
  </head>
  <body><button class="btn-primary">Start</button></body>
</html>
""",
                encoding="utf-8",
            )

            extracted = extract_source_colors(html_path)
            ledger = build_source_style_ledger(extracted)

            self.assertEqual(ledger["type"], "source_style_ledger")
            generation_values = {
                entry["value"]
                for entry in ledger["palette"]["generation_palette"]
            }
            self.assertIn("#2244CC", generation_values)
            self.assertIn("#FFFFFF", generation_values)
            self.assertNotIn("rgb(var(--tw-text-opacity)/<alpha-value>)", generation_values)
            self.assertTrue(any("action_fill" in entry["role_families"] for entry in ledger["palette"]["generation_palette"]))

            prompt_block = source_style_ledger_prompt_block(ledger)
            self.assertIn("source_style_ledger.v1", prompt_block)
            self.assertIn("generation_palette", prompt_block)

            reconciled, audit = reconcile_document_styles(
                "tokens:\n  primaryAction: '#2344cc'\n",
                extracted,
                ledger,
            )
            self.assertIn("#2244CC", reconciled)
            self.assertEqual(audit["replacement_count"], 1)


if __name__ == "__main__":
    unittest.main()
