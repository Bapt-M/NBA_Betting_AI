import pandas as pd
import numpy as np
import os

def calculate_advanced_stats(df):
    """Calcule les métriques avancées pour chaque match."""
    # Formule officielle des Possessions (approx): 0.96 * (FGA + TOV + 0.44 * FTA - OREB)
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
    # Différence en jours entre les matchs d'une même équipe
    df['Rest_Days'] = df.groupby('TEAM_ID')['GAME_DATE'].diff().dt.days
    # Remplir les NaN (début de saison) par 3 jours (reposé)
    df['Rest_Days'] = df['Rest_Days'].fillna(3)
    # Caper à 7 jours (inutile de savoir si c'est 10 ou 20 jours)
    df['Rest_Days'] = df['Rest_Days'].clip(upper=7)
    return df

def get_rolling_and_season_stats(df, window=5):
    """
    Crée les variables historiques :
    - L5_ : Moyenne sur les 5 derniers matchs (Forme récente)
    - Szn_ : Moyenne depuis le début de la saison (Niveau global)
    """
    features = ['ORtg', 'POSS', '3P%', 'TOV%', 'PTS', 'Defensive_PTS', 'FTR']
    
    df_sorted = df.sort_values('GAME_DATE')
    
    # Groupement par équipe et saison
    grouped = df_sorted.groupby(['TEAM_ID', 'SEASON_ID'])[features]
    
    # 1. Rolling Mean (L5) - shift(1) pour ne pas inclure le match actuel !
    rolling = grouped.apply(lambda x: x.shift(1).rolling(window=window, min_periods=1).mean())
    rolling = rolling.reset_index(level=[0,1], drop=True)
    rolling.columns = [f'L5_{col}' for col in rolling.columns]
    
    # 2. Expanding Mean (Saison)
    season_avg = grouped.apply(lambda x: x.shift(1).expanding().mean())
    season_avg = season_avg.reset_index(level=[0,1], drop=True)
    season_avg.columns = [f'Szn_{col}' for col in season_avg.columns]
    
    return pd.concat([df_sorted, rolling, season_avg], axis=1)

def process_data(input_path="data/raw/nba_games_raw.csv", output_path="data/processed/nba_data_train.csv"):
    print("--- Traitement des Données (Feature Engineering) ---")
    
    if not os.path.exists(input_path):
        print("Erreur: Fichier raw introuvable.")
        return

    df = pd.read_csv(input_path)
    # Suppression doublons API
    df.drop_duplicates(subset=['GAME_ID', 'TEAM_ID'], inplace=True)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    
    # 1. Filtre anti-AllStar (Matchs > 165 pts par équipe = non représentatif)
    df = df[df['PTS'] < 165]
    
    # 2. Identification Home/Away
    df['Is_Home'] = df['MATCHUP'].str.contains(' vs. ')
    
    # 3. Mapping Points Défensifs
    # Pour calculer la défense, il faut savoir combien l'équipe a encaissé
    df_home = df[df['Is_Home']].drop_duplicates(subset=['GAME_ID'])
    df_away = df[~df['Is_Home']].drop_duplicates(subset=['GAME_ID'])
    
    home_pts_map = df_home.set_index('GAME_ID')['PTS']
    away_pts_map = df_away.set_index('GAME_ID')['PTS']
    
    df['Defensive_PTS'] = np.where(
        df['Is_Home'],
        df['GAME_ID'].map(away_pts_map),
        df['GAME_ID'].map(home_pts_map)
    )
    df.dropna(subset=['Defensive_PTS'], inplace=True)

    # 4. Calculs de base
    df = calculate_advanced_stats(df)
    df = get_rest_days(df)
    
    # 5. Calculs Historiques (L5, Saison)
    df = get_rolling_and_season_stats(df, window=5)
    
    # 6. Fusion Match (Ligne unique : Home vs Away)
    # CORRECTION ICI : Ajout de 'TEAM_ABBREVIATION' dans cols_meta
    cols_meta = ['GAME_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'GAME_DATE', 'Rest_Days']
    
    # On garde toutes les colonnes calculées (L5_..., Szn_...)
    cols_features = [c for c in df.columns if 'L5_' in c or 'Szn_' in c]
    
    df_base = df[cols_meta + cols_features].copy()
    
    df_h = df_base[df_base['GAME_ID'].isin(df_home['GAME_ID'])].add_suffix('_Home')
    df_a = df_base[df_base['GAME_ID'].isin(df_away['GAME_ID'])].add_suffix('_Away')
    
    final = pd.merge(df_h, df_a, left_on='GAME_ID_Home', right_on='GAME_ID_Away')
    
    # 7. Création de la Target et Features Meta
    final['TARGET_Total_Pts'] = final['GAME_ID_Home'].map(home_pts_map) + final['GAME_ID_Home'].map(away_pts_map)
    
    # Feature : Pace Prédit (Moyenne des 4 indicateurs de vitesse)
    final['Meta_Predicted_Pace'] = (
        final['L5_POSS_Home'] + final['L5_POSS_Away'] +
        final['Szn_POSS_Home'] + final['Szn_POSS_Away']
    ) / 4
    
    # Feature : Fatigue Diff (Positif = Home plus reposé)
    final['Meta_Rest_Diff'] = final['Rest_Days_Home'] - final['Rest_Days_Away']
    
    # Feature : Matchup Scoring (Forme Offensiv Home vs Forme Def Away)
    final['Meta_Off_vs_Def_Home'] = final['L5_ORtg_Home'] - (100 * final['L5_Defensive_PTS_Away'] / final['L5_POSS_Away'])
    
    # Nettoyage final
    final.dropna(inplace=True)
    final.rename(columns={'GAME_DATE_Home': 'GAME_DATE'}, inplace=True)
    
    # Sauvegarde
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.to_csv(output_path, index=False)
    print(f"Dataset prêt : {len(final)} matchs traités dans {output_path}")

if __name__ == "__main__":
    process_data()