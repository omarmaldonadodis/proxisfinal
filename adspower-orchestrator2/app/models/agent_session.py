# app/models/agent_session.py
"""
AgentSession: cada vez que un agente abre un navegador AdsPower
BrowserEvent: cada evento dentro de ese navegador
"""
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime,
    JSON, Float, ForeignKey, Text, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class SessionStatus(str, enum.Enum):
    PENDING_AUTH = "pending_auth"   # esperando autorización del admin
    OPENING = "opening"              # el agente está abriendo el navegador
    ACTIVE = "active"                # navegador abierto y funcionando
    CLOSED = "closed"                # cerrado normalmente
    CRASHED = "crashed"              # cerró de forma inesperada
    DENIED = "denied"                # admin denegó la apertura


class BrowserEventType(str, enum.Enum):
    NAVIGATION = "navigation"
    FORM_SUBMIT = "form_submit"
    DOWNLOAD = "download"
    SCREENSHOT = "screenshot"
    TAB_OPENED = "tab_opened"
    TAB_CLOSED = "tab_closed"
    ERROR = "error"


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Referencias
    assignment_id = Column(Integer, ForeignKey("profile_assignments.id"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, index=True)
    computer_id = Column(Integer, ForeignKey("computers.id"), nullable=True, index=True)

    # Quién abrió (desnormalizado para consultas rápidas)
    agent_name = Column(String(255), nullable=False, index=True)

    # Qué abrió
    target_url = Column(String(1024))
    adspower_profile_id = Column(String(255))  # el ID string de AdsPower

    # Estado
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.OPENING, index=True)

    # Timestamps
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    opened_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # Métricas de red
    data_sent_mb = Column(Float, default=0.0)
    data_received_mb = Column(Float, default=0.0)
    total_data_mb = Column(Float, default=0.0)

    # Métricas de uso
    pages_visited = Column(Integer, default=0)
    last_url = Column(Text)
    last_url_at = Column(DateTime(timezone=True))

    # Salud del navegador
    browser_health = Column(String(20), default="unknown")  # healthy, slow, crashed
    avg_response_time_ms = Column(Float)

    # Info del proceso local (llenado por el agente)
    browser_pid = Column(Integer)
    local_cpu_percent = Column(Float)
    local_ram_mb = Column(Float)

    # Admin
    authorized_by = Column(String(255))
    denial_reason = Column(Text)

    # Relationships
    assignment = relationship("ProfileAssignment", back_populates="sessions")
    profile = relationship("Profile")
    computer = relationship("Computer")
    events = relationship(
        "BrowserEvent",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="BrowserEvent.timestamp"
    )


class BrowserEvent(Base):
    __tablename__ = "browser_events"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=False, index=True)

    event_type = Column(SQLEnum(BrowserEventType), nullable=False, index=True)
    url = Column(Text)
    page_title = Column(String(512))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Datos adicionales del evento
    extra_data = Column(JSON)

    session = relationship("AgentSession", back_populates="events")