# app/utils/soax_cities_manager.py
"""
Sistema dinámico para obtener ciudades disponibles en SOAX en tiempo real
Soluciona el problema de disponibilidad rotativa
"""
import httpx
from typing import List, Dict, Optional, Set
from loguru import logger
from datetime import datetime, timedelta
import asyncio
from app.config import settings


class SOAXCitiesManager:
    """
    Gestor dinámico de ciudades disponibles en SOAX
    """
    
    # Cache de ciudades disponibles
    _cache: Dict[str, List[str]] = {}
    _cache_timestamp: Dict[str, datetime] = {}
    _cache_ttl_minutes = 5
    
    # ✅ SOLUCIÓN: Inicializar directamente desde settings
    @classmethod
    def get_api_key(cls) -> Optional[str]:
        """Obtiene API key desde settings"""
        return getattr(settings, 'SOAX_API_KEY', None)
    
    @classmethod
    async def initialize(cls):
        """Inicializa el manager (opcional ahora)"""
        api_key = cls.get_api_key()
        
        if not api_key:
            logger.warning(
                "⚠️ SOAX_API_KEY no configurado. "
                "Sistema de rotación usará ciudades estáticas."
            )
        else:
            logger.info(f"✅ SOAX_API_KEY configurado: {api_key[:8]}...")
    
    @classmethod
    async def get_available_cities(
        cls,
        country: str = "ec",
        conn_type: str = "mobile",
        force_refresh: bool = False
    ) -> List[str]:
        """Obtiene ciudades disponibles desde API de SOAX"""
        
        cache_key = f"{country}_{conn_type}"
        
        # 1. VERIFICAR CACHE
        if not force_refresh and cache_key in cls._cache:
            cache_age = datetime.utcnow() - cls._cache_timestamp[cache_key]
            
            if cache_age < timedelta(minutes=cls._cache_ttl_minutes):
                logger.debug(
                    f"✓ Cache hit: {len(cls._cache[cache_key])} ciudades "
                    f"(age: {cache_age.seconds}s)"
                )
                return cls._cache[cache_key]
        
        # 2. OBTENER API KEY
        api_key = cls.get_api_key()  # ✅ Obtener dinámicamente
        
        if not api_key:
            logger.warning("SOAX_API_KEY no disponible, usando fallback")
            return cls._get_fallback_cities()
        
        try:
            url = "https://api.soax.com/api/get-country-cities"
            
            params = {
                "api_key": api_key,  # ✅ Usar el valor obtenido
                "package_key": settings.SOAX_PASSWORD,
                "country_iso": country.lower(),
                "conn_type": conn_type
            }
            
            logger.info(f"🌐 Consultando ciudades disponibles en SOAX...")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(
                        f"❌ SOAX API error: {response.status_code} - {response.text}"
                    )
                    return cls._get_fallback_cities()
                
                data = response.json()

                if isinstance(data, list):
                    cities = [c.lower().strip() for c in data if c]
                else:
                    logger.error(f"Formato inesperado de respuesta SOAX: {data}")
                    return cls._get_fallback_cities()
                
                if not cities:
                    logger.warning("⚠️ SOAX retornó 0 ciudades, usando fallback")
                    return cls._get_fallback_cities()
                
                # 3. GUARDAR EN CACHE
                cls._cache[cache_key] = cities
                cls._cache_timestamp[cache_key] = datetime.utcnow()
                
                logger.info(
                    f"✅ {len(cities)} ciudades disponibles en SOAX: "
                    f"{', '.join(cities[:5])}{'...' if len(cities) > 5 else ''}"
                )
                
                return cities
        
        except httpx.TimeoutException:
            logger.error("⏱️ Timeout consultando SOAX API")
            return cls._get_fallback_cities()
        
        except Exception as e:
            logger.error(f"❌ Error consultando SOAX: {e}")
            return cls._get_fallback_cities()
    
    @classmethod
    def _parse_soax_response(cls, data: Dict) -> List[str]:
        """
        Parsea respuesta de SOAX API
        
        Formato esperado:
        {
            "status": "success",
            "cities": ["Quito", "Guayaquil", "Santo Domingo de los Colorados", ...]
        }
        """
        if not isinstance(data, dict):
            return []
        
        if data.get("status") != "success":
            return []
        
        cities_raw = data.get("cities", [])
        
        if not isinstance(cities_raw, list):
            return []
        
        # Normalizar nombres: lowercase, espacios → guiones
        cities_normalized = []
        
        for city in cities_raw:
            if not isinstance(city, str):
                continue
            
            # "Santo Domingo de los Colorados" → "santo-domingo-de-los-colorados"
            normalized = city.lower().strip().replace(" ", "-")
            cities_normalized.append(normalized)
        
        return cities_normalized
    
    @classmethod
    def _get_fallback_cities(cls) -> List[str]:
        """
        Ciudades de fallback (las más grandes y estables)
        Se usan cuando la API falla
        """
        return [
            "quito",
            "guayaquil",
            "cuenca",
            "santo-domingo-de-los-colorados",
            "machala",
            "ambato",
            "manta",
            "portoviejo",
            "loja",
            "riobamba",
            "esmeraldas",
            "ibarra"
        ]
    
    @classmethod
    def normalize_city_for_soax(cls, city: str) -> str:
        """
        Normaliza ciudad para username de SOAX
        
        Args:
            city: "santo domingo de los colorados" o "santo-domingo-de-los-colorados"
        
        Returns:
            "santo+domingo+de+los+colorados" (formato SOAX)
        """
        # Eliminar guiones y convertir espacios a +
        normalized = city.lower().strip()
        normalized = normalized.replace("-", " ")  # Guiones → espacios
        normalized = normalized.replace(" ", "+")   # Espacios → +
        
        return normalized
    
    @classmethod
    async def get_optimal_city(
        cls,
        country: str = "ec",
        exclude_cities: List[str] = None,
        preferred_region: Optional[str] = None
    ) -> Optional[str]:
        """
        Obtiene ciudad óptima disponible
        
        Estrategia:
        1. Si hay preferred_region, buscar ciudades en esa región
        2. Si no, buscar ciudad más grande disponible
        3. Si todo falla, retornar None (usar solo región)
        
        Returns:
            Ciudad en formato normalizado: "guayaquil", "santo-domingo-..."
            None si ninguna ciudad disponible
        """
        exclude_cities = exclude_cities or []
        
        # Obtener ciudades disponibles
        available = await cls.get_available_cities(country=country)
        
        # Filtrar excluidas
        available = [
            city for city in available 
            if city not in exclude_cities
        ]
        
        if not available:
            logger.warning("❌ No hay ciudades disponibles en SOAX")
            return None
        
        # Si hay región preferida, buscar ciudad en esa región
        if preferred_region:
            region_cities = cls._get_cities_in_region(preferred_region)
            
            for city in region_cities:
                if city in available:
                    logger.info(f"✓ Ciudad encontrada en región {preferred_region}: {city}")
                    return city
        
        # Retornar la primera disponible (generalmente la más grande)
        optimal = available[0]
        logger.info(f"✓ Ciudad óptima seleccionada: {optimal}")
        
        return optimal
    
    @classmethod
    def _get_cities_in_region(cls, region: str) -> List[str]:
        """
        Mapeo básico de ciudades por región
        (Solo las más importantes)
        """
        region_map = {
            "pichincha": ["quito", "sangolqui"],
            "guayas": ["guayaquil", "duran", "samborondon", "milagro"],
            "azuay": ["cuenca"],
            "manabi": ["manta", "portoviejo", "bahia-de-caraquez"],
            "el-oro": ["machala", "huaquillas"],
            "los-rios": ["babahoyo", "quevedo"],
            "santo-domingo": ["santo-domingo-de-los-colorados"],
            "tungurahua": ["ambato"],
            "chimborazo": ["riobamba"],
            "imbabura": ["ibarra", "otavalo"],
            "esmeraldas": ["esmeraldas", "atacames"],
            "loja": ["loja"],
            "sucumbios": ["nueva-loja"],
        }
        
        return region_map.get(region.lower(), [])
    
    @classmethod
    async def test_city_availability(cls, city: str) -> bool:
        """
        Verifica si una ciudad específica está disponible
        """
        available = await cls.get_available_cities()
        return city.lower() in available
    
    @classmethod
    def clear_cache(cls):
        """Limpia cache (útil para testing)"""
        cls._cache.clear()
        cls._cache_timestamp.clear()
        logger.info("🧹 Cache de ciudades limpiado")


# ========================================
# FUNCIONES HELPER
# ========================================

async def get_soax_username_with_dynamic_city(
    base_username: str,
    country: str = "ec",
    region: Optional[str] = None,
    preferred_city: Optional[str] = None,
    exclude_cities: List[str] = None,
    session_id: str = None,
    session_lifetime: int = 3600
) -> Dict[str, str]:
    """
    Construye username SOAX con ciudad dinámica
    
    Returns:
        {
            "username": "user-country-ec-city-guayaquil-sessionid-...",
            "selected_city": "guayaquil",
            "fallback_used": False
        }
    """
    
    exclude_cities = exclude_cities or []
    
    if not session_id:
        import secrets
        session_id = secrets.token_urlsafe(16)
    
    # ========================================
    # 1. INTENTAR CIUDAD ESPECÍFICA
    # ========================================
    if preferred_city:
        available = await SOAXCitiesManager.test_city_availability(preferred_city)
        
        if available:
            city_normalized = SOAXCitiesManager.normalize_city_for_soax(preferred_city)
            
            username = (
                f"{base_username}-"
                f"country-{country.lower()}-"
                f"city-{city_normalized}-"
                f"sessionid-{session_id}-"
                f"sessionlength-{session_lifetime}"
            )
            
            return {
                "username": username,
                "selected_city": preferred_city,
                "fallback_used": False
            }
    
    # ========================================
    # 2. BUSCAR CIUDAD ÓPTIMA
    # ========================================
    optimal_city = await SOAXCitiesManager.get_optimal_city(
        country=country,
        exclude_cities=exclude_cities,
        preferred_region=region
    )
    
    if optimal_city:
        city_normalized = SOAXCitiesManager.normalize_city_for_soax(optimal_city)
        
        username = (
            f"{base_username}-"
            f"country-{country.lower()}-"
            f"city-{city_normalized}-"
            f"sessionid-{session_id}-"
            f"sessionlength-{session_lifetime}"
        )
        
        return {
            "username": username,
            "selected_city": optimal_city,
            "fallback_used": False
        }
    
    # ========================================
    # 3. FALLBACK: SOLO REGIÓN O SOLO PAÍS
    # ========================================
    logger.warning("⚠️ No hay ciudades disponibles, usando región o país")
    
    if region:
        username = (
            f"{base_username}-"
            f"country-{country.lower()}-"
            f"region-{region.lower()}-"
            f"sessionid-{session_id}-"
            f"sessionlength-{session_lifetime}"
        )
        
        return {
            "username": username,
            "selected_city": None,
            "selected_region": region,
            "fallback_used": True,
            "fallback_type": "region"
        }
    else:
        username = (
            f"{base_username}-"
            f"country-{country.lower()}-"
            f"sessionid-{session_id}-"
            f"sessionlength-{session_lifetime}"
        )
        
        return {
            "username": username,
            "selected_city": None,
            "fallback_used": True,
            "fallback_type": "country"
        }


# Test
if __name__ == "__main__":
    async def test():
        await SOAXCitiesManager.initialize()
        
        # Test 1: Obtener ciudades disponibles
        cities = await SOAXCitiesManager.get_available_cities()
        print(f"✅ {len(cities)} ciudades disponibles:")
        print(cities)
        
        # Test 2: Normalizar nombres
        print(f"\n🔄 Normalización:")
        print(f"  'Santo Domingo de los Colorados' → '{SOAXCitiesManager.normalize_city_for_soax('santo domingo de los colorados')}'")
        print(f"  'Nueva Loja' → '{SOAXCitiesManager.normalize_city_for_soax('nueva loja')}'")
        
        # Test 3: Obtener ciudad óptima
        optimal = await SOAXCitiesManager.get_optimal_city()
        print(f"\n🎯 Ciudad óptima: {optimal}")
        
        # Test 4: Generar username
        result = await get_soax_username_with_dynamic_city(
            base_username=settings.SOAX_USERNAME,
            country="ec",
            preferred_city="guayaquil"
        )
        
        print(f"\n📝 Username generado:")
        print(f"  {result['username']}")
        print(f"  Ciudad: {result['selected_city']}")
        print(f"  Fallback: {result['fallback_used']}")
    
    asyncio.run(test())