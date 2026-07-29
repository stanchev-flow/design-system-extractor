# Replica gate — rebuild-as-proof report

- brand: **Greenhouse**
- source screenshot: `screenshots/greenhouse-v2/home/home-fullpage.png`
- replica page: `index.html` → `replica-fullpage.png` (doc 14746px vs source 5031px)
- metric: score = 0.5·structure + 0.3·pixel + 0.2·height (Pillow RGB MAE; structure at 64px, pixel at 720px)
- `width` = content-span ratio (diagnostic, not in score): detected content width fraction of each band, min/max ratio — catches centered stacks collapsed to a fraction of the source's content width, which the averaged pixel metric barely registers
- **overall score (height-weighted): 0.854**

| band | source section | score | structure | pixel | height | width | src h | replica h | crops |
|---|---|---|---|---|---|---|---|---|---|
| page-nav | navbar (chrome header) | **0.000** | 0.000 | 0.000 | 0.000 | — | 0px | 81px | — |
| sec-0 | hero — The only hiring platform you’ll | **0.857** | 0.873 | 0.857 | 0.817 | 0.713 | 900px | 1102px | [side-by-side](diff/sec-0.png) |
| sec-1 | featureGrid — Greenhouse introduces Voice AI following our acquisition of Ezra AI Labs, bringing conversational AI to the hiring proce | **0.292** | 0.325 | 0.315 | 0.177 | 0.809 | 132px | 746px | [side-by-side](diff/sec-1.png) |
| sec-2 | logoWall — Real Talent | **0.833** | 0.817 | 0.814 | 0.901 | 0.996 | 634px | 571px | [side-by-side](diff/sec-2.png) |
| sec-3 | stats — Great companies hire with Greenhouse | **0.860** | 0.948 | 0.943 | 0.514 | 0.818 | 786px | 404px | [side-by-side](diff/sec-3.png) |
| sec-4 | testimonial — The best teams start with hiring – and the best hiring starts with Greenhouse | **0.792** | 0.870 | 0.868 | 0.486 | 0.433 | 905px | 440px | [side-by-side](diff/sec-4.png) |
| sec-5 | cta — Everything you need to get better at hiring | **0.920** | 0.961 | 0.957 | 0.760 | 0.663 | 630px | 479px | [side-by-side](diff/sec-5.png) |
| footer | footer (closing bookend) | **0.945** | 0.968 | 0.959 | 0.867 | 0.952 | 1043px | 904px | [side-by-side](diff/footer.png) |

## Multi-viewport replica gate (Phase 5)

Desktop **fidelity** (the `overall` above) is scored against the source full-page screenshot, captured at the primary viewport only. The other viewports have no source shot to diff against, so they record a **responsiveness-health** number instead (1.0 = no horizontal overflow, every band present, reflow intact) — responsiveness is *verified*, not a faked cross-viewport SSIM.

| viewport | role | health | overflow px | bands | hero h | footer cols | doc h | shot |
|---|---|---|---|---|---|---|---|---|
| 1440 | primary (fidelity) | 1.0 | 0 | 19 | 1102px | 5 | 14746px | `replica-fullpage-1440.png` |
| 1920 | responsiveness | 1.0 | 0 | 19 | 1136px | 5 | 14987px | `replica-fullpage-1920.png` |
| 960 | responsiveness | 0.6167 | 184 (`c-foot-cols`) | 19 | 1542px | 6 | 14809px | `replica-fullpage-960.png` |
| 375 | responsiveness | 0.5 | 669 (`c-foot-cols`) | 19 | 1067px | 6 | 17237px | `replica-fullpage-375.png` |

![strip](diff/strip.png)

## Structural gate

Signals the averaged-MAE score cannot carry: whether the rebuild used the same number of bands, the same kind of layout, and the same content span as the source.

| signal | value | floor | ok | detail |
| --- | --- | --- | --- | --- |
| bandCountAgreement | 1.0 | 1.0 | yes | every measured content band is rebuilt by exactly one authored section |
| archetypeFamilyAgreement | 0.6875 | 1.0 | **no** | stats: measured 3 track(s) composed as 'generic-flow'; testimonial: measured 3 track(s) composed as 'generic-flow'; cta: measured 2 track(s) composed as 'generic-flow' — the authored section carries no slot able to occupy the secondary track, so the measured band's second occupant was lost in projection, not in routing; features: measured 3 track(s) composed as 'generic-flow'; featuresSectionHeadingTop: measured 3 track(s) composed as 'generic-flow' |
| contentSpanFidelity | 0.7604 | 0.8 | **no** | rebuilt content spans a different share of the band than the source — a collapsed or over-wide container leaves most of the band as matching background, so the averaged metric barely registers it |

**Structural gate: FAIL**

## Renderer-gap punch list

1. **hero — content width diverges** (score 0.857): content span 0.71 of band vs source 1.00 (width fidelity 0.71) — check hug/measure collapse or over-wide container
2. **featureGrid — fidelity below threshold** (score 0.292): band renders taller (746px vs 132px); coarse layout structure diverges (module geometry / art direction); surface color / texture diverges
3. **logoWall — fidelity below threshold** (score 0.833): inspect the side-by-side crop
4. **testimonial — content width diverges** (score 0.792): content span 0.36 of band vs source 0.84 (width fidelity 0.43) — check hug/measure collapse or over-wide container
5. **testimonial — fidelity below threshold** (score 0.792): band renders shorter (440px vs 905px)
6. **cta — content width diverges** (score 0.920): content span 0.57 of band vs source 0.85 (width fidelity 0.66) — check hug/measure collapse or over-wide container
7. **page — display font ('Untitled Serif', Georgia, serif)**: not self-hosted and not Google-loadable — headings render in the declared fallback stack; extract the woff2 files into assets/fonts/
8. **page — band census**: provenance anchoring unavailable (12/17 pairs resolved, 5 distinct) — falling back to positional band pairing
9. **page — band census**: source chrome census has no measured header band — the page nav is excluded from scoring by declaration (its source pixels sit inside the first content band); fix the measure stage to score it
10. **page — structural gate**: archetypeFamilyAgreement: 0.6875 < floor 1.0 (stats: measured 3 track(s) composed as 'generic-flow'; testimonial: measured 3 track(s) composed as 'generic-flow'; cta: measured 2 track(s) composed as 'generic-flow' — the authored section carries no slot able to occupy the secondary track, so the measured band's second occupant was lost in projection, not in routing; features: measured 3 track(s) composed as 'generic-flow'; featuresSectionHeadingTop: measured 3 track(s) composed as 'generic-flow')
11. **page — structural gate**: contentSpanFidelity: 0.7604 < floor 0.8 (rebuilt content spans a different share of the band than the source — a collapsed or over-wide container leaves most of the band as matching background, so the averaged metric barely registers it)

Diagnostic, not blocking — re-run with `--fail-under <score>` to gate.
