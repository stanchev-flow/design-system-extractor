#!/usr/bin/env python3
"""Unit tests for the token-provenance scanner (brand_pipeline/token_provenance.py —
SPEC §D, DECISIONS.md #3). Uses the synthetic fixture brand from test_tokens_css plus
the live WoodWave index as the "foreign brand" so DNA-leak callouts are exercised
without touching runs/hubspot/**.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_token_provenance
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import tokens_css as tc            # noqa: E402
import token_provenance as tp      # noqa: E402
from tests.test_tokens_css import FIXTURE  # noqa: E402

_WOODWAVE = _BRAND_PIPELINE.parent / "runs" / "woodwave" / "brand" / "brand.yaml"


def _page(body_css: str, tokens_css: str = ":root { --color-x: #10141A; }") -> str:
    return (f'<style id="tokens">\n{tokens_css}\n</style>\n'
            f"<style>\n{body_css}\n</style>")


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = tc.build_page_tokens(FIXTURE).index
        cls.ww_index = tc.build_page_tokens(
            yaml.safe_load(_WOODWAVE.read_text())).index

    def scan(self, css, **kw):
        kw.setdefault("brand", "Ravine")
        return tp.check_token_provenance(_page(css), self.index, **kw)


class CleanPassTests(_Base):
    def test_var_only_page_passes(self):
        res = self.scan("""
.c-button { background: var(--c-button-bg); color: var(--c-button-ink);
            font-weight: var(--c-button-weight); transition: filter var(--c-motion-fast) var(--c-motion-ease); }
.cs-section { padding-block: var(--c-section-pad-y); }
""")
        self.assertTrue(res["passed"])
        self.assertEqual(res["errors"], [])
        self.assertEqual(res["warnings"], [])
        self.assertNotIn("|", res["detail"])

    def test_own_brand_literal_is_traceable(self):
        # a literal equal to the brand's own measured value traces to brand.yaml
        res = self.scan(".panel { background: #EEF2F7; } "
                        ".h2 { font-size: 2.75rem; font-weight: 400; text-transform: uppercase; }")
        self.assertTrue(res["passed"], res["errors"])

    def test_tokens_block_is_skipped(self):
        html = ('<style id="tokens">:root { --color-alien: #123456; '
                '--size-alien: 9.99rem; }</style>')
        res = tp.check_token_provenance(html, self.index, brand="Ravine")
        self.assertTrue(res["passed"])


class ViolationTests(_Base):
    def test_foreign_hex_is_error_with_suggestion(self):
        res = self.scan(".hero { color: #ABCDEF; }")
        self.assertFalse(res["passed"])
        self.assertEqual(len(res["errors"]), 1)
        self.assertIn("raw `#ABCDEF`", res["errors"][0])
        self.assertIn("nearest color token", res["errors"][0])

    def test_woodwave_dna_leak_gets_foreign_callout(self):
        # WoodWave gold on a Ravine page → the smoking-gun callout
        res = self.scan(".link:hover { color: #edd580; }",
                        foreign_indexes={"WoodWave": self.ww_index})
        self.assertFalse(res["passed"])
        self.assertIn("foreign-brand value: matches WoodWave", res["errors"][0])

    def test_duration_and_easing_are_warnings_not_errors(self):
        # DECISIONS.md #3: motion provenance violations never gate
        res = self.scan(".x { transition: transform 999ms cubic-bezier(.9,.1,.9,.1); }")
        self.assertTrue(res["passed"])
        self.assertEqual(res["errors"], [])
        self.assertEqual(len(res["warnings"]), 2)
        self.assertIn("999ms", res["warnings"][0])

    def test_untraceable_weight_and_case(self):
        res = self.scan(".t { font-weight: 900; } .u { text-transform: capitalize; }")
        # 900 not a Ravine weight → error; capitalize IS (control-text title) → pass
        self.assertEqual(len(res["errors"]), 1)
        self.assertIn("`900`", res["errors"][0])

    def test_spacing_gated_on_section_selectors_only(self):
        res = self.scan(".c-card { padding: 1.1875rem; }")
        self.assertTrue(res["passed"])  # micro-gap inside a component: CR-8, not gated
        res2 = self.scan(".cs-section { padding: 1.1875rem 0; }")
        self.assertFalse(res2["passed"])
        self.assertIn("1.1875rem", res2["errors"][0])

    def test_var_fallback_literal_is_flagged(self):
        # removing literal fallbacks inside var() is part of the batch contract
        res = self.scan(".x { background: var(--c-panel, #fdf9f0); }")
        self.assertFalse(res["passed"])
        self.assertIn("#fdf9f0", res["errors"][0])

    def test_aspect_literal(self):
        res = self.scan(".m { aspect-ratio: 16/9; }")
        self.assertFalse(res["passed"])  # Ravine palette is 3/2 + 4/5
        res2 = self.scan(".m { aspect-ratio: 3/2; }")
        self.assertTrue(res2["passed"])


class AllowlistTests(_Base):
    def test_structural_comment_before_declaration(self):
        res = self.scan("""
.cs-ghost { z-index: 0;
  /* provenance: structural ghost-guard — px hairline registration, brand-independent */
  font-size: 22rem; }
""")
        self.assertTrue(res["passed"], res["errors"])
        self.assertEqual(res["allowlisted"], 1)

    def test_structural_comment_at_rule_head_covers_rule(self):
        res = self.scan("""
/* provenance: structural focus-ring — a11y outline, brand-independent */
.x:focus-visible { outline-color: #888888; font-size: 0.7rem; }
""")
        self.assertTrue(res["passed"], res["errors"])
        self.assertEqual(res["allowlisted"], 2)

    def test_structural_comment_does_not_leak_to_next_rule(self):
        res = self.scan("""
/* provenance: structural spacer — registration */
.a { font-size: 0.7rem; }
.b { font-size: 0.7rem; }
""")
        self.assertFalse(res["passed"])
        self.assertEqual(len(res["errors"]), 1)
        self.assertIn(".b", res["errors"][0])

    def test_preview_chrome_block_suppressed(self):
        html = ('<style id="tokens">:root{}</style>'
                "<style>/* provenance: preview-chrome */ "
                ".bar { background: #333333; font-size: 3rem; }</style>")
        res = tp.check_token_provenance(html, self.index, brand="Ravine")
        self.assertTrue(res["passed"])
        self.assertGreaterEqual(res["allowlisted"], 1)


class MediaAndDetailTests(_Base):
    def test_media_query_rules_are_scanned(self):
        res = self.scan("@media (max-width: 767px) { .hero { color: #ABCDEF; } }")
        self.assertFalse(res["passed"])
        self.assertIn("#ABCDEF", res["errors"][0])

    def test_detail_is_pipe_free_and_capped(self):
        css = "\n".join(f".v{i} {{ color: #0{i}0{i}0{i}; }}" for i in range(1, 10))
        res = self.scan(css)
        self.assertFalse(res["passed"])
        self.assertNotIn("|", res["detail"])
        self.assertIn("more)", res["detail"])  # capped with (+N more)


if __name__ == "__main__":
    unittest.main()
