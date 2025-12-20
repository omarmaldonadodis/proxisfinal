from fastapi import APIRouter

from app.api.v1 import computers, proxies, profiles, health, warming, registration, events, proxy_rotation

router = APIRouter()

router.include_router(computers.router)
router.include_router(proxies.router)
router.include_router(profiles.router)
router.include_router(health.router)
router.include_router(warming.router) 
router.include_router(registration.router)
router.include_router(events.router)
router.include_router(proxy_rotation.router)

__all__ = ["router"]

