<a href="https://jordanngo205.github.io/toronto-tempo-analytics/"><img src="readme_art/out/banner.png" alt="Tempo Lab: Toronto's first season, broken down with data" width="100%"></a>

<div align="center">

[![Open the live site](https://img.shields.io/badge/OPEN%20THE%20LIVE%20SITE-%E2%86%92-8a1f42?style=for-the-badge)](https://jordanngo205.github.io/toronto-tempo-analytics/)
[![Python](https://img.shields.io/badge/Python-3.14-33476d?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![sportsdataverse](https://img.shields.io/badge/data-sportsdataverse-33476d?style=for-the-badge)](https://py.sportsdataverse.org/)
[![Hand-built SVG](https://img.shields.io/badge/charts-hand--built%20SVG-12161d?style=for-the-badge)](docs/assets/kit.js)

</div>

The Toronto Tempo joined the WNBA in 2026 and went **11–33**. This repo pulls every game, shot and lineup from that season and turns them into six interactive pages. The goal is to explain why the season went the way it did, and who Toronto should draft for year two.

<img src="readme_art/out/by-the-numbers.png" alt="Tempo by the numbers" width="100%">

---

## Every shot of the season

<img src="readme_art/out/constellation.png" alt="Every shot of 2026 on a full court, made shots glowing" width="100%">

Each dot is one field-goal attempt from a Tempo game, and the glowing dots are makes. Toronto attacks the right basket and its opponents attack the left. Both ends are crowded around the rim, and the opponent end is brighter: opponents made more of their shots than Toronto did.

---

## The expansion race

The Tempo, the 2026 Portland Fire and the 2025 Golden State Valkyries all started at the same Elo rating, 1300. Golden State went 23–21 and made the playoffs in year one. Toronto finished last in the league.

<div align="center"><img src="readme_art/out/elo-race.gif" alt="Animated Elo race between the three expansion teams" width="90%"></div>

## The season in a circle

<table>
<tr>
<td width="55%"><a href="https://jordanngo205.github.io/toronto-tempo-analytics/#season"><img src="readme_art/out/season-circle.png" alt="Every Tempo game arranged in a circle"></a></td>
<td width="45%">

**44 games, one picture.** Each bar is one game and points toward the winner: in toward the Tempo logo for a win, out toward the opponent's logo for a loss. Longer bar = bigger margin. On the [live version](https://jordanngo205.github.io/toronto-tempo-analytics/#season), every bar links to that game's recap and box score.

- **9 of the 11 wins** came in May and June (top right).
- After beating New York on July 12, Toronto won only once more: **82–79 over Portland** on August 21.
- The biggest win was **125–97** over LA on June 25. The worst loss was **69–106** at home to New York on September 20.

</td>
</tr>
</table>

## Unknown Pressures

<table>
<tr>
<td width="50%"><img src="readme_art/out/ridgeline.png" alt="All 44 games as stacked margin lines, Joy Division style"></td>
<td width="50%"><img src="readme_art/out/rotation-ring.png" alt="Rotation ring: minutes for every player in every game"></td>
</tr>
<tr>
<td><sub><b>Unknown Pressures.</b> Every game's score margin from tip-off to the final buzzer, stacked like the Joy Division album cover. Peaks mean Toronto was leading, and the 11 pink lines are wins. Most of the pink is near the top, in May and June.</sub></td>
<td><sub><b>The rotation ring.</b> Each ring is a player and each slice is a game. Laura Juskaite, the innermost ring, played all 44 games. Brittney Sykes played only 17, and the ✕ marks show how much of the roster spent the season injured. Blue on the inner and outer rings marks the 11 wins.</sub></td>
</tr>
</table>

## The card set

<img src="readme_art/out/player-cards.png" alt="Trading cards for four Tempo players with mini shot charts" width="100%">

Each card's mini shot chart comes from that player's own 2026 shots: hex size shows where she shoots, and darker means more makes.

<img src="readme_art/out/shot-fans.png" alt="Who should take which shots: shot fans for eight Tempo players, coloured by points per shot vs the WNBA" width="100%">

**Who should take which shots.** Each fan opens from the basket. Petal length is how often she shoots from there, and colour is points per shot compared with the WNBA from the same spot. Marina Mabrey's corner threes (1.38 points a shot) are worth taking more often. Maria Conde scored just 0.74 points a shot at the rim, 0.57 below the league. The samples behind some notes are small (20-35 shots), so treat them as leads to check on film.

---

## Who should Toronto draft?

<img src="readme_art/out/big-board.png" alt="The 2027 big board: Toronto's top 10 college seniors" width="100%">

The [**Draft Lab**](https://jordanngo205.github.io/toronto-tempo-analytics/draft-lab/) starts with what broke: Toronto was last in defensive rating, opponent eFG%, opponent shots at the rim and blocks. Then it follows every WNBA draftee from 2018 to 2025 back to college to see what actually translates. After you account for draft slot, box plus-minus, defensive BPM and steals still predicted WNBA minutes. College scoring didn't. Every 2026-27 senior is scored on **talent** (a ridge model plus sportsdataverse's draft projection) and **fit** (blocks, defensive rebounding, defensive BPM, size). A slider lets you trade one for the other, a toggle switches to the consensus order, each prospect gets an archetype ("3 & D", "Rim protector"...), and a list flags the players the model likes more than consensus: the late-round targets.

---

## What's on the site

| | Page | What you can do there |
|:---:|---|---|
| **01** | [**The Expansion Class**](https://jordanngo205.github.io/toronto-tempo-analytics/expansion-class/) | Compare the Tempo, Fire and Valkyries with Elo, the Four Factors, hex shot maps and roster experience. The 2006 Sky and 2008 Dream are included as history. |
| **02** | [**Shot Lab**](https://jordanngo205.github.io/toronto-tempo-analytics/shot-lab/) | Pick any Tempo shooter and see every make and miss. Compare expected vs actual points per shot for every player in the league. |
| **03** | [**Rotation Lab**](https://jordanngo205.github.io/toronto-tempo-analytics/rotation-lab/) | See who played in every game, a network of which pairs worked together, and lineup results. |
| **04** | [**Game Flow**](https://jordanngo205.github.io/toronto-tempo-analytics/game-flow/) | See every minute of every game, every 8–0 run, and upsets measured against pregame odds. |
| **05** | [**Game Center**](https://jordanngo205.github.io/toronto-tempo-analytics/game-center/) | Pick any of the 44 games for a full recap: game flow, shot charts and box scores. |
| **06** | [**Draft Lab**](https://jordanngo205.github.io/toronto-tempo-analytics/draft-lab/) | See what Toronto needs, which college numbers translate to the WNBA, and an adjustable 2027 big board of the senior class. |

---

## How it's built

```mermaid
flowchart LR
    A[sportsdataverse<br/>WNBA + college<br/>pbp · box scores · lineups · drafts] -->|data/pull.py| B[(data/raw<br/>parquet files)]
    B --> C1[01 build.py<br/>Elo · Four Factors]
    B --> C2[02 build.py<br/>shot zones]
    B --> C3[03 build.py<br/>rotations]
    B --> C4[04 build.py<br/>runs · game grid]
    B --> C5[05 build.py<br/>game recaps]
    B --> C6[06 build.py<br/>draft board]
    E[elo.py · flow.py<br/>common.py] -.-> C1 & C4 & C5
    C1 & C2 & C3 & C4 & C5 & C6 -->|lab.py| D[docs/<br/>HTML pages]
    K[docs/assets/kit.js<br/>my SVG chart helpers] -.-> D
    D -->|GitHub Pages| W((live site))
    B --> R[readme_art/make_art.py] --> P[README graphics]
```

- **Python** pulls the data, does all the math, and saves the results as JSON inside each page.
- **JavaScript** draws every chart as SVG by hand, without a chart library. The shared helpers are in [`docs/assets/kit.js`](docs/assets/kit.js).
- **Every graphic here is also on the site**, on the page it belongs to, and the card set has its own [Players page](https://jordanngo205.github.io/toronto-tempo-analytics/players/) with a card for every player.
- **The README graphics** are built from the same data by [`readme_art/make_art.py`](readme_art/make_art.py): the banner, by-the-numbers poster, Elo race GIF, shot constellation, season ring, Unknown Pressures ridgeline, rotation ring, card set and shot fans. Each one is a small HTML poster screenshotted with headless Chrome, except the GIF, which matplotlib renders.
- Everything uses the official team colours: Tempo bordeaux and navy, Valkyries violet and Fire pink.

## Methods

| Metric | How it's calculated |
|---|---|
| **Elo** | Every WNBA game since 2003: K = 25, 60-point home edge, margin-of-victory multiplier, 40% regression to 1500 between seasons, new teams start at 1300. Settings tuned on 2004–23 and tested on 2024–26 ([`elo.py`](elo.py)) |
| **Possessions** | FGA − ORB + TOV + 0.44 × FTA |
| **Expected pts/shot** | League points per shot for the zone each shot came from |
| **Shot making** | Actual points per shot minus expected |
| **Usage** | (FGA + 0.44 × FTA + TOV) ÷ team plays while the player was on the court |
| **Runs** | Points in a row by one team with no opposing points between them |

## Run it yourself

```bash
git clone https://github.com/jordanngo205/toronto-tempo-analytics.git
cd toronto-tempo-analytics
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python data/pull.py              # WNBA 2025–26 + history, college 2015–26, drafts
.venv/bin/python build_site.py             # rebuild every page in docs/
.venv/bin/python readme_art/make_art.py    # rebuild the README graphics (needs Google Chrome)
open docs/index.html
```

<details>
<summary><b>Repo layout</b></summary>

```
├── 01_expansion_class/   build.py · page.html  → docs/expansion-class/
├── 02_shot_diet/         build.py · page.html  → docs/shot-lab/      (+ analysis.py: static PNG charts)
├── 03_player_impact/     build.py · page.html  → docs/rotation-lab/  (+ analysis.py)
├── 04_close_games/       build.py · page.html  → docs/game-flow/     (+ analysis.py)
├── 05_game_recap/        build.py · page.html  → docs/game-center/   (+ recap.py: PNG recap cards)
├── 06_draft_lab/         build.py · page.html  → docs/draft-lab/
├── readme_art/           make_art.py → out/ (the graphics in this README)
├── data/pull.py          sportsdataverse → data/raw/ (not committed)
├── common.py · elo.py · flow.py · lab.py · build_site.py · home.html
├── assets/               team logos and player headshots
└── docs/                 the GitHub Pages site
```
</details>

---

<div align="center">

Built by **Jordan Ngo** · data from [sportsdataverse](https://py.sportsdataverse.org/) · inspired by [Rise of the Valkyries](https://riseofthevalkyries.substack.com/) and [Neil Paine](https://neilpaine.substack.com/t/basketball)

<sub>Unofficial fan project. Team names, logos and player photos belong to their owners.</sub>

</div>
