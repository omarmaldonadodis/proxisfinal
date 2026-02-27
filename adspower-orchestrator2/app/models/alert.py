# app/models/alert.py
import enum
from sqlalchemy import Column, String, Integer, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database import Base


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"
    RESOLVED = "resolved"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    severity = Column(String(50), default=AlertSeverity.INFO.value, nullable=False)
    status = Column(String(50), default=AlertStatus.ACTIVE.value, nullable=False, index=True)
    source = Column(String(100), nullable=True)       # "proxy", "computer", "profile"
    source_id = Column(Integer, nullable=True)
    acknowledged_by = Column(String(255), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    silenced_until = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

