import aiohttp
import os
from loguru import logger
from auto_config import AutoConfig
from typing import Dict, Optional
import json

class RegistrationClient:
    """Cliente de registro automático"""
    
    def __init__(self, orchestrator_url: str, config):
        self.orchestrator_url = orchestrator_url.rstrip('/')
        self.config = config
        self.token_file = ".agent_token"
        self.registration_file = ".agent_registration.json"
    
    async def register(self) -> Dict:
        """
        Registra computadora automáticamente
        
        Returns:
            {
                "computer_id": 1,
                "token": "abc123...",
                "is_new": True/False
            }
        """
        
        # Detectar hardware
        hardware_info = AutoConfig.get_hardware_info(self.config)
        
        logger.info("🔍 Detected hardware:")
        logger.info(f"  Name: {hardware_info['name']}")
        logger.info(f"  Hostname: {hardware_info['hostname']}")
        logger.info(f"  IP: {hardware_info['ip_address']}")
        logger.info(f"  CPU: {hardware_info['cpu_cores']} cores")
        logger.info(f"  RAM: {hardware_info['ram_gb']} GB")
        logger.info(f"  AdsPower: {hardware_info['adspower_api_url']}")
        
        # Registrar en orquestador
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.orchestrator_url}/api/v1/registration/register"
                
                async with session.post(url, json=hardware_info, timeout=10) as response:
                    if response.status != 200:
                        text = await response.text()
                        raise Exception(f"Registration failed: {response.status} - {text}")
                    
                    result = await response.json()
                    
                    # Guardar token y datos de registro
                    self._save_token(result["token"])
                    self._save_registration(result)
                    
                    if result["is_new"]:
                        logger.info(f"✅ Registered as NEW computer (ID: {result['computer_id']})")
                    else:
                        logger.info(f"✅ Reconnected (ID: {result['computer_id']})")
                    
                    return result
        
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to orchestrator: {e}")
            raise Exception(f"Cannot connect to orchestrator at {self.orchestrator_url}")
        except Exception as e:
            logger.error(f"Registration error: {e}")
            raise
    
    def _save_token(self, token: str):
        """Guarda token localmente"""
        with open(self.token_file, 'w') as f:
            f.write(token)
        logger.debug(f"Token saved to {self.token_file}")
    
    def _save_registration(self, registration_data: Dict):
        """Guarda datos de registro localmente"""
        with open(self.registration_file, 'w') as f:
            json.dump(registration_data, f, indent=2)
        logger.debug(f"Registration data saved to {self.registration_file}")
    
    def load_token(self) -> Optional[str]:
        """Carga token guardado"""
        if os.path.exists(self.token_file):
            with open(self.token_file, 'r') as f:
                return f.read().strip()
        return None
    
    def load_registration(self) -> Optional[Dict]:
        """Carga datos de registro guardados"""
        if os.path.exists(self.registration_file):
            try:
                with open(self.registration_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None
    
    async def validate_token(self, token: str) -> Dict:
        """
        Valida token con orquestador
        
        Returns:
            {
                "valid": True/False,
                "computer_id": 1,
                "computer_name": "..."
            }
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.orchestrator_url}/api/v1/registration/validate"
                
                async with session.post(url, json={"token": token}, timeout=10) as response:
                    if response.status != 200:
                        return {"valid": False}
                    
                    result = await response.json()
                    return result
        
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {"valid": False}
