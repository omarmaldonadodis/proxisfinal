# app/integrations/soax_client.py - VERSIÓN ACTUALIZADA CON REGION + CITY
from typing import Dict, Optional
import httpx
import random
import string
import time
from loguru import logger


class SOAXClient:
    """Cliente para configurar proxies SOAX con jerarquía completa"""
    
    def __init__(
        self,
        username: str,
        password: str,
        host: str = "proxy.soax.com",
        port: int = 5000
    ):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
    
    def get_proxy_config(
        self,
        proxy_type: str = "mobile",
        country: Optional[str] = None,
        region: Optional[str] = None,  # ✅ NUEVO
        city: Optional[str] = None,
        session_id: Optional[str] = None,
        session_lifetime: int = 3600
    ) -> Dict:
        """
        Genera configuración de proxy SOAX con jerarquía completa
        
        ✅ NUEVO: Ahora envía country + region + city en el username
        
        Args:
            proxy_type: "mobile" o "residential"
            country: Código país (ej: "ec")
            region: Región (ej: "pichincha")
            city: Ciudad (ej: "quito")
            session_id: ID de sesión (auto-generado si None)
            session_lifetime: Duración de sesión en segundos
        
        Returns:
            Dict con configuración del proxy
        """
        if not session_id:
            session_id = self._generate_session_id()
        
        username_parts = [self.username]
        
        # ✅ NUEVO: Jerarquía completa Country → Region → City
        if country:
            username_parts.append(f"country-{country.lower()}")
        
        # ✅ CRÍTICO: Agregar REGION si existe
        if region:
            username_parts.append(f"region-{region.lower()}")
        
        # ✅ Agregar CITY si existe
        if city:
            username_parts.append(f"city-{city.lower()}")
        
        # Sesión
        username_parts.append(f"sessionid-{session_id}")
        username_parts.append(f"sessionlength-{session_lifetime}")
        username_parts.append("opt-lookalike")
        
        proxy_username = "-".join(username_parts)
        
        logger.debug(
            f"SOAX username: {proxy_username} "
            f"(country={country}, region={region}, city={city})"
        )
        
        return {
            "type": proxy_type,
            "host": self.host,
            "port": self.port,
            "username": proxy_username,
            "password": self.password,
            "session_id": session_id
        }
    
    async def test_proxy(
        self,
        proxy_config: Dict,
        timeout: float = 10.0,
        test_urls: list = None
    ) -> Dict:
        """
        Prueba proxy usando múltiples servicios
        
        ✅ NUEVO: Ahora mide velocidad y problemas
        
        Returns:
            {
                "success": True/False,
                "ip": "1.2.3.4",
                "country": "EC",
                "city": "Quito",
                "isp": "SOAX",
                "latency_ms": 234.5,
                "download_speed_mbps": 12.3,
                "issues": ["slow", "timeout"],  # ✅ NUEVO
                "error": None
            }
        """
        proxy_url = self._get_proxy_url(proxy_config)
        
        if not test_urls:
            test_urls = [
                "https://api.ipify.org?format=json",
                "http://ip-api.com/json/",
                "https://httpbin.org/ip"
            ]
        
        result = {
            "success": False,
            "ip": None,
            "country": None,
            "city": None,
            "isp": None,
            "latency_ms": None,
            "download_speed_mbps": None,
            "issues": [],
            "error": None
        }
        
        # ========================================
        # 1. TEST DE LATENCIA
        # ========================================
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(
                proxies={"http://": proxy_url, "https://": proxy_url},
                timeout=timeout
            ) as client:
                # Test con ipify
                response = await client.get(test_urls[0])
                response.raise_for_status()
                
                latency = (time.time() - start_time) * 1000
                result["latency_ms"] = round(latency, 2)
                
                # ✅ Detectar latencia alta
                if latency > 3000:
                    result["issues"].append("slow")
                
                # Obtener IP
                data = response.json()
                result["ip"] = data.get("ip")
                
                # ========================================
                # 2. TEST GEO-LOCATION
                # ========================================
                try:
                    response = await client.get("http://ip-api.com/json/")
                    if response.status_code == 200:
                        geo_data = response.json()
                        result["country"] = geo_data.get("countryCode")
                        result["city"] = geo_data.get("city")
                        result["isp"] = geo_data.get("isp")
                except Exception as e:
                    logger.debug(f"Geo test failed: {e}")
                
                # ========================================
                # 3. TEST DE VELOCIDAD (10KB download)
                # ========================================
                try:
                    start_dl = time.time()
                    response = await client.get("https://httpbin.org/bytes/10240")
                    download_time = time.time() - start_dl
                    
                    if download_time > 0:
                        file_size_mb = 10240 / (1024 * 1024)
                        speed_mbps = (file_size_mb / download_time) * 8
                        result["download_speed_mbps"] = round(speed_mbps, 2)
                        
                        # ✅ Detectar velocidad baja
                        if speed_mbps < 0.5:  # < 0.5 Mbps
                            result["issues"].append("slow_download")
                
                except Exception as e:
                    logger.debug(f"Speed test failed: {e}")
                
                result["success"] = True
        
        except httpx.TimeoutException:
            result["error"] = "timeout"
            result["issues"].append("timeout")
            logger.warning(f"Proxy timeout: {proxy_url}")
        
        except httpx.HTTPStatusError as e:
            result["error"] = f"HTTP {e.response.status_code}"
            result["issues"].append("blocked")
            logger.warning(f"Proxy blocked: {proxy_url}")
        
        except Exception as e:
            result["error"] = str(e)
            result["issues"].append("connection_error")
            logger.error(f"Proxy test failed: {e}")
        
        return result
    
    def _get_proxy_url(self, proxy_config: Dict) -> str:
        """Convierte configuración a URL de proxy"""
        return (
            f"http://{proxy_config['username']}:{proxy_config['password']}"
            f"@{proxy_config['host']}:{proxy_config['port']}"
        )
    
    def _generate_session_id(self, length: int = 16) -> str:
        """Genera un session ID aleatorio"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))