# app/schemas/profile.py
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.profile import ProfileStatus, DeviceType


# ─── CREATE ───────────────────────────────────────────────────────────────────
# Profile ya NO necesita computer_id — es global

class ProfileCreate(BaseModel):
    name:      str
    proxy_id:  Optional[int] = None   # Si ya existe un proxy, asignarlo directamente

    # Identidad
    owner:     Optional[str] = None
    bookie:    Optional[str] = None
    sport:     Optional[str] = None
    country:   Optional[str] = None
    city:      Optional[str] = None
    language:  Optional[str] = "es-ES"

    # Dispositivo
    device_type:       DeviceType = DeviceType.DESKTOP
    os:                Optional[str] = "Windows"
    screen_resolution: Optional[str] = "1920x1080"

    # Proxy / Red
    rotation_minutes: int       = 30
    warmup_urls:      List[str] = []

    # Opciones
    auto_fingerprint: bool = True
    tags:             List[str] = []
    notes:            Optional[str] = None


# ─── CREATE CON PROXY (crea proxy y perfil en una sola operación) ────────────

class ProfileWithProxyCreate(BaseModel):
    # Info general
    name:    str
    owner:   Optional[str] = None
    bookie:  Optional[str] = None
    sport:   Optional[str] = None

    # Proxy / Red
    proxy_type:       str       = "RESIDENTIAL"   # RESIDENTIAL | MOBILE_4G | DATACENTER
    country:          str       = "ES"
    city:             Optional[str] = None
    rotation_minutes: int       = 30
    warmup_urls:      List[str] = []

    # Dispositivo / Huella digital
    device_type:      str  = "DESKTOP"            # DESKTOP | TABLET | MOBILE
    os:               str  = "Windows"
    screen_res:       str  = "1920x1080"
    language:         str  = "es-ES"
    auto_fingerprint: bool = True
    open_on_create:   bool = False                # Abrir navegador al crear


# ─── UPDATE ───────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    name:              Optional[str]   = None
    status:            Optional[ProfileStatus] = None
    proxy_id:          Optional[int]   = None
    owner:             Optional[str]   = None
    bookie:            Optional[str]   = None
    sport:             Optional[str]   = None
    browser_score:     Optional[float] = None
    fingerprint_score: Optional[float] = None
    cookie_status:     Optional[str]   = None
    health_score:      Optional[float] = None
    trust_score:       Optional[float] = None
    last_action:       Optional[str]   = None
    memory_mb:         Optional[float] = None
    is_warmed:         Optional[bool]  = None
    warmup_urls:       Optional[List[str]] = None
    tags:              Optional[List[str]] = None
    notes:             Optional[str]   = None
    meta_data:         Optional[dict]  = None


# ─── RESPONSE ─────────────────────────────────────────────────────────────────

class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    adspower_id:      str
    name:             str
    proxy_id:         Optional[int] = None
    status:           ProfileStatus

    # Identidad
    owner:            Optional[str] = None
    bookie:           Optional[str] = None
    sport:            Optional[str] = None
    country:          Optional[str] = None
    city:             Optional[str] = None
    language:         Optional[str] = None

    # Dispositivo
    device_type:      DeviceType
    os:               Optional[str] = None
    screen_resolution: Optional[str] = None

    # Métricas de calidad
    health_score:      float = 100.0
    trust_score:       float = 100.0
    browser_score:     float = 0.0
    fingerprint_score: float = 0.0
    cookie_status:     str   = "MISSING"
    last_action:       Optional[str] = None
    memory_mb:         float = 0.0

    # Proxy / Red
    rotation_minutes:  int       = 30
    warmup_urls:       List[str] = []

    is_warmed:         bool = False
    total_sessions:    int  = 0
    tags:              List[str] = []
    created_at:        datetime
    updated_at:        Optional[datetime] = None


# ─── LIST ─────────────────────────────────────────────────────────────────────

class ProfileListResponse(BaseModel):
    total: int
    items: List[ProfileResponse]

class ProfileBulkCreate(BaseModel):
    count:       int
    proxy_id:    int
    device_type: DeviceType = DeviceType.DESKTOP
    owner:       Optional[str] = None
    bookie:      Optional[str] = None
    sport:       Optional[str] = None
    country:     Optional[str] = None
    city:        Optional[str] = None
    language:    Optional[str] = "es-ES"
    tags:        List[str] = []
    notes:       Optional[str] = None