import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, date

# IMPORTS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_fetcher import fetch_all_game_data
from src.data_processor import process_data
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
    if df_actual.empty:
        print("DataFrame vide, pas de sync.")
        return

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
    Met à jour l'historique avec les prédictions du modèle (Test Set).
    Nécessite que train_xgb.py ait généré le fichier 'latest_test_predictions.csv'.
    """
    print("--- Injection des Prédictions de Test en DB ---")
    pred_path = os.path.join(settings.BASE_DIR, "data/processed/latest_test_predictions.csv")
    
    if not os.path.exists(pred_path):
        print("(Info) Pas de fichier de prédictions de test trouvé. Ignore.")
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
        
        # On cherche le résultat dans la DB directement (remplie par sync_history_to_db juste avant)
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
            
            # --- CORRECTION MAJEURE : UTILISATION DE LA VRAIE COTE ---
            # Si la cote est stockée (ex: 1.85), on l'utilise. Sinon 1.90 par défaut.
            real_odd = pred.odd if (pred.odd and pred.odd > 1.0) else 1.90
            
            if won:
                profit = real_odd - 1.0
            else:
                profit = -1.0
                
            pred.payout = profit
            # ---------------------------------------------------------
            
            updated_count += 1
            
            # Stats pour le rapport du jour
            daily_stats["total"] += 1
            daily_stats["profit"] += profit
            if won:
                daily_stats["wins"] += 1

    db.commit()
    print(f"✅ {updated_count} paris mis à jour depuis la table MatchResult.")
    return daily_stats

def update_performance_metrics(db, daily_stats):
    """Enregistre la performance globale du jour."""
    if daily_stats["total"] == 0: return

    today = datetime.now().date()
    perf = db.query(ModelPerformance).filter(ModelPerformance.date == today).first()
    
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
            mae=0.0 # Le MAE est calculé lors de l'entraînement, pas ici
        )
        db.add(new_perf)
    
    db.commit()
    print("✅ Métriques de performance mises à jour.")

def run_update_pipeline():
    print("==================================================")
    print("   MISE À JOUR & SYNC DB")
    print("==================================================")
    
    # 1. Chargement données réelles (Data Processed doit être à jour via data_processor)
    try:
        if os.path.exists(settings.DATA_PROCESSED):
            df_actual = pd.read_csv(settings.DATA_PROCESSED)
        else:
            df_actual = pd.DataFrame()
            print("[WARN] Fichier processed introuvable. Sync historique impossible.")
    except Exception as e:
        print(f"[WARN] Erreur lecture CSV: {e}")
        df_actual = pd.DataFrame()

    # 2. DB Operations
    db = SessionLocal()
    try:
        # A. Sync les vrais résultats (Score réel)
        if not df_actual.empty:
            sync_history_to_db(db, df_actual)
        
        # B. Évaluation des paris en attente (C'est ici que l'argent se calcule)
        # On passe df_actual mais la fonction utilise surtout la DB MatchResult
        stats = evaluate_db_predictions(db, df_actual)
        
        # C. Update KPI Dashboard
        update_performance_metrics(db, stats)
        
        # D. (Optionnel) Injection historique Test si dispo
        inject_test_predictions_into_db(db)
        
    except Exception as e:
        print(f"❌ Erreur DB Sync: {e}")
        # On log l'erreur complète pour débug
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_update_pipeline()