# app/models/task.py
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class TaskType(str, enum.Enum):
    CREATE_PROFILE = "create_profile"
    WARMUP_PROFILE = "warmup_profile"
    PARALLEL_SEARCH = "parallel_search"
    PARALLEL_NAVIGATION = "parallel_navigation"
    BULK_CREATE = "bulk_create"
    HEALTH_CHECK = "health_check"
    BACKUP = "backup"

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Task info
    task_type = Column(SQLEnum(TaskType), nullable=False, index=True)
    celery_task_id = Column(String(255), unique=True, index=True)
    
    # Assignment
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=True, index=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=True, index=True)
    
    # Status
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, index=True)
    progress = Column(Integer, default=0)  # 0-100
    
    # Input/Output
    input_data = Column(JSON, default=dict)
    result_data = Column(JSON, default=dict)
    error_message = Column(Text)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    profile = relationship("Profile", back_populates="tasks")
    
    def __repr__(self):
        return f"<Task(type={self.task_type}, status={self.status})>"