# agent/first_run.py
"""
Configuración inicial por línea de comandos (sin GUI).
Compatible con todos los macOS.
"""
import sys
import httpx
from loguru import logger
from agent.config import AgentConfig


class FirstRunSetup:

    def __init__(self):
        self.config = AgentConfig.load()
        self.result = False

    def run(self) -> bool:
        print("\n" + "="*50)
        print("  CONFIGURACIÓN INICIAL - AdsPower Agent")
        print("="*50 + "\n")

        # ----------------------------------------
        # URL del servidor
        # ----------------------------------------
        default_url = self.config.server_url or "http://localhost:8000"
        server_url = input(f"URL del servidor [{default_url}]: ").strip()
        if not server_url:
            server_url = default_url
        server_url = server_url.rstrip("/")

        # Verificar conexión al servidor
        print(f"\nVerificando conexión a {server_url}...")
        try:
            response = httpx.get(f"{server_url}/health", timeout=5.0)
            if response.status_code == 200:
                print("✅ Servidor conectado correctamente")
            else:
                print(f"⚠️  Servidor respondió con código {response.status_code}, continuando...")
        except Exception as e:
            print(f"⚠️  No se pudo verificar el servidor: {e}")
            continuar = input("¿Continuar de todas formas? (s/n): ").strip().lower()
            if continuar != "s":
                return False

        # ----------------------------------------
        # Token de agente
        # ----------------------------------------
        token = input("\nToken de agente (dado por el administrador): ").strip()
        if not token:
            print("❌ El token es requerido")
            return False

        # ----------------------------------------
        # Nombre del agente
        # ----------------------------------------
        import socket
        default_name = self.config.agent_name or socket.gethostname()
        name = input(f"Tu nombre [{default_name}]: ").strip()
        if not name:
            name = default_name

        # ----------------------------------------
        # URL de AdsPower local
        # ----------------------------------------
        default_adspower_url = self.config.adspower_url or "http://local.adspower.net:50325"
        adspower_url = input(f"\nURL de AdsPower local [{default_adspower_url}]: ").strip()
        if not adspower_url:
            adspower_url = default_adspower_url

        # ----------------------------------------
        # API Key de AdsPower
        # Dónde obtenerla: AdsPower → Settings → API → Local API Key
        # ----------------------------------------
        default_key_hint = f"{self.config.adspower_api_key[:8]}..." if self.config.adspower_api_key else "(vacío)"
        print(f"\nAPI Key de AdsPower")
        print(f"  Dónde obtenerla: AdsPower → Settings (⚙️) → API → Local API Key")
        adspower_api_key = input(f"  API Key [{default_key_hint}]: ").strip()
        if not adspower_api_key:
            adspower_api_key = self.config.adspower_api_key or ""

        # Verificar conexión a AdsPower local con la key ingresada
        if adspower_api_key:
            print(f"\nVerificando conexión a AdsPower en {adspower_url}...")
            try:
                response = httpx.get(
                    f"{adspower_url}/api/v1/user/list",
                    params={"page": 1, "page_size": 1, "api_key": adspower_api_key},
                    timeout=5.0
                )
                data = response.json()
                if data.get("code") == 0:
                    print("✅ AdsPower conectado correctamente")
                else:
                    print(f"⚠️  AdsPower respondió: {data.get('msg', 'Error desconocido')}")
            except Exception as e:
                print(f"⚠️  No se pudo verificar AdsPower: {e}")
        else:
            print("⚠️  Sin API Key de AdsPower — no podrás abrir navegadores")

        # ----------------------------------------
        # Guardar configuración
        # ----------------------------------------
        self.config.server_url = server_url
        self.config.server_token = token
        self.config.agent_name = name
        self.config.adspower_url = adspower_url
        self.config.adspower_api_key = adspower_api_key
        self.config.save()

        print(f"\n✅ Configuración guardada correctamente")
        print(f"   Servidor:       {server_url}")
        print(f"   Agente:         {name}")
        print(f"   AdsPower URL:   {adspower_url}")
        print(f"   AdsPower Key:   {adspower_api_key[:8]}..." if adspower_api_key else "   AdsPower Key:   (no configurada)")
        print()

        self.result = True
        return True