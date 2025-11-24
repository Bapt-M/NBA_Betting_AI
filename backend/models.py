from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Date
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class MatchResult(Base):
    __tablename__ = "match_results"
    id = Column(Integer, primary_key=True, index=True)
    match_id_nba = Column(String, unique=True, index=True)
    date = Column(DateTime)
    home_team = Column(String)
    away_team = Column(String)
    actual_total = Column(Float)
    # Pour l'historique visuel
    predicted_total = Column(Float, nullable=True)
    betting_line = Column(Float, nullable=True)
    prediction_correct = Column(Boolean, nullable=True) 

class DailyPrediction(Base):
    __tablename__ = "daily_predictions"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    match_date = Column(Date)
    home_team = Column(String)
    away_team = Column(String)
    model_prediction = Column(Float)
    fdj_line = Column(Float)
    bet_type = Column(String)
    confidence_score = Column(Float)
    recommendation = Column(String)
    is_processed = Column(Boolean, default=False)
    
    # NOUVEAUX CHAMPS
    bet_result = Column(String, nullable=True) 
    actual_score = Column(Float, nullable=True) 
    payout = Column(Float, default=0.0) 

class ModelPerformance(Base):
    __tablename__ = "model_performance"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True)
    total_predictions = Column(Integer)
    correct_predictions = Column(Integer)
    success_rate = Column(Float)
    profit_net = Column(Float)
    mae = Column(Float)