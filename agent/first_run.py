# agent/first_run.py  ← REEMPLAZAR COMPLETO
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

        # URL del servidor
        default_url = self.config.server_url or "http://localhost:8000"
        server_url = input(f"URL del servidor [{default_url}]: ").strip()
        if not server_url:
            server_url = default_url
        server_url = server_url.rstrip("/")

        # Verificar conexión
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

        # Token
        token = input("\nToken de agente (dado por el administrador): ").strip()
        if not token:
            print("❌ El token es requerido")
            return False

        # Nombre
        import socket
        default_name = self.config.agent_name or socket.gethostname()
        name = input(f"Tu nombre [{default_name}]: ").strip()
        if not name:
            name = default_name

        # Guardar
        self.config.server_url = server_url
        self.config.server_token = token
        self.config.agent_name = name
        self.config.save()

        print(f"\n✅ Configuración guardada correctamente")
        print(f"   Servidor: {server_url}")
        print(f"   Agente:   {name}\n")

        self.result = True
        return True