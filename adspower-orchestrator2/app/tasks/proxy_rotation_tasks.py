# app/tasks/proxy_rotation_tasks.py - ✅ CORREGIDO CON RECUPERACIÓN

"""
CORRECCIONES:
1. auto_rotate_slow_proxies_task() ahora incluye proxies FAILED
2. Nuevo método _attempt_recovery_sync() para recuperar proxies offline
3. Logs mejorados para distinguir rotación vs recuperación
"""

from celery import Task
from loguru import logger


def get_celery_app():
    from app.tasks import celery_app
    return celery_app


celery_app = get_celery_app()


@celery_app.task(name='tasks.auto_rotate_slow_proxies', bind=True)
def auto_rotate_slow_proxies_task(self: Task):
    """Dispara la rotación vía HTTP interno para aprovechar el event loop de FastAPI."""
    import httpx
    from app.config import settings

    try:
        with httpx.Client(timeout=10.0) as client:
            api_port = getattr(settings, 'API_PORT', 8000)
            r = client.post(
                f"http://localhost:{api_port}/api/v1/proxy-rotation/check-and-rotate-all"
            )
            logger.info(f"Rotación disparada: {r.status_code}")
            return r.json()
    except Exception as e:
        logger.error(f"Error disparando rotación: {e}")
        return {"error": str(e)}

def _check_and_rotate_proxy_sync(db, proxy: "Proxy") -> dict:
    """
    ✅ Versión SYNC con recuperación automática
    """
    import httpx
    import time
    import secrets
    from app.config import settings
    
    logger.info(f"🔍 Checking proxy {proxy.id}: {proxy.city}, {proxy.region}")
    
    old_latency = _ping_proxy_sync(proxy)
    
    # ✅ SI ESTÁ OFFLINE → INTENTAR RECUPERAR
    if old_latency is None:
        logger.warning(f"⚠️ Proxy {proxy.id} OFFLINE → Attempting recovery...")
        
        # Actualizar failed_checks
        proxy.total_checks = (proxy.total_checks or 0) + 1
        proxy.failed_checks = (proxy.failed_checks or 0) + 1
        
        if proxy.total_checks > 0:
            proxy.success_rate = (
                (proxy.total_checks - proxy.failed_checks) / proxy.total_checks
            ) * 100
        
        # ✅ INTENTAR RECUPERACIÓN
        recovery_result = _attempt_recovery_sync(db, proxy)
        
        if recovery_result["recovered"]:
            logger.info(
                f"✅ Proxy {proxy.id} RECOVERED: "
                f"{recovery_result['new_location']} ({recovery_result['new_latency_ms']}ms)"
            )
            return recovery_result
        else:
            # Marcar como FAILED
            proxy.status = "failed"
            return {
                "rotated": False,
                "recovered": False,
                "error": "Proxy offline and recovery failed",
                "old_latency_ms": None
            }
    
    # Actualizar success rate
    proxy.total_checks = (proxy.total_checks or 0) + 1
    
    if proxy.total_checks > 0:
        successful = proxy.total_checks - (proxy.failed_checks or 0)
        proxy.success_rate = (successful / proxy.total_checks) * 100
    
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
    
    # Generar nueva sesión
    session_id = secrets.token_urlsafe(16)
    
    new_username = (
        f"{settings.SOAX_USERNAME}-"
        f"country-ec-"
        f"city-{proxy.city.lower().replace(' ', '-') if proxy.city else 'guayaquil'}-"
        f"sessionid-{session_id}"
    )
    
    old_username = proxy.username
    old_session_id = proxy.session_id
    
    proxy.username = new_username
    proxy.session_id = session_id
    
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
    
    # Actualizar AdsPower
    success = _update_adspower_profiles_sync(db, proxy)
    
    if not success:
        logger.error("❌ AdsPower sync failed, rollback")
        proxy.username = old_username
        proxy.session_id = old_session_id
        return {
            "rotated": False,
            "error": "AdsPower sync failed",
            "old_latency_ms": old_latency
        }
    
    proxy.avg_response_time = new_latency
    proxy.status = "active"
    proxy.failed_checks = 0  # Reset
    
    logger.info(
        f"✅ Proxy {proxy.id} rotated: {old_latency}ms → {new_latency}ms"
    )
    
    return {
        "rotated": True,
        "old_latency_ms": old_latency,
        "new_latency_ms": new_latency
    }


def _attempt_recovery_sync(db, proxy: "Proxy") -> dict:
    """
    ✅ NUEVO: Intenta recuperar proxy FAILED
    """
    import secrets
    from app.config import settings
    
    logger.info(f"🔄 Attempting recovery for proxy {proxy.id}")
    
    # Generar nueva sesión en misma ciudad
    if proxy.city:
        session_id = secrets.token_urlsafe(16)
        
        new_username = (
            f"{settings.SOAX_USERNAME}-"
            f"country-ec-"
            f"city-{proxy.city.lower().replace(' ', '-')}-"
            f"sessionid-{session_id}"
        )
        
        old_username = proxy.username
        old_session_id = proxy.session_id
        old_city = proxy.city
        
        proxy.username = new_username
        proxy.session_id = session_id
        
        new_latency = _ping_proxy_sync(proxy)
        
        if new_latency is not None:
            # Actualizar AdsPower
            success = _update_adspower_profiles_sync(db, proxy)
            
            if success:
                proxy.avg_response_time = new_latency
                proxy.status = "active"
                proxy.failed_checks = 0
                
                return {
                    "recovered": True,
                    "rotated": True,
                    "new_location": f"{proxy.city}, EC",
                    "new_latency_ms": new_latency,
                    "recovery_type": "same_city"
                }
        
        # Rollback si falló
        proxy.username = old_username
        proxy.session_id = old_session_id
    
    # Si no se pudo recuperar, usar Guayaquil como fallback
    session_id = secrets.token_urlsafe(16)
    
    fallback_username = (
        f"{settings.SOAX_USERNAME}-"
        f"country-ec-"
        f"city-guayaquil-"
        f"sessionid-{session_id}"
    )
    
    old_username = proxy.username
    old_session_id = proxy.session_id
    
    proxy.username = fallback_username
    proxy.session_id = session_id
    proxy.city = "Guayaquil"
    proxy.region = "Guayas"
    
    new_latency = _ping_proxy_sync(proxy)
    
    if new_latency is not None:
        success = _update_adspower_profiles_sync(db, proxy)
        
        if success:
            proxy.avg_response_time = new_latency
            proxy.status = "active"
            proxy.failed_checks = 0
            
            return {
                "recovered": True,
                "rotated": True,
                "new_location": "Guayaquil, EC",
                "new_latency_ms": new_latency,
                "recovery_type": "fallback"
            }
    
    # No se pudo recuperar
    proxy.username = old_username
    proxy.session_id = old_session_id
    
    return {"recovered": False, "error": "All recovery attempts failed"}


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
    
    except Exception:
        return None


def _update_adspower_profiles_sync(db, proxy: "Proxy") -> bool:
    """Actualiza profiles en AdsPower (versión sync)"""
    import httpx
    from app.models.profile import Profile
    from app.config import settings
    
    profiles = db.query(Profile).filter(
        Profile.proxy_id == proxy.id
    ).all()
    
    if not profiles:
        return True
    
    logger.info(f"🔄 Updating {len(profiles)} profiles in AdsPower...")
    
    adspower_url = settings.ADSPOWER_DEFAULT_API_URL
    adspower_key = settings.ADSPOWER_DEFAULT_API_KEY
    
    if not adspower_url or not adspower_key:
        logger.error("❌ AdsPower credentials not configured")
        return False
    
    proxy_config = {
        "user_proxy_config": {
            "proxy_soft": "other",
            "proxy_type": "http",
            "proxy_host": proxy.host,
            "proxy_port": str(proxy.port),
            "proxy_user": proxy.username or "",
            "proxy_password": proxy.password or ""
        }
    }
    
    # Verificar conectividad
    is_reachable = _check_adspower_reachable_sync(adspower_url, adspower_key)
    
    if not is_reachable:
        logger.error(f"❌ AdsPower not reachable: {adspower_url}")
        return False
    
    success_count = 0
    failed_count = 0
    
    try:
        with httpx.Client(timeout=30.0) as client:
            for profile in profiles:
                try:
                    url = f"{adspower_url}/api/v1/user/update"
                    
                    payload = {
                        "user_id": profile.adspower_id,
                        **proxy_config
                    }
                    
                    response = client.post(
                        url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {adspower_key}",
                            "Content-Type": "application/json"
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("code") == 0:
                            success_count += 1
                        else:
                            failed_count += 1
                    else:
                        failed_count += 1
                
                except Exception as e:
                    logger.error(f"❌ Error: {e}")
                    failed_count += 1
    
    except Exception as e:
        logger.error(f"❌ Client error: {e}")
        return False
    
    if failed_count > 0:
        logger.error(f"⚠️ Partial update: {success_count} OK, {failed_count} failed")
        return False
    
    logger.info(f"✅ All profiles updated: {success_count}/{len(profiles)}")
    return True


def _check_adspower_reachable_sync(adspower_url: str, adspower_key: str) -> bool:
    """Verifica que AdsPower responda"""
    import httpx
    
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(
                f"{adspower_url}/api/v1/user/list",
                params={"page": 1, "page_size": 1},
                headers={
                    "Authorization": f"Bearer {adspower_key}"
                }
            )
            
            return response.status_code == 200
    
    except Exception:
        return False