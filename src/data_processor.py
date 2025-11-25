import pandas as pd
import numpy as np
import os
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

def get_rolling_and_season_stats(df, window=5):
    features = ['ORtg', 'POSS', '3P%', 'TOV%', 'PTS', 'Defensive_PTS', 'FTR']
    df_sorted = df.sort_values('GAME_DATE')
    grouped = df_sorted.groupby(['TEAM_ID', 'SEASON_ID'])[features]
    
    rolling = grouped.apply(lambda x: x.shift(1).rolling(window=window, min_periods=1).mean())
    rolling = rolling.reset_index(level=[0,1], drop=True)
    rolling.columns = [f'L5_{col}' for col in rolling.columns]
    
    season_avg = grouped.apply(lambda x: x.shift(1).expanding().mean())
    season_avg = season_avg.reset_index(level=[0,1], drop=True)
    season_avg.columns = [f'Szn_{col}' for col in season_avg.columns]
    
    return pd.concat([df_sorted, rolling, season_avg], axis=1)

def process_data(input_path=None, output_path=None):
    input_path = input_path or settings.DATA_RAW
    output_path = output_path or settings.DATA_PROCESSED
    
    print("--- Traitement des Données (Correction Stricte) ---")
    
    if not os.path.exists(input_path):
        print("Erreur: Fichier raw introuvable.")
        return

    df = pd.read_csv(input_path)
    
    # NETTOYAGE ID STRICT
    df['GAME_ID'] = df['GAME_ID'].astype(str).str.strip()
    df['TEAM_ID'] = df['TEAM_ID'].astype(str).str.strip()
    
    # DEDUPLICATION INITIALE
    df.drop_duplicates(subset=['GAME_ID', 'TEAM_ID'], inplace=True)
    
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df[df['PTS'] < 165]
    
    df['Is_Home'] = df['MATCHUP'].str.contains(' vs. ')
    
    # MAPPING POINTS
    # On force 1 seule ligne par GAME_ID pour Home et Away
    df_home = df[df['Is_Home']].drop_duplicates(subset=['GAME_ID']).set_index('GAME_ID')
    df_away = df[~df['Is_Home']].drop_duplicates(subset=['GAME_ID']).set_index('GAME_ID')
    
    df['Defensive_PTS'] = np.where(
        df['Is_Home'],
        df['GAME_ID'].map(df_away['PTS']),
        df['GAME_ID'].map(df_home['PTS'])
    )
    df.dropna(subset=['Defensive_PTS'], inplace=True)

    # FEATURES
    df = calculate_advanced_stats(df)
    df = get_rest_days(df)
    df = get_rolling_and_season_stats(df, window=5)
    
    # FUSION FINALE
    cols_meta = ['GAME_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'GAME_DATE', 'Rest_Days']
    cols_features = [c for c in df.columns if 'L5_' in c or 'Szn_' in c]
    
    df_base = df[cols_meta + cols_features].copy()
    
    # SÉPARATION & FUSION STRICTE
    # On ne prend que les IDs présents dans les deux sets (intersection)
    common_ids = set(df_home.index).intersection(set(df_away.index))
    
    df_h = df_base[df_base['GAME_ID'].isin(common_ids) & (df_base['GAME_ID'].isin(df_home.index))].drop_duplicates(subset=['GAME_ID']).add_suffix('_Home')
    df_a = df_base[df_base['GAME_ID'].isin(common_ids) & (df_base['GAME_ID'].isin(df_away.index))].drop_duplicates(subset=['GAME_ID']).add_suffix('_Away')
    
    final = pd.merge(df_h, df_a, left_on='GAME_ID_Home', right_on='GAME_ID_Away')
    
    # FILTRE ANTI-DOUBLONS (Sécurité finale)
    # Si Home == Away, c'est une erreur de données, on vire.
    final = final[final['TEAM_ID_Home'] != final['TEAM_ID_Away']]
    
    # TARGETS
    final['TARGET_Total_Pts'] = final['GAME_ID_Home'].map(df_home['PTS']) + final['GAME_ID_Home'].map(df_away['PTS'])
    final['Meta_Predicted_Pace'] = (final['L5_POSS_Home'] + final['L5_POSS_Away'] + final['Szn_POSS_Home'] + final['Szn_POSS_Away']) / 4
    final['Meta_Rest_Diff'] = final['Rest_Days_Home'] - final['Rest_Days_Away']
    
    poss_away = final['L5_POSS_Away'].replace(0, 1)
    final['Meta_Off_vs_Def_Home'] = final['L5_ORtg_Home'] - (100 * final['L5_Defensive_PTS_Away'] / poss_away)
    
    final.dropna(inplace=True)
    final.rename(columns={'GAME_DATE_Home': 'GAME_DATE'}, inplace=True)
    final.sort_values('GAME_DATE', inplace=True)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.to_csv(output_path, index=False)
    print(f"✅ Dataset propre généré : {len(final)} matchs.")

if __name__ == "__main__":
    process_data()