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
    """Rotador Inteligente con selección por LATENCIA"""
    
    # Thresholds
    MAX_LATENCY_MS = 3000
    TIMEOUT_THRESHOLD = 3
    
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
        """Detecta problemas y rota a la IP con MEJOR LATENCIA"""
        
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        
        if not proxy:
            return {"error": "Proxy not found"}
        
        logger.info(f"🔍 Checking proxy {proxy_id}: {proxy.country}/{proxy.city}")
        
        # 1. Detectar problemas
        issues = await self._detect_proxy_issues(proxy, test_urls)
        
        if not issues:
            logger.info(f"✓ Proxy {proxy_id} is healthy")
            return {
                "rotated": False,
                "issues_detected": [],
                "message": "Proxy is healthy"
            }
        
        logger.warning(f"⚠️  Proxy {proxy_id} has issues: {', '.join(issues)}")
        
        # 2. Rotar a ubicación ÓPTIMA
        new_proxy = await self._rotate_to_optimal_location(proxy, issues)
        
        if not new_proxy:
            return {
                "rotated": False,
                "issues_detected": issues,
                "error": "No optimal locations available"
            }
        
        # 3. Actualizar profiles (DB + AdsPower)
        updated_count = await self._update_profiles_proxy(
            old_proxy_id=proxy.id,
            new_proxy_id=new_proxy.id
        )
        
        logger.info(
            f"✅ Rotated {updated_count} profiles: "
            f"{proxy.city} ({proxy.estimated_latency_ms or 'N/A'}ms) → "
            f"{new_proxy.city} ({new_proxy.estimated_latency_ms or 'N/A'}ms)"
        )
        
        return {
            "rotated": True,
            "issues_detected": issues,
            "old_proxy_id": proxy.id,
            "old_location": f"{proxy.city}, {proxy.region or proxy.country}",
            "old_latency_ms": getattr(proxy, 'estimated_latency_ms', None),
            "new_proxy_id": new_proxy.id,
            "new_location": f"{new_proxy.city}, {new_proxy.region or new_proxy.country}",
            "new_latency_ms": getattr(new_proxy, 'estimated_latency_ms', None),
            "profiles_updated": updated_count,
            "message": f"Rotated to optimal location: {new_proxy.city}"
        }
    
    async def _detect_proxy_issues(
        self,
        proxy: Proxy,
        test_urls: List[str] = None
    ) -> List[str]:
        """Detecta problemas del proxy"""
        
        issues = []
        
        # 1. Verificar score
        from app.models.proxy_health import ProxyScore
        
        result = await self.db.execute(
            select(ProxyScore).where(ProxyScore.proxy_id == proxy.id)
        )
        score = result.scalar_one_or_none()
        
        if score:
            if score.is_blacklisted:
                issues.append("unavailable")
                return issues
            
            if score.avg_latency and score.avg_latency > self.MAX_LATENCY_MS:
                issues.append("slow_loading")
            
            if score.uptime_percentage < 70:
                issues.append("timeout")
        
        # 2. Test funcionalidad si hay URLs
        if test_urls and not issues:
            functionality_ok = await self._test_proxy_functionality(proxy, test_urls)
            if not functionality_ok:
                issues.append("functionality_blocked")
        
        return issues
    
    async def _test_proxy_functionality(
        self,
        proxy: Proxy,
        test_urls: List[str]
    ) -> bool:
        """Prueba funcionalidad del proxy"""
        
        proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
        
        for url in test_urls:
            try:
                start = time.time()
                
                async with httpx.AsyncClient(
                    proxies={"http://": proxy_url, "https://": proxy_url},
                    timeout=10.0,
                    follow_redirects=True
                ) as client:
                    response = await client.get(url)
                    
                    elapsed = (time.time() - start) * 1000
                    
                    if elapsed > self.MAX_LATENCY_MS:
                        logger.warning(f"Slow loading: {elapsed:.0f}ms on {url}")
                        return False
                    
                    if response.status_code in [403, 429]:
                        logger.warning(f"Blocked: {response.status_code} on {url}")
                        return False
                    
                    content = response.text.lower()
                    if "cloudflare" in content or "recaptcha" in content:
                        logger.warning(f"CAPTCHA detected on {url}")
                        return False
            
            except httpx.TimeoutException:
                logger.warning(f"Timeout on {url}")
                return False
            except Exception as e:
                logger.error(f"Error testing {url}: {e}")
                return False
        
        return True
    
    async def _rotate_to_optimal_location(
        self,
        current_proxy: Proxy,
        issues: List[str]
    ) -> Optional[Proxy]:
        """
        🎯 Rota a ubicación ÓPTIMA (menor latencia)
        """
        
        # Obtener ciudades ya fallidas
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
        
        # 🎯 Obtener ubicación ÓPTIMA (mejor latencia)
        optimal_location = GeoManager.get_optimal_location(
            country=current_proxy.country,
            exclude_cities=failed_cities + [current_proxy.city]
        )
        
        logger.info(
            f"🎯 Testing optimal location: {optimal_location.city} "
            f"(est. latency: {optimal_location.estimated_latency_ms}ms)"
        )
        
        # Generar configuración SOAX
        proxy_config = self.soax.get_proxy_config(
            proxy_type=current_proxy.proxy_type,
            country=optimal_location.country,
            region=optimal_location.region_code,
            city=optimal_location.city_code,
            session_lifetime=current_proxy.session_lifetime or 3600
        )
        
        # Test disponibilidad
        test_result = await self.soax.test_proxy(proxy_config, timeout=10.0)
        
        if test_result["success"]:
            logger.info(f"✓ Optimal location available: {optimal_location.city}")
            
            # Crear nuevo proxy
            new_proxy = Proxy(
                proxy_type=current_proxy.proxy_type,
                host=proxy_config["host"],
                port=proxy_config["port"],
                username=proxy_config["username"],
                password=proxy_config["password"],
                country=optimal_location.country,
                region=optimal_location.region,
                city=optimal_location.city,
                session_id=proxy_config["session_id"],
                session_lifetime=current_proxy.session_lifetime,
                sticky_session=True,
                status=ProxyStatus.ACTIVE,
                is_available=True,
                detected_ip=test_result.get("ip"),
                detected_country=test_result.get("country"),
                detected_city=test_result.get("city"),
                avg_response_time=test_result.get("latency_ms"),
                total_checks=1,
                success_rate=100.0
            )
            
            # ✅ Agregar latencia estimada como atributo
            setattr(new_proxy, 'estimated_latency_ms', optimal_location.estimated_latency_ms)
            
            self.db.add(new_proxy)
            
            # Marcar proxy viejo como failed
            current_proxy.status = ProxyStatus.FAILED
            current_proxy.is_available = False
            
            await self.db.commit()
            await self.db.refresh(new_proxy)
            
            return new_proxy
        
        logger.error(f"✗ Optimal location not available: {optimal_location.city}")
        return None
    
    async def _update_profiles_proxy(
        self,
        old_proxy_id: int,
        new_proxy_id: int
    ) -> int:
        """
        ✅ ACTUALIZA PROFILES EN DB + ADSPOWER
        Usa el endpoint correcto de AdsPower API
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
        
        # ✅ Mapeo correcto de tipos de proxy para AdsPower
        proxy_type_map = {
            "http": "http",
            "https": "https",
            "socks5": "socks5",
            "mobile": "http",  # SOAX mobile usa HTTP
            "residential": "http"  # SOAX residential usa HTTP
        }
        
        for profile in profiles:
            try:
                # 1. Actualizar en DB
                profile.proxy_id = new_proxy_id
                
                # 2. Obtener computer del profile
                result = await self.db.execute(
                    select(Computer).where(Computer.id == profile.computer_id)
                )
                computer = result.scalar_one_or_none()
                
                if not computer:
                    logger.error(f"Computer {profile.computer_id} not found")
                    continue
                
                # 3. Crear cliente AdsPower
                adspower_client = AdsPowerClient(
                    api_url=computer.adspower_api_url,
                    api_key=computer.adspower_api_key
                )
                
                # 4. ✅ Configuración correcta del proxy para AdsPower
                # IMPORTANTE: Usar el endpoint /api/v1/user/update
                proxy_config = {
                    "user_proxy_config": {
                        "proxy_soft": "other",
                        "proxy_type": proxy_type_map.get(new_proxy.proxy_type, "http"),
                        "proxy_host": new_proxy.host,
                        "proxy_port": str(new_proxy.port),  # ✅ Convertir a string
                        "proxy_user": new_proxy.username or "",
                        "proxy_password": new_proxy.password or ""
                    }
                }
                
                logger.debug(
                    f"Updating profile {profile.adspower_id} proxy: "
                    f"{new_proxy.username}@{new_proxy.host}:{new_proxy.port}"
                )
                
                # 5. ✅ Actualizar en AdsPower
                success = await adspower_client.update_profile(
                    profile_id=profile.adspower_id,
                    profile_data=proxy_config
                )
                
                if success:
                    updated_count += 1
                    logger.info(
                        f"✓ Profile {profile.id} ({profile.adspower_id}) updated: "
                        f"{new_proxy.city}, {new_proxy.region}"
                    )
                else:
                    logger.error(
                        f"✗ Failed to update profile {profile.id} in AdsPower"
                    )
            
            except Exception as e:
                logger.error(f"Error updating profile {profile.id}: {e}")
        
        # Commit cambios en DB
        await self.db.commit()
        
        logger.info(f"✅ Updated {updated_count}/{len(profiles)} profiles successfully")
        
        return updated_count
    
    async def scan_and_rotate_all_proxies(
        self,
        test_urls: List[str] = None
    ) -> Dict:
        """Escanea todos los proxies y rota los problemáticos"""
        
        result = await self.db.execute(
            select(Proxy).where(
                and_(
                    Proxy.is_available == True,
                    Proxy.status == ProxyStatus.ACTIVE
                )
            )
        )
        
        proxies = list(result.scalars().all())
        
        logger.info(f"🔍 Scanning {len(proxies)} active proxies...")
        
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
            f"✅ Scan complete: {stats['rotated']} rotated, "
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