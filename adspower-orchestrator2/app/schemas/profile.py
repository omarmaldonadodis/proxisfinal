# app/schemas/profile.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.profile import ProfileStatus, DeviceType

class ProfileBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    age: Optional[int] = Field(None, ge=18, le=100)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    city: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    device_type: DeviceType = DeviceType.DESKTOP
    device_name: Optional[str] = None
    interests: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    meta_data: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

class ProfileCreate(ProfileBase):
    computer_id: int = Field(..., ge=1)
    proxy_id: Optional[int] = None
    proxy_type: Optional[str] = Field(None, pattern="^(mobile|residential)$")
    proxy_country: Optional[str] = None
    proxy_city: Optional[str] = None
    auto_warmup: bool = False
    warmup_duration_minutes: int = Field(default=20, ge=5, le=120)

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    computer_id: Optional[int] = None
    proxy_id: Optional[int] = None
    status: Optional[ProfileStatus] = None
    tags: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class ProfileResponse(ProfileBase):
    id: int
    adspower_id: str
    computer_id: int
    proxy_id: Optional[int]
    status: ProfileStatus
    is_warmed: bool
    warmup_completed_at: Optional[datetime]
    last_opened_at: Optional[datetime]
    total_sessions: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Nested relationships (opcional)
    computer_name: Optional[str] = None
    proxy_info: Optional[str] = None
    
    class Config:
        from_attributes = True

class ProfileListResponse(BaseModel):
    total: int
    items: List[ProfileResponse]

class ProfileBulkCreate(BaseModel):
    count: int = Field(..., ge=1, le=100)
    computer_id: int
    proxy_type: str = Field(..., pattern="^(mobile|residential)$")
    country: str = Field(default="ec", min_length=2, max_length=2)
    city: Optional[str] = None
    device_type: DeviceType = DeviceType.MOBILE
    auto_warmup: bool = False
    warmup_duration_minutes: int = Field(default=15, ge=5, le=60)
    tags: List[str] = Field(default_factory=list)