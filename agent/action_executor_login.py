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
    """Ejecutor de login humanizado con soporte para Angular"""
    
    AUTH_ERROR_INDICATORS = [
        "wrong password",
        "incorrect password",
        "invalid credentials",
        "contraseña incorrecta",
        "credenciales inválidas",
        "usuario o contraseña incorrectos",
        "wrong username",
        "user not found",
        "usuario no encontrado",
        "datos incorrectos"
    ]
    
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
        """Ejecuta login humanizado con soporte para Angular"""
        
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
            # 1. Detectar reCAPTCHA antes de empezar
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
            
            # 3. ✅ NUEVO: Esperar a que el modal esté completamente cargado
            await self._wait_for_angular_modal(driver)
            logger.info(f"✓ Modal Angular cargado")
            
            # 4. Obtener selectores
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
            
            # 5. ✅ MEJORADO: Buscar campo username con múltiples estrategias
            username_element = await self._find_angular_input(driver, username_selector, "username", timeout=20)
            if not username_element:
                return LoginResult(False, "Username field not found", "username_field_not_found")
            
            logger.info(f"✓ Paso 3 completado - Username field found")

            # 6. ✅ Llenar username con disparo de eventos Angular
            username_filled = await self._fill_angular_field(driver, username_element, username)
            if not username_filled:
                return LoginResult(False, "Could not fill username field", "username_fill_failed")
            
            await asyncio.sleep(random.uniform(0.8, 1.5))
            logger.info(f"✓ Paso 4 completado - Username filled")

            # 7. Buscar campo password
            password_element = await self._find_angular_input(driver, password_selector, "password", timeout=15)
            if not password_element:
                return LoginResult(False, "Password field not found", "password_field_not_found")
            
            # 8. Llenar password con disparo de eventos Angular
            password_filled = await self._fill_angular_field(driver, password_element, password)
            if not password_filled:
                return LoginResult(False, "Could not fill password field", "password_fill_failed")
            
            await asyncio.sleep(random.uniform(1.0, 2.0))
            logger.info(f"✓ Paso 5 completado - Password filled")

            # 9. ✅ NUEVO: Esperar a que Angular valide el formulario
            await self._wait_for_form_validation(driver)
            logger.info(f"✓ Formulario validado por Angular")

            # 10. Detectar CAPTCHA después de llenar campos
            if not params.get("ignore_recaptcha", False) and self._detect_recaptcha(driver):
                logger.warning("⚠️ reCAPTCHA detected after filling fields")
                return LoginResult(
                    success=False,
                    message="reCAPTCHA detected after filling fields",
                    error_type="recaptcha",
                    needs_captcha=True
                )
            
            logger.info(f"✓ Paso 6 completado - No CAPTCHA detected")

            # 11. ✅ Click en submit (con manejo de botón deshabilitado)
            submit_clicked = await self._click_angular_submit(driver, submit_selector)
            if not submit_clicked:
                return LoginResult(False, "Could not click submit button", "submit_button_not_found")
            
            logger.info(f"✓ Paso 7 completado - Submit clicked")
            
            # 12. Esperar resultado
            wait_after = params.get("wait_after_submit", 5)
            await asyncio.sleep(wait_after)
            
            # 13. Verificar login exitoso
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
            
            # 14. Revisar errores
            page_text = driver.page_source.lower()
            if any(e in page_text for e in self.AUTH_ERROR_INDICATORS):
                return LoginResult(False, "Authentication failed", "auth_error")
            
            if any(b in page_text for b in self.BLOCKED_INDICATORS):
                return LoginResult(False, "Account blocked", "blocked", blocked=True)
            
            if any(f in page_text for f in self.TWO_FA_INDICATORS):
                return LoginResult(False, "2FA required", "2fa", needs_2fa=True)
            
            # 15. Asumir éxito si no hay errores
            return LoginResult(True, "Login completed (no errors detected)", None)
        
        except Exception as e:
            logger.error(f"Login execution error: {e}")
            return LoginResult(False, str(e), "exception")
    
    # ============================================
    # ✅ MÉTODOS NUEVOS PARA ANGULAR
    # ============================================
    
    async def _wait_for_angular_modal(self, driver: webdriver.Chrome, timeout: int = 10):
        """Espera a que el modal de Angular esté completamente cargado"""
        
        try:
            # Esperar a que el overlay esté presente
            await asyncio.sleep(2)
            
            # Verificar que Angular haya terminado de renderizar
            driver.execute_script("""
                // Forzar detección de cambios en Angular
                if (typeof window.getAllAngularTestabilities !== 'undefined') {
                    window.getAllAngularTestabilities().forEach(t => t.whenStable(() => {}));
                }
            """)
            
            await asyncio.sleep(1)
            logger.debug("✓ Modal Angular estabilizado")
            
        except Exception as e:
            logger.warning(f"Angular modal wait warning: {e}")
    
    async def _find_angular_input(
        self,
        driver: webdriver.Chrome,
        selector: str,
        field_name: str,
        timeout: int = 15
    ):
        """Busca input en modal Angular con múltiples estrategias"""
        
        selectors = [s.strip() for s in selector.split(",")]
        
        # Estrategia 1: Selectores directos
        for sel in selectors:
            try:
                logger.debug(f"Trying selector: {sel}")
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                
                # Verificar que esté visible en el modal
                is_visible = driver.execute_script("""
                    var elem = arguments[0];
                    var rect = elem.getBoundingClientRect();
                    var style = window.getComputedStyle(elem);
                    return (
                        style.display !== 'none' &&
                        style.visibility !== 'hidden' &&
                        rect.width > 0 &&
                        rect.height > 0
                    );
                """, element)
                
                if is_visible:
                    logger.debug(f"✓ Found with selector: {sel}")
                    return element
            except:
                continue
        
        # Estrategia 2: Buscar por atributos Angular específicos
        angular_attrs = {
            "username": [
                "formcontrolname='username'",
                "id='usernameLogin'",
                "placeholder*='usuario'",
                "placeholder*='correo'"
            ],
            "password": [
                "formcontrolname='password'",
                "id='toggle-password-sign-in'",
                "placeholder*='contraseña'",
                "type='password'"
            ]
        }
        
        for attr in angular_attrs.get(field_name, []):
            try:
                logger.debug(f"Trying Angular attribute: {attr}")
                selector_with_attr = f"input[{attr}]"
                elements = driver.find_elements(By.CSS_SELECTOR, selector_with_attr)
                
                for elem in elements:
                    is_visible = driver.execute_script("""
                        var elem = arguments[0];
                        var rect = elem.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    """, elem)
                    
                    if is_visible:
                        logger.debug(f"✓ Found with Angular attr: {attr}")
                        return elem
            except:
                continue
        
        logger.error(f"❌ {field_name} field not found with any strategy")
        return None
    
    async def _fill_angular_field(
        self,
        driver: webdriver.Chrome,
        element,
        text: str
    ) -> bool:
        """✅ VERSIÓN ULTRA-AGRESIVA: Llena campo Angular forzando escritura"""
        
        try:
            # 1. Scroll y hacer visible
            driver.execute_script("""
                var elem = arguments[0];
                elem.scrollIntoView({behavior: 'smooth', block: 'center'});
                elem.style.display = 'block';
                elem.style.visibility = 'visible';
                elem.style.opacity = '1';
            """, element)
            await asyncio.sleep(0.5)
            
            # 2. Remover atributo readonly y disabled
            driver.execute_script("""
                var elem = arguments[0];
                elem.removeAttribute('readonly');
                elem.removeAttribute('disabled');
                elem.disabled = false;
                elem.readOnly = false;
            """, element)
            
            # 3. Focus con múltiples métodos
            driver.execute_script("""
                var elem = arguments[0];
                elem.focus();
                elem.click();
                
                // Simular evento de mouse
                var rect = elem.getBoundingClientRect();
                var mouseEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: rect.left + rect.width / 2,
                    clientY: rect.top + rect.height / 2
                });
                elem.dispatchEvent(mouseEvent);
            """, element)
            await asyncio.sleep(0.5)
            
            # 4. Limpiar campo (múltiples métodos)
            driver.execute_script("""
                var elem = arguments[0];
                elem.value = '';
                elem.setAttribute('value', '');
            """, element)
            
            # Verificar que se limpió
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.BACKSPACE)
            await asyncio.sleep(0.3)
            
            # 5. ✅ MÉTODO 1: Escribir carácter por carácter con Selenium
            logger.debug(f"Writing text: '{text}'")
            for char in text:
                element.send_keys(char)
                await asyncio.sleep(random.uniform(0.08, 0.15))
            
            await asyncio.sleep(0.5)
            
            # 6. ✅ MÉTODO 2: Forzar con JavaScript como backup
            current_value = driver.execute_script("return arguments[0].value;", element)
            if not current_value or len(current_value) < len(text):
                logger.warning("⚠️ Selenium typing incomplete, forcing with JS...")
                driver.execute_script("""
                    var elem = arguments[0];
                    var text = arguments[1];
                    
                    // Forzar valor
                    elem.value = text;
                    elem.setAttribute('value', text);
                    
                    // Disparar TODOS los eventos posibles
                    elem.dispatchEvent(new Event('input', { bubbles: true }));
                    elem.dispatchEvent(new Event('change', { bubbles: true }));
                    elem.dispatchEvent(new Event('keyup', { bubbles: true }));
                    elem.dispatchEvent(new Event('keydown', { bubbles: true }));
                    elem.dispatchEvent(new Event('blur', { bubbles: true }));
                    
                    // Forzar cambio en el modelo Angular
                    if (elem._ngModelController) {
                        elem._ngModelController.$setViewValue(text);
                        elem._ngModelController.$render();
                    }
                    
                    // Método alternativo para Angular nuevo
                    var event = new Event('input', { 
                        bubbles: true,
                        cancelable: true 
                    });
                    Object.defineProperty(event, 'target', {
                        writable: false,
                        value: elem
                    });
                    elem.dispatchEvent(event);
                    
                """, element, text)
                await asyncio.sleep(0.5)
            
            # 7. ✅ CRÍTICO: Disparar detección de cambios de Angular
            driver.execute_script("""
                var element = arguments[0];
                
                // Método 1: Angular moderno (Angular 2+)
                try {
                    if (typeof window.ng !== 'undefined') {
                        // Intentar obtener el componente
                        const debugElement = window.ng.probe(element);
                        if (debugElement) {
                            const component = debugElement.componentInstance;
                            if (component) {
                                // Forzar detección de cambios
                                if (debugElement.injector) {
                                    const cd = debugElement.injector.get(window.ng.coreTokens.ChangeDetectorRef);
                                    if (cd) cd.detectChanges();
                                    
                                    const appRef = debugElement.injector.get(window.ng.coreTokens.ApplicationRef);
                                    if (appRef) appRef.tick();
                                }
                            }
                        }
                    }
                } catch(e) {
                    console.log('Angular change detection error:', e);
                }
                
                // Método 2: Forzar validación del formulario
                try {
                    const form = element.closest('form');
                    if (form) {
                        form.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                } catch(e) {}
                
                // Método 3: Disparar evento nativo
                element.dispatchEvent(new Event('input', { bubbles: true }));
                
            """, element)
            
            await asyncio.sleep(0.5)
            
            # 8. Verificar MÚLTIPLES VECES que se escribió
            for attempt in range(3):
                current_value = driver.execute_script("return arguments[0].value;", element)
                logger.debug(f"Verification attempt {attempt+1}: value = '{current_value}'")
                
                if current_value == text:
                    logger.info(f"✅ Field filled successfully: '{text}'")
                    
                    # Screenshot de confirmación
                    try:
                        timestamp = int(time.time())
                        filename = f"screenshots/field_filled_{timestamp}.png"
                        driver.save_screenshot(filename)
                        logger.debug(f"Field fill screenshot: {filename}")
                    except:
                        pass
                    
                    return True
                
                if attempt < 2:
                    # Reintentar con JS puro
                    logger.warning(f"⚠️ Value mismatch (attempt {attempt+1}): expected '{text}', got '{current_value}'")
                    driver.execute_script("arguments[0].value = arguments[1];", element, text)
                    driver.execute_script("""
                        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                    """, element)
                    await asyncio.sleep(0.5)
            
            # Si llegamos aquí, falló
            final_value = driver.execute_script("return arguments[0].value;", element)
            logger.error(f"❌ Field fill failed: expected '{text}', final value '{final_value}'")
            return False
        
        except Exception as e:
            logger.error(f"Fill Angular field error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _wait_for_form_validation(self, driver: webdriver.Chrome, timeout: int = 5):
        """Espera a que Angular valide el formulario"""
        
        try:
            # Esperar a que Angular procese la validación
            await asyncio.sleep(1.5)
            
            # Verificar estado del formulario
            is_valid = driver.execute_script("""
                // Buscar formulario Angular
                var forms = document.querySelectorAll('form');
                for (var i = 0; i < forms.length; i++) {
                    var form = forms[i];
                    
                    // Verificar clases de validación de Angular
                    if (form.classList.contains('ng-valid')) {
                        return true;
                    }
                    
                    // Verificar si todos los inputs tienen valores
                    var inputs = form.querySelectorAll('input[required], input[formcontrolname]');
                    var allFilled = Array.from(inputs).every(input => input.value.length > 0);
                    if (allFilled) {
                        return true;
                    }
                }
                
                return false;
            """)
            
            if is_valid:
                logger.debug("✓ Formulario válido")
            else:
                logger.warning("⚠️ Formulario podría no estar válido")
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.debug(f"Form validation check warning: {e}")
    
    async def _click_angular_submit(
        self,
        driver: webdriver.Chrome,
        selector: str
    ) -> bool:
        """✅ VERSIÓN ULTRA-AGRESIVA: Click en botón submit de Angular"""
        
        # Buscar botón
        element = await self._wait_for_element_robust(driver, selector, timeout=10)
        if not element:
            logger.error("Submit button not found")
            return False
        
        try:
            # 1. Screenshot ANTES del click
            try:
                timestamp = int(time.time())
                filename = f"screenshots/before_submit_{timestamp}.png"
                driver.save_screenshot(filename)
                logger.debug(f"Before submit screenshot: {filename}")
            except:
                pass
            
            # 2. Scroll hacia el botón
            driver.execute_script("""
                var btn = arguments[0];
                btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                
                // Hacer visible y clickeable
                btn.style.display = 'block';
                btn.style.visibility = 'visible';
                btn.style.opacity = '1';
                btn.style.pointerEvents = 'auto';
            """, element)
            await asyncio.sleep(0.8)
            
            # 3. ✅ FORZAR HABILITACIÓN (múltiples métodos)
            driver.execute_script("""
                var btn = arguments[0];
                
                // Remover disabled de todas las formas posibles
                btn.disabled = false;
                btn.removeAttribute('disabled');
                btn.setAttribute('disabled', 'false');
                
                // Remover clase disabled
                btn.classList.remove('disabled');
                btn.classList.remove('btn-disabled');
                
                // Forzar cursor pointer
                btn.style.cursor = 'pointer';
                
                console.log('Button enabled:', !btn.disabled);
            """, element)
            
            await asyncio.sleep(0.5)
            
            # 4. Verificar estado
            is_enabled = driver.execute_script("""
                var btn = arguments[0];
                return !btn.disabled && btn.offsetParent !== null;
            """, element)
            
            logger.info(f"Button enabled: {is_enabled}")
            
            # 5. ✅ MÉTODO 1: Click con JavaScript (MÁS CONFIABLE)
            logger.debug("Attempting JavaScript click...")
            click_result = driver.execute_script("""
                var btn = arguments[0];
                
                try {
                    // Focus
                    btn.focus();
                    
                    // Simular eventos completos de mouse
                    var rect = btn.getBoundingClientRect();
                    var x = rect.left + rect.width / 2;
                    var y = rect.top + rect.height / 2;
                    
                    // MouseDown
                    var mouseDownEvent = new MouseEvent('mousedown', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: x,
                        clientY: y,
                        button: 0
                    });
                    btn.dispatchEvent(mouseDownEvent);
                    
                    // MouseUp
                    var mouseUpEvent = new MouseEvent('mouseup', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: x,
                        clientY: y,
                        button: 0
                    });
                    btn.dispatchEvent(mouseUpEvent);
                    
                    // Click
                    var clickEvent = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true,
                        clientX: x,
                        clientY: y,
                        button: 0
                    });
                    btn.dispatchEvent(clickEvent);
                    
                    // Click directo (múltiples veces por si acaso)
                    btn.click();
                    
                    // Touch events para mobile
                    var touchEvent = new TouchEvent('touchstart', {
                        bubbles: true,
                        cancelable: true
                    });
                    btn.dispatchEvent(touchEvent);
                    
                    var touchEndEvent = new TouchEvent('touchend', {
                        bubbles: true,
                        cancelable: true
                    });
                    btn.dispatchEvent(touchEndEvent);
                    
                    console.log('Click events dispatched');
                    return true;
                    
                } catch(e) {
                    console.error('Click error:', e);
                    return false;
                }
            """, element)
            
            logger.info(f"JavaScript click result: {click_result}")
            await asyncio.sleep(1.0)
            
            # 6. ✅ MÉTODO 2: Selenium click como backup
            try:
                logger.debug("Attempting Selenium click...")
                element.click()
                logger.info("Selenium click executed")
            except Exception as e:
                logger.warning(f"Selenium click failed: {e}")
            
            await asyncio.sleep(0.5)
            
            # 7. ✅ MÉTODO 3: Submit del formulario directamente
            try:
                logger.debug("Attempting form submit...")
                driver.execute_script("""
                    var btn = arguments[0];
                    var form = btn.closest('form');
                    if (form) {
                        console.log('Submitting form directly');
                        
                        // Disparar submit
                        form.dispatchEvent(new Event('submit', { 
                            bubbles: true, 
                            cancelable: true 
                        }));
                        
                        // Método alternativo
                        if (form.requestSubmit) {
                            form.requestSubmit();
                        } else {
                            form.submit();
                        }
                    }
                """, element)
                logger.info("Form submit executed")
            except Exception as e:
                logger.warning(f"Form submit failed: {e}")
            
            await asyncio.sleep(1.0)
            
            # 8. Screenshot DESPUÉS del click
            try:
                timestamp = int(time.time())
                filename = f"screenshots/after_submit_{timestamp}.png"
                driver.save_screenshot(filename)
                logger.debug(f"After submit screenshot: {filename}")
            except:
                pass
            
            # 9. Verificar si hubo cambio en la página
            await asyncio.sleep(2.0)
            
            # Verificar URL cambió o hay loading
            has_changed = driver.execute_script("""
                // Verificar si hay indicador de loading
                var loadingIndicators = document.querySelectorAll(
                    '.loading, .spinner, [class*="loading"], [class*="spinner"]'
                );
                
                if (loadingIndicators.length > 0) {
                    console.log('Loading indicator found');
                    return true;
                }
                
                // Verificar si el modal se cerró
                var modal = document.querySelector('.modal, [class*="modal"]');
                if (!modal || modal.style.display === 'none') {
                    console.log('Modal closed');
                    return true;
                }
                
                return false;
            """)
            
            if has_changed:
                logger.info("✅ Submit successful - page changed")
                return True
            else:
                logger.warning("⚠️ Submit may not have worked - no visible change")
                return True  # Retornar True de todos modos para continuar
        
        except Exception as e:
            logger.error(f"Submit click error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _wait_for_element_robust(
        self,
        driver: webdriver.Chrome,
        selector: str,
        timeout: int = 15
    ):
        """Espera elemento con múltiples estrategias"""
        
        selectors = [s.strip() for s in selector.split(",")]
        
        for sel in selectors:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, sel))
                )
                if element:
                    return element
            except:
                continue
        
        return None
    
    def _detect_recaptcha(self, driver: webdriver.Chrome) -> bool:
        """Detecta si hay un reCAPTCHA visible"""
        try:
            recaptcha_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            for iframe in recaptcha_iframes:
                if iframe.is_displayed():
                    return True
            
            checkboxes = driver.find_elements(By.CSS_SELECTOR, ".g-recaptcha, .recaptcha-checkbox")
            for box in checkboxes:
                if box.is_displayed():
                    return True
            
            return False
        except Exception:
            return False
    
    async def _wait_for_page_stability(self, driver: webdriver.Chrome, timeout: int = 3):
        await asyncio.sleep(random.uniform(timeout, timeout + 2))