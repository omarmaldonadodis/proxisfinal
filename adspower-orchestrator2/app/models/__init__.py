# app/models/__init__.py  ← REEMPLAZAR COMPLETO
from app.models.computer import Computer, ComputerStatus
from app.models.computer_token import ComputerToken
from app.models.proxy import Proxy, ProxyType, ProxyStatus
from app.models.profile import Profile, ProfileStatus, DeviceType
from app.models.health_check import HealthCheck
from app.models.proxy_health import ProxyHealthCheck, ProxyScore
from app.models.profile_metrics import ProfileMetrics, ProxyUsageStats
from app.models.profile_assignment import AgentToken, ProfileAssignment
from app.models.agent_session import AgentSession, BrowserEvent, SessionStatus, BrowserEventType
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger

__all__ = [
    "Computer", "ComputerStatus",
    "ComputerToken",
    "Proxy", "ProxyType", "ProxyStatus",
    "Profile", "ProfileStatus", "DeviceType",
    "HealthCheck",
    "ProxyHealthCheck", "ProxyScore",
    "ProfileMetrics", "ProxyUsageStats",
    "AgentToken", "ProfileAssignment",
    "AgentSession", "BrowserEvent", "SessionStatus", "BrowserEventType",
    "Alert", "AlertSeverity", "AlertStatus",
    "ProxyRotationLog", "RotationTrigger",
]