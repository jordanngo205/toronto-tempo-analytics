"""Rebuild every page of the GitHub Pages site (docs/) and, with --shots, the screenshots used by the hub and README.

    .venv/bin/python build_site.py           # data + pages
    .venv/bin/python build_site.py --shots   # also refresh docs/assets/shots/*.png (needs Google Chrome)
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

import lab

ROOT = Path(__file__).parent
PY = sys.executable
BUILDS = ["01_expansion_class/build.py", "02_shot_diet/build.py", "03_player_impact/build.py",
          "04_close_games/build.py", "05_game_recap/build.py"]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SHOTS = ROOT / "docs" / "assets" / "shots"


def shoot(url, out, w=1280, h=900, crop=None):
    tmp = out.with_suffix(".full.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}",
                    "--virtual-time-budget=6000", "--force-device-scale-factor=2", f"--screenshot={tmp}", url],
                   capture_output=True, check=False)
    im = Image.open(tmp)
    if crop:
        im = im.crop(tuple(v * 2 for v in crop))
    im.thumbnail((1600, 1600))
    im.save(out, optimize=True)
    tmp.unlink()
    print("shot", out.relative_to(ROOT))


if __name__ == "__main__":
    for b in BUILDS:
        subprocess.run([PY, str(ROOT / b)], check=True, capture_output=True)
        print("built", b)
    summary = json.loads((ROOT / "docs" / "assets" / "summary.json").read_text())
    lab.write_home(ROOT / "home.html", summary)
    if "--shots" in sys.argv:
        SHOTS.mkdir(parents=True, exist_ok=True)
        base = (ROOT / "docs").as_uri()
        for slug, crop_y in [("expansion-class", 60), ("shot-lab", 470), ("rotation-lab", 560), ("game-flow", 600), ("game-center", 60)]:
            shoot(f"{base}/{slug}/index.html", SHOTS / f"{slug}.png", h=1700, crop=(0, crop_y, 1280, crop_y + 1000))
        shoot(f"{base}/index.html", SHOTS / "home.png", h=1100, crop=(0, 0, 1280, 1000))
