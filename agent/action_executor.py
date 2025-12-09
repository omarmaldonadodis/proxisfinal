# agent/action_executor.py - FIXED VERSION
from typing import Dict, Optional, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    WebDriverException,
    NoSuchWindowException,
    TimeoutException,
)
from loguru import logger
import asyncio
import random
import time
import os

# ✅ IMPORTAR LOGIN ACTION
from action_executor_login import HumanizedLoginExecutor


class HumanBehavior:
    @staticmethod
    def typing_speed() -> float:
        return random.uniform(0.05, 0.15)
    
    @staticmethod
    def scroll_amount() -> int:
        return random.randint(100, 400)


class ActionExecutor:
    """Ejecutor de acciones con debugging"""
    
    def __init__(self, config):
        self.config = config
        self.behavior = HumanBehavior()
        self.session_vars = {}
        
        # Crear directorio de screenshots
        os.makedirs("screenshots", exist_ok=True)
    
    def set_session_var(self, key: str, value: str):
        self.session_vars[key] = value
        logger.debug(f"Session var set: {key}")
    
    def _replace_variables(self, text: str) -> str:
        for key, value in self.session_vars.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        return text
    
    def _is_browser_alive(self, driver: webdriver.Chrome) -> bool:
        try:
            _ = driver.title
            return True
        except (NoSuchWindowException, WebDriverException):
            return False
    
    def _take_debug_screenshot(self, driver: webdriver.Chrome, name: str):
        """Toma screenshot para debugging"""
        try:
            timestamp = int(time.time())
            filename = f"screenshots/debug_{name}_{timestamp}.png"
            driver.save_screenshot(filename)
            logger.info(f"📸 Screenshot saved: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    def _log_page_info(self, driver: webdriver.Chrome):
        """Log información de la página actual"""
        try:
            logger.debug(f"Current URL: {driver.current_url}")
            logger.debug(f"Page title: {driver.title}")
        except:
            pass
    
    def _find_element_with_strategies(
        self,
        driver: webdriver.Chrome,
        selector: str,
        selector_type: str,
        timeout: int = 15
    ):
        """Busca elemento con múltiples estrategias"""
        
        # Estrategia 1: Selector original
        try:
            if selector_type.lower() == "xpath":
                by = By.XPATH
            else:
                by = By.CSS_SELECTOR
            
            logger.debug(f"Strategy 1: Looking for {by} = {selector}")
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            logger.debug(f"✓ Found with strategy 1")
            return element
        except TimeoutException:
            logger.debug(f"Strategy 1 failed")
        
        # Estrategia 2: JavaScript query (para CSS)
        if selector_type.lower() != "xpath":
            try:
                logger.debug(f"Strategy 2: JavaScript querySelector")
                element = driver.execute_script(f"return document.querySelector('{selector}');")
                if element:
                    logger.debug(f"✓ Found with strategy 2")
                    return element
            except:
                logger.debug(f"Strategy 2 failed")
        
        return None
    
    async def execute_action(
        self,
        driver: webdriver.Chrome,
        action: Dict[str, Any]
    ) -> bool:
        action_type = action.get("type")
        params = action.get("params", {})
        
        logger.debug(f"Executing action: {action_type}")
        
        if not self._is_browser_alive(driver):
            logger.error(f"Browser is closed")
            return False
        
        try:
            timeout = 60 if action_type in ["advanced_login", "login"] else params.get("timeout", 30)
            
            try:
                result = await asyncio.wait_for(
                    self._execute_action_internal(driver, action_type, params),
                    timeout=timeout
                )
                return result
            except asyncio.TimeoutError:
                logger.error(f"Action timeout ({timeout}s): {action_type}")
                self._take_debug_screenshot(driver, f"timeout_{action_type}")
                return False
        
        except Exception as e:
            logger.error(f"Action failed ({action_type}): {e}")
            self._take_debug_screenshot(driver, f"error_{action_type}")
            return False
    
    async def _execute_action_internal(
        self,
        driver: webdriver.Chrome,
        action_type: str,
        params: Dict[str, Any]
    ) -> bool:
        
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
        elif action_type == "search_google":
            return await self._search_google(driver, params)
        elif action_type == "screenshot":
            return await self._screenshot(driver, params)
        # ✅ AGREGAR ADVANCED_LOGIN
        elif action_type in ["advanced_login", "login"]:
            login_executor = HumanizedLoginExecutor(self.config)
            result = await login_executor.execute_login(driver, params)
            logger.info(f"Login result: success={result.success}, message={result.message}")
            return result.success
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return False
    
    async def _navigate(self, driver: webdriver.Chrome, params: Dict) -> bool:
        url = params.get("url")
        if not url:
            return False
        
        if not url.startswith("http"):
            url = f"https://{url}"
        
        try:
            driver.get(url)
            await asyncio.sleep(random.uniform(2, 4))
            self._log_page_info(driver)
            logger.info(f"✓ Navigated to: {url}")
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def _click(self, driver: webdriver.Chrome, params: Dict) -> bool:
        selector = params.get("selector")
        selector_type = params.get("selector_type") or params.get("by", "css")
        human = params.get("human", True)
        fallback_text = params.get("text")
        
        if not selector:
            logger.error("No selector provided for click")
            return False
        
        self._take_debug_screenshot(driver, "before_click")
        self._log_page_info(driver)
        
        logger.info(f"🔍 Looking for click element: {selector_type} = {selector}")
        
        # ✅ ESTRATEGIA MEJORADA: Buscar con JavaScript y verificar visibilidad
        element = None
        
        try:
            # Esperar a que el elemento exista
            if selector_type.lower() == "xpath":
                by = By.XPATH
            else:
                by = By.CSS_SELECTOR
            
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((by, selector))
            )
            
            # ✅ VERIFICAR SI ES VISIBLE Y CLICKEABLE
            is_visible = driver.execute_script("""
                var elem = arguments[0];
                var rect = elem.getBoundingClientRect();
                var style = window.getComputedStyle(elem);
                return (
                    style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    style.opacity !== '0' &&
                    rect.width > 0 &&
                    rect.height > 0
                );
            """, element)
            
            if not is_visible:
                logger.warning(f"Element found but not visible, trying to make it visible...")
                
                # ✅ INTENTAR HACER VISIBLE EL ELEMENTO
                driver.execute_script("""
                    var elem = arguments[0];
                    elem.style.display = 'block';
                    elem.style.visibility = 'visible';
                    elem.style.opacity = '1';
                """, element)
                
                await asyncio.sleep(1)
        
        except TimeoutException:
            logger.error(f"❌ Element not found: {selector}")
            return False
        
        if not element:
            logger.error(f"❌ Element not found for click: {selector}")
            self._take_debug_screenshot(driver, "click_not_found")
            return False
        
        try:
            # ✅ MÉTODO 1: Scroll y click con ActionChains
            if human:
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        element
                    )
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    actions = ActionChains(driver)
                    actions.move_to_element(element)
                    actions.pause(random.uniform(0.2, 0.5))
                    actions.click()
                    actions.perform()
                    
                    logger.info(f"✓ Clicked element (ActionChains)")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    self._take_debug_screenshot(driver, "after_click")
                    return True
                
                except Exception as e:
                    logger.warning(f"ActionChains failed: {e}, trying JavaScript click...")
            
            # ✅ MÉTODO 2: Click con JavaScript (FALLBACK)
            driver.execute_script("arguments[0].click();", element)
            logger.info(f"✓ Clicked element (JavaScript)")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            self._take_debug_screenshot(driver, "after_click")
            return True
        
        except Exception as e:
            logger.error(f"Click failed: {e}")
            self._take_debug_screenshot(driver, "click_error")
            return False
    
    async def _type(self, driver: webdriver.Chrome, params: Dict) -> bool:
        selector = params.get("selector")
        text = params.get("text", "")
        selector_type = params.get("selector_type") or params.get("by", "css")
        human = params.get("human", True)
        clear_first = params.get("clear", True)
        
        if not selector:
            logger.error("No selector provided for type")
            return False
        
        text = self._replace_variables(text)
        
        self._take_debug_screenshot(driver, "before_type")
        logger.info(f"🔍 Looking for type element: {selector_type} = {selector}")
        
        element = self._find_element_with_strategies(driver, selector, selector_type, timeout=15)
        
        if not element:
            logger.error(f"❌ Element not found for type: {selector}")
            self._take_debug_screenshot(driver, "type_not_found")
            return False
        
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            await asyncio.sleep(0.5)
            
            if clear_first:
                element.clear()
                await asyncio.sleep(0.3)
            
            element.click()
            await asyncio.sleep(0.3)
            
            if human:
                for char in text:
                    element.send_keys(char)
                    await asyncio.sleep(self.behavior.typing_speed())
            else:
                element.send_keys(text)
            
            await asyncio.sleep(random.uniform(0.3, 0.7))
            logger.info(f"✓ Typed text")
            return True
        
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return False
    
    async def _scroll(self, driver: webdriver.Chrome, params: Dict) -> bool:
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
            logger.debug(f"✓ Scrolled {direction} {amount}px")
            return True
        
        except Exception as e:
            logger.error(f"Scroll failed: {e}")
            return False
    
    async def _wait(self, driver: webdriver.Chrome, params: Dict) -> bool:
        duration = params.get("duration", 1)
        await asyncio.sleep(duration)
        logger.debug(f"✓ Waited {duration}s")
        return True
    
    async def _search_google(self, driver: webdriver.Chrome, params: Dict) -> bool:
        query = params.get("query", "")
        if not query:
            return False

        try:
            await asyncio.sleep(2)
            
            current_url = driver.current_url.lower()
            if "google" not in current_url:
                driver.get("https://www.google.com")
                await asyncio.sleep(3)
            
            search_box = None
            search_selectors = [
                "textarea[name='q']",
                "input[name='q']",
            ]
            
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if search_box:
                        break
                except:
                    continue
            
            if not search_box:
                return False
            
            driver.execute_script("arguments[0].focus(); arguments[0].click();", search_box)
            await asyncio.sleep(0.5)
            
            driver.execute_script("arguments[0].value = '';", search_box)
            await asyncio.sleep(0.3)
            
            for char in query:
                search_box.send_keys(char)
                await asyncio.sleep(self.behavior.typing_speed())
            
            await asyncio.sleep(random.uniform(0.5, 1.0))
            search_box.send_keys(Keys.ENTER)
            await asyncio.sleep(random.uniform(3, 5))
            
            logger.info(f"✅ Google search completed")
            return True

        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return False
    
    async def _screenshot(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """✅ ACCIÓN DE SCREENSHOT"""
        name = params.get("name", "screenshot")
        filename = self._take_debug_screenshot(driver, name)
        return filename is not None