# agent/tray_icon.py
import threading
import webbrowser
import platform
from loguru import logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.main import AdsPowerAgent


class TrayIcon:

    def __init__(self, agent: "AdsPowerAgent"):
        self.agent = agent
        self._icon = None
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            import rumps

            agent_ref = self.agent

            class AdsPowerAgentApp(rumps.App):
                def __init__(self):
                    super().__init__(
                        "AdsPower Agent",
                        icon=None,
                        quit_button=None
                    )
                    self.menu = [
                        rumps.MenuItem("Estado: Conectando...", callback=None),
                        None,  # separador
                        rumps.MenuItem("Abrir panel del agente", callback=self.open_panel),
                        None,
                        rumps.MenuItem("Salir", callback=self.quit_app)
                    ]

                def open_panel(self, _):
                    url = f"{agent_ref.config.server_url}/agent"
                    webbrowser.open(url)

                def quit_app(self, _):
                    agent_ref.stop()
                    rumps.quit_application()

            self._app = AdsPowerAgentApp()
            self._app.run()

        except ImportError:
            logger.warning("rumps no disponible, intentando pystray...")
            self._run_pystray()
        except Exception as e:
            logger.warning(f"Tray icon no disponible: {e}. Agente corriendo sin icono.")

    def _run_pystray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            agent_ref = self.agent

            def create_image():
                size = 64
                image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
                draw = ImageDraw.Draw(image)
                draw.ellipse([4, 4, size - 4, size - 4], fill=(59, 130, 246, 255))
                return image

            def open_panel(icon, item):
                webbrowser.open(f"{agent_ref.config.server_url}/agent")

            def quit_app(icon, item):
                icon.stop()
                agent_ref.stop()

            menu = pystray.Menu(
                pystray.MenuItem("Abrir panel del agente", open_panel),
                pystray.MenuItem("Salir", quit_app)
            )

            self._icon = pystray.Icon(
                "AdsPower Agent",
                create_image(),
                "AdsPower Agent",
                menu
            )
            self._icon.run()

        except Exception as e:
            logger.warning(f"pystray tampoco disponible: {e}. Sin icono en bandeja.")

    def update_status(self, connected: bool):
        try:
            if hasattr(self, '_app') and self._app:
                status = "Conectado ✅" if connected else "Desconectado ❌"
                self._app.menu["Estado: Conectando..."].title = f"Estado: {status}"
        except Exception:
            pass