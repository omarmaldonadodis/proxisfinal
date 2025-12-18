# app/utils/geo_manager.py
"""
Sistema de Gestión Geográfica de Proxies SOAX
Maneja jerarquía: País → Región → Ciudad con fallbacks inteligentes
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class GeoLocation:
    """Ubicación geográfica con códigos SOAX"""
    country: str  # Código de 2 letras: "ec"
    country_name: str
    region: Optional[str] = None  # Nombre completo: "Azuay"
    region_code: Optional[str] = None  # Código SOAX: "azuay"
    city: Optional[str] = None  # Nombre: "Cuenca"
    city_code: Optional[str] = None  # Código SOAX: "cuenca"
    priority: int = 1  # 1=preferida, 2=secundaria, 3=última opción
    
    def to_soax_string(self) -> str:
        """
        Genera string para SOAX con jerarquía completa
        
        Returns:
            "country-ec-region-azuay-city-cuenca" (jerarquía completa)
            "country-ec-city-guayaquil" (sin región)
            "country-ec" (solo país)
        """
        parts = [f"country-{self.country.lower()}"]
        
        if self.region_code:
            parts.append(f"region-{self.region_code.lower()}")
        
        if self.city_code:
            parts.append(f"city-{self.city_code.lower()}")
        
        return "-".join(parts)


class GeoManager:
    """
    Gestor de ubicaciones geográficas con fallbacks inteligentes
    
    Características:
    - Jerarquía País → Región → Ciudad
    - Fallbacks automáticos por proximidad geográfica
    - Priorización de ubicaciones
    - Rotación inteligente
    """
    
    # 🗺️ BASE DE DATOS GEOGRÁFICA ECUADOR
    # Estructura: Región → Ciudades (ordenadas por tamaño/importancia)
    ECUADOR_GEO = {
        "pichincha": {
            "region_name": "Pichincha",
            "cities": [
                {"name": "Quito", "code": "quito", "priority": 1},
                {"name": "Sangolquí", "code": "sangolqui", "priority": 2},
                {"name": "Cayambe", "code": "cayambe", "priority": 3},
            ]
        },
        "guayas": {
            "region_name": "Guayas",
            "cities": [
                {"name": "Guayaquil", "code": "guayaquil", "priority": 1},
                {"name": "Durán", "code": "duran", "priority": 2},
                {"name": "Milagro", "code": "milagro", "priority": 3},
                {"name": "Daule", "code": "daule", "priority": 3},
            ]
        },
        "azuay": {
            "region_name": "Azuay",
            "cities": [
                {"name": "Cuenca", "code": "cuenca", "priority": 1},
                {"name": "Gualaceo", "code": "gualaceo", "priority": 2},
            ]
        },
        "manabi": {
            "region_name": "Manabí",
            "cities": [
                {"name": "Manta", "code": "manta", "priority": 1},
                {"name": "Portoviejo", "code": "portoviejo", "priority": 1},
                {"name": "Bahía de Caráquez", "code": "bahia", "priority": 2},
            ]
        },
        "el_oro": {
            "region_name": "El Oro",
            "cities": [
                {"name": "Machala", "code": "machala", "priority": 1},
                {"name": "Huaquillas", "code": "huaquillas", "priority": 2},
            ]
        },
        "los_rios": {
            "region_name": "Los Ríos",
            "cities": [
                {"name": "Babahoyo", "code": "babahoyo", "priority": 1},
                {"name": "Quevedo", "code": "quevedo", "priority": 1},
            ]
        },
        "imbabura": {
            "region_name": "Imbabura",
            "cities": [
                {"name": "Ibarra", "code": "ibarra", "priority": 1},
                {"name": "Otavalo", "code": "otavalo", "priority": 2},
            ]
        },
        "tungurahua": {
            "region_name": "Tungurahua",
            "cities": [
                {"name": "Ambato", "code": "ambato", "priority": 1},
            ]
        },
        "santo_domingo": {
            "region_name": "Santo Domingo de los Tsáchilas",
            "cities": [
                {"name": "Santo Domingo", "code": "santo_domingo", "priority": 1},
            ]
        },
        "esmeraldas": {
            "region_name": "Esmeraldas",
            "cities": [
                {"name": "Esmeraldas", "code": "esmeraldas", "priority": 1},
            ]
        },
    }
    
    # 🌎 Proximidad geográfica (regiones cercanas para fallback)
    PROXIMITY_MAP = {
        "pichincha": ["imbabura", "santo_domingo", "tungurahua"],
        "guayas": ["los_rios", "manabi", "el_oro"],
        "azuay": ["el_oro", "guayas"],
        "manabi": ["guayas", "los_rios", "esmeraldas"],
        "el_oro": ["guayas", "azuay"],
        "los_rios": ["guayas", "manabi"],
        "imbabura": ["pichincha", "esmeraldas"],
        "tungurahua": ["pichincha"],
        "santo_domingo": ["pichincha", "esmeraldas"],
        "esmeraldas": ["manabi", "imbabura"],
    }
    
    @classmethod
    def create_location(
        cls,
        country: str = "ec",
        region: Optional[str] = None,
        city: Optional[str] = None
    ) -> GeoLocation:
        """
        Crea ubicación geográfica válida
        
        Args:
            country: Código país (default: "ec")
            region: Región (ej: "Pichincha", "pichincha")
            city: Ciudad (ej: "Quito", "quito")
        
        Returns:
            GeoLocation con todos los códigos necesarios
        """
        
        # Normalizar país
        country = country.lower()
        country_name = "Ecuador" if country == "ec" else country.upper()
        
        # Si no hay región/ciudad, retornar solo país
        if not region and not city:
            return GeoLocation(
                country=country,
                country_name=country_name,
                priority=1
            )
        
        # Normalizar región
        if region:
            region = region.lower().replace(" ", "_")
            
            # Buscar en base de datos
            if region in cls.ECUADOR_GEO:
                region_data = cls.ECUADOR_GEO[region]
                
                # Si hay ciudad específica
                if city:
                    city_normalized = city.lower().replace(" ", "_")
                    
                    # Buscar ciudad en región
                    city_data = next(
                        (c for c in region_data["cities"] 
                         if c["code"] == city_normalized or c["name"].lower() == city_normalized),
                        None
                    )
                    
                    if city_data:
                        return GeoLocation(
                            country=country,
                            country_name=country_name,
                            region=region_data["region_name"],
                            region_code=region,
                            city=city_data["name"],
                            city_code=city_data["code"],
                            priority=city_data["priority"]
                        )
                    else:
                        # Ciudad no encontrada, usar primera ciudad de región
                        logger.warning(
                            f"City '{city}' not found in region '{region}', "
                            f"using default: {region_data['cities'][0]['name']}"
                        )
                        default_city = region_data["cities"][0]
                        return GeoLocation(
                            country=country,
                            country_name=country_name,
                            region=region_data["region_name"],
                            region_code=region,
                            city=default_city["name"],
                            city_code=default_city["code"],
                            priority=default_city["priority"]
                        )
                else:
                    # Solo región (sin ciudad)
                    return GeoLocation(
                        country=country,
                        country_name=country_name,
                        region=region_data["region_name"],
                        region_code=region,
                        priority=1
                    )
        
        # Si llegó aquí, ubicación no válida - retornar default (Quito)
        logger.warning(
            f"Invalid location: region={region}, city={city}. "
            f"Using default: Quito, Pichincha"
        )
        return GeoLocation(
            country="ec",
            country_name="Ecuador",
            region="Pichincha",
            region_code="pichincha",
            city="Quito",
            city_code="quito",
            priority=1
        )
    
    @classmethod
    def get_fallback_locations(
        cls,
        current_location: GeoLocation,
        exclude_cities: List[str] = None
    ) -> List[GeoLocation]:
        """
        Genera lista de ubicaciones alternativas (fallbacks)
        
        Estrategia:
        1. Otras ciudades en la misma región
        2. Ciudades en regiones cercanas (geográficamente)
        3. Ciudades principales de otras regiones
        
        Args:
            current_location: Ubicación actual
            exclude_cities: Ciudades a excluir (ya probadas)
        
        Returns:
            Lista de GeoLocation ordenada por prioridad
        """
        
        fallbacks = []
        exclude_cities = exclude_cities or []
        
        # 1. Otras ciudades en la misma región
        if current_location.region_code:
            region_data = cls.ECUADOR_GEO.get(current_location.region_code)
            
            if region_data:
                for city_data in region_data["cities"]:
                    if city_data["code"] not in exclude_cities:
                        fallbacks.append(GeoLocation(
                            country=current_location.country,
                            country_name=current_location.country_name,
                            region=region_data["region_name"],
                            region_code=current_location.region_code,
                            city=city_data["name"],
                            city_code=city_data["code"],
                            priority=city_data["priority"]
                        ))
        
        # 2. Ciudades en regiones cercanas
        if current_location.region_code:
            nearby_regions = cls.PROXIMITY_MAP.get(current_location.region_code, [])
            
            for region_code in nearby_regions:
                region_data = cls.ECUADOR_GEO.get(region_code)
                
                if region_data:
                    for city_data in region_data["cities"]:
                        if city_data["code"] not in exclude_cities:
                            fallbacks.append(GeoLocation(
                                country=current_location.country,
                                country_name=current_location.country_name,
                                region=region_data["region_name"],
                                region_code=region_code,
                                city=city_data["name"],
                                city_code=city_data["code"],
                                priority=city_data["priority"] + 1  # +1 por ser otra región
                            ))
        
        # 3. Ciudades principales de todas las regiones restantes
        for region_code, region_data in cls.ECUADOR_GEO.items():
            if region_code != current_location.region_code:
                # Solo ciudades prioritarias (priority=1)
                for city_data in region_data["cities"]:
                    if city_data["priority"] == 1 and city_data["code"] not in exclude_cities:
                        fallbacks.append(GeoLocation(
                            country=current_location.country,
                            country_name=current_location.country_name,
                            region=region_data["region_name"],
                            region_code=region_code,
                            city=city_data["name"],
                            city_code=city_data["code"],
                            priority=city_data["priority"] + 2  # +2 por ser región lejana
                        ))
        
        # Ordenar por prioridad (menor = mejor)
        fallbacks.sort(key=lambda loc: loc.priority)
        
        return fallbacks
    
    @classmethod
    def get_all_locations(cls, country: str = "ec") -> List[GeoLocation]:
        """
        Obtiene TODAS las ubicaciones disponibles del país
        
        Útil para:
        - Mostrar lista de ciudades disponibles
        - Testing de disponibilidad masiva
        
        Returns:
            Lista de todas las ubicaciones posibles
        """
        
        locations = []
        
        for region_code, region_data in cls.ECUADOR_GEO.items():
            for city_data in region_data["cities"]:
                locations.append(GeoLocation(
                    country=country,
                    country_name="Ecuador",
                    region=region_data["region_name"],
                    region_code=region_code,
                    city=city_data["name"],
                    city_code=city_data["code"],
                    priority=city_data["priority"]
                ))
        
        return locations
    
    @classmethod
    def parse_location_from_string(cls, location_str: str) -> Optional[GeoLocation]:
        """
        Parsea string de ubicación a GeoLocation
        
        Ejemplos:
            "Quito, Pichincha" → GeoLocation(city="Quito", region="Pichincha")
            "Guayaquil" → GeoLocation(city="Guayaquil")
            "ec" → GeoLocation(country="ec")
        
        Returns:
            GeoLocation o None si no se puede parsear
        """
        
        if not location_str:
            return None
        
        parts = [p.strip() for p in location_str.split(",")]
        
        if len(parts) == 2:
            # "Ciudad, Región"
            city, region = parts
            return cls.create_location(country="ec", region=region, city=city)
        
        elif len(parts) == 1:
            # Solo ciudad o región
            location = parts[0].lower().replace(" ", "_")
            
            # Buscar si es región
            if location in cls.ECUADOR_GEO:
                return cls.create_location(country="ec", region=location)
            
            # Buscar si es ciudad en alguna región
            for region_code, region_data in cls.ECUADOR_GEO.items():
                for city_data in region_data["cities"]:
                    if city_data["code"] == location or city_data["name"].lower() == location:
                        return cls.create_location(
                            country="ec",
                            region=region_code,
                            city=city_data["code"]
                        )
            
            # No encontrado
            logger.warning(f"Could not parse location: {location_str}")
            return None
        
        return None


# ========================================
# FUNCIONES DE UTILIDAD
# ========================================

def get_soax_username_with_geo(
    base_username: str,
    location: GeoLocation,
    session_id: str,
    session_lifetime: int = 3600
) -> str:
    """
    Construye username SOAX con jerarquía geográfica completa
    
    Args:
        base_username: "package-325401"
        location: GeoLocation con region y city
        session_id: ID de sesión
        session_lifetime: Duración sesión (segundos)
    
    Returns:
        "package-325401-country-ec-region-pichincha-city-quito-sessionid-...-sessionlength-3600-opt-lookalike"
    """
    
    parts = [base_username]
    
    # Agregar jerarquía geográfica
    parts.append(location.to_soax_string())
    
    # Sesión
    parts.append(f"sessionid-{session_id}")
    parts.append(f"sessionlength-{session_lifetime}")
    
    # Opciones
    parts.append("opt-lookalike")
    
    return "-".join(parts)


# ========================================
# EJEMPLO DE USO
# ========================================

if __name__ == "__main__":
    # Crear ubicación específica
    loc = GeoManager.create_location(
        country="ec",
        region="Pichincha",
        city="Quito"
    )
    
    print(f"Location: {loc.city}, {loc.region}")
    print(f"SOAX String: {loc.to_soax_string()}")
    
    # Username completo
    username = get_soax_username_with_geo(
        base_username="package-325401",
        location=loc,
        session_id="abc123",
        session_lifetime=3600
    )
    print(f"Username: {username}")
    
    # Fallbacks
    fallbacks = GeoManager.get_fallback_locations(loc)
    print(f"\nFallback locations:")
    for fb in fallbacks[:5]:
        print(f"  - {fb.city}, {fb.region} (priority: {fb.priority})")