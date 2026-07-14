#!/usr/bin/env python3
"""Eval-matrix BASELINE round findings (2026-07-14) — renderer-level fixes,
fixture-proven both directions (fails the synthetic bad, passes the real lanes).

FINDING (conversion hardFloor, both webinar-event cells): a conversion-use
section whose registration form the model authored as a `form-field` contract
slot (copy = the field LIST) on a `split` archetype rendered as a button-only
band — the stamp reader only knew the dict shape (`form` slot, copy.fields),
and only conversion STACKS route form anatomy. Fix, two adapter rules in
compose_from_composition:

  1. `_form_fields_stamp` resolves the LIST shape: a `form-field` contract
     slot's field list (help→helper, "A / B / C" options-string → list, an
     option run coerces text→select), the sibling `checkbox` slot as the
     opt-in row, the consent-named paragraph slot as the consent line.
  2. conversion-use sections with a VALIDATED stamp normalize to the
     conversion stack (`is_conversion`), whatever archetype they declared.

Both are fact-gated on the stamp: form-less conversion splits keep their
declared shape; the dict shape stamps exactly as before (pinned below); repo
scan found zero existing compositions in the newly-routed class.

Run: ./venv/bin/python -m pytest brand_pipeline/tests/test_baseline_findings.py -q
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import compose_from_composition as cfc  # noqa: E402

REPO = _BRAND_PIPELINE.parent
HUBSPOT = REPO / "runs" / "hubspot-v2" / "brand" / "brand.yaml"


def register_section(**overrides) -> dict:
    """The webinar-event `register` shape (verbatim structure from the baseline
    round's composition, copy trimmed) — the model's natural registration
    emission the adapter used to drop."""
    sec = {
        "id": "register",
        "useCase": "cta",
        "archetype": "split",
        "surfaceIntent": "primary",
        "slots": [
            {"name": "intro", "role": "form-intro", "contract": "header",
             "copy": {"heading": "Save your seat",
                      "text": "One registration gets you the live session and the recording."}},
            {"name": "fields", "role": "registration-fields", "contract": "form-field",
             "copy": [
                 {"label": "Full name"},
                 {"label": "Work email", "help": "Your invite and the recording land here."},
                 {"label": "Company"},
                 {"label": "Company size", "options": "1–25 / 26–200 / 201–2,000 / 2,000+"},
                 {"label": "Role", "options": "Marketing / Sales / Service / Operations / Other"},
             ]},
            {"name": "optin", "role": "opt-in", "contract": "checkbox",
             "copy": "Send me occasional research from HubSpot."},
            {"name": "submit", "role": "primary-action", "contract": "button",
             "copy": "Save my seat"},
            {"name": "consent", "role": "consent-note", "contract": "paragraph",
             "copy": "We'll email you about this session and the recording. Unsubscribe anytime."},
        ],
        "treatments": [],
    }
    sec.update(overrides)
    return sec


class ListShapeStamp(unittest.TestCase):
    """`_form_fields_stamp` — the LIST shape (form-field contract slot)."""

    def setUp(self):
        self.stamp = cfc._form_fields_stamp(register_section())

    def test_stamp_resolves(self):
        self.assertIsNotNone(self.stamp)

    def test_all_authored_fields_plus_optin_checkbox(self):
        labels = [f["label"] for f in self.stamp["fields"]]
        self.assertEqual(labels, ["Full name", "Work email", "Company",
                                  "Company size", "Role",
                                  "Send me occasional research from HubSpot."])
        self.assertEqual(self.stamp["fields"][-1]["kind"], "checkbox")

    def test_options_string_splits_on_slash_separators(self):
        size = next(f for f in self.stamp["fields"] if f["label"] == "Company size")
        # values with embedded commas survive (only ' / ' separates)
        self.assertEqual(size["options"], ["1–25", "26–200", "201–2,000", "2,000+"])
        self.assertEqual(size["kind"], "select",
                         "an authored option run is a choice control, not a text input")

    def test_help_key_normalizes_to_helper(self):
        email = next(f for f in self.stamp["fields"] if f["label"] == "Work email")
        self.assertEqual(email["helper"], "Your invite and the recording land here.")

    def test_consent_slot_rides_the_stamp(self):
        self.assertIn("Unsubscribe anytime", self.stamp["consent"])

    def test_no_fields_slot_no_stamp(self):
        sec = register_section()
        sec["slots"] = [s for s in sec["slots"] if s["contract"] != "form-field"]
        self.assertIsNone(cfc._form_fields_stamp(sec))


class DictShapeUnchanged(unittest.TestCase):
    """The dict shape (form slot, copy.fields) stamps exactly as before —
    the event-genlaunch/leadgen composition shape."""

    SEC = {
        "id": "signup", "useCase": "conversion", "archetype": "stack",
        "slots": [{
            "name": "form", "role": "capture", "contract": "form",
            "copy": {
                "fields": [
                    {"label": "Work email", "kind": "email", "required": True},
                    {"label": "Company size", "kind": "select",
                     "options": ["1–25", "26–200"]},
                ],
                "submit": "Get the report",
                "consent": "We'll email the report.",
                "success": "Check your inbox.",
            },
        }],
    }

    def test_dict_stamp_pinned(self):
        stamp = cfc._form_fields_stamp(self.SEC)
        self.assertEqual(stamp, {
            "fields": [
                {"kind": "email", "label": "Work email", "required": True},
                {"kind": "select", "label": "Company size",
                 "options": ["1–25", "26–200"]},
            ],
            "consent": "We'll email the report.",
            "success": "Check your inbox.",
            "submit": "Get the report",
        })


class ConversionRouting(unittest.TestCase):
    """A conversion-use section with a validated stamp routes to the
    conversion stack; without one it keeps its declared shape."""

    def test_registration_split_normalizes_to_conversion_stack(self):
        layout = cfc.composition_to_layout(register_section())
        self.assertEqual(layout["archetype"], "stack")
        self.assertIsNotNone(layout.get("_formFields"))
        # provenance keeps the DECLARED archetype
        self.assertEqual(layout["_composition"]["archetype"], "split")

    def test_formless_cta_split_keeps_split(self):
        sec = register_section()
        sec["slots"] = [s for s in sec["slots"]
                        if s["contract"] not in ("form-field", "checkbox")]
        layout = cfc.composition_to_layout(sec)
        self.assertEqual(layout["archetype"], "split")
        self.assertIsNone(layout.get("_formFields"))

    def test_hero_never_rides_this_route(self):
        sec = register_section(useCase="hero")
        layout = cfc.composition_to_layout(sec)
        self.assertNotEqual(layout["archetype"], "stack")


class RenderedProof(unittest.TestCase):
    """End-to-end through the real brand: the registration section renders a
    real <form> with every authored control (was: zero <form> elements)."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        comp = {"schemaVersion": "composition.v1", "brief": "registration fix proof",
                "sections": [register_section()]}
        cls._tmp = tempfile.TemporaryDirectory()
        cfc.render_composition(comp, HUBSPOT, Path(cls._tmp.name),
                               style_id="corporate-saas-clean")
        cls.html = (Path(cls._tmp.name) / "index.html").read_text()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_real_form_with_all_controls(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self.html, "html.parser")
        forms = [f for f in soup.select("form")
                 if f.find_parent("nav") is None]
        self.assertEqual(len(forms), 1)
        form = forms[0]
        labels = [l.get_text(strip=True) for l in form.select(".cs-field-label")]
        self.assertEqual(labels, ["Full name", "Work email", "Company",
                                  "Company size", "Role"])
        self.assertEqual(len(form.select("select")), 2)
        self.assertEqual(len(form.select('input[type="checkbox"]')), 1)
        self.assertTrue(form.select_one('button[type="submit"]'))

    def test_submit_label_is_the_button_slots(self):
        self.assertIn("Save my seat", self.html)


if __name__ == "__main__":
    unittest.main()
