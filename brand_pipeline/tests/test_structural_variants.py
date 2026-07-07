#!/usr/bin/env python3
"""Unit tests for the SPEC §C.3 structural-variant flags + the per-surface layer-2
alias emission (token-layer batch).

Covers: input-shape / cta-shape resolution order (brand structure LAW > token
presence > default); the boxed-field CSS variant existing with token-driven
magnitudes; component_vars emitting var()-reference aliases (no literal hex/ms in
layer 2 when a surface_role is given); the per-surface link-hover re-scoping (AS-20:
measured hover on dark surfaces only, ink on light).

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_structural_variants
"""
from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import component_render as cr  # noqa: E402
from tests.test_tokens_css import FIXTURE  # noqa: E402


def _woodwavish():
    """A WoodWave-shaped structure-law doc: underline inputs + typographic CTA."""
    doc = copy.deepcopy(FIXTURE)
    doc["neverDo"] = [{"id": "no-boxed-inputs"}, {"id": "no-radius"}]
    doc["primitives"] = {"button": {"use": "never"}}
    doc.pop("buttons", None)
    return doc


class InputShape(unittest.TestCase):
    def test_never_do_forces_underline(self):
        self.assertEqual(cr.input_shape(_woodwavish()), "underline")

    def test_input_radius_token_selects_boxed(self):
        doc = copy.deepcopy(FIXTURE)
        doc["tokens"]["radius"] = {"input": {"value": "0.375rem"}}
        self.assertEqual(cr.input_shape(doc), "boxed")

    def test_default_is_underline(self):
        self.assertEqual(cr.input_shape(copy.deepcopy(FIXTURE)), "underline")

    def test_render_input_stamps_boxed_class(self):
        doc = copy.deepcopy(FIXTURE)
        doc["tokens"]["radius"] = {"input": {"value": "0.375rem"}}
        ctx = cr.ComponentContext(surface_role="surface/primary", is_dark=False)
        self.assertIn("c-field--boxed", cr.render_input(doc, ctx, {"placeholder": "x"}))
        self.assertNotIn("c-field--boxed",
                         cr.render_input(_woodwavish(), ctx, {"placeholder": "x"}))

    def test_boxed_variant_css_is_token_driven(self):
        # the boxed rule lives in the CONDITIONAL variant CSS (emitted only for boxed
        # brands / the gallery) — never in the always-on COMPONENT_CSS (dormant grammar
        # is the AS-24 leak the neverDo checks police).
        self.assertNotIn(".c-field--boxed", cr.COMPONENT_CSS)
        doc = copy.deepcopy(FIXTURE)
        doc["tokens"]["radius"] = {"input": {"value": "0.375rem"}}
        css = cr.structural_variant_css(doc)
        rule = re.search(r"\.c-field--boxed \{[^}]+\}", css).group(0)
        for var in ("--c-input-border", "--c-input-radius", "--c-input-bg"):
            self.assertIn(var, rule)
        self.assertNotRegex(rule, r"#[0-9a-fA-F]{3}")  # no literal hexes in the variant

    def test_variant_css_empty_for_underline_typographic_brand(self):
        # button/boxed variants stay ABSENT for a WoodWave-shaped brand. The variant
        # layer is no longer empty though: the footer GRAMMAR (fix-batch 2026-07, B6)
        # always emits exactly ONE grammar — the display-links default here — because
        # the sitemap rules moved out of the always-on COMPONENT_CSS (same dormant-
        # grammar discipline as button/boxed-field).
        css = cr.structural_variant_css(_woodwavish())
        self.assertNotIn(".c-button", css)
        self.assertNotIn(".c-field--boxed", css)
        self.assertIn(".c-foot-sitemap-link", css)     # display-links grammar selected
        self.assertNotIn(".c-foot-cols", css)          # columns grammar NOT carried

    def test_variant_css_gallery_mode_carries_all(self):
        css = cr.structural_variant_css(_woodwavish(), include_all=True)
        self.assertIn(".c-button", css)
        self.assertIn(".c-field--boxed", css)
        self.assertIn(".c-foot-sitemap-link", css)
        self.assertIn(".c-foot-cols", css)

    def test_button_variant_emitted_for_filled_brand(self):
        css = cr.structural_variant_css(copy.deepcopy(FIXTURE))
        self.assertIn(".c-button", css)  # FIXTURE carries buttons.primary → filled
        self.assertNotIn(".c-field--boxed", css)  # FIXTURE inputs stay underline


class CtaShape(unittest.TestCase):
    def test_use_never_keeps_typographic(self):
        self.assertEqual(cr.cta_shape(_woodwavish()), "typographic")

    def test_never_typographic_primary_forces_filled(self):
        doc = copy.deepcopy(FIXTURE)
        doc["neverDo"] = [{"id": "never-typographic-primary"}]
        self.assertEqual(cr.cta_shape(doc), "filled")

    def test_measured_button_family_implies_filled(self):
        # FIXTURE carries buttons.primary (the measured family) → filled
        self.assertEqual(cr.cta_shape(copy.deepcopy(FIXTURE)), "filled")

    def test_render_hint_wins_over_default(self):
        doc = copy.deepcopy(FIXTURE)
        doc.pop("buttons", None)
        doc["tokens"]["buttons"] = {"renderHint": {"useFilledButton": True}}
        self.assertEqual(cr.cta_shape(doc), "filled")


class PerSurfaceAliases(unittest.TestCase):
    def _vars(self, role):
        doc = copy.deepcopy(FIXTURE)
        surf = doc["tokens"]["surfaces"][role]
        return cr.component_vars(doc, surf, selector=".t", surface_role=role)

    def test_paper_is_surface_var_reference(self):
        self.assertIn("--c-paper: var(--surface-surface-primary)",
                      self._vars("surface/primary"))
        self.assertIn("--c-paper: var(--surface-surface-inverse)",
                      self._vars("surface/inverse"))

    def test_no_raw_hex_in_alias_block(self):
        # every color alias must be a var() reference into layer 1, never a resolved hex
        for role in ("surface/primary", "surface/inverse"):
            self.assertNotRegex(self._vars(role), r":\s*#[0-9a-fA-F]{3,8}\b")

    def test_no_raw_duration_in_motion_vars(self):
        css = cr.motion_vars_css(copy.deepcopy(FIXTURE))
        self.assertNotRegex(css, r"\b\d+ms\b")
        self.assertIn("var(--motion-fast)", css)

    def test_link_hover_rescopes_per_surface(self):
        doc = copy.deepcopy(FIXTURE)
        # measured hover exists (footer.measured.linkHoverColor) — dark surface gets the
        # chrome hover reference; the light surface must stay on ink (AS-10/AS-20).
        dark = self._vars("surface/inverse")
        light = self._vars("surface/primary")
        self.assertIn("--c-link-hover: var(--chrome-link-hover)", dark)
        self.assertNotIn("--chrome-link-hover", light)

    def test_button_aliases_emitted_only_with_family(self):
        with_btn = self._vars("surface/primary")
        self.assertIn("--c-button-bg: var(--button-bg)", with_btn)
        doc = _woodwavish()
        surf = doc["tokens"]["surfaces"]["surface/primary"]
        without = cr.component_vars(doc, surf, selector=".t",
                                    surface_role="surface/primary")
        self.assertNotIn("--c-button-bg", without)


class EyebrowRegister(unittest.TestCase):
    """layout.eyebrowRegister → section-scoped --c-eyebrow-color (theme-scoped
    eyebrow families, sysfix 2026-07). Declared = layer-1 var reference; undeclared
    = no emission (the .c-eyebrow fallback register applies); unknown role = loud."""

    def setUp(self):
        import compose_section as cs
        self.cs = cs
        self.doc = copy.deepcopy(FIXTURE)

    def test_declared_register_emits_scoped_var(self):
        css = self.cs.eyebrow_register_css(
            self.doc, {"id": "s", "eyebrowRegister": "accent/primary"}, "#sec-3")
        self.assertIn("#sec-3 { --c-eyebrow-color: var(--color-accent-primary); }",
                      css)

    def test_undeclared_layout_emits_nothing(self):
        self.assertEqual(self.cs.eyebrow_register_css(self.doc, {"id": "s"}, "#s"), "")

    def test_unknown_role_fails_loud(self):
        with self.assertRaises(KeyError):
            self.cs.eyebrow_register_css(
                self.doc, {"id": "s", "eyebrowRegister": "accent/nope"}, "#s")


if __name__ == "__main__":
    unittest.main()
