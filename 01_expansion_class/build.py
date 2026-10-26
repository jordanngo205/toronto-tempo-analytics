"""Project 1 - The Expansion Class.

Builds expansion.json for the interactive page (index.html): Golden State 2025,
Toronto 2026 and Portland 2026, with Chicago 2006 and Atlanta 2008 as the
historical bar. Pieces:
  * Elo ratings for every WNBA game 2003-2026 (538-style, new teams start at 1300)
  * league-rank fingerprint on ratings and Four Factors
  * hex shot maps (size = shot frequency, colour = zone efficiency vs league)
  * roster experience, head-to-heads, clutch, top players
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# let this file import elo.py, lab.py and common.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import elo
import lab
from common import RAW, possessions

OUT = Path(__file__).parent
# the five expansion teams I compare: (short name, ESPN team id, their first season, full name)
CLASS = [  # key, team_id, season, label
    ("GS", 129689, 2025, "Golden State Valkyries"),
    ("TOR", 131935, 2026, "Toronto Tempo"),
    ("POR", 132052, 2026, "Portland Fire"),
    ("CHI", 19, 2006, "Chicago Sky"),
    ("ATL", 20, 2008, "Atlanta Dream"),
]
MODERN = CLASS[:3]  # the three recent teams get the detailed sections (shots, players...)


def read(name):
    # small helper: load a parquet file from data/raw
    return pq.read_table(RAW / f"{name}.parquet").to_pandas(ignore_metadata=True)


def num(df, cols):
    # some columns come in as text, so turn them into numbers (bad values become NaN)
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# --- all games ----------------------------------------------------------------
# stack the old seasons (2003-2024) and the new ones (2025-2026) into one table
tb = pd.concat([read("team_box_hist"), read("team_box")], ignore_index=True)
tb["season_type"] = tb.season_type.astype(str)
tb = num(tb, ["team_score", "opponent_team_score", "field_goals_attempted", "field_goals_made",
              "three_point_field_goals_made", "free_throws_attempted", "free_throws_made",
              "offensive_rebounds", "defensive_rebounds", "total_turnovers", "points_in_paint"])
# drop All-Star exhibitions: keep teams with a real schedule that season
counts = tb.groupby(["season", "team_id"]).size()
real = counts[counts >= 20].reset_index()[["season", "team_id"]]
# merge twice: once to check the team is real, once to check the opponent is real
tb = tb.merge(real, on=["season", "team_id"]).merge(
    real.rename(columns={"team_id": "opponent_team_id"}), on=["season", "opponent_team_id"])
tb["game_date"] = pd.to_datetime(tb.game_date)
tb = tb.sort_values(["game_date", "game_id"]).reset_index(drop=True)  # Elo needs date order

# --- Elo ----------------------------------------------------------------------
# run Elo over every game since 2003 (see elo.py for how it works)
elo_log = elo.compute(tb)
NEW_TEAM = elo.NEW_TEAM

# Elo path of each expansion team through its first regular season
elo_paths = {}
for key, tid, season, _ in CLASS:
    e = elo_log[(elo_log.team_id == tid) & (elo_log.season == season) & (elo_log.season_type == "2")]
    # start the line at 1300 (before game 1), then add the rating after every game
    elo_paths[key] = [round(NEW_TEAM)] + e.post.round(1).tolist()

# the two turning points on the Elo chart, worked out from each team's results
def results(tid, season):
    # one row per regular-season game in date order: win (1/0) and final margin
    r = tb[(tb.team_id == tid) & (tb.season == season) & (tb.season_type == "2")]
    return pd.DataFrame({"w": (r.team_score > r.opponent_team_score).astype(int).to_numpy(),
                         "mar": (r.team_score - r.opponent_team_score).to_numpy()})


gs_r, tor_r = results(129689, 2025), results(131935, 2026)
# 1) the stretch where Golden State pulled away: its best 9-game run by total margin
best = int(gs_r.mar.rolling(9).sum().idxmax())  # last game of that run (0-based)
run = gs_r.iloc[best - 8:best + 1]
# 2) Toronto's peak Elo, and its record before and after that game
peak = int(np.argmax(elo_paths["TOR"]))  # games played when the rating peaked
before, after = tor_r.iloc[:peak], tor_r.iloc[peak:]
turns = {"gs": {"from": best - 7, "to": best + 1, "w": int(run.w.sum()), "l": int(9 - run.w.sum()),
                "mar": round(float(run.mar.mean()), 1), "big": int((run.mar >= 20).sum())},
         "tor": {"peak": peak, "elo": round(elo_paths["TOR"][peak]), "w1": int(before.w.sum()), "l1": int(len(before) - before.w.sum()),
                 "w2": int(after.w.sum()), "l2": int(len(after) - after.w.sum()),
                 "m1": round(float(before.mar.mean()), 1), "m2": round(float(after.mar.mean()), 1)}}
print("turning points", turns)

# end-of-2026 league table
names = tb.drop_duplicates("team_id", keep="last").set_index("team_id")
# each team's rating after its last 2026 game, best to worst
cur = elo_log[elo_log.season == 2026].groupby("team_id").post.last().sort_values(ascending=False)
elo_2026 = [{"team": names.loc[t, "team_display_name"], "abbr": names.loc[t, "team_abbreviation"],
             "elo": round(v)} for t, v in cur.items()]
# where each expansion team finished in Elo at the end of its first regular season (and its rank that year)
first_season_bar = {}
for key, tid, season, _ in CLASS:
    s = elo_log[(elo_log.season == season) & (elo_log.season_type == "2")]
    end = s.groupby("team_id").post.last()
    # rank = 1 + number of teams with a higher rating
    first_season_bar[key] = {"end": round(end[tid]), "rank": int((end > end[tid]).sum() + 1), "of": len(end)}

# --- ratings & four factors (league rank within own season) -------------------
def season_table(season):
    # every team's season totals for one season, turned into ratings and Four Factors
    t = tb[(tb.season == season) & (tb.season_type == "2")].copy()
    t["poss"] = possessions(t.field_goals_attempted, t.offensive_rebounds, t.total_turnovers, t.free_throws_attempted)
    # attach the opponent's numbers (prefix o_) to each team row
    opp = t[["game_id", "team_id", "poss", "field_goals_attempted", "field_goals_made", "three_point_field_goals_made",
             "free_throws_made", "offensive_rebounds", "defensive_rebounds", "total_turnovers"]].add_prefix("o_")
    t = t.merge(opp, left_on=["game_id", "opponent_team_id"], right_on=["o_game_id", "o_team_id"])
    # add up every game for each team
    s = t.groupby("team_id").sum(numeric_only=True)
    out = pd.DataFrame(index=s.index)
    out["gp"] = t.groupby("team_id").size()
    out["w"] = t.groupby("team_id").team_winner.sum()
    # offensive / defensive rating = points scored / allowed per 100 possessions
    out["ortg"] = 100 * s.team_score / s.poss
    out["drtg"] = 100 * s.opponent_team_score / s.o_poss
    out["net"] = out.ortg - out.drtg
    out["pace"] = (s.poss + s.o_poss) / 2 / out.gp  # possessions per game
    # the Four Factors on offense: shooting, turnovers, offensive rebounding, getting to the line
    out["efg"] = (s.field_goals_made + 0.5 * s.three_point_field_goals_made) / s.field_goals_attempted
    out["tov"] = s.total_turnovers / s.poss
    out["orb"] = s.offensive_rebounds / (s.offensive_rebounds + s.o_defensive_rebounds)
    out["ftr"] = s.free_throws_made / s.field_goals_attempted
    # and the same four on defense (what opponents did against this team)
    out["opp_efg"] = (s.o_field_goals_made + 0.5 * s.o_three_point_field_goals_made) / s.o_field_goals_attempted
    out["opp_tov"] = s.o_total_turnovers / s.o_poss
    out["drb"] = s.defensive_rebounds / (s.defensive_rebounds + s.o_offensive_rebounds)
    out["opp_ftr"] = s.o_free_throws_made / s.o_field_goals_attempted
    return out, t


# (stat, is higher better?) - used to rank teams 1 = best
METRICS = [("ortg", True), ("drtg", False), ("net", True), ("efg", True), ("tov", False), ("orb", True),
           ("ftr", True), ("opp_efg", False), ("opp_tov", True), ("drb", True), ("opp_ftr", False)]
fingerprint, rolling = {}, {}
for key, tid, season, _ in CLASS:
    tab, tg = season_table(season)
    r = tab.loc[tid]
    fingerprint[key] = {"teams": len(tab), "w": int(r.w), "l": int(r.gp - r.w), "pace": round(r.pace, 1)}
    for m, hib in METRICS:
        # rank this team against the rest of the league that season
        rank = tab[m].rank(ascending=not hib).loc[tid]
        fingerprint[key][m] = {"v": round(float(r[m]), 4), "rank": int(rank), "lg": round(float(tab[m].mean()), 4)}
    if (key, tid, season, _) in MODERN:
        # rolling 10-game net rating for the season arc chart
        d = tg[tg.team_id == tid].sort_values("game_date")
        pts, opp_pts = d.team_score.rolling(10).sum(), d.opponent_team_score.rolling(10).sum()
        net = 100 * pts / d.poss.rolling(10).sum() - 100 * opp_pts / d.o_poss.rolling(10).sum()
        # the first 9 games are NaN (not 10 games yet), JSON needs None instead
        rolling[key] = [None if np.isnan(v) else round(v, 1) for v in net]

# --- game logs, head-to-heads, clutch ------------------------------------------
pbp = read("pbp")
pbp = num(pbp, ["home_score", "away_score", "end_game_seconds_remaining", "home_team_id", "away_team_id", "game_play_number"])
pbp["season_type"] = pbp.season_type.astype(str)
pbp = pbp[pbp.season_type == "2"].sort_values(["game_id", "game_play_number"])

games_out, clutch = {}, {}
for key, tid, season, _ in MODERN:
    # simple game log: date, opponent, home/away and score for every game
    d = tb[(tb.team_id == tid) & (tb.season == season) & (tb.season_type == "2")].sort_values("game_date")
    gl = []
    for i, g in enumerate(d.itertuples(), 1):
        gl.append({"n": i, "date": g.game_date.strftime("%b %-d"), "opp": g.opponent_team_abbreviation,
                   "home": g.team_home_away == "home", "pf": int(g.team_score), "pa": int(g.opponent_team_score)})
    games_out[key] = gl
    # margin from this team's side for every play of the season
    p = pbp[(pbp.season == season) & ((pbp.home_team_id == tid) | (pbp.away_team_id == tid))].copy()
    p["m"] = np.where(p.home_team_id == tid, p.home_score - p.away_score, p.away_score - p.home_score)
    # clutch game = within 5 points at any moment in the last 5 minutes (300 seconds)
    late = p[p.end_game_seconds_remaining <= 300]
    ids = late[late.m.abs() <= 5].game_id.unique()
    fin = p.groupby("game_id").m.last()  # final margin of each game
    clutch[key] = {"w": int((fin.loc[ids] > 0).sum()), "l": int((fin.loc[ids] < 0).sum()),
                   # lost even though they led by 10+ at some point
                   "blown10": int(((p.groupby("game_id").m.max() >= 10) & (fin < 0)).sum()),
                   # won even though they trailed by 10+ at some point
                   "comeback10": int(((p.groupby("game_id").m.min() <= -10) & (fin > 0)).sum())}

# games in 2026 where two of the three new teams played each other
h2h = []
ids = {tid for _, tid, _, _ in MODERN}
for g in tb[(tb.season == 2026) & (tb.season_type == "2") & tb.team_id.isin(ids) & tb.opponent_team_id.isin(ids)
            & (tb.team_home_away == "home")].itertuples():
    h2h.append({"date": g.game_date.strftime("%b %-d"), "home": g.team_abbreviation, "away": g.opponent_team_abbreviation,
                "hs": int(g.team_score), "as": int(g.opponent_team_score)})

# --- hex shot maps --------------------------------------------------------------
# every field-goal attempt (free throws don't have a location that matters)
shots = pbp[pbp.shooting_play.astype(bool) & ~pbp.type_text.str.contains("Free Throw")].copy()
shots = num(shots, ["coordinate_x_raw", "coordinate_y_raw", "points_attempted", "team_id"])
# only half-court shots: x goes 0-50 ft across, y is feet from the basket
shots = shots[(shots.coordinate_y_raw <= 30) & shots.coordinate_x_raw.between(0, 50)]
shots["pts"] = np.where(shots.scoring_play.astype(bool), shots.points_attempted, 0)  # points scored on the shot
# distance and angle from the basket (the basket is at x = 25)
dx, y = shots.coordinate_x_raw - 25, shots.coordinate_y_raw
dist = np.hypot(dx, y)
ang = np.degrees(np.arctan2(y, dx))  # 0 = right baseline, 90 = straight on
three = shots.points_attempted == 3
# split the court into left / centre / right by angle
side = np.where(ang < 60, "R", np.where(ang > 120, "L", "C"))
# put every shot in a zone. np.select checks the conditions in order and uses the first one that's true
shots["zone"] = np.select(
    [dist < 4, (dist < 10) & ~three, ~three, three & (y <= 3)],
    ["Rim", "Short", "Mid " + pd.Series(side, index=shots.index), "Corner3 " + pd.Series(side, index=shots.index)],
    default="Arc3 " + pd.Series(side, index=shots.index))

# snap each shot to the centre of a hexagon so I can count shots per hex
R = 1.5  # hex radius in feet (pointy-top grid)
w_, h_ = np.sqrt(3) * R, 1.5 * R  # horizontal and vertical spacing between hex centres
row = np.round((shots.coordinate_y_raw + 5) / h_).astype(int)
# every other row is shifted half a hex to the right (that's how hex grids tile)
col = np.round((shots.coordinate_x_raw - (row % 2) * w_ / 2) / w_).astype(int)
shots["hx"] = (col * w_ + (row % 2) * w_ / 2).round(2)
shots["hy"] = (row * h_ - 5).round(2)

hexmaps = {}
for key, tid, season, _ in MODERN:
    s = shots[shots.season == season]
    in_game = (s.home_team_id == tid) | (s.away_team_id == tid)
    # league average for each zone in that season (to compare against)
    lg_zone = s.groupby("zone").pts.mean()
    lg_freq = s.groupby("zone").size() / len(s)
    hexmaps[key] = {}
    # "off" = this team's shots, "def" = opponents' shots against this team
    for side_name, sel in (("off", s.team_id == tid), ("def", in_game & (s.team_id != tid))):
        t = s[sel]
        # zone summary: attempts, points per shot, share of shots, and the difference vs league
        z = t.groupby("zone").agg(n=("pts", "size"), pps=("pts", "mean"))
        z["freq"] = z.n / z.n.sum()
        z["d_pps"] = z.pps - lg_zone.reindex(z.index)
        z["d_freq"] = z.freq - lg_freq.reindex(z.index)
        # hex counts (hexes with only 1 shot are dropped to keep the map clean)
        hx = t.groupby(["hx", "hy"]).agg(n=("pts", "size"), zone=("zone", "first")).reset_index()
        hx = hx[hx.n >= 2]
        hexmaps[key][side_name] = {
            "total": int(len(t)),
            "hexes": [[r.hx, r.hy, int(r.n), r.zone] for r in hx.itertuples()],
            "zones": {k: {"n": int(v.n), "pps": round(v.pps, 3), "d": round(v.d_pps, 3), "freq": round(v.freq, 3),
                          "dfreq": round(v.d_freq, 3)} for k, v in z.iterrows()},
        }

# --- roster experience & top players -----------------------------------------------
pb_hist = read("player_box_hist")
pb_now = read("player_box")
# every (player, season) where the player got real minutes, so I can count prior WNBA seasons
pb_all = pd.concat([pb_hist[["season", "athlete_id", "minutes"]], pb_now[["season", "athlete_id", "minutes"]]])
pb_all["minutes"] = pd.to_numeric(pb_all.minutes, errors="coerce")
played = pb_all[pb_all.minutes > 0].groupby(["athlete_id", "season"]).size().reset_index()[["athlete_id", "season"]]

pb_now = num(pb_now, ["minutes", "points", "field_goals_attempted", "free_throws_attempted", "turnovers",
                      "rebounds", "assists", "plus_minus"])
pb_now["season_type"] = pb_now.season_type.astype(str)
experience, players = {}, {}
for key, tid, season, _ in MODERN:  # box history starts 2003, too short for 2006/08 experience
    src = pb_now if season >= 2025 else pb_hist.assign(minutes=pd.to_numeric(pb_hist.minutes, errors="coerce"))
    src = src[(src.season == season) & (src.season_type.astype(str) == "2")]
    if season < 2025:
        src = src[src.team_abbreviation == key]
    else:
        src = src[src.team_id == tid]
    src = src[src.minutes.fillna(0) > 0]  # DNP rows would deflate per-game numbers
    # total minutes per player this season
    mins = src.groupby(["athlete_id", "athlete_display_name"]).minutes.sum().reset_index()
    # how many earlier WNBA seasons each player had played in
    prior = played[played.season < season].groupby("athlete_id").size()
    mins["exp"] = mins.athlete_id.map(prior).fillna(0).astype(int)
    # group into experience buckets and get each bucket's share of team minutes
    mins["bucket"] = pd.cut(mins.exp, [-1, 0, 2, 5, 99], labels=["Rookie", "1-2 yrs", "3-5 yrs", "6+ yrs"])
    share = mins.groupby("bucket", observed=False).minutes.sum() / mins.minutes.sum()
    experience[key] = {k: round(float(v), 3) for k, v in share.items()}
    # average experience, weighted by minutes (players who play more count more)
    experience[key]["avg_exp"] = round(float((mins.exp * mins.minutes).sum() / mins.minutes.sum()), 1)
    if season >= 2025:
        # the six players with the most minutes, with per-game numbers
        agg = src.groupby("athlete_display_name").agg(
            mins=("minutes", "sum"), pts=("points", "sum"), fga=("field_goals_attempted", "sum"),
            fta=("free_throws_attempted", "sum"), pm=("plus_minus", "sum"), gp=("game_id", "nunique"))
        agg = agg.sort_values("mins", ascending=False).head(6)
        exp_map = mins.set_index("athlete_display_name").exp
        players[key] = [{"name": n, "mpg": round(r.mins / r.gp, 1), "ppg": round(r.pts / r.gp, 1),
                         "ts": round(r.pts / (2 * (r.fga + 0.44 * r.fta)), 3), "pm40": round(40 * r.pm / r.mins, 1),
                         "exp": int(exp_map.get(n, 0))} for n, r in agg.iterrows()]

# logos are put straight into the page as base64 text so the page works on its own
logos = {k: "data:image/png;base64," + base64.b64encode((OUT.parent / "assets" / "logos" / f"{k.lower()}_sm.png").read_bytes()).decode()
         for k, *_ in CLASS}

# everything the page needs, in one dictionary
data = {
    "logos": logos,
    "class": [{"key": k, "season": s, "name": n} for k, _, s, n in CLASS],
    "elo": {"paths": elo_paths, "table2026": elo_2026, "end": first_season_bar,
            "params": elo.PARAMS, "turns": turns},
    "fingerprint": fingerprint, "rolling": rolling, "games": games_out, "h2h": h2h, "clutch": clutch,
    "hex": hexmaps, "hex_r": R, "experience": experience, "players": players,
}
# a few headline numbers for the home page
lab.summary("expansion-class", {"tor_elo": first_season_bar["TOR"]["end"], "por_elo": first_season_bar["POR"]["end"],
                                "gs_elo": first_season_bar["GS"]["end"], "tor_def_rank": fingerprint["TOR"]["drtg"]["rank"]})
payload = json.dumps(data, separators=(",", ":"))
(OUT / "expansion.json").write_text(payload)
# put the data where page.html says /*DATA*/, then add the shared site head and nav bar
page = (OUT / "page.html").read_text().replace("/*DATA*/", payload.replace("</", "<\\/"))
standalone = page.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
style, rest = standalone.split("</style>", 1)
style = style.replace("<title>The Expansion Class</title>\n", "")  # lab.head() adds its own title
html = (lab.head("The Expansion Class", "Valkyries 2025, Tempo 2026 and Fire 2026 compared through Elo, Four Factors, shot maps and roster-building.")
        + style + "</style>\n</head>\n<body>\n" + rest.replace('<div class="wrap">', '<div class="wrap">\n' + lab.nav("expansion-class"), 1)
        .replace("</script>\n", "</script>\n", 1) + "</body>\n</html>\n")
out = lab.DOCS / "expansion-class" / "index.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(lab.versioned(html))
# print some numbers so I can sanity check them in the terminal
print("wrote", OUT / "expansion.json", round((OUT / "expansion.json").stat().st_size / 1024), "KB")
print(json.dumps({k: data["fingerprint"][k]["net"] | {"w": data["fingerprint"][k]["w"]} for k in data["fingerprint"]}, indent=0))
print(json.dumps(first_season_bar), json.dumps(clutch), json.dumps(experience), sep="\n")
print(h2h)
print(elo_2026)
