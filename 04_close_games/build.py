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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow
import lab

p = flow.tempo_pbp()
meta, _ = flow.game_meta()
odds, pre_elo = flow.pregame_odds()

games, all_runs = [], []
grid_t = np.arange(0, 2401, 20)
for g in meta.itertuples():
    gp = p[p.game_id == g.game_id]
    steps = flow.margin_steps(gp)
    reg = gp[gp.t <= 2400]
    sampled = np.interp(grid_t, np.r_[0, reg.t.to_numpy(float)], np.r_[0, reg.m.to_numpy(float)])
    secs_lead = np.diff(np.r_[0, gp.t.to_numpy(float)])
    prev_m = np.r_[0, gp.m.to_numpy()[:-1]]
    rs = flow.runs(gp)
    for r in rs:
        all_runs.append({**r, "g": int(g.n)})
    q = gp.groupby("per").m.last()
    qm = (q - q.shift(fill_value=0)).astype(int).tolist()
    late = gp[(gp.t >= 2100)]
    games.append({
        "n": int(g.n), "id": int(g.game_id), "date": g.game_date.strftime("%b %-d"), "opp": g.opponent_team_abbreviation,
        "home": g.team_home_away == "home", "pf": int(g.team_score), "pa": int(g.opponent_team_score),
        "p": round(float(odds.get(g.game_id, np.nan)), 3), "elo": round(float(pre_elo.get(g.game_id, np.nan))),
        "ot": bool((gp.per > 4).any()), "q": qm,
        "lead": round(float(secs_lead[prev_m > 0].sum() / gp.t.max()), 3),
        "trail": round(float(secs_lead[prev_m < 0].sum() / gp.t.max()), 3),
        "max": int(gp.m.max()), "min": int(gp.m.min()),
        "clutch": bool((late.m.abs() <= 5).any()),
        "s": [int(v) for v in np.round(sampled)], "steps": steps,
    })

data = {"games": games, "runs": all_runs, "grid_step": 20}
lab.summary("game-flow", {"lead": float(np.mean([g["lead"] for g in games])), "runs_for": sum(r["team"] == "TOR" for r in all_runs),
                          "runs_against": sum(r["team"] == "OPP" for r in all_runs), "xwins": float(sum(g["p"] for g in games)),
                          "wins": sum(g["pf"] > g["pa"] for g in games)})
lab.write_page("game-flow", "Game Flow", "How every Toronto Tempo game of 2026 unfolded: the game grid, margin worms, scoring runs and Elo upsets.",
               Path(__file__).parent / "page.html", data)
import pandas as pd
gdf = pd.DataFrame(games)
print("avg lead share", gdf.lead.mean().round(3), "trail", gdf.trail.mean().round(3))
print("runs for/against", sum(r["team"] == "TOR" for r in all_runs), sum(r["team"] == "OPP" for r in all_runs))
print("upset wins (p<.35)", ((gdf.p < .35) & (gdf.pf > gdf.pa)).sum(), "losses as fav (p>.5)", ((gdf.p > .5) & (gdf.pf < gdf.pa)).sum(), "fav games", (gdf.p > .5).sum())
print("expected wins", gdf.p.sum().round(1))
print(gdf[["n", "opp", "p", "pf", "pa", "ot", "q"]].head(5).to_string())
