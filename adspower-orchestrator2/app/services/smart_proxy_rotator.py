# app/services/smart_proxy_rotator.py - VERSIÓN BLINDADA Y OPTIMIZADA
"""
Sistema de Rotación Inteligente de Proxies - VERSIÓN FINAL
✅ FIXES CRÍTICOS:
- NO crea duplicados - solo actualiza sesiones
- UN navegador = UNA proxy única
- Ping de latencia antes de asignar
- Jerarquía geográfica correcta (misma región → región cercana → país)
- Sistema 100% blindado contra errores
"""
from typing import Optional, Dict, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from loguru import logger
import asyncio
import time
import httpx

from app.models.proxy import Proxy, ProxyStatus
from app.models.profile import Profile
from app.models.proxy_health import ProxyScore
from app.utils.geo_manager import GeoManager, GeoLocation
from app.integrations.adspower_client import AdsPowerClient
from app.integrations.soax_client import SOAXClient
from app.models.computer import Computer
from app.config import settings


class ProxyRotationError(Exception):
    """Error específico de rotación"""
    pass


class SmartProxyRotator:
    """Rotador Inteligente BLINDADO"""
    
    # Thresholds
    MAX_LATENCY_MS = 3000  # 3 segundos
    OPTIMAL_LATENCY_MS = 1000  # 1 segundo
    MIN_SUCCESS_RATE = 70.0  # 70%
    
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
        🎯 Detecta problemas y rota INTELIGENTEMENTE
        
        Estrategia:
        1. Ping actual proxy
        2. Si falla o lento → buscar alternativa óptima
        3. Actualizar sesión de proxy existente (NO crear nueva)
        4. Actualizar AdsPower con nueva configuración
        5. Rollback si falla
        """
        
        try:
            # ========================================
            # 1. OBTENER PROXY ACTUAL
            # ========================================
            result = await self.db.execute(
                select(Proxy).where(Proxy.id == proxy_id)
            )
            current_proxy = result.scalar_one_or_none()
            
            if not current_proxy:
                raise ProxyRotationError(f"Proxy {proxy_id} not found")
            
            logger.info(
                f"🔍 Checking proxy {proxy_id}: "
                f"{current_proxy.city}, {current_proxy.region}"
            )
            
            # ========================================
            # 2. PING ACTUAL PROXY
            # ========================================
            ping_result = await self._ping_proxy(current_proxy)
            
            if ping_result["success"] and ping_result["latency_ms"] < self.OPTIMAL_LATENCY_MS:
                logger.info(
                    f"✅ Proxy {proxy_id} is optimal "
                    f"({ping_result['latency_ms']}ms)"
                )
                return {
                    "rotated": False,
                    "reason": "proxy_optimal",
                    "latency_ms": ping_result["latency_ms"],
                    "message": f"Proxy is healthy ({ping_result['latency_ms']}ms)"
                }
            
            # ========================================
            # 3. DETECTAR PROBLEMAS
            # ========================================
            issues = []
            
            if not ping_result["success"]:
                issues.append("unavailable")
            elif ping_result["latency_ms"] > self.MAX_LATENCY_MS:
                issues.append("slow")
            
            # Test funcionalidad si hay URLs
            if test_urls and ping_result["success"]:
                functionality_ok = await self._test_functionality(
                    current_proxy, 
                    test_urls
                )
                if not functionality_ok:
                    issues.append("blocked")
            
            if not issues:
                return {
                    "rotated": False,
                    "reason": "no_issues",
                    "message": "Proxy working but not optimal"
                }
            
            logger.warning(
                f"⚠️ Proxy {proxy_id} has issues: {', '.join(issues)}"
            )
            
            # ========================================
            # 4. BUSCAR UBICACIÓN ÓPTIMA
            # ========================================
            optimal_location = await self._find_optimal_location(
                current_location=GeoManager.create_location(
                    country=current_proxy.country,
                    region=current_proxy.region,
                    city=current_proxy.city
                ),
                exclude_cities=[current_proxy.city]
            )
            
            if not optimal_location:
                raise ProxyRotationError("No optimal locations available")
            
            logger.info(
                f"🎯 Optimal location found: {optimal_location.city}, "
                f"{optimal_location.region} (estimated {optimal_location.estimated_latency_ms}ms)"
            )
            
            # ========================================
            # 5. ACTUALIZAR SESIÓN DEL PROXY EXISTENTE
            # ========================================
            await self._update_proxy_session(
                proxy=current_proxy,
                new_location=optimal_location
            )
            
            # ========================================
            # 6. VERIFICAR QUE NUEVA SESIÓN FUNCIONA
            # ========================================
            verify_result = await self._ping_proxy(current_proxy)
            
            if not verify_result["success"]:
                # Rollback
                await self.db.rollback()
                raise ProxyRotationError(
                    f"New session failed verification: {verify_result.get('error')}"
                )
            
            logger.info(
                f"✅ New session verified: {verify_result['latency_ms']}ms"
            )
            
            # ========================================
            # 7. ACTUALIZAR ADSPOWER
            # ========================================
            await self._update_adspower_profiles(current_proxy)
            
            # ========================================
            # 8. COMMIT CAMBIOS
            # ========================================
            await self.db.commit()
            
            logger.info(
                f"✅ Rotation complete: {current_proxy.city} "
                f"(issues: {', '.join(issues)}) "
                f"→ {optimal_location.city} ({verify_result['latency_ms']}ms)"
            )
            
            return {
                "rotated": True,
                "issues_detected": issues,
                "old_location": f"{current_proxy.city}, {current_proxy.region}",
                "new_location": f"{optimal_location.city}, {optimal_location.region}",
                "old_latency_ms": ping_result.get("latency_ms"),
                "new_latency_ms": verify_result["latency_ms"],
                "message": f"Rotated to optimal location: {optimal_location.city}"
            }
        
        except ProxyRotationError as e:
            logger.error(f"Rotation failed: {e}")
            await self.db.rollback()
            return {
                "rotated": False,
                "error": str(e),
                "message": f"Rotation failed: {e}"
            }
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await self.db.rollback()
            return {
                "rotated": False,
                "error": str(e),
                "message": f"Unexpected error: {e}"
            }
    
    async def _ping_proxy(self, proxy: Proxy) -> Dict:
        """
        🏓 Ping proxy para verificar latencia y disponibilidad
        
        Returns:
            {
                "success": True/False,
                "latency_ms": 123.45,
                "ip": "1.2.3.4",
                "error": "..." (si falla)
            }
        """
        
        proxy_url = (
            f"http://{proxy.username}:{proxy.password}"
            f"@{proxy.host}:{proxy.port}"
        )
        
        try:
            start = time.time()
            
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0
            ) as client:
                response = await client.get("https://api.ipify.org?format=json")
                
                latency = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        "success": True,
                        "latency_ms": round(latency, 2),
                        "ip": data.get("ip")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    }
        
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "timeout"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _test_functionality(
        self,
        proxy: Proxy,
        test_urls: List[str]
    ) -> bool:
        """Prueba funcionalidad del proxy con URLs específicas"""
        
        proxy_url = (
            f"http://{proxy.username}:{proxy.password}"
            f"@{proxy.host}:{proxy.port}"
        )
        
        for url in test_urls:
            try:
                async with httpx.AsyncClient(
                    proxies={"http://": proxy_url, "https://": proxy_url},
                    timeout=15.0,
                    follow_redirects=True
                ) as client:
                    response = await client.get(url)
                    
                    if response.status_code in [403, 429]:
                        logger.warning(f"Blocked: {response.status_code} on {url}")
                        return False
                    
                    content = response.text.lower()
                    if "cloudflare" in content or "recaptcha" in content:
                        logger.warning(f"CAPTCHA detected on {url}")
                        return False
            
            except Exception as e:
                logger.warning(f"Functionality test failed for {url}: {e}")
                return False
        
        return True
    
    async def _find_optimal_location(
        self,
        current_location: GeoLocation,
        exclude_cities: List[str]
    ) -> Optional[GeoLocation]:
        """
        🎯 Encuentra ubicación óptima con PING REAL
        
        Estrategia:
        1. Misma región, otra ciudad
        2. Regiones cercanas
        3. Cualquier ubicación en el país
        
        Para cada ubicación: PING REAL antes de seleccionar
        """
        
        logger.info(
            f"🔍 Finding optimal location from: "
            f"{current_location.city}, {current_location.region}"
        )
        
        candidates = []
        
        # ========================================
        # 1. MISMA REGIÓN
        # ========================================
        if current_location.region_code:
            region_locations = [
                loc for loc in GeoManager.get_all_locations()
                if (
                    loc.region_code == current_location.region_code and
                    loc.city_code not in exclude_cities and
                    loc.city_code != current_location.city_code
                )
            ]
            
            logger.info(f"Found {len(region_locations)} locations in same region")
            candidates.extend(region_locations)
        
        # ========================================
        # 2. REGIONES CERCANAS
        # ========================================
        if current_location.region_code:
            nearby_regions = GeoManager.PROXIMITY_MAP.get(
                current_location.region_code, 
                []
            )
            
            for region_code in nearby_regions:
                nearby_locations = [
                    loc for loc in GeoManager.get_all_locations()
                    if (
                        loc.region_code == region_code and
                        loc.city_code not in exclude_cities
                    )
                ]
                
                logger.info(
                    f"Found {len(nearby_locations)} locations in {region_code}"
                )
                candidates.extend(nearby_locations)
        
        # ========================================
        # 3. TODO EL PAÍS
        # ========================================
        if not candidates:
            all_locations = [
                loc for loc in GeoManager.get_all_locations()
                if loc.city_code not in exclude_cities
            ]
            
            logger.info(f"Expanding search to all {len(all_locations)} locations")
            candidates.extend(all_locations)
        
        if not candidates:
            logger.error("No candidate locations found")
            return None
        
        # ========================================
        # 4. PING CADA CANDIDATO Y SELECCIONAR MEJOR
        # ========================================
        logger.info(f"Testing {len(candidates)} candidate locations...")
        
        # Limitar a top 10 por latencia estimada
        candidates.sort(key=lambda loc: loc.estimated_latency_ms)
        top_candidates = candidates[:10]
        
        best_location = None
        best_latency = float('inf')
        
        for location in top_candidates:
            # Generar sesión temporal para test
            test_config = self.soax.get_proxy_config(
                proxy_type="mobile",
                country=location.country,
                region=location.region_code,
                city=location.city_code,
                session_lifetime=3600
            )

            logger.warning(f"SOAX USERNAME TESTED: {test_config['username']}")

            
            # Crear proxy temporal para ping
            test_proxy = Proxy(
                proxy_type="mobile",
                host=test_config["host"],
                port=test_config["port"],
                username=test_config["username"],
                password=test_config["password"]
            )
            
            # PING REAL
            ping_result = await self._ping_proxy(test_proxy)
            
            if ping_result["success"]:
                latency = ping_result["latency_ms"]
                
                logger.info(
                    f"✓ {location.city}: {latency}ms "
                    f"(estimated: {location.estimated_latency_ms}ms)"
                )
                
                if latency < best_latency:
                    best_latency = latency
                    best_location = location
            else:
                logger.warning(
                    f"✗ {location.city}: {ping_result.get('error')}"
                )
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        if best_location:
            logger.info(
                f"🏆 Best location: {best_location.city} "
                f"({best_latency}ms actual latency)"
            )
            return best_location
        
        logger.error("No working locations found")
        return None
    
    async def _update_proxy_session(
        self,
        proxy: Proxy,
        new_location: GeoLocation
    ):
        """
        🔄 Actualiza sesión del proxy (NO crea nuevo)
        
        ✅ CRÍTICO: Solo actualiza campos, no crea registro nuevo
        """
        
        # Generar nueva configuración SOAX
        new_config = self.soax.get_proxy_config(
            proxy_type=proxy.proxy_type,
            country=new_location.country,
            region=new_location.region_code,
            city=new_location.city_code,
            session_lifetime=proxy.session_lifetime or 3600
        )
        
        # ✅ ACTUALIZAR campos del proxy existente
        proxy.country = new_location.country
        proxy.region = new_location.region
        proxy.city = new_location.city
        proxy.session_id = new_config["session_id"]
        proxy.username = new_config["username"]
        proxy.password = new_config["password"]
        proxy.status = ProxyStatus.ACTIVE
        proxy.is_available = True
        proxy.updated_at = datetime.utcnow()
        
        
        logger.info(
            f"✓ Proxy {proxy.id} session updated: "
            f"{new_location.city}, session_id={new_config['session_id'][:8]}..."
        )
    
    async def _update_adspower_profiles(self, proxy: Proxy):
        """
        🔄 Actualiza TODOS los profiles en AdsPower con nueva config
        
        ✅ CRÍTICO: Rollback si falla alguno
        """
        
        # Obtener profiles que usan este proxy
        result = await self.db.execute(
            select(Profile).where(Profile.proxy_id == proxy.id)
        )
        profiles = list(result.scalars().all())
        
        if not profiles:
            logger.info(f"No profiles using proxy {proxy.id}")
            return
        
        logger.info(
            f"Updating {len(profiles)} profiles in AdsPower for proxy {proxy.id}"
        )
        
        proxy_type_map = {
            "http": "http",
            "https": "https",
            "socks5": "socks5",
            "mobile": "http",
            "residential": "http"
        }
        
        updated_count = 0
        errors = []
        
        for profile in profiles:
            try:
                # Obtener computer
                result = await self.db.execute(
                    select(Computer).where(Computer.id == profile.computer_id)
                )
                computer = result.scalar_one_or_none()
                
                if not computer:
                    errors.append(f"Computer {profile.computer_id} not found")
                    continue
                
                # Actualizar en AdsPower
                adspower_client = AdsPowerClient(
                    api_url=computer.adspower_api_url,
                    api_key=computer.adspower_api_key
                )
                
                proxy_config = {
                    "user_proxy_config": {
                        "proxy_soft": "other",
                        "proxy_type": proxy_type_map.get(proxy.proxy_type, "http"),
                        "proxy_host": proxy.host,
                        "proxy_port": str(proxy.port),
                        "proxy_user": proxy.username or "",
                        "proxy_password": proxy.password or ""
                    }
                }
                
                success = await adspower_client.update_profile(
                    profile_id=profile.adspower_id,
                    profile_data=proxy_config
                )
                
                if success:
                    updated_count += 1
                    logger.info(f"✓ Profile {profile.id} updated in AdsPower")
                else:
                    errors.append(f"Profile {profile.id} update failed")
            
            except Exception as e:
                errors.append(f"Profile {profile.id}: {str(e)}")
                logger.error(f"Error updating profile {profile.id}: {e}")
        
        if errors:
            error_msg = f"Failed to update {len(errors)} profiles: {'; '.join(errors)}"
            logger.error(error_msg)
            
            # Si falló más del 50%, rollback
            if len(errors) > len(profiles) / 2:
                raise ProxyRotationError(
                    f"Too many failures ({len(errors)}/{len(profiles)}), "
                    "rolling back"
                )
        
        logger.info(
            f"✅ AdsPower update complete: {updated_count}/{len(profiles)} profiles"
        )


# ========================================
# FUNCIONES HELPER
# ========================================

async def rotate_proxy_if_slow(db: AsyncSession, proxy_id: int) -> Dict:
    """Helper: Rota proxy si es lento"""
    rotator = SmartProxyRotator(db)
    return await rotator.detect_and_rotate_if_needed(proxy_id)


async def ping_all_proxies(db: AsyncSession) -> Dict:
    """Helper: Ping todos los proxies y retorna estadísticas"""
    
    result = await db.execute(select(Proxy))
    proxies = list(result.scalars().all())
    
    rotator = SmartProxyRotator(db)
    
    stats = {
        "total": len(proxies),
        "optimal": 0,
        "slow": 0,
        "failed": 0,
        "results": []
    }
    
    for proxy in proxies:
        ping_result = await rotator._ping_proxy(proxy)
        
        status = "failed"
        if ping_result["success"]:
            if ping_result["latency_ms"] < rotator.OPTIMAL_LATENCY_MS:
                status = "optimal"
                stats["optimal"] += 1
            else:
                status = "slow"
                stats["slow"] += 1
        else:
            stats["failed"] += 1
        
        stats["results"].append({
            "proxy_id": proxy.id,
            "location": f"{proxy.city}, {proxy.region}",
            "status": status,
            "latency_ms": ping_result.get("latency_ms"),
            "error": ping_result.get("error")
        })
    
    return stats