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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
from common import load

TOR = 131935
R = 1.5  # hex radius, feet

p = load("pbp", 2026)
shots = p[p.shooting_play.astype(bool) & ~p.type_text.str.contains("Free Throw")].copy()
shots = shots[(shots.coordinate_y_raw <= 30) & shots.coordinate_x_raw.between(0, 50)]
shots["made"] = shots.scoring_play.astype(bool)
shots["three"] = shots.points_attempted == 3
shots["pts"] = np.where(shots.made, shots.points_attempted, 0)
x, y = shots.coordinate_x_raw.astype(float), shots.coordinate_y_raw.astype(float)
dx = x - 25
shots["dist"] = np.hypot(dx, y)
ang = np.degrees(np.arctan2(y, dx))
side = pd.Series(np.where(ang < 60, "R", np.where(ang > 120, "L", "C")), index=shots.index)
shots["zone"] = np.select(
    [shots.dist < 4, (shots.dist < 10) & ~shots.three, ~shots.three, shots.three & (y <= 3)],
    ["Rim", "Short", "Mid " + side, "Corner3 " + side], default="Arc3 " + side)
w_, h_ = np.sqrt(3) * R, 1.5 * R
row = np.round((y + 5) / h_).astype(int)
col = np.round((x - (row % 2) * w_ / 2) / w_).astype(int)
shots["hx"] = (col * w_ + (row % 2) * w_ / 2).round(2)
shots["hy"] = (row * h_ - 5).round(2)

FAMILIES = [  # (family, substrings in ESPN type_text), first match wins
    ("Putback / tip", ["Putback", "Tip"]), ("Dunk", ["Dunk"]), ("Alley-oop", ["Alley Oop"]),
    ("Floater", ["Floating"]), ("Hook", ["Hook"]), ("Layup", ["Layup", "Finger Roll"]),
    ("Step-back", ["Step Back"]), ("Pull-up", ["Pullup"]), ("Fadeaway / turnaround", ["Fade", "Turnaround"]),
    ("Jump shot", ["Jump"]),
]


def family(t):
    for name, keys in FAMILIES:
        if any(k in t for k in keys):
            return name
    return "Other"


shots["family"] = shots.type_text.map(family)
lg_zone = shots.groupby("zone").pts.mean()
shots["xpts"] = shots.zone.map(lg_zone)
in_tor = (shots.home_team_id == TOR) | (shots.away_team_id == TOR)
lg = shots


def profile(s):
    z = s.groupby("zone").agg(n=("pts", "size"), pps=("pts", "mean"), fg=("made", "mean"))
    z["freq"] = z.n / z.n.sum()
    z["d"] = z.pps - lg_zone.reindex(z.index)
    hx = s.groupby(["hx", "hy"]).agg(n=("pts", "size"), m=("made", "sum"), zone=("zone", "first")).reset_index()
    fam = s.groupby("family").agg(n=("pts", "size"), pps=("pts", "mean"))
    fam["freq"] = fam.n / fam.n.sum()
    made = s[s.made]
    return {
        "fga": int(len(s)), "pps": round(s.pts.mean(), 3), "xpps": round(s.xpts.mean(), 3),
        "fg": round(s.made.mean(), 3), "rim": round((s.zone == "Rim").mean(), 3), "three": round(s.three.mean(), 3),
        "ast": round(made.athlete_id_2.notna().mean(), 3) if len(made) else None,
        "zones": {k: {"n": int(v.n), "pps": round(v.pps, 3), "fg": round(v.fg, 3), "freq": round(v.freq, 3), "d": round(v.d, 3)}
                  for k, v in z.iterrows()},
        "hexes": [[r.hx, r.hy, int(r.n), int(r.m), r.zone] for r in hx.itertuples()],
        "fam": {k: {"n": int(v.n), "pps": round(v.pps, 3), "freq": round(v.freq, 3)} for k, v in fam.iterrows()},
    }


tor_shots = shots[shots.team_id == TOR]
opp_shots = shots[in_tor & (shots.team_id != TOR)]
players = tor_shots.groupby("athlete_name_1").size().sort_values(ascending=False)
players = players[players >= 60]
views = {"Tempo": profile(tor_shots), "Opponents": profile(opp_shots)}
for name in players.index:
    views[name] = profile(tor_shots[tor_shots.athlete_name_1 == name])
views["League"] = profile(lg)

# raw Tempo + opponent shots for the dot view: [x, y, made, three, shooter index or -1 for opponents]
names = list(players.index)
dots = [[round(r.coordinate_x_raw, 1), round(r.coordinate_y_raw, 1), int(r.made), int(r.three),
         names.index(r.athlete_name_1) if r.athlete_name_1 in names else -2] for r in tor_shots.itertuples()]
opp_dots = [[round(r.coordinate_x_raw, 1), round(r.coordinate_y_raw, 1), int(r.made), int(r.three), -1]
            for r in opp_shots.itertuples()]

# league shot quality vs shot making (players with 150+ FGA)
abbr = load("team_box", 2026).drop_duplicates("team_id").set_index("team_id").team_abbreviation
qm = shots.groupby(["athlete_name_1", "team_id"]).agg(fga=("pts", "size"), pps=("pts", "mean"), xpps=("xpts", "mean"),
                                                      rim=("zone", lambda z: (z == "Rim").mean()), three=("three", "mean"))
qm = qm[qm.fga >= 150].reset_index()
quality = [{"n": r.athlete_name_1, "t": abbr.get(r.team_id, "?"), "fga": int(r.fga), "pps": round(r.pps, 3),
            "x": round(r.xpps, 3), "rim": round(r.rim, 3), "three": round(r.three, 3)} for r in qm.itertuples()]

# distance curve, 1-ft bins up to 28 ft
def curve(s):
    b = s.assign(bin=np.minimum(s.dist.astype(int), 28)).groupby("bin").agg(n=("pts", "size"), pps=("pts", "mean"))
    b = b.reindex(range(29))
    b["freq"] = b.n / b.n.sum()
    return [[None if np.isnan(v) else round(v, 4) for v in (r.freq, r.pps)] for r in b.itertuples()]


dist = {"Tempo": curve(tor_shots), "Opponents": curve(opp_shots), "League": curve(lg)}

data = {"views": views, "players": names, "dots": dots, "opp_dots": opp_dots, "quality": quality,
        "dist": dist, "hex_r": R, "families": [f for f, _ in FAMILIES]}
lab.summary("shot-lab", {"xpps": views["Tempo"]["xpps"], "pps": views["Tempo"]["pps"], "lg_xpps": views["League"]["xpps"],
                         "rim": views["Tempo"]["rim"], "opp_rim": views["Opponents"]["rim"]})
lab.write_page("shot-lab", "Shot Lab", "Every Toronto Tempo shot of 2026: player hex maps, shot quality vs shot making, distance curves.",
               Path(__file__).parent / "page.html", data)
t, o, L = views["Tempo"], views["Opponents"], views["League"]
print({k: (t[k], o[k], L[k]) for k in ["pps", "xpps", "fg", "rim", "three", "ast"]})
print(names)
q = pd.DataFrame(quality); q["make"] = q.pps - q.x
print(q[q.t == "TOR"].sort_values("fga", ascending=False).round(3).to_string())
print(q.make.describe().round(3).to_string())
