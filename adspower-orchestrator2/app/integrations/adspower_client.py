# app/integrations/adspower_client.py - ✅ VERSIÓN CORREGIDA
from typing import Dict, List, Optional
import httpx
from loguru import logger


class AdsPowerClient:
    """Cliente para interactuar con AdsPower API"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.timeout = 60.0  # ✅ Aumentado a 60s (AdsPower puede ser lento)
    
    def _get_headers(self) -> Dict[str, str]:
        """Genera headers con Bearer token"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict:
        """Hace una petición HTTP a la API de AdsPower"""
        url = f"{self.api_url}{endpoint}"
        headers = self._get_headers()
        
        # ✅ CRÍTICO: Si data contiene "cookie" como string, no hacer json.dumps doble
        request_data = data
        
        if data and "cookie" in data:
            # ✅ Verificar si cookie ya es string JSON
            if isinstance(data["cookie"], str):
                logger.debug("Cookie is JSON string, keeping as-is")
            elif isinstance(data["cookie"], list):
                # ✅ Convertir lista a JSON string
                import json as json_lib
                data_copy = data.copy()
                data_copy["cookie"] = json_lib.dumps(data["cookie"])
                request_data = data_copy
                logger.debug(f"Converted cookie list to JSON: {data_copy['cookie'][:200]}")
        
        try:
            # ✅ LOGGING DETALLADO
            logger.debug(f"Making {method} request to: {url}")
            logger.debug(f"Headers: {headers}")
            if params:
                logger.debug(f"Params: {params}")
            if request_data:
                logger.debug(f"Data keys: {list(request_data.keys())}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=request_data
                )
                
                # ✅ Log response para debugging
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response body (first 500): {response.text[:500]}")
                
                response.raise_for_status()
                return response.json()
        
        except httpx.ConnectError as e:
            logger.error(f"❌ AdsPower connection error: Cannot connect to {url}")
            logger.error(f"   Error: {str(e)}")
            logger.error(f"   ¿Está AdsPower corriendo en este computer?")
            raise Exception(f"Cannot connect to AdsPower at {url}. Is AdsPower running?")
        
        except httpx.TimeoutException as e:
            logger.error(f"❌ AdsPower timeout: {url}")
            logger.error(f"   Error: {str(e)}")
            raise Exception(f"AdsPower API timeout after {self.timeout}s")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ AdsPower API error: {e.response.status_code}")
            logger.error(f"   URL: {url}")
            logger.error(f"   Response: {e.response.text}")
            raise Exception(f"AdsPower API error: {e.response.status_code} - {e.response.text[:200]}")
        
        except Exception as e:
            logger.error(f"❌ Unexpected AdsPower error: {type(e).__name__}")
            logger.error(f"   Error: {str(e)}")
            raise Exception(f"AdsPower error: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Prueba la conexión con AdsPower"""
        try:
            result = await self._make_request(
                "GET", 
                "/api/v1/user/list", 
                params={"page": 1, "page_size": 1}
            )
            return result.get("code") == 0
        except Exception as e:
            logger.error(f"AdsPower connection test failed: {str(e)}")
            return False
    
    async def update_profile(self, profile_id: str, profile_data: Dict) -> bool:
        """
        ✅ ACTUALIZADO: Retorna True/False explícitamente
        """
        data = {"user_id": profile_id, **profile_data}
        
        logger.debug(f"Updating profile {profile_id} with keys: {list(profile_data.keys())}")
        
        try:
            result = await self._make_request("POST", "/api/v1/user/update", data=data)
            
            if result.get("code") == 0:
                logger.info(f"✅ Profile {profile_id} updated successfully")
                return True
            else:
                logger.warning(
                    f"⚠️ Profile update failed - code: {result.get('code')}, "
                    f"msg: {result.get('msg')}"
                )
                return False
        
        except Exception as e:
            logger.error(f"❌ Exception updating profile {profile_id}: {str(e)}")
            return False
    
    async def create_profile(self, profile_data: Dict) -> Dict:
        """Crea un nuevo perfil en AdsPower"""
        result = await self._make_request("POST", "/api/v1/user/create", data=profile_data)
        return result
    
    async def get_profile(self, profile_id: str) -> Dict:
        """Obtiene información de un perfil"""
        result = await self._make_request(
            "GET",
            "/api/v1/user/detail",
            params={"user_id": profile_id}
        )
        
        if result.get("code") != 0:
            raise Exception(f"Failed to get profile: {result.get('msg')}")
        
        return result["data"]
    
    async def list_profiles(self, page: int = 1, page_size: int = 100, group_id: Optional[str] = None) -> Dict:
        """Lista perfiles de AdsPower"""
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if group_id:
            params["group_id"] = group_id
        
        result = await self._make_request("GET", "/api/v1/user/list", params=params)
        
        if result.get("code") != 0:
            raise Exception(f"Failed to list profiles: {result.get('msg')}")
        
        return result["data"]
    
    async def delete_profile(self, profile_ids: List[str]) -> bool:
        """Elimina uno o más perfiles"""
        result = await self._make_request(
            "POST",
            "/api/v1/user/delete",
            data={"user_ids": profile_ids}
        )
        
        return result.get("code") == 0
    
    async def open_browser(self, profile_id: str, **kwargs) -> Dict:
        """Abre el navegador para un perfil"""
        params = {
            "user_id": profile_id,
            "ip_tab": kwargs.get("ip_tab", 0),
            "new_first_tab": kwargs.get("new_first_tab", 1),
            "launch_args": kwargs.get("launch_args", []),
            "headless": kwargs.get("headless", 0)
        }
        
        result = await self._make_request("GET", "/api/v1/browser/start", params=params)
        
        if result.get("code") != 0:
            raise Exception(f"Failed to open browser: {result.get('msg')}")
        
        return result["data"]
    
    async def close_browser(self, profile_id: str) -> bool:
        """Cierra el navegador de un perfil"""
        result = await self._make_request(
            "GET",
            "/api/v1/browser/stop",
            params={"user_id": profile_id}
        )
        
        return result.get("code") == 0
    
    async def check_browser_status(self, profile_id: str) -> Dict:
        """Verifica el estado del navegador de un perfil"""
        result = await self._make_request(
            "GET",
            "/api/v1/browser/active",
            params={"user_id": profile_id}
        )
        
        if result.get("code") != 0:
            return {"status": "inactive"}
        
        return result["data"]
    
    async def upload_cookies(self, profile_id: str, cookies: List[Dict]) -> bool:
        """
        Sube cookies a un perfil existente
        """
        return await self.update_profile(profile_id, {"cookie": cookies})