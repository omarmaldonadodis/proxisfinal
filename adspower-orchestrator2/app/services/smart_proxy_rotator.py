# app/services/smart_proxy_rotator_v2.py
"""
Smart Proxy Rotator V2 - Con ciudades dinámicas de SOAX
✅ Consulta ciudades disponibles en tiempo real
✅ Fallback inteligente: Ciudad → Región → País
✅ Maneja nombres con espacios correctamente
"""
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from loguru import logger
import time
import httpx

from app.models.proxy import Proxy, ProxyStatus
from app.models.profile import Profile
from app.models.computer import Computer
from app.integrations.adspower_client import AdsPowerClient
from app.utils.soax_cities_manager import (
    SOAXCitiesManager,
    get_soax_username_with_dynamic_city
)
from app.config import settings


class ProxyRotationError(Exception):
    """Error específico de rotación"""
    pass


class SmartProxyRotator:
    """Rotador Inteligente con Ciudades Dinámicas"""
    
    # Thresholds
    MAX_LATENCY_MS = 3000
    OPTIMAL_LATENCY_MS = 1000
    
    # Regiones por proximidad (para fallback)
    REGION_PROXIMITY = {
        "pichincha": ["cotopaxi", "imbabura", "santo-domingo"],
        "guayas": ["los-rios", "santa-elena", "manabi"],
        "azuay": ["canar", "el-oro", "loja"],
        "manabi": ["santo-domingo", "guayas", "los-rios"],
        "el-oro": ["azuay", "loja", "guayas"],
        "loja": ["zamora-chinchipe", "el-oro", "azuay"],
        "imbabura": ["pichincha", "carchi", "sucumbios"],
        "carchi": ["imbabura", "sucumbios", "pichincha"],
        "sucumbios": ["orellana", "napo", "imbabura"],
        "napo": ["pichincha", "pastaza", "orellana"],
        "orellana": ["napo", "sucumbios", "pastaza"],
        "pastaza": ["orellana", "morona-santiago", "napo"],
        "morona-santiago": ["pastaza", "loja", "zamora-chinchipe"],
        "zamora-chinchipe": ["loja", "morona-santiago", "el-oro"],
        "cotopaxi": ["pichincha", "tungurahua", "bolivar"],
        "tungurahua": ["cotopaxi", "chimborazo", "bolivar"],
        "bolivar": ["tungurahua", "chimborazo", "cotopaxi"],
        "chimborazo": ["bolivar", "tungurahua", "canar"],
        "canar": ["azuay", "chimborazo", "guayas"],
        "los-rios": ["guayas", "manabi", "cotopaxi"],
        "esmeraldas": ["manabi", "imbabura", "santo-domingo"],
        "santo-domingo": ["pichincha", "manabi", "los-rios"],
        "santa-elena": ["guayas", "manabi", "los-rios"],
        "galapagos": ["manabi", "guayas", "santa-elena"]  # por aproximación logística
    }

    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def detect_and_rotate_if_needed(
        self,
        proxy_id: int,
        test_urls: List[str] = None
    ) -> Dict:
        """
        🎯 Detecta problemas y rota INTELIGENTEMENTE con ciudades dinámicas
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
                f"{current_proxy.city or current_proxy.region or current_proxy.country}"
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
            # 3. NECESITA ROTACIÓN
            # ========================================
            issues = []
            
            if not ping_result["success"]:
                issues.append("unavailable")
            elif ping_result["latency_ms"] > self.MAX_LATENCY_MS:
                issues.append("slow")
            
            logger.warning(
                f"⚠️ Proxy {proxy_id} has issues: {', '.join(issues)}"
            )
            
            # ========================================
            # 4. OBTENER CIUDADES DISPONIBLES
            # ========================================
            available_cities = await SOAXCitiesManager.get_available_cities(
                country=current_proxy.country or "ec",
                conn_type=current_proxy.proxy_type or "mobile"
            )
            
            logger.info(
                f"🌐 {len(available_cities)} ciudades disponibles en SOAX: "
                f"{', '.join(available_cities[:5])}..."
            )
            
            # ========================================
            # 5. BUSCAR MEJOR UBICACIÓN
            # ========================================
            best_location = await self._find_best_available_location(
                current_proxy=current_proxy,
                available_cities=available_cities,
                exclude_cities=[current_proxy.city] if current_proxy.city else []
            )
            
            if not best_location:
                raise ProxyRotationError("No optimal locations available")
            
            logger.info(
                f"🎯 Best location: {best_location['display_name']} "
                f"(estimated {best_location['estimated_latency_ms']}ms)"
            )
            
            # ========================================
            # 6. ACTUALIZAR SESIÓN DEL PROXY
            # ========================================
            await self._update_proxy_session(
                proxy=current_proxy,
                new_location=best_location
            )
            
            # ========================================
            # 7. VERIFICAR NUEVA SESIÓN
            # ========================================
            verify_result = await self._ping_proxy(current_proxy)
            
            if not verify_result["success"]:
                await self.db.rollback()
                raise ProxyRotationError(
                    f"New session failed: {verify_result.get('error')}"
                )
            
            logger.info(
                f"✅ New session verified: {verify_result['latency_ms']}ms"
            )
            
            # ========================================
            # 8. ACTUALIZAR ADSPOWER
            # ========================================
            await self._update_adspower_profiles(current_proxy)
            
            # ========================================
            # 9. COMMIT
            # ========================================
            await self.db.commit()
            
            logger.info(
                f"✅ Rotation complete: "
                f"{current_proxy.city or current_proxy.region or 'country'} "
                f"→ {best_location['display_name']} ({verify_result['latency_ms']}ms)"
            )
            
            return {
                "rotated": True,
                "issues_detected": issues,
                "old_location": self._get_display_name(current_proxy),
                "new_location": best_location["display_name"],
                "old_latency_ms": ping_result.get("latency_ms"),
                "new_latency_ms": verify_result["latency_ms"],
                "message": f"Rotated to: {best_location['display_name']}"
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
    
    async def _find_best_available_location(
        self,
        current_proxy: Proxy,
        available_cities: List[str],
        exclude_cities: List[str]
    ) -> Optional[Dict]:
        """
        Encuentra mejor ubicación entre las disponibles
        
        Estrategia:
        1. Ciudades en misma región (disponibles)
        2. Ciudades en regiones cercanas (disponibles)
        3. Cualquier ciudad disponible con menor latencia estimada
        4. Solo región (si ninguna ciudad funciona)
        5. Solo país (último recurso)
        """
        
        candidates = []
        
        # ========================================
        # 1. CIUDADES EN MISMA REGIÓN
        # ========================================
        if current_proxy.region:
            region_normalized = current_proxy.region.lower().replace(" ", "-")
            region_cities = SOAXCitiesManager._get_cities_in_region(region_normalized)
            
            for city in region_cities:
                if city in available_cities and city not in exclude_cities:
                    # Ping real
                    latency = await self._ping_city(
                        country=current_proxy.country or "ec",
                        city=city
                    )
                    
                    if latency:
                        candidates.append({
                            "type": "city",
                            "city": city,
                            "region": current_proxy.region,
                            "display_name": f"{city}, {current_proxy.region}",
                            "estimated_latency_ms": latency,
                            "priority": 1  # Mismo región = prioridad 1
                        })
        
        # ========================================
        # 2. CIUDADES EN REGIONES CERCANAS
        # ========================================
        if current_proxy.region:
            region_normalized = current_proxy.region.lower().replace(" ", "-")
            nearby_regions = self.REGION_PROXIMITY.get(region_normalized, [])
            
            for nearby_region in nearby_regions:
                region_cities = SOAXCitiesManager._get_cities_in_region(nearby_region)
                
                for city in region_cities:
                    if city in available_cities and city not in exclude_cities:
                        latency = await self._ping_city(
                            country=current_proxy.country or "ec",
                            city=city
                        )
                        
                        if latency:
                            candidates.append({
                                "type": "city",
                                "city": city,
                                "region": nearby_region,
                                "display_name": f"{city}, {nearby_region}",
                                "estimated_latency_ms": latency,
                                "priority": 2  # Región cercana = prioridad 2
                            })
        
        # ========================================
        # 3. CUALQUIER CIUDAD DISPONIBLE
        # ========================================
        for city in available_cities:
            if city not in exclude_cities:
                # Skip si ya está en candidates
                if any(c["city"] == city for c in candidates):
                    continue
                
                latency = await self._ping_city(
                    country=current_proxy.country or "ec",
                    city=city
                )
                
                if latency:
                    candidates.append({
                        "type": "city",
                        "city": city,
                        "region": None,
                        "display_name": city,
                        "estimated_latency_ms": latency,
                        "priority": 3  # Cualquier ciudad = prioridad 3
                    })
        
        # ========================================
        # 4. ORDENAR Y SELECCIONAR MEJOR
        # ========================================
        if candidates:
            # Ordenar por: prioridad (asc), luego latencia (asc)
            candidates.sort(
                key=lambda c: (c["priority"], c["estimated_latency_ms"])
            )
            
            best = candidates[0]
            
            logger.info(
                f"🏆 Best among {len(candidates)} candidates: "
                f"{best['display_name']} ({best['estimated_latency_ms']}ms)"
            )
            
            return best
        
        # ========================================
        # 5. FALLBACK: SOLO REGIÓN
        # ========================================
        if current_proxy.region:
            logger.warning("⚠️ No cities available, using region-only")
            
            return {
                "type": "region",
                "city": None,
                "region": current_proxy.region,
                "display_name": current_proxy.region,
                "estimated_latency_ms": 150,
                "fallback": True
            }
        
        # ========================================
        # 6. FALLBACK: SOLO PAÍS
        # ========================================
        logger.warning("⚠️ No cities/regions available, using country-only")
        
        return {
            "type": "country",
            "city": None,
            "region": None,
            "display_name": current_proxy.country or "ec",
            "estimated_latency_ms": 200,
            "fallback": True
        }
    
    async def _ping_city(
        self,
        country: str,
        city: str
    ) -> Optional[int]:
        """
        Ping una ciudad específica en SOAX
        
        Returns:
            Latencia en ms, o None si falla
        """
        
        try:
            # Generar username temporal
            result = await get_soax_username_with_dynamic_city(
                base_username=settings.SOAX_USERNAME,
                country=country,
                preferred_city=city,
                session_lifetime=300  # 5 min
            )
            
            if not result["selected_city"]:
                return None
            
            # Construir URL del proxy
            proxy_url = (
                f"http://{result['username']}:{settings.SOAX_PASSWORD}"
                f"@{settings.SOAX_HOST}:{settings.SOAX_PORT}"
            )
            
            # Ping
            start = time.time()
            
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=10.0
            ) as client:
                response = await client.get("https://api.ipify.org?format=json")
                
                if response.status_code == 200:
                    latency = (time.time() - start) * 1000
                    logger.debug(f"✓ {city}: {latency:.0f}ms")
                    return int(latency)
            
            return None
        
        except Exception as e:
            logger.debug(f"✗ {city}: {e}")
            return None
    
    async def _update_proxy_session(
        self,
        proxy: Proxy,
        new_location: Dict
    ):
        """Actualiza sesión del proxy con nueva ubicación"""
        
        # Generar username con ciudad dinámica
        result = await get_soax_username_with_dynamic_city(
            base_username=settings.SOAX_USERNAME,
            country=proxy.country or "ec",
            region=new_location.get("region"),
            preferred_city=new_location.get("city"),
            session_lifetime=proxy.session_lifetime or 3600
        )
        
        # Actualizar proxy
        proxy.country = proxy.country or "ec"
        proxy.region = new_location.get("region")
        proxy.city = new_location.get("city")
        proxy.session_id = result["username"].split("sessionid-")[1].split("-")[0]
        proxy.username = result["username"]
        proxy.password = settings.SOAX_PASSWORD
        proxy.status = ProxyStatus.ACTIVE
        proxy.is_available = True
        proxy.updated_at = datetime.utcnow()
        
        logger.info(
            f"✓ Proxy {proxy.id} session updated: {new_location['display_name']}"
        )
    
    async def _ping_proxy(self, proxy: Proxy) -> Dict:
        """Ping proxy para verificar latencia"""
        
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
            return {"success": False, "error": "timeout"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_adspower_profiles(self, proxy: Proxy):
        """Actualiza profiles en AdsPower"""
        
        result = await self.db.execute(
            select(Profile).where(Profile.proxy_id == proxy.id)
        )
        profiles = list(result.scalars().all())
        
        if not profiles:
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
        
        for profile in profiles:
            try:
                result = await self.db.execute(
                    select(Computer).where(Computer.id == profile.computer_id)
                )
                computer = result.scalar_one_or_none()
                
                if not computer:
                    continue
                
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
                
                await adspower_client.update_profile(
                    profile_id=profile.adspower_id,
                    profile_data=proxy_config
                )
                
                logger.info(f"✓ Profile {profile.id} updated in AdsPower")
            
            except Exception as e:
                logger.error(f"Error updating profile {profile.id}: {e}")
    
    def _get_display_name(self, proxy: Proxy) -> str:
        """Genera nombre display del proxy"""
        if proxy.city:
            return f"{proxy.city}, {proxy.region or proxy.country}"
        elif proxy.region:
            return f"{proxy.region}, {proxy.country}"
        else:
            return proxy.country or "ec"