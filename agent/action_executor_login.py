from typing import Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from loguru import logger
import asyncio
import random
import time


class LoginResult:
    """Resultado de intento de login"""
    
    def __init__(
        self,
        success: bool,
        message: str,
        error_type: Optional[str] = None,
        needs_captcha: bool = False,
        needs_2fa: bool = False,
        blocked: bool = False
    ):
        self.success = success
        self.message = message
        self.error_type = error_type
        self.needs_captcha = needs_captcha
        self.needs_2fa = needs_2fa
        self.blocked = blocked
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "message": self.message,
            "error_type": self.error_type,
            "needs_captcha": self.needs_captcha,
            "needs_2fa": self.needs_2fa,
            "blocked": self.blocked
        }


class HumanizedLoginExecutor:
    """Ejecutor de login humanizado con detección de problemas"""
    
    # Detectores de errores de autenticación
    AUTH_ERROR_INDICATORS = [
        "wrong password",
        "incorrect password",
        "invalid credentials",
        "contraseña incorrecta",
        "credenciales inválidas",
        "usuario o contraseña incorrectos",
        "wrong username",
        "user not found",
        "usuario no encontrado"
    ]
    
    # Detectores de bloqueo
    BLOCKED_INDICATORS = [
        "account locked",
        "account suspended",
        "too many attempts",
        "temporarily blocked",
        "cuenta bloqueada",
        "cuenta suspendida",
        "demasiados intentos",
        "bloqueado temporalmente"
    ]
    
    # Detectores de 2FA
    TWO_FA_INDICATORS = [
        "verification code",
        "two-factor",
        "2fa",
        "código de verificación",
        "autenticación de dos factores",
        "enter code",
        "6-digit code"
    ]
    
    def __init__(self, config: Dict = {}):
        self.config = config
    
    async def execute_login(
        self,
        driver: webdriver.Chrome,
        params: Dict[str, Any]
    ) -> LoginResult:
        """
        Ejecuta login humanizado con detección completa
        """
        
        service = params.get("service", "generic")
        username = params.get("username")
        password = params.get("password")
        
        if not username or not password:
            return LoginResult(
                success=False,
                message="Username or password not provided",
                error_type="missing_credentials"
            )
        
        logger.info(f"🔐 Starting login for service: {service}")
        
        try:
            # 1. Detectar reCAPTCHA visible antes de empezar
            if not params.get("ignore_recaptcha", False) and self._detect_recaptcha(driver):
                logger.warning("⚠️ reCAPTCHA detected before login")
                return LoginResult(
                    success=False,
                    message="reCAPTCHA detected on page",
                    error_type="recaptcha",
                    needs_captcha=True
                )
            logger.info(f"✓ Paso 1 completado")

            # 2. Esperar estabilidad de la página
            await self._wait_for_page_stability(driver)
            logger.info(f"✓ Paso 2 completado")

            
            # 3. ✅ MEJORADO: Esperar a que los campos del modal estén visibles
            username_selector = params.get(
                "username_selector",
                "input[placeholder*='Correo'], input[type='text'], input[name='email']"
            )
            password_selector = params.get(
                "password_selector",
                "input[type='password'], input[placeholder*='Contrasena']"
            )
            submit_selector = params.get(
                "submit_selector",
                "button:contains('Acceder'), button.btn-success, button[type='submit']"
            )
            
            # ✅ MEJORADO: Usar método más robusto para esperar elemento
            username_element = await self._wait_for_element_robust(driver, username_selector, timeout=15)
            if not username_element:
                return LoginResult(False, "Username field not found", "username_field_not_found")
            
            logger.info(f"✓ Paso 3 completado - Username field found")

            # 4. Llenar username
            username_filled = await self._fill_field_robust(driver, username_element, username)
            if not username_filled:
                return LoginResult(False, "Could not fill username field", "username_fill_failed")
            
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
            logger.info(f"✓ Paso 4 completado - Username filled")

            # 5. Llenar password
            password_element = await self._wait_for_element_robust(driver, password_selector, timeout=10)
            if not password_element:
                return LoginResult(False, "Password field not found", "password_field_not_found")
            
            password_filled = await self._fill_field_robust(driver, password_element, password)
            if not password_filled:
                return LoginResult(False, "Could not fill password field", "password_fill_failed")
            
            await asyncio.sleep(random.uniform(1.0, 2.0))
            logger.info(f"✓ Paso 5 completado - Password filled")

            # 6. Detectar CAPTCHA visible después de llenar campos
            if not params.get("ignore_recaptcha", False) and self._detect_recaptcha(driver):
                logger.warning("⚠️ reCAPTCHA detected after filling fields")
                return LoginResult(
                    success=False,
                    message="reCAPTCHA detected after filling fields",
                    error_type="recaptcha",
                    needs_captcha=True
                )
            
            logger.info(f"✓ Paso 6 completado - No CAPTCHA detected")

            # 7. Hacer click en submit
            submit_clicked = await self._click_submit_robust(driver, submit_selector)
            if not submit_clicked:
                return LoginResult(False, "Could not click submit button", "submit_button_not_found")
            
            logger.info(f"✓ Paso 7 completado - Submit clicked")
            
            # 8. Esperar resultado
            wait_after = params.get("wait_after_submit", 5)
            await asyncio.sleep(wait_after)
            
            # 9. Verificar login exitoso
            success_url = params.get("success_url_contains")
            success_element_selector = params.get("success_element")
            
            if success_url and success_url.lower() in driver.current_url.lower():
                return LoginResult(True, "Login successful")
            
            if success_element_selector:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, success_element_selector))
                    )
                    return LoginResult(True, "Login successful")
                except TimeoutException:
                    pass
            
            # 10. Revisar errores de login
            page_text = driver.page_source.lower()
            if any(e in page_text for e in self.AUTH_ERROR_INDICATORS):
                return LoginResult(False, "Authentication failed", "auth_error")
            
            if any(b in page_text for b in self.BLOCKED_INDICATORS):
                return LoginResult(False, "Account blocked", "blocked", blocked=True)
            
            if any(f in page_text for f in self.TWO_FA_INDICATORS):
                return LoginResult(False, "2FA required", "2fa", needs_2fa=True)
            
            # 11. Si nada funcionó
            return LoginResult(False, "Login failed for unknown reason", "unknown")
        
        except Exception as e:
            logger.error(f"Login execution error: {e}")
            return LoginResult(False, str(e), "exception")
    
    # -----------------------------
    # ✅ MÉTODOS MEJORADOS
    # -----------------------------
    
    async def _wait_for_element_robust(
        self,
        driver: webdriver.Chrome,
        selector: str,
        timeout: int = 15
    ):
        """✅ MEJORADO: Espera elemento con múltiples estrategias"""
        
        selectors = [s.strip() for s in selector.split(",")]
        
        # Estrategia 1: CSS Selectors con espera explícita
        for sel in selectors:
            try:
                logger.debug(f"Trying CSS selector: {sel}")
                element = WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                )
                if element and element.is_displayed():
                    logger.debug(f"✓ Found with CSS: {sel}")
                    return element
            except TimeoutException:
                logger.debug(f"✗ CSS selector failed: {sel}")
                continue
            except Exception as e:
                logger.debug(f"✗ CSS selector error: {e}")
                continue
        
        # Estrategia 2: JavaScript querySelector
        for sel in selectors:
            try:
                logger.debug(f"Trying JavaScript querySelector: {sel}")
                element = driver.execute_script(f"""
                    return document.querySelector('{sel}');
                """)
                if element:
                    # Verificar visibilidad
                    is_visible = driver.execute_script("""
                        var elem = arguments[0];
                        var rect = elem.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    """, element)
                    
                    if is_visible:
                        logger.debug(f"✓ Found with JS: {sel}")
                        return element
            except Exception as e:
                logger.debug(f"✗ JavaScript selector error: {e}")
                continue
        
        # Estrategia 3: Búsqueda por atributos comunes
        common_attrs = [
            ("id", "loginUsername"),
            ("id", "username"),
            ("id", "email"),
            ("name", "email"),
            ("name", "username"),
            ("placeholder", "correo"),
            ("placeholder", "email"),
            ("type", "email"),
        ]
        
        for attr, value in common_attrs:
            try:
                logger.debug(f"Trying attribute: {attr}='{value}'")
                elements = driver.find_elements(By.CSS_SELECTOR, f"input[{attr}*='{value}' i]")
                for elem in elements:
                    if elem.is_displayed():
                        logger.debug(f"✓ Found with attribute search: {attr}={value}")
                        return elem
            except Exception as e:
                logger.debug(f"✗ Attribute search error: {e}")
                continue
        
        logger.error(f"❌ Element not found after all strategies: {selector}")
        return None
    
    async def _fill_field_robust(self, driver: webdriver.Chrome, element, text: str) -> bool:
        """✅ MEJORADO: Llena campo con múltiples estrategias"""
        
        try:
            # Estrategia 1: Scroll y focus
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            await asyncio.sleep(0.5)
            
            # Estrategia 2: Click con JavaScript
            driver.execute_script("arguments[0].focus(); arguments[0].click();", element)
            await asyncio.sleep(0.3)
            
            # Estrategia 3: Limpiar campo (múltiples métodos)
            try:
                element.clear()
            except:
                driver.execute_script("arguments[0].value = '';", element)
            
            await asyncio.sleep(0.2)
            
            # Estrategia 4: Tipeo humanizado
            for char in text:
                element.send_keys(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Verificar que se escribió
            current_value = driver.execute_script("return arguments[0].value;", element)
            if current_value == text:
                logger.debug(f"✓ Field filled successfully")
                return True
            else:
                logger.warning(f"⚠️ Value mismatch: expected '{text}', got '{current_value}'")
                return False
        
        except Exception as e:
            logger.error(f"Fill field error: {e}")
            return False
    
    async def _click_submit_robust(self, driver: webdriver.Chrome, selector: str) -> bool:
        """✅ MEJORADO: Click en submit con múltiples estrategias"""
        
        element = await self._wait_for_element_robust(driver, selector, timeout=10)
        if not element:
            logger.error("Submit button not found")
            return False
        
        try:
            # Scroll hacia el botón
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
            await asyncio.sleep(0.5)
            
            # Click con JavaScript (más confiable)
            driver.execute_script("arguments[0].click();", element)
            logger.debug("✓ Submit button clicked")
            await asyncio.sleep(random.uniform(0.5, 1.0))
            return True
        
        except Exception as e:
            logger.error(f"Submit click error: {e}")
            return False
    
    def _detect_recaptcha(self, driver: webdriver.Chrome) -> bool:
        """Detecta si hay un reCAPTCHA visible en la página"""
        try:
            # Iframes de reCAPTCHA visibles
            recaptcha_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            for iframe in recaptcha_iframes:
                if iframe.is_displayed():
                    return True
            # Checkbox visible
            checkboxes = driver.find_elements(By.CSS_SELECTOR, ".g-recaptcha, .recaptcha-checkbox, .recaptcha")
            for box in checkboxes:
                if box.is_displayed():
                    return True
            return False
        except Exception:
            return False
    
    async def _wait_for_page_stability(self, driver: webdriver.Chrome, timeout: int = 3):
        await asyncio.sleep(random.uniform(timeout, timeout + 2))