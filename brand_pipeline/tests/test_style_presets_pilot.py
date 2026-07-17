#!/usr/bin/env python3
"""Format-lock tests for the style preset PILOT import (2026-07-15).

contracts/style-library/styles/pilot-presets.yaml + extraction-map.yaml are the
Claude-Design "spec 3" deliverables answering REQUEST-preset-pilot.md. These tests
lock the pilot format so (a) the import can't drift, and (b) the remaining 46
styles must arrive in the same shape or fail here:

  - 5 pilot styles, ids resolving into directives.yaml, presets carrying the
    required axes with plausible values;
  - exactly 5 signatures each, in the signature-gate schema (legal kinds/modes/
    role vocabulary);
  - exemplars 2-3 per style, EVERY one tagged calibration-only (the anti-mimicry
    policy — exemplars must never reach a generation prompt);
  - the request's color self-consistency floors hold (text/bg + text/surface AA,
    muted/bg 3:1) — locks the transparent import fix on neumorphism muted;
  - no-filler: no style pair shares more than 4 preset axes;
  - the pass/fail neighbor pair (scandinavian vs japandi) is separable by
    signature checks alone (disjoint display families, cross-failing radii,
    different whitespace floors);
  - extraction map covers every token-schema leaf (documented aggregates
    excepted), bindings are only snap|literal, snap entries carry a snapRule,
    and the confidence policy exists;
  - both files carry the authored-prior provenance header.
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
PILOT_PATH = LIB / "styles" / "pilot-presets.yaml"
EMAP_PATH = LIB / "extraction-map.yaml"

PILOT = yaml.safe_load(PILOT_PATH.read_text())
EMAP = yaml.safe_load(EMAP_PATH.read_text())
DIRECTIVES = yaml.safe_load((LIB / "styles" / "directives.yaml").read_text())
TOKEN_SCHEMA = yaml.safe_load((LIB / "token-schema.yaml").read_text())

STYLES = PILOT["styles"]
PILOT_IDS = ["swiss", "editorial-magazine", "neumorphism", "scandinavian", "japandi"]

SIGNATURE_KINDS = {"accent-scope", "shape-motif", "type-treatment", "surface-habit", "spacing-habit"}
ROLE_VOCAB = {"action-primary", "arrow-link", "logo-mark", "body-text", "heading",
              "divider", "icon", "badge"}


def _rel_lum(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(a: str, b: str) -> float:
    la, lb = _rel_lum(a), _rel_lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _axes(style: dict) -> dict:
    p = style["preset"]
    return {
        "scaleRatio": p["type"]["scaleRatio"], "baseSize": p["type"]["baseSizePx"],
        "radiusBtn": p["shape"]["radiusPx"]["button"], "border": p["shape"]["borderWidthPx"],
        "shadow": "none" if p["shape"]["shadow"] == "none" else "recipe",
        "maxWidth": p["layout"]["maxWidthPx"], "gutter": p["layout"]["gutterPx"],
        "rhythm": p["space"]["sectionRhythmPx"], "steps": tuple(p["space"]["stepsPx"]),
        "displayFont": p["font"]["display"]["family"], "accent": p["color"]["accent"]["hex"],
        "bg": p["color"]["bg"]["hex"],
    }


class PilotShape(unittest.TestCase):
    def test_five_styles_with_known_ids(self):
        self.assertEqual(sorted(STYLES), sorted(PILOT_IDS))
        for sid in STYLES:
            self.assertIn(sid, DIRECTIVES["styles"], f"{sid} not a directives.yaml id")

    def test_preset_axes_present(self):
        for sid, s in STYLES.items():
            p = s["preset"]
            for axis in ("font", "type", "color", "space", "shape", "layout", "imagery"):
                self.assertIn(axis, p, f"{sid} preset missing `{axis}`")
            for role in ("bg", "surface", "text", "muted", "border", "accent"):
                self.assertIn(role, p["color"], f"{sid} color missing `{role}`")
                self.assertIn("oklch", p["color"][role])
                self.assertIn("hex", p["color"][role])
            for slot in ("display", "body"):
                f = p["font"][slot]
                self.assertTrue(f.get("family") and f.get("stack") and f.get("weights"))

    def test_provenance_headers(self):
        for path in (PILOT_PATH, EMAP_PATH):
            head = path.read_text().split("\n", 1)[0]
            self.assertIn("authored-prior", head, f"{path.name} missing provenance header")


class SignatureSchema(unittest.TestCase):
    def test_exactly_five_legal_signatures_each(self):
        for sid, s in STYLES.items():
            sigs = s["signatures"]
            self.assertEqual(len(sigs), 5, sid)
            for g in sigs:
                self.assertIn(g["kind"], SIGNATURE_KINDS, f"{sid}/{g['id']}")
                self.assertIn(g["mode"], ("always", "never"), f"{sid}/{g['id']}")
                self.assertTrue(g.get("claim"), f"{sid}/{g['id']} missing claim")
                self.assertIsInstance(g.get("check"), dict, f"{sid}/{g['id']} missing check")

    def test_role_vocabulary(self):
        for sid, s in STYLES.items():
            for g in s["signatures"]:
                for key in ("allowedRoles", "forbiddenRoles"):
                    extra = set(g["check"].get(key, [])) - ROLE_VOCAB
                    self.assertFalse(extra, f"{sid}/{g['id']} unknown roles {extra}")

    def test_all_five_kinds_covered_per_style(self):
        for sid, s in STYLES.items():
            kinds = {g["kind"] for g in s["signatures"]}
            # neumorphism doubles surface-habit (its identity) and skips spacing-habit;
            # every other pilot style covers all 5 kinds
            if sid == "neumorphism":
                self.assertIn("surface-habit", kinds)
                self.assertGreaterEqual(len(kinds), 4, sid)
            else:
                self.assertEqual(kinds, SIGNATURE_KINDS, sid)


class ExemplarPolicy(unittest.TestCase):
    def test_two_to_three_each_all_calibration_only(self):
        for sid, s in STYLES.items():
            ex = s["exemplars"]
            self.assertTrue(2 <= len(ex) <= 3, f"{sid} has {len(ex)} exemplars")
            for e in ex:
                self.assertEqual(e.get("usage"), "calibration-only", f"{sid}/{e.get('name')}")
                self.assertTrue(e.get("url", "").startswith("http"), f"{sid}/{e.get('name')}")
                self.assertTrue(e.get("lookAt"), f"{sid}/{e.get('name')} missing lookAt")

    def test_policy_block_present(self):
        text = PILOT_PATH.read_text()
        self.assertIn("EXEMPLAR USAGE POLICY", text)
        self.assertIn("NOT generation input", text)
        self.assertIn("NOT pixel-compared", text)


class ColorSelfConsistency(unittest.TestCase):
    def test_request_floors_hold(self):
        for sid, s in STYLES.items():
            c = s["preset"]["color"]
            self.assertGreaterEqual(_contrast(c["text"]["hex"], c["bg"]["hex"]), 4.5, f"{sid} text/bg")
            self.assertGreaterEqual(_contrast(c["text"]["hex"], c["surface"]["hex"]), 4.5, f"{sid} text/surface")
            self.assertGreaterEqual(_contrast(c["muted"]["hex"], c["bg"]["hex"]), 3.0, f"{sid} muted/bg")


class NoFiller(unittest.TestCase):
    def test_no_pair_shares_more_than_four_axes(self):
        ax = {sid: _axes(s) for sid, s in STYLES.items()}
        for a, b in itertools.combinations(STYLES, 2):
            shared = [k for k in ax[a] if ax[a][k] == ax[b][k]]
            self.assertLessEqual(len(shared), 4, f"{a} vs {b} share {shared}")

    def test_scale_ratio_carries_signal(self):
        ratios = {s["preset"]["type"]["scaleRatio"] for s in STYLES.values()}
        self.assertGreaterEqual(len(ratios), 3, f"ratios collapsed: {ratios}")


class NeighborSeparation(unittest.TestCase):
    """The pilot's pass/fail bar: scandinavian vs japandi by checks alone."""

    def _display_families(self, sid):
        fams = set()
        for g in STYLES[sid]["signatures"]:
            if g["kind"] != "type-treatment":
                continue
            for probe in g["check"]["probes"]:
                if probe.get("on") == "display":
                    fams |= set(probe["familyIncludesAny"])
        return fams

    def test_display_family_sets_disjoint(self):
        self.assertFalse(self._display_families("scandinavian") & self._display_families("japandi"))

    def test_radii_cross_fail(self):
        sc_preset = STYLES["scandinavian"]["preset"]["shape"]["radiusPx"]["button"]
        jp_preset = STYLES["japandi"]["preset"]["shape"]["radiusPx"]["button"]
        sc_check = next(g["check"]["buttons"]["radiusPx"] for g in STYLES["scandinavian"]["signatures"]
                        if g["kind"] == "shape-motif")
        jp_check = next(g["check"]["buttons"]["radiusPx"] for g in STYLES["japandi"]["signatures"]
                        if g["kind"] == "shape-motif")
        self.assertNotEqual(sc_preset, jp_check)
        self.assertNotEqual(jp_preset, sc_check)

    def test_whitespace_floors_separate(self):
        sc = next(g["check"]["whitespaceRatioMin"] for g in STYLES["scandinavian"]["signatures"]
                  if g["kind"] == "spacing-habit")
        jp = next(g["check"]["whitespaceRatioMin"] for g in STYLES["japandi"]["signatures"]
                  if g["kind"] == "spacing-habit")
        self.assertLess(sc, jp, "scandinavian preset must fail japandi's whitespace floor")

    def test_temperature_separates_in_values(self):
        # cool bg (blue-family hue) vs warm bg (yellow-family hue) via oklch hue readouts
        sc_bg = STYLES["scandinavian"]["preset"]["color"]["bg"]["oklch"]
        jp_bg = STYLES["japandi"]["preset"]["color"]["bg"]["oklch"]
        sc_hue = float(sc_bg.split()[-1].rstrip(")"))
        jp_hue = float(jp_bg.split()[-1].rstrip(")"))
        self.assertGreater(sc_hue, 180, "scandinavian bg should be cool-hued")
        self.assertLess(jp_hue, 120, "japandi bg should be warm-hued")


class ExtractionMap(unittest.TestCase):
    # aggregates the map documents rather than maps 1:1 (see file header note)
    DOCUMENTED_GAPS = {"color.roles", "type.baseSize", "brand.overrides.$note"}

    @staticmethod
    def _leaves(tree, prefix=""):
        out = []
        for k, v in tree.items():
            kk = f"{prefix}{k}"
            if isinstance(v, dict) and v:
                out.extend(ExtractionMap._leaves(v, kk + "."))
            else:
                out.append(kk)
        return out

    def test_bindings_legal_and_snap_rules_present(self):
        for key, spec in EMAP["extractionMap"].items():
            self.assertIn(spec["binding"], ("snap", "literal"), key)
            if spec["binding"] == "snap":
                self.assertTrue(spec.get("snapRule"), f"{key} snap without snapRule")

    def test_covers_token_schema_leaves(self):
        leaves = set(self._leaves(TOKEN_SCHEMA["style"]))
        leaves |= {"brand." + k for k in self._leaves(TOKEN_SCHEMA["brand"])}
        mapped = set(EMAP["extractionMap"])

        def covered(leaf: str) -> bool:
            parts = leaf.split(".")
            return any(".".join(parts[:i]) in mapped for i in range(1, len(parts) + 1))

        missing = {l for l in leaves if not covered(l)} - self.DOCUMENTED_GAPS
        self.assertFalse(missing, f"unmapped token-schema leaves: {sorted(missing)}")

    def test_confidence_policy(self):
        pol = EMAP["confidencePolicy"]
        self.assertTrue(pol.get("noisyKeys"))
        self.assertIn("flag for human confirmation", pol["belowThresholdAction"])

    def test_identity_keys_stay_literal(self):
        for key in ("color.accent", "color.bg", "type.pair", "brand.font.display", "brand.logo"):
            self.assertEqual(EMAP["extractionMap"][key]["binding"], "literal", key)


if __name__ == "__main__":
    unittest.main()
