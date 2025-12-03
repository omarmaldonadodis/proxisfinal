# app/models/profile.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class ProfileStatus(str, enum.Enum):
    CREATING = "creating"
    READY = "ready"
    WARMING = "warming"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    DELETED = "deleted"

class DeviceType(str, enum.Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # AdsPower ID
    adspower_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Computer assignment
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=False, index=True)
    
    # Proxy assignment
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=True, index=True)
    
    # Profile info
    name = Column(String(255), nullable=False)
    age = Column(Integer)
    gender = Column(String(10))
    
    # Location
    country = Column(String(2), index=True)
    city = Column(String(255))
    timezone = Column(String(100))
    language = Column(String(10))
    
    # Device
    device_type = Column(SQLEnum(DeviceType), default=DeviceType.DESKTOP)
    device_name = Column(String(255))
    user_agent = Column(Text)
    
    # Fingerprints
    screen_resolution = Column(String(50))
    viewport = Column(String(50))
    pixel_ratio = Column(String(10))
    hardware_concurrency = Column(Integer)
    device_memory = Column(Integer)
    platform = Column(String(50))
    
    # Profile data
    interests = Column(JSON, default=list)
    browsing_history = Column(JSON, default=list)
    
    # Status
    status = Column(SQLEnum(ProfileStatus), default=ProfileStatus.CREATING, index=True)
    is_warmed = Column(Boolean, default=False)
    warmup_completed_at = Column(DateTime(timezone=True))
    
    # Usage tracking
    last_opened_at = Column(DateTime(timezone=True))
    total_sessions = Column(Integer, default=0)
    total_duration_seconds = Column(Integer, default=0)
    
    # Metadata
    tags = Column(JSON, default=list)
    meta_data = Column(JSON, nullable=True)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    computer = relationship("Computer", back_populates="profiles")
    proxy = relationship("Proxy", back_populates="profiles")
    tasks = relationship("Task", back_populates="profile", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Profile(name={self.name}, adspower_id={self.adspower_id}, status={self.status})>"