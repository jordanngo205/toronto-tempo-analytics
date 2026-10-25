"""Pull WNBA data from sportsdataverse and cache it as parquet in data/raw/.

Run once (or after new games): .venv/bin/python data/pull.py
"""
from pathlib import Path

import sportsdataverse.wnba as w

# save everything next to this file in data/raw/
RAW = Path(__file__).parent / "raw"
RAW.mkdir(exist_ok=True)
SEASONS = [2025, 2026]  # 2025 = Valkyries' expansion year, 2026 = Tempo's

# file name -> the sportsdataverse function that downloads it
LOADERS = {
    "team_box": w.load_wnba_team_boxscore,      # one row per team per game
    "player_box": w.load_wnba_player_boxscore,  # one row per player per game
    "pbp": w.load_wnba_pbp,                     # every play (shots, fouls, subs...) with the clock and score
    "shots": w.load_wnba_shots,                 # shot locations
    "lineups": w.load_wnba_stats_lineups,       # five-player lineup totals from WNBA Stats
    "impact": w.load_wnba_player_impact,        # RAPM / BPM style impact numbers
}

# download each one and save it as a parquet file (much faster to load than csv)
for name, fn in LOADERS.items():
    df = fn(seasons=SEASONS, return_as_pandas=True)
    df.to_parquet(RAW / f"{name}.parquet")
    print(f"{name:12s} {df.shape}")

# history for the Expansion Class page (Elo back to 2003, roster experience)
HIST = list(range(2003, 2025))
w.load_wnba_team_boxscore(seasons=HIST, return_as_pandas=True).to_parquet(RAW / "team_box_hist.parquet")
# the old player box scores are big, so only keep the columns I actually use
cols = ["season", "season_type", "game_id", "athlete_id", "athlete_display_name", "team_abbreviation", "minutes"]
w.load_wnba_player_boxscore(seasons=HIST, return_as_pandas=True)[cols].to_parquet(RAW / "player_box_hist.parquet")
print("history     2003-2024")

# --- college data for the Draft Lab --------------------------------------------
import pandas as pd
import sportsdataverse.wbb as wbb

# rosters: 2026 = the 2025-26 college season, 2027 = the 2026-27 season (draft class of 2027)
wbb.load_wbb_rosters(seasons=[2026, 2027], return_as_pandas=True).to_parquet(RAW / "wbb_rosters.parquet")
# college box-score plus-minus for 2015-2026 (history + this year's prospects)
COLLEGE = list(range(2015, 2027))
wbb.load_wbb_player_value(seasons=COLLEGE, return_as_pandas=True).to_parquet(RAW / "wbb_player_value.parquet")
# college box scores are huge (150k+ rows a season), so add each player's season up right away
STATS = ["minutes", "points", "field_goals_made", "field_goals_attempted", "three_point_field_goals_made",
         "three_point_field_goals_attempted", "free_throws_made", "free_throws_attempted", "offensive_rebounds",
         "defensive_rebounds", "rebounds", "assists", "steals", "blocks", "turnovers", "fouls"]
seasons = []
for yr in COLLEGE:
    box = wbb.load_wbb_player_boxscore(seasons=[yr], return_as_pandas=True)
    for c in STATS:
        box[c] = pd.to_numeric(box[c], errors="coerce")
    box = box[box.minutes > 0]  # only games where she played
    tot = box.groupby(["season", "athlete_id"]).agg(
        name=("athlete_display_name", "last"), team=("team_display_name", "last"), team_id=("team_id", "last"),
        pos=("athlete_position_abbreviation", "last"), gp=("game_id", "nunique"), **{c: (c, "sum") for c in STATS})
    seasons.append(tot.reset_index())
    print("college box", yr, len(tot))
pd.concat(seasons).to_parquet(RAW / "wbb_player_seasons.parquet")
# sportsdataverse's own draft model (chance of being drafted + projected pick) from 2025-26 stats
wbb.wbb_draft_projection(seasons=[2026], league="womens", return_as_pandas=True).to_parquet(RAW / "wbb_draft_projection.parquet")
# every WNBA draft ESPN has (2018-2025), to see what college numbers turned into pro careers
pd.concat([w.espn_wnba_draft(yr, return_as_pandas=True) for yr in range(2018, 2026)],
          ignore_index=True).to_parquet(RAW / "wnba_draft.parquet")
print("college + draft data saved")
