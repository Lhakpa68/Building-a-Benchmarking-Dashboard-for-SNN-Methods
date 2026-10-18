import subprocess, time, sys, os
from playwright.sync_api import sync_playwright
env=dict(os.environ, SNN_RESULTS_DIR="/root/work/cpu/final/results")
p=subprocess.Popen([sys.executable,"app.py"],cwd="/root/work/cpu/final/dashboard",env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(4)
out="/root/work/cpu/figs/"
try:
  with sync_playwright() as pw:
    b=pw.chromium.launch()
    pg=b.new_page(viewport={"width":1600,"height":1000}, device_scale_factor=1)
    errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://127.0.0.1:5000/"); pg.wait_for_timeout(3000)
    pg.screenshot(path=out+"fig-5-1.png", clip={"x":0,"y":0,"width":1600,"height":595})
    pg.set_viewport_size({"width":1360,"height":1000})
    pg.goto("http://127.0.0.1:5000/sensitivity"); pg.wait_for_timeout(3000)
    card=pg.locator(".card", has=pg.locator(".card-title", has_text="Rank order: smallest network measured vs largest")).first
    card.screenshot(path=out+"fig-5-2.png")
    pg.goto("http://127.0.0.1:5000/provenance"); pg.wait_for_timeout(3000)
    c1=pg.locator(".card", has=pg.locator(".card-title", has_text="Measured rate against the reference rate")).first
    c2=pg.locator(".card", has=pg.locator(".card-title", has_text="Pass / fail composition")).first
    b1=c1.bounding_box(); b2=c2.bounding_box()
    x0=min(b1["x"],b2["x"]); y0=min(b1["y"],b2["y"]); x1=max(b1["x"]+b1["width"],b2["x"]+b2["width"]); y1=max(b1["y"]+b1["height"],b2["y"]+b2["height"])
    pg.screenshot(path=out+"fig-5-3.png", clip={"x":x0,"y":y0,"width":x1-x0,"height":y1-y0}, full_page=True)
    print("errors:",errs)
    b.close()
finally:
    p.terminate()
