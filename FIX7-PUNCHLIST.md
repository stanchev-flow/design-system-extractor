# FIX7 — Accent application, list/stat devices, heading fit (gallery review round 3)

User review of the hero-archetype gallery (developer + demo heroes, 2026-07-14) surfaced
seven defects. All fixes are SYSTEM-LEVEL: shared mechanics stay palette-agnostic and
brand-agnostic; brand specifics live in brand data. Do not patch the two lanes cosmetically.

STATUS: QUEUED — must not start until BOTH running agents land (steals Stage B gate wiring;
pass 3 resolver/bakeoff). Their fences exclude renderers and the audit modules this pass
needs, and mid-flight renderer changes would corrupt their verification (replica re-scores,
gallery battery runs, bakeoff renders).

## Evidence (what the user saw, confirmed against data)

- Developer hero (`runs/hubspot-v2/brand/compose/hero-archetypes/developer/`):
  heading ends in an INK period although `brand.yaml` carries the signature
  "landmark serif headings may CLOSE with an orange period accent" — extracted, never applied.
  The form `note` ("Popular: …") renders as a free-floating ragged 2-line caption BETWEEN
  lede and search control, duplicating the quick-links row below the control. Reads as
  two subheadings + broken alignment. Zero accent devices anywhere → "no visual touches".
- Demo hero (`.../demo/`): composition declares `knobs.supportKind: "list"` but NO consumer
  exists in brand_pipeline (grep: zero hits) — the 3 parallel benefit items silently rendered
  as stacked plain paragraphs. Stat (`contract: stat`, value "299,000+" + label) renders with
  no visual binding: label-gap ≈ list-gap, so hierarchy collapses. Display-rung heading in a
  6-col split column wraps to 6 lines — no fit-stepping.

## Items

1. ACCENT DEVICE APPLICATION (floor, not just ceiling)
   - brand-schema: explicit `accentDevices` licensing — device kind (punctuation-accent,
     marked-list-glyph, underline-accent, accent-word), licensed contexts (landmark bands,
     benefit lists, standing links), floor + ceiling per context. Palette-agnostic: any brand,
     any accent role, any glyph.
   - Renderer: generic "punctuation-accent" device — when licensed and the landmark heading's
     terminal punctuation matches the licensed mark, wrap it in the accent role span.
   - signature_audit: add FLOOR mode — landmark contexts must carry >= floor licensed devices
     (today the gate only caps overuse; accent-starved pages pass silently).
   - Generation prompt: licensed-device roster rides the pass-3 signature injection.
   - hubspot-v2 data: signature already present; author floors (landmark hero: exactly 1
     accent device). Replica CAUTION: source hero "go to grow." HAS the orange period —
     check whether replica currently paints it; device may IMPROVE replica score. Verify both
     replicas either way (0.956 / 0.950 must hold or improve).

2. KNOB CONSUMPTION LINT (fail loud, never silent-drop)
   - Registry of consumable knobs per archetype/renderer device. A composition knob with no
     consumer = HARD composition lint error (same class as the silent-slot-drop guards from
     the stress-test pass). `supportKind` is the proving case.

3. CHECKLIST DEVICE (marked list)
   - Renderer: content-block items render as a marked list when knob/contract says list:
     brand glyph marker in accent role (inline SVG channel), hanging indent, item gap from
     the relational ladder. Works for any brand's marker glyph (checkmark, arrow, dash).
   - hubspot-v2 data: harvest the checkmark glyph from evidence/sprites into assets +
     glyph inventory (follow the icon-next.svg pattern); checkmarks are named in the accent
     role provenance, so evidence exists.
   - AS rule (slop audit): >= 3 consecutive sibling short paragraphs of parallel benefit
     phrasing inside a value-proof block SHOULD be a marked list — advisory normally,
     hard failure when the composition itself declared list intent.

4. STAT PAIR BINDING (value+label proximity)
   - Generic relational rule: inside a stat device, value-to-label gap must be the tightest
     gap in the block (<= 0.5x sibling gap) AND the pair separates from the preceding block
     by >= 1.5x sibling gap. Renderer wraps the pair as a bound stack; `statPair` joins the
     relational spacing ladder; spacing_audit check added.

5. HEADING FIT-TO-MEASURE STEPPING
   - Display rung placed in a sub-measure column auto-steps DOWN the brand ladder until
     projected line count <= cap (hero display: 3 lines; section headings: 2 per
     section-rules). Deterministic renderer mechanic + AS rule. Coordinates with the new
     Stage-B heading gate: gate detects, this is the fix mechanic. Demo hero heading (6 lines)
     is the proving case.

6. META/NOTE LINE DISCIPLINE + REDUNDANCY
   - Form `note` renders ATTACHED to its control (caption register, below the control, capped
     to the control's width) — never a free-floating line between lede and control.
   - Redundancy lint: no two sibling slots may carry the same enumerable content in different
     registers (note enumerating the same links as an adjacent quick-links row = composition
     defect; keep the structured device, drop the prose line). Add to generation prompt rules.

7. STACK ANCHOR COHERENCE FOR META/CAPTION CHILDREN
   - Every direct child of an anchored stack honors the stack anchor, including caption-register
     lines; multi-word meta lines get balanced wrap (text-wrap: balance) + measure cap so no
     ragged 2-line floaters. Extend the existing painted-edge/anchor audit to caption children.

## After landing

- Re-render + re-shoot all 8 gallery lanes; re-run full battery (incl. new Stage-B gates).
- Re-render pass-3 style-bakeoff lanes (deterministic, no model calls) so they inherit devices.
- Regenerate gallery contact sheet for user review.
- Both replicas re-scored; suite green; changelog per lane + root changes.md updated.
