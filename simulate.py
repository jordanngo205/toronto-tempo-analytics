"""Two season simulations for the Expansion Class page, both built on the Elo ratings from elo.py.

1. luck(): how unlucky was Toronto's 11-33? Replay the 2026 schedule 100,000 times, two ways:
     * "game by game": each game's odds as Elo had them before that game (they drop as Toronto loses)
     * "preseason":    every game priced from the ratings at the start of the season, never updated
   and see how often a season ends with 11 wins or fewer.
2. playoffs(): Toronto's chance to make the 2027 playoffs if the ratings carry over the way Elo does.
     * every team starts 2027 at 0.6 x its final 2026 Elo + 0.4 x 1500 (Elo's normal between-season step)
     * teams don't stay exactly where Elo starts them, so each team gets a random shift for the season.
       Its size comes from history: how far each team's average rating during a season (2004-2026)
       ended up from where it started that season.
     * a balanced schedule: every team plays every other team 3 times (42 games), home court picked at random
     * the top 8 by wins make the playoffs (ties broken at random)
   Roster moves, the draft and injuries aren't in it, so it's a starting point, not a forecast.
"""
import numpy as np

import elo

N = 100_000


def win_chance(diff):
    # standard Elo formula: chance to win with a rating edge of `diff` points
    return 1 / (1 + 10 ** (-diff / 400))


def luck(log, tid=131935, season=2026, seed=7):
    rng = np.random.default_rng(seed)
    log = log.assign(team_id=log.team_id.astype(int))
    # elo.compute writes the home team's row first for every game
    log["home"] = ~log.duplicated("game_id")
    s = log[(log.season == season) & (log.season_type.astype(str) == "2")]
    me = s[s.team_id == tid]
    real_wins = int((me.post > me.pre).sum())  # a win raises the rating
    # 1) game by game: the pregame odds Elo had at the time
    p_game = me.p_win.to_numpy()
    # 2) preseason: every team's rating at its first game of the season, plus the home edge from elo.py
    start = s.groupby("team_id").pre.first()
    opp = s[s.game_id.isin(me.game_id) & (s.team_id != tid)].set_index("game_id").team_id.reindex(me.game_id)
    edge = start[tid] - start.reindex(opp).to_numpy() + np.where(me.home.to_numpy(), elo.HCA, -elo.HCA)
    p_pre = win_chance(edge)
    out = {"real": real_wins, "games": int(len(me))}
    for name, p in [("game", p_game), ("pre", p_pre)]:
        wins = (rng.random((N, len(p))) < p).sum(axis=1)
        out[name] = {"mean": round(float(wins.mean()), 1), "le_real": round(float((wins <= real_wins).mean()), 4),
                     "hist": np.bincount(wins, minlength=len(p) + 1).tolist(),
                     "p10": int(np.percentile(wins, 10)), "p90": int(np.percentile(wins, 90))}
    return out


def drift_sd(log):
    """How far a team's average rating during a season lands from where Elo started it (history, 2004-2026)."""
    s = log[log.season_type.astype(str) == "2"].groupby(["season", "team_id"]).agg(start=("pre", "first"), avg=("pre", "mean"), n=("pre", "size"))
    s = s[(s.n >= 20) & (s.index.get_level_values(0) >= 2004)]
    return float((s.avg - s.start).std())


def playoffs(log, names, season=2026, seed=11, spots=8, meet=3):
    rng = np.random.default_rng(seed)
    log = log.assign(team_id=log.team_id.astype(int))
    end = log[log.season == season].groupby("team_id").post.last()  # final 2026 rating, playoffs included
    teams = list(end.index)
    start = elo.CARRY * end.to_numpy() + (1 - elo.CARRY) * elo.MEAN  # carried into 2027
    sd = drift_sd(log)
    t = len(teams)
    wins = np.zeros((N, t))
    # each team's "true" 2027 strength for every simulated season
    true = start + rng.normal(0, sd, (N, t))
    for i in range(t):
        for j in range(i + 1, t):
            for _ in range(meet):
                home_i = rng.random(N) < 0.5
                p = win_chance(true[:, i] - true[:, j] + np.where(home_i, elo.HCA, -elo.HCA))
                w = rng.random(N) < p
                wins[:, i] += w
                wins[:, j] += ~w
    # rank by wins with a tiny random tiebreak; top `spots` make it
    rank = np.argsort(np.argsort(-(wins + rng.random(wins.shape) * 0.1), axis=1), axis=1)
    made = rank < spots
    table = [{"t": names.get(tm, str(tm)), "start": round(float(start[k])), "wins": round(float(wins[:, k].mean()), 1),
              "playoffs": round(float(made[:, k].mean()), 3)} for k, tm in enumerate(teams)]
    table.sort(key=lambda r: -r["playoffs"])
    return {"table": table, "sd": round(sd, 1), "games": (t - 1) * meet, "spots": spots}
