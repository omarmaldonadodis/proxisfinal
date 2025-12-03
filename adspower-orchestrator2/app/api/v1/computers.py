# app/api/v1/computers.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.services.computer_service import ComputerService
from app.schemas.computer import (
    ComputerCreate,
    ComputerUpdate,
    ComputerResponse,
    ComputerListResponse
)
from app.models.computer import ComputerStatus

router = APIRouter(prefix="/computers", tags=["Computers"])

@router.post("/", response_model=ComputerResponse, status_code=201)
async def create_computer(
    computer_in: ComputerCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo computer"""
    service = ComputerService(db)
    try:
        computer = await service.create_computer(computer_in)
        return computer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=ComputerListResponse)
async def list_computers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[ComputerStatus] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista computers con filtros"""
    service = ComputerService(db)
    computers, total = await service.list_computers(
        skip=skip,
        limit=limit,
        status=status,
        is_active=is_active
    )
    return ComputerListResponse(total=total, items=computers)

@router.get("/{computer_id}", response_model=ComputerResponse)
async def get_computer(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene computer por ID"""
    service = ComputerService(db)
    computer = await service.get_computer(computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    return computer

@router.patch("/{computer_id}", response_model=ComputerResponse)
async def update_computer(
    computer_id: int,
    computer_in: ComputerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza computer"""
    service = ComputerService(db)
    try:
        computer = await service.update_computer(computer_id, computer_in)
        if not computer:
            raise HTTPException(status_code=404, detail="Computer not found")
        return computer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{computer_id}", status_code=204)
async def delete_computer(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Elimina computer"""
    service = ComputerService(db)
    try:
        success = await service.delete_computer(computer_id)
        if not success:
            raise HTTPException(status_code=404, detail="Computer not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{computer_id}/health-check")
async def health_check_computer(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Verifica salud del computer"""
    service = ComputerService(db)
    try:
        result = await service.health_check(computer_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/stats/summary")
async def get_computers_stats(
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas de computers"""
    service = ComputerService(db)
    stats = await service.get_stats()
    return stats