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
            logger.info(f"Termiina paso 1")

            # 2. Esperar estabilidad de la página
            await self._wait_for_page_stability(driver)
            logger.info(f"Termiina paso 2")

            
            # 3. Esperar a que los campos del modal estén visibles
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
            
            await self._wait_for_element(driver, username_selector)
            logger.info(f"Termiina paso 3")

            # 4. Llenar username
            username_filled = await self._fill_username(driver, username, username_selector)
            if not username_filled:
                return LoginResult(False, "Could not find username field", "username_field_not_found")
            
            await asyncio.sleep(random.uniform(0.8, 1.5))
            
            logger.info(f"Termiina paso 4")

            # 5. Llenar password
            password_filled = await self._fill_password(driver, password, password_selector)
            if not password_filled:
                return LoginResult(False, "Could not find password field", "password_field_not_found")
            
            await asyncio.sleep(random.uniform(1.0, 2.0))
            logger.info(f"Termiina paso 5")

            # 6. Detectar CAPTCHA visible después de llenar campos
            if not params.get("ignore_recaptcha", False) and self._detect_recaptcha(driver):
                logger.warning("⚠️ reCAPTCHA detected after filling fields")
                return LoginResult(
                    success=False,
                    message="reCAPTCHA detected after filling fields",
                    error_type="recaptcha",
                    needs_captcha=True
                )
            
            logger.info(f"Termiina paso 6")

            # 7. Hacer click en submit
            submit_clicked = await self._click_submit(driver, submit_selector)
            if not submit_clicked:
                return LoginResult(False, "Could not click submit button", "submit_button_not_found")
            
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
    # Métodos internos auxiliares
    # -----------------------------
    
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
    
    async def _wait_for_element(self, driver: webdriver.Chrome, selector: str, timeout: int = 10):
        """Espera hasta que un elemento sea visible"""
        selectors = [s.strip() for s in selector.split(",")]
        for sel in selectors:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                )
                return True
            except TimeoutException:
                continue
        return False
    
    async def _fill_username(self, driver: webdriver.Chrome, username: str, selector: str) -> bool:
        element = None
        selectors = [s.strip() for s in selector.split(",")]
        for sel in selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                )
                if element.is_displayed():
                    break
            except TimeoutException:
                continue
        if not element:
            return False
        element.click()
        await asyncio.sleep(random.uniform(0.2, 0.5))
        for char in username:
            element.send_keys(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))
        return True
    
    async def _fill_password(self, driver: webdriver.Chrome, password: str, selector: str) -> bool:
        element = None
        selectors = [s.strip() for s in selector.split(",")]
        for sel in selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, sel))
                )
                if element.is_displayed():
                    break
            except TimeoutException:
                continue
        if not element:
            return False
        element.click()
        await asyncio.sleep(random.uniform(0.2, 0.5))
        for char in password:
            element.send_keys(char)
            await asyncio.sleep(random.uniform(0.05, 0.15))
        return True
    
    async def _click_submit(self, driver: webdriver.Chrome, selector: str) -> bool:
        element = None
        selectors = [s.strip() for s in selector.split(",")]
        for sel in selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                if element.is_displayed():
                    break
            except TimeoutException:
                continue
        if not element:
            return False
        element.click()
        await asyncio.sleep(random.uniform(0.5, 1.0))
        return True
