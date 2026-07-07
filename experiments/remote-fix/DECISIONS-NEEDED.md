# remote-fix — DECISIONS-NEEDED (taste-flavored calls left open)

1. **Bossa licensing / sourcing.** The `selfHostedFonts` registry is live for Remote, but
   the capture has no Bossa woff/woff2 (commercial face served from Remote's CDN). Until
   licensed files are dropped into `runs/remote/brand/assets/fonts/`, display type
   renders in the measured proxy (Lexend Deca). Decide: acquire/license Bossa, or accept
   the proxy permanently. (Zero pipeline work either way — files in, `@font-face` out.)

2. **Remote hero panel width.** The live render paints the inset panel edge-to-edge
   inside the content measure (`--content-measure` cap, like the source's 12px-radius
   module). Remote's real page also insets the panel from the viewport with visible
   canvas margin at some breakpoints. If the canvas-margin look is wanted at 1440px, that
   is a measured-geometry token question (panel inset value), not a mechanic — needs a
   taste call + measurement, not code.

3. **Marquee motion for the logo strip.** `logo-marquee-strip`'s sanctioned treatment
   allows continuous autoplay; the composed strip is the static reduced form. Animating
   it is a motion-taste decision (and an accessibility stance) beyond this batch's scope.

4. **Footer surface tie-breaking.** `footer_surface_role` prefers the historical
   `surface/inverse-strong` on exact RGB ties so aliased-palette brands keep their
   existing render. If a future brand measures a footer equidistant between two roles,
   the "closest by RGB" answer may not match editorial intent — revisit only if a real
   brand hits it.

5. **CSS-comment brand mentions.** Shared `COMPONENT_CSS` comments still name WoodWave in
   explanatory prose (e.g. "honors WoodWave no-boxed-inputs"). These are non-rendering
   comments, invisible to the gate's content checks, and shipping on all brands' pages
   today. Scrubbing them to generic wording is a hygiene pass someone should bless
   separately (touches many baseline-parity surfaces at once).

6. **Hero link-contract secondary actions (AS-26 family).** `_hero_mapping` maps only
   `button` contract slots into the hero actions row; the Remote live run declared its
   secondary CTA ("See how it works") as a `link` contract, so the panel hero renders
   one pill where the source pattern shows a filled + outlined pair. Mapping hero link
   slots (as arrow-links or outlined pills?) is both a slot-faithfulness fix and a taste
   call, and it touches every existing composition's hero mapping — needs its own
   parity-cycled batch.
