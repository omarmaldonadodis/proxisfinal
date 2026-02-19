# app/api/v1/profiles.py
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.services.profile_service import ProfileService
from app.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse,
    ProfileListResponse,
    ProfileBulkCreate
)
from app.models.profile import ProfileStatus

router = APIRouter(prefix="/profiles", tags=["Profiles"])

@router.post("/", response_model=ProfileResponse, status_code=201)
async def create_profile(
    profile_in: ProfileCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo profile"""
    service = ProfileService(db)
    try:
        profile = await service.create_profile(profile_in)
        return profile
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bulk", status_code=202)
async def bulk_create_profiles(
    bulk_in: ProfileBulkCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Crea múltiples profiles en background"""
    from app.tasks.profile_tasks import bulk_create_profiles_task
    
    # Lanzar tarea en Celery
    task = bulk_create_profiles_task.delay(bulk_in.model_dump())
    
    return {
        "message": f"Bulk creation of {bulk_in.count} profiles started",
        "task_id": task.id
    }

@router.get("/", response_model=ProfileListResponse)
async def list_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    computer_id: Optional[int] = None,
    status: Optional[ProfileStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista profiles con filtros"""
    service = ProfileService(db)
    profiles, total = await service.list_profiles(
        skip=skip,
        limit=limit,
        computer_id=computer_id,
        status=status
    )
    return ProfileListResponse(total=total, items=profiles)

@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene profile por ID"""
    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    profile_in: ProfileUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza profile"""
    service = ProfileService(db)
    try:
        profile = await service.update_profile(profile_id, profile_in)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return profile
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Elimina profile"""
    service = ProfileService(db)
    try:
        success = await service.delete_profile(profile_id)
        if not success:
            raise HTTPException(status_code=404, detail="Profile not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{profile_id}/warmup", status_code=202)
async def warmup_profile(
    profile_id: int,
    duration_minutes: int = Query(20, ge=5, le=120),
    db: AsyncSession = Depends(get_db)
):
    """Inicia warmup de profile"""
    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    from app.tasks.profile_tasks import warmup_profile_task
    task = warmup_profile_task.delay(profile_id, duration_minutes)
    
    return {
        "message": f"Warmup started for profile {profile_id}",
        "task_id": task.id
    }

@router.get("/stats/summary")
async def get_profiles_stats(
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas de profiles"""
    service = ProfileService(db)
    stats = await service.get_stats()
    return stats