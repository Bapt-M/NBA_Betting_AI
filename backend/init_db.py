import pandas as pd
import os
import sys
from sqlalchemy import text
# Assurez-vous que l'import fonctionne dans votre env Docker
from database import SessionLocal, engine
from models import Base, MatchResult
from config import settings

def init_historical_data():
    print("--- Initialisation Historique DB (Nettoyage) ---")
    
    csv_path = settings.DATA_PROCESSED
    if not os.path.exists(csv_path):
        print(f"❌ Fichier introuvable : {csv_path}")
        return

    df = pd.read_csv(csv_path)
    # TRI CRITIQUE : On veut les matchs les plus récents à la fin pour le .tail()
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df.sort_values('GAME_DATE', inplace=True)
    
    db = SessionLocal()
    
    try:
        # 1. VIDER LA TABLE (Pour supprimer les doublons erronés)
        print("Nettoyage de la table match_results...")
        db.execute(text("TRUNCATE TABLE match_results RESTART IDENTITY;"))
        db.commit()
        
        # 2. IMPORTER
        print(f"Importation de {len(df)} matchs...")
        # On importe tout l'historique (ou ajustez .tail(1000))
        # Pour éviter de saturer, on peut prendre les 2 dernières saisons (~2500 matchs)
        subset = df.tail(2500)
        
        for _, row in subset.iterrows():
            try:
                match_id = f"{row['GAME_DATE'].date().strftime('%Y%m%d')}-{row['TEAM_ABBREVIATION_Home']}-{row['TEAM_ABBREVIATION_Away']}"
                
                match = MatchResult(
                    match_id_nba=match_id,
                    date=row['GAME_DATE'],
                    home_team=row['TEAM_ABBREVIATION_Home'],
                    away_team=row['TEAM_ABBREVIATION_Away'],
                    actual_total=float(row['TARGET_Total_Pts'])
                )
                db.add(match)
            except: continue
            
        db.commit()
        print(f"✅ Succès : {len(subset)} matchs importés.")
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_historical_data()