"""Project 4 - Game Flow (interactive): how every Tempo game unfolded.

Writes docs/game-flow/index.html:
  * the game grid: margin over time for all 44 games as a heat strip, sortable
  * margin worm for any game against the season's spread
  * scoring runs (8-0 or better) for and against, by game minute
  * upsets and heartbreaks: pregame Elo win probability vs final margin
"""
import sys
from pathlib import Path

import numpy as np

# let this file import flow.py and lab.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow
import lab

# play-by-play for Tempo games (with time and margin columns), the game list, and pregame Elo odds
p = flow.tempo_pbp()
meta, _ = flow.game_meta()
odds, pre_elo = flow.pregame_odds()

games, all_runs = [], []
# for the game grid I sample the margin every 20 seconds of regulation (0, 20, 40 ... 2400)
grid_t = np.arange(0, 2401, 20)
for g in meta.itertuples():
    gp = p[p.game_id == g.game_id]  # plays from this game only
    steps = flow.margin_steps(gp)
    reg = gp[gp.t <= 2400]  # regulation only (no overtime) for the grid
    # np.interp reads the margin at each 20-second mark (starting from 0-0 at tip-off)
    sampled = np.interp(grid_t, np.r_[0, reg.t.to_numpy(float)], np.r_[0, reg.m.to_numpy(float)])
    # how many seconds passed between each play and the one before it
    secs_lead = np.diff(np.r_[0, gp.t.to_numpy(float)])
    # the margin during those seconds (the margin from the play before)
    prev_m = np.r_[0, gp.m.to_numpy()[:-1]]
    # scoring runs of 8+ in this game, tagged with the game number
    rs = flow.runs(gp)
    for r in rs:
        all_runs.append({**r, "g": int(g.n)})
    # margin within each quarter = margin at end of quarter minus margin at end of the quarter before
    q = gp.groupby("per").m.last()
    qm = (q - q.shift(fill_value=0)).astype(int).tolist()
    late = gp[(gp.t >= 2100)]  # last 5 minutes of regulation (2100 s = 35:00 into the game)
    games.append({
        "n": int(g.n), "id": int(g.game_id), "date": g.game_date.strftime("%b %-d"), "opp": g.opponent_team_abbreviation,
        "home": g.team_home_away == "home", "pf": int(g.team_score), "pa": int(g.opponent_team_score),
        # pregame win chance and Toronto's Elo going into the game
        "p": round(float(odds.get(g.game_id, np.nan)), 3), "elo": round(float(pre_elo.get(g.game_id, np.nan))),
        "ot": bool((gp.per > 4).any()), "q": qm,
        # share of the game Toronto spent leading / trailing (seconds where the margin was > 0 or < 0)
        "lead": round(float(secs_lead[prev_m > 0].sum() / gp.t.max()), 3),
        "trail": round(float(secs_lead[prev_m < 0].sum() / gp.t.max()), 3),
        "max": int(gp.m.max()), "min": int(gp.m.min()),  # biggest lead and biggest deficit
        "clutch": bool((late.m.abs() <= 5).any()),       # within 5 at some point in the last 5 min
        "s": [int(v) for v in np.round(sampled)], "steps": steps,
    })

data = {"games": games, "runs": all_runs, "grid_step": 20}
# headline numbers for the home page (expected wins = add up the pregame win chances)
lab.summary("game-flow", {"lead": float(np.mean([g["lead"] for g in games])), "runs_for": sum(r["team"] == "TOR" for r in all_runs),
                          "runs_against": sum(r["team"] == "OPP" for r in all_runs), "xwins": float(sum(g["p"] for g in games)),
                          "wins": sum(g["pf"] > g["pa"] for g in games)})
lab.write_page("game-flow", "Game Flow", "How every Toronto Tempo game of 2026 unfolded: the game grid, margin worms, scoring runs and Elo upsets.",
               Path(__file__).parent / "page.html", data)
# print numbers to check in the terminal
import pandas as pd
gdf = pd.DataFrame(games)
print("avg lead share", gdf.lead.mean().round(3), "trail", gdf.trail.mean().round(3))
print("runs for/against", sum(r["team"] == "TOR" for r in all_runs), sum(r["team"] == "OPP" for r in all_runs))
print("upset wins (p<.35)", ((gdf.p < .35) & (gdf.pf > gdf.pa)).sum(), "losses as fav (p>.5)", ((gdf.p > .5) & (gdf.pf < gdf.pa)).sum(), "fav games", (gdf.p > .5).sum())
print("expected wins", gdf.p.sum().round(1))
print(gdf[["n", "opp", "p", "pf", "pa", "ot", "q"]].head(5).to_string())
