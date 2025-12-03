# app/services/task_service.py
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.task_repository import TaskRepository
from app.models.task import Task, TaskStatus, TaskType
from app.schemas.task import TaskCreate, TaskUpdate
from loguru import logger

class TaskService:
    """Servicio para gestión de Tasks"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TaskRepository(db)
    
    async def create_task(self, task_in: TaskCreate, celery_task_id: str) -> Task:
        """Crea una nueva task"""
        task_data = task_in.model_dump()
        task_data['celery_task_id'] = celery_task_id
        task_data['status'] = TaskStatus.PENDING
        
        task = await self.repo.create(task_data)
        await self.db.commit()
        
        logger.info(f"Task created: {task.id} (Celery: {celery_task_id})")
        return task
    
    async def get_task(self, task_id: int) -> Optional[Task]:
        """Obtiene task por ID"""
        return await self.repo.get(task_id)
    
    async def get_task_by_celery_id(self, celery_task_id: str) -> Optional[Task]:
        """Obtiene task por Celery ID"""
        return await self.repo.get_by_celery_id(celery_task_id)
    
    async def list_tasks(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None
    ) -> tuple[List[Task], int]:
        """Lista tasks con filtros"""
        filters = {}
        if status:
            filters['status'] = status
        if task_type:
            filters['task_type'] = task_type
        
        tasks = await self.repo.get_multi(skip=skip, limit=limit, filters=filters, order_by='-created_at')
        total = await self.repo.count(filters=filters)
        
        return tasks, total
    
    async def update_task(self, task_id: int, task_in: TaskUpdate) -> Optional[Task]:
        """Actualiza task"""
        task = await self.repo.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        update_data = task_in.model_dump(exclude_unset=True)
        task = await self.repo.update(task_id, update_data)
        await self.db.commit()
        
        return task
    
    async def cancel_task(self, task_id: int) -> bool:
        """Cancela una task"""
        task = await self.repo.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise ValueError(f"Task cannot be cancelled (status: {task.status})")
        
        # Intentar cancelar en Celery
        from celery.result import AsyncResult
        celery_task = AsyncResult(task.celery_task_id)
        celery_task.revoke(terminate=True)
        
        # Actualizar status en DB
        await self.repo.update(task_id, {'status': TaskStatus.CANCELLED})
        await self.db.commit()
        
        logger.info(f"Task cancelled: {task_id}")
        return True
    
    async def get_stats(self) -> Dict:
        """Obtiene estadísticas de tasks"""
        return await self.repo.get_stats()