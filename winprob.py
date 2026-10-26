"""In-game win probability for every WNBA game in 2025 and 2026.

At any moment, the chance the home team wins depends on three things:
  * the score margin,
  * how much time is left (a 5-point lead with 30 seconds left is safe, with 30 minutes left it isn't),
  * how good the two teams are (the pregame Elo odds), which matters less and less as the game goes on.
So the model is a logistic regression with three inputs:
  x1 = margin / sqrt(minutes left + 1)      the lead, counted for more as time runs out
  x2 = pregame log-odds x (time left / 40 min)   team strength, fading to nothing at the buzzer
  x3 = margin                               a little extra weight on the raw lead
Trained on 2025, tested on 2026 games it never saw, then refit on both seasons for the site.
Win probability added (WPA) for a play = how much it moved its own team's win chance (scoring plays only,
since the play-by-play doesn't say who has the ball).
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

import flow
from common import load


def plays(season=None):
    """Every play with seconds left, home margin, pregame odds and the final result (home won = 1)."""
    p = load("pbp", season).sort_values(["game_id", "game_play_number"]).copy()
    clock = p.clock_minutes.astype(float) * 60 + p.clock_seconds.astype(float)
    per = p.period_number.astype(int)
    # seconds since tip-off (same as flow.tempo_pbp), and seconds left in the game as it stands
    p["t"] = np.where(per <= 4, (per - 1) * 600 + 600 - clock, 2400 + (per - 5) * 300 + 300 - clock)
    end = np.where(per <= 4, 2400, 2400 + (per - 4) * 300)  # when the current period's game ends
    p["left"] = np.clip(end - p.t, 0, None)
    p["m"] = p.home_score.astype(int) - p.away_score.astype(int)
    p["per"] = per
    # final result from the last play of each game
    last = p.groupby("game_id").m.last()
    p["home_won"] = (p.game_id.map(last) > 0).astype(int)
    # pregame home win chance from Elo
    log = flow.elo_log()
    home_p = log.set_index(["game_id", "team_id"]).p_win
    p["pre"] = [home_p.get((g, h), np.nan) for g, h in zip(p.game_id, p.home_team_id)]
    return p.dropna(subset=["pre"])


def features(df):
    lo = np.log(df.pre / (1 - df.pre))  # pregame odds as log-odds
    return np.c_[df.m / np.sqrt(df.left / 60 + 1), lo * df.left / 2400, df.m]


def fit(df):
    return LogisticRegression(C=1e4, max_iter=1000).fit(features(df), df.home_won)


def test():
    """Train on 2025, score on 2026: log loss, Brier score and a calibration table."""
    p = plays()
    tr, te = p[p.season == 2025], p[p.season == 2026]
    m = fit(tr)
    q = np.clip(m.predict_proba(features(te))[:, 1], 1e-6, 1 - 1e-6)  # keep away from exactly 0 or 1 for the log
    y = te.home_won.to_numpy()
    ll = -np.mean(y * np.log(q) + (1 - y) * np.log(1 - q))
    base = te.pre.to_numpy()  # pregame odds only, never updated
    ll0 = -np.mean(y * np.log(base) + (1 - y) * np.log(1 - base))
    bins = pd.cut(q, np.linspace(0, 1, 11), include_lowest=True)
    cal = pd.DataFrame({"pred": q, "won": y}).groupby(bins, observed=True).agg(pred=("pred", "mean"), won=("won", "mean"), n=("won", "size"))
    return {"logloss": round(float(ll), 4), "logloss_pregame_only": round(float(ll0), 4),
            "brier": round(float(np.mean((q - y) ** 2)), 4), "plays": int(len(te)), "games": int(te.game_id.nunique()),
            "calibration": [[round(float(r.pred), 3), round(float(r.won), 3), int(r.n)] for r in cal.itertuples()]}


_model = None


def model():
    """The model fitted on both seasons (fitted once, then reused)."""
    global _model
    if _model is None:
        _model = fit(plays())
    return _model


def coefs():
    """The fitted numbers, for the formula shown on the page."""
    m = model()
    return {"b0": round(float(m.intercept_[0]), 3), "b1": round(float(m.coef_[0][0]), 3),
            "b2": round(float(m.coef_[0][1]), 3), "b3": round(float(m.coef_[0][2]), 3)}


def game(gp, tor_home):
    """Win probability for one game's plays (gp from plays()), from Toronto's side.
    Returns the plays with columns wp (Toronto's chance after the play) and wpa (change for the team that made the play)."""
    g = gp.copy()
    wp_home = model().predict_proba(features(g))[:, 1]
    # at the final buzzer the result is known
    done = (g.left == 0) & (g.per >= 4) & (g.m != 0)
    wp_home = np.where(done, (g.m > 0).astype(float), wp_home)
    g["wp"] = wp_home if tor_home else 1 - wp_home
    # change in the HOME team's chance from each play, measured at the same moment in time: the chance after the
    # play minus the chance with the old score at that time. (Comparing with the previous play instead would also
    # count the clock running, which isn't anything the player did.) Only plays that change the score move it.
    prev = g.copy()
    prev["m"] = g.groupby("game_id").m.shift(fill_value=0)
    before = model().predict_proba(features(prev))[:, 1]
    before = np.where(done, wp_home, before)
    d_home = wp_home - before
    g["wpa"] = np.where(g.team_id == g.home_team_id, d_home, -d_home)
    return g


if __name__ == "__main__":
    import json
    print(json.dumps(test(), indent=1))
    print("coefficients", model().coef_.round(4), model().intercept_.round(4))
