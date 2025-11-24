from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
# CORRECTION : Imports absolus
from backend import models, schemas
from backend.database import get_db

router = APIRouter(prefix="/results", tags=["Results"])

@router.get("/latest", response_model=List[schemas.MatchResult])
def get_latest_results(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(models.MatchResult)\
             .order_by(models.MatchResult.date.desc())\
             .limit(limit)\
             .all()