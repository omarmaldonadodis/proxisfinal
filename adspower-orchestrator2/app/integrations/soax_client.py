# app/integrations/soax_client.py
from typing import Dict, Optional
import httpx
import random
import string
from loguru import logger


class SOAXClient:
    """Cliente para configurar proxies SOAX"""
    
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
        city: Optional[str] = None,
        region: Optional[str] = None,
        session_id: Optional[str] = None,
        session_lifetime: int = 3600
    ) -> Dict:
        """Genera configuración de proxy SOAX"""
        # Generar session_id si no se proporciona
        if not session_id:
            session_id = self._generate_session_id()
        
        # Construir username con parámetros SOAX
        username_parts = [self.username]
        
        if country:
            username_parts.append(f"country-{country.lower()}")
        
        if city:
            username_parts.append(f"city-{city.lower()}")
        elif region:
            username_parts.append(f"region-{region.lower()}")
        
        username_parts.append(f"sessionid-{session_id}")
        username_parts.append(f"sessionlength-{session_lifetime}")
        username_parts.append("opt-lookalike")
        
        proxy_username = "-".join(username_parts)
        
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
        timeout: float = 10.0
    ) -> Dict:
        """Prueba un proxy usando múltiples servicios"""
        proxy_url = self._get_proxy_url(proxy_config)
        
        # Intentar con diferentes servicios
        test_services = [
            {
                "url": "https://api.ipify.org?format=json",
                "parser": lambda r: {"ip": r.json().get("ip")}
            },
            {
                "url": "http://ip-api.com/json/",
                "parser": lambda r: {
                    "ip": r.json().get("query"),
                    "country": r.json().get("countryCode"),
                    "city": r.json().get("city"),
                    "isp": r.json().get("isp")
                }
            },
            {
                "url": "https://httpbin.org/ip",
                "parser": lambda r: {"ip": r.json().get("origin")}
            }
        ]
        
        start_time = None
        
        for service in test_services:
            try:
                import time
                start_time = time.time()
                
                async with httpx.AsyncClient(
                    proxies={"http://": proxy_url, "https://": proxy_url},
                    timeout=timeout
                ) as client:
                    response = await client.get(service["url"])
                    response.raise_for_status()
                    
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    
                    # Parsear respuesta
                    data = service["parser"](response)
                    
                    return {
                        "success": True,
                        "ip": data.get("ip"),
                        "country": data.get("country"),
                        "city": data.get("city"),
                        "isp": data.get("isp"),
                        "response_time_ms": round(response_time, 2),
                        "error": None
                    }
                    
            except Exception as e:
                logger.debug(f"Service {service['url']} failed: {str(e)}")
                continue
        
        # Si todos los servicios fallaron
        return {
            "success": False,
            "ip": None,
            "country": None,
            "city": None,
            "isp": None,
            "response_time_ms": 0,
            "error": "All test services failed"
        }
    
    def _get_proxy_url(self, proxy_config: Dict) -> str:
        """Convierte configuración a URL de proxy"""
        return f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
    
    def _generate_session_id(self, length: int = 16) -> str:
        """Genera un session ID aleatorio"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))