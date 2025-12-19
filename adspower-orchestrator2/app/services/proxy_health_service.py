# app/services/proxy_health_service.py - VERSIÓN CORREGIDA
"""
Servicio CORREGIDO con:
- Speed test más robusto (sin 500 errors)
- Auto-recovery mejorado
- Detección de proxies lentas
- Rotación automática
"""
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from datetime import datetime, timedelta
from loguru import logger
import httpx
import asyncio
import time

from app.models.proxy import Proxy, ProxyStatus
from app.models.proxy_health import ProxyHealthCheck, ProxyScore
from app.integrations.soax_client import SOAXClient


class ProxyHealthService:
    """Servicio de monitoreo MEJORADO"""
    
    # ✅ URLs más confiables (sin 500 errors)
    TEST_URLS = [
        "https://httpbin.org/ip",           # Muy confiable
        "https://ifconfig.me/ip",           # Simple y rápido
        "https://api.ipify.org?format=json" # Backup
    ]
    
    # ✅ Speed test más ligero (evita timeouts)
    SPEED_TEST_URL = "https://httpbin.org/bytes/5120"  # Solo 5KB
    
    # ✅ Thresholds más realistas
    MAX_LATENCY_MS = 2500      # 2.5s (antes 3s)
    OPTIMAL_LATENCY_MS = 1000  # 1s
    MAX_CONSECUTIVE_FAILURES = 5  # Más tolerante
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def comprehensive_health_check(
        self,
        proxy_id: int,
        test_multiple_sessions: bool = False
    ) -> Dict:
        """✅ Health check CORREGIDO"""
        
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        
        if not proxy:
            raise ValueError(f"Proxy {proxy_id} not found")
        
        logger.info(f"🔍 Health check: Proxy {proxy_id} ({proxy.city}, {proxy.region})")
        
        # ========================================
        # 1. SPEED TEST (MÁS ROBUSTO)
        # ========================================
        speed_result = await self._test_speed_robust(proxy)
        
        # ========================================
        # 2. AVAILABILITY
        # ========================================
        availability_result = await self._test_availability_robust(proxy)
        
        # ========================================
        # 3. GEO VERIFICATION (OPCIONAL SI FALLÓ SPEED)
        # ========================================
        geo_result = {"geo_match": True, "status": "skipped"}
        
        if speed_result["status"] == "success":
            geo_result = await self._verify_geo_location(proxy)
        
        # ========================================
        # 4. CALCULAR SCORE
        # ========================================
        overall_score = self._calculate_score_safe(
            speed_result,
            availability_result,
            geo_result
        )
        
        overall_status = self._determine_status(overall_score, availability_result)
        
        # ========================================
        # 5. GUARDAR EN DB (SAFE)
        # ========================================
        await self._save_health_check_safe(
            proxy_id=proxy_id,
            speed=speed_result,
            availability=availability_result,
            geo=geo_result
        )
        
        # ========================================
        # 6. ACTUALIZAR SCORE
        # ========================================
        await self._update_proxy_score_safe(proxy_id, overall_score, {
            "speed": speed_result,
            "availability": availability_result,
            "geo": geo_result
        })
        
        # ========================================
        # 7. AUTO-RECOVERY SI ES NECESARIO
        # ========================================
        if overall_status in ["unhealthy", "offline"]:
            logger.warning(f"⚠️ Proxy {proxy_id} unhealthy, triggering auto-recovery")
            await self._attempt_auto_recovery_smart(proxy)
        
        return {
            "proxy_id": proxy_id,
            "overall_status": overall_status,
            "overall_score": overall_score,
            "speed_test": speed_result,
            "geo_verification": geo_result,
            "availability": availability_result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _test_speed_robust(self, proxy: Proxy) -> Dict:
        """✅ Speed test MÁS ROBUSTO (sin 500 errors)"""
        
        proxy_url = self._build_proxy_url(proxy)
        
        results = {
            "latency_ms": None,
            "download_speed_mbps": None,
            "status": "pending"
        }
        
        # ========================================
        # INTENTAR CON MÚLTIPLES URLs
        # ========================================
        for test_url in self.TEST_URLS:
            try:
                start_time = time.time()
                
                async with httpx.AsyncClient(
                    proxies={"http://": proxy_url, "https://": proxy_url},
                    timeout=15.0,  # ✅ Timeout más generoso
                    follow_redirects=True
                ) as client:
                    response = await client.get(test_url)
                    
                    if response.status_code == 200:
                        latency = (time.time() - start_time) * 1000
                        results["latency_ms"] = round(latency, 2)
                        results["status"] = "success"
                        
                        logger.info(
                            f"✅ Speed test OK: Proxy {proxy.id} = {latency:.0f}ms"
                        )
                        
                        # ✅ OPCIONAL: Test de velocidad solo si latency es OK
                        if latency < 3000:
                            try:
                                start_dl = time.time()
                                dl_response = await client.get(
                                    self.SPEED_TEST_URL,
                                    timeout=10.0
                                )
                                
                                if dl_response.status_code == 200:
                                    download_time = time.time() - start_dl
                                    
                                    if download_time > 0:
                                        file_size_mb = 5120 / (1024 * 1024)
                                        speed_mbps = (file_size_mb / download_time) * 8
                                        results["download_speed_mbps"] = round(speed_mbps, 2)
                            
                            except Exception as e:
                                logger.debug(f"Download test failed: {e}")
                        
                        return results
            
            except httpx.TimeoutException:
                logger.debug(f"Timeout con {test_url}")
                continue
            
            except Exception as e:
                logger.debug(f"Error con {test_url}: {e}")
                continue
        
        # ========================================
        # TODOS FALLARON
        # ========================================
        results["status"] = "failed"
        logger.error(f"❌ Speed test failed: Proxy {proxy.id} (todas URLs fallaron)")
        
        return results
    
    async def _test_availability_robust(self, proxy: Proxy) -> Dict:
        """✅ Availability test MEJORADO"""
        
        proxy_url = self._build_proxy_url(proxy)
        logger.info(f"🔹 Proxy URL construido: {proxy_url}")
        
        results = {
            "is_available": False,
            "response_code": None,
            "test_url": None,
            "status": "pending"
        }
        
        # Intentar con al menos 2 URLs
        for test_url in self.TEST_URLS[:2]:
            try:
                async with httpx.AsyncClient(
                    proxies={"http://": proxy_url, "https://": proxy_url},
                    timeout=12.0,
                    follow_redirects=True
                ) as client:
                    response = await client.get(test_url)
                    
                    if response.status_code == 200:
                        results["is_available"] = True
                        results["response_code"] = 200
                        results["test_url"] = test_url
                        results["status"] = "success"
                        
                        logger.info(f"✅ Availability: Proxy {proxy.id} is available")
                        return results
            
            except Exception as e:
                logger.debug(f"Availability test failed with {test_url}: {e}")
                continue
        
        results["status"] = "failed"
        logger.warning(f"⚠️ Availability: Proxy {proxy.id} is unavailable")
        
        return results
    
    async def _verify_geo_location(self, proxy: Proxy) -> Dict:
        """Geo verification (solo si proxy funciona)"""
        
        proxy_url = self._build_proxy_url(proxy)
        
        results = {
            "detected_ip": None,
            "detected_country": None,
            "detected_city": None,
            "expected_country": proxy.country,
            "geo_match": False,
            "status": "pending"
        }
        
        try:
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0
            ) as client:
                response = await client.get("http://ip-api.com/json/")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    results["detected_ip"] = data.get("query")
                    results["detected_country"] = data.get("countryCode")
                    results["detected_city"] = data.get("city")
                    
                    if proxy.country:
                        results["geo_match"] = (
                            results["detected_country"] and
                            results["detected_country"].lower() == proxy.country.lower()
                        )
                    else:
                        results["geo_match"] = True
                    
                    results["status"] = "success"
        
        except Exception as e:
            results["status"] = "failed"
            logger.debug(f"Geo verification failed: {e}")
        
        return results
    
    def _calculate_score_safe(
        self,
        speed: Dict,
        availability: Dict,
        geo: Dict
    ) -> float:
        """Calcula score de forma SEGURA"""
        
        scores = []
        
        # 1. Speed (40%)
        if speed["status"] == "success" and speed["latency_ms"]:
            latency = speed["latency_ms"]
            
            if latency < 500:
                speed_score = 100
            elif latency < 1000:
                speed_score = 85
            elif latency < 1500:
                speed_score = 70
            elif latency < 2000:
                speed_score = 55
            elif latency < 2500:
                speed_score = 40
            else:
                speed_score = 20
            
            scores.append(("speed", speed_score, 0.40))
        else:
            scores.append(("speed", 0, 0.40))
        
        # 2. Availability (40%) - ✅ Más peso
        availability_score = 100 if availability["is_available"] else 0
        scores.append(("availability", availability_score, 0.40))
        
        # 3. Geo (20%)
        geo_score = 100 if geo.get("geo_match", True) else 60
        scores.append(("geo", geo_score, 0.20))
        
        overall_score = sum(score * weight for _, score, weight in scores)
        
        return round(overall_score, 2)
    
    def _determine_status(self, score: float, availability: Dict) -> str:
        """Determina estado"""
        
        if not availability["is_available"]:
            return "offline"
        
        if score >= 75:
            return "healthy"
        elif score >= 50:
            return "degraded"
        else:
            return "unhealthy"
    
    async def _save_health_check_safe(
        self,
        proxy_id: int,
        speed: Dict,
        availability: Dict,
        geo: Dict
    ):
        """Guarda health check (SAFE)"""
        
        try:
            health_check = ProxyHealthCheck(
                proxy_id=proxy_id,
                status=availability["status"],
                check_type="comprehensive",
                latency_ms=speed.get("latency_ms"),
                download_speed_mbps=speed.get("download_speed_mbps"),
                detected_ip=geo.get("detected_ip"),
                detected_country=geo.get("detected_country"),
                detected_city=geo.get("detected_city"),
                geo_match=geo.get("geo_match", False),
                is_available=availability["is_available"],
                response_code=availability.get("response_code"),
                test_urls=self.TEST_URLS,
                raw_response={
                    "speed": speed,
                    "availability": availability,
                    "geo": geo
                }
            )
            
            self.db.add(health_check)
            await self.db.commit()
            await self.db.refresh(health_check)
            
            logger.debug(f"✓ Health check saved: Proxy {proxy_id}, ID: {health_check.id}")
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error saving health check: {e}")
    
    async def _update_proxy_score_safe(
        self,
        proxy_id: int,
        overall_score: float,
        details: Dict
    ):
        """✅ Actualiza score de forma ULTRA-SEGURA"""
        
        try:
            result = await self.db.execute(
                select(ProxyScore).where(ProxyScore.proxy_id == proxy_id)
            )
            score_record = result.scalar_one_or_none()
            
            if not score_record:
                score_record = ProxyScore(
                    proxy_id=proxy_id,
                    overall_score=overall_score,
                    total_checks=1,
                    successful_checks=1 if details["availability"]["is_available"] else 0,
                    failed_checks=0 if details["availability"]["is_available"] else 1,
                    consecutive_failures=0 if details["availability"]["is_available"] else 1,
                    uptime_percentage=100.0 if details["availability"]["is_available"] else 0.0,
                    avg_latency=details["speed"].get("latency_ms"),
                    min_latency=details["speed"].get("latency_ms"),
                    max_latency=details["speed"].get("latency_ms"),
                    is_blacklisted=False
                )
                self.db.add(score_record)
                await self.db.flush()
            
            # ✅ Actualizar contadores de forma segura
            score_record.total_checks = (score_record.total_checks or 0) + 1
            
            if details["availability"]["is_available"]:
                score_record.successful_checks = (score_record.successful_checks or 0) + 1
                score_record.consecutive_failures = 0
            else:
                score_record.failed_checks = (score_record.failed_checks or 0) + 1
                score_record.consecutive_failures = (score_record.consecutive_failures or 0) + 1
            
            # ✅ Actualizar latencia
            latency = details["speed"].get("latency_ms")
            if latency:
                if score_record.avg_latency is None:
                    score_record.avg_latency = latency
                else:
                    score_record.avg_latency = (score_record.avg_latency * 0.7) + (latency * 0.3)
                
                if score_record.min_latency is None or latency < score_record.min_latency:
                    score_record.min_latency = latency
                
                if score_record.max_latency is None or latency > score_record.max_latency:
                    score_record.max_latency = latency
            
            # ✅ Uptime
            if score_record.total_checks > 0:
                score_record.uptime_percentage = round(
                    (score_record.successful_checks / score_record.total_checks) * 100,
                    2
                )
            
            score_record.overall_score = overall_score
            
            # ✅ BLACKLIST solo si > 5 fallos consecutivos
            if score_record.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                if not score_record.is_blacklisted:
                    score_record.is_blacklisted = True
                    score_record.blacklist_reason = f"{score_record.consecutive_failures} consecutive failures"
                    score_record.blacklisted_at = datetime.utcnow()
                    
                    logger.warning(
                        f"🚫 Proxy {proxy_id} blacklisted: "
                        f"{score_record.consecutive_failures} failures"
                    )
            
            score_record.last_check_at = datetime.utcnow()
            score_record.score_updated_at = datetime.utcnow()
            
            await self.db.commit()
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating score: {e}")
    
    async def _attempt_auto_recovery_smart(self, proxy: Proxy):
        """✅ Auto-recovery INTELIGENTE"""
        
        logger.info(f"🔄 Smart auto-recovery: Proxy {proxy.id}")
        
        try:
            # ========================================
            # ESTRATEGIA: Rotar sesión (nueva IP)
            # ========================================
            from app.integrations.soax_client import SOAXClient
            
            soax = SOAXClient(
                username=proxy.username.split('-')[0] if proxy.username else "",
                password=proxy.password or ""
            )
            
            # Generar nueva sesión
            new_config = soax.get_proxy_config(
                proxy_type=proxy.proxy_type,
                country=proxy.country,
                region=proxy.region,
                city=proxy.city
            )
            
            # Actualizar
            proxy.session_id = new_config["session_id"]
            proxy.username = new_config["username"]
            proxy.status = ProxyStatus.ACTIVE  # ✅ Reactivar
            
            await self.db.commit()
            
            logger.info(f"✅ Auto-recovery: New session for proxy {proxy.id}")
            
            # ✅ Re-test después de 10s
            await asyncio.sleep(10)
            
            result = await self.comprehensive_health_check(
                proxy_id=proxy.id,
                test_multiple_sessions=False
            )
            
            if result["overall_status"] == "healthy":
                logger.info(f"🎉 Recovery successful: Proxy {proxy.id}")
                
                # Reset blacklist
                score_result = await self.db.execute(
                    select(ProxyScore).where(ProxyScore.proxy_id == proxy.id)
                )
                score = score_result.scalar_one_or_none()
                
                if score and score.is_blacklisted:
                    score.is_blacklisted = False
                    score.blacklist_reason = None
                    score.blacklisted_at = None
                    score.consecutive_failures = 0
                    await self.db.commit()
            else:
                logger.warning(f"⚠️ Recovery failed: Proxy {proxy.id}")
        
        except Exception as e:
            logger.error(f"Error in auto-recovery: {e}")
    
    def _build_proxy_url(self, proxy: Proxy) -> str:
        """Construye URL del proxy"""
        return (
            f"http://{proxy.username}:{proxy.password}"
            f"@{proxy.host}:{proxy.port}"
        )
    
    # ========================================
    # BATCH OPERATIONS
    # ========================================
    
    async def health_check_all_proxies(
        self,
        only_active: bool = False,
        max_concurrent: int = 5
    ) -> Dict:
        """Health check de todos los proxies (MEJORADO)"""
        
        query = select(Proxy)
        
        if only_active:
            query = query.where(
                and_(
                    Proxy.is_available == True,
                    Proxy.status == ProxyStatus.ACTIVE
                )
            )
        
        result = await self.db.execute(query)
        proxies = list(result.scalars().all())
        
        logger.info(f"🏥 Starting batch health check: {len(proxies)} proxies")
        
        results = {
            "total": len(proxies),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "offline": 0,
            "details": []
        }
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def check_with_semaphore(proxy):
            async with semaphore:
                try:
                    return await self.comprehensive_health_check(
                        proxy.id,
                        test_multiple_sessions=False
                    )
                except Exception as e:
                    logger.error(f"Health check failed for proxy {proxy.id}: {e}")
                    return {
                        "proxy_id": proxy.id,
                        "overall_status": "error",
                        "error": str(e)
                    }
        
        tasks = [check_with_semaphore(proxy) for proxy in proxies]
        check_results = await asyncio.gather(*tasks)
        
        for check_result in check_results:
            status = check_result["overall_status"]
            
            if status == "healthy":
                results["healthy"] += 1
            elif status == "degraded":
                results["degraded"] += 1
            elif status == "unhealthy":
                results["unhealthy"] += 1
            else:
                results["offline"] += 1
            
            results["details"].append(check_result)
        
        logger.info(
            f"✅ Batch health check complete: "
            f"{results['healthy']} healthy, "
            f"{results['offline']} offline"
        )
        
        return results