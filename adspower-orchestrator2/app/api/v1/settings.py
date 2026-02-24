# app/api/v1/settings.py
from fastapi import APIRouter
from app.config import settings

router = APIRouter(prefix="/settings", tags=["⚙️ Settings"])


def _mask(value: str | None) -> str | None:
    if not value:
        return None
    return "***" + value[-4:] if len(value) > 4 else "***"


@router.get("/")
async def get_settings():
    return {
        "adspower": {
            "api_url": settings.ADSPOWER_DEFAULT_API_URL,
            "api_key": _mask(settings.ADSPOWER_DEFAULT_API_KEY),
        },
        "soax": {
            "host": settings.SOAX_HOST,
            "port": settings.SOAX_PORT,
            "username": settings.SOAX_USERNAME,
            "password": _mask(settings.SOAX_PASSWORD),
        },
        "backup": {
            "enabled": settings.BACKUP_ENABLED,
            "interval_hours": settings.BACKUP_INTERVAL // 3600,
            "path": settings.BACKUP_PATH,
        },
        "system": {
            "health_check_interval_seconds": settings.HEALTH_CHECK_INTERVAL,
            "debug": settings.DEBUG,
        },
    }