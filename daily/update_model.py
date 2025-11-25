import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, date

# IMPORTS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_fetcher import fetch_all_game_data
from src.data_processor import process_data
from src.train_xgb import train_xgboost_model
from backend.database import SessionLocal
from backend.models import MatchResult, DailyPrediction, ModelPerformance
from backend.config import settings

def sync_history_to_db(db, df_actual):
    """
    Copie les données du CSV historique vers la table match_results.
    """
    print("--- Sync Historique DB ---")
    
    count = 0
    # On prend une plage large pour être sûr
    recent_games = df_actual.tail(100)
    
    for _, row in recent_games.iterrows():
        try:
            game_date = pd.to_datetime(row['GAME_DATE']).date()
            match_id = f"{game_date.strftime('%Y%m%d')}-{row['TEAM_ABBREVIATION_Home']}-{row['TEAM_ABBREVIATION_Away']}"
            
            exists = db.query(MatchResult).filter(MatchResult.match_id_nba == match_id).first()
            if not exists:
                new_match = MatchResult(
                    match_id_nba=match_id,
                    date=game_date,
                    home_team=row['TEAM_ABBREVIATION_Home'],
                    away_team=row['TEAM_ABBREVIATION_Away'],
                    actual_total=float(row['TARGET_Total_Pts'])
                )
                db.add(new_match)
                count += 1
        except Exception:
            continue
            
    db.commit()
    print(f"✅ {count} nouveaux matchs ajoutés à l'historique DB.")

def inject_test_predictions_into_db(db):
    """
    Met à jour l'historique avec les prédictions du modèle (Test Set)
    """
    print("--- Injection des Prédictions de Test en DB ---")
    pred_path = os.path.join(settings.BASE_DIR, "data/processed/latest_test_predictions.csv")
    
    if not os.path.exists(pred_path):
        return

    df_preds = pd.read_csv(pred_path)
    count = 0
    
    for _, row in df_preds.iterrows():
        try:
            game_date = pd.to_datetime(row['GAME_DATE']).date()
            match_id = f"{game_date.strftime('%Y%m%d')}-{row['TEAM_ABBREVIATION_Home']}-{row['TEAM_ABBREVIATION_Away']}"
            
            match = db.query(MatchResult).filter(MatchResult.match_id_nba == match_id).first()
            if match:
                match.predicted_total = float(row['Predicted_Total'])
                diff = abs(match.actual_total - match.predicted_total)
                match.prediction_correct = diff < 5.0 
                count += 1
        except Exception:
            continue
            
    db.commit()
    print(f"✅ {count} matchs historiques mis à jour avec la prédiction.")

def evaluate_db_predictions(db, df_actual=None):
    """
    Vérifie les paris en attente en comparant avec la table MatchResult (Source de vérité).
    """
    print("--- Évaluation des Paris (Source: DB MatchResult) ---")
    
    # Récupérer tous les paris qui ne sont pas encore traités
    pending_preds = db.query(DailyPrediction).filter(DailyPrediction.is_processed == False).all()
    
    updated_count = 0
    daily_stats = {"total": 0, "wins": 0, "profit": 0.0}
    
    for pred in pending_preds:
        # Reconstitution de l'ID unique du match pour le trouver dans la table Résultats
        # Format: YYYYMMDD-HOME-AWAY
        match_id = f"{pred.match_date.strftime('%Y%m%d')}-{pred.home_team}-{pred.away_team}"
        
        # On cherche le résultat dans la DB directement
        match_res = db.query(MatchResult).filter(MatchResult.match_id_nba == match_id).first()
        
        if match_res:
            real_score = match_res.actual_total
            
            # Logique WIN/LOSS
            won = False
            if pred.bet_type == "OVER" and real_score > pred.fdj_line: won = True
            elif pred.bet_type == "UNDER" and real_score < pred.fdj_line: won = True
            
            # Mise à jour
            pred.is_processed = True
            pred.actual_score = real_score
            pred.bet_result = "WIN" if won else "LOSS"
            
            # Simulation Profit (Cote fixée à 1.90 si inconnue, ou utiliser une vraie cote si dispo)
            # Ici on utilise 1.90 par défaut comme dans l'ancien code
            cote = 1.90
            pred.payout = (cote - 1) if won else -1.0
            
            updated_count += 1
            
            # Stats pour le rapport du jour
            daily_stats["total"] += 1
            if won:
                daily_stats["wins"] += 1
                daily_stats["profit"] += (cote - 1)
            else:
                daily_stats["profit"] -= 1.0

    db.commit()
    print(f"✅ {updated_count} paris mis à jour depuis la table MatchResult.")
    return daily_stats

def update_performance_metrics(db, daily_stats):
    """Enregistre la performance globale du jour."""
    if daily_stats["total"] == 0: return

    today = datetime.now().date()
    perf = db.query(ModelPerformance).filter(ModelPerformance.date == today).first()
    
    # Calcul simple pour l'exemple (à affiner si on lance plusieurs fois par jour)
    success_rate = daily_stats["wins"] / daily_stats["total"]
    
    if perf:
        perf.total_predictions += daily_stats["total"]
        perf.correct_predictions += daily_stats["wins"]
        perf.profit_net += daily_stats["profit"]
        perf.success_rate = perf.correct_predictions / perf.total_predictions
    else:
        new_perf = ModelPerformance(
            date=today,
            total_predictions=daily_stats["total"],
            correct_predictions=daily_stats["wins"],
            success_rate=success_rate,
            profit_net=daily_stats["profit"],
            mae=0.0
        )
        db.add(new_perf)
    
    db.commit()
    print("✅ Métriques de performance mises à jour.")

def run_update_pipeline():
    print("==================================================")
    print("   MISE À JOUR & SYNC DB")
    print("==================================================")
    
    # 1. Fetch & Process (Si possible)
    try:
        if os.path.exists(settings.DATA_RAW):
             # On tente de charger le CSV s'il existe pour sync_history
            df_actual = pd.read_csv(settings.DATA_PROCESSED)
        else:
            df_actual = pd.DataFrame() # Vide
    except Exception:
        df_actual = pd.DataFrame()

    # 2. DB Operations
    db = SessionLocal()
    try:
        # Si le CSV est valide, on sync l'historique (utile pour les nouveaux vrais matchs)
        if not df_actual.empty:
            sync_history_to_db(db, df_actual)
        
        # Injection des prédictions de test (si le fichier existe)
        inject_test_predictions_into_db(db)
        
        # Évaluation des paris (Source DB)
        stats = evaluate_db_predictions(db, df_actual) # df_actual n'est plus utilisé mais gardé en paramètre optionnel
        
        # Update KPI
        update_performance_metrics(db, stats)
        
    except Exception as e:
        print(f"❌ Erreur DB Sync: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_update_pipeline()