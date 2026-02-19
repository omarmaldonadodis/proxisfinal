# app/schemas/__init__.py  ← REEMPLAZAR COMPLETO
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
from app.schemas.agent import (
    AgentTokenCreate,
    AgentTokenResponse,
    OpenBrowserRequest,
    SessionResponse,
    SessionListResponse,
    SessionCloseRequest,
    BrowserEventCreate,
    BrowserEventResponse,
    AgentRegisterRequest,
    SessionMetricsUpdate
)
from app.schemas.assignment import (
    ProfileAssignmentCreate,
    ProfileAssignmentUpdate,
    ProfileAssignmentResponse,
    ProfileAssignmentListResponse
)

__all__ = [
    "ComputerCreate", "ComputerUpdate", "ComputerResponse", "ComputerListResponse",
    "ProxyCreate", "ProxyUpdate", "ProxyResponse", "ProxyListResponse", "ProxyTestResponse",
    "ProfileCreate", "ProfileUpdate", "ProfileResponse", "ProfileListResponse", "ProfileBulkCreate",
    "AgentTokenCreate", "AgentTokenResponse", "OpenBrowserRequest",
    "SessionResponse", "SessionListResponse", "SessionCloseRequest",
    "BrowserEventCreate", "BrowserEventResponse", "AgentRegisterRequest", "SessionMetricsUpdate",
    "ProfileAssignmentCreate", "ProfileAssignmentUpdate",
    "ProfileAssignmentResponse", "ProfileAssignmentListResponse",
]