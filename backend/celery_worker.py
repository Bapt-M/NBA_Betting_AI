from celery import Celery
from celery.schedules import crontab
import os
import sys

# Configuration
celery_app = Celery(
    "nba_tasks",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
)

# --- ROUTINES AUTOMATIQUES ---
celery_app.conf.beat_schedule = {
    'morning-update': {
        'task': 'full_morning_pipeline',
        'schedule': crontab(hour=8, minute=0),
    },
    'afternoon-predict': {
        'task': 'full_afternoon_pipeline',
        'schedule': crontab(hour=14, minute=0),
    },
}

# --- TÂCHES UNITAIRES (Pour appel manuel via UI) ---

@celery_app.task(name="task_fetch_data")
def task_fetch_data():
    sys.path.append("/app")
    from src.data_fetcher import fetch_all_game_data
    return fetch_all_game_data()

@celery_app.task(name="task_process_data")
def task_process_data():
    sys.path.append("/app")
    from src.data_processor import process_data
    process_data()
    return "Data processed successfully"

@celery_app.task(name="task_train_model")
def task_train_model():
    sys.path.append("/app")
    from src.train_xgb import train_xgboost_model
    train_xgboost_model()
    return "Model trained successfully"

@celery_app.task(name="task_scrape_odds")
def task_scrape_odds():
    sys.path.append("/app")
    from daily.scraper_fdj import scrape_nba_odds
    scrape_nba_odds()
    return "Odds scraped"

@celery_app.task(name="task_predict_daily")
def task_predict_daily():
    sys.path.append("/app")
    from daily.daily_predict import run_predictions
    run_predictions()
    return "Daily predictions generated and saved to DB"

@celery_app.task(name="task_update_history")
def task_update_history():
    """Met à jour l'historique des matchs et évalue les paris en base."""
    sys.path.append("/app")
    
    # CORRECTION ICI : Import des nouvelles fonctions DB
    from daily.update_model import sync_history_to_db, update_performance_metrics, evaluate_db_predictions
    from backend.database import SessionLocal
    from backend.config import settings
    import pandas as pd
    import os
    
    if not os.path.exists(settings.DATA_PROCESSED):
        return "Error: Processed data file not found. Run process_data first."

    db = SessionLocal()
    try:
        # 1. Charger les nouvelles données traitées
        df = pd.read_csv(settings.DATA_PROCESSED)
        
        # 2. Synchroniser l'historique visuel (MatchResult)
        sync_history_to_db(db, df)
        
        # 3. Évaluer les paris (DailyPrediction -> WIN/LOSS)
        stats = evaluate_db_predictions(db, df)
        
        # 4. Mettre à jour les stats globales (ModelPerformance)
        update_performance_metrics(db, stats)
        
    except Exception as e:
        print(f"Error in update history task: {e}")
        raise e
    finally:
        db.close()
        
    return "History updated and bets evaluated"

# --- PIPELINES COMPLETS ---

@celery_app.task(name="full_morning_pipeline")
def full_morning_pipeline():
    # Chainage : Fetch -> Process -> Update History -> Train
    task_fetch_data()
    task_process_data()
    task_update_history()
    task_train_model()
    return "Morning Pipeline Done"

@celery_app.task(name="full_afternoon_pipeline")
def full_afternoon_pipeline():
    # Chainage : Scrape -> Predict
    task_scrape_odds()
    task_predict_daily()
    return "Afternoon Pipeline Done"