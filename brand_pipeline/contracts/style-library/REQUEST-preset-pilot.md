# Request — style preset pilot (paste into Claude Design chat)

> Status: **ANSWERED 2026-07-15** ("spec 3" export) → imported as
> `styles/pilot-presets.yaml` + `extraction-map.yaml` (audit + one transparent
> color fix in `changes.md`; format lock `tests/test_style_presets_pilot.py`;
> calibration kit `runs/style-calibration/v001/`). Kept for provenance and as the
> commissioning template for the remaining 46 styles.
>
> Original status: OUTBOUND REQUEST, authored 2026-07-14. Paste the section below the rule
> into the Claude Design chat that produced the 15-file style package. The reply,
> if it honors the format, merges directly into `styles/directives.yaml` (new
> `preset:` / `exemplars:` / `neighbors:` blocks per style) and `token-schema.yaml`
> (extraction map). Import provenance stays `authored-prior` — NOT evidence.

---

You built the 51-style directive catalog (`styles/directives.yaml`). We agreed the
17-key directives are guardrails, not generators — too abstract to make a style
*recognizable* (Scandinavian, Japandi, and Minimalist currently read nearly
identically). You offered concrete token presets, sharper signatures, exemplars,
and an extraction map. We want them — as a **pilot of 5 styles first**, so we can
validate the format end-to-end in a bakeoff before commissioning the remaining 46.

## Pilot scope

Exactly these 5 style ids (as they appear in `directives.yaml`):

1. `swiss`
2. `editorial-magazine`
3. `neumorphism`
4. `scandinavian`
5. `japandi`

Scandinavian + Japandi are both in on purpose: they are nearest neighbors. If your
presets and signatures don't cleanly separate those two, the format has failed the
pilot. Before emitting, self-check: **no two pilot styles may share identical
values on more than 4 preset axes**, and every shared value must be a true
convergence you can defend, not a default you copied across.

## What to return — one fenced YAML block, merge-ready

Do **not** re-emit or alter the existing 17 directive keys. Return only NEW blocks
per style, keyed by the same ids, in this exact shape:

```yaml
styles:
  scandinavian:                    # ← format illustration ONLY; supply your own values
    preset:
      font:
        display: { family: "<real typeface>", stack: "<family>, <fallbacks>", weights: [400, 500], googleFont: "<name or null>" }
        body:    { family: "<real typeface>", stack: "<family>, <fallbacks>", weights: [400, 500], googleFont: "<name or null>" }
      type:
        baseSizePx: 16
        scaleRatio: 1.25           # the TRUE ratio for this style — see "no filler" rule
        lineHeight: { display: 1.1, body: 1.6 }
        measureCh: { body: 62, lead: 48 }
      color:                        # oklch canonical + hex mirror, all 6 roles
        bg:      { oklch: "oklch(0.98 0.005 90)", hex: "#f9f8f6" }
        surface: { oklch: "…", hex: "…" }
        text:    { oklch: "…", hex: "…" }
        muted:   { oklch: "…", hex: "…" }
        border:  { oklch: "…", hex: "…" }
        accent:  { oklch: "…", hex: "…" }
      space:
        basePx: 8
        stepsPx: [4, 8, 16, 24, 40, 64]
        sectionRhythmPx: 112
      shape:
        radiusPx: { button: 6, card: 8, input: 6 }
        borderWidthPx: 1
        shadow: "none"             # or the real box-shadow recipe if the style has one
      layout:
        maxWidthPx: 1200
        gutterPx: 24
      motion:                       # ONLY if motion is a real signature of this style; else omit
        easing: "cubic-bezier(…)"
        durationsMs: [120, 240]
      imagery:                      # concrete art direction, not a category word
        subjects: "<what is photographed/drawn>"
        lighting: "<e.g. soft natural daylight, no hard flash>"
        backdrop: "<e.g. seamless light neutral, lived-in interiors>"
        treatment: "<e.g. matte, low saturation, no duotone>"
        aspectHabits: ["4:3", "1:1"]
    signatures:                     # exactly 5, MACHINE-CHECKABLE, in our gate schema
      - id: <slug>
        kind: accent-scope | shape-motif | type-treatment | surface-habit | spacing-habit
        mode: always | never
        claim: "<one sentence>"
        check: { }                  # kind-specific params — see check vocabulary below
    neighbors: [japandi, minimalist]
    distinguishers:                 # what separates this style from EACH named neighbor
      japandi: "<one concrete, checkable difference>"
      minimalist: "<one concrete, checkable difference>"
    exemplars:                      # 2-3 real references
      - { name: "<site/product>", url: "<url>", lookAt: "<one line: what to study>" }
```

### Signature `check:` vocabulary (our validator consumes these)

- `accent-scope`: `{ maxPaintSharePct: <n>, allowedRoles: […], forbiddenRoles: […] }`
- `shape-motif`: `{ buttons: {radiusPx: <n>} | {pill: true} | {neverPill: true}, cards: {…} }`
- `type-treatment`: `{ probes: [{on: display|body, familyIncludesAny: […], weightMax: <n>, caseIs: upper|mixed}] }`
- `surface-habit`: `{ sectionMinLuminance: <0-1> | darkMaxLuminance: <0-1>, shadow: none|allowed }`
- `spacing-habit`: `{ minSectionPaddingPx: <n>, whitespaceRatioMin: <0-1> }`

Roles vocabulary for accent scoping: `action-primary`, `arrow-link`, `logo-mark`,
`body-text`, `heading`, `divider`, `icon`, `badge`.

## Rules (non-negotiable)

1. **No filler values.** Every number must be defensible for THIS style
   specifically. Our resolver already discards axes where 49+/51 styles carried the
   same value (`scaleRatio: 1.25`, `motion: subtle`) as zero-signal. If the true
   value genuinely equals a common default, keep it — but expect the
   self-check above to catch lazy repetition across the pilot set.
2. **Presets are level-2 DEFAULTS.** Every value you emit will be beaten by any
   measured brand fact in our cascade. Do not write rules that assume they win.
3. **Generic names only** in ids and roles — structure and role words, never a
   company, campaign, or section name.
4. **Self-consistent color.** `text` on `bg` and `text` on `surface` must clear
   WCAG AA (4.5:1). `muted` on `bg` must clear 3:1.
5. **Signatures must separate neighbors.** At least 2 of the 5 signatures per style
   must be checks that would FAIL if run against the named neighbors' presets.
6. **Exemplars are ground truth, not decoration.** Pick references you'd defend as
   canonical for the style; we will screenshot them and use them in a taste gate.

## Second deliverable — the extraction map

One more fenced YAML block: for every key in `token-schema.yaml` (style + brand
trees), mark where a measured value lands and how:

```yaml
extractionMap:
  type.scaleRatio:   { binding: snap,    snapRule: "nearest of [1.2, 1.25, 1.333, 1.414, 1.5]" }
  color.accent:      { binding: literal, note: "brand identity — never snapped" }
  space.stepsPx:     { binding: snap,    snapRule: "cluster to nearest preset step, tolerance ±2px" }
  font.display:      { binding: literal }
  shape.radiusPx:    { binding: snap,    snapRule: "…" }
  # … every remaining key, no omissions
```

`snap` = style-bound (measured value snaps to the style's preset rung);
`literal` = brand-bound (exact measured value is the brand, kept verbatim).
Add a `confidence` note where extraction is typically noisy.

## What happens next (so you can calibrate)

We import the pilot behind our provenance discipline (`authored-prior`), wire
`preset:` as cascade level-2 defaults, then re-run our 3-style bakeoff on a real
extracted brand plus one style-first generation with NO brand. Pass bar: the five
styles must be tellable-apart at a glance in a contact sheet, and
Scandinavian-vs-Japandi must be distinguishable by their signature checks alone.
If the format survives that, we commission the remaining 46 styles in the same shape.
