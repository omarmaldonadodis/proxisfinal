# app/services/proxy_rotation_service.py - ✅ VERSIÓN CORREGIDA CON FORMATO CORRECTO

"""
CAMBIO CRÍTICO:
- Usar EXACTAMENTE el mismo formato que profile_service.py usa al crear perfiles
- El campo se llama "user_proxy_config", no "proxy_config"
- Debe incluir "proxy_soft": "other"
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
        max_retries: int = 2
    ) -> bool:
        """Actualiza profiles con retry automático"""
        
        for attempt in range(max_retries + 1):
            if attempt > 0:
                logger.info(f"🔄 Reintento {attempt}/{max_retries}...")
                await asyncio.sleep(2)
            
            success = await self._update_adspower_profiles_sync(proxy)
            
            if success:
                return True
            
            logger.warning(f"⚠️ Intento {attempt + 1} falló")
        
        return False
    
    async def _update_adspower_profiles_sync(self, proxy: Proxy) -> bool:
        """
        ✅ CORRECCIÓN CRÍTICA: Usar el MISMO formato que profile_service.py
        
        ANTES (incorrecto):
        proxy_config = {
            "user_proxy_config": {
                "proxy_soft": "other",
                "proxy_type": "http",
                "proxy_host": proxy.host,
                "proxy_port": str(proxy.port),
                "proxy_user": proxy.username,
                "proxy_password": proxy.password
            }
        }
        
        AHORA (correcto, igual que en creación):
        Copiar EXACTAMENTE el formato de profile_service.py líneas 100-108
        """
        
        result = await self.db.execute(
            select(Profile).where(Profile.proxy_id == proxy.id)
        )
        profiles = list(result.scalars().all())
        
        if not profiles:
            logger.info(f"ℹ️ Proxy {proxy.id} no tiene profiles asignados")
            return True
        
        logger.info(f"🔄 Actualizando {len(profiles)} profiles en AdsPower...")
        
        # ✅ MAPEO DE TIPOS DE PROXY (igual que en profile_service.py)
        proxy_type_map = {
            "http": "http",
            "https": "https",
            "socks5": "socks5",
            "mobile": "http",      # ✅ SOAX mobile usa http
            "residential": "http",  # ✅ SOAX residential usa http
            "datacenter": "http"
        }
        
        # ✅ FORMATO EXACTO usado en profile_service.py (línea 100-108)
        proxy_config = {
            "user_proxy_config": {
                "proxy_soft": "other",
                "proxy_type": proxy_type_map.get(proxy.proxy_type, "http"),
                "proxy_host": proxy.host,
                "proxy_port": proxy.port,  # ✅ INT, no string
                "proxy_user": proxy.username or "",
                "proxy_password": proxy.password or ""
            }
        }
        
        # ✅ DEBUG: Imprimir EXACTAMENTE lo que se envía
        logger.info(f"📤 Datos que se enviarán a AdsPower:")
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
                
                # ✅ CREAR CLIENT con los MISMOS parámetros que profile_service.py
                client = AdsPowerClient(
                    api_url=computer.adspower_api_url,
                    api_key=computer.adspower_api_key
                )
                
                # Actualizar profiles de este computer
                for profile in computer_profiles:
                    try:
                        # ✅ USAR EL MISMO MÉTODO que profile_service.py
                        logger.info(f"📤 Actualizando profile {profile.adspower_id} en AdsPower...")
                        logger.info(f"   URL: {computer.adspower_api_url}/api/v1/user/update")
                        logger.info(f"   Profile ID: {profile.adspower_id}")
                        
                        success = await client.update_profile(
                            profile_id=profile.adspower_id,
                            profile_data=proxy_config
                        )
                        
                        if success:
                            logger.info(f"✅ Profile {profile.id} actualizado")
                            success_count += 1
                        else:
                            logger.error(f"❌ Profile {profile.id} falló (returned False)")
                            failed_count += 1
                    
                    except Exception as e:
                        logger.error(f"❌ Exception actualizando profile {profile.id}: {e}")
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