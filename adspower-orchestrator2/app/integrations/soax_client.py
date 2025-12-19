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
        # ✅ VALIDAR formato del username
        if not username or not username.startswith("package-"):
            logger.error(
                f"❌ SOAX_USERNAME inválido: '{username}'\n"
                f"   Formato esperado: 'package-XXXXXX'\n"
                f"   Ejemplo: 'package-325401'\n"
                f"   Verifica tu archivo .env"
            )
            raise ValueError(
                f"SOAX_USERNAME debe tener formato 'package-XXXXXX', "
                f"recibido: '{username}'"
            )
        
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        
        logger.info(f"✅ SOAXClient inicializado con username: {username}")
    
    def get_proxy_config(
        self,
        proxy_type: str = "mobile",
        country: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        session_id: Optional[str] = None,
        session_lifetime: int = 3600
    ) -> Dict:
        """
        Genera configuración de proxy SOAX con jerarquía completa
        
        ✅ NUEVO: Valida que username tenga formato correcto
        """
        if not session_id:
            session_id = self._generate_session_id()
        
        # ✅ USAR self.username completo (package-325401)
        username_parts = [self.username]  # "package-325401"
        
        # Agregar country
        if country:
            username_parts.append(f"country-{country.lower()}")
        
        # Agregar region
        if region:
            username_parts.append(f"region-{region.lower()}")
        
        # Agregar city
        if city:
            username_parts.append(f"city-{city.lower()}")
        
        # Sesión
        username_parts.append(f"sessionid-{session_id}")
        username_parts.append(f"sessionlength-{session_lifetime}")
        username_parts.append("opt-lookalike")
        
        proxy_username = "-".join(username_parts)
        
        # ✅ LOG para debugging
        logger.info(
            f"✅ SOAX username construido:\n"
            f"   Base: {self.username}\n"
            f"   Full: {proxy_username[:80]}...\n"
            f"   Location: {city or region or country}"
        )
        
        return {
            "type": proxy_type,
            "host": self.host,
            "port": self.port,
            "username": proxy_username,
            "password": self.password,
            "session_id": session_id
        }
    
    def _get_proxy_url(self, proxy_config: Dict) -> str:
        """Convierte configuración a URL de proxy"""
        return (
            f"http://{proxy_config['username']}:{proxy_config['password']}"
            f"@{proxy_config['host']}:{proxy_config['port']}"
        )
    
    def _generate_session_id(self, length: int = 16) -> str:
        """Genera un session ID aleatorio"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))