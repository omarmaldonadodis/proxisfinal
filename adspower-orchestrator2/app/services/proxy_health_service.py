# app/services/proxy_health_service.py - SECCIÓN DE IMPORTS (AL INICIO DEL ARCHIVO)

"""
Servicio CORREGIDO con:
- Speed test más robusto (sin 500 errors)
- Auto-recovery mejorado
- Detección de proxies lentas
- Rotación automática
✅ FIX: Importaciones correctas para ProxyScore
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
from app.models.proxy_health import ProxyHealthCheck, ProxyScore  # ✅ IMPORTAR AQUÍ
from app.integrations.soax_client import SOAXClient
from app.config import settings


class ProxyHealthService:
    """Servicio de monitoreo MEJORADO"""
    
    # ✅ URLs más confiables (sin 500 errors)
    TEST_URLS = [
        "https://httpbin.org/ip",
        "https://ifconfig.me/ip",
        "https://api.ipify.org?format=json"
    ]
    
    # ✅ Speed test más ligero (evita timeouts)
    SPEED_TEST_URL = "https://httpbin.org/bytes/5120"  # Solo 5KB
    
    # ✅ Thresholds más realistas
    MAX_LATENCY_MS = 2500      # 2.5s (antes 3s)
    OPTIMAL_LATENCY_MS = 1500  # 1s
    MAX_CONSECUTIVE_FAILURES = 5  # Más tolerante
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def comprehensive_health_check(
        self,
        proxy_id: int,
        test_multiple_sessions: bool = False
    ) -> Dict:
        """✅ Health check ULTRA-SEGURO - NUNCA retorna None"""
        
        try:
            result = await self.db.execute(
                select(Proxy).where(Proxy.id == proxy_id)
            )
            proxy = result.scalar_one_or_none()
            
            if not proxy:
                logger.error(f"❌ Proxy {proxy_id} not found in database")
                return {
                    "proxy_id": proxy_id,
                    "overall_status": "error",
                    "overall_score": 0,
                    "error": "Proxy not found",
                    "speed_test": {"status": "failed"},
                    "availability": {"is_available": False}
                }
            
            logger.info(f"🔍 Health check: Proxy {proxy_id} ({proxy.city}, {proxy.region})")
            
            # ========================================
            # 1. SPEED TEST (MÁS ROBUSTO)
            # ========================================
            try:
                speed_result = await self._test_speed_robust(proxy)
            except Exception as e:
                logger.error(f"Speed test exception for proxy {proxy_id}: {e}")
                speed_result = {"status": "failed", "latency_ms": None}
            
            # ========================================
            # 2. AVAILABILITY
            # ========================================
            try:
                availability_result = await self._test_availability_robust(proxy)
            except Exception as e:
                logger.error(f"Availability test exception for proxy {proxy_id}: {e}")
                availability_result = {"status": "failed", "is_available": False}
            
            # ========================================
            # 3. GEO VERIFICATION (OPCIONAL)
            # ========================================
            geo_result = {"geo_match": True, "status": "skipped"}
            
            if speed_result.get("status") == "success":
                try:
                    geo_result = await self._verify_geo_location(proxy)
                except Exception as e:
                    logger.error(f"Geo verification exception for proxy {proxy_id}: {e}")
                    geo_result = {"status": "failed", "geo_match": False}
            
            # ========================================
            # 4. CALCULAR SCORE (SIEMPRE RETORNA VALOR)
            # ========================================
            try:
                overall_score = self._calculate_score_safe(
                    speed_result,
                    availability_result,
                    geo_result
                )
            except Exception as e:
                logger.error(f"Score calculation exception for proxy {proxy_id}: {e}")
                overall_score = 0.0
            
            overall_status = self._determine_status(overall_score, availability_result)
            
            # ========================================
            # 5. GUARDAR EN DB (NO BLOQUEAR SI FALLA)
            # ========================================
            try:
                await self._save_health_check_safe(
                    proxy_id=proxy_id,
                    speed=speed_result,
                    availability=availability_result,
                    geo=geo_result
                )
            except Exception as e:
                logger.error(f"Failed to save health check for proxy {proxy_id}: {e}")
            
            # ========================================
            # 6. ACTUALIZAR SCORE (NO BLOQUEAR SI FALLA)
            # ========================================
            try:
                await self._update_proxy_score_safe(proxy_id, overall_score, {
                    "speed": speed_result,
                    "availability": availability_result,
                    "geo": geo_result
                })
            except Exception as e:
                logger.error(f"Failed to update score for proxy {proxy_id}: {e}")
            
            # ========================================
            # 7. AUTO-RECOVERY SI ES NECESARIO (NO BLOQUEAR)
            # ========================================
            if overall_status in ["unhealthy", "offline"]:
                try:
                    result = await self.db.execute(
                        select(ProxyScore).where(ProxyScore.proxy_id == proxy_id)
                    )
                    score = result.scalar_one_or_none()
                    
                    if score and score.consecutive_failures >= 10:
                        logger.error(
                            f"🛑 CIRCUIT BREAKER: Proxy {proxy_id} tiene "
                            f"{score.consecutive_failures} fallos consecutivos"
                        )
                    else:
                        logger.warning(f"⚠️ Proxy {proxy_id} unhealthy, triggering auto-recovery")
                        await self._attempt_auto_recovery_smart(proxy)
                except Exception as e:
                    logger.error(f"Auto-recovery failed for proxy {proxy_id}: {e}")
            
            # ========================================
            # 8. ✅ RETORNAR RESULTADO COMPLETO (NUNCA None)
            # ========================================
            return {
                "proxy_id": proxy_id,
                "overall_status": overall_status,
                "overall_score": overall_score,
                "speed_test": speed_result,
                "availability": availability_result,
                "geo_verification": geo_result,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            # ✅ ÚLTIMO RECURSO: Si todo falla, retornar estructura básica
            logger.error(f"❌ CRITICAL: Comprehensive health check failed for proxy {proxy_id}: {e}")
            return {
                "proxy_id": proxy_id,
                "overall_status": "error",
                "overall_score": 0,
                "error": str(e),
                "speed_test": {"status": "failed"},
                "availability": {"is_available": False},
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
                        f"{score_record.consecutive_failures} failures (threshold: {self.MAX_CONSECUTIVE_FAILURES})"
                    )
            
            # ✅ CIRCUIT BREAKER: Marcar como unavailable después de 10 fallos
            if score_record.consecutive_failures >= 10:
                logger.error(
                    f"🛑 CIRCUIT BREAKER: Proxy {proxy_id} alcanzó 10 fallos consecutivos. "
                    f"Marcando como UNAVAILABLE."
                )
                
                # Actualizar el proxy también
                from app.models.proxy import Proxy
                proxy_result = await self.db.execute(
                    select(Proxy).where(Proxy.id == proxy_id)
                )
                proxy = proxy_result.scalar_one_or_none()
                
                if proxy:
                    proxy.is_available = False
                    proxy.status = ProxyStatus.FAILED
            
            score_record.last_check_at = datetime.utcnow()
            score_record.score_updated_at = datetime.utcnow()
            
            await self.db.commit()
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating score: {e}")
    
    # app/services/proxy_health_service.py - LÍNEA ~440
    async def _attempt_auto_recovery_smart(self, proxy: Proxy):
        """✅ Auto-recovery con circuit breaker y validación - CORREGIDO"""
        
        # ========================================
        # ✅ IMPORTAR ProxyScore AL INICIO
        # ========================================
        from app.models.proxy_health import ProxyScore
        
        # ========================================
        # 🛑 CIRCUIT BREAKER: Detener si ya intentó muchas veces
        # ========================================
        result = await self.db.execute(
            select(ProxyScore).where(ProxyScore.proxy_id == proxy.id)
        )
        score = result.scalar_one_or_none()
        
        if score and score.consecutive_failures >= 10:
            logger.error(
                f"🛑 CIRCUIT BREAKER: Proxy {proxy.id} tiene {score.consecutive_failures} fallos consecutivos. "
                f"Auto-recovery deshabilitado. Requiere intervención manual."
            )
            return
        
        logger.info(f"🔄 Smart auto-recovery: Proxy {proxy.id} (attempt #{score.consecutive_failures if score else 0})")
        
        try:
            # ✅ EXTRAER BASE USERNAME CORRECTO
            current_username = proxy.username or ""
            
            # El base_username debe ser el package-XXXXXX del PROXY, no de settings
            if current_username.startswith("package-") and "-country-" in current_username:
                base_username = current_username.split("-country-")[0]
                logger.info(f"✓ Base username extraído: {base_username}")
            elif settings.SOAX_USERNAME.startswith("package-"):
                base_username = settings.SOAX_USERNAME
                logger.warning(f"⚠️ Usando SOAX_USERNAME como fallback: {base_username}")
            else:
                logger.error(
                    f"❌ No se pudo extraer base username. "
                    f"Current: '{current_username}', Settings: '{settings.SOAX_USERNAME}'"
                )
                return
            
            # ========================================
            # GENERAR NUEVA SESIÓN (MISMA CIUDAD PRIMERO)
            # ========================================
            from app.utils.soax_cities_manager import get_soax_username_with_dynamic_city
            
            logger.info(
                f"🔍 Intentando recuperar en misma ciudad: {proxy.city or 'N/A'}, "
                f"región: {proxy.region or 'N/A'}"
            )
            
            result = await get_soax_username_with_dynamic_city(
                base_username=base_username,
                country=proxy.country or "ec",
                region=proxy.region,
                preferred_city=proxy.city,
                session_lifetime=proxy.session_lifetime or 3600
            )
            
            new_username = result["username"]
            selected_city = result.get("selected_city")
            
            # ✅ VALIDAR username generado
            if not new_username.startswith("package-"):
                logger.error(f"❌ Username generado inválido: '{new_username}'")
                return
            
            # ========================================
            # ACTUALIZAR PROXY
            # ========================================
            proxy.username = new_username
            proxy.session_id = new_username.split("sessionid-")[1].split("-")[0]
            proxy.status = ProxyStatus.ACTIVE
            
            # ✅ Actualizar ciudad solo si cambió
            if selected_city and selected_city != proxy.city:
                proxy.city = selected_city
                logger.info(f"📍 Ciudad actualizada: {proxy.city} → {selected_city}")
            
            await self.db.commit()
            
            logger.info(
                f"✅ Auto-recovery completado:\n"
                f"   Proxy {proxy.id}\n"
                f"   Ciudad: {selected_city or proxy.city or 'N/A'}\n"
                f"   Username: {new_username[:70]}..."
            )
            
            # ========================================
            # RE-VERIFICAR (CON RATE LIMITING)
            # ========================================
            logger.info(f"⏳ Esperando 10s antes de re-verificar...")
            await asyncio.sleep(10)
            
            check_result = await self.comprehensive_health_check(
                proxy_id=proxy.id,
                test_multiple_sessions=False
            )
            
            # ========================================
            # RESULTADO
            # ========================================
            if check_result["overall_status"] == "healthy":
                logger.info(f"🎉 Recovery successful: Proxy {proxy.id}")
                
                # Reset blacklist y contadores
                score_result = await self.db.execute(
                    select(ProxyScore).where(ProxyScore.proxy_id == proxy.id)
                )
                score = score_result.scalar_one_or_none()
                
                if score:
                    score.is_blacklisted = False
                    score.blacklist_reason = None
                    score.blacklisted_at = None
                    score.consecutive_failures = 0  # ✅ RESET CONTADOR
                    await self.db.commit()
                    logger.info(f"✓ Contadores reseteados para proxy {proxy.id}")
            else:
                logger.warning(
                    f"⚠️ Recovery falló para proxy {proxy.id}. "
                    f"Status: {check_result['overall_status']}"
                )
                
                # ✅ INCREMENTAR contador de fallos (para circuit breaker)
                score_result = await self.db.execute(
                    select(ProxyScore).where(ProxyScore.proxy_id == proxy.id)
                )
                score = score_result.scalar_one_or_none()
                
                if score:
                    score.consecutive_failures = (score.consecutive_failures or 0) + 1
                    await self.db.commit()
        
        except Exception as e:
            logger.error(f"Error in auto-recovery: {e}")
            import traceback
            logger.error(traceback.format_exc())

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
        """✅ Health check MASIVO - NUNCA retorna None"""
        
        # ========================================
        # 1. OBTENER IDs DE PROXIES
        # ========================================
        query = select(Proxy.id)
        
        if only_active:
            query = query.where(
                and_(
                    Proxy.is_available == True,
                    Proxy.status == ProxyStatus.ACTIVE
                )
            )
        
        try:
            result = await self.db.execute(query)
            proxy_ids = [row[0] for row in result.all()]
        except Exception as e:
            logger.error(f"Failed to fetch proxy IDs: {e}")
            return {
                "total": 0,
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0,
                "offline": 0,
                "details": [],
                "error": str(e)
            }
        
        logger.info(f"🏥 Starting batch health check: {len(proxy_ids)} proxies")
        
        results = {
            "total": len(proxy_ids),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "offline": 0,
            "details": []
        }
        
        if not proxy_ids:
            logger.warning("No proxies to check")
            return results
        
        # ========================================
        # 2. FUNCIÓN CON SESIÓN INDEPENDIENTE
        # ========================================
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def check_with_independent_session(proxy_id: int):
            """✅ NUNCA retorna None - siempre retorna Dict"""
            from app.database import AsyncSessionLocal
            
            async with semaphore:
                try:
                    async with AsyncSessionLocal() as independent_db:
                        independent_service = ProxyHealthService(independent_db)
                        
                        result = await independent_service.comprehensive_health_check(
                            proxy_id=proxy_id,
                            test_multiple_sessions=False
                        )
                        
                        # ✅ VALIDACIÓN: Si result es None, crear estructura básica
                        if result is None:
                            logger.error(f"Health check returned None for proxy {proxy_id}")
                            return {
                                "proxy_id": proxy_id,
                                "overall_status": "error",
                                "overall_score": 0,
                                "error": "Health check returned None"
                            }
                        
                        return result
                
                except Exception as e:
                    logger.error(f"Exception in check_with_independent_session for proxy {proxy_id}: {e}")
                    return {
                        "proxy_id": proxy_id,
                        "overall_status": "error",
                        "overall_score": 0,
                        "error": str(e)
                    }
        
        # ========================================
        # 3. EJECUTAR EN PARALELO
        # ========================================
        try:
            tasks = [
                check_with_independent_session(proxy_id) 
                for proxy_id in proxy_ids
            ]
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Failed to gather health check tasks: {e}")
            return {
                **results,
                "error": f"Failed to execute batch: {str(e)}"
            }
        
        # ========================================
        # 4. PROCESAR RESULTADOS
        # ========================================
        for check_result in check_results:
            # Manejar excepciones
            if isinstance(check_result, Exception):
                logger.error(f"Task failed with exception: {check_result}")
                results["offline"] += 1
                continue
            
            # ✅ VALIDACIÓN: Si es None, marcarlo como error
            if check_result is None:
                logger.error("Health check returned None, marcando como offline")
                results["offline"] += 1
                results["details"].append({
                    "proxy_id": None,
                    "overall_status": "error",
                    "error": "None returned"
                })
                continue
            
            # ✅ Validar que sea un dict
            if not isinstance(check_result, dict):
                logger.error(f"Invalid result type: {type(check_result)}")
                results["offline"] += 1
                continue
            
            status = check_result.get("overall_status", "error")
            
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