# HubSpot — design language (hubspot-v2 extraction)

Extracted 2026-07-10 from a fresh live capture of https://www.hubspot.com/ through
the canonical pipeline (mine → measure → slice → vision-ground → curate → author).
Machine-readable truth lives in `brand.yaml`; this file is the human summary.

## The system in one paragraph

HubSpot is a **warm editorial SaaS system**: a warm off-white canvas (`#fcfcfa`)
with cream accents (`#f8f5ee`), one vivid orange (`#ff4800`) that carries every
primary action, checkmark, underline accent, heading period, and the wordmark
itself. Display headings are **HubSpot Serif, weight 500, sentence case** — 80px
in the photographic hero, 48/40px in sections — often closing with an orange
period. Body is **HubSpot Sans at the LIGHT weight (300)**, 16px/28px, which
gives the page its airy texture against 500-weight sans card headings. Buttons
are soft **8px-radius rectangles** (never pills) at three insets (8×16 / 12×24 /
16×40) with a constant 2px border slot. Cards are **flat white plates on
hairline borders** — hover is a wash plus a 1px ring, never elevation. Warm
peach→pink gradient art (`#fcc6b1`/`#fcc3dc`/`#ffa581`) paints one feature band
and section seams. Dark appears only as the closing sequence: a **deep-teal
conversion band** (`#042729`) and the **near-black footer** (`#1f1f1f`), both
with cream ink (`#f8f5ee`, never pure white).

## Type

| Role | Face | Size @1440 | Weight | Notes |
|---|---|---|---|---|
| Hero display | HubSpot Serif (Book master) | 80/95 | 400-glyph | orange period accent |
| Section H1 | HubSpot Serif | 48/55 | 500 | platform + closing band |
| Section H2 | HubSpot Serif | 40/44 | 500 | product/agents/case studies |
| Card heading lg | HubSpot Sans | 24/34 | 500 | agent cards |
| Statement heading | HubSpot Sans | 22/32 | 500 | logo strip, badges, banner |
| Card heading sm | HubSpot Sans | 18/28 | 500 | product cards |
| Body | HubSpot Sans | 16/28 | **300** | light body is a signature |
| Small body | HubSpot Sans | 14/22 | 300 | checklists |
| Eyebrow | HubSpot Sans | 14/22 | 500 | uppercase microlabel |
| Stat numerals | HubSpot Serif | ~44 | 400 | testimonial stats |

Both families are self-hosted from the capture (`assets/fonts/`): Sans
Book/Medium, Serif Book/Medium — weight mapping mirrors the source's own
`@font-face` blocks.

## Signature devices

- **Orange period accent** ending landmark serif headings.
- **Pill + dotted-rule rail**: bordered eyebrow pill joined by a dotted rule to
  a right-aligned quiet CTA (feature/proof section openers).
- **Ink links with orange underlines**; card text-arrows nudge 5px right on hover.
- **Round carousel controls** (48px, 50% radius) + dot rails; the agent track
  auto-plays with a pause control.
- **Real proof artifacts**: 5 customer logo vectors, 6 G2 badges, tabbed verbatim
  case-study quotes with workplace photography and serif stat numerals.

## Component recipes

Recurring multi-slot anatomies this brand reuses across sections — recorded as
first-class recipes in `layout-library.yaml` `recipes:` so generators compose
them as units instead of re-deriving the parts. This SaaS brand **opens its
major working bands with a headrail, not a bare eyebrow**: the rail is the
genre voice of the page.

### section-headrail — the house section opener

A leading identity kicker on a white plate, a **dotted 1px hairline leader
rule** running to the far content edge, optionally closed by a quiet
ink-outlined action; the section heading follows ~32px below. The rail always
spans the section's content container. One anatomy, three observed stylings:

- **icon-chip** — feature-band opener: the band's product identity as an
  icon-only chip (66×66, r16, hairline border, white plate, 32px icon). Seen on
  the agents carousel band; closes with the outlined "Get started free" CTA.
- **label-pill** — editorial section opener: a hairline label pill (14px w500
  sentence case, r4, 4×8 inset, white plate) leads the rail. Seen on the case-
  studies band; closes with the outlined CTA.
- **badge-with-icon** — in-column opener for split copy rails: icon+label badge
  (16px sparkle + label in one hairline box), no trailing action; the rail
  spans its own copy column, not the page. Seen on the "Powered by AI" split.

### Other recurring anatomy

- **Card plate family**: flat white plates on hairline borders (r8), media
  wells, 500-weight sans headings over 300-weight body, arrow-links that nudge
  right on hover — the agents carousel, product grid, and case-study rail all
  draw from this one family at different densities.
- **Action pair**: one filled-orange primary + one outlined secondary, 16px
  apart (24px on the closing band), left-anchored in reading-edge contexts,
  centered only in the photographic hero (`layoutGrammar.actionGroup`).

## Page rhythm (source order)

photo hero → logo proof strip → platform carousel → product grid (gradient seam)
→ agent carousel (gradient band) → integration banner → case-study rail →
testimonial tabs → badge row → deep-teal CTA → near-black footer.
