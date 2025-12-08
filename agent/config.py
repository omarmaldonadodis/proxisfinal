from pydantic_settings import BaseSettings
from typing import Optional

class AgentConfig(BaseSettings):
    """Configuración del agente"""
    
    # ✅ Identificación (COMPUTER_ID ahora es opcional - se obtiene al registrar)
    COMPUTER_ID: Optional[int] = None  # Se asigna después del registro
    COMPUTER_NAME: str  # Único campo obligatorio para identificación
    
    # Orquestador
    ORCHESTRATOR_URL: str
    ORCHESTRATOR_WS_URL: Optional[str] = None  # Se genera automáticamente
    
    # AdsPower Local
    ADSPOWER_API_URL: Optional[str] = None  # Se detecta automáticamente
    ADSPOWER_API_KEY: str  # Obligatorio
    
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
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # ✅ Auto-generar ORCHESTRATOR_WS_URL si no existe
        if not self.ORCHESTRATOR_WS_URL:
            self.ORCHESTRATOR_WS_URL = self.ORCHESTRATOR_URL.replace("http://", "ws://").replace("https://", "wss://")
    
    def set_computer_id(self, computer_id: int):
        """Establece el COMPUTER_ID después del registro"""
        self.COMPUTER_ID = computer_id
