import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import json
import os
import sys
from datetime import datetime

# Ajout du path pour importer utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def get_latest_stats(df, team_code, team_map):
    """
    Récupère la dernière ligne de stats connue pour une équipe donnée.
    Version corrigée pour éviter l'erreur InvalidIndexError.
    """
    if team_code not in team_map:
        return None
        
    team_id = team_map[team_code]
    
    # --- 1. Perspective DOMICILE ---
    mask_home = df['TEAM_ID_Home'] == team_id
    if not mask_home.any():
        df_home = pd.DataFrame()
    else:
        df_home = df[mask_home].copy()
        cols_to_keep = ['GAME_DATE'] + [c for c in df.columns if c.endswith('_Home')]
        df_home = df_home[cols_to_keep]
        df_home.columns = [c.replace('_Home', '') for c in df_home.columns]

    # --- 2. Perspective EXTÉRIEUR ---
    mask_away = df['TEAM_ID_Away'] == team_id
    if not mask_away.any():
        df_away = pd.DataFrame()
    else:
        df_away = df[mask_away].copy()
        cols_to_keep = ['GAME_DATE'] + [c for c in df.columns if c.endswith('_Away') and c != 'GAME_DATE_Away']
        df_away = df_away[cols_to_keep]
        df_away.columns = [c.replace('_Away', '') for c in df_away.columns]
    
    # --- 3. Fusion et Tri ---
    if df_home.empty and df_away.empty:
        return None
        
    df_team = pd.concat([df_home, df_away], ignore_index=True)
    df_team['GAME_DATE'] = pd.to_datetime(df_team['GAME_DATE'])
    df_team.sort_values('GAME_DATE', inplace=True)
    
    if df_team.empty:
        return None
        
    return df_team.iloc[-1]

def build_features_for_match(home_code, away_code, df_hist, team_map, feature_names):
    """Construit le vecteur d'entrée pour le modèle XGBoost."""
    
    h_stats = get_latest_stats(df_hist, home_code, team_map)
    a_stats = get_latest_stats(df_hist, away_code, team_map)
    
    if h_stats is None or a_stats is None:
        return None

    row = {}
    
    # Remplissage des stats historiques
    for col in h_stats.index:
        if col.startswith('L5_') or col.startswith('Szn_'):
            row[f"{col}_Home"] = h_stats[col]
            
    for col in a_stats.index:
        if col.startswith('L5_') or col.startswith('Szn_'):
            row[f"{col}_Away"] = a_stats[col]

    # Fatigue par défaut
    row['Rest_Days_Home'] = 2.0 
    row['Rest_Days_Away'] = 2.0
    
    # Meta-Features
    try:
        p_pace = (h_stats.get('L5_POSS', 98) + a_stats.get('L5_POSS', 98) + 
                  h_stats.get('Szn_POSS', 98) + a_stats.get('Szn_POSS', 98)) / 4
        row['Meta_Predicted_Pace'] = p_pace
        row['Meta_Rest_Diff'] = row['Rest_Days_Home'] - row['Rest_Days_Away']
        
        poss_away = a_stats.get('L5_POSS', 98)
        if poss_away == 0: poss_away = 1
        def_pts_away = a_stats.get('L5_Defensive_PTS', 110)
        def_rating_away = 100 * def_pts_away / poss_away
        
        row['Meta_Off_vs_Def_Home'] = h_stats.get('L5_ORtg', 110) - def_rating_away
    except Exception:
        return None

    df_input = pd.DataFrame([row])
    
    for col in feature_names:
        if col not in df_input.columns:
            df_input[col] = 0.0
            
    return df_input[feature_names]

def run_predictions():
    print("--- PRÉDICTIONS NBA DU JOUR & EXPORT CSV ---")
    
    # Chemins
    MODEL_PATH = "models/xgb_nba_model.json"
    FEATURES_PATH = "models/feature_names.pkl"
    DATA_PATH = "data/processed/nba_data_train.csv"
    ODDS_PATH = "data/daily/cotes_fdj.json"
    
    OUTPUT_ALL_CSV = "data/daily/all_odds_predictions.csv"
    OUTPUT_BEST_CSV = "data/daily/best_bets.csv"
    
    if not os.path.exists(ODDS_PATH):
        print("[ERREUR] Pas de cotes. Lancez 'python daily/scraper_fdj.py'.")
        return

    # Chargement
    try:
        model = xgb.XGBRegressor()
        model.load_model(MODEL_PATH)
        feature_names = joblib.load(FEATURES_PATH)
        df_hist = pd.read_csv(DATA_PATH)
    except Exception as e:
        print(f"[ERREUR] Erreur chargement : {e}")
        return
    
    # Mapping Team ID
    if 'TEAM_ABBREVIATION_Home' in df_hist.columns:
        map_df = df_hist[['TEAM_ID_Home', 'TEAM_ABBREVIATION_Home']].drop_duplicates()
        team_map = dict(zip(map_df.TEAM_ABBREVIATION_Home, map_df.TEAM_ID_Home))
    else:
        print("[ERREUR] Colonne TEAM_ABBREVIATION_Home manquante.")
        return
    
    with open(ODDS_PATH, 'r', encoding='utf-8') as f:
        matches = json.load(f)
        
    all_results = []
    
    print(f"Analyse de {len(matches)} matchs...")
    
    for match in matches:
        home = match['home']
        away = match['away']
        odds = match['odds']
        match_label = f"{home} vs {away}"
        
        # Prédiction
        X_input = build_features_for_match(home, away, df_hist, team_map, feature_names)
        if X_input is None: continue
            
        pred_total = float(model.predict(X_input)[0])
        
        for odd in odds:
            line = odd['line']
            otype = odd['type']
            quote = odd['odd']
            
            diff = pred_total - line
            
            # Calcul Confiance
            current_conf = 0
            if otype == "OVER":
                # Si pred=230, line=220, diff=+10 -> Bon pour Over
                if diff > 0:
                    current_conf = min(99, 50 + (diff * 4))
                else:
                    current_conf = 0 # Pas un Over
            elif otype == "UNDER":
                # Si pred=210, line=220, diff=-10 -> Bon pour Under
                if diff < 0:
                    current_conf = min(99, 50 + (abs(diff) * 4))
                else:
                    current_conf = 0

            # On stocke tout
            all_results.append({
                "Date": datetime.now().strftime('%Y-%m-%d'),
                "Match": match_label,
                "Home": home,
                "Away": away,
                "Prediction_Modele": round(pred_total, 2),
                "Ligne_Bookmaker": line,
                "Type_Pari": otype,
                "Cote": quote,
                "Ecart": round(diff, 2),
                "Confiance_Score": round(current_conf, 1)
            })

    # --- GÉNÉRATION DES CSV ---
    
    if not all_results:
        print("Aucune donnée générée.")
        return

    df_all = pd.DataFrame(all_results)
    
    # 1. Sauvegarde de TOUTES les cotes
    df_all.to_csv(OUTPUT_ALL_CSV, index=False)
    print(f"Fichier complet généré : {OUTPUT_ALL_CSV} ({len(df_all)} lignes)")
    
    # 2. Sauvegarde des BEST BETS (Top 2 par match)
    # Filtre : Marge de sécurité > 3 points
    df_best = df_all[df_all['Ecart'].abs() > 3].copy()
    
    # Tri par Match et par Confiance (Descendant)
    df_best = df_best.sort_values(by=['Match', 'Confiance_Score'], ascending=[True, False])
    
    # On garde les 2 meilleurs par match
    df_best = df_best.groupby('Match').head(1)
    
    if not df_best.empty:
        df_best.to_csv(OUTPUT_BEST_CSV, index=False)
        print(f"Fichier Best Bets généré : {OUTPUT_BEST_CSV} ({len(df_best)} paris)")
        
        # Affichage console pour plaisir immédiat
        print("\nTOP PARIS DU JOUR :")
        print(f"{'MATCH':<15} | {'PARI':<12} | {'COTE':<5} | {'CONF':<6}")
        print("-" * 45)
        for _, row in df_best.iterrows():
            pari = f"{row['Type_Pari']} {row['Ligne_Bookmaker']}"
            print(f"{row['Match']:<15} | {pari:<12} | {row['Cote']:<5} | {row['Confiance_Score']}")
    else:
        print("Aucun pari 'Best Bet' ne respecte la marge de sécurité (> 3 pts) aujourd'hui.")

if __name__ == "__main__":
    run_predictions()