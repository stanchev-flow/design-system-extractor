#!/usr/bin/env python3
"""Build the item-local Remote editorial-flow variant without shared-file edits."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
COMPOSE = HERE.parent
SOURCE = COMPOSE / "02 Remote"
ASSET_PREFIX = "../../../../remote/brand/assets/"

STRUCTURE = [
    "navigation",
    "type-led-offset-media-opener",
    "staggered-logo-proof-rail",
    "asymmetric-feature-narrative",
    "numbered-product-chapters",
    "vertical-employment-process-timeline",
    "editorial-resource-card-composition",
    "offset-quote-media-treatment",
    "awards-proof-band",
    "asymmetric-infrastructure-note",
    "strong-closing-band",
    "multi-column-footer",
]

SURFACES = [
    "surface/hero-noise",
    "surface/primary",
    "surface/primary",
    "surface/primary",
    "surface/primary",
    "surface/primary",
    "surface/primary",
    "surface/primary",
    "surface/primary",
    "surface/hero-noise",
    "surface/raised",
]

MEDIA = [
    ("navigation-wordmark", "remote-wordmark.svg", "logo"),
    ("opener-media", "hero-globe-illustration.webp", "hero-illustration"),
    ("feature-media", "collage-eor-ui.webp", "product-UI"),
    ("chapter-media", "panel-infrastructure-ui-snippet.webp", "product-graphic"),
    ("resource-mcp", "card-mcp-agents.webp", "product-graphic"),
    ("resource-integrations", "card-integrations.webp", "product-graphic"),
    ("resource-api", "card-api-first.webp", "product-graphic"),
    ("quote-media", "avatar-luke-mckinlay.webp", "testimonial-avatar"),
    ("footer-wordmark", "remote-wordmark.svg", "logo"),
]


def img(name: str, alt: str, cls: str = "") -> str:
    return f'<img class="{cls}" src="{ASSET_PREFIX}{name}" alt="{alt}" loading="lazy">'


def build() -> None:
    source = json.loads((SOURCE / "composition.json").read_text())
    tokens = json.loads((SOURCE / "tokens.manifest.json").read_text())
    contracts = source["componentContracts"]

    composition = {
        "schemaVersion": "composition.v1",
        "name": "04 Remote Variant — Editorial Flow",
        "displayName": "Remote Variant — Editorial Flow",
        "brandSource": "runs/remote/brand",
        "canonicalStatus": source["canonicalStatus"],
        "structure": STRUCTURE,
        "recipeSequence": [
            {"recipe": "hero-header-media-collage", "adaptation": "type-led offset media"},
            {"recipe": "logo-repeated-grid", "adaptation": "staggered horizontal proof rail"},
            {"recipe": "feature-media-collage", "adaptation": "asymmetric narrative"},
            {"recipe": "feature-content-stack", "adaptation": "numbered editorial chapters"},
            {"recipe": "timeline-timeline", "adaptation": "vertical process"},
            {"recipe": "feature-repeated-grid", "adaptation": "editorial card composition"},
            {"recipe": "testimonial-media-collage", "adaptation": "offset quote and portrait"},
            {"recipe": "logo-repeated-grid", "adaptation": "awards proof band"},
            {"recipe": "feature-content-stack", "adaptation": "asymmetric infrastructure note"},
            {"recipe": "cta-content-stack", "adaptation": "strong closing band"},
            {"recipe": "footer-content-stack", "adaptation": "canonical multi-column footer"},
        ],
        "surfaceSequence": SURFACES,
        "resolvedRhythm": source["resolvedRhythm"],
        "rhythmSources": source["rhythmSources"],
        "typographyStatus": source["typographyStatus"],
        "componentContractSource": source["componentContractSource"],
        "componentContracts": contracts,
        "componentDegradations": source["componentDegradations"],
        "mediaPolicy": "existing-extracted-assets-only",
        "mediaGeometryPolicy": "intrinsic extracted dimensions; no generic 4:3 ratios; grid children align without stretch",
        "mediaBindings": [
            {"slot": slot, "status": "resolved", "asset": asset, "useCase": use_case}
            for slot, asset, use_case in MEDIA
        ],
        "gaps": [],
        "acceptanceStatus": "pending browser verification",
    }
    (HERE / "composition.json").write_text(json.dumps(composition, indent=2) + "\n")
    tokens["variant"] = "editorial-flow"
    tokens["note"] = "Exact values inherited from the canonical Remote composition; structure only varies."
    (HERE / "tokens.manifest.json").write_text(json.dumps(tokens, indent=2) + "\n")

    logos = [
        ("logo-anthropic.svg", "Anthropic"), ("logo-gitlab.svg", "GitLab"),
        ("logo-vercel.svg", "Vercel"), ("logo-miro.svg", "Miro"),
        ("logo-datadog.svg", "Datadog"), ("logo-kfc.svg", "KFC"),
    ]
    badges = [
        ("badge-g2-gep-leader.webp", "G2 Global Employment Leader"),
        ("badge-g2-payroll-leader.webp", "G2 Payroll Leader"),
        ("badge-g2-top100-fastest-growing.webp", "G2 Fastest Growing"),
        ("badge-g2-top100-global-sellers.webp", "G2 Global Sellers"),
        ("badge-g2-top100-hr.webp", "G2 Top HR"),
        ("badge-g2-top50-hr.webp", "G2 Top 50 HR"),
    ]
    logo_html = "".join(
        f'<div class="proof-mark proof-mark--{i % 3}">{img(asset, alt)}</div>'
        for i, (asset, alt) in enumerate(logos)
    )
    badge_html = "".join(f'<div class="award">{img(asset, alt)}</div>' for asset, alt in badges)

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Remote editorial-flow structural variant using canonical extracted brand facts and assets.">
<title>Relume test · Remote Variant — Editorial Flow</title>
<style>
:root{{--canvas:#eff0f0;--raised:#f6f7f8;--panel:#fff;--ink:#141415;--muted:#383a3d;--navy:#00235c;--blue:#0564ff;--blue-hover:#0047bc;--blue-press:#003284;--pale:#dae2e8;--focus:#9bc1ff;--line:rgba(179,181,183,.4);--body:Inter,Arial,sans-serif;--display:'Lexend Deca',Arial,sans-serif;--container:76rem;--section-y:3rem;--gutter:2rem;--column-gap:3rem;--grid-gap:2rem;--radius:.625rem;--motion:200ms cubic-bezier(0,0,.2,1)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;overflow-x:hidden;background:var(--canvas);color:var(--ink);font:1.125rem/1.5 var(--body)}}img{{display:block;max-width:100%}}a{{color:inherit}}button,summary{{font:inherit}}:focus-visible{{outline:2px solid var(--blue-press);outline-offset:2px}}.skip{{position:fixed;z-index:99;left:1rem;top:1rem;transform:translateY(-180%);background:#fff;padding:.75rem 1rem}}.skip:focus{{transform:none}}
.container{{width:min(calc(100% - 2 * var(--gutter)),var(--container));margin-inline:auto}}.section{{padding:var(--section-y) 0}}.primary{{background:var(--canvas)}}.raised{{background:var(--raised)}}.hero-surface{{background:var(--pale)}}.eyebrow{{margin:0 0 .75rem;color:#0047bc;font-size:.875rem;letter-spacing:.05em;text-transform:uppercase}}h1,h2,h3,p,blockquote{{margin:0}}h1,h2,.quote{{font-family:var(--display);font-weight:400}}h1{{max-width:13ch;font-size:clamp(3rem,4vw,3.5rem);line-height:1.2}}h2{{font-size:clamp(2.25rem,3vw,2.875rem);line-height:1.2}}h3{{font-size:1.25rem;line-height:1.25}}.lede{{max-width:58ch;color:var(--muted)}}.actions{{display:flex;flex-wrap:wrap;gap:1rem;margin-top:2rem}}
.site-header{{position:sticky;top:0;z-index:30;background:var(--canvas);border-bottom:1px solid var(--line)}}.nav{{min-height:5rem;display:flex;align-items:center;gap:2rem}}.brand{{display:inline-flex;margin-right:auto}}.brand img{{width:auto;max-width:145px;max-height:38px}}.nav-links,.nav-actions{{display:flex;align-items:center;gap:1.5rem}}.nav-links a{{text-decoration:none}}
[data-control]{{display:inline-flex;align-items:center;justify-content:center;width:fit-content;text-decoration:none;cursor:pointer;transition:background-color var(--motion),color var(--motion),border-color var(--motion),box-shadow var(--motion)}}.control--primary{{height:3rem;padding:0 1.5rem;border:0;border-radius:2.5rem;background:#0564ff;color:#fff;font:500 1.125rem Inter,var(--body)}}.control--primary:hover{{background:#0047bc}}.control--primary:active{{background:#003284}}.control--primary:focus,.control--primary:focus-visible{{outline:2px solid #9bc1ff;outline-offset:2px}}.control--primary:disabled{{background:#ccdfff;color:#fff}}.control--secondary{{height:3rem;padding:0 1.5rem;border:1px solid #003284;border-radius:2.5rem;background:transparent;color:#003284;font:500 1.125rem Inter,var(--body)}}.control--secondary:hover{{background:#0564ff;color:#fff}}.control--secondary:active{{background:#0047bc;color:#fff}}.control--secondary:focus,.control--secondary:focus-visible{{outline:2px solid #9bc1ff;outline-offset:2px}}.control--secondary:disabled{{background:#ccdfff;color:#003284}}.control--tertiary,.menu-control{{height:3rem;padding:0 1.5rem;border:0;border-radius:2.5rem;background:#232325;color:#fff;font:500 1.125rem Inter,var(--body)}}.control--tertiary:hover,.menu-control:hover{{background:#595b5f}}.control--tertiary:active,.menu-control:active{{background:#383a3d}}.control--tertiary:focus,.control--tertiary:focus-visible,.menu-control:focus,.menu-control:focus-visible{{outline:2px solid #9bc1ff;outline-offset:2px}}.control--tertiary:disabled,.menu-control:disabled{{background:#d2d3d5;color:#fff}}.control--textCta{{height:auto;padding:0;border:0;border-radius:0;background:transparent;color:#0564ff;font:500 1rem Inter,var(--body);text-decoration:underline;text-underline-offset:.25em}}.control--textCta:hover,.control--textCta:active{{color:#0047bc}}.control--textCta:focus,.control--textCta:focus-visible{{outline:2px solid #9bc1ff;outline-offset:2px}}.control--textCta:disabled,.control--textCta[aria-disabled='true']{{background:#ccdfff;color:#0564ff;cursor:not-allowed}}.menu-control{{display:none}}
.opener{{padding:5rem 0}}.opener-grid{{display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr);gap:3rem;align-items:start}}.opener-copy{{padding-top:3rem}}.opener-copy .lede{{margin-top:1rem}}.opener-frame{{position:relative;align-self:start;padding:2rem 0 0 2rem}}.opener-frame:before{{content:"";position:absolute;inset:0 2rem 2rem 0;border:1px solid var(--line);border-radius:var(--radius)}}.opener-frame img{{position:relative;width:100%;height:auto;object-fit:contain;background:var(--navy);border-radius:var(--radius)}}
.proof-head{{display:grid;grid-template-columns:1fr 2fr;gap:3rem;align-items:end;margin-bottom:3rem}}.proof-rail{{display:grid;grid-template-columns:repeat(6,minmax(8rem,1fr));gap:2rem;align-items:start;overflow-x:auto;padding:1rem 0 2rem}}.proof-mark{{display:grid;min-width:8rem;height:4.5rem;place-items:center;border-top:1px solid var(--line)}}.proof-mark--1{{margin-top:2rem}}.proof-mark--2{{margin-top:4rem}}.proof-mark img{{max-width:8rem;max-height:3rem}}
.narrative{{display:grid;grid-template-columns:minmax(0,4fr) minmax(0,7fr);gap:5rem;align-items:start}}.narrative-copy{{position:sticky;top:8rem}}.narrative-copy .lede{{margin-top:1rem}}.media-frame{{align-self:start;min-width:0;background:var(--navy);border-radius:var(--radius);overflow:hidden}}.media-frame img{{width:100%;height:auto;object-fit:contain}}.chapter-list{{margin-top:3rem;border-top:1px solid var(--line)}}.chapter{{display:grid;grid-template-columns:4rem 1fr;gap:2rem;padding:2rem 0;border-bottom:1px solid var(--line)}}.chapter-no{{color:#0047bc}}.chapter p{{margin-top:.75rem;color:var(--muted)}}
.timeline-layout{{display:grid;grid-template-columns:5fr 7fr;gap:5rem;align-items:start}}.timeline{{border-left:1px solid var(--line);padding-left:3rem}}.step{{position:relative;padding:0 0 3rem}}.step:before{{content:"";position:absolute;left:-3.45rem;top:.35rem;width:.875rem;height:.875rem;border-radius:50%;background:var(--blue)}}.step p{{margin-top:.75rem;color:var(--muted)}}
.editorial-head{{display:grid;grid-template-columns:7fr 5fr;gap:3rem;align-items:end;margin-bottom:4rem}}.editorial-grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:2rem;align-items:start}}.story-card{{background:#fff;border:1px solid var(--line);border-radius:var(--radius);overflow:hidden}}.story-card:nth-child(1){{grid-column:1/span 7}}.story-card:nth-child(2){{grid-column:8/span 5;margin-top:5rem}}.story-card:nth-child(3){{grid-column:3/span 7}}.story-card img{{width:100%;height:auto;object-fit:cover;background:var(--navy)}}.story-body{{padding:2rem}}.story-body p{{margin:.75rem 0 1.5rem;color:var(--muted)}}
.quote-layout{{display:grid;grid-template-columns:4fr 8fr;gap:5rem;align-items:start}}.quote-portrait{{align-self:start;padding-top:4rem}}.quote-portrait img{{width:100%;height:auto;aspect-ratio:2000/1468;object-fit:cover;border-radius:var(--radius)}}.quote{{font-size:clamp(1.75rem,3vw,2.7rem);line-height:1.25}}.attribution{{margin-top:4rem;color:var(--muted)}}.award-layout{{display:grid;grid-template-columns:4fr 8fr;gap:3rem;align-items:start}}.awards{{display:grid;grid-template-columns:repeat(6,minmax(7rem,1fr));gap:2rem;overflow-x:auto}}.award{{min-width:7rem}}.award img{{width:auto;height:7rem;margin-inline:auto;object-fit:contain}}
.infrastructure{{display:grid;grid-template-columns:7fr 4fr;gap:5rem;align-items:center}}.infrastructure .media-frame{{order:1}}.infrastructure .copy{{order:2}}.infrastructure .lede{{margin-top:1rem}}.closing{{padding:5rem 0;background:var(--pale)}}.closing-grid{{display:grid;grid-template-columns:8fr 4fr;gap:3rem;align-items:end}}.closing .lede{{margin-top:1rem}}.closing .actions{{justify-content:flex-end}}
.footer{{padding:3rem 0 2rem;background:var(--raised)}}.footer-main{{display:grid;grid-template-columns:.8fr 2fr;gap:3rem}}.footer-brand{{display:flex;flex-direction:column;align-items:flex-start;gap:1.25rem}}.footer-grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:2rem}}.footer-column{{display:flex;flex-direction:column;gap:.8rem}}.footer-column h3{{font-size:.85rem;text-transform:uppercase;letter-spacing:.06em}}.footer-column a{{color:#595b5f;text-decoration:none}}.legal{{display:flex;justify-content:space-between;gap:1rem;margin-top:4rem;padding-top:1.5rem;border-top:1px solid var(--line);font-size:.8rem}}.preview-link{{position:fixed;right:1rem;bottom:1rem;z-index:30;background:var(--navy);color:#fff;padding:.55rem .8rem;font-size:.72rem;text-decoration:none}}
@media(max-width:980px){{.nav-links{{display:none}}.proof-rail,.awards{{grid-template-columns:none;grid-auto-flow:column;grid-auto-columns:9rem}}.footer-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:720px){{body{{font-size:1rem}}:root{{--section-y:2rem;--gutter:1rem;--column-gap:1.5rem}}h1{{font-size:1.75rem}}h2{{font-size:1.375rem}}.opener{{padding:5rem 0}}.menu-control{{display:inline-flex}}.nav-actions{{display:none;position:absolute;left:0;right:0;top:100%;padding:1rem;background:var(--canvas);border-bottom:1px solid var(--line);flex-direction:column}}.nav-actions.open{{display:flex}}.opener-grid,.proof-head,.narrative,.timeline-layout,.editorial-head,.quote-layout,.award-layout,.infrastructure,.closing-grid{{grid-template-columns:1fr;gap:1.5rem}}.opener-copy{{padding-top:0}}.opener-frame{{padding:1rem 0 0 1rem}}.proof-mark--1,.proof-mark--2{{margin-top:0}}.narrative-copy{{position:static}}.chapter{{grid-template-columns:2.5rem 1fr;gap:1rem}}.timeline{{padding-left:2rem}}.step:before{{left:-2.45rem}}.editorial-grid{{display:flex;flex-direction:column;gap:2rem}}.story-card:nth-child(n){{margin-top:0}}.quote-portrait{{padding-top:0;max-width:12rem}}.closing .actions{{justify-content:flex-start}}.footer-main,.footer-grid{{grid-template-columns:1fr}}.legal{{flex-direction:column}}}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}*{{transition-duration:.01ms!important}}}}
</style></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><nav class="container nav" aria-label="Primary"><a class="brand" href="#">{img("remote-wordmark.svg","Remote")}</a><div class="nav-links"><a href="#platform">Products</a><a href="#process">Solutions</a><a href="#resources">Resources</a><a href="#closing">Pricing</a></div><button class="menu-control" type="button" aria-expanded="false" aria-controls="mobile-actions">Menu</button><div class="nav-actions" id="mobile-actions"><a href="#resources">Sign up</a><a data-control class="control--tertiary" href="#closing">Book demo</a></div></nav></header>
<main id="main">
<section class="opener hero-surface" data-surface="surface/hero-noise"><div class="container opener-grid"><div class="opener-copy"><p class="eyebrow">GLOBAL EMPLOYMENT</p><h1>Global employment runs on Remote</h1><p class="lede">Hire and pay anyone in the world — with the compliance, reliability, and local expertise that only owned infrastructure delivers.</p><div class="actions"><a data-control class="control--primary" href="#platform">Book demo</a><a data-control class="control--secondary" href="#resources">Sign up</a></div></div><figure class="opener-frame">{img("hero-globe-illustration.webp","Remote globe product illustration")}</figure></div></section>
<section class="section primary" data-surface="surface/primary"><div class="container"><div class="proof-head"><p class="eyebrow">GLOBAL COMPANIES GROW WITH REMOTE</p><p class="lede">One employment platform, trusted across borders and operating models.</p></div><div class="proof-rail" role="list" aria-label="Customer logos">{logo_html}</div></div></section>
<section class="section primary" data-surface="surface/primary" id="platform"><div class="container narrative"><div class="narrative-copy"><p class="eyebrow">HOW WE DO IT</p><h2>One system of record. Every employment need.</h2><p class="lede">Move from first international hire to consolidated payroll without handing the work to a partner network.</p></div><div><div class="media-frame">{img("collage-eor-ui.webp","Employer of Record product UI collage")}</div><div class="chapter-list"><article class="chapter"><span class="chapter-no">01</span><div><h3>Employer of Record (EOR)</h3><p>Employment contracts, taxes, benefits, and compliance — onboarded in hours, not months.</p></div></article><article class="chapter"><span class="chapter-no">02</span><div><h3>Global Payroll</h3><p>Accurate, compliant payroll run by Remote’s in-house teams in every country you operate.</p></div></article><article class="chapter"><span class="chapter-no">03</span><div><h3>Contractor of Record (COR)</h3><p>Contracts, payments, and risk handled by local experts.</p></div></article><article class="chapter"><span class="chapter-no">04</span><div><h3>Contractor Management</h3><p>Engage contractors compliantly and convert them before misclassification risk grows.</p></div></article></div></div></div></section>
<section class="section primary" data-surface="surface/primary"><div class="container infrastructure"><div class="media-frame">{img("panel-infrastructure-ui-snippet.webp","Remote infrastructure product interface")}</div><div class="copy"><p class="eyebrow">INTELLIGENT INFRASTRUCTURE</p><h2>Owned end to end. Operated in house.</h2><p class="lede">Remote’s legal experts, payroll specialists, and compliance teams work on one infrastructure layer.</p><div class="actions"><a data-control class="control--primary" href="#process">Explore our platform</a></div></div></div></section>
<section class="section primary" data-surface="surface/primary" id="process"><div class="container timeline-layout"><div><p class="eyebrow">A CLEARER WAY FORWARD</p><h2>From first hire to one global view</h2></div><div class="timeline"><article class="step"><p class="eyebrow">STEP 01</p><h3>Choose the right employment path</h3><p>Hire employees through EOR, engage contractors, or bring existing entities into one operating view.</p></article><article class="step"><p class="eyebrow">STEP 02</p><h3>Onboard with local expertise</h3><p>Contracts, benefits, tax details, and compliance are handled through Remote’s owned infrastructure.</p></article><article class="step"><p class="eyebrow">STEP 03</p><h3>Run payroll with confidence</h3><p>Finance teams see currencies, contracts, and payroll status in one system of record.</p></article><article class="step"><p class="eyebrow">STEP 04</p><h3>Grow without rebuilding operations</h3><p>Add countries and worker types while keeping the same platform and support model.</p></article></div></div></section>
<section class="section primary" data-surface="surface/primary" id="resources"><div class="container"><div class="editorial-head"><div><p class="eyebrow">INTEGRATIONS, API, AND MCP</p><h2>Your workflows, your way, on our infrastructure</h2></div><p class="lede">Connect employment data to the tools and agents your teams already use.</p></div><div class="editorial-grid"><article class="story-card">{img("card-mcp-agents.webp","Remote MCP agents product card")}<div class="story-body"><p class="eyebrow">MCP</p><h3>Deploy AI agents on real employment data</h3><p>Give agents a secure connection to payroll, contracts, compliance data, and org structure.</p><a data-control class="control--textCta" href="#closing">Learn more</a></div></article><article class="story-card">{img("card-integrations.webp","Remote integrations product card")}<div class="story-body"><p class="eyebrow">INTEGRATIONS</p><h3>Plug Remote into your stack</h3><p>Keep the HR tools your team already uses while Remote runs payroll and compliance underneath.</p><a data-control class="control--textCta" href="#closing">Learn more</a></div></article><article class="story-card">{img("card-api-first.webp","Remote API-first product card")}<div class="story-body"><p class="eyebrow">API</p><h3>Build on top of ours</h3><p>Use the REST API, webhooks, and CLI to build custom workflows.</p><a data-control class="control--textCta" href="#closing">Learn more</a></div></article></div></div></section>
<section class="section primary" data-surface="surface/primary"><div class="container quote-layout"><figure class="quote-portrait">{img("avatar-luke-mckinlay.webp","Luke McKinlay")}</figure><div><p class="eyebrow">CUSTOMER STORY</p><blockquote class="quote">“If we had to manage and coordinate everything in-house, it would cost us well over $500,000 more each year.”</blockquote><p class="attribution">Luke McKinlay · VP of Finance</p></div></div></section>
<section class="section primary" data-surface="surface/primary"><div class="container award-layout"><div><p class="eyebrow">CUSTOMER-RATED</p><h2>The #1 global HR platform as voted by you</h2></div><div class="awards" role="list" aria-label="G2 awards">{badge_html}</div></div></section>
<section class="section primary" data-surface="surface/primary"><div class="container narrative"><div><p class="eyebrow">GLOBAL EMPLOYMENT</p><h2>Hiring internationally, converting contractors, or consolidating payroll?</h2></div><div><p class="lede">Talk to our team about the operating model behind your next stage of growth.</p><div class="actions"><a data-control class="control--primary" href="#closing">Book demo</a></div></div></div></section>
<section class="closing hero-surface" data-surface="surface/hero-noise" id="closing"><div class="container closing-grid"><div><p class="eyebrow">GLOBAL EMPLOYMENT</p><h2>Global employment is hard. We built the infrastructure to do it right.</h2><p class="lede">Remote handles the hard stuff with in-house payroll teams, local legal experts, and owned entities.</p></div><div class="actions"><a data-control class="control--primary" href="#footer">Book demo</a></div></div></section>
</main>
<footer class="footer" data-surface="surface/raised" id="footer"><div class="container"><div class="footer-main"><div class="footer-brand"><a class="brand" href="#">{img("remote-wordmark.svg","Remote")}</a><p>Hire and pay anyone in the world with owned infrastructure and local expertise.</p></div><nav class="footer-grid" aria-label="Footer"><section class="footer-column"><h3>Products</h3><a href="#">Employer of Record</a><a href="#">Global Payroll</a><a href="#">Contractor of Record</a><a href="#">Contractor Management</a></section><section class="footer-column"><h3>Infrastructure</h3><a href="#">Integrations</a><a href="#">API</a><a href="#">MCP</a><a href="#">PEO</a></section><section class="footer-column"><h3>Resources</h3><a href="#">Customer stories</a><a href="#">Global HR platform</a><a href="#">Compliance</a><a href="#">Pricing</a></section><section class="footer-column"><h3>Company</h3><a href="#">Products</a><a href="#">Solutions</a><a href="#">Resources</a><a href="#">Pricing</a></section></nav></div><div class="legal"><span>Remote · extracted brand facts</span><span>Editorial Flow · structure-only variant</span></div></div></footer>
<a class="preview-link" href="preview.png">Preview screenshot</a><script>const m=document.querySelector('.menu-control'),n=document.querySelector('.nav-actions');m?.addEventListener('click',()=>{{const o=m.getAttribute('aria-expanded')==='true';m.setAttribute('aria-expanded',String(!o));n.classList.toggle('open',!o)}});</script></body></html>"""
    (HERE / "index.html").write_text(html)
    (HERE / "changes.md").write_text(
        "# Remote Variant — Editorial Flow\n\n"
        "- Added as an item-local Studio composition; no shared builder or discovery file was changed.\n"
        "- Canonical source: `runs/remote/brand` (lane changelog inspected; no lane manifest exists on disk).\n"
        "- Structure varies; Remote tokens, component contracts/states, section rhythm, surfaces, nav, and footer remain invariant.\n"
        "- Relume structural priors are recorded in `composition.json#recipeSequence`; visual defaults were ignored.\n"
        "- All rendered media resolves to the extracted Remote asset inventory. No generated or invented media is used.\n"
        "- Media uses intrinsic/extracted ratios; no generic 4:3 ratio or stretch alignment is present.\n"
        "- Browser verification and screenshots: pending.\n"
    )


if __name__ == "__main__":
    build()
