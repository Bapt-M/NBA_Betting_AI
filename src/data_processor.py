import pandas as pd
import numpy as np
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.config import settings

def calculate_advanced_stats(df):
    df['POSS'] = 0.96 * (df['FGA'] + df['TOV'] + 0.44 * df['FTA'] - df['OREB'])
    df['POSS'] = df['POSS'].replace(0, 1)
    df['ORtg'] = 100 * (df['PTS'] / df['POSS'])
    df['FG3A'] = df['FG3A'].replace(0, 1)
    df['3P%'] = df['FG3M'] / df['FG3A']
    df['TOV%'] = df['TOV'] / df['POSS']
    df['FTR'] = df['FTA'] / df['FGA'].replace(0, 1)
    return df

def get_rest_days(df):
    df = df.sort_values('GAME_DATE')
    df['Rest_Days'] = df.groupby('TEAM_ID')['GAME_DATE'].diff().dt.days
    df['Rest_Days'] = df['Rest_Days'].fillna(3)
    df['Rest_Days'] = df['Rest_Days'].clip(upper=7)
    return df

# --- MODIFICATION ICI : AJOUT DE LA VOLATILITÉ ---
def get_rolling_and_season_stats(df, window=5):
    features = ['ORtg', 'POSS', '3P%', 'TOV%', 'PTS', 'Defensive_PTS', 'FTR']
    
    df_sorted = df.sort_values('GAME_DATE')
    grouped = df_sorted.groupby(['TEAM_ID', 'SEASON_ID'])[features]
    
    # 1. Rolling Mean (Moyenne L5)
    rolling = grouped.apply(lambda x: x.shift(1).rolling(window=window, min_periods=1).mean())
    rolling = rolling.reset_index(level=[0,1], drop=True)
    rolling.columns = [f'L5_{col}' for col in rolling.columns]

    # 2. Rolling STD (Volatilité L5) - NOUVEAU
    # Cela capture l'instabilité (écart-type des 5 derniers matchs)
    rolling_std = grouped.apply(lambda x: x.shift(1).rolling(window=window, min_periods=1).std())
    rolling_std = rolling_std.reset_index(level=[0,1], drop=True)
    rolling_std.columns = [f'L5_Volat_{col}' for col in rolling_std.columns]
    
    # 3. Expanding Mean (Saison)
    season_avg = grouped.apply(lambda x: x.shift(1).expanding().mean())
    season_avg = season_avg.reset_index(level=[0,1], drop=True)
    season_avg.columns = [f'Szn_{col}' for col in season_avg.columns]
    
    return pd.concat([df_sorted, rolling, rolling_std, season_avg], axis=1)
# -------------------------------------------------

def process_data():
    input_path = settings.DATA_RAW
    output_path = settings.DATA_PROCESSED
    print("--- Traitement des Données (Feature Engineering + Volatilité) ---")
    
    if not os.path.exists(input_path):
        print(f"Erreur: Fichier raw introuvable: {input_path}")
        return

    df = pd.read_csv(input_path)
    df.drop_duplicates(subset=['GAME_ID', 'TEAM_ID'], inplace=True)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df[df['PTS'] < 165]
    
    df['Is_Home'] = df['MATCHUP'].str.contains(' vs', case=False, regex=False)
    
    df_home_only = df[df['Is_Home']].drop_duplicates(subset=['GAME_ID']).set_index('GAME_ID')
    df_away_only = df[~df['Is_Home']].drop_duplicates(subset=['GAME_ID']).set_index('GAME_ID')
    
    df['Defensive_PTS'] = np.where(
        df['Is_Home'],
        df['GAME_ID'].map(df_away_only['PTS']),
        df['GAME_ID'].map(df_home_only['PTS'])
    )
    df.dropna(subset=['Defensive_PTS'], inplace=True)

    df = calculate_advanced_stats(df)
    df = get_rest_days(df)
    df = get_rolling_and_season_stats(df, window=5)
    
    cols_meta = ['GAME_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'GAME_DATE', 'Rest_Days']
    # On inclut maintenant les colonnes Volat_
    cols_features = [c for c in df.columns if 'L5_' in c or 'Szn_' in c]
    
    df_h = df[df['Is_Home']].drop_duplicates(subset=['GAME_ID'])[cols_meta + cols_features].copy().add_suffix('_Home')
    df_a = df[~df['Is_Home']].drop_duplicates(subset=['GAME_ID'])[cols_meta + cols_features].copy().add_suffix('_Away')
    
    final = pd.merge(df_h, df_a, left_on='GAME_ID_Home', right_on='GAME_ID_Away')
    
    final['TARGET_Total_Pts'] = final['GAME_ID_Home'].map(df_home_only['PTS']) + final['GAME_ID_Home'].map(df_away_only['PTS'])
    
    final['Meta_Predicted_Pace'] = (
        final['L5_POSS_Home'] + final['L5_POSS_Away'] +
        final['Szn_POSS_Home'] + final['Szn_POSS_Away']
    ) / 4
    
    final['Meta_Rest_Diff'] = final['Rest_Days_Home'] - final['Rest_Days_Away']
    final['Meta_Off_vs_Def_Home'] = final['L5_ORtg_Home'] - (100 * final['L5_Defensive_PTS_Away'] / final['L5_POSS_Away'])
    
    # Feature Risque : Somme des volatilités
    final['Meta_Risk_Factor'] = final['L5_Volat_PTS_Home'] + final['L5_Volat_PTS_Away']

    final.dropna(inplace=True)
    final.rename(columns={'GAME_DATE_Home': 'GAME_DATE'}, inplace=True)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.to_csv(output_path, index=False)
    print(f"✅ Dataset propre généré (avec Volatilité) : {len(final)} matchs traités.")

if __name__ == "__main__":
    process_data()