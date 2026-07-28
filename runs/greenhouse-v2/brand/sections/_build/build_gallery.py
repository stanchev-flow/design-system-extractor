#!/usr/bin/env python3
"""Build the review gallery + per-type contact sheets from the captured
per-section PNGs (robust: no live-iframe compositing), then screenshot them.

Run AFTER generate.py + capture.py have produced shots/<type>-v<n>.png.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent
SHOTS = OUT / "shots"
MANIFEST = json.loads((OUT / "_build" / "manifest.json").read_text())

FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,'
         'wght@9..144,300..500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')

by_type = OrderedDict()
for m in MANIFEST:
    by_type.setdefault(m["type"], {"label": m["label"], "items": []})
    by_type[m["type"]]["items"].append(m)


CONTACT_CSS = """
*{box-sizing:border-box;}
body{margin:0;font-family:'Inter',Arial,sans-serif;background:#eef1f0;color:#15372c;padding:40px;}
.back{display:inline-block;margin-bottom:1.25rem;color:#008561;text-decoration:none;}
h1{font-family:'Fraunces',Georgia,serif;font-weight:400;font-size:2.4rem;margin:0 0 .35rem;}
.lead{color:#5b716a;margin:0 0 2.5rem;max-width:74ch;}
.item{background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,.08);margin-bottom:2.5rem;}
.item a{display:block;}
.item img{display:block;width:100%;height:auto;border-bottom:1px solid #e3e8e6;}
.cap{padding:1rem 1.5rem;display:flex;flex-direction:column;gap:.15rem;}
.cap strong{font-size:1.05rem;}
.cap .rid{color:#008561;font-family:'Inter';font-size:.85rem;}
.cap span{color:#5b716a;font-size:.9rem;}
"""


def build_contact(stype, data):
    items = ""
    for m in data["items"]:
        items += f"""
  <figure class="item">
    <a href="v{m['v']}/index.html"><img src="../shots/{stype}-v{m['v']}.png" alt="{stype} v{m['v']}"></a>
    <figcaption class="cap">
      <strong>v{m['v']} · {m['label']}</strong>
      <span class="rid">RELUME recipe: <code>{m['recipe_id']}</code> — {m['structure']}</span>
      <span>{m['desc']}</span>
    </figcaption>
  </figure>"""
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Greenhouse — {data['label']} contact sheet</title>{FONTS}
<style>{CONTACT_CSS}</style></head><body>
<a class="back" href="../index.html">&larr; All sections</a>
<h1>{data['label']}</h1>
<p class="lead">5 on-brand greenhouse-v2 variations. Structure selected from the RELUME structural recipe catalog; every colour, type ramp, pill button, surface, copy string and image is bound from the measured greenhouse-v2 brand facts.</p>
{items}
</body></html>"""
    (OUT / stype / "index.html").write_text(doc)


GALLERY_CSS = """
*{box-sizing:border-box;}
body{margin:0;font-family:'Inter',Arial,sans-serif;background:#c9f0e6;color:#15372c;}
.hero{padding:60px 48px 30px;}
.hero h1{font-family:'Fraunces',Georgia,serif;font-weight:400;font-size:3rem;margin:0 0 .5rem;letter-spacing:-.01em;}
.hero p{max-width:80ch;color:#2f4a41;font-size:1.05rem;margin:0;}
.wrap{padding:0 48px 80px;}
.group{margin-top:3rem;}
.group-head{display:flex;align-items:baseline;justify-content:space-between;border-bottom:1px solid rgba(21,55,44,.15);padding-bottom:.7rem;margin-bottom:1.5rem;}
.group-head h2{font-family:'Fraunces',Georgia,serif;font-weight:400;font-size:1.8rem;margin:0;}
.group-head a{color:#008561;text-decoration:none;font-size:.95rem;}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:1.75rem;}
.tile{background:#fff;border-radius:14px;overflow:hidden;text-decoration:none;color:inherit;box-shadow:0 6px 24px rgba(0,0,0,.08);transition:transform .18s,box-shadow .18s;}
.tile:hover{transform:translateY(-4px);box-shadow:0 14px 36px rgba(0,0,0,.14);}
.tile-frame{height:220px;overflow:hidden;border-bottom:1px solid #eef1f0;background:#fff;}
.tile-frame img{width:100%;display:block;}
.tile-cap{padding:.8rem 1.1rem;font-size:.9rem;}
.tile-cap strong{color:#008561;}
.tile-cap span{display:block;color:#5b716a;font-size:.8rem;margin-top:.12rem;}
"""


def build_gallery():
    blocks = ""
    for stype, data in by_type.items():
        tiles = ""
        for m in data["items"]:
            tiles += f"""
      <a class="tile" href="{stype}/v{m['v']}/index.html">
        <div class="tile-frame"><img src="shots/{stype}-v{m['v']}.png" alt="{stype} v{m['v']}"></div>
        <div class="tile-cap"><strong>v{m['v']}</strong> · {m['recipe_id']}<span>{m['structure']}</span></div>
      </a>"""
        blocks += f"""
  <section class="group">
    <div class="group-head"><h2>{data['label']}</h2><a href="{stype}/index.html">Contact sheet &rarr;</a></div>
    <div class="tiles">{tiles}</div>
  </section>"""
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Greenhouse-v2 — RELUME section gallery (25)</title>{FONTS}
<style>{GALLERY_CSS}</style></head><body>
<div class="hero">
  <h1>Greenhouse · RELUME section bake-off</h1>
  <p>25 on-brand sections — 5 types &times; 5 variations. Structure is selected from the RELUME structural recipe catalog; every colour, type ramp, pill button, surface, copy string and image is bound from the measured greenhouse-v2 brand facts. Held for review.</p>
</div>
<div class="wrap">{blocks}</div>
</body></html>"""
    (OUT / "index.html").write_text(doc)


def shoot():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 400}, device_scale_factor=1)
        for stype in by_type:
            pg.goto((OUT / stype / "index.html").as_uri())
            pg.wait_for_timeout(600)
            pg.screenshot(path=str(SHOTS / f"{stype}-contact.png"), full_page=True)
            print("contact sheet", f"{stype}-contact.png")
        pg.goto((OUT / "index.html").as_uri())
        pg.wait_for_timeout(800)
        pg.screenshot(path=str(SHOTS / "gallery.png"), full_page=True)
        print("gallery.png")
        b.close()


if __name__ == "__main__":
    for stype, data in by_type.items():
        build_contact(stype, data)
    build_gallery()
    shoot()
    print("gallery + contact sheets built")
