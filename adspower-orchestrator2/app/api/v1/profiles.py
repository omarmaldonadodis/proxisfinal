# app/api/v1/profiles.py
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select 
from typing import Optional
from datetime import datetime 
from app.database import get_db
from app.services.profile_service import ProfileService
from app.schemas.profile import (
    ProfileCreate,
    ProfileWithProxyCreate,
    ProfileUpdate,
    ProfileResponse,
    ProfileListResponse,
    ProfileBulkCreate
)
from app.models.profile import Profile, ProfileStatus, DeviceType



router = APIRouter(prefix="/profiles", tags=["Profiles"])

@router.post("/", response_model=ProfileResponse, status_code=201)
async def create_profile(
    profile_in: ProfileCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo profile"""
    service = ProfileService(db)
    try:
        profile = await service.create_profile(profile_in)
        return profile
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bulk", status_code=202)
async def bulk_create_profiles(
    bulk_in: ProfileBulkCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Crea múltiples profiles en background"""
    from app.tasks.profile_tasks import bulk_create_profiles_task
    
    # Lanzar tarea en Celery
    task = bulk_create_profiles_task.delay(bulk_in.model_dump())
    
    return {
        "message": f"Bulk creation of {bulk_in.count} profiles started",
        "task_id": task.id
    }
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


    from app.integrations.soax_client import SOAXClient
    from app.config import settings
    import uuid

    soax = SOAXClient(
        username=settings.SOAX_USERNAME,  # "package-325401"
        password=settings.SOAX_PASSWORD,
        host=    "proxy.soax.com",
        port=    5000,
    )

    proxy_config = soax.get_proxy_config(
        proxy_type=       db_proxy_type,
        country=          data.country.lower(),
        city=             (data.city or "").lower() or None,
        session_id=       uuid.uuid4().hex[:16],
        session_lifetime= (data.rotation_minutes or 30) * 60,
    )

    proxy = Proxy(
        host=       proxy_config["host"],
        port=       proxy_config["port"],
        username=   proxy_config["username"],   # ← username completo de SOAX
        password=   proxy_config["password"],
        proxy_type= db_proxy_type,
        country=    data.country,
        city=       data.city,
        status=     ProxyStatus.ACTIVE,
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

    # ── Paso 4: Generar fingerprint completo en el servidor ───────────────────
    from app.utils.profile_generator import ProfileGenerator

    profile_config = ProfileGenerator.generate_profile(
        name=                 data.name,
        country=              data.country,
        city=                 data.city,
        device_type=          data.device_type,
        include_cookies=      True,
        include_localstorage= True
    )

    screen_res = profile_config["screen_resolution"].replace("x", "_")

    fingerprint_config = {
        "automatic_timezone":   "0",
        "timezone":             profile_config["timezone"],
        "webrtc":               "proxy",
        "location":             "ask",
        "language":             [profile_config["language"]],
        "page_language":        [profile_config["language"]],
        "ua":                   profile_config["user_agent"],
        "screen_resolution":    screen_res,
        "fonts":                ["all"],
        "canvas":               "1",
        "webgl_image":          "1",
        "webgl":                "1",
        "audio":                "1",
        "do_not_track":         "default",
        "hardware_concurrency": str(profile_config["hardware_concurrency"]),
        "device_memory":        str(profile_config["device_memory"]),
        "flash":                "block",
        "media_devices":        "1",
        "client_rects":         "1",
        "speech_voices":        "1",
    }

    user_proxy_config = {
        "proxy_soft":     "other",
        "proxy_type":     "http",
        "proxy_host":     proxy.host,
        "proxy_port":     str(proxy.port),
        "proxy_user":     proxy.username,
        "proxy_password": proxy.password or getattr(settings, "SOAX_PASSWORD", ""),
    }

    # ── Actualizar perfil en BD con datos reales del generator ────────────────
    profile.language=          profile_config["language"]
    profile.timezone=          profile_config["timezone"]
    profile.device_name=       profile_config["device_name"]
    profile.user_agent=        profile_config["user_agent"]
    profile.screen_resolution= profile_config["screen_resolution"]
    profile.viewport=          profile_config["viewport"]
    profile.pixel_ratio=       profile_config["pixel_ratio"]
    profile.hardware_concurrency= profile_config["hardware_concurrency"]
    profile.device_memory=     profile_config["device_memory"]
    profile.platform=          profile_config["platform"]
    profile.interests=         profile_config["interests"]
    await db.commit()

    # ── Paso 5: Buscar agente online y enviar comando con TODO el fingerprint ─
    computer_result = await db.execute(
        select(Computer).where(Computer.status == ComputerStatus.ONLINE).limit(1)
    )
    computer = computer_result.scalar_one_or_none()

    command_sent = False
    if computer:
        command_sent = await connection_manager.send_command_to_agent(
            computer_id=computer.id,
            command="create_adspower_profile",
            payload={
                "profile_id":         profile.id,
                "name":               data.name,
                "remark":             profile_config["remark"],
                "fingerprint_config": fingerprint_config,      # ← completo
                "user_proxy_config":  user_proxy_config,       # ← completo
                "cookies":            profile_config.get("cookies", []),
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


@router.get("/stats/summary")
async def get_profiles_stats(
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas de profiles"""
    service = ProfileService(db)
    stats = await service.get_stats()
    return stats

@router.get("/", response_model=ProfileListResponse)
async def list_profiles(
    skip:        int              = Query(0,    ge=0),
    limit:       int              = Query(100,  ge=1, le=1000),
    status:      Optional[ProfileStatus] = None,
    owner:       Optional[str]    = None,
    bookie:      Optional[str]    = None,
    cookie_status: Optional[str]  = None,
    db: AsyncSession = Depends(get_db)
):
    service = ProfileService(db)
    profiles, total = await service.list_profiles(
        skip=skip, limit=limit,
        status=status,
        owner=owner, bookie=bookie, cookie_status=cookie_status
    )
    return ProfileListResponse(total=total, items=profiles)

    

@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene profile por ID"""
    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.patch("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: int,
    profile_in: ProfileUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza profile"""
    service = ProfileService(db)
    try:
        profile = await service.update_profile(profile_id, profile_in)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return profile
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Elimina profile"""
    service = ProfileService(db)
    try:
        success = await service.delete_profile(profile_id)
        if not success:
            raise HTTPException(status_code=404, detail="Profile not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{profile_id}/warmup", status_code=202)
async def warmup_profile(
    profile_id: int,
    duration_minutes: int = Query(20, ge=5, le=120),
    db: AsyncSession = Depends(get_db)
):
    """Inicia warmup de profile"""
    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    from app.tasks.profile_tasks import warmup_profile_task
    task = warmup_profile_task.delay(profile_id, duration_minutes)
    
    return {
        "message": f"Warmup started for profile {profile_id}",
        "task_id": task.id
    }

@router.post("/{profile_id}/verify-security")
async def verify_profile_security(
    profile_id: int,
    db: AsyncSession = Depends(get_db)
):
    from app.core.connection_manager import connection_manager
    import asyncio, uuid

    service = ProfileService(db)
    profile = await service.get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if profile.adspower_id.startswith("pending"):
        raise HTTPException(status_code=400, detail="Perfil aún no creado en AdsPower")

    # ── Obtener agente online ──────────────────────────────────
    online_agents = connection_manager.get_online_agents()
    if not online_agents:
        raise HTTPException(status_code=503, detail="No hay agentes online")

    computer_id = next(iter(online_agents))

    # ── Crear Future para esperar respuesta del agente ─────────
    request_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    connection_manager._pending_proxy_checks[request_id] = future  # reusar el mismo dict

    sent = await connection_manager.send_command_to_agent(
        computer_id=computer_id,
        command="verify_profile",
        payload={
            "request_id":  request_id,
            "adspower_id": profile.adspower_id,
        }
    )

    if not sent:
        del connection_manager._pending_proxy_checks[request_id]
        raise HTTPException(status_code=503, detail="No se pudo enviar comando al agente")

    # ── Esperar respuesta (timeout 15s) ────────────────────────
    try:
        result = await asyncio.wait_for(future, timeout=15.0)
    except asyncio.TimeoutError:
        connection_manager._pending_proxy_checks.pop(request_id, None)
        raise HTTPException(status_code=504, detail="Agente no respondió a tiempo")

    # ── Calcular scores desde la respuesta ────────────────────
    fp_config         = result.get("fingerprint_config", {})
    has_cookies       = result.get("has_cookies", False)
    browser_score     = _calc_browser_score(fp_config)
    fingerprint_score = _calc_fingerprint_score(fp_config)
    cookie_status     = "OK" if has_cookies else "MISSING"

    # ── Guardar en BD ─────────────────────────────────────────
    profile.browser_score     = browser_score
    profile.fingerprint_score = fingerprint_score
    profile.cookie_status     = cookie_status
    await db.commit()

    return {
        "profile_id":        profile_id,
        "browser_score":     browser_score,
        "fingerprint_score": fingerprint_score,
        "cookie_status":     cookie_status,
        "verified":          True,
    }
    
def _calc_browser_score(fp_config: dict) -> float:
    score = 100.0
    critical = ["ua", "timezone", "language", "screen_resolution"]
    for field in critical:
        if not fp_config.get(field):
            score -= 25.0
    return max(0.0, score)

def _calc_fingerprint_score(fp_config: dict) -> float:
    score = 100.0
    fields = ["canvas", "webgl", "audio", "fonts", "hardware_concurrency", "device_memory"]
    per_field = 100.0 / len(fields)
    for field in fields:
        if not fp_config.get(field):
            score -= per_field
    return max(0.0, round(score, 1))