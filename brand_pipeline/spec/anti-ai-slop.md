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
5. **Scope check before adding**: this registry owns UNIVERSAL failure shapes — wrong on
   any surface, in any section. A failure only falsifiable inside ONE section family's
   anatomy (stat-unit parallelism, tier-card slot parity, FAQ answer length…) belongs in
   `contracts/section-rules.yaml` (spec/section-rules.md; enforced by
   `section_rules_audit.py`) — those rows cross-reference AS ids via `delegatedTo` instead
   of duplicating them, and their `registryCandidates` block is the promotion path INTO
   this registry when a section-scoped rule turns out to be universal.

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

## AS-23 — Image backing outlives its loading/error state

**Rule**: every unresolved/loading or broken content-image slot carries a PLACEHOLDER
BACKING — a subtle diagonal
hatch (`repeating-linear-gradient(135deg, …13px/26px)`) built from the surface's OWN
tokens: stripe A is `var(--c-paper)`, stripe B is `color-mix(in srgb, var(--c-paper) 93%,
var(--c-ink))`. It shows while the image loads and remains on a broken src. After a
successful load it must be removed completely: transparent pixels reveal the actual
parent/surface behind the asset, never stripes. The colors are NEVER hardcoded at system
level (AS-01): the same one rule resolves to a deep-brown hatch on a dark section and a
gently-shaded cream hatch on a light one. State is load truth, not `src` presence:
`data-load-state="loaded"` is stamped only after load (including cache-complete images);
`error` retains the fallback, and lazy images transition when their eventual load fires.

**Scope — ART-TAGGED media is exempt by contract**: non-photographic art (illustrations,
product-UI graphics, marks — the renderer's `c-image--art` / `c-acc-media--contain`
classes, driven by the brand's tagged asset inventory) deliberately keeps
`background: none` as its JS-disabled safe fallback. The renderer's tag decision is the
single shared law: the audit exempts exactly the classes the renderer stamps, never a
parallel filename heuristic of its own (two independent judgments would drift — the W3
failure class, where the audit flagged what the renderer did on purpose).

**Why it happens**: images "always load" on the developer's machine, so the unpainted
frame state is never seen; a backing added later gets hardcoded to the one brand being
looked at, or is left permanently on the `<img>` where transparent pixels expose it after
load. The first is AS-01 with extra steps; the second conflates "has src" with "loaded."

**Caught here**: WoodWave kit-field homepage review — image frames sat on the raw
section background until load. Added as the system-level `.c-image` rule in
`component_render.COMPONENT_CSS` (per-surface by construction since it reads
`--c-paper`/`--c-ink`); on WoodWave's dark hero it resolves to rgb(58,45,31)/rgb(51,39,26).

**Verify**: gate — `slop_audit.mjs` AS-23 checks the lifecycle state against computed
paint: unresolved/error images contain `repeating-linear-gradient`; successfully loaded
images do not (logos/icons under 80px exempt; `.c-image--art` /
`.c-acc-media--contain` exempt per the JS-disabled art contract above).

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

## AS-40 — Multi-open disclosure systems (menus/accordions that stack open states)

**Rule**: A disclosure SYSTEM (accordion, nav mega-menu, dropdown family) opens ONE
member at a time unless the brand's evidence shows stacked open states. Prefer
platform-enforced exclusivity (`<details name="…">` shares one exclusivity group per
system; hover/focus-scoped panels that close when the pointer leaves) over JS
bookkeeping. The OPEN member is evidence-driven: compose the item the capture shows
expanded (its inversion/surface from the brand's own token roles); with no open-state
evidence, all-closed is the degrade — never "open them all so the content is visible".

**Why it happens**: generators optimize for "show everything" — an accordion with
every panel expanded screenshots as richer content, and hand-rolled open/close JS
defaults to independent toggles because exclusive groups need shared state. Real
design systems treat disclosure as focus management: one open panel is the resting
grammar users see in the capture.

**Caught here**: P2 replica gate (2026-07-07) — the source's feature accordion renders
exactly one ACTIVE item (deep-accent inset inversion, white ink); the composed replica
drew all rows idle/closed (capability gap), and the naive alternative (all-open) would
have mis-stated the brand's grammar. Fixed with the `<details name=…>` accordion device
in `compose_section._compose_accordion_split` — one `open` item max, platform-exclusive.

**Verify**: unit — `tests/test_p2_interaction_devices.py` (composed accordion carries
exactly one `open` item, all items share one `name` group). Manual — click a second
trigger in the composed page: the first closes without any script.

---

## AS-41 — Scroll-reveal without a failsafe (IntersectionObserver strands content)

**Rule**: Any reveal choreography that HIDES content until an observer callback fires
must carry redundant failsafes: (a) the hidden initial state applies only under a
JS-added gate class (no JS ⇒ nothing is ever hidden), (b) reduced-motion and
missing-IntersectionObserver paths return early BEFORE the gate class is added, and
(c) a timed fallback force-reveals everything after a deadline (seconds, not
minutes) — a mis-rooted observer, iframe quirk, or never-firing callback must cost
motion polish, never content. The reveal is an enhancement, not a gate.

**Why it happens**: reveal-on-scroll is written against the happy path (observer
fires as you scroll), and the hidden pre-state is baked into the stylesheet because
that is the easy place to put it. Every local test scrolls, so the strand only
surfaces in embedded/headless/print contexts — exactly where screenshots and gates
run.

**Caught here**: Phase D screenshot pass — full-page captures shot before the scroll
pass showed sections stuck invisible (`opacity: 0`) because the IO reveal had not
fired for below-fold targets; the replica gate now scroll-passes before shooting, and
`compose_page.REVEAL_SCRIPT` adds the 4s timed force-reveal on top of its existing
no-JS/no-IO/reduced-motion early-outs.

**Verify**: unit — `tests/test_p2_interaction_devices.py` (REVEAL_SCRIPT carries the
gate class, the early-outs, and the timed failsafe). Manual — load a composed page
with JS disabled: all content visible.

---

## AS-42 — Marquee seam math (loops that jump, drift, or change speed per content)

**Rule**: An endless marquee is TWO IDENTICAL halves inside one `max-content` track,
looped by a single `translateX(0 → -50%)` keyframe — the wrap lands exactly on the
second half's start, so the seam is invisible by construction (each half carries a
trailing copy of the inter-item gap; the aria-hidden duplicate half is presentation,
not content). Duration is px/s-CONSTANT: derived from the measured half width (one
shared surface speed across marquees), never a fixed time per marquee (which makes
long tracks sprint and short tracks crawl). Reduced-motion pauses at the resting
offset; the static row (= the animation's t=0 frame) is the degrade for brands whose
evidence declares no marquee.

**Why it happens**: the naive marquee animates `translateX(0 → -100%)` on a single
copy (hard jump at wrap), pads with a hand-tuned duplicate ("looks seamless at my
viewport"), and picks `30s` because it looked right for twelve logos — all three
break the moment content, gap, or viewport changes.

**Caught here**: P2 replica gate (2026-07-07) — the source logo strip is a
continuously translating JS-timed track (`motion-audit jsTimingNotes`: duration set
per-content at runtime); the composed replica rendered a static spaced row. Fixed
with the seam-correct device in `compose_section.compose_generic_flow` +
`compose_page.MARQUEE_SCRIPT` (half-width ÷ 90px/s), item-count fallback duration
for JS-off renders.

**Verify**: unit — `tests/test_p2_interaction_devices.py` (two byte-identical halves,
-50% keyframe, reduced-motion pause rule ships with the device). Manual — let the
composed strip run one full loop: no visible jump at the wrap point.

---

## AS-43 — Disabled/inactive states faked with opacity (or filters) instead of colors

**Rule**: A control's disabled/inactive state renders with the brand's own DISABLED
COLOR tokens (measured `bgDisabled`/`fgDisabled` fills and inks) — never
`opacity: 0.5`, `filter: grayscale(…)`, or blend tricks on the enabled state.
Opacity ghosting composites against whatever sits behind the control (unpredictable
contrast on image/dark/panel surfaces, text bleeding through), inherits onto children
(icon + label wash out together regardless of their own tokens), and misstates the
brand (the measured disabled gray is a DESIGNED color, not 50% of the primary).
Absent disabled-color evidence, don't invent the state at all — render the enabled
resting state.

**Why it happens**: opacity is one property, works on any button family without new
tokens, and pattern-matches every CSS tutorial. Extracting the real disabled pair
takes a measurement pass, so generators reach for the shortcut exactly where evidence
is thinnest.

**Caught here**: P2 rule-hardening (2026-07-07) — the preview's measured button
families already do this right: a family with measured `bgDisabled`/`fgDisabled`
emits a COLOR disabled rule that explicitly resets the harness dim (`opacity: 1`,
`render_components_preview` button-family CSS). The gallery's generic state-row
exhibits keep a dimmed HARNESS fallback for evidence-less demo chips — that is a
gallery exhibit device, not brand grammar, and it must never migrate into composed
pages or generated kits (the competing kit faded disabled buttons to 40% opacity —
unreadable on its dark surface bands).

**Verify**: unit — `tests/test_p2_interaction_devices.py` (a measured-disabled
family's preview CSS carries the color rule with the `opacity: 1` reset; composed
page CSS carries no opacity-based disabled rules). Review — any new state CSS
touching `disabled` in composers/kits greps clean of `opacity`/`grayscale`.

---

## AS-44 — Structural defaults competing with recorded pattern facts (facts must win)

**Rule**: when a pattern's `contentShape` records presentation facts — `alignment`,
`stackMeasure`, `bandPadding`, `deviceGeometry`, `mediaScale` — every composer that
renders a section seeded from that pattern MUST resolve its alignment, geometry, and
measure from those facts. The structural default (the generic split registration, the
46rem column, the site-average rhythm, the left-anchor literal) is exclusively the
DEGRADE for patterns without the fact — never a competing source of truth that a lane,
adapter, or composer branch is allowed to fall back to while the fact exists upstream.
A fact that is recorded but dropped anywhere along the resolution chain (pattern →
composition → adapter → stamp → composer) is a bug in the chain, not a rendering choice.

**Why it happens**: each adapter hop re-serializes the section into its own vocabulary,
and any hop that doesn't model a fact silently drops it; the composer downstream still
renders *something* (its structural default), so nothing fails loud. The output looks
plausible in isolation — it only reads wrong next to the source or next to the other
lane that kept the fact.

**Caught here**: fid10 (2026-07) — the composed-from-catalog page rendered every
section at structural defaults (hero collapsed to a narrow centered panel, accordion
packed left with dead right space, split media cover-cropped) while the replica lane
rendered the SAME patterns from the same library correctly: the catalog lane's
`composition_to_doc` post-processed `composition_to_layout` differently from the
replica lane, dropping the authored copy overlay and brand-layout declarations, and
the fact stamps only fired on the lane that kept the `patternRef`.

**Verify**: unit — `tests/test_fid10_lane_parity.py` (`LaneParityTest.
test_stamp_parity_for_every_fact_class` asserts every stamped fact class survives the
catalog path non-vacuously). Review — any new `contentShape` fact needs a consumer
test proving the composed markup differs from the no-fact degrade.

---

## AS-45 — Centered stacks collapsing to hug/prose width (measure belongs to paragraphs)

**Rule**: a section CONTAINER spans the shared content measure and centers itself
(`max-width: var(--content-measure…); margin-inline: auto`) — a bare `max-width` with
no centering margin is a left-packed band at any viewport wider than the measure. The
prose measure (`ch`-based clamps) applies to PARAGRAPH slots only: headings, eyebrows,
action rows, and media hug or span their own content INSIDE the full-measure container.
A centered stack must never inherit a narrow slot's width — "hug" is a slot behavior,
never a container behavior, and a container must never be sized by its narrowest child.

**Why it happens**: one `max-width` on the wrapper "fixes" an over-wide band at the
authoring viewport and nobody widens the window; a ch-clamp added for body text gets
applied to every flow item because the loop doesn't branch by contract — the clamp
resolves against the wrapper's inherited body size, so even headings wrap inside a
~500px box and the whole stack reads collapsed.

**Caught here**: fid6→fid10 (2026-07) — `SCAFFOLD_FLOW_CSS` carried `max-width: 72rem`
with no `margin-inline: auto` (partner/badge/logo walls packed left with dead space
right at wide viewports) and clamped every `.cs-flow-item` to 62ch (centered stacks
collapsed to ~500px); the conversion stack's 46rem/40ch structural defaults did the
same to a closing band measured at an 870px column.

**Verify**: unit — `tests/test_fid10_lane_parity.py` (`ContainerLawTest`: flow, split,
conversion panel, and page-footer content all cap at the shared measure AND center;
prose clamps ride `--prose`/paragraph selectors only). Manual — view the composed page
at ≥2× the content measure: every band's content column sits centered, none hug the
left padding edge.

---

## AS-46 — Composition lanes with private adaptation forks (lane fact-parity)

**Rule**: every lane that renders brand sections from patterns — the composed-from-
catalog page, the replica assembler, the components-preview demo hydrator, and any
future lane — MUST consume pattern facts through the SAME shared adaptation path (one
function owning the brand-aware merge: authored copy overlay, brand-layout declaration
ride-through, fact stamping). A lane must never re-implement its own partial copy of
that post-processing: two hand-maintained copies WILL drift, and the drift is invisible
until the lanes render the same section differently. When a lane needs an extra step,
add it to the shared path (flag-gated if truly lane-specific), never as a private fork.

**Why it happens**: the second lane starts as a copy-paste of the first lane's five
post-processing lines ("it's just a pop and a merge"); the first lane later grows a
sixth line (an authored-copy overlay, a declaration ride-through) and nobody remembers
the copy exists. Each lane passes its own tests; only cross-lane comparison exposes it.

**Caught here**: fid10 (2026-07) — `compose_replica.build_replica_page`,
`render_components_preview.compose_pattern_docs`, and `compose_from_composition.
composition_to_doc` each carried a private variant of the same adapt-section block; the
catalog lane's variant skipped the authored `layoutCopy` merge and dropped
`eyebrowRegister`, so the composed page lost authored headings/subheads and per-section
eyebrow registers while the replica page kept them. All three now call
`compose_from_composition.adapt_brand_section` — the single shared path.

**Verify**: unit — `tests/test_fid10_lane_parity.py` (`LaneParityTest.
test_catalog_path_matches_direct_path`: the catalog lane emits the SAME adapted layout
+ copy entry as calling the shared helper directly; `AdaptBrandSectionTest` locks the
helper's merge semantics). Review — grep for `composition_to_layout(` call sites: every
caller outside `adapt_brand_section` itself must justify why it bypasses the shared path.

---

## AS-47 — Interactive state grammar shipped without its captured motion

**Rule**: when a brand's evidence captures the MOTION of an interaction mechanic
(disclosure panel height, trigger state wash, marker turn, active-surface inversion —
durations, easings, reduced-motion behavior), EVERY rendering of that mechanic in every
lane and scaffold must ship that motion: a new scaffold that re-renders the same
mechanic (a FAQ list re-rendering the accordion's details rows) inherits the motion
grammar, not just the markup and state paint. Implement the mechanic's motion as ONE
shared CSS source parameterized by selector family — never a second hand-written copy
(AS-46 applied to interaction CSS). Timing/easing values ride the brand's motion
aliases BARE (no literal fallbacks): a brand with no captured motion language degrades
to the instant toggle, never to an invented 200ms.

**Why it happens**: the state grammar is what screenshots show, so the new scaffold
faithfully reproduces surfaces, inks, radii, and open-state inversion — and looks
finished in every static capture. Motion lives only in the ORIGINAL component's CSS
block, which the new scaffold never imports because its selectors differ; no static
gate measures a transition, so the fork ships silent. The defect is invisible until
someone clicks.

**Caught here**: event-genlaunch (2026-07) — the composed homepage's accordion device
animated (`::details-content` height tween + chevron turn + state fade on
`--c-motion-base`/`--c-motion-fast`/`--c-ease`, fid5) while the event page's agenda and
FAQ sections — the SAME details-rows mechanic through the new FAQ scaffold — rendered
with zero transitions: the brand's captured 150/200ms motion facts never reached them.
Fixed by factoring the fid5 motion into `compose_section.disclosure_motion_css`
(selector-parameterized shared block, gated on the brand's motion trio + easing),
consumed by both the accordion device and the FAQ scaffold in every lane.

Also caught (fix5 2026-07): the nav-chevron fact-less degrade in
`component_render.nav_affordance_css` shipped an INVENTED rotation tween
(`transform var(--c-motion-fast, 0.2s)`) — exactly the invented-200ms degrade this
rule forbids. Fixed to `transition: none` (the instant toggle). Separately, the
user's curated ruling on the MEASURED chevron tween ("no spin — swap instantly")
rides the fact as `curation.motion` (brand-schema §4.4c applied to a chrome fact):
generation lanes honor it; the replica lane keeps the measured transition.

**Verify**: unit — `tests/test_event_scaffolds.py` (`DisclosureMotionTest`: a
details-emitting layout on a motion-bearing doc MUST emit the shared block per family;
a motion-less doc emits ""; timing rides bare aliases with zero literals; the scaffold
constants may never grow a private `::details-content` copy back) and
`tests/test_p2_interaction_devices.py` (`test_disclosure_animation_rides_motion_vars`).
Render — grep the emitted page: every `<details` scaffold family present implies a
matching `::details-content` transition block when the brand carries motion tokens.

---

## AS-48 — Uniform stack gap where a captured relational rhythm exists

**Rule**: when a brand's evidence captures a RELATIONAL spacing ladder (per-pair rungs
between content roles — label→headline, headline→description, description→action, plus
the content-block row rhythm), header/anatomy stacks must render as NO-GAP columns
whose every seam is a per-pair margin riding the authored ladder tokens — the source's
own mechanic. A uniform container `gap` on such a stack is a named defect: it flattens
three different measured seams into one invented rhythm (and stacks ON TOP of any
pair margin that does exist, inflating it). Uniform gap remains legitimate ONLY as the
degrade for brands whose evidence exposes no ladder, and for genuine grid/card
gutters and control rows — which must themselves ride captured row-gap/column-gap
facts where those exist.

**Why it happens**: `display:flex; gap:` is the modern one-liner for a vertical stack,
and a single gap value looks "clean" in code review. The source's rhythm lives in
per-element margins (`margin-bottom: var(--label-headline-spacing)`) that no screenshot
labels, so the generator reads the average spacing, picks one gap, and every pair seam
lands wrong by a little — too much under the eyebrow, too little over the CTA — while
still looking plausibly finished.

**Caught here**: Remote (fid11 2026-07) — the source's header component is a flex
column with NO gap; each element carries its own semantic margin from the
`--zora-st-*` ladder (label→headline 12px, headline→description 16px,
description→button 32px, content rows 64px at the 1440 tier), while the composers
flattened everything with uniform `--c-block-gap` (2.5rem) container gaps — the FAQ
column even added its gap on top of the eyebrow wrap's own margin. Fixed by authoring
the complete generic ladder (`eyebrow-to-heading`, `heading-to-body`, `body-to-cta`,
`block-to-block`, `column-to-column`, + `body-measure`/`header-measure` companions)
into `tokens.spacing` and converting the stack mechanic via ONE gated source
(`compose_section.relational_ladder_css`: gap:0 + per-pair margins; `compose_flow`
stamps `data-row` so flow seams key on content relationships), with `--c-block-gap`
itself now resolving from the brand's `block-to-block` rung.

**Verify**: unit — `tests/test_relational_ladder.py` (ladder-bearing doc ⇒ the gated
block ships with gap:0 + pair rungs and zero literals; ladder-less doc ⇒ ""; rhythm
prefers `block-to-block`). Validator — C15 completeness: mined relational custom
properties ⇒ every exposed rung authored, fail loud. Render — inspect a header run's
computed seams against the brand's rung values (eyebrow→heading == the authored token,
not the uniform gap).

---

## AS-49 — Headers aligned by scaffold habit instead of the brand's captured grammar

**Rule**: generated headers must follow the brand's captured alignment grammar —
`layoutGrammar.headerContext` (split-column vs standalone-stack anchors, derived from
the observed patterns' measured alignment) — resolved through the ONE alignment chain:
`section explicit > pattern curation (generation lanes) > pattern
contentShape.alignment > brand headerContext grammar > style role default`. A
scaffold-hardcoded `text-align`/`align-items` on a header run is a named defect:
alignment is a brand fact with a resolution order, never a scaffold default. Explicit
per-pattern facts still win over the grammar (the brand-default layer BENEATH them —
exactly what newly GENERATED sections without facts need) — UNLESS a design curator
recorded a `curation: { alignment: { resolve: follow-grammar } }` ruling on the
pattern (brand-schema §4.4c): the source dissents from its own grammar, the curator
resolves the dissent toward the grammar for OUR generated output, and the pattern's
measured fact is retired for generation lanes only. The REPLICA lane ignores curation
(it rebuilds the source 1:1; the measured fact stays its truth and its gate score must
not move). Contexts the evidence never corroborated stay un-authored and fall through
to the style layer.

**Why it happens**: each scaffold gets built against one reference section, so its
header alignment gets baked in as CSS (`.cs-modules-intro { text-align: left }`) and
looks right for that section. The next composition reuses the scaffold in the other
context — a standalone pricing header on a brand that centers standalone headers —
and ships left-aligned, because nothing connected the scaffold to the brand's
contextual rule; per-section facts can't help a section that HAS no pattern.

**Caught here**: Remote (fid11 2026-07) — the source aligns its one header component
LEFT inside every split column (hero, accordion, infra: 3/3 observed patterns, media
counterweight) and CENTERS it standing alone atop stack/grid sections (6/7 observed:
marquee, inline CTA, partner row, badge strip, closing CTA, testimonial header; the
one left standalone header rides its own explicit pattern fact + cards counterweight,
which outranks the grammar). The event page's bento and pricing sections — generated,
pattern-less, fact-less — rendered their intro headers by scaffold habit instead of
centering. Fixed by authoring `layoutGrammar.headerContext` (splitColumn: left +
media counterweight / standaloneStack: centered) and adding the brand layer to
`resolve_alignment` (stamped `data-align-source="brand"`).

**Verify**: unit — `tests/test_relational_ladder.py` (`HeaderGrammarTest`: grammar
resolves per context; pattern/section facts outrank it; chrome archetypes and
grammar-less brands unchanged). Validator — C18: both contexts corroborated ⇒ grammar
authored and matching the observed majority, fail loud. Render — a generated
fact-less standalone header stamps `data-align="centered" data-align-source="brand"`
on a brand whose grammar says so.

---

## AS-50 — Ragged card rows where the brand's evidence captures grid equalization

**Rule**: when a brand's evidence captures grid equalization
(`contentShape.gridEqualize`, brand-schema §4.4d), cards sharing a grid row must
render EQUAL height, with the slack absorbed by the captured slot and action rows
pinned per the captured anatomy (`actionPinned` — the `margin-top: auto` seam, with
the pair-margin rung preserved as the pinned row's minimum seam so the tallest card
never renders its action flush against the body). Ragged bottoms in an equalized
grid, and floating CTAs mid-card from equalizing WITHOUT the pinning fact, are both
named defects — the second is why the heights fact and the anatomy facts travel
together. The pattern-less generated card scaffolds (bento mosaic cells, pricing
tier panels) follow the same rule through the brand's derived grammar
(`grid_equalize_grammar`): a brand whose observed card grids equalize gets equalized
mosaic rows and tier rows; an all-hug brand gets content-sized cells; a fact-less
brand keeps the scaffold's built-in behavior byte-identical. A `heights: hug` fact
is equally binding: content-sized cards on a brand that hugs, never
equalization-by-default.

**Why it happens**: CSS grid stretches items to the row track by default, so a card
grid LOOKS equalized until one scaffold sets `align-items: start` for an editorial
stagger layout and a declared N-up grid variant inherits it — then every card hugs
its content and row bottoms go ragged. The inverse failure is equalizing blindly:
stretch alignment without the flex-grow slack slot and the pinned action row leaves
the extra height BELOW the action (CTA floating mid-card, dead space under it),
which reads broken in exactly the way the source's own anatomy avoids.

**Caught here**: Remote (fid14 2026-07) — the source equalizes both observed card
grids (workflow cards: 3 cards all 536px with differing text, body `flex-grow: 1`
stretched 240→288px, image well fixed 248px; testimonials: all cards 391px while
quotes run 135/108/108px, the quote frame flexes and the author row pins after it).
Our composed workflow grid rendered 620/590/590px — the cards scaffold's
`align-items: start` (correct for its stagger layout) leaked into the declared 3-up
grid, and `.c-arrow-link` rows rode the ladder margin instead of pinning. Fixed by
authoring the facts on both grid patterns and emitting per-section
`pattern_equalize_css` (stretch + pinned trailing actions with the
`--space-body-to-cta` rung as the minimum seam).

**Verify**: unit — `tests/test_fid14_grid_equalize.py` (fact accessor, stretch/hug/
degrade emission, pinned action rows, bento/tier grammar release, byte-identical
fact-less pages). Validator — C20: card-grid patterns carry `gridEqualize` or the
not-observed marker, fail loud. Render — measure per-row card heights in the
composed grid (equal despite differing content) and the pinned action's bottom
offset (constant across the row's cards).

---

## AS-51 — Heading-scale inflation below the hero (every section a poster)

**Rule**: only the OPENING section rides the brand's display/poster register. A
non-hero section's heading that declares no explicit level demotes to the brand's
measured section-heading tier (`section_heading_level`: the extracted h2 role when
the type ladder carries one; the display degrade only for brands without the fact).
An AUTHORED level always wins — a composition may deliberately declare a display
statement — but the DEFAULT must never be display. This applies to every path that
resolves a heading register: contract slot mappings (`usage.level`), composer copy
(`headingLevel`), and composer-internal defaults (the info-band's band heading).
Multiple H1-scale heads on one page is a named defect, not a stylistic choice.

**Why it happens**: the hero composer's display default gets copied into new section
composers and slot translators one at a time ("big headings look impressive"), and
each looks fine in a single-section preview — the inflation is only visible on a
composed PAGE, where four sections shout at the same register and the type
hierarchy (the brand's most-measured fact) flattens.

**Caught here**: remote stress-playbook (2026-07) — `pb-stats`/`pb-compare` generic-flow
headings and the `pb-process` info-band intro all rendered at the display tier
(three poster heads below the hero) because `_inline_props`/`_split_copy` defaulted
`level` to `display` and `compose_info_band` hardcoded it. Fixed by demoting
level-less non-hero heading/header slots + composer `headingLevel` to
`section_heading_level(doc)` in `adapt_brand_section` (W5), with the authored
`copy.level` override carried through.

**Verify**: unit — `tests/test_stress_playbook_weaknesses.py` (demotion below the
hero, authored-level override, hero untouched). Render — count elements at the
display size in a composed page: exactly the hero's (plus any AUTHORED display
statements), never a default.

---

## AS-52 — Phantom media: default-art backfill in attributed/quote modules

**Rule**: default-art backfill (the brand-asset rotation that fills a card grid's
unbound media wells) must never inject media into a QUOTE/TESTIMONIAL module — a
module carrying person attribution (name / role / avatar fields). Those modules are
text-first: only an EXPLICITLY bound asset renders, and an asset-less quote card
composes with no media frame at all (no empty figure, no placeholder). A random
brand photo beside a person's words reads as a portrait of that person — invented
evidence about a real human, the worst kind of phantom content.

**Why it happens**: the backfill exists so photo-led card grids never render empty
wells, and it keys on "card has no asset" without asking what KIND of card it is —
the one content shape where an unrelated image actively lies (attribution binds the
imagery to a person) inherits a mechanism designed for anonymous editorial photos.

**Caught here**: remote stress-playbook (2026-07) — `pb-stories` testimonial cards
drew rotating product-UI art next to customer quotes with names/roles; the lane had
to pin explicit assets as a workaround. Fixed in `compose_features_cards` (W7):
person-attributed cards skip the `_assets[i % len(_assets)]` rotation, render
figure-less when unbound, and stamp `cs-module--quote` for audit traceability.

**Verify**: unit — `tests/test_stress_playbook_weaknesses.py` (quote card without
asset renders no `<figure>`/default art; explicit asset still renders; non-quote
cards keep the backfill). Render — every image inside a `cs-module--quote` module
traces to an authored `asset` binding in the composition/copy layer.

---

## AS-53 — Silent slot drops (declared content that simply vanishes)

**Rule**: every DECLARED slot a composition binds must either render through its
section's grammar or leave a VISIBLE trace — an `<!-- unresolved slot … -->` marker
in the emitted HTML (which the gate's slot-resolution invariant counts) or a loud
composer advisory. A composer that consumes a section may not quietly ignore slots
its happy path doesn't place: dropping an authored action/caption/media slot leaves
no marker, no warning, and no way to tell "deliberately elided" from "lost".
Elision is only correct for EMPTY copy (the AS-34 no-invention rule); authored
content that goes missing is a named defect even when the section "looks fine".

**Why it happens**: bespoke composers are written against the slots their reference
layout uses; extra slots fall off the end of the translator (`_split_copy` reads
what it knows) and nothing downstream notices because the unresolved counter only
sees slots the composer *attempted* — the drop happens before accounting.

**Caught here**: remote stress-playbook (2026-07) — `pb-process` (split + accordion
device) declared a `process-cta` action slot; `_compose_accordion_split` rendered
header/rows/media and returned without placing the cta and without a marker (W8).
Fixed: the accordion split renders the authored cta as its list-column foot
(`cs-acc-foot`, arrow-link register, left-anchored per the split grammar) when no
bound button slot already renders in the intro's actions row. Related counter bug
(W11): the CLI parity counter re-rendered slots per layout and reported phantom
`unresolved: 2` that the emitted page never carried — the count now reads the
EMITTED html's markers, so the number is the page's truth.

**Verify**: unit — `tests/test_stress_playbook_weaknesses.py` (accordion split
renders the authored cta; cta-less sections render no foot; `render_composition`'s
`unresolved` equals the emitted marker count). Gate — `slot-resolution` invariant:
declared-slot coverage against the emitted page, zero markers on a green lane.

---

## AS-54 — Double-application of a spacing mechanic (gap + owl margin)

**Rule**: exactly ONE mechanic owns each seam. When a stack is converted to the
relational ladder (owl `margin-block-start` per pair), every flex/grid `gap`
covering the same seam must be zeroed in that scope — and no LATER, more-specific
rule may re-declare the gap "for safety". A seam owned twice measures the SUM:
the ladder's 12px eyebrow→heading plus a re-added 12px flex gap renders 24px and
no single rule looks wrong in isolation.

**Why it happens**: a scaffold override wants to restate the component's look
("the split body header keeps the eyebrow gap") without checking which mechanic
already owns the seam at lower specificity. `gap` re-declared at higher
specificity beats the base `gap: 0` that the ladder relies on, and the owl margin
still applies — both mechanics fire.

**Caught here**: remote spacing baseline (2026-07) — `.cs-split-body .c-header
{ gap: var(--c-eyebrow-gap) }` in `SCAFFOLD_SPLIT_CSS` re-added the flex gap on
top of the ladder margin: every split-scope eyebrow→heading seam measured 24px
against the brand's 12px rung (replica + homepage + stress lanes). Fix: delete
the re-add; base `.c-header` + the ladder own the seam.

**Verify**: unit — `tests/test_relational_ladder.py` (ladder scopes zero their
gaps; no scaffold CSS re-declares gap inside a ladder scope). Gate — spacing
audit `header.eyebrow-to-heading` measures the rung once per lane.

---

## AS-55 — Pinned-slot collision (margin-top:auto with no minimum seam)

**Rule**: a slot pinned to the end of an equalized box (`margin-top: auto` on a
card's action row, an attribution row, a footer link) must carry a MINIMUM seam
on the box-to-box side facing the content above it — the ladder rung for that
relationship, expressed as the *preceding sibling's* `margin-bottom` (a real
box-to-box distance `auto` cannot collapse). `auto` may only absorb slack BEYOND
the rung. Padding on the pinned slot itself is not a seam: it moves the glyph
but the measured box-to-box distance still reads 0.

**Why it happens**: equalization thinking stops at "pin the action row so rows
align". In every card except the row's tallest the slack IS the seam, so the
collision only shows on the tallest card — the one place `auto` computes to 0.

**Caught here**: remote spacing baseline (2026-07) — equalized chapter/team card
grids pinned `.c-arrow-link` with `margin-top: auto`; on each row's tallest card
the CTA sat flush against the body (0px against a 14.4px body→cta rung). Fix in
`pattern_equalize_css`: the element preceding a pinned last-child action gets
`margin-bottom: var(--space-body-to-cta …)`; quote cards get the same guard on
the attribution row rung.

**Verify**: unit — `tests/test_fid14_grid_equalize.py` (the `:has(+ …:last-child)`
minimum-seam rule rides every equalize scope; no `padding-block-start` stand-in).
Gate — spacing audit `card.body-to-actions` ≥ rung on the tallest card per row.

---

## AS-56 — Scaffold families escaping the container law

**Rule**: every top-level scaffold wrapper that spans the page column MUST ride
the shared content-container rule (`max-width: var(--content-measure);
margin-inline: auto`) — by joining the one shared selector list, never by
declaring its own width. A scaffold that declares `max-width: 100%` (or nothing)
silently becomes a second, wider page column: sections stop sharing edges and
the page reads as two different sites stacked.

**Why it happens**: a new scaffold family is developed against a lane whose
parent already constrains width, so "100% works here"; nothing fails at author
time because the container law lives in a selector list the new family never
joined. The failure only appears when the scaffold lands in a full-bleed section
band.

**Caught here**: remote spacing baseline (2026-07) — the compare band's
`.cs-split-intro` declared `max-width: 100%` and rendered 1360px wide against
the brand's 1216px container law (stress lane). Fix: the intro joined the shared
container selector list in `SCAFFOLD_BASE_CSS`; the local width override was
deleted. Same pass: `.cs-split-intro` was also missing from the ladder's stack
registry (`_LADDER_STACKS`) — same failure shape, a registry a new family never
joined — heading→body measured 0px against a 16px rung.

**Verify**: unit — `tests/test_relational_ladder.py::LadderRegistryGuard`
(every `cs-*` scaffold selector that renders a `c-header` stack is either in
`_LADDER_STACKS` or on the documented exemption list; container-law membership
asserted for intro/grid wrappers). Gate — spacing audit `container.section-width`
per lane.

---

## AS-57 — Hover-only disclosure (no keyboard/AT parity for hover-driven UI)

**Rule**: any content revealed by `:hover`/`:focus-within` CSS (mega-menu panels,
dropdown menus, dismissible strips, overflow rails) must be operable and
*dismissible* without a pointer, and must expose its state to AT: the trigger is
a real `<button>` (or a link with disclosure state when it truly navigates),
`aria-expanded` mirrors the open state, Enter/Space toggles, and **Escape closes
and returns focus to the trigger** (WCAG 1.4.13 dismissible). The pure-CSS hover
path stays as the JS-off degrade; the structural script layers state on top —
never replaces it.

**Why it happens**: CSS-only disclosure is genuinely elegant (`:focus-within`
even passes a quick Tab test), so the keyboard story looks done. But CSS cannot
express `aria-expanded`, cannot implement Escape-to-dismiss, and a focused
trigger that shows a panel with no way to dismiss it TRAPS sighted keyboard
users on hover-card content (1.4.13's exact target).

**Caught here**: remote interaction baseline (2026-07) — all four compose lanes:
mega-menu triggers were `<a href="">` with no state (IC-NAV-01/02/04/08),
language `<details>` ignored Escape (IC-LANG-06), the banner close button was
wired to nothing (IC-BAN-04), edge-cut rails were unreachable by keyboard
(IC-CAR-01/05). Fix: `component_render.interaction_script` — guarded structural
blocks emitted only for components present on the page; triggers became real
buttons inheriting the measured pill styles (`button.cs-nav-trigger` UA reset).

**Verify**: unit — `tests/test_interaction_remediation.py` (trigger element,
state attributes, script emission guards). Gate — interaction audit `--strict`
lanes nav/lang/banner/carousel behavioral checks green.

---

## AS-58 — Advanced mechanics without content-shape preconditions

**Rule**: the simplest layout mechanic that reproduces captured evidence wins.
Every advanced device (interlock, float-wrap, overlap, straddle) must declare
evidence and content-shape preconditions at its adapter/composer boundary, plus
a plain, semantically complete degradation path. If any precondition is absent,
render the ordinary grid/stack/split; do not preserve complexity for its own sake.

**Why it happens**: a visually distinctive catalog pattern is treated as a
section label instead of a conditional device. Short copy, non-landscape media,
or an extra foot cluster then inherits float math, clearance, and drop offsets
designed for long editorial text, manufacturing voids with no source evidence.

**Caught here**: the Remote stress playbook's statement was a complete
eyebrow/heading/body/action stack beside one illustration, but rendered through
the editorial interlock's float, seven-column inset, large drop, and clear-both
foot. It now binds the ordinary media split. The interlock itself requires
explicit evidence, landscape media, its canonical caption/statement/media shape,
and no unsupported foot cluster; otherwise it degrades to that same split.

**Verify**: unit — interlock precondition tests cover every failed condition and
the explicit qualified path; rendered CSS contains grid mechanics and no
`float`/`clear` device law. Visual proof compares the complete split stack and
landscape media at desktop and the one-column responsive degrade.

---

## AS-59 — Multi-action groups without register hierarchy

**Rule**: in any multi-action group (hero action pair, bar action group, card
action row), exactly one action takes the brand's filled PRIMARY register; every
sibling takes a different measured register — the brand's outlined secondary,
ghost, or text-link. Two actions sharing the same filled register in one group
is a flag. Palette-agnostic by construction: the check compares computed paint
shape (fill vs stroke vs bare text), never any brand's hex values.

**Why it happens**: a generator resolves every action slot through the same
"CTA = primary button" default because the primary register is the only one it
confidently knows. The measured secondary register exists in the extracted
button matrix, but the action-pair authoring (slot role prose, action list) never
names it — so the renderer's family dispatch lands on primary twice. Visually
the group loses its hierarchy: two identical solid pills read as noise, and the
source's carefully measured secondary register silently disappears.

**Caught here**: the hubspot-v2 hero authored "Get a demo" + "Get started free"
as two solid accent pills; the source pairs the solid primary with an OUTLINED
secondary (bg white, 2px accent stroke — present in the measured button matrix
all along). Same failure shape appeared in the bar's action group when the
two-tier chrome contract landed (item-12b): both bar CTAs initially resolved to
the filled register.

**Verify**: `slop_audit.mjs` AS-59 — for every `[class*="-actions"]` /
`.c-actions` group (sections AND the chrome bar), classify each visible
`.c-button` / `a[role="button"]` as filled / outlined / text by computed style;
≥2 filled actions with identical computed background in one group ⇒ FLAG. Unit:
`brand_pipeline/tests/test_fix1_hubspot_punchlist.py` asserts the classifier +
both scan passes exist and sit before the flag push.

---

## AS-60 — Scaffold-habit action-group layout over declared facts

**Rule**: a rendered multi-action group that stamps its measured layout
declaration (`data-ag-gap` / `data-ag-align`, from the brand's
`layoutGrammar.actionGroup` facts + per-pattern overrides — brand-schema §4.4f)
must actually COMPUTE that layout. A group whose computed inter-action gap
deviates >2px from its own stamped gap, or whose computed `justify-content`
resolves to a different alignment than its stamp outside any anchoring context
(`.cs-foot`, `[data-align="centered"]`, `.cs-hero-panel--center`), is running on
scaffold habit over brand facts ⇒ FLAG.

**Why it happens**: action rows are the scaffold's oldest habit — a uniform
`gap: 1em` / block-gap default and a context-inherited alignment predate the
fact family, and every composer emits the row markup independently. When a new
composer route (or a CSS refactor) forgets the action-group law, the page
silently falls back to the habit: buttons drift 40px apart on a brand whose
measured pair runs 16px, and nothing else fails — the buttons themselves are
perfectly on-register.

**Caught here**: the hubspot-v2 "Powered by AI" split rendered its CTA pair on
the modules-row block-gap default (40px) where the source's `.cl-cta-group`
measures 16px, and the closing band pair rendered 40px where the source's
elevated-CTA group measures 24px — both while every button was individually
on-register (AS-59 clean).

**Verify**: `slop_audit.mjs` AS-60 — for every `[data-ag-gap]`/`[data-ag-align]`
group with ≥2 visible children: computed `column-gap` within ±2px of the stamped
px; computed `justify-content` (mapped to start/center/end) equals the stamped
alignment unless an anchoring context owns it. Declaration-driven: fact-less
brands stamp nothing and are never flagged. The spacing auditor measures the
same contract as relationships (`actions.item-gap` / `actions.alignment`).

**Painted-edge addendum (fix3)**: comparing computed `justify-content` to the
stamp is NOT sufficient — a group whose BOX re-implements containment privately
(`max-width` + `margin-inline: auto` inside an already-contained column) hugs
its content and floats centered while `justify-content` still computes the
stamped value, so the justify check reads clean on a visibly displaced row
(the hubspot-v2 side-rail CTA pair painted 21px off its column edge with a
conforming stamp). AS-60 therefore also measures the ITEMS' painted edges
against the content column a reader compares them to (widest in-flow sibling,
else the parent's content box) and flags >4px deviation from the stamped edge.
The structural fix is the containment law (one shared `width: 100%` +
`max-width` + `margin-inline: auto` rule; devices never re-declare the pair) —
see spacing-conformance §Container law.

---

## AS-61 — Text-link ink spanning the container (unhugged typographic actions)

**Rule**: a typographic action's box — and therefore its underline ink (border /
pseudo-element rules span the box) — must HUG its label + glyph run in every
placement. A text link whose box runs to its container's far edge paints an
underline that reads as a rule/divider, not a link affordance ⇒ FLAG.

**Why it happens**: the content-hugging-controls mechanic (this registry's
button/eyebrow prose, now explicit for text links): column flex stacks blockify
and STRETCH their children by default, so `display: inline-flex` +
`width: auto` is not enough — a card-footer "Learn more →" link inside a
`flex-direction: column` card body stretches to the card width, and its
underline (static or hover-drawn) paints to the card's right edge. Nothing else
fails: the label, glyph and hover nudge are all correct.

**Caught here**: the hubspot-v2 product-grid card links rendered 261px boxes
around a 110px "Learn more →" run (and the tab-card case-study links 406px
around 173px) — every hover underline drew to the card edge instead of hugging
the label. Fixed at the component: `.c-arrow-link { width: fit-content }`
(fit-content beats flex stretch, which only applies to auto widths; no-op in
rows and inline contexts) — the hug end of the containment-vs-measure-vs-hug
discipline: a typographic action owns no column, so its box never spans one.

**Verify**: `slop_audit.mjs` AS-61 — for every visible in-section
`.c-arrow-link` (nav links excluded: padded hit-target boxes are deliberate
chrome geometry): the box width must not exceed the content run
(`Range.getBoundingClientRect`) by more than 12px. Structural, not
declaration-driven — the hug contract is component law, not a brand fact.

---

## AS-62 — Plausible arithmetic that invents an off-ladder magnitude

**Rule**: a value computed FROM brand tokens is not automatically ON the brand's
ladder. Any derived size/gap in novel geometry (`calc(ratio × token)`, averaged
gaps, proportional step-downs) must land on a measured fact or a derived-scale
step (`style-scale.yaml`) — otherwise the arithmetic has invented a magnitude
the brand never ships, however principled the formula looks.

**Why it happens**: ratios feel safer than literals ("0.62 of the display size
respects the token!"), so generated CSS multiplies its way off the ladder. The
formula references brand values, which passes every provenance check — but the
RESULT is a foreign number, and foreign numbers are what make generated pages
feel almost-right-but-off next to the source.

**Caught here** (pass1 2026-07, at the `scale_adherence` gate's introduction):
the overlay panel's stepped-down display heading — `calc(0.62 *
var(--c-display-size))` = 49.6px on a brand whose ladder runs …44, 48, 52…
(measured h1 48, derived step 52). Re-registered to 0.6 so the stepped rank
lands on the brand's own h1 rung. Same pass: an 8px form label seam read
off-scale because the scale normalizer hadn't mined the brand's own authored
`--spacing-*` custom properties — the fix was completing the evidence harvest,
not snapping the render.

**Verify**: `spacing_audit.py` `scale_adherence` (generative lanes; spec
`spacing-conformance.md` §3b) — rendered section-content font sizes + unmapped
section space steps classify measured | on-scale | **off-scale** (hard fail);
chrome + replica lanes exempt by construction.

---

## AS-63 — Declared knob with no consumer (silent intent drop)

**Rule**: every `knobs` entry a composition section declares must have a
CONSUMER — a renderer/adapter device (the `composition_lint.KNOB_CONSUMERS`
registry) or the section's chosen archetype's own `variantKnobs` vocabulary —
and the USED VALUE must sit inside that consumer's declared vocabulary. A knob
nothing consumes, or a value no consumer can render, is a HARD composition lint
failure, never a silent no-op.

**Why it happens**: knobs read like configuration, so emitting one FEELS like
declaring behavior — but a renderer only honors the knobs it implements. The
model records a real plan ("supportKind: list"), nothing reads it, and the
declared anatomy quietly renders as something else. The page still passes every
paint/contrast gate because nothing is *wrong*, only *missing* — exactly the
silent-slot-drop class the stress-test pass closed for slots.

**Caught here** (fix7 2026-07, the proving case): the demo hero declared
`knobs.supportKind: "list"` on `hero-form-split`; a repo grep found ZERO
consumers, so its three parallel benefit items rendered as stacked look-alike
paragraphs and the review read the band as "no visual touches". Same sweep:
five gallery knob values sat outside their archetype enums (`panelSpan:
"half"` vs `[4, 5, 6]`, `metaPlacement: "above"` vs `above-heading`…) —
recorded plans that could never render.

**Verify**: `composition_lint.lint_knobs` — wired as a generation-loop
prefilter (hard, repairable) and as the `knob-consumption` composition
invariant in `onbrand_check --composition`. The registry is test-pinned to
real consuming code (a registry entry without a consumer is the lie the lint
exists to catch).

---

## AS-64 — Parallel benefit run rendered as look-alike paragraphs

**Rule**: three or more consecutive sibling short paragraphs of parallel
benefit phrasing inside a value-proof block SHOULD render as a marked list
(the brand's own marker glyph in the accent role, hanging indent, list rhythm)
— ADVISORY normally; a HARD failure when the composition itself declared list
intent (the renderer stamps `data-list-intent`) and the paragraphs still
rendered plain.

**Why it happens**: the adapter's safe degrade for unhandled copy shapes is
the paragraph — so a benefit run whose list declaration was dropped (AS-63)
melts into body copy. Each paragraph is individually fine; the ROW of them
reads as three identical subheadings with no scanning affordance, which is
exactly the "AI slop" texture human editors flag.

**Caught here** (fix7 2026-07): the demo hero's "What you'll see in 30
minutes" content-block — three parallel claims, declared `supportKind: "list"`
— rendered as three plain paragraphs whose stride matched the stat label gap,
collapsing the whole column's hierarchy. Fixed by the marked-list device
(`component_render.render_marked_list` + the brand's licensed checkmark glyph).

**Verify**: `slop_audit.mjs` AS-64 — hard arm: a `[data-list-intent]`
container rendering 3+ plain sibling paragraphs and no `.c-marked-list`; the
SHOULD arm prints as `ADVISORY` (surfaced for review, never an exit flag).

---

## AS-65 — Sibling-slot content redundancy (one payload, two registers)

**Rule**: no two sibling slots in one section may carry the same ENUMERABLE
content in different registers. A prose line (a form `note`, a caption) that
re-lists what an adjacent structured slot already binds is a composition
defect: keep the structured device, drop the prose line.

**Why it happens**: the model narrates its own structure — having authored a
quick-links slot, it "helpfully" summarizes the same links into the form's
note ("Popular: CRM API · UI extensions · OAuth · webhooks"). Each slot is
individually plausible; together they render a duplicated row plus a floating
meta line, and the reader sees the page repeat itself.

**Caught here** (fix7 2026-07): the developer hero's search `note` enumerated
the exact four destinations its `popular` link slot already rendered as the
arrow-link rail — a ragged two-line caption floating between the lede and the
control, duplicating the row below it.

**Verify**: `composition_lint.lint_redundancy` — separator-split (·/|/,)
normalized item sets per slot (nested `note`/`caption` strings included);
>= 2 shared items covering >= 50% of the smaller set flags. Wired beside
AS-63 (generation prefilter + `content-redundancy` gate row). The generation
prompt states the rule up front (COPY QUALITY block).

---

## AS-66 — Display register unfitted to its measure

**Rule**: a display-rung heading placed in a SUB-MEASURE column must fit its
register cap (hero display: 3 rendered lines; section headings ride
SR-HDR-01's tighter budget) — the renderer steps the SIZE down the brand's own
measured heading ladder (display → h1 → h2) until the projected line count
fits, and stamps the contract (`data-fit-cap` + `data-fit-rung`). A stamped
column whose heading still exceeds its cap is a HARD flag: the mechanic failed
or was bypassed.

**Why it happens**: the display size is measured on the FULL-measure hero
band; a form-split/half column keeps the 80px register on ~500px of measure —
~10 characters a line — so nearly ANY claim wraps past the budget. Copy
tightening (the stage-B remedy) carries one lane; the register is the class
fix, exactly like pass1's overlay-panel 0.6 re-registration.

**Caught here** (fix7 2026-07, the stage-B follow-up): the demo
hero-form-split display rendered 4–6 lines at 80px in the 500px column across
three copy revisions. The fit mechanic (`compose_section.heading_fit_level`,
greedy word-wrap projection at 0.6em mean glyph advance) steps it to the
brand's measured h1 rung (48px → 2 lines), keeping every magnitude on the
ladder (AS-62 safe by construction).

**Verify**: `slop_audit.mjs` AS-66 — for every `[data-fit-cap]` element, the
first `.c-heading`'s rendered line count (box height / line-height) must not
exceed the stamped cap. Declaration-driven: no stamp, no audit. SR-HERO-01
stays the copy-budget gate; this rule polices the fix mechanic itself.

---

## AS-67 — Third-party marks decorating invented content (mark legality)

**Rule**: an asset whose `usageRights` is `third-party-mark` (client/partner/press/
integration logos, review/award/compliance/app-store badges — media-assets.v1
taxonomy) may render ONLY in factual proof contexts: logo/proof/badge/integration
strips, partner rows, and testimonials that carry real attribution copy. Never
decorate an invented quote/testimonial with a client's mark; never fabricate a
badge — a badge-role slot binds a REGISTERED mark or declares its gap (a generated
placeholder recipe can never stand in for a badge) ⇒ FLAG.

**Why it happens**: marks read like free credibility, so a generator reaches for
them wherever a section feels thin — a customer logo "illustrating" a made-up
quote, an award shield invented to fill a proof row. Each binding is individually
plausible (the file is real, the render is clean); the LEGALITY is what breaks:
someone else's mark now endorses content the mark's owner never said, which is
both an anti-slop texture (fake-proof filler) and a genuine rights problem.

**Caught here** (media semantics 2026-07, registered with the machine arm at the
layer's introduction): the Remote source carries company marks atop its
testimonial cards ONLY as attribution of real, named quotes — the extraction
records those marks `usageRights: third-party-mark`, and the composed-lane check
exists precisely so a generated lane cannot re-deploy them beside brief-invented
quotes with no attribution (the shape the review flagged as the likeliest misuse
of the new `assetRef` channel).

**Verify**: `media_semantics.lint_media_bindings` rule `mark-legality` —
machine-checkable via the registry's `usageRights` flag × the slot's use-case/role
context (+ attribution-copy presence in testimonial sections). Wired as a
generation prefilter (repairable) and as the `mark-legality` gate row under
`onbrand_check --composition`. Fact-gated: brands without `media-assets.yaml`
are never flagged.

---

## AS-75 — Repeated components squeezed below content demand

**Rule**: repeated components negotiate visible copy, child roles, padding,
gutter, and available container allocation before choosing tracks. Use the
maximum feasible count; step down `3 → 2 → 1` when minimum item width, line
caps, or unbreakable-token fit fails. One component family uses one internal
anatomy; narrow icon/text items use icon-top rather than incoherent inline
baselines.

**Why it happens**: item count is mistaken for column count. Three records
become three tracks even when an adjacent intro rail leaves only half a
container, so prose wraps into tall letter-width columns and sibling icons
float against different text lines.

**Caught here**: the customer-story challenge band requested three columns
inside a counterweight allocation. The fit plan records each candidate width
and rejects the three-track squeeze before rendering.

**Verify**: `wireframe.v1 componentFit` records demand, candidate widths,
rejections, chosen columns/anatomy, and derived breakpoints.
`slop_audit.mjs` measures each stamped item against its declared minimum and
line caps, checks overflow, and rejects unlicensed sibling-anatomy divergence.

---

## AS-76 — Testimonial intent flattened into loose text

**Rule**: a testimonial/quote with attribution renders as one testimonial
component containing quote + author/role and compatible bound media when
available. If no compatible asset exists, emit an asset request and use an
intentional no-photo anatomy. Bare paragraph/caption pairs, silently dropped
media, and excessive unexplained section whitespace are hard failures.

**Why it happens**: a generic-flow safety adapter can preserve every string yet
erase the semantic component. The resulting quote paragraph and uppercase
caption technically satisfy content-presence gates while losing portrait,
surface, attribution grouping, quote measure, and intentional section balance.

**Caught here**: the customer-story testimonial carried Whitney Hallock's quote
and Angel City FC attribution, while the extracted media registry already held
the compatible Angel City client photo. The adapter flattened the contract into
paragraph + caption and never asked the testimonial renderer to bind the image.

**Verify**: wireframe testimonial completeness requires quote + attribution and
`assetStatus: bound|requested`; the renderer stamps
`data-component-contract="testimonial"`. `slop_audit.mjs` rejects missing
wrapper/content, a bound asset without an image, and an empty-space ratio over
the declared cap unless a monument archetype is licensed.

---

## AS-77 — Orphan final-row grid void

**Rule**: after feasible grid tracks are selected, repeated components must fill
their final row. Use an explicit `lead-span`, `tail-span`, or `single-column`
plan; use higher columns only when AS-75 passes. A partial row is allowed only
as licensed asymmetry with a real painted balancing counterweight.

**Why it happens**: stepping down from squeezed tracks fixes item readability
but can create a new composition defect. Three equal cards in two columns leave
an unexplained fourth-cell void when normal wrapping is mistaken for a balanced
layout.

**Caught here**: the HubSpot customer-story challenge correctly rejected three
184px tracks and selected two 292px tracks, but its third peer item previously
occupied only the first track of row two. The peer collection now uses an
explicit tail span with a constrained internal reading measure.

**Verify**: `wireframe.v1` records fill candidates, rejection reasons, the
chosen strategy, and each item span. `slop_audit.mjs` groups rendered cards by
row and fails when the final row's painted width leaves unused tracks, when a
declared span does not render full-row, or when asymmetry has no counterweight.

---

## AS-78 — Circle integrity

**Rule**: a component declared round/circular is icon-, image-, or avatar-only and
computes approximately square. Text-bearing controls use a pill/capsule family;
`border-radius: 50%` on a non-square text host is a hard failure. Hover, pressed,
focus rings, and pseudo layers preserve the host aspect and radius without
changing layout geometry.

**Why it happens**: a renderer reuses the normal CTA label inside a circular
carousel family. The text expands the host horizontally while the percentage
radius follows the new rectangle, creating a giant ellipse; an outline then
makes the malformed shape more visible.

**Caught here**: a measured icon-only round control was previewed with the
generic “Get started free” specimen label. Its 50% radius wrapped the text-sized
rectangle and the focus state became an oversized oval.

**Verify**: `slop_audit.mjs` inspects semantic round hosts and computed geometry
at runtime: aspect deviation must stay within 6%/3px, visible text is forbidden
unless the host is explicitly a pill, and computed 50% elliptical hosts fail.
Focus outline/pseudo geometry must remain shape-compatible and layout-neutral.

---

## AS-79 — Control-family coherence

**Rule**: toggle, switch, input, and button controls inherit the active brand's
control grammar: radius family, stroke, surface/contrast roles, focus treatment,
disabled opacity, motion timing/easing, and target sizing. An unobserved toggle
is explicitly designed from those facts. Its track is a capsule, its knob is
circular and square with a coherent inset, and every state remains branded.
Raw browser/default or neutral catalog controls are hard failures.

**Why it happens**: catalog completeness supplies a generic square switch after
the measured control family has already established rounded corners, branded
surfaces, and motion. Metadata says “designed,” but the specimen never consumes
the licensed signals.

**Caught here**: the synthesized toggle used square track and knob geometry,
generic light/dark paint, and catalog-local transitions despite a measured
rounded HubSpot control family.

**Verify**: `slop_audit.mjs` checks computed track/knob aspect, capsule/circle
radii, inset, focus ring, target size, and non-default state paint/motion.
Harness G3 additionally verifies designed-control provenance and brand-radius
consumption against `brand.yaml`.

---

## AS-80 — Icon-family asset blown up as a card's hero/lead media

**Rule**: asset-kind and slot-role are an eligibility pair. IMAGE/media-well roles
(hero-media, card-lead-media, full-bleed background, feature-image, product-shot,
portrait/illustration/split media) accept ONLY image-family kinds
(photograph/portrait/illustration/product-ui-screenshot/product-packshot/3d-render/
diagram/background-art). ICON/MARK-family kinds (spot-icon/ui-glyph/social-icon/logo
marks) are content-scale glyphs: they render at MARK height (above a heading, inline
in a headline, in a nav/social/proof row) and are NEVER stretched to fill a lead/hero
image slot. An icon may sit INSIDE a card; it must never BE the card's lead visual.
If an image role has no compatible image-family asset, declare the gap
(`noCompatibleAsset {requiredKind}` → asset-request manifest) — never substitute or
blow up an icon.

**Why it happens**: the card/media renderer keys its fit off the asset's captured
kind — a photograph/screenshot covers the well, a mark sits at mark height. When an
asset that is REALLY an icon is mis-tagged as `photograph` (or any image kind), it
inherits the `cover` default and is stretched to the full media-well dimensions.
Nothing in a CSS-property diff catches it: the markup is valid, the fit is a legal
value, only the KIND↔ROLE pairing is wrong. Two cards in the SAME grid can then read
completely differently — small spot icons above the heading on the correctly-tagged
cards, a giant blown-up glyph as the lead visual on the mis-tagged ones.

**Caught here**: the HubSpot v3 product-platform card grid. `009-small-business.svg`
(a 22×26 orange sprocket) and `027-ai-20sparkle.svg` (a 16×17 gradient sparkle) were
tagged `assetKind: photograph`, so they fell to the `cover` default and rendered in a
`16 / 10` media well — huge lead glyphs — while the eight product-hub `spot-icon`
cards beside them (`fit: mark`) rendered as small icons above the heading. The source
DOM shows ALL these product cards using the same small `global-nav-card-icon` glyph
(`width="22" height="26"`), never a photograph. Fix: reclassify the two glyphs to
their true `spot-icon` kind (`fit: mark`) so they render as marks like their siblings.

**Verify**: `media_semantics.lint_media_bindings` emits a `slot-role-eligibility`
row (surfaced by `onbrand_check.check_media_bindings`): an icon-family asset bound
into an image/hero-lead/full-bleed role FAILS, and an icon-family asset carrying an
explicit media-well fit (`cover`/`contain`) FAILS (a mis-scaled icon). The render arm
`component_render.asset_render_mode` coerces an EXPLICIT media-well fit authored on an
icon/mark asset to `mark` (`media_semantics.eligible_render_mode`); the unset default
stays `cover` so held baselines whose icon/mark assets legitimately fall to that
default remain byte-identical. Tests:
`brand_pipeline/tests/test_asset_kind_role_eligibility.py`.

---

## AS-81 — Declared multi-panel / stat device flattened to a plain block

**Rule**: a section whose DECLARATION names a tabbed / multi-panel switcher or a stat
device MUST render that anatomy — a tab rail of controls (`role="tab"`) for a tabbed
section, and stat items for a stat section. A declared tabbed-testimonial that renders as
a single plain quote (no tab rail, no stats) FAILS. This is the structural companion to
AS-80: AS-80 guards asset-kind↔slot-role; AS-81 guards declared-device↔rendered-device.

**Why it happens**: the composer routes a section to a generic archetype fallback (e.g. a
plain info-band / quote split) when the interaction DEVICE that should fire was never
armed — the pattern's tab treatment wasn't `sanctioned`, or the section copy never carried
the switcher's `panels`/`tabs`, so the tab composer's guard is false and the section
silently degrades to heading + body + one image. The markup is valid and the CSS is legal,
so a CSS-property diff sees nothing wrong; only comparing the DECLARED device against the
RENDERED controls surfaces the missing rail and the dropped stat footer.

**Caught here**: HubSpot v3 `tabbed-testimonial-with-stats` (source: HubSpot "Breeze Agents
tabbed testimonials", `section-07`). The measured anatomy is a 3-tab rail
(Enterprise/Mid-Sized Business/Small Business, first active, 4px `#ff4800` underline), a
photo-left / quote+author-right card, and a stat footer (2 stats on the active panel, 3 on
the others). It rendered as a plain single quote — no tab rail, no stats — because the
layout-library treatment was `tabbed-content-swap` (not the sanctioned `tabs` the renderer
stamps) and section-copy carried no `panels`. Fix: author the three panels + tab labels in
section-copy, promote the treatment to a sanctioned `tabs` (+ `stat-rule`) so the existing
WAI-ARIA APG tab device composes the full anatomy; nothing invented (all three panels are
DOM-verbatim).

**Verify**: `onbrand_check.anatomy_presence_hits(comp, html)` (surfaced by
`check_anatomy_presence`, wired into the composition-invariant rows). It reads the generated
`composition.json`, flags every section whose slots/treatments/useCase declare a tab or
stat device (word-anchored so "sans stat heading" and "deep-accent active state" never
misfire), order-aligns declared sections to rendered non-chrome `<section>`s, and FAILS a
declared tab section with <2 `role="tab"` controls or a declared stat section with no
`c-stat-value`/`cs-tabcard-stat` items. Fails OPEN on count mismatch (no false positives)
and is [] for composition-less lanes. Tests:
`brand_pipeline/tests/test_anatomy_presence.py`.

---

## Adding a new entry

Copy this shape: **Rule** (the imperative, one or two sentences) / **Why it happens** (the
plausible-but-wrong reasoning that produces it) / **Caught here** (the concrete instance —
name the file, the values, the visible symptom) / **Verify** (a repeatable check, ideally
scriptable). Keep entries brand-agnostic — this file lives in `brand_pipeline/spec/`
alongside `brand-schema.md`/`layout-analyst-skill.md` because these failure shapes recur
across ANY project this pipeline generates, not just WoodWave.
