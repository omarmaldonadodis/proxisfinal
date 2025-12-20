# app/services/proxy_rotation_service.py
"""
Sistema SIMPLIFICADO de rotación de proxies
- Ping en tiempo real
- Rotación automática si latencia > 2000ms
- Actualización en AdsPower + DB
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
    """Servicio TODO-EN-UNO para rotación de proxies"""
    
    # Umbrales
    MAX_LATENCY_MS = 2000
    OPTIMAL_LATENCY_MS = 1000
    
    # Regiones cercanas (Ecuador)
    NEARBY_REGIONS = {
        "pichincha": ["cotopaxi", "imbabura", "santo-domingo"],
        "guayas": ["los-rios", "santa-elena", "manabi"],
        "azuay": ["canar", "el-oro", "loja"],
        "manabi": ["santo-domingo", "guayas", "esmeraldas"],
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========================================
    # 1️⃣ MÉTODO PRINCIPAL (LO ÚNICO QUE NECESITAS)
    # ========================================
    
    async def check_and_rotate_proxy(self, proxy_id: int) -> Dict:
        """
        🎯 MÉTODO MAESTRO: Verifica y rota proxy si es necesario
        
        Flujo:
        1. Ping proxy actual
        2. Si >2000ms → Rotar a otra sesión misma ciudad
        3. Si ciudad no disponible → Buscar ciudad cercana
        4. Actualizar AdsPower
        5. Actualizar DB
        
        Returns:
            {
                "rotated": True/False,
                "old_latency_ms": 3500,
                "new_latency_ms": 800,
                "old_location": "Quito, Pichincha",
                "new_location": "Guayaquil, Guayas",
                "message": "✅ Rotación exitosa"
            }
        """
        
        # ========================================
        # PASO 1: Obtener proxy
        # ========================================
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        
        if not proxy:
            return {"error": "Proxy no encontrado"}
        
        logger.info(f"🔍 Verificando proxy {proxy_id}: {proxy.city}, {proxy.region}")
        
        # ========================================
        # PASO 2: Ping actual
        # ========================================
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
        
        # ========================================
        # PASO 3: Verificar si necesita rotación
        # ========================================
        if old_latency < self.MAX_LATENCY_MS:
            logger.info(f"✅ Proxy {proxy_id} está óptimo ({old_latency}ms)")
            
            # Actualizar métricas en DB
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
        
        # ========================================
        # PASO 4: ROTAR (Latencia > 2000ms)
        # ========================================
        logger.warning(f"⚠️ Proxy {proxy_id} LENTO ({old_latency}ms) → Rotando...")
        
        # Intentar rotar en orden de prioridad
        new_session = None
        
        # A) Misma ciudad, nueva sesión
        if proxy.city:
            new_session = await self._rotate_same_city(proxy)
        
        # B) Ciudad cercana (misma región)
        if not new_session and proxy.region:
            new_session = await self._rotate_nearby_city_in_region(proxy)
        
        # C) Cualquier ciudad disponible en regiones cercanas
        if not new_session:
            new_session = await self._rotate_nearby_region(proxy)
        
        # D) Fallback: Guayaquil (mejor latencia nacional)
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
        
        # ========================================
        # PASO 5: Aplicar nueva sesión
        # ========================================
        old_location = f"{proxy.city or proxy.region}, {proxy.country}"
        
        proxy.username = new_session["username"]
        proxy.session_id = new_session["session_id"]
        proxy.city = new_session.get("city")
        proxy.region = new_session.get("region")
        proxy.country = new_session.get("country", "ec")
        
        # ========================================
        # PASO 6: Verificar nueva sesión
        # ========================================
        new_latency = await self._ping_proxy(proxy)
        
        if new_latency is None:
            logger.error("❌ Nueva sesión falló, rollback")
            await self.db.rollback()
            return {
                "rotated": False,
                "error": "Nueva sesión falló",
                "old_latency_ms": old_latency
            }
        
        # ========================================
        # PASO 7: Actualizar AdsPower
        # ========================================
        await self._update_adspower_profiles(proxy)
        
        # ========================================
        # PASO 8: Guardar en DB
        # ========================================
        proxy.avg_response_time = new_latency
        proxy.last_check_at = datetime.utcnow()
        proxy.status = ProxyStatus.ACTIVE
        await self.db.commit()
        
        new_location = f"{proxy.city or proxy.region}, {proxy.country}"
        
        logger.info(
            f"✅ Proxy {proxy_id} rotado: "
            f"{old_location} ({old_latency}ms) → {new_location} ({new_latency}ms)"
        )
        
        return {
            "rotated": True,
            "old_location": old_location,
            "new_location": new_location,
            "old_latency_ms": old_latency,
            "new_latency_ms": new_latency,
            "improvement_ms": old_latency - new_latency,
            "message": f"✅ Mejorado de {old_latency}ms a {new_latency}ms"
        }
    
    # ========================================
    # 2️⃣ MÉTODOS HELPER (PRIVADOS)
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
        
        # Verificar si ciudad está disponible
        available_cities = await SOAXCitiesManager.get_available_cities(
            country=proxy.country or "ec"
        )
        
        city_normalized = proxy.city.lower().replace(" ", "-")
        
        if city_normalized not in available_cities:
            logger.warning(f"Ciudad {proxy.city} no disponible")
            return None
        
        # Generar nueva sesión
        session_id = secrets.token_urlsafe(16)
        
        result = await get_soax_username_with_dynamic_city(
            base_username=settings.SOAX_USERNAME,
            country=proxy.country or "ec",
            preferred_city=city_normalized,
            session_id=session_id,
            session_lifetime=proxy.session_lifetime or 3600
        )
        
        # Ping nueva sesión
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
        
        # Obtener ciudades disponibles
        available_cities = await SOAXCitiesManager.get_available_cities(
            country=proxy.country or "ec"
        )
        
        # Ciudades de la región (excluyendo actual)
        region_cities = SOAXCitiesManager._get_cities_in_region(proxy.region)
        nearby = [c for c in region_cities if c in available_cities and c != proxy.city]
        
        if not nearby:
            return None
        
        # Probar cada ciudad
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
            
            # Probar primera ciudad disponible
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
        """Fallback: Guayaquil (mejor latencia)"""
        
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
    
    async def _update_adspower_profiles(self, proxy: Proxy):
        """Actualiza profiles en AdsPower"""
        
        result = await self.db.execute(
            select(Profile).where(Profile.proxy_id == proxy.id)
        )
        profiles = list(result.scalars().all())
        
        if not profiles:
            return
        
        logger.info(f"Actualizando {len(profiles)} profiles en AdsPower")
        
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
        
        for profile in profiles:
            try:
                result = await self.db.execute(
                    select(Computer).where(Computer.id == profile.computer_id)
                )
                computer = result.scalar_one_or_none()
                
                if not computer:
                    continue
                
                client = AdsPowerClient(
                    api_url=computer.adspower_api_url,
                    api_key=computer.adspower_api_key
                )
                
                await client.update_profile(
                    profile_id=profile.adspower_id,
                    profile_data=proxy_config
                )
                
                logger.info(f"✓ Profile {profile.id} actualizado")
            
            except Exception as e:
                logger.error(f"Error actualizando profile {profile.id}: {e}")
    
    # ========================================
    # 3️⃣ MÉTODO BATCH (PARA TODOS LOS PROXIES)
    # ========================================
    
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
            
            # Rate limiting
            await asyncio.sleep(2)
        
        logger.info(
            f"✅ Verificación completa: "
            f"{stats['optimal']} óptimos, "
            f"{stats['rotated']} rotados, "
            f"{stats['failed']} fallidos"
        )
        
        return stats


