import json
import tempfile
import unittest
from pathlib import Path

from run_pipeline import (
    combine_design_system_review_sections,
    combine_grounding_references,
    collect_section_grounding_markdown,
    design_system_review_needs_regeneration,
    design_system_review_payload_to_markdown,
    generate_website_html,
    normalize_design_system_section_review,
    parse_provider_list,
    strip_source_provenance_for_site_generation,
    split_design_system_review_sections,
)


class DesignSystemReviewTests(unittest.TestCase):
    def test_split_design_system_review_sections_uses_leaf_sections(self) -> None:
        markdown = """---
colors:
  primary: "#fff"
---
## Overview
Reusable summary.

## Foundations
### Color
Color rules.
#### Rules
- Use paired surfaces.

### Typography
Type rules.

## Components
### Buttons
Button rules.

## Source CSS Color Report
This generated appendix should not be reviewed.
"""
        frontmatter, sections = split_design_system_review_sections(markdown)

        self.assertIn("colors:", frontmatter)
        self.assertEqual([section["heading"] for section in sections], ["Overview", "Color", "Typography", "Buttons"])
        self.assertEqual(sections[1]["parent_heading"], "Foundations")
        self.assertIn("#### Rules", sections[1]["content"])
        self.assertNotIn("Source CSS", "\n".join(section["content"] for section in sections))

    def test_normalize_and_combine_design_system_section_reviews(self) -> None:
        color_section = {"id": "foundations-color", "heading": "Color", "parent_heading": "Foundations", "level": 3}
        type_section = {"id": "foundations-typography", "heading": "Typography", "parent_heading": "Foundations", "level": 3}

        color = normalize_design_system_section_review(
            color_section,
            {
                "score": "12",
                "confidence": "8",
                "summary": " Strong color mapping. ",
                "accurate_patterns": ["Surface contrast"],
                "missing_or_weak_patterns": "not a list",
                "actionable_learnings": ["Tighten inverse surface rules."],
                "verdict": "Good",
            },
            "raw color",
        )
        typography = normalize_design_system_section_review(
            type_section,
            {
                "score": 5,
                "confidence": -2,
                "summary": "Type is too generic.",
                "actionable_learnings": ["Name concrete type scale relationships."],
            },
            "raw type",
        )

        self.assertEqual(color["score"], 10)
        self.assertEqual(color["confidence"], 0.8)
        self.assertEqual(color["missing_or_weak_patterns"], [])
        self.assertEqual(typography["confidence"], 0)

        combined = combine_design_system_review_sections([color, typography])
        self.assertEqual(combined["weighted_score"], 75)
        self.assertEqual(list(combined["scores"].keys()), ["foundations-color", "foundations-typography"])
        self.assertIn("Name concrete type scale relationships.", combined["actionable_learnings"])

        markdown = design_system_review_payload_to_markdown(combined)
        self.assertIn("# Design System Review", markdown)
        self.assertIn("Weighted score: **75.00 / 100**", markdown)
        self.assertIn("Foundations / Color", markdown)

    def test_design_system_review_regeneration_predicate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "design-system-review.json"

            self.assertTrue(design_system_review_needs_regeneration(path))

            path.write_text("{bad json")
            self.assertTrue(design_system_review_needs_regeneration(path))

            path.write_text(json.dumps({"weighted_score": 80, "raw_response": "ok"}))
            self.assertTrue(design_system_review_needs_regeneration(path))

            path.write_text(json.dumps({"weighted_score": 0, "section_reviews": [], "raw_response": "failed", "verdict": "Review failed: boom"}))
            self.assertTrue(design_system_review_needs_regeneration(path))

            path.write_text(json.dumps({"weighted_score": 80, "section_reviews": [], "raw_response": "ok"}))
            self.assertFalse(design_system_review_needs_regeneration(path))

    def test_collects_section_grounding_reference_for_downstream_sync(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            section_dir = root / "section-groundings"
            section_dir.mkdir()
            (section_dir / "02-hero.md").write_text("Hero primary button fill #E8EEF6\n")
            (section_dir / "01-nav.md").write_text("Nav heading case: uppercase\n")

            collected = collect_section_grounding_markdown(root)
            combined = combine_grounding_references("Merged grounding", collected)

            self.assertLess(collected.index("01-nav"), collected.index("02-hero"))
            self.assertIn("Hero primary button fill #E8EEF6", collected)
            self.assertIn("Detailed Section Grounding Reference", combined)
            self.assertIn("Nav heading case: uppercase", combined)

    def test_provider_list_filters_disabled_gemini(self) -> None:
        self.assertEqual(parse_provider_list("claude\ngemini\ngpt54\n"), ["claude", "gpt55"])
        self.assertEqual(parse_provider_list("gemini\n"), ["gpt55"])

    def test_gemini_site_generation_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "Gemini site generation is disabled"):
            generate_website_html("tokens: {}", "gemini")

    def test_site_generation_strips_subject_metadata_without_dropping_visual_rules(self) -> None:
        markdown = """
schema_version: design_system_yaml.v1
patterns:
  image_graphics:
    - name: media_asset_rows
      rule: "Logo/proof assets are media and should be placed in sparse rows."
imagery:
  interfaces:
    creativeDirection: "Stylized embedded UI/mockup media with simple waveforms, rounded panels, and blue-framed compositions."
    avoid:
      - "Promoting waveform controls into live components."
do_not_generalize:
  - "Exact brand mark, wordmark, partner/customer logo names, and logo letterforms."
  - "Literal business/product/industry copy and section ordering."
  - "The 72px asymmetric card corner as a universal radius."
embedded_showcase_only:
  - name: audio_waveform_demo_ui
    reason: "Contained inside a demo media well; internal play, waveform, pills, and timers are visual media."
  - name: product_interface_preview_cards
    reason: "Floating UI cards are part of an embedded product showcase."
rules:
  typography:
    - "Use source font for all live page text."
"""

        stripped = strip_source_provenance_for_site_generation(markdown)

        self.assertNotIn("embedded_showcase_only", stripped)
        self.assertNotIn("audio_waveform_demo_ui", stripped)
        self.assertNotIn("Literal business/product/industry copy", stripped)
        self.assertNotIn("Exact brand mark", stripped)
        self.assertNotIn("waveform", stripped.lower())
        self.assertIn("abstract data visualizations", stripped)
        self.assertIn("The 72px asymmetric card corner as a universal radius.", stripped)
        self.assertIn("Logo/proof assets are media", stripped)


if __name__ == "__main__":
    unittest.main()
