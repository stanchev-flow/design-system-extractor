#!/usr/bin/env python3
"""harvest_font_faces.py — turn captured ``@font-face`` rules into a TYPOGRAPHY
AVAILABILITY fact.

``mine_css.py`` already dumps every parsed rule, ``@font-face`` included, into
``evidence/pages/*/css-rules.json`` — but nothing downstream ever read a ``src:``
URL, so a brand.yaml could declare a family that the pipeline had no way of
delivering and no record that it could not. A declared-but-undelivered face then
rendered as whatever generic the declaration happened to end in, silently.

This pass closes that hole. It is READ-ONLY over the evidence and DOWNLOADS
NOTHING: a discovered URL is recorded as evidence of where the face lives, never
fetched. Vendoring a face is a licensing decision (most retail webfonts are
licensed to one domain and may not be redistributed), so the harvester states
what it observed and leaves the substitution decision to the brand author.

Two documents come out of one pass:

  font-faces.json         every ``@font-face`` observed: family, weights, styles,
                          per-source URL/format/kind, which stylesheet it came
                          from, and whether the bytes were inline (data: URI).
  font-availability.json  the DELIVERY fact per declared family, cross-referenced
                          against the brand's own ``selfHostedFonts`` registry and
                          ``tokens.type`` families when a --brand-dir is given:
                          ``self-hosted`` | ``proxy-substituted`` | ``unavailable``,
                          each with the evidence that supports it.

The availability document is what makes "we cannot ship this face" an explicit,
reviewable fact instead of an invisible fallback. Adopting it is an authoring
step: ``--emit-brand-snippet`` writes the ``fontAvailability:`` block to paste
into brand.yaml (see brand_pipeline/spec/font-availability-schema.md).

Usage:
    ./venv/bin/python tools/extract/harvest_font_faces.py \
        --evidence runs/<brand>/brand/evidence [--brand-dir runs/<brand>/brand]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "font-availability.v1"

# Hosts that only ever serve openly licensed webfonts. Seeing one is positive
# evidence that a discovered face is redistributable; seeing anything else is NOT
# evidence of the opposite, so every other host is recorded with an unknown hint.
# This is deliberately a very short list: the harvester must not guess a license.
_OPEN_WEBFONT_HOSTS = {
    "fonts.gstatic.com": "google-fonts",
    "fonts.googleapis.com": "google-fonts",
}

_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)(?:\s*format\(\s*['\"]?([^'\")]+))?",
                     re.S)


def _iter_rule_files(evidence: Path) -> list[Path]:
    """Every ``css-rules.json`` under an evidence dir (per-page dirs included)."""
    if evidence.is_file():
        return [evidence]
    found = sorted(evidence.rglob("css-rules.json"))
    return found


def _decls(text: str) -> dict[str, str]:
    """Parse a declaration block, keeping the LAST value per property (CSS order).

    Declarations are split on ``;`` OUTSIDE parentheses. A naive split loses every
    inline face: a ``data:`` URI carries its own ``;`` separators, so ``src`` would be
    truncated to ``url(data:application/x-font-ttf`` and the face would look
    source-less."""
    out: dict[str, str] = {}
    depth, start, parts = 0, 0, []
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    for part in parts:
        prop, sep, value = part.partition(":")
        if sep and prop.strip():
            out[prop.strip().lower()] = value.strip()
    return out


def _sources(src_value: str) -> list[dict]:
    """Each ``url(...)`` in a ``src:`` declaration, classified by where it points.

    ``data`` — the bytes are inline in the stylesheet (icon fonts usually are);
    ``remote`` — an absolute URL, recorded with its host for provenance;
    ``relative`` — a path next to the stylesheet, i.e. a face the capture may
    already hold on disk."""
    out: list[dict] = []
    for _q, url, fmt in _URL_RE.findall(src_value or ""):
        url = url.strip()
        if not url:
            continue
        entry: dict = {"format": (fmt or "").strip().lower() or None}
        if url.lower().startswith("data:"):
            entry["kind"] = "data"
            entry["url"] = url[:64] + "…" if len(url) > 64 else url
            entry["bytesInline"] = True
        elif "://" in url or url.startswith("//"):
            host = urlsplit(url if "://" in url else "https:" + url).netloc.lower()
            entry["kind"] = "remote"
            entry["url"] = url
            entry["host"] = host
            if host in _OPEN_WEBFONT_HOSTS:
                entry["licenseHint"] = _OPEN_WEBFONT_HOSTS[host]
        else:
            entry["kind"] = "relative"
            entry["url"] = url
        out.append(entry)
    return out


def _family_name(value: str) -> str:
    v = (value or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    return v.strip()


def harvest_faces(rule_docs) -> list[dict]:
    """One row per observed ``@font-face``, deduped across pages that share a sheet.

    ``rule_docs`` is an iterable of ``(label, parsed css-rules.json)``."""
    by_key: dict[tuple, dict] = {}
    for label, doc in rule_docs:
        for row in (doc or {}).get("rules", []) or []:
            selector = str(row.get("selector") or "").strip()
            if not selector.lower().startswith("@font-face"):
                continue
            d = _decls(str(row.get("decls") or ""))
            family = _family_name(d.get("font-family", ""))
            if not family:
                continue
            weight = (d.get("font-weight") or "400").strip()
            style = (d.get("font-style") or "normal").strip()
            srcs = _sources(d.get("src", ""))
            key = (family, weight, style, tuple(s.get("url", "") for s in srcs))
            face = by_key.setdefault(key, {
                "family": family,
                "weight": weight,
                "style": style,
                "display": (d.get("font-display") or "").strip() or None,
                "unicodeRange": (d.get("unicode-range") or "").strip() or None,
                "sources": srcs,
                "seenIn": [],
            })
            for where in (label, str(row.get("file") or "")):
                if where and where not in face["seenIn"]:
                    face["seenIn"].append(where)
    return sorted(by_key.values(),
                  key=lambda f: (f["family"].lower(), str(f["weight"]), f["style"]))


def group_families(faces: list[dict]) -> list[dict]:
    """Collapse observed faces into one availability row per family."""
    out: dict[str, dict] = {}
    for face in faces:
        fam = out.setdefault(face["family"], {
            "family": face["family"],
            "weights": [],
            "styles": [],
            "sourceKinds": [],
            "hosts": [],
            "urls": [],
            "licenseHint": None,
            "bytesInline": False,
            "faceCount": 0,
        })
        fam["faceCount"] += 1
        for key, value in (("weights", str(face["weight"])), ("styles", face["style"])):
            if value not in fam[key]:
                fam[key].append(value)
        for src in face["sources"]:
            if src["kind"] not in fam["sourceKinds"]:
                fam["sourceKinds"].append(src["kind"])
            if src.get("host") and src["host"] not in fam["hosts"]:
                fam["hosts"].append(src["host"])
            if src["kind"] == "remote" and src["url"] not in fam["urls"]:
                fam["urls"].append(src["url"])
            if src.get("bytesInline"):
                fam["bytesInline"] = True
            if src.get("licenseHint") and not fam["licenseHint"]:
                fam["licenseHint"] = src["licenseHint"]
    return sorted(out.values(), key=lambda f: f["family"].lower())


def _load_brand(brand_dir: Path | None):
    if not brand_dir:
        return None
    path = Path(brand_dir) / "brand.yaml"
    if not path.is_file():
        return None
    import yaml  # noqa: PLC0415 — only needed when a brand dir is supplied

    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else None


def _delivery_rows(doc: dict, brand_dir: Path) -> list[dict]:
    """The canonical delivery decision, taken from the ONE place that also builds the
    font stacks (``tokens_css.typography_delivery``) so evidence and render agree."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "brand_pipeline"))
    import tokens_css as tc  # noqa: PLC0415

    return tc.typography_delivery(doc, brand_dir)


def build_availability(faces: list[dict], brand_doc: dict | None,
                       brand_dir: Path | None) -> dict:
    """The availability fact: what the capture proves exists, crossed with what the
    brand can actually deliver.

    ``observed`` is pure evidence and needs no brand. ``declared`` needs one: it is
    the per-family delivery outcome, annotated with whether the capture even found a
    ``@font-face`` for that family and where its bytes live."""
    observed = group_families(faces)
    by_family = {f["family"].lower(): f for f in observed}
    out: dict = {
        "schemaVersion": SCHEMA,
        "observed": observed,
        "faces": faces,
    }
    if not brand_doc or brand_dir is None:
        return out
    declared = []
    for row in _delivery_rows(brand_doc, brand_dir):
        found = by_family.get(str(row.get("family", "")).lower())
        entry = dict(row)
        entry["capturedFontFace"] = bool(found)
        if found:
            entry["capturedWeights"] = found["weights"]
            entry["capturedStyles"] = found["styles"]
            entry["capturedSourceKinds"] = found["sourceKinds"]
            entry["capturedUrls"] = found["urls"]
            entry["licenseHint"] = found["licenseHint"]
        declared.append(entry)
    out["declared"] = declared
    out["summary"] = {
        "observedFamilies": len(observed),
        "declaredFamilies": len({d["family"] for d in declared}),
        "selfHosted": sorted({d["family"] for d in declared
                              if d.get("status") == "self-hosted"}),
        "proxySubstituted": sorted({d["family"] for d in declared
                                    if d.get("status") == "proxy-substituted"}),
        "unavailable": sorted({d["family"] for d in declared
                               if d.get("status") == "unavailable"}),
        "discoverableButNotVendored": sorted({
            d["family"] for d in declared
            if d.get("status") != "self-hosted" and d.get("capturedUrls")}),
    }
    return out


def brand_snippet(availability: dict) -> str:
    """The ``fontAvailability:`` block to paste into brand.yaml — the authored record
    that a declared face is substituted or knowingly missing. Emitted as text rather
    than written into brand.yaml: which faces a project may ship is a human call."""
    lines = ["# Generated by tools/extract/harvest_font_faces.py — review before adopting.",
             "# Records how each declared type family is delivered. A family listed as",
             "# 'unavailable' or 'proxy-substituted' is a KNOWN replica gap, not a bug.",
             "fontAvailability:"]
    seen: set[str] = set()
    for row in availability.get("declared", []) or []:
        family = row.get("family", "")
        if family in seen:
            continue
        seen.add(family)
        roles = sorted({r for other in availability["declared"]
                        if other.get("family") == family
                        for r in (other.get("roles") or [])})
        lines.append(f"  - family: {json.dumps(family)}")
        lines.append(f"    status: {row.get('status', 'unavailable')}")
        if row.get("proxy"):
            lines.append(f"    substitutedBy: {json.dumps(row['proxy'])}")
        lines.append(f"    capturedFontFace: {str(bool(row.get('capturedFontFace'))).lower()}")
        if roles:
            lines.append(f"    roles: [{', '.join(roles)}]")
        for url in (row.get("capturedUrls") or [])[:4]:
            lines.append(f"    # discovered (not fetched): {url}")
        lines.append(f"    licenseHint: {json.dumps(row.get('licenseHint'))}")
        if row.get("note"):
            lines.append(f"    note: {json.dumps(row['note'])}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence", type=Path, required=True,
                    help="evidence dir (scanned for css-rules.json) or one such file")
    ap.add_argument("--brand-dir", type=Path,
                    help="brand dir holding brand.yaml + assets/fonts/ (enables the "
                         "declared-family delivery cross-reference)")
    ap.add_argument("--out-dir", type=Path,
                    help="where to write the documents (default: --evidence dir)")
    ap.add_argument("--emit-brand-snippet", action="store_true",
                    help="also write font-availability.brand-snippet.yaml")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    rule_files = _iter_rule_files(args.evidence)
    if not rule_files:
        raise SystemExit(f"no css-rules.json found under {args.evidence} — run mine_css.py first")

    docs = []
    for path in rule_files:
        try:
            docs.append((path.parent.name, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError) as exc:
            print(f"  [skip] {path}: {exc}")
    faces = harvest_faces(docs)
    brand_doc = _load_brand(args.brand_dir)
    availability = build_availability(faces, brand_doc, args.brand_dir)

    out_dir = args.out_dir or (args.evidence if args.evidence.is_dir()
                               else args.evidence.parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "font-faces.json").write_text(
        json.dumps({"schemaVersion": SCHEMA, "faces": faces}, indent=1) + "\n",
        encoding="utf-8")
    (out_dir / "font-availability.json").write_text(
        json.dumps(availability, indent=1) + "\n", encoding="utf-8")
    if args.emit_brand_snippet:
        (out_dir / "font-availability.brand-snippet.yaml").write_text(
            brand_snippet(availability), encoding="utf-8")

    summary = availability.get("summary") or {}
    print(f"[done] font-faces: {len(faces)} @font-face rules across "
          f"{len(rule_files)} evidence file(s); "
          f"{summary.get('observedFamilies', len(group_families(faces)))} families observed")
    for key in ("selfHosted", "proxySubstituted", "unavailable",
                "discoverableButNotVendored"):
        if summary.get(key):
            print(f"  {key}: {', '.join(summary[key])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
