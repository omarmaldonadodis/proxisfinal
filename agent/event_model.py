# agent/event_model.py
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from event_types import EventType, EventSeverity


class ExecutionEvent(BaseModel):
    """Evento de ejecución estructurado"""
    
    # Identificación
    event_id: str                       # UUID único
    event_type: EventType
    severity: EventSeverity
    
    # Contexto de ejecución
    execution_id: int
    computer_id: int
    profile_id: str
    action_index: Optional[int] = None
    action_type: Optional[str] = None
    
    # Detalles del evento
    message: str                        # Mensaje legible
    details: Dict[str, Any]             # Datos técnicos
    
    # Estado actual
    current_url: Optional[str] = None
    page_title: Optional[str] = None
    screenshot_path: Optional[str] = None
    
    # Timestamps
    timestamp: datetime
    
    # Indicadores
    requires_manual_intervention: bool = False
    can_retry: bool = True
    retry_count: int = 0
    
    # Sugerencias de acción
    suggested_action: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }