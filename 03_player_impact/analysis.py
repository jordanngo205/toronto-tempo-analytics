"""Project 3 - Player Impact.

1. Usage vs true shooting: who carried the Tempo offense, and did they do it efficiently?
2. Pair chemistry: net rating of every two-player Tempo combo, built from 5-man lineup data.
"""
import sys
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import INK, LEAGUE, MUTED, TEMPO, load, save, style

OUT = Path(__file__).parent
MIN_MINUTES = 300

# --- usage & true shooting from box scores -----------------------------------
pb = load("player_box", 2026)
pb = pb[pb.minutes.fillna(0) > 0].copy()
pb["plus_minus"] = pd.to_numeric(pb.plus_minus.astype(str).str.lstrip("+"), errors="coerce")
tb = load("team_box", 2026)[["game_id", "team_id", "field_goals_attempted", "free_throws_attempted", "total_turnovers"]]
tb.columns = ["game_id", "team_id", "tm_fga", "tm_fta", "tm_tov"]
team_min = pb.groupby(["game_id", "team_id"]).minutes.sum().rename("tm_min")
pb = pb.merge(tb, on=["game_id", "team_id"]).merge(team_min, on=["game_id", "team_id"])
pb["plays"] = pb.field_goals_attempted + 0.44 * pb.free_throws_attempted + pb.turnovers
# share of team plays while on court: player plays / (team plays * minutes share)
pb["tm_plays_on"] = (pb.tm_fga + 0.44 * pb.tm_fta + pb.tm_tov) * pb.minutes / (pb.tm_min / 5)

agg = pb.groupby(["athlete_display_name", "team_abbreviation"]).agg(
    gp=("game_id", "nunique"), mins=("minutes", "sum"), pts=("points", "sum"),
    fga=("field_goals_attempted", "sum"), fta=("free_throws_attempted", "sum"),
    plays=("plays", "sum"), tm_plays_on=("tm_plays_on", "sum"), pm=("plus_minus", "sum"),
).reset_index()
agg["usg"] = agg.plays / agg.tm_plays_on
agg["ts"] = agg.pts / (2 * (agg.fga + 0.44 * agg.fta))
agg["pts40"] = 40 * agg.pts / agg.mins
agg["pm40"] = 40 * agg.pm / agg.mins
qual = agg[agg.mins >= MIN_MINUTES]

impact = load("impact", 2026)[["player_name", "team_abbreviation", "rapm", "o_rapm", "d_rapm", "war"]]
tor = qual[qual.team_abbreviation == "TOR"].merge(
    impact, left_on=["athlete_display_name", "team_abbreviation"],
    right_on=["player_name", "team_abbreviation"], how="left").drop(columns="player_name")
tor.sort_values("mins", ascending=False).to_csv(OUT / "tempo_players.csv", index=False)
print(tor[["athlete_display_name", "mins", "usg", "ts", "pts40", "pm40", "rapm"]]
      .sort_values("mins", ascending=False).round(3).to_string(index=False))

lg_ts = agg.pts.sum() / (2 * (agg.fga.sum() + 0.44 * agg.fta.sum()))
fig, ax = plt.subplots(figsize=(9, 6))
others = qual[qual.team_abbreviation != "TOR"]
ax.scatter(others.usg, others.ts, s=22, color=LEAGUE, alpha=0.45, lw=0, label=f"Rest of WNBA ({MIN_MINUTES}+ min)")
ax.scatter(tor.usg, tor.ts, s=tor.mins / 6, color=TEMPO, edgecolor="white", lw=2, zorder=3, label="Tempo (size = minutes)")
for _, r in tor.iterrows():
    below = r.athlete_display_name == "Laura Juskaite"  # sits on top of Rice
    ax.annotate(r.athlete_display_name.split()[-1], (r.usg, r.ts), xytext=(7, -12 if below else 4),
                textcoords="offset points", fontsize=9, color=INK)
ax.axhline(lg_ts, color=MUTED, lw=1, ls="--")
ax.text(qual.usg.max(), lg_ts + 0.004, "league TS%", ha="right", fontsize=8, color=MUTED)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.set_xlabel("Usage rate (share of team plays used while on court)", color=MUTED, fontsize=9)
ax.set_ylabel("True shooting %", color=MUTED, fontsize=9)
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
style(ax, "Who carried the Tempo offense, and at what cost", "Usage vs efficiency, 2026 regular season")
save(fig, OUT / "usage_vs_ts.png")

# --- pair chemistry from 5-man lineups ---------------------------------------
lu = load("lineups", 2026)
lu = lu[(lu.team_abbreviation == "TOR") & (lu.measure_type == "Base")]
rows = []
for _, r in lu.iterrows():
    names = [n.strip() for n in r.group_name.split(" - ")]
    for a, b in combinations(sorted(names), 2):
        rows.append((a, b, r["min"], r.plus_minus))
pairs = pd.DataFrame(rows, columns=["a", "b", "min", "pm"]).groupby(["a", "b"]).sum().reset_index()
pairs["pm40"] = 40 * pairs.pm / pairs["min"]

core = (pd.concat([pairs.groupby("a")["min"].sum(), pairs.groupby("b")["min"].sum()])
        .groupby(level=0).sum().sort_values(ascending=False).head(10).index)
mat = pd.DataFrame(np.nan, index=core, columns=core)
mins = mat.copy()
for _, r in pairs[pairs.a.isin(core) & pairs.b.isin(core)].iterrows():
    if r["min"] >= 30:
        mat.loc[r.a, r.b] = mat.loc[r.b, r.a] = r.pm40
    mins.loc[r.a, r.b] = mins.loc[r.b, r.a] = r["min"]
mat.to_csv(OUT / "pair_pm40.csv")

cmap = LinearSegmentedColormap.from_list("tempo_div", ["#B8325A", "#F1F2F4", "#2F5DA8"])
lim = np.nanmax(np.abs(mat.to_numpy()))
fig, ax = plt.subplots(figsize=(8.5, 7.5))
rows_, cols_ = core[1:], core[:-1]  # lower triangle without the empty first row / last column
grid = mat.loc[rows_, cols_].to_numpy()
tri = np.triu(np.ones_like(grid, dtype=bool), k=1)
im = ax.imshow(np.ma.array(grid, mask=tri | np.isnan(grid)), cmap=cmap, norm=TwoSlopeNorm(0, -lim, lim))
for i, a in enumerate(rows_):
    for j, b in enumerate(cols_):
        v, m = mat.loc[a, b], mins.loc[a, b]
        if j <= i and not np.isnan(v):
            ax.text(j, i, f"{v:+.0f}\n{m:.0f}m", ha="center", va="center", fontsize=7.5, color=INK)
ax.set_xticks(range(len(cols_)), cols_, rotation=45, ha="right", fontsize=9, color=INK)
ax.set_yticks(range(len(rows_)), rows_, fontsize=9, color=INK)
ax.tick_params(length=0)
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
cb.set_label("Plus-minus per 40 minutes together", color=MUTED, fontsize=9)
cb.ax.tick_params(colors=MUTED, labelsize=8)
ax.set_title("Tempo pair chemistry", loc="left", fontsize=13, fontweight="bold", color=INK, pad=24)
ax.text(0, 1.02, "+/- per 40 when both share the floor (pairs with 30+ min; from tracked 5-man lineups)",
        transform=ax.transAxes, fontsize=9, color=MUTED)
save(fig, OUT / "pair_chemistry.png")
