"""WNBA Elo ratings, FiveThirtyEight / Neil Paine style.

K = 25, 60-point home edge, margin-of-victory multiplier, 40% regression to
1500 between seasons, new franchises start at 1300.
The settings were picked by testing combinations on 2004-2023 games and checking the winner
on 2024-2026 games it never saw (Brier score 0.2105, down from 0.2143 with K=20/80/25%).
"""
import pandas as pd

# K = how much one game can move a rating
# HCA = home court advantage in Elo points (60 Elo is roughly 2 points on the scoreboard)
# NEW_TEAM = starting rating for an expansion team (below average on purpose)
# MEAN = league average rating
# CARRY = how much of last season's rating a team keeps (the other 40% goes back toward 1500)
K, HCA, NEW_TEAM, MEAN, CARRY = 25, 60, 1300, 1500, 0.6
PARAMS = {"K": K, "hca": HCA, "new_team": NEW_TEAM, "carry": CARRY}


def compute(tb, first_season=2003):
    """tb: team box rows (both teams per game), sorted by date. Returns one row per team-game."""
    # elo = current rating for every team, last_season = the last season I saw each team in
    elo, last_season, rows = {}, {}, []
    # every game shows up twice in the box scores (once per team), so only loop over the home rows
    for g in tb[tb.team_home_away == "home"].itertuples():
        h, a = g.team_id, g.opponent_team_id
        for t in (h, a):
            if t not in elo:
                # first time seeing this team: teams that already existed in 2003 start at average,
                # teams that show up later are expansion teams and start at 1300
                elo[t] = NEW_TEAM if g.season > first_season else MEAN
            elif last_season[t] != g.season:
                # new season: pull the rating 40% of the way back toward 1500
                elo[t] = CARRY * elo[t] + (1 - CARRY) * MEAN
            last_season[t] = g.season
        # rating gap from the home team's point of view (home team gets the home court bonus)
        diff = elo[h] + HCA - elo[a]
        # standard Elo formula: chance the home team wins
        p_home = 1 / (1 + 10 ** (-diff / 400))
        # margin of victory (positive = home team won)
        mov = g.team_score - g.opponent_team_score
        # FiveThirtyEight's margin multiplier: bigger wins move ratings more,
        # but a favourite blowing out a weak team counts a bit less (the 0.006 * diff part)
        mult = ((abs(mov) + 3) ** 0.8) / (7.5 + 0.006 * (diff if mov > 0 else -diff))
        # how many points the home team gains (the away team loses the same amount)
        # (mov > 0) is 1 for a home win and 0 for a loss, so a surprise result moves ratings more
        shift = K * mult * ((mov > 0) - p_home)
        # save one row per team: rating before, rating after, and pregame win chance
        rows += [(g.game_id, h, g.season, g.season_type, elo[h], elo[h] + shift, p_home),
                 (g.game_id, a, g.season, g.season_type, elo[a], elo[a] - shift, 1 - p_home)]
        elo[h] += shift
        elo[a] -= shift
    return pd.DataFrame(rows, columns=["game_id", "team_id", "season", "season_type", "pre", "post", "p_win"])
