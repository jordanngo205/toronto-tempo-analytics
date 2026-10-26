"""Per-game timelines for Tempo games: score margin over time, scoring runs, pregame Elo odds."""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import elo
from common import RAW, load

TOR = 131935  # ESPN's team id for the Toronto Tempo


def tempo_pbp(season=2026):
    # play-by-play for every Tempo game (home or away), in the order the plays happened
    p = load("pbp", season)
    p = p[(p.home_team_id == TOR) | (p.away_team_id == TOR)].copy()
    p = p.sort_values(["game_id", "game_play_number"])
    # time left on the game clock in seconds
    clock = p.clock_minutes.astype(float) * 60 + p.clock_seconds.astype(float)
    per = p.period_number.astype(int)
    # turn "period + clock" into seconds since tip-off
    # quarters are 10 minutes (600 s); overtime periods are 5 minutes (300 s) and start at 2400 s
    p["t"] = np.where(per <= 4, (per - 1) * 600 + 600 - clock, 2400 + (per - 5) * 300 + 300 - clock)
    # score from Toronto's side, so it doesn't matter if they were home or away
    home = p.home_team_id == TOR
    p["tor"] = np.where(home, p.home_score, p.away_score).astype(int)
    p["opp"] = np.where(home, p.away_score, p.home_score).astype(int)
    p["m"] = p.tor - p.opp  # margin: positive means Toronto is winning
    p["per"] = per
    return p


def runs(g, min_pts=8):
    """Unanswered scoring runs within one game: [{team, pts, t0, t1, per}]."""
    # only the plays where someone scored
    sc = g[g.scoring_play.astype(bool) & (g.score_value.astype(int) > 0)]
    out, cur = [], None  # out = finished runs, cur = the run happening right now
    for r in sc.itertuples():
        side = "TOR" if r.team_id == TOR else "OPP"
        if cur and cur["team"] == side:
            # same team scored again, so the run keeps going
            cur["pts"] += int(r.score_value)
            cur["t1"] = float(r.t)
        else:
            # the other team scored, so the old run is over. Keep it if it was big enough
            if cur and cur["pts"] >= min_pts:
                out.append(cur)
            # start a new run for the team that just scored
            cur = {"team": side, "pts": int(r.score_value), "t0": float(r.t), "t1": float(r.t), "per": int(r.per)}
    # don't forget the run that was still going at the final buzzer
    if cur and cur["pts"] >= min_pts:
        out.append(cur)
    return out


def margin_steps(g):
    """Compressed margin path: [seconds elapsed, margin] at every change, starting at tip."""
    d = g[["t", "m"]].copy()
    # only keep rows where the margin actually changed (saves a lot of space in the web page)
    d = d[d.m != d.m.shift()]
    pts = [[0, 0]] + [[round(float(t), 1), int(m)] for t, m in zip(d.t, d.m)]
    # add a final point at the end of the game so the line goes all the way to the buzzer
    end = float(g.t.max())
    if pts[-1][0] < end:
        pts.append([round(end, 1), pts[-1][1]])
    return pts


def elo_log():
    """Elo for every team-game since 2003 (one row per team per game, with the pregame win chance)."""
    # Elo needs history, so load every season since 2003 plus 2025-26
    tb = pd.concat([pq.read_table(RAW / "team_box_hist.parquet").to_pandas(ignore_metadata=True),
                    pq.read_table(RAW / "team_box.parquet").to_pandas(ignore_metadata=True)], ignore_index=True)
    for c in ["team_score", "opponent_team_score"]:
        tb[c] = pd.to_numeric(tb[c], errors="coerce")
    # All-Star teams only play 1 game a year, so keep teams with 20+ games in a season
    counts = tb.groupby(["season", "team_id"]).size()
    real = counts[counts >= 20].reset_index()[["season", "team_id"]]
    # the second merge removes games where the OPPONENT was an All-Star team
    tb = tb.merge(real, on=["season", "team_id"]).merge(real.rename(columns={"team_id": "opponent_team_id"}), on=["season", "opponent_team_id"])
    tb["game_date"] = pd.to_datetime(tb.game_date)
    tb = tb.sort_values(["game_date", "game_id"])  # Elo has to go in date order
    return elo.compute(tb)


def pregame_odds():
    """Pregame Elo win probability for Toronto, keyed by game_id."""
    log = elo_log()
    t = log[log.team_id == TOR]
    # two lookups by game id: win probability, and Toronto's Elo before the game
    return dict(zip(t.game_id, t.p_win)), dict(zip(t.game_id, t.pre))


def game_meta(season=2026):
    # one row per Tempo game with a game number (1 to 44) in date order
    tb = load("team_box", season)
    t = tb[tb.team_id == TOR].copy()
    t["game_date"] = pd.to_datetime(t.game_date)
    t = t.sort_values("game_date").reset_index(drop=True)
    t["n"] = t.index + 1
    # also return the full table so builds can look up the opponent's row
    return t, tb
