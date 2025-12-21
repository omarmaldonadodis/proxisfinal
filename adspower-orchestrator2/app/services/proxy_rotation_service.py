# app/services/proxy_rotation_service.py - ✅ VERSIÓN CORREGIDA COMPLETA

"""
Sistema de Rotación de Proxies con:
1. Validación de conectividad AdsPower
2. Formato correcto API v2
3. Manejo robusto de errores
4. Retry con backoff exponencial
"""

from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import httpx
import time
import secrets

from app.models.proxy import Proxy, ProxyStatus
from app.models.profile import Profile
from app.models.computer import Computer
from app.integrations.adspower_client import AdsPowerClient
from app.utils.soax_cities_manager import (
    SOAXCitiesManager,
    get_soax_username_with_dynamic_city
)
from app.config import settings

from datetime import datetime
import asyncio


class ProxyRotationService:
    """Servicio optimizado para rotación de proxies"""
    
    MAX_LATENCY_MS = 2000
    OPTIMAL_LATENCY_MS = 1000
    
    NEARBY_REGIONS = {
        "pichincha": ["cotopaxi", "imbabura", "santo-domingo"],
        "guayas": ["los-rios", "santa-elena", "manabi"],
        "azuay": ["canar", "el-oro", "loja"],
        "manabi": ["santo-domingo", "guayas", "esmeraldas"],
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_and_rotate_proxy(self, proxy_id: int) -> Dict:
        """🎯 Verifica y rota proxy si es necesario"""
        
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        
        if not proxy:
            return {"error": "Proxy no encontrado"}
        
        logger.info(f"🔍 Verificando proxy {proxy_id}: {proxy.city}, {proxy.region}")
        
        old_latency = await self._ping_proxy(proxy)
        
        if old_latency is None:
            logger.error(f"❌ Proxy {proxy_id} está OFFLINE")
            proxy.status = ProxyStatus.FAILED
            await self.db.commit()
            return {
                "rotated": False,
                "error": "Proxy offline",
                "old_latency_ms": None
            }
        
        if old_latency < self.MAX_LATENCY_MS:
            logger.info(f"✅ Proxy {proxy_id} está óptimo ({old_latency}ms)")
            
            proxy.avg_response_time = old_latency
            proxy.last_check_at = datetime.utcnow()
            proxy.status = ProxyStatus.ACTIVE
            await self.db.commit()
            
            return {
                "rotated": False,
                "reason": "optimal",
                "old_latency_ms": old_latency,
                "message": f"Proxy óptimo ({old_latency}ms)"
            }
        
        logger.warning(f"⚠️ Proxy {proxy_id} LENTO ({old_latency}ms) → Rotando...")
        
        new_session = None
        
        if proxy.city:
            new_session = await self._rotate_same_city(proxy)
        
        if not new_session and proxy.region:
            new_session = await self._rotate_nearby_city_in_region(proxy)
        
        if not new_session:
            new_session = await self._rotate_nearby_region(proxy)
        
        if not new_session:
            logger.warning("⚠️ Usando fallback: Guayaquil")
            new_session = await self._rotate_to_fallback()
        
        if not new_session:
            logger.error(f"❌ No se pudo rotar proxy {proxy_id}")
            return {
                "rotated": False,
                "error": "No hay ubicaciones disponibles",
                "old_latency_ms": old_latency
            }
        
        old_location = f"{proxy.city or proxy.region}, {proxy.country}"
        
        old_username = proxy.username
        old_session_id = proxy.session_id
        old_city = proxy.city
        old_region = proxy.region
        
        proxy.username = new_session["username"]
        proxy.session_id = new_session["session_id"]
        proxy.city = new_session.get("city")
        proxy.region = new_session.get("region")
        proxy.country = new_session.get("country", "ec")
        
        new_latency = await self._ping_proxy(proxy)
        
        if new_latency is None:
            logger.error("❌ Nueva sesión falló, rollback")
            
            proxy.username = old_username
            proxy.session_id = old_session_id
            proxy.city = old_city
            proxy.region = old_region
            
            await self.db.rollback()
            return {
                "rotated": False,
                "error": "Nueva sesión falló",
                "old_latency_ms": old_latency
            }
        
        logger.info(f"🔄 Actualizando perfiles en AdsPower con nuevo proxy...")
        
        adspower_success = await self._update_adspower_profiles_with_retry(proxy)
        
        if not adspower_success:
            logger.error("❌ Error actualizando AdsPower, rollback")
            
            proxy.username = old_username
            proxy.session_id = old_session_id
            proxy.city = old_city
            proxy.region = old_region
            
            await self.db.rollback()
            
            return {
                "rotated": False,
                "error": "Error sincronizando con AdsPower (timeout o conexión fallida)",
                "old_latency_ms": old_latency
            }
        
        proxy.avg_response_time = new_latency
        proxy.last_check_at = datetime.utcnow()
        proxy.status = ProxyStatus.ACTIVE
        await self.db.commit()
        
        new_location = f"{proxy.city or proxy.region}, {proxy.country}"
        
        logger.info(
            f"✅ Proxy {proxy_id} rotado y sincronizado: "
            f"{old_location} ({old_latency}ms) → {new_location} ({new_latency}ms)"
        )
        
        return {
            "rotated": True,
            "old_location": old_location,
            "new_location": new_location,
            "old_latency_ms": old_latency,
            "new_latency_ms": new_latency,
            "improvement_ms": old_latency - new_latency,
            "adspower_updated": True,
            "message": f"✅ Mejorado de {old_latency}ms a {new_latency}ms"
        }
    
    async def _update_adspower_profiles_with_retry(
        self, 
        proxy: Proxy,
        max_retries: int = 3
    ) -> bool:
        """
        ✅ CRÍTICO: Actualiza profiles con retry automático
        
        Cambios:
        1. Verifica conectividad ANTES de cada intento
        2. Backoff exponencial entre reintentos
        3. Timeout reducido a 30s por intento
        """
        
        for attempt in range(max_retries):
            if attempt > 0:
                wait_time = min(2 ** attempt, 10)  # Exponential backoff (max 10s)
                logger.info(f"🔄 Reintento {attempt}/{max_retries} en {wait_time}s...")
                await asyncio.sleep(wait_time)
            
            # ✅ VERIFICAR CONECTIVIDAD ANTES DE INTENTAR
            result = await self.db.execute(
                select(Profile).where(Profile.proxy_id == proxy.id).limit(1)
            )
            sample_profile = result.scalar_one_or_none()
            
            if sample_profile:
                result = await self.db.execute(
                    select(Computer).where(Computer.id == sample_profile.computer_id)
                )
                computer = result.scalar_one_or_none()
                
                if computer:
                    is_reachable = await self._check_adspower_connectivity(computer)
                    
                    if not is_reachable:
                        logger.error(
                            f"❌ AdsPower en {computer.ip_address}:{computer.adspower_api_url} "
                            f"NO RESPONDE - Saltando intento {attempt + 1}"
                        )
                        continue  # Pasar al siguiente intento
            
            # Ejecutar actualización
            success = await self._update_adspower_profiles_sync(proxy, timeout=30.0)
            
            if success:
                return True
            
            logger.warning(f"⚠️ Intento {attempt + 1} falló")
        
        return False
    
    async def _check_adspower_connectivity(self, computer: Computer) -> bool:
        """
        ✅ NUEVO: Verifica que AdsPower responda ANTES de intentar actualizar
        
        Returns:
            True si AdsPower responde, False si no
        """
        try:
            client = AdsPowerClient(
                api_url=computer.adspower_api_url,
                api_key=computer.adspower_api_key
            )
            
            # Test simple: listar 1 profile
            async with httpx.AsyncClient(timeout=5.0) as http_client:
                response = await http_client.get(
                    f"{computer.adspower_api_url}/api/v1/user/list",
                    params={"page": 1, "page_size": 1},
                    headers={"Authorization": f"Bearer {computer.adspower_api_key}"}
                )
                
                if response.status_code == 200:
                    logger.debug(f"✅ AdsPower respondió: {computer.ip_address}")
                    return True
                else:
                    logger.warning(
                        f"⚠️ AdsPower retornó {response.status_code}: {computer.ip_address}"
                    )
                    return False
        
        except httpx.TimeoutException:
            logger.error(f"⏱️ Timeout verificando AdsPower: {computer.ip_address}")
            return False
        
        except Exception as e:
            logger.error(f"❌ Error verificando AdsPower: {e}")
            return False
    
    async def _update_adspower_profiles_sync(
        self, 
        proxy: Proxy,
        timeout: float = 30.0
    ) -> bool:
        """
        ✅ FORMATO CORRECTO según documentación AdsPower
        
        Documentación: https://localapi-doc-en.adspower.com/docs/Update-Profile-Info-V2
        
        CRÍTICO: AdsPower espera el formato EXACTO del ejemplo de creación:
        {
            "user_id": "k182wa7h",
            "user_proxy_config": {
                "proxy_soft": "other",
                "proxy_type": "http",
                "proxy_host": "proxy.soax.com",
                "proxy_port": "5000",  # ⚠️ STRING en docs oficiales
                "proxy_user": "user",
                "proxy_password": "pass"
            }
        }
        """
        
        result = await self.db.execute(
            select(Profile).where(Profile.proxy_id == proxy.id)
        )
        profiles = list(result.scalars().all())
        
        if not profiles:
            logger.info(f"ℹ️ Proxy {proxy.id} no tiene profiles asignados")
            return True
        
        logger.info(f"🔄 Actualizando {len(profiles)} profiles en AdsPower...")
        
        # ✅ FORMATO EXACTO según documentación
        proxy_config = {
            "user_proxy_config": {
                "proxy_soft": "other",
                "proxy_type": "http",  # SOAX siempre usa http
                "proxy_host": proxy.host,
                "proxy_port": str(proxy.port),  # ⚠️ STRING según docs
                "proxy_user": proxy.username or "",
                "proxy_password": proxy.password or ""
            }
        }
        
        # ✅ LOG DETALLADO
        logger.info(f"📤 Datos para AdsPower API v2:")
        logger.info(f"   proxy_soft: {proxy_config['user_proxy_config']['proxy_soft']}")
        logger.info(f"   proxy_type: {proxy_config['user_proxy_config']['proxy_type']}")
        logger.info(f"   proxy_host: {proxy_config['user_proxy_config']['proxy_host']}")
        logger.info(f"   proxy_port: {proxy_config['user_proxy_config']['proxy_port']} (type: {type(proxy_config['user_proxy_config']['proxy_port']).__name__})")
        logger.info(f"   proxy_user length: {len(proxy_config['user_proxy_config']['proxy_user'])}")
        
        # Agrupar profiles por computer
        profiles_by_computer = {}
        for profile in profiles:
            if profile.computer_id not in profiles_by_computer:
                profiles_by_computer[profile.computer_id] = []
            profiles_by_computer[profile.computer_id].append(profile)
        
        success_count = 0
        failed_count = 0
        
        for computer_id, computer_profiles in profiles_by_computer.items():
            try:
                result = await self.db.execute(
                    select(Computer).where(Computer.id == computer_id)
                )
                computer = result.scalar_one_or_none()
                
                if not computer:
                    logger.warning(f"⚠️ Computer {computer_id} no encontrado")
                    failed_count += len(computer_profiles)
                    continue
                
                # ✅ USAR HTTPX DIRECTAMENTE (más control)
                async with httpx.AsyncClient(timeout=timeout) as http_client:
                    
                    for profile in computer_profiles:
                        try:
                            url = f"{computer.adspower_api_url}/api/v1/user/update"
                            
                            # ✅ PAYLOAD COMPLETO
                            payload = {
                                "user_id": profile.adspower_id,
                                **proxy_config
                            }
                            
                            logger.info(f"📤 POST {url}")
                            logger.info(f"   Profile: {profile.adspower_id}")
                            
                            response = await http_client.post(
                                url,
                                json=payload,
                                headers={
                                    "Authorization": f"Bearer {computer.adspower_api_key}",
                                    "Content-Type": "application/json"
                                }
                            )
                            
                            logger.info(f"📥 Response: {response.status_code}")
                            
                            if response.status_code == 200:
                                data = response.json()
                                
                                if data.get("code") == 0:
                                    logger.info(f"✅ Profile {profile.id} actualizado")
                                    success_count += 1
                                else:
                                    logger.error(
                                        f"❌ AdsPower error code {data.get('code')}: "
                                        f"{data.get('msg')}"
                                    )
                                    failed_count += 1
                            else:
                                logger.error(
                                    f"❌ HTTP {response.status_code}: {response.text[:200]}"
                                )
                                failed_count += 1
                        
                        except httpx.TimeoutException:
                            logger.error(f"⏱️ Timeout actualizando profile {profile.id}")
                            failed_count += 1
                        
                        except Exception as e:
                            logger.error(f"❌ Error profile {profile.id}: {e}")
                            failed_count += 1
            
            except Exception as e:
                logger.error(f"❌ Error con computer {computer_id}: {e}")
                failed_count += len(computer_profiles)
        
        if failed_count > 0:
            logger.error(
                f"⚠️ Actualización parcial: {success_count} OK, {failed_count} fallidos"
            )
            return False
        
        logger.info(f"✅ Todos los profiles actualizados: {success_count}/{len(profiles)}")
        return True
    
    # ========================================
    # MÉTODOS HELPER (sin cambios)
    # ========================================
    
    async def _ping_proxy(self, proxy: Proxy) -> Optional[int]:
        """Ping simple y rápido"""
        try:
            proxy_url = (
                f"http://{proxy.username}:{proxy.password}"
                f"@{proxy.host}:{proxy.port}"
            )
            
            start = time.time()
            
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0
            ) as client:
                response = await client.get("https://api.ipify.org?format=json")
                
                if response.status_code == 200:
                    latency_ms = int((time.time() - start) * 1000)
                    return latency_ms
            
            return None
        
        except Exception as e:
            logger.debug(f"Ping failed: {e}")
            return None
    
    async def _rotate_same_city(self, proxy: Proxy) -> Optional[Dict]:
        """Rota a nueva sesión en MISMA ciudad"""
        
        if not proxy.city:
            return None
        
        logger.info(f"🔄 Intentando rotar en misma ciudad: {proxy.city}")
        
        available_cities = await SOAXCitiesManager.get_available_cities(
            country=proxy.country or "ec"
        )
        
        city_normalized = proxy.city.lower().replace(" ", "-")
        
        if city_normalized not in available_cities:
            logger.warning(f"Ciudad {proxy.city} no disponible")
            return None
        
        session_id = secrets.token_urlsafe(16)
        
        result = await get_soax_username_with_dynamic_city(
            base_username=settings.SOAX_USERNAME,
            country=proxy.country or "ec",
            preferred_city=city_normalized,
            session_id=session_id,
            session_lifetime=proxy.session_lifetime or 3600
        )
        
        test_proxy = Proxy(
            username=result["username"],
            password=settings.SOAX_PASSWORD,
            host=settings.SOAX_HOST,
            port=settings.SOAX_PORT
        )
        
        latency = await self._ping_proxy(test_proxy)
        
        if latency and latency < self.MAX_LATENCY_MS:
            logger.info(f"✅ Nueva sesión OK: {proxy.city} ({latency}ms)")
            return {
                "username": result["username"],
                "session_id": session_id,
                "city": proxy.city,
                "region": proxy.region,
                "country": proxy.country or "ec",
                "latency_ms": latency
            }
        
        return None
    
    async def _rotate_nearby_city_in_region(self, proxy: Proxy) -> Optional[Dict]:
        """Rota a ciudad cercana en MISMA región"""
        
        if not proxy.region:
            return None
        
        logger.info(f"🔄 Buscando ciudad cercana en región: {proxy.region}")
        
        available_cities = await SOAXCitiesManager.get_available_cities(
            country=proxy.country or "ec"
        )
        
        region_cities = SOAXCitiesManager._get_cities_in_region(proxy.region)
        nearby = [c for c in region_cities if c in available_cities and c != proxy.city]
        
        if not nearby:
            return None
        
        for city in nearby:
            session_id = secrets.token_urlsafe(16)
            
            result = await get_soax_username_with_dynamic_city(
                base_username=settings.SOAX_USERNAME,
                country=proxy.country or "ec",
                preferred_city=city,
                session_id=session_id
            )
            
            test_proxy = Proxy(
                username=result["username"],
                password=settings.SOAX_PASSWORD,
                host=settings.SOAX_HOST,
                port=settings.SOAX_PORT
            )
            
            latency = await self._ping_proxy(test_proxy)
            
            if latency and latency < self.MAX_LATENCY_MS:
                logger.info(f"✅ Ciudad cercana encontrada: {city} ({latency}ms)")
                return {
                    "username": result["username"],
                    "session_id": session_id,
                    "city": city,
                    "region": proxy.region,
                    "country": proxy.country or "ec",
                    "latency_ms": latency
                }
        
        return None
    
    async def _rotate_nearby_region(self, proxy: Proxy) -> Optional[Dict]:
        """Rota a región geográficamente cercana"""
        
        if not proxy.region:
            return None
        
        region_code = proxy.region.lower().replace(" ", "-")
        nearby_regions = self.NEARBY_REGIONS.get(region_code, [])
        
        if not nearby_regions:
            return None
        
        logger.info(f"🔄 Buscando en regiones cercanas: {nearby_regions}")
        
        available_cities = await SOAXCitiesManager.get_available_cities()
        
        for region in nearby_regions:
            cities = SOAXCitiesManager._get_cities_in_region(region)
            available = [c for c in cities if c in available_cities]
            
            if not available:
                continue
            
            city = available[0]
            session_id = secrets.token_urlsafe(16)
            
            result = await get_soax_username_with_dynamic_city(
                base_username=settings.SOAX_USERNAME,
                country="ec",
                preferred_city=city,
                session_id=session_id
            )
            
            test_proxy = Proxy(
                username=result["username"],
                password=settings.SOAX_PASSWORD,
                host=settings.SOAX_HOST,
                port=settings.SOAX_PORT
            )
            
            latency = await self._ping_proxy(test_proxy)
            
            if latency and latency < self.MAX_LATENCY_MS:
                logger.info(f"✅ Región cercana: {city}, {region} ({latency}ms)")
                return {
                    "username": result["username"],
                    "session_id": session_id,
                    "city": city,
                    "region": region,
                    "country": "ec",
                    "latency_ms": latency
                }
        
        return None
    
    async def _rotate_to_fallback(self) -> Optional[Dict]:
        """Fallback: Guayaquil"""
        session_id = secrets.token_urlsafe(16)
        
        result = await get_soax_username_with_dynamic_city(
            base_username=settings.SOAX_USERNAME,
            country="ec",
            preferred_city="guayaquil",
            session_id=session_id
        )
        
        return {
            "username": result["username"],
            "session_id": session_id,
            "city": "Guayaquil",
            "region": "Guayas",
            "country": "ec"
        }
    
    async def check_and_rotate_all_proxies(self) -> Dict:
        """Verifica y rota TODOS los proxies activos"""
        
        result = await self.db.execute(
            select(Proxy).where(Proxy.status == ProxyStatus.ACTIVE)
        )
        proxies = list(result.scalars().all())
        
        logger.info(f"🔄 Verificando {len(proxies)} proxies activos...")
        
        stats = {
            "total": len(proxies),
            "optimal": 0,
            "rotated": 0,
            "failed": 0
        }
        
        for proxy in proxies:
            result = await self.check_and_rotate_proxy(proxy.id)
            
            if result.get("rotated"):
                stats["rotated"] += 1
            elif result.get("error"):
                stats["failed"] += 1
            else:
                stats["optimal"] += 1
            
            await asyncio.sleep(2)
        
        logger.info(
            f"✅ Verificación completa: "
            f"{stats['optimal']} óptimos, "
            f"{stats['rotated']} rotados, "
            f"{stats['failed']} fallidos"
        )
        
        return stats