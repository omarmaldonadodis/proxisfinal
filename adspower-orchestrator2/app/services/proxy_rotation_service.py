# app/services/proxy_rotation_service.py - ✅ VERSIÓN CORREGIDA CON RECUPERACIÓN

"""
CORRECCIONES:
1. check_and_rotate_all_proxies() ahora incluye proxies FAILED
2. Nuevo método _attempt_recovery() para recuperar proxies FAILED
3. Nuevo método _apply_new_session() para aplicar y verificar nuevas sesiones
"""

from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from loguru import logger
import httpx
import time
import secrets
from datetime import datetime

from app.models.proxy import Proxy, ProxyStatus
from app.models.profile import Profile
from app.models.computer import Computer
from app.integrations.adspower_client import AdsPowerClient
from app.utils.soax_cities_manager import (
    SOAXCitiesManager,
    get_soax_username_with_dynamic_city
)
from app.config import settings
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
        """Verifica y rota proxy si es necesario"""
        
        result = await self.db.execute(
            select(Proxy).where(Proxy.id == proxy_id)
        )
        proxy = result.scalar_one_or_none()
        
        if not proxy:
            return {"error": "Proxy no encontrado"}
        
        logger.info(f"🔍 Verificando proxy {proxy_id}: {proxy.city}, {proxy.region}")
        
        old_latency = await self._ping_proxy(proxy)
        
        # ✅ SI ESTÁ OFFLINE → INTENTAR RECUPERAR
        if old_latency is None:
            logger.warning(f"⚠️ Proxy {proxy_id} está OFFLINE → Intentando recuperar...")
            
            await self._update_success_rate(proxy, success=False)
            
            # ✅ INTENTAR RECUPERACIÓN AUTOMÁTICA
            recovery_result = await self._attempt_recovery(proxy)
            
            if recovery_result["recovered"]:
                logger.info(
                    f"✅ Proxy {proxy_id} recuperado: "
                    f"{recovery_result['new_location']} ({recovery_result['new_latency_ms']}ms)"
                )
                return recovery_result
            else:
                # Si no se pudo recuperar, marcar como FAILED
                proxy.status = ProxyStatus.FAILED
                await self.db.commit()
                
                return {
                    "rotated": False,
                    "recovered": False,
                    "error": "Proxy offline y no se pudo recuperar",
                    "old_latency_ms": None
                }
        
        # ✅ Actualizar success rate dinámicamente
        await self._update_success_rate(proxy, success=True)
        
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
        
        # Intentar rotación
        return await self._rotate_proxy(proxy, old_latency)
    
    async def _attempt_recovery(self, proxy: Proxy) -> Dict:
        """
        ✅ NUEVO: Intenta recuperar un proxy FAILED
        
        Estrategia:
        1. Generar nueva sesión en misma ciudad
        2. Si falla, probar ciudad cercana
        3. Si falla, probar región cercana
        4. Si falla, usar Guayaquil (fallback)
        """
        logger.info(f"🔄 Intentando recuperar proxy {proxy.id}...")
        
        # Intentar nueva sesión en misma ciudad
        if proxy.city:
            new_session = await self._rotate_same_city(proxy)
            if new_session:
                return await self._apply_new_session(proxy, new_session, "recovery_same_city")
        
        # Intentar ciudad cercana en misma región
        if proxy.region:
            new_session = await self._rotate_nearby_city_in_region(proxy)
            if new_session:
                return await self._apply_new_session(proxy, new_session, "recovery_nearby_city")
        
        # Intentar región cercana
        new_session = await self._rotate_nearby_region(proxy)
        if new_session:
            return await self._apply_new_session(proxy, new_session, "recovery_nearby_region")
        
        # Fallback: Guayaquil
        new_session = await self._rotate_to_fallback()
        if new_session:
            return await self._apply_new_session(proxy, new_session, "recovery_fallback")
        
        return {"recovered": False, "error": "No se pudo encontrar sesión viable"}
    
    async def _apply_new_session(self, proxy: Proxy, new_session: Dict, recovery_type: str) -> Dict:
        """Aplica nueva sesión al proxy y verifica"""
        
        old_location = f"{proxy.city or proxy.region}, {proxy.country}"
        old_username = proxy.username
        old_session_id = proxy.session_id
        old_city = proxy.city
        old_region = proxy.region
        
        # Aplicar cambios
        proxy.username = new_session["username"]
        proxy.session_id = new_session["session_id"]
        proxy.city = new_session.get("city")
        proxy.region = new_session.get("region")
        proxy.country = new_session.get("country", "ec")
        
        # Verificar nueva sesión
        new_latency = await self._ping_proxy(proxy)
        
        if new_latency is None:
            logger.error(f"❌ Nueva sesión falló en {recovery_type}")
            # Rollback
            proxy.username = old_username
            proxy.session_id = old_session_id
            proxy.city = old_city
            proxy.region = old_region
            await self.db.rollback()
            return {"recovered": False, "error": f"Nueva sesión falló ({recovery_type})"}
        
        # Actualizar AdsPower
        success = await self._update_adspower_profiles_centralized(proxy)
        
        if not success:
            logger.error(f"❌ Error sincronizando con AdsPower en {recovery_type}")
            # Rollback
            proxy.username = old_username
            proxy.session_id = old_session_id
            proxy.city = old_city
            proxy.region = old_region
            await self.db.rollback()
            return {"recovered": False, "error": "Error sincronizando AdsPower"}
        
        # ✅ ÉXITO: Actualizar estado
        proxy.avg_response_time = new_latency
        proxy.last_check_at = datetime.utcnow()
        proxy.status = ProxyStatus.ACTIVE
        proxy.failed_checks = 0  # Reset contador de fallos
        await self.db.commit()
        
        new_location = f"{proxy.city or proxy.region}, {proxy.country}"
        
        logger.info(
            f"✅ Proxy {proxy.id} recuperado ({recovery_type}): "
            f"{old_location} → {new_location} ({new_latency}ms)"
        )
        
        return {
            "recovered": True,
            "rotated": True,
            "recovery_type": recovery_type,
            "old_location": old_location,
            "new_location": new_location,
            "new_latency_ms": new_latency,
            "message": f"Proxy recuperado ({recovery_type})"
        }
    
    async def _rotate_proxy(self, proxy: Proxy, old_latency: int) -> Dict:
        """Rota proxy lento"""
        
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
            logger.error(f"❌ No se pudo rotar proxy {proxy.id}")
            return {
                "rotated": False,
                "error": "No hay ubicaciones disponibles",
                "old_latency_ms": old_latency
            }
        
        return await self._apply_new_session(proxy, new_session, "rotation")
    
    async def check_and_rotate_all_proxies(self) -> Dict:
        from sqlalchemy import select

        # ✅ Cargar solo IDs — sin objetos ORM que puedan expirar
        result = await self.db.execute(
            select(Proxy.id).where(
                or_(
                    Proxy.status == ProxyStatus.ACTIVE,
                    Proxy.status == ProxyStatus.FAILED
                )
            )
        )
        proxy_ids = list(result.scalars().all())  # lista de ints puros

        logger.info(f"🔄 Verificando {len(proxy_ids)} proxies (ACTIVE + FAILED)...")

        stats = {
            "total":     len(proxy_ids),
            "optimal":   0,
            "rotated":   0,
            "recovered": 0,
            "failed":    0
        }

        for proxy_id in proxy_ids:
            try:
                result = await self.check_and_rotate_proxy(proxy_id)

                if result.get("recovered"):
                    stats["recovered"] += 1
                elif result.get("rotated"):
                    stats["rotated"] += 1
                elif result.get("error"):
                    stats["failed"] += 1
                else:
                    stats["optimal"] += 1

            except Exception as e:
                logger.error(f"Error procesando proxy {proxy_id}: {e}")
                stats["failed"] += 1

            await asyncio.sleep(2)

        logger.info(
            f"✅ Verificación completa: "
            f"{stats['optimal']} óptimos, {stats['rotated']} rotados, "
            f"{stats['recovered']} recuperados, {stats['failed']} fallidos"
        )

        return stats
    
    # ========================================
    # MÉTODOS HELPER (mantienen la misma lógica)
    # ========================================
    
    async def _update_adspower_profiles_centralized(self, proxy: Proxy) -> bool:
        result = await self.db.execute(
            select(Profile).where(Profile.proxy_id == proxy.id)
        )
        profiles = list(result.scalars().all())

        # ✅ Filtrar perfiles que aún no existen en AdsPower
        valid_profiles = [
            p for p in profiles
            if p.adspower_id and not p.adspower_id.startswith("pending-")
        ]

        skipped = len(profiles) - len(valid_profiles)
        if skipped:
            logger.warning(f"⚠️ {skipped} perfiles pendientes omitidos (aún no en AdsPower)")

        if not valid_profiles:
            logger.info(f"ℹ️ Proxy {proxy.id} sin perfiles válidos en AdsPower")
            return True

        logger.info(f"🔄 Actualizando {len(valid_profiles)} perfiles en AdsPower...")

        proxy_config = {
            "user_proxy_config": {
                "proxy_soft":     "other",
                "proxy_type":     "http",
                "proxy_host":     proxy.host,
                "proxy_port":     str(proxy.port),
                "proxy_user":     proxy.username or "",
                "proxy_password": proxy.password or ""
            }
        }

        is_reachable = await self._check_adspower_reachable_centralized(
            settings.ADSPOWER_DEFAULT_API_URL,
            settings.ADSPOWER_DEFAULT_API_KEY
        )
        if not is_reachable:
            logger.error("❌ AdsPower no disponible")
            return False

        success_count = 0
        failed_count  = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            for profile in valid_profiles:
                try:
                    response = await client.post(
                        f"{settings.ADSPOWER_DEFAULT_API_URL}/api/v1/user/update",
                        json={"user_id": profile.adspower_id, **proxy_config},
                        headers={
                            "Authorization": f"Bearer {settings.ADSPOWER_DEFAULT_API_KEY}",
                            "Content-Type":  "application/json"
                        }
                    )
                    data = response.json()

                    if data.get("code") == 0:
                        success_count += 1
                    else:
                        logger.error(f"❌ AdsPower error en {profile.adspower_id}: {data.get('msg')}")
                        failed_count += 1

                except Exception as e:
                    logger.error(f"❌ Error actualizando perfil {profile.id}: {e}")
                    failed_count += 1

                # ✅ Rate limiting — AdsPower acepta ~1 req/s
                await asyncio.sleep(1.1)

        if failed_count > 0:
            logger.error(f"⚠️ Parcial: {success_count} OK, {failed_count} fallidos")
            return failed_count == 0

        logger.info(f"✅ Todos actualizados: {success_count}/{len(valid_profiles)}")
        return True  

    async def _check_adspower_reachable_centralized(
        self, 
        adspower_url: str,
        adspower_key: str
    ) -> bool:
        """Verifica que AdsPower centralizado responda"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{adspower_url}/api/v1/user/list",
                    params={"page": 1, "page_size": 1},
                    headers={
                        "Authorization": f"Bearer {adspower_key}"
                    }
                )
                
                return response.status_code == 200
        
        except Exception:
            return False
    
    async def _update_success_rate(self, proxy: Proxy, success: bool):
        """Actualiza success rate dinámicamente"""
        proxy.total_checks = (proxy.total_checks or 0) + 1
        
        if not success:
            proxy.failed_checks = (proxy.failed_checks or 0) + 1
        
        if proxy.total_checks > 0:
            successful_checks = proxy.total_checks - (proxy.failed_checks or 0)
            proxy.success_rate = (successful_checks / proxy.total_checks) * 100
    
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
        
        except Exception:
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