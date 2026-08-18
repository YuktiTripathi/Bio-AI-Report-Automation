#!/usr/bin/env python3
"""Rebuild the dedicated female At A Glance scene from stored Figma layers.

Does NOT use the male scene.png. Output:
  pdf_renderer/static/assets/at_a_glance/female/scene.png
  pdf_renderer/static/assets/at_a_glance/scene_female.png  (pipeline entry)

Requires assets already present under at_a_glance/female/ (bg, rings, circuits, glow, body, deco).
Refresh those from Figma first if layers change.
"""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
AAG = ROOT / "pdf_renderer/static/assets/at_a_glance"
FEM = AAG / "female"


def _key_circuits(raw: Image.Image) -> Image.Image:
    hi = raw.resize((raw.width * 3, raw.height * 3), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", hi.size, (0, 0, 0, 0))
    sp, dp = hi.load(), out.load()
    w, h = hi.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = sp[x, y]
            if abs(r - g) < 12 and abs(g - b) < 12 and 135 <= r <= 215:
                continue
            if (
                abs(r - g) < 20
                and abs(g - b) < 25
                and 140 <= r <= 210
                and r < 230
                and (r - max(g, b)) < 25
                and (r - g) < 18
            ):
                continue
            if r >= 50 and r >= g - 5:
                rr = min(255, int(r * 1.15 + 10))
                gg = min(255, int(g * 1.05))
                bb = min(255, int(b * 1.05))
                aa = 230 if (r - g) > 20 else 200
                dp[x, y] = (rr, gg, bb, aa)
    circuits = out.resize((258, 728), Image.Resampling.LANCZOS)
    cp = circuits.load()
    for y in range(circuits.height):
        for x in range(circuits.width):
            r, g, b, a = cp[x, y]
            if a and abs(r - g) < 10 and abs(g - b) < 10 and 145 <= r <= 205:
                cp[x, y] = (0, 0, 0, 0)
    return circuits


def _fit_glow(tex: Image.Image, tw: int = 142, th: int = 474) -> Image.Image:
    gw, gh = tex.size
    scale = max(tw / gw, th / gh)
    nw, nh = int(gw * scale + 0.5), int(gh * scale + 0.5)
    gs = tex.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    glow = gs.crop((left, top, left + tw, top + th))
    gp = glow.load()
    for y in range(th):
        for x in range(tw):
            r, g, b, a = gp[x, y]
            if a < 6:
                gp[x, y] = (0, 0, 0, 0)
    return glow


def prepare_derived() -> None:
    raw = Image.open(FEM / "circuits_raw.png").convert("RGBA")
    circuits = _key_circuits(raw)
    circuits.save(FEM / "circuits.png")
    circuits.save(AAG / "circuits_female.png")

    glow = _fit_glow(Image.open(FEM / "body_glow_tex.png").convert("RGBA"))
    glow.save(FEM / "body_glow.png")
    glow.save(AAG / "body_glow_female.png")

    deco_raw = Image.open(FEM / "deco_tri.png").convert("RGBA")
    deco = Image.new("RGBA", deco_raw.size, (0, 0, 0, 0))
    sp, dp = deco_raw.load(), deco.load()
    for y in range(deco_raw.height):
        for x in range(deco_raw.width):
            r, g, b, a = sp[x, y]
            if abs(r - g) < 12 and abs(g - b) < 12 and 120 <= r <= 210:
                continue
            if r > 80 and r >= g:
                dp[x, y] = (r, g, b, min(255, int(a * 0.9)) if a else 180)
    deco.save(FEM / "deco_glow.png")
    deco.save(AAG / "deco_glow_female.png")

    shutil.copy(FEM / "body.svg", AAG / "body_female.svg")
    shutil.copy(FEM / "bg.svg", AAG / "bg_female.svg")


async def compose() -> None:
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  html, body {{ margin:0; padding:0; background:#002826; }}
  .page {{ position:relative; width:595px; height:842px; overflow:hidden; background:#002826; }}
  .bg {{ position:absolute; left:-3.21px; top:-6.58px; width:601.42px; height:855.16px; display:block; }}
  .rings {{
    position:absolute; left:160.41px; top:-2.82px; width:274.16px; height:847.65px;
    display:block; mix-blend-mode:luminosity; opacity:0.7; pointer-events:none;
  }}
  .circuits {{
    position:absolute; left:168.34px; top:113.83px; width:258.31px; height:728.17px;
    display:block; pointer-events:none; opacity:0.95;
  }}
  .deco {{ position:absolute; left:144.31px; width:306.34px; opacity:0.20; object-fit:cover; pointer-events:none; }}
  .glow {{ position:absolute; left:226.71px; top:263.02px; width:141.53px; height:474.06px; display:block; }}
  .body {{ position:absolute; left:241.86px; top:278.19px; width:111.30px; height:443.74px; display:block; }}
</style></head><body>
<div class="page" id="p">
  <img class="bg" src="{(FEM / 'bg.svg').as_uri()}" />
  <img class="rings" src="{(FEM / 'rings.svg').as_uri()}" />
  <img class="circuits" src="{(FEM / 'circuits.png').as_uri()}" />
  <img class="deco" style="top:451.08px;height:307.48px" src="{(FEM / 'deco_glow.png').as_uri()}" />
  <img class="deco" style="top:551.66px;height:211.47px" src="{(FEM / 'deco_glow.png').as_uri()}" />
  <img class="glow" src="{(FEM / 'body_glow.png').as_uri()}" />
  <img class="body" src="{(FEM / 'body.svg').as_uri()}" />
</div>
</body></html>"""
    html_path = FEM / "_compose.html"
    html_path.write_text(html)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 595, "height": 842}, device_scale_factor=3)
        await page.goto(html_path.as_uri())
        await page.wait_for_timeout(400)
        el = await page.query_selector("#p")
        assert el is not None
        await el.screenshot(path=str(FEM / "scene_hi.png"), omit_background=False)
        await browser.close()

    im = Image.open(FEM / "scene_hi.png").convert("RGBA").resize((595, 842), Image.Resampling.LANCZOS)
    im.save(FEM / "scene.png")
    im.save(AAG / "scene_female.png")
    print(f"Wrote {FEM / 'scene.png'}")
    print(f"Wrote {AAG / 'scene_female.png'}")


def main() -> None:
    required = ["bg.svg", "rings.svg", "circuits_raw.png", "body_glow_tex.png", "body.svg", "deco_tri.png"]
    missing = [n for n in required if not (FEM / n).exists()]
    if missing:
        raise SystemExit(f"Missing female AAG source layers in {FEM}: {missing}")
    prepare_derived()
    asyncio.run(compose())


if __name__ == "__main__":
    main()
