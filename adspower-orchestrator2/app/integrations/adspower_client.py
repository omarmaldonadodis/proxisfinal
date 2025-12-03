from typing import Dict, List, Optional
import httpx
from loguru import logger


class AdsPowerClient:
    """Cliente para interactuar con AdsPower API"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.timeout = 30.0
    
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
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"AdsPower API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"AdsPower API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"AdsPower connection error: {str(e)}")
            raise Exception(f"AdsPower connection error: {str(e)}")
    
    async def test_connection(self) -> bool:
        """Prueba la conexión con AdsPower"""
        try:
            result = await self._make_request("GET", "/api/v1/user/list", params={"page": 1, "page_size": 1})
            return result.get("code") == 0
        except Exception as e:
            logger.error(f"AdsPower connection test failed: {str(e)}")
            return False
    
    async def create_profile(self, profile_data: Dict) -> Dict:
        """Crea un nuevo perfil en AdsPower"""
        # ✅ FIX: Retornar dict completo en lugar de solo el ID
        result = await self._make_request("POST", "/api/v1/user/create", data=profile_data)
        return result  # Retorna todo el dict con code, msg, data
    
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
    
    async def update_profile(self, profile_id: str, profile_data: Dict) -> bool:
        """Actualiza un perfil existente"""
        data = {"user_id": profile_id, **profile_data}
        result = await self._make_request("POST", "/api/v1/user/update", data=data)
        
        return result.get("code") == 0
    
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
