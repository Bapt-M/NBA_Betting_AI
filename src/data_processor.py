import pandas as pd
import numpy as np
import os
import sys

# Ajout du chemin pour importer backend.config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.config import settings

def calculate_advanced_stats(df):
    """Calcule les métriques avancées pour chaque match."""
    # Formule officielle des Possessions (approx)
    df['POSS'] = 0.96 * (df['FGA'] + df['TOV'] + 0.44 * df['FTA'] - df['OREB'])
    df['POSS'] = df['POSS'].replace(0, 1) # Sécurité division par 0
    
    # Offensive Rating : Points pour 100 possessions
    df['ORtg'] = 100 * (df['PTS'] / df['POSS'])
    
    # Pourcentages et efficacité
    df['FG3A'] = df['FG3A'].replace(0, 1)
    df['3P%'] = df['FG3M'] / df['FG3A']
    df['TOV%'] = df['TOV'] / df['POSS']
    df['FTR'] = df['FTA'] / df['FGA'].replace(0, 1) # Free Throw Rate
    
    return df

def get_rest_days(df):
    """Calcule les jours de repos depuis le dernier match."""
    df = df.sort_values('GAME_DATE')
    df['Rest_Days'] = df.groupby('TEAM_ID')['GAME_DATE'].diff().dt.days
    df['Rest_Days'] = df['Rest_Days'].fillna(3)
    df['Rest_Days'] = df['Rest_Days'].clip(upper=7)
    return df

def get_rolling_and_season_stats(df, window=5):
    """Crée les variables historiques (L5_ et Szn_)."""
    features = ['ORtg', 'POSS', '3P%', 'TOV%', 'PTS', 'Defensive_PTS', 'FTR']
    
    df_sorted = df.sort_values('GAME_DATE')
    grouped = df_sorted.groupby(['TEAM_ID', 'SEASON_ID'])[features]
    
    # 1. Rolling Mean (L5)
    rolling = grouped.apply(lambda x: x.shift(1).rolling(window=window, min_periods=1).mean())
    rolling = rolling.reset_index(level=[0,1], drop=True)
    rolling.columns = [f'L5_{col}' for col in rolling.columns]
    
    # 2. Expanding Mean (Saison)
    season_avg = grouped.apply(lambda x: x.shift(1).expanding().mean())
    season_avg = season_avg.reset_index(level=[0,1], drop=True)
    season_avg.columns = [f'Szn_{col}' for col in season_avg.columns]
    
    return pd.concat([df_sorted, rolling, season_avg], axis=1)

def process_data():
    input_path = settings.DATA_RAW
    output_path = settings.DATA_PROCESSED
    print("--- Traitement des Données (Feature Engineering) ---")
    
    if not os.path.exists(input_path):
        print(f"Erreur: Fichier raw introuvable: {input_path}")
        return

    df = pd.read_csv(input_path)
    
    # Nettoyage initial
    df.drop_duplicates(subset=['GAME_ID', 'TEAM_ID'], inplace=True)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df[df['PTS'] < 165] # Filtre All-Star
    
    # 1. IDENTIFICATION ROBUSTE HOME / AWAY
    # On cherche ' vs ' (Home) ou absence de '@' (Away)
    df['Is_Home'] = df['MATCHUP'].str.contains(' vs', case=False, regex=False)
    
    print(f"Stats brutes: {len(df)} lignes. Home detectés: {df['Is_Home'].sum()}")

    # 2. CALCUL POINTS DÉFENSIFS
    # CORRECTION CRASH: On s'assure que les index sont uniques pour le mapping.
    # .drop_duplicates(subset=['GAME_ID']) garde la première occurrence si data corrompue
    df_home_only = df[df['Is_Home']].drop_duplicates(subset=['GAME_ID']).set_index('GAME_ID')
    df_away_only = df[~df['Is_Home']].drop_duplicates(subset=['GAME_ID']).set_index('GAME_ID')
    
    # Map sécurisée des points adverses
    df['Defensive_PTS'] = np.where(
        df['Is_Home'],
        df['GAME_ID'].map(df_away_only['PTS']), # Si Home, Def = Away PTS
        df['GAME_ID'].map(df_home_only['PTS'])  # Si Away, Def = Home PTS
    )
    
    # Suppression des matchs orphelins (où il manque une des deux équipes)
    df.dropna(subset=['Defensive_PTS'], inplace=True)

    # 3. CALCULS FEATURES
    df = calculate_advanced_stats(df)
    df = get_rest_days(df)
    df = get_rolling_and_season_stats(df, window=5)
    
    # 4. FUSION MATCH (CORRECTION DOUBLONS)
    cols_meta = ['GAME_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'GAME_DATE', 'Rest_Days']
    cols_features = [c for c in df.columns if 'L5_' in c or 'Szn_' in c]
    
    # SÉPARATION STRICTE : On utilise le masque booléen 'Is_Home' directement
    # Et on s'assure encore de l'unicité par match pour éviter l'explosion du merge
    df_h = df[df['Is_Home']].drop_duplicates(subset=['GAME_ID'])[cols_meta + cols_features].copy().add_suffix('_Home')
    df_a = df[~df['Is_Home']].drop_duplicates(subset=['GAME_ID'])[cols_meta + cols_features].copy().add_suffix('_Away')
    
    # Fusion sur l'ID de match unique
    final = pd.merge(df_h, df_a, left_on='GAME_ID_Home', right_on='GAME_ID_Away')
    
    # 5. TARGET & META FEATURES
    # On récupère les scores finaux via les IDs
    final['TARGET_Total_Pts'] = final['GAME_ID_Home'].map(df_home_only['PTS']) + final['GAME_ID_Home'].map(df_away_only['PTS'])
    
    # Feature : Pace Prédit
    final['Meta_Predicted_Pace'] = (
        final['L5_POSS_Home'] + final['L5_POSS_Away'] +
        final['Szn_POSS_Home'] + final['Szn_POSS_Away']
    ) / 4
    
    # Feature : Fatigue Diff
    final['Meta_Rest_Diff'] = final['Rest_Days_Home'] - final['Rest_Days_Away']
    
    # Feature : Matchup Scoring
    final['Meta_Off_vs_Def_Home'] = final['L5_ORtg_Home'] - (100 * final['L5_Defensive_PTS_Away'] / final['L5_POSS_Away'])
    
    # Nettoyage final (NaNs du début de saison dus au rolling window)
    final.dropna(inplace=True)
    final.rename(columns={'GAME_DATE_Home': 'GAME_DATE'}, inplace=True)
    
    # Sauvegarde
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.to_csv(output_path, index=False)
    print(f"✅ Dataset propre généré : {len(final)} matchs traités dans {output_path}")

if __name__ == "__main__":
    process_data()