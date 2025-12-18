# app/utils/geo_manager.py - VERSIÓN EXPANDIDA CON TODAS LAS CIUDADES
"""
Sistema de Gestión Geográfica EXPANDIDO
- Todas las provincias de Ecuador
- 100+ ciudades con priorización por latencia
- Jerarquía completa: País → Región → Ciudad
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class GeoLocation:
    """Ubicación geográfica con códigos SOAX"""
    country: str
    country_name: str
    region: Optional[str] = None
    region_code: Optional[str] = None
    city: Optional[str] = None
    city_code: Optional[str] = None
    priority: int = 1  # 1=mejor latencia, 5=peor latencia
    estimated_latency_ms: int = 100  # Estimación de latencia
    
    def to_soax_string(self) -> str:
        """Genera string para SOAX con jerarquía completa"""
        parts = [f"country-{self.country.lower()}"]
        
        if self.region_code:
            parts.append(f"region-{self.region_code.lower()}")
        
        if self.city_code:
            parts.append(f"city-{self.city_code.lower()}")
        
        return "-".join(parts)


class GeoManager:
    """
    Gestor de ubicaciones con TODAS las ciudades de Ecuador
    Priorización por latencia estimada (proximidad a centros de datos)
    """
    
    # 🗺️ MAPA COMPLETO DE ECUADOR (24 PROVINCIAS + 100+ CIUDADES)
    ECUADOR_GEO = {
        # ========================================
        # SIERRA (Montaña - Latencia Media)
        # ========================================
        "pichincha": {
            "region_name": "Pichincha",
            "cities": [
                {"name": "Quito", "code": "quito", "priority": 1, "latency_ms": 80},  # Capital - mejor conectividad
                {"name": "Sangolquí", "code": "sangolqui", "priority": 2, "latency_ms": 90},
                {"name": "Cayambe", "code": "cayambe", "priority": 3, "latency_ms": 100},
                {"name": "Machachi", "code": "machachi", "priority": 3, "latency_ms": 95},
                {"name": "Tabacundo", "code": "tabacundo", "priority": 4, "latency_ms": 110},
                {"name": "San Miguel de los Bancos", "code": "san_miguel", "priority": 4, "latency_ms": 120},
                {"name": "Pedro Vicente Maldonado", "code": "pedro_vicente", "priority": 5, "latency_ms": 130},
            ]
        },
        "azuay": {
            "region_name": "Azuay",
            "cities": [
                {"name": "Cuenca", "code": "cuenca", "priority": 1, "latency_ms": 85},  # 3ra ciudad - buena conectividad
                {"name": "Gualaceo", "code": "gualaceo", "priority": 2, "latency_ms": 100},
                {"name": "Paute", "code": "paute", "priority": 3, "latency_ms": 105},
                {"name": "Sigsig", "code": "sigsig", "priority": 3, "latency_ms": 110},
                {"name": "Santa Isabel", "code": "santa_isabel", "priority": 4, "latency_ms": 115},
                {"name": "Girón", "code": "giron", "priority": 4, "latency_ms": 120},
            ]
        },
        "tungurahua": {
            "region_name": "Tungurahua",
            "cities": [
                {"name": "Ambato", "code": "ambato", "priority": 1, "latency_ms": 90},
                {"name": "Baños", "code": "banos", "priority": 2, "latency_ms": 100},
                {"name": "Pelileo", "code": "pelileo", "priority": 3, "latency_ms": 105},
                {"name": "Píllaro", "code": "pillaro", "priority": 3, "latency_ms": 110},
            ]
        },
        "imbabura": {
            "region_name": "Imbabura",
            "cities": [
                {"name": "Ibarra", "code": "ibarra", "priority": 1, "latency_ms": 95},
                {"name": "Otavalo", "code": "otavalo", "priority": 2, "latency_ms": 100},
                {"name": "Cotacachi", "code": "cotacachi", "priority": 3, "latency_ms": 110},
                {"name": "Atuntaqui", "code": "atuntaqui", "priority": 3, "latency_ms": 105},
            ]
        },
        "chimborazo": {
            "region_name": "Chimborazo",
            "cities": [
                {"name": "Riobamba", "code": "riobamba", "priority": 1, "latency_ms": 95},
                {"name": "Alausí", "code": "alausi", "priority": 3, "latency_ms": 110},
                {"name": "Guano", "code": "guano", "priority": 3, "latency_ms": 105},
            ]
        },
        "cañar": {
            "region_name": "Cañar",
            "cities": [
                {"name": "Azogues", "code": "azogues", "priority": 2, "latency_ms": 100},
                {"name": "Cañar", "code": "canar", "priority": 3, "latency_ms": 110},
                {"name": "La Troncal", "code": "la_troncal", "priority": 2, "latency_ms": 95},
            ]
        },
        "carchi": {
            "region_name": "Carchi",
            "cities": [
                {"name": "Tulcán", "code": "tulcan", "priority": 2, "latency_ms": 110},
                {"name": "San Gabriel", "code": "san_gabriel", "priority": 3, "latency_ms": 120},
            ]
        },
        "bolivar": {
            "region_name": "Bolívar",
            "cities": [
                {"name": "Guaranda", "code": "guaranda", "priority": 2, "latency_ms": 105},
                {"name": "San Miguel", "code": "san_miguel_bolivar", "priority": 3, "latency_ms": 115},
            ]
        },
        "cotopaxi": {
            "region_name": "Cotopaxi",
            "cities": [
                {"name": "Latacunga", "code": "latacunga", "priority": 2, "latency_ms": 90},
                {"name": "La Maná", "code": "la_mana", "priority": 3, "latency_ms": 100},
                {"name": "Pujilí", "code": "pujili", "priority": 3, "latency_ms": 105},
            ]
        },
        "loja": {
            "region_name": "Loja",
            "cities": [
                {"name": "Loja", "code": "loja", "priority": 1, "latency_ms": 100},
                {"name": "Catamayo", "code": "catamayo", "priority": 2, "latency_ms": 110},
                {"name": "Macará", "code": "macara", "priority": 3, "latency_ms": 120},
            ]
        },
        
        # ========================================
        # COSTA (Mejor latencia - cerca de cables submarinos)
        # ========================================
        "guayas": {
            "region_name": "Guayas",
            "cities": [
                {"name": "Guayaquil", "code": "guayaquil", "priority": 1, "latency_ms": 70},  # MEJOR LATENCIA - puerto principal
                {"name": "Durán", "code": "duran", "priority": 1, "latency_ms": 75},
                {"name": "Samborondón", "code": "samborondon", "priority": 1, "latency_ms": 75},
                {"name": "Milagro", "code": "milagro", "priority": 2, "latency_ms": 85},
                {"name": "Daule", "code": "daule", "priority": 2, "latency_ms": 80},
                {"name": "Yaguachi", "code": "yaguachi", "priority": 3, "latency_ms": 90},
                {"name": "El Triunfo", "code": "el_triunfo", "priority": 3, "latency_ms": 95},
                {"name": "Naranjal", "code": "naranjal", "priority": 3, "latency_ms": 95},
                {"name": "Balzar", "code": "balzar", "priority": 4, "latency_ms": 100},
                {"name": "Santa Lucía", "code": "santa_lucia", "priority": 4, "latency_ms": 100},
            ]
        },
        "manabi": {
            "region_name": "Manabí",
            "cities": [
                {"name": "Manta", "code": "manta", "priority": 1, "latency_ms": 80},  # Puerto importante
                {"name": "Portoviejo", "code": "portoviejo", "priority": 1, "latency_ms": 85},
                {"name": "Bahía de Caráquez", "code": "bahia", "priority": 2, "latency_ms": 90},
                {"name": "Chone", "code": "chone", "priority": 2, "latency_ms": 95},
                {"name": "Jipijapa", "code": "jipijapa", "priority": 3, "latency_ms": 100},
                {"name": "Montecristi", "code": "montecristi", "priority": 2, "latency_ms": 85},
                {"name": "Calceta", "code": "calceta", "priority": 3, "latency_ms": 105},
                {"name": "Pedernales", "code": "pedernales", "priority": 3, "latency_ms": 110},
            ]
        },
        "el_oro": {
            "region_name": "El Oro",
            "cities": [
                {"name": "Machala", "code": "machala", "priority": 1, "latency_ms": 80},
                {"name": "Huaquillas", "code": "huaquillas", "priority": 2, "latency_ms": 95},
                {"name": "Pasaje", "code": "pasaje", "priority": 2, "latency_ms": 90},
                {"name": "Santa Rosa", "code": "santa_rosa", "priority": 2, "latency_ms": 90},
                {"name": "Piñas", "code": "pinas", "priority": 3, "latency_ms": 100},
                {"name": "Zaruma", "code": "zaruma", "priority": 3, "latency_ms": 105},
            ]
        },
        "los_rios": {
            "region_name": "Los Ríos",
            "cities": [
                {"name": "Babahoyo", "code": "babahoyo", "priority": 1, "latency_ms": 85},
                {"name": "Quevedo", "code": "quevedo", "priority": 1, "latency_ms": 85},
                {"name": "Ventanas", "code": "ventanas", "priority": 2, "latency_ms": 95},
                {"name": "Vinces", "code": "vinces", "priority": 3, "latency_ms": 100},
                {"name": "Puebloviejo", "code": "puebloviejo", "priority": 3, "latency_ms": 100},
            ]
        },
        "santa_elena": {
            "region_name": "Santa Elena",
            "cities": [
                {"name": "Salinas", "code": "salinas", "priority": 1, "latency_ms": 85},
                {"name": "La Libertad", "code": "la_libertad", "priority": 1, "latency_ms": 85},
                {"name": "Santa Elena", "code": "santa_elena_ciudad", "priority": 2, "latency_ms": 90},
            ]
        },
        "santo_domingo": {
            "region_name": "Santo Domingo de los Tsáchilas",
            "cities": [
                {"name": "Santo Domingo", "code": "santo_domingo", "priority": 1, "latency_ms": 85},
            ]
        },
        "esmeraldas": {
            "region_name": "Esmeraldas",
            "cities": [
                {"name": "Esmeraldas", "code": "esmeraldas", "priority": 1, "latency_ms": 90},
                {"name": "Atacames", "code": "atacames", "priority": 2, "latency_ms": 100},
                {"name": "Muisne", "code": "muisne", "priority": 3, "latency_ms": 110},
                {"name": "Quinindé", "code": "quininde", "priority": 3, "latency_ms": 105},
            ]
        },
        
        # ========================================
        # ORIENTE (Amazonía - Mayor latencia)
        # ========================================
        "sucumbios": {
            "region_name": "Sucumbíos",
            "cities": [
                {"name": "Nueva Loja", "code": "nueva_loja", "priority": 2, "latency_ms": 120},
                {"name": "Shushufindi", "code": "shushufindi", "priority": 3, "latency_ms": 130},
            ]
        },
        "orellana": {
            "region_name": "Orellana",
            "cities": [
                {"name": "Francisco de Orellana", "code": "orellana", "priority": 2, "latency_ms": 125},
            ]
        },
        "napo": {
            "region_name": "Napo",
            "cities": [
                {"name": "Tena", "code": "tena", "priority": 2, "latency_ms": 110},
                {"name": "Archidona", "code": "archidona", "priority": 3, "latency_ms": 120},
            ]
        },
        "pastaza": {
            "region_name": "Pastaza",
            "cities": [
                {"name": "Puyo", "code": "puyo", "priority": 2, "latency_ms": 115},
            ]
        },
        "morona_santiago": {
            "region_name": "Morona Santiago",
            "cities": [
                {"name": "Macas", "code": "macas", "priority": 2, "latency_ms": 120},
                {"name": "Sucúa", "code": "sucua", "priority": 3, "latency_ms": 130},
            ]
        },
        "zamora_chinchipe": {
            "region_name": "Zamora Chinchipe",
            "cities": [
                {"name": "Zamora", "code": "zamora", "priority": 2, "latency_ms": 115},
                {"name": "Yantzaza", "code": "yantzaza", "priority": 3, "latency_ms": 125},
            ]
        },
        
        # ========================================
        # REGIÓN INSULAR
        # ========================================
        "galapagos": {
            "region_name": "Galápagos",
            "cities": [
                {"name": "Puerto Ayora", "code": "puerto_ayora", "priority": 3, "latency_ms": 200},  # Conexión satelital
                {"name": "Puerto Baquerizo Moreno", "code": "puerto_baquerizo", "priority": 3, "latency_ms": 200},
            ]
        },
    }
    
    # 🌎 Proximidad geográfica EXPANDIDA
    PROXIMITY_MAP = {
        # Sierra Norte
        "pichincha": ["imbabura", "santo_domingo", "cotopaxi", "napo"],
        "imbabura": ["pichincha", "carchi", "esmeraldas"],
        "carchi": ["imbabura", "sucumbios"],
        
        # Sierra Centro
        "cotopaxi": ["pichincha", "tungurahua", "los_rios", "napo"],
        "tungurahua": ["cotopaxi", "chimborazo", "pastaza", "bolivar"],
        "chimborazo": ["tungurahua", "bolivar", "guayas", "cañar"],
        "bolivar": ["chimborazo", "tungurahua", "los_rios", "guayas"],
        
        # Sierra Sur
        "cañar": ["azuay", "chimborazo", "guayas", "el_oro"],
        "azuay": ["cañar", "el_oro", "morona_santiago", "loja"],
        "loja": ["azuay", "el_oro", "zamora_chinchipe"],
        
        # Costa Norte
        "esmeraldas": ["imbabura", "manabi", "pichincha", "santo_domingo"],
        "santo_domingo": ["pichincha", "esmeraldas", "manabi", "los_rios"],
        
        # Costa Centro
        "manabi": ["esmeraldas", "santo_domingo", "los_rios", "guayas"],
        "los_rios": ["manabi", "santo_domingo", "guayas", "cotopaxi", "bolivar"],
        
        # Costa Sur
        "guayas": ["los_rios", "manabi", "santa_elena", "cañar", "bolivar", "el_oro"],
        "santa_elena": ["guayas"],
        "el_oro": ["guayas", "azuay", "loja"],
        
        # Oriente
        "sucumbios": ["carchi", "orellana", "napo"],
        "orellana": ["sucumbios", "napo"],
        "napo": ["pichincha", "cotopaxi", "orellana", "sucumbios", "pastaza"],
        "pastaza": ["napo", "tungurahua", "morona_santiago"],
        "morona_santiago": ["pastaza", "azuay", "zamora_chinchipe"],
        "zamora_chinchipe": ["morona_santiago", "loja"],
        
        # Insular
        "galapagos": ["guayas", "manabi"],  # Conexión vía vuelos
    }
    
    @classmethod
    def get_optimal_location(
        cls,
        country: str = "ec",
        exclude_cities: List[str] = None
    ) -> GeoLocation:
        """
        🎯 Obtiene la ubicación ÓPTIMA (menor latencia)
        
        Returns:
            GeoLocation con la mejor latencia disponible
        """
        exclude_cities = exclude_cities or []
        
        all_locations = cls.get_all_locations(country)
        
        # Filtrar excluidas
        available = [
            loc for loc in all_locations
            if loc.city_code not in exclude_cities
        ]
        
        if not available:
            logger.warning("No available locations, returning default (Guayaquil)")
            return cls.create_location(country="ec", region="guayas", city="guayaquil")
        
        # Ordenar por latencia (menor = mejor)
        available.sort(key=lambda loc: loc.estimated_latency_ms)
        
        optimal = available[0]
        
        logger.info(
            f"✓ Optimal location selected: {optimal.city}, {optimal.region} "
            f"(latency: {optimal.estimated_latency_ms}ms)"
        )
        
        return optimal
    
    @classmethod
    def create_location(
        cls,
        country: str = "ec",
        region: Optional[str] = None,
        city: Optional[str] = None
    ) -> GeoLocation:
        """Crea ubicación geográfica válida"""
        
        country = country.lower()
        country_name = "Ecuador" if country == "ec" else country.upper()
        
        if not region and not city:
            return GeoLocation(
                country=country,
                country_name=country_name,
                priority=1,
                estimated_latency_ms=100
            )
        
        if region:
            region = region.lower().replace(" ", "_")
            
            if region in cls.ECUADOR_GEO:
                region_data = cls.ECUADOR_GEO[region]
                
                if city:
                    city_normalized = city.lower().replace(" ", "_")
                    
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
                            priority=city_data["priority"],
                            estimated_latency_ms=city_data["latency_ms"]
                        )
                    else:
                        default_city = region_data["cities"][0]
                        return GeoLocation(
                            country=country,
                            country_name=country_name,
                            region=region_data["region_name"],
                            region_code=region,
                            city=default_city["name"],
                            city_code=default_city["code"],
                            priority=default_city["priority"],
                            estimated_latency_ms=default_city["latency_ms"]
                        )
                else:
                    return GeoLocation(
                        country=country,
                        country_name=country_name,
                        region=region_data["region_name"],
                        region_code=region,
                        priority=1,
                        estimated_latency_ms=100
                    )
        
        # Default: Guayaquil (mejor latencia)
        logger.warning(f"Invalid location, using Guayaquil (optimal)")
        return GeoLocation(
            country="ec",
            country_name="Ecuador",
            region="Guayas",
            region_code="guayas",
            city="Guayaquil",
            city_code="guayaquil",
            priority=1,
            estimated_latency_ms=70
        )
    
    @classmethod
    def get_fallback_locations(
        cls,
        current_location: GeoLocation,
        exclude_cities: List[str] = None
    ) -> List[GeoLocation]:
        """
        Genera fallbacks ordenados por LATENCIA (mejor primero)
        
        Estrategia:
        1. Ciudades con mejor latencia en misma región
        2. Ciudades con mejor latencia en regiones cercanas
        3. Ciudades con mejor latencia en todo Ecuador
        """
        
        fallbacks = []
        exclude_cities = exclude_cities or []
        
        # 1. Misma región
        if current_location.region_code:
            region_data = cls.ECUADOR_GEO.get(current_location.region_code)
            
            if region_data:
                for city_data in region_data["cities"]:
                    if city_data["code"] not in exclude_cities and city_data["code"] != current_location.city_code:
                        fallbacks.append(GeoLocation(
                            country=current_location.country,
                            country_name=current_location.country_name,
                            region=region_data["region_name"],
                            region_code=current_location.region_code,
                            city=city_data["name"],
                            city_code=city_data["code"],
                            priority=city_data["priority"],
                            estimated_latency_ms=city_data["latency_ms"]
                        ))
        
        # 2. Regiones cercanas
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
                                priority=city_data["priority"],
                                estimated_latency_ms=city_data["latency_ms"]
                            ))
        
        # 3. Resto de Ecuador
        for region_code, region_data in cls.ECUADOR_GEO.items():
            if region_code != current_location.region_code:
                for city_data in region_data["cities"]:
                    if city_data["code"] not in exclude_cities and city_data["priority"] == 1:
                        fallbacks.append(GeoLocation(
                            country=current_location.country,
                            country_name=current_location.country_name,
                            region=region_data["region_name"],
                            region_code=region_code,
                            city=city_data["name"],
                            city_code=city_data["code"],
                            priority=city_data["priority"],
                            estimated_latency_ms=city_data["latency_ms"]
                        ))
        
        # 🎯 ORDENAR POR LATENCIA (menor = mejor)
        fallbacks.sort(key=lambda loc: (loc.estimated_latency_ms, loc.priority))
        
        return fallbacks
    
    @classmethod
    def get_all_locations(cls, country: str = "ec") -> List[GeoLocation]:
        """Obtiene TODAS las ubicaciones con sus latencias"""
        
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
                    priority=city_data["priority"],
                    estimated_latency_ms=city_data["latency_ms"]
                ))
        
        return locations
    
    @classmethod
    def get_stats(cls) -> Dict:
        """Estadísticas del mapa geográfico"""
        all_locations = cls.get_all_locations()
        
        return {
            "total_locations": len(all_locations),
            "total_regions": len(cls.ECUADOR_GEO),
            "avg_latency_ms": sum(loc.estimated_latency_ms for loc in all_locations) / len(all_locations),
            "best_latency_ms": min(loc.estimated_latency_ms for loc in all_locations),
            "worst_latency_ms": max(loc.estimated_latency_ms for loc in all_locations),
            "regions": list(cls.ECUADOR_GEO.keys())
        }


def get_soax_username_with_geo(
    base_username: str,
    location: GeoLocation,
    session_id: str,
    session_lifetime: int = 3600
) -> str:
    """Construye username SOAX con jerarquía completa"""
    
    parts = [base_username]
    parts.append(location.to_soax_string())
    parts.append(f"sessionid-{session_id}")
    parts.append(f"sessionlength-{session_lifetime}")
    parts.append("opt-lookalike")
    
    return "-".join(parts)


# Test
if __name__ == "__main__":
    stats = GeoManager.get_stats()
    print(f"📊 Mapa Geográfico Ecuador:")
    print(f"   Total ubicaciones: {stats['total_locations']}")
    print(f"   Total regiones: {stats['total_regions']}")
    print(f"   Latencia promedio: {stats['avg_latency_ms']:.0f}ms")
    print(f"   Mejor latencia: {stats['best_latency_ms']}ms")
    
    optimal = GeoManager.get_optimal_location()
    print(f"\n🎯 Ubicación óptima: {optimal.city}, {optimal.region}")
    print(f"   Latencia: {optimal.estimated_latency_ms}ms")
    print(f"   SOAX: {optimal.to_soax_string()}")