# app/api/v1/automation.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.automation_service import AutomationService
from app.schemas.automation import (
    ParallelSearchRequest,
    ParallelNavigationRequest,
    AutomationResponse,
    AutomationType
)
from loguru import logger

router = APIRouter(prefix="/automation", tags=["Automation"])

@router.post("/parallel-search", response_model=AutomationResponse, status_code=202)
async def parallel_search(
    request: ParallelSearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Ejecuta búsqueda paralela sincronizada"""
    from app.tasks.automation_tasks import parallel_search_task
    
    # Lanzar tarea
    task = parallel_search_task.delay(
        request.profile_ids,
        request.search_query,
        request.max_parallel
    )
    
    return AutomationResponse(
        task_id=task.id,
        automation_type=AutomationType.PARALLEL_SEARCH,
        profiles_count=len(request.profile_ids),
        message=f"Parallel search started for {len(request.profile_ids)} profiles"
    )

@router.post("/parallel-navigation", response_model=AutomationResponse, status_code=202)
async def parallel_navigation(
    request: ParallelNavigationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Ejecuta navegación paralela"""
    from app.tasks.automation_tasks import parallel_navigation_task
    
    # Lanzar tarea
    task = parallel_navigation_task.delay(
        request.profile_ids,
        request.urls,
        request.stay_duration_min,
        request.stay_duration_max,
        request.max_parallel,
        request.randomize_order
    )
    
    return AutomationResponse(
        task_id=task.id,
        automation_type=AutomationType.PARALLEL_NAVIGATION,
        profiles_count=len(request.profile_ids),
        message=f"Parallel navigation started for {len(request.profile_ids)} profiles"
    )

@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estado de una tarea de automatización"""
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id)
    
    response = {
        'task_id': task_id,
        'status': task.state,
        'result': None,
        'error': None
    }
    
    if task.state == 'SUCCESS':
        response['result'] = task.result
    elif task.state == 'FAILURE':
        response['error'] = str(task.info)
    elif task.state == 'PENDING':
        response['message'] = 'Task is waiting to be executed'
    elif task.state == 'STARTED':
        response['message'] = 'Task is currently running'
    
    return response