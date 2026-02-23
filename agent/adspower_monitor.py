# agent/adspower_monitor.py
"""
Monitorea AdsPower via su API local (http://local.adspower.net:50325)
y via psutil para CPU/RAM del proceso.

NOTA SOBRE AUTENTICACIÓN:
AdsPower local API usa Authorization: Bearer <api_key> en el header.
NO como query parameter.
"""
import httpx
import psutil
from typing import List, Dict, Optional
from loguru import logger


class AdsPowerMonitor:

    def __init__(
        self,
        adspower_url: str = "http://local.adspower.net:50325",
        api_key: Optional[str] = None
    ):
        self.adspower_url = adspower_url.rstrip("/")
        self.api_key = api_key or ""
        self._client = httpx.Client(
            timeout=5.0,
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        )

    def is_adspower_running(self) -> bool:
        """Verifica si AdsPower está corriendo como proceso"""
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
            response = self._client.get(
                f"{self.adspower_url}/api/v1/browser/active",
                params={"user_id": "ping_test"}
            )
            return response.status_code in (200, 400)
        except Exception:
            return False

    def get_active_browsers(self) -> List[Dict]:
        """Lista navegadores activos via AdsPower API local."""
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

    def open_browser(
        self,
        profile_id: str,
        url: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> Dict:
        """Abre un perfil en AdsPower via Authorization: Bearer header."""
        try:
            params = {
                "user_id": profile_id,
                "open_tabs": 1,
                "ip_tab": 0,
            }

            # AdsPower acepta open_urls para abrir una URL al inicio
            if url:
                params["open_urls"] = url

            logger.debug(f"AdsPower open_browser: user_id={profile_id}, url={url}")

            # Timeout extendido: AdsPower puede tardar 15-30s en lanzar el navegador
            response = self._client.get(
                f"{self.adspower_url}/api/v1/browser/start",
                params=params,
                timeout=30.0
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
                error_msg = data.get("msg", "Error desconocido")
                logger.error(f"AdsPower open_browser error: code={data.get('code')}, msg={error_msg}")
                return {"success": False, "error": error_msg}

        except Exception as e:
            logger.error(f"Excepción en open_browser: {e}")
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
        """healthy / slow / crashed"""
        import time
        start = time.time()
        status = self.get_browser_status(profile_id)
        response_time = (time.time() - start) * 1000

        if not status.get("is_running"):
            return "crashed"
        if response_time > 3000:
            return "slow"
        return "healthy"

    def cleanup(self):
        self._client.close()