# app/schemas/agent.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.agent_session import SessionStatus, BrowserEventType


# ========================================
# AGENT TOKEN
# ========================================

class AgentTokenCreate(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None


class AgentTokenResponse(BaseModel):
    id: int
    agent_name: str
    token: str
    is_active: bool
    notes: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


# ========================================
# SESSIONS
# ========================================

class OpenBrowserRequest(BaseModel):
    """El agente manda esto cuando hace click en 'Abrir navegador'"""
    assignment_id: int
    computer_id: int  # en qué máquina abrir (detectado automáticamente por el ejecutable)


class SessionResponse(BaseModel):
    id: int
    assignment_id: int
    profile_id: int
    agent_name: str
    target_url: Optional[str]
    adspower_profile_id: Optional[str]
    status: SessionStatus
    requested_at: datetime
    opened_at: Optional[datetime]
    closed_at: Optional[datetime]
    duration_seconds: Optional[int]
    data_sent_mb: float
    data_received_mb: float
    total_data_mb: float
    pages_visited: int
    last_url: Optional[str]
    browser_health: Optional[str]
    computer_id: Optional[int]

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    total: int
    items: List[SessionResponse]


class SessionCloseRequest(BaseModel):
    """El ejecutable manda esto al cerrar el navegador"""
    data_sent_mb: float = 0.0
    data_received_mb: float = 0.0
    pages_visited: int = 0
    browser_pid: Optional[int] = None
    crash_reason: Optional[str] = None


class SessionMetricsUpdate(BaseModel):
    """Actualización de métricas en tiempo real desde el ejecutable"""
    session_id: int
    data_sent_mb: float
    data_received_mb: float
    pages_visited: int
    current_url: Optional[str] = None
    browser_health: Optional[str] = "healthy"
    cpu_percent: Optional[float] = None
    ram_mb: Optional[float] = None


# ========================================
# BROWSER EVENTS
# ========================================

class BrowserEventCreate(BaseModel):
    event_type: BrowserEventType
    url: Optional[str] = None
    page_title: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class BrowserEventResponse(BaseModel):
    id: int
    session_id: int
    event_type: BrowserEventType
    url: Optional[str]
    page_title: Optional[str]
    timestamp: datetime
    extra_data: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True


# ========================================
# WEBSOCKET MESSAGES (agente → servidor)
# ========================================

class AgentMetricsPayload(BaseModel):
    """Lo que el ejecutable envía cada 10 segundos"""
    computer_id: int
    active_browsers: List[Dict[str, Any]] = []
    network: Dict[str, Any] = {}
    adspower_cpu_percent: float = 0.0
    adspower_ram_mb: float = 0.0
    active_sessions: List[int] = []  # IDs de sesiones activas


class AgentRegisterRequest(BaseModel):
    """El ejecutable se registra en el servidor"""
    name: str
    hostname: str
    ip_address: str
    adspower_api_url: str
    adspower_api_key: str
    os_info: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_gb: Optional[int] = None