# agent/browser_controller.py
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
from loguru import logger
import asyncio

class BrowserController:
    """Controlador de navegadores AdsPower"""
    
    def __init__(self, config):
        self.config = config
        self.active_browsers: Dict[int, webdriver.Chrome] = {}  # profile_id -> driver
        self.browser_info: Dict[int, Dict] = {}  # profile_id -> info
    
    async def open_browser(self, profile_id: int) -> Optional[webdriver.Chrome]:
        """Abre navegador de AdsPower para un profile"""
        
        # Si ya está abierto, retornar
        if profile_id in self.active_browsers:
            logger.info(f"Browser already open for profile {profile_id}")
            return self.active_browsers[profile_id]
        
        try:
            # Headers para API de AdsPower
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.config.ADSPOWER_API_KEY}'
            }
            
            # Abrir navegador en AdsPower
            logger.info(f"Opening browser in AdsPower for profile {profile_id}")
            
            response = requests.get(
                f"{self.config.ADSPOWER_API_URL}/api/v1/browser/start",
                params={"user_id": profile_id},
                headers=headers,
                timeout=self.config.BROWSER_OPEN_TIMEOUT
            )
            
            if response.status_code != 200:
                raise Exception(f"AdsPower API error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            if result.get('code') != 0:
                raise Exception(f"AdsPower error: {result.get('msg')}")
            
            data = result.get('data', {})
            debug_port = data.get('debug_port')
            
            if not debug_port:
                raise Exception("No debug_port in AdsPower response")
            
            logger.info(f"Browser opened on port {debug_port}")
            
            # Conectar Selenium al navegador
            chrome_options = Options()
            chrome_options.add_experimental_option(
                "debuggerAddress", 
                f"127.0.0.1:{debug_port}"
            )
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            # Guardar driver
            self.active_browsers[profile_id] = driver
            self.browser_info[profile_id] = {
                'debug_port': debug_port,
                'ws_endpoint': data.get('ws', {}).get('selenium'),
                'opened_at': asyncio.get_event_loop().time()
            }
            
            logger.info(f"Selenium connected to browser for profile {profile_id}")
            
            # Preparar navegador (cerrar tabs extras, navegar a página inicial)
            await self._prepare_browser(driver, profile_id)
            
            return driver
        
        except Exception as e:
            logger.error(f"Failed to open browser for profile {profile_id}: {e}")
            return None
    
    async def _prepare_browser(self, driver: webdriver.Chrome, profile_id: int) -> bool:
        """Prepara navegador (limpia tabs, navega a inicio)"""
        
        try:
            logger.info(f"Preparing browser for profile {profile_id}")
            
            # Obtener handles
            all_handles = driver.window_handles
            
            # Cerrar DevTools si está abierto
            for handle in list(all_handles):
                try:
                    driver.switch_to.window(handle)
                    await asyncio.sleep(0.2)
                    current_url = driver.current_url
                    if "devtools://" in current_url:
                        driver.close()
                        await asyncio.sleep(0.3)
                except:
                    pass
            
            # Actualizar handles
            await asyncio.sleep(0.5)
            all_handles = driver.window_handles
            
            # Si no hay handles, crear uno
            if not all_handles:
                driver.execute_script("window.open('about:blank');")
                await asyncio.sleep(1)
                all_handles = driver.window_handles
            
            # Mantener solo un tab
            if len(all_handles) > 1:
                keep_handle = all_handles[0]
                for handle in all_handles[1:]:
                    try:
                        driver.switch_to.window(handle)
                        await asyncio.sleep(0.1)
                        driver.close()
                        await asyncio.sleep(0.2)
                    except:
                        pass
                
                await asyncio.sleep(0.5)
                driver.switch_to.window(keep_handle)
            
            # Navegar a página en blanco
            driver.get("about:blank")
            await asyncio.sleep(1)
            
            logger.info(f"Browser prepared for profile {profile_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error preparing browser for profile {profile_id}: {e}")
            return False
    
    async def close_browser(self, profile_id: int) -> bool:
        """Cierra navegador"""
        
        if profile_id not in self.active_browsers:
            logger.warning(f"Browser not open for profile {profile_id}")
            return False
        
        try:
            driver = self.active_browsers[profile_id]
            
            # Cerrar Selenium
            try:
                driver.quit()
            except:
                pass
            
            # Cerrar en AdsPower
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.config.ADSPOWER_API_KEY}'
            }
            
            response = requests.get(
                f"{self.config.ADSPOWER_API_URL}/api/v1/browser/stop",
                params={"user_id": profile_id},
                headers=headers,
                timeout=10
            )
            
            # Limpiar
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
        profile_ids = list(self.active_browsers.keys())
        
        for profile_id in profile_ids:
            await self.close_browser(profile_id)
    
    def get_active_count(self) -> int:
        """Retorna cantidad de navegadores activos"""
        return len(self.active_browsers)
    
    def is_browser_open(self, profile_id: int) -> bool:
        """Verifica si navegador está abierto"""
        return profile_id in self.active_browsers