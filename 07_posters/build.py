"""Project 7 - Posters: every README graphic on the live site too.

Copies the pictures that readme_art/make_art.py made into docs/assets/art/, then writes
docs/posters/index.html with each poster, a short caption and a link to the page where it's interactive.
Run readme_art/make_art.py first if the art changed.
"""
import shutil
import sys
from pathlib import Path

# let this file import lab.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART, OUT = ROOT / "readme_art" / "out", ROOT / "docs" / "assets" / "art"
OUT.mkdir(parents=True, exist_ok=True)

# [file, title, caption, link to the interactive page, link text, "wide" = full width]
POSTERS = [
    ["by-the-numbers.png", "By the numbers", "The season in its headline numbers.", "expansion-class/", "Expansion Class", True],
    ["constellation.png", "The shot constellation", "Every field-goal attempt from a Tempo game. Glowing dots are makes; Toronto attacks the right basket, opponents the left.",
     "shot-lab/", "Every shot in Shot Lab", True],
    ["elo-race.gif", "The Elo race", "Valkyries '25, Tempo '26 and Fire '26, game by game.", "expansion-class/", "The Elo chart", True],
    ["season-circle.png", "The season in a circle", "Every game around a circle. Bars point toward the winner, longer = bigger margin.", "#season", "Clickable version on the home page", False],
    ["rotation-ring.png", "The rotation ring", "Each ring is a player, each slice a game. Brighter = more minutes, ✕ = injured, blue rings = wins.", "rotation-lab/", "Rotation Lab", False],
    ["ridgeline.png", "Unknown Pressures", "Every game's margin from tip-off to the buzzer, stacked like the Joy Division cover. Pink lines are wins.", "game-flow/", "Game Flow", False],
    ["big-board.png", "The 2027 big board", "Toronto's top 10 college seniors at the default setting.", "draft-lab/", "Draft Lab", False],
    ["player-cards.png", "The card set", "Trading cards with each player's own shot chart: hex size = where she shoots, darker = more makes.", "shot-lab/", "Shot Lab", True],
    ["shot-fans.png", "Who should take which shots", "Petal length = how often she shoots from there; colour = points per shot vs the WNBA from the same spot.",
     "shot-lab/", "Shot Lab", True],
]

# the social card used for link previews of every page (see lab.head), shrunk to the 1280 x 640
# size GitHub and most sites expect (the art is drawn at 2x)
Image.open(ART / "social-preview.png").resize((1280, 640), Image.LANCZOS).save(ROOT / "docs" / "assets" / "social.png", optimize=True)
# copy every poster (and the banner for the top of the page)
for name in ["banner.png"] + [p[0] for p in POSTERS]:
    shutil.copy2(ART / name, OUT / name)
    print("copied", name)

lab.write_page("posters", "Posters", "Every Tempo Lab poster: the season circle, rotation ring, shot constellation, Elo race and more.",
               Path(__file__).parent / "page.html", {"posters": POSTERS})
