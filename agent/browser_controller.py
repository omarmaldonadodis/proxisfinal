# agent/browser_controller.py
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
import requests
from loguru import logger
import asyncio
import os
import time
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

        debug_port = None
        driver = None

        try:
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.config.ADSPOWER_API_KEY}'
            }

            logger.info(f"Opening browser in AdsPower for profile {profile_id}")

            # 1. Llamada a AdsPower API
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

            # 2. ESPERAR a que el navegador esté completamente listo
            await asyncio.sleep(3)  # ✅ CRÍTICO: Dar tiempo al navegador
            
            # 3. Verificar que el puerto responde
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    test_response = requests.get(
                        f"http://127.0.0.1:{debug_port}/json/version",
                        timeout=2
                    )
                    if test_response.status_code == 200:
                        logger.info(f"Browser port {debug_port} is responding")
                        break
                except:
                    if attempt < max_retries - 1:
                        logger.debug(f"Port not ready, retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(1)
                    else:
                        raise Exception(f"Browser port {debug_port} not responding after {max_retries} attempts")

            # 4. Configurar Selenium
            service = Service(self.chromedriver_path)

            chrome_options = Options()
            chrome_options.add_experimental_option(
                "debuggerAddress",
                f"127.0.0.1:{debug_port}"
            )

            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            # 5. Conectar Selenium con reintentos
            max_selenium_retries = 3
            for attempt in range(max_selenium_retries):
                try:
                    logger.info(f"Connecting Selenium (attempt {attempt + 1}/{max_selenium_retries})...")
                    driver = webdriver.Chrome(
                        service=service,
                        options=chrome_options
                    )
                    logger.info(f"Selenium connected successfully to port {debug_port}")
                    break
                except WebDriverException as e:
                    if "target window already closed" in str(e).lower():
                        logger.warning(f"Window closed error, retrying... ({attempt + 1}/{max_selenium_retries})")
                        if attempt < max_selenium_retries - 1:
                            await asyncio.sleep(2)
                            continue
                    raise

            if not driver:
                raise Exception("Failed to connect Selenium after retries")

            # 6. Guardar driver
            self.active_browsers[profile_id] = driver
            self.browser_info[profile_id] = {
                'debug_port': debug_port,
                'opened_at': asyncio.get_event_loop().time()
            }

            # 7. Preparar navegador (SOLO si la conexión fue exitosa)
            try:
                await self._prepare_browser(driver, profile_id)
            except Exception as e:
                logger.warning(f"Browser preparation failed (non-critical): {e}")

            return driver

        except Exception as e:
            logger.error(f"Failed to open browser for profile {profile_id}: {e}")
            
            # Cleanup en caso de error
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            if debug_port and profile_id:
                # Cerrar en AdsPower también
                try:
                    headers = {
                        'Authorization': f'Bearer {self.config.ADSPOWER_API_KEY}'
                    }
                    requests.get(
                        f"{self.config.ADSPOWER_API_URL}/api/v1/browser/stop",
                        params={"user_id": profile_id},
                        headers=headers,
                        timeout=5
                    )
                except:
                    pass
            
            return None

    async def _prepare_browser(self, driver: webdriver.Chrome, profile_id: int) -> bool:
        """Verifica que el navegador esté listo (SIN manipular ventanas)."""
        try:
            logger.info(f"Preparing browser for profile {profile_id}")

            # Esperar un poco
            await asyncio.sleep(1)

            # SOLO verificar que podemos obtener el título (sin cerrar nada)
            try:
                _ = driver.title
                logger.info(f"Browser ready for profile {profile_id}")
                return True
            except WebDriverException as e:
                logger.error(f"Browser not ready: {e}")
                return False

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

            # Cerrar Selenium
            try:
                driver.quit()
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Error quitting driver: {e}")

            # Cerrar en AdsPower
            try:
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
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Error closing in AdsPower: {e}")

            # Cleanup
            del self.active_browsers[profile_id]
            if profile_id in self.browser_info:
                del self.browser_info[profile_id]

            logger.info(f"Browser closed for profile {profile_id}")
            return True

        except Exception as e:
            logger.error(f"Error closing browser for profile {profile_id}: {e}")
            return False

    async def close_all_browsers(self):
        """Cierra todos los navegadores"""
        for profile_id in list(self.active_browsers.keys()):
            await self.close_browser(profile_id)

    def get_active_count(self) -> int:
        """Retorna cantidad de navegadores activos"""
        return len(self.active_browsers)

    def is_browser_open(self, profile_id: int) -> bool:
        """Verifica si un navegador está abierto"""
        return profile_id in self.active_browsers