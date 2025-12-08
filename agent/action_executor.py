# agent/action_executor.py (DEBUGGING VERSION)
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
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
    
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
        
        # Estrategia 3: Buscar todos los elementos y filtrar
        if selector_type.lower() == "xpath":
            try:
                logger.debug(f"Strategy 3: Find all elements")
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        logger.debug(f"✓ Found visible element with strategy 3")
                        return elem
            except:
                logger.debug(f"Strategy 3 failed")
        
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
        elif action_type == "debug_page":
            return await self._debug_page(driver, params)
        elif action_type in ["advanced_login", "login"]:
            # params debe incluir los campos para login
            login_executor = HumanizedLoginExecutor(self.config)
            result = await login_executor.execute_login(driver, params)
            logger.info(f"Login result: {result.to_dict()}")
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
        fallback_text = params.get("text")  # ✅ Texto alternativo para buscar
        
        if not selector:
            logger.error("No selector provided for click")
            return False
        
        # 🔍 DEBUG
        self._take_debug_screenshot(driver, "before_click")
        self._log_page_info(driver)
        
        logger.info(f"🔍 Looking for click element: {selector_type} = {selector}")
        
        # ✅ NUEVO: Si selector tiene múltiples opciones separadas por coma
        if "," in selector and selector_type.lower() == "css":
            # Probar cada selector individualmente
            selectors = [s.strip() for s in selector.split(",")]
            element = None
            
            for sel in selectors:
                # Saltar selectores inválidos como :contains()
                if ":contains(" in sel:
                    continue
                
                try:
                    logger.debug(f"Trying selector: {sel}")
                    element = self._find_element_with_strategies(driver, sel, "css", timeout=3)
                    if element:
                        logger.debug(f"✓ Found with selector: {sel}")
                        break
                except:
                    continue
        else:
            element = self._find_element_with_strategies(driver, selector, selector_type, timeout=15)
        
        # ✅ FALLBACK: Buscar por texto si selector falló
        if not element and fallback_text:
            logger.info(f"🔍 Fallback: searching by text '{fallback_text}'")
            element = self._find_element_by_text(driver, fallback_text)
        
        if not element:
            logger.error(f"❌ Element not found for click: {selector}")
            await self._debug_find_similar_elements(driver, selector, selector_type)
            self._take_debug_screenshot(driver, "click_not_found")
            return False
        
        try:
            if human:
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
            else:
                element.click()
            
            await asyncio.sleep(random.uniform(0.5, 1.5))
            logger.info(f"✓ Clicked element")
            self._take_debug_screenshot(driver, "after_click")
            return True
        
        except Exception as e:
            logger.error(f"Click failed: {e}")
            self._take_debug_screenshot(driver, "click_error")
            return False
    
    def _find_element_by_text(self, driver: webdriver.Chrome, text: str):
        """Busca elemento por su texto visible"""
        try:
            # Buscar en todos los elementos clickeables
            elements = driver.find_elements(By.TAG_NAME, "a") + \
                      driver.find_elements(By.TAG_NAME, "button")
            
            for elem in elements:
                try:
                    if elem.is_displayed() and text.lower() in elem.text.lower():
                        logger.debug(f"Found by text: '{elem.text}'")
                        return elem
                except:
                    continue
            
            return None
        except:
            return None
    
    async def _type(self, driver: webdriver.Chrome, params: Dict) -> bool:
        selector = params.get("selector")
        text = params.get("text", "")
        selector_type = params.get("selector_type") or params.get("by", "css")
        human = params.get("human", True)
        clear_first = params.get("clear", True)
        placeholder = params.get("placeholder")  # ✅ Buscar por placeholder
        
        if not selector:
            logger.error("No selector provided for type")
            return False
        
        text = self._replace_variables(text)
        
        # 🔍 DEBUG
        self._take_debug_screenshot(driver, "before_type")
        logger.info(f"🔍 Looking for type element: {selector_type} = {selector}")
        
        # ✅ Probar múltiples selectores
        element = None
        
        if "," in selector and selector_type.lower() == "css":
            selectors = [s.strip() for s in selector.split(",")]
            
            for sel in selectors:
                try:
                    logger.debug(f"Trying selector: {sel}")
                    element = self._find_element_with_strategies(driver, sel, "css", timeout=3)
                    if element:
                        logger.debug(f"✓ Found with selector: {sel}")
                        break
                except:
                    continue
        else:
            element = self._find_element_with_strategies(driver, selector, selector_type, timeout=15)
        
        # ✅ FALLBACK: Buscar por placeholder
        if not element and placeholder:
            logger.info(f"🔍 Fallback: searching by placeholder '{placeholder}'")
            element = self._find_input_by_placeholder(driver, placeholder)
        
        if not element:
            logger.error(f"❌ Element not found for type: {selector}")
            await self._debug_find_similar_elements(driver, selector, selector_type)
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
    
    def _find_input_by_placeholder(self, driver: webdriver.Chrome, placeholder: str):
        """Busca input por su placeholder"""
        try:
            inputs = driver.find_elements(By.TAG_NAME, "input") + \
                    driver.find_elements(By.TAG_NAME, "textarea")
            
            for inp in inputs:
                try:
                    ph = inp.get_attribute("placeholder")
                    if ph and placeholder.lower() in ph.lower():
                        logger.debug(f"Found by placeholder: '{ph}'")
                        return inp
                except:
                    continue
            
            return None
        except:
            return None
    
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
    
    async def _debug_page(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """Acción de debugging para inspeccionar la página"""
        
        logger.info("🔍 DEBUG PAGE INFO:")
        logger.info(f"URL: {driver.current_url}")
        logger.info(f"Title: {driver.title}")
        
        # Tomar screenshot
        self._take_debug_screenshot(driver, "debug_page")
        
        # Listar botones de login
        try:
            buttons = driver.find_elements(By.TAG_NAME, "button")
            links = driver.find_elements(By.TAG_NAME, "a")
            
            logger.info(f"Found {len(buttons)} buttons")
            logger.info(f"Found {len(links)} links")
            
            # Buscar elementos con texto "iniciar", "login", etc.
            login_keywords = ["iniciar", "ingresar", "login", "acceder", "entrar"]
            
            for link in links[:20]:  # Primeros 20 links
                try:
                    text = link.text.lower()
                    if any(keyword in text for keyword in login_keywords):
                        logger.info(f"  Login link found: '{link.text}' - HTML: {link.get_attribute('outerHTML')[:100]}")
                except:
                    pass
            
            for button in buttons[:20]:
                try:
                    text = button.text.lower()
                    if any(keyword in text for keyword in login_keywords):
                        logger.info(f"  Login button found: '{button.text}' - HTML: {button.get_attribute('outerHTML')[:100]}")
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Debug failed: {e}")
        
        return True
    
    async def _debug_find_similar_elements(self, driver: webdriver.Chrome, selector: str, selector_type: str):
        """Busca elementos similares para debugging"""
        
        logger.info("🔍 Looking for similar elements...")
        
        try:
            if selector_type.lower() == "xpath":
                # Si es XPath, intentar variaciones
                if "text()" in selector:
                    # Extraer texto buscado
                    import re
                    matches = re.findall(r"'([^']+)'", selector)
                    if matches:
                        search_text = matches[0]
                        logger.info(f"Searching for elements with text containing: '{search_text}'")
                        
                        # Buscar en links
                        links = driver.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            try:
                                if search_text.lower() in link.text.lower():
                                    logger.info(f"  Found link: '{link.text}' - {link.get_attribute('outerHTML')[:150]}")
                            except:
                                pass
            
            else:
                # Si es CSS, intentar encontrar el elemento
                logger.info(f"Trying to find CSS element: {selector}")
        
        except Exception as e:
            logger.error(f"Debug similar elements failed: {e}")