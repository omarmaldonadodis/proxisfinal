# app/integrations/threexui_client.py
import httpx
from typing import Dict, List, Optional
from loguru import logger

class ThreeXUIClient:
    """Cliente para 3X-UI Panel (opcional)"""
    
    def __init__(self, panel_url: str, username: str, password: str):
        self.panel_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session_cookie = None
    
    async def login(self) -> bool:
        """Login al panel"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.panel_url}/login",
                    data={
                        'username': self.username,
                        'password': self.password
                    }
                )
                
                if response.status_code == 200:
                    self.session_cookie = response.cookies.get('session')
                    logger.info("3X-UI login successful")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"3X-UI login failed: {e}")
            return False
    
    async def get_inbounds(self) -> List[Dict]:
        """Obtiene lista de inbounds"""
        if not self.session_cookie:
            await self.login()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.panel_url}/panel/api/inbounds/list",
                    cookies={'session': self.session_cookie}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('obj', [])
                
                return []
        except Exception as e:
            logger.error(f"Failed to get inbounds: {e}")
            return []
    
    async def add_client(self, inbound_id: int, email: str) -> Optional[str]:
        """Agrega un cliente a un inbound"""
        if not self.session_cookie:
            await self.login()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.panel_url}/panel/api/inbounds/addClient",
                    json={
                        'id': inbound_id,
                        'settings': {
                            'clients': [{
                                'email': email,
                                'enable': True,
                                'expiryTime': 0,
                                'totalGB': 0
                            }]
                        }
                    },
                    cookies={'session': self.session_cookie}
                )
                
                if response.status_code == 200:
                    logger.info(f"Client added: {email}")
                    return email
                
                return None
        except Exception as e:
            logger.error(f"Failed to add client: {e}")
            return None