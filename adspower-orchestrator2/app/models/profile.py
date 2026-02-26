# app/models/profile.py
#
# MODELO CORRECTO: Profile es GLOBAL.
# - No pertenece a ninguna computadora específica.
# - Cualquier computer puede abrir cualquier perfil.
# - El tracking de "quién abrió qué" está en AgentSession, no aquí.
#
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class ProfileStatus(str, enum.Enum):
    CREATING = "creating"
    READY    = "ready"
    WARMING  = "warming"
    ACTIVE   = "active"
    BUSY     = "busy"
    ERROR    = "error"
    DELETED  = "deleted"


class DeviceType(str, enum.Enum):
    DESKTOP = "desktop"
    MOBILE  = "mobile"
    TABLET  = "tablet"


class Profile(Base):
    __tablename__ = "profiles"

    id                   = Column(Integer, primary_key=True, index=True)
    adspower_id          = Column(String(255), unique=True, nullable=False, index=True)

    # ── Proxy asignado al perfil (global, no de una computadora) ──────────────
    # El proxy SÍ pertenece al perfil porque define la identidad de red.
    # Cualquier computadora que abra este perfil usará este proxy.
    proxy_id             = Column(Integer, ForeignKey("proxies.id"), nullable=True, index=True)

    # ── Identidad del perfil ──────────────────────────────────────────────────
    name                 = Column(String(255), nullable=False)
    age                  = Column(Integer)
    gender               = Column(String(10))
    country              = Column(String(10), index=True)   # Código ISO: ES, MX, GB...
    city                 = Column(String(255))
    timezone             = Column(String(100))
    language             = Column(String(10))              # es-ES, en-US...

    # ── Huella de dispositivo ─────────────────────────────────────────────────
    device_type          = Column(SQLEnum(DeviceType), default=DeviceType.DESKTOP)
    device_name          = Column(String(255))
    os                   = Column(String(50))              # Windows, macOS, Android, iOS
    user_agent           = Column(Text)
    screen_resolution    = Column(String(50))
    viewport             = Column(String(50))
    pixel_ratio          = Column(String(10))
    hardware_concurrency = Column(Integer)
    device_memory        = Column(Integer)
    platform             = Column(String(50))

    # ── Campos de negocio ─────────────────────────────────────────────────────
    owner             = Column(String(255), nullable=True, index=True)   # Dueño del perfil
    bookie            = Column(String(100), nullable=True, index=True)   # Bet365, 1xBet...
    sport             = Column(String(50),  nullable=True)               # Fútbol, Tenis...
    rotation_minutes  = Column(Integer,     default=30)                  # Rotación de proxy

    # ── Métricas de calidad ───────────────────────────────────────────────────
    browser_score     = Column(Float, default=0.0)
    fingerprint_score = Column(Float, default=0.0)
    cookie_status     = Column(String(20), default="MISSING")  # OK | EXPIRED | MISSING
    health_score      = Column(Float, default=100.0)
    trust_score       = Column(Float, default=100.0)
    last_action       = Column(String(50), nullable=True)      # OPEN | CLOSE | WARM | ERROR
    memory_mb         = Column(Float, default=0.0)

    # ── URLs de warm-up (historial de navegación simulado) ───────────────────
    warmup_urls       = Column(JSON, default=list)    # ["https://google.com", ...]
    interests         = Column(JSON, default=list)
    browsing_history  = Column(JSON, default=list)

    # ── Estado ────────────────────────────────────────────────────────────────
    status                 = Column(SQLEnum(ProfileStatus), default=ProfileStatus.CREATING, index=True)
    is_warmed              = Column(Boolean, default=False)
    warmup_completed_at    = Column(DateTime(timezone=True))
    last_opened_at         = Column(DateTime(timezone=True))
    total_sessions         = Column(Integer, default=0)
    total_duration_seconds = Column(Integer, default=0)
    tags                   = Column(JSON, default=list)
    meta_data              = Column(JSON, nullable=True)
    notes                  = Column(Text)
    created_at             = Column(DateTime(timezone=True), server_default=func.now())
    updated_at             = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relaciones ────────────────────────────────────────────────────────────
    proxy    = relationship("Proxy", back_populates="profiles")
    sessions = relationship("AgentSession", back_populates="profile")
    

    def __repr__(self):
        return f"<Profile(name={self.name}, adspower_id={self.adspower_id}, status={self.status})>"