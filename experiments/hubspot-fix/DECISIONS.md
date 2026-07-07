# Fix-batch DECISIONS-NEEDED — user ratifications (2026-07-03 ~16:00)

Answers to the four items in `REPORT.md` § DECISIONS-NEEDED. Binding.

1. **Measured-pair contrast exemption — RATIFIED (keep).** Provenance-scoped exemption in
   `readability.py` stands: (fg,bg) pairs exactly matching measured `buttons.*` pairs in
   the active brand.yaml are exempt from the 4.5 text-contrast floor, visibly reported in
   the scorecard. All non-measured pairings still fail. No revert.
2. **WoodWave nav register materialization — RATIFIED (keep).** The token batch's
   `--c-nav-size` single-sourcing stays; no pin-back to control-text. The re-rendered nav
   register is the new WoodWave baseline (documented intended diff, `shots/nav-stack.png`).
3. **Logo walls — DIRECTIVE (new work item):** logo walls must render REAL logo images
   from the extracted brand assets when the extraction captured them; when no logo assets
   were extracted, fall back to the existing text-caption device. Never emit broken or
   invented image references. (User verbatim: "we need either logo from the extracted
   brand or if not extracted show at least text.")
4. **Conversion-stack CTA treatment — RATIFIED (slot-faithful).** Both declared button
   actions render filled; no house-rule downgrade of companion actions. Matches the real
   site's own double-filled usage.

Items 1/2/4 require no code changes (ratify as-implemented). Item 3 delegated to a
logo-strip device worker immediately after these ratifications.

5. **HubSpot navigation — RATIFIED as-is (2026-07-03 16:14).** User verdict: "right now
   the navigation of hubspot is perfect." The green runs carry footer navigation only
   (per-brand `columns` footer grammar: sitemap nav + social nav) and no top navbar,
   which is appropriate for a signup/conversion landing composition. The REPORT.md
   "remaining deltas" item (a) "no navbar" is hereby NOT a defect and needs no work.
   Do not add top-navbar generation for this page type without a new user request.
