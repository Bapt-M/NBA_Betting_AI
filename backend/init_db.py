# backend/init_db.py
import pandas as pd
import os
import sys
from database import SessionLocal, engine
from models import Base, MatchResult

# Création des tables
Base.metadata.create_all(bind=engine)

def init_historical_data():
    print("--- Initialisation Historique DB ---")
    csv_path = "../data/processed/nba_data_train.csv"
    
    if not os.path.exists(csv_path):
        print("CSV introuvable. Lancez data_processor.py d'abord.")
        return

    df = pd.read_csv(csv_path)
    db = SessionLocal()
    
    # On prend les 500 derniers matchs pour avoir de la donnée
    subset = df.tail(500)
    count = 0
    
    for _, row in subset.iterrows():
        try:
            game_date = pd.to_datetime(row['GAME_DATE']).date()
            match_id = f"{game_date.strftime('%Y%m%d')}-{row['TEAM_ABBREVIATION_Home']}-{row['TEAM_ABBREVIATION_Away']}"
            
            exists = db.query(MatchResult).filter(MatchResult.match_id_nba == match_id).first()
            if not exists:
                match = MatchResult(
                    match_id_nba=match_id,
                    date=game_date,
                    home_team=row['TEAM_ABBREVIATION_Home'],
                    away_team=row['TEAM_ABBREVIATION_Away'],
                    actual_total=float(row['TARGET_Total_Pts'])
                )
                db.add(match)
                count += 1
        except Exception:
            continue
            
    db.commit()
    db.close()
    print(f"✅ {count} matchs importés en base.")

if __name__ == "__main__":
    init_historical_data()