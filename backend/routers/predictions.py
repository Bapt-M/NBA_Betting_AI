from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json
import os
from backend import models, schemas
from backend.database import get_db

router = APIRouter(prefix="/predictions", tags=["Predictions"])

@router.get("/json_formatted")
def get_formatted_predictions():
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
    return db.query(models.DailyPrediction)\
             .filter(models.DailyPrediction.is_processed == True)\
             .order_by(models.DailyPrediction.match_date.desc())\
             .limit(limit)\
             .all()

# --- NOUVELLE FONCTION POUR CHANGER LE BEST BET MANUELLEMENT ---
@router.put("/toggle_best_bet")
def toggle_best_bet_status(payload: schemas.BestBetToggle, db: Session = Depends(get_db)):
    """
    Active le 'Best Bet' pour un pari donné et le désactive pour tous les autres paris du même match.
    Met à jour à la fois le JSON (Frontend) et la DB (Analytics).
    """
    # 1. MISE A JOUR DU JSON (Pour DailyBets)
    json_path = "/app/data/daily/frontend_predictions.json"
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as f:
                bets = json.load(f)
            
            # On parcourt pour trouver le match et basculer le flag
            for bet in bets:
                # On identifie le match par Date + Home + Away
                if (bet.get('Date') == payload.match_date and 
                    bet.get('Home') == payload.home_team and 
                    bet.get('Away') == payload.away_team):
                    
                    # Si c'est le pari cliqué -> Devenir Best Bet
                    if (bet.get('Type_Pari') == payload.bet_type and 
                        float(bet.get('Ligne_Bookmaker')) == payload.line):
                        bet['is_best_bet'] = not bet.get('is_best_bet', False) # Toggle (ON/OFF)
                    else:
                        # Pour les autres paris du MEME match -> Force OFF (Un seul best bet par match)
                        bet['is_best_bet'] = False
            
            with open(json_path, 'w') as f:
                json.dump(bets, f, indent=4)
        except Exception as e:
            print(f"Erreur update JSON: {e}")

    # 2. MISE A JOUR DE LA DB (Pour Analytics)
    try:
        # On récupère tous les paris de ce match en DB
        db_bets = db.query(models.DailyPrediction).filter(
            models.DailyPrediction.match_date == payload.match_date,
            models.DailyPrediction.home_team == payload.home_team,
            models.DailyPrediction.away_team == payload.away_team
        ).all()

        for db_bet in db_bets:
            # Si c'est le pari cible
            if (db_bet.bet_type == payload.bet_type and 
                db_bet.fdj_line == payload.line):
                
                # Toggle : Si c'était déjà Best Bet, on le passe en Normal, sinon Best Bet
                if db_bet.recommendation == "Best Bet":
                    db_bet.recommendation = "Normal" # ou restaurer l'ancien statut si on l'avait stocké
                else:
                    db_bet.recommendation = "Best Bet"
            else:
                # Pour les autres : on retire le statut Best Bet s'ils l'avaient
                if db_bet.recommendation == "Best Bet":
                    db_bet.recommendation = "Normal"
        
        db.commit()
        return {"status": "success", "message": "Best bet updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
@router.put("/toggle_ignore/{prediction_id}")
def toggle_prediction_ignore(prediction_id: int, db: Session = Depends(get_db)):
    """Active ou désactive le statut 'Ignoré' d'un pari."""
    pred = db.query(models.DailyPrediction).filter(models.DailyPrediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    
    # On inverse la valeur actuelle
    pred.is_ignored = not pred.is_ignored
    
    # Si on l'ignore, on retire aussi le statut Best Bet pour être cohérent
    if pred.is_ignored:
        pred.recommendation = "Normal"
        
    db.commit()
    return {"status": "success", "is_ignored": pred.is_ignored}
