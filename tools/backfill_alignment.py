#!/usr/bin/env python3
"""One-shot backfill (AS-18): declare explicit contentShape.alignment intent on every
standard-tier layout pattern. Inserts an `alignment:` line as the first key of each
pattern's contentShape block (comment-preserving text insertion, not a YAML re-dump).
Idempotent: a pattern that already carries contentShape.alignment is skipped."""
import re
import sys
from pathlib import Path

LP = Path(__file__).resolve().parent.parent / "brand_pipeline" / "contracts" / "layout-patterns"

# id -> the alignment declaration (brand-schema §4.4 spelling: value/counterweight/inheritance).
ASSIGN = {
    # hero
    "hero-centered-stack-on-media": "{ value: centered, inheritance: block-inherits }",
    "hero-split-media-copy": "{ value: left, counterweight: media, inheritance: per-slot-override }",
    "hero-ghostword-atmospheric": "{ value: left, counterweight: ghostword, inheritance: per-slot-override }",
    "card-over-portrait-statement": "{ value: centered, inheritance: block-inherits }",
    "boundary-straddle-headline": "{ value: left, counterweight: photo, inheritance: per-slot-override }",
    "framed-inset-monument": "{ value: left, counterweight: annotation, inheritance: per-slot-override }",
    "stepped-overlay-statement": "{ value: left, counterweight: support, inheritance: per-slot-override }",
    "type-behind-media-masthead": "{ value: centered, inheritance: block-inherits }",
    "tucked-headline-panorama": "{ value: left, counterweight: support, inheritance: per-slot-override }",
    "hero-fullbleed-scrimmed-overlay": "{ value: left, counterweight: media, inheritance: per-slot-override }",
    # about
    "about-two-column-media-copy": "{ value: left, counterweight: media, inheritance: per-slot-override }",
    "about-split-editorial-grid": "{ value: left, counterweight: cards, inheritance: per-slot-override }",
    "seam-straddle-portrait": "{ value: centered, inheritance: block-inherits }",
    "about-ghostword-editorial-run": "{ value: left, counterweight: ghostword, inheritance: per-slot-override }",
    # gallery
    "gallery-editorial-card-grid": "{ value: left, counterweight: media, inheritance: per-slot-override }",
    "gallery-square-card-run": "{ value: left, counterweight: media, inheritance: per-slot-override }",
    "gallery-logo-strip": "{ value: space-between, inheritance: per-slot-override }",
    "staggered-caption-columns-3": "{ value: left, counterweight: column-image, inheritance: per-slot-override }",
    "gallery-mosaic-with-overflow": "{ value: left, counterweight: media, inheritance: per-slot-override }",
    # features
    "features-split-feature": "{ value: left, counterweight: media, inheritance: per-slot-override }",
    "features-shared-light-run": "{ value: left, counterweight: label, inheritance: per-slot-override }",
    "features-icon-label-grid": "{ value: centered, inheritance: block-inherits }",
    "features-media-card-overlay": "{ value: left, counterweight: media, inheritance: per-slot-override }",
    # pricing
    "pricing-two-card-row": "{ value: centered, inheritance: block-inherits }",
    "pricing-toggle-intro-plan-cards": "{ value: centered, inheritance: block-inherits }",
    "pricing-editorial-two-column": "{ value: left, counterweight: offer, inheritance: per-slot-override }",
    # testimonial
    "testimonial-centered-quote-stack": "{ value: centered, inheritance: block-inherits }",
    "testimonial-horizontal-card-rail-carousel": "{ value: left, counterweight: quote, inheritance: per-slot-override }",
    # cta
    "cta-centered-inverse-cta": "{ value: centered, inheritance: block-inherits }",
    "cta-split-copy-cta": "{ value: left, counterweight: actions, inheritance: per-slot-override }",
    "cta-fullbleed-scrimmed-media": "{ value: centered, inheritance: block-inherits }",
    "cta-inline-form-pill": "{ value: space-between, inheritance: per-slot-override }",
    # footer
    "footer-link-column-grid": "{ value: left, counterweight: links, inheritance: per-slot-override }",
    "footer-inverse-closing-oversized-wordmark": "{ value: centered, inheritance: block-inherits }",
    "footer-compact-utility-bar": "{ value: space-between, inheritance: per-slot-override }",
}


# PROJECT tier: a brand's extracted layout-library.yaml, passed on argv (there is NO
# default — pointing a one-shot backfill at one specific brand's library by default is
# how cross-brand assumptions creep in). These declarations pin each extracted
# pattern's OWN anchor so the style layer's role defaults can never re-anchor a
# signature device (e.g. editorial-luxury's `testimonial: centered` role must not
# centre the portrait-collage quote, and its `features: left` role must not left-flip
# the centered ruled-list panels' headings).
PROJECT_ASSIGN = {
    "hero-display-over-staggered-media": "{ value: centered, inheritance: block-inherits }",
    "editorial-ghostword-collage": "{ value: left, counterweight: ghostword, inheritance: per-slot-override }",
    "features-flush-split-panel": "{ value: left, counterweight: opposite-panel, inheritance: per-slot-override }",
    # cta-underline-conversion-stack already declares { value: center } — skipped (idempotent)
    "gallery-fullbleed-counter-band": "{ value: edge-to-edge, inheritance: per-slot-override }",
    "about-anchored-statement": "{ value: left, counterweight: media, inheritance: per-slot-override }",
    "heritage-ghost-numerals-timeline": "{ value: left, counterweight: ghost-numerals, inheritance: per-slot-override }",
    "curator-quote-portrait-collage": "{ value: left, counterweight: portrait, inheritance: per-slot-override }",
    "visit-dual-panel-map": "{ value: left, counterweight: map-panel, inheritance: per-slot-override }",
    "features-staggered-caption-cards": "{ value: left, counterweight: staggered-grid, inheritance: per-slot-override }",
    "editorial-interlocking-inset": "{ value: left, counterweight: inset-media, inheritance: per-slot-override }",
    "pricing-ruled-list-panel": "{ value: centered, inheritance: block-inherits }",
    "schedule-ruled-list-panel": "{ value: centered, inheritance: block-inherits }",
    "faq-accordion-list": "{ value: centered, inheritance: block-inherits }",
    "logos-hairline-strip": "{ value: space-between, inheritance: per-slot-override }",
}


def backfill_project(path: Path) -> list[str]:
    """Same comment-preserving insertion for the project library's flat top-level list
    (`- id:` at col 0, `contentShape:` at 2, keys at 4)."""
    text = path.read_text()
    done = []
    for pid, decl in PROJECT_ASSIGN.items():
        m = re.search(rf"^- id: {re.escape(pid)}\n", text, re.M)
        if not m:
            continue
        nxt = re.search(r"^- id: ", text[m.end():], re.M)
        block_end = m.end() + (nxt.start() if nxt else len(text[m.end():]))
        block = text[m.end():block_end]
        cs = re.search(r"^  contentShape:\n", block, re.M)
        if not cs:
            continue
        if re.search(r"^    alignment:", block, re.M):
            done.append(pid)  # already declared — idempotent
            continue
        insert_at = m.end() + cs.end()
        text = text[:insert_at] + f"    alignment: {decl}\n" + text[insert_at:]
        done.append(pid)
    path.write_text(text)
    return done


def backfill(path: Path) -> list[str]:
    text = path.read_text()
    done = []
    for pid, decl in ASSIGN.items():
        m = re.search(rf"^  - id: {re.escape(pid)}\n", text, re.M)
        if not m:
            continue
        # the pattern block ends at the next `  - id:` or EOF
        nxt = re.search(r"^  - id: ", text[m.end():], re.M)
        block_end = m.end() + (nxt.start() if nxt else len(text[m.end():]))
        block = text[m.end():block_end]
        cs = re.search(r"^    contentShape:\n", block, re.M)
        if not cs:
            continue
        if re.search(r"^      alignment:", block, re.M):
            done.append(pid)  # already declared — idempotent
            continue
        insert_at = m.end() + cs.end()
        line = f"      alignment: {decl}\n"
        text = text[:insert_at] + line + text[insert_at:]
        done.append(pid)
    path.write_text(text)
    return done


def main():
    total = []
    for f in sorted(LP.glob("*.yaml")):
        if f.name == "index.yaml":
            continue
        done = backfill(f)
        if done:
            print(f"{f.name}: {', '.join(done)}")
        total += done
    missing = sorted(set(ASSIGN) - set(total))
    # project-tier library comes from argv ONLY (no brand-specific default path).
    proj_lib = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    proj_done = backfill_project(proj_lib) if (proj_lib and proj_lib.exists()) else []
    if proj_done:
        print(f"{proj_lib.name} (project): {', '.join(proj_done)}")
    if missing:
        print(f"NOT FOUND (check ids): {missing}", file=sys.stderr)
        return 1
    print(f"backfilled {len(total)} standard + {len(proj_done)} project patterns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
