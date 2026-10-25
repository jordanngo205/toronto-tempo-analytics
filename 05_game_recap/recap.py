"""Project 5 - Game Recap Card (in the spirit of Rise of the Valkyries' game write-ups).

One-page card for any Tempo game: margin worm, Four Factors head-to-head, top performers.
    .venv/bin/python 05_game_recap/recap.py            # latest Tempo game
    .venv/bin/python 05_game_recap/recap.py 401857215  # a specific game_id
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# let this file import common.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import FIRE, INK, MUTED, TEMPO, VALKYRIES, add_logo, load, save, style, team_games

OUT = Path(__file__).parent / "recaps"  # recap cards go in this folder
TOR_ID = 131935

# team box scores with possessions and opponent stats attached
games = team_games(2026)
tor_games = games[games.team_id == TOR_ID]
# use the game id typed after the script name, or the most recent game if none was given
game_id = int(sys.argv[1]) if len(sys.argv) > 1 else int(tor_games.iloc[-1].game_id)
g = games[games.game_id == game_id].set_index("team_id")
tor, opp = g.loc[TOR_ID], g.drop(TOR_ID).iloc[0]  # Toronto's row and the opponent's row

# play-by-play for this game, used for the game flow chart
pbp = load("pbp", 2026)
pbp = pbp[pbp.game_id == game_id].sort_values("game_play_number")
home = pbp.home_team_id.iloc[0] == TOR_ID
margin = np.where(home, pbp.home_score - pbp.away_score, pbp.away_score - pbp.home_score)
elapsed = (2400 - pbp.end_game_seconds_remaining) / 60  # minutes since tip-off

# player box scores for this game, with Game Score for each player
pb = load("player_box", 2026)
pb = pb[(pb.game_id == game_id) & (pb.minutes.fillna(0) > 0)].copy()
pb["gs"] = (pb.points + 0.4 * pb.field_goals_made - 0.7 * pb.field_goals_attempted
            - 0.4 * (pb.free_throws_attempted - pb.free_throws_made) + 0.7 * pb.offensive_rebounds
            + 0.3 * pb.defensive_rebounds + pb.steals + 0.7 * pb.assists + 0.7 * pb.blocks
            - 0.4 * pb.fouls - pb.turnovers)  # Hollinger game score


def factors(t):
    # the "key battles" numbers for one team in this game
    return {
        "Off. rating": 100 * t.team_score / t.poss,
        "eFG%": 100 * (t.field_goals_made + 0.5 * t.three_point_field_goals_made) / t.field_goals_attempted,
        "TOV%": 100 * t.total_turnovers / t.poss,
        "OREB%": 100 * t.offensive_rebounds / (t.offensive_rebounds + t.opp_defensive_rebounds),
        "FT rate": 100 * t.free_throws_made / t.field_goals_attempted,
        "Paint pts": float(t.points_in_paint),
    }


ft, fo = factors(tor), factors(opp)
# ESPN's colour feed is off for some new teams; use the logo colours there
OPP = {"POR": FIRE, "GS": VALKYRIES}.get(str(opp.team_abbreviation), "#" + str(opp.team_color))
better_low = {"TOV%"}  # for turnovers, lower is better
result = "W" if tor.team_winner else "L"
date = pd.Timestamp(tor.game_date).strftime("%b %-d, %Y")
venue = "vs" if home else "at"

# page layout: game flow across the top, key battles bottom-left, top players bottom-right
fig = plt.figure(figsize=(11, 7.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1], width_ratios=[1.25, 1], hspace=0.5, wspace=0.25, top=0.84)
fig.suptitle(f"Tempo {int(tor.team_score)}, {opp.team_display_name} {int(opp.team_score)}  ({result})",
             x=0.06, y=0.985, ha="left", fontsize=17, fontweight="bold", color=INK)
fig.text(0.06, 0.935, f"{date} · Toronto {venue} {opp.team_abbreviation}", fontsize=10, color=MUTED)

# game flow: Tempo colour when Toronto leads, opponent colour when they trail
ax = fig.add_subplot(gs[0, :])
ax.fill_between(elapsed, margin, 0, where=margin >= 0, color=TEMPO, alpha=0.25, step="post", lw=0)
ax.fill_between(elapsed, margin, 0, where=margin < 0, color=OPP, alpha=0.3, step="post", lw=0)
ax.step(elapsed, margin, where="post", color=INK, lw=1.4)  # step = the score only changes on scoring plays
ax.axhline(0, color=MUTED, lw=1)
end = max(40, elapsed.max())  # longer than 40 minutes if there was overtime
ax.set_xlim(0, end)
ax.set_xticks([0, 10, 20, 30, 40], ["Tip", "Q2", "Half", "Q4", "End"])
style(ax, "Game flow", "Tempo margin (above zero = Toronto leads)")

# key battles: a little text table, winner of each row is bold with a coloured dot
ax = fig.add_subplot(gs[1, 0])
labels = list(ft)
y = np.arange(len(labels))[::-1]  # first stat at the top
for yi, k in zip(y, labels):
    a, b = ft[k], fo[k]
    tor_better = (a < b) if k in better_low else (a > b)
    ax.text(0.0, yi, k, fontsize=10, color=INK, va="center")
    ax.text(0.55, yi, f"{a:.1f}", fontsize=10.5, va="center", ha="right", color=INK,
            fontweight="bold" if tor_better else "normal")
    ax.text(0.85, yi, f"{b:.1f}", fontsize=10.5, va="center", ha="right", color=INK,
            fontweight="bold" if not tor_better else "normal")
    ax.scatter(0.6, yi, s=40, color=TEMPO if tor_better else OPP)
ax.text(0.55, len(labels) - 0.2, "TOR", ha="right", fontsize=9, color=MUTED)
ax.text(0.85, len(labels) - 0.2, opp.team_abbreviation, ha="right", fontsize=9, color=MUTED)
ax.set_xlim(0, 1); ax.set_ylim(-0.6, len(labels) + 0.2); ax.axis("off")
ax.set_title("Key battles (bold + dot = winner)", loc="left", fontsize=12, fontweight="bold", color=INK)

# top 5 Tempo players by Game Score, with their stat line under each bar
ax = fig.add_subplot(gs[1, 1])
top = pb[pb.team_id == TOR_ID].nlargest(5, "gs")
ax.barh(top.athlete_display_name[::-1], top.gs[::-1], color=TEMPO, height=0.6, edgecolor="white", lw=2)
for i, (_, r) in enumerate(top[::-1].iterrows()):
    line = f"{int(r.points)} pts · {int(r.rebounds)} reb · {int(r.assists)} ast · {int(r.field_goals_made)}/{int(r.field_goals_attempted)} FG"
    ax.text(0.3, i - 0.38, line, fontsize=7.5, color=MUTED, va="center")
style(ax, "Top Tempo performers", "Game Score")
ax.grid(axis="y", visible=False); ax.grid(axis="x", color="#ECEEF0")

# file name like 2026-08-21_POR_401857163.png
out = OUT / f"{pd.Timestamp(tor.game_date):%Y-%m-%d}_{opp.team_abbreviation}_{game_id}.png"
logo_file = Path(__file__).resolve().parents[1] / "assets" / "logos" / f"{str(opp.team_abbreviation).lower()}_sm.png"
if not logo_file.exists():  # fetch opponent logo once
    import urllib.request
    urllib.request.urlretrieve(str(opp.team_logo), logo_file.with_name(logo_file.stem.replace("_sm", "") + ".png"))
    from PIL import Image
    im = Image.open(logo_file.with_name(logo_file.stem.replace("_sm", "") + ".png")).convert("RGBA")
    im.thumbnail((160, 160)); im.save(logo_file)
# opponent logo next to the Tempo logo that save() adds in the corner
add_logo(fig, str(opp.team_abbreviation).lower(), size=0.06)
fig.axes[-1].set_position([0.86, 0.9, 0.06, 0.06])
save(fig, out)
