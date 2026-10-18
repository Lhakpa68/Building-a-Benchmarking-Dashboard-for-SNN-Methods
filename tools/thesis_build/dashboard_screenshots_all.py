"""Capture the dashboard pages used as thesis figures and as docs/dashboard_screenshots/.

    python3 dashboard_screenshots_all.py <project-root> <output-dir>

<project-root> is the folder holding dashboard/ and results/. Needs playwright
(`pip install playwright && playwright install chromium`).
"""
import subprocess, time, sys, os
from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
OUT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else 'shots') + os.sep
os.makedirs(OUT, exist_ok=True)
env = dict(os.environ, SNN_RESULTS_DIR=os.path.join(ROOT, "results"))
srv = subprocess.Popen([sys.executable, "app.py"], cwd=os.path.join(ROOT, "dashboard"),
                       env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(5)
BASE = "http://127.0.0.1:5000"
PAGES = [("01_dashboard_home", "/"), ("02_all_simulators", "/all-simulators"),
         ("03_inference", "/inference"), ("04_scalability", "/scalability"),
         ("05_memory", "/memory"), ("06_training", "/training"),
         ("07_sensitivity", "/sensitivity"), ("08_provenance", "/provenance"),
         ("09_about_baselines", "/about")]
errs = []
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=1)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        for name, route in PAGES:
            pg.goto(BASE + route); pg.wait_for_timeout(3000)
            pg.screenshot(path=OUT + name + ".png", full_page=True)
        pg.goto(BASE + "/inference"); pg.wait_for_timeout(2500)
        d = pg.locator("details").first
        if d.count():
            d.click(); pg.wait_for_timeout(1500)
        pg.screenshot(path=OUT + "10_inference_detail_table_expanded.png", full_page=True)

        # thesis figures 5.1 - 5.3
        pg.set_viewport_size({"width": 1600, "height": 1000})
        pg.goto(BASE + "/"); pg.wait_for_timeout(3500)
        pg.screenshot(path=OUT + "fig-5-1.png", clip={"x": 0, "y": 0, "width": 1600, "height": 595})
        pg.set_viewport_size({"width": 1360, "height": 1000})
        pg.goto(BASE + "/sensitivity"); pg.wait_for_timeout(3500)
        pg.locator(".card", has=pg.locator(".card-title",
            has_text="Rank order: smallest network measured vs largest")).first.screenshot(
            path=OUT + "fig-5-2.png")
        pg.goto(BASE + "/provenance"); pg.wait_for_timeout(3500)
        c1 = pg.locator(".card", has=pg.locator(".card-title", has_text="Measured rate against the reference rate")).first
        c2 = pg.locator(".card", has=pg.locator(".card-title", has_text="Pass / fail composition")).first
        b1, b2 = c1.bounding_box(), c2.bounding_box()
        pg.screenshot(path=OUT + "fig-5-3.png", full_page=True, clip={
            "x": min(b1["x"], b2["x"]), "y": min(b1["y"], b2["y"]),
            "width": max(b1["x"] + b1["width"], b2["x"] + b2["width"]) - min(b1["x"], b2["x"]),
            "height": max(b1["y"] + b1["height"], b2["y"] + b2["height"]) - min(b1["y"], b2["y"])})
        b.close()
finally:
    srv.terminate()
print("page errors:", errs)
