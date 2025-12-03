# app/models/proxy.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class ProxyType(str, enum.Enum):
    MOBILE = "mobile"
    RESIDENTIAL = "residential"
    DATACENTER = "datacenter"

class ProxyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CHECKING = "checking"
    FAILED = "failed"

class Proxy(Base):
    __tablename__ = "proxies"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Proxy info
    proxy_type = Column(SQLEnum(ProxyType), nullable=False, index=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(512))
    password = Column(String(512))
    
    # Geo-targeting
    country = Column(String(2), index=True)
    region = Column(String(255))
    city = Column(String(255))
    
    # Session info
    session_id = Column(String(255), unique=True)
    session_lifetime = Column(Integer, default=3600)
    sticky_session = Column(Boolean, default=True)
    
    # Status
    status = Column(SQLEnum(ProxyStatus), default=ProxyStatus.INACTIVE, index=True)
    is_available = Column(Boolean, default=True)
    
    # Health metrics
    last_check_at = Column(DateTime(timezone=True))
    last_success_at = Column(DateTime(timezone=True))
    success_rate = Column(Float, default=100.0)
    avg_response_time = Column(Float)  # milliseconds
    total_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    
    # IP info (from last check)
    detected_ip = Column(String(45))
    detected_country = Column(String(2))
    detected_city = Column(String(255))
    detected_isp = Column(String(255))
    
    # Usage tracking
    profiles_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))
    
    # Metadata
    tags = Column(JSON, default=list)
    meta_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    profiles = relationship("Profile", back_populates="proxy")
    
    def __repr__(self):
        return f"<Proxy(type={self.proxy_type}, country={self.country}, status={self.status})>"