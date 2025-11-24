import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils import get_team_code
from backend.database import SessionLocal
from backend.models import DailyPrediction

def get_latest_stats(df, team_code, team_map):
    # (Garder la fonction existante, inchangée car elle marche bien)
    if team_code not in team_map: return None
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
    # (Garder la fonction existante)
    h_stats = get_latest_stats(df_hist, home_code, team_map)
    a_stats = get_latest_stats(df_hist, away_code, team_map)
    if h_stats is None or a_stats is None: return None
    row = {}
    for col in h_stats.index:
        if col.startswith('L5_') or col.startswith('Szn_'): row[f"{col}_Home"] = h_stats[col]
    for col in a_stats.index:
        if col.startswith('L5_') or col.startswith('Szn_'): row[f"{col}_Away"] = a_stats[col]
    row['Rest_Days_Home'] = 2.0; row['Rest_Days_Away'] = 2.0
    try:
        p_pace = (h_stats.get('L5_POSS', 98) + a_stats.get('L5_POSS', 98) + h_stats.get('Szn_POSS', 98) + a_stats.get('Szn_POSS', 98)) / 4
        row['Meta_Predicted_Pace'] = p_pace
        row['Meta_Rest_Diff'] = 0.0
        poss_away = a_stats.get('L5_POSS', 98); poss_away = 1 if poss_away == 0 else poss_away
        def_pts_away = a_stats.get('L5_Defensive_PTS', 110)
        def_rating_away = 100 * def_pts_away / poss_away
        row['Meta_Off_vs_Def_Home'] = h_stats.get('L5_ORtg', 110) - def_rating_away
    except: return None
    df_input = pd.DataFrame([row])
    for col in feature_names:
        if col not in df_input.columns: df_input[col] = 0.0
    return df_input[feature_names]

def save_prediction_to_db(db, match_data):
    # Mapping pour la DB (Model SQLAlchemy) qui a des noms anglais
    # Le frontend utilisera les clés françaises du JSON
    existing = db.query(DailyPrediction).filter(
        DailyPrediction.match_date == match_data['Date'],
        DailyPrediction.home_team == match_data['Home'],
        DailyPrediction.away_team == match_data['Away'],
        DailyPrediction.bet_type == match_data['Type_Pari']
    ).first()

    # Transformation des clés pour le modèle DB
    db_obj = {
        "match_date": match_data['Date'],
        "home_team": match_data['Home'],
        "away_team": match_data['Away'],
        "model_prediction": match_data['Prediction_Modele'],
        "fdj_line": match_data['Ligne_Bookmaker'],
        "bet_type": match_data['Type_Pari'],
        "confidence_score": match_data['Confiance_Score'],
        "recommendation": "Best Bet" if match_data.get('is_best_bet') else "Normal",
        "is_processed": False
    }

    if existing:
        existing.model_prediction = db_obj['model_prediction']
        existing.fdj_line = db_obj['fdj_line']
        existing.confidence_score = db_obj['confidence_score']
        existing.recommendation = db_obj['recommendation']
    else:
        db.add(DailyPrediction(**db_obj))
    db.commit()

def run_predictions():
    print("--- PRÉDICTIONS FORMATÉES ---")
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    MODEL_PATH = os.path.join(BASE_DIR, "models/xgb_nba_model.json")
    FEATURES_PATH = os.path.join(BASE_DIR, "models/feature_names.pkl")
    DATA_PATH = os.path.join(BASE_DIR, "data/processed/nba_data_train.csv")
    ODDS_PATH = os.path.join(BASE_DIR, "data/daily/cotes_fdj.json")
    
    if not os.path.exists(ODDS_PATH): return

    try:
        model = xgb.XGBRegressor(); model.load_model(MODEL_PATH)
        feature_names = joblib.load(FEATURES_PATH)
        df_hist = pd.read_csv(DATA_PATH)
    except: return
    
    if 'TEAM_ABBREVIATION_Home' in df_hist.columns:
        map_df = df_hist[['TEAM_ID_Home', 'TEAM_ABBREVIATION_Home']].drop_duplicates()
        team_map = dict(zip(map_df.TEAM_ABBREVIATION_Home, map_df.TEAM_ID_Home))
    else: return
    
    with open(ODDS_PATH, 'r', encoding='utf-8') as f: matches = json.load(f)
        
    all_bets = []
    
    # 1. Calcul de tous les paris possibles
    for match in matches:
        home, away = match['home'], match['away']
        X_input = build_features_for_match(home, away, df_hist, team_map, feature_names)
        if X_input is None: continue
        pred_total = float(model.predict(X_input)[0])
        
        for odd in match['odds']:
            line = odd['line']
            otype = odd['type']
            quote = odd['odd']
            
            diff = pred_total - line
            conf = 0
            
            if otype == "OVER":
                conf = min(99, 50 + (diff * 4)) if diff > 0 else 0
            elif otype == "UNDER":
                conf = min(99, 50 + (abs(diff) * 4)) if diff < 0 else 0
            
            if conf > 0: # On ne garde que ce qui a un sens
                all_bets.append({
                    "Date": datetime.now().strftime('%Y-%m-%d'),
                    "Match": f"{home} vs {away}",
                    "Home": home,
                    "Away": away,
                    "Prediction_Modele": round(pred_total, 2),
                    "Ligne_Bookmaker": line,
                    "Type_Pari": otype,
                    "Cote": quote,
                    "Ecart": round(abs(diff), 2),
                    "Confiance_Score": round(conf, 1),
                    "is_best_bet": False # Init
                })

    # 2. Détermination des Best Bets (Meilleur score par match)
    # On groupe par "Match"
    df_bets = pd.DataFrame(all_bets)
    if not df_bets.empty:
        # On trie par Match et Confiance décroissante
        df_bets = df_bets.sort_values(by=['Match', 'Confiance_Score'], ascending=[True, False])
        
        # On marque le premier de chaque groupe comme Best Bet
        best_indices = df_bets.groupby('Match').head(1).index
        df_bets.loc[best_indices, 'is_best_bet'] = True
        
        all_bets = df_bets.to_dict(orient='records')

    # 3. Sauvegarde DB & JSON pour le front
    db = SessionLocal()
    try:
        for bet in all_bets:
            save_prediction_to_db(db, bet)
    finally:
        db.close()
        
    # Sauvegarde JSON formaté pour le frontend (lecture directe)
    FRONTEND_JSON = os.path.join(BASE_DIR, "data/daily/frontend_predictions.json")
    with open(FRONTEND_JSON, 'w') as f:
        json.dump(all_bets, f, indent=4)
    
    print(f"✅ {len(all_bets)} paris générés dont {df_bets['is_best_bet'].sum() if not df_bets.empty else 0} Best Bets.")

if __name__ == "__main__":
    run_predictions()