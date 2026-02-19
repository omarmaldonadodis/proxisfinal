
# agent/action_executor_login.py - DETECCIÓN MEJORADA
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
    """Ejecutor de login con detección ESTRICTA"""
    
    AUTH_ERROR_INDICATORS = [
        "wrong password", "incorrect password", "invalid credentials",
        "contraseña incorrecta", "credenciales inválidas", 
        "usuario o contraseña incorrectos", "invalid login",
        "authentication failed", "login failed",
        "usuario (login) no existe",  
        "usuario no existe",          
        "correo no existe",         
        "email no existe",           
        "user not found",           
        "cuenta no encontrada",      
        "datos incorrectos",         
        "acceso denegado",            
        "email o contraseña incorrectos", 
        "usuario o clave incorrectos",    
    ]
    
    BLOCKED_INDICATORS = [
        "account locked", "account suspended", "too many attempts",
        "cuenta bloqueada", "demasiados intentos"
    ]
    
    TWO_FA_INDICATORS = [
        "verification code", "two-factor", "2fa",
        "código de verificación"
    ]
    
    # ✅ NUEVO: Indicadores de éxito más estrictos
    SUCCESS_INDICATORS = [
        "dashboard", "bienvenido", "welcome", "logout", "cerrar sesión",
        "mi cuenta", "my account", "perfil", "profile"
    ]
    
    def __init__(self, config: Dict = {}):
        self.config = config
    
    async def execute_login(
        self,
        driver: webdriver.Chrome,
        params: Dict[str, Any]
    ) -> LoginResult:
        """Ejecuta login con validación ESTRICTA"""
        
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
            # 1. Verificar reCAPTCHA
            if not params.get("ignore_recaptcha", False) and self._detect_recaptcha(driver):
                return LoginResult(False, "reCAPTCHA detected", "recaptcha", needs_captcha=True)
            
            # 2. Esperar estabilidad
            await self._wait_for_page_stability(driver)
            
            # 3. Detectar tipo de formulario
            is_angular = await self._detect_angular_modal(driver)
            logger.info(f"✓ Form type: {'Angular modal' if is_angular else 'Standard HTML'}")
            
            # 4. Obtener selectores
            username_selector = params.get("username_selector", "input[type='text'], input[type='email']")
            password_selector = params.get("password_selector", "input[type='password']")
            
            # 5. Llenar username
            if is_angular:
                username_filled = await self._fill_angular_field(driver, username_selector, username)
            else:
                username_element = await self._wait_for_element_robust(driver, username_selector)
                username_filled = await self._fill_field_robust(driver, username_element, username) if username_element else False
            
            if not username_filled:
                return LoginResult(False, "Could not fill username", "username_fill_failed")
            
            logger.info(f"✓ Username filled")
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
            # 6. Llenar password
            if is_angular:
                password_filled = await self._fill_angular_field(driver, password_selector, password)
            else:
                password_element = await self._wait_for_element_robust(driver, password_selector)
                password_filled = await self._fill_field_robust(driver, password_element, password) if password_element else False
            
            if not password_filled:
                return LoginResult(False, "Could not fill password", "password_fill_failed")
            
            logger.info(f"✓ Password filled")
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # 7. Validar formulario Angular
            if is_angular:
                await self._trigger_angular_validation(driver)
            
            # 8. Verificar CAPTCHA después de llenar
            if not params.get("ignore_recaptcha", False) and self._detect_recaptcha(driver):
                return LoginResult(False, "reCAPTCHA after fill", "recaptcha", needs_captcha=True)
            
            # 9. Submit
            submit_selector = params.get("submit_selector")
            submit_clicked = await self._click_angular_submit(driver, submit_selector)
            
            # ✅ Fallback: ENTER en password
            if not submit_clicked:
                try:
                    pw_list = driver.find_elements(By.CSS_SELECTOR, password_selector)
                    for pw in pw_list:
                        if pw.is_displayed() and pw.is_enabled():
                            pw.send_keys(Keys.ENTER)
                            logger.info("✓ ENTER sent to password field")
                            submit_clicked = True
                            break
                except Exception as e:
                    logger.warning(f"Could not send ENTER: {e}")
            
            if not submit_clicked:
                return LoginResult(False, "Could not click submit", "submit_failed")
            
            logger.info(f"✓ Submit clicked")
            
            # 10. ✅ ESPERA CRÍTICA: dar tiempo al servidor
            wait_time = params.get("wait_after_submit", 10)
            logger.info(f"⏳ Waiting {wait_time}s for server response...")
            await asyncio.sleep(wait_time)
            
            # 11. ✅ VALIDACIÓN ESTRICTA
            return await self._validate_login_result(
                driver,
                params.get("success_url_contains")
            )
        
        except Exception as e:
            logger.error(f"Login execution error: {e}")
            return LoginResult(False, str(e), "exception")
    
    async def _validate_login_result(
        self,
        driver: webdriver.Chrome,
        expected_url: Optional[str]
    ) -> LoginResult:
        """
        ✅ VALIDACIÓN ESTRICTA - ORDEN CORRECTO
        
        1. Errores de credenciales → FAIL (PRIMERO)
        2. Cuenta bloqueada → FAIL
        3. URL cambió → SUCCESS
        4. Elementos de sesión → SUCCESS
        5. Modal abierto → FAIL
        6. Por defecto → FAIL
        """
        
        try:
            current_url = driver.current_url
            page_text = driver.page_source.lower()  # ✅ Cambiar a page_source
            
            logger.info(f"🔍 Validating login result...")
            logger.debug(f"  Current URL: {current_url}")
            
            # ✅ 1. VERIFICAR ERRORES PRIMERO (máxima prioridad)
            for error_pattern in self.AUTH_ERROR_INDICATORS:
                if error_pattern in page_text:
                    logger.error(f"❌ Auth error detected: '{error_pattern}'")
                    return LoginResult(
                        False,
                        f"Wrong credentials: '{error_pattern}' found",
                        "auth_error"
                    )
            
            # ✅ 2. VERIFICAR CUENTA BLOQUEADA
            for block_pattern in self.BLOCKED_INDICATORS:
                if block_pattern in page_text:
                    logger.error(f"❌ Account blocked: '{block_pattern}'")
                    return LoginResult(
                        False,
                        "Account blocked",
                        "blocked",
                        blocked=True
                    )
            
            # ✅ 3. VERIFICAR CAMBIO DE URL (indica éxito)
            if expected_url and expected_url.lower() in current_url:
                logger.info(f"✅ Login success: URL matches '{expected_url}'")
                return LoginResult(True, "Login successful (URL redirect)")
            
            # ✅ 4. VERIFICAR ELEMENTOS DE SESIÓN ACTIVA
            success_detected = False
            
            for success_pattern in self.SUCCESS_INDICATORS:
                if success_pattern in page_text:
                    logger.info(f"✅ Login success: '{success_pattern}' found in page")
                    success_detected = True
                    break
            
            if success_detected:
                return LoginResult(True, "Login successful (session indicators)")
            
            # ✅ 5. VERIFICAR COOKIES DE SESIÓN
            cookies = driver.get_cookies()
            session_cookies = [
                c for c in cookies
                if any(keyword in c["name"].lower() for keyword in ["session", "token", "auth", "user"])
            ]
            
            if session_cookies and len(session_cookies) > 0:
                logger.info(f"✅ Login success: {len(session_cookies)} session cookies found")
                return LoginResult(True, f"Login successful ({len(session_cookies)} session cookies)")
            
            # ✅ 6. VERIFICAR SI MODAL SIGUE ABIERTO
            modal_still_open = driver.execute_script("""
                const modal = document.querySelector('.modal.show, [role="dialog"]');
                return modal !== null && window.getComputedStyle(modal).display !== 'none';
            """)
            
            if modal_still_open:
                logger.error("❌ Modal still open - assuming failure")
                return LoginResult(
                    False,
                    "Login modal still open - no redirect occurred",
                    "no_redirect"
                )
            
            # ✅ 7. POR DEFECTO → FALLO
            logger.error("❌ No success indicators found")
            return LoginResult(
                False,
                "Login validation failed - no success indicators detected",
                "validation_failed"
            )
        
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return LoginResult(False, f"Validation error: {str(e)}", "validation_error")
    async def _detect_angular_modal(self, driver: webdriver.Chrome) -> bool:
        """Detecta si hay un modal Angular activo"""
        try:
            angular_indicators = driver.execute_script("""
                    return document.querySelector('[ng-version]') !== null ||
                        document.querySelector('[_nghost]') !== null ||
                        document.querySelector('[_ngcontent]') !== null ||
                        typeof window.ng !== 'undefined';
                """)
            return angular_indicators
        except:
            return False
    
    async def _fill_angular_field(self, driver: webdriver.Chrome, selector: str, value: str) -> bool:
        """Llena campo Angular disparando eventos correctos"""
        try:
            script = """
            const selector = arguments[0];
            const value = arguments[1];
            
            function isReallyVisible(elem) {
                if (!elem) return false;
                const style = window.getComputedStyle(elem);
                const rect = elem.getBoundingClientRect();
                return (
                    style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    style.opacity !== '0' &&
                    rect.width > 0 &&
                    rect.height > 0 &&
                    elem.offsetParent !== null
                );
            }
            
            const allFields = document.querySelectorAll(selector);
            let field = null;
            
            for (let f of allFields) {
                if (isReallyVisible(f)) {
                    field = f;
                    break;
                }
            }
            
            if (!field) return false;
            
            field.scrollIntoView({ behavior: 'smooth', block: 'center' });
            field.focus();
            field.value = '';
            
            field.dispatchEvent(new Event('focus', { bubbles: true }));
            field.dispatchEvent(new Event('click', { bubbles: true }));
            
            for (let i = 0; i < value.length; i++) {
                field.value = value.substring(0, i + 1);
                field.dispatchEvent(new Event('input', { bubbles: true }));
                field.dispatchEvent(new Event('keydown', { bubbles: true }));
                field.dispatchEvent(new Event('keyup', { bubbles: true }));
                field.dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            field.dispatchEvent(new Event('blur', { bubbles: true }));
            
            return field.value === value;
            """
            
            success = driver.execute_script(script, selector, value)
            
            if success:
                await asyncio.sleep(random.uniform(0.3, 0.7))
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Angular field fill error: {e}")
            return False
    
    async def _trigger_angular_validation(self, driver: webdriver.Chrome):
        """Dispara validación de formulario Angular"""
        try:
            driver.execute_script("""
                const inputs = document.querySelectorAll('input');
                inputs.forEach(input => {
                    input.dispatchEvent(new Event('blur', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                });
                
                if (typeof window.ng !== 'undefined') {
                    const components = window.ng.probe(document.body);
                    if (components && components.injector) {
                        const appRef = components.injector.get(window.ng.coreTokens.ApplicationRef);
                        appRef.tick();
                    }
                }
            """)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning(f"Angular validation trigger error: {e}")
    
    async def _click_angular_submit(self, driver: webdriver.Chrome, selector: str) -> bool:
        """Click en botón submit Angular"""
        try:
            script = """
            const selector = arguments[0];
            
            function isReallyVisible(elem) {
                if (!elem) return false;
                const style = window.getComputedStyle(elem);
                const rect = elem.getBoundingClientRect();
                return (
                    style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    style.opacity !== '0' &&
                    rect.width > 0 &&
                    rect.height > 0 &&
                    elem.offsetParent !== null
                );
            }
            
            let allButtons = selector ? 
                Array.from(document.querySelectorAll(selector)) : 
                Array.from(document.querySelectorAll('button'));
            
            let button = null;
            
            for (let btn of allButtons) {
                if (isReallyVisible(btn)) {
                    const text = btn.textContent.toLowerCase();
                    if (text.includes('ingresar') || 
                        text.includes('login') || 
                        text.includes('acceder') ||
                        btn.type === 'submit') {
                        button = btn;
                        break;
                    }
                }
            }
            
            if (!button) return false;
            
            button.scrollIntoView({ behavior: 'smooth', block: 'center' });
            button.disabled = false;
            button.removeAttribute('disabled');
            button.classList.remove('disabled');
            button.style.pointerEvents = 'auto';
            button.style.cursor = 'pointer';
            
            button.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
            button.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            button.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            button.click();
            
            let form = null;
            const modal = button.closest('div, section, app-root, body');
            
            if (modal) {
                form = modal.querySelector('form');
            }
            
            if (form) {
                form.dispatchEvent(new Event('submit', { bubbles: true }));
                form.submit();
            }
            
            return true;
            """
            
            success = driver.execute_script(script, selector)
            
            if success:
                logger.info("✓ Submit button clicked")
                await asyncio.sleep(1.0)
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Submit click error: {e}")
            return False
    
    async def _wait_for_element_robust(self, driver: webdriver.Chrome, selector: str, timeout: int = 15):
        """Espera elemento con múltiples selectores"""
        selectors = [s.strip() for s in selector.split(",")]
        
        for sel in selectors:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                if element and element.is_displayed():
                    return element
            except:
                continue
        
        return None
    
    async def _fill_field_robust(self, driver: webdriver.Chrome, element, text: str) -> bool:
        """Llena campo estándar"""
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            await asyncio.sleep(0.3)
            
            element.clear()
            await asyncio.sleep(0.2)
            
            for char in text:
                element.send_keys(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
            
            return True
        except:
            return False
    
    def _detect_recaptcha(self, driver: webdriver.Chrome) -> bool:
        """Detecta reCAPTCHA visible"""
        try:
            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            for iframe in iframes:
                if iframe.is_displayed() and iframe.size['width'] > 0:
                    return True
            return False
        except:
            return False
    
    async def _wait_for_page_stability(self, driver: webdriver.Chrome, timeout: int = 3):
        """Espera estabilidad de página"""
        await asyncio.sleep(random.uniform(timeout, timeout + 2))