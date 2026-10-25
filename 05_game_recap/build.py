"""Project 5 - Game Center (interactive): a full recap for any of Toronto's 44 games.

Writes docs/game-center/index.html: season strip to pick a game, then scoreboard, line score,
game flow with runs, both teams' shot charts, four-factor battles and full box scores.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# let this file import flow.py, lab.py and common.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow
import lab
from common import load

TOR = flow.TOR
p = flow.tempo_pbp()            # every play from every Tempo game
meta, tb = flow.game_meta()     # Tempo game list + all team box scores
odds, _ = flow.pregame_odds()   # pregame Elo win chance for each game
pb = load("player_box", 2026)
# box score columns I need as numbers (missing values become 0)
NUM = ["minutes", "points", "rebounds", "offensive_rebounds", "assists", "steals", "blocks", "turnovers", "fouls",
       "field_goals_made", "field_goals_attempted", "three_point_field_goals_made", "three_point_field_goals_attempted",
       "free_throws_made", "free_throws_attempted"]
for c in NUM:
    pb[c] = pd.to_numeric(pb[c], errors="coerce").fillna(0)
pb["plus_minus"] = pd.to_numeric(pb.plus_minus.astype(str).str.lstrip("+"), errors="coerce").fillna(0)
# same thing for the team box score columns
for c in ["field_goals_made", "field_goals_attempted", "three_point_field_goals_made", "three_point_field_goals_attempted",
          "free_throws_made", "free_throws_attempted", "offensive_rebounds", "defensive_rebounds", "total_turnovers",
          "assists", "steals", "blocks", "points_in_paint", "fast_break_points", "turnover_points", "largest_lead", "team_score"]:
    tb[c] = pd.to_numeric(tb[c], errors="coerce").fillna(0)


def team_line(t, o):
    """Team stats for one game. t = this team's box score row, o = the opponent's row."""
    poss = t.field_goals_attempted - t.offensive_rebounds + t.total_turnovers + 0.44 * t.free_throws_attempted
    return {
        "fg": [int(t.field_goals_made), int(t.field_goals_attempted)],
        "fg3": [int(t.three_point_field_goals_made), int(t.three_point_field_goals_attempted)],
        "ft": [int(t.free_throws_made), int(t.free_throws_attempted)],
        # Four Factors
        "efg": round((t.field_goals_made + 0.5 * t.three_point_field_goals_made) / t.field_goals_attempted, 3),
        "tov": round(t.total_turnovers / poss, 3), "orb": round(t.offensive_rebounds / (t.offensive_rebounds + o.defensive_rebounds), 3),
        "ftr": round(t.free_throws_made / t.field_goals_attempted, 3), "paint": int(t.points_in_paint),
        "fast": int(t.fast_break_points), "tovpts": int(t.turnover_points), "ast": int(t.assists),
        "reb": int(t.offensive_rebounds + t.defensive_rebounds), "stl": int(t.steals), "blk": int(t.blocks),
        "poss": round(poss, 1), "ortg": round(100 * t.team_score / poss, 1),  # points per 100 possessions
    }


def box(gid, team_id):
    """Box score rows for one team in one game (only players who played)."""
    b = pb[(pb.game_id == gid) & (pb.team_id == team_id) & (pb.minutes > 0)].copy()
    # Hollinger's Game Score: one number for how good a player's game was
    b["gs"] = (b.points + 0.4 * b.field_goals_made - 0.7 * b.field_goals_attempted - 0.4 * (b.free_throws_attempted - b.free_throws_made)
               + 0.7 * b.offensive_rebounds + 0.3 * (b.rebounds - b.offensive_rebounds) + b.steals + 0.7 * b.assists
               + 0.7 * b.blocks - 0.4 * b.fouls - b.turnovers)
    b = b.sort_values(["starter", "minutes"], ascending=False)  # starters first, then by minutes
    # each row is a plain list to keep the page small. The page reads them by position:
    # [name, starter, min, pts, reb, ast, stl, blk, tov, fgm, fga, 3pm, 3pa, ftm, fta, +/-, game score]
    return [[r.athlete_display_name, int(bool(r.starter)), int(r.minutes), int(r.points), int(r.rebounds), int(r.assists),
             int(r.steals), int(r.blocks), int(r.turnovers), int(r.field_goals_made), int(r.field_goals_attempted),
             int(r.three_point_field_goals_made), int(r.three_point_field_goals_attempted), int(r.free_throws_made),
             int(r.free_throws_attempted), int(r.plus_minus), round(r.gs, 1)] for r in b.itertuples()]


games = []
wins = 0  # running win count so each game can show the record after it
for g in meta.itertuples():
    gp = p[p.game_id == g.game_id]
    # the opponent's and Toronto's team box score rows for this game
    o = tb[(tb.game_id == g.game_id) & (tb.team_id != TOR)].iloc[0]
    t = tb[(tb.game_id == g.game_id) & (tb.team_id == TOR)].iloc[0]
    wins += int(g.team_score > g.opponent_team_score)
    # line score: points per quarter = score at end of quarter minus score at end of previous quarter
    q = gp.groupby("per")[["tor", "opp"]].last()
    line = {"tor": (q.tor - q.tor.shift(fill_value=0)).astype(int).tolist(), "opp": (q.opp - q.opp.shift(fill_value=0)).astype(int).tolist()}
    # field-goal attempts in this game (both teams) for the shot charts
    sh = gp[gp.shooting_play.astype(bool) & ~gp.type_text.str.contains("Free Throw")]
    sh = sh[(sh.coordinate_y_raw.astype(float) <= 30) & sh.coordinate_x_raw.astype(float).between(0, 50)]
    # store shooter names once and point to them by index (saves space)
    names = sorted(sh.athlete_name_1.dropna().unique().tolist())
    # each shot: [x, y, made, three, team (0 = Tempo, 1 = opponent), shooter index, seconds into game]
    shots = [[round(float(r.coordinate_x_raw), 1), round(float(r.coordinate_y_raw), 1), int(bool(r.scoring_play)),
              int(r.points_attempted == 3), int(r.team_id != TOR), names.index(r.athlete_name_1) if r.athlete_name_1 in names else -1,
              round(float(r.t))] for r in sh.itertuples()]
    games.append({
        "n": int(g.n), "id": int(g.game_id), "date": g.game_date.strftime("%a %b %-d"), "short": g.game_date.strftime("%b %-d"),
        "opp": g.opponent_team_abbreviation, "opp_name": g.opponent_team_display_name, "home": g.team_home_away == "home",
        "pf": int(g.team_score), "pa": int(g.opponent_team_score), "rec": f"{wins}-{int(g.n) - wins}",
        "p": round(float(odds.get(g.game_id, np.nan)), 3), "ot": bool((gp.per > 4).any()),
        "line": line, "steps": flow.margin_steps(gp), "runs": flow.runs(gp),
        "team": {"tor": team_line(t, o), "opp": team_line(o, t)},
        "box": {"tor": box(g.game_id, TOR), "opp": box(g.game_id, o.team_id)},
        "names": names, "shots": shots, "lead": int(t.largest_lead), "opp_lead": int(o.largest_lead),
    })

# headline numbers for the home page, then write the page
lab.summary("game-center", {"games": len(games), "record": games[-1]["rec"]})
data = {"games": games}
lab.write_page("game-center", "Game Center", "A full recap for every Toronto Tempo game of 2026: game flow, shot charts, key battles and box scores.",
               Path(__file__).parent / "page.html", data)
