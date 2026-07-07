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

## AS-21 — Single-viewport verification (certifying the one width you looked at)

**Rule**: every scripted geometry/overlap gate runs at MULTIPLE viewport widths — at
minimum the desktop reference width (1440) and one mid width inside the awkward band
(~1180, where poster-scale type meets narrowing grid tracks). A PASS at one width
certifies exactly that width and nothing else. Grid does not clip overflow: an oversized
display heading paints over the neighboring column silently, with no layout shift to
notice in the DOM.

**Why it happens**: audits standardize on one `viewport:` constant because that is the
width the developer's own browser happened to be; breakpoints are authored in pairs
(desktop + 767px mobile) leaving the 768–1300px band covered by the DESKTOP grid with
~25% less room — precisely where clamp() minimums stop shrinking type.

**Caught here**: both rejected WoodWave wildcard candidates (hero transplant, ghost
colossal) showed the collage display heading painted over the body column at Studio's
~1180px review width; `slop_audit.mjs` had certified them PASS at its single hardcoded
1440px. Fixed: `slop_audit.mjs` loops `WIDTHS = [1440, 1180]`, and the collage scaffold
gained a mid collapse (`@media (max-width: 1280px)` → single column) so the 6/6 column
split never hosts poster type it cannot contain.

**Verify**: gate — `slop_audit.mjs` output shows every target twice (`@1440px`,
`@1180px`). Grep — `rg 'width: 1440' brand_pipeline/*.mjs` must only hit inside a
width loop.

---

## AS-22 — Grammar transplant blind to the target's surface contract

**Rule**: a use-case TRANSPLANT (rendering use-case X's content in use-case Y's layout
grammar) must adopt the TARGET use-case's `surfaceIntent` and captured non-negotiables
(hero-must-be-dark, footer-must-carry-utility, …), never the source grammar's surface.
The layout grammar travels; the surface contract does not.

**Why it happens**: the transplant is implemented as "clone the source layout, swap the
content" — surface comes along silently because it lives on the cloned layout dict, and
every gate passes (contrast is fine on EITHER surface; only the brand's captured
expectation for that slot is violated, which no per-element check sees).

**Caught here**: WoodWave `wildcard-opening-bookend-L4` set the hero in the about-run's
cream ghost-word collage; the captured hero pattern (`hero-display-over-staggered-media`)
is `surface/inverse` — the user rejected it on sight ("hero should be dark"). The
`hero-ghost` recipe is parked until it re-fits the ghost grammar for a dark surface.

**Verify**: recipe review — every `RECIPES` entry that clones a foreign layout must
override `surfaceIntent` to the target use-case's captured pattern surface; compare
`mutate()` output against `layout_library.get()` for the target use-case.

---

## AS-23 — Naked image slots (no placeholder backing)

**Rule**: every content-image slot carries a PLACEHOLDER BACKING — a subtle diagonal
hatch (`repeating-linear-gradient(135deg, …13px/26px)`) built from the surface's OWN
tokens: stripe A is `var(--c-paper)`, stripe B is `color-mix(in srgb, var(--c-paper) 93%,
var(--c-ink))`. It shows while the photo loads, on a broken src, or wherever cover-fit
leaves the frame unpainted — the frame never flashes the raw page background. The colors
are NEVER hardcoded at system level (AS-01): the same one rule resolves to a deep-brown
hatch on a dark section and a gently-shaded cream hatch on a light one.

**Why it happens**: images "always load" on the developer's machine, so the unpainted
frame state is never seen; a backing added later gets hardcoded to the one brand being
looked at, which is AS-01 with extra steps.

**Caught here**: WoodWave kit-field homepage review — image frames sat on the raw
section background until load. Added as the system-level `.c-image` rule in
`component_render.COMPONENT_CSS` (per-surface by construction since it reads
`--c-paper`/`--c-ink`); on WoodWave's dark hero it resolves to rgb(58,45,31)/rgb(51,39,26).

**Verify**: gate — `slop_audit.mjs` AS-23 check: every rendered content image's computed
`background-image` contains `repeating-linear-gradient` (logos/icons under 80px exempt).

---

## AS-24 — Brand DNA leak: raw visual values in shared renderers

**Rule**: a shared renderer/composer may never emit a literal visual value (hex/rgba,
px/rem magnitude, weight, case transform, radius, shadow, duration, easing, aspect) —
every visual value resolves through the generated token layer (the per-page
`<style id="tokens">` block generated by `tokens_css.py` from the ACTIVE brand's
brand.yaml), or carries an explicit `provenance: structural` comment. A
`var(--x, LITERAL)` fallback **is** a raw emission: the fallback is somebody's brand.

**Why it happens**: renderers get built against the first brand that exercised them; its
measured values feel like "the defaults" and calcify into the shared CSS. Every later
brand then renders brand-one's typography/shape/rhythm with its own hues swapped in —
plausible at a glance, off-brand everywhere.

**Caught here**: the HubSpot E2E page (2026-07-02) rendered "WoodWave brand with HubSpot
colors": uppercase editorial headings (`text-transform: uppercase` ×10 in
component_render), WoodWave button weight/padding (`700` / `0.8em 1.6em`), WoodWave
motion (`320/480/620ms cubic-bezier(.22,1,.36,1)` fallbacks), WoodWave panel surfaces
(`var(--c-panel, #F7EFE6)`, `#1F1A14` inks, `rgba(31,26,20,.30)` hairlines) — while
HubSpot's brand.yaml measured `sentence` case, weight 500 buttons `0.75rem 1.5rem`,
`150/200/300ms ease-in-out`, `#f8f5ee` panels the whole time.

**Composer discipline**: three layers — measured brand values (generated layer-1 tokens
block) → semantic `--c-*` aliases (generated per surface scope by `component_vars`) →
component CSS references ONLY vars. No literal fallbacks in `var()`. Missing REQUIRED
token = fail-loud at generation (`TokenGenerationError` naming the token); missing
OPTIONAL token = the device is disabled, never substituted from another brand.

**Gate check**: `onbrand_check.py` invariant `token-provenance` (advisory by default,
HARD under `--composition`) — scans emitted CSS (minus the generated tokens block) for
raw visual values not traceable to the active brand's token index
(`tokens.manifest.json`); each violation names the offending value AND the suggested
token with its resolved value (or flags a foreign-brand match — the smoking gun);
structural constants allowlist via `/* provenance: structural … */` comments;
durations/easing report as warnings (DECISIONS.md #3).

**Verify**: unit — `brand_pipeline/tests/test_tokens_css.py` +
`tests/test_token_provenance.py` (synthetic fixture brand exercises foreign-brand
detection). Spot check — `rg -n "var\(--[a-z-]+,\s*[#0-9]" brand_pipeline/*.py` returns
zero var-with-literal-fallback sites in renderer CSS; render the same composition for
two brands and diff the emitted CSS — every diff line must be a token value, never a
selector's literal. (The preview gallery's old light-canvas `--c-accent: var(--ink)`
pinning was the same shape in harness form — fixed by per-surface generated alias
scopes in `render_components_preview.component_alias_css`.)

---

## AS-25 — Alignment layers that disagree or can't see each other

**Rule**: the alignment declaration layers must be mutually CONSISTENT and mutually
VISIBLE. Three obligations: (1) a pattern's `variantKnobs.align.default` must agree with
its own `contentShape.alignment` — one pattern, one declared stance; (2) a section that
declares only a bare asymmetric ANCHOR (`left`/`right`, the common generator shorthand)
inherits its counterweight DEVICE from the deepest layer declaring one for the SAME
anchor (pattern first, then style role scan across ALL candidate role keys) — only when
no layer declares a device does the stamp stay bare, and the G10 gate then fails it;
(3) the gate judges stamps against the OPERATIVE style definition the render used —
pages self-declare it as `data-align-stance="declared|none"` on `<html>` — never by
re-loading today's `styles/<id>.md` by name.

**Why it happens**: (1) knob defaults are authored while iterating a variant axis and
nobody re-checks them against the declared stance; (2) generators emit `align: left`
because the anchor is the only field they were taught, and the counterweight concept
lives one layer down; (3) checks resolve context by IDENTIFIER (style id) instead of by
what the artifact actually carries — a snapshotted/frozen styles dir renders under an
older definition with the same name, and the check silently judges it by the new one.

**Caught here**: closing the AS-18 batch regate — `seam-straddle-portrait` declared
`contentShape.alignment: centered` but its `align` knob defaulted to `left`, emitting a
counterweight-less left section on every showcase page; hybrid/ablation LLM compositions
(`knobs.align: left` with no seeded pattern) stamped bare-left although editorial-luxury
declares `interlock/split: {left, +device}` for exactly those sections; the A/B arm
(`experiments/woodwave-ab/`, frozen `styles_dir` snapshot WITHOUT an alignment block)
failed G10 because the gate loaded the CURRENT editorial-luxury by id and demanded
stamps the operative style never declared. Fixed: knob default corrected in
`about.yaml`; counterweight inheritance in `compose_section.resolve_alignment` (scans
all `_align_role_keys`); `data-align-stance` stamped by `compose_page.build_page` + the
single-section renderer, read first by `onbrand_check._style_declares_alignment`.

**Verify**: unit — `brand_pipeline/tests/test_alignment_resolution.py`. Gate — G10
`alignment-resolution` under `--composition`. Grep — for every pattern with an `align`
variant knob, the knob default must normalize to `contentShape.alignment.value`;
`rg 'data-align-stance' <render>/index.html` on any styled composed page must hit.

---

## AS-26 — Slot-faithless adapters: bound actions dropped, unbound forms invented

**Rule**: the composition adapter must be SLOT-FAITHFUL both ways. A slot the section
binds (a `contract: button` action, a testimonial, a logo wall, a link list) must reach
a renderer — never be silently dropped by a fixed-shape mapping. A device the section
does NOT bind (the signup form) must never be invented for it. Stack disambiguation
routes on EVIDENCE — a conversion useCase, a bound form/input slot, or bound button
actions select the conversion composer; any other non-hero stack renders its own slots
through the generic-flow composer.

**Why it happens**: the first conversion section an adapter meets is a newsletter form,
so "non-hero stack" gets hard-wired to `[header, form]`; every later section role
(logos, testimonial, footer, feature dividers) then collapses into near-identical
invented signup forms, and the real bound actions — the one thing the brand's gate
demands — are the only slots that never render.

**Caught here**: HubSpot tokenized validation (2026-07-03) — `_cta_mapping()` in
`compose_from_composition.py` took no section argument at all: logos/testimonial/footer
stacks each rendered an invented "you@company.com" form (near-quadruplication), the
hero + cta `contract: button` slots ("Start free" / "See how it works") were dropped,
and `never-typographic-primary` failed with no filled CTA on the page. Same shape on
WoodWave's own showcase page: `value-props`/divider stacks rendered as signup forms.

**Verify**: unit — `tests/test_fix_batch.py` (`AdapterSlotFaithfulness`: buttons
preserved, no invented form beside real actions, logos→captions, testimonial→
paragraph+attribution, footer links→link entries, legacy heading+link conversions keep
the exact `[header, form]` mapping). Gate — `slot-resolution` zero markers + one
`.c-button` element where the brand law demands it.

---

## AS-27 — CTA shape resolved brand-law-first, style-default-second — and enforced at the renderer

**Rule**: the `cta-shape` structural flag resolves in this order: brand structure LAW
(`neverDo.never-typographic-primary` / `renderHint.useFilledButton` → filled;
`primitives.button.use: never` → typographic) > the active STYLE's `primaryAction`
soft-option default (front-matter) > measured `buttons.primary` presence > typographic.
`render_button` itself dispatches on the resolved shape: a typographic brand CANNOT
emit `.c-button` through the catalog (the contract downgrades to the arrow link), and a
filled brand's form submit renders its filled button. Variant magnitudes stay tokens —
a boxed-input brand's `--c-input-radius` aliases its own measured `--radius-input`,
never the global `--radius`.

**Why it happens**: shape decisions get made ad hoc at individual call sites, so each
composer picks whatever the brand it was built against needed; the style layer (whose
archetype actually owns the default — corporate demands filled primaries, editorial
grammar is typographic links) never gets consulted, and a blanket render change would
swap every brand at once.

**Caught here**: HubSpot (filled by law, corporate-saas-clean by archetype) rendered
zero filled CTAs while WoodWave (typographic by law under any style) had to stay
byte-stable; inputs rendered 1rem card radius instead of the measured 0.25rem because
`--c-input-radius` was consumed by `.c-field--boxed` but never emitted.

**Gate note — fidelity-over-floor**: rendering the real filled CTA surfaces the brand's
MEASURED label-on-fill pair to the `text-contrast` invariant, which targets AI drift; a
provenance-verified measured component pair (`buttons.primary/secondary` fg-on-bg from
brand.yaml) is exempt from the generic WCAG-ish floor and reported as
"exempt as MEASURED brand pairs" (real brands ship sub-AA primaries). The SAME colors
in any non-measured pairing still fail.

**Verify**: unit — `tests/test_fix_batch.py` (`StyleAwareCtaShape`: law beats style both
directions; style default fills the law-silent gap; dispatch renders arrow-link for a
`use: never` brand, `.c-button` for a filled-law brand;
`MeasuredPairContrastExemption`: measured pair exempt + reported, non-measured pair
still fails). Grep — `--c-input-radius:` in a boxed brand's render resolves to
`var(--radius-input)`.

---

## AS-28 — Footer grammar is a per-brand structural variant, not shared scaffold

**Rule**: the closing-bookend footer's GRAMMAR (oversized display slash-sitemap vs
measured multi-column directory) is a structural-variant flag resolved from the brand's
own extracted facts (`footer_grammar`: a type-scale footer display tier → display-links;
extracted `footer.columns` → columns), emitted per brand like button/boxed-field CSS —
never always-on component CSS. Footer CONTENT resolves from the brand: the display-links
sitemap is the brand's own navbar destinations matched against its footer columns (never
a hardcoded label tuple); the columns grammar passes `footer.columns` through verbatim;
the columns register rides the measured chrome tokens (`--c-foot-link-size/-weight`).

**Why it happens**: the first brand's footer device ships inside `COMPONENT_CSS` "as the
footer", its nav labels get frozen into the composer as a filter list, and every later
brand inherits both — a dense-directory brand renders another brand's oversized didone
slash grammar with an empty sitemap (its labels never match the frozen list).

**Caught here**: HubSpot pages carried `.c-foot-sitemap-link`'s
`clamp(1.75rem, 3.5cqw, 3rem)` (flagged by provenance as a WoodWave-adjacent raw value)
plus `compose_page.footer_content`'s literal
`("about", "gallery", "exhibition", "visit", "buy tickets")` — WoodWave's nav frozen
into the scaffold — while HubSpot's real 5-column/41-link footer never rendered.

**Verify**: unit — `tests/test_fix_batch.py` (`FooterGrammar`) +
`tests/test_structural_variants.py` (exactly one grammar per brand; gallery mode carries
both). Grep — `.c-foot-sitemap` absent from `component_render.COMPONENT_CSS`; a
columns-brand render carries `.c-foot-cols` and no `.c-foot-sitemap-link`.

---

## AS-29 — Brand-named literals in emitted content attributes

**Rule**: composer/renderer-authored CONTENT (alt text, aria-labels, titles, default
copy) must derive from the ACTIVE brand (asset metadata, `brand.name`, the module's own
caption) — never a brand-named string literal in shared code. A hardcoded
`alt="<BrandX> …"` is the content-attribute twin of a raw visual value (AS-24).

**Why it happens**: alt text feels like harmless boilerplate, so the first brand's name
gets typed into the renderer default and nobody scans content attributes the way they
scan CSS values.

**Caught here**: `compose_section.py` carried `alt="WoodWave editorial photography"`,
`alt="WoodWave detail photography"` and `alt="WoodWave — <asset>"` literals in
`_props_for`/`compose_features_cards`; the HubSpot page shipped WoodWave's name in its
image alts.

**Verify**: gate — new slop row `No foreign-brand content literals (alt/aria/title)`
(names from the local `runs/*/brand` corpus; the active brand's own name exempt under
any label). Unit — `tests/test_fix_batch.py` (`ForeignBrandContent`). Grep —
`rg '"alt": "[A-Z]' brand_pipeline/*.py` returns no brand-name literals.

---

## AS-30 — Structured asset payloads unwrapped at the adapter boundary

**Rule**: the adapter layer owns the asset payload SHAPE. A sanitizer/normalizer that
wraps bare asset strings into `{src, alt}` dicts must be paired with unwrapping at
every consumer boundary — composers receive `src`/`alt` STRINGS and never
string-interpolate a structured payload into a path.

**Why it happens**: a normalizer is added for one field shape (slot.asset) and the
repeatable-copy shape (module list items) inherits the wrapping without inheriting the
unwrapping; Python happily formats the dict repr into the f-string path.

**Caught here**: HubSpot features cards — `_sanitize_assets._clean_asset` normalized
module `asset: "ProductIcons_….webp"` strings into `{'src': 'assets/…'}` dicts,
`_cards_copy` passed the dict through, and `compose_features_cards` emitted
`src="assets/{'src': 'assets/ProductIcons_SalesHub_Icon_Orange.webp'}"` — three
"missing" assets on the fidelity + slop rows.

**Verify**: unit — `tests/test_fix_batch.py`
(`test_cards_copy_unwraps_sanitized_asset_dict`). Gate — `All brand image assets
present` on a composition whose modules declare real brand assets.

---

## AS-31 — Scale gates must resolve var() chains before judging

**Rule**: any gate check that compares an emitted CSS value against a brand scale must
first resolve the page's OWN `var(--name[, fallback])` chains (via the page's custom
property declarations). An alias chain that lands on an on-scale token is the token
architecture working; judging the unresolved reference text as an off-scale literal is
a false positive that punishes exactly the discipline AS-24 demands.

**Why it happens**: checks are written when pages carry resolved literals; once the
token layer replaces literals with references, string-set membership silently inverts
from "on scale" to "off scale".

**Caught here**: HubSpot slop row `Rounding matches brand radius scale` failed on
`var(--button-radius)` — which resolves through the generated layer-1 block to
`0.5rem`, squarely on HubSpot's measured `0.25/0.5/1rem/999999px` scale.

**Verify**: unit — `tests/test_fix_batch.py` (`RadiusVarChain`: single hop, nested
chain, fallback hop, dead-end passthrough, cycle termination, on-scale pass +
true-off-scale fail through `check_slop`).

---

## AS-32 — Display magnitude ownership + exact-role tier resolution

**Rule**: WHO owns the display magnitude is a declared style stance
(`type.display_source` front-matter): `poster` — the style's oversized clamp IS the
identity (editorial archetypes); `brand` — the brand's measured `display-hero` tier
drives the size and the style shapes only leading/tracking/weight (corporate
archetypes). Role→tier resolution honors exact tier names: a hyphenated role
(`display-hero`) that exists verbatim in the brand scale is AUTHORITATIVE over
family-keyword heuristics; and every register a component renders carries its measured
tier attributes — body copy rides `--c-body-weight` (the brand's measured body weight),
not the UA default.

**Why it happens**: the poster clamp is authored as "the display" while building
editorial styles, so a corporate brand's 65px hero inflates to 172.8px; keyword
heuristics pick "the largest display-family tier" so the verbatim-requested tier loses
to a bigger sibling; and font-weight silently falls through to the UA 400 because the
first brand's body happened to measure 400.

**Caught here**: HubSpot hero rendered 172.8px/500 vs the real ~65px/300
(corporate-saas-clean poster clamp + `_pick_scale_entry` choosing `display-02` over the
verbatim `display-hero`); `.c-paragraph` carried no font-weight at all, rendering
HubSpot's measured 300 body at 400.

**Verify**: unit — `tests/test_fix_batch.py` (`ExactRolePicker`, `DisplaySource`).
Gate — style Rule 1 is display_source-aware (`Display rides the brand's measured
display tier` for `brand`-sourced styles; poster reach unchanged for `poster`). Grep —
`--c-body-weight` present in section alias blocks and consumed by `.c-paragraph`.

---

## AS-33 — Asset-role devices keyed to filenames instead of files (logo walls)

**Rule**: a device that renders EXTRACTED ASSETS (a partner/customer logo wall) resolves
per entry on DISK EVIDENCE — the asset file existing in the active brand's extracted
dir — never on a filename appearing in a composition or on the device's own default
content. Three legal outcomes per entry, resolved at the adapter boundary: a
disk-backed file renders as a REAL image in the image device (`.cs-logo-strip`); an
entry with metadata but no file falls back to the declared TEXT device (uppercase
caption of the mark's own alt/label); an entry with neither maps to NOTHING (never a
substitute device). The composer stamps the resolved device on the section
(`data-logo-device="image|text|empty"`) so the resolution is visible, and a brand-
wordmark device is never a logo-wall fallback — the wordmark is a NAV device whose
default text is the composing module's brand, i.e. somebody's brand (AS-24's content
twin, same shape as AS-29).

**Why it happens**: the logo contract's first consumer is the nav wordmark, so the
shared `logo` renderer's text default ("the" brand wordmark) feels safe; when a logo
WALL later routes slots through the same contract, each unhandled entry falls through
to that default — five identical foreign wordmarks that compile, render, and even look
deliberate. And filename-keyed rendering feels evidence-based because the filenames
came from the extraction — but a composition is a plan, not proof the file survived to
disk; interpolating it unchecked ships broken `<img>` srcs that pass every text-level
review.

**Caught here**: HubSpot live seeded run (`signup-launch-fixed-live`, 2026-07-03) — the
composition bound five real logo slots (`doordash-logo.svg`, `ebay-logo.svg`, … all
present in `runs/hubspot/brand/assets/`), but `_inline_props`'s logo branch dropped the
src/alt payload and rendered `SECTION_COPY["wordmark"]` — five "WoodWave" glyph
wordmarks on the HubSpot trust wall (the deterministic replay's list-copy shape had
already been routed to text captions by the fix batch; the per-slot shape fell through
a different hole to a worse device). Fixed: `_logo_item_mapping` (adapter, both slot
shapes) routes on `_sanitize_assets` disk evidence; the generic-flow composer groups
image entries into the `.cs-logo-strip` device (style-layer qualitative `logoStrip`
treatment: monochrome/reduced/plain) and stamps `data-logo-device`; `_inline_props`
unwraps src-bearing logo slots into image mode (AS-30).

**Verify**: gate — `onbrand_check.py` invariant `logo-wall-integrity` (G14): an
`image`-stamped section carries ≥1 `.c-logo-img` with a non-empty, on-disk src and a
non-empty metadata-derived alt; a `text`-stamped section carries ≥1 non-empty caption;
an `empty` stamp always fails. Unit — `brand_pipeline/tests/test_logo_strip.py`
(routing on disk evidence for both slot shapes, filename-without-file fallback, alt
provenance, device stamps, gate rows). Grep — `rg 'SECTION_COPY\["wordmark"\]'
brand_pipeline/compose_section.py` hits only nav/hero paths, never a logo-wall
mapping.

---

## AS-34 — Default/fallback art borrowed across brands (asset resolution without active-brand evidence)

**Rule**: every default, fallback, or placeholder ASSET a shared composer/adapter emits
must resolve against the ACTIVE brand's own on-disk inventory — or be OMITTED. A literal
filename in shared code (a `some-hero-photo.jpg`-style default) is at most a
*preference* to look up in that inventory, never an emittable src. The inventory itself
must be discovered recursively (subdirectories included) from the brand's extracted
tree, and repeatable asset-role slots must iterate the RAW authored list — a bare-string
item is coerced on disk evidence (file exists → image entry) or kept as its own text
caption, never silently dict-filtered away.

**Why it happens**: shared composers are grown against ONE development brand, so its
asset names get baked in as "safe defaults" — and they keep working for every brand
because the files ship with the pipeline's test project, making the leak invisible until
a second brand renders a hero with the first brand's staircase photo in it. The
bare-string drop has the same root: the adapter models the slot shape it saw first
(list-of-dicts) and a `isinstance(it, dict)` guard reads as defensive rather than lossy.
And `glob("*")` on the assets dir looks complete until an extraction writes
`assets/logos/…` one level down.

**Caught here**: Remote E2E run (`runs/remote/brand/compose/signup-launch`, 2026-07-03)
— `_hero_mapping` injected WoodWave's `hero-staircase.jpg`/`overlap-vase.jpg` into
Remote's hero and `_ov_media_html`/`_props_for`/`_LAYER_FALLBACK` carried the same
literals for every overlay/collage composer; `_logo_item_mapping` dropped bare-string
logo items from the wall; `copy_assets`/`_valid_asset_names` missed subdirectory assets.
Fixed: `compose_section.brand_image_inventory` (recursive, attached per-doc via
`attach_asset_inventory`) + `_brand_art` evidence-checked resolution at every default
site; `_logo_item_mapping` iterates raw lists and coerces strings on disk evidence.

**Verify**: gate — `onbrand_check.py` slop row "No foreign-brand asset references"
(`_brand_asset_corpus`: an image basename owned by a sibling brand's extracted tree and
absent from the active brand's fails). Unit —
`brand_pipeline/tests/test_remote_fix.py::BrandOwnedDefaultArt` (exact-name parity,
keyword fallback resolves own art, no-match omits, empty inventory omits),
`::BareStringLogoItems`, `::RecursiveAssetDiscovery`, `::ForeignAssetGate`. Grep —
`rg '"hero-staircase\.jpg"' brand_pipeline/` hits only preference arguments routed
through `_brand_art`, never a direct src interpolation.

---

## AS-35 — Chrome surface roles hardcoded to one brand's grammar (footer inverse-strong)

**Rule**: a page-chrome surface (the closing footer, the nav bar) is a PER-BRAND
resolution, not a shared constant. Resolve it from the brand's MEASURED chrome capture
(its extracted footer/nav surface color) matched against the brand's own `surfaces`
roles; only when the brand is silent fall back to the structural default. Role naming
stays palette-agnostic (`surface/raised`, `surface/inverse-strong`) — the resolver
compares measured VALUES, never name-matches a foreign brand's role vocabulary.

**Why it happens**: the first composed brand had a near-black footer, so
`FOOTER_SURFACE = "surface/inverse-strong"` reads as a reasonable page-grammar constant
— dark footers are common enough that two more brands render "fine" (HubSpot's footer
IS dark), and the constant survives until a genuinely all-light brand ships a navy
footer it never had. Chrome is exactly where this hides: it's composed by the page
assembler, not a section composer, so per-brand surface-intent resolution never touches
it.

**Caught here**: Remote E2E run (2026-07-03) — Remote's measured footer is `#f6f7f8`
(`surface/raised`, provenance `[footer]`), but every composed page closed on
`inverse-strong` deep navy: the largest visual delta on the page.
Fixed: `compose_page.footer_surface_role` — parses the brand's measured chrome-footer
bg (brand.yaml `footer.surface.bg`), nearest-matches it to the brand's own surface
roles by RGB distance (ties prefer the historical default), falls back to
`FOOTER_SURFACE_DEFAULT` only for silent brands (WoodWave byte-unchanged: its `#181313`
chrome footer resolves to its own `inverse-strong` ink).

**Verify**: unit — `test_remote_fix.py::FooterSurfaceRole` (light measured footer picks
the light role; near-black measured footer keeps inverse-strong; silent brand keeps the
default). Render — Remote `signup-launch-fixed/index.html` closing bookend stamps
`data-surface="surface/raised"`. Grep — `rg 'FOOTER_SURFACE\b' brand_pipeline/` hits
only the `_DEFAULT` constant + resolver, no direct role literal at a compose site.

---

## AS-36 — Composer copy contracts keyed to the dev brand (KeyError crashes + specimen leaks)

**Rule**: shared composers may not treat the development brand's copy keys as a schema:
every `copy["key"]` access must tolerate absence (empty-string semantics, section
omitted) because other brands' `brand.yaml` carries different section copy. And every
PREVIEW/specimen string (captions, headlines, placeholder labels) must derive from the
ACTIVE brand's own measured copy, voice, or law facts — a preview tier is a render of
THIS brand, not a gallery of the first brand's content.

**Why it happens**: composers are written against one brand.yaml whose `sectionCopy`
always has `panelTitle`, `subhead`, etc., so bare dict indexing never fails in
development; the crash only fires when a leaner brand routes through the same composer.
Specimen strings feel like neutral fixture text ("WoodWave Gallery", "Melodrama
ligatures…") because in the dev repo they ARE the brand — the leak is invisible until
the preview renders under a different brand.yaml and still talks about wood galleries.

**Caught here**: Remote E2E run (2026-07-03) — the components-preview tier crashed with
`KeyError: 'panelTitle'` (`copy_for` → ruled-list composer) and, before that, every
non-WoodWave preview carried WoodWave captions/headlines. Fixed:
`compose_section._SafeCopy` (missing key → `""`, composers' existing emptiness guards
then skip the fragment) + `render_components_preview._specimen`/`_brand_law` (headline
from the brand's own measured `blockMapping`/name; captions computed from the brand's
actual law facts: fonts, radius stance, cta shape) + preview `main()` attaches the
active brand's asset inventory so preview art rides AS-34 resolution.

**Verify**: unit — `test_remote_fix.py::PreviewTierSafety` (`copy_for` tolerates missing
keys; specimen headline derives from measured copy). Live — regenerate
`render_components_preview.py` for a non-WoodWave brand: zero tracebacks, zero WoodWave
strings/art in the output HTML. Grep — `rg 'copy\["' brand_pipeline/compose_section.py`
finds only `_SafeCopy`-backed access.

---

## AS-37 — Device CSS shipped unconditionally (dormant grammar that trips other brands' law)

**Rule**: a style-gated DEVICE (the inset art-panel hero: a rounded, art-painted panel
hosting the hero) enters a page in three law-ordered steps — brand neverDo first
(`no-radius`/`no-gradients` brands never render it), style-layer qualitative flag second
(`artPanel: inset|none` front-matter), brand tokens last (radius via the
`--radius-panel → --radius` chain, paint from the brand's OWN art per AS-34). And its
CSS ships ONLY on pages whose sections actually render the device: a dormant
`border-radius:` rule in a shared scaffold is not "inert" — static law checks read page
TEXT, so unconditional device CSS makes every sharp-cornered brand's page carry a
rounded-device declaration it must fail.

**Why it happens**: shared scaffold blobs are append-only by habit ("scoped to its own
classes, emitting all of them is idempotent") — which holds for GEOMETRY but not for
LAW-VISIBLE properties (radius, gradients, shadows): the static checker judges
declarations, not computed usage. And a new device's first implementation naturally
lands inside the archetype scaffold it extends, inheriting that unconditional emission.

**Caught here**: this fix batch (2026-07-03) — the art-panel CSS first landed inside
`SCAFFOLD_HERO_CSS`; `tools/phase0_regate.py` immediately flagged `neverDo no-radius
PASS->FAIL` on every regenerated WoodWave page (the pages never rendered a panel; the
rule text alone tripped `_ck_no_radius`). Fixed: split into
`SCAFFOLD_ART_PANEL_CSS`, emitted by `scaffold_css_for`/`build_page` only when a layout
carries `_artPanel`; regate returned to zero PASS→FAIL with the WoodWave matrix
byte-parity on CSS-visible law.

**Verify**: unit — `test_remote_fix.py::InsetArtPanel` (style flag parses; permission
gating: no-radius/no-gradients brand or `artPanel: none` style refuses; panel hero
renders with brand-treatment art; declared-but-absent art paints the plain panel).
Regate — `tools/phase0_regate.py` zero PASS→FAIL. Grep — `rg 'cs-hero-panel'
runs/*/brand/compose/*/index.html` hits only pages whose composition declares the
panel.

---

## AS-38 — Bootstrap-brand DNA frozen into shared code paths (cross-brand contamination)

**Rule**: the shared pipeline (composers, prompt grammar, specs, preview/gallery,
wildcard machinery, kit export) must carry ZERO brand-specific data — no copy tables,
nav label lists, page orders, accent-layout ids, hero design law, asset/font
registries, layout-id-keyed ladders, or brand-named prompt rules. Brand facts live in
that brand's `runs/<brand>/brand/` data (`brand.yaml`, `section-copy.yaml`, assets) and
are attached to the doc at load time; shared fallbacks either derive from the ACTIVE
brand's extracted evidence and degrade to empty/neutral (copy/content — the `_SafeCopy`
/ AS-34 posture), or fail loud (structure/law — the CR-3 posture). Never borrow another
brand's values as a default.

**Why it happens**: the first brand extracted IS the pipeline's development fixture, so
its literals get typed straight into module constants ("we need *a* default") and its
rules get written into shared prompt grammar as if they were universal law. Every
render of that brand still looks perfect, so nothing complains until a SECOND brand
renders with the first brand's nav, voice, hero styling, or forbidden-device rules.

**Caught here**: contamination-fix batch (2026-07-05) — WoodWave was baked into
`compose_section.py` (`SECTION_COPY`/`LAYOUT_COPY`/`LAYOUT_IMAGES`/`ASSET_SOURCES`/
`SELF_HOSTED_FONTS`), `compose_page.py` (`DEFAULT_ORDER`, `ACCENT_LAYOUT`, hardcoded
hero-override CSS), `generate_composition.py` (the `opening-bookend` gate default),
`wildcard_generator.py` (WoodWave-layout-keyed ladder + hero-ghost copy),
`styles/composition-rules.md` §2/§4 (WoodWave neverDo rules stated as the universal
grammar), and `export_kit.py` (shipping this registry verbatim, case studies and all,
into every kit). Every non-WoodWave brand rendered "About / Gallery / Exhibition /
Visit" + "Buy Tickets" nav, WoodWave hero CSS, and prompt rules naming WoodWave.
Fixed by relocating all of it into `runs/woodwave/brand/` data, deriving/failing-loud
in shared code, re-keying the wildcard ladder to scaffold families, rewriting the
grammar generically, and distilling this registry at kit export.

**Verify**: unit — `tests/test_no_cross_brand_dna.py` (static AST scan of shared
modules' string literals + `styles/*.md` + `contracts/**/*.yaml` against a hardcoded
WoodWave corpus; functional render of a synthetic navbar-less brand asserts no corpus
term and a wordmark-only nav). E2E — re-render a non-WoodWave brand and grep the output
tree for the corpus; assemble a generation prompt and grep it. Regression — WoodWave
lanes byte-identical (or comment-only) against pre-fix baselines.

---

## AS-39 — Chrome PRESENTATION DNA in shared renderers (casing / separators / surfaces)

**Rule**: AS-38's *presentation* subclass — beyond copy and structure, a brand's chrome
STYLING must never be a shared-code default. No hardcoded `text-transform` casing (ride
the generated `--case-<tier>` variables, fallback `none`), no Python-side label casing
(`.upper()` is styling), no hardcoded separator glyphs in nav/footer/list markup (a
declared `navbar.separator` / `footer.separator` renders; silence renders spacing
only), no assumed chrome surface (nav/footer/logo surfaces resolve from the brand's
measured chrome colors to its OWN roles — `nav_surface_role` / `footer_surface_role`),
no single-family action grammar (the nav CTA dispatches through the law-first
`cta-shape` like every action), and chrome interactions (hover wash / color-shift)
render only from measured evidence.

**Why it happens**: content decontamination (AS-38) moves the *words* out but leaves
the *look* behind, because presentation hides in CSS literals, harness styling, and
"tiny" separator spans that carry no greppable brand name. The bootstrap brand's
tracked-caps dark slash-separated chrome still reads perfect on that brand, so every
render stays green until a sentence-case light-chrome brand ships wearing it.

**Caught here**: nav-fix batch (2026-07-07) — after the AS-38 batch, Remote (light
`#eff0f0` bar, sentence-case Inter links, no separators, pill hover, filled nav CTA)
still rendered WoodWave's slash separators between nav links and footer social links
(`render_navbar`/`render_footer` hardcoded `/` spans), Python-uppercased footer
sitemap/social labels (`footer_content` `.upper()`), a components-preview gallery with
~30 hardcoded `text-transform: uppercase` rules, a slash `.ex-li` list marker, "/ "
eyebrow prefixes, and navbar/logo/footer demos pinned to `.surface-dark` ("the brand
confines nav to dark bands" — one brand's law), plus a typographic arrow nav CTA on
filled-button brands and Remote's measured nav hover wash dropped on the floor.

**Verify**: unit — `tests/test_no_cross_brand_dna.py::test_no_hardcoded_chrome_presentation`
(AST scan: no `text-transform: uppercase|capitalize|lowercase` and no non-empty
`cs-sep`/`c-foot-sep` glyph literals in shared modules) and
`FunctionalRender::test_no_inherited_chrome_presentation` (a declaration-less synthetic
brand renders zero separator spans and no literal casing). Regression — the bootstrap
brand's lanes pixel-identical with its devices re-declared as ITS brand data
(`navbar.separator`, `footer.separator`, `tokens.type.eyebrow.prefix`).

---

## Adding a new entry

Copy this shape: **Rule** (the imperative, one or two sentences) / **Why it happens** (the
plausible-but-wrong reasoning that produces it) / **Caught here** (the concrete instance —
name the file, the values, the visible symptom) / **Verify** (a repeatable check, ideally
scriptable). Keep entries brand-agnostic — this file lives in `brand_pipeline/spec/`
alongside `brand-schema.md`/`layout-analyst-skill.md` because these failure shapes recur
across ANY project this pipeline generates, not just WoodWave.
