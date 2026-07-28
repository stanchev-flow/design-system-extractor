# Replica gate — rebuild-as-proof report

- brand: **Greenhouse**
- source screenshot: `<repo>/screenshots/greenhouse-v2/home/home-fullpage.png`
- replica page: `index.html` → `replica-fullpage.png` (doc 4506px vs source 5031px)
- metric: score = 0.5·structure + 0.3·pixel + 0.2·height (Pillow RGB MAE; structure at 64px, pixel at 720px)
- `width` = content-span ratio (diagnostic, not in score): detected content width fraction of each band, min/max ratio — catches centered stacks collapsed to a fraction of the source's content width, which the averaged pixel metric barely registers
- **overall score (height-weighted): 0.873**

| band | source section | score | structure | pixel | height | width | src h | replica h | crops |
|---|---|---|---|---|---|---|---|---|---|
| page-nav | navbar (chrome header) | **0.000** | 0.000 | 0.000 | 0.000 | — | 0px | 81px | — |
| sec-0 | hero — The only hiring platform you’ll | **0.862** | 0.872 | 0.855 | 0.849 | 0.713 | 900px | 1060px | [side-by-side](diff/sec-0.png) |
| sec-1 | (unauthored) — Greenhouse introduces Voice AI following our acquisition of Ezra AI Labs, bringing conversational AI to the hiring proce | **0.000** | 0.000 | 0.000 | 0.000 | — | 132px | 0px | — |
| sec-2 | featuresThreeColumnCard — Real Talent | **0.856** | 0.841 | 0.815 | 0.953 | 0.882 | 634px | 665px | [side-by-side](diff/sec-2.png) |
| sec-3 | logoWall — Great companies hire with Greenhouse | **0.927** | 0.978 | 0.978 | 0.725 | 0.918 | 786px | 570px | [side-by-side](diff/sec-3.png) |
| sec-4 | featureGrid — The best teams start with hiring – and the best hiring starts with Greenhouse | **0.863** | 0.882 | 0.856 | 0.825 | 0.882 | 905px | 747px | [side-by-side](diff/sec-4.png) |
| sec-5 | cta — Everything you need to get better at hiring | **0.919** | 0.961 | 0.957 | 0.759 | 0.663 | 630px | 478px | [side-by-side](diff/sec-5.png) |
| footer | footer (closing bookend) | **0.945** | 0.968 | 0.959 | 0.868 | 0.952 | 1043px | 905px | [side-by-side](diff/footer.png) |

![strip](diff/strip.png)

## Structural gate

Signals the averaged-MAE score cannot carry: whether the rebuild used the same number of bands, the same kind of layout, and the same content span as the source.

| signal | value | floor | ok | detail |
| --- | --- | --- | --- | --- |
| bandCountAgreement | 0.8571 | 1.0 | **no** | 1 of 7 band slots diverge — measured but unauthored: ['sec-1']; the score averages over a census that does not match the source page |
| archetypeFamilyAgreement | 0.75 | 1.0 | **no** | cta: measured 2 track(s) composed as 'generic-flow' — the authored section carries no slot able to occupy the secondary track, so the measured band's second occupant was lost in projection, not in routing |
| contentSpanFidelity | 0.8433 | 0.8 | yes | rebuilt content occupies the measured share of each band |

**Structural gate: FAIL**

## Renderer-gap punch list

1. **hero — content width diverges** (score 0.862): content span 0.71 of band vs source 1.00 (width fidelity 0.71) — check hug/measure collapse or over-wide container
2. **sec-1 — fidelity below threshold** (score 0.000): band renders shorter (0px vs 132px); coarse layout structure diverges (module geometry / art direction); surface color / texture diverges
3. **cta — content width diverges** (score 0.919): content span 0.57 of band vs source 0.85 (width fidelity 0.66) — check hug/measure collapse or over-wide container
4. **page — display font ('Untitled Serif', Georgia, serif)**: not self-hosted and not Google-loadable — headings render in the declared fallback stack; extract the woff2 files into assets/fonts/
5. **page — band census**: 1 measured source band(s) have no authored pattern (index [1]) — scored as unauthored, not absorbed into a neighbour
6. **page — band census**: source chrome census has no measured header band — the page nav is excluded from scoring by declaration (its source pixels sit inside the first content band); fix the measure stage to score it
7. **page — structural gate**: bandCountAgreement: 0.8571 < floor 1.0 (1 of 7 band slots diverge — measured but unauthored: ['sec-1']; the score averages over a census that does not match the source page)
8. **page — structural gate**: archetypeFamilyAgreement: 0.75 < floor 1.0 (cta: measured 2 track(s) composed as 'generic-flow' — the authored section carries no slot able to occupy the secondary track, so the measured band's second occupant was lost in projection, not in routing)

Diagnostic, not blocking — re-run with `--fail-under <score>` to gate.
