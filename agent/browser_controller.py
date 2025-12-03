# agent/browser_controller.py
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
from loguru import logger
import asyncio
import os
from selenium.webdriver.chrome.service import Service


class BrowserController:
    """Controlador de navegadores AdsPower usando ChromeDriver local + Remote Debugging."""

    def __init__(self, config):
        self.config = config
        self.active_browsers: Dict[int, webdriver.Chrome] = {}
        self.browser_info: Dict[int, Dict] = {}

        # Ruta ABSOLUTA del ChromeDriver 141
        self.chromedriver_path = (
            "/Users/omarmaldonado/Desktop/proxys/proyectofinal/agent/chromedriver"
        )

        if not os.path.exists(self.chromedriver_path):
            logger.error(f"ChromeDriver no encontrado en: {self.chromedriver_path}")
        else:
            logger.info(f"ChromeDriver detectado en: {self.chromedriver_path}")

    async def open_browser(self, profile_id: int) -> Optional[webdriver.Chrome]:
        """Abre un navegador AdsPower y conecta Selenium vía Remote Debugging."""

        if profile_id in self.active_browsers:
            logger.info(f"Browser already open for profile {profile_id}")
            return self.active_browsers[profile_id]

        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.config.ADSPOWER_API_KEY}'
            }

            logger.info(f"Opening browser in AdsPower for profile {profile_id}")

            # Llamada a AdsPower API
            response = requests.get(
                f"{self.config.ADSPOWER_API_URL}/api/v1/browser/start",
                params={"user_id": profile_id},
                headers=headers,
                timeout=self.config.BROWSER_OPEN_TIMEOUT
            )

            if response.status_code != 200:
                raise Exception(f"AdsPower API error: {response.status_code} - {response.text}")

            data = response.json()
            if data.get("code") != 0:
                raise Exception(f"AdsPower error: {data.get('msg')}")

            data = data.get("data", {})
            debug_port = data.get("debug_port")

            if not debug_port:
                raise Exception("No debug_port in AdsPower response")

            logger.info(f"Browser opened on port {debug_port}")

            # Configurar Selenium para conectarse al navegador AdsPower
            service = Service(self.chromedriver_path)

            chrome_options = Options()
            chrome_options.add_experimental_option(
                "debuggerAddress",
                f"127.0.0.1:{debug_port}"
            )

            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--log-level=3")

            # Usar ChromeDriver local 141 (NO el de AdsPower)
            driver = webdriver.Chrome(
                service=service,
                options=chrome_options
            )
            self.active_browsers[profile_id] = driver
            self.browser_info[profile_id] = {
                'debug_port': debug_port,
                'opened_at': asyncio.get_event_loop().time()
            }

            logger.info(f"Selenium connected to browser for profile {profile_id}")

            # Preparar navegador
            await self._prepare_browser(driver, profile_id)

            return driver

        except Exception as e:
            logger.error(f"Failed to open browser for profile {profile_id}: {e}")
            return None

    async def _prepare_browser(self, driver: webdriver.Chrome, profile_id: int) -> bool:
        """Limpia pestañas y deja el navegador listo."""
        try:
            logger.info(f"Preparing browser for profile {profile_id}")

            all_handles = driver.window_handles

            # Cerrar DevTools si está abierto
            for handle in all_handles:
                try:
                    driver.switch_to.window(handle)
                    await asyncio.sleep(0.2)
                    if "devtools://" in driver.current_url:
                        driver.close()
                        await asyncio.sleep(0.3)
                except:
                    pass

            await asyncio.sleep(0.5)
            all_handles = driver.window_handles

            # Si no hay pestañas, abrir una
            if not all_handles:
                driver.execute_script("window.open('about:blank');")
                await asyncio.sleep(1)
                all_handles = driver.window_handles

            # Mantener solo una pestaña
            if len(all_handles) > 1:
                keep = all_handles[0]
                for h in all_handles[1:]:
                    try:
                        driver.switch_to.window(h)
                        driver.close()
                        await asyncio.sleep(0.2)
                    except:
                        pass
                await asyncio.sleep(0.5)
                driver.switch_to.window(keep)

            driver.get("about:blank")
            await asyncio.sleep(1)

            logger.info(f"Browser prepared for profile {profile_id}")
            return True

        except Exception as e:
            logger.error(f"Error preparing browser for profile {profile_id}: {e}")
            return False

    async def close_browser(self, profile_id: int) -> bool:
        """Cierra Selenium y AdsPower."""

        if profile_id not in self.active_browsers:
            logger.warning(f"Browser not open for profile {profile_id}")
            return False

        try:
            driver = self.active_browsers[profile_id]

            try:
                driver.quit()
            except:
                pass

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.config.ADSPOWER_API_KEY}'
            }

            requests.get(
                f"{self.config.ADSPOWER_API_URL}/api/v1/browser/stop",
                params={"user_id": profile_id},
                headers=headers,
                timeout=10
            )

            del self.active_browsers[profile_id]
            if profile_id in self.browser_info:
                del self.browser_info[profile_id]

            logger.info(f"Browser closed for profile {profile_id}")
            return True

        except Exception as e:
            logger.error(f"Error closing browser for profile {profile_id}: {e}")
            return False

    async def close_all_browsers(self):
        for profile_id in list(self.active_browsers.keys()):
            await self.close_browser(profile_id)

    def get_active_count(self) -> int:
        return len(self.active_browsers)

    def is_browser_open(self, profile_id: int) -> bool:
        return profile_id in self.active_browsers
