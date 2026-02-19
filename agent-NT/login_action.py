# agent/login_action.py
"""
Acción de login humanizada con detección inteligente de problemas
Se integra con ActionExecutor
"""
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from loguru import logger
import asyncio
import random
import time

# Importar detector
from login_detector import LoginDetector, LoginIssue


class LoginAction:
    """Acción de login mejorada con detección"""
    
    def __init__(self, config):
        self.config = config
        self.detector = LoginDetector()
        self.max_retries = 2  # Máximo 2 reintentos
    
    async def execute_login(
        self,
        driver: webdriver.Chrome,
        params: Dict
    ) -> Dict:
        """
        Ejecuta login con detección de problemas
        
        Params esperados:
        {
            "site": "ecuabet" | "melbet" | "custom",
            "username": "user@example.com",
            "password": "password123",
            "username_selector": "input[name='email']",  # Opcional
            "password_selector": "input[name='password']",  # Opcional
            "submit_selector": "button[type='submit']",  # Opcional
            "expected_success_url": "https://site.com/dashboard",  # Opcional
            "wait_after_submit": 5  # Segundos de espera después del submit
        }
        
        Returns:
        {
            "success": True/False,
            "issue_detected": "recaptcha" | "wrong_credentials" | None,
            "details": {...},
            "screenshot": "path/to/screenshot.png",
            "retries": 1
        }
        """
        
        site = params.get("site", "custom")
        username = params.get("username")
        password = params.get("password")
        
        if not username or not password:
            return {
                "success": False,
                "issue_detected": "missing_credentials",
                "details": {"error": "Username or password not provided"},
                "retries": 0
            }
        
        # Obtener selectores (usar predefinidos o custom)
        selectors = self._get_selectors(site, params)
        
        logger.info(f"🔐 Attempting login on: {site}")
        
        # Intentar login con reintentos
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                logger.info(f"Retry attempt {attempt}/{self.max_retries}")
                await asyncio.sleep(random.uniform(3, 5))
            
            result = await self._try_login(
                driver,
                username,
                password,
                selectors,
                params
            )
            
            # Si tuvo éxito, retornar
            if result["success"]:
                result["retries"] = attempt
                return result
            
            # Si no debe reintentar, retornar
            if not self.detector.should_retry(result.get("issue_detected", "")):
                logger.warning(f"Cannot retry: {result['issue_detected']}")
                result["retries"] = attempt
                return result
            
            logger.info(f"Retrying login... (attempt {attempt + 1})")
        
        # Máximo de reintentos alcanzado
        result["retries"] = self.max_retries
        return result
    
    async def _try_login(
        self,
        driver: webdriver.Chrome,
        username: str,
        password: str,
        selectors: Dict,
        params: Dict
    ) -> Dict:
        """Intenta login una vez"""
        
        try:
            # 1. Esperar y localizar campo de usuario
            logger.debug(f"Looking for username field: {selectors['username']}")
            
            try:
                username_field = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selectors["username"]))
                )
            except TimeoutException:
                return {
                    "success": False,
                    "issue_detected": "timeout",
                    "details": {"error": "Username field not found", "selector": selectors["username"]},
                    "screenshot": self.detector._take_screenshot(driver, "username_not_found")
                }
            
            # 2. Click y focus en campo de usuario (humanizado)
            await self._humanized_click_and_focus(driver, username_field)
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
            # 3. Limpiar campo
            username_field.clear()
            await asyncio.sleep(0.2)
            
            # 4. Escribir usuario (tipeo humanizado)
            await self._humanized_typing(username_field, username)
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # 5. Esperar y localizar campo de contraseña
            logger.debug(f"Looking for password field: {selectors['password']}")
            
            try:
                password_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selectors["password"]))
                )
            except TimeoutException:
                return {
                    "success": False,
                    "issue_detected": "timeout",
                    "details": {"error": "Password field not found", "selector": selectors["password"]},
                    "screenshot": self.detector._take_screenshot(driver, "password_not_found")
                }
            
            # 6. Click y focus en campo de contraseña
            await self._humanized_click_and_focus(driver, password_field)
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
            # 7. Limpiar campo
            password_field.clear()
            await asyncio.sleep(0.2)
            
            # 8. Escribir contraseña (tipeo humanizado)
            await self._humanized_typing(password_field, password)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # 9. Submit (botón o Enter)
            submit_success = await self._submit_login(driver, selectors.get("submit"), password_field)
            
            if not submit_success:
                return {
                    "success": False,
                    "issue_detected": "submit_failed",
                    "details": {"error": "Could not submit login form"},
                    "screenshot": self.detector._take_screenshot(driver, "submit_failed")
                }
            
            # 10. Esperar respuesta del servidor
            wait_time = params.get("wait_after_submit", 5)
            await asyncio.sleep(wait_time)
            
            # 11. DETECTAR PROBLEMAS
            detection_result = await self.detector.detect_login_issues(
                driver,
                expected_success_url=params.get("expected_success_url")
            )
            
            # 12. Construir respuesta
            if detection_result["issue_type"] == LoginIssue.SUCCESS:
                return {
                    "success": True,
                    "issue_detected": None,
                    "details": detection_result["details"],
                    "screenshot": detection_result.get("screenshot")
                }
            else:
                return {
                    "success": False,
                    "issue_detected": detection_result["issue_type"],
                    "details": detection_result["details"],
                    "screenshot": detection_result.get("screenshot")
                }
        
        except Exception as e:
            logger.error(f"Login execution error: {e}")
            return {
                "success": False,
                "issue_detected": "execution_error",
                "details": {"error": str(e)},
                "screenshot": self.detector._take_screenshot(driver, "execution_error")
            }
    
    async def _humanized_click_and_focus(self, driver: webdriver.Chrome, element):
        """Click y focus humanizado"""
        try:
            # Scroll hacia el elemento
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            await asyncio.sleep(random.uniform(0.3, 0.6))
            
            # Focus con JavaScript
            driver.execute_script("arguments[0].focus();", element)
            await asyncio.sleep(0.2)
            
            # Click con JavaScript (más confiable)
            driver.execute_script("arguments[0].click();", element)
            
        except Exception as e:
            logger.warning(f"Humanized click error: {e}")
            # Fallback: click normal
            element.click()
    
    async def _humanized_typing(self, element, text: str):
        """Tipeo humanizado con delays aleatorios"""
        for char in text:
            element.send_keys(char)
            # Delay aleatorio entre caracteres (50-150ms)
            await asyncio.sleep(random.uniform(0.05, 0.15))
    
    async def _submit_login(
        self,
        driver: webdriver.Chrome,
        submit_selector: Optional[str],
        password_field
    ) -> bool:
        """Submit del formulario (botón o Enter)"""
        
        try:
            # Método 1: Botón de submit
            if submit_selector:
                try:
                    submit_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, submit_selector))
                    )
                    
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        submit_button
                    )
                    await asyncio.sleep(0.5)
                    
                    # Click humanizado
                    driver.execute_script("arguments[0].click();", submit_button)
                    logger.debug("✓ Submit button clicked")
                    return True
                    
                except TimeoutException:
                    logger.warning("Submit button not found, trying Enter key")
            
            # Método 2: Enter key en campo de contraseña
            from selenium.webdriver.common.keys import Keys
            password_field.send_keys(Keys.ENTER)
            logger.debug("✓ Enter key pressed")
            return True
            
        except Exception as e:
            logger.error(f"Submit error: {e}")
            return False
    
    def _get_selectors(self, site: str, params: Dict) -> Dict:
        """Obtiene selectores según el sitio"""
        
        # Si vienen selectores custom, usarlos
        if params.get("username_selector"):
            return {
                "username": params["username_selector"],
                "password": params["password_selector"],
                "submit": params.get("submit_selector")
            }
        
        # Selectores predefinidos por sitio (casas de apuestas ecuatorianas)
        SITE_SELECTORS = {
            "ecuabet": {
                "username": "input[name='email'], input[type='email'], #email",
                "password": "input[name='password'], input[type='password'], #password",
                "submit": "button[type='submit'], .login-btn, .submit-btn"
            },
            "melbet": {
                "username": "input[name='login'], #login",
                "password": "input[name='password'], #password",
                "submit": "button[type='submit'], .login-btn"
            },
            "betprolive": {
                "username": "input[placeholder*='Usuario'], input[placeholder*='Correo'], input[type='email']",
                "password": "input[type='password']",
                "submit": "button[type='submit'], .login-button, .btn-login"
            },
            "1xbet": {
                "username": "input[name='login'], #login",
                "password": "input[name='password'], #password",
                "submit": "button.auth_login_btn, button[type='submit']"
            },
            "novibet": {
                "username": "input[name='email'], input[type='email']",
                "password": "input[type='password']",
                "submit": "button[type='submit'], .login-submit"
            },
            "sorti": {
                "username": "input[name='username'], input[type='email']",
                "password": "input[type='password']",
                "submit": "button[type='submit'], .login-button"
            },
            "sportbet": {
                "username": "input[name='email'], input[type='email']",
                "password": "input[type='password']",
                "submit": "button[type='submit']"
            },
            "doradobet": {
                "username": "input[name='email'], input[type='email']",
                "password": "input[type='password']",
                "submit": "button[type='submit'], .btn-login"
            },
            "turbobet": {
                "username": "input[name='username'], input[type='email']",
                "password": "input[type='password']",
                "submit": "button[type='submit']"
            },
            # Selector genérico para sitios no listados
            "generic": {
                "username": "input[type='email'], input[name='email'], input[name='username'], input[name='user'], input[placeholder*='Email'], input[placeholder*='Usuario'], input[placeholder*='Correo']",
                "password": "input[type='password'], input[name='password'], input[placeholder*='Contraseña']",
                "submit": "button[type='submit'], .login-button, .submit-button, .btn-login, input[type='submit']"
            }
        }
        
        return SITE_SELECTORS.get(site, SITE_SELECTORS["generic"])