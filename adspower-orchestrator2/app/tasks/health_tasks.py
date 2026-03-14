# app/tasks/health_tasks.py — versión corregida usando HTTP interno
# (mismo patrón que proxy_rotation_tasks.py que ya usa httpx)

from celery import Task
import httpx
from loguru import logger


def get_celery_app():
    from app.tasks import celery_app
    return celery_app

celery_app = get_celery_app()


@celery_app.task(name='tasks.health_check_all_computers')
def health_check_all_computers_task():
    """Delega al endpoint FastAPI que tiene el event loop correcto."""
    from app.config import settings
    api_port = getattr(settings, 'API_PORT', 8000)
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"http://localhost:{api_port}/api/v1/health/computers")
            logger.info(f"Health check computers: {r.status_code}")
            return r.json()
    except Exception as e:
        logger.error(f"Error health check computers: {e}")
        return {"error": str(e)}


@celery_app.task(name='tasks.health_check_proxies')
def health_check_proxies_task():
    """Delega al endpoint FastAPI."""
    from app.config import settings
    api_port = getattr(settings, 'API_PORT', 8000)
    try:
        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                f"http://localhost:{api_port}/api/v1/proxies/health-check/batch",
                params={"limit": 50}
            )
            return r.json()
    except Exception as e:
        logger.error(f"Error health check proxies: {e}")
        return {"error": str(e)}