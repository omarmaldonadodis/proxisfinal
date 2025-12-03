# app/config.py
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "AdsPower Orchestrator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str
    DATABASE_SYNC_URL: str
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # AdsPower
    ADSPOWER_DEFAULT_API_URL: str = "http://local.adspower.net:50325"
    ADSPOWER_DEFAULT_API_KEY: Optional[str] = None
    
    # SOAX
    SOAX_USERNAME: str
    SOAX_PASSWORD: str
    SOAX_HOST: str = "proxy.soax.com"
    SOAX_PORT: int = 5000
    
    # 3X-UI
    USE_3XUI: bool = False
    THREEXUI_PANEL_URL: Optional[str] = None
    THREEXUI_USERNAME: Optional[str] = None
    THREEXUI_PASSWORD: Optional[str] = None
    
    # Monitoring
    ENABLE_METRICS: bool = True
    HEALTH_CHECK_INTERVAL: int = 300
    
    # Backup
    BACKUP_ENABLED: bool = True
    BACKUP_INTERVAL: int = 86400
    BACKUP_PATH: str = "/backups"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()