import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import json
import os
import sys
from datetime import datetime

# IMPORTS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils import get_team_code
from backend.database import SessionLocal
from backend.models import DailyPrediction
from backend.config import settings

def get_latest_stats(df, team_code, team_map):
    """Récupère la dernière ligne de stats connue pour une équipe."""
    if team_code not in team_map: return None
    team_id = team_map[team_code]
    
    mask_home = df['TEAM_ID_Home'] == team_id
    df_home = df[mask_home].copy() if mask_home.any() else pd.DataFrame()
    if not df_home.empty:
        cols = ['GAME_DATE'] + [c for c in df.columns if c.endswith('_Home')]
        df_home = df_home[cols]
        df_home.columns = [c.replace('_Home', '') for c in df_home.columns]
    
    mask_away = df['TEAM_ID_Away'] == team_id
    df_away = df[mask_away].copy() if mask_away.any() else pd.DataFrame()
    if not df_away.empty:
        cols = ['GAME_DATE'] + [c for c in df.columns if c.endswith('_Away') and c != 'GAME_DATE_Away']
        df_away = df_away[cols]
        df_away.columns = [c.replace('_Away', '') for c in df_away.columns]
        
    if df_home.empty and df_away.empty: return None
    
    df_team = pd.concat([df_home, df_away], ignore_index=True)
    df_team['GAME_DATE'] = pd.to_datetime(df_team['GAME_DATE'])
    df_team.sort_values('GAME_DATE', inplace=True)
    
    return df_team.iloc[-1] if not df_team.empty else None

def build_features_for_match(home_code, away_code, df_hist, team_map, feature_names):
    h_stats = get_latest_stats(df_hist, home_code, team_map)
    a_stats = get_latest_stats(df_hist, away_code, team_map)
    
    if h_stats is None or a_stats is None: return None, 0.0
    
    row = {}
    for col in h_stats.index:
        if any(x in col for x in ['L5_', 'Szn_']): row[f"{col}_Home"] = h_stats[col]
    for col in a_stats.index:
        if any(x in col for x in ['L5_', 'Szn_']): row[f"{col}_Away"] = a_stats[col]
            
    row['Rest_Days_Home'] = 2.0
    row['Rest_Days_Away'] = 2.0
    
    try:
        p_pace = (h_stats.get('L5_POSS', 98) + a_stats.get('L5_POSS', 98) + 
                  h_stats.get('Szn_POSS', 98) + a_stats.get('Szn_POSS', 98)) / 4
        row['Meta_Predicted_Pace'] = p_pace
        row['Meta_Rest_Diff'] = 0.0
        poss_away = a_stats.get('L5_POSS', 98) or 1
        row['Meta_Off_vs_Def_Home'] = h_stats.get('L5_ORtg', 110) - (100 * a_stats.get('L5_Defensive_PTS', 110) / poss_away)
        
        volat_h = h_stats.get('L5_Volat_PTS', 10.0) 
        volat_a = a_stats.get('L5_Volat_PTS', 10.0)
        if pd.isna(volat_h): volat_h = 10.0
        if pd.isna(volat_a): volat_a = 10.0
        
        risk_factor = volat_h + volat_a
        row['Meta_Risk_Factor'] = risk_factor

    except Exception as e:
        return None, 0.0

    df_input = pd.DataFrame([row])
    for col in feature_names:
        if col not in df_input.columns: df_input[col] = 0.0
            
    return df_input[feature_names], float(risk_factor)

def check_injuries(home, away, injuries_data):
    malus = 0
    notes = []
    
    for team in [home, away]:
        if team in injuries_data:
            players = injuries_data[team]
            out_count = sum(1 for p in players if 'Out' in p['status'])
            if out_count > 0:
                malus += (out_count * 5)
                notes.append(f"{out_count} absents chez {team}")
    
    return malus, "; ".join(notes)

def save_prediction_to_db(db, match_data):
    # RECHERCHE INTELLIGENTE : Distinction des lignes
    existing = db.query(DailyPrediction).filter(
        DailyPrediction.home_team == match_data['Home'],
        DailyPrediction.away_team == match_data['Away'],
        DailyPrediction.bet_type == match_data['Type_Pari'],
        DailyPrediction.fdj_line == float(match_data['Ligne_Bookmaker']), 
        DailyPrediction.is_processed == False 
    ).first()

    db_obj = {
        "match_date": match_data['Date'],
        "home_team": match_data['Home'],
        "away_team": match_data['Away'],
        "model_prediction": float(match_data['Prediction_Modele']),
        "fdj_line": float(match_data['Ligne_Bookmaker']),
        "bet_type": match_data['Type_Pari'],
        "odd": float(match_data['Cote']),
        "confidence_score": float(match_data['Confiance_Score']),
        "recommendation": "Best Bet" if match_data.get('is_best_bet') else match_data.get('Info_Risk', 'Normal'),
        "is_processed": False
        # CORRECTION : Suppression de 'Prob_High_Score' car la colonne n'existe pas en DB
        # L'info est toujours présente dans le JSON pour le frontend
    }

    if existing:
        # UPDATE
        existing.match_date = db_obj['match_date']
        existing.odd = db_obj['odd']
        existing.confidence_score = db_obj['confidence_score']
        existing.recommendation = db_obj['recommendation']
    else:
        # INSERT
        db.add(DailyPrediction(**db_obj))
    
    db.commit()

def run_predictions():
    print("--- PRÉDICTIONS HYBRIDES (Toutes Lignes) ---")
    
    if not os.path.exists(settings.DATA_DAILY_ODDS):
        print("Pas de cotes disponibles.")
        return

    try:
        regressor = xgb.XGBRegressor()
        regressor.load_model(settings.MODEL_PATH)
        
        clf_path = settings.MODEL_PATH.replace(".json", "_classifier.json")
        classifier = None
        if os.path.exists(clf_path):
            classifier = xgb.XGBClassifier()
            classifier.load_model(clf_path)
        
        feature_names = joblib.load(settings.FEATURE_NAMES)
        df_hist = pd.read_csv(settings.DATA_PROCESSED)
        
        injuries_path = os.path.join(settings.BASE_DIR, "data/daily/injuries.json")
        injuries_data = {}
        if os.path.exists(injuries_path):
            with open(injuries_path, 'r') as f: injuries_data = json.load(f)
            
    except Exception as e:
        print(f"Erreur init modèles/data: {e}")
        return
    
    if 'TEAM_ABBREVIATION_Home' not in df_hist.columns: return
    map_df = df_hist[['TEAM_ID_Home', 'TEAM_ABBREVIATION_Home']].drop_duplicates()
    team_map = dict(zip(map_df.TEAM_ABBREVIATION_Home, map_df.TEAM_ID_Home))
    
    with open(settings.DATA_DAILY_ODDS, 'r', encoding='utf-8') as f: matches = json.load(f)
        
    all_bets = []
    
    for match in matches:
        home, away = match['home'], match['away']
        
        X_input, risk_factor = build_features_for_match(home, away, df_hist, team_map, feature_names)
        if X_input is None: continue
        
        pred_total = float(regressor.predict(X_input)[0])
        
        prob_high_score = 0.5
        if classifier:
            prob_high_score = float(classifier.predict_proba(X_input)[0][1])

        injury_malus, injury_note = check_injuries(home, away, injuries_data)

        for odd in match['odds']:
            line = odd['line']
            otype = odd['type']
            quote = odd['odd']
            
            diff = pred_total - line
            
            base_conf = 0
            if otype == "OVER" and diff > 0:
                base_conf = 50 + (diff * 3)
            elif otype == "UNDER" and diff < 0:
                base_conf = 50 + (abs(diff) * 3)
            
            if base_conf < 50: continue
            
            final_conf = base_conf
            
            if otype == "OVER":
                if prob_high_score > 0.60: final_conf += 5
                elif prob_high_score < 0.40: final_conf -= 10
            elif otype == "UNDER":
                if prob_high_score < 0.40: final_conf += 5
                elif prob_high_score > 0.60: final_conf -= 10

            if risk_factor > 25:
                final_conf -= (risk_factor - 25)
            
            final_conf -= injury_malus
            final_conf = max(0, min(99, final_conf))
            
            if final_conf > 50:
                all_bets.append({
                    "Date": datetime.now().strftime('%Y-%m-%d'),
                    "Match": f"{home} vs {away}",
                    "Home": home, "Away": away,
                    "Prediction_Modele": float(round(pred_total, 2)),
                    "Ligne_Bookmaker": float(line),
                    "Type_Pari": otype,
                    "Cote": float(quote),
                    "Ecart": float(round(abs(diff), 2)),
                    "Confiance_Score": float(round(final_conf, 1)),
                    "Prob_High_Score": float(round(prob_high_score * 100, 1)),
                    "Info_Risk": f"Risk:{int(risk_factor)} | {injury_note}",
                    "is_best_bet": False
                })

    # --- SELECTION BEST BETS (LE MEILLEUR DE CHAQUE MATCH) ---
    bets_by_match = {}
    for bet in all_bets:
        match_key = bet['Match']
        if match_key not in bets_by_match:
            bets_by_match[match_key] = []
        bets_by_match[match_key].append(bet)

    for match_key, bets in bets_by_match.items():
        if not bets: continue
        # On trie par confiance décroissante
        bets.sort(key=lambda x: x['Confiance_Score'], reverse=True)
        # Le premier est le Best Bet
        bets[0]['is_best_bet'] = True

    # Sauvegarde JSON
    OUTPUT_JSON = os.path.join(settings.BASE_DIR, "data/daily/frontend_predictions.json")
    with open(OUTPUT_JSON, 'w') as f: json.dump(all_bets, f, indent=4)

    # Sauvegarde DB
    db = SessionLocal()
    try:
        for bet in all_bets:
            save_prediction_to_db(db, bet)
    finally: db.close()
    
    print(f"✅ {len(all_bets)} paris générés (DB Clean).")

if __name__ == "__main__":
    run_predictions()