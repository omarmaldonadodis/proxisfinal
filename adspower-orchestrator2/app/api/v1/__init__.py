# app/api/v1/__init__.py
from fastapi import APIRouter

# Importar routers
from app.api.v1 import computers, proxies, profiles, tasks, health, automation, warming

# Router principal v1
router = APIRouter()

# Incluir todos los routers
router.include_router(computers.router)
router.include_router(proxies.router)
router.include_router(profiles.router)
router.include_router(tasks.router)
router.include_router(health.router)
router.include_router(automation.router)
router.include_router(warming.router)  # ✅ AÑADIDO

__all__ = ["router"]