# Replication probe — remote.com one-shot speed baseline

> **NOT A LANE — experiment baseline, not pipeline output.**
> This artifact is HAND-AUTHORED BY DESIGN as a deliberate speed experiment.
> It must never appear as a Studio lane, never under `runs/`, never be
> registered anywhere, and must not be run through the on-brand gate.
> It exists solely as the "fast baseline" to compare against the measured
> extraction pipeline processing the same brand.

## Protocol and phase timestamps (honest accounting)

| Phase | Start | End | Duration | Counted? |
|---|---|---|---|---|
| Setup (look at screenshot, find shot harness) | 17:24:13 | 17:28:01 | 3m 48s | no |
| **Replication (write tokens + replica, 1 sanity pass, 1 fix)** | **17:28:01** | **17:31:14** | **3m 13s** | **yes — under the 5-minute budget** |
| Judging (shots, CSS spot-checks, brand.yaml diff, report) | 17:31:14 | — | — | no |

All times 2026-07-03 WEST, logged via `date` before/after each phase.

Budget honesty: the 5-minute budget **was honored — 3m13s of replication work**.
Inside the window: one `Write` for `tokens.css`, one `Write` for `replica.html`,
one sanity screenshot (two failed attempts due to a sandbox `PLAYWRIGHT_BROWSERS_PATH`
env issue, then success at 17:30:36 — tooling friction, not design iteration), one
viewing of the sanity shot, and exactly one small fix (hero gradient stop nudged from
45% to 60%). No other polish. The artifact is whatever that produced.

## Artifact inventory

- `tokens.css` — one-look guessed token layer (colors, type, spacing, radii, shadow, motion)
- `replica.html` — single self-contained page, all values via `var(--token)`, images referenced
  read-only from the saved `_files/` capture (hero globe illustration + 3 workflow card images)
- `gt-full.png`, `gt-slice-{0,1,2}.png` — ground-truth conversions used for the one look
- `shots/sanity.png` — the mid-budget sanity shot
- `shots/replica-full.png`, `shots/replica-viewport.png` (+ `-small` variants) — final shots
- `shots/side-by-side.png` — ground truth (left) vs replica (right)

## What got replicated / skipped

Replicated (8 sections, top ~2/3 of the visible page):
banner strip, nav, hero split (real globe asset), customer-logo strip (text spans, not
vector logos), "How we do it" accordion with the deep-maroon active item, "Intelligent
infrastructure" split with chip-stack art, grey rounded CTA band, and the 3-card
"Your workflows" grid (real navy card images).

Skipped (bottom ~1/3): partner-logos band, testimonial slider, G2 badge strip, closing
noise-art CTA, footer directory, all dropdown/mega-menu chrome, the real logo SVGs, and
the Bossa webfont (system fallback rendered instead).

## Fidelity verdict

**Layout structure: good.** The side-by-side lines up section-for-section over the
replicated range — same banner/nav/hero-panel/logos/accordion/split/CTA/card-grid
skeleton, same left-content-right-media splits, same rounded inset hero panel idea.

**Palette: consistently near, never exact.** Every major hue landed in the right family
but a measurable distance off (see spot-checks). Systematic bias: my neutrals guessed
warm, Remote's are cool.

**Type character: the visible miss.** Remote's display face is **Bossa** (quirky geometric
grotesque, **weight 400 at every heading tier** — a signature). I guessed "Aeonik" w500,
so the replica renders Inter/Helvetica at the wrong weight. The body face was a lucky hit:
my fallback stack led with Inter, which is Remote's actual body/UI font.

**Spacing feel: close enough to pass a squint test**, but real hero h1 is 46px at my 1440
render width (56 only at 1920+), body is 18px not 16, and cards are flat-at-idle
(shadow is hover-only) where mine carry an idle shadow.

### Spot-checked values — guessed vs real saved CSS (checked AFTER the clock)

| Value | My guess | Real (saved CSS) | Call |
|---|---|---|---|
| Brand blue | `#2563f5` | `#0564ff` | near-miss (hue right, real is more vivid) |
| Heading ink | `#1b1b1b` | `#141415` | near-miss |
| Page canvas | `#f0efec` (warm) | `#eff0f0` (cool) | near-miss, wrong temperature |
| Deep navy | `#0e2a5c` | `#00235c` | near-miss (close) |
| Accordion maroon | `#5a1a30` | `#511621` | near-miss (close) |
| Crimson eyebrow | `#a32035` | `#a52d44` | near-miss (close) |
| Display font | "Aeonik" w500 | Bossa w400 | wrong (both name and weight) |
| Body font | Inter (fallback) | Inter | exact |
| Hero h1 size | 56px | 46px @1440 / 56px @1920 | near-miss (right tier, wrong breakpoint) |
| Button radius | 999px pill | 40px pill | exact (functionally identical) |

## Token-vs-measured diff (`runs/remote/brand/brand.yaml` — present, read-only)

The measured extraction finished in time, so the full diff was possible.
Sample of 21 comparable tokens:

| Class | Count | Examples |
|---|---|---|
| exact | 3 | card surface `#ffffff`; body font Inter; pill radius (999px ≡ 40px full-round) |
| near-miss | 12 | blue `#2563f5`→`#0564ff`; ink `#1b1b1b`→`#141415`; canvas `#f0efec`→`#eff0f0`; navy `#0e2a5c`→`#00235c`; maroon `#5a1a30`→`#511621`; crimson `#a32035`→`#a52d44`; body grey `#4b4b4b`→`#595b5f`; blue-hover `#1d4fd7`→`#0047bc`; blue tint `#dbe7fb`→`#ccdfff`; container 1200→1216; button pad 12/24→11/24; body 16→18px |
| wrong | 5 | display weight 500 vs 400 (single-weight system missed); hero panel radius 24px vs 12px; idle card shadow vs measured flat-idle/hover-only; motion 150/250ms vs measured 300/500/1000ms house tempo; eyebrow tracking 0.14em vs 0.05em |
| not-measured-by-me | large | entire state matrices (hover/active/focus/disabled fills), on-dark link family `#9bc1ff`/`#ccdfff`, warm hover wash `#fceef1`, focus ring, input borders, footer greys `#383a3d`/`#b3b5b7`, aspect palette, surface nesting rules, motion easing census, Bossa render-proxy strategy |

Rough score: ~14% exact, ~57% near-miss, ~24% wrong over what I attempted — and the
attempted set is maybe a third of what `brand.yaml` actually measured.

## What this buys / what it can't do

**Buys:** a structurally credible, palette-adjacent single-page facsimile in ~3 minutes of
authoring — useful as a visual strawman, a layout-skeleton reference, or a "does the brand
read?" smoke test. The token file even has sensible semantic names.

**Can't do:** every value is unverifiable eyeball guesswork with no provenance — near-misses
look plausible but would drift a real brand system (wrong blue on every CTA, wrong display
weight everywhere). It has no state matrices, no breakpoint ramps, no motion system, no
surface grammar, no asset pipeline, no reuse story — it is one page, not a system, and it
missed the two things a human brand reviewer would flag first (Bossa's character and the
single-weight heading rule). Speed is the only axis on which it wins.
