# app/models/computer.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class ComputerStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"

class Computer(Base):
    __tablename__ = "computers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=False)
    
    # AdsPower API info
    adspower_api_url = Column(String(512), nullable=False)
    adspower_api_key = Column(String(512), nullable=False)
    
    # Status
    status = Column(SQLEnum(ComputerStatus), default=ComputerStatus.OFFLINE)
    is_active = Column(Boolean, default=True)
    
    # Capacity
    max_profiles = Column(Integer, default=50)
    current_profiles = Column(Integer, default=0)
    
    # Specs
    cpu_cores = Column(Integer)
    ram_gb = Column(Integer)
    os_info = Column(String(255))
    
    # Metadata
    tags = Column(JSON, default=list)
    meta_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True))
    
    # Relationships
    profiles = relationship("Profile", back_populates="computer", cascade="all, delete-orphan")
    health_checks = relationship("HealthCheck", back_populates="computer", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Computer(name={self.name}, status={self.status})>"