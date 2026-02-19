# agent/config.py
"""
Maneja la configuración local del agente.
Se guarda en config.json junto al ejecutable.
"""
import json
import os
import platform
import socket
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


def get_config_path() -> Path:
    """
    Ruta del config.json según el SO:
    - Windows: C:/Users/<user>/AppData/Local/AdsPowerAgent/config.json
    - Mac:     ~/Library/Application Support/AdsPowerAgent/config.json
    - Linux:   ~/.config/AdsPowerAgent/config.json
    """
    system = platform.system()

    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"

    config_dir = base / "AdsPowerAgent"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


@dataclass
class AgentConfig:
    # Servidor
    server_url: str = ""
    server_token: str = ""

    # AdsPower local
    adspower_url: str = "http://local.adspower.net:50325"
    adspower_api_key: str = ""        # ← AGREGAR ESTA LÍNEA

    # Esta computadora (llenado al registrarse)
    computer_id: Optional[int] = None
    computer_token: Optional[str] = None

    # Info del agente humano
    agent_name: str = ""

    # Configuración
    metrics_interval_seconds: int = 10
    auto_start: bool = True

    @classmethod
    def load(cls) -> "AgentConfig":
        path = get_config_path()

        if not path.exists():
            return cls()

        try:
            with open(path, "r") as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except Exception:
            return cls()

    def save(self):
        path = get_config_path()
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    def is_configured(self) -> bool:
        """Verifica si el agente ya fue configurado"""
        return bool(self.server_url and self.server_token and self.agent_name)

    def get_hostname(self) -> str:
        return socket.gethostname()

    def get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"