# app/schemas/proxy.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.proxy import ProxyType, ProxyStatus

class ProxyBase(BaseModel):
    proxy_type: ProxyType
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    region: Optional[str] = None
    city: Optional[str] = None
    session_lifetime: int = Field(default=3600, ge=60, le=86400)
    sticky_session: bool = True
    tags: List[str] = Field(default_factory=list)
    meta_data: Dict[str, Any] = Field(default_factory=dict)

class ProxyCreate(ProxyBase):
    pass

class ProxyUpdate(BaseModel):
    proxy_type: Optional[ProxyType] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    status: Optional[ProxyStatus] = None
    is_available: Optional[bool] = None
    tags: Optional[List[str]] = None
    meta_data: Optional[Dict[str, Any]] = None

class ProxyResponse(ProxyBase):
    id: int
    session_id: Optional[str]
    status: ProxyStatus
    is_available: bool
    last_check_at: Optional[datetime]
    success_rate: float
    avg_response_time: Optional[float]
    detected_ip: Optional[str]
    detected_country: Optional[str]
    detected_city: Optional[str]
    profiles_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProxyListResponse(BaseModel):
    total: int
    items: List[ProxyResponse]

class ProxyTestResponse(BaseModel):
    success: bool
    ip: Optional[str]
    country: Optional[str]
    city: Optional[str]
    isp: Optional[str]
    response_time_ms: Optional[float]
    error: Optional[str]