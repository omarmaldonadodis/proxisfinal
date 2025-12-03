# app/repositories/task_repository.py
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.models.task import Task, TaskStatus, TaskType
from datetime import datetime

class TaskRepository(BaseRepository[Task]):
    """Repositorio para Tasks"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Task, db)
    
    async def get_by_celery_id(self, celery_task_id: str) -> Optional[Task]:
        """Obtiene task por celery_task_id"""
        result = await self.db.execute(
            select(Task).where(Task.celery_task_id == celery_task_id)
        )
        return result.scalar_one_or_none()
    
    async def get_pending(self, limit: int = 100) -> List[Task]:
        """Obtiene tasks pendientes"""
        result = await self.db.execute(
            select(Task)
            .where(Task.status == TaskStatus.PENDING)
            .order_by(Task.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_running(self) -> List[Task]:
        """Obtiene tasks en ejecución"""
        result = await self.db.execute(
            select(Task).where(Task.status == TaskStatus.RUNNING)
        )
        return list(result.scalars().all())
    
    async def update_progress(self, id: int, progress: int) -> bool:
        """Actualiza progreso"""
        return await self.update(id, {'progress': progress})
    
    async def mark_started(self, id: int) -> bool:
        """Marca task como iniciada"""
        return await self.update(id, {
            'status': TaskStatus.RUNNING,
            'started_at': datetime.utcnow()
        })
    
    async def mark_completed(self, id: int, result_data: dict) -> bool:
        """Marca task como completada"""
        task = await self.get(id)
        if not task:
            return False
        
        duration = None
        if task.started_at:
            duration = int((datetime.utcnow() - task.started_at).total_seconds())
        
        return await self.update(id, {
            'status': TaskStatus.COMPLETED,
            'progress': 100,
            'result_data': result_data,
            'completed_at': datetime.utcnow(),
            'duration_seconds': duration
        })
    
    async def mark_failed(self, id: int, error_message: str) -> bool:
        """Marca task como fallida"""
        task = await self.get(id)
        if not task:
            return False
        
        duration = None
        if task.started_at:
            duration = int((datetime.utcnow() - task.started_at).total_seconds())
        
        return await self.update(id, {
            'status': TaskStatus.FAILED,
            'error_message': error_message,
            'completed_at': datetime.utcnow(),
            'duration_seconds': duration
        })
    
    async def get_stats(self) -> dict:
        """Obtiene estadísticas de tasks"""
        result = await self.db.execute(
            select(
                func.count(Task.id).label('total'),
                func.count(Task.id).filter(Task.status == TaskStatus.PENDING).label('pending'),
                func.count(Task.id).filter(Task.status == TaskStatus.RUNNING).label('running'),
                func.count(Task.id).filter(Task.status == TaskStatus.COMPLETED).label('completed'),
                func.count(Task.id).filter(Task.status == TaskStatus.FAILED).label('failed')
            )
        )
        row = result.one()
        return {
            'total': row.total or 0,
            'pending': row.pending or 0,
            'running': row.running or 0,
            'completed': row.completed or 0,
            'failed': row.failed or 0
        }