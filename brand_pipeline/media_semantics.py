#!/usr/bin/env python3
"""media_semantics.py — the MEDIA SEMANTICS SYSTEM runtime (media-assets.v1).

Normative spec: brand_pipeline/spec/media-assets-schema.md. This module is the ONE
code home for the three media families:

  ASSET SEMANTICS       — the per-brand ``runs/<brand>/brand/media-assets.yaml``
                          registry (stable logical-asset ids, variant dedupe, kind
                          taxonomy, rights, luminance facts, treatmentDefaults).
  COMPOSITION SEMANTICS — the ``mediaComposition`` slot grammar (mode + layers with
                          the §4.6.5 registration/z vocabulary VERBATIM) normalized
                          onto the EXISTING renderer channels (layered-media path,
                          per-item media swap, logo-strip item folds, mask clips).
  GENERATED VISUALS     — code recipes (css-gradient / mesh-gradient-blobs / …)
                          licensed by measured evidence, carrying posters.

Everything is FACT-GATED: a brand without ``media-assets.yaml`` loads ``None`` and
every consumer keeps byte-identical behavior (prompt assembly, rendering, gating) —
the same degrade contract as style-scale/voice-facts (pass-3).

Wire points:
  - ``compose_section.attach_asset_inventory``  → ``attach_media_assets`` (in-memory
    ``_mediaAssets`` + ``_mediaAssetsFit`` registries).
  - ``component_render.asset_render_mode``      → per-asset ``treatmentDefaults.fit``
    (falls back to assets-tagged.json facts).
  - ``compose_from_composition.render_composition`` → ``apply_media_composition``
    (assetRef resolution + mode normalization) + the ASSET-REQUEST MANIFEST
    (``asset-requests.json`` beside ``composition.json``).
  - ``generate_composition.build_prompt``       → ``media_rules_block`` (inventory
    digest + the HARD RULE + the no-match ladder; [[MEDIA-FACTS:BEGIN/END]]).
  - ``generate_composition.generate_composition`` prefilter + ``onbrand_check
    --composition`` rows → ``lint_media_bindings`` (media-binding + AS-67
    mark-legality).

No brand or palette knowledge lives here — ids/kinds/rights come from the ACTIVE
brand's own artifact.
"""
from __future__ import annotations

import copy as _copy
import json
import re
from pathlib import Path

import yaml

SCHEMA_VERSION = "media-assets.v1"
MEDIA_FACTS_BEGIN = "[[MEDIA-FACTS:BEGIN]]"
MEDIA_FACTS_END = "[[MEDIA-FACTS:END]]"

# ── the closed vocabularies (spec §2.1 / §3 / §5) ────────────────────────────────────

ASSET_KINDS = frozenset({
    "photograph", "portrait", "avatar", "team-photo", "client-photo",
    "product-packshot", "product-ui-screenshot", "device-framed-mockup",
    "product-ui-collage", "diagram", "chart", "illustration", "spot-icon",
    "ui-glyph", "social-icon", "logo-own", "logo-third-party",
    "badge-compliance", "badge-review-award", "badge-appstore",
    "background-art", "texture-noise", "pattern-tile", "accent-shape",
    "3d-render", "map", "social-proof-screenshot", "video-ambient-loop",
    "video-content", "video-embed-third-party", "video-poster", "animation",
})

GENERATED_KINDS = frozenset({
    "css-gradient", "mesh-gradient-blobs", "shader-canvas", "embedded-3d",
    "noise-grain", "dot-grid",
})
# declarative kinds whose recipe alone reproduces the visual — poster may be null
# (with a posterNote); every other kind REQUIRES a captured poster (spec §5.1).
SELF_RENDERING_KINDS = frozenset({"css-gradient", "noise-grain", "dot-grid"})

MEDIA_COMP_MODES = frozenset({
    "single", "layered", "masked-media", "background-with-foreground",
    "overlapping-cluster", "scattered-cluster", "facepile", "tiled-grid",
    "marquee", "masonry", "split-pair", "carousel", "state-swap",
    "atomic-collage", "icon-in-headline",
})
STATE_SWAP_TRIGGERS = frozenset({"active-item", "hover", "tab"})
USAGE_RIGHTS = frozenset({"own", "stock", "third-party-mark"})
TREATMENT_FITS = frozenset({"cover", "contain", "mark"})
BADGE_KINDS = frozenset({"badge-compliance", "badge-review-award", "badge-appstore"})

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# slot roles/names that constitute a FACTUAL PROOF context for third-party marks
# (AS-67). Generic role words only — never section/content names.
_PROOF_ROLE_RE = re.compile(
    r"proof|logo|partner|integration|badge|press|award|rating|marquee|trust|client",
    re.IGNORECASE)
_BADGE_ROLE_RE = re.compile(r"badge|award|rating", re.IGNORECASE)
# copy keys whose non-empty value counts as ATTRIBUTION for a testimonial mark
_ATTRIBUTION_KEYS = ("name", "author", "attribution", "company", "source")


# ── asset-kind ↔ slot-role ELIGIBILITY (spec §6.1; AS-80) ────────────────────────────
#
# GENERIC, brand-agnostic, DECLARATIVE. Two families of media slot roles exist:
#
#   IMAGE (media-well) roles — hero-media, card-lead-media, full-bleed background,
#     feature-image, product-shot, portrait/illustration/split media — paint a
#     visual that FILLS a slot (fit: cover|contain). They accept ONLY image-family
#     kinds (photograph/portrait/illustration/product-ui-screenshot/packshot/
#     3d-render/diagram/background-art/…).
#   ICON/MARK roles — a content-scale glyph that sits at MARK height (above a
#     heading, inline in a headline, in a nav/social/proof row). They carry the
#     ICON-family kinds (spot-icon/ui-glyph/social-icon/logo marks).
#
# The eligibility law: an ICON-family kind must render at `mark` height and is
# NEVER blown up to fill an image/lead/full-bleed media well; an image role with
# no compatible image-family asset must declare its gap (asset-request), never
# substitute an icon. Other brands INHERIT this table unchanged — no brand,
# palette, section, or content knowledge lives in it.
ICON_FAMILY_KINDS = frozenset({
    "spot-icon", "ui-glyph", "social-icon", "logo-own", "logo-third-party",
})
IMAGE_FAMILY_KINDS = frozenset({
    "photograph", "portrait", "avatar", "team-photo", "client-photo",
    "product-packshot", "product-ui-screenshot", "device-framed-mockup",
    "product-ui-collage", "diagram", "chart", "illustration",
    "background-art", "texture-noise", "pattern-tile", "accent-shape",
    "3d-render", "map", "social-proof-screenshot", "video-poster",
})
# a media-well fit FILLS an image slot; an icon/mark asset resolved this way is
# the mis-scale (icon artwork stretched to lead-media dimensions) AS-80 catches.
MEDIA_WELL_FITS = frozenset({"cover", "contain"})
# generic role words that DEMAND an image-family asset (a full media well / lead /
# hero visual). Never section or content names — reusable across brands.
_IMAGE_LEAD_ROLE_RE = re.compile(
    r"hero|lead|full-?bleed|feature-image|product-shot|background-media|"
    r"portrait-media|illustration-media|split-media|photo|cover-media",
    re.IGNORECASE)


def kind_family(kind: str | None) -> str:
    """Coarse family for the eligibility table: ``icon`` (icon/mark-family),
    ``badge`` (award/compliance/appstore marks), ``image`` (media-well-eligible),
    or ``other`` (video/animation/generated — governed elsewhere)."""
    k = str(kind or "").strip().lower()
    if k in ICON_FAMILY_KINDS:
        return "icon"
    if k in BADGE_KINDS:
        return "badge"
    if k in IMAGE_FAMILY_KINDS:
        return "image"
    return "other"


def is_icon_family(kind: str | None) -> bool:
    return kind_family(kind) == "icon"


def role_demands_image(role_probe: str | None) -> bool:
    """True when a slot's generic role words name an IMAGE/lead/full-bleed media
    role (the roles that require an image-family asset, never an icon)."""
    return bool(_IMAGE_LEAD_ROLE_RE.search(str(role_probe or "")))


def eligible_render_mode(kind: str | None, fit: str | None) -> str:
    """The ELIGIBLE render fit for an asset given its KIND and an EXPLICITLY
    resolved fit (``cover|contain|mark``). The render-time arm of the
    asset-kind↔slot-role eligibility rule: an ICON/MARK-family kind is never
    rendered as a media well — an EXPLICIT ``cover``/``contain`` fit authored on an
    icon/mark asset is coerced to ``mark`` so a content-scale glyph can never be
    blown up to fill a lead/hero image slot. Image-family kinds pass through
    unchanged. The unset/absent case ("") is NOT coerced here — the renderer keeps
    its historical ``cover`` default so brands whose icon/mark assets legitimately
    fall to that default stay byte-identical; the AS-80 gate row flags those. Byte-
    identity for every existing explicit binding that is not an icon media-well."""
    f = str(fit or "").strip().lower()
    if is_icon_family(kind) and f in MEDIA_WELL_FITS:
        return "mark"
    return f


# ── loading + indexes (fact-gated) ───────────────────────────────────────────────────

def load_media_assets(brand_dir: Path | str | None) -> dict | None:
    """Parsed media-assets.yaml for a brand dir, or None (absent/invalid/foreign
    schema) — the same fact-gating shape as style_scale.load_style_scale. Consumers
    treat None as "the media semantics layer does not exist" and keep byte-identical
    behavior."""
    if not brand_dir:
        return None
    path = Path(brand_dir) / "media-assets.yaml"
    if not path.exists():
        return None
    try:
        doc = yaml.safe_load(path.read_text())
    except Exception:
        return None
    if not isinstance(doc, dict) or doc.get("schemaVersion") != SCHEMA_VERSION:
        return None
    return doc


def asset_entries(registry: dict | None) -> list[dict]:
    return [a for a in ((registry or {}).get("assets") or []) if isinstance(a, dict)]


def generated_entries(registry: dict | None) -> list[dict]:
    return [g for g in ((registry or {}).get("generatedVisuals") or [])
            if isinstance(g, dict)]


def asset_index(registry: dict | None) -> dict[str, dict]:
    """id → logical-asset entry."""
    return {str(a.get("id")): a for a in asset_entries(registry) if a.get("id")}


def generated_index(registry: dict | None) -> dict[str, dict]:
    return {str(g.get("id")): g for g in generated_entries(registry) if g.get("id")}


def file_index(registry: dict | None) -> dict[str, dict]:
    """filename (canonical AND variants) → logical-asset entry."""
    out: dict[str, dict] = {}
    for a in asset_entries(registry):
        f = str(a.get("file") or "").strip()
        if f:
            out.setdefault(Path(f).name, a)
        for v in (a.get("variants") or []):
            if isinstance(v, dict) and v.get("file"):
                out.setdefault(Path(str(v["file"])).name, a)
    return out


def resolve_ref(registry: dict | None, ref: str | None) -> str | None:
    """assetRef → the CANONICAL variant filename (relative to assets/), or None."""
    if not ref:
        return None
    entry = asset_index(registry).get(str(ref).strip())
    if not entry:
        return None
    f = str(entry.get("file") or "").strip()
    return Path(f).name if f else None


def _entry_alt(entry: dict) -> str:
    sem = entry.get("assetSemantics") if isinstance(entry.get("assetSemantics"), dict) else {}
    facts = entry.get("facts") if isinstance(entry.get("facts"), dict) else {}
    return str(facts.get("altHarvested") or sem.get("subject")
               or entry.get("id") or "").strip()


def fit_map(registry: dict | None) -> dict[str, str]:
    """filename → treatmentDefaults.fit for every registered file (canonical +
    variants). Only entries carrying an explicit fit appear."""
    out: dict[str, str] = {}
    for a in asset_entries(registry):
        td = a.get("treatmentDefaults") if isinstance(a.get("treatmentDefaults"), dict) else {}
        fit = str(td.get("fit") or "").strip().lower()
        if fit not in TREATMENT_FITS:
            continue
        names = [str(a.get("file") or "")]
        names += [str(v.get("file") or "") for v in (a.get("variants") or [])
                  if isinstance(v, dict)]
        for n in names:
            n = Path(n).name
            if n:
                out.setdefault(n, fit)
    return out


def kind_map(registry: dict | None) -> dict[str, str]:
    """filename → assetSemantics.kind for every registered file (canonical +
    variants). Feeds the render-time asset-kind↔slot-role eligibility coercion so
    the renderer can classify a bound file's FAMILY without re-reading disk."""
    out: dict[str, str] = {}
    for a in asset_entries(registry):
        sem = a.get("assetSemantics") if isinstance(a.get("assetSemantics"), dict) else {}
        k = str(sem.get("kind") or "").strip().lower()
        if not k:
            continue
        names = [str(a.get("file") or "")]
        names += [str(v.get("file") or "") for v in (a.get("variants") or [])
                  if isinstance(v, dict)]
        for n in names:
            n = Path(n).name
            if n:
                out.setdefault(n, k)
    return out


def attach_media_assets(doc: dict, brand_dir: Path | str) -> dict:
    """Attach the ACTIVE brand's media-assets registry to the in-memory doc
    (``_mediaAssets`` raw + ``_mediaAssetsFit`` filename→fit + ``_mediaAssetsKind``
    filename→kind). Brands without the artifact attach None/{} — every consumer
    then behaves byte-identically. Idempotent; returns the doc for chaining."""
    if isinstance(doc, dict):
        registry = load_media_assets(brand_dir)
        doc["_mediaAssets"] = registry
        doc["_mediaAssetsFit"] = fit_map(registry)
        doc["_mediaAssetsKind"] = kind_map(registry)
    return doc


# ── aspect classification (digest + compatibility vocabulary) ────────────────────────

def aspect_class(entry: dict) -> str:
    """The logical asset's aspect CLASS from its measured intrinsic geometry —
    the same class vocabulary composition slots use (mediaAspect)."""
    facts = entry.get("facts") if isinstance(entry.get("facts"), dict) else {}
    ratio = facts.get("intrinsicAspect")
    if not isinstance(ratio, (int, float)) or ratio <= 0:
        orient = str(facts.get("orientation") or "").strip().lower()
        return orient or "freeform"
    if ratio >= 2.8:
        return "pano"
    if ratio >= 1.9:
        return "wide"
    if ratio > 1.1:
        return "landscape"
    if ratio >= 0.9:
        return "square"
    return "portrait"


# ── prompt injection (fact-gated digest + hard rule + ladder) ────────────────────────

def media_digest_lines(registry: dict) -> list[str]:
    """One compact line per LOGICAL asset: id · kind · aspect-class · rights ·
    luminance band · default fit. The generator binds by ID; filenames stay the
    compat channel."""
    lines: list[str] = []
    for a in asset_entries(registry):
        sem = a.get("assetSemantics") if isinstance(a.get("assetSemantics"), dict) else {}
        facts = a.get("facts") if isinstance(a.get("facts"), dict) else {}
        stats = facts.get("stats") if isinstance(facts.get("stats"), dict) else {}
        td = a.get("treatmentDefaults") if isinstance(a.get("treatmentDefaults"), dict) else {}
        bits = [str(a.get("id") or "?"), str(sem.get("kind") or "?"), aspect_class(a),
                str(a.get("usageRights") or "?")]
        if stats.get("luminanceBand"):
            bits.append(str(stats["luminanceBand"]))
        if td.get("fit"):
            bits.append(f"fit:{td['fit']}")
        sub = str(sem.get("subtype") or "").strip()
        if sub:
            bits.insert(2, sub)
        lines.append("- " + " · ".join(bits))
    return lines


def generated_digest_lines(registry: dict) -> list[str]:
    return [f"- {g.get('id')} · {g.get('kind')} (licensed generated-visual recipe)"
            for g in generated_entries(registry) if g.get("id")]


def media_rules_block(registry: dict | None) -> str:
    """The MEDIA INVENTORY + HARD RULE + NO-MATCH LADDER prompt block ("" when the
    brand ships no media-assets.yaml — the byte-identity contract)."""
    if not registry:
        return ""
    lines = media_digest_lines(registry)
    gen = generated_digest_lines(registry)
    parts = [MEDIA_FACTS_BEGIN,
             "## Media inventory (media-assets.v1 — bind by `assetRef` id)",
             "Extracted LOGICAL assets (id · kind · aspect-class · rights · "
             "luminance · default fit):"]
    parts += lines or ["- (none)"]
    if gen:
        parts += ["Licensed GENERATED-VISUAL recipes (the ONLY legal placeholder "
                  "devices; a brand device roster, never a renderer default):"]
        parts += gen
    parts += [
        "MEDIA BINDING — HARD RULE: for any media-bearing slot, when a COMPATIBLE "
        "extracted asset exists (kind + composition role + aspect-class match), BIND "
        "it: set `assetRef` to its id (or `asset.src` to its exact filename). NEVER "
        "invent a filename. NEVER synthesize/regenerate a visual when a compatible "
        "extracted asset exists.",
        "NO-MATCH LADDER (when nothing compatible exists, in order):",
        "1. reuse-with-treatment — bind the nearest compatible asset and declare the "
        "adapting treatment (recrop/tint per the brand's treatment rules); still an "
        "`assetRef` binding.",
        "2. declared gap — set `noCompatibleAsset: {reason, requiredKind, aspect?, "
        "surface?}` on the slot; the pipeline emits it into the lane's asset-request "
        "manifest.",
        "3. brand-legal placeholder recipe — the declared gap may name `placeholder: "
        "<generatedVisuals id>` from the roster above. Renderer default plates are "
        "NOT a rung.",
        "A media slot that neither resolves an asset nor declares its gap FAILS the "
        "gate (silent placeholder = failure).",
        "THIRD-PARTY MARKS (AS-67): assets with rights `third-party-mark` "
        "(client/partner/press/integration logos, review badges) bind ONLY into "
        "factual proof contexts (logo/proof/badge/integration strips; attributed "
        "testimonials). Never decorate invented quotes with a client's mark; never "
        "fabricate a badge (badge slots bind registry marks or declare the gap — a "
        "placeholder recipe cannot stand in for a badge).",
        MEDIA_FACTS_END,
    ]
    return "\n".join(parts)


# ── composition normalization (assetRef + mediaComposition → existing channels) ──────

def _is_media_slot(slot: dict) -> bool:
    return (str(slot.get("contract") or "").lower() in ("image", "video")
            or any(k in str(slot.get("role") or "").lower()
                   for k in ("photo", "media", "image")))


def _layer_role(layer: dict, i: int) -> str:
    z = str(layer.get("z") or "").lower()
    if z == "back" or str(layer.get("width") or "") == "full-bleed":
        return "background"
    return f"overlay-photo-{i}"


def apply_media_composition(comp: dict, registry: dict | None) -> dict:
    """Normalize a composition's media-semantics vocabulary onto the channels the
    EXISTING renderer already consumes. Registry None → the SAME object back,
    untouched (byte-identity for artifact-less brands). Otherwise operates on a
    deep copy:

      - ``slot.assetRef``            → ``slot.asset {src, alt}`` (canonical variant).
      - ``mediaComposition.maskRef`` → ``slot.asset.mask`` (the accent-shape clip;
        render_image/_layer_img consume it as a CSS mask).
      - mode ``state-swap``          → per-item ``media`` on the section's repeatable
        items copy (the accordion media-swap channel, fid5/fid8) — layers bind by
        ``forItem`` index/label, else in order.
      - modes ``layered`` / ``background-with-foreground`` / ``overlapping-cluster``
        / ``scattered-cluster`` → additional MEDIA SLOTS carrying the layer's
        placement (the §4.6.5 layered-media path); ``componentRef`` layers become
        regular slots on the component's own contract (the existing overlay/panel
        machinery draws them where the archetype supports placement).
      - modes ``tiled-grid`` / ``marquee`` / ``facepile`` / ``split-pair`` /
        ``carousel`` → the slot's repeatable copy items (the logo-strip / marks
        fold), only when the slot carries no authored item list already.

    Unresolvable refs are left for ``lint_media_bindings`` to fail loud — this
    normalizer never invents and never drops declared intent silently."""
    if not registry or not isinstance(comp, dict):
        return comp
    idx = asset_index(registry)
    out = _copy.deepcopy(comp)

    def _bind_asset(slot: dict, ref: str) -> None:
        entry = idx.get(str(ref).strip())
        if not entry:
            return
        f = resolve_ref(registry, ref)
        if not f:
            return
        a = slot.get("asset") if isinstance(slot.get("asset"), dict) else {}
        if not a.get("src"):
            a = {**a, "src": f}
            if not a.get("alt"):
                alt = _entry_alt(entry)
                if alt:
                    a["alt"] = alt
            slot["asset"] = a

    for sec in (out.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        slots = [s for s in (sec.get("slots") or []) if isinstance(s, dict)]
        new_slots: list[dict] = []
        for slot in slots:
            if slot.get("assetRef"):
                _bind_asset(slot, str(slot["assetRef"]))
            mc = slot.get("mediaComposition")
            if not isinstance(mc, dict):
                continue
            mode = str(mc.get("mode") or "").strip().lower()
            layers = [l for l in (mc.get("layers") or []) if isinstance(l, dict)]

            # masked-media: the clip asset rides on the slot's asset payload.
            mask_file = resolve_ref(registry, mc.get("maskRef")) \
                if mc.get("maskRef") else None
            if mode == "masked-media":
                if layers and layers[0].get("assetRef") and not slot.get("asset"):
                    _bind_asset(slot, str(layers[0]["assetRef"]))
                if mask_file and isinstance(slot.get("asset"), dict):
                    slot["asset"].setdefault("mask", f"assets/{mask_file}")

            elif mode == "state-swap":
                # generalized accordion/tab/hover media swap: fold layer files onto
                # the per-item `media` channel (C17's items[].media contract).
                items_slot = next(
                    (s for s in slots if isinstance(s.get("copy"), list)
                     and s.get("copy")), None)
                items = items_slot.get("copy") if items_slot is not None else None
                if isinstance(items, list):
                    for i, layer in enumerate(layers):
                        f = resolve_ref(registry, layer.get("assetRef"))
                        if not f:
                            continue
                        tgt = layer.get("forItem", i)
                        item = None
                        if isinstance(tgt, int) and 0 <= tgt < len(items):
                            item = items[tgt]
                        elif isinstance(tgt, str):
                            item = next(
                                (it for it in items if isinstance(it, dict)
                                 and tgt.strip().lower() in str(
                                     it.get("label") or it.get("heading") or ""
                                 ).strip().lower()), None)
                        if isinstance(item, dict) and not item.get("media"):
                            item["media"] = f

            elif mode in ("layered", "background-with-foreground",
                          "overlapping-cluster", "scattered-cluster"):
                for i, layer in enumerate(layers):
                    comp_ref = layer.get("componentRef") \
                        if isinstance(layer.get("componentRef"), dict) else None
                    extra: dict = {
                        "name": f"{slot.get('name') or 'media'}-layer-{i}",
                        "z": layer.get("z") or ("back" if i == 0 else "front"),
                    }
                    for k in ("registration", "alignTo", "colSpan", "offsetCols",
                              "offsetBaselines", "width", "mediaAspect"):
                        if layer.get(k) is not None:
                            extra[k] = layer[k]
                    if comp_ref is not None:
                        extra["role"] = "floating-component"
                        extra["contract"] = str(comp_ref.get("contract") or "card")
                        if isinstance(comp_ref.get("usage"), dict):
                            extra["copy"] = dict(comp_ref["usage"])
                    else:
                        f = resolve_ref(registry, layer.get("assetRef"))
                        if not f:
                            continue
                        entry = idx.get(str(layer.get("assetRef") or "").strip())
                        extra["role"] = _layer_role(layer, i)
                        extra["contract"] = "image"
                        extra["asset"] = {"src": f}
                        alt = _entry_alt(entry or {})
                        if alt:
                            extra["asset"]["alt"] = alt
                        if mask_file:
                            extra["asset"]["mask"] = f"assets/{mask_file}"
                        if str(extra["z"]).lower() == "back" \
                                and not extra.get("width") \
                                and mode == "background-with-foreground":
                            extra["width"] = "full-bleed"
                    new_slots.append(extra)

            elif mode in ("tiled-grid", "marquee", "facepile", "split-pair",
                          "carousel"):
                if layers and not isinstance(slot.get("copy"), list):
                    items = []
                    for layer in layers:
                        f = resolve_ref(registry, layer.get("assetRef"))
                        if not f:
                            continue
                        entry = idx.get(str(layer.get("assetRef") or "").strip())
                        item = {"asset": {"src": f}}
                        alt = _entry_alt(entry or {})
                        if alt:
                            item["alt"] = alt
                        items.append(item)
                    if items:
                        slot["copy"] = items
            # single / atomic-collage / masonry / icon-in-headline: the slot's own
            # (resolved) asset is the whole binding — semantics ride as data.
        if new_slots:
            sec["slots"] = list(slots) + new_slots
    return out


# ── the composed-lane lints (media-binding + AS-67 mark legality) ─────────────────────

def _slot_resolves(slot: dict, idx: dict[str, dict],
                   files: dict[str, dict]) -> bool:
    a = slot.get("asset")
    if isinstance(a, dict) and str(a.get("src") or "").strip():
        return True
    if isinstance(a, str) and a.strip():
        return True
    if slot.get("assetRef") and str(slot["assetRef"]).strip() in idx:
        return True
    mc = slot.get("mediaComposition")
    if isinstance(mc, dict):
        for layer in (mc.get("layers") or []):
            if not isinstance(layer, dict):
                continue
            if isinstance(layer.get("componentRef"), dict):
                continue
            if str(layer.get("assetRef") or "").strip() in idx:
                return True
    # a repeatable copy list whose items carry assets resolves the slot too
    c = slot.get("copy")
    if isinstance(c, list):
        for item in c:
            if isinstance(item, dict) and isinstance(item.get("asset"), (dict, str)):
                return True
    return False


def _section_has_attribution(sec: dict) -> bool:
    for slot in (sec.get("slots") or []):
        if not isinstance(slot, dict):
            continue
        payloads = []
        c = slot.get("copy")
        if isinstance(c, dict):
            payloads.append(c)
        elif isinstance(c, list):
            payloads += [it for it in c if isinstance(it, dict)]
        for p in payloads:
            if any(str(p.get(k) or "").strip() for k in _ATTRIBUTION_KEYS):
                return True
    return False


def _slot_refs(slot: dict) -> list[str]:
    """Every assetRef the slot binds (its own + mediaComposition layers + maskRef)."""
    refs: list[str] = []
    if slot.get("assetRef"):
        refs.append(str(slot["assetRef"]).strip())
    mc = slot.get("mediaComposition")
    if isinstance(mc, dict):
        if mc.get("maskRef"):
            refs.append(str(mc["maskRef"]).strip())
        for layer in (mc.get("layers") or []):
            if isinstance(layer, dict) and layer.get("assetRef"):
                refs.append(str(layer["assetRef"]).strip())
    return refs


def _bound_asset_entries(slot: dict, idx: dict[str, dict],
                         files: dict[str, dict]) -> list[dict]:
    """Every registry entry a slot actually binds — its own ``assetRef`` +
    ``asset.src`` filename, its ``mediaComposition`` layer refs, and any repeatable
    ``copy[]`` item assets (the card-grid/carousel item media channel). Deduped by
    id, in binding order. Unresolvable refs are skipped here (they fail loud in the
    media-binding rule already)."""
    out: list[dict] = []
    seen: set[str] = set()

    def _add(entry: dict | None) -> None:
        if isinstance(entry, dict):
            eid = str(entry.get("id") or id(entry))
            if eid not in seen:
                seen.add(eid)
                out.append(entry)

    for ref in _slot_refs(slot):
        _add(idx.get(ref))
    a = slot.get("asset")
    if isinstance(a, dict) and a.get("src"):
        _add(files.get(Path(str(a["src"])).name))
    elif isinstance(a, str) and a.strip():
        _add(files.get(Path(a).name))
    c = slot.get("copy")
    if isinstance(c, list):
        for item in c:
            if not isinstance(item, dict):
                continue
            ia = item.get("asset")
            if isinstance(ia, dict) and ia.get("src"):
                _add(files.get(Path(str(ia["src"])).name))
            elif isinstance(ia, str) and ia.strip():
                _add(files.get(Path(ia).name))
    return out


def lint_media_bindings(comp: dict, registry: dict | None) -> list[tuple[str, str, str]]:
    """[(section_id, rule, message)] — the composed-lane media lints. Registry None
    → [] (artifact-less brands are never flagged; the same fact-gating as every
    media consumer).

    rule ``media-binding``   — every media-bearing slot resolves an asset
        (``asset.src`` / ``assetRef`` / resolving mediaComposition layers / item
        assets) OR declares ``noCompatibleAsset {reason}``; every declared ref
        resolves into the registry; a declared placeholder names a LICENSED
        generatedVisuals id. Silent drops are the failure class (spec §6).
    rule ``mark-legality``   — AS-67: third-party marks only in factual proof
        contexts; testimonial marks require attribution copy; badge-role slots
        never fabricate (registry marks or a declared gap — a placeholder recipe
        cannot stand in for a badge).
    rule ``slot-role-eligibility`` — AS-80: asset-kind↔slot-role eligibility. An
        ICON/MARK-family asset (spot-icon/ui-glyph/social-icon/logo mark) is never
        bound into an IMAGE/hero-lead/full-bleed role, and never carries an explicit
        media-well fit (cover/contain) — a content-scale glyph must render at mark
        height, never blown up to fill a lead/hero image slot. An image role with
        no compatible image-family asset must declare its gap, not substitute an
        icon (spec §6.1)."""
    if not registry or not isinstance(comp, dict):
        return []
    idx = asset_index(registry)
    files = file_index(registry)
    gen_idx = generated_index(registry)
    hits: list[tuple[str, str, str]] = []

    for sec in (comp.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or sec.get("useCase") or "section")
        use_case = str(sec.get("useCase") or "").strip().lower()
        for slot in (sec.get("slots") or []):
            if not isinstance(slot, dict):
                continue
            sname = str(slot.get("name") or slot.get("role") or "slot")
            role_probe = f"{slot.get('name') or ''} {slot.get('role') or ''}"
            gap = slot.get("noCompatibleAsset")
            gap = gap if isinstance(gap, dict) else None

            # every declared ref must resolve
            for ref in _slot_refs(slot):
                if ref and ref not in idx:
                    hits.append((sid, "media-binding",
                                 f"slot `{sname}` binds assetRef `{ref}` which the "
                                 "brand's media-assets registry does not carry — "
                                 "bind a real id or declare noCompatibleAsset"))
            # declared gap hygiene
            if gap is not None:
                if not str(gap.get("reason") or "").strip():
                    hits.append((sid, "media-binding",
                                 f"slot `{sname}` declares noCompatibleAsset without "
                                 "a reason — the gap entry is what the asset-request "
                                 "manifest carries"))
                ph = str(gap.get("placeholder") or "").strip()
                if ph and ph not in gen_idx:
                    hits.append((sid, "media-binding",
                                 f"slot `{sname}` names placeholder recipe `{ph}` "
                                 "which is not in the brand's licensed "
                                 "generatedVisuals roster — a device must be "
                                 "licensed by measured evidence, never invented"))
                if ph and ph in gen_idx and _BADGE_ROLE_RE.search(role_probe):
                    hits.append((sid, "mark-legality",
                                 f"slot `{sname}` fills a badge/award/rating role "
                                 "with a generated placeholder recipe — badges are "
                                 "never fabricated (AS-67); bind a registry mark or "
                                 "leave the declared gap unfilled"))
            # silent drop: a media slot with nothing resolved and nothing declared
            if _is_media_slot(slot) and gap is None \
                    and not _slot_resolves(slot, idx, files):
                hits.append((sid, "media-binding",
                             f"media slot `{sname}` resolves NO asset and declares "
                             "no gap — bind an assetRef/real file or declare "
                             "noCompatibleAsset {reason} (silent placeholder = "
                             "failure, spec §6)"))

            # AS-67 mark legality for resolved third-party marks
            for ref in _slot_refs(slot):
                entry = idx.get(ref)
                if not entry or str(entry.get("usageRights") or "") != "third-party-mark":
                    continue
                in_proof_role = bool(_PROOF_ROLE_RE.search(role_probe))
                if use_case in ("logos", "footer") or in_proof_role:
                    continue
                if use_case == "testimonial":
                    if _section_has_attribution(sec):
                        continue
                    hits.append((sid, "mark-legality",
                                 f"slot `{sname}` binds third-party mark `{ref}` "
                                 "beside an UNATTRIBUTED quote — marks decorate "
                                 "factual, attributed proof only (AS-67)"))
                    continue
                hits.append((sid, "mark-legality",
                             f"slot `{sname}` binds third-party mark `{ref}` outside "
                             "a factual proof context (use-case "
                             f"`{use_case or '?'}`) — client/partner/press marks "
                             "belong in proof strips, not decoration (AS-67)"))
            # AS-80 asset-kind↔slot-role eligibility: an icon/mark-family asset must
            # never be bound as a card's hero/lead image or carry a media-well fit.
            slot_is_image_role = (str(slot.get("contract") or "").lower() == "image"
                                  or role_demands_image(role_probe))
            for entry in _bound_asset_entries(slot, idx, files):
                sem = entry.get("assetSemantics") \
                    if isinstance(entry.get("assetSemantics"), dict) else {}
                if not is_icon_family(sem.get("kind")):
                    continue
                ekind = str(sem.get("kind") or "").strip().lower()
                eid = str(entry.get("id") or "?")
                if slot_is_image_role:
                    hits.append((sid, "slot-role-eligibility",
                                 f"slot `{sname}` binds icon-family asset `{eid}` "
                                 f"({ekind}) into an image/hero-lead/full-bleed role "
                                 "— icons render at mark height, never as lead media; "
                                 "bind an image-family asset or declare "
                                 "noCompatibleAsset {requiredKind: <image kind>}"))
                    continue
                td = entry.get("treatmentDefaults") \
                    if isinstance(entry.get("treatmentDefaults"), dict) else {}
                efit = str(td.get("fit") or "").strip().lower()
                if efit in MEDIA_WELL_FITS:
                    hits.append((sid, "slot-role-eligibility",
                                 f"slot `{sname}` binds icon-family asset `{eid}` "
                                 f"({ekind}) with fit `{efit}` — a content-scale glyph "
                                 "stretched to a media well is a mis-scaled icon; an "
                                 "icon/mark asset must render `fit: mark`"))
            # fabricated badge via a raw invented src (registry-bearing brands):
            a = slot.get("asset")
            src_name = Path(str(a.get("src"))).name \
                if isinstance(a, dict) and a.get("src") else None
            if src_name and _BADGE_ROLE_RE.search(role_probe) \
                    and src_name not in files:
                hits.append((sid, "mark-legality",
                             f"slot `{sname}` fills a badge/award/rating role with "
                             f"`{src_name}`, which is not a registered third-party "
                             "mark — badges bind registry marks or declare the gap "
                             "(AS-67)"))
    return hits


# ── the ASSET-REQUEST MANIFEST (declared gaps → a per-lane artifact) ─────────────────

ASSET_REQUESTS_NAME = "asset-requests.json"


def collect_asset_requests(comp: dict) -> list[dict]:
    """Every declared gap in the composition → one manifest entry
    {section, slot, role, requiredKind, aspect, surface, reason, placeholder}."""
    out: list[dict] = []
    for sec in ((comp or {}).get("sections") or []):
        if not isinstance(sec, dict):
            continue
        sid = str(sec.get("id") or sec.get("useCase") or "section")
        for slot in (sec.get("slots") or []):
            if not isinstance(slot, dict):
                continue
            gap = slot.get("noCompatibleAsset")
            if not isinstance(gap, dict):
                continue
            out.append({
                "section": sid,
                "slot": str(slot.get("name") or "slot"),
                "role": str(slot.get("role") or ""),
                "requiredKind": str(gap.get("requiredKind") or ""),
                "aspect": str(gap.get("aspect") or slot.get("mediaAspect") or ""),
                "surface": str(gap.get("surface")
                               or sec.get("surfaceIntent") or ""),
                "reason": str(gap.get("reason") or ""),
                "placeholder": str(gap.get("placeholder") or "") or None,
            })
    return out


def write_asset_request_manifest(out_dir: Path | str, comp: dict) -> Path | None:
    """Emit ``asset-requests.json`` beside the render when the composition declares
    gaps; remove a stale manifest when it declares none (a repaired composition
    must not leave the previous attempt's requests behind). Returns the path
    written, else None."""
    out_dir = Path(out_dir)
    entries = collect_asset_requests(comp)
    path = out_dir / ASSET_REQUESTS_NAME
    if not entries:
        if path.exists():
            path.unlink()
        return None
    path.write_text(json.dumps({
        "schemaVersion": "asset-requests.v1",
        "note": ("Declared media gaps (media-assets-schema.md §6 ladder rung 2): "
                 "roles the brief needed and the brand's extracted inventory could "
                 "not serve. Source each asset (or extend extraction) and re-run."),
        "requests": entries,
    }, indent=1) + "\n")
    return path
