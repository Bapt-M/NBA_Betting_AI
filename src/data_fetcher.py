import pandas as pd
import time
from datetime import datetime
from nba_api.stats.endpoints import leaguegamelog
from tqdm import tqdm
import os
import sys

# Ajout path pour import backend config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from backend.config import settings
except ImportError:
    # Fallback si lancé manuellement hors structure
    class MockSettings:
        DATA_RAW = "data/raw/nba_games_raw.csv"
    settings = MockSettings()

def get_seasons_list(num_years=10):
    now = datetime.now()
    start_year = now.year if now.month >= 10 else now.year - 1
    return sorted([f"{start_year - i}-{(start_year - i + 1) % 100:02d}" for i in range(num_years)])

def fetch_all_game_data():
    """Fonction principale appelée par Celery"""
    print(f"--- Fetching Data to {settings.DATA_RAW} ---")
    seasons = get_seasons_list(10)
    all_games = []

    for season in seasons: # Enlever tqdm pour les logs Docker propres
        try:
            log = leaguegamelog.LeagueGameLog(season=season, season_type_all_star="Regular Season", player_or_team_abbreviation="T")
            df = log.get_data_frames()[0]
            df['SEASON_ID'] = season
            all_games.append(df)
            time.sleep(0.6)
        except Exception as e:
            print(f"Error {season}: {e}")

    if not all_games: return "No data found"

    final_df = pd.concat(all_games, ignore_index=True)
    # ... (Conversion numérique idem avant) ...
    cols_num = ['PTS', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'DREB', 'AST', 'STL', 'BLK', 'TOV', 'PF']
    for c in cols_num:
        if c in final_df.columns: final_df[c] = pd.to_numeric(final_df[c])
    
    final_df['GAME_DATE'] = pd.to_datetime(final_df['GAME_DATE'])
    
    os.makedirs(os.path.dirname(settings.DATA_RAW), exist_ok=True)
    final_df.to_csv(settings.DATA_RAW, index=False)
    return f"Success: {len(final_df)} rows saved."

if __name__ == "__main__":
    fetch_all_game_data()