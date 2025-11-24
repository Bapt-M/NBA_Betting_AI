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
    sys.path.append("/app")
    from daily.update_model import run_update_pipeline
    # Note: update_model fait déjà fetch + process + train en interne dans sa version actuelle
    # On peut soit l'appeler directement, soit appeler juste la partie évaluation
    from daily.update_model import evaluate_past_predictions, sync_history_to_db, update_performance_metrics
    from backend.database import SessionLocal
    import pandas as pd
    from backend.config import settings
    
    # Version "Lite" qui ne refait pas tout le fetch/train (car on a des boutons séparés)
    db = SessionLocal()
    try:
        df = pd.read_csv(settings.DATA_PROCESSED)
        sync_history_to_db(db, df)
        # Evaluation des paris en DB
        from daily.update_model import evaluate_db_predictions
        stats = evaluate_db_predictions(db, df)
        update_performance_metrics(db, stats)
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