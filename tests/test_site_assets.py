import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import screenshot_to_template.site_assets as site_assets
from screenshot_to_template.config import AppConfig
from screenshot_to_template.site_assets import (
    ASSET_BRIEF_ATTRIBUTE,
    apply_generated_site_assets,
    _png_has_meaningful_transparency,
    _annotate_dom_nodes,
    _asset_should_have_transparent_background,
    _asset_generation_skip_reason,
    _build_asset_plan,
    _build_asset_prompt,
    _build_asset_style_profile,
    _choose_chroma_key_color,
    _choose_reference_image_for_asset,
    _generate_image_with_retries,
    _inject_asset_scan_script,
    _merge_asset_candidates,
    _remove_chroma_key_background,
    _rewrite_html_with_assets,
    _scan_asset_candidates,
    _static_asset_candidates,
    _write_png_asset,
)


class SiteAssetRewriteTests(unittest.TestCase):
    def test_png_transparency_detection_distinguishes_alpha_content(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as temp_dir:
            transparent_path = Path(temp_dir) / "transparent.png"
            opaque_path = Path(temp_dir) / "opaque.png"

            transparent = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
            transparent.putpixel((10, 10), (255, 0, 0, 255))
            transparent.save(transparent_path)

            opaque = Image.new("RGBA", (20, 20), (255, 255, 255, 255))
            opaque.save(opaque_path)

            self.assertTrue(_png_has_meaningful_transparency(transparent_path))
            self.assertFalse(_png_has_meaningful_transparency(opaque_path))

    def test_write_png_asset_normalizes_jpeg_bytes_to_png_file(self) -> None:
        from PIL import Image

        source = Image.new("RGB", (24, 12), (200, 20, 40))
        buffer = BytesIO()
        source.save(buffer, format="JPEG")

        with tempfile.TemporaryDirectory() as temp_dir:
            asset_path = Path(temp_dir) / "asset.png"
            _write_png_asset(asset_path, buffer.getvalue())

            with Image.open(asset_path) as normalized:
                self.assertEqual(normalized.format, "PNG")
                self.assertEqual(normalized.size, (24, 12))

    def test_remove_chroma_key_background_converts_key_color_to_alpha(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as temp_dir:
            asset_path = Path(temp_dir) / "asset.png"
            image = Image.new("RGB", (12, 12), (0, 255, 0))
            for x in range(4, 8):
                for y in range(4, 8):
                    image.putpixel((x, y), (180, 40, 30))
            image.save(asset_path)

            _remove_chroma_key_background(asset_path, key_color="#00FF00")

            with Image.open(asset_path) as result:
                self.assertEqual(result.mode, "RGBA")
                self.assertEqual(result.getpixel((0, 0))[3], 0)
                self.assertEqual(result.getpixel((5, 5))[3], 255)
            self.assertTrue(_png_has_meaningful_transparency(asset_path))

    def test_rewrite_html_updates_img_svg_and_background_targets(self) -> None:
        html = """
<!DOCTYPE html>
<html>
  <body>
    <div class="visual-well" style="background: linear-gradient(red, blue);">
      <img data-stt-node-id="node-0001" src="old.png" alt="Existing alt">
    </div>
    <svg data-stt-node-id="node-0002" class="hero-mark" style="display: block;" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"></circle></svg>
    <div data-stt-node-id="node-0003" class="hero" style="padding: 20px;"></div>
  </body>
</html>
"""
        rewritten = _rewrite_html_with_assets(
            html,
            [
                {
                    "node_id": "node-0001",
                    "target_kind": "img",
                    "asset_rel_path": "generated-assets/page/asset-001.png",
                    "asset_url": "generated-assets/page/asset-001.png?v=123",
                    "alt_text": "Generated hero art",
                    "clear_parent_background": True,
                },
                {
                    "node_id": "node-0002",
                    "target_kind": "svg",
                    "asset_rel_path": "generated-assets/page/asset-002.png",
                    "asset_url": "generated-assets/page/asset-002.png?v=456",
                    "alt_text": "Generated badge",
                    "width": 120,
                    "height": 60,
                },
                {
                    "node_id": "node-0003",
                    "target_kind": "css_background",
                    "asset_rel_path": "generated-assets/page/asset-003.png",
                    "asset_url": "generated-assets/page/asset-003.png?v=789",
                    "background_image": "linear-gradient(rgba(0,0,0,0.2), rgba(0,0,0,0.8)), url('https://example.com/old.png')",
                    "background_size": "cover",
                    "background_position": "center center",
                    "background_repeat": "no-repeat",
                },
            ],
        )

        self.assertIn('src="generated-assets/page/asset-001.png?v=123"', rewritten)
        self.assertIn('src="generated-assets/page/asset-002.png?v=456"', rewritten)
        self.assertIn('alt="Generated badge"', rewritten)
        self.assertIn('style="display: block; width: 100%; height: auto; object-fit: contain; opacity: 1"', rewritten)
        self.assertIn('style="display: block; opacity: 1"', rewritten)
        self.assertIn("background: transparent", rewritten)
        self.assertIn("background-image: none", rewritten)
        self.assertIn("background-color: transparent", rewritten)
        self.assertIn("background-image: linear-gradient(rgba(0,0,0,0.2), rgba(0,0,0,0.8)), url('generated-assets/page/asset-003.png?v=789')", rewritten)
        self.assertNotIn("data-stt-node-id", rewritten)

    def test_rewrite_preserves_compact_logo_slot_sizing(self) -> None:
        html = """
<!DOCTYPE html>
<html>
  <body>
    <div class="logo-band-item" style="height: 28px;">
      <img data-stt-node-id="node-0001" data-stt-asset-brief="Monochrome partner logo wordmark" src="data:image/svg+xml,%3Csvg%3E%3C/svg%3E" alt="Partner logo">
    </div>
  </body>
</html>
"""
        rewritten = _rewrite_html_with_assets(
            html,
            [
                {
                    "node_id": "node-0001",
                    "target_kind": "img",
                    "asset_rel_path": "generated-assets/page/asset-001.png",
                    "asset_url": "generated-assets/page/asset-001.png?v=123",
                    "alt_text": "Partner logo",
                    "asset_brief": "Monochrome partner logo wordmark",
                    "label_hint": "Partner logo",
                    "class_name": "",
                    "width": 100,
                    "height": 28,
                    "clear_parent_background": True,
                },
            ],
        )

        self.assertIn("height: 100%", rewritten)
        self.assertIn("width: auto", rewritten)
        self.assertIn("max-width: 100%", rewritten)
        self.assertNotIn("width: 100%; height: auto", rewritten)

    def test_scan_asset_candidates_handles_svg_classname_and_asset_brief(self) -> None:
        html = f"""
<!DOCTYPE html>
<html>
  <body>
    <section style="background: #112233;">
      <h2>Hero</h2>
      <img
        src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='400'%3E%3C/svg%3E"
        alt="Abstract editorial hero image"
        {ASSET_BRIEF_ATTRIBUTE}="Wide editorial collage with layered documentary textures in a restrained green-black palette"
        style="width: 400px; height: 200px;"
      />
      <svg
        class="badge-mark"
        width="80"
        height="80"
        viewBox="0 0 24 24"
        {ASSET_BRIEF_ATTRIBUTE}="Simple generated badge mark for the hero media area"
      >
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="2" x2="12" y2="22"></line>
        <line x1="2" y1="12" x2="22" y2="12"></line>
      </svg>
    </section>
  </body>
</html>
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            scan_path = Path(temp_dir) / "scan.html"
            scan_path.write_text(_inject_asset_scan_script(_annotate_dom_nodes(html)))
            candidates = _scan_asset_candidates(scan_path)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["asset_brief"], "Wide editorial collage with layered documentary textures in a restrained green-black palette")
        self.assertEqual(candidates[0]["section_heading"], "Hero")
        self.assertIn(candidates[1]["target_kind"], {"svg", "img"})

    def test_scan_asset_candidates_includes_motion_prep_hidden_briefs(self) -> None:
        html = f"""
<!DOCTYPE html>
<html class="motion-prep">
  <head>
    <style>
      html.motion-prep [data-reveal-group] > * {{
        opacity: 0;
        visibility: hidden;
        transform: translateY(18px);
      }}
    </style>
  </head>
  <body>
    <section>
      <h2>Hidden Reveal Gallery</h2>
      <div data-reveal-group>
        <figure style="width: 360px;">
          <img
            src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='720' height='960'%3E%3C/svg%3E"
            alt="Portrait harvest photo"
            {ASSET_BRIEF_ATTRIBUTE}="Portrait documentary harvest photograph with warm paper tones"
            style="width: 360px; height: 480px;"
          />
        </figure>
      </div>
    </section>
  </body>
</html>
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            scan_path = Path(temp_dir) / "scan.html"
            scan_path.write_text(_inject_asset_scan_script(_annotate_dom_nodes(html)))
            candidates = _scan_asset_candidates(scan_path)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["alt_text"], "Portrait harvest photo")
        self.assertEqual(candidates[0]["width"], 360)
        self.assertEqual(candidates[0]["height"], 480)

    def test_static_asset_candidates_finds_explicit_img_briefs(self) -> None:
        html = f"""
<!DOCTYPE html>
<html>
  <head><title>Example</title></head>
  <body>
    <section>
      <h2>Proof Cards</h2>
      <div class="frame">
        <img
          data-stt-node-id="node-0007"
          src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 10'%3E%3C/svg%3E"
          alt="Evidence graphic"
          {ASSET_BRIEF_ATTRIBUTE}="Soft green evidence-card illustration with transparent background"
          style="width: 320px; height: 180px;"
        />
      </div>
    </section>
  </body>
</html>
"""
        candidates = _static_asset_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["node_id"], "node-0007")
        self.assertEqual(candidates[0]["target_kind"], "img")
        self.assertEqual(candidates[0]["width"], 320)
        self.assertEqual(candidates[0]["height"], 180)
        self.assertEqual(candidates[0]["section_heading"], "Proof Cards")

    def test_static_asset_candidates_reads_svg_placeholder_dimensions(self) -> None:
        html = f"""
<!DOCTYPE html>
<html>
  <body>
    <img
      data-stt-node-id="node-0009"
      src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='720' height='960'%3E%3C/svg%3E"
      alt="Portrait ingredient crop"
      {ASSET_BRIEF_ATTRIBUTE}="Portrait editorial ingredient photograph"
    />
  </body>
</html>
"""
        candidates = _static_asset_candidates(html)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["width"], 720)
        self.assertEqual(candidates[0]["height"], 960)

    def test_merge_asset_candidates_prefers_browser_measurements_and_keeps_static_briefs(self) -> None:
        browser_candidates = [
            {
                "node_id": "node-0001",
                "width": 300,
                "height": 200,
                "asset_brief": "Visible measured image",
            }
        ]
        static_candidates = [
            {
                "node_id": "node-0001",
                "width": 1024,
                "height": 1024,
                "asset_brief": "Visible measured image",
            },
            {
                "node_id": "node-0002",
                "width": 720,
                "height": 960,
                "asset_brief": "Hidden explicit placeholder",
            },
        ]

        merged = _merge_asset_candidates(browser_candidates, static_candidates)

        self.assertEqual([candidate["node_id"] for candidate in merged], ["node-0001", "node-0002"])
        self.assertEqual((merged[0]["width"], merged[0]["height"]), (300, 200))
        self.assertEqual((merged[1]["width"], merged[1]["height"]), (720, 960))

    def test_generate_image_with_retries_retries_transient_server_errors(self) -> None:
        class FlakyProvider:
            def __init__(self) -> None:
                self.calls = 0

            def generate_image(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("server had an error while processing your request")
                return b"png", "image/png"

        provider = FlakyProvider()
        image_bytes, mime_type = _generate_image_with_retries(
            provider,
            prompt="test",
            aspect_ratio="1:1",
            image_size="1K",
            output_mime_type="image/png",
            transparent_background=False,
            sleep_seconds=0,
        )

        self.assertEqual(provider.calls, 2)
        self.assertEqual(image_bytes, b"png")
        self.assertEqual(mime_type, "image/png")

    def test_generate_image_with_retries_does_not_retry_non_transient_errors(self) -> None:
        class BadProvider:
            def __init__(self) -> None:
                self.calls = 0

            def generate_image(self, **kwargs):
                self.calls += 1
                raise ValueError("invalid image size")

        provider = BadProvider()
        with self.assertRaises(ValueError):
            _generate_image_with_retries(
                provider,
                prompt="test",
                aspect_ratio="1:1",
                image_size="1K",
                output_mime_type="image/png",
                transparent_background=False,
                sleep_seconds=0,
            )

        self.assertEqual(provider.calls, 1)

    def test_asset_prompt_uses_targeted_context_not_full_generation_input(self) -> None:
        design_system = """
---
name: Acid Lime Editorial Event System
description: A dark, poster-like system built from charcoal fields, acid-lime typography, full-bleed photography, and flat grid-based sectioning.
colors:
  primary: "#1a1c1b"
  accent: "#d9fb06"
---

## Overview
- Bold, flat, poster-like design language with very little conventional UI chrome.
- Dark surfaces and photography carry most of the mood.

### Photography
- Full-bleed documentary/event-style photography is a core system feature.
#### Rules
- Photography usually runs edge-to-edge with no visible caption frame.

## Components
components:
  button-accent:
    cssSizingHint: "inline-flex + width:auto + white-space:nowrap"

## Active Site Generation Skills

### shader-effects
# Shader Effects
Use shader-like canvas effects for procedural backgrounds.
"""
        candidate = {
            "target_kind": "img",
            "width": 756,
            "height": 425,
            "asset_brief": "Wide documentary photograph of a dense festival crowd at night, dramatic stage lighting cutting through haze.",
            "page_title": "PULSE",
            "section_heading": "Opening Night",
            "nearby_text": "Three nights of sound, vision, and collective energy.",
            "label_hint": "Festival crowd image",
            "section_background": "#1A1C1B",
        }

        style_profile = _build_asset_style_profile(design_system)
        asset_plan = _build_asset_plan(candidate, style_profile)
        prompt = _build_asset_prompt(
            candidate,
            design_system,
            transparent_background=False,
            fallback_background=candidate["section_background"],
            style_profile=style_profile,
            asset_plan=asset_plan,
        )

        self.assertEqual(asset_plan["asset_kind"], "photographic")
        self.assertLess(len(prompt), 5000)
        self.assertIn("Asset kind: photographic", prompt)
        self.assertIn("Wide documentary photograph", prompt)
        self.assertIn("Palette cues: primary: #1A1C1B; accent: #D9FB06", prompt)
        self.assertIn("Brand-fit requirements", prompt)
        self.assertNotIn("shader-like canvas effects", prompt)
        self.assertNotIn("cssSizingHint", prompt)
        self.assertNotIn("components:", prompt)

    def test_transparency_gate_is_asset_kind_based(self) -> None:
        style_profile = {"system_name": "example"}
        photo_candidate = {
            "target_kind": "img",
            "width": 640,
            "height": 480,
            "asset_brief": "Documentary photograph of an event crowd at night.",
            "section_background": "#111111",
        }
        illustration_candidate = {
            "target_kind": "img",
            "width": 320,
            "height": 240,
            "asset_brief": "Soft green line-art illustration of layered product cards as a foreground graphic.",
            "section_background": "#FFFFFF",
        }

        photo_plan = _build_asset_plan(photo_candidate, style_profile)
        illustration_plan = _build_asset_plan(illustration_candidate, style_profile)

        self.assertEqual(photo_plan["asset_kind"], "photographic")
        self.assertFalse(_asset_should_have_transparent_background(photo_candidate, photo_plan))
        self.assertEqual(illustration_plan["asset_kind"], "abstract_graphic")
        self.assertTrue(_asset_should_have_transparent_background(illustration_candidate, illustration_plan))
        self.assertEqual(_choose_chroma_key_color(illustration_candidate), "#FF00FF")

    def test_single_color_icon_and_logo_routes_skip_image_generation(self) -> None:
        style_profile = {"system_name": "example"}
        single_color_icon = {
            "target_kind": "img",
            "width": 24,
            "height": 24,
            "asset_brief": "single-color-icon simple stroke search glyph using currentColor",
        }
        logo = {
            "target_kind": "img",
            "width": 120,
            "height": 32,
            "asset_brief": "Customer logo wordmark in the body color for this surface",
        }

        icon_plan = _build_asset_plan(single_color_icon, style_profile)
        logo_plan = _build_asset_plan(logo, style_profile)

        self.assertEqual(icon_plan["asset_kind"], "single_color_icon")
        self.assertEqual(icon_plan["creative_category"], "icons")
        self.assertFalse(_asset_should_have_transparent_background(single_color_icon, icon_plan))
        self.assertIn("Phosphor/currentColor", _asset_generation_skip_reason(single_color_icon, icon_plan))
        self.assertEqual(logo_plan["asset_kind"], "brand_or_badge")
        self.assertIn("not image generation", _asset_generation_skip_reason(logo, logo_plan))

    def test_multi_color_icon_requires_icon_generation_route_and_reference(self) -> None:
        style_profile = {"system_name": "example"}
        candidate = {
            "target_kind": "img",
            "width": 96,
            "height": 96,
            "asset_brief": "multi-color-icon pictorial wellness badge with two palette colors and soft dimensional shading",
            "section_heading": "Benefits",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            reference_path = Path(temp_dir) / "03-benefits.png"
            reference_path.write_bytes(b"not actually decoded in this unit test")
            references = [
                {
                    "path": reference_path,
                    "label": "03-benefits",
                    "text": "benefits icon badge multi color pictorial style",
                    "tokens": {"benefits", "icon", "badge", "multi", "color", "pictorial", "style"},
                }
            ]

            asset_plan = _build_asset_plan(candidate, style_profile)
            chosen_reference = _choose_reference_image_for_asset(candidate, asset_plan, references)

        self.assertEqual(asset_plan["asset_kind"], "multi_color_icon")
        self.assertEqual(asset_plan["creative_category"], "icons")
        self.assertTrue(_asset_should_have_transparent_background(candidate, asset_plan))
        self.assertEqual(chosen_reference, reference_path)
        self.assertEqual(_asset_generation_skip_reason(candidate, asset_plan), "")

    def test_multi_color_icon_asset_generation_passes_reference_to_provider(self) -> None:
        from PIL import Image

        class RecordingProvider:
            def __init__(self) -> None:
                self.calls = []

            def supports_transparent_image_background(self) -> bool:
                return False

            def generate_image(self, **kwargs):
                self.calls.append(kwargs)
                image = Image.new("RGB", (24, 24), (0, 255, 0))
                for x in range(8, 16):
                    for y in range(8, 16):
                        image.putpixel((x, y), (220, 30, 80))
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                return buffer.getvalue(), "image/png"

        html = f"""
<!DOCTYPE html>
<html>
  <body>
    <section>
      <h2>Benefits</h2>
      <img
        data-stt-node-id="node-0001"
        src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96'%3E%3C/svg%3E"
        alt="Pictorial benefit badge"
        {ASSET_BRIEF_ATTRIBUTE}="multi-color-icon pictorial benefit badge with palette colors and soft dimensional shading"
        style="width: 96px; height: 96px;"
      />
    </section>
  </body>
</html>
"""
        provider = RecordingProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            single_dir = Path(temp_dir) / "single"
            crops_dir = single_dir / "crops"
            grounding_dir = single_dir / "section-groundings"
            crops_dir.mkdir(parents=True)
            grounding_dir.mkdir()
            html_path = single_dir / "site-gpt55.html"
            html_path.write_text(html)
            reference_path = crops_dir / "01-benefits.png"
            reference_path.write_bytes(b"reference style crop")
            (grounding_dir / "01-benefits.md").write_text(
                "multi-color icon badge, pictorial icon, soft dimensional graphic style"
            )

            with patch.object(site_assets, "_image_provider_for_model", return_value=provider):
                payload = apply_generated_site_assets(
                    html_path,
                    "imagery:\n  icons:\n    observed: true\n",
                    AppConfig(site_asset_image_model="gpt-image-2"),
                    source_crops_dir=crops_dir,
                )

        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["candidates"][0]["asset_plan"]["asset_kind"], "multi_color_icon")
        self.assertEqual(payload["candidates"][0]["reference_image_path"], "crops/01-benefits.png")
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0]["reference_image_paths"], [reference_path])

    def test_asset_prompt_can_request_chroma_key_background_for_local_removal(self) -> None:
        design_system = """
---
name: Example
description: A crisp editorial system.
---
"""
        candidate = {
            "target_kind": "img",
            "width": 320,
            "height": 240,
            "asset_brief": "Clean line-art illustration of modular blocks.",
            "page_title": "Example",
            "section_background": "#FFFFFF",
        }
        style_profile = _build_asset_style_profile(design_system)
        asset_plan = _build_asset_plan(candidate, style_profile)

        prompt = _build_asset_prompt(
            candidate,
            design_system,
            transparent_background=False,
            fallback_background=candidate["section_background"],
            chroma_key_background="#00FF00",
            style_profile=style_profile,
            asset_plan=asset_plan,
        )

        self.assertIn("chroma-key background", prompt)
        self.assertIn("#00FF00", prompt)
        self.assertIn("Do not use #00FF00 anywhere in the subject", prompt)
        self.assertIn("must occupy the target slot width", prompt)
        self.assertIn("do not create an extra inset", prompt)

    def test_diagrammatic_foreground_beats_incidental_background_wording(self) -> None:
        candidate = {
            "target_kind": "img",
            "width": 320,
            "height": 240,
            "asset_brief": "Transparent foreground diagram of evidence rows, no internal background card.",
        }

        asset_plan = _build_asset_plan(candidate, {"system_name": "example"})

        self.assertEqual(asset_plan["asset_kind"], "diagrammatic")
        self.assertTrue(_asset_should_have_transparent_background(candidate, asset_plan))

    def test_yaml_design_system_brand_cues_feed_image_prompt(self) -> None:
        design_system = """
schema_version: design_system_yaml.v1
type: design_system
metadata:
  name: mint_inverse_editorial_system
  description: Calm mint system with dark-green editorial graphics.
tokens:
  color:
    surface:
      paleMintCard: "#EDFFED"
    accent:
      deepGreen: "#07371A"
layout_patterns:
  image_graphics:
    - name: foreground_vector_marks
      placement: foreground_graphic
      edgeBehavior: seamless, unframed
      realism: flat_vector
      description: Monochrome deep-green symbols sit directly on transparent or tonal surfaces.
rules:
  imagery_graphics:
    - Use flat deep-green vector marks on mint fields without gradients or shadows.
  cards:
    - Pale mint carousel cards use fill contrast, no outer border, no shadow.
do_not_generalize:
  - Universal shadows; most depth is tonal contrast, radius, clipping, or thin rules.
"""
        candidate = {
            "target_kind": "img",
            "width": 320,
            "height": 240,
            "asset_brief": "Transparent foreground diagram of evidence rows.",
        }
        style_profile = _build_asset_style_profile(design_system)
        asset_plan = _build_asset_plan(candidate, style_profile)
        prompt = _build_asset_prompt(
            candidate,
            design_system,
            transparent_background=False,
            chroma_key_background="#00FF00",
            style_profile=style_profile,
            asset_plan=asset_plan,
        )

        self.assertEqual(style_profile["system_name"], "mint_inverse_editorial_system")
        self.assertIn("surface.paleMintCard: #EDFFED", prompt)
        self.assertIn("flat_vector", prompt)
        self.assertIn("without gradients or shadows", prompt)
        self.assertIn("Universal shadows", prompt)
        self.assertIn("Do not introduce off-palette status colors", prompt)

    def test_yaml_patterns_alias_feeds_image_graphic_cues(self) -> None:
        design_system = """
schema_version: design_system_yaml.v1
type: design_system
metadata:
  name: brand_system
patterns:
  image_graphics:
    - name: foreground_marks
      placement: foreground_graphic
      edgeBehavior: unframed
      realism: flat_vector
      description: Dark ink vector marks only.
"""
        style_profile = _build_asset_style_profile(design_system)

        self.assertTrue(any("flat_vector" in cue for cue in style_profile["image_cues"]))


if __name__ == "__main__":
    unittest.main()
