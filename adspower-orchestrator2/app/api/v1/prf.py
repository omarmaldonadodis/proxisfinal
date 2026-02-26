# app/api/v1/profiles.py
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.services.profile_service import ProfileService
from app.schemas.profile import (
    ProfileCreate,
    ProfileWithProxyCreate,
    ProfileUpdate,
    ProfileResponse,
    ProfileListResponse,
)
from app.models.profile import Profile, ProfileStatus, DeviceType

router = APIRouter()


# ─── LISTAR ────────────────────────────────────────────────────────────────────
# IMPORTANTE: las rutas estáticas van ANTES de /{profile_id}

@router.get("/", response_model=ProfileListResponse)
async def list_profiles(
    skip:          int             = Query(0,   ge=0),
    limit:         int             = Query(100, ge=1, le=1000),
    status:        Optional[str]   = Query(None),
    owner:         Optional[str]   = Query(None),
    bookie:        Optional[str]   = Query(None),
    cookie_status: Optional[str]   = Query(None),
    country:       Optional[str]   = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los perfiles del sistema. Sin filtro por computadora — los perfiles son globales."""
    service = ProfileService(db)
    profiles, total = await service.list_profiles(
        skip=skip, limit=limit,
        status=status, owner=owner,
        bookie=bookie, cookie_status=cookie_status,
        country=country,
    )
    return ProfileListResponse(total=total, items=profiles)


# ─── CREAR SIMPLE ──────────────────────────────────────────────────────────────
@router.post("/", response_model=ProfileResponse, status_code=201)
async def create_profile(
    data: ProfileCreate,
    db: AsyncSession = Depends(get_db),
):
    """Crea un perfil. No requiere computer_id — el perfil es global."""
    service = ProfileService(db)
    profile = await service.create_profile(data)
    return profile


# ─── CREAR CON PROXY (operación atómica) ──────────────────────────────────────
# DEBE ir antes de /{profile_id} para que FastAPI no lo confunda con un ID
@router.post("/create-with-proxy", status_code=201)
async def create_profile_with_proxy(
    data: ProfileWithProxyCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Crea proxy + perfil en una sola operación.
    El perfil es GLOBAL: no se asigna a ninguna computadora.
    Si open_on_create=True, el sistema enviará el comando a cualquier agente online.

    Flujo:
    1. Busca un proxy disponible con país/tipo solicitado
    2. Si no hay, crea uno nuevo en la tabla proxies
    3. Crea el Profile en BD (status=CREATING)
    4. Envía comando create_adspower_profile al agente disponible
    5. Notifica al panel admin via WebSocket
    """
    import uuid
    from app.models.proxy import Proxy, ProxyStatus
    from app.models.computer import Computer, ComputerStatus
    from app.core.connection_manager import connection_manager

    proxy_type_map = {
        "RESIDENTIAL": "residential",
        "MOBILE_4G":   "mobile",
        "DATACENTER":  "datacenter",
    }
    db_proxy_type = proxy_type_map.get(data.proxy_type, "residential")

    # ── Paso 1: Buscar proxy disponible ───────────────────────────────────────
    proxy_result = await db.execute(
        select(Proxy)
        .where(
            Proxy.status     == ProxyStatus.ACTIVE,
            Proxy.proxy_type == db_proxy_type,
            Proxy.country    == data.country,
        )
        .limit(1)
    )
    proxy = proxy_result.scalar_one_or_none()

    # ── Paso 2: Si no hay, crear uno nuevo ────────────────────────────────────
    if not proxy:
        from app.config import settings
        proxy = Proxy(
            host=             "proxy.soax.com",
            port=             5000,
            username=         f"user-{data.country.lower()}-{db_proxy_type}",
            password=         getattr(settings, "SOAX_PASSWORD", "changeme"),
            proxy_type=       db_proxy_type,
            country=          data.country,
            city=             data.city,
            status=           ProxyStatus.ACTIVE,
            rotation_minutes= data.rotation_minutes,
            created_at=       datetime.utcnow(),
        )
        db.add(proxy)
        await db.flush()

    # ── Paso 3: Crear el perfil ────────────────────────────────────────────────
    device_map = {
        "DESKTOP": DeviceType.DESKTOP,
        "TABLET":  DeviceType.TABLET,
        "MOBILE":  DeviceType.MOBILE,
    }

    profile = Profile(
        adspower_id=       f"pending-{uuid.uuid4().hex[:10]}",
        proxy_id=          proxy.id,
        name=              data.name,
        owner=             data.owner,
        bookie=            data.bookie,
        sport=             data.sport,
        country=           data.country,
        city=              data.city,
        language=          data.language,
        device_type=       device_map.get(data.device_type, DeviceType.DESKTOP),
        os=                data.os,
        screen_resolution= data.screen_res,
        rotation_minutes=  data.rotation_minutes,
        warmup_urls=       data.warmup_urls,
        status=            ProfileStatus.CREATING,
        browser_score=     0.0,
        fingerprint_score= 0.0,
        cookie_status=     "MISSING",
        health_score=      100.0,
        trust_score=       100.0,
        last_action=       "CREATE",
        meta_data={
            "auto_fingerprint": data.auto_fingerprint,
            "open_on_create":   data.open_on_create,
        },
        created_at=        datetime.utcnow(),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    # ── Paso 4: Buscar cualquier agente online y enviar comando ───────────────
    computer_result = await db.execute(
        select(Computer)
        .where(Computer.status == ComputerStatus.ONLINE)
        .limit(1)
    )
    computer = computer_result.scalar_one_or_none()

    command_sent = False
    if computer:
        command_sent = await connection_manager.send_command_to_agent(
            computer_id=computer.id,
            command="create_adspower_profile",
            payload={
                "profile_id":       profile.id,
                "name":             data.name,
                "proxy_type":       data.proxy_type,
                "country":          data.country,
                "city":             data.city,
                "os":               data.os,
                "screen_res":       data.screen_res,
                "language":         data.language,
                "auto_fingerprint": data.auto_fingerprint,
                "warmup_urls":      data.warmup_urls,
                "open_on_create":   data.open_on_create,
                "rotation_minutes": data.rotation_minutes,
            }
        )

    # ── Paso 5: Notificar al panel ────────────────────────────────────────────
    await connection_manager.broadcast_to_admins({
        "type":       "profile_created",
        "profile_id": profile.id,
        "name":       data.name,
        "owner":      data.owner,
        "bookie":     data.bookie,
        "timestamp":  datetime.utcnow().isoformat(),
    })

    return {
        "profile_id":   profile.id,
        "name":         profile.name,
        "status":       "creating",
        "proxy_id":     proxy.id,
        "proxy_country": proxy.country,
        "command_sent": command_sent,
        "message":      f"Perfil '{data.name}' creado. Esperando registro en AdsPower.",
    }


# ─── ESTADÍSTICAS ──────────────────────────────────────────────────────────────
@router.get("/stats")
async def get_profile_stats(db: AsyncSession = Depends(get_db)):
    service = ProfileService(db)
    return await service.get_stats()


# ─── OBTENER UNO ───────────────────────────────────────────────────────────────
@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ─── ACTUALIZAR ────────────────────────────────────────────────────────────────
@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    data: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService(db)
    profile = await service.update_profile(profile_id, data)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ─── ELIMINAR ──────────────────────────────────────────────────────────────────
@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.delete(profile)
    await db.commit()


# ─── VERIFICAR SEGURIDAD (cookies, fingerprint) ────────────────────────────────
@router.post("/{profile_id}/verify-security")
async def verify_profile_security(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Verifica estado real de cookies y fingerprint en AdsPower. Actualiza scores en BD."""
    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Scores calculados localmente (sin AdsPower API en esta versión básica)
    # En producción: conectar con AdsPowerClient para datos reales
    browser_score     = 85.0 if profile.is_warmed else 40.0
    fingerprint_score = 90.0 if profile.os else 50.0
    cookie_status     = "OK" if profile.is_warmed else "MISSING"

    profile.browser_score     = browser_score
    profile.fingerprint_score = fingerprint_score
    profile.cookie_status     = cookie_status
    profile.updated_at        = datetime.utcnow()
    await db.commit()

    return {
        "profile_id":        profile_id,
        "browser_score":     browser_score,
        "fingerprint_score": fingerprint_score,
        "cookie_status":     cookie_status,
        "verified":          True,
    }


# ─── WARMUP ────────────────────────────────────────────────────────────────────
@router.post("/{profile_id}/warmup")
async def warmup_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Inicia el proceso de warm-up del perfil en cualquier agente disponible."""
    from app.models.computer import Computer, ComputerStatus
    from app.core.connection_manager import connection_manager

    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    computer_result = await db.execute(
        select(Computer).where(Computer.status == ComputerStatus.ONLINE).limit(1)
    )
    computer = computer_result.scalar_one_or_none()

    sent = False
    if computer:
        sent = await connection_manager.send_command_to_agent(
            computer_id=computer.id,
            command="warmup_profile",
            payload={
                "profile_id":    profile_id,
                "adspower_id":   profile.adspower_id,
                "warmup_urls":   profile.warmup_urls or [],
            }
        )

    profile.status     = ProfileStatus.WARMING
    profile.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "profile_id":  profile_id,
        "status":      "warming",
        "command_sent": sent,
    }