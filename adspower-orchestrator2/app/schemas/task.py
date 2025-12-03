# app/schemas/task.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.task import TaskType, TaskStatus

class TaskBase(BaseModel):
    task_type: TaskType
    input_data: Dict[str, Any] = Field(default_factory=dict)

class TaskCreate(TaskBase):
    profile_id: Optional[int] = None
    computer_id: Optional[int] = None

class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class TaskResponse(TaskBase):
    id: int
    celery_task_id: Optional[str]
    profile_id: Optional[int]
    computer_id: Optional[int]
    status: TaskStatus
    progress: int
    result_data: Dict[str, Any]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    retry_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class TaskListResponse(BaseModel):
    total: int
    items: list[TaskResponse]