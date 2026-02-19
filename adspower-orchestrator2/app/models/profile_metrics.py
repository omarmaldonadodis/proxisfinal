# app/models/profile_metrics.py
"""
Métricas de uso de profiles y proxies
"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class ProfileMetrics(Base):
    """Métricas de uso de profiles"""
    __tablename__ = "profile_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relaciones
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, index=True)
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=True, index=True)
    
    # Métricas de proxy
    proxy_latency_ms = Column(Float)  # Latencia al momento de crear profile
    proxy_country = Column(String(2))
    proxy_city = Column(String(255))
    proxy_session_id = Column(String(255))
    
    # Métricas de creación
    creation_duration_seconds = Column(Float)  # Tiempo que tomó crear el profile
    creation_success = Column(Integer, default=1)  # 1 = éxito, 0 = fallo
    
    # Fingerprint usado
    device_type = Column(String(20))  # mobile, tablet, desktop
    device_brand = Column(String(50))
    device_os = Column(String(50))
    
    # Metadata
    adspower_response_time_ms = Column(Float)
    cookies_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    profile = relationship("Profile", backref="metrics")
    proxy = relationship("Proxy", backref="profile_metrics")


class ProxyUsageStats(Base):
    """Estadísticas agregadas de uso de proxies"""
    __tablename__ = "proxy_usage_stats"
    
    id = Column(Integer, primary_key=True)
    proxy_id = Column(Integer, ForeignKey("proxies.id"), unique=True, nullable=False, index=True)
    
    # Estadísticas de uso
    total_profiles_created = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    
    # Métricas de rendimiento
    avg_latency_ms = Column(Float)
    min_latency_ms = Column(Float)
    max_latency_ms = Column(Float)
    
    # Métricas de confiabilidad
    success_rate = Column(Float, default=100.0)
    total_rotations = Column(Integer, default=0)
    last_rotation_at = Column(DateTime(timezone=True))
    
    # Costos estimados (opcional)
    estimated_data_usage_gb = Column(Float, default=0.0)
    
    # Timestamps
    first_used_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    proxy = relationship("Proxy", backref="usage_stats")