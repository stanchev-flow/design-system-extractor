#!/usr/bin/env python3
"""AS-78 round-control glyph-centering gate (fix4 2026-07).

The `→`/chevron inside a round/circle control must be flex-centered, and the AS-78
circle-integrity audit must ENFORCE it (extended to cover the structural composed-page
round chrome — edge-cut / panel-carousel paddles + pause, the circle-arrow go
affordance — which was previously un-audited). This is an analyzer-only change: no
rendered bytes move, so the v2/remote/v3 replicas stay byte-identical.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_fix_round_glyph
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
_AUDIT = _BRAND_PIPELINE / "slop_audit.mjs"

_CENTERED = """<!doctype html><html><body>
<div id="sec-0">
  <button class="cs-edgecut-arrow" style="width:48px;height:48px;border-radius:999px;
      display:flex;align-items:center;justify-content:center;padding:0;border:0">
    <svg width="8" height="12" viewBox="0 0 8 12" aria-hidden="true"><path d="M1 1l5 5-5 5"/></svg>
  </button>
</div></body></html>"""

# same control, but the glyph is shoved to the right (a non-centered line box / padding)
_OFF_CENTER = """<!doctype html><html><body>
<div id="sec-0">
  <button class="cs-edgecut-arrow" style="width:48px;height:48px;border-radius:999px;
      display:flex;align-items:center;justify-content:flex-start;padding:0;border:0">
    <svg width="8" height="12" viewBox="0 0 8 12" aria-hidden="true"><path d="M1 1l5 5-5 5"/></svg>
  </button>
</div></body></html>"""


class Static(unittest.TestCase):
    def test_as78_covers_structural_round_controls_and_centering(self):
        audit = _AUDIT.read_text()
        for token in (".cs-edgecut-arrow", ".cs-panelcar-arrow", ".cs-edgecut-pause",
                      ".c-acc-go", "off the round control center", "must be flex-centered"):
            self.assertIn(token, audit, token)


class Functional(unittest.TestCase):
    """Runs the real node audit on planted fixtures (skipped when node is absent)."""

    def _run(self, html: str) -> str:
        if shutil.which("node") is None or not _AUDIT.is_file():
            self.skipTest("node / slop_audit.mjs not available")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "index.html"
            p.write_text(html)
            res = subprocess.run(["node", str(_AUDIT), str(p)],
                                 capture_output=True, text=True, timeout=120)
            return res.stdout + res.stderr

    def test_off_center_glyph_is_flagged(self):
        self.assertIn("off the round control center", self._run(_OFF_CENTER))

    def test_centered_glyph_passes(self):
        self.assertNotIn("off the round control center", self._run(_CENTERED))


if __name__ == "__main__":
    unittest.main()
