import sys
import os
from sqlalchemy import text
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.database import SessionLocal

def add_column():
    print("--- Migration DB : Ajout de 'is_ignored' ---")
    db = SessionLocal()
    try:
        # On ajoute la colonne si elle n'existe pas
        db.execute(text("ALTER TABLE daily_predictions ADD COLUMN IF NOT EXISTS is_ignored BOOLEAN DEFAULT FALSE;"))
        db.commit()
        print("✅ Colonne 'is_ignored' ajoutée avec succès.")
    except Exception as e:
        print(f"⚠️ Note : {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_column()