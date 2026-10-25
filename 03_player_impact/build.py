"""Project 3 - Rotation Lab (interactive): who played, with whom, and how it went.

Writes docs/rotation-lab/index.html:
  * rotation heatmap: minutes for every player in every game (starts, injuries, DNPs)
  * chemistry network from 5-man lineup data (pair minutes + plus-minus per 40)
  * usage vs true shooting for the whole league, Tempo highlighted
  * best and worst five-player lineups
"""
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

# let this file import lab.py and common.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
from common import load

TOR = 131935  # ESPN team id for the Tempo

# player box scores for every team in 2026
pb = load("player_box", 2026)
# make sure these columns are numbers, not text
for c in ["minutes", "points", "rebounds", "assists", "field_goals_attempted", "free_throws_attempted",
          "turnovers", "field_goals_made"]:
    pb[c] = pd.to_numeric(pb[c], errors="coerce")
# plus-minus comes in as text like "+5", so strip the plus sign first
pb["plus_minus"] = pd.to_numeric(pb.plus_minus.astype(str).str.lstrip("+"), errors="coerce")
pb["game_date"] = pd.to_datetime(pb.game_date)

# --- rotation heatmap ------------------------------------------------------------
tor = pb[pb.team_id == TOR].copy()
# one row per Tempo game in date order, numbered 1 to 44
games = (tor.drop_duplicates("game_id").sort_values("game_date")
         [["game_id", "game_date", "opponent_team_abbreviation", "home_away", "team_score", "opponent_team_score"]])
games["n"] = range(1, len(games) + 1)
game_list = [{"n": int(g.n), "date": g.game_date.strftime("%b %-d"), "opp": g.opponent_team_abbreviation,
              "home": g.home_away == "home", "pf": int(g.team_score), "pa": int(g.opponent_team_score)}
             for g in games.itertuples()]
gidx = dict(zip(games.game_id, games.n - 1))  # game id -> column number in the grid

# every player who played at least one minute, most minutes first (that's the row order)
roster = tor.groupby("athlete_display_name").minutes.sum().sort_values(ascending=False)
roster = roster[roster > 0]
grid = {}
for name in roster.index:
    # one cell per game. None = not on the roster that game
    rows = [None] * len(games)
    for r in tor[tor.athlete_display_name == name].itertuples():
        i = gidx[r.game_id]
        if r.minutes and r.minutes > 0:
            # played: [minutes, started (1/0), points, plus-minus]
            rows[i] = [int(r.minutes), int(bool(r.starter)), int(r.points), int(r.plus_minus or 0)]
        elif str(r.did_not_play) == "True":
            # did not play: save the reason (injury, coach's decision...)
            rows[i] = ["dnp", str(r.reason or "").title()]
    grid[name] = rows

# --- season lines ------------------------------------------------------------------------
# team totals per game, needed for the usage calculation
tb = load("team_box", 2026)[["game_id", "team_id", "field_goals_attempted", "free_throws_attempted", "total_turnovers"]]
tb.columns = ["game_id", "team_id", "tm_fga", "tm_fta", "tm_tov"]
for c in ["tm_fga", "tm_fta", "tm_tov"]:
    tb[c] = pd.to_numeric(tb[c], errors="coerce")
# only players who actually played, with their team's totals attached
on = pb[pb.minutes.fillna(0) > 0].merge(tb, on=["game_id", "team_id"])
# total minutes the team played that game (200 in regulation = 5 players x 40 min)
on = on.merge(on.groupby(["game_id", "team_id"]).minutes.sum().rename("tm_min"), on=["game_id", "team_id"])
# "plays" a player used: shots + free throw trips + turnovers
on["plays"] = on.field_goals_attempted + 0.44 * on.free_throws_attempted + on.turnovers
# estimate of the team's plays while she was on the court (team plays x her share of the game)
on["tm_plays_on"] = (on.tm_fga + 0.44 * on.tm_fta + on.tm_tov) * on.minutes / (on.tm_min / 5)
# add up the season for every player in the league
agg = on.groupby(["athlete_display_name", "team_abbreviation"]).agg(
    gp=("game_id", "nunique"), gs=("starter", "sum"), mins=("minutes", "sum"), pts=("points", "sum"),
    reb=("rebounds", "sum"), ast=("assists", "sum"), fga=("field_goals_attempted", "sum"),
    fta=("free_throws_attempted", "sum"), plays=("plays", "sum"), on_plays=("tm_plays_on", "sum"),
    pm=("plus_minus", "sum")).reset_index()
agg["usg"] = agg.plays / agg.on_plays                       # usage rate
agg["ts"] = agg.pts / (2 * (agg.fga + 0.44 * agg.fta))      # true shooting %
qual = agg[agg.mins >= 300]  # only players with real minutes go on the scatter plot
league = [{"n": r.athlete_display_name, "t": r.team_abbreviation, "min": int(r.mins), "usg": round(r.usg, 4),
           "ts": round(r.ts, 4), "ppg": round(r.pts / r.gp, 1)} for r in qual.itertuples()]
# league-wide true shooting (the dashed line on the chart)
lg_ts = agg.pts.sum() / (2 * (agg.fga.sum() + 0.44 * agg.fta.sum()))
# per-game numbers for every Tempo player (used in tooltips and the network side panel)
players = {}
for r in agg[agg.team_abbreviation == "TOR"].itertuples():
    players[r.athlete_display_name] = {
        "gp": int(r.gp), "gs": int(r.gs), "mpg": round(r.mins / r.gp, 1), "ppg": round(r.pts / r.gp, 1),
        "rpg": round(r.reb / r.gp, 1), "apg": round(r.ast / r.gp, 1), "ts": round(r.ts, 3), "usg": round(r.usg, 3),
        "pm40": round(40 * r.pm / r.mins, 1)}

# --- lineups & pairs --------------------------------------------------------------------
lu = load("lineups", 2026)
# WNBA Stats gives two tables per lineup: "Base" (minutes, +/-) and "Advanced" (ratings)
base = lu[(lu.team_abbreviation == "TOR") & (lu.measure_type == "Base")]
adv = lu[(lu.team_abbreviation == "TOR") & (lu.measure_type == "Advanced")][["group_id", "off_rating", "def_rating", "net_rating"]]
lines = base[["group_id", "group_name", "min", "plus_minus", "gp"]].merge(adv, on="group_id")
# lineup names look like "M. Mabrey", so make a lookup back to full names
short = {n.split(" ")[0][0] + ". " + " ".join(n.split(" ")[1:]): n for n in roster.index}
rows, edges = [], {}
for r in lines.itertuples():
    names = [short.get(n.strip(), n.strip()) for n in r.group_name.split(" - ")]
    rows.append({"p": names, "min": round(float(r.min), 1), "pm": int(r.plus_minus), "gp": int(r.gp),
                 "ortg": float(r.off_rating), "drtg": float(r.def_rating), "net": float(r.net_rating)})
    # every five-player lineup has 10 pairs in it. Add this lineup's minutes and +/- to each pair
    for a, b in combinations(sorted(names), 2):
        e = edges.setdefault((a, b), [0.0, 0])
        e[0] += float(r.min)
        e[1] += int(r.plus_minus)
# pairs with 20+ minutes together, with plus-minus per 40 minutes
pair_list = [{"a": a, "b": b, "min": round(m, 1), "pm40": round(40 * pm / m, 1)} for (a, b), (m, pm) in edges.items() if m >= 20]
# lineups with 25+ minutes, best net rating first
lineups = sorted([l for l in rows if l["min"] >= 25], key=lambda l: -l["net"])

# everything the page needs
data = {"games": game_list, "roster": list(roster.index), "grid": grid, "players": players, "league": league,
        "lg_ts": round(lg_ts, 4), "pairs": pair_list, "lineups": lineups}
# count different starting fives: for each game, the sorted set of players who started
starts = {tuple(sorted(n for n in roster.index if grid[n][i] and grid[n][i][0] != "dnp" and grid[n][i][1] == 1))
          for i in range(len(games))}
lab.summary("rotation-lab", {"players": len(roster), "lineups": len(starts),
                             "best": lineups[0]["net"] if lineups else None})
lab.write_page("rotation-lab", "Rotation Lab", "Toronto Tempo 2026 rotation: minutes in every game, player chemistry network, usage vs efficiency, lineups.",
               Path(__file__).parent / "page.html", data)
# print numbers to check in the terminal
print(len(lineups), "lineups 25+ min;", len(pair_list), "pairs")
print(pd.DataFrame(players).T.sort_values("mpg", ascending=False).head(12).to_string())
print([(l["p"], l["min"], l["net"]) for l in lineups[:3]], [(l["p"], l["min"], l["net"]) for l in lineups[-3:]])
