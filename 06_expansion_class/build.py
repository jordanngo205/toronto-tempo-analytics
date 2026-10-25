"""Project 6 - The Expansion Class.

Builds expansion.json for the interactive page (index.html): Golden State 2025,
Toronto 2026 and Portland 2026, with Chicago 2006 and Atlanta 2008 as the
historical bar. Pieces:
  * Elo ratings for every WNBA game 2003-2026 (538-style, new teams start at 1300)
  * league-rank fingerprint on ratings and Four Factors
  * hex shot maps (size = shot frequency, colour = zone efficiency vs league)
  * roster experience, head-to-heads, clutch, top players
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RAW, possessions

OUT = Path(__file__).parent
CLASS = [  # key, team_id, season, label
    ("GS", 129689, 2025, "Golden State Valkyries"),
    ("TOR", 131935, 2026, "Toronto Tempo"),
    ("POR", 132052, 2026, "Portland Fire"),
    ("CHI", 19, 2006, "Chicago Sky"),
    ("ATL", 20, 2008, "Atlanta Dream"),
]
MODERN = CLASS[:3]


def read(name):
    return pq.read_table(RAW / f"{name}.parquet").to_pandas(ignore_metadata=True)


def num(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# --- all games ----------------------------------------------------------------
tb = pd.concat([read("team_box_hist"), read("team_box")], ignore_index=True)
tb["season_type"] = tb.season_type.astype(str)
tb = num(tb, ["team_score", "opponent_team_score", "field_goals_attempted", "field_goals_made",
              "three_point_field_goals_made", "free_throws_attempted", "free_throws_made",
              "offensive_rebounds", "defensive_rebounds", "total_turnovers", "points_in_paint"])
# drop All-Star exhibitions: keep teams with a real schedule that season
counts = tb.groupby(["season", "team_id"]).size()
real = counts[counts >= 20].reset_index()[["season", "team_id"]]
tb = tb.merge(real, on=["season", "team_id"]).merge(
    real.rename(columns={"team_id": "opponent_team_id"}), on=["season", "opponent_team_id"])
tb["game_date"] = pd.to_datetime(tb.game_date)
tb = tb.sort_values(["game_date", "game_id"]).reset_index(drop=True)

# --- Elo ----------------------------------------------------------------------
K, HCA, NEW_TEAM, MEAN, CARRY = 20, 80, 1300, 1500, 0.75
elo, last_season = {}, {}
games = tb[tb.team_home_away == "home"]
rows = []
for g in games.itertuples():
    h, a = g.team_id, g.opponent_team_id
    for t in (h, a):
        if t not in elo:
            elo[t] = NEW_TEAM if g.season > 2003 else MEAN
        elif last_season[t] != g.season:
            elo[t] = CARRY * elo[t] + (1 - CARRY) * MEAN
        last_season[t] = g.season
    diff = elo[h] + HCA - elo[a]
    p_home = 1 / (1 + 10 ** (-diff / 400))
    mov = g.team_score - g.opponent_team_score
    win_diff = diff if mov > 0 else -diff
    mult = ((abs(mov) + 3) ** 0.8) / (7.5 + 0.006 * win_diff)
    shift = K * mult * ((mov > 0) - p_home)
    rows += [(g.game_id, h, g.season, g.season_type, elo[h], elo[h] + shift, p_home),
             (g.game_id, a, g.season, g.season_type, elo[a], elo[a] - shift, 1 - p_home)]
    elo[h] += shift
    elo[a] -= shift
elo_log = pd.DataFrame(rows, columns=["game_id", "team_id", "season", "season_type", "pre", "post", "p_win"])

# Elo path of each expansion team through its first regular season
elo_paths = {}
for key, tid, season, _ in CLASS:
    e = elo_log[(elo_log.team_id == tid) & (elo_log.season == season) & (elo_log.season_type == "2")]
    elo_paths[key] = [round(NEW_TEAM)] + e.post.round(1).tolist()

# end-of-2026 league table
names = tb.drop_duplicates("team_id", keep="last").set_index("team_id")
cur = elo_log[elo_log.season == 2026].groupby("team_id").post.last().sort_values(ascending=False)
elo_2026 = [{"team": names.loc[t, "team_display_name"], "abbr": names.loc[t, "team_abbreviation"],
             "elo": round(v)} for t, v in cur.items()]
# the 2025 Valkyries' path for reference, plus where all 2026 teams stood
first_season_bar = {}
for key, tid, season, _ in CLASS:
    s = elo_log[(elo_log.season == season) & (elo_log.season_type == "2")]
    end = s.groupby("team_id").post.last()
    first_season_bar[key] = {"end": round(end[tid]), "rank": int((end > end[tid]).sum() + 1), "of": len(end)}

# --- ratings & four factors (league rank within own season) -------------------
def season_table(season):
    t = tb[(tb.season == season) & (tb.season_type == "2")].copy()
    t["poss"] = possessions(t.field_goals_attempted, t.offensive_rebounds, t.total_turnovers, t.free_throws_attempted)
    opp = t[["game_id", "team_id", "poss", "field_goals_attempted", "field_goals_made", "three_point_field_goals_made",
             "free_throws_made", "offensive_rebounds", "defensive_rebounds", "total_turnovers"]].add_prefix("o_")
    t = t.merge(opp, left_on=["game_id", "opponent_team_id"], right_on=["o_game_id", "o_team_id"])
    s = t.groupby("team_id").sum(numeric_only=True)
    out = pd.DataFrame(index=s.index)
    out["gp"] = t.groupby("team_id").size()
    out["w"] = t.groupby("team_id").team_winner.sum()
    out["ortg"] = 100 * s.team_score / s.poss
    out["drtg"] = 100 * s.opponent_team_score / s.o_poss
    out["net"] = out.ortg - out.drtg
    out["pace"] = (s.poss + s.o_poss) / 2 / out.gp
    out["efg"] = (s.field_goals_made + 0.5 * s.three_point_field_goals_made) / s.field_goals_attempted
    out["tov"] = s.total_turnovers / s.poss
    out["orb"] = s.offensive_rebounds / (s.offensive_rebounds + s.o_defensive_rebounds)
    out["ftr"] = s.free_throws_made / s.field_goals_attempted
    out["opp_efg"] = (s.o_field_goals_made + 0.5 * s.o_three_point_field_goals_made) / s.o_field_goals_attempted
    out["opp_tov"] = s.o_total_turnovers / s.o_poss
    out["drb"] = s.defensive_rebounds / (s.defensive_rebounds + s.o_offensive_rebounds)
    out["opp_ftr"] = s.o_free_throws_made / s.o_field_goals_attempted
    return out, t


METRICS = [("ortg", True), ("drtg", False), ("net", True), ("efg", True), ("tov", False), ("orb", True),
           ("ftr", True), ("opp_efg", False), ("opp_tov", True), ("drb", True), ("opp_ftr", False)]
fingerprint, rolling = {}, {}
for key, tid, season, _ in CLASS:
    tab, tg = season_table(season)
    r = tab.loc[tid]
    fingerprint[key] = {"teams": len(tab), "w": int(r.w), "l": int(r.gp - r.w), "pace": round(r.pace, 1)}
    for m, hib in METRICS:
        rank = tab[m].rank(ascending=not hib).loc[tid]
        fingerprint[key][m] = {"v": round(float(r[m]), 4), "rank": int(rank), "lg": round(float(tab[m].mean()), 4)}
    if (key, tid, season, _) in MODERN:
        d = tg[tg.team_id == tid].sort_values("game_date")
        pts, opp_pts = d.team_score.rolling(10).sum(), d.opponent_team_score.rolling(10).sum()
        net = 100 * pts / d.poss.rolling(10).sum() - 100 * opp_pts / d.o_poss.rolling(10).sum()
        rolling[key] = [None if np.isnan(v) else round(v, 1) for v in net]

# --- game logs, head-to-heads, clutch ------------------------------------------
pbp = read("pbp")
pbp = num(pbp, ["home_score", "away_score", "end_game_seconds_remaining", "home_team_id", "away_team_id", "game_play_number"])
pbp["season_type"] = pbp.season_type.astype(str)
pbp = pbp[pbp.season_type == "2"].sort_values(["game_id", "game_play_number"])

games_out, clutch = {}, {}
for key, tid, season, _ in MODERN:
    d = tb[(tb.team_id == tid) & (tb.season == season) & (tb.season_type == "2")].sort_values("game_date")
    gl = []
    for i, g in enumerate(d.itertuples(), 1):
        gl.append({"n": i, "date": g.game_date.strftime("%b %-d"), "opp": g.opponent_team_abbreviation,
                   "home": g.team_home_away == "home", "pf": int(g.team_score), "pa": int(g.opponent_team_score)})
    games_out[key] = gl
    p = pbp[(pbp.season == season) & ((pbp.home_team_id == tid) | (pbp.away_team_id == tid))].copy()
    p["m"] = np.where(p.home_team_id == tid, p.home_score - p.away_score, p.away_score - p.home_score)
    late = p[p.end_game_seconds_remaining <= 300]
    ids = late[late.m.abs() <= 5].game_id.unique()
    fin = p.groupby("game_id").m.last()
    clutch[key] = {"w": int((fin.loc[ids] > 0).sum()), "l": int((fin.loc[ids] < 0).sum()),
                   "blown10": int(((p.groupby("game_id").m.max() >= 10) & (fin < 0)).sum()),
                   "comeback10": int(((p.groupby("game_id").m.min() <= -10) & (fin > 0)).sum())}

h2h = []
ids = {tid for _, tid, _, _ in MODERN}
for g in tb[(tb.season == 2026) & (tb.season_type == "2") & tb.team_id.isin(ids) & tb.opponent_team_id.isin(ids)
            & (tb.team_home_away == "home")].itertuples():
    h2h.append({"date": g.game_date.strftime("%b %-d"), "home": g.team_abbreviation, "away": g.opponent_team_abbreviation,
                "hs": int(g.team_score), "as": int(g.opponent_team_score)})

# --- hex shot maps --------------------------------------------------------------
shots = pbp[pbp.shooting_play.astype(bool) & ~pbp.type_text.str.contains("Free Throw")].copy()
shots = num(shots, ["coordinate_x_raw", "coordinate_y_raw", "points_attempted", "team_id"])
shots = shots[(shots.coordinate_y_raw <= 30) & shots.coordinate_x_raw.between(0, 50)]
shots["pts"] = np.where(shots.scoring_play.astype(bool), shots.points_attempted, 0)
dx, y = shots.coordinate_x_raw - 25, shots.coordinate_y_raw
dist = np.hypot(dx, y)
ang = np.degrees(np.arctan2(y, dx))  # 0 = right baseline, 90 = straight on
three = shots.points_attempted == 3
side = np.where(ang < 60, "R", np.where(ang > 120, "L", "C"))
shots["zone"] = np.select(
    [dist < 4, (dist < 10) & ~three, ~three, three & (y <= 3)],
    ["Rim", "Short", "Mid " + pd.Series(side, index=shots.index), "Corner3 " + pd.Series(side, index=shots.index)],
    default="Arc3 " + pd.Series(side, index=shots.index))

R = 1.5  # hex radius in feet (pointy-top grid)
w_, h_ = np.sqrt(3) * R, 1.5 * R
row = np.round((shots.coordinate_y_raw + 5) / h_).astype(int)
col = np.round((shots.coordinate_x_raw - (row % 2) * w_ / 2) / w_).astype(int)
shots["hx"] = (col * w_ + (row % 2) * w_ / 2).round(2)
shots["hy"] = (row * h_ - 5).round(2)

hexmaps = {}
for key, tid, season, _ in MODERN:
    s = shots[shots.season == season]
    in_game = (s.home_team_id == tid) | (s.away_team_id == tid)
    lg_zone = s.groupby("zone").pts.mean()
    lg_freq = s.groupby("zone").size() / len(s)
    hexmaps[key] = {}
    for side_name, sel in (("off", s.team_id == tid), ("def", in_game & (s.team_id != tid))):
        t = s[sel]
        z = t.groupby("zone").agg(n=("pts", "size"), pps=("pts", "mean"))
        z["freq"] = z.n / z.n.sum()
        z["d_pps"] = z.pps - lg_zone.reindex(z.index)
        z["d_freq"] = z.freq - lg_freq.reindex(z.index)
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
    mins = src.groupby(["athlete_id", "athlete_display_name"]).minutes.sum().reset_index()
    prior = played[played.season < season].groupby("athlete_id").size()
    mins["exp"] = mins.athlete_id.map(prior).fillna(0).astype(int)
    mins["bucket"] = pd.cut(mins.exp, [-1, 0, 2, 5, 99], labels=["Rookie", "1-2 yrs", "3-5 yrs", "6+ yrs"])
    share = mins.groupby("bucket", observed=False).minutes.sum() / mins.minutes.sum()
    experience[key] = {k: round(float(v), 3) for k, v in share.items()}
    experience[key]["avg_exp"] = round(float((mins.exp * mins.minutes).sum() / mins.minutes.sum()), 1)
    if season >= 2025:
        agg = src.groupby("athlete_display_name").agg(
            mins=("minutes", "sum"), pts=("points", "sum"), fga=("field_goals_attempted", "sum"),
            fta=("free_throws_attempted", "sum"), pm=("plus_minus", "sum"), gp=("game_id", "nunique"))
        agg = agg.sort_values("mins", ascending=False).head(6)
        exp_map = mins.set_index("athlete_display_name").exp
        players[key] = [{"name": n, "mpg": round(r.mins / r.gp, 1), "ppg": round(r.pts / r.gp, 1),
                         "ts": round(r.pts / (2 * (r.fga + 0.44 * r.fta)), 3), "pm40": round(40 * r.pm / r.mins, 1),
                         "exp": int(exp_map.get(n, 0))} for n, r in agg.iterrows()]

data = {
    "class": [{"key": k, "season": s, "name": n} for k, _, s, n in CLASS],
    "elo": {"paths": elo_paths, "table2026": elo_2026, "end": first_season_bar,
            "params": {"K": K, "hca": HCA, "new_team": NEW_TEAM, "carry": CARRY}},
    "fingerprint": fingerprint, "rolling": rolling, "games": games_out, "h2h": h2h, "clutch": clutch,
    "hex": hexmaps, "hex_r": R, "experience": experience, "players": players,
}
payload = json.dumps(data, separators=(",", ":"))
(OUT / "expansion.json").write_text(payload)
page = (OUT / "page.html").read_text().replace("/*DATA*/", payload.replace("</", "<\\/"))
(OUT / "expansion_class.html").write_text(page)
docs = OUT.parent / "docs"  # GitHub Pages
docs.mkdir(exist_ok=True)
standalone = page.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Valkyries 2025, Tempo 2026 and Fire 2026 compared through Elo, Four Factors, shot maps and roster-building.">\n')
standalone = head + standalone.replace("</style>", "</style>\n</head>\n<body>", 1) + "</body>\n</html>\n"
(docs / "index.html").write_text(standalone)
print("wrote", OUT / "expansion.json", round((OUT / "expansion.json").stat().st_size / 1024), "KB")
print(json.dumps({k: data["fingerprint"][k]["net"] | {"w": data["fingerprint"][k]["w"]} for k in data["fingerprint"]}, indent=0))
print(json.dumps(first_season_bar), json.dumps(clutch), json.dumps(experience), sep="\n")
print(h2h)
print(elo_2026)
