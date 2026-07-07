#!/usr/bin/env python3
"""Contamination guard: NO brand's DNA may live in shared code paths (AS-38).

WoodWave was the bootstrap brand, and its copy/nav/assets/colors leaked into the
shared composers, prompts, and specs — every other brand's generations inherited
"About / Gallery / Exhibition / Visit", "Buy Tickets", Melodrama, the gold #edd580,
and the rest. This test hardcodes the WoodWave corpus (test fixtures MAY name the
brand — that is their job) and asserts the shared surface is clean two ways:

  Scan A (static): AST-parse the shared pipeline modules and flag any NON-docstring
      string literal carrying a corpus term (docstrings/comments are historical
      documentation and never reach output; emitted CSS/prompt blocks ARE literals
      and must be clean). styles/*.md and brand_pipeline/contracts/**/*.yaml are
      scanned as full text (they are shipped/prompt-assembled verbatim).
  Scan B (functional): compose a full page for a minimal synthetic brand (complete
      tokens, NO navbar/footer extracted, one stub layout) and assert the HTML
      carries no corpus term — and that the nav degrades to a wordmark-only bar
      instead of borrowing another brand's links/CTA.

Run:  ./venv/bin/python -m unittest brand_pipeline.tests.test_no_cross_brand_dna
"""
from __future__ import annotations

import ast
import copy
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

_BRAND_PIPELINE = Path(__file__).resolve().parent.parent
_REPO = _BRAND_PIPELINE.parent
if str(_BRAND_PIPELINE) not in sys.path:
    sys.path.insert(0, str(_BRAND_PIPELINE))

from tests.test_tokens_css import FIXTURE  # noqa: E402

# ── the WoodWave corpus (substring, case-insensitive) ─────────────────────────────
CORPUS = [
    "woodwave",
    "buy tickets",
    "est. 2019",
    "portland",
    "elin marsh",
    "timber hall",
    "harbour",
    "melodrama",
    "hero-staircase",
    "overlap-vase",
    "about-img-",
    "web-gallery-",
    "map.jpg",
    "#edd580",
    "#faf0e8",
    "#181313",
    "#1b150f",
    "#f7efe6",
    "#1f1a14",
]

# WoodWave's nav label set — flagged only when the four labels appear TOGETHER as one
# list literal (the individual words are far too generic to scan for alone).
NAV_LIST = ["about", "gallery", "exhibition", "visit"]

# Shared pipeline modules whose STRING LITERALS must be corpus-free (Scan A).
SHARED_MODULES = [
    "compose_section.py",
    "compose_page.py",
    "compose_from_composition.py",
    "component_render.py",
    "render_components_preview.py",
    "wildcard_generator.py",
    "generate_composition.py",
    "export_kit.py",
]


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """ids of the Constant nodes that are docstrings (module/class/function heads)."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and \
                    isinstance(body[0].value, ast.Constant) and \
                    isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def _literal_hits(py_path: Path) -> list[str]:
    """Corpus hits in the file's non-docstring string literals: ['line N: term'…]."""
    tree = ast.parse(py_path.read_text())
    doc_nodes = _docstring_nodes(tree)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in doc_nodes:
            low = node.value.lower()
            for term in CORPUS:
                if term in low:
                    hits.append(f"line {node.lineno}: {term!r} in literal "
                                f"{node.value[:60]!r}")
        if isinstance(node, ast.List):
            values = [e.value.lower() for e in node.elts
                      if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if len(values) >= len(NAV_LIST):
                for i in range(len(values) - len(NAV_LIST) + 1):
                    if values[i:i + len(NAV_LIST)] == NAV_LIST:
                        hits.append(f"line {node.lineno}: WoodWave nav label list")
                        break
    return hits


def _text_hits(path: Path) -> list[str]:
    hits = []
    low = path.read_text().lower()
    for term in CORPUS:
        if term in low:
            hits.append(term)
    return hits


class StaticScan(unittest.TestCase):
    """Scan A — shared code/spec surfaces carry no WoodWave literal."""

    def test_shared_module_string_literals_clean(self):
        failures = []
        for name in SHARED_MODULES:
            p = _BRAND_PIPELINE / name
            for hit in _literal_hits(p):
                failures.append(f"{name}: {hit}")
        self.assertFalse(failures, "WoodWave DNA in shared string literals:\n  "
                         + "\n  ".join(failures))

    def test_styles_md_clean(self):
        failures = []
        for f in sorted((_REPO / "styles").glob("*.md")):
            for term in _text_hits(f):
                failures.append(f"styles/{f.name}: {term!r}")
        self.assertFalse(failures, "WoodWave DNA in styles/*.md:\n  "
                         + "\n  ".join(failures))

    def test_contracts_yaml_clean(self):
        failures = []
        for f in sorted((_BRAND_PIPELINE / "contracts").rglob("*.yaml")):
            for term in _text_hits(f):
                failures.append(f"contracts/{f.relative_to(_BRAND_PIPELINE / 'contracts')}: "
                                f"{term!r}")
        self.assertFalse(failures, "WoodWave DNA in contracts YAMLs:\n  "
                         + "\n  ".join(failures))


def _synthetic_brand() -> dict:
    """A complete-token brand with NO extracted navbar/footer and one stub layout —
    the partially-extracted state every fallback must degrade honestly for."""
    doc = copy.deepcopy(FIXTURE)
    doc.pop("navbar", None)
    doc.pop("footer", None)
    doc["layouts"] = [{
        "id": "landing-hero",
        "archetype": "stack",
        "surfaceIntent": "surface/inverse",
        "blockMapping": [
            {"slot": "main", "role": "display title", "contract": "heading",
             "usage": {"Text": "Everything in view", "level": "display"}},
        ],
    }]
    return doc


class FunctionalRender(unittest.TestCase):
    """Scan B — a synthetic brand's composed page carries no corpus term and its nav
    degrades to a wordmark-only bar."""

    @classmethod
    def setUpClass(cls):
        import compose_page as cp
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        brand_yaml = tmp / "brand.yaml"
        brand_yaml.write_text(yaml.safe_dump(_synthetic_brand(), sort_keys=False,
                                             allow_unicode=True))
        doc = cp.load_doc(brand_yaml)
        from styles import inactive_context
        cls.html = cp.build_page(doc, brand_yaml, ["landing-hero"], inactive_context())

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_no_corpus_term_in_html(self):
        low = self.html.lower()
        hits = [t for t in CORPUS if t in low]
        self.assertFalse(hits, f"WoodWave DNA in synthetic brand's page: {hits}")

    def test_nav_is_wordmark_only(self):
        low = self.html.lower()
        self.assertIn("ravine", low)  # the brand's OWN wordmark renders
        for label in ("#about", ">about<", ">gallery<", ">exhibition<", ">visit<"):
            self.assertNotIn(label, low,
                             f"borrowed nav label {label!r} on a navbar-less brand")


if __name__ == "__main__":
    unittest.main()
