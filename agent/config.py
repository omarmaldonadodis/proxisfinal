# agent/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class AgentConfig(BaseSettings):
    """Configuración del agente"""
    
    # Identificación
    COMPUTER_ID: int
    COMPUTER_NAME: str = "Agent Computer"
    
    # Orquestador
    ORCHESTRATOR_URL: str = "http://localhost:8000"
    ORCHESTRATOR_WS_URL: str = "ws://localhost:8000"
    
    # AdsPower Local
    ADSPOWER_API_URL: str = "http://local.adspower.net:50325"
    ADSPOWER_API_KEY: str
    
    # Capacidad
    MAX_BROWSERS: int = 10
    MAX_CONCURRENT_EXECUTIONS: int = 5
    
    # Timeouts
    ACTION_TIMEOUT: int = 30  # segundos
    BROWSER_OPEN_TIMEOUT: int = 60
    
    # Logs
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = "logs"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

