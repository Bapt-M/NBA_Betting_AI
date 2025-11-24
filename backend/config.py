import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "NBA Betting AI Dashboard"
    
    # Database & Redis
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://nba_user:nba_password@db:5432/nba_betting_db")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

    # Paths (Absolus pour Docker)
    BASE_DIR: str = "/app" if os.path.exists("/app") else os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    DATA_RAW: str = os.path.join(BASE_DIR, "data/raw/nba_games_raw.csv")
    DATA_PROCESSED: str = os.path.join(BASE_DIR, "data/processed/nba_data_train.csv")
    DATA_DAILY_ODDS: str = os.path.join(BASE_DIR, "data/daily/cotes_fdj.json")
    MODEL_PATH: str = os.path.join(BASE_DIR, "models/xgb_nba_model.json")
    FEATURE_NAMES: str = os.path.join(BASE_DIR, "models/feature_names.pkl")

    class Config:
        case_sensitive = True

settings = Settings()