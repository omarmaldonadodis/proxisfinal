# app/schemas/automation.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class AutomationType(str, Enum):
    PARALLEL_SEARCH = "parallel_search"
    PARALLEL_NAVIGATION = "parallel_navigation"
    CUSTOM_SCRIPT = "custom_script"

class ParallelSearchRequest(BaseModel):
    profile_ids: List[int] = Field(..., min_items=1, max_items=50)
    search_query: str = Field(..., min_length=1, max_length=500)
    max_parallel: int = Field(default=5, ge=1, le=10)
    
class ParallelNavigationRequest(BaseModel):
    profile_ids: List[int] = Field(..., min_items=1, max_items=50)
    urls: List[str] = Field(..., min_items=1, max_items=100)
    stay_duration_min: int = Field(default=10, ge=5, le=300)
    stay_duration_max: int = Field(default=30, ge=10, le=600)
    max_parallel: int = Field(default=5, ge=1, le=10)
    randomize_order: bool = True

class AutomationResponse(BaseModel):
    task_id: str
    automation_type: AutomationType
    profiles_count: int
    message: str

class AutomationResultDetail(BaseModel):
    profile_id: int
    profile_name: str
    success: bool
    duration_seconds: Optional[float]
    error: Optional[str]

class AutomationResult(BaseModel):
    task_id: str
    status: str
    total: int
    successful: int
    failed: int
    results: List[AutomationResultDetail]
    total_duration_seconds: Optional[float]