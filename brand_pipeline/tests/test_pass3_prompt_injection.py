#!/usr/bin/env python3
"""Pass-3 stage-2 tests — the prompt injection in generate_composition.build_prompt
(checkpoint C).

Pass 2 proved pass-1 facts POLICED generation but never SHAPED it (build_prompt
byte-identical with/without them). Stage 2 closes that gap; these tests pin the
wiring:

  - the PASS-1 FACTS block ([[PASS3-FACTS:BEGIN/END]]) is present for a brand
    carrying pass-1 artifacts, with the REAL fact strings (scale rungs,
    signature claims, voice budgets) inside;
  - byte-stability: fixed inputs → identical prompt bytes;
  - GRACEFUL DEGRADATION: a brand with NO pass-1 artifacts gets NO block and a
    prompt byte-identical to the pre-pass-3 assembly (proven structurally: the
    with-artifacts prompt minus the injected block equals the without-artifacts
    prompt for an otherwise-identical brand);
  - the STYLE DIRECTIVE block ([[PASS3-STYLE:BEGIN/END]]) injects only when the
    caller passes one (absent → byte-identical), mirroring hero_candidates;
  - injection is prompt-shaping only: no renderer/gate module imports
    style_resolver (fence proof, grep-level).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

import generate_composition as gc  # noqa: E402
import style_resolver as sr        # noqa: E402

REPO = _BRAND_PIPELINE.parent
HUBSPOT = REPO / "runs" / "hubspot-v2" / "brand" / "brand.yaml"
REMOTE = REPO / "runs" / "remote" / "brand" / "brand.yaml"


def _prompt(brand_yaml: Path, **kw) -> str:
    doc = gc.load_brand(brand_yaml)
    seeds = gc.seed_patterns(doc, brand_yaml)
    return gc.build_prompt("Brief.", brand_yaml, "corporate-saas-clean", seeds, **kw)


class FactsBlockPresence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prompt = _prompt(HUBSPOT)

    def test_sentinels_present_exactly_once(self):
        self.assertEqual(self.prompt.count(gc.PASS3_FACTS_BEGIN), 1)
        self.assertEqual(self.prompt.count(gc.PASS3_FACTS_END), 1)

    def test_derived_scale_rungs_injected_as_geometry_vocabulary(self):
        block = self._block()
        self.assertIn("Derived scale rungs — the ALLOWED geometry vocabulary", block)
        # real numbers from runs/hubspot-v2/brand/style-scale.yaml
        self.assertIn("base 16px · ratio 1.125", block)
        self.assertIn("section rhythm(px): 24, 40, 64, 96", block)
        self.assertIn("radius modes: 4px(small) · 8px(button,card) · 16px(panel)", block)
        self.assertIn("motion band: 150–500ms", block)
        self.assertIn("scale_adherence", block)

    def test_signatures_injected_as_always_never_constraints(self):
        block = self._block()
        self.assertIn("[never] action-orange-scope (accent-scope)", block)
        self.assertIn("[always] serif-display-sans-body (type-treatment)", block)
        self.assertIn("[always] rounded-8-controls (shape-motif)", block)
        self.assertIn("[never] deep-teal-dark-family (surface-habit)", block)

    def test_voice_facts_injected_as_copy_constraints(self):
        block = self._block()
        self.assertIn("mean ≤14w, p90 ≤23w", block)
        self.assertIn("exclamation marks: max 0", block)
        self.assertIn("headings: sentence case", block)
        self.assertIn("banned words", block)
        self.assertIn("leverage, synergy", block)

    def test_block_sits_inside_the_system_prompt_before_the_palette(self):
        i = self.prompt.index(gc.PASS3_FACTS_END)
        self.assertLess(self.prompt.index("## Brand facts"),
                        self.prompt.index(gc.PASS3_FACTS_BEGIN))
        self.assertLess(i, self.prompt.index("## Primitive palette"))

    def test_remote_brand_gets_its_own_facts(self):
        p = _prompt(REMOTE)
        self.assertIn(gc.PASS3_FACTS_BEGIN, p)
        self.assertIn("[always] pill-controls (shape-motif)", p)
        self.assertIn("[never] action-blue-scope (accent-scope)", p)

    def _block(self) -> str:
        i = self.prompt.index(gc.PASS3_FACTS_BEGIN)
        j = self.prompt.index(gc.PASS3_FACTS_END)
        return self.prompt[i:j]


class ByteStability(unittest.TestCase):
    def test_fixed_inputs_fixed_bytes(self):
        self.assertEqual(_prompt(HUBSPOT), _prompt(HUBSPOT))

    def test_facts_block_itself_is_stable(self):
        doc = gc.load_brand(HUBSPOT)
        a = gc.pass1_facts_block(doc, HUBSPOT.parent)
        b = gc.pass1_facts_block(doc, HUBSPOT.parent)
        self.assertEqual(a, b)
        self.assertTrue(a.startswith(gc.PASS3_FACTS_BEGIN))
        self.assertTrue(a.endswith(gc.PASS3_FACTS_END))


class GracefulDegradation(unittest.TestCase):
    """A brand WITHOUT pass-1 artifacts must keep the prompt unchanged from the
    pre-pass-3 assembly. Proven structurally: strip the injected block from an
    artifacts-present prompt and you get EXACTLY the artifacts-absent prompt of
    an otherwise-identical brand dir."""

    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.mkdtemp(prefix="pass3-degrade-")
        src = HUBSPOT.parent
        cls.with_dir = Path(cls.td) / "with-artifacts"
        cls.without_dir = Path(cls.td) / "without-artifacts"
        for dst in (cls.with_dir, cls.without_dir):
            dst.mkdir(parents=True)
            shutil.copy(src / "brand.yaml", dst / "brand.yaml")
            if (src / "layout-library.yaml").exists():
                shutil.copy(src / "layout-library.yaml", dst / "layout-library.yaml")
        # artifacts only in the WITH dir
        shutil.copy(src / "style-scale.yaml", cls.with_dir / "style-scale.yaml")
        shutil.copy(src / "voice-facts.yaml", cls.with_dir / "voice-facts.yaml")
        # the WITHOUT brand must also carry no signatures block (brand.yaml-owned)
        doc = (cls.without_dir / "brand.yaml").read_text()
        doc = doc.replace("\nsignatures:\n", "\n_retired_signatures:\n", 1)
        (cls.without_dir / "brand.yaml").write_text(doc)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.td, ignore_errors=True)

    def test_artifactless_brand_has_no_sentinel(self):
        p = _prompt(self.without_dir / "brand.yaml")
        self.assertNotIn(gc.PASS3_FACTS_BEGIN, p)
        self.assertNotIn(gc.PASS3_FACTS_END, p)

    def test_injection_is_purely_additive(self):
        p_with = _prompt(self.with_dir / "brand.yaml")
        p_without = _prompt(self.without_dir / "brand.yaml")
        i = p_with.index(gc.PASS3_FACTS_BEGIN)
        j = p_with.index(gc.PASS3_FACTS_END) + len(gc.PASS3_FACTS_END)
        block = p_with[i:j]
        # the block occupies the template slot as "\n{block}\n" — an empty slot
        # renders as "" — so removing "\n{block}\n" wholesale must reproduce the
        # artifacts-absent assembly EXACTLY (modulo the brand-dir path in
        # brand.ref, a fixture-name artifact)
        stripped = p_with.replace("\n" + block + "\n", "", 1)
        p_without_norm = p_without.replace(str(self.without_dir), str(self.with_dir))
        self.assertEqual(stripped, p_without_norm)

    def test_partial_artifacts_still_inject_partially(self):
        """signatures alone (no scale/voice files) still produce a block — the
        gating is per artifact, never all-or-nothing."""
        doc = gc.load_brand(self.without_dir / "brand.yaml")
        doc["signatures"] = [{"id": "test-sig", "kind": "shape-motif",
                              "mode": "always", "claim": "test claim"}]
        block = gc.pass1_facts_block(doc, self.without_dir)
        self.assertIn("[always] test-sig", block)
        self.assertNotIn("Derived scale rungs", block)
        self.assertNotIn("Voice constraints", block)


class StyleDirectiveInjection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = sr.load_library()
        cls.bundle = sr.load_brand_bundle(HUBSPOT.parent)
        res = sr.resolve_all("swiss", cls.lib, cls.bundle,
                             ["hero", "feature-trio", "cta-band"])
        cls.block = sr.render_style_directive_block("swiss", res, cls.lib)

    def test_absent_style_directives_keep_prompt_byte_identical(self):
        base = _prompt(HUBSPOT)
        again = _prompt(HUBSPOT, style_directives=None)
        self.assertEqual(base, again)
        self.assertNotIn(sr.STYLE_BLOCK_BEGIN, base)

    def test_present_style_directives_inject_delimited(self):
        p = _prompt(HUBSPOT, style_directives=self.block)
        self.assertEqual(p.count(sr.STYLE_BLOCK_BEGIN), 1)
        self.assertEqual(p.count(sr.STYLE_BLOCK_END), 1)
        self.assertIn("STYLE DIRECTIVE — Swiss / International", p)
        # rides in the system prompt, after the seeds, before the user brief
        self.assertLess(p.index("## SEED constraints"), p.index(sr.STYLE_BLOCK_BEGIN))
        self.assertLess(p.index(sr.STYLE_BLOCK_BEGIN), p.index("# USER — brief"))

    def test_style_injection_is_purely_additive(self):
        base = _prompt(HUBSPOT)
        p = _prompt(HUBSPOT, style_directives=self.block)
        # injected as system += "\n" + block.strip() + "\n" — removing exactly
        # that span must reproduce the base assembly byte-for-byte
        injected = "\n" + self.block.strip() + "\n"
        self.assertIn(injected, p)
        self.assertEqual(p.replace(injected, "", 1), base)


class FenceProof(unittest.TestCase):
    """Injection is prompt-shaping ONLY: deterministic physics stays in renderers
    and gates. Grep-level pins (the same style as ReplicaNeverLoadsScaleTest)."""

    RENDER_AND_GATE_MODULES = (
        "compose_section.py", "compose_page.py", "compose_from_composition.py",
        "compose_replica.py", "component_render.py", "onbrand_check.py",
        "spacing_audit.py", "signature_audit.py", "voice_audit.py",
    )

    def test_no_renderer_or_gate_imports_the_resolver(self):
        for name in self.RENDER_AND_GATE_MODULES:
            src = (_BRAND_PIPELINE / name).read_text()
            self.assertNotIn("style_resolver", src,
                             f"{name} must not consume the style resolver")

    def test_replica_never_sees_the_facts_block(self):
        src = (_BRAND_PIPELINE / "compose_replica.py").read_text()
        self.assertNotIn("PASS3", src)
        self.assertNotIn("pass1_facts_block", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
