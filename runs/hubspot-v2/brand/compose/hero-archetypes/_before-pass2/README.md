# _before-pass2 — archived BEFORE state for the pass-2 A/B (2026-07-14)

Frozen copy of the 8 hero page dirs (index.html + composition.json + assets +
telemetry + onbrand reports) exactly as they stood before the pass-2
regeneration. This is the **A** side of the checkpoint-B eval.

## What this state already includes (honest framing)

These renders are **fix6 + pass 1's own real-lane fixes** — pass 1 did not leave
this lane untouched, so the A/B measures what FRESH GENERATION adds on top of
already-banked pass-1 value:

1. **Shared renderer**: panel stepped-display factor 0.62 → **0.6**
   (`compose_section.py`, pass-1 finding #1) — the product hero's panel display
   re-registered from 49.6px (no ladder) to 48px (the brand's measured h1 rung).
   All 8 heroes were re-rendered with this in the pass-1 pass.
2. **blog composition copy**: hero body split into two brand-length sentences
   (was one 24-word em-dash run-on; corpus max 20w) — voice-gate finding.
3. **demo composition copy**: 33-word run-on tightened to 17w + 8w — voice-gate
   finding.
4. Everything from fix6: copy-first event hero, surface diversity re-selection
   (product `primary`, demo `accent-wash`), slot-faithful anatomy devices.

Gate state at archive time (measured post-pass-1, recorded in the lane
changes.md pass1 section): onbrand PASS ×8 · slop PASS @1440+@1180 ×8 ·
interaction strict 0 required fails ×8 · spacing strict exit 0 ×8 incl.
scale_adherence cells · signature strict PASS ×8 (accent share 0.30–1.08% vs 2%
budget) · voice PASS ×8.

## Shots

- `shots/` — **fresh** 1440×900 reduced-motion full-page shots of THIS archived
  HTML (+ contact-sheet.png), taken at archive time. Use these as the A side:
  they include the pass-1 touch-ups above.
- `shots-fix6/` — the lane's previous shot set (taken 14:27, BEFORE the pass-1
  re-render at 15:33–15:52), archived for provenance. Slightly stale vs the
  archived HTML: predates the 49.6→48px panel display and the blog/demo copy
  tightening.
- `fix6-contact-sheet.png` — the user-named visual before-artifact (same
  vintage as shots-fix6/).
