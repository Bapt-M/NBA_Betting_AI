from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import models, schemas
from database import get_db

router = APIRouter(prefix="/results", tags=["Results"])

@router.get("/latest", response_model=List[schemas.MatchResult])
def get_latest_results(limit: int = 50, db: Session = Depends(get_db)):
    """
    Récupère les derniers résultats de matchs avec la comparaison prédiction/réalité.
    """
    return db.query(models.MatchResult)\
             .order_by(models.MatchResult.date.desc())\
             .limit(limit)\
             .all()