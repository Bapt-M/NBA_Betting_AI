from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
# CORRECTION : Imports absolus
from backend import models, schemas
from backend.database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/roi", response_model=schemas.AnalyticsResponse)
def get_roi_analytics(db: Session = Depends(get_db)):
    perfs = db.query(models.ModelPerformance).order_by(models.ModelPerformance.date.asc()).all()
    
    if not perfs:
        return {
            "summary": {"total_bets": 0, "win_rate": 0, "roi": 0, "profit_net": 0},
            "history": []
        }

    total_bets = sum(p.total_predictions for p in perfs)
    total_wins = sum(p.correct_predictions for p in perfs)
    total_profit = sum(p.profit_net for p in perfs)
    
    win_rate = (total_wins / total_bets) if total_bets > 0 else 0
    roi = (total_profit / total_bets) * 100 if total_bets > 0 else 0

    history = []
    running_profit = 0.0
    for p in perfs:
        running_profit += p.profit_net
        history.append({"date": p.date, "cumulative_profit": running_profit})

    return {
        "summary": {
            "total_bets": total_bets,
            "win_rate": round(win_rate * 100, 2),
            "roi": round(roi, 2),
            "profit_net": round(total_profit, 2)
        },
        "history": history
    }