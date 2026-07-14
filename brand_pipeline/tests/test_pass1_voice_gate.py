#!/usr/bin/env python3
"""pass1 (2026-07) — voice gate tests (brand_pipeline/voice_audit.py): copy
extraction (chrome exclusion, role routing), every metric check FAILS on a
synthetic bad fixture and PASSES on clean copy, the brand-term casing
allowance, and both brands' committed voice-facts.yaml shape.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_pass1_voice_gate
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
_ROOT = _BRAND_PIPELINE.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import voice_audit as va  # noqa: E402


FACTS = {
    "schema": "voice-facts.v1",
    "sentences": {"gate": {"meanWordsMax": 14, "p90WordsMax": 22}},
    "punctuation": {"exclamations": {"gate": {"max": 0}}},
    "bannedHype": {"lexicon": ["revolutionary", "game-changing", "supercharge"]},
    "casing": {"headings": {"rule": "sentence",
                            "brandTerms": ["Marketing Hub", "HubSpot", "AI"]}},
}


def _copy(headings=(), bodies=(), eyebrows=(), ctas=()):
    return {"headings": list(headings), "bodies": list(bodies),
            "eyebrows": list(eyebrows), "ctas": list(ctas)}


class ExtractCopyTest(unittest.TestCase):
    HTML = """
    <html><body>
      <nav class="cs-nav"><button class="c-button">Nav CTA ignored</button></nav>
      <main>
        <section id="sec-0">
          <p class="c-eyebrow">MARKETING</p>
          <h1 class="c-heading c-heading--display">Grow better every day</h1>
          <p>Copy that sells without shouting.</p>
          <a class="c-button c-button--primary">Get a demo</a>
          <a class="c-button c-arrow-link">Learn more</a>
        </section>
      </main>
      <footer class="c-foot"><p>Legal chrome line ignored.</p></footer>
    </body></html>"""

    def test_roles_routed_and_chrome_excluded(self):
        copy = va.extract_copy(self.HTML)
        self.assertEqual(copy["headings"], ["Grow better every day"])
        self.assertEqual(copy["bodies"], ["Copy that sells without shouting."])
        self.assertEqual(copy["eyebrows"], ["MARKETING"])
        self.assertEqual(copy["ctas"], ["Get a demo"])  # arrow-link excluded

    def test_svg_and_script_text_never_leaks(self):
        html = ('<section id="sec-0"><h2>Real heading'
                '<svg><title>glyph title</title></svg></h2>'
                '<script>var x = "not copy";</script></section>')
        copy = va.extract_copy(html)
        self.assertEqual(copy["headings"], ["Real heading"])


class SentenceLengthTest(unittest.TestCase):
    def test_run_on_copy_fails(self):
        long = ("This sentence keeps going and going with clause after clause "
                "after clause because nobody edited it down to the punchy "
                "length the brand actually ships on its own pages today.")
        rows = va.audit_copy(_copy(bodies=[long, long, long]), FACTS)
        cell = next(r for r in rows if r["check"] == "sentence-length")
        self.assertFalse(cell["ok"])

    def test_measured_length_band_passes(self):
        rows = va.audit_copy(_copy(
            bodies=["Grow revenue without growing headcount.",
                    "Meet the platform your teams already love."],
            headings=["Marketing that runs itself"]), FACTS)
        cell = next(r for r in rows if r["check"] == "sentence-length")
        self.assertTrue(cell["ok"])


class ExclamationTest(unittest.TestCase):
    def test_exclamation_fails_the_measured_ban(self):
        rows = va.audit_copy(_copy(headings=["Grow better now!"]), FACTS)
        cell = next(r for r in rows if r["check"] == "exclamations")
        self.assertFalse(cell["ok"])

    def test_no_exclamations_passes(self):
        rows = va.audit_copy(_copy(headings=["Grow better now"]), FACTS)
        cell = next(r for r in rows if r["check"] == "exclamations")
        self.assertTrue(cell["ok"])


class BannedHypeTest(unittest.TestCase):
    def test_hype_lexicon_hit_fails(self):
        rows = va.audit_copy(
            _copy(bodies=["A revolutionary platform to supercharge growth."]),
            FACTS)
        cell = next(r for r in rows if r["check"] == "banned-hype")
        self.assertFalse(cell["ok"])
        self.assertIn("revolutionary", cell["detail"])

    def test_substring_never_false_positives(self):
        # 'supercharge' banned; 'supercharged' as substring of another word is
        # still a word-boundary miss for e.g. 'superchargers' vs the lexicon
        rows = va.audit_copy(_copy(bodies=["Visit our superchargers page."]),
                             FACTS)
        cell = next(r for r in rows if r["check"] == "banned-hype")
        self.assertTrue(cell["ok"])


class HeadingCasingTest(unittest.TestCase):
    def test_title_cased_heading_fails_sentence_rule(self):
        rows = va.audit_copy(
            _copy(headings=["Grow Better Every Single Day"]), FACTS)
        cell = next(r for r in rows if r["check"] == "heading-casing")
        self.assertFalse(cell["ok"])

    def test_brand_terms_and_proper_nouns_allowed(self):
        rows = va.audit_copy(
            _copy(headings=["Marketing Hub grows with HubSpot AI",
                            "One stray Capital is not a title case"]), FACTS)
        cell = next(r for r in rows if r["check"] == "heading-casing")
        self.assertTrue(cell["ok"], cell["detail"])

    def test_multiword_brand_term_strips_as_phrase(self):
        words = va._title_words("Meet the new Marketing Hub today",
                                {"Marketing Hub"})
        self.assertEqual(words, [])


class CommittedFactsTest(unittest.TestCase):
    """Both brands' voice-facts.yaml: schema, derived stats present, gates
    self-consistent (gate budgets at/above the measured stats they envelope)."""

    def _facts(self, brand):
        p = _ROOT / "runs" / brand / "brand" / "voice-facts.yaml"
        self.assertTrue(p.exists(), f"{p} missing")
        return yaml.safe_load(p.read_text())

    def test_both_brands_facts_shape(self):
        for brand in ("hubspot-v2", "remote"):
            f = self._facts(brand)
            self.assertEqual(f["schema"], "voice-facts.v1", brand)
            sen = f["sentences"]
            self.assertLessEqual(sen["meanWords"],
                                 sen["gate"]["meanWordsMax"], brand)
            self.assertLessEqual(sen["p90Words"],
                                 sen["gate"]["p90WordsMax"], brand)
            self.assertIn("rule", f["casing"]["headings"])
            self.assertTrue(f["bannedHype"]["lexicon"], brand)
            self.assertTrue(f.get("provenance"), f"{brand}: no provenance")

    def test_fact_gated_skip_without_facts(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            report = va.run_audit([], Path(td), None)
            self.assertIn("fact-gated skip", report["note"])


if __name__ == "__main__":
    unittest.main()
