"""Project 5 - Game Center (interactive): a full recap for any of Toronto's 44 games.

Writes docs/game-center/index.html: season strip to pick a game, then scoreboard, line score,
game flow with runs, both teams' shot charts, four-factor battles and full box scores.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# let this file import flow.py, lab.py and common.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow
import lab
import winprob
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


def court_colour(row):
    """The opponent's colour for the shot chart. ESPN's main colour is sometimes too pale to see on a white
    court (Las Vegas grey, New York mint), so fall back to the alternate colour when it's too light.
    Portland and Golden State use their logo colours, which ESPN's feed doesn't have right."""
    fixed = {"POR": "#e8379b", "GS": "#9b6fc6"}
    if row.team_abbreviation in fixed:
        return fixed[row.team_abbreviation]
    def lum(h):
        # relative brightness of a hex colour (0 = black, 1 = white)
        r, g, b_ = (int(str(h)[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_
    main, alt = str(row.team_color), str(row.team_alternate_color)
    return "#" + (alt if lum(main) > 0.55 and alt not in ("nan", "None") else main)


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


def story(gp):
    """Numbers for the game-story panel, from the play-by-play of one game."""
    m = gp.m.to_numpy()
    sign = np.sign(m)
    nz = sign[sign != 0]
    lead_changes = int((np.diff(nz) != 0).sum())                # leader switched from one team to the other
    ties = int(((m[1:] == 0) & (m[:-1] != 0)).sum())           # score went back to level
    # share of game time Toronto led / trailed (time between plays, counted with the margin before the play)
    t = gp.t.to_numpy(float)
    secs = np.diff(np.r_[0, t])
    prev = np.r_[0, m[:-1]]
    total = t.max()
    return {"lc": lead_changes, "ties": ties, "lead": round(float(secs[prev > 0].sum() / total), 3),
            "trail": round(float(secs[prev < 0].sum() / total), 3), "max": int(m.max()), "min": int(m.min())}


def clutch_points(gp):
    """Points each player scored in clutch time: the last 5 minutes of the 4th quarter or any overtime,
    on plays that started with the score within 5."""
    m_before = gp.m.shift(fill_value=0)  # margin before each play
    late = ((gp.per == 4) & (gp.t >= 2100)) | (gp.per > 4)
    sc = gp[late & (m_before.abs() <= 5) & gp.scoring_play.astype(bool) & (gp.score_value.astype(int) > 0)]
    return {k: int(v) for k, v in sc.groupby("athlete_name_1").score_value.sum().items()}


# order of the numbers in each player's "awards" list (the page reads them by position)
AWARD_KEYS = ["rim", "mid", "corner3", "floater", "driving", "cutting", "fade", "putback", "bank", "fast", "late", "goahead", "blocked"]


def award_counts(gp):
    """Per-player numbers for the ESPN-style award strip, counted from one game's play-by-play.
    Most are points from one kind of shot. 'fast' = points within 6 seconds of her team winning the ball (432 Tempo points on the season vs ESPN's 437),
    'late' = points with under 5 seconds left on an estimated shot clock, 'goahead' = points that put her
    team in front, 'blocked' = how many of her shots got blocked."""
    out = {}
    def add(name, key, v):
        if isinstance(name, str) and v:
            out.setdefault(name, [0] * len(AWARD_KEYS))[AWARD_KEYS.index(key)] += v
    # the play-by-play doesn't have a shot clock, so I estimate it: I track which team has the ball and
    # when that possession started (defensive rebound, turnover, made basket by the other team, new period).
    # An offensive rebound resets the clock to 14 like the real rule.
    teams = [x for x in gp.team_id.dropna().unique()]
    other = lambda tm: next((x for x in teams if x != tm), None)
    owner, start, clock, last_per = None, 0.0, 24, None
    for r in gp.itertuples():
        t, team, typ = float(r.t), r.team_id, str(r.type_text)
        if r.per != last_per:  # new quarter: nobody has the ball yet
            owner, start, clock, last_per = None, t, 24, r.per
        made = bool(r.scoring_play) and int(r.score_value) > 0
        is_ft = "Free Throw" in typ
        if made:
            pts = int(r.score_value)
            # margin from the scoring team's point of view, before and after the basket
            after = int(r.m) if team == TOR else -int(r.m)
            if after - pts <= 0 < after:
                add(r.athlete_name_1, "goahead", pts)
            if not is_ft:
                if owner == team and clock == 24 and t - start <= 6:
                    add(r.athlete_name_1, "fast", pts)
                if owner == team and t - start >= clock - 5:
                    add(r.athlete_name_1, "late", pts)
                # shot type from ESPN's description of the shot
                for word, key in [("Float", "floater"), ("Driving", "driving"), ("Cutting", "cutting"), ("Fade", "fade"), ("Bank", "bank")]:
                    if word in typ:
                        add(r.athlete_name_1, key, pts)
                if "Putback" in typ or "Tip" in typ:
                    add(r.athlete_name_1, "putback", pts)
                # shot location, same zones as Shot Lab (only when the spot is on the half court)
                x, y = float(r.coordinate_x_raw), float(r.coordinate_y_raw)
                if 0 <= x <= 50 and y <= 30:
                    d = np.hypot(x - 25, y)
                    three = r.points_attempted == 3
                    if d < 4:
                        add(r.athlete_name_1, "rim", pts)
                    elif three and y <= 3:
                        add(r.athlete_name_1, "corner3", pts)
                    elif not three and d >= 10:
                        add(r.athlete_name_1, "mid", pts)
        if "blocks" in str(r.text):
            add(r.athlete_name_1, "blocked", 1)
        # who has the ball after this play
        ft = re.search(r"(\d) of (\d)", typ)
        last_ft = bool(ft) and ft.group(1) == ft.group(2)
        if typ == "Defensive Rebound":
            owner, start, clock = team, t, 24
        elif typ == "Offensive Rebound":
            owner, start, clock = team, t, 14
        elif "Turnover" in typ or (made and (not is_ft or last_ft)):
            owner, start, clock = other(team), t, 24
        elif "Foul" in typ and "Shooting" not in typ and "Offensive" not in typ and team != owner:
            # a defensive foul away from the shot: the shot clock goes back up to 14 if it was lower
            if clock - (t - start) < 14:
                start, clock = t, 14
    return out


def box(gid, team_id):
    """Box score rows for one team in one game (only players who played)."""
    b = pb[(pb.game_id == gid) & (pb.team_id == team_id) & (pb.minutes > 0)].copy()
    # Hollinger's Game Score: one number for how good a player's game was
    b["gs"] = (b.points + 0.4 * b.field_goals_made - 0.7 * b.field_goals_attempted - 0.4 * (b.free_throws_attempted - b.free_throws_made)
               + 0.7 * b.offensive_rebounds + 0.3 * (b.rebounds - b.offensive_rebounds) + b.steals + 0.7 * b.assists
               + 0.7 * b.blocks - 0.4 * b.fouls - b.turnovers)
    b = b.sort_values(["starter", "minutes"], ascending=False)  # starters first, then by minutes
    # each row is a plain list to keep the page small. The page reads them by position:
    # [name, starter, min, pts, reb, ast, stl, blk, tov, fgm, fga, 3pm, 3pa, ftm, fta, +/-, game score, oreb, fouls]
    return [[r.athlete_display_name, int(bool(r.starter)), int(r.minutes), int(r.points), int(r.rebounds), int(r.assists),
             int(r.steals), int(r.blocks), int(r.turnovers), int(r.field_goals_made), int(r.field_goals_attempted),
             int(r.three_point_field_goals_made), int(r.three_point_field_goals_attempted), int(r.free_throws_made),
             int(r.free_throws_attempted), int(r.plus_minus), round(r.gs, 1),
             int(r.offensive_rebounds), int(r.fouls)] for r in b.itertuples()]  # [17] offensive rebounds, [18] fouls (for the Game Score breakdown)


# --- best games around the league each night (Game Score for every WNBA player, every game) ---------------
lg = pb[pb.minutes > 0].copy()
lg["gs"] = (lg.points + 0.4 * lg.field_goals_made - 0.7 * lg.field_goals_attempted - 0.4 * (lg.free_throws_attempted - lg.free_throws_made)
            + 0.7 * lg.offensive_rebounds + 0.3 * (lg.rebounds - lg.offensive_rebounds) + lg.steals + 0.7 * lg.assists
            + 0.7 * lg.blocks - 0.4 * lg.fouls - lg.turnovers)
lg["date"] = pd.to_datetime(lg.game_date).dt.date
lg["won"] = pd.to_numeric(lg.team_score, errors="coerce") > pd.to_numeric(lg.opponent_team_score, errors="coerce")


def nightly(date, gid, n=8):
    """Top Game Scores across the WNBA on one date: [name, team, opponent, gs, pts, reb, ast, won, in_this_game, headshot]."""
    d = lg[lg.date == date].sort_values("gs", ascending=False)
    top = d.head(n)
    out = [[r.athlete_display_name, r.team_abbreviation, r.opponent_team_abbreviation, round(r.gs, 1), int(r.points),
            int(r.rebounds), int(r.assists), bool(r.won), int(r.game_id) == int(gid),
            r.athlete_headshot_href if isinstance(r.athlete_headshot_href, str) else ""] for r in top.itertuples()]
    # where the best Tempo player that night ranked among everyone who played
    tor = d[d.team_id == TOR]
    best_rank = int((d.gs > tor.gs.max()).sum() + 1) if len(tor) else None
    return {"top": out, "players": int(len(d)), "games": int(d.game_id.nunique()), "tor_best_rank": best_rank}


# --- win probability (see winprob.py) -------------------------------------------------------
WP = winprob.plays(2026)


def win_chance(gid, tor_home):
    """Toronto's win chance through one game, the biggest swing plays, and each player's win probability added."""
    g = winprob.game(WP[WP.game_id == gid], tor_home)
    tor_side = g.team_id == TOR
    # Toronto's change in win chance on each play (wpa is for the team that made the play)
    d_tor = np.where(tor_side, g.wpa, -g.wpa)
    # the line: the start, every play that moved the chance by half a point or more, and the end
    keep = (np.abs(d_tor) >= 0.005) | g.scoring_play.astype(bool)
    keep.iloc[0] = True  # always start at tip-off
    pts = [[round(float(a)), round(float(b) * 100, 1)] for a, b in zip(g.t[keep], g.wp[keep])]
    pts.append([round(float(g.t.max())), 100.0 if g.m.iloc[-1] * (1 if tor_home else -1) > 0 else 0.0])
    # the three plays that moved Toronto's chance the most, either way
    big = g.assign(d=d_tor).loc[lambda d: d.athlete_name_1.notna()].reindex(columns=["t", "d", "text", "athlete_name_1", "home_score", "away_score"])
    big = big.loc[big.d.abs().sort_values(ascending=False).index[:3]]
    swings = [[round(float(r.t)), round(float(r.d) * 100, 1), str(r.text), r.athlete_name_1,
               f"{int(r.home_score if tor_home else r.away_score)}-{int(r.away_score if tor_home else r.home_score)}"] for r in big.itertuples()]
    # each player's single biggest swing for her own team (the play-by-play can't charge defenders for the other
    # team's baskets, so adding up a player's swings over a game would only count the good half)
    wpa = g.dropna(subset=["athlete_name_1"]).groupby("athlete_name_1").wpa.max()
    won = g.m.iloc[-1] * (1 if tor_home else -1) > 0
    # the lowest chance Toronto came back from in a win, or the highest it let slip in a loss
    extreme = float(g.wp.min() if won else g.wp.max())
    return {"pts": pts, "swings": swings, "wpa": {k: round(float(v) * 100, 1) for k, v in wpa.items()},
            "extreme": round(extreme * 100, 1)}


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
        "opp_color": court_colour(o),
        "story": story(gp),
        "night": nightly(g.game_date.date(), g.game_id),
        "clutch": clutch_points(gp),
        "aw": award_counts(gp),
        "wp": win_chance(g.game_id, g.team_home_away == "home"),
        # headshot link for every player who played (empty when ESPN has none)
        "heads": {r.athlete_display_name: r.athlete_headshot_href for r in
                  pb[(pb.game_id == g.game_id) & (pb.minutes > 0)].itertuples() if isinstance(r.athlete_headshot_href, str)},
    })

# headline numbers for the home page, then write the page
# the home page draws the season as a circle, so it gets every game: [game number, opponent, points for, points against, date]
def top_scorer(g):
    # Toronto's leading scorer in that game: [name, points]
    r = max(g["box"]["tor"], key=lambda r: r[3])
    return [r[0], r[3]]


# [game number, opponent, points for, points against, date, home (1/0), opponent's full name, top scorer, her points]
season = [[g["n"], g["opp"], g["pf"], g["pa"], g["short"], int(g["home"]), g["opp_name"], *top_scorer(g)] for g in games]
lab.summary("game-center", {"games": len(games), "record": games[-1]["rec"], "season": season})
data = {"games": games, "aw_keys": AWARD_KEYS}
lab.write_page("game-center", "Game Center", "A full recap for every Toronto Tempo game of 2026: game flow, shot charts, key battles and box scores.",
               Path(__file__).parent / "page.html", data)
