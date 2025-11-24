from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# CORRECTION : Imports absolus (backend.xxx)
from backend import models
from backend.database import engine
from backend.routers import predictions, results, analytics, tasks, system

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NBA Betting AI Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(system.router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "online", "message": "NBA Betting AI Backend Running"}