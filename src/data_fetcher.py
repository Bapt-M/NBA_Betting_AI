import pandas as pd
import time
from datetime import datetime
from nba_api.stats.endpoints import leaguegamelog
from tqdm import tqdm
import os

def get_seasons_list(num_years=10):
    """
    Génère dynamiquement les codes de saison (ex: '2024-25') 
    en se basant sur la date d'aujourd'hui.
    """
    now = datetime.now()
    # La saison NBA commence généralement en Octobre.
    # Si on est en Septembre (9) ou avant, la saison actuelle a commencé l'année d'avant.
    start_year = now.year if now.month >= 10 else now.year - 1
        
    seasons = []
    for i in range(num_years):
        y_start = start_year - i
        y_end = (y_start + 1) % 100
        season_str = f"{y_start}-{y_end:02d}"
        seasons.append(season_str)
    
    # Tri du plus ancien au plus récent pour l'entrainement
    return sorted(seasons)

def fetch_all_game_data(save_path="data/raw/nba_games_raw.csv"):
    seasons = get_seasons_list(10)
    all_games = []

    print(f"--- Récupération des saisons : {seasons[0]} à {seasons[-1]} ---")
    
    for season in tqdm(seasons, desc="Téléchargement API NBA"):
        try:
            # Récupère tous les matchs de la saison régulière
            log = leaguegamelog.LeagueGameLog(
                season=season, 
                season_type_all_star="Regular Season",
                player_or_team_abbreviation="T" # T pour Team stats
            )
            df_season = log.get_data_frames()[0]
            df_season['SEASON_ID'] = season
            all_games.append(df_season)
            time.sleep(1) # Pause pour éviter le ban IP
        except Exception as e:
            print(f" Erreur sur la saison {season}: {e}")

    if not all_games:
        print("Aucune donnée récupérée.")
        return

    final_df = pd.concat(all_games, ignore_index=True)
    
    # Conversion des colonnes numériques (l'API renvoie parfois du texte)
    cols_to_numeric = ['PTS', 'FGM', 'FGA', 'FG3M', 'FG3A', 'FTM', 'FTA', 'OREB', 'DREB', 'AST', 'STL', 'BLK', 'TOV', 'PF']
    for col in cols_to_numeric:
        if col in final_df.columns:
            final_df[col] = pd.to_numeric(final_df[col])
            
    # Conversion date
    final_df['GAME_DATE'] = pd.to_datetime(final_df['GAME_DATE'])

    # Sauvegarde
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    final_df.to_csv(save_path, index=False)
    print(f"Succès : {len(final_df)} matchs sauvegardés dans {save_path}")

if __name__ == "__main__":
    fetch_all_game_data()