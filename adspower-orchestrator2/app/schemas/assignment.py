# app/schemas/assignment.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProfileAssignmentCreate(BaseModel):
    profile_id: int = Field(..., ge=1)
    agent_id: int = Field(..., ge=1)
    target_url: str = Field(default="https://www.google.com")
    assignment_name: Optional[str] = None
    requires_auth: bool = False
    notes: Optional[str] = None


class ProfileAssignmentUpdate(BaseModel):
    target_url: Optional[str] = None
    assignment_name: Optional[str] = None
    is_active: Optional[bool] = None
    requires_auth: Optional[bool] = None
    notes: Optional[str] = None


class ProfileAssignmentResponse(BaseModel):
    id: int
    profile_id: int
    agent_id: int
    agent_name: Optional[str] = None   # del join
    profile_name: Optional[str] = None  # del join
    target_url: str
    assignment_name: Optional[str]
    is_active: bool
    requires_auth: bool
    notes: Optional[str]
    created_at: datetime

    # Resumen de sesiones
    total_sessions: Optional[int] = 0
    last_session_at: Optional[datetime] = None
    has_active_session: Optional[bool] = False

    class Config:
        from_attributes = True


class ProfileAssignmentListResponse(BaseModel):
    total: int
    items: List[ProfileAssignmentResponse]