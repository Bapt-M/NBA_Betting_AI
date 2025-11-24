from fastapi import APIRouter, HTTPException
import schemas

# On importe les tâches Celery (Attention à l'import circulaire, on le fait souvent dans la fonction)
# Pour cet exemple, on suppose que celery_worker est accessible dans le PYTHONPATH

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.post("/trigger/{task_name}", response_model=schemas.TaskTriggerResponse)
def trigger_task(task_name: str):
    """
    Lance manuellement une tâche de fond (Scraping, Entrainement...).
    """
    # Import dynamique pour éviter que main.py ne charge tout Celery au démarrage
    from celery_worker import run_morning_pipeline, run_afternoon_pipeline
    
    task = None
    if task_name == "morning_update":
        task = run_morning_pipeline.delay()
    elif task_name == "afternoon_predictions":
        task = run_afternoon_pipeline.delay()
    else:
        raise HTTPException(status_code=404, detail=f"Tâche '{task_name}' inconnue.")
    
    return {
        "status": "started", 
        "task_id": task.id,
        "message": f"Tâche {task_name} lancée en arrière-plan."
    }