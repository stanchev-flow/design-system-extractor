# Token-layer design decisions — user calls (2026-07-03 00:35)

Answers to the six open questions in `SPEC.md` ("Open questions for the user", line ~420).
These are binding for the implementation batch.

1. **Alias-layer naming — keep `--c-*` as layer 2.** No `--ds-*` rename; zero churn in
   existing component CSS. Layer 1 (generated measured vars) feeds the existing `--c-*`
   contract; literal fallbacks inside `var()` are removed per spec.
2. **Missing-token behavior — hard-fail at generation time.** A compose run aborts with a
   named-token error when the active brand.yaml lacks a required measured token. No
   render-with-sentinel mode. E2E harnesses surface extraction gaps before model spend.
3. **Duration/easing severity — warning first.** Keep the spec's phased default
   (warnings now; flip to error in a later documented pass). Do not flip immediately.
4. **`render_section.py` — RETIRE, do not retrofit.** Single-section rendering migrates to
   the composer path. Implementation chunk previously scoped as "retrofit chunk 5" becomes
   a retirement/migration chunk: route callers to composer path, then remove or quarantine
   the legacy module. Its 232 raw-value hits fall out of provenance scope on retirement.
5. **HubSpot aspectPalette — intrinsic-only is intended.** No extraction change; absence of
   `tokens.imagery.aspectPalette` is legitimate for photography-led brands. Provenance/
   token generation must treat aspectPalette as optional; no hard-fail on its absence
   (consistent with decision 2 applying to *required* tokens only).
6. **Fluid clamps — accept calc-of-var in layers 2/3.** Layer 1 stays flat (Webflow-
   mappable endpoints); no precomputed per-brand static clamp strings.

Provenance: decisions collected interactively from the user in the coordinating session,
2026-07-03 ~00:35 WEST, after the read-only design worker delivered `SPEC.md`,
`hardcode-audit.md`, `changes.md`. Implementation remains queued behind the anti-slop
alignment batch close (serialized writers on composers/gate).
