# agent/event_types.py
from enum import Enum

class EventType(str, Enum):
    """Tipos de eventos que requieren atención"""
    
    # 🔴 CRÍTICOS (requieren intervención manual)
    RECAPTCHA_DETECTED = "recaptcha_detected"
    IP_BLOCKED = "ip_blocked"
    ACCOUNT_SUSPENDED = "account_suspended"
    BROWSER_CRASH = "browser_crash"
    ADSPOWER_LIMIT_REACHED = "adspower_limit_reached"
    
    # 🟡 ADVERTENCIAS (posible intervención)
    LOGIN_FAILED_CREDENTIALS = "login_failed_credentials"
    ALREADY_LOGGED_IN = "already_logged_in"
    SESSION_EXPIRED = "session_expired"
    POPUP_BLOCKED = "popup_blocked"
    PAGE_NOT_LOADING = "page_not_loading"
    PROXY_TIMEOUT = "proxy_timeout"
    
    # 🟢 INFORMATIVOS
    LOGIN_SUCCESS = "login_success"
    NAVIGATION_SUCCESS = "navigation_success"
    ACTION_COMPLETED = "action_completed"
    
    # 🔵 ESTADO
    EXECUTION_STARTED = "execution_started"
    EXECUTION_PROGRESS = "execution_progress"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"


class EventSeverity(str, Enum):
    """Nivel de severidad"""
    CRITICAL = "critical"      # Requiere intervención inmediata
    WARNING = "warning"        # Puede requerir intervención
    INFO = "info"              # Solo informativo
    DEBUG = "debug"            # Detalles técnicos