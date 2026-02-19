# app/models/proxy_health.py
"""
Sistema de Health Tracking para Proxies
Almacena historial de verificaciones y métricas
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class HealthCheckStatus(str, enum.Enum):
    """Estados de verificación"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    SLOW = "slow"

# adspower-orchestrator2/app/models/proxy_health.py


class ProxyHealthCheck(Base):
    """Historial de verificaciones de proxy"""
    __tablename__ = "proxy_health_checks"
    
    # ✅ CRÍTICO: ID auto-generado (no manual)
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Relación con proxy
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=False, index=True)
    
    # Resultado de verificación
    status = Column(String(20), nullable=False, index=True)
    check_type = Column(String(50), nullable=False)
    
    # Métricas de velocidad
    latency_ms = Column(Float)
    download_speed_mbps = Column(Float)
    upload_speed_mbps = Column(Float)
    
    # Verificación geográfica
    detected_ip = Column(String(45))
    detected_country = Column(String(2))
    detected_city = Column(String(255))
    detected_isp = Column(String(255))
    geo_match = Column(Boolean)
    
    # Información de disponibilidad
    is_available = Column(Boolean)
    response_code = Column(Integer)
    error_message = Column(Text)
    
    # Sesión utilizada
    session_id = Column(String(255))
    session_test_result = Column(JSON)
    
    # Metadata
    test_urls = Column(JSON)
    raw_response = Column(JSON)
    
    # Timestamp
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    proxy = relationship("Proxy", back_populates="health_checks")
    
   #  def __repr__(self):
   #      return f"<ProxyHealthCheck(proxy_id={self.proxy_id}, status={self.status}, latency={self.latency_ms}ms)>"


class ProxyScore(Base):
    """Sistema de scoring para proxies"""
    __tablename__ = "proxy_scores"
    
    id = Column(Integer, primary_key=True)
    proxy_id = Column(Integer, ForeignKey("proxies.id"), unique=True, nullable=False, index=True)
    
    # Score general (0-100)
    overall_score = Column(Float, default=100.0, index=True)
    
    # Scores por categoría
    speed_score = Column(Float, default=100.0)  # Basado en latencia
    availability_score = Column(Float, default=100.0)  # Basado en uptime
    geo_accuracy_score = Column(Float, default=100.0)  # Basado en coincidencia geo
    stability_score = Column(Float, default=100.0)  # Basado en consistencia
    
    # Estadísticas
    total_checks = Column(Integer, default=0)
    successful_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    timeout_checks = Column(Integer, default=0)
    
    # Latencias (ms)
    avg_latency = Column(Float)
    min_latency = Column(Float)
    max_latency = Column(Float)
    
    # Uptime
    uptime_percentage = Column(Float, default=100.0)
    
    # Geo accuracy
    geo_mismatch_count = Column(Integer, default=0)
    
    # Blacklist
    is_blacklisted = Column(Boolean, default=False, index=True)
    blacklist_reason = Column(Text)
    blacklisted_at = Column(DateTime(timezone=True))
    
    # Auto-recovery
    consecutive_failures = Column(Integer, default=0)
    last_recovery_attempt = Column(DateTime(timezone=True))
    
    # Timestamps
    last_check_at = Column(DateTime(timezone=True))
    score_updated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    proxy = relationship("Proxy", back_populates="score")
    
    def __repr__(self):
        return f"<ProxyScore(proxy_id={self.proxy_id}, score={self.overall_score})>"


