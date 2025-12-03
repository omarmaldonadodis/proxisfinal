# app/schemas/computer.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.computer import ComputerStatus

class ComputerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    hostname: str
    ip_address: str
    adspower_api_url: str
    adspower_api_key: str
    max_profiles: int = Field(default=50, ge=1, le=1000)
    cpu_cores: Optional[int] = None
    ram_gb: Optional[int] = None
    os_info: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    meta_data: Dict[str, Any] = Field(default_factory=dict)

class ComputerCreate(ComputerBase):
    pass

class ComputerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    adspower_api_url: Optional[str] = None
    adspower_api_key: Optional[str] = None
    status: Optional[ComputerStatus] = None
    is_active: Optional[bool] = None
    max_profiles: Optional[int] = None
    cpu_cores: Optional[int] = None
    ram_gb: Optional[int] = None
    os_info: Optional[str] = None
    tags: Optional[List[str]] = None
    meta_data: Optional[dict] = None

class ComputerResponse(ComputerBase):
    id: int
    status: ComputerStatus
    is_active: bool
    current_profiles: int
    created_at: datetime
    updated_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class ComputerListResponse(BaseModel):
    total: int
    items: List[ComputerResponse]