# app/tasks/proxy_rotation_tasks.py - ✅ CORREGIDO PARA CELERY

"""
CORRECCIÓN CRÍTICA:
- Celery trabaja en contexto síncrono (workers fork/multiprocess)
- SQLAlchemy async requiere greenlet/asyncio context
- Solución: Usar sync engine en lugar de async
"""

from celery import Task
from loguru import logger


def get_celery_app():
    from app.tasks import celery_app
    return celery_app


celery_app = get_celery_app()


@celery_app.task(name='tasks.auto_rotate_slow_proxies', bind=True)
def auto_rotate_slow_proxies_task(self: Task):
    """
    ⏰ Rotación automática cada 15 minutos
    
    ✅ CORRECCIÓN: Usar sesión SYNC de SQLAlchemy (no async)
    """
    
    logger.info("🔄 Starting automatic proxy rotation")
    
    # ✅ USAR SYNC SESSION (NO ASYNC)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    from app.models.proxy import Proxy, ProxyStatus
    
    # Crear engine síncrono
    sync_engine = create_engine(
        settings.DATABASE_SYNC_URL,
        pool_pre_ping=True
    )
    
    SyncSession = sessionmaker(bind=sync_engine)
    
    try:
        with SyncSession() as db:
            # Obtener proxies activos
            proxies = db.query(Proxy).filter(
                Proxy.status == ProxyStatus.ACTIVE
            ).all()
            
            logger.info(f"Found {len(proxies)} active proxies to check")
            
            stats = {
                "total": len(proxies),
                "optimal": 0,
                "rotated": 0,
                "failed": 0
            }
            
            # Procesar cada proxy
            for proxy in proxies:
                try:
                    # ✅ Llamar versión SYNC del servicio
                    result = _check_and_rotate_proxy_sync(db, proxy)
                    
                    if result.get("rotated"):
                        stats["rotated"] += 1
                    elif result.get("error"):
                        stats["failed"] += 1
                    else:
                        stats["optimal"] += 1
                    
                    db.commit()
                
                except Exception as e:
                    logger.error(f"Error processing proxy {proxy.id}: {e}")
                    db.rollback()
                    stats["failed"] += 1
            
            logger.info(
                f"✅ Rotation complete: "
                f"{stats['rotated']} rotated, "
                f"{stats['optimal']} optimal, "
                f"{stats['failed']} failed"
            )
            
            return stats
    
    except Exception as e:
        logger.error(f"❌ Rotation task failed: {e}")
        return {
            "error": str(e),
            "total": 0,
            "rotated": 0,
            "failed": 0
        }


def _check_and_rotate_proxy_sync(db, proxy: "Proxy") -> dict:
    """
    ✅ Versión SYNC de check_and_rotate_proxy
    
    Esta función trabaja con SQLAlchemy sync session (no async)
    """
    import httpx
    import time
    import secrets
    from app.config import settings
    
    logger.info(f"🔍 Checking proxy {proxy.id}: {proxy.city}, {proxy.region}")
    
    # 1. PING PROXY
    old_latency = _ping_proxy_sync(proxy)
    
    if old_latency is None:
        logger.error(f"❌ Proxy {proxy.id} OFFLINE")
        proxy.status = "failed"
        return {
            "rotated": False,
            "error": "Proxy offline",
            "old_latency_ms": None
        }
    
    # 2. VERIFICAR SI ES NECESARIO ROTAR
    MAX_LATENCY_MS = 2000
    
    if old_latency < MAX_LATENCY_MS:
        logger.info(f"✅ Proxy {proxy.id} optimal ({old_latency}ms)")
        proxy.avg_response_time = old_latency
        proxy.status = "active"
        return {
            "rotated": False,
            "reason": "optimal",
            "old_latency_ms": old_latency
        }
    
    logger.warning(f"⚠️ Proxy {proxy.id} slow ({old_latency}ms) → Rotating...")
    
    # 3. GENERAR NUEVA SESIÓN
    session_id = secrets.token_urlsafe(16)
    
    # Construir nuevo username SOAX
    new_username = (
        f"{settings.SOAX_USERNAME}-"
        f"country-ec-"
        f"city-{proxy.city.lower().replace(' ', '-') if proxy.city else 'guayaquil'}-"
        f"sessionid-{session_id}"
    )
    
    # 4. GUARDAR VALORES ANTIGUOS (para rollback)
    old_username = proxy.username
    old_session_id = proxy.session_id
    
    # 5. ACTUALIZAR PROXY
    proxy.username = new_username
    proxy.session_id = session_id
    
    # 6. VERIFICAR NUEVA SESIÓN
    new_latency = _ping_proxy_sync(proxy)
    
    if new_latency is None:
        logger.error("❌ New session failed, rollback")
        proxy.username = old_username
        proxy.session_id = old_session_id
        return {
            "rotated": False,
            "error": "New session failed",
            "old_latency_ms": old_latency
        }
    
    # 7. ACTUALIZAR PROFILES EN ADSPOWER
    success = _update_adspower_profiles_sync(db, proxy)
    
    if not success:
        logger.error("❌ AdsPower update failed, rollback")
        proxy.username = old_username
        proxy.session_id = old_session_id
        return {
            "rotated": False,
            "error": "AdsPower sync failed",
            "old_latency_ms": old_latency
        }
    
    # 8. COMMIT CAMBIOS
    proxy.avg_response_time = new_latency
    proxy.status = "active"
    
    logger.info(
        f"✅ Proxy {proxy.id} rotated: "
        f"{old_latency}ms → {new_latency}ms"
    )
    
    return {
        "rotated": True,
        "old_latency_ms": old_latency,
        "new_latency_ms": new_latency,
        "improvement_ms": old_latency - new_latency
    }


def _ping_proxy_sync(proxy: "Proxy") -> int | None:
    """Ping síncrono de proxy"""
    import httpx
    import time
    
    try:
        proxy_url = (
            f"http://{proxy.username}:{proxy.password}"
            f"@{proxy.host}:{proxy.port}"
        )
        
        start = time.time()
        
        with httpx.Client(
            proxies={"http://": proxy_url, "https://": proxy_url},
            timeout=10.0
        ) as client:
            response = client.get("https://api.ipify.org?format=json")
            
            if response.status_code == 200:
                latency_ms = int((time.time() - start) * 1000)
                return latency_ms
        
        return None
    
    except Exception as e:
        logger.debug(f"Ping failed: {e}")
        return None


def _update_adspower_profiles_sync(db, proxy: "Proxy") -> bool:
    """
    ✅ Actualiza profiles en AdsPower (versión sync)
    
    Formato según docs: https://localapi-doc-en.adspower.com/docs/Update-Profile-Info-V2
    """
    import httpx
    from app.models.profile import Profile
    from app.models.computer import Computer
    
    # Obtener profiles asociados a este proxy
    profiles = db.query(Profile).filter(
        Profile.proxy_id == proxy.id
    ).all()
    
    if not profiles:
        logger.info(f"ℹ️ Proxy {proxy.id} has no profiles")
        return True
    
    logger.info(f"🔄 Updating {len(profiles)} profiles in AdsPower...")
    
    # ✅ FORMATO EXACTO según documentación
    proxy_config = {
        "user_proxy_config": {
            "proxy_soft": "other",
            "proxy_type": "http",
            "proxy_host": proxy.host,
            "proxy_port": str(proxy.port),  # ⚠️ STRING según docs
            "proxy_user": proxy.username or "",
            "proxy_password": proxy.password or ""
        }
    }
    
    # Agrupar por computer
    profiles_by_computer = {}
    for profile in profiles:
        if profile.computer_id not in profiles_by_computer:
            profiles_by_computer[profile.computer_id] = []
        profiles_by_computer[profile.computer_id].append(profile)
    
    success_count = 0
    failed_count = 0
    
    for computer_id, computer_profiles in profiles_by_computer.items():
        try:
            # Obtener computer
            computer = db.query(Computer).filter(
                Computer.id == computer_id
            ).first()
            
            if not computer:
                logger.warning(f"⚠️ Computer {computer_id} not found")
                failed_count += len(computer_profiles)
                continue
            
            # Verificar conectividad primero
            is_reachable = _check_adspower_reachable_sync(computer)
            
            if not is_reachable:
                logger.error(
                    f"❌ AdsPower not reachable: {computer.ip_address}"
                )
                failed_count += len(computer_profiles)
                continue
            
            # Actualizar cada profile
            with httpx.Client(timeout=30.0) as client:
                for profile in computer_profiles:
                    try:
                        url = f"{computer.adspower_api_url}/api/v1/user/update"
                        
                        payload = {
                            "user_id": profile.adspower_id,
                            **proxy_config
                        }
                        
                        logger.info(f"📤 Updating profile {profile.adspower_id}")
                        
                        response = client.post(
                            url,
                            json=payload,
                            headers={
                                "Authorization": f"Bearer {computer.adspower_api_key}",
                                "Content-Type": "application/json"
                            }
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            if data.get("code") == 0:
                                logger.info(f"✅ Profile {profile.id} updated")
                                success_count += 1
                            else:
                                logger.error(
                                    f"❌ AdsPower error: {data.get('msg')}"
                                )
                                failed_count += 1
                        else:
                            logger.error(f"❌ HTTP {response.status_code}")
                            failed_count += 1
                    
                    except httpx.TimeoutException:
                        logger.error(f"⏱️ Timeout updating profile {profile.id}")
                        failed_count += 1
                    
                    except Exception as e:
                        logger.error(f"❌ Error: {e}")
                        failed_count += 1
        
        except Exception as e:
            logger.error(f"❌ Computer {computer_id} error: {e}")
            failed_count += len(computer_profiles)
    
    if failed_count > 0:
        logger.error(f"⚠️ Partial update: {success_count} OK, {failed_count} failed")
        return False
    
    logger.info(f"✅ All profiles updated: {success_count}/{len(profiles)}")
    return True


def _check_adspower_reachable_sync(computer: "Computer") -> bool:
    """Verifica que AdsPower responda"""
    import httpx
    
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                f"{computer.adspower_api_url}/api/v1/user/list",
                params={"page": 1, "page_size": 1},
                headers={
                    "Authorization": f"Bearer {computer.adspower_api_key}"
                }
            )
            
            if response.status_code == 200:
                logger.debug(f"✅ AdsPower reachable: {computer.ip_address}")
                return True
            else:
                logger.warning(
                    f"⚠️ AdsPower returned {response.status_code}"
                )
                return False
    
    except httpx.TimeoutException:
        logger.error(f"⏱️ Timeout checking AdsPower: {computer.ip_address}")
        return False
    
    except Exception as e:
        logger.error(f"❌ Error checking AdsPower: {e}")
        return False