"""Pull WNBA data from sportsdataverse and cache it as parquet in data/raw/.

Run once (or after new games): .venv/bin/python data/pull.py
"""
from pathlib import Path

import sportsdataverse.wnba as w

RAW = Path(__file__).parent / "raw"
RAW.mkdir(exist_ok=True)
SEASONS = [2025, 2026]  # 2025 = Valkyries' expansion year, 2026 = Tempo's

LOADERS = {
    "team_box": w.load_wnba_team_boxscore,
    "player_box": w.load_wnba_player_boxscore,
    "pbp": w.load_wnba_pbp,
    "shots": w.load_wnba_shots,
    "lineups": w.load_wnba_stats_lineups,
    "impact": w.load_wnba_player_impact,
}

for name, fn in LOADERS.items():
    df = fn(seasons=SEASONS, return_as_pandas=True)
    df.to_parquet(RAW / f"{name}.parquet")
    print(f"{name:12s} {df.shape}")

# history for the Expansion Class page (Elo back to 2003, roster experience)
HIST = list(range(2003, 2025))
w.load_wnba_team_boxscore(seasons=HIST, return_as_pandas=True).to_parquet(RAW / "team_box_hist.parquet")
cols = ["season", "season_type", "game_id", "athlete_id", "athlete_display_name", "team_abbreviation", "minutes"]
w.load_wnba_player_boxscore(seasons=HIST, return_as_pandas=True)[cols].to_parquet(RAW / "player_box_hist.parquet")
print("history     2003-2024")
