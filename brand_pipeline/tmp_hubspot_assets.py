#!/usr/bin/env python3
"""One-off: re-derive HubSpot assets-tagged.{json,md} from the REAL saved _files/.

NOT part of the spine. Reads the locally saved "Save Page As, Complete" asset
directory, classifies each real image by use-case + intended slot + section, and
writes runs/hubspot/brand/assets-tagged.json (+ .md projection).
"""
import json
import re
import struct
from pathlib import Path

FILES = Path("screenshots/hubspot/HubSpot/HubSpot _ Software & Tools for your Business - Homepage_files")
OUT_JSON = Path("runs/hubspot/brand/assets-tagged.json")
OUT_MD = Path("runs/hubspot/brand/assets-tagged.md")

IMG_EXT = {".svg", ".png", ".webp", ".jpg", ".jpeg", ".gif"}


def dims(p: Path):
    """Best-effort (width, height) for common formats; None if unknown."""
    try:
        if p.suffix.lower() == ".svg":
            t = p.read_text(errors="ignore")[:2000]
            w = re.search(r'width="([\d.]+)', t)
            h = re.search(r'height="([\d.]+)', t)
            if w and h:
                return int(float(w.group(1))), int(float(h.group(1)))
            vb = re.search(r'viewBox="[\d.]+ [\d.]+ ([\d.]+) ([\d.]+)', t)
            if vb:
                return int(float(vb.group(1))), int(float(vb.group(2)))
            return None
        b = p.read_bytes()
        if p.suffix.lower() == ".png" and len(b) > 24:
            w, h = struct.unpack(">II", b[16:24])
            return w, h
        if p.suffix.lower() in (".jpg", ".jpeg"):
            i = 2
            while i < len(b) - 9:
                if b[i] != 0xFF:
                    i += 1
                    continue
                m = b[i + 1]
                if m in (0xC0, 0xC1, 0xC2, 0xC3):
                    h, w = struct.unpack(">HH", b[i + 5:i + 9])
                    return w, h
                seg = struct.unpack(">H", b[i + 2:i + 4])[0]
                i += 2 + seg
            return None
        if p.suffix.lower() == ".webp" and len(b) > 30 and b[:4] == b"RIFF":
            fmt = b[12:16]
            if fmt == b"VP8 ":
                w = struct.unpack("<H", b[26:28])[0] & 0x3FFF
                h = struct.unpack("<H", b[28:30])[0] & 0x3FFF
                return w, h
            if fmt == b"VP8L":
                bb = b[21:25]
                n = struct.unpack("<I", bb)[0]
                w = (n & 0x3FFF) + 1
                h = ((n >> 14) & 0x3FFF) + 1
                return w, h
            if fmt == b"VP8X":
                w = (b[24] | (b[25] << 8) | (b[26] << 16)) + 1
                h = (b[27] | (b[28] << 8) | (b[29] << 16)) + 1
                return w, h
            return None
    except Exception:
        return None
    return None


# (filename-substring matcher, useCase, intendedSlot, section, label) — order matters.
RULES = [
    ("HS_Full_Bleed", "background-photo", "hero full-bleed background (dark scrim, no blur)", "hero", "Hero full-bleed photo"),
    ("Customer Platform Graphic", "product-graphic", "customer-platform carousel product graphic", "customer-platform", "Customer Platform graphic"),
    ("customer-platform-graphic", "product-graphic", "customer-platform carousel product graphic", "customer-platform", "Customer Platform graphic (Breeze)"),
    ("Why Choose HubSpot", "product-graphic", "customer-platform supporting graphic", "customer-platform", "Why Choose HubSpot"),
    ("ProductIcons_", "feature-icon", "product-hub card icon (orange)", "product-platform", "Product hub icon"),
    ("-hub.svg", "feature-icon", "product-hub icon (nav/card)", "product-platform", "Product hub icon"),
    ("smart-crm", "feature-icon", "product-hub icon (Smart CRM)", "product-platform", "Smart CRM icon"),
    ("small-business.svg", "feature-icon", "product-hub icon (small business)", "product-platform", "Small Business icon"),
    ("app-marketplace", "feature-icon", "product-hub icon (app marketplace)", "product-platform", "App Marketplace icon"),
    ("Breeze", "feature-icon", "breeze AI agent glyph", "breeze-agents-carousel", "Breeze symbol"),
    ("AI Sparkle", "feature-icon", "breeze AI sparkle glyph", "breeze-agents-carousel", "AI Sparkle"),
    ("agent-en", "product-graphic", "breeze agent UI preview", "breeze-agents-carousel", "Breeze agent preview"),
    ("Chat_Bot", "feature-icon", "breeze chatbot glyph", "breeze-agents-carousel", "Breeze chatbot"),
    ("doordash", "logo-wall-logo", "customer trust logo", "logo-carousel", "DoorDash"),
    ("ebay", "logo-wall-logo", "customer trust logo", "logo-carousel", "eBay"),
    ("eventbrite", "logo-wall-logo", "customer trust logo", "logo-carousel", "Eventbrite"),
    ("tripadvisor", "logo-wall-logo", "customer trust logo", "logo-carousel", "Tripadvisor"),
    ("reddit", "logo-wall-logo", "customer trust logo", "logo-carousel", "Reddit"),
    ("Unipart", "logo-wall-logo", "customer trust logo", "logo-carousel", "Unipart"),
    ("angel-FC", "logo-wall-logo", "customer trust logo", "logo-carousel", "Angel FC"),
    ("youth-on-course", "logo-wall-logo", "customer trust logo", "logo-carousel", "Youth on Course"),
    ("gmail", "integration-logo", "integration partner logo", "integrations-rotating", "Gmail"),
    ("slack", "integration-logo", "integration partner logo", "integrations-rotating", "Slack"),
    ("shopify", "integration-logo", "integration partner logo", "integrations-rotating", "Shopify"),
    ("mailchimp", "integration-logo", "integration partner logo", "integrations-rotating", "Mailchimp"),
    ("zapier", "integration-logo", "integration partner logo", "integrations-rotating", "Zapier"),
    ("google-ads", "integration-logo", "integration partner logo", "integrations-rotating", "Google Ads"),
    ("commerce-hub", "feature-icon", "integration/product glyph", "integrations-rotating", "Commerce Hub"),
    ("aeo.svg", "feature-icon", "integration/product glyph", "integrations-rotating", "AEO"),
    # award badges first — names contain 'enterprise'/'small-business' which would
    # otherwise be mis-caught by the testimonial rules below.
    ("badge-", "award-badge", "G2 award badge", "badges", "G2 award badge"),
    ("bagde-", "award-badge", "G2 award badge", "badges", "G2 award badge"),
    ("best-relationships", "award-badge", "G2 award badge", "badges", "G2 award badge"),
    ("best-support", "award-badge", "G2 award badge", "badges", "G2 award badge"),
    ("Enterprise.webp", "testimonial-avatar", "case-study tab image (Enterprise)", "case-studies-tabbed", "Enterprise case study"),
    ("Small Businesses", "testimonial-avatar", "case-study tab image (Small Business)", "case-studies-tabbed", "Small Business case study"),
    ("Case Studies", "testimonial-avatar", "case-study tab image", "case-studies-tabbed", "Case studies"),
    ("spotlight_resized", "testimonial-avatar", "case-study spotlight image", "case-studies-tabbed", "Case study spotlight"),
    ("app store high res", "app-badge", "app-store download badge", "footer", "App Store badge"),
    ("google play high res", "app-badge", "app-store download badge", "footer", "Google Play badge"),
]

LEGEND = {
    "background-photo": "Full-bleed photographic backgrounds (hero dark-scrim, no blur).",
    "product-graphic": "Colorful product/platform graphics for customer-platform & breeze carousels.",
    "feature-icon": "Orange product-hub / Breeze / integration glyphs for cards and bullets.",
    "logo-wall-logo": "Monochrome customer trust logos for the logo carousel.",
    "integration-logo": "Colorful integration partner logos for the rotating-SVG strip.",
    "testimonial-avatar": "Customer/case-study photos for the tabbed testimonials.",
    "award-badge": "G2 award badges for the badges proof section.",
    "app-badge": "App-store download badges (footer).",
    "logo": "HubSpot brand wordmark/mark (nav, footer).",
    "decorative": "Uncategorized decorative imagery.",
}

SECTION_INDEX = {
    "nav": 0, "hero": 1, "logo-carousel": 2, "customer-platform": 3, "product-platform": 4,
    "breeze-agents-carousel": 5, "integrations-rotating": 6, "results-header": 7,
    "case-studies-tabbed": 8, "badges": 9, "elevated-cta": 10, "footer": 11,
}


def classify(name: str):
    for sub, uc, slot, sect, label in RULES:
        if sub.lower() in name.lower():
            return uc, slot, sect, label
    return None


def main():
    assets = []
    counts = {}
    for p in sorted(FILES.iterdir()):
        if p.suffix.lower() not in IMG_EXT:
            continue
        c = classify(p.name)
        if not c:
            continue  # skip tracking pixels / uncategorized chrome
        uc, slot, sect, label = c
        wh = dims(p)
        counts[uc] = counts.get(uc, 0) + 1
        assets.append({
            "filename": p.name,
            "useCase": uc,
            "intendedSlot": slot,
            "label": label,
            "mimeType": f"image/{'svg+xml' if p.suffix.lower()=='.svg' else p.suffix.lower().lstrip('.')}",
            "width": wh[0] if wh else None,
            "height": wh[1] if wh else None,
            "sizeBytes": p.stat().st_size,
            "appearsInSections": [SECTION_INDEX.get(sect, -1)],
            "sectionLabels": [sect],
        })

    doc = {
        "schemaVersion": 2,
        "source": str(FILES),
        "note": ("Re-derived from the local 'Save Page As, Complete' capture (real _files/ assets), "
                 "tagged with use-case + intended slot + section. Referenced by brand.yaml (indexes.assetsTagged). "
                 "Hero background is a dark-scrim full-bleed photo (NO blur)."),
        "useCaseLegend": LEGEND,
        "counts": dict(sorted(counts.items())),
        "total": len(assets),
        "assets": sorted(assets, key=lambda a: (a["appearsInSections"][0], a["useCase"], a["filename"])),
    }
    OUT_JSON.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    # markdown projection
    md = ["# assets-tagged.md — HubSpot (re-derived from saved _files/)", "",
          "> Generated from `assets-tagged.json`. Source: local Save-Page-As capture. "
          "Hero background = dark-scrim full-bleed photo, NO blur.", "",
          f"**{len(assets)} tagged assets** across {len({a['sectionLabels'][0] for a in assets})} sections.", "",
          "## Counts by use-case", ""]
    for uc, n in sorted(counts.items()):
        md.append(f"- `{uc}` ({n}): {LEGEND.get(uc,'')}")
    md += ["", "## Assets by section", ""]
    by_sect = {}
    for a in doc["assets"]:
        by_sect.setdefault(a["sectionLabels"][0], []).append(a)
    for sect in sorted(by_sect, key=lambda s: SECTION_INDEX.get(s, 99)):
        md.append(f"### {sect}")
        md.append("")
        md.append("| asset | use-case | slot | dims |")
        md.append("|---|---|---|---|")
        for a in by_sect[sect]:
            d = f"{a['width']}×{a['height']}" if a['width'] else "—"
            md.append(f"| `{a['filename']}` | {a['useCase']} | {a['intendedSlot']} | {d} |")
        md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"Wrote {OUT_JSON} ({len(assets)} assets)")
    print(f"Wrote {OUT_MD}")
    print("counts:", doc["counts"])


if __name__ == "__main__":
    main()
