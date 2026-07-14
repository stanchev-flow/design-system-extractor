# Replica gate — rebuild-as-proof report

- brand: **HubSpot**
- source screenshot: `/Users/stanchev/Webflow/campaigns-hackathon/design-system-extractor-mine/screenshots/hubspot-v2/hubspot-fullpage.png`
- replica page: `index.html` → `replica-fullpage.png` (doc 6985px vs source 6986px)
- metric: score = 0.5·structure + 0.3·pixel + 0.2·height (Pillow RGB MAE; structure at 64px, pixel at 720px)
- `width` = content-span ratio (diagnostic, not in score): detected content width fraction of each band, min/max ratio — catches centered stacks collapsed to a fraction of the source's content width, which the averaged pixel metric barely registers
- **overall score (height-weighted): 0.957**

| band | source section | score | structure | pixel | height | width | src h | replica h | crops |
|---|---|---|---|---|---|---|---|---|---|
| page-nav | navbar (chrome header) | **0.977** | 0.977 | 0.961 | 1.000 | 1.000 | 128px | 128px | [side-by-side](diff/page-nav.png) |
| sec-0 | hero — Where go-to-market teams go to 
               grow scale close retain grow | **0.965** | 0.973 | 0.947 | 0.972 | 1.000 | 772px | 750px | [side-by-side](diff/sec-0.png) |
| sec-1 | logo-wall — 299,000+ customers in over 135 countries grow their businesses with HubSpot. | **0.975** | 0.987 | 0.975 | 0.946 | 1.000 | 261px | 276px | [side-by-side](diff/sec-1.png) |
| sec-2 | platform-carousel — HubSpot's Agentic Customer Platform | **0.948** | 0.952 | 0.943 | 0.945 | 0.938 | 742px | 701px | [side-by-side](diff/sec-2.png) |
| sec-3 | product-grid — Growing a business is hard. HubSpot makes it easier. | **0.971** | 0.981 | 0.967 | 0.951 | 0.975 | 1600px | 1682px | [side-by-side](diff/sec-3.png) |
| sec-4 | agent-carousel — Built-in AI agents that work for you 24/7. | **0.916** | 0.906 | 0.890 | 0.979 | 0.828 | 992px | 971px | [side-by-side](diff/sec-4.png) |
| sec-5 | integration-banner — Works with the tools you already use. 2,000+ integrations. | **0.938** | 0.933 | 0.923 | 0.971 | 1.000 | 330px | 340px | [side-by-side](diff/sec-5.png) |
| sec-6 | case-study-header — Remarkable results for every size business. | **0.970** | 0.986 | 0.967 | 0.938 | 1.000 | 240px | 256px | [side-by-side](diff/sec-6.png) |
| sec-7 | testimonial-tabs — section-7 | **0.961** | 0.960 | 0.944 | 0.990 | 0.842 | 714px | 707px | [side-by-side](diff/sec-7.png) |
| sec-8 | badge-row — Voted #1 in 526 G2 Reports | **0.950** | 0.968 | 0.954 | 0.900 | 0.944 | 216px | 240px | [side-by-side](diff/sec-8.png) |
| sec-9 | closing-cta — Make impossible growth feel impossibly easy, with HubSpot | **0.973** | 0.978 | 0.960 | 0.979 | 0.568 | 335px | 328px | [side-by-side](diff/sec-9.png) |
| footer | footer (closing bookend) | **0.966** | 0.980 | 0.971 | 0.924 | 0.971 | 656px | 606px | [side-by-side](diff/footer.png) |

![strip](diff/strip.png)

## Renderer-gap punch list

1. **hero — video static** (score 0.965): video static — the source embeds motion media; the composer renders a still
2. **agent-carousel — video static** (score 0.916): video static — the source embeds motion media; the composer renders a still
3. **closing-cta — content width diverges** (score 0.973): content span 0.39 of band vs source 0.69 (width fidelity 0.57) — check hug/measure collapse or over-wide container
4. **navbar — mega-menu open panels** (score 0.977): the brand declares mega-menu columns; the replica (and the source shot) render the closed bar only — open-panel fidelity is unexercised by this gate

Diagnostic, not blocking — re-run with `--fail-under <score>` to gate.
