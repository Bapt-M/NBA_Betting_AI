import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import json
import os
import sys
from datetime import datetime

# --- IMPORTS BACKEND & UTILS ---
# On ajoute le dossier parent au path pour accéder au backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils import get_team_code
# Import de la DB
from backend.database import SessionLocal
from backend.models import DailyPrediction

def get_latest_stats(df, team_code, team_map):
    # ... (Garde cette fonction identique à la version précédente) ...
    if team_code not in team_map:
        return None
    team_id = team_map[team_code]
    mask_home = df['TEAM_ID_Home'] == team_id
    if not mask_home.any(): df_home = pd.DataFrame()
    else:
        df_home = df[mask_home].copy()
        cols = ['GAME_DATE'] + [c for c in df.columns if c.endswith('_Home')]
        df_home = df_home[cols]
        df_home.columns = [c.replace('_Home', '') for c in df_home.columns]

    mask_away = df['TEAM_ID_Away'] == team_id
    if not mask_away.any(): df_away = pd.DataFrame()
    else:
        df_away = df[mask_away].copy()
        cols = ['GAME_DATE'] + [c for c in df.columns if c.endswith('_Away') and c != 'GAME_DATE_Away']
        df_away = df_away[cols]
        df_away.columns = [c.replace('_Away', '') for c in df_away.columns]
    
    if df_home.empty and df_away.empty: return None
    df_team = pd.concat([df_home, df_away], ignore_index=True)
    df_team['GAME_DATE'] = pd.to_datetime(df_team['GAME_DATE'])
    df_team.sort_values('GAME_DATE', inplace=True)
    if df_team.empty: return None
    return df_team.iloc[-1]

def build_features_for_match(home_code, away_code, df_hist, team_map, feature_names):
    # ... (Garde cette fonction identique à la version précédente) ...
    h_stats = get_latest_stats(df_hist, home_code, team_map)
    a_stats = get_latest_stats(df_hist, away_code, team_map)
    if h_stats is None or a_stats is None: return None
    row = {}
    for col in h_stats.index:
        if col.startswith('L5_') or col.startswith('Szn_'): row[f"{col}_Home"] = h_stats[col]
    for col in a_stats.index:
        if col.startswith('L5_') or col.startswith('Szn_'): row[f"{col}_Away"] = a_stats[col]
    row['Rest_Days_Home'] = 2.0 
    row['Rest_Days_Away'] = 2.0
    try:
        p_pace = (h_stats.get('L5_POSS', 98) + a_stats.get('L5_POSS', 98) + h_stats.get('Szn_POSS', 98) + a_stats.get('Szn_POSS', 98)) / 4
        row['Meta_Predicted_Pace'] = p_pace
        row['Meta_Rest_Diff'] = row['Rest_Days_Home'] - row['Rest_Days_Away']
        poss_away = a_stats.get('L5_POSS', 98)
        if poss_away == 0: poss_away = 1
        def_pts_away = a_stats.get('L5_Defensive_PTS', 110)
        def_rating_away = 100 * def_pts_away / poss_away
        row['Meta_Off_vs_Def_Home'] = h_stats.get('L5_ORtg', 110) - def_rating_away
    except: return None
    df_input = pd.DataFrame([row])
    for col in feature_names:
        if col not in df_input.columns: df_input[col] = 0.0
    return df_input[feature_names]

def save_prediction_to_db(db, match_data):
    """Sauvegarde ou met à jour une prédiction en base de données."""
    # On vérifie si une prédiction existe déjà pour ce match/date/type
    existing = db.query(DailyPrediction).filter(
        DailyPrediction.match_date == match_data['match_date'],
        DailyPrediction.home_team == match_data['home_team'],
        DailyPrediction.away_team == match_data['away_team'],
        DailyPrediction.bet_type == match_data['bet_type']
    ).first()

    if existing:
        # Mise à jour
        existing.model_prediction = match_data['model_prediction']
        existing.fdj_line = match_data['fdj_line']
        existing.confidence_score = match_data['confidence_score']
        existing.recommendation = match_data['recommendation']
    else:
        # Création
        new_pred = DailyPrediction(**match_data)
        db.add(new_pred)
    
    db.commit()

def run_predictions():
    print("--- PRÉDICTIONS NBA & DATABASE SYNC ---")
    
    # Chemins (Absolus pour Docker de préférence, ou relatifs robustes)
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    MODEL_PATH = os.path.join(BASE_DIR, "models/xgb_nba_model.json")
    FEATURES_PATH = os.path.join(BASE_DIR, "models/feature_names.pkl")
    DATA_PATH = os.path.join(BASE_DIR, "data/processed/nba_data_train.csv")
    ODDS_PATH = os.path.join(BASE_DIR, "data/daily/cotes_fdj.json")
    
    if not os.path.exists(ODDS_PATH):
        print("❌ Pas de cotes. Lancez le scraper.")
        return

    # Chargement
    try:
        model = xgb.XGBRegressor()
        model.load_model(MODEL_PATH)
        feature_names = joblib.load(FEATURES_PATH)
        df_hist = pd.read_csv(DATA_PATH)
    except Exception as e:
        print(f"❌ Erreur chargement : {e}")
        return
    
    # Mapping
    if 'TEAM_ABBREVIATION_Home' in df_hist.columns:
        map_df = df_hist[['TEAM_ID_Home', 'TEAM_ABBREVIATION_Home']].drop_duplicates()
        team_map = dict(zip(map_df.TEAM_ABBREVIATION_Home, map_df.TEAM_ID_Home))
    else:
        print("❌ Colonne TEAM_ABBREVIATION_Home manquante.")
        return
    
    with open(ODDS_PATH, 'r', encoding='utf-8') as f:
        matches = json.load(f)
        
    # Connexion DB
    db = SessionLocal()
    predictions_count = 0
    
    try:
        for match in matches:
            home = match['home']
            away = match['away']
            odds = match['odds']
            
            X_input = build_features_for_match(home, away, df_hist, team_map, feature_names)
            if X_input is None: continue
                
            pred_total = float(model.predict(X_input)[0])
            
            for odd in odds:
                line = odd['line']
                otype = odd['type']
                
                diff = pred_total - line
                current_conf = 0
                recommendation = "No Bet"
                
                if otype == "OVER" and diff > 3:
                    current_conf = min(99, 50 + (diff * 4))
                    recommendation = "High Confidence" if current_conf > 80 else "Value Bet"
                elif otype == "UNDER" and diff < -3:
                    current_conf = min(99, 50 + (abs(diff) * 4))
                    recommendation = "High Confidence" if current_conf > 80 else "Value Bet"
                
                # On sauvegarde TOUTES les prédictions intéressantes (>50%) en base
                if current_conf > 50:
                    pred_data = {
                        "match_date": datetime.now().date(),
                        "home_team": home,
                        "away_team": away,
                        "model_prediction": round(pred_total, 2),
                        "fdj_line": line,
                        "bet_type": otype,
                        "confidence_score": round(current_conf, 2),
                        "recommendation": recommendation,
                        "is_processed": False
                    }
                    save_prediction_to_db(db, pred_data)
                    predictions_count += 1

        print(f"✅ {predictions_count} prédictions sauvegardées en base de données.")
        
    except Exception as e:
        print(f"❌ Erreur durant la prédiction : {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_predictions()