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

# Chemins
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TRAIN_DATA = os.path.join(BASE_DIR, "data/processed/nba_data_train.csv")

def sync_history_to_db(db, df_actual):
    """
    Copie les données du CSV historique vers la table match_results.
    C'est utile pour afficher l'historique dans le Dashboard.
    """
    print("--- Sync Historique DB ---")
    # On ne synchronise que les matchs récents pour aller vite (ex: 30 derniers jours)
    # Ou on vérifie s'ils existent déjà via match_id (construit depuis date+teams)
    
    count = 0
    # Pour l'exemple, on prend les 50 derniers matchs du CSV
    recent_games = df_actual.tail(50)
    
    for _, row in recent_games.iterrows():
        # Création d'un ID unique : YYYYMMDD-HOME-AWAY
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
            
    db.commit()
    print(f"✅ {count} nouveaux matchs ajoutés à l'historique DB.")

def evaluate_db_predictions(db, df_actual):
    """
    Vérifie les paris en attente dans la table DailyPrediction.
    """
    print("--- Évaluation des Paris ---")
    
    # Récupérer les prédictions non traitées
    pending_preds = db.query(DailyPrediction).filter(DailyPrediction.is_processed == False).all()
    
    updated_count = 0
    daily_stats = {"total": 0, "wins": 0, "profit": 0.0}
    
    # Mapping rapide pour recherche dans df_actual (plus rapide que loop)
    # On crée une clé unique Date+Home dans le dataframe
    df_actual['lookup_key'] = df_actual.apply(
        lambda x: f"{pd.to_datetime(x['GAME_DATE']).date()}-{x['TEAM_ABBREVIATION_Home']}", axis=1
    )
    
    for pred in pending_preds:
        # Clé de recherche
        key = f"{pred.match_date}-{pred.home_team}"
        
        # Trouver le match dans le CSV mis à jour
        match_row = df_actual[df_actual['lookup_key'] == key]
        
        if not match_row.empty:
            real_score = match_row.iloc[0]['TARGET_Total_Pts']
            
            # Vérification du pari
            won = False
            if pred.bet_type == "OVER" and real_score > pred.fdj_line: won = True
            elif pred.bet_type == "UNDER" and real_score < pred.fdj_line: won = True
            
            # Mise à jour DB
            # On pourrait lier ça à MatchResult ici, mais restons simples
            pred.is_processed = True
            updated_count += 1
            
            # Stats du jour
            daily_stats["total"] += 1
            if won:
                daily_stats["wins"] += 1
                # Profit simulé (cote moyenne ~1.80)
                daily_stats["profit"] += 0.80 
            else:
                daily_stats["profit"] -= 1.00
                
            # On met aussi à jour MatchResult si on veut afficher la prédiction à côté du résultat
            # (Logique à implémenter selon besoin)

    db.commit()
    print(f"✅ {updated_count} paris vérifiés et mis à jour.")
    return daily_stats

def update_performance_metrics(db, daily_stats):
    """Enregistre la performance globale du jour."""
    if daily_stats["total"] == 0: return

    today = datetime.now().date()
    
    # Vérifier si perf existe déjà
    perf = db.query(ModelPerformance).filter(ModelPerformance.date == today).first()
    
    success_rate = daily_stats["wins"] / daily_stats["total"]
    
    if perf:
        perf.total_predictions += daily_stats["total"]
        perf.correct_predictions += daily_stats["wins"]
        perf.profit_net += daily_stats["profit"]
        # Recalcul taux
        perf.success_rate = perf.correct_predictions / perf.total_predictions
    else:
        new_perf = ModelPerformance(
            date=today,
            total_predictions=daily_stats["total"],
            correct_predictions=daily_stats["wins"],
            success_rate=success_rate,
            profit_net=daily_stats["profit"],
            mae=0.0 # TODO: Calculer la MAE réelle
        )
        db.add(new_perf)
    
    db.commit()
    print("✅ Métriques de performance mises à jour.")

def run_update_pipeline():
    print("==================================================")
    print("   MISE À JOUR & SYNC DB")
    print("==================================================")
    
    # 1. Fetch & Process Data (CSV)
    try:
        fetch_all_game_data()
        process_data()
    except Exception as e:
        print(f"❌ Erreur Fetch/Process: {e}")
        return

    # 2. DB Operations
    db = SessionLocal()
    try:
        # Recharger le CSV frais
        if not os.path.exists(TRAIN_DATA):
            print("❌ CSV non trouvé après update.")
            return
        df_actual = pd.read_csv(TRAIN_DATA)
        
        # Sync Historique
        sync_history_to_db(db, df_actual)
        
        # Check Paris
        stats = evaluate_db_predictions(db, df_actual)
        
        # Update KPI
        update_performance_metrics(db, stats)
        
    except Exception as e:
        print(f"❌ Erreur DB Sync: {e}")
    finally:
        db.close()

    # 3. Retrain Model
    print("\n--- Ré-entraînement ---")
    try:
        train_xgboost_model()
    except Exception as e:
        print(f"❌ Erreur Training: {e}")

if __name__ == "__main__":
    run_update_pipeline()