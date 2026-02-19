# app/models/health_check.py
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class HealthCheck(Base):
    __tablename__ = "health_checks"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Target
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=False, index=True)
    
    # Check results
    is_healthy = Column(Boolean, default=False)
    response_time_ms = Column(Float)
    
    # Component status
    adspower_status = Column(String(20))  # online, offline, error
    database_status = Column(String(20))
    redis_status = Column(String(20))
    
    # Metrics
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    active_profiles = Column(Integer)
    
    # Details
    checks_details = Column(JSON, default=dict)
    errors = Column(JSON, default=list)
    
    # Timestamp
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    computer = relationship("Computer", back_populates="health_checks")
    
    def __repr__(self):
        return f"<HealthCheck(computer_id={self.computer_id}, healthy={self.is_healthy})>"