"""Project 1 - The Expansion Blueprint.

Golden State went 23-21 and made the playoffs in their 2025 expansion year.
Toronto went 11-33 in 2026. Where exactly is the gap? Rank both expansion
teams within their own season on ratings and the Four Factors, then compare
how each season trended.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import INK, LEAGUE, MUTED, TEMPO, VALKYRIES as ACCENT, save, style, team_games

OUT = Path(__file__).parent

FACTORS = [  # (column, label, higher_is_better)
    ("ortg", "Offensive rating", True),
    ("drtg", "Defensive rating", False),
    ("efg", "eFG%", True),
    ("tov", "Turnover %", False),
    ("orb", "Off. rebound %", True),
    ("ftr", "FT rate", True),
    ("opp_efg", "Opp eFG%", False),
    ("opp_tov", "Opp turnover %", True),
    ("drb", "Def. rebound %", True),
    ("opp_ftr", "Opp FT rate", False),
]


def season_table(season):
    g = team_games(season)
    s = g.groupby("team_abbreviation").sum(numeric_only=True)
    s = s[g.groupby("team_abbreviation").size() >= 30]  # drops All-Star teams
    out = pd.DataFrame(index=s.index)
    out["gp"] = g.groupby("team_abbreviation").size()
    out["w"] = g.groupby("team_abbreviation").team_winner.sum()
    out["ortg"] = 100 * s.team_score / s.poss
    out["drtg"] = 100 * s.opponent_team_score / s.opp_poss
    out["net"] = out.ortg - out.drtg
    out["efg"] = (s.field_goals_made + 0.5 * s.three_point_field_goals_made) / s.field_goals_attempted
    out["tov"] = s.total_turnovers / s.poss
    out["orb"] = s.offensive_rebounds / (s.offensive_rebounds + s.opp_defensive_rebounds)
    out["ftr"] = s.free_throws_made / s.field_goals_attempted
    out["opp_efg"] = (s.opp_field_goals_made + 0.5 * s.opp_three_point_field_goals_made) / s.opp_field_goals_attempted
    out["opp_tov"] = s.opp_total_turnovers / s.opp_poss
    out["drb"] = s.defensive_rebounds / (s.defensive_rebounds + s.opp_offensive_rebounds)
    out["opp_ftr"] = s.opp_free_throws_made / s.opp_field_goals_attempted
    for col, _, hib in FACTORS:
        out[f"{col}_rank"] = out[col].rank(ascending=not hib).astype(int)
    return out.dropna(subset=["gp"]), g


tor, g26 = season_table(2026)
gsv, g25 = season_table(2025)
cmp = pd.DataFrame({"TOR 2026": tor.loc["TOR"], "GS 2025": gsv.loc["GS"]})
cmp.to_csv(OUT / "comparison.csv")
print(cmp.round(3).to_string())

# --- Chart 1: league rank on every factor -------------------------------------
fig, ax = plt.subplots(figsize=(8, 6.2))
n26, n25 = len(tor), len(gsv)
for i, (col, label, _) in enumerate(FACTORS):
    r_tor, r_gs = tor.loc["TOR", f"{col}_rank"], gsv.loc["GS", f"{col}_rank"]
    y = len(FACTORS) - 1 - i
    ax.plot([r_gs, r_tor], [y, y], color="#D0D4D9", lw=2, zorder=1)
    dy = 0.13 if r_tor == r_gs else 0  # split tied ranks so both dots show
    ax.scatter(r_gs, y - dy, s=90, color=ACCENT, zorder=2, edgecolor="white", lw=2)
    ax.scatter(r_tor, y + dy, s=90, color=TEMPO, zorder=3, edgecolor="white", lw=2)
    ax.text(n26 + 0.9, y, f"{r_tor:>2} / {r_gs:>2}", va="center", fontsize=9, color=INK)
ax.axhline(7.5, color="#ECEEF0", lw=1)
ax.text(n26 + 0.9, len(FACTORS) - 0.3, "TOR / GS", fontsize=8, color=MUTED)
ax.set_yticks(range(len(FACTORS)))
ax.set_yticklabels([f[1] for f in FACTORS][::-1], fontsize=10, color=INK)
ax.set_xlim(0.5, n26 + 0.5)
ax.set_xticks([1, 5, 10, n26])
ax.set_xlabel("League rank (1 = best)", color=MUTED, fontsize=9)
ax.grid(axis="x", color="#ECEEF0")
ax.grid(axis="y", visible=False)
style(ax, "Where the Tempo trail the Valkyries' expansion blueprint",
      f"League rank within own season · Tempo 2026 went {int(tor.loc['TOR','w'])}-{int(tor.loc['TOR','gp']-tor.loc['TOR','w'])}, "
      f"Valkyries 2025 went {int(gsv.loc['GS','w'])}-{int(gsv.loc['GS','gp']-gsv.loc['GS','w'])}")
leg = [plt.Line2D([], [], marker="o", ls="", color=TEMPO, ms=8, label="Tempo 2026"),
       plt.Line2D([], [], marker="o", ls="", color=ACCENT, ms=8, label="Valkyries 2025")]
ax.legend(handles=leg, loc="lower right", frameon=False, fontsize=9)
save(fig, OUT / "factor_ranks.png")

# --- Chart 2: rolling net rating by game number ------------------------------
def rolling_net(g, team, window=10):
    d = g[g.team_abbreviation == team].copy().reset_index(drop=True)
    pts, opp = d.team_score.rolling(window).sum(), d.opponent_team_score.rolling(window).sum()
    poss, opp_poss = d.poss.rolling(window).sum(), d.opp_poss.rolling(window).sum()
    d["net"] = 100 * pts / poss - 100 * opp / opp_poss
    d["game_no"] = d.index + 1
    return d

fig, ax = plt.subplots(figsize=(9, 4.6))
for team, g, color, label in [("GS", g25, ACCENT, "Valkyries 2025"), ("TOR", g26, TEMPO, "Tempo 2026")]:
    d = rolling_net(g, team)
    ax.plot(d.game_no, d.net, color=color, lw=2)
    last = d.dropna(subset=["net"]).iloc[-1]
    ax.text(last.game_no + 0.6, last.net, label, color=INK, fontsize=9, va="center")
    ax.scatter(last.game_no, last.net, color=color, s=30, zorder=3)
ax.axhline(0, color=MUTED, lw=1)
ax.set_xlabel("Game number", color=MUTED, fontsize=9)
ax.set_ylabel("Net rating, rolling 10 games", color=MUTED, fontsize=9)
ax.set_xlim(9, 49)
style(ax, "Season arc: did the Tempo grow into the league?", "Points per 100 possessions minus points allowed per 100, trailing 10 games")
save(fig, OUT / "rolling_net.png")
