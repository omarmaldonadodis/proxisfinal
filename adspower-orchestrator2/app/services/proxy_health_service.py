# app/services/proxy_health_service.py
"""
Servicio profesional de health monitoring para proxies SOAX
Incluye: velocidad, disponibilidad, geo-verificación, auto-recuperación
"""
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from datetime import datetime, timedelta
from loguru import logger
import httpx
import asyncio
import time

from app.models.proxy import Proxy, ProxyStatus
from app.models.proxy_health import ProxyHealthCheck, ProxyScore, HealthCheckStatus
from app.integrations.soax_client import SOAXClient


class ProxyHealthService:
    """Servicio de monitoreo de salud de proxies"""
    
    # URLs de test (múltiples para redundancia)
    TEST_URLS = [
        "https://api.ipify.org?format=json",
        "http://ip-api.com/json/",
        "https://ipinfo.io/json",
        "https://httpbin.org/ip",
    ]
    
    # Speed test URLs (archivos pequeños)
    SPEED_TEST_URLS = [
        "https://httpbin.org/bytes/1024",  # 1KB
        "https://httpbin.org/bytes/10240",  # 10KB
    ]
    
    # Thresholds
    MAX_LATENCY_MS = 3000  # 3 segundos
    MIN_SPEED_SCORE = 60.0
    MAX_CONSECUTIVE_FAILURES = 3
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def comprehensive_health_check(
        self,
        proxy_id: int,
        test_multiple_sessions: bool = True
    ) -> Dict:
        """
        Verificación completa de un proxy
        
        Incluye:
        - Velocidad (latencia, download)
        - Disponibilidad
        - Geo-verificación
        - Test con múltiples sesiones (opcional)
        
        Returns:
            {
                "proxy_id": 1,
                "overall_status": "healthy",
                "speed_test": {...},
                "geo_verification": {...},
                "availability": {...},
                "session_tests": [...],
                "score": 95.5
            }
        """
        
        # Obtener proxy
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        
        if not proxy:
            raise ValueError(f"Proxy {proxy_id} not found")
        
        logger.info(f"Starting comprehensive health check for proxy {proxy_id}")
        
        # 1. Speed Test
        speed_result = await self._test_speed(proxy)
        
        # 2. Availability Check
        availability_result = await self._test_availability(proxy)
        
        # 3. Geo Verification
        geo_result = await self._verify_geo_location(proxy)
        
        # 4. Test con múltiples sesiones (si está habilitado)
        session_tests = []
        if test_multiple_sessions:
            session_tests = await self._test_multiple_sessions(proxy, count=3)
        
        # 5. Calcular score general
        overall_score = await self._calculate_score(
            speed_result,
            availability_result,
            geo_result,
            session_tests
        )
        
        # 6. Determinar estado general
        overall_status = self._determine_status(overall_score, availability_result)
        
        # 7. Guardar resultados en DB
        await self._save_health_check(
            proxy_id=proxy_id,
            speed=speed_result,
            availability=availability_result,
            geo=geo_result,
            sessions=session_tests
        )
        
        # 8. Actualizar score del proxy
        await self._update_proxy_score(proxy_id, overall_score, {
            "speed": speed_result,
            "availability": availability_result,
            "geo": geo_result
        })
        
        # 9. Auto-recovery si es necesario
        if overall_status == "unhealthy":
            await self._attempt_auto_recovery(proxy)
        
        return {
            "proxy_id": proxy_id,
            "overall_status": overall_status,
            "overall_score": overall_score,
            "speed_test": speed_result,
            "geo_verification": geo_result,
            "availability": availability_result,
            "session_tests": session_tests,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _test_speed(self, proxy: Proxy) -> Dict:
        """Test de velocidad del proxy"""
        
        proxy_url = self._build_proxy_url(proxy)
        
        results = {
            "latency_ms": None,
            "download_speed_mbps": None,
            "status": "pending"
        }
        
        try:
            # 1. Latency Test
            start_time = time.time()
            
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0
            ) as client:
                response = await client.get(self.TEST_URLS[0])
                
                latency = (time.time() - start_time) * 1000
                results["latency_ms"] = round(latency, 2)
                
                # 2. Download Speed Test (archivo pequeño)
                start_time = time.time()
                response = await client.get(self.SPEED_TEST_URLS[1])  # 10KB
                download_time = time.time() - start_time
                
                file_size_mb = 10240 / (1024 * 1024)  # 10KB en MB
                download_speed = file_size_mb / download_time if download_time > 0 else 0
                results["download_speed_mbps"] = round(download_speed, 2)
                
                results["status"] = "success"
                
                logger.info(
                    f"Speed test: Proxy {proxy.id} - "
                    f"Latency: {results['latency_ms']}ms, "
                    f"Speed: {results['download_speed_mbps']} Mbps"
                )
        
        except asyncio.TimeoutError:
            results["status"] = "timeout"
            logger.warning(f"Speed test timeout for proxy {proxy.id}")
        
        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            logger.error(f"Speed test failed for proxy {proxy.id}: {e}")
        
        return results
    
    async def _test_availability(self, proxy: Proxy) -> Dict:
        """Test de disponibilidad"""
        
        proxy_url = self._build_proxy_url(proxy)
        
        results = {
            "is_available": False,
            "response_code": None,
            "test_url": None,
            "status": "pending"
        }
        
        # Probar con múltiples URLs para redundancia
        for test_url in self.TEST_URLS:
            try:
                async with httpx.AsyncClient(
                    proxies={"http://": proxy_url, "https://": proxy_url},
                    timeout=10.0
                ) as client:
                    response = await client.get(test_url)
                    
                    if response.status_code == 200:
                        results["is_available"] = True
                        results["response_code"] = 200
                        results["test_url"] = test_url
                        results["status"] = "success"
                        
                        logger.info(f"Availability: Proxy {proxy.id} is available")
                        return results
            
            except Exception as e:
                logger.debug(f"Availability test failed with {test_url}: {e}")
                continue
        
        # Si llegó aquí, falló con todas las URLs
        results["status"] = "failed"
        logger.warning(f"Availability: Proxy {proxy.id} is unavailable")
        
        return results
    
    async def _verify_geo_location(self, proxy: Proxy) -> Dict:
        """Verificación de ubicación geográfica"""
        
        proxy_url = self._build_proxy_url(proxy)
        
        results = {
            "detected_ip": None,
            "detected_country": None,
            "detected_city": None,
            "detected_isp": None,
            "expected_country": proxy.country,
            "geo_match": False,
            "status": "pending"
        }
        
        try:
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0
            ) as client:
                # Usar ip-api.com para geo info completa
                response = await client.get("http://ip-api.com/json/")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    results["detected_ip"] = data.get("query")
                    results["detected_country"] = data.get("countryCode")
                    results["detected_city"] = data.get("city")
                    results["detected_isp"] = data.get("isp")
                    
                    # Verificar coincidencia de país
                    if proxy.country:
                        results["geo_match"] = (
                            results["detected_country"] and
                            results["detected_country"].lower() == proxy.country.lower()
                        )
                    else:
                        results["geo_match"] = True  # No hay país esperado
                    
                    results["status"] = "success"
                    
                    match_status = "✓" if results["geo_match"] else "✗"
                    logger.info(
                        f"Geo verification: Proxy {proxy.id} - "
                        f"{match_status} Expected: {proxy.country}, "
                        f"Detected: {results['detected_country']}"
                    )
        
        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            logger.error(f"Geo verification failed for proxy {proxy.id}: {e}")
        
        return results
    
    async def _test_multiple_sessions(
        self,
        proxy: Proxy,
        count: int = 3
    ) -> List[Dict]:
        """Test con múltiples sesiones para verificar rotación"""
        
        results = []
        
        for i in range(count):
            # Generar nueva sesión
            new_session_id = f"test_session_{int(time.time())}_{i}"
            
            # Crear proxy temporal con nueva sesión
            temp_proxy_config = {
                "type": proxy.proxy_type,
                "host": proxy.host,
                "port": proxy.port,
                "username": proxy.username.replace(
                    f"sessionid-{proxy.session_id}",
                    f"sessionid-{new_session_id}"
                ) if proxy.username else None,
                "password": proxy.password
            }
            
            proxy_url = (
                f"http://{temp_proxy_config['username']}:{temp_proxy_config['password']}"
                f"@{temp_proxy_config['host']}:{temp_proxy_config['port']}"
            )
            
            try:
                async with httpx.AsyncClient(
                    proxies={"http://": proxy_url, "https://": proxy_url},
                    timeout=10.0
                ) as client:
                    response = await client.get("https://api.ipify.org?format=json")
                    
                    if response.status_code == 200:
                        ip = response.json().get("ip")
                        
                        results.append({
                            "session_id": new_session_id,
                            "ip": ip,
                            "success": True,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        
                        logger.debug(f"Session test {i+1}: IP={ip}")
            
            except Exception as e:
                results.append({
                    "session_id": new_session_id,
                    "success": False,
                    "error": str(e)
                })
                logger.debug(f"Session test {i+1} failed: {e}")
            
            # Pequeña pausa entre tests
            await asyncio.sleep(1)
        
        # Verificar rotación
        unique_ips = set(r["ip"] for r in results if r.get("success"))
        
        logger.info(
            f"Session rotation test: Proxy {proxy.id} - "
            f"{len(unique_ips)}/{count} unique IPs"
        )
        
        return results
    
    async def _calculate_score(
        self,
        speed: Dict,
        availability: Dict,
        geo: Dict,
        sessions: List[Dict]
    ) -> float:
        """Calcula score general del proxy (0-100)"""
        
        scores = []
        
        # 1. Speed Score (40% del total)
        if speed["status"] == "success" and speed["latency_ms"]:
            if speed["latency_ms"] < 500:
                speed_score = 100
            elif speed["latency_ms"] < 1000:
                speed_score = 80
            elif speed["latency_ms"] < 2000:
                speed_score = 60
            elif speed["latency_ms"] < 3000:
                speed_score = 40
            else:
                speed_score = 20
            
            scores.append(("speed", speed_score, 0.40))
        else:
            scores.append(("speed", 0, 0.40))
        
        # 2. Availability Score (30% del total)
        availability_score = 100 if availability["is_available"] else 0
        scores.append(("availability", availability_score, 0.30))
        
        # 3. Geo Accuracy Score (20% del total)
        geo_score = 100 if geo["geo_match"] else 50  # 50 si no coincide pero funciona
        scores.append(("geo", geo_score, 0.20))
        
        # 4. Session Rotation Score (10% del total)
        if sessions:
            successful_sessions = sum(1 for s in sessions if s.get("success"))
            session_score = (successful_sessions / len(sessions)) * 100
        else:
            session_score = 100  # No se testeó, asumir OK
        
        scores.append(("sessions", session_score, 0.10))
        
        # Calcular score ponderado
        overall_score = sum(score * weight for _, score, weight in scores)
        
        logger.debug(f"Score breakdown: {scores} -> Overall: {overall_score:.2f}")
        
        return round(overall_score, 2)
    
    def _determine_status(self, score: float, availability: Dict) -> str:
        """Determina estado general del proxy"""
        
        if not availability["is_available"]:
            return "offline"
        
        if score >= 80:
            return "healthy"
        elif score >= 60:
            return "degraded"
        else:
            return "unhealthy"
    
    async def _save_health_check(
        self,
        proxy_id: int,
        speed: Dict,
        availability: Dict,
        geo: Dict,
        sessions: List[Dict]
    ):
        """Guarda resultados en DB"""
        
        health_check = ProxyHealthCheck(
            proxy_id=proxy_id,
            status=availability["status"],
            check_type="comprehensive",
            latency_ms=speed.get("latency_ms"),
            download_speed_mbps=speed.get("download_speed_mbps"),
            detected_ip=geo.get("detected_ip"),
            detected_country=geo.get("detected_country"),
            detected_city=geo.get("detected_city"),
            detected_isp=geo.get("detected_isp"),
            geo_match=geo.get("geo_match", False),
            is_available=availability["is_available"],
            response_code=availability.get("response_code"),
            session_test_result=sessions if sessions else None,
            test_urls=self.TEST_URLS,
            raw_response={
                "speed": speed,
                "availability": availability,
                "geo": geo
            }
        )
        
        self.db.add(health_check)
        await self.db.commit()
    
    async def _update_proxy_score(
        self,
        proxy_id: int,
        overall_score: float,
        details: Dict
    ):
        """Actualiza score del proxy"""
        
        # Buscar score existente
        result = await self.db.execute(
            select(ProxyScore).where(ProxyScore.proxy_id == proxy_id)
        )
        score_record = result.scalar_one_or_none()
        
        if not score_record:
            # Crear nuevo
            score_record = ProxyScore(proxy_id=proxy_id)
            self.db.add(score_record)
        
        # Actualizar scores
        score_record.overall_score = overall_score
        
        # Actualizar estadísticas
        score_record.total_checks += 1
        
        if details["availability"]["is_available"]:
            score_record.successful_checks += 1
        else:
            score_record.failed_checks += 1
            score_record.consecutive_failures += 1
        
        # Actualizar latencia
        latency = details["speed"].get("latency_ms")
        if latency:
            if not score_record.avg_latency:
                score_record.avg_latency = latency
            else:
                # Media móvil
                score_record.avg_latency = (
                    score_record.avg_latency * 0.8 + latency * 0.2
                )
            
            if not score_record.min_latency or latency < score_record.min_latency:
                score_record.min_latency = latency
            
            if not score_record.max_latency or latency > score_record.max_latency:
                score_record.max_latency = latency
        
        # Uptime percentage
        if score_record.total_checks > 0:
            score_record.uptime_percentage = (
                score_record.successful_checks / score_record.total_checks * 100
            )
        
        # Geo mismatch
        if not details["geo"].get("geo_match"):
            score_record.geo_mismatch_count += 1
        
        # Blacklist automático
        if score_record.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            score_record.is_blacklisted = True
            score_record.blacklist_reason = (
                f"{score_record.consecutive_failures} consecutive failures"
            )
            score_record.blacklisted_at = datetime.utcnow()
            
            logger.warning(f"Proxy {proxy_id} blacklisted: {score_record.blacklist_reason}")
        
        score_record.last_check_at = datetime.utcnow()
        score_record.score_updated_at = datetime.utcnow()
        
        await self.db.commit()
    
    async def _attempt_auto_recovery(self, proxy: Proxy):
        """Intenta recuperar proxy automáticamente"""
        
        logger.info(f"Attempting auto-recovery for proxy {proxy.id}")
        
        # Estrategia 1: Rotar sesión
        from app.integrations.soax_client import SOAXClient
        
        soax = SOAXClient(
            username=proxy.username.split('-')[0] if proxy.username else "",
            password=proxy.password or ""
        )
        
        # Generar nueva sesión
        new_config = soax.get_proxy_config(
            proxy_type=proxy.proxy_type,
            country=proxy.country,
            city=proxy.city
        )
        
        # Actualizar proxy
        proxy.session_id = new_config["session_id"]
        proxy.username = new_config["username"]
        
        await self.db.commit()
        
        logger.info(f"Auto-recovery: New session ID for proxy {proxy.id}")
        
        # Re-test después de 30 segundos
        await asyncio.sleep(30)
        result = await self.comprehensive_health_check(proxy.id, test_multiple_sessions=False)
        
        if result["overall_status"] == "healthy":
            logger.info(f"✓ Auto-recovery successful for proxy {proxy.id}")
            
            # Reset consecutive failures
            score_result = await self.db.execute(
                select(ProxyScore).where(ProxyScore.proxy_id == proxy.id)
            )
            score = score_result.scalar_one_or_none()
            if score:
                score.consecutive_failures = 0
                score.last_recovery_attempt = datetime.utcnow()
                await self.db.commit()
        else:
            logger.warning(f"✗ Auto-recovery failed for proxy {proxy.id}")
    
    def _build_proxy_url(self, proxy: Proxy) -> str:
        """Construye URL del proxy"""
        return (
            f"http://{proxy.username}:{proxy.password}"
            f"@{proxy.host}:{proxy.port}"
        )
    
    # ========================================
    # MÉTODOS PARA MONITOREO EN BATCH
    # ========================================
    
    async def health_check_all_proxies(
        self,
        only_active: bool = True,
        max_concurrent: int = 10
    ) -> Dict:
        """Ejecuta health check en todos los proxies (paralelo)"""
        
        # Obtener proxies
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
        
        logger.info(f"Starting health check for {len(proxies)} proxies")
        
        results = {
            "total": len(proxies),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "offline": 0,
            "details": []
        }
        
        # Ejecutar en paralelo con límite de concurrencia
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def check_with_semaphore(proxy):
            async with semaphore:
                try:
                    return await self.comprehensive_health_check(
                        proxy.id,
                        test_multiple_sessions=False  # Más rápido
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
        
        # Consolidar resultados
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
            f"Health check completed: "
            f"{results['healthy']} healthy, "
            f"{results['degraded']} degraded, "
            f"{results['unhealthy']} unhealthy, "
            f"{results['offline']} offline"
        )
        
        return results
    
    async def get_proxy_health_history(
        self,
        proxy_id: int,
        limit: int = 100
    ) -> List[ProxyHealthCheck]:
        """Obtiene historial de health checks"""
        
        result = await self.db.execute(
            select(ProxyHealthCheck)
            .where(ProxyHealthCheck.proxy_id == proxy_id)
            .order_by(desc(ProxyHealthCheck.checked_at))
            .limit(limit)
        )
        
        return list(result.scalars().all())
    
    async def get_top_performing_proxies(
        self,
        limit: int = 10,
        min_score: float = 80.0
    ) -> List[Dict]:
        """Obtiene proxies con mejor rendimiento"""
        
        result = await self.db.execute(
            select(Proxy, ProxyScore)
            .join(ProxyScore)
            .where(
                and_(
                    ProxyScore.overall_score >= min_score,
                    ProxyScore.is_blacklisted == False,
                    Proxy.is_available == True
                )
            )
            .order_by(desc(ProxyScore.overall_score))
            .limit(limit)
        )
        
        rows = result.all()
        
        return [
            {
                "proxy_id": proxy.id,
                "proxy_type": proxy.proxy_type,
                "country": proxy.country,
                "score": score.overall_score,
                "uptime": score.uptime_percentage,
                "avg_latency": score.avg_latency
            }
            for proxy, score in rows
        ]