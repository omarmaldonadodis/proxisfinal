# app/models/proxy_rotation_log.py
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class RotationTrigger(str, enum.Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    HEALTH_FAIL = "health_fail"


class ProxyRotationLog(Base):
    __tablename__ = "proxy_rotation_logs"

    id = Column(Integer, primary_key=True, index=True)
    proxy_id = Column(Integer, ForeignKey("proxies.id", ondelete="SET NULL"), nullable=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    computer_id = Column(Integer, ForeignKey("computers.id", ondelete="SET NULL"), nullable=True)
    old_proxy_display = Column(String(255), nullable=True)
    new_proxy_display = Column(String(255), nullable=True)
    trigger = Column(SQLEnum(RotationTrigger), default=RotationTrigger.MANUAL, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=True)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    proxy = relationship("Proxy", foreign_keys=[proxy_id])