import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App config
    PROJECT_NAME: str = "NBA Betting AI Dashboard"
    API_V1_STR: str = "/api"
    
    # Database (PostgreSQL)
    # Valeur par défaut pour Docker Compose
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://nba_user:nba_password@db:5432/nba_betting_db")
    
    # Redis / Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

    class Config:
        case_sensitive = True

settings = Settings()