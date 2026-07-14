#!/usr/bin/env python3
"""Regression tests for the pass-2 A/B eval findings (2026-07) — two renderer
slot-binding bugs the regeneration surfaced, both in the SPLIT-family paths that
fix6's stack-hero slot-faithfulness work did not cover:

1. `_split_copy` string-leak: `_text`'s plain-string passthrough matches ANY key,
   so (a) a string-copy heading echoed into the EYEBROW via the header fallback and
   (b) the last-resort `first()` scan leaked whatever string slot came first into
   the BODY (the blog's kicker "The HubSpot Blog" rendered as the hero paragraph).
   Fixes: dict-guard on the header eyebrow fallback, declared-contract fallbacks
   (eyebrow / paragraph), dict-strict `first()`.

2. Form-split `content-block` support: the hero-form-split anatomy DECLARES its
   support slot as `content-block`, but only `list` copy was consumed — a
   header+body support block silently dropped, leaving the capture form with no
   stated reason before it (slop AS-14, caught by the pass-2 battery on the
   regenerated demo hero). Fixes: the block's body strings stamp as the proof
   points, its own heading rides as `_formSplit.intro` and composes as the copy
   column's lead-in paragraph when no separate body paragraph is authored.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))

import compose_from_composition as cfc  # noqa: E402


class SplitCopyBinding(unittest.TestCase):
    """_split_copy binds by role first, declared contract second — and never lets a
    plain-string slot masquerade as a different key."""

    @staticmethod
    def _blog_like_section(**over):
        # the pass-2 blog shape: model-authored domain role words that dodge the
        # role keyword table entirely; every copy value a plain string.
        sec = {
            "id": "blog-hero", "useCase": "hero", "archetype": "split",
            "archetypeRef": "hero-content-featured-lead",
            "slots": [
                {"name": "kicker", "role": "hub-register-label",
                 "contract": "eyebrow", "copy": "The HubSpot Blog"},
                {"name": "heading", "role": "hub-masthead", "contract": "heading",
                 "copy": "Playbooks, benchmarks, and honest takes"},
                {"name": "subheading", "role": "hub-promise", "contract": "paragraph",
                 "copy": "For go-to-market teams planning the next quarter."},
                {"name": "browse", "role": "hub-action", "contract": "link",
                 "copy": "Browse all articles"},
            ],
        }
        sec.update(over)
        return sec

    def test_string_heading_never_echoes_into_eyebrow(self):
        copy = cfc._split_copy(self._blog_like_section())
        self.assertEqual(copy["heading"], "Playbooks, benchmarks, and honest takes")
        self.assertNotEqual(copy["eyebrow"], copy["heading"])

    def test_eyebrow_binds_the_declared_eyebrow_contract(self):
        copy = cfc._split_copy(self._blog_like_section())
        self.assertEqual(copy["eyebrow"], "The HubSpot Blog")

    def test_body_binds_the_declared_paragraph_contract(self):
        copy = cfc._split_copy(self._blog_like_section())
        self.assertEqual(copy["body"],
                         "For go-to-market teams planning the next quarter.")

    def test_string_slot_never_leaks_into_body(self):
        # no paragraph slot at all: body must be EMPTY, not the kicker string
        sec = self._blog_like_section()
        sec["slots"] = [s for s in sec["slots"] if s["name"] != "subheading"]
        copy = cfc._split_copy(sec)
        self.assertEqual(copy["body"], "")

    def test_role_keyword_lookup_still_wins(self):
        # the fix6-era shape (role words the keyword table knows) is unchanged
        sec = self._blog_like_section()
        for s in sec["slots"]:
            if s["name"] == "subheading":
                s["role"] = "hub-lede"
                s["copy"] = "Fresh research and field-tested tactics."
        copy = cfc._split_copy(sec)
        self.assertEqual(copy["body"], "Fresh research and field-tested tactics.")

    def test_dict_header_eyebrow_fallback_still_honored(self):
        # legacy dict-shaped header copy keeps its own eyebrow (byte-identity)
        sec = self._blog_like_section()
        sec["slots"] = [
            {"name": "header", "role": "intro", "contract": "header",
             "copy": {"eyebrow": "Authored eyebrow", "heading": "The heading"}},
        ]
        copy = cfc._split_copy(sec)
        self.assertEqual(copy["eyebrow"], "Authored eyebrow")
        self.assertEqual(copy["heading"], "The heading")


class FormSplitContentBlock(unittest.TestCase):
    """A form-split hero whose support slot is the anatomy's declared content-block
    stamps points + intro — never a silent drop (AS-14)."""

    @staticmethod
    def _demo_like_section(support_slot, **over):
        sec = {
            "id": "demo-hero", "useCase": "hero", "archetype": "split",
            "surfaceIntent": "accent-wash", "archetypeRef": "hero-form-split",
            "knobs": {"formSide": "right", "formFrame": "panel"},
            "slots": [
                {"name": "kicker", "role": "register-label", "contract": "eyebrow",
                 "copy": "Request a demo"},
                {"name": "heading", "role": "the-offer", "contract": "heading",
                 "copy": "See the customer platform work for your team."},
                support_slot,
                {"name": "form", "role": "capture-form", "contract": "form",
                 "copy": {"fields": [{"label": "Work email", "type": "email"}],
                          "submit": "Book my demo"}},
            ],
        }
        sec.update(over)
        return sec

    CONTENT_BLOCK = {
        "name": "support", "role": "what-you-see", "contract": "content-block",
        "copy": {"header": {"heading": "What you'll see in 30 minutes"},
                 "body": ["Breeze AI agents working a real pipeline live.",
                          "Marketing, sales, and service on one connected CRM."]},
    }

    def test_content_block_body_stamps_as_support_paragraphs(self):
        # the block contract's body strings are PARAGRAPHS (the ruled-points
        # device stays the `list` contract's presentation)
        layout = cfc.composition_to_layout(self._demo_like_section(self.CONTENT_BLOCK))
        self.assertEqual(layout["_formSplit"]["support"],
                         ["Breeze AI agents working a real pipeline live.",
                          "Marketing, sales, and service on one connected CRM."])
        self.assertEqual(layout["_formSplit"]["points"], [])

    def test_content_block_heading_stamps_as_intro(self):
        layout = cfc.composition_to_layout(self._demo_like_section(self.CONTENT_BLOCK))
        self.assertEqual(layout["_formSplit"]["intro"],
                         "What you'll see in 30 minutes")

    def test_list_slot_still_wins_over_content_block(self):
        # both authored: the declared list keeps precedence (fix6 byte-identity)
        sec = self._demo_like_section(self.CONTENT_BLOCK)
        sec["slots"].insert(3, {"name": "see-points", "role": "value-list",
                                "contract": "list", "copy": ["Live pipeline"]})
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(layout["_formSplit"]["points"], ["Live pipeline"])
        self.assertNotIn("intro", layout["_formSplit"])
        self.assertNotIn("support", layout["_formSplit"])

    def test_intro_composes_as_lead_in_paragraph_before_the_field(self):
        """AS-14 shape: the stated reason precedes the form field in DOM order."""
        import yaml
        import compose_section as cs
        doc = yaml.safe_load((REPO / "runs/hubspot-v2/brand/brand.yaml").read_text())
        layout = cfc.composition_to_layout(self._demo_like_section(self.CONTENT_BLOCK))
        layout.setdefault("id", "demo-hero")
        surf = (doc.get("tokens") or {}).get("surfaces", {}).get("surface/accent-wash")
        ctx = cs.cr.make_context(doc, "surface/accent-wash", surf)
        html = cs._compose_form_split(
            doc, layout, ctx, [],
            {"eyebrow": "Request a demo", "heading": "See it work.",
             "body": "", "cta": ""})
        self.assertIn("What you&#x27;ll see in 30 minutes", html)
        self.assertLess(html.index("What you&#x27;ll see in 30 minutes"),
                        html.index("cs-input"))
        # the block's body strings render as real paragraphs BEFORE the field
        self.assertIn("Breeze AI agents working a real pipeline live.", html)
        self.assertLess(html.index("Breeze AI agents working a real pipeline live."),
                        html.index("cs-input"))

    def test_authored_body_paragraph_still_wins_over_intro(self):
        import yaml
        import compose_section as cs
        doc = yaml.safe_load((REPO / "runs/hubspot-v2/brand/brand.yaml").read_text())
        layout = cfc.composition_to_layout(self._demo_like_section(self.CONTENT_BLOCK))
        layout.setdefault("id", "demo-hero")
        surf = (doc.get("tokens") or {}).get("surfaces", {}).get("surface/accent-wash")
        ctx = cs.cr.make_context(doc, "surface/accent-wash", surf)
        html = cs._compose_form_split(
            doc, layout, ctx, [],
            {"eyebrow": "", "heading": "See it work.",
             "body": "An authored body paragraph.", "cta": ""})
        self.assertIn("An authored body paragraph.", html)
        self.assertNotIn("What you&#x27;ll see in 30 minutes", html)


class RegeneratedDemoPage(unittest.TestCase):
    """End-to-end: the regenerated demo hero renders its authored content-block
    support (the pass-2 AS-14 regression, fixed at the renderer level)."""

    DEMO = (REPO / "runs" / "hubspot-v2" / "brand" / "compose" / "hero-archetypes"
            / "demo" / "index.html")

    def test_demo_page_renders_the_content_block_support(self):
        html = self.DEMO.read_text()
        self.assertIn("What you&#x27;ll see in 30 minutes", html)
        self.assertIn("Breeze AI agents working a real pipeline live", html)
        self.assertIn("A walkthrough tailored to your stack", html)


if __name__ == "__main__":
    unittest.main()
