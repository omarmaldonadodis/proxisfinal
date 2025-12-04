# agent/action_executor.py
from typing import Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchWindowException,
    TimeoutException,
    StaleElementReferenceException
)
from loguru import logger
import asyncio
import random
import time

class HumanBehavior:
    """Comportamiento humano para acciones"""
    
    @staticmethod
    def random_delay(min_ms: int = 100, max_ms: int = 300):
        """Delay aleatorio en milisegundos"""
        time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))
    
    @staticmethod
    def typing_speed() -> float:
        """Velocidad de tipeo aleatoria"""
        return random.uniform(0.05, 0.15)
    
    @staticmethod
    def mouse_movement_speed() -> float:
        """Velocidad de movimiento de mouse"""
        return random.uniform(0.5, 1.5)
    
    @staticmethod
    def scroll_amount() -> int:
        """Cantidad de scroll aleatorio"""
        return random.randint(100, 400)

class ActionExecutor:
    """Ejecutor de acciones en navegadores"""
    
    def __init__(self, config):
        self.config = config
        self.behavior = HumanBehavior()
    
    def _is_browser_alive(self, driver: webdriver.Chrome) -> bool:
        """Verifica si el navegador sigue activo"""
        try:
            # Intentar obtener el título de la ventana
            _ = driver.title
            return True
        except (NoSuchWindowException, WebDriverException):
            return False
    
    def _safe_driver_call(self, func, *args, **kwargs):
        """Ejecuta una llamada al driver de forma segura"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except StaleElementReferenceException:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                raise
            except (NoSuchWindowException, WebDriverException) as e:
                if "target window already closed" in str(e).lower():
                    raise
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    continue
                raise
    
    async def execute_action(
        self,
        driver: webdriver.Chrome,
        action: Dict[str, Any]
    ) -> bool:
        """Ejecuta una acción en el navegador"""
        
        action_type = action.get("type")
        params = action.get("params", {})
        
        logger.debug(f"Executing action: {action_type}")
        
        # ✅ VERIFICAR QUE EL NAVEGADOR ESTÉ VIVO ANTES DE EJECUTAR
        if not self._is_browser_alive(driver):
            logger.error(f"Browser is closed, cannot execute action: {action_type}")
            return False
        
        try:
            # Ejecutar según tipo
            if action_type == "navigate":
                return await self._navigate(driver, params)
            
            elif action_type == "click":
                return await self._click(driver, params)
            
            elif action_type == "type":
                return await self._type(driver, params)
            
            elif action_type == "scroll":
                return await self._scroll(driver, params)
            
            elif action_type == "wait":
                return await self._wait(driver, params)
            
            elif action_type == "wait_element":
                return await self._wait_element(driver, params)
            
            elif action_type == "hover":
                return await self._hover(driver, params)
            
            elif action_type == "select":
                return await self._select(driver, params)
            
            elif action_type == "press_key":
                return await self._press_key(driver, params)
            
            elif action_type == "screenshot":
                return await self._screenshot(driver, params)
            
            elif action_type == "switch_tab":
                return await self._switch_tab(driver, params)
            
            elif action_type == "close_tab":
                return await self._close_tab(driver, params)
            
            elif action_type == "execute_script":
                return await self._execute_script(driver, params)
            
            elif action_type == "random_mouse":
                return await self._random_mouse_movement(driver, params)
            
            elif action_type == "human_typing":
                return await self._human_typing(driver, params)
            
            elif action_type == "search_google":
                return await self._search_google(driver, params)
            
            elif action_type == "login":
                return await self._login(driver, params)
            
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return False
        
        except (NoSuchWindowException, WebDriverException) as e:
            if "target window already closed" in str(e).lower():
                logger.error(f"Browser closed during action ({action_type}): {e}")
                return False
            logger.error(f"Action failed ({action_type}): {e}")
            return False
        
        except Exception as e:
            logger.error(f"Action failed ({action_type}): {e}")
            return False
    
    async def _navigate(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Navega a una URL"""
        url = params.get("url")
        if not url:
            return False
        
        if not url.startswith("http"):
            url = f"https://{url}"
        
        try:
            self._safe_driver_call(driver.get, url)
            await asyncio.sleep(random.uniform(2, 4))
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def _click(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Hace click en un elemento"""
        selector = params.get("selector")
        by_type = params.get("by", "css")
        human = params.get("human", True)
        
        if not selector:
            return False
        
        try:
            # Obtener tipo de selector
            by = By.CSS_SELECTOR if by_type == "css" else By.XPATH
            
            # Encontrar elemento
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((by, selector))
            )
            
            if human:
                # Scroll al elemento
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    element
                )
                await asyncio.sleep(random.uniform(0.5, 1.0))
                
                # Mover mouse al elemento
                actions = ActionChains(driver)
                actions.move_to_element(element)
                actions.pause(random.uniform(0.2, 0.5))
                actions.click()
                actions.perform()
            else:
                element.click()
            
            await asyncio.sleep(random.uniform(0.5, 1.5))
            return True
        
        except TimeoutException:
            logger.warning(f"Element not found: {selector}")
            return False
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False
    
    async def _type(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Escribe texto en un elemento"""
        selector = params.get("selector")
        text = params.get("text", "")
        by_type = params.get("by", "css")
        human = params.get("human", True)
        clear_first = params.get("clear", True)
        
        if not selector:
            return False
        
        try:
            by = By.CSS_SELECTOR if by_type == "css" else By.XPATH
            
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((by, selector))
            )
            
            # Limpiar campo si es necesario
            if clear_first:
                element.clear()
                await asyncio.sleep(0.3)
            
            # Click en el elemento
            element.click()
            await asyncio.sleep(0.3)
            
            if human:
                # Tipeo humanizado
                for char in text:
                    element.send_keys(char)
                    await asyncio.sleep(self.behavior.typing_speed())
            else:
                element.send_keys(text)
            
            await asyncio.sleep(random.uniform(0.3, 0.7))
            return True
        
        except TimeoutException:
            logger.warning(f"Element not found: {selector}")
            return False
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return False
    
    async def _scroll(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Hace scroll"""
        direction = params.get("direction", "down")
        amount = params.get("amount", self.behavior.scroll_amount())
        smooth = params.get("smooth", True)
        
        try:
            if smooth:
                if direction == "down":
                    driver.execute_script(f"window.scrollBy({{top: {amount}, behavior: 'smooth'}});")
                else:
                    driver.execute_script(f"window.scrollBy({{top: -{amount}, behavior: 'smooth'}});")
            else:
                if direction == "down":
                    driver.execute_script(f"window.scrollBy(0, {amount});")
                else:
                    driver.execute_script(f"window.scrollBy(0, -{amount});")
            
            await asyncio.sleep(random.uniform(1, 2))
            return True
        
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False
    
    async def _wait(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Espera un tiempo"""
        duration = params.get("duration", 1)
        await asyncio.sleep(duration)
        return True
    
    async def _wait_element(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Espera a que aparezca un elemento"""
        selector = params.get("selector")
        by_type = params.get("by", "css")
        timeout = params.get("timeout", 10)
        
        if not selector:
            return False
        
        try:
            by = By.CSS_SELECTOR if by_type == "css" else By.XPATH
            
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return True
        
        except TimeoutException:
            logger.warning(f"Element not found within {timeout}s: {selector}")
            return False
        except Exception as e:
            logger.error(f"Wait element failed: {e}")
            return False
    
    async def _search_google(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Búsqueda completa en Google (Mobile & Desktop)"""
        query = params.get("query", "")
        if not query:
            return False

        try:
            # Esperar input de búsqueda
            search_box = None
            search_selectors = [
                "input[name='q'][type='text']",
                "input[aria-label='Buscar']",
                "input[aria-label='Search']",
                "textarea.gLFyf",
                "input.gLFyf"
            ]
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue

            if not search_box:
                logger.error("Search box not found")
                return False

            # Scroll al input
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                search_box
            )
            await asyncio.sleep(0.5)

            # Click y limpiar
            search_box.click()
            await asyncio.sleep(0.3)
            search_box.clear()
            await asyncio.sleep(0.3)

            # Tipeo humanizado
            for char in query:
                search_box.send_keys(char)
                await asyncio.sleep(self.behavior.typing_speed())

            search_box.send_keys(Keys.ENTER)
            await asyncio.sleep(random.uniform(3, 5))

            logger.info("✓ Google search completed")
            return True

        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return False

    # Métodos auxiliares simplificados
    async def _hover(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Hover sobre elemento"""
        try:
            selector = params.get("selector")
            if not selector:
                return False
            
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            
            ActionChains(driver).move_to_element(element).perform()
            await asyncio.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Hover failed: {e}")
            return False
    
    async def _select(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Select en dropdown"""
        try:
            selector = params.get("selector")
            value = params.get("value")
            if not selector or not value:
                return False
            
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            
            select = Select(element)
            select.select_by_value(value)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Select failed: {e}")
            return False
    
    async def _press_key(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Presiona tecla"""
        try:
            key = params.get("key", "ENTER")
            key_obj = getattr(Keys, key.upper(), Keys.ENTER)
            
            ActionChains(driver).send_keys(key_obj).perform()
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Press key failed: {e}")
            return False
    
    async def _screenshot(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Toma screenshot"""
        try:
            filename = params.get("filename", f"screenshot_{int(time.time())}.png")
            driver.save_screenshot(filename)
            return True
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return False
    
    async def _switch_tab(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Cambia de pestaña"""
        try:
            index = params.get("index", 0)
            handles = driver.window_handles
            if index < len(handles):
                driver.switch_to.window(handles[index])
                await asyncio.sleep(0.5)
                return True
            return False
        except Exception as e:
            logger.error(f"Switch tab failed: {e}")
            return False
    
    async def _close_tab(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Cierra pestaña"""
        try:
            driver.close()
            handles = driver.window_handles
            if handles:
                driver.switch_to.window(handles[0])
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Close tab failed: {e}")
            return False
    
    async def _execute_script(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Ejecuta JavaScript"""
        try:
            script = params.get("script")
            if not script:
                return False
            driver.execute_script(script)
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Execute script failed: {e}")
            return False
    
    async def _random_mouse_movement(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Movimiento aleatorio de mouse"""
        try:
            movements = params.get("movements", 3)
            actions = ActionChains(driver)
            
            for _ in range(movements):
                x = random.randint(-200, 200)
                y = random.randint(-200, 200)
                actions.move_by_offset(x, y)
                actions.pause(random.uniform(0.5, 1.5))
            
            actions.perform()
            return True
        except Exception as e:
            logger.error(f"Random mouse failed: {e}")
            return False
    
    async def _human_typing(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Tipeo humanizado con errores"""
        return await self._type(driver, {**params, "human": True})
    
    async def _login(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Login genérico"""
        logger.warning("Login action not fully implemented")
        return False