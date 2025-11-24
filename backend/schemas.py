from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List

# --- Match Result Schemas ---
class MatchResultBase(BaseModel):
    match_id_nba: str
    date: datetime
    home_team: str
    away_team: str
    actual_total: float
    predicted_total: Optional[float] = None
    betting_line: Optional[float] = None
    prediction_correct: Optional[bool] = None
    performance_score: Optional[int] = None

class MatchResultCreate(MatchResultBase):
    pass

class MatchResult(MatchResultBase):
    id: int
    class Config:
        from_attributes = True

# --- Daily Prediction Schemas ---
class DailyPredictionBase(BaseModel):
    match_date: date
    home_team: str
    away_team: str
    model_prediction: float
    fdj_line: float
    bet_type: str
    confidence_score: float
    recommendation: str

class DailyPredictionCreate(DailyPredictionBase):
    pass

class DailyPrediction(DailyPredictionBase):
    id: int
    created_at: datetime
    is_processed: bool
    
    class Config:
        from_attributes = True

# --- Performance Analytics Schemas ---
class PerformanceSummary(BaseModel):
    total_bets: int
    win_rate: float
    roi: float
    profit_net: float
    
class ROIDataPoint(BaseModel):
    date: date
    cumulative_profit: float

class AnalyticsResponse(BaseModel):
    summary: PerformanceSummary
    history: List[ROIDataPoint]

# --- Task Schemas ---
class TaskTriggerResponse(BaseModel):
    status: str
    task_id: str
    message: str