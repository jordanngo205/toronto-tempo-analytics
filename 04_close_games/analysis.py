"""Project 4 - Game Flow & Close Games.

When do the Tempo lose games? Quarter-by-quarter scoring margin, every game's
margin "worm", and record in clutch games (within 5 points, last 5 minutes).
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import INK, LEAGUE, MUTED, TEMPO, TEMPO_NAVY, load, save, style

OUT = Path(__file__).parent
TOR_ID = 131935

p = load("pbp", 2026)
p = p[(p.home_team_id == TOR_ID) | (p.away_team_id == TOR_ID)].copy()
home = p.home_team_id == TOR_ID
p["margin"] = np.where(home, p.home_score - p.away_score, p.away_score - p.home_score)
p["elapsed"] = 40 * 60 - p.end_game_seconds_remaining  # OT runs past 2400
p = p.sort_values(["game_id", "game_play_number"])
p["opp"] = np.where(home, p.away_team_abbrev, p.home_team_abbrev)

final = p.groupby("game_id").agg(margin=("margin", "last"), opp=("opp", "first"), date=("game_date", "first"))

# quarter-by-quarter margin: margin at end of each period minus start
q = p.groupby(["game_id", "period"]).margin.last().unstack()
q_change = q.diff(axis=1)
q_change[1] = q[1]
by_q = q_change[[1, 2, 3, 4]].mean()

# clutch: any point in last 5 min of regulation (or OT) with margin within 5
late = p[(p.end_game_seconds_remaining <= 300)]
clutch_ids = late[late.margin.abs() <= 5].game_id.unique()
clutch = final.loc[clutch_ids]
summary = pd.DataFrame({
    "games": [len(final), len(clutch)],
    "wins": [(final.margin > 0).sum(), (clutch.margin > 0).sum()],
}, index=["all", "clutch"])
summary["losses"] = summary.games - summary.wins
lead_blown = p.groupby("game_id").margin.max()
blown = final[(final.margin < 0) & (lead_blown.reindex(final.index) >= 10)]
print(summary.to_string())
print("\nAvg margin by quarter:\n", by_q.round(2).to_string())
print(f"\nLosses after leading by 10+: {len(blown)}")
summary.to_csv(OUT / "clutch_summary.csv")

# --- Chart 1: quarter margins -------------------------------------------------
fig, ax = plt.subplots(figsize=(7.5, 4.4))
colors = [TEMPO_NAVY if v >= 0 else TEMPO for v in by_q]
bars = ax.bar(["Q1", "Q2", "Q3", "Q4"], by_q, color=colors, width=0.55, edgecolor="white", lw=2)
for b, v in zip(bars, by_q):
    ax.text(b.get_x() + b.get_width() / 2, v + (0.12 if v >= 0 else -0.12), f"{v:+.1f}",
            ha="center", va="bottom" if v >= 0 else "top", fontsize=10, color=INK)
ax.axhline(0, color=MUTED, lw=1)
ax.set_ylabel("Avg point margin in quarter", color=MUTED, fontsize=9)
style(ax, "Which quarter sinks the Tempo?", "Average Tempo point differential within each quarter, 2026 regular season")
save(fig, OUT / "quarter_margin.png")

# --- Chart 2: margin worms ----------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 5.2))
grid = np.arange(0, 2401, 30)
curves = []
for gid, g in p.groupby("game_id"):
    g = g[g.elapsed <= 2400]
    m = np.interp(grid, g.elapsed, g.margin)
    curves.append(m)
    ax.plot(grid / 60, m, color=TEMPO if final.loc[gid, "margin"] > 0 else LEAGUE, lw=0.8, alpha=0.5)
avg = np.mean(curves, axis=0)
ax.plot(grid / 60, avg, color=INK, lw=2.4)
ax.text(40.4, avg[-1], f"Average\n{avg[-1]:+.1f}", fontsize=9, color=INK, va="center")
ax.axhline(0, color=MUTED, lw=1)
for qx in (10, 20, 30):
    ax.axvline(qx, color="#ECEEF0", lw=1, zorder=0)
ax.set_xlim(0, 44)
ax.set_xticks([0, 10, 20, 30, 40], ["Tip", "Q2", "Half", "Q4", "End"])
ax.set_ylabel("Tempo point margin", color=MUTED, fontsize=9)
w, l = summary.loc["clutch", ["wins", "losses"]]
style(ax, "Every Tempo game, 2026",
      f"Score margin through regulation · blue = win, gray = loss · black = average · clutch record {w}-{l}")
save(fig, OUT / "margin_worms.png")
