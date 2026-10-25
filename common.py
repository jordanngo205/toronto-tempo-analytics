"""Shared loaders and chart style for the Tempo projects."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# folder paths: ROOT is the main project folder, RAW is where data/pull.py saves the data
ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"

# colours I use for the static matplotlib charts
TEMPO = "#8A1F42"       # Tempo bordeaux (logo colour)
TEMPO_NAVY = "#33476D"  # Tempo secondary
VALKYRIES = "#9B6FC6"
FIRE = "#E8379B"
ACCENT = VALKYRIES      # default comparison team
LEAGUE = "#A3A9B0"      # grey for "everyone else"
INK, MUTED = "#1F2328", "#6B7280"  # dark text colour and light text colour


def load(name, season=None, regular=True):
    # read one of the saved parquet files (for example "pbp" or "team_box")
    # ignore_metadata=True gives normal pandas columns instead of pyarrow ones
    df = pq.read_table(RAW / f"{name}.parquet").to_pandas(ignore_metadata=True)
    # keep only one season if I asked for one
    if season is not None and "season" in df:
        df = df[df["season"] == season]
    # keep only regular season games (season_type 2), some files write it as text instead
    if regular and "season_type" in df:
        df = df[df["season_type"].astype(str).isin(["2", "Regular Season"])]
    return df.reset_index(drop=True)


def possessions(fga, oreb, tov, fta):
    # standard possession estimate: shots - offensive rebounds + turnovers + 0.44 * free throw attempts
    # (0.44 because not every free throw trip ends a possession, e.g. and-ones and 3-shot fouls)
    return fga - oreb + tov + 0.44 * fta


def team_games(season):
    """One row per team-game with possessions and opponent stats attached."""
    t = load("team_box", season).copy()
    # possessions for each team in each game
    t["poss"] = possessions(t.field_goals_attempted, t.offensive_rebounds,
                            t.total_turnovers, t.free_throws_attempted)
    # make a copy of the stats I need for the opponent side
    opp = t[["game_id", "team_id", "poss", "field_goals_attempted", "field_goals_made",
             "three_point_field_goals_made", "free_throws_attempted", "free_throws_made",
             "offensive_rebounds", "defensive_rebounds", "total_turnovers"]]
    # rename them to opp_... so they don't clash, and rename team_id so it matches opponent_team_id
    opp = opp.add_prefix("opp_").rename(columns={"opp_game_id": "game_id", "opp_team_id": "opponent_team_id"})
    # join: each team row now also has its opponent's stats from the same game
    t = t.merge(opp, on=["game_id", "opponent_team_id"])
    t["game_date"] = pd.to_datetime(t["game_date"])
    # sort by team then date so rolling calculations go in order
    return t.sort_values(["team_abbreviation", "game_date"]).reset_index(drop=True)


def style(ax, title=None, subtitle=None):
    # my default look for every matplotlib chart: no top/right border, light grid, grey ticks
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#D0D4D9")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color="#ECEEF0", lw=0.8)
    ax.set_axisbelow(True)  # draw the grid behind the data
    # title on the left, with extra space under it if there is a subtitle
    if title:
        ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK, pad=22 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=MUTED)


def add_logo(fig, team="tor", size=0.07):
    """Team logo in the top-right corner of the figure."""
    img = plt.imread(ROOT / "assets" / "logos" / f"{team}_sm.png")
    # a tiny extra axes in the corner just to hold the picture
    ax = fig.add_axes([1 - size - 0.005, 1 - size + 0.01, size, size], anchor="NE", zorder=10)
    ax.imshow(img)
    ax.axis("off")


def save(fig, path, source="Data: sportsdataverse (ESPN / WNBA Stats)", logo="tor"):
    # add the logo and a data source line, then save the chart as a PNG
    if logo:
        add_logo(fig, logo)
    fig.text(0.01, -0.04, source, fontsize=7.5, color=MUTED, va="top")
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)  # close it so memory doesn't fill up when making lots of charts
    print("saved", path)


# global matplotlib settings for every chart
plt.rcParams.update({"font.family": "Helvetica Neue", "figure.facecolor": "white"})
# don't print warnings when dividing by zero (some players have 0 attempts)
np.seterr(divide="ignore", invalid="ignore")
