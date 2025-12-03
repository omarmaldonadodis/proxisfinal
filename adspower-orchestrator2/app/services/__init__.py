# app/services/__init__.py
from app.services.computer_service import ComputerService
from app.services.proxy_service import ProxyService
from app.services.profile_service import ProfileService
from app.services.task_service import TaskService
from app.services.health_service import HealthService
from app.services.automation_service import AutomationService

__all__ = [
    "ComputerService",
    "ProxyService",
    "ProfileService",
    "TaskService",
    "HealthService",
    "AutomationService",
]