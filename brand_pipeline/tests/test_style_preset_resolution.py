#!/usr/bin/env python3
"""Resolver-behavior tests for the LIVE preset layer (§P, 2026-07-16).

style_resolver.py now loads pilot-presets.yaml + generated-presets.yaml as one
merged preset map and folds presets into resolution as LEVEL-2 DEFAULTS. These
tests pin the precedence guarantees:

  - LOADING: 50 presets (5 pilot + 45 generated) keyed into directives.yaml;
    pilot WINS on id collision; unknown preset ids fail closed; exemplars are
    stripped at load (calibration-only — never travel toward a prompt); the
    YAML-1.1 `on:` probe-key coercion is normalized in memory;
  - GAP-FILLING: with no brand facts (create-from-style posture) the full
    preset survives untouched, zero dissents;
  - BRAND WINS: every measured brand fact suppresses its preset slot(s) and
    logs a presetDissents row (winner=brand, provenance named) — proven on
    the real hubspot-v2 bundle and on targeted synthetic bundles;
  - BYTE-IDENTITY: dark-mode (the 1/51 uncovered id) resolves and renders
    byte-identically to a presets-empty library — the preset layer is purely
    additive, proven structurally (strip the preset lines from a preset
    style's block and the no-preset block remains);
  - RENDERING: the block carries the preset values, the 5 signatures as
    always/never guidance with check parameters, the explicit
    "authored defaults (uncalibrated) — any measured brand fact beats these"
    marker, and the preset-dissent ledger; no exemplar URL ever appears.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import style_resolver as sr  # noqa: E402

REPO = _BRAND_PIPELINE.parent
HUBSPOT_DIR = REPO / "runs" / "hubspot-v2" / "brand"

PILOT_IDS = {"swiss", "editorial-magazine", "neumorphism", "scandinavian", "japandi"}
UNCOVERED_STYLE = "dark-mode"


def _lib() -> sr.StyleLibrary:
    return sr.load_library()


def _presetless(lib: sr.StyleLibrary) -> sr.StyleLibrary:
    """The same library with the preset layer removed — the pre-preset world."""
    return sr.StyleLibrary(
        sections=lib.sections, styles=lib.styles, overrides=lib.overrides,
        primitives=lib.primitives, global_axes=lib.global_axes,
        presets={}, source_dir=lib.source_dir)


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, default=str)


# ─────────────────────────── loading + merge rules ─────────────────────────────────

class PresetLoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()

    def test_fifty_presets_pilot_plus_generated(self):
        self.assertEqual(len(self.lib.presets), 50)
        sources = {sid: p["source"] for sid, p in self.lib.presets.items()}
        self.assertEqual({sid for sid, s in sources.items() if s == "pilot"},
                         PILOT_IDS)
        self.assertEqual(sum(1 for s in sources.values() if s == "generated"), 45)

    def test_uncovered_style_has_no_preset(self):
        self.assertNotIn(UNCOVERED_STYLE, self.lib.presets)
        self.assertIn(UNCOVERED_STYLE, self.lib.styles)   # still a directive

    def test_every_preset_id_is_a_directive_id(self):
        for sid in self.lib.presets:
            self.assertIn(sid, self.lib.styles)

    def test_exemplars_stripped_at_load(self):
        for sid, entry in self.lib.presets.items():
            self.assertNotIn("exemplars", entry, sid)

    def test_probe_on_keys_normalized_from_yaml_bool(self):
        """The preset files write `{ on: display, ... }`; YAML 1.1 parses the
        bare `on` key as boolean True. The loader must hand back string keys."""
        seen_probe = False
        for sid, entry in self.lib.presets.items():
            for g in entry["signatures"]:
                for probe in (g.get("check") or {}).get("probes") or []:
                    seen_probe = True
                    self.assertNotIn(True, probe, f"{sid}/{g['id']}")
                    self.assertIn("on", probe, f"{sid}/{g['id']}")
        self.assertTrue(seen_probe)

    def test_pilot_wins_on_id_collision(self):
        """Append a conflicting swiss entry to generated-presets.yaml in a
        temp copy of the library — the pilot's values must survive."""
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "lib"
            shutil.copytree(sr.LIBRARY_DIR, bad)
            gen = bad / "styles" / "generated-presets.yaml"
            gen.write_text(gen.read_text() + (
                "\n  swiss:\n"
                "    preset:\n"
                '      font: { display: { family: "Impostor Sans" } }\n'))
            lib = sr.load_library(bad)
            self.assertEqual(lib.presets["swiss"]["source"], "pilot")
            self.assertEqual(
                lib.presets["swiss"]["preset"]["font"]["display"]["family"],
                "Neue Haas Grotesk Display")

    def test_unknown_preset_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "lib"
            shutil.copytree(sr.LIBRARY_DIR, bad)
            gen = bad / "styles" / "generated-presets.yaml"
            gen.write_text(gen.read_text() + (
                "\n  not-a-style:\n"
                "    preset: {}\n"))
            with self.assertRaises(sr.StyleResolutionError) as ctx:
                sr.load_library(bad)
            self.assertIn("not-a-style", str(ctx.exception))

    def test_missing_preset_files_degrade_to_directive_only(self):
        with tempfile.TemporaryDirectory() as td:
            bare = Path(td) / "lib"
            shutil.copytree(sr.LIBRARY_DIR, bare)
            (bare / "styles" / "pilot-presets.yaml").unlink()
            (bare / "styles" / "generated-presets.yaml").unlink()
            lib = sr.load_library(bare)
            self.assertEqual(lib.presets, {})
            r = sr.resolve("hero", "swiss", lib)
            self.assertNotIn("stylePreset", r)


# ─────────────────────────── precedence: preset fills gaps ─────────────────────────

class PresetFillsGaps(unittest.TestCase):
    """Create-from-style posture: the brand has NO measured facts, so the
    preset speaks in full as the level-2 default."""

    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()

    def test_no_brand_keeps_full_preset_no_dissents(self):
        for style in ("bauhaus", "cyberpunk", "swiss"):
            for brand in (None, sr.BrandBundle()):
                r = sr.resolve("hero", style, self.lib, brand)
                self.assertIn("stylePreset", r, style)
                self.assertEqual(r["presetDissents"], [], style)
                p = r["stylePreset"]["preset"]
                for axis in ("font", "type", "color", "space", "shape",
                             "layout", "imagery"):
                    self.assertIn(axis, p, f"{style} lost {axis}")

    def test_partial_facts_suppress_only_their_slots(self):
        """A bundle carrying ONLY measured radius modes beats shape.radiusPx;
        font/color/space presets survive as the defaults they are."""
        bundle = sr.BrandBundle(style_scale={
            "schema": "style-scale.v1",
            "radius": {"modes": [{"px": 8, "roles": ["button"]}], "policy": "tiered"},
        })
        r = sr.resolve("hero", "bauhaus", self.lib, bundle)
        slots = {d["slot"] for d in r["presetDissents"]}
        self.assertEqual(slots, {"shape.radiusPx"})
        p = r["stylePreset"]["preset"]
        self.assertNotIn("radiusPx", p.get("shape") or {})
        self.assertIn("borderWidthPx", p["shape"])        # rest of shape survives
        self.assertIn("font", p)
        self.assertIn("color", p)
        self.assertIn("space", p)

    def test_genuinely_differing_preset_ratio_survives_without_brand_fact(self):
        """Presets carry REAL values — a preset scaleRatio is a deliberate
        authored default (the §5 filler rule applies to directives only) and
        survives when no measured brand ratio exists."""
        r = sr.resolve("hero", "bauhaus", self.lib, sr.BrandBundle())
        self.assertEqual(r["stylePreset"]["preset"]["type"]["scaleRatio"], 1.333)
        # even a preset 1.25 survives — it is authored, not filler
        r2 = sr.resolve("hero", "scandinavian", self.lib, sr.BrandBundle())
        self.assertEqual(r2["stylePreset"]["preset"]["type"]["scaleRatio"], 1.25)


# ─────────────────────────── precedence: brand facts win ───────────────────────────

class BrandFactBeatsPreset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()
        cls.bundle = sr.load_brand_bundle(HUBSPOT_DIR)

    def test_hubspot_facts_suppress_their_preset_slots_with_dissents(self):
        r = sr.resolve("hero", "bauhaus", self.lib, self.bundle)
        slots = {d["slot"] for d in r["presetDissents"]}
        self.assertEqual(slots, {"font.display", "font.body", "type.scaleRatio",
                                 "type.baseSizePx", "space", "shape.radiusPx",
                                 "color"})
        for d in r["presetDissents"]:
            self.assertEqual(d["winner"], "brand", d["slot"])
            self.assertTrue(d["provenance"], d["slot"])
            self.assertIsNotNone(d["preset"], d["slot"])
        p = r["stylePreset"]["preset"]
        self.assertNotIn("font", p)
        self.assertNotIn("color", p)
        self.assertNotIn("space", p)

    def test_unmeasured_slots_survive_the_brand_merge(self):
        """hubspot carries no measured imagery/layout/border facts — those
        preset slots stay, exactly the fill-only-the-gaps contract."""
        r = sr.resolve("hero", "bauhaus", self.lib, self.bundle)
        p = r["stylePreset"]["preset"]
        self.assertIn("imagery", p)
        self.assertIn("layout", p)
        self.assertIn("borderWidthPx", p.get("shape") or {})
        self.assertEqual(r["stylePreset"]["signatures"][0]["id"],
                         "primary-triad-restraint")   # signatures always survive

    def test_preset_dissent_values_echo_the_brand_binding(self):
        r = sr.resolve("hero", "cyberpunk", self.lib, self.bundle)
        by_slot = {d["slot"]: d for d in r["presetDissents"]}
        self.assertEqual(by_slot["type.scaleRatio"]["brand"], 1.125)
        self.assertEqual(by_slot["font.display"]["brand"], "HubSpot Serif")
        self.assertIn("style-scale.yaml", by_slot["type.scaleRatio"]["provenance"])

    def test_directive_dissents_unchanged_by_preset_layer(self):
        """The §4.2 directive dissent ledger is untouched — presets add their
        own ledger, they never rewrite constraints."""
        r = sr.resolve("hero", "editorial-magazine", self.lib, self.bundle)
        directive_keys = {d["key"] for d in r["dissents"]}
        self.assertLessEqual({"scaleRatio", "typeDisplay", "typeBody", "case"},
                             directive_keys)
        self.assertEqual(r["constraints"]["scaleRatio"], 1.125)


# ─────────────────────────── byte-identity for the uncovered style ─────────────────

class UncoveredStyleByteIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()
        cls.bare = _presetless(cls.lib)
        cls.bundle = sr.load_brand_bundle(HUBSPOT_DIR)

    def test_resolution_identical_to_presetless_library(self):
        for brand in (None, self.bundle):
            with_presets = sr.resolve_all(UNCOVERED_STYLE, self.lib, brand)
            without = sr.resolve_all(UNCOVERED_STYLE, self.bare, brand)
            self.assertEqual(_canon(with_presets), _canon(without))
            for res in with_presets.values():
                self.assertNotIn("stylePreset", res)
                self.assertNotIn("presetDissents", res)

    def test_rendered_block_byte_identical(self):
        for brand in (None, self.bundle):
            res = sr.resolve_all(UNCOVERED_STYLE, self.lib, brand,
                                 ["hero", "cta-band", "pricing"])
            res_bare = sr.resolve_all(UNCOVERED_STYLE, self.bare, brand,
                                      ["hero", "cta-band", "pricing"])
            a = sr.render_style_directive_block(UNCOVERED_STYLE, res, self.lib)
            b = sr.render_style_directive_block(UNCOVERED_STYLE, res_bare, self.bare)
            self.assertEqual(a, b)
            self.assertNotIn("Style preset", a)
            self.assertNotIn("uncalibrated", a)


# ─────────────────────────── rendering the preset block ────────────────────────────

class PresetBlockRendering(unittest.TestCase):
    SECTIONS = ["hero", "feature-trio", "cta-band"]

    @classmethod
    def setUpClass(cls):
        cls.lib = _lib()
        cls.bundle = sr.load_brand_bundle(HUBSPOT_DIR)

    def _block(self, style, brand=None, sections=None):
        res = sr.resolve_all(style, self.lib, brand, sections or self.SECTIONS)
        return sr.render_style_directive_block(style, res, self.lib)

    def test_uncalibrated_marker_present_for_preset_styles(self):
        for style in ("bauhaus", "swiss", "cyberpunk"):
            block = self._block(style)
            self.assertIn("authored defaults (uncalibrated) — any measured brand",
                          block, style)
            self.assertIn("fact beats these", block, style)
            self.assertIn("style-calibration workflow", block, style)

    def test_block_carries_preset_values_create_from_style(self):
        """No brand: font pairing, palette (oklch+hex), space, shape, layout,
        imagery, and the 5 signatures with check parameters all render."""
        block = self._block("bauhaus")
        self.assertIn('display "Josefin Sans"', block)
        self.assertIn("stack: Josefin Sans, Futura, Century Gothic, sans-serif", block)
        self.assertIn("bg oklch(0.97 0.01 90) (#f7f2e4)", block)
        self.assertIn("steps(px) 8, 16, 24, 40, 64", block)
        self.assertIn("section rhythm 88px", block)
        self.assertIn("radius(px) button 0 / card 0 / input 0", block)
        self.assertIn("max-width 1200", block)
        self.assertIn("geometric abstraction", block)          # imagery
        self.assertIn("check thresholds UNCALIBRATED", block)
        self.assertIn("[always] primary-triad-restraint (accent-scope)", block)
        self.assertIn("[never] sharp-corners (shape-motif)", block)
        self.assertIn("maxPaintSharePct=15", block)            # check parameters
        self.assertIn("ratio 1.333", block)

    def test_block_shows_preset_dissent_ledger_under_brand(self):
        block = self._block("bauhaus", self.bundle)
        self.assertIn("Preset slots suppressed by measured brand facts", block)
        self.assertIn("font.display: authored default → brand fact HubSpot Serif WINS",
                      block)
        self.assertIn("color: authored default → brand fact brand-owned palette WINS",
                      block)
        # suppressed slots must NOT render their preset values
        self.assertNotIn('display "Josefin Sans"', block)
        self.assertNotIn("#f7f2e4", block)
        # unmeasured slots still render
        self.assertIn("geometric abstraction", block)

    def test_no_exemplar_ever_reaches_the_block(self):
        """Anti-mimicry: exemplars are calibration-only. No URL, no exemplar
        name may render for any preset style."""
        for style in ("bauhaus", "swiss", "cyberpunk", "luxury-fashion"):
            block = self._block(style)
            self.assertNotIn("http", block, style)
            self.assertNotIn("calibration-only", block, style)

    def test_preset_lines_are_purely_additive(self):
        """Strip the injected preset lines from a preset style's block and the
        presetless render remains — mirrors the prompt-injection additivity
        proofs."""
        bare = _presetless(self.lib)
        block = self._block("bauhaus")
        res_bare = sr.resolve_all("bauhaus", bare, None, self.SECTIONS)
        block_bare = sr.render_style_directive_block("bauhaus", res_bare, bare)
        res = sr.resolve_all("bauhaus", self.lib, None, self.SECTIONS)
        preset_lines = sr._preset_lines(next(iter(res.values())))
        injected = "\n" + "\n".join(["", *preset_lines])
        self.assertIn(injected, block)
        self.assertEqual(block.replace(injected, "", 1), block_bare)

    def test_block_deterministic(self):
        a = self._block("cyberpunk", self.bundle)
        b = self._block("cyberpunk", self.bundle)
        self.assertEqual(a, b)

    def test_pilot_preset_renders_for_pilot_styles(self):
        block = self._block("swiss")
        self.assertIn('display "Neue Haas Grotesk Display"', block)
        self.assertIn("accent oklch(0.56 0.21 27) (#de2010)", block)
        self.assertIn("[always] accent-structural-only (accent-scope)", block)


# ─────────────────────────── all-pairs smoke with presets live ─────────────────────

class AllPairsWithPresets(unittest.TestCase):
    def test_every_section_x_style_resolves_and_renders(self):
        lib = _lib()
        for style in lib.styles:
            res = sr.resolve_all(style, lib)
            self.assertEqual(len(res), 21, style)
            block = sr.render_style_directive_block(style, res, lib)
            self.assertTrue(block.startswith(sr.STYLE_BLOCK_BEGIN), style)
            if style == UNCOVERED_STYLE:
                self.assertNotIn("Style preset", block)
            else:
                self.assertIn("authored defaults (uncalibrated)", block, style)


if __name__ == "__main__":
    unittest.main()
