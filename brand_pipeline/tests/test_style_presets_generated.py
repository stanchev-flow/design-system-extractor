#!/usr/bin/env python3
"""Format-lock tests for the GENERATED preset import (2026-07-16).

contracts/style-library/styles/generated-presets.yaml is the Claude-Design
delivery of the 45 non-pilot style presets, imported behind the same
authored-prior discipline as the pilot (tests/test_style_presets_pilot.py owns
the pilot 5 + extraction-map; THIS file owns the 45). Locks:

  - exactly 45 styles, every id resolving into directives.yaml, DISJOINT from
    the pilot ids; coverage math pinned explicitly: 51 directives = 5 pilot +
    45 generated + exactly ONE uncovered style, `dark-mode`;
  - preset axes present with oklch+hex mirrored color roles and complete
    display/body font slots;
  - exactly 5 signatures per style in the signature-gate schema (legal kinds,
    modes always/never plus the delivery's 6 documented `sometimes` rows,
    legal role vocabulary, claim + non-empty check on every row);
  - the request's color self-consistency floors hold for ALL 45 from the hex
    mirrors (text/bg ≥ 4.5, text/surface ≥ 4.5, muted/bg ≥ 3.0; rgba surfaces
    composited over bg; dark styles compute identically — contrast math is
    symmetric) — locks the NINE transparent import fixes (y2k, vaporwave,
    psychedelic, glassmorphism, claymorphism, boutique-wellness, maximalist,
    anti-design ×2), each pinned to its shipped value;
  - exemplar policy: every exemplar carries url + lookAt +
    usage: calibration-only; the delivery's 17 single-exemplar styles are
    pinned as a KNOWN GAP (queued for the deferred calibration pass) — every
    other style carries 2+;
  - no-filler hard line: no two styles (across all 50 presets incl. pilot)
    share an identical font+palette+radius triple; scaleRatio carries real
    signal. Near-duplicate shared-axis pairs are calibration-queue notes in
    ../contracts/style-library/changes.md, NOT failures here (calibration is
    deferred by design);
  - provenance + UNCALIBRATED + EXEMPLAR USAGE POLICY headers present.
"""
from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

LIB = _BRAND_PIPELINE / "contracts" / "style-library"
GEN_PATH = LIB / "styles" / "generated-presets.yaml"
PILOT_PATH = LIB / "styles" / "pilot-presets.yaml"

GEN = yaml.safe_load(GEN_PATH.read_text())
PILOT = yaml.safe_load(PILOT_PATH.read_text())
DIRECTIVES = yaml.safe_load((LIB / "styles" / "directives.yaml").read_text())

STYLES = GEN["styles"]
PILOT_IDS = {"swiss", "editorial-magazine", "neumorphism", "scandinavian", "japandi"}
UNCOVERED_STYLE = "dark-mode"          # the 1/51 directive id with NO preset

SIGNATURE_KINDS = {"accent-scope", "shape-motif", "type-treatment", "surface-habit",
                   "spacing-habit"}
SIGNATURE_MODES = {"always", "never", "sometimes"}
ROLE_VOCAB = {"action-primary", "arrow-link", "logo-mark", "body-text", "heading",
              "divider", "icon", "badge"}

# the delivery gap documented in the file header: single-exemplar styles queued
# for the deferred calibration pass to top up to the 2-3 target
SINGLE_EXEMPLAR_STYLES = {
    "y2k", "vaporwave", "pixel-8bit", "psychedelic", "art-deco", "art-nouveau",
    "skeuomorphic", "ios-hig", "fluent", "hand-drawn", "collage", "organic",
    "grunge", "textured-paper", "anti-design", "cyberpunk", "poster-typographic",
}

# the nine transparent WCAG import fixes (style, role, shipped oklch, shipped hex)
IMPORT_FIXES = [
    ("y2k", "muted", "oklch(0.48 0.02 250)", "#6c7486"),
    ("vaporwave", "surface", "oklch(0.56 0.13 280)", "#7a58bc"),
    ("psychedelic", "surface", "oklch(0.5 0.2 30)", "#c54114"),
    ("glassmorphism", "bg", "oklch(0.5 0.2 280)", "#6d3fc0"),
    ("claymorphism", "muted", "oklch(0.53 0.03 300)", "#847493"),
    ("boutique-wellness", "muted", "oklch(0.57 0.02 55)", "#918665"),
    ("maximalist", "surface", "oklch(0.62 0.2 340)", "#d05098"),
    ("anti-design", "text", "oklch(0.39 0.2 280)", "#772aa5"),
    ("anti-design", "muted", "oklch(0.43 0 0)", "#6c6c6c"),
]


# ── color math (hex mirrors; rgba composited over bg — CSS source-over) ─────────────

def _rgb(hex_color: str) -> tuple[float, float, float]:
    return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _parse(value: str, bg_hex: str) -> tuple[float, float, float]:
    value = value.strip()
    if value.startswith("#"):
        return _rgb(value)
    if value.startswith("rgba"):
        parts = value[value.index("(") + 1:value.rindex(")")].split(",")
        r, g, b = (float(p) / 255 for p in parts[:3])
        a = float(parts[3])
        br, bgc, bb = _rgb(bg_hex)
        return (a * r + (1 - a) * br, a * g + (1 - a) * bgc, a * b + (1 - a) * bb)
    raise ValueError(value)


def _rel_lum(rgb: tuple[float, float, float]) -> float:
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2])


def _contrast(a: tuple, b: tuple) -> float:
    la, lb = _rel_lum(a), _rel_lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _axes(style: dict) -> dict:
    p = style["preset"]
    c = p["color"]
    accent = c.get("accent") or c.get("accentPrimary") or {}
    shadow = str(p["shape"].get("shadow", ""))
    return {
        "scaleRatio": p["type"].get("scaleRatio"),
        "baseSize": p["type"].get("baseSizePx"),
        "radiusBtn": p["shape"]["radiusPx"]["button"],
        "border": p["shape"].get("borderWidthPx"),
        "shadow": "none" if shadow.startswith("none") else "recipe",
        "maxWidth": p["layout"].get("maxWidthPx"),
        "gutter": p["layout"].get("gutterPx"),
        "rhythm": p["space"].get("sectionRhythmPx"),
        "steps": tuple(p["space"].get("stepsPx") or []),
        "displayFont": p["font"]["display"].get("family"),
        "accent": accent.get("hex"),
        "bg": c["bg"]["hex"],
    }


class CoverageMath(unittest.TestCase):
    def test_exactly_45_styles_all_resolving_into_directives(self):
        self.assertEqual(len(STYLES), 45)
        for sid in STYLES:
            self.assertIn(sid, DIRECTIVES["styles"], f"{sid} not a directives.yaml id")

    def test_disjoint_from_pilot(self):
        self.assertFalse(set(STYLES) & PILOT_IDS)
        self.assertFalse(set(STYLES) & set(PILOT["styles"]))

    def test_51_equals_5_plus_45_plus_one_uncovered(self):
        """The coverage accounting, pinned: dark-mode is the ONLY directive
        style with no preset in either file."""
        directive_ids = set(DIRECTIVES["styles"])
        self.assertEqual(len(directive_ids), 51)
        covered = set(STYLES) | set(PILOT["styles"])
        self.assertEqual(directive_ids - covered, {UNCOVERED_STYLE})

    def test_neighbors_reference_real_directive_ids(self):
        for sid, s in STYLES.items():
            for n in s.get("neighbors") or []:
                self.assertIn(n, DIRECTIVES["styles"], f"{sid} neighbor {n}")
            for n in s.get("neighbors") or []:
                self.assertIn(n, s.get("distinguishers") or {},
                              f"{sid} missing distinguisher for neighbor {n}")


class PresetShape(unittest.TestCase):
    def test_preset_axes_present(self):
        for sid, s in STYLES.items():
            p = s["preset"]
            for axis in ("font", "type", "color", "space", "shape", "layout", "imagery"):
                self.assertIn(axis, p, f"{sid} preset missing `{axis}`")

    def test_color_roles_with_oklch_hex_mirrors(self):
        for sid, s in STYLES.items():
            c = s["preset"]["color"]
            for role in ("bg", "surface", "text", "muted", "border"):
                self.assertIn(role, c, f"{sid} color missing `{role}`")
                self.assertIn("oklch", c[role], f"{sid}.{role}")
                self.assertIn("hex", c[role], f"{sid}.{role}")
            self.assertTrue(
                any(role == "accent" or role.startswith("accent") for role in c),
                f"{sid} carries no accent role")

    def test_font_slots_complete(self):
        for sid, s in STYLES.items():
            for slot in ("display", "body"):
                f = s["preset"]["font"][slot]
                self.assertTrue(f.get("family"), f"{sid}.{slot}")
                self.assertTrue(f.get("stack"), f"{sid}.{slot}")
                self.assertTrue(f.get("weights"), f"{sid}.{slot}")


class SignatureSchema(unittest.TestCase):
    def test_exactly_five_legal_signatures_each(self):
        for sid, s in STYLES.items():
            sigs = s["signatures"]
            self.assertEqual(len(sigs), 5, sid)
            for g in sigs:
                self.assertIn(g["kind"], SIGNATURE_KINDS, f"{sid}/{g['id']}")
                self.assertIn(g["mode"], SIGNATURE_MODES, f"{sid}/{g['id']}")
                self.assertTrue(g.get("claim"), f"{sid}/{g['id']} missing claim")
                self.assertIsInstance(g.get("check"), dict, f"{sid}/{g['id']}")
                self.assertTrue(g["check"], f"{sid}/{g['id']} empty check")

    def test_sometimes_mode_stays_the_documented_six(self):
        """`sometimes` (optional motifs) is prompt guidance, never a gate —
        the delivery shipped exactly 6 rows; new ones must be deliberate."""
        rows = [f"{sid}/{g['id']}" for sid, s in STYLES.items()
                for g in s["signatures"] if g["mode"] == "sometimes"]
        self.assertEqual(sorted(rows), [
            "bento-grid/tile-background-variation",
            "book-literary/drop-cap-optional",
            "claymorphism/playful-mascot-illustration",
            "poster-typographic/image-optional",
            "skeuomorphic/stitch-and-seam-details",
            "vaporwave/classical-bust-iconography",
        ])

    def test_role_vocabulary(self):
        for sid, s in STYLES.items():
            for g in s["signatures"]:
                for key in ("allowedRoles", "forbiddenRoles"):
                    extra = set(g["check"].get(key, [])) - ROLE_VOCAB
                    self.assertFalse(extra, f"{sid}/{g['id']} unknown roles {extra}")


class ColorSelfConsistency(unittest.TestCase):
    def test_request_floors_hold_for_all_45(self):
        """text/bg ≥ 4.5 · text/surface ≥ 4.5 · muted/bg ≥ 3.0, computed from
        the hex mirrors; rgba surfaces composite over bg first; dark styles
        compute the same way (contrast math is symmetric)."""
        for sid, s in STYLES.items():
            c = s["preset"]["color"]
            bg_hex = c["bg"]["hex"]
            text = _parse(c["text"]["hex"], bg_hex)
            bg = _parse(c["bg"]["hex"], bg_hex)
            surface = _parse(c["surface"]["hex"], bg_hex)
            muted = _parse(c["muted"]["hex"], bg_hex)
            self.assertGreaterEqual(_contrast(text, bg), 4.5, f"{sid} text/bg")
            self.assertGreaterEqual(_contrast(text, surface), 4.5, f"{sid} text/surface")
            self.assertGreaterEqual(_contrast(muted, bg), 3.0, f"{sid} muted/bg")

    def test_the_nine_import_fixes_are_pinned(self):
        """The transparent fixes shipped at import (header ledger) — drift here
        means someone re-imported without re-running the floors."""
        for sid, role, oklch, hexv in IMPORT_FIXES:
            entry = STYLES[sid]["preset"]["color"][role]
            self.assertEqual(entry["oklch"], oklch, f"{sid}.{role}")
            self.assertEqual(entry["hex"], hexv, f"{sid}.{role}")

    def test_fix_ledger_lives_in_the_header(self):
        head = GEN_PATH.read_text()[:4000]
        self.assertIn("NINE color defects fixed transparently", head)
        for sid, *_ in IMPORT_FIXES:
            self.assertIn(sid, head, f"fix ledger missing {sid}")


class ExemplarPolicy(unittest.TestCase):
    def test_every_exemplar_tagged_and_complete(self):
        for sid, s in STYLES.items():
            for e in s["exemplars"]:
                self.assertEqual(e.get("usage"), "calibration-only",
                                 f"{sid}/{e.get('name')}")
                self.assertTrue(str(e.get("url", "")).startswith("http"),
                                f"{sid}/{e.get('name')}")
                self.assertTrue(e.get("lookAt"), f"{sid}/{e.get('name')}")

    def test_counts_two_plus_except_the_documented_gap(self):
        """17 styles arrived with ONE exemplar (short of the 2-3 target) —
        pinned as the known delivery gap, queued for the deferred calibration
        pass. Everything else carries 2+."""
        singles = {sid for sid, s in STYLES.items() if len(s["exemplars"]) == 1}
        self.assertEqual(singles, SINGLE_EXEMPLAR_STYLES)
        for sid, s in STYLES.items():
            if sid not in SINGLE_EXEMPLAR_STYLES:
                self.assertGreaterEqual(len(s["exemplars"]), 2, sid)
            self.assertLessEqual(len(s["exemplars"]), 3, sid)

    def test_policy_block_present(self):
        text = GEN_PATH.read_text()
        self.assertIn("EXEMPLAR USAGE POLICY", text)
        self.assertIn("NOT generation input", text)
        self.assertIn("NOT pixel-compared", text)


class NoFiller(unittest.TestCase):
    """Calibration is deferred: near-duplicate pairs are queue notes in
    changes.md, not failures. The HARD line is identical font+palette+radius
    triples — none may exist across all 50 presets."""

    @classmethod
    def setUpClass(cls):
        cls.all_styles = {**STYLES, **PILOT["styles"]}

    def test_no_identical_font_palette_radius_triples(self):
        import json
        triples: dict = {}
        for sid, s in self.all_styles.items():
            p = s["preset"]
            key = (p["font"]["display"].get("family"),
                   tuple(sorted((r, v.get("hex")) for r, v in p["color"].items())),
                   json.dumps(p["shape"]["radiusPx"], sort_keys=True))
            triples.setdefault(key, []).append(sid)
        dupes = [v for v in triples.values() if len(v) > 1]
        self.assertFalse(dupes, f"identical font+palette+radius triples: {dupes}")

    def test_no_pair_is_axis_identical(self):
        ax = {sid: _axes(s) for sid, s in self.all_styles.items()}
        for a, b in itertools.combinations(sorted(self.all_styles), 2):
            shared = [k for k in ax[a] if ax[a][k] == ax[b][k]]
            self.assertLess(len(shared), len(ax[a]), f"{a} vs {b} fully identical")

    def test_scale_ratio_carries_signal(self):
        ratios = {s["preset"]["type"]["scaleRatio"] for s in STYLES.values()}
        self.assertGreaterEqual(len(ratios), 6, f"ratios collapsed: {ratios}")


class ProvenanceHeaders(unittest.TestCase):
    def test_authored_prior_first_line(self):
        head = GEN_PATH.read_text().split("\n", 1)[0]
        self.assertIn("authored-prior", head)
        self.assertIn("2026-07-16", head)

    def test_uncalibrated_status_and_calibration_path_stated(self):
        head = GEN_PATH.read_text()[:4000]
        self.assertIn("UNCALIBRATED", head)
        self.assertIn("style-calibration", head)
        self.assertIn("LEVEL-2 DEFAULTS", head)
        self.assertIn("beaten by any measured brand fact", head)

    def test_uncovered_style_named_in_header(self):
        self.assertIn(UNCOVERED_STYLE, GEN_PATH.read_text()[:4500])


if __name__ == "__main__":
    unittest.main()
