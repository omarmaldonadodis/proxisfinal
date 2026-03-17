# agent/adspower_monitor.py
import asyncio
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
        self._headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        self._client = httpx.Client(timeout=5.0, headers=self._headers)

    # ──────────────────────────────────────────────
    # OPCIÓN A: Verifica una lista conocida de perfiles (rápido)
    # ──────────────────────────────────────────────

    def get_active_browsers_from_known(self, profile_ids: List[str]) -> List[Dict]:
        """
        Verifica en paralelo (threads) el estado de una lista conocida de profile_ids.
        Usa los perfiles que el BrowserLauncher ya conoce.
        Ideal para polling frecuente — O(n) requests donde n = sesiones activas del agente.
        """
        if not profile_ids:
            return []

        active = []
        # httpx no tiene async aquí, usamos un pool simple con ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def check_one(pid: str) -> Optional[Dict]:
            try:
                r = self._client.get(
                    f"{self.adspower_url}/api/v1/browser/active",
                    params={"user_id": pid}
                )
                data = r.json()
                if data.get("code") == 0 and data.get("data", {}).get("status") == "Active":
                    return {
                        "user_id": pid,
                        "status": "Active",
                        "ws": data["data"].get("ws", {}),
                        "debug_port": data["data"].get("debug_port"),
                    }
            except Exception as e:
                logger.debug(f"Error verificando perfil {pid}: {e}")
            return None

        with ThreadPoolExecutor(max_workers=min(len(profile_ids), 10)) as pool:
            futures = {pool.submit(check_one, pid): pid for pid in profile_ids}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    active.append(result)

        return active

    # ──────────────────────────────────────────────
    # OPCIÓN B: Scan completo de todos los perfiles (costoso pero completo)
    # Detecta browsers abiertos desde fuera del agente
    # ──────────────────────────────────────────────

    def get_active_browsers_full_scan(self, max_profiles: int = 200) -> List[Dict]:
        """
        Pagina /api/v1/user/list y verifica cada perfil contra /api/v1/browser/active.
        Llama esto solo cuando necesitas descubrir browsers que no abriste tú.
        Respeta el rate limit de AdsPower: 2-10 req/s según cantidad de perfiles.
        """
        profile_ids = self._get_all_profile_ids(max_profiles)
        logger.debug(f"Full scan: {len(profile_ids)} perfiles a verificar")

        if not profile_ids:
            return []

        return self.get_active_browsers_from_known(profile_ids)

    def _get_all_profile_ids(self, max_profiles: int = 200) -> List[str]:
        """Pagina /api/v1/user/list y retorna todos los user_ids"""
        ids = []
        page = 1
        page_size = 100

        while len(ids) < max_profiles:
            try:
                r = self._client.get(
                    f"{self.adspower_url}/api/v1/user/list",
                    params={"page": page, "page_size": page_size}
                )
                data = r.json()

                if data.get("code") != 0:
                    break

                profiles = data.get("data", {}).get("list", [])
                if not profiles:
                    break  # No hay más páginas

                ids.extend(p["user_id"] for p in profiles if "user_id" in p)

                # Si nos devolvieron menos que page_size, es la última página
                if len(profiles) < page_size:
                    break

                page += 1

            except Exception as e:
                logger.debug(f"Error paginando perfiles página {page}: {e}")
                break

        return ids[:max_profiles]

    # ──────────────────────────────────────────────
    # Método principal — usa A por default
    # ──────────────────────────────────────────────

    def get_active_browsers(self, known_profile_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        Por default usa la lista conocida (rápido).
        Si known_profile_ids es None y no hay nada que verificar, retorna [].
        """
        if known_profile_ids is not None:
            return self.get_active_browsers_from_known(known_profile_ids)
        return []

    # ──────────────────────────────────────────────
    # Resto de métodos sin cambios
    # ──────────────────────────────────────────────

    def is_adspower_running(self) -> bool:
        for proc in psutil.process_iter(["name"]):
            try:
                if "adspower" in proc.info["name"].lower():
                    return True
            except Exception:
                pass
        return False

    def ping_api(self) -> bool:
        try:
            response = self._client.get(
                f"{self.adspower_url}/api/v1/browser/active",
                params={"user_id": "ping_test"}
            )
            return response.status_code in (200, 400)
        except Exception:
            return False

    def get_browser_status(self, profile_id: str) -> Dict:
        try:
            response = self._client.get(
                f"{self.adspower_url}/api/v1/browser/active",
                params={"user_id": profile_id}
            )
            data = response.json()
            if data.get("code") == 0:
                browser_data = data.get("data", {})
                return {
                    "is_running": browser_data.get("status") == "Active",
                    "status": browser_data.get("status", "unknown"),
                    "ws_puppeteer": browser_data.get("ws", {}).get("puppeteer"),
                    "ws_selenium": browser_data.get("ws", {}).get("selenium"),
                    "debug_port": browser_data.get("debug_port")
                }
            return {"is_running": False}
        except Exception:
            return {"is_running": False, "error": "API no disponible"}

    def open_browser(self, profile_id: str, url: Optional[str] = None) -> Dict:
        try:
            params = {"user_id": profile_id, "open_tabs": 1, "ip_tab": 0}
            if url:
                params["open_urls"] = url

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
            return {"success": False, "error": data.get("msg", "Error desconocido")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_browser(self, profile_id: str) -> bool:
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