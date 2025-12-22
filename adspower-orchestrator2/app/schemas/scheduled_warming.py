# adspower-orchestrator2/app/schemas/scheduled_warming.py
"""
Schemas para warming programado
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from datetime import datetime


class ScheduledWarmingCreate(BaseModel):
    """Schema para crear warming programado"""
    
    script_id: int = Field(..., description="ID del script a ejecutar")
    profile_ids: List[int] = Field(..., min_items=1, description="IDs de profiles")
    
    # Frecuencia de ejecución
    frequency: str = Field(
        ...,
        description="once | daily | weekly | monthly | custom",
        pattern="^(once|daily|weekly|monthly|custom)$"
    )
    
    # Fecha/hora de primera ejecución (UTC)
    scheduled_at: datetime = Field(..., description="Primera ejecución (UTC)")
    
    # Para frecuencia custom
    cron_expression: Optional[str] = Field(None, description="Expresión cron (ej: '0 14 * * *')")
    
    # Timezone del usuario
    timezone: str = Field(default="UTC", description="Timezone (ej: America/Guayaquil)")
    
    # Para frecuencia weekly
    days_of_week: Optional[List[int]] = Field(
        None,
        description="Días de la semana [0=Lunes, 6=Domingo]"
    )
    
    # Hora del día (para daily/weekly)
    time_of_day: Optional[str] = Field(
        None,
        description="Hora del día (HH:MM, ej: '14:30')",
        pattern="^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
    )
    
    # Límites
    max_executions: Optional[int] = Field(
        None,
        description="Máximo de ejecuciones (None = infinito)"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Fecha de expiración (UTC)"
    )
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(None, max_length=500)


class ScheduledWarmingUpdate(BaseModel):
    """Schema para actualizar warming programado"""
    
    is_active: Optional[bool] = None
    max_executions: Optional[int] = None
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class ScheduledWarmingResponse(BaseModel):
    """Schema de respuesta de warming programado"""
    
    id: int
    script_id: int
    profile_ids: List[int]
    frequency: str
    scheduled_at: datetime
    next_execution_at: Optional[datetime]
    last_execution_at: Optional[datetime]
    
    cron_expression: Optional[str]
    timezone: str
    days_of_week: Optional[List[int]]
    time_of_day: Optional[str]
    
    status: str
    is_active: bool
    
    execution_count: int
    success_count: int
    failure_count: int
    
    max_executions: Optional[int]
    expires_at: Optional[datetime]
    
    tags: List[str]
    notes: Optional[str]
    
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)
