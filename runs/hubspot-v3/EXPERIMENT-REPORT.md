# HubSpot v3 staged-authoring experiment

## Outcome

**Authoring, C1-C28, and the harness pass, but G4 remains blocked after the
three permitted measured-replica repairs: 0.6897 → 0.7943 → 0.8701 → 0.8591,
below the required 0.90. Generation remains disallowed.** Fresh capture,
evidence, grounding, assets, and valid author stages were reused without
rerunning.

## Completed author stages

- `foundation`: 150,184 input bytes; 123.409s; `claude-opus-4-8`;
  68,130 input / 12,328 output tokens.
- `copy-chrome`: 120,360 input bytes; 95.501s; `claude-opus-4-8`;
  53,194 input / 9,831 output tokens.
- `patterns-recipes`: 109,202 input bytes; 90.328s; `claude-opus-4-8`;
  47,766 input / 8,336 output tokens.

All completed stages passed YAML/required-key validation before atomic install.
Each is independently checkpointed in `brand/author-stage-status.json`.

## Blocking stage

The recovery removed the full 66-record draft and manifest from the prompt. Its
input is a seven-tag census, twelve representatives, and photography grounding;
the measured draft remains on disk. The two bounded calls were:

- attempt 1: 14,776 bytes, 27.419s, 6,608 input / 2,039 output tokens;
- attempt 2: 14,945 bytes, 15.736s, 6,689 input / 1,208 output tokens.

Both used `claude-opus-4-8`, zero provider retries, a 180s hard child timeout, and
a dynamic 3,450 output-token request under a 4,000-token hard cap. Attempt 2
returned valid `media-guidance.v1`, an evidence-scoped photography fingerprint,
and exactly one rule for each of the seven observed tags.

The valid media result remains deterministically installed as a 35,633-byte
`media-assets.yaml` and 8,660-byte `assets-tagged.json`.

## Deterministic repair and bounded resume

The canonical schema requires `brand` to be an identity mapping. The staged-author
boundary now normalizes only the supported legacy non-empty scalar into
`{name: ...}`, preserves canonical mappings, rejects malformed types, requires
future foundation responses to emit that mapping, and makes C1 enforce it.
`render_brand_md` also reads the checkpoint's legacy list-shaped `blocks` for
projection only; the validator still reports that noncanonical structure.

All deterministic projections then completed. C1 passed. Because foundation was
invalid, one bounded `claude-opus-4-8` foundation re-author ran: 150,317 input
bytes, 122.010s, 68,178 input / 11,869 output tokens. Copy-chrome,
patterns-recipes, and media were checkpoint-skipped; no recapture or evidence
stage reran.

The repair path now groups exact validator rows by owner and schema path and sends
only failing fragments, exact spec sections, affected evidence, and immutable
dependency summaries. Live payloads were 17,704; 17,902; 21,414; 5,658; 7,256;
19,939; 22,147; and 22,116 bytes. Eight calls started; seven returned telemetry
totaling 50,179 input / 25,612 output tokens. The first response was truncated
before valid JSON and returned no persisted usage.

Successful bounded patches narrowed C2/C3 and fixed C4. Canonical mechanical
projections fixed the footer-social wrapper and projected existing authored
motion into `tokens.motion`. A malformed list-shaped layout patch was removed;
structural validation and rollback now prevent such installation. The final
button response was fenced JSON and was rolled back by the strict parser; fenced
JSON is now supported and tested, but no third live cycle was run.

## Downstream gates

- C1-C28: PASS, 0 errors and 26 advisory warnings after the measured correction.
- Harness/spec-book/catalog: PASS, 7/7 chapters; Studio HTTP 200; screenshot at
  `brand/harness/studio-spec-book.png`.
- Replica: G4 BLOCKED at 0.8591 after three repairs. Final pairs/contact strip:
  `brand/compose/replica/diff/`.
- Creative pages: prohibited and not generated.
- Visual review: final replica reviewed; dominant blockers are the 4,243px
  product-icon card band (source 1,600px), incomplete testimonial/stat anatomy,
  hero photo/scrim mismatch, and static edge-cut agent cards.

## Verification

- Focused author/flow tests: 40 passed.
- Full suite before browser installation: 1,614 passed with two Node Playwright
  runtime failures caused by a missing browser binary.
- Both Python and Node Playwright browser builds were installed; the affected
  focused gates then passed.
- Compact-repair focused suite: **28 passed** plus 4 subtests.
- Post-repair full suite: **1,641 passed** plus 4 subtests, 8 existing Pillow
  deprecation warnings, zero failures.

## 2026-07-20 harness forensic correction

The reported blank/square UI was a stale components-preview projection, not the
current measured replica. Full evidence and correction:
`brand/harness-regression-audit.md`.

- Corrupt author/harness outputs archived at
  `brand/_pre-repair-corrupt-author/`; evidence/assets retained.
- Current public identity/copy/pattern outputs re-authored and projected from
  fresh v3 evidence. C1-C28: 0 errors, 11 warnings.
- G3 is digest-current and quality-gated: 7/7 chapters, 36 primitives,
  32 blocks, 10/10 extracted layouts, AS-78/79 pass, Studio HTTP 200.
- Harness:
  `http://127.0.0.1:1500/runs/hubspot-v3/brand/components-preview/index.html`.
- The real preserved replica baseline was 0.8591. Three post-harness iterations
  scored 0.8542, 0.8542, and **0.8633**. G4 remains blocked below 0.90;
  no creative pages were generated.
- HubSpot v2 holds 0.957. Remote currently re-renders at 0.936 versus the
  requested 0.951 safety baseline, so the work is not declared fully complete.

## 2026-07-20 CTA label-channel correction

A further measured root cause was confirmed in `computed-styles.json`: action
evidence treated raw `textContent` as painted copy, conflating visually hidden
descriptive suffixes with the visible CTA label. The 113.375px and 141.781px nav
controls could not geometrically contain the recorded long strings.

The generic extractor now records painted `visibleLabel` independently from
`accessibleName`/`ariaLabel`/`labelledBy`, excludes hidden and clipped
descendants, and records text-fit facts. Projection and rendering preserve the
same separation. Existing v3 evidence was deterministically re-measured from its
saved HTML, and the harness/catalog were regenerated: visible controls now read
`Get a demo` and `Get started free`, while the full descriptions remain in
`aria-label`. C1-C28 remains at 0 errors / 11 warnings and harness quality passes.
The refreshed measured replica improved from **0.8633 to 0.8891** (nav 0.9382;
product grid 0.9161), but remains below the 0.90 gate, so G5 stays blocked.
Final full regression suite: **1,674 passed + 4 subtests**.

## 2026-07-20 final focused G4 pass

Weighted evidence ranked the agent carousel, hero, product grid, testimonial,
and platform carousel as the largest remaining contributors. The bounded repair
corrected section-04's factual routing from a plain contained primary-surface
grid to its measured generic soft-accent surface, split headrail, and edge-cut
card track. It also fixed generic full-CSS-stack matching for the four freshly
captured, locally hosted HubSpot Sans/Serif WOFF2 files.

The verification replica improved **0.8891 → 0.8955**, still **0.0045** below
G4. Section-04 improved **0.8208 → 0.8867**; its width fidelity rose
**0.7725 → 0.9551** and its 894px height is close to the 992px source.
Residuals are hero composite art (0.8097), testimonial tabs/stats anatomy
(0.8649), platform carousel height/width (0.8749), section-04 card-track
details (0.8867), and headrail projection (0.8999). Product-grid hosted-font
metrics increased its height and moved it **0.9176 → 0.9043**.

C1-C28 passes with 0 errors; G3 rebuilt digest-current and passed at Studio
HTTP 200. Remote held **0.9509**, HubSpot v2 held **0.9567**, and the full suite
passed **1,676 tests** with 8 existing warnings. G5 remained fail-closed, so no
requested pages or URLs were produced.

## Responsive-fidelity generalization + Phase 5 multi-viewport gate (2026-07-21)

The proven hero+footer responsive-fact mechanism was generalized to the remaining
computed-CSS divergences, driven by `compose/replica/css-diff.md`. New generic,
provenance-tagged fact blocks (`responsive-facts.yaml`) — nav mega-panel surface, hero
primary-button geometry, a brand-wide hover-transform purge, and heading line-heights — are
merged at load and consumed by fact-gated, scoped emitters (byte-stable without a block).

The computed-CSS diff dropped **22 → 13** divergences with the last **critical** cleared
(nav mega-panel now painted `#ffffff` from the resolved container var; the un-grounded
button `translateY(-1px)` hover lift purged; the hero CTA font-size/line-height/border and
h2 line-heights pinned to their measured values). The 13 residuals are honest capability
limits: an inline-flex-vs-block box-model equivalence on the CTA, an authored surface-token
drift on section-04, a footer probe/element mismatch, and a pre-existing font-family
stack-quoting artifact.

Phase 5 extends the replica gate to the viewport ladder: 1440 remains the source-fidelity
score (**0.9111**, ≥0.90), and 1920/960/375 record responsiveness-health (no source shot to
SSIM against, so it is not faked as fidelity). v3 is overflow-free at 1440/960/1920 and its
footer reflows 5→1 columns at 375; the 375 health of 0.500 is a pre-existing nav
mobile-collapse gap (`.cs-nav-util`) shared by every brand. v2 (**0.9556**) and remote
(**0.9509**) desktop scores held with composed HTML proven byte-identical, and their
non-reflowing footers at 375 are the intended byte-stable contrast. C1–C28 pass with 0
errors; the full suite added +16 tests with zero new failures.
