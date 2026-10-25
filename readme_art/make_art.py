"""Makes the graphics for the README (they are NOT screenshots of the website).

Each graphic is a small HTML page that I build as a string, then I use headless
Google Chrome to take a picture of it. That way I can use the same fonts and
colours as the website. The Elo race is a matplotlib animation saved as a GIF.

Run it with:  .venv/bin/python readme_art/make_art.py
Pictures go to readme_art/out/
"""
import json
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw without opening a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image

# let this script import common.py and elo.py from the main folder
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import elo
from common import RAW, load

HERE = Path(__file__).parent
OUT = HERE / "out"          # finished pictures
TMP = HERE / "_tmp"         # throwaway html files
OUT.mkdir(exist_ok=True)
TMP.mkdir(exist_ok=True)
LOGOS = ROOT / "assets" / "logos"
HEADS = ROOT / "assets" / "headshots"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TOR = 131935  # ESPN's team id for the Toronto Tempo

# team colours (same ones the website uses)
BORDEAUX = "#8a1f42"
NAVY = "#33476d"
FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800'
         '&family=Barlow:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">')


def render(name, html, width, height):
    """Save the html to a file, screenshot it with Chrome, and save a PNG in out/."""
    page = TMP / f"{name}.html"
    page.write_text(f"<!doctype html><html><head><meta charset='utf-8'>{FONTS}</head>"
                    f"<body style='margin:0'>{html}</body></html>")
    shot = OUT / f"{name}.png"
    # --force-device-scale-factor=2 makes the picture twice as sharp (retina)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    f"--window-size={width},{height}", "--force-device-scale-factor=2", "--virtual-time-budget=4000",
                    f"--screenshot={shot}", page.as_uri()], capture_output=True)
    # shrink a little so the README doesn't load huge files
    im = Image.open(shot)
    im.thumbnail((2400, 2400))
    im.save(shot, optimize=True)
    print("made", shot.relative_to(ROOT))


def uri(path):
    """Chrome needs full file:// links to load the logos and headshots."""
    return Path(path).resolve().as_uri()


# ---------------------------------------------------------------------------
# 1. Load the data I need
# ---------------------------------------------------------------------------

# one row per Tempo game, in date order
tb = load("team_box", 2026)
games = tb[tb.team_id == TOR].copy()
games["game_date"] = pd.to_datetime(games.game_date)
games = games.sort_values("game_date").reset_index(drop=True)
games["margin"] = games.team_score - games.opponent_team_score
wins = int((games.margin > 0).sum())
losses = len(games) - wins

# player box scores (only games where the player actually played)
pb = load("player_box", 2026)
for col in ["minutes", "points", "rebounds", "assists", "field_goals_attempted", "free_throws_attempted"]:
    pb[col] = pd.to_numeric(pb[col], errors="coerce").fillna(0)
pb["plus_minus"] = pd.to_numeric(pb.plus_minus.astype(str).str.lstrip("+"), errors="coerce").fillna(0)
tor_box = pb[(pb.team_id == TOR) & (pb.minutes > 0)]

# season totals per player
season = tor_box.groupby("athlete_display_name").agg(
    gp=("game_id", "nunique"), mins=("minutes", "sum"), pts=("points", "sum"), reb=("rebounds", "sum"),
    ast=("assists", "sum"), fga=("field_goals_attempted", "sum"), fta=("free_throws_attempted", "sum"),
    pm=("plus_minus", "sum"), jersey=("athlete_jersey", "first"), pos=("athlete_position_abbreviation", "first"))
season["ts"] = season.pts / (2 * (season.fga + 0.44 * season.fta))  # true shooting %

# every Tempo field-goal attempt with its location (for the little shot charts)
pbp = load("pbp", 2026)
shots = pbp[pbp.shooting_play.astype(bool) & ~pbp.type_text.str.contains("Free Throw") & (pbp.team_id == TOR)].copy()
shots = shots[(shots.coordinate_y_raw <= 28) & shots.coordinate_x_raw.between(0, 50)]

# headline numbers that the website build already saved
summary = json.loads((ROOT / "docs" / "assets" / "summary.json").read_text())


# ---------------------------------------------------------------------------
# 2. Banner: the 44 games drawn as "speed lines" like the Tempo logo
# ---------------------------------------------------------------------------

def banner():
    W, H = 1600, 560
    lines = []
    top = 70
    # one streak per game: longer streak = more points scored, bright = win, faded = loss
    for i, g in games.iterrows():
        length = (g.team_score - 55) / 70 * 520  # 55 pts -> 0 px, 125 pts -> 520 px (stays clear of the title)
        y = top + i * 9.6
        opacity = 0.95 if g.margin > 0 else 0.28
        # streaks start at the logo and go to the left, so x = right edge minus length
        lines.append(f'<rect x="{1290 - length:.0f}" y="{y:.1f}" width="{length:.0f}" height="5.2" rx="2.6" '
                     f'fill="#fff" opacity="{opacity}"/>')
    svg = f'<svg width="{W}" height="{H}" style="position:absolute;inset:0">{"".join(lines)}</svg>'
    html = f"""
    <div style="width:{W}px;height:{H}px;position:relative;overflow:hidden;font-family:Barlow,sans-serif;color:#fff;
                background:linear-gradient(115deg,#140a10 0%,#3d0d1f 45%,{BORDEAUX} 100%)">
      {svg}
      <img src="{uri(LOGOS / 'tor_white.png')}" style="position:absolute;right:40px;top:150px;width:300px;opacity:.96">
      <div style="position:absolute;left:70px;top:70px;width:760px">
        <div style="font:500 17px 'IBM Plex Mono';letter-spacing:.18em;opacity:.75">TORONTO TEMPO · WNBA 2026</div>
        <div style="font:800 168px/0.9 'Barlow Condensed';letter-spacing:-.01em;margin-top:18px">TEMPO LAB</div>
        <div style="font:700 34px 'Barlow Condensed';text-transform:uppercase;letter-spacing:.03em;margin-top:14px;color:#f3c1d1">
          Toronto's first season, broken down with data</div>
        <div style="display:flex;gap:12px;margin-top:34px">
          {"".join(f'<span style="font:700 24px Barlow Condensed;padding:8px 16px;border:2px solid rgba(255,255,255,.55)">{t}</span>'
                   for t in [f"{wins}–{losses}", f"Elo {summary['expansion-class']['tor_elo']}", "44 games", "5 interactive pages"])}
        </div>
      </div>
      <div style="position:absolute;left:70px;bottom:26px;font:400 14px 'IBM Plex Mono';opacity:.6">
        each streak = one game · length = points scored · bright = win</div>
    </div>"""
    render("banner", html, W, H)


# ---------------------------------------------------------------------------
# 3. Season ring: every game around a circle, bar = final margin
# ---------------------------------------------------------------------------

def season_ring():
    S = 1200          # picture width
    HT = 1380         # picture height (taller so the title sits above the ring)
    cx, cy = S / 2, 770
    base = 330      # radius of the "zero" circle
    scale = 4.2     # pixels per point of margin
    parts = []
    n = len(games)
    # light rings for +10/+20 and -10/-20 so you can read the bars
    for m in [-20, -10, 10, 20]:
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{base + m * scale}" fill="none" stroke="#2a303b" stroke-dasharray="3 5"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{base}" fill="none" stroke="#6b7280" stroke-width="1.5"/>')
    for i, g in games.iterrows():
        # angle for this game: start at the top (-90 degrees) and go clockwise
        a = np.radians(-90 + (i + 0.5) * 360 / n)
        r1 = base + max(-35, min(35, g.margin)) * scale
        x0, y0 = cx + base * np.cos(a), cy + base * np.sin(a)
        x1, y1 = cx + r1 * np.cos(a), cy + r1 * np.sin(a)
        color = "#7e9bd0" if g.margin > 0 else "#d0587c"
        parts.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{color}" stroke-width="13" stroke-linecap="round"/>')
        # opponent logo on the outside, on a small white circle so dark logos still show
        lx, ly = cx + 520 * np.cos(a), cy + 520 * np.sin(a)
        parts.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="21" fill="#eef0f4"/>')
        logo = LOGOS / f"{g.opponent_team_abbreviation.lower()}_sm.png"
        parts.append(f'<image href="{uri(logo)}" x="{lx - 15:.1f}" y="{ly - 15:.1f}" width="30" height="30"/>')
        # score text just inside the logo ring
        tx, ty = cx + 470 * np.cos(a), cy + 470 * np.sin(a)
        parts.append(f'<text x="{tx:.1f}" y="{ty + 4:.1f}" text-anchor="middle" font-family="IBM Plex Mono" font-size="11" '
                     f'fill="{"#c9d4ea" if g.margin > 0 else "#8a91a0"}">{g.team_score}-{g.opponent_team_score}</text>')
    # month labels inside the ring, placed at each month's first game
    seen = set()
    for i, g in games.iterrows():
        mon = g.game_date.strftime("%b").upper()
        if mon in seen:
            continue
        seen.add(mon)
        a = np.radians(-90 + i * 360 / n)
        mx, my = cx + 574 * np.cos(a), cy + 574 * np.sin(a)
        parts.append(f'<text x="{mx:.1f}" y="{my + 5:.1f}" text-anchor="middle" font-family="IBM Plex Mono" font-size="14" font-weight="500" fill="#d0587c">{mon}</text>')
    avg = games.margin.mean()
    html = f"""
    <div style="width:{S}px;height:{HT}px;background:#12161d;position:relative;font-family:Barlow,sans-serif;color:#eef0f4">
      <svg width="{S}" height="{HT}" style="position:absolute;inset:0">{"".join(parts)}</svg>
      <div style="position:absolute;left:0;right:0;top:{cy - 95}px;text-align:center">
        <img src="{uri(LOGOS / 'tor_white.png')}" style="width:120px;opacity:.95">
        <div style="font:800 96px/0.95 'Barlow Condensed'">{wins}–{losses}</div>
        <div style="font:500 15px 'IBM Plex Mono';letter-spacing:.14em;color:#8a91a0;margin-top:6px">AVG MARGIN {avg:+.1f}</div>
      </div>
      <div style="position:absolute;left:0;right:0;top:34px;text-align:center">
        <div style="font:800 48px 'Barlow Condensed';text-transform:uppercase">The season in a circle</div>
        <div style="font:400 17px Barlow;color:#b7bdc9">Every Tempo game, clockwise from opening night. Bars point out for wins and in for losses. Longer bar = bigger margin.</div>
      </div>
      <div style="position:absolute;right:36px;bottom:30px;text-align:right;font:500 14px 'IBM Plex Mono';color:#8a91a0">
        <span style="color:#7e9bd0">■</span> win &nbsp; <span style="color:#d0587c">■</span> loss</div>
    </div>"""
    render("season-ring", html, S, HT)


# ---------------------------------------------------------------------------
# 4. Player trading cards with a mini shot chart for each player
# ---------------------------------------------------------------------------

def mini_hexes(name, width=300):
    """Small hex shot chart as SVG. Hex size = how often she shoots there, colour = how often it goes in."""
    s = shots[shots.athlete_name_1 == name]
    R = 1.9  # hex radius in feet
    w, h = np.sqrt(3) * R, 1.5 * R
    x, y = s.coordinate_x_raw.astype(float), s.coordinate_y_raw.astype(float)
    # snap every shot to the nearest hex centre (pointy-top hex grid)
    row = np.round((y + 5) / h).astype(int)
    col = np.round((x - (row % 2) * w / 2) / w).astype(int)
    s = s.assign(hx=col * w + (row % 2) * w / 2, hy=row * h - 5)
    bins = s.groupby(["hx", "hy"]).agg(n=("scoring_play", "size"), made=("scoring_play", "sum")).reset_index()
    k = width / 50  # pixels per foot
    biggest = bins.n.max()
    polys = []
    for b in bins.itertuples():
        r = R * k * 0.95 * np.sqrt(b.n / biggest)
        if r < 1.5:
            continue
        fg = b.made / b.n
        # mix between light pink (cold) and deep bordeaux (hot)
        color = f"color-mix(in oklab, {BORDEAUX} {int(25 + 75 * fg)}%, #f3e6eb)"
        pts = " ".join(f"{b.hx * k + r * np.cos(np.radians(60 * j - 90)):.1f},{(b.hy + 5.25) * k + r * np.sin(np.radians(60 * j - 90)):.1f}"
                       for j in range(6))
        polys.append(f'<polygon points="{pts}" fill="{color}"/>')
    # simple court lines: paint, rim and three-point arc
    c3 = np.sqrt(22.15 ** 2 - 9)
    court = (f'<rect x="{17 * k}" y="0" width="{16 * k}" height="{19 * k}" fill="none" stroke="#c9ced8"/>'
             f'<circle cx="{25 * k}" cy="{5.25 * k}" r="{0.75 * k}" fill="none" stroke="#c9ced8"/>'
             f'<path d="M {(25 - c3) * k} 0 L {(25 - c3) * k} {8.25 * k} A {22.15 * k} {22.15 * k} 0 0 0 {(25 + c3) * k} {8.25 * k} L {(25 + c3) * k} 0" fill="none" stroke="#c9ced8"/>')
    return f'<svg width="{width}" height="{33 * k:.0f}" viewBox="0 0 {width} {33 * k:.0f}">{court}{"".join(polys)}</svg>'


def player_cards():
    # (player, label on the card) - labels describe a real number from the data
    picks = [("Marina Mabrey", "Top scorer"), ("Laura Juskaite", "Rookie · minutes leader"),
             ("Nyara Sabally", "Most net-positive duos"), ("Julie Allemand", "Most efficient")]
    cards = []
    for i, (name, tag) in enumerate(picks):
        r = season.loc[name]
        last = name.split()[-1]
        stats = [("PPG", f"{r.pts / r.gp:.1f}"), ("RPG", f"{r.reb / r.gp:.1f}"), ("APG", f"{r.ast / r.gp:.1f}"), ("TS%", f"{100 * r.ts:.1f}")]
        cards.append(f"""
        <div style="width:350px;height:720px;background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 18px 40px rgba(0,0,0,.35);
                    position:relative;font-family:Barlow,sans-serif;color:#12161d">
          <div style="height:330px;position:relative;background:linear-gradient(160deg,{BORDEAUX},#3d0d1f);overflow:hidden">
            <div style="position:absolute;right:-10px;top:-30px;font:800 230px/1 'Barlow Condensed';color:rgba(255,255,255,.12)">{r.jersey}</div>
            {"".join(f'<div style="position:absolute;left:0;top:{40 + j * 22}px;height:6px;width:{120 + (j * 37) % 90}px;background:rgba(255,255,255,.18);border-radius:3px"></div>' for j in range(6))}
            <img src="{uri(HEADS / (last.lower() + '.png'))}" style="position:absolute;left:50%;bottom:0;transform:translateX(-50%);height:300px">
            <img src="{uri(LOGOS / 'tor_white.png')}" style="position:absolute;left:18px;top:16px;width:64px">
            <div style="position:absolute;left:0;right:0;bottom:0;height:70px;background:linear-gradient(transparent,rgba(20,10,16,.85))"></div>
            <div style="position:absolute;left:20px;bottom:14px;color:#fff;font:700 15px 'IBM Plex Mono';letter-spacing:.1em">#{r.jersey} · {r.pos}</div>
          </div>
          <div style="padding:16px 20px 0">
            <div style="font:600 13px 'IBM Plex Mono';letter-spacing:.12em;color:{BORDEAUX};text-transform:uppercase">{tag}</div>
            <div style="font:800 40px/1 'Barlow Condensed';text-transform:uppercase;margin-top:4px">{name}</div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);margin-top:14px;border-top:2px solid #12161d">
              {"".join(f'<div style="padding-top:8px"><div style="font:800 30px/1 Barlow Condensed">{v}</div><div style="font:500 12px IBM Plex Mono;color:#7a8191">{k}</div></div>' for k, v in stats)}
            </div>
            <div style="margin-top:10px">{mini_hexes(name)}</div>
            <div style="font:400 12px 'IBM Plex Mono';color:#7a8191">{int(r.gp)} games · {r.mins / r.gp:.1f} min · {len(shots[shots.athlete_name_1 == name])} shots charted</div>
          </div>
          <div style="position:absolute;right:18px;top:346px;font:700 13px 'IBM Plex Mono';color:#c9ced8">{i + 1:02d}/04</div>
        </div>""")
    html = f"""
    <div style="width:1600px;height:900px;background:radial-gradient(circle at 30% 20%,#2b1420,#0f1217 70%);display:flex;flex-direction:column;
                align-items:center;justify-content:center;gap:26px">
      <div style="font:800 46px 'Barlow Condensed';color:#fff;letter-spacing:.02em;text-transform:uppercase">The 2026 Tempo card set
        <span style="font:500 16px 'IBM Plex Mono';color:#b7bdc9;letter-spacing:.1em;margin-left:14px">hex = where she shoots · darker = more makes</span></div>
      <div style="display:flex;gap:28px">{"".join(cards)}</div>
    </div>"""
    render("player-cards", html, 1600, 900)


# ---------------------------------------------------------------------------
# 5. "By the numbers" poster
# ---------------------------------------------------------------------------

def by_the_numbers():
    sh, fl, ro = summary["shot-lab"], summary["game-flow"], summary["rotation-lab"]
    # points per game lost because shots went in less than their location says they should
    fga_per_game = len(shots) / len(games)
    lost = (sh["pps"] - sh["xpps"]) * fga_per_game
    tiles = [
        (f"{wins}–{losses}", "record in year one", BORDEAUX, "#fff", 2),
        (f"{summary['expansion-class']['tor_elo']}", "final Elo · last in the WNBA", "#fff", "#12161d", 1),
        (f"{fl['runs_against']}", f"8–0 runs allowed (scored {fl['runs_for']})", NAVY, "#fff", 1),
        (f"{100 * fl['lead']:.0f}%", "of game time spent leading", "#fff", "#12161d", 1),
        (f"{lost:+.1f}".replace("-", "−"), "points a game lost to cold shooting", "#f3e6eb", BORDEAUX, 1),
        (f"{ro['lineups']}", "different starting lineups", "#12161d", "#fff", 1),
        (f"{100 * sh['opp_rim']:.0f}%", "of opponent shots at the rim", BORDEAUX, "#fff", 1),
    ]
    cells = "".join(f"""
      <div style="grid-column:span {span};background:{bg};color:{fg};padding:26px 30px;display:flex;flex-direction:column;justify-content:flex-end;
                  border-radius:6px;min-height:318px">
        <div style="font:800 {150 if span == 2 else 112}px/0.85 'Barlow Condensed';letter-spacing:-.02em">{big}</div>
        <div style="font:600 21px Barlow;margin-top:12px;opacity:.85">{small}</div>
      </div>""" for big, small, bg, fg, span in tiles)
    html = f"""
    <div style="width:1600px;height:900px;background:#f5f6f8;padding:40px;box-sizing:border-box;font-family:Barlow,sans-serif">
      <div style="display:flex;justify-content:space-between;align-items:end;margin-bottom:22px">
        <div style="font:800 64px/1 'Barlow Condensed';text-transform:uppercase;color:#12161d">Tempo by the numbers</div>
        <div style="font:500 16px 'IBM Plex Mono';color:#7a8191;letter-spacing:.1em">2026 REGULAR SEASON</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px">{cells}</div>
    </div>"""
    render("by-the-numbers", html, 1600, 900)


# ---------------------------------------------------------------------------
# 6. Animated Elo race: Valkyries '25 vs Tempo '26 vs Fire '26 (GIF)
# ---------------------------------------------------------------------------

def elo_race():
    import pyarrow.parquet as pq
    # all games since 2003 so Elo has history (same as the website)
    tb_all = pd.concat([pq.read_table(RAW / "team_box_hist.parquet").to_pandas(ignore_metadata=True),
                        pq.read_table(RAW / "team_box.parquet").to_pandas(ignore_metadata=True)], ignore_index=True)
    for c in ["team_score", "opponent_team_score"]:
        tb_all[c] = pd.to_numeric(tb_all[c], errors="coerce")
    # drop All-Star games: keep only teams that played 20+ games that season
    counts = tb_all.groupby(["season", "team_id"]).size()
    real = counts[counts >= 20].reset_index()[["season", "team_id"]]
    tb_all = tb_all.merge(real, on=["season", "team_id"]).merge(real.rename(columns={"team_id": "opponent_team_id"}),
                                                                on=["season", "opponent_team_id"])
    tb_all["game_date"] = pd.to_datetime(tb_all.game_date)
    log = elo.compute(tb_all.sort_values(["game_date", "game_id"]))
    reg = log[log.season_type.astype(str) == "2"]  # regular season only
    teams = [("gs", 129689, 2025, "#a47dd1", "Valkyries '25"), ("tor", TOR, 2026, "#c23a5c", "Tempo '26"),
             ("por", 132052, 2026, "#f070c0", "Fire '26")]
    paths = {k: [1300] + reg[(reg.team_id == tid) & (reg.season == yr)].post.tolist() for k, tid, yr, _, _ in teams}

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=110)
    fig.patch.set_facecolor("#12161d")
    ax.set_facecolor("#12161d")
    lines, heads = {}, {}
    for k, _, _, color, label in teams:
        lines[k], = ax.plot([], [], color=color, lw=4 if k == "tor" else 2.6, solid_capstyle="round")
        # logo that rides on the end of each line
        img = OffsetImage(plt.imread(LOGOS / f"{k}_sm.png"), zoom=0.2)
        heads[k] = AnnotationBbox(img, (0, 1300), frameon=True, bboxprops=dict(boxstyle="circle,pad=0.15", fc="#eef0f4", ec="none"))
        ax.add_artist(heads[k])
    ax.axhline(1300, color="#3a414e", lw=1, ls="--")
    ax.set_xlim(0, 47)
    ax.set_ylim(1200, 1520)
    ax.tick_params(colors="#8a91a0", labelsize=10)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.grid(axis="y", color="#222833")
    ax.set_xlabel("game number in year one", color="#8a91a0")
    ax.text(0, 1.06, "THE EXPANSION ELO RACE", transform=ax.transAxes, color="#eef0f4", fontsize=20, fontweight="bold")
    ax.text(0, 1.015, "new teams start at 1300 · league average is 1500", transform=ax.transAxes, color="#8a91a0", fontsize=10)
    counter = ax.text(0.98, 0.93, "", transform=ax.transAxes, ha="right", color="#eef0f4", fontsize=26, fontweight="bold")
    labels = {k: ax.text(0, 0, "", color=c, fontsize=10, fontweight="bold") for k, _, _, c, _ in teams}

    frames = list(range(1, 45)) + [44] * 12  # hold the last frame for a moment

    def draw(f):
        for k, _, _, _, label in teams:
            p = paths[k][: f + 1]
            lines[k].set_data(range(len(p)), p)
            heads[k].xybox = (len(p) - 1, p[-1])
            heads[k].xy = (len(p) - 1, p[-1])
            labels[k].set_position((len(p) + 0.6, p[-1] - 4))
            labels[k].set_text(f"{label} {p[-1]:.0f}")
        counter.set_text(f"G{f}")
        return []

    from matplotlib.animation import FuncAnimation, PillowWriter
    anim = FuncAnimation(fig, draw, frames=frames, blit=False)
    anim.save(OUT / "elo-race.gif", writer=PillowWriter(fps=8))
    plt.close(fig)
    # Pillow merges identical frames, so make the last frame stay on screen longer by hand
    gif = Image.open(OUT / "elo-race.gif")
    frames_out = []
    for i in range(gif.n_frames):
        gif.seek(i)
        frames_out.append(gif.convert("RGB").quantize(colors=96))
    durations = [125] * (len(frames_out) - 1) + [2500]
    frames_out[0].save(OUT / "elo-race.gif", save_all=True, append_images=frames_out[1:], duration=durations, loop=0, optimize=True)
    print("made", (OUT / "elo-race.gif").relative_to(ROOT))


# ---------------------------------------------------------------------------
# 7. Shot constellation: every shot of the season on a full court, glowing
# ---------------------------------------------------------------------------

def constellation():
    W, H = 1600, 1000
    k = 16                      # pixels per foot
    ox, oy = (W - 94 * k) / 2, 150  # top-left corner of the court in the picture
    # all shots in Tempo games (both teams), not just Tempo shots
    allp = pbp[(pbp.home_team_id == TOR) | (pbp.away_team_id == TOR)]
    s2 = allp[allp.shooting_play.astype(bool) & ~allp.type_text.str.contains("Free Throw")]
    s2 = s2[(s2.coordinate_y_raw <= 40) & s2.coordinate_x_raw.between(0, 50)]
    glow, dots = [], []
    rng = np.random.default_rng(7)  # fixed seed so the picture is the same every time
    for r in s2.itertuples():
        # ESPN rounds locations to whole feet, so add a tiny random wiggle (under half a foot)
        # so the dots look like stars instead of a grid
        x = float(r.coordinate_x_raw) + rng.uniform(-0.45, 0.45)
        y = float(r.coordinate_y_raw) + rng.uniform(-0.45, 0.45)
        if not (0.3 <= x <= 49.7 and -4.9 <= y <= 40):
            continue  # skip anything that would land outside the court lines
        if r.team_id == TOR:
            # Tempo attack the RIGHT basket: distance from the basket goes to the left
            cx, cy = ox + (94 - 5.25 - y) * k, oy + x * k
        else:
            # opponents attack the LEFT basket
            cx, cy = ox + (5.25 + y) * k, oy + (50 - x) * k
        if r.scoring_play:
            col = "#ff6b95" if r.team_id == TOR else "#9fb4e0"
            glow.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{col}"/>')
            dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.9" fill="#fff"/>')
        else:
            # misses are tiny and faint, like far-away stars
            dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="1.3" fill="#ffffff" opacity="0.28"/>')
    # court lines (very faint): outline, half court, both paints, both 3-point arcs
    c3 = np.sqrt(22.15 ** 2 - 9)
    line = 'fill="none" stroke="#ffffff" stroke-opacity="0.13" stroke-width="1.5"'
    court = [f'<rect x="{ox}" y="{oy}" width="{94 * k}" height="{50 * k}" {line}/>',
             f'<line x1="{ox + 47 * k}" y1="{oy}" x2="{ox + 47 * k}" y2="{oy + 50 * k}" {line}/>',
             f'<circle cx="{ox + 47 * k}" cy="{oy + 25 * k}" r="{6 * k}" {line}/>']
    for side in (0, 1):
        bx = ox + (5.25 if side == 0 else 94 - 5.25) * k   # basket x
        edge = ox if side == 0 else ox + 94 * k              # baseline x
        d = 1 if side == 0 else -1                            # direction into the court
        court.append(f'<rect x="{min(edge, edge + d * 19 * k)}" y="{oy + 17 * k}" width="{19 * k}" height="{16 * k}" {line}/>')
        court.append(f'<circle cx="{bx}" cy="{oy + 25 * k}" r="{0.75 * k}" {line}/>')
        sweep = 1 if side == 0 else 0
        court.append(f'<path d="M {edge} {oy + (25 - c3) * k} L {bx + d * 3 * k} {oy + (25 - c3) * k} '
                     f'A {22.15 * k} {22.15 * k} 0 0 {sweep} {bx + d * 3 * k} {oy + (25 + c3) * k} L {edge} {oy + (25 + c3) * k}" {line}/>')
    tor_n = int((s2.team_id == TOR).sum())
    opp_n = len(s2) - tor_n
    html = f"""
    <div style="width:{W}px;height:{H}px;position:relative;font-family:Barlow,sans-serif;color:#fff;
                background:radial-gradient(ellipse at 50% 55%,#1c1220 0%,#0a0b10 70%)">
      <svg width="{W}" height="{H}" style="position:absolute;inset:0">
        <defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter></defs>
        {"".join(court)}
        <g filter="url(#glow)" opacity="0.55">{"".join(glow)}</g>
        {"".join(dots)}
      </svg>
      <div style="position:absolute;left:0;right:0;top:40px;text-align:center">
        <div style="font:800 64px/1 'Barlow Condensed';letter-spacing:.02em">EVERY SHOT OF 2026</div>
        <div style="font:500 16px 'IBM Plex Mono';letter-spacing:.12em;color:#b7bdc9;margin-top:10px">
          <span style="color:#9fb4e0">OPPONENTS · {opp_n:,} SHOTS</span> &nbsp;←&nbsp; glowing = made &nbsp;→&nbsp; <span style="color:#ff6b95">TEMPO · {tor_n:,} SHOTS</span></div>
      </div>
      <img src="{uri(LOGOS / 'tor_white.png')}" style="position:absolute;right:56px;bottom:26px;width:90px;opacity:.9">
      <div style="position:absolute;left:56px;bottom:34px;font:400 14px 'IBM Plex Mono';color:#8a91a0">
        Toronto attacks the right basket · opponents attack the left · 44 games · ESPN shot locations</div>
    </div>"""
    render("constellation", html, W, H)


# ---------------------------------------------------------------------------
# 8. "Unknown Pleasures" ridgeline: every game's margin, stacked like the album cover
# ---------------------------------------------------------------------------

def ridgeline():
    import flow  # my helper that turns play-by-play into seconds + margin
    p = flow.tempo_pbp()
    W, H = 1200, 1500
    left, right, top = 260, 940, 250   # where the lines go
    gap, amp = 25, 2.8                 # space between games, pixels per point of margin
    t_grid = np.arange(0, 2401, 15)    # every 15 seconds of regulation
    layers = []
    for i, g in games.iterrows():
        gp = p[(p.game_id == g.game_id) & (p.t <= 2400)]
        # margin at each 15-second mark (starting 0-0)
        m = np.interp(t_grid, np.r_[0, gp.t.to_numpy(float)], np.r_[0, gp.m.to_numpy(float)])
        base = top + i * gap
        xs = left + t_grid / 2400 * (right - left)
        ys = base - m * amp            # leading = line goes UP
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
        win = g.margin > 0
        stroke = "#ff6b95" if win else "#eef0f4"
        # fill the area under the line with the background colour so it hides the lines behind it
        layers.append(f'<polygon points="{left},{base + 60} {pts} {right},{base + 60}" fill="#0a0b10"/>'
                      f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="{2.2 if win else 1.6}" stroke-linejoin="round"/>')
        # small label on the left: opponent and result
        layers.append(f'<text x="{left - 14}" y="{base + 4}" text-anchor="end" font-family="IBM Plex Mono" font-size="11" '
                      f'fill="{"#ff6b95" if win else "#5d6472"}">{g.game_date.strftime("%b %-d").upper()} {g.opponent_team_abbreviation} '
                      f'{g.team_score}-{g.opponent_team_score}</text>')
    html = f"""
    <div style="width:{W}px;height:{H}px;background:#0a0b10;position:relative;color:#eef0f4;font-family:Barlow,sans-serif">
      <svg width="{W}" height="{H}" style="position:absolute;inset:0">{"".join(layers)}</svg>
      <div style="position:absolute;left:0;right:0;top:70px;text-align:center">
        <div style="font:800 72px/1 'Barlow Condensed';letter-spacing:.08em">UNKNOWN PRESSURES</div>
        <div style="font:500 15px 'IBM Plex Mono';letter-spacing:.14em;color:#8a91a0;margin-top:12px">
          TORONTO TEMPO · 2026 · 44 GAMES · TIP-OFF TO FINAL BUZZER</div>
      </div>
      <div style="position:absolute;left:0;right:0;bottom:44px;text-align:center;font:400 14px 'IBM Plex Mono';color:#8a91a0">
        each line is one game's score margin · peaks = Toronto leading · <span style="color:#ff6b95">pink = win</span></div>
    </div>"""
    render("ridgeline", html, W, H)


# ---------------------------------------------------------------------------
# 9. Rotation ring: who played in every game, as a circle
# ---------------------------------------------------------------------------

def rotation_ring():
    S = 1300
    cx, cy = S / 2, S / 2 + 40
    r0, ring = 190, 26                     # inner radius and width of each player's ring
    order = season.sort_values("mins", ascending=False).head(14).index.tolist()  # 14 most-used players
    gap_deg = 34                           # empty slice at the top where the names go
    n = len(games)
    span = (360 - gap_deg) / n             # degrees per game
    gid = {g: i for i, g in enumerate(games.game_id)}
    allbox = pb[pb.team_id == TOR]         # includes did-not-play rows
    parts = []

    def wedge(r_in, r_out, a0, a1):
        # SVG path for one ring segment ("annular wedge"), angles in degrees, 0 = straight up
        a0r, a1r = np.radians(a0 - 90), np.radians(a1 - 90)
        p = [(cx + r_out * np.cos(a0r), cy + r_out * np.sin(a0r)), (cx + r_out * np.cos(a1r), cy + r_out * np.sin(a1r)),
             (cx + r_in * np.cos(a1r), cy + r_in * np.sin(a1r)), (cx + r_in * np.cos(a0r), cy + r_in * np.sin(a0r))]
        return (f"M {p[0][0]:.1f} {p[0][1]:.1f} A {r_out} {r_out} 0 0 1 {p[1][0]:.1f} {p[1][1]:.1f} "
                f"L {p[2][0]:.1f} {p[2][1]:.1f} A {r_in} {r_in} 0 0 0 {p[3][0]:.1f} {p[3][1]:.1f} Z")

    for j, name in enumerate(order):
        r_in = r0 + j * ring
        r_out = r_in + ring - 3
        rows = allbox[allbox.athlete_display_name == name]
        for r in rows.itertuples():
            i = gid.get(r.game_id)
            if i is None:
                continue
            a0 = gap_deg / 2 + i * span + 0.6
            a1 = a0 + span - 1.2
            if r.minutes > 0:
                # more minutes = brighter bordeaux/pink
                t = min(1, r.minutes / 36)
                color = f"color-mix(in oklab, #ff6b95 {int(100 * t)}%, #2a1820)"
                parts.append(f'<path d="{wedge(r_in, r_out, a0, a1)}" fill="{color}"/>')
            elif str(r.did_not_play) == "True" and "COACH" not in str(r.reason).upper():
                # missed with injury/illness: small x in the middle of the cell
                am = np.radians((a0 + a1) / 2 - 90)
                rm = (r_in + r_out) / 2
                px, py = cx + rm * np.cos(am), cy + rm * np.sin(am)
                parts.append(f'<path d="M {px - 4} {py - 4} L {px + 4} {py + 4} M {px + 4} {py - 4} L {px - 4} {py + 4}" stroke="#7e9bd0" stroke-width="1.6"/>')
        # player's last name in the gap at the top
        ny = cy - (r_in + r_out) / 2 + 4
        parts.append(f'<text x="{cx}" y="{ny:.1f}" text-anchor="middle" font-family="Barlow Condensed" font-weight="700" '
                     f'font-size="13" fill="#d7dbe2" letter-spacing="0.5">{name.split()[-1].upper()}</text>')
    # month labels around the outside
    seen = set()
    for i, g in games.iterrows():
        mon = g.game_date.strftime("%b").upper()
        if mon in seen:
            continue
        seen.add(mon)
        a = np.radians(gap_deg / 2 + i * span - 90)
        rr = r0 + len(order) * ring + 26
        parts.append(f'<text x="{cx + rr * np.cos(a):.1f}" y="{cy + rr * np.sin(a) + 5:.1f}" text-anchor="middle" '
                     f'font-family="IBM Plex Mono" font-size="15" fill="#ff6b95">{mon}</text>')
    lineups = summary["rotation-lab"]["lineups"]
    html = f"""
    <div style="width:{S}px;height:{S + 80}px;background:#0f1217;position:relative;color:#eef0f4;font-family:Barlow,sans-serif">
      <svg width="{S}" height="{S + 80}" style="position:absolute;inset:0">{"".join(parts)}</svg>
      <div style="position:absolute;left:0;right:0;top:{cy - 70}px;text-align:center">
        <div style="font:800 110px/0.9 'Barlow Condensed'">{lineups}</div>
        <div style="font:500 14px 'IBM Plex Mono';letter-spacing:.14em;color:#8a91a0">STARTING LINEUPS</div>
      </div>
      <div style="position:absolute;left:44px;top:36px">
        <div style="font:800 50px 'Barlow Condensed';text-transform:uppercase">The rotation ring</div>
        <div style="font:400 17px Barlow;color:#b7bdc9;max-width:420px">Each ring is a player and each slice is a game, clockwise from opening night. Brighter = more minutes. <span style="color:#7e9bd0">✕ = missed through injury or illness.</span></div>
      </div>
      <img src="{uri(LOGOS / 'tor_white.png')}" style="position:absolute;right:44px;top:44px;width:110px;opacity:.9">
    </div>"""
    render("rotation-ring", html, S, S + 80)


# ---------------------------------------------------------------------------
# 10. Shot fans: where each player shoots from, as a polar "fan"
# ---------------------------------------------------------------------------

def shot_fans():
    top8 = shots.athlete_name_1.value_counts().head(8).index.tolist()
    bands = [("Rim", "#ff6b95", 0, 4), ("Midrange", "#b33a55", 4, 22.15), ("Three", "#7e9bd0", 22.15, 99)]
    cards = []
    for name in top8:
        s = shots[shots.athlete_name_1 == name]
        dx, dy = s.coordinate_x_raw.astype(float) - 25, s.coordinate_y_raw.astype(float)
        dist = np.hypot(dx, dy)
        ang = np.degrees(np.arctan2(dy.clip(lower=0), dx))  # 0 = right baseline, 180 = left baseline
        nb = 12                                             # 12 directions, 15 degrees each
        b = np.clip((ang // (180 / nb)).astype(int), 0, nb - 1)
        three = s.points_attempted == 3
        W2, H2 = 300, 190
        cx, cy, R = W2 / 2, 170, 150
        paths = []
        share_max = 0.17                                    # a direction with 17% of shots fills the radius
        for i in range(nb):
            inb = b == i
            inner = 0.0
            for band, color, lo, hi in bands:
                if band == "Three":
                    sel = inb & three
                elif band == "Rim":
                    sel = inb & ~three & (dist < 4)
                else:
                    sel = inb & ~three & (dist >= 4)
                share = sel.sum() / len(s)
                if share == 0:
                    continue
                # stack the bands outward, square root so the AREA matches the share
                r_in = R * np.sqrt(inner / share_max)
                inner += share
                r_out = R * np.sqrt(min(inner, share_max) / share_max)
                # angle 0 = right, 180 = left; in the picture the basket is at the bottom
                a0, a1 = np.radians(180 - i * 15 - 1), np.radians(180 - (i + 1) * 15 + 1)
                pts = [(cx + r_out * np.cos(a0), cy - r_out * np.sin(a0)), (cx + r_out * np.cos(a1), cy - r_out * np.sin(a1)),
                       (cx + r_in * np.cos(a1), cy - r_in * np.sin(a1)), (cx + r_in * np.cos(a0), cy - r_in * np.sin(a0))]
                paths.append(f'<path d="M {pts[0][0]:.1f} {pts[0][1]:.1f} A {r_out:.1f} {r_out:.1f} 0 0 1 {pts[1][0]:.1f} {pts[1][1]:.1f} '
                             f'L {pts[2][0]:.1f} {pts[2][1]:.1f} A {r_in:.1f} {r_in:.1f} 0 0 0 {pts[3][0]:.1f} {pts[3][1]:.1f} Z" fill="{color}"/>')
        guide = (f'<path d="M {cx - R} {cy} A {R} {R} 0 0 1 {cx + R} {cy}" fill="none" stroke="#2a303b"/>'
                 f'<line x1="{cx - R}" y1="{cy}" x2="{cx + R}" y2="{cy}" stroke="#2a303b"/>'
                 f'<circle cx="{cx}" cy="{cy}" r="4" fill="#eef0f4"/>')
        r = season.loc[name]
        cards.append(f"""
        <div style="background:#151920;border:1px solid #232934;border-radius:14px;padding:18px 18px 14px;display:grid;gap:4px">
          <svg width="{W2}" height="{H2}">{guide}{"".join(paths)}</svg>
          <div style="font:800 26px/1 'Barlow Condensed';text-transform:uppercase;margin-top:6px">{name}</div>
          <div style="font:400 13px 'IBM Plex Mono';color:#8a91a0">#{r.jersey} · {len(s)} shots · {100 * r.ts:.1f} TS%</div>
        </div>""")
    legend = "".join(f'<span style="display:inline-flex;align-items:center;gap:8px"><i style="width:14px;height:14px;background:{c};display:inline-block;border-radius:3px"></i>{n}</span>'
                     for n, c, _, _ in bands)
    html = f"""
    <div style="width:1600px;height:900px;background:#0f1217;color:#eef0f4;font-family:Barlow,sans-serif;padding:44px 60px;box-sizing:border-box">
      <div style="display:flex;justify-content:space-between;align-items:end;margin-bottom:26px">
        <div><div style="font:800 56px/1 'Barlow Condensed';text-transform:uppercase">Shot fans</div>
        <div style="font:400 17px Barlow;color:#b7bdc9;margin-top:6px">Each fan opens from the basket. Petal = direction, length = share of her shots, colour = distance.</div></div>
        <div style="display:flex;gap:22px;font:500 15px 'IBM Plex Mono';color:#d7dbe2">{legend}</div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px">{"".join(cards)}</div>
    </div>"""
    render("shot-fans", html, 1600, 900)


# ---------------------------------------------------------------------------
# 11. The 2027 big board (top 10 from the Draft Lab page)
# ---------------------------------------------------------------------------

def big_board():
    import re
    # the Draft Lab build put its data inside the page, so read it back out of the html
    html_page = (ROOT / "docs" / "draft-lab" / "index.html").read_text()
    data = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html_page, re.S).group(1))
    # same scoring as the page's default setting: 60% talent, 40% fit
    top = sorted(data["prospects"], key=lambda p: -(0.6 * p["talent"] + 0.4 * p["fit"]))[:10]
    cards = []
    for i, p in enumerate(top, 1):
        ht = f"{p['ht'] // 12}'{p['ht'] % 12}\""
        img = f'<img src="{p["img"]}" style="width:100%;height:100%;object-fit:cover;object-position:top">' if p["img"] else ""
        cards.append(f"""
        <div style="background:#151920;border:1px solid #232934;border-radius:16px;padding:18px;display:grid;gap:10px;position:relative;overflow:hidden">
          <div style="position:absolute;right:12px;top:-6px;font:800 92px/1 'Barlow Condensed';color:rgba(255,107,149,.14)">{i}</div>
          <div style="width:96px;height:96px;border-radius:50%;overflow:hidden;background:#2a303b;border:3px solid #ff6b95">{img}</div>
          <div><div style="font:800 26px/1 'Barlow Condensed';text-transform:uppercase">{p['name']}</div>
          <div style="font:400 13px 'IBM Plex Mono';color:#8a91a0;margin-top:4px">{p['school']}</div>
          <div style="font:400 13px 'IBM Plex Mono';color:#8a91a0">{p['pos']} · {ht} · BPM {p['bpm']}</div></div>
          <div style="display:grid;grid-template-columns:52px 1fr;gap:6px 8px;align-items:center;font:500 12px 'IBM Plex Mono';color:#b7bdc9">
            <span>TALENT</span><span style="height:8px;background:#2a303b"><i style="display:block;height:8px;width:{p['talent']}%;background:#7e9bd0"></i></span>
            <span>FIT</span><span style="height:8px;background:#2a303b"><i style="display:block;height:8px;width:{p['fit']}%;background:#ff6b95"></i></span>
          </div>
          <div style="font:500 13px 'IBM Plex Mono';color:#d7dbe2">{p['pts']} pts · {p['reb']} reb · {p['blk']} blk</div>
        </div>""")
    html = f"""
    <div style="width:1600px;height:850px;background:radial-gradient(circle at 80% 0%,#2b1420,#0f1217 60%);color:#eef0f4;font-family:Barlow,sans-serif;padding:44px 56px;box-sizing:border-box">
      <div style="display:flex;justify-content:space-between;align-items:end;margin-bottom:26px">
        <div><div style="font:800 64px/1 'Barlow Condensed';text-transform:uppercase">The 2027 big board</div>
        <div style="font:400 18px Barlow;color:#b7bdc9;margin-top:8px">Toronto's top 10 college seniors, weighted 60% talent and 40% fit for what the Tempo need: rim protection, defensive rebounding and defense.</div></div>
        <img src="{uri(LOGOS / 'tor_white.png')}" style="width:120px;opacity:.9">
      </div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:18px">{"".join(cards)}</div>
    </div>"""
    render("big-board", html, 1600, 850)


if __name__ == "__main__":
    banner()
    season_ring()
    player_cards()
    by_the_numbers()
    elo_race()
    constellation()
    ridgeline()
    rotation_ring()
    shot_fans()
    big_board()
