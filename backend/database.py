from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

# Création du moteur de base de données
engine = create_engine(settings.DATABASE_URL)

# Session locale pour les requêtes
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base pour les modèles ORM
Base = declarative_base()

# Dépendance pour FastAPI (injecte la session DB dans les routes)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()