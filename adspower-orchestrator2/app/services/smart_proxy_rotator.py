# app/services/smart_proxy_rotator.py
"""
Sistema de Rotación Inteligente de Proxies
- Detecta IPs bloqueadas/lentas
- Rota automáticamente a ubicaciones alternativas
- Actualiza DB + AdsPower
- Monitoreo en tiempo real
"""
from typing import Optional, Dict, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from loguru import logger
import asyncio
import httpx

from app.models.proxy import Proxy, ProxyStatus
from app.models.profile import Profile
from app.models.proxy_health import ProxyHealthCheck, ProxyScore
from app.utils.geo_manager import GeoManager, GeoLocation, get_soax_username_with_geo
from app.integrations.adspower_client import AdsPowerClient
from app.integrations.soax_client import SOAXClient
from app.models.computer import Computer
from app.config import settings


class ProxyIssueType:
    """Tipos de problemas detectables"""
    TIMEOUT = "timeout"  # Timeouts frecuentes
    SLOW_LOADING = "slow_loading"  # Carga lenta (>5s)
    GEO_MISMATCH = "geo_mismatch"  # País/región incorrecta
    FUNCTIONALITY_BLOCKED = "functionality_blocked"  # Funcionalidades bloqueadas
    CAPTCHA_DETECTED = "captcha_detected"  # reCAPTCHA/Cloudflare
    BOT_DETECTED = "bot_detected"  # "Access Denied" / 403 Forbidden
    FINGERPRINT_FAILED = "fingerprint_failed"  # Fingerprint detectado
    UNAVAILABLE = "unavailable"  # No responde


class SmartProxyRotator:
    """
    Rotador Inteligente de Proxies con Auto-Recuperación
    
    Características:
    - Detecta problemas de IPs (lentas, bloqueadas, detectadas)
    - Rota automáticamente a ubicaciones alternativas
    - Actualiza DB + AdsPower
    - Monitoreo en tiempo real
    """
    
    # Thresholds de detección
    MAX_LATENCY_MS = 5000  # 5 segundos (muy lento)
    TIMEOUT_THRESHOLD = 3  # 3 timeouts consecutivos
    CAPTCHA_THRESHOLD = 2  # 2 CAPTCHAs en 1 hora
    BOT_DETECTION_THRESHOLD = 3  # 3 detecciones de bot en 24h
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.soax = SOAXClient(
            username=settings.SOAX_USERNAME,
            password=settings.SOAX_PASSWORD,
            host=settings.SOAX_HOST,
            port=settings.SOAX_PORT
        )
    
    async def detect_and_rotate_if_needed(
        self,
        proxy_id: int,
        test_urls: List[str] = None
    ) -> Dict:
        """
        Detecta problemas y rota proxy si es necesario
        
        Args:
            proxy_id: ID del proxy a verificar
            test_urls: URLs para probar funcionalidad
        
        Returns:
            {
                "rotated": True/False,
                "issues_detected": [...],
                "new_proxy_id": 123,  # Si se rotó
                "new_location": "Guayaquil, Guayas"
            }
        """
        
        # Obtener proxy
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        
        if not proxy:
            return {"error": "Proxy not found"}
        
        logger.info(f"Checking proxy {proxy_id}: {proxy.country}/{proxy.city}")
        
        # 1. Detectar problemas
        issues = await self._detect_proxy_issues(proxy, test_urls)
        
        if not issues:
            logger.info(f"✓ Proxy {proxy_id} is healthy")
            return {
                "rotated": False,
                "issues_detected": [],
                "message": "Proxy is healthy"
            }
        
        # 2. Problemas detectados - rotar
        logger.warning(
            f"⚠️  Proxy {proxy_id} has issues: {', '.join(issues)}. Rotating..."
        )
        
        # 3. Rotar a ubicación alternativa
        new_proxy = await self._rotate_to_alternative_location(proxy, issues)
        
        if not new_proxy:
            return {
                "rotated": False,
                "issues_detected": issues,
                "error": "No alternative locations available"
            }
        
        # 4. Actualizar profiles que usan este proxy
        await self._update_profiles_proxy(
            old_proxy_id=proxy.id,
            new_proxy_id=new_proxy.id
        )
        
        return {
            "rotated": True,
            "issues_detected": issues,
            "old_proxy_id": proxy.id,
            "old_location": f"{proxy.city}, {proxy.region or proxy.country}",
            "new_proxy_id": new_proxy.id,
            "new_location": f"{new_proxy.city}, {new_proxy.region or new_proxy.country}",
            "message": f"Rotated to {new_proxy.city}"
        }
    
    async def _detect_proxy_issues(
        self,
        proxy: Proxy,
        test_urls: List[str] = None
    ) -> List[str]:
        """
        Detecta problemas del proxy
        
        Returns:
            Lista de issues detectados (vacía si todo OK)
        """
        
        issues = []
        
        # 1. Verificar score del proxy
        result = await self.db.execute(
            select(ProxyScore).where(ProxyScore.proxy_id == proxy.id)
        )
        score = result.scalar_one_or_none()
        
        if score:
            # Blacklisted
            if score.is_blacklisted:
                issues.append(ProxyIssueType.UNAVAILABLE)
                return issues  # No seguir chequeando
            
            # Latencia muy alta
            if score.avg_latency and score.avg_latency > self.MAX_LATENCY_MS:
                issues.append(ProxyIssueType.SLOW_LOADING)
            
            # Uptime bajo
            if score.uptime_percentage < 70:
                issues.append(ProxyIssueType.TIMEOUT)
            
            # Geo mismatch frecuente
            if score.geo_mismatch_count > 3:
                issues.append(ProxyIssueType.GEO_MISMATCH)
        
        # 2. Verificar health checks recientes
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        result = await self.db.execute(
            select(ProxyHealthCheck)
            .where(
                and_(
                    ProxyHealthCheck.proxy_id == proxy.id,
                    ProxyHealthCheck.checked_at >= one_hour_ago
                )
            )
            .order_by(ProxyHealthCheck.checked_at.desc())
            .limit(10)
        )
        
        recent_checks = list(result.scalars().all())
        
        if recent_checks:
            # Contar fallos
            failed_checks = sum(
                1 for check in recent_checks
                if check.status in ["failed", "timeout", "blocked"]
            )
            
            if failed_checks >= self.TIMEOUT_THRESHOLD:
                if ProxyIssueType.TIMEOUT not in issues:
                    issues.append(ProxyIssueType.TIMEOUT)
        
        # 3. Test funcionalidad (si se proporcionan URLs)
        if test_urls and not issues:
            # Solo si no hay issues obvios
            functionality_ok = await self._test_proxy_functionality(proxy, test_urls)
            
            if not functionality_ok:
                issues.append(ProxyIssueType.FUNCTIONALITY_BLOCKED)
        
        return issues
    
    async def _test_proxy_functionality(
        self,
        proxy: Proxy,
        test_urls: List[str]
    ) -> bool:
        """
        Prueba funcionalidad del proxy en sitios reales
        
        Detecta:
        - Timeouts
        - Carga lenta
        - Bloqueos (403, Cloudflare, reCAPTCHA)
        
        Returns:
            True si funciona OK, False si hay problemas
        """
        
        proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
        
        for url in test_urls:
            try:
                import time
                start = time.time()
                
                async with httpx.AsyncClient(
                    proxies={"http://": proxy_url, "https://": proxy_url},
                    timeout=10.0,
                    follow_redirects=True
                ) as client:
                    response = await client.get(url)
                    
                    elapsed = (time.time() - start) * 1000
                    
                    # Timeout/lento
                    if elapsed > self.MAX_LATENCY_MS:
                        logger.warning(f"Slow loading: {elapsed:.0f}ms on {url}")
                        return False
                    
                    # Bloqueos comunes
                    if response.status_code in [403, 429]:
                        logger.warning(f"Blocked: {response.status_code} on {url}")
                        return False
                    
                    # Cloudflare/reCAPTCHA
                    content = response.text.lower()
                    if "cloudflare" in content or "recaptcha" in content or "captcha" in content:
                        logger.warning(f"CAPTCHA detected on {url}")
                        return False
                    
                    # Bot detection patterns
                    if "access denied" in content or "bot detected" in content:
                        logger.warning(f"Bot detection on {url}")
                        return False
            
            except httpx.TimeoutException:
                logger.warning(f"Timeout on {url}")
                return False
            
            except Exception as e:
                logger.error(f"Error testing {url}: {e}")
                return False
        
        return True
    
    async def _rotate_to_alternative_location(
        self,
        current_proxy: Proxy,
        issues: List[str]
    ) -> Optional[Proxy]:
        """
        Rota a ubicación alternativa
        
        Estrategia:
        1. Obtener ubicación actual
        2. Generar fallbacks geográficos
        3. Probar disponibilidad de cada ubicación
        4. Crear nuevo proxy con primera ubicación disponible
        
        Returns:
            Nuevo proxy o None si falla
        """
        
        # 1. Ubicación actual
        current_location = GeoManager.create_location(
            country=current_proxy.country,
            region=current_proxy.region,
            city=current_proxy.city
        )
        
        # 2. Ciudades ya probadas (blacklisted o con problemas)
        result = await self.db.execute(
            select(Proxy.city)
            .where(
                and_(
                    Proxy.country == current_proxy.country,
                    Proxy.status == ProxyStatus.FAILED
                )
            )
        )
        
        failed_cities = [row[0] for row in result.all() if row[0]]
        
        # 3. Generar fallbacks
        fallback_locations = GeoManager.get_fallback_locations(
            current_location=current_location,
            exclude_cities=failed_cities
        )
        
        logger.info(
            f"Testing {len(fallback_locations)} alternative locations "
            f"(excluding {len(failed_cities)} failed cities)"
        )
        
        # 4. Probar cada ubicación hasta encontrar una disponible
        for location in fallback_locations:
            logger.info(f"Testing: {location.city}, {location.region}")
            
            # Generar configuración SOAX
            proxy_config = self.soax.get_proxy_config(
                proxy_type=current_proxy.proxy_type,
                country=location.country,
                # ✅ NUEVO: Enviar region Y city
                region=location.region_code,
                city=location.city_code,
                session_lifetime=current_proxy.session_lifetime or 3600
            )
            
            # Test disponibilidad
            test_result = await self.soax.test_proxy(proxy_config, timeout=10.0)
            
            if test_result["success"]:
                # ✅ Ubicación disponible - crear proxy
                logger.info(f"✓ Found available location: {location.city}")
                
                new_proxy = Proxy(
                    proxy_type=current_proxy.proxy_type,
                    host=proxy_config["host"],
                    port=proxy_config["port"],
                    username=proxy_config["username"],
                    password=proxy_config["password"],
                    country=location.country,
                    region=location.region,
                    city=location.city,
                    session_id=proxy_config["session_id"],
                    session_lifetime=current_proxy.session_lifetime,
                    sticky_session=True,
                    status=ProxyStatus.ACTIVE,
                    is_available=True,
                    detected_ip=test_result.get("ip"),
                    detected_country=test_result.get("country"),
                    detected_city=test_result.get("city"),
                    avg_response_time=test_result.get("response_time_ms"),
                    total_checks=1,
                    success_rate=100.0
                )
                
                self.db.add(new_proxy)
                
                # Marcar proxy viejo como failed
                current_proxy.status = ProxyStatus.FAILED
                current_proxy.is_available = False
                
                await self.db.commit()
                await self.db.refresh(new_proxy)
                
                return new_proxy
            
            else:
                logger.warning(f"✗ Not available: {location.city}")
                await asyncio.sleep(1)  # Rate limiting
        
        # No se encontró ubicación disponible
        logger.error("No alternative locations available")
        return None
    
    async def _update_profiles_proxy(
        self,
        old_proxy_id: int,
        new_proxy_id: int
    ) -> int:
        """
        Actualiza profiles que usan el proxy viejo
        
        Acciones:
        1. Actualizar DB (profile.proxy_id)
        2. Actualizar AdsPower (user_proxy_config)
        
        Returns:
            Número de profiles actualizados
        """
        
        # Obtener nuevo proxy
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == new_proxy_id)
        )
        new_proxy = result.scalar_one_or_none()
        
        if not new_proxy:
            logger.error(f"New proxy {new_proxy_id} not found")
            return 0
        
        # Obtener profiles que usan el proxy viejo
        result = await self.db.execute(
            select(Profile).where(Profile.proxy_id == old_proxy_id)
        )
        
        profiles = list(result.scalars().all())
        
        if not profiles:
            logger.info("No profiles using this proxy")
            return 0
        
        logger.info(f"Updating {len(profiles)} profiles with new proxy")
        
        updated_count = 0
        
        for profile in profiles:
            try:
                # 1. Actualizar en DB
                profile.proxy_id = new_proxy_id
                
                # 2. Actualizar en AdsPower
                result = await self.db.execute(
                    select(Computer).where(Computer.id == profile.computer_id)
                )
                computer = result.scalar_one_or_none()
                
                if computer:
                    adspower_client = AdsPowerClient(
                        api_url=computer.adspower_api_url,
                        api_key=computer.adspower_api_key
                    )
                    
                    # Configuración de proxy para AdsPower
                    proxy_type_map = {
                        "http": "http",
                        "https": "https",
                        "socks5": "socks5",
                        "mobile": "http",
                        "residential": "http"
                    }
                    
                    proxy_config = {
                        "user_proxy_config": {
                            "proxy_soft": "other",
                            "proxy_type": proxy_type_map.get(new_proxy.proxy_type, "http"),
                            "proxy_host": new_proxy.host,
                            "proxy_port": new_proxy.port,
                            "proxy_user": new_proxy.username,
                            "proxy_password": new_proxy.password
                        }
                    }
                    
                    # Actualizar en AdsPower
                    success = await adspower_client.update_profile(
                        profile_id=profile.adspower_id,
                        profile_data=proxy_config
                    )
                    
                    if success:
                        updated_count += 1
                        logger.info(
                            f"✓ Profile {profile.id} updated: "
                            f"New location: {new_proxy.city}, {new_proxy.region}"
                        )
                    else:
                        logger.error(f"✗ Failed to update profile {profile.id} in AdsPower")
            
            except Exception as e:
                logger.error(f"Error updating profile {profile.id}: {e}")
        
        # Commit cambios en DB
        await self.db.commit()
        
        logger.info(f"Updated {updated_count}/{len(profiles)} profiles")
        
        return updated_count
    
    async def scan_and_rotate_all_proxies(
        self,
        test_urls: List[str] = None
    ) -> Dict:
        """
        Escanea TODOS los proxies activos y rota los problemáticos
        
        Útil para:
        - Mantenimiento programado
        - Detección masiva de IPs quemadas
        
        Returns:
            {
                "total_scanned": 50,
                "rotated": 12,
                "healthy": 38
            }
        """
        
        # Obtener todos los proxies activos
        result = await self.db.execute(
            select(Proxy).where(
                and_(
                    Proxy.is_available == True,
                    Proxy.status == ProxyStatus.ACTIVE
                )
            )
        )
        
        proxies = list(result.scalars().all())
        
        logger.info(f"Scanning {len(proxies)} active proxies...")
        
        stats = {
            "total_scanned": len(proxies),
            "rotated": 0,
            "healthy": 0,
            "errors": 0
        }
        
        for proxy in proxies:
            try:
                result = await self.detect_and_rotate_if_needed(
                    proxy_id=proxy.id,
                    test_urls=test_urls
                )
                
                if result.get("rotated"):
                    stats["rotated"] += 1
                else:
                    stats["healthy"] += 1
            
            except Exception as e:
                logger.error(f"Error scanning proxy {proxy.id}: {e}")
                stats["errors"] += 1
            
            # Rate limiting
            await asyncio.sleep(2)
        
        logger.info(
            f"Scan complete: {stats['rotated']} rotated, "
            f"{stats['healthy']} healthy, {stats['errors']} errors"
        )
        
        return stats


# ========================================
# TAREA CELERY PARA AUTO-ROTACIÓN
# ========================================

from app.tasks import celery_app

@celery_app.task(name='tasks.auto_rotate_problematic_proxies')
def auto_rotate_problematic_proxies_task():
    """
    Tarea automática que detecta y rota proxies problemáticos
    Se ejecuta cada 30 minutos
    """
    
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _rotate():
        from app.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            rotator = SmartProxyRotator(db)
            
            # Test URLs comunes (ajusta según tus necesidades)
            test_urls = [
                "https://www.google.com",
                "https://www.ecuabet.com",  # ✅ Tu caso de uso
            ]
            
            results = await rotator.scan_and_rotate_all_proxies(test_urls=test_urls)
            
            logger.info(f"Auto-rotation completed: {results}")
            
            return results
    
    try:
        return loop.run_until_complete(_rotate())
    finally:
        pass