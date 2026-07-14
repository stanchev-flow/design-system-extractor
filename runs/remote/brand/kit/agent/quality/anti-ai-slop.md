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

> **Kit copy — distilled at export.** Each entry below is the rule statement only; the home repo's registry additionally carries the concrete caught-instance history behind every rule.

## AS-01 — Context-blind color tokens (dark-on-dark / light-on-light)

**Rule**: never resolve a color for an element without knowing which SURFACE it renders
on. A token name like `border/hairline-on-primary` is not automatically safe just because
it resolves to a valid hex — it may have been extracted for ONE surface tier and reused
unconditionally on every other tier.

---

## AS-02 — Fallback chains that never fire (truthy-string traps)

**Rule**: a `value_a or fallback` pattern only works if `value_a` is genuinely falsy
(`None`, `""`, `0`) when it should fall through. Never assume a helper function returns
`None` on failure without checking — some return the INPUT unchanged as a pass-through for
a different valid use case, which is truthy and silently defeats the `or`.

---

## AS-03 — Arbitrary spacing literals disconnected from actual geometry

**Rule**: a spacing value (padding, margin, a spacer element's height) that exists to clear
another element's overlap/bleed must be DERIVED from that element's actual offset — not a
round number picked because it "looked about right" at one test viewport.

---

## AS-04 — Container-relative units measured against the wrong container

**Rule**: a `cq*`/`%` unit resolves against its NEAREST ancestor with the matching
container context — verify that ancestor is actually the box you intend, especially when
the intended reference box (e.g. a width-capped collage) is a SIBLING, not an ancestor, of
the element using the unit.

---

## AS-05 — Absolute positioning against the wrong ancestor (content drift)

**Rule**: an absolutely-positioned decorative element (a ghost watermark, a floating badge)
must be positioned relative to the SAME box as the content it's meant to overlap — not a
wider ancestor that happens to look aligned at one viewport width.

---

## AS-06 — Hand-duplicated logic across two code paths

**Rule**: when the same concept (a CSS rule set, a style override, a registry of
special-case scaffolds) is needed by two different assembly paths (a single-item preview
and a full-page/batch assembly), it must be read from ONE shared source — never
re-declared as a second, hand-maintained copy "for now."

---

## AS-07 — Dispatch keyed to a literal id instead of the reusable identity

**Rule**: when routing to a composer/handler based on "which section is this," dispatch on
the REUSABLE identity (a `patternRef.id`) first, falling back to the literal instance id
only when no reusable identity exists — never dispatch on the literal id alone.

---

## AS-08 — `max-width`-capped containers with no centering, defaulting to flush-left

**Rule**: any element with `max-width` set (to cap line length or content width on wide
viewports) needs an explicit centering mechanism (`margin: 0 auto`, or a flex parent with
`justify-content: center`) — a `max-width` alone does nothing to the element's own
position; it defaults to flush against its containing block's start edge.

---

## AS-09 — A shared mask/transform wrapper that also contains unrelated sibling content

**Rule**: when applying `overflow: hidden` + a `transform`/`scale`/animation to "mask" one
element (e.g. a parallax-panning image), the mask wrapper must contain ONLY that element —
never a sibling that shouldn't be clipped or visually bled into (a caption, a label).

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

---

## AS-11 — Under-filled sections (metadata-only, no primary content)

**Rule**: a section must carry PRIMARY content — a heading plus at least one substantive
element (body copy, media, ruled rows/list, or a purposeful form). A section composed only
of metadata-register elements (eyebrow, caption, counter, CTA link) is not a section, it's
an empty frame. Two sub-shapes, both defects:
- eyebrow + CTA with no heading and no text at all;
- eyebrow + heading alone — acceptable ONLY if the heading is long/display-scale enough to
  carry the section; otherwise it needs one more element (media, list, description).

---

## AS-12 — Empty column in a multi-column layout

**Rule**: every column of a grid/split layout must contain content. If one side has
nothing to say, either give it meaningful content (a description, a heading+description —
top-, center-, or bottom-anchored, all fine) or change the layout to single-column.
Whitespace is a tool; a structurally EMPTY column reads as broken, not as editorial
restraint.

---

## AS-13 — Information-bearing media without its data as text

**Rule**: media that ENCODES information (a map, a chart, a schedule graphic) is an
illustration of that information, not a replacement for it. A map section must also carry
the address (and ideally hours/directions) as text; a chart needs its key figures. The
reader must never have to decode an image to get data the section exists to provide.

---

## AS-14 — Purpose-blind conversion UI (an input with no stated reason)

**Rule**: every form/input must be preceded by copy that states the EXCHANGE — what the
person gets for what they give ("One letter a season — new works, new hours, nothing
else."). A bare input + submit, or an input whose only context is an eyebrow, converts
nobody and reads as machine-assembled. The placeholder is not the purpose.

---

## AS-15 — Ragged text wrapping (unbalanced last lines)

**Rule**: headings and short text blocks must not wrap into ragged, accidental shapes (a
single orphaned word on the last line of a three-line display heading). Use the CSS
text-wrapping primitives as a system-level default: `text-wrap: balance` for headings/
eyebrows/captions, and balanced/pretty wrapping for paragraphs.

---

## AS-16 — Text set flush against media (missing gutter)

**Rule**: body/heading text must never sit flush against an image edge — wrapped text
beside a floated/inset image needs a real inline gutter, and text below an image needs a
real block gap. Margin captions are exempt (they sit close by design); the hero's
sanctioned display-over-media overlap is exempt; everything else needs breathing room.

---

## AS-17 — Aspect-ratio monotony (the brand's ratio VARIETY not captured)

**Rule**: a brand's imagery system is a PALETTE of aspect ratios, not one number — a real
editorial site mixes wide bands, standard landscapes, near-squares, and portraits
deliberately. Extraction must capture that palette (`tokens.imagery.aspectPalette`, each
entry with value + role + provenance), and execution must deploy from it — a composed
page where every image renders at the same hardcoded ratio flattens a signature the
source actually had.

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

---

## AS-19 — Media placement blind to the resolved anchor (misregistration)

**Rule**: a slot's grid placement must DERIVE from the section's resolved anchor, never
from a hardcoded span that was authored for one anchor. A centered text block requires a
symmetric media span (e.g. `4 / -4`); the asymmetric editorial offset (`6 / -1`,
`8 / -1`) is legal only under a side (left/right) anchor or a registered counterweight.
Any override that collapses a grid's tracks must also re-place the children that carried
track-relative spans.

---

## AS-20 — Interaction tokens that don't re-scope per surface (hover leakage)

**Rule**: interaction tokens (`--c-link-hover`, accent link colors) re-scope PER SURFACE
MODE — including CARDS and PANELS, which must re-scope ink/accent/link-hover exactly like
sections re-scope surfaces. A measured accent hover extracted from a dark surface (gold
from a dark footer) is legal on dark/textAccent-bearing surfaces ONLY; on light surfaces
the hover resolves to that surface's own ink (ink-shift) or the underline-draw per
`motionSpec`. The `:hover` state is part of the surface contract, not a global constant.

---

## AS-21 — Single-viewport verification (certifying the one width you looked at)

**Rule**: every scripted geometry/overlap gate runs at MULTIPLE viewport widths — at
minimum the desktop reference width (1440) and one mid width inside the awkward band
(~1180, where poster-scale type meets narrowing grid tracks). A PASS at one width
certifies exactly that width and nothing else. Grid does not clip overflow: an oversized
display heading paints over the neighboring column silently, with no layout shift to
notice in the DOM.

---

## AS-22 — Grammar transplant blind to the target's surface contract

**Rule**: a use-case TRANSPLANT (rendering use-case X's content in use-case Y's layout
grammar) must adopt the TARGET use-case's `surfaceIntent` and captured non-negotiables
(hero-must-be-dark, footer-must-carry-utility, …), never the source grammar's surface.
The layout grammar travels; the surface contract does not.

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

---

## AS-24 — Brand DNA leak: raw visual values in shared renderers

**Rule**: a shared renderer/composer may never emit a literal visual value (hex/rgba,
px/rem magnitude, weight, case transform, radius, shadow, duration, easing, aspect) —
every visual value resolves through the generated token layer (the per-page
`<style id="tokens">` block generated by `tokens_css.py` from the ACTIVE brand's
brand.yaml), or carries an explicit `provenance: structural` comment. A
`var(--x, LITERAL)` fallback **is** a raw emission: the fallback is somebody's brand.

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

---

## AS-26 — Slot-faithless adapters: bound actions dropped, unbound forms invented

**Rule**: the composition adapter must be SLOT-FAITHFUL both ways. A slot the section
binds (a `contract: button` action, a testimonial, a logo wall, a link list) must reach
a renderer — never be silently dropped by a fixed-shape mapping. A device the section
does NOT bind (the signup form) must never be invented for it. Stack disambiguation
routes on EVIDENCE — a conversion useCase, a bound form/input slot, or bound button
actions select the conversion composer; any other non-hero stack renders its own slots
through the generic-flow composer.

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

---

## AS-29 — Brand-named literals in emitted content attributes

**Rule**: composer/renderer-authored CONTENT (alt text, aria-labels, titles, default
copy) must derive from the ACTIVE brand (asset metadata, `brand.name`, the module's own
caption) — never a brand-named string literal in shared code. A hardcoded
`alt="<BrandX> …"` is the content-attribute twin of a raw visual value (AS-24).

---

## AS-30 — Structured asset payloads unwrapped at the adapter boundary

**Rule**: the adapter layer owns the asset payload SHAPE. A sanitizer/normalizer that
wraps bare asset strings into `{src, alt}` dicts must be paired with unwrapping at
every consumer boundary — composers receive `src`/`alt` STRINGS and never
string-interpolate a structured payload into a path.

---

## AS-31 — Scale gates must resolve var() chains before judging

**Rule**: any gate check that compares an emitted CSS value against a brand scale must
first resolve the page's OWN `var(--name[, fallback])` chains (via the page's custom
property declarations). An alias chain that lands on an on-scale token is the token
architecture working; judging the unresolved reference text as an off-scale literal is
a false positive that punishes exactly the discipline AS-24 demands.

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

---

## AS-35 — Chrome surface roles hardcoded to one brand's grammar (footer inverse-strong)

**Rule**: a page-chrome surface (the closing footer, the nav bar) is a PER-BRAND
resolution, not a shared constant. Resolve it from the brand's MEASURED chrome capture
(its extracted footer/nav surface color) matched against the brand's own `surfaces`
roles; only when the brand is silent fall back to the structural default. Role naming
stays palette-agnostic (`surface/raised`, `surface/inverse-strong`) — the resolver
compares measured VALUES, never name-matches a foreign brand's role vocabulary.

---

## AS-36 — Composer copy contracts keyed to the dev brand (KeyError crashes + specimen leaks)

**Rule**: shared composers may not treat the development brand's copy keys as a schema:
every `copy["key"]` access must tolerate absence (empty-string semantics, section
omitted) because other brands' `brand.yaml` carries different section copy. And every
PREVIEW/specimen string (captions, headlines, placeholder labels) must derive from the
ACTIVE brand's own measured copy, voice, or law facts — a preview tier is a render of
THIS brand, not a gallery of the first brand's content.

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

---

## AS-40 — Multi-open disclosure systems (menus/accordions that stack open states)

**Rule**: A disclosure SYSTEM (accordion, nav mega-menu, dropdown family) opens ONE
member at a time unless the brand's evidence shows stacked open states. Prefer
platform-enforced exclusivity (`<details name="…">` shares one exclusivity group per
system; hover/focus-scoped panels that close when the pointer leaves) over JS
bookkeeping. The OPEN member is evidence-driven: compose the item the capture shows
expanded (its inversion/surface from the brand's own token roles); with no open-state
evidence, all-closed is the degrade — never "open them all so the content is visible".

---

## AS-41 — Scroll-reveal without a failsafe (IntersectionObserver strands content)

**Rule**: Any reveal choreography that HIDES content until an observer callback fires
must carry redundant failsafes: (a) the hidden initial state applies only under a
JS-added gate class (no JS ⇒ nothing is ever hidden), (b) reduced-motion and
missing-IntersectionObserver paths return early BEFORE the gate class is added, and
(c) a timed fallback force-reveals everything after a deadline (seconds, not
minutes) — a mis-rooted observer, iframe quirk, or never-firing callback must cost
motion polish, never content. The reveal is an enhancement, not a gate.

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

---

## AS-45 — Centered stacks collapsing to hug/prose width (measure belongs to paragraphs)

**Rule**: a section CONTAINER spans the shared content measure and centers itself
(`max-width: var(--content-measure…); margin-inline: auto`) — a bare `max-width` with
no centering margin is a left-packed band at any viewport wider than the measure. The
prose measure (`ch`-based clamps) applies to PARAGRAPH slots only: headings, eyebrows,
action rows, and media hug or span their own content INSIDE the full-measure container.
A centered stack must never inherit a narrow slot's width — "hug" is a slot behavior,
never a container behavior, and a container must never be sized by its narrowest child.

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

---

## AS-52 — Phantom media: default-art backfill in attributed/quote modules

**Rule**: default-art backfill (the brand-asset rotation that fills a card grid's
unbound media wells) must never inject media into a QUOTE/TESTIMONIAL module — a
module carrying person attribution (name / role / avatar fields). Those modules are
text-first: only an EXPLICITLY bound asset renders, and an asset-less quote card
composes with no media frame at all (no empty figure, no placeholder). A random
brand photo beside a person's words reads as a portrait of that person — invented
evidence about a real human, the worst kind of phantom content.

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

---

## AS-54 — Double-application of a spacing mechanic (gap + owl margin)

**Rule**: exactly ONE mechanic owns each seam. When a stack is converted to the
relational ladder (owl `margin-block-start` per pair), every flex/grid `gap`
covering the same seam must be zeroed in that scope — and no LATER, more-specific
rule may re-declare the gap "for safety". A seam owned twice measures the SUM:
the ladder's 12px eyebrow→heading plus a re-added 12px flex gap renders 24px and
no single rule looks wrong in isolation.

---

## AS-55 — Pinned-slot collision (margin-top:auto with no minimum seam)

**Rule**: a slot pinned to the end of an equalized box (`margin-top: auto` on a
card's action row, an attribution row, a footer link) must carry a MINIMUM seam
on the box-to-box side facing the content above it — the ladder rung for that
relationship, expressed as the *preceding sibling's* `margin-bottom` (a real
box-to-box distance `auto` cannot collapse). `auto` may only absorb slack BEYOND
the rung. Padding on the pinned slot itself is not a seam: it moves the glyph
but the measured box-to-box distance still reads 0.

---

## AS-56 — Scaffold families escaping the container law

**Rule**: every top-level scaffold wrapper that spans the page column MUST ride
the shared content-container rule (`max-width: var(--content-measure);
margin-inline: auto`) — by joining the one shared selector list, never by
declaring its own width. A scaffold that declares `max-width: 100%` (or nothing)
silently becomes a second, wider page column: sections stop sharing edges and
the page reads as two different sites stacked.

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

---

## AS-58 — Advanced mechanics without content-shape preconditions

**Rule**: the simplest layout mechanic that reproduces captured evidence wins.
Every advanced device (interlock, float-wrap, overlap, straddle) must declare
evidence and content-shape preconditions at its adapter/composer boundary, plus
a plain, semantically complete degradation path. If any precondition is absent,
render the ordinary grid/stack/split; do not preserve complexity for its own sake.

---

## AS-59 — Multi-action groups without register hierarchy

**Rule**: in any multi-action group (hero action pair, bar action group, card
action row), exactly one action takes the brand's filled PRIMARY register; every
sibling takes a different measured register — the brand's outlined secondary,
ghost, or text-link. Two actions sharing the same filled register in one group
is a flag. Palette-agnostic by construction: the check compares computed paint
shape (fill vs stroke vs bare text), never any brand's hex values.

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

---

## AS-61 — Text-link ink spanning the container (unhugged typographic actions)

**Rule**: a typographic action's box — and therefore its underline ink (border /
pseudo-element rules span the box) — must HUG its label + glyph run in every
placement. A text link whose box runs to its container's far edge paints an
underline that reads as a rule/divider, not a link affordance ⇒ FLAG.

---
