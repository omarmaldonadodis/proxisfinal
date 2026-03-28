# app/tasks/profile_verification.py  (versión simplificada)
from celery import shared_task
import httpx

@shared_task(name="verify_all_profiles")
def verify_all_profiles():
    from app.config import settings
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(f"{settings.API_INTERNAL_URL}/api/v1/profiles/verify-all")
    except Exception as e:
        pass