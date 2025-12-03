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

class ScriptAction(BaseModel):
    """Acción individual de un script"""
    type: ActionType
    params: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "navigate",
                    "params": {"url": "https://google.com"},
                    "description": "Navegar a Google"
                },
                {
                    "type": "type",
                    "params": {
                        "selector": "input[name='q']",
                        "text": "test query",
                        "human": True,
                        "speed": "medium"
                    },
                    "description": "Escribir en buscador"
                },
                {
                    "type": "click",
                    "params": {"selector": "button[type='submit']"},
                    "description": "Hacer click en botón"
                }
            ]
        }

class WarmingScriptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    actions: List[ScriptAction]
    duration_minutes: int = Field(default=15, ge=1, le=120)
    randomize_order: bool = False
    repeat_count: int = Field(default=1, ge=1, le=10)
    tags: List[str] = Field(default_factory=list)
    is_template: bool = False

class WarmingScriptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    actions: Optional[List[ScriptAction]] = None
    duration_minutes: Optional[int] = None
    randomize_order: Optional[bool] = None
    repeat_count: Optional[int] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

class WarmingScriptResponse(BaseModel):
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

class WarmingExecutionCreate(BaseModel):
    script_id: int
    profile_ids: List[int] = Field(..., min_items=1, max_items=50)
    computer_id: Optional[int] = None  # Si es None, auto-asignar

class WarmingExecutionResponse(BaseModel):
    id: int
    script_id: int
    profile_id: int
    computer_id: int
    status: str
    progress: int
    actions_completed: int
    actions_failed: int
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True

class BatchWarmingRequest(BaseModel):
    """Ejecutar warming en múltiples profiles"""
    script_id: int
    profile_ids: List[int] = Field(..., min_items=1, max_items=100)
    max_parallel: int = Field(default=5, ge=1, le=20)
    computer_ids: Optional[List[int]] = None  # Computers específicas

class BatchWarmingResponse(BaseModel):
    task_id: str
    total_profiles: int
    message: str
    executions: List[int]  # IDs de ejecuciones creadas