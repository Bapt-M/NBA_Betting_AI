from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os
import json # AJOUT
import pandas as pd
from datetime import datetime, date

from backend.database import get_db
from backend import models, schemas
from backend.config import settings

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/status", response_model=schemas.SystemStatusResponse)
def get_system_status(db: Session = Depends(get_db)):
    # 1. Check Raw Data (CSV)
    raw_count = 0
    if os.path.exists(settings.DATA_RAW):
        try:
            df_raw = pd.read_csv(settings.DATA_RAW, usecols=[0])
            raw_count = len(df_raw)
        except: pass

    # 2. Check Processed Data (DB)
    processed_count = db.query(models.MatchResult).count()
    
    # 3. Check Up-to-date
    last_match = db.query(models.MatchResult).order_by(models.MatchResult.date.desc()).first()
    last_date = last_match.date.date() if last_match else None
    
    is_up_to_date = False
    if last_date:
        delta = (datetime.now().date() - last_date).days
        is_up_to_date = delta <= 1

    # 4. Check Model
    model_exists = os.path.exists(settings.MODEL_PATH)
    model_mae = 0.0
    last_trained = None
    
    if model_exists:
        last_trained = datetime.fromtimestamp(os.path.getmtime(settings.MODEL_PATH))
        
        # --- CORRECTION : Lire le fichier model_metrics.json ---
        metrics_path = os.path.join(os.path.dirname(settings.MODEL_PATH), "model_metrics.json")
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, "r") as f:
                    metrics = json.load(f)
                    model_mae = metrics.get("mae", 0.0)
            except: pass
        
        # Fallback si le fichier JSON n'existe pas (ancienne méthode)
        if model_mae == 0.0:
            perf = db.query(models.ModelPerformance).order_by(models.ModelPerformance.date.desc()).first()
            if perf:
                model_mae = perf.mae

    return {
        "data": {
            "raw_rows": raw_count,
            "processed_rows": processed_count,
            "last_update": last_date,
            "is_up_to_date": is_up_to_date
        },
        "model": {
            "exists": model_exists,
            "last_trained": last_trained,
            "mae": round(model_mae, 2)
        },
        "api_status": "online"
    }