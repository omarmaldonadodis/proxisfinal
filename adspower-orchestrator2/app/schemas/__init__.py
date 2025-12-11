# app/schemas/__init__.py
from app.schemas.computer import (
    ComputerCreate,
    ComputerUpdate,
    ComputerResponse,
    ComputerListResponse
)
from app.schemas.proxy import (
    ProxyCreate,
    ProxyUpdate,
    ProxyResponse,
    ProxyListResponse,
    ProxyTestResponse
)
from app.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
    ProfileListResponse,
    ProfileBulkCreate
)

from app.schemas.warming_script import (
    ActionType,
    ScriptAction,
    WarmingScriptCreate,
    WarmingScriptUpdate,
    WarmingScriptResponse,
    WarmingExecutionCreate,
    WarmingExecutionResponse,
    BatchWarmingRequest,
    BatchWarmingResponse
)

__all__ = [
    "ComputerCreate",
    "ComputerUpdate",
    "ComputerResponse",
    "ComputerListResponse",
    "ProxyCreate",
    "ProxyUpdate",
    "ProxyResponse",
    "ProxyListResponse",
    "ProxyTestResponse",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    "ProfileListResponse",
    "ProfileBulkCreate",
    "ParallelSearchRequest",
    "ParallelNavigationRequest",
    "AutomationResponse",
    "AutomationResult",
    "ActionType",
    "ScriptAction",
    "WarmingScriptCreate",
    "WarmingScriptUpdate",
    "WarmingScriptResponse",
    "WarmingExecutionCreate",
    "WarmingExecutionResponse",
    "BatchWarmingRequest",
    "BatchWarmingResponse",
]