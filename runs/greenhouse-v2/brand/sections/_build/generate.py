#!/usr/bin/env python3
"""Generate 25 on-brand greenhouse-v2 sections (5 types x 5 variations).

Structure comes from the RELUME structural recipe catalog
(brand_pipeline/contracts/section-recipes/catalog.structural.yaml); ALL styling,
copy and media come from the measured greenhouse-v2 brand facts. No pipeline
renderer source is edited or imported.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import yaml

import brandkit as bk
from brandkit import page, fingerprint_leaf_svg, brand_g_badge

BRAND = bk.BRAND_DIR
OUT = BRAND / "sections"
ASSETS_SRC = BRAND / "assets"
ASSETS_DST = OUT / "assets"
COPY = yaml.safe_load((BRAND / "section-copy.yaml").read_text())

LC = COPY["layoutCopy"]
SC = COPY["sectionCopy"]

TAGLINE = "The all-together hiring platform"  # measured brand trademark (brand.yaml legal)

# ---- real greenhouse assets (from media-assets.yaml) ------------------------
def A(name: str) -> str:
    return f"../../assets/{name}"

PORT_WOMAN = "022-6716b884e5b3b85778949f5e-hiring-maturity-curve-and-woman-in-white-suit-in-brightly-lit-office.webp"
PORT_WALK = "023-6a0f41318cffb1788f1a6f43-6a06331af6baf12400fd36cb-en-nav-two-office-workers-chatting-while-walking-through-office.avif"
PORT_TABLET = "033-6a298fd15eb091333bcbe885-d-en-cg-home-two-office-workers-discussing-content-on-tablet-bright-space.png"
PORT_LAPTOP = "035-6a063cdcba100ecc20453980-d-en-cg-home-woman-in-suit-on-laptop-smiling-setup-job-alert-ui.avif"
PORT_NAV = "024-68dbdc1d5be3e4f3eb40d079-featured-nav-image-asset-402x.png"

UI_HERO = "030-689610cd7418c453485571fd-home-hero-m-clusters-of-three-solutions-workflows-with-photos-of-ui-and-people-working-402x.png"
UI_AI = "031-6a20cd945dce24bd4f73b612-d-en-hero-greenhouse-ai-notetaker-tool.avif"
UI_TALENT = "034-6a063cdddfe47d8d3429a902-d-en-cg-home-real-talent-fraud-detection-candidate-cards.avif"
UI_JOBBOARD = "037-66fede4422f8f7c1d1cb3f92-internal-job-board-and-add-a-referral-ui-with-green-fingerprint-collage-png.webp"
UI_POOLS = "033-66fedd7a62023763e2595fdc-collage-of-campaigin-pools-ui-and-fingerprint-leaf-png.webp"
UI_JOBAD = "032-676afa936f2bdcaefd2b096b-collage-of-job-ad-market-ui-and-partner-campaign-ui-with-fingerprint-leaf-m.avif"
UI_INTERVIEW = "051-67ae6cbf40adf97492caaeca-man-posing-wearing-glasses-and-gh-interview-kit-ui-fingerprint-leaf-illustration-uk.avif"

IC_DEI = "019-6716a7aa2b8818b873608ccb-greenhouse-dei-icon-and-office-worker-facing-cameria-in-collared-shirt.webp"
IC_SCORE = "020-6716b79fb7517eec7624852b-greenhouse-scorecard-icon-thumbs-up-and-office-worker-waving-to-person-virtually.webp"
IC_AI = "021-6716b8508a5978331488f06f-greenhouse-ai-icon-and-office-worker-sitting-at-a-table.webp"

LOGOS = [
    "036-68b07bd107c5a9802f71177f-coupang-logo.png",
    "038-67abbfc7a18f878bd4fd4189-hellofresh-logo.avif",
    "039-67264458a1a3be620e0a5033-trivago-company-logo.avif",
    "040-67abc305add47300764f9fd2-remote-logo.avif",
    "041-6724ffc984cbe2b871361fbb-gong-logo-515-c3-97-160.avif",
    "044-684b1591b49b84db80e1e68b-logo-anthropic.png",
    "045-684b154b7f3a0b8ea13a87db-logo-datavant.png",
    "046-6849817eafb5f7300bca18d3-revlon.png",
    "043-66db2afc7f4ffa8dac7d63af-coursera-2024-02-22-193551-bfgg.avif",
    "037-68b07c8b9ce3850b8412365a-trust-logo.png",
]
BADGES = [
    "042-6a1895bc83e54d86cbd45bbe-d-us-awards-image-g2-ent-leader-summer-2026-on-marigold-background.png",
    "043-6a1895bc8f2d9491ce3db846-d-us-awards-image-g2-mm-leader-summer-2026-on-marigold-background.png",
    "044-6a1895bc5ecfc15c4fdec10a-d-us-awards-image-g2-leader-europe-summer-2026-on-marigold-background.png",
]

# ---- small html helpers -----------------------------------------------------
def eyebrow(text, cls=""):
    return f'<span class="gh-eyebrow gh-eyebrow-gap {cls}">{text}</span>'

def display(text, cls=""):
    return f'<h1 class="gh-display {cls}">{text}</h1>'

def h2(text, cls=""):
    return f'<h2 class="gh-h2 {cls}">{text}</h2>'

def body(text, cls=""):
    return f'<p class="gh-body {cls}">{text}</p>'

def btn(text, kind="green", href="#"):
    return f'<a class="gh-btn gh-btn--{kind}" href="{href}">{text}</a>'

def link(text, kind="", href="#"):
    return (f'<a class="gh-link {kind}" href="{href}">{text}'
            f'<span class="gh-arrow" aria-hidden="true">&rarr;</span></a>')

def nav():
    links = "".join(f'<a class="gh-nav__link" href="#">{n}</a>' for n in SC["nav"])
    return f"""
<header class="gh-nav">
  <div class="gh-nav__inner">
    <a class="gh-nav__brand" href="#">{brand_g_badge(1.9)}<span>greenhouse</span></a>
    <nav class="gh-nav__links">{links}</nav>
    <div class="gh-nav__actions">
      <a class="gh-btn gh-btn--outline-dark gh-nav__signin" href="#">Sign In</a>
      <a class="gh-btn gh-btn--blue" href="#">Request a demo</a>
    </div>
  </div>
</header>
<style>
.gh-nav {{ background:#fff; border-bottom:1px solid var(--color-border-hairline-on-primary); }}
.gh-nav__inner {{ max-width:1320px; margin-inline:auto; display:flex; align-items:center;
  justify-content:space-between; gap:2rem; padding:1.1rem clamp(1.5rem,5vw,5rem); }}
.gh-nav__brand {{ display:flex; align-items:center; gap:.55rem; text-decoration:none;
  font-family:var(--gh-serif); font-size:1.4rem; color:var(--color-text-primary); }}
.gh-nav__links {{ display:flex; gap:1.6rem; }}
.gh-nav__link {{ font-family:var(--gh-sans); font-size:1rem; color:var(--color-text-primary);
  text-decoration:none; }}
.gh-nav__actions {{ display:flex; align-items:center; gap:.75rem; }}
.gh-nav .gh-btn {{ padding:10px 22px; }}
@media (max-width:1024px){{ .gh-nav__links,.gh-nav__signin{{display:none;}} }}
</style>
"""

# =============================================================================
# HERO — 5 relume-driven variations
# =============================================================================
def hero_v1():
    """RELUME hero-media-collage (skeleton=media-collage / archetype=collage).
    Signature greenhouse hero: centered serif display on mint canvas with
    floating product-UI cards + circle-cropped portraits."""
    return nav() + f"""
<section class="gh-sec gh-sec--band surf-tint" style="min-height:760px;">
  {fingerprint_leaf_svg('var(--color-accent-primary)', 0.05)}
  <style>.hero1-fp{{position:absolute; right:-120px; top:40px; width:520px; height:650px; opacity:.05;}}</style>
  <div class="gh-wrap gh-stack gh-stack--center" style="max-width:900px; min-height:640px; justify-content:center;">
    {eyebrow(TAGLINE)}
    {display(LC['hero']['heading'])}
    {body(LC['hero']['body'], 'gh-lead gh-heading-gap')}
    <div class="gh-actions gh-actions--center gh-cta-gap">
      {btn(LC['hero']['cta'], 'green')}
      {link(LC['hero']['ghost'], 'gh-link--ink')}
    </div>
  </div>
  <div class="gh-float" style="left:2%; top:120px; width:210px; height:150px;"><img src="{A(UI_TALENT)}" alt="Real Talent candidate cards"></div>
  <div class="gh-portrait" style="left:6%; bottom:70px; width:150px; height:150px;"><img src="{A(PORT_WOMAN)}" alt="Greenhouse customer"></div>
  <div class="gh-float" style="right:3%; top:150px; width:230px; height:165px;"><img src="{A(UI_AI)}" alt="Greenhouse AI notetaker"></div>
  <div class="gh-portrait" style="right:8%; bottom:60px; width:135px; height:135px;"><img src="{A(PORT_WALK)}" alt="Greenhouse customers"></div>
</section>
"""

def hero_v2():
    """RELUME hero-content-media-split (skeleton=content-media-split / split).
    Copy-left, floating product-UI card cluster right on white canvas."""
    return nav() + f"""
<section class="gh-sec surf-canvas" style="padding-top:5rem;padding-bottom:5rem;">
  <div class="gh-wrap gh-wrap--wide gh-split gh-split--wide-copy">
    <div class="gh-stack">
      {eyebrow('Greenhouse AI')}
      {display(LC['hero']['heading'])}
      {body(LC['hero']['body'], 'gh-lead gh-heading-gap')}
      <div class="gh-actions gh-cta-gap">
        {btn(LC['hero']['cta'], 'green')}
        {link(LC['hero']['ghost'], 'gh-link--ink')}
      </div>
    </div>
    <div style="position:relative; min-height:460px;">
      <div class="gh-media-well" style="position:absolute; inset:0 0 40px 40px;"><img src="{A(UI_JOBBOARD)}" alt="Greenhouse internal job board UI"></div>
      <div class="gh-float" style="left:-10px; bottom:0; width:230px; height:150px;"><img src="{A(UI_AI)}" alt="Greenhouse AI notetaker"></div>
      <div class="gh-portrait" style="right:-14px; top:-14px; width:120px; height:120px;"><img src="{A(PORT_WOMAN)}" alt="Greenhouse customer"></div>
    </div>
  </div>
</section>
"""

def hero_v3():
    """RELUME hero-content-stack (skeleton=content-stack / stack).
    Centered editorial copy stack with a single wide product illustration below."""
    return nav() + f"""
<section class="gh-sec surf-canvas" style="padding-bottom:0;">
  <div class="gh-wrap gh-stack gh-stack--center" style="max-width:860px;">
    {eyebrow(TAGLINE)}
    {display(LC['hero']['heading'])}
    {body(LC['hero']['body'], 'gh-lead gh-heading-gap')}
    <div class="gh-actions gh-actions--center gh-cta-gap">
      {btn(LC['hero']['cta'], 'green')}
      {link(LC['hero']['ghost'], 'gh-link--ink')}
    </div>
  </div>
  <div class="gh-wrap gh-wrap--wide" style="margin-top:3.5rem;">
    <div class="gh-media-well" style="aspect-ratio:16/7;"><img src="{A(UI_HERO)}" alt="Greenhouse platform overview"></div>
  </div>
</section>
"""

def hero_v4():
    """RELUME hero-media-background (skeleton=media-background / overlay).
    Inverse forest-green hero band, copy-left over a product visual right."""
    return nav() + f"""
<section class="gh-sec gh-sec--band surf-inverse">
  {fingerprint_leaf_svg('var(--color-accent-soft)', 0.09)}
  <style>#hero4 .gh-fingerprint{{left:-140px; bottom:-120px; width:560px; height:680px;}}</style>
  <div id="hero4" class="gh-wrap gh-wrap--wide gh-split">
    <div class="gh-stack">
      {eyebrow('Greenhouse Real Talent&trade;')}
      {display(LC['hero']['heading'])}
      {body(LC['hero']['body'], 'gh-lead gh-heading-gap')}
      <div class="gh-actions gh-cta-gap">
        {btn(LC['hero']['cta'], 'blue')}
        {link(LC['hero']['ghost'])}
      </div>
    </div>
    <div class="gh-media-well" style="aspect-ratio:4/3; background:transparent; box-shadow:none;">
      <img src="{A(UI_TALENT)}" alt="Real Talent fraud detection" style="border-radius:22px;">
    </div>
  </div>
</section>
"""

def hero_v5():
    """RELUME hero-repeated-grid (skeleton=repeated-grid / cards).
    Headline over a 3-up row of product entry-point cards."""
    items = [
        (LC['featureGrid']['items'][0]['heading'], UI_AI, 'See AI features'),
        (LC['featureGrid']['items'][1]['heading'], UI_TALENT, 'See Real Talent'),
        (LC['featureGrid']['items'][2]['heading'], UI_JOBBOARD, 'Explore MyGreenhouse'),
    ]
    cards = "".join(f"""
      <div class="gh-card">
        <div class="gh-card__media"><img src="{A(img)}" alt="{ttl}"></div>
        <div class="gh-card__body">{h2(ttl, 'gh-h3')}{link(cta)}</div>
      </div>""" for ttl, img, cta in items)
    return nav() + f"""
<section class="gh-sec gh-sec--band surf-tint">
  <div class="gh-wrap gh-wrap--wide">
    <div class="gh-stack gh-stack--center" style="max-width:820px;margin-inline:auto;">
      {eyebrow(TAGLINE)}
      {display(LC['hero']['heading'])}
      <div class="gh-actions gh-actions--center gh-cta-gap" style="margin-top:2rem;">
        {btn(LC['hero']['cta'], 'green')}{link(LC['hero']['ghost'], 'gh-link--ink')}
      </div>
    </div>
    <div class="gh-grid gh-grid--3" style="margin-top:3.5rem;">{cards}</div>
  </div>
</section>
"""

# =============================================================================
# FEATURE GRID — 5 relume-driven variations
# =============================================================================
def feature_v1():
    """RELUME feature-repeated-grid (repeated-grid / cards) — measured greenhouse
    featureGrid: heading full-width, 3-up media-top cards w/ trailing link."""
    imgs = [UI_AI, UI_TALENT, UI_JOBBOARD]
    cards = "".join(f"""
      <div class="gh-card">
        <div class="gh-card__media"><img src="{A(imgs[i])}" alt="{it['heading']}"></div>
        <div class="gh-card__body">
          {h2(it['heading'], 'gh-h3')}
          {body(it['body'])}
          {link(it['cta'])}
        </div>
      </div>""" for i, it in enumerate(LC['featureGrid']['items']))
    return f"""
<section class="gh-sec surf-canvas">
  <div class="gh-wrap gh-wrap--wide">
    {h2(LC['featureGrid']['heading'], 'gh-display')}
    <div class="gh-grid gh-grid--3" style="margin-top:3.5rem;">{cards}</div>
  </div>
</section>
"""

def feature_v2():
    """RELUME feature-content-media-split (content-media-split / split) —
    alternating media/content rows (order flips per row)."""
    it = LC['featureGrid']['items']
    def row(item, img, media_left):
        media = f'<div class="gh-media-well" style="aspect-ratio:4/3;"><img src="{A(img)}" alt="{item["heading"]}"></div>'
        copy = f'<div class="gh-stack">{eyebrow("Only in Greenhouse")}{h2(item["heading"])}{body(item["body"],"gh-heading-gap")}<div class="gh-cta-gap">{link(item["cta"])}</div></div>'
        inner = (media + copy) if media_left else (copy + media)
        return f'<div class="gh-split" style="margin-bottom:4rem;">{inner}</div>'
    rows = row(it[0], UI_TALENT, True) + row(it[1], UI_JOBBOARD, False)
    return f"""
<section class="gh-sec surf-canvas">
  <div class="gh-wrap gh-wrap--wide">
    <div style="max-width:720px;margin-bottom:3.5rem;">{eyebrow('Why Greenhouse')}{h2(LC['featureGrid']['heading'],'gh-display')}</div>
    {rows}
  </div>
</section>
"""

def feature_v3():
    """RELUME feature-tabs (tabs / cards) — tabbed feature switcher with a
    product-UI panel (static: first tab active)."""
    it = LC['featureGrid']['items']
    tabs = "".join(
        f'<button class="gh-tab {"gh-tab--on" if i==0 else ""}">{item["heading"]}</button>'
        for i, item in enumerate(it))
    active = it[0]
    return f"""
<section class="gh-sec surf-muted">
  <div class="gh-wrap gh-wrap--wide">
    <div class="gh-stack gh-stack--center" style="max-width:760px;margin-inline:auto;">
      {eyebrow('The Greenhouse platform')}{h2(LC['featureGrid']['heading'],'gh-display')}
    </div>
    <div class="gh-tabs" style="justify-content:center;margin:2.5rem 0;">{tabs}</div>
    <div class="gh-split" style="background:#fff;border-radius:24px;padding:clamp(2rem,4vw,3.5rem);box-shadow:var(--shadow-subtle);">
      <div class="gh-stack">{h2(active['heading'])}{body(active['body'],'gh-heading-gap')}<div class="gh-cta-gap">{btn(active['cta'],'green')}</div></div>
      <div class="gh-media-well" style="aspect-ratio:4/3;"><img src="{A(UI_AI)}" alt="{active['heading']}"></div>
    </div>
  </div>
</section>
"""

def feature_v4():
    """RELUME feature-media-collage (media-collage / collage) — single feature
    with a floating product-UI collage."""
    it = LC['featureGrid']['items'][2]
    return f"""
<section class="gh-sec gh-sec--band surf-tint">
  <div class="gh-wrap gh-wrap--wide gh-split gh-split--wide-media">
    <div class="gh-stack">
      {eyebrow('MyGreenhouse')}
      {h2(it['heading'],'gh-display')}
      {body(it['body'],'gh-lead gh-heading-gap')}
      <div class="gh-cta-gap">{btn(it['cta'],'green')}</div>
    </div>
    <div style="position:relative;min-height:460px;">
      <div class="gh-media-well" style="position:absolute; right:0; top:0; width:80%; aspect-ratio:4/3;"><img src="{A(UI_POOLS)}" alt="Greenhouse candidate pools"></div>
      <div class="gh-float" style="left:0; bottom:20px; width:250px; height:170px;"><img src="{A(UI_JOBBOARD)}" alt="Greenhouse job board"></div>
      <div class="gh-portrait" style="left:36%; top:-10px; width:120px; height:120px;"><img src="{A(PORT_LAPTOP)}" alt="Greenhouse customer"></div>
    </div>
  </div>
</section>
"""

def feature_v5():
    """RELUME feature-media-background (media-background / overlay) — inverse
    forest feature band with a 3-up icon-led feature set."""
    icons = [IC_AI, IC_SCORE, IC_DEI]
    it = LC['featureGrid']['items']
    cells = "".join(f"""
      <div class="gh-stack" style="gap:1rem;">
        <div class="gh-media-well" style="aspect-ratio:3/2;width:100%;background:rgba(255,255,255,.06);box-shadow:none;"><img src="{A(icons[i])}" alt="{it[i]['heading']}"></div>
        {h2(it[i]['heading'],'gh-h3')}
        {body(it[i]['body'])}
        {link(it[i]['cta'])}
      </div>""" for i in range(3))
    return f"""
<section class="gh-sec gh-sec--band surf-inverse">
  {fingerprint_leaf_svg('var(--color-accent-soft)', 0.06)}
  <style>#feat5 .gh-fingerprint{{right:-160px;top:-120px;width:520px;height:640px;}}</style>
  <div id="feat5" class="gh-wrap gh-wrap--wide">
    <div style="max-width:760px;">{eyebrow('Greenhouse AI')}{h2(LC['featureGrid']['heading'],'gh-display')}</div>
    <div class="gh-grid gh-grid--3" style="margin-top:3.5rem;">{cells}</div>
  </div>
</section>
"""

# =============================================================================
# TESTIMONIAL — 5 relume-driven variations
# =============================================================================
TQ = LC['testimonial']['items']
def testimonial_v1():
    """RELUME testimonial-repeated-grid (repeated-grid / cards) — measured
    greenhouse: heading top-left, 3-up quote blocks."""
    # 3 columns: reuse two real quotes + a compare-derived stat quote line
    quotes = [
        (TQ[0]['quote'], TQ[0]['heading'], TQ[0]['meta']),
        (TQ[1]['quote'], TQ[1]['heading'], TQ[1]['meta']),
        (LC['stats']['items'][0]['body'], 'Major League Baseball', 'Enterprise customer'),
    ]
    cols = "".join(f"""
      <div class="gh-stack" style="gap:1.25rem;">
        <span class="gh-quote-mark">&ldquo;</span>
        <p class="gh-quote">{q}</p>
        <div class="gh-person" style="margin-top:auto;">
          <div><div class="gh-person__name">{name}</div><div class="gh-person__meta">{meta}</div></div>
        </div>
      </div>""" for q, name, meta in quotes)
    return f"""
<section class="gh-sec surf-canvas">
  <div class="gh-wrap gh-wrap--wide">
    {h2(LC['testimonial']['heading'],'gh-display')}
    <div class="gh-grid gh-grid--3" style="margin-top:3.5rem;align-items:stretch;">{cols}</div>
  </div>
</section>
"""

def testimonial_v2():
    """RELUME testimonial-content-media-split (content-media-split / split) —
    single big quote + customer portrait panel."""
    q = TQ[0]
    return f"""
<section class="gh-sec surf-tint">
  <div class="gh-wrap gh-wrap--wide gh-split">
    <div class="gh-media-well" style="aspect-ratio:1/1;"><img src="{A(PORT_WOMAN)}" alt="{q['heading']}"></div>
    <div class="gh-stack" style="gap:1.5rem;">
      <span class="gh-quote-mark">&ldquo;</span>
      <p class="gh-quote" style="font-size:1.75rem;">{q['quote']}</p>
      <div class="gh-person">
        <div><div class="gh-person__name">{q['heading']}</div><div class="gh-person__meta">{q['meta']}</div></div>
      </div>
      {link('Read customer stories')}
    </div>
  </div>
</section>
"""

def testimonial_v3():
    """RELUME testimonial-carousel (carousel / cards) — peeking carousel of
    quote cards (static: 2 full + 1 clipped peek)."""
    cards = [TQ[0], TQ[1], TQ[0]]
    def card(q, faded=False):
        return f"""
      <div class="gh-card" style="min-width:420px;flex:0 0 420px;{'opacity:.5;' if faded else ''}">
        <div class="gh-card__body" style="gap:1.25rem;padding:2.25rem;">
          <span class="gh-quote-mark">&ldquo;</span>
          <p class="gh-quote">{q['quote']}</p>
          <div class="gh-person" style="margin-top:.5rem;">
            <div><div class="gh-person__name">{q['heading']}</div><div class="gh-person__meta">{q['meta']}</div></div>
          </div>
        </div>
      </div>"""
    track = card(cards[0]) + card(cards[1]) + card(cards[2], faded=True)
    return f"""
<section class="gh-sec surf-canvas">
  <div class="gh-wrap gh-wrap--wide">
    <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:2rem;flex-wrap:wrap;">
      {h2(LC['testimonial']['heading'],'gh-display')}
      <div class="gh-actions"><button class="gh-tab">&larr;</button><button class="gh-tab gh-tab--on">&rarr;</button></div>
    </div>
    <div style="display:flex;gap:2rem;margin-top:3rem;overflow:hidden;">{track}</div>
  </div>
</section>
"""

def testimonial_v4():
    """RELUME testimonial-content-stack (content-stack / stack) — centered single
    large pull-quote with avatar."""
    q = TQ[0]
    return f"""
<section class="gh-sec gh-sec--band surf-muted">
  <div class="gh-wrap gh-stack gh-stack--center" style="max-width:920px;">
    <span class="gh-quote-mark" style="font-size:5rem;height:3rem;">&ldquo;</span>
    <p class="gh-quote" style="font-size:2.25rem;text-align:center;line-height:1.35;">{q['quote']}</p>
    <div class="gh-person" style="margin-top:2.5rem;justify-content:center;">
      <div class="gh-person__avatar"><img src="{A(PORT_WALK)}" alt=""></div>
      <div style="text-align:left;"><div class="gh-person__name">{q['heading']}</div><div class="gh-person__meta">{q['meta']}</div></div>
    </div>
  </div>
</section>
"""

def testimonial_v5():
    """RELUME testimonial-media-background (media-background / overlay) — quote on
    inverse forest band flanked by G2 review-award badges."""
    q = TQ[1]
    badges = "".join(f'<img src="{A(b)}" alt="G2 award">' for b in BADGES)
    return f"""
<section class="gh-sec gh-sec--band surf-inverse">
  <div class="gh-wrap gh-stack gh-stack--center" style="max-width:960px;">
    {eyebrow('Demonstrated industry leadership')}
    <span class="gh-quote-mark">&ldquo;</span>
    <p class="gh-quote" style="font-size:2rem;text-align:center;line-height:1.35;">{q['quote']}</p>
    <div class="gh-person" style="margin-top:1.5rem;justify-content:center;">
      <div><div class="gh-person__name">{q['heading']}</div><div class="gh-person__meta">{q['meta']}</div></div>
    </div>
    <div class="gh-badges" style="justify-content:center;margin-top:3rem;">{badges}</div>
  </div>
</section>
"""

# =============================================================================
# LOGO WALL — 5 variations (relume logo-wall has 2 skeletons; distinctness via
# the recipe variant axes + the brand's measured split logos pattern)
# =============================================================================
def logos_v1():
    """RELUME logo-wall-repeated-grid (columns=2) rendered as the MEASURED
    greenhouse `logos` pattern: split copy-left + 2-col logo grid right + rule."""
    grid = "".join(f'<img src="{A(l)}" alt="customer logo">' for l in LOGOS[:6])
    return f"""
<section class="gh-sec surf-canvas">
  <div class="gh-wrap gh-wrap--wide" style="display:grid;grid-template-columns:1fr auto 1.2fr;gap:clamp(2rem,6vw,5rem);align-items:center;">
    <div class="gh-stack">
      {h2(LC['logos']['heading'],'gh-display')}
      <div class="gh-cta-gap">{btn(LC['logos']['cta'],'green')}</div>
    </div>
    <div class="gh-vrule gh-logos-rule"></div>
    <div class="gh-logogrid" style="grid-template-columns:repeat(2,1fr);">{grid}</div>
  </div>
  <style>@media(max-width:900px){{.gh-logos-rule{{display:none;}}}}</style>
</section>
"""

def logos_v2():
    """RELUME logo-wall-repeated-grid (columns=5) — centered heading over a
    single 5-up logo row on the mint canvas."""
    row = "".join(f'<img src="{A(l)}" alt="customer logo">' for l in LOGOS[:5])
    row2 = "".join(f'<img src="{A(l)}" alt="customer logo">' for l in LOGOS[5:10])
    return f"""
<section class="gh-sec surf-tint">
  <div class="gh-wrap gh-wrap--wide gh-stack gh-stack--center">
    {eyebrow('Great companies hire with Greenhouse')}
    {h2(LC['logos']['heading'],'gh-display')}
    <div class="gh-logogrid" style="grid-template-columns:repeat(5,1fr);width:100%;margin-top:3rem;">{row}{row2}</div>
  </div>
</section>
"""

def logos_v3():
    """RELUME logo-wall-repeated-grid (columns=3) — 6 logos in white cards
    inside a mint band, heading above."""
    cards = "".join(f'<div class="gh-logo-card"><img src="{A(l)}" alt="customer logo"></div>' for l in LOGOS[:6])
    return f"""
<section class="gh-sec surf-muted">
  <div class="gh-wrap gh-wrap--wide">
    <div style="display:flex;align-items:flex-end;justify-content:space-between;gap:2rem;flex-wrap:wrap;margin-bottom:2.5rem;">
      <div>{eyebrow('Proven leadership')}{h2(LC['logos']['heading'],'gh-display')}</div>
      {link(LC['logos']['cta'])}
    </div>
    <div class="gh-grid gh-grid--3">{cards}</div>
  </div>
</section>
"""

def logos_v4():
    """RELUME logo-wall-carousel (carousel / cards) — a single nowrap marquee row
    on an inverse forest band (logos kept in white chips to preserve colours)."""
    chips = "".join(f'<div class="gh-logo-card" style="min-width:180px;">'
                    f'<img src="{A(l)}" alt="customer logo"></div>' for l in LOGOS)
    return f"""
<section class="gh-sec surf-inverse" style="padding-top:5rem;padding-bottom:5rem;">
  <div class="gh-wrap gh-wrap--wide gh-stack gh-stack--center">
    {eyebrow('Great companies hire with Greenhouse')}
    <div style="display:flex;gap:1.5rem;overflow:hidden;margin-top:2rem;-webkit-mask:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent);mask:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent);">{chips}</div>
  </div>
</section>
"""

def logos_v5():
    """RELUME logo-wall-repeated-grid (columns=4 + actions) — a trust wall pairing
    customer logos with the G2 review-award badges."""
    grid = "".join(f'<img src="{A(l)}" alt="customer logo">' for l in LOGOS[:8])
    badges = "".join(f'<img src="{A(b)}" alt="G2 award">' for b in BADGES)
    return f"""
<section class="gh-sec surf-canvas">
  <div class="gh-wrap gh-wrap--wide gh-stack gh-stack--center">
    {eyebrow('Demonstrated industry leadership')}
    {h2(LC['logos']['heading'],'gh-display')}
    <div class="gh-logogrid" style="grid-template-columns:repeat(4,1fr);width:100%;margin-top:2.5rem;">{grid}</div>
    <div class="gh-badges" style="justify-content:center;margin-top:3rem;">{badges}</div>
    <div class="gh-cta-gap">{btn(LC['logos']['cta'],'green')}</div>
  </div>
</section>
"""

# =============================================================================
# CTA BAND — 5 relume-driven variations
# =============================================================================
def cta_v1():
    """RELUME cta-content-media-split (content-media-split / split) — measured
    greenhouse ctaBand: forest inverse, copy-left + blue pill, fingerprint art."""
    return f"""
<section class="gh-sec gh-sec--band surf-inverse">
  <div class="gh-wrap gh-wrap--wide gh-split">
    <div class="gh-stack">
      {h2(LC['ctaBand']['heading'],'gh-display')}
      <div class="gh-cta-gap">{btn(LC['ctaBand']['cta'],'blue')}</div>
    </div>
    <div style="position:relative;min-height:280px;">
      {fingerprint_leaf_svg('var(--color-accent-soft)', 0.7)}
      <style>#cta1 .gh-fingerprint{{right:0;top:50%;transform:translateY(-50%);width:300px;height:380px;}}</style>
    </div>
  </div>
  <div id="cta1"></div>
</section>
"""

def cta_v2():
    """RELUME cta-content-stack (content-stack / stack) — centered CTA stack on a
    forest band, primary pill + ghost."""
    return f"""
<section class="gh-sec gh-sec--band surf-inverse">
  {fingerprint_leaf_svg('var(--color-accent-soft)', 0.07)}
  <style>#cta2 .gh-fingerprint{{left:50%;top:-80px;transform:translateX(-50%);width:520px;height:620px;}}</style>
  <div id="cta2" class="gh-wrap gh-stack gh-stack--center" style="max-width:820px;">
    {eyebrow(TAGLINE)}
    {h2(LC['ctaBand']['heading'],'gh-display')}
    <div class="gh-actions gh-actions--center gh-cta-gap">
      {btn(LC['ctaBand']['cta'],'blue')}{link('Explore platform')}
    </div>
  </div>
</section>
"""

def cta_v3():
    """RELUME cta-media-background (media-background / overlay) — CTA over a
    photographic background with a forest overlay."""
    return f"""
<section class="gh-sec gh-sec--band" style="position:relative;color:#fff;">
  <img src="{A(PORT_TABLET)}" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0;">
  <div style="position:absolute;inset:0;background:linear-gradient(90deg,rgba(21,55,44,.94),rgba(21,55,44,.72));z-index:1;"></div>
  <div class="gh-wrap" style="max-width:640px;">
    <div class="gh-stack">
      {eyebrow('Why Greenhouse')}
      {h2(LC['ctaBand']['heading'],'gh-display')}
      <p class="gh-body gh-heading-gap" style="color:var(--color-text-on-inverse-muted);">Save more, hire with confidence and move faster with AI-powered tools built for every step of hiring.</p>
      <div class="gh-actions gh-cta-gap">{btn(LC['ctaBand']['cta'],'blue')}{btn('Explore platform','outline-white')}</div>
    </div>
  </div>
</section>
"""

def cta_v4():
    """RELUME cta-repeated-grid (repeated-grid / cards) — CTA heading over two
    option cards on the mint canvas."""
    options = [
        ('Talk to sales', 'See how Greenhouse fits your hiring process with a guided platform tour.', 'Request a demo', 'blue'),
        ('Start hiring better', 'Explore structured hiring, AI tooling and Real Talent trust layers.', 'Explore platform', 'green'),
    ]
    cards = "".join(f"""
      <div class="gh-card" style="padding:0;">
        <div class="gh-card__body" style="padding:2.5rem;gap:1rem;">
          {h2(t,'gh-h3')}{body(d)}
          <div style="margin-top:1rem;">{btn(c,k)}</div>
        </div>
      </div>""" for t, d, c, k in options)
    return f"""
<section class="gh-sec gh-sec--band surf-tint">
  <div class="gh-wrap gh-wrap--wide gh-stack gh-stack--center">
    {h2(LC['ctaBand']['heading'],'gh-display')}
    <div class="gh-grid gh-grid--2" style="margin-top:3rem;width:100%;max-width:960px;">{cards}</div>
  </div>
</section>
"""

def cta_v5():
    """RELUME cta-media-collage (media-collage / collage) — CTA heading with a
    floating product-UI collage anchored bottom, mint canvas."""
    return f"""
<section class="gh-sec surf-tint" style="padding-bottom:0;min-height:560px;">
  <div class="gh-wrap gh-stack gh-stack--center" style="max-width:760px;">
    {eyebrow(TAGLINE)}
    {h2(LC['ctaBand']['heading'],'gh-display')}
    <div class="gh-actions gh-actions--center gh-cta-gap">{btn(LC['ctaBand']['cta'],'green')}{link('Explore platform','gh-link--ink')}</div>
  </div>
  <div class="gh-wrap gh-wrap--wide" style="position:relative;height:220px;margin-top:2.5rem;">
    <div class="gh-float" style="left:4%;bottom:-40px;width:280px;height:190px;"><img src="{A(UI_JOBBOARD)}" alt="Greenhouse UI"></div>
    <div class="gh-float" style="left:36%;bottom:0;width:300px;height:200px;z-index:4;"><img src="{A(UI_AI)}" alt="Greenhouse AI"></div>
    <div class="gh-float" style="right:4%;bottom:-30px;width:280px;height:190px;"><img src="{A(UI_TALENT)}" alt="Greenhouse Real Talent"></div>
  </div>
</section>
"""

# =============================================================================
# registry + emit
# =============================================================================
SECTIONS = {
    "hero": {
        "label": "Hero",
        "variants": [
            ("hero-media-collage", "media-collage / collage",
             "Signature centered serif display on mint canvas with floating product-UI cards + circle portraits.", hero_v1),
            ("hero-content-media-split", "content-media-split / split",
             "Copy-left with a floating product-UI card cluster on the white canvas.", hero_v2),
            ("hero-content-stack", "content-stack / stack",
             "Centered editorial copy stack over one wide platform illustration.", hero_v3),
            ("hero-media-background", "media-background / overlay",
             "Inverse forest-green hero band, copy-left over a Real Talent product visual.", hero_v4),
            ("hero-repeated-grid", "repeated-grid / cards",
             "Headline over a 3-up row of product entry-point cards.", hero_v5),
        ],
    },
    "feature": {
        "label": "Feature grid",
        "variants": [
            ("feature-repeated-grid", "repeated-grid / cards",
             "Measured greenhouse feature grid: 3-up media-top cards with trailing links.", feature_v1),
            ("feature-content-media-split", "content-media-split / split",
             "Alternating media/content feature rows (order flips per row).", feature_v2),
            ("feature-tabs", "tabs / cards",
             "Tabbed feature switcher with a product-UI panel.", feature_v3),
            ("feature-media-collage", "media-collage / collage",
             "Single feature with a floating product-UI collage on mint.", feature_v4),
            ("feature-media-background", "media-background / overlay",
             "Inverse forest feature band with a 3-up icon-led feature set.", feature_v5),
        ],
    },
    "testimonial": {
        "label": "Testimonial",
        "variants": [
            ("testimonial-repeated-grid", "repeated-grid / cards",
             "Measured greenhouse: heading top-left over 3-up quote blocks.", testimonial_v1),
            ("testimonial-content-media-split", "content-media-split / split",
             "Single large quote beside a customer portrait panel.", testimonial_v2),
            ("testimonial-carousel", "carousel / cards",
             "Peeking carousel of quote cards with prev/next controls.", testimonial_v3),
            ("testimonial-content-stack", "content-stack / stack",
             "Centered single large pull-quote with avatar attribution.", testimonial_v4),
            ("testimonial-media-background", "media-background / overlay",
             "Quote on an inverse forest band flanked by G2 review-award badges.", testimonial_v5),
        ],
    },
    "logos": {
        "label": "Logo wall",
        "variants": [
            ("logo-wall-repeated-grid", "repeated-grid / cards (cols=2)",
             "Measured greenhouse split: copy-left + 2-col logo grid right, vertical rule.", logos_v1),
            ("logo-wall-repeated-grid", "repeated-grid / cards (cols=5, center)",
             "Centered heading over a 5-up logo row on the mint canvas.", logos_v2),
            ("logo-wall-repeated-grid", "repeated-grid / cards (cols=3, inset cards)",
             "6 logos in white inset cards on a grey band.", logos_v3),
            ("logo-wall-carousel", "carousel / cards",
             "Marquee logo strip on an inverse forest band (white chips preserve mark colours).", logos_v4),
            ("logo-wall-repeated-grid", "repeated-grid / cards (cols=4 + actions)",
             "Trust wall pairing customer logos with G2 review-award badges.", logos_v5),
        ],
    },
    "cta": {
        "label": "CTA band",
        "variants": [
            ("cta-content-media-split", "content-media-split / split",
             "Measured greenhouse CTA band: forest inverse, copy-left + blue pill, fingerprint-leaf art.", cta_v1),
            ("cta-content-stack", "content-stack / stack",
             "Centered CTA stack on a forest band, primary pill + ghost.", cta_v2),
            ("cta-media-background", "media-background / overlay",
             "CTA over a photographic background with a forest overlay.", cta_v3),
            ("cta-repeated-grid", "repeated-grid / cards",
             "CTA heading over two option cards on mint.", cta_v4),
            ("cta-media-collage", "media-collage / collage",
             "CTA with a floating product-UI collage anchored to the band base.", cta_v5),
        ],
    },
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS_DST.mkdir(parents=True, exist_ok=True)
    for f in ASSETS_SRC.iterdir():
        if f.is_file():
            shutil.copy2(f, ASSETS_DST / f.name)

    manifest = []
    for stype, spec in SECTIONS.items():
        (OUT / stype).mkdir(parents=True, exist_ok=True)
        for i, (recipe_id, struct, desc, fn) in enumerate(spec["variants"], start=1):
            vdir = OUT / stype / f"v{i}"
            vdir.mkdir(parents=True, exist_ok=True)
            title = f"Greenhouse — {spec['label']} v{i} ({recipe_id})"
            html = page(title, fn())
            (vdir / "index.html").write_text(html)
            manifest.append({
                "type": stype, "label": spec["label"], "v": i,
                "recipe_id": recipe_id, "structure": struct, "desc": desc,
                "path": f"{stype}/v{i}/index.html",
                "shot": f"shots/{stype}-v{i}.png",
            })

    (OUT / "_build" / "manifest.json").write_text(
        __import__("json").dumps(manifest, indent=2))
    print(f"generated {len(manifest)} sections into {OUT}")
    return manifest


if __name__ == "__main__":
    main()
