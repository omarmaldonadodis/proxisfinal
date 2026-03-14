# app/models/agent_session.py
#
# MODELO CORRECTO: AgentSession es el registro de toda actividad.
# - computer_id: OBLIGATORIO — quién abrió el navegador
# - profile_id:  OPCIONAL — si se usó un perfil de AdsPower
# - assignment_id: ELIMINADO — ya no hay assignments rígidos
#
# Registra CUALQUIER apertura de navegador, incluso sin perfil (solo URL).
#
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum


try:
    from app.database import Base
except ImportError:
    from sqlalchemy.orm import declarative_base
    Base = declarative_base()


class SessionStatus(str, enum.Enum):
    OPENING  = "opening"   # Comando enviado, esperando confirmación
    ACTIVE   = "active"    # Navegador abierto y activo
    CLOSED   = "closed"    # Cerrado correctamente
    CRASHED  = "crashed"   # Cerró de forma inesperada
    DENIED   = "denied"    # Se rechazó (perfil bloqueado, proxy caído, etc.)


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id           = Column(Integer, primary_key=True, index=True)

    # ── Quién abrió el navegador ──────────────────────────────────────────────
    # Siempre requerido — es la clave del tracking
    computer_id  = Column(Integer, ForeignKey("computers.id"), nullable=False, index=True)
    agent_name   = Column(String(255), nullable=True)   # Nombre del agente/operador

    # ── Qué perfil usó (OPCIONAL) ─────────────────────────────────────────────
    # Si es solo una visita web sin AdsPower, profile_id es NULL
    profile_id          = Column(Integer, ForeignKey("profiles.id"), nullable=True, index=True)
    adspower_profile_id = Column(String(255), nullable=True, index=True)

    # ── Qué hizo ──────────────────────────────────────────────────────────────
    target_url   = Column(Text, nullable=True)     # URL donde fue
    last_url     = Column(Text, nullable=True)     # Última URL visitada

    # ── Estado y tiempos ──────────────────────────────────────────────────────
    status = Column(
        String(50),
        default=SessionStatus.OPENING.value,  # ← .value, no el enum
        index=True
    )

    
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    opened_at    = Column(DateTime(timezone=True), nullable=True)
    closed_at    = Column(DateTime(timezone=True), nullable=True)

    # ── Métricas de la sesión ─────────────────────────────────────────────────
    duration_seconds = Column(Integer, nullable=True)     # Duración total
    pages_visited    = Column(Integer, default=0)         # Páginas visitadas
    total_data_mb    = Column(Float,   default=0.0)       # Datos consumidos
    browser_health = Column(String(50), nullable=True)
    memory_mb        = Column(Float,   default=0.0)       # RAM usada

    # ── Razón de error/denegación ─────────────────────────────────────────────
    denial_reason    = Column(Text, nullable=True)
    error_detail     = Column(Text, nullable=True)

    # ── Eventos durante la sesión ─────────────────────────────────────────────
    events           = Column(JSON, default=list)   # Lista de eventos registrados


    assignment_id      = Column(Integer, nullable=True)
    data_sent_mb       = Column(Float, nullable=True)
    data_received_mb   = Column(Float, nullable=True)
    last_url_at        = Column(DateTime(timezone=True), nullable=True)
    avg_response_time_ms = Column(Float, nullable=True)
    browser_pid        = Column(Integer, nullable=True)
    local_cpu_percent  = Column(Float, nullable=True)
    local_ram_mb       = Column(Float, nullable=True)
    authorized_by      = Column(String(255), nullable=True)

    # ── Relaciones ────────────────────────────────────────────────────────────
    # sessions = relationship("AgentSession", back_populates="computer")
    computer = relationship("Computer", back_populates="sessions")
    profile  = relationship("Profile",   back_populates="sessions")
    browser_events = relationship("BrowserEvent", back_populates="session")
    # app/models/agent_session.py — en la sección de relaciones, agregar:


    def __repr__(self):
        return (
            f"<AgentSession(id={self.id}, computer={self.computer_id}, "
            f"profile={self.profile_id}, status={self.status})>"
        )
# ─── BrowserEvent — requerido por app/models/__init__.py ─────────────────────

class BrowserEventType(str, enum.Enum):
    PAGE_VISIT      = "page_visit"
    FORM_SUBMIT     = "form_submit"
    CLICK           = "click"
    SCROLL          = "scroll"
    LOGIN           = "login"
    LOGOUT          = "logout"
    ERROR           = "error"
    SCREENSHOT      = "screenshot"
    DOWNLOAD        = "download"
    UPLOAD          = "upload"


class BrowserEvent(Base):
    __tablename__ = "browser_events"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=False, index=True)
    event_type = Column(
        String(50),
        nullable=False,
        index=True
    )
    url        = Column(Text,        nullable=True)
    details    = Column(JSON,        nullable=True)
    timestamp  = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    session = relationship("AgentSession", back_populates="browser_events")