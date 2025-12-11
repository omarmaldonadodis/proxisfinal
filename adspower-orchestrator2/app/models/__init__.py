# app/models/__init__.py
from app.models.computer import Computer, ComputerStatus
from app.models.computer_token import ComputerToken  # ✅ AGREGAR ESTA LÍNEA
from app.models.proxy import Proxy, ProxyType, ProxyStatus
from app.models.profile import Profile, ProfileStatus, DeviceType
from app.models.health_check import HealthCheck
from app.models.warming_script import (
    WarmingScript,
    WarmingExecution,
    AgentConnection,
    ActionType,
    ScriptStatus,
    ExecutionStatus,
)
from app.models.scheduled_warming import (
    ScheduledWarming,
    ScheduleFrequency,
    ScheduledWarmingStatus
)

from app.models.execution_event import (
    EventSeverityDB,
    ExecutionEventDB,
 )

__all__ = [
    "Computer",
    "ComputerStatus",
    "ComputerToken", 
    "Proxy",
    "ProxyType",
    "ProxyStatus",
    "Profile",
    "ProfileStatus",
    "DeviceType",
    "HealthCheck",
    "WarmingScript",
    "WarmingExecution",
    "AgentConnection",
    "ActionType",
    "ScriptStatus",
    "ExecutionStatus",
    "ScheduledWarming",
    "ScheduleFrequency",
    "ScheduledWarmingStatus",
    "EventSeverityDB",
    "ExecutionEventDB",
]