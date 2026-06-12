import unittest

from screenshot_to_template.pipeline.grounding_by_section import (
    _apply_full_page_review_to_analysis,
)


class GroundingBySectionReviewTests(unittest.TestCase):
    def test_full_page_review_applies_background_graphic_relationship(self) -> None:
        section_analysis = """## Section 1: Hero

### Section
- **Section type:** opening bookend
- **Background:** dark atmospheric field
"""
        updated = _apply_full_page_review_to_analysis(
            section_analysis,
            {
                "background_graphic_relationship": (
                    "Large glow reads as a seamless section-background layer with reserved visual space."
                )
            },
        )

        self.assertIn(
            "- **Background graphic relationship:** Large glow reads as a seamless section-background layer with reserved visual space.",
            updated,
        )


if __name__ == "__main__":
    unittest.main()
