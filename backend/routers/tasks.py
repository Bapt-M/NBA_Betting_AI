from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
# CORRECTION : Import absolu
from backend import schemas

router = APIRouter(prefix="/tasks", tags=["Tasks"])

class TaskResponse(BaseModel):
    task_id: str
    status: str

@router.post("/trigger/{action}", response_model=TaskResponse)
def trigger_pipeline(action: str):
    # CORRECTION : Import depuis backend.celery_worker
    from backend.celery_worker import (
        task_fetch_data, task_process_data, task_train_model,
        task_scrape_odds, task_predict_daily, task_update_history,
        full_morning_pipeline, full_afternoon_pipeline
    )
    
    task_map = {
        "fetch_data": task_fetch_data,
        "process_data": task_process_data,
        "train_model": task_train_model,
        "scrape_odds": task_scrape_odds,
        "predict_daily": task_predict_daily,
        "update_history": task_update_history,
        "full_morning": full_morning_pipeline,
        "full_afternoon": full_afternoon_pipeline
    }
    
    if action not in task_map:
        raise HTTPException(status_code=404, detail="Action inconnue")
        
    task = task_map[action].delay()
    
    return {"task_id": task.id, "status": "started"}