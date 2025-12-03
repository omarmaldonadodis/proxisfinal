# app/api/v1/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("/")
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy",
        "message": "API is running"
    }

@router.get("/system")
async def system_health(
    db: AsyncSession = Depends(get_db)
):
    """Health check del sistema completo"""
    service = HealthService(db)
    health = await service.check_system_health()
    return health

@router.get("/computers")
async def computers_health(
    db: AsyncSession = Depends(get_db)
):
    """Health check de todos los computers"""
    service = HealthService(db)
    health = await service.check_all_computers()
    return health

@router.get("/proxies")
async def proxies_health(
    db: AsyncSession = Depends(get_db)
):
    """Health check de proxies"""
    service = HealthService(db)
    health = await service.check_proxies()
    return health

@router.get("/database")
async def database_health(
    db: AsyncSession = Depends(get_db)
):
    """Health check de base de datos"""
    service = HealthService(db)
    health = await service.check_database()
    return health

@router.get("/redis")
async def redis_health():
    """Health check de Redis"""
    service = HealthService(None)
    health = await service.check_redis()
    return health