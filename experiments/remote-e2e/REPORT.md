# Remote (remote.com) — third-brand end-to-end REPORT

Date: 2026-07-03 · Worker: Remote-brand e2e · Fence: `runs/remote/**` + `experiments/remote-e2e/**` only.
Result: **extraction complete → live generation PASS (1 fix round) → gate green with a clean
three-way foreign-brand check → Studio lane live.**

---

## 1. Extraction coverage vs the token schema (SPEC required keys)

Source of truth: 22 saved CSS files in the local capture (primary measurement source),
inline styles mined from the 2.1MB HTML, Playwright `getComputedStyle` harness
(`measure_chrome.py`, JS disabled, 1440×900 → `chrome-measured.json`), ground-truth webp
for composition/creative direction. `tokens_css.build_page_tokens` on the finished
`brand.yaml`: **BUILD OK, `missing == []`** (6,930 chars of CSS emitted).

| Schema area | Status | Evidence quality |
|---|---|---|
| colors (palette + roles) | 50 tokens | all `source: saved-css` / `inline-style` / `computed`; canonical aliases included |
| surfaces | 7 surfaces | incl. `surface/hero-noise` (bg = sampled art average `#dae2e8`, mirrored as the `surface/art-pastel` color token) |
| type roles + ladders | 9 roles, per-role **weights REQUIRED — filled** | Bossa w400 across display/h1–h4/eyebrow (measured), Inter w400/500 body/control; case + tracking per role (eyebrow: uppercase, 0.05em); responsive ladders from `@media` rules |
| font delivery | `renderProxy` per role | Bossa is not a Google face → proxied to **Lexend Deca**; Inter is loaded as itself. Self-hosting Bossa is impossible without a pipeline edit (see schema-gaps) |
| buttons (measured pairs + hover) | 4 families, full state matrices | **truly mined from CSS `:hover` rules, not guessed**: primary `#0564ff` → hover `#0047bc`; outline hover wash `#ebf2ff`; neutral pill hover `#595b5f`; link `#0564ff` → `#0047bc` + underline; on-dark link hover `#ccdfff`; disabled `#d2d3d5`; pill radius 2.5rem |
| radius tiers | 5 tiers | 0.1875 / 0.625 / 0.75 / 1 / 2.5 rem — all measured |
| shadow | hover-only elevation | cards elevate only on hover (measured) |
| spacing rhythm | 13 keys | incl. `container-max: 76rem` (84.45% @1440 ≈ 1216px measured) and `badge-tier: 6.25rem` (measured `.iconBox.badge{height:100px}`, `.remote-logo{max-width:100px}`) |
| motion spec | **measured, not guessed** | dominant `ease`; tempo 300ms (micro) / **500ms house tempo** (buttons, nav pills, card hover, accordion — `all .5s ease` ×17) / 1000ms (large reveals, one `cubic-bezier(.49,.78,.46,1.34)` on menu panels); links = color-shift + underline-on-hover; scroll reveal = fade (lozad); no `prefers-reduced-motion` declared by the site |
| chrome (nav + footer) | measured | nav blocks, pill CTA, menu-open bg `#f6f7f8`; footer = 6 real columns, light `#f6f7f8` bg, 14px gray links that darken + underline on hover |
| heroTreatment / surfaceGrammar | filled | inset noise-gradient pastel art panel; all-light section rhythm (navy `#00235c` appears only as media-panel backdrop, never a section band) |
| layouts | 12 in brand.yaml + 7 extracted patterns in `layout-library.yaml` | patterns carry contentShape alignment + counterweights |
| do / avoid / neverDo, voice | filled | `never-typographic-primary`, `never-zero-radius`, `never-allcaps-headings` |

Identity signals from the brief, verified against the capture: pill CTAs ✔ (2.5rem radius
family), pastel/noise surfaces ✔ (noise-gradient art panels on hero + closing CTA),
uppercase color-coded eyebrows ✔. **Correction to the brief's memory:** no irregular
blob photo masks and no serif — Remote's homepage is geometric-sans (Bossa) + Inter with
16px-rounded rectangular cards; the "distinctive pairing" is display-sans/text-sans, not
serif/sans. Encoded as measured, palette-agnostic roles only.

## 2. Assets tagged

44 curated assets in `runs/remote/brand/assets/` (names sanitized, SVG logos extracted
from inline HTML). For the logo-strip device: **12 `logo-wall-logo` SVGs** (Anthropic, Box,
BYD, Datadog, GitLab, Heineken, KFC, Lovable, Mercury, Miro, Mizuho, Vercel) + 1 wordmark +
4 integration logos. Badges: **6 award-badge + 3 rating-badge = 9**. Rest: 6 product
graphics, 6 feature icons, 4 avatars, 1 hero illustration, 1 background art.
Note: assets had to live FLAT in `assets/` — both `generate_composition`'s inventory and
`compose_section.copy_assets` ignore subdirectories (see BLOCKERS).

## 3. Generation outcome + gate verdict

Live pipeline only (`generate_composition` seeded path → composers → gate), style
`corporate-saas-clean`, output `runs/remote/brand/compose/signup-launch/`. No hand-authored
HTML/JSON, no post-processing. Runner: `run_page.py` (mirrors `experiments/hubspot-validation/`).

- **gen1: gate FAIL (7 findings)** — all diagnosed, all fixed inside my fence (brand.yaml
  tokens, layout-library counterweights, directive steering). Details in `changes.md`.
- **gen2: gate PASS, 1 attempt, 88.3s wall.** Scorecard (`onbrand-report.md`): neverDo 3/3,
  fidelity 3/3 (surface `#eff0f0`, Bossa display tier, 17 local assets), slop 7/7,
  composition invariants 14/14 HARD — including `text-contrast` (worst 4.91 ≥ 4.5),
  `interaction-contrast` (48 hover colors re-scoped, worst 11.16), `alignment-resolution`
  (7/7 source-stamped, counterweights present), `logo-wall-integrity` (12 disk-backed logos).

**Three-way foreign-brand check (first with 3 brands in the corpus):** the provenance
scanner loaded BOTH sibling indexes — HubSpot (213 tokens) and WoodWave Gallery (124
tokens) — and matched every emitted visual value against them. Result re-verified
standalone: **0 errors, 0 warnings, 0 foreign-brand callouts; 7 allowlisted structural
literals**. The check behaves correctly with N>2 brands: in gen1 it caught the scaffold's
`6.25rem` fallback as *both* a raw literal *and* a foreign-brand collision (HubSpot
`--chrome-nav-logo-w` / WoodWave `section-padding-dark`) — resolved not by allowlisting but
by measuring Remote's own legitimate 100px badge tier and tokenizing it (`spacing.badge-tier`).
The content-literal check (alt/aria/title) is also three-way clean.

Logo-strip device: landed mid-run (its REPORT.md gated phase 2) and works — the generated
logo wall is image-backed from my tagged SVGs.

## 4. Visual verdict vs the real screenshot

Shots: `shots/gen-full.png`, `gen-hero.png`, `gen-footer.png`, band slices, and
`side-by-side.png` / `side-by-side-top.png` vs the ground-truth webp.

Matches (strong): light `#eff0f0` canvas with ink text; geometric-sans display in sentence
case at the measured 2.875rem tier (Lexend Deca proxy reads convincingly close to Bossa);
uppercase letter-spaced eyebrows; the real hero globe illustration; navy `#00235c` used
exactly as the brand uses it — media-panel backdrop, never a section band — with the real
product graphics on it; the real 12-logo monochrome customer row; filled blue pill
"Start free" CTA (correct hue + pill radius); footer chrome carries the 6 real columns.

Strongest deltas (worst first):

1. **Hero composition**: real = split left-copy / right-illustration on an inset pastel
   noise panel with two pill CTAs; generated = centered stack hero whose display title
   collides with the media top edge ("in one place" overlaps the illustration) — the
   layered stack-hero is WoodWave DNA, off-Remote.
2. **Hero CTA is a typographic arrow link**, not a filled pill — `compose_stack_hero`
   renders the hero foot CTA as an arrow link by design; the page passes
   `never-typographic-primary` only because the CTA section carries a real `.c-button`.
3. **The noise-panel treatment didn't ship**: `heroTreatment` + `surface/hero-noise` are in
   brand.yaml, but no composer consumes an inset art-panel surface; hero sits on flat primary.
4. **Chrome footer is navy** (`FOOTER_SURFACE` hardcoded `inverse-strong`); the real Remote
   footer is light `#f6f7f8` with dark links. Model also composed a small arrow-link footer
   section above it (double footer).
5. CTA section copy tripled ("Ready to get everything in one place?" as eyebrow + heading +
   paragraph) — model copy quality, not pipeline.
6. Density: real homepage is ~13.5k px with many more sections; generated is a 7-section
   signup page per the brief — expected, not a defect.

Screenshot gotcha for future workers: full-page shots need `reduced_motion='reduce'` (or a
scroll pass) — the IntersectionObserver reveal keeps below-fold sections at opacity 0.

## 5. BLOCKERS (pipeline defects — NOT fixed by me, per fence) + schema-gaps

Blockers, with anchors:

- `brand_pipeline/compose_from_composition.py :: _logo_item_mapping` — silently DROPS
  logo-wall copy items that are bare strings; only `{alt, asset}` dicts survive. gen1
  produced an empty logo wall that then failed `logo-wall-integrity`. Should coerce strings
  (filename → alt from stem) instead of filtering.
- `brand_pipeline/compose_from_composition.py :: _hero_mapping` (non-layered stack-hero
  path) — injects WoodWave placeholder art (`overlap-vase.jpg`, `hero-staircase.jpg`) when
  the composition doesn't opt into layered media. Foreign-brand assets should never be
  default fills for another brand's render. Same class of fallback in the testimonial
  cards path.
- `brand_pipeline/compose_section.py :: compose_stack_hero` — hero foot CTA is ALWAYS a
  typographic arrow link; brands whose `neverDo` includes `never-typographic-primary`
  (Remote, HubSpot) need a slot-faithful filled-pill option (DECISIONS.md "slot-faithful
  CTAs" precedent).
- `brand_pipeline/compose_page.py` + `compose_section.py` scaffold CSS — literal
  `var(--c-section-pad, 6.25rem)` fallbacks. For any brand without a 6.25rem token the
  provenance gate flags a raw literal AND a cross-brand collision. Fallbacks should emit
  from the brand token index or carry the structural-allowlist comment.
- `brand_pipeline/compose_page.py :: FOOTER_SURFACE` — hardcoded `inverse-strong`; Remote's
  measured footer is light. Footer grammar is per-brand by decision (DECISIONS.md); the
  surface should come from `brand.yaml` chrome facts. (Logged in `signals.log` at
  extraction time.)
- `brand_pipeline/generate_composition.py` (asset inventory) + `compose_section.py ::
  copy_assets` — only glob the assets root; subdirectories (e.g. `assets/logos/`) are
  invisible. Forced me to flatten the curated tree.
- `brand_pipeline/render_components_preview.py` + `component_render.py` (preview tier only)
  — `KeyError: 'panelTitle'` when a brand's custom layout ids hit the split archetype's
  `SECTION_COPY` registry, and WoodWave-flavored captions/placeholder assets leak into
  other brands' previews. Cosmetic (live path unaffected) but misleading.

Schema-gaps (generic framing):

- **Self-hosted font registry is closed** — `compose_section.SELF_HOSTED_FONTS` is a
  hardcoded dict, so a brand whose display face isn't on Google Fonts (Bossa) can only ship
  via `renderProxy`. Schema should let brand.yaml register self-hosted faces + files.
- **Inset art-panel surface** — a surface whose background is a shipped art asset on an
  inset rounded panel (Remote's hero/closing noise panels) has no composable expression;
  I approximated with a sampled-average color token. A generic `surface w/ assetFill +
  inset panel` concept would express it for any brand.
- **Light chrome footer** — chrome surface intent is not brand-selectable (see
  FOOTER_SURFACE blocker; the schema side is that brand.yaml has nowhere to say "my footer
  is light" that the composer respects).

## 6. Studio lane

`studio_server.py` on **:1500 answers 200**. The Remote lane is visible in `/api/projects`
with title "Remote", url, thumbnail (ground-truth webp) — enabled by writing
`runs/remote/studio-project.json`, mirroring `runs/hubspot/studio-project.json`.
`pipeline_status: "building"` — the same status tier the HubSpot lane shows (only WoodWave
has a full generated-site lane). No Studio restart was needed.

## 7. Fence + safety gate

Writes were confined to `runs/remote/**` and `experiments/remote-e2e/**` — zero edits to
`brand_pipeline/**`, `styles/**`, `tools/**`, sibling runs, or `screenshots/remote/**`
(inputs hash-snapshotted in `input-hashes.txt`). No git operations. The phase-2
serialization gate DID delay work once: a pre-generation re-check at 17:37:50 found
`compose_from_composition.py` modified 4 minutes earlier; held ~18 minutes until 17:56:12,
when `experiments/logo-strip/REPORT.md` existed AND `brand_pipeline/` had been quiet >10
minutes (both conditions). The wait was spent on report drafting and asset polish.
