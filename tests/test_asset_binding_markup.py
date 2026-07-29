"""An asset binding never reaches markup as a Python repr.

A binding arrives at the renderers in three shapes: a bare filename, an
already-resolved path or URL, and the ``{"src": …, "alt": …}`` mapping that
``compose_from_composition._sanitize_assets`` coerces bare strings into. The
mapping shape can therefore appear at any consumer downstream of sanitization,
and every consumer that formatted it straight into an attribute produced

    src="assets/{'src': 'assets/x.webp'}"

which 404s. `runs/hubspot/brand/compose/signup-launch-tokenized/index.html` still
carries three of them.

These tests lock the two halves of the fix: ``component_render.asset_binding`` is
the one reader of the three shapes, and no composer may re-derive the strings
inline. The composer cases below each reproduced the malformation before the fix.
"""

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "brand_pipeline"))

import component_render as cr  # noqa: E402
import compose_section as cs  # noqa: E402

# a src attribute is malformed when it carries a Python container's punctuation
_REPR_IN_ATTR = re.compile(r"""(?:src|href)="[^"]*(?:\{|&#x7b;|&#x27;|%7B)""", re.I)
_SRC_ATTR = re.compile(r'src="([^"]*)"')

# the sanitizer's mapping shape, and the same binding as a bare filename
RECORD = {"src": "assets/photo.webp", "alt": "Measured alt"}
BARE = "photo.webp"


def _doc():
    return {"brand": {"name": "Acme"}, cs.ASSET_INVENTORY_KEY: ["photo.webp"]}


def _ctx():
    return cr.ComponentContext("surface/primary", False)


def _assert_clean(case: unittest.TestCase, html: str) -> list[str]:
    """No attribute in `html` carries a container repr; return the srcs it emitted."""
    leaked = _REPR_IN_ATTR.findall(html)
    case.assertEqual([], leaked, f"container repr reached an attribute: {leaked}")
    return _SRC_ATTR.findall(html)


class AssetBindingTests(unittest.TestCase):
    def test_reads_all_three_binding_shapes(self) -> None:
        self.assertEqual(("assets/photo.webp", None), cr.asset_binding(BARE))
        self.assertEqual(("assets/photo.webp", None), cr.asset_binding("assets/photo.webp"))
        self.assertEqual(("assets/photo.webp", "Measured alt"), cr.asset_binding(RECORD))

    def test_a_resolved_src_is_never_re_prefixed(self) -> None:
        for src in ("assets/x.webp", "https://cdn.example/x.webp",
                    "http://cdn.example/x.webp", "data:image/png;base64,AAA",
                    "//cdn.example/x.webp", "/x.webp"):
            self.assertEqual(src, cr.asset_src(src), src)
            self.assertEqual(src, cr.asset_src({"src": src}), src)

    def test_an_absent_binding_resolves_to_none(self) -> None:
        for empty in (None, "", "   ", {}, {"src": None}, {"src": ""}):
            self.assertIsNone(cr.asset_src(empty), repr(empty))

    def test_a_container_never_survives_as_a_src_string(self) -> None:
        for shape in (RECORD, {"asset": {"src": "assets/photo.webp"}}, {"uri": BARE}):
            src = cr.asset_src(shape)
            self.assertIsNotNone(src, repr(shape))
            self.assertNotIn("{", src, repr(shape))
            self.assertNotIn("'", src, repr(shape))

    def test_esc_refuses_a_container_instead_of_writing_its_repr(self) -> None:
        with self.assertRaises(TypeError):
            cr.esc(RECORD)


class RenderImageTests(unittest.TestCase):
    """The primitive is the last line of defence: every composer funnels through it."""

    def test_a_mapping_src_resolves_to_the_path_and_its_alt(self) -> None:
        html = cr.render_image(_doc(), _ctx(), {"src": RECORD})
        self.assertEqual(["assets/photo.webp"], _assert_clean(self, html))
        self.assertIn('alt="Measured alt"', html)

    def test_an_explicit_alt_still_wins_over_the_binding(self) -> None:
        html = cr.render_image(_doc(), _ctx(), {"src": RECORD, "alt": "Authored"})
        self.assertIn('alt="Authored"', html)

    def test_a_mapping_mask_resolves_instead_of_writing_its_repr(self) -> None:
        html = cr.render_image(_doc(), _ctx(),
                               {"src": "assets/photo.webp", "mask": {"src": "shape.svg"}})
        style = html.split('style="')[1].split('"')[0]
        self.assertIn("mask-image: url(&#x27;assets/shape.svg&#x27;)", style)
        self.assertNotIn("{", style)


class ComposerBindingTests(unittest.TestCase):
    """Each composer here emitted `src="assets/{'src': …}"` before the fix."""

    def setUp(self) -> None:
        self._saved = dict(cs.LAYOUT_COPY)
        cs.LAYOUT_COPY.clear()

    def tearDown(self) -> None:
        cs.LAYOUT_COPY.clear()
        cs.LAYOUT_COPY.update(self._saved)

    def _render(self, fn: str, copy: dict) -> str:
        cs.LAYOUT_COPY["probe"] = copy
        return getattr(cs, fn)(_doc(), {"id": "probe"}, _ctx(), {}, {})

    def test_media_split_resolves_a_mapping_asset(self) -> None:
        html = self._render("compose_media_split",
                            {"asset": RECORD, "caption": "Cap", "statement": "Stmt"})
        self.assertEqual(["assets/photo.webp"], _assert_clean(self, html))

    def test_editorial_interlock_resolves_a_mapping_asset(self) -> None:
        html = self._render("compose_editorial_interlock",
                            {"asset": RECORD, "caption": "Cap", "statement": "Stmt"})
        self.assertEqual(["assets/photo.webp"], _assert_clean(self, html))

    def test_feature_cards_resolve_a_mapping_asset_beside_a_bare_one(self) -> None:
        html = self._render("compose_features_cards", {
            "heading": "H",
            "cards": [{"caption": "One", "asset": RECORD, "body": "b"},
                      {"caption": "Two", "asset": BARE, "body": "b"}],
        })
        self.assertEqual(["assets/photo.webp", "assets/photo.webp"],
                         _assert_clean(self, html))

    def test_a_card_avatar_resolves_from_a_mapping_too(self) -> None:
        html = self._render("compose_features_cards", {
            "heading": "H",
            "cards": [{"caption": "One", "body": "b", "name": "A Person",
                       "avatar": {"src": "photo.webp"}}],
        })
        self.assertIn("assets/photo.webp", _assert_clean(self, html))

    def test_the_bound_alt_reaches_the_image_when_none_is_authored(self) -> None:
        html = self._render("compose_media_split",
                            {"asset": RECORD, "caption": "Cap", "statement": "Stmt"})
        self.assertIn('alt="Measured alt"', html)


class SanitizerHandoffTests(unittest.TestCase):
    """The producer of the mapping shape, and the translator that consumes it."""

    def test_the_sanitizer_coerces_a_bare_card_asset_into_the_mapping(self) -> None:
        import compose_from_composition as cfc

        comp = {"sections": [{
            "id": "features", "archetype": "cards",
            "slots": [{"name": "cards", "contract": "feature-item",
                       "copy": [{"heading": "One", "asset": BARE}]}],
        }]}
        with _brand_dir_holding(BARE) as brand_dir:
            out = cfc._sanitize_assets(comp, brand_dir)
        item = out["sections"][0]["slots"][0]["copy"][0]
        self.assertEqual({"src": "assets/photo.webp"}, item["asset"])

    def test_the_cards_translator_hands_the_composer_a_string(self) -> None:
        import compose_from_composition as cfc

        section = {"id": "features", "archetype": "cards", "slots": [
            {"name": "cards", "contract": "feature-item",
             "copy": [{"heading": "One", "asset": dict(RECORD)}]}]}
        card = cfc._cards_copy(section)["cards"][0]
        self.assertEqual("assets/photo.webp", card["asset"])
        self.assertEqual("Measured alt", card["alt"])


class _brand_dir_holding:
    """A throwaway brand dir whose `assets/` really holds the named files, so the
    sanitizer's disk-evidence check has something to find."""

    def __init__(self, *names: str) -> None:
        self._names = names

    def __enter__(self) -> Path:
        from tempfile import TemporaryDirectory

        self._tmp = TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "assets").mkdir()
        for name in self._names:
            (root / "assets" / name).write_bytes(b"\x00")
        return root

    def __exit__(self, *exc) -> None:
        self._tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
