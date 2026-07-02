# anti-ai-slop.md — a growing checklist of generation-quality failures

> **Status: living document.** This is NOT a one-time spec — it grows every time a real
> quality bug is caught in this pipeline's generated output. Add a new entry (next `AS-NN`
> id) whenever you fix something that fits the pattern below; do not just fix the instance
> and move on. The point is to stop paying for the SAME class of mistake twice.

## What counts as "AI slop" here

Not "the design looks bad" — that's covered by `brand-schema.md`'s `neverDo`/`do`/`avoid`
rules and `onbrand_check.py`. **Slop is a specific failure shape**: code that looks
plausible, compiles, and even renders *something*, but was generated without actually
reasoning about the CONTEXT it runs in — the surface it paints on, the container it sits
in, the viewport range it has to survive, or the sibling it shares a box with. It is
generic-looking because it ignores context that a careful human would have checked. Every
entry below follows the same shape: **a value or mechanism that "looks right" in one
narrow case and silently breaks outside it.**

## How to use this

1. Before calling a render "done", skim the rule list below against what you just built.
2. When `onbrand_check.py` passes but the output still looks wrong, look here first — most
   slop is invisible to a brand-rule checker because it's not a brand violation, it's a
   context-blindness bug (onbrand_check verifies *values*, not *whether a value adapts
   correctly to where it's used*).
3. When you catch a NEW instance of this shape, add a rule. Reuse an existing `AS-NN` if
   it's the same class; only add a new id for a genuinely new failure shape.
4. Prefer a **scriptable verification** for every rule (a computed-style check, a geometry
   check, a grep) over "look at a screenshot" — screenshots miss things reliably (see
   AS-01's own history: it rendered "fine" in single-section previews for weeks).

---

## AS-01 — Context-blind color tokens (dark-on-dark / light-on-light)

**Rule**: never resolve a color for an element without knowing which SURFACE it renders
on. A token name like `border/hairline-on-primary` is not automatically safe just because
it resolves to a valid hex — it may have been extracted for ONE surface tier and reused
unconditionally on every other tier.

**Why it happens**: a single global CSS var (`--c-hairline`) gets set ONE way per document
and every section reads it, without a per-surface branch. It's the same shape as `--c-ink`/
`--c-ink-muted`/`--c-accent`, which usually DO branch correctly by surface — it's easy to
add a new token and forget to give it the same branch.

**Caught here**: the exhibition schedule/visit ruled-row dividers used
`border/hairline-on-primary` (`rgba(31,26,20,0.30)`, a near-black line meant for the cream
surface) unconditionally, including on the dark `surface/inverse` band — a near-invisible
dark line on a dark-brown background.

**Verify**: for every color CSS var used inside a component that's shared across surfaces,
render the component on BOTH a light and a dark surface instance and diff the resolved
`--c-*` value. A var that resolves to the SAME value on both surfaces is suspect unless the
brand genuinely has only one value for it (rare for anything meant to read as "hairline"/
"muted"/"border").

---

## AS-02 — Fallback chains that never fire (truthy-string traps)

**Rule**: a `value_a or fallback` pattern only works if `value_a` is genuinely falsy
(`None`, `""`, `0`) when it should fall through. Never assume a helper function returns
`None` on failure without checking — some return the INPUT unchanged as a pass-through for
a different valid use case, which is truthy and silently defeats the `or`.

**Why it happens**: `color_value(doc, token)` is designed so a caller can pass either a
token NAME (resolved via lookup) or a raw hex value (returned as-is) — a legitimate,
intentional dual-purpose. But a caller doing `color_value(doc, "some-token") or fallback`
to detect "token missing" breaks silently, because a missing token still returns the input
STRING (the token name itself), which is truthy.

**Caught here**: attempting to fix AS-01, `color_value(doc, "border/hairline-on-inverse")
or muted` never fell through to `muted` because the token didn't exist and the function
returned the literal string `"border/hairline-on-inverse"` — which then got written
directly into the CSS as `--c-hairline: border/hairline-on-inverse;`, an invalid color
value, so the browser dropped the whole custom property to its initial value
(`transparent`). The bug LOOKED like a missing-fallback bug but was actually a
worse-than-missing bug: a plausible-looking but entirely broken CSS declaration.

**Verify**: for any `x = helper(...) or fallback` pattern, check what `helper` actually
returns on the "not found" path — read the function, don't assume. Prefer checking
existence directly (`token in known_set`) over relying on a return value's truthiness when
the helper has more than one calling convention.

---

## AS-03 — Arbitrary spacing literals disconnected from actual geometry

**Rule**: a spacing value (padding, margin, a spacer element's height) that exists to clear
another element's overlap/bleed must be DERIVED from that element's actual offset — not a
round number picked because it "looked about right" at one test viewport.

**Why it happens**: computing the exact clearance needs geometry (aspect ratios, percentage
offsets compounding through a chain of ancestors) that's genuinely fiddly, so a rounder,
bigger number gets picked "to be safe" — and then never gets revisited once it renders
without obviously overlapping anything.

**Caught here**: `.cs-spacer { height: 22cqw; }` existed purely to clear the hero's overlap
image (`bottom: -28%` on a 34%-wide, 785:620 image inside a 1355:570 collage). The actual
geometrically-needed clearance is ~11.7% of the collage's own width (worked from the
overlap image's real offset) — the `22cqw` value was roughly 2× too generous even before
accounting for AS-04 below.

**Verify**: when you find a spacer/gap that exists "to clear" a specific overlapping
element, do the arithmetic (offset % × contributing dimension) instead of eyeballing it.
If the exact number is inconvenient, snap to the nearest STYLE spacing-scale step
(`StyleStructure.space_scale`) rather than an arbitrary literal — reuse the scale, don't
invent a new number outside it.

---

## AS-04 — Container-relative units measured against the wrong container

**Rule**: a `cq*`/`%` unit resolves against its NEAREST ancestor with the matching
container context — verify that ancestor is actually the box you intend, especially when
the intended reference box (e.g. a width-capped collage) is a SIBLING, not an ancestor, of
the element using the unit.

**Why it happens**: it's easy to reason "this value is 22% of the relevant box" while
writing the number, without checking that the CSS containing-block chain the browser will
actually use matches that mental model.

**Caught here**: `.cs-spacer`'s `22cqw` was intended to scale with the hero collage
(`.cs-collage`, `max-width: 80rem`), but `.cs-spacer` is a SIBLING of `.cs-collage` (both
children of `.cs-slot`), so its `cqw` resolved against `.cs-slot`'s full, UNCAPPED width —
meaning the spacer kept growing on wide viewports even after the collage itself stopped
growing at its 80rem cap. At a 2400px viewport this alone accounted for most of the
"too large" complaint (528px computed vs. ~150px actually needed).

**Verify**: for any `cq*` unit, trace the actual DOM ancestor chain to the nearest
`container-type` context (or, without an explicit container, the true block containing it)
— don't assume it matches whichever sibling element "feels like" the reference. When the
intended reference box is a sibling, either nest the element inside it, or cap the value
with `clamp()` so the upper bound does the real capping work regardless of which container
the mid-term resolves against.

---

## AS-05 — Absolute positioning against the wrong ancestor (content drift)

**Rule**: an absolutely-positioned decorative element (a ghost watermark, a floating badge)
must be positioned relative to the SAME box as the content it's meant to overlap — not a
wider ancestor that happens to look aligned at one viewport width.

**Why it happens**: the decorative element and the "real" content often start as siblings
under the same section wrapper, and at typical preview widths their edges roughly line up
by coincidence, hiding the fact that they're anchored to different boxes.

**Caught here**: the editorial-collage/heritage-timeline ghost watermark (`.cs-ghost`) was
positioned `right: -3cqw` relative to the full-bleed `.cs-collage-sec`, while the actual
content (`.cs-collage-grid`) was separately capped at `max-width: 86rem` and centered. On
a wide viewport the content shrank toward the center while the ghost stayed anchored to the
section's outer edge, so they visibly drifted apart — the ghost ended up floating in the
empty margin instead of behind the heading it was meant to shadow.

**Verify**: when a decorative absolutely-positioned element is meant to align with a
sibling's content box, check they share the SAME positioned ancestor. If the content box is
narrower than the section (has its own `max-width` + `margin: auto`), nest the decorative
element inside that same box rather than leaving it as an outer sibling.

---

## AS-06 — Hand-duplicated logic across two code paths

**Rule**: when the same concept (a CSS rule set, a style override, a registry of
special-case scaffolds) is needed by two different assembly paths (a single-item preview
and a full-page/batch assembly), it must be read from ONE shared source — never
re-declared as a second, hand-maintained copy "for now."

**Why it happens**: the second path often gets built by copy-adapting the first, which is
fast and works at the time — but nobody goes back to the first copy every time the second
is edited (or vice versa), so they drift silently, and only one of the two paths shows the
bug.

**Caught here THREE separate times** in this session, always between `compose_section.py`
(single-section) and `compose_page.py` (full-page):
1. `.cs-conversion`'s centering override existed in `compose_section.style_override_css`
   but a second, independently-maintained copy in `compose_page.page_style_override` still
   listed `.cs-conversion` in its left-anchor selector group — silently re-breaking
   centering only on the full page, not the single-section preview.
2. `_LAYOUT_SCAFFOLD_EXTRA` (the id→CSS lookup for section-specific scaffold geometry) was
   keyed only by literal layout id; a NEW layout reusing an EXISTING pattern under a
   different id got the right composer markup but none of the matching CSS.
3. `page_scaffold_css()` built its full-page stylesheet from its OWN hardcoded `parts` list
   of scaffold CSS blocks — when two new scaffolds (`SCAFFOLD_RULEDLIST_CSS`,
   `SCAFFOLD_FAQ_CSS`) were added to `compose_section.py`, they rendered correctly in
   single-section previews but were completely absent from the full page, because nobody
   remembered to also add them to this second list.

**Fix pattern**: create ONE canonical registry/function in the module that owns the
concept, and have BOTH assembly paths import and read from it. See
`compose_section._LAYOUT_ID_SCAFFOLD` + `_primary_scaffold_for` for the pattern this
resolved into (issue #3 above) — both `scaffold_css()` and `compose_page.page_scaffold_css`
now read the same dict; nothing is hand-copied.

**Verify**: grep for the concept's name/selector across BOTH `compose_section.py` and
`compose_page.py`. If it appears as two separate literal definitions rather than one
definition + one import, that's the bug waiting to happen.

---

## AS-07 — Dispatch keyed to a literal id instead of the reusable identity

**Rule**: when routing to a composer/handler based on "which section is this," dispatch on
the REUSABLE identity (a `patternRef.id`) first, falling back to the literal instance id
only when no reusable identity exists — never dispatch on the literal id alone.

**Why it happens**: the very first instance of a pattern is usually built and dispatched
by its own literal id (`if layout.id == "curator-quote": ...`), which works fine until the
whole POINT of the pattern library — reusing that exact pattern under a NEW instance id
(`exhibition-curator-quote`) — actually happens, and the id-only check doesn't recognize it.

**Caught here**: `compose_stack`/`compose_collage`/`compose_split`'s archetype dispatchers,
and the scaffold-CSS lookup, were all keyed to the literal WoodWave section ids
(`"curator-quote"`, `"heritage-timeline"`, ...). Adding `exhibition-curator-quote` (which
reuses the `curator-quote-portrait-collage` pattern) crashed, because none of the id checks
matched and it fell through to the wrong composer (`compose_info_band`, expecting fields
this layout never set).

**Fix pattern**: `_pattern_id(layout)` reads `layout.patternRef.id`; every dispatcher checks
`pid == "<pattern-id>" or lid == "<legacy-literal-id>"`, preferring the pattern id.

**Verify**: for every `if layout_id == "...":` dispatch branch, ask "if I added a NEW
layout instance that reuses this exact pattern under a different id, would this still
route correctly?" If no, it needs the `patternRef.id` check added.

---

## AS-08 — `max-width`-capped containers with no centering, defaulting to flush-left

**Rule**: any element with `max-width` set (to cap line length or content width on wide
viewports) needs an explicit centering mechanism (`margin: 0 auto`, or a flex parent with
`justify-content: center`) — a `max-width` alone does nothing to the element's own
position; it defaults to flush against its containing block's start edge.

**Why it happens**: `max-width` reads, in isolation, like "this constrains and centers the
content" — it only constrains. Centering is a separate declaration that's easy to forget,
especially when the element renders correctly-looking in a NARROW preview where there's
little or no slack width for the missing centering to be visible in.

**Caught here TWICE**: (1) `.cs-quote-grid`/`.cs-statement-grid`/`.cs-visit-panels` all had
`max-width: 86rem` with no `margin: auto`, leaving a large dead void on the right on wide
viewports while content hugged the left edge. (2) The exhibition pricing/schedule/FAQ
sections (`.cs-ruledlist`, `.cs-faq`) rendered completely unstyled on the full page (see
AS-06 #3) — which manifested as the SAME symptom (full width, flush left) even though the
root cause that time was "no CSS at all," not "CSS present but missing a centering rule."
Both bugs produce the identical visible symptom — check AS-06 first when you see this.

**Verify**: for any `max-width` declaration, confirm a centering rule exists on the SAME
selector (or its flex/grid parent). A quick geometry check: measure the element's
`left`-edge-to-container-`left`-edge gap vs. its `right`-edge-to-container-`right`-edge gap
at a wide viewport — they should be equal; if the right gap is much larger, centering is
missing (or, per AS-06, the scaffold CSS never loaded at all).

---

## AS-09 — A shared mask/transform wrapper that also contains unrelated sibling content

**Rule**: when applying `overflow: hidden` + a `transform`/`scale`/animation to "mask" one
element (e.g. a parallax-panning image), the mask wrapper must contain ONLY that element —
never a sibling that shouldn't be clipped or visually bled into (a caption, a label).

**Why it happens**: the natural DOM grouping for "an image with its caption" is one
wrapper (`<figure>`) containing both — reusing that SAME wrapper as the mask/transform
target is the path of least resistance, but couples two unrelated concerns (mask geometry
+ content grouping) onto one element.

**Caught here**: the scroll-parallax mask/scale treatment was applied directly to
`.cs-collage-media`/`.cs-quote-media`/etc. (the figure wrapping BOTH the image and its
caption), so the image's transform-scaled paint could visually bleed into the caption text
sitting below it in the same overflow:hidden box.

**Fix pattern**: introduce a dedicated single-purpose wrapper (`.c-image-mask`) around ONLY
the image; the caption stays a sibling of the mask, not a child of it.

**Verify**: before applying `overflow: hidden` + transform to a wrapper, list everything
inside it. If it's more than the one element meant to be masked/animated, split it — never
mask a wrapper that also carries unrelated content.

---

## AS-10 — Interactive-state colors bypass the contrast check the resting state got

**Rule**: contrast must be verified for EVERY state a text/UI color can appear in —
`:hover`, `:focus-visible`, `:active` — not just the default resting state. A color
extracted or chosen for ONE surface (or one state) must never be applied unconditionally
across every surface a component can render on. This generalizes AS-01 (which was scoped
to a static divider color) to interactive states specifically, because they're easy to
verify by accident-of-omission: a resting-state color review naturally looks at the
rendered page as-is; a hover color only reveals itself on interaction, so it's the kind of
bug that survives every screenshot-based review.

**Why it happens**: a brand's "measured link-hover color" is extracted from wherever the
extractor happened to sample it (often the footer or nav, which is frequently a dark/
inverse surface) and then wired as ONE global CSS custom property, on the reasonable-
looking assumption that "the brand's hover color" is a single fact — without checking it
against every surface the SAME link component renders on elsewhere in the page.

**Caught here**: WoodWave's measured link-hover (`#edd580`, gold, sampled from the dark
footer) was applied via a single unconditional `:root { --c-link-hover: #edd580; }` to
EVERY `.c-arrow-link` on the page. Against the dark surface it was measured on, contrast is
8.96:1 (excellent). Against the cream `surface/primary` background, contrast is **1.3:1** —
a hard WCAG failure (text needs ≥4.5:1; UI components need ≥3:1 minimum) that reads as
"link disappears on hover." This was ALSO a silent violation of the brand's own
`no-accent-on-light` neverDo rule that `onbrand_check.py` never caught, because that check
inspects the resting-state HTML/CSS, not `:hover` rules.

**Fix pattern**: resolve the interactive-state color PER SURFACE, the same way `--c-ink`/
`--c-hairline` already are — apply the brand's measured accent hover ONLY on the
dark/`textAccent`-bearing surface it's sanctioned for; every other surface falls back to
that surface's own already-safe ink color (no visible shift; the arrow-nudge motion still
signals interactivity). Give the GLOBAL `:root` declaration a safe, non-accent default
(`var(--c-ink)`) so any usage that somehow escapes per-surface scoping still fails safe
rather than failing loud.

**Verify**: run `node brand_pipeline/contrast_audit.mjs <rendered-index.html>` — it walks
every visible text element against its EFFECTIVE background (nearest painted ancestor, not
an assumed surface) AND resolves each section's `--c-link-hover` custom property against
that section's background, flagging anything below 4.5:1 (normal text) / 3:1 (large text).
It is wired as a hard gate in `wildcard_generator.gate_candidate`; run it manually on any
composed page before shipping. (Negative-tested: it reports the original gold-on-cream
failure at exactly 1.30:1 for both the TEXT and HOVER paths.)

---

## AS-11 — Under-filled sections (metadata-only, no primary content)

**Rule**: a section must carry PRIMARY content — a heading plus at least one substantive
element (body copy, media, ruled rows/list, or a purposeful form). A section composed only
of metadata-register elements (eyebrow, caption, counter, CTA link) is not a section, it's
an empty frame. Two sub-shapes, both defects:
- eyebrow + CTA with no heading and no text at all;
- eyebrow + heading alone — acceptable ONLY if the heading is long/display-scale enough to
  carry the section; otherwise it needs one more element (media, list, description).

**Why it happens**: the pattern's slot list gets partially filled — the generator has an
eyebrow and a CTA handy (they're short, always available) and ships the section anyway,
because nothing enforced the pattern's own `contentShape` minimums. Every slot rendered is
"correct"; the SECTION is still empty.

**Caught here**: an externally-generated page (v44, built outside this pipeline): one
section with only eyebrow + CTA; another ("A Collection Across Eras") with only eyebrow +
a short heading floating in empty space.

**Verify**: run `node brand_pipeline/slop_audit.mjs <index.html>` — flags any section
whose primary-content count (headings with real length, paragraphs >40 chars, media,
rows/list items, forms) is zero, or whose only content is metadata-register elements.

---

## AS-12 — Empty column in a multi-column layout

**Rule**: every column of a grid/split layout must contain content. If one side has
nothing to say, either give it meaningful content (a description, a heading+description —
top-, center-, or bottom-anchored, all fine) or change the layout to single-column.
Whitespace is a tool; a structurally EMPTY column reads as broken, not as editorial
restraint.

**Why it happens**: a two-column pattern gets reused for content that only fills one
column (a portrait + name caption, nothing else), and the composer renders the grid
anyway — the empty column is invisible in the code (the grid is "correct") and only
obvious visually.

**Caught here**: v44's curator section — a portrait photo + "Chief Curator" caption on
the right, a completely empty left half. The person deserved a description; the layout
demanded one.

**Verify**: `slop_audit.mjs` measures each direct child of grid/split containers — a
column whose content bounding box is empty (no text nodes, no media) while a sibling
column is filled gets flagged.

---

## AS-13 — Information-bearing media without its data as text

**Rule**: media that ENCODES information (a map, a chart, a schedule graphic) is an
illustration of that information, not a replacement for it. A map section must also carry
the address (and ideally hours/directions) as text; a chart needs its key figures. The
reader must never have to decode an image to get data the section exists to provide.

**Why it happens**: the media slot fills the visual space convincingly, so the section
LOOKS complete — the missing text data doesn't leave a visible hole the way a missing
image does.

**Caught here**: v44's map section — eyebrow + map graphic + CTA, no address anywhere.
(Contrast the pipeline's own visit-band: map + hours/address panel rows — the data rides
with the picture.)

**Verify**: heuristic in `slop_audit.mjs`: a section whose media alt/src suggests
map/chart content but which contains no address-like/data-like text rows gets flagged for
human review.

---

## AS-14 — Purpose-blind conversion UI (an input with no stated reason)

**Rule**: every form/input must be preceded by copy that states the EXCHANGE — what the
person gets for what they give ("One letter a season — new works, new hours, nothing
else."). A bare input + submit, or an input whose only context is an eyebrow, converts
nobody and reads as machine-assembled. The placeholder is not the purpose.

**Why it happens**: the form component is self-contained and renders fine standalone, so
a generator can drop it into a section without the surrounding copy — nothing in the
component contract demanded a reason-why.

**Caught here**: v44's email-capture section — a field with no explanation of why an
email should be entered.

**Verify**: `slop_audit.mjs` flags any section containing an input/form with fewer than
~40 characters of body copy before the form within the same section.

---

## AS-15 — Ragged text wrapping (unbalanced last lines)

**Rule**: headings and short text blocks must not wrap into ragged, accidental shapes (a
single orphaned word on the last line of a three-line display heading). Use the CSS
text-wrapping primitives as a system-level default: `text-wrap: balance` for headings/
eyebrows/captions, and balanced/pretty wrapping for paragraphs.

**Why it happens**: line breaking is content-dependent — a heading that wrapped cleanly
with the template copy wraps badly with real copy, and nobody re-checks every heading at
every width.

**Fix (applied system-level in COMPONENT_CSS)**:
```css
.c-heading, .c-eyebrow, .c-caption { text-wrap: balance; }
p { text-wrap-style: balance; }   /* engines cap balance at ~6 lines — long body text is
                                     unaffected; short paragraphs stop orphaning */
```

**Verify**: visual/spot check at 2+ widths; balance is a browser primitive so once the CSS
ships the check is that it hasn't been overridden.

---

## AS-16 — Text set flush against media (missing gutter)

**Rule**: body/heading text must never sit flush against an image edge — wrapped text
beside a floated/inset image needs a real inline gutter, and text below an image needs a
real block gap. Margin captions are exempt (they sit close by design); the hero's
sanctioned display-over-media overlap is exempt; everything else needs breathing room.

**Why it happens**: float/inset margins are SIDE-SPECIFIC — a margin authored for one
float side (gap-left for a right-floated image) silently becomes zero-gutter when the
layout is mirrored or the knob flips; and below-image gaps depend on line-height
interactions nobody re-checks per copy change.

**Caught here**: reported on an interlock (float-wrap) render — statement text touching
the image's edge and running flush beneath it. (Note: the on-disk render measured healthy
68-118px gaps at review time — the reported state was a stale browser copy, which is
itself why this rule is now SCRIPTED rather than review-dependent, and why Studio now
sends no-store cache headers.)

**Verify**: `slop_audit.mjs` measures per-LINE text boxes (Range.getClientRects) against
every image box — flags intersection, inline gaps < 16px, and below-gaps < 16px, skipping
captions, aria-hidden decoration, and the hero's sanctioned overlap.

---

## AS-17 — Aspect-ratio monotony (the brand's ratio VARIETY not captured)

**Rule**: a brand's imagery system is a PALETTE of aspect ratios, not one number — a real
editorial site mixes wide bands, standard landscapes, near-squares, and portraits
deliberately. Extraction must capture that palette (`tokens.imagery.aspectPalette`, each
entry with value + role + provenance), and execution must deploy from it — a composed
page where every image renders at the same hardcoded ratio flattens a signature the
source actually had.

**Why it happens**: each section scaffold hardcodes the one ratio that looked right when
that section was built; nothing ever represented "the brand's ratios" as a first-class
extracted fact, so composers had nothing to consult.

**Caught here**: WoodWave's source images span 9:4, 7:4, 3:2, 9:7, and 3:4 — but the
scaffolds hardcoded a single ratio per section with no link to those measurements.
Fixed: the measured palette now lives in `brand.yaml tokens.imagery.aspectPalette`,
`component_vars` emits it as `--c-aspect-*` vars, and every scaffold reads the var (with
its old hardcoded value as fallback, so palette-less brands are unchanged).

**Verify**: extraction — confirm `tokens.imagery.aspectPalette` exists and its values
match measured source-image dimensions. Execution — rendered pages should show ≥2 distinct
ratios when the palette has ≥2 (spot-check `img` bounding boxes).

---

## AS-18 — Silent alignment fall-through (layout anchored by CSS accident)

**Rule**: every section's alignment must be RESOLVED through one explicit chain —
section-explicit `alignment` > pattern `contentShape.alignment` (brand-schema §4.4) >
style role default — and the winning layer must be STAMPED on the section wrapper
(`data-align` + `data-align-source="section|pattern|style"` + `data-align-counterweight`,
mirroring `data-pattern`). A section whose anchor comes from a hardcoded
`align-items: flex-start` or a `text-align: left` literal in a scaffold/override has no
declared intent — that is a defect even when it happens to look fine. Out-of-enum anchor
values must WARN loudly and fall through explicitly, never drop silently; asymmetric
(left/right) anchors must name their counterweight device.

**Why it happens**: alignment "defaults" accrete per-layer — a scaffold hardcodes
flex-start because the first section built with it was left, a page override duplicates
left literals, a placement emitter only fires when a knob exists and only targets one
archetype's selectors — so declared intent (pattern `contentShape.alignment`, style
`shape.centered`) is parsed nowhere and every layer assumes another layer decided.

**Caught here**: 19/27 standard sections on `showcase-standard-editorial-luxury` rendered
left-aligned with zero declared intent: `contentShape.alignment` was never parsed into
`layout_library.Pattern` (and `footer-compact-utility-bar`'s `space-between` was silently
dropped as out-of-enum), `SCAFFOLD_FLOW_CSS` hardcoded `flex-start`, both
`page_style_override` twins hardcoded left literals, `layout_placement_css` no-oped on
non-stack markup (#sec-1 declared center, rendered uncentered and DROPPED its heading),
and the gate's `no-centered-everything` read the accidental flex-start as an asymmetry
PASS. Fixed: `resolve_alignment()` in `compose_section.py` is the single chain; styles
carry machine-readable `alignment:` front-matter blocks; all 35 standard + 15 project
patterns declare `contentShape.alignment`; anchor CSS covers every archetype (stack,
flow, gallery band, cards, overlay, banded); `space-between`/`edge-to-edge` joined the
enum; the G10 `alignment-resolution` gate fails a stamp-less section on a stance-bearing
style, and `no-centered-everything` now reads declared anchors.

**Verify**: gate — `onbrand_check.py --composition` check `alignment-resolution` (every
`#sec-N` wrapper carries `data-align` + `data-align-source`; left/right anchors carry a
counterweight). Grep — `rg 'align-items: flex-start|text-align: left' brand_pipeline/`
must not hit a scaffold/override literal that bypasses `resolve_alignment`.

---

## AS-19 — Media placement blind to the resolved anchor (misregistration)

**Rule**: a slot's grid placement must DERIVE from the section's resolved anchor, never
from a hardcoded span that was authored for one anchor. A centered text block requires a
symmetric media span (e.g. `4 / -4`); the asymmetric editorial offset (`6 / -1`,
`8 / -1`) is legal only under a side (left/right) anchor or a registered counterweight.
Any override that collapses a grid's tracks must also re-place the children that carried
track-relative spans.

**Why it happens**: the span was correct for the archetype's ORIGINAL anchor and nobody
re-derived it when a wildcard/style/pattern re-anchored the text — grid-column literals
don't participate in any resolution chain, so they survive every re-anchoring untouched
(and an out-of-range grid-column on a collapsed 1-track grid "works" by implicit track
creation, which is why it renders shifted instead of erroring).

**Caught here**: the `centered-monument` wildcard centered the 'What we hold' statement
text but `.cs-statement-media { grid-column: 6 / -1 }` kept the media right-shifted under
it (`full-wildcard-centered-monument`). Fixed: statement/quote scaffolds read var-driven
spans (`--c-statement-*-col` / `--c-quote-*-col`, editorial-offset defaults); the
resolved-centered anchor re-scopes them symmetric (text `3 / -3`, media `4 / -4`) via
`layout_placement_css`; the wildcard now DECLARES `alignment: {anchor: centered}`
(mutate) instead of fighting the scaffold with `1fr !important`; the section-ladder
centered inversions re-place their spanned children (`grid-column: 1`). Composition-rules
carries the legality note.

**Verify**: gate — `onbrand_check.py --composition` check `media-registration` (a
`data-align="centered"` section containing statement/quote media must scope a symmetric
`--c-*-media-col`, tolerance |start−end| ≤ 1). Grep — every `cs-*-media { grid-column: }`
literal in `compose_section.py` must be var-driven or anchor-conditional.

---

## AS-20 — Interaction tokens that don't re-scope per surface (hover leakage)

**Rule**: interaction tokens (`--c-link-hover`, accent link colors) re-scope PER SURFACE
MODE — including CARDS and PANELS, which must re-scope ink/accent/link-hover exactly like
sections re-scope surfaces. A measured accent hover extracted from a dark surface (gold
from a dark footer) is legal on dark/textAccent-bearing surfaces ONLY; on light surfaces
the hover resolves to that surface's own ink (ink-shift) or the underline-draw per
`motionSpec`. The `:hover` state is part of the surface contract, not a global constant.

**Why it happens**: hover colors are extracted from ONE context (the footer/nav where
they were measured) and emitted once at `:root`/section scope; panels re-scope their
resting tokens (`--c-ink`, `--c-accent`) but nobody lists the INTERACTION tokens in the
re-scope set, and static checks only look at resting-state colors, so the leak is
invisible until someone hovers.

**Caught here**: WoodWave's measured gold `#edd580` hover (dark-footer truth, kept as-is
there) leaked onto the cream visit-band card — "GET DIRECTIONS →" hovered gold-on-cream
at ~1.3:1 (`full-wildcard-centered-monument`). Fixed: `.cs-panel`, `.cs-ov-panel` and the
banded `band_vars` inline scopes now re-scope `--c-link-hover` with their own ink (bands:
gold only when the band surface carries `textAccent`); `readability.py` gained
`check_link_hover_contrast` — it re-binds every `:hover`/`:focus` color rule to its
resting element, resolves it in the element's OWN custom-property scope, and measures it
against the element's OWN effective background (card bg, not section bg).

**Verify**: gate — `onbrand_check.py --composition` check `interaction-contrast`
(gold-on-cream fails mechanically; the dark-footer gold hover passes). Unit —
`brand_pipeline/tests/test_readability_checks.py` hover fixtures.

---

## Adding a new entry

Copy this shape: **Rule** (the imperative, one or two sentences) / **Why it happens** (the
plausible-but-wrong reasoning that produces it) / **Caught here** (the concrete instance —
name the file, the values, the visible symptom) / **Verify** (a repeatable check, ideally
scriptable). Keep entries brand-agnostic — this file lives in `brand_pipeline/spec/`
alongside `brand-schema.md`/`layout-analyst-skill.md` because these failure shapes recur
across ANY project this pipeline generates, not just WoodWave.
