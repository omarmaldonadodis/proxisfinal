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
    """Ejecutor de login humanizado con soporte especial para Angular"""
    
    AUTH_ERROR_INDICATORS = [
        "wrong password", "incorrect password", "invalid credentials",
        "contraseña incorrecta", "credenciales inválidas", 
        "usuario o contraseña incorrectos"
    ]
    
    BLOCKED_INDICATORS = [
        "account locked", "account suspended", "too many attempts",
        "cuenta bloqueada", "demasiados intentos"
    ]
    
    TWO_FA_INDICATORS = [
        "verification code", "two-factor", "2fa",
        "código de verificación"
    ]
    
    def __init__(self, config: Dict = {}):
        self.config = config
    
    async def execute_login(
        self,
        driver: webdriver.Chrome,
        params: Dict[str, Any]
    ) -> LoginResult:
        """Ejecuta login con soporte especial para Angular"""
        
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
            logger.info(f"✓ Paso 1 completado")

            # 2. Esperar estabilidad
            await self._wait_for_page_stability(driver)
            logger.info(f"✓ Paso 2 completado")

            # 3. Detectar si es modal Angular
            is_angular = await self._detect_angular_modal(driver)
            logger.info(f"✓ Modal Angular cargado" if is_angular else "✓ Formulario HTML estándar")
            
            # 4. Obtener selectores
            username_selector = params.get("username_selector", "input[type='text'], input[type='email']")
            password_selector = params.get("password_selector", "input[type='password']")
            
            # 5. Llenar campos con método Angular
            if is_angular:
                username_filled = await self._fill_angular_field(driver, username_selector, username)
            else:
                username_element = await self._wait_for_element_robust(driver, username_selector)
                username_filled = await self._fill_field_robust(driver, username_element, username) if username_element else False
            
            if not username_filled:
                return LoginResult(False, "Could not fill username", "username_fill_failed")
            
            logger.info(f"✓ Paso 3 completado - Username field found")
            await asyncio.sleep(random.uniform(0.8, 1.5))
            logger.info(f"✓ Paso 4 completado - Username filled")
            
            # 6. Llenar password
            if is_angular:
                password_filled = await self._fill_angular_field(driver, password_selector, password)
            else:
                password_element = await self._wait_for_element_robust(driver, password_selector)
                password_filled = await self._fill_field_robust(driver, password_element, password) if password_element else False
            
            if not password_filled:
                return LoginResult(False, "Could not fill password", "password_fill_failed")
            
            logger.info(f"✓ Paso 5 completado - Password filled")
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # 7. Verificar Angular form validity
            if is_angular:
                await self._trigger_angular_validation(driver)
                logger.info(f"✓ Formulario validado por Angular")
            
            # 8. Verificar CAPTCHA después de llenar
            if not params.get("ignore_recaptcha", False) and self._detect_recaptcha(driver):
                return LoginResult(False, "reCAPTCHA after fill", "recaptcha", needs_captcha=True)
            logger.info(f"✓ Paso 6 completado - No CAPTCHA detected")
            
            # 9. Submit
            submit_selector = params.get("submit_selector")
            submit_clicked = await self._click_angular_submit(driver, submit_selector)
            try:
                pw_list = driver.find_elements(By.CSS_SELECTOR, params.get("password_selector"))
                for pw in pw_list:
                    if pw.is_displayed() and pw.is_enabled():
                        pw.send_keys(Keys.ENTER)
                        logger.info("✅ ENTER enviado al campo password (Angular fallback)")
                        break
            except Exception as e:
                logger.warning(f"No se pudo enviar ENTER: {e}")

            
            if not submit_clicked:
                return LoginResult(False, "Could not click submit", "submit_failed")
            
            logger.info(f"✓ Paso 7 completado - Submit clicked")
            
            # 10. Esperar resultado
            await asyncio.sleep(params.get("wait_after_submit", 5))
            
            # 11. Verificar éxito
            success_url = params.get("success_url_contains")
            if success_url and success_url.lower() in driver.current_url.lower():
                return LoginResult(True, "Login successful")
            
            # 12. Verificar errores
            page_text = driver.page_source.lower()
            if any(e in page_text for e in self.AUTH_ERROR_INDICATORS):
                return LoginResult(False, "Wrong credentials", "auth_error")
            
            if any(b in page_text for b in self.BLOCKED_INDICATORS):
                return LoginResult(False, "Account blocked", "blocked", blocked=True)
            
            # Si llegamos aquí, asumimos éxito (no hubo errores)
            return LoginResult(True, "Login completed (no errors detected)")
        
        except Exception as e:
            logger.error(f"Login execution error: {e}")
            return LoginResult(False, str(e), "exception")
    
    async def _detect_angular_modal(self, driver: webdriver.Chrome) -> bool:
        """Detecta si hay un modal Angular activo"""
        try:
            # Buscar atributos Angular comunes
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
        """Llena campo Angular disparando eventos correctos - SOLO MODAL VISIBLE"""
        try:
            logger.debug(f"Filling Angular field: {selector}")
            
            # Script que busca el campo VISIBLE y lo llena
            script = """
            const selector = arguments[0];
            const value = arguments[1];
            
            // Función para verificar si un elemento es REALMENTE visible
            function isReallyVisible(elem) {
                if (!elem) return false;
                
                const style = window.getComputedStyle(elem);
                const rect = elem.getBoundingClientRect();
                
                // Verificar que esté visible
                return (
                    style.display !== 'none' &&
                    style.visibility !== 'hidden' &&
                    style.opacity !== '0' &&
                    rect.width > 0 &&
                    rect.height > 0 &&
                    elem.offsetParent !== null
                );
            }
            
            // Buscar TODOS los campos que coincidan
            const allFields = document.querySelectorAll(selector);
            console.log('Found ' + allFields.length + ' fields matching selector');
            
            // Filtrar solo los VISIBLES
            let field = null;
            for (let f of allFields) {
                if (isReallyVisible(f)) {
                    field = f;
                    console.log('Found VISIBLE field:', f);
                    break;
                }
            }
            
            if (!field) {
                console.error('No VISIBLE field found for:', selector);
                return false;
            }
            
            // Verificar que el modal padre esté visible
            const modal = field.closest('.modal, [role="dialog"], .zg-modal');
            if (modal && !isReallyVisible(modal)) {
                console.error('Field found but modal is not visible');
                return false;
            }
            
            // Scroll al campo
            field.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Focus
            field.focus();
            
            // Limpiar
            field.value = '';
            
            // Disparar eventos Angular
            field.dispatchEvent(new Event('focus', { bubbles: true }));
            field.dispatchEvent(new Event('click', { bubbles: true }));
            
            // Establecer valor carácter por carácter (simular tipeo)
            for (let i = 0; i < value.length; i++) {
                field.value = value.substring(0, i + 1);
                
                // Disparar eventos de input
                field.dispatchEvent(new Event('input', { bubbles: true }));
                field.dispatchEvent(new Event('keydown', { bubbles: true }));
                field.dispatchEvent(new Event('keyup', { bubbles: true }));
                field.dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            // Disparar blur para validación Angular
            field.dispatchEvent(new Event('blur', { bubbles: true }));
            
            // Verificar que el valor se estableció
            console.log('Field value after fill:', field.value);
            console.log('Field is visible:', isReallyVisible(field));
            
            return field.value === value;
            """
            
            # Ejecutar script
            success = driver.execute_script(script, selector, value)
            
            if success:
                logger.info(f"✅ Field filled successfully: '{value}'")
                await asyncio.sleep(random.uniform(0.3, 0.7))
                return True
            else:
                logger.error(f"❌ Failed to fill field: {selector}")
                return False
        
        except Exception as e:
            logger.error(f"Angular field fill error: {e}")
            return False
    
    async def _trigger_angular_validation(self, driver: webdriver.Chrome):
        """Dispara validación de formulario Angular"""
        try:
            driver.execute_script("""
                // Disparar validación en todos los campos del formulario
                const inputs = document.querySelectorAll('input');
                inputs.forEach(input => {
                    input.dispatchEvent(new Event('blur', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                });
                
                // Forzar detección de cambios Angular
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
        """Click en botón submit Angular - SOLO BOTÓN VISIBLE"""
        try:
            logger.debug(f"Looking for submit button: {selector}")
            
            # Script mejorado que busca el botón VISIBLE
            script = """
            const selector = arguments[0];
            
            // Función para verificar visibilidad real
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
            
            // Buscar todos los botones que coincidan
            let allButtons = [];
            
            if (selector) {
                allButtons = Array.from(document.querySelectorAll(selector));
            }
            
            // Si no se encontró, buscar por texto
            if (allButtons.length === 0) {
                allButtons = Array.from(document.querySelectorAll('button'));
            }
            
            console.log('Total buttons found:', allButtons.length);
            
            // Filtrar solo los VISIBLES
            let button = null;
            for (let btn of allButtons) {
                if (isReallyVisible(btn)) {
                    const text = btn.textContent.toLowerCase();
                    if (text.includes('ingresar') || 
                        text.includes('login') || 
                        text.includes('acceder') ||
                        btn.type === 'submit') {
                        button = btn;
                        console.log('Found VISIBLE submit button:', btn);
                        break;
                    }
                }
            }
            
            if (!button) {
                console.error('No VISIBLE submit button found');
                return false;
            }
            
            // Verificar estado
            const isDisabled = button.disabled || 
                              button.getAttribute('disabled') !== null ||
                              button.classList.contains('disabled');
            
            console.log('Button enabled:', !isDisabled);
            console.log('Button classes:', button.className);
            
            // Scroll al botón
            button.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Remover disabled FORZOSAMENTE
            button.disabled = false;
            button.removeAttribute('disabled');
            button.classList.remove('disabled');
            
            // Hacer clickeable
            button.style.pointerEvents = 'auto';
            button.style.cursor = 'pointer';
            
            // Disparar eventos completos
            button.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
            button.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            button.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
            button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            
            // Click directo como fallback
            button.click();

            // ✅ Forzar submit real del formulario Angular
            // 🔥 Buscar el form real en todo el modal
            let form = null;
            const modal = button.closest('div, section, app-root, body');

            if (modal) {
                form = modal.querySelector('form');
            }

            if (form) {
                form.dispatchEvent(new Event('submit', { bubbles: true }));
                form.submit();
                console.log('✅ Form submit forzado desde modal');
            } else {
                console.log('⚠️ No se encontró <form>, fallback solo click');
            }


            console.log('Click + form submit forzado');

            return true;

            """
            
            success = driver.execute_script(script, selector)
            
            if success:
                logger.info("✓ Submit button clicked (JavaScript)")
                await asyncio.sleep(1.0)
                
                # Verificar cambio en página
                await asyncio.sleep(2)
                current_url = driver.current_url
                logger.debug(f"URL after submit: {current_url}")
                
                # Verificar si el modal sigue abierto (indicaría error)
                modal_still_open = driver.execute_script("""
                    const modal = document.querySelector('.modal.show, [role="dialog"][style*="display: block"]');
                    return modal !== null;
                """)
                
                if modal_still_open:
                    logger.warning("⚠️ Submit may not have worked - modal still open")
                else:
                    logger.info("✓ Modal closed after submit")
                
                return True
            else:
                logger.error("❌ Submit button not found or not clickable")
                return False
        
        except Exception as e:
            logger.error(f"Submit click error: {e}")
            return False
    
    async def _wait_for_element_robust(self, driver: webdriver.Chrome, selector: str, timeout: int = 15):
        """Espera elemento con múltiples estrategias"""
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
        """Llena campo estándar (no Angular)"""
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