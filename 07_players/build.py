"""Project 7 - Players: a trading card for every Tempo player of 2026.

Writes docs/players/index.html. Each card has the player's photo, number and position, a label for
something she led the team in, per-game numbers, true shooting and a mini hex chart of her shots.
Also copies the README pictures into docs/assets/art/ so each page can show the one that belongs to it.
"""
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

# let this file import lab.py and common.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
from common import load

ROOT = Path(__file__).resolve().parents[1]
TOR = 131935

# --- copy the README pictures into the site ---------------------------------------------------------
ART, OUT = ROOT / "readme_art" / "out", ROOT / "docs" / "assets" / "art"
OUT.mkdir(parents=True, exist_ok=True)
for f in ART.glob("*"):
    if f.suffix in (".png", ".gif") and f.name != "social-preview.png":
        shutil.copy2(f, OUT / f.name)
# the social card used for link previews of every page (see lab.head), shrunk to the 1280 x 640
# size GitHub and most sites expect (the art is drawn at 2x)
Image.open(ART / "social-preview.png").resize((1280, 640), Image.LANCZOS).save(ROOT / "docs" / "assets" / "social.png", optimize=True)

# --- season numbers for every Tempo player ------------------------------------------------------------
pb = load("player_box", 2026)
for c in ["minutes", "points", "rebounds", "assists", "steals", "blocks", "field_goals_attempted", "free_throws_attempted",
          "three_point_field_goals_made"]:
    pb[c] = pd.to_numeric(pb[c], errors="coerce").fillna(0)
tor = pb[(pb.team_id.astype(int) == TOR) & (pb.minutes > 0)]
season = tor.groupby("athlete_display_name").agg(
    gp=("game_id", "nunique"), mins=("minutes", "sum"), pts=("points", "sum"), reb=("rebounds", "sum"), ast=("assists", "sum"),
    stl=("steals", "sum"), blk=("blocks", "sum"), fga=("field_goals_attempted", "sum"), fta=("free_throws_attempted", "sum"),
    tpm=("three_point_field_goals_made", "sum"), jersey=("athlete_jersey", "first"), pos=("athlete_position_abbreviation", "first"),
    img=("athlete_headshot_href", "first"))
season["ts"] = season.pts / (2 * (season.fga + 0.44 * season.fta))  # true shooting %
season = season.sort_values("mins", ascending=False)

# the label on each card: something she led the team in (players with 10+ games, and 100+ shots for TS%)
LEADS = [("pts", "Top scorer", 10), ("reb", "Top rebounder", 10), ("ast", "Assists leader", 10), ("mins", "Minutes leader", 10),
         ("blk", "Blocks leader", 10), ("stl", "Steals leader", 10), ("tpm", "Most threes", 10), ("ts", "Most efficient (TS%)", 10)]
tags = {}
for col, label, min_gp in LEADS:
    pool = season[(season.gp >= min_gp) & ((season.fga >= 100) if col == "ts" else True)]
    per_game = pool[col] if col in ("ts",) else pool[col]  # totals for counting stats, rate for TS%
    tags.setdefault(per_game.idxmax(), []).append(label)
games_all = int(tor.game_id.nunique())
for name, r in season.iterrows():
    if name not in tags:
        # no team lead: say how much she played instead
        tags[name] = ([f"Played all {games_all} games"] if r.gp == games_all else [f"Played {int(r.gp)} of {games_all} games"] if r.gp >= 35
                      else ["Rotation player"] if r.gp >= 10 and r.mins / r.gp >= 15 else ["Reserve"])

# --- mini hex shot chart data: every Tempo field-goal attempt with a location ---------------------------
p = load("pbp", 2026)
shots = p[p.shooting_play.astype(bool) & ~p.type_text.str.contains("Free Throw") & (p.team_id == TOR)].copy()
shots = shots[(shots.coordinate_y_raw.astype(float) <= 28) & shots.coordinate_x_raw.astype(float).between(0, 50)]
R = 1.9  # hex radius in feet (same as the README cards)
w_, h_ = np.sqrt(3) * R, 1.5 * R
x, y = shots.coordinate_x_raw.astype(float), shots.coordinate_y_raw.astype(float)
row = np.round((y + 5) / h_).astype(int)
col = np.round((x - (row % 2) * w_ / 2) / w_).astype(int)
shots["hx"], shots["hy"] = (col * w_ + (row % 2) * w_ / 2).round(2), (row * h_ - 5).round(2)


def hexes(name):
    # [x, y, shots, makes] for each hex where she took a shot
    b = shots[shots.athlete_name_1 == name].groupby(["hx", "hy"]).agg(n=("scoring_play", "size"), m=("scoring_play", "sum")).reset_index()
    return [[r.hx, r.hy, int(r.n), int(r.m)] for r in b.itertuples()]


cards = [{"n": name, "jersey": str(r.jersey), "pos": r.pos if isinstance(r.pos, str) else "", "img": r.img if isinstance(r.img, str) else "",
          "tags": tags[name], "gp": int(r.gp), "mpg": round(r.mins / r.gp, 1), "ppg": round(r.pts / r.gp, 1), "rpg": round(r.reb / r.gp, 1),
          "apg": round(r.ast / r.gp, 1), "ts": None if r.fga + r.fta == 0 else round(float(r.ts), 3), "hex": hexes(name),
          "shots": int((shots.athlete_name_1 == name).sum())} for name, r in season.iterrows()]

lab.summary("players", {"players": len(cards)})
lab.write_page("players", "Players", "A trading card for every Toronto Tempo player of 2026: photo, numbers and a mini shot chart.",
               Path(__file__).parent / "page.html", {"cards": cards, "hex_r": R})
