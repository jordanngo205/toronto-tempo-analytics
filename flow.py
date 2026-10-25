"""Per-game timelines for Tempo games: score margin over time, scoring runs, pregame Elo odds."""
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import elo
from common import RAW, load

TOR = 131935


def tempo_pbp(season=2026):
    p = load("pbp", season)
    p = p[(p.home_team_id == TOR) | (p.away_team_id == TOR)].copy()
    p = p.sort_values(["game_id", "game_play_number"])
    clock = p.clock_minutes.astype(float) * 60 + p.clock_seconds.astype(float)
    per = p.period_number.astype(int)
    p["t"] = np.where(per <= 4, (per - 1) * 600 + 600 - clock, 2400 + (per - 5) * 300 + 300 - clock)
    home = p.home_team_id == TOR
    p["tor"] = np.where(home, p.home_score, p.away_score).astype(int)
    p["opp"] = np.where(home, p.away_score, p.home_score).astype(int)
    p["m"] = p.tor - p.opp
    p["per"] = per
    return p


def runs(g, min_pts=8):
    """Unanswered scoring runs within one game: [{team, pts, t0, t1, per}]."""
    sc = g[g.scoring_play.astype(bool) & (g.score_value.astype(int) > 0)]
    out, cur = [], None
    for r in sc.itertuples():
        side = "TOR" if r.team_id == TOR else "OPP"
        if cur and cur["team"] == side:
            cur["pts"] += int(r.score_value)
            cur["t1"] = float(r.t)
        else:
            if cur and cur["pts"] >= min_pts:
                out.append(cur)
            cur = {"team": side, "pts": int(r.score_value), "t0": float(r.t), "t1": float(r.t), "per": int(r.per)}
    if cur and cur["pts"] >= min_pts:
        out.append(cur)
    return out


def margin_steps(g):
    """Compressed margin path: [seconds elapsed, margin] at every change, starting at tip."""
    d = g[["t", "m"]].copy()
    d = d[d.m != d.m.shift()]
    pts = [[0, 0]] + [[round(float(t), 1), int(m)] for t, m in zip(d.t, d.m)]
    end = float(g.t.max())
    if pts[-1][0] < end:
        pts.append([round(end, 1), pts[-1][1]])
    return pts


def pregame_odds():
    """Pregame Elo win probability for Toronto, keyed by game_id."""
    tb = pd.concat([pq.read_table(RAW / "team_box_hist.parquet").to_pandas(ignore_metadata=True),
                    pq.read_table(RAW / "team_box.parquet").to_pandas(ignore_metadata=True)], ignore_index=True)
    for c in ["team_score", "opponent_team_score"]:
        tb[c] = pd.to_numeric(tb[c], errors="coerce")
    counts = tb.groupby(["season", "team_id"]).size()
    real = counts[counts >= 20].reset_index()[["season", "team_id"]]
    tb = tb.merge(real, on=["season", "team_id"]).merge(real.rename(columns={"team_id": "opponent_team_id"}), on=["season", "opponent_team_id"])
    tb["game_date"] = pd.to_datetime(tb.game_date)
    tb = tb.sort_values(["game_date", "game_id"])
    log = elo.compute(tb)
    t = log[log.team_id == TOR]
    return dict(zip(t.game_id, t.p_win)), dict(zip(t.game_id, t.pre))


def game_meta(season=2026):
    tb = load("team_box", season)
    t = tb[tb.team_id == TOR].copy()
    t["game_date"] = pd.to_datetime(t.game_date)
    t = t.sort_values("game_date").reset_index(drop=True)
    t["n"] = t.index + 1
    return t, tb
