# Brief — WoodWave hero: ANCHORED VARIATION of the measured original

Purpose: produce ONE hero section that is a CONTROLLED VARIATION of the original WoodWave
hero — the measured opening bookend captured as the project pattern
`hero-display-over-staggered-media` (extracted from the real site's `opening-bookend`).
You are NOT inventing a new hero. You are re-emitting the original with EXACTLY ONE axis
varied (the VARIETY DIRECTIVE names the axis).

## The original (the anchor — reproduce it, then deviate on ONE axis only)
- Centered oversized didone display title (Melodrama, display tier, weight 500) layered
  over two hard-edged photographs; the smaller portrait photo is offset right and crosses
  the landscape photo's lower edge (media-over-media, sanctioned).
- Dark inverse surface; the gold accent lives ONLY on this hero's display title.
- Measured copy: eyebrow "Est. 2019 — Portland, Oregon" · headline "WOODWAVE GALLERY" ·
  support "An evolving exhibition of woodgrain, light, and the quiet geometry of the
  handmade." · CTA "Buy Tickets".

## HARD INVARIANTS (you may NOT change these — any change here is drift/slop)
- Palette roles: gold accent on the dark inverse hero only; everything else ink/paper.
- Type: Melodrama display tier for the headline (the brand's display-hero, weight 500).
- Spacing: the brand's named spacing steps only; the original's rhythm.
- Edge registration: media registers to the grid/heading edges exactly as the seeded
  pattern's treatments describe — nothing free-floats.
- `novelty` MUST be `"adapt"` (never `"novel"`), `seededFrom` MUST reference the seeded
  hero pattern `{"lib": "project", "id": "hero-display-over-staggered-media"}`.

## Placement vocabulary (composition.v1 §4.6.5 — the contract levers for the directed axis)
The renderer honors these OPTIONAL slot/section fields for real; omitted fields keep the
measured original geometry byte-identical:
- `colSpan`/`colStart` — whole-column widths/positions on the shared 12-col grid.
- `mediaAspect` — a REAL aspect-ratio: `pano` 3:1 · `wide` 21:9 · `portrait` 3:4 · `square` 1:1.
- `registration` `{toSlot, edge, depthCols|depthBaselines, z}` — how an overlapping media
  slot registers to its base image's edge (declare it on EVERY overlap; mirror = flip edge).
- `z: "back"` + `width: "full-bleed"` — a true background layer behind the section copy
  (sanctioned text-on-media; the renderer scrims it), `alignTo {corner}` — a small
  `z:"front"` image pinned to the section frame's corner.
- section `alignment {anchor: "centered"}` — the original's centered treatment (declare it;
  mid-page heroes are no longer centered by position).
Use EXACTLY the fields the variety directive names — placement is the varied axis.

## What to emit
1. Exactly ONE `useCase:"hero"` section that reuses the seeded pattern with the ONE
   directed axis varied. No other sections (no footer needed).
2. Bind the measured copy above into the slots (adapt wording ONLY if the directed axis
   is copy/density — otherwise keep it verbatim).
3. Real brand assets only (or `asset: null` for the renderer's measured defaults —
   preferred when the directed axis is not media).
