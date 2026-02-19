# agent/adspower_monitor.py
"""
Monitorea AdsPower via su API local (http://local.adspower.net:50325)
y via psutil para CPU/RAM del proceso
"""
import httpx
import psutil
import platform
from typing import List, Dict, Optional
from loguru import logger


class AdsPowerMonitor:

    def __init__(self, adspower_url: str = "http://local.adspower.net:50325", api_key: Optional[str] = None):
        self.adspower_url = adspower_url
        self.api_key = api_key
        # ← CAMBIO: Authorization Bearer en vez de api-key
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(timeout=5.0, headers=self._headers)

    def is_adspower_running(self) -> bool:
        """Verifica si AdsPower está corriendo"""
        for proc in psutil.process_iter(["name"]):
            try:
                if "adspower" in proc.info["name"].lower():
                    return True
            except Exception:
                pass
        return False

    def ping_api(self) -> bool:
        """Verifica si la API local de AdsPower responde"""
        try:
            response = self._client.get(f"{self.adspower_url}/api/v1/browser/active-list")
            return response.status_code == 200
        except Exception:
            return False

    def get_active_browsers(self) -> List[Dict]:
        """
        Lista navegadores activos via AdsPower API local.
        Retorna lista de perfiles con su estado.
        """
        try:
            response = self._client.get(
                f"{self.adspower_url}/api/v1/browser/active-list",
                params={"page": 1, "page_size": 100}
            )
            data = response.json()

            if data.get("code") == 0:
                return data.get("data", {}).get("list", [])
            return []

        except Exception as e:
            logger.debug(f"AdsPower API no disponible: {e}")
            return []

    def get_browser_status(self, profile_id: str) -> Dict:
        """Estado de un perfil específico"""
        try:
            response = self._client.get(
                f"{self.adspower_url}/api/v1/browser/active",
                params={"user_id": profile_id}
            )
            data = response.json()

            if data.get("code") == 0:
                browser_data = data.get("data", {})
                return {
                    "is_running": True,
                    "status": browser_data.get("status", "unknown"),
                    "ws_puppeteer": browser_data.get("ws", {}).get("puppeteer"),
                    "ws_selenium": browser_data.get("ws", {}).get("selenium"),
                    "debug_port": browser_data.get("debug_port")
                }
            return {"is_running": False}

        except Exception:
            return {"is_running": False, "error": "API no disponible"}

    def open_browser(self, profile_id: str, url: Optional[str] = None, api_key: Optional[str] = None) -> Dict:
        try:
            params = {
                "user_id": profile_id,
                "open_tabs": 1,
                "ip_tab": 0,
            }
            if url:
                params["launch_args"] = f'["--new-tab={url}"]'

            # self._client ya tiene el header Authorization: Bearer
            response = self._client.get(
                f"{self.adspower_url}/api/v1/browser/start",
                params=params
            )
            data = response.json()

            if data.get("code") == 0:
                browser_data = data.get("data", {})
                return {
                    "success": True,
                    "selenium": browser_data.get("ws", {}).get("selenium"),
                    "puppeteer": browser_data.get("ws", {}).get("puppeteer"),
                    "debug_port": browser_data.get("debug_port"),
                    "webdriver": browser_data.get("webdriver")
                }
            else:
                return {"success": False, "error": data.get("msg", "Error desconocido")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_browser(self, profile_id: str) -> bool:
        """Cierra un perfil"""
        try:
            response = self._client.get(
                f"{self.adspower_url}/api/v1/browser/stop",
                params={"user_id": profile_id}
            )
            data = response.json()
            return data.get("code") == 0
        except Exception:
            return False

    def get_process_stats(self) -> Dict:
        """CPU y RAM que consume AdsPower en total"""
        total_cpu = 0.0
        total_ram_mb = 0.0
        process_count = 0

        for proc in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
            try:
                if "adspower" in proc.info["name"].lower():
                    total_cpu += proc.info["cpu_percent"] or 0
                    total_ram_mb += (proc.info["memory_info"].rss or 0) / (1024 * 1024)
                    process_count += 1
            except Exception:
                pass

        return {
            "is_running": process_count > 0,
            "process_count": process_count,
            "cpu_percent": round(total_cpu, 2),
            "ram_mb": round(total_ram_mb, 2)
        }

    def get_browser_health(self, profile_id: str) -> str:
        """
        Determina salud del navegador:
        healthy / slow / crashed / unknown
        """
        import time

        start = time.time()
        status = self.get_browser_status(profile_id)
        response_time = (time.time() - start) * 1000  # ms

        if not status.get("is_running"):
            return "crashed"
        if response_time > 3000:
            return "slow"
        return "healthy"

    def cleanup(self):
        self._client.close()