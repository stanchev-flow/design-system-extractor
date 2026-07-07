#!/usr/bin/env python3
"""curate_assets.py — build runs/remote/brand/assets/ from the local capture.

- Extracts the 12 inline customer-logo SVGs from the homepage logo wall
  (swiper duplicates removed) into assets/logos/customer-logo-NN.svg
  (renamed after visual identification).
- Copies curated webp/png assets from the saved _files dir with sanitized names.

Writes ONLY under runs/remote/brand/assets/. Source capture stays untouched.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent.parent
CAP = REPO / "screenshots" / "remote"
HTML = CAP / ("Remote — Global Employment Infrastructure _ EOR, Payroll & "
              "Compliance, Worldwide.html")
FILES = CAP / ("Remote — Global Employment Infrastructure _ EOR, Payroll & "
               "Compliance, Worldwide_files")
OUT = REPO / "runs" / "remote" / "brand" / "assets"

# curated copy list: (source filename in _files, sanitized destination name)
COPY = [
    # hero + narrative art
    ("new-global-employment-runs-on-remote-hero-homepage_english@2x.webp",
     "hero-globe-illustration.webp"),
    ("new-panel-inteligent-infrastructure-snippet-certified_english@2x.webp",
     "panel-infrastructure-ui-snippet.webp"),
    ("background-homepage-noise-grey-green-blue-top@2x.webp",
     "bg-noise-grey-green-blue-top.webp"),
    # image-grid card art (dark navy product cards)
    ("remote-mcp-blue-image-card@2x.webp", "card-mcp-agents.webp"),
    ("remote-integrations-image-card@2x.webp", "card-integrations.webp"),
    ("remote-api-first-by-design-image-card@2x.webp", "card-api-first.webp"),
    ("remote-reverse-tech@2x.webp", "card-customer-story-reverse-tech.webp"),
    ("cultivating-a-thriving-remote-first-culture-in-partnership-with-remote@2x.webp",
     "card-customer-story-culture.webp"),
    # testimonial avatars
    ("erik-sveen-home-project-profile-picture-blue-bg-new@2x.webp",
     "avatar-erik-sveen.webp"),
    ("luke-mckinlay-fountain-profile-picture-blue-bg@2x.webp",
     "avatar-luke-mckinlay.webp"),
    ("maria-shkaruppa-semrush-profile-picture-blue-bg@2x.webp",
     "avatar-maria-shkaruppa.webp"),
    ("marisol-jimenez-reverse-tech-profile-picture-blue-bg-new@2x.webp",
     "avatar-marisol-jimenez.webp"),
    # partner / certification logos (logo strip #2)
    ("logo_workday-certified-integration-big-color.webp", "logo-workday-certified.webp"),
    ("logo_gusto-big-color.webp", "logo-gusto.webp"),
    ("logo_bamboohr-big-color.webp", "logo-bamboohr.webp"),
    ("logo_personio-big-color.webp", "logo-personio.webp"),
    # G2 award badges (logo strip #3)
    ("1.g2-best-software-top-50-hr-products@2x.webp", "badge-g2-top50-hr.webp"),
    ("g2-best-software-top-100-hr-products@2x.webp", "badge-g2-top100-hr.webp"),
    ("4.g2-best-software-top-100-fastest-growing@2x.webp", "badge-g2-top100-fastest-growing.webp"),
    ("g2-best-software-top-100-global-sellers@2x.webp", "badge-g2-top100-global-sellers.webp"),
    ("g2-multi-country-payroll-leader@2x.webp", "badge-g2-payroll-leader.webp"),
    ("g2-global-employment-platforms-leader-gep@2x.webp", "badge-g2-gep-leader.webp"),
    # review-platform rating chips
    ("xxl-xl-g2-reviews-book-demo.webp", "rating-g2.webp"),
    ("xxl-xl-capterra-reviews-book-demo.webp", "rating-capterra.webp"),
    ("xxl-xl-trustpilot-reviews-book-demo.webp", "rating-trustpilot.webp"),
    # product icons (32px webp)
    ("employer-of-record-icon-product_32.webp", "icon-eor.webp"),
    ("global-payroll-icon-product_32.webp", "icon-global-payroll.webp"),
    ("contractor-management-icon-product_32.webp", "icon-contractor-management.webp"),
    ("contractor-of-record-icon-product_32.webp", "icon-contractor-of-record.webp"),
    ("peo-icon-product_32.webp", "icon-peo.webp"),
    ("051-check-star-stamp.webp", "icon-check-star-stamp.webp"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "logos").mkdir(exist_ok=True)

    copied = []
    for src, dst in COPY:
        s = FILES / src
        if not s.exists():
            print(f"MISSING {src}")
            continue
        shutil.copy2(s, OUT / dst)
        copied.append(dst)
    print(f"copied {len(copied)} curated files")

    soup = BeautifulSoup(HTML.read_text(errors="replace"), "html.parser")
    sp = soup.find("section", class_=re.compile("social-proof"))
    items = [it for it in sp.find_all(class_="social-proof-item")
             if "swiper-slide-duplicate" not in " ".join(it.get("class", []))]
    items.sort(key=lambda it: int(it.get("data-swiper-slide-index", "99")))
    n = 0
    for it in items:
        svg = it.find("svg")
        if svg is None:
            continue
        idx = it.get("data-swiper-slide-index", str(n))
        p = OUT / "logos" / f"customer-logo-{int(idx):02d}.svg"
        p.write_text(str(svg))
        n += 1
    print(f"extracted {n} inline customer-logo SVGs -> assets/logos/")


if __name__ == "__main__":
    main()
