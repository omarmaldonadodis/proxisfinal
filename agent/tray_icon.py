# agent/tray_icon.py
import threading
import webbrowser
import platform
from loguru import logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.main import AdsPowerAgent

# agent/tray_icon.py

class TrayIcon:

    def __init__(self, agent):
        self.agent = agent
        self._icon = None
        self._thread = None
        self._status_item = None   # ← referencia directa al MenuItem

    def _run(self):
        try:
            import rumps
            agent_ref = self.agent
            tray_ref  = self

            class AdsPowerAgentApp(rumps.App):
                def __init__(self):
                    self._status_item = rumps.MenuItem("Estado: Conectando...", callback=None)
                    super().__init__(
                        "AdsPower Agent",
                        icon=None,
                        quit_button=None
                    )
                    self.menu = [
                        self._status_item,   # ← guardar referencia
                        None,
                        rumps.MenuItem("Abrir panel del agente", callback=self.open_panel),
                        None,
                        rumps.MenuItem("Salir", callback=self.quit_app)
                    ]
                    tray_ref._status_item = self._status_item   # ← exponer al TrayIcon

                def open_panel(self, _):
                    import webbrowser
                    webbrowser.open(f"{agent_ref.config.server_url}/agent")

                def quit_app(self, _):
                    agent_ref.stop()
                    rumps.quit_application()

            self._app = AdsPowerAgentApp()
            self._app.run()

        except ImportError:
            self._run_pystray()
        except Exception as e:
            logger.warning(f"Tray icon no disponible: {e}")

    def update_status(self, connected: bool):
        status_text = "Estado: Conectado ✅" if connected else "Estado: Desconectado ❌"
        try:
            # Opción 1: rumps — usar referencia directa
            if self._status_item is not None:
                self._status_item.title = status_text
        except Exception:
            pass
        try:
            # Opción 2: pystray — actualizar el title del icon
            if self._icon is not None:
                self._icon.title = f"AdsPower Agent — {'Conectado' if connected else 'Desconectado'}"
        except Exception:
            pass