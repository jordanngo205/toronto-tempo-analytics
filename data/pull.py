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
