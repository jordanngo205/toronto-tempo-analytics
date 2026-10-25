# Toronto Tempo Analytics

**Live page: [The Expansion Class](https://jordanngo205.github.io/toronto-tempo-analytics/)**

Toronto Tempo analytics, built on [sportsdataverse](https://py.sportsdataverse.org/) WNBA data.
Inspired by [Rise of the Valkyries](https://riseofthevalkyries.substack.com/) (film + data on every
WNBA team, focused on Golden State). This is the Toronto version.

## Setup
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python data/pull.py        # caches 2025-26 data + 2003-24 history to data/raw/ (parquet)
```
Every project is a single script: `.venv/bin/python <folder>/analysis.py` (01 uses `build.py`, which also writes `docs/index.html` for GitHub Pages). Charts and CSVs land in that folder.

## Projects
| # | Project | Question | Output |
|---|---------|----------|--------|
| 01 | **Expansion Class** | Valkyries '25 vs Tempo '26 vs Fire '26, plus Sky '06 and Dream '08: Elo (Neil Paine style), Four Factors, hex shot maps, roster experience, head-to-heads. `build.py` creates the data and the page. | `expansion_class.html` ([live page](https://jordanngo205.github.io/toronto-tempo-analytics/)) |
| 02 | Shot Diet | Where do the Tempo shoot from, where do opponents score on them, and how efficient is each zone? | `shot_zones.png`, `player_shot_mix.png` |
| 03 | Player Impact | Who carried the offense efficiently, and which pairs win their minutes? | `usage_vs_ts.png`, `pair_chemistry.png` |
| 04 | Close Games | When do the Tempo lose games? | `margin_worms.png`, `quarter_margin.png` |
| 05 | Game Recap | One-page card for any game, like a Substack recap. `recap.py [game_id]` | `recaps/*.png` |

## 2026 findings so far
- **The offence was fine, the defence wasn't.** Offensive rating ranked 10th, close to the 2025 Valkyries (9th), and both Toronto and Portland scored more efficiently than Golden State's year-one team. Defence ranked 15th of 15, compared with 3rd for GS. Opponent eFG% ranked 15th and defensive rebounding 14th.
- **By Elo, Toronto finished last (1234)**, below the 2006 Sky and 2008 Dream. Portland rose to 1369.
- **The season came apart after game ~25.** The rolling net rating dropped from about -5 to about -20 and never recovered.
- **Opponents lived at the rim.** 33% of opponent shots came at the rim (league average: 27%), at 1.33 points per shot.
- **Allemand was very efficient on low usage** (67.6% TS, 10% usage). Mabrey carried 30% usage at an above-average 60% TS. Conde (48% TS) and Key (42% TS) are the efficiency holes.
- **Sabally and Sykes combos hold up.** Most Fagbenle and Nurse pairings were deep in the red.
- **The losses were gradual, not collapses.** The Tempo lost every quarter on average, with the biggest deficits in Q2 and Q3. They went 6-8 in clutch games.

## Ideas for next
- Opponent scouting previews, like the Substack's Finals "mega-previews": run 01-03 for any team abbreviation
- Rim protection deep-dive: who's on the floor when opponents get to the rim (`load_wnba_stats_pbp` + on-court)
- 2027 offseason: expansion draft/free-agent targets using `load_wnba_player_impact` (RAPM / DARKO)
- Kia Nurse / Canadian player tracker
- Automated weekly recaps: schedule `05_game_recap` after each game next season

## Caveats
- `plus_minus` and lineup data come from NBA-stats-style tracking. The lineup table is truncated league-wide, so pair minutes are a lower bound.
- The player impact feed (RAPM / BPM) minutes don't match the box scores. It's used only as a reference column in `tempo_players.csv`.
