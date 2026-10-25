"""Project 2 - Shot Diet.

Where do the Tempo shoot from, where do opponents shoot from against them,
and how does each zone's points-per-shot compare with the 2026 league?
Uses ESPN play-by-play shot locations (feet, basket at x=25, y=0).
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Arc, Circle, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import INK, MUTED, load, save, style

OUT = Path(__file__).parent
TOR_ID = 131935
ZONES = ["Rim", "Paint (non-rim)", "Midrange", "Corner 3", "Above-break 3"]
ARC_R, CORNER_X, BREAK_Y = 22.15, 22.0, 3.0  # WNBA three-point line, basket-relative feet


def zone(x, y, three=None):
    dx = np.asarray(x) - 25.0
    y = np.asarray(y, dtype=float)
    d = np.hypot(dx, y)
    if three is None:  # geometric fallback for drawing the court
        three = np.where(y <= BREAK_Y, np.abs(dx) >= CORNER_X, d >= ARC_R)
    in_paint = (np.abs(dx) <= 8) & (y <= 14)
    return np.select(
        [three & (y <= BREAK_Y), three, d < 4, in_paint],
        ["Corner 3", "Above-break 3", "Rim", "Paint (non-rim)"],
        default="Midrange",
    )


p = load("pbp", 2026)
shots = p[p.shooting_play & ~p.type_text.str.contains("Free Throw")].copy()
shots["made"] = shots.scoring_play.astype(bool)
shots["pts"] = np.where(shots.made, shots.points_attempted, 0)
shots["zone"] = zone(shots.coordinate_x_raw, shots.coordinate_y_raw, shots.points_attempted.eq(3).to_numpy())
tor_games = (shots.home_team_id == TOR_ID) | (shots.away_team_id == TOR_ID)


def profile(df):
    g = df.groupby("zone").agg(fga=("made", "size"), pps=("pts", "mean"), fg=("made", "mean"))
    g["freq"] = g.fga / g.fga.sum()
    return g.reindex(ZONES)


league = profile(shots)
offense = profile(shots[shots.team_id == TOR_ID])
defense = profile(shots[tor_games & (shots.team_id != TOR_ID)])
table = pd.concat({"league": league, "tempo_off": offense, "tempo_def": defense}, axis=1)
table.to_csv(OUT / "zone_profile.csv")
print(table[[(k, c) for k in ["league", "tempo_off", "tempo_def"] for c in ["freq", "pps"]]].round(3).to_string())


def draw_court(ax):
    kw = dict(color="#8A9099", lw=1.2, fill=False)
    ax.add_patch(Rectangle((-0, -5.25), 50, 47, **kw))
    ax.add_patch(Rectangle((17, -5.25), 16, 19, **kw))
    ax.add_patch(Circle((25, 0), 0.75, **kw))
    ax.plot([22, 28], [-1.25, -1.25], color="#8A9099", lw=1.5)
    ax.add_patch(Arc((25, 13.75), 12, 12, theta1=0, theta2=180, color="#8A9099", lw=1.2))
    ang = np.degrees(np.arcsin(BREAK_Y / ARC_R))
    ax.add_patch(Arc((25, 0), 2 * ARC_R, 2 * ARC_R, theta1=ang, theta2=180 - ang, color="#8A9099", lw=1.2))
    for x in (25 - CORNER_X, 25 + CORNER_X):
        ax.plot([x, x], [-5.25, BREAK_Y], color="#8A9099", lw=1.2)
    ax.set_xlim(0, 50); ax.set_ylim(-5.5, 30)
    ax.set_aspect("equal"); ax.axis("off")


# diverging in Tempo colours: navy = good for Toronto, bordeaux = bad, gray midpoint
cmap = LinearSegmentedColormap.from_list("tempo_div", ["#8A1F42", "#F1F2F4", "#33476D"])
gx, gy = np.meshgrid(np.linspace(0, 50, 500), np.linspace(-5.25, 30, 360))
gz = zone(gx.ravel(), gy.ravel()).reshape(gx.shape)

fig, axes = plt.subplots(1, 2, figsize=(12, 6.4), layout="constrained")
panels = [(axes[0], offense, +1, "Tempo offense", "Shot share and points per shot, vs league average"),
          (axes[1], defense, -1, "Tempo defense (opponents)", "Navy = opponents scored less than league average")]
norm = TwoSlopeNorm(vcenter=0, vmin=-0.2, vmax=0.2)
label_pos = {"Rim": (25, 1.6), "Paint (non-rim)": (25, 9), "Midrange": (25, 18.5),
             "Corner 3": (1.6, 6), "Above-break 3": (25, 26.5)}
for ax, prof, sign, title, sub in panels:
    diff = sign * (prof.pps - league.pps)
    img = np.vectorize(lambda z: diff[z])(gz)
    ax.imshow(img, extent=(0, 50, -5.25, 30), origin="lower", cmap=cmap, norm=norm, alpha=0.9)
    draw_court(ax)
    for z, (x, y) in label_pos.items():
        share_diff = prof.freq[z] - league.freq[z]
        txt = f"{prof.freq[z]:.0%} of shots ({share_diff:+.0%})\n{prof.pps[z]:.2f} pts/shot"
        if z == "Corner 3":
            for cx, ha in ((1.0, "left"), (49.0, "right")):
                ax.text(cx, y, txt if ha == "left" else "", ha=ha, va="center", fontsize=7.5, color=INK)
        else:
            ax.text(x, y, txt, ha="center", va="center", fontsize=8.5, color=INK,
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.75))
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=INK)
    ax.text(0, -7.5, sub, fontsize=8.5, color=MUTED)

cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=axes, orientation="horizontal",
                  fraction=0.05, aspect=50)
cb.set_label("Points per shot vs 2026 league average (navy = better for Toronto)", color=MUTED, fontsize=9)
cb.ax.tick_params(colors=MUTED, labelsize=8)
fig.suptitle("Tempo shot diet, 2026: where the points come from and where they leak", x=0.02, ha="left",
             fontsize=14, fontweight="bold", color=INK)
save(fig, OUT / "shot_zones.png")

# --- Player shot diets ------------------------------------------------------
ts = shots[shots.team_id == TOR_ID]
top = ts.athlete_name_1.value_counts().head(8).index
mix = (ts[ts.athlete_name_1.isin(top)].groupby(["athlete_name_1", "zone"]).size()
       .unstack(fill_value=0).reindex(columns=ZONES))
mix = mix.div(mix.sum(axis=1), axis=0).loc[top[::-1]]
fig, ax = plt.subplots(figsize=(9, 4.8))
zone_colors = ["#1E2A42", "#33476D", "#9AA8C2", "#C98AA0", "#8A1F42"]  # Tempo navy = 2s, bordeaux = 3s
left = np.zeros(len(mix))
for z, c in zip(ZONES, zone_colors):
    ax.barh(mix.index, mix[z], left=left, color=c, edgecolor="white", lw=2, height=0.7, label=z)
    left += mix[z].to_numpy()
ax.set_xlim(0, 1)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.legend(ncol=5, frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, -0.08))
style(ax, "Who takes which shots", "Share of each player's field-goal attempts by zone, top 8 Tempo shooters by volume")
ax.grid(axis="y", visible=False)
save(fig, OUT / "player_shot_mix.png")
