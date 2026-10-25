"""Project 6 - Draft Lab (interactive): who should the Tempo draft in 2027?

Writes docs/draft-lab/index.html. Three parts:
  1. What Toronto needs: where the 2026 Tempo ranked on defense, rebounding and rim protection
  2. What translates: for every WNBA draftee 2018-2025, which college numbers predicted
     WNBA minutes in their first two seasons (beyond what the draft slot already says)
  3. The board: every 2026-27 college senior, scored on talent (my model + sportsdataverse's
     draft projection) and on fit (does she fix what Toronto needs?)
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# let this file import lab.py and common.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
from common import RAW, load, possessions

TOR = 131935


def read(name):
    # load a parquet file from data/raw with plain pandas columns
    return pq.read_table(RAW / f"{name}.parquet").to_pandas(ignore_metadata=True)


def inches(h):
    # "6'4\"" -> 76 inches. Returns NaN if the height is missing or written differently
    m = re.match(r"(\d+)'\s*(\d+)", str(h))
    return int(m.group(1)) * 12 + int(m.group(2)) if m else np.nan


def z(s):
    # z-score: how many standard deviations above/below average (so different stats can be added up)
    return (s - s.mean()) / s.std()


# ---------------------------------------------------------------------------
# 1. What Toronto needs (2026 WNBA team numbers, ranked 1 = best)
# ---------------------------------------------------------------------------
t = load("team_box", 2026).copy()
for c in ["field_goals_attempted", "field_goals_made", "three_point_field_goals_made", "offensive_rebounds",
          "defensive_rebounds", "total_turnovers", "free_throws_attempted", "blocks", "steals", "team_score",
          "opponent_team_score"]:
    t[c] = pd.to_numeric(t[c], errors="coerce")
t["poss"] = possessions(t.field_goals_attempted, t.offensive_rebounds, t.total_turnovers, t.free_throws_attempted)
# attach each opponent's numbers to the team's row (prefix o_)
o = t[["game_id", "team_id", "poss", "field_goals_attempted", "field_goals_made", "three_point_field_goals_made",
       "offensive_rebounds", "total_turnovers"]].add_prefix("o_")
t = t.merge(o, left_on=["game_id", "opponent_team_id"], right_on=["o_game_id", "o_team_id"])
s = t.groupby("team_abbreviation").sum(numeric_only=True)
s = s[t.groupby("team_abbreviation").size() >= 30]  # drop the All-Star teams

# share of opponent shots that came at the rim (from the play-by-play shot locations)
pbp = load("pbp", 2026)
sh = pbp[pbp.shooting_play.astype(bool) & ~pbp.type_text.str.contains("Free Throw")].copy()
sh["rim"] = np.hypot(sh.coordinate_x_raw.astype(float) - 25, sh.coordinate_y_raw.astype(float)) < 4
abbr = t.drop_duplicates("team_id").set_index("team_id").team_abbreviation
sh["def_team"] = np.where(sh.team_id == sh.home_team_id, sh.away_team_id, sh.home_team_id)  # the team defending the shot
sh["def_abbr"] = sh.def_team.map(abbr)
opp_rim = sh.groupby("def_abbr").rim.mean()

# (key, label, value per team, is higher better?)
NEEDS = [
    ("drtg", "Defensive rating", 100 * s.opponent_team_score / s.o_poss, False),
    ("opp_efg", "Opponent eFG%", (s.o_field_goals_made + 0.5 * s.o_three_point_field_goals_made) / s.o_field_goals_attempted, False),
    ("opp_rim", "Opponent shots at the rim", opp_rim.reindex(s.index), False),
    ("drb", "Defensive rebound %", s.defensive_rebounds / (s.defensive_rebounds + s.o_offensive_rebounds), True),
    ("blk", "Blocks per 100 possessions", 100 * s.blocks / s.o_poss, True),
    ("stl", "Steals per 100 possessions", 100 * s.steals / s.o_poss, True),
    ("ortg", "Offensive rating", 100 * s.team_score / s.poss, True),
    ("efg", "eFG%", (s.field_goals_made + 0.5 * s.three_point_field_goals_made) / s.field_goals_attempted, True),
]
needs = []
for key, label, vals, hib in NEEDS:
    rank = vals.rank(ascending=not hib)
    needs.append({"key": key, "label": label, "v": round(float(vals["TOR"]), 4), "rank": int(rank["TOR"]),
                  "teams": int(vals.notna().sum()), "lg": round(float(vals.mean()), 4), "pct": key in ("opp_efg", "opp_rim", "drb", "efg")})

# ---------------------------------------------------------------------------
# 2. College seasons, per 40 minutes
# ---------------------------------------------------------------------------
cs = read("wbb_player_seasons")
cs["athlete_id"] = cs.athlete_id.astype(str)
val = read("wbb_player_value")
val["player_id"] = val.player_id.astype(str)
# box plus-minus for each player-season (OBPM = offense, DBPM = defense)
cs = cs.merge(val[["player_id", "season", "box_bpm", "box_obpm", "box_dbpm"]],
              left_on=["athlete_id", "season"], right_on=["player_id", "season"], how="left")
m40 = 40 / cs.minutes
for col, src in [("pts40", "points"), ("reb40", "rebounds"), ("dreb40", "defensive_rebounds"), ("oreb40", "offensive_rebounds"),
                 ("ast40", "assists"), ("stl40", "steals"), ("blk40", "blocks"), ("tov40", "turnovers")]:
    cs[col] = cs[src] * m40
cs["ts"] = cs.points / (2 * (cs.field_goals_attempted + 0.44 * cs.free_throws_attempted))  # true shooting %
cs["three_rate"] = cs.three_point_field_goals_attempted / cs.field_goals_attempted       # share of shots that are 3s
cs["mpg"] = cs.minutes / cs.gp

FEATURES = ["box_bpm", "box_obpm", "box_dbpm", "pts40", "reb40", "ast40", "stl40", "blk40", "tov40", "ts", "three_rate", "height"]
LABELS = {"box_bpm": "Box plus-minus", "box_obpm": "Offensive BPM", "box_dbpm": "Defensive BPM", "pts40": "Points / 40",
          "reb40": "Rebounds / 40", "ast40": "Assists / 40", "stl40": "Steals / 40", "blk40": "Blocks / 40",
          "tov40": "Turnovers / 40", "ts": "True shooting %", "three_rate": "3-point attempt rate", "height": "Height"}

# ---------------------------------------------------------------------------
# 3. History: every draftee 2018-2025 -> did she get WNBA minutes?
# ---------------------------------------------------------------------------
dr = read("wnba_draft")
dr = dr[dr.season.between(2018, 2025)].copy()
# ESPN uses the same athlete id in college and the WNBA. In this table it's inside the player's link (".../id/3149391/...")
dr["athlete_id"] = dr.link_web.astype(str).str.extract(r"/id/(\d+)")[0]
dr["height"] = dr.athlete_height.map(inches)

# WNBA minutes per player per season, 2003-2026
wn = pd.concat([read("player_box_hist")[["season", "athlete_id", "minutes"]], read("player_box")[["season", "athlete_id", "minutes"]]])
wn["minutes"] = pd.to_numeric(wn.minutes, errors="coerce").fillna(0)
wn["athlete_id"] = wn.athlete_id.astype(str)
wmin = wn.groupby(["athlete_id", "season"]).minutes.sum()

rows = []
for d in dr.itertuples():
    # her last college season before the draft, with real minutes
    c = cs[(cs.athlete_id == d.athlete_id) & (cs.season <= d.season) & (cs.minutes >= 300)].sort_values("season")
    if c.empty:
        continue
    c = c.iloc[-1]
    # outcome: total WNBA minutes in the draft year and the year after
    pro = sum(wmin.get((d.athlete_id, yr), 0) for yr in (d.season, d.season + 1))
    rows.append({"name": d.athlete_display_name, "year": int(d.season), "pick": int(d.overall_pick), "rd": int(d.round_number), "pro_min": float(pro),
                 "height": d.height, **{f: c[f] for f in FEATURES if f != "height"}})
hist = pd.DataFrame(rows).dropna(subset=["box_bpm"])
hist["log_pick"] = np.log(hist.pick)
hist["sqrt_min"] = np.sqrt(hist.pro_min)  # square root so a few huge-minute stars don't dominate

# how much of WNBA minutes the draft slot alone explains (a straight line on log(pick))
A = np.c_[np.ones(len(hist)), hist.log_pick]
coef_pick = np.linalg.lstsq(A, hist.sqrt_min, rcond=None)[0]
hist["resid"] = hist.sqrt_min - A @ coef_pick  # positive = played more than her draft slot predicted

# correlation of each college number with (a) WNBA minutes and (b) minutes beyond the draft slot
translate = []
for f in FEATURES:
    ok = hist[f].notna()
    translate.append({"f": f, "label": LABELS[f],
                      "r_min": round(float(np.corrcoef(hist.loc[ok, f], hist.loc[ok, "sqrt_min"])[0, 1]), 3),
                      "r_resid": round(float(np.corrcoef(hist.loc[ok, f], hist.loc[ok, "resid"])[0, 1]), 3)})

# my talent model: ridge regression from college numbers to sqrt(WNBA minutes)
MODEL_F = ["box_bpm", "box_dbpm", "pts40", "reb40", "ast40", "stl40", "blk40", "ts", "height"]
train = hist.dropna(subset=MODEL_F)
mu, sd = train[MODEL_F].mean(), train[MODEL_F].std()
X = np.c_[np.ones(len(train)), (train[MODEL_F] - mu) / sd]
lam = 5.0  # ridge penalty: keeps the weights small so the model doesn't overfit ~300 players
I = np.eye(X.shape[1]); I[0, 0] = 0  # don't shrink the intercept
beta = np.linalg.solve(X.T @ X + lam * I, X.T @ train.sqrt_min)
pred_hist = X @ beta
model_r = float(np.corrcoef(pred_hist, train.sqrt_min)[0, 1])  # how well it fits the history


# ---------------------------------------------------------------------------
# 3b. How accurate is it? Test on draft classes the model has never seen
# ---------------------------------------------------------------------------
# "Leave one year out": hide one draft class, train on the other 7, predict the hidden one.
# Repeat for every year. This is a fair test because the model never saw the answers.
def ridge_predict(tr, te, cols):
    m_, s_ = tr[cols].mean(), tr[cols].std()
    Xtr = np.c_[np.ones(len(tr)), (tr[cols] - m_) / s_]
    Ii = np.eye(Xtr.shape[1]); Ii[0, 0] = 0
    b_ = np.linalg.solve(Xtr.T @ Xtr + lam * Ii, Xtr.T @ tr.sqrt_min)
    return np.c_[np.ones(len(te)), (te[cols] - m_) / s_] @ b_


cv = []
for yr in sorted(train.year.unique()):
    tr, te = train[train.year != yr], train[train.year == yr]
    cv.append(pd.DataFrame({
        "name": te.name, "year": yr, "pick": te.pick, "rd": te.rd, "actual": te.pro_min,
        "college": ridge_predict(tr, te, MODEL_F),               # my model: college stats only
        "slot": ridge_predict(tr, te, ["log_pick"]),             # draft slot only
        "both": ridge_predict(tr, te, MODEL_F + ["log_pick"]),   # college stats + draft slot
    }))
cv = pd.concat(cv, ignore_index=True)
cv["y"] = np.sqrt(cv.actual)


def r_of(col, d=cv):
    # correlation between a prediction and what really happened
    return round(float(np.corrcoef(d[col], d.y)[0, 1]), 3)


first = cv[cv.rd == 1]  # first-round picks only (where Toronto will be picking)
# top 5 of each class by the model vs everyone: how many became rotation players (500+ min in 2 seasons)?
top5 = cv.sort_values("college", ascending=False).groupby("year").head(5)
rot = lambda d: round(float((d.actual >= 500).mean()), 3)
# hit rate by model rank group within each class (1-5, 6-10, 11-20, 21+)
cv["mrank"] = cv.groupby("year").college.rank(ascending=False)
tiers = []
for lo_, hi_, lab_ in [(1, 5, "Model's top 5"), (6, 10, "6-10"), (11, 20, "11-20"), (21, 99, "21+")]:
    d = cv[cv.mrank.between(lo_, hi_)]
    tiers.append({"label": lab_, "n": int(len(d)), "hit": rot(d)})
validation = {
    "n": int(len(cv)), "classes": int(cv.year.nunique()),
    "r": {"college": r_of("college"), "slot": r_of("slot"), "both": r_of("both")},
    "first": {"n": int(len(first)), "college": r_of("college", first), "slot": r_of("slot", first)},
    "top5": {"n": int(len(top5)), "hit": rot(top5)}, "all_hit": rot(cv), "tiers": tiers,
    # every past draftee: [name, year, pick, predicted minutes, actual minutes]
    "pts": [[r_["name"], int(r_.year), int(r_.pick), int(max(r_.college, 0) ** 2), int(r_.actual)] for _, r_ in cv.iterrows()],
}

# ---------------------------------------------------------------------------
# 4. The 2027 board: the 2026-27 senior class
# ---------------------------------------------------------------------------
# The roster files don't have up-to-date class years, so I work it out from each player's own
# college history: if her first college season was 2023-24 (season 2024), then 2026-27 is her
# senior year and she's in the 2027 draft class.
first = cs[cs.minutes > 0].groupby("athlete_id").season.min()
ro = read("wbb_rosters")
ro["athlete_id"] = ro.athlete_id.astype(str)
info = ro[ro.season == 2026].drop_duplicates("athlete_id").set_index("athlete_id")
# anyone who already went in the 2026 draft (early entrants / international) is off the board
gone = set(read("wnba_draft_2026").athlete_uid.astype(str).str.extract(r"a:(\d+)")[0].dropna())
# their most recent full season: 2025-26 if they played 400+ minutes, otherwise 2024-25.
# The 2024-25 fallback is only for players still on a 2025-26 college roster (someone who sat out
# 2025-26, like JuJu Watkins), so players who left college don't sneak back in.
cand = cs[cs.season.isin([2025, 2026]) & (cs.minutes >= 400) & (cs.athlete_id.map(first) == 2024) & ~cs.athlete_id.isin(gone)]
cand = cand[(cand.season == 2026) | cand.athlete_id.isin(info.index)]
pool = cand.sort_values("season").groupby("athlete_id").tail(1).copy()  # keep the latest season per player
pool["height"] = pool.athlete_id.map(info.height).map(inches)  # roster height is text like 6' 2", turn it into inches
# a few players have no height listed: give them the typical height for their position
pool["height"] = pool.height.fillna(pool.groupby("pos").height.transform("median")).fillna(pool.height.median())
pool["school"] = pool.athlete_id.map(info.team_display_name).fillna(pool.team)
pool["school_logo"] = pool.athlete_id.map(info.team_logo)
pool["headshot"] = pool.athlete_id.map(info.headshot_href)
pool["pos"] = pool.athlete_id.map(info.position_abbreviation).fillna(pool.pos)
pool = pool.dropna(subset=MODEL_F)

# sportsdataverse's draft model (based on the same 2025-26 numbers)
proj = read("wbb_draft_projection")
proj["player_id"] = proj.player_id.astype(str)
pool = pool.merge(proj[["player_id", "draft_prob", "projected_pick"]], left_on="athlete_id", right_on="player_id", how="left", suffixes=("", "_p"))
# sportsdataverse only projects players from their 2025-26 numbers, so anyone using a 2024-25 season has no projection
pool.loc[pool.season != 2026, ["draft_prob", "projected_pick"]] = np.nan

# talent = my model's projected WNBA minutes, mixed 50/50 with sportsdataverse's draft probability
Xp = np.c_[np.ones(len(pool)), (pool[MODEL_F] - mu) / sd]
pool["proj_min"] = np.clip(Xp @ beta, 0, None) ** 2   # undo the square root -> minutes in first two seasons
# talent = half my model, half sportsdataverse's draft probability, each as a percentile rank (0 to 1).
# Ranks, not z-scores: draft probabilities are very skewed (most near 0%, a few above 70%), and a z-score
# of a skewed number lets one input swamp the other. Players without a projection use my model's rank only.
model_rank = np.sqrt(pool.proj_min).rank(pct=True)
has_dp = pool.draft_prob.notna()
dp_rank = pool.draft_prob.rank(pct=True)  # NaN for players without a projection
pool["talent"] = np.where(has_dp, 0.5 * model_rank + 0.5 * dp_rank, model_rank)
# fit = fixes Toronto's weak spots: rim protection, defensive rebounding, defense in general, size, steals
pool["dreb40"] = pool.dreb40
pool["fit"] = (z(pool.blk40) + z(pool.dreb40) + z(pool.box_dbpm) + z(pool.height) + 0.5 * z(pool.stl40)) / 4.5
# scores on a 0-100 scale (percentile among all eligible seniors) so they're easy to read
pool["talent_pct"] = pool.talent.rank(pct=True) * 100
pool["fit_pct"] = pool.fit.rank(pct=True) * 100
# rank within the class (1 = best) for the talent-vs-fit chart, which uses a log scale so the top spreads out
pool["talent_rank"] = pool.talent.rank(ascending=False, method="min").astype(int)
pool["fit_rank"] = pool.fit.rank(ascending=False, method="min").astype(int)

# percentile of each prospect on key stats compared with the whole senior class (for the prospect card)
PCT = {"box_bpm": "BPM", "box_dbpm": "Def. BPM", "pts40": "Points/40", "ast40": "Assists/40", "stl40": "Steals/40",
       "blk40": "Blocks/40", "dreb40": "Def. reb/40", "ts": "True shooting", "height": "Height"}
for col in PCT:
    pool[col + "_pct"] = pool[col].rank(pct=True) * 100

board = pool.sort_values("talent", ascending=False).head(60)  # page shows the top of these after weighting
prospects = [{
    "id": r.athlete_id, "name": r["name"], "school": r.school, "logo": r.school_logo if isinstance(r.school_logo, str) else "",
    "img": r.headshot if isinstance(r.headshot, str) else "", "pos": r.pos if isinstance(r.pos, str) else "",
    "ht": int(r.height), "gp": int(r.gp), "mpg": round(r.mpg, 1),
    "pts": round(r.points / r.gp, 1), "reb": round(r.rebounds / r.gp, 1), "ast": round(r.assists / r.gp, 1),
    "blk": round(r.blocks / r.gp, 1), "stl": round(r.steals / r.gp, 1),
    "blk40": round(r.blk40, 2), "dreb40": round(r.dreb40, 1), "ts": round(r.ts, 3), "bpm": round(r.box_bpm, 1),
    "dbpm": round(r.box_dbpm, 1), "three": round(r.three_rate, 3),
    "dp": None if pd.isna(r.draft_prob) else round(float(r.draft_prob), 3), "pick": None if pd.isna(r.projected_pick) else round(float(r.projected_pick), 1),
    "season": int(r.season), "tr": int(r.talent_rank), "fr": int(r.fit_rank),  # which college season the numbers come from (2026 = 2025-26)
    "pmin": round(float(r.proj_min)), "talent": round(float(r.talent_pct), 1), "fit": round(float(r.fit_pct), 1),
    "pct": [round(float(r[col + "_pct"])) for col in PCT],
} for _, r in board.iterrows()]

# history points for the scatter: last college BPM vs WNBA minutes in first two seasons
hist_pts = [{"n": r["name"], "y": int(r.year), "pick": int(r.pick), "rd": int(r.rd), "bpm": round(r.box_bpm, 1), "min": int(r.pro_min),
             "blk": round(r.blk40, 2) if pd.notna(r.blk40) else None, "ht": None if pd.isna(r.height) else int(r.height)}
            for _, r in hist.iterrows()]

data = {"needs": needs, "translate": translate, "hist": hist_pts, "prospects": prospects,
        "model": {"r": round(model_r, 3), "n": int(len(train)), "features": [LABELS[f] for f in MODEL_F],
                  "weights": [round(float(b), 3) for b in beta[1:]]},
        "pool_n": int(len(pool)), "pct_labels": list(PCT.values()), "validation": validation}
# the No. 1 at the page's default setting (60% talent, 40% fit) for the home page tile
top_default = max(prospects, key=lambda p: 0.6 * p["talent"] + 0.4 * p["fit"])["name"] if prospects else None
lab.summary("draft-lab", {"pool": int(len(pool)), "top": top_default})
lab.write_page("draft-lab", "Draft Lab", "Who should the Toronto Tempo draft in 2027? Team needs, what translates from college, and a weighted draft board.",
               Path(__file__).parent / "page.html", data)

# print things to check in the terminal
print(pd.DataFrame(needs)[["label", "v", "rank", "teams"]].to_string(index=False))
print(pd.DataFrame(translate).sort_values("r_resid", ascending=False).to_string(index=False))
print("history n", len(hist), "model n", len(train), "model r", round(model_r, 3))
print("pool", len(pool))
print("validation", {k: v for k, v in validation.items() if k != "pts"})
print(board[["name", "school", "pos", "height", "box_bpm", "blk40", "dreb40", "draft_prob", "proj_min", "talent_pct", "fit_pct"]].head(25).round(2).to_string(index=False))
