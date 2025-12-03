# app/api/v1/tasks.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.services.task_service import TaskService
from app.schemas.task import TaskResponse, TaskListResponse
from app.models.task import TaskStatus, TaskType

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[TaskStatus] = None,
    task_type: Optional[TaskType] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista tasks con filtros"""
    service = TaskService(db)
    tasks, total = await service.list_tasks(
        skip=skip,
        limit=limit,
        status=status,
        task_type=task_type
    )
    return TaskListResponse(total=total, items=tasks)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene task por ID"""
    service = TaskService(db)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/celery/{celery_task_id}", response_model=TaskResponse)
async def get_task_by_celery_id(
    celery_task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene task por Celery ID"""
    service = TaskService(db)
    task = await service.get_task_by_celery_id(celery_task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/{task_id}/cancel", status_code=200)
async def cancel_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Cancela una task"""
    service = TaskService(db)
    try:
        success = await service.cancel_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
        return {"message": "Task cancelled successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats/summary")
async def get_tasks_stats(
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas de tasks"""
    service = TaskService(db)
    stats = await service.get_stats()
    return stats