#!/usr/bin/env python3
"""MEDIA SEMANTICS SYSTEM (media-assets.v1 — spec/media-assets-schema.md):

- registry loading is FACT-GATED (absent/foreign schema → None; every consumer
  byte-identical without the artifact);
- assetRef resolution (canonical variant), variant file index, per-asset
  treatmentDefaults consumption in asset_render_mode (falls back to tagged facts);
- mediaComposition normalization onto EXISTING channels: masked-media clip,
  state-swap → per-item media (the generalized accordion swap), layered/
  background/cluster → layered-media slots (componentRef layers ride the
  overlay machinery as contract slots), tiled-grid/marquee/facepile → item folds;
- the composed-lane lints: media-binding (no silent drops, refs resolve,
  placeholder recipes licensed) + AS-67 mark-legality (third-party marks in
  factual proof contexts only; badges never fabricated);
- the NO-MATCH LADDER's declared-gap rung → the ASSET-REQUEST MANIFEST
  (asset-requests.json emission + stale-file removal);
- validator checks C26 (artifact shape + poster-frame discipline), C27
  (reference integrity incl. orphan bound assets), C28 (variant dedupe sanity)
  on pass/fail fixtures — including the mesh-gradient re-instantiation recipe;
- prompt injection: [[MEDIA-FACTS]] block present for artifact brands, absent
  (byte-identically) otherwise;
- render_image masked-media style is declared-only (mask-less markup unchanged).
"""
from __future__ import annotations

import copy
import json
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "brand_pipeline"))
sys.path.insert(0, str(REPO / "tools" / "extract"))

import component_render as cr  # noqa: E402
import media_semantics as ms  # noqa: E402
from validate_brand_evidence import Report, _check_media_assets  # noqa: E402


def _png_bytes(w: int = 4, h: int = 4, rgb=(200, 60, 40)) -> bytes:
    """A tiny valid PNG (no Pillow needed to WRITE fixtures)."""
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def _entry(aid, fname, kind="photograph", rights="own", **over):
    e = {
        "id": aid, "file": fname,
        "assetSemantics": {"kind": kind, "subject": "generic subject"},
        "facts": {"intrinsic": {"w": 40, "h": 30}, "intrinsicAspect": 1.3333,
                  "orientation": "landscape", "alpha": False,
                  "stats": {"dominantHue": 20, "luminanceBand": "mid",
                            "busyness": "low", "saturationBand": "muted",
                            "source": "measured"},
                  "focalPoint": None, "safeCrop": None, "altHarvested": None},
        "usageRights": rights,
        "treatmentDefaults": None,
        "compositionRoles": [],
        "provenance": {"source": "capture-files", "sections": ["hero"],
                       "confidence": "high"},
    }
    e.update(over)
    return e


class Fixture(unittest.TestCase):
    """A tmp brand dir with a valid media-assets.yaml + files on disk."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="media-sem-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.assets = self.tmp / "assets"
        self.assets.mkdir(parents=True)
        for i, name in enumerate(("photo-a.png", "photo-a-2x.png", "mark-client.png",
                                  "shape-blob.png", "badge-award.png", "ui-shot-a.png",
                                  "ui-shot-b.png", "face-1.png", "face-2.png",
                                  "poster-x.png")):
            # per-file distinct bytes — byte-identity is C28's DELIBERATE fixture only
            (self.assets / name).write_bytes(_png_bytes(rgb=(10 + i * 17, 90, 40)))
        self.registry = {
            "schemaVersion": "media-assets.v1",
            "brand": "Fixture",
            "assets": [
                _entry("hero-photo", "photo-a.png",
                       # canonical = highest-res: the sibling is the DOWNSCALE
                       variants=[{"file": "photo-a-2x.png", "relation": "srcset",
                                  "scale": 0.5, "note": "half-res srcset sibling",
                                  "w": 20, "h": 15}],
                       treatmentDefaults={"fit": "cover", "salience": "content"}),
                _entry("client-mark", "mark-client.png", kind="logo-third-party",
                       rights="third-party-mark",
                       assetSemantics={"kind": "logo-third-party", "subtype": "client",
                                       "subject": "customer mark"}),
                _entry("accent-blob", "shape-blob.png", kind="accent-shape"),
                _entry("award-mark", "badge-award.png", kind="badge-review-award",
                       rights="third-party-mark"),
                _entry("ui-shot-a", "ui-shot-a.png", kind="product-ui-screenshot",
                       treatmentDefaults={"fit": "contain", "salience": "content"}),
                _entry("ui-shot-b", "ui-shot-b.png", kind="product-ui-screenshot"),
                _entry("face-one", "face-1.png", kind="avatar"),
                _entry("face-two", "face-2.png", kind="avatar"),
            ],
            "generatedVisuals": [
                {"id": "soft-wash", "kind": "css-gradient",
                 "recipe": {"shape": "linear", "angle": 90,
                            "stops": ["accent/warm 0%", "accent/cool 100%"],
                            "tokenRoles": ["accent/warm", "accent/cool"]},
                 "poster": None,
                 "posterNote": "declarative stops reproduce the wash deterministically",
                 "degrade": ["live", "poster", "omit"],
                 "provenance": {"source": "capture-files", "sections": ["hero"],
                                "confidence": "high"}},
                # MESH-GRADIENT RE-INSTANTIATION recipe: blob count + per-blob hue
                # ROLE from the brand palette + geometry + blur — never a bitmap.
                {"id": "mesh-drift", "kind": "mesh-gradient-blobs",
                 "recipe": {"blobs": [
                     {"hueRole": "accent/warm", "sizeFrac": 0.5,
                      "position": {"x": 0.2, "y": 0.3}, "blurPx": 80},
                     {"hueRole": "accent/cool", "sizeFrac": 0.4,
                      "position": {"x": 0.8, "y": 0.7}, "blurPx": 60}],
                     "blendMode": "screen", "animation": {"drift": "slow"}},
                 "poster": "poster-x.png",
                 "degrade": ["live", "poster", "omit"],
                 "provenance": {"source": "capture-files", "sections": ["hero"],
                                "confidence": "medium"}},
            ],
        }
        (self.tmp / "media-assets.yaml").write_text(
            yaml.safe_dump(self.registry, sort_keys=False))

    def load(self):
        return ms.load_media_assets(self.tmp)


# ── loading + indexes ────────────────────────────────────────────────────────────────

class LoadingFactGate(Fixture):
    def test_absent_dir_loads_none(self):
        self.assertIsNone(ms.load_media_assets(self.tmp / "nope"))
        self.assertIsNone(ms.load_media_assets(None))

    def test_foreign_schema_loads_none(self):
        (self.tmp / "media-assets.yaml").write_text("schemaVersion: something-else.v9")
        self.assertIsNone(self.load())

    def test_valid_registry_loads(self):
        reg = self.load()
        self.assertEqual(reg["schemaVersion"], "media-assets.v1")
        self.assertEqual(len(ms.asset_entries(reg)), 8)

    def test_resolve_ref_returns_canonical_variant(self):
        reg = self.load()
        self.assertEqual(ms.resolve_ref(reg, "hero-photo"), "photo-a.png")
        self.assertIsNone(ms.resolve_ref(reg, "not-an-id"))

    def test_file_index_covers_variants(self):
        idx = ms.file_index(self.load())
        self.assertIn("photo-a.png", idx)
        self.assertIn("photo-a-2x.png", idx)          # variant file → same entry
        self.assertEqual(idx["photo-a-2x.png"]["id"], "hero-photo")

    def test_fit_map_only_explicit_fits(self):
        fits = ms.fit_map(self.load())
        self.assertEqual(fits["photo-a.png"], "cover")
        self.assertEqual(fits["photo-a-2x.png"], "cover")   # variant inherits
        self.assertEqual(fits["ui-shot-a.png"], "contain")
        self.assertNotIn("mark-client.png", fits)           # no default → absent

    def test_aspect_classes(self):
        def cls(ratio):
            return ms.aspect_class({"facts": {"intrinsicAspect": ratio}})
        self.assertEqual(cls(3.0), "pano")
        self.assertEqual(cls(2.0), "wide")
        self.assertEqual(cls(1.5), "landscape")
        self.assertEqual(cls(1.0), "square")
        self.assertEqual(cls(0.7), "portrait")
        self.assertEqual(ms.aspect_class({"facts": {}}), "freeform")


# ── renderer consumption (treatmentDefaults + masked-media) ──────────────────────────

class RendererConsumption(Fixture):
    def test_asset_render_mode_prefers_media_assets_fit(self):
        doc = {"_mediaAssetsFit": ms.fit_map(self.load()),
               "_assetTags": {"ui-shot-a.png": {"assetKind": "product-graphic"}},
               "_mediaTreatmentRules": [{"assetKind": "product-graphic",
                                         "role": "*", "fit": "cover"}]}
        # registry says contain; the tagged rule would say cover — registry wins
        self.assertEqual(cr.asset_render_mode(doc, "ui-shot-a.png"), "contain")

    def test_asset_render_mode_falls_back_to_tagged_facts(self):
        doc = {"_mediaAssetsFit": ms.fit_map(self.load()),
               "_assetTags": {"other.png": {"assetKind": "product-graphic"}},
               "_mediaTreatmentRules": [{"assetKind": "product-graphic",
                                         "role": "*", "fit": "contain"}]}
        self.assertEqual(cr.asset_render_mode(doc, "other.png"), "contain")
        self.assertEqual(cr.asset_render_mode({}, "unknown.png"), "cover")

    def test_render_image_mask_is_declared_only(self):
        ctx = cr.make_context({}, {}, {})
        plain = cr.render_image({}, ctx, {
            "src": "assets/x.png", "alt": "x", "aspect": "1 / 1"})
        self.assertNotIn("mask-image", plain)
        self.assertIn('style="aspect-ratio: 1 / 1"', plain)   # legacy markup shape
        masked = cr.render_image({}, ctx, {
            "src": "assets/x.png", "alt": "x",
            "mask": "assets/shape-blob.png"})
        self.assertIn("mask-image", masked)
        self.assertIn("shape-blob.png", masked)


# ── mediaComposition normalization ───────────────────────────────────────────────────

class ApplyMediaComposition(Fixture):
    def test_registry_none_returns_same_object(self):
        comp = {"sections": [{"slots": [{"name": "m", "contract": "image"}]}]}
        self.assertIs(ms.apply_media_composition(comp, None), comp)

    def test_asset_ref_binds_canonical_src_and_alt(self):
        comp = {"sections": [{"slots": [
            {"name": "m", "role": "photo", "contract": "image",
             "assetRef": "hero-photo"}]}]}
        out = ms.apply_media_composition(comp, self.load())
        a = out["sections"][0]["slots"][0]["asset"]
        self.assertEqual(a["src"], "photo-a.png")
        self.assertTrue(a["alt"])

    def test_masked_media_sets_clip(self):
        comp = {"sections": [{"slots": [
            {"name": "m", "role": "photo", "contract": "image",
             "mediaComposition": {"mode": "masked-media", "maskRef": "accent-blob",
                                  "layers": [{"assetRef": "hero-photo"}]}}]}]}
        out = ms.apply_media_composition(comp, self.load())
        a = out["sections"][0]["slots"][0]["asset"]
        self.assertEqual(a["src"], "photo-a.png")
        self.assertEqual(a["mask"], "assets/shape-blob.png")

    def test_state_swap_folds_per_item_media(self):
        comp = {"sections": [{"slots": [
            {"name": "list", "contract": "accordion", "copy": [
                {"label": "Alpha", "value": "a"},
                {"label": "Beta", "value": "b"},
                {"label": "Gamma", "value": "c"}]},
            {"name": "m", "role": "media well", "contract": "image",
             "mediaComposition": {"mode": "state-swap", "trigger": "active-item",
                                  "layers": [
                                      {"assetRef": "ui-shot-a", "forItem": "Beta"},
                                      {"assetRef": "ui-shot-b", "forItem": 0}]}}]}]}
        out = ms.apply_media_composition(comp, self.load())
        items = out["sections"][0]["slots"][0]["copy"]
        self.assertEqual(items[1]["media"], "ui-shot-a.png")   # by label
        self.assertEqual(items[0]["media"], "ui-shot-b.png")   # by index
        self.assertNotIn("media", items[2])                    # unbound stays clean

    def test_layered_cluster_expands_layer_slots(self):
        """LAYERED PHOTO + ACCENT-BACKPLATE CTA: base photo over an accent-shape
        backplate + a componentRef stat chip riding the overlay machinery."""
        comp = {"sections": [{"id": "cta", "slots": [
            {"name": "media", "role": "photo", "contract": "image",
             "assetRef": "hero-photo",
             "mediaComposition": {
                 "mode": "layered",
                 "layers": [
                     {"assetRef": "accent-blob", "z": "back",
                      "registration": {"toSlot": "media", "edge": "left",
                                       "depthCols": 1}},
                     {"componentRef": {"contract": "stat",
                                       "usage": {"value": "98%", "label": "retention"}},
                      "z": "front",
                      "registration": {"toSlot": "media", "edge": "bottom",
                                       "depthBaselines": 2}}]}}]}]}
        out = ms.apply_media_composition(comp, self.load())
        slots = out["sections"][0]["slots"]
        self.assertEqual(len(slots), 3)
        backplate = slots[1]
        self.assertEqual(backplate["asset"]["src"], "shape-blob.png")
        self.assertEqual(backplate["z"], "back")
        self.assertEqual(backplate["registration"]["edge"], "left")
        chip = slots[2]
        self.assertEqual(chip["contract"], "stat")               # existing contract
        self.assertEqual(chip["copy"]["value"], "98%")
        self.assertEqual(chip["registration"]["depthBaselines"], 2)

    def test_background_with_foreground_defaults_full_bleed(self):
        comp = {"sections": [{"slots": [
            {"name": "bg", "role": "background", "contract": "image",
             "mediaComposition": {"mode": "background-with-foreground",
                                  "layers": [{"assetRef": "hero-photo", "z": "back"}]}}]}]}
        out = ms.apply_media_composition(comp, self.load())
        layer = out["sections"][0]["slots"][1]
        self.assertEqual(layer["width"], "full-bleed")
        self.assertEqual(layer["z"], "back")

    def test_facepile_and_tiled_grid_fold_items(self):
        for mode in ("facepile", "tiled-grid", "marquee"):
            comp = {"sections": [{"slots": [
                {"name": "faces", "role": "avatar row", "contract": "logo",
                 "mediaComposition": {"mode": mode, "layers": [
                     {"assetRef": "face-one"}, {"assetRef": "face-two"}]}}]}]}
            out = ms.apply_media_composition(comp, self.load())
            items = out["sections"][0]["slots"][0]["copy"]
            self.assertEqual([i["asset"]["src"] for i in items],
                             ["face-1.png", "face-2.png"], mode)

    def test_fold_never_overwrites_authored_items(self):
        comp = {"sections": [{"slots": [
            {"name": "faces", "contract": "logo", "copy": [{"text": "authored"}],
             "mediaComposition": {"mode": "facepile",
                                  "layers": [{"assetRef": "face-one"}]}}]}]}
        out = ms.apply_media_composition(comp, self.load())
        self.assertEqual(out["sections"][0]["slots"][0]["copy"],
                         [{"text": "authored"}])


# ── the composed-lane lints ──────────────────────────────────────────────────────────

def _sec(slots, use_case="features", sid="s1"):
    return {"id": sid, "useCase": use_case, "slots": slots}


class MediaBindingLint(Fixture):
    def test_registry_none_never_flags(self):
        comp = {"sections": [_sec([{"name": "m", "contract": "image"}])]}
        self.assertEqual(ms.lint_media_bindings(comp, None), [])

    def test_clean_bindings_pass(self):
        comp = {"sections": [_sec([
            {"name": "m", "role": "photo", "contract": "image",
             "assetRef": "hero-photo"}])]}
        self.assertEqual(ms.lint_media_bindings(comp, self.load()), [])

    def test_dangling_ref_flags(self):
        comp = {"sections": [_sec([
            {"name": "m", "role": "photo", "contract": "image",
             "assetRef": "invented-id"}])]}
        hits = ms.lint_media_bindings(comp, self.load())
        self.assertTrue(any(r == "media-binding" and "invented-id" in m
                            for _, r, m in hits))

    def test_silent_media_slot_flags(self):
        """THE defect class: a media slot resolving nothing and declaring nothing."""
        comp = {"sections": [_sec([
            {"name": "m", "role": "photo", "contract": "image", "asset": None}])]}
        hits = ms.lint_media_bindings(comp, self.load())
        self.assertTrue(any("silent placeholder" in m.lower() or
                            "declares no gap" in m for _, _, m in hits))

    def test_declared_gap_passes_and_needs_reason(self):
        ok = {"sections": [_sec([
            {"name": "m", "role": "photo", "contract": "image",
             "noCompatibleAsset": {"reason": "no team photo in inventory",
                                   "requiredKind": "team-photo"}}])]}
        self.assertEqual(ms.lint_media_bindings(ok, self.load()), [])
        bad = {"sections": [_sec([
            {"name": "m", "role": "photo", "contract": "image",
             "noCompatibleAsset": {"requiredKind": "team-photo"}}])]}
        hits = ms.lint_media_bindings(bad, self.load())
        self.assertTrue(any("reason" in m for _, _, m in hits))

    def test_placeholder_recipe_must_be_licensed(self):
        ok = {"sections": [_sec([
            {"name": "m", "role": "photo", "contract": "image",
             "noCompatibleAsset": {"reason": "gap", "placeholder": "soft-wash"}}])]}
        self.assertEqual(ms.lint_media_bindings(ok, self.load()), [])
        bad = {"sections": [_sec([
            {"name": "m", "role": "photo", "contract": "image",
             "noCompatibleAsset": {"reason": "gap", "placeholder": "invented-glow"}}])]}
        hits = ms.lint_media_bindings(bad, self.load())
        self.assertTrue(any("licensed" in m for _, _, m in hits))


class MarkLegalityLint(Fixture):
    """AS-67: usageRights × slot use-case, machine-checkable."""

    def test_mark_in_logos_section_passes(self):
        comp = {"sections": [_sec([
            {"name": "logos", "role": "logo wall", "contract": "logo",
             "assetRef": "client-mark"}], use_case="logos")]}
        self.assertEqual(
            [h for h in ms.lint_media_bindings(comp, self.load())
             if h[1] == "mark-legality"], [])

    def test_mark_in_proof_role_passes_any_section(self):
        comp = {"sections": [_sec([
            {"name": "strip", "role": "integration proof strip", "contract": "logo",
             "assetRef": "client-mark"}], use_case="features")]}
        self.assertEqual(
            [h for h in ms.lint_media_bindings(comp, self.load())
             if h[1] == "mark-legality"], [])

    def test_mark_decorating_features_flags(self):
        comp = {"sections": [_sec([
            {"name": "m", "role": "decorative photo", "contract": "image",
             "assetRef": "client-mark"}], use_case="features")]}
        hits = ms.lint_media_bindings(comp, self.load())
        self.assertTrue(any(r == "mark-legality" and "proof context" in m
                            for _, r, m in hits))

    def test_unattributed_testimonial_mark_flags(self):
        comp = {"sections": [_sec([
            {"name": "quote", "role": "customer quote", "contract": "testimonial",
             "copy": {"quote": "Great product"}},
            {"name": "m", "role": "company photo", "contract": "image",
             "assetRef": "client-mark"}], use_case="testimonial")]}
        hits = ms.lint_media_bindings(comp, self.load())
        self.assertTrue(any(r == "mark-legality" and "UNATTRIBUTED" in m
                            for _, r, m in hits))

    def test_attributed_testimonial_mark_passes(self):
        comp = {"sections": [_sec([
            {"name": "quote", "role": "customer quote", "contract": "testimonial",
             "copy": {"quote": "Great product", "name": "Jo Doe", "role": "COO"}},
            {"name": "m", "role": "company photo", "contract": "image",
             "assetRef": "client-mark"}], use_case="testimonial")]}
        self.assertEqual(
            [h for h in ms.lint_media_bindings(comp, self.load())
             if h[1] == "mark-legality"], [])

    def test_badge_placeholder_recipe_flags(self):
        """Badges are never fabricated — a generated recipe cannot stand in."""
        comp = {"sections": [_sec([
            {"name": "badges", "role": "award badge row", "contract": "image",
             "noCompatibleAsset": {"reason": "no badges", "placeholder": "soft-wash"}}])]}
        hits = ms.lint_media_bindings(comp, self.load())
        self.assertTrue(any(r == "mark-legality" and "fabricated" in m
                            for _, r, m in hits))

    def test_badge_with_unregistered_src_flags(self):
        comp = {"sections": [_sec([
            {"name": "badges", "role": "rating badge", "contract": "image",
             "asset": {"src": "assets/fake-badge.png"}}])]}
        hits = ms.lint_media_bindings(comp, self.load())
        self.assertTrue(any(r == "mark-legality" and "registered" in m
                            for _, r, m in hits))

    def test_badge_bound_from_registry_passes(self):
        comp = {"sections": [_sec([
            {"name": "badges", "role": "award badge row", "contract": "image",
             "assetRef": "award-mark"}], use_case="logos")]}
        self.assertEqual(
            [h for h in ms.lint_media_bindings(comp, self.load())
             if h[1] == "mark-legality"], [])


# ── the asset-request manifest (no-match ladder rung 2) ──────────────────────────────

class AssetRequestManifest(Fixture):
    def test_collect_and_write(self):
        comp = {"sections": [
            {"id": "hero", "useCase": "hero", "surfaceIntent": "primary", "slots": [
                {"name": "m", "role": "team photo", "contract": "image",
                 "mediaAspect": "landscape",
                 "noCompatibleAsset": {"reason": "no team photography extracted",
                                       "requiredKind": "team-photo",
                                       "placeholder": "soft-wash"}}]}]}
        entries = ms.collect_asset_requests(comp)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["requiredKind"], "team-photo")
        self.assertEqual(entries[0]["aspect"], "landscape")   # slot aspect inherited
        self.assertEqual(entries[0]["surface"], "primary")    # section surface inherited
        self.assertEqual(entries[0]["placeholder"], "soft-wash")
        out = self.tmp / "lane"
        out.mkdir()
        path = ms.write_asset_request_manifest(out, comp)
        payload = json.loads(path.read_text())
        self.assertEqual(payload["schemaVersion"], "asset-requests.v1")
        self.assertEqual(len(payload["requests"]), 1)

    def test_stale_manifest_removed_when_gapless(self):
        out = self.tmp / "lane2"
        out.mkdir()
        (out / ms.ASSET_REQUESTS_NAME).write_text("{}")
        self.assertIsNone(ms.write_asset_request_manifest(out, {"sections": []}))
        self.assertFalse((out / ms.ASSET_REQUESTS_NAME).exists())


# ── validator checks C26/C27/C28 ─────────────────────────────────────────────────────

class ValidatorChecks(Fixture):
    def _run(self, lib_doc=None):
        rep = Report(self.tmp)
        _check_media_assets(rep, self.tmp, lib_doc or {})
        return rep

    def _rewrite(self, mutate):
        reg = copy.deepcopy(self.registry)
        mutate(reg)
        (self.tmp / "media-assets.yaml").write_text(
            yaml.safe_dump(reg, sort_keys=False))

    def test_valid_fixture_passes_clean(self):
        rep = self._run()
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])

    def test_absence_is_a_note_not_an_error(self):
        (self.tmp / "media-assets.yaml").unlink()
        rep = self._run()
        self.assertEqual(rep.errors, [])
        self.assertTrue(any("C26" in n for n in rep.notes))

    def test_bad_kind_fails(self):
        self._rewrite(lambda r: r["assets"][0]["assetSemantics"].update(
            kind="campaign-hero-art"))
        self.assertTrue(any("kind" in e for e in self._run().errors))

    def test_missing_file_fails(self):
        self._rewrite(lambda r: r["assets"][0].update(file="ghost.png"))
        self.assertTrue(any("not on disk" in e for e in self._run().errors))

    def test_missing_rights_fails(self):
        self._rewrite(lambda r: r["assets"][0].update(usageRights=None))
        self.assertTrue(any("usageRights" in e for e in self._run().errors))

    def test_missing_provenance_fails(self):
        self._rewrite(lambda r: r["assets"][0].update(provenance={}))
        self.assertTrue(any("provenance" in e for e in self._run().errors))

    def test_non_slug_or_duplicate_id_fails(self):
        self._rewrite(lambda r: r["assets"][0].update(id="Hero Photo!"))
        self.assertTrue(any("slug" in e for e in self._run().errors))
        self._rewrite(lambda r: r["assets"][1].update(id="hero-photo"))
        self.assertTrue(any("duplicate id" in e for e in self._run().errors))

    def test_poster_discipline(self):
        # shader-canvas REQUIRES a poster
        self._rewrite(lambda r: r["generatedVisuals"].append(
            {"id": "live-canvas", "kind": "shader-canvas",
             "recipe": {"source": None, "uniforms": {}},
             "poster": None, "degrade": ["live", "poster", "omit"],
             "provenance": {"source": "capture-files", "sections": [],
                            "confidence": "low"}}))
        self.assertTrue(any("REQUIRES a captured poster" in e
                            for e in self._run().errors))
        # css-gradient may go poster-less ONLY with a posterNote
        self._rewrite(lambda r: r["generatedVisuals"][0].pop("posterNote"))
        self.assertTrue(any("posterNote" in e for e in self._run().errors))
        # a named poster must exist on disk
        self._rewrite(lambda r: r["generatedVisuals"][1].update(poster="ghost.png"))
        self.assertTrue(any("poster" in e and "not on disk" in e
                            for e in self._run().errors))

    def test_mesh_gradient_recipe_params_survive_load(self):
        reg = self.load()
        mesh = ms.generated_index(reg)["mesh-drift"]
        blobs = mesh["recipe"]["blobs"]
        self.assertEqual(len(blobs), 2)
        self.assertEqual(blobs[0]["hueRole"], "accent/warm")   # token ROLE, not hex
        self.assertEqual(blobs[1]["blurPx"], 60)
        self.assertEqual(mesh["degrade"], ["live", "poster", "omit"])

    def test_c27_dangling_layer_ref_fails(self):
        lib = {"patterns": [{"id": "p1", "contentShape": {"slots": [
            {"name": "media", "mediaComposition": {
                "mode": "layered", "layers": [{"assetRef": "ghost-id"}]}}]}}]}
        rep = self._run(lib)
        self.assertTrue(any("C27" in e and "ghost-id" in e for e in rep.errors))

    def test_c27_orphan_bound_asset_fails(self):
        lib = {"patterns": [{"id": "p1", "contentShape": {"slots": [
            {"name": "media", "assets": ["unregistered-file.png"]}]}}]}
        rep = self._run(lib)
        self.assertTrue(any("C27" in e and "unregistered-file.png" in e
                            for e in rep.errors))
        # a REGISTERED binding stays clean (canonical or variant filename)
        ok_lib = {"patterns": [{"id": "p1", "contentShape": {"slots": [
            {"name": "media", "assets": ["photo-a.png", "photo-a-2x.png"]}]}}]}
        self.assertEqual([e for e in self._run(ok_lib).errors if "C27" in e], [])

    def test_c27_bad_mode_and_layer_shape_fail(self):
        lib = {"patterns": [{"id": "p1", "contentShape": {"slots": [
            {"name": "media", "mediaComposition": {
                "mode": "pinwheel", "layers": [{}]}}]}}]}
        errs = self._run(lib).errors
        self.assertTrue(any("mode" in e for e in errs))
        self.assertTrue(any("neither assetRef nor componentRef" in e for e in errs))

    def test_c27_component_ref_contract_must_exist(self):
        lib = {"patterns": [{"id": "p1", "contentShape": {"slots": [
            {"name": "media", "mediaComposition": {
                "mode": "layered",
                "layers": [{"componentRef": {"contract": "hologram"}}]}}]}}]}
        rep = self._run(lib)
        self.assertTrue(any("componentRef contract" in e for e in rep.errors))

    def test_c28_byte_identical_duplicates_warn(self):
        (self.assets / "photo-b.png").write_bytes(
            (self.assets / "photo-a.png").read_bytes())
        self._rewrite(lambda r: r["assets"].append(
            _entry("hero-photo-twin", "photo-b.png")))
        rep = self._run()
        self.assertEqual(rep.errors, [])
        self.assertTrue(any("C28" in w and "byte-identical" in w
                            for w in rep.warnings))

    def test_c28_variant_outresolving_canonical_warns(self):
        self._rewrite(lambda r: r["assets"][0]["variants"].__setitem__(
            0, {"file": "photo-a-2x.png", "relation": "retina", "scale": 2,
                "w": 4000, "h": 3000}))
        rep = self._run()
        self.assertTrue(any("C28" in w and "out-resolves" in w
                            for w in rep.warnings))


# ── curate_assets media-assets DRAFT emission ────────────────────────────────────────

class CurateDraft(unittest.TestCase):
    """curate_assets.py emits media-assets-draft.yaml: stable ids, content-hash
    dedupe → variants[], Pillow stats where measurable (graceful skip for
    vectors), TAG_GUESSES-mapped kind/rights hints, status: draft."""

    def setUp(self):
        import curate_assets as ca
        self.ca = ca
        self.tmp = Path(tempfile.mkdtemp(prefix="curate-draft-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.assets = self.tmp / "assets"
        self.assets.mkdir(parents=True)
        (self.assets / "hero-photo.png").write_bytes(_png_bytes(rgb=(200, 80, 40)))
        (self.assets / "hero-photo-copy.png").write_bytes(
            (self.assets / "hero-photo.png").read_bytes())          # byte twin
        (self.assets / "badge-top-10.png").write_bytes(_png_bytes(rgb=(30, 30, 30)))
        (self.assets / "logo-inline-00.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h9v9z"/></svg>')
        self.entries = [
            {"dest": "hero-photo.png", "origin": "files", "bytes": 200,
             "tagGuess": "hero"},
            {"dest": "hero-photo-copy.png", "origin": "files", "bytes": 200,
             "tagGuess": "hero"},
            {"dest": "badge-top-10.png", "origin": "files", "bytes": 180,
             "tagGuess": "award-badge"},
            {"dest": "logo-inline-00.svg", "origin": "inline-svg", "bytes": 90,
             "tagGuess": "logo-wall-logo", "altHint": "Acme"},
        ]

    def test_draft_shape_dedupe_stats_and_hints(self):
        draft = self.ca.build_media_draft(self.assets, self.entries)
        self.assertEqual(draft["schemaVersion"], "media-assets.v1")
        self.assertEqual(draft["status"], "draft")
        by_id = {a["id"]: a for a in draft["assets"]}
        self.assertEqual(len(by_id), 3)                # 4 files, one byte-twin folded
        photo = next(a for a in draft["assets"]
                     if a["file"] in ("hero-photo.png", "hero-photo-copy.png"))
        self.assertEqual(photo["variants"][0]["relation"], "duplicate")
        # Pillow stats measured for rasters, gracefully absent for the vector
        self.assertEqual(photo["facts"]["stats"]["source"], "measured")
        self.assertIn(photo["facts"]["stats"]["luminanceBand"],
                      ("dark", "mid", "light"))
        self.assertIsNone(photo["facts"]["focalPoint"])      # null = UNKNOWN
        vec = next(a for a in draft["assets"] if a["file"].endswith(".svg"))
        self.assertIsNone(vec["facts"]["stats"])
        self.assertEqual(vec["facts"]["altHarvested"], "Acme")
        self.assertEqual(vec["provenance"]["source"], "inline-svg")
        # kind/rights hints from the tag guesses
        badge = next(a for a in draft["assets"] if a["file"].startswith("badge"))
        self.assertEqual(badge["assetSemantics"]["kind"], "badge-review-award")
        self.assertEqual(badge["usageRights"], "third-party-mark")
        self.assertEqual(vec["assetSemantics"]["kind"], "logo-third-party")

    def test_emit_writes_sibling_draft_file(self):
        path = self.ca.emit_media_draft(self.tmp, self.entries)
        self.assertEqual(path.name, "media-assets-draft.yaml")
        loaded = yaml.safe_load(path.read_text())
        self.assertEqual(loaded["status"], "draft")
        # the draft's filename differs from the authored artifact — the runtime
        # loader must NOT pick it up (draft-vs-authored discipline)
        self.assertIsNone(ms.load_media_assets(self.tmp))

    def test_kind_guess_map_stays_in_enum(self):
        for kind, rights in self.ca.KIND_GUESSES.values():
            self.assertIn(kind, ms.ASSET_KINDS)
            self.assertIn(rights, ms.USAGE_RIGHTS)


# ── prompt injection block ───────────────────────────────────────────────────────────

class PromptBlock(Fixture):
    def test_empty_for_artifactless(self):
        self.assertEqual(ms.media_rules_block(None), "")

    def test_block_carries_digest_rule_ladder_and_as67(self):
        block = ms.media_rules_block(self.load())
        self.assertIn(ms.MEDIA_FACTS_BEGIN, block)
        self.assertIn(ms.MEDIA_FACTS_END, block)
        self.assertIn("hero-photo · photograph · landscape · own · mid · fit:cover",
                      block)
        self.assertIn("soft-wash · css-gradient", block)
        self.assertIn("HARD RULE", block)
        self.assertIn("NO-MATCH LADDER", block)
        self.assertIn("noCompatibleAsset", block)
        self.assertIn("AS-67", block)


if __name__ == "__main__":
    unittest.main()
