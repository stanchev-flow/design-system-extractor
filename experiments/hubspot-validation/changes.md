# HubSpot token-layer validation — running log (2026-07-03)

Worker: HubSpot validation (post-token-batch decisive E2E retest).
Fences: `runs/hubspot/**` and `experiments/hubspot-e2e/**` READ-ONLY except NEW dirs
under `runs/hubspot/brand/compose/`. No edits to `brand_pipeline/**` unless a token-
generator wiring bug is found (then full suite + regate required). No commits/pushes.

## Conflict-protocol snapshot (12:29–12:31 WEST)

Volatile-input hashes + mtimes recorded in `input-hashes.txt`:
- `runs/hubspot/brand/brand.yaml` sha256 96d08de4… mtime 1783031037 (Jul 2 23:23) — UNTOUCHED baseline
- `runs/hubspot/brand/REPORT.md` sha256 19c4578f… mtime 1783030080 (Jul 2 23:08)
- all `brand_pipeline/*.py` mtimes recorded (token batch's edits from ~03:00–05:20 Jul 3)

Re-check scheduled before finish; any change ⇒ STOP + report anomaly.

## Log

- 12:29 read HANDOFF-2026-07-02.md, token-layer-impl/REPORT.md, token-layer-design/
  SPEC.md + DECISIONS.md + hardcode-audit.md, runs/hubspot/brand/REPORT.md (B1–B12),
  prior harness run_page.py + gen*.log + results.json.
- 12:30 snapshot hashes/mtimes -> input-hashes.txt. Created experiments/hubspot-validation/.
- 12:31 dry-ran layer-1 token generation for HubSpot brand.yaml: OK, 213 tokens,
  disabledDevices = ghost-watermark, footer-display-links, aspect-palette (all
  legitimate per DECISIONS.md #5 / optional-token policy). NO hard-fail: required set
  complete. Sampled values all trace to brand.yaml (orange #ff4800, hover #c93700,
  motion 150/200/300ms ease-in-out, radius 0.5/1rem, case none, panel #f8f5ee).
  NOTE: --size-display-hero resolves to 4.5rem (display-02) not the measured 4.0625rem
  heroDisplay tier — the scale picker still prefers largest display-family entry over
  exact-role match (B11 partial; provenance-clean since 4.5rem IS HubSpot's display-02).
- 12:31 verified structural variants for HubSpot: cta_shape=filled, input_shape=boxed
  (button + boxed-field CSS emitted conditionally).
- 12:31 baseline unit suite: 108/108 OK (no code edited; pre-flight sanity).
- 12:32 wrote run_validation.py (live pipeline only; NEW out dir
  runs/hubspot/brand/compose/signup-launch-tokenized/ — additive fence respected;
  layout="footer" gate context, same as prior harness, B8 workaround).
- 12:41 live run finished: ok=false, 3 attempts (1+2 repairs), 334s. Page + reports +
  tokens.manifest.json landed in signup-launch-tokenized/ (manifest brand sha == snapshot).
- 12:44–12:55 gate forensics: 5 FAIL lines = never-typographic-primary (composers drop
  `button` contract slots — zero .c-button elements; tokenized .c-button CSS present
  unused), 2× asset checks (adapter _sanitize_assets dict-src malformation, pre-existing),
  radius-scale false positive (checker doesn't resolve var(--button-radius)),
  token-provenance 3 errors / 2 WoodWave callouts — ALL in dormant scaffold fallbacks
  (.c-foot-sitemap-link 3rem clamp endpoint; .cs-ov-* 5rem), no live rendered value
  foreign. Off-palette hex now PASS (was FAIL with #1f1a14/#f7efe6 on 07-02).
- 12:50 screenshots: first pass blank below fold (scroll-reveal IntersectionObserver);
  re-shot with reduced_motion=reduce (page honors prefers-reduced-motion) →
  shots/tokenized-{full,hero,cta,footer-end}.png + sec-0..6.png. computed-samples.json
  captured for the traceability table. PLAYWRIGHT_BROWSERS_PATH had to be forced to
  ~/Library/Caches/ms-playwright (sandbox default pointed at empty tmp).
- 12:58 Studio: relaunched ./start-studio.sh persistently (first nohup died with parent
  shell); :1500 → 200; /project/hubspot lists lane "v04 · 07-03 12:41 · Composed:
  signup-launch-tokenized" beside prior v03.
- 13:05 conflict-protocol re-check: brand.yaml sha 96d08de4… + REPORT.md sha 19c4578f… +
  all 11 tracked brand_pipeline mtimes UNCHANGED. No conflicts. No brand_pipeline edits
  made → no regate required (pre-flight suite baseline 108/108 stands).
- 13:06 wrote REPORT.md (verdict, gate scorecard + provenance detail, traceability table,
  B1–B12 + A1–A5 disposition, new findings N1–N9, Studio lane, fences).
