from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routers import predictions, results, analytics, tasks

# Création automatique des tables (pour le dev)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NBA Betting AI Dashboard", version="1.0.0")

# Configuration CORS (pour autoriser le frontend React)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # URL du frontend React par défaut
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enregistrement des routeurs
app.include_router(predictions.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "online", "message": "NBA Betting AI Backend Running"}