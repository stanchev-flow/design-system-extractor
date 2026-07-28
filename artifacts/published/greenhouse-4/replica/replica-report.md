# Replica gate — rebuild-as-proof report

- brand: **Greenhouse**
- source screenshot: `screenshots/greenhouse-4/home/home-fullpage.png`
- replica page: `index.html` → `replica-fullpage.png` (doc 5150px vs source 5031px)
- metric: score = 0.5·structure + 0.3·pixel + 0.2·height (Pillow RGB MAE; structure at 64px, pixel at 720px)
- `width` = content-span ratio (diagnostic, not in score): detected content width fraction of each band, min/max ratio — catches centered stacks collapsed to a fraction of the source's content width, which the averaged pixel metric barely registers
- **overall score (height-weighted): 0.744**

| band | source section | score | structure | pixel | height | width | src h | replica h | crops |
|---|---|---|---|---|---|---|---|---|---|
| page-nav | navbar (chrome header) | **0.000** | 0.000 | 0.000 | 0.000 | — | 0px | 77px | — |
| sec-0 | hero — The only hiring platform you’ll | **0.772** | 0.847 | 0.832 | 0.496 | 0.913 | 900px | 1816px | [side-by-side](diff/sec-0.png) |
| sec-1 | featureGrid — Greenhouse introduces Voice AI following our acquisition of Ezra AI Labs, bringing conversational AI to the hiring proce | **0.278** | 0.313 | 0.301 | 0.158 | 0.755 | 132px | 835px | [side-by-side](diff/sec-1.png) |
| sec-2 | logoWall — Real Talent | **0.798** | 0.820 | 0.815 | 0.716 | 0.642 | 634px | 454px | [side-by-side](diff/sec-2.png) |
| sec-3 | stats — Great companies hire with Greenhouse | **0.885** | 0.872 | 0.868 | 0.941 | 0.805 | 786px | 835px | [side-by-side](diff/sec-3.png) |
| sec-4 | testimonial — The best teams start with hiring – and the best hiring starts with Greenhouse | **0.309** | 0.296 | 0.287 | 0.373 | 0.708 | 905px | 338px | [side-by-side](diff/sec-4.png) |
| sec-5 | cta — Everything you need to get better at hiring | **0.868** | 0.953 | 0.948 | 0.536 | 0.667 | 630px | 338px | [side-by-side](diff/sec-5.png) |
| footer | footer (closing bookend) | **0.941** | 0.969 | 0.962 | 0.843 | 0.440 | 1043px | 879px | [side-by-side](diff/footer.png) |

## Multi-viewport replica gate (Phase 5)

Desktop **fidelity** (the `overall` above) is scored against the source full-page screenshot, captured at the primary viewport only. The other viewports have no source shot to diff against, so they record a **responsiveness-health** number instead (1.0 = no horizontal overflow, every band present, reflow intact) — responsiveness is *verified*, not a faked cross-viewport SSIM.

| viewport | role | health | overflow px | bands | hero h | footer cols | doc h | shot |
|---|---|---|---|---|---|---|---|---|
| 1440 | primary (fidelity) | 1.0 | 0 | 7 | 1816px | 5 | 5150px | `replica-fullpage-1440.png` |
| 1920 | responsiveness | 1.0 | 0 | 7 | 1816px | 5 | 5184px | `replica-fullpage-1920.png` |
| 960 | responsiveness | 0.6167 | 184 (`c-foot-cols`) | 7 | 1511px | 6 | 5056px | `replica-fullpage-960.png` |
| 375 | responsiveness | 0.5 | 669 (`c-foot-cols`) | 7 | 1072px | 6 | 6411px | `replica-fullpage-375.png` |

![strip](diff/strip.png)

## Renderer-gap punch list

1. **hero — fidelity below threshold** (score 0.772): band renders taller (1816px vs 900px)
2. **featureGrid — fidelity below threshold** (score 0.278): band renders taller (835px vs 132px); coarse layout structure diverges (module geometry / art direction); surface color / texture diverges
3. **logoWall — content width diverges** (score 0.798): content span 0.54 of band vs source 0.84 (width fidelity 0.64) — check hug/measure collapse or over-wide container
4. **logoWall — fidelity below threshold** (score 0.798): band renders shorter (454px vs 634px)
5. **testimonial — content width diverges** (score 0.309): content span 0.59 of band vs source 0.83 (width fidelity 0.71) — check hug/measure collapse or over-wide container
6. **testimonial — fidelity below threshold** (score 0.309): band renders shorter (338px vs 905px); coarse layout structure diverges (module geometry / art direction); surface color / texture diverges
7. **cta — content width diverges** (score 0.868): content span 0.59 of band vs source 0.39 (width fidelity 0.67) — check hug/measure collapse or over-wide container
8. **page — display font ('Untitled Serif', Georgia, serif)**: not self-hosted and not Google-loadable — headings render in the declared fallback stack; extract the woff2 files into assets/fonts/

Diagnostic, not blocking — re-run with `--fail-under <score>` to gate.
