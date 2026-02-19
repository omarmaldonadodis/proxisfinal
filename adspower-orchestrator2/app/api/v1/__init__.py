# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.v1 import computers, proxies, profiles, health, proxy_rotation, metrics

router = APIRouter()

router.include_router(computers.router)
router.include_router(proxies.router)
router.include_router(profiles.router)
router.include_router(health.router)
router.include_router(proxy_rotation.router)
router.include_router(metrics.router)  # NUEVO

__all__ = ["router"]