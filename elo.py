"""WNBA Elo ratings, FiveThirtyEight / Neil Paine style.

K = 20, 80-point home edge, margin-of-victory multiplier, 25% regression to
1500 between seasons, new franchises start at 1300.
"""
import pandas as pd

K, HCA, NEW_TEAM, MEAN, CARRY = 20, 80, 1300, 1500, 0.75
PARAMS = {"K": K, "hca": HCA, "new_team": NEW_TEAM, "carry": CARRY}


def compute(tb, first_season=2003):
    """tb: team box rows (both teams per game), sorted by date. Returns one row per team-game."""
    elo, last_season, rows = {}, {}, []
    for g in tb[tb.team_home_away == "home"].itertuples():
        h, a = g.team_id, g.opponent_team_id
        for t in (h, a):
            if t not in elo:
                elo[t] = NEW_TEAM if g.season > first_season else MEAN
            elif last_season[t] != g.season:
                elo[t] = CARRY * elo[t] + (1 - CARRY) * MEAN
            last_season[t] = g.season
        diff = elo[h] + HCA - elo[a]
        p_home = 1 / (1 + 10 ** (-diff / 400))
        mov = g.team_score - g.opponent_team_score
        mult = ((abs(mov) + 3) ** 0.8) / (7.5 + 0.006 * (diff if mov > 0 else -diff))
        shift = K * mult * ((mov > 0) - p_home)
        rows += [(g.game_id, h, g.season, g.season_type, elo[h], elo[h] + shift, p_home),
                 (g.game_id, a, g.season, g.season_type, elo[a], elo[a] - shift, 1 - p_home)]
        elo[h] += shift
        elo[a] -= shift
    return pd.DataFrame(rows, columns=["game_id", "team_id", "season", "season_type", "pre", "post", "p_win"])
