import pandas as pd
import os
import sys
from database import SessionLocal, engine
from models import Base, MatchResult

# Création des tables
Base.metadata.create_all(bind=engine)

def init_historical_data():
    print("--- Initialisation Historique DB ---")
    
    # DÉTECTION INTELLIGENTE DU CHEMIN
    # Si on est dans Docker (/app existe), le chemin est /app/data...
    # Sinon (local), on remonte d'un cran depuis le dossier du script.
    if os.path.exists("/app"):
        BASE_DIR = "/app"
    else:
        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        
    csv_path = os.path.join(BASE_DIR, "data/processed/nba_data_train.csv")
    print(f"Recherche du fichier : {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"❌ ERREUR : Fichier introuvable : {csv_path}")
        print("Assurez-vous d'avoir lancé 'python src/data_processor.py' en local avant de lancer Docker,")
        print("ou que le volume docker est bien monté.")
        return

    df = pd.read_csv(csv_path)
    db = SessionLocal()
    
    print(f"Fichier trouvé. Importation de {len(df)} lignes...")
    
    count = 0
    # On importe tout ou une partie
    for _, row in df.iterrows():
        try:
            game_date = pd.to_datetime(row['GAME_DATE']).date()
            # ID unique : DATE-HOME-AWAY
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
    print(f"✅ Succès : {count} nouveaux matchs importés en base.")

if __name__ == "__main__":
    init_historical_data()