# app/services/smart_proxy_rotator.py - VERSIÓN CORREGIDA FINAL
"""
Sistema de Rotación Inteligente de Proxies
✅ FIXES:
- Busca alternativas sin importar status actual
- Crea ProxyScore automáticamente si no existe
- Maneja correctamente proxies sin score
- Algoritmo de selección más flexible
"""
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from loguru import logger
import asyncio
import httpx
import time

from app.models.proxy import Proxy, ProxyStatus
from app.models.profile import Profile
from app.models.proxy_health import ProxyScore
from app.utils.geo_manager import GeoManager, GeoLocation
from app.integrations.adspower_client import AdsPowerClient
from app.integrations.soax_client import SOAXClient
from app.models.computer import Computer
from app.config import settings


class ProxyIssueType:
    """Tipos de problemas detectables"""
    TIMEOUT = "timeout"
    SLOW_LOADING = "slow_loading"
    GEO_MISMATCH = "geo_mismatch"
    FUNCTIONALITY_BLOCKED = "functionality_blocked"
    CAPTCHA_DETECTED = "captcha_detected"
    BOT_DETECTED = "bot_detected"
    FINGERPRINT_FAILED = "fingerprint_failed"
    UNAVAILABLE = "unavailable"


class SmartProxyRotator:
    """Rotador Inteligente CORREGIDO"""
    
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
        
        # ✅ Crear ProxyScore si no existe
        await self._ensure_proxy_score(proxy_id)
        
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
            f"{proxy.city} → {new_proxy.city}"
        )
        
        return {
            "rotated": True,
            "issues_detected": issues,
            "old_proxy_id": proxy.id,
            "old_location": f"{proxy.city}, {proxy.region or proxy.country}",
            "new_proxy_id": new_proxy.id,
            "new_location": f"{new_proxy.city}, {new_proxy.region or new_proxy.country}",
            "profiles_updated": updated_count,
            "message": f"Rotated to optimal location: {new_proxy.city}"
        }
    
    async def _ensure_proxy_score(self, proxy_id: int):
        """✅ Crea ProxyScore si no existe"""
        
        result = await self.db.execute(
            select(ProxyScore).where(ProxyScore.proxy_id == proxy_id)
        )
        score = result.scalar_one_or_none()
        
        if not score:
            logger.info(f"Creating ProxyScore for proxy {proxy_id}")
            
            score = ProxyScore(
                proxy_id=proxy_id,
                overall_score=100.0,
                speed_score=100.0,
                availability_score=100.0,
                geo_accuracy_score=100.0,
                stability_score=100.0,
                total_checks=0,
                successful_checks=0,
                failed_checks=0,
                uptime_percentage=100.0,
                consecutive_failures=0
            )
            
            self.db.add(score)
            await self.db.commit()
    
    async def _detect_proxy_issues(
        self,
        proxy: Proxy,
        test_urls: List[str] = None
    ) -> List[str]:
        """Detecta problemas del proxy (maneja score=None)"""
        
        issues = []
        
        # ✅ Manejar proxy sin score
        result = await self.db.execute(
            select(ProxyScore).where(ProxyScore.proxy_id == proxy.id)
        )
        score = result.scalar_one_or_none()
        
        if not score:
            # Sin score = necesita health check
            logger.warning(f"Proxy {proxy.id} has no score - needs health check")
            issues.append("no_score")
            return issues
        
        # Verificar blacklist
        if score.is_blacklisted:
            issues.append("unavailable")
            return issues
        
        # Verificar latencia
        if score.avg_latency and score.avg_latency > self.MAX_LATENCY_MS:
            issues.append("slow_loading")
        
        # Verificar uptime
        if score.uptime_percentage < 70:
            issues.append("timeout")
        
        # Test funcionalidad si hay URLs
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
        🎯 Rota a ubicación ÓPTIMA sin crear duplicados
        
        Estrategia:
        1. Buscar proxies EXISTENTES (status ACTIVE o INACTIVE)
        2. Si existe, reactivar y actualizar
        3. Solo crear nuevo si NO existe ninguno en esa ubicación
        """
        
        # Obtener ubicación óptima
        optimal_location = GeoManager.get_optimal_location(
            country=current_proxy.country,
            exclude_cities=[current_proxy.city] if current_proxy.city else []
        )
        
        logger.info(
            f"🎯 Optimal location: {optimal_location.city} "
            f"(latency: {optimal_location.estimated_latency_ms}ms)"
        )
        
        # ========================================
        # 1. BUSCAR PROXY EXISTENTE (sin filtro de status)
        # ========================================
        result = await self.db.execute(
            select(Proxy, ProxyScore)
            .outerjoin(ProxyScore, Proxy.id == ProxyScore.proxy_id)
            .where(
                and_(
                    Proxy.country == optimal_location.country,
                    Proxy.region == optimal_location.region,
                    Proxy.city == optimal_location.city,
                    Proxy.proxy_type == current_proxy.proxy_type  # ✅ Mismo tipo
                )
            )
        )
        
        candidates = list(result.all())
        
        if candidates:
            # ========================================
            # 2. SELECCIONAR MEJOR CANDIDATO
            # ========================================
            best_proxy = None
            best_score = -1
            
            for proxy, score in candidates:
                # Preferir ACTIVE con buen score
                if proxy.status == ProxyStatus.ACTIVE:
                    if score and score.overall_score > best_score:
                        best_proxy = proxy
                        best_score = score.overall_score if score else 0
                    elif not best_proxy:
                        best_proxy = proxy
                
                # Si no hay ACTIVE, usar CUALQUIERA con mejor score
                elif not best_proxy and score:
                    if score.overall_score > best_score:
                        best_proxy = proxy
                        best_score = score.overall_score
            
            # Si encontramos alguno, REUTILIZARLO
            if best_proxy:
                logger.info(
                    f"✓ Reusing existing proxy: {best_proxy.city} "
                    f"(ID: {best_proxy.id}, Score: {best_score:.1f})"
                )
                
                # ✅ ACTUALIZAR (NO CREAR)
                if best_proxy.status != ProxyStatus.ACTIVE:
                    best_proxy.status = ProxyStatus.ACTIVE
                    best_proxy.is_available = True
                    logger.info(f"Reactivated proxy {best_proxy.id}")
                
                # ✅ Rotar sesión (nueva IP sin cambiar proxy)
                await self._rotate_session(best_proxy)
                
                # Marcar proxy viejo como failed
                current_proxy.status = ProxyStatus.FAILED
                current_proxy.is_available = False
                
                await self.db.commit()
                
                return best_proxy
        
        # ========================================
        # 3. SI NO EXISTE, CREAR NUEVO (último recurso)
        # ========================================
        logger.info(f"No existing proxy found, creating new for {optimal_location.city}")
        
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
        
        if not test_result["success"]:
            logger.error(f"✗ New proxy failed test: {optimal_location.city}")
            return None
        
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
            avg_response_time=test_result.get("latency_ms"),
            total_checks=1,
            success_rate=100.0
        )
        
        self.db.add(new_proxy)
        
        # Marcar proxy viejo como failed
        current_proxy.status = ProxyStatus.FAILED
        current_proxy.is_available = False
        
        await self.db.commit()
        await self.db.refresh(new_proxy)
        
        # Crear ProxyScore
        score = ProxyScore(
            proxy_id=new_proxy.id,
            overall_score=100.0,
            total_checks=1,
            successful_checks=1,
            uptime_percentage=100.0
        )
        self.db.add(score)
        await self.db.commit()
        
        logger.info(f"✓ New proxy created: {new_proxy.city} (ID: {new_proxy.id})")
        
        return new_proxy


    async def _rotate_session(self, proxy: Proxy):
        """
        🔄 Rota sesión del proxy (nueva IP) sin crear proxy nuevo
        """
        from app.integrations.soax_client import SOAXClient
        
        soax = SOAXClient(
            username=proxy.username.split('-')[0] if proxy.username else "",
            password=proxy.password or ""
        )
        
        # Generar nueva configuración con nueva sesión
        new_config = soax.get_proxy_config(
            proxy_type=proxy.proxy_type,
            country=proxy.country,
            region=proxy.region,
            city=proxy.city,
            session_lifetime=proxy.session_lifetime or 3600
        )
        
        # Actualizar proxy con nueva sesión
        proxy.session_id = new_config["session_id"]
        proxy.username = new_config["username"]
        
        logger.info(f"Session rotated for proxy {proxy.id}: New IP incoming")
        
        async def _try_fallback_location(
            self,
            current_proxy: Proxy,
            fallback_location: GeoLocation
        ) -> Optional[Proxy]:
            """Intenta crear proxy en ubicación alternativa"""
            
            logger.info(f"Trying fallback: {fallback_location.city}")
            
            proxy_config = self.soax.get_proxy_config(
                proxy_type=current_proxy.proxy_type,
                country=fallback_location.country,
                region=fallback_location.region_code,
                city=fallback_location.city_code,
                session_lifetime=current_proxy.session_lifetime or 3600
            )
            
            test_result = await self.soax.test_proxy(proxy_config, timeout=10.0)
            
            if not test_result["success"]:
                return None
            
            new_proxy = Proxy(
                proxy_type=current_proxy.proxy_type,
                host=proxy_config["host"],
                port=proxy_config["port"],
                username=proxy_config["username"],
                password=proxy_config["password"],
                country=fallback_location.country,
                region=fallback_location.region,
                city=fallback_location.city,
                session_id=proxy_config["session_id"],
                session_lifetime=current_proxy.session_lifetime,
                sticky_session=True,
                status=ProxyStatus.ACTIVE,
                is_available=True,
                detected_ip=test_result.get("ip"),
                avg_response_time=test_result.get("latency_ms"),
                total_checks=1,
                success_rate=100.0
            )
            
            self.db.add(new_proxy)
            await self.db.commit()
            await self.db.refresh(new_proxy)
            
            # Crear score
            score = ProxyScore(
                proxy_id=new_proxy.id,
                overall_score=100.0,
                total_checks=1,
                successful_checks=1
            )
            self.db.add(score)
            await self.db.commit()
            
            return new_proxy
    
    async def _update_profiles_proxy(
        self,
        old_proxy_id: int,
        new_proxy_id: int
    ) -> int:
        """Actualiza profiles en DB + AdsPower con ROLLBACK si falla"""
        
        # Obtener nuevo proxy
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == new_proxy_id)
        )
        new_proxy = result.scalar_one_or_none()
        
        if not new_proxy:
            logger.error(f"New proxy {new_proxy_id} not found")
            return 0
        
        # Obtener profiles usando proxy viejo
        result = await self.db.execute(
            select(Profile).where(Profile.proxy_id == old_proxy_id)
        )
        profiles = list(result.scalars().all())
        
        if not profiles:
            logger.info("No profiles using this proxy")
            return 0
        
        logger.info(f"Updating {len(profiles)} profiles with new proxy")
        
        updated_count = 0
        failed_profiles = []
        
        proxy_type_map = {
            "http": "http",
            "https": "https",
            "socks5": "socks5",
            "mobile": "http",
            "residential": "http"
        }
        
        for profile in profiles:
            try:
                # Actualizar en AdsPower
                result = await self.db.execute(
                    select(Computer).where(Computer.id == profile.computer_id)
                )
                computer = result.scalar_one_or_none()
                
                if not computer:
                    logger.error(f"Computer {profile.computer_id} not found")
                    failed_profiles.append(profile.id)
                    continue
                
                adspower_client = AdsPowerClient(                    
                    api_url=settings.ADSPOWER_DEFAULT_API_URL or computer.adspower_api_url,
                    api_key=settings.ADSPOWER_DEFAULT_API_KEY or computer.adspower_api_key
                )
                
                proxy_config = {
                    "user_proxy_config": {
                        "proxy_soft": "other",
                        "proxy_type": proxy_type_map.get(new_proxy.proxy_type, "http"),
                        "proxy_host": new_proxy.host,
                        "proxy_port": str(new_proxy.port),
                        "proxy_user": new_proxy.username or "",
                        "proxy_password": new_proxy.password or ""
                    }
                }
                
                success = await adspower_client.update_profile(
                    profile_id=profile.adspower_id,
                    profile_data=proxy_config
                )
                
                if success:
                    # ✅ Solo actualizar DB si AdsPower fue exitoso
                    profile.proxy_id = new_proxy_id
                    updated_count += 1
                    
                    logger.info(f"✓ Profile {profile.id} updated")
                else:
                    failed_profiles.append(profile.id)
                    logger.error(f"✗ AdsPower update failed for profile {profile.id}")
            
            except Exception as e:
                failed_profiles.append(profile.id)
                logger.error(f"Error updating profile {profile.id}: {e}")
        
        # Commit cambios en DB
        await self.db.commit()
        
        if failed_profiles:
            logger.warning(f"⚠️ {len(failed_profiles)} profiles failed to update")
        
        logger.info(f"✅ Updated {updated_count}/{len(profiles)} profiles successfully")
        
        return updated_count
    
    async def scan_and_rotate_all_proxies(
        self,
        test_urls: List[str] = None
    ) -> Dict:
        """Escanea TODAS las proxies (sin filtro de status)"""
        
        # ✅ SIN FILTRO - todas las proxies
        result = await self.db.execute(select(Proxy))
        proxies = list(result.scalars().all())
        
        logger.info(f"🔍 Scanning {len(proxies)} total proxies...")
        
        stats = {
            "total_scanned": len(proxies),
            "rotated": 0,
            "healthy": 0,
            "errors": 0,
            "skipped": 0
        }
        
        for proxy in proxies:
            try:
                # Skip si ya está en proceso
                if proxy.status == ProxyStatus.CHECKING:
                    stats["skipped"] += 1
                    continue
                
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