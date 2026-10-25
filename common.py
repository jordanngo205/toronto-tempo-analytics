"""Shared loaders and chart style for the Tempo projects."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"

TEMPO = "#2F5DA8"   # brightened Tempo navy (the official #33476D reads gray on charts)
ACCENT = "#B8325A"  # Tempo maroon / comparison team
LEAGUE = "#A3A9B0"
INK, MUTED = "#1F2328", "#6B7280"


def load(name, season=None, regular=True):
    df = pq.read_table(RAW / f"{name}.parquet").to_pandas(ignore_metadata=True)
    if season is not None and "season" in df:
        df = df[df["season"] == season]
    if regular and "season_type" in df:
        df = df[df["season_type"].astype(str).isin(["2", "Regular Season"])]
    return df.reset_index(drop=True)


def possessions(fga, oreb, tov, fta):
    return fga - oreb + tov + 0.44 * fta


def team_games(season):
    """One row per team-game with possessions and opponent stats attached."""
    t = load("team_box", season).copy()
    t["poss"] = possessions(t.field_goals_attempted, t.offensive_rebounds,
                            t.total_turnovers, t.free_throws_attempted)
    opp = t[["game_id", "team_id", "poss", "field_goals_attempted", "field_goals_made",
             "three_point_field_goals_made", "free_throws_attempted", "free_throws_made",
             "offensive_rebounds", "defensive_rebounds", "total_turnovers"]]
    opp = opp.add_prefix("opp_").rename(columns={"opp_game_id": "game_id", "opp_team_id": "opponent_team_id"})
    t = t.merge(opp, on=["game_id", "opponent_team_id"])
    t["game_date"] = pd.to_datetime(t["game_date"])
    return t.sort_values(["team_abbreviation", "game_date"]).reset_index(drop=True)


def style(ax, title=None, subtitle=None):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#D0D4D9")
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="y", color="#ECEEF0", lw=0.8)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, loc="left", fontsize=13, fontweight="bold", color=INK, pad=22 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=MUTED)


def save(fig, path, source="Data: sportsdataverse (ESPN / WNBA Stats)"):
    fig.text(0.01, -0.04, source, fontsize=7.5, color=MUTED, va="top")
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("saved", path)


plt.rcParams.update({"font.family": "Helvetica Neue", "figure.facecolor": "white"})
np.seterr(divide="ignore", invalid="ignore")
