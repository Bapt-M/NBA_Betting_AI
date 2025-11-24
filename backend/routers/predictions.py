from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend import models, schemas
from backend.database import get_db
import json
import os

router = APIRouter(prefix="/predictions", tags=["Predictions"])

@router.get("/json_formatted")
def get_formatted_predictions():
    """Renvoie directement le JSON généré par daily_predict pour le tableau exact"""
    path = "/app/data/daily/frontend_predictions.json"
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return []

@router.get("/today", response_model=List[schemas.DailyPrediction])
def get_todays_predictions(db: Session = Depends(get_db)):
    return db.query(models.DailyPrediction)\
             .filter(models.DailyPrediction.is_processed == False)\
             .order_by(models.DailyPrediction.confidence_score.desc())\
             .all()
             
@router.get("/history", response_model=List[schemas.DailyPrediction])
def get_prediction_history(limit: int = 1000, db: Session = Depends(get_db)):
    """
    Récupère l'historique des prédictions terminées (avec résultats WIN/LOSS).
    """
    return db.query(models.DailyPrediction)\
             .filter(models.DailyPrediction.is_processed == True)\
             .order_by(models.DailyPrediction.match_date.desc())\
             .limit(limit)\
             .all()