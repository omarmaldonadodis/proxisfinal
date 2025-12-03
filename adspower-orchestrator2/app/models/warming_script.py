# app/models/warming_script.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class ActionType(str, enum.Enum):
    """Tipos de acciones para warming"""
    NAVIGATE = "navigate"              # Navegar a URL
    CLICK = "click"                   # Hacer click
    TYPE = "type"                     # Escribir texto
    SCROLL = "scroll"                 # Hacer scroll
    WAIT = "wait"                     # Esperar tiempo
    WAIT_ELEMENT = "wait_element"     # Esperar elemento
    HOVER = "hover"                   # Pasar mouse sobre elemento
    SELECT = "select"                 # Seleccionar opción
    PRESS_KEY = "press_key"           # Presionar tecla
    SCREENSHOT = "screenshot"          # Tomar screenshot
    SWITCH_TAB = "switch_tab"         # Cambiar de pestaña
    CLOSE_TAB = "close_tab"           # Cerrar pestaña
    EXECUTE_SCRIPT = "execute_script" # Ejecutar JavaScript
    RANDOM_MOUSE = "random_mouse"     # Movimiento aleatorio de mouse
    HUMAN_TYPING = "human_typing"     # Tipeo humanizado
    SEARCH_GOOGLE = "search_google"   # Búsqueda en Google
    LOGIN = "login"                   # Login en servicio

class ScriptStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

class WarmingScript(Base):
    """Scripts de warming reutilizables"""
    __tablename__ = "warming_scripts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Información básica
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # social_media, ecommerce, news, etc
    
    # Script
    actions = Column(JSON, nullable=False)  # Lista de acciones
    # Ejemplo: [
    #   {"type": "navigate", "url": "https://google.com"},
    #   {"type": "wait", "duration": 2},
    #   {"type": "click", "selector": "input[name='q']"},
    #   {"type": "type", "selector": "input[name='q']", "text": "test query", "human": true}
    # ]
    
    # Configuración
    duration_minutes = Column(Integer, default=15)
    randomize_order = Column(Boolean, default=False)
    repeat_count = Column(Integer, default=1)
    
    # Metadata
    status = Column(SQLEnum(ScriptStatus), default=ScriptStatus.DRAFT)
    is_template = Column(Boolean, default=False)
    tags = Column(JSON, default=list)
    success_rate = Column(Integer, default=0)  # 0-100
    times_used = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    executions = relationship("WarmingExecution", back_populates="script")

class ExecutionStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WarmingExecution(Base):
    """Historial de ejecuciones de warming"""
    __tablename__ = "warming_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Referencias
    script_id = Column(Integer, ForeignKey("warming_scripts.id"), nullable=False)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=False)
    
    # Estado
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.QUEUED, index=True)
    progress = Column(Integer, default=0)  # 0-100
    
    # Resultados
    actions_completed = Column(Integer, default=0)
    actions_failed = Column(Integer, default=0)
    execution_log = Column(JSON, default=list)  # Log detallado de cada acción
    error_message = Column(Text)
    screenshots = Column(JSON, default=list)  # URLs de screenshots
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    script = relationship("WarmingScript", back_populates="executions")
    profile = relationship("Profile")
    computer = relationship("Computer")

class AgentConnection(Base):
    """Estado de conexión de agentes (Computadoras B)"""
    __tablename__ = "agent_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Computer vinculado
    computer_id = Column(Integer, ForeignKey("computers.id"), unique=True, nullable=False)
    
    # Conexión
    websocket_id = Column(String(255), unique=True)
    is_connected = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime(timezone=True))
    
    # Estado del agente
    active_browsers = Column(Integer, default=0)
    max_browsers = Column(Integer, default=10)
    cpu_usage = Column(Integer)  # Porcentaje
    memory_usage = Column(Integer)  # Porcentaje
    
    # Metadata
    agent_version = Column(String(50))
    capabilities = Column(JSON, default=dict)  # selenium, playwright, etc
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    computer = relationship("Computer")