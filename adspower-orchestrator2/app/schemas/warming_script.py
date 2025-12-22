# app/schemas/warming_script.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    WAIT_ELEMENT = "wait_element"
    HOVER = "hover"
    SELECT = "select"
    PRESS_KEY = "press_key"
    SCREENSHOT = "screenshot"
    SWITCH_TAB = "switch_tab"
    CLOSE_TAB = "close_tab"
    EXECUTE_SCRIPT = "execute_script"
    RANDOM_MOUSE = "random_mouse"
    HUMAN_TYPING = "human_typing"
    SEARCH_GOOGLE = "search_google"
    LOGIN = "login"
    ADVANCED_LOGIN = "advanced_login"

# adspower-orchestrator2/app/schemas/warming_script.py (ACTUALIZACIÓN)


class ActionParams(BaseModel):
    """Parámetros de una acción"""
    
    class Config:
        extra = "allow"  # Permite cualquier parámetro adicional


class WarmingAction(BaseModel):
    """Acción de warming"""
    
    type: str = Field(..., description="Tipo de acción (navigate, click, type, etc)")
    params: ActionParams = Field(default_factory=dict, description="Parámetros de la acción")
    description: Optional[str] = Field(None, description="Descripción de la acción")


class WarmingScriptCreate(BaseModel):
    """Schema para crear warming script"""
    
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    actions: List[WarmingAction] = Field(..., min_items=1)
    duration_minutes: int = Field(default=15, ge=1, le=180)
    randomize_order: bool = False
    repeat_count: int = Field(default=1, ge=1, le=10)
    tags: List[str] = Field(default_factory=list)
    is_template: bool = False


class WarmingScriptUpdate(BaseModel):
    """Schema para actualizar warming script"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    actions: Optional[List[WarmingAction]] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=180)
    randomize_order: Optional[bool] = None
    repeat_count: Optional[int] = Field(None, ge=1, le=10)
    tags: Optional[List[str]] = None
    status: Optional[str] = None


class WarmingScriptResponse(BaseModel):
    """Schema de respuesta de warming script"""
    
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    actions: List[Dict[str, Any]]
    duration_minutes: int
    randomize_order: bool
    repeat_count: int
    status: str
    is_template: bool
    tags: List[str]
    success_rate: int
    times_used: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class BatchWarmingRequest(BaseModel):
    """
    ✅ SIMPLIFICADO: Solo script_id y profile_ids
    
    El sistema asigna automáticamente:
    - Computadoras según disponibilidad
    - Concurrencia sin límites artificiales
    """
    
    script_id: int = Field(..., description="ID del script de warming")
    profile_ids: List[int] = Field(..., min_items=1, description="IDs de profiles a ejecutar")


class BatchWarmingResponse(BaseModel):
    """Respuesta de batch warming"""
    
    task_id: str = Field(..., description="ID del batch (UUID)")
    total_profiles: int
    message: str
    executions: List[int]


class WarmingExecutionResponse(BaseModel):
    """Schema de respuesta de ejecución"""
    
    id: int
    script_id: int
    profile_id: int
    computer_id: int
    status: str
    progress: int
    actions_completed: int
    actions_failed: int
    execution_log: List[Dict[str, Any]]
    error_message: Optional[str]
    screenshots: List[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True