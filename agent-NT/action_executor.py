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
        elif action_type == "wait_element":
            return await self._wait_element(driver, params)
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return False
    
    async def _navigate(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """
        ✅ NAVEGACIÓN MEJORADA - No se bloquea en SPAs
        """
        url = params.get("url")
        timeout = params.get("timeout", 45)  # ← Aumentado de 40 a 45

        if not url:
            logger.error("No URL provided")
            return False

        if not url.startswith("http"):
            url = f"https://{url}"

        try:
            logger.info(f"🌐 Navigating to: {url}")
            
            # Configurar timeouts más largos
            driver.set_page_load_timeout(timeout)
            driver.set_script_timeout(30)
            
            # ============================================
            # MÉTODO 1: Navegación normal con timeout
            # ============================================
            try:
                driver.get(url)
                logger.debug("Navigation completed (full load)")
            
            except Exception as e:
                # Si falla por timeout, intentar stop
                error_msg = str(e).lower()
                
                if "timeout" in error_msg or "timed out" in error_msg:
                    logger.warning("Page load timeout, trying to stop loading...")
                    
                    try:
                        # Detener carga de página
                        driver.execute_script("window.stop();")
                        await asyncio.sleep(1)
                        logger.debug("Page loading stopped")
                    except:
                        pass
                else:
                    # Si no es timeout, es un error real
                    raise

            # ============================================
            # PASO 2: Esperar a que haya contenido básico
            # ============================================
            try:
                # Esperar solo a que el BODY esté presente
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                logger.debug("✓ Body element found")
            except TimeoutException:
                logger.warning("Body not found in 15s, continuing anyway...")

            # ============================================
            # PASO 3: Esperar carga de JavaScript (para SPAs)
            # ============================================
            try:
                # Esperar a que Angular/React termine de cargar
                await asyncio.sleep(2)  # Espera base
                
                # Verificar si Angular está cargando
                is_loading = driver.execute_script("""
                    // Verificar Angular
                    if (typeof window.getAllAngularTestabilities !== 'undefined') {
                        const testabilities = window.getAllAngularTestabilities();
                        return testabilities.some(t => t.isStable() === false);
                    }
                    
                    // Verificar React
                    if (typeof window.React !== 'undefined') {
                        return false; // React no tiene API de "isLoading"
                    }
                    
                    return false;
                """)
                
                if is_loading:
                    logger.debug("Angular still loading, waiting...")
                    await asyncio.sleep(3)
            
            except Exception as e:
                logger.debug(f"SPA check warning: {e}")

            # ============================================
            # PASO 4: Verificar que estamos en la página correcta
            # ============================================
            try:
                current_url = driver.current_url
                page_title = driver.title
                
                logger.info(f"✅ Navigation complete")
                logger.debug(f"  Current URL: {current_url}")
                logger.debug(f"  Page title: {page_title}")
                
                # Verificar que no estamos en about:blank
                if current_url == "about:blank":
                    logger.error("Navigation failed - still on about:blank")
                    return False
                
                # Verificar que la URL contiene el dominio esperado
                from urllib.parse import urlparse
                expected_domain = urlparse(url).netloc
                current_domain = urlparse(current_url).netloc
                
                if expected_domain not in current_domain:
                    logger.warning(f"Domain mismatch: expected {expected_domain}, got {current_domain}")
            
            except Exception as e:
                logger.warning(f"URL verification warning: {e}")

            # ============================================
            # PASO 5: Espera humanizada final
            # ============================================
            await asyncio.sleep(random.uniform(2, 4))
            
            return True

        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            self._take_debug_screenshot(driver, "navigate_error")
            return False
        
    async def _click(self, driver: webdriver.Chrome, params: Dict) -> bool:
        """
        ✅ CLICK seguro para Angular Material / CDK Overlay / Modales
        Compatible con AdsPower
        """
        selector = params.get("selector")
        selector_type = params.get("selector_type", "css")
        text = params.get("text")
        human = params.get("human", True)

        if not selector and not text:
            logger.error("❌ No selector or text provided")
            return False

        logger.info(f"🔍 Looking for (modal-safe): {selector_type}={selector}")

        overlays = []

        # 1. Buscar overlays activos (Angular CDK)
        try:
            overlays = driver.find_elements(By.CSS_SELECTOR, ".cdk-overlay-pane")
        except:
            overlays = []

        search_contexts = overlays[::-1] if overlays else [driver]

        element = None

        # 2. Buscar dentro de overlays primero
        for ctx in search_contexts:
            try:
                if selector:
                    if selector_type.lower() == "xpath":
                        element = ctx.find_element(By.XPATH, selector)
                    else:
                        element = ctx.find_element(By.CSS_SELECTOR, selector)
                elif text:
                    element = driver.execute_script("""
                        const root = arguments[0] === document ? document : arguments[0];
                        const candidates = root.querySelectorAll('button, a, div, span');
                        const txt = arguments[1];
                        return [...candidates].find(el => 
                            el.innerText && el.innerText.trim().includes(txt)
                        );
                    """, ctx if ctx != driver else driver.execute_script("return document"), text)

                if element:
                    logger.debug("✅ Element found inside overlay")
                    break
            except:
                continue

        if not element:
            logger.error(f"❌ Element not found in overlay: {selector or text}")
            self._take_debug_screenshot(driver, "element_not_found")
            return False

        # 3. Esperar a que sea realmente clickeable
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(element)
            )
        except:
            pass

        # 4. Scroll centrado
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                element
            )
            await asyncio.sleep(0.3)
        except:
            pass

        # 5. CLICK SEGURO (sin coordenadas reales)
        try:
            logger.debug("✅ Executing safe click (no coordinate math)...")

            driver.execute_script("""
                const ev = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                arguments[0].dispatchEvent(ev);
            """, element)

            logger.info("✅ Modal-safe click successful")

            if human:
                await asyncio.sleep(random.uniform(0.4, 1.0))
            else:
                await asyncio.sleep(0.2)

            self._take_debug_screenshot(driver, "after_click")
            return True

        except Exception as e:
            logger.error(f"❌ Modal-safe click failed: {e}")
            self._take_debug_screenshot(driver, "click_failed")
            return False

    async def _wait_element(self, driver: webdriver.Chrome, params: Dict) -> bool:
        selector = params.get("selector")
        timeout = params.get("timeout", 20)

        if not selector:
            return False

        logger.info(f"⏳ Waiting VISIBLE element: {selector}")

        try:
            end = time.time() + timeout

            while time.time() < end:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)

                for el in elements:
                    try:
                        is_displayed = el.is_displayed()
                        rect = driver.execute_script("""
                            const r = arguments[0].getBoundingClientRect();
                            return {w: r.width, h: r.height};
                        """, el)

                        if is_displayed and rect["w"] > 5 and rect["h"] > 5:
                            logger.info("✅ Real visible element found")
                            return True
                    except:
                        continue

                await asyncio.sleep(0.5)

            raise Exception("Timeout waiting visible element")

        except Exception as e:
            logger.error(f"wait_element failed: {e}")
            self._take_debug_screenshot(driver, "wait_element_failed")
            return False

                  
    async def _type(self, driver: webdriver.Chrome, params: Dict) -> bool:
        selector = params.get("selector")
        text = params.get("text", "")
        human = params.get("human", True)
        clear_first = params.get("clear", True)
        
        if not selector:
            logger.error("No selector provided for type")
            return False

        text = self._replace_variables(text)
        self._take_debug_screenshot(driver, "before_type")
        logger.info(f"🔍 Looking for type element: css = {selector}")

        try:
            # Buscar input REAL dentro del overlay
            element = driver.execute_script("""
                const sel = arguments[0];
                const overlays = document.querySelectorAll('.cdk-overlay-pane');
                for (const overlay of overlays) {
                    const el = overlay.querySelector(sel);
                    if (el && el.offsetParent !== null) return el;
                }
                // fallback al body
                const el = document.querySelector(sel);
                return (el && el.offsetParent !== null) ? el : null;
            """, selector)
        except Exception as e:
            logger.error(f"JS query failed: {e}")
            return False

        if not element:
            logger.error("❌ No visible input found")
            self._take_debug_screenshot(driver, "type_not_found")
            return False

        try:
            # Forzar foco real
            driver.execute_script("""
                arguments[0].scrollIntoView({behavior:'auto', block:'center'});
                arguments[0].removeAttribute('disabled');
                arguments[0].focus();
            """, element)
            await asyncio.sleep(0.5)

            if clear_first:
                try:
                    element.clear()
                    await asyncio.sleep(0.3)
                except:
                    # input oculto, usar JS
                    driver.execute_script("arguments[0].value = '';", element)
                    await asyncio.sleep(0.3)

            # Enviar texto
            if human:
                for char in text:
                    element.send_keys(char)
                    await asyncio.sleep(self.behavior.typing_speed())
            else:
                element.send_keys(text)

            await asyncio.sleep(random.uniform(0.3, 0.7))
            logger.info("✓ Typed text successfully")
            return True

        except Exception as e:
            logger.error(f"Type failed: {e}")
            self._take_debug_screenshot(driver, "type_failed")
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