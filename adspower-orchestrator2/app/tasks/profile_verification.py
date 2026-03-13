# app/tasks/profile_verification.py  (versión simplificada)
from celery import shared_task
import httpx

@shared_task(name="verify_all_profiles")
def verify_all_profiles():
    """Llama al endpoint FastAPI que sí tiene acceso al connection_manager."""
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post("http://localhost:8000/api/v1/profiles/verify-all")
    except Exception as e:
        pass  # FastAPI puede no estar listo todavía