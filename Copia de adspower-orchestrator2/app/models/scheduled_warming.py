# app/models/scheduled_warming.py
"""
Modelo para warming scripts programados
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class ScheduleFrequency(str, enum.Enum):
    """Frecuencia de ejecución"""
    ONCE = "once"              # Una sola vez
    DAILY = "daily"            # Diario
    WEEKLY = "weekly"          # Semanal
    MONTHLY = "monthly"        # Mensual
    CUSTOM_CRON = "custom"     # Cron personalizado

class ScheduledWarmingStatus(str, enum.Enum):
    """Estado de programación"""
    PENDING = "pending"        # Esperando ejecución
    RUNNING = "running"        # Ejecutando
    COMPLETED = "completed"    # Completado
    FAILED = "failed"          # Falló
    CANCELLED = "cancelled"    # Cancelado
    PAUSED = "paused"          # Pausado

class ScheduledWarming(Base):
    """Warming script programado"""
    __tablename__ = "scheduled_warmings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Script y perfil
    script_id = Column(Integer, ForeignKey("warming_scripts.id"), nullable=False)
    profile_ids = Column(JSON, nullable=False)  # Lista de profile IDs
    
    # Programación
    frequency = Column(SQLEnum(ScheduleFrequency), nullable=False, default=ScheduleFrequency.ONCE)
    
    # Fecha/hora de ejecución (UTC)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)  # Primera ejecución
    
    # Para recurrencia
    cron_expression = Column(String(100), nullable=True)  # Ej: "0 14 * * *" (2 PM diario)
    timezone = Column(String(50), nullable=True, default="UTC")  # Timezone del usuario
    
    # Días de la semana (para frecuencia WEEKLY)
    days_of_week = Column(JSON, nullable=True)  # [0,1,2,3,4] = Lunes a Viernes
    
    # Tiempo de ejecución
    time_of_day = Column(String(5), nullable=True)  # "14:30" = 2:30 PM
    
    # Estado
    status = Column(SQLEnum(ScheduledWarmingStatus), default=ScheduledWarmingStatus.PENDING)
    is_active = Column(Boolean, default=True)
    
    # Resultados
    last_execution_at = Column(DateTime(timezone=True), nullable=True)
    next_execution_at = Column(DateTime(timezone=True), nullable=True)
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    
    # Límites
    max_executions = Column(Integer, nullable=True)  # None = infinito
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Fecha de expiración
    
    # Metadata
    created_by = Column(String(100), nullable=True)
    tags = Column(JSON, default=list)
    notes = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    script = relationship("WarmingScript")
    executions = relationship("WarmingExecution", back_populates="scheduled_warming", foreign_keys="[WarmingExecution.scheduled_warming_id]")
    
    def __repr__(self):
        return f"<ScheduledWarming(script_id={self.script_id}, scheduled_at={self.scheduled_at})>"