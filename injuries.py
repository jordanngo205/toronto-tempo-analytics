"""How much did injuries cost each team in 2026, and how many wins would a healthy Toronto have had?

Used by 03_player_impact/build.py (Rotation Lab).

How it works:
  1. A "lost game" is a box-score row marked did-not-play with an injury or illness reason
     (coach's decisions, personal reasons and "not with team" don't count).
  2. Each lost game is worth that player's average Game Score in the games she did play,
     so losing a starter costs more than losing the 12th player.
  3. Across every 2026 game (one row per game), fit home margin = home strength - visitor strength + home edge
     + slope x (Game Score the home team lost - Game Score the visitor lost). The slope says how many
     points of margin one point of missing Game Score is worth.
  4. Healthy Toronto: add the lost Game Score back to each game's margin, then turn each margin into
     a win chance using how spread out real results are around the fit.
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

from common import load

TOR = 131935
# reasons that mean the player was available (or away for non-injury reasons), so they don't count
NOT_INJURY = {"COACH'S DECISION", "PERSONAL", "NOT WITH TEAM", "SUSPENSION", "SUSPENDED", "REST", "LOAD MANAGEMENT"}


def body_part(reason):
    """'LEFT ANKLE INJURY' -> 'Ankle', so the same injury isn't listed three ways."""
    r = str(reason).title()
    if "/" in r:  # "Injury/Illness" is ESPN's general label, keep it as is
        return r
    # a few long ESPN phrases, shortened
    r = r.replace("Concussion Protocol", "Concussion").replace("Return To Competition Reconditioning", "Reconditioning")
    words = [w for w in r.split() if w not in ("Left", "Right", "Injury", "Soreness", "Muscle")]
    return " ".join(words) or r


def compute(season=2026):
    pb = load("player_box", season)
    for c in ["minutes", "points", "rebounds", "offensive_rebounds", "assists", "steals", "blocks", "turnovers", "fouls",
              "field_goals_made", "field_goals_attempted", "free_throws_made", "free_throws_attempted"]:
        pb[c] = pd.to_numeric(pb[c], errors="coerce").fillna(0)
    # Hollinger Game Score for every player-game
    pb["gs"] = (pb.points + 0.4 * pb.field_goals_made - 0.7 * pb.field_goals_attempted - 0.4 * (pb.free_throws_attempted - pb.free_throws_made)
                + 0.7 * pb.offensive_rebounds + 0.3 * (pb.rebounds - pb.offensive_rebounds) + pb.steals + 0.7 * pb.assists
                + 0.7 * pb.blocks - 0.4 * pb.fouls - pb.turnovers)
    pb["team_id"] = pb.team_id.astype(int)
    # only real teams: the All-Star teams play one game, so anything with fewer than 20 games is dropped
    counts = pb.groupby("team_id").game_id.nunique()
    pb = pb[pb.team_id.isin(counts[counts >= 20].index)].copy()
    reason = pb.reason.astype(str).str.upper()
    pb["inj"] = (pb.did_not_play.astype(str) == "True") & pb.reason.notna() & ~reason.isin(NOT_INJURY) & (reason != "NONE")

    # each player's average Game Score and minutes in the games she played for that team
    avg = pb[pb.minutes > 0].groupby(["team_id", "athlete_id"]).agg(avg_gs=("gs", "mean"), mpg=("minutes", "mean"))
    inj = pb[pb.inj].join(avg, on=["team_id", "athlete_id"]).dropna(subset=["avg_gs"])

    # --- 1) league table: Game Score lost per game, every team ---
    ngames = pb.groupby("team_id").game_id.nunique()
    abbr = pb.drop_duplicates("team_id").set_index("team_id").team_abbreviation
    t = inj.groupby("team_id").agg(lost=("game_id", "size"), mins=("mpg", "sum"), gs=("avg_gs", "sum")).reindex(ngames.index).fillna(0)
    league = [{"t": abbr[i], "games": int(r.lost), "mins": round(float(r.mins)), "gs_pg": round(float(r.gs / ngames[i]), 1)}
              for i, r in t.sort_values("gs", ascending=False).iterrows()]

    # --- 2) Toronto's injured players ---
    ti = inj[inj.team_id == TOR].groupby("athlete_display_name").agg(
        games=("game_id", "size"), gs=("avg_gs", "first"), mpg=("mpg", "first"),
        why=("reason", lambda r: sorted({body_part(x) for x in r})))
    players = [{"n": n, "games": int(r.games), "gs": round(float(r.gs), 1), "mpg": round(float(r.mpg), 1), "why": r.why}
               for n, r in ti.sort_values(["games", "gs"], ascending=False).iterrows()]

    # --- 3) what a point of missing Game Score costs in final margin (whole league) ---
    tb = load("team_box", season)
    for c in ["team_score", "opponent_team_score"]:
        tb[c] = pd.to_numeric(tb[c])
    tb["team_id"], tb["opponent_team_id"] = tb.team_id.astype(int), tb.opponent_team_id.astype(int)
    tb = tb[tb.team_id.isin(ngames.index) & tb.opponent_team_id.isin(ngames.index)].reset_index(drop=True)  # no All-Star game
    lost = inj.groupby(["game_id", "team_id"]).avg_gs.sum()
    tb["lost"] = [lost.get((g, i), 0.0) for g, i in zip(tb.game_id, tb.team_id)]
    tb["olost"] = [lost.get((g, i), 0.0) for g, i in zip(tb.game_id, tb.opponent_team_id)]
    tb["mar"] = tb.team_score - tb.opponent_team_score
    teams = sorted(ngames.index)
    # one row per game, from the home team's side (each game shows up twice in the box scores, once per team,
    # and fitting both copies would double count it)
    hm = tb[tb.team_home_away == "home"].reset_index(drop=True)
    # design matrix: +1 for the home team, -1 for the visitor, a constant (home edge), and the Game Score difference lost
    X = np.zeros((len(hm), len(teams) + 2))
    for k, (a, b) in enumerate(zip(hm.team_id, hm.opponent_team_id)):
        X[k, teams.index(a)], X[k, teams.index(b)] = 1, -1
    X[:, -2] = 1
    X[:, -1] = hm.lost - hm.olost
    y = hm.mar.to_numpy(float)
    # team strengths only matter relative to each other, so drop the last team's column to make the fit unique
    X = np.delete(X, len(teams) - 1, axis=1)
    coef = np.linalg.lstsq(X, y, rcond=None)[0]
    res = y - X @ coef
    sd = float(res.std(ddof=X.shape[1]))
    # standard error of the slope from the usual least-squares formula, then a 90% range (+/- 1.645 SE)
    se = float(np.sqrt(sd ** 2 * np.linalg.inv(X.T @ X)[-1, -1]))
    slope = coef[-1]
    lo, hi = slope - 1.645 * se, slope + 1.645 * se

    # --- 4) healthy Toronto ---
    tt = tb[tb.team_id == TOR]
    healthy = lambda s: float(norm.cdf((tt.mar - s * tt.lost) / sd).sum())  # expected wins if nothing was lost
    tor = {"wins": int((tt.mar > 0).sum()), "games": int(len(tt)), "gs_pg": round(float(tt.lost.mean()), 1),
           "mar": round(float(tt.mar.mean()), 1), "mar_healthy": round(float((tt.mar - slope * tt.lost).mean()), 1),
           "healthy": round(healthy(slope), 1), "healthy_lo": round(healthy(hi), 1), "healthy_hi": round(healthy(lo), 1)}
    return {"league": league, "players": players, "tor": tor,
            "slope": round(float(-slope), 3), "slope_lo": round(float(-hi), 3), "slope_hi": round(float(-lo), 3)}


if __name__ == "__main__":
    import json
    print(json.dumps(compute(), indent=1)[:3000])
