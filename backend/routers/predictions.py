from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db

router = APIRouter(prefix="/predictions", tags=["Predictions"])

@router.get("/today", response_model=List[schemas.DailyPrediction])
def get_todays_predictions(db: Session = Depends(get_db)):
    """
    Récupère les prédictions du jour qui n'ont pas encore été archivées/traitées.
    """
    return db.query(models.DailyPrediction)\
             .filter(models.DailyPrediction.is_processed == False)\
             .order_by(models.DailyPrediction.confidence_score.desc())\
             .all()