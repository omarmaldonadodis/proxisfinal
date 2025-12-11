# adspower-orchestrator2/app/models/execution_event.py (NUEVO)
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database import Base
import enum

class EventSeverityDB(str, enum.Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"

class ExecutionEventDB(Base):
    """Eventos de ejecución (para troubleshooting)"""
    __tablename__ = "execution_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Contexto
    execution_id = Column(Integer, ForeignKey("warming_executions.id"), nullable=False, index=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, index=True)
    
    # Evento
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(SQLEnum(EventSeverityDB), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, default=dict)
    
    # Estado
    current_url = Column(Text)
    page_title = Column(String(500))
    screenshot_path = Column(String(500))
    
    # Flags
    requires_manual_intervention = Column(Boolean, default=False, index=True)
    can_retry = Column(Boolean, default=True)
    retry_count = Column(Integer, default=0)
    
    # Sugerencias
    suggested_action = Column(Text)
    
    # Acción relacionada
    action_index = Column(Integer)
    action_type = Column(String(100))
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)