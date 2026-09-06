#!/usr/bin/env python3
"""Load every built page in a real browser and prove it works. verify.py checks the words;
this checks the pixels and the behaviour. Both must pass before anything ships.

    cd <repo root>
    setsid python3 -m http.server 8899 &
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python3 _build/shot.py
"""
import asyncio, glob, os, sys
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8899"
PATHS = sorted(set(["/"] + ["/" + os.path.basename(f) for f in glob.glob(os.path.join(ROOT, "*.html"))
                            if os.path.basename(f) != "index.html"]))
SHOTS = [("/", "index"), ("/jessica-mackrael.html", "profile"), ("/moving-here.html", "moving"),
         ("/about.html", "about")]
WIDTHS = [(360, 780, "sm"), (390, 844, "mob"), (768, 1024, "tab"), (1440, 900, "desk")]

async def main():
    fails, errs = [], []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w, h, tag in WIDTHS:
            pg = await b.new_page(viewport={"width": w, "height": h})
            pg.on("pageerror", lambda ex: errs.append(str(ex)))
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            for path in PATHS:
                r = await pg.goto(BASE + path, wait_until="networkidle")
                if r.status != 200:
                    fails.append(f"{tag} {path}: HTTP {r.status}"); continue
                # the page itself must never scroll sideways; wide tables scroll inside their box
                x = await pg.evaluate("()=>{window.scrollTo(500,0);const x=window.scrollX;"
                                      "window.scrollTo(0,0);return x}")
                if x: fails.append(f"{tag} {path}: page scrolls sideways by {x}px")
                # the serif must have loaded - if it falls back to Times, fonts/ did not deploy
                if path == "/":
                    served = await pg.evaluate("()=>document.fonts.check('600 40px Newsreader')")
                    if not served: fails.append(f"{tag}: the Newsreader webfont did not load")
                for sp, name in SHOTS:
                    if sp == path and tag in ("desk", "mob"):
                        await pg.screenshot(path=f"/tmp/{name}-{tag}.png", full_page=(tag == "desk"))
            # every gutter on the front page must line up on the same pixel
            if tag == "desk":
                await pg.goto(BASE + "/", wait_until="networkidle")
                xs = await pg.evaluate("""() => {const q=s=>{const el=document.querySelector(s);
                  return el?Math.round(el.getBoundingClientRect().left):null};
                  return [q('.mast'),q('.folio'),q('h1'),q('.tablewrap')];}""")
                if len(set(xs)) != 1: fails.append(f"desk: gutters do not line up: {xs}")
            await pg.close()
        await b.close()
    print(f"{len(PATHS) * len(WIDTHS)} page loads checked")
    if errs: fails.append(f"console/page errors: {errs[:5]}")
    if fails:
        print(f"\n{len(fails)} FAILED:")
        for f in fails: print("  -", f)
        sys.exit(1)
    print("ALL PASS")

asyncio.run(main())
