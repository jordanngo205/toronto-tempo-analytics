"""Project 2 - Shot Lab (interactive): every Tempo shot of 2026.

Writes docs/shot-lab/index.html. Pieces:
  * per-player hex maps + raw shot dots (size = frequency, colour = zone pts/shot vs league)
  * shot quality (expected pts/shot from location) vs shot making (actual minus expected), league-wide
  * distance curve, shot-type families, assisted rate
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# let this file import lab.py and common.py from the main folder
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
from common import load

TOR = 131935  # ESPN team id for the Tempo
R = 1.5  # hex radius, feet

# --- every field-goal attempt in the league in 2026 ---------------------------------
p = load("pbp", 2026)
# shooting plays only, and no free throws
shots = p[p.shooting_play.astype(bool) & ~p.type_text.str.contains("Free Throw")].copy()
# keep half-court shots (x is 0-50 ft across the court, y is feet from the basket)
shots = shots[(shots.coordinate_y_raw <= 30) & shots.coordinate_x_raw.between(0, 50)]
shots["made"] = shots.scoring_play.astype(bool)
shots["three"] = shots.points_attempted == 3
shots["pts"] = np.where(shots.made, shots.points_attempted, 0)  # 0, 2 or 3 points
x, y = shots.coordinate_x_raw.astype(float), shots.coordinate_y_raw.astype(float)
dx = x - 25  # how far left/right of the basket
shots["dist"] = np.hypot(dx, y)  # straight-line distance to the basket
ang = np.degrees(np.arctan2(y, dx))
# left / centre / right of the court based on the angle
side = pd.Series(np.where(ang < 60, "R", np.where(ang > 120, "L", "C")), index=shots.index)
# put every shot in one of ten zones (first true condition wins)
shots["zone"] = np.select(
    [shots.dist < 4, (shots.dist < 10) & ~shots.three, ~shots.three, shots.three & (y <= 3)],
    ["Rim", "Short", "Mid " + side, "Corner3 " + side], default="Arc3 " + side)
# snap every shot to the centre of its hexagon (every other row is shifted half a hex)
w_, h_ = np.sqrt(3) * R, 1.5 * R
row = np.round((y + 5) / h_).astype(int)
col = np.round((x - (row % 2) * w_ / 2) / w_).astype(int)
shots["hx"] = (col * w_ + (row % 2) * w_ / 2).round(2)
shots["hy"] = (row * h_ - 5).round(2)

# ESPN has ~50 shot type names, so I group them into families by looking for key words
FAMILIES = [  # (family, substrings in ESPN type_text), first match wins
    ("Putback / tip", ["Putback", "Tip"]), ("Dunk", ["Dunk"]), ("Alley-oop", ["Alley Oop"]),
    ("Floater", ["Floating"]), ("Hook", ["Hook"]), ("Layup", ["Layup", "Finger Roll"]),
    ("Step-back", ["Step Back"]), ("Pull-up", ["Pullup"]), ("Fadeaway / turnaround", ["Fade", "Turnaround"]),
    ("Jump shot", ["Jump"]),
]


def family(t):
    # return the first family whose key word is in the shot description
    for name, keys in FAMILIES:
        if any(k in t for k in keys):
            return name
    return "Other"


shots["family"] = shots.type_text.map(family)
# league points per shot in each zone
lg_zone = shots.groupby("zone").pts.mean()
# expected points for every shot = what the average WNBA shot from that zone is worth
shots["xpts"] = shots.zone.map(lg_zone)
in_tor = (shots.home_team_id == TOR) | (shots.away_team_id == TOR)  # shots taken in Tempo games
lg = shots


def profile(s):
    """Everything the page shows for one group of shots (a player, the team, opponents or the league)."""
    # zone table: attempts, points per shot, FG%, share of shots, and points per shot vs league
    z = s.groupby("zone").agg(n=("pts", "size"), pps=("pts", "mean"), fg=("made", "mean"))
    z["freq"] = z.n / z.n.sum()
    z["d"] = z.pps - lg_zone.reindex(z.index)
    # shots and makes in each hexagon
    hx = s.groupby(["hx", "hy"]).agg(n=("pts", "size"), m=("made", "sum"), zone=("zone", "first")).reset_index()
    # shot type families
    fam = s.groupby("family").agg(n=("pts", "size"), pps=("pts", "mean"))
    fam["freq"] = fam.n / fam.n.sum()
    made = s[s.made]
    return {
        "fga": int(len(s)), "pps": round(s.pts.mean(), 3), "xpps": round(s.xpts.mean(), 3),
        "fg": round(s.made.mean(), 3), "rim": round((s.zone == "Rim").mean(), 3), "three": round(s.three.mean(), 3),
        # assisted rate: a made shot has a second player listed (athlete_id_2) when someone got the assist
        "ast": round(made.athlete_id_2.notna().mean(), 3) if len(made) else None,
        "zones": {k: {"n": int(v.n), "pps": round(v.pps, 3), "fg": round(v.fg, 3), "freq": round(v.freq, 3), "d": round(v.d, 3)}
                  for k, v in z.iterrows()},
        "hexes": [[r.hx, r.hy, int(r.n), int(r.m), r.zone] for r in hx.itertuples()],
        "fam": {k: {"n": int(v.n), "pps": round(v.pps, 3), "freq": round(v.freq, 3)} for k, v in fam.iterrows()},
    }


tor_shots = shots[shots.team_id == TOR]                  # Tempo shooting
opp_shots = shots[in_tor & (shots.team_id != TOR)]       # opponents shooting against the Tempo
# Tempo players with at least 60 attempts get their own button on the page
players = tor_shots.groupby("athlete_name_1").size().sort_values(ascending=False)
players = players[players >= 60]
views = {"Tempo": profile(tor_shots), "Opponents": profile(opp_shots)}
for name in players.index:
    views[name] = profile(tor_shots[tor_shots.athlete_name_1 == name])
views["League"] = profile(lg)

# raw Tempo + opponent shots for the dot view: [x, y, made, three, shooter index or -1 for opponents]
# (-2 means a Tempo player with fewer than 60 shots)
names = list(players.index)
dots = [[round(r.coordinate_x_raw, 1), round(r.coordinate_y_raw, 1), int(r.made), int(r.three),
         names.index(r.athlete_name_1) if r.athlete_name_1 in names else -2] for r in tor_shots.itertuples()]
opp_dots = [[round(r.coordinate_x_raw, 1), round(r.coordinate_y_raw, 1), int(r.made), int(r.three), -1]
            for r in opp_shots.itertuples()]

# league shot quality vs shot making (players with 150+ FGA)
abbr = load("team_box", 2026).drop_duplicates("team_id").set_index("team_id").team_abbreviation
# per player: attempts, actual points per shot, expected points per shot, rim share and 3PA share
qm = shots.groupby(["athlete_name_1", "team_id"]).agg(fga=("pts", "size"), pps=("pts", "mean"), xpps=("xpts", "mean"),
                                                      rim=("zone", lambda z: (z == "Rim").mean()), three=("three", "mean"))
qm = qm[qm.fga >= 150].reset_index()
quality = [{"n": r.athlete_name_1, "t": abbr.get(r.team_id, "?"), "fga": int(r.fga), "pps": round(r.pps, 3),
            "x": round(r.xpps, 3), "rim": round(r.rim, 3), "three": round(r.three, 3)} for r in qm.itertuples()]

# distance curve, 1-ft bins up to 28 ft
def curve(s):
    # put each shot in a 1-foot bin (28+ feet all go in the last bin)
    b = s.assign(bin=np.minimum(s.dist.astype(int), 28)).groupby("bin").agg(n=("pts", "size"), pps=("pts", "mean"))
    b = b.reindex(range(29))  # make sure every bin 0-28 exists, even empty ones
    b["freq"] = b.n / b.n.sum()
    # smoothed points per shot for the line: a bin with few shots borrows shots from the feet next to it
    # (1 ft each way, then 2, ...) until it has at least 50. It never borrows across the 3-point line (22 ft),
    # so the jump in value at the line stays sharp.
    n, pts = b.n.fillna(0).to_numpy(), (b.n * b.pps).fillna(0).to_numpy()
    smooth = []
    for i in range(29):
        side = range(22, 29) if i >= 22 else range(0, 22)
        w = 0
        while n[[j for j in range(i - w, i + w + 1) if j in side]].sum() < 50 and w < 6:
            w += 1
        js = [j for j in range(i - w, i + w + 1) if j in side]
        smooth.append(pts[js].sum() / n[js].sum() if n[js].sum() else np.nan)
    b["smooth"] = smooth
    # [share of shots, points per shot, smoothed points per shot, attempts] per bin; empty bins become None for JSON
    return [[None if np.isnan(v) else round(float(v), 4) for v in (r.freq, r.pps, r.smooth)] + [int(r.n) if r.n == r.n else 0]
            for r in b.itertuples()]


dist = {"Tempo": curve(tor_shots), "Opponents": curve(opp_shots), "League": curve(lg)}

# --- how every team's plays ended (Sportradar "defending pick actions" style, for all plays) -------------
# A "play" ends in one of: a shooting-foul trip to the line, a field-goal attempt from a zone, or a turnover.
# And-one free throws ("1 of 1") are left out because the made basket already counted as the play.
allp = p.sort_values(["game_id", "game_play_number"]).copy()
allp["off"] = allp.team_id
allp["kind"] = None
fga = allp.shooting_play.astype(bool) & ~allp.type_text.str.contains("Free Throw")
allp.loc[fga, "kind"] = shots["zone"].reindex(allp.index[fga]).map(
    lambda z: "Rim" if z == "Rim" else "Short paint" if z == "Short" else "Midrange" if str(z).startswith("Mid")
    else "Corner 3" if str(z).startswith("Corner3") else "Above-break 3")
trip_start = allp.type_text.isin(["Free Throw - 1 of 2", "Free Throw - 1 of 3"])
allp.loc[trip_start, "kind"] = "Shooting foul"
tov = allp.type_text.str.contains("Turnover") | allp.type_text.isin(["Traveling", "Kicked Ball"])
allp.loc[tov, "kind"] = "Turnover"
# points from each free-throw trip = made free throws in that trip (the next 1-2 free throws by the same team)
ft = allp[allp.type_text.str.startswith("Free Throw - ") & ~allp.type_text.str.contains("Technical")].copy()
ft["trip"] = (ft.type_text.str.contains("1 of")).cumsum()
trip_pts = ft.groupby("trip").scoring_play.apply(lambda v: int(v.astype(bool).sum()))
ft_first = ft[ft.type_text.isin(["Free Throw - 1 of 2", "Free Throw - 1 of 3"])]
allp["pts_play"] = np.nan
allp.loc[ft_first.index, "pts_play"] = ft_first.trip.map(trip_pts).values
allp.loc[fga, "pts_play"] = np.where(allp.loc[fga].scoring_play.astype(bool), allp.loc[fga].points_attempted, 0)
allp.loc[tov, "pts_play"] = 0
plays = allp[allp.kind.notna() & allp.off.notna()].copy()
plays = plays[plays.index.isin(shots.index) | ~fga[plays.index]]  # field goals: only the half-court shots kept above
plays["def"] = np.where(plays.off == plays.home_team_id, plays.away_team_id, plays.home_team_id)
OUTCOMES = plays.groupby("kind").pts_play.mean().sort_values(ascending=False)  # value of each outcome, best first
abbr2 = load("team_box", 2026).drop_duplicates("team_id")
real_teams = abbr2.groupby("team_id").size().index
team_ab = abbr2.set_index("team_id").team_abbreviation
outcomes = {"order": list(OUTCOMES.index), "value": [round(float(v), 3) for v in OUTCOMES.values],
            "league": [round(float(v), 4) for v in plays.kind.value_counts(normalize=True).reindex(OUTCOMES.index).values]}
for side in ("def", "off"):
    rows = []
    for tid, d in plays.groupby(side):
        ab = team_ab.get(tid)
        if ab is None or len(d) < 1000:   # skip All-Star teams
            continue
        share = d.kind.value_counts(normalize=True).reindex(OUTCOMES.index).fillna(0)
        rows.append({"t": ab, "share": [round(float(v), 4) for v in share.values], "ppp": round(float(d.pts_play.mean()), 3), "n": int(len(d))})
    outcomes[side] = rows

# everything the page needs
data = {"outcomes": outcomes, "views": views, "players": names, "dots": dots, "opp_dots": opp_dots, "quality": quality,
        "dist": dist, "hex_r": R, "families": [f for f, _ in FAMILIES]}
# headline numbers for the home page
lab.summary("shot-lab", {"xpps": views["Tempo"]["xpps"], "pps": views["Tempo"]["pps"], "lg_xpps": views["League"]["xpps"],
                         "rim": views["Tempo"]["rim"], "opp_rim": views["Opponents"]["rim"]})
lab.write_page("shot-lab", "Shot Lab", "Every Toronto Tempo shot of 2026: player hex maps, shot quality vs shot making, distance curves.",
               Path(__file__).parent / "page.html", data)
# print numbers to check them in the terminal
t, o, L = views["Tempo"], views["Opponents"], views["League"]
print({k: (t[k], o[k], L[k]) for k in ["pps", "xpps", "fg", "rim", "three", "ast"]})
print(names)
print("outcome values", outcomes["order"], outcomes["value"])
print("defenses by pts/play", sorted([(r["t"], r["ppp"]) for r in outcomes["def"]], key=lambda x: x[1]))
q = pd.DataFrame(quality); q["make"] = q.pps - q.x
print(q[q.t == "TOR"].sort_values("fga", ascending=False).round(3).to_string())
print(q.make.describe().round(3).to_string())
