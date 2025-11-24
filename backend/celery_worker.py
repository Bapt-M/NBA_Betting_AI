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

# Configuration du Planning (Schedules)
celery_app.conf.beat_schedule = {
    # 08:00 : Mise à jour des données et du modèle
    'morning-update-routine': {
        'task': 'run_morning_pipeline',
        'schedule': crontab(hour=8, minute=0),
    },
    # 14:00 : Récupération des cotes et prédictions
    'afternoon-prediction-routine': {
        'task': 'run_afternoon_pipeline',
        'schedule': crontab(hour=14, minute=0),
    },
}

# --- DÉFINITION DES TÂCHES ---

@celery_app.task(name="run_morning_pipeline")
def run_morning_pipeline():
    """Exécute update_model.py : Fetch results -> Eval -> Train"""
    # Import dynamique pour éviter les erreurs circulaires
    sys.path.append("/app")
    from daily.update_model import run_update_pipeline
    
    print(">>> Démarrage Pipeline Matin")
    run_update_pipeline()
    
    # TODO: Lire le fichier model_history_log.csv généré et le sauvegarder en BDD (Table ModelPerformance)
    return "Morning Pipeline Completed"

@celery_app.task(name="run_afternoon_pipeline")
def run_afternoon_pipeline():
    """Exécute scraper_fdj.py puis daily_predict.py"""
    sys.path.append("/app")
    from daily.scraper_fdj import scrape_nba_odds
    from daily.daily_predict import run_predictions
    
    print(">>> Démarrage Pipeline Après-midi")
    
    # 1. Scraper les cotes
    scrape_nba_odds()
    
    # 2. Générer les prédictions
    run_predictions()
    
    # TODO: Lire le fichier best_bets.csv généré et le sauvegarder en BDD (Table DailyPrediction)
    return "Afternoon Pipeline Completed"