import socket
import platform
import psutil
import os
from typing import Dict

class AutoConfig:
    """Detecta configuración automáticamente"""
    
    @staticmethod 
    def get_hardware_info(config) -> Dict:
        """
        Detecta información de hardware
        
        Args:
            config: AgentConfig con valores básicos
        """
        
        # Nombre único de computadora
        hostname = socket.gethostname()
        name = config.COMPUTER_NAME
        
        # IP local
        ip_address = AutoConfig._get_local_ip()
        
        
        # AdsPower API URL
        if config.ADSPOWER_API_URL:
            adspower_url = config.ADSPOWER_API_URL
        else:
            # Auto-detectar basado en IP local
            adspower_url = f"http://{ip_address}:50325"
        
        # Hardware
        cpu_cores = psutil.cpu_count()
        ram_gb = round(psutil.virtual_memory().total / (1024**3))
        
        # OS
        os_info = f"{platform.system()} {platform.release()}"
        
        return {
            "name": name,
            "hostname": hostname,
            "ip_address": ip_address,
            "adspower_api_url": adspower_url,
            "adspower_api_key": config.ADSPOWER_API_KEY,
            "cpu_cores": cpu_cores,
            "ram_gb": ram_gb,
            "os_info": os_info
        }
    
    @staticmethod
    def _get_local_ip() -> str:
        """Detecta IP local de la computadora"""
        try:
            # Método 1: Conectar a Google DNS
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            try:
                # Método 2: Obtener hostname
                return socket.gethostbyname(socket.gethostname())
            except:
                # Fallback
                return "127.0.0.1"