from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List

# --- Match Result ---
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

class MatchResultCreate(MatchResultBase): pass
class MatchResult(MatchResultBase):
    id: int
    class Config: from_attributes = True

# --- Daily Prediction ---
class DailyPredictionBase(BaseModel):
    match_date: date
    home_team: str
    away_team: str
    model_prediction: float
    fdj_line: float
    bet_type: str
    
    # AJOUT CRITIQUE : La cote
    odd: float = 1.90 
    
    confidence_score: float
    recommendation: str
    bet_result: Optional[str] = None
    actual_score: Optional[float] = None
    payout: Optional[float] = 0.0

class DailyPredictionCreate(DailyPredictionBase): pass
class DailyPrediction(DailyPredictionBase):
    id: int
    created_at: datetime
    is_processed: bool
    class Config: from_attributes = True

# --- Analytics ---
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

# --- System ---
class DataStatus(BaseModel):
    raw_rows: int
    processed_rows: int
    last_update: Optional[date] = None
    is_up_to_date: bool

class ModelStatus(BaseModel):
    exists: bool
    last_trained: Optional[datetime] = None
    mae: float

class SystemStatusResponse(BaseModel):
    data: DataStatus
    model: ModelStatus
    api_status: str

# --- Tasks ---
class TaskTriggerResponse(BaseModel):
    status: str
    task_id: str
    message: str